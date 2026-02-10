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
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List, Optional

from backend.api import system_routes
from backend.config.config import settings
from backend.service.code_scan_service import get_code_scan_service
from backend.service.esb_service import get_esb_service
from backend.service.system_profile_service import get_system_profile_service
from backend.utils.llm_client import llm_client

logger = logging.getLogger(__name__)


PROFILE_FIELDS = [
    "in_scope",
    "out_of_scope",
    "core_functions",
    "business_goals",
    "business_objects",
    "integration_points",
    "key_constraints",
]


class ProfileSummaryService:
    def __init__(self) -> None:
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="profile_summary")

    def trigger_summary(
        self,
        *,
        system_id: str,
        system_name: str,
        actor: Optional[Dict[str, Any]] = None,
        reason: str = "import",
    ) -> Dict[str, Any]:
        normalized_system_id = str(system_id or "").strip()
        normalized_system_name = str(system_name or "").strip()
        if not normalized_system_id or not normalized_system_name:
            raise ValueError("system_id/system_name不能为空")

        profile_service = get_system_profile_service()
        job = profile_service.get_or_create_ai_suggestions_job(
            normalized_system_name,
            normalized_system_id,
            actor=actor,
        )
        if not job.get("created_new"):
            return job

        job_id = str(job.get("job_id") or "").strip()
        if not job_id:
            return job

        self.executor.submit(
            self._run_job,
            system_id=normalized_system_id,
            system_name=normalized_system_name,
            job_id=job_id,
            reason=str(reason or "").strip() or "import",
        )
        return job

    def _run_job(self, *, system_id: str, system_name: str, job_id: str, reason: str) -> None:
        profile_service = get_system_profile_service()
        profile_service.update_ai_suggestions_job(system_name, job_id=job_id, status="running")

        owner_info = system_routes.resolve_system_owner(system_id=system_id)
        owner_user_id = str(owner_info.get("resolved_owner_id") or "").strip()

        try:
            context = self._build_context(system_id=system_id, system_name=system_name)
            suggestions = self._call_llm(system_id=system_id, system_name=system_name, context=context)

            profile_service.set_ai_suggestions(system_name, suggestions=suggestions)
            profile_service.update_ai_suggestions_job(system_name, job_id=job_id, status="completed")

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
            profile_service.update_ai_suggestions_job(
                system_name,
                job_id=job_id,
                status="failed",
                error_code="SUMMARY_001",
                error_reason=reason_text,
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

    def _call_llm(self, *, system_id: str, system_name: str, context: str) -> Dict[str, str]:
        prompt = f"""请基于以下材料，为系统画像生成7个字段的候选建议（不要求完美，缺信息可留空字符串）。

系统：{system_name}（system_id={system_id}）

材料（可能不完整）：
{(context or '')[:10000]}

请只返回JSON（不要解释），格式如下：
{{
  "in_scope": "",
  "out_of_scope": "",
  "core_functions": "",
  "business_goals": "",
  "business_objects": "",
  "integration_points": "",
  "key_constraints": ""
}}
"""

        response = llm_client.chat_with_system_prompt(
            system_prompt="你是一个严谨的系统分析助手，擅长从材料中总结系统边界、核心功能、业务目标、集成点与关键约束。",
            user_prompt=prompt,
            temperature=0.2,
            max_tokens=1200,
        )

        parsed = llm_client.extract_json(response)
        suggestions: Dict[str, str] = {}
        if isinstance(parsed, dict):
            for key in PROFILE_FIELDS:
                value = parsed.get(key)
                text = "" if value is None else str(value).strip()
                suggestions[key] = text
        else:
            for key in PROFILE_FIELDS:
                suggestions[key] = ""

        return suggestions


_profile_summary_service: Optional[ProfileSummaryService] = None


def get_profile_summary_service() -> ProfileSummaryService:
    global _profile_summary_service
    if _profile_summary_service is None:
        _profile_summary_service = ProfileSummaryService()
    return _profile_summary_service

