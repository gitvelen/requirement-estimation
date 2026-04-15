import json
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.config.config import settings
from backend.service.profile_schema_service import (
    V27_DOMAIN_KEYS,
    build_card_candidates,
    build_empty_profile_data,
    build_profile_cards,
    normalize_profile_data,
)
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
    assert _count_canonical_fields(profile_data) == 29

    assert profile_data["system_positioning"]["canonical"]["extensions"] == {}
    assert profile_data["business_capabilities"]["canonical"]["extensions"] == {}
    assert profile_data["integration_interfaces"]["canonical"]["extensions"] == {}
    assert profile_data["technical_architecture"]["canonical"]["extensions"] == {}
    assert profile_data["constraints_risks"]["canonical"]["extensions"] == {}

    assert profile_data["system_positioning"]["canonical"] == {
        "system_type": "",
        "system_aliases": [],
        "lifecycle_status": "",
        "business_domains": [],
        "business_lines": [],
        "architecture_layer": "",
        "application_level": "",
        "target_users": [],
        "core_responsibility": "",
        "extensions": {},
    }

    assert profile_data["business_capabilities"]["canonical"] == {
        "functional_modules": [],
        "business_scenarios": [],
        "business_flows": [],
        "data_reports": [],
        "extensions": {},
    }

    assert profile_data["constraints_risks"]["canonical"] == {
        "business_constraints": [],
        "prerequisites": [],
        "sensitive_points": [],
        "risk_items": [],
        "extensions": {},
    }

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


def test_normalize_profile_data_maps_legacy_canonical_aliases_to_current_fields():
    normalized = normalize_profile_data(
        {
            "system_positioning": {
                "canonical": {
                    "service_scope": "统一支付受理与账务处理",
                }
            },
            "business_capabilities": {
                "canonical": {
                    "business_processes": [
                        {"name": "支付开户", "description": "处理开户与账户校验"},
                    ],
                    "data_assets": [
                        {"name": "支付流水", "description": "记录交易流水"},
                    ],
                }
            },
            "constraints_risks": {
                "canonical": {
                    "technical_constraints": [
                        {"name": "批量窗口", "description": "依赖核心日终时点"},
                    ],
                    "known_risks": [
                        {"name": "核心依赖", "impact": "高"},
                    ],
                }
            },
        }
    )

    assert normalized["system_positioning"]["canonical"]["core_responsibility"] == "统一支付受理与账务处理"
    assert normalized["business_capabilities"]["canonical"]["business_flows"] == [
        {"name": "支付开户", "description": "处理开户与账户校验"},
    ]
    assert normalized["business_capabilities"]["canonical"]["data_reports"] == [
        {"name": "支付流水", "type": "data", "description": "记录交易流水"},
    ]
    assert normalized["constraints_risks"]["canonical"]["prerequisites"] == [
        {"name": "批量窗口", "description": "依赖核心日终时点"},
    ]
    assert normalized["constraints_risks"]["canonical"]["risk_items"] == [
        {"name": "核心依赖", "impact": "高"},
    ]


def test_build_card_candidates_maps_legacy_field_aliases_and_ignored_current_field_path():
    cards = build_card_candidates(
        {
            "system_positioning.canonical.service_scope": {
                "value": "统一支付受理与账务处理",
                "confidence": 0.88,
            },
            "business_capabilities.canonical.business_processes": {
                "value": [
                    {"name": "支付开户", "description": "处理开户与账户校验"},
                ],
                "confidence": 0.76,
            },
        },
        ignored_map={
            "business_capabilities.canonical.business_flows": [
                {"name": "支付开户", "description": "处理开户与账户校验"},
            ]
        },
        profile_data=build_empty_profile_data(),
    )

    assert cards["service_positioning"]["content"] == {
        "system_positioning.canonical.core_responsibility": "统一支付受理与账务处理",
    }
    assert cards["service_positioning"]["summary"] == {
        "target_users": [],
        "core_responsibility": "统一支付受理与账务处理",
    }
    assert "business_flows" not in cards


