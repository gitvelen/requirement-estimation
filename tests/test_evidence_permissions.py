import json
import os
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.config.config import settings
from backend.service import user_service
from backend.api import routes as task_routes
from backend.service import evidence_service as evidence_module


@pytest.fixture()
def client(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    upload_dir = tmp_path / "uploads"
    data_dir.mkdir(parents=True, exist_ok=True)
    upload_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(settings, "REPORT_DIR", str(data_dir))
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload_dir))

    monkeypatch.setattr(user_service, "USER_STORE_PATH", str(data_dir / "users.json"))
    monkeypatch.setattr(user_service, "USER_STORE_LOCK_PATH", str(data_dir / "users.json.lock"))

    monkeypatch.setattr(task_routes, "TASK_STORE_PATH", str(data_dir / "task_storage.json"))
    monkeypatch.setattr(task_routes, "TASK_STORE_LOCK_PATH", str(data_dir / "task_storage.json.lock"))

    monkeypatch.setattr(evidence_module, "_evidence_service", None)

    return TestClient(app)


def seed_user(username, password, roles):
    user = user_service.create_user_record({
        "username": username,
        "display_name": username,
        "password": password,
        "roles": roles,
    })
    with user_service.user_storage_context() as users:
        users.append(user)
    return user


def login(client: TestClient, username: str, password: str) -> str:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["data"]["token"]


def prepare_evidence_doc(tmp_path, doc_id="evd_test"):
    evidence_dir = tmp_path / "uploads" / "evidence" / "系统A" / doc_id
    evidence_dir.mkdir(parents=True, exist_ok=True)
    file_path = evidence_dir / "evidence.pdf"
    file_path.write_bytes(b"dummy pdf content")

    doc_meta = {
        "doc_id": doc_id,
        "system_id": "SYS_A",
        "system_name": "系统A",
        "filename": "evidence.pdf",
        "stored_path": str(file_path),
        "doc_type": "pdf",
        "trust_level": "中",
        "doc_date": "2026-02-01",
        "source_org": "测试",
        "version_hint": "v1",
        "parse_meta": {},
        "chunk_count": 0,
        "created_by": "tester",
        "created_at": datetime.now().isoformat(),
    }

    docs_path = tmp_path / "data" / "evidence_docs.json"
    docs_path.write_text(json.dumps([doc_meta], ensure_ascii=False, indent=2), encoding="utf-8")
    return doc_id


def seed_task(task_id, expert_id, doc_id):
    task = {
        "task_id": task_id,
        "name": "权限测试任务",
        "status": "completed",
        "workflow_status": "evaluating",
        "expert_assignments": [
            {
                "assignment_id": "assign_1",
                "expert_id": expert_id,
                "expert_name": expert_id,
                "status": "invited",
            }
        ],
        "evidence_doc_ids": [doc_id],
    }
    with task_routes._task_storage_context() as data:
        data[task_id] = task


def test_expert_preview_permission(client, tmp_path):
    expert = seed_user("expert_ok", "pass123", ["expert"])
    other = seed_user("expert_no", "pass123", ["expert"])

    doc_id = prepare_evidence_doc(tmp_path)
    task_id = "task_perm_1"
    seed_task(task_id, expert["id"], doc_id)

    token_ok = login(client, "expert_ok", "pass123")
    token_no = login(client, "expert_no", "pass123")

    ok_resp = client.get(
        f"/api/v1/knowledge/evidence/preview/{doc_id}?task_id={task_id}",
        headers={"Authorization": f"Bearer {token_ok}"},
    )
    assert ok_resp.status_code == 200

    deny_resp = client.get(
        f"/api/v1/knowledge/evidence/preview/{doc_id}?task_id={task_id}",
        headers={"Authorization": f"Bearer {token_no}"},
    )
    assert deny_resp.status_code == 403
