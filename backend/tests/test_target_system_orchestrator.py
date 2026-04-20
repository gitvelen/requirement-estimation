import os
import sys
from datetime import datetime

import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.agent import agent_orchestrator as orchestrator_module
from backend.api import routes as task_routes
from backend.config.config import settings


class SpecificModeSystemAgent:
    def __init__(self, calls):
        self.calls = calls

    def identify_with_verdict(self, requirement_content, task_id=None):
        self.calls["identify"] += 1
        raise AssertionError("specific 模式不应执行自动系统识别")

    def identify(self, requirement_content, task_id=None):
        self.calls["identify"] += 1
        raise AssertionError("specific 模式不应执行自动系统识别")


class UnlimitedModeSystemAgent:
    def __init__(self, calls):
        self.calls = calls

    def identify_with_verdict(self, requirement_content, task_id=None):
        self.calls["identify"] += 1
        self.calls["identification_content"] = requirement_content
        self.calls["task_id"] = task_id
        return {
            "final_verdict": "matched",
            "selected_systems": [
                {"name": "支付系统", "type": "主系统", "is_standard": True, "system_id": "SYS-PAY"},
                {"name": "核心账务", "type": "从系统", "is_standard": True, "system_id": "SYS-CORE"},
            ],
            "candidate_systems": [],
            "maybe_systems": [],
            "questions": [],
            "reason_summary": "ok",
            "matched_aliases": ["支付系统", "核心账务"],
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
        for feature in features:
            feature["系统"] = system_name
        return features


class RecordingFeatureAgent:
    def __init__(self, calls, features_by_system):
        self.calls = calls
        self.features_by_system = features_by_system

    def breakdown_with_context(self, requirement_content, system_name, system_type, task_id=None):
        self.calls["feature_calls"].append(
            {
                "requirement_content": requirement_content,
                "system_name": system_name,
                "system_type": system_type,
                "task_id": task_id,
            }
        )
        return {
            "features": list(self.features_by_system.get(system_name, [])),
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


def test_specific_mode_skips_identification_and_keeps_single_system(monkeypatch):
    calls = {"identify": 0, "feature_calls": []}
    features_by_system = {
        "支付系统": [
            {
                "id": "feat_pay_1",
                "序号": "1.1",
                "功能模块": "支付接入",
                "功能点": "支付订单同步",
                "业务描述": "全文需求输入",
                "预估人天": 1.0,
                "复杂度": "中",
            }
        ]
    }

    monkeypatch.setattr(
        orchestrator_module,
        "get_system_identification_agent",
        lambda knowledge_service=None: SpecificModeSystemAgent(calls),
    )
    monkeypatch.setattr(
        orchestrator_module,
        "get_feature_breakdown_agent",
        lambda knowledge_service=None: RecordingFeatureAgent(calls, features_by_system),
    )
    monkeypatch.setattr(orchestrator_module, "get_system_profile_service", lambda: DummyProfileService())
    monkeypatch.setattr(orchestrator_module, "work_estimation_agent", DummyWorkEstimationAgent())
    monkeypatch.setattr(orchestrator_module, "excel_generator", DummyExcelGenerator())

    orchestrator = orchestrator_module.AgentOrchestrator(knowledge_service=None)
    report_path, systems_data, ai_system_analysis, ai_original_output = orchestrator.process_requirement(
        "task_specific_mode",
        {
            "requirement_name": "支付需求",
            "requirement_summary": "支付摘要",
            "requirement_content": "全文需求输入",
            "target_system_mode": "specific",
            "target_system_name": "支付系统",
        },
    )

    assert report_path == "/tmp/task_specific_mode.xlsx"
    assert calls["identify"] == 0
    assert calls["feature_calls"] == [
        {
            "requirement_content": "全文需求输入",
            "system_name": "支付系统",
            "system_type": "主系统",
            "task_id": "task_specific_mode",
        }
    ]
    assert list(systems_data.keys()) == ["支付系统"]
    assert ai_system_analysis["selected_systems"][0]["name"] == "支付系统"
    assert ai_original_output["system_recognition"]["final_verdict"] == "skipped"


def test_specific_mode_fails_when_no_features(monkeypatch):
    calls = {"identify": 0, "feature_calls": []}

    monkeypatch.setattr(
        orchestrator_module,
        "get_system_identification_agent",
        lambda knowledge_service=None: SpecificModeSystemAgent(calls),
    )
    monkeypatch.setattr(
        orchestrator_module,
        "get_feature_breakdown_agent",
        lambda knowledge_service=None: RecordingFeatureAgent(calls, {"支付系统": []}),
    )
    monkeypatch.setattr(orchestrator_module, "get_system_profile_service", lambda: DummyProfileService())
    monkeypatch.setattr(orchestrator_module, "work_estimation_agent", DummyWorkEstimationAgent())
    monkeypatch.setattr(orchestrator_module, "excel_generator", DummyExcelGenerator())

    orchestrator = orchestrator_module.AgentOrchestrator(knowledge_service=None)

    with pytest.raises(ValueError, match="支付系统.*未拆分出相关功能点"):
        orchestrator.process_requirement(
            "task_specific_empty",
            {
                "requirement_name": "支付需求",
                "requirement_content": "全文需求输入",
                "target_system_mode": "specific",
                "target_system_name": "支付系统",
            },
        )


def test_unlimited_mode_still_identifies_before_breakdown(monkeypatch):
    calls = {"identify": 0, "feature_calls": []}
    features_by_system = {
        "支付系统": [
            {
                "id": "feat_pay_1",
                "序号": "1.1",
                "功能模块": "支付接入",
                "功能点": "支付订单同步",
                "业务描述": "全文需求输入",
                "预估人天": 1.0,
                "复杂度": "中",
            }
        ],
        "核心账务": [
            {
                "id": "feat_core_1",
                "序号": "1.1",
                "功能模块": "账务处理",
                "功能点": "凭证生成",
                "业务描述": "全文需求输入",
                "预估人天": 1.0,
                "复杂度": "中",
            }
        ],
    }

    monkeypatch.setattr(
        orchestrator_module,
        "get_system_identification_agent",
        lambda knowledge_service=None: UnlimitedModeSystemAgent(calls),
    )
    monkeypatch.setattr(
        orchestrator_module,
        "get_feature_breakdown_agent",
        lambda knowledge_service=None: RecordingFeatureAgent(calls, features_by_system),
    )
    monkeypatch.setattr(orchestrator_module, "get_system_profile_service", lambda: DummyProfileService())
    monkeypatch.setattr(orchestrator_module, "work_estimation_agent", DummyWorkEstimationAgent())
    monkeypatch.setattr(orchestrator_module, "excel_generator", DummyExcelGenerator())

    orchestrator = orchestrator_module.AgentOrchestrator(knowledge_service=None)
    _, systems_data, _, ai_original_output = orchestrator.process_requirement(
        "task_unlimited_mode",
        {
            "requirement_name": "支付需求",
            "requirement_summary": "支付摘要",
            "requirement_content": "全文需求输入",
            "target_system_mode": "unlimited",
            "target_system_name": "",
        },
    )

    assert calls["identify"] == 1
    assert set(systems_data.keys()) == {"支付系统", "核心账务"}
    assert ai_original_output["system_recognition"]["final_verdict"] == "matched"


def test_process_task_sync_forwards_target_system_selection(monkeypatch, tmp_path):
    data_dir = tmp_path / "data"
    upload_dir = tmp_path / "uploads"
    data_dir.mkdir(parents=True, exist_ok=True)
    upload_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(settings, "REPORT_DIR", str(data_dir))
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload_dir))
    monkeypatch.setattr(task_routes, "TASK_STORE_PATH", str(data_dir / "task_storage.json"))
    monkeypatch.setattr(task_routes, "TASK_STORE_LOCK_PATH", str(data_dir / "task_storage.json.lock"))

    task_id = "task_sync_specific"
    file_path = tmp_path / "requirements.docx"
    file_path.write_bytes(b"fake-docx")

    with task_routes._task_storage_context() as data:
        data[task_id] = {
            "task_id": task_id,
            "name": "同步任务",
            "filename": "requirements.docx",
            "file_path": str(file_path),
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "target_system_mode": "specific",
            "target_system_name": "支付系统",
        }

    monkeypatch.setattr(
        task_routes.docx_parser,
        "parse",
        lambda path: {
            "requirement_name": "支付需求",
            "requirement_summary": "支付摘要",
            "requirement_content": "全文需求输入",
            "basic_info": {},
            "all_paragraphs": ["全文需求输入"],
        },
    )

    captured = {}

    class DummyOrchestrator:
        def process_with_retry(self, task_id, requirement_data, max_retry=3, progress_callback=None):
            captured["task_id"] = task_id
            captured["requirement_data"] = dict(requirement_data)
            return (
                "/tmp/task_sync_specific.xlsx",
                {"支付系统": []},
                {
                    "selected_systems": [{"name": "支付系统", "type": "主系统"}],
                    "candidate_systems": [],
                    "maybe_systems": [],
                    "questions": [],
                    "context_degraded": False,
                    "degraded_reasons": [],
                    "result_status": "success",
                },
                {
                    "system_recognition": {"final_verdict": "skipped"},
                    "feature_split": {"systems_data": {"支付系统": []}},
                    "work_estimation": {"total_workload": 0},
                },
            )

    monkeypatch.setattr(task_routes, "get_agent_orchestrator", lambda: DummyOrchestrator())

    task_routes.process_task_sync(task_id, str(file_path))

    assert captured["task_id"] == task_id
    assert captured["requirement_data"]["target_system_mode"] == "specific"
    assert captured["requirement_data"]["target_system_name"] == "支付系统"
