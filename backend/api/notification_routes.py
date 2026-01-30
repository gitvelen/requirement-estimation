"""
通知管理API（文件存储版本）
"""
import json
import logging
import os
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Depends

from backend.config.config import settings
from backend.api.auth import get_current_user

try:
    import fcntl
    FCNTL_AVAILABLE = True
except ImportError:
    FCNTL_AVAILABLE = False

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/notifications", tags=["通知管理"])

NOTIFY_STORE_PATH = os.path.join(settings.REPORT_DIR, "notifications.json")
NOTIFY_STORE_LOCK_PATH = f"{NOTIFY_STORE_PATH}.lock"
notify_storage_lock = threading.RLock()


@contextmanager
def _notify_store_lock():
    if FCNTL_AVAILABLE:
        os.makedirs(os.path.dirname(NOTIFY_STORE_LOCK_PATH), exist_ok=True)
        with open(NOTIFY_STORE_LOCK_PATH, "a") as lock_file:
            fcntl.flock(lock_file, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file, fcntl.LOCK_UN)
    else:
        with notify_storage_lock:
            yield


def _load_notifications_unlocked() -> List[Dict[str, Any]]:
    if not os.path.exists(NOTIFY_STORE_PATH):
        return []
    try:
        with open(NOTIFY_STORE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        logger.warning(f"读取通知存储失败: {e}")
        return []


def _save_notifications_unlocked(items: List[Dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(NOTIFY_STORE_PATH), exist_ok=True)
    tmp_path = f"{NOTIFY_STORE_PATH}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, NOTIFY_STORE_PATH)


@contextmanager
def _notify_storage_context():
    with _notify_store_lock():
        items = _load_notifications_unlocked()
        yield items
        _save_notifications_unlocked(items)


@router.get("")
async def list_notifications(current_user: Dict[str, Any] = Depends(get_current_user)):
    with _notify_storage_context() as items:
        filtered = [item for item in items if _match_notice(item, current_user)]
        items_sorted = sorted(filtered, key=lambda item: item.get("created_at", ""), reverse=True)
    return {"code": 200, "data": items_sorted}


@router.get("/unread-count")
async def unread_count(current_user: Dict[str, Any] = Depends(get_current_user)):
    with _notify_storage_context() as items:
        count = sum(1 for item in items if _match_notice(item, current_user) and not item.get("is_read"))
    return {"code": 200, "data": {"unread": count}}


@router.put("/{notify_id}/read")
async def mark_read(notify_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    with _notify_storage_context() as items:
        target = next((item for item in items if item.get("id") == notify_id and _match_notice(item, current_user)), None)
        if not target:
            raise HTTPException(status_code=404, detail="通知不存在")
        target["is_read"] = True
        target["read_at"] = datetime.now().isoformat()
    return {"code": 200, "message": "success"}


@router.put("/read-all")
async def mark_all_read(current_user: Dict[str, Any] = Depends(get_current_user)):
    with _notify_storage_context() as items:
        now = datetime.now().isoformat()
        for item in items:
            if _match_notice(item, current_user) and not item.get("is_read"):
                item["is_read"] = True
                item["read_at"] = now
    return {"code": 200, "message": "success"}


@router.delete("/clear-read")
async def clear_read(current_user: Dict[str, Any] = Depends(get_current_user)):
    with _notify_storage_context() as items:
        items[:] = [item for item in items if not (_match_notice(item, current_user) and item.get("is_read"))]
    return {"code": 200, "message": "success"}


@router.delete("/{notify_id}")
async def delete_notification(notify_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    with _notify_storage_context() as items:
        target = next((item for item in items if item.get("id") == notify_id and _match_notice(item, current_user)), None)
        if not target:
            raise HTTPException(status_code=404, detail="通知不存在")
        items.remove(target)
    return {"code": 200, "message": "success"}

def _user_identifiers(user: Dict[str, Any]) -> set:
    return {user.get("id"), user.get("username"), user.get("display_name")}


def _match_notice(notice: Dict[str, Any], user: Dict[str, Any]) -> bool:
    roles = notice.get("roles") or []
    user_ids = notice.get("user_ids") or []
    if roles or user_ids:
        if roles and any(role in (user.get("roles") or []) for role in roles):
            return True
        if user_ids:
            identifiers = _user_identifiers(user)
            if any(item in identifiers for item in user_ids):
                return True
        return False
    return True


def create_notification(
    title: str,
    content: str,
    notify_type: str = "system",
    roles: Optional[List[str]] = None,
    user_ids: Optional[List[str]] = None
) -> Dict[str, Any]:
    """内部使用：创建通知（非API）"""
    notice = {
        "id": f"notice_{uuid.uuid4().hex}",
        "title": title,
        "content": content,
        "type": notify_type,
        "is_read": False,
        "created_at": datetime.now().isoformat()
    }
    if roles:
        notice["roles"] = roles
    if user_ids:
        notice["user_ids"] = user_ids
    with _notify_storage_context() as items:
        items.append(notice)
    return notice
