import os
import sys
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.app import app
from backend.config.config import settings
from backend.api import system_routes, subsystem_routes
from backend.service import user_service


@pytest.fixture()
def client(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(settings, "REPORT_DIR", str(data_dir))
    monkeypatch.setattr(user_service, "USER_STORE_PATH", str(data_dir / "users.json"))
    monkeypatch.setattr(user_service, "USER_STORE_LOCK_PATH", str(data_dir / "users.json.lock"))

    monkeypatch.setattr(system_routes, "CSV_PATH", str(tmp_path / "system_list.csv"))
    monkeypatch.setattr(subsystem_routes, "CSV_PATH", str(tmp_path / "subsystem_list.csv"))

    return TestClient(app)


def _seed_admin():
    admin = user_service.create_user_record({
        "username": "admin",
        "display_name": "管理员",
        "password": "admin123",
        "roles": ["admin"],
    })
    with user_service.user_storage_context() as users:
        users.append(admin)
    return admin


def _seed_manager(username: str = "manager", password: str = "manager123"):
    manager = user_service.create_user_record({
        "username": username,
        "display_name": "经理",
        "password": password,
        "roles": ["manager"],
    })
    with user_service.user_storage_context() as users:
        users.append(manager)
    return manager


def _login(client: TestClient, username: str, password: str) -> str:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["data"]["token"]


def _build_template_xlsx() -> bytes:
    wb = Workbook()
    ws1 = wb.active
    ws1.title = "应用系统清单"
    ws1.append(["系统名称", "英文简称", "状态", "功能描述"])
    ws1.append(["HOP", "HOP", "运行中", "核心系统"])
    ws1.append(["CLMP", "CLMP", "建设中", "贷款平台"])

    ws2 = wb.create_sheet("应用子系统清单")
    ws2.append(["编号", "英文简称", "系统名称", "所属系统", "功能描述"])
    ws2.append([1, "KFC", "开放存", "HOP", "存款子系统"])
    ws2.append([2, "LDP", "联合贷平台", "CLMP", "贷款子系统"])

    bio = BytesIO()
    wb.save(bio)
    return bio.getvalue()


def _build_owner_alias_xlsx() -> bytes:
    wb = Workbook()
    ws1 = wb.active
    ws1.title = "应用系统清单"
    ws1.append(["系统名称", "英文简称", "状态", "系统负责人ID", "系统负责人账号", "负责人姓名"])
    ws1.append(["HOP", "HOP", "运行中", "", "manager", "张三"])

    ws2 = wb.create_sheet("应用子系统清单")
    ws2.append(["编号", "英文简称", "系统名称", "所属系统"])
    ws2.append([1, "KFC", "开放存", "HOP"])

    bio = BytesIO()
    wb.save(bio)
    return bio.getvalue()


def test_system_list_batch_import_replace(client, monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", False)

    _seed_admin()
    token = _login(client, "admin", "admin123")

    excel_bytes = _build_template_xlsx()
    preview = client.post(
        "/api/v1/system-list/batch-import",
        files={"file": ("system_list.xlsx", excel_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert preview.status_code == 200
    data = preview.json()["data"]
    assert data["summary"]["systems_total"] == 2
    assert data["summary"]["mappings_total"] == 2
    assert data["summary"]["systems_error"] == 0
    assert data["summary"]["mappings_error"] == 0

    confirm = client.post(
        "/api/v1/system-list/batch-import/confirm",
        json={"mode": "replace", "systems": data["systems"], "mappings": data["mappings"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert confirm.status_code == 200

    systems = system_routes._read_systems()
    assert {item["name"] for item in systems} == {"HOP", "CLMP"}
    assert {item["abbreviation"] for item in systems} == {"HOP", "CLMP"}
    assert all(item.get("id") for item in systems)
    by_name = {item["name"]: item for item in systems}
    assert by_name["HOP"].get("extra", {}).get("功能描述") == "核心系统"
    assert by_name["CLMP"].get("extra", {}).get("功能描述") == "贷款平台"

    mappings = subsystem_routes._read_subsystem_mappings()
    mapping_dict = {item["subsystem"]: item["main_system"] for item in mappings}
    assert mapping_dict["开放存"] == "HOP"
    assert mapping_dict["联合贷平台"] == "CLMP"
    mapping_by_sub = {item["subsystem"]: item for item in mappings}
    assert mapping_by_sub["开放存"].get("extra", {}).get("功能描述") == "存款子系统"
    assert mapping_by_sub["联合贷平台"].get("extra", {}).get("功能描述") == "贷款子系统"


def test_system_list_preview_owner_alias_and_auth_error_schema(client, monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", False)

    _seed_admin()
    _seed_manager()
    token = _login(client, "admin", "admin123")

    excel_bytes = _build_owner_alias_xlsx()
    preview = client.post(
        "/api/v1/system-list/batch-import",
        files={"file": ("system_list_alias.xlsx", excel_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers={"Authorization": f"Bearer {token}", "X-Request-ID": "req_system_list_alias"},
    )
    assert preview.status_code == 200
    data = preview.json()["data"]
    assert data["summary"]["systems_total"] == 1
    extra = data["systems"][0].get("extra", {})
    assert extra.get("owner_id") == ""
    assert extra.get("owner_username") == "manager"
    assert extra.get("owner_name") == "张三"
    assert "系统负责人ID" not in extra

    confirm = client.post(
        "/api/v1/system-list/batch-import/confirm",
        json={"mode": "replace", "systems": data["systems"], "mappings": data["mappings"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert confirm.status_code == 200

    owner_info = system_routes.resolve_system_owner(system_name="HOP")
    assert owner_info.get("system_found") is True
    assert owner_info.get("resolved_by") == "owner_username"
    assert owner_info.get("resolved_owner_id")

    unauthorized = client.post(
        "/api/v1/system-list/batch-import",
        files={"file": ("system_list_alias.xlsx", excel_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers={"Authorization": "Bearer invalid", "X-Request-ID": "req_system_list_auth"},
    )
    assert unauthorized.status_code == 403
    payload = unauthorized.json()
    assert payload.get("error_code") == "AUTH_001"
    assert payload.get("message")
    assert payload.get("request_id") == "req_system_list_auth"


def test_system_list_confirm_invalid_mode_returns_syslist_003(client, monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", False)

    _seed_admin()
    token = _login(client, "admin", "admin123")

    response = client.post(
        "/api/v1/system-list/batch-import/confirm",
        json={"mode": "invalid_mode", "systems": [], "mappings": []},
        headers={"Authorization": f"Bearer {token}", "X-Request-ID": "req_system_list_mode"},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload.get("error_code") == "SYSLIST_003"
    assert payload.get("request_id") == "req_system_list_mode"
