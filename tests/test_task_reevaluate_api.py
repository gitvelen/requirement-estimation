import os
import sys
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.app import app
from backend.api import routes as task_routes
from backend.agent.work_estimation_agent import WorkEstimationAgent, work_estimation_agent
from backend.config.config import settings
from backend.service import profile_artifact_service
from backend.service import system_profile_service
from backend.service import user_service


@pytest.fixture()
def client(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    artifact_dir = tmp_path / "profile_artifacts"

    monkeypatch.setattr(settings, "REPORT_DIR", str(data_dir))
    monkeypatch.setattr(settings, "PROFILE_ARTIFACT_ROOT", str(artifact_dir), raising=False)
    monkeypatch.setattr(settings, "DEBUG", False)

    monkeypatch.setattr(user_service, "USER_STORE_PATH", str(data_dir / "users.json"))
    monkeypatch.setattr(user_service, "USER_STORE_LOCK_PATH", str(data_dir / "users.json.lock"))

    monkeypatch.setattr(task_routes, "TASK_STORE_PATH", str(data_dir / "task_storage.json"))
    monkeypatch.setattr(task_routes, "TASK_STORE_LOCK_PATH", str(data_dir / "task_storage.json.lock"))
    system_profile_service._system_profile_service = None
    profile_artifact_service._profile_artifact_service = None

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


def _seed_task(task_id: str, creator_id: str):
    task = {
        "task_id": task_id,
        "name": "重评估任务",
        "creator_id": creator_id,
        "status": "completed",
        "ai_status": "completed",
        "workflow_status": "draft",
        "created_at": datetime.now().isoformat(),
        "systems_data": {
            "HOP": [
                {
                    "id": "feat_1",
                    "功能点": "开户",
                    "备注": "旧备注",
                    "预估人天": 2.0,
                    "cosmic_analysis": {
                        "data_movements": {
                            "E": [{"data_group": "开户请求", "description": "录入开户信息"}],
                            "X": [{"data_group": "开户结果", "description": "返回开户结果"}],
                            "R": [{"data_group": "客户档案", "description": "读取客户基础信息"}],
                            "W": [{"data_group": "账户台账", "description": "写入新账户"}],
                        },
                        "cff": 4,
                        "counting_basis": "开户功能涉及 1 次录入、1 次返回、1 次读取、1 次写入。",
                    },
                }
            ]
        },
        "modifications": [
            {
                "id": "mod_1",
                "operation": "update",
                "system": "HOP",
                "feature_id": "feat_1",
            }
        ],
    }

    with task_routes._task_storage_context() as data:
        data[task_id] = task


def test_reevaluate_returns_404_when_task_not_found(client):
    manager = _seed_user("reeval_mgr_nf", "pwd123", ["manager"])
    token = _login(client, "reeval_mgr_nf", "pwd123")

    response = client.post(
        "/api/v1/tasks/not-exists/reevaluate",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json().get("error_code") == "task_not_found"


def test_reevaluate_idempotent_returns_existing_running_job(client):
    manager = _seed_user("reeval_mgr_running", "pwd123", ["manager"])
    token = _login(client, "reeval_mgr_running", "pwd123")

    task_id = "task_reeval_running"
    _seed_task(task_id, manager["id"])

    with task_routes._task_storage_context() as data:
        data[task_id]["reevaluate_jobs"] = [
            {
                "job_id": "reeval_existing",
                "status": "running",
                "created_at": datetime.now().isoformat(),
            }
        ]

    response = client.post(
        f"/api/v1/tasks/{task_id}/reevaluate",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload.get("job_id") == "reeval_existing"
    assert payload.get("status") == "running"


def test_reevaluate_returns_skipped_when_auto_disabled(client, monkeypatch):
    manager = _seed_user("reeval_mgr_skip", "pwd123", ["manager"])
    token = _login(client, "reeval_mgr_skip", "pwd123")

    task_id = "task_reeval_skip"
    _seed_task(task_id, manager["id"])

    monkeypatch.setattr(settings, "V21_AUTO_REEVAL_ENABLED", False)
    monkeypatch.setattr(settings, "V21_AI_REMARK_ENABLED", True)

    response = client.post(
        f"/api/v1/tasks/{task_id}/reevaluate",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload.get("job_id") is None
    assert payload.get("status") == "skipped"


def test_reevaluate_creates_pending_job_when_enabled(client, monkeypatch):
    manager = _seed_user("reeval_mgr_ok", "pwd123", ["manager"])
    token = _login(client, "reeval_mgr_ok", "pwd123")

    task_id = "task_reeval_enabled"
    _seed_task(task_id, manager["id"])

    monkeypatch.setattr(settings, "V21_AUTO_REEVAL_ENABLED", True)

    response = client.post(
        f"/api/v1/tasks/{task_id}/reevaluate",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload.get("job_id")
    assert payload.get("status") == "pending"


def test_reevaluate_accepts_missing_body(client, monkeypatch):
    manager = _seed_user("reeval_mgr_no_body", "pwd123", ["manager"])
    token = _login(client, "reeval_mgr_no_body", "pwd123")

    task_id = "task_reeval_no_body"
    _seed_task(task_id, manager["id"])

    monkeypatch.setattr(settings, "V21_AUTO_REEVAL_ENABLED", False)
    monkeypatch.setattr(settings, "V21_AI_REMARK_ENABLED", True)

    response = client.post(
        f"/api/v1/tasks/{task_id}/reevaluate",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload.get("job_id") is None
    assert payload.get("status") == "skipped"


def test_task_estimate_returns_three_point_fields_and_persists_baseline(client, monkeypatch):
    manager = _seed_user("estimate_mgr_ok", "pwd123", ["manager"])
    token = _login(client, "estimate_mgr_ok", "pwd123")

    task_id = "task_estimate_ok"
    _seed_task(task_id, manager["id"])

    monkeypatch.setattr(
        work_estimation_agent,
        "estimate_three_point_for_feature",
        lambda *args, **kwargs: {
            "optimistic": 1.5,
            "most_likely": 2.5,
            "pessimistic": 4.0,
            "expected": 2.58,
            "reasoning": "规则复杂且涉及跨系统接口",
        },
        raising=False,
    )

    response = client.post(
        f"/api/v1/tasks/{task_id}/estimate",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload.get("degraded") is False
    features = payload.get("features") or []
    assert len(features) == 1
    first = features[0]
    assert first.get("name") == "开户"
    assert first.get("optimistic") == 1.5
    assert first.get("most_likely") == 2.5
    assert first.get("pessimistic") == 4.0
    assert first.get("expected") == 2.58
    assert first.get("reasoning")
    assert first.get("original_estimate") == 2.0

    with task_routes._task_storage_context() as data:
        feature = data[task_id]["systems_data"]["HOP"][0]
        assert feature.get("original_estimate") == 2.0
        assert feature.get("预估人天") == 2.58


def test_task_estimate_degrades_to_original_estimate_on_llm_failure(client, monkeypatch):
    manager = _seed_user("estimate_mgr_degraded", "pwd123", ["manager"])
    token = _login(client, "estimate_mgr_degraded", "pwd123")

    task_id = "task_estimate_degraded"
    _seed_task(task_id, manager["id"])

    def _raise_llm_error(*args, **kwargs):
        raise RuntimeError("llm unavailable")

    monkeypatch.setattr(
        work_estimation_agent,
        "estimate_three_point_for_feature",
        _raise_llm_error,
        raising=False,
    )

    response = client.post(
        f"/api/v1/tasks/{task_id}/estimate",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload.get("degraded") is True
    assert payload.get("code") == "LLM_ESTIMATION_DEGRADED"
    features = payload.get("features") or []
    assert len(features) == 1
    first = features[0]
    assert first.get("optimistic") is None
    assert first.get("most_likely") is None
    assert first.get("pessimistic") is None
    assert first.get("reasoning") is None
    assert first.get("expected") == 2.0
    assert first.get("original_estimate") == 2.0


def test_task_estimate_uses_profile_context_and_returns_context_metadata(client, monkeypatch):
    manager = _seed_user("estimate_mgr_ctx", "pwd123", ["manager"])
    token = _login(client, "estimate_mgr_ctx", "pwd123")

    task_id = "task_estimate_ctx"
    _seed_task(task_id, manager["id"])

    monkeypatch.setattr(settings, "ENABLE_V27_PROFILE_SCHEMA", True)

    profile_service = system_profile_service.get_system_profile_service()
    profile_service.ensure_profile("HOP", system_id="sys_hop", actor={"id": manager["id"]})
    profile_service.apply_v27_field_updates(
        "HOP",
        system_id="sys_hop",
        field_updates={
            "system_positioning.canonical.service_scope": "账户开户与账务处理",
        },
        actor={"id": manager["id"]},
    )

    artifact_service = profile_artifact_service.get_profile_artifact_service()
    artifact_service.append_layer_record(
        layer="wiki",
        system_id="sys_hop",
        payload={
            "system_id": "sys_hop",
            "target_fields": [
                "system_positioning.canonical.service_scope",
                "technical_architecture.canonical.architecture_style",
            ],
            "candidates": {
                "technical_architecture.canonical.architecture_style": {
                    "value": "分层微服务架构",
                    "confidence": 0.92,
                    "reason": "技术方案明确提到分层微服务部署",
                }
            },
        },
        operator_id=manager["id"],
        latest_file_name="candidate_profile.json",
    )

    captured_context = {}

    def _capture_estimate(feature, **kwargs):
        captured_context[feature["id"]] = kwargs
        return {
            "optimistic": 1.5,
            "most_likely": 2.5,
            "pessimistic": 4.0,
            "expected": 2.58,
            "reasoning": "规则复杂且涉及跨系统接口",
        }

    monkeypatch.setattr(
        work_estimation_agent,
        "estimate_three_point_for_feature",
        _capture_estimate,
        raising=False,
    )

    response = client.post(
        f"/api/v1/tasks/{task_id}/estimate",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    features = payload.get("features") or []
    assert len(features) == 1
    first = features[0]
    assert first.get("profile_context_used") is True
    assert first.get("context_source") == "canonical+wiki_candidate"
    assert "账户开户与账务处理" in captured_context["feat_1"]["system_context"]
    assert "分层微服务架构" in captured_context["feat_1"]["system_context"]

    with task_routes._task_storage_context() as data:
        feature = data[task_id]["systems_data"]["HOP"][0]
        assert feature.get("profile_context_used") is True
        assert feature.get("context_source") == "canonical+wiki_candidate"

    output_items = artifact_service.list_layer_records(layer="output", system_id="sys_hop")
    estimation_items = [
        item
        for item in output_items
        if isinstance(item.get("payload"), dict) and item["payload"].get("output_type") == "estimation_context"
    ]
    assert len(estimation_items) == 1
    estimation_payload = estimation_items[0]["payload"]
    assert estimation_payload["task_id"] == task_id
    assert estimation_payload["context_source"] == "canonical+wiki_candidate"
    assert estimation_payload["features"][0]["feature_id"] == "feat_1"
    workspace_path = artifact_service.repository.get_workspace_path(system_id="sys_hop")
    assert workspace_path
    latest_estimation_path = os.path.join(workspace_path, "audit", "estimation", "latest_estimation.json")
    assert os.path.exists(latest_estimation_path)


def test_work_estimation_agent_estimate_uses_system_context_map():
    agent = WorkEstimationAgent()
    captured = []

    def _capture(feature, **kwargs):
        captured.append(
            {
                "feature_id": feature["id"],
                "system_context": kwargs.get("system_context"),
            }
        )
        return {
            "optimistic": 1.0,
            "most_likely": 2.0,
            "pessimistic": 3.0,
            "expected": 2.0,
            "reasoning": "基于系统画像进行估算",
            "original_estimate": 2.0,
        }

    agent.estimate_three_point_for_feature = _capture

    estimates = agent.estimate(
        [
            {"id": "feat_hop", "系统": "HOP", "功能点": "开户", "预估人天": 2.0},
            {"id": "feat_crm", "系统": "CRM", "功能点": "客户查询", "预估人天": 1.0},
        ],
        system_context_map={
            "HOP": {
                "text": "HOP 上下文",
                "profile_context_used": True,
                "context_source": "canonical",
            },
            "CRM": {
                "text": "",
                "profile_context_used": False,
                "context_source": "none",
            },
        },
    )

    assert estimates["feat_hop"] == 2.0
    assert estimates["feat_crm"] == 2.0
    assert captured[0]["system_context"] == "HOP 上下文"
    assert captured[1]["system_context"] == ""
    assert agent._latest_estimation_details["feat_hop"]["profile_context_used"] is True
    assert agent._latest_estimation_details["feat_hop"]["context_source"] == "canonical"
    assert agent._latest_estimation_details["feat_crm"]["profile_context_used"] is False
    assert agent._latest_estimation_details["feat_crm"]["context_source"] == "none"


def test_task_estimate_injects_rule_context_and_preserves_requirement_content(client, monkeypatch):
    manager = _seed_user("estimate_mgr_rule_ctx", "pwd123", ["manager"])
    token = _login(client, "estimate_mgr_rule_ctx", "pwd123")

    task_id = "task_estimate_rule_ctx"
    _seed_task(task_id, manager["id"])
    with task_routes._task_storage_context() as data:
        data[task_id]["requirement_content"] = "完整需求上下文：重构6021手续费收入模型，修正总分不平，来源系统改为动态，渠道业务与贷款手续费按差异化逻辑处理。"

    captured_context = {}

    def _capture_estimate(feature, **kwargs):
        captured_context[feature["id"]] = kwargs
        return {
            "optimistic": 1.0,
            "most_likely": 2.0,
            "pessimistic": 3.0,
            "expected": 2.0,
            "reasoning": "结合完整语义与规则上下文估算",
            "original_estimate": 2.0,
        }

    monkeypatch.setattr(
        work_estimation_agent,
        "estimate_three_point_for_feature",
        _capture_estimate,
        raising=False,
    )

    response = client.post(
        f"/api/v1/tasks/{task_id}/estimate",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload.get("degraded") is False
    feature = (payload.get("features") or [])[0]
    rule_context = feature.get("rule_context")
    assert isinstance(rule_context, dict)
    assert rule_context.get("rule_id") == "cosmic"
    assert rule_context.get("status") == "applied"
    assert isinstance(rule_context.get("summary_text"), str)
    assert isinstance(rule_context.get("structured_payload"), dict)
    assert captured_context["feat_1"].get("requirement_context") == (
        "完整需求上下文：重构6021手续费收入模型，修正总分不平，来源系统改为动态，渠道业务与贷款手续费按差异化逻辑处理。"
    )
    assert captured_context["feat_1"].get("rule_context", {}).get("rule_id") == "cosmic"


def test_task_estimate_runs_cosmic_analysis_at_estimate_time(client, monkeypatch):
    manager = _seed_user("estimate_mgr_runtime_cosmic", "pwd123", ["manager"])
    token = _login(client, "estimate_mgr_runtime_cosmic", "pwd123")

    task_id = "task_estimate_runtime_cosmic"
    _seed_task(task_id, manager["id"])
    with task_routes._task_storage_context() as data:
        data[task_id]["systems_data"]["HOP"][0].pop("cosmic_analysis", None)

    analyze_calls = []

    def _fake_analyze(description, feature_info=None):
        analyze_calls.append({
            "description": description,
            "feature_id": (feature_info or {}).get("id"),
        })
        return {
            "data_movements": {
                "E": [{"data_group": "开户请求", "description": "录入开户信息"}],
                "X": [{"data_group": "开户结果", "description": "返回开户结果"}],
                "R": [],
                "W": [{"data_group": "账户台账", "description": "写入新账户"}],
            },
            "cff": 3,
            "counting_basis": "点击估算时基于当前 COSMIC 配置重新分析。",
        }

    monkeypatch.setattr(task_routes.cosmic_analyzer, "analyze_feature", _fake_analyze, raising=False)
    monkeypatch.setattr(
        work_estimation_agent,
        "estimate_three_point_for_feature",
        lambda *args, **kwargs: {
            "optimistic": 1.0,
            "most_likely": 2.0,
            "pessimistic": 3.0,
            "expected": 2.0,
            "reasoning": "结合运行时 COSMIC 分析估算",
            "original_estimate": 2.0,
        },
        raising=False,
    )

    response = client.post(
        f"/api/v1/tasks/{task_id}/estimate",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert analyze_calls == [{"description": "开户", "feature_id": "feat_1"}]
    payload = response.json()
    feature = (payload.get("features") or [])[0]
    assert feature.get("rule_context", {}).get("status") == "applied"

    with task_routes._task_storage_context() as data:
        stored_feature = data[task_id]["systems_data"]["HOP"][0]
    assert stored_feature.get("cosmic_analysis", {}).get("cff") == 3
    assert stored_feature.get("rule_context", {}).get("structured_payload", {}).get("cff") == 3


def test_task_estimate_reuses_existing_cosmic_analysis_without_rerun(client, monkeypatch):
    manager = _seed_user("estimate_mgr_reuse_cosmic", "pwd123", ["manager"])
    token = _login(client, "estimate_mgr_reuse_cosmic", "pwd123")

    task_id = "task_estimate_reuse_cosmic"
    _seed_task(task_id, manager["id"])

    analyze_calls = []

    def _fake_analyze(*args, **kwargs):
        analyze_calls.append({"args": args, "kwargs": kwargs})
        return {
            "data_movements": {"E": [], "X": [], "R": [], "W": []},
            "cff": 0,
            "counting_basis": "不应走到这里",
        }

    monkeypatch.setattr(task_routes.cosmic_analyzer, "analyze_feature", _fake_analyze, raising=False)
    monkeypatch.setattr(
        work_estimation_agent,
        "estimate_three_point_for_feature",
        lambda *args, **kwargs: {
            "optimistic": 1.0,
            "most_likely": 2.0,
            "pessimistic": 3.0,
            "expected": 2.0,
            "reasoning": "复用既有 COSMIC 分析结果估算",
            "original_estimate": 2.0,
        },
        raising=False,
    )

    response = client.post(
        f"/api/v1/tasks/{task_id}/estimate",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert analyze_calls == []
    payload = response.json()
    feature = (payload.get("features") or [])[0]
    assert feature.get("rule_context", {}).get("structured_payload", {}).get("cff") == 4


def test_task_estimate_marks_rule_context_skipped_when_rule_not_selected(client, monkeypatch):
    manager = _seed_user("estimate_mgr_rule_skipped", "pwd123", ["manager"])
    token = _login(client, "estimate_mgr_rule_skipped", "pwd123")

    task_id = "task_estimate_rule_skipped"
    _seed_task(task_id, manager["id"])
    with task_routes._task_storage_context() as data:
        data[task_id]["estimation_rule"] = "none"

    captured_context = {}

    def _capture_estimate(feature, **kwargs):
        captured_context[feature["id"]] = kwargs
        return {
            "optimistic": 1.0,
            "most_likely": 2.0,
            "pessimistic": 3.0,
            "expected": 2.0,
            "reasoning": "未选择规则时跳过 COSMIC 上下文",
            "original_estimate": 2.0,
        }

    monkeypatch.setattr(
        work_estimation_agent,
        "estimate_three_point_for_feature",
        _capture_estimate,
        raising=False,
    )

    response = client.post(
        f"/api/v1/tasks/{task_id}/estimate",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    feature = (payload.get("features") or [])[0]
    assert feature.get("rule_context", {}).get("status") == "skipped"
    assert feature.get("rule_context", {}).get("failure_reason") == "rule_not_selected"
    assert captured_context["feat_1"].get("rule_context", {}).get("status") == "skipped"


def test_task_estimate_records_feature_level_rule_context_degradation(client, monkeypatch):
    manager = _seed_user("estimate_mgr_rule_degraded", "pwd123", ["manager"])
    token = _login(client, "estimate_mgr_rule_degraded", "pwd123")

    task_id = "task_estimate_rule_degraded"
    _seed_task(task_id, manager["id"])

    monkeypatch.setattr(settings, "ENABLE_V27_PROFILE_SCHEMA", True)
    profile_service = system_profile_service.get_system_profile_service()
    profile_service.ensure_profile("HOP", system_id="sys_hop", actor={"id": manager["id"]})

    monkeypatch.setattr(
        task_routes,
        "build_feature_rule_context",
        lambda *args, **kwargs: {
            "rule_id": "cosmic",
            "rule_name": "COSMIC",
            "status": "degraded",
            "summary_text": "COSMIC 规则降级",
            "structured_payload": {},
            "failure_reason": "cosmic analyzer unavailable",
        },
        raising=False,
    )
    monkeypatch.setattr(
        work_estimation_agent,
        "estimate_three_point_for_feature",
        lambda *args, **kwargs: {
            "optimistic": 1.0,
            "most_likely": 2.0,
            "pessimistic": 3.0,
            "expected": 2.0,
            "reasoning": "规则降级后按完整上下文估算",
            "original_estimate": 2.0,
        },
        raising=False,
    )

    response = client.post(
        f"/api/v1/tasks/{task_id}/estimate",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    feature = (payload.get("features") or [])[0]
    assert feature.get("rule_context", {}).get("status") == "degraded"
    assert feature.get("rule_context", {}).get("failure_reason") == "cosmic analyzer unavailable"

    artifact_service = profile_artifact_service.get_profile_artifact_service()
    output_items = artifact_service.list_layer_records(layer="output", system_id="sys_hop")
    estimation_items = [
        item
        for item in output_items
        if isinstance(item.get("payload"), dict) and item["payload"].get("output_type") == "estimation_context"
    ]
    assert len(estimation_items) == 1
    estimation_payload = estimation_items[0]["payload"]
    assert estimation_payload["features"][0]["rule_context"]["status"] == "degraded"
    assert estimation_payload["features"][0]["rule_context"]["failure_reason"] == "cosmic analyzer unavailable"