def test_build_profile_cards_uses_new_d4_card_structure_and_fixed_slots():
    profile_data = build_empty_profile_data()
    technical = profile_data["technical_architecture"]["canonical"]
    technical["architecture_style"] = "分层微服务架构"
    technical["network_zone"] = "生产内网区"
    technical["tech_stack"] = {
        "languages": ["Java"],
        "frameworks": ["Spring Boot"],
        "databases": ["MySQL"],
        "middleware": ["Redis"],
        "others": ["Docker"],
    }
    technical["performance_baseline"] = {
        "online": {"peak_tps": "200 TPS", "p95_latency_ms": "80", "availability_target": "99.99%"},
        "batch": {"window": "日终 30 分钟", "data_volume": "", "peak_duration": ""},
        "processing_model": "",
    }
    technical["extensions"] = {
        "deployment_mode": "云上分布式集群部署",
        "topology_characteristics": ["应用节点互备", "数据库一主多从"],
        "architecture_deployment_notes": "支持按业务量横向扩容。",
        "infrastructure_components": ["服务注册中心", "配置中心", "数据库连接池"],
        "technical_stack_notes": "统一接入容器化运行平台。",
        "design_methods": ["组件化设计", "插件化扩展"],
        "extensibility_features": ["参数可配置化", "支持灵活扩展"],
        "common_capabilities": ["日志", "权限控制", "订阅发布"],
        "design_characteristics_notes": "支持多租户隔离。",
        "availability_design": ["应用节点互备", "自动故障切换"],
        "monitoring_operations": ["服务监控", "异常诊断", "资源监控"],
        "security_requirements": ["等保三级", "敏感数据传输加密"],
        "quality_attribute_notes": "关键链路支持审计留痕。",
    }

    cards = build_profile_cards(profile_data)

    assert "architecture_mode" not in cards
    assert "tech_stack_impl" not in cards
    assert "deployment_network" not in cards
    assert "performance_resilience_current" not in cards

    architecture_card = cards["architecture_deployment"]
    assert architecture_card["title"] == "架构与部署方式"
    assert architecture_card["summary"] == {
        "architecture_style": "分层微服务架构",
        "deployment_mode": "云上分布式集群部署",
        "deployment_environment": "网络区域：生产内网区",
        "topology_characteristics": ["应用节点互备", "数据库一主多从"],
        "supplementary_notes": "支持按业务量横向扩容。",
    }

    tech_stack_card = cards["tech_stack_infrastructure"]
    assert tech_stack_card["title"] == "技术栈与基础设施"
    assert tech_stack_card["summary"]["infrastructure_components"] == ["服务注册中心", "配置中心", "数据库连接池"]
    assert tech_stack_card["summary"]["supplementary_notes"] == "统一接入容器化运行平台。"

    design_card = cards["design_characteristics"]
    assert design_card["title"] == "系统设计特点"
    assert design_card["summary"]["design_methods"] == ["组件化设计", "插件化扩展"]
    assert design_card["summary"]["extensibility_features"] == ["参数可配置化", "支持灵活扩展"]
    assert design_card["summary"]["common_capabilities"] == ["日志", "权限控制", "订阅发布"]
    assert design_card["summary"]["supplementary_notes"] == "支持多租户隔离。"

    quality_card = cards["quality_attributes"]
    assert quality_card["title"] == "性能、安全与可用性"
    assert quality_card["summary"]["performance_requirements"] == {
        "peak_tps": "200 TPS",
        "p95_latency_ms": "80",
        "availability_target": "99.99%",
        "batch_window": "日终 30 分钟",
    }
    assert quality_card["summary"]["availability_design"] == ["应用节点互备", "自动故障切换"]
    assert quality_card["summary"]["monitoring_operations"] == ["服务监控", "异常诊断", "资源监控"]
    assert quality_card["summary"]["security_requirements"] == ["等保三级", "敏感数据传输加密"]
    assert quality_card["summary"]["supplementary_notes"] == "关键链路支持审计留痕。"


