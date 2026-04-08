import os
import sys
import threading
from typing import Any, Dict, List
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from docx import Document

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.app import app
from backend.api import system_routes
from backend.config.config import settings
from backend.service import document_parser
from backend.service import document_skill_adapter
from backend.service import knowledge_service as ks
from backend.service import memory_service
from backend.service import profile_summary_service as profile_summary_module
from backend.service import runtime_execution_service
from backend.service import system_profile_service
from backend.service import user_service


class DummyEmbeddingService:
    def generate_embedding(self, text):
        return [1.0, 0.0, 0.0]

    def batch_generate_embeddings(self, texts, batch_size=25):
        return [[1.0, 0.0, 0.0] for _ in texts]


class StubProfileSummaryService:
    def __init__(self) -> None:
        self.calls: List[Dict[str, Any]] = []
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
        job_id = f"summary_task_{self._counter:03d}"
        self.calls.append(
            {
                "job_id": job_id,
                "system_id": system_id,
                "system_name": system_name,
                "reason": reason,
                "source_file": source_file,
                "trigger": trigger,
                "actor_id": (actor or {}).get("id"),
                "context_override": context_override or {},
            }
        )
        system_profile_service.get_system_profile_service().upsert_extraction_task(
            system_id,
            task_id=job_id,
            status="pending",
            trigger=str(trigger or "document_import"),
            source_file=str(source_file or ""),
        )
        return {"job_id": job_id, "status": "queued", "created_new": True}


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
    document_skill_adapter._document_skill_adapter = None
    ks._knowledge_service = None
    system_profile_service._system_profile_service = None
    profile_summary_module._profile_summary_service = None
    memory_service._memory_service = None
    runtime_execution_service._runtime_execution_service = None

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


def _receive_json_with_timeout(websocket, timeout: float = 3.0):
    result: Dict[str, Any] = {}
    error: Dict[str, Exception] = {}

    def _reader():
        try:
            result["payload"] = websocket.receive_json()
        except Exception as exc:  # pragma: no cover - raised back to main thread
            error["exc"] = exc

    reader = threading.Thread(target=_reader, daemon=True)
    reader.start()
    reader.join(timeout=timeout)
    if reader.is_alive():
        raise AssertionError("websocket receive timeout")
    if "exc" in error:
        raise error["exc"]
    return result["payload"]


