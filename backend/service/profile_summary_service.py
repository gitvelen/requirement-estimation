"""
系统画像 AI 总结服务（异步）

对齐 requirements REQ-024 / API-018：
- 触发：代码扫描入库/ESB导入/知识导入（绑定系统）成功后；或 API-018 手动重试
- 输出：system_profile.ai_suggestions + ai_suggestions_updated_at
- 通知：summary_ready / summary_failed（发送给系统主责）
- 幂等：同一 system 同一时刻最多一个运行中任务；有运行中任务直接复用 job_id
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from backend.api import system_routes
from backend.config.config import settings
from backend.service.code_scan_service import get_code_scan_service
from backend.service.esb_service import get_esb_service
from backend.service.system_profile_service import PROFILE_V24_DOMAIN_KEYS, get_system_profile_service
from backend.utils.llm_client import deep_merge, extract_usage_from_response, llm_client, merge_stage1_responses
from backend.utils.token_counter import chunk_text, estimate_tokens

logger = logging.getLogger(__name__)


PROFILE_DOMAIN_KEYS = tuple(PROFILE_V24_DOMAIN_KEYS)

DOMAIN_HINT_KEYWORDS: Dict[str, tuple[str, ...]] = {
    "system_positioning": (
        "系统定位",
        "边界",
        "目标用户",
        "适用范围",
        "业务背景",
    ),
    "business_capabilities": (
        "模块",
        "流程",
        "功能",
        "开户",
        "还款",
        "交易",
    ),
    "integration_interfaces": (
        "接口",
        "esb",
        "rpc",
        "sftp",
        "对接",
        "外部系统",
        "报文",
    ),
    "technical_architecture": (
        "技术架构",
        "架构",
        "部署",
        "技术栈",
        "高可用",
        "性能",
        "并发",
        "微服务",
        "tomcat",
        "redis",
        "mysql",
        "sofa",
        "jvm",
    ),
    "constraints_risks": (
        "约束",
        "风险",
        "限制",
        "假设",
        "依赖",
        "安全",
        "合规",
    ),
}


@dataclass(frozen=True)
class SummaryContextBundle:
    static_prefix_text: str
    chunkable_body_text: str


class ProfileSummaryService:
    def __init__(self) -> None:
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="profile_summary")
        self._system_lock_guard = threading.Lock()
        self._system_locks: Dict[str, threading.Lock] = {}

    def _get_system_lock(self, system_id: str) -> threading.Lock:
        key = str(system_id or "").strip() or "__unknown__"
        with self._system_lock_guard:
            lock = self._system_locks.get(key)
            if lock is None:
                lock = threading.Lock()
                self._system_locks[key] = lock
            return lock

    def trigger_summary(
        self,
        *,
        system_id: str,
        system_name: str,
        actor: Optional[Dict[str, Any]] = None,
        reason: str = "import",
        source_file: str = "",
        trigger: str = "document_import",
        context_override: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        normalized_system_id = str(system_id or "").strip()
        normalized_system_name = str(system_name or "").strip()
        if not normalized_system_id or not normalized_system_name:
            raise ValueError("system_id/system_name不能为空")

        profile_service = get_system_profile_service()
        job_id = f"summary_{uuid.uuid4().hex}"
        profile_service.upsert_extraction_task(
            normalized_system_id,
            task_id=job_id,
            status="pending",
            trigger=str(trigger or "").strip() or "document_import",
            source_file=source_file,
        )

        self.executor.submit(
            self._run_job,
            system_id=normalized_system_id,
            system_name=normalized_system_name,
            job_id=job_id,
            reason=str(reason or "").strip() or "import",
            trigger=str(trigger or "").strip() or "document_import",
            source_file=str(source_file or "").strip(),
            actor=actor or {},
            context_override=context_override or {},
        )
        return {"job_id": job_id, "status": "pending", "created_new": True}

    def _run_job(
        self,
        *,
        system_id: str,
        system_name: str,
        job_id: str,
        reason: str,
        trigger: str,
        source_file: str,
        actor: Dict[str, Any],
        context_override: Dict[str, Any],
    ) -> None:
        profile_service = get_system_profile_service()

        owner_info = system_routes.resolve_system_owner(system_id=system_id)
        owner_user_id = str(owner_info.get("resolved_owner_id") or "").strip()

        with self._get_system_lock(system_id):
            profile_service.update_extraction_task_status(system_id, task_id=job_id, status="processing")

            try:
                context_bundle = self._build_context_bundle(
                    system_id=system_id,
                    system_name=system_name,
                    context_override=context_override,
                )
                llm_result = self._call_llm(
                    system_id=system_id,
                    system_name=system_name,
                    context_bundle=context_bundle,
                )
                suggestions = llm_result.get("suggestions") if isinstance(llm_result, dict) else {}
                relevant_domains = llm_result.get("relevant_domains") if isinstance(llm_result, dict) else []
                related_systems = llm_result.get("related_systems") if isinstance(llm_result, dict) else []

                profile_service.set_ai_suggestions(
                    system_name,
                    suggestions=suggestions if isinstance(suggestions, dict) else {},
                    relevant_domains=relevant_domains if isinstance(relevant_domains, list) else [],
                    trigger=trigger,
                    source=source_file,
                    actor=actor,
                )
                notifications = self._build_multi_system_notifications(
                    system_name=system_name,
                    related_systems=related_systems if isinstance(related_systems, list) else [],
                )
                profile_service.update_extraction_task_status(
                    system_id,
                    task_id=job_id,
                    status="completed",
                    notifications=notifications,
                )

                self._notify(
                    user_id=owner_user_id,
                    notify_type="system_profile_summary_ready",
                    system_id=system_id,
                    system_name=system_name,
                    payload={
                        "job_id": job_id,
                        "reason": reason,
                    },
                )
            except Exception as exc:
                reason_text = str(exc or "").strip() or "画像AI总结失败"
                profile_service.update_extraction_task_status(
                    system_id,
                    task_id=job_id,
                    status="failed",
                    error=reason_text,
                )
                self._notify(
                    user_id=owner_user_id,
                    notify_type="system_profile_summary_failed",
                    system_id=system_id,
                    system_name=system_name,
                    payload={
                        "job_id": job_id,
                        "error_code": "SUMMARY_001",
                        "error_reason": reason_text[:500],
                        "reason": reason,
                    },
                )

    def _notify(
        self,
        *,
        user_id: str,
        notify_type: str,
        system_id: str,
        system_name: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not str(user_id or "").strip():
            logger.warning("系统主责未配置或无法映射用户，已跳过通知: system_id=%s system_name=%s", system_id, system_name)
            return

        link = f"/system-profiles/board?system_id={system_id}&system_name={system_name}"
        final_payload: Dict[str, Any] = {
            "system_id": system_id,
            "system_name": system_name,
            "link": link,
        }
        if isinstance(payload, dict):
            final_payload.update(payload)

        title = "画像AI总结完成" if notify_type == "system_profile_summary_ready" else "画像AI总结失败"
        content = (
            f"系统【{system_name}】AI建议已生成，请在信息看板查看并采纳/忽略。"
            if notify_type == "system_profile_summary_ready"
            else f"系统【{system_name}】AI建议生成失败，可在信息看板重试。"
        )

        try:
            from backend.api.notification_routes import create_notification

            create_notification(
                title=title,
                content=content,
                notify_type=notify_type,
                user_ids=[user_id],
                payload=final_payload,
            )
        except Exception as exc:
            logger.warning("创建通知失败: %s", exc)

    def _build_static_context(self, *, system_id: str, system_name: str) -> str:
        parts: List[str] = []

        # code scan (latest completed job)
        try:
            service = get_code_scan_service()
            jobs = service.list_jobs()
            jobs = [
                job
                for job in jobs
                if isinstance(job, dict)
                and str(job.get("system_id") or "").strip() == system_id
                and str(job.get("status") or "").strip() == "completed"
            ]
            if jobs:
                job = sorted(jobs, key=lambda x: str(x.get("finished_at") or x.get("created_at") or ""), reverse=True)[0]
                result_path = str(job.get("result_path") or "").strip()
                if result_path and os.path.exists(result_path):
                    with open(result_path, "r", encoding="utf-8") as f:
                        data = json.load(f) if f else {}
                    items = data.get("items") or []
                    samples = []
                    for item in items[:30]:
                        if not isinstance(item, dict):
                            continue
                        samples.append(
                            f"- {item.get('entry_type','')} {item.get('entry_id','')}: {item.get('summary','')}"
                        )
                    parts.append("【代码扫描】")
                    parts.append(f"items_total={len(items)}")
                    if samples:
                        parts.append("\n".join(samples))
        except Exception as exc:
            logger.info("收集代码扫描上下文失败（忽略）: %s", exc)

        # ESB entries (best-effort)
        try:
            def _normalize(value: Any) -> str:
                text = str(value or "").strip()
                return text.casefold() if text else ""

            owner_info = system_routes.resolve_system_owner(system_id=system_id, system_name=system_name)
            target_candidates = {
                _normalize(system_id),
                _normalize(system_name),
                _normalize(owner_info.get("system_abbreviation")),
            }
            target_candidates.discard("")

            esb = get_esb_service()
            with esb._lock():  # noqa: SLF001 - internal lock reused for read
                store = esb._load_unlocked()  # noqa: SLF001 - file store, safe for internal read
            entries = store.get("entries") or []
            related = []
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                pid = _normalize(entry.get("provider_system_id"))
                cid = _normalize(entry.get("consumer_system_id"))
                pname = _normalize(entry.get("provider_system_name"))
                cname = _normalize(entry.get("consumer_system_name"))
                if not any(value in target_candidates for value in (pid, cid, pname, cname) if value):
                    continue
                related.append(entry)
            samples = []
            for entry in related[:30]:
                samples.append(
                    f"- {entry.get('service_name','')}"
                    f" provider={entry.get('provider_system_id','')}"
                    f" consumer={entry.get('consumer_system_id','')}"
                    f" scenario={entry.get('scenario_code','')}"
                    f" status={entry.get('status','')}"
                )
            parts.append("【ESB】")
            parts.append(f"entries_total={len(related)}")
            if samples:
                parts.append("\n".join(samples))
        except Exception as exc:
            logger.info("收集ESB上下文失败（忽略）: %s", exc)

        joined = "\n".join(parts).strip()
        return joined[: self._context_max_chars()] if joined else ""

    def _build_knowledge_context(self, *, system_name: str) -> str:
        parts: List[str] = []
        try:
            store_path = os.path.join(settings.REPORT_DIR, "knowledge_store.json")
            if os.path.exists(store_path):
                with open(store_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    related = [
                        item
                        for item in data
                        if isinstance(item, dict)
                        and str(item.get("system_name") or "").strip() == system_name
                        and str(item.get("knowledge_type") or "").strip() in {"document", "code", "capability_item"}
                    ]
                    related.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
                    samples = []
                    for item in self._select_knowledge_samples(related, max_items=self._sample_max_items()):
                        content = str(item.get("content") or "").strip()
                        if not content:
                            continue
                        samples.append(content[: self._sample_item_max_chars()])
                    parts.append("【文档/代码材料片段】")
                    parts.append(f"chunks_total={len(related)}")
                    if samples:
                        parts.append("\n---\n".join(samples))
        except Exception as exc:
            logger.info("收集知识库上下文失败（忽略）: %s", exc)

        return "\n".join(parts).strip()[: self._context_max_chars()] if parts else ""

    def _build_context_bundle(
        self,
        *,
        system_id: str,
        system_name: str,
        context_override: Optional[Dict[str, Any]] = None,
    ) -> SummaryContextBundle:
        override = context_override if isinstance(context_override, dict) else {}
        document_text = str(override.get("document_text") or "").strip()
        static_prefix_text = self._build_static_context(system_id=system_id, system_name=system_name)

        if document_text:
            if not static_prefix_text:
                static_prefix_text = f"系统：{system_name}（{system_id}）。"
            return SummaryContextBundle(
                static_prefix_text=static_prefix_text,
                chunkable_body_text=document_text,
            )

        knowledge_context = self._build_knowledge_context(system_name=system_name)
        if not static_prefix_text and not knowledge_context:
            static_prefix_text = f"系统：{system_name}（{system_id}）。材料不足。"
        return SummaryContextBundle(
            static_prefix_text=static_prefix_text,
            chunkable_body_text=knowledge_context,
        )

    def _compose_context_text(self, *, bundle: SummaryContextBundle, body_text: Optional[str] = None) -> str:
        parts = [
            str(bundle.static_prefix_text or "").strip(),
            str(body_text if body_text is not None else bundle.chunkable_body_text or "").strip(),
        ]
        return "\n".join(part for part in parts if part).strip()

    def _build_context(self, *, system_id: str, system_name: str) -> str:
        bundle = self._build_context_bundle(system_id=system_id, system_name=system_name)
        combined = self._compose_context_text(bundle=bundle)
        if combined:
            return combined[: self._context_max_chars()]
        return f"系统：{system_name}（{system_id}）。材料不足。"

    def _context_max_chars(self) -> int:
        value = int(getattr(settings, "PROFILE_SUMMARY_CONTEXT_MAX_CHARS", 120000) or 120000)
        return max(value, 12000)

    def _sample_max_items(self) -> int:
        value = int(getattr(settings, "PROFILE_SUMMARY_SAMPLE_MAX_ITEMS", 48) or 48)
        return max(value, 12)

    def _sample_item_max_chars(self) -> int:
        value = int(getattr(settings, "PROFILE_SUMMARY_SAMPLE_ITEM_MAX_CHARS", 1200) or 1200)
        return max(value, 300)

    def _extract_chunk_index(self, item: Dict[str, Any]) -> Optional[int]:
        metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        raw_chunk_index = metadata.get("chunk_index")
        if raw_chunk_index is None:
            return None
        try:
            return int(raw_chunk_index)
        except (TypeError, ValueError):
            return None

    def _select_knowledge_samples(self, related: List[Dict[str, Any]], max_items: int = 12) -> List[Dict[str, Any]]:
        if not related:
            return []

        if len(related) <= max_items:
            selected = list(related)
        else:
            latest = related[0] if isinstance(related[0], dict) else {}
            latest_metadata = latest.get("metadata") if isinstance(latest.get("metadata"), dict) else {}
            latest_source = str(latest_metadata.get("source_filename") or latest.get("source_file") or "").strip()

            source_related: List[Dict[str, Any]] = []
            if latest_source:
                for item in related:
                    if not isinstance(item, dict):
                        continue
                    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
                    source_name = str(metadata.get("source_filename") or item.get("source_file") or "").strip()
                    if source_name == latest_source:
                        source_related.append(item)

            candidate = source_related if source_related else related

            candidate_with_index = [
                (item, self._extract_chunk_index(item))
                for item in candidate
                if isinstance(item, dict)
            ]
            candidate_with_index = [
                (item, idx)
                for item, idx in candidate_with_index
                if idx is not None
            ]

            if candidate_with_index:
                candidate_with_index.sort(key=lambda pair: pair[1])
                ordered = [item for item, _ in candidate_with_index]
                if len(ordered) <= max_items:
                    selected = ordered
                else:
                    selected = []
                    total = len(ordered)
                    for i in range(max_items):
                        slot = round(i * (total - 1) / (max_items - 1))
                        chosen = ordered[slot]
                        if chosen not in selected:
                            selected.append(chosen)
            else:
                head_count = max_items // 2
                tail_count = max_items - head_count
                selected = candidate[:head_count] + candidate[-tail_count:]
                deduped: List[Dict[str, Any]] = []
                seen_keys = set()
                for item in selected:
                    item_key = (
                        str(item.get("id") or ""),
                        str(item.get("created_at") or ""),
                        str((item.get("metadata") or {}).get("chunk_index") if isinstance(item.get("metadata"), dict) else ""),
                        str((item.get("metadata") or {}).get("source_filename") if isinstance(item.get("metadata"), dict) else ""),
                    )
                    if item_key in seen_keys:
                        continue
                    seen_keys.add(item_key)
                    deduped.append(item)
                selected = deduped

        selected.sort(
            key=lambda item: (
                self._extract_chunk_index(item) if self._extract_chunk_index(item) is not None else 10**9,
                str(item.get("created_at") or ""),
            )
        )
        return selected[:max_items]

    def _infer_domains_from_context(self, context: str) -> List[str]:
        haystack = str(context or "").lower()
        inferred: List[str] = []
        for domain, keywords in DOMAIN_HINT_KEYWORDS.items():
            if domain not in PROFILE_DOMAIN_KEYS:
                continue
            if any(str(keyword or "").lower() in haystack for keyword in keywords):
                inferred.append(domain)
        return inferred

    def _normalize_relevant_domains(self, raw_domains: Any) -> List[str]:
        if isinstance(raw_domains, str):
            candidates = [part.strip() for part in raw_domains.split(",") if part.strip()]
        elif isinstance(raw_domains, list):
            candidates = [str(item).strip() for item in raw_domains if str(item).strip()]
        else:
            candidates = []

        normalized: List[str] = []
        for item in candidates:
            if item in PROFILE_DOMAIN_KEYS and item not in normalized:
                normalized.append(item)
        return normalized

    def _normalize_related_systems(self, raw_systems: Any, *, current_system_name: str) -> List[str]:
        if isinstance(raw_systems, str):
            candidates = [part.strip() for part in raw_systems.split(",") if part.strip()]
        elif isinstance(raw_systems, list):
            candidates = [str(item).strip() for item in raw_systems if str(item).strip()]
        else:
            candidates = []

        current_name = str(current_system_name or "").strip().lower()
        normalized: List[str] = []
        for item in candidates:
            if item.lower() == current_name:
                continue
            if item not in normalized:
                normalized.append(item)
        return normalized

    def _build_multi_system_notifications(
        self,
        *,
        system_name: str,
        related_systems: List[str],
    ) -> List[Dict[str, Any]]:
        systems = self._normalize_related_systems(related_systems, current_system_name=system_name)
        if not systems:
            return []

        joined_names = "、".join(systems)
        return [
            {
                "type": "multi_system_detected",
                "systems": systems,
                "message": f"检测到文档中还包含系统 {joined_names} 的信息，如需更新请前往对应系统操作",
            }
        ]

    def _build_stage1_prompt(self, *, system_id: str, system_name: str, context_text: str) -> str:
        context_window = (context_text or "")[: self._context_max_chars()]
        return f"""请基于以下材料判断系统画像相关域，并识别材料中提及的其他系统。

