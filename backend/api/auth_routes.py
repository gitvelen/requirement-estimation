"""
认证接口
"""
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from backend.api.auth import create_access_token, get_current_user
from backend.api.profile_routes import record_activity, build_avatar_url
from backend.service import user_service

router = APIRouter(prefix="/api/v1/auth", tags=["认证"])


class LoginRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    oldPassword: str
    newPassword: str


@router.post("/login")
async def login(request: LoginRequest):
    with user_service.user_storage_context() as users:
        user = user_service.find_user_by_username(users, request.username)
        if not user:
            raise HTTPException(status_code=401, detail="用户名或密码错误")
        if not user.get("is_active"):
            raise HTTPException(status_code=403, detail="账号已禁用")
        if not user_service.verify_password(request.password, user.get("password_hash", "")):
            raise HTTPException(status_code=401, detail="用户名或密码错误")

        user_service.record_login(user)
        record_activity(user, "login", "登录成功")

    token = create_access_token({
        "user_id": user.get("id"),
        "username": user.get("username"),
        "roles": user.get("roles", []),
    })

    return {
        "code": 200,
        "message": "success",
        "data": {
            "token": token,
            "user": {
                "id": user.get("id"),
                "username": user.get("username"),
                "displayName": user.get("display_name"),
                "roles": user.get("roles", []),
                "avatar": build_avatar_url(user.get("avatar")),
            }
        }
    }


@router.get("/me")
async def me(current_user: Dict[str, Any] = Depends(get_current_user)):
    return {
        "code": 200,
        "data": {
            "id": current_user.get("id"),
            "username": current_user.get("username"),
            "displayName": current_user.get("display_name"),
            "roles": current_user.get("roles", []),
            "avatar": build_avatar_url(current_user.get("avatar")),
        }
    }


@router.post("/change-password")
async def change_password(request: ChangePasswordRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    with user_service.user_storage_context() as users:
        user = user_service.find_user_by_id(users, current_user.get("id"))
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        if not user_service.verify_password(request.oldPassword, user.get("password_hash", "")):
            raise HTTPException(status_code=400, detail="旧密码不正确")
        pwd_err = user_service.validate_password_strength(request.newPassword)
        if pwd_err:
            raise HTTPException(status_code=400, detail=pwd_err)
        user["password_hash"] = user_service.hash_password(request.newPassword)
    record_activity(current_user, "change_password", "修改密码")
    return {"code": 200, "message": "success"}
