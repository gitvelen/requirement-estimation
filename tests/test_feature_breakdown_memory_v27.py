import os
import sys

import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.agent.feature_breakdown_agent import FeatureBreakdownAgent
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

    memory_service._memory_service = None
    system_profile_service._system_profile_service = None
    yield
    memory_service._memory_service = None
    system_profile_service._system_profile_service = None


def _seed_profile():
    profile_service = system_profile_service.get_system_profile_service()
    profile_service.ensure_profile("核心账务", system_id="SYS-001", actor={"username": "tester"})
    profile_service.apply_v27_field_updates(
        "核心账务",
        system_id="SYS-001",
        field_updates={
            "system_positioning.canonical.service_scope": "账户开户、销户与账务处理",
            "business_capabilities.canonical.functional_modules": ["账户服务", "客户管理"],
        },
        actor={"username": "tester"},
    )


def _seed_adjustment_memory():
    service = memory_service.get_memory_service()
    service.append_record(
        system_id="SYS-001",
        memory_type="function_point_adjustment",
        memory_subtype="task_feature_update",
        scene_id="task_feature_update",
        source_type="requirement_task",
        source_id="task_001",
        summary="PM 统一命名与模块归属",
        payload={
            "adjustment_types": ["naming_normalization", "module_mapping"],
            "modifications": [
                {
                    "adjustment_type": "naming_normalization",
                    "feature_name": "开户申请",
                    "field": "功能点",
                    "old_value": "开户申请",
                    "new_value": "开户注册",
                },
                {
                    "adjustment_type": "module_mapping",
                    "feature_name": "开户注册",
                    "field": "功能模块",
                    "old_value": "渠道接入",
                    "new_value": "账户服务",
                },
            ],
        },
        actor="tester",
    )


def test_breakdown_prompt_requires_source_item_coverage_and_no_invented_features():
    agent = FeatureBreakdownAgent(knowledge_service=None)

    prompt = agent._build_breakdown_prompt(
        requirement_content="1.不动产接口字段类型调整。\n2.押品系统新增DNS改造功能。",
        system_name="押品管理",
        system_type="主系统",
        memory_context={},
        knowledge_context="",
    )

    assert "原文编号项" in prompt
    assert "不得新增原文未明确提出的独立功能点" in prompt


def test_breakdown_with_context_applies_low_risk_adjustment_patterns(monkeypatch):
    _seed_profile()
    _seed_adjustment_memory()

    monkeypatch.setattr(llm_client, "chat_with_system_prompt", lambda **kwargs: "{}")
    monkeypatch.setattr(
        llm_client,
        "extract_json",
        lambda response: {
            "features": [
                {
                    "序号": "1.1",
                    "功能模块": "渠道接入",
                    "功能点": "开户申请",
                    "业务描述": "发起开户",
                    "预估人天": 1.0,
                    "复杂度": "中",
                    "备注": "",
                }
            ]
        },
    )

    agent = FeatureBreakdownAgent(knowledge_service=None)
    result = agent.breakdown_with_context(
        requirement_content="新增开户能力",
        system_name="核心账务",
        system_type="主系统",
        task_id="task_001",
    )

    assert result["context_degraded"] is False
    assert result["applied_adjustments"]
    assert result["features"][0]["功能点"] == "开户注册"
    assert result["features"][0]["功能模块"] == "账户服务"


