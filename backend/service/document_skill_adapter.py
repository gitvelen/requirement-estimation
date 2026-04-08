from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional, Tuple

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
from backend.service.runtime_execution_service import get_runtime_execution_service
from backend.service.skill_runtime_service import get_skill_runtime_service
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
        "system_positioning.canonical.service_scope",
        "system_positioning.canonical.system_boundary",
        "business_capabilities.canonical.functional_modules",
        "business_capabilities.canonical.business_processes",
        "business_capabilities.canonical.data_assets",
        "constraints_risks.canonical.technical_constraints",
        "constraints_risks.canonical.business_constraints",
        "constraints_risks.canonical.known_risks",
    ),
    "design": (
        "technical_architecture.canonical.architecture_style",
        "technical_architecture.canonical.tech_stack",
        "technical_architecture.canonical.network_zone",
        "technical_architecture.canonical.performance_baseline",
    ),
    "tech_solution": (
        "integration_interfaces.canonical.other_integrations",
        "technical_architecture.canonical.architecture_style",
        "technical_architecture.canonical.tech_stack",
        "technical_architecture.canonical.network_zone",
        "technical_architecture.canonical.performance_baseline",
        "constraints_risks.canonical.technical_constraints",
        "constraints_risks.canonical.business_constraints",
        "constraints_risks.canonical.known_risks",
    ),
}


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


