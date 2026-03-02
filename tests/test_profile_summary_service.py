import copy
import json

import pytest

from backend.config.config import settings
from backend.service import profile_summary_service
from backend.service.system_profile_service import SystemProfileService


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