def test_breakdown_with_context_marks_context_degraded_when_memory_read_fails(monkeypatch):
    monkeypatch.setattr(llm_client, "chat_with_system_prompt", lambda **kwargs: "{}")
    monkeypatch.setattr(
        llm_client,
        "extract_json",
        lambda response: {
            "features": [
                {
                    "序号": "1.1",
                    "功能模块": "渠道接入",
                    "功能点": "开户申请",
                    "业务描述": "发起开户",
                    "预估人天": 1.0,
                    "复杂度": "中",
                    "备注": "",
                }
            ]
        },
    )

    service = memory_service.get_memory_service()
    monkeypatch.setattr(service, "query_records", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")))

    agent = FeatureBreakdownAgent(knowledge_service=None)
    result = agent.breakdown_with_context(
        requirement_content="新增开户能力",
        system_name="核心账务",
        system_type="主系统",
        task_id="task_002",
    )

    assert result["context_degraded"] is True
    assert result["features"][0]["功能点"] == "开户申请"
    assert result["applied_adjustments"] == []


def test_breakdown_with_context_uses_profile_context_without_system_profile_search(monkeypatch):
    _seed_profile()

    prompts = {}

    class DummyKnowledgeService:
        def search_similar_knowledge(self, **kwargs):
            raise AssertionError("feature breakdown should not search system_profile vectors")

    monkeypatch.setattr(
        llm_client,
        "chat_with_system_prompt",
        lambda **kwargs: prompts.setdefault("user_prompt", kwargs.get("user_prompt") or "") or "{}",
    )
    monkeypatch.setattr(
        llm_client,
        "extract_json",
        lambda response: {
            "features": [
                {
                    "序号": "1.1",
                    "功能模块": "账户服务",
                    "功能点": "开户注册",
                    "业务描述": "开户并落账",
                    "预估人天": 2.0,
                    "复杂度": "中",
                    "备注": "",
                }
            ]
        },
    )

    agent = FeatureBreakdownAgent(knowledge_service=DummyKnowledgeService())
    result = agent.breakdown_with_context(
        requirement_content="新增开户并完成账务落账",
        system_name="核心账务",
        system_type="主系统",
        task_id="task_ctx",
    )

    assert result["features"][0]["功能点"] == "开户注册"
    assert "系统画像参考" in prompts["user_prompt"]
    assert "账户开户、销户与账务处理" in prompts["user_prompt"]


def test_breakdown_with_context_retries_with_higher_token_budget_when_json_is_truncated(monkeypatch):
    responses = [
        """{
  "system": "核心账务",
  "features": [
    {
      "序号": "1.1",
      "功能模块": "账户服务",
      "功能点": "开户注册",
      "业务描述": "发起开户",
      "输入": "申请信息",
      "输出": "开户结果",
      "依赖": "无",
      "预估人天": 1,
      "复杂度": "中",
      "备注": "[归属依据] 属于账户服务""",
        """{
  "system": "核心账务",
  "features": [
    {
      "序号": "1.1",
      "功能模块": "账户服务",
      "功能点": "开户注册",
      "业务描述": "发起开户",
      "输入": "申请信息",
      "输出": "开户结果",
      "依赖": "无",
      "预估人天": 1,
      "复杂度": "中",
      "备注": "[归属依据] 属于账户服务\\n[系统约束] 复用既有开户主流程\\n[集成点] 无\\n[待确认] 无"
    }
  ]
}""",
    ]
    seen_max_tokens = []

    def fake_chat_with_system_prompt(**kwargs):
        seen_max_tokens.append(kwargs.get("max_tokens"))
        return responses[len(seen_max_tokens) - 1]

    monkeypatch.setattr(llm_client, "chat_with_system_prompt", fake_chat_with_system_prompt)

    agent = FeatureBreakdownAgent(knowledge_service=None)
    result = agent.breakdown_with_context(
        requirement_content="新增开户能力",
        system_name="核心账务",
        system_type="主系统",
        task_id="task_retry",
    )

    assert seen_max_tokens[0] == 3000
    assert seen_max_tokens[1] >= 8000
    assert result["features"][0]["功能点"] == "开户注册"


def test_breakdown_with_context_chunks_long_content_and_deduplicates_exact_matches(monkeypatch):
    prompts = []

    def fake_request_json_payload(*, user_prompt, operation_label, temperature=0.5):
        prompts.append(user_prompt)
        if "片段B" in user_prompt:
            return {
                "features": [
                    {
                        "序号": "1.1",
                        "功能模块": "数据模型优化",
                        "功能点": "新增FTP分类字段",
                        "业务描述": "来自片段B",
                        "预估人天": 1.0,
                        "复杂度": "中",
                        "备注": "B",
                    },
                    {
                        "序号": "1.2",
                        "功能模块": "数据模型优化",
                        "功能点": "新增FTP分类字段",
                        "业务描述": "来自片段B-重复",
                        "预估人天": 1.0,
                        "复杂度": "中",
                        "备注": "B-重复",
                    },
                ]
            }
        return {
            "features": [
                {
                    "序号": "1.1",
                    "功能模块": "数据模型优化",
                    "功能点": "新增同业往来新核心记账账号字段",
                    "业务描述": "来自片段A",
                    "预估人天": 1.0,
                    "复杂度": "中",
                    "备注": "A",
                }
            ]
        }

    monkeypatch.setattr(FeatureBreakdownAgent, "_request_json_payload", staticmethod(fake_request_json_payload))

    agent = FeatureBreakdownAgent(knowledge_service=None)
    result = agent.breakdown_with_context(
        requirement_content="片段A\n" + ("A" * 6200) + "\n【附件: attachment.docx】\n片段B\n" + ("B" * 6200),
        system_name="核心账务",
        system_type="主系统",
        task_id="task_chunk",
    )

    assert len(prompts) >= 2
    feature_names = [item["功能点"] for item in result["features"]]
    assert feature_names.count("新增FTP分类字段") == 1
    assert "新增同业往来新核心记账账号字段" in feature_names
