from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from backend.api import system_routes
from backend.service.profile_artifact_service import get_profile_artifact_service
from backend.service.profile_schema_service import get_field_value, has_non_empty_value
from backend.service.system_profile_service import get_system_profile_service
from backend.utils.time_utils import current_time_iso


class ProfileHealthService:
    LOW_CONFIDENCE_THRESHOLD = 0.6

    def __init__(self) -> None:
        self.artifact_service = get_profile_artifact_service()
        self.profile_service = get_system_profile_service()

    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _normalize_candidate_map(self, value: Any) -> Dict[str, Dict[str, Any]]:
        raw_candidates = value if isinstance(value, dict) else {}
        normalized: Dict[str, Dict[str, Any]] = {}
        for raw_field_path, raw_payload in raw_candidates.items():
            field_path = str(raw_field_path or "").strip()
            if not field_path:
                continue
            if isinstance(raw_payload, dict):
                payload = dict(raw_payload)
            else:
                payload = {"value": raw_payload}
            if not has_non_empty_value(payload.get("value")):
                continue
            normalized[field_path] = payload
        return normalized

    def _canonical_compare_value(self, value: Any) -> str:
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False, sort_keys=True)
        return str(value or "").strip()

    def _find_matching_output_record(
        self,
        *,
        system_id: str,
        wiki_artifact_id: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        output_items = self.artifact_service.list_layer_records(layer="output", system_id=system_id)
        import_quality_items = []
        for item in output_items:
            payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
            output_type = str(payload.get("output_type") or "").strip()
            if output_type not in {"", "import_quality"}:
                continue
            import_quality_items.append(item)
        normalized_wiki_artifact_id = str(wiki_artifact_id or "").strip()
        if normalized_wiki_artifact_id:
            for item in import_quality_items:
                if str(item.get("source_artifact_id") or "").strip() == normalized_wiki_artifact_id:
                    return dict(item)
        if not import_quality_items:
            return None
        return dict(import_quality_items[0])

    def _find_latest_health_report_record(self, *, system_id: str) -> Optional[Dict[str, Any]]:
        output_items = self.artifact_service.list_layer_records(layer="output", system_id=system_id)
        for item in output_items:
            payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
            if str(payload.get("output_type") or "").strip() != "health_report":
                continue
            return dict(item)
        return None

    def build_report(self, *, system_id: str, system_name: str = "") -> Dict[str, Any]:
        normalized_system_id = str(system_id or "").strip()
        owner_info = system_routes.resolve_system_owner(system_id=normalized_system_id)
        resolved_system_name = str(system_name or owner_info.get("system_name") or "").strip()
        projection_items = self.artifact_service.list_candidate_records(
            system_id=normalized_system_id,
            category="projections",
        )
        latest_projection = dict(projection_items[0]) if projection_items else {}
        previous_projection = dict(projection_items[1]) if len(projection_items) > 1 else {}
        latest_projection_payload = latest_projection.get("payload") if isinstance(latest_projection.get("payload"), dict) else {}
        previous_projection_payload = previous_projection.get("payload") if isinstance(previous_projection.get("payload"), dict) else {}
        latest_projection_candidates = self.profile_service._normalize_projection_candidate_map(
            latest_projection_payload.get("merged_candidates")
        ) if latest_projection_payload else {}
        previous_projection_candidates = self.profile_service._normalize_projection_candidate_map(
            previous_projection_payload.get("merged_candidates")
        ) if previous_projection_payload else {}

        if latest_projection_candidates:
            latest_wiki = latest_projection
            previous_wiki = previous_projection
            candidate_bundle = self.profile_service._load_latest_candidate_bundle(normalized_system_id)
            quality_report = candidate_bundle.get("quality_report") if isinstance(candidate_bundle.get("quality_report"), dict) else {}
            missing_fields_from_quality = [
                str(item).strip()
                for item in (quality_report.get("missing_targets") or [])
                if str(item).strip()
            ]
            target_field_count = int(quality_report.get("target_field_count") or 0)
            latest_candidates = latest_projection_candidates
            previous_candidates = previous_projection_candidates
            target_fields = list(latest_candidates.keys())
            for field_path in missing_fields_from_quality:
                if field_path not in target_fields:
                    target_fields.append(field_path)
        else:
            wiki_items = self.artifact_service.list_layer_records(layer="wiki", system_id=normalized_system_id)
            latest_wiki = dict(wiki_items[0]) if wiki_items else {}
            previous_wiki = dict(wiki_items[1]) if len(wiki_items) > 1 else {}
            latest_wiki_payload = latest_wiki.get("payload") if isinstance(latest_wiki.get("payload"), dict) else {}
            previous_wiki_payload = previous_wiki.get("payload") if isinstance(previous_wiki.get("payload"), dict) else {}

            target_fields = [
                str(item).strip()
                for item in (latest_wiki_payload.get("target_fields") or [])
                if str(item).strip()
            ]
            target_field_count = len(target_fields)
            latest_candidates = self._normalize_candidate_map(latest_wiki_payload.get("candidates"))
            previous_candidates = self._normalize_candidate_map(previous_wiki_payload.get("candidates"))

        missing_target_fields = [field for field in target_fields if field not in latest_candidates]
        if not target_field_count:
            target_field_count = len(target_fields) or len(latest_candidates)
        candidate_field_count = len(latest_candidates)
        coverage_ratio = round(
            (candidate_field_count / target_field_count) if target_field_count else 0.0,
            2,
        )

        low_confidence_candidates: List[Dict[str, Any]] = []
        for field_path, payload in latest_candidates.items():
            confidence = round(self._safe_float(payload.get("confidence"), default=0.0), 2)
            if confidence >= self.LOW_CONFIDENCE_THRESHOLD:
                continue
            low_confidence_candidates.append(
                {
                    "field_path": field_path,
                    "confidence": confidence,
                    "value": payload.get("value"),
                    "reason": str(payload.get("reason") or "").strip(),
                    "artifact_id": latest_wiki.get("artifact_id"),
                }
            )

        conflicts: List[Dict[str, Any]] = []
        for field_path, payload in latest_candidates.items():
            latest_value = payload.get("value")
            previous_value = previous_candidates.get(field_path, {}).get("value")
            if has_non_empty_value(previous_value) and self._canonical_compare_value(previous_value) != self._canonical_compare_value(latest_value):
                conflicts.append(
                    {
                        "field_path": field_path,
                        "conflict_type": "wiki_candidate_changed",
                        "previous_value": previous_value,
                        "latest_value": latest_value,
                        "previous_artifact_id": previous_wiki.get("artifact_id"),
                        "latest_artifact_id": latest_wiki.get("artifact_id"),
                    }
                )

        profile = self.profile_service.get_profile(resolved_system_name) if resolved_system_name else None
        profile_data = (profile or {}).get("profile_data") if isinstance(profile, dict) else {}
        for field_path, payload in latest_candidates.items():
            canonical_value = get_field_value(profile_data, field_path)
            if not has_non_empty_value(canonical_value):
                continue
            latest_value = payload.get("value")
            if self._canonical_compare_value(canonical_value) == self._canonical_compare_value(latest_value):
                continue
            conflicts.append(
                {
                    "field_path": field_path,
                    "conflict_type": "canonical_vs_candidate",
                    "canonical_value": canonical_value,
                    "latest_value": latest_value,
                    "latest_artifact_id": latest_wiki.get("artifact_id"),
                }
            )

        latest_output = self._find_matching_output_record(
            system_id=normalized_system_id,
            wiki_artifact_id=latest_wiki.get("artifact_id"),
        )
        latest_output_payload = latest_output.get("payload") if isinstance((latest_output or {}).get("payload"), dict) else {}
        quality = latest_output_payload.get("quality") if isinstance(latest_output_payload.get("quality"), dict) else {}
        latest_output_quality = {
            "artifact_id": latest_output.get("artifact_id") if isinstance(latest_output, dict) else None,
            "line_count": int(quality.get("line_count") or 0),
            "suggestion_count": int(quality.get("suggestion_count") or 0),
            "missing_targets": [
                str(item).strip()
                for item in (quality.get("missing_targets") or [])
                if str(item).strip()
            ],
        }
        latest_output_quality["missing_target_count"] = len(latest_output_quality["missing_targets"])
        latest_output_quality["noise_ratio"] = round(
            (
                latest_output_quality["missing_target_count"] / target_field_count
                if target_field_count
                else 0.0
            ),
            2,
        )

        return {
            "artifact_id": None,
            "generated_at": None,
            "output_type": "health_report",
            "system_id": normalized_system_id,
            "system_name": resolved_system_name,
            "coverage": {
                "target_field_count": target_field_count,
                "candidate_field_count": candidate_field_count,
                "missing_target_fields": missing_target_fields,
                "coverage_ratio": coverage_ratio,
            },
            "low_confidence_candidates": low_confidence_candidates,
            "conflicts": conflicts,
            "latest_output_quality": latest_output_quality,
        }

    def get_latest_report(self, *, system_id: str, system_name: str = "") -> Dict[str, Any]:
        normalized_system_id = str(system_id or "").strip()
        latest_record = self._find_latest_health_report_record(system_id=normalized_system_id)
        if latest_record:
            payload = latest_record.get("payload") if isinstance(latest_record.get("payload"), dict) else {}
            if payload:
                archived_payload = dict(payload)
                archived_payload["artifact_id"] = str(latest_record.get("artifact_id") or "").strip() or None
                return archived_payload
        return self.build_report(system_id=normalized_system_id, system_name=system_name)

    def generate_and_archive_report(
        self,
        *,
        system_id: str,
        system_name: str = "",
        operator_id: str = "system",
    ) -> Dict[str, Any]:
        normalized_system_id = str(system_id or "").strip()
        report = self.build_report(system_id=normalized_system_id, system_name=system_name)
        generated_at = current_time_iso()
        latest_projection = self.artifact_service.list_candidate_records(
            system_id=normalized_system_id,
            category="projections",
        )
        if latest_projection:
            source_artifact_id = str((latest_projection[0] if latest_projection else {}).get("artifact_id") or "").strip() or None
        else:
            latest_wiki = self.artifact_service.list_layer_records(layer="wiki", system_id=normalized_system_id)
            source_artifact_id = str((latest_wiki[0] if latest_wiki else {}).get("artifact_id") or "").strip() or None

        report_payload = {
            **report,
            "generated_at": generated_at,
            "output_type": "health_report",
        }
        artifact = self.artifact_service.append_layer_record(
            layer="output",
            system_id=normalized_system_id,
            payload=report_payload,
            operator_id=str(operator_id or "system").strip() or "system",
            source_artifact_id=source_artifact_id,
            latest_file_name="health/latest_report.json",
        )
        report_payload["artifact_id"] = str(artifact.get("artifact_id") or "").strip() or None
        return report_payload


_profile_health_service: Optional[ProfileHealthService] = None


def get_profile_health_service() -> ProfileHealthService:
    global _profile_health_service
    expected_artifact_root = get_profile_artifact_service().root_dir
    expected_store_path = get_system_profile_service().store_path
    if (
        _profile_health_service is None
        or _profile_health_service.artifact_service.root_dir != expected_artifact_root
        or _profile_health_service.profile_service.store_path != expected_store_path
    ):
        _profile_health_service = ProfileHealthService()
    return _profile_health_service
