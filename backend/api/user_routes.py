"""
用户管理API（文件存储版本）
提供用户的增删改查与批量导入功能
"""
import logging
import uuid
import os
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from openpyxl import load_workbook

from backend.api.auth import require_admin_api_key
from backend.config.config import settings
from backend.service import user_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/users", tags=["用户管理"])

USER_TEMPLATE_PATH = os.path.join(settings.REPORT_DIR, "templates", "user_import_template.xlsx")


class UserCreateRequest(BaseModel):
    username: str
    display_name: str = Field(..., alias="displayName")
    password: str
    roles: List[str]
    email: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None
    expertise: Optional[List[str]] = None
    on_duty: bool = Field(True, alias="onDuty")
    is_active: bool = Field(True, alias="isActive")

    model_config = {"populate_by_name": True}


class UserUpdateRequest(BaseModel):
    display_name: Optional[str] = Field(None, alias="displayName")
    password: Optional[str] = None
    roles: Optional[List[str]] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None
    expertise: Optional[List[str]] = None
    on_duty: Optional[bool] = Field(None, alias="onDuty")
    is_active: Optional[bool] = Field(None, alias="isActive")

    model_config = {"populate_by_name": True}


class UserStatusRequest(BaseModel):
    is_active: bool = Field(..., alias="isActive")

    model_config = {"populate_by_name": True}


class BatchConfirmRequest(BaseModel):
    users: List[Dict[str, Any]]


@router.get("", dependencies=[Depends(require_admin_api_key)])
async def list_users():
    return {"code": 200, "data": user_service.list_users()}


