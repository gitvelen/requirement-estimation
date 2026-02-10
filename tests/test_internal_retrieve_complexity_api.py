import os
import sys

import pytest
from fastapi.testclient import TestClient

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.app import app
from backend.config.config import settings
from backend.service import code_scan_service
from backend.service import esb_service
from backend.service import knowledge_service as ks
from backend.service import system_profile_service
from backend.service import user_service


class DummyEmbeddingService:
    def generate_embedding(self, text):
        return [1.0, 0.0, 0.0]

    def batch_generate_embeddings(self, texts, batch_size=25):
        return [[1.0, 0.0, 0.0] for _ in texts]


@pytest.fixture()
def client(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(settings, "REPORT_DIR", str(data_dir))
    monkeypatch.setattr(settings, "KNOWLEDGE_VECTOR_STORE", "local")
    monkeypatch.setattr(settings, "DEBUG", False)

    monkeypatch.setattr(user_service, "USER_STORE_PATH", str(data_dir / "users.json"))
    monkeypatch.setattr(user_service, "USER_STORE_LOCK_PATH", str(data_dir / "users.json.lock"))

    monkeypatch.setattr(ks, "get_embedding_service", lambda: DummyEmbeddingService())

    ks._knowledge_service = None
    code_scan_service._code_scan_service = None
    esb_service._esb_service = None
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


def test_internal_retrieve_system_profile_context(client):
    _seed_user("internal_admin", "pwd123", ["admin"])
    token = _login(client, "internal_admin", "pwd123")

    profile_service = system_profile_service.get_system_profile_service()
    profile_service.upsert_profile(
        "HOP",
        {"system_id": "sys_hop", "fields": {"core_functions": "开户"}, "evidence_refs": []},
        actor={"id": "internal_admin", "username": "internal_admin"},
    )
    profile_service.mark_code_scan_ingested(
        system_name="HOP",
        system_id="sys_hop",
        job_id="scan_1",
        result_path="/tmp/scan_1.json",
        actor={"id": "internal_admin", "username": "internal_admin"},
    )

    knowledge = ks.get_knowledge_service()
    knowledge.vector_store.batch_insert_knowledge(
        [
            {
                "system_name": "HOP",
                "knowledge_type": "document",
                "content": "转账接口说明",
                "embedding": [1.0, 0.0, 0.0],
                "metadata": {"level": "normal"},
                "source_file": "doc.txt",
            }
        ]
    )

    code_scan = code_scan_service.get_code_scan_service()
    code_scan.embedding_service = DummyEmbeddingService()
    code_scan.vector_store.batch_insert_knowledge(
        [
            {
                "system_name": "HOP",
                "knowledge_type": "capability_item",
                "content": "GET /transfer/query",
                "embedding": [1.0, 0.0, 0.0],
                "metadata": {"entry_id": "HTTP GET /transfer/query"},
                "source_file": "scan.json",
            }
        ]
    )

    esb = esb_service.get_esb_service()
    esb.embedding_service = DummyEmbeddingService()
    esb.import_esb(
        (
            "提供方系统简称,调用方系统简称,交易名称,状态\n"
            "sys_hop,sys_x,转账服务,正常使用\n"
        ).encode("utf-8"),
        "esb.csv",
        target_system_id="sys_hop",
        strict_embedding=True,
    )

    response = client.post(
        "/api/v1/internal/system-profiles/retrieve",
        json={"system_name": "HOP", "query": "转账接口", "top_k": 5},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload.get("system_profile")
    assert isinstance(payload.get("capabilities"), list)
    assert isinstance(payload.get("documents"), list)
    assert isinstance(payload.get("esb_integrations"), list)
    assert int(payload.get("completeness_score") or 0) >= 30


def test_internal_complexity_evaluate(client):
    _seed_user("internal_admin2", "pwd123", ["admin"])
    token = _login(client, "internal_admin2", "pwd123")

    response = client.post(
        "/api/v1/internal/complexity/evaluate",
        json={
            "feature_description": "新增跨系统转账，需风控校验并对接核心账务接口，含性能与并发要求",
            "system_context": {"integration_points": ["risk", "core"]},
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload.get("complexity_level") in {"low", "medium", "high"}
    assert 0 <= float(payload.get("complexity_score") or 0) <= 100
    assert "reasoning" in payload
