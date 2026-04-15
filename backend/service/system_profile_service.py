"""
系统画像服务（B层）
维护系统画像的草稿/发布态与证据引用。
"""
from __future__ import annotations

import copy
import json
import logging
import os
import re
import threading
import uuid
from contextlib import contextmanager
from typing import Any, Callable, Dict, List, Optional

try:
    import fcntl
    FCNTL_AVAILABLE = True
except ImportError:
    FCNTL_AVAILABLE = False

from backend.config.config import settings
from backend.service.memory_service import get_memory_service
from backend.service.profile_artifact_service import get_profile_artifact_service
from backend.service.runtime_execution_service import get_runtime_execution_service
from backend.service.system_profile_repository import (
    SystemProfileRepository,
    get_system_profile_repository,
    resolve_system_profile_root,
)
from backend.service.profile_schema_service import (
    DOMAIN_TITLES,
    PROFILE_CARD_DEFINITIONS,
    PROFILE_CARD_DEFINITIONS_BY_KEY,
    V27_DOMAIN_KEYS,
    apply_card_content_to_profile,
    build_card_candidates,
    build_domain_summary,
    build_empty_profile_data,
    build_profile_cards,
    get_card_keys_for_field_path,
    get_field_value,
    get_logical_field_key,
    has_non_empty_value,
    normalize_profile_data,
    normalize_card_baselines,
    resolve_canonical_field_path,
    set_field_value,
)
from backend.service.system_profile_legacy_helper import (
    LEGACY_TREE_ERROR,
    LEGACY_CONSTRAINT_KEY,
    LEGACY_FIELDS_KEY,
    LEGACY_INTERFACE_KEY,
    LEGACY_MODULE_TREE_KEY,
    LEGACY_PENDING_FIELDS_KEY,
    LEGACY_PROFILE_DOMAIN_KEYS,
    LEGACY_PROFILE_FIELD_KEYS,
    LEGACY_PROFILE_FIELD_MAPPING,
    LEGACY_SYSTEM_SCOPE_KEY,
    default_legacy_profile_data,
    extract_legacy_fields_from_profile_data,
    is_v24_profile_shape,
    merge_profile_data,
    migrate_suggestions_structure,
    normalize_module_structure,
    normalize_domain_value_for_legacy_field,
    normalize_fields_for_output,
    normalize_fields_for_storage,
    normalize_interface_payload as normalize_interface_entries,
    normalize_constraint_payload as normalize_constraint_entries,
    normalize_capability_payload as normalize_capability_tree,
    normalize_metric_payload as normalize_metric_profile,
    normalize_legacy_profile_value as normalize_legacy_profile_part,
    normalize_text_payload as normalize_text_entries,
    build_profile_data_from_legacy_fields,
)
from backend.utils.time_utils import current_time_iso

logger = logging.getLogger(__name__)

PROFILE_FIELD_KEYS = LEGACY_PROFILE_FIELD_KEYS
PROFILE_V24_DOMAIN_KEYS = LEGACY_PROFILE_DOMAIN_KEYS
PROFILE_V24_TO_LEGACY_FIELD = LEGACY_PROFILE_FIELD_MAPPING
V27_LEGACY_TO_CANONICAL_FIELD = {
    ("system_positioning", "system_description"): "core_responsibility",
    ("system_positioning", "service_scope"): "core_responsibility",
    ("system_positioning", "business_domain"): "business_domains",
    ("business_capabilities", "core_processes"): "business_flows",
    ("business_capabilities", "business_processes"): "business_flows",
    ("business_capabilities", "data_assets"): "data_reports",
    ("integration_interfaces", "integration_points"): "other_integrations",
    ("technical_architecture", "architecture_positioning"): "architecture_style",
    ("constraints_risks", "key_constraints"): "prerequisites",
    ("constraints_risks", "technical_constraints"): "prerequisites",
    ("constraints_risks", "known_risks"): "risk_items",
}
V27_CANONICAL_TO_LEGACY_FIELDS: Dict[tuple[str, str], List[str]] = {}
for (_domain_key, _legacy_field), _canonical_field in V27_LEGACY_TO_CANONICAL_FIELD.items():
    V27_CANONICAL_TO_LEGACY_FIELDS.setdefault((_domain_key, _canonical_field), []).append(_legacy_field)

PROFILE_WORKSPACE_RESET_SCENE_IDS = [
    "pm_document_ingest",
    "admin_service_governance_import",
    "admin_system_catalog_import",
]
AUTHORITATIVE_ONLY_CANDIDATE_FIELDS = {
    "integration_interfaces.canonical.provided_services",
    "integration_interfaces.canonical.consumed_services",
}


