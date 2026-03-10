import copy
import json
import sys
from contextlib import contextmanager
from types import ModuleType, SimpleNamespace

import pytest

from backend.config.config import settings
from backend.api import system_routes
from backend.service import profile_summary_service
from backend.service.system_profile_service import SystemProfileService
from backend.utils.token_counter import ChunkPlanItem


class _DummyExecutor:
    def __init__(self):
        self.submissions = []

    def submit(self, fn, **kwargs):
        self.submissions.append({"fn": fn, "kwargs": kwargs})

        class _DummyFuture:
            def result(self, timeout=None):
                return None

        return _DummyFuture()


@pytest.fixture()
def profile_services(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "REPORT_DIR", str(data_dir))

    profile_store = data_dir / "system_profiles.json"
    service = SystemProfileService(store_path=str(profile_store))

    monkeypatch.setattr(profile_summary_service, "get_system_profile_service", lambda: service)

    return {
        "data_dir": data_dir,
        "profile_store": profile_store,
        "service": service,
    }


def _seed_profile(service: SystemProfileService, *, system_name: str, system_id: str):
    service.upsert_profile(
        system_name,
        {
            "system_id": system_id,
            "fields": {
                "system_scope": f"{system_name} old scope",
                "module_structure": [{"module_name": "账户", "functions": [{"name": "开户"}]}],
                "integration_points": "old integration",
                "key_constraints": "old constraints",
            },
            "evidence_refs": [],
        },
        actor={"id": "owner_1", "username": "owner_1", "displayName": "Owner"},
    )


def _full_domain_suggestions():
    return {
        "system_positioning": {
            "system_description": "old system description",
            "target_users": ["运营"],
            "boundaries": [{"item": "old boundary"}],
        },
        "business_capabilities": {
            "module_structure": [{"module_name": "账户", "functions": [{"name": "开户"}]}],
            "core_processes": [{"name": "开户", "description": "old process"}],
        },
        "integration_interfaces": {
            "integration_points": [{"description": "old integration point"}],
            "external_dependencies": [{"name": "old dependency"}],
        },
        "technical_architecture": {
            "architecture_positioning": "old architecture",
            "tech_stack": ["FastAPI"],
            "performance_profile": {"qps": "100"},
        },
        "constraints_risks": {
            "key_constraints": [{"category": "合规", "description": "old constraint"}],
            "known_risks": [{"description": "old risk", "impact_level": "medium"}],
        },
    }


def test_trigger_summary_same_system_inflight_creates_new_pending_task(profile_services):
    service = profile_services["service"]
    _seed_profile(service, system_name="HOP", system_id="sys_hop")

    summary_service = profile_summary_service.ProfileSummaryService()
    summary_service.executor = _DummyExecutor()

    first = summary_service.trigger_summary(
        system_id="sys_hop",
        system_name="HOP",
        actor={"id": "owner_1", "username": "owner_1"},
        reason="document_import",
        source_file="v1.docx",
        trigger="document_import",
    )
    second = summary_service.trigger_summary(
        system_id="sys_hop",
        system_name="HOP",
        actor={"id": "owner_1", "username": "owner_1"},
        reason="document_import",
        source_file="v2.docx",
        trigger="document_import",
    )

    assert first.get("created_new") is True
    assert second.get("created_new") is True
    assert second.get("job_id") != first.get("job_id")

    latest_task = service.get_extraction_task("sys_hop")
    assert latest_task is not None
    assert latest_task.get("task_id") == second.get("job_id")
    assert latest_task.get("status") == "pending"


