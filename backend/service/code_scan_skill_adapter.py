from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from backend.config.config import settings
from backend.service.memory_service import get_memory_service
from backend.service.system_profile_service import get_system_profile_service


def _normalize_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


class CodeScanSkillAdapter:
    def __init__(self) -> None:
        self.memory_service = get_memory_service()
        self.profile_service = get_system_profile_service()

    def _infer_tech_stack(self, result_payload: Dict[str, Any]) -> Dict[str, Any]:
        items = result_payload.get("items") if isinstance(result_payload.get("items"), list) else []
        languages: List[str] = []
        frameworks: List[str] = []

        for item in items:
            if not isinstance(item, dict):
                continue
            location = item.get("location") if isinstance(item.get("location"), dict) else {}
            file_name = _normalize_text(location.get("file")).lower()
            entry_type = _normalize_text(item.get("entry_type"))

            if file_name.endswith(".java") and "Java" not in languages:
                languages.append("Java")
            if file_name.endswith((".js", ".jsx")) and "JavaScript" not in languages:
                languages.append("JavaScript")
            if file_name.endswith((".ts", ".tsx")) and "TypeScript" not in languages:
                languages.append("TypeScript")

            if entry_type == "http_api" and "Spring Boot" not in frameworks:
                frameworks.append("Spring Boot")

        return {
            "languages": languages,
            "frameworks": frameworks,
            "databases": [],
            "middleware": [],
            "others": [],
        }

    def build_suggestions(self, result_payload: Dict[str, Any]) -> Dict[str, Any]:
        analysis = result_payload.get("analysis") if isinstance(result_payload.get("analysis"), dict) else {}
        impact = analysis.get("impact") if isinstance(analysis.get("impact"), dict) else {}
        service_dependencies = analysis.get("service_dependencies") if isinstance(analysis.get("service_dependencies"), dict) else {}

        tech_stack = self._infer_tech_stack(result_payload)
        code_structure = {
            "ast_summary": analysis.get("ast_summary") or {},
            "call_graph": {
                "node_count": int((analysis.get("call_graph") or {}).get("node_count") or 0),
                "edge_count": int((analysis.get("call_graph") or {}).get("edge_count") or 0),
            },
            "service_dependencies": service_dependencies.get("by_type") or {},
            "complexity": analysis.get("complexity") or {},
        }
        feature_context = {
            "features": impact.get("features") or [],
            "apis": impact.get("apis") or [],
            "evidence": impact.get("evidence") or [],
        }
        interface_clues = {
            "dependencies": service_dependencies.get("dependencies") or [],
            "total": int(service_dependencies.get("total") or 0),
        }

        return {
            "technical_architecture.canonical.tech_stack": {
                "value": tech_stack,
                "scene_id": "code_scan_ingest",
                "skill_id": "code_scan_skill",
                "decision_policy": "suggestion_only",
                "confidence": 0.65,
                "reason": "基于代码扫描推断技术栈，仅作为建议上下文",
            },
            "technical_architecture.canonical.extensions.code_structure": {
                "value": code_structure,
                "scene_id": "code_scan_ingest",
                "skill_id": "code_scan_skill",
                "decision_policy": "suggestion_only",
                "confidence": 0.7,
                "reason": "基于代码扫描生成的工程结构与复杂度摘要",
            },
            "technical_architecture.canonical.extensions.feature_context": {
                "value": feature_context,
                "scene_id": "code_scan_ingest",
                "skill_id": "code_scan_skill",
                "decision_policy": "suggestion_only",
                "confidence": 0.7,
                "reason": "用于后续功能点拆解的代码上下文摘要",
            },
            "technical_architecture.canonical.extensions.interface_clues": {
                "value": interface_clues,
                "scene_id": "code_scan_ingest",
                "skill_id": "code_scan_skill",
                "decision_policy": "suggestion_only",
                "confidence": 0.65,
                "reason": "基于代码扫描得到的接口与依赖线索",
            },
        }

    def apply_scan_result(
        self,
        *,
        system_id: str,
        system_name: str,
        execution_id: str,
        source_file: str,
        result_payload: Dict[str, Any],
        actor: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        normalized_system_id = _normalize_text(system_id) or _normalize_text(system_name)
        normalized_system_name = _normalize_text(system_name)
        if not normalized_system_name:
            raise ValueError("system_name不能为空")

        self.profile_service.ensure_profile(
            normalized_system_name,
            system_id=normalized_system_id if normalized_system_id != normalized_system_name else None,
            actor=actor,
        )
        suggestions = self.build_suggestions(result_payload)

        existing = self.profile_service.get_profile(normalized_system_name) or {}
        merged_suggestions = (
            existing.get("ai_suggestions") if isinstance(existing.get("ai_suggestions"), dict) else {}
        )
        merged_suggestions = {**merged_suggestions, **suggestions}
        self.profile_service.update_ai_suggestions_map(
            normalized_system_name,
            suggestions=merged_suggestions,
            actor=actor,
        )

        policy_results = [
            {
                "field_path": field_path,
                "decision": "suggestion_only",
                "reason": "code_scan_skill always suggestion_only",
            }
            for field_path in suggestions.keys()
        ]

        status = "completed"
        memory_error = None
        try:
            self.memory_service.append_record(
                system_id=normalized_system_id,
                memory_type="profile_update",
                memory_subtype="code_scan_suggestion",
                scene_id="code_scan_ingest",
                source_type="code_scan",
                source_id=str(execution_id or "").strip(),
                summary="代码扫描生成画像建议",
                payload={
                    "changed_fields": list(suggestions.keys()),
                    "source_file": _normalize_text(source_file),
                },
                decision_policy="suggestion_only",
                confidence=0.7,
                actor=(actor or {}).get("username"),
            )
        except Exception as exc:  # pragma: no cover
            status = "partial_success"
            memory_error = str(exc)

        return {
            "status": status,
            "memory_error": memory_error,
            "policy_results": policy_results,
            "suggestions": suggestions,
        }


_code_scan_skill_adapter: Optional[CodeScanSkillAdapter] = None


def get_code_scan_skill_adapter() -> CodeScanSkillAdapter:
    global _code_scan_skill_adapter
    expected_memory_path = os.path.join(settings.REPORT_DIR, "memory_records.json")
    expected_profile_path = os.path.join(settings.REPORT_DIR, "system_profiles.json")
    if (
        _code_scan_skill_adapter is None
        or os.path.realpath(_code_scan_skill_adapter.memory_service.store_path) != os.path.realpath(expected_memory_path)
        or os.path.realpath(_code_scan_skill_adapter.profile_service.store_path) != os.path.realpath(expected_profile_path)
    ):
        _code_scan_skill_adapter = CodeScanSkillAdapter()
    return _code_scan_skill_adapter
