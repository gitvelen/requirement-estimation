from __future__ import annotations

import copy
from typing import Any, Dict, Iterable, Iterator, List, Tuple

V27_DOMAIN_KEYS = (
    "system_positioning",
    "business_capabilities",
    "integration_interfaces",
    "technical_architecture",
    "constraints_risks",
)

DOMAIN_TITLES = {
    "system_positioning": "D1 系统定位",
    "business_capabilities": "D2 业务能力",
    "integration_interfaces": "D3 系统交互",
    "technical_architecture": "D4 技术架构",
    "constraints_risks": "D5 风险约束",
}

PROFILE_CARD_DEFINITIONS = (
    {
        "card_key": "system_identity",
        "domain_key": "system_positioning",
        "title": "系统身份",
        "field_paths": (
            "system_positioning.canonical.system_type",
            "system_positioning.canonical.lifecycle_status",
            "system_positioning.canonical.system_aliases",
        ),
    },
    {
        "card_key": "business_affiliation",
        "domain_key": "system_positioning",
        "title": "业务归属",
        "field_paths": (
            "system_positioning.canonical.business_domains",
            "system_positioning.canonical.business_lines",
        ),
    },
    {
        "card_key": "application_hierarchy",
        "domain_key": "system_positioning",
        "title": "应用层级",
        "field_paths": (
            "system_positioning.canonical.architecture_layer",
            "system_positioning.canonical.application_level",
        ),
    },
    {
        "card_key": "service_positioning",
        "domain_key": "system_positioning",
        "title": "服务定位",
        "field_paths": (
            "system_positioning.canonical.target_users",
            "system_positioning.canonical.core_responsibility",
        ),
    },
    {
        "card_key": "capability_modules",
        "domain_key": "business_capabilities",
        "title": "功能模块",
        "field_paths": (
            "business_capabilities.canonical.functional_modules",
        ),
    },
    {
        "card_key": "business_scenarios",
        "domain_key": "business_capabilities",
        "title": "典型场景",
        "field_paths": (
            "business_capabilities.canonical.business_scenarios",
        ),
    },
    {
        "card_key": "business_flows",
        "domain_key": "business_capabilities",
        "title": "业务流程",
        "field_paths": (
            "business_capabilities.canonical.business_flows",
        ),
    },
    {
        "card_key": "data_reports",
        "domain_key": "business_capabilities",
        "title": "数据报表",
        "field_paths": (
            "business_capabilities.canonical.data_reports",
        ),
    },
    {
        "card_key": "provided_capabilities",
        "domain_key": "integration_interfaces",
        "title": "对外提供能力",
        "field_paths": (
            "integration_interfaces.canonical.provided_services",
        ),
    },
    {
        "card_key": "consumed_capabilities",
        "domain_key": "integration_interfaces",
        "title": "对外依赖能力",
        "field_paths": (
            "integration_interfaces.canonical.consumed_services",
        ),
    },
    {
        "card_key": "data_exchange_batch_links",
        "domain_key": "integration_interfaces",
        "title": "数据交换与批量链路",
        "field_paths": (
            "integration_interfaces.canonical.other_integrations",
        ),
    },
    {
        "card_key": "architecture_deployment",
        "domain_key": "technical_architecture",
        "title": "架构与部署方式",
        "field_paths": (
            "technical_architecture.canonical.architecture_style",
            "technical_architecture.canonical.network_zone",
            "technical_architecture.canonical.extensions.cloud_deployment",
            "technical_architecture.canonical.extensions.internet_exit",
            "technical_architecture.canonical.extensions.cluster_category",
            "technical_architecture.canonical.extensions.virtualization_distribution",
            "technical_architecture.canonical.extensions.deployment_mode",
            "technical_architecture.canonical.extensions.topology_characteristics",
            "technical_architecture.canonical.extensions.architecture_deployment_notes",
        ),
    },
    {
        "card_key": "tech_stack_infrastructure",
        "domain_key": "technical_architecture",
        "title": "技术栈与基础设施",
        "field_paths": (
            "technical_architecture.canonical.tech_stack",
            "technical_architecture.canonical.extensions.infrastructure_components",
            "technical_architecture.canonical.extensions.technical_stack_notes",
        ),
    },
    {
        "card_key": "design_characteristics",
        "domain_key": "technical_architecture",
        "title": "系统设计特点",
        "field_paths": (
            "technical_architecture.canonical.extensions.design_methods",
            "technical_architecture.canonical.extensions.extensibility_features",
            "technical_architecture.canonical.extensions.common_capabilities",
            "technical_architecture.canonical.extensions.design_characteristics_notes",
        ),
    },
    {
        "card_key": "quality_attributes",
        "domain_key": "technical_architecture",
        "title": "性能、安全与可用性",
        "field_paths": (
            "technical_architecture.canonical.performance_baseline",
            "technical_architecture.canonical.extensions.availability_design",
            "technical_architecture.canonical.extensions.monitoring_operations",
            "technical_architecture.canonical.extensions.security_requirements",
            "technical_architecture.canonical.extensions.quality_attribute_notes",
            "technical_architecture.canonical.extensions.dual_active",
            "constraints_risks.canonical.extensions.dr_status",
            "constraints_risks.canonical.extensions.dr_site",
        ),
    },
    {
        "card_key": "business_constraints",
        "domain_key": "constraints_risks",
        "title": "业务约束",
        "field_paths": (
            "constraints_risks.canonical.business_constraints",
        ),
    },
    {
        "card_key": "prerequisites",
        "domain_key": "constraints_risks",
        "title": "前提条件",
        "field_paths": (
            "constraints_risks.canonical.prerequisites",
        ),
    },
    {
        "card_key": "sensitive_points",
        "domain_key": "constraints_risks",
        "title": "敏感环节",
        "field_paths": (
            "constraints_risks.canonical.sensitive_points",
        ),
    },
    {
        "card_key": "risk_items",
        "domain_key": "constraints_risks",
        "title": "风险事项",
        "field_paths": (
            "constraints_risks.canonical.risk_items",
        ),
    },
)