def _build_docx_bytes(*paragraphs: str) -> bytes:
    document = Document()
    for paragraph in paragraphs:
        document.add_paragraph(paragraph)
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def test_profile_import_success_returns_task_id_and_records_history(client, monkeypatch):
    manager = _seed_user("import_owner", "pwd123", ["manager"])
    token = _login(client, "import_owner", "pwd123")
    _seed_system("HOP", "sys_hop", owner_id=manager["id"])

    summary_stub = StubProfileSummaryService()
    monkeypatch.setattr(profile_summary_module, "get_profile_summary_service", lambda: summary_stub)

    response = client.post(
        "/api/v1/system-profiles/sys_hop/profile/import",
        data={"doc_type": "requirements"},
        files={"file": ("requirements.csv", "字段,说明\nA,账户系统边界".encode("utf-8"), "text/csv")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["import_result"]["status"] == "success"
    assert payload["import_result"]["file_name"] == "requirements.csv"
    assert payload["import_result"]["failure_reason"] is None
    assert payload["extraction_task_id"] == "summary_task_001"

    history = client.get(
        "/api/v1/system-profiles/sys_hop/profile/import-history",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert history.status_code == 200
    history_payload = history.json()
    assert history_payload["total"] == 1
    item = history_payload["items"][0]
    assert item["doc_type"] == "requirements"
    assert item["file_name"] == "requirements.csv"
    assert item["status"] == "success"
    assert item["failure_reason"] is None
    assert item["operator_id"] == manager["id"]

    status = client.get(
        "/api/v1/system-profiles/sys_hop/profile/extraction-status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert status.status_code == 200
    status_payload = status.json()
    assert status_payload["task_id"] == "summary_task_001"
    assert status_payload["status"] == "pending"
    assert status_payload["trigger"] == "document_import"
    assert status_payload["error"] is None
    assert isinstance(status_payload["notifications"], list)


def test_v27_profile_import_uses_runtime_and_execution_status_aliases(client, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_V27_PROFILE_SCHEMA", True)
    monkeypatch.setattr(settings, "ENABLE_V27_RUNTIME", True)
    monkeypatch.setattr(settings, "KNOWLEDGE_ENABLED", False)

    manager = _seed_user("import_v27_owner", "pwd123", ["manager"])
    token = _login(client, "import_v27_owner", "pwd123")
    _seed_system("PAY", "sys_pay", owner_id=manager["id"])

    response = client.post(
        "/api/v1/system-profiles/sys_pay/profile/import",
        data={"doc_type": "requirements"},
        files={
            "file": (
                "requirements.docx",
                _build_docx_bytes("需求概述", "支付统一受理系统", "核心边界与服务对象"),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["scene_id"] == "pm_document_ingest"
    assert payload["result_status"] == "queued"
    assert payload["execution_id"].startswith("exec_")

    status_response = client.get(
        "/api/v1/system-profiles/sys_pay/profile/execution-status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert status_response.status_code == 200
    status_payload = status_response.json()
    assert status_payload["execution_id"] == payload["execution_id"]
    assert status_payload["scene_id"] == "pm_document_ingest"
    assert status_payload["status"] == "completed"
    assert status_payload["skill_chain"] == ["requirements_skill"]

    compat_status = client.get(
        "/api/v1/system-profiles/sys_pay/profile/extraction-status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert compat_status.status_code == 200
    assert compat_status.json()["execution_id"] == payload["execution_id"]

    history = client.get(
        "/api/v1/system-profiles/sys_pay/profile/import-history",
        headers={"Authorization": f"Bearer {token}"},
    )
    history_item = history.json()["items"][0]
    assert history_item["doc_type"] == "requirements"
    assert history_item["execution_id"] == payload["execution_id"]


def test_v27_profile_import_rejects_removed_doc_types(client, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_V27_RUNTIME", True)

    manager = _seed_user("import_v27_reject", "pwd123", ["manager"])
    token = _login(client, "import_v27_reject", "pwd123")
    _seed_system("PAY", "sys_pay2", owner_id=manager["id"])

    response = client.post(
        "/api/v1/system-profiles/sys_pay2/profile/import",
        data={"doc_type": "history_report"},
        files={"file": ("history.docx", _build_docx_bytes("旧报告"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "PROFILE_IMPORT_FAILED"


def test_v27_tech_solution_import_filters_toc_and_generates_multidomain_suggestions(client, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_V27_PROFILE_SCHEMA", True)
    monkeypatch.setattr(settings, "ENABLE_V27_RUNTIME", True)
    monkeypatch.setattr(settings, "KNOWLEDGE_ENABLED", False)

    manager = _seed_user("import_v27_tech", "pwd123", ["manager"])
    token = _login(client, "import_v27_tech", "pwd123")
    _seed_system("PAY", "sys_pay_tech", owner_id=manager["id"])

    response = client.post(
        "/api/v1/system-profiles/sys_pay_tech/profile/import",
        data={"doc_type": "tech_solution"},
        files={
            "file": (
                "tech_solution.docx",
                _build_docx_bytes(
                    "上海华瑞银行贷款核算项目 技术方案建议书",
                    "目 录",
                    "第一章 引言 5",
                    "1.1 编写目的 5",
                    "第二章 现状分析 9",
                    "第三章 数据分析 11",
                    "第四章 集成设计",
                    "提供贷款核算查询接口，对接核心系统和数据仓库。",
                    "第五章 技术架构",
                    "系统采用分层微服务架构，生产环境双活部署。",
                    "技术栈包括 Java、Spring Boot、Redis、MySQL。",
                    "第六章 约束与风险",
                    "批量窗口紧张，依赖核心系统日终处理时点。",
                ),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

    profile = system_profile_service.get_system_profile_service().get_profile("PAY")
    suggestions = (profile or {}).get("ai_suggestions") or {}

    assert "integration_interfaces.canonical.other_integrations" in suggestions
    assert "technical_architecture.canonical.architecture_style" in suggestions
    assert "technical_architecture.canonical.tech_stack" in suggestions
    assert "constraints_risks.canonical.known_risks" in suggestions

    integration_items = suggestions["integration_interfaces.canonical.other_integrations"]["value"]
    assert any("核心系统" in item for item in integration_items)

    architecture_style = suggestions["technical_architecture.canonical.architecture_style"]["value"]
    assert "分层微服务架构" in architecture_style

    tech_stack = suggestions["technical_architecture.canonical.tech_stack"]["value"]
    assert "Java" in tech_stack["languages"]
    assert "Spring Boot" in tech_stack["frameworks"]
    assert "MySQL" in tech_stack["databases"]
    assert "Redis" in tech_stack["middleware"]

    risks = suggestions["constraints_risks.canonical.known_risks"]["value"]
    assert any("批量窗口紧张" in item for item in risks)
    assert all("目 录" not in item for item in risks)
    assert all("第一章 引言 5" not in item for item in risks)


def test_v27_flat_document_suggestion_accept_updates_canonical_field(client, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_V27_PROFILE_SCHEMA", True)
    monkeypatch.setattr(settings, "ENABLE_V27_RUNTIME", True)
    monkeypatch.setattr(settings, "KNOWLEDGE_ENABLED", False)

    manager = _seed_user("accept_v27_doc_owner", "pwd123", ["manager"])
    token = _login(client, "accept_v27_doc_owner", "pwd123")
    _seed_system("PAY", "sys_pay_accept_doc", owner_id=manager["id"])

    import_response = client.post(
        "/api/v1/system-profiles/sys_pay_accept_doc/profile/import",
        data={"doc_type": "tech_solution"},
        files={
            "file": (
                "tech_solution.docx",
                _build_docx_bytes(
                    "技术方案",
                    "第五章 技术架构",
                    "系统采用分层微服务架构，生产环境双活部署。",
                    "第六章 约束与风险",
                    "批量窗口紧张。",
                ),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert import_response.status_code == 200

    accept_response = client.post(
        "/api/v1/system-profiles/sys_pay_accept_doc/profile/suggestions/accept",
        json={"domain": "technical_architecture", "sub_field": "architecture_style"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert accept_response.status_code == 200
    payload = accept_response.json()["data"]
    assert payload["profile_data"]["technical_architecture"]["canonical"]["architecture_style"] == "系统采用分层微服务架构，生产环境双活部署。"


def test_v27_flat_document_suggestion_ignore_persists_real_ignored_value(client, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_V27_PROFILE_SCHEMA", True)
    monkeypatch.setattr(settings, "ENABLE_V27_RUNTIME", True)
    monkeypatch.setattr(settings, "KNOWLEDGE_ENABLED", False)

    manager = _seed_user("ignore_v27_doc_owner", "pwd123", ["manager"])
    token = _login(client, "ignore_v27_doc_owner", "pwd123")
    _seed_system("PAY", "sys_pay_ignore_doc", owner_id=manager["id"])

    import_response = client.post(
        "/api/v1/system-profiles/sys_pay_ignore_doc/profile/import",
        data={"doc_type": "tech_solution"},
        files={
            "file": (
                "tech_solution.docx",
                _build_docx_bytes(
                    "技术方案",
                    "第六章 约束与风险",
                    "批量窗口紧张，依赖核心系统日终处理时点。",
                ),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert import_response.status_code == 200

    ignore_response = client.post(
        "/api/v1/system-profiles/sys_pay_ignore_doc/profile/suggestions/ignore",
        json={"domain": "constraints_risks", "sub_field": "known_risks"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert ignore_response.status_code == 200
    payload = ignore_response.json()["data"]
    ignored_risks = payload["ai_suggestion_ignored"]["constraints_risks.known_risks"]
    assert any("批量窗口紧张" in item for item in ignored_risks)
    assert any("核心系统日终处理时点" in item for item in ignored_risks)


def test_v27_retry_replays_runtime_snapshot_for_supported_imports(client, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_V27_PROFILE_SCHEMA", True)
    monkeypatch.setattr(settings, "ENABLE_V27_RUNTIME", True)
    monkeypatch.setattr(settings, "KNOWLEDGE_ENABLED", False)

    manager = _seed_user("retry_v27_owner", "pwd123", ["manager"])
    token = _login(client, "retry_v27_owner", "pwd123")
    _seed_system("PAY", "sys_pay_retry", owner_id=manager["id"])

    import_response = client.post(
        "/api/v1/system-profiles/sys_pay_retry/profile/import",
        data={"doc_type": "tech_solution"},
        files={
            "file": (
                "tech_solution.docx",
                _build_docx_bytes(
                    "技术方案",
                    "第四章 集成设计",
                    "提供贷款核算查询接口，对接核心系统。",
                    "第五章 技术架构",
                    "系统采用分层架构。",
                    "第六章 约束与风险",
                    "批量窗口紧张。",
                ),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert import_response.status_code == 200

    retry_response = client.post(
        "/api/v1/system-profiles/sys_pay_retry/ai-suggestions/retry",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert retry_response.status_code == 200
    retry_payload = retry_response.json()
    assert retry_payload["status"] == "completed"
    assert retry_payload["message"] == "已重新生成 AI 建议"
    assert retry_payload["execution_id"].startswith("exec_")

    latest_execution = runtime_execution_service.get_runtime_execution_service().get_latest_execution("sys_pay_retry")
    assert latest_execution["execution_id"] == retry_payload["execution_id"]


def test_v27_retry_rejects_historical_import_without_runtime_snapshot(client, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_V27_PROFILE_SCHEMA", True)
    monkeypatch.setattr(settings, "ENABLE_V27_RUNTIME", True)
    monkeypatch.setattr(settings, "KNOWLEDGE_ENABLED", False)

    manager = _seed_user("retry_v27_legacy", "pwd123", ["manager"])
    token = _login(client, "retry_v27_legacy", "pwd123")
    _seed_system("PAY", "sys_pay_retry_legacy", owner_id=manager["id"])

    profile_service = system_profile_service.get_system_profile_service()
    profile_service.ensure_profile("PAY", system_id="sys_pay_retry_legacy", actor=manager)

    execution_service = runtime_execution_service.get_runtime_execution_service()
    execution = execution_service.create_execution(
        scene_id="pm_document_ingest",
        system_id="sys_pay_retry_legacy",
        source_type="document",
        source_file="legacy.docx",
        skill_chain=["tech_solution_skill"],
    )
    execution_service.update_execution(
        execution["execution_id"],
        status="completed",
        result_summary={"updated_system_ids": ["sys_pay_retry_legacy"], "skipped_items": []},
        policy_results=[],
    )
    profile_service.record_import_history(
        "sys_pay_retry_legacy",
        doc_type="tech_solution",
        file_name="legacy.docx",
        status="success",
        operator_id=manager["id"],
        execution_id=execution["execution_id"],
    )

    retry_response = client.post(
        "/api/v1/system-profiles/sys_pay_retry_legacy/ai-suggestions/retry",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert retry_response.status_code == 400
    assert retry_response.json()["error_code"] == "PROFILE_RETRY_NOT_SUPPORTED"
    assert retry_response.json()["message"] == "当前历史导入记录不支持自动重跑，请重新上传文档"


def test_v27_profile_memory_query_supports_filters(client, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_V27_PROFILE_SCHEMA", True)
    monkeypatch.setattr(settings, "ENABLE_V27_RUNTIME", True)

    manager = _seed_user("memory_query_owner", "pwd123", ["manager"])
    token = _login(client, "memory_query_owner", "pwd123")
    _seed_system("PAY", "sys_pay_memory", owner_id=manager["id"])

    service = memory_service.get_memory_service()
    service.append_record(
        system_id="sys_pay_memory",
        memory_type="profile_update",
        memory_subtype="document_suggestion",
        scene_id="pm_document_ingest",
        source_type="document",
        source_id="exec_doc_001",
        summary="需求文档导入生成建议",
        payload={"changed_fields": ["system_positioning.canonical.service_scope"]},
        decision_policy="suggestion_only",
        confidence=0.7,
        actor="memory_query_owner",
    )
    service.append_record(
        system_id="sys_pay_memory",
        memory_type="function_point_adjustment",
        memory_subtype="task_feature_update",
        scene_id="feature_breakdown",
        source_type="task",
        source_id="task_001",
        summary="PM 合并功能点",
        payload={"adjustment_type": "merge"},
        decision_policy="manual",
        confidence=1,
        actor="memory_query_owner",
    )

    response = client.get(
        "/api/v1/system-profiles/sys_pay_memory/memory",
        params={"memory_type": "profile_update", "scene_id": "pm_document_ingest"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["memory_type"] == "profile_update"
    assert payload["items"][0]["memory_subtype"] == "document_suggestion"


def test_profile_import_passes_full_document_text_to_summary_job(client, monkeypatch):
    manager = _seed_user("import_full_text", "pwd123", ["manager"])
    token = _login(client, "import_full_text", "pwd123")
    _seed_system("HOP", "sys_hop", owner_id=manager["id"])

    summary_stub = StubProfileSummaryService()
    monkeypatch.setattr(profile_summary_module, "get_profile_summary_service", lambda: summary_stub)

    service = ks.get_knowledge_service()
    full_text = "需求概述\n系统边界\n接口清单"
    monkeypatch.setattr(service.document_parser, "parse", lambda **_kwargs: {"text": full_text})
    monkeypatch.setattr(service, "_chunk_text", lambda _text: ["需求概述", "系统边界"])

    response = client.post(
        "/api/v1/system-profiles/sys_hop/profile/import",
        data={"doc_type": "requirements"},
        files={"file": ("requirements.csv", b"ignored", "text/csv")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert len(summary_stub.calls) == 1
    assert summary_stub.calls[0]["context_override"]["document_text"] == full_text


def test_profile_import_history_supports_pagination(client, monkeypatch):
    manager = _seed_user("import_owner_page", "pwd123", ["manager"])
    token = _login(client, "import_owner_page", "pwd123")
    _seed_system("HOP", "sys_hop", owner_id=manager["id"])

    summary_stub = StubProfileSummaryService()
    monkeypatch.setattr(profile_summary_module, "get_profile_summary_service", lambda: summary_stub)

    first = client.post(
        "/api/v1/system-profiles/sys_hop/profile/import",
        data={"doc_type": "requirements"},
        files={"file": ("r1.csv", "字段,说明\nA,需求".encode("utf-8"), "text/csv")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert first.status_code == 200

    second = client.post(
        "/api/v1/system-profiles/sys_hop/profile/import",
        data={"doc_type": "design"},
        files={"file": ("d1.csv", "字段,说明\nA,设计".encode("utf-8"), "text/csv")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert second.status_code == 200

    page_1 = client.get(
        "/api/v1/system-profiles/sys_hop/profile/import-history",
        params={"limit": 1, "offset": 0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert page_1.status_code == 200
    payload_1 = page_1.json()
    assert payload_1["total"] == 2
    assert len(payload_1["items"]) == 1

    page_2 = client.get(
        "/api/v1/system-profiles/sys_hop/profile/import-history",
        params={"limit": 1, "offset": 1},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert page_2.status_code == 200
    payload_2 = page_2.json()
    assert payload_2["total"] == 2
    assert len(payload_2["items"]) == 1
    assert payload_1["items"][0]["id"] != payload_2["items"][0]["id"]


def test_profile_import_requires_owner_or_backup_permission(client):
    owner = _seed_user("import_owner_acl", "pwd123", ["manager"])
    other = _seed_user("import_other_acl", "pwd123", ["manager"])
    owner_token = _login(client, "import_owner_acl", "pwd123")
    other_token = _login(client, "import_other_acl", "pwd123")
    _seed_system("HOP", "sys_hop", owner_id=owner["id"])

    denied = client.post(
        "/api/v1/system-profiles/sys_hop/profile/import",
        data={"doc_type": "requirements"},
        files={"file": ("requirements.csv", "字段,说明\nA,账户系统边界".encode("utf-8"), "text/csv")},
        headers={"Authorization": f"Bearer {other_token}", "X-Request-ID": "req_import_denied"},
    )
    assert denied.status_code == 403
    denied_payload = denied.json()
    assert denied_payload["error_code"] == "permission_denied"
    assert denied_payload["request_id"] == "req_import_denied"

    allowed = client.post(
        "/api/v1/system-profiles/sys_hop/profile/import",
        data={"doc_type": "requirements"},
        files={"file": ("requirements.csv", "字段,说明\nA,账户系统边界".encode("utf-8"), "text/csv")},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert allowed.status_code == 200


def test_profile_import_accepts_v27_doc_type_canonical_values(client, monkeypatch):
    manager = _seed_user("import_doc_type_alias", "pwd123", ["manager"])
    token = _login(client, "import_doc_type_alias", "pwd123")
    _seed_system("HOP", "sys_hop", owner_id=manager["id"])

    summary_stub = StubProfileSummaryService()
    monkeypatch.setattr(profile_summary_module, "get_profile_summary_service", lambda: summary_stub)

    response = client.post(
        "/api/v1/system-profiles/sys_hop/profile/import",
        data={"doc_type": "tech_solution"},
        files={"file": ("tech.csv", "字段,说明\nA,技术方案".encode("utf-8"), "text/csv")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["import_result"]["status"] == "success"

    history = client.get(
        "/api/v1/system-profiles/sys_hop/profile/import-history",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert history.status_code == 200
    history_payload = history.json()
    assert history_payload["total"] == 1
    assert history_payload["items"][0]["doc_type"] == "tech_solution"


def test_profile_import_rejects_invalid_doc_type(client):
    manager = _seed_user("import_invalid_doc_type", "pwd123", ["manager"])
    token = _login(client, "import_invalid_doc_type", "pwd123")
    _seed_system("HOP", "sys_hop", owner_id=manager["id"])

    response = client.post(
        "/api/v1/system-profiles/sys_hop/profile/import",
        data={"doc_type": "bad_doc_type"},
        files={"file": ("requirements.csv", "字段,说明\nA,账户系统边界".encode("utf-8"), "text/csv")},
        headers={"Authorization": f"Bearer {token}", "X-Request-ID": "req_import_bad_doc_type"},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error_code"] == "PROFILE_IMPORT_FAILED"
    assert payload["request_id"] == "req_import_bad_doc_type"


def test_profile_template_download_rejects_removed_types_on_main_and_alias_paths(client):
    manager = _seed_user("template_owner", "pwd123", ["manager"])
    token = _login(client, "template_owner", "pwd123")
    _seed_system("HOP", "sys_hop", owner_id=manager["id"])

    main_response = client.get(
        "/api/v1/system-profiles/template/history_report",
        headers={"Authorization": f"Bearer {token}", "X-Request-ID": "req_template_removed_main"},
    )
    assert main_response.status_code == 400
    assert main_response.json()["error_code"] == "TEMPLATE_TYPE_INVALID"
    assert main_response.json()["request_id"] == "req_template_removed_main"

    alias_response = client.get(
        "/api/system-profile/template/esb_document",
        headers={"Authorization": f"Bearer {token}", "X-Request-ID": "req_template_removed_alias"},
    )
    assert alias_response.status_code == 400
    assert alias_response.json()["error_code"] == "TEMPLATE_TYPE_INVALID"
    assert alias_response.json()["request_id"] == "req_template_removed_alias"


def test_profile_template_download_rejects_invalid_type(client):
    manager = _seed_user("template_invalid", "pwd123", ["manager"])
    token = _login(client, "template_invalid", "pwd123")

    response = client.get(
        "/api/v1/system-profiles/template/unknown",
        headers={"Authorization": f"Bearer {token}", "X-Request-ID": "req_template_invalid"},
    )
    assert response.status_code == 400
    payload = response.json()
    assert payload["error_code"] == "TEMPLATE_TYPE_INVALID"
    assert payload["request_id"] == "req_template_invalid"


def test_profile_task_status_by_task_id_supports_alias_and_state_mapping(client):
    manager = _seed_user("task_status_owner", "pwd123", ["manager"])
    token = _login(client, "task_status_owner", "pwd123")
    _seed_system("HOP", "sys_hop", owner_id=manager["id"])

    service = system_profile_service.get_system_profile_service()
    service.upsert_extraction_task(
        "sys_hop",
        task_id="summary_task_001",
        status="pending",
        trigger="document_import",
    )

    started_response = client.get(
        "/api/v1/system-profiles/task-status/summary_task_001",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert started_response.status_code == 200
    started_payload = started_response.json()
    assert started_payload["task_id"] == "summary_task_001"
    assert started_payload["status"] == "extraction_started"
    assert started_payload["system_name"] == "HOP"

    service.update_extraction_task_status(
        "sys_hop",
        task_id="summary_task_001",
        status="completed",
    )

    completed_response = client.get(
        "/api/system-profile/task-status/summary_task_001",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert completed_response.status_code == 200
    completed_payload = completed_response.json()
    assert completed_payload["status"] == "extraction_completed"


def test_profile_task_status_by_task_id_returns_404_when_missing(client):
    manager = _seed_user("task_status_missing", "pwd123", ["manager"])
    token = _login(client, "task_status_missing", "pwd123")

    response = client.get(
        "/api/v1/system-profiles/task-status/task_not_exists",
        headers={"Authorization": f"Bearer {token}", "X-Request-ID": "req_task_missing"},
    )
    assert response.status_code == 404
    payload = response.json()
    assert payload["error_code"] == "TASK_NOT_FOUND"
    assert payload["request_id"] == "req_task_missing"


def test_profile_task_websocket_ping_pong_and_status_push(client):
    manager = _seed_user("ws_owner", "pwd123", ["manager"])
    token = _login(client, "ws_owner", "pwd123")
    _seed_system("HOP", "sys_hop", owner_id=manager["id"])

    with client.websocket_connect(f"/ws/system-profile/HOP?token={token}") as websocket:
        websocket.send_json({"event": "ping"})
        pong_payload = _receive_json_with_timeout(websocket)
        assert pong_payload["event"] == "pong"
        assert pong_payload["system_name"] == "HOP"

        service = system_profile_service.get_system_profile_service()
        service.upsert_extraction_task(
            "sys_hop",
            task_id="summary_task_ws",
            status="pending",
            trigger="document_import",
        )
        started_payload = _receive_json_with_timeout(websocket)
        assert started_payload["task_id"] == "summary_task_ws"
        assert started_payload["status"] == "extraction_started"
        assert started_payload["system_name"] == "HOP"

        service.update_extraction_task_status(
            "sys_hop",
            task_id="summary_task_ws",
            status="completed",
        )
        completed_payload = _receive_json_with_timeout(websocket)
        assert completed_payload["task_id"] == "summary_task_ws"
        assert completed_payload["status"] == "extraction_completed"


def test_profile_task_websocket_requires_manager_role(client):
    admin = _seed_user("ws_admin", "pwd123", ["admin"])
    token = _login(client, "ws_admin", "pwd123")

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/ws/system-profile/HOP?token={token}"):
            pass
