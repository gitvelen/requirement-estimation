import os
import sys

import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.agent.system_identification_agent import SystemIdentificationAgent
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