PROFILE_CARD_KEYS = tuple(item["card_key"] for item in PROFILE_CARD_DEFINITIONS)
PROFILE_CARD_DEFINITIONS_BY_KEY = {item["card_key"]: item for item in PROFILE_CARD_DEFINITIONS}
PROFILE_CARD_KEYS_BY_DOMAIN: Dict[str, List[str]] = {domain_key: [] for domain_key in V27_DOMAIN_KEYS}
FIELD_PATH_TO_CARD_KEYS: Dict[str, List[str]] = {}
for _item in PROFILE_CARD_DEFINITIONS:
    PROFILE_CARD_KEYS_BY_DOMAIN.setdefault(_item["domain_key"], []).append(_item["card_key"])
    for _field_path in _item["field_paths"]:
        FIELD_PATH_TO_CARD_KEYS.setdefault(_field_path, []).append(_item["card_key"])

FIELD_PATH_ALIAS_DEFINITIONS: Dict[str, Tuple[str, ...]] = {
    "system_positioning.canonical.core_responsibility": (
        "system_positioning.canonical.system_description",
        "system_positioning.canonical.service_scope",
    ),
    "system_positioning.canonical.business_domains": (
        "system_positioning.canonical.business_domain",
    ),
    "business_capabilities.canonical.business_scenarios": (
        "business_capabilities.canonical.extensions.business_scenarios",
    ),
    "business_capabilities.canonical.business_flows": (
        "business_capabilities.canonical.core_processes",
        "business_capabilities.canonical.business_processes",
    ),
    "business_capabilities.canonical.data_reports": (
        "business_capabilities.canonical.data_assets",
    ),
    "integration_interfaces.canonical.other_integrations": (
        "integration_interfaces.canonical.integration_points",
    ),
    "technical_architecture.canonical.architecture_style": (
        "technical_architecture.canonical.architecture_positioning",
    ),
    "constraints_risks.canonical.prerequisites": (
        "constraints_risks.canonical.key_constraints",
        "constraints_risks.canonical.technical_constraints",
    ),
    "constraints_risks.canonical.risk_items": (
        "constraints_risks.canonical.known_risks",
    ),
}


def _build_field_path_aliases(canonical_field_path: str, aliases: Tuple[str, ...]) -> List[str]:
    items: List[str] = []
    for raw_path in (canonical_field_path, *aliases):
        normalized = str(raw_path or "").strip()
        if not normalized:
            continue
        for candidate in (
            normalized,
            normalized.replace(".canonical.", ".", 1) if ".canonical." in normalized else normalized,
        ):
            if candidate and candidate not in items:
                items.append(candidate)
    return items


