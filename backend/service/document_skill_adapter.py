from __future__ import annotations

import os
from typing import Any, Dict, Optional

from backend.service.document_parser import get_document_parser
from backend.service.memory_service import get_memory_service
from backend.service.runtime_execution_service import get_runtime_execution_service
from backend.service.skill_runtime_service import get_skill_runtime_service
from backend.service.system_profile_service import get_system_profile_service


def _parsed_to_text(parsed_data: Any) -> str:
    if isinstance(parsed_data, str):
        return parsed_data
    if isinstance(parsed_data, list):
        lines = []
        for item in parsed_data:
            if isinstance(item, dict):
                line = " ".join(str(value).strip() for value in item.values() if str(value).strip())
            else:
                line = str(item or "").strip()
            if line:
                lines.append(line)
        return "\n".join(lines)
    if isinstance(parsed_data, dict):
        lines = []
        if isinstance(parsed_data.get("paragraphs"), list):
            for paragraph in parsed_data["paragraphs"]:
                if isinstance(paragraph, dict):
                    text = str(paragraph.get("text") or "").strip()
                else:
                    text = str(paragraph or "").strip()
                if text:
                    lines.append(text)
        if isinstance(parsed_data.get("tables"), list):
            for table in parsed_data["tables"]:
                if not isinstance(table, dict):
                    continue
                for row in table.get("data") or []:
                    if isinstance(row, list):
                        text = " | ".join(str(cell).strip() for cell in row if str(cell or "").strip())
                    else:
                        text = str(row or "").strip()
                    if text:
                        lines.append(text)
        if isinstance(parsed_data.get("slides"), list):
            for slide in parsed_data["slides"]:
                if isinstance(slide, dict):
                    text = str(slide.get("text") or "").strip()
                else:
                    text = str(slide or "").strip()
                if text:
                    lines.append(text)
        if isinstance(parsed_data.get("pages"), list):
            for page in parsed_data["pages"]:
                if isinstance(page, dict):
                    text = str(page.get("text") or "").strip()
                else:
                    text = str(page or "").strip()
                if text:
                    lines.append(text)
        return "\n".join(lines)
    return str(parsed_data or "").strip()


class DocumentSkillAdapter:
    ALLOWED_EXTENSIONS = {".docx", ".pdf", ".pptx"}

    def __init__(self) -> None:
        self.document_parser = get_document_parser()
        self.runtime_service = get_skill_runtime_service()
        self.execution_service = get_runtime_execution_service()
        self.memory_service = get_memory_service()
        self.profile_service = get_system_profile_service()

    def _build_suggestions(self, doc_type: str, text: str, skill_id: str) -> Dict[str, Any]:
        snippet = str(text or "").strip()[:200]
        if doc_type == "requirements":
            field_path = "system_positioning.canonical.service_scope"
        elif doc_type == "design":
            field_path = "technical_architecture.canonical.architecture_style"
        else:
            field_path = "constraints_risks.canonical.known_risks"

        payload: Dict[str, Any] = {
            "value": [snippet] if field_path.endswith("known_risks") else snippet,
            "scene_id": "pm_document_ingest",
            "skill_id": skill_id,
            "decision_policy": "suggestion_only",
            "confidence": 0.7,
            "reason": "从文档正文中提取的保守建议",
        }
        return {field_path: payload}

    def ingest_document(
        self,
        *,
        system_id: str,
        system_name: str,
        doc_type: str,
        file_name: str,
        file_content: bytes,
        actor: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        ext = os.path.splitext(str(file_name or "").lower())[1]
        if ext not in self.ALLOWED_EXTENSIONS:
            raise ValueError(f"文件类型不支持: {ext}")

        scene = self.runtime_service.resolve_scene("pm_document_ingest", {"doc_type": doc_type})
        skill_id = scene["skill_chain"][0]
        execution = self.execution_service.create_execution(
            scene_id="pm_document_ingest",
            system_id=system_id,
            source_type="document",
            source_file=file_name,
            skill_chain=scene["skill_chain"],
        )
        try:
            parsed = self.document_parser.parse(file_content=file_content, filename=file_name)
            text = _parsed_to_text(parsed)
            if not str(text or "").strip():
                raise ValueError("未提取到有效正文")

            self.profile_service.ensure_profile(system_name, system_id=system_id, actor=actor)
            suggestions = self._build_suggestions(doc_type, text, skill_id)
            self.profile_service.update_ai_suggestions_map(system_name, suggestions=suggestions, actor=actor)

            policy_results = []
            for field_path in suggestions:
                policy_results.append(
                    {
                        "field_path": field_path,
                        "decision": "suggestion_only",
                        "reason": "pm_document_ingest always suggestion_only",
                    }
                )

            status_name = "completed"
            memory_error = None
            try:
                self.memory_service.append_record(
                    system_id=system_id,
                    memory_type="profile_update",
                    memory_subtype="document_suggestion",
                    scene_id="pm_document_ingest",
                    source_type="document",
                    source_id=execution["execution_id"],
                    summary=f"{doc_type} 文档导入生成画像建议",
                    payload={"changed_fields": list(suggestions.keys())},
                    decision_policy="suggestion_only",
                    confidence=0.7,
                    actor=(actor or {}).get("username"),
                )
            except Exception as exc:  # pragma: no cover - exercised via failure injection later
                status_name = "partial_success"
                memory_error = str(exc)

            updated_execution = self.execution_service.update_execution(
                execution["execution_id"],
                status=status_name,
                error=memory_error,
                result_summary={"updated_system_ids": [system_id], "skipped_items": []},
                policy_results=policy_results,
            )
        except Exception as exc:
            updated_execution = self.execution_service.update_execution(
                execution["execution_id"],
                status="failed",
                error=str(exc),
                result_summary={"updated_system_ids": [], "skipped_items": []},
                policy_results=[],
            )
            raise

        return {
            "execution": updated_execution,
            "policy_results": updated_execution.get("policy_results") or [],
            "memory_error": updated_execution.get("error"),
        }


_document_skill_adapter: Optional[DocumentSkillAdapter] = None


def get_document_skill_adapter() -> DocumentSkillAdapter:
    global _document_skill_adapter
    if _document_skill_adapter is None:
        _document_skill_adapter = DocumentSkillAdapter()
    return _document_skill_adapter
