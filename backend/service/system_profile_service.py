"""
系统画像服务（B层）
维护系统画像的草稿/发布态与证据引用。
"""
from __future__ import annotations

import copy
import json
import logging
import os
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

try:
    import fcntl
    FCNTL_AVAILABLE = True
except ImportError:
    FCNTL_AVAILABLE = False

from backend.config.config import settings

logger = logging.getLogger(__name__)

PROFILE_FIELD_KEYS = (
    "system_scope",
    "module_structure",
    "integration_points",
    "key_constraints",
)

PROFILE_TEXT_FIELD_KEYS = {
    "system_scope",
    "integration_points",
    "key_constraints",
}

PROFILE_V24_DOMAIN_KEYS = (
    "system_positioning",
    "business_capabilities",
    "integration_interfaces",
    "technical_architecture",
    "constraints_risks",
)

PROFILE_V24_TO_LEGACY_FIELD = {
    ("system_positioning", "system_description"): "system_scope",
    ("business_capabilities", "module_structure"): "module_structure",
    ("integration_interfaces", "integration_points"): "integration_points",
    ("constraints_risks", "key_constraints"): "key_constraints",
}


class SystemProfileService:
    def __init__(self, store_path: Optional[str] = None) -> None:
        self.store_path = store_path or os.path.join(settings.REPORT_DIR, "system_profiles.json")
        self.lock_path = f"{self.store_path}.lock"
        self.import_history_store_path = os.path.join(settings.REPORT_DIR, "import_history.json")
        self.extraction_task_store_path = os.path.join(settings.REPORT_DIR, "extraction_tasks.json")
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
        if not os.path.exists(self.store_path):
            return []
        try:
            with open(self.store_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception as exc:
            logger.warning(f"读取系统画像失败: {exc}")
            return []

    def _save_unlocked(self, items: List[Dict[str, Any]]) -> None:
        os.makedirs(os.path.dirname(self.store_path) or ".", exist_ok=True)
        tmp_path = f"{self.store_path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self.store_path)

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

    def _find_profile(self, items: List[Dict[str, Any]], system_name: str) -> Optional[Dict[str, Any]]:
        for item in items:
            if isinstance(item, dict) and item.get("system_name") == system_name:
                return item
        return None

    def _normalize_module_node(
        self,
        node: Any,
        *,
        strict: bool,
        depth: int,
        max_depth: int,
    ) -> tuple[Optional[Dict[str, Any]], bool]:
        if not isinstance(node, dict):
            if strict:
                raise ValueError("invalid_module_structure")
            return None, False

        module_name = str(node.get("module_name") or "").strip()
        if not module_name:
            if strict:
                raise ValueError("invalid_module_structure")
            return None, False

        description = "" if node.get("description") is None else str(node.get("description")).strip()
        normalized_node: Dict[str, Any] = {
            "module_name": module_name,
            "description": description,
            "children": [],
        }
        depth_truncated = False
        normalized_children: List[Dict[str, Any]] = []

        raw_children = node.get("children")
        if raw_children is not None:
            if not isinstance(raw_children, list):
                if strict:
                    raise ValueError("invalid_module_structure")
            elif depth >= max_depth:
                if raw_children:
                    depth_truncated = True
            else:
                for child_item in raw_children:
                    child_node, child_truncated = self._normalize_module_node(
                        child_item,
                        strict=strict,
                        depth=depth + 1,
                        max_depth=max_depth,
                    )
                    if child_node is not None:
                        normalized_children.append(child_node)
                    depth_truncated = depth_truncated or child_truncated

        raw_functions = node.get("functions")
        if raw_functions is not None:
            if not isinstance(raw_functions, list):
                if strict:
                    raise ValueError("invalid_module_structure")
            elif depth >= max_depth:
                if raw_functions:
                    depth_truncated = True
            else:
                seen_child_names = {
                    str(child.get("module_name") or "").strip()
                    for child in normalized_children
                    if isinstance(child, dict)
                }
                for function_item in raw_functions:
                    if isinstance(function_item, dict):
                        function_name = str(function_item.get("name") or "").strip()
                        function_desc = "" if function_item.get("desc") is None else str(function_item.get("desc")).strip()
                    elif isinstance(function_item, str):
                        function_name = function_item.strip()
                        function_desc = ""
                    else:
                        if strict:
                            raise ValueError("invalid_module_structure")
                        continue

                    if not function_name:
                        if strict:
                            raise ValueError("invalid_module_structure")
                        continue
                    if function_name in seen_child_names:
                        continue

                    normalized_children.append(
                        {
                            "module_name": function_name,
                            "description": function_desc,
                            "children": [],
                        }
                    )
                    seen_child_names.add(function_name)

        normalized_node["children"] = normalized_children
        return normalized_node, depth_truncated

    def _normalize_module_structure(self, value: Any, *, strict: bool) -> List[Dict[str, Any]]:
        if value is None:
            return []

        parsed_value = value
        if isinstance(parsed_value, str):
            text = parsed_value.strip()
            if not text:
                return []
            try:
                parsed_value = json.loads(text)
            except Exception:
                if strict:
                    raise ValueError("invalid_module_structure")
                return []

        if not isinstance(parsed_value, list):
            if strict:
                raise ValueError("invalid_module_structure")
            return []

        normalized_modules: List[Dict[str, Any]] = []
        now = datetime.now().isoformat()
        max_depth = 3
        has_depth_truncated = False

        for module_item in parsed_value:
            normalized_module, depth_truncated = self._normalize_module_node(
                module_item,
                strict=strict,
                depth=1,
                max_depth=max_depth,
            )
            if normalized_module is None:
                continue
            normalized_module["last_updated"] = str(module_item.get("last_updated") or "").strip() or now
            normalized_modules.append(normalized_module)
            has_depth_truncated = has_depth_truncated or depth_truncated

        if has_depth_truncated:
            logger.warning(
                "module_structure depth exceeds limit(%s), extra levels were truncated",
                max_depth,
            )

        return normalized_modules

    def _normalize_fields_for_storage(self, fields: Dict[str, Any]) -> Dict[str, Any]:
        normalized: Dict[str, Any] = {}
        raw_fields = fields if isinstance(fields, dict) else {}

        for key in PROFILE_TEXT_FIELD_KEYS:
            if key in raw_fields:
                value = raw_fields.get(key)
                normalized[key] = "" if value is None else str(value).strip()

        if "module_structure" in raw_fields:
            normalized["module_structure"] = self._normalize_module_structure(raw_fields.get("module_structure"), strict=True)

        return normalized

    def _normalize_fields_for_output(self, fields: Dict[str, Any]) -> Dict[str, Any]:
        raw_fields = fields if isinstance(fields, dict) else {}

        return {
            "system_scope": "" if raw_fields.get("system_scope") is None else str(raw_fields.get("system_scope")).strip(),
            "module_structure": self._normalize_module_structure(raw_fields.get("module_structure"), strict=False),
            "integration_points": ""
            if raw_fields.get("integration_points") is None
            else str(raw_fields.get("integration_points")).strip(),
            "key_constraints": ""
            if raw_fields.get("key_constraints") is None
            else str(raw_fields.get("key_constraints")).strip(),
        }

    def _normalize_ai_suggestion_ignored_for_storage(self, value: Any) -> Dict[str, Any]:
        raw_ignored = value if isinstance(value, dict) else {}
        normalized: Dict[str, Any] = {}
        for raw_key, raw_value in raw_ignored.items():
            field_path = str(raw_key or "").strip()
            if not field_path or "." not in field_path:
                continue
            domain_key, sub_field = field_path.split(".", 1)
            domain_key = domain_key.strip()
            sub_field = sub_field.strip()
            if not domain_key or not sub_field:
                continue
            normalized[f"{domain_key}.{sub_field}"] = copy.deepcopy(raw_value)
        return normalized

    def _normalize_profile_for_output(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(profile or {})
        raw_fields = payload.get("fields") if isinstance(payload.get("fields"), dict) else {}
        payload["fields"] = self._normalize_fields_for_output(raw_fields)
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
        return {
            "system_positioning": {
                "system_description": "",
                "target_users": [],
                "boundaries": [],
            },
            "business_capabilities": {
                "module_structure": [],
                "core_processes": [],
            },
            "integration_interfaces": {
                "integration_points": [],
                "external_dependencies": [],
            },
            "technical_architecture": {
                "architecture_positioning": "",
                "tech_stack": [],
                "performance_profile": {},
            },
            "constraints_risks": {
                "key_constraints": [],
                "known_risks": [],
            },
        }

    def _normalize_text_list(self, value: Any) -> List[str]:
        if isinstance(value, list):
            items = []
            for item in value:
                text = str(item or "").strip()
                if text:
                    items.append(text)
            return items

        if isinstance(value, str):
            normalized = (
                value.replace("，", ",")
                .replace("、", ",")
                .replace("；", ",")
                .replace(";", ",")
            )
            items = []
            for line in normalized.splitlines():
                for part in line.split(","):
                    text = part.strip()
                    if text:
                        items.append(text)
            return items

        return []

    def _normalize_integration_points(self, value: Any) -> List[Dict[str, Any]]:
        if isinstance(value, str):
            text = value.strip()
            return [{"description": text}] if text else []

        if not isinstance(value, list):
            return []

        normalized_points: List[Dict[str, Any]] = []
        for item in value:
            if isinstance(item, dict):
                point = {
                    "peer_system": str(item.get("peer_system") or "").strip(),
                    "protocol": str(item.get("protocol") or "").strip(),
                    "direction": str(item.get("direction") or "").strip(),
                    "description": str(item.get("description") or item.get("name") or "").strip(),
                }
                # 保持数据可读，去掉空字段
                compact = {k: v for k, v in point.items() if str(v).strip()}
                if compact:
                    normalized_points.append(compact)
                continue

            text = str(item or "").strip()
            if text:
                normalized_points.append({"description": text})

        return normalized_points

    def _normalize_key_constraints(self, value: Any) -> List[Dict[str, str]]:
        if isinstance(value, str):
            text = value.strip()
            return [{"category": "通用", "description": text}] if text else []

        if not isinstance(value, list):
            return []

        constraints: List[Dict[str, str]] = []
        for item in value:
            if isinstance(item, dict):
                description = str(item.get("description") or item.get("value") or "").strip()
                if not description:
                    continue
                category = str(item.get("category") or "通用").strip() or "通用"
                constraints.append({"category": category, "description": description})
                continue

            text = str(item or "").strip()
            if text:
                constraints.append({"category": "通用", "description": text})

        return constraints

    def _normalize_performance_profile(self, value: Any) -> Dict[str, str]:
        if isinstance(value, dict):
            normalized: Dict[str, str] = {}
            for key, raw_value in value.items():
                metric = str(key or "").strip()
                if not metric:
                    continue
                normalized[metric] = str(raw_value or "").strip()
            return normalized

        if not isinstance(value, list):
            return {}

        normalized = {}
        for item in value:
            if not isinstance(item, dict):
                continue
            key = str(item.get("key") or item.get("metric") or "").strip()
            if not key:
                continue
            normalized[key] = str(item.get("value") or "").strip()
        return normalized

    def _normalize_profile_data_sub_field(self, domain_key: str, sub_field: str, value: Any) -> Any:
        if domain_key == "system_positioning" and sub_field in {"target_users", "boundaries"}:
            return self._normalize_text_list(value)

        if domain_key == "business_capabilities":
            if sub_field == "module_structure":
                return self._normalize_module_structure(value, strict=False)
            if sub_field == "core_processes":
                return self._normalize_text_list(value)

        if domain_key == "integration_interfaces":
            if sub_field == "integration_points":
                return self._normalize_integration_points(value)
            if sub_field == "external_dependencies":
                return self._normalize_text_list(value)

        if domain_key == "technical_architecture":
            if sub_field == "tech_stack":
                return self._normalize_text_list(value)
            if sub_field == "performance_profile":
                return self._normalize_performance_profile(value)

        if domain_key == "constraints_risks":
            if sub_field == "key_constraints":
                return self._normalize_key_constraints(value)
            if sub_field == "known_risks":
                return self._normalize_text_list(value)

        if isinstance(value, str):
            return value.strip()

        return copy.deepcopy(value)

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
        normalized = self._normalize_fields_for_output(fields if isinstance(fields, dict) else {})
        module_structure = self._normalize_module_structure(normalized.get("module_structure"), strict=False)
        integration_points = str(normalized.get("integration_points") or "").strip()
        key_constraints = str(normalized.get("key_constraints") or "").strip()

        profile_data = self._empty_profile_data()
        profile_data["system_positioning"]["system_description"] = str(normalized.get("system_scope") or "").strip()
        profile_data["business_capabilities"]["module_structure"] = module_structure

        if integration_points:
            profile_data["integration_interfaces"]["integration_points"] = [{"description": integration_points}]
        if key_constraints:
            profile_data["constraints_risks"]["key_constraints"] = [
                {"category": "通用", "description": key_constraints}
            ]
        return profile_data

    def _is_v24_profile_shape(self, value: Any) -> bool:
        if not isinstance(value, dict):
            return False
        return any(domain in value for domain in PROFILE_V24_DOMAIN_KEYS)

    def _migrate_suggestions_structure(self, value: Any, fallback_fields: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(value, dict):
            return {}
        if self._is_v24_profile_shape(value):
            return value

        legacy = {
            "system_scope": value.get("system_scope", fallback_fields.get("system_scope")),
            "module_structure": value.get("module_structure", fallback_fields.get("module_structure")),
            "integration_points": value.get("integration_points", fallback_fields.get("integration_points")),
            "key_constraints": value.get("key_constraints", fallback_fields.get("key_constraints")),
        }
        return self._build_profile_data_from_legacy_fields(legacy)

    def _migrate_profile_record(self, profile: Dict[str, Any]) -> bool:
        if not isinstance(profile, dict):
            return False

        changed = False
        now = datetime.now().isoformat()
        fields = profile.get("fields") if isinstance(profile.get("fields"), dict) else {}
        fields = self._normalize_fields_for_output(fields)

        if not isinstance(profile.get("profile_data"), dict):
            profile["profile_data"] = self._build_profile_data_from_legacy_fields(fields)
            profile["_migrated"] = True
            if not profile.get("_migrated_at"):
                profile["_migrated_at"] = now
            changed = True

        if isinstance(profile.get("ai_suggestions"), dict) and (not self._is_v24_profile_shape(profile.get("ai_suggestions"))):
            profile["ai_suggestions"] = self._migrate_suggestions_structure(profile.get("ai_suggestions"), fields)
            changed = True

        if profile.get("ai_suggestions_previous") is not None:
            previous = profile.get("ai_suggestions_previous")
            if isinstance(previous, dict) and (not self._is_v24_profile_shape(previous)):
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
        field_key = str(legacy_field or "").strip()
        if field_key == "module_structure":
            return self._normalize_module_structure(value, strict=False)
        if field_key == "integration_points":
            if isinstance(value, list):
                segments: List[str] = []
                for item in value:
                    if isinstance(item, dict):
                        text = str(item.get("description") or item.get("name") or "").strip()
                    else:
                        text = str(item or "").strip()
                    if text:
                        segments.append(text)
                return "；".join(segments)
            return "" if value is None else str(value).strip()
        if field_key == "key_constraints":
            if isinstance(value, list):
                segments = []
                for item in value:
                    if isinstance(item, dict):
                        text = str(item.get("description") or item.get("value") or "").strip()
                    else:
                        text = str(item or "").strip()
                    if text:
                        segments.append(text)
                return "；".join(segments)
            return "" if value is None else str(value).strip()
        return "" if value is None else str(value).strip()

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
                "timestamp": datetime.now().isoformat(),
                "source": str(source or "").strip(),
                "summary": str(summary or "").strip(),
                "affected_domains": list(affected_domains or []),
            }
        )
        profile["profile_events"] = events

    def _ensure_profile_data_shape(self, profile: Dict[str, Any], fields: Dict[str, Any]) -> Dict[str, Any]:
        profile_data = profile.get("profile_data") if isinstance(profile.get("profile_data"), dict) else None
        if profile_data is None:
            profile_data = self._build_profile_data_from_legacy_fields(fields)
            profile["profile_data"] = profile_data
        return profile_data

    def _merge_profile_data(self, base: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
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
        if self._is_v24_profile_shape(value):
            return value
        migrated = self._migrate_suggestions_structure(value, fields)
        profile[key] = migrated
        return migrated

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
        now = datetime.now().isoformat()

        with self._lock():
            items = self._load_unlocked()
            profile = self._find_profile(items, name)
            if not profile:
                raise ValueError("系统画像不存在")

            fields = profile.get("fields") if isinstance(profile.get("fields"), dict) else {}
            fields = self._normalize_fields_for_output(fields)
            profile_data = self._ensure_profile_data_shape(profile, fields)
            ai_suggestions = self._ensure_suggestions_shape(profile, key="ai_suggestions", fields=fields)

            domain_payload = ai_suggestions.get(normalized_domain)
            if not isinstance(domain_payload, dict) or (normalized_sub_field not in domain_payload):
                raise ValueError("SUGGESTION_NOT_FOUND")

            accepted_value = copy.deepcopy(domain_payload.get(normalized_sub_field))
            current_domain_payload = profile_data.get(normalized_domain)
            if not isinstance(current_domain_payload, dict):
                current_domain_payload = {}
                profile_data[normalized_domain] = current_domain_payload
            current_domain_payload[normalized_sub_field] = accepted_value
            profile["profile_data"] = profile_data

            legacy_field = PROFILE_V24_TO_LEGACY_FIELD.get((normalized_domain, normalized_sub_field))
            if legacy_field:
                normalized_for_storage = self._normalize_fields_for_storage(profile.get("fields") or {})
                normalized_for_storage[legacy_field] = self._normalize_domain_value_for_legacy_field(
                    legacy_field,
                    accepted_value,
                )
                profile["fields"] = normalized_for_storage

            ignored_key = f"{normalized_domain}.{normalized_sub_field}"
            ignored_map = self._normalize_ai_suggestion_ignored_for_storage(profile.get("ai_suggestion_ignored"))
            if ignored_key in ignored_map:
                ignored_map.pop(ignored_key, None)
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

            return self._normalize_profile_for_output(profile)

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
        now = datetime.now().isoformat()

        with self._lock():
            items = self._load_unlocked()
            profile = self._find_profile(items, name)
            if not profile:
                raise ValueError("系统画像不存在")

            fields = profile.get("fields") if isinstance(profile.get("fields"), dict) else {}
            fields = self._normalize_fields_for_output(fields)
            ai_suggestions = self._ensure_suggestions_shape(profile, key="ai_suggestions", fields=fields)
            previous = self._ensure_suggestions_shape(profile, key="ai_suggestions_previous", fields=fields)

            prev_domain_payload = previous.get(normalized_domain) if isinstance(previous, dict) else None
            if not isinstance(prev_domain_payload, dict) or (normalized_sub_field not in prev_domain_payload):
                raise ValueError("ROLLBACK_NO_PREVIOUS")

            target_domain = ai_suggestions.get(normalized_domain)
            if not isinstance(target_domain, dict):
                target_domain = {}
                ai_suggestions[normalized_domain] = target_domain

            rolled_back_value = copy.deepcopy(prev_domain_payload.get(normalized_sub_field))
            target_domain[normalized_sub_field] = rolled_back_value
            profile["ai_suggestions"] = ai_suggestions

            ignored_key = f"{normalized_domain}.{normalized_sub_field}"
            ignored_map = self._normalize_ai_suggestion_ignored_for_storage(profile.get("ai_suggestion_ignored"))
            if ignored_key in ignored_map:
                ignored_map.pop(ignored_key, None)
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

            return {
                "profile": self._normalize_profile_for_output(profile),
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
        now = datetime.now().isoformat()

        with self._lock():
            items = self._load_unlocked()
            profile = self._find_profile(items, name)
            if not profile:
                raise ValueError("系统画像不存在")

            fields = profile.get("fields") if isinstance(profile.get("fields"), dict) else {}
            fields = self._normalize_fields_for_output(fields)
            ai_suggestions = self._ensure_suggestions_shape(profile, key="ai_suggestions", fields=fields)

            domain_payload = ai_suggestions.get(normalized_domain)
            if not isinstance(domain_payload, dict) or (normalized_sub_field not in domain_payload):
                raise ValueError("SUGGESTION_NOT_FOUND")

            ignored_key = f"{normalized_domain}.{normalized_sub_field}"
            ignored_value = copy.deepcopy(domain_payload.get(normalized_sub_field))
            ignored_map = self._normalize_ai_suggestion_ignored_for_storage(profile.get("ai_suggestion_ignored"))
            ignored_map[ignored_key] = ignored_value
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

            return self._normalize_profile_for_output(profile)

    def record_import_history(
        self,
        system_id: str,
        *,
        doc_type: str,
        file_name: str,
        status: str,
        operator_id: str,
        failure_reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        normalized_system_id = str(system_id or "").strip()
        if not normalized_system_id:
            raise ValueError("system_id不能为空")

        now = datetime.now().isoformat()
        item = {
            "id": uuid.uuid4().hex,
            "doc_type": str(doc_type or "").strip(),
            "file_name": str(file_name or "").strip(),
            "imported_at": now,
            "status": str(status or "").strip() or "failed",
            "failure_reason": None if not str(failure_reason or "").strip() else str(failure_reason or "").strip(),
            "operator_id": str(operator_id or "").strip() or "unknown",
        }

        with self._lock():
            payload = self._load_object_file_unlocked(self.import_history_store_path)
            records = payload.get(normalized_system_id) if isinstance(payload.get(normalized_system_id), list) else []
            records = [record for record in records if isinstance(record, dict)]
            records.append(item)
            records.sort(key=lambda record: str(record.get("imported_at") or ""), reverse=True)
            payload[normalized_system_id] = records
            self._save_object_file_unlocked(self.import_history_store_path, payload)

        return dict(item)

    def get_import_history(self, system_id: str, *, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        normalized_system_id = str(system_id or "").strip()
        if not normalized_system_id:
            raise ValueError("system_id不能为空")

        safe_limit = max(1, min(int(limit or 50), 200))
        safe_offset = max(0, int(offset or 0))

        with self._lock():
            payload = self._load_object_file_unlocked(self.import_history_store_path)
            records = payload.get(normalized_system_id) if isinstance(payload.get(normalized_system_id), list) else []
            records = [record for record in records if isinstance(record, dict)]
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
        now = datetime.now().isoformat()

        with self._lock():
            payload = self._load_object_file_unlocked(self.extraction_task_store_path)
            existing = payload.get(normalized_system_id) if isinstance(payload.get(normalized_system_id), dict) else {}
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

            payload[normalized_system_id] = task
            self._save_object_file_unlocked(self.extraction_task_store_path, payload)
            result = dict(task)
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
        now = datetime.now().isoformat()
        with self._lock():
            payload = self._load_object_file_unlocked(self.extraction_task_store_path)
            existing = payload.get(normalized_system_id) if isinstance(payload.get(normalized_system_id), dict) else {}

            existing_task_id = str(existing.get("task_id") or "").strip()
            if existing_task_id and existing_task_id != normalized_task_id:
                # Ignore stale status updates from older tasks when a newer task has already
                # been recorded for the same system.
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

            payload[normalized_system_id] = existing
            self._save_object_file_unlocked(self.extraction_task_store_path, payload)
            result = dict(existing)
        self._notify_extraction_task_listeners(normalized_system_id, result)
        return result

    def get_extraction_task(self, system_id: str) -> Optional[Dict[str, Any]]:
        normalized_system_id = str(system_id or "").strip()
        if not normalized_system_id:
            raise ValueError("system_id不能为空")

        with self._lock():
            payload = self._load_object_file_unlocked(self.extraction_task_store_path)
            task = payload.get(normalized_system_id)
            if not isinstance(task, dict):
                return None
            return dict(task)

    def get_extraction_task_by_task_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        normalized_task_id = str(task_id or "").strip()
        if not normalized_task_id:
            raise ValueError("task_id不能为空")

        with self._lock():
            payload = self._load_object_file_unlocked(self.extraction_task_store_path)
            if not isinstance(payload, dict):
                return None

            for system_id, task in payload.items():
                if not isinstance(task, dict):
                    continue
                if str(task.get("task_id") or "").strip() != normalized_task_id:
                    continue
                return {
                    "system_id": str(system_id or "").strip(),
                    "task": dict(task),
                }
        return None

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

    def upsert_profile(
        self,
        system_name: str,
        payload: Dict[str, Any],
        actor: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        name = str(system_name or "").strip()
        if not name:
            raise ValueError("system_name不能为空")

        incoming_fields = payload.get("fields") if isinstance(payload.get("fields"), dict) else {}
        incoming_fields = self._normalize_fields_for_storage(incoming_fields)
        incoming_profile_data = payload.get("profile_data") if isinstance(payload.get("profile_data"), dict) else None
        evidence_refs = payload.get("evidence_refs") if isinstance(payload.get("evidence_refs"), list) else []
        system_id = str(payload.get("system_id") or "").strip()
        incoming_sources = payload.get("field_sources") if isinstance(payload.get("field_sources"), dict) else {}
        incoming_ignored = self._normalize_ai_suggestion_ignored_for_storage(payload.get("ai_suggestion_ignored"))

        now = datetime.now().isoformat()
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
                    "fields": {},
                    "evidence_refs": [],
                    "pending_fields": [],
                    "field_sources": {},
                    "ai_suggestions": {},
                    "ai_suggestion_ignored": {},
                    "ai_suggestions_updated_at": "",
                    "created_at": now,
                }
                items.append(existing)

            existing["system_id"] = system_id or existing.get("system_id") or ""
            existing_fields = existing.get("fields") if isinstance(existing.get("fields"), dict) else {}
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
            existing["fields"] = existing_fields
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

        now = datetime.now().isoformat()
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

        now = datetime.now().isoformat()
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

        now = datetime.now().isoformat()
        actor_name = (actor or {}).get("displayName") or (actor or {}).get("username") or "system"
        source_text = str(source or "").strip() or actor_name
        normalized_trigger = str(trigger or "").strip() or "document_import"
        raw_suggestions = suggestions if isinstance(suggestions, dict) else {}

        with self._lock():
            items = self._load_unlocked()
            profile = self._find_profile(items, name)
            if not profile:
                raise ValueError("系统画像不存在")

            fields = profile.get("fields") if isinstance(profile.get("fields"), dict) else {}
            fields = self._normalize_fields_for_output(fields)

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
                        # If domain appears multiple times, no-op; keep ordered unique list.
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
            updated_domains: List[str] = []
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

        now = datetime.now().isoformat()
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
                    "fields": {},
                    "evidence_refs": [],
                    "pending_fields": [],
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

        now = datetime.now().isoformat()
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
                    "fields": {},
                    "evidence_refs": [],
                    "pending_fields": [],
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
        now = datetime.now().isoformat()
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
                    "fields": {},
                    "evidence_refs": [],
                    "pending_fields": [],
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

        now = datetime.now().isoformat()
        actor_id = (actor or {}).get("id") or (actor or {}).get("username") or "unknown"
        actor_name = (actor or {}).get("displayName") or (actor or {}).get("username") or "unknown"

        with self._lock():
            items = self._load_unlocked()
            profile = self._find_profile(items, name)
            if not profile:
                raise ValueError("系统画像不存在")

            fields = profile.get("fields") if isinstance(profile.get("fields"), dict) else {}
            fields = self._normalize_fields_for_storage(fields)

            profile_snapshot = copy.deepcopy(profile)
            profile_snapshot["fields"] = fields
            pending_fields = self._calc_pending_fields(profile_snapshot)
            profile_snapshot["pending_fields"] = pending_fields
            profile_snapshot["status"] = "published"
            profile_snapshot["published_at"] = now
            profile_snapshot["updated_by"] = actor_id
            profile_snapshot["updated_by_name"] = actor_name
            profile_snapshot["updated_at"] = now

        try:
            from backend.service.knowledge_service import get_knowledge_service
            knowledge_service = get_knowledge_service()
            text = self._build_profile_text(profile_snapshot)
            embedding = knowledge_service.embedding_service.generate_embedding(text)
            knowledge_service.vector_store.insert_knowledge(
                system_name=profile_snapshot.get("system_name"),
                knowledge_type="system_profile",
                content=text,
                embedding=embedding,
                metadata=profile_snapshot.get("fields") or {},
                source_file="system_profile_manual",
            )
        except Exception as exc:
            raise RuntimeError(f"embedding服务不可用: {exc}") from exc

        with self._lock():
            items = self._load_unlocked()
            profile = self._find_profile(items, name)
            if not profile:
                raise ValueError("系统画像不存在")

            if isinstance(profile.get("fields"), dict):
                profile["fields"] = self._normalize_fields_for_storage(profile.get("fields") or {})

            pending_fields = self._calc_pending_fields(profile)
            profile["pending_fields"] = pending_fields
            profile["status"] = "published"
            profile["published_at"] = now
            profile["updated_by"] = actor_id
            profile["updated_by_name"] = actor_name
            profile["updated_at"] = now

            self._save_unlocked(items)

            return self._normalize_profile_for_output(profile)

    def _calc_pending_fields(self, profile: Dict[str, Any]) -> List[str]:
        fields = profile.get("fields") if isinstance(profile.get("fields"), dict) else {}
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

    def _build_profile_text(self, profile: Dict[str, Any]) -> str:
        fields = profile.get("fields") if isinstance(profile.get("fields"), dict) else {}
        module_structure = self._normalize_module_structure(fields.get("module_structure"), strict=False)
        module_segments: List[str] = []
        for module_item in module_structure[:20]:
            module_name = str(module_item.get("module_name") or "").strip()
            function_names = self._collect_module_leaf_names(module_item, limit=20)
            if module_name and function_names:
                module_segments.append(f"{module_name}({ '、'.join(function_names[:20]) })")
            elif module_name:
                module_segments.append(module_name)
        module_structure_text = "；".join(module_segments)
        return (
            f"系统名称:{profile.get('system_name','')} | "
            f"系统定位与边界:{fields.get('system_scope','')} | "
            f"模块结构:{module_structure_text} | "
            f"主要集成点:{fields.get('integration_points','')} | "
            f"关键约束:{fields.get('key_constraints','')}"
        )

    def has_published_profile(self, system_name: str) -> bool:
        profile = self.get_profile(system_name)
        return bool(profile and profile.get("status") == "published")

    def get_minimal_profile_flags(self, system_name: str) -> Dict[str, Any]:
        profile = self.get_profile(system_name) or {}
        fields = profile.get("fields") if isinstance(profile.get("fields"), dict) else {}
        minimal_keys = ["system_scope", "module_structure"]
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
    if _system_profile_service is None:
        _system_profile_service = SystemProfileService()
    return _system_profile_service
