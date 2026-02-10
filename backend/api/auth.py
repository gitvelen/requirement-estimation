"""
简单鉴权工具
生产环境通过 X-API-Key 保护敏感接口
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
import jwt
from fastapi import Header, HTTPException, Depends
from backend.config.config import settings
from backend.service import user_service

logger = logging.getLogger(__name__)


def require_admin_api_key(
    x_api_key: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None)
) -> None:
    """
    校验管理接口的 API Key。
    - DEBUG 模式下放行，便于本地调试
    - 非 DEBUG 模式下必须配置 ADMIN_API_KEY
    """
    if settings.DEBUG:
        return

    if authorization and authorization.startswith("Bearer "):
        try:
            token = authorization.split(" ", 1)[1].strip()
            payload = decode_access_token(token)
            user_id = payload.get("user_id")
            if user_id:
                users = user_service.list_users()
                user = next((item for item in users if item.get("id") == user_id), None)
                if user and user.get("is_active") and "admin" in user.get("roles", []):
                    return
        except HTTPException:
            pass

    if not settings.ADMIN_API_KEY:
        logger.error("ADMIN_API_KEY 未配置，拒绝访问管理接口")
        raise HTTPException(status_code=500, detail="ADMIN_API_KEY 未配置")

    if x_api_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="未授权访问")


def create_access_token(payload: Dict[str, Any]) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    data = {**payload, "exp": expire}
    return jwt.encode(data, settings.JWT_SECRET, algorithm="HS256")


def decode_access_token(token: str) -> Dict[str, Any]:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail="Token已过期") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="无效Token") from exc


def get_current_user(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="缺少Authorization")
    token = authorization.split(" ", 1)[1].strip()
    payload = decode_access_token(token)
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="无效Token")

    users = user_service.list_users()
    user = next((item for item in users if item.get("id") == user_id), None)
    if not user or not user.get("is_active"):
        raise HTTPException(status_code=401, detail="用户不存在或已停用")
    return user


def require_roles(roles: List[str]):
    def _checker(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_roles = current_user.get("roles", [])
        if not any(role in user_roles for role in roles):
            raise HTTPException(status_code=403, detail="权限不足")
        return current_user
    return _checker