def test_build_profile_cards_uses_redesigned_d1_d2_d5_cards():
    profile_data = build_empty_profile_data()
    positioning = profile_data["system_positioning"]["canonical"]
    positioning["system_type"] = "信贷核心系统"
    positioning["system_aliases"] = ["LA", "贷款核算"]
    positioning["lifecycle_status"] = "生产运行"
    positioning["business_domains"] = ["信贷"]
    positioning["business_lines"] = ["零售信贷", "对公信贷"]
    positioning["architecture_layer"] = "业务应用层"
    positioning["application_level"] = "重要系统"
    positioning["target_users"] = ["客户经理", "运营"]
    positioning["core_responsibility"] = "负责贷款账户全生命周期核算与账务处理。"

    business = profile_data["business_capabilities"]["canonical"]
    business["functional_modules"] = [
        {"name": "产品工厂", "description": "维护贷款产品定义与参数。"},
        {"name": "贷款开户", "description": "完成贷款建户与合同建立。"},
    ]
    business["business_scenarios"] = [
        {"name": "常规放款", "description": "贷款审批通过后完成放款开户。"},
    ]
    business["business_flows"] = [
        {"name": "贷款发放流程", "description": "审批通过后生成借据并完成放款。"},
    ]
    business["data_reports"] = [
        {"name": "贷款台账", "type": "data", "description": "维护贷款主数据与余额信息。"},
        {"name": "日终对账报表", "type": "report", "description": "输出日终核算与对账结果。"},
    ]

    constraints = profile_data["constraints_risks"]["canonical"]
    constraints["business_constraints"] = [
        {"name": "清算窗口", "description": "需在核心清算窗口前完成日终处理。"},
    ]
    constraints["prerequisites"] = [
        {"name": "主数据到位", "description": "产品、机构、科目等基础配置必须先完成。"},
    ]
    constraints["sensitive_points"] = [
        {"name": "计息结息", "description": "利率、罚息和减值规则变更影响范围大。"},
    ]
    constraints["risk_items"] = [
        {"name": "外部依赖抖动", "impact": "影响放款与还款链路稳定性。"},
    ]

    cards = build_profile_cards(profile_data)

    assert "boundary_ecosystem" not in cards
    assert "e2e_processes" not in cards
    assert "business_objects_assets" not in cards
    assert "compliance_grading" not in cards
    assert "technical_resource_constraints" not in cards
    assert "continuity_recovery_requirements" not in cards
    assert "known_risks_governance" not in cards

    assert cards["system_identity"]["title"] == "系统身份"
    assert cards["business_affiliation"]["title"] == "业务归属"
    assert cards["application_hierarchy"]["title"] == "应用层级"
    assert cards["service_positioning"]["title"] == "服务定位"
    assert cards["capability_modules"]["title"] == "功能模块"
    assert cards["business_scenarios"]["title"] == "典型场景"
    assert cards["business_flows"]["title"] == "业务流程"
    assert cards["data_reports"]["title"] == "数据报表"
    assert cards["business_constraints"]["title"] == "业务约束"
    assert cards["prerequisites"]["title"] == "前提条件"
    assert cards["sensitive_points"]["title"] == "敏感环节"
    assert cards["risk_items"]["title"] == "风险事项"

    assert cards["service_positioning"]["summary"] == {
        "target_users": ["客户经理", "运营"],
        "core_responsibility": "负责贷款账户全生命周期核算与账务处理。",
    }
    assert cards["capability_modules"]["summary"]["functional_modules"] == business["functional_modules"]
    assert cards["data_reports"]["summary"]["data_reports"] == business["data_reports"]
    assert cards["risk_items"]["summary"]["risk_items"] == constraints["risk_items"]


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

    repository = service.repository
    row = repository.load_profile(state="working", system_id="SYS-001")
    assert isinstance(row, dict)
    assert "fields" not in row
    assert row["profile_data"]["system_positioning"]["canonical"]["core_responsibility"] == "支付统一受理"
    assert "system_scope" not in json.dumps(row, ensure_ascii=False)
    assert not (data_dir / "system_profiles.json").exists()
    assert saved["board_version"] == "cards_v1"
    assert saved["profile_cards"]["system_identity"]["title"] == "系统身份"
    assert saved["profile_cards"]["system_identity"]["summary"]["system_type"] == "渠道支撑系统"
    assert saved["profile_cards"]["service_positioning"]["summary"]["core_responsibility"] == "支付统一受理"
    assert saved["domain_summary"]["system_positioning"]["card_count"] == 4


