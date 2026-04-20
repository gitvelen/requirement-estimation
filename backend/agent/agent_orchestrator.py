"""
Agent编排器
使用LangGraph实现Agent协同工作流程
支持知识库注入到Agent中
"""
import logging
import time
import concurrent.futures
from datetime import datetime
from typing import Dict, List, Any, Callable, Optional
from langgraph.graph import StateGraph, END
from backend.agent.system_identification_agent import get_system_identification_agent
from backend.agent.feature_breakdown_agent import get_feature_breakdown_agent
from backend.agent.work_estimation_agent import work_estimation_agent
from backend.utils.excel_generator import excel_generator
from backend.service.knowledge_service import get_knowledge_service
from backend.service.system_profile_service import get_system_profile_service
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

    def _resolve_target_system_selection(self, requirement_data: Dict[str, Any]) -> tuple[str, str]:
        selection_mode = str(requirement_data.get("target_system_mode") or "unlimited").strip().lower()
        if selection_mode not in {"specific", "unlimited"}:
            selection_mode = "unlimited"
        target_system_name = str(requirement_data.get("target_system_name") or "").strip()
        return selection_mode, target_system_name

    def _build_specific_system_payload(self, target_system_name: str) -> List[Dict[str, Any]]:
        profile_service = get_system_profile_service()
        system_id = ""
        try:
            profile = profile_service.get_profile(target_system_name)
            if isinstance(profile, dict):
                system_id = str(profile.get("system_id") or "").strip()
        except Exception as exc:
            logger.debug("[待评估系统] 读取系统画像失败（忽略）: %s", exc)

        return [
            {
                "name": target_system_name,
                "type": "主系统",
                "is_standard": True,
                "system_id": system_id,
            }
        ]

    def _build_specific_ai_system_analysis(
        self,
        systems: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        selected_systems: List[Dict[str, Any]] = []
        missing_profiles: List[str] = []

        for system in systems or []:
            if not isinstance(system, dict):
                continue
            system_name = str(system.get("name") or "").strip()
            if not system_name:
                continue
            system_id = str(system.get("system_id") or "").strip()
            if not system_id:
                missing_profiles.append(system_name)
            selected_systems.append(
                {
                    "name": system_name,
                    "type": system.get("type") or "主系统",
                    "description": "创建时已指定待评估系统",
                    "confidence": "高",
                    "reasons": ["项目经理在创建阶段明确选择该待评估系统"],
                    "kb_hits": [],
                    "system_id": system_id,
                }
            )

        return {
            "generated_at": datetime.now().isoformat(),
            "knowledge_enabled": bool(self.knowledge_enabled),
            "candidate_systems": [],
            "selected_systems": selected_systems,
            "maybe_systems": [],
            "questions": [],
            "missing_system_profiles": missing_profiles,
            "final_verdict": "skipped",
            "reason_summary": "已按待评估系统跳过自动系统识别",
            "matched_aliases": [],
            "context_degraded": False,
            "degraded_reasons": [],
            "result_status": "success",
        }

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
            tuple: (report_path, systems_data, ai_system_analysis, ai_original_output)
                - report_path: 生成的Excel报告文件路径
                - systems_data: 所有系统的功能点数据
                - ai_system_analysis: 系统校准分析
                - ai_original_output: AI 原始输出快照
        """
        start_time = time.time()
        requirement_name = requirement_data.get("requirement_name", "未知需求")
        selection_mode, target_system_name = self._resolve_target_system_selection(requirement_data)
        identification_input_parts: List[str] = []
        for value in (
            requirement_name,
            requirement_data.get("requirement_summary", ""),
            requirement_data.get("requirement_content", ""),
        ):
            normalized = str(value or "").strip()
            if normalized and normalized not in identification_input_parts:
                identification_input_parts.append(normalized)
        identification_content = "\n".join(identification_input_parts)

        try:
            logger.info("")
            logger.info("=" * 80)
            logger.info(f"[任务开始] 任务ID: {task_id}")
            logger.info(f"[需求信息] 名称: {requirement_name}")
            logger.info(f"[评估范围] selection_mode={selection_mode}, target_system={target_system_name or '不限'}")
            logger.info("=" * 80)

            # 步骤1：系统识别
            step_start = time.time()
            logger.info("")
            logger.info("[步骤 1/4] 系统识别")
            logger.info("-" * 80)

            identification_result = None
            ai_system_analysis = None
            sys_agent = None

            if selection_mode == "specific":
                if not target_system_name:
                    raise ValueError("具体系统模式缺少待评估系统名称")

                self._update_progress(progress_callback, 20, "正在锁定待评估系统...")
                systems = self._build_specific_system_payload(target_system_name)
                ai_system_analysis = self._build_specific_ai_system_analysis(systems)
                identification_result = {
                    "final_verdict": "skipped",
                    "reason_summary": "已按待评估系统跳过自动系统识别",
                    "selected_systems": systems,
                    "candidate_systems": [],
                    "maybe_systems": [],
                    "questions": [],
                    "matched_aliases": [],
                    "context_degraded": False,
                    "degraded_reasons": [],
                    "result_status": "success",
                }
            else:
                self._update_progress(progress_callback, 20, "正在识别系统...")

                # 获取系统识别Agent（注入knowledge_service）
                sys_agent = get_system_identification_agent(self.knowledge_service)
                if settings.ENABLE_V27_RUNTIME:
                    identification_result = sys_agent.identify_with_verdict(
                        identification_content,
                        task_id=task_id,
                    )
                    systems = identification_result.get("selected_systems") or []
                    if identification_result.get("final_verdict") != "matched":
                        raise ValueError(
                            f"系统识别结果为{identification_result.get('final_verdict')}，"
                            f"{identification_result.get('reason_summary') or '无法继续自动拆分'}"
                        )
                else:
                    systems = sys_agent.identify(
                        identification_content,
                        task_id=task_id
                    )

                    # 验证和标准化系统名称
                    logger.info("[处理中] 验证和标准化系统名称...")
                    systems = sys_agent.validate_and_filter_systems(systems)

                    if not systems:
                        raise ValueError("未识别到任何系统")

                    sys_agent.validate_systems(systems)

                # 【新增】构建系统校准分析（供编辑页展示与纠偏：候选系统/置信度/疑问清单）
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

            # 【v2.4】保存 Step 1 快照
            ai_original_output_step1 = {
                "systems": [{"name": s["name"], "type": s.get("type"), "is_standard": s.get("is_standard", False)} for s in systems],
                "system_count": len(systems),
                "timestamp": time.time(),
                "final_verdict": (identification_result or {}).get("final_verdict") if identification_result else "matched",
                "selection_mode": selection_mode,
                "reason_summary": (identification_result or {}).get("reason_summary") or "",
                "context_degraded": bool((ai_system_analysis or {}).get("context_degraded")),
                "result_status": (ai_system_analysis or {}).get("result_status") or "success",
            }

            self._update_progress(progress_callback, 35, f"系统识别完成：{len(systems)}个系统")

            # 步骤2：功能点拆分
            step_start = time.time()
            logger.info("")
            logger.info("[步骤 2/4] 功能点拆分")
            logger.info("-" * 80)

            self._update_progress(progress_callback, 40, "正在拆分功能点...")

            systems_data = {}
            total_features = 0
            feature_context_degraded = False
            degraded_reasons = list((ai_system_analysis or {}).get("degraded_reasons") or [])
            applied_adjustments_summary: Dict[str, List[Dict[str, Any]]] = {}

            # 并行化功能点拆分
            def process_single_system(idx, system):
                """处理单个系统的功能点拆分（可并行执行）"""
                system_name = system["name"]
                system_type = system["type"]
                logger.info(f"[{idx}/{len(systems)}] 拆分系统: {system_name}")

                # 获取功能拆分Agent（注入knowledge_service）
                feature_agent = get_feature_breakdown_agent(self.knowledge_service)
                if settings.ENABLE_V27_RUNTIME or selection_mode == "specific":
                    feature_result = feature_agent.breakdown_with_context(
                        requirement_data.get("requirement_content", ""),
                        system_name,
                        system_type,
                        task_id=task_id,
                    )
                    features = feature_result["features"]
                    context_degraded = feature_result.get("context_degraded", False)
                    degraded_reasons_local = feature_result.get("degraded_reasons") or []
                    applied_adjustments_local = feature_result.get("applied_adjustments") or []
                else:
                    features = feature_agent.breakdown(
                        requirement_data.get("requirement_content", ""),
                        system_name,
                        system_type,
                        task_id=task_id
                    )
                    context_degraded = False
                    degraded_reasons_local = []
                    applied_adjustments_local = []

                # 校验功能点中的系统名称
                logger.info(f"  └─ 校验功能点系统名称...")
                for feature in features:
                    if isinstance(feature, dict):
                        feature["系统"] = system_name
                if sys_agent is not None:
                    features = sys_agent.validate_system_names_in_features(
                        system_name, features
                    )

                logger.info(f"  └─ 完成: {len(features)} 个功能点")
                return {
                    "system_name": system_name,
                    "features": features,
                    "context_degraded": context_degraded,
                    "degraded_reasons": degraded_reasons_local,
                    "applied_adjustments": applied_adjustments_local,
                }

            # 使用线程池并行处理（最多4个并发）
            max_workers = min(4, len(systems))
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(process_single_system, idx, system): idx
                    for idx, system in enumerate(systems, 1)
                }

                for future in concurrent.futures.as_completed(futures):
                    idx = futures[future]
                    try:
                        result = future.result()
                        system_name = result["system_name"]
                        features = result["features"]

                        systems_data[system_name] = features
                        total_features += len(features)

                        if result["context_degraded"]:
                            feature_context_degraded = True
                            degraded_reasons.extend(result["degraded_reasons"])
                        if result["applied_adjustments"]:
                            applied_adjustments_summary[system_name] = result["applied_adjustments"]

                        # 更新进度
                        progress = 40 + int(20 * len(systems_data) / len(systems))
                        self._update_progress(progress_callback, progress, f"拆分功能点：{system_name} ({len(systems_data)}/{len(systems)})")
                    except Exception as e:
                        logger.error(f"处理系统时出错: {e}", exc_info=True)
                        raise

            if selection_mode == "specific" and total_features == 0:
                raise ValueError(f"待评估系统【{target_system_name}】未拆分出相关功能点")

            step_time = time.time() - step_start
            logger.info(f"[完成] 共拆分 {total_features} 个功能点")
            logger.info(f"[耗时] {step_time:.2f}秒")

            # 【v2.4】保存 Step 2 快照
            ai_original_output_step2 = {
                "systems_data": {
                    sys_name: [
                        {
                            "id": f.get("id"),
                            "功能点": f.get("功能点"),
                            "业务描述": f.get("业务描述"),
                            "功能模块": f.get("功能模块")
                        } for f in features
                    ] for sys_name, features in systems_data.items()
                },
                "total_features": total_features,
                "timestamp": time.time(),
                "context_degraded": feature_context_degraded,
                "applied_adjustments": applied_adjustments_summary,
            }

            if settings.ENABLE_V27_RUNTIME and ai_system_analysis is not None:
                combined_reasons: List[str] = []
                for item in degraded_reasons:
                    normalized = str(item or "").strip()
                    if normalized and normalized not in combined_reasons:
                        combined_reasons.append(normalized)
                ai_system_analysis["context_degraded"] = bool(
                    ai_system_analysis.get("context_degraded") or feature_context_degraded
                )
                ai_system_analysis["degraded_reasons"] = combined_reasons
                if ai_system_analysis.get("context_degraded"):
                    ai_system_analysis["result_status"] = "partial_success"
                else:
                    ai_system_analysis["result_status"] = ai_system_analysis.get("result_status") or "success"

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

            # 并行化 build_estimation_context
            profile_service = get_system_profile_service()
            system_context_map = {}

            def build_context_for_system(system_name):
                """为单个系统构建估算上下文（可并行执行）"""
                return system_name, profile_service.build_estimation_context(system_name)

            max_workers = min(4, len(systems_data))
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                context_futures = {
                    executor.submit(build_context_for_system, name): name
                    for name in systems_data.keys()
                }

                for future in concurrent.futures.as_completed(context_futures):
                    try:
                        system_name, context = future.result()
                        system_context_map[system_name] = context
                    except Exception as e:
                        logger.error(f"构建系统上下文时出错: {e}", exc_info=True)
                        # 降级：使用空上下文
                        system_name = context_futures[future]
                        system_context_map[system_name] = {}

            # Delphi估算
            estimates = work_estimation_agent.estimate(
                all_features,
                system_context_map=system_context_map,
            )

            # 应用估算结果
            total_workload = 0
            for system_name in systems_data:
                systems_data[system_name] = work_estimation_agent.apply_estimates_to_features(
                    systems_data[system_name],
                    estimates
                )
                profile_service.record_estimation_context_artifact(
                    system_name=system_name,
                    task_id=task_id,
                    features=[feature for feature in systems_data[system_name] if isinstance(feature, dict)],
                    context_payload=system_context_map.get(system_name, {}),
                    trigger="agent_orchestrator",
                )
                # 统计工作量
                system_workload = sum(f.get("预估人天", 0) for f in systems_data[system_name])
                total_workload += system_workload
                logger.info(f"  └─ {system_name}: {len(systems_data[system_name])} 个功能点，总工作量: {system_workload:.1f} 人天")

            step_time = time.time() - step_start
            logger.info(f"[完成] 总工作量估算: {total_workload:.1f} 人天")
            logger.info(f"[耗时] {step_time:.2f}秒")

            # 【v2.4】保存 Step 3 快照（从 work_estimation_agent 获取详细估算数据）
            estimation_details = work_estimation_agent._latest_estimation_details or {}
            ai_original_output_step3 = {
                "estimation_details": {
                    fid: {
                        "optimistic": detail.get("optimistic"),
                        "most_likely": detail.get("most_likely"),
                        "pessimistic": detail.get("pessimistic"),
                        "expected": detail.get("expected"),
                        "reasoning": detail.get("reasoning"),
                        "original_estimate": detail.get("original_estimate"),
                        "profile_context_used": detail.get("profile_context_used"),
                        "context_source": detail.get("context_source"),
                    } for fid, detail in estimation_details.items()
                },
                "total_workload": total_workload,
                "timestamp": time.time()
            }

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

            # 【v2.4】汇总三步快照并返回
            ai_original_output = {
                "system_recognition": ai_original_output_step1,
                "feature_split": ai_original_output_step2,
                "work_estimation": ai_original_output_step3
            }

            # 【新增】返回report_path、systems_data、ai_system_analysis与ai_original_output，用于人机协作修正
            return report_path, systems_data, ai_system_analysis, ai_original_output

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
            tuple: (report_path, systems_data, ai_system_analysis, ai_original_output)
                - report_path: Excel报告文件路径
                - systems_data: 所有系统的功能点数据
                - ai_system_analysis: 系统校准分析（候选系统/置信度/疑问清单）
                - ai_original_output: AI 原始输出快照（三步）
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
