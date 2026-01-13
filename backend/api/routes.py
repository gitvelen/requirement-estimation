"""
API路由
定义所有RESTful API接口
"""
import os
import uuid
import logging
from datetime import datetime
from typing import Dict, Any
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from backend.utils.docx_parser import docx_parser
from backend.agent.agent_orchestrator import agent_orchestrator
from backend.config.config import settings

# 创建线程池用于异步任务处理
executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="task_worker")

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix=settings.API_PREFIX, tags=["需求评估"])

# 全局任务存储（生产环境应使用Redis或数据库）
task_storage = {}


class EvaluateRequest(BaseModel):
    """评估请求模型"""
    request_id: str
    callback_url: str = None
    priority: int = 0


class TaskStatusResponse(BaseModel):
    """任务状态响应模型"""
    task_id: str
    status: str  # pending, processing, completed, failed
    progress: int  # 0-100
    message: str
    report_path: str = None
    error: str = None


@router.post("/requirement/upload")
async def upload_requirement(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """
    上传需求文档并启动评估任务

    Args:
        file: 上传的.docx文件
        background_tasks: 后台任务

    Returns:
        Dict: 包含task_id的任务信息
    """
    try:
        logger.info(f"接收到文件上传请求: {file.filename}")

        # 验证文件
        if not file.filename.endswith(".docx"):
            raise HTTPException(status_code=400, detail="仅支持.docx格式文件")

        # 生成任务ID
        task_id = str(uuid.uuid4())

        # 保存文件
        upload_dir = settings.UPLOAD_DIR
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, f"{task_id}_{file.filename}")

        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        logger.info(f"文件已保存: {file_path}")

        # 创建任务记录
        task_storage[task_id] = {
            "task_id": task_id,
            "filename": file.filename,
            "file_path": file_path,
            "status": "pending",
            "progress": 0,
            "message": "任务已创建，等待处理",
            "created_at": datetime.now().isoformat(),
            "report_path": None
        }

        # 启动后台处理任务
        if background_tasks:
            background_tasks.add_task(process_task, task_id, file_path)

        return {
            "code": 200,
            "message": "文件上传成功",
            "data": {
                "task_id": task_id,
                "filename": file.filename,
                "status": "pending"
            }
        }

    except Exception as e:
        logger.error(f"文件上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")


@router.post("/requirement/evaluate")
async def evaluate_requirement(
    request: EvaluateRequest,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """
    DevOps系统调用的评估接口

    Args:
        request: 评估请求
        file: 需求文档文件
        background_tasks: 后台任务

    Returns:
        Dict: 任务信息
    """
    try:
        logger.info(f"接收到DevOps评估请求: {request.request_id}")

        # 生成任务ID
        task_id = request.request_id or str(uuid.uuid4())

        # 保存文件
        upload_dir = settings.UPLOAD_DIR
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, f"{task_id}_{file.filename}")

        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # 创建任务记录
        task_storage[task_id] = {
            "task_id": task_id,
            "filename": file.filename,
            "file_path": file_path,
            "status": "pending",
            "progress": 0,
            "message": "任务已创建",
            "created_at": datetime.now().isoformat(),
            "callback_url": request.callback_url,
            "report_path": None
        }

        # 启动后台处理
        if background_tasks:
            background_tasks.add_task(process_task_with_callback, task_id, file_path, request.callback_url)

        return {
            "code": 200,
            "message": "评估任务已创建",
            "data": {
                "task_id": task_id,
                "status": "pending"
            }
        }

    except Exception as e:
        logger.error(f"创建评估任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建评估任务失败: {str(e)}")


@router.get("/requirement/tasks")
async def get_all_tasks():
    """
    获取所有任务列表

    Returns:
        Dict: 所有任务列表
    """
    tasks_list = list(task_storage.values())
    # 按创建时间倒序排列
    tasks_list.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    return {
        "code": 200,
        "data": tasks_list,
        "total": len(tasks_list)
    }