def test_system_profile_service_v27_publish_skips_knowledge_embedding_sync(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    captured = {}

    class DummyEmbeddingService:
        def generate_embedding(self, text):
            captured["embedding_text"] = text
            raise AssertionError("publish should not generate embedding for system_profile")

    class DummyVectorStore:
        def insert_knowledge(self, **kwargs):
            captured["insert_payload"] = kwargs
            raise AssertionError("publish should not insert system_profile into vector store")

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
    assert captured == {}


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


def test_system_profile_service_v27_accept_card_candidate_supports_nested_extension_fields(tmp_path, monkeypatch):
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
            "evidence_refs": [],
        },
        actor={"username": "pm"},
    )
    service.update_ai_suggestions_map(
        "统一支付平台",
        suggestions={
            "system_positioning.canonical.lifecycle_status": {
                "value": "运行中",
                "confidence": 0.9,
            },
            "system_positioning.canonical.system_aliases": {
                "value": ["UPAY"],
                "confidence": 0.8,
            },
        },
        actor={"username": "pm"},
    )

    updated = service.accept_card_candidate("统一支付平台", card_key="system_identity", actor={"username": "pm"})

    canonical = updated["profile_data"]["system_positioning"]["canonical"]
    assert canonical["system_type"] == "渠道支撑系统"
    assert canonical["lifecycle_status"] == "运行中"
    assert canonical["system_aliases"] == ["UPAY"]
    assert "system_identity" not in updated["card_candidates"]


