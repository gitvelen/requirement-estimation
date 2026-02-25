import os
import sys
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.api import routes as task_routes
from backend.app import app
from backend.config.config import settings
from backend.service import user_service


@pytest.fixture()
def client(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(settings, "REPORT_DIR", str(data_dir))
    monkeypatch.setattr(settings, "DEBUG", False)
    monkeypatch.setattr(settings, "V21_AUTO_REEVAL_ENABLED", False)
    monkeypatch.setattr(settings, "V21_AI_REMARK_ENABLED", True)

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


def _seed_task(task_id: str, manager_id: str, manager_name: str, expert=None):
    feature = {
        "id": "feat_1",
        "序号": "1.1",
        "功能模块": "账户管理",
        "功能点": "开户",
        "业务描述": "原始描述",
        "预估人天": 2,
        "系统": "HOP",
    }
    task = {
        "task_id": task_id,
        "name": "备注测试任务",
        "creator_id": manager_id,
        "creator_name": manager_name,
        "status": "completed",
        "workflow_status": "evaluating",
        "current_round": 1,
        "max_rounds": 3,
        "created_at": datetime.now().isoformat(),
        "systems_data": {"HOP": [feature]},
        "systems": ["HOP"],
        "evaluations": {},
        "evaluation_drafts": {},
        "round_feature_ids": {},
        "round_means": {},
        "deviations": {},
        "high_deviation_features": {},
        "report_versions": [],
        "modifications": [],
        "remark": "历史人工备注",
    }

    if expert:
        task["expert_assignments"] = [
            {
                "assignment_id": "assign_1",
                "expert_id": expert["id"],
                "expert_name": expert["display_name"],
                "invite_token": "invite_token_1",
                "status": "invited",
                "created_at": datetime.now().isoformat(),
                "round_submissions": {},
            }
        ]
    else:
        task["expert_assignments"] = []

    with task_routes._task_storage_context() as data:
        data[task_id] = task


def test_pm_save_appends_pm_remark_line(client):
    manager = _seed_user("remark_mgr_1", "pwd123", ["manager"])
    token = _login(client, "remark_mgr_1", "pwd123")
    task_id = "task_pm_remark"
    _seed_task(task_id, manager["id"], manager["display_name"])

    response = client.put(
        f"/api/v1/requirement/features/{task_id}",
        json={
            "system": "HOP",
            "operation": "update",
            "feature_index": 0,
            "confirm": True,
            "feature_data": {"业务描述": "PM修改后描述"},
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    task = task_routes._get_task(task_id)
    lines = [line for line in str(task.get("remark") or "").splitlines() if line.strip()]
    assert lines
    assert "PM" in lines[0]
    assert "历史人工备注" in lines[-1]


def test_expert_submit_appends_expert_remark_line(client):
    manager = _seed_user("remark_mgr_2", "pwd123", ["manager"])
    expert = _seed_user("remark_exp_1", "pwd123", ["expert"])
    token = _login(client, "remark_exp_1", "pwd123")
    task_id = "task_expert_remark"
    _seed_task(task_id, manager["id"], manager["display_name"], expert=expert)

    response = client.post(
        f"/api/v1/evaluation/{task_id}/submit?token=invite_token_1",
        json={"round": 1, "evaluations": {"feat_1": 3}},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    task = task_routes._get_task(task_id)
    lines = [line for line in str(task.get("remark") or "").splitlines() if line.strip()]
    assert lines
    assert "专家" in lines[0]


def test_reevaluate_appends_ai_remark_line_and_deduplicates(client):
    manager = _seed_user("remark_mgr_3", "pwd123", ["manager"])
    token = _login(client, "remark_mgr_3", "pwd123")
    task_id = "task_ai_remark"
    _seed_task(task_id, manager["id"], manager["display_name"])

    save_resp = client.put(
        f"/api/v1/requirement/features/{task_id}",
        json={
            "system": "HOP",
            "operation": "update",
            "feature_index": 0,
            "confirm": True,
            "feature_data": {"业务描述": "触发重评估的PM修改"},
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert save_resp.status_code == 200

    first = client.post(
        f"/api/v1/tasks/{task_id}/reevaluate",
        json={"force": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert first.status_code == 200

    second = client.post(
        f"/api/v1/tasks/{task_id}/reevaluate",
        json={"force": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert second.status_code == 200

    task = task_routes._get_task(task_id)
    lines = [line for line in str(task.get("remark") or "").splitlines() if line.strip()]
    assert lines
    assert "AI重评估" in lines[0]
    assert sum(1 for line in lines if "AI重评估" in line) == 1

