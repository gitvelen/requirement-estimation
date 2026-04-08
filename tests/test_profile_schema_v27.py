import json
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.config.config import settings
from backend.service.profile_schema_service import V27_DOMAIN_KEYS, build_empty_profile_data
from backend.service import system_profile_service
from backend.service import knowledge_service


def _count_canonical_fields(profile_data):
    total = 0
    for domain in V27_DOMAIN_KEYS:
        canonical = ((profile_data.get(domain) or {}).get("canonical")) or {}
        total += len(canonical)
    return total


def test_empty_profile_data_contains_v27_canonical_domains_and_extensions():
    profile_data = build_empty_profile_data()

    assert tuple(profile_data.keys()) == V27_DOMAIN_KEYS
    assert _count_canonical_fields(profile_data) == 24

    assert profile_data["system_positioning"]["canonical"]["extensions"] == {}
    assert profile_data["business_capabilities"]["canonical"]["extensions"] == {}
    assert profile_data["integration_interfaces"]["canonical"]["extensions"] == {}
    assert profile_data["technical_architecture"]["canonical"]["extensions"] == {}
    assert profile_data["constraints_risks"]["canonical"]["extensions"] == {}

    tech_stack = profile_data["technical_architecture"]["canonical"]["tech_stack"]
    assert tech_stack == {
        "languages": [],
        "frameworks": [],
        "databases": [],
        "middleware": [],
        "others": [],
    }

    performance_baseline = profile_data["technical_architecture"]["canonical"]["performance_baseline"]
    assert performance_baseline == {
        "online": {
            "peak_tps": "",
            "p95_latency_ms": "",
            "availability_target": "",
        },
        "batch": {
            "window": "",
            "data_volume": "",
            "peak_duration": "",
        },
        "processing_model": "",
    }


