"""
Agent编排器
使用LangGraph实现Agent协同工作流程
"""
import logging
from typing import Dict, List, Any
from langgraph.graph import StateGraph, END
from backend.agent.system_identification_agent import system_identification_agent
from backend.agent.feature_breakdown_agent import feature_breakdown_agent
from backend.agent.work_estimation_agent import work_estimation_agent
from backend.utils.excel_generator import excel_generator

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """Agent编排器"""

    def __init__(self):
        """初始化编排器"""
        self.name = "Agent编排器"
        logger.info(f"{self.name}初始化完成")

    def process_requirement(self, task_id: str, requirement_data: Dict[str, str]) -> str:
        """
        处理需求评估的主流程

        Args:
            task_id: 任务ID
            requirement_data: 需求数据，包含解析后的文档内容

        Returns:
            str: 生成的Excel报告文件路径
        """
        try:
            logger.info(f"开始处理任务: {task_id}")

            # 步骤1：系统识别
            logger.info("=" * 60)
            logger.info("步骤1: 系统识别")
            systems = system_identification_agent.identify(
                requirement_data.get("requirement_content", "")
            )
            system_identification_agent.validate_systems(systems)

            # 步骤2：功能点拆分
            logger.info("=" * 60)
            logger.info("步骤2: 功能点拆分")
            systems_data = {}
            for system in systems:
                system_name = system["name"]
                system_type = system["type"]
                logger.info(f"拆分系统: {system_name}")

                features = feature_breakdown_agent.breakdown(
                    requirement_data.get("requirement_content", ""),
                    system_name,
                    system_type
                )
                systems_data[system_name] = features

            # 步骤3：工作量估算
            logger.info("=" * 60)
            logger.info("步骤3: 工作量估算")

            # 收集所有功能点
            all_features = []
            for features in systems_data.values():
                all_features.extend(features)

            # Delphi估算
            estimates = work_estimation_agent.estimate(all_features)

            # 应用估算结果
            for system_name in systems_data:
                systems_data[system_name] = work_estimation_agent.apply_estimates_to_features(
                    systems_data[system_name],
                    estimates
                )

            # 步骤4：生成Excel报告
            logger.info("=" * 60)
            logger.info("步骤4: 生成Excel报告")
            report_path = excel_generator.generate_report(
                task_id=task_id,
                requirement_name=requirement_data.get("requirement_name", "未知需求"),
                systems_data=systems_data
            )

            logger.info("=" * 60)
            logger.info(f"任务处理完成: {task_id}")
            logger.info(f"报告路径: {report_path}")

            return report_path

        except Exception as e:
            logger.error(f"任务处理失败: {str(e)}")
            raise

    def process_with_retry(
        self,
        task_id: str,
        requirement_data: Dict[str, str],
        max_retry: int = 3
    ) -> str:
        """
        带重试机制的需求处理

        Args:
            task_id: 任务ID
            requirement_data: 需求数据
            max_retry: 最大重试次数

        Returns:
            str: Excel报告文件路径
        """
        for attempt in range(max_retry):
            try:
                logger.info(f"任务处理尝试 {attempt + 1}/{max_retry}")
                return self.process_requirement(task_id, requirement_data)
            except Exception as e:
                logger.warning(f"任务处理失败（第{attempt + 1}次）: {str(e)}")

                if attempt < max_retry - 1:
                    logger.info("准备重试...")
                else:
                    logger.error(f"任务处理失败，已重试{max_retry}次")
                    raise


# 全局编排器实例
agent_orchestrator = AgentOrchestrator()