def test_set_ai_suggestions_updates_only_relevant_domain_and_keeps_previous(profile_services):
    service = profile_services["service"]
    profile_store = profile_services["profile_store"]
    _seed_profile(service, system_name="HOP", system_id="sys_hop")

    with open(profile_store, "r", encoding="utf-8") as f:
        rows = json.load(f)
    rows[0]["ai_suggestions"] = _full_domain_suggestions()
    rows[0]["profile_events"] = []
    with open(profile_store, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    old_suggestions = copy.deepcopy(rows[0]["ai_suggestions"])
    new_integration = {
        "integration_interfaces": {
            "integration_points": [{"description": "new integration point"}],
            "external_dependencies": [{"name": "redis", "type": "middleware", "purpose": "cache"}],
        }
    }

    updated = service.set_ai_suggestions(
        "HOP",
        suggestions=new_integration,
        relevant_domains=["integration_interfaces"],
        trigger="document_import",
        source="v2.docx",
    )

    assert updated.get("ai_suggestions_previous") == old_suggestions
    assert (
        updated.get("ai_suggestions", {})
        .get("system_positioning", {})
        .get("system_description")
        == old_suggestions["system_positioning"]["system_description"]
    )
    assert (
        updated.get("ai_suggestions", {})
        .get("integration_interfaces", {})
        .get("integration_points")
    ) == [{"description": "new integration point"}]

    events = updated.get("profile_events") or []
    assert events
    last_event = events[-1]
    assert last_event.get("event_type") == "document_import"
    assert last_event.get("affected_domains") == ["integration_interfaces"]


def test_build_context_collects_esb_entries_by_system_alias(profile_services, monkeypatch):
    class _DummyEsbService:
        @contextmanager
        def _lock(self):
            yield

        def _load_unlocked(self):
            return {
                "entries": [
                    {
                        "provider_system_id": "ULCA",
                        "provider_system_name": "贷款核算",
                        "consumer_system_id": "CLMP",
                        "consumer_system_name": "融资中台",
                        "service_name": "一般贷款开户",
                        "scenario_code": "3022000701",
                        "status": "正常使用",
                    }
                ]
            }

    monkeypatch.setattr(profile_summary_service, "get_esb_service", lambda: _DummyEsbService())
    monkeypatch.setattr(
        system_routes,
        "resolve_system_owner",
        lambda **_: {
            "system_found": True,
            "system_id": "6d8a1fc0d67e4b7785f1a9a2670d08c6",
            "system_name": "贷款核算",
            "system_abbreviation": "ULCA",
        },
    )

    summary_service = profile_summary_service.ProfileSummaryService()
    context = summary_service._build_context(
        system_id="6d8a1fc0d67e4b7785f1a9a2670d08c6",
        system_name="贷款核算",
    )

    assert "【ESB】" in context
    assert "entries_total=1" in context
    assert "一般贷款开户" in context


def test_build_context_samples_chunks_across_latest_source(profile_services):
    data_dir = profile_services["data_dir"]
    store_path = data_dir / "knowledge_store.json"

    rows = []
    for idx in range(20):
        rows.append(
            {
                "system_name": "贷款核算",
                "knowledge_type": "document",
                "content": f"chunk-{idx}",
                "created_at": f"2026-03-05T09:40:{idx:02d}.000000",
                "source_file": "v1.docx",
                "metadata": {
                    "chunk_index": idx,
                    "source_filename": "v1.docx",
                },
            }
        )

    with open(store_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    summary_service = profile_summary_service.ProfileSummaryService()
    context = summary_service._build_context(system_id="sys_hop", system_name="贷款核算")

    assert "【文档/代码材料片段】" in context
    assert "chunks_total=20" in context
    assert "chunk-0" in context
    assert "chunk-10" in context
    assert "chunk-19" in context


def test_call_llm_merges_domain_hints_from_context(monkeypatch):
    call_counter = {"count": 0}
    stage2_prompts = []

    def _fake_chat_raw(messages, temperature, max_tokens, retry_times):
        _ = retry_times
        _ = temperature
        _ = max_tokens
        call_counter["count"] += 1
        user_prompt = messages[1]["content"]
        if call_counter["count"] == 1:
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content=json.dumps(
                                {
                                    "relevant_domains": ["system_positioning", "business_capabilities", "integration_interfaces"],
                                    "related_systems": [],
                                },
                                ensure_ascii=False,
                            )
                        )
                    )
                ],
                usage=None,
            )

        stage2_prompts.append(user_prompt)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=json.dumps(
                            {
                                "suggestions": {
                                    "technical_architecture": {
                                        "architecture_positioning": "微服务架构",
                                        "tech_stack": ["Java", "Redis"],
                                        "performance_profile": {"峰值TPS": "70"},
                                    }
                                }
                            },
                            ensure_ascii=False,
                        )
                    )
                )
            ],
            usage=None,
        )

    monkeypatch.setattr(
        profile_summary_service.llm_client,
        "_chat_raw",
        _fake_chat_raw,
    )
    monkeypatch.setattr(profile_summary_service.llm_client, "extract_json", lambda value: json.loads(value))

    summary_service = profile_summary_service.ProfileSummaryService()
    context = "系统采用微服务架构，技术栈包含 Java、Redis，应用部署要求高可用。"
    result = summary_service._call_llm(system_id="sys_hop", system_name="贷款核算", context=context)

    assert stage2_prompts
    assert "technical_architecture" in stage2_prompts[0]
    assert "technical_architecture" in result.get("relevant_domains", [])
    assert (
        result.get("suggestions", {})
        .get("technical_architecture", {})
        .get("tech_stack")
    ) == ["Java", "Redis"]


