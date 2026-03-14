from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional


class SkillRuntimeService:
    BUILTIN_SKILLS: List[Dict[str, Any]] = [
        {
            "skill_id": "service_governance_skill",
            "skill_type": "governance",
            "supported_inputs": ["xlsx", "xls", "csv"],
            "supported_tasks": ["import"],
            "target_artifacts": ["integration_interfaces"],
            "execution_mode": "sync",
            "decision_policy": "auto_apply",
            "version": "2.7.0",
            "enabled": True,
        },
        {
            "skill_id": "system_catalog_skill",
            "skill_type": "catalog",
            "supported_inputs": ["xlsx", "xls"],
            "supported_tasks": ["preview", "confirm"],
            "target_artifacts": ["system_positioning", "technical_architecture", "constraints_risks"],
            "execution_mode": "sync",
            "decision_policy": "auto_apply",
            "version": "2.7.0",
            "enabled": True,
        },
        {
            "skill_id": "requirements_skill",
            "skill_type": "document",
            "supported_inputs": ["docx", "pdf", "pptx"],
            "supported_tasks": ["ingest"],
            "target_artifacts": ["system_positioning", "business_capabilities", "constraints_risks"],
            "execution_mode": "sync",
            "decision_policy": "suggestion_only",
            "version": "2.7.0",
            "enabled": True,
        },
        {
            "skill_id": "design_skill",
            "skill_type": "document",
            "supported_inputs": ["docx", "pdf", "pptx"],
            "supported_tasks": ["ingest"],
            "target_artifacts": ["technical_architecture"],
            "execution_mode": "sync",
            "decision_policy": "suggestion_only",
            "version": "2.7.0",
            "enabled": True,
        },
        {
            "skill_id": "tech_solution_skill",
            "skill_type": "document",
            "supported_inputs": ["docx", "pdf", "pptx"],
            "supported_tasks": ["ingest"],
            "target_artifacts": ["integration_interfaces", "technical_architecture", "constraints_risks"],
            "execution_mode": "sync",
            "decision_policy": "suggestion_only",
            "version": "2.7.0",
            "enabled": True,
        },
        {
            "skill_id": "code_scan_skill",
            "skill_type": "code_scan",
            "supported_inputs": ["repo_path", "repo_archive"],
            "supported_tasks": ["scan"],
            "target_artifacts": ["technical_architecture", "feature_context"],
            "execution_mode": "async",
            "decision_policy": "suggestion_only",
            "version": "2.7.0",
            "enabled": True,
            "scan_boundary": "Java / Spring Boot + JS / TS 中度语义扫描",
        },
    ]

    COMPONENTS = [
        "Skill Registry",
        "Skill Router",
        "Scene Executor",
        "Policy Gate",
        "Memory Reader/Writer",
    ]

    SCENES = {
        "admin_service_governance_import": {"skill_chain": ["service_governance_skill"]},
        "admin_system_catalog_import": {"skill_chain": ["system_catalog_skill"]},
        "system_identification": {"skill_chain": []},
        "feature_breakdown": {"skill_chain": []},
        "code_scan_ingest": {"skill_chain": ["code_scan_skill"]},
    }

    DOC_TYPE_TO_SKILL = {
        "requirements": "requirements_skill",
        "design": "design_skill",
        "tech_solution": "tech_solution_skill",
    }

    def __init__(self, extra_skills: Optional[List[Dict[str, Any]]] = None) -> None:
        self._skills = copy.deepcopy(self.BUILTIN_SKILLS)
        for skill in extra_skills or []:
            if isinstance(skill, dict):
                self._skills.append(copy.deepcopy(skill))

    def list_enabled_skills(self) -> List[Dict[str, Any]]:
        return [copy.deepcopy(item) for item in self._skills if bool(item.get("enabled", True))]

    def get_registry_snapshot(self) -> Dict[str, Any]:
        return {
            "components": list(self.COMPONENTS),
            "scenes": copy.deepcopy(self.SCENES),
            "all_skill_ids": [str(item.get("skill_id") or "") for item in self._skills],
            "enabled_skill_ids": [str(item.get("skill_id") or "") for item in self._skills if bool(item.get("enabled", True))],
        }

    def get_skill(self, skill_id: str) -> Dict[str, Any]:
        normalized_skill_id = str(skill_id or "").strip()
        for item in self._skills:
            if str(item.get("skill_id") or "").strip() == normalized_skill_id:
                return copy.deepcopy(item)
        raise ValueError("skill_not_found")

    def resolve_scene(self, scene_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        normalized_scene_id = str(scene_id or "").strip()
        context = context if isinstance(context, dict) else {}

        if normalized_scene_id == "pm_document_ingest":
            doc_type = str(context.get("doc_type") or "").strip()
            skill_id = self.DOC_TYPE_TO_SKILL.get(doc_type)
            if not skill_id:
                raise ValueError("unknown_doc_type")
            return {
                "scene_id": normalized_scene_id,
                "skill_chain": [skill_id],
            }

        scene = self.SCENES.get(normalized_scene_id)
        if not scene:
            raise ValueError("unknown_scene")
        return {
            "scene_id": normalized_scene_id,
            "skill_chain": list(scene.get("skill_chain") or []),
        }


_skill_runtime_service: Optional[SkillRuntimeService] = None


def get_skill_runtime_service() -> SkillRuntimeService:
    global _skill_runtime_service
    if _skill_runtime_service is None:
        _skill_runtime_service = SkillRuntimeService()
    return _skill_runtime_service
