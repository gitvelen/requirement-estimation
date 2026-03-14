from __future__ import annotations

import copy
import json
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List

logger = logging.getLogger(__name__)

LEGACY_FIELDS_KEY = "fields"
LEGACY_PENDING_FIELDS_KEY = "pending_fields"

LEGACY_SYSTEM_SCOPE_KEY = "system_scope"
LEGACY_MODULE_TREE_KEY = "module_structure"
LEGACY_INTERFACE_KEY = "integration_points"
LEGACY_CONSTRAINT_KEY = "key_constraints"
LEGACY_ARCH_POSITION_KEY = "architecture_positioning"
LEGACY_TREE_ERROR = "invalid_module_structure"

LEGACY_PROFILE_FIELD_KEYS = (
    LEGACY_SYSTEM_SCOPE_KEY,
    LEGACY_MODULE_TREE_KEY,
    LEGACY_INTERFACE_KEY,
    LEGACY_CONSTRAINT_KEY,
)

LEGACY_PROFILE_TEXT_KEYS = {
    LEGACY_SYSTEM_SCOPE_KEY,
    LEGACY_INTERFACE_KEY,
    LEGACY_CONSTRAINT_KEY,
}

LEGACY_PROFILE_DOMAIN_KEYS = (
    "system_positioning",
    "business_capabilities",
    "integration_interfaces",
    "technical_architecture",
    "constraints_risks",
)

LEGACY_PROFILE_FIELD_MAPPING = {
    ("system_positioning", "system_description"): LEGACY_SYSTEM_SCOPE_KEY,
    ("business_capabilities", LEGACY_MODULE_TREE_KEY): LEGACY_MODULE_TREE_KEY,
    ("integration_interfaces", LEGACY_INTERFACE_KEY): LEGACY_INTERFACE_KEY,
    ("constraints_risks", LEGACY_CONSTRAINT_KEY): LEGACY_CONSTRAINT_KEY,
}


def default_legacy_profile_data() -> Dict[str, Any]:
    return {
        "system_positioning": {
            "system_description": "",
            "target_users": [],
            "boundaries": [],
        },
        "business_capabilities": {
            LEGACY_MODULE_TREE_KEY: [],
            "core_processes": [],
        },
        "integration_interfaces": {
            LEGACY_INTERFACE_KEY: [],
            "external_dependencies": [],
        },
        "technical_architecture": {
            LEGACY_ARCH_POSITION_KEY: "",
            "tech_stack": [],
            "performance_profile": {},
        },
        "constraints_risks": {
            LEGACY_CONSTRAINT_KEY: [],
            "known_risks": [],
        },
    }


def normalize_text_list(value: Any) -> List[str]:
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