def test_single_call_path(monkeypatch):
    summary_service = profile_summary_service.ProfileSummaryService()
    bundle = profile_summary_service.SummaryContextBundle(
        static_prefix_text="STATIC",
        chunkable_body_text="BODY",
    )
    stage1_calls = []
    stage2_calls = []

    monkeypatch.setattr(profile_summary_service, "estimate_tokens", lambda text: len(str(text or "")))
    monkeypatch.setattr(
        summary_service,
        "_calculate_body_budget",
        lambda **kwargs: 100,
    )
    monkeypatch.setattr(
        profile_summary_service,
        "chunk_text",
        lambda *args, **kwargs: pytest.fail("single call path should not chunk"),
    )
    monkeypatch.setattr(
        summary_service,
        "_execute_stage1",
        lambda **kwargs: stage1_calls.append(kwargs) or {
            "relevant_domains": ["technical_architecture"],
            "related_systems": [],
        },
    )
    monkeypatch.setattr(
        summary_service,
        "_execute_stage2",
        lambda **kwargs: stage2_calls.append(kwargs) or {
            "technical_architecture": {
                "tech_stack": ["Java", "Redis"],
            }
        },
    )

    result = summary_service._call_llm(
        system_id="sys_hop",
        system_name="贷款核算",
        context_bundle=bundle,
    )

    assert len(stage1_calls) == 1
    assert len(stage2_calls) == 1
    assert stage1_calls[0]["chunk_index"] is None
    assert "STATIC" in stage1_calls[0]["context_text"]
    assert "BODY" in stage1_calls[0]["context_text"]
    assert result["relevant_domains"] == ["technical_architecture"]
    assert result["suggestions"]["technical_architecture"]["tech_stack"] == ["Java", "Redis"]


def test_chunking_path(monkeypatch):
    summary_service = profile_summary_service.ProfileSummaryService()
    bundle = profile_summary_service.SummaryContextBundle(
        static_prefix_text="STATIC",
        chunkable_body_text="BODY-NEEDS-CHUNKING",
    )
    stage1_calls = []
    stage2_calls = []
    chunk_calls = []

    monkeypatch.setattr(profile_summary_service, "estimate_tokens", lambda text: len(str(text or "")))
    monkeypatch.setattr(
        summary_service,
        "_calculate_body_budget",
        lambda **kwargs: 8,
    )
    monkeypatch.setattr(
        profile_summary_service,
        "chunk_text",
        lambda text, max_tokens, overlap_paragraphs: chunk_calls.append(
            {
                "text": text,
                "max_tokens": max_tokens,
                "overlap_paragraphs": overlap_paragraphs,
            }
        )
        or [
            ChunkPlanItem(0, "body-1", 6, 0, 0),
            ChunkPlanItem(1, "body-2", 6, 1, 1),
        ],
    )

    def _fake_stage1(**kwargs):
        stage1_calls.append(kwargs)
        if kwargs["chunk_index"] == 0:
            return {
                "relevant_domains": ["system_positioning", "business_capabilities"],
                "related_systems": ["ECIF"],
            }
        return {
            "relevant_domains": ["business_capabilities", "technical_architecture"],
            "related_systems": ["ECIF", "MOB"],
        }

    def _fake_stage2(**kwargs):
        stage2_calls.append(kwargs)
        if kwargs["chunk_index"] == 0:
            return {
                "system_positioning": {"system_description": "范围A"},
                "business_capabilities": {
                    "module_structure": [{"module_name": "M1", "functions": [{"name": "开户", "desc": "开户登记"}]}]
                },
            }
        return {
            "system_positioning": {"system_description": "范围B"},
            "business_capabilities": {
                "module_structure": [
                    {"module_name": "M1", "functions": [{"name": "放款", "desc": "放款处理"}]},
                    {"module_name": "M2", "functions": [{"name": "核算", "desc": "核算处理"}]},
                ]
            },
            "technical_architecture": {"tech_stack": ["Java"]},
        }

    monkeypatch.setattr(summary_service, "_execute_stage1", _fake_stage1)
    monkeypatch.setattr(summary_service, "_execute_stage2", _fake_stage2)

    result = summary_service._call_llm(
        system_id="sys_hop",
        system_name="贷款核算",
        context_bundle=bundle,
    )

    assert chunk_calls == [
        {
            "text": "BODY-NEEDS-CHUNKING",
            "max_tokens": 8,
            "overlap_paragraphs": settings.LLM_CHUNK_OVERLAP_PARAGRAPHS,
        }
    ]
    assert len(stage1_calls) == 2
    assert len(stage2_calls) == 2
    assert result["relevant_domains"] == [
        "system_positioning",
        "business_capabilities",
        "technical_architecture",
    ]
    assert result["related_systems"] == ["ECIF", "MOB"]
    assert result["suggestions"]["system_positioning"]["system_description"] == "范围A; 范围B"
    assert result["suggestions"]["business_capabilities"]["module_structure"] == [
        {
            "module_name": "M1",
            "functions": [
                {"name": "开户", "desc": "开户登记"},
                {"name": "放款", "desc": "放款处理"},
            ],
        },
        {
            "module_name": "M2",
            "functions": [{"name": "核算", "desc": "核算处理"}],
        },
    ]


