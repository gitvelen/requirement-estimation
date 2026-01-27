"""
知识库管理API路由
提供知识导入、检索、统计等接口
"""
import logging
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel

from backend.service.knowledge_service import get_knowledge_service

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


class FeatureCaseData(BaseModel):
    """功能案例数据"""
    system_name: str  # 系统名称
    module: str  # 功能模块
    feature_name: str  # 功能点名称
    description: str  # 业务描述
    estimated_days: float  # 预估人天
    complexity: str  # 复杂度（高/中/低）
    tech_points: str = ""  # 技术要点
    dependencies: str = ""  # 依赖系统
    project_case: str = ""  # 实施案例
    source: str = "人工修正"  # 来源


@router.post("/import")
async def import_knowledge(
    file: UploadFile = File(...),
    auto_extract: bool = Form(True)
):
    """
    导入知识库文件

    支持的文件格式：
    - CSV: 系统知识库、功能案例库
    - DOCX: 系统说明书、需求文档
    - XLSX: Excel格式的系统清单、案例库
    - PDF: 架构文档、技术方案

    Args:
        file: 上传的文件
        auto_extract: 是否自动提取结构化数据

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

        # 验证文件名
        if not file.filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")

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
            auto_extract=auto_extract
        )

        return {
            "code": 200,
            "message": f"导入完成，成功{result['success']}条，失败{result['failed']}条",
            "data": result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"知识导入失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"知识导入失败: {str(e)}"
        )


@router.post("/search")
async def search_knowledge(request: SearchRequest):
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

        # 获取知识库服务
        knowledge_service = get_knowledge_service()

        # 执行检索
        results = knowledge_service.search_similar_knowledge(
            query_text=request.query,
            system_name=request.system_name,
            knowledge_type=request.knowledge_type,
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
async def get_knowledge_stats():
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
        stats = knowledge_service.get_knowledge_stats()

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
async def rebuild_index():
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
async def health_check():
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


@router.post("/save_case")
async def save_feature_case(case_data: FeatureCaseData):
    """
    保存功能案例到知识库

    将人工修正后的功能点保存为案例，供后续评估参考

    Args:
        case_data: 案例数据

    Returns:
        Dict: 保存结果
    """
    try:
        logger.info(f"接收到保存案例请求: {case_data.system_name} - {case_data.feature_name}")

        # 获取知识库服务
        knowledge_service = get_knowledge_service()

        # 保存案例
        result = knowledge_service.save_feature_case(
            system_name=case_data.system_name,
            module=case_data.module,
            feature_name=case_data.feature_name,
            description=case_data.description,
            estimated_days=case_data.estimated_days,
            complexity=case_data.complexity,
            tech_points=case_data.tech_points,
            dependencies=case_data.dependencies,
            project_case=case_data.project_case,
            source=case_data.source
        )

        if result["status"] == "success":
            return {
                "code": 200,
                "message": "案例保存成功",
                "data": result["case"]
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "保存失败")
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"保存案例失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"保存案例失败: {str(e)}"
        )
