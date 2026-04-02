import os
import sys
from io import BytesIO

import pytest
from fastapi.testclient import TestClient

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.app import app
from backend.api import esb_routes
from backend.service import user_service


class DummyMetadataGovernanceService:
    def get_current_config(self):
        return {
            "similarity_threshold": 0.8,
            "execution_time": "now",
            "match_scope": "new",
        }

    def run_or_schedule(self, *, similarity_threshold: float, execution_time: str, match_scope: str):
        if execution_time == "daily_23":
            return type("ScheduledResult", (), {"scheduled": True, "execution_time": "daily_23"})()
        return type(
            "RunNowResult",
            (),
            {
                "scheduled": False,
                "execution_time": "now",
                "job_id": "mgov_testjob123",
            },
        )()

    def get_job(self, job_id: str):
        return {
            "job_id": job_id,
            "status": "completed",
            "created_at": "2026-03-31T10:00:00",
            "completed_at": "2026-03-31T10:05:00",
        }

    def get_latest_job(self):
        return {
            "job_id": "mgov_testjob123",
            "status": "completed",
            "created_at": "2026-03-31T10:00:00",
            "completed_at": "2026-03-31T10:05:00",
        }

    def get_result_path(self, job_id: str):
        return None


@pytest.fixture()
def client(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(user_service, "USER_STORE_PATH", str(data_dir / "users.json"))
    monkeypatch.setattr(user_service, "USER_STORE_LOCK_PATH", str(data_dir / "users.json.lock"))
    monkeypatch.setattr(esb_routes, "get_metadata_governance_service", lambda: DummyMetadataGovernanceService())

    return TestClient(app)


def _seed_user(username: str, password: str, roles, display_name: str | None = None):
    user = user_service.create_user_record(
        {
            "username": username,
            "display_name": display_name or username,
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


def test_metadata_governance_config_requires_esb_admin(client):
    _seed_user("other_admin", "pwd123", ["admin"])
    token = _login(client, "other_admin", "pwd123")

    response = client.get(
        "/api/v1/esb/metadata-governance/config",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_metadata_governance_config_returns_current_defaults_for_esb_display_name_admin(client):
    _seed_user("admin", "pwd123", ["admin"], display_name="esb")
    token = _login(client, "admin", "pwd123")

    response = client.get(
        "/api/v1/esb/metadata-governance/config",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert "similarity_threshold" in payload
    assert "execution_time" in payload
    assert "match_scope" in payload


def test_metadata_governance_run_returns_job_id_for_esb_display_name_admin_run_now(client):
    _seed_user("admin", "pwd123", ["admin"], display_name="esb")
    token = _login(client, "admin", "pwd123")

    response = client.post(
        "/api/v1/esb/metadata-governance/run",
        json={
            "similarity_threshold": 0.8,
            "execution_time": "now",
            "match_scope": "new",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert "job_id" in payload
    assert payload["status"] == "pending"


def test_metadata_governance_run_saves_schedule_for_esb_display_name_admin_without_immediate_file(client):
    _seed_user("admin", "pwd123", ["admin"], display_name="esb")
    token = _login(client, "admin", "pwd123")

    response = client.post(
        "/api/v1/esb/metadata-governance/run",
        json={
            "similarity_threshold": 0.85,
            "execution_time": "daily_23",
            "match_scope": "all",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["scheduled"] is True
    assert payload["execution_time"] == "daily_23"
