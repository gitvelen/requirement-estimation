import os
import sys

import pytest
from fastapi.testclient import TestClient

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.app import app
from backend.api import system_routes
from backend.config.config import settings
from backend.service import system_profile_service
from backend.service import user_service


@pytest.fixture()
def client(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(settings, "REPORT_DIR", str(data_dir))
    monkeypatch.setattr(user_service, "USER_STORE_PATH", str(data_dir / "users.json"))
    monkeypatch.setattr(user_service, "USER_STORE_LOCK_PATH", str(data_dir / "users.json.lock"))
    monkeypatch.setattr(system_routes, "CSV_PATH", str(tmp_path / "system_list.csv"))

    system_profile_service._system_profile_service = None

    return TestClient(app)


def _seed_user(username: str, password: str, roles):
    user = user_service.create_user_record(
        {
            "username": username,
            "display_name": username,
            "password": password,
            "roles": roles,
        }
    )
    with user_service.user_storage_context() as users:
        users.append(user)
    return user


def _login(client: TestClient, username: str, password: str) -> str:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["data"]["token"]


def _seed_system(owner_id: str, system_id: str = "sys_hop", system_name: str = "HOP"):
    system_routes._write_systems(
        [
            {
                "id": system_id,
                "name": system_name,
                "abbreviation": system_name,
                "status": "运行中",
                "extra": {"owner_id": owner_id},
            }
        ]
    )


def test_system_profile_v21_only_four_fields(client, monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", False)

    owner = _seed_user("manager_v21_fields", "pwd123", ["manager"])
    _seed_system(owner["id"])
    token = _login(client, "manager_v21_fields", "pwd123")

    response = client.put(
        "/api/v1/system-profiles/HOP",
        json={
            "system_id": "sys_hop",
            "fields": {
                "system_scope": "账户系统",
                "module_structure": [{"module_name": "账户", "functions": [{"name": "开户"}]}],
                "integration_points": "核心账务",
                "key_constraints": "高可用",
                "in_scope": "legacy",
                "core_functions": "legacy",
            },
            "evidence_refs": [],
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    fields = (response.json().get("data") or {}).get("fields") or {}
    assert set(fields.keys()) == {"system_scope", "module_structure", "integration_points", "key_constraints"}


def test_system_profile_module_structure_must_be_array(client, monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", False)

    owner = _seed_user("manager_v21_validation", "pwd123", ["manager"])
    _seed_system(owner["id"], system_id="sys_hop_2", system_name="HOP2")
    token = _login(client, "manager_v21_validation", "pwd123")

    response = client.put(
        "/api/v1/system-profiles/HOP2",
        json={
            "system_id": "sys_hop_2",
            "fields": {
                "system_scope": "账户系统",
                "module_structure": {"module_name": "账户", "functions": []},
            },
            "evidence_refs": [],
        },
        headers={"Authorization": f"Bearer {token}", "X-Request-ID": "req_invalid_module_structure"},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload.get("error_code") == "invalid_module_structure"
    assert payload.get("request_id") == "req_invalid_module_structure"


def test_system_profile_admin_has_global_write_permission(client, monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", False)

    owner = _seed_user("owner_for_admin_v21", "pwd123", ["manager"])
    admin = _seed_user("admin_v21_writer", "pwd123", ["admin"])
    _seed_system(owner["id"], system_id="sys_hop_3", system_name="HOP3")
    token = _login(client, "admin_v21_writer", "pwd123")

    response = client.put(
        "/api/v1/system-profiles/HOP3",
        json={
            "system_id": "sys_hop_3",
            "fields": {"system_scope": "admin修改"},
            "evidence_refs": [],
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload.get("code") == 200
    assert payload.get("data", {}).get("system_name") == "HOP3"


def test_system_profile_unknown_system_returns_system_not_found(client, monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", False)

    manager = _seed_user("manager_unknown_v21", "pwd123", ["manager"])
    token = _login(client, "manager_unknown_v21", "pwd123")

    response = client.put(
        "/api/v1/system-profiles/UNKNOWN",
        json={"fields": {"system_scope": "测试"}, "evidence_refs": []},
        headers={"Authorization": f"Bearer {token}", "X-Request-ID": "req_unknown_system"},
    )

    assert response.status_code == 404
    payload = response.json()
    assert payload.get("error_code") == "system_not_found"
    assert payload.get("request_id") == "req_unknown_system"