CANONICAL_FIELD_PATH_ALIASES: Dict[str, List[str]] = {}
FIELD_PATH_TO_CANONICAL_PATH: Dict[str, str] = {}
for _canonical_field_path, _aliases in FIELD_PATH_ALIAS_DEFINITIONS.items():
    _items = _build_field_path_aliases(_canonical_field_path, _aliases)
    CANONICAL_FIELD_PATH_ALIASES[_canonical_field_path] = _items
    for _item in _items:
        FIELD_PATH_TO_CANONICAL_PATH[_item] = _canonical_field_path

_EMPTY_PROFILE_TEMPLATE: Dict[str, Any] = {
    "system_positioning": {
        "canonical": {
            "system_type": "",
            "system_aliases": [],
            "lifecycle_status": "",
            "business_domains": [],
            "business_lines": [],
            "architecture_layer": "",
            "application_level": "",
            "target_users": [],
            "core_responsibility": "",
            "extensions": {},
        }
    },
    "business_capabilities": {
        "canonical": {
            "functional_modules": [],
            "business_scenarios": [],
            "business_flows": [],
            "data_reports": [],
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
            "business_constraints": [],
            "prerequisites": [],
            "sensitive_points": [],
            "risk_items": [],
            "extensions": {},
        }
    },
}

_STRING_LIST_FIELDS = {
    "system_positioning": {"system_aliases", "business_domains", "business_lines", "target_users"},
}

_STRUCTURED_LIST_FIELDS = {
    "business_capabilities": {"functional_modules", "business_scenarios", "business_flows", "data_reports"},
    "constraints_risks": {"business_constraints", "prerequisites", "sensitive_points", "risk_items"},
}

_GENERIC_LIST_FIELDS = {
    "integration_interfaces": {"provided_services", "consumed_services", "other_integrations"},
}

_STRING_FIELDS = {
    "system_positioning": {"system_type", "lifecycle_status", "architecture_layer", "application_level", "core_responsibility"},
    "technical_architecture": {"architecture_style", "network_zone"},
}


def build_empty_profile_data() -> Dict[str, Any]:
    return copy.deepcopy(_EMPTY_PROFILE_TEMPLATE)


def resolve_canonical_field_path(field_path: str) -> str:
    normalized = str(field_path or "").strip()
    if not normalized:
        return ""
    return FIELD_PATH_TO_CANONICAL_PATH.get(normalized, normalized)


def get_field_path_aliases(field_path: str) -> List[str]:
    canonical_field_path = resolve_canonical_field_path(field_path)
    aliases = list(CANONICAL_FIELD_PATH_ALIASES.get(canonical_field_path, []))
    if canonical_field_path and canonical_field_path not in aliases:
        aliases.insert(0, canonical_field_path)
    direct_path = canonical_field_path.replace(".canonical.", ".", 1) if ".canonical." in canonical_field_path else canonical_field_path
    if direct_path and direct_path not in aliases:
        aliases.append(direct_path)
    return aliases


def get_logical_field_key(field_path: str) -> str:
    canonical_field_path = resolve_canonical_field_path(field_path)
    return canonical_field_path.replace(".canonical.", ".", 1) if ".canonical." in canonical_field_path else canonical_field_path


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


def _dedupe_strings(items: Iterable[Any]) -> list[str]:
    seen = set()
    result: list[str] = []
    for item in items:
        text = _normalize_string(item)
        if not text or text in seen:
            continue
        seen.add(text)
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


def _infer_data_report_type(name: str, description: str = "") -> str:
    text = f"{_normalize_string(name)} {_normalize_string(description)}"
    if any(keyword in text for keyword in ("报表", "报告", "日报", "月报", "清单", "对账")):
        return "report"
    return "data"


def _normalize_name_description_items(value: Any) -> list[Dict[str, str]]:
    if value is None:
        return []
    raw_items = value if isinstance(value, list) else [value]
    items: list[Dict[str, str]] = []
    for raw_item in raw_items:
        if isinstance(raw_item, dict):
            name = _normalize_string(
                raw_item.get("name")
                or raw_item.get("module_name")
                or raw_item.get("title")
                or raw_item.get("scenario_name")
            )
            description = _normalize_string(
                raw_item.get("description")
                or raw_item.get("summary")
                or raw_item.get("desc")
                or raw_item.get("notes")
            )
        else:
            name = _normalize_string(raw_item)
            description = ""
        if not name and not description:
            continue
        if not name:
            name = description
            description = ""
        items.append({"name": name, "description": description})
    return items


