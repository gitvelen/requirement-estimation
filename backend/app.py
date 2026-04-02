"""
FastAPI主程序
业务需求工作量评估系统
"""
import logging
import sys
import os
from contextlib import asynccontextmanager

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from backend.config.config import settings
from backend.api.routes import router
from backend.api.cosmic_routes import router as cosmic_router
from backend.api.system_routes import router as system_router
from backend.api.knowledge_routes import router as knowledge_router
from backend.api.evidence_routes import router as evidence_router
from backend.api.evidence_level_routes import router as evidence_level_router
from backend.api.user_routes import router as user_router
from backend.api.notification_routes import router as notification_router
from backend.api.report_routes import router as report_router
from backend.api.auth_routes import router as auth_router
from backend.api.profile_routes import router as profile_router
from backend.api.department_routes import router as department_router
from backend.api.system_list_routes import router as system_list_router
from backend.api.system_profile_routes import (
    compat_router as system_profile_compat_router,
    router as system_profile_router,
    ws_router as system_profile_ws_router,
)
from backend.api.code_scan_routes import router as code_scan_router
from backend.api.esb_routes import router as esb_router
from backend.api.error_utils import ApiError, build_error_payload
from backend.utils.pdf_report import get_font_info
from backend.service.metadata_governance_service import get_metadata_governance_service

# 配置日志
handlers = [logging.StreamHandler()]

# 尝试添加文件处理器，如果失败则只使用控制台输出
try:
    import os
    os.makedirs('logs', exist_ok=True)
    file_handler = logging.FileHandler('logs/app.log', encoding='utf-8')
    handlers.append(file_handler)
except (PermissionError, OSError) as e:
    # 忽略文件日志错误，继续使用控制台输出
    pass

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=handlers
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def app_lifespan(_: FastAPI):
    """应用生命周期事件"""
    logger.info("=" * 60)
    logger.info(f"{settings.APP_NAME} 启动中...")
    logger.info(f"版本: {settings.APP_VERSION}")
    logger.info(f"调试模式: {settings.DEBUG}")
    logger.info(f"监听地址: {settings.HOST}:{settings.PORT}")
    logger.info(f"API前缀: {settings.API_PREFIX}")
    logger.info(f"工作进程数: {settings.WORKERS}")
    font_info = get_font_info()
    if font_info.get("reportlab_available"):
        font_path = font_info.get("font_path") or font_info.get("source")
        logger.info(f"PDF字体: {font_info.get('font_name')} ({font_path})")
    else:
        logger.info("PDF字体: reportlab 未安装，使用最小PDF模式")
    logger.info("=" * 60)
    try:
        get_metadata_governance_service().bootstrap_scheduler_from_config()
    except Exception:
        logger.warning("元数据治理定时任务恢复失败", exc_info=True)
    yield
    logger.info(f"{settings.APP_NAME} 正在关闭...")


# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="基于Agent智能体的业务需求工作量评估系统",
    lifespan=app_lifespan,
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(router)
app.include_router(cosmic_router)
app.include_router(system_router)
app.include_router(knowledge_router)
app.include_router(evidence_router)
app.include_router(evidence_level_router)
app.include_router(user_router)
app.include_router(notification_router)
app.include_router(report_router)
app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(department_router)
app.include_router(system_list_router)
app.include_router(system_profile_router)
app.include_router(system_profile_compat_router)
app.include_router(system_profile_ws_router)
app.include_router(code_scan_router)
app.include_router(esb_router)


@app.exception_handler(ApiError)
async def api_error_exception_handler(request: Request, exc: ApiError):
    payload = build_error_payload(
        request=request,
        error_code=exc.error_code,
        message=exc.message,
        details=exc.details,
    )
    return JSONResponse(status_code=exc.status_code, content=payload)

# 创建必要的目录
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.REPORT_DIR, exist_ok=True)
os.makedirs("logs", exist_ok=True)

# 静态文件服务（用于前端）
# app.mount("/", StaticFiles(directory="../frontend/build", html=True), name="static")
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host=settings.HOST,
        port=settings.PORT,
        workers=settings.WORKERS if not settings.DEBUG else 1,
        reload=settings.DEBUG,
        log_level="info"
    )
