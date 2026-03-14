import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.service.skill_runtime_service import SkillRuntimeService


def test_skill_runtime_registry_exposes_six_builtin_skills_and_ignores_disabled_future_skill():
    service = SkillRuntimeService(
        extra_skills=[
            {
                "skill_id": "requirement_review_skill",
                "skill_type": "future",
                "supported_inputs": ["docx"],
                "supported_tasks": ["review"],
                "target_artifacts": ["review_note"],
                "execution_mode": "sync",
                "decision_policy": "suggestion_only",
                "version": "0.1.0",
                "enabled": False,
            }
        ]
    )

    builtins = service.list_enabled_skills()
    assert [item["skill_id"] for item in builtins] == [
        "service_governance_skill",
        "system_catalog_skill",
        "requirements_skill",
        "design_skill",
        "tech_solution_skill",
        "code_scan_skill",
    ]

    registry = service.get_registry_snapshot()
    assert "requirement_review_skill" in registry["all_skill_ids"]
    assert "requirement_review_skill" not in registry["enabled_skill_ids"]


def test_skill_runtime_routes_core_scenes_to_expected_skill_chain():
    service = SkillRuntimeService()

    pm_scene = service.resolve_scene("pm_document_ingest", {"doc_type": "requirements"})
    governance_scene = service.resolve_scene("admin_service_governance_import", {})
    catalog_scene = service.resolve_scene("admin_system_catalog_import", {})

    assert pm_scene["skill_chain"] == ["requirements_skill"]
    assert governance_scene["skill_chain"] == ["service_governance_skill"]
    assert catalog_scene["skill_chain"] == ["system_catalog_skill"]
