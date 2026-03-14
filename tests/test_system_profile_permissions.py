import os
import sys

import pytest
from fastapi.testclient import TestClient

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.app import app
from backend.config.config import settings
from backend.service import user_service
from backend.api import system_routes
from backend.service import system_profile_service


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


def test_system_profile_write_requires_owner(client, monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", False)

    owner = _seed_user("owner", "owner123", ["manager"])
    other = _seed_user("other", "other123", ["manager"])

    system_routes._write_systems(
        [
            {
                "id": "sys_hop",
                "name": "HOP",
                "abbreviation": "HOP",
                "status": "运行中",
                "extra": {"owner_id": owner["id"], "owner_name": "负责人"},
            }
        ]
    )

    owner_token = _login(client, "owner", "owner123")
    other_token = _login(client, "other", "other123")

    denied = client.put(
        "/api/v1/system-profiles/HOP",
        json={"fields": {"system_scope": "账户领域"}, "evidence_refs": []},
        headers={"Authorization": f"Bearer {other_token}", "X-Request-ID": "req_profile_denied"},
    )
    assert denied.status_code == 403
    denied_payload = denied.json()
    assert denied_payload.get("error_code") == "permission_denied"
    assert denied_payload.get("request_id") == "req_profile_denied"

    allowed = client.put(
        "/api/v1/system-profiles/HOP",
        json={"system_id": "sys_hop", "fields": {"system_scope": "账户领域"}, "evidence_refs": []},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert allowed.status_code == 200
    allowed_data = allowed.json().get("data", {})
    assert allowed_data.get("system_name") == "HOP"
    fields = allowed_data.get("fields") or {}
    assert set(fields.keys()) == {"system_scope", "module_structure", "integration_points", "key_constraints"}


def test_system_profile_write_rejects_missing_owner_config(client, monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", False)

    manager = _seed_user("manager", "manager123", ["manager"])
    token = _login(client, "manager", "manager123")

    system_routes._write_systems(
        [
            {
                "id": "sys_no_owner",
                "name": "NO_OWNER",
                "abbreviation": "NO",
                "status": "运行中",
                "extra": {},
            }
        ]
    )

    response = client.put(
        "/api/v1/system-profiles/NO_OWNER",
        json={"system_id": "sys_no_owner", "fields": {"system_scope": "测试范围"}, "evidence_refs": []},
        headers={"Authorization": f"Bearer {token}", "X-Request-ID": "req_profile_no_owner"},
    )

    assert response.status_code == 403
    payload = response.json()
    assert payload.get("error_code") == "permission_denied"
    assert payload.get("request_id") == "req_profile_no_owner"
    assert "未配置主责" in str(payload.get("details", {}).get("reason", ""))



def test_system_profile_admin_can_write(client, monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", False)

    owner = _seed_user("owner_admin_case", "owner123", ["manager"])
    admin = _seed_user("admin_admin_case", "admin123", ["admin"])

    system_routes._write_systems(
        [
            {
                "id": "sys_hop",
                "name": "HOP",
                "abbreviation": "HOP",
                "status": "运行中",
                "extra": {"owner_id": owner["id"]},
            }
        ]
    )

    admin_token = _login(client, "admin_admin_case", "admin123")

    response = client.put(
        "/api/v1/system-profiles/HOP",
        json={"system_id": "sys_hop", "fields": {"system_scope": "全局管理"}, "evidence_refs": []},
        headers={"Authorization": f"Bearer {admin_token}", "X-Request-ID": "req_profile_admin_write"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload.get("code") == 200
    assert payload.get("data", {}).get("system_name") == "HOP"


def test_system_profile_write_rejects_unknown_system(client, monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", False)

    manager = _seed_user("manager_unknown_system", "manager123", ["manager"])
    token = _login(client, "manager_unknown_system", "manager123")

    response = client.put(
        "/api/v1/system-profiles/UNKNOWN_SYSTEM",
        json={"fields": {"system_scope": "测试"}, "evidence_refs": []},
        headers={"Authorization": f"Bearer {token}", "X-Request-ID": "req_profile_unknown_system"},
    )

    assert response.status_code == 404
    payload = response.json()
    assert payload.get("error_code") == "system_not_found"
    assert payload.get("request_id") == "req_profile_unknown_system"


def test_system_profile_completeness_api_formula(client, monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", False)

    manager = _seed_user("manager_completeness", "manager123", ["manager"])
    token = _login(client, "manager_completeness", "manager123")

    system_routes._write_systems(
        [
            {
                "id": "sys_hop",
                "name": "HOP",
                "abbreviation": "HOP",
                "status": "运行中",
                "extra": {"owner_id": manager["id"]},
            }
        ]
    )

    service = system_profile_service.get_system_profile_service()
    service.upsert_profile(
        "HOP",
        {
            "system_id": "sys_hop",
            "fields": {"system_scope": "账户域", "module_structure": [{"module_name": "账户", "functions": [{"name": "开户"}]}]},
            "evidence_refs": [],
        },
        actor=manager,
    )
    service.mark_code_scan_ingested(
        system_name="HOP",
        system_id="sys_hop",
        job_id="scan_demo",
        result_path="/tmp/scan_demo.json",
        actor=manager,
    )
    service.mark_esb_ingested(
        system_name="HOP",
        system_id="sys_hop",
        import_id="esb_demo",
        source_file="esb.csv",
        actor=manager,
    )
    service.mark_document_imported(
        system_name="HOP",
        system_id="sys_hop",
        import_id="doc_demo",
        source_file="spec.txt",
        level="normal",
        actor=manager,
    )

    response = client.get(
        "/api/v1/system-profiles/completeness",
        params={"system_name": "HOP"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload.get("exists") is True
    assert payload.get("breakdown", {}).get("code_scan") == 30
    assert payload.get("breakdown", {}).get("documents") == 10
    assert payload.get("breakdown", {}).get("esb") == 30
    assert payload.get("completeness_score") == 70

    missing = client.get(
        "/api/v1/system-profiles/completeness",
        params={"system_name": "UNKNOWN_SYS"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert missing.status_code == 200
    missing_payload = missing.json()
    assert missing_payload.get("exists") is False
    assert missing_payload.get("completeness_score") == 0


def test_profile_template_download_requires_manager_role(client):
    manager = _seed_user("template_manager_acl", "pwd123", ["manager"])
    admin = _seed_user("template_admin_acl", "pwd123", ["admin"])
    manager_token = _login(client, "template_manager_acl", "pwd123")
    admin_token = _login(client, "template_admin_acl", "pwd123")

    manager_response = client.get(
        "/api/v1/system-profiles/template/history_report",
        headers={"Authorization": f"Bearer {manager_token}", "X-Request-ID": "req_template_removed_for_manager"},
    )
    assert manager_response.status_code == 400
    assert manager_response.json()["error_code"] == "TEMPLATE_TYPE_INVALID"
    assert manager_response.json()["request_id"] == "req_template_removed_for_manager"

    admin_response = client.get(
        "/api/v1/system-profiles/template/history_report",
        headers={"Authorization": f"Bearer {admin_token}", "X-Request-ID": "req_template_admin_forbidden"},
    )
    assert admin_response.status_code == 403

    no_auth = client.get("/api/v1/system-profiles/template/history_report")
    assert no_auth.status_code == 401


def test_profile_task_status_requires_manager_role(client):
    manager = _seed_user("task_manager_acl", "pwd123", ["manager"])
    admin = _seed_user("task_admin_acl", "pwd123", ["admin"])
    manager_token = _login(client, "task_manager_acl", "pwd123")
    admin_token = _login(client, "task_admin_acl", "pwd123")

    system_routes._write_systems(
        [
            {
                "id": "sys_hop",
                "name": "HOP",
                "abbreviation": "HOP",
                "status": "运行中",
                "extra": {"owner_id": manager["id"]},
            }
        ]
    )

    service = system_profile_service.get_system_profile_service()
    service.upsert_extraction_task(
        "sys_hop",
        task_id="task_acl_001",
        status="pending",
        trigger="document_import",
    )

    manager_response = client.get(
        "/api/v1/system-profiles/task-status/task_acl_001",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert manager_response.status_code == 200

    admin_response = client.get(
        "/api/v1/system-profiles/task-status/task_acl_001",
        headers={"Authorization": f"Bearer {admin_token}", "X-Request-ID": "req_task_admin_forbidden"},
    )
    assert admin_response.status_code == 403

    no_auth = client.get("/api/v1/system-profiles/task-status/task_acl_001")
    assert no_auth.status_code == 401
