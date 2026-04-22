from __future__ import annotations

import copy
import json
import os
import re
import uuid
from typing import Any, Dict, List, Optional, Tuple

from backend.config.config import settings
from backend.service.document_parser import get_document_parser
from backend.service.document_text_cleaner import (
    clean_document_text,
    extract_clean_lines,
    looks_like_heading,
    looks_like_toc_entry,
    normalize_text,
    parsed_to_text,
)
from backend.service.memory_service import get_memory_service
from backend.service.profile_artifact_service import get_profile_artifact_service
from backend.service.profile_schema_service import (
    get_logical_field_key,
    has_non_empty_value,
    resolve_canonical_field_path,
)
from backend.service.profile_summary_service import get_profile_summary_service
from backend.service.runtime_execution_service import get_runtime_execution_service
from backend.service.skill_runtime_service import get_skill_runtime_service
from backend.service.system_profile_repository import get_system_profile_repository
from backend.service.system_profile_service import get_system_profile_service

SCENE_ID = "pm_document_ingest"
SNAPSHOT_VERSION = "document_ingest_v1"

TOPIC_KEYWORDS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("constraints", ("约束", "风险", "建议", "限制", "依赖", "合规", "安全", "窗口", "注意")),
    ("integration", ("接口", "集成", "对接", "调用", "报文", "数据流向", "同步", "异步", "服务方", "消费方", "渠道")),
    ("technical", ("架构", "部署", "技术栈", "高可用", "双活", "容灾", "网络", "性能", "并发", "缓存", "数据库", "中间件")),
    ("business", ("业务", "流程", "功能", "模块", "数据分析", "数据资产", "场景")),
    ("positioning", ("背景", "概述", "定位", "范围", "边界", "目标", "编写目的", "需求概述")),
)

TECH_STACK_PATTERNS: Dict[str, Tuple[Tuple[str, str], ...]] = {
    "languages": (
        ("Java", r"\bjava\b"),
        ("Python", r"\bpython\b"),
        ("Go", r"\bgo\b|golang"),
        ("JavaScript", r"javascript|\bnode\.?js\b"),
        ("TypeScript", r"typescript"),
        ("C#", r"c#|\.net"),
    ),
    "frameworks": (
        ("Spring Boot", r"spring\s*boot"),
        ("Spring Cloud", r"spring\s*cloud"),
        ("SOFA", r"\bsofa\b"),
        ("Vue", r"\bvue\b"),
        ("React", r"\breact\b"),
    ),
    "databases": (
        ("MySQL", r"\bmysql\b"),
        ("Oracle", r"\boracle\b"),
        ("PostgreSQL", r"postgresql"),
        ("SQL Server", r"sql\s*server"),
        ("DB2", r"\bdb2\b"),
    ),
    "middleware": (
        ("Redis", r"\bredis\b"),
        ("Kafka", r"\bkafka\b"),
        ("RabbitMQ", r"rabbitmq"),
        ("RocketMQ", r"rocketmq"),
        ("Nginx", r"\bnginx\b"),
        ("ESB", r"\besb\b"),
    ),
    "others": (
        ("Docker", r"\bdocker\b"),
        ("Kubernetes", r"\bkubernetes\b|\bk8s\b"),
        ("Linux", r"\blinux\b"),
    ),
}

DOC_TYPE_TARGET_FIELDS: Dict[str, Tuple[str, ...]] = {
    "requirements": (
        "system_positioning.canonical.core_responsibility",
        "business_capabilities.canonical.functional_modules",
        "business_capabilities.canonical.business_scenarios",
        "business_capabilities.canonical.business_flows",
        "business_capabilities.canonical.data_reports",
        "constraints_risks.canonical.business_constraints",
        "constraints_risks.canonical.prerequisites",
        "constraints_risks.canonical.sensitive_points",
        "constraints_risks.canonical.risk_items",
    ),
    "design": (
        "technical_architecture.canonical.architecture_style",
        "technical_architecture.canonical.tech_stack",
        "technical_architecture.canonical.network_zone",
        "technical_architecture.canonical.performance_baseline",
        "technical_architecture.canonical.extensions.deployment_mode",
        "technical_architecture.canonical.extensions.topology_characteristics",
        "technical_architecture.canonical.extensions.infrastructure_components",
        "technical_architecture.canonical.extensions.design_methods",
        "technical_architecture.canonical.extensions.extensibility_features",
        "technical_architecture.canonical.extensions.common_capabilities",
        "technical_architecture.canonical.extensions.availability_design",
        "technical_architecture.canonical.extensions.monitoring_operations",
        "technical_architecture.canonical.extensions.security_requirements",
    ),
    "tech_solution": (
        "integration_interfaces.canonical.other_integrations",
        "technical_architecture.canonical.architecture_style",
        "technical_architecture.canonical.tech_stack",
        "technical_architecture.canonical.network_zone",
        "technical_architecture.canonical.performance_baseline",
        "technical_architecture.canonical.extensions.deployment_mode",
        "technical_architecture.canonical.extensions.topology_characteristics",
        "technical_architecture.canonical.extensions.infrastructure_components",
        "technical_architecture.canonical.extensions.design_methods",
        "technical_architecture.canonical.extensions.extensibility_features",
        "technical_architecture.canonical.extensions.common_capabilities",
        "technical_architecture.canonical.extensions.availability_design",
        "technical_architecture.canonical.extensions.monitoring_operations",
        "technical_architecture.canonical.extensions.security_requirements",
        "constraints_risks.canonical.business_constraints",
        "constraints_risks.canonical.prerequisites",
        "constraints_risks.canonical.sensitive_points",
        "constraints_risks.canonical.risk_items",
    ),
}

DOC_TYPE_FILENAME_HINTS: Dict[str, Tuple[str, ...]] = {
    "requirements": ("requirement", "requirements", "需求", "prd", "spec"),
    "design": ("design", "概要设计", "详细设计", "设计"),
    "tech_solution": ("tech", "solution", "技术方案", "方案", "架构"),
}

DOC_TYPE_SIGNAL_KEYWORDS: Dict[str, Tuple[str, ...]] = {
    "requirements": ("负责", "范围", "边界", "功能", "模块", "流程", "数据资产", "服务"),
    "design": ("设计", "架构", "部署", "技术栈", "数据库", "中间件", "内网", "性能"),
    "tech_solution": ("接口", "对接", "集成", "调用", "报文", "服务编排", "技术方案", "约束", "风险"),
}

LLM_CANONICAL_FIELD_MAP: Dict[str, str] = {
    "system_positioning.system_description": "system_positioning.canonical.core_responsibility",
    "system_positioning.target_users": "system_positioning.canonical.target_users",
    "business_capabilities.module_structure": "business_capabilities.canonical.functional_modules",
    "business_capabilities.core_processes": "business_capabilities.canonical.business_flows",
    "integration_interfaces.integration_points": "integration_interfaces.canonical.other_integrations",
    "technical_architecture.architecture_positioning": "technical_architecture.canonical.architecture_style",
    "technical_architecture.tech_stack": "technical_architecture.canonical.tech_stack",
    "constraints_risks.key_constraints": "constraints_risks.canonical.prerequisites",
    "constraints_risks.known_risks": "constraints_risks.canonical.risk_items",
}

GENERIC_STRUCTURAL_LABELS = {
    "需求概述",
    "系统说明",
    "技术方案",
    "概要设计",
    "详细设计",
    "设计说明",
    "总体设计",
    "总体架构",
    "架构设计",
    "集成设计",
    "性能设计",
    "网络设计",
    "项目背景",
    "功能概述",
    "功能性需求要点",
    "名词解释",
    "概要说明",
    "假设及约束",
    "其它要求",
    "应用部署架构",
    "系统逻辑架构",
    "技术方案特点",
    "整体架构图",
    "架构图说明",
    "逻辑架构图",
    "逻辑架构说明",
    "数据流向说明",
    "数据备份方案",
    "数据清理方案",
    "数据恢复方案",
    "第一章 引言",
    "第二章 现有系统现状分析",
    "第三章 数据分析",
    "第四章 技术方案说明",
}

AUTHORITATIVE_ONLY_DOCUMENT_FIELDS = {
    "integration_interfaces.canonical.provided_services",
    "integration_interfaces.canonical.consumed_services",
}

POSITIONING_SECTION_TITLES = ("编写目的", "业务背景", "需求概述")
MAIN_FEATURE_SECTION_TITLES = ("主要功能说明", "功能模块说明", "主要模块说明", "功能性需求要点", "功能分类", "功能描述")
MAIN_FEATURE_SECTION_END_TITLES = (
    "工作说明",
    "非功能工作说明",
    "技术方案局限性",
    "实施方案",
    "实施阶段计划及工作量",
    "安全方案",
)
CONSTRAINT_SECTION_TITLES = ("假设及约束", "技术方案局限性")
RISK_SECTION_TITLES = ("实施风险",)
MODULE_SUBSECTION_TITLES = {
    "功能简述",
    "详细说明",
    "限制条件",
    "数据要求",
    "界面要求",
    "其他要求",
    "回单",
    "凭证样式",
    "移动互联网",
    "输入",
    "输出",
}
DESIGN_SECTION_TITLES = (
    "整体架构",
    "应用部署架构",
    "系统逻辑架构",
    "逻辑架构图",
    "技术方案特点",
    "性能分析",
    "高可用方案",
)
PERFORMANCE_SECTION_TITLES = ("性能分析",)
QUALITY_SECTION_TITLES = (
    "性能分析",
    "高可用方案",
    "数据高可用方案",
    "数据备份方案",
    "数据恢复方案",
    "安全策略方案",
    "安全方案",
    "非功能工作说明",
)
GENERIC_NOISE_SEGMENTS = {
    "技术方案建议书",
    "假设及约束",
    "安全策略方案",
    "实施风险",
    "功能性需求要点",
}
SECTION_CONTENT_SKIP_LABELS = {
    "整体架构图",
    "架构图说明",
    "逻辑架构图",
    "逻辑架构说明",
}
BOILERPLATE_PREFIXES = (
    "本技术方案建议书编写为了",
    "说明项目实施的前提条件与风险",
    "修订标志",
    "修改日期：",
    "修改后文档版本号：",
    "修改前文档版本号：",
)


