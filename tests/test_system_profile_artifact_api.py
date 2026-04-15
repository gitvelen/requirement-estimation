from __future__ import annotations

import json
import os
import sys
import threading
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List

from docx import Document
from fastapi.testclient import TestClient

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.app import app
from backend.api import system_routes
from backend.config.config import settings
from backend.service import document_parser
from backend.service import document_skill_adapter
from backend.service import knowledge_service
from backend.service import memory_service
from backend.service import profile_health_service
from backend.service import profile_artifact_service
from backend.service import runtime_execution_service
from backend.service import system_profile_service
from backend.service import user_service


class DummyEmbeddingService:
    def generate_embedding(self, text):
        return [1.0, 0.0, 0.0]

    def batch_generate_embeddings(self, texts, batch_size=25):
        return [[1.0, 0.0, 0.0] for _ in texts]


class DummyVectorStore:
    def insert_knowledge(self, **kwargs):
        return {"id": "knowledge_001"}


class DummyKnowledgeService:
    def __init__(self) -> None:
        self.embedding_service = DummyEmbeddingService()
        self.vector_store = DummyVectorStore()


class StubProfileSummaryService:
    def __init__(self) -> None:
        self.calls: List[Dict[str, Any]] = []
        self._counter = 0


import pytest


@pytest.fixture()
def client(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    artifact_dir = tmp_path / "profile_artifacts"

    monkeypatch.setattr(settings, "REPORT_DIR", str(data_dir))
    monkeypatch.setattr(settings, "PROFILE_ARTIFACT_ROOT", str(artifact_dir), raising=False)
    monkeypatch.setattr(settings, "DEBUG", False)
    monkeypatch.setattr(settings, "ENABLE_V27_PROFILE_SCHEMA", True)
    monkeypatch.setattr(settings, "ENABLE_V27_RUNTIME", True)
    monkeypatch.setattr(settings, "KNOWLEDGE_ENABLED", False)

    monkeypatch.setattr(user_service, "USER_STORE_PATH", str(data_dir / "users.json"))
    monkeypatch.setattr(user_service, "USER_STORE_LOCK_PATH", str(data_dir / "users.json.lock"))
    monkeypatch.setattr(system_routes, "CSV_PATH", str(tmp_path / "system_list.csv"))

    document_parser._document_parser = None
    document_skill_adapter._document_skill_adapter = None
    runtime_execution_service._runtime_execution_service = None
    system_profile_service._system_profile_service = None
    profile_artifact_service._profile_artifact_service = None
    profile_health_service._profile_health_service = None

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


def _build_docx_bytes(*paragraphs: str) -> bytes:
    document = Document()
    for paragraph in paragraphs:
        document.add_paragraph(paragraph)
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def _load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_import_writes_document_candidate_and_system_projection_artifacts(client):
    manager = _seed_user("artifact_owner", "pwd123", ["manager"])
    token = _login(client, "artifact_owner", "pwd123")
    _seed_system("PAY", "sys_pay", owner_id=manager["id"])

    response = client.post(
        "/api/v1/system-profiles/sys_pay/profile/import",
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
                ),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200, response.text
    execution_id = response.json()["execution_id"]

    artifact_service = profile_artifact_service.get_profile_artifact_service()
    raw_items = artifact_service.list_layer_records(layer="raw", system_id="sys_pay")
    output_items = artifact_service.list_layer_records(layer="output", system_id="sys_pay")

    assert len(raw_items) == 1
    assert len(output_items) == 1
    workspace_path = artifact_service.repository.get_workspace_path(system_id="sys_pay")
    assert workspace_path
    workspace_prefix = os.path.basename(workspace_path)
    assert raw_items[0]["path"].startswith(f"{workspace_prefix}/source/documents/src_doc_")
    assert raw_items[0]["path"].endswith("/raw.bin")
    assert output_items[0]["path"].startswith(f"{workspace_prefix}/audit/records/")
    assert output_items[0]["latest_path"] == f"{workspace_prefix}/audit/latest_report.json"
    assert output_items[0]["source_artifact_id"].startswith("projection_")

    workspace = Path(workspace_path)
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
    assert (latest_candidate_dir / "candidate_profile.json").exists()

    system_projection = _load_json(latest_candidate_dir / "system_projection.json")
    merged_candidates = _load_json(latest_candidate_dir / "merged_candidates.json")
    card_render = _load_json(latest_candidate_dir / "card_render.json")
    compat_projection = _load_json(latest_candidate_dir / "candidate_profile.json")

    assert system_projection["projection_type"] == "system_projection"
    assert system_projection["system_id"] == "sys_pay"
    assert compat_projection["projection_type"] == "system_projection"
    integration_candidate = merged_candidates["integration_interfaces.canonical.other_integrations"]
    architecture_candidate = merged_candidates["technical_architecture.canonical.architecture_style"]
    assert integration_candidate["selected_value"]
    assert architecture_candidate["selected_value"]
    assert integration_candidate["candidate_items"][0]["source_anchors"]
    assert architecture_candidate["candidate_items"][0]["source_anchors"]
    assert card_render["data_exchange_batch_links"]["card_key"] == "data_exchange_batch_links"

    execution = runtime_execution_service.get_runtime_execution_service().get_execution(execution_id)
    snapshot = execution["input_snapshot"]
    assert snapshot["raw_artifact_id"] == raw_items[0]["artifact_id"]
    assert snapshot["raw_artifact_path"].startswith(f"{workspace_prefix}/source/documents/src_doc_")
    assert snapshot["raw_artifact_path"].endswith("/raw.bin")
    assert snapshot["document_candidate_artifact_id"].startswith("candidate_")
    assert snapshot["projection_artifact_id"].startswith("projection_")
    assert snapshot["output_artifact_id"] == output_items[0]["artifact_id"]

    history = client.get(
        "/api/v1/system-profiles/sys_pay/profile/import-history",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert history.status_code == 200
    first_item = history.json()["items"][0]
    assert first_item["artifact_refs"]["raw_artifact_id"] == raw_items[0]["artifact_id"]
    assert first_item["artifact_refs"]["document_candidate_artifact_id"].startswith("candidate_")
    assert first_item["artifact_refs"]["projection_artifact_id"].startswith("projection_")


def test_import_history_preserves_candidate_projection_artifact_refs(client):
    manager = _seed_user("artifact_owner_2", "pwd123", ["manager"])
    token = _login(client, "artifact_owner_2", "pwd123")
    _seed_system("CRM", "sys_crm", owner_id=manager["id"])

    response = client.post(
        "/api/v1/system-profiles/sys_crm/profile/import",
        data={"doc_type": "requirements"},
        files={
            "file": (
                "requirements.docx",
                _build_docx_bytes("需求概述", "CRM系统服务范围", "负责客户信息维护"),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200

    history = client.get(
        "/api/v1/system-profiles/sys_crm/profile/import-history",
        headers={"Authorization": f"Bearer {token}"},
    )
    item = history.json()["items"][0]
    assert "artifact_refs" in item
    assert item["artifact_refs"]["raw_artifact_id"].startswith("raw_")
    assert item["artifact_refs"]["document_candidate_artifact_id"].startswith("candidate_")
    assert item["artifact_refs"]["projection_artifact_id"].startswith("projection_")
    assert item["artifact_refs"]["output_artifact_id"].startswith("output_")


def test_multiple_imports_merge_candidates_into_latest_system_projection_without_semantic_loss(client):
    manager = _seed_user("artifact_owner_3", "pwd123", ["manager"])
    token = _login(client, "artifact_owner_3", "pwd123")
    _seed_system("PAYMERGE", "sys_pay_merge", owner_id=manager["id"])

    first_response = client.post(
        "/api/v1/system-profiles/sys_pay_merge/profile/import",
        data={"doc_type": "requirements"},
        files={
            "file": (
                "requirements_1.docx",
                _build_docx_bytes(
                    "需求概述",
                    "统一支付平台负责支付统一受理。",
                    "系统边界：不负责总账处理。",
                ),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert first_response.status_code == 200, first_response.text

    second_response = client.post(
        "/api/v1/system-profiles/sys_pay_merge/profile/import",
        data={"doc_type": "requirements"},
        files={
            "file": (
                "requirements_2.docx",
                _build_docx_bytes(
                    "需求概述",
                    "统一支付平台还承担渠道编排与路由控制。",
                    "系统边界：不负责总账处理。",
                ),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert second_response.status_code == 200, second_response.text

    artifact_service = profile_artifact_service.get_profile_artifact_service()
    workspace_path = artifact_service.repository.get_workspace_path(system_id="sys_pay_merge")
    workspace = Path(workspace_path)
    merged_candidates = _load_json(workspace / "candidate" / "latest" / "merged_candidates.json")
    service_scope = merged_candidates["system_positioning.canonical.core_responsibility"]

    assert len(service_scope["candidate_items"]) >= 2
    assert any("支付统一受理" in str(item["value"]) for item in service_scope["candidate_items"])
    assert any("渠道编排与路由控制" in str(item["value"]) for item in service_scope["candidate_items"])
    assert "支付统一受理" in str(service_scope["selected_value"])
    assert "渠道编排与路由控制" in str(service_scope["selected_value"])
    assert service_scope["logical_field"] == "system_positioning.core_responsibility"


def test_profile_health_report_returns_coverage_conflicts_and_low_confidence(client):
    manager = _seed_user("artifact_health_owner", "pwd123", ["manager"])
    token = _login(client, "artifact_health_owner", "pwd123")
    _seed_system("PAY", "sys_pay", owner_id=manager["id"])

    profile_service = system_profile_service.get_system_profile_service()
    profile_service.ensure_profile("PAY", system_id="sys_pay", actor={"id": manager["id"]})
    profile_service.apply_v27_field_updates(
        "PAY",
        system_id="sys_pay",
        field_updates={
            "system_positioning.canonical.service_scope": "支付受理与账务处理",
        },
        actor={"id": manager["id"]},
    )

    artifact_service = profile_artifact_service.get_profile_artifact_service()
    first_wiki = artifact_service.append_layer_record(
        layer="wiki",
        system_id="sys_pay",
        payload={
            "system_id": "sys_pay",
            "target_fields": [
                "system_positioning.canonical.service_scope",
                "technical_architecture.canonical.architecture_style",
            ],
            "candidates": {
                "technical_architecture.canonical.architecture_style": {
                    "value": "单体分层架构",
                    "confidence": 0.91,
                    "reason": "旧版技术方案描述",
                }
            },
        },
        operator_id=manager["id"],
        latest_file_name="candidate_profile.json",
    )
    artifact_service.append_layer_record(
        layer="output",
        system_id="sys_pay",
        payload={
            "quality": {
                "line_count": 20,
                "suggestion_count": 1,
                "missing_targets": ["system_positioning.canonical.service_scope"],
            }
        },
        operator_id=manager["id"],
        source_artifact_id=first_wiki["artifact_id"],
        latest_file_name="latest_report.json",
    )

    latest_wiki = artifact_service.append_layer_record(
        layer="wiki",
        system_id="sys_pay",
        payload={
            "system_id": "sys_pay",
            "target_fields": [
                "system_positioning.canonical.service_scope",
                "technical_architecture.canonical.architecture_style",
            ],
            "candidates": {
                "system_positioning.canonical.service_scope": {
                    "value": "支付受理与账务处理",
                    "confidence": 0.88,
                    "reason": "需求文档明确描述服务边界",
                },
                "technical_architecture.canonical.architecture_style": {
                    "value": "分层微服务架构",
                    "confidence": 0.42,
                    "reason": "技术方案存在多处不一致表述",
                },
            },
        },
        operator_id=manager["id"],
        latest_file_name="candidate_profile.json",
    )
    artifact_service.append_layer_record(
        layer="output",
        system_id="sys_pay",
        payload={
            "quality": {
                "line_count": 36,
                "suggestion_count": 2,
                "missing_targets": [],
            }
        },
        operator_id=manager["id"],
        source_artifact_id=latest_wiki["artifact_id"],
        latest_file_name="latest_report.json",
    )

    response = client.get(
        "/api/v1/system-profiles/sys_pay/profile/health-report",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["system_id"] == "sys_pay"
    assert payload["system_name"] == "PAY"
    assert payload["coverage"]["target_field_count"] == 2
    assert payload["coverage"]["candidate_field_count"] == 2
    assert payload["coverage"]["missing_target_fields"] == []
    assert payload["coverage"]["coverage_ratio"] == 1.0
    assert payload["latest_output_quality"]["suggestion_count"] == 2
    assert payload["latest_output_quality"]["missing_target_count"] == 0
    assert payload["low_confidence_candidates"][0]["field_path"] == "technical_architecture.canonical.architecture_style"
    assert payload["low_confidence_candidates"][0]["confidence"] == 0.42
    conflict = payload["conflicts"][0]
    assert conflict["field_path"] == "technical_architecture.canonical.architecture_style"
    assert conflict["previous_value"] == "单体分层架构"
    assert conflict["latest_value"] == "分层微服务架构"


def test_profile_decision_actions_append_output_records(client, monkeypatch):
    manager = _seed_user("artifact_action_owner", "pwd123", ["manager"])
    token = _login(client, "artifact_action_owner", "pwd123")
    _seed_system("PAY", "sys_pay_action", owner_id=manager["id"])

    monkeypatch.setattr(knowledge_service, "get_knowledge_service", lambda: DummyKnowledgeService())

    profile_service = system_profile_service.get_system_profile_service()
    profile_service.ensure_profile("PAY", system_id="sys_pay_action", actor={"id": manager["id"], "username": manager["username"]})
    profile_service.apply_v27_field_updates(
        "PAY",
        system_id="sys_pay_action",
        field_updates={
            "system_positioning.canonical.service_scope": "支付受理",
        },
        actor={"id": manager["id"], "username": manager["username"]},
    )

    profile_service.update_ai_suggestions_map(
        "PAY",
        suggestions={
            "system_positioning.canonical.service_scope": {
                "value": "支付受理与账务处理",
                "confidence": 0.91,
                "reason": "导入建议",
                "skill_id": "requirements_skill",
                "decision_policy": "suggestion_only",
            }
        },
        actor={"id": manager["id"], "username": manager["username"]},
    )

    accepted = client.post(
        "/api/v1/system-profiles/sys_pay_action/profile/suggestions/accept",
        json={"domain": "system_positioning", "sub_field": "service_scope"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert accepted.status_code == 200, accepted.text

    profile_service.update_ai_suggestions_map(
        "PAY",
        suggestions={
            "constraints_risks.canonical.business_constraints": {
                "value": ["清算窗口限制"],
                "confidence": 0.88,
                "reason": "导入建议",
                "skill_id": "requirements_skill",
                "decision_policy": "suggestion_only",
            }
        },
        actor={"id": manager["id"], "username": manager["username"]},
    )

    ignored = client.post(
        "/api/v1/system-profiles/sys_pay_action/profile/suggestions/ignore",
        json={"domain": "constraints_risks", "sub_field": "business_constraints"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert ignored.status_code == 200, ignored.text

    stored_profile = profile_service.repository.load_profile(state="working", system_id="sys_pay_action")
    assert isinstance(stored_profile, dict)
    stored_profile["ai_suggestions"] = {
        "integration_interfaces.canonical.other_integrations": {
            "value": ["核心账务接口", "数据仓库同步"],
            "confidence": 0.79,
            "reason": "当前建议",
            "skill_id": "tech_solution_skill",
            "decision_policy": "suggestion_only",
        }
    }
    stored_profile["ai_suggestions_previous"] = {
        "integration_interfaces.canonical.other_integrations": {
            "value": ["核心账务接口"],
            "confidence": 0.86,
            "reason": "上一轮建议",
            "skill_id": "tech_solution_skill",
            "decision_policy": "suggestion_only",
        }
    }
    profile_service.repository.save_working_profile(stored_profile)

    rolled_back = client.post(
        "/api/v1/system-profiles/sys_pay_action/profile/suggestions/rollback",
        json={"domain": "integration_interfaces", "sub_field": "other_integrations"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert rolled_back.status_code == 200, rolled_back.text

    published = client.post(
        "/api/v1/system-profiles/PAY/publish",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert published.status_code == 200, published.text

    artifact_service = profile_artifact_service.get_profile_artifact_service()
    output_items = artifact_service.list_layer_records(layer="output", system_id="sys_pay_action")
    decision_items = [
        item
        for item in output_items
        if isinstance(item.get("payload"), dict) and item["payload"].get("output_type") == "decision_log"
    ]
    decision_actions = {item["payload"].get("decision_action") for item in decision_items}
    assert {
        "accept_suggestion",
        "ignore_suggestion",
        "rollback_suggestion",
        "publish_profile",
    } <= decision_actions
    publish_item = next(item for item in decision_items if item["payload"].get("decision_action") == "publish_profile")
    assert publish_item["payload"]["profile_status"] == "published"


def test_health_report_trigger_archives_latest_report(client):
    manager = _seed_user("artifact_health_trigger", "pwd123", ["manager"])
    token = _login(client, "artifact_health_trigger", "pwd123")
    _seed_system("PAY", "sys_pay_health", owner_id=manager["id"])

    profile_service = system_profile_service.get_system_profile_service()
    profile_service.ensure_profile("PAY", system_id="sys_pay_health", actor={"id": manager["id"]})

    artifact_service = profile_artifact_service.get_profile_artifact_service()
    latest_wiki = artifact_service.append_layer_record(
        layer="wiki",
        system_id="sys_pay_health",
        payload={
            "system_id": "sys_pay_health",
            "target_fields": ["system_positioning.canonical.service_scope"],
            "candidates": {
                "system_positioning.canonical.service_scope": {
                    "value": "支付受理",
                    "confidence": 0.93,
                    "reason": "需求文档明确描述",
                }
            },
        },
        operator_id=manager["id"],
        latest_file_name="candidate_profile.json",
    )
    artifact_service.append_layer_record(
        layer="output",
        system_id="sys_pay_health",
        payload={
            "output_type": "import_quality",
            "quality": {
                "line_count": 12,
                "suggestion_count": 1,
                "missing_targets": [],
            },
        },
        operator_id=manager["id"],
        source_artifact_id=latest_wiki["artifact_id"],
        latest_file_name="latest_report.json",
    )

    triggered = client.post(
        "/api/v1/system-profiles/sys_pay_health/profile/health-report/trigger",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert triggered.status_code == 200, triggered.text
    triggered_payload = triggered.json()
    assert triggered_payload["artifact_id"].startswith("output_")

    workspace_path = artifact_service.repository.get_workspace_path(system_id="sys_pay_health")
    assert workspace_path
    latest_file_path = os.path.join(workspace_path, "audit", "health", "latest_report.json")
    assert os.path.exists(latest_file_path)

    fetched = client.get(
        "/api/v1/system-profiles/sys_pay_health/profile/health-report",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert fetched.status_code == 200, fetched.text
    fetched_payload = fetched.json()
    assert fetched_payload["artifact_id"] == triggered_payload["artifact_id"]
    assert fetched_payload["coverage"]["candidate_field_count"] == 1


def test_admin_can_archive_raw_artifact_via_api(client):
    manager = _seed_user("artifact_raw_owner", "pwd123", ["manager"])
    admin = _seed_user("artifact_raw_admin", "pwd123", ["admin"])
    owner_token = _login(client, "artifact_raw_owner", "pwd123")
    admin_token = _login(client, "artifact_raw_admin", "pwd123")
    _seed_system("PAY", "sys_pay_raw", owner_id=manager["id"])

    response = client.post(
        "/api/v1/system-profiles/sys_pay_raw/profile/import",
        data={"doc_type": "requirements"},
        files={
            "file": (
                "requirements.docx",
                _build_docx_bytes("需求概述", "支付系统服务范围", "负责支付受理"),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert response.status_code == 200, response.text

    artifact_service = profile_artifact_service.get_profile_artifact_service()
    raw_items = artifact_service.list_layer_records(layer="raw", system_id="sys_pay_raw")
    assert len(raw_items) == 1
    raw_artifact_id = raw_items[0]["artifact_id"]

    denied = client.post(
        f"/api/v1/system-profiles/sys_pay_raw/profile/raw-artifacts/{raw_artifact_id}/archive",
        json={"reason": "重复导入"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert denied.status_code == 403

    archived = client.post(
        f"/api/v1/system-profiles/sys_pay_raw/profile/raw-artifacts/{raw_artifact_id}/archive",
        json={"reason": "重复导入"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert archived.status_code == 200, archived.text
    archived_payload = archived.json()["data"]
    assert archived_payload["status"] == "archived"
    assert archived_payload["archive_reason"] == "重复导入"

    listing = client.get(
        "/api/v1/system-profiles/sys_pay_raw/profile/raw-artifacts?include_archived=true",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert listing.status_code == 200, listing.text
    assert listing.json()["items"][0]["status"] == "archived"


def test_admin_can_reset_profile_workspace_and_clear_profile_artifacts(client):
    manager = _seed_user("artifact_reset_owner", "pwd123", ["manager"])
    admin = _seed_user("artifact_reset_admin", "pwd123", ["admin"])
    owner_token = _login(client, "artifact_reset_owner", "pwd123")
    admin_token = _login(client, "artifact_reset_admin", "pwd123")
    _seed_system("PAY", "sys_pay_reset", owner_id=manager["id"])

    response = client.post(
        "/api/v1/system-profiles/sys_pay_reset/profile/import",
        data={"doc_type": "requirements"},
        files={
            "file": (
                "requirements.docx",
                _build_docx_bytes("需求概述", "支付系统服务范围", "负责支付受理"),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert response.status_code == 200, response.text
    execution_id = response.json()["execution_id"]

    artifact_service = profile_artifact_service.get_profile_artifact_service()
    profile_service = system_profile_service.get_system_profile_service()
    runtime_service = runtime_execution_service.get_runtime_execution_service()
    workspace_path = artifact_service.repository.get_workspace_path(system_id="sys_pay_reset")
    assert workspace_path
    assert runtime_service.get_execution(execution_id) is not None
    assert memory_service.get_memory_service().query_records(
        "sys_pay_reset",
        memory_type="profile_update",
        scene_id="pm_document_ingest",
    )["total"] == 1

    denied = client.post(
        "/api/v1/system-profiles/sys_pay_reset/profile/reset",
        json={"reason": "manual_cleanup"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert denied.status_code == 403

    reset = client.post(
        "/api/v1/system-profiles/sys_pay_reset/profile/reset",
        json={"reason": "manual_cleanup"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert reset.status_code == 200, reset.text
    reset_payload = reset.json()["data"]
    assert reset_payload["deleted"] is True
    assert reset_payload["system_id"] == "sys_pay_reset"
    assert reset_payload["workspace_deleted"] is True
    assert reset_payload["deleted_runtime_executions"] == 1
    assert reset_payload["deleted_memory_records"] == 1

    assert artifact_service.repository.get_workspace_path(system_id="sys_pay_reset") is None
    assert profile_service.get_profile("PAY") is None
    assert runtime_service.get_execution(execution_id) is None
    assert runtime_service.get_latest_execution("sys_pay_reset") is None
    assert memory_service.get_memory_service().query_records(
        "sys_pay_reset",
        memory_type="profile_update",
        scene_id="pm_document_ingest",
    )["total"] == 0

    history = client.get(
        "/api/v1/system-profiles/sys_pay_reset/profile/import-history",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert history.status_code == 200, history.text
    assert history.json()["total"] == 0


def test_admin_can_reset_all_profile_workspaces(client):
    owner = _seed_user("artifact_bulk_owner", "pwd123", ["manager"])
    admin = _seed_user("artifact_bulk_admin", "pwd123", ["admin"])
    owner_token = _login(client, "artifact_bulk_owner", "pwd123")
    admin_token = _login(client, "artifact_bulk_admin", "pwd123")
    system_routes._write_systems(
        [
            {
                "id": "sys_pay_bulk_a",
                "name": "PAY_A",
                "abbreviation": "PAY_A",
                "status": "运行中",
                "extra": {"owner_id": owner["id"]},
            },
            {
                "id": "sys_pay_bulk_b",
                "name": "PAY_B",
                "abbreviation": "PAY_B",
                "status": "运行中",
                "extra": {"owner_id": owner["id"]},
            },
        ]
    )

    for system_id, file_name, content in (
        ("sys_pay_bulk_a", "bulk-a.docx", _build_docx_bytes("业务背景", "统一支付负责支付受理与路由编排")),
        ("sys_pay_bulk_b", "bulk-b.docx", _build_docx_bytes("业务背景", "贷款核算负责贷款账务处理与批量对账")),
    ):
        response = client.post(
            f"/api/v1/system-profiles/{system_id}/profile/import",
            data={"doc_type": "requirements"},
            files={
                "file": (
                    file_name,
                    content,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert response.status_code == 200, response.text

    artifact_service = profile_artifact_service.get_profile_artifact_service()
    assert artifact_service.repository.get_workspace_path(system_id="sys_pay_bulk_a")
    assert artifact_service.repository.get_workspace_path(system_id="sys_pay_bulk_b")

    denied = client.post(
        "/api/v1/system-profiles/profile/reset-all",
        json={"reason": "global_cleanup"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert denied.status_code == 403

    reset = client.post(
        "/api/v1/system-profiles/profile/reset-all",
        json={"reason": "global_cleanup"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert reset.status_code == 200, reset.text
    payload = reset.json()["data"]
    assert payload["reason"] == "global_cleanup"
    assert payload["deleted_workspace_count"] == 2
    assert payload["deleted_runtime_execution_count"] == 2
    assert payload["deleted_memory_record_count"] == 2
    assert {item["system_id"] for item in payload["systems"]} == {"sys_pay_bulk_a", "sys_pay_bulk_b"}

    assert artifact_service.repository.get_workspace_path(system_id="sys_pay_bulk_a") is None
    assert artifact_service.repository.get_workspace_path(system_id="sys_pay_bulk_b") is None
