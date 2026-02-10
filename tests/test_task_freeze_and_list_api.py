import os
import sys
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.app import app
from backend.api import routes as task_routes
from backend.api import system_routes
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

    monkeypatch.setattr(system_routes, "CSV_PATH", str(tmp_path / "system_list.csv"))

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


def test_task_freeze_snapshot_on_confirmed_task(client):
    manager = _seed_user("freeze_mgr", "pwd123", ["manager"])

    system_routes._write_systems(
        [
            {
                "id": "sys_hop",
                "name": "HOP",
                "abbreviation": "HOP",
                "status": "运行中",
                "extra": {"owner_id": manager["id"], "owner_name": "负责人"},
            }
        ]
    )

    task_id = "task_freeze"
    with task_routes._task_storage_context() as data:
        data[task_id] = {
            "task_id": task_id,
            "name": "冻结测试",
            "creator_id": manager["id"],
            "creator_name": manager["display_name"],
            "status": "completed",
            "workflow_status": "draft",
            "confirmed": True,
            "created_at": datetime.now().isoformat(),
            "systems_data": {
                "HOP": [
                    {
                        "id": "feat_1",
                        "功能点": "开户",
                        "预估人天": 2,
                    }
                ]
            },
        }

    task = task_routes._get_task(task_id)
    assert task
    assert task.get("workflow_status") == "completed"
    assert task.get("frozen_at")
    assert float(task.get("final_estimation_days_total") or 0) >= 2

    owner_snapshot = task.get("owner_snapshot") or {}
    assert owner_snapshot.get("primary_owner_id") == manager["id"]
    by_system = task.get("final_estimation_days_by_system") or []
    assert by_system and by_system[0].get("system_id") == "sys_hop"


def test_task_list_group_by_status_and_filters(client):
    admin = _seed_user("freeze_admin", "pwd123", ["admin"])
    manager = _seed_user("freeze_mgr2", "pwd123", ["manager"])

    admin_token = _login(client, "freeze_admin", "pwd123")

    now = datetime.now().isoformat()
    with task_routes._task_storage_context() as data:
        data["task_pending"] = {
            "task_id": "task_pending",
            "name": "待处理",
            "creator_id": manager["id"],
            "creator_name": manager["display_name"],
            "status": "completed",
            "workflow_status": "draft",
            "created_at": now,
            "systems_data": {},
        }
        data["task_progress"] = {
            "task_id": "task_progress",
            "name": "进行中",
            "creator_id": manager["id"],
            "creator_name": manager["display_name"],
            "status": "completed",
            "workflow_status": "evaluating",
            "created_at": now,
            "systems_data": {},
        }
        data["task_done"] = {
            "task_id": "task_done",
            "name": "已完成",
            "creator_id": manager["id"],
            "creator_name": manager["display_name"],
            "status": "completed",
            "workflow_status": "completed",
            "frozen_at": now,
            "created_at": now,
            "owner_snapshot": {"primary_owner_id": manager["id"], "owners": []},
            "systems_data": {},
        }

    grouped = client.get(
        "/api/v1/tasks",
        params={"group_by_status": "true", "page": 1, "page_size": 20},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert grouped.status_code == 200
    groups = grouped.json().get("task_groups", {})
    assert groups.get("pending", {}).get("total", 0) >= 1
    assert groups.get("in_progress", {}).get("total", 0) >= 1
    assert groups.get("completed", {}).get("total", 0) >= 1

    completed_only = client.get(
        "/api/v1/tasks",
        params={"status": "completed", "owner_id": manager["id"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert completed_only.status_code == 200
    items = completed_only.json().get("data", [])
    assert all(item.get("status") == "completed" for item in items)


def test_expert_can_view_assigned_task_detail_and_high_deviation(client):
    manager = _seed_user("detail_mgr", "pwd123", ["manager"])
    expert = _seed_user("detail_exp", "pwd123", ["expert"])

    expert_token = _login(client, "detail_exp", "pwd123")

    now = datetime.now().isoformat()
    with task_routes._task_storage_context() as data:
        data["task_assigned_detail"] = {
            "task_id": "task_assigned_detail",
            "name": "专家可查看任务",
            "creator_id": manager["id"],
            "creator_name": manager["display_name"],
            "status": "completed",
            "workflow_status": "evaluating",
            "current_round": 1,
            "created_at": now,
            "systems_data": {
                "HOP": [
                    {
                        "id": "feat_1",
                        "功能模块": "账户",
                        "功能点": "开户",
                        "预估人天": 2,
                    }
                ]
            },
            "expert_assignments": [
                {
                    "assignment_id": "asg_1",
                    "expert_id": expert["username"],
                    "expert_name": expert["display_name"],
                    "status": "accepted",
                    "round_submissions": {"1": now},
                    "invite_token": "tok_1",
                }
            ],
            "deviations": {"1": {"feat_1": 35}},
            "round_means": {"1": {"feat_1": 1.5}},
            "high_deviation_features": {"1": ["feat_1"]},
        }

        data["task_forbidden_detail"] = {
            "task_id": "task_forbidden_detail",
            "name": "专家不可查看任务",
            "creator_id": manager["id"],
            "creator_name": manager["display_name"],
            "status": "completed",
            "workflow_status": "evaluating",
            "current_round": 1,
            "created_at": now,
            "systems_data": {
                "HOP": [
                    {
                        "id": "feat_9",
                        "功能模块": "账户",
                        "功能点": "销户",
                        "预估人天": 1,
                    }
                ]
            },
            "expert_assignments": [],
        }

    detail = client.get(
        "/api/v1/tasks/task_assigned_detail",
        headers={"Authorization": f"Bearer {expert_token}"},
    )
    assert detail.status_code == 200
    assert detail.json().get("data", {}).get("id") == "task_assigned_detail"

    high_dev = client.get(
        "/api/v1/tasks/task_assigned_detail/high-deviation",
        headers={"Authorization": f"Bearer {expert_token}"},
    )
    assert high_dev.status_code == 200
    assert high_dev.json().get("data", {}).get("round") == 1
    assert len(high_dev.json().get("data", {}).get("items", [])) == 1

    denied = client.get(
        "/api/v1/tasks/task_forbidden_detail",
        headers={"Authorization": f"Bearer {expert_token}"},
    )
    assert denied.status_code == 403