def test_chunking_disabled(monkeypatch):
    summary_service = profile_summary_service.ProfileSummaryService()
    bundle = profile_summary_service.SummaryContextBundle(
        static_prefix_text="STATIC",
        chunkable_body_text="BODY-NEEDS-CHUNKING",
    )

    monkeypatch.setattr(profile_summary_service, "estimate_tokens", lambda text: len(str(text or "")))
    monkeypatch.setattr(summary_service, "_calculate_body_budget", lambda **kwargs: 8)
    monkeypatch.setattr(settings, "ENABLE_LLM_CHUNKING", False)

    with pytest.raises(ValueError, match="CHUNKING_DISABLED_OVERSIZE"):
        summary_service._call_llm(
            system_id="sys_hop",
            system_name="贷款核算",
            context_bundle=bundle,
        )


def test_chunking_disabled_still_allows_normal_document(monkeypatch):
    summary_service = profile_summary_service.ProfileSummaryService()
    bundle = profile_summary_service.SummaryContextBundle(
        static_prefix_text="STATIC",
        chunkable_body_text="BODY-NORMAL",
    )
    stage1_calls = []
    stage2_calls = []

    monkeypatch.setattr(profile_summary_service, "estimate_tokens", lambda text: 20000 if text == "BODY-NORMAL" else len(str(text or "")))
    monkeypatch.setattr(summary_service, "_calculate_body_budget", lambda **kwargs: 25000)
    monkeypatch.setattr(settings, "ENABLE_LLM_CHUNKING", False)
    monkeypatch.setattr(
        summary_service,
        "_execute_stage1",
        lambda **kwargs: stage1_calls.append(kwargs) or {
            "relevant_domains": ["technical_architecture"],
            "related_systems": [],
        },
    )
    monkeypatch.setattr(
        summary_service,
        "_execute_stage2",
        lambda **kwargs: stage2_calls.append(kwargs) or {
            "technical_architecture": {"tech_stack": ["Redis"]},
        },
    )

    result = summary_service._call_llm(
        system_id="sys_hop",
        system_name="贷款核算",
        context_bundle=bundle,
    )

    assert len(stage1_calls) == 1
    assert len(stage2_calls) == 1
    assert result["suggestions"]["technical_architecture"]["tech_stack"] == ["Redis"]


def test_chunking_path_fails_when_any_chunk_processing_fails(monkeypatch):
    summary_service = profile_summary_service.ProfileSummaryService()
    bundle = profile_summary_service.SummaryContextBundle(
        static_prefix_text="STATIC",
        chunkable_body_text="BODY-NEEDS-CHUNKING",
    )

    monkeypatch.setattr(profile_summary_service, "estimate_tokens", lambda text: len(str(text or "")))
    monkeypatch.setattr(summary_service, "_calculate_body_budget", lambda **kwargs: 8)
    monkeypatch.setattr(
        profile_summary_service,
        "chunk_text",
        lambda *args, **kwargs: [
            ChunkPlanItem(0, "body-1", 6, 0, 0),
            ChunkPlanItem(1, "body-2", 6, 1, 1),
        ],
    )
    monkeypatch.setattr(
        summary_service,
        "_execute_stage1",
        lambda **kwargs: {
            "relevant_domains": ["technical_architecture"],
            "related_systems": [],
        },
    )

    def _failing_stage2(**kwargs):
        if kwargs["chunk_index"] == 1:
            raise RuntimeError("CHUNK_PROCESSING_FAILED")
        return {"technical_architecture": {"tech_stack": ["Java"]}}

    monkeypatch.setattr(summary_service, "_execute_stage2", _failing_stage2)

    with pytest.raises(RuntimeError, match="CHUNK_PROCESSING_FAILED"):
        summary_service._call_llm(
            system_id="sys_hop",
            system_name="贷款核算",
            context_bundle=bundle,
        )


