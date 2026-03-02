#!/usr/bin/env python3
"""
初始化内网部署默认账号到 data/users.json。
"""
import argparse
import hashlib
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


INTERNAL_DEFAULT_USERS = (
    {"username": "admin", "roles": ["admin"]},
    {"username": "manager", "roles": ["manager"]},
    {"username": "expert1", "roles": ["expert"]},
    {"username": "expert2", "roles": ["expert"]},
    {"username": "expert3", "roles": ["expert"]},
)

ROLE_MAP = {
    "管理员": "admin",
    "项目经理": "manager",
    "专家": "expert",
    "admin": "admin",
    "manager": "manager",
    "expert": "expert",
}


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _normalize_roles(raw_roles: Any) -> List[str]:
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


def _create_user_record(username: str, roles: List[str]) -> Dict[str, Any]:
    return {
        "id": f"user_{uuid.uuid4().hex}",
        "username": username,
        "display_name": username,
        "password_hash": _hash_password(username),
        "roles": roles,
        "email": None,
        "phone": None,
        "department": None,
        "avatar": None,
        "expertise": [],
        "on_duty": True,
        "is_active": True,
        "created_at": datetime.now().isoformat(),
        "last_login_at": None,
    }


def _load_users(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    return data if isinstance(data, list) else []


def _save_users(path: Path, users: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(users, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(path)


def _is_missing_pydantic_settings(exc: ModuleNotFoundError) -> bool:
    if exc.name == "pydantic_settings":
        return True
    return "pydantic_settings" in str(exc)


def _init_users_with_backend_service(users_path: Path, preserve_password: bool) -> Optional[Dict[str, int]]:
    try:
        from backend.service import user_service
    except ModuleNotFoundError as exc:
        if _is_missing_pydantic_settings(exc):
            return None
        raise

    user_service.USER_STORE_PATH = str(users_path)
    user_service.USER_STORE_LOCK_PATH = f"{users_path}.lock"
    return user_service.ensure_internal_default_users(force_reset_password=not preserve_password)


def _init_users_fallback(users_path: Path, preserve_password: bool) -> Dict[str, int]:
    users = _load_users(users_path)
    created = 0
    updated = 0

    existing_by_username: Dict[str, Dict[str, Any]] = {}
    for item in users:
        if not isinstance(item, dict):
            continue
        username = str(item.get("username") or "").strip()
        if username and username not in existing_by_username:
            existing_by_username[username] = item

    for default_user in INTERNAL_DEFAULT_USERS:
        username = default_user["username"]
        expected_roles = list(default_user["roles"])
        expected_password_hash = _hash_password(username)
        existing_user = existing_by_username.get(username)

        if existing_user is None:
            users.append(_create_user_record(username, expected_roles))
            created += 1
            continue

        changed = False
        if not preserve_password and existing_user.get("password_hash") != expected_password_hash:
            existing_user["password_hash"] = expected_password_hash
            changed = True

        if _normalize_roles(existing_user.get("roles")) != expected_roles:
            existing_user["roles"] = expected_roles
            changed = True

        if not str(existing_user.get("display_name") or "").strip():
            existing_user["display_name"] = username
            changed = True

        if existing_user.get("is_active") is not True:
            existing_user["is_active"] = True
            changed = True

        if existing_user.get("on_duty") is not True:
            existing_user["on_duty"] = True
            changed = True

        if changed:
            updated += 1

    _save_users(users_path, users)
    return {"created": created, "updated": updated, "total_defaults": len(INTERNAL_DEFAULT_USERS)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize internal default users.")
    parser.add_argument(
        "--data-dir",
        default=str(ROOT_DIR / "data"),
        help="Directory that contains users.json (default: ./data)",
    )
    parser.add_argument(
        "--preserve-password",
        action="store_true",
        help="Do not reset existing default users password to username.",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir).resolve()
    data_dir.mkdir(parents=True, exist_ok=True)

    users_path = data_dir / "users.json"
    summary = _init_users_with_backend_service(users_path, args.preserve_password)
    if summary is None:
        summary = _init_users_fallback(users_path, args.preserve_password)
    print(
        "internal users initialized: "
        f"file={users_path}, created={summary['created']}, updated={summary['updated']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
