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


def _seed_task(task_id: str, creator_id: str):
    task = {
        "task_id": task_id,
        "name": "轨迹测试任务",
        "creator_id": creator_id,
        "status": "completed",
        "workflow_status": "draft",
        "created_at": datetime.now().isoformat(),
        "systems_data": {
            "HOP": [
                {
                    "id": "feat_1",
                    "功能点": "开户",
                    "reasoning": "r" * 1200,
                }
            ]
        },
        "ai_initial_features": [
            {
                "feature_id": "feat_1",
                "system_name": "HOP",
                "reasoning": "r" * 1200,
                "feature": {"id": "feat_1", "功能点": "开户"},
            }
        ],
        "ai_initial_feature_count": 1,
        "modification_traces": [
            {
                "trace_id": "trace_old",
                "operation": "adjust",
                "feature_id": "feat_1",
                "reason_code": "旧记录",
                "notes": "old",
                "actor": creator_id,
                "recorded_at": (datetime.now() - timedelta(days=200)).isoformat(),
                "original_ai_reasoning": "old",
            }
        ],
    }

    with task_routes._task_storage_context() as data:
        data[task_id] = task


class DummyOrchestrator:
    def __init__(self, systems_data, captured_requirement_data=None):
        self._systems_data = systems_data
        self._captured_requirement_data = captured_requirement_data

    def process_with_retry(self, task_id, requirement_data, max_retry, progress_callback=None):
        if self._captured_requirement_data is not None:
            self._captured_requirement_data.update(requirement_data)
        if progress_callback:
            progress_callback(80, "dummy")
        # 【v2.4】返回 4 个值：report_path, systems_data, ai_system_analysis, ai_original_output
        ai_original_output = {
            "system_recognition": {"systems": [{"name": "HOP"}], "system_count": 1, "timestamp": 0},
            "feature_split": {"systems_data": self._systems_data, "total_features": 1, "timestamp": 0},
            "work_estimation": {"estimation_details": {}, "total_workload": 0, "timestamp": 0}
        }
        return (
            os.path.join(settings.REPORT_DIR, f"{task_id}.xlsx"),
            self._systems_data,
            {"selected_systems": [{"name": "HOP"}]},
            ai_original_output,
        )


def test_ai_initial_snapshot_written_once(client, monkeypatch):
    manager = _seed_user("snapshot_mgr", "pwd123", ["manager"])

    task_id = "task_snapshot"
    with task_routes._task_storage_context() as data:
        data[task_id] = {
            "task_id": task_id,
            "status": "pending",
            "ai_status": "pending",
            "progress": 0,
            "message": "",
            "file_path": "/tmp/req.docx",
            "filename": "req.docx",
            "creator_id": manager["id"],
            "created_at": datetime.now().isoformat(),
            "systems_data": {},
        }

    monkeypatch.setattr(task_routes.docx_parser, "parse", lambda _: {"requirement_content": "需求内容"})
    first_systems = {"HOP": [{"功能点": "开户", "reasoning": "首次推理"}]}
    monkeypatch.setattr(task_routes, "get_agent_orchestrator", lambda: DummyOrchestrator(first_systems))

    task_routes.process_task_sync(task_id, "/tmp/req.docx")

    after_first = task_routes._get_task(task_id)
    assert after_first.get("ai_initial_feature_count") == 1
    first_snapshot = list(after_first.get("ai_initial_features") or [])
    assert first_snapshot

    second_systems = {"HOP": [{"功能点": "二次推理", "reasoning": "第二次"}]}
    monkeypatch.setattr(task_routes, "get_agent_orchestrator", lambda: DummyOrchestrator(second_systems))
    task_routes.process_task_sync(task_id, "/tmp/req.docx")

    after_second = task_routes._get_task(task_id)
    assert after_second.get("ai_initial_feature_count") == 1
    assert after_second.get("ai_initial_features") == first_snapshot


