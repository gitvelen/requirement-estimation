"""
功能点拆分Agent
按系统维度拆分功能点
支持知识库注入，提供系统知识参考
"""
from __future__ import annotations

import copy
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from backend.api import system_routes
from backend.config.config import settings
from backend.service.system_profile_repository import resolve_system_profile_root
from backend.prompts.prompt_templates import FEATURE_BREAKDOWN_PROMPT
from backend.service.memory_service import get_memory_service
from backend.service.system_profile_service import get_system_profile_service
from backend.utils.llm_client import llm_client

logger = logging.getLogger(__name__)


def _normalize_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _dedupe_key_for_feature(feature: Dict[str, Any]) -> tuple[str, str]:
    return (
        _normalize_text(feature.get("功能模块")),
        _normalize_text(feature.get("功能点")),
    )


class FeatureAdjustmentMemoryAdapter:
    def __init__(self, memory_service=None, profile_service=None) -> None:
        self.memory_service = memory_service or get_memory_service()
        self.profile_service = profile_service or get_system_profile_service()

    def build_context(self, system_name: str) -> Dict[str, Any]:
        resolved = system_routes.resolve_system_owner(system_name=system_name)
        profile = self.profile_service.get_profile(system_name)
        profile_system_id = _normalize_text((profile or {}).get("system_id"))
        system_id = _normalize_text(resolved.get("system_id")) or profile_system_id or _normalize_text(system_name)

        try:
            adjustment_records = self.memory_service.query_records(
                system_id,
                memory_type="function_point_adjustment",
                limit=20,
            )["items"]
            profile_records = self.memory_service.query_records(
                system_id,
                memory_type="profile_update",
                limit=5,
            )["items"]
            identification_records = self.memory_service.query_records(
                system_id,
                memory_type="identification_decision",
                limit=5,
            )["items"]
        except Exception as exc:
            return {
                "system_id": system_id,
                "profile": None,
                "prompt_context": "",
                "patterns": {"rename_map": {}, "module_map": {}},
                "context_degraded": True,
                "degraded_reasons": [str(exc)],
                "adjustment_records": [],
                "profile_records": [],
                "identification_records": [],
            }

        patterns = self._extract_patterns(adjustment_records)
        return {
            "system_id": system_id,
            "profile": profile,
            "prompt_context": self._build_prompt_context(profile, patterns, identification_records, profile_records),
            "patterns": patterns,
            "context_degraded": False,
            "degraded_reasons": [],
            "adjustment_records": adjustment_records,
            "profile_records": profile_records,
            "identification_records": identification_records,
        }

    def _extract_patterns(self, records: List[Dict[str, Any]]) -> Dict[str, Dict[str, str]]:
        rename_map: Dict[str, str] = {}
        module_map: Dict[str, str] = {}

        for record in records or []:
            payload = record.get("payload") if isinstance(record.get("payload"), dict) else {}
            modifications = payload.get("modifications") if isinstance(payload.get("modifications"), list) else []
            for item in modifications:
                if not isinstance(item, dict):
                    continue
                adjustment_type = _normalize_text(item.get("adjustment_type"))
                feature_name = _normalize_text(item.get("feature_name"))
                old_value = _normalize_text(item.get("old_value"))
                new_value = _normalize_text(item.get("new_value"))

                if adjustment_type == "naming_normalization" and old_value and new_value:
                    rename_map[old_value] = new_value
                elif adjustment_type == "module_mapping" and feature_name and new_value:
                    module_map[feature_name] = new_value

        return {"rename_map": rename_map, "module_map": module_map}

    def _build_prompt_context(
        self,
        profile: Optional[Dict[str, Any]],
        patterns: Dict[str, Dict[str, str]],
        identification_records: List[Dict[str, Any]],
        profile_records: List[Dict[str, Any]],
    ) -> str:
        lines: List[str] = []

        profile_data = (profile or {}).get("profile_data") if isinstance((profile or {}).get("profile_data"), dict) else {}
        positioning = ((profile_data.get("system_positioning") or {}).get("canonical") or {}) if isinstance(profile_data, dict) else {}
        business = ((profile_data.get("business_capabilities") or {}).get("canonical") or {}) if isinstance(profile_data, dict) else {}

        service_scope = _normalize_text(positioning.get("service_scope"))
        if service_scope:
            lines.append(f"- 系统服务范围: {service_scope}")

        modules = business.get("functional_modules") if isinstance(business.get("functional_modules"), list) else []
        if modules:
            lines.append(f"- 已确认稳定模块: {', '.join(str(item).strip() for item in modules if str(item).strip())}")

        rename_map = patterns.get("rename_map") or {}
        if rename_map:
            sample = [f"{old} -> {new}" for old, new in list(rename_map.items())[:5]]
            lines.append(f"- 历史命名归一: {'; '.join(sample)}")

        module_map = patterns.get("module_map") or {}
        if module_map:
            sample = [f"{name} => {module}" for name, module in list(module_map.items())[:5]]
            lines.append(f"- 历史模块归属: {'; '.join(sample)}")

        if identification_records:
            payload = identification_records[0].get("payload") if isinstance(identification_records[0].get("payload"), dict) else {}
            verdict = _normalize_text(payload.get("final_verdict"))
            reason_summary = _normalize_text(payload.get("reason_summary"))
            if verdict or reason_summary:
                lines.append(f"- 最近识别结论: {verdict or 'unknown'} {reason_summary}".strip())

        if profile_records:
            payload = profile_records[0].get("payload") if isinstance(profile_records[0].get("payload"), dict) else {}
            changed_fields = payload.get("changed_fields") if isinstance(payload.get("changed_fields"), list) else []
            if changed_fields:
                lines.append(f"- 最近画像更新字段: {', '.join(str(item).strip() for item in changed_fields[:5] if str(item).strip())}")

        return "\n".join(lines)

    def apply_adjustments(
        self,
        features: List[Dict[str, Any]],
        context: Dict[str, Any],
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        rename_map = (context.get("patterns") or {}).get("rename_map") or {}
        module_map = (context.get("patterns") or {}).get("module_map") or {}

        updated_features = copy.deepcopy(features or [])
        applied_adjustments: List[Dict[str, Any]] = []

        for feature in updated_features:
            if not isinstance(feature, dict):
                continue
            original_name = _normalize_text(feature.get("功能点"))
            if original_name in rename_map:
                renamed = rename_map[original_name]
                if renamed and renamed != original_name:
                    feature["功能点"] = renamed
                    applied_adjustments.append(
                        {
                            "adjustment_type": "naming_normalization",
                            "feature_name": original_name,
                            "new_value": renamed,
                        }
                    )

            current_name = _normalize_text(feature.get("功能点"))
            target_module = module_map.get(current_name) or module_map.get(original_name)
            current_module = _normalize_text(feature.get("功能模块"))
            if target_module and target_module != current_module:
                feature["功能模块"] = target_module
                applied_adjustments.append(
                    {
                        "adjustment_type": "module_mapping",
                        "feature_name": current_name or original_name,
                        "new_value": target_module,
                    }
                )

        deduped_features: List[Dict[str, Any]] = []
        seen = set()
        for feature in updated_features:
            if not isinstance(feature, dict):
                continue
            dedupe_key = (
                _normalize_text(feature.get("功能模块")),
                _normalize_text(feature.get("功能点")),
            )
            if dedupe_key in seen:
                applied_adjustments.append(
                    {
                        "adjustment_type": "deduplicate",
                        "feature_name": dedupe_key[1],
                        "new_value": "removed_duplicate",
                    }
                )
                continue
            seen.add(dedupe_key)
            deduped_features.append(feature)

        return deduped_features, applied_adjustments


class FeatureBreakdownAgent:
    """功能点拆分Agent"""

    def __init__(self, knowledge_service=None):
        """
        初始化Agent

        Args:
            knowledge_service: 知识库服务（可选，用于注入历史案例）
        """
        self.name = "功能点拆分Agent"
        self.prompt_template = FEATURE_BREAKDOWN_PROMPT
        self.knowledge_service = knowledge_service
        self.knowledge_enabled = settings.KNOWLEDGE_ENABLED
        self.memory_adapter = FeatureAdjustmentMemoryAdapter()
        self.profile_service = self.memory_adapter.profile_service

        logger.info(f"{self.name}初始化完成（画像上下文：已启用）")

    def _split_requirement_content(self, requirement_content: str, *, max_chunk_chars: int = 6000) -> List[str]:
        text = str(requirement_content or "").strip()
        if not text:
            return [""]

        segments: List[str] = []
        current: List[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if current and self._is_chunk_boundary(stripped):
                segments.append("\n".join(current))
                current = [stripped]
                continue
            current.append(stripped)
        if current:
            segments.append("\n".join(current))

        packed: List[str] = []
        current_chunk = ""
        for segment in segments:
            if not current_chunk:
                current_chunk = segment
                continue
            if len(current_chunk) + 2 + len(segment) <= max_chunk_chars:
                current_chunk = f"{current_chunk}\n\n{segment}"
                continue
            packed.append(current_chunk)
            current_chunk = segment
        if current_chunk:
            packed.append(current_chunk)

        return packed or [text]

    def _is_chunk_boundary(self, line: str) -> bool:
        if line.startswith("【附件:"):
            return True
        if line.startswith("（") and line.endswith("）"):
            return True
        if re.match(r"^\d+[.、].+", line):
            return True
        if re.match(r"^\d+\.\d+.+", line):
            return True
        if re.match(r"^[一二三四五六七八九十]+[、，].+", line):
            return True
        return False

    def _build_breakdown_prompt(
        self,
        *,
        requirement_content: str,
        system_name: str,
        system_type: str,
        memory_context: Dict[str, Any],
        knowledge_context: str,
    ) -> str:
        user_prompt = f"""需求内容：\n\n{requirement_content}\n\n"""
        user_prompt += f"""请针对【{system_name}】（类型：{system_type}）进行功能点拆分。\n\n"""

        prompt_context = _normalize_text(memory_context.get("prompt_context"))
        if prompt_context:
            user_prompt += f"""【画像与Memory约束】\n{prompt_context}\n\n"""
            user_prompt += "请优先复用已确认的命名、模块归属和系统边界，避免与历史稳定模式冲突。\n\n"

        if knowledge_context:
            user_prompt += f"""【系统画像参考】\n{knowledge_context}\n\n"""
            user_prompt += "请参考上述系统画像（边界、核心能力、交互关系、技术约束等）进行拆分，避免将其他系统的功能误拆入本系统。\n\n"

        user_prompt += """拆分要求：
1. 只拆分属于该系统的功能点
2. 功能点粒度控制在0.5-5人天
3. 明确标注依赖关系
4. 评估复杂度（高/中/低）
5. 备注字段必须包含以下标签（用于系统校准与复核）：[归属依据]、[系统约束]、[集成点]、[待确认]
6. 原子性：每个功能点必须是单一功能，不能把多项独立子功能合并为一个功能点。
   当业务描述包含"1. ...；2. ..."等原文编号项时，每项应拆为独立功能点。
7. 覆盖性：必须覆盖需求内容中的全部原文编号项和明确业务要点；如某项不属于当前系统，只能在备注中说明原因，不能直接遗漏。
8. 真实性：不得新增原文未明确提出的独立功能点；基于工程经验推断出的扩展能力只能写入[待确认]。"""
        return user_prompt

    def _merge_chunk_features(self, feature_groups: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        merged: List[Dict[str, Any]] = []
        index_by_key: Dict[tuple[str, str], int] = {}

        for group in feature_groups:
            for feature in group:
                key = _dedupe_key_for_feature(feature)
                if key not in index_by_key:
                    index_by_key[key] = len(merged)
                    merged.append(copy.deepcopy(feature))
                    continue

                existing = merged[index_by_key[key]]
                current_score = sum(1 for item in feature.values() if _normalize_text(item))
                existing_score = sum(1 for item in existing.values() if _normalize_text(item))
                if current_score > existing_score:
                    merged[index_by_key[key]] = copy.deepcopy(feature)
                    existing = merged[index_by_key[key]]

                merged_remark = _normalize_text(existing.get("备注"))
                new_remark = _normalize_text(feature.get("备注"))
                if new_remark and new_remark not in merged_remark:
                    existing["备注"] = f"{merged_remark}\n{new_remark}".strip() if merged_remark else new_remark

        for idx, feature in enumerate(merged, start=1):
            feature["序号"] = f"1.{idx}"

        for feature in merged:
            desc = str(feature.get("业务描述") or "")
            numbered_items = re.findall(r"[；;]\s*\d+[.、]", desc)
            if len(numbered_items) >= 2:
                remark = str(feature.get("备注") or "").strip()
                note = f"[粒度提示] 业务描述含{len(numbered_items)}个编号子项，可能需要进一步拆分。"
                feature["备注"] = f"{remark}\n{note}".strip() if remark else note

        return merged

    def _should_retry_json_parse(self, response_text: str) -> bool:
        text = str(response_text or "").strip()
        if not text:
            return False
        return text.startswith("{") or text.startswith("```json") or '"features"' in text

    def _request_json_payload(
        self,
        user_prompt: str,
        *,
        operation_label: str,
        temperature: float = 0.5,
    ) -> Dict[str, Any]:
        token_budgets = []
        for candidate in (3000, max(int(getattr(settings, "LLM_MAX_TOKENS", 0) or 0), 8000)):
            if candidate > 0 and candidate not in token_budgets:
                token_budgets.append(candidate)

        last_error: Optional[Exception] = None
        for attempt, max_tokens in enumerate(token_budgets, start=1):
            response = llm_client.chat_with_system_prompt(
                system_prompt=self.prompt_template,
                user_prompt=user_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            try:
                return llm_client.extract_json(response)
            except ValueError as exc:
                last_error = exc
                should_retry = (
                    attempt < len(token_budgets)
                    and self._should_retry_json_parse(response)
                )
                if not should_retry:
                    raise
                logger.warning(
                    "[功能拆分] %s 返回疑似截断JSON，放大输出预算后重试（attempt=%s/%s, max_tokens=%s, response_chars=%s）",
                    operation_label,
                    attempt,
                    len(token_budgets),
                    max_tokens,
                    len(response or ""),
                )

        if last_error is not None:
            raise last_error
        raise RuntimeError(f"{operation_label} 未获得有效响应")

    def breakdown(
        self,
        requirement_content: str,
        system_name: str,
        system_type: str = "主系统",
        task_id: Optional[str] = None,
    ) -> List[Dict[str, any]]:
        result = self.breakdown_with_context(
            requirement_content=requirement_content,
            system_name=system_name,
            system_type=system_type,
            task_id=task_id,
        )
        return result["features"]

    def breakdown_with_context(
        self,
        requirement_content: str,
        system_name: str,
        system_type: str = "主系统",
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        对指定系统进行功能点拆分，并返回 Memory 上下文状态。
        """
        try:
            logger.info(f"[功能拆分] 开始拆分: {system_name} ({system_type})")

            memory_context = self.memory_adapter.build_context(system_name)

            knowledge_context = ""
            system_profiles: List[Dict[str, Any]] = []
            try:
                logger.info(f"[功能拆分] 正在组装【{system_name}】的系统画像上下文...")
                context_bundle = self.profile_service.build_context_bundle(
                    system_name,
                    query=requirement_content,
                    top_k=max(int(getattr(settings, "KNOWLEDGE_TOP_K", 8) or 8), 3),
                )
                if str(context_bundle.get("profile_text") or "").strip() or context_bundle.get("profile_cards"):
                    system_profiles = [
                        {
                            "system_name": system_name,
                            "score": 1.0,
                            "profile_text": str(context_bundle.get("profile_text") or "").strip(),
                            "profile_cards": copy.deepcopy(context_bundle.get("profile_cards")) if isinstance(context_bundle.get("profile_cards"), list) else [],
                            "context_source": str(context_bundle.get("context_source") or "profile").strip() or "profile",
                            "completeness_score": int(context_bundle.get("completeness_score") or 0),
                        }
                    ]
                    knowledge_context = self._build_profile_context_text(context_bundle)
                else:
                    logger.info(f"[功能拆分] 【{system_name}】暂无可用画像上下文")
            except Exception as e:
                logger.warning(f"[功能拆分] 画像上下文组装失败: {e}，继续使用传统方式")

            chunk_results: List[List[Dict[str, Any]]] = []
            chunks = self._split_requirement_content(requirement_content)
            for chunk_index, chunk in enumerate(chunks, start=1):
                user_prompt = self._build_breakdown_prompt(
                    requirement_content=chunk,
                    system_name=system_name,
                    system_type=system_type,
                    memory_context=memory_context,
                    knowledge_context=knowledge_context,
                )

                result = self._request_json_payload(
                    user_prompt=user_prompt,
                    operation_label=f"{system_name} 功能拆分 chunk {chunk_index}/{len(chunks)}",
                )

                if "features" not in result:
                    raise ValueError("响应中缺少'features'字段")

                features = result["features"]
                for idx, feature in enumerate(features, start=1):
                    if "序号" not in feature:
                        feature["序号"] = f"1.{idx}"

                for feature in features:
                    self._validate_feature(feature)

                chunk_results.append(features)

            features = self._merge_chunk_features(chunk_results)

            try:
                self._apply_kb_calibration_to_features(
                    features=features,
                    system_name=system_name,
                    system_profiles=system_profiles,
                    task_id=task_id,
                )
            except Exception as e:
                logger.debug(f"[功能拆分] 系统校准提示写入失败（忽略）: {e}")

            features, applied_adjustments = self.memory_adapter.apply_adjustments(features, memory_context)

            complexity_count = {"高": 0, "中": 0, "低": 0}
            for feature in features:
                complexity = feature.get("复杂度", "中")
                if complexity in complexity_count:
                    complexity_count[complexity] += 1

            logger.info(
                "[功能拆分] 完成，共 %s 个功能点（高:%s 中:%s 低:%s）",
                len(features),
                complexity_count["高"],
                complexity_count["中"],
                complexity_count["低"],
            )
            return {
                "features": features,
                "context_degraded": bool(memory_context.get("context_degraded")),
                "degraded_reasons": memory_context.get("degraded_reasons") or [],
                "applied_adjustments": applied_adjustments,
            }
        except Exception as e:
            logger.error(f"[功能拆分] 拆分失败 ({system_name}): {str(e)}")
            raise

    def _validate_feature(self, feature: Dict[str, any]):
        """
        验证功能点数据的完整性
        """
        required_fields = ["序号", "功能模块", "功能点", "业务描述", "预估人天", "复杂度"]
        for field in required_fields:
            if field not in feature:
                raise ValueError(f"功能点缺少必需字段: {field}")

        try:
            man_days = float(feature["预估人天"])
            if man_days < 0.5 or man_days > 5:
                logger.warning(f"功能点{feature['序号']}的人天{man_days}超出建议范围(0.5-5)")
        except ValueError:
            raise ValueError(f"功能点{feature['序号']}的预估人天格式错误: {feature['预估人天']}")

        if feature["复杂度"] not in ["高", "中", "低"]:
            raise ValueError(f"功能点{feature['序号']}的复杂度值错误: {feature['复杂度']}")

        description = str(feature.get("业务描述") or "")
        if re.search(r"[；;]\s*\d+[.、]\s", description) or description.count("；1.") > 0:
            logger.warning(
                f"功能点{feature.get('序号', '?')}的业务描述包含编号列表，"
                f"可能应由多个原子功能点组成，建议人工复核粒度"
            )

    def _apply_kb_calibration_to_features(
        self,
        features: List[Dict[str, Any]],
        system_name: str,
        system_profiles: List[Dict[str, Any]],
        task_id: Optional[str],
    ) -> None:
        if not features:
            return

        kb_ref_line = self._build_kb_reference_line(system_profiles)
        for feature in features:
            if not isinstance(feature, dict):
                continue
            remark = str(feature.get("备注") or "").strip()
            parts = [p for p in remark.splitlines() if p.strip()] if remark else []
            if kb_ref_line:
                parts.append(kb_ref_line)
            feature["备注"] = "\n".join(parts).strip()

        checks = 0
        max_checks = 12
        for feature in features:
            if checks >= max_checks:
                break
            if not self._is_high_risk_feature(feature):
                continue
            checks += 1

            query_text = self._build_feature_query_text(feature)
            if not query_text.strip():
                continue

            results = self.profile_service.search_relevant_profile_contexts(query_text, limit=3)
            if not results:
                continue

            top = results[0]
            top_system = str(top.get("system_name") or "").strip()
            top_sim = float(top.get("score") or top.get("similarity") or 0.0)
            if not top_system or top_system == system_name:
                continue

            best_current = 0.0
            for item in results:
                if str(item.get("system_name") or "").strip() == system_name:
                    best_current = max(best_current, float(item.get("score") or item.get("similarity") or 0.0))

            if top_sim - best_current < 1.0:
                continue

            remark = str(feature.get("备注") or "").strip()
            note = f"[归属复核] 疑似更偏向系统：{top_system} (score={top_sim:.2f})，建议复核。"
            feature["备注"] = f"{remark}\n{note}".strip() if remark else note

    def _build_kb_reference_line(self, system_profiles: List[Dict[str, Any]]) -> str:
        if not system_profiles:
            return "[画像引用] 无（该系统尚无可用画像上下文）"

        hits = []
        for item in sorted(system_profiles, key=lambda x: x.get("score", x.get("similarity", 0.0)), reverse=True)[:2]:
            source_file = str(item.get("source_file") or item.get("context_source") or "").strip()
            sim = float(item.get("score") or item.get("similarity") or 0.0)
            if source_file:
                hits.append(f"{source_file}(score={sim:.2f})")
            else:
                hits.append(f"profile_context(score={sim:.2f})")
        if not hits:
            return "[画像引用] profile_context"
        return "[画像引用] " + "；".join(hits)

    def _build_profile_context_text(self, context_bundle: Dict[str, Any]) -> str:
        if not isinstance(context_bundle, dict):
            return ""

        parts: List[str] = []
        profile_text = _normalize_text(context_bundle.get("profile_text"))
        if profile_text:
            parts.append(f"画像摘要: {profile_text}")

        cards = context_bundle.get("profile_cards") if isinstance(context_bundle.get("profile_cards"), list) else []
        card_lines: List[str] = []
        for card in cards[:5]:
            if not isinstance(card, dict) or not card.get("has_content"):
                continue
            title = _normalize_text(card.get("title"))
            summary = card.get("summary")
            if title and summary:
                card_lines.append(f"{title}: {json.dumps(summary, ensure_ascii=False)}")
        if card_lines:
            parts.append("关键卡片: " + "；".join(card_lines))

        integrations = context_bundle.get("integrations") if isinstance(context_bundle.get("integrations"), list) else []
        if integrations:
            integration_names = [
                _normalize_text(item.get("service_name"))
                for item in integrations
                if isinstance(item, dict) and _normalize_text(item.get("service_name"))
            ]
            if integration_names:
                parts.append("相关对外交互: " + "、".join(integration_names[:6]))

        capabilities = context_bundle.get("capabilities") if isinstance(context_bundle.get("capabilities"), list) else []
        if capabilities:
            capability_names = [
                _normalize_text(item.get("summary") or item.get("entry_id"))
                for item in capabilities
                if isinstance(item, dict) and _normalize_text(item.get("summary") or item.get("entry_id"))
            ]
            if capability_names:
                parts.append("代码能力线索: " + "、".join(capability_names[:6]))

        return "\n".join(parts).strip()

    def _is_high_risk_feature(self, feature: Dict[str, Any]) -> bool:
        try:
            complexity = str(feature.get("复杂度") or "").strip()
        except Exception:
            complexity = ""
        if complexity == "高":
            return True

        dep = str(feature.get("依赖项") or feature.get("依赖") or "").strip()
        if dep and dep not in ("无", "-"):
            return True

        text = " ".join(
            str(feature.get(k) or "").strip()
            for k in ("功能点", "业务描述", "输入", "输出", "依赖", "依赖项", "备注")
        )
        keywords = ("接口", "联调", "同步", "对账", "加密", "权限", "性能", "合规", "上线", "发布", "迁移", "改造")
        return any(k in text for k in keywords)

    def _build_feature_query_text(self, feature: Dict[str, Any]) -> str:
        module = str(feature.get("功能模块") or "").strip()
        name = str(feature.get("功能点") or "").strip()
        desc = str(feature.get("业务描述") or "").strip()
        dep = str(feature.get("依赖项") or feature.get("依赖") or "").strip()
        return "\n".join([part for part in (module, name, desc, dep) if part])

    def refine_breakdown(
        self,
        features: List[Dict[str, any]],
        feedback: str,
    ) -> List[Dict[str, any]]:
        """
        根据反馈优化功能点拆分
        """
        try:
            logger.info("根据反馈优化功能点拆分")

            features_text = json.dumps(features, ensure_ascii=False, indent=2)
            user_prompt = f"""当前功能点拆分结果：\n\n{features_text}\n\n"""
            user_prompt += f"""反馈意见：\n{feedback}\n\n"""
            user_prompt += """请根据反馈意见优化功能点拆分，保持相同的JSON格式。"""

            result = self._request_json_payload(
                user_prompt=user_prompt,
                operation_label="功能点优化",
            )

            if "features" not in result:
                raise ValueError("响应中缺少'features'字段")

            optimized_features = result["features"]
            logger.info(f"功能点优化完成，{len(features)} -> {len(optimized_features)}")
            return optimized_features

        except Exception as e:
            logger.error(f"功能点优化失败: {str(e)}")
            return features


feature_breakdown_agent = None


def get_feature_breakdown_agent(knowledge_service=None):
    """
    获取功能拆分Agent实例

    Args:
        knowledge_service: 知识库服务（可选）

    Returns:
        FeatureBreakdownAgent: Agent实例
    """
    global feature_breakdown_agent
    expected_memory_path = os.path.join(settings.REPORT_DIR, "memory_records.json")
    expected_profile_path = resolve_system_profile_root()
    current_memory_path = (
        feature_breakdown_agent.memory_adapter.memory_service.store_path
        if feature_breakdown_agent is not None
        else ""
    )
    current_profile_path = (
        feature_breakdown_agent.memory_adapter.profile_service.store_path
        if feature_breakdown_agent is not None
        else ""
    )
    if (
        feature_breakdown_agent is None
        or os.path.realpath(current_memory_path) != os.path.realpath(expected_memory_path)
        or os.path.realpath(current_profile_path) != os.path.realpath(expected_profile_path)
        or (knowledge_service is not None and feature_breakdown_agent.knowledge_service is not knowledge_service)
    ):
        feature_breakdown_agent = FeatureBreakdownAgent(knowledge_service)
    return feature_breakdown_agent