def _normalize_data_report_items(value: Any) -> list[Dict[str, str]]:
    if value is None:
        return []
    raw_items = value if isinstance(value, list) else [value]
    items: list[Dict[str, str]] = []
    for raw_item in raw_items:
        if isinstance(raw_item, dict):
            name = _normalize_string(raw_item.get("name") or raw_item.get("title"))
            description = _normalize_string(
                raw_item.get("description") or raw_item.get("summary") or raw_item.get("notes")
            )
            item_type = _normalize_string(raw_item.get("type")).lower()
        else:
            name = _normalize_string(raw_item)
            description = ""
            item_type = ""
        if not name and not description:
            continue
        if not name:
            name = description
            description = ""
        normalized_type = item_type if item_type in {"data", "report"} else _infer_data_report_type(name, description)
        items.append({"name": name, "type": normalized_type, "description": description})
    return items


def _normalize_risk_items(value: Any) -> list[Dict[str, str]]:
    if value is None:
        return []
    raw_items = value if isinstance(value, list) else [value]
    items: list[Dict[str, str]] = []
    for raw_item in raw_items:
        if isinstance(raw_item, dict):
            name = _normalize_string(raw_item.get("name") or raw_item.get("title") or raw_item.get("description"))
            impact = _normalize_string(raw_item.get("impact") or raw_item.get("impact_level") or raw_item.get("notes"))
        else:
            name = _normalize_string(raw_item)
            impact = ""
        if not name and not impact:
            continue
        if not name:
            name = impact
            impact = ""
        items.append({"name": name, "impact": impact})
    return items


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


def _read_nested_payload_value(payload: Any, path: str) -> Any:
    cursor: Any = payload
    for part in str(path or "").split("."):
        if not isinstance(cursor, dict):
            return None
        cursor = cursor.get(part)
    return copy.deepcopy(cursor)


def _resolve_domain_canonical_value(domain: str, canonical_payload: Dict[str, Any], field_name: str) -> Any:
    exact_value = _read_nested_payload_value(canonical_payload, field_name)
    if exact_value is not None:
        return exact_value

    canonical_field_path = f"{domain}.canonical.{field_name}"
    for alias_path in get_field_path_aliases(canonical_field_path):
        if ".canonical." in alias_path:
            nested_path = alias_path.split(".canonical.", 1)[1]
        elif "." in alias_path:
            nested_path = alias_path.split(".", 1)[1]
        else:
            nested_path = alias_path
        alias_value = _read_nested_payload_value(canonical_payload, nested_path)
        if alias_value is not None:
            return alias_value
    return None


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
                target[field_name] = _normalize_extensions(_resolve_domain_canonical_value(domain, canonical, field_name))
                continue

            if domain == "technical_architecture" and field_name == "tech_stack":
                target[field_name] = _normalize_tech_stack(_resolve_domain_canonical_value(domain, canonical, field_name))
                continue

            if domain == "technical_architecture" and field_name == "performance_baseline":
                target[field_name] = _normalize_performance_baseline(_resolve_domain_canonical_value(domain, canonical, field_name))
                continue

            if field_name in _STRING_LIST_FIELDS.get(domain, set()):
                target[field_name] = _normalize_string_list(_resolve_domain_canonical_value(domain, canonical, field_name))
                continue

            if field_name in _STRUCTURED_LIST_FIELDS.get(domain, set()):
                if domain == "business_capabilities" and field_name == "data_reports":
                    target[field_name] = _normalize_data_report_items(_resolve_domain_canonical_value(domain, canonical, field_name))
                elif domain == "constraints_risks" and field_name == "risk_items":
                    target[field_name] = _normalize_risk_items(_resolve_domain_canonical_value(domain, canonical, field_name))
                else:
                    target[field_name] = _normalize_name_description_items(_resolve_domain_canonical_value(domain, canonical, field_name))
                continue

            if field_name in _GENERIC_LIST_FIELDS.get(domain, set()):
                target[field_name] = _normalize_generic_list(_resolve_domain_canonical_value(domain, canonical, field_name))
                continue

            if field_name in _STRING_FIELDS.get(domain, set()):
                target[field_name] = _normalize_string(_resolve_domain_canonical_value(domain, canonical, field_name))
                continue

            target[field_name] = copy.deepcopy(_resolve_domain_canonical_value(domain, canonical, field_name))

    return normalized


