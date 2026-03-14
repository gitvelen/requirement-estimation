import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.config.config import settings
from backend.service.memory_service import MemoryService
from backend.service.runtime_execution_service import RuntimeExecutionService


def test_memory_service_supports_query_and_future_types(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "REPORT_DIR", str(data_dir))

    service = MemoryService()
    service.append_record(
        system_id="SYS-001",
        memory_type="profile_update",
        memory_subtype="document_suggestion",
        scene_id="pm_document_ingest",
        source_type="document",
        source_id="exec-1",
        summary="写入画像建议",
        payload={"changed_fields": ["system_positioning.canonical.service_scope"]},
        decision_policy="suggestion_only",
        confidence=0.82,
    )
    service.append_record(
        system_id="SYS-001",
        memory_type="review_resolution",
        memory_subtype="future",
        scene_id="future_scene",
        source_type="future_source",
        source_id="future-1",
        summary="未来扩展",
        payload={"k": "v"},
        decision_policy="reject",
        confidence=1.0,
    )

    all_records = service.query_records("SYS-001")
    assert all_records["total"] == 2
    assert all_records["items"][0]["memory_type"] == "review_resolution"

    profile_records = service.query_records("SYS-001", memory_type="profile_update")
    assert profile_records["total"] == 1
    assert profile_records["items"][0]["memory_subtype"] == "document_suggestion"


def test_runtime_execution_service_tracks_latest_status_and_partial_success(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "REPORT_DIR", str(data_dir))

    service = RuntimeExecutionService()
    execution = service.create_execution(
        scene_id="pm_document_ingest",
        system_id="SYS-001",
        source_type="document",
        source_file="requirements.docx",
        skill_chain=["requirements_skill"],
    )
    assert execution["status"] == "queued"

    updated = service.update_execution(
        execution["execution_id"],
        status="partial_success",
        error="memory write failed",
        result_summary={"updated_system_ids": ["SYS-001"], "skipped_items": []},
        policy_results=[
            {
                "field_path": "system_positioning.canonical.service_scope",
                "decision": "suggestion_only",
                "reason": "pm_document_ingest always suggestion_only",
            }
        ],
    )
    assert updated["status"] == "partial_success"
    assert updated["error"] == "memory write failed"

    latest = service.get_latest_execution("SYS-001")
    assert latest["execution_id"] == execution["execution_id"]
    assert latest["status"] == "partial_success"
    assert latest["skill_chain"] == ["requirements_skill"]
