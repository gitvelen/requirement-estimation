"""
系统画像 AI 总结服务（异步）

对齐 requirements REQ-024 / API-018：
- 触发：代码扫描入库/ESB导入/知识导入（绑定系统）成功后；或 API-018 手动重试
- 输出：system_profile.ai_suggestions + ai_suggestions_updated_at
- 通知：summary_ready / summary_failed（发送给系统主责）
- 幂等：同一 system 同一时刻最多一个运行中任务；有运行中任务直接复用 job_id
"""

from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from backend.api import system_routes
from backend.config.config import settings
from backend.service.code_scan_service import get_code_scan_service
from backend.service.esb_service import get_esb_service
from backend.service.system_profile_service import PROFILE_V24_DOMAIN_KEYS, get_system_profile_service
from backend.utils.llm_client import llm_client

logger = logging.getLogger(__name__)


PROFILE_DOMAIN_KEYS = tuple(PROFILE_V24_DOMAIN_KEYS)


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
    ) -> None:
        profile_service = get_system_profile_service()

        owner_info = system_routes.resolve_system_owner(system_id=system_id)
        owner_user_id = str(owner_info.get("resolved_owner_id") or "").strip()

        with self._get_system_lock(system_id):
            profile_service.update_extraction_task_status(system_id, task_id=job_id, status="processing")

            try:
                context = self._build_context(system_id=system_id, system_name=system_name)
                llm_result = self._call_llm(system_id=system_id, system_name=system_name, context=context)
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

    def _build_context(self, *, system_id: str, system_name: str) -> str:
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
            esb = get_esb_service()
            with esb._lock():  # noqa: SLF001 - internal lock reused for read
                store = esb._load_unlocked()  # noqa: SLF001 - file store, safe for internal read
            entries = store.get("entries") or []
            related = []
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                pid = str(entry.get("provider_system_id") or "").strip()
                cid = str(entry.get("consumer_system_id") or "").strip()
                if system_id not in {pid, cid}:
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

        # knowledge_store (local only, best-effort)
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
                    for item in related[:12]:
                        content = str(item.get("content") or "").strip()
                        if not content:
                            continue
                        samples.append(content[:500])
                    parts.append("【文档/代码材料片段】")
                    parts.append(f"chunks_total={len(related)}")
                    if samples:
                        parts.append("\n---\n".join(samples))
        except Exception as exc:
            logger.info("收集知识库上下文失败（忽略）: %s", exc)

        joined = "\n".join(parts).strip()
        if not joined:
            return f"系统：{system_name}（{system_id}）。材料不足。"
        return joined[:12000]

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

    def _call_llm(self, *, system_id: str, system_name: str, context: str) -> Dict[str, Any]:
        stage1_prompt = f"""请基于以下材料判断系统画像相关域，并识别材料中提及的其他系统。

系统：{system_name}（system_id={system_id}）
材料（可能不完整）：
{(context or '')[:9000]}

请只返回JSON（不要解释），格式：
{{
  "relevant_domains": ["system_positioning", "business_capabilities"],
  "related_systems": ["系统A", "系统B"]
}}
relevant_domains 只允许以下值：
system_positioning, business_capabilities, integration_interfaces, technical_architecture, constraints_risks
"""
        stage1_response = llm_client.chat_with_system_prompt(
            system_prompt="你是一个严谨的系统分析助手，擅长从材料中识别系统画像相关域和跨系统信息。",
            user_prompt=stage1_prompt,
            temperature=0.1,
            max_tokens=600,
        )
        stage1_parsed = llm_client.extract_json(stage1_response)
        stage1_data = stage1_parsed if isinstance(stage1_parsed, dict) else {}
        relevant_domains = self._normalize_relevant_domains(stage1_data.get("relevant_domains"))
        related_systems = self._normalize_related_systems(
            stage1_data.get("related_systems"),
            current_system_name=system_name,
        )

        if not relevant_domains:
            relevant_domains = list(PROFILE_DOMAIN_KEYS)

        stage2_prompt = f"""请基于以下材料，仅输出相关域的系统画像建议。

系统：{system_name}（system_id={system_id}）
相关域：{", ".join(relevant_domains)}
材料（可能不完整）：
{(context or '')[:9000]}

请只返回JSON（不要解释），格式：
{{
  "suggestions": {{
    "system_positioning": {{
      "system_description": "系统描述文本",
      "target_users": ["用户类型1", "用户类型2"],
      "boundaries": ["边界说明1", "边界说明2"]
    }},
    "business_capabilities": {{
      "module_structure": [{{"module_name": "模块名", "functions": [{{"name": "功能名", "desc": "功能描述"}}]}}],
      "core_processes": ["核心流程1", "核心流程2"]
    }},
    "integration_interfaces": {{
      "integration_points": [{{"peer_system": "对端系统", "protocol": "协议", "direction": "方向", "description": "描述"}}],
      "external_dependencies": ["外部依赖1", "外部依赖2"]
    }},
    "technical_architecture": {{
      "architecture_positioning": "架构定位文本",
      "tech_stack": ["技术栈1", "技术栈2"],
      "performance_profile": {{"指标名": "指标值"}}
    }},
    "constraints_risks": {{
      "key_constraints": [{{"category": "约束类别", "description": "约束描述"}}],
      "known_risks": ["风险1", "风险2"]
    }}
  }}
}}
只填充相关域；不相关域可以省略。每个域内的字段尽量填充，如果材料中没有信息则使用空值（空字符串/空数组/空对象）。
"""
        stage2_response = llm_client.chat_with_system_prompt(
            system_prompt="你是一个严谨的系统分析助手，擅长输出结构化系统画像建议。",
            user_prompt=stage2_prompt,
            temperature=0.2,
            max_tokens=2500,
        )
        logger.info(f"LLM Stage2 原始响应: {stage2_response[:500]}")
        stage2_parsed = llm_client.extract_json(stage2_response)
        logger.info(f"LLM Stage2 解析结果: {json.dumps(stage2_parsed, ensure_ascii=False)[:500]}")

        suggestions: Dict[str, Any] = {}
        if isinstance(stage2_parsed, dict):
            nested = stage2_parsed.get("suggestions")
            if isinstance(nested, dict):
                suggestions = nested
            elif isinstance(stage2_parsed.get("profile_data"), dict):
                suggestions = stage2_parsed.get("profile_data") or {}
            else:
                suggestions = stage2_parsed

        # 转换 LLM 返回的简化结构到前端期望的详细结构
        normalized_suggestions = {}
        for domain_key, domain_value in suggestions.items():
            if not isinstance(domain_value, dict):
                continue

            normalized_domain = {}

            if domain_key == "system_positioning":
                # 优先使用 LLM 返回的正确字段名，否则尝试 description 字段
                normalized_domain["system_description"] = domain_value.get("system_description", domain_value.get("description", ""))
                normalized_domain["target_users"] = domain_value.get("target_users", [])
                normalized_domain["boundaries"] = domain_value.get("boundaries", [])

            elif domain_key == "business_capabilities":
                desc = domain_value.get("description", "")
                normalized_domain["module_structure"] = domain_value.get("module_structure", [])
                normalized_domain["core_processes"] = domain_value.get("core_processes", [])
                # 如果只有 description，尝试解析为 core_processes
                if desc and not normalized_domain["core_processes"]:
                    normalized_domain["core_processes"] = [desc]

            elif domain_key == "integration_interfaces":
                desc = domain_value.get("description", "")
                normalized_domain["integration_points"] = domain_value.get("integration_points", [])
                normalized_domain["external_dependencies"] = domain_value.get("external_dependencies", [])
                # 如果只有 description，尝试解析为 external_dependencies
                if desc and not normalized_domain["external_dependencies"]:
                    normalized_domain["external_dependencies"] = [desc]

            elif domain_key == "technical_architecture":
                normalized_domain["architecture_positioning"] = domain_value.get("architecture_positioning", domain_value.get("description", ""))
                normalized_domain["tech_stack"] = domain_value.get("tech_stack", [])
                normalized_domain["performance_profile"] = domain_value.get("performance_profile", {})

            elif domain_key == "constraints_risks":
                desc = domain_value.get("description", "")
                normalized_domain["key_constraints"] = domain_value.get("key_constraints", [])
                normalized_domain["known_risks"] = domain_value.get("known_risks", [])
                # 如果只有 description，尝试解析为 known_risks
                if desc and not normalized_domain["known_risks"]:
                    normalized_domain["known_risks"] = [desc]

            if normalized_domain:
                normalized_suggestions[domain_key] = normalized_domain

        logger.info(f"标准化后 suggestions: {json.dumps(normalized_suggestions, ensure_ascii=False)[:500]}")

        if not relevant_domains and isinstance(suggestions, dict):
            relevant_domains = [domain for domain in PROFILE_DOMAIN_KEYS if domain in suggestions]

        return {
            "suggestions": normalized_suggestions if isinstance(normalized_suggestions, dict) else {},
            "relevant_domains": relevant_domains,
            "related_systems": related_systems,
        }


_profile_summary_service: Optional[ProfileSummaryService] = None


def get_profile_summary_service() -> ProfileSummaryService:
    global _profile_summary_service
    if _profile_summary_service is None:
        _profile_summary_service = ProfileSummaryService()
    return _profile_summary_service
