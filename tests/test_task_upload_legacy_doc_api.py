import os
import sys

import pytest
from fastapi.testclient import TestClient

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
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
    monkeypatch.setattr(settings, "DEBUG", False)
    monkeypatch.setattr(task_routes, "TASK_STORE_PATH", str(data_dir / "task_storage.json"))
    monkeypatch.setattr(task_routes, "TASK_STORE_LOCK_PATH", str(data_dir / "task_storage.json.lock"))
    monkeypatch.setattr(task_routes, "MAGIC_AVAILABLE", False)

    async def _noop_process_task(*_args, **_kwargs):
        return None

    monkeypatch.setattr(task_routes, "process_task", _noop_process_task)
    return TestClient(app)


def test_requirement_upload_accepts_legacy_doc(client):
    response = client.post(
        "/api/v1/requirement/upload",
        files={"file": ("legacy.doc", b"fake-doc-content", "application/msword")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["filename"] == "legacy.doc"


def test_requirement_evaluate_accepts_legacy_doc(client):
    response = client.post(
        "/api/v1/requirement/evaluate",
        data={"request_id": "req-legacy-doc", "priority": 0},
        files={"file": ("legacy.doc", b"fake-doc-content", "application/msword")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["task_id"] == "req-legacy-doc"