def _read_nested_value(value: Any, path: str) -> Any:
    cursor: Any = value
    for part in str(path or "").split("."):
        if not isinstance(cursor, dict):
            return None
        cursor = cursor.get(part)
    return copy.deepcopy(cursor)


def _unwrap_candidate_value(value: Any) -> Any:
    if isinstance(value, dict) and "value" in value:
        return copy.deepcopy(value.get("value"))
    return copy.deepcopy(value)


def _read_suggestion_by_field_path(suggestions: Any, field_path: str) -> Any:
    flat_path = str(field_path or "").strip()
    if not flat_path or not isinstance(suggestions, dict):
        return None
    for candidate_path in get_field_path_aliases(flat_path):
        if candidate_path in suggestions:
            return copy.deepcopy(suggestions.get(candidate_path))
        nested_value = _read_nested_value(suggestions, candidate_path)
        if nested_value is not None:
            return nested_value

    return None


def _normalize_card_content(content: Any) -> Dict[str, Any]:
    if not isinstance(content, dict):
        return {}
    result: Dict[str, Any] = {}
    for raw_key, raw_value in content.items():
        field_path = str(raw_key or "").strip()
        if not field_path:
            continue
        canonical_field_path = resolve_canonical_field_path(field_path)
        if not canonical_field_path:
            continue
        if field_path == canonical_field_path or canonical_field_path not in result:
            result[canonical_field_path] = copy.deepcopy(raw_value)
    return result


def normalize_card_baselines(value: Any) -> Dict[str, Dict[str, Any]]:
    raw_map = value if isinstance(value, dict) else {}
    normalized: Dict[str, Dict[str, Any]] = {}
    for raw_key, raw_value in raw_map.items():
        card_key = str(raw_key or "").strip()
        if card_key not in PROFILE_CARD_DEFINITIONS_BY_KEY:
            continue
        normalized[card_key] = _normalize_card_content(raw_value)
    return normalized


def get_card_keys_for_field_path(field_path: str) -> List[str]:
    normalized_path = resolve_canonical_field_path(field_path)
    return list(FIELD_PATH_TO_CARD_KEYS.get(normalized_path, []))


def _resolve_card_source_mode(content: Dict[str, Any], field_sources: Any) -> str:
    if not isinstance(field_sources, dict):
        return "none"
    modes: List[str] = []
    for field_path in content.keys():
        source_meta = field_sources.get(field_path)
        if not isinstance(source_meta, dict):
            continue
        source_name = _normalize_string(source_meta.get("source"))
        if source_name:
            modes.append(source_name)
    if not modes:
        return "none"
    if "manual" in modes:
        return "manual"
    if len(set(modes)) == 1:
        return modes[0]
    return "mixed"


def _resolve_card_source_summary(source_mode: str) -> str:
    return {
        "manual": "人工确认内容",
        "system_catalog": "高可信基础资料",
        "governance": "高可信基础资料",
        "document": "材料编译候选",
        "pm_document_ingest": "材料编译候选",
        "code_scan": "材料编译候选",
        "candidate": "材料编译候选",
        "mixed": "多来源融合",
        "none": "暂无来源",
    }.get(str(source_mode or "").strip(), "材料编译候选")


def _normalize_service_items(value: Any) -> List[Dict[str, Any]]:
    if not isinstance(value, list):
        return []
    items: List[Dict[str, Any]] = []
    for entry in value:
        if not isinstance(entry, dict):
            continue
        items.append(
            {
                "service_name": _normalize_string(entry.get("service_name") or entry.get("integration_name")),
                "transaction_name": _normalize_string(entry.get("transaction_name")),
                "scenario_code": _normalize_string(entry.get("scenario_code")),
                "peer_system": _normalize_string(entry.get("peer_system")),
                "status": _normalize_string(entry.get("status")),
                "notes": _normalize_string(entry.get("notes")),
                "exchange_object": _normalize_string(entry.get("exchange_object")),
                "exchange_mode": _normalize_string(entry.get("exchange_mode")),
                "schedule": _normalize_string(entry.get("schedule") or entry.get("trigger_cycle")),
            }
        )
    return items


