"""
API路由
定义所有RESTful API接口
"""
import os
import re
import uuid
import logging
import socket
import threading
import ipaddress
from urllib.parse import urlparse
from datetime import datetime
from typing import Dict, Any
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from backend.utils.docx_parser import docx_parser
from backend.agent.agent_orchestrator import get_agent_orchestrator
from backend.config.config import settings

# 尝试导入 python-magic（用于文件类型检测）
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
    logger.warning("python-magic 未安装，将跳过MIME类型检测")

# 创建线程池用于异步任务处理
executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="task_worker")

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix=settings.API_PREFIX, tags=["需求评估"])

# 全局任务存储（生产环境应使用Redis或数据库）
task_storage = {}
task_storage_lock = threading.RLock()


def _sanitize_filename(filename: str, default_name: str = "upload.docx") -> str:
    """将上传文件名清洗为安全的本地文件名"""
    if not filename:
        return default_name

    cleaned = os.path.basename(filename.replace("\\", "/")).strip().replace("\x00", "")
    name, ext = os.path.splitext(cleaned)
    if ext.lower() != ".docx":
        ext = ".docx"
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    if not name:
        name = "upload"
    return f"{name}{ext}"


def _is_internal_callback_url(callback_url: str) -> bool:
    """仅允许内网/本机地址，防止SSRF"""
    try:
        parsed = urlparse(callback_url)
        if parsed.scheme not in ("http", "https"):
            return False
        if not parsed.hostname:
            return False

        host = parsed.hostname
        try:
            ip = ipaddress.ip_address(host)
            return ip.is_private or ip.is_loopback or ip.is_link_local
        except ValueError:
            pass

        try:
            addrs = socket.getaddrinfo(host, None)
        except OSError:
            return False

        has_addr = False
        for family, _, _, _, sockaddr in addrs:
            if family == socket.AF_INET:
                addr = sockaddr[0]
            elif family == socket.AF_INET6:
                addr = sockaddr[0]
            else:
                continue
            has_addr = True
            ip = ipaddress.ip_address(addr)
            if not (ip.is_private or ip.is_loopback or ip.is_link_local):
                return False
        return has_addr
    except Exception:
        return False


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

        # 验证文件名后缀
        if not file.filename or not file.filename.endswith(".docx"):
            raise HTTPException(status_code=400, detail="仅支持.docx格式文件")

        # 读取文件内容
        content = await file.read()

        # 验证文件大小
        if len(content) > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"文件过大，最大允许{settings.MAX_FILE_SIZE // (1024*1024)}MB"
            )

        # 验证文件内容类型（MIME type）
        if MAGIC_AVAILABLE:
            try:
                mime_type = magic.from_buffer(content, mime=True)
                if mime_type != "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                    raise HTTPException(
                        status_code=400,
                        detail=f"无效的文件类型: {mime_type}，仅支持.docx文件"
                    )
            except Exception as e:
                logger.warning(f"MIME类型检测失败: {e}，继续处理")
        else:
            logger.info("跳过MIME类型检测（python-magic未安装）")

        # 生成任务ID
        task_id = str(uuid.uuid4())

        # 保存文件
        upload_dir = settings.UPLOAD_DIR
        os.makedirs(upload_dir, exist_ok=True)
        safe_filename = _sanitize_filename(file.filename)
        file_path = os.path.join(upload_dir, f"{task_id}_{safe_filename}")

        with open(file_path, "wb") as buffer:
            buffer.write(content)

        logger.info(f"文件已保存: {file_path}")

        # 创建任务记录
        task_storage[task_id] = {
            "task_id": task_id,
            "filename": safe_filename,
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
    request_id: str = Form(...),
    callback_url: str = Form(None),
    priority: int = Form(0),
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """
    DevOps系统调用的评估接口

    Args:
        request_id: 请求ID
        callback_url: 回调通知地址
        priority: 优先级
        file: 需求文档文件
        background_tasks: 后台任务

    Returns:
        Dict: 任务信息
    """
    try:
        logger.info(f"接收到DevOps评估请求: {request_id}")

        if callback_url and not _is_internal_callback_url(callback_url):
            raise HTTPException(status_code=400, detail="回调地址必须为内网或本机地址")

        # 验证文件名后缀
        if not file.filename or not file.filename.endswith(".docx"):
            raise HTTPException(status_code=400, detail="仅支持.docx格式文件")

        # 读取文件内容
        content = await file.read()

        # 验证文件大小
        if len(content) > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"文件过大，最大允许{settings.MAX_FILE_SIZE // (1024*1024)}MB"
            )

        # 验证文件内容类型（MIME type）
        if MAGIC_AVAILABLE:
            try:
                mime_type = magic.from_buffer(content, mime=True)
                if mime_type != "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                    raise HTTPException(
                        status_code=400,
                        detail=f"无效的文件类型: {mime_type}，仅支持.docx文件"
                    )
            except Exception as e:
                logger.warning(f"MIME类型检测失败: {e}，继续处理")
        else:
            logger.info("跳过MIME类型检测（python-magic未安装）")

        # 生成任务ID
        task_id = request_id or str(uuid.uuid4())

        # 保存文件
        upload_dir = settings.UPLOAD_DIR
        os.makedirs(upload_dir, exist_ok=True)
        safe_filename = _sanitize_filename(file.filename)
        file_path = os.path.join(upload_dir, f"{task_id}_{safe_filename}")

        with open(file_path, "wb") as buffer:
            buffer.write(content)

        # 创建任务记录
        task_storage[task_id] = {
            "task_id": task_id,
            "filename": safe_filename,
            "file_path": file_path,
            "status": "pending",
            "progress": 0,
            "message": "任务已创建",
            "created_at": datetime.now().isoformat(),
            "callback_url": callback_url,
            "report_path": None
        }

        # 启动后台处理
        if background_tasks:
            background_tasks.add_task(process_task_with_callback, task_id, file_path, callback_url)

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

    # 防止路径遍历攻击
    real_report_dir = os.path.realpath(settings.REPORT_DIR)
    real_report_path = os.path.realpath(report_path)

    # 验证路径在允许的目录内
    if not real_report_path.startswith(real_report_dir):
        logger.error(f"路径遍历攻击检测: {report_path}")
        raise HTTPException(status_code=403, detail="非法访问")

    if not os.path.exists(real_report_path):
        raise HTTPException(status_code=404, detail="报告文件不存在")

    return FileResponse(
        path=real_report_path,
        filename=os.path.basename(real_report_path),
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

        # 获取Agent编排器（支持知识库注入）
        orchestrator = get_agent_orchestrator()

        # 处理需求评估（传递进度回调）
        report_path, systems_data = orchestrator.process_with_retry(
            task_id=task_id,
            requirement_data=requirement_data,
            max_retry=settings.TASK_RETRY_TIMES,
            progress_callback=update_progress
        )

        # 【新增】保存systems_data到task_storage，用于人机协作修正
        task_storage[task_id]["systems_data"] = systems_data
        task_storage[task_id]["modifications"] = []  # 初始化为空列表
        task_storage[task_id]["confirmed"] = False  # 初始状态为未确认

        # 更新任务状态
        task_storage[task_id]["status"] = "completed"
        task_storage[task_id]["progress"] = 100
        task_storage[task_id]["message"] = "评估完成"
        task_storage[task_id]["report_path"] = report_path

        logger.info(f"任务 {task_id} 处理完成，系统数: {len(systems_data)}，功能点总数: {sum(len(v) for v in systems_data.values())}")

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
        if not _is_internal_callback_url(callback_url):
            logger.warning(f"回调地址不符合内网策略，已跳过: {callback_url}")
            return
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
                    timeout=httpx.Timeout(120.0, connect=10.0)  # 总超时120秒，连接超时10秒
                )
            logger.info(f"回调通知已发送: {callback_url}")

        except Exception as e:
            logger.warning(f"发送回调通知失败: {str(e)}")


