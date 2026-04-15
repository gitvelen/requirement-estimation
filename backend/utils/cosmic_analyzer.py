"""
COSMIC功能点分析器
根据COSMIC方法进行数据移动分析和计数
"""
import logging
from typing import Dict, List, Any
from backend.utils.llm_client import llm_client
from backend.utils.cosmic_config_store import DEFAULT_COSMIC_CONFIG, load_cosmic_config

logger = logging.getLogger(__name__)


class CosmicAnalyzer:
    """COSMIC功能点分析器"""

    def __init__(self):
        """初始化分析器"""
        self.config = None
        self.load_config()
        logger.info("COSMIC分析器初始化完成")

    def load_config(self):
        """加载配置"""
        try:
            self.config = load_cosmic_config()
        except Exception as e:
            logger.warning(f"加载COSMIC配置失败: {e}，使用默认配置")
            self.config = DEFAULT_COSMIC_CONFIG

    def analyze_feature(self, feature_description: str, feature_info: Dict = None) -> Dict[str, Any]:
        """
        分析功能点的COSMIC数据移动

        Args:
            feature_description: 功能点描述
            feature_info: 功能点详细信息（可选）

        Returns:
            Dict: COSMIC分析结果
        """
        try:
            logger.info(f"[COSMIC分析] 开始分析功能点")

            # 构建分析提示词
            analysis_prompt = self._build_analysis_prompt(feature_description, feature_info)

            # 使用LLM进行智能分析
            system_prompt = """你是COSMIC功能点分析专家。请根据COSMIC方法分析功能点的数据移动。

分析规则：
1. E (Entry): 数据从用户进入功能处理
2. X (Exit): 数据从功能处理返回给用户
3. R (Read): 从持久存储读取数据
4. W (Write): 数据写入持久存储

输出格式（JSON）：
{
  "data_movements": {
    "E": [{"data_group": "数据组名", "description": "说明"}],
    "X": [{"data_group": "数据组名", "description": "说明"}],
    "R": [{"data_group": "数据组名", "description": "说明"}],
    "W": [{"data_group": "数据组名", "description": "说明"}]
  },
  "cff": 数字,
  "counting_basis": "计数依据说明，详细解释为什么这样计数"
}

请仅输出JSON，不要输出其他内容。"""

            response = llm_client.chat_with_system_prompt(
                system_prompt=system_prompt,
                user_prompt=analysis_prompt,
                temperature=0.3
            )

            # 解析响应
            result = llm_client.extract_json(response)

            # 应用配置规则
            result = self._apply_config_rules(result)

            # 验证结果
            self._validate_analysis_result(result)

            logger.info(f"[COSMIC分析] 分析完成，CFF: {result.get('cff', 0)}")
            return result

        except Exception as e:
            logger.error(f"[COSMIC分析] 分析失败: {str(e)}")
            # 返回默认分析结果
            return self._get_default_analysis()

    def _build_analysis_prompt(self, feature_description: str, feature_info: Dict = None) -> str:
        """构建分析提示词"""
        prompt = f"""功能点描述：{feature_description}\n\n"""

        if feature_info:
            prompt += "功能点详细信息：\n"
            if "业务描述" in feature_info:
                prompt += f"业务描述：{feature_info['业务描述']}\n"
            if "输入" in feature_info:
                prompt += f"输入：{feature_info['输入']}\n"
            if "输出" in feature_info:
                prompt += f"输出：{feature_info['输出']}\n"
            if "依赖" in feature_info:
                prompt += f"依赖：{feature_info['依赖']}\n"

        # 添加配置的关键词提示
        if self.config and "data_movement_rules" in self.config:
            prompt += "\n数据移动判定关键词：\n"
            for movement_type, rules in self.config["data_movement_rules"].items():
                if rules.get("enabled", True):
                    keywords = ", ".join(rules.get("keywords", []))
                    prompt += f"- {movement_type.upper()}: {keywords}\n"

        prompt += "\n请分析该功能点的数据移动，并给出详细的计数依据。"
        return prompt

    def _apply_config_rules(self, result: Dict) -> Dict:
        """应用配置规则调整分析结果"""
        if not self.config:
            return result

        # 检查是否需要禁用某些数据移动类型
        data_movement_rules = self.config.get("data_movement_rules", {})
        for movement_type in ["entry", "exit", "read", "write"]:
            if not data_movement_rules.get(movement_type, {}).get("enabled", True):
                type_code = movement_type[0].upper()  # entry -> E
                if "data_movements" in result and type_code in result["data_movements"]:
                    result["data_movements"][type_code] = []
                    logger.debug(f"数据移动 {type_code} 已被配置禁用")

        # 应用计数规则
        counting_rules = self.config.get("counting_rules", {})
        if counting_rules.get("cff_calculation_method") == "weighted":
            # 使用加权计算
            total = 0
            if "data_movements" in result:
                for movement_type, movements in result["data_movements"].items():
                    weight = data_movement_rules.get(movement_type.lower(), {}).get("weight", 1)
                    total += len(movements) * weight
            result["cff"] = total
        elif "cff" not in result:
            # 默认求和
            result["cff"] = self._calculate_cff(result.get("data_movements", {}))

        return result

    def _calculate_cff(self, data_movements: Dict) -> int:
        """计算CFF（COSMIC功能点数）"""
        total = 0
        for movement_type, movements in data_movements.items():
            if isinstance(movements, list):
                total += len(movements)
            else:
                total += movements
        return total

    def _validate_analysis_result(self, result: Dict):
        """验证分析结果"""
        if not self.config:
            return

        validation_rules = self.config.get("validation_rules", {})
        cff = result.get("cff", 0)

        # 检查CFF范围
        min_cff = validation_rules.get("min_cff_per_feature", 2)
        max_cff = validation_rules.get("max_cff_per_feature", 100)

        if cff < min_cff:
            logger.warning(f"CFF值 {cff} 小于最小值 {min_cff}")
        if cff > max_cff:
            logger.warning(f"CFF值 {cff} 大于最大值 {max_cff}")

    def _get_default_analysis(self) -> Dict:
        """获取默认分析结果"""
        return {
            "data_movements": {
                "E": [],
                "X": [],
                "R": [],
                "W": []
            },
            "cff": 0,
            "counting_basis": "分析失败，使用默认值"
        }

    def analyze_features_batch(self, features: List[Dict]) -> List[Dict]:
        """
        批量分析功能点

        Args:
            features: 功能点列表

        Returns:
            List: 包含COSMIC分析的功能点列表
        """
        results = []
        for feature in features:
            try:
                description = feature.get("业务描述", feature.get("功能点", ""))
                cosmic_analysis = self.analyze_feature(description, feature)

                # 将分析结果添加到功能点
                feature_with_cosmic = feature.copy()
                feature_with_cosmic["cosmic_analysis"] = cosmic_analysis

                results.append(feature_with_cosmic)
            except Exception as e:
                logger.error(f"功能点 {feature.get('功能点', '')} COSMIC分析失败: {str(e)}")
                feature["cosmic_analysis"] = self._get_default_analysis()
                results.append(feature)

        return results

    def get_counting_basis_text(self, cosmic_analysis: Dict) -> str:
        """
        生成计数依据文本

        Args:
            cosmic_analysis: COSMIC分析结果

        Returns:
            str: 计数依据说明文本
        """
        data_movements = cosmic_analysis.get("data_movements", {})
        cff = cosmic_analysis.get("cff", 0)
        counting_basis = cosmic_analysis.get("counting_basis", "")

        text_parts = [
            f"**COSMIC功能点计数**\n",
            f"**CFF (COSMIC功能点数)**: {cff}\n\n",
            f"**数据移动明细**:\n"
        ]

        movement_names = {
            "E": "入口数据移动",
            "X": "出口数据移动",
            "R": "读数据移动",
            "W": "写数据移动"
        }

        for movement_type, movements in data_movements.items():
            name = movement_names.get(movement_type, movement_type)
            text_parts.append(f"- {name} ({movement_type}): {len(movements)} 次\n")

            for movement in movements:
                if isinstance(movement, dict):
                    data_group = movement.get("data_group", "未知数据组")
                    description = movement.get("description", "")
                    text_parts.append(f"  • {data_group}: {description}\n")

        text_parts.append(f"\n**计数依据说明**:\n{counting_basis}\n")

        return "".join(text_parts)


# 全局分析器实例
cosmic_analyzer = CosmicAnalyzer()
