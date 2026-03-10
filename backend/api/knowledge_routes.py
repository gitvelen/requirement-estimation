"""
知识库管理API路由
提供知识导入、检索、统计等接口
"""
import json
import logging
import os
import uuid
from typing import Any, Dict, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Request
from pydantic import BaseModel

from backend.config.config import settings
from backend.service.knowledge_service import get_knowledge_service
from backend.service.system_profile_service import get_system_profile_service
from backend.api.auth import require_roles
from backend.api.error_utils import build_error_response
from backend.api import system_routes

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/v1/knowledge", tags=["知识库管理"])


class SearchRequest(BaseModel):
    """知识检索请求"""
    query: str  # 查询文本
    system_name: Optional[str] = None  # 过滤系统名称
    knowledge_type: Optional[str] = None  # 过滤知识类型
    top_k: int = 5  # 返回结果数
    similarity_threshold: float = 0.6  # 相似度阈值




SUPPORTED_IMPORT_EXTENSIONS = {".docx", ".doc", ".pdf", ".pptx", ".txt", ".xlsx", ".xls", ".csv"}
SUPPORTED_DOC_TYPES = {"requirements", "design", "tech_solution", "history_report"}


def _parsed_to_text(parsed_data: Any) -> str:
    if isinstance(parsed_data, str):
        return parsed_data

    if isinstance(parsed_data, list):
        lines = []
        for item in parsed_data:
            if isinstance(item, dict):
                line = " ".join(str(v).strip() for v in item.values() if str(v).strip())
                if line:
                    lines.append(line)
            elif item is not None:
                line = str(item).strip()
                if line:
                    lines.append(line)
        return "\n".join(lines)

    if isinstance(parsed_data, dict):
        if "text" in parsed_data and isinstance(parsed_data.get("text"), str):
            return str(parsed_data.get("text") or "")

        # DOCX parser output: {"paragraphs": [...], "tables": [...], "metadata": {...}}
        if "paragraphs" in parsed_data:
            lines = []
            for paragraph in parsed_data.get("paragraphs") or []:
                if isinstance(paragraph, dict):
                    line = str(paragraph.get("text") or "").strip()
                else:
                    line = str(paragraph or "").strip()
                if line:
                    lines.append(line)

            for table in parsed_data.get("tables") or []:
                if not isinstance(table, dict):
                    continue
                for row in table.get("data") or []:
                    if isinstance(row, list):
                        line = " | ".join(str(cell).strip() for cell in row if cell is not None and str(cell).strip())
                    elif isinstance(row, dict):
                        line = " ".join(str(v).strip() for v in row.values() if str(v).strip())
                    else:
                        line = str(row or "").strip()
                    if line:
                        lines.append(line)

            if lines:
                return "\n".join(lines)

        # PPTX parser output: {"slides": [...]}
        if "slides" in parsed_data:
            lines = []
            for slide in parsed_data.get("slides") or []:
                if isinstance(slide, dict):
                    line = str(slide.get("text") or "").strip()
                else:
                    line = str(slide or "").strip()
                if line:
                    lines.append(line)
            if lines:
                return "\n".join(lines)

        # PDF parser output: {"pages": [...]}
        if "pages" in parsed_data:
            lines = []
            for page in parsed_data.get("pages") or []:
                if isinstance(page, dict):
                    line = str(page.get("text") or "").strip()
                else:
                    line = str(page or "").strip()
                if line:
                    lines.append(line)
            if lines:
                return "\n".join(lines)

        if parsed_data and all(isinstance(v, list) for v in parsed_data.values()):
            lines = []
            for _, rows in parsed_data.items():
                for row in rows:
                    if isinstance(row, list):
                        line = " | ".join(str(cell).strip() for cell in row if cell is not None and str(cell).strip())
                        if line:
                            lines.append(line)
                    elif isinstance(row, dict):
                        line = " ".join(str(v).strip() for v in row.values() if str(v).strip())
                        if line:
                            lines.append(line)
            if lines:
                return "\n".join(lines)

        try:
            return json.dumps(parsed_data, ensure_ascii=False)
        except Exception:
            return str(parsed_data)

    return str(parsed_data)


