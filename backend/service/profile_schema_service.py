from __future__ import annotations

import copy
from typing import Any, Dict, Iterable, Iterator, Tuple

V27_DOMAIN_KEYS = (
    "system_positioning",
    "business_capabilities",
    "integration_interfaces",
    "technical_architecture",
    "constraints_risks",
)

_EMPTY_PROFILE_TEMPLATE: Dict[str, Any] = {
    "system_positioning": {
        "canonical": {
            "system_type": "",
            "business_domain": [],
            "architecture_layer": "",
            "target_users": [],
            "service_scope": "",
            "system_boundary": [],
            "extensions": {},
        }
    },
    "business_capabilities": {
        "canonical": {
            "functional_modules": [],
            "business_processes": [],
            "data_assets": [],
            "extensions": {},
        }
    },
    "integration_interfaces": {
        "canonical": {
            "provided_services": [],
            "consumed_services": [],
            "other_integrations": [],
            "extensions": {},
        }
    },
    "technical_architecture": {
        "canonical": {
            "architecture_style": "",
            "tech_stack": {
                "languages": [],
                "frameworks": [],
                "databases": [],
                "middleware": [],
                "others": [],
            },
            "network_zone": "",
            "performance_baseline": {
                "online": {
                    "peak_tps": "",
                    "p95_latency_ms": "",
                    "availability_target": "",
                },
                "batch": {
                    "window": "",
                    "data_volume": "",
                    "peak_duration": "",
                },
                "processing_model": "",
            },
            "extensions": {},
        }
    },
    "constraints_risks": {
        "canonical": {
            "technical_constraints": [],
            "business_constraints": [],
            "known_risks": [],
            "extensions": {},
        }
    },
}

_LIST_FIELDS = {
    "system_positioning": {"business_domain", "target_users", "system_boundary"},
    "business_capabilities": {"functional_modules", "business_processes", "data_assets"},
    "integration_interfaces": {"provided_services", "consumed_services", "other_integrations"},
    "constraints_risks": {"technical_constraints", "business_constraints", "known_risks"},
}

_STRING_FIELDS = {
    "system_positioning": {"system_type", "architecture_layer", "service_scope"},
    "technical_architecture": {"architecture_style", "network_zone"},
}


def build_empty_profile_data() -> Dict[str, Any]:
    return copy.deepcopy(_EMPTY_PROFILE_TEMPLATE)


def _normalize_string(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _normalize_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        raw_items = value
    elif isinstance(value, str):
        normalized = (
            value.replace("，", ",")
            .replace("、", ",")
            .replace("；", ",")
            .replace(";", ",")
        )
        raw_items = []
        for line in normalized.splitlines():
            raw_items.extend(line.split(","))
    else:
        raw_items = [value]

    result: list[str] = []
    for item in raw_items:
        text = _normalize_string(item)
        if text:
            result.append(text)
    return result


def _normalize_generic_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return copy.deepcopy(value)
    if isinstance(value, str):
        items = _normalize_string_list(value)
        return items
    return [copy.deepcopy(value)]


def _normalize_tech_stack(value: Any) -> Dict[str, list[str]]:
    template = build_empty_profile_data()["technical_architecture"]["canonical"]["tech_stack"]
    if not isinstance(value, dict):
        return template

    normalized = copy.deepcopy(template)
    for key in template:
        normalized[key] = _normalize_string_list(value.get(key))
    return normalized


def _normalize_performance_baseline(value: Any) -> Dict[str, Any]:
    template = build_empty_profile_data()["technical_architecture"]["canonical"]["performance_baseline"]
    if not isinstance(value, dict):
        return template

    normalized = copy.deepcopy(template)
    for section in ("online", "batch"):
        raw_section = value.get(section)
        if not isinstance(raw_section, dict):
            continue
        for key in normalized[section]:
            normalized[section][key] = _normalize_string(raw_section.get(key))
    normalized["processing_model"] = _normalize_string(value.get("processing_model"))
    return normalized


def _normalize_extensions(value: Any) -> Dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return copy.deepcopy(value)


def normalize_profile_data(value: Any) -> Dict[str, Any]:
    raw_profile_data = value if isinstance(value, dict) else {}
    normalized = build_empty_profile_data()

    for domain in V27_DOMAIN_KEYS:
        raw_domain = raw_profile_data.get(domain)
        canonical = raw_domain.get("canonical") if isinstance(raw_domain, dict) else {}
        if not isinstance(canonical, dict):
            canonical = {}

        target = normalized[domain]["canonical"]
        for field_name in list(target.keys()):
            if field_name == "extensions":
                target[field_name] = _normalize_extensions(canonical.get(field_name))
                continue

            if domain == "technical_architecture" and field_name == "tech_stack":
                target[field_name] = _normalize_tech_stack(canonical.get(field_name))
                continue

            if domain == "technical_architecture" and field_name == "performance_baseline":
                target[field_name] = _normalize_performance_baseline(canonical.get(field_name))
                continue

            if field_name in _LIST_FIELDS.get(domain, set()):
                if field_name in {"provided_services", "consumed_services", "other_integrations"}:
                    target[field_name] = _normalize_generic_list(canonical.get(field_name))
                else:
                    target[field_name] = _normalize_string_list(canonical.get(field_name))
                continue

            if field_name in _STRING_FIELDS.get(domain, set()):
                target[field_name] = _normalize_string(canonical.get(field_name))
                continue

            target[field_name] = copy.deepcopy(canonical.get(field_name))

    return normalized


def has_non_empty_value(value: Any) -> bool:
    if value in (None, ""):
        return False
    if isinstance(value, list):
        return any(has_non_empty_value(item) for item in value)
    if isinstance(value, dict):
        return any(has_non_empty_value(item) for item in value.values())
    return True


def is_blank_profile(profile: Dict[str, Any]) -> bool:
    profile_data = normalize_profile_data((profile or {}).get("profile_data"))
    for domain in V27_DOMAIN_KEYS:
        canonical = profile_data[domain]["canonical"]
        if has_non_empty_value(canonical):
            return False
    return True


def iter_canonical_field_paths(profile_data: Dict[str, Any]) -> Iterator[Tuple[str, Any]]:
    normalized = normalize_profile_data(profile_data)
    for domain in V27_DOMAIN_KEYS:
        canonical = normalized[domain]["canonical"]
        for key, value in canonical.items():
            yield f"{domain}.canonical.{key}", value


def get_field_value(profile_data: Dict[str, Any], field_path: str) -> Any:
    parts = str(field_path or "").split(".")
    cursor: Any = profile_data
    for part in parts:
        if not isinstance(cursor, dict):
            return None
        cursor = cursor.get(part)
    return copy.deepcopy(cursor)


def set_field_value(profile_data: Dict[str, Any], field_path: str, value: Any) -> Dict[str, Any]:
    normalized = normalize_profile_data(profile_data)
    parts = str(field_path or "").split(".")
    if len(parts) < 3:
        raise ValueError("invalid_field_path")

    cursor: Dict[str, Any] = normalized
    for part in parts[:-1]:
        next_value = cursor.get(part)
        if not isinstance(next_value, dict):
            next_value = {}
            cursor[part] = next_value
        cursor = next_value
    cursor[parts[-1]] = copy.deepcopy(value)
    return normalized