def normalize_module_structure(value: Any, *, strict: bool) -> List[Dict[str, Any]]:
    def _normalize_module_node(
        node: Any,
        *,
        strict: bool,
        depth: int,
        max_depth: int,
    ) -> tuple[Dict[str, Any] | None, bool]:
        if not isinstance(node, dict):
            if strict:
                raise ValueError(LEGACY_TREE_ERROR)
            return None, False

        module_name = str(node.get("module_name") or "").strip()
        if not module_name:
            if strict:
                raise ValueError(LEGACY_TREE_ERROR)
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
                    raise ValueError(LEGACY_TREE_ERROR)
            elif depth >= max_depth:
                if raw_children:
                    depth_truncated = True
            else:
                for child_item in raw_children:
                    child_node, child_truncated = _normalize_module_node(
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
                    raise ValueError(LEGACY_TREE_ERROR)
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
                            raise ValueError(LEGACY_TREE_ERROR)
                        continue

                    if not function_name:
                        if strict:
                            raise ValueError(LEGACY_TREE_ERROR)
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
                raise ValueError(LEGACY_TREE_ERROR)
            return []

    if not isinstance(parsed_value, list):
        if strict:
            raise ValueError(LEGACY_TREE_ERROR)
        return []

    normalized_modules: List[Dict[str, Any]] = []
    now = datetime.now().isoformat()
    max_depth = 3
    has_depth_truncated = False

    for module_item in parsed_value:
        normalized_module, depth_truncated = _normalize_module_node(
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


def normalize_fields_for_storage(fields: Dict[str, Any]) -> Dict[str, Any]:
    raw_fields = fields if isinstance(fields, dict) else {}
    normalized: Dict[str, Any] = {}
    for key in LEGACY_PROFILE_TEXT_KEYS:
        if key in raw_fields:
            value = raw_fields.get(key)
            normalized[key] = "" if value is None else str(value).strip()
    if LEGACY_MODULE_TREE_KEY in raw_fields:
        normalized[LEGACY_MODULE_TREE_KEY] = normalize_module_structure(
            raw_fields.get(LEGACY_MODULE_TREE_KEY),
            strict=True,
        )
    return normalized


def normalize_fields_for_output(fields: Dict[str, Any]) -> Dict[str, Any]:
    raw_fields = fields if isinstance(fields, dict) else {}
    return {
        LEGACY_SYSTEM_SCOPE_KEY: ""
        if raw_fields.get(LEGACY_SYSTEM_SCOPE_KEY) is None
        else str(raw_fields.get(LEGACY_SYSTEM_SCOPE_KEY)).strip(),
        LEGACY_MODULE_TREE_KEY: normalize_module_structure(
            raw_fields.get(LEGACY_MODULE_TREE_KEY),
            strict=False,
        ),
        LEGACY_INTERFACE_KEY: ""
        if raw_fields.get(LEGACY_INTERFACE_KEY) is None
        else str(raw_fields.get(LEGACY_INTERFACE_KEY)).strip(),
        LEGACY_CONSTRAINT_KEY: ""
        if raw_fields.get(LEGACY_CONSTRAINT_KEY) is None
        else str(raw_fields.get(LEGACY_CONSTRAINT_KEY)).strip(),
    }


def normalize_integration_points(value: Any) -> List[Dict[str, Any]]:
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
            compact = {k: v for k, v in point.items() if str(v).strip()}
            if compact:
                normalized_points.append(compact)
            continue

        text = str(item or "").strip()
        if text:
            normalized_points.append({"description": text})

    return normalized_points


def normalize_key_constraints(value: Any) -> List[Dict[str, str]]:
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


def normalize_performance_profile(value: Any) -> Dict[str, str]:
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


def normalize_profile_data_sub_field(domain_key: str, sub_field: str, value: Any) -> Any:
    if domain_key == "system_positioning" and sub_field in {"target_users", "boundaries"}:
        return normalize_text_list(value)

    if domain_key == "business_capabilities":
        if sub_field == LEGACY_MODULE_TREE_KEY:
            return normalize_module_structure(value, strict=False)
        if sub_field == "core_processes":
            return normalize_text_list(value)

    if domain_key == "integration_interfaces":
        if sub_field == LEGACY_INTERFACE_KEY:
            return normalize_integration_points(value)
        if sub_field == "external_dependencies":
            return normalize_text_list(value)

    if domain_key == "technical_architecture":
        if sub_field == "tech_stack":
            return normalize_text_list(value)
        if sub_field == "performance_profile":
            return normalize_performance_profile(value)

    if domain_key == "constraints_risks":
        if sub_field == LEGACY_CONSTRAINT_KEY:
            return normalize_key_constraints(value)
        if sub_field == "known_risks":
            return normalize_text_list(value)

    if isinstance(value, str):
        return value.strip()

    return copy.deepcopy(value)


def build_profile_data_from_legacy_fields(
    empty_profile_factory: Callable[[], Dict[str, Any]],
    fields: Dict[str, Any],
) -> Dict[str, Any]:
    normalized = normalize_fields_for_output(fields if isinstance(fields, dict) else {})
    module_structure = normalize_module_structure(normalized.get(LEGACY_MODULE_TREE_KEY), strict=False)
    integration_points = str(normalized.get(LEGACY_INTERFACE_KEY) or "").strip()
    key_constraints = str(normalized.get(LEGACY_CONSTRAINT_KEY) or "").strip()

    profile_data = empty_profile_factory()
    profile_data["system_positioning"]["system_description"] = str(normalized.get(LEGACY_SYSTEM_SCOPE_KEY) or "").strip()
    profile_data["business_capabilities"][LEGACY_MODULE_TREE_KEY] = module_structure

    if integration_points:
        profile_data["integration_interfaces"][LEGACY_INTERFACE_KEY] = [{"description": integration_points}]
    if key_constraints:
        profile_data["constraints_risks"][LEGACY_CONSTRAINT_KEY] = [
            {"category": "通用", "description": key_constraints}
        ]
    return profile_data


def is_v24_profile_shape(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    return any(domain in value for domain in LEGACY_PROFILE_DOMAIN_KEYS)


def migrate_suggestions_structure(
    empty_profile_factory: Callable[[], Dict[str, Any]],
    value: Any,
    fallback_fields: Dict[str, Any],
) -> Dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    if is_v24_profile_shape(value):
        return value

    legacy = {
        LEGACY_SYSTEM_SCOPE_KEY: value.get(LEGACY_SYSTEM_SCOPE_KEY, fallback_fields.get(LEGACY_SYSTEM_SCOPE_KEY)),
        LEGACY_MODULE_TREE_KEY: value.get(LEGACY_MODULE_TREE_KEY, fallback_fields.get(LEGACY_MODULE_TREE_KEY)),
        LEGACY_INTERFACE_KEY: value.get(LEGACY_INTERFACE_KEY, fallback_fields.get(LEGACY_INTERFACE_KEY)),
        LEGACY_CONSTRAINT_KEY: value.get(LEGACY_CONSTRAINT_KEY, fallback_fields.get(LEGACY_CONSTRAINT_KEY)),
    }
    return build_profile_data_from_legacy_fields(empty_profile_factory, legacy)


def normalize_domain_value_for_legacy_field(legacy_field: str, value: Any) -> Any:
    field_key = str(legacy_field or "").strip()
    if field_key == LEGACY_MODULE_TREE_KEY:
        return normalize_module_structure(value, strict=False)
    if field_key == LEGACY_INTERFACE_KEY:
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
    if field_key == LEGACY_CONSTRAINT_KEY:
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


def merge_profile_data(
    empty_profile_factory: Callable[[], Dict[str, Any]],
    base: Dict[str, Any],
    incoming: Dict[str, Any],
) -> Dict[str, Any]:
    merged = copy.deepcopy(base if isinstance(base, dict) else empty_profile_factory())
    if not isinstance(incoming, dict):
        return merged

    for domain_key, domain_value in incoming.items():
        if domain_key not in LEGACY_PROFILE_DOMAIN_KEYS:
            continue
        if not isinstance(domain_value, dict):
            continue
        target_domain = merged.get(domain_key)
        if not isinstance(target_domain, dict):
            target_domain = {}
            merged[domain_key] = target_domain
        for sub_field, sub_value in domain_value.items():
            normalized_sub_field = str(sub_field)
            target_domain[normalized_sub_field] = normalize_profile_data_sub_field(
                domain_key,
                normalized_sub_field,
                sub_value,
            )
    return merged


def extract_legacy_fields_from_profile_data(profile_data: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(profile_data, dict):
        return {}

    mapped: Dict[str, Any] = {}
    for (domain_key, sub_field), legacy_field in LEGACY_PROFILE_FIELD_MAPPING.items():
        domain_payload = profile_data.get(domain_key)
        if not isinstance(domain_payload, dict):
            continue
        if sub_field not in domain_payload:
            continue
        mapped[legacy_field] = normalize_domain_value_for_legacy_field(
            legacy_field,
            domain_payload.get(sub_field),
        )
    return mapped


normalize_text_payload = normalize_text_list
normalize_capability_payload = normalize_module_structure
normalize_interface_payload = normalize_integration_points
normalize_constraint_payload = normalize_key_constraints
normalize_metric_payload = normalize_performance_profile
normalize_legacy_profile_value = normalize_profile_data_sub_field