@router.get("/template", dependencies=[Depends(require_admin_api_key)])
async def download_user_template():
    if not os.path.exists(USER_TEMPLATE_PATH):
        raise HTTPException(status_code=404, detail="模板文件不存在")
    return FileResponse(
        path=USER_TEMPLATE_PATH,
        filename=os.path.basename(USER_TEMPLATE_PATH),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@router.post("", dependencies=[Depends(require_admin_api_key)])
async def create_user(request: UserCreateRequest):
    with user_service.user_storage_context() as users:
        if user_service.find_user_by_username(users, request.username):
            raise HTTPException(status_code=400, detail="用户名已存在")

        pwd_err = user_service.validate_password_strength(request.password)
        if pwd_err:
            raise HTTPException(status_code=400, detail=pwd_err)

        user = user_service.create_user_record({
            "username": request.username,
            "display_name": request.display_name,
            "password": request.password,
            "roles": request.roles,
            "email": request.email,
            "phone": request.phone,
            "department": request.department,
            "expertise": request.expertise,
            "on_duty": request.on_duty,
            "is_active": request.is_active,
        })
        users.append(user)

    return {"code": 200, "message": "success", "data": user}


@router.put("/{user_id}", dependencies=[Depends(require_admin_api_key)])
async def update_user(user_id: str, request: UserUpdateRequest):
    with user_service.user_storage_context() as users:
        user = user_service.find_user_by_id(users, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")

        if request.password:
            pwd_err = user_service.validate_password_strength(request.password)
            if pwd_err:
                raise HTTPException(status_code=400, detail=pwd_err)

        user_service.update_user_record(user, {
            "display_name": request.display_name,
            "password": request.password,
            "roles": request.roles,
            "email": request.email,
            "phone": request.phone,
            "department": request.department,
            "expertise": request.expertise,
            "on_duty": request.on_duty,
            "is_active": request.is_active,
        })

    return {"code": 200, "message": "success", "data": user}


@router.put("/{user_id}/status", dependencies=[Depends(require_admin_api_key)])
async def update_user_status(user_id: str, request: UserStatusRequest):
    with user_service.user_storage_context() as users:
        user = user_service.find_user_by_id(users, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        user["is_active"] = request.is_active
    return {"code": 200, "message": "success", "data": user}


@router.delete("/{user_id}", dependencies=[Depends(require_admin_api_key)])
async def delete_user(user_id: str):
    with user_service.user_storage_context() as users:
        user = user_service.find_user_by_id(users, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        users.remove(user)
    return {"code": 200, "message": "success"}


def _parse_excel(file_bytes: bytes) -> List[Dict[str, Any]]:
    wb = load_workbook(filename=BytesIO(file_bytes), data_only=True)
    ws = wb.active
    rows = list(ws.rows)
    if not rows:
        return []

    headers = [str(cell.value).strip() if cell.value is not None else "" for cell in rows[0]]
    header_map = {header: idx for idx, header in enumerate(headers)}

    def get_value(row, key, default=""):
        idx = header_map.get(key)
        if idx is None:
            return default
        value = row[idx].value if idx < len(row) else default
        return str(value).strip() if value is not None else default

    expertise_headers = [h for h in headers if h.startswith("专长领域")]

    results = []
    usernames = set()
    for row in rows[1:]:
        username = get_value(row, "用户名")
        display_name = get_value(row, "姓名")
        password = get_value(row, "密码")
        email = get_value(row, "邮箱")
        phone = get_value(row, "手机")
        department = get_value(row, "所属部门")
        role_raw = get_value(row, "角色")
        expertise_values = []
        for header in expertise_headers:
            value = get_value(row, header)
            if value:
                expertise_values.append(value)

        errors = []
        if not username:
            errors.append("用户名不能为空")
        if not display_name:
            errors.append("姓名不能为空")
        if not password:
            errors.append("密码不能为空")
        if username in usernames:
            errors.append("用户名重复")
        usernames.add(username)

        results.append({
            "username": username,
            "display_name": display_name,
            "password": password,
            "roles": user_service.normalize_roles(role_raw),
            "email": email,
            "phone": phone,
            "department": department,
            "expertise": expertise_values,
            "errors": errors
        })

    return results


@router.post("/batch-import", dependencies=[Depends(require_admin_api_key)])
async def batch_import_preview(file: UploadFile = File(...)):
    try:
        content = await file.read()
        rows = _parse_excel(content)
        return {
            "code": 200,
            "data": {
                "total": len(rows),
                "rows": rows
            }
        }
    except Exception as e:
        logger.error(f"批量导入解析失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"批量导入解析失败: {str(e)}")


@router.post("/batch-import/confirm", dependencies=[Depends(require_admin_api_key)])
async def batch_import_confirm(payload: BatchConfirmRequest):
    success = 0
    failed = 0
    errors = []

    with user_service.user_storage_context() as users:
        existing_usernames = {user.get("username") for user in users}

        for row in payload.users:
            username = (row.get("username") or "").strip()
            display_name = (row.get("display_name") or row.get("displayName") or "").strip()
            password = (row.get("password") or "").strip()

            row_errors = list(row.get("errors", []))
            if not username:
                row_errors.append("用户名不能为空")
            if not display_name:
                row_errors.append("姓名不能为空")
            if not password:
                row_errors.append("密码不能为空")
            if username in existing_usernames:
                row_errors.append("用户名已存在")

            if row_errors:
                failed += 1
                errors.append({"username": username or "-", "errors": row_errors})
                continue

            user = {
                "id": f"user_{uuid.uuid4().hex}",
                "username": username,
                "display_name": display_name,
                "password_hash": user_service.hash_password(password),
                "roles": user_service.normalize_roles(row.get("roles")),
                "email": row.get("email"),
                "phone": row.get("phone"),
                "department": row.get("department"),
                "expertise": user_service.normalize_expertise(row.get("expertise")),
                "on_duty": True,
                "is_active": True,
                "created_at": datetime.now().isoformat(),
            }
            users.append(user)
            existing_usernames.add(username)
            success += 1

    return {
        "code": 200,
        "data": {
            "success": success,
            "failed": failed,
            "errors": errors
        }
    }