@pytest.mark.parametrize(
    ("body_tokens", "expect_chunking"),
    [
        (20000, False),
        (25000, False),
        (30000, True),
        (50000, True),
    ],
    ids=["20k-single", "25k-single", "30k-chunk", "50k-chunk"],
)
def test_call_llm_switches_by_token_budget(monkeypatch, body_tokens, expect_chunking):
    summary_service = profile_summary_service.ProfileSummaryService()
    bundle = profile_summary_service.SummaryContextBundle(
        static_prefix_text="STATIC",
        chunkable_body_text=f"BODY-{body_tokens}",
    )
    stage1_calls = []
    stage2_calls = []
    chunk_calls = []

    def _fake_estimate_tokens(text):
        if text == bundle.chunkable_body_text:
            return body_tokens
        return len(str(text or ""))

    monkeypatch.setattr(profile_summary_service, "estimate_tokens", _fake_estimate_tokens)
    monkeypatch.setattr(summary_service, "_calculate_body_budget", lambda **kwargs: 25000)
    monkeypatch.setattr(
        summary_service,
        "_execute_stage1",
        lambda **kwargs: stage1_calls.append(kwargs) or {
            "relevant_domains": ["technical_architecture"],
            "related_systems": [],
        },
    )
    monkeypatch.setattr(
        summary_service,
        "_execute_stage2",
        lambda **kwargs: stage2_calls.append(kwargs) or {
            "technical_architecture": {"tech_stack": ["Redis"]},
        },
    )

    if expect_chunking:
        monkeypatch.setattr(
            profile_summary_service,
            "chunk_text",
            lambda *args, **kwargs: chunk_calls.append(kwargs) or [
                ChunkPlanItem(0, "body-1", 20000, 0, 0),
                ChunkPlanItem(1, "body-2", body_tokens - 20000, 1, 1),
            ],
        )
    else:
        monkeypatch.setattr(
            profile_summary_service,
            "chunk_text",
            lambda *args, **kwargs: pytest.fail("single-call sample should not chunk"),
        )

    result = summary_service._call_llm(
        system_id="sys_hop",
        system_name="贷款核算",
        context_bundle=bundle,
    )

    assert result["suggestions"]["technical_architecture"]["tech_stack"] == ["Redis"]
    if expect_chunking:
        assert len(stage1_calls) == 2
        assert len(stage2_calls) == 2
        assert chunk_calls
    else:
        assert len(stage1_calls) == 1
        assert len(stage2_calls) == 1


def test_trigger_summary_validates_inputs_and_preserves_context_override(profile_services):
    service = profile_services["service"]
    _seed_profile(service, system_name="HOP", system_id="sys_hop")

    summary_service = profile_summary_service.ProfileSummaryService()
    summary_service.executor = _DummyExecutor()

    with pytest.raises(ValueError, match="system_id/system_name不能为空"):
        summary_service.trigger_summary(system_id="", system_name="HOP")

    job = summary_service.trigger_summary(
        system_id="sys_hop",
        system_name="HOP",
        context_override={"document_text": "完整原文"},
    )

    assert job["status"] == "pending"
    assert summary_service.executor.submissions[0]["kwargs"]["context_override"] == {"document_text": "完整原文"}
    assert service.get_extraction_task("sys_hop")["task_id"] == job["job_id"]


