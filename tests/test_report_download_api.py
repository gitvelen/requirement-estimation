import os
import sys
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.app import app
from backend.api import routes as task_routes
from backend.config.config import settings
from backend.service import user_service


@pytest.fixture()
def client(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(settings, "REPORT_DIR", str(data_dir))
    monkeypatch.setattr(settings, "DEBUG", False)

    monkeypatch.setattr(user_service, "USER_STORE_PATH", str(data_dir / "users.json"))
    monkeypatch.setattr(user_service, "USER_STORE_LOCK_PATH", str(data_dir / "users.json.lock"))

    monkeypatch.setattr(task_routes, "TASK_STORE_PATH", str(data_dir / "task_storage.json"))
    monkeypatch.setattr(task_routes, "TASK_STORE_LOCK_PATH", str(data_dir / "task_storage.json.lock"))

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


def _seed_report_task(task_id: str, manager, expert, report_path: str):
    with task_routes._task_storage_context() as data:
        data[task_id] = {
            "task_id": task_id,
            "name": "报告下载任务",
            "creator_id": manager["id"],
            "creator_name": manager["display_name"],
            "status": "completed",
            "workflow_status": "completed",
            "created_at": datetime.now().isoformat(),
            "report_versions": [
                {"id": "rep_1", "round": 1, "version": 1, "file_path": report_path}
            ],
            "expert_assignments": [
                {
                    "assignment_id": "assign_1",
                    "expert_id": expert["username"],
                    "expert_name": expert["display_name"],
                    "invite_token": "token_1",
                    "status": "submitted",
                    "round_submissions": {"1": datetime.now().isoformat()},
                }
            ],
        }


def test_report_download_expert_permissions_and_format(client, tmp_path):
    manager = _seed_user("rep_mgr", "pwd123", ["manager"])
    expert = _seed_user("rep_exp", "pwd123", ["expert"])
    outsider = _seed_user("rep_out", "pwd123", ["expert"])

    manager_token = _login(client, "rep_mgr", "pwd123")
    expert_token = _login(client, "rep_exp", "pwd123")
    outsider_token = _login(client, "rep_out", "pwd123")

    report_file = tmp_path / "report.pdf"
    report_file.write_bytes(b"%PDF-1.4\n%test")

    _seed_report_task("task_report", manager, expert, str(report_file))

    docx_resp = client.get(
        "/api/v1/tasks/task_report/report",
        params={"format": "docx"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert docx_resp.status_code == 400
    assert docx_resp.json().get("error_code") == "REPORT_002"

    denied = client.get(
        "/api/v1/tasks/task_report/report",
        headers={"Authorization": f"Bearer {outsider_token}"},
    )
    assert denied.status_code == 403
    assert denied.json().get("error_code") == "AUTH_001"

    allowed = client.get(
        "/api/v1/tasks/task_report/report",
        headers={"Authorization": f"Bearer {expert_token}"},
    )
    assert allowed.status_code == 200
    assert "application/pdf" in str(allowed.headers.get("content-type") or "")


def test_report_download_missing_report_returns_report003(client, tmp_path):
    manager = _seed_user("rep_mgr2", "pwd123", ["manager"])
    token = _login(client, "rep_mgr2", "pwd123")

    with task_routes._task_storage_context() as data:
        data["task_no_report"] = {
            "task_id": "task_no_report",
            "name": "无报告任务",
            "creator_id": manager["id"],
            "creator_name": manager["display_name"],
            "status": "completed",
            "workflow_status": "evaluating",
            "created_at": datetime.now().isoformat(),
            "report_versions": [],
            "expert_assignments": [],
        }

    response = client.get(
        "/api/v1/tasks/task_no_report/report",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400
    assert response.json().get("error_code") == "REPORT_003"
