import json
import os
import sys

import pytest
from fastapi.testclient import TestClient

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.app import app
from backend.api import system_routes
from backend.config.config import settings
from backend.service import knowledge_service as ks
from backend.service import system_profile_service
from backend.service import user_service


class DummyEmbeddingService:
    def generate_embedding(self, text: str):
        return [1.0, 0.0, 0.0]


@pytest.fixture()
def client(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(settings, "REPORT_DIR", str(data_dir))
    monkeypatch.setattr(settings, "KNOWLEDGE_VECTOR_STORE", "local")

    monkeypatch.setattr(user_service, "USER_STORE_PATH", str(data_dir / "users.json"))
    monkeypatch.setattr(user_service, "USER_STORE_LOCK_PATH", str(data_dir / "users.json.lock"))
    monkeypatch.setattr(system_routes, "CSV_PATH", str(tmp_path / "system_list.csv"))

    # Avoid real embedding initialization (depends on DASHSCOPE_API_KEY / network).
    monkeypatch.setattr(ks, "get_embedding_service", lambda: DummyEmbeddingService())

    system_profile_service._system_profile_service = None
    ks._knowledge_service = None

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


def _seed_system(owner, system_id: str = "sys_hop", system_name: str = "HOP"):
    system_routes._write_systems(
        [
            {
                "id": system_id,
                "name": system_name,
                "abbreviation": system_name,
                "status": "运行中",
                "extra": {"owner_id": owner["id"], "owner_name": "负责人"},
            }
        ]
    )


def test_publish_allows_v21_four_fields(client, monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", False)

    owner = _seed_user("owner_publish_ok", "owner123", ["manager"])
    _seed_system(owner)

    token = _login(client, "owner_publish_ok", "owner123")

    saved = client.put(
        "/api/v1/system-profiles/HOP",
        json={
            "system_id": "sys_hop",
            "fields": {
                "system_scope": "账户管理系统",
                "module_structure": [{"module_name": "账户", "functions": [{"name": "开户", "desc": "开户流程"}]}],
                "integration_points": "核心账务",
                "key_constraints": "合规",
            },
            "evidence_refs": [],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert saved.status_code == 200

    published = client.post(
        "/api/v1/system-profiles/HOP/publish",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert published.status_code == 200
    payload = published.json()
    assert payload.get("code") == 200
    assert payload.get("data", {}).get("status") == "published"


def test_save_rejects_invalid_module_structure(client, monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", False)

    owner = _seed_user("owner_publish_missing", "owner123", ["manager"])
    _seed_system(owner)

    token = _login(client, "owner_publish_missing", "owner123")

    response = client.put(
        "/api/v1/system-profiles/HOP",
        json={
            "system_id": "sys_hop",
            "fields": {
                "system_scope": "账户管理系统",
                "module_structure": {"module_name": "账户"},
            },
            "evidence_refs": [],
        },
        headers={"Authorization": f"Bearer {token}", "X-Request-ID": "req_profile_publish_missing"},
    )
    assert response.status_code == 400
    payload = response.json()
    assert payload.get("error_code") == "invalid_module_structure"
    assert payload.get("request_id") == "req_profile_publish_missing"
    assert "module_structure" in str(payload.get("message") or "")


def test_profile_fields_only_keep_v21_contract(client, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "DEBUG", False)

    owner = _seed_user("owner_business_goal", "owner123", ["manager"])
    _seed_system(owner)

    token = _login(client, "owner_business_goal", "owner123")

    saved = client.put(
        "/api/v1/system-profiles/HOP",
        json={
            "system_id": "sys_hop",
            "fields": {
                "system_scope": "做A",
                "module_structure": [{"module_name": "账户", "functions": [{"name": "开立", "desc": "开立账户"}]}],
                "integration_points": "核心账务",
                "key_constraints": "高可用",
                "business_goal": "应被忽略",
                "core_functions": "应被忽略",
            },
            "evidence_refs": [],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert saved.status_code == 200

    fetched = client.get(
        "/api/v1/system-profiles/HOP",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert fetched.status_code == 200
    data = fetched.json().get("data") or {}
    fields = data.get("fields") or {}
    assert set(fields.keys()) == {"system_scope", "module_structure", "integration_points", "key_constraints"}
    assert fields.get("system_scope") == "做A"
    assert isinstance(fields.get("module_structure"), list)
    assert fields.get("module_structure")[0].get("module_name") == "账户"

    store_path = os.path.join(settings.REPORT_DIR, "system_profiles.json")
    with open(store_path, "r", encoding="utf-8") as f:
        stored = json.load(f)
    assert stored and isinstance(stored, list)
    stored_fields = stored[0].get("fields") or {}
    assert set(stored_fields.keys()) == {"system_scope", "module_structure", "integration_points", "key_constraints"}

    published = client.post(
        "/api/v1/system-profiles/HOP/publish",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert published.status_code == 200

    knowledge_store = os.path.join(settings.REPORT_DIR, "knowledge_store.json")
    with open(knowledge_store, "r", encoding="utf-8") as f:
        entries = json.load(f)
    assert isinstance(entries, list)
    inserted = [item for item in entries if item.get("system_name") == "HOP" and item.get("knowledge_type") == "system_profile"]
    assert inserted
    metadata = inserted[-1].get("metadata", {})
    assert set(metadata.keys()) == {"system_scope", "module_structure", "integration_points", "key_constraints"}