def _normalize_extension_string(value: Any) -> str:
    return _normalize_string(value)


def _normalize_extension_list(value: Any) -> List[str]:
    return _normalize_string_list(value)


def _build_deployment_environment_summary(content: Dict[str, Any]) -> str:
    parts: List[str] = []

    cloud_deployment = _normalize_extension_string(
        content.get("technical_architecture.canonical.extensions.cloud_deployment")
    )
    if cloud_deployment:
        parts.append(f"云部署：{cloud_deployment}")

    network_zone = _normalize_extension_string(content.get("technical_architecture.canonical.network_zone"))
    if network_zone:
        parts.append(f"网络区域：{network_zone}")

    cluster_category = _normalize_extension_string(
        content.get("technical_architecture.canonical.extensions.cluster_category")
    )
    if cluster_category:
        parts.append(f"集群类型：{cluster_category}")

    virtualization_distribution = _normalize_extension_string(
        content.get("technical_architecture.canonical.extensions.virtualization_distribution")
    )
    if virtualization_distribution:
        parts.append(f"虚拟化分布：{virtualization_distribution}")

    internet_exit = _normalize_extension_string(
        content.get("technical_architecture.canonical.extensions.internet_exit")
    )
    if internet_exit:
        parts.append(f"互联网出口：{internet_exit}")

    return "；".join(parts)


def _build_performance_requirements_summary(baseline: Dict[str, Any]) -> Dict[str, str]:
    online = baseline.get("online") if isinstance(baseline.get("online"), dict) else {}
    batch = baseline.get("batch") if isinstance(baseline.get("batch"), dict) else {}
    return {
        "peak_tps": _normalize_string(online.get("peak_tps")),
        "p95_latency_ms": _normalize_string(online.get("p95_latency_ms")),
        "availability_target": _normalize_string(online.get("availability_target")),
        "batch_window": _normalize_string(batch.get("window")),
    }


