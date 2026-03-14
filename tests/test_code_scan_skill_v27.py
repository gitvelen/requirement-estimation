import os
import sys

import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.config.config import settings
from backend.service import memory_service, runtime_execution_service, system_profile_service
from backend.service.code_scan_skill_adapter import CodeScanSkillAdapter


@pytest.fixture(autouse=True)
def isolated_runtime(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(settings, "REPORT_DIR", str(data_dir))
    monkeypatch.setattr(settings, "ENABLE_V27_RUNTIME", True)
    monkeypatch.setattr(settings, "ENABLE_V27_PROFILE_SCHEMA", True)

    memory_service._memory_service = None
    runtime_execution_service._runtime_execution_service = None
    system_profile_service._system_profile_service = None

    yield

    memory_service._memory_service = None
    runtime_execution_service._runtime_execution_service = None
    system_profile_service._system_profile_service = None


def _sample_result():
    return {
        "system_id": "sys_hop",
        "system_name": "HOP",
        "items": [
            {
                "entry_type": "http_api",
                "entry_id": "GET /api/demo/query",
                "summary": "query",
                "keywords": ["query", "demo"],
                "related_calls": [{"type": "http", "target": "external"}],
                "location": {"file": "DemoController.java", "line": 7},
            }
        ],
        "analysis": {
            "ast_summary": {"files_total": 1, "files_with_entries": 1, "entry_count": 1},
            "call_graph": {"node_count": 2, "edge_count": 1},
            "service_dependencies": {"by_type": {"http": 1}, "dependencies": [{"dependency": "http:external", "count": 1}]},
            "data_flow": {"entities": [{"entity": "DemoController", "operations": ["read"]}], "entity_count": 1},
            "complexity": {"method_count": 1, "avg_cyclomatic_complexity": 2.0, "max_cyclomatic_complexity": 2},
            "impact": {
                "systems": [{"system_id": "sys_hop", "system_name": "HOP"}],
                "features": ["query"],
                "apis": ["GET /api/demo/query"],
                "evidence": [{"file": "DemoController.java", "line": 7, "entry_id": "GET /api/demo/query"}],
            },
        },
        "metrics": {"m1": 1.0, "m2": 1.0, "m3": 1.0, "m4": 1.0, "m5": 1.0, "m6": 1.0},
    }


def test_code_scan_skill_adapter_writes_suggestions_only_and_memory():
    adapter = CodeScanSkillAdapter()

    result = adapter.apply_scan_result(
        system_id="sys_hop",
        system_name="HOP",
        execution_id="exec_code_scan_1",
        source_file="repo.zip",
        result_payload=_sample_result(),
        actor={"username": "tester"},
    )

    assert result["status"] == "completed"
    assert "technical_architecture.canonical.tech_stack" in result["suggestions"]
    assert "technical_architecture.canonical.extensions.code_structure" in result["suggestions"]
    assert "technical_architecture.canonical.extensions.feature_context" in result["suggestions"]

    profile = system_profile_service.get_system_profile_service().get_profile("HOP")
    assert profile
    assert profile["profile_data"]["technical_architecture"]["canonical"]["tech_stack"]["languages"] == []
    assert profile["ai_suggestions"]["technical_architecture.canonical.tech_stack"]["decision_policy"] == "suggestion_only"

    records = memory_service.get_memory_service().query_records("sys_hop", memory_type="profile_update")
    assert records["total"] == 1
    assert records["items"][0]["memory_subtype"] == "code_scan_suggestion"


def test_code_scan_skill_adapter_returns_partial_success_when_memory_write_fails(monkeypatch):
    adapter = CodeScanSkillAdapter()
    service = memory_service.get_memory_service()
    monkeypatch.setattr(service, "append_record", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("memory boom")))

    result = adapter.apply_scan_result(
        system_id="sys_hop",
        system_name="HOP",
        execution_id="exec_code_scan_2",
        source_file="repo.zip",
        result_payload=_sample_result(),
        actor={"username": "tester"},
    )

    assert result["status"] == "partial_success"
    assert "memory boom" in (result["memory_error"] or "")

    profile = system_profile_service.get_system_profile_service().get_profile("HOP")
    assert profile
    assert "technical_architecture.canonical.tech_stack" in profile["ai_suggestions"]
