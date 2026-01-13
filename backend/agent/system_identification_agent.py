"""
系统识别Agent
从需求文本中识别涉及改造的所有系统
"""
import logging
import json
import os
from typing import Dict, List
from backend.utils.llm_client import llm_client
from backend.prompts.prompt_templates import SYSTEM_IDENTIFICATION_PROMPT

logger = logging.getLogger(__name__)


class SystemIdentificationAgent:
    """系统识别Agent"""

    def __init__(self):
        """初始化Agent"""
        self.name = "系统识别Agent"
        self.prompt_template = SYSTEM_IDENTIFICATION_PROMPT
        self.system_list = []  # 延迟加载
        self.subsystem_mapping = {}  # 延迟加载
        logger.info(f"{self.name}初始化完成（系统列表和映射将在首次使用时加载）")

    def _load_system_list(self) -> List[str]:
        """
        加载标准系统列表

        优先级：
        1. system_list.md (Markdown格式，更易维护)
        2. system_list.csv (CSV格式，向后兼容)

        Markdown格式示例：
        ```markdown
        # 系统名称 | 英文简称 | 系统状态 | 系统分类
        新一代核心 | CBS | 运行中 | 核心系统
        ```
        """
        system_list = []
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # 尝试从MD文件加载
        md_path = os.path.join(base_dir, "system_list.md")
        if os.path.exists(md_path):
            try:
                with open(md_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        # 跳过注释行和空行
                        if not line or line.startswith('#') or line.startswith('>'):
                            continue
                        # 跳过标题行（包含"系统名称"的行）
                        if '系统名称' in line and '英文简称' in line:
                            continue
                        # 解析数据行：系统名称 | 英文简称 | 系统状态 | 系统分类
                        if '|' in line:
                            parts = [p.strip() for p in line.split('|')]
                            if len(parts) >= 1 and parts[0]:
                                system_list.append(parts[0])

                logger.info(f"从system_list.md加载了{len(system_list)}个系统")
                return system_list
            except Exception as e:
                logger.warning(f"加载system_list.md失败: {e}，尝试加载CSV文件")

        # 回退到CSV文件加载
        csv_path = os.path.join(base_dir, "system_list.csv")
        if os.path.exists(csv_path):
            try:
                with open(csv_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("系统名称"):
                            parts = line.split(',')
                            if len(parts) >= 1 and parts[0].strip():
                                system_list.append(parts[0].strip())
                logger.info(f"从system_list.csv加载了{len(system_list)}个系统")
                return system_list
            except Exception as e:
                logger.warning(f"加载system_list.csv失败: {e}")

        if not system_list:
            logger.info(f"未找到系统列表文件（MD或CSV），请在前端配置页面添加系统")

        return system_list

    def _load_subsystem_mapping(self) -> Dict[str, str]:
        """
        加载子系统与主系统的映射关系

        Returns:
            Dict: 子系统名称 -> 主系统名称 的映射
        """
        subsystem_mapping = {}
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        csv_path = os.path.join(base_dir, "backend", "subsystem_list.csv")

        if os.path.exists(csv_path):
            try:
                with open(csv_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        # 跳过空行和标题行
                        if not line or line.startswith("子系统名称"):
                            continue
                        parts = line.split(',')
                        if len(parts) >= 2:
                            subsystem = parts[0].strip()
                            main_system = parts[1].strip()
                            if subsystem and main_system:
                                subsystem_mapping[subsystem] = main_system

                logger.info(f"从subsystem_list.csv加载了{len(subsystem_mapping)}个子系统映射")
            except Exception as e:
                logger.warning(f"加载subsystem_list.csv失败: {e}")
        else:
            logger.info(f"未找到subsystem_list.csv文件，可通过前端配置页面添加映射")

        return subsystem_mapping

    def identify(self, requirement_content: str) -> List[Dict[str, str]]:
        """
        识别需求中涉及的所有系统

        Args:
            requirement_content: 需求内容文本

        Returns:
            List: 系统列表，每个系统包含name、type、description字段

        Raises:
            ValueError: 识别失败或返回格式错误
        """
        try:
            # 延迟加载系统列表（首次使用时）
            if not self.system_list:
                logger.info("[系统识别] 首次使用，加载系统列表...")
                self.system_list = self._load_system_list()
                logger.info(f"[系统识别] 已加载 {len(self.system_list)} 个标准系统")

            # 延迟加载子系统映射（首次使用时）
            if not self.subsystem_mapping:
                logger.info("[系统识别] 首次使用，加载子系统映射...")
                self.subsystem_mapping = self._load_subsystem_mapping()
                logger.info(f"[系统识别] 已加载 {len(self.subsystem_mapping)} 个子系统映射")

            logger.info(f"[系统识别] 开始识别系统...")
            logger.info(f"[内容长度] {len(requirement_content)} 字符")

            # 构建提示词
            user_prompt = f"需求内容：\n\n{requirement_content}\n\n请识别该需求涉及的所有系统。"

            # 调用LLM
            response = llm_client.chat_with_system_prompt(
                system_prompt=self.prompt_template,
                user_prompt=user_prompt,
                temperature=0.3  # 使用较低温度以获得更稳定的结果
            )

            # 解析JSON响应
            result = llm_client.extract_json(response)

            if "systems" not in result:
                raise ValueError("响应中缺少'systems'字段")

            systems = result["systems"]

            # 验证数据格式并标准化系统名称
            for system in systems:
                if "name" not in system:
                    raise ValueError("系统缺少'name'字段")

                # 标准化系统名称：匹配标准系统列表
                original_name = system["name"]
                standard_name = self._match_standard_system(original_name)
                system["name"] = standard_name
                system["original_name"] = original_name  # 保留原始名称

                if "type" not in system:
                    system["type"] = "主系统"  # 默认类型
                if "description" not in system:
                    system["description"] = ""

                logger.debug(f"  └─ {original_name} → {standard_name}")

            logger.info(f"[系统识别] 识别完成，共 {len(systems)} 个系统")
            return systems

        except Exception as e:
            logger.error(f"[系统识别] 识别失败: {str(e)}")
            raise

    def _match_standard_system(self, system_name: str) -> str:
        """
        匹配标准系统名称

        Args:
            system_name: 识别出的系统名称

        Returns:
            str: 标准系统名称，如果无法匹配返回None
        """
        # 首先尝试精确匹配
        if system_name in self.system_list:
            return system_name

        # 尝试模糊匹配（包含关系）
        for standard_name in self.system_list:
            if system_name in standard_name or standard_name in system_name:
                return standard_name

        # 尝试关键词匹配
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
            "中台": "支付中台",  # 默认支付中台，如果其他中台可以再添加
            # 新增关键词映射
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
                # 计算匹配度
                score = len(keyword) / len(system_name)
                if score > best_score and standard_name in self.system_list:
                    best_score = score
                    best_match = standard_name

        if best_match:
            return best_match

        # 如果都匹配不上，保留原系统名称并标记为外部系统
        logger.warning(f"系统 '{system_name}' 无法匹配到标准系统名称，保留为外部系统")
        return system_name  # 返回原系统名称，而不是None

    def validate_and_filter_systems(self, systems: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        验证并标准化系统列表，保留所有系统（包括无法匹配的）
        将子系统映射到主系统

        Args:
            systems: 原始系统列表

        Returns:
            List: 验证后的系统列表
        """
        validated_systems = []
        standard_count = 0
        external_count = 0
        subsystem_count = 0

        for system in systems:
            original_name = system.get("name", "")
            standard_name = self._match_standard_system(original_name)

            # 检查是否为子系统，如果是则映射到主系统
            if standard_name in self.subsystem_mapping:
                main_system = self.subsystem_mapping[standard_name]
                logger.info(f"  → 子系统映射: {original_name} → {standard_name} → 主系统: {main_system}")
                standard_name = main_system
                subsystem_count += 1

            # 检查是否已经添加过（避免重复）
            if not any(s["name"] == standard_name for s in validated_systems):
                system["name"] = standard_name
                system["original_name"] = original_name

                # 标记是否为标准系统
                if standard_name in self.system_list:
                    system["is_standard"] = True
                    standard_count += 1
                    logger.debug(f"  ✓ {original_name} → {standard_name} (标准系统)")
                else:
                    system["is_standard"] = False
                    external_count += 1
                    logger.warning(f"  ! {original_name} → {standard_name} (外部系统)")

                validated_systems.append(system)
            else:
                logger.warning(f"  - 系统 '{standard_name}' 重复，已跳过")

        logger.info(f"[系统验证] 完成，共 {len(validated_systems)} 个系统（标准: {standard_count}，外部: {external_count}，子系统映射: {subsystem_count}）")
        return validated_systems

    def validate_system_names_in_features(self, system_name: str, features: List[Dict]) -> List[Dict]:
        """
        校验功能点中的系统名称，修正不一致的系统引用

        Args:
            system_name: 当前系统的标准名称
            features: 功能点列表

        Returns:
            List: 修正后的功能点列表
        """
        validated_features = []

        for feature in features:
            # 检查功能点中的系统名称字段
            feature_system = feature.get("系统", "")
            if feature_system and feature_system != system_name:
                # 尝试匹配标准系统
                standard_name = self._match_standard_system(feature_system)
                if standard_name == system_name:
                    # 匹配成功，更新为标准名称
                    feature["系统"] = system_name
                    logger.info(f"功能点 '{feature.get('功能点', '')}' 的系统名称从 '{feature_system}' 修正为 '{system_name}'")
                else:
                    # 无法匹配，记录警告并使用当前系统
                    logger.warning(f"功能点 '{feature.get('功能点', '')}' 中的系统 '{feature_system}' 无法匹配当前系统 '{system_name}'，已修正")
                    feature["系统"] = system_name

            validated_features.append(feature)

        return validated_features

    def validate_systems(self, systems: List[Dict[str, str]]) -> bool:
        """
        验证识别结果的合理性

        Args:
            systems: 系统列表

        Returns:
            bool: 是否合理
        """
        if not systems:
            logger.warning("未识别到任何系统")
            return False

        # 检查是否有主系统
        has_main_system = any(s.get("type") == "主系统" for s in systems)
        if not has_main_system:
            logger.warning("未识别到主系统，将第一个系统标记为主系统")
            systems[0]["type"] = "主系统"

        return True


# 全局Agent实例
system_identification_agent = SystemIdentificationAgent()