def test_run_job_success_updates_status_and_sends_ready_notification(profile_services, monkeypatch):
    service = profile_services["service"]
    _seed_profile(service, system_name="HOP", system_id="sys_hop")
    service.upsert_extraction_task("sys_hop", task_id="job-1", status="pending", trigger="document_import")

    summary_service = profile_summary_service.ProfileSummaryService()
    notifications = []

    monkeypatch.setattr(
        system_routes,
        "resolve_system_owner",
        lambda **_: {"resolved_owner_id": "owner_1"},
    )
    monkeypatch.setattr(
        summary_service,
        "_build_context_bundle",
        lambda **kwargs: profile_summary_service.SummaryContextBundle(
            static_prefix_text="STATIC",
            chunkable_body_text="BODY",
        ),
    )
    monkeypatch.setattr(
        summary_service,
        "_call_llm",
        lambda **kwargs: {
            "suggestions": {"technical_architecture": {"tech_stack": ["Redis"]}},
            "relevant_domains": ["technical_architecture"],
            "related_systems": ["ECIF"],
        },
    )
    monkeypatch.setattr(
        summary_service,
        "_notify",
        lambda **kwargs: notifications.append(kwargs),
    )

    summary_service._run_job(
        system_id="sys_hop",
        system_name="HOP",
        job_id="job-1",
        reason="document_import",
        trigger="document_import",
        source_file="requirements.docx",
        actor={"id": "owner_1"},
        context_override={"document_text": "完整原文"},
    )

    task = service.get_extraction_task("sys_hop")
    profile = service.get_profile("HOP")

    assert task["status"] == "completed"
    assert task["notifications"][0]["systems"] == ["ECIF"]
    assert profile["ai_suggestions"]["technical_architecture"]["tech_stack"] == ["Redis"]
    assert notifications == [
        {
            "user_id": "owner_1",
            "notify_type": "system_profile_summary_ready",
            "system_id": "sys_hop",
            "system_name": "HOP",
            "payload": {"job_id": "job-1", "reason": "document_import"},
        }
    ]


