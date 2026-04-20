import os
import sys
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.api import routes as task_routes
from backend.app import app
from backend.config.config import settings


@pytest.fixture()
def client(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    upload_dir = tmp_path / "uploads"
    data_dir.mkdir(parents=True, exist_ok=True)
    upload_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(settings, "REPORT_DIR", str(data_dir))
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload_dir))
    monkeypatch.setattr(task_routes, "TASK_STORE_PATH", str(data_dir / "task_storage.json"))
    monkeypatch.setattr(task_routes, "TASK_STORE_LOCK_PATH", str(data_dir / "task_storage.json.lock"))

    return TestClient(app)


def _build_locked_task():
    return {
        "task_id": "task_locked_specific",
        "name": "锁定任务",
        "status": "completed",
        "workflow_status": "draft",
        "created_at": datetime.now().isoformat(),
        "confirmed": False,
        "requirement_content": "全文需求输入",
        "systems_data": {
            "支付系统": [
                {
                    "id": "feat_1",
                    "序号": "1.1",
                    "功能模块": "支付接入",
                    "功能点": "支付订单同步",
                    "业务描述": "原始描述",
                    "预估人天": 1.0,
                    "复杂度": "中",
                    "系统": "支付系统",
                }
            ]
        },
        "systems": ["支付系统"],
        "modifications": [],
        "ai_system_analysis": {
            "selected_systems": [{"name": "支付系统", "type": "主系统"}],
            "candidate_systems": [],
        },
        "target_system_mode": "specific",
        "target_system_name": "支付系统",
    }


def _seed_locked_task():
    with task_routes._task_storage_context() as data:
        data["task_locked_specific"] = _build_locked_task()


@pytest.mark.parametrize(
    "method,path,kwargs",
    [
        ("post", "/api/v1/requirement/systems/task_locked_specific", {"json": {"name": "核心账务", "type": "主系统", "auto_breakdown": False, "confirm": True}}),
        ("put", "/api/v1/requirement/systems/task_locked_specific/%E6%94%AF%E4%BB%98%E7%B3%BB%E7%BB%9F/rename", {"json": {"new_name": "支付系统-新", "confirm": True}}),
        ("delete", "/api/v1/requirement/systems/task_locked_specific/%E6%94%AF%E4%BB%98%E7%B3%BB%E7%BB%9F?confirm=true", {}),
        ("post", "/api/v1/requirement/systems/task_locked_specific/%E6%94%AF%E4%BB%98%E7%B3%BB%E7%BB%9F/rebreakdown", {"json": {"system_type": "主系统"}}),
    ],
)
def test_locked_specific_task_rejects_system_scope_changes(client, method, path, kwargs):
    _seed_locked_task()

    response = getattr(client, method)(path, **kwargs)

    assert response.status_code == 409
    assert "系统范围已锁定" in response.json()["detail"]


def test_locked_specific_task_still_allows_feature_level_update(client):
    _seed_locked_task()

    response = client.put(
        "/api/v1/requirement/features/task_locked_specific",
        json={
            "system": "支付系统",
            "operation": "update",
            "feature_index": 0,
            "feature_data": {"业务描述": "更新后的业务描述"},
            "confirm": True,
            "actor_id": "pm_locked",
            "actor_role": "manager",
        },
    )

    assert response.status_code == 200

    task = task_routes._get_task("task_locked_specific")
    assert task["systems_data"]["支付系统"][0]["业务描述"] == "更新后的业务描述"
