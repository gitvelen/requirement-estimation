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


def _seed_task(task_id: str):
    task = {
        "task_id": task_id,
        "name": "功能点修改任务",
        "creator_id": "mgr_1",
        "status": "completed",
        "workflow_status": "draft",
        "created_at": datetime.now().isoformat(),
        "systems_data": {
            "HOP": [
                {
                    "id": "feat_1",
                    "功能点": "开户",
                    "业务描述": "旧描述",
                    "备注": "旧备注",
                }
            ]
        },
        "modifications": [],
    }
    with task_routes._task_storage_context() as data:
        data[task_id] = task


def test_update_feature_fills_actor_from_login_context(client):
    manager = _seed_user("actor_mgr", "pwd123", ["manager"])
    token = _login(client, "actor_mgr", "pwd123")

    task_id = "task_actor_fill"
    _seed_task(task_id)

    response = client.put(
        f"/api/v1/requirement/features/{task_id}",
        json={
            "system": "HOP",
            "operation": "update",
            "feature_index": 0,
            "feature_data": {"业务描述": "新描述"},
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["actor_id"] == manager["id"]
    assert payload["data"]["actor_role"] == "manager"

    task = task_routes._get_task(task_id)
    last_mod = task.get("modifications")[-1]
    assert last_mod.get("actor_id") == manager["id"]
    assert last_mod.get("actor_role") == "manager"


def test_update_feature_ignores_client_remark_write(client):
    _seed_user("actor_mgr2", "pwd123", ["manager"])
    token = _login(client, "actor_mgr2", "pwd123")

    task_id = "task_actor_remark"
    _seed_task(task_id)

    response = client.put(
        f"/api/v1/requirement/features/{task_id}",
        json={
            "system": "HOP",
            "operation": "update",
            "feature_index": 0,
            "feature_data": {"备注": "客户端恶意备注", "业务描述": "新描述2"},
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

    task = task_routes._get_task(task_id)
    feature = task.get("systems_data", {}).get("HOP", [])[0]
    assert feature.get("业务描述") == "新描述2"
    assert feature.get("备注") == "旧备注"


def test_update_feature_returns_missing_actor_without_login(client):
    task_id = "task_actor_missing"
    _seed_task(task_id)

    response = client.put(
        f"/api/v1/requirement/features/{task_id}",
        json={
            "system": "HOP",
            "operation": "update",
            "feature_index": 0,
            "feature_data": {"业务描述": "新描述3"},
        },
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload.get("error_code") == "missing_actor"

