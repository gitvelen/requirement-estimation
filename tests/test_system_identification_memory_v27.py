import os
import sys

import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.agent.system_identification_agent import DirectDecisionResolver, SystemIdentificationAgent
from backend.api import system_routes
from backend.config.config import settings
from backend.service import memory_service, system_profile_service
from backend.utils.llm_client import llm_client


@pytest.fixture(autouse=True)
def isolated_runtime(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(settings, "REPORT_DIR", str(data_dir))
    monkeypatch.setattr(settings, "ENABLE_V27_RUNTIME", True)
    monkeypatch.setattr(settings, "ENABLE_V27_PROFILE_SCHEMA", True)
    monkeypatch.setattr(system_routes, "CSV_PATH", str(data_dir / "system_list.csv"))

    memory_service._memory_service = None
    system_profile_service._system_profile_service = None
    yield
    memory_service._memory_service = None
    system_profile_service._system_profile_service = None


def test_identify_with_verdict_uses_catalog_alias_direct_match(monkeypatch):
    system_routes._write_systems(
        [
            {
                "id": "SYS-001",
                "name": "核心账务",
                "abbreviation": "HOP",
                "status": "运行中",
                "extra": {"aliases": ["核心账务系统"]},
            }
        ]
    )

    monkeypatch.setattr(
        llm_client,
        "chat_with_system_prompt",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("direct decision should not call llm")),
    )

    agent = SystemIdentificationAgent(knowledge_service=None)
    result = agent.identify_with_verdict("本次需求需要改造HOP开户流程", task_id="task_match")

    assert result["final_verdict"] == "matched"
    assert [item["name"] for item in result["selected_systems"]] == ["核心账务"]
    assert result["matched_aliases"] == ["HOP"]

    records = memory_service.get_memory_service().query_records("SYS-001", memory_type="identification_decision")
    assert records["total"] == 1
    assert records["items"][0]["payload"]["final_verdict"] == "matched"


def test_direct_resolver_prefers_stable_system_and_keeps_ambiguous_alias_as_maybe():
    system_routes._write_systems(
        [
            {"id": "SYS-MAS", "name": "管理会计集市", "abbreviation": "MAS", "status": "运行中", "extra": {}},
            {"id": "SYS-CRM", "name": "客户关系管理", "abbreviation": "CRM", "status": "运行中", "extra": {}},
            {"id": "SYS-CRM2", "name": "公司经营数据分析", "abbreviation": "CRM", "status": "下线中", "extra": {}},
        ]
    )

    resolver = DirectDecisionResolver()
    result = resolver.resolve(
        "\n".join(
            [
                "2026年管理会计集市系统中收模型优化等共计33个迭代优化需求",
                "针对经营分析与绩效考核要求，管会集市进行系统优化",
                "管会集市从取分润补录表改为接入CRM业绩分润数据",
            ]
        )
    )

    assert result["final_verdict"] == "matched"
    assert [item["name"] for item in result["selected_systems"]] == ["管理会计集市"]
    assert [item["name"] for item in result["maybe_systems"]] == ["客户关系管理", "公司经营数据分析"]
    assert [item["name"] for item in result["candidate_systems"]] == ["客户关系管理", "公司经营数据分析"]
    assert result["matched_aliases"] == ["管理会计集市"]
    assert result["questions"] == ["别名“CRM”可对应多个系统，请补充标准系统名称。"]


def test_direct_resolver_keeps_ambiguous_when_only_ambiguous_alias_is_present():
    system_routes._write_systems(
        [
            {"id": "SYS-CRM", "name": "客户关系管理", "abbreviation": "CRM", "status": "运行中", "extra": {}},
            {"id": "SYS-CRM2", "name": "公司经营数据分析", "abbreviation": "CRM", "status": "下线中", "extra": {}},
        ]
    )

    resolver = DirectDecisionResolver()
    result = resolver.resolve("本次需求需要接入CRM业绩分润数据")

    assert result["final_verdict"] == "ambiguous"
    assert result["selected_systems"] == []
    assert [item["name"] for item in result["candidate_systems"]] == ["客户关系管理", "公司经营数据分析"]
    assert result["questions"] == ["别名“CRM”可对应多个系统，请补充标准系统名称。"]


def test_identify_with_verdict_marks_ambiguous_when_llm_keeps_maybe_systems(monkeypatch):
    system_routes._write_systems(
        [
            {"id": "SYS-001", "name": "核心账务", "abbreviation": "HOP", "status": "运行中", "extra": {}},
            {"id": "SYS-002", "name": "支付中台", "abbreviation": "PAY", "status": "运行中", "extra": {}},
        ]
    )

    monkeypatch.setattr(llm_client, "chat_with_system_prompt", lambda **kwargs: "{}")
    monkeypatch.setattr(
        llm_client,
        "extract_json",
        lambda response: {
            "systems": [
                {
                    "name": "核心账务",
                    "type": "主系统",
                    "description": "账务处理",
                    "confidence": "高",
                    "reasons": ["命中账务关键字"],
                }
            ],
            "maybe_systems": ["支付中台"],
            "questions": ["是否还涉及支付联动？"],
        },
    )

    agent = SystemIdentificationAgent(knowledge_service=None)
    result = agent.identify_with_verdict("需求涉及账户与支付联动", task_id="task_ambiguous")

    assert result["final_verdict"] == "ambiguous"
    assert [item["name"] for item in result["selected_systems"]] == ["核心账务"]
    assert result["questions"] == ["是否还涉及支付联动？"]

    records = memory_service.get_memory_service().query_records("SYS-001", memory_type="identification_decision")
    assert records["total"] == 1
    assert records["items"][0]["payload"]["final_verdict"] == "ambiguous"


