"""
PM 修正 diff 计算服务（v2.4）
负责计算 AI 原始输出与 PM 最终版本的差异，以及专家评估与 AI 估算的偏差
"""
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class DiffService:
    """PM 修正 diff 计算服务"""

    @staticmethod
    def compute_phase1_diff(
        task_id: str,
        ai_original_output: Dict[str, Any],
        pm_final_systems_data: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        计算 Phase 1 diff（PM 提交时）

        Args:
            task_id: 任务 ID
            ai_original_output: AI 原始输出快照
            pm_final_systems_data: PM 最终确认的 systems_data

        Returns:
            Dict: 按系统维度组织的 diff 结果
        """
        pm_correction_diff = {}

        # 提取 AI 原始系统列表和功能点列表
        ai_system_recognition = ai_original_output.get("system_recognition") or {}
        ai_feature_split = ai_original_output.get("feature_split") or {}

        ai_systems = {s["name"]: s for s in (ai_system_recognition.get("systems") or [])}
        ai_systems_data = ai_feature_split.get("systems_data") or {}

        pm_systems = set(pm_final_systems_data.keys())
        ai_system_names = set(ai_systems.keys())

        # 系统级 diff
        system_level_diff = []

        # 新增系统
        for sys_name in (pm_systems - ai_system_names):
            system_level_diff.append({
                "operation": "added",
                "system_name": sys_name,
                "timestamp": datetime.now().isoformat()
            })

        # 删除系统
        for sys_name in (ai_system_names - pm_systems):
            system_level_diff.append({
                "operation": "deleted",
                "system_name": sys_name,
                "timestamp": datetime.now().isoformat()
            })

        # 按系统计算功能点级 diff
        for system_name in pm_systems:
            pm_features = pm_final_systems_data.get(system_name) or []
            ai_features = ai_systems_data.get(system_name) or []

            # 构建 AI 功能点索引（按 id 或功能点名称）
            ai_feature_index = {}
            for f in ai_features:
                key = f.get("id") or f.get("功能点")
                if key:
                    ai_feature_index[key] = f

            # 构建 PM 功能点索引
            pm_feature_index = {}
            for f in pm_features:
                key = f.get("id") or f.get("功能点")
                if key:
                    pm_feature_index[key] = f

            feature_level_diff = []

            # 新增功能点
            for fid, pm_feature in pm_feature_index.items():
                if fid not in ai_feature_index:
                    feature_level_diff.append({
                        "operation": "added",
                        "feature_id": fid,
                        "feature_name": pm_feature.get("功能点"),
                        "timestamp": datetime.now().isoformat()
                    })

            # 删除功能点
            for fid, ai_feature in ai_feature_index.items():
                if fid not in pm_feature_index:
                    feature_level_diff.append({
                        "operation": "deleted",
                        "feature_id": fid,
                        "feature_name": ai_feature.get("功能点"),
                        "timestamp": datetime.now().isoformat()
                    })

            # 修改功能点（描述变化）
            for fid in (set(pm_feature_index.keys()) & set(ai_feature_index.keys())):
                pm_feature = pm_feature_index[fid]
                ai_feature = ai_feature_index[fid]

                pm_desc = pm_feature.get("业务描述") or ""
                ai_desc = ai_feature.get("业务描述") or ""

                if pm_desc != ai_desc:
                    feature_level_diff.append({
                        "operation": "modified",
                        "feature_id": fid,
                        "feature_name": pm_feature.get("功能点"),
                        "field": "业务描述",
                        "ai_value": ai_desc,
                        "pm_value": pm_desc,
                        "timestamp": datetime.now().isoformat()
                    })

            # 按系统维度组织 diff
            if system_name not in pm_correction_diff:
                pm_correction_diff[system_name] = {
                    "system_level": [],
                    "feature_level": [],
                    "estimation_level": None  # Phase 2 填充
                }

            pm_correction_diff[system_name]["feature_level"] = feature_level_diff

        # 全局系统级 diff
        if system_level_diff:
            for system_name in pm_correction_diff:
                pm_correction_diff[system_name]["system_level"] = system_level_diff

        logger.info(f"[DiffService] Phase 1 diff 计算完成，任务 {task_id}，系统数: {len(pm_correction_diff)}")
        return pm_correction_diff

    @staticmethod
    def compute_phase2_diff(
        task_id: str,
        ai_original_output: Dict[str, Any],
        expert_final_means: Dict[str, float],
        pm_correction_diff: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        计算 Phase 2 diff（评估完成后）

        Args:
            task_id: 任务 ID
            ai_original_output: AI 原始输出快照
            expert_final_means: 专家评估终值（feature_id -> mean_value）
            pm_correction_diff: Phase 1 已计算的 diff

        Returns:
            Dict: 更新后的 pm_correction_diff（包含 estimation_level）
        """
        ai_work_estimation = ai_original_output.get("work_estimation") or {}
        estimation_details = ai_work_estimation.get("estimation_details") or {}

        # 按系统组织估值级 diff
        for system_name, system_diff in pm_correction_diff.items():
            estimation_level_diff = []

            for feature_id, expert_mean in expert_final_means.items():
                ai_detail = estimation_details.get(feature_id)
                if not ai_detail:
                    continue

                ai_expected = ai_detail.get("expected")
                if ai_expected is None:
                    continue

                # 计算偏差
                deviation = abs(expert_mean - ai_expected)
                deviation_pct = (deviation / ai_expected * 100) if ai_expected > 0 else 0

                estimation_level_diff.append({
                    "feature_id": feature_id,
                    "ai_expected": round(ai_expected, 2),
                    "expert_final": round(expert_mean, 2),
                    "deviation": round(deviation, 2),
                    "deviation_pct": round(deviation_pct, 2),
                    "timestamp": datetime.now().isoformat()
                })

            system_diff["estimation_level"] = estimation_level_diff

        logger.info(f"[DiffService] Phase 2 diff 计算完成，任务 {task_id}")
        return pm_correction_diff

    @staticmethod
    def is_diff_empty(pm_correction_diff: Dict[str, Any]) -> bool:
        """
        判断 diff 是否为空（PM 无修改）

        Args:
            pm_correction_diff: PM 修正 diff

        Returns:
            bool: True 表示无修改
        """
        if not pm_correction_diff:
            return True

        for system_name, system_diff in pm_correction_diff.items():
            if system_diff.get("system_level"):
                return False
            if system_diff.get("feature_level"):
                return False
            if system_diff.get("estimation_level"):
                return False

        return True


    @staticmethod
    def update_correction_history(
        system_profile_service,
        system_id: str,
        pm_correction_diff: Dict[str, Any]
    ) -> None:
        """
        将 PM 修正 diff 聚合更新到系统画像的 ai_correction_history

        Args:
            system_profile_service: SystemProfileService 实例
            system_id: 系统 ID
            pm_correction_diff: PM 修正 diff（按系统维度）
        """
        if not pm_correction_diff or DiffService.is_diff_empty(pm_correction_diff):
            logger.info(f"[DiffService] 系统 {system_id} 无修正，跳过 correction_history 更新")
            return

        # 读取系统画像
        profile = system_profile_service.get_profile(system_id)
        if not profile:
            logger.warning(f"[DiffService] 系统 {system_id} 画像不存在，跳过更新")
            return

        # 获取或初始化 ai_correction_history
        correction_history = profile.get("ai_correction_history") or {
            "total_corrections": 0,
            "system_level_corrections": 0,
            "feature_level_corrections": 0,
            "estimation_level_corrections": 0,
            "average_deviation_pct": 0.0,
            "notable_patterns": [],
            "last_updated": None
        }

        # 统计修正次数
        system_diff = pm_correction_diff.get(system_id) or {}
        system_level_count = len(system_diff.get("system_level") or [])
        feature_level_count = len(system_diff.get("feature_level") or [])
        estimation_level = system_diff.get("estimation_level") or []
        estimation_level_count = len(estimation_level)

        correction_history["total_corrections"] += 1
        correction_history["system_level_corrections"] += system_level_count
        correction_history["feature_level_corrections"] += feature_level_count
        correction_history["estimation_level_corrections"] += estimation_level_count

        # 计算平均偏差
        if estimation_level:
            deviations = [item["deviation_pct"] for item in estimation_level if "deviation_pct" in item]
            if deviations:
                avg_deviation = sum(deviations) / len(deviations)
                # 更新移动平均
                old_avg = correction_history.get("average_deviation_pct") or 0.0
                old_count = correction_history.get("estimation_level_corrections", 1) - estimation_level_count
                if old_count > 0:
                    correction_history["average_deviation_pct"] = round(
                        (old_avg * old_count + avg_deviation * estimation_level_count) /
                        (old_count + estimation_level_count),
                        2
                    )
                else:
                    correction_history["average_deviation_pct"] = round(avg_deviation, 2)

        correction_history["last_updated"] = datetime.now().isoformat()

        # 更新画像
        profile["ai_correction_history"] = correction_history
        system_profile_service.update_profile(system_id, profile)

        logger.info(
            f"[DiffService] 系统 {system_id} correction_history 已更新，"
            f"总修正次数: {correction_history['total_corrections']}"
        )


def get_diff_service() -> DiffService:
    """获取 DiffService 单例"""
    return DiffService()
