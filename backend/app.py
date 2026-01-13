"""
FastAPI主程序
业务需求工作量评估系统
"""
import logging
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.config.config import settings
from backend.api.routes import router
from backend.api.subsystem_routes import router as subsystem_router
from backend.api.cosmic_routes import router as cosmic_router
from backend.api.system_routes import router as system_router

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

# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="基于Agent智能体的业务需求工作量评估系统"
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
app.include_router(subsystem_router)
app.include_router(cosmic_router)
app.include_router(system_router)

# 创建必要的目录
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.REPORT_DIR, exist_ok=True)
os.makedirs("logs", exist_ok=True)

# 静态文件服务（用于前端）
# app.mount("/", StaticFiles(directory="../frontend/build", html=True), name="static")


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info("=" * 60)
    logger.info(f"{settings.APP_NAME} 启动中...")
    logger.info(f"版本: {settings.APP_VERSION}")
    logger.info(f"调试模式: {settings.DEBUG}")
    logger.info(f"监听地址: {settings.HOST}:{settings.PORT}")
    logger.info(f"API前缀: {settings.API_PREFIX}")
    logger.info(f"工作进程数: {settings.WORKERS}")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info(f"{settings.APP_NAME} 正在关闭...")


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