def test_run_job_failure_updates_status_and_sends_failed_notification(profile_services, monkeypatch):
    service = profile_services["service"]
    _seed_profile(service, system_name="HOP", system_id="sys_hop")
    service.upsert_extraction_task("sys_hop", task_id="job-2", status="pending", trigger="document_import")

    summary_service = profile_summary_service.ProfileSummaryService()
    notifications = []

    monkeypatch.setattr(
        system_routes,
        "resolve_system_owner",
        lambda **_: {"resolved_owner_id": "owner_1"},
    )
    monkeypatch.setattr(
        summary_service,
        "_build_context_bundle",
        lambda **kwargs: profile_summary_service.SummaryContextBundle(
            static_prefix_text="STATIC",
            chunkable_body_text="BODY",
        ),
    )
    monkeypatch.setattr(summary_service, "_call_llm", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr(
        summary_service,
        "_notify",
        lambda **kwargs: notifications.append(kwargs),
    )

    summary_service._run_job(
        system_id="sys_hop",
        system_name="HOP",
        job_id="job-2",
        reason="manual_retry",
        trigger="manual_retry",
        source_file="",
        actor={"id": "owner_1"},
        context_override={},
    )

    task = service.get_extraction_task("sys_hop")
    assert task["status"] == "failed"
    assert task["error"] == "boom"
    assert notifications == [
        {
            "user_id": "owner_1",
            "notify_type": "system_profile_summary_failed",
            "system_id": "sys_hop",
            "system_name": "HOP",
            "payload": {
                "job_id": "job-2",
                "error_code": "SUMMARY_001",
                "error_reason": "boom",
                "reason": "manual_retry",
            },
        }
    ]


def test_notify_builds_payload_and_handles_missing_owner_or_notification_failure(monkeypatch):
    summary_service = profile_summary_service.ProfileSummaryService()
    captured = []

    fake_module = ModuleType("backend.api.notification_routes")
    fake_module.create_notification = lambda **kwargs: captured.append(kwargs)
    monkeypatch.setitem(sys.modules, "backend.api.notification_routes", fake_module)

    summary_service._notify(
        user_id="",
        notify_type="system_profile_summary_ready",
        system_id="sys_hop",
        system_name="HOP",
    )
    assert captured == []

    summary_service._notify(
        user_id="owner_1",
        notify_type="system_profile_summary_ready",
        system_id="sys_hop",
        system_name="HOP",
        payload={"job_id": "job-1"},
    )

    assert captured[0]["title"] == "画像AI总结完成"
    assert captured[0]["user_ids"] == ["owner_1"]
    assert captured[0]["payload"]["link"] == "/system-profiles/board?system_id=sys_hop&system_name=HOP"
    assert captured[0]["payload"]["job_id"] == "job-1"

    fake_module.create_notification = lambda **kwargs: (_ for _ in ()).throw(RuntimeError("notify failed"))
    summary_service._notify(
        user_id="owner_1",
        notify_type="system_profile_summary_failed",
        system_id="sys_hop",
        system_name="HOP",
    )


def test_context_helpers_and_notifications_normalize_values(monkeypatch):
    summary_service = profile_summary_service.ProfileSummaryService()

    monkeypatch.setattr(summary_service, "_build_static_context", lambda **kwargs: "")
    monkeypatch.setattr(summary_service, "_build_knowledge_context", lambda **kwargs: "")

    empty_bundle = summary_service._build_context_bundle(system_id="sys_hop", system_name="HOP")
    doc_bundle = summary_service._build_context_bundle(
        system_id="sys_hop",
        system_name="HOP",
        context_override={"document_text": "完整原文"},
    )

    monkeypatch.setattr(settings, "PROFILE_SUMMARY_CONTEXT_MAX_CHARS", 10)
    monkeypatch.setattr(settings, "PROFILE_SUMMARY_SAMPLE_MAX_ITEMS", 2)
    monkeypatch.setattr(settings, "PROFILE_SUMMARY_SAMPLE_ITEM_MAX_CHARS", 10)

    assert empty_bundle.static_prefix_text == "系统：HOP（sys_hop）。材料不足。"
    assert empty_bundle.chunkable_body_text == ""
    assert doc_bundle.static_prefix_text == "系统：HOP（sys_hop）。"
    assert doc_bundle.chunkable_body_text == "完整原文"
    assert summary_service._context_max_chars() == 12000
    assert summary_service._sample_max_items() == 12
    assert summary_service._sample_item_max_chars() == 300
    assert summary_service._extract_chunk_index({"metadata": {"chunk_index": "3"}}) == 3
    assert summary_service._extract_chunk_index({"metadata": {"chunk_index": "bad"}}) is None
    assert summary_service._normalize_relevant_domains("system_positioning, technical_architecture, bad") == [
        "system_positioning",
        "technical_architecture",
    ]
    assert summary_service._normalize_relevant_domains(["technical_architecture", "technical_architecture", "bad"]) == [
        "technical_architecture"
    ]
    assert summary_service._normalize_related_systems("HOP,ECIF,ECIF", current_system_name="hop") == ["ECIF"]
    assert summary_service._normalize_related_systems(["MOB", "HOP", "MOB"], current_system_name="hop") == ["MOB"]
    assert summary_service._build_multi_system_notifications(system_name="HOP", related_systems=[]) == []
    assert summary_service._build_multi_system_notifications(system_name="HOP", related_systems=["HOP", "ECIF"]) == [
        {
            "type": "multi_system_detected",
            "systems": ["ECIF"],
            "message": "检测到文档中还包含系统 ECIF 的信息，如需更新请前往对应系统操作",
        }
    ]


def test_select_knowledge_samples_without_indexes_uses_head_tail_fallback():
    summary_service = profile_summary_service.ProfileSummaryService()
    related = [
        {
            "id": f"item-{idx}",
            "created_at": f"2026-03-05T09:40:0{idx}",
            "source_file": "latest.docx",
            "metadata": {"source_filename": "latest.docx"},
        }
        for idx in range(6)
    ]
    related.insert(2, copy.deepcopy(related[1]))

    selected = summary_service._select_knowledge_samples(related, max_items=4)

    assert len(selected) == 4
    assert {item["id"] for item in selected} == {"item-0", "item-1", "item-4", "item-5"}


def test_build_static_context_includes_latest_code_scan_result(profile_services, monkeypatch):
    data_dir = profile_services["data_dir"]
    result_path = data_dir / "scan_result.json"
    result_path.write_text(
        json.dumps(
            {
                "items": [
                    {"entry_type": "controller", "entry_id": "loan.open", "summary": "开户入口"},
                    {"entry_type": "service", "entry_id": "loan.repay", "summary": "还款服务"},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    class _DummyCodeScanService:
        def list_jobs(self):
            return [
                {"system_id": "other", "status": "completed", "result_path": "missing.json"},
                {"system_id": "sys_hop", "status": "completed", "result_path": str(result_path)},
            ]

    class _DummyEsbService:
        @contextmanager
        def _lock(self):
            yield

        def _load_unlocked(self):
            return {"entries": []}

    monkeypatch.setattr(profile_summary_service, "get_code_scan_service", lambda: _DummyCodeScanService())
    monkeypatch.setattr(profile_summary_service, "get_esb_service", lambda: _DummyEsbService())
    monkeypatch.setattr(
        system_routes,
        "resolve_system_owner",
        lambda **kwargs: {"system_abbreviation": "HOP"},
    )

    summary_service = profile_summary_service.ProfileSummaryService()
    context = summary_service._build_static_context(system_id="sys_hop", system_name="HOP")

    assert "【代码扫描】" in context
    assert "items_total=2" in context
    assert "loan.open" in context
    assert "【ESB】" in context
    assert "entries_total=0" in context


def test_calculate_body_budget_and_execute_stage_calls(monkeypatch):
    summary_service = profile_summary_service.ProfileSummaryService()
    metrics = []

    monkeypatch.setattr(settings, "LLM_INPUT_MAX_TOKENS", 25000)
    monkeypatch.setattr(settings, "LLM_MAX_CONTEXT_TOKENS", 32000)
    monkeypatch.setattr(profile_summary_service, "estimate_tokens", lambda text: len(str(text or "")))
    monkeypatch.setattr(summary_service, "_log_chunk_metric", lambda **kwargs: metrics.append(kwargs))
    monkeypatch.setattr(profile_summary_service.time, "perf_counter", lambda: 100.0)

    budget = summary_service._calculate_body_budget(
        system_id="sys_hop",
        system_name="HOP",
        static_prefix_text="STATIC",
    )
    assert 1 <= budget <= settings.LLM_INPUT_MAX_TOKENS

    stage1_response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content=json.dumps(
                        {
                            "relevant_domains": "system_positioning",
                            "related_systems": ["HOP", "ECIF"],
                        },
                        ensure_ascii=False,
                    )
                )
            )
        ],
        usage=SimpleNamespace(total_tokens=91, prompt_tokens=11, completion_tokens=80),
    )
    stage2_response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content=json.dumps(
                        {
                            "profile_data": {
                                "system_positioning": {"description": "系统定位"},
                                "business_capabilities": {"description": "核心流程"},
                                "integration_interfaces": {"description": "依赖ESB"},
                                "technical_architecture": {
                                    "description": "微服务架构",
                                    "tech_stack": ["Redis"],
                                },
                                "constraints_risks": {"description": "强监管"},
                            }
                        },
                        ensure_ascii=False,
                    )
                )
            )
        ],
        usage=SimpleNamespace(total_tokens=109, prompt_tokens=20, completion_tokens=89),
    )

    monkeypatch.setattr(profile_summary_service.llm_client, "_chat_raw", lambda messages, **kwargs: stage1_response)
    monkeypatch.setattr(profile_summary_service.llm_client, "extract_json", lambda text: json.loads(text))
    stage1 = summary_service._execute_stage1(
        system_id="sys_hop",
        system_name="HOP",
        context_text="系统定位与微服务架构说明",
        chunk_index=0,
        estimated_tokens=123,
    )

    assert stage1["relevant_domains"] == ["system_positioning", "technical_architecture"]
    assert stage1["related_systems"] == ["ECIF"]
    assert metrics[0]["stage"] == "stage1"
    assert metrics[0]["usage"]["total_tokens"] == 91

    monkeypatch.setattr(profile_summary_service.llm_client, "_chat_raw", lambda messages, **kwargs: stage2_response)
    stage2 = summary_service._execute_stage2(
        system_id="sys_hop",
        system_name="HOP",
        context_text="系统定位与微服务架构说明",
        relevant_domains=["system_positioning", "technical_architecture"],
        chunk_index=1,
        estimated_tokens=234,
    )

    assert stage2["system_positioning"]["system_description"] == "系统定位"
    assert stage2["business_capabilities"]["core_processes"] == ["核心流程"]
    assert stage2["integration_interfaces"]["external_dependencies"] == ["依赖ESB"]
    assert stage2["technical_architecture"]["architecture_positioning"] == "微服务架构"
    assert stage2["constraints_risks"]["known_risks"] == ["强监管"]
    assert metrics[1]["stage"] == "stage2"
    assert metrics[1]["usage"]["total_tokens"] == 109

    bad_response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps({"relevant_domains": []}, ensure_ascii=False)))],
        usage=None,
    )
    monkeypatch.setattr(profile_summary_service.llm_client, "_chat_raw", lambda messages, **kwargs: bad_response)
    with pytest.raises(ValueError, match="CHUNK_PROCESSING_FAILED"):
        summary_service._execute_stage1(
            system_id="sys_hop",
            system_name="HOP",
            context_text="无效响应",
            chunk_index=2,
            estimated_tokens=12,
        )


def test_get_profile_summary_service_returns_singleton(monkeypatch):
    monkeypatch.setattr(profile_summary_service, "_profile_summary_service", None)

    first = profile_summary_service.get_profile_summary_service()
    second = profile_summary_service.get_profile_summary_service()

    assert first is second