@router.get("/requirement/status/{task_id}")
async def get_task_status(task_id: str):
    """
    获取任务状态

    Args:
        task_id: 任务ID

    Returns:
        Dict: 任务状态信息
    """
    if task_id not in task_storage:
        raise HTTPException(status_code=404, detail="任务不存在")

    task = task_storage[task_id]
    # 直接返回完整的任务信息，不使用TaskStatusResponse模型
    return {
        "code": 200,
        "data": {
            "task_id": task["task_id"],
            "status": task["status"],
            "progress": task["progress"],
            "message": task["message"],
            "report_path": task.get("report_path"),
            "error": task.get("error"),
            "filename": task.get("filename"),
            "created_at": task.get("created_at")
        }
    }


@router.get("/requirement/report/{task_id}")
async def download_report(task_id: str):
    """
    下载Excel报告

    Args:
        task_id: 任务ID

    Returns:
        FileResponse: Excel文件
    """
    if task_id not in task_storage:
        raise HTTPException(status_code=404, detail="任务不存在")

    task = task_storage[task_id]

    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail="任务未完成")

    if not task.get("report_path"):
        raise HTTPException(status_code=404, detail="报告文件不存在")

    report_path = task["report_path"]

    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="报告文件不存在")

    return FileResponse(
        path=report_path,
        filename=os.path.basename(report_path),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# 后台任务处理函数
def process_task_sync(task_id: str, file_path: str):
    """同步处理评估任务（在线程池中运行）"""
    try:
        # 更新任务状态
        task_storage[task_id]["status"] = "processing"
        task_storage[task_id]["progress"] = 10
        task_storage[task_id]["message"] = "正在解析文档..."

        # 定义进度更新函数
        def update_progress(progress: int, message: str):
            """更新任务进度"""
            if task_id in task_storage:
                task_storage[task_id]["progress"] = progress
                task_storage[task_id]["message"] = message
                logger.info(f"[任务 {task_id}] 进度: {progress}% - {message}")

        # 解析文档
        requirement_data = docx_parser.parse(file_path)

        # 提取文档文件名（不包含扩展名）作为需求名称
        original_filename = task_storage[task_id].get("filename", "")
        if original_filename:
            # 去掉.docx扩展名
            requirement_name = original_filename.rsplit(".", 1)[0] if "." in original_filename else original_filename
        else:
            # 如果没有文件名，使用文件路径的basename
            basename = os.path.basename(file_path)
            requirement_name = basename.rsplit(".", 1)[0] if "." in basename else basename

        # 使用文档文件名覆盖需求名称
        requirement_data["requirement_name"] = requirement_name
        logger.info(f"使用文档文件名作为需求名称: {requirement_name}")

        update_progress(15, "文档解析完成")

        # 处理需求评估（传递进度回调）
        report_path = agent_orchestrator.process_with_retry(
            task_id=task_id,
            requirement_data=requirement_data,
            max_retry=settings.TASK_RETRY_TIMES,
            progress_callback=update_progress
        )

        # 更新任务状态
        task_storage[task_id]["status"] = "completed"
        task_storage[task_id]["progress"] = 100
        task_storage[task_id]["message"] = "评估完成"
        task_storage[task_id]["report_path"] = report_path

        logger.info(f"任务 {task_id} 处理完成")

    except Exception as e:
        logger.error(f"任务 {task_id} 处理失败: {str(e)}")
        task_storage[task_id]["status"] = "failed"
        task_storage[task_id]["message"] = f"处理失败: {str(e)}"
        task_storage[task_id]["error"] = str(e)


async def process_task(task_id: str, file_path: str):
    """异步处理评估任务"""
    # 提交到线程池执行
    loop = None
    try:
        import asyncio
        loop = asyncio.get_event_loop()
    except RuntimeError:
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    await loop.run_in_executor(executor, process_task_sync, task_id, file_path)


async def process_task_with_callback(task_id: str, file_path: str, callback_url: str = None):
    """处理评估任务（带回调）"""
    # 先执行任务
    await process_task(task_id, file_path)

    # 如果有回调地址，发送回调通知
    if callback_url:
        try:
            import httpx
            task = task_storage[task_id]

            async with httpx.AsyncClient() as client:
                await client.post(
                    callback_url,
                    json={
                        "task_id": task_id,
                        "status": task["status"],
                        "report_path": task.get("report_path"),
                        "error": task.get("error")
                    },
                    timeout=10.0
                )
            logger.info(f"回调通知已发送: {callback_url}")

        except Exception as e:
            logger.warning(f"发送回调通知失败: {str(e)}")


@router.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION
    }