def test_identify_with_verdict_marks_unknown_when_nothing_is_selected(monkeypatch):
    system_routes._write_systems(
        [
            {"id": "SYS-001", "name": "核心账务", "abbreviation": "HOP", "status": "运行中", "extra": {}},
        ]
    )

    monkeypatch.setattr(llm_client, "chat_with_system_prompt", lambda **kwargs: "{}")
    monkeypatch.setattr(
        llm_client,
        "extract_json",
        lambda response: {
            "systems": [],
            "maybe_systems": [],
            "questions": ["请补充涉及的系统名称"],
        },
    )

    agent = SystemIdentificationAgent(knowledge_service=None)
    result = agent.identify_with_verdict("优化开户体验", task_id="task_unknown")

    assert result["final_verdict"] == "unknown"
    assert result["selected_systems"] == []
    assert result["questions"] == ["请补充涉及的系统名称"]


def test_identify_with_verdict_uses_profile_context_candidates_without_system_profile_vector_search(monkeypatch):
    system_routes._write_systems(
        [
            {"id": "SYS-001", "name": "核心账务", "abbreviation": "HOP", "status": "运行中", "extra": {}},
            {"id": "SYS-002", "name": "支付中台", "abbreviation": "PAY", "status": "运行中", "extra": {}},
        ]
    )

    profile_service = system_profile_service.get_system_profile_service()
    profile_service.ensure_profile("核心账务", system_id="SYS-001", actor={"username": "tester"})
    profile_service.apply_v27_field_updates(
        "核心账务",
        system_id="SYS-001",
        field_updates={
            "system_positioning.canonical.service_scope": "账户开户、销户与账务处理",
            "business_capabilities.canonical.functional_modules": ["账户服务", "总账处理"],
        },
        actor={"username": "tester"},
    )

    prompts = {}

    class DummyKnowledgeService:
        def search_similar_knowledge(self, **kwargs):
            raise AssertionError("system_profile should not use vector search")

    monkeypatch.setattr(
        llm_client,
        "chat_with_system_prompt",
        lambda **kwargs: prompts.setdefault("user_prompt", kwargs.get("user_prompt") or "") or "{}",
    )
    monkeypatch.setattr(
        llm_client,
        "extract_json",
        lambda response: {
            "systems": [
                {
                    "name": "核心账务",
                    "type": "主系统",
                    "description": "账务处理",
                    "confidence": "高",
                    "reasons": ["画像命中开户与账务处理语义"],
                }
            ],
            "maybe_systems": [],
            "questions": [],
        },
    )

    agent = SystemIdentificationAgent(knowledge_service=DummyKnowledgeService())
    result = agent.identify_with_verdict("新增开户校验并同步账务处理", task_id="task_ctx")

    assert result["final_verdict"] == "matched"
    assert [item["name"] for item in result["selected_systems"]] == ["核心账务"]
    assert "候选系统榜单" in prompts["user_prompt"]
    assert "账户开户、销户与账务处理" in prompts["user_prompt"]


def test_search_relevant_profile_contexts_does_not_build_esb_context_for_relevance(monkeypatch):
    system_routes._write_systems(
        [
            {"id": "SYS-001", "name": "核心账务", "abbreviation": "HOP", "status": "运行中", "extra": {}},
        ]
    )

    profile_service = system_profile_service.get_system_profile_service()
    profile_service.ensure_profile("核心账务", system_id="SYS-001", actor={"username": "tester"})
    profile_service.apply_v27_field_updates(
        "核心账务",
        system_id="SYS-001",
        field_updates={
            "system_positioning.canonical.service_scope": "账户开户、销户与账务处理",
            "business_capabilities.canonical.functional_modules": ["账户服务", "总账处理"],
        },
        actor={"username": "tester"},
    )

    monkeypatch.setattr(
        profile_service,
        "_build_esb_context",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("relevance scoring should not build esb context")),
    )
    monkeypatch.setattr(
        profile_service,
        "build_estimation_context",
        lambda system_name: (_ for _ in ()).throw(AssertionError("relevance scoring should not build estimation context")),
    )

    results = profile_service.search_relevant_profile_contexts("新增开户校验并同步账务处理", limit=3)

    assert len(results) == 1
    assert results[0]["system_name"] == "核心账务"


def test_identify_with_verdict_uses_budgeted_llm_timeout(monkeypatch):
    system_routes._write_systems(
        [
            {"id": "SYS-001", "name": "核心账务", "abbreviation": "HOP", "status": "运行中", "extra": {}},
        ]
    )

    monkeypatch.setattr(settings, "PROFILE_IMPORT_LLM_TIMEOUT", 7)
    monkeypatch.setattr(settings, "PROFILE_IMPORT_LLM_RETRY_TIMES", 1)

    captured = {}
    monkeypatch.setattr(
        llm_client,
        "chat_with_system_prompt",
        lambda **kwargs: captured.update(kwargs) or "{}",
    )
    monkeypatch.setattr(
        llm_client,
        "extract_json",
        lambda response: {
            "systems": [
                {
                    "name": "核心账务",
                    "type": "主系统",
                    "description": "账务处理",
                    "confidence": "高",
                    "reasons": ["预算内完成识别"],
                }
            ],
            "maybe_systems": [],
            "questions": [],
        },
    )

    agent = SystemIdentificationAgent(knowledge_service=None)
    result = agent.identify_with_verdict("新增开户校验并同步账务处理", task_id="task_budget")

    assert result["final_verdict"] == "matched"
    assert captured["timeout"] == 7
    assert captured["retry_times"] == 1
