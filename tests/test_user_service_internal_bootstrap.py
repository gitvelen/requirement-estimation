import json
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.service import user_service


def _read_users(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_ensure_internal_default_users_creates_required_accounts(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    users_path = data_dir / "users.json"
    monkeypatch.setattr(user_service, "USER_STORE_PATH", str(users_path))
    monkeypatch.setattr(user_service, "USER_STORE_LOCK_PATH", str(users_path) + ".lock")

    summary = user_service.ensure_internal_default_users()

    assert summary["created"] == 5
    assert summary["updated"] == 0

    users = _read_users(users_path)
    by_username = {item.get("username"): item for item in users}

    expected_roles = {
        "admin": ["admin"],
        "manager": ["manager"],
        "expert1": ["expert"],
        "expert2": ["expert"],
        "expert3": ["expert"],
    }

    for username, roles in expected_roles.items():
        assert username in by_username
        account = by_username[username]
        assert account.get("roles") == roles
        assert user_service.verify_password(username, account.get("password_hash", ""))
        assert account.get("is_active") is True
        assert account.get("on_duty") is True


def test_ensure_internal_default_users_updates_existing_accounts(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    users_path = data_dir / "users.json"
    monkeypatch.setattr(user_service, "USER_STORE_PATH", str(users_path))
    monkeypatch.setattr(user_service, "USER_STORE_LOCK_PATH", str(users_path) + ".lock")

    with user_service.user_storage_context() as users:
        users.append(
            user_service.create_user_record(
                {
                    "username": "admin",
                    "display_name": "管理员",
                    "password": "old_password",
                    "roles": ["viewer"],
                    "is_active": False,
                    "on_duty": False,
                }
            )
        )

    summary = user_service.ensure_internal_default_users()

    assert summary["created"] == 4
    assert summary["updated"] == 1

    users = _read_users(users_path)
    admin = next(item for item in users if item.get("username") == "admin")
    assert admin.get("roles") == ["admin"]
    assert user_service.verify_password("admin", admin.get("password_hash", ""))
    assert admin.get("is_active") is True
    assert admin.get("on_duty") is True