# ==================== 人机协作修正API ====================

class FeatureUpdateRequest(BaseModel):
    """功能点更新请求"""
    system: str  # 系统名称
    operation: str  # add, update, delete
    feature_index: int = None  # 功能点索引（update/delete时需要）
    feature_data: dict = None  # 功能点数据（add/update时需要）


@router.get("/requirement/result/{task_id}")
async def get_evaluation_result(task_id: str):
    """
    获取AI评估结果（包含systems_data）

    Args:
        task_id: 任务ID

    Returns:
        Dict: 评估结果数据
    """
    if task_id not in task_storage:
        raise HTTPException(status_code=404, detail="任务不存在")

    task = task_storage[task_id]

    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"任务未完成，当前状态: {task['status']}")

    # 如果没有systems_data，尝试向后兼容（从Excel解析）
    systems_data = task.get("systems_data")
    if systems_data is None:
        raise HTTPException(status_code=400, detail="该任务没有可编辑的评估数据（可能是旧版本任务）")

    return {
        "code": 200,
        "data": {
            "task_id": task_id,
            "systems_data": systems_data,
            "modifications": task.get("modifications", []),
            "confirmed": task.get("confirmed", False)
        }
    }


@router.put("/requirement/features/{task_id}")
async def update_features(task_id: str, request: FeatureUpdateRequest):
    """
    批量更新功能点

    支持操作：
    - add: 添加新功能点
    - update: 修改现有功能点
    - delete: 删除功能点

    Args:
        task_id: 任务ID
        request: 更新请求

    Returns:
        Dict: 更新结果
    """
    if task_id not in task_storage:
        raise HTTPException(status_code=404, detail="任务不存在")

    task = task_storage[task_id]

    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail="只能修改已完成的任务")

    if task.get("confirmed", False):
        raise HTTPException(status_code=400, detail="该任务已确认，不能修改")

    systems_data = task.get("systems_data", {})
    modifications = task.get("modifications", [])

    if request.system not in systems_data:
        raise HTTPException(status_code=400, detail=f"系统 '{request.system}' 不存在")

    try:
        mod = {
            "id": f"mod_{uuid.uuid4().hex[:8]}",
            "timestamp": datetime.now().isoformat(),
            "operation": request.operation,
            "system": request.system
        }

        if request.operation == "update":
            # 修改功能点
            if request.feature_index is None:
                raise HTTPException(status_code=400, detail="update操作需要feature_index")

            features = systems_data[request.system]
            if request.feature_index < 0 or request.feature_index >= len(features):
                raise HTTPException(status_code=400, detail="feature_index超出范围")

            old_feature = features[request.feature_index]
            if request.feature_data is None:
                raise HTTPException(status_code=400, detail="update操作需要feature_data")

            # 记录修改
            for key, new_value in request.feature_data.items():
                old_value = old_feature.get(key)
                if old_value != new_value:
                    mod["field"] = key
                    mod["old_value"] = old_value
                    mod["new_value"] = new_value
                    # 应用修改
                    old_feature[key] = new_value

            logger.info(f"[任务 {task_id}] 更新功能点: 系统={request.system}, 索引={request.feature_index}")

        elif request.operation == "delete":
            # 删除功能点
            if request.feature_index is None:
                raise HTTPException(status_code=400, detail="delete操作需要feature_index")

            features = systems_data[request.system]
            if request.feature_index < 0 or request.feature_index >= len(features):
                raise HTTPException(status_code=400, detail="feature_index超出范围")

            deleted_feature = features.pop(request.feature_index)
            mod["deleted_feature"] = deleted_feature

            logger.info(f"[任务 {task_id}] 删除功能点: 系统={request.system}, 索引={request.feature_index}")

        elif request.operation == "add":
            # 添加新功能点
            if request.feature_data is None:
                raise HTTPException(status_code=400, detail="add操作需要feature_data")

            features = systems_data[request.system]
            new_feature = request.feature_data

            # 设置默认值
            if "序号" not in new_feature:
                new_feature["序号"] = f"{len(features)+1}.1"
            if "预估人天" not in new_feature:
                new_feature["预估人天"] = 2.5
            if "复杂度" not in new_feature:
                new_feature["复杂度"] = "中"

            features.append(new_feature)
            mod["added_feature"] = new_feature

            logger.info(f"[任务 {task_id}] 添加功能点: 系统={request.system}")

        else:
            raise HTTPException(status_code=400, detail=f"不支持的操作: {request.operation}")

        # 保存修改记录
        modifications.append(mod)
        task["modifications"] = modifications

        # 持久化到JSON（实现数据闭环）
        _save_modifications_to_json(task_id, modifications)

        return {
            "code": 200,
            "message": "更新成功",
            "data": {
                "modification_id": mod["id"],
                "updated_systems_data": systems_data
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新功能点失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新功能点失败: {str(e)}")


@router.post("/requirement/confirm/{task_id}")
async def confirm_evaluation(task_id: str):
    """
    确认评估结果，生成最终报告

    流程：
    1. 标记任务为confirmed
    2. 使用最新的systems_data重新生成Excel
    3. 更新report_path
    4. 如果有回调URL，发送完成通知

    Args:
        task_id: 任务ID

    Returns:
        Dict: 确认结果
    """
    if task_id not in task_storage:
        raise HTTPException(status_code=404, detail="任务不存在")

    task = task_storage[task_id]

    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail="任务未完成")

    if task.get("confirmed", False):
        raise HTTPException(status_code=400, detail="该任务已经确认过了")

    try:
        # 获取最新的systems_data
        systems_data = task.get("systems_data", {})
        if not systems_data:
            raise HTTPException(status_code=400, detail="没有可确认的评估数据")

        # 生成新的Excel报告（包含修正记录）
        from backend.utils.excel_generator import excel_generator
        from backend.agent.work_estimation_agent import work_estimation_agent

        # 获取专家评分数据
        expert_estimates = work_estimation_agent.get_expert_estimates_for_excel()

        # 生成新的报告文件名（加上final标记）
        import os
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        requirement_name = task.get("requirement_name", task_id)
        filename = f"{task_id}_{requirement_name[:20]}_final_{timestamp}.xlsx"
        file_path = os.path.join(settings.REPORT_DIR, filename)

        # 生成报告
        report_path = excel_generator.generate_report(
            task_id=task_id,
            requirement_name=requirement_name,
            systems_data=systems_data,
            expert_estimates=expert_estimates,
            output_path=file_path
        )

        # 更新任务状态
        task["confirmed"] = True
        task["confirmed_at"] = datetime.now().isoformat()
        task["report_path"] = report_path
        task["message"] = "评估完成并已确认"

        logger.info(f"[任务 {task_id}] 已确认，最终报告: {report_path}")

        return {
            "code": 200,
            "message": "确认成功",
            "data": {
                "report_path": file_path,
                "confirmed_at": task["confirmed_at"]
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"确认评估失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"确认评估失败: {str(e)}")


@router.get("/requirement/modifications/{task_id}")
async def get_modifications(task_id: str):
    """
    获取修正历史记录

    Args:
        task_id: 任务ID

    Returns:
        Dict: 修正历史
    """
    if task_id not in task_storage:
        raise HTTPException(status_code=404, detail="任务不存在")

    modifications = task_storage[task_id].get("modifications", [])

    return {
        "code": 200,
        "data": {
            "task_id": task_id,
            "total": len(modifications),
            "modifications": modifications
        }
    }


def _save_modifications_to_json(task_id: str, modifications: list):
    """
    持久化修正记录到JSON文件

    Args:
        task_id: 任务ID
        modifications: 修改记录列表
    """
    try:
        import json
        import os

        # 确保data目录存在
        os.makedirs("data", exist_ok=True)

        # 保存到JSON文件
        json_file = os.path.join("data", "task_modifications.json")

        # 读取现有数据
        existing_data = {}
        if os.path.exists(json_file):
            with open(json_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)

        # 更新数据
        existing_data[task_id] = {
            "task_id": task_id,
            "modifications": modifications,
            "updated_at": datetime.now().isoformat()
        }

        # 写入文件
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=2)

        logger.info(f"修正记录已保存到 {json_file}")

    except Exception as e:
        logger.error(f"保存修正记录失败: {str(e)}")


@router.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION
    }
