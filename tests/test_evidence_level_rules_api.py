import os
import sys

from fastapi.testclient import TestClient

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.app import app
from backend.config.config import settings
from backend.service import user_service


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


def test_update_rules_accepts_human_friendly_payload(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(settings, "REPORT_DIR", str(data_dir))
    monkeypatch.setattr(settings, "DEBUG", False)
    monkeypatch.setattr(user_service, "USER_STORE_PATH", str(data_dir / "users.json"))
    monkeypatch.setattr(user_service, "USER_STORE_LOCK_PATH", str(data_dir / "users.json.lock"))

    client = TestClient(app)
    _seed_user("admin_rule_human", "admin123", ["admin"])
    token = _login(client, "admin_rule_human", "admin123")

    response = client.put(
        "/api/v1/evidence-level/rules",
        json={
            "version": 5,
            "levels": [
                {
                    "level": "e3",
                    "all_of": "code,profile",
                    "any_groups": ["evidence,esb", "profile"],
                    "none_of": ["unknown"],
                },
                "E0",
            ],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["version"] == 5
    assert payload["levels"][0]["level"] == "E3"
    assert payload["levels"][0]["all_of"] == ["code", "profile"]
    assert payload["levels"][0]["any_groups"] == [["evidence", "esb"], ["profile"]]
    assert "none_of" not in payload["levels"][0]
    assert payload["levels"][1] == {"level": "E0"}

    fetched = client.get(
        "/api/v1/evidence-level/rules",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert fetched.status_code == 200
    fetched_data = fetched.json()["data"]
    assert fetched_data["version"] == 5
    assert fetched_data["levels"][0]["level"] == "E3"


def test_update_rules_supports_legacy_rules_wrapper(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(settings, "REPORT_DIR", str(data_dir))
    monkeypatch.setattr(settings, "DEBUG", False)
    monkeypatch.setattr(user_service, "USER_STORE_PATH", str(data_dir / "users.json"))
    monkeypatch.setattr(user_service, "USER_STORE_LOCK_PATH", str(data_dir / "users.json.lock"))

    client = TestClient(app)
    _seed_user("admin_rule_legacy", "admin123", ["admin"])
    token = _login(client, "admin_rule_legacy", "admin123")

    response = client.put(
        "/api/v1/evidence-level/rules",
        json={
            "rules": {
                "version": 2,
                "levels": [
                    {"level": "E1", "any_of": ["profile"]},
                    {"level": "E0"},
                ],
            }
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["version"] == 2
    assert payload["levels"][0]["level"] == "E1"
    assert payload["levels"][0]["any_of"] == ["profile"]
