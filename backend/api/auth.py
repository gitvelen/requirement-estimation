"""
简单鉴权工具
生产环境通过 X-API-Key 保护敏感接口
"""
import logging
from typing import Optional
from fastapi import Header, HTTPException
from backend.config.config import settings

logger = logging.getLogger(__name__)


def require_admin_api_key(x_api_key: Optional[str] = Header(None)) -> None:
    """
    校验管理接口的 API Key。
    - DEBUG 模式下放行，便于本地调试
    - 非 DEBUG 模式下必须配置 ADMIN_API_KEY
    """
    if settings.DEBUG:
        return

    if not settings.ADMIN_API_KEY:
        logger.error("ADMIN_API_KEY 未配置，拒绝访问管理接口")
        raise HTTPException(status_code=500, detail="ADMIN_API_KEY 未配置")

    if x_api_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="未授权访问")