def _build_card_summary(card_key: str, content: Dict[str, Any]) -> Dict[str, Any]:
    def pick(path: str) -> Any:
        return copy.deepcopy(content.get(path))

    if card_key == "system_identity":
        return {
            "system_type": _normalize_string(pick("system_positioning.canonical.system_type")),
            "lifecycle_status": _normalize_string(pick("system_positioning.canonical.lifecycle_status")),
            "system_aliases": _normalize_string_list(pick("system_positioning.canonical.system_aliases")),
        }
    if card_key == "business_affiliation":
        return {
            "business_domains": _normalize_string_list(pick("system_positioning.canonical.business_domains")),
            "business_lines": _normalize_string_list(pick("system_positioning.canonical.business_lines")),
        }
    if card_key == "application_hierarchy":
        return {
            "architecture_layer": _normalize_string(pick("system_positioning.canonical.architecture_layer")),
            "application_level": _normalize_string(pick("system_positioning.canonical.application_level")),
        }
    if card_key == "service_positioning":
        return {
            "target_users": _normalize_string_list(pick("system_positioning.canonical.target_users")),
            "core_responsibility": _normalize_string(pick("system_positioning.canonical.core_responsibility")),
        }
    if card_key == "capability_modules":
        return {
            "functional_modules": _normalize_name_description_items(
                pick("business_capabilities.canonical.functional_modules")
            ),
        }
    if card_key == "business_scenarios":
        return {
            "business_scenarios": _normalize_name_description_items(
                pick("business_capabilities.canonical.business_scenarios")
            ),
        }
    if card_key == "business_flows":
        return {
            "business_flows": _normalize_name_description_items(
                pick("business_capabilities.canonical.business_flows")
            ),
        }
    if card_key == "data_reports":
        return {
            "data_reports": _normalize_data_report_items(
                pick("business_capabilities.canonical.data_reports")
            ),
        }
    if card_key in {"provided_capabilities", "consumed_capabilities", "data_exchange_batch_links"}:
        field_path = {
            "provided_capabilities": "integration_interfaces.canonical.provided_services",
            "consumed_capabilities": "integration_interfaces.canonical.consumed_services",
            "data_exchange_batch_links": "integration_interfaces.canonical.other_integrations",
        }[card_key]
        return {"items": _normalize_service_items(pick(field_path))}
    if card_key == "architecture_deployment":
        return {
            "architecture_style": _normalize_string(pick("technical_architecture.canonical.architecture_style")),
            "deployment_mode": _normalize_extension_string(
                pick("technical_architecture.canonical.extensions.deployment_mode")
            ),
            "deployment_environment": _build_deployment_environment_summary(content),
            "topology_characteristics": _normalize_extension_list(
                pick("technical_architecture.canonical.extensions.topology_characteristics")
            ),
            "supplementary_notes": _normalize_extension_string(
                pick("technical_architecture.canonical.extensions.architecture_deployment_notes")
            ),
        }
    if card_key == "tech_stack_infrastructure":
        return {
            "tech_stack": _normalize_tech_stack(pick("technical_architecture.canonical.tech_stack")),
            "infrastructure_components": _normalize_extension_list(
                pick("technical_architecture.canonical.extensions.infrastructure_components")
            ),
            "supplementary_notes": _normalize_extension_string(
                pick("technical_architecture.canonical.extensions.technical_stack_notes")
            ),
        }
    if card_key == "design_characteristics":
        return {
            "design_methods": _normalize_extension_list(
                pick("technical_architecture.canonical.extensions.design_methods")
            ),
            "extensibility_features": _normalize_extension_list(
                pick("technical_architecture.canonical.extensions.extensibility_features")
            ),
            "common_capabilities": _normalize_extension_list(
                pick("technical_architecture.canonical.extensions.common_capabilities")
            ),
            "supplementary_notes": _normalize_extension_string(
                pick("technical_architecture.canonical.extensions.design_characteristics_notes")
            ),
        }
    if card_key == "quality_attributes":
        baseline = _normalize_performance_baseline(pick("technical_architecture.canonical.performance_baseline"))
        availability_design = _normalize_extension_list(
            pick("technical_architecture.canonical.extensions.availability_design")
        )
        monitoring_operations = _normalize_extension_list(
            pick("technical_architecture.canonical.extensions.monitoring_operations")
        )
        security_requirements = _normalize_extension_list(
            pick("technical_architecture.canonical.extensions.security_requirements")
        )
        dual_active = _normalize_string(pick("technical_architecture.canonical.extensions.dual_active"))
        dr_status = _normalize_string(pick("constraints_risks.canonical.extensions.dr_status"))
        dr_site = _normalize_string(pick("constraints_risks.canonical.extensions.dr_site"))
        if dual_active:
            availability_design.append(f"双活：{dual_active}")
        if dr_status:
            availability_design.append(f"容灾状态：{dr_status}")
        if dr_site:
            availability_design.append(f"容灾站点：{dr_site}")
        return {
            "performance_requirements": _build_performance_requirements_summary(baseline),
            "availability_design": _dedupe_strings(availability_design),
            "monitoring_operations": _dedupe_strings(monitoring_operations),
            "security_requirements": _dedupe_strings(security_requirements),
            "supplementary_notes": _normalize_extension_string(
                pick("technical_architecture.canonical.extensions.quality_attribute_notes")
            ),
        }
    if card_key == "business_constraints":
        return {
            "business_constraints": _normalize_name_description_items(
                pick("constraints_risks.canonical.business_constraints")
            ),
        }
    if card_key == "prerequisites":
        return {
            "prerequisites": _normalize_name_description_items(
                pick("constraints_risks.canonical.prerequisites")
            ),
        }
    if card_key == "sensitive_points":
        return {
            "sensitive_points": _normalize_name_description_items(
                pick("constraints_risks.canonical.sensitive_points")
            ),
        }
    if card_key == "risk_items":
        return {
            "risk_items": _normalize_risk_items(pick("constraints_risks.canonical.risk_items")),
        }
    return {}


