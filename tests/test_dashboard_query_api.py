import os
import sys
from datetime import datetime, timedelta

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


def _seed_dashboard_tasks(manager, expert):
    now = datetime.now()

    with task_routes._task_storage_context() as data:
        data["task_dashboard_a"] = {
            "task_id": "task_dashboard_a",
            "name": "看板任务A",
            "creator_id": manager["id"],
            "creator_name": manager["display_name"],
            "status": "completed",
            "workflow_status": "completed",
            "created_at": (now - timedelta(days=4)).isoformat(),
            "frozen_at": (now - timedelta(days=2)).isoformat(),
            "project_id": "proj_a",
            "ai_involved": True,
            "ai_estimation_days_total": 10,
            "final_estimation_days_total": 12,
            "final_estimation_days_by_system": [
                {"system_id": "sys_hop", "system_name": "HOP", "days": 8},
                {"system_id": "sys_pay", "system_name": "PAY", "days": 4},
            ],
            "owner_snapshot": {
                "primary_owner_id": manager["id"],
                "primary_owner_name": manager["display_name"],
            },
            "expert_assignments": [
                {
                    "assignment_id": "assign_a",
                    "expert_id": expert["username"],
                    "expert_name": expert["display_name"],
                    "status": "submitted",
                    "round_submissions": {"1": now.isoformat()},
                }
            ],
        }

        data["task_dashboard_b"] = {
            "task_id": "task_dashboard_b",
            "name": "看板任务B",
            "creator_id": manager["id"],
            "creator_name": manager["display_name"],
            "status": "completed",
            "workflow_status": "archived",
            "created_at": (now - timedelta(days=8)).isoformat(),
            "frozen_at": (now - timedelta(days=5)).isoformat(),
            "project_id": "proj_b",
            "ai_involved": False,
            "ai_estimation_days_total": 4,
            "final_estimation_days_total": 5,
            "final_estimation_days_by_system": [
                {"system_id": "sys_hop", "system_name": "HOP", "days": 5},
            ],
            "owner_snapshot": {
                "primary_owner_id": manager["id"],
                "primary_owner_name": manager["display_name"],
            },
            "expert_assignments": [
                {
                    "assignment_id": "assign_b",
                    "expert_id": expert["username"],
                    "expert_name": expert["display_name"],
                    "status": "invited",
                    "round_submissions": {},
                }
            ],
        }

        data["task_dashboard_pending"] = {
            "task_id": "task_dashboard_pending",
            "name": "在途任务",
            "creator_id": manager["id"],
            "creator_name": manager["display_name"],
            "status": "completed",
            "workflow_status": "evaluating",
            "created_at": now.isoformat(),
            "ai_involved": True,
            "owner_snapshot": {
                "primary_owner_id": manager["id"],
                "primary_owner_name": manager["display_name"],
            },
        }


def test_dashboard_query_returns_widgets_for_all_pages(client):
    _seed_user("dash_admin", "pwd123", ["admin"])
    manager = _seed_user("dash_mgr", "pwd123", ["manager"])
    expert = _seed_user("dash_exp", "pwd123", ["expert"])

    admin_token = _login(client, "dash_admin", "pwd123")
    _seed_dashboard_tasks(manager, expert)

    for page in ["overview", "rankings", "ai", "system", "flow"]:
        response = client.post(
            "/api/v1/efficiency/dashboard/query",
            json={
                "page": page,
                "perspective": "executive",
                "filters": {"time_range": "last_30d"},
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        result = response.json().get("result", {})
        widgets = result.get("widgets") or []
        assert result.get("page") == page
        assert len(widgets) >= 2
        assert all("sample_size" in widget for widget in widgets)


def test_dashboard_query_validates_params(client):
    _seed_user("dash_admin2", "pwd123", ["admin"])
    token = _login(client, "dash_admin2", "pwd123")

    bad_page = client.post(
        "/api/v1/efficiency/dashboard/query",
        json={"page": "bad", "perspective": "executive", "filters": {}},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert bad_page.status_code == 400
    assert bad_page.json().get("error_code") == "REPORT_002"

    bad_time = client.post(
        "/api/v1/efficiency/dashboard/query",
        json={
            "page": "overview",
            "perspective": "executive",
            "filters": {"time_range": "custom"},
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert bad_time.status_code == 400
    assert bad_time.json().get("error_code") == "REPORT_002"


def test_dashboard_query_drilldown_filters_include_system_scope(client):
    _seed_user("dash_admin3", "pwd123", ["admin"])
    manager = _seed_user("dash_mgr3", "pwd123", ["manager"])
    expert = _seed_user("dash_exp3", "pwd123", ["expert"])

    token = _login(client, "dash_admin3", "pwd123")
    _seed_dashboard_tasks(manager, expert)

    response = client.post(
        "/api/v1/efficiency/dashboard/query",
        json={
            "page": "system",
            "perspective": "executive",
            "filters": {
                "time_range": "last_30d",
                "system_ids": ["sys_hop"],
                "ai_involved": True,
            },
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    widgets = response.json().get("result", {}).get("widgets", [])
    assert len(widgets) >= 2

    top_widget = widgets[0]
    assert top_widget.get("drilldown_filters", {}).get("system_id") == "sys_hop"
    items = top_widget.get("data", {}).get("items", [])
    assert items
    assert all(item.get("system_id") == "sys_hop" for item in items)
