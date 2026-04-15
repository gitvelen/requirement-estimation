import os
import sys
import threading
import json
from datetime import datetime
from typing import Any, Dict, List
from io import BytesIO
from pathlib import Path

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
from backend.service import profile_artifact_service
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
        style = None
        text = paragraph
        if isinstance(paragraph, tuple):
            text, style = paragraph
        para = document.add_paragraph(text)
        if style:
            para.style = style
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def _assert_iso_has_timezone(value: str) -> None:
    parsed = datetime.fromisoformat(value)
    assert parsed.tzinfo is not None
    assert parsed.utcoffset() is not None


def test_merge_candidate_records_prefers_latest_document_candidate_for_same_file():
    service = system_profile_service.SystemProfileService.__new__(system_profile_service.SystemProfileService)

    legacy_record = {
        "artifact_id": "candidate_old",
        "source_artifact_id": "raw_old",
        "category": "documents",
        "created_at": "2026-04-13T10:00:00+08:00",
        "payload": {
            "doc_type": "tech_solution",
            "file_name": "贷款核算系统技术方案建议书v2.0.docx",
            "field_candidates": {
                "business_capabilities.canonical.functional_modules": {
                    "value": [
                        "通过零售贷款核心系统提供贷款生命周期相关完整的功能",
                        "系统采用组件化的模块设计方式和插件化的处理方式",
                    ],
                    "confidence": 0.82,
                    "reason": "legacy_bad_parse",
                },
                "technical_architecture.canonical.architecture_style": {
                    "value": "整体架构图",
                    "confidence": 0.82,
                    "reason": "legacy_bad_parse",
                },
                "technical_architecture.canonical.performance_baseline": {
                    "value": {
                        "batch": {"window": "批量服务功能：主要实现增量信息加载、增量信息导出等功能"},
                        "processing_model": "在线",
                    },
                    "confidence": 0.82,
                    "reason": "legacy_bad_parse",
                },
            },
        },
    }
    latest_record = {
        "artifact_id": "candidate_new",
        "source_artifact_id": "raw_new",
        "category": "documents",
        "created_at": "2026-04-13T16:00:00+08:00",
        "payload": {
            "doc_type": "tech_solution",
            "file_name": "贷款核算系统技术方案建议书v2.0.docx",
            "field_candidates": {
                "business_capabilities.canonical.functional_modules": {
                    "value": [
                        "产品工厂",
                        "贷款开户",
                        "贷款发放",
                        "日终批量处理",
                    ],
                    "confidence": 0.82,
                    "reason": "latest_good_parse",
                },
                "technical_architecture.canonical.architecture_style": {
                    "value": "服务采用分布式集群部署方式，每台应用服务器均部署相同的功能模块，且互为备份。",
                    "confidence": 0.82,
                    "reason": "latest_good_parse",
                },
            },
        },
    }

    merged = service._merge_candidate_records([legacy_record, latest_record])

    functional_modules = merged["business_capabilities.canonical.functional_modules"]
    assert functional_modules["selected_value"] == [
        "产品工厂",
        "贷款开户",
        "贷款发放",
        "日终批量处理",
    ]
    assert [item["candidate_artifact_id"] for item in functional_modules["candidate_items"]] == ["candidate_new"]

    architecture_style = merged["technical_architecture.canonical.architecture_style"]
    assert architecture_style["selected_value"] == "服务采用分布式集群部署方式，每台应用服务器均部署相同的功能模块，且互为备份。"
    assert [item["candidate_artifact_id"] for item in architecture_style["candidate_items"]] == ["candidate_new"]
    assert "technical_architecture.canonical.performance_baseline" not in merged


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
    _assert_iso_has_timezone(item["imported_at"])

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
    _assert_iso_has_timezone(status_payload["created_at"])


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
    _assert_iso_has_timezone(status_payload["created_at"])
    _assert_iso_has_timezone(status_payload["completed_at"])

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