def _build_card_payload(
    *,
    card_key: str,
    content: Dict[str, Any],
    field_sources: Any = None,
    baseline_content: Any = None,
) -> Dict[str, Any]:
    definition = PROFILE_CARD_DEFINITIONS_BY_KEY[card_key]
    normalized_content = _normalize_card_content(content)
    normalized_baseline = _normalize_card_content(baseline_content)
    source_mode = _resolve_card_source_mode(normalized_content, field_sources)
    return {
        "card_key": card_key,
        "domain_key": definition["domain_key"],
        "title": definition["title"],
        "content": normalized_content,
        "summary": _build_card_summary(card_key, normalized_content),
        "source_mode": source_mode,
        "source_summary": _resolve_card_source_summary(source_mode),
        "baseline_content": normalized_baseline,
        "baseline_summary": _build_card_summary(card_key, normalized_baseline),
        "editable": True,
        "edited": source_mode == "manual",
    }


def build_profile_cards(
    profile_data: Any,
    *,
    field_sources: Any = None,
    baselines: Any = None,
) -> Dict[str, Dict[str, Any]]:
    normalized_profile = normalize_profile_data(profile_data)
    normalized_baselines = normalize_card_baselines(baselines)
    cards: Dict[str, Dict[str, Any]] = {}
    for definition in PROFILE_CARD_DEFINITIONS:
        content: Dict[str, Any] = {}
        for field_path in definition["field_paths"]:
            value = get_field_value(normalized_profile, field_path)
            if has_non_empty_value(value):
                content[field_path] = value
        cards[definition["card_key"]] = _build_card_payload(
            card_key=definition["card_key"],
            content=content,
            field_sources=field_sources,
            baseline_content=normalized_baselines.get(definition["card_key"]),
        )
    return cards


def build_card_candidates(
    suggestions: Any,
    *,
    ignored_map: Any = None,
    profile_data: Any = None,
) -> Dict[str, Dict[str, Any]]:
    ignored = ignored_map if isinstance(ignored_map, dict) else {}
    normalized_profile = normalize_profile_data(profile_data)
    cards: Dict[str, Dict[str, Any]] = {}
    for definition in PROFILE_CARD_DEFINITIONS:
        content: Dict[str, Any] = {}
        for field_path in definition["field_paths"]:
            if field_path in ignored:
                continue
            raw_entry = _read_suggestion_by_field_path(suggestions, field_path)
            if raw_entry is None:
                continue
            value = _unwrap_candidate_value(raw_entry)
            if has_non_empty_value(value):
                current_value = get_field_value(normalized_profile, field_path)
                if has_non_empty_value(current_value) and current_value == value:
                    continue
                content[field_path] = value
        if content:
            cards[definition["card_key"]] = {
                **_build_card_payload(card_key=definition["card_key"], content=content),
                "source_mode": "candidate",
                "source_summary": "材料编译候选",
                "edited": False,
            }
    return cards


def build_domain_summary(
    profile_cards: Any,
    *,
    card_candidates: Any = None,
) -> Dict[str, Dict[str, Any]]:
    cards = profile_cards if isinstance(profile_cards, dict) else {}
    candidates = card_candidates if isinstance(card_candidates, dict) else {}
    result: Dict[str, Dict[str, Any]] = {}
    for domain_key in V27_DOMAIN_KEYS:
        card_keys = PROFILE_CARD_KEYS_BY_DOMAIN.get(domain_key, [])
        result[domain_key] = {
            "domain_key": domain_key,
            "title": DOMAIN_TITLES.get(domain_key, domain_key),
            "card_count": len(card_keys),
            "candidate_count": sum(1 for card_key in card_keys if card_key in candidates),
            "card_keys": list(card_keys),
            "has_content": any(
                card_key in cards and has_non_empty_value((cards.get(card_key) or {}).get("content"))
                for card_key in card_keys
            ),
        }
    return result


def apply_card_content_to_profile(profile_data: Any, card_content: Any) -> Dict[str, Any]:
    normalized = normalize_profile_data(profile_data)
    for field_path, value in _normalize_card_content(card_content).items():
        normalized = set_field_value(normalized, field_path, value)
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
    parts = resolve_canonical_field_path(field_path).split(".")
    cursor: Any = profile_data
    for part in parts:
        if not isinstance(cursor, dict):
            return None
        cursor = cursor.get(part)
    return copy.deepcopy(cursor)


def set_field_value(profile_data: Dict[str, Any], field_path: str, value: Any) -> Dict[str, Any]:
    normalized = normalize_profile_data(profile_data)
    parts = resolve_canonical_field_path(field_path).split(".")
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