系统：{system_name}（system_id={system_id}）
材料（可能不完整）：
{context_window}

分析要求：
1. 忽略目录，忽略封面，忽略页码行、章节列表等文档噪声。
2. 只有标题、没有正文支撑的信息，不作为域识别依据。
3. 仅根据正文中的明确事实判断相关域。

请只返回JSON（不要解释），格式：
{{
  "relevant_domains": ["system_positioning", "business_capabilities"],
  "related_systems": ["系统A", "系统B"]
}}
relevant_domains 只允许以下值：
system_positioning, business_capabilities, integration_interfaces, technical_architecture, constraints_risks
"""

    def _build_stage2_prompt(
        self,
        *,
        system_id: str,
        system_name: str,
        relevant_domains: List[str],
        context_text: str,
    ) -> str:
        context_window = (context_text or "")[: self._context_max_chars()]
        return f"""请基于以下材料，仅输出相关域的系统画像建议。

系统：{system_name}（system_id={system_id}）
相关域：{", ".join(relevant_domains)}
材料（可能不完整）：
{context_window}

分析要求：
1. 忽略目录，忽略封面，忽略页码行、章节列表等文档噪声。
2. 只有标题、没有正文支撑的信息，不得作为建议依据。
3. 输出必须是归纳后的系统画像建议，不得复制目录条目、章节列表或页码文本。

