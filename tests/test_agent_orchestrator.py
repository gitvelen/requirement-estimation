import os
import sys

import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.agent import agent_orchestrator as orchestrator_module
from backend.config.config import settings


class DummySystemAgent:
    def __init__(self, captured):
        self.captured = captured

    def identify_with_verdict(self, requirement_content, task_id=None):
        self.captured["requirement_content"] = requirement_content
        self.captured["task_id"] = task_id
        return {
            "final_verdict": "matched",
            "selected_systems": [
                {
                    "name": "管理会计集市",
                    "type": "主系统",
                    "is_standard": True,
                    "system_id": "SYS-MAS",
                }
            ],
            "candidate_systems": [],
            "maybe_systems": [],
            "questions": [],
            "reason_summary": "ok",
            "matched_aliases": ["管理会计集市"],
            "context_degraded": False,
            "degraded_reasons": [],
            "result_status": "success",
        }

    def build_ai_system_analysis(self, systems):
        return {
            "selected_systems": list(systems),
            "candidate_systems": [],
            "maybe_systems": [],
            "questions": [],
            "context_degraded": False,
            "degraded_reasons": [],
            "result_status": "success",
        }

    def validate_system_names_in_features(self, system_name, features):
        return features


class DummyFeatureAgent:
    def breakdown_with_context(self, requirement_content, system_name, system_type, task_id=None):
        return {
            "features": [
                {
                    "id": "feat_1",
                    "功能模块": "数据模型优化",
                    "功能点": "业绩分润接入",
                    "业务描述": requirement_content,
                    "预估人天": 1.0,
                }
            ],
            "context_degraded": False,
            "degraded_reasons": [],
            "applied_adjustments": [],
        }


class DummyProfileService:
    def build_estimation_context(self, system_name):
        return {}

    def record_estimation_context_artifact(self, **kwargs):
        return None


class DummyWorkEstimationAgent:
    def __init__(self):
        self._latest_estimation_details = {}

    def estimate(self, all_features, system_context_map=None):
        return []

    def apply_estimates_to_features(self, features, estimates):
        return features

    def get_expert_estimates_for_excel(self):
        return {}


class DummyExcelGenerator:
    def generate_report(self, task_id, requirement_name, systems_data, expert_estimates):
        return f"/tmp/{task_id}.xlsx"


@pytest.fixture(autouse=True)
def isolate_runtime(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_V27_RUNTIME", True)
    monkeypatch.setattr(settings, "KNOWLEDGE_ENABLED", False)


def test_process_requirement_uses_name_summary_and_content_for_identification(monkeypatch):
    captured = {}
    dummy_work_estimation = DummyWorkEstimationAgent()

    monkeypatch.setattr(
        orchestrator_module,
        "get_system_identification_agent",
        lambda knowledge_service=None: DummySystemAgent(captured),
    )
    monkeypatch.setattr(
        orchestrator_module,
        "get_feature_breakdown_agent",
        lambda knowledge_service=None: DummyFeatureAgent(),
    )
    monkeypatch.setattr(
        orchestrator_module,
        "get_system_profile_service",
        lambda: DummyProfileService(),
    )
    monkeypatch.setattr(orchestrator_module, "work_estimation_agent", dummy_work_estimation)
    monkeypatch.setattr(orchestrator_module, "excel_generator", DummyExcelGenerator())

    orchestrator = orchestrator_module.AgentOrchestrator(knowledge_service=None)
    orchestrator.process_requirement(
        "task_orchestrator_input",
        {
            "requirement_name": "2026年管理会计集市系统中收模型优化等共计33个迭代优化需求",
            "requirement_summary": "针对经营分析与绩效考核要求，管会集市进行系统优化",
            "requirement_content": "管会集市从取分润补录表改为接入CRM业绩分润数据",
        },
    )

    identification_text = captured["requirement_content"]
    assert "2026年管理会计集市系统中收模型优化等共计33个迭代优化需求" in identification_text
    assert "针对经营分析与绩效考核要求，管会集市进行系统优化" in identification_text
    assert "管会集市从取分润补录表改为接入CRM业绩分润数据" in identification_text
