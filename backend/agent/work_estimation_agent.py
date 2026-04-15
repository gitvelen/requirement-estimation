"""
工作量估算Agent
使用Delphi专家评估法进行工作量估算
"""
import logging
import json
import statistics
from typing import Any, Dict, List, Optional
from backend.utils.llm_client import llm_client
from backend.prompts.prompt_templates import WORK_ESTIMATION_PROMPT
from backend.config.config import settings

logger = logging.getLogger(__name__)


class WorkEstimationAgent:
    """工作量估算Agent"""

    def __init__(self):
        """初始化Agent"""
        self.name = "工作量估算Agent"
        self.prompt_template = WORK_ESTIMATION_PROMPT
        self.delphi_rounds = settings.DELPHI_ROUNDS
        # 只使用前3个专家（对应Excel中的专家1-3列）
        self.experts = settings.DELPHI_EXPERTS[:3]
        self.expert_weights = {k: v for k, v in settings.DELPHI_EXPERT_WEIGHTS.items() if k in self.experts}
        logger.info(f"{self.name}初始化完成，使用{len(self.experts)}位专家")
        self._latest_estimation_details: Dict[str, Dict[str, Any]] = {}

    def _feature_key(self, feature: Dict[str, Any]) -> str:
        feature_id = str(feature.get("id") or "").strip()
        if feature_id:
            return feature_id
        return str(feature.get("功能点") or feature.get("name") or "").strip()

    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _resolve_original_estimate(self, feature: Dict[str, Any]) -> float:
        for key in ("original_estimate", "预估人天", "aiEstimatedDays", "预估人天数", "AI预估人天", "AI预估"):
            if key not in feature:
                continue
            value = self._safe_float(feature.get(key), default=0.0)
            if value > 0:
                return round(value, 2)
        return 1.0

    def estimate_three_point_for_feature(
        self,
        feature: Dict[str, Any],
        *,
        system_context: str = "",
        correction_context: str = "",
        historical_context: str = "",
    ) -> Dict[str, Any]:
        feature_name = str(feature.get("功能点") or feature.get("name") or "").strip() or "未命名功能点"
        description = str(feature.get("业务描述") or feature.get("description") or "").strip()
        original_estimate = self._resolve_original_estimate(feature)

        prompt = f"""请为以下功能点给出三点估计（单位：人天），仅返回 JSON。

功能点：{feature_name}
描述：{description}
拆分阶段原始估值（用于校准，不可直接照搬）：{original_estimate}

第一层知识（系统画像）：
{system_context or "无"}

第二层知识（历史修正模式）：
{correction_context or "无"}

第三层知识（历史评估样本）：
{historical_context or "无"}

输出格式：
{{
  "optimistic": 1.5,
  "most_likely": 2.5,
  "pessimistic": 4.0,
  "reasoning": "估算依据"
}}
"""
        response = llm_client.chat_with_system_prompt(
            system_prompt="你是软件估算专家。输出必须是可解析JSON，数值必须为正数，reasoning简明具体。",
            user_prompt=prompt,
            temperature=0.2,
            max_tokens=800,
        )
        parsed = llm_client.extract_json(response)
        if not isinstance(parsed, dict):
            raise ValueError("invalid_estimation_payload")

        optimistic = self._safe_float(parsed.get("optimistic"), default=-1.0)
        most_likely = self._safe_float(parsed.get("most_likely"), default=-1.0)
        pessimistic = self._safe_float(parsed.get("pessimistic"), default=-1.0)
        reasoning = str(parsed.get("reasoning") or "").strip()

        if min(optimistic, most_likely, pessimistic) <= 0:
            raise ValueError("invalid_estimation_value")

        expected = round((optimistic + 4 * most_likely + pessimistic) / 6, 2)
        return {
            "optimistic": round(optimistic, 2),
            "most_likely": round(most_likely, 2),
            "pessimistic": round(pessimistic, 2),
            "expected": expected,
            "reasoning": reasoning or "LLM 未返回理由",
            "original_estimate": original_estimate,
        }

    def estimate(
        self,
        features: List[Dict],
        *,
        system_context_map: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, float]:
        """
        对功能点进行工作量估算（LLM三点估计 + PERT）

        Args:
            features: 功能点列表
            system_context_map: 按系统名映射的画像上下文

        Returns:
            Dict: 每个功能点的估算工作量（人天）
        """
        try:
            logger.info(f"[工作量估算] 开始估算 {len(features)} 个功能点")
            self._latest_estimation_details = {}
            estimates = {}
            total_estimated = 0

            for idx, feature in enumerate(features, 1):
                key = self._feature_key(feature)
                fallback = self._resolve_original_estimate(feature)
                system_name = str(
                    feature.get("系统")
                    or feature.get("system")
                    or feature.get("system_name")
                    or ""
                ).strip()
                context_payload = (
                    system_context_map.get(system_name, {})
                    if isinstance(system_context_map, dict)
                    else {}
                )
                system_context = str(context_payload.get("text") or "").strip()
                profile_context_used = bool(context_payload.get("profile_context_used"))
                context_source = str(context_payload.get("context_source") or "none").strip() or "none"
                try:
                    detail = self.estimate_three_point_for_feature(
                        feature,
                        system_context=system_context,
                    )
                except Exception as exc:
                    logger.warning("LLM估算失败，使用降级值 feature=%s error=%s", key, exc)
                    detail = {
                        "optimistic": None,
                        "most_likely": None,
                        "pessimistic": None,
                        "expected": round(fallback, 2),
                        "reasoning": None,
                        "original_estimate": round(fallback, 2),
                    }
                detail["profile_context_used"] = profile_context_used
                detail["context_source"] = context_source
                estimates[key] = detail["expected"]
                self._latest_estimation_details[key] = detail
                total_estimated += detail["expected"]
                if idx % 10 == 0 or idx == len(features):
                    logger.info(f"[进度] {idx}/{len(features)} 功能点已估算")

            logger.info(f"[工作量估算] 完成估算，总工作量: {total_estimated:.1f} 人天")
            return estimates

        except Exception as e:
            logger.error(f"[工作量估算] 估算失败: {str(e)}")
            raise

    def _round1_estimate(self, feature: Dict) -> List[float]:
        """
        第一轮估算：基于复杂度的快速估算（不调用LLM）

        Args:
            feature: 功能点信息

        Returns:
            List: 各专家的估算值
        """
        estimates = []

        # 基于复杂度的基准工作量
        complexity = feature.get("复杂度", "中")
        if complexity == "高":
            base_workload = 4.0
        elif complexity == "中":
            base_workload = 2.5
        else:
            base_workload = 1.5

        # 为每个专家生成略有不同的估算（模拟专家差异）
        import random
        random.seed(hash(feature.get("功能点", "")) % 10000)  # 基于功能点名称的随机种子

        for i, expert in enumerate(self.experts):
            # 在基准值基础上增加±20%的随机波动
            variation = random.uniform(-0.2, 0.2)
            estimate = round(base_workload * (1 + variation), 1)
            # 确保不低于0.5
            estimate = max(0.5, estimate)
            estimates.append(estimate)

        logger.info(f"基于复杂度 '{complexity}' 的估算: {estimates}, 基准值: {base_workload}")

        return estimates

    def _round2_estimate(self, feature: Dict, round1_estimates: List[float]) -> List[float]:
        """
        第二轮估算：反馈第一轮结果，专家调整

        Args:
            feature: 功能点信息
            round1_estimates: 第一轮估算值

        Returns:
            List: 第二轮估算值
        """
        # 计算第一轮统计信息
        min_val = min(round1_estimates)
        max_val = max(round1_estimates)
        mean_val = statistics.mean(round1_estimates)
        std_val = statistics.stdev(round1_estimates) if len(round1_estimates) > 1 else 0

        feedback = f"""第一轮估算结果统计：
- 最小值: {min_val:.2f}人天
- 最大值: {max_val:.2f}人天
- 平均值: {mean_val:.2f}人天
- 标准差: {std_val:.2f}

请参考以上统计信息，结合你的专业判断，给出你的第二轮估算值（仅输出一个数字，保留1位小数）。"""

        estimates = []

        for i, expert in enumerate(self.experts):
            try:
                # 简化版：直接使用统计调整
                round1 = round1_estimates[i]

                # 如果偏离平均值较大，向平均值调整
                if abs(round1 - mean_val) > std_val:
                    adjusted = round1 * 0.7 + mean_val * 0.3
                else:
                    adjusted = round1

                estimates.append(adjusted)

            except Exception as e:
                logger.warning(f"专家{expert}第2轮估算失败: {str(e)}")
                estimates.append(round1_estimates[i])

        return estimates

    def _round3_estimate(self, feature: Dict, round2_estimates: List[float]) -> List[float]:
        """
        第三轮估算：最终确认

        Args:
            feature: 功能点信息
            round2_estimates: 第二轮估算值

        Returns:
            List: 第三轮估算值
        """
        # 计算第二轮统计信息
        mean_val = statistics.mean(round2_estimates)
        std_val = statistics.stdev(round2_estimates) if len(round2_estimates) > 1 else 0

        # 检查是否收敛（标准差小于平均值的20%）
        if std_val < mean_val * 0.2:
            logger.info("估算已收敛，使用第二轮结果")
            return round2_estimates

        # 继续微调
        estimates = []
        for i, expert in enumerate(self.experts):
            try:
                # 向平均值微调
                round2 = round2_estimates[i]
                adjusted = round2 * 0.8 + mean_val * 0.2
                estimates.append(adjusted)
            except:
                estimates.append(round2_estimates[i])

        return estimates

    def _calculate_weighted_estimates(self, estimates: Dict[str, List[float]]) -> Dict[str, float]:
        """
        计算加权平均值作为最终估值

        Args:
            estimates: 原始估算值

        Returns:
            Dict: 加权后的估算值
        """
        weighted = {}

        for feature_name, values in estimates.items():
            total_weight = 0
            weighted_sum = 0

            for i, expert in enumerate(self.experts):
                if i < len(values):
                    weight = self.expert_weights.get(expert, 1.0)
                    weighted_sum += values[i] * weight
                    total_weight += weight

            if total_weight > 0:
                weighted[feature_name] = round(weighted_sum / total_weight, 1)
            else:
                weighted[feature_name] = round(statistics.mean(values), 1)

        return weighted

    def apply_estimates_to_features(
        self,
        features: List[Dict],
        estimates: Dict[str, float]
    ) -> List[Dict]:
        """
        将估算结果应用到功能点

        Args:
            features: 功能点列表
            estimates: 估算结果

        Returns:
            List: 更新后的功能点列表
        """
        for feature in features:
            key = self._feature_key(feature)
            feature_name = str(feature.get("功能点") or feature.get("name") or key)

            if key in estimates:
                man_days = self._safe_float(estimates[key], default=self._resolve_original_estimate(feature))
            else:
                man_days = self._resolve_original_estimate(feature)
                logger.warning("功能点 '%s' 没有估算值，使用原始估值: %.2f人天", feature_name, man_days)

            if man_days <= 0:
                man_days = self._resolve_original_estimate(feature)

            if "original_estimate" not in feature:
                feature["original_estimate"] = self._resolve_original_estimate(feature)

            detail = self._latest_estimation_details.get(key, {})
            feature["optimistic"] = detail.get("optimistic")
            feature["most_likely"] = detail.get("most_likely")
            feature["pessimistic"] = detail.get("pessimistic")
            feature["expected"] = round(man_days, 2)
            feature["reasoning"] = detail.get("reasoning")
            feature["预估人天"] = round(man_days, 2)
            feature["profile_context_used"] = bool(detail.get("profile_context_used"))
            feature["context_source"] = str(detail.get("context_source") or "none").strip() or "none"

            logger.info("功能点 '%s' 工作量: %.2f人天", feature_name, feature["预估人天"])

        return features

    def get_expert_estimates_for_excel(self) -> Dict[str, Dict[str, List[float]]]:
        """
        获取专家评分数据用于Excel导出

        Returns:
            Dict: 格式为 {"系统名": {"功能点名": [专家1分, 专家2分, 专家3分]}}
        """
        # 这个方法需要记录每个功能点的专家评分
        # 由于当前实现中专家评分是内部处理的，我们需要在estimate过程中保存这些数据
        # 这里返回一个空字典，实际使用时需要在estimate过程中保存数据
        return {}

    def save_expert_scores(self, feature_name: str, round_scores: List[float]):
        """
        保存专家评分数据

        Args:
            feature_name: 功能点名称
            round_scores: 某一轮的专家评分
        """
        if not hasattr(self, '_expert_scores_dict'):
            self._expert_scores_dict = {}

        if feature_name not in self._expert_scores_dict:
            self._expert_scores_dict[feature_name] = []

        self._expert_scores_dict[feature_name].append(round_scores)

    def get_saved_expert_scores(self) -> Dict[str, List[List[float]]]:
        """
        获取保存的专家评分数据

        Returns:
            Dict: {"功能点1": [[第1轮评分], [第2轮评分], [第3轮评分]]}
        """
        if hasattr(self, '_expert_scores_dict'):
            return self._expert_scores_dict
        return {}


# 全局Agent实例
work_estimation_agent = WorkEstimationAgent()
