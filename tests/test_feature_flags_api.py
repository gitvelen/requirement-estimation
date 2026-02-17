import os
import sys

import pytest
from fastapi.testclient import TestClient

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.app import app
from backend.config.config import settings
from backend.service import user_service


@pytest.fixture()
def client(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(settings, "REPORT_DIR", str(data_dir))
    monkeypatch.setattr(user_service, "USER_STORE_PATH", str(data_dir / "users.json"))
    monkeypatch.setattr(user_service, "USER_STORE_LOCK_PATH", str(data_dir / "users.json.lock"))

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


def test_feature_flags_requires_login(client):
    response = client.get("/api/v1/system/config/feature-flags")
    assert response.status_code == 401


def test_feature_flags_returns_expected_values(client, monkeypatch):
    _seed_user("flag_admin", "pwd123", ["admin"])
    token = _login(client, "flag_admin", "pwd123")

    monkeypatch.setattr(settings, "V21_AUTO_REEVAL_ENABLED", False)
    monkeypatch.setattr(settings, "V21_AI_REMARK_ENABLED", True)
    monkeypatch.setattr(settings, "V21_DASHBOARD_MGMT_ENABLED", False)

    response = client.get(
        "/api/v1/system/config/feature-flags",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "V21_AUTO_REEVAL_ENABLED": False,
        "V21_AI_REMARK_ENABLED": True,
        "V21_DASHBOARD_MGMT_ENABLED": False,
    }


def test_feature_flags_visible_to_all_logged_in_roles(client):
    _seed_user("flag_manager", "pwd123", ["manager"])
    token = _login(client, "flag_manager", "pwd123")

    response = client.get(
        "/api/v1/system/config/feature-flags",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert set(payload.keys()) == {
        "V21_AUTO_REEVAL_ENABLED",
        "V21_AI_REMARK_ENABLED",
        "V21_DASHBOARD_MGMT_ENABLED",
    }

