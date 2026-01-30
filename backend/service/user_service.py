"""
用户管理服务（文件存储版本）
"""
import json
import logging
import os
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from backend.config.config import settings

try:
    import fcntl
    FCNTL_AVAILABLE = True
except ImportError:
    FCNTL_AVAILABLE = False

logger = logging.getLogger(__name__)

USER_STORE_PATH = os.path.join(settings.REPORT_DIR, "users.json")
USER_STORE_LOCK_PATH = f"{USER_STORE_PATH}.lock"
_user_storage_lock = threading.RLock()

ROLE_MAP = {
    "管理员": "admin",
    "项目经理": "manager",
    "专家": "expert",
    "admin": "admin",
    "manager": "manager",
    "expert": "expert",
}


@contextmanager
def _user_store_lock():
    if FCNTL_AVAILABLE:
        os.makedirs(os.path.dirname(USER_STORE_LOCK_PATH), exist_ok=True)
        with open(USER_STORE_LOCK_PATH, "a") as lock_file:
            fcntl.flock(lock_file, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file, fcntl.LOCK_UN)
    else:
        with _user_storage_lock:
            yield


def _load_users_unlocked() -> List[Dict[str, Any]]:
    if not os.path.exists(USER_STORE_PATH):
        return []
    try:
        with open(USER_STORE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        logger.warning(f"读取用户存储失败: {e}")
        return []


def _save_users_unlocked(users: List[Dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(USER_STORE_PATH), exist_ok=True)
    tmp_path = f"{USER_STORE_PATH}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, USER_STORE_PATH)


@contextmanager
def user_storage_context():
    with _user_store_lock():
        users = _load_users_unlocked()
        yield users
        _save_users_unlocked(users)


def hash_password(password: str) -> str:
    import hashlib
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == password_hash


def normalize_roles(raw_roles: Any) -> List[str]:
    if raw_roles is None:
        return []
    if isinstance(raw_roles, list):
        values = raw_roles
    else:
        values = [item.strip() for item in str(raw_roles).replace("，", ",").split(",") if item.strip()]
    result = []
    for role in values:
        mapped = ROLE_MAP.get(role, role)
        if mapped not in result:
            result.append(mapped)
    return result


def normalize_expertise(raw: Any) -> List[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [item for item in raw if item]
    parts = [item.strip() for item in str(raw).replace("，", ",").split(",") if item.strip()]
    return parts


def list_users() -> List[Dict[str, Any]]:
    with user_storage_context() as users:
        return sorted(users, key=lambda item: item.get("created_at", ""), reverse=True)


def find_user_by_id(users: List[Dict[str, Any]], user_id: str) -> Optional[Dict[str, Any]]:
    for user in users:
        if user.get("id") == user_id:
            return user
    return None


def find_user_by_username(users: List[Dict[str, Any]], username: str) -> Optional[Dict[str, Any]]:
    for user in users:
        if user.get("username") == username:
            return user
    return None


def create_user_record(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": data.get("id") or f"user_{uuid.uuid4().hex}",
        "username": data["username"],
        "display_name": data.get("display_name") or data.get("displayName") or data["username"],
        "password_hash": data.get("password_hash") or hash_password(data.get("password", "")),
        "roles": normalize_roles(data.get("roles")),
        "email": data.get("email"),
        "phone": data.get("phone"),
        "department": data.get("department"),
        "avatar": data.get("avatar"),
        "expertise": normalize_expertise(data.get("expertise")),
        "on_duty": bool(data.get("on_duty", True)),
        "is_active": bool(data.get("is_active", True)),
        "created_at": data.get("created_at") or datetime.now().isoformat(),
        "last_login_at": data.get("last_login_at"),
    }


def update_user_record(user: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
    if data.get("display_name") is not None:
        user["display_name"] = data["display_name"]
    if data.get("password"):
        user["password_hash"] = hash_password(data["password"])
    if data.get("roles") is not None:
        user["roles"] = normalize_roles(data.get("roles"))
    if data.get("email") is not None:
        user["email"] = data["email"]
    if data.get("phone") is not None:
        user["phone"] = data["phone"]
    if data.get("department") is not None:
        user["department"] = data["department"]
    if data.get("avatar") is not None:
        user["avatar"] = data["avatar"]
    if data.get("expertise") is not None:
        user["expertise"] = normalize_expertise(data.get("expertise"))
    if data.get("on_duty") is not None:
        user["on_duty"] = bool(data.get("on_duty"))
    if data.get("is_active") is not None:
        user["is_active"] = bool(data.get("is_active"))
    return user


def record_login(user: Dict[str, Any]) -> None:
    user["last_login_at"] = datetime.now().isoformat()