请只返回JSON（不要解释），格式：
{{
  "suggestions": {{
    "system_positioning": {{
      "core_responsibility": "系统职责文本",
      "target_users": ["用户类型1", "用户类型2"],
      "business_domains": ["业务域1", "业务域2"]
    }},
    "business_capabilities": {{
      "functional_modules": [{{"name": "模块名", "description": "模块职责"}}],
      "business_flows": [{{"name": "流程名", "description": "流程说明"}}]
    }},
    "integration_interfaces": {{
      "other_integrations": [{{"peer_system": "对端系统", "protocol": "协议", "direction": "方向", "description": "描述"}}],
      "external_dependencies": ["外部依赖1", "外部依赖2"]
    }},
    "technical_architecture": {{
      "architecture_style": "架构定位文本",
      "tech_stack": ["技术栈1", "技术栈2"],
      "performance_profile": {{"指标名": "指标值"}}
    }},
    "constraints_risks": {{
      "prerequisites": [{{"name": "前提条件", "description": "前提说明"}}],
      "risk_items": [{{"name": "风险1", "impact": "风险影响"}}]
    }}
  }}
}}
只填充相关域；不相关域可以省略。每个域内的字段尽量填充，如果材料中没有信息则使用空值（空字符串/空数组/空对象）。
"""

    def _log_chunk_metric(
        self,
        *,
        stage: str,
        chunk_index: Optional[int],
        estimated_tokens: int,
        latency_ms: int,
        usage: Dict[str, int],
    ) -> None:
        payload = {
            "stage": stage,
            "chunk_index": chunk_index,
            "estimated_tokens": estimated_tokens,
            "latency_ms": latency_ms,
        }
        if usage.get("total_tokens") is not None:
            payload["actual_total_tokens"] = usage["total_tokens"]
        logger.info("profile_summary_chunk_metric %s", payload)

    def _calculate_body_budget(
        self,
        *,
        system_id: str,
        system_name: str,
        static_prefix_text: str,
    ) -> int:
        static_prefix_tokens = estimate_tokens(static_prefix_text)
        stage1_prompt_overhead = estimate_tokens(
            self._build_stage1_prompt(system_id=system_id, system_name=system_name, context_text="")
        )
        stage2_prompt_overhead = estimate_tokens(
            self._build_stage2_prompt(
                system_id=system_id,
                system_name=system_name,
                relevant_domains=list(PROFILE_DOMAIN_KEYS),
                context_text="",
            )
        )
        safety_tokens = 1000
        stage1_budget = min(
            settings.LLM_INPUT_MAX_TOKENS,
            settings.LLM_MAX_CONTEXT_TOKENS - 600 - safety_tokens - stage1_prompt_overhead - static_prefix_tokens,
        )
        stage2_budget = min(
            settings.LLM_INPUT_MAX_TOKENS,
            settings.LLM_MAX_CONTEXT_TOKENS - 2500 - safety_tokens - stage2_prompt_overhead - static_prefix_tokens,
        )
        return max(1, min(stage1_budget, stage2_budget))

    def _normalize_named_suggestion_items(self, value: Any) -> List[Dict[str, str]]:
        items = value if isinstance(value, list) else [value]
        normalized: List[Dict[str, str]] = []
        for item in items:
            if isinstance(item, dict):
                name = str(
                    item.get("name")
                    or item.get("module_name")
                    or item.get("title")
                    or item.get("category")
                    or item.get("description")
                    or ""
                ).strip()
                description = str(
                    item.get("description")
                    or item.get("desc")
                    or item.get("summary")
                    or item.get("purpose")
                    or ""
                ).strip()
                functions = item.get("functions")
                if not description and isinstance(functions, list):
                    function_descs = []
                    for function in functions:
                        if not isinstance(function, dict):
                            continue
                        function_name = str(function.get("name") or "").strip()
                        function_desc = str(function.get("desc") or function.get("description") or "").strip()
                        if function_name and function_desc:
                            function_descs.append(f"{function_name}:{function_desc}")
                        elif function_name:
                            function_descs.append(function_name)
                    description = "；".join(function_descs)
            else:
                name = str(item or "").strip()
                description = ""

            if not name and not description:
                continue
            if not name:
                name = description
                description = ""
            normalized.append({"name": name, "description": description})
        return normalized

    def _normalize_risk_suggestion_items(self, value: Any) -> List[Dict[str, str]]:
        items = value if isinstance(value, list) else [value]
        normalized: List[Dict[str, str]] = []
        for item in items:
            if isinstance(item, dict):
                name = str(item.get("name") or item.get("title") or item.get("description") or "").strip()
                impact = str(item.get("impact") or item.get("impact_level") or item.get("notes") or "").strip()
            else:
                name = str(item or "").strip()
                impact = ""
            if not name and not impact:
                continue
            if not name:
                name = impact
                impact = ""
            normalized.append({"name": name, "impact": impact})
        return normalized

    def _normalize_stage2_suggestions(self, stage2_parsed: Any) -> Dict[str, Any]:
        suggestions: Dict[str, Any] = {}
        if isinstance(stage2_parsed, dict):
            nested = stage2_parsed.get("suggestions")
            if isinstance(nested, dict):
                suggestions = nested
            elif isinstance(stage2_parsed.get("profile_data"), dict):
                suggestions = stage2_parsed.get("profile_data") or {}
            else:
                suggestions = stage2_parsed

        normalized_suggestions: Dict[str, Any] = {}
        for domain_key, domain_value in suggestions.items():
            if not isinstance(domain_value, dict):
                continue

            normalized_domain: Dict[str, Any] = {}

            if domain_key == "system_positioning":
                normalized_domain["core_responsibility"] = domain_value.get(
                    "core_responsibility",
                    domain_value.get("system_description", domain_value.get("description", "")),
                )
                normalized_domain["target_users"] = domain_value.get("target_users", [])
                normalized_domain["business_domains"] = domain_value.get("business_domains", domain_value.get("business_domain", []))

            elif domain_key == "business_capabilities":
                desc = domain_value.get("description", "")
                normalized_domain["functional_modules"] = self._normalize_named_suggestion_items(
                    domain_value.get("functional_modules", domain_value.get("module_structure", []))
                )
                normalized_domain["business_flows"] = self._normalize_named_suggestion_items(
                    domain_value.get("business_flows", domain_value.get("core_processes", []))
                )
                if desc and not normalized_domain["business_flows"]:
                    normalized_domain["business_flows"] = [{"name": desc, "description": ""}]

            elif domain_key == "integration_interfaces":
                desc = domain_value.get("description", "")
                normalized_domain["other_integrations"] = domain_value.get(
                    "other_integrations",
                    domain_value.get("integration_points", []),
                )
                normalized_domain["external_dependencies"] = domain_value.get("external_dependencies", [])
                if desc and not normalized_domain["external_dependencies"]:
                    normalized_domain["external_dependencies"] = [desc]

            elif domain_key == "technical_architecture":
                normalized_domain["architecture_style"] = domain_value.get(
                    "architecture_style",
                    domain_value.get("architecture_positioning", domain_value.get("description", "")),
                )
                normalized_domain["tech_stack"] = domain_value.get("tech_stack", [])
                normalized_domain["performance_profile"] = domain_value.get("performance_profile", {})

            elif domain_key == "constraints_risks":
                desc = domain_value.get("description", "")
                normalized_domain["prerequisites"] = self._normalize_named_suggestion_items(
                    domain_value.get("prerequisites", domain_value.get("key_constraints", []))
                )
                normalized_domain["risk_items"] = self._normalize_risk_suggestion_items(
                    domain_value.get("risk_items", domain_value.get("known_risks", []))
                )
                if desc and not normalized_domain["risk_items"]:
                    normalized_domain["risk_items"] = [{"name": desc, "impact": ""}]

            if normalized_domain:
                normalized_suggestions[domain_key] = normalized_domain

        return normalized_suggestions

    def _execute_stage1(
        self,
        *,
        system_id: str,
        system_name: str,
        context_text: str,
        chunk_index: Optional[int],
        estimated_tokens: int,
        llm_timeout: Optional[float] = None,
        llm_retry_times: int = 3,
    ) -> Dict[str, Any]:
        stage1_prompt = self._build_stage1_prompt(
            system_id=system_id,
            system_name=system_name,
            context_text=context_text,
        )
        started_at = time.perf_counter()
        response = llm_client._chat_raw(
            [
                {"role": "system", "content": "你是一个严谨的系统分析助手，擅长从材料中识别系统画像相关域和跨系统信息。"},
                {"role": "user", "content": stage1_prompt},
            ],
            temperature=0.1,
            max_tokens=600,
            retry_times=max(int(llm_retry_times or 1), 1),
            timeout=llm_timeout,
        )
        latency_ms = int((time.perf_counter() - started_at) * 1000)
        usage = extract_usage_from_response(response)
        self._log_chunk_metric(
            stage="stage1",
            chunk_index=chunk_index,
            estimated_tokens=estimated_tokens,
            latency_ms=latency_ms,
            usage=usage,
        )
        stage1_text = response.choices[0].message.content
        stage1_parsed = llm_client.extract_json(stage1_text)
        stage1_data = stage1_parsed if isinstance(stage1_parsed, dict) else {}
        if "relevant_domains" not in stage1_data or "related_systems" not in stage1_data:
            raise ValueError("CHUNK_PROCESSING_FAILED")
        relevant_domains = self._normalize_relevant_domains(stage1_data.get("relevant_domains"))
        inferred_domains = self._infer_domains_from_context(context_text)
        for domain in inferred_domains:
            if domain not in relevant_domains:
                relevant_domains.append(domain)
        return {
            "relevant_domains": relevant_domains,
            "related_systems": self._normalize_related_systems(
            stage1_data.get("related_systems"),
            current_system_name=system_name,
            ),
        }

    def _execute_stage2(
        self,
        *,
        system_id: str,
        system_name: str,
        context_text: str,
        relevant_domains: List[str],
        chunk_index: Optional[int],
        estimated_tokens: int,
        llm_timeout: Optional[float] = None,
        llm_retry_times: int = 3,
    ) -> Dict[str, Any]:
        stage2_prompt = self._build_stage2_prompt(
            system_id=system_id,
            system_name=system_name,
            relevant_domains=relevant_domains,
            context_text=context_text,
        )
        started_at = time.perf_counter()
        response = llm_client._chat_raw(
            [
                {"role": "system", "content": "你是一个严谨的系统分析助手，擅长输出结构化系统画像建议。"},
                {"role": "user", "content": stage2_prompt},
            ],
            temperature=0.2,
            max_tokens=2500,
            retry_times=max(int(llm_retry_times or 1), 1),
            timeout=llm_timeout,
        )
        latency_ms = int((time.perf_counter() - started_at) * 1000)
        usage = extract_usage_from_response(response)
        self._log_chunk_metric(
            stage="stage2",
            chunk_index=chunk_index,
            estimated_tokens=estimated_tokens,
            latency_ms=latency_ms,
            usage=usage,
        )
        stage2_text = response.choices[0].message.content
        logger.info("LLM Stage2 原始响应: %s", stage2_text[:500])
        stage2_parsed = llm_client.extract_json(stage2_text)
        logger.info("LLM Stage2 解析结果: %s", json.dumps(stage2_parsed, ensure_ascii=False)[:500])
        normalized_suggestions = self._normalize_stage2_suggestions(stage2_parsed)
        logger.info("标准化后 suggestions: %s", json.dumps(normalized_suggestions, ensure_ascii=False)[:500])
        return normalized_suggestions

    def _call_llm(
        self,
        *,
        system_id: str,
        system_name: str,
        context: Optional[str] = None,
        context_bundle: Optional[SummaryContextBundle] = None,
        llm_timeout: Optional[float] = None,
        llm_retry_times: int = 3,
        allow_chunking: Optional[bool] = None,
    ) -> Dict[str, Any]:
        bundle = context_bundle or SummaryContextBundle(
            static_prefix_text="",
            chunkable_body_text=str(context or ""),
        )
        normalized_retry_times = max(int(llm_retry_times or 1), 1)
        chunking_enabled = getattr(settings, "ENABLE_LLM_CHUNKING", True) if allow_chunking is None else bool(allow_chunking)
        body_budget = self._calculate_body_budget(
            system_id=system_id,
            system_name=system_name,
            static_prefix_text=bundle.static_prefix_text,
        )
        body_text = str(bundle.chunkable_body_text or "")
        body_tokens = estimate_tokens(body_text)

        if body_tokens <= body_budget:
            context_text = self._compose_context_text(bundle=bundle)
            stage1_result = self._execute_stage1(
                system_id=system_id,
                system_name=system_name,
                context_text=context_text,
                chunk_index=None,
                estimated_tokens=body_tokens,
                llm_timeout=llm_timeout,
                llm_retry_times=normalized_retry_times,
            )
            relevant_domains = stage1_result.get("relevant_domains") or list(PROFILE_DOMAIN_KEYS)
            stage2_suggestions = self._execute_stage2(
                system_id=system_id,
                system_name=system_name,
                context_text=context_text,
                relevant_domains=relevant_domains,
                chunk_index=None,
                estimated_tokens=body_tokens,
                llm_timeout=llm_timeout,
                llm_retry_times=normalized_retry_times,
            )
            return {
                "suggestions": stage2_suggestions if isinstance(stage2_suggestions, dict) else {},
                "relevant_domains": relevant_domains,
                "related_systems": stage1_result.get("related_systems") or [],
            }

        if not chunking_enabled:
            raise ValueError("CHUNKING_DISABLED_OVERSIZE")

        chunks = chunk_text(
            body_text,
            max_tokens=body_budget,
            overlap_paragraphs=getattr(settings, "LLM_CHUNK_OVERLAP_PARAGRAPHS", 2),
        )

        stage1_results = []
        for chunk in chunks:
            context_text = self._compose_context_text(bundle=bundle, body_text=chunk.content)
            stage1_results.append(
                self._execute_stage1(
                    system_id=system_id,
                    system_name=system_name,
                    context_text=context_text,
                    chunk_index=chunk.chunk_index,
                    estimated_tokens=chunk.estimated_tokens,
                    llm_timeout=llm_timeout,
                    llm_retry_times=normalized_retry_times,
                )
            )

        merged_stage1 = merge_stage1_responses(stage1_results)
        relevant_domains = merged_stage1.get("relevant_domains") or list(PROFILE_DOMAIN_KEYS)
        merged_suggestions: Dict[str, Any] = {}

        for chunk in chunks:
            context_text = self._compose_context_text(bundle=bundle, body_text=chunk.content)
            chunk_suggestions = self._execute_stage2(
                system_id=system_id,
                system_name=system_name,
                context_text=context_text,
                relevant_domains=relevant_domains,
                chunk_index=chunk.chunk_index,
                estimated_tokens=chunk.estimated_tokens,
                llm_timeout=llm_timeout,
                llm_retry_times=normalized_retry_times,
            )
            merged_suggestions = deep_merge(merged_suggestions, chunk_suggestions)

        return {
            "suggestions": merged_suggestions,
            "relevant_domains": relevant_domains,
            "related_systems": merged_stage1.get("related_systems") or [],
        }


_profile_summary_service: Optional[ProfileSummaryService] = None


def get_profile_summary_service() -> ProfileSummaryService:
    global _profile_summary_service
    if _profile_summary_service is None:
        _profile_summary_service = ProfileSummaryService()
    return _profile_summary_service
