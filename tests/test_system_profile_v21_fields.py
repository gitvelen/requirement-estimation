import json
import os
import sys
import logging

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
from backend.service.system_profile_service import SystemProfileService


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
                "module_structure": [
                    {
                        "module_name": "账户",
                        "description": "账户核心域",
                        "children": [
                            {
                                "module_name": "开户子模块",
                                "description": "处理开户",
                                "children": [{"module_name": "开户校验", "description": "校验资料"}],
                            }
                        ],
                    }
                ],
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
    assert fields["module_structure"][0]["module_name"] == "账户"
    assert fields["module_structure"][0]["children"][0]["module_name"] == "开户子模块"
    assert fields["module_structure"][0]["children"][0]["children"][0]["module_name"] == "开户校验"
    assert "functions" not in fields["module_structure"][0]


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


def test_system_profile_legacy_functions_are_converted_to_children(client, monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", False)

    owner = _seed_user("manager_v21_legacy", "pwd123", ["manager"])
    _seed_system(owner["id"], system_id="sys_hop_legacy", system_name="HOP_LEGACY")
    token = _login(client, "manager_v21_legacy", "pwd123")

    response = client.put(
        "/api/v1/system-profiles/HOP_LEGACY",
        json={
            "system_id": "sys_hop_legacy",
            "fields": {
                "system_scope": "账户系统",
                "module_structure": [{"module_name": "账户", "functions": [{"name": "开户", "desc": "开户流程"}]}],
            },
            "evidence_refs": [],
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    fields = (response.json().get("data") or {}).get("fields") or {}
    modules = fields.get("module_structure") or []
    assert len(modules) == 1
    assert modules[0]["module_name"] == "账户"
    assert modules[0]["children"] == [{"module_name": "开户", "description": "开户流程", "children": []}]
    assert "functions" not in modules[0]


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


def test_system_profile_service_startup_migrates_legacy_fields_to_profile_data(tmp_path):
    store_path = tmp_path / "system_profiles.json"
    legacy_profile = {
        "system_id": "sys_hop",
        "system_name": "HOP",
        "status": "draft",
        "fields": {
            "system_scope": "账户系统",
            "module_structure": [{"module_name": "账户", "functions": [{"name": "开户"}]}],
            "integration_points": "核心账务",
            "key_constraints": "高可用",
        },
        "created_at": "2026-02-28T00:00:00",
    }
    store_path.write_text(json.dumps([legacy_profile], ensure_ascii=False), encoding="utf-8")

    service = SystemProfileService(store_path=str(store_path))
    migrated = service.get_profile("HOP")

    assert migrated is not None
    assert migrated.get("_migrated") is True
    assert isinstance(migrated.get("_migrated_at"), str) and migrated.get("_migrated_at")

    profile_data = migrated.get("profile_data") or {}
    assert set(profile_data.keys()) == {
        "system_positioning",
        "business_capabilities",
        "integration_interfaces",
        "technical_architecture",
        "constraints_risks",
    }
    assert profile_data["system_positioning"]["system_description"] == "账户系统"
    module_structure = profile_data["business_capabilities"]["module_structure"]
    assert isinstance(module_structure, list) and len(module_structure) == 1
    assert module_structure[0]["module_name"] == "账户"
    assert module_structure[0]["children"] == [{"module_name": "开户", "description": "", "children": []}]
    assert isinstance(module_structure[0].get("last_updated"), str) and module_structure[0]["last_updated"]
    assert profile_data["integration_interfaces"]["integration_points"] == [{"description": "核心账务"}]
    assert profile_data["constraints_risks"]["key_constraints"] == [{"category": "通用", "description": "高可用"}]

    fields = migrated.get("fields") or {}
    assert fields["system_scope"] == "账户系统"
    assert fields["integration_points"] == "核心账务"
    assert fields["key_constraints"] == "高可用"


def test_system_profile_service_startup_migration_is_idempotent(tmp_path):
    store_path = tmp_path / "system_profiles.json"
    legacy_profile = {
        "system_id": "sys_hop",
        "system_name": "HOP",
        "status": "draft",
        "fields": {
            "system_scope": "账户系统",
            "module_structure": [{"module_name": "账户", "functions": [{"name": "开户"}]}],
            "integration_points": "核心账务",
            "key_constraints": "高可用",
        },
        "created_at": "2026-02-28T00:00:00",
    }
    store_path.write_text(json.dumps([legacy_profile], ensure_ascii=False), encoding="utf-8")

    SystemProfileService(store_path=str(store_path))
    first_data = json.loads(store_path.read_text(encoding="utf-8"))[0]
    first_migrated_at = first_data.get("_migrated_at")
    first_profile_data = first_data.get("profile_data")

    SystemProfileService(store_path=str(store_path))
    second_data = json.loads(store_path.read_text(encoding="utf-8"))[0]

    assert second_data.get("_migrated") is True
    assert second_data.get("_migrated_at") == first_migrated_at
    assert second_data.get("profile_data") == first_profile_data


def test_module_structure_depth_over_three_is_truncated_and_logged(tmp_path, caplog):
    service = SystemProfileService(store_path=str(tmp_path / "profiles.json"))
    deep_structure = [
        {
            "module_name": "L1",
            "children": [
                {
                    "module_name": "L2",
                    "children": [
                        {
                            "module_name": "L3",
                            "children": [{"module_name": "L4", "children": [{"module_name": "L5"}]}],
                        }
                    ],
                }
            ],
        }
    ]

    with caplog.at_level(logging.WARNING):
        normalized = service._normalize_module_structure(deep_structure, strict=False)

    assert normalized[0]["children"][0]["children"][0]["module_name"] == "L3"
    assert normalized[0]["children"][0]["children"][0]["children"] == []
    assert any("module_structure depth exceeds limit" in record.message for record in caplog.records)
