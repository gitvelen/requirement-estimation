import json
import os
import sys
from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.app import app
from backend.api import system_routes
from backend.config.config import settings
from backend.service import document_parser
from backend.service import knowledge_service as ks
from backend.service import profile_summary_service as profile_summary_module
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


class StubProfileSummaryService:
    def __init__(self) -> None:
        self.calls = []
        self._counter = 0

    def trigger_summary(
        self,
        *,
        system_id: str,
        system_name: str,
        actor: Dict[str, Any] | None = None,
        reason: str = "import",
        source_file: str | None = None,
        trigger: str | None = None,
        context_override: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        self._counter += 1
        self.calls.append(
            {
                "job_id": f"summary_task_{self._counter:03d}",
                "system_id": system_id,
                "system_name": system_name,
                "actor_id": (actor or {}).get("id"),
                "reason": reason,
                "source_file": source_file,
                "trigger": trigger,
                "context_override": context_override or {},
            }
        )
        return {"job_id": f"summary_task_{self._counter:03d}", "status": "queued", "created_new": True}


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

    document_parser._document_parser = None
    ks._knowledge_service = None
    system_profile_service._system_profile_service = None
    profile_summary_module._profile_summary_service = None

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


def test_knowledge_import_accepts_doc_type_and_persists_metadata(client):
    manager = _seed_user("kmgr_doc_type", "pwd123", ["manager"])
    token = _login(client, "kmgr_doc_type", "pwd123")
    _seed_system("HOP", "sys_hop", owner_id=manager["id"])

    response = client.post(
        "/api/v1/knowledge/imports",
        data={
            "knowledge_type": "document",
            "level": "normal",
            "doc_type": "design",
            "system_id": "sys_hop",
        },
        files={"file": ("design.csv", "字段,说明\nA,系统架构设计".encode("utf-8"), "text/csv")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["imported"] >= 1
    assert payload["failed"] == 0

    store_path = os.path.join(settings.REPORT_DIR, "knowledge_store.json")
    with open(store_path, "r", encoding="utf-8") as fp:
        stored_items = json.load(fp)

    assert stored_items
    assert any((item.get("metadata") or {}).get("doc_type") == "design" for item in stored_items)


def test_knowledge_import_rejects_invalid_doc_type(client):
    manager = _seed_user("kmgr_doc_type_bad", "pwd123", ["manager"])
    token = _login(client, "kmgr_doc_type_bad", "pwd123")

    response = client.post(
        "/api/v1/knowledge/imports",
        data={
            "knowledge_type": "document",
            "level": "normal",
            "doc_type": "invalid_type",
        },
        files={"file": ("design.csv", "字段,说明\nA,系统架构设计".encode("utf-8"), "text/csv")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "KNOW_001"


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


def test_knowledge_import_parse_failure_exposes_reason_in_message(client, monkeypatch):
    _seed_user("kmgr7", "pwd123", ["manager"])
    token = _login(client, "kmgr7", "pwd123")

    service = ks.get_knowledge_service()

    def broken_parse(*_args, **_kwargs):
        raise RuntimeError("旧格式解析工具不可用：aspose-words 未安装或不可导入")

    monkeypatch.setattr(service.document_parser, "parse", broken_parse)

    response = client.post(
        "/api/v1/knowledge/imports",
        data={"knowledge_type": "document", "level": "normal"},
        files={"file": ("legacy.xls", b"fake-content", "application/vnd.ms-excel")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error_code"] == "KNOW_002"
    assert "aspose-words 未安装或不可导入" in str(payload.get("message") or "")


def test_knowledge_import_accepts_legacy_doc(client, monkeypatch):
    manager = _seed_user("kmgr_doc_import", "pwd123", ["manager"])
    token = _login(client, "kmgr_doc_import", "pwd123")
    _seed_system("HOP", "sys_hop", owner_id=manager["id"])

    service = ks.get_knowledge_service()
    monkeypatch.setattr(service.document_parser, "parse", lambda **_kwargs: {"text": "老式Word系统说明正文"})

    response = client.post(
        "/api/v1/knowledge/imports",
        data={
            "knowledge_type": "document",
            "level": "normal",
            "system_id": "sys_hop",
        },
        files={"file": ("legacy.doc", b"fake-doc-content", "application/msword")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["imported"] >= 1


def test_knowledge_import_passes_cleaned_document_text_to_summary_job(client, monkeypatch):
    manager = _seed_user("kmgr_full_text", "pwd123", ["manager"])
    token = _login(client, "kmgr_full_text", "pwd123")
    _seed_system("HOP", "sys_hop", owner_id=manager["id"])

    summary_stub = StubProfileSummaryService()
    monkeypatch.setattr(profile_summary_module, "get_profile_summary_service", lambda: summary_stub)

    service = ks.get_knowledge_service()
    toc_text = "技术方案建议书\n目 录\n第一章 引言 5\n1.1 编写目的 5\n第四章 集成设计\n提供贷款核算查询接口，对接核心系统。"
    monkeypatch.setattr(service.document_parser, "parse", lambda **_kwargs: {"text": toc_text})
    monkeypatch.setattr(service, "_chunk_text", lambda _text: ["第四章 集成设计", "提供贷款核算查询接口，对接核心系统。"])

    response = client.post(
        "/api/v1/knowledge/imports",
        data={
            "knowledge_type": "document",
            "level": "normal",
            "system_id": "sys_hop",
        },
        files={"file": ("spec.csv", b"ignored", "text/csv")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert len(summary_stub.calls) == 1
    cleaned_text = summary_stub.calls[0]["context_override"]["document_text"]
    assert "提供贷款核算查询接口" in cleaned_text
    assert "目 录" not in cleaned_text
    assert "第一章 引言 5" not in cleaned_text