def test_system_profile_service_v27_persists_profile_data_without_legacy_fields(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(settings, "REPORT_DIR", str(data_dir))
    monkeypatch.setattr(settings, "ENABLE_V27_PROFILE_SCHEMA", True)
    system_profile_service._system_profile_service = None

    service = system_profile_service.get_system_profile_service()
    saved = service.upsert_profile(
        "统一支付平台",
        {
            "system_id": "SYS-001",
            "profile_data": {
                "system_positioning": {
                    "canonical": {
                        "system_type": "渠道支撑系统",
                        "business_domain": ["支付"],
                        "architecture_layer": "",
                        "target_users": ["柜面"],
                        "service_scope": "支付统一受理",
                        "system_boundary": [],
                        "extensions": {},
                    }
                },
                "business_capabilities": build_empty_profile_data()["business_capabilities"],
                "integration_interfaces": build_empty_profile_data()["integration_interfaces"],
                "technical_architecture": build_empty_profile_data()["technical_architecture"],
                "constraints_risks": build_empty_profile_data()["constraints_risks"],
            },
            "field_sources": {
                "system_positioning.canonical.system_type": {
                    "source": "manual",
                    "scene_id": "profile_manual_edit",
                }
            },
            "evidence_refs": [{"source_type": "pm_doc", "source_id": "doc-1"}],
        },
        actor={"username": "pm"},
    )

    assert "fields" not in saved
    assert saved["profile_data"]["system_positioning"]["canonical"]["system_type"] == "渠道支撑系统"
    assert saved["field_sources"]["system_positioning.canonical.system_type"]["source"] == "manual"

    store_path = data_dir / "system_profiles.json"
    rows = json.loads(store_path.read_text(encoding="utf-8"))
    assert len(rows) == 1
    row = rows[0]
    assert "fields" not in row
    assert row["profile_data"]["system_positioning"]["canonical"]["service_scope"] == "支付统一受理"
    assert "system_scope" not in json.dumps(row, ensure_ascii=False)


def test_system_profile_service_v27_publish_uses_canonical_profile_snapshot(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    captured = {}

    class DummyEmbeddingService:
        def generate_embedding(self, text):
            captured["embedding_text"] = text
            return [1.0, 0.0, 0.0]

    class DummyVectorStore:
        def insert_knowledge(self, **kwargs):
            captured["insert_payload"] = kwargs

    class DummyKnowledgeService:
        def __init__(self):
            self.embedding_service = DummyEmbeddingService()
            self.vector_store = DummyVectorStore()

    monkeypatch.setattr(settings, "REPORT_DIR", str(data_dir))
    monkeypatch.setattr(settings, "ENABLE_V27_PROFILE_SCHEMA", True)
    monkeypatch.setattr(knowledge_service, "get_knowledge_service", lambda: DummyKnowledgeService())
    system_profile_service._system_profile_service = None

    service = system_profile_service.get_system_profile_service()
    service.upsert_profile(
        "统一支付平台",
        {
            "system_id": "SYS-001",
            "profile_data": {
                "system_positioning": {
                    "canonical": {
                        "system_type": "渠道支撑系统",
                        "business_domain": ["支付"],
                        "architecture_layer": "渠道层",
                        "target_users": ["柜面", "运营"],
                        "service_scope": "支付统一受理",
                        "system_boundary": ["统一支付入口"],
                        "extensions": {},
                    }
                },
                "business_capabilities": {
                    "canonical": {
                        "functional_modules": ["支付查询", "支付扣款"],
                        "business_processes": ["统一受理"],
                        "data_assets": ["支付流水"],
                        "extensions": {},
                    }
                },
                "integration_interfaces": build_empty_profile_data()["integration_interfaces"],
                "technical_architecture": build_empty_profile_data()["technical_architecture"],
                "constraints_risks": build_empty_profile_data()["constraints_risks"],
            },
            "evidence_refs": [],
        },
        actor={"username": "pm"},
    )

    published = service.publish_profile("统一支付平台", actor={"username": "pm"})

    assert published["status"] == "published"
    assert "fields" not in published
    insert_payload = captured["insert_payload"]
    assert insert_payload["knowledge_type"] == "system_profile"
    assert insert_payload["source_file"] == "system_profile_manual"
    assert "支付统一受理" in insert_payload["content"]
    assert "支付查询" in insert_payload["content"]
    metadata = insert_payload["metadata"]
    assert "system_scope" not in metadata
    assert metadata["profile_data"]["system_positioning"]["canonical"]["service_scope"] == "支付统一受理"


def test_system_profile_service_v27_minimal_flags_use_canonical_fields(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(settings, "REPORT_DIR", str(data_dir))
    monkeypatch.setattr(settings, "ENABLE_V27_PROFILE_SCHEMA", True)
    system_profile_service._system_profile_service = None

    service = system_profile_service.get_system_profile_service()
    service.upsert_profile(
        "统一支付平台",
        {
            "system_id": "SYS-001",
            "profile_data": {
                "system_positioning": {
                    "canonical": {
                        "service_scope": "支付统一受理",
                    }
                },
                "business_capabilities": {
                    "canonical": {
                        "functional_modules": ["支付查询"],
                    }
                },
            },
            "evidence_refs": [],
        },
        actor={"username": "pm"},
    )

    flags = service.get_minimal_profile_flags("统一支付平台")

    assert flags["has_profile"] is True
    assert flags["missing_minimal_fields"] == []


def test_system_profile_service_v27_accept_ai_suggestion_updates_canonical_field(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(settings, "REPORT_DIR", str(data_dir))
    monkeypatch.setattr(settings, "ENABLE_V27_PROFILE_SCHEMA", True)
    system_profile_service._system_profile_service = None

    service = system_profile_service.get_system_profile_service()
    service.upsert_profile(
        "统一支付平台",
        {
            "system_id": "SYS-001",
            "profile_data": {
                "system_positioning": {
                    "canonical": {
                        "system_type": "渠道支撑系统",
                        "business_domain": ["支付"],
                        "architecture_layer": "渠道层",
                        "target_users": ["柜面"],
                        "service_scope": "支付统一受理",
                        "system_boundary": [],
                        "extensions": {},
                    }
                },
                "business_capabilities": build_empty_profile_data()["business_capabilities"],
                "integration_interfaces": build_empty_profile_data()["integration_interfaces"],
                "technical_architecture": build_empty_profile_data()["technical_architecture"],
                "constraints_risks": build_empty_profile_data()["constraints_risks"],
            },
            "evidence_refs": [],
        },
        actor={"username": "pm"},
    )
    service.update_ai_suggestions_map(
        "统一支付平台",
        suggestions={
            "system_positioning": {
                "target_users": ["柜面", "运营"],
            },
        },
        actor={"username": "pm"},
    )

    accepted = service.accept_ai_suggestion(
        "统一支付平台",
        domain="system_positioning",
        sub_field="target_users",
        actor={"username": "pm"},
    )

    assert accepted["profile_data"]["system_positioning"]["canonical"]["target_users"] == ["柜面", "运营"]


def test_system_profile_service_v27_accepts_flat_canonical_ai_suggestion_without_blanking_field(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(settings, "REPORT_DIR", str(data_dir))
    monkeypatch.setattr(settings, "ENABLE_V27_PROFILE_SCHEMA", True)
    system_profile_service._system_profile_service = None

    service = system_profile_service.get_system_profile_service()
    profile_data = build_empty_profile_data()
    profile_data["technical_architecture"]["canonical"]["architecture_style"] = "旧架构"
    service.upsert_profile(
        "统一支付平台",
        {
            "system_id": "SYS-001",
            "profile_data": profile_data,
            "evidence_refs": [],
        },
        actor={"username": "pm"},
    )
    service.update_ai_suggestions_map(
        "统一支付平台",
        suggestions={
            "technical_architecture.canonical.architecture_style": {
                "value": "分层微服务架构",
                "scene_id": "pm_document_ingest",
            },
        },
        actor={"username": "pm"},
    )

    accepted = service.accept_ai_suggestion(
        "统一支付平台",
        domain="technical_architecture",
        sub_field="architecture_style",
        actor={"username": "pm"},
    )

    assert accepted["profile_data"]["technical_architecture"]["canonical"]["architecture_style"] == "分层微服务架构"


def test_system_profile_service_v27_startup_migration_keeps_flat_canonical_ai_suggestions(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(settings, "REPORT_DIR", str(data_dir))
    monkeypatch.setattr(settings, "ENABLE_V27_PROFILE_SCHEMA", True)
    system_profile_service._system_profile_service = None

    store_path = data_dir / "system_profiles.json"
    store_path.write_text(
        json.dumps(
            [
                {
                    "system_id": "SYS-001",
                    "system_name": "统一支付平台",
                    "status": "draft",
                    "created_at": "2026-04-08T12:00:00",
                    "updated_at": "2026-04-08T12:00:00",
                    "profile_data": build_empty_profile_data(),
                    "field_sources": {},
                    "ai_suggestions": {
                        "technical_architecture.canonical.architecture_style": {
                            "value": "分层微服务架构",
                            "scene_id": "pm_document_ingest",
                        }
                    },
                    "evidence_refs": [],
                }
            ],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    service = system_profile_service.get_system_profile_service()
    fetched = service.get_profile("统一支付平台")

    assert fetched["ai_suggestions"]["technical_architecture.canonical.architecture_style"]["value"] == "分层微服务架构"

    rows = json.loads(store_path.read_text(encoding="utf-8"))
    assert "technical_architecture.canonical.architecture_style" in rows[0]["ai_suggestions"]
    assert "technical_architecture" not in rows[0]["ai_suggestions"]


def test_system_profile_service_v27_ignore_ai_suggestion_returns_ignored_map(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(settings, "REPORT_DIR", str(data_dir))
    monkeypatch.setattr(settings, "ENABLE_V27_PROFILE_SCHEMA", True)
    system_profile_service._system_profile_service = None

    service = system_profile_service.get_system_profile_service()
    service.upsert_profile(
        "统一支付平台",
        {
            "system_id": "SYS-001",
            "profile_data": build_empty_profile_data(),
            "evidence_refs": [],
        },
        actor={"username": "pm"},
    )
    service.update_ai_suggestions_map(
        "统一支付平台",
        suggestions={
            "system_positioning": {
                "target_users": ["柜面", "运营"],
            },
        },
        actor={"username": "pm"},
    )

    ignored = service.ignore_ai_suggestion(
        "统一支付平台",
        domain="system_positioning",
        sub_field="target_users",
        actor={"username": "pm"},
    )

    assert ignored["ai_suggestion_ignored"]["system_positioning.target_users"] == ["柜面", "运营"]


def test_system_profile_service_v27_ignore_flat_canonical_ai_suggestion_persists_real_value(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(settings, "REPORT_DIR", str(data_dir))
    monkeypatch.setattr(settings, "ENABLE_V27_PROFILE_SCHEMA", True)
    system_profile_service._system_profile_service = None

    service = system_profile_service.get_system_profile_service()
    service.upsert_profile(
        "统一支付平台",
        {
            "system_id": "SYS-001",
            "profile_data": build_empty_profile_data(),
            "evidence_refs": [],
        },
        actor={"username": "pm"},
    )
    service.update_ai_suggestions_map(
        "统一支付平台",
        suggestions={
            "constraints_risks.canonical.known_risks": {
                "value": ["批量窗口紧张", "依赖核心系统日终处理"],
                "scene_id": "pm_document_ingest",
            },
        },
        actor={"username": "pm"},
    )

    ignored = service.ignore_ai_suggestion(
        "统一支付平台",
        domain="constraints_risks",
        sub_field="known_risks",
        actor={"username": "pm"},
    )

    assert ignored["ai_suggestion_ignored"]["constraints_risks.known_risks"] == [
        "批量窗口紧张",
        "依赖核心系统日终处理",
    ]


def test_system_profile_service_v27_mixed_shape_prefers_flat_canonical_suggestion(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(settings, "REPORT_DIR", str(data_dir))
    monkeypatch.setattr(settings, "ENABLE_V27_PROFILE_SCHEMA", True)
    system_profile_service._system_profile_service = None

    service = system_profile_service.get_system_profile_service()
    profile_data = build_empty_profile_data()
    profile_data["technical_architecture"]["canonical"]["architecture_style"] = "旧架构"
    service.upsert_profile(
        "统一支付平台",
        {
            "system_id": "SYS-001",
            "profile_data": profile_data,
            "evidence_refs": [],
        },
        actor={"username": "pm"},
    )
    service.update_ai_suggestions_map(
        "统一支付平台",
        suggestions={
            "technical_architecture": {
                "canonical": {
                    "architecture_style": "",
                }
            },
            "technical_architecture.canonical.architecture_style": {
                "value": "分层微服务架构",
                "scene_id": "pm_document_ingest",
            },
        },
        actor={"username": "pm"},
    )

    accepted = service.accept_ai_suggestion(
        "统一支付平台",
        domain="technical_architecture",
        sub_field="architecture_style",
        actor={"username": "pm"},
    )

    assert accepted["profile_data"]["technical_architecture"]["canonical"]["architecture_style"] == "分层微服务架构"