def _resolve_system_binding(system_id: str, system_name: str, guessed_system_name: str) -> Dict[str, str]:
    normalized_id = str(system_id or "").strip()
    normalized_name = str(system_name or "").strip()
    guessed_name = str(guessed_system_name or "").strip()

    if normalized_id:
        owner_info = system_routes.resolve_system_owner(system_id=normalized_id)
        if owner_info.get("system_found"):
            return {
                "system_id": str(owner_info.get("system_id") or normalized_id),
                "system_name": str(owner_info.get("system_name") or ""),
            }

    if normalized_name:
        owner_info = system_routes.resolve_system_owner(system_name=normalized_name)
        if owner_info.get("system_found"):
            return {
                "system_id": str(owner_info.get("system_id") or ""),
                "system_name": str(owner_info.get("system_name") or normalized_name),
            }

    if guessed_name:
        owner_info = system_routes.resolve_system_owner(system_name=guessed_name)
        if owner_info.get("system_found"):
            return {
                "system_id": str(owner_info.get("system_id") or ""),
                "system_name": str(owner_info.get("system_name") or guessed_name),
            }

    return {"system_id": "", "system_name": ""}


@router.post("/imports")
async def import_knowledge_v2(
    request: Request,
    file: UploadFile = File(...),
    knowledge_type: str = Form(...),
    level: str = Form("normal"),
    doc_type: Optional[str] = Form(None),
    system_name: Optional[str] = Form(None),
    system_id: Optional[str] = Form(None),
    current_user: Dict[str, Any] = Depends(require_roles(["manager"])),
):
    normalized_type = str(knowledge_type or "").strip().lower()
    if normalized_type not in {"document", "code"}:
        return build_error_response(
            request=request,
            status_code=400,
            error_code="KNOW_001",
            message="知识库文件类型不支持",
            details={"reason": "knowledge_type 仅支持 document/code"},
        )

    normalized_level = str(level or "normal").strip().lower() or "normal"
    if normalized_level not in {"normal", "l0"}:
        return build_error_response(
            request=request,
            status_code=400,
            error_code="KNOW_001",
            message="知识库文件类型不支持",
            details={"reason": "level 仅支持 normal/l0"},
        )

    if normalized_level == "l0" and normalized_type != "document":
        return build_error_response(
            request=request,
            status_code=400,
            error_code="KNOW_001",
            message="知识库文件类型不支持",
            details={"reason": "仅 knowledge_type=document 支持 level=l0"},
        )

    normalized_doc_type = str(doc_type or "").strip().lower()
    if normalized_doc_type and normalized_doc_type not in SUPPORTED_DOC_TYPES:
        return build_error_response(
            request=request,
            status_code=400,
            error_code="KNOW_001",
            message="知识库文件类型不支持",
            details={"reason": f"doc_type 仅支持 {', '.join(sorted(SUPPORTED_DOC_TYPES))}"},
        )

    if normalized_doc_type and normalized_type != "document":
        return build_error_response(
            request=request,
            status_code=400,
            error_code="KNOW_001",
            message="知识库文件类型不支持",
            details={"reason": "仅 knowledge_type=document 支持 doc_type"},
        )

    if not file.filename:
        return build_error_response(
            request=request,
            status_code=400,
            error_code="KNOW_001",
            message="知识库文件类型不支持",
        )

    ext = os.path.splitext(file.filename.lower())[1]
    if ext not in SUPPORTED_IMPORT_EXTENSIONS:
        return build_error_response(
            request=request,
            status_code=400,
            error_code="KNOW_001",
            message="知识库文件类型不支持",
            details={"filename": file.filename},
        )

    try:
        file_content = await file.read()
        if not file_content:
            raise ValueError("知识库文件解析失败")

        max_bytes = int(getattr(settings, "KNOWLEDGE_IMPORT_MAX_BYTES", 200 * 1024 * 1024))
        max_mb = max(int(max_bytes // (1024 * 1024)), 1)
        if len(file_content) > max_bytes:
            return build_error_response(
                request=request,
                status_code=400,
                error_code="KNOW_001",
                message="知识库文件类型不支持",
                details={"reason": f"文件大小超过{max_mb}MB限制"},
            )

        knowledge_service = get_knowledge_service()

        parsed_data = knowledge_service.document_parser.parse(
            file_content=file_content,
            filename=file.filename,
        )
        text_content = _parsed_to_text(parsed_data)
        if not str(text_content or "").strip():
            text_content = file_content.decode("utf-8", errors="ignore")

        chunks = knowledge_service._chunk_text(text_content)
        if not chunks:
            raise ValueError("知识库文件解析失败")

        provided_system_name = str(system_name or "").strip()
        provided_system_id = str(system_id or "").strip()
        explicit_binding = bool(provided_system_name or provided_system_id)
        guessed_name = ""
        if (not provided_system_name) and (not provided_system_id):
            guessed_name = knowledge_service._guess_system_name(text_content[:3000], file.filename)

        binding = _resolve_system_binding(
            system_id=provided_system_id,
            system_name=provided_system_name,
            guessed_system_name=guessed_name,
        )
        bound_system_name = str(binding.get("system_name") or "").strip()
        bound_system_id = str(binding.get("system_id") or "").strip()

        if bound_system_name and bound_system_id:
            ownership = system_routes.resolve_system_ownership(
                current_user,
                system_id=bound_system_id,
                system_name=bound_system_name,
            )
            if not ownership.get("allowed_draft_write"):
                owner_info = ownership.get("owner_info") or {}
                resolved_owner_id = str(owner_info.get("resolved_owner_id") or "").strip()
                resolved_backups = owner_info.get("resolved_backup_owner_ids") or []
                has_backups = any(str(item).strip() for item in resolved_backups)
                reason = "当前用户不是系统主责或B角"
                if (not resolved_owner_id) and (not has_backups):
                    reason = "系统清单未配置主责或B角（owner_id/owner_username/backup_owner_ids/backup_owner_usernames）"
                elif owner_info.get("mapping_status") == "owner_username_unresolved":
                    reason = "owner_username 未映射到有效用户"

                if explicit_binding:
                    return build_error_response(
                        request=request,
                        status_code=403,
                        error_code="AUTH_001",
                        message="权限不足",
                        details={"reason": reason, "system_id": bound_system_id, "system_name": bound_system_name},
                    )

                # system binding is guessed; avoid unauthorized binding by falling back to UNASSIGNED
                bound_system_name = ""
                bound_system_id = ""

        storage_system_name = bound_system_name or "UNASSIGNED"

        try:
            embeddings = knowledge_service.embedding_service.batch_generate_embeddings(chunks)
        except Exception as exc:
            return build_error_response(
                request=request,
                status_code=503,
                error_code="EMB_001",
                message="embedding服务不可用，请稍后重试",
                details={"reason": str(exc)},
            )

        knowledge_list = []
        for idx, chunk in enumerate(chunks):
            embedding = embeddings[idx] if idx < len(embeddings) else []
            metadata = {
                "level": normalized_level,
                "doc_type": normalized_doc_type,
                "chunk_index": idx,
                "source_filename": file.filename,
                "bound_system_id": bound_system_id,
                "bound_system_name": bound_system_name,
                "imported_by": str(current_user.get("id") or current_user.get("username") or ""),
            }
            knowledge_list.append(
                {
                    "system_name": storage_system_name,
                    "knowledge_type": normalized_type,
                    "content": chunk,
                    "embedding": embedding,
                    "metadata": metadata,
                    "source_file": file.filename,
                }
            )

        insert_result = knowledge_service.vector_store.batch_insert_knowledge(knowledge_list)
        imported = int(insert_result.get("success") or 0)
        failed = int(insert_result.get("failed") or 0)
        errors = []
        if failed > 0:
            errors.append(f"{failed} 条知识写入失败")
        if not bound_system_name:
            errors.append("未绑定系统，不更新完整度")

        if imported > 0 and bound_system_name and normalized_type == "document":
            profile_service = get_system_profile_service()
            profile_service.mark_document_imported(
                system_name=bound_system_name,
                system_id=bound_system_id or None,
                import_id=f"know_{uuid.uuid4().hex}",
                source_file=file.filename,
                level=normalized_level,
                actor=current_user,
            )

            # 异步触发系统画像AI总结（失败不影响主流程）
            try:
                from backend.service.profile_summary_service import get_profile_summary_service

                if bound_system_id and bound_system_name:
                    get_profile_summary_service().trigger_summary(
                        system_id=bound_system_id,
                        system_name=bound_system_name,
                        actor=current_user,
                        reason="knowledge_import",
                        context_override={"document_text": text_content},
                    )
            except Exception as exc:
                logger.warning("触发画像AI总结失败（忽略）: %s", exc)

        return {
            "imported": imported,
            "failed": failed,
            "errors": errors,
        }
    except ValueError as exc:
        reason = str(exc).strip()
        return build_error_response(
            request=request,
            status_code=400,
            error_code="KNOW_002",
            message=f"知识库文件解析失败：{reason}" if reason else "知识库文件解析失败",
            details={"reason": reason},
        )
    except Exception as exc:
        reason = str(exc).strip()
        logger.error("知识导入失败: %s", exc)
        return build_error_response(
            request=request,
            status_code=400,
            error_code="KNOW_002",
            message=f"知识库文件解析失败：{reason}" if reason else "知识库文件解析失败",
            details={"reason": reason},
        )

@router.post("/import")
async def import_knowledge(
    file: UploadFile = File(...),
    auto_extract: bool = Form(True),
    knowledge_type: Optional[str] = Form(None),
    system_name: Optional[str] = Form(None),
    _auth: None = Depends(require_roles(["manager"]))
):
    """
    导入知识库文件

    支持的文件格式：
    - DOCX: 系统说明书、系统架构说明
    - PPTX: 系统架构汇报、系统介绍材料

    Args:
        file: 上传的文件
        auto_extract: 是否自动提取结构化数据
        system_name: 主系统名称（知识库维度）

    Returns:
        Dict: 导入结果
            {
                "code": 200,
                "message": "导入成功",
                "data": {
                    "total": 50,
                    "success": 48,
                    "failed": 2,
                    "errors": [...]
                }
            }
    """
    try:
        logger.info(f"接收到知识导入请求: {file.filename}")

        normalized_system = str(system_name or "").strip()
        if not normalized_system:
            raise HTTPException(status_code=400, detail="请选择主系统（system_name）")

        if knowledge_type and str(knowledge_type).strip() not in ("", "system_profile"):
            raise HTTPException(status_code=400, detail="当前仅支持导入系统知识（system_profile）")

        # 验证文件名
        if not file.filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")

        ext = os.path.splitext(file.filename.lower())[1]
        if ext not in (".docx", ".pptx"):
            raise HTTPException(status_code=400, detail="仅支持 DOCX / PPTX 格式导入系统知识")

        # 读取文件内容
        content = await file.read()

        # 验证文件大小（可配置，默认200MB）
        max_bytes = int(getattr(settings, "KNOWLEDGE_IMPORT_MAX_BYTES", 200 * 1024 * 1024))
        max_mb = max(int(max_bytes // (1024 * 1024)), 1)
        if len(content) > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"文件过大，最大允许{max_mb}MB"
            )

        # 获取知识库服务
        knowledge_service = get_knowledge_service()

        # 导入文件
        result = knowledge_service.import_from_file(
            file_content=content,
            filename=file.filename,
            auto_extract=auto_extract,
            knowledge_type="system_profile",
            system_name=normalized_system
        )

        return {
            "code": 200,
            "message": f"导入完成，成功{result['success']}条，失败{result['failed']}条",
            "data": result
        }

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"知识导入失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"知识导入失败: {str(e)}"
        )


@router.post("/search")
async def search_knowledge(
    request: SearchRequest,
    _auth: None = Depends(require_roles(["manager"]))
):
    """
    检索相似知识

    Args:
        request: 检索请求

    Returns:
        Dict: 检索结果
            {
                "code": 200,
                "data": {
                    "total": 3,
                    "results": [...]
                }
            }
    """
    try:
        logger.info(f"接收到知识检索请求: {request.query}")

        normalized_system = str(request.system_name or "").strip()
        if not normalized_system:
            raise HTTPException(status_code=400, detail="请选择主系统（system_name）")
        if request.knowledge_type and str(request.knowledge_type).strip() not in ("", "system_profile"):
            raise HTTPException(status_code=400, detail="当前仅支持检索系统知识（system_profile）")

        # 获取知识库服务
        knowledge_service = get_knowledge_service()

        # 执行检索
        results = knowledge_service.search_similar_knowledge(
            query_text=request.query,
            system_name=normalized_system,
            knowledge_type="system_profile",
            top_k=request.top_k,
            similarity_threshold=request.similarity_threshold
        )

        return {
            "code": 200,
            "data": {
                "total": len(results),
                "results": results
            }
        }

    except Exception as e:
        logger.error(f"知识检索失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"知识检索失败: {str(e)}"
        )


@router.get("/stats")
async def get_knowledge_stats(
    system_name: Optional[str] = None,
    _auth: None = Depends(require_roles(["manager"]))
):
    """
    获取知识库统计信息

    Returns:
        Dict: 统计信息
            {
                "code": 200,
                "data": {
                    "name": "system_knowledge",
                    "count": 100,
                    "index": "IVF_FLAT"
                }
            }
    """
    try:
        # 获取知识库服务
        knowledge_service = get_knowledge_service()

        # 获取统计信息
        stats = knowledge_service.get_knowledge_stats(system_name=system_name)

        return {
            "code": 200,
            "data": stats
        }

    except Exception as e:
        logger.error(f"获取统计信息失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取统计信息失败: {str(e)}"
        )


@router.post("/rebuild-index")
async def rebuild_index(_auth: None = Depends(require_roles(["manager"]))):
    """
    重建索引

    Returns:
        Dict: 重建结果
    """
    try:
        logger.info("接收到索引重建请求")

        # 获取知识库服务
        knowledge_service = get_knowledge_service()

        # 重建索引
        result = knowledge_service.rebuild_index()

        return {
            "code": 200,
            "message": "索引重建完成",
            "data": result
        }

    except Exception as e:
        logger.error(f"重建索引失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"重建索引失败: {str(e)}"
        )


@router.get("/health")
async def health_check(
    _auth: None = Depends(require_roles(["manager"]))
):
    """
    健康检查

    Returns:
        Dict: 健康状态
    """
    try:
        # 获取知识库服务
        knowledge_service = get_knowledge_service()

        # 检查连接
        stats = knowledge_service.get_knowledge_stats()

        if stats:
            return {
                "code": 200,
                "status": "healthy",
                "service": "knowledge_base"
            }
        else:
            return {
                "code": 503,
                "status": "unhealthy",
                "service": "knowledge_base"
            }

    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        return {
            "code": 503,
            "status": "unhealthy",
            "error": str(e)
        }


@router.get("/evaluation-metrics")
async def get_evaluation_metrics(
    _auth: None = Depends(require_roles(["manager"]))
):
    """
    获取知识库效果评估指标

    Returns:
        Dict: 评估指标
            {
                "code": 200,
                "data": {
                    "hit_rate": 75.5,  # 检索命中率（%）
                    "avg_similarity": 68.2,  # 平均相似度（%）
                    "adoption_rate": 45.3,  # 案例采纳率（%）
                    "total_searches": 120,  # 总检索次数
                    "total_tasks": 159,  # 总评估任务数
                    "quality_comparison": {
                        "with_kb": 85.2,  # 使用知识库的准确度（%）
                        "without_kb": 72.1  # 未使用知识库的准确度（%）
                    }
                }
            }
    """
    try:
        knowledge_service = get_knowledge_service()
        metrics = knowledge_service.get_evaluation_metrics()

        return {
            "code": 200,
            "data": metrics
        }

    except Exception as e:
        logger.error(f"获取评估指标失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取评估指标失败: {str(e)}")
