"""
通知中心 API（文件存储版本）

对齐 requirements API-017：
- 通知仅允许用户访问自己的通知（notification.user_id == current_user.id）
- 支持分页列表 / 未读数 / 标记已读 / 全部已读 / 清理已读 / 删除单条
- 已读通知留存期默认90天（可配置），采用惰性清理落地“每日清理”语义

兼容性：
- create_notification 仍支持 roles/user_ids 作为收件人选择条件，但实际落盘为“按用户拆分”的单播通知记录。
"""

from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, Query

from backend.api.auth import get_current_user
from backend.config.config import settings
from backend.service import user_service

try:
    import fcntl

    FCNTL_AVAILABLE = True
except ImportError:
    FCNTL_AVAILABLE = False

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/notifications", tags=["消息通知"])

NOTIFY_STORE_PATH = os.path.join(settings.REPORT_DIR, "notifications.json")
NOTIFY_STORE_LOCK_PATH = f"{NOTIFY_STORE_PATH}.lock"
NOTIFY_META_PATH = os.path.join(settings.REPORT_DIR, "notifications_meta.json")

_notify_storage_lock = threading.RLock()


@contextmanager
def _notify_store_lock():
    if FCNTL_AVAILABLE:
        os.makedirs(os.path.dirname(NOTIFY_STORE_LOCK_PATH) or ".", exist_ok=True)
        with open(NOTIFY_STORE_LOCK_PATH, "a") as lock_file:
            fcntl.flock(lock_file, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file, fcntl.LOCK_UN)
    else:
        with _notify_storage_lock:
            yield


def _load_json(path: str, default: Any) -> Any:
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.warning("读取JSON失败: %s: %s", path, exc)
        return default


def _save_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)


def _load_notifications_unlocked() -> List[Dict[str, Any]]:
    data = _load_json(NOTIFY_STORE_PATH, default=[])
    return data if isinstance(data, list) else []


def _save_notifications_unlocked(items: List[Dict[str, Any]]) -> None:
    _save_json(NOTIFY_STORE_PATH, items)


def _load_meta_unlocked() -> Dict[str, Any]:
    data = _load_json(NOTIFY_META_PATH, default={})
    return data if isinstance(data, dict) else {}


def _save_meta_unlocked(meta: Dict[str, Any]) -> None:
    _save_json(NOTIFY_META_PATH, meta)


