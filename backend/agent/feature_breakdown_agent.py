"""
功能点拆分Agent
按系统维度拆分功能点
支持知识库注入，提供系统知识参考
"""
import logging
import json
from typing import Dict, List, Optional, Any
from backend.utils.llm_client import llm_client
from backend.prompts.prompt_templates import FEATURE_BREAKDOWN_PROMPT
from backend.config.config import settings

logger = logging.getLogger(__name__)


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

        if self.knowledge_enabled and self.knowledge_service:
            logger.info(f"{self.name}初始化完成（知识库功能：已启用）")
        else:
            logger.info(f"{self.name}初始化完成（知识库功能：未启用）")

    def breakdown(
        self,
        requirement_content: str,
        system_name: str,
        system_type: str = "主系统",
        task_id: Optional[str] = None
    ) -> List[Dict[str, any]]:
        """
        对指定系统进行功能点拆分

        Args:
            requirement_content: 需求内容文本
            system_name: 系统名称
            system_type: 系统类型

        Returns:
            List: 功能点列表

        Raises:
            ValueError: 拆分失败或返回格式错误
        """
        try:
            logger.info(f"[功能拆分] 开始拆分: {system_name} ({system_type})")

            # 【新增】知识库增强：检索系统知识（系统边界/核心功能/技术栈等）
            knowledge_context = ""
            system_profiles: List[Dict[str, Any]] = []
            if self.knowledge_enabled and self.knowledge_service:
                try:
                    logger.info(f"[功能拆分] 正在检索【{system_name}】的系统知识...")
                    system_profiles = self.knowledge_service.search_similar_knowledge(
                        query_text=requirement_content,
                        system_name=system_name,
                        knowledge_type="system_profile",
                        top_k=settings.KNOWLEDGE_TOP_K,
                        similarity_threshold=settings.KNOWLEDGE_SIMILARITY_THRESHOLD,
                        task_id=task_id,
                        stage="feature_breakdown"
                    )

                    if system_profiles:
                        logger.info(f"[功能拆分] 检索到 {len(system_profiles)} 条相关系统知识")
                        knowledge_context = self.knowledge_service.build_knowledge_context(system_profiles, max_length=1500)
                    else:
                        logger.info(f"[功能拆分] 未检索到【{system_name}】的系统知识")

                except Exception as e:
                    logger.warning(f"[功能拆分] 知识库检索失败: {e}，继续使用传统方式")

            # 构建提示词
            user_prompt = f"""需求内容：\n\n{requirement_content}\n\n"""
            user_prompt += f"""请针对【{system_name}】（类型：{system_type}）进行功能点拆分。\n\n"""

            # 【新增】注入系统知识上下文
            if knowledge_context:
                user_prompt += f"""【系统知识参考】\n{knowledge_context}\n\n"""
                user_prompt += "请参考上述系统知识（系统边界、核心功能、技术栈等）进行拆分，避免将其他系统的功能误拆入本系统。\n\n"

            user_prompt += """拆分要求：
1. 只拆分属于该系统的功能点
2. 功能点粒度控制在0.5-5人天
3. 明确标注依赖关系
4. 评估复杂度（高/中/低）
5. 备注字段必须包含以下标签（用于系统校准与复核）：[归属依据]、[系统约束]、[集成点]、[待确认]"""

            # 调用LLM
            response = llm_client.chat_with_system_prompt(
                system_prompt=self.prompt_template,
                user_prompt=user_prompt,
                temperature=0.5,
                max_tokens=3000
            )

            # 解析JSON响应
            result = llm_client.extract_json(response)

            if "features" not in result:
                raise ValueError("响应中缺少'features'字段")

            features = result["features"]

            # 为每个功能点添加序号
            for idx, feature in enumerate(features, start=1):
                if "序号" not in feature:
                    feature["序号"] = f"1.{idx}"

            # 验证功能点数据
            for feature in features:
                self._validate_feature(feature)

            # 统计复杂度分布
            complexity_count = {"高": 0, "中": 0, "低": 0}
            for feature in features:
                complexity = feature.get("复杂度", "中")
                if complexity in complexity_count:
                    complexity_count[complexity] += 1

            # 【新增】系统校准：写入知识引用与归属复核提示（只提示，不自动调整归属）
            try:
                self._apply_kb_calibration_to_features(
                    features=features,
                    system_name=system_name,
                    system_profiles=system_profiles,
                    task_id=task_id
                )
            except Exception as e:
                logger.debug(f"[功能拆分] 系统校准提示写入失败（忽略）: {e}")

            logger.info(f"[功能拆分] 完成，共 {len(features)} 个功能点（高:{complexity_count['高']} 中:{complexity_count['中']} 低:{complexity_count['低']}）")
            return features

        except Exception as e:
            logger.error(f"[功能拆分] 拆分失败 ({system_name}): {str(e)}")
            raise

    def _validate_feature(self, feature: Dict[str, any]):
        """
        验证功能点数据的完整性

        Args:
            feature: 功能点数据

        Raises:
            ValueError: 数据不完整或格式错误
        """
        required_fields = ["序号", "功能模块", "功能点", "业务描述", "预估人天", "复杂度"]

        for field in required_fields:
            if field not in feature:
                raise ValueError(f"功能点缺少必需字段: {field}")

        # 验证人天范围
        try:
            man_days = float(feature["预估人天"])
            if man_days < 0.5 or man_days > 5:
                logger.warning(f"功能点{feature['序号']}的人天{man_days}超出建议范围(0.5-5)")
        except ValueError:
            raise ValueError(f"功能点{feature['序号']}的预估人天格式错误: {feature['预估人天']}")

        # 验证复杂度
        if feature["复杂度"] not in ["高", "中", "低"]:
            raise ValueError(f"功能点{feature['序号']}的复杂度值错误: {feature['复杂度']}")

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

        # 高风险功能点才做跨系统归属复核（减少embedding调用）
        if not (self.knowledge_enabled and self.knowledge_service):
            return

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

            threshold = max(float(getattr(settings, "KNOWLEDGE_SIMILARITY_THRESHOLD", 0.6) or 0.6), 0.75)
            results = self.knowledge_service.search_similar_knowledge(
                query_text=query_text,
                knowledge_type="system_profile",
                top_k=3,
                similarity_threshold=threshold,
                task_id=task_id,
                module=str(feature.get("功能模块") or "").strip() or None,
                feature_name=str(feature.get("功能点") or "").strip() or None,
                stage="feature_attribution_check",
            )
            if not results:
                continue

            top = results[0]
            top_system = str(top.get("system_name") or "").strip()
            top_sim = float(top.get("similarity") or 0.0)
            if not top_system or top_system == system_name:
                continue

            best_current = 0.0
            for item in results:
                if str(item.get("system_name") or "").strip() == system_name:
                    best_current = max(best_current, float(item.get("similarity") or 0.0))

            if top_sim - best_current < 0.08:
                continue

            remark = str(feature.get("备注") or "").strip()
            note = f"[归属复核] 疑似更偏向系统：{top_system} (sim={top_sim:.2f})，建议复核。"
            feature["备注"] = f"{remark}\n{note}".strip() if remark else note

    def _build_kb_reference_line(self, system_profiles: List[Dict[str, Any]]) -> str:
        if not system_profiles:
            return "[知识引用] 无（该系统未导入system_profile系统画像）"

        hits = []
        for item in sorted(system_profiles, key=lambda x: x.get("similarity", 0.0), reverse=True)[:2]:
            source_file = str(item.get("source_file") or "").strip()
            sim = float(item.get("similarity") or 0.0)
            if source_file:
                hits.append(f"{source_file}(sim={sim:.2f})")
            else:
                hits.append(f"system_profile(sim={sim:.2f})")
        if not hits:
            return "[知识引用] system_profile"
        return "[知识引用] " + "；".join(hits)

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
        feedback: str
    ) -> List[Dict[str, any]]:
        """
        根据反馈优化功能点拆分

        Args:
            features: 原始功能点列表
            feedback: 反馈意见

        Returns:
            List: 优化后的功能点列表
        """
        try:
            logger.info("根据反馈优化功能点拆分")

            # 将现有功能点格式化为文本
            features_text = json.dumps(features, ensure_ascii=False, indent=2)

            user_prompt = f"""当前功能点拆分结果：\n\n{features_text}\n\n"""
            user_prompt += f"""反馈意见：\n{feedback}\n\n"""
            user_prompt += """请根据反馈意见优化功能点拆分，保持相同的JSON格式。"""

            # 调用LLM
            response = llm_client.chat_with_system_prompt(
                system_prompt=self.prompt_template,
                user_prompt=user_prompt,
                temperature=0.5,
                max_tokens=3000
            )

            # 解析结果
            result = llm_client.extract_json(response)

            if "features" not in result:
                raise ValueError("响应中缺少'features'字段")

            optimized_features = result["features"]

            logger.info(f"功能点优化完成，{len(features)} -> {len(optimized_features)}")

            return optimized_features

        except Exception as e:
            logger.error(f"功能点优化失败: {str(e)}")
            # 如果优化失败，返回原始结果
            return features

# 全局Agent实例（延迟初始化，在agent_orchestrator中注入knowledge_service）
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
    if feature_breakdown_agent is None:
        feature_breakdown_agent = FeatureBreakdownAgent(knowledge_service)
    return feature_breakdown_agent
