"""
个人中心API（简易文件存储）
"""
import json
import logging
import os
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.config.config import settings
from backend.api.auth import get_current_user
from backend.api import routes as task_routes
from backend.service import user_service

try:
    import fcntl
    FCNTL_AVAILABLE = True
except ImportError:
    FCNTL_AVAILABLE = False

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/profile", tags=["个人中心"])

ACTIVITY_STORE_PATH = os.path.join(settings.REPORT_DIR, "activity_logs.json")
ACTIVITY_STORE_LOCK_PATH = f"{ACTIVITY_STORE_PATH}.lock"
_activity_lock = threading.RLock()
AVATAR_DIR = os.path.join(settings.UPLOAD_DIR, "avatars")

ALLOWED_AVATAR_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}
CONTENT_TYPE_EXTENSION_MAP = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/gif": "gif",
    "image/webp": "webp",
}


@contextmanager
def _activity_store_lock():
    if FCNTL_AVAILABLE:
        os.makedirs(os.path.dirname(ACTIVITY_STORE_LOCK_PATH), exist_ok=True)
        with open(ACTIVITY_STORE_LOCK_PATH, "a") as lock_file:
            fcntl.flock(lock_file, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file, fcntl.LOCK_UN)
    else:
        with _activity_lock:
            yield


