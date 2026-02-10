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


def _seed_task(task_id: str, manager, expert):
    with task_routes._task_storage_context() as data:
        data[task_id] = {
            "task_id": task_id,
            "name": "评估详情任务",
            "creator_id": manager["id"],
            "creator_name": manager["display_name"],
            "status": "completed",
            "workflow_status": "completed",
            "created_at": datetime.now().isoformat(),
            "systems": ["HOP"],
            "systems_data": {
                "HOP": [
                    {
                        "id": "feat_1",
                        "功能点": "开户",
                        "预估人天": 2,
                        "reasoning": "AI判断规则复杂",
                    },
                    {
                        "id": "feat_2",
                        "功能点": "销户",
                        "预估人天": 1,
                    },
                ]
            },
            "evaluations": {
                "1": {
                    expert["username"]: {
                        "feat_1": 3,
                        "feat_2": 1,
                    }
                }
            },
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


def test_expert_deviation_compute_and_query(client):
    admin = _seed_user("eval_admin", "pwd123", ["admin"])
    manager = _seed_user("eval_mgr", "pwd123", ["manager"])
    expert = _seed_user("eval_exp", "pwd123", ["expert"])
    outsider = _seed_user("eval_out", "pwd123", ["expert"])

    admin_token = _login(client, "eval_admin", "pwd123")
    manager_token = _login(client, "eval_mgr", "pwd123")
    expert_token = _login(client, "eval_exp", "pwd123")
    outsider_token = _login(client, "eval_out", "pwd123")

    _seed_task("task_eval_contract", manager, expert)

    compute = client.post(
        "/api/v1/internal/tasks/task_eval_contract/expert-deviations/compute",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert compute.status_code == 200
    report = compute.json().get("deviation_report", {})
    assert report.get("summary", {}).get("feature_count", 0) >= 1

    manager_query = client.get(
        "/api/v1/tasks/task_eval_contract/expert-deviations",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert manager_query.status_code == 200
    assert manager_query.json().get("deviation_report")

    expert_query = client.get(
        "/api/v1/tasks/task_eval_contract/expert-deviations",
        headers={"Authorization": f"Bearer {expert_token}"},
    )
    assert expert_query.status_code == 200

    denied = client.get(
        "/api/v1/tasks/task_eval_contract/expert-deviations",
        headers={"Authorization": f"Bearer {outsider_token}"},
    )
    assert denied.status_code == 403
    assert denied.json().get("error_code") == "AUTH_001"


def test_task_evaluation_detail_contract(client):
    manager = _seed_user("eval_mgr2", "pwd123", ["manager"])
    expert = _seed_user("eval_exp2", "pwd123", ["expert"])

    manager_token = _login(client, "eval_mgr2", "pwd123")
    _seed_task("task_eval_detail", manager, expert)

    response = client.get(
        "/api/v1/tasks/task_eval_detail/evaluation",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload.get("task_id") == "task_eval_detail"
    assert payload.get("status") == "completed"
    features = payload.get("features") or []
    assert len(features) == 2
    assert all(item.get("feature_id") for item in features)