def _dedupe_strings(items: List[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for item in items:
        text = normalize_text(item)
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _split_semantic_segments(line: str) -> List[str]:
    text = normalize_text(line)
    if not text:
        return []
    return [
        segment
        for segment in (normalize_text(part) for part in re.split(r"[；;。]", text))
        if len(segment) >= 4
    ]


def _classify_topic(text: str) -> Optional[str]:
    normalized = normalize_text(text)
    if not normalized:
        return None
    for topic, keywords in TOPIC_KEYWORDS:
        if any(keyword in normalized for keyword in keywords):
            return topic
    return None


def _looks_like_structural_label(line: str) -> bool:
    text = normalize_text(line)
    compact = text.replace(" ", "")
    if not text:
        return False
    if looks_like_toc_entry(text):
        return True
    if compact in GENERIC_STRUCTURAL_LABELS:
        return True
    if _normalize_heading_label(text) in set(POSITIONING_SECTION_TITLES + MAIN_FEATURE_SECTION_TITLES + MAIN_FEATURE_SECTION_END_TITLES):
        return True
    if _normalize_heading_label(text) in set(
        DESIGN_SECTION_TITLES
        + PERFORMANCE_SECTION_TITLES
        + QUALITY_SECTION_TITLES
        + CONSTRAINT_SECTION_TITLES
        + RISK_SECTION_TITLES
    ):
        return True
    if _normalize_heading_label(text) in MODULE_SUBSECTION_TITLES:
        return True
    if looks_like_heading(text) or looks_like_toc_entry(text):
        return True
    return False


def _ordered_unique_doc_types(doc_types: List[str]) -> List[str]:
    ordered: List[str] = []
    seen = set()
    for doc_type in DOC_TYPE_TARGET_FIELDS:
        if doc_type in doc_types and doc_type not in seen:
            ordered.append(doc_type)
            seen.add(doc_type)
    return ordered


def _normalize_heading_label(line: str) -> str:
    text = normalize_text(line)
    if not text:
        return ""
    text = re.sub(r"^\d+(?:\.\d+){0,5}\.?\s*", "", text)
    text = re.sub(r"^第[一二三四五六七八九十百零\d]+[章节篇]\s*", "", text)
    text = re.sub(r"\s+\d+$", "", text)
    return normalize_text(text)


def _line_matches_title(line: str, titles: Tuple[str, ...]) -> bool:
    if looks_like_toc_entry(line):
        return False
    label = _normalize_heading_label(line)
    return label in titles




def _bucket_lines(lines: List[str]) -> Dict[str, List[str]]:
    buckets: Dict[str, List[str]] = {
        "positioning": [],
        "business": [],
        "integration": [],
        "technical": [],
        "constraints": [],
    }
    active_topic: Optional[str] = None

    for line in lines:
        if looks_like_toc_entry(line):
            continue
        if looks_like_heading(line):
            active_topic = _classify_topic(line)
            continue

        topic = _classify_topic(line)
        if topic:
            buckets[topic].append(line)
            continue

        if active_topic:
            buckets[active_topic].append(line)

    return {topic: _dedupe_strings(items) for topic, items in buckets.items()}


def _contains_any(text: str, keywords: Tuple[str, ...]) -> bool:
    normalized = normalize_text(text)
    return any(keyword in normalized for keyword in keywords)


def _is_table_or_checklist_line(line: str) -> bool:
    text = normalize_text(line)
    if not text:
        return False
    if "□" in text:
        return True
    return "|" in text


def _is_boilerplate_line(line: str) -> bool:
    text = normalize_text(line)
    if not text:
        return False
    if text in GENERIC_NOISE_SEGMENTS:
        return True
    return any(text.startswith(prefix) for prefix in BOILERPLATE_PREFIXES)


def _is_semantic_line(line: str) -> bool:
    text = normalize_text(line)
    if not text:
        return False
    if _looks_like_structural_label(text):
        return False
    if _is_table_or_checklist_line(text):
        return False
    if _is_boilerplate_line(text):
        return False
    return True


def _extract_table_tail_value(line: str) -> str:
    text = normalize_text(line)
    if "|" not in text:
        return ""
    segments = [normalize_text(segment) for segment in text.split("|")]
    for segment in reversed(segments):
        if not segment:
            continue
        if "□" in segment:
            continue
        if _looks_like_structural_label(segment):
            continue
        return segment
    return ""


class DocumentSkillAdapter:
    ALLOWED_EXTENSIONS = {".doc", ".docx", ".pdf", ".pptx"}

    def __init__(self) -> None:
        self.document_parser = get_document_parser()
        self.runtime_service = get_skill_runtime_service()
        self.execution_service = get_runtime_execution_service()
        self.memory_service = get_memory_service()
        self.artifact_service = get_profile_artifact_service()
        self.repository = get_system_profile_repository()
        self.profile_service = get_system_profile_service()

    def _write_json_file(self, path: str, payload: Any) -> None:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def _write_jsonl_file(self, path: str, rows: List[Dict[str, Any]]) -> None:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False))
                f.write("\n")

    def _build_source_chunks(
        self,
        *,
        clean_lines: List[str],
        doc_type: str,
        file_name: str,
    ) -> List[Dict[str, Any]]:
        chunks: List[Dict[str, Any]] = []
        for index, line in enumerate(clean_lines, start=1):
            chunks.append(
                {
                    "chunk_id": f"chunk_{index:04d}",
                    "doc_type": str(doc_type or "").strip() or "unknown",
                    "file_name": str(file_name or "").strip() or "document",
                    "line_start": index,
                    "line_end": index,
                    "text": line,
                    "labels": [
                        label
                        for label, matched in (
                            ("heading", looks_like_heading(line)),
                            ("toc", looks_like_toc_entry(line)),
                        )
                        if matched
                    ],
                }
            )
        return chunks

    def _persist_source_bundle(
        self,
        *,
        system_id: str,
        system_name: str,
        doc_type: str,
        file_name: str,
        parsed_data: Any,
        text: str,
        raw_artifact: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        workspace_path, _ = self.repository.ensure_workspace(system_id=system_id, system_name=system_name)
        raw_meta_path = ""
        if isinstance(raw_artifact, dict):
            raw_meta_path = str(raw_artifact.get("meta_path") or "").strip()

        if raw_meta_path:
            source_dir = os.path.dirname(os.path.join(self.artifact_service.root_dir, raw_meta_path))
        else:
            source_dir = os.path.join(workspace_path, "source", "documents", f"src_doc_{uuid.uuid4().hex[:12]}")
            os.makedirs(source_dir, exist_ok=True)

        clean_lines = extract_clean_lines(text)
        chunks = self._build_source_chunks(clean_lines=clean_lines, doc_type=doc_type, file_name=file_name)
        parsed_payload = parsed_data if isinstance(parsed_data, (dict, list)) else {"text": text}

        parsed_path = os.path.join(source_dir, "parsed.json")
        chunks_path = os.path.join(source_dir, "chunks.jsonl")
        self._write_json_file(parsed_path, parsed_payload)
        self._write_jsonl_file(chunks_path, chunks)

        meta_path = os.path.join(source_dir, "meta.json")
        meta_payload = {}
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    meta_payload = loaded
            except Exception:
                meta_payload = {}
        meta_payload.update(
            {
                "system_id": system_id,
                "system_name": system_name,
                "doc_type": str(doc_type or "").strip() or "unknown",
                "file_name": str(file_name or "").strip() or "document",
                "line_count": len(clean_lines),
                "chunk_count": len(chunks),
            }
        )
        self._write_json_file(meta_path, meta_payload)

        return {
            "source_dir": source_dir,
            "clean_lines": clean_lines,
            "chunks": chunks,
            "parsed_payload": parsed_payload,
            "meta_path": meta_path,
        }

    def _build_llm_candidate_bundle(
        self,
        *,
        system_id: str,
        system_name: str,
        clean_text: str,
    ) -> Dict[str, Any]:
        if not normalize_text(clean_text):
            return {
                "llm_used": False,
                "relevant_domains": [],
                "related_systems": [],
                "suggestions": {},
                "error": None,
            }
        try:
            summary_service = get_profile_summary_service()
            llm_result = summary_service._call_llm(
                system_id=system_id,
                system_name=system_name,
                context=clean_text,
                llm_timeout=max(int(getattr(settings, "PROFILE_IMPORT_LLM_TIMEOUT", 5) or 5), 1),
                llm_retry_times=max(int(getattr(settings, "PROFILE_IMPORT_LLM_RETRY_TIMES", 1) or 1), 1),
                allow_chunking=bool(getattr(settings, "PROFILE_IMPORT_LLM_ALLOW_CHUNKING", False)),
            )
            return {
                "llm_used": True,
                "relevant_domains": list(llm_result.get("relevant_domains") or []),
                "related_systems": list(llm_result.get("related_systems") or []),
                "suggestions": llm_result.get("suggestions") if isinstance(llm_result.get("suggestions"), dict) else {},
                "error": None,
            }
        except Exception as exc:
            return {
                "llm_used": False,
                "relevant_domains": [],
                "related_systems": [],
                "suggestions": {},
                "error": str(exc),
            }

    def _flatten_llm_suggestions(self, suggestions: Dict[str, Any]) -> List[Tuple[str, Any]]:
        flattened: List[Tuple[str, Any]] = []

        def _walk(prefix: str, value: Any) -> None:
            if isinstance(value, dict):
                for key, nested in value.items():
                    next_prefix = f"{prefix}.{key}" if prefix else str(key or "").strip()
                    _walk(next_prefix, nested)
                return
            if value in ({}, [], "", None):
                return
            flattened.append((prefix, value))

        _walk("", suggestions if isinstance(suggestions, dict) else {})
        return flattened

    def _canonicalize_llm_field_path(self, field_path: str) -> str:
        normalized = str(field_path or "").strip()
        if not normalized:
            return ""
        return LLM_CANONICAL_FIELD_MAP.get(normalized, normalized)

    def _build_llm_candidate_entries(
        self,
        *,
        llm_bundle: Dict[str, Any],
        source_lines: Optional[List[str]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        entries: Dict[str, Dict[str, Any]] = {}
        for field_path, value in self._flatten_llm_suggestions(llm_bundle.get("suggestions") if isinstance(llm_bundle, dict) else {}):
            canonical_field_path = self._canonicalize_llm_field_path(field_path)
            if not canonical_field_path or not has_non_empty_value(value):
                continue
            if canonical_field_path in AUTHORITATIVE_ONLY_DOCUMENT_FIELDS:
                continue
            if canonical_field_path == "business_capabilities.canonical.functional_modules" and isinstance(value, list):
                normalized_modules = []
                for item in value:
                    if isinstance(item, dict):
                        module_name = normalize_text(item.get("module_name") or item.get("name"))
                        module_desc = normalize_text(item.get("description") or item.get("summary"))
                        if module_name or module_desc:
                            normalized_modules.append({"name": module_name or module_desc, "description": module_desc if module_name else ""})
                if normalized_modules:
                    value = normalized_modules
            if canonical_field_path == "technical_architecture.canonical.tech_stack" and not isinstance(value, dict):
                continue
            entries[canonical_field_path] = {
                "value": value,
                "confidence": 0.72,
                "reason": "llm_compile_projection",
                "source_anchors": self._build_source_anchors(source_lines, value),
            }
        return entries

    def _build_candidate_facts(
        self,
        *,
        system_id: str,
        system_name: str,
        raw_artifact_id: Optional[str],
        suggestions: Dict[str, Any],
        llm_bundle: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        facts: List[Dict[str, Any]] = []
        for field_path, payload in suggestions.items():
            if not isinstance(payload, dict):
                continue
            facts.append(
                {
                    "fact_id": f"fact_{uuid.uuid4().hex}",
                    "subject": {"type": "system", "id": system_id, "name": system_name},
                    "predicate": "profile_field",
                    "value": payload.get("value"),
                    "value_type": type(payload.get("value")).__name__,
                    "normalized_value": payload.get("value"),
                    "domain_tags": [str(field_path).split(".", 1)[0]],
                    "projection_hints": [field_path],
                    "confidence": payload.get("confidence"),
                    "evidence": payload.get("source_anchors") if isinstance(payload.get("source_anchors"), list) else [],
                    "source_refs": [raw_artifact_id] if raw_artifact_id else [],
                    "origin": "rule_compile",
                }
            )

        for field_path, value in self._flatten_llm_suggestions(llm_bundle.get("suggestions") if isinstance(llm_bundle, dict) else {}):
            facts.append(
                {
                    "fact_id": f"fact_{uuid.uuid4().hex}",
                    "subject": {"type": "system", "id": system_id, "name": system_name},
                    "predicate": "llm_inference",
                    "value": value,
                    "value_type": type(value).__name__,
                    "normalized_value": value,
                    "domain_tags": [str(field_path).split(".", 1)[0]],
                    "projection_hints": [field_path],
                    "confidence": 0.55,
                    "evidence": [],
                    "source_refs": [raw_artifact_id] if raw_artifact_id else [],
                    "origin": "llm_compile",
                }
            )

        return facts

    def _build_candidate_entity_graph(
        self,
        *,
        system_id: str,
        system_name: str,
        facts: List[Dict[str, Any]],
        llm_bundle: Dict[str, Any],
    ) -> Dict[str, Any]:
        domain_map: Dict[str, List[str]] = {}
        for fact in facts:
            for domain_tag in fact.get("domain_tags") or []:
                domain_map.setdefault(str(domain_tag), []).append(str(fact.get("fact_id") or ""))
        return {
            "system": {"system_id": system_id, "system_name": system_name},
            "domains": domain_map,
            "related_systems": list(llm_bundle.get("related_systems") or []),
            "fact_count": len(facts),
        }

    def _build_profile_projection(
        self,
        *,
        system_id: str,
        system_name: str,
        doc_type: str,
        compiled_doc_types: List[str],
        classification_scores: Dict[str, int],
        suggestions: Dict[str, Any],
        facts: List[Dict[str, Any]],
        llm_bundle: Dict[str, Any],
    ) -> Dict[str, Any]:
        candidates: Dict[str, Any] = {}
        fact_map: Dict[str, List[str]] = {}
        for fact in facts:
            for hint in fact.get("projection_hints") or []:
                fact_map.setdefault(str(hint), []).append(str(fact.get("fact_id") or ""))

        for field_path, payload in suggestions.items():
            candidates[field_path] = {
                "selected_value": payload.get("value") if isinstance(payload, dict) else payload,
                "confidence": payload.get("confidence") if isinstance(payload, dict) else None,
                "reason": payload.get("reason") if isinstance(payload, dict) else "",
                "source_anchors": payload.get("source_anchors") if isinstance(payload, dict) else [],
                "supporting_fact_ids": fact_map.get(field_path, []),
                "alternatives": [],
                "logical_field": payload.get("logical_field") if isinstance(payload, dict) else get_logical_field_key(field_path),
                "canonical_field_path": payload.get("canonical_field_path") if isinstance(payload, dict) else field_path,
                "validation_status": payload.get("validation_status") if isinstance(payload, dict) else "passed",
                "validation_reason": payload.get("validation_reason") if isinstance(payload, dict) else "semantic_gate_passed",
                "schema_version": payload.get("schema_version") if isinstance(payload, dict) else "logical_candidate_v1",
            }
        return {
            "system_id": system_id,
            "system_name": system_name,
            "doc_type": doc_type,
            "compiled_doc_types": compiled_doc_types,
            "classification_scores": classification_scores,
            "candidates": candidates,
            "llm_relevant_domains": list(llm_bundle.get("relevant_domains") or []),
            "llm_related_systems": list(llm_bundle.get("related_systems") or []),
        }

    def _build_candidate_dossier(
        self,
        *,
        system_id: str,
        system_name: str,
        doc_type: str,
        compiled_doc_types: List[str],
        classification_scores: Dict[str, int],
        source_chunks: List[Dict[str, Any]],
        llm_bundle: Dict[str, Any],
        facts: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        headings = [item.get("text") for item in source_chunks if "heading" in (item.get("labels") or [])][:20]
        return {
            "system_id": system_id,
            "system_name": system_name,
            "doc_type": doc_type,
            "compiled_doc_types": compiled_doc_types,
            "classification_scores": classification_scores,
            "headings": headings,
            "related_systems": list(llm_bundle.get("related_systems") or []),
            "relevant_domains": list(llm_bundle.get("relevant_domains") or []),
            "llm_domain_suggestions": llm_bundle.get("suggestions") if isinstance(llm_bundle.get("suggestions"), dict) else {},
            "open_fact_count": len(facts),
            "notes": {
                "llm_used": bool(llm_bundle.get("llm_used")),
                "llm_error": llm_bundle.get("error"),
            },
        }

    def _build_quality_report(
        self,
        *,
        target_fields: List[str],
        suggestions: Dict[str, Any],
        facts: List[Dict[str, Any]],
        llm_bundle: Dict[str, Any],
        rejected_candidates: Optional[List[Dict[str, Any]]] = None,
        section_analysis: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        missing_targets = [field for field in target_fields if field not in suggestions]
        low_confidence_fields = [
            field_path
            for field_path, payload in suggestions.items()
            if isinstance(payload, dict) and float(payload.get("confidence") or 0.0) < 0.6
        ]
        recognized_section_gaps: List[Dict[str, Any]] = []
        recognized = (section_analysis or {}).get("recognized_sections") if isinstance(section_analysis, dict) else {}
        if recognized.get("positioning_sections") and "system_positioning.canonical.core_responsibility" not in suggestions:
            recognized_section_gaps.append(
                {
                    "section_key": "positioning_sections",
                    "target_field": "system_positioning.canonical.core_responsibility",
                }
            )
        if recognized.get("main_feature_section") and "business_capabilities.canonical.functional_modules" not in suggestions:
            recognized_section_gaps.append(
                {
                    "section_key": "main_feature_section",
                    "target_field": "business_capabilities.canonical.functional_modules",
                }
            )
        if recognized.get("performance_section") and "technical_architecture.canonical.performance_baseline" not in suggestions:
            recognized_section_gaps.append(
                {
                    "section_key": "performance_section",
                    "target_field": "technical_architecture.canonical.performance_baseline",
                }
            )
        return {
            "target_field_count": len(target_fields),
            "suggestion_count": len(suggestions),
            "fact_count": len(facts),
            "missing_targets": missing_targets,
            "low_confidence_fields": low_confidence_fields,
            "recognized_section_gaps": recognized_section_gaps,
            "validator_failures": [
                {
                    "field_path": str(item.get("field_path") or "").strip(),
                    "logical_field": str(item.get("logical_field") or "").strip(),
                    "reason": str(item.get("reason") or "").strip(),
                }
                for item in (rejected_candidates or [])
                if isinstance(item, dict)
            ],
            "rejected_candidates": [
                copy.deepcopy(item)
                for item in (rejected_candidates or [])
                if isinstance(item, dict)
            ],
            "llm_used": bool(llm_bundle.get("llm_used")),
            "llm_error": llm_bundle.get("error"),
            "related_system_count": len(llm_bundle.get("related_systems") or []),
        }

    def _build_review_queue(
        self,
        *,
        quality_report: Dict[str, Any],
        llm_bundle: Dict[str, Any],
        suggestions: Dict[str, Any],
        section_analysis: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        queue: List[Dict[str, Any]] = []
        for field_path in quality_report.get("missing_targets") or []:
            queue.append(
                {
                    "priority": "medium",
                    "target_area": field_path,
                    "reason": "target_field_missing",
                    "recommended_action": "补充材料或人工填写该字段",
                    "evidence_refs": [],
                }
            )
        for field_path in quality_report.get("low_confidence_fields") or []:
            queue.append(
                {
                    "priority": "high",
                    "target_area": field_path,
                    "reason": "low_confidence_candidate",
                    "recommended_action": "人工确认候选值后再采纳",
                    "evidence_refs": suggestions.get(field_path, {}).get("source_anchors") if isinstance(suggestions.get(field_path), dict) else [],
                }
            )
        for gap in quality_report.get("recognized_section_gaps") or []:
            queue.append(
                {
                    "priority": "high",
                    "target_area": str(gap.get("target_field") or ""),
                    "reason": "recognized_section_without_candidate",
                    "recommended_action": f"已识别章节 {gap.get('section_key')}，但未产出对应候选，请检查章节抽取规则",
                    "evidence_refs": [],
                }
            )
        for rejected in quality_report.get("rejected_candidates") or []:
            if not isinstance(rejected, dict):
                continue
            queue.append(
                {
                    "priority": "high",
                    "target_area": str(rejected.get("field_path") or ""),
                    "reason": str(rejected.get("reason") or "").strip() or "semantic_gate_rejected",
                    "recommended_action": "检查章节抽取与字段语义规则，必要时人工补充该字段",
                    "evidence_refs": rejected.get("source_anchors") if isinstance(rejected.get("source_anchors"), list) else [],
                }
            )
        if llm_bundle.get("error"):
            queue.append(
                {
                    "priority": "medium",
                    "target_area": "candidate_compile",
                    "reason": "llm_compile_failed",
                    "recommended_action": "保留规则候选，同时检查 LLM 配置后重试",
                    "evidence_refs": [],
                }
            )
        for system_name in llm_bundle.get("related_systems") or []:
            queue.append(
                {
                    "priority": "high",
                    "target_area": "multi_system_content",
                    "reason": "related_system_detected",
                    "recommended_action": f"确认该材料是否混入系统 {system_name} 的内容",
                    "evidence_refs": [],
                }
            )
        return queue

    def _persist_candidate_bundle(
        self,
        *,
        system_id: str,
        candidate_artifact_id: str,
        source_manifest: Dict[str, Any],
        facts: List[Dict[str, Any]],
        entity_graph: Dict[str, Any],
        profile_projection: Dict[str, Any],
        dossier: Dict[str, Any],
        quality_report: Dict[str, Any],
        review_queue: List[Dict[str, Any]],
    ) -> Dict[str, str]:
        file_payloads = {
            "source_manifest.json": source_manifest,
            "entity_graph.json": entity_graph,
            "profile_projection.json": profile_projection,
            "dossier.json": dossier,
            "quality_report.json": quality_report,
            "review_queue.json": review_queue,
        }
        written_paths: Dict[str, str] = {}
        for name, payload in file_payloads.items():
            written_paths[name] = self.artifact_service.write_candidate_support_file(
                system_id=system_id,
                category="documents",
                artifact_id=candidate_artifact_id,
                file_name=name,
                payload=payload,
            )

        written_paths["facts.jsonl"] = self.artifact_service.write_candidate_support_file(
            system_id=system_id,
            category="documents",
            artifact_id=candidate_artifact_id,
            file_name="facts.jsonl",
            payload=facts,
        )
        return written_paths

    def _flatten_anchor_terms(self, value: Any) -> List[str]:
        terms: List[str] = []

        def _walk(item: Any) -> None:
            if isinstance(item, dict):
                for nested in item.values():
                    _walk(nested)
                return
            if isinstance(item, (list, tuple, set)):
                for nested in item:
                    _walk(nested)
                return
            text = normalize_text(item)
            if text:
                terms.append(text)

        _walk(value)
        return _dedupe_strings(terms)

    def _build_source_anchors(self, lines: Optional[List[str]], value: Any, *, limit: int = 3) -> List[Dict[str, Any]]:
        source_lines = [normalize_text(line) for line in (lines or []) if normalize_text(line)]
        anchor_terms = [
            normalize_text(term).lower()
            for term in self._flatten_anchor_terms(value)
            if len(normalize_text(term)) >= 2
        ]
        if not source_lines or not anchor_terms:
            return []

        anchors: List[Dict[str, Any]] = []
        seen_snippets = set()
        for index, line in enumerate(source_lines, start=1):
            normalized_line = line.lower()
            if not any(term in normalized_line for term in anchor_terms):
                continue
            if line in seen_snippets:
                continue
            seen_snippets.add(line)
            anchors.append(
                {
                    "line_start": index,
                    "line_end": index,
                    "snippet": line,
                }
            )
            if len(anchors) >= limit:
                break
        return anchors

    def _build_payload(
        self,
        *,
        value: Any,
        skill_id: str,
        reason: str,
        confidence: float = 0.82,
        source_lines: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        return {
            "value": value,
            "scene_id": SCENE_ID,
            "skill_id": skill_id,
            "decision_policy": "suggestion_only",
            "confidence": confidence,
            "reason": reason,
            "source_anchors": self._build_source_anchors(source_lines, value),
        }

    def _annotate_candidate_payload(
        self,
        *,
        field_path: str,
        payload: Dict[str, Any],
        validation_status: str,
        validation_reason: str,
    ) -> Dict[str, Any]:
        canonical_field_path = resolve_canonical_field_path(field_path)
        annotated = dict(payload)
        annotated["logical_field"] = get_logical_field_key(canonical_field_path)
        annotated["canonical_field_path"] = canonical_field_path
        annotated["validation_status"] = validation_status
        annotated["validation_reason"] = validation_reason
        annotated["schema_version"] = "logical_candidate_v1"
        return annotated

    def _looks_like_document_purpose_text(self, value: Any) -> bool:
        text = normalize_text(value)
        if not text:
            return True
        return any(
            token in text
            for token in (
                "本文档编写的目的",
                "本文档编写目的是",
                "本需求说明书",
                "本技术方案建议书",
                "使用对象不限于",
                "用于指引后续的人员开发设计系统使用",
            )
        )

    def _is_invalid_module_name(self, value: Any) -> bool:
        text = normalize_text(value)
        if not text:
            return True
        if text in MODULE_SUBSECTION_TITLES or text in MAIN_FEATURE_SECTION_TITLES or text in MAIN_FEATURE_SECTION_END_TITLES:
            return True
        if text in GENERIC_STRUCTURAL_LABELS:
            return True
        if text in {"编写目的", "业务背景", "需求概述", "其他要求", "其它要求", "名词解释"}:
            return True
        if looks_like_toc_entry(text) or _looks_like_structural_label(text):
            return True
        return False

    def _normalize_named_entries_for_gate(self, value: Any) -> List[Dict[str, str]]:
        if isinstance(value, list):
            raw_items = value
        else:
            raw_items = [value]

        normalized: List[Dict[str, str]] = []
        for raw_item in raw_items:
            if isinstance(raw_item, dict):
                name = normalize_text(
                    raw_item.get("name")
                    or raw_item.get("module_name")
                    or raw_item.get("title")
                    or raw_item.get("scenario_name")
                )
                description = normalize_text(
                    raw_item.get("description")
                    or raw_item.get("summary")
                    or raw_item.get("notes")
                )
            else:
                name = normalize_text(raw_item)
                description = ""
            if not name and not description:
                continue
            if not name:
                name = description
                description = ""
            normalized.append({"name": name, "description": description})
        return normalized

    def _apply_semantic_gate(self, suggestions: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        accepted: Dict[str, Any] = {}
        rejected: List[Dict[str, Any]] = []

        for raw_field_path, raw_payload in suggestions.items():
            field_path = resolve_canonical_field_path(raw_field_path)
            payload = raw_payload if isinstance(raw_payload, dict) else {"value": raw_payload}
            value = copy.deepcopy(payload.get("value"))
            rejection_reason = ""

            if field_path == "system_positioning.canonical.core_responsibility":
                text = normalize_text(value)
                if self._looks_like_document_purpose_text(text):
                    rejection_reason = "document_purpose_noise"
                elif not _contains_any(text, ("负责", "提供", "用于", "支持", "服务")) and not any(token in text for token in ("系统", "平台")):
                    rejection_reason = "weak_scope_semantics"
            elif field_path in {
                "business_capabilities.canonical.functional_modules",
                "business_capabilities.canonical.business_scenarios",
            }:
                items = []
                for item in self._normalize_named_entries_for_gate(value):
                    if self._is_invalid_module_name(item.get("name")):
                        continue
                    if self._looks_like_document_purpose_text(item.get("description")):
                        continue
                    items.append(item)
                if not items:
                    rejection_reason = "module_entities_not_found"
                else:
                    value = items
            elif field_path == "business_capabilities.canonical.business_flows":
                items = []
                for item in self._normalize_named_entries_for_gate(value):
                    text = f"{item.get('name', '')} {item.get('description', '')}"
                    if self._is_invalid_module_name(item.get("name")):
                        continue
                    if not _contains_any(text, ("流程", "处理", "步骤", "环节", "调用", "批量", "记账", "对账")):
                        continue
                    items.append(item)
                if not items:
                    rejection_reason = "business_flow_semantics_missing"
                else:
                    value = items
            elif field_path == "business_capabilities.canonical.data_reports":
                items = []
                for item in self._normalize_named_entries_for_gate(value):
                    text = f"{item.get('name', '')} {item.get('description', '')}"
                    if self._is_invalid_module_name(item.get("name")):
                        continue
                    if not _contains_any(text, ("数据", "台账", "流水", "报表", "对账", "清单", "报告")):
                        continue
                    items.append(item)
                if not items:
                    rejection_reason = "data_report_semantics_missing"
                else:
                    value = [
                        {
                            "name": item["name"],
                            "type": "report" if _contains_any(f"{item['name']} {item['description']}", ("报表", "报告", "清单", "对账")) else "data",
                            "description": item["description"],
                        }
                        for item in items
                    ]

            if rejection_reason:
                rejected.append(
                    {
                        "field_path": field_path,
                        "logical_field": get_logical_field_key(field_path),
                        "reason": rejection_reason,
                        "value": copy.deepcopy(payload.get("value")),
                        "source_anchors": copy.deepcopy(payload.get("source_anchors")) if isinstance(payload.get("source_anchors"), list) else [],
                    }
                )
                continue

            next_payload = dict(payload)
            next_payload["value"] = value
            accepted[field_path] = self._annotate_candidate_payload(
                field_path=field_path,
                payload=next_payload,
                validation_status="passed",
                validation_reason="semantic_gate_passed",
            )

        return accepted, rejected

    def _match_inline_module_summary(self, line: str) -> Optional[Tuple[str, str]]:
        text = normalize_text(line)
        if not text or _looks_like_structural_label(text) or _is_table_or_checklist_line(text):
            return None
        matched = re.match(r"^([^：:]{2,24})[：:]\s*(.+)$", text)
        if not matched:
            return None
        module_name = normalize_text(matched.group(1))
        summary = normalize_text(matched.group(2))
        if not module_name or not summary:
            return None
        if module_name in MODULE_SUBSECTION_TITLES:
            return None
        return module_name, summary

    def _extract_section_contents(self, lines: List[str], section_titles: Tuple[str, ...]) -> List[str]:
        contents: List[str] = []
        for index, line in enumerate(lines):
            if not _line_matches_title(line, section_titles):
                continue
            pointer = index + 1
            while pointer < len(lines):
                current = normalize_text(lines[pointer])
                if not current:
                    pointer += 1
                    continue
                if looks_like_toc_entry(current):
                    pointer += 1
                    continue
                if _normalize_heading_label(current) in SECTION_CONTENT_SKIP_LABELS:
                    pointer += 1
                    continue
                if _looks_like_structural_label(current):
                    break
                contents.append(current)
                pointer += 1
        return _dedupe_strings(contents)

    def _is_module_heading(self, line: str, next_line: str) -> bool:
        text = normalize_text(line)
        next_text = normalize_text(next_line)
        if not text:
            return False
        if looks_like_toc_entry(text):
            return False
        if text in MODULE_SUBSECTION_TITLES or text in MAIN_FEATURE_SECTION_TITLES or text in MAIN_FEATURE_SECTION_END_TITLES:
            return False
        if len(text) > 24:
            return False
        if any(token in text for token in (":", "：", "|")):
            return False
        if _looks_like_structural_label(text):
            return False
        return _normalize_heading_label(next_text) in MODULE_SUBSECTION_TITLES

    def _extract_main_feature_modules(self, lines: List[str]) -> Tuple[List[str], List[str], List[str]]:
        start_indices = [idx for idx, line in enumerate(lines) if _line_matches_title(line, MAIN_FEATURE_SECTION_TITLES)]
        if not start_indices:
            return [], [], []

        best_modules: List[str] = []
        best_scenarios: List[str] = []
        best_process_items: List[str] = []
        best_score = -1

        for start_index in start_indices:
            modules: List[str] = []
            scenarios: List[str] = []
            process_items: List[str] = []
            index = start_index + 1
            while index < len(lines):
                current = normalize_text(lines[index])
                if not current:
                    index += 1
                    continue
                if looks_like_toc_entry(current):
                    index += 1
                    continue

                normalized_current = _normalize_heading_label(current)
                if normalized_current in MAIN_FEATURE_SECTION_END_TITLES:
                    break
                if modules and normalized_current in MAIN_FEATURE_SECTION_TITLES:
                    break
                if modules and _looks_like_structural_label(current) and normalized_current not in MODULE_SUBSECTION_TITLES:
                    break

                inline_module = self._match_inline_module_summary(current)
                if inline_module:
                    module_name, summary = inline_module
                    modules.append(module_name)
                    scenarios.append(f"{module_name}：{summary}")
                    if _contains_any(summary, ("流程", "处理", "步骤", "环节", "调用", "批量", "记账", "对账")):
                        process_items.append(f"{module_name}：{summary}")
                    index += 1
                    continue

                next_line = lines[index + 1] if index + 1 < len(lines) else ""
                if not self._is_module_heading(current, next_line):
                    index += 1
                    continue

                module_name = current
                modules.append(module_name)
                summary = ""
                detail_clues: List[str] = []
                pointer = index + 1
                while pointer < len(lines):
                    candidate = normalize_text(lines[pointer])
                    if not candidate:
                        pointer += 1
                        continue
                    if looks_like_toc_entry(candidate):
                        pointer += 1
                        continue
                    normalized_candidate = _normalize_heading_label(candidate)
                    if normalized_candidate in MAIN_FEATURE_SECTION_END_TITLES:
                        break
                    if self._is_module_heading(candidate, lines[pointer + 1] if pointer + 1 < len(lines) else ""):
                        break
                    if normalized_candidate in MODULE_SUBSECTION_TITLES:
                        pointer += 1
                        continue
                    if candidate.startswith(("输入：", "输出：")):
                        pointer += 1
                        continue
                    if _looks_like_structural_label(candidate) and normalized_candidate not in MODULE_SUBSECTION_TITLES:
                        break
                    if not summary and _is_semantic_line(candidate):
                        summary = candidate
                    if _is_semantic_line(candidate) and _contains_any(
                        candidate, ("流程", "处理", "步骤", "环节", "调用", "批量", "记账", "对账")
                    ):
                        detail_clues.append(candidate)
                    pointer += 1

                if summary:
                    scenarios.append(f"{module_name}：{summary}")
                for item in detail_clues[:2]:
                    process_items.append(f"{module_name}：{item}")
                index = max(pointer, index + 1)

            score = len(_dedupe_strings(modules)) * 10 + len(_dedupe_strings(scenarios)) * 3 + len(_dedupe_strings(process_items))
            if score > best_score:
                best_score = score
                best_modules = modules
                best_scenarios = scenarios
                best_process_items = process_items

        return _dedupe_strings(best_modules), _dedupe_strings(best_scenarios), _dedupe_strings(best_process_items)

    def _analyze_document_sections(self, lines: List[str]) -> Dict[str, Any]:
        positioning_lines = self._extract_section_contents(lines, POSITIONING_SECTION_TITLES)
        design_lines = self._extract_section_contents(lines, DESIGN_SECTION_TITLES)
        performance_lines = self._extract_section_contents(lines, PERFORMANCE_SECTION_TITLES)
        quality_lines = self._extract_section_contents(lines, QUALITY_SECTION_TITLES)
        module_titles, module_scenarios, module_processes = self._extract_main_feature_modules(lines)
        return {
            "recognized_sections": {
                "positioning_sections": bool(positioning_lines),
                "main_feature_section": bool(module_titles or any(_line_matches_title(line, MAIN_FEATURE_SECTION_TITLES) for line in lines)),
                "design_sections": bool(design_lines),
                "performance_section": bool(performance_lines),
                "quality_section": bool(quality_lines),
            },
            "positioning_lines": positioning_lines,
            "design_lines": design_lines,
            "performance_lines": performance_lines,
            "quality_lines": quality_lines,
            "module_titles": module_titles,
            "module_scenarios": module_scenarios,
            "module_processes": module_processes,
        }

    def _expand_compiled_doc_types(
        self,
        *,
        compiled_doc_types: List[str],
        clean_lines: List[str],
        primary_doc_type: str,
    ) -> List[str]:
        expanded = _ordered_unique_doc_types(compiled_doc_types)
        if primary_doc_type != "tech_solution":
            return expanded
        section_analysis = self._analyze_document_sections(clean_lines)
        recognized = section_analysis.get("recognized_sections") if isinstance(section_analysis, dict) else {}
        if recognized.get("positioning_sections") or recognized.get("main_feature_section"):
            expanded = _ordered_unique_doc_types(expanded + ["requirements"])
        if recognized.get("design_sections") or recognized.get("performance_section") or recognized.get("quality_section"):
            expanded = _ordered_unique_doc_types(expanded + ["design"])
        return expanded

    def _build_compile_plan(self, requested_doc_type: str, file_name: str, text: str) -> Dict[str, Any]:
        normalized_doc_type = str(requested_doc_type or "").strip().lower()
        clean_lines = extract_clean_lines(text)

        if normalized_doc_type in DOC_TYPE_TARGET_FIELDS:
            compiled_doc_types = self._expand_compiled_doc_types(
                compiled_doc_types=[normalized_doc_type],
                clean_lines=clean_lines,
                primary_doc_type=normalized_doc_type,
            )
            return {
                "resolved_doc_type": normalized_doc_type,
                "primary_doc_type": normalized_doc_type,
                "compiled_doc_types": compiled_doc_types,
                "classification_scores": self._score_doc_types(file_name, text),
            }

        return self._resolve_compile_plan(file_name, text)

    def _score_doc_types(self, file_name: str, text: str) -> Dict[str, int]:
        scores = {doc_type: 0 for doc_type in DOC_TYPE_TARGET_FIELDS}
        normalized_file_name = str(file_name or "").strip().lower()
        clean_lines = extract_clean_lines(text)
        clean_text = "\n".join(clean_lines)
        buckets = _bucket_lines(clean_lines)

        for doc_type, hints in DOC_TYPE_FILENAME_HINTS.items():
            if any(hint.lower() in normalized_file_name for hint in hints):
                scores[doc_type] += 5

        for doc_type, keywords in DOC_TYPE_SIGNAL_KEYWORDS.items():
            scores[doc_type] += sum(1 for keyword in keywords if keyword in clean_text)

        if buckets["positioning"] or buckets["business"]:
            scores["requirements"] += 1
        if buckets["technical"]:
            scores["design"] += 1
        if buckets["integration"]:
            scores["tech_solution"] += 2
        if buckets["constraints"]:
            scores["requirements"] += 1
            scores["tech_solution"] += 1

        return scores

    def _resolve_compile_plan(self, file_name: str, text: str) -> Dict[str, Any]:
        scores = self._score_doc_types(file_name, text)
        clean_lines = extract_clean_lines(text)
        ranked = sorted(
            scores.items(),
            key=lambda item: (-int(item[1] or 0), item[0]),
        )
        positive = [(doc_type, score) for doc_type, score in ranked if score > 0]

        if not positive:
            compiled_doc_types = list(DOC_TYPE_TARGET_FIELDS.keys())
            compiled_doc_types = self._expand_compiled_doc_types(
                compiled_doc_types=compiled_doc_types,
                clean_lines=clean_lines,
                primary_doc_type="tech_solution",
            )
            return {
                "resolved_doc_type": "general",
                "primary_doc_type": "tech_solution",
                "compiled_doc_types": compiled_doc_types,
                "classification_scores": scores,
            }

        top_doc_type, top_score = positive[0]
        second_score = positive[1][1] if len(positive) > 1 else -1
        if len(positive) > 1 and top_score - second_score <= 1:
            compiled_doc_types = self._expand_compiled_doc_types(
                compiled_doc_types=[doc_type for doc_type, _ in positive],
                clean_lines=clean_lines,
                primary_doc_type=top_doc_type,
            )
            return {
                "resolved_doc_type": "general",
                "primary_doc_type": top_doc_type,
                "compiled_doc_types": compiled_doc_types,
                "classification_scores": scores,
            }

        compiled_doc_types = self._expand_compiled_doc_types(
            compiled_doc_types=[top_doc_type],
            clean_lines=clean_lines,
            primary_doc_type=top_doc_type,
        )
        return {
            "resolved_doc_type": top_doc_type,
            "primary_doc_type": top_doc_type,
            "compiled_doc_types": compiled_doc_types,
            "classification_scores": scores,
        }

    def _extract_scope_text(self, lines: List[str]) -> str:
        semantic_lines = [line for line in lines if _is_semantic_line(line)]
        keywords = ("范围", "提供", "负责", "用于", "支持", "服务")
        for line in semantic_lines:
            if _contains_any(line, keywords):
                return line
        for line in semantic_lines:
            if "系统" in line or "平台" in line:
                return line
        return ""

    def _extract_boundary_items(self, lines: List[str]) -> List[str]:
        items: List[str] = []
        for line in lines:
            for segment in _split_semantic_segments(line):
                if _contains_any(segment, ("边界", "不处理", "不包括", "仅负责", "限定")):
                    items.append(segment)
        return _dedupe_strings(items)[:5]

    def _build_named_entries(self, items: List[str]) -> List[Dict[str, str]]:
        entries: List[Dict[str, str]] = []
        for item in items:
            normalized_item = normalize_text(item)
            if not normalized_item:
                continue
            inline = self._match_inline_module_summary(normalized_item)
            if inline:
                name, description = inline
            else:
                name = normalized_item.rstrip("：:")
                description = ""
            entries.append({"name": name, "description": description})
        return entries

    def _build_data_report_entries(self, items: List[str]) -> List[Dict[str, str]]:
        entries: List[Dict[str, str]] = []
        for item in items:
            normalized_item = normalize_text(item)
            if not normalized_item:
                continue
            inline = self._match_inline_module_summary(normalized_item)
            report_source_text = normalized_item
            if inline:
                name, description = inline
                report_source_text = description or normalized_item
            else:
                description = normalized_item.rstrip("：:")
                name = normalized_item.rstrip("：:")
            report_match = re.search(
                r"([\u4e00-\u9fa5A-Za-z0-9_-]+(?:台账|流水|报表|清单|报告|对账文件生成))",
                report_source_text,
            )
            if "对账文件生成" in report_source_text:
                name = "对账文件生成"
            elif report_match:
                name = normalize_text(report_match.group(1))
            item_type = "report" if _contains_any(f"{name} {description}", ("报表", "报告", "清单", "对账")) else "data"
            entries.append({"name": name, "type": item_type, "description": description})
        return entries

    def _build_risk_items(self, items: List[str]) -> List[Dict[str, str]]:
        entries: List[Dict[str, str]] = []
        for item in items:
            normalized_item = normalize_text(item)
            if not normalized_item:
                continue
            if "，" in normalized_item:
                name, impact = normalized_item.split("，", 1)
            elif "," in normalized_item:
                name, impact = normalized_item.split(",", 1)
            else:
                name, impact = normalized_item, ""
            normalized_impact = normalize_text(impact)
            if normalized_impact and not normalized_impact.endswith(("。", "！", "？")):
                normalized_impact = f"{normalized_impact}。"
            entries.append({"name": normalize_text(name), "impact": normalized_impact})
        return entries

    def _extract_keyword_segments(
        self,
        lines: List[str],
        *,
        include_keywords: Tuple[str, ...],
        exclude_keywords: Tuple[str, ...] = (),
        limit: int = 5,
    ) -> List[str]:
        items: List[str] = []
        semantic_lines = [line for line in lines if _is_semantic_line(line)]
        for line in semantic_lines:
            for segment in _split_semantic_segments(line):
                if include_keywords and (not _contains_any(segment, include_keywords)):
                    continue
                if exclude_keywords and _contains_any(segment, exclude_keywords):
                    continue
                if segment in GENERIC_NOISE_SEGMENTS or segment in MODULE_SUBSECTION_TITLES:
                    continue
                if _is_table_or_checklist_line(segment) or _is_boilerplate_line(segment):
                    continue
                items.append(segment)
        return _dedupe_strings(items)[:limit]

    def _extract_integration_items(
        self,
        lines: List[str],
        *,
        module_titles: Optional[List[str]] = None,
        module_scenarios: Optional[List[str]] = None,
    ) -> List[str]:
        semantic_lines = [line for line in lines if _is_semantic_line(line)]
        known_modules = {normalize_text(title) for title in (module_titles or []) if normalize_text(title)}
        excluded_segments = set()
        for item in module_scenarios or []:
            text = normalize_text(item)
            if not text:
                continue
            excluded_segments.add(text)
            if "：" in text:
                excluded_segments.add(normalize_text(text.split("：", 1)[1]))
        items: List[str] = []
        for line in semantic_lines:
            if normalize_text(line) in excluded_segments:
                continue
            inline_module = self._match_inline_module_summary(line)
            if inline_module and inline_module[0] in known_modules:
                continue
            for segment in _split_semantic_segments(line):
                if not _contains_any(segment, ("接口", "集成", "对接", "服务", "调用", "报文", "数据流向", "核心系统", "数据仓库")):
                    continue
                if normalize_text(segment) in excluded_segments:
                    continue
                if _is_table_or_checklist_line(segment) or _is_boilerplate_line(segment):
                    continue
                items.append(segment)
        return _dedupe_strings(items)[:6]

    def _extract_architecture_style(self, lines: List[str]) -> str:
        semantic_lines = [line for line in lines if _is_semantic_line(line)]
        priority_keywords = ("架构", "部署", "双活", "分层", "微服务", "容灾", "集群")
        for line in semantic_lines:
            if _contains_any(line, priority_keywords) and "技术栈" not in line:
                return line
        return ""

    def _extract_network_zone(self, lines: List[str]) -> str:
        for line in lines:
            if not _is_semantic_line(line):
                continue
            if _contains_any(line, ("内网", "内联网", "内联网关", "外网", "DMZ", "专线", "生产区", "互联网区", "核心区")):
                return line
        return ""

    def _extract_tech_stack(self, text: str) -> Dict[str, List[str]]:
        normalized_text = str(text or "")
        tech_stack: Dict[str, List[str]] = {
            "languages": [],
            "frameworks": [],
            "databases": [],
            "middleware": [],
            "others": [],
        }

        for group, patterns in TECH_STACK_PATTERNS.items():
            for label, pattern in patterns:
                if re.search(pattern, normalized_text, re.IGNORECASE):
                    tech_stack[group].append(label)

        return tech_stack

    def _extract_performance_baseline(self, lines: List[str], text: str) -> Optional[Dict[str, Any]]:
        baseline: Dict[str, Any] = {
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
        }

        semantic_lines = [line for line in lines if _is_semantic_line(line)]
        if not semantic_lines:
            return None

        joined = "\n".join(semantic_lines) if semantic_lines else str(text or "")

        peak_match = re.search(r"(\d+(?:\.\d+)?)\s*(TPS|QPS)", joined, re.IGNORECASE)
        if peak_match:
            baseline["online"]["peak_tps"] = f"{peak_match.group(1)} {peak_match.group(2).upper()}"

        latency_match = re.search(r"P?95[^0-9]{0,8}(\d+(?:\.\d+)?)\s*ms", joined, re.IGNORECASE)
        if latency_match:
            baseline["online"]["p95_latency_ms"] = latency_match.group(1)
        else:
            latency_seconds_match = re.search(r"(?:响应时间|时延)[^0-9]{0,8}(\d+(?:\.\d+)?)\s*(s|秒)", joined, re.IGNORECASE)
            if latency_seconds_match:
                baseline["online"]["p95_latency_ms"] = str(int(float(latency_seconds_match.group(1)) * 1000))

        availability_match = re.search(r"(?:可用性|availability)[^0-9]{0,8}(\d+(?:\.\d+)?)\s*%", joined, re.IGNORECASE)
        if availability_match:
            baseline["online"]["availability_target"] = f"{availability_match.group(1)}%"

        data_volume_match = re.search(r"批量数据量[^0-9]{0,4}(\d+(?:\.\d+)?(?:万|亿|千)?(?:笔|条|个)?)", joined, re.IGNORECASE)
        if data_volume_match:
            baseline["batch"]["data_volume"] = data_volume_match.group(1)

        duration_match = re.search(r"处理时间[^，。；;\n]{0,12}(半小时|\d+(?:\.\d+)?\s*(?:小时|分钟|min|h))", joined, re.IGNORECASE)
        if duration_match:
            baseline["batch"]["peak_duration"] = duration_match.group(1)

        for line in semantic_lines:
            if (not baseline["batch"]["window"]) and _contains_any(line, ("批量", "窗口", "日终")):
                baseline["batch"]["window"] = line
            if (not baseline["processing_model"]) and _contains_any(line, ("实时", "在线", "批量")):
                baseline["processing_model"] = "在线" if _contains_any(line, ("实时", "在线")) else "批量"

        if any(
            normalize_text(value)
            for value in (
                baseline["online"]["peak_tps"],
                baseline["online"]["p95_latency_ms"],
                baseline["online"]["availability_target"],
                baseline["batch"]["window"],
                baseline["batch"]["data_volume"],
                baseline["batch"]["peak_duration"],
                baseline["processing_model"],
            )
        ):
            return baseline
        return None

    def _extract_deployment_mode(self, lines: List[str]) -> str:
        semantic_lines = [line for line in lines if _is_semantic_line(line)]
        primary_keywords = ("部署方式", "部署架构", "应用部署架构", "集群部署", "分布式集群", "应用服务器", "互为备份")
        for line in semantic_lines:
            if _contains_any(line, primary_keywords):
                return line
        for line in semantic_lines:
            if _contains_any(line, ("部署", "集群", "主从")):
                return line
        for line in semantic_lines:
            if _contains_any(line, ("云上实施", "云上部署", "实施")):
                return line
        return ""

    def _extract_topology_characteristics(self, lines: List[str]) -> List[str]:
        items: List[str] = []
        semantic_lines = [line for line in lines if _is_semantic_line(line)]
        for line in semantic_lines:
            if not _contains_any(line, ("主从", "物理拆分", "分片", "分库", "分表", "多实例", "单中心")):
                continue
            if _is_table_or_checklist_line(line) or _is_boilerplate_line(line):
                continue
            items.append(line)
        return _dedupe_strings(items)[:4]

    def _extract_infrastructure_components(self, lines: List[str]) -> List[str]:
        component_patterns: Tuple[Tuple[str, str], ...] = (
            ("云上统一服务注册中心", r"统一服务注册中心|服务注册中心"),
            ("内联网关", r"内联网关|内联网管|网关"),
            ("服务总线", r"服务总线|\besb\b"),
            ("配置中心", r"配置中心"),
            ("数据库连接池", r"数据库连接池|连接池"),
            ("消息中间件", r"消息中间件|kafka|rocketmq|rabbitmq"),
            ("缓存", r"缓存|redis"),
        )
        matched_labels = set()
        for line in lines:
            if not _is_semantic_line(line):
                continue
            if _contains_any(line, ("公共组件处理", "基本可管理能力")):
                continue
            normalized_line = str(line or "")
            for label, pattern in component_patterns:
                if re.search(pattern, normalized_line, re.IGNORECASE):
                    matched_labels.add(label)
        return [label for label, _pattern in component_patterns if label in matched_labels][:6]

    def _extract_design_methods(self, lines: List[str]) -> List[str]:
        items: List[str] = []
        semantic_lines = [line for line in lines if _is_semantic_line(line)]
        for line in semantic_lines:
            candidate_segments = [
                normalize_text(segment)
                for segment in re.findall(r"[^。；;]+[。；;]?", line)
                if normalize_text(segment)
            ] or [line]
            for segment in candidate_segments:
                if not _contains_any(segment, ("组件化", "插件化", "模块设计", "参数可配置", "配置化", "分层")):
                    continue
                if _is_table_or_checklist_line(segment) or _is_boilerplate_line(segment):
                    continue
                items.append(segment)
        return _dedupe_strings(items)[:4]

    def _extract_extensibility_features(self, lines: List[str]) -> List[str]:
        items: List[str] = []
        semantic_lines = [line for line in lines if _is_semantic_line(line)]
        for line in semantic_lines:
            if not _contains_any(line, ("结构清晰", "易于理解", "扩展方便", "灵活性", "可扩展", "灵活调整")):
                continue
            if _is_table_or_checklist_line(line) or _is_boilerplate_line(line):
                continue
            items.append(line)
        return _dedupe_strings(items)[:4]

    def _extract_common_capabilities(self, lines: List[str]) -> List[str]:
        items: List[str] = []
        semantic_lines = [line for line in lines if _is_semantic_line(line)]
        for line in semantic_lines:
            normalized_line = normalize_text(line)
            if "模块：" in normalized_line:
                continue
            if normalized_line.count("监控") >= 2 and len(normalized_line) <= 20:
                continue
            if not (normalized_line.startswith("具备") or normalized_line.startswith("提供")):
                continue
            if not _contains_any(
                line,
                ("监控", "诊断", "路由", "流量控制", "订阅发布", "日志", "连接池", "权限控制", "资源监控", "应用配置"),
            ):
                continue
            if _is_table_or_checklist_line(line) or _is_boilerplate_line(line):
                continue
            items.append(normalized_line.rstrip("；;"))
        return _dedupe_strings(items)[:6]

    def _extract_availability_design(self, lines: List[str]) -> List[str]:
        items: List[str] = []
        semantic_lines = [line for line in lines if _is_semantic_line(line)]
        for line in semantic_lines:
            if not _contains_any(line, ("高可用", "灾备", "异地", "主从", "主多从", "互为备份", "双活", "故障切换", "灾备演练")):
                continue
            if _is_table_or_checklist_line(line) or _is_boilerplate_line(line):
                continue
            normalized_line = normalize_text(line)
            if normalized_line in {"数据高可用方案", "数据备份方案", "备份方案", "高可用方案"}:
                continue
            if "备份数据" in normalized_line and "灾备" not in normalized_line:
                continue
            items.append(line)
        return _dedupe_strings(items)[:6]

    def _extract_monitoring_operations(self, lines: List[str]) -> List[str]:
        items: List[str] = []
        semantic_lines = [line for line in lines if _is_semantic_line(line)]
        for line in semantic_lines:
            normalized_line = normalize_text(line)
            if "模块：" in normalized_line:
                continue
            if normalized_line.startswith("提供公共组件"):
                continue
            if not _contains_any(line, ("监控", "告警", "审计", "诊断", "日志", "资源监控", "自动清理")):
                continue
            if _is_table_or_checklist_line(line) or _is_boilerplate_line(line):
                continue
            if not (
                normalized_line.startswith("具备")
                or "监控" in normalized_line and len(normalized_line) <= 24
                or "告警" in normalized_line
                or "审计" in normalized_line
            ):
                continue
            items.append(normalized_line.rstrip("；;"))
        return _dedupe_strings(items)[:6]

    def _extract_security_requirements(self, lines: List[str]) -> List[str]:
        items: List[str] = []
        security_priority_keywords = ("国密", "漏洞", "渗透", "等保", "认证", "访问控制", "安全审计", "验证码", "USB KEY", "TOKEN")
        for raw_line in lines:
            line = normalize_text(raw_line)
            if not line:
                continue
            candidate = _extract_table_tail_value(line) or line
            normalized_candidate = normalize_text(candidate)
            if not normalized_candidate:
                continue
            if normalized_candidate.startswith("（") or normalized_candidate.startswith("("):
                continue
            if "□" in normalized_candidate:
                continue
            if _looks_like_structural_label(normalized_candidate) or _is_boilerplate_line(normalized_candidate):
                continue
            if normalized_candidate in {"身份认证", "网络安全", "服务器安全", "应用安全", "数据安全"}:
                continue
            if not _contains_any(normalized_candidate, security_priority_keywords):
                continue
            if len(normalized_candidate) <= 6 and not _contains_any(normalized_candidate, ("国密", "等保", "验证码", "USB KEY", "TOKEN")):
                continue
            items.append(normalized_candidate.rstrip("；;"))
        return _dedupe_strings(items)[:6]

    def _extract_constraint_groups(
        self,
        lines: List[str],
    ) -> Tuple[List[Dict[str, str]], List[Dict[str, str]], List[Dict[str, str]], List[Dict[str, str]]]:
        business_constraints: List[str] = []
        prerequisites: List[str] = []
        sensitive_points: List[str] = []
        risk_items: List[str] = []

        for line in lines:
            if not _is_semantic_line(line):
                continue
            for segment in _split_semantic_segments(line):
                if segment in GENERIC_NOISE_SEGMENTS or segment in MODULE_SUBSECTION_TITLES:
                    continue
                if _is_table_or_checklist_line(segment) or _is_boilerplate_line(segment):
                    continue
                if _contains_any(segment, ("风险", "隐患", "抖动", "失败", "瓶颈", "紧张", "依赖")):
                    risk_items.append(segment)
                    continue
                if _contains_any(segment, ("监管", "合规", "业务", "窗口", "时点", "流程")):
                    business_constraints.append(segment)
                    continue
                if _contains_any(segment, ("敏感", "关键", "计息", "结息", "扣款", "路由", "参数", "核算", "账务")):
                    sensitive_points.append(segment)
                    continue
                prerequisites.append(segment)

        return (
            self._build_named_entries(_dedupe_strings(business_constraints)[:5]),
            self._build_named_entries(_dedupe_strings(prerequisites)[:5]),
            self._build_named_entries(_dedupe_strings(sensitive_points)[:5]),
            self._build_risk_items(_dedupe_strings(risk_items)[:5]),
        )

    def _build_suggestions(
        self,
        doc_type: str,
        text: str,
        skill_id: str,
        compiled_doc_types: Optional[List[str]] = None,
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        clean_lines = extract_clean_lines(text)
        clean_text = clean_document_text(text)
        buckets = _bucket_lines(clean_lines)
        section_analysis = self._analyze_document_sections(clean_lines)
        reason = "从文档正文提取（已过滤目录/封面噪声）" if clean_text != str(text or "").strip() else "从文档正文提取"
        suggestions: Dict[str, Any] = {}
        compiled_types = _ordered_unique_doc_types(
            compiled_doc_types or ([doc_type] if doc_type in DOC_TYPE_TARGET_FIELDS else list(DOC_TYPE_TARGET_FIELDS.keys()))
        )
        constraint_section_titles = CONSTRAINT_SECTION_TITLES + RISK_SECTION_TITLES
        constraint_section_lines = self._extract_section_contents(clean_lines, constraint_section_titles)
        has_constraint_sections = any(_line_matches_title(line, constraint_section_titles) for line in clean_lines)
        positioning_lines = section_analysis.get("positioning_lines") or buckets["positioning"] or clean_lines
        business_lines = buckets["business"] or clean_lines
        integration_lines = buckets["integration"] or clean_lines
        technical_lines = section_analysis.get("design_lines") or buckets["technical"] or clean_lines
        performance_lines = section_analysis.get("performance_lines") or []
        quality_lines = section_analysis.get("quality_lines") or []
        constraint_lines = constraint_section_lines if has_constraint_sections else (constraint_section_lines or buckets["constraints"])
        module_titles = section_analysis.get("module_titles") or []
        module_scenarios = section_analysis.get("module_scenarios") or []
        module_processes = section_analysis.get("module_processes") or []

        if "requirements" in compiled_types:
            core_responsibility = self._extract_scope_text(positioning_lines)
            if core_responsibility:
                suggestions["system_positioning.canonical.core_responsibility"] = self._build_payload(
                    value=core_responsibility,
                    skill_id=skill_id,
                    reason=reason,
                    source_lines=positioning_lines,
                )

            functional_module_lines = module_scenarios or module_titles or self._extract_keyword_segments(
                business_lines,
                include_keywords=("模块", "功能", "能力"),
            )
            functional_modules = self._build_named_entries(functional_module_lines)
            if functional_modules:
                suggestions["business_capabilities.canonical.functional_modules"] = self._build_payload(
                    value=functional_modules,
                    skill_id=skill_id,
                    reason=reason,
                    source_lines=business_lines,
                )

            business_scenarios = self._build_named_entries(module_scenarios)
            if business_scenarios:
                suggestions["business_capabilities.canonical.business_scenarios"] = self._build_payload(
                    value=business_scenarios,
                    skill_id=skill_id,
                    reason=reason,
                    source_lines=business_lines,
                )

            business_flow_lines = module_processes or self._extract_keyword_segments(
                business_lines,
                include_keywords=("流程", "处理", "步骤", "环节"),
            )
            business_flows = self._build_named_entries(business_flow_lines)
            if business_flows:
                suggestions["business_capabilities.canonical.business_flows"] = self._build_payload(
                    value=business_flows,
                    skill_id=skill_id,
                    reason=reason,
                    source_lines=business_lines,
                )

            data_report_source_lines = _dedupe_strings([
                *module_scenarios,
                *module_processes,
                *business_lines,
            ])
            data_report_lines = self._extract_keyword_segments(
                data_report_source_lines,
                include_keywords=("数据", "台账", "流水", "报表", "对账", "清单", "报告"),
            )
            data_reports = self._build_data_report_entries(data_report_lines)
            if data_reports:
                suggestions["business_capabilities.canonical.data_reports"] = self._build_payload(
                    value=data_reports,
                    skill_id=skill_id,
                    reason=reason,
                    source_lines=data_report_source_lines,
                )

        if "design" in compiled_types or "tech_solution" in compiled_types:
            architecture_style = self._extract_architecture_style(technical_lines)
            if architecture_style:
                suggestions["technical_architecture.canonical.architecture_style"] = self._build_payload(
                    value=architecture_style,
                    skill_id=skill_id,
                    reason=reason,
                    source_lines=technical_lines,
                )

            tech_stack = self._extract_tech_stack(clean_text)
            if any(tech_stack.values()):
                suggestions["technical_architecture.canonical.tech_stack"] = self._build_payload(
                    value=tech_stack,
                    skill_id=skill_id,
                    reason=reason,
                    source_lines=technical_lines,
                )

            network_zone = self._extract_network_zone(technical_lines)
            if network_zone:
                suggestions["technical_architecture.canonical.network_zone"] = self._build_payload(
                    value=network_zone,
                    skill_id=skill_id,
                    reason=reason,
                    source_lines=technical_lines,
                )

            performance_baseline = self._extract_performance_baseline(performance_lines, clean_text)
            if performance_baseline:
                suggestions["technical_architecture.canonical.performance_baseline"] = self._build_payload(
                    value=performance_baseline,
                    skill_id=skill_id,
                    reason=reason,
                    source_lines=performance_lines,
                )

            deployment_mode = self._extract_deployment_mode(technical_lines)
            if deployment_mode:
                suggestions["technical_architecture.canonical.extensions.deployment_mode"] = self._build_payload(
                    value=deployment_mode,
                    skill_id=skill_id,
                    reason=reason,
                    source_lines=technical_lines,
                )

            topology_characteristics = self._extract_topology_characteristics(technical_lines)
            if topology_characteristics:
                suggestions["technical_architecture.canonical.extensions.topology_characteristics"] = self._build_payload(
                    value=topology_characteristics,
                    skill_id=skill_id,
                    reason=reason,
                    source_lines=technical_lines,
                )

            infrastructure_components = self._extract_infrastructure_components(technical_lines)
            if infrastructure_components:
                suggestions["technical_architecture.canonical.extensions.infrastructure_components"] = self._build_payload(
                    value=infrastructure_components,
                    skill_id=skill_id,
                    reason=reason,
                    source_lines=technical_lines,
                )

            design_methods = self._extract_design_methods(technical_lines)
            if design_methods:
                suggestions["technical_architecture.canonical.extensions.design_methods"] = self._build_payload(
                    value=design_methods,
                    skill_id=skill_id,
                    reason=reason,
                    source_lines=technical_lines,
                )

            extensibility_features = self._extract_extensibility_features(technical_lines)
            if extensibility_features:
                suggestions["technical_architecture.canonical.extensions.extensibility_features"] = self._build_payload(
                    value=extensibility_features,
                    skill_id=skill_id,
                    reason=reason,
                    source_lines=technical_lines,
                )

            common_capabilities = self._extract_common_capabilities(technical_lines)
            if common_capabilities:
                suggestions["technical_architecture.canonical.extensions.common_capabilities"] = self._build_payload(
                    value=common_capabilities,
                    skill_id=skill_id,
                    reason=reason,
                    source_lines=technical_lines,
                )

            quality_source_lines = quality_lines or performance_lines or []

            availability_design = self._extract_availability_design(quality_source_lines + technical_lines + clean_lines)
            if availability_design:
                suggestions["technical_architecture.canonical.extensions.availability_design"] = self._build_payload(
                    value=availability_design,
                    skill_id=skill_id,
                    reason=reason,
                    source_lines=quality_source_lines + technical_lines + clean_lines,
                )

            monitoring_operations = self._extract_monitoring_operations(quality_source_lines + technical_lines)
            if monitoring_operations:
                suggestions["technical_architecture.canonical.extensions.monitoring_operations"] = self._build_payload(
                    value=monitoring_operations,
                    skill_id=skill_id,
                    reason=reason,
                    source_lines=quality_source_lines + technical_lines,
                )

            security_requirements = self._extract_security_requirements(quality_source_lines + constraint_lines + clean_lines)
            if security_requirements:
                suggestions["technical_architecture.canonical.extensions.security_requirements"] = self._build_payload(
                    value=security_requirements,
                    skill_id=skill_id,
                    reason=reason,
                    source_lines=quality_source_lines + constraint_lines + clean_lines,
                )

        if "tech_solution" in compiled_types:
            integrations = self._extract_integration_items(
                integration_lines,
                module_titles=module_titles,
                module_scenarios=module_scenarios,
            )
            if integrations:
                suggestions["integration_interfaces.canonical.other_integrations"] = self._build_payload(
                    value=integrations,
                    skill_id=skill_id,
                    reason=reason,
                    source_lines=integration_lines,
                )

        if "requirements" in compiled_types or "tech_solution" in compiled_types:
            business_constraints, prerequisites, sensitive_points, risk_items = self._extract_constraint_groups(constraint_lines)
            if business_constraints:
                suggestions["constraints_risks.canonical.business_constraints"] = self._build_payload(
                    value=business_constraints,
                    skill_id=skill_id,
                    reason=reason,
                    source_lines=constraint_lines,
                )
            if prerequisites:
                suggestions["constraints_risks.canonical.prerequisites"] = self._build_payload(
                    value=prerequisites,
                    skill_id=skill_id,
                    reason=reason,
                    source_lines=constraint_lines,
                )
            if sensitive_points:
                suggestions["constraints_risks.canonical.sensitive_points"] = self._build_payload(
                    value=sensitive_points,
                    skill_id=skill_id,
                    reason=reason,
                    source_lines=constraint_lines,
                )
            if risk_items:
                suggestions["constraints_risks.canonical.risk_items"] = self._build_payload(
                    value=risk_items,
                    skill_id=skill_id,
                    reason=reason,
                    source_lines=constraint_lines,
                )

        target_fields: List[str] = []
        for compiled_doc_type in compiled_types:
            target_fields.extend(DOC_TYPE_TARGET_FIELDS.get(compiled_doc_type, ()))
        suggestions, rejected_candidates = self._apply_semantic_gate(suggestions)
        snapshot = {
            "snapshot_type": SNAPSHOT_VERSION,
            "doc_type": doc_type,
            "compiled_doc_types": compiled_types,
            "cleaned_text": clean_text,
            "line_count": len(clean_lines),
            "target_fields": target_fields or list(suggestions.keys()),
            "section_analysis": section_analysis,
            "rejected_candidates": rejected_candidates,
        }
        return suggestions, snapshot

    def _merge_document_suggestions(
        self,
        *,
        system_name: str,
        doc_type: str,
        compiled_doc_types: Optional[List[str]],
        suggestions: Dict[str, Any],
        actor: Optional[Dict[str, Any]] = None,
    ) -> None:
        existing_profile = self.profile_service.get_profile(system_name) or {}
        existing_suggestions = (
            existing_profile.get("ai_suggestions") if isinstance(existing_profile.get("ai_suggestions"), dict) else {}
        )
        merged_suggestions = dict(existing_suggestions)
        fields_to_clear: List[str] = []
        for compiled_doc_type in _ordered_unique_doc_types(compiled_doc_types or [doc_type]):
            fields_to_clear.extend(DOC_TYPE_TARGET_FIELDS.get(compiled_doc_type, ()))
        if not fields_to_clear:
            fields_to_clear = list(suggestions.keys())
        for field_path in fields_to_clear:
            merged_suggestions.pop(field_path, None)
        merged_suggestions.update(suggestions)
        self.profile_service.update_ai_suggestions_map(system_name, suggestions=merged_suggestions, actor=actor)

    def _build_policy_results(self, suggestions: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [
            {
                "field_path": field_path,
                "decision": "suggestion_only",
                "reason": "pm_document_ingest always suggestion_only",
            }
            for field_path in suggestions
        ]

    def _apply_document_suggestions(
        self,
        *,
        system_id: str,
        system_name: str,
        doc_type: str,
        compiled_doc_types: Optional[List[str]],
        skill_id: str,
        suggestions: Dict[str, Any],
        execution_id: str,
        actor: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, Optional[str], List[Dict[str, Any]]]:
        self.profile_service.ensure_profile(system_name, system_id=system_id, actor=actor)
        policy_results = self._build_policy_results(suggestions)
        status_name = "completed"
        memory_error = None
        try:
            self.memory_service.append_record(
                system_id=system_id,
                memory_type="profile_update",
                memory_subtype="document_suggestion",
                scene_id=SCENE_ID,
                source_type="document",
                source_id=execution_id,
                summary=f"{doc_type} 文档导入生成画像建议",
                payload={"changed_fields": list(suggestions.keys())},
                decision_policy="suggestion_only",
                confidence=0.8,
                actor=(actor or {}).get("username"),
            )
        except Exception as exc:  # pragma: no cover
            status_name = "partial_success"
            memory_error = str(exc)

        return status_name, memory_error, policy_results

    def _process_document_text(
        self,
        *,
        system_id: str,
        system_name: str,
        doc_type: str,
        file_name: str,
        text: str,
        parsed_data: Any = None,
        actor: Optional[Dict[str, Any]] = None,
        raw_artifact: Optional[Dict[str, Any]] = None,
        primary_doc_type: Optional[str] = None,
        compiled_doc_types: Optional[List[str]] = None,
        classification_scores: Optional[Dict[str, int]] = None,
    ) -> Dict[str, Any]:
        scene = self.runtime_service.resolve_scene(SCENE_ID, {"doc_type": primary_doc_type or doc_type})
        skill_id = scene["skill_chain"][0]
        execution = self.execution_service.create_execution(
            scene_id=SCENE_ID,
            system_id=system_id,
            source_type="document",
            source_file=file_name,
            skill_chain=scene["skill_chain"],
        )

        try:
            suggestions, snapshot = self._build_suggestions(doc_type, text, skill_id, compiled_doc_types)
            snapshot["file_name"] = file_name
            snapshot["classification_scores"] = classification_scores if isinstance(classification_scores, dict) else {}
            raw_artifact_id = str((raw_artifact or {}).get("artifact_id") or "").strip() or None
            raw_artifact_path = str((raw_artifact or {}).get("path") or "").strip() or None
            source_bundle = self._persist_source_bundle(
                system_id=system_id,
                system_name=system_name,
                doc_type=doc_type,
                file_name=file_name,
                parsed_data=parsed_data,
                text=text,
                raw_artifact=raw_artifact,
            )
            llm_bundle = self._build_llm_candidate_bundle(
                system_id=system_id,
                system_name=system_name,
                clean_text=snapshot.get("cleaned_text") if isinstance(snapshot.get("cleaned_text"), str) else text,
            )
            llm_candidate_entries = self._build_llm_candidate_entries(
                llm_bundle=llm_bundle,
                source_lines=source_bundle.get("clean_lines") if isinstance(source_bundle.get("clean_lines"), list) else [],
            )
            facts = self._build_candidate_facts(
                system_id=system_id,
                system_name=system_name,
                raw_artifact_id=raw_artifact_id,
                suggestions=suggestions,
                llm_bundle=llm_bundle,
            )
            profile_projection = self._build_profile_projection(
                system_id=system_id,
                system_name=system_name,
                doc_type=doc_type,
                compiled_doc_types=snapshot.get("compiled_doc_types") if isinstance(snapshot.get("compiled_doc_types"), list) else [],
                classification_scores=snapshot.get("classification_scores") if isinstance(snapshot.get("classification_scores"), dict) else {},
                suggestions=suggestions,
                facts=facts,
                llm_bundle=llm_bundle,
            )
            dossier = self._build_candidate_dossier(
                system_id=system_id,
                system_name=system_name,
                doc_type=doc_type,
                compiled_doc_types=snapshot.get("compiled_doc_types") if isinstance(snapshot.get("compiled_doc_types"), list) else [],
                classification_scores=snapshot.get("classification_scores") if isinstance(snapshot.get("classification_scores"), dict) else {},
                source_chunks=source_bundle.get("chunks") if isinstance(source_bundle.get("chunks"), list) else [],
                llm_bundle=llm_bundle,
                facts=facts,
            )
            quality_report = self._build_quality_report(
                target_fields=snapshot.get("target_fields") if isinstance(snapshot.get("target_fields"), list) else [],
                suggestions=suggestions,
                facts=facts,
                llm_bundle=llm_bundle,
                rejected_candidates=snapshot.get("rejected_candidates") if isinstance(snapshot.get("rejected_candidates"), list) else [],
                section_analysis=snapshot.get("section_analysis") if isinstance(snapshot.get("section_analysis"), dict) else {},
            )
            review_queue = self._build_review_queue(
                quality_report=quality_report,
                llm_bundle=llm_bundle,
                suggestions=suggestions,
                section_analysis=snapshot.get("section_analysis") if isinstance(snapshot.get("section_analysis"), dict) else {},
            )
            document_candidate_payload = {
                "candidate_type": "document_candidate",
                "system_id": system_id,
                "system_name": system_name,
                "doc_type": doc_type,
                "compiled_doc_types": snapshot.get("compiled_doc_types") or [],
                "file_name": file_name,
                "raw_artifact_id": raw_artifact_id,
                "chunk_count": len(source_bundle.get("chunks") or []),
                "classification_scores": snapshot.get("classification_scores") or {},
                "target_fields": snapshot.get("target_fields") or [],
                "candidates": {
                    field_path: {
                        "value": payload.get("value"),
                        "confidence": payload.get("confidence"),
                        "reason": payload.get("reason"),
                        "skill_id": payload.get("skill_id"),
                        "decision_policy": payload.get("decision_policy"),
                        "source_anchors": payload.get("source_anchors") if isinstance(payload.get("source_anchors"), list) else [],
                    }
                    for field_path, payload in suggestions.items()
                },
                "llm_candidates": llm_candidate_entries,
            }
            document_candidate = self.artifact_service.append_candidate_record(
                system_id=system_id,
                category="documents",
                payload=document_candidate_payload,
                operator_id=str((actor or {}).get("username") or (actor or {}).get("id") or "system"),
                source_artifact_id=raw_artifact_id,
            )
            candidate_bundle_id = str(document_candidate.get("artifact_id") or "").strip() or f"cand_{uuid.uuid4().hex}"
            self._persist_candidate_bundle(
                system_id=system_id,
                candidate_artifact_id=candidate_bundle_id,
                source_manifest={
                    "system_id": system_id,
                    "system_name": system_name,
                    "raw_artifact_id": raw_artifact_id,
                    "raw_artifact_path": raw_artifact_path,
                    "doc_type": doc_type,
                    "file_name": file_name,
                    "compiled_doc_types": snapshot.get("compiled_doc_types") if isinstance(snapshot.get("compiled_doc_types"), list) else [],
                    "classification_scores": snapshot.get("classification_scores") if isinstance(snapshot.get("classification_scores"), dict) else {},
                    "chunk_count": len(source_bundle.get("chunks") or []),
                    "source_dir": os.path.relpath(source_bundle.get("source_dir") or "", self.repository.root_dir),
                },
                facts=facts,
                entity_graph=self._build_candidate_entity_graph(
                    system_id=system_id,
                    system_name=system_name,
                    facts=facts,
                    llm_bundle=llm_bundle,
                ),
                profile_projection=profile_projection,
                dossier=dossier,
                quality_report=quality_report,
                review_queue=review_queue,
            )
            projection_artifact = self.profile_service.refresh_candidate_projection(
                system_name,
                system_id=system_id,
                actor=actor,
            )
            output_artifact = self.artifact_service.append_layer_record(
                layer="output",
                system_id=system_id,
                payload={
                    "output_type": "import_quality",
                    "doc_type": doc_type,
                    "file_name": file_name,
                    "quality": {
                        "line_count": snapshot.get("line_count") or 0,
                        "suggestion_count": len(suggestions),
                        "missing_targets": [
                            field for field in (snapshot.get("target_fields") or []) if field not in suggestions
                        ],
                    },
                    "classification_scores": snapshot.get("classification_scores") or {},
                    "compiled_doc_types": snapshot.get("compiled_doc_types") or [],
                },
                operator_id=str((actor or {}).get("username") or (actor or {}).get("id") or "system"),
                source_artifact_id=str((projection_artifact or {}).get("artifact_id") or "") or None,
                latest_file_name="latest_report.json",
            )
            snapshot["raw_artifact_id"] = raw_artifact_id
            snapshot["raw_artifact_path"] = raw_artifact_path
            snapshot["document_candidate_artifact_id"] = str(document_candidate.get("artifact_id") or "") or None
            snapshot["projection_artifact_id"] = str((projection_artifact or {}).get("artifact_id") or "") or None
            snapshot["output_artifact_id"] = str(output_artifact.get("artifact_id") or "") or None
            status_name, memory_error, policy_results = self._apply_document_suggestions(
                system_id=system_id,
                system_name=system_name,
                doc_type=doc_type,
                compiled_doc_types=snapshot.get("compiled_doc_types") if isinstance(snapshot.get("compiled_doc_types"), list) else None,
                skill_id=skill_id,
                suggestions=suggestions,
                execution_id=execution["execution_id"],
                actor=actor,
            )
            updated_execution = self.execution_service.update_execution(
                execution["execution_id"],
                status=status_name,
                error=memory_error,
                result_summary={"updated_system_ids": [system_id], "skipped_items": []},
                policy_results=policy_results,
                input_snapshot=snapshot,
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
            "resolved_doc_type": doc_type,
            "compiled_doc_types": snapshot.get("compiled_doc_types") if isinstance(snapshot.get("compiled_doc_types"), list) else [],
            "artifact_refs": {
                "raw_artifact_id": snapshot.get("raw_artifact_id"),
                "document_candidate_artifact_id": snapshot.get("document_candidate_artifact_id"),
                "projection_artifact_id": snapshot.get("projection_artifact_id"),
                "output_artifact_id": snapshot.get("output_artifact_id"),
            },
        }

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

        parsed = self.document_parser.parse(file_content=file_content, filename=file_name)
        text = parsed_to_text(parsed)
        if not normalize_text(text):
            raise ValueError("未提取到有效正文")

        normalized_doc_type = str(doc_type or "").strip().lower()
        compile_plan = self._build_compile_plan(normalized_doc_type, file_name, text)

        raw_artifact = self.artifact_service.write_raw_document(
            system_id=system_id,
            doc_type=compile_plan["resolved_doc_type"],
            source_name=file_name,
            file_content=file_content,
            operator_id=str((actor or {}).get("username") or (actor or {}).get("id") or "unknown"),
            metadata={
                "system_name": system_name,
                "source_type": "profile_import",
                "requested_doc_type": normalized_doc_type or "auto",
                "compiled_doc_types": compile_plan["compiled_doc_types"],
            },
        )

        return self._process_document_text(
            system_id=system_id,
            system_name=system_name,
            doc_type=compile_plan["resolved_doc_type"],
            file_name=file_name,
            text=text,
            parsed_data=parsed,
            actor=actor,
            raw_artifact=raw_artifact,
            primary_doc_type=compile_plan["primary_doc_type"],
            compiled_doc_types=compile_plan["compiled_doc_types"],
            classification_scores=compile_plan["classification_scores"],
        )

    def retry_document(
        self,
        *,
        system_id: str,
        system_name: str,
        doc_type: str,
        file_name: str,
        cleaned_text: str,
        actor: Optional[Dict[str, Any]] = None,
        raw_artifact: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not normalize_text(cleaned_text):
            raise ValueError("当前历史导入记录不支持自动重跑，请重新上传文档")

        normalized_doc_type = str(doc_type or "").strip().lower()
        compile_plan = self._build_compile_plan(normalized_doc_type, file_name, cleaned_text)

        return self._process_document_text(
            system_id=system_id,
            system_name=system_name,
            doc_type=compile_plan["resolved_doc_type"],
            file_name=file_name,
            text=cleaned_text,
            parsed_data={"text": cleaned_text},
            actor=actor,
            raw_artifact=raw_artifact,
            primary_doc_type=compile_plan["primary_doc_type"],
            compiled_doc_types=compile_plan["compiled_doc_types"],
            classification_scores=compile_plan["classification_scores"],
        )


_document_skill_adapter: Optional[DocumentSkillAdapter] = None


def get_document_skill_adapter() -> DocumentSkillAdapter:
    global _document_skill_adapter
    if _document_skill_adapter is None:
        _document_skill_adapter = DocumentSkillAdapter()
    return _document_skill_adapter
