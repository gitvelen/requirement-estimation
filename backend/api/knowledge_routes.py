"""
知识库管理API路由
提供知识导入、检索、统计等接口
"""
import logging
import os
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from pydantic import BaseModel

from backend.service.knowledge_service import get_knowledge_service
from backend.api.auth import require_roles

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

        # 验证文件大小（限制50MB）
        if len(content) > 50 * 1024 * 1024:
            raise HTTPException(
                status_code=413,
                detail="文件过大，最大允许50MB"
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