class DocumentSkillAdapter:
    ALLOWED_EXTENSIONS = {".docx", ".pdf", ".pptx"}

    def __init__(self) -> None:
        self.document_parser = get_document_parser()
        self.runtime_service = get_skill_runtime_service()
        self.execution_service = get_runtime_execution_service()
        self.memory_service = get_memory_service()
        self.profile_service = get_system_profile_service()

    def _build_payload(self, *, value: Any, skill_id: str, reason: str, confidence: float = 0.82) -> Dict[str, Any]:
        return {
            "value": value,
            "scene_id": SCENE_ID,
            "skill_id": skill_id,
            "decision_policy": "suggestion_only",
            "confidence": confidence,
            "reason": reason,
        }

    def _extract_scope_text(self, lines: List[str]) -> str:
        keywords = ("范围", "提供", "负责", "用于", "支持", "服务")
        for line in lines:
            if _contains_any(line, keywords):
                return line
        for line in lines:
            if "系统" in line or "平台" in line:
                return line
        return lines[0] if lines else ""

    def _extract_boundary_items(self, lines: List[str]) -> List[str]:
        items: List[str] = []
        for line in lines:
            for segment in _split_semantic_segments(line):
                if _contains_any(segment, ("边界", "不处理", "不包括", "仅负责", "限定")):
                    items.append(segment)
        return _dedupe_strings(items)[:5]

    def _extract_keyword_segments(
        self,
        lines: List[str],
        *,
        include_keywords: Tuple[str, ...],
        exclude_keywords: Tuple[str, ...] = (),
        limit: int = 5,
    ) -> List[str]:
        items: List[str] = []
        for line in lines:
            for segment in _split_semantic_segments(line):
                if include_keywords and (not _contains_any(segment, include_keywords)):
                    continue
                if exclude_keywords and _contains_any(segment, exclude_keywords):
                    continue
                items.append(segment)
        return _dedupe_strings(items)[:limit]

    def _extract_integration_items(self, lines: List[str]) -> List[str]:
        items = self._extract_keyword_segments(
            lines,
            include_keywords=("接口", "集成", "对接", "服务", "调用", "报文", "数据流向", "核心系统", "数据仓库"),
            limit=6,
        )
        if items:
            return items
        return _dedupe_strings(lines)[:4]

    def _extract_architecture_style(self, lines: List[str]) -> str:
        priority_keywords = ("架构", "部署", "双活", "分层", "微服务", "容灾")
        for line in lines:
            if _contains_any(line, priority_keywords) and "技术栈" not in line:
                return line
        return lines[0] if lines else ""

    def _extract_network_zone(self, lines: List[str]) -> str:
        for line in lines:
            if _contains_any(line, ("内网", "外网", "DMZ", "专线", "生产区", "互联网区", "核心区")):
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

        joined = "\n".join(lines) if lines else str(text or "")

        peak_match = re.search(r"(\d+(?:\.\d+)?)\s*(TPS|QPS)", joined, re.IGNORECASE)
        if peak_match:
            baseline["online"]["peak_tps"] = f"{peak_match.group(1)} {peak_match.group(2).upper()}"

        latency_match = re.search(r"P?95[^0-9]{0,8}(\d+(?:\.\d+)?)\s*ms", joined, re.IGNORECASE)
        if latency_match:
            baseline["online"]["p95_latency_ms"] = latency_match.group(1)

        availability_match = re.search(r"(?:可用性|availability)[^0-9]{0,8}(\d+(?:\.\d+)?)\s*%", joined, re.IGNORECASE)
        if availability_match:
            baseline["online"]["availability_target"] = f"{availability_match.group(1)}%"

        for line in lines:
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

    def _extract_constraint_groups(self, lines: List[str]) -> Tuple[List[str], List[str], List[str]]:
        technical_constraints: List[str] = []
        business_constraints: List[str] = []
        known_risks: List[str] = []

        for line in lines:
            for segment in _split_semantic_segments(line):
                if _contains_any(segment, ("风险", "隐患", "抖动", "失败", "瓶颈", "紧张", "依赖")):
                    known_risks.append(segment)
                    continue
                if _contains_any(segment, ("监管", "合规", "业务", "窗口", "时点", "流程")):
                    business_constraints.append(segment)
                    continue
                technical_constraints.append(segment)

        return (
            _dedupe_strings(technical_constraints)[:5],
            _dedupe_strings(business_constraints)[:5],
            _dedupe_strings(known_risks)[:5],
        )

    def _build_suggestions(self, doc_type: str, text: str, skill_id: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        clean_lines = extract_clean_lines(text)
        clean_text = clean_document_text(text)
        buckets = _bucket_lines(clean_lines)
        reason = "从文档正文提取（已过滤目录/封面噪声）" if clean_text != str(text or "").strip() else "从文档正文提取"
        suggestions: Dict[str, Any] = {}

        if doc_type == "requirements":
            service_scope = self._extract_scope_text(buckets["positioning"])
            if service_scope:
                suggestions["system_positioning.canonical.service_scope"] = self._build_payload(
                    value=service_scope,
                    skill_id=skill_id,
                    reason=reason,
                )

            system_boundaries = self._extract_boundary_items(buckets["positioning"])
            if system_boundaries:
                suggestions["system_positioning.canonical.system_boundary"] = self._build_payload(
                    value=system_boundaries,
                    skill_id=skill_id,
                    reason=reason,
                )

            functional_modules = self._extract_keyword_segments(
                buckets["business"],
                include_keywords=("模块", "功能", "能力"),
            )
            if functional_modules:
                suggestions["business_capabilities.canonical.functional_modules"] = self._build_payload(
                    value=functional_modules,
                    skill_id=skill_id,
                    reason=reason,
                )

            business_processes = self._extract_keyword_segments(
                buckets["business"],
                include_keywords=("流程", "处理", "步骤", "环节"),
            )
            if business_processes:
                suggestions["business_capabilities.canonical.business_processes"] = self._build_payload(
                    value=business_processes,
                    skill_id=skill_id,
                    reason=reason,
                )

            data_assets = self._extract_keyword_segments(
                buckets["business"],
                include_keywords=("数据", "台账", "流水", "报表"),
            )
            if data_assets:
                suggestions["business_capabilities.canonical.data_assets"] = self._build_payload(
                    value=data_assets,
                    skill_id=skill_id,
                    reason=reason,
                )

        if doc_type in {"design", "tech_solution"}:
            architecture_style = self._extract_architecture_style(buckets["technical"])
            if architecture_style:
                suggestions["technical_architecture.canonical.architecture_style"] = self._build_payload(
                    value=architecture_style,
                    skill_id=skill_id,
                    reason=reason,
                )

            tech_stack = self._extract_tech_stack(clean_text)
            if any(tech_stack.values()):
                suggestions["technical_architecture.canonical.tech_stack"] = self._build_payload(
                    value=tech_stack,
                    skill_id=skill_id,
                    reason=reason,
                )

            network_zone = self._extract_network_zone(buckets["technical"])
            if network_zone:
                suggestions["technical_architecture.canonical.network_zone"] = self._build_payload(
                    value=network_zone,
                    skill_id=skill_id,
                    reason=reason,
                )

            performance_baseline = self._extract_performance_baseline(buckets["technical"], clean_text)
            if performance_baseline:
                suggestions["technical_architecture.canonical.performance_baseline"] = self._build_payload(
                    value=performance_baseline,
                    skill_id=skill_id,
                    reason=reason,
                )

        if doc_type == "tech_solution":
            integrations = self._extract_integration_items(buckets["integration"])
            if integrations:
                suggestions["integration_interfaces.canonical.other_integrations"] = self._build_payload(
                    value=integrations,
                    skill_id=skill_id,
                    reason=reason,
                )

        if doc_type in {"requirements", "tech_solution"}:
            technical_constraints, business_constraints, known_risks = self._extract_constraint_groups(buckets["constraints"])
            if technical_constraints:
                suggestions["constraints_risks.canonical.technical_constraints"] = self._build_payload(
                    value=technical_constraints,
                    skill_id=skill_id,
                    reason=reason,
                )
            if business_constraints:
                suggestions["constraints_risks.canonical.business_constraints"] = self._build_payload(
                    value=business_constraints,
                    skill_id=skill_id,
                    reason=reason,
                )
            if known_risks:
                suggestions["constraints_risks.canonical.known_risks"] = self._build_payload(
                    value=known_risks,
                    skill_id=skill_id,
                    reason=reason,
                )

        if (not suggestions) and clean_lines:
            fallback_field = "technical_architecture.canonical.architecture_style" if doc_type != "requirements" else "system_positioning.canonical.service_scope"
            suggestions[fallback_field] = self._build_payload(
                value=clean_lines[0],
                skill_id=skill_id,
                reason=reason,
                confidence=0.65,
            )

        snapshot = {
            "snapshot_type": SNAPSHOT_VERSION,
            "doc_type": doc_type,
            "cleaned_text": clean_text,
            "line_count": len(clean_lines),
            "target_fields": list(DOC_TYPE_TARGET_FIELDS.get(doc_type, suggestions.keys())),
        }
        return suggestions, snapshot

    def _merge_document_suggestions(
        self,
        *,
        system_name: str,
        doc_type: str,
        suggestions: Dict[str, Any],
        actor: Optional[Dict[str, Any]] = None,
    ) -> None:
        existing_profile = self.profile_service.get_profile(system_name) or {}
        existing_suggestions = (
            existing_profile.get("ai_suggestions") if isinstance(existing_profile.get("ai_suggestions"), dict) else {}
        )
        merged_suggestions = dict(existing_suggestions)
        for field_path in DOC_TYPE_TARGET_FIELDS.get(doc_type, ()):
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
        skill_id: str,
        suggestions: Dict[str, Any],
        execution_id: str,
        actor: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, Optional[str], List[Dict[str, Any]]]:
        self.profile_service.ensure_profile(system_name, system_id=system_id, actor=actor)
        self._merge_document_suggestions(
            system_name=system_name,
            doc_type=doc_type,
            suggestions=suggestions,
            actor=actor,
        )

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
        actor: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        scene = self.runtime_service.resolve_scene(SCENE_ID, {"doc_type": doc_type})
        skill_id = scene["skill_chain"][0]
        execution = self.execution_service.create_execution(
            scene_id=SCENE_ID,
            system_id=system_id,
            source_type="document",
            source_file=file_name,
            skill_chain=scene["skill_chain"],
        )

        try:
            suggestions, snapshot = self._build_suggestions(doc_type, text, skill_id)
            snapshot["file_name"] = file_name
            status_name, memory_error, policy_results = self._apply_document_suggestions(
                system_id=system_id,
                system_name=system_name,
                doc_type=doc_type,
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

        return self._process_document_text(
            system_id=system_id,
            system_name=system_name,
            doc_type=doc_type,
            file_name=file_name,
            text=text,
            actor=actor,
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
    ) -> Dict[str, Any]:
        if not normalize_text(cleaned_text):
            raise ValueError("当前历史导入记录不支持自动重跑，请重新上传文档")

        return self._process_document_text(
            system_id=system_id,
            system_name=system_name,
            doc_type=doc_type,
            file_name=file_name,
            text=cleaned_text,
            actor=actor,
        )


_document_skill_adapter: Optional[DocumentSkillAdapter] = None


def get_document_skill_adapter() -> DocumentSkillAdapter:
    global _document_skill_adapter
    if _document_skill_adapter is None:
        _document_skill_adapter = DocumentSkillAdapter()
    return _document_skill_adapter
