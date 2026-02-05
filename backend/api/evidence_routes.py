"""
证据库API路由
"""
import logging
import os
from typing import Optional, Dict, Any

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.api.auth import require_roles, get_current_user
from backend.service.evidence_service import get_evidence_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/knowledge/evidence", tags=["证据库"])


class EvidenceSearchRequest(BaseModel):
    query: str
    system_id: Optional[str] = None
    system_name: Optional[str] = None
    top_k: int = 5
    similarity_threshold: float = 0.6
    task_id: Optional[str] = None


@router.post("/import")
async def import_evidence(
    file: UploadFile = File(...),
    system_name: str = Form(...),
    system_id: Optional[str] = Form(None),
    trust_level: str = Form("中"),
    doc_date: Optional[str] = Form(None),
    source_org: Optional[str] = Form(None),
    version_hint: Optional[str] = Form(None),
    current_user: Dict[str, Any] = Depends(require_roles(["manager"]))
):
    """
    导入证据材料（DOCX/PPTX/PDF）
    """
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")

        content = await file.read()
        if len(content) > 50 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="文件过大，最大允许50MB")

        if trust_level not in ("高", "中", "低"):
            raise HTTPException(status_code=400, detail="trust_level仅支持 高/中/低")

        service = get_evidence_service()
        result = service.import_evidence(
            file_content=content,
            filename=file.filename,
            system_name=system_name,
            system_id=system_id,
            trust_level=trust_level,
            doc_date=doc_date,
            source_org=source_org,
            version_hint=version_hint,
            created_by=current_user.get("id")
        )

        return {
            "code": 200,
            "message": "导入完成",
            "data": result
        }
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(f"证据导入失败: {exc}")
        raise HTTPException(status_code=500, detail=f"证据导入失败: {exc}") from exc


@router.get("/list")
async def list_evidence(
    system_id: Optional[str] = None,
    system_name: Optional[str] = None,
    limit: int = Query(200, ge=1, le=1000),
    _auth: None = Depends(require_roles(["manager"]))
):
    """
    证据文档列表（按系统过滤）
    """
    service = get_evidence_service()
    docs = service.list_docs(system_name=system_name, system_id=system_id, limit=limit)
    return {
        "code": 200,
        "data": docs
    }


@router.post("/search")
async def search_evidence(
    request: EvidenceSearchRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    检索证据块（支持按系统过滤）
    """
    roles = current_user.get("roles", [])
    if "manager" not in roles and "expert" not in roles and "admin" not in roles:
        raise HTTPException(status_code=403, detail="权限不足")

    if "expert" in roles and not request.task_id:
        raise HTTPException(status_code=400, detail="专家检索需提供task_id")

    try:
        service = get_evidence_service()
        results = service.search_evidence(
            query=request.query,
            system_name=request.system_name,
            system_id=request.system_id,
            top_k=request.top_k,
            similarity_threshold=request.similarity_threshold,
            task_id=request.task_id,
            actor=current_user
        )
        return {
            "code": 200,
            "data": {
                "total": len(results),
                "results": results
            }
        }
    except Exception as exc:
        logger.error(f"证据检索失败: {exc}")
        raise HTTPException(status_code=500, detail=f"证据检索失败: {exc}") from exc


@router.get("/stats")
async def evidence_stats(
    system_id: Optional[str] = None,
    system_name: Optional[str] = None,
    _auth: None = Depends(require_roles(["manager"]))
):
    """
    证据统计
    """
    service = get_evidence_service()
    stats = service.get_stats(system_name=system_name, system_id=system_id)
    return {"code": 200, "data": stats}


@router.get("/preview/{doc_id}")
async def preview_evidence(
    doc_id: str,
    task_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    在线预览证据材料（不提供下载）
    """
    service = get_evidence_service()
    if not service.can_preview_doc(current_user, doc_id, task_id=task_id):
        raise HTTPException(status_code=403, detail="无权预览该证据")

    doc = service.get_doc(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="证据不存在")

    stored_path = doc.get("stored_path")
    doc_type = doc.get("doc_type")
    if not stored_path or not os.path.exists(stored_path):
        raise HTTPException(status_code=404, detail="证据文件不存在")

    if doc_type == "pdf":
        return FileResponse(
            stored_path,
            media_type="application/pdf",
            filename=doc.get("filename"),
            headers={"Content-Disposition": f"inline; filename={doc.get('filename') or 'evidence.pdf'}"}
        )

    preview = service.get_preview_text(doc)
    return {
        "code": 200,
        "data": preview
    }