class SystemProfileService:
    def __init__(self, store_path: Optional[str] = None) -> None:
        requested_path = str(store_path or "").strip()
        legacy_store_dir = str(getattr(settings, "REPORT_DIR", "") or "").strip() or "data"
        explicit_legacy_store_path = ""
        if requested_path.lower().endswith(".json"):
            explicit_legacy_store_path = os.path.abspath(requested_path)
            legacy_store_dir = os.path.dirname(explicit_legacy_store_path) or legacy_store_dir
            requested_path = os.path.splitext(requested_path)[0]
        self.store_path = resolve_system_profile_root(requested_path or None)
        self.repository = SystemProfileRepository(root_dir=self.store_path)
        self.lock_path = os.path.join(self.store_path, ".service.lock")
        self.import_history_store_path = os.path.join(self.store_path, "_compat_import_history.json")
        self.extraction_task_store_path = os.path.join(self.store_path, "_compat_extraction_tasks.json")
        self.legacy_store_path = explicit_legacy_store_path or os.path.join(legacy_store_dir, "system_profiles.json")
        self.legacy_import_history_store_path = os.path.join(legacy_store_dir, "import_history.json")
        self.legacy_extraction_task_store_path = os.path.join(legacy_store_dir, "extraction_tasks.json")
        self._mutex = threading.RLock()
        self._extraction_task_listeners: List[Callable[[Dict[str, Any]], None]] = []
        self._run_startup_migration()

    @contextmanager
    def _lock(self):
        if FCNTL_AVAILABLE:
            os.makedirs(os.path.dirname(self.lock_path) or ".", exist_ok=True)
            with open(self.lock_path, "a") as lock_file:
                fcntl.flock(lock_file, fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(lock_file, fcntl.LOCK_UN)
        else:
            with self._mutex:
                yield

    def _load_unlocked(self) -> List[Dict[str, Any]]:
        try:
            return self.repository.list_profiles(state="working")
        except Exception as exc:
            logger.warning(f"读取系统画像失败: {exc}")
            return []

    def _save_unlocked(self, items: List[Dict[str, Any]]) -> None:
        self.repository.save_working_profiles(items)

    def _load_object_file_unlocked(self, path: str) -> Dict[str, Any]:
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception as exc:
            logger.warning("读取JSON对象文件失败(%s): %s", path, exc)
            return {}

    def _save_object_file_unlocked(self, path: str, payload: Dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        tmp_path = f"{path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)

    def _resolve_profile_system_id(self, profile: Optional[Dict[str, Any]], fallback_name: str = "") -> str:
        if isinstance(profile, dict):
            direct_system_id = str(profile.get("system_id") or "").strip()
            if direct_system_id:
                return direct_system_id
            profile_name = str(profile.get("system_name") or fallback_name or "").strip()
            if profile_name:
                return self._resolve_system_id_from_catalog(profile_name)
        fallback_profile_name = str(fallback_name or "").strip()
        if not fallback_profile_name:
            return ""
        return self._resolve_system_id_from_catalog(fallback_profile_name)

    def _resolve_artifact_operator_id(self, actor: Optional[Dict[str, Any]]) -> str:
        return str((actor or {}).get("username") or (actor or {}).get("id") or "system").strip() or "system"

    def _get_latest_wiki_artifact_id(self, system_id: str) -> Optional[str]:
        latest_projection = self._get_latest_projection_record(system_id)
        artifact_id = str((latest_projection or {}).get("artifact_id") or "").strip()
        if artifact_id:
            return artifact_id
        latest_wiki = self._get_latest_wiki_candidate_record(system_id)
        artifact_id = str((latest_wiki or {}).get("artifact_id") or "").strip()
        return artifact_id or None

    def _append_output_artifact(
        self,
        *,
        system_id: str,
        payload: Dict[str, Any],
        actor: Optional[Dict[str, Any]] = None,
        source_artifact_id: Optional[str] = None,
        latest_file_name: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        normalized_system_id = str(system_id or "").strip()
        if not normalized_system_id:
            return None
        try:
            return get_profile_artifact_service().append_layer_record(
                layer="output",
                system_id=normalized_system_id,
                payload=payload if isinstance(payload, dict) else {},
                operator_id=self._resolve_artifact_operator_id(actor),
                source_artifact_id=source_artifact_id,
                latest_file_name=latest_file_name,
            )
        except Exception as exc:  # pragma: no cover
            logger.warning("写入系统画像 output 产物失败 system=%s error=%s", normalized_system_id, exc)
            return None

    def _record_decision_output(
        self,
        *,
        profile: Optional[Dict[str, Any]],
        system_name: str,
        decision_action: str,
        actor: Optional[Dict[str, Any]] = None,
        domain: Optional[str] = None,
        sub_field: Optional[str] = None,
        target_field_path: Optional[str] = None,
        extra_payload: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        normalized_system_name = str(system_name or "").strip()
        system_id = self._resolve_profile_system_id(profile, normalized_system_name)
        if not system_id:
            return None

        payload = {
            "output_type": "decision_log",
            "decision_action": str(decision_action or "").strip() or "unknown",
            "system_id": system_id,
            "system_name": normalized_system_name,
            "domain": str(domain or "").strip() or None,
            "sub_field": str(sub_field or "").strip() or None,
            "target_field_path": str(target_field_path or "").strip() or None,
            "profile_status": str((profile or {}).get("status") or "draft").strip() or "draft",
            "created_at": current_time_iso(),
        }
        if isinstance(extra_payload, dict):
            payload.update(extra_payload)

        return self._append_output_artifact(
            system_id=system_id,
            payload=payload,
            actor=actor,
            source_artifact_id=self._get_latest_wiki_artifact_id(system_id),
            latest_file_name="decisions/latest_decision.json",
        )

    def record_estimation_context_artifact(
        self,
        *,
        system_name: str,
        task_id: str,
        features: List[Dict[str, Any]],
        context_payload: Optional[Dict[str, Any]] = None,
        actor: Optional[Dict[str, Any]] = None,
        trigger: str = "task_estimate",
    ) -> Optional[Dict[str, Any]]:
        normalized_system_name = str(system_name or "").strip()
        normalized_task_id = str(task_id or "").strip()
        if not normalized_system_name or not normalized_task_id:
            return None

        normalized_context = context_payload if isinstance(context_payload, dict) else {}
        system_id = str(normalized_context.get("system_id") or "").strip() or self._resolve_system_id_from_catalog(normalized_system_name)
        if not system_id:
            return None

        feature_items: List[Dict[str, Any]] = []
        for feature in features or []:
            if not isinstance(feature, dict):
                continue
            feature_items.append(
                {
                    "feature_id": str(feature.get("id") or "").strip() or None,
                    "feature_name": str(feature.get("功能点") or feature.get("name") or "").strip(),
                    "expected": feature.get("expected") if feature.get("expected") is not None else feature.get("预估人天"),
                    "original_estimate": feature.get("original_estimate"),
                    "profile_context_used": bool(feature.get("profile_context_used")),
                    "context_source": str(feature.get("context_source") or normalized_context.get("context_source") or "none").strip() or "none",
                }
            )
        if not feature_items:
            return None

        payload = {
            "output_type": "estimation_context",
            "task_id": normalized_task_id,
            "trigger": str(trigger or "").strip() or "task_estimate",
            "system_id": system_id,
            "system_name": normalized_system_name,
            "profile_context_used": bool(normalized_context.get("profile_context_used")),
            "context_source": str(normalized_context.get("context_source") or "none").strip() or "none",
            "context_text": str(normalized_context.get("text") or "").strip(),
            "feature_count": len(feature_items),
            "features": feature_items,
            "generated_at": current_time_iso(),
        }
        return self._append_output_artifact(
            system_id=system_id,
            payload=payload,
            actor=actor,
            source_artifact_id=self._get_latest_wiki_artifact_id(system_id),
            latest_file_name="estimation/latest_estimation.json",
        )

    def _find_profile(self, items: List[Dict[str, Any]], system_name: str) -> Optional[Dict[str, Any]]:
        for item in items:
            if isinstance(item, dict) and item.get("system_name") == system_name:
                return item
        return None

    def _normalize_capability_tree(self, value: Any, *, strict: bool) -> List[Dict[str, Any]]:
        return normalize_capability_tree(value, strict=strict)

    def _normalize_module_structure(self, value: Any, *, strict: bool) -> List[Dict[str, Any]]:
        return normalize_module_structure(value, strict=strict)

    def _normalize_fields_for_storage(self, fields: Dict[str, Any]) -> Dict[str, Any]:
        return normalize_fields_for_storage(fields)

    def _normalize_fields_for_output(self, fields: Dict[str, Any]) -> Dict[str, Any]:
        return normalize_fields_for_output(fields)

    def _normalize_ai_suggestion_ignored_for_storage(self, value: Any) -> Dict[str, Any]:
        raw_ignored = value if isinstance(value, dict) else {}
        normalized: Dict[str, Any] = {}
        for raw_key, raw_value in raw_ignored.items():
            raw_field_path = str(raw_key or "").strip()
            field_path = resolve_canonical_field_path(raw_field_path)
            if not field_path or "." not in field_path:
                continue
            if raw_field_path and "." in raw_field_path and raw_field_path not in normalized:
                normalized[raw_field_path] = copy.deepcopy(raw_value)
            if field_path not in normalized or raw_field_path == field_path:
                normalized[field_path] = copy.deepcopy(raw_value)
        return normalized

    def _normalize_v27_metadata_map(self, value: Any) -> Dict[str, Any]:
        raw_map = value if isinstance(value, dict) else {}
        normalized: Dict[str, Any] = {}
        for raw_key, raw_value in raw_map.items():
            field_path = resolve_canonical_field_path(str(raw_key or "").strip())
            if not field_path:
                continue
            if isinstance(raw_value, dict):
                payload = copy.deepcopy(raw_value)
            else:
                payload = {"value": copy.deepcopy(raw_value)}
            payload.setdefault("logical_field", get_logical_field_key(field_path))
            payload.setdefault("canonical_field_path", field_path)
            normalized[field_path] = payload
        return normalized

    def _normalize_v27_ai_suggestions(self, value: Any) -> Dict[str, Any]:
        raw_map = value if isinstance(value, dict) else {}
        normalized: Dict[str, Any] = {}
        for raw_key, raw_value in raw_map.items():
            field_path = str(raw_key or "").strip()
            if not field_path:
                continue
            if "." in field_path:
                canonical_field_path = resolve_canonical_field_path(field_path)
                if canonical_field_path not in normalized or field_path == canonical_field_path:
                    normalized[canonical_field_path] = copy.deepcopy(raw_value)
                continue

            domain_key = field_path
            if domain_key not in V27_DOMAIN_KEYS or not isinstance(raw_value, dict):
                normalized[field_path] = copy.deepcopy(raw_value)
                continue

            canonical_payload = raw_value.get("canonical") if isinstance(raw_value.get("canonical"), dict) else None
            if canonical_payload:
                for nested_key, nested_value in canonical_payload.items():
                    canonical_field_path = resolve_canonical_field_path(f"{domain_key}.canonical.{nested_key}")
                    if canonical_field_path not in normalized or canonical_field_path == f"{domain_key}.canonical.{nested_key}":
                        normalized[canonical_field_path] = copy.deepcopy(nested_value)

            for nested_key, nested_value in raw_value.items():
                nested_field = str(nested_key or "").strip()
                if not nested_field or nested_field == "canonical":
                    continue
                canonical_sub_field = self._resolve_v27_canonical_sub_field(domain_key, nested_field)
                canonical_field_path = resolve_canonical_field_path(f"{domain_key}.canonical.{canonical_sub_field}")
                if canonical_field_path not in normalized or canonical_field_path == f"{domain_key}.canonical.{nested_field}":
                    normalized[canonical_field_path] = copy.deepcopy(nested_value)
        return normalized

    def _normalize_v27_card_baselines(self, value: Any) -> Dict[str, Dict[str, Any]]:
        return normalize_card_baselines(value)

    def _build_v27_profile_record(self, system_name: str, system_id: str, now: str) -> Dict[str, Any]:
        profile = {
            "system_id": system_id,
            "system_name": system_name,
            "status": "draft",
            "created_at": now,
            "updated_at": now,
            "profile_data": build_empty_profile_data(),
            "field_sources": {},
            "ai_suggestions": {},
            "ai_suggestion_ignored": {},
            "card_baselines": {},
            "evidence_refs": [],
        }
        self._refresh_v27_card_views(profile)
        return profile

    def _refresh_v27_card_views(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        if not getattr(settings, "ENABLE_V27_PROFILE_SCHEMA", False):
            return profile

        profile_data = normalize_profile_data(profile.get("profile_data"))
        field_sources = self._normalize_v27_metadata_map(profile.get("field_sources"))
        projection_suggestions = self._load_projection_candidate_map(str(profile.get("system_id") or "").strip())
        stored_ai_suggestions = self._normalize_v27_ai_suggestions(profile.get("ai_suggestions"))
        card_candidate_source = projection_suggestions or stored_ai_suggestions
        ignored_map = self._normalize_ai_suggestion_ignored_for_storage(profile.get("ai_suggestion_ignored"))
        baselines = self._normalize_v27_card_baselines(profile.get("card_baselines"))

        profile["profile_data"] = profile_data
        profile["field_sources"] = field_sources
        profile["ai_suggestions"] = stored_ai_suggestions
        profile["card_baselines"] = baselines
        profile["board_version"] = "cards_v1"
        profile["profile_cards"] = build_profile_cards(
            profile_data,
            field_sources=field_sources,
            baselines=baselines,
        )
        profile["card_candidates"] = build_card_candidates(
            card_candidate_source,
            ignored_map=ignored_map,
            profile_data=profile_data,
        )
        profile["domain_summary"] = build_domain_summary(
            profile.get("profile_cards"),
            card_candidates=profile.get("card_candidates"),
        )
        return profile

    def _update_v27_card_baselines_from_sources(
        self,
        profile: Dict[str, Any],
        *,
        field_updates: Dict[str, Any],
        field_sources: Dict[str, Any],
    ) -> None:
        if not field_updates or not field_sources:
            return

        trusted_paths = [
            field_path
            for field_path, source_meta in field_sources.items()
            if isinstance(source_meta, dict) and str(source_meta.get("source") or "").strip() in {"system_catalog", "governance"}
        ]
        if not trusted_paths:
            return

        baselines = self._normalize_v27_card_baselines(profile.get("card_baselines"))
        normalized_profile = normalize_profile_data(profile.get("profile_data"))
        for field_path in trusted_paths:
            card_keys = get_card_keys_for_field_path(field_path)
            if not card_keys:
                continue
            value = get_field_value(normalized_profile, field_path)
            if not has_non_empty_value(value):
                continue
            for card_key in card_keys:
                card_baseline = dict(baselines.get(card_key) or {})
                card_baseline[field_path] = copy.deepcopy(value)
                baselines[card_key] = card_baseline
        profile["card_baselines"] = baselines

    def _resolve_card_candidate_content(
        self,
        profile: Dict[str, Any],
        *,
        card_key: str,
    ) -> Dict[str, Any]:
        candidate_cards = profile.get("card_candidates") if isinstance(profile.get("card_candidates"), dict) else {}
        candidate_card = candidate_cards.get(card_key) if isinstance(candidate_cards.get(card_key), dict) else {}
        candidate_content = candidate_card.get("content") if isinstance(candidate_card.get("content"), dict) else {}
        if candidate_content:
            return copy.deepcopy(candidate_content)

        projection_suggestions = self._load_projection_candidate_map(str(profile.get("system_id") or "").strip())
        stored_ai_suggestions = self._normalize_v27_ai_suggestions(profile.get("ai_suggestions"))
        card_candidate_source = projection_suggestions or stored_ai_suggestions
        ignored_map = self._normalize_ai_suggestion_ignored_for_storage(profile.get("ai_suggestion_ignored"))
        raw_candidate_cards = build_card_candidates(
            card_candidate_source,
            ignored_map=ignored_map,
        )
        raw_candidate_card = raw_candidate_cards.get(card_key) if isinstance(raw_candidate_cards.get(card_key), dict) else {}
        raw_candidate_content = raw_candidate_card.get("content") if isinstance(raw_candidate_card.get("content"), dict) else {}
        return copy.deepcopy(raw_candidate_content) if raw_candidate_content else {}

    def _field_updates_to_card_content(
        self,
        profile: Dict[str, Any],
        *,
        card_key: str,
        source: str = "manual",
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        profile_cards = profile.get("profile_cards") if isinstance(profile.get("profile_cards"), dict) else {}
        card = profile_cards.get(card_key) if isinstance(profile_cards.get(card_key), dict) else {}
        content = card.get("content") if isinstance(card.get("content"), dict) else {}
        field_updates = {}
        field_sources = {}
        for field_path, value in content.items():
            field_updates[str(field_path)] = copy.deepcopy(value)
            field_sources[str(field_path)] = {"source": source}
        return field_updates, field_sources

    def _normalize_profile_for_output(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        if getattr(settings, "ENABLE_V27_PROFILE_SCHEMA", False):
            payload = dict(profile or {})
            self._refresh_v27_card_views(payload)
            payload["ai_suggestions_previous"] = (
                self._normalize_v27_ai_suggestions(payload.get("ai_suggestions_previous"))
                if isinstance(payload.get("ai_suggestions_previous"), dict)
                else None
            )
            payload["ai_suggestion_ignored"] = self._normalize_ai_suggestion_ignored_for_storage(
                payload.get("ai_suggestion_ignored")
            )
            payload["evidence_refs"] = payload.get("evidence_refs") if isinstance(payload.get("evidence_refs"), list) else []
            payload.pop(LEGACY_FIELDS_KEY, None)
            payload.pop(LEGACY_PENDING_FIELDS_KEY, None)
            return payload

        payload = dict(profile or {})
        raw_fields = payload.get(LEGACY_FIELDS_KEY) if isinstance(payload.get(LEGACY_FIELDS_KEY), dict) else {}
        payload[LEGACY_FIELDS_KEY] = self._normalize_fields_for_output(raw_fields)
        if not isinstance(payload.get("field_sources"), dict):
            payload["field_sources"] = {}
        if not isinstance(payload.get("ai_suggestions"), dict):
            payload["ai_suggestions"] = {}
        payload["ai_suggestion_ignored"] = self._normalize_ai_suggestion_ignored_for_storage(
            payload.get("ai_suggestion_ignored")
        )
        payload.setdefault("ai_suggestions_updated_at", "")
        if payload.get("ai_suggestions_updated_at") is None:
            payload["ai_suggestions_updated_at"] = ""
        if payload.get("ai_suggestions_job") is not None and not isinstance(payload.get("ai_suggestions_job"), dict):
            payload["ai_suggestions_job"] = {"raw": payload.get("ai_suggestions_job")}
        return payload

    def _empty_profile_data(self) -> Dict[str, Any]:
        if getattr(settings, "ENABLE_V27_PROFILE_SCHEMA", False):
            return build_empty_profile_data()
        return default_legacy_profile_data()

    def _normalize_profile_data_sub_field(self, domain_key: str, sub_field: str, value: Any) -> Any:
        return normalize_legacy_profile_part(domain_key, sub_field, value)

    def _default_ai_correction_history(self) -> Dict[str, Any]:
        return {
            "total_corrections": 0,
            "last_updated": None,
            "system_level": {"additions": 0, "deletions": 0, "renames": 0},
            "feature_level": {"additions": 0, "deletions": 0, "modifications": 0},
            "estimation_level": {"avg_deviation": 0, "bias_direction": "none", "sample_count": 0},
            "notable_patterns": [],
        }

    def _build_profile_data_from_legacy_fields(self, fields: Dict[str, Any]) -> Dict[str, Any]:
        return build_profile_data_from_legacy_fields(self._empty_profile_data, fields)

    def _is_v24_profile_shape(self, value: Any) -> bool:
        return is_v24_profile_shape(value)

    def _migrate_suggestions_structure(self, value: Any, fallback_fields: Dict[str, Any]) -> Dict[str, Any]:
        return migrate_suggestions_structure(self._empty_profile_data, value, fallback_fields)

    def _migrate_profile_record(self, profile: Dict[str, Any]) -> bool:
        if not isinstance(profile, dict):
            return False

        changed = False
        now = current_time_iso()
        v27_enabled = getattr(settings, "ENABLE_V27_PROFILE_SCHEMA", False)
        fields = profile.get(LEGACY_FIELDS_KEY) if isinstance(profile.get(LEGACY_FIELDS_KEY), dict) else {}
        fields = self._normalize_fields_for_output(fields)

        if not isinstance(profile.get("profile_data"), dict):
            profile["profile_data"] = self._build_profile_data_from_legacy_fields(fields)
            profile["_migrated"] = True
            if not profile.get("_migrated_at"):
                profile["_migrated_at"] = now
            changed = True

        suggestions = profile.get("ai_suggestions")
        if isinstance(suggestions, dict):
            if v27_enabled:
                normalized_suggestions = self._normalize_v27_ai_suggestions(suggestions)
                if suggestions != normalized_suggestions:
                    profile["ai_suggestions"] = normalized_suggestions
                    changed = True
            elif not self._is_v24_profile_shape(suggestions):
                profile["ai_suggestions"] = self._migrate_suggestions_structure(suggestions, fields)
                changed = True
        elif v27_enabled:
            profile["ai_suggestions"] = {}
            changed = True

        if profile.get("ai_suggestions_previous") is not None:
            previous = profile.get("ai_suggestions_previous")
            if isinstance(previous, dict):
                if v27_enabled:
                    normalized_previous = self._normalize_v27_ai_suggestions(previous)
                    if previous != normalized_previous:
                        profile["ai_suggestions_previous"] = normalized_previous
                        changed = True
                elif not self._is_v24_profile_shape(previous):
                    profile["ai_suggestions_previous"] = self._migrate_suggestions_structure(previous, fields)
                    changed = True

        if not isinstance(profile.get("ai_suggestion_ignored"), dict):
            profile["ai_suggestion_ignored"] = {}
            changed = True

        if not isinstance(profile.get("ai_correction_history"), dict):
            profile["ai_correction_history"] = self._default_ai_correction_history()
            changed = True

        if not isinstance(profile.get("profile_events"), list):
            profile["profile_events"] = []
            changed = True

        return changed

    def _run_startup_migration(self) -> None:
        try:
            self.repository.migrate_legacy_profile_store(self.legacy_store_path)
            self.repository.migrate_legacy_import_history(self.legacy_import_history_store_path)
            self.repository.migrate_legacy_extraction_tasks(self.legacy_extraction_task_store_path)
            with self._lock():
                items = self._load_unlocked()
                changed = False
                for item in items:
                    if self._migrate_profile_record(item):
                        changed = True
                if changed:
                    self._save_unlocked(items)
        except Exception as exc:
            logger.warning(f"系统画像启动迁移失败: {exc}")

    def _normalize_domain_value_for_legacy_field(self, legacy_field: str, value: Any) -> Any:
        return normalize_domain_value_for_legacy_field(legacy_field, value)

    def _append_profile_event(
        self,
        profile: Dict[str, Any],
        *,
        event_type: str,
        source: str,
        summary: str,
        affected_domains: Optional[List[str]] = None,
    ) -> None:
        events = profile.get("profile_events") if isinstance(profile.get("profile_events"), list) else []
        events = list(events)
        events.append(
            {
                "event_id": uuid.uuid4().hex,
                "event_type": str(event_type or "").strip(),
                "timestamp": current_time_iso(),
                "source": str(source or "").strip(),
                "summary": str(summary or "").strip(),
                "affected_domains": list(affected_domains or []),
            }
        )
        profile["profile_events"] = events

    def _ensure_profile_data_shape(self, profile: Dict[str, Any], fields: Dict[str, Any]) -> Dict[str, Any]:
        if getattr(settings, "ENABLE_V27_PROFILE_SCHEMA", False):
            profile_data = normalize_profile_data(profile.get("profile_data"))
            profile["profile_data"] = profile_data
            return profile_data
        profile_data = profile.get("profile_data") if isinstance(profile.get("profile_data"), dict) else None
        if profile_data is None:
            profile_data = self._build_profile_data_from_legacy_fields(fields)
            profile["profile_data"] = profile_data
        return profile_data

    def _merge_profile_data(self, base: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
        if getattr(settings, "ENABLE_V27_PROFILE_SCHEMA", False):
            return normalize_profile_data(incoming if isinstance(incoming, dict) else base)
        merged = copy.deepcopy(base if isinstance(base, dict) else self._empty_profile_data())
        if not isinstance(incoming, dict):
            return merged

        for domain_key, domain_value in incoming.items():
            if domain_key not in PROFILE_V24_DOMAIN_KEYS:
                continue
            if not isinstance(domain_value, dict):
                continue
            target_domain = merged.get(domain_key)
            if not isinstance(target_domain, dict):
                target_domain = {}
                merged[domain_key] = target_domain
            for sub_field, sub_value in domain_value.items():
                normalized_sub_field = str(sub_field)
                target_domain[normalized_sub_field] = self._normalize_profile_data_sub_field(
                    domain_key,
                    normalized_sub_field,
                    sub_value,
                )
        return merged

    def _extract_legacy_fields_from_profile_data(self, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(profile_data, dict):
            return {}

        mapped: Dict[str, Any] = {}
        for (domain_key, sub_field), legacy_field in PROFILE_V24_TO_LEGACY_FIELD.items():
            domain_payload = profile_data.get(domain_key)
            if not isinstance(domain_payload, dict):
                continue
            if sub_field not in domain_payload:
                continue
            mapped[legacy_field] = self._normalize_domain_value_for_legacy_field(
                legacy_field,
                domain_payload.get(sub_field),
            )
        return mapped

    def _ensure_suggestions_shape(
        self,
        profile: Dict[str, Any],
        *,
        key: str,
        fields: Dict[str, Any],
    ) -> Dict[str, Any]:
        value = profile.get(key)
        if not isinstance(value, dict):
            return {}
        if getattr(settings, "ENABLE_V27_PROFILE_SCHEMA", False):
            normalized = self._normalize_v27_ai_suggestions(value)
            if value != normalized:
                profile[key] = normalized
            return normalized
        if self._is_v24_profile_shape(value):
            return value
        migrated = self._migrate_suggestions_structure(value, fields)
        profile[key] = migrated
        return migrated

    def _resolve_v27_canonical_sub_field(self, domain: str, sub_field: str) -> str:
        normalized_domain = str(domain or "").strip()
        normalized_sub_field = str(sub_field or "").strip()
        canonical_field_path = resolve_canonical_field_path(
            f"{normalized_domain}.canonical.{normalized_sub_field}"
        )
        if canonical_field_path.startswith(f"{normalized_domain}.canonical."):
            return canonical_field_path.split(".canonical.", 1)[1]
        return V27_LEGACY_TO_CANONICAL_FIELD.get((normalized_domain, normalized_sub_field), normalized_sub_field)

    def _iter_v27_suggestion_field_candidates(self, domain: str, sub_field: str) -> List[str]:
        normalized_domain = str(domain or "").strip()
        normalized_sub_field = str(sub_field or "").strip()
        canonical_sub_field = self._resolve_v27_canonical_sub_field(normalized_domain, normalized_sub_field)

        candidates: List[str] = []
        for candidate in [
            normalized_sub_field,
            canonical_sub_field,
            *V27_CANONICAL_TO_LEGACY_FIELDS.get((normalized_domain, canonical_sub_field), []),
        ]:
            candidate_text = str(candidate or "").strip()
            if candidate_text and candidate_text not in candidates:
                candidates.append(candidate_text)
        return candidates

    def _read_v27_suggestion_value(
        self,
        domain_payload: Any,
        *,
        domain: str,
        sub_field: str,
    ) -> tuple[Optional[str], Any]:
        if not isinstance(domain_payload, dict):
            return None, None

        canonical_payload = domain_payload.get("canonical") if isinstance(domain_payload.get("canonical"), dict) else None
        for candidate in self._iter_v27_suggestion_field_candidates(domain, sub_field):
            if canonical_payload is not None and candidate in canonical_payload:
                return candidate, copy.deepcopy(canonical_payload.get(candidate))
            if candidate in domain_payload:
                return candidate, copy.deepcopy(domain_payload.get(candidate))
        return None, None

    def _unwrap_ai_suggestion_value(self, value: Any) -> Any:
        if isinstance(value, dict) and ("value" in value):
            return copy.deepcopy(value.get("value"))
        return copy.deepcopy(value)

    def _iter_v27_flat_suggestion_paths(self, domain: str, sub_field: str) -> List[str]:
        paths: List[str] = []
        for candidate in self._iter_v27_suggestion_field_candidates(domain, sub_field):
            for field_path in (
                f"{domain}.canonical.{candidate}",
                f"{domain}.{candidate}",
            ):
                if field_path not in paths:
                    paths.append(field_path)
        return paths

    def _read_v27_suggestion_entry(
        self,
        suggestions: Any,
        *,
        domain: str,
        sub_field: str,
    ) -> tuple[Optional[str], Any]:
        if not isinstance(suggestions, dict):
            return None, None

        for candidate in self._iter_v27_suggestion_field_candidates(domain, sub_field):
            flat_canonical_path = f"{domain}.canonical.{candidate}"
            if flat_canonical_path in suggestions:
                return candidate, copy.deepcopy(suggestions.get(flat_canonical_path))

            flat_domain_path = f"{domain}.{candidate}"
            if flat_domain_path in suggestions:
                return candidate, copy.deepcopy(suggestions.get(flat_domain_path))

        domain_payload = suggestions.get(domain)
        return self._read_v27_suggestion_value(
            domain_payload,
            domain=domain,
            sub_field=sub_field,
        )

    def _remove_v27_suggestion_entries(
        self,
        suggestions: Any,
        *,
        domain: str,
        sub_field: str,
    ) -> Dict[str, Any]:
        if not isinstance(suggestions, dict):
            return {}

        next_suggestions = self._normalize_v27_ai_suggestions(suggestions)
        candidates = self._iter_v27_suggestion_field_candidates(domain, sub_field)
        for field_path in self._iter_v27_flat_suggestion_paths(domain, sub_field):
            next_suggestions.pop(field_path, None)

        domain_payload = next_suggestions.get(domain)
        if isinstance(domain_payload, dict):
            canonical_payload = domain_payload.get("canonical")
            if isinstance(canonical_payload, dict):
                for candidate in candidates:
                    canonical_payload.pop(candidate, None)
                if canonical_payload:
                    domain_payload["canonical"] = canonical_payload
                else:
                    domain_payload.pop("canonical", None)

            for candidate in candidates:
                domain_payload.pop(candidate, None)

            if domain_payload:
                next_suggestions[domain] = domain_payload
            else:
                next_suggestions.pop(domain, None)

        return next_suggestions

    def _set_v27_flat_suggestion_entry(
        self,
        suggestions: Any,
        *,
        domain: str,
        sub_field: str,
        value: Any,
    ) -> Dict[str, Any]:
        next_suggestions = self._remove_v27_suggestion_entries(
            suggestions,
            domain=domain,
            sub_field=sub_field,
        )
        canonical_sub_field = self._resolve_v27_canonical_sub_field(domain, sub_field)
        next_suggestions[f"{domain}.canonical.{canonical_sub_field}"] = copy.deepcopy(value)
        return next_suggestions

    def _remove_v27_domain_suggestions(
        self,
        suggestions: Any,
        *,
        domain: str,
    ) -> Dict[str, Any]:
        normalized_domain = str(domain or "").strip()
        next_suggestions = self._normalize_v27_ai_suggestions(suggestions)
        if not normalized_domain:
            return next_suggestions

        domain_prefix = f"{normalized_domain}."
        for field_path in list(next_suggestions.keys()):
            if str(field_path or "").strip().startswith(domain_prefix):
                next_suggestions.pop(field_path, None)
        next_suggestions.pop(normalized_domain, None)
        return next_suggestions

    def _clear_v27_ignored_entries(
        self,
        ignored_map: Any,
        *,
        domain: str,
        sub_field: str,
    ) -> tuple[Dict[str, Any], bool]:
        next_ignored = self._normalize_ai_suggestion_ignored_for_storage(ignored_map)
        removed = False
        keys_to_remove = set()
        for candidate in self._iter_v27_suggestion_field_candidates(domain, sub_field):
            keys_to_remove.add(f"{domain}.{candidate}")
            keys_to_remove.add(f"{domain}.canonical.{candidate}")

        for ignored_key in keys_to_remove:
            if ignored_key in next_ignored:
                next_ignored.pop(ignored_key, None)
                removed = True

        return next_ignored, removed

    def _set_v27_suggestion_value(
        self,
        domain_payload: Any,
        *,
        sub_field: str,
        value: Any,
    ) -> Dict[str, Any]:
        if not isinstance(domain_payload, dict):
            domain_payload = {}

        canonical_payload = domain_payload.get("canonical")
        if isinstance(canonical_payload, dict) and sub_field in canonical_payload:
            canonical_payload[sub_field] = copy.deepcopy(value)
            domain_payload["canonical"] = canonical_payload
            return domain_payload

        domain_payload[sub_field] = copy.deepcopy(value)
        return domain_payload

    def get_profile_events(self, system_name: str, *, limit: int = 20, offset: int = 0) -> Dict[str, Any]:
        name = str(system_name or "").strip()
        if not name:
            raise ValueError("system_name不能为空")

        safe_limit = max(1, min(int(limit or 20), 200))
        safe_offset = max(0, int(offset or 0))

        with self._lock():
            items = self._load_unlocked()
            profile = self._find_profile(items, name)
            if not profile:
                return {"total": 0, "items": []}

            events = profile.get("profile_events") if isinstance(profile.get("profile_events"), list) else []
            ordered = sorted(
                [item for item in events if isinstance(item, dict)],
                key=lambda item: str(item.get("timestamp") or ""),
                reverse=True,
            )
            return {
                "total": len(ordered),
                "items": ordered[safe_offset : safe_offset + safe_limit],
            }

    def accept_ai_suggestion(
        self,
        system_name: str,
        *,
        domain: str,
        sub_field: str,
        actor: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        name = str(system_name or "").strip()
        normalized_domain = str(domain or "").strip()
        normalized_sub_field = str(sub_field or "").strip()
        if not name:
            raise ValueError("system_name不能为空")
        if not normalized_domain or not normalized_sub_field:
            raise ValueError("invalid_domain_or_sub_field")

        actor_name = (actor or {}).get("displayName") or (actor or {}).get("username") or "unknown"
        now = current_time_iso()
        accepted_value = None
        target_sub_field = normalized_sub_field
        normalized_profile: Dict[str, Any]

        with self._lock():
            items = self._load_unlocked()
            profile = self._find_profile(items, name)
            if not profile:
                raise ValueError("系统画像不存在")

            fields = profile.get(LEGACY_FIELDS_KEY) if isinstance(profile.get(LEGACY_FIELDS_KEY), dict) else {}
            fields = self._normalize_fields_for_output(fields)
            profile_data = self._ensure_profile_data_shape(profile, fields)
            if getattr(settings, "ENABLE_V27_PROFILE_SCHEMA", False):
                ai_suggestions = self._normalize_v27_ai_suggestions(profile.get("ai_suggestions"))
                matched_sub_field, accepted_entry = self._read_v27_suggestion_entry(
                    ai_suggestions,
                    domain=normalized_domain,
                    sub_field=normalized_sub_field,
                )
                if matched_sub_field is None:
                    raise ValueError("SUGGESTION_NOT_FOUND")
                accepted_value = self._unwrap_ai_suggestion_value(accepted_entry)
            else:
                ai_suggestions = self._ensure_suggestions_shape(profile, key="ai_suggestions", fields=fields)
                domain_payload = ai_suggestions.get(normalized_domain)
                matched_sub_field, accepted_value = self._read_v27_suggestion_value(
                    domain_payload,
                    domain=normalized_domain,
                    sub_field=normalized_sub_field,
                )
                if matched_sub_field is None:
                    raise ValueError("SUGGESTION_NOT_FOUND")

            target_sub_field = self._resolve_v27_canonical_sub_field(normalized_domain, matched_sub_field)
            current_domain_payload = profile_data.get(normalized_domain)
            if not isinstance(current_domain_payload, dict):
                current_domain_payload = {}
                profile_data[normalized_domain] = current_domain_payload

            if getattr(settings, "ENABLE_V27_PROFILE_SCHEMA", False):
                current_canonical_payload = current_domain_payload.get("canonical")
                if not isinstance(current_canonical_payload, dict):
                    current_canonical_payload = {}
                    current_domain_payload["canonical"] = current_canonical_payload
                current_canonical_payload[target_sub_field] = copy.deepcopy(accepted_value)
            else:
                current_domain_payload[matched_sub_field] = self._normalize_profile_data_sub_field(
                    normalized_domain,
                    matched_sub_field,
                    accepted_value,
                )

            profile["profile_data"] = profile_data
            if getattr(settings, "ENABLE_V27_PROFILE_SCHEMA", False):
                profile["ai_suggestions"] = self._remove_v27_suggestion_entries(
                    ai_suggestions,
                    domain=normalized_domain,
                    sub_field=matched_sub_field,
                )

            legacy_field = (
                PROFILE_V24_TO_LEGACY_FIELD.get((normalized_domain, matched_sub_field))
                or PROFILE_V24_TO_LEGACY_FIELD.get((normalized_domain, target_sub_field))
            )
            if legacy_field:
                normalized_for_storage = self._normalize_fields_for_storage(profile.get(LEGACY_FIELDS_KEY) or {})
                normalized_for_storage[legacy_field] = self._normalize_domain_value_for_legacy_field(
                    legacy_field,
                    accepted_value,
                )
                profile[LEGACY_FIELDS_KEY] = normalized_for_storage

            ignored_map = self._normalize_ai_suggestion_ignored_for_storage(profile.get("ai_suggestion_ignored"))
            if getattr(settings, "ENABLE_V27_PROFILE_SCHEMA", False):
                ignored_map, changed_ignored = self._clear_v27_ignored_entries(
                    ignored_map,
                    domain=normalized_domain,
                    sub_field=matched_sub_field,
                )
            else:
                ignored_keys = {
                    f"{normalized_domain}.{normalized_sub_field}",
                    f"{normalized_domain}.{matched_sub_field}",
                    f"{normalized_domain}.{target_sub_field}",
                }
                changed_ignored = False
                for ignored_key in ignored_keys:
                    if ignored_key in ignored_map:
                        ignored_map.pop(ignored_key, None)
                        changed_ignored = True
            if changed_ignored:
                profile["ai_suggestion_ignored"] = ignored_map

            self._append_profile_event(
                profile,
                event_type="ai_suggestion_accept",
                source=actor_name,
                summary=f"采纳 {normalized_domain}.{normalized_sub_field} 的 AI 建议",
                affected_domains=[normalized_domain],
            )
            profile["updated_at"] = now
            profile["updated_by_name"] = actor_name
            self._save_unlocked(items)
            normalized_profile = self._normalize_profile_for_output(profile)

        self._record_decision_output(
            profile=normalized_profile,
            system_name=name,
            decision_action="accept_suggestion",
            actor=actor,
            domain=normalized_domain,
            sub_field=matched_sub_field,
            target_field_path=f"{normalized_domain}.canonical.{target_sub_field}",
            extra_payload={
                "accepted_value": copy.deepcopy(accepted_value),
                "requested_sub_field": normalized_sub_field,
            },
        )
        return normalized_profile

    def rollback_ai_suggestion(
        self,
        system_name: str,
        *,
        domain: str,
        sub_field: str,
        actor: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        name = str(system_name or "").strip()
        normalized_domain = str(domain or "").strip()
        normalized_sub_field = str(sub_field or "").strip()
        if not name:
            raise ValueError("system_name不能为空")
        if not normalized_domain or not normalized_sub_field:
            raise ValueError("invalid_domain_or_sub_field")

        actor_name = (actor or {}).get("displayName") or (actor or {}).get("username") or "unknown"
        now = current_time_iso()
        normalized_profile: Dict[str, Any]
        rolled_back_value: Any = None
        matched_sub_field = normalized_sub_field

        with self._lock():
            items = self._load_unlocked()
            profile = self._find_profile(items, name)
            if not profile:
                raise ValueError("系统画像不存在")

            fields = profile.get(LEGACY_FIELDS_KEY) if isinstance(profile.get(LEGACY_FIELDS_KEY), dict) else {}
            fields = self._normalize_fields_for_output(fields)
            if getattr(settings, "ENABLE_V27_PROFILE_SCHEMA", False):
                ai_suggestions = self._normalize_v27_ai_suggestions(profile.get("ai_suggestions"))
                previous = self._normalize_v27_ai_suggestions(profile.get("ai_suggestions_previous"))
                matched_sub_field, rolled_back_entry = self._read_v27_suggestion_entry(
                    previous,
                    domain=normalized_domain,
                    sub_field=normalized_sub_field,
                )
                if matched_sub_field is None:
                    raise ValueError("ROLLBACK_NO_PREVIOUS")

                rolled_back_value = self._unwrap_ai_suggestion_value(rolled_back_entry)
                profile["ai_suggestions"] = self._set_v27_flat_suggestion_entry(
                    ai_suggestions,
                    domain=normalized_domain,
                    sub_field=matched_sub_field,
                    value=rolled_back_entry,
                )
                ignored_map, changed_ignored = self._clear_v27_ignored_entries(
                    profile.get("ai_suggestion_ignored"),
                    domain=normalized_domain,
                    sub_field=matched_sub_field,
                )
            else:
                ai_suggestions = self._ensure_suggestions_shape(profile, key="ai_suggestions", fields=fields)
                previous = self._ensure_suggestions_shape(profile, key="ai_suggestions_previous", fields=fields)

                prev_domain_payload = previous.get(normalized_domain) if isinstance(previous, dict) else None
                matched_sub_field, rolled_back_value = self._read_v27_suggestion_value(
                    prev_domain_payload,
                    domain=normalized_domain,
                    sub_field=normalized_sub_field,
                )
                if matched_sub_field is None:
                    raise ValueError("ROLLBACK_NO_PREVIOUS")

                target_domain = ai_suggestions.get(normalized_domain)
                if not isinstance(target_domain, dict):
                    target_domain = {}
                    ai_suggestions[normalized_domain] = target_domain

                target_domain = self._set_v27_suggestion_value(
                    target_domain,
                    sub_field=matched_sub_field,
                    value=rolled_back_value,
                )
                ai_suggestions[normalized_domain] = target_domain
                profile["ai_suggestions"] = ai_suggestions

                ignored_map = self._normalize_ai_suggestion_ignored_for_storage(profile.get("ai_suggestion_ignored"))
                ignored_keys = {
                    f"{normalized_domain}.{normalized_sub_field}",
                    f"{normalized_domain}.{matched_sub_field}",
                    f"{normalized_domain}.{self._resolve_v27_canonical_sub_field(normalized_domain, matched_sub_field)}",
                }
                changed_ignored = False
                for ignored_key in ignored_keys:
                    if ignored_key in ignored_map:
                        ignored_map.pop(ignored_key, None)
                        changed_ignored = True
            if changed_ignored:
                profile["ai_suggestion_ignored"] = ignored_map

            self._append_profile_event(
                profile,
                event_type="ai_suggestion_rollback",
                source=actor_name,
                summary=f"回滚 {normalized_domain}.{normalized_sub_field} 的 AI 建议",
                affected_domains=[normalized_domain],
            )
            profile["updated_at"] = now
            profile["updated_by_name"] = actor_name
            self._save_unlocked(items)
            normalized_profile = self._normalize_profile_for_output(profile)

        self._record_decision_output(
            profile=normalized_profile,
            system_name=name,
            decision_action="rollback_suggestion",
            actor=actor,
            domain=normalized_domain,
            sub_field=matched_sub_field,
            target_field_path=f"{normalized_domain}.canonical.{self._resolve_v27_canonical_sub_field(normalized_domain, matched_sub_field)}",
            extra_payload={
                "rolled_back_value": copy.deepcopy(rolled_back_value),
                "requested_sub_field": normalized_sub_field,
            },
        )
        return {
            "profile": normalized_profile,
            "rolled_back_value": rolled_back_value,
        }

    def ignore_ai_suggestion(
        self,
        system_name: str,
        *,
        domain: str,
        sub_field: str,
        actor: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        name = str(system_name or "").strip()
        normalized_domain = str(domain or "").strip()
        normalized_sub_field = str(sub_field or "").strip()
        if not name:
            raise ValueError("system_name不能为空")
        if not normalized_domain or not normalized_sub_field:
            raise ValueError("invalid_domain_or_sub_field")

        actor_name = (actor or {}).get("displayName") or (actor or {}).get("username") or "unknown"
        now = current_time_iso()
        ignored_value: Any = None
        normalized_profile: Dict[str, Any]
        matched_sub_field = normalized_sub_field

        with self._lock():
            items = self._load_unlocked()
            profile = self._find_profile(items, name)
            if not profile:
                raise ValueError("系统画像不存在")

            fields = profile.get(LEGACY_FIELDS_KEY) if isinstance(profile.get(LEGACY_FIELDS_KEY), dict) else {}
            fields = self._normalize_fields_for_output(fields)
            if getattr(settings, "ENABLE_V27_PROFILE_SCHEMA", False):
                ai_suggestions = self._normalize_v27_ai_suggestions(profile.get("ai_suggestions"))
                matched_sub_field, ignored_entry = self._read_v27_suggestion_entry(
                    ai_suggestions,
                    domain=normalized_domain,
                    sub_field=normalized_sub_field,
                )
                if matched_sub_field is None:
                    raise ValueError("SUGGESTION_NOT_FOUND")
                ignored_value = self._unwrap_ai_suggestion_value(ignored_entry)
            else:
                ai_suggestions = self._ensure_suggestions_shape(profile, key="ai_suggestions", fields=fields)
                domain_payload = ai_suggestions.get(normalized_domain)
                matched_sub_field, ignored_value = self._read_v27_suggestion_value(
                    domain_payload,
                    domain=normalized_domain,
                    sub_field=normalized_sub_field,
                )
                if matched_sub_field is None:
                    raise ValueError("SUGGESTION_NOT_FOUND")

            ignored_key = f"{normalized_domain}.{matched_sub_field}"
            requested_ignored_key = f"{normalized_domain}.{normalized_sub_field}"
            ignored_map = self._normalize_ai_suggestion_ignored_for_storage(profile.get("ai_suggestion_ignored"))
            ignored_map[ignored_key] = ignored_value
            if requested_ignored_key != ignored_key:
                ignored_map[requested_ignored_key] = copy.deepcopy(ignored_value)
            profile["ai_suggestion_ignored"] = ignored_map

            self._append_profile_event(
                profile,
                event_type="ai_suggestion_ignore",
                source=actor_name,
                summary=f"忽略 {normalized_domain}.{normalized_sub_field} 的 AI 建议",
                affected_domains=[normalized_domain],
            )
            profile["updated_at"] = now
            profile["updated_by_name"] = actor_name
            self._save_unlocked(items)
            normalized_profile = self._normalize_profile_for_output(profile)

        self._record_decision_output(
            profile=normalized_profile,
            system_name=name,
            decision_action="ignore_suggestion",
            actor=actor,
            domain=normalized_domain,
            sub_field=matched_sub_field,
            target_field_path=f"{normalized_domain}.canonical.{self._resolve_v27_canonical_sub_field(normalized_domain, matched_sub_field)}",
            extra_payload={
                "ignored_value": copy.deepcopy(ignored_value),
                "requested_sub_field": normalized_sub_field,
            },
        )
        return normalized_profile

    def _parse_v27_field_path(self, field_path: str) -> tuple[Optional[str], Optional[str]]:
        normalized_path = str(field_path or "").strip()
        if not normalized_path:
            return None, None
        if ".canonical." in normalized_path:
            domain_key, sub_field = normalized_path.split(".canonical.", 1)
            return str(domain_key or "").strip() or None, str(sub_field or "").strip() or None
        if "." not in normalized_path:
            return None, None
        domain_key, sub_field = normalized_path.split(".", 1)
        return str(domain_key or "").strip() or None, str(sub_field or "").strip() or None

    def _require_v27_card_key(self, card_key: str) -> str:
        normalized_card_key = str(card_key or "").strip()
        if normalized_card_key not in PROFILE_CARD_DEFINITIONS_BY_KEY:
            raise ValueError("invalid_card_key")
        return normalized_card_key

    def _apply_flat_field_content(
        self,
        profile: Dict[str, Any],
        *,
        card_key: str,
        card_content: Dict[str, Any],
        actor_name: str,
        scene_id: str,
        event_type: str,
        summary: str,
        clear_suggestions: bool = False,
        mark_ignored: bool = False,
        apply_to_profile: bool = True,
    ) -> Dict[str, Any]:
        profile_data = normalize_profile_data(profile.get("profile_data"))
        field_sources = self._normalize_v27_metadata_map(profile.get("field_sources"))
        ai_suggestions = self._normalize_v27_ai_suggestions(profile.get("ai_suggestions"))
        ignored_map = self._normalize_ai_suggestion_ignored_for_storage(profile.get("ai_suggestion_ignored"))

        for field_path, value in card_content.items():
            if apply_to_profile:
                profile_data = set_field_value(profile_data, field_path, value)
            if not mark_ignored:
                field_sources[str(field_path)] = {
                    "source": "manual",
                    "scene_id": scene_id,
                    "card_key": card_key,
                }

            domain_key, sub_field = self._parse_v27_field_path(field_path)
            if not domain_key or not sub_field:
                continue
            if clear_suggestions:
                ai_suggestions = self._remove_v27_suggestion_entries(
                    ai_suggestions,
                    domain=domain_key,
                    sub_field=sub_field,
                )
                ignored_map, _ = self._clear_v27_ignored_entries(
                    ignored_map,
                    domain=domain_key,
                    sub_field=sub_field,
                )
            if mark_ignored:
                ignored_map[field_path] = copy.deepcopy(value)

        if apply_to_profile:
            profile["profile_data"] = profile_data
        profile["field_sources"] = field_sources
        profile["ai_suggestions"] = ai_suggestions
        profile["ai_suggestion_ignored"] = ignored_map

        if apply_to_profile:
            legacy_fields = self._normalize_fields_for_storage(profile.get(LEGACY_FIELDS_KEY) or {})
            for key, value in self._extract_legacy_fields_from_profile_data(profile_data).items():
                legacy_fields[key] = value
            profile[LEGACY_FIELDS_KEY] = legacy_fields

        self._append_profile_event(
            profile,
            event_type=event_type,
            source=actor_name,
            summary=summary,
            affected_domains=[PROFILE_CARD_DEFINITIONS_BY_KEY[card_key]["domain_key"]],
        )
        self._refresh_v27_card_views(profile)
        return profile

    def accept_card_candidate(
        self,
        system_name: str,
        *,
        card_key: str,
        actor: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        name = str(system_name or "").strip()
        normalized_card_key = self._require_v27_card_key(card_key)
        if not name:
            raise ValueError("system_name不能为空")
        if not getattr(settings, "ENABLE_V27_PROFILE_SCHEMA", False):
            raise ValueError("v27_schema_disabled")

        actor_name = (actor or {}).get("displayName") or (actor or {}).get("username") or "unknown"
        now = current_time_iso()

        with self._lock():
            items = self._load_unlocked()
            profile = self._find_profile(items, name)
            if not profile:
                raise ValueError("系统画像不存在")

            self._refresh_v27_card_views(profile)
            candidate_content = self._resolve_card_candidate_content(
                profile,
                card_key=normalized_card_key,
            )
            if not candidate_content:
                raise ValueError("card_candidate_not_found")

            self._apply_flat_field_content(
                profile,
                card_key=normalized_card_key,
                card_content=candidate_content,
                actor_name=actor_name,
                scene_id="card_candidate_accept",
                event_type="ai_suggestion_accept",
                summary=f"采纳卡片 {normalized_card_key} 的候选内容",
                clear_suggestions=True,
            )
            profile["updated_at"] = now
            profile["updated_by_name"] = actor_name
            self._save_unlocked(items)
            normalized_profile = self._normalize_profile_for_output(profile)

        self._record_decision_output(
            profile=normalized_profile,
            system_name=name,
            decision_action="accept_card_candidate",
            actor=actor,
            target_field_path=normalized_card_key,
            extra_payload={"card_key": normalized_card_key},
        )
        return normalized_profile

    def ignore_card_candidate(
        self,
        system_name: str,
        *,
        card_key: str,
        actor: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        name = str(system_name or "").strip()
        normalized_card_key = self._require_v27_card_key(card_key)
        if not name:
            raise ValueError("system_name不能为空")
        if not getattr(settings, "ENABLE_V27_PROFILE_SCHEMA", False):
            raise ValueError("v27_schema_disabled")

        actor_name = (actor or {}).get("displayName") or (actor or {}).get("username") or "unknown"
        now = current_time_iso()

        with self._lock():
            items = self._load_unlocked()
            profile = self._find_profile(items, name)
            if not profile:
                raise ValueError("系统画像不存在")

            self._refresh_v27_card_views(profile)
            candidate_content = self._resolve_card_candidate_content(
                profile,
                card_key=normalized_card_key,
            )
            if not candidate_content:
                raise ValueError("card_candidate_not_found")

            self._apply_flat_field_content(
                profile,
                card_key=normalized_card_key,
                card_content=candidate_content,
                actor_name=actor_name,
                scene_id="card_candidate_ignore",
                event_type="ai_suggestion_ignore",
                summary=f"忽略卡片 {normalized_card_key} 的候选内容",
                mark_ignored=True,
                apply_to_profile=False,
            )
            profile["updated_at"] = now
            profile["updated_by_name"] = actor_name
            self._save_unlocked(items)
            normalized_profile = self._normalize_profile_for_output(profile)

        self._record_decision_output(
            profile=normalized_profile,
            system_name=name,
            decision_action="ignore_card_candidate",
            actor=actor,
            target_field_path=normalized_card_key,
            extra_payload={"card_key": normalized_card_key},
        )
        return normalized_profile

    def restore_card_baseline(
        self,
        system_name: str,
        *,
        card_key: str,
        actor: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        name = str(system_name or "").strip()
        normalized_card_key = self._require_v27_card_key(card_key)
        if not name:
            raise ValueError("system_name不能为空")
        if not getattr(settings, "ENABLE_V27_PROFILE_SCHEMA", False):
            raise ValueError("v27_schema_disabled")

        actor_name = (actor or {}).get("displayName") or (actor or {}).get("username") or "unknown"
        now = current_time_iso()

        with self._lock():
            items = self._load_unlocked()
            profile = self._find_profile(items, name)
            if not profile:
                raise ValueError("系统画像不存在")

            self._refresh_v27_card_views(profile)
            profile_cards = profile.get("profile_cards") if isinstance(profile.get("profile_cards"), dict) else {}
            profile_card = profile_cards.get(normalized_card_key) if isinstance(profile_cards.get(normalized_card_key), dict) else {}
            baseline_content = profile_card.get("baseline_content") if isinstance(profile_card.get("baseline_content"), dict) else {}
            if not baseline_content:
                raise ValueError("card_baseline_not_found")

            self._apply_flat_field_content(
                profile,
                card_key=normalized_card_key,
                card_content=baseline_content,
                actor_name=actor_name,
                scene_id="card_baseline_restore",
                event_type="manual_edit",
                summary=f"恢复卡片 {normalized_card_key} 的高可信基线",
                clear_suggestions=False,
            )
            profile["updated_at"] = now
            profile["updated_by_name"] = actor_name
            self._save_unlocked(items)
            normalized_profile = self._normalize_profile_for_output(profile)

        self._record_decision_output(
            profile=normalized_profile,
            system_name=name,
            decision_action="restore_card_baseline",
            actor=actor,
            target_field_path=normalized_card_key,
            extra_payload={"card_key": normalized_card_key},
        )
        return normalized_profile

    def record_import_history(
        self,
        system_id: str,
        *,
        doc_type: str,
        file_name: str,
        status: str,
        operator_id: str,
        failure_reason: Optional[str] = None,
        execution_id: Optional[str] = None,
        artifact_refs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        normalized_system_id = str(system_id or "").strip()
        if not normalized_system_id:
            raise ValueError("system_id不能为空")

        now = current_time_iso()
        item = {
            "id": uuid.uuid4().hex,
            "doc_type": str(doc_type or "").strip(),
            "file_name": str(file_name or "").strip(),
            "imported_at": now,
            "status": str(status or "").strip() or "failed",
            "failure_reason": None if not str(failure_reason or "").strip() else str(failure_reason or "").strip(),
            "operator_id": str(operator_id or "").strip() or "unknown",
            "execution_id": None if not str(execution_id or "").strip() else str(execution_id or "").strip(),
            "artifact_refs": artifact_refs if isinstance(artifact_refs, dict) else {},
        }

        system_name = self._resolve_workspace_system_name(normalized_system_id)
        return self.repository.append_import_history(
            system_id=normalized_system_id,
            system_name=system_name,
            item=item,
        )

    def reset_profile_workspace(
        self,
        system_name: str,
        *,
        system_id: Optional[str] = None,
        actor: Optional[Dict[str, Any]] = None,
        reason: str = "manual_reset",
    ) -> Dict[str, Any]:
        normalized_system_name = str(system_name or "").strip()
        normalized_system_id = str(system_id or "").strip() or self._resolve_system_id_from_catalog(normalized_system_name)
        if not normalized_system_name and not normalized_system_id:
            raise ValueError("system_id不能为空")

        resolved_system_name = self._resolve_workspace_system_name(
            normalized_system_id,
            preferred_name=normalized_system_name,
        )
        deleted_workspace = self.repository.delete_workspace(
            system_id=normalized_system_id,
            system_name=resolved_system_name,
        )
        runtime_cleanup = get_runtime_execution_service().delete_executions(
            normalized_system_id,
            scene_ids=PROFILE_WORKSPACE_RESET_SCENE_IDS,
        ) if normalized_system_id else {"deleted_count": 0, "deleted_execution_ids": []}
        memory_cleanup = get_memory_service().delete_records(
            normalized_system_id,
            memory_type="profile_update",
            scene_ids=PROFILE_WORKSPACE_RESET_SCENE_IDS,
        ) if normalized_system_id else {"deleted_count": 0, "deleted_memory_ids": []}

        deleted = bool(
            deleted_workspace.get("deleted")
            or int(runtime_cleanup.get("deleted_count") or 0) > 0
            or int(memory_cleanup.get("deleted_count") or 0) > 0
        )

        return {
            "system_id": normalized_system_id or str(deleted_workspace.get("system_id") or "").strip(),
            "system_name": resolved_system_name or str(deleted_workspace.get("system_name") or "").strip(),
            "reason": str(reason or "").strip() or "manual_reset",
            "workspace_deleted": bool(deleted_workspace.get("deleted")),
            "workspace_path": deleted_workspace.get("workspace_path"),
            "deleted_runtime_executions": int(runtime_cleanup.get("deleted_count") or 0),
            "deleted_memory_records": int(memory_cleanup.get("deleted_count") or 0),
            "deleted": deleted,
            "deleted_at": current_time_iso(),
            "deleted_by": self._resolve_artifact_operator_id(actor),
        }

    def reset_all_profile_workspaces(
        self,
        *,
        actor: Optional[Dict[str, Any]] = None,
        reason: str = "manual_reset_all",
    ) -> Dict[str, Any]:
        systems = self.repository.list_workspace_identities()
        results: List[Dict[str, Any]] = []
        deleted_workspace_count = 0
        deleted_runtime_execution_count = 0
        deleted_memory_record_count = 0

        for item in systems:
            system_id = str(item.get("system_id") or "").strip()
            system_name = str(item.get("system_name") or "").strip()
            result = self.reset_profile_workspace(
                system_name,
                system_id=system_id,
                actor=actor,
                reason=reason,
            )
            results.append(result)
            if result.get("workspace_deleted"):
                deleted_workspace_count += 1
            deleted_runtime_execution_count += int(result.get("deleted_runtime_executions") or 0)
            deleted_memory_record_count += int(result.get("deleted_memory_records") or 0)

        return {
            "reason": str(reason or "").strip() or "manual_reset_all",
            "systems": results,
            "deleted_workspace_count": deleted_workspace_count,
            "deleted_runtime_execution_count": deleted_runtime_execution_count,
            "deleted_memory_record_count": deleted_memory_record_count,
            "deleted_at": current_time_iso(),
            "deleted_by": self._resolve_artifact_operator_id(actor),
        }

    def get_import_history(self, system_id: str, *, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        normalized_system_id = str(system_id or "").strip()
        if not normalized_system_id:
            raise ValueError("system_id不能为空")

        safe_limit = max(1, min(int(limit or 50), 200))
        safe_offset = max(0, int(offset or 0))

        records = self.repository.get_import_history(system_id=normalized_system_id)
        records.sort(key=lambda record: str(record.get("imported_at") or ""), reverse=True)
        return {
            "total": len(records),
            "items": records[safe_offset : safe_offset + safe_limit],
        }

    def register_extraction_task_listener(self, listener: Callable[[Dict[str, Any]], None]) -> None:
        if not callable(listener):
            return
        with self._lock():
            if listener in self._extraction_task_listeners:
                return
            self._extraction_task_listeners.append(listener)

    def _notify_extraction_task_listeners(self, system_id: str, task: Dict[str, Any]) -> None:
        listeners = list(self._extraction_task_listeners)
        if not listeners:
            return

        payload = {
            "system_id": str(system_id or "").strip(),
            "task": dict(task or {}),
        }
        for listener in listeners:
            try:
                listener(payload)
            except Exception as exc:
                logger.warning("通知 extraction task listener 失败: %s", exc)

    def upsert_extraction_task(
        self,
        system_id: str,
        *,
        task_id: str,
        status: str,
        trigger: str,
        source_file: Optional[str] = None,
        error: Optional[str] = None,
        notifications: Optional[List[Dict[str, Any]]] = None,
        created_at: Optional[str] = None,
        completed_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        normalized_system_id = str(system_id or "").strip()
        normalized_task_id = str(task_id or "").strip()
        if not normalized_system_id:
            raise ValueError("system_id不能为空")
        if not normalized_task_id:
            raise ValueError("task_id不能为空")

        normalized_status = str(status or "").strip().lower() or "pending"
        now = current_time_iso()

        existing = self.repository.get_extraction_task(system_id=normalized_system_id) or {}
        if str(existing.get("task_id") or "").strip() != normalized_task_id:
            existing = {}

        task = {
            "task_id": normalized_task_id,
            "status": normalized_status,
            "trigger": str(trigger or "").strip() or "document_import",
            "source_file": str(source_file or existing.get("source_file") or "").strip(),
            "created_at": str(created_at or existing.get("created_at") or now),
            "completed_at": completed_at if (completed_at is not None) else existing.get("completed_at"),
            "error": error if (error is not None) else existing.get("error"),
            "notifications": notifications if isinstance(notifications, list) else list(existing.get("notifications") or []),
        }

        if normalized_status in {"pending", "processing"}:
            task["completed_at"] = None
        elif normalized_status in {"completed", "failed"}:
            task["completed_at"] = str(task.get("completed_at") or now)

        if normalized_status != "failed" and not str(error or "").strip():
            task["error"] = None

        system_name = self._resolve_workspace_system_name(normalized_system_id)
        result = self.repository.save_extraction_task(
            system_id=normalized_system_id,
            system_name=system_name,
            task=task,
        )
        self._notify_extraction_task_listeners(normalized_system_id, result)
        return result

    def update_extraction_task_status(
        self,
        system_id: str,
        *,
        task_id: str,
        status: str,
        error: Optional[str] = None,
        notifications: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        normalized_system_id = str(system_id or "").strip()
        normalized_task_id = str(task_id or "").strip()
        if not normalized_system_id:
            raise ValueError("system_id不能为空")
        if not normalized_task_id:
            raise ValueError("task_id不能为空")

        normalized_status = str(status or "").strip().lower() or "pending"
        now = current_time_iso()
        existing = self.repository.get_extraction_task(system_id=normalized_system_id) or {}

        existing_task_id = str(existing.get("task_id") or "").strip()
        if existing_task_id and existing_task_id != normalized_task_id:
            return dict(existing)

        if existing_task_id != normalized_task_id:
            existing = {
                "task_id": normalized_task_id,
                "trigger": "document_import",
                "source_file": "",
                "created_at": now,
                "notifications": [],
            }

        existing["status"] = normalized_status
        if normalized_status in {"pending", "processing"}:
            existing["completed_at"] = None
        elif normalized_status in {"completed", "failed"}:
            existing["completed_at"] = now

        if notifications is not None:
            existing["notifications"] = notifications if isinstance(notifications, list) else []

        if error is not None:
            existing["error"] = str(error).strip() or None
        elif normalized_status != "failed":
            existing["error"] = None

        system_name = self._resolve_workspace_system_name(normalized_system_id)
        result = self.repository.save_extraction_task(
            system_id=normalized_system_id,
            system_name=system_name,
            task=existing,
        )
        self._notify_extraction_task_listeners(normalized_system_id, result)
        return result

    def get_extraction_task(self, system_id: str) -> Optional[Dict[str, Any]]:
        normalized_system_id = str(system_id or "").strip()
        if not normalized_system_id:
            raise ValueError("system_id不能为空")

        task = self.repository.get_extraction_task(system_id=normalized_system_id)
        return dict(task) if isinstance(task, dict) else None

    def get_extraction_task_by_task_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        normalized_task_id = str(task_id or "").strip()
        if not normalized_task_id:
            raise ValueError("task_id不能为空")

        return self.repository.get_extraction_task_by_task_id(normalized_task_id)

    def get_profile(self, system_name: str) -> Optional[Dict[str, Any]]:
        name = str(system_name or "").strip()
        if not name:
            return None
        with self._lock():
            items = self._load_unlocked()
        profile = self._find_profile(items, name)
        if not profile:
            return None
        return self._normalize_profile_for_output(profile)

    def list_profiles(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock():
            items = self._load_unlocked()
        if status:
            items = [item for item in items if item.get("status") == status]
        return [self._normalize_profile_for_output(item) for item in items if isinstance(item, dict)]

    def ensure_profile(
        self,
        system_name: str,
        *,
        system_id: Optional[str] = None,
        actor: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        name = str(system_name or "").strip()
        if not name:
            raise ValueError("system_name不能为空")

        if not getattr(settings, "ENABLE_V27_PROFILE_SCHEMA", False):
            return self.upsert_profile(
                name,
                {"system_id": str(system_id or "").strip(), LEGACY_FIELDS_KEY: {}, "evidence_refs": []},
                actor=actor,
            )

        now = current_time_iso()
        normalized_system_id = str(system_id or "").strip()
        actor_id = (actor or {}).get("id") or (actor or {}).get("username") or "unknown"
        actor_name = (actor or {}).get("displayName") or (actor or {}).get("username") or "unknown"

        with self._lock():
            items = self._load_unlocked()
            existing = self._find_profile(items, name)
            if not existing:
                existing = self._build_v27_profile_record(name, normalized_system_id, now)
                existing["updated_by"] = actor_id
                existing["updated_by_name"] = actor_name
                items.append(existing)
            else:
                existing["profile_data"] = normalize_profile_data(existing.get("profile_data"))
                existing["field_sources"] = self._normalize_v27_metadata_map(existing.get("field_sources"))
                existing["ai_suggestions"] = self._normalize_v27_ai_suggestions(existing.get("ai_suggestions"))
                if normalized_system_id and not str(existing.get("system_id") or "").strip():
                    existing["system_id"] = normalized_system_id
                existing.pop(LEGACY_FIELDS_KEY, None)
                existing.pop(LEGACY_PENDING_FIELDS_KEY, None)
                existing["updated_at"] = str(existing.get("updated_at") or now)

            self._save_unlocked(items)

        return self._normalize_profile_for_output(existing)

    def upsert_profile(
        self,
        system_name: str,
        payload: Dict[str, Any],
        actor: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if getattr(settings, "ENABLE_V27_PROFILE_SCHEMA", False):
            return self._upsert_profile_v27(system_name, payload, actor=actor)

        name = str(system_name or "").strip()
        if not name:
            raise ValueError("system_name不能为空")

        incoming_fields = payload.get(LEGACY_FIELDS_KEY) if isinstance(payload.get(LEGACY_FIELDS_KEY), dict) else {}
        incoming_fields = self._normalize_fields_for_storage(incoming_fields)
        incoming_profile_data = payload.get("profile_data") if isinstance(payload.get("profile_data"), dict) else None
        evidence_refs = payload.get("evidence_refs") if isinstance(payload.get("evidence_refs"), list) else []
        system_id = str(payload.get("system_id") or "").strip()
        incoming_sources = payload.get("field_sources") if isinstance(payload.get("field_sources"), dict) else {}
        incoming_ignored = self._normalize_ai_suggestion_ignored_for_storage(payload.get("ai_suggestion_ignored"))

        now = current_time_iso()
        actor_id = (actor or {}).get("id") or (actor or {}).get("username") or "unknown"
        actor_name = (actor or {}).get("displayName") or (actor or {}).get("username") or "unknown"

        with self._lock():
            items = self._load_unlocked()
            existing = self._find_profile(items, name)
            if not existing:
                existing = {
                    "system_id": system_id,
                    "system_name": name,
                    "status": "draft",
                    LEGACY_FIELDS_KEY: {},
                    "evidence_refs": [],
                    LEGACY_PENDING_FIELDS_KEY: [],
                    "field_sources": {},
                    "ai_suggestions": {},
                    "ai_suggestion_ignored": {},
                    "ai_suggestions_updated_at": "",
                    "created_at": now,
                }
                items.append(existing)

            existing["system_id"] = system_id or existing.get("system_id") or ""
            existing_fields = existing.get(LEGACY_FIELDS_KEY) if isinstance(existing.get(LEGACY_FIELDS_KEY), dict) else {}
            existing_fields = self._normalize_fields_for_storage(existing_fields)

            if incoming_profile_data is not None:
                existing_profile_data = existing.get("profile_data") if isinstance(existing.get("profile_data"), dict) else self._empty_profile_data()
                merged_profile_data = self._merge_profile_data(existing_profile_data, incoming_profile_data)
                existing["profile_data"] = merged_profile_data
                for key, value in self._extract_legacy_fields_from_profile_data(merged_profile_data).items():
                    existing_fields[key] = value

            for field_key in PROFILE_FIELD_KEYS:
                if field_key in incoming_fields:
                    existing_fields[field_key] = incoming_fields.get(field_key)
            existing[LEGACY_FIELDS_KEY] = existing_fields
            existing["evidence_refs"] = evidence_refs

            # field_sources: manual by default for user-provided fields; allow overriding to ai on accept action
            field_sources = existing.get("field_sources") if isinstance(existing.get("field_sources"), dict) else {}
            field_sources = dict(field_sources)
            for key in incoming_fields.keys():
                field_sources[str(key)] = "manual"
            for key, value in incoming_sources.items():
                k = str(key or "").strip()
                v = str(value or "").strip().lower()
                if not k:
                    continue
                if v not in {"manual", "ai"}:
                    continue
                field_sources[k] = v
            existing["field_sources"] = field_sources

            if incoming_ignored:
                existing["ai_suggestion_ignored"] = incoming_ignored
            elif not isinstance(existing.get("ai_suggestion_ignored"), dict):
                existing["ai_suggestion_ignored"] = {}

            existing["updated_by"] = actor_id
            existing["updated_by_name"] = actor_name
            existing["updated_at"] = now

            self._save_unlocked(items)

        return self._normalize_profile_for_output(existing)

    def _upsert_profile_v27(
        self,
        system_name: str,
        payload: Dict[str, Any],
        actor: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        name = str(system_name or "").strip()
        if not name:
            raise ValueError("system_name不能为空")

        now = current_time_iso()
        normalized_system_id = str(payload.get("system_id") or "").strip()
        incoming_profile_data = normalize_profile_data(payload.get("profile_data"))
        evidence_refs = payload.get("evidence_refs") if isinstance(payload.get("evidence_refs"), list) else []
        incoming_sources = self._normalize_v27_metadata_map(payload.get("field_sources"))
        actor_id = (actor or {}).get("id") or (actor or {}).get("username") or "unknown"
        actor_name = (actor or {}).get("displayName") or (actor or {}).get("username") or "unknown"

        with self._lock():
            items = self._load_unlocked()
            existing = self._find_profile(items, name)
            if not existing:
                existing = self._build_v27_profile_record(name, normalized_system_id, now)
                items.append(existing)

            if normalized_system_id:
                existing["system_id"] = normalized_system_id
            elif not str(existing.get("system_id") or "").strip():
                existing["system_id"] = ""

            existing["profile_data"] = incoming_profile_data
            existing["field_sources"] = {
                **self._normalize_v27_metadata_map(existing.get("field_sources")),
                **incoming_sources,
            }
            existing["ai_suggestions"] = self._normalize_v27_ai_suggestions(existing.get("ai_suggestions"))
            existing["evidence_refs"] = evidence_refs
            existing["updated_by"] = actor_id
            existing["updated_by_name"] = actor_name
            existing["updated_at"] = now
            existing.pop(LEGACY_FIELDS_KEY, None)
            existing.pop(LEGACY_PENDING_FIELDS_KEY, None)
            self._update_v27_card_baselines_from_sources(
                existing,
                field_updates=incoming_profile_data,
                field_sources=incoming_sources,
            )
            self._refresh_v27_card_views(existing)

            self._save_unlocked(items)

        return self._normalize_profile_for_output(existing)

    def update_ai_suggestions_map(
        self,
        system_name: str,
        *,
        suggestions: Dict[str, Any],
        actor: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        name = str(system_name or "").strip()
        if not name:
            raise ValueError("system_name不能为空")

        now = current_time_iso()
        actor_id = (actor or {}).get("id") or (actor or {}).get("username") or "unknown"
        actor_name = (actor or {}).get("displayName") or (actor or {}).get("username") or "unknown"

        with self._lock():
            items = self._load_unlocked()
            profile = self._find_profile(items, name)
            if not profile:
                profile = self._build_v27_profile_record(name, "", now)
                items.append(profile)
            profile["ai_suggestions"] = self._normalize_v27_ai_suggestions(suggestions)
            profile["updated_by"] = actor_id
            profile["updated_by_name"] = actor_name
            profile["updated_at"] = now
            profile.pop(LEGACY_FIELDS_KEY, None)
            profile.pop(LEGACY_PENDING_FIELDS_KEY, None)
            self._refresh_v27_card_views(profile)
            self._save_unlocked(items)

        return self._normalize_profile_for_output(profile)

    def apply_v27_field_updates(
        self,
        system_name: str,
        *,
        system_id: Optional[str] = None,
        field_updates: Optional[Dict[str, Any]] = None,
        field_sources: Optional[Dict[str, Any]] = None,
        actor: Optional[Dict[str, Any]] = None,
        evidence_refs: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        name = str(system_name or "").strip()
        if not name:
            raise ValueError("system_name不能为空")
        if not getattr(settings, "ENABLE_V27_PROFILE_SCHEMA", False):
            raise ValueError("v27_schema_disabled")

        now = current_time_iso()
        normalized_system_id = str(system_id or "").strip()
        actor_id = (actor or {}).get("id") or (actor or {}).get("username") or "unknown"
        actor_name = (actor or {}).get("displayName") or (actor or {}).get("username") or "unknown"
        normalized_updates = field_updates if isinstance(field_updates, dict) else {}
        normalized_sources = self._normalize_v27_metadata_map(field_sources)

        with self._lock():
            items = self._load_unlocked()
            profile = self._find_profile(items, name)
            if not profile:
                profile = self._build_v27_profile_record(name, normalized_system_id, now)
                items.append(profile)

            if normalized_system_id:
                profile["system_id"] = normalized_system_id

            profile_data = normalize_profile_data(profile.get("profile_data"))
            for field_path, value in normalized_updates.items():
                profile_data = set_field_value(profile_data, field_path, value)
            profile["profile_data"] = profile_data
            profile["field_sources"] = {
                **self._normalize_v27_metadata_map(profile.get("field_sources")),
                **normalized_sources,
            }
            if evidence_refs is not None:
                profile["evidence_refs"] = evidence_refs if isinstance(evidence_refs, list) else []
            profile["updated_by"] = actor_id
            profile["updated_by_name"] = actor_name
            profile["updated_at"] = now
            profile.pop(LEGACY_FIELDS_KEY, None)
            profile.pop(LEGACY_PENDING_FIELDS_KEY, None)
            self._update_v27_card_baselines_from_sources(
                profile,
                field_updates=normalized_updates,
                field_sources=normalized_sources,
            )
            self._refresh_v27_card_views(profile)

            self._save_unlocked(items)

        return self._normalize_profile_for_output(profile)

    def get_or_create_ai_suggestions_job(
        self,
        system_name: str,
        system_id: Optional[str],
        *,
        actor: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        name = str(system_name or "").strip()
        if not name:
            raise ValueError("system_name不能为空")

        now = current_time_iso()
        actor_id = (actor or {}).get("id") or (actor or {}).get("username") or "unknown"
        normalized_system_id = str(system_id or "").strip()

        with self._lock():
            items = self._load_unlocked()
            profile = self._find_profile(items, name)
            if not profile:
                raise ValueError("系统画像不存在")

            if normalized_system_id and not profile.get("system_id"):
                profile["system_id"] = normalized_system_id

            job = profile.get("ai_suggestions_job") if isinstance(profile.get("ai_suggestions_job"), dict) else {}
            job_id = str(job.get("job_id") or "").strip()
            status = str(job.get("status") or "").strip().lower()
            if job_id and status in {"queued", "running"}:
                return {"job_id": job_id, "status": status, "created_new": False}

            job_id = f"summary_{uuid.uuid4().hex}"
            profile["ai_suggestions_job"] = {
                "job_id": job_id,
                "status": "queued",
                "created_at": now,
                "updated_at": now,
                "triggered_by": actor_id,
            }
            profile["updated_at"] = now
            self._save_unlocked(items)

        return {"job_id": job_id, "status": "queued", "created_new": True}

    def update_ai_suggestions_job(
        self,
        system_name: str,
        *,
        job_id: str,
        status: str,
        error_code: Optional[str] = None,
        error_reason: Optional[str] = None,
    ) -> None:
        name = str(system_name or "").strip()
        if not name:
            raise ValueError("system_name不能为空")

        normalized_job_id = str(job_id or "").strip()
        if not normalized_job_id:
            return

        now = current_time_iso()
        normalized_status = str(status or "").strip().lower() or "running"

        with self._lock():
            items = self._load_unlocked()
            profile = self._find_profile(items, name)
            if not profile:
                return

            job = profile.get("ai_suggestions_job") if isinstance(profile.get("ai_suggestions_job"), dict) else {}
            if str(job.get("job_id") or "").strip() != normalized_job_id:
                return

            job["status"] = normalized_status
            job["updated_at"] = now
            if error_code:
                job["error_code"] = str(error_code)
            if error_reason:
                job["error_reason"] = str(error_reason)[:500]
            profile["ai_suggestions_job"] = job
            profile["updated_at"] = now
            self._save_unlocked(items)

    def set_ai_suggestions(
        self,
        system_name: str,
        *,
        suggestions: Dict[str, Any],
        relevant_domains: Optional[List[str]] = None,
        trigger: str = "document_import",
        source: str = "",
        actor: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        name = str(system_name or "").strip()
        if not name:
            raise ValueError("system_name不能为空")

        now = current_time_iso()
        actor_name = (actor or {}).get("displayName") or (actor or {}).get("username") or "system"
        source_text = str(source or "").strip() or actor_name
        normalized_trigger = str(trigger or "").strip() or "document_import"
        raw_suggestions = suggestions if isinstance(suggestions, dict) else {}

        with self._lock():
            items = self._load_unlocked()
            profile = self._find_profile(items, name)
            if not profile:
                raise ValueError("系统画像不存在")

            fields = profile.get(LEGACY_FIELDS_KEY) if isinstance(profile.get(LEGACY_FIELDS_KEY), dict) else {}
            fields = self._normalize_fields_for_output(fields)

            updated_domains: List[str] = []
            if getattr(settings, "ENABLE_V27_PROFILE_SCHEMA", False):
                existing_suggestions = self._normalize_v27_ai_suggestions(profile.get("ai_suggestions"))
                profile["ai_suggestions_previous"] = copy.deepcopy(existing_suggestions)

                normalized_incoming = self._normalize_v27_ai_suggestions(raw_suggestions)
                inferred_domains = [
                    domain
                    for domain in V27_DOMAIN_KEYS
                    if any(str(field_path or "").strip().startswith(f"{domain}.") for field_path in normalized_incoming.keys())
                ]
                if isinstance(relevant_domains, list) and relevant_domains:
                    target_domains = [
                        str(domain).strip()
                        for domain in relevant_domains
                        if str(domain).strip() in V27_DOMAIN_KEYS
                    ]
                else:
                    target_domains = inferred_domains

                merged_suggestions = copy.deepcopy(existing_suggestions)
                for domain in target_domains:
                    domain_entries = {
                        field_path: copy.deepcopy(value)
                        for field_path, value in normalized_incoming.items()
                        if str(field_path or "").strip().startswith(f"{domain}.")
                    }
                    if not domain_entries:
                        continue
                    merged_suggestions = self._remove_v27_domain_suggestions(
                        merged_suggestions,
                        domain=domain,
                    )
                    merged_suggestions.update(domain_entries)
                    if domain not in updated_domains:
                        updated_domains.append(domain)
            else:
                existing_suggestions = self._ensure_suggestions_shape(profile, key="ai_suggestions", fields=fields)
                if not isinstance(existing_suggestions, dict) or not existing_suggestions:
                    existing_suggestions = self._empty_profile_data()

                profile["ai_suggestions_previous"] = copy.deepcopy(existing_suggestions)

                incoming_is_v24 = self._is_v24_profile_shape(raw_suggestions)
                if incoming_is_v24:
                    normalized_incoming = copy.deepcopy(raw_suggestions)
                    inferred_domains = [
                        domain
                        for domain in PROFILE_V24_DOMAIN_KEYS
                        if domain in normalized_incoming and self._has_value(normalized_incoming.get(domain))
                    ]
                else:
                    normalized_incoming = self._migrate_suggestions_structure(raw_suggestions, fields)
                    inferred_domains = []
                    for (domain_key, sub_field), legacy_field in PROFILE_V24_TO_LEGACY_FIELD.items():
                        if legacy_field in raw_suggestions and self._has_value(raw_suggestions.get(legacy_field)):
                            if domain_key not in inferred_domains:
                                inferred_domains.append(domain_key)
                            _ = sub_field

                if isinstance(relevant_domains, list) and relevant_domains:
                    target_domains = [
                        str(domain).strip()
                        for domain in relevant_domains
                        if str(domain).strip() in PROFILE_V24_DOMAIN_KEYS
                    ]
                else:
                    target_domains = inferred_domains

                merged_suggestions = copy.deepcopy(existing_suggestions)
                for domain in target_domains:
                    domain_payload = normalized_incoming.get(domain)
                    if not isinstance(domain_payload, dict):
                        continue
                    merged_suggestions[domain] = copy.deepcopy(domain_payload)
                    if domain not in updated_domains:
                        updated_domains.append(domain)

            profile["ai_suggestions"] = merged_suggestions
            profile["ai_suggestions_updated_at"] = now
            profile["updated_at"] = now
            profile["updated_by_name"] = actor_name

            summary = "AI 结构化提取完成"
            if updated_domains:
                summary = f"AI 结构化提取完成，更新域：{', '.join(updated_domains)}"
            self._append_profile_event(
                profile,
                event_type=normalized_trigger,
                source=source_text,
                summary=summary,
                affected_domains=updated_domains,
            )
            self._refresh_v27_card_views(profile)
            self._save_unlocked(items)

        return self._normalize_profile_for_output(profile)

    def _calculate_completeness_score(self, completeness: Dict[str, Any]) -> int:
        score = 0

        if bool(completeness.get("code_scan")):
            score += 30

        documents_normal = int(completeness.get("documents_normal") or 0)
        if documents_normal >= 11:
            score += 40
        elif documents_normal >= 6:
            score += 30
        elif documents_normal >= 1:
            score += 10

        if bool(completeness.get("esb")):
            score += 30

        return max(0, min(100, score))

    def mark_code_scan_ingested(
        self,
        system_name: str,
        system_id: Optional[str],
        job_id: str,
        result_path: str,
        actor: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        name = str(system_name or "").strip()
        if not name:
            raise ValueError("system_name不能为空")

        now = current_time_iso()
        actor_id = (actor or {}).get("id") or (actor or {}).get("username") or "unknown"
        actor_name = (actor or {}).get("displayName") or (actor or {}).get("username") or "unknown"
        normalized_system_id = str(system_id or "").strip()

        with self._lock():
            items = self._load_unlocked()
            profile = self._find_profile(items, name)
            if not profile:
                profile = {
                    "system_id": normalized_system_id,
                    "system_name": name,
                    "status": "draft",
                    LEGACY_FIELDS_KEY: {},
                    "evidence_refs": [],
                    LEGACY_PENDING_FIELDS_KEY: [],
                    "created_at": now,
                }
                items.append(profile)

            if normalized_system_id:
                profile["system_id"] = normalized_system_id
            elif not profile.get("system_id"):
                profile["system_id"] = ""

            completeness = profile.get("completeness") if isinstance(profile.get("completeness"), dict) else {}
            completeness = dict(completeness)
            completeness.setdefault("documents_normal", int(profile.get("document_count") or 0))
            completeness.setdefault("esb", bool(completeness.get("esb")))
            completeness["code_scan"] = True
            profile["completeness"] = completeness
            profile["document_count"] = int(completeness.get("documents_normal") or 0)
            profile["completeness_score"] = self._calculate_completeness_score(completeness)

            evidence_refs = profile.get("evidence_refs") if isinstance(profile.get("evidence_refs"), list) else []
            evidence_refs = list(evidence_refs)
            normalized_job_id = str(job_id or "").strip()
            already_exists = False
            if normalized_job_id:
                for ref in evidence_refs:
                    if not isinstance(ref, dict):
                        continue
                    if str(ref.get("source_type") or "") != "code_scan":
                        continue
                    if str(ref.get("source_id") or "") == normalized_job_id:
                        already_exists = True
                        break

            if normalized_job_id and (not already_exists):
                evidence_refs.append(
                    {
                        "source_type": "code_scan",
                        "source_id": normalized_job_id,
                        "source_path": str(result_path or ""),
                        "created_at": now,
                    }
                )
            profile["evidence_refs"] = evidence_refs

            profile["updated_by"] = actor_id
            profile["updated_by_name"] = actor_name
            profile["updated_at"] = now

            self._save_unlocked(items)

        return profile

    def mark_esb_ingested(
        self,
        system_name: str,
        system_id: Optional[str],
        import_id: str,
        source_file: str,
        actor: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        name = str(system_name or "").strip()
        if not name:
            raise ValueError("system_name不能为空")

        now = current_time_iso()
        actor_id = (actor or {}).get("id") or (actor or {}).get("username") or "unknown"
        actor_name = (actor or {}).get("displayName") or (actor or {}).get("username") or "unknown"
        normalized_system_id = str(system_id or "").strip()

        with self._lock():
            items = self._load_unlocked()
            profile = self._find_profile(items, name)
            if not profile:
                profile = {
                    "system_id": normalized_system_id,
                    "system_name": name,
                    "status": "draft",
                    LEGACY_FIELDS_KEY: {},
                    "evidence_refs": [],
                    LEGACY_PENDING_FIELDS_KEY: [],
                    "created_at": now,
                }
                items.append(profile)

            if normalized_system_id:
                profile["system_id"] = normalized_system_id
            elif not profile.get("system_id"):
                profile["system_id"] = ""

            completeness = profile.get("completeness") if isinstance(profile.get("completeness"), dict) else {}
            completeness = dict(completeness)
            completeness.setdefault("documents_normal", int(profile.get("document_count") or 0))
            completeness.setdefault("code_scan", bool(completeness.get("code_scan")))
            completeness["esb"] = True
            profile["completeness"] = completeness
            profile["document_count"] = int(completeness.get("documents_normal") or 0)
            profile["completeness_score"] = self._calculate_completeness_score(completeness)

            evidence_refs = profile.get("evidence_refs") if isinstance(profile.get("evidence_refs"), list) else []
            evidence_refs = list(evidence_refs)
            normalized_import_id = str(import_id or "").strip()
            already_exists = False
            if normalized_import_id:
                for ref in evidence_refs:
                    if not isinstance(ref, dict):
                        continue
                    if str(ref.get("source_type") or "") != "esb":
                        continue
                    if str(ref.get("source_id") or "") == normalized_import_id:
                        already_exists = True
                        break

            if normalized_import_id and (not already_exists):
                evidence_refs.append(
                    {
                        "source_type": "esb",
                        "source_id": normalized_import_id,
                        "source_file": str(source_file or ""),
                        "created_at": now,
                    }
                )
            profile["evidence_refs"] = evidence_refs

            profile["updated_by"] = actor_id
            profile["updated_by_name"] = actor_name
            profile["updated_at"] = now

            self._save_unlocked(items)

        return profile

    def mark_document_imported(
        self,
        system_name: str,
        system_id: Optional[str],
        import_id: str,
        source_file: str,
        level: str = "normal",
        actor: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        name = str(system_name or "").strip()
        if not name:
            raise ValueError("system_name不能为空")

        normalized_level = str(level or "normal").strip().lower() or "normal"
        now = current_time_iso()
        actor_id = (actor or {}).get("id") or (actor or {}).get("username") or "unknown"
        actor_name = (actor or {}).get("displayName") or (actor or {}).get("username") or "unknown"
        normalized_system_id = str(system_id or "").strip()

        with self._lock():
            items = self._load_unlocked()
            profile = self._find_profile(items, name)
            if not profile:
                profile = {
                    "system_id": normalized_system_id,
                    "system_name": name,
                    "status": "draft",
                    LEGACY_FIELDS_KEY: {},
                    "evidence_refs": [],
                    LEGACY_PENDING_FIELDS_KEY: [],
                    "created_at": now,
                }
                items.append(profile)

            if normalized_system_id:
                profile["system_id"] = normalized_system_id
            elif not profile.get("system_id"):
                profile["system_id"] = ""

            completeness = profile.get("completeness") if isinstance(profile.get("completeness"), dict) else {}
            completeness = dict(completeness)
            completeness.setdefault("code_scan", bool(completeness.get("code_scan")))
            completeness.setdefault("esb", bool(completeness.get("esb")))
            documents_normal = int(completeness.get("documents_normal") or profile.get("document_count") or 0)
            if normalized_level == "normal":
                documents_normal += 1
            completeness["documents_normal"] = max(0, documents_normal)
            profile["document_count"] = int(completeness.get("documents_normal") or 0)
            profile["completeness"] = completeness
            profile["completeness_score"] = self._calculate_completeness_score(completeness)

            evidence_refs = profile.get("evidence_refs") if isinstance(profile.get("evidence_refs"), list) else []
            evidence_refs = list(evidence_refs)
            normalized_import_id = str(import_id or "").strip()
            already_exists = False
            if normalized_import_id:
                for ref in evidence_refs:
                    if not isinstance(ref, dict):
                        continue
                    if str(ref.get("source_type") or "") != "knowledge_import":
                        continue
                    if str(ref.get("source_id") or "") == normalized_import_id:
                        already_exists = True
                        break

            if normalized_import_id and (not already_exists):
                evidence_refs.append(
                    {
                        "source_type": "knowledge_import",
                        "source_id": normalized_import_id,
                        "source_file": str(source_file or ""),
                        "level": normalized_level,
                        "created_at": now,
                    }
                )
            profile["evidence_refs"] = evidence_refs

            profile["updated_by"] = actor_id
            profile["updated_by_name"] = actor_name
            profile["updated_at"] = now

            self._save_unlocked(items)

        return profile

    def publish_profile(
        self,
        system_name: str,
        actor: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        name = str(system_name or "").strip()
        if not name:
            raise ValueError("system_name不能为空")

        now = current_time_iso()
        actor_id = (actor or {}).get("id") or (actor or {}).get("username") or "unknown"
        actor_name = (actor or {}).get("displayName") or (actor or {}).get("username") or "unknown"
        normalized_profile: Dict[str, Any]
        knowledge_index_status = "skipped"
        knowledge_index_error: Optional[str] = None

        with self._lock():
            items = self._load_unlocked()
            profile = self._find_profile(items, name)
            if not profile:
                raise ValueError("系统画像不存在")

            profile_snapshot = copy.deepcopy(profile)
            if getattr(settings, "ENABLE_V27_PROFILE_SCHEMA", False):
                profile_snapshot["profile_data"] = normalize_profile_data(profile_snapshot.get("profile_data"))
                profile_snapshot["field_sources"] = self._normalize_v27_metadata_map(profile_snapshot.get("field_sources"))
                profile_snapshot["ai_suggestions"] = self._normalize_v27_ai_suggestions(profile_snapshot.get("ai_suggestions"))
                self._refresh_v27_card_views(profile_snapshot)
                profile_snapshot.pop(LEGACY_FIELDS_KEY, None)
                profile_snapshot.pop(LEGACY_PENDING_FIELDS_KEY, None)
            else:
                fields = profile.get(LEGACY_FIELDS_KEY) if isinstance(profile.get(LEGACY_FIELDS_KEY), dict) else {}
                fields = self._normalize_fields_for_storage(fields)
                profile_snapshot[LEGACY_FIELDS_KEY] = fields
                pending_fields = self._calc_pending_fields(profile_snapshot)
                profile_snapshot[LEGACY_PENDING_FIELDS_KEY] = pending_fields
            profile_snapshot["status"] = "published"
            profile_snapshot["published_at"] = now
            profile_snapshot["updated_by"] = actor_id
            profile_snapshot["updated_by_name"] = actor_name
            profile_snapshot["updated_at"] = now

        with self._lock():
            items = self._load_unlocked()
            profile = self._find_profile(items, name)
            if not profile:
                raise ValueError("系统画像不存在")

            if getattr(settings, "ENABLE_V27_PROFILE_SCHEMA", False):
                profile["profile_data"] = normalize_profile_data(profile.get("profile_data"))
                profile["field_sources"] = self._normalize_v27_metadata_map(profile.get("field_sources"))
                self._refresh_v27_card_views(profile)
                profile.pop(LEGACY_FIELDS_KEY, None)
                profile.pop(LEGACY_PENDING_FIELDS_KEY, None)
            else:
                if isinstance(profile.get(LEGACY_FIELDS_KEY), dict):
                    profile[LEGACY_FIELDS_KEY] = self._normalize_fields_for_storage(profile.get(LEGACY_FIELDS_KEY) or {})
                pending_fields = self._calc_pending_fields(profile)
                profile[LEGACY_PENDING_FIELDS_KEY] = pending_fields
            profile["status"] = "published"
            profile["published_at"] = now
            profile["updated_by"] = actor_id
            profile["updated_by_name"] = actor_name
            profile["updated_at"] = now

            self._save_unlocked(items)
            normalized_profile = self._normalize_profile_for_output(profile)

        self._record_decision_output(
            profile=normalized_profile,
            system_name=name,
            decision_action="publish_profile",
            actor=actor,
            extra_payload={
                "published_at": now,
                "knowledge_index_status": knowledge_index_status,
                "knowledge_index_error": knowledge_index_error,
            },
        )
        return normalized_profile

    def _calc_pending_fields(self, profile: Dict[str, Any]) -> List[str]:
        fields = profile.get(LEGACY_FIELDS_KEY) if isinstance(profile.get(LEGACY_FIELDS_KEY), dict) else {}
        evidence_refs = profile.get("evidence_refs") if isinstance(profile.get("evidence_refs"), list) else []

        filled_fields = [key for key, value in fields.items() if self._has_value(value)]
        if not filled_fields:
            return []

        covered = set()
        for ref in evidence_refs:
            if not isinstance(ref, dict):
                continue
            field_name = str(ref.get("field") or "").strip()
            if field_name:
                covered.add(field_name)

        if not evidence_refs:
            return filled_fields

        # 若证据引用未指明字段，默认认为已覆盖
        if evidence_refs and not covered:
            return []

        return [field for field in filled_fields if field not in covered]

    def _collect_module_leaf_names(self, node: Dict[str, Any], *, limit: int = 20) -> List[str]:
        if limit <= 0 or (not isinstance(node, dict)):
            return []

        names: List[str] = []
        children = node.get("children") if isinstance(node.get("children"), list) else []

        if children:
            for child in children:
                if len(names) >= limit or (not isinstance(child, dict)):
                    continue
                child_name = str(child.get("module_name") or "").strip()
                nested_children = child.get("children") if isinstance(child.get("children"), list) else []
                if nested_children:
                    nested_names = self._collect_module_leaf_names(child, limit=limit - len(names))
                    if nested_names:
                        names.extend(nested_names)
                    elif child_name:
                        names.append(child_name)
                elif child_name:
                    names.append(child_name)
            return names[:limit]

        raw_functions = node.get("functions") if isinstance(node.get("functions"), list) else []
        for function_item in raw_functions:
            if len(names) >= limit:
                break
            if isinstance(function_item, dict):
                function_name = str(function_item.get("name") or "").strip()
            elif isinstance(function_item, str):
                function_name = function_item.strip()
            else:
                function_name = ""
            if function_name:
                names.append(function_name)
        return names[:limit]

    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _profile_data_has_meaningful_content(self, profile_data: Any) -> bool:
        normalized = normalize_profile_data(profile_data)
        for domain_key in V27_DOMAIN_KEYS:
            canonical = normalized.get(domain_key, {}).get("canonical", {})
            if has_non_empty_value(canonical):
                return True
        return False

    def _resolve_system_id_from_catalog(self, system_name: str) -> str:
        normalized_name = str(system_name or "").strip()
        if not normalized_name:
            return ""
        try:
            from backend.api import system_routes

            owner_info = system_routes.resolve_system_owner(system_name=normalized_name)
        except Exception:
            return ""
        return str(owner_info.get("system_id") or "").strip()

    def _resolve_system_name_from_catalog(self, system_id: str) -> str:
        normalized_system_id = str(system_id or "").strip()
        if not normalized_system_id:
            return ""
        try:
            from backend.api import system_routes

            owner_info = system_routes.resolve_system_owner(system_id=normalized_system_id)
        except Exception:
            return ""
        return str(owner_info.get("system_name") or "").strip()

    def _resolve_workspace_system_name(self, system_id: str, *, preferred_name: str = "") -> str:
        normalized_system_id = str(system_id or "").strip()
        normalized_preferred_name = str(preferred_name or "").strip()
        if normalized_preferred_name:
            return normalized_preferred_name
        if not normalized_system_id:
            return ""

        identity = self.repository.get_workspace_identity(system_id=normalized_system_id) or {}
        workspace_name = str(identity.get("system_name") or "").strip()
        if workspace_name:
            return workspace_name
        return self._resolve_system_name_from_catalog(normalized_system_id) or normalized_system_id

    def _get_latest_wiki_candidate_record(self, system_id: str) -> Optional[Dict[str, Any]]:
        normalized_system_id = str(system_id or "").strip()
        if not normalized_system_id:
            return None
        try:
            from backend.service.profile_artifact_service import get_profile_artifact_service

            items = get_profile_artifact_service().list_layer_records(
                layer="wiki",
                system_id=normalized_system_id,
            )
        except Exception:
            return None
        if not items:
            return None
        for item in items:
            category = str(item.get("category") or "").strip()
            if category in {"", "documents"}:
                return dict(item)
        return dict(items[0])

    def _normalize_wiki_candidate_map(self, value: Any) -> Dict[str, Dict[str, Any]]:
        raw_candidates = value if isinstance(value, dict) else {}
        normalized: Dict[str, Dict[str, Any]] = {}
        for raw_field_path, raw_payload in raw_candidates.items():
            field_path = resolve_canonical_field_path(str(raw_field_path or "").strip())
            if not field_path:
                continue
            if isinstance(raw_payload, dict):
                payload = dict(raw_payload)
            else:
                payload = {"value": raw_payload}
            candidate_value = payload.get("value")
            if not has_non_empty_value(candidate_value):
                continue
            payload["logical_field"] = get_logical_field_key(field_path)
            payload["canonical_field_path"] = field_path
            payload.setdefault("validation_status", "passed")
            payload.setdefault("validation_reason", "")
            payload.setdefault("schema_version", "logical_candidate_v1")
            if field_path not in normalized or str(raw_field_path or "").strip() == field_path:
                normalized[field_path] = payload
        return normalized

    def _normalize_projection_candidate_map(self, value: Any) -> Dict[str, Dict[str, Any]]:
        raw_candidates = value if isinstance(value, dict) else {}
        normalized: Dict[str, Dict[str, Any]] = {}
        for raw_field_path, raw_payload in raw_candidates.items():
            field_path = resolve_canonical_field_path(str(raw_field_path or "").strip())
            if not field_path or not isinstance(raw_payload, dict):
                continue
            selected_value = raw_payload.get("selected_value")
            if not has_non_empty_value(selected_value):
                continue
            candidate_items = copy.deepcopy(raw_payload.get("candidate_items")) if isinstance(raw_payload.get("candidate_items"), list) else []
            confidence = raw_payload.get("confidence")
            if confidence is None and candidate_items:
                confidences = [
                    self._safe_float(item.get("confidence"), default=1.0)
                    for item in candidate_items
                    if isinstance(item, dict)
                ]
                confidence = max(confidences) if confidences else 1.0
            normalized[field_path] = {
                "value": copy.deepcopy(selected_value),
                "confidence": confidence,
                "reason": raw_payload.get("selection_policy") or raw_payload.get("reason") or "",
                "candidate_items": candidate_items,
                "source_mode": raw_payload.get("source_mode"),
                "logical_field": get_logical_field_key(field_path),
                "canonical_field_path": field_path,
                "validation_status": raw_payload.get("validation_status") or "passed",
                "validation_reason": raw_payload.get("validation_reason") or "",
                "schema_version": raw_payload.get("schema_version") or "logical_candidate_v1",
            }
        return normalized

    def _priority_for_candidate_source(self, source_mode: str) -> int:
        return {
            "governance": 0,
            "system_catalog": 1,
            "manual": 2,
            "document_llm": 3,
            "code_scan": 3,
            "document": 4,
            "pm_document_ingest": 4,
            "candidate": 5,
        }.get(str(source_mode or "").strip(), 9)

    def _merge_candidate_values(self, values: List[Any]) -> Any:
        meaningful = [copy.deepcopy(value) for value in values if has_non_empty_value(value)]
        if not meaningful:
            return None
        first = meaningful[0]
        if isinstance(first, dict):
            keys: List[str] = []
            for value in meaningful:
                if not isinstance(value, dict):
                    continue
                for key in value.keys():
                    if key not in keys:
                        keys.append(key)
            merged: Dict[str, Any] = {}
            for key in keys:
                nested_values = [value.get(key) for value in meaningful if isinstance(value, dict) and has_non_empty_value(value.get(key))]
                if not nested_values:
                    continue
                merged[key] = self._merge_candidate_values(nested_values)
            return merged
        if isinstance(first, list):
            merged_items: List[Any] = []
            seen = set()
            for value in meaningful:
                if isinstance(value, list):
                    items = value
                else:
                    items = [value]
                for item in items:
                    if not has_non_empty_value(item):
                        continue
                    if isinstance(item, (dict, list)):
                        marker = json.dumps(item, ensure_ascii=False, sort_keys=True)
                    else:
                        marker = str(item).strip()
                    if not marker or marker in seen:
                        continue
                    seen.add(marker)
                    merged_items.append(copy.deepcopy(item))
            return merged_items

        texts: List[str] = []
        for value in meaningful:
            text = str(value or "").strip()
            if text and text not in texts:
                texts.append(text)
        if not texts:
            return None
        if len(texts) == 1:
            return texts[0]
        return "\n".join(texts)

    def _extract_candidate_items_from_record(self, record: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        payload = record.get("payload") if isinstance(record.get("payload"), dict) else {}
        category = str(record.get("category") or "").strip()
        source_mode = str(payload.get("source_mode") or "").strip()
        if not source_mode:
            if category == "authoritative":
                source_mode = str(payload.get("authority") or "authoritative").strip() or "authoritative"
            else:
                source_mode = "document"

        result: Dict[str, List[Dict[str, Any]]] = {}

        candidate_groups = [
            (
                self._normalize_wiki_candidate_map(
                    payload.get("field_candidates") if isinstance(payload.get("field_candidates"), dict) else payload.get("candidates")
                ),
                source_mode,
            )
        ]
        llm_candidates = payload.get("llm_candidates")
        if isinstance(llm_candidates, dict):
            candidate_groups.append((self._normalize_wiki_candidate_map(llm_candidates), "document_llm"))

        for normalized_candidates, group_source_mode in candidate_groups:
            for field_path, candidate in normalized_candidates.items():
                result.setdefault(field_path, []).append(
                    {
                        "candidate_artifact_id": str(record.get("artifact_id") or "").strip(),
                        "source_artifact_id": str(record.get("source_artifact_id") or "").strip() or None,
                        "source_mode": group_source_mode,
                        "category": category or "documents",
                        "doc_type": str(payload.get("doc_type") or "").strip() or None,
                        "file_name": str(payload.get("file_name") or "").strip() or None,
                        "value": copy.deepcopy(candidate.get("value")),
                        "confidence": candidate.get("confidence"),
                        "reason": str(candidate.get("reason") or "").strip(),
                        "source_anchors": copy.deepcopy(candidate.get("source_anchors")) if isinstance(candidate.get("source_anchors"), list) else [],
                        "logical_field": str(candidate.get("logical_field") or get_logical_field_key(field_path)).strip(),
                        "canonical_field_path": str(candidate.get("canonical_field_path") or field_path).strip() or field_path,
                        "validation_status": str(candidate.get("validation_status") or "passed").strip() or "passed",
                        "validation_reason": str(candidate.get("validation_reason") or "").strip(),
                        "schema_version": str(candidate.get("schema_version") or "logical_candidate_v1").strip() or "logical_candidate_v1",
                        "created_at": str(record.get("created_at") or "").strip(),
                    }
                )
        return result

    def _candidate_supersede_key(self, item: Dict[str, Any]) -> Optional[tuple]:
        source_mode = str(item.get("source_mode") or "").strip()
        if source_mode not in {"document", "document_llm", "pm_document_ingest"}:
            return None
        file_name = str(item.get("file_name") or "").strip().lower()
        doc_type = str(item.get("doc_type") or "").strip().lower()
        category = str(item.get("category") or "").strip().lower() or "documents"
        if file_name:
            return (category, source_mode, doc_type, file_name)
        source_artifact_id = str(item.get("source_artifact_id") or "").strip()
        if source_artifact_id:
            return (category, source_mode, doc_type, source_artifact_id)
        return None

    def _record_supersede_key(self, record: Dict[str, Any]) -> Optional[tuple]:
        payload = record.get("payload") if isinstance(record.get("payload"), dict) else {}
        category = str(record.get("category") or "").strip().lower() or "documents"
        source_mode = str(payload.get("source_mode") or "").strip()
        if not source_mode:
            if category == "authoritative":
                source_mode = str(payload.get("authority") or "authoritative").strip() or "authoritative"
            else:
                source_mode = "document"
        if source_mode not in {"document", "pm_document_ingest"}:
            return None
        doc_type = str(payload.get("doc_type") or "").strip().lower()
        file_name = str(payload.get("file_name") or "").strip().lower()
        if file_name:
            return (category, source_mode, doc_type, file_name)
        source_artifact_id = str(record.get("source_artifact_id") or "").strip()
        if source_artifact_id:
            return (category, source_mode, doc_type, source_artifact_id)
        return None

    def _merge_candidate_records(self, records: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        effective_records: List[Dict[str, Any]] = []
        superseded_record_keys = set()
        for record in sorted(records, key=lambda item: str(item.get("created_at") or ""), reverse=True):
            supersede_key = self._record_supersede_key(record)
            if supersede_key is not None:
                if supersede_key in superseded_record_keys:
                    continue
                superseded_record_keys.add(supersede_key)
            effective_records.append(record)

        merged_source_items: Dict[str, List[Dict[str, Any]]] = {}
        for record in effective_records:
            extracted = self._extract_candidate_items_from_record(record)
            for field_path, items in extracted.items():
                merged_source_items.setdefault(field_path, []).extend(items)

        merged_candidates: Dict[str, Dict[str, Any]] = {}
        for field_path, items in merged_source_items.items():
            if not items:
                continue
            deduped_latest_items: List[Dict[str, Any]] = []
            superseded_keys = set()
            for item in sorted(items, key=lambda candidate: str(candidate.get("created_at") or ""), reverse=True):
                supersede_key = self._candidate_supersede_key(item)
                if supersede_key is not None:
                    if supersede_key in superseded_keys:
                        continue
                    superseded_keys.add(supersede_key)
                deduped_latest_items.append(item)

            sorted_items = sorted(
                deduped_latest_items,
                key=lambda item: (
                    self._priority_for_candidate_source(str(item.get("source_mode") or "")),
                    str(item.get("created_at") or ""),
                ),
            )
            authoritative_items = [
                item
                for item in sorted_items
                if str(item.get("source_mode") or "").strip() in {"system_catalog", "governance"}
            ]
            governance_items = [
                item
                for item in sorted_items
                if str(item.get("source_mode") or "").strip() == "governance"
            ]
            if field_path in AUTHORITATIVE_ONLY_CANDIDATE_FIELDS:
                if not governance_items:
                    continue
                selected_value = self._merge_candidate_values([item.get("value") for item in governance_items])
                if not has_non_empty_value(selected_value):
                    continue
                merged_candidates[field_path] = {
                    "selected_value": selected_value,
                    "candidate_items": sorted_items,
                    "candidate_count": len(sorted_items),
                    "confidence": max((self._safe_float(item.get("confidence"), default=0.0) for item in governance_items), default=0.0),
                    "selection_policy": "governance_only",
                    "source_mode": "governance",
                    "logical_field": str((governance_items[0] if governance_items else {}).get("logical_field") or get_logical_field_key(field_path)).strip(),
                    "canonical_field_path": field_path,
                    "validation_status": "passed",
                    "validation_reason": "",
                    "schema_version": str((governance_items[0] if governance_items else {}).get("schema_version") or "logical_candidate_v1").strip() or "logical_candidate_v1",
                }
                continue
            llm_items = [
                item
                for item in sorted_items
                if str(item.get("source_mode") or "").strip() == "document_llm"
            ]
            prefer_llm = bool(llm_items) and all(
                not isinstance(item.get("value"), (dict, list))
                for item in llm_items
            )
            merge_base = authoritative_items or (llm_items if prefer_llm else []) or sorted_items
            selected_value = self._merge_candidate_values([item.get("value") for item in merge_base])
            if not has_non_empty_value(selected_value):
                continue
            source_mode = str((merge_base[0] if merge_base else {}).get("source_mode") or "candidate").strip() or "candidate"
            merged_candidates[field_path] = {
                "selected_value": selected_value,
                "candidate_items": sorted_items,
                "candidate_count": len(sorted_items),
                "confidence": max((self._safe_float(item.get("confidence"), default=0.0) for item in sorted_items), default=0.0),
                "selection_policy": "authoritative_preferred" if authoritative_items else "merge_all",
                "source_mode": source_mode,
                "logical_field": str((merge_base[0] if merge_base else {}).get("logical_field") or get_logical_field_key(field_path)).strip(),
                "canonical_field_path": field_path,
                "validation_status": "passed",
                "validation_reason": "",
                "schema_version": str((merge_base[0] if merge_base else {}).get("schema_version") or "logical_candidate_v1").strip() or "logical_candidate_v1",
            }
        return merged_candidates

    def _load_latest_projection_bundle(self, system_id: str) -> Dict[str, Any]:
        normalized_system_id = str(system_id or "").strip()
        if not normalized_system_id:
            return {}
        workspace_path = self.repository.get_workspace_path(system_id=normalized_system_id)
        if not workspace_path:
            return {}

        latest_dir = os.path.join(workspace_path, "candidate", "latest")
        if not os.path.isdir(latest_dir):
            return {}

        return {
            "system_projection": self._read_json_file(os.path.join(latest_dir, "system_projection.json")) or {},
            "merged_candidates": self._read_json_file(os.path.join(latest_dir, "merged_candidates.json")) or {},
            "card_render": self._read_json_file(os.path.join(latest_dir, "card_render.json")) or {},
        }

    def _load_projection_candidate_map(self, system_id: str) -> Dict[str, Dict[str, Any]]:
        projection_bundle = self._load_latest_projection_bundle(system_id)
        merged_candidates = projection_bundle.get("merged_candidates") if isinstance(projection_bundle.get("merged_candidates"), dict) else {}
        return self._normalize_projection_candidate_map(merged_candidates)

    def _get_latest_projection_record(self, system_id: str) -> Optional[Dict[str, Any]]:
        normalized_system_id = str(system_id or "").strip()
        if not normalized_system_id:
            return None
        try:
            items = get_profile_artifact_service().list_candidate_records(
                system_id=normalized_system_id,
                category="projections",
            )
        except Exception:
            return None
        if not items:
            return None
        return dict(items[0])

    def refresh_candidate_projection(
        self,
        system_name: str,
        *,
        system_id: str,
        actor: Optional[Dict[str, Any]] = None,
        sync_ai_suggestions: bool = True,
    ) -> Optional[Dict[str, Any]]:
        normalized_system_id = str(system_id or "").strip()
        normalized_system_name = self._resolve_workspace_system_name(
            normalized_system_id,
            preferred_name=system_name,
        )
        if not normalized_system_id:
            return None
        if normalized_system_name:
            self.ensure_profile(normalized_system_name, system_id=normalized_system_id, actor=actor)

        candidate_records = get_profile_artifact_service().list_candidate_records(
            system_id=normalized_system_id,
        )
        candidate_records = [
            item
            for item in candidate_records
            if str(item.get("category") or "").strip() in {"documents", "authoritative"}
        ]
        merged_candidates = self._merge_candidate_records(candidate_records)

        projection_candidate_map = self._normalize_projection_candidate_map(merged_candidates)
        candidate_profile_data = build_empty_profile_data()
        for field_path, candidate in projection_candidate_map.items():
            try:
                candidate_profile_data = set_field_value(candidate_profile_data, field_path, candidate.get("value"))
            except ValueError:
                continue

        ignored_map: Dict[str, Any] = {}
        with self._lock():
            items = self._load_unlocked()
            profile = self._find_profile(items, normalized_system_name)
            if profile:
                ignored_map = self._normalize_ai_suggestion_ignored_for_storage(profile.get("ai_suggestion_ignored"))
                if sync_ai_suggestions:
                    profile["ai_suggestions"] = copy.deepcopy(projection_candidate_map)
                self._refresh_v27_card_views(profile)
                profile["updated_at"] = str(profile.get("updated_at") or current_time_iso())
                self._save_unlocked(items)

        card_render = build_card_candidates(
            projection_candidate_map,
            ignored_map=ignored_map,
        )
        projection_payload = {
            "projection_type": "system_projection",
            "system_id": normalized_system_id,
            "system_name": normalized_system_name,
            "source_record_ids": [str(item.get("artifact_id") or "").strip() for item in candidate_records],
            "merged_candidates": merged_candidates,
            "card_render": card_render,
        }
        return get_profile_artifact_service().append_candidate_record(
            system_id=normalized_system_id,
            category="projections",
            payload=projection_payload,
            operator_id=str((actor or {}).get("username") or (actor or {}).get("id") or "system"),
            source_artifact_id=str(candidate_records[0].get("artifact_id") or "").strip() if candidate_records else None,
            latest_payloads={
                "system_projection.json": projection_payload,
                "merged_candidates.json": merged_candidates,
                "card_render.json": card_render,
                "candidate_profile.json": projection_payload,
            },
        )

    def record_authoritative_candidate(
        self,
        system_name: str,
        *,
        system_id: str,
        authority: str,
        field_candidates: Dict[str, Any],
        actor: Optional[Dict[str, Any]] = None,
        source_artifact_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        normalized_system_id = str(system_id or "").strip()
        normalized_system_name = str(system_name or "").strip()
        if not normalized_system_id or not field_candidates:
            return None

        payload = {
            "candidate_type": "authoritative_candidate",
            "system_id": normalized_system_id,
            "system_name": normalized_system_name,
            "authority": str(authority or "").strip() or "authoritative",
            "source_mode": str(authority or "").strip() or "authoritative",
            "field_candidates": copy.deepcopy(field_candidates),
        }
        if isinstance(metadata, dict):
            payload["metadata"] = copy.deepcopy(metadata)

        return get_profile_artifact_service().append_candidate_record(
            system_id=normalized_system_id,
            category="authoritative",
            payload=payload,
            operator_id=str((actor or {}).get("username") or (actor or {}).get("id") or "system"),
            source_artifact_id=source_artifact_id,
            metadata=metadata,
        )

    def _read_json_file(self, path: str) -> Any:
        normalized_path = str(path or "").strip()
        if not normalized_path or not os.path.exists(normalized_path):
            return None
        try:
            with open(normalized_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.debug("读取JSON文件失败 path=%s error=%s", normalized_path, exc)
            return None

    def _load_latest_candidate_bundle(self, system_id: str) -> Dict[str, Any]:
        normalized_system_id = str(system_id or "").strip()
        if not normalized_system_id:
            return {}
        bundle = self._load_latest_projection_bundle(normalized_system_id)
        latest_documents = []
        try:
            latest_documents = get_profile_artifact_service().list_candidate_records(
                system_id=normalized_system_id,
                category="documents",
            )
        except Exception:
            latest_documents = []
        if latest_documents:
            latest_document = latest_documents[0]
            base_dir = os.path.dirname(os.path.join(get_profile_artifact_service().root_dir, str(latest_document.get("path") or "").strip()))
            for file_name in ("source_manifest.json", "profile_projection.json", "dossier.json", "quality_report.json", "review_queue.json"):
                bundle[file_name[:-5]] = self._read_json_file(os.path.join(base_dir, file_name))
        return bundle

    def _build_context_card_list(self, profile: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized_profile = profile if isinstance(profile, dict) else {}
        profile_cards = normalized_profile.get("profile_cards") if isinstance(normalized_profile.get("profile_cards"), dict) else {}
        candidate_cards = normalized_profile.get("card_candidates") if isinstance(normalized_profile.get("card_candidates"), dict) else {}

        cards: List[Dict[str, Any]] = []
        for definition in PROFILE_CARD_DEFINITIONS:
            card_key = str(definition.get("card_key") or "").strip()
            current_card = profile_cards.get(card_key) if isinstance(profile_cards.get(card_key), dict) else {}
            candidate_card = candidate_cards.get(card_key) if isinstance(candidate_cards.get(card_key), dict) else {}
            cards.append(
                {
                    "card_key": card_key,
                    "domain_key": definition.get("domain_key"),
                    "domain_title": DOMAIN_TITLES.get(definition.get("domain_key"), definition.get("domain_key")),
                    "title": definition.get("title"),
                    "has_content": has_non_empty_value(current_card.get("content")) if isinstance(current_card, dict) else False,
                    "has_candidate": has_non_empty_value(candidate_card.get("content")) if isinstance(candidate_card, dict) else False,
                    "source_mode": current_card.get("source_mode") if isinstance(current_card, dict) else "none",
                    "source_summary": current_card.get("source_summary") if isinstance(current_card, dict) else "暂无来源",
                    "summary": copy.deepcopy(current_card.get("summary")) if isinstance(current_card, dict) else {},
                    "candidate_summary": copy.deepcopy(candidate_card.get("summary")) if isinstance(candidate_card, dict) else {},
                    "editable": bool(current_card.get("editable", True)) if isinstance(current_card, dict) else True,
                }
            )
        return cards

    def _build_document_context(self, profile: Optional[Dict[str, Any]], candidate_bundle: Dict[str, Any], top_k: int) -> List[Dict[str, Any]]:
        normalized_profile = profile if isinstance(profile, dict) else {}
        normalized_system_id = str(normalized_profile.get("system_id") or "").strip()
        documents: List[Dict[str, Any]] = []

        try:
            candidate_records = get_profile_artifact_service().list_candidate_records(
                system_id=normalized_system_id,
                category="documents",
            )
        except Exception:
            candidate_records = []

        for record in candidate_records:
            payload = record.get("payload") if isinstance(record.get("payload"), dict) else {}
            documents.append(
                {
                    "source_type": "document_candidate",
                    "source_id": str(record.get("artifact_id") or "").strip(),
                    "source_file": str(payload.get("file_name") or "").strip(),
                    "doc_type": str(payload.get("doc_type") or "").strip(),
                    "source_path": str(payload.get("raw_artifact_id") or "").strip(),
                    "chunk_count": int(payload.get("chunk_count") or 0),
                    "created_at": str(record.get("created_at") or "").strip(),
                }
            )
        return documents[: max(int(top_k or 0), 0)]

    def _build_code_scan_context(self, profile: Optional[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
        normalized_profile = profile if isinstance(profile, dict) else {}
        evidence_refs = normalized_profile.get("evidence_refs") if isinstance(normalized_profile.get("evidence_refs"), list) else []
        scan_refs = [
            ref
            for ref in evidence_refs
            if isinstance(ref, dict) and str(ref.get("source_type") or "").strip() == "code_scan"
        ]
        scan_refs.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
        if not scan_refs:
            return []

        latest_ref = scan_refs[0]
        payload = self._read_json_file(str(latest_ref.get("source_path") or "").strip())
        items = payload.get("items") if isinstance(payload, dict) and isinstance(payload.get("items"), list) else []

        capabilities: List[Dict[str, Any]] = []
        for item in items[: max(int(top_k or 0), 0)]:
            if not isinstance(item, dict):
                continue
            capabilities.append(
                {
                    "entry_type": str(item.get("entry_type") or "").strip(),
                    "entry_id": str(item.get("entry_id") or "").strip(),
                    "summary": str(item.get("summary") or "").strip(),
                    "location": copy.deepcopy(item.get("location")) if isinstance(item.get("location"), dict) else {},
                    "keywords": copy.deepcopy(item.get("keywords")) if isinstance(item.get("keywords"), list) else [],
                    "related_calls": copy.deepcopy(item.get("related_calls")) if isinstance(item.get("related_calls"), list) else [],
                }
            )
        return capabilities

    def _build_esb_context(
        self,
        *,
        system_name: str,
        system_id: str,
        query: str,
        top_k: int,
    ) -> List[Dict[str, Any]]:
        try:
            from backend.service.esb_service import get_esb_service

            esb_query = str(query or "").strip() or str(system_name or "").strip()
            if not esb_query:
                return []
            return get_esb_service().search_esb(
                query=esb_query,
                system_id=system_id or None,
                system_name=system_name or None,
                top_k=top_k,
                similarity_threshold=0.0,
            )
        except Exception as exc:
            logger.debug("构建ESB上下文失败 system=%s error=%s", system_name, exc)
            return []

    def build_context_bundle(
        self,
        system_name: str,
        *,
        query: str = "",
        top_k: int = 20,
    ) -> Dict[str, Any]:
        normalized_name = str(system_name or "").strip()
        safe_top_k = max(1, min(int(top_k or 20), 50))
        if not normalized_name:
            return {
                "system_name": "",
                "system_id": "",
                "profile_text": "",
                "context_source": "none",
                "profile_cards": [],
                "candidate_cards": [],
                "documents": [],
                "capabilities": [],
                "integrations": [],
                "quality_report": {},
                "review_queue": [],
                "completeness_score": 0,
                "degraded": False,
            }

        profile = self.get_profile(normalized_name) or {}
        estimation_context = self.build_estimation_context(normalized_name)
        resolved_system_id = (
            str(estimation_context.get("system_id") or "").strip()
            or str(profile.get("system_id") or "").strip()
            or self._resolve_system_id_from_catalog(normalized_name)
        )
        candidate_bundle = self._load_latest_candidate_bundle(resolved_system_id)
        profile_cards = self._build_context_card_list(profile)
        candidate_cards = [
            item
            for item in profile_cards
            if bool(item.get("has_candidate"))
        ]
        documents = self._build_document_context(profile, candidate_bundle, safe_top_k)
        capabilities = self._build_code_scan_context(profile, safe_top_k)
        integrations = self._build_esb_context(
            system_name=normalized_name,
            system_id=resolved_system_id,
            query=query,
            top_k=safe_top_k,
        )
        completeness_score = int(
            profile.get("completeness_score")
            if isinstance(profile, dict) and profile.get("completeness_score") is not None
            else self._calculate_completeness_score(
                profile.get("completeness") if isinstance(profile.get("completeness"), dict) else {}
            )
        )

        return {
            "system_name": normalized_name,
            "system_id": resolved_system_id,
            "profile_text": str(estimation_context.get("text") or "").strip(),
            "context_source": str(estimation_context.get("context_source") or "none").strip() or "none",
            "profile_cards": profile_cards,
            "candidate_cards": candidate_cards,
            "documents": documents,
            "capabilities": capabilities,
            "integrations": integrations,
            "quality_report": candidate_bundle.get("quality_report") if isinstance(candidate_bundle.get("quality_report"), dict) else {},
            "review_queue": candidate_bundle.get("review_queue") if isinstance(candidate_bundle.get("review_queue"), list) else [],
            "completeness_score": completeness_score,
            "degraded": False,
        }

    def _tokenize_relevance_query(self, text: str) -> List[str]:
        normalized = str(text or "").lower()
        if not normalized:
            return []
        tokens = [
            token.strip()
            for token in re.split(r"[^0-9a-zA-Z\u4e00-\u9fa5]+", normalized)
            if len(token.strip()) >= 2
        ]
        cjk_segments = re.findall(r"[\u4e00-\u9fa5]{2,}", normalized)
        for segment in cjk_segments:
            if len(segment) <= 4:
                tokens.append(segment)
                continue
            max_size = min(len(segment), 4)
            for size in range(2, max_size + 1):
                for index in range(0, len(segment) - size + 1):
                    tokens.append(segment[index : index + size])
        if len(normalized) <= 24 and normalized not in tokens:
            tokens.insert(0, normalized)
        ordered: List[str] = []
        for token in tokens:
            if token not in ordered:
                ordered.append(token)
        return ordered[:24]

    def search_relevant_profile_contexts(self, query_text: str, *, limit: int = 8) -> List[Dict[str, Any]]:
        normalized_query = str(query_text or "").strip()
        safe_limit = max(1, min(int(limit or 8), 20))
        profiles = self.list_profiles()
        if not profiles:
            return []

        tokens = self._tokenize_relevance_query(normalized_query)
        query_lower = normalized_query.lower()
        scored: List[Dict[str, Any]] = []
        for profile in profiles:
            if not isinstance(profile, dict):
                continue
            system_name = str(profile.get("system_name") or "").strip()
            if not system_name:
                continue
            profile_cards = self._build_context_card_list(profile)
            profile_text = ""
            context_source = "none"
            if getattr(settings, "ENABLE_V27_PROFILE_SCHEMA", False):
                profile_data = normalize_profile_data(profile.get("profile_data"))
                if self._profile_data_has_meaningful_content(profile_data):
                    profile_text = self._build_profile_text(
                        {
                            "system_name": system_name,
                            "profile_data": profile_data,
                        }
                    ).strip()
                    context_source = "canonical"
            else:
                if self._has_value((profile.get(LEGACY_FIELDS_KEY) or {})):
                    profile_text = self._build_profile_text(profile).strip()
                    context_source = "canonical"
            haystack = " ".join(
                [
                    system_name,
                    profile_text,
                    json.dumps(profile_cards, ensure_ascii=False),
                ]
            ).lower()

            score = 0.0
            if system_name.lower() in query_lower:
                score += 10.0
            for token in tokens:
                if token and token in haystack:
                    score += 1.5
            score += float(profile.get("completeness_score") or 0) / 100.0
            if profile.get("status") == "published":
                score += 0.5
            if score <= 0:
                continue

            scored.append(
                {
                    "system_name": system_name,
                    "system_id": str(profile.get("system_id") or "").strip(),
                    "score": round(score, 4),
                    "profile_text": profile_text,
                    "profile_cards": copy.deepcopy(profile_cards),
                    "context_source": context_source,
                    "completeness_score": int(profile.get("completeness_score") or 0),
                }
            )

        scored.sort(
            key=lambda item: (
                -float(item.get("score") or 0.0),
                -int(item.get("completeness_score") or 0),
                str(item.get("system_name") or ""),
            )
        )
        return scored[:safe_limit]

    def build_estimation_context(self, system_name: str) -> Dict[str, Any]:
        normalized_name = str(system_name or "").strip()
        result = {
            "system_name": normalized_name,
            "system_id": "",
            "text": "",
            "profile_context_used": False,
            "context_source": "none",
        }
        if not normalized_name:
            return result

        profile = self.get_profile(normalized_name) or {}
        system_id = str(profile.get("system_id") or "").strip()
        if not system_id:
            system_id = self._resolve_system_id_from_catalog(normalized_name)
        result["system_id"] = system_id

        if not getattr(settings, "ENABLE_V27_PROFILE_SCHEMA", False):
            if profile and self._has_value(profile.get(LEGACY_FIELDS_KEY)):
                result["text"] = self._build_profile_text(profile)
                result["profile_context_used"] = True
                result["context_source"] = "canonical"
            return result

        canonical_profile_data = normalize_profile_data((profile or {}).get("profile_data"))
        merged_profile_data = normalize_profile_data(canonical_profile_data)
        context_sources: List[str] = []
        if self._profile_data_has_meaningful_content(canonical_profile_data):
            context_sources.append("canonical")

        projection_used = False
        projection_candidates = self._load_projection_candidate_map(system_id)
        for field_path, candidate in projection_candidates.items():
            confidence = self._safe_float(candidate.get("confidence"), default=0.0)
            if confidence < 0.6:
                continue
            if has_non_empty_value(get_field_value(merged_profile_data, field_path)):
                continue
            try:
                merged_profile_data = set_field_value(merged_profile_data, field_path, candidate.get("value"))
            except ValueError:
                continue
            projection_used = True

        if projection_used:
            context_sources.append("projection_candidate")
        elif not projection_candidates:
            latest_wiki = self._get_latest_wiki_candidate_record(system_id)
            wiki_payload = latest_wiki.get("payload") if isinstance(latest_wiki, dict) else {}
            wiki_candidates = self._normalize_wiki_candidate_map(
                wiki_payload.get("candidates") if isinstance(wiki_payload, dict) else {}
            )
            wiki_used = False
            for field_path, candidate in wiki_candidates.items():
                confidence = self._safe_float(candidate.get("confidence"), default=0.0)
                if confidence < 0.6:
                    continue
                if has_non_empty_value(get_field_value(merged_profile_data, field_path)):
                    continue
                try:
                    merged_profile_data = set_field_value(merged_profile_data, field_path, candidate.get("value"))
                except ValueError:
                    continue
                wiki_used = True
            if wiki_used:
                context_sources.append("wiki_candidate")

        if not context_sources or not self._profile_data_has_meaningful_content(merged_profile_data):
            return result

        result["text"] = self._build_profile_text(
            {
                "system_name": normalized_name,
                "profile_data": merged_profile_data,
            }
        )
        result["profile_context_used"] = True
        result["context_source"] = "+".join(context_sources)
        return result

    def _build_profile_text(self, profile: Dict[str, Any]) -> str:
        if getattr(settings, "ENABLE_V27_PROFILE_SCHEMA", False):
            profile_data = normalize_profile_data(profile.get("profile_data"))
            positioning = profile_data["system_positioning"]["canonical"]
            business = profile_data["business_capabilities"]["canonical"]
            integration = profile_data["integration_interfaces"]["canonical"]
            technical = profile_data["technical_architecture"]["canonical"]
            constraints = profile_data["constraints_risks"]["canonical"]

            def _join_values(items: Any, key_candidates: Optional[List[str]] = None) -> str:
                if not isinstance(items, list):
                    return ""
                result: List[str] = []
                for item in items:
                    if isinstance(item, dict):
                        key_candidates_local = key_candidates or ["service_name", "description", "name", "peer_system"]
                        value = ""
                        for key in key_candidates_local:
                            value = str(item.get(key) or "").strip()
                            if value:
                                break
                    else:
                        value = str(item or "").strip()
                    if value:
                        result.append(value)
                return "、".join(result[:20])

            return (
                f"系统名称:{profile.get('system_name','')} | "
                f"系统类型:{positioning.get('system_type', '')} | "
                f"服务定位:{positioning.get('core_responsibility', '')} | "
                f"功能模块:{_join_values(business.get('functional_modules'), ['name', 'description'])} | "
                f"提供服务:{_join_values(integration.get('provided_services'))} | "
                f"依赖服务:{_join_values(integration.get('consumed_services'))} | "
                f"技术架构:{technical.get('architecture_style', '')} | "
                f"风险事项:{_join_values(constraints.get('risk_items'), ['name', 'impact'])}"
            )

        fields = profile.get(LEGACY_FIELDS_KEY) if isinstance(profile.get(LEGACY_FIELDS_KEY), dict) else {}
        module_tree = self._normalize_capability_tree(fields.get(LEGACY_MODULE_TREE_KEY), strict=False)
        module_segments: List[str] = []
        for module_item in module_tree[:20]:
            module_name = str(module_item.get("module_name") or "").strip()
            function_names = self._collect_module_leaf_names(module_item, limit=20)
            if module_name and function_names:
                module_segments.append(f"{module_name}({ '、'.join(function_names[:20]) })")
            elif module_name:
                module_segments.append(module_name)
        module_text = "；".join(module_segments)
        return (
            f"系统名称:{profile.get('system_name','')} | "
            f"系统定位与边界:{fields.get(LEGACY_SYSTEM_SCOPE_KEY,'')} | "
            f"模块结构:{module_text} | "
            f"主要集成点:{fields.get(LEGACY_INTERFACE_KEY,'')} | "
            f"关键约束:{fields.get(LEGACY_CONSTRAINT_KEY,'')}"
        )

    def has_published_profile(self, system_name: str) -> bool:
        profile = self.get_profile(system_name)
        return bool(profile and profile.get("status") == "published")

    def get_minimal_profile_flags(self, system_name: str) -> Dict[str, Any]:
        profile = self.get_profile(system_name) or {}
        if getattr(settings, "ENABLE_V27_PROFILE_SCHEMA", False):
            profile_data = normalize_profile_data(profile.get("profile_data"))
            positioning = profile_data["system_positioning"]["canonical"]
            business = profile_data["business_capabilities"]["canonical"]
            missing = []
            if not self._has_value(positioning.get("core_responsibility")):
                missing.append("system_positioning.canonical.core_responsibility")
            if not self._has_value(business.get("functional_modules")):
                missing.append("business_capabilities.canonical.functional_modules")
        else:
            fields = profile.get(LEGACY_FIELDS_KEY) if isinstance(profile.get(LEGACY_FIELDS_KEY), dict) else {}
            minimal_keys = [LEGACY_SYSTEM_SCOPE_KEY, LEGACY_MODULE_TREE_KEY]
            missing = [key for key in minimal_keys if not self._has_value(fields.get(key))]
        return {
            "has_profile": bool(profile),
            "is_published": profile.get("status") == "published",
            "missing_minimal_fields": missing,
        }

    def _has_value(self, value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, (list, tuple, set)):
            return any(str(item).strip() for item in value)
        return bool(str(value).strip())


_system_profile_service = None


def get_system_profile_service() -> SystemProfileService:
    global _system_profile_service
    expected_path = resolve_system_profile_root()
    if (
        _system_profile_service is None
        or os.path.realpath(_system_profile_service.store_path) != os.path.realpath(expected_path)
    ):
        _system_profile_service = SystemProfileService(store_path=expected_path)
    return _system_profile_service
