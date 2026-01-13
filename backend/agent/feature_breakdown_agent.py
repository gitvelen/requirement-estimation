"""
功能点拆分Agent
按系统维度拆分功能点
"""
import logging
import json
from typing import Dict, List
from backend.utils.llm_client import llm_client
from backend.prompts.prompt_templates import FEATURE_BREAKDOWN_PROMPT

logger = logging.getLogger(__name__)


class FeatureBreakdownAgent:
    """功能点拆分Agent"""

    def __init__(self):
        """初始化Agent"""
        self.name = "功能点拆分Agent"
        self.prompt_template = FEATURE_BREAKDOWN_PROMPT
        logger.info(f"{self.name}初始化完成")

    def breakdown(
        self,
        requirement_content: str,
        system_name: str,
        system_type: str = "主系统"
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

            # 构建提示词
            user_prompt = f"""需求内容：\n\n{requirement_content}\n\n"""
            user_prompt += f"""请针对【{system_name}】（类型：{system_type}）进行功能点拆分。\n\n"""
            user_prompt += """拆分要求：
1. 只拆分属于该系统的功能点
2. 功能点粒度控制在0.5-5人天
3. 明确标注依赖关系
4. 评估复杂度（高/中/低）"""

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


# 全局Agent实例
feature_breakdown_agent = FeatureBreakdownAgent()