def test_v27_profile_import_writes_document_candidate_bundle_and_latest_projection_under_system_workspace(client, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_V27_PROFILE_SCHEMA", True)
    monkeypatch.setattr(settings, "ENABLE_V27_RUNTIME", True)
    monkeypatch.setattr(settings, "KNOWLEDGE_ENABLED", False)

    manager = _seed_user("import_v27_bundle_owner", "pwd123", ["manager"])
    token = _login(client, "import_v27_bundle_owner", "pwd123")
    _seed_system("PAY", "sys_pay_bundle", owner_id=manager["id"])

    response = client.post(
        "/api/v1/system-profiles/sys_pay_bundle/profile/import",
        data={"doc_type": "tech_solution"},
        files={
            "file": (
                "tech_solution.docx",
                _build_docx_bytes(
                    "技术方案",
                    "提供支付受理服务，并对接核心账务系统。",
                    "系统采用分层微服务架构，技术栈包括 Java、Redis、MySQL。",
                    "风险：批量窗口紧张，依赖核心账务日终时点。",
                ),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

    system_roots = list((Path(settings.REPORT_DIR) / "system_profiles").glob("sid_*__PAY"))
    assert len(system_roots) == 1
    workspace = system_roots[0]

    source_dirs = list((workspace / "source" / "documents").glob("src_doc_*"))
    assert len(source_dirs) == 1
    source_dir = source_dirs[0]
    assert (source_dir / "raw.bin").exists()
    assert (source_dir / "meta.json").exists()
    assert (source_dir / "parsed.json").exists()
    assert (source_dir / "chunks.jsonl").exists()

    document_candidate_dirs = list((workspace / "candidate" / "documents").glob("doc_cand_*"))
    assert len(document_candidate_dirs) == 1
    document_candidate_dir = document_candidate_dirs[0]
    assert (document_candidate_dir / "document_candidate.json").exists()
    assert (document_candidate_dir / "source_manifest.json").exists()
    assert (document_candidate_dir / "facts.jsonl").exists()
    assert (document_candidate_dir / "entity_graph.json").exists()
    assert (document_candidate_dir / "profile_projection.json").exists()
    assert (document_candidate_dir / "dossier.json").exists()
    assert (document_candidate_dir / "quality_report.json").exists()
    assert (document_candidate_dir / "review_queue.json").exists()

    latest_candidate_dir = workspace / "candidate" / "latest"
    assert (latest_candidate_dir / "system_projection.json").exists()
    assert (latest_candidate_dir / "merged_candidates.json").exists()
    assert (latest_candidate_dir / "card_render.json").exists()


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
    assert "constraints_risks.canonical.risk_items" in suggestions

    integration_items = suggestions["integration_interfaces.canonical.other_integrations"]["value"]
    assert any("核心系统" in item for item in integration_items)

    architecture_style = suggestions["technical_architecture.canonical.architecture_style"]["value"]
    assert "分层微服务架构" in architecture_style

    tech_stack = suggestions["technical_architecture.canonical.tech_stack"]["value"]
    assert "Java" in tech_stack["languages"]
    assert "Spring Boot" in tech_stack["frameworks"]
    assert "MySQL" in tech_stack["databases"]
    assert "Redis" in tech_stack["middleware"]

    risks = suggestions["constraints_risks.canonical.risk_items"]["value"]
    assert any(item["name"] == "批量窗口紧张" for item in risks)
    assert any("核心系统日终处理时点" in item["impact"] for item in risks)
    assert all("目 录" not in item["name"] for item in risks)
    assert all("第一章 引言 5" not in item["name"] for item in risks)


def test_v27_tech_solution_import_expands_compile_plan_and_generates_d2_candidates(client, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_V27_PROFILE_SCHEMA", True)
    monkeypatch.setattr(settings, "ENABLE_V27_RUNTIME", True)
    monkeypatch.setattr(settings, "KNOWLEDGE_ENABLED", False)

    manager = _seed_user("import_v27_mixed", "pwd123", ["manager"])
    token = _login(client, "import_v27_mixed", "pwd123")
    _seed_system("PAY", "sys_pay_mixed", owner_id=manager["id"])

    response = client.post(
        "/api/v1/system-profiles/sys_pay_mixed/profile/import",
        data={"doc_type": "tech_solution"},
        files={
            "file": (
                "tech_solution.docx",
                _build_docx_bytes(
                    ("业务背景", "Heading 2"),
                    "通过贷款核算系统提供贷款生命周期相关完整的功能，包括放款、还款、计息结息和日终批量处理。",
                    ("需求概述", "Heading 2"),
                    "支持放款、还款、计息和日终批量处理。",
                    ("主要功能说明", "Heading 2"),
                    ("产品工厂", "Heading 3"),
                    ("功能简述", "Heading 4"),
                    "灵活新建和复制现有贷款产品，并对贷款基本信息进行维护。",
                    ("贷款开户", "Heading 3"),
                    ("功能简述", "Heading 4"),
                    "支持一般、特殊等各种类型的贷款开户操作。",
                    ("贷款发放", "Heading 3"),
                    ("功能简述", "Heading 4"),
                    "支持手动放款、渠道调用放款或根据合同约定的放款方式和金额进行自动贷款发放。",
                    ("日终批量处理", "Heading 3"),
                    ("功能简述", "Heading 4"),
                    "根据系统配置的参数处理贷款账户计提、结息、自动扣收和对账文件生成。",
                    ("整体架构", "Heading 2"),
                    "系统采用分层微服务架构。",
                    ("性能分析", "Heading 2"),
                    "系统联机性能分析：预计日交易量20万、交易响应时间1s。",
                    "批量性能分析：批量数据量200万、处理时间半小时。",
                    ("实施风险", "Heading 2"),
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
    assert suggestions["business_capabilities.canonical.functional_modules"]["value"] == [
        {"name": "产品工厂", "description": "灵活新建和复制现有贷款产品，并对贷款基本信息进行维护。"},
        {"name": "贷款开户", "description": "支持一般、特殊等各种类型的贷款开户操作。"},
        {"name": "贷款发放", "description": "支持手动放款、渠道调用放款或根据合同约定的放款方式和金额进行自动贷款发放。"},
        {"name": "日终批量处理", "description": "根据系统配置的参数处理贷款账户计提、结息、自动扣收和对账文件生成。"},
    ]
    scenarios = suggestions["business_capabilities.canonical.business_scenarios"]["value"]
    assert scenarios == [
        {"name": "产品工厂", "description": "灵活新建和复制现有贷款产品，并对贷款基本信息进行维护。"},
        {"name": "贷款开户", "description": "支持一般、特殊等各种类型的贷款开户操作。"},
        {"name": "贷款发放", "description": "支持手动放款、渠道调用放款或根据合同约定的放款方式和金额进行自动贷款发放。"},
        {"name": "日终批量处理", "description": "根据系统配置的参数处理贷款账户计提、结息、自动扣收和对账文件生成。"},
    ]
    flows = suggestions["business_capabilities.canonical.business_flows"]["value"]
    assert any(item["name"] == "贷款发放" for item in flows)
    data_reports = suggestions["business_capabilities.canonical.data_reports"]["value"]
    assert any(item["name"] == "对账文件生成" and item["type"] == "report" for item in data_reports)
    risks = suggestions["constraints_risks.canonical.risk_items"]["value"]
    assert any(item["name"] == "批量窗口紧张" for item in risks)
    assert any("依赖核心系统日终处理时点" in item["impact"] for item in risks)
    performance = suggestions["technical_architecture.canonical.performance_baseline"]["value"]
    assert performance["online"]["p95_latency_ms"] == "1000"

    execution_id = response.json()["execution_id"]
    latest_execution = runtime_execution_service.get_runtime_execution_service().get_execution(execution_id)
    assert latest_execution["input_snapshot"]["compiled_doc_types"] == ["requirements", "design", "tech_solution"]

    artifact_service = profile_artifact_service.get_profile_artifact_service()
    workspace_path = artifact_service.repository.get_workspace_path(system_id="sys_pay_mixed")
    assert workspace_path
    workspace = Path(workspace_path)
    candidate_dirs = list((workspace / "candidate" / "documents").glob("doc_cand_*"))
    assert len(candidate_dirs) == 1
    with open(candidate_dirs[0] / "quality_report.json", "r", encoding="utf-8") as f:
        quality_report = json.load(f)
    assert not any(
        gap["target_field"] == "business_capabilities.canonical.functional_modules"
        for gap in quality_report.get("recognized_section_gaps", [])
    )


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
    assert payload["profile_data"]["technical_architecture"]["canonical"]["architecture_style"] == "分层微服务架构"


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
        json={"domain": "constraints_risks", "sub_field": "risk_items"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert ignore_response.status_code == 200
    payload = ignore_response.json()["data"]
    ignored_risks = payload["ai_suggestion_ignored"]["constraints_risks.canonical.risk_items"]
    assert any(item["name"] == "批量窗口紧张" for item in ignored_risks)
    assert any("核心系统日终处理时点" in item["impact"] for item in ignored_risks)


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


def test_v27_retry_backfills_d2_candidates_from_runtime_snapshot(client, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_V27_PROFILE_SCHEMA", True)
    monkeypatch.setattr(settings, "ENABLE_V27_RUNTIME", True)
    monkeypatch.setattr(settings, "KNOWLEDGE_ENABLED", False)

    manager = _seed_user("retry_v27_backfill", "pwd123", ["manager"])
    token = _login(client, "retry_v27_backfill", "pwd123")
    _seed_system("PAY", "sys_pay_retry_backfill", owner_id=manager["id"])

    profile_service = system_profile_service.get_system_profile_service()
    profile_service.ensure_profile("PAY", system_id="sys_pay_retry_backfill", actor=manager)

    execution_service = runtime_execution_service.get_runtime_execution_service()
    execution = execution_service.create_execution(
        scene_id="pm_document_ingest",
        system_id="sys_pay_retry_backfill",
        source_type="document",
        source_file="tech_solution.docx",
        skill_chain=["tech_solution_skill"],
    )
    execution_service.update_execution(
        execution["execution_id"],
        status="completed",
        result_summary={"updated_system_ids": ["sys_pay_retry_backfill"], "skipped_items": []},
        policy_results=[],
        input_snapshot={
            "snapshot_type": "document_ingest_v1",
            "doc_type": "tech_solution",
            "file_name": "tech_solution.docx",
            "cleaned_text": "\n".join(
                [
                    "业务背景",
                    "通过贷款核算系统提供贷款生命周期相关完整的功能。",
                    "主要功能说明",
                    "产品工厂",
                    "功能简述",
                    "灵活新建和复制现有贷款产品，并对贷款基本信息进行维护。",
                    "贷款开户",
                    "功能简述",
                    "支持一般、特殊等各种类型的贷款开户操作。",
                    "整体架构",
                    "系统采用分层架构。",
                ]
            ),
        },
    )
    profile_service.record_import_history(
        "sys_pay_retry_backfill",
        doc_type="tech_solution",
        file_name="tech_solution.docx",
        status="success",
        operator_id=manager["id"],
        execution_id=execution["execution_id"],
    )

    retry_response = client.post(
        "/api/v1/system-profiles/sys_pay_retry_backfill/ai-suggestions/retry",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert retry_response.status_code == 200
    profile = profile_service.get_profile("PAY")
    suggestions = (profile or {}).get("ai_suggestions") or {}
    assert suggestions["business_capabilities.canonical.functional_modules"]["value"] == [
        {"name": "产品工厂", "description": "灵活新建和复制现有贷款产品，并对贷款基本信息进行维护。"},
        {"name": "贷款开户", "description": "支持一般、特殊等各种类型的贷款开户操作。"},
    ]


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




def test_v27_batch_profile_import_accepts_multiple_files_and_infers_doc_types(client, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_V27_PROFILE_SCHEMA", True)
    monkeypatch.setattr(settings, "ENABLE_V27_RUNTIME", True)
    monkeypatch.setattr(settings, "KNOWLEDGE_ENABLED", False)

    manager = _seed_user("batch_import_owner", "pwd123", ["manager"])
    token = _login(client, "batch_import_owner", "pwd123")
    _seed_system("PAY", "sys_pay_batch", owner_id=manager["id"])

    response = client.post(
        "/api/v1/system-profiles/sys_pay_batch/profile/import-batch",
        files=[
            (
                "files",
                (
                    "requirements.docx",
                    _build_docx_bytes("需求概述", "支付系统服务范围", "负责支付受理"),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                ),
            ),
            (
                "files",
                (
                    "design.docx",
                    _build_docx_bytes("概要设计", "系统采用分层架构", "部署在内网区域"),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                ),
            ),
        ],
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["batch_count"] == 2
    assert payload["success_count"] == 2
    assert payload["failure_count"] == 0
    assert len(payload["results"]) == 2

    history = client.get(
        "/api/v1/system-profiles/sys_pay_batch/profile/import-history",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert history.status_code == 200
    history_payload = history.json()
    assert history_payload["total"] == 2
    doc_types = {item["doc_type"] for item in history_payload["items"]}
    assert doc_types == {"requirements", "design"}
    for item in history_payload["items"]:
        assert item["artifact_refs"]["raw_artifact_id"].startswith("raw_")
        assert item["artifact_refs"]["document_candidate_artifact_id"].startswith("candidate_")
        assert item["artifact_refs"]["projection_artifact_id"].startswith("projection_")
        assert item["artifact_refs"]["output_artifact_id"].startswith("output_")


def test_v27_batch_profile_import_keeps_ambiguous_files_successful(client, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_V27_PROFILE_SCHEMA", True)
    monkeypatch.setattr(settings, "ENABLE_V27_RUNTIME", True)
    monkeypatch.setattr(settings, "KNOWLEDGE_ENABLED", False)

    manager = _seed_user("batch_import_general", "pwd123", ["manager"])
    token = _login(client, "batch_import_general", "pwd123")
    _seed_system("PAY", "sys_pay_general", owner_id=manager["id"])

    response = client.post(
        "/api/v1/system-profiles/sys_pay_general/profile/import-batch",
        files=[
            (
                "files",
                (
                    "notes.docx",
                    _build_docx_bytes(
                        "系统说明",
                        "负责支付受理与渠道服务编排",
                        "系统采用分层架构部署在内网区域",
                        "对接核心系统提供贷款核算查询接口",
                    ),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                ),
            ),
        ],
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["batch_count"] == 1
    assert payload["success_count"] == 1
    assert payload["failure_count"] == 0

    history = client.get(
        "/api/v1/system-profiles/sys_pay_general/profile/import-history",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert history.status_code == 200
    item = history.json()["items"][0]
    assert item["status"] == "success"
    assert item["doc_type"] == "general"
    assert item["failure_reason"] is None


def test_v27_batch_profile_import_uses_bounded_llm_enrichment_settings(client, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_V27_PROFILE_SCHEMA", True)
    monkeypatch.setattr(settings, "ENABLE_V27_RUNTIME", True)
    monkeypatch.setattr(settings, "KNOWLEDGE_ENABLED", False)

    manager = _seed_user("batch_import_timeout", "pwd123", ["manager"])
    token = _login(client, "batch_import_timeout", "pwd123")
    _seed_system("PAY", "sys_pay_timeout", owner_id=manager["id"])

    class TimeoutProfileSummaryService:
        def __init__(self) -> None:
            self.calls: List[Dict[str, Any]] = []

        def _call_llm(self, **kwargs):
            self.calls.append(dict(kwargs))
            raise TimeoutError("Request timed out")

    summary_stub = TimeoutProfileSummaryService()
    monkeypatch.setattr(document_skill_adapter, "get_profile_summary_service", lambda: summary_stub)

    response = client.post(
        "/api/v1/system-profiles/sys_pay_timeout/profile/import-batch",
        files=[
            (
                "files",
                (
                    "loan-accounting-tech-solution.docx",
                    _build_docx_bytes(
                        "技术方案建议书",
                        "4.6 主要功能说明",
                        "贷款核算系统负责贷款试算、放款、还款计划生成、账务核对。",
                        "系统提供贷款核算查询服务，并依赖核心账务日终处理。",
                    ),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                ),
            ),
        ],
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success_count"] == 1
    assert payload["failure_count"] == 0
    assert summary_stub.calls
    assert summary_stub.calls[0]["llm_timeout"] == 5
    assert summary_stub.calls[0]["llm_retry_times"] == 1
    assert summary_stub.calls[0]["allow_chunking"] is False
