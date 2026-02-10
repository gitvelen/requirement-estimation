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
    def generate_embedding(self, text):
        return [1.0, 0.0, 0.0]

    def batch_generate_embeddings(self, texts, batch_size=25):
        return [[1.0, 0.0, 0.0] for _ in texts]


class BrokenEmbeddingService:
    def generate_embedding(self, text):
        raise RuntimeError("embedding unavailable")

    def batch_generate_embeddings(self, texts, batch_size=25):
        raise RuntimeError("embedding unavailable")


@pytest.fixture()
def client(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(settings, "REPORT_DIR", str(data_dir))
    monkeypatch.setattr(settings, "KNOWLEDGE_VECTOR_STORE", "local")
    monkeypatch.setattr(settings, "DEBUG", False)

    monkeypatch.setattr(user_service, "USER_STORE_PATH", str(data_dir / "users.json"))
    monkeypatch.setattr(user_service, "USER_STORE_LOCK_PATH", str(data_dir / "users.json.lock"))
    monkeypatch.setattr(system_routes, "CSV_PATH", str(tmp_path / "system_list.csv"))

    monkeypatch.setattr(ks, "get_embedding_service", lambda: DummyEmbeddingService())

    ks._knowledge_service = None
    system_profile_service._system_profile_service = None

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


def _seed_system(system_name: str, system_id: str, owner_id: str = ""):
    extra = {}
    if owner_id:
        extra["owner_id"] = owner_id

    system_routes._write_systems(
        [
            {
                "id": system_id,
                "name": system_name,
                "abbreviation": system_name,
                "status": "运行中",
                "extra": extra,
            }
        ]
    )


def test_knowledge_import_invalid_format_returns_know001(client):
    _seed_user("kmgr1", "pwd123", ["manager"])
    token = _login(client, "kmgr1", "pwd123")

    response = client.post(
        "/api/v1/knowledge/imports",
        data={"knowledge_type": "document", "level": "normal"},
        files={"file": ("bad.doc", b"fake", "application/msword")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "KNOW_002"


def test_knowledge_import_level_l0_requires_document(client):
    _seed_user("kmgr2", "pwd123", ["manager"])
    token = _login(client, "kmgr2", "pwd123")

    response = client.post(
        "/api/v1/knowledge/imports",
        data={"knowledge_type": "code", "level": "l0"},
        files={"file": ("notes.txt", b"hello", "text/plain")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "KNOW_001"


def test_knowledge_import_document_updates_completeness(client):
    manager = _seed_user("kmgr3", "pwd123", ["manager"])
    token = _login(client, "kmgr3", "pwd123")
    _seed_system("HOP", "sys_hop", owner_id=manager["id"])

    response = client.post(
        "/api/v1/knowledge/imports",
        data={
            "knowledge_type": "document",
            "level": "normal",
            "system_id": "sys_hop",
        },
        files={"file": ("spec.csv", "字段,说明\nA,系统说明与接口约束".encode("utf-8"), "text/csv")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["imported"] >= 1
    assert payload["failed"] == 0

    profile = system_profile_service.get_system_profile_service().get_profile("HOP")
    assert profile
    assert int(profile.get("document_count") or 0) >= 1
    assert int(profile.get("completeness_score") or 0) >= 10


def test_knowledge_import_l0_not_counted_in_completeness(client):
    manager = _seed_user("kmgr4", "pwd123", ["manager"])
    token = _login(client, "kmgr4", "pwd123")
    _seed_system("HOP", "sys_hop", owner_id=manager["id"])

    response = client.post(
        "/api/v1/knowledge/imports",
        data={
            "knowledge_type": "document",
            "level": "l0",
            "system_id": "sys_hop",
        },
        files={"file": ("history.csv", "字段,说明\nA,历史评估结论".encode("utf-8"), "text/csv")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["imported"] >= 1

    profile = system_profile_service.get_system_profile_service().get_profile("HOP")
    assert profile
    assert int(profile.get("document_count") or 0) == 0
    assert int(profile.get("completeness_score") or 0) == 0


def test_knowledge_import_embedding_unavailable_returns_emb001(client):
    manager = _seed_user("kmgr5", "pwd123", ["manager"])
    token = _login(client, "kmgr5", "pwd123")
    _seed_system("HOP", "sys_hop", owner_id=manager["id"])

    service = ks.get_knowledge_service()
    service.embedding_service = BrokenEmbeddingService()

    response = client.post(
        "/api/v1/knowledge/imports",
        data={
            "knowledge_type": "document",
            "level": "normal",
            "system_id": "sys_hop",
        },
        files={"file": ("spec.csv", "字段,说明\nA,系统说明".encode("utf-8"), "text/csv")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 503
    assert response.json()["error_code"] == "EMB_001"


def test_knowledge_import_parse_failure_returns_know002(client):
    _seed_user("kmgr6", "pwd123", ["manager"])
    token = _login(client, "kmgr6", "pwd123")

    response = client.post(
        "/api/v1/knowledge/imports",
        data={"knowledge_type": "document", "level": "normal"},
        files={"file": ("empty.txt", b"", "text/plain")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "KNOW_002"