def test_system_profile_service_v27_accept_card_candidate_hides_projection_candidate_after_apply(tmp_path, monkeypatch):
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
            "evidence_refs": [],
        },
        actor={"username": "pm"},
    )

    workspace_path = service.repository.get_workspace_path(system_id="SYS-001")
    latest_dir = os.path.join(workspace_path, "candidate", "latest")
    os.makedirs(latest_dir, exist_ok=True)

    merged_candidates = {
        "system_positioning.canonical.lifecycle_status": {
            "selected_value": "运行中",
            "candidate_items": [
                {
                    "source_mode": "document",
                    "value": "运行中",
                    "confidence": 0.92,
                }
            ],
            "confidence": 0.92,
            "selection_policy": "merge_all",
            "source_mode": "document",
        },
        "system_positioning.canonical.system_aliases": {
            "selected_value": ["UPAY"],
            "candidate_items": [
                {
                    "source_mode": "document",
                    "value": ["UPAY"],
                    "confidence": 0.88,
                }
            ],
            "confidence": 0.88,
            "selection_policy": "merge_all",
            "source_mode": "document",
        },
    }
    with open(os.path.join(latest_dir, "merged_candidates.json"), "w", encoding="utf-8") as f:
        json.dump(merged_candidates, f, ensure_ascii=False, indent=2)
    with open(os.path.join(latest_dir, "system_projection.json"), "w", encoding="utf-8") as f:
        json.dump(
            {
                "projection_type": "system_projection",
                "system_id": "SYS-001",
                "system_name": "统一支付平台",
                "merged_candidates": merged_candidates,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    updated = service.accept_card_candidate("统一支付平台", card_key="system_identity", actor={"username": "pm"})

    canonical = updated["profile_data"]["system_positioning"]["canonical"]
    assert canonical["lifecycle_status"] == "运行中"
    assert canonical["system_aliases"] == ["UPAY"]
    assert "system_identity" not in updated["card_candidates"]
    assert updated["domain_summary"]["system_positioning"]["candidate_count"] == 0


def test_system_profile_service_v27_accept_card_candidate_allows_stale_projection_candidate_when_value_matches_profile(tmp_path, monkeypatch):
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
                        "architecture_layer": "",
                        "target_users": ["柜面"],
                        "service_scope": "支付统一受理",
                        "system_boundary": [],
                        "lifecycle_status": "运行中",
                        "system_aliases": ["UPAY"],
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

    workspace_path = service.repository.get_workspace_path(system_id="SYS-001")
    latest_dir = os.path.join(workspace_path, "candidate", "latest")
    os.makedirs(latest_dir, exist_ok=True)

    merged_candidates = {
        "system_positioning.canonical.lifecycle_status": {
            "selected_value": "运行中",
            "candidate_items": [{"source_mode": "document", "value": "运行中", "confidence": 0.92}],
            "confidence": 0.92,
            "selection_policy": "merge_all",
            "source_mode": "document",
        },
        "system_positioning.canonical.system_aliases": {
            "selected_value": ["UPAY"],
            "candidate_items": [{"source_mode": "document", "value": ["UPAY"], "confidence": 0.88}],
            "confidence": 0.88,
            "selection_policy": "merge_all",
            "source_mode": "document",
        },
    }
    with open(os.path.join(latest_dir, "merged_candidates.json"), "w", encoding="utf-8") as f:
        json.dump(merged_candidates, f, ensure_ascii=False, indent=2)

    updated = service.accept_card_candidate("统一支付平台", card_key="system_identity", actor={"username": "pm"})

    canonical = updated["profile_data"]["system_positioning"]["canonical"]
    assert canonical["lifecycle_status"] == "运行中"
    assert canonical["system_aliases"] == ["UPAY"]
    assert "system_identity" not in updated["card_candidates"]
    assert updated["domain_summary"]["system_positioning"]["candidate_count"] == 0


def test_system_profile_service_v27_ignore_card_candidate_allows_stale_projection_candidate_when_value_matches_profile(tmp_path, monkeypatch):
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
                        "architecture_layer": "",
                        "target_users": ["柜面"],
                        "service_scope": "支付统一受理",
                        "system_boundary": [],
                        "lifecycle_status": "运行中",
                        "system_aliases": ["UPAY"],
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

    workspace_path = service.repository.get_workspace_path(system_id="SYS-001")
    latest_dir = os.path.join(workspace_path, "candidate", "latest")
    os.makedirs(latest_dir, exist_ok=True)

    merged_candidates = {
        "system_positioning.canonical.lifecycle_status": {
            "selected_value": "运行中",
            "candidate_items": [{"source_mode": "document", "value": "运行中", "confidence": 0.92}],
            "confidence": 0.92,
            "selection_policy": "merge_all",
            "source_mode": "document",
        },
        "system_positioning.canonical.system_aliases": {
            "selected_value": ["UPAY"],
            "candidate_items": [{"source_mode": "document", "value": ["UPAY"], "confidence": 0.88}],
            "confidence": 0.88,
            "selection_policy": "merge_all",
            "source_mode": "document",
        },
    }
    with open(os.path.join(latest_dir, "merged_candidates.json"), "w", encoding="utf-8") as f:
        json.dump(merged_candidates, f, ensure_ascii=False, indent=2)

    updated = service.ignore_card_candidate("统一支付平台", card_key="system_identity", actor={"username": "pm"})

    ignored = updated["ai_suggestion_ignored"]
    assert ignored["system_positioning.canonical.lifecycle_status"] == "运行中"
    assert ignored["system_positioning.canonical.system_aliases"] == ["UPAY"]
    assert "system_identity" not in updated["card_candidates"]
    assert updated["domain_summary"]["system_positioning"]["candidate_count"] == 0


def test_system_profile_service_v27_restore_card_baseline_restores_high_trust_card_content(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(settings, "REPORT_DIR", str(data_dir))
    monkeypatch.setattr(settings, "ENABLE_V27_PROFILE_SCHEMA", True)
    system_profile_service._system_profile_service = None

    service = system_profile_service.get_system_profile_service()
    service.apply_v27_field_updates(
        "统一支付平台",
        system_id="SYS-001",
        field_updates={
            "integration_interfaces.canonical.provided_services": [
                {"service_name": "支付路由服务", "peer_system": "核心账务"}
            ],
        },
        field_sources={
            "integration_interfaces.canonical.provided_services": {
                "source": "governance",
            }
        },
        actor={"username": "system"},
    )
    service.apply_v27_field_updates(
        "统一支付平台",
        system_id="SYS-001",
        field_updates={
            "integration_interfaces.canonical.provided_services": [
                {"service_name": "支付路由服务", "peer_system": "清算平台"}
            ],
        },
        field_sources={
            "integration_interfaces.canonical.provided_services": {
                "source": "manual",
            }
        },
        actor={"username": "pm"},
    )

    restored = service.restore_card_baseline("统一支付平台", card_key="provided_capabilities", actor={"username": "pm"})

    provided = restored["profile_data"]["integration_interfaces"]["canonical"]["provided_services"]
    assert provided == [{"service_name": "支付路由服务", "peer_system": "核心账务"}]


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

    assert ignored["ai_suggestion_ignored"]["constraints_risks.canonical.risk_items"] == [
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