def _load_activities_unlocked() -> List[Dict[str, Any]]:
    if not os.path.exists(ACTIVITY_STORE_PATH):
        return []
    try:
        with open(ACTIVITY_STORE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        logger.warning(f"读取操作记录失败: {e}")
        return []


def _save_activities_unlocked(items: List[Dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(ACTIVITY_STORE_PATH), exist_ok=True)
    tmp_path = f"{ACTIVITY_STORE_PATH}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, ACTIVITY_STORE_PATH)


@contextmanager
def _activity_context():
    with _activity_store_lock():
        items = _load_activities_unlocked()
        yield items
        _save_activities_unlocked(items)


def record_activity(user: Dict[str, Any], action: str, detail: str = "") -> None:
    try:
        item = {
            "id": f"act_{uuid.uuid4().hex[:10]}",
            "user_id": user.get("id"),
            "username": user.get("username"),
            "display_name": user.get("display_name"),
            "action": action,
            "detail": detail,
            "created_at": datetime.now().isoformat()
        }
        with _activity_context() as items:
            items.append(item)
    except Exception as e:
        logger.warning(f"记录操作日志失败: {e}")


def build_avatar_url(avatar_value: Optional[str]) -> Optional[str]:
    if not avatar_value:
        return None
    if avatar_value.startswith("http://") or avatar_value.startswith("https://"):
        return avatar_value
    if avatar_value.startswith("/"):
        return avatar_value
    return f"{settings.API_PREFIX}/profile/avatar/{avatar_value}"


def _resolve_avatar_extension(upload: UploadFile) -> str:
    filename = upload.filename or ""
    ext = os.path.splitext(filename)[1].lower().lstrip(".")
    if ext in ALLOWED_AVATAR_EXTENSIONS:
        return ext
    content_type = (upload.content_type or "").lower()
    mapped = CONTENT_TYPE_EXTENSION_MAP.get(content_type)
    return mapped or ""


def _build_task_summary(task: Dict[str, Any], current_user: Dict[str, Any]) -> Dict[str, Any]:
    task_routes._ensure_task_schema(task)
    active_assignments = task_routes._get_active_assignments(task)
    round_no = task.get("current_round", 1)
    round_key = task_routes._get_round_key(round_no)
    submitted = sum(
        1 for assignment in active_assignments
        if assignment.get("round_submissions", {}).get(round_key)
    )

    my_invite_token = None
    if "expert" in current_user.get("roles", []):
        for assignment in active_assignments:
            if task_routes._assignment_matches_user(assignment, current_user):
                my_invite_token = assignment.get("invite_token")
                break

    return {
        "id": task.get("task_id"),
        "name": task.get("name"),
        "status": task.get("workflow_status"),
        "aiStatus": task.get("ai_status") or task.get("status"),
        "progress": task.get("progress"),
        "message": task.get("message"),
        "currentRound": task.get("current_round"),
        "maxRounds": task.get("max_rounds"),
        "creatorName": task.get("creator_name"),
        "createdAt": task.get("created_at"),
        "systems": task.get("systems", []),
        "evaluationProgress": {
            "submitted": submitted,
            "total": len(active_assignments)
        },
        "reportVersions": task.get("report_versions", []),
        "myInviteToken": my_invite_token
    }


class ProfileUpdateRequest(BaseModel):
    display_name: str = Field(..., alias="displayName")
    email: str | None = None
    phone: str | None = None
    department: str | None = None

    model_config = {"populate_by_name": True}


@router.get("")
async def get_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    return {
        "code": 200,
        "data": {
            "id": current_user.get("id"),
            "username": current_user.get("username"),
            "displayName": current_user.get("display_name"),
            "email": current_user.get("email"),
            "phone": current_user.get("phone"),
            "department": current_user.get("department"),
            "avatar": build_avatar_url(current_user.get("avatar")),
            "roles": current_user.get("roles", []),
            "lastLoginAt": current_user.get("last_login_at")
        }
    }


@router.put("")
async def update_profile(request: ProfileUpdateRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    with user_service.user_storage_context() as users:
        user = user_service.find_user_by_id(users, current_user.get("id"))
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        user["display_name"] = request.display_name
        if request.email is not None:
            user["email"] = request.email
        if request.phone is not None:
            user["phone"] = request.phone
        if request.department is not None:
            user["department"] = request.department
    record_activity(current_user, "update_profile", "更新个人资料")
    return {"code": 200, "message": "success"}


@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    ext = _resolve_avatar_extension(file)
    if not ext:
        raise HTTPException(status_code=400, detail="仅支持jpg/png/gif/webp格式图片")

    os.makedirs(AVATAR_DIR, exist_ok=True)
    avatar_name = f"{current_user.get('id')}_{uuid.uuid4().hex[:8]}.{ext}"
    avatar_path = os.path.join(AVATAR_DIR, avatar_name)

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="头像内容为空")

    with open(avatar_path, "wb") as f:
        f.write(content)

    old_avatar = None
    with user_service.user_storage_context() as users:
        user = user_service.find_user_by_id(users, current_user.get("id"))
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        old_avatar = user.get("avatar")
        user["avatar"] = avatar_name

    if old_avatar:
        old_name = os.path.basename(old_avatar)
        old_path = os.path.join(AVATAR_DIR, old_name)
        if os.path.exists(old_path) and old_path != avatar_path:
            try:
                os.remove(old_path)
            except OSError:
                logger.warning("清理旧头像失败", exc_info=True)

    record_activity(current_user, "upload_avatar", "更新头像")
    return {"code": 200, "data": {"avatar": build_avatar_url(avatar_name)}}


@router.get("/avatar/{avatar_name}")
async def get_avatar(avatar_name: str):
    safe_name = os.path.basename(avatar_name)
    if safe_name != avatar_name:
        raise HTTPException(status_code=400, detail="非法文件名")
    avatar_path = os.path.join(AVATAR_DIR, safe_name)
    if not os.path.exists(avatar_path):
        raise HTTPException(status_code=404, detail="头像不存在")
    return FileResponse(path=avatar_path, filename=safe_name)


@router.get("/activity-logs")
async def get_activity_logs(current_user: Dict[str, Any] = Depends(get_current_user)):
    with _activity_context() as items:
        filtered = [item for item in items if item.get("user_id") == current_user.get("id")]
        filtered.sort(key=lambda item: item.get("created_at", ""), reverse=True)
    return {
        "code": 200,
        "data": {
            "total": len(filtered),
            "items": filtered[:200]
        }
    }


@router.get("/my-tasks")
async def get_my_tasks(current_user: Dict[str, Any] = Depends(get_current_user)):
    if "manager" not in current_user.get("roles", []):
        raise HTTPException(status_code=403, detail="无权访问我的任务")

    with task_routes._task_storage_context() as data:
        task_routes._cleanup_tasks(data)
        tasks = list(data.values())

    result = []
    for task in tasks:
        task_routes._ensure_task_schema(task)
        creator_id = task.get("creator_id")
        creator_name = task.get("creator_name")
        if creator_id != current_user.get("id") and creator_name not in {
            current_user.get("display_name"),
            current_user.get("username")
        }:
            continue
        result.append(_build_task_summary(task, current_user))

    result.sort(key=lambda item: item.get("createdAt", ""), reverse=True)
    return {"code": 200, "data": result, "total": len(result)}


@router.get("/my-evaluations")
async def get_my_evaluations(current_user: Dict[str, Any] = Depends(get_current_user)):
    if "expert" not in current_user.get("roles", []):
        raise HTTPException(status_code=403, detail="无权访问我的评估")

    with task_routes._task_storage_context() as data:
        task_routes._cleanup_tasks(data)
        tasks = list(data.values())

    result = []
    for task in tasks:
        task_routes._ensure_task_schema(task)
        matched = False
        for assignment in task_routes._get_active_assignments(task):
            if task_routes._assignment_matches_user(assignment, current_user):
                matched = True
                break
        if not matched:
            continue
        result.append(_build_task_summary(task, current_user))

    result.sort(key=lambda item: item.get("createdAt", ""), reverse=True)
    return {"code": 200, "data": result, "total": len(result)}
