"""
Agent编排器
使用LangGraph实现Agent协同工作流程
支持知识库注入到Agent中
"""
import logging
import time
from typing import Dict, List, Any, Callable, Optional
from langgraph.graph import StateGraph, END
from backend.agent.system_identification_agent import get_system_identification_agent
from backend.agent.feature_breakdown_agent import get_feature_breakdown_agent
from backend.agent.work_estimation_agent import work_estimation_agent
from backend.utils.excel_generator import excel_generator
from backend.service.knowledge_service import get_knowledge_service
from backend.config.config import settings

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """Agent编排器"""

    def __init__(self, knowledge_service=None):
        """
        初始化编排器

        Args:
            knowledge_service: 知识库服务（可选）
        """
        self.name = "Agent编排器"

        # 初始化知识库服务
        self.knowledge_service = knowledge_service
        self.knowledge_enabled = settings.KNOWLEDGE_ENABLED

        if self.knowledge_enabled:
            if self.knowledge_service is None:
                try:
                    self.knowledge_service = get_knowledge_service()
                    logger.info(f"[{self.name}] 知识库功能已启用")
                except Exception as e:
                    logger.warning(f"[{self.name}] 知识库初始化失败: {e}，继续使用传统方式")
                    self.knowledge_enabled = False
            else:
                logger.info(f"[{self.name}] 知识库功能已启用")
        else:
            logger.info(f"[{self.name}] 知识库功能未启用")

        logger.info(f"[{self.name}] 初始化完成")

    def _update_progress(
        self,
        progress_callback: Optional[Callable[[int, str], None]],
        progress: int,
        message: str
    ):
        """
        更新任务进度

        Args:
            progress_callback: 进度回调函数
            progress: 进度值 (0-100)
            message: 进度消息
        """
        if progress_callback:
            try:
                progress_callback(progress, message)
            except Exception as e:
                logger.warning(f"进度回调失败: {e}")

    def process_requirement(
        self,
        task_id: str,
        requirement_data: Dict[str, str],
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> tuple:
        """
        处理需求评估的主流程

        Args:
            task_id: 任务ID
            requirement_data: 需求数据，包含解析后的文档内容
            progress_callback: 进度回调函数 (progress, message) => None

        Returns:
            tuple: (report_path, systems_data)
                - report_path: 生成的Excel报告文件路径
                - systems_data: 所有系统的功能点数据
        """
        start_time = time.time()
        requirement_name = requirement_data.get("requirement_name", "未知需求")

        try:
            logger.info("")
            logger.info("=" * 80)
            logger.info(f"[任务开始] 任务ID: {task_id}")
            logger.info(f"[需求信息] 名称: {requirement_name}")
            logger.info("=" * 80)

            # 步骤1：系统识别
            step_start = time.time()
            logger.info("")
            logger.info("[步骤 1/4] 系统识别")
            logger.info("-" * 80)

            self._update_progress(progress_callback, 20, "正在识别系统...")

            # 获取系统识别Agent（注入knowledge_service）
            sys_agent = get_system_identification_agent(self.knowledge_service)
            systems = sys_agent.identify(
                requirement_data.get("requirement_content", ""),
                task_id=task_id
            )

            # 验证和标准化系统名称
            logger.info("[处理中] 验证和标准化系统名称...")
            systems = sys_agent.validate_and_filter_systems(systems)

            if not systems:
                raise ValueError("未识别到任何系统")

            sys_agent.validate_systems(systems)

            # 【新增】构建系统校准分析（供编辑页展示与纠偏：候选系统/置信度/疑问清单）
            ai_system_analysis = None
            try:
                ai_system_analysis = sys_agent.build_ai_system_analysis(systems)
            except Exception as e:
                logger.debug(f"[系统识别] 构建系统校准分析失败（忽略）: {e}")

            # 统计系统信息
            system_names = [s["name"] for s in systems]
            main_systems = [s for s in systems if s.get("type") == "主系统"]
            standard_count = sum(1 for s in systems if s.get("is_standard", False))

            step_time = time.time() - step_start
            logger.info(f"[完成] 识别到 {len(systems)} 个系统（标准系统: {standard_count}，主系统: {len(main_systems)}）")
            logger.info(f"[系统列表] {', '.join(system_names)}")
            logger.info(f"[耗时] {step_time:.2f}秒")

            self._update_progress(progress_callback, 35, f"系统识别完成：{len(systems)}个系统")

            # 步骤2：功能点拆分
            step_start = time.time()
            logger.info("")
            logger.info("[步骤 2/4] 功能点拆分")
            logger.info("-" * 80)

            self._update_progress(progress_callback, 40, "正在拆分功能点...")

            systems_data = {}
            total_features = 0

            for idx, system in enumerate(systems, 1):
                system_name = system["name"]
                system_type = system["type"]
                logger.info(f"[{idx}/{len(systems)}] 拆分系统: {system_name}")

                # 更新进度
                progress = 40 + int(20 * idx / len(systems))
                self._update_progress(progress_callback, progress, f"拆分功能点：{system_name} ({idx}/{len(systems)})")

                # 获取功能拆分Agent（注入knowledge_service）
                feature_agent = get_feature_breakdown_agent(self.knowledge_service)
                features = feature_agent.breakdown(
                    requirement_data.get("requirement_content", ""),
                    system_name,
                    system_type,
                    task_id=task_id
                )

                # 校验功能点中的系统名称
                logger.info(f"  └─ 校验功能点系统名称...")
                features = sys_agent.validate_system_names_in_features(
                    system_name, features
                )

                systems_data[system_name] = features
                total_features += len(features)
                logger.info(f"  └─ 完成: {len(features)} 个功能点")

            step_time = time.time() - step_start
            logger.info(f"[完成] 共拆分 {total_features} 个功能点")
            logger.info(f"[耗时] {step_time:.2f}秒")

            self._update_progress(progress_callback, 60, f"功能点拆分完成：{total_features}个功能点")

            # 步骤3：工作量估算
            step_start = time.time()
            logger.info("")
            logger.info("[步骤 3/4] 工作量估算")
            logger.info("-" * 80)

            self._update_progress(progress_callback, 65, "正在进行工作量估算...")

            # 收集所有功能点
            all_features = []
            for features in systems_data.values():
                all_features.extend(features)

            logger.info(f"[处理中] 开始估算 {len(all_features)} 个功能点的工作量...")

            # Delphi估算
            estimates = work_estimation_agent.estimate(all_features)

            # 应用估算结果
            total_workload = 0
            for system_name in systems_data:
                systems_data[system_name] = work_estimation_agent.apply_estimates_to_features(
                    systems_data[system_name],
                    estimates
                )
                # 统计工作量
                system_workload = sum(f.get("预估人天", 0) for f in systems_data[system_name])
                total_workload += system_workload
                logger.info(f"  └─ {system_name}: {len(systems_data[system_name])} 个功能点，总工作量: {system_workload:.1f} 人天")

            step_time = time.time() - step_start
            logger.info(f"[完成] 总工作量估算: {total_workload:.1f} 人天")
            logger.info(f"[耗时] {step_time:.2f}秒")

            self._update_progress(progress_callback, 85, f"工作量估算完成：{total_workload:.1f}人天")

            # 步骤4：生成Excel报告
            step_start = time.time()
            logger.info("")
            logger.info("[步骤 4/4] 生成Excel报告")
            logger.info("-" * 80)

            self._update_progress(progress_callback, 90, "正在生成Excel报告...")

            # 生成专家评分数据（用于Excel）
            expert_estimates = work_estimation_agent.get_expert_estimates_for_excel()

            report_path = excel_generator.generate_report(
                task_id=task_id,
                requirement_name=requirement_name,
                systems_data=systems_data,
                expert_estimates=expert_estimates
            )

            step_time = time.time() - step_start
            total_time = time.time() - start_time

            logger.info(f"[完成] Excel报告生成成功")
            logger.info(f"[文件路径] {report_path}")
            logger.info(f"[耗时] {step_time:.2f}秒")

            self._update_progress(progress_callback, 95, "报告生成完成")

            # 总结
            logger.info("")
            logger.info("=" * 80)
            logger.info(f"[任务完成] 任务ID: {task_id}")
            logger.info(f"[统计信息]")
            logger.info(f"  - 识别系统: {len(systems)} 个")
            logger.info(f"  - 功能点数: {total_features} 个")
            logger.info(f"  - 工作量总计: {total_workload:.1f} 人天")
            logger.info(f"  - 总耗时: {total_time:.2f} 秒")
            logger.info("=" * 80)
            logger.info("")

            # 【新增】返回report_path、systems_data与ai_system_analysis，用于人机协作修正
            return report_path, systems_data, ai_system_analysis

        except Exception as e:
            total_time = time.time() - start_time
            logger.error("")
            logger.error("=" * 80)
            logger.error(f"[任务失败] 任务ID: {task_id}")
            logger.error(f"[错误信息] {str(e)}")
            logger.error(f"[耗时] {total_time:.2f}秒")
            logger.error("=" * 80)
            logger.error("")
            raise

    def process_with_retry(
        self,
        task_id: str,
        requirement_data: Dict[str, str],
        max_retry: int = 3,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> tuple:
        """
        带重试机制的需求处理

        Args:
            task_id: 任务ID
            requirement_data: 需求数据
            max_retry: 最大重试次数
            progress_callback: 进度回调函数

        Returns:
            tuple: (report_path, systems_data, ai_system_analysis)
                - report_path: Excel报告文件路径
                - systems_data: 所有系统的功能点数据
                - ai_system_analysis: 系统校准分析（候选系统/置信度/疑问清单）
        """
        for attempt in range(max_retry):
            try:
                if attempt > 0:
                    logger.info(f"[重试] 第 {attempt + 1}/{max_retry} 次尝试处理任务: {task_id}")
                    self._update_progress(progress_callback, 10, f"重试中... ({attempt + 1}/{max_retry})")
                return self.process_requirement(task_id, requirement_data, progress_callback)
            except Exception as e:
                logger.warning(f"[失败] 第 {attempt + 1} 次尝试失败: {str(e)}")

                if attempt < max_retry - 1:
                    logger.info(f"[等待] 5秒后重试...")
                    import time
                    time.sleep(5)
                else:
                    logger.error(f"[终止] 任务处理失败，已重试 {max_retry} 次")
                    raise


# 全局编排器实例（延迟初始化，支持注入knowledge_service）
agent_orchestrator = None

def get_agent_orchestrator(knowledge_service=None):
    """
    获取Agent编排器实例

    Args:
        knowledge_service: 知识库服务（可选）

    Returns:
        AgentOrchestrator: 编排器实例
    """
    global agent_orchestrator
    if agent_orchestrator is None:
        agent_orchestrator = AgentOrchestrator(knowledge_service)
    return agent_orchestrator
