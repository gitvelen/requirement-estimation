"""
系统识别Agent
从需求文本中识别涉及改造的所有系统
支持知识库注入，提供系统上下文信息
"""
from __future__ import annotations

import csv
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from backend.api import system_routes
from backend.config.config import settings
from backend.service.system_profile_repository import resolve_system_profile_root
from backend.prompts.prompt_templates import SYSTEM_IDENTIFICATION_PROMPT
from backend.service.memory_service import get_memory_service
from backend.service.system_profile_service import get_system_profile_service
from backend.utils.llm_client import llm_client

logger = logging.getLogger(__name__)


def _normalize_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _normalize_text_list(value: Any) -> List[str]:
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
            .replace("\n", ",")
        )
        raw_items = normalized.split(",")
    else:
        raw_items = [value]

    result: List[str] = []
    for item in raw_items:
        text = _normalize_text(item)
        if text and text not in result:
            result.append(text)
    return result


class DirectDecisionResolver:
    def __init__(self, memory_service=None, profile_service=None) -> None:
        self.memory_service = memory_service or get_memory_service()
        self.profile_service = profile_service or get_system_profile_service()

    def resolve(self, requirement_text: str) -> Optional[Dict[str, Any]]:
        normalized_text = _normalize_text(requirement_text)
        if not normalized_text:
            return None

        systems = system_routes._read_systems()
        if not systems:
            return None

        alias_hits: Dict[str, List[Dict[str, Any]]] = {}
        for system in systems:
            for alias in self._collect_aliases(system):
                if not self._contains_alias(normalized_text, alias):
                    continue
                alias_hits.setdefault(alias, []).append(system)

        if not alias_hits:
            return None

        stable_aliases = [
            alias
            for alias, matched_systems in alias_hits.items()
            if len({str(item.get("id") or item.get("name") or "").strip() for item in matched_systems}) == 1
        ]
        ambiguous_aliases = [
            alias
            for alias, matched_systems in alias_hits.items()
            if len({str(item.get("id") or item.get("name") or "").strip() for item in matched_systems}) > 1
        ]
        selected_systems = self._dedupe_systems(
            [item for alias in stable_aliases for item in alias_hits.get(alias, [])]
        )
        if ambiguous_aliases:
            candidate_systems = self._dedupe_systems([item for alias in ambiguous_aliases for item in alias_hits.get(alias, [])])
            maybe_systems = self._build_maybe_systems(candidate_systems, ambiguous_aliases)
            questions = [f"别名“{alias}”可对应多个系统，请补充标准系统名称。" for alias in ambiguous_aliases]
            if selected_systems:
                selected_names = [item["name"] for item in selected_systems if str(item.get("name") or "").strip()]
                return {
                    "final_verdict": "matched",
                    "selected_systems": selected_systems,
                    "candidate_systems": candidate_systems,
                    "maybe_systems": maybe_systems,
                    "questions": questions,
                    "reason_summary": (
                        f"直接命中稳定系统：{', '.join(selected_names)}；"
                        f"同时存在待确认别名：{', '.join(ambiguous_aliases)}"
                    ),
                    "matched_aliases": stable_aliases,
                    "context_degraded": False,
                    "degraded_reasons": [],
                    "result_status": "success",
                }
            return {
                "final_verdict": "ambiguous",
                "selected_systems": [],
                "candidate_systems": candidate_systems,
                "maybe_systems": maybe_systems,
                "questions": questions,
                "reason_summary": f"直接判定命中了歧义别名：{', '.join(ambiguous_aliases)}",
                "matched_aliases": ambiguous_aliases,
                "context_degraded": False,
                "degraded_reasons": [],
                "result_status": "success",
            }

        matched_aliases = stable_aliases
        return {
            "final_verdict": "matched",
            "selected_systems": selected_systems,
            "candidate_systems": list(selected_systems),
            "maybe_systems": [],
            "questions": [],
            "reason_summary": f"直接命中系统清单稳定别名：{', '.join(matched_aliases)}",
            "matched_aliases": matched_aliases,
            "context_degraded": False,
            "degraded_reasons": [],
            "result_status": "success",
        }

    def _build_maybe_systems(
        self,
        candidate_systems: List[Dict[str, Any]],
        ambiguous_aliases: List[str],
    ) -> List[Dict[str, Any]]:
        reason = f"命中歧义别名“{', '.join(ambiguous_aliases)}”，需补充标准系统名称"
        result: List[Dict[str, Any]] = []
        for item in candidate_systems:
            result.append(
                {
                    "system_id": _normalize_text(item.get("system_id") or item.get("id")),
                    "name": _normalize_text(item.get("name")),
                    "confidence": "低",
                    "reason": reason,
                    "type": item.get("type") or "主系统",
                    "description": item.get("description") or "",
                }
            )
        return result

    def _contains_alias(self, text: str, alias: str) -> bool:
        normalized_alias = _normalize_text(alias)
        if len(normalized_alias) < 2:
            return False
        if normalized_alias.isascii():
            return normalized_alias.lower() in text.lower()
        return normalized_alias in text

    def _collect_aliases(self, system: Dict[str, Any]) -> List[str]:
        aliases: List[str] = []
        name = _normalize_text(system.get("name"))
        abbreviation = _normalize_text(system.get("abbreviation"))
        extra = system.get("extra") if isinstance(system.get("extra"), dict) else {}
        system_id = _normalize_text(system.get("id"))

        for value in (
            name,
            abbreviation,
            extra.get("aliases"),
            extra.get("alias"),
            extra.get("别名"),
            extra.get("系统简称"),
            extra.get("英文简称"),
        ):
            for item in _normalize_text_list(value):
                if item not in aliases:
                    aliases.append(item)

        profile = self.profile_service.get_profile(name) if name else None
        profile_aliases = (
            (((profile or {}).get("profile_data") or {}).get("system_positioning") or {})
            .get("canonical", {})
            .get("extensions", {})
            .get("aliases")
        )
        for item in _normalize_text_list(profile_aliases):
            if item not in aliases:
                aliases.append(item)

        memory_aliases = self._collect_memory_aliases(system_id=system_id, system_name=name)
        for item in memory_aliases:
            if item not in aliases:
                aliases.append(item)

        return aliases

    def _collect_memory_aliases(self, *, system_id: str, system_name: str) -> List[str]:
        aliases: List[str] = []
        try:
            records = self.memory_service.list_records(memory_type="identification_decision", limit=200)
        except Exception as exc:  # pragma: no cover
            logger.debug("读取 identification_decision Memory 失败: %s", exc)
            return aliases

        for record in records:
            payload = record.get("payload") if isinstance(record.get("payload"), dict) else {}
            if str(payload.get("final_verdict") or "").strip() != "matched":
                continue

            selected_systems = payload.get("selected_systems") if isinstance(payload.get("selected_systems"), list) else []
            selected_hit = False
            for system in selected_systems:
                if not isinstance(system, dict):
                    continue
                candidate_id = _normalize_text(system.get("system_id") or system.get("id"))
                candidate_name = _normalize_text(system.get("name"))
                if (system_id and candidate_id == system_id) or (system_name and candidate_name == system_name):
                    selected_hit = True
                    break
            if not selected_hit:
                continue

            for item in _normalize_text_list(payload.get("matched_aliases")):
                if item not in aliases:
                    aliases.append(item)

        return aliases

    def _dedupe_systems(self, systems: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        seen = set()
        for system in systems:
            if not isinstance(system, dict):
                continue
            system_name = _normalize_text(system.get("name"))
            system_id = _normalize_text(system.get("id"))
            key = system_id or system_name
            if not key or key in seen:
                continue
            seen.add(key)
            result.append(
                {
                    "system_id": system_id,
                    "name": system_name,
                    "type": "主系统",
                    "description": "",
                    "confidence": "高",
                    "reasons": [],
                    "is_standard": True,
                }
            )
        return result


class SystemIdentificationAgent:
    """系统识别Agent"""

    def __init__(self, knowledge_service=None):
        """
        初始化Agent

        Args:
            knowledge_service: 知识库服务（可选，用于注入系统知识）
        """
        self.name = "系统识别Agent"
        self.prompt_template = SYSTEM_IDENTIFICATION_PROMPT
        self.system_list = []  # 延迟加载
        self.knowledge_service = knowledge_service
        self.knowledge_enabled = settings.KNOWLEDGE_ENABLED
        self.memory_service = get_memory_service()
        self.profile_service = get_system_profile_service()
        self.direct_resolver = DirectDecisionResolver(
            memory_service=self.memory_service,
            profile_service=self.profile_service,
        )
        self._last_candidate_systems: List[Dict[str, Any]] = []
        self._last_questions: List[str] = []
        self._last_maybe_systems: List[Dict[str, Any]] = []
        self._last_final_verdict: str = "unknown"
        self._last_reason_summary: str = ""
        self._last_matched_aliases: List[str] = []
        self._last_context_degraded: bool = False
        self._last_degraded_reasons: List[str] = []
        self._last_result_status: str = "success"
        self.last_ai_system_analysis: Optional[Dict[str, Any]] = None

        logger.info(f"{self.name}初始化完成（画像上下文：已启用）")

    def _load_system_list(self) -> List[str]:
        """
        加载标准系统列表

        优先级：
        1. data/system_list.csv (CSV格式，系统清单单一数据源)
        """
        system_list = []

        csv_path = os.path.join(settings.REPORT_DIR, "system_list.csv")
        if os.path.exists(csv_path):
            try:
                with open(csv_path, "r", encoding="utf-8", newline="") as f:
                    rows = list(csv.reader(f))
                    if not rows:
                        return system_list

                    header = rows[0]
                    header_map = {str(cell).strip(): idx for idx, cell in enumerate(header) if cell}
                    name_idx = None
                    if "系统名称" in header_map:
                        name_idx = header_map["系统名称"]
                    elif "name" in header_map:
                        name_idx = header_map["name"]

                    data_rows = rows[1:] if name_idx is not None else rows
                    if name_idx is None:
                        name_idx = 0

                    for row in data_rows:
                        if name_idx < len(row):
                            name = str(row[name_idx]).strip() if row[name_idx] is not None else ""
                            if name:
                                system_list.append(name)
                logger.info(f"从data/system_list.csv加载了{len(system_list)}个系统")
                return system_list
            except Exception as e:
                logger.warning(f"加载data/system_list.csv失败: {e}")

        if not system_list:
            logger.info("未找到系统列表文件（MD或CSV），请在前端配置页面添加系统")

        return system_list

    def identify(self, requirement_content: str, task_id: Optional[str] = None) -> List[Dict[str, str]]:
        result = self.identify_with_verdict(requirement_content, task_id=task_id)
        return result.get("selected_systems") or []

    def identify_with_verdict(self, requirement_content: str, task_id: Optional[str] = None) -> Dict[str, Any]:
        try:
            if not self.system_list:
                logger.info("[系统识别] 首次使用，加载系统列表...")
                self.system_list = self._load_system_list()
                logger.info(f"[系统识别] 已加载 {len(self.system_list)} 个标准系统")

            logger.info("[系统识别] 开始识别系统...")
            logger.info(f"[内容长度] {len(requirement_content)} 字符")

            direct_result = self.direct_resolver.resolve(requirement_content)
            if direct_result:
                self._remember_result(direct_result)
                self._write_identification_memory(direct_result, task_id=task_id)
                self.last_ai_system_analysis = self.build_ai_system_analysis(direct_result.get("selected_systems") or [])
                logger.info("[系统识别] 直接判定完成，verdict=%s", direct_result["final_verdict"])
                return direct_result

            llm_result = self._identify_with_llm(requirement_content, task_id=task_id)
            self._remember_result(llm_result)
            self._write_identification_memory(llm_result, task_id=task_id)
            self.last_ai_system_analysis = self.build_ai_system_analysis(llm_result.get("selected_systems") or [])
            logger.info("[系统识别] 识别完成，verdict=%s", llm_result["final_verdict"])
            return llm_result
        except Exception as e:
            logger.error(f"[系统识别] 识别失败: {str(e)}")
            raise

    def _identify_with_llm(self, requirement_content: str, task_id: Optional[str] = None) -> Dict[str, Any]:
        knowledge_context = ""
        system_profiles: List[Dict[str, Any]] = []
        candidate_systems: List[Dict[str, Any]] = []
        try:
            logger.info("[系统识别] 正在组装相关系统画像上下文...")
            system_profiles = self.profile_service.search_relevant_profile_contexts(
                requirement_content,
                limit=max(int(getattr(settings, "KNOWLEDGE_TOP_K", 8) or 8), 3),
            )
            if system_profiles:
                logger.info(f"[系统识别] 命中 {len(system_profiles)} 个相关系统画像")
                candidate_systems = self._build_candidate_systems(system_profiles, limit=8)
                knowledge_context = self._build_knowledge_context(system_profiles)
            else:
                logger.info("[系统识别] 未命中相关系统画像")
        except Exception as e:
            logger.warning(f"[系统识别] 画像上下文组装失败: {e}，继续使用传统方式")

        self._last_candidate_systems = candidate_systems

        user_prompt = f"需求内容：\n\n{requirement_content}\n\n"
        if candidate_systems:
            user_prompt += "【候选系统榜单（来自知识库system_profile命中，JSON）】\n"
            user_prompt += json.dumps(candidate_systems, ensure_ascii=False, indent=2)
            user_prompt += "\n\n"

        if knowledge_context:
            user_prompt += f"\n【系统知识参考】\n{knowledge_context}\n\n"
            user_prompt += "请参考上述系统知识与候选系统榜单，识别该需求涉及的所有系统，并给出置信度与理由。"
        else:
            user_prompt += "请识别该需求涉及的所有系统，并给出置信度与理由。"

        llm_timeout = max(float(getattr(settings, "PROFILE_IMPORT_LLM_TIMEOUT", 5) or 5), 1.0)
        if candidate_systems or knowledge_context:
            # 命中系统画像后，提示词会显著变长，5 秒预算对线上波动过于敏感。
            llm_timeout = max(llm_timeout, 15.0)

        response = llm_client.chat_with_system_prompt(
            system_prompt=self.prompt_template,
            user_prompt=user_prompt,
            temperature=0.3,
            retry_times=max(int(getattr(settings, "PROFILE_IMPORT_LLM_RETRY_TIMES", 1) or 1), 1),
            timeout=llm_timeout,
        )
        result = llm_client.extract_json(response)
        if "systems" not in result:
            raise ValueError("响应中缺少'systems'字段")

        systems = result["systems"]
        questions = result.get("questions") or []
        maybe_systems = result.get("maybe_systems") or []

        if not isinstance(questions, list):
            questions = []
        questions = [str(item).strip() for item in questions if str(item).strip()]

        if not isinstance(maybe_systems, list):
            maybe_systems = []
        normalized_maybe = []
        for item in maybe_systems:
            if isinstance(item, dict) and str(item.get("name") or "").strip():
                normalized_maybe.append(item)
            elif isinstance(item, str) and item.strip():
                normalized_maybe.append({"name": item.strip(), "confidence": "低", "reason": ""})
        maybe_systems = normalized_maybe

        normalized_systems: List[Dict[str, Any]] = []
        for system in systems:
            if "name" not in system:
                raise ValueError("系统缺少'name'字段")

            original_name = system["name"]
            standard_name = self._match_standard_system(original_name)
            normalized_system = dict(system)
            normalized_system["name"] = standard_name
            normalized_system["original_name"] = original_name
            normalized_system.setdefault("type", "主系统")
            normalized_system.setdefault("description", "")
            normalized_system.setdefault("confidence", "中")
            if not isinstance(normalized_system.get("reasons"), list):
                normalized_system["reasons"] = [str(normalized_system.get("reasons"))] if normalized_system.get("reasons") else []
            normalized_systems.append(normalized_system)
            logger.debug(f"  └─ {original_name} → {standard_name}")

        selected_systems = self.validate_and_filter_systems(normalized_systems)
        if selected_systems:
            self.validate_systems(selected_systems)

        final_verdict = self._resolve_final_verdict(selected_systems, maybe_systems)
        reason_summary = self._build_reason_summary(selected_systems, maybe_systems, questions, final_verdict)

        return {
            "final_verdict": final_verdict,
            "selected_systems": selected_systems,
            "candidate_systems": self._last_candidate_systems or [],
            "maybe_systems": maybe_systems[:8],
            "questions": questions[:10],
            "reason_summary": reason_summary,
            "matched_aliases": [],
            "context_degraded": False,
            "degraded_reasons": [],
            "result_status": "success",
        }

    def _resolve_final_verdict(
        self,
        selected_systems: List[Dict[str, Any]],
        maybe_systems: List[Dict[str, Any]],
    ) -> str:
        if selected_systems and (not maybe_systems or self._is_speculative_maybe_set(selected_systems, maybe_systems)):
            return "matched"
        if selected_systems or maybe_systems:
            return "ambiguous"
        return "unknown"

    def _is_speculative_maybe_set(
        self,
        selected_systems: List[Dict[str, Any]],
        maybe_systems: List[Dict[str, Any]],
    ) -> bool:
        if len(selected_systems) != 1 or not maybe_systems:
            return False

        selected_confidence = str(selected_systems[0].get("confidence") or "").strip().lower()
        if selected_confidence not in {"高", "high"}:
            return False

        uncertainty_markers = ("未明确", "未提及", "可能", "待确认", "需进一步确认", "进一步确认")
        for item in maybe_systems:
            if not isinstance(item, dict):
                return False

            maybe_confidence = str(item.get("confidence") or "").strip().lower()
            if maybe_confidence not in {"低", "low"}:
                return False

            maybe_reason = str(item.get("reason") or "").strip()
            if not maybe_reason or not any(marker in maybe_reason for marker in uncertainty_markers):
                return False

        return True

    def _build_reason_summary(
        self,
        selected_systems: List[Dict[str, Any]],
        maybe_systems: List[Dict[str, Any]],
        questions: List[str],
        final_verdict: str,
    ) -> str:
        if final_verdict == "matched":
            names = [str(item.get("name") or "").strip() for item in selected_systems if str(item.get("name") or "").strip()]
            return f"LLM 已给出明确系统结论：{', '.join(names)}"
        if final_verdict == "ambiguous":
            candidate_names = [
                str(item.get("name") or "").strip()
                for item in maybe_systems
                if isinstance(item, dict) and str(item.get("name") or "").strip()
            ]
            if candidate_names:
                return f"LLM 仍保留待确认系统：{', '.join(candidate_names)}"
            if questions:
                return f"LLM 需要补充信息后才能确定：{questions[0]}"
            return "LLM 未形成唯一稳定结论"
        if questions:
            return f"当前无法识别目标系统：{questions[0]}"
        return "当前无法从需求文本中识别出稳定系统结论"

    def _remember_result(self, result: Dict[str, Any]) -> None:
        self._last_candidate_systems = list(result.get("candidate_systems") or [])
        self._last_questions = list(result.get("questions") or [])[:10]
        self._last_maybe_systems = list(result.get("maybe_systems") or [])[:8]
        self._last_final_verdict = str(result.get("final_verdict") or "unknown").strip() or "unknown"
        self._last_reason_summary = str(result.get("reason_summary") or "").strip()
        self._last_matched_aliases = list(result.get("matched_aliases") or [])
        self._last_context_degraded = bool(result.get("context_degraded"))
        self._last_degraded_reasons = list(result.get("degraded_reasons") or [])
        self._last_result_status = str(result.get("result_status") or "success").strip() or "success"

    def _write_identification_memory(self, result: Dict[str, Any], *, task_id: Optional[str]) -> None:
        target_systems = result.get("selected_systems") or result.get("candidate_systems") or []
        if not target_systems:
            return

        errors: List[str] = []
        payload = {
            "task_id": str(task_id or "").strip(),
            "final_verdict": result.get("final_verdict"),
            "selected_systems": result.get("selected_systems") or [],
            "candidate_systems": result.get("candidate_systems") or [],
            "questions": result.get("questions") or [],
            "reason_summary": result.get("reason_summary") or "",
            "matched_aliases": result.get("matched_aliases") or [],
        }

        seen_ids = set()
        for system in target_systems:
            if not isinstance(system, dict):
                continue
            system_id = _normalize_text(system.get("system_id") or system.get("id") or system.get("name"))
            if not system_id or system_id in seen_ids:
                continue
            seen_ids.add(system_id)
            try:
                self.memory_service.append_record(
                    system_id=system_id,
                    memory_type="identification_decision",
                    memory_subtype="system_identification",
                    scene_id="system_identification",
                    source_type="requirement_task",
                    source_id=str(task_id or ""),
                    summary=f"系统识别结论：{result.get('final_verdict')}",
                    payload=payload,
                    decision_policy="direct_decision",
                    confidence=1.0 if result.get("final_verdict") == "matched" else 0.6,
                    actor="system",
                )
            except Exception as exc:  # pragma: no cover
                errors.append(str(exc))

        if errors:
            degraded_reasons = list(result.get("degraded_reasons") or [])
            degraded_reasons.append("identification_memory_write_failed")
            result["context_degraded"] = True
            result["degraded_reasons"] = degraded_reasons
            result["result_status"] = "partial_success"
            result["memory_error"] = "; ".join(errors)

    def _build_candidate_systems(self, system_profiles: List[Dict[str, Any]], limit: int = 8) -> List[Dict[str, Any]]:
        grouped: Dict[str, Dict[str, Any]] = {}
        for item in system_profiles or []:
            if not isinstance(item, dict):
                continue
            name = str(item.get("system_name") or "").strip()
            if not name:
                meta = item.get("metadata") or {}
                if isinstance(meta, dict):
                    name = str(meta.get("system_name") or "").strip()
            if not name:
                continue

            try:
                similarity = float(item.get("score") or item.get("similarity") or 0.0)
            except (TypeError, ValueError):
                similarity = 0.0

            source_file = str(item.get("source_file") or item.get("context_source") or "")
            excerpt = str(item.get("profile_text") or item.get("content") or "")
            excerpt = " ".join(excerpt.split())[:120]

            slot = grouped.setdefault(name, {"name": name, "score": similarity, "kb_hits": []})
            slot["score"] = max(float(slot.get("score") or 0.0), similarity)
            slot["kb_hits"].append(
                {
                    "source_file": source_file,
                    "similarity": round(similarity, 3),
                    "excerpt": excerpt,
                }
            )

        candidates: List[Dict[str, Any]] = []
        for name, slot in grouped.items():
            hits = sorted(slot.get("kb_hits") or [], key=lambda x: x.get("similarity", 0.0), reverse=True)[:2]
            candidates.append({"name": name, "score": round(float(slot.get("score") or 0.0), 3), "kb_hits": hits})

        candidates.sort(key=lambda x: x.get("score", 0.0), reverse=True)
        return candidates[: max(int(limit or 0), 0)] if limit else candidates

    def build_ai_system_analysis(self, systems: List[Dict[str, Any]]) -> Dict[str, Any]:
        """构建可用于前端展示的系统校准分析结果（写入任务，用于人机协作纠偏）。"""
        selected_systems: List[Dict[str, Any]] = []
        for system in systems or []:
            if not isinstance(system, dict):
                continue
            name = str(system.get("name") or "").strip()
            if not name:
                continue

            kb_hits = []
            for cand in self._last_candidate_systems or []:
                if cand.get("name") == name:
                    kb_hits = cand.get("kb_hits") or []
                    break

            selected_systems.append(
                {
                    "name": name,
                    "type": system.get("type") or "主系统",
                    "description": system.get("description") or "",
                    "confidence": system.get("confidence") or "中",
                    "reasons": system.get("reasons") or [],
                    "kb_hits": kb_hits,
                    "system_id": system.get("system_id") or system.get("id") or "",
                }
            )

        missing_profiles = [item["name"] for item in selected_systems if not item.get("kb_hits")]
        analysis = {
            "generated_at": datetime.now().isoformat(),
            "knowledge_enabled": True,
            "candidate_systems": self._last_candidate_systems or [],
            "selected_systems": selected_systems,
            "maybe_systems": self._last_maybe_systems or [],
            "questions": self._last_questions or [],
            "missing_system_profiles": missing_profiles,
            "final_verdict": self._last_final_verdict,
            "reason_summary": self._last_reason_summary,
            "matched_aliases": self._last_matched_aliases or [],
            "context_degraded": self._last_context_degraded,
            "degraded_reasons": self._last_degraded_reasons or [],
            "result_status": self._last_result_status,
        }
        self.last_ai_system_analysis = analysis
        return analysis

    def _match_standard_system(self, system_name: str) -> str:
        """
        匹配标准系统名称

        Args:
            system_name: 识别出的系统名称

        Returns:
            str: 标准系统名称，如果无法匹配返回原值
        """
        if system_name in self.system_list:
            return system_name

        for standard_name in self.system_list:
            if system_name in standard_name or standard_name in system_name:
                return standard_name

        keywords_map = {
            "支付": "支付中台",
            "核心": "新一代核心",
            "企业网银": "企业网银",
            "手机银行": "新移动银行",
            "移动银行": "新移动银行",
            "柜面": "新综合柜面",
            "综合柜面": "新综合柜面",
            "信贷": "综合信贷",
            "贷款": "综合信贷",
            "网银": "企业网银",
            "供应链": "在线供应链融资",
            "同业": "同业",
            "存款": "在线存款",
            "反欺诈": "交易反欺诈",
            "中台": "支付中台",
            "网联": "统一支付",
            "云闪付": "统一支付",
            "银企": "银企对账",
            "银联": "银联电子渠道整合",
            "跨境": "人民币跨境收付",
            "自贸": "自贸区资金监测",
            "票据": "票据交易",
            "理财": "财富管理平台",
            "基金": "财富管理平台",
            "保险": "在线保险销售",
            "证券": "统一集中账户管理系统",
            "托管": "统一集中账户管理系统",
            "清算": "统一支付",
            "核算": "贷款核算",
            "账务": "交易级总账",
            "总账": "交易级总账",
            "客户": "客户信息管理",
            "账户": "统一集中账户管理系统",
            "风险": "交易反欺诈",
            "合规": "治理风险合规系统",
            "审计": "非现场审计",
            "数据": "数据中台",
            "影像": "统一影像平台",
            "文件": "电子档案管理",
            "证书": "数字证书",
            "签名": "办公电子签章",
            "人脸": "人脸识别",
            "身份": "身份核验",
            "核查": "公民联网核查",
            "征信": "征信二代查询前置",
            "报送": "监管报送平台",
            "监管": "监管报送平台",
            "利率": "利率定价",
            "汇率": "资产负债",
            "资金": "企业资金流信息",
            "现金流": "客户流水解析系统",
            "流水": "客户流水解析系统",
            "对账": "银企对账",
            "授信": "授信反欺诈平台",
            "催收": "新催收",
            "贷后": "贷后管理",
            "押品": "押品管理",
            "营销": "智能营销",
            "销售": "在线保险销售",
            "服务": "企业服务总线",
            "路由": "新企业服务总线",
            "总线": "新企业服务总线",
            "开放": "开放平台",
            "接口": "开放平台",
            "消息": "消息管理平台",
            "邮件": "邮件",
            "办公": "办公自动化",
            "人力": "人力管理系统",
            "财务": "财务管理",
            "会计": "管理会计集市",
            "成本": "成本分摊及盈利分析",
            "绩效": "绩效管理",
            "模型": "模型实验室",
            "实验室": "模型实验室",
            "AI": "AI中台",
            "人工智能": "AI中台",
            "区块链": "区块链在线存证",
            "知识图谱": "知识图谱平台",
            "远程": "远程银行",
            "电话": "远程银行",
            "呼叫": "智能外呼",
            "手机": "新移动银行",
            "移动": "新移动银行",
            "微信": "微信银行",
        }

        best_match = None
        best_score = 0
        for keyword, standard_name in keywords_map.items():
            if keyword in system_name:
                score = len(keyword) / len(system_name)
                if score > best_score and standard_name in self.system_list:
                    best_score = score
                    best_match = standard_name

        if best_match:
            return best_match

        logger.warning(f"系统 '{system_name}' 无法匹配到标准系统名称，保留为外部系统")
        return system_name

    def validate_and_filter_systems(self, systems: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        验证并标准化系统列表，保留所有系统（包括无法匹配的）
        """
        validated_systems = []
        standard_count = 0
        external_count = 0

        for system in systems:
            original_name = system.get("name", "")
            standard_name = self._match_standard_system(original_name)
            if any(s["name"] == standard_name for s in validated_systems):
                logger.warning(f"  - 系统 '{standard_name}' 重复，已跳过")
                continue

            system["name"] = standard_name
            system["original_name"] = original_name
            resolved = system_routes.resolve_system_owner(system_name=standard_name)
            resolved_system_id = _normalize_text(resolved.get("system_id"))
            if resolved_system_id:
                system["system_id"] = resolved_system_id

            if standard_name in self.system_list:
                system["is_standard"] = True
                standard_count += 1
                logger.debug(f"  ✓ {original_name} → {standard_name} (标准系统)")
            else:
                system["is_standard"] = False
                external_count += 1
                logger.warning(f"  ! {original_name} → {standard_name} (外部系统)")

            validated_systems.append(system)

        logger.info(f"[系统验证] 完成，共 {len(validated_systems)} 个系统（标准: {standard_count}，外部: {external_count}）")
        return validated_systems

    def validate_system_names_in_features(self, system_name: str, features: List[Dict]) -> List[Dict]:
        """
        校验功能点中的系统名称，修正不一致的系统引用
        """
        validated_features = []
        for feature in features:
            feature_system = feature.get("系统", "")
            if feature_system and feature_system != system_name:
                standard_name = self._match_standard_system(feature_system)
                if standard_name == system_name:
                    feature["系统"] = system_name
                    logger.info(f"功能点 '{feature.get('功能点', '')}' 的系统名称从 '{feature_system}' 修正为 '{system_name}'")
                else:
                    logger.warning(f"功能点 '{feature.get('功能点', '')}' 中的系统 '{feature_system}' 无法匹配当前系统 '{system_name}'，已修正")
                    feature["系统"] = system_name

            validated_features.append(feature)
        return validated_features

    def validate_systems(self, systems: List[Dict[str, str]]) -> bool:
        """
        验证识别结果的合理性
        """
        if not systems:
            logger.warning("未识别到任何系统")
            return False

        has_main_system = any(s.get("type") == "主系统" for s in systems)
        if not has_main_system:
            logger.warning("未识别到主系统，将第一个系统标记为主系统")
            systems[0]["type"] = "主系统"

        return True

    def _build_knowledge_context(self, system_profiles: List[Dict[str, Any]]) -> str:
        """
        构建系统知识上下文（用于Agent Prompt）
        """
        if not system_profiles:
            return ""

        context_parts = []
        for idx, profile in enumerate(system_profiles, 1):
            profile_text = str(profile.get("profile_text") or profile.get("content") or "").strip()
            excerpt = " ".join(profile_text.split())[:220]
            cards = profile.get("profile_cards") if isinstance(profile.get("profile_cards"), list) else []
            summaries = []
            for card in cards[:3]:
                if not isinstance(card, dict):
                    continue
                title = str(card.get("title") or "").strip()
                summary = card.get("summary")
                if title and summary:
                    summaries.append(f"{title}:{json.dumps(summary, ensure_ascii=False)}")
            similarity = float(profile.get("score") or profile.get("similarity") or 0.0)
            completeness = int(profile.get("completeness_score") or 0)
            title_name = str(profile.get("system_name") or "").strip()
            context_source = str(profile.get("context_source") or profile.get("source_file") or "profile").strip()

            part = f"""【画像{idx}】{title_name}
   - 来源: {context_source}
   - 完整度: {completeness}
   - 卡片摘要: {'；'.join(summaries[:3])}
   - 画像文本: {excerpt}
   - 相关度: {similarity:.2f}
"""
            context_parts.append(part)

        return "\n".join(context_parts)


system_identification_agent = None


def get_system_identification_agent(knowledge_service=None):
    """
    获取系统识别Agent实例

    Args:
        knowledge_service: 知识库服务（可选）

    Returns:
        SystemIdentificationAgent: Agent实例
    """
    global system_identification_agent
    expected_memory_path = os.path.join(settings.REPORT_DIR, "memory_records.json")
    expected_profile_path = resolve_system_profile_root()
    if (
        system_identification_agent is None
        or os.path.realpath(system_identification_agent.memory_service.store_path) != os.path.realpath(expected_memory_path)
        or os.path.realpath(system_identification_agent.profile_service.store_path) != os.path.realpath(expected_profile_path)
        or (knowledge_service is not None and system_identification_agent.knowledge_service is not knowledge_service)
    ):
        system_identification_agent = SystemIdentificationAgent(knowledge_service)
    return system_identification_agent