def test_process_task_sync_clears_stale_error_after_success(client, monkeypatch):
    manager = _seed_user("snapshot_mgr_2", "pwd123", ["manager"])

    task_id = "task_snapshot_error"
    with task_routes._task_storage_context() as data:
        data[task_id] = {
            "task_id": task_id,
            "status": "failed",
            "ai_status": "failed",
            "progress": 20,
            "message": "处理失败: Request timed out.",
            "error": "Request timed out.",
            "file_path": "/tmp/req.docx",
            "filename": "req.docx",
            "creator_id": manager["id"],
            "created_at": datetime.now().isoformat(),
            "systems_data": {},
        }

    monkeypatch.setattr(task_routes.docx_parser, "parse", lambda _: {"requirement_content": "需求内容"})
    monkeypatch.setattr(
        task_routes,
        "get_agent_orchestrator",
        lambda: DummyOrchestrator({"HOP": [{"功能点": "开户", "reasoning": "首次推理"}]}),
    )

    task_routes.process_task_sync(task_id, "/tmp/req.docx")

    task = task_routes._get_task(task_id)
    assert task["status"] == "completed"
    assert task["message"] == "评估完成"
    assert "error" not in task


def test_process_task_sync_prefers_parsed_requirement_name_over_filename(client, monkeypatch):
    manager = _seed_user("snapshot_mgr_3", "pwd123", ["manager"])

    task_id = "task_snapshot_name"
    with task_routes._task_storage_context() as data:
        data[task_id] = {
            "task_id": task_id,
            "status": "pending",
            "ai_status": "pending",
            "progress": 0,
            "message": "",
            "file_path": "/tmp/req.docx",
            "filename": "req.docx",
            "creator_id": manager["id"],
            "created_at": datetime.now().isoformat(),
            "systems_data": {},
        }

    monkeypatch.setattr(
        task_routes.docx_parser,
        "parse",
        lambda _: {
            "requirement_content": "需求内容",
            "requirement_name": "真实需求名称",
            "requirement_summary": "真实需求摘要",
        },
    )
    captured_requirement_data = {}
    monkeypatch.setattr(
        task_routes,
        "get_agent_orchestrator",
        lambda: DummyOrchestrator(
            {"HOP": [{"功能点": "开户", "reasoning": "首次推理"}]},
            captured_requirement_data=captured_requirement_data,
        ),
    )

    task_routes.process_task_sync(task_id, "/tmp/req.docx")

    task = task_routes._get_task(task_id)
    assert captured_requirement_data["requirement_name"] == "真实需求名称"
    assert task["requirement_name"] == "真实需求名称"


def test_modification_trace_api_permissions_and_retention(client, monkeypatch):
    manager = _seed_user("trace_mgr", "pwd123", ["manager"])
    other = _seed_user("trace_other", "pwd123", ["manager"])

    manager_token = _login(client, "trace_mgr", "pwd123")
    other_token = _login(client, "trace_other", "pwd123")

    _seed_task("task_trace", manager["id"])

    response = client.post(
        "/api/v1/tasks/task_trace/modification-traces",
        json={
            "operation": "delete",
            "feature_id": "feat_1",
            "reason_code": "拆分过细",
            "notes": "需要合并",
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload.get("trace_id")
    assert payload.get("recorded_at")

    stored = task_routes._get_task("task_trace")
    traces = stored.get("modification_traces") or []
    assert len(traces) == 1
    trace = traces[0]
    assert trace.get("actor") == manager["id"]
    assert trace.get("operation") == "delete"
    assert trace.get("reason_code") == "拆分过细"
    assert len(trace.get("original_ai_reasoning") or "") <= 1015

    denied = client.post(
        "/api/v1/tasks/task_trace/modification-traces",
        json={
            "operation": "adjust",
            "feature_id": "feat_1",
            "reason_code": "口径修正",
        },
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert denied.status_code == 403
    assert denied.json().get("error_code") == "AUTH_001"

    invalid = client.post(
        "/api/v1/tasks/task_trace/modification-traces",
        json={
            "operation": "adjust",
            "feature_id": "feat_1",
            "reason_code": "",
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert invalid.status_code == 400
    assert invalid.json().get("error_code") == "TRACE_001"