def _normalize_status(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in {"read", "1", "true", "yes"}:
        return "read"
    return "unread"


def _normalize_notification_item(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not isinstance(item, dict):
        return None

    notification_id = str(item.get("notification_id") or item.get("id") or "").strip()
    user_id = str(item.get("user_id") or "").strip()
    if not notification_id or not user_id:
        return None

    notify_type = str(item.get("type") or "system").strip()
    status = _normalize_status(item.get("status") or item.get("is_read"))
    payload = item.get("payload")
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        payload = {"raw": payload}

    # legacy fields: title/content
    title = str(item.get("title") or "").strip()
    content = str(item.get("content") or "").strip()
    if title and "title" not in payload:
        payload["title"] = title
    if content and "content" not in payload:
        payload["content"] = content

    created_at = str(item.get("created_at") or "").strip() or datetime.now().isoformat()
    normalized = {
        "notification_id": notification_id,
        "user_id": user_id,
        "type": notify_type,
        "status": status,
        "payload": payload,
        "created_at": created_at,
    }
    if status == "read":
        read_at = str(item.get("read_at") or item.get("readAt") or "").strip()
        if read_at:
            normalized["read_at"] = read_at
    return normalized


def _index_users() -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    users = user_service.list_users()
    mapping: Dict[str, str] = {}
    for user in users:
        if not isinstance(user, dict):
            continue
        uid = str(user.get("id") or "").strip()
        if not uid:
            continue
        mapping[uid] = uid
        username = str(user.get("username") or "").strip()
        if username:
            mapping[username] = uid
        display_name = str(user.get("display_name") or "").strip()
        if display_name:
            mapping[display_name] = uid
    return users, mapping


def _resolve_recipient_user_ids(
    *,
    roles: Optional[List[str]] = None,
    user_ids: Optional[List[str]] = None,
) -> List[str]:
    roles = roles or []
    user_ids = user_ids or []
    users, id_map = _index_users()

    resolved: List[str] = []

    for raw in user_ids:
        text = str(raw or "").strip()
        if not text:
            continue
        uid = id_map.get(text)
        if uid and uid not in resolved:
            resolved.append(uid)

    if roles:
        role_set = {str(role or "").strip() for role in roles if str(role or "").strip()}
        for user in users:
            user_roles = user.get("roles") if isinstance(user.get("roles"), list) else []
            if any(role in user_roles for role in role_set):
                uid = str(user.get("id") or "").strip()
                if uid and uid not in resolved:
                    resolved.append(uid)

    if not roles and not user_ids:
        # broadcast: all active users (best-effort; keep small scale)
        for user in users:
            if user.get("is_active") is False:
                continue
            uid = str(user.get("id") or "").strip()
            if uid and uid not in resolved:
                resolved.append(uid)

    return resolved


def _migrate_legacy_notifications(items: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], bool]:
    """
    Migrate legacy schema to per-user notification records.

    Legacy schema fields:
      - id/title/content/type/is_read/created_at/roles/user_ids
    """
    changed = False
    migrated: List[Dict[str, Any]] = []

    for item in items or []:
        if not isinstance(item, dict):
            changed = True
            continue

        normalized = _normalize_notification_item(item)
        if normalized:
            migrated.append(normalized)
            if item is not normalized:
                changed = True
            continue

        # legacy item
        legacy_type = str(item.get("type") or "system").strip()
        legacy_status = _normalize_status(item.get("is_read"))
        created_at = str(item.get("created_at") or "").strip() or datetime.now().isoformat()
        payload = item.get("payload")
        if payload is None:
            payload = {}
        if not isinstance(payload, dict):
            payload = {"raw": payload}
        title = str(item.get("title") or "").strip()
        content = str(item.get("content") or "").strip()
        if title:
            payload.setdefault("title", title)
        if content:
            payload.setdefault("content", content)

        recipients = _resolve_recipient_user_ids(
            roles=item.get("roles") if isinstance(item.get("roles"), list) else None,
            user_ids=item.get("user_ids") if isinstance(item.get("user_ids"), list) else None,
        )
        if not recipients:
            changed = True
            continue

        for uid in recipients:
            migrated.append(
                {
                    "notification_id": f"notice_{uuid.uuid4().hex}",
                    "user_id": uid,
                    "type": legacy_type,
                    "status": legacy_status,
                    "payload": payload,
                    "created_at": created_at,
                }
            )
        changed = True

    return migrated, changed


def _parse_iso_datetime(value: Any) -> Optional[datetime]:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except Exception:
        return None


def _cleanup_expired_read_notifications(items: List[Dict[str, Any]], *, retention_days: int) -> int:
    retention_days = int(retention_days or 0)
    if retention_days <= 0:
        return 0

    threshold = datetime.now() - timedelta(days=retention_days)
    before = len(items)

    retained = []
    for item in items:
        status = _normalize_status(item.get("status") or item.get("is_read"))
        if status != "read":
            retained.append(item)
            continue
        created_at = _parse_iso_datetime(item.get("created_at"))
        if created_at is None:
            retained.append(item)
            continue
        if created_at >= threshold:
            retained.append(item)
            continue

    items[:] = retained
    return before - len(items)


def _get_retention_days() -> int:
    try:
        value = int(os.getenv("NOTIFICATION_RETENTION_DAYS", "90"))
    except Exception:
        value = 90
    return max(1, min(value, 3650))


def _maybe_daily_cleanup(items: List[Dict[str, Any]], meta: Dict[str, Any]) -> None:
    today = datetime.now().date().isoformat()
    last_cleanup = str((meta or {}).get("last_cleanup_at") or "").strip()
    if last_cleanup == today:
        return
    removed = _cleanup_expired_read_notifications(items, retention_days=_get_retention_days())
    meta["last_cleanup_at"] = today
    if removed:
        meta["last_cleanup_removed"] = int(meta.get("last_cleanup_removed") or 0) + removed


@contextmanager
def _notify_storage_context(*, cleanup: bool = True):
    with _notify_store_lock():
        items = _load_notifications_unlocked()
        meta = _load_meta_unlocked()

        items, migrated = _migrate_legacy_notifications(items)
        if migrated:
            # drop per-process meta to ensure we re-run cleanup after migration
            meta.pop("last_cleanup_at", None)

        if cleanup:
            _maybe_daily_cleanup(items, meta)

        yield items

        _save_notifications_unlocked(items)
        _save_meta_unlocked(meta)


def _to_api_item(item: Dict[str, Any]) -> Dict[str, Any]:
    payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
    notification_id = str(item.get("notification_id") or "")
    status = _normalize_status(item.get("status"))
    title = str(payload.get("title") or "")
    content = str(payload.get("content") or "")
    return {
        "notification_id": notification_id,
        "id": notification_id,
        "type": str(item.get("type") or "system"),
        "status": status,
        "is_read": status == "read",
        "title": title,
        "content": content,
        "payload": payload,
        "created_at": str(item.get("created_at") or ""),
    }


@router.get("")
async def list_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    current_user_id = str(current_user.get("id") or "").strip()
    with _notify_storage_context() as items:
        mine = [item for item in items if str(item.get("user_id") or "").strip() == current_user_id]
        mine.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)

        total = len(mine)
        start = (page - 1) * page_size
        end = start + page_size
        paged = mine[start:end]

    api_items = [_to_api_item(item) for item in paged]

    return {
        "items": api_items,
        "data": api_items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/unread-count")
async def unread_count(current_user: Dict[str, Any] = Depends(get_current_user)):
    current_user_id = str(current_user.get("id") or "").strip()
    with _notify_storage_context() as items:
        count = sum(
            1
            for item in items
            if str(item.get("user_id") or "").strip() == current_user_id
            and _normalize_status(item.get("status")) == "unread"
        )
    return {
        "unread_count": count,
        "data": {"unread": count},
    }


@router.put("/{notification_id}/read")
async def mark_read(notification_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    current_user_id = str(current_user.get("id") or "").strip()
    normalized_id = str(notification_id or "").strip()
    if not normalized_id:
        return {"message": "success"}

    with _notify_storage_context() as items:
        now = datetime.now().isoformat()
        for item in items:
            if str(item.get("notification_id") or "").strip() != normalized_id:
                continue
            if str(item.get("user_id") or "").strip() != current_user_id:
                continue
            if _normalize_status(item.get("status")) != "read":
                item["status"] = "read"
                item["read_at"] = now
            break

    return {"message": "success"}


@router.put("/read-all")
async def mark_all_read(current_user: Dict[str, Any] = Depends(get_current_user)):
    current_user_id = str(current_user.get("id") or "").strip()
    with _notify_storage_context() as items:
        now = datetime.now().isoformat()
        for item in items:
            if str(item.get("user_id") or "").strip() != current_user_id:
                continue
            if _normalize_status(item.get("status")) == "unread":
                item["status"] = "read"
                item["read_at"] = now
    return {"message": "success"}


@router.delete("/clear-read")
async def clear_read(current_user: Dict[str, Any] = Depends(get_current_user)):
    current_user_id = str(current_user.get("id") or "").strip()
    with _notify_storage_context() as items:
        items[:] = [
            item
            for item in items
            if not (
                str(item.get("user_id") or "").strip() == current_user_id
                and _normalize_status(item.get("status")) == "read"
            )
        ]
    return {"message": "success"}


@router.delete("/{notification_id}")
async def delete_notification(notification_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    current_user_id = str(current_user.get("id") or "").strip()
    normalized_id = str(notification_id or "").strip()
    if not normalized_id:
        return {"message": "success"}

    with _notify_storage_context() as items:
        items[:] = [
            item
            for item in items
            if not (
                str(item.get("user_id") or "").strip() == current_user_id
                and str(item.get("notification_id") or "").strip() == normalized_id
            )
        ]
    return {"message": "success"}


def create_notification(
    title: str,
    content: str,
    notify_type: str = "system",
    roles: Optional[List[str]] = None,
    user_ids: Optional[List[str]] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> Any:
    """
    内部使用：创建通知（落盘为按用户拆分的单播记录）。

    - roles: 目标角色列表（会展开为所有匹配用户）
    - user_ids: 目标用户标识列表（允许 user.id/username/display_name 混用）
    - payload: 可选载荷（将合并 title/content）
    """
    recipients = _resolve_recipient_user_ids(roles=roles, user_ids=user_ids)
    if not recipients:
        return {}

    now = datetime.now().isoformat()
    base_payload: Dict[str, Any] = {}
    if isinstance(payload, dict):
        base_payload.update(payload)
    if title and "title" not in base_payload:
        base_payload["title"] = title
    if content and "content" not in base_payload:
        base_payload["content"] = content

    created_items = []
    with _notify_storage_context(cleanup=True) as items:
        for uid in recipients:
            record = {
                "notification_id": f"notice_{uuid.uuid4().hex}",
                "user_id": uid,
                "type": str(notify_type or "system").strip(),
                "status": "unread",
                "payload": dict(base_payload),
                "created_at": now,
            }
            items.append(record)
            created_items.append(record)

    if len(created_items) == 1:
        return created_items[0]
    return created_items
