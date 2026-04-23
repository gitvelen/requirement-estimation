"""
API路由
定义所有RESTful API接口
"""
import os
import re
import uuid
import json
import logging
import socket
import threading
import ipaddress
from contextlib import contextmanager
try:
    import fcntl
    FCNTL_AVAILABLE = True
except ImportError:
    FCNTL_AVAILABLE = False
from urllib.parse import urlparse
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import statistics
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Request, Depends, Query
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from backend.utils.docx_parser import docx_parser
from backend.agent.agent_orchestrator import get_agent_orchestrator
from backend.config.config import settings
from backend.service.knowledge_service import get_knowledge_service
from backend.service.memory_service import get_memory_service
from backend.service import user_service
from backend.service.system_profile_service import get_system_profile_service
from backend.utils.pdf_report import write_report_pdf
from backend.utils.cosmic_analyzer import cosmic_analyzer
from backend.api.auth import get_current_user, require_roles, decode_access_token
from backend.api import system_routes
from backend.service.ai_effect_service import create_snapshots
from backend.api.notification_routes import create_notification
from backend.api.error_utils import build_error_response
from backend.utils.time_utils import current_time, parse_iso_datetime

# 创建logger实例
logger = logging.getLogger(__name__)

# 创建线程池用于异步任务处理
executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="task_worker")

# 尝试导入 python-magic（用于文件类型检测）
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
    logger.warning("python-magic 未安装，将跳过MIME类型检测")

# 创建路由器
router = APIRouter(prefix=settings.API_PREFIX, tags=["需求评估"])

# 全局任务存储（生产环境应使用Redis或数据库）
task_storage = {}
task_storage_lock = threading.RLock()
TASK_STORE_PATH = os.path.join(settings.REPORT_DIR, "task_storage.json")
TASK_STORE_LOCK_PATH = f"{TASK_STORE_PATH}.lock"


@contextmanager
def _task_store_lock():
    """跨进程文件锁，保证任务存储一致性"""
    if FCNTL_AVAILABLE:
        os.makedirs(os.path.dirname(TASK_STORE_LOCK_PATH), exist_ok=True)
        with open(TASK_STORE_LOCK_PATH, "a") as lock_file:
            fcntl.flock(lock_file, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file, fcntl.LOCK_UN)
    else:
        with task_storage_lock:
            yield


def _load_task_storage_unlocked() -> Dict[str, Any]:
    """读取任务存储（不加锁）"""
    if not os.path.exists(TASK_STORE_PATH):
        return {}
    try:
        with open(TASK_STORE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception as e:
        logger.warning(f"读取任务存储失败: {e}")
        return {}


def _save_task_storage_unlocked(data: Dict[str, Any]) -> None:
    """写入任务存储（不加锁）"""
    os.makedirs(os.path.dirname(TASK_STORE_PATH), exist_ok=True)
    tmp_path = f"{TASK_STORE_PATH}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, TASK_STORE_PATH)


@contextmanager
def _task_storage_context():
    """读取-写入的原子上下文"""
    with _task_store_lock():
        data = _load_task_storage_unlocked()
        yield data
        _save_task_storage_unlocked(data)


def _get_task(task_id: str) -> Dict[str, Any]:
    """获取单个任务"""
    with _task_store_lock():
        data = _load_task_storage_unlocked()
        task = data.get(task_id)
        if task:
            _ensure_task_schema(task)
        return task


def _cleanup_tasks(data: Dict[str, Any]) -> int:
    """清理过期任务"""
    retention_days = settings.TASK_RETENTION_DAYS
    if retention_days <= 0:
        return 0
    cutoff = datetime.now() - timedelta(days=retention_days)
    removed = 0
    for task_id, task in list(data.items()):
        status = task.get("status")
        created_at = task.get("created_at")
        if status not in ("completed", "failed"):
            continue
        if not created_at:
            continue
        try:
            created_time = datetime.fromisoformat(created_at)
        except Exception:
            continue
        if created_time < cutoff:
            del data[task_id]
            removed += 1
    return removed


def _ensure_task_schema(task: Dict[str, Any]) -> None:
    """补齐v2任务字段默认值（原地修改）"""
    if not task:
        return

    task.setdefault("name", task.get("requirement_name") or task.get("filename") or task.get("task_id"))
    task.setdefault("description", "")
    task.setdefault("creator_id", task.get("creator_id") or "unknown")
    task.setdefault("creator_name", task.get("creator_name") or "未知")

    task.setdefault("workflow_status", "draft")
    task.setdefault("current_round", 1)
    task.setdefault("max_rounds", DEFAULT_MAX_ROUNDS)
    task.setdefault("expert_assignments", [])
    task.setdefault("evaluations", {})
    task.setdefault("evaluation_drafts", {})
    task.setdefault("report_versions", [])
    task.setdefault("round_feature_ids", {})
    task.setdefault("deviations", {})
    task.setdefault("round_means", {})
    task.setdefault("high_deviation_features", {})
    task.setdefault("modification_traces", [])
    task.setdefault("ai_initial_features", [])
    task.setdefault("ai_initial_feature_count", int(task.get("ai_initial_feature_count") or 0))
    task.setdefault("ai_involved", bool(task.get("ai_involved") or task.get("ai_initial_feature_count") or task.get("ai_initial_features")))
    task.setdefault("ai_status", task.get("status"))
    task.setdefault("requirement_content", task.get("requirement_content") or "")
    task.setdefault("ai_system_analysis", task.get("ai_system_analysis"))
    task.setdefault("target_system_mode", "unlimited")
    task.setdefault("target_system_name", "")

    if "systems_data" in task and "systems" not in task:
        task["systems"] = list(task["systems_data"].keys())

    if task.get("confirmed"):
        task["workflow_status"] = "completed"
    elif task.get("status") == "completed" and task["workflow_status"] == "draft":
        # AI完成但未提交给管理员
        task["workflow_status"] = "draft"

    _freeze_task_if_needed(task)


def _ensure_feature_ids(task: Dict[str, Any]) -> bool:
    """为功能点补齐ID，返回是否发生变更"""
    systems_data = task.get("systems_data") or {}
    changed = False
    for system_name, features in systems_data.items():
        if not isinstance(features, list):
            continue
        for feature in features:
            if not isinstance(feature, dict):
                continue
            if "id" not in feature:
                feature["id"] = f"feat_{uuid.uuid4().hex}"
                changed = True
            feature.setdefault("系统", system_name)
    if changed:
        task["systems_data"] = systems_data
    return changed


def _ensure_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        parts = re.split(r"[,\n;/，、]+", value)
        return [item.strip() for item in parts if item.strip()]
    return [str(value).strip()]


def build_feature_rule_context(task: Dict[str, Any], feature: Dict[str, Any]) -> Dict[str, Any]:
    selected_rule = str((task or {}).get("estimation_rule") or "cosmic").strip().lower()
    if selected_rule in {"", "none", "skip", "skipped"}:
        return {
            "rule_id": "cosmic",
            "rule_name": "COSMIC",
            "status": "skipped",
            "summary_text": "当前任务未选择 COSMIC 规则，已跳过 COSMIC 上下文注入",
            "structured_payload": {},
            "failure_reason": "rule_not_selected",
        }

    if selected_rule != "cosmic":
        return {
            "rule_id": selected_rule,
            "rule_name": selected_rule.upper(),
            "status": "skipped",
            "summary_text": f"当前任务选择的是 {selected_rule.upper()}，本链路未注入 COSMIC 上下文",
            "structured_payload": {},
            "failure_reason": "rule_not_supported",
        }

    if not settings.COSMIC_ENABLED:
        return {
            "rule_id": "cosmic",
            "rule_name": "COSMIC",
            "status": "degraded",
            "summary_text": "COSMIC 功能当前未启用，未生成规则上下文",
            "structured_payload": {},
            "failure_reason": "cosmic_disabled",
        }

    cosmic_analysis = feature.get("cosmic_analysis") if isinstance(feature, dict) else None
    if not isinstance(cosmic_analysis, dict):
        feature_description = str(
            feature.get("业务描述")
            or feature.get("description")
            or feature.get("功能点")
            or feature.get("name")
            or ""
        ).strip()
        cosmic_analysis = cosmic_analyzer.analyze_feature(feature_description, feature)
        if isinstance(feature, dict):
            feature["cosmic_analysis"] = cosmic_analysis

    return cosmic_analyzer.build_rule_context_from_analysis(cosmic_analysis)


def _list_manager_responsible_system_names(current_user: Optional[Dict[str, Any]]) -> List[str]:
    result: List[str] = []
    try:
        systems = system_routes._read_systems()
    except Exception:
        systems = []

    for system in systems:
        if not isinstance(system, dict):
            continue
        system_name = str(system.get("name") or "").strip()
        if not system_name:
            continue
        ownership = system_routes.resolve_system_ownership(
            current_user,
            system_id=system.get("id"),
            system_name=system_name,
        )
        if ownership.get("allowed_draft_write") and system_name not in result:
            result.append(system_name)
    return result


def _normalize_target_system_selection(
    target_system_mode: Optional[str],
    target_system_name: Optional[str],
    current_user: Optional[Dict[str, Any]],
) -> Tuple[str, str]:
    normalized_mode = str(target_system_mode or "").strip().lower()
    normalized_name = str(target_system_name or "").strip()

    if normalized_mode not in {"specific", "unlimited"}:
        raise HTTPException(status_code=400, detail="待评估系统不能为空")

    if normalized_mode == "unlimited":
        return "unlimited", ""

    allowed_system_names = _list_manager_responsible_system_names(current_user)
    if normalized_name not in allowed_system_names:
        raise HTTPException(status_code=400, detail="待评估系统不在当前项目经理可选范围内")
    return "specific", normalized_name


def _target_system_display(task: Dict[str, Any]) -> str:
    mode = str(task.get("target_system_mode") or "unlimited").strip().lower()
    if mode == "specific":
        return str(task.get("target_system_name") or "").strip()
    return "不限"


def _is_single_system_locked(task: Optional[Dict[str, Any]]) -> bool:
    mode = str((task or {}).get("target_system_mode") or "unlimited").strip().lower()
    return mode == "specific"


def _ensure_system_scope_mutation_allowed(task: Optional[Dict[str, Any]]) -> None:
    if _is_single_system_locked(task):
        raise HTTPException(status_code=409, detail="具体系统任务的系统范围已锁定，不允许修改系统范围")


def _get_ai_estimate(feature: Dict[str, Any]) -> float:
    for key in ("aiEstimatedDays", "预估人天", "预估人天数", "AI预估人天", "AI预估"):
        if key in feature and feature[key] is not None:
            try:
                return float(feature[key])
            except (TypeError, ValueError):
                return 0.0
    return 0.0


def _to_float_or_none(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_estimation_detail(feature: Dict[str, Any]) -> Dict[str, Any]:
    optimistic = _to_float_or_none(feature.get("optimistic"))
    most_likely = _to_float_or_none(feature.get("most_likely"))
    pessimistic = _to_float_or_none(feature.get("pessimistic"))

    original_estimate = _to_float_or_none(feature.get("original_estimate"))
    if original_estimate is None or original_estimate <= 0:
        original_estimate = _get_ai_estimate(feature)
    if original_estimate <= 0:
        original_estimate = 1.0

    expected = _to_float_or_none(feature.get("expected"))
    if expected is None:
        if optimistic is not None and most_likely is not None and pessimistic is not None:
            expected = round((optimistic + 4 * most_likely + pessimistic) / 6, 2)
        else:
            expected = round(original_estimate, 2)
    else:
        expected = round(expected, 2)

    reasoning = str(feature.get("reasoning") or feature.get("AI分析理由") or "").strip()
    degraded = optimistic is None or most_likely is None or pessimistic is None

    return {
        "optimistic": optimistic,
        "most_likely": most_likely,
        "pessimistic": pessimistic,
        "expected": expected,
        "reasoning": reasoning,
        "original_estimate": round(float(original_estimate), 2),
        "degraded": degraded,
        "profile_context_used": bool(feature.get("profile_context_used")),
        "context_source": str(feature.get("context_source") or "none").strip() or "none",
    }


def _build_feature_response(feature: Dict[str, Any], my_value: Optional[float] = None) -> Dict[str, Any]:
    estimation = _extract_estimation_detail(feature)
    return {
        "id": feature.get("id"),
        "sequence": feature.get("序号", ""),
        "module": feature.get("功能模块", ""),
        "name": feature.get("功能点", ""),
        "description": feature.get("业务描述", ""),
        "inputs": _ensure_list(feature.get("输入") or feature.get("输入项") or feature.get("inputs")),
        "outputs": _ensure_list(feature.get("输出") or feature.get("输出项") or feature.get("outputs")),
        "dependencies": _ensure_list(feature.get("依赖项") or feature.get("依赖") or feature.get("dependencies")),
        "aiEstimatedDays": estimation["expected"],
        "optimistic": estimation["optimistic"],
        "mostLikely": estimation["most_likely"],
        "most_likely": estimation["most_likely"],
        "pessimistic": estimation["pessimistic"],
        "expected": estimation["expected"],
        "originalEstimate": estimation["original_estimate"],
        "reasoning": estimation["reasoning"],
        "estimationDegraded": estimation["degraded"],
        "profileContextUsed": estimation["profile_context_used"],
        "profile_context_used": estimation["profile_context_used"],
        "contextSource": estimation["context_source"],
        "context_source": estimation["context_source"],
        "remark": feature.get("备注") or feature.get("remark"),
        "myEvaluation": my_value
    }


def _get_round_key(round_no: int) -> str:
    return str(round_no)


def _get_round_feature_ids(task: Dict[str, Any], round_no: int) -> List[str]:
    round_key = _get_round_key(round_no)
    if task.get("round_feature_ids", {}).get(round_key):
        return list(task["round_feature_ids"][round_key])
    # 默认首轮包含全部功能点
    feature_ids = []
    for features in (task.get("systems_data") or {}).values():
        for feature in features or []:
            fid = feature.get("id")
            if fid:
                feature_ids.append(fid)
    task.setdefault("round_feature_ids", {})[round_key] = feature_ids
    return feature_ids


def _get_active_assignments(task: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [assignment for assignment in task.get("expert_assignments", []) if assignment.get("status") != "revoked"]


def _get_assignment_by_token(task: Dict[str, Any], token: str) -> Optional[Dict[str, Any]]:
    if not token:
        return None
    invalid_tokens = set()
    for assignment in task.get("expert_assignments", []):
        invalid_tokens.update(assignment.get("invalid_tokens") or [])
    if token in invalid_tokens:
        return None
    for assignment in task.get("expert_assignments", []):
        if assignment.get("status") == "revoked":
            continue
        if token in (assignment.get("invalid_tokens") or []):
            continue
        if assignment.get("invite_token") == token:
            return assignment
    return None


def _assignment_matches_user(assignment: Dict[str, Any], user: Dict[str, Any]) -> bool:
    expert_id = assignment.get("expert_id")
    if not expert_id or not user:
        return False
    candidates = {
        user.get("id"),
        user.get("username"),
        user.get("display_name")
    }
    return expert_id in candidates


def _resolve_user_for_assignment(users: List[Dict[str, Any]], identifier: str) -> Optional[Dict[str, Any]]:
    value = (identifier or "").strip()
    if not value:
        return None
    for user in users:
        if value == user.get("id") or value == user.get("username"):
            return user
    matches = [user for user in users if value == user.get("display_name")]
    if len(matches) == 1:
        return matches[0]
    return None


def _get_default_scope(user: Dict[str, Any]) -> str:
    roles = user.get("roles", [])
    if "admin" in roles:
        return "all"
    if "manager" in roles:
        return "created"
    if "expert" in roles:
        return "assigned"
    return "all"


def _compute_task_estimation_snapshot(task: Dict[str, Any]) -> Dict[str, Any]:
    systems_data = task.get("systems_data") or {}
    latest_round = None
    round_means = task.get("round_means") or {}
    for key in round_means.keys():
        try:
            round_no = int(key)
        except (TypeError, ValueError):
            continue
        if latest_round is None or round_no > latest_round:
            latest_round = round_no

    latest_means: Dict[str, Any] = {}
    if latest_round is not None:
        latest_means = round_means.get(str(latest_round)) or {}

    ai_total = 0.0
    final_total = 0.0
    ai_by_system = []
    final_by_system = []

    for system_name, features in systems_data.items():
        if not isinstance(features, list):
            continue
        ai_sum = 0.0
        final_sum = 0.0
        for feature in features:
            if not isinstance(feature, dict):
                continue
            ai_value = float(_get_ai_estimate(feature))
            ai_sum += ai_value
            feature_id = str(feature.get("id") or "").strip()
            final_value = ai_value
            if feature_id and feature_id in latest_means:
                try:
                    final_value = float(latest_means.get(feature_id) or 0.0)
                except (TypeError, ValueError):
                    final_value = ai_value
            final_sum += final_value

        ai_sum = round(ai_sum, 2)
        final_sum = round(final_sum, 2)
        ai_total += ai_sum
        final_total += final_sum

        owner_info = system_routes.resolve_system_owner(system_name=system_name)
        system_id = owner_info.get("system_id") or ""
        ai_by_system.append({"system_id": system_id, "system_name": system_name, "days": ai_sum})
        final_by_system.append({"system_id": system_id, "system_name": system_name, "days": final_sum})

    return {
        "ai_total": round(ai_total, 2),
        "final_total": round(final_total, 2),
        "ai_by_system": ai_by_system,
        "final_by_system": final_by_system,
    }


def _build_owner_snapshot(task: Dict[str, Any], final_by_system: List[Dict[str, Any]]) -> Dict[str, Any]:
    owners = []
    primary_owner = None
    primary_days = -1.0

    for item in final_by_system:
        system_name = str(item.get("system_name") or "").strip()
        final_days = float(item.get("days") or 0.0)
        if not system_name:
            continue

        owner_info = system_routes.resolve_system_owner(system_name=system_name)
        owner_entry = {
            "system_id": owner_info.get("system_id") or "",
            "system_name": system_name,
            "owner_id": owner_info.get("resolved_owner_id") or "",
            "owner_name": owner_info.get("owner_name") or "",
            "final_days": round(final_days, 2),
        }
        owners.append(owner_entry)

        if final_days > primary_days:
            primary_days = final_days
            primary_owner = owner_entry

    snapshot = {"owners": owners}
    if primary_owner:
        snapshot["primary_owner_id"] = primary_owner.get("owner_id") or ""
        snapshot["primary_owner_name"] = primary_owner.get("owner_name") or ""
    else:
        snapshot["primary_owner_id"] = ""
        snapshot["primary_owner_name"] = ""
    return snapshot


def _freeze_task_if_needed(task: Dict[str, Any]) -> None:
    if not isinstance(task, dict):
        return
    if task.get("workflow_status") != "completed":
        return
    if task.get("frozen_at"):
        return

    snapshot = _compute_task_estimation_snapshot(task)
    task["frozen_at"] = datetime.now().isoformat()
    task["ai_estimation_days_total"] = snapshot["ai_total"]
    task["final_estimation_days_total"] = snapshot["final_total"]
    task["ai_estimation_days_by_system"] = snapshot["ai_by_system"]
    task["final_estimation_days_by_system"] = snapshot["final_by_system"]
    task["owner_snapshot"] = _build_owner_snapshot(task, snapshot["final_by_system"])


def _ensure_manager_access(task: Dict[str, Any], user: Dict[str, Any]) -> None:
    roles = user.get("roles", [])
    if "admin" in roles:
        return
    if "manager" in roles:
        creator_id = task.get("creator_id")
        creator_name = task.get("creator_name")
        if creator_id == user.get("id"):
            return
        if creator_name and creator_name in {user.get("display_name"), user.get("username")}:
            return
    raise HTTPException(status_code=403, detail="无权访问该任务")


def _get_withdrawable_round(task: Dict[str, Any], assignment: Dict[str, Any]) -> Optional[int]:
    submissions = assignment.get("round_submissions", {})
    rounds: List[int] = []
    for key in submissions.keys():
        try:
            rounds.append(int(key))
        except (TypeError, ValueError):
            continue
    rounds.sort(reverse=True)
    if not rounds:
        return None
    report_rounds = {item.get("round") for item in task.get("report_versions", [])}
    for round_no in rounds:
        if round_no not in report_rounds:
            return round_no
    return None


def _rollback_round_state(task: Dict[str, Any], round_no: int) -> None:
    round_key = _get_round_key(round_no)
    task.get("deviations", {}).pop(round_key, None)
    task.get("round_means", {}).pop(round_key, None)
    task.get("high_deviation_features", {}).pop(round_key, None)

    round_feature_ids = task.get("round_feature_ids", {})
    remove_keys = []
    for key in list(round_feature_ids.keys()):
        try:
            key_round = int(key)
        except (TypeError, ValueError):
            continue
        if key_round > round_no:
            remove_keys.append(key)
    for key in remove_keys:
        round_feature_ids.pop(key, None)

    if task.get("current_round", round_no) > round_no:
        task["current_round"] = round_no

    if task.get("workflow_status") != "archived":
        task["workflow_status"] = "evaluating"
        task.pop("completed_at", None)


def _extract_invite_token(token: Optional[str], request: Optional[Request]) -> Optional[str]:
    if token:
        return token
    if request:
        return request.headers.get("X-Invite-Token") or request.headers.get("x-invite-token")
    return None


def _build_feature_index(task: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    features_by_id: Dict[str, Dict[str, Any]] = {}
    for features in (task.get("systems_data") or {}).values():
        for feature in features or []:
            fid = feature.get("id")
            if fid:
                features_by_id[fid] = feature
    return features_by_id


def _extract_ai_reasoning(feature: Dict[str, Any]) -> str:
    for key in ("reasoning", "ai_reasoning", "AI推理", "AI分析理由", "推理", "analysis"):
        value = feature.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _build_ai_initial_snapshot(systems_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    snapshots: List[Dict[str, Any]] = []
    for system_name, features in (systems_data or {}).items():
        if not isinstance(features, list):
            continue
        for index, feature in enumerate(features):
            if not isinstance(feature, dict):
                continue
            feature_copy = dict(feature)
            feature_id = str(feature_copy.get("id") or feature_copy.get("feature_id") or "").strip()
            if not feature_id:
                feature_id = f"feat_{uuid.uuid4().hex}"
                feature_copy["id"] = feature_id
            feature_copy.setdefault("系统", system_name)
            snapshots.append(
                {
                    "feature_id": feature_id,
                    "system_name": str(system_name),
                    "reasoning": _extract_ai_reasoning(feature_copy),
                    "feature": feature_copy,
                    "captured_at": datetime.now().isoformat(),
                    "sequence": index + 1,
                }
            )
    return snapshots


def _get_round_evaluations(task: Dict[str, Any], round_no: int) -> Dict[str, Dict[str, float]]:
    return task.get("evaluations", {}).get(_get_round_key(round_no), {})


def _record_report_version(task: Dict[str, Any], round_no: int, file_path: str) -> Dict[str, Any]:
    round_versions = [rv for rv in task.get("report_versions", []) if rv.get("round") == round_no]
    version = len(round_versions) + 1
    report = {
        "id": f"rep_{uuid.uuid4().hex[:8]}",
        "round": round_no,
        "version": version,
        "file_name": os.path.basename(file_path),
        "file_path": file_path,
        "generated_at": datetime.now().isoformat()
    }
    task.setdefault("report_versions", []).append(report)
    return report


def _generate_round_report(task: Dict[str, Any], round_no: int) -> Optional[str]:
    """生成简单PDF报告，返回路径"""
    if not task.get("systems_data"):
        return None

    round_feature_ids = _get_round_feature_ids(task, round_no)
    features_by_id = _build_feature_index(task)
    assignments = _get_active_assignments(task)
    evaluations_round = _get_round_evaluations(task, round_no)

    meta_lines = [
        f"任务ID: {task.get('task_id')}",
        f"任务名称: {task.get('name', '')}",
        f"评估轮次: {round_no}",
        f"生成时间: {datetime.now().isoformat()}",
        ""
    ]
    headers = ["系统", "序号", "功能模块", "功能点", "AI预估", "专家1", "专家2", "专家3", "均值", "偏离度%"]
    rows: List[List[str]] = []

    for fid in round_feature_ids:
        feature = features_by_id.get(fid, {})
        ai_value = _get_ai_estimate(feature)
        expert_values = []
        for assignment in assignments:
            expert_id = assignment.get("expert_id")
            expert_values.append(
                evaluations_round.get(expert_id, {}).get(fid)
            )
        valid_values = [v for v in expert_values if v is not None]
        mean_val = round(statistics.mean(valid_values), 2) if valid_values else 0.0
        deviation = round(abs(mean_val - ai_value) / ai_value * 100, 2) if ai_value else 0.0

        system_name = feature.get("系统", "")
        seq = feature.get("序号", "")
        module = feature.get("功能模块", "")
        name = feature.get("功能点", "")
        rows.append([
            system_name,
            seq,
            module,
            name,
            str(ai_value),
            str(expert_values[0] if len(expert_values) > 0 else ""),
            str(expert_values[1] if len(expert_values) > 1 else ""),
            str(expert_values[2] if len(expert_values) > 2 else ""),
            str(mean_val),
            str(deviation)
        ])

    os.makedirs(settings.REPORT_DIR, exist_ok=True)
    file_name = f"{task.get('task_id')}_round{round_no}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    file_path = os.path.join(settings.REPORT_DIR, file_name)
    write_report_pdf(meta_lines, headers, rows, file_path)
    return file_path


def _finalize_round(task: Dict[str, Any], round_no: int) -> None:
    """计算偏离度、生成报告并推进轮次或完成"""
    round_key = _get_round_key(round_no)
    round_feature_ids = _get_round_feature_ids(task, round_no)
    features_by_id = _build_feature_index(task)
    assignments = _get_active_assignments(task)
    evaluations_round = _get_round_evaluations(task, round_no)

    deviations: Dict[str, float] = {}
    means: Dict[str, float] = {}

    for fid in round_feature_ids:
        feature = features_by_id.get(fid, {})
        ai_value = _get_ai_estimate(feature)
        values = []
        for assignment in assignments:
            expert_id = assignment.get("expert_id")
            value = evaluations_round.get(expert_id, {}).get(fid)
            if value is not None:
                values.append(value)
        mean_val = round(statistics.mean(values), 2) if values else 0.0
        deviation = round(abs(mean_val - ai_value) / ai_value * 100, 2) if ai_value else 0.0
        means[fid] = mean_val
        deviations[fid] = deviation

    task.setdefault("round_means", {})[round_key] = means
    task.setdefault("deviations", {})[round_key] = deviations

    high_deviation_ids = [fid for fid, dev in deviations.items() if dev > DEVIATION_THRESHOLD]
    task.setdefault("high_deviation_features", {})[round_key] = high_deviation_ids

    # 【v2.4】如果是最后一轮且已有 Phase 1 diff，计算 Phase 2 diff 并更新 correction_history
    max_rounds = task.get("max_rounds", DEFAULT_MAX_ROUNDS)
    if round_no >= max_rounds and task.get("pm_correction_diff"):
        from backend.service.diff_service import get_diff_service
        from backend.service.system_profile_service import get_system_profile_service
        diff_service = get_diff_service()

        ai_original_output = task.get("ai_original_output") or {}
        pm_correction_diff = task.get("pm_correction_diff") or {}

        # 计算 Phase 2 diff（估值级）
        updated_diff = diff_service.compute_phase2_diff(
            task_id=task.get("task_id"),
            ai_original_output=ai_original_output,
            expert_final_means=means,
            pm_correction_diff=pm_correction_diff
        )
        task["pm_correction_diff"] = updated_diff
        logger.info(f"[任务 {task.get('task_id')}] Phase 2 diff 已计算")

        # 更新系统画像的 ai_correction_history
        try:
            system_profile_service = get_system_profile_service()
            systems = task.get("systems") or []
            for system_name in systems:
                if system_name in updated_diff:
                    diff_service.update_correction_history(
                        system_profile_service=system_profile_service,
                        system_id=system_name,
                        pm_correction_diff={system_name: updated_diff[system_name]}
                    )
        except Exception as e:
            logger.warning(f"[任务 {task.get('task_id')}] 更新 correction_history 失败: {e}")

    report_path = _generate_round_report(task, round_no)
    if report_path:
        _record_report_version(task, round_no, report_path)
        create_notification(
            title="评估报告已生成",
            content=f"任务【{task.get('name', task.get('task_id'))}】第{round_no}轮报告已生成。",
            notify_type="report_generated",
            roles=["admin"]
        )
        create_notification(
            title="评估报告已生成",
            content=f"任务【{task.get('name', task.get('task_id'))}】第{round_no}轮报告已生成。",
            notify_type="report_generated",
            user_ids=[item for item in [task.get("creator_id"), task.get("creator_name")] if item]
        )

    try:
        create_snapshots(task, round_no)
    except Exception as e:
        logger.warning(f"生成AI效果快照失败: {e}")

    if high_deviation_ids and round_no < task.get("max_rounds", DEFAULT_MAX_ROUNDS):
        task["current_round"] = round_no + 1
        task.setdefault("round_feature_ids", {})[_get_round_key(round_no + 1)] = high_deviation_ids
        task["workflow_status"] = "evaluating"
        for assignment in task.get("expert_assignments", []):
            if assignment.get("status") != "revoked":
                assignment["status"] = "invited"
        for assignment in task.get("expert_assignments", []):
            if assignment.get("status") == "revoked":
                continue
            create_notification(
                title="进入下一轮评估",
                content=f"任务【{task.get('name', task.get('task_id'))}】进入第{round_no + 1}轮评估，高偏离功能点{len(high_deviation_ids)}个。",
                notify_type="next_round",
                user_ids=[item for item in [assignment.get("expert_id"), assignment.get("expert_name")] if item]
            )
    else:
        task["workflow_status"] = "completed"
        task["completed_at"] = datetime.now().isoformat()
        _freeze_task_if_needed(task)


def _safe_log_task_event():
    """记录任务创建事件（失败不影响主流程）"""
    try:
        knowledge_service = get_knowledge_service()
        knowledge_service.log_task_event()
    except Exception as e:
        logger.warning(f"记录任务事件失败: {e}")


def _safe_log_modification_event():
    """记录修改事件（失败不影响主流程）"""
    try:
        knowledge_service = get_knowledge_service()
        knowledge_service.log_modification_event()
    except Exception as e:
        logger.warning(f"记录修改事件失败: {e}")


def _sanitize_filename(filename: str, default_name: str = "upload.docx") -> str:
    """将上传文件名清洗为安全的本地文件名（仅保留安全字符与白名单后缀）"""
    if not filename:
        return default_name

    cleaned = os.path.basename(filename.replace("\\", "/")).strip().replace("\x00", "")
    name, ext = os.path.splitext(cleaned)
    allowed_exts = {".docx", ".doc", ".xls"}
    ext = ext.lower()
    if ext not in allowed_exts:
        ext = os.path.splitext(default_name)[1].lower() if default_name else ".docx"
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    if not name:
        name = "upload"
    return f"{name}{ext}"


def _is_internal_callback_url(callback_url: str) -> bool:
    """仅允许内网/本机地址，防止SSRF"""
    try:
        parsed = urlparse(callback_url)
        if parsed.scheme not in ("http", "https"):
            return False
        if not parsed.hostname:
            return False

        host = parsed.hostname
        try:
            ip = ipaddress.ip_address(host)
            return ip.is_private or ip.is_loopback or ip.is_link_local
        except ValueError:
            pass

        try:
            addrs = socket.getaddrinfo(host, None)
        except OSError:
            return False

        has_addr = False
        for family, _, _, _, sockaddr in addrs:
            if family == socket.AF_INET:
                addr = sockaddr[0]
            elif family == socket.AF_INET6:
                addr = sockaddr[0]
            else:
                continue
            has_addr = True
            ip = ipaddress.ip_address(addr)
            if not (ip.is_private or ip.is_loopback or ip.is_link_local):
                return False
        return has_addr
    except Exception:
        return False


class TaskStatusResponse(BaseModel):
    """任务状态响应模型"""
    task_id: str
    status: str  # pending, processing, completed, failed
    progress: int  # 0-100
    message: str
    report_path: str = None
    error: str = None


class AssignExpertsRequest(BaseModel):
    """分配专家请求"""
    expert_ids: List[str] = Field(..., alias="expertIds")
    expert_names: Optional[List[str]] = Field(None, alias="expertNames")

    model_config = {
        "populate_by_name": True
    }


class EvaluationDraftRequest(BaseModel):
    """保存评估草稿"""
    round: int
    evaluations: Dict[str, float]


class EvaluationSubmitRequest(BaseModel):
    """提交评估"""
    round: int
    evaluations: Dict[str, float]


DEVIATION_THRESHOLD = 20.0
DEFAULT_MAX_ROUNDS = 3


@router.post("/requirement/upload")
async def upload_requirement(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """
    上传需求文档并启动评估任务

    Args:
        file: 上传的.docx文件
        background_tasks: 后台任务

    Returns:
        Dict: 包含task_id的任务信息
    """
    try:
        logger.info(f"接收到文件上传请求: {file.filename}")

        # 验证文件名后缀
        if not file.filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")
        ext = os.path.splitext(file.filename.lower())[1]
        allowed_exts = {".docx", ".doc", ".xls"}
        if ext not in allowed_exts:
            raise HTTPException(status_code=400, detail="仅支持.docx/.doc/.xls格式文件")

        # 读取文件内容
        content = await file.read()

        # 验证文件大小
        if len(content) > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"文件过大，最大允许{settings.MAX_FILE_SIZE // (1024*1024)}MB"
            )

        # 验证文件内容类型（MIME type）
        if MAGIC_AVAILABLE:
            try:
                mime_type = magic.from_buffer(content, mime=True)
                allowed_mimes = {
                    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
                    ".doc": {"application/msword", "application/vnd.ms-word"},
                    ".xls": {"application/vnd.ms-excel"},
                }
                if mime_type not in (allowed_mimes.get(ext) or set()) and mime_type != "application/octet-stream":
                    raise HTTPException(
                        status_code=400,
                        detail=f"无效的文件类型: {mime_type}，仅支持.docx/.doc/.xls文件"
                    )
            except Exception as e:
                logger.warning(f"MIME类型检测失败: {e}，继续处理")
        else:
            logger.info("跳过MIME类型检测（python-magic未安装）")

        # 生成任务ID
        task_id = str(uuid.uuid4())

        # 保存文件
        upload_dir = settings.UPLOAD_DIR
        os.makedirs(upload_dir, exist_ok=True)
        safe_filename = _sanitize_filename(file.filename)
        file_path = os.path.join(upload_dir, f"{task_id}_{safe_filename}")

        with open(file_path, "wb") as buffer:
            buffer.write(content)

        logger.info(f"文件已保存: {file_path}")

        # 创建任务记录
        created_at = datetime.now().isoformat()
        task_record = {
            "task_id": task_id,
            "name": os.path.splitext(safe_filename)[0],
            "description": "",
            "creator_id": "unknown",
            "creator_name": "未知",
            "filename": safe_filename,
            "file_path": file_path,
            "status": "pending",
            "ai_status": "pending",
            "progress": 0,
            "message": "任务已创建，等待处理",
            "created_at": created_at,
            "report_path": None,
            "workflow_status": "draft",
            "current_round": 1,
            "max_rounds": DEFAULT_MAX_ROUNDS,
            "expert_assignments": [],
            "evaluations": {},
            "evaluation_drafts": {},
            "report_versions": [],
            "round_feature_ids": {},
            "deviations": {},
            "high_deviation_features": {}
        }
        with _task_storage_context() as data:
            data[task_id] = task_record

        # 记录任务事件
        _safe_log_task_event()

        # 启动后台处理任务
        if background_tasks:
            background_tasks.add_task(process_task, task_id, file_path)

        return {
            "code": 200,
            "message": "文件上传成功",
            "data": {
                "task_id": task_id,
                "filename": file.filename,
                "status": "pending"
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")


@router.post("/requirement/evaluate")
async def evaluate_requirement(
    request_id: str = Form(...),
    callback_url: str = Form(None),
    priority: int = Form(0),
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """
    DevOps系统调用的评估接口

    Args:
        request_id: 请求ID
        callback_url: 回调通知地址
        priority: 优先级
        file: 需求文档文件
        background_tasks: 后台任务

    Returns:
        Dict: 任务信息
    """
    try:
        logger.info(f"接收到DevOps评估请求: {request_id}")

        if callback_url and not _is_internal_callback_url(callback_url):
            raise HTTPException(status_code=400, detail="回调地址必须为内网或本机地址")

        # 验证文件名后缀
        if not file.filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")
        ext = os.path.splitext(file.filename.lower())[1]
        allowed_exts = {".docx", ".doc", ".xls"}
        if ext not in allowed_exts:
            raise HTTPException(status_code=400, detail="仅支持.docx/.doc/.xls格式文件")

        # 读取文件内容
        content = await file.read()

        # 验证文件大小
        if len(content) > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"文件过大，最大允许{settings.MAX_FILE_SIZE // (1024*1024)}MB"
            )

        # 验证文件内容类型（MIME type）
        if MAGIC_AVAILABLE:
            try:
                mime_type = magic.from_buffer(content, mime=True)
                allowed_mimes = {
                    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
                    ".doc": {"application/msword", "application/vnd.ms-word"},
                    ".xls": {"application/vnd.ms-excel"},
                }
                if mime_type not in (allowed_mimes.get(ext) or set()) and mime_type != "application/octet-stream":
                    raise HTTPException(
                        status_code=400,
                        detail=f"无效的文件类型: {mime_type}，仅支持.docx/.doc/.xls文件"
                    )
            except Exception as e:
                logger.warning(f"MIME类型检测失败: {e}，继续处理")
        else:
            logger.info("跳过MIME类型检测（python-magic未安装）")

        # 生成任务ID
        task_id = request_id or str(uuid.uuid4())

        # 保存文件
        upload_dir = settings.UPLOAD_DIR
        os.makedirs(upload_dir, exist_ok=True)
        safe_filename = _sanitize_filename(file.filename)
        file_path = os.path.join(upload_dir, f"{task_id}_{safe_filename}")

        with open(file_path, "wb") as buffer:
            buffer.write(content)

        # 创建任务记录
        created_at = datetime.now().isoformat()
        task_record = {
            "task_id": task_id,
            "name": os.path.splitext(safe_filename)[0],
            "description": "",
            "creator_id": "unknown",
            "creator_name": "未知",
            "filename": safe_filename,
            "file_path": file_path,
            "status": "pending",
            "ai_status": "pending",
            "progress": 0,
            "message": "任务已创建",
            "created_at": created_at,
            "callback_url": callback_url,
            "report_path": None,
            "workflow_status": "draft",
            "current_round": 1,
            "max_rounds": DEFAULT_MAX_ROUNDS,
            "expert_assignments": [],
            "evaluations": {},
            "evaluation_drafts": {},
            "report_versions": [],
            "round_feature_ids": {},
            "deviations": {},
            "high_deviation_features": {}
        }
        with _task_storage_context() as data:
            data[task_id] = task_record

        # 记录任务事件
        _safe_log_task_event()

        # 启动后台处理
        if background_tasks:
            background_tasks.add_task(process_task_with_callback, task_id, file_path, callback_url)

        return {
            "code": 200,
            "message": "评估任务已创建",
            "data": {
                "task_id": task_id,
                "status": "pending"
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建评估任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建评估任务失败: {str(e)}")


@router.get("/requirement/tasks")
async def get_all_tasks():
    """
    获取所有任务列表

    Returns:
        Dict: 所有任务列表
    """
    with _task_storage_context() as data:
        removed = _cleanup_tasks(data)
        tasks_list = list(data.values())
        for task in tasks_list:
            _ensure_task_schema(task)
    # 按创建时间倒序排列
    tasks_list.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    return {
        "code": 200,
        "data": tasks_list,
        "total": len(tasks_list)
    }


@router.get("/requirement/status/{task_id}")
async def get_task_status(task_id: str):
    """
    获取任务状态

    Args:
        task_id: 任务ID

    Returns:
        Dict: 任务状态信息
    """
    task = _get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    # 直接返回完整的任务信息，不使用TaskStatusResponse模型
    return {
        "code": 200,
        "data": {
            "task_id": task["task_id"],
            "status": task["status"],
            "progress": task["progress"],
            "message": task["message"],
            "report_path": task.get("report_path"),
            "error": task.get("error"),
            "filename": task.get("filename"),
            "created_at": task.get("created_at")
        }
    }


@router.get("/requirement/report/{task_id}")
async def download_report(task_id: str):
    """
    下载Excel报告

    Args:
        task_id: 任务ID

    Returns:
        FileResponse: Excel文件
    """
    task = _get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail="任务未完成")

    if not task.get("report_path"):
        raise HTTPException(status_code=404, detail="报告文件不存在")

    report_path = task["report_path"]

    # 防止路径遍历攻击
    real_report_dir = os.path.realpath(settings.REPORT_DIR)
    real_report_path = os.path.realpath(report_path)

    # 验证路径在允许的目录内
    if not real_report_path.startswith(real_report_dir):
        logger.error(f"路径遍历攻击检测: {report_path}")
        raise HTTPException(status_code=403, detail="非法访问")

    if not os.path.exists(real_report_path):
        raise HTTPException(status_code=404, detail="报告文件不存在")

    return FileResponse(
        path=real_report_path,
        filename=os.path.basename(real_report_path),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# 后台任务处理函数
def process_task_sync(task_id: str, file_path: str):
    """同步处理评估任务（在线程池中运行）"""
    try:
        # 更新任务状态
        with _task_storage_context() as data:
            task = data.get(task_id)
            if not task:
                logger.warning(f"任务 {task_id} 不存在，停止处理")
                return
            task["status"] = "processing"
            task["ai_status"] = "processing"
            task["progress"] = 10
            task["message"] = "正在解析文档..."
            task.pop("error", None)

        # 定义进度更新函数
        def update_progress(progress: int, message: str):
            """更新任务进度"""
            with _task_storage_context() as data:
                task = data.get(task_id)
                if task:
                    task["progress"] = progress
                    task["message"] = message
            logger.info(f"[任务 {task_id}] 进度: {progress}% - {message}")

        # 解析文档（支持 .docx/.doc/.xls）
        ext = os.path.splitext(str(file_path or ""))[1].lower()
        if ext == ".docx":
            requirement_data = docx_parser.parse(file_path)
        elif ext == ".doc":
            from backend.utils.old_format_parser import doc_bytes_to_text

            with open(file_path, "rb") as f:
                text = doc_bytes_to_text(f.read(), os.path.basename(file_path))
            requirement_data = {
                "requirement_name": "",
                "requirement_summary": "",
                "requirement_content": text,
                "basic_info": {},
                "all_paragraphs": [text] if text else [],
            }
        elif ext == ".xls":
            from backend.utils.old_format_parser import xls_bytes_to_text

            with open(file_path, "rb") as f:
                text = xls_bytes_to_text(f.read(), os.path.basename(file_path))
            requirement_data = {
                "requirement_name": "",
                "requirement_summary": "",
                "requirement_content": text,
                "basic_info": {},
                "all_paragraphs": [text] if text else [],
            }
        else:
            raise ValueError(f"不支持的文件类型: {ext}")

        def _is_placeholder_requirement_name(value: Any) -> bool:
            normalized = str(value or "").strip()
            return normalized in {"", "需求名称", "需求名", "name", "requirement_name"}

        # 优先保留文档里解析出的真实需求名称，仅在缺失/占位时回退到文件名
        task_snapshot = _get_task(task_id) or {}
        original_filename = task_snapshot.get("filename", "")
        parsed_requirement_name = str(requirement_data.get("requirement_name") or "").strip()
        if _is_placeholder_requirement_name(parsed_requirement_name):
            if original_filename:
                requirement_name = original_filename.rsplit(".", 1)[0] if "." in original_filename else original_filename
            else:
                basename = os.path.basename(file_path)
                requirement_name = basename.rsplit(".", 1)[0] if "." in basename else basename
        else:
            requirement_name = parsed_requirement_name

        requirement_data["requirement_name"] = requirement_name
        requirement_data["target_system_mode"] = str(task_snapshot.get("target_system_mode") or "unlimited").strip().lower() or "unlimited"
        requirement_data["target_system_name"] = str(task_snapshot.get("target_system_name") or "").strip()
        logger.info(f"本次评估使用的需求名称: {requirement_name}")

        update_progress(15, "文档解析完成")

        # 获取Agent编排器（支持知识库注入）
        orchestrator = get_agent_orchestrator()

        # 处理需求评估（传递进度回调）
        report_path, systems_data, ai_system_analysis, ai_original_output = orchestrator.process_with_retry(
            task_id=task_id,
            requirement_data=requirement_data,
            max_retry=settings.TASK_RETRY_TIMES,
            progress_callback=update_progress
        )

        # 【新增】保存systems_data到task_storage，用于人机协作修正
        with _task_storage_context() as data:
            task = data.get(task_id)
            if task:
                analysis_result_status = ""
                analysis_context_degraded = False
                if isinstance(ai_system_analysis, dict):
                    analysis_result_status = str(ai_system_analysis.get("result_status") or "").strip()
                    analysis_context_degraded = bool(ai_system_analysis.get("context_degraded"))
                task["systems_data"] = systems_data
                _ensure_feature_ids(task)
                if not task.get("ai_initial_features"):
                    ai_initial_features = _build_ai_initial_snapshot(task.get("systems_data") or {})
                    task["ai_initial_features"] = ai_initial_features
                    task["ai_initial_feature_count"] = len(ai_initial_features)
                    task["ai_involved"] = bool(ai_initial_features)
                task["modifications"] = []  # 初始化为空列表
                task["confirmed"] = False  # 初始状态为未确认
                task["requirement_name"] = requirement_name
                task["requirement_content"] = requirement_data.get("requirement_content", "")
                task["ai_system_analysis"] = ai_system_analysis
                # 【v2.4】保存 AI 原始输出快照
                task["ai_original_output"] = ai_original_output
                # 更新任务状态
                task["status"] = "completed"
                task["ai_status"] = "partial_success" if (analysis_result_status == "partial_success" or analysis_context_degraded) else "completed"
                task["progress"] = 100
                task["message"] = "评估完成（上下文已降级）" if task["ai_status"] == "partial_success" else "评估完成"
                task["report_path"] = report_path
                task["workflow_status"] = "draft"
                task["systems"] = list(systems_data.keys())
                task.pop("error", None)

        logger.info(f"任务 {task_id} 处理完成，系统数: {len(systems_data)}，功能点总数: {sum(len(v) for v in systems_data.values())}")

    except Exception as e:
        logger.error(f"任务 {task_id} 处理失败: {str(e)}")
        with _task_storage_context() as data:
            task = data.get(task_id)
            if task:
                task["status"] = "failed"
                task["ai_status"] = "failed"
                task["message"] = f"处理失败: {str(e)}"
                task["error"] = str(e)


async def process_task(task_id: str, file_path: str):
    """异步处理评估任务"""
    # 提交到线程池执行
    loop = None
    try:
        import asyncio
        loop = asyncio.get_event_loop()
    except RuntimeError:
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    await loop.run_in_executor(executor, process_task_sync, task_id, file_path)


async def process_task_with_callback(task_id: str, file_path: str, callback_url: str = None):
    """处理评估任务（带回调）"""
    # 先执行任务
    await process_task(task_id, file_path)

    # 如果有回调地址，发送回调通知
    if callback_url:
        if not _is_internal_callback_url(callback_url):
            logger.warning(f"回调地址不符合内网策略，已跳过: {callback_url}")
            return
        try:
            import httpx
            task = _get_task(task_id) or {}

            async with httpx.AsyncClient() as client:
                await client.post(
                    callback_url,
                    json={
                        "task_id": task_id,
                        "status": task["status"],
                        "report_path": task.get("report_path"),
                        "error": task.get("error")
                    },
                    timeout=httpx.Timeout(120.0, connect=10.0)  # 总超时120秒，连接超时10秒
                )
            logger.info(f"回调通知已发送: {callback_url}")

        except Exception as e:
            logger.warning(f"发送回调通知失败: {str(e)}")


# ==================== 人机协作修正API ====================

class FeatureUpdateRequest(BaseModel):
    """功能点更新请求"""
    system: str  # 系统名称
    operation: str  # add, update, delete
    feature_index: int = None  # 功能点索引（update/delete时需要）
    feature_data: dict = None  # 功能点数据（add/update时需要）
    confirm: bool = False
    actor_id: Optional[str] = None
    actor_role: Optional[str] = None


class ReevaluateRequest(BaseModel):
    force: bool = False


class SystemRenameRequest(BaseModel):
    """系统重命名请求"""
    new_name: str
    confirm: bool = False


class AddSystemRequest(BaseModel):
    """新增系统Tab请求（默认自动拆分）"""
    name: str
    type: str = "主系统"
    auto_breakdown: bool = True
    confirm: bool = False


class RebreakdownSystemRequest(BaseModel):
    """重新拆分系统请求（覆盖当前系统下全部功能点）"""
    system_type: Optional[str] = None


_ALLOWED_ACTOR_ROLES = {"admin", "manager", "expert"}
_REMARK_FIELDS = {"备注", "remark"}
_ESTIMATED_DAY_FIELDS = {"预估人天", "estimated_days", "estimatedDays"}
_NON_SUBSTANTIVE_FEATURE_FIELDS = {"序号"}
_CORE_FEATURE_FIELDS = {"功能点", "业务描述", "系统"}


def _pick_actor_role(roles: Any) -> Optional[str]:
    if not isinstance(roles, list):
        return None
    for role in roles:
        normalized = str(role or "").strip().lower()
        if normalized in _ALLOWED_ACTOR_ROLES:
            return normalized
    return None


def _extract_login_user(request: Request) -> Optional[Dict[str, Any]]:
    auth_header = str(request.headers.get("Authorization") or "").strip()
    if not auth_header.startswith("Bearer "):
        return None

    token = auth_header.split(" ", 1)[1].strip()
    if not token:
        return None

    try:
        payload = decode_access_token(token)
    except Exception:
        return None

    user_id = str(payload.get("user_id") or "").strip()
    if not user_id:
        return None

    users = user_service.list_users()
    user = next((item for item in users if str(item.get("id") or "") == user_id), None)
    if not user or not user.get("is_active"):
        return None
    return user


def _resolve_actor(request: Request, payload_actor_id: Optional[str], payload_actor_role: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    actor_id = str(payload_actor_id or "").strip()
    actor_role = str(payload_actor_role or "").strip().lower()

    if actor_role and actor_role not in _ALLOWED_ACTOR_ROLES:
        return None, None

    login_user = _extract_login_user(request)

    if not actor_id and login_user:
        actor_id = str(login_user.get("id") or "").strip()

    if not actor_role:
        user_for_role = None
        if login_user and actor_id and str(login_user.get("id") or "") == actor_id:
            user_for_role = login_user
        elif actor_id:
            users = user_service.list_users()
            user_for_role = next((item for item in users if str(item.get("id") or "") == actor_id), None)

        actor_role = _pick_actor_role((user_for_role or {}).get("roles"))

    if not actor_id or not actor_role:
        return None, None

    if actor_role not in _ALLOWED_ACTOR_ROLES:
        return None, None

    return actor_id, actor_role


def _new_modification_base(operation: str, system: str, actor_id: str, actor_role: str) -> Dict[str, Any]:
    return {
        "timestamp": datetime.now().isoformat(),
        "operation": operation,
        "system": system,
        "actor_id": actor_id,
        "actor_role": actor_role,
    }


def _is_manager(actor_role: str) -> bool:
    return str(actor_role or "").strip().lower() == "manager"


def _requires_confirm_for_feature_update(changes: List[Dict[str, Any]]) -> bool:
    if not changes:
        return False
    for item in changes:
        field = str(item.get("field") or "").strip()
        if field in _NON_SUBSTANTIVE_FEATURE_FIELDS:
            continue
        return True
    return False


def _classify_feature_adjustment(modification: Dict[str, Any]) -> str:
    operation = str(modification.get("operation") or "").strip()
    field = str(modification.get("field") or "").strip()

    if operation == "add":
        return "addition"
    if operation == "delete":
        return "deletion"
    if field == "功能点":
        return "naming_normalization"
    if field == "功能模块":
        return "module_mapping"
    if field in _ESTIMATED_DAY_FIELDS or field == "复杂度":
        return "complexity_adjustment"
    if field == "系统":
        return "ownership_adjustment"
    if field == "业务描述":
        return "rewrite"
    return "field_update"


def _build_function_point_adjustment_payload(
    *,
    task_id: str,
    system_name: str,
    modifications: List[Dict[str, Any]],
) -> Dict[str, Any]:
    normalized_modifications: List[Dict[str, Any]] = []
    adjustment_types: List[str] = []

    for item in modifications:
        if not isinstance(item, dict):
            continue
        adjustment_type = _classify_feature_adjustment(item)
        if adjustment_type not in adjustment_types:
            adjustment_types.append(adjustment_type)

        normalized_modifications.append(
            {
                "modification_id": item.get("id"),
                "adjustment_type": adjustment_type,
                "feature_id": item.get("feature_id"),
                "feature_name": item.get("feature_name"),
                "module": item.get("module"),
                "field": item.get("field"),
                "old_value": item.get("old_value")
                if item.get("old_value") is not None
                else ((item.get("deleted_feature") or {}).get("功能点") if isinstance(item.get("deleted_feature"), dict) else None),
                "new_value": item.get("new_value")
                if item.get("new_value") is not None
                else ((item.get("added_feature") or {}).get("功能点") if isinstance(item.get("added_feature"), dict) else None),
                "operation": item.get("operation"),
            }
        )

    return {
        "task_id": task_id,
        "system_name": system_name,
        "adjustment_types": adjustment_types,
        "modifications": normalized_modifications,
    }


def _record_function_point_adjustment_memory(
    *,
    task_id: str,
    system_name: str,
    actor_id: str,
    actor_role: str,
    modifications: List[Dict[str, Any]],
) -> Dict[str, Any]:
    payload = _build_function_point_adjustment_payload(
        task_id=task_id,
        system_name=system_name,
        modifications=modifications,
    )
    adjustment_types = payload.get("adjustment_types") or []
    if not adjustment_types:
        raise ValueError("missing_adjustment_types")

    resolved = system_routes.resolve_system_owner(system_name=system_name)
    system_id = str(resolved.get("system_id") or "").strip() or system_name
    summary = f"PM确认功能点调整：{'/'.join(adjustment_types)}"

    return get_memory_service().append_record(
        system_id=system_id,
        memory_type="function_point_adjustment",
        memory_subtype="task_feature_update",
        scene_id="task_feature_update",
        source_type="requirement_task",
        source_id=task_id,
        summary=summary,
        payload=payload,
        decision_policy="manual",
        confidence=1.0,
        actor=f"{actor_role}:{actor_id}",
    )


def _read_task_remark_lines(task: Dict[str, Any]) -> List[str]:
    raw = str(task.get("remark") or "")
    return [line.strip() for line in raw.splitlines() if str(line).strip()]


def _prepend_task_remark(task: Dict[str, Any], message: str) -> bool:
    text = str(message or "").strip()
    if not text:
        return False

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_line = f"{timestamp} {text}"
    lines = _read_task_remark_lines(task)
    task["remark"] = "\n".join([new_line, *lines])
    return True


def _build_ai_remark_summary(modifications: List[Dict[str, Any]]) -> str:
    total = len(modifications)
    add_count = sum(1 for item in modifications if str(item.get("operation") or "") == "add")
    update_count = sum(1 for item in modifications if str(item.get("operation") or "") == "update")
    delete_count = sum(1 for item in modifications if str(item.get("operation") or "") == "delete")

    systems: List[str] = []
    for item in modifications:
        name = str(item.get("system") or "").strip()
        if name and name not in systems:
            systems.append(name)

    systems_text = "、".join(systems[:3]) if systems else "-"
    summary = (
        f"AI重评估：本次修改共{total}项，新增{add_count}项、调整{update_count}项、删除{delete_count}项，"
        f"涉及系统：{systems_text}。"
    )
    return summary[:500]


def _apply_ai_remark(task: Dict[str, Any], source_modifications: List[Dict[str, Any]]) -> bool:
    if not source_modifications:
        return False

    modifications = task.get("modifications") or []
    if not modifications:
        return False

    latest_mod_id = str(modifications[-1].get("id") or "").strip()
    if not latest_mod_id:
        return False

    if str(task.get("last_remark_mod_id") or "") == latest_mod_id:
        return False

    remark_text = _build_ai_remark_summary(source_modifications)
    systems_data = task.get("systems_data") or {}

    touched_feature_ids = {
        str(item.get("feature_id") or "").strip()
        for item in source_modifications
        if str(item.get("feature_id") or "").strip()
    }

    if touched_feature_ids:
        for _, features in systems_data.items():
            if not isinstance(features, list):
                continue
            for feature in features:
                if not isinstance(feature, dict):
                    continue
                feature_id = str(feature.get("id") or "").strip()
                if feature_id and feature_id in touched_feature_ids:
                    feature["备注"] = remark_text

    _prepend_task_remark(task, remark_text)
    task["last_remark_mod_id"] = latest_mod_id
    task["last_ai_remark"] = remark_text
    task["last_ai_remark_at"] = datetime.now().isoformat()
    return True


def _find_active_reevaluate_job(task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    jobs = task.get("reevaluate_jobs") if isinstance(task.get("reevaluate_jobs"), list) else []
    for job in reversed(jobs):
        status = str(job.get("status") or "")
        if status in {"pending", "running"}:
            return job
    return None


def _update_reevaluate_job_status(task_id: str, job_id: str, status: str, *, error: Optional[str] = None) -> None:
    with _task_storage_context() as data:
        task = data.get(task_id)
        if not task:
            return
        jobs = task.get("reevaluate_jobs") if isinstance(task.get("reevaluate_jobs"), list) else []
        for job in jobs:
            if str(job.get("job_id") or "") != job_id:
                continue
            job["status"] = status
            if status == "running":
                job["started_at"] = datetime.now().isoformat()
            if status in {"completed", "failed"}:
                job["completed_at"] = datetime.now().isoformat()
            if error:
                job["error"] = error
            break


def _run_reevaluate_job_sync(task_id: str, job_id: str) -> None:
    _update_reevaluate_job_status(task_id, job_id, "running")

    try:
        with _task_storage_context() as data:
            task = data.get(task_id)
            if not task:
                raise ValueError("task_not_found")

            _ensure_task_schema(task)
            if settings.V21_AI_REMARK_ENABLED:
                _apply_ai_remark(task, task.get("modifications") or [])

        _update_reevaluate_job_status(task_id, job_id, "completed")
    except Exception as exc:
        logger.error(f"重评估任务失败 task_id={task_id}, job_id={job_id}: {exc}")
        _update_reevaluate_job_status(task_id, job_id, "failed", error=str(exc))


@router.get("/requirement/result/{task_id}")
async def get_evaluation_result(task_id: str):
    """
    获取AI评估结果（包含systems_data）

    Args:
        task_id: 任务ID

    Returns:
        Dict: 评估结果数据
    """
    task = _get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    _ensure_task_schema(task)

    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"任务未完成，当前状态: {task['status']}")

    # 如果没有systems_data，尝试向后兼容（从Excel解析）
    systems_data = task.get("systems_data")
    if systems_data is None:
        raise HTTPException(status_code=400, detail="该任务没有可编辑的评估数据（可能是旧版本任务）")

    confirmed = task.get("workflow_status") != "draft"
    return {
        "code": 200,
        "data": {
            "task_id": task_id,
            "systems_data": systems_data,
            "ai_system_analysis": task.get("ai_system_analysis"),
            "modifications": task.get("modifications", []),
            "confirmed": confirmed,
            "workflow_status": task.get("workflow_status"),
            "target_system_mode": task.get("target_system_mode"),
            "target_system_name": task.get("target_system_name"),
            "target_system_display": _target_system_display(task),
        }
    }


@router.put("/requirement/features/{task_id}")
async def update_features(task_id: str, request: FeatureUpdateRequest, http_request: Request):
    """
    批量更新功能点

    支持操作：
    - add: 添加新功能点
    - update: 修改现有功能点
    - delete: 删除功能点

    Args:
        task_id: 任务ID
        request: 更新请求

    Returns:
        Dict: 更新结果
    """
    try:
        with _task_storage_context() as data:
            task = data.get(task_id)
            if not task:
                raise HTTPException(status_code=404, detail="任务不存在")

            if task["status"] != "completed":
                raise HTTPException(status_code=400, detail="只能修改已完成的任务")

            if task.get("confirmed", False):
                raise HTTPException(status_code=400, detail="该任务已确认，不能修改")

            systems_data = task.get("systems_data", {})
            modifications = task.get("modifications", [])

            if request.system not in systems_data:
                raise HTTPException(status_code=400, detail=f"系统 '{request.system}' 不存在")

            actor_id, actor_role = _resolve_actor(http_request, request.actor_id, request.actor_role)
            if not actor_id or not actor_role:
                return build_error_response(
                    request=http_request,
                    status_code=400,
                    error_code="missing_actor",
                    message="缺少操作人信息",
                )

            base_mod = _new_modification_base(
                operation=request.operation,
                system=request.system,
                actor_id=actor_id,
                actor_role=actor_role,
            )
            last_mod_id = None
            new_modifications: List[Dict[str, Any]] = []

            if request.operation == "update":
                # 修改功能点
                if request.feature_index is None:
                    raise HTTPException(status_code=400, detail="update操作需要feature_index")

                features = systems_data[request.system]
                if request.feature_index < 0 or request.feature_index >= len(features):
                    raise HTTPException(status_code=400, detail="feature_index超出范围")

                old_feature = features[request.feature_index]
                if request.feature_data is None:
                    raise HTTPException(status_code=400, detail="update操作需要feature_data")

                # 记录修改
                changes = []
                for key, new_value in request.feature_data.items():
                    normalized_key = str(key or "").strip()
                    if normalized_key in _REMARK_FIELDS:
                        continue
                    old_value = old_feature.get(key)
                    if old_value != new_value:
                        changes.append({
                            "field": normalized_key,
                            "raw_field": key,
                            "old_value": old_value,
                            "new_value": new_value
                        })

                if _is_manager(actor_role):
                    estimated_day_change = next(
                        (item for item in changes if str(item.get("field") or "").strip() in _ESTIMATED_DAY_FIELDS),
                        None,
                    )
                    if estimated_day_change:
                        return build_error_response(
                            request=http_request,
                            status_code=403,
                            error_code="AUTH_001",
                            message="权限不足",
                        )

                if _requires_confirm_for_feature_update(changes) and not request.confirm:
                    raise HTTPException(status_code=400, detail="实质性修改需要确认")

                for change in changes:
                    old_feature[change["raw_field"]] = change["new_value"]

                if changes:
                    for change in changes:
                        mod = {
                            "id": f"mod_{uuid.uuid4().hex[:8]}",
                            **base_mod,
                            "feature_name": old_feature.get("功能点"),
                            "module": old_feature.get("功能模块"),
                            "feature_index": request.feature_index,
                            "feature_id": old_feature.get("id"),
                            "field": change["field"],
                            "old_value": change["old_value"],
                            "new_value": change["new_value"],
                        }
                        modifications.append(mod)
                        new_modifications.append(mod)
                        last_mod_id = mod["id"]

                logger.info(f"[任务 {task_id}] 更新功能点: 系统={request.system}, 索引={request.feature_index}")

            elif request.operation == "delete":
                # 删除功能点
                if request.feature_index is None:
                    raise HTTPException(status_code=400, detail="delete操作需要feature_index")
                if not request.confirm:
                    raise HTTPException(status_code=400, detail="实质性修改需要确认")

                features = systems_data[request.system]
                if request.feature_index < 0 or request.feature_index >= len(features):
                    raise HTTPException(status_code=400, detail="feature_index超出范围")

                deleted_feature = features.pop(request.feature_index)
                mod = {
                    "id": f"mod_{uuid.uuid4().hex[:8]}",
                    **base_mod,
                    "deleted_feature": deleted_feature,
                    "feature_name": deleted_feature.get("功能点") if isinstance(deleted_feature, dict) else None,
                    "module": deleted_feature.get("功能模块") if isinstance(deleted_feature, dict) else None,
                    "feature_id": deleted_feature.get("id") if isinstance(deleted_feature, dict) else None,
                    "feature_index": request.feature_index
                }
                modifications.append(mod)
                new_modifications.append(mod)
                last_mod_id = mod["id"]

                logger.info(f"[任务 {task_id}] 删除功能点: 系统={request.system}, 索引={request.feature_index}")

            elif request.operation == "add":
                # 添加新功能点
                if request.feature_data is None:
                    raise HTTPException(status_code=400, detail="add操作需要feature_data")
                if not request.confirm:
                    raise HTTPException(status_code=400, detail="实质性修改需要确认")

                features = systems_data[request.system]
                new_feature = dict(request.feature_data)

                # 设置默认值
                if "序号" not in new_feature:
                    new_feature["序号"] = f"{len(features)+1}.1"
                if _is_manager(actor_role):
                    new_feature["预估人天"] = None
                elif "预估人天" not in new_feature:
                    new_feature["预估人天"] = 2.5
                if "复杂度" not in new_feature:
                    new_feature["复杂度"] = "中"
                if "id" not in new_feature:
                    new_feature["id"] = f"feat_{uuid.uuid4().hex}"

                features.append(new_feature)
                mod = {
                    "id": f"mod_{uuid.uuid4().hex[:8]}",
                    **base_mod,
                    "added_feature": new_feature,
                    "feature_name": new_feature.get("功能点"),
                    "module": new_feature.get("功能模块"),
                    "feature_id": new_feature.get("id")
                }
                modifications.append(mod)
                new_modifications.append(mod)
                last_mod_id = mod["id"]

                logger.info(f"[任务 {task_id}] 添加功能点: 系统={request.system}")

            else:
                raise HTTPException(status_code=400, detail=f"不支持的操作: {request.operation}")

            # 保存修改记录
            task["modifications"] = modifications
            if last_mod_id and _is_manager(actor_role):
                _prepend_task_remark(task, f"PM：保存功能点修改（系统：{request.system}，操作：{request.operation}）")

            # 持久化到JSON（实现数据闭环）
            _save_modifications_to_json(task_id, modifications)

        # 记录修改事件
        _safe_log_modification_event()

        result_status = "success"
        memory_error = None
        if settings.ENABLE_V27_RUNTIME and new_modifications:
            try:
                _record_function_point_adjustment_memory(
                    task_id=task_id,
                    system_name=request.system,
                    actor_id=actor_id,
                    actor_role=actor_role,
                    modifications=new_modifications,
                )
            except Exception as exc:
                result_status = "partial_success"
                memory_error = str(exc)

        return {
            "code": 200,
            "message": "更新成功" if result_status == "success" else "更新成功，但 Memory 写入失败",
            "result_status": result_status,
            "data": {
                "modification_id": last_mod_id,
                "updated_systems_data": systems_data,
                "actor_id": actor_id,
                "actor_role": actor_role,
                "memory_error": memory_error,
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新功能点失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新功能点失败: {str(e)}")


@router.delete("/requirement/systems/{task_id}/{system_name}")
async def delete_system(task_id: str, system_name: str, confirm: bool = Query(False)):
    """删除系统Tab"""
    try:
        with _task_storage_context() as data:
            task = data.get(task_id)
            if not task:
                raise HTTPException(status_code=404, detail="任务不存在")

            if task["status"] != "completed":
                raise HTTPException(status_code=400, detail="只能修改已完成的任务")

            if task.get("confirmed", False):
                raise HTTPException(status_code=400, detail="该任务已确认，不能修改")
            if not confirm:
                raise HTTPException(status_code=400, detail="实质性修改需要确认")
            _ensure_system_scope_mutation_allowed(task)

            systems_data = task.get("systems_data", {})
            modifications = task.get("modifications", [])

            if system_name not in systems_data:
                raise HTTPException(status_code=400, detail=f"系统 '{system_name}' 不存在")

            deleted_features = systems_data.pop(system_name)
            task["systems_data"] = systems_data
            if "systems" in task:
                task["systems"] = [name for name in task["systems"] if name != system_name]

            # 同步系统校准卡片（只维护 selected_systems，避免前端展示过期系统）
            analysis = task.get("ai_system_analysis") or {}
            if isinstance(analysis, dict) and isinstance(analysis.get("selected_systems"), list):
                analysis["selected_systems"] = [s for s in analysis["selected_systems"] if s.get("name") != system_name]
                analysis["updated_at"] = datetime.now().isoformat()
                task["ai_system_analysis"] = analysis

            mod = {
                "id": f"mod_{uuid.uuid4().hex[:8]}",
                "timestamp": datetime.now().isoformat(),
                "operation": "delete_system",
                "system": system_name,
                "deleted_features": deleted_features
            }
            modifications.append(mod)
            task["modifications"] = modifications
            _prepend_task_remark(task, f"PM：删除系统（{system_name}）")
            _save_modifications_to_json(task_id, modifications)

        _safe_log_modification_event()

        return {
            "code": 200,
            "message": "删除成功",
            "data": {
                "updated_systems_data": systems_data
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除系统失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除系统失败: {str(e)}")


@router.put("/requirement/systems/{task_id}/{system_name}/rename")
async def rename_system(task_id: str, system_name: str, request: SystemRenameRequest):
    """重命名系统Tab"""
    try:
        new_name = request.new_name.strip()
        if not new_name:
            raise HTTPException(status_code=400, detail="新系统名称不能为空")

        with _task_storage_context() as data:
            task = data.get(task_id)
            if not task:
                raise HTTPException(status_code=404, detail="任务不存在")

            if task["status"] != "completed":
                raise HTTPException(status_code=400, detail="只能修改已完成的任务")

            if task.get("confirmed", False):
                raise HTTPException(status_code=400, detail="该任务已确认，不能修改")
            if not request.confirm:
                raise HTTPException(status_code=400, detail="实质性修改需要确认")
            _ensure_system_scope_mutation_allowed(task)

            systems_data = task.get("systems_data", {})
            modifications = task.get("modifications", [])

            if system_name not in systems_data:
                raise HTTPException(status_code=400, detail=f"系统 '{system_name}' 不存在")
            if new_name in systems_data:
                raise HTTPException(status_code=400, detail="新系统名称已存在")

            systems_data[new_name] = systems_data.pop(system_name)
            for feature in systems_data[new_name]:
                if isinstance(feature, dict):
                    feature["系统"] = new_name

            task["systems_data"] = systems_data
            if "systems" in task:
                task["systems"] = [new_name if name == system_name else name for name in task["systems"]]

            # 同步系统校准卡片（只维护 selected_systems）
            analysis = task.get("ai_system_analysis") or {}
            if isinstance(analysis, dict) and isinstance(analysis.get("selected_systems"), list):
                for item in analysis["selected_systems"]:
                    if item.get("name") == system_name:
                        item["name"] = new_name
                        item.setdefault("reasons", [])
                        if isinstance(item["reasons"], list):
                            item["reasons"].append("系统Tab被项目经理重命名")
                        item["confidence"] = item.get("confidence") or "人工"
                analysis["updated_at"] = datetime.now().isoformat()
                task["ai_system_analysis"] = analysis

            mod = {
                "id": f"mod_{uuid.uuid4().hex[:8]}",
                "timestamp": datetime.now().isoformat(),
                "operation": "rename_system",
                "system": system_name,
                "field": "system_name",
                "old_value": system_name,
                "new_value": new_name
            }
            modifications.append(mod)
            task["modifications"] = modifications
            _prepend_task_remark(task, f"PM：重命名系统（{system_name} -> {new_name}）")
            _save_modifications_to_json(task_id, modifications)

        _safe_log_modification_event()

        return {
            "code": 200,
            "message": "重命名成功",
            "data": {
                "updated_systems_data": systems_data,
                "new_name": new_name
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重命名系统失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"重命名系统失败: {str(e)}")


@router.post("/requirement/systems/{task_id}")
async def add_system(task_id: str, request: AddSystemRequest):
    """新增系统Tab（默认自动拆分）"""
    raw_name = str(request.name or "").strip()
    if not raw_name:
        raise HTTPException(status_code=400, detail="系统名称不能为空")

    system_type = str(request.type or "主系统").strip() or "主系统"
    auto_breakdown = bool(request.auto_breakdown)

    breakdown_error: Optional[str] = None
    added_features = 0

    try:
        with _task_storage_context() as data:
            task = data.get(task_id)
            if not task:
                raise HTTPException(status_code=404, detail="任务不存在")

            if task.get("status") != "completed":
                raise HTTPException(status_code=400, detail="只能修改已完成的任务")

            if task.get("confirmed", False):
                raise HTTPException(status_code=400, detail="该任务已确认，不能修改")
            if not request.confirm:
                raise HTTPException(status_code=400, detail="实质性修改需要确认")
            _ensure_system_scope_mutation_allowed(task)

            systems_data = task.get("systems_data", {})
            modifications = task.get("modifications", [])

            # 需求内容：优先用任务快照；没有则回退解析原始DOCX
            requirement_content = str(task.get("requirement_content") or "").strip()
            if not requirement_content:
                file_path = str(task.get("file_path") or "").strip()
                if file_path:
                    real_upload_dir = os.path.realpath(settings.UPLOAD_DIR)
                    real_path = os.path.realpath(file_path)
                    if real_path.startswith(real_upload_dir) and os.path.exists(real_path):
                        parsed = docx_parser.parse(real_path)
                        requirement_content = str(parsed.get("requirement_content") or "").strip()
                        if requirement_content:
                            task["requirement_content"] = requirement_content
                if not requirement_content:
                    raise HTTPException(status_code=400, detail="缺少requirement_content，无法自动拆分（可重新评估或重新上传）")

            # 标准化系统名称（匹配系统清单）
            from backend.agent.system_identification_agent import get_system_identification_agent
            from backend.agent.feature_breakdown_agent import get_feature_breakdown_agent

            knowledge_service = get_knowledge_service()
            sys_agent = get_system_identification_agent(knowledge_service)
            if not getattr(sys_agent, "system_list", None):
                sys_agent.system_list = sys_agent._load_system_list()

            validated = sys_agent.validate_and_filter_systems([{"name": raw_name, "type": system_type, "description": ""}])
            final_name = validated[0]["name"] if validated else raw_name

            if final_name in systems_data:
                raise HTTPException(status_code=400, detail=f"系统 '{final_name}' 已存在")

            # 先创建空Tab，保证即使自动拆分失败也能保留系统Tab用于手工补齐
            systems_data[final_name] = []
            task["systems_data"] = systems_data
            task["systems"] = list(systems_data.keys())

            if auto_breakdown:
                try:
                    feature_agent = get_feature_breakdown_agent(knowledge_service)
                    features = feature_agent.breakdown(
                        requirement_content=requirement_content,
                        system_name=final_name,
                        system_type=system_type,
                        task_id=task_id
                    )
                    features = sys_agent.validate_system_names_in_features(final_name, features)
                    systems_data[final_name] = features
                    task["systems_data"] = systems_data
                    _ensure_feature_ids(task)
                    added_features = len(features)
                except Exception as e:
                    breakdown_error = str(e)
                    logger.warning(f"[任务 {task_id}] 新增系统Tab自动拆分失败: {e}")

            # 同步系统校准卡片（只维护 selected_systems）
            analysis = task.get("ai_system_analysis") or {}
            if not isinstance(analysis, dict):
                analysis = {}
            selected = analysis.get("selected_systems")
            if not isinstance(selected, list):
                selected = []
            if not any(item.get("name") == final_name for item in selected if isinstance(item, dict)):
                kb_hits = []
                for cand in analysis.get("candidate_systems") or []:
                    if isinstance(cand, dict) and cand.get("name") == final_name:
                        kb_hits = cand.get("kb_hits") or []
                        break
                selected.append({
                    "name": final_name,
                    "type": system_type,
                    "description": "",
                    "confidence": "人工补充",
                    "reasons": ["项目经理新增系统Tab并触发自动拆分"],
                    "kb_hits": kb_hits,
                })
            analysis["selected_systems"] = selected
            analysis["updated_at"] = datetime.now().isoformat()
            task["ai_system_analysis"] = analysis

            mod = {
                "id": f"mod_{uuid.uuid4().hex[:8]}",
                "timestamp": datetime.now().isoformat(),
                "operation": "add_system",
                "system": final_name,
                "system_type": system_type,
                "auto_breakdown": auto_breakdown,
                "added_features": added_features,
                "breakdown_error": breakdown_error,
            }
            modifications.append(mod)
            task["modifications"] = modifications
            _prepend_task_remark(task, f"PM：新增系统（{final_name}）")
            _save_modifications_to_json(task_id, modifications)

        _safe_log_modification_event()

        return {
            "code": 200,
            "message": "新增成功" if not breakdown_error else "新增成功（自动拆分失败，可手工补齐）",
            "data": {
                "final_system_name": final_name,
                "added_features": added_features,
                "auto_breakdown": auto_breakdown,
                "breakdown_error": breakdown_error,
                "updated_systems_data": systems_data
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"新增系统Tab失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"新增系统Tab失败: {str(e)}")


@router.post("/requirement/systems/{task_id}/{system_name}/rebreakdown")
async def rebreakdown_system(task_id: str, system_name: str, request: RebreakdownSystemRequest):
    """重新拆分指定系统（覆盖该系统下全部功能点）"""
    normalized_system = str(system_name or "").strip()
    if not normalized_system:
        raise HTTPException(status_code=400, detail="system_name不能为空")

    breakdown_error: Optional[str] = None
    old_count = 0
    new_count = 0
    resolved_type = str(request.system_type or "").strip() or None

    try:
        with _task_storage_context() as data:
            task = data.get(task_id)
            if not task:
                raise HTTPException(status_code=404, detail="任务不存在")

            if task.get("status") != "completed":
                raise HTTPException(status_code=400, detail="只能修改已完成的任务")

            if task.get("confirmed", False):
                raise HTTPException(status_code=400, detail="该任务已确认，不能修改")
            _ensure_system_scope_mutation_allowed(task)

            systems_data = task.get("systems_data", {})
            if normalized_system not in systems_data:
                raise HTTPException(status_code=400, detail=f"系统 '{normalized_system}' 不存在")

            modifications = task.get("modifications", [])

            # 需求内容：优先用任务快照；没有则回退解析原始DOCX
            requirement_content = str(task.get("requirement_content") or "").strip()
            if not requirement_content:
                file_path = str(task.get("file_path") or "").strip()
                if file_path:
                    real_upload_dir = os.path.realpath(settings.UPLOAD_DIR)
                    real_path = os.path.realpath(file_path)
                    if real_path.startswith(real_upload_dir) and os.path.exists(real_path):
                        parsed = docx_parser.parse(real_path)
                        requirement_content = str(parsed.get("requirement_content") or "").strip()
                        if requirement_content:
                            task["requirement_content"] = requirement_content
                if not requirement_content:
                    raise HTTPException(status_code=400, detail="缺少requirement_content，无法自动拆分（可重新评估或重新上传）")

            # 系统类型：优先请求参数，其次从ai_system_analysis.selected_systems推断
            analysis = task.get("ai_system_analysis") or {}
            if not resolved_type and isinstance(analysis, dict) and isinstance(analysis.get("selected_systems"), list):
                for item in analysis.get("selected_systems") or []:
                    if isinstance(item, dict) and item.get("name") == normalized_system:
                        resolved_type = str(item.get("type") or "").strip() or None
                        break
            if not resolved_type:
                resolved_type = "主系统"

            # 记录旧数量
            old_features = systems_data.get(normalized_system) or []
            old_count = len(old_features) if isinstance(old_features, list) else 0

            # 重新拆分
            from backend.agent.system_identification_agent import get_system_identification_agent
            from backend.agent.feature_breakdown_agent import get_feature_breakdown_agent

            knowledge_service = get_knowledge_service()
            sys_agent = get_system_identification_agent(knowledge_service)
            if not getattr(sys_agent, "system_list", None):
                sys_agent.system_list = sys_agent._load_system_list()

            try:
                feature_agent = get_feature_breakdown_agent(knowledge_service)
                features = feature_agent.breakdown(
                    requirement_content=requirement_content,
                    system_name=normalized_system,
                    system_type=resolved_type,
                    task_id=task_id
                )
                features = sys_agent.validate_system_names_in_features(normalized_system, features)
                systems_data[normalized_system] = features
                task["systems_data"] = systems_data
                _ensure_feature_ids(task)
                new_count = len(features)
            except Exception as e:
                breakdown_error = str(e)
                logger.warning(f"[任务 {task_id}] 重新拆分失败: {e}")
                new_count = old_count

            # 更新系统校准卡片理由
            if isinstance(analysis, dict) and isinstance(analysis.get("selected_systems"), list):
                for item in analysis.get("selected_systems") or []:
                    if isinstance(item, dict) and item.get("name") == normalized_system:
                        item.setdefault("reasons", [])
                        if isinstance(item.get("reasons"), list):
                            item["reasons"].append("项目经理触发重新拆分当前系统")
                        item["confidence"] = item.get("confidence") or "人工"
                        item["type"] = item.get("type") or resolved_type
                analysis["updated_at"] = datetime.now().isoformat()
                task["ai_system_analysis"] = analysis

            mod = {
                "id": f"mod_{uuid.uuid4().hex[:8]}",
                "timestamp": datetime.now().isoformat(),
                "operation": "rebreakdown_system",
                "system": normalized_system,
                "system_type": resolved_type,
                "old_features": old_count,
                "new_features": new_count,
                "breakdown_error": breakdown_error,
            }
            modifications.append(mod)
            task["modifications"] = modifications
            _save_modifications_to_json(task_id, modifications)

        _safe_log_modification_event()

        return {
            "code": 200,
            "message": "重新拆分完成" if not breakdown_error else "重新拆分失败（保留原结果）",
            "data": {
                "system": normalized_system,
                "system_type": resolved_type,
                "old_features": old_count,
                "new_features": new_count,
                "breakdown_error": breakdown_error,
                "updated_systems_data": systems_data,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重新拆分系统失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"重新拆分系统失败: {str(e)}")


@router.post("/requirement/confirm/{task_id}")
async def confirm_evaluation(task_id: str):
    """
    确认评估结果，生成最终报告

    流程：
    1. 标记任务为confirmed
    2. 【v2.4】计算 Phase 1 diff（PM 修正）
    3. 使用最新的systems_data重新生成Excel
    4. 更新report_path
    5. 如果有回调URL，发送完成通知

    Args:
        task_id: 任务ID

    Returns:
        Dict: 确认结果
    """
    task = _get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail="任务未完成")

    if task.get("confirmed", False):
        raise HTTPException(status_code=400, detail="该任务已经确认过了")

    try:
        # 获取最新的systems_data
        systems_data = task.get("systems_data", {})
        if not systems_data:
            raise HTTPException(status_code=400, detail="没有可确认的评估数据")

        # 【v2.4】计算 Phase 1 diff（PM 提交时）
        ai_original_output = task.get("ai_original_output")
        if ai_original_output:
            from backend.service.diff_service import get_diff_service
            diff_service = get_diff_service()

            pm_correction_diff = diff_service.compute_phase1_diff(
                task_id=task_id,
                ai_original_output=ai_original_output,
                pm_final_systems_data=systems_data
            )

            # 保存 Phase 1 diff
            with _task_storage_context() as data:
                task_record = data.get(task_id)
                if task_record:
                    task_record["pm_correction_diff"] = pm_correction_diff
                    logger.info(f"[任务 {task_id}] Phase 1 diff 已计算并保存")

        # 生成新的Excel报告（包含修正记录）
        from backend.utils.excel_generator import excel_generator
        from backend.agent.work_estimation_agent import work_estimation_agent

        # 获取专家评分数据
        expert_estimates = work_estimation_agent.get_expert_estimates_for_excel()

        # 生成新的报告文件名（加上final标记）
        import os
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        requirement_name = task.get("requirement_name", task_id)
        filename = f"{task_id}_{requirement_name[:20]}_final_{timestamp}.xlsx"
        file_path = os.path.join(settings.REPORT_DIR, filename)

        # 生成报告
        report_path = excel_generator.generate_report(
            task_id=task_id,
            requirement_name=requirement_name,
            systems_data=systems_data,
            expert_estimates=expert_estimates,
            output_path=file_path
        )

        # 更新任务状态
        confirmed_at = datetime.now().isoformat()
        with _task_storage_context() as data:
            task_record = data.get(task_id)
            if task_record:
                task_record["confirmed"] = True
                task_record["confirmed_at"] = confirmed_at
                task_record["workflow_status"] = "completed"
                task_record["report_path"] = report_path
                task_record["message"] = "评估完成并已确认"
                _freeze_task_if_needed(task_record)

        logger.info(f"[任务 {task_id}] 已确认，最终报告: {report_path}")

        return {
            "code": 200,
            "message": "确认成功",
            "data": {
                "report_path": file_path,
                "confirmed_at": confirmed_at
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"确认评估失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"确认评估失败: {str(e)}")


@router.get("/requirement/modifications/{task_id}")
async def get_modifications(task_id: str):
    """
    获取修正历史记录

    Args:
        task_id: 任务ID

    Returns:
        Dict: 修正历史
    """
    task = _get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    modifications = task.get("modifications", [])

    return {
        "code": 200,
        "data": {
            "task_id": task_id,
            "total": len(modifications),
            "modifications": modifications
        }
    }


def _save_modifications_to_json(task_id: str, modifications: list):
    """
    持久化修正记录到JSON文件

    Args:
        task_id: 任务ID
        modifications: 修改记录列表
    """
    try:
        import json
        import os

        # 确保data目录存在
        os.makedirs("data", exist_ok=True)

        # 保存到JSON文件
        json_file = os.path.join("data", "task_modifications.json")

        # 读取现有数据
        existing_data = {}
        if os.path.exists(json_file):
            with open(json_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)

        # 更新数据
        existing_data[task_id] = {
            "task_id": task_id,
            "modifications": modifications,
            "updated_at": datetime.now().isoformat()
        }

        # 写入文件
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=2)

        logger.info(f"修正记录已保存到 {json_file}")

    except Exception as e:
        logger.error(f"保存修正记录失败: {str(e)}")


# ==================== v2 任务与评估接口 ====================

@router.post("/tasks")
async def create_task_v2(
    request: Request,
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(""),
    target_system_mode: Optional[str] = Form(None),
    target_system_name: Optional[str] = Form(""),
    background_tasks: BackgroundTasks = None,
    current_user: Dict[str, Any] = Depends(require_roles(["manager"]))
):
    """创建任务（v2）"""
    try:
        if not file.filename:
            return build_error_response(
                request=request,
                status_code=400,
                error_code="TASK_002",
                message="任务文件类型不支持",
            )

        ext = os.path.splitext(file.filename.lower())[1]
        allowed_exts = {".docx", ".doc", ".xls"}
        if ext not in allowed_exts:
            return build_error_response(
                request=request,
                status_code=400,
                error_code="TASK_002",
                message="任务文件类型不支持",
                details={"filename": file.filename, "supported": sorted(allowed_exts)},
            )

        content = await file.read()
        if len(content) > settings.MAX_FILE_SIZE:
            return build_error_response(
                request=request,
                status_code=413,
                error_code="TASK_003",
                message="文件过大",
                details={
                    "max_bytes": settings.MAX_FILE_SIZE,
                    "max_mb": int(settings.MAX_FILE_SIZE // (1024 * 1024)),
                },
            )

        if MAGIC_AVAILABLE:
            try:
                mime_type = magic.from_buffer(content, mime=True)
                allowed_mimes = {
                    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
                    ".doc": {"application/msword", "application/vnd.ms-word"},
                    ".xls": {"application/vnd.ms-excel"},
                }
                if mime_type not in (allowed_mimes.get(ext) or set()) and mime_type != "application/octet-stream":
                    return build_error_response(
                        request=request,
                        status_code=400,
                        error_code="TASK_002",
                        message="任务文件类型不支持",
                        details={"filename": file.filename, "mime_type": mime_type, "supported": sorted(allowed_exts)},
                    )
            except Exception as e:
                logger.warning(f"MIME类型检测失败: {e}，继续处理")

        normalized_target_system_mode, normalized_target_system_name = _normalize_target_system_selection(
            target_system_mode,
            target_system_name,
            current_user,
        )

        task_id = str(uuid.uuid4())
        upload_dir = settings.UPLOAD_DIR
        os.makedirs(upload_dir, exist_ok=True)
        safe_filename = _sanitize_filename(file.filename, default_name=f"upload{ext}")
        file_path = os.path.join(upload_dir, f"{task_id}_{safe_filename}")
        with open(file_path, "wb") as buffer:
            buffer.write(content)

        created_at = datetime.now().isoformat()
        creator_id = current_user.get("id")
        creator_name = current_user.get("display_name") or current_user.get("username") or "未知"
        task_record = {
            "task_id": task_id,
            "name": name or os.path.splitext(safe_filename)[0],
            "description": description or "",
            "creator_id": creator_id,
            "creator_name": creator_name,
            "filename": safe_filename,
            "file_path": file_path,
            "target_system_mode": normalized_target_system_mode,
            "target_system_name": normalized_target_system_name,
            "status": "pending",
            "ai_status": "pending",
            "progress": 0,
            "message": "任务已创建，等待处理",
            "created_at": created_at,
            "report_path": None,
            "workflow_status": "draft",
            "current_round": 1,
            "max_rounds": DEFAULT_MAX_ROUNDS,
            "expert_assignments": [],
            "evaluations": {},
            "evaluation_drafts": {},
            "report_versions": [],
            "round_feature_ids": {},
            "deviations": {},
            "round_means": {},
            "high_deviation_features": {}
        }
        with _task_storage_context() as data:
            data[task_id] = task_record

        _safe_log_task_event()

        if background_tasks:
            background_tasks.add_task(process_task, task_id, file_path)

        return {"task_id": task_id, "status": "processing", "message": "AI正在分析文档，请稍候..."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建任务失败: {str(e)}")
        return build_error_response(
            request=request,
            status_code=400,
            error_code="TASK_004",
            message="任务文件解析失败",
            details={"reason": str(e)},
        )


class DashboardQueryRequest(BaseModel):
    page: str
    perspective: str
    filters: Optional[Dict[str, Any]] = None


def _parse_dashboard_time_window(filters: Dict[str, Any]) -> Tuple[Optional[datetime], Optional[datetime], Optional[str]]:
    now = datetime.now()
    time_range = str((filters or {}).get("time_range") or "").strip().lower()
    if not time_range:
        return now - timedelta(days=90), now, None

    # v2.2 统一统计窗口：固定近90天（不对外暴露可配置窗口），保留历史入参但统一落到90天口径。
    if time_range in {"last_7d", "last_30d", "this_month", "last_month", "last_90d"}:
        return now - timedelta(days=90), now, None

    # 禁止自定义时间窗口（避免被前端/外部调用绕开“固定90天”口径）
    if time_range == "custom":
        return None, None, "time_range"

    return None, None, "time_range"


def _dashboard_safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _dashboard_parse_iso_datetime(value: Any) -> Optional[datetime]:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except Exception:
        return None


def _dashboard_extract_final_days_by_system(task: Dict[str, Any]) -> Dict[str, float]:
    by_system = task.get("final_estimation_days_by_system") if isinstance(task.get("final_estimation_days_by_system"), list) else []
    result: Dict[str, float] = {}
    for item in by_system:
        if not isinstance(item, dict):
            continue
        sid = str(item.get("system_id") or item.get("system_name") or "").strip()
        if not sid:
            continue
        result[sid] = result.get(sid, 0.0) + _dashboard_safe_float(item.get("days"))

    if result:
        return result

    systems = task.get("systems") if isinstance(task.get("systems"), list) else []
    systems = [str(item or "").strip() for item in systems if str(item or "").strip()]
    if len(systems) == 1:
        total = _dashboard_safe_float(task.get("final_estimation_days_total"))
        if total > 0:
            result[systems[0]] = total
    return result


def _dashboard_extract_ai_initial_feature_counts(task: Dict[str, Any]) -> Tuple[Dict[str, int], bool]:
    counts: Dict[str, int] = {}
    ai_initial_features = task.get("ai_initial_features") if isinstance(task.get("ai_initial_features"), list) else []
    if ai_initial_features:
        for item in ai_initial_features:
            if not isinstance(item, dict):
                continue
            feature_payload = item.get("feature") if isinstance(item.get("feature"), dict) else {}
            system_name = str(item.get("system_name") or feature_payload.get("系统") or "").strip()
            if not system_name:
                continue
            counts[system_name] = counts.get(system_name, 0) + 1
        return counts, False

    systems_data = task.get("systems_data") if isinstance(task.get("systems_data"), dict) else {}
    for system_name, features in systems_data.items():
        normalized = str(system_name or "").strip()
        if not normalized:
            continue
        if isinstance(features, list):
            counts[normalized] = counts.get(normalized, 0) + len([item for item in features if isinstance(item, dict)])
    return counts, True


def _dashboard_extract_ai_days_by_system(task: Dict[str, Any]) -> Tuple[Dict[str, float], bool]:
    days: Dict[str, float] = {}
    ai_initial_features = task.get("ai_initial_features") if isinstance(task.get("ai_initial_features"), list) else []
    if ai_initial_features:
        for item in ai_initial_features:
            if not isinstance(item, dict):
                continue
            feature_payload = item.get("feature") if isinstance(item.get("feature"), dict) else {}
            system_name = str(item.get("system_name") or feature_payload.get("系统") or "").strip()
            if not system_name:
                continue
            days[system_name] = days.get(system_name, 0.0) + _get_ai_estimate(feature_payload)
        return days, False

    systems_data = task.get("systems_data") if isinstance(task.get("systems_data"), dict) else {}
    for system_name, features in systems_data.items():
        normalized = str(system_name or "").strip()
        if not normalized or not isinstance(features, list):
            continue
        for feature in features:
            if not isinstance(feature, dict):
                continue
            days[normalized] = days.get(normalized, 0.0) + _get_ai_estimate(feature)

    if days:
        return days, True

    final_by_system = _dashboard_extract_final_days_by_system(task)
    if len(final_by_system) == 1:
        ai_total = _dashboard_safe_float(task.get("ai_estimation_days_total"))
        if ai_total > 0:
            only_system = next(iter(final_by_system.keys()))
            return {only_system: ai_total}, True

    return {}, True


def _dashboard_feature_key(modification: Dict[str, Any]) -> str:
    feature_id = str(modification.get("feature_id") or "").strip()
    if feature_id:
        return feature_id

    feature_name = str(modification.get("feature_name") or "").strip()
    feature_index = modification.get("feature_index")
    if feature_name:
        return f"{feature_name}#{feature_index}"

    mod_id = str(modification.get("id") or "").strip()
    if mod_id:
        return mod_id

    return uuid.uuid4().hex


def _dashboard_is_profile_stale(profile: Dict[str, Any]) -> bool:
    stale_days = int(os.getenv("PROFILE_STALE_DAYS", "30"))
    if stale_days <= 0:
        return False

    updated_at = str(profile.get("updated_at") or profile.get("created_at") or "").strip()
    if not updated_at:
        return True

    try:
        updated_dt = parse_iso_datetime(updated_at)
    except Exception:
        return True
    if updated_dt is None:
        return True

    return updated_dt < (current_time() - timedelta(days=stale_days))


def _dashboard_documents_score(document_count: int) -> int:
    if document_count >= 11:
        return 25
    if document_count >= 6:
        return 15
    if document_count >= 1:
        return 5
    return 0


def _dashboard_profile_completeness(profile: Dict[str, Any]) -> Dict[str, Any]:
    fields = profile.get("fields") if isinstance(profile.get("fields"), dict) else {}
    completeness = profile.get("completeness") if isinstance(profile.get("completeness"), dict) else {}

    code_scan_score = 30 if bool(completeness.get("code_scan")) else 0
    esb_score = 25 if bool(completeness.get("esb")) else 0
    document_count = int(completeness.get("documents_normal") or profile.get("document_count") or 0)
    documents_score = _dashboard_documents_score(document_count)
    module_structure = fields.get("module_structure") if isinstance(fields.get("module_structure"), list) else []
    module_score = 20 if len(module_structure) >= 1 else 0
    total_score = max(0, min(100, code_scan_score + esb_score + documents_score + module_score))

    return {
        "total_score": total_score,
        "code_scan_score": code_scan_score,
        "esb_score": esb_score,
        "documents_score": documents_score,
        "module_score": module_score,
        "document_count": document_count,
        "module_count": len(module_structure),
        "is_stale": _dashboard_is_profile_stale(profile),
    }


def _dashboard_user_display_name_map() -> Dict[str, str]:
    users = user_service.list_users()
    name_map: Dict[str, str] = {}
    for user in users:
        if not isinstance(user, dict):
            continue
        user_id = str(user.get("id") or "").strip()
        username = str(user.get("username") or "").strip()
        display_name = str(user.get("display_name") or username or user_id).strip()
        if user_id:
            name_map[user_id] = display_name
        if username and username not in name_map:
            name_map[username] = display_name
    return name_map


def _dashboard_system_display_name_map(scoped_tasks: List[Dict[str, Any]], profiles: List[Dict[str, Any]]) -> Dict[str, str]:
    name_map: Dict[str, str] = {}

    try:
        systems = system_routes._read_systems()
    except Exception:
        systems = []

    for system in systems:
        if not isinstance(system, dict):
            continue
        sid = str(system.get("id") or "").strip()
        sname = str(system.get("name") or "").strip()
        if sid and sname:
            name_map[sid] = sname
        if sname and sname not in name_map:
            name_map[sname] = sname

    for profile in profiles:
        if not isinstance(profile, dict):
            continue
        sid = str(profile.get("system_id") or "").strip()
        sname = str(profile.get("system_name") or "").strip()
        if sid and sname:
            name_map[sid] = sname
        if sname and sname not in name_map:
            name_map[sname] = sname

    for task in scoped_tasks:
        if not isinstance(task, dict):
            continue
        final_by_system = task.get("final_estimation_days_by_system")
        if not isinstance(final_by_system, list):
            continue
        for item in final_by_system:
            if not isinstance(item, dict):
                continue
            sid = str(item.get("system_id") or "").strip()
            sname = str(item.get("system_name") or "").strip()
            if sid and sname:
                name_map[sid] = sname
            if sname and sname not in name_map:
                name_map[sname] = sname

    return name_map


def _dashboard_resolve_system_name(system_id: str, system_name_map: Dict[str, str]) -> str:
    sid = str(system_id or "").strip()
    if not sid:
        return ""
    return str(system_name_map.get(sid) or sid).strip()


def _build_management_dashboard_widgets(
    *,
    page: str,
    scoped_tasks: List[Dict[str, Any]],
    shared_filters: Dict[str, Any],
) -> List[Dict[str, Any]]:
    profile_service = get_system_profile_service()
    profiles = profile_service.list_profiles()
    user_name_map = _dashboard_user_display_name_map()
    system_name_map = _dashboard_system_display_name_map(scoped_tasks, profiles)

    profile_completeness_items: List[Dict[str, Any]] = []
    profile_score_map: Dict[str, float] = {}
    for profile in profiles:
        if not isinstance(profile, dict):
            continue
        system_id = str(profile.get("system_id") or profile.get("system_name") or "").strip()
        if not system_id:
            continue
        score_payload = _dashboard_profile_completeness(profile)
        total_score = float(score_payload.get("total_score") or 0)
        profile_score_map[system_id] = total_score

        system_name = str(profile.get("system_name") or system_name_map.get(system_id) or system_id).strip() or system_id
        system_name_map[system_id] = system_name
        if system_name not in system_name_map:
            system_name_map[system_name] = system_name

        profile_completeness_items.append(
            {
                "system_id": system_id,
                "system_name": system_name,
                "completeness_score": int(total_score),
                "code_scan": int(score_payload.get("code_scan_score") or 0),
                "esb": int(score_payload.get("esb_score") or 0),
                "documents": int(score_payload.get("documents_score") or 0),
                "module_structure": int(score_payload.get("module_score") or 0),
                "stale": "过期" if bool(score_payload.get("is_stale")) else "-",
                "risk": "低分预警" if total_score < 40 else "-",
                "drilldown_filters": {**shared_filters, "system_id": system_id},
            }
        )

    profile_completeness_items.sort(
        key=lambda item: (
            -_dashboard_safe_float(item.get("completeness_score")),
            str(item.get("system_id") or ""),
        )
    )

    pm_stats: Dict[str, Dict[str, Any]] = {}
    ai_stats: Dict[str, Dict[str, Any]] = {}
    owner_cycle_stats: Dict[str, Dict[str, Any]] = {}

    for task in scoped_tasks:
        task_id = str(task.get("task_id") or "").strip()
        final_days_by_system = _dashboard_extract_final_days_by_system(task)
        ai_feature_count_by_system, feature_count_downgraded = _dashboard_extract_ai_initial_feature_counts(task)
        ai_days_by_system, ai_days_downgraded = _dashboard_extract_ai_days_by_system(task)

        for system_id in final_days_by_system.keys():
            if system_id not in pm_stats:
                pm_stats[system_id] = {
                    "task_ids": set(),
                    "correction_keys": set(),
                    "addition_keys": set(),
                    "ai_initial_total": 0,
                    "caliber_downgraded": False,
                }
            pm_stats[system_id]["task_ids"].add(task_id)
            pm_stats[system_id]["ai_initial_total"] += int(ai_feature_count_by_system.get(system_id) or 0)
            if feature_count_downgraded:
                pm_stats[system_id]["caliber_downgraded"] = True

        modifications = task.get("modifications") if isinstance(task.get("modifications"), list) else []
        for modification in modifications:
            if not isinstance(modification, dict):
                continue
            if str(modification.get("actor_role") or "").strip() != "manager":
                continue
            operation = str(modification.get("operation") or "").strip().lower()
            if operation not in {"add", "update", "delete"}:
                continue
            system_id = str(modification.get("system") or "").strip()
            if not system_id:
                continue
            if system_id not in pm_stats:
                pm_stats[system_id] = {
                    "task_ids": set(),
                    "correction_keys": set(),
                    "addition_keys": set(),
                    "ai_initial_total": 0,
                    "caliber_downgraded": feature_count_downgraded,
                }
            pm_stats[system_id]["task_ids"].add(task_id)
            feature_key = _dashboard_feature_key(modification)
            dedupe_key = f"{task_id}:{feature_key}"
            if operation == "add":
                pm_stats[system_id]["addition_keys"].add(dedupe_key)
            else:
                pm_stats[system_id]["correction_keys"].add(dedupe_key)

        for system_id, final_days in final_days_by_system.items():
            if system_id not in ai_stats:
                ai_stats[system_id] = {
                    "task_ids": set(),
                    "metric_count": 0,
                    "hit_count": 0,
                    "deviation_values": [],
                    "trend_points": [],
                    "caliber_downgraded": False,
                }
            stat = ai_stats[system_id]
            stat["task_ids"].add(task_id)

            ai_days = ai_days_by_system.get(system_id)
            if ai_days is None and len(final_days_by_system) == 1:
                fallback_ai_total = _dashboard_safe_float(task.get("ai_estimation_days_total"))
                if fallback_ai_total > 0:
                    ai_days = fallback_ai_total
                    stat["caliber_downgraded"] = True

            if ai_days is None or final_days <= 0:
                continue

            if ai_days_downgraded:
                stat["caliber_downgraded"] = True

            stat["metric_count"] += 1
            abs_error = abs(ai_days - final_days)
            if (abs_error / final_days) <= 0.2 or abs_error <= 0.5:
                stat["hit_count"] += 1

            deviation_pct = ((ai_days - final_days) / final_days) * 100
            stat["deviation_values"].append(deviation_pct)

            created_dt = _dashboard_parse_iso_datetime(task.get("created_at")) or _dashboard_parse_iso_datetime(task.get("frozen_at"))
            if created_dt:
                stat["trend_points"].append(
                    {
                        "created_at": created_dt.isoformat(),
                        "correction_rate": round(abs_error / final_days * 100, 2),
                    }
                )

        owner_snapshot = task.get("owner_snapshot") if isinstance(task.get("owner_snapshot"), dict) else {}
        owner_id = str(owner_snapshot.get("primary_owner_id") or task.get("creator_id") or "UNASSIGNED").strip() or "UNASSIGNED"
        owner_name = (
            str(owner_snapshot.get("primary_owner_name") or "").strip()
            or user_name_map.get(owner_id)
            or str(task.get("creator_name") or owner_id)
        )

        created_dt = _dashboard_parse_iso_datetime(task.get("created_at"))
        frozen_dt = _dashboard_parse_iso_datetime(task.get("frozen_at"))
        if owner_id not in owner_cycle_stats:
            owner_cycle_stats[owner_id] = {
                "owner_name": owner_name,
                "task_ids": set(),
                "cycle_days": [],
            }
        owner_cycle_stats[owner_id]["task_ids"].add(task_id)
        if created_dt and frozen_dt:
            owner_cycle_stats[owner_id]["cycle_days"].append((frozen_dt - created_dt).total_seconds() / 86400)

    pm_correction_items: List[Dict[str, Any]] = []
    for system_id, stat in pm_stats.items():
        task_count = len(stat["task_ids"])
        ai_initial_total = int(stat.get("ai_initial_total") or 0)
        correction_count = len(stat.get("correction_keys") or [])
        addition_count = len(stat.get("addition_keys") or [])

        correction_rate_value: Optional[float] = None
        addition_rate_value: Optional[float] = None
        if task_count >= 3 and ai_initial_total > 0:
            correction_rate_value = round(correction_count / ai_initial_total * 100, 1)
            addition_rate_value = round(addition_count / ai_initial_total * 100, 1)

        pm_correction_items.append(
            {
                "system_id": system_id,
                "system_name": _dashboard_resolve_system_name(system_id, system_name_map),
                "sample_tasks": task_count,
                "ai_initial_features": ai_initial_total,
                "pm_corrections": correction_count,
                "pm_additions": addition_count,
                "correction_rate": correction_rate_value if correction_rate_value is not None else "N/A",
                "addition_rate": addition_rate_value if addition_rate_value is not None else "N/A",
                "caliber": "口径降级" if stat.get("caliber_downgraded") else "标准",
                "drilldown_filters": {**shared_filters, "system_id": system_id},
            }
        )

    pm_correction_items.sort(
        key=lambda item: (
            -9999 if isinstance(item.get("correction_rate"), str) else -_dashboard_safe_float(item.get("correction_rate")),
            str(item.get("system_id") or ""),
        )
    )

    ai_hit_items: List[Dict[str, Any]] = []
    ai_deviation_items: List[Dict[str, Any]] = []
    ai_trend_items: List[Dict[str, Any]] = []
    ai_trend_series: List[Dict[str, Any]] = []

    for system_id, stat in ai_stats.items():
        task_count = len(stat.get("task_ids") or [])
        metric_count = int(stat.get("metric_count") or 0)
        hit_count = int(stat.get("hit_count") or 0)

        hit_rate_value: Optional[float] = None
        if task_count >= 3 and metric_count >= 3:
            hit_rate_value = round(hit_count / metric_count * 100, 1)

        completeness_score = profile_score_map.get(system_id)
        priority_tag = ""
        if hit_rate_value is not None and completeness_score is not None:
            if hit_rate_value < 50 and completeness_score < 60:
                priority_tag = "优先补画像"

        ai_hit_items.append(
            {
                "system_id": system_id,
                "system_name": _dashboard_resolve_system_name(system_id, system_name_map),
                "sample_tasks": task_count,
                "metric_tasks": metric_count,
                "hit_rate": hit_rate_value if hit_rate_value is not None else "N/A",
                "profile_score": int(completeness_score) if completeness_score is not None else "N/A",
                "priority_tag": priority_tag or "-",
                "caliber": "口径降级" if stat.get("caliber_downgraded") else "标准",
                "drilldown_filters": {**shared_filters, "system_id": system_id},
            }
        )

        deviation_values = stat.get("deviation_values") if isinstance(stat.get("deviation_values"), list) else []
        avg_deviation_value: Optional[float] = None
        if task_count >= 3 and deviation_values:
            avg_deviation_value = round(statistics.mean(deviation_values), 1)

        ai_deviation_items.append(
            {
                "system_id": system_id,
                "system_name": _dashboard_resolve_system_name(system_id, system_name_map),
                "sample_tasks": task_count,
                "avg_deviation_pct": avg_deviation_value if avg_deviation_value is not None else "N/A",
                "max_deviation_pct": round(max(deviation_values), 1) if deviation_values else None,
                "min_deviation_pct": round(min(deviation_values), 1) if deviation_values else None,
                "caliber": "口径降级" if stat.get("caliber_downgraded") else "标准",
                "drilldown_filters": {**shared_filters, "system_id": system_id},
            }
        )

        trend_points = stat.get("trend_points") if isinstance(stat.get("trend_points"), list) else []
        trend_points = sorted(
            [item for item in trend_points if isinstance(item, dict)],
            key=lambda item: str(item.get("created_at") or ""),
        )
        trend_value = "N/A"
        first_rate = None
        latest_rate = None
        if len(trend_points) >= 3:
            first_rate = _dashboard_safe_float(trend_points[0].get("correction_rate"))
            latest_rate = _dashboard_safe_float(trend_points[-1].get("correction_rate"))
            if latest_rate < first_rate:
                trend_value = "improving"
            elif latest_rate > first_rate:
                trend_value = "worsening"
            else:
                trend_value = "flat"

        ai_trend_items.append(
            {
                "system_id": system_id,
                "system_name": _dashboard_resolve_system_name(system_id, system_name_map),
                "sample_tasks": len(trend_points),
                "first_correction_rate": round(first_rate, 1) if first_rate is not None else "N/A",
                "latest_correction_rate": round(latest_rate, 1) if latest_rate is not None else "N/A",
                "trend": trend_value,
                "drilldown_filters": {**shared_filters, "system_id": system_id},
            }
        )

        ai_trend_series.append(
            {
                "system_id": system_id,
                "points": [
                    {
                        "x": str(item.get("created_at") or ""),
                        "y": round(_dashboard_safe_float(item.get("correction_rate")), 2),
                    }
                    for item in trend_points
                ],
            }
        )

    ai_hit_items.sort(
        key=lambda item: (
            -9999 if isinstance(item.get("hit_rate"), str) else -_dashboard_safe_float(item.get("hit_rate")),
            str(item.get("system_id") or ""),
        )
    )
    ai_deviation_items.sort(
        key=lambda item: (
            9999 if isinstance(item.get("avg_deviation_pct"), str) else -abs(_dashboard_safe_float(item.get("avg_deviation_pct"))),
            str(item.get("system_id") or ""),
        )
    )
    ai_trend_items.sort(key=lambda item: str(item.get("system_id") or ""))

    evaluation_cycle_items: List[Dict[str, Any]] = []
    for owner_id, stat in owner_cycle_stats.items():
        task_count = len(stat.get("task_ids") or [])
        cycle_days = stat.get("cycle_days") if isinstance(stat.get("cycle_days"), list) else []
        avg_cycle = None
        if task_count >= 3 and cycle_days:
            avg_cycle = round(statistics.mean(cycle_days), 1)

        evaluation_cycle_items.append(
            {
                "owner_id": owner_id,
                "owner_name": stat.get("owner_name") or owner_id,
                "sample_tasks": task_count,
                "avg_cycle_days": avg_cycle if avg_cycle is not None else "N/A",
                "drilldown_filters": {**shared_filters, "owner_id": owner_id},
            }
        )

    evaluation_cycle_items.sort(
        key=lambda item: (
            -9999 if isinstance(item.get("avg_cycle_days"), str) else -_dashboard_safe_float(item.get("avg_cycle_days")),
            str(item.get("owner_id") or ""),
        )
    )

    profile_contribution_stats: Dict[str, Dict[str, Any]] = {}
    for profile in profiles:
        if not isinstance(profile, dict):
            continue

        actor_id = str(profile.get("updated_by") or "").strip()
        if not actor_id:
            continue

        fields = profile.get("fields") if isinstance(profile.get("fields"), dict) else {}
        module_structure = fields.get("module_structure") if isinstance(fields.get("module_structure"), list) else []
        completeness = profile.get("completeness") if isinstance(profile.get("completeness"), dict) else {}
        document_count = int(completeness.get("documents_normal") or profile.get("document_count") or 0)

        field_count = 0
        for field_key in ("system_scope", "integration_points", "key_constraints"):
            if str(fields.get(field_key) or "").strip():
                field_count += 1

        module_item_count = 0
        for module_item in module_structure:
            if not isinstance(module_item, dict):
                continue
            functions = module_item.get("functions") if isinstance(module_item.get("functions"), list) else []
            if functions:
                module_item_count += len([item for item in functions if isinstance(item, dict)])
            else:
                module_item_count += 1

        contribution_score = document_count + field_count + module_item_count
        if actor_id not in profile_contribution_stats:
            profile_contribution_stats[actor_id] = {
                "contribution_score": 0,
                "document_count": 0,
                "field_count": 0,
                "module_item_count": 0,
                "systems": set(),
            }

        profile_contribution_stats[actor_id]["contribution_score"] += contribution_score
        profile_contribution_stats[actor_id]["document_count"] += document_count
        profile_contribution_stats[actor_id]["field_count"] += field_count
        profile_contribution_stats[actor_id]["module_item_count"] += module_item_count
        profile_contribution_stats[actor_id]["systems"].add(str(profile.get("system_name") or "").strip())

    profile_contribution_items: List[Dict[str, Any]] = []
    for actor_id, stat in profile_contribution_stats.items():
        profile_contribution_items.append(
            {
                "owner_id": actor_id,
                "owner_name": user_name_map.get(actor_id, actor_id),
                "contribution_score": int(stat.get("contribution_score") or 0),
                "document_count": int(stat.get("document_count") or 0),
                "field_count": int(stat.get("field_count") or 0),
                "module_item_count": int(stat.get("module_item_count") or 0),
                "systems_count": len(stat.get("systems") or []),
                "drilldown_filters": {**shared_filters, "owner_id": actor_id},
            }
        )

    profile_contribution_items.sort(
        key=lambda item: (
            -_dashboard_safe_float(item.get("contribution_score")),
            str(item.get("owner_id") or ""),
        )
    )

    widgets_by_page = {
        "system": [
            {
                "widget_id": "profile_completeness_ranking",
                "title": "画像完整度排名",
                "sample_size": len(profile_completeness_items),
                "data": {"items": profile_completeness_items[:20]},
                "drilldown_filters": shared_filters,
            }
        ],
        "ai": [
            {
                "widget_id": "pm_correction_rate_ranking",
                "title": "PM修正率排行（按系统）",
                "sample_size": len(pm_correction_items),
                "data": {"items": pm_correction_items[:20]},
                "drilldown_filters": shared_filters,
            },
            {
                "widget_id": "ai_hit_rate_ranking",
                "title": "AI命中率排行（按系统）",
                "sample_size": len(ai_hit_items),
                "data": {"items": ai_hit_items[:20]},
                "drilldown_filters": shared_filters,
            },
            {
                "widget_id": "ai_deviation_monitoring",
                "title": "AI工作量偏差监控",
                "sample_size": len(ai_deviation_items),
                "data": {"items": ai_deviation_items[:20]},
                "drilldown_filters": shared_filters,
            },
            {
                "widget_id": "ai_learning_trend",
                "title": "AI学习趋势",
                "sample_size": len(ai_trend_items),
                "data": {"items": ai_trend_items[:20], "series": ai_trend_series},
                "drilldown_filters": shared_filters,
            },
        ],
        "rankings": [
            {
                "widget_id": "evaluation_cycle_ranking",
                "title": "评估周期排行（按PM）",
                "sample_size": len(evaluation_cycle_items),
                "data": {"items": evaluation_cycle_items[:20]},
                "drilldown_filters": shared_filters,
            },
            {
                "widget_id": "profile_contribution_ranking",
                "title": "画像贡献度排行（按PM）",
                "sample_size": len(profile_contribution_items),
                "data": {"items": profile_contribution_items[:20]},
                "drilldown_filters": shared_filters,
            },
        ],
    }

    return widgets_by_page.get(page, [])


@router.post("/efficiency/dashboard/query")
async def query_efficiency_dashboard(
    payload: DashboardQueryRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_roles(["admin", "manager", "expert", "viewer"])),
):
    page = str(payload.page or "").strip().lower()
    perspective = str(payload.perspective or "").strip().lower()
    if page not in {"overview", "rankings", "ai", "system", "flow"}:
        return build_error_response(
            request=request,
            status_code=400,
            error_code="REPORT_002",
            message="报表参数不合法",
            details={"field": "page"},
        )
    if perspective not in {"executive", "owner", "expert"}:
        return build_error_response(
            request=request,
            status_code=400,
            error_code="invalid_perspective",
            message="perspective 必须为 owner/expert/executive",
            details={"field": "perspective"},
        )

    filters = payload.filters if isinstance(payload.filters, dict) else {}
    start_at, end_at, time_error = _parse_dashboard_time_window(filters)
    if time_error:
        return build_error_response(
            request=request,
            status_code=400,
            error_code="REPORT_002",
            message="报表参数不合法",
            details={"field": time_error},
        )

    roles = set(current_user.get("roles", []))

    filter_system_ids = set(_ensure_list(filters.get("system_ids")))
    filter_project_ids = set(_ensure_list(filters.get("project_ids")))
    filter_owner_id = str(filters.get("owner_id") or "").strip()
    filter_expert_id = str(filters.get("expert_id") or "").strip()

    with _task_storage_context() as data:
        _cleanup_tasks(data)
        tasks = list(data.values())

    scoped_tasks = []
    for task in tasks:
        _ensure_task_schema(task)
        status_mapped = {
            "draft": "pending",
            "awaiting_assignment": "pending",
            "evaluating": "in_progress",
            "completed": "completed",
            "archived": "closed",
        }.get(str(task.get("workflow_status") or ""), "pending")

        if status_mapped not in {"completed", "closed"}:
            continue

        if "admin" in roles or "viewer" in roles:
            pass
        elif "manager" in roles:
            creator_ok = str(task.get("creator_id") or "") == str(current_user.get("id") or "")
            owner_snapshot = task.get("owner_snapshot") if isinstance(task.get("owner_snapshot"), dict) else {}
            owner_ok = str(owner_snapshot.get("primary_owner_id") or "") == str(current_user.get("id") or "")
            if not (creator_ok or owner_ok):
                continue
        elif "expert" in roles:
            if not any(_assignment_matches_user(item, current_user) for item in _get_active_assignments(task)):
                continue

        frozen_dt = _dashboard_parse_iso_datetime(task.get("frozen_at"))
        if not frozen_dt:
            continue

        if start_at and frozen_dt < start_at:
            continue
        if end_at and frozen_dt > end_at:
            continue

        if filter_project_ids:
            project_id = str(task.get("project_id") or "").strip()
            if project_id not in filter_project_ids:
                continue

        final_days_by_system = _dashboard_extract_final_days_by_system(task)
        task_system_ids = set(final_days_by_system.keys())
        if filter_system_ids and not (task_system_ids & filter_system_ids):
            continue

        if filter_owner_id:
            owner_snapshot = task.get("owner_snapshot") if isinstance(task.get("owner_snapshot"), dict) else {}
            owner_id = str(owner_snapshot.get("primary_owner_id") or "").strip()
            if owner_id != filter_owner_id:
                continue

        if filter_expert_id:
            assignments = _get_active_assignments(task)
            matched = False
            for assignment in assignments:
                expert_id = str(assignment.get("expert_id") or "").strip()
                expert_name = str(assignment.get("expert_name") or "").strip()
                if filter_expert_id in {expert_id, expert_name}:
                    matched = True
                    break
            if not matched:
                continue

        scoped_tasks.append(task)

    sample_size = len(scoped_tasks)

    total_final_days = sum(_dashboard_safe_float(item.get("final_estimation_days_total")) for item in scoped_tasks)
    avg_final_days = round(total_final_days / sample_size, 2) if sample_size else 0.0
    ai_involved_count = sum(
        1
        for item in scoped_tasks
        if bool(item.get("ai_involved") or item.get("ai_initial_feature_count") or item.get("ai_initial_features"))
    )
    ai_involved_rate = round(ai_involved_count / sample_size * 100, 2) if sample_size else 0.0

    user_name_map = _dashboard_user_display_name_map()
    system_name_map = _dashboard_system_display_name_map(scoped_tasks, [])

    creator_counts: Dict[str, int] = {}
    expert_efficiency_stats: Dict[str, Dict[str, Any]] = {}
    system_days: Dict[str, float] = {}
    system_task_counts: Dict[str, int] = {}
    hit_count = 0
    ai_metric_count = 0
    bias_values = []

    for task in scoped_tasks:
        creator_id = str(task.get("creator_id") or "").strip() or "UNASSIGNED"
        creator_counts[creator_id] = creator_counts.get(creator_id, 0) + 1

        task_id = str(task.get("task_id") or "").strip()
        for assignment in _get_active_assignments(task):
            expert_id = str(assignment.get("expert_id") or "").strip()
            if not expert_id:
                continue

            submissions = assignment.get("round_submissions", {})
            if not isinstance(submissions, dict) or not submissions:
                continue

            submitted_dts = [_dashboard_parse_iso_datetime(ts) for ts in submissions.values()]
            submitted_dts = [dt for dt in submitted_dts if dt]
            if not submitted_dts:
                continue

            submitted_dt = max(submitted_dts)
            created_dt = (
                _dashboard_parse_iso_datetime(assignment.get("created_at"))
                or _dashboard_parse_iso_datetime(task.get("created_at"))
                or _dashboard_parse_iso_datetime(task.get("frozen_at"))
            )
            duration_days = 0.0
            if created_dt and submitted_dt and submitted_dt >= created_dt:
                duration_days = (submitted_dt - created_dt).total_seconds() / 86400

            stat = expert_efficiency_stats.setdefault(
                expert_id,
                {
                    "expert_name": str(assignment.get("expert_name") or user_name_map.get(expert_id) or expert_id),
                    "task_durations": {},
                },
            )
            if not str(stat.get("expert_name") or "").strip():
                stat["expert_name"] = str(assignment.get("expert_name") or user_name_map.get(expert_id) or expert_id)

            if task_id:
                task_durations = stat.get("task_durations") if isinstance(stat.get("task_durations"), dict) else {}
                existing = task_durations.get(task_id)
                if existing is None or duration_days > _dashboard_safe_float(existing):
                    task_durations[task_id] = duration_days
                stat["task_durations"] = task_durations

        counted_system_ids = set()
        for system_id, days in _dashboard_extract_final_days_by_system(task).items():
            if filter_system_ids and system_id not in filter_system_ids:
                continue
            system_days[system_id] = system_days.get(system_id, 0.0) + _dashboard_safe_float(days)
            if system_id not in counted_system_ids:
                system_task_counts[system_id] = system_task_counts.get(system_id, 0) + 1
                counted_system_ids.add(system_id)

        ai_total = _dashboard_safe_float(task.get("ai_estimation_days_total"))
        final_total = _dashboard_safe_float(task.get("final_estimation_days_total"))
        if final_total > 0:
            ai_metric_count += 1
            abs_error = abs(ai_total - final_total)
            hit = (abs_error / final_total) <= 0.2 if final_total >= 1 else abs_error <= 0.5
            if hit:
                hit_count += 1
            bias_values.append(ai_total - final_total)

    system_ranking = sorted(system_days.items(), key=lambda item: item[1], reverse=True)
    system_count_ranking = sorted(system_task_counts.items(), key=lambda item: item[1], reverse=True)
    ai_hit_rate = round(hit_count / ai_metric_count * 100, 2) if ai_metric_count else 0.0
    ai_bias = round(statistics.mean(bias_values), 2) if bias_values else 0.0

    shared_filters = {"time_range": "last_90d"}
    if len(filter_system_ids) == 1:
        shared_filters["system_id"] = next(iter(filter_system_ids))
    if len(filter_project_ids) == 1:
        shared_filters["project_id"] = next(iter(filter_project_ids))
    if filter_owner_id:
        shared_filters["owner_id"] = filter_owner_id
    if filter_expert_id:
        shared_filters["expert_id"] = filter_expert_id

    expert_efficiency_items: List[Dict[str, Any]] = []
    for expert_id, stat in expert_efficiency_stats.items():
        task_durations = stat.get("task_durations") if isinstance(stat.get("task_durations"), dict) else {}
        completed_count = len([key for key in task_durations.keys() if str(key or "").strip()])
        total_days = sum(_dashboard_safe_float(value) for value in task_durations.values())
        efficiency_value = round(completed_count / total_days, 3) if total_days > 0 else 0.0
        expert_efficiency_items.append(
            {
                "expert_id": expert_id,
                "expert_name": str(stat.get("expert_name") or user_name_map.get(expert_id) or expert_id),
                "completed_evaluations": completed_count,
                "evaluation_time_days": round(total_days, 2),
                "efficiency": efficiency_value,
                "drilldown_filters": {**shared_filters, "expert_id": expert_id},
            }
        )

    expert_efficiency_items.sort(
        key=lambda item: (
            -_dashboard_safe_float(item.get("efficiency")),
            -_dashboard_safe_float(item.get("completed_evaluations")),
            str(item.get("expert_id") or ""),
        )
    )

    creator_ranking = sorted(creator_counts.items(), key=lambda item: item[1], reverse=True)
    creator_submission_items = [
        {
            "manager_id": creator_id,
            "manager_name": str(user_name_map.get(creator_id) or creator_id),
            "task_count": int(task_count),
            "drilldown_filters": {**shared_filters, "owner_id": creator_id},
        }
        for creator_id, task_count in creator_ranking
    ]

    system_activity_items = [
        {
            "system_id": system_id,
            "system_name": _dashboard_resolve_system_name(system_id, system_name_map),
            "task_count": int(task_count),
            "drilldown_filters": {**shared_filters, "system_id": system_id},
        }
        for system_id, task_count in system_count_ranking
    ]
    system_activity_items.sort(
        key=lambda item: (
            -_dashboard_safe_float(item.get("task_count")),
            str(item.get("system_id") or ""),
        )
    )

    widgets: List[Dict[str, Any]] = []
    if page == "overview":
        widgets = [
            {
                "widget_id": "task_completion_overview",
                "title": "评估任务完成概览",
                "sample_size": sample_size,
                "data": {"task_count": sample_size, "avg_final_days": avg_final_days},
                "drilldown_filters": shared_filters,
            },
            {
                "widget_id": "ai_involved_rate",
                "title": "AI参与率",
                "sample_size": sample_size,
                "data": {"rate": ai_involved_rate, "count": ai_involved_count},
                "drilldown_filters": shared_filters,
            },
        ]
    elif page == "rankings":
        widgets = [
            {
                "widget_id": "evaluation_efficiency_ranking",
                "title": "评估效率排行",
                "sample_size": sample_size,
                "data": {
                    "items": [
                        {
                            **item,
                        }
                        for item in expert_efficiency_items[:20]
                    ]
                },
                "drilldown_filters": shared_filters,
            },
            {
                "widget_id": "task_submission_ranking",
                "title": "任务提交排行",
                "sample_size": sample_size,
                "data": {
                    "items": [
                        {
                            **item,
                        }
                        for item in creator_submission_items[:20]
                    ]
                },
                "drilldown_filters": shared_filters,
            },
            {
                "widget_id": "system_activity_ranking",
                "title": "系统活跃排行",
                "sample_size": sample_size,
                "data": {
                    "items": [
                        {
                            **item,
                        }
                        for item in system_activity_items[:20]
                    ]
                },
                "drilldown_filters": shared_filters,
            },
        ]
    elif page == "ai":
        widgets = [
            {
                "widget_id": "ai_accuracy_overview",
                "title": "AI准确率概览",
                "sample_size": ai_metric_count,
                "data": {"hit_rate": ai_hit_rate, "sample_size": ai_metric_count},
                "drilldown_filters": shared_filters,
            },
            {
                "widget_id": "ai_bias_overview",
                "title": "AI偏差概览",
                "sample_size": ai_metric_count,
                "data": {"bias": ai_bias},
                "drilldown_filters": shared_filters,
            },
        ]
    elif page == "system":
        widgets = [
            {
                "widget_id": "system_remodel_count_top",
                "title": "系统改造次数Top",
                "sample_size": sample_size,
                "data": {
                    "items": [
                        {
                            "system_id": sid,
                            "task_count": count,
                            "drilldown_filters": {**shared_filters, "system_id": sid},
                        }
                        for sid, count in system_count_ranking[:10]
                    ]
                },
                "drilldown_filters": shared_filters,
            },
            {
                "widget_id": "system_remodel_workload_top",
                "title": "系统改造工作量Top",
                "sample_size": sample_size,
                "data": {
                    "items": [
                        {
                            "system_id": sid,
                            "days": round(days, 2),
                            "drilldown_filters": {**shared_filters, "system_id": sid},
                        }
                        for sid, days in system_ranking[:10]
                    ]
                },
                "drilldown_filters": shared_filters,
            },
        ]
    elif page == "flow":
        cycle_times = []
        for task in scoped_tasks:
            created_dt = _dashboard_parse_iso_datetime(task.get("created_at"))
            frozen_dt = _dashboard_parse_iso_datetime(task.get("frozen_at"))
            if not created_dt or not frozen_dt:
                continue
            cycle_times.append((frozen_dt - created_dt).total_seconds() / 86400)
        avg_cycle = round(statistics.mean(cycle_times), 2) if cycle_times else 0.0

        widgets = [
            {
                "widget_id": "flow_cycle_time",
                "title": "流程周期",
                "sample_size": len(cycle_times),
                "data": {"avg_days": avg_cycle},
                "drilldown_filters": shared_filters,
            },
            {
                "widget_id": "flow_throughput",
                "title": "流程吞吐",
                "sample_size": sample_size,
                "data": {"completed_tasks": sample_size},
                "drilldown_filters": shared_filters,
            },
        ]

    if settings.V21_DASHBOARD_MGMT_ENABLED:
        widgets.extend(
            _build_management_dashboard_widgets(
                page=page,
                scoped_tasks=scoped_tasks,
                shared_filters=shared_filters,
            )
        )

    return {
        "result": {
            "page": page,
            "perspective": perspective,
            "widgets": widgets,
        }
    }
@router.get("/tasks")
async def list_tasks_v2(
    scope: Optional[str] = Query(None),
    group_by_status: bool = Query(False),
    time_range: Optional[str] = Query(None),
    start_at: Optional[str] = Query(None),
    end_at: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    system_id: Optional[str] = Query(None),
    owner_id: Optional[str] = Query(None),
    expert_id: Optional[str] = Query(None),
    project_id: Optional[str] = Query(None),
    ai_involved: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """获取任务列表（v2 / API-010）"""

    roles = set(current_user.get("roles", []))
    allowed_roles = {"admin", "manager", "expert", "viewer"}
    if not (roles & allowed_roles):
        raise HTTPException(status_code=403, detail="权限不足")

    def _map_status(workflow_status: str) -> str:
        mapping = {
            "draft": "pending",
            "awaiting_assignment": "pending",
            "evaluating": "in_progress",
            "completed": "completed",
            "archived": "closed",
        }
        return mapping.get(str(workflow_status or "").strip(), "pending")

    def _parse_time_window() -> Tuple[Optional[datetime], Optional[datetime]]:
        if not time_range:
            return None, None

        now = datetime.now()
        value = str(time_range).strip().lower()
        if value == "last_7d":
            return now - timedelta(days=7), now
        if value == "last_30d":
            return now - timedelta(days=30), now
        if value == "last_90d":
            return now - timedelta(days=90), now
        if value == "this_month":
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            return month_start, now
        if value == "last_month":
            current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            last_month_end = current_month_start - timedelta(microseconds=1)
            last_month_start = last_month_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            return last_month_start, last_month_end
        if value == "custom":
            if not start_at or not end_at:
                return None, None
            try:
                return datetime.fromisoformat(start_at), datetime.fromisoformat(end_at)
            except Exception:
                return None, None
        return None, None

    def _match_scope(task: Dict[str, Any]) -> bool:
        explicit_scope = str(scope or "").strip().lower()
        if explicit_scope:
            if explicit_scope not in {"all", "created", "assigned"}:
                return False
            if explicit_scope == "all":
                return bool({"admin", "viewer"} & roles)
            if explicit_scope == "created":
                if "manager" not in roles:
                    return False
                creator_id = task.get("creator_id")
                creator_name = task.get("creator_name")
                return creator_id == current_user.get("id") or creator_name in {
                    current_user.get("display_name"),
                    current_user.get("username"),
                }
            if explicit_scope == "assigned":
                if "expert" not in roles:
                    return False
                return any(_assignment_matches_user(item, current_user) for item in _get_active_assignments(task))

        if "admin" in roles or "viewer" in roles:
            return True
        if "expert" in roles:
            return any(_assignment_matches_user(item, current_user) for item in _get_active_assignments(task))
        if "manager" in roles:
            creator_id = task.get("creator_id")
            creator_name = task.get("creator_name")
            if creator_id == current_user.get("id") or creator_name in {
                current_user.get("display_name"),
                current_user.get("username"),
            }:
                return True
            owner_snapshot = task.get("owner_snapshot") if isinstance(task.get("owner_snapshot"), dict) else {}
            primary_owner_id = str(owner_snapshot.get("primary_owner_id") or "").strip()
            return bool(primary_owner_id and primary_owner_id == str(current_user.get("id") or "").strip())
        return False

    def _extract_filter_time(task: Dict[str, Any], mapped_status: str) -> Optional[datetime]:
        if mapped_status in {"completed", "closed"}:
            candidates = [task.get("frozen_at"), task.get("confirmed_at"), task.get("completed_at"), task.get("created_at")]
        else:
            candidates = [task.get("created_at")]
        for value in candidates:
            text_value = str(value or "").strip()
            if not text_value:
                continue
            try:
                return datetime.fromisoformat(text_value)
            except Exception:
                continue
        return None

    def _match_filters(task: Dict[str, Any], mapped_status: str) -> bool:
        normalized_status = str(status or "").strip().lower()
        if normalized_status and normalized_status != mapped_status:
            return False

        normalized_system_id = str(system_id or "").strip()
        if normalized_system_id:
            systems = task.get("final_estimation_days_by_system") if isinstance(task.get("final_estimation_days_by_system"), list) else []
            if not any(str(item.get("system_id") or "").strip() == normalized_system_id for item in systems if isinstance(item, dict)):
                return False

        normalized_owner_id = str(owner_id or "").strip()
        if normalized_owner_id:
            owner_snapshot = task.get("owner_snapshot") if isinstance(task.get("owner_snapshot"), dict) else {}
            owner_ids = {str(owner_snapshot.get("primary_owner_id") or "").strip()}
            for item in owner_snapshot.get("owners") or []:
                if isinstance(item, dict):
                    owner_ids.add(str(item.get("owner_id") or "").strip())
            owner_ids.discard("")
            if normalized_owner_id not in owner_ids:
                return False

        normalized_expert_id = str(expert_id or "").strip()
        if normalized_expert_id:
            assignments = task.get("expert_assignments") if isinstance(task.get("expert_assignments"), list) else []
            if not any(
                isinstance(item, dict) and str(item.get("expert_id") or "").strip() == normalized_expert_id
                for item in assignments
            ):
                return False

        normalized_project_id = str(project_id or "").strip()
        if normalized_project_id and str(task.get("project_id") or "").strip() != normalized_project_id:
            return False

        if ai_involved is not None:
            ai_flag = bool(task.get("ai_involved") or task.get("ai_initial_feature_count") or task.get("ai_initial_features"))
            if ai_flag != bool(ai_involved):
                return False

        return True

    window_start, window_end = _parse_time_window()

    with _task_storage_context() as data:
        _cleanup_tasks(data)
        tasks = list(data.values())

    items = []
    for task in tasks:
        _ensure_task_schema(task)

        if not _match_scope(task):
            continue

        mapped_status = _map_status(task.get("workflow_status"))

        if window_start or window_end:
            filter_time = _extract_filter_time(task, mapped_status)
            if not filter_time:
                continue
            if window_start and filter_time < window_start:
                continue
            if window_end and filter_time > window_end:
                continue

        if not _match_filters(task, mapped_status):
            continue

        active_assignments = _get_active_assignments(task)
        round_no = task.get("current_round", 1)
        round_key = _get_round_key(round_no)
        submitted = sum(
            1 for assignment in active_assignments
            if assignment.get("round_submissions", {}).get(round_key)
        )

        my_invite_token = None
        if "expert" in roles:
            for assignment in active_assignments:
                if _assignment_matches_user(assignment, current_user):
                    my_invite_token = assignment.get("invite_token")
                    break

        items.append({
            "id": task.get("task_id"),
            "name": task.get("name"),
            "status": mapped_status,
            "workflowStatus": task.get("workflow_status"),
            "aiStatus": task.get("ai_status") or task.get("status"),
            "progress": task.get("progress"),
            "message": task.get("message"),
            "currentRound": task.get("current_round"),
            "maxRounds": task.get("max_rounds"),
            "creatorName": task.get("creator_name"),
            "createdAt": task.get("created_at"),
            "frozenAt": task.get("frozen_at"),
            "systems": task.get("systems", []),
            "ownerSnapshot": task.get("owner_snapshot"),
            "evaluationProgress": {
                "submitted": submitted,
                "total": len(active_assignments)
            },
            "reportVersions": task.get("report_versions", []),
            "myInviteToken": my_invite_token,
        })

    items.sort(key=lambda x: str(x.get("createdAt") or ""), reverse=True)

    if group_by_status:
        pending_items = [item for item in items if item.get("status") == "pending"]
        in_progress_items = [item for item in items if item.get("status") == "in_progress"]
        completed_items = [item for item in items if item.get("status") in {"completed", "closed"}]

        def _paginate(group_items: List[Dict[str, Any]]) -> Dict[str, Any]:
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            return {
                "total": len(group_items),
                "items": group_items[start_idx:end_idx],
            }

        return {
            "task_groups": {
                "pending": _paginate(pending_items),
                "in_progress": _paginate(in_progress_items),
                "completed": _paginate(completed_items),
            },
            "page": page,
            "page_size": page_size,
        }

    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paged_items = items[start_idx:end_idx]

    return {
        "code": 200,
        "message": "success",
        "data": paged_items,
        "total": len(items),
        "page": page,
        "page_size": page_size,
    }


@router.get("/tasks/{task_id}/ai-progress")
async def get_task_ai_progress(
    task_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """获取AI评估进度"""
    task = _get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    _ensure_task_schema(task)

    roles = current_user.get("roles", [])
    has_access = False
    if "admin" in roles:
        has_access = True
    if not has_access and "manager" in roles:
        try:
            _ensure_manager_access(task, current_user)
            has_access = True
        except HTTPException:
            pass
    if not has_access and "expert" in roles:
        for assignment in _get_active_assignments(task):
            if _assignment_matches_user(assignment, current_user):
                has_access = True
                break
    if not has_access:
        raise HTTPException(status_code=403, detail="无权访问该任务")

    return {
        "code": 200,
        "message": "success",
        "data": {
            "taskId": task.get("task_id"),
            "status": task.get("status"),
            "aiStatus": task.get("ai_status") or task.get("status"),
            "progress": task.get("progress", 0),
            "message": task.get("message"),
            "error": task.get("error"),
            "createdAt": task.get("created_at"),
            "documentName": task.get("filename"),
            "workflowStatus": task.get("workflow_status"),
        }
    }


@router.get("/tasks/{task_id}")
async def get_task_detail_v2(
    task_id: str,
    current_user: Dict[str, Any] = Depends(require_roles(["admin", "manager", "expert"]))
):
    """获取任务详情（v2）"""
    with _task_storage_context() as data:
        task = data.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        _ensure_task_schema(task)
        _ensure_feature_ids(task)

    active_assignments = _get_active_assignments(task)
    round_no = task.get("current_round", 1)
    round_key = _get_round_key(round_no)
    submitted = sum(
        1 for assignment in active_assignments
        if assignment.get("round_submissions", {}).get(round_key)
    )
    systems_data = task.get("systems_data") if isinstance(task.get("systems_data"), dict) else {}
    feature_count = 0
    for features in systems_data.values():
        if isinstance(features, list):
            feature_count += len(features)
    if not feature_count and isinstance(task.get("features"), list):
        feature_count = len(task.get("features"))

    task_remark = str(task.get("remark") or "").strip()
    if not task_remark:
        task_remark = str(task.get("last_ai_remark") or "").strip()

    assignments_payload = []
    for assignment in task.get("expert_assignments", []):
        invite_token = assignment.get("invite_token")
        assignments_payload.append({
            **assignment,
            "invite_link": f"/evaluate/{task_id}?token={invite_token}" if invite_token else None
        })

    roles = current_user.get("roles", [])
    if "admin" not in roles:
        if "manager" in roles:
            _ensure_manager_access(task, current_user)
        elif "expert" in roles:
            if not _expert_has_task_access(task, current_user):
                raise HTTPException(status_code=403, detail="无权访问该任务")

    return {
        "code": 200,
        "message": "success",
        "data": {
            "id": task.get("task_id"),
            "name": task.get("name"),
            "description": task.get("description"),
            "status": task.get("workflow_status"),
            "aiStatus": task.get("ai_status") or task.get("status"),
            "currentRound": task.get("current_round"),
            "maxRounds": task.get("max_rounds"),
            "creatorName": task.get("creator_name"),
            "createdAt": task.get("created_at"),
            "documentName": task.get("filename"),
            "systems": task.get("systems", []),
            "featureCount": feature_count,
            "remark": task_remark,
            "targetSystemMode": task.get("target_system_mode"),
            "targetSystemName": task.get("target_system_name"),
            "targetSystemDisplay": _target_system_display(task),
            "expertAssignments": assignments_payload,
            "evaluationProgress": {
                "submitted": submitted,
                "total": len(active_assignments)
            },
            "reportVersions": task.get("report_versions", []),
            "deviations": task.get("deviations", {})
        }
    }


@router.post("/tasks/{task_id}/submit-to-admin")
async def submit_to_admin(
    task_id: str,
    current_user: Dict[str, Any] = Depends(require_roles(["manager"]))
):
    """项目经理提交给管理员"""
    with _task_storage_context() as data:
        task = data.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        _ensure_task_schema(task)
        _ensure_manager_access(task, current_user)
        if task.get("workflow_status") != "draft":
            raise HTTPException(status_code=400, detail="当前状态不可提交")
        task["workflow_status"] = "awaiting_assignment"
        task["submitted_to_admin_at"] = datetime.now().isoformat()

    create_notification(
        title="任务待分配",
        content=f"任务【{task.get('name', task_id)}】已提交，等待管理员分配专家。",
        notify_type="task_assignment",
        roles=["admin"]
    )

    return {"code": 200, "message": "success"}


@router.post("/tasks/{task_id}/assign-experts")
async def assign_experts(
    task_id: str,
    request: AssignExpertsRequest,
    current_user: Dict[str, Any] = Depends(require_roles(["admin"]))
):
    """管理员分配专家"""
    with _task_storage_context() as data:
        task = data.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        _ensure_task_schema(task)
        _ensure_feature_ids(task)

        if not request.expert_ids:
            raise HTTPException(status_code=400, detail="expertIds不能为空")
        raw_expert_ids = [str(item).strip() for item in request.expert_ids if str(item).strip()]
        if len(raw_expert_ids) != 3:
            raise HTTPException(status_code=400, detail="必须分配3位专家")
        if len(set(raw_expert_ids)) != 3:
            raise HTTPException(status_code=400, detail="专家不能重复")

        users = user_service.list_users()
        resolved_users: List[Dict[str, Any]] = []
        for expert_id in raw_expert_ids:
            user = _resolve_user_for_assignment(users, expert_id)
            if not user:
                raise HTTPException(status_code=400, detail=f"专家账号不存在: {expert_id}")
            if "expert" not in (user.get("roles") or []):
                raise HTTPException(status_code=400, detail=f"账号不是专家: {user.get('username') or expert_id}")
            if not user.get("is_active"):
                raise HTTPException(status_code=400, detail=f"专家账号已停用: {user.get('username') or expert_id}")
            if not bool(user.get("on_duty", True)):
                raise HTTPException(status_code=400, detail=f"专家当前休假，无法分配: {user.get('username') or expert_id}")
            resolved_users.append(user)

        assignments = []
        for user in resolved_users:
            token = uuid.uuid4().hex
            username = user.get("username") or user.get("id")
            display_name = user.get("display_name") or username
            assignments.append({
                "assignment_id": f"assign_{uuid.uuid4().hex[:8]}",
                "expert_id": username,
                "expert_name": display_name,
                "invite_token": token,
                "status": "invited",
                "created_at": datetime.now().isoformat(),
                "round_submissions": {}
            })

        task["expert_assignments"] = assignments
        task["workflow_status"] = "evaluating"
        task["current_round"] = 1
        task.setdefault("round_feature_ids", {})["1"] = _get_round_feature_ids(task, 1)

    for assignment in assignments:
        create_notification(
            title="专家邀请",
            content=f"您有新的评估任务：{task.get('name', task_id)}，请及时完成评估。",
            notify_type="expert_invite",
            user_ids=[item for item in [assignment.get("expert_id"), assignment.get("expert_name")] if item]
        )

    invite_links = [
        {
            "expertId": assignment["expert_id"],
            "expertName": assignment["expert_name"],
            "link": f"/evaluate/{task_id}?token={assignment['invite_token']}",
            "token": assignment["invite_token"],
            "assignmentId": assignment["assignment_id"]
        }
        for assignment in assignments
    ]

    return {
        "code": 200,
        "message": "success",
        "data": {
            "inviteLinks": invite_links
        }
    }


@router.post("/tasks/{task_id}/invites/{assignment_id}/resend")
async def resend_invite(
    task_id: str,
    assignment_id: str,
    current_user: Dict[str, Any] = Depends(require_roles(["admin"]))
):
    with _task_storage_context() as data:
        task = data.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        _ensure_task_schema(task)

        assignment = None
        for item in task.get("expert_assignments", []):
            if item.get("assignment_id") == assignment_id:
                assignment = item
                break
        if not assignment:
            raise HTTPException(status_code=404, detail="分配记录不存在")
        if assignment.get("status") == "revoked":
            raise HTTPException(status_code=400, detail="邀请已撤销")

        assignment.setdefault("invalid_tokens", []).append(assignment.get("invite_token"))
        assignment["invite_token"] = uuid.uuid4().hex
        assignment["last_sent_at"] = datetime.now().isoformat()

        link = f"/evaluate/{task_id}?token={assignment['invite_token']}"

    return {
        "code": 200,
        "data": {
            "invite_link": link,
            "invite_token": assignment["invite_token"]
        }
    }


@router.post("/tasks/{task_id}/invites/{assignment_id}/revoke")
async def revoke_invite(
    task_id: str,
    assignment_id: str,
    current_user: Dict[str, Any] = Depends(require_roles(["admin"]))
):
    with _task_storage_context() as data:
        task = data.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        _ensure_task_schema(task)

        assignment = None
        for item in task.get("expert_assignments", []):
            if item.get("assignment_id") == assignment_id:
                assignment = item
                break
        if not assignment:
            raise HTTPException(status_code=404, detail="分配记录不存在")

        assignment.setdefault("invalid_tokens", []).append(assignment.get("invite_token"))
        assignment["status"] = "revoked"
        assignment["revoked_at"] = datetime.now().isoformat()

    return {"code": 200, "message": "撤销成功"}


@router.put("/tasks/{task_id}/archive")
async def archive_task(
    task_id: str,
    current_user: Dict[str, Any] = Depends(require_roles(["admin", "manager", "expert"]))
):
    with _task_storage_context() as data:
        task = data.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        _ensure_task_schema(task)
        _ensure_manager_access(task, current_user)
        task["workflow_status"] = "archived"
        task["archived_at"] = datetime.now().isoformat()
    return {"code": 200, "message": "success"}


@router.delete("/tasks/{task_id}")
async def delete_task_v2(
    task_id: str,
    current_user: Dict[str, Any] = Depends(require_roles(["admin", "manager", "expert"]))
):
    with _task_storage_context() as data:
        task = data.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        _ensure_task_schema(task)
        if task.get("workflow_status") not in ("draft", "awaiting_assignment"):
            raise HTTPException(status_code=400, detail="当前状态不可删除")
        if "admin" not in current_user.get("roles", []):
            _ensure_manager_access(task, current_user)
        data.pop(task_id, None)
    return {"code": 200, "message": "success"}


@router.get("/tasks/{task_id}/reports")
async def list_report_versions(
    task_id: str,
    current_user: Dict[str, Any] = Depends(require_roles(["admin", "manager", "expert"]))
):
    task = _get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    _ensure_task_schema(task)

    roles = current_user.get("roles", [])
    if "admin" not in roles:
        if "manager" in roles:
            _ensure_manager_access(task, current_user)
        elif "expert" in roles:
            if not _expert_has_task_access(task, current_user):
                raise HTTPException(status_code=403, detail="无权访问该任务")

    return {
        "code": 200,
        "data": {
            "task_id": task_id,
            "reports": task.get("report_versions", [])
        }
    }


@router.get("/reports/{report_id}/export")
async def export_report_excel(
    report_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_roles(["admin", "manager"]))
):
    matched_task = None
    with _task_store_lock():
        for task in list(_load_task_storage_unlocked().values()):
            _ensure_task_schema(task)
            if any(str(item.get("id")) == str(report_id) for item in task.get("report_versions", []) if isinstance(item, dict)):
                matched_task = task
                break

    if not matched_task:
        return build_error_response(
            request=request,
            status_code=404,
            error_code="REPORT_003",
            message="报告不存在",
            details={"report_id": report_id},
        )

    if "admin" not in (current_user.get("roles") or []):
        try:
            _ensure_manager_access(matched_task, current_user)
        except HTTPException:
            return build_error_response(
                request=request,
                status_code=403,
                error_code="AUTH_001",
                message="权限不足",
                details={"reason": "无权导出该报告", "report_id": report_id},
            )

    try:
        from backend.utils.excel_generator import excel_generator
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_name = f"{matched_task.get('task_id')}_{report_id}_{timestamp}.xlsx"
        output_path = os.path.join(settings.REPORT_DIR, output_name)
        file_path = excel_generator.export_three_point_report(matched_task, output_path=output_path)
    except Exception as exc:
        logger.exception("导出评估报告Excel失败 report_id=%s", report_id)
        return build_error_response(
            request=request,
            status_code=500,
            error_code="REPORT_004",
            message="导出失败",
            details={"report_id": report_id, "error": str(exc)},
        )

    return FileResponse(
        path=file_path,
        filename=os.path.basename(file_path),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@router.get("/tasks/{task_id}/high-deviation")
async def get_task_high_deviation(
    task_id: str,
    current_user: Dict[str, Any] = Depends(require_roles(["admin", "manager", "expert"]))
):
    task = _get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    _ensure_task_schema(task)
    _ensure_feature_ids(task)

    roles = current_user.get("roles", [])
    if "admin" not in roles:
        if "manager" in roles:
            _ensure_manager_access(task, current_user)
        elif "expert" in roles:
            if not _expert_has_task_access(task, current_user):
                raise HTTPException(status_code=403, detail="无权访问该任务")

    deviations = task.get("deviations", {})
    if not deviations:
        return {"code": 200, "data": {"round": None, "isOfficial": False, "items": []}}

    rounds = []
    for key in deviations.keys():
        try:
            rounds.append(int(key))
        except (TypeError, ValueError):
            continue
    if not rounds:
        return {"code": 200, "data": {"round": None, "isOfficial": False, "items": []}}
    latest_round = max(rounds)
    round_key = _get_round_key(latest_round)

    deviation_map = deviations.get(round_key, {})
    high_ids = task.get("high_deviation_features", {}).get(round_key, [])
    if not high_ids:
        high_ids = [fid for fid, dev in deviation_map.items() if dev > DEVIATION_THRESHOLD]

    means_map = task.get("round_means", {}).get(round_key, {})
    features_by_id = _build_feature_index(task)

    items = []
    for fid in high_ids:
        feature = features_by_id.get(fid, {})
        items.append({
            "id": fid,
            "system": feature.get("系统") or feature.get("system") or feature.get("system_name"),
            "module": feature.get("功能模块") or feature.get("module"),
            "name": feature.get("功能点") or feature.get("name"),
            "aiEstimatedDays": _get_ai_estimate(feature),
            "meanDays": means_map.get(fid),
            "deviation": deviation_map.get(fid),
        })
    items.sort(key=lambda item: item.get("deviation") or 0, reverse=True)

    is_official = any(item.get("round") == latest_round for item in task.get("report_versions", []))

    return {
        "code": 200,
        "data": {
            "round": latest_round,
            "isOfficial": is_official,
            "items": items
        }
    }


@router.get("/tasks/{task_id}/reports/{report_id}")
async def download_report_version(
    task_id: str,
    report_id: str,
    current_user: Dict[str, Any] = Depends(require_roles(["admin", "manager", "expert"]))
):
    task = _get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    _ensure_task_schema(task)

    roles = current_user.get("roles", [])
    if "admin" not in roles:
        if "manager" in roles:
            _ensure_manager_access(task, current_user)
        elif "expert" in roles:
            if not _expert_has_task_access(task, current_user):
                raise HTTPException(status_code=403, detail="无权访问该任务")

    report = next((item for item in task.get("report_versions", []) if item.get("id") == report_id), None)
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")
    report_path = report.get("file_path")
    if not report_path or not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="报告文件不存在")
    return FileResponse(
        path=report_path,
        filename=os.path.basename(report_path),
        media_type="application/pdf"
    )


@router.get("/tasks/{task_id}/report")
async def download_latest_report(
    task_id: str,
    request: Request,
    format: str = Query("pdf"),
    current_user: Dict[str, Any] = Depends(require_roles(["admin", "manager", "expert"]))
):
    normalized_format = str(format or "pdf").strip().lower()
    if normalized_format not in {"pdf", "docx"}:
        return build_error_response(
            request=request,
            status_code=400,
            error_code="REPORT_002",
            message="报表参数不合法",
            details={"field": "format", "expected": ["pdf"]},
        )
    if normalized_format == "docx":
        return build_error_response(
            request=request,
            status_code=400,
            error_code="REPORT_002",
            message="报表参数不合法",
            details={"field": "format", "supported": ["pdf"]},
        )

    task = _get_task(task_id)
    if not task:
        return build_error_response(
            request=request,
            status_code=404,
            error_code="TASK_001",
            message="评估任务不存在",
            details={"task_id": task_id},
        )

    _ensure_task_schema(task)

    roles = current_user.get("roles", [])
    if "expert" in roles and "admin" not in roles and "manager" not in roles:
        assigned = any(_assignment_matches_user(item, current_user) for item in _get_active_assignments(task))
        if not assigned:
            return build_error_response(
                request=request,
                status_code=403,
                error_code="AUTH_001",
                message="权限不足",
                details={"reason": "专家未参与该任务", "task_id": task_id},
            )
    else:
        try:
            _ensure_manager_access(task, current_user)
        except HTTPException:
            return build_error_response(
                request=request,
                status_code=403,
                error_code="AUTH_001",
                message="权限不足",
                details={"reason": "无权访问该任务", "task_id": task_id},
            )

    if task.get("workflow_status") != "completed" or not task.get("report_versions"):
        return build_error_response(
            request=request,
            status_code=400,
            error_code="REPORT_003",
            message="任务未完成或报告未生成，请稍后重试",
            details={"task_id": task_id},
        )

    latest = sorted(
        task.get("report_versions", []),
        key=lambda item: (item.get("round", 0), item.get("version", 0))
    )[-1]
    report_path = latest.get("file_path")
    if not report_path or not os.path.exists(report_path):
        return build_error_response(
            request=request,
            status_code=400,
            error_code="REPORT_003",
            message="任务未完成或报告未生成，请稍后重试",
            details={"task_id": task_id},
        )

    return FileResponse(
        path=report_path,
        filename=os.path.basename(report_path),
        media_type="application/pdf"
    )


@router.get("/tasks/{task_id}/document")
async def download_task_document(
    task_id: str,
    current_user: Dict[str, Any] = Depends(require_roles(["admin", "manager", "expert"]))
):
    task = _get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    _ensure_task_schema(task)

    roles = current_user.get("roles", [])
    if "admin" not in roles:
        if "manager" in roles:
            _ensure_manager_access(task, current_user)
        elif "expert" in roles:
            if not _expert_has_task_access(task, current_user):
                raise HTTPException(status_code=403, detail="无权访问该任务")

    file_path = task.get("file_path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="需求文档不存在")

    real_upload_dir = os.path.realpath(settings.UPLOAD_DIR)
    real_file_path = os.path.realpath(file_path)
    if not real_file_path.startswith(real_upload_dir):
        logger.error(f"非法路径访问: {file_path}")
        raise HTTPException(status_code=403, detail="非法访问")

    return FileResponse(
        path=real_file_path,
        filename=os.path.basename(file_path),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


@router.post("/tasks/{task_id}/estimate")
async def estimate_task_workload(
    task_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_roles(["manager"])),
):
    with _task_storage_context() as data:
        task = data.get(task_id)
        if not task:
            return build_error_response(
                request=request,
                status_code=404,
                error_code="TASK_001",
                message="评估任务不存在",
                details={"task_id": task_id},
            )

        _ensure_task_schema(task)
        _ensure_feature_ids(task)

        try:
            _ensure_manager_access(task, current_user)
        except HTTPException:
            return build_error_response(
                request=request,
                status_code=403,
                error_code="AUTH_001",
                message="权限不足",
                details={"reason": "仅任务创建者可触发估算", "task_id": task_id},
            )

        systems_data = task.get("systems_data") if isinstance(task.get("systems_data"), dict) else {}
        features_payload: List[Dict[str, Any]] = []
        degraded = False

        from backend.agent.work_estimation_agent import work_estimation_agent
        profile_service = get_system_profile_service()
        estimation_context_map = {
            system_name: profile_service.build_estimation_context(system_name)
            for system_name in systems_data.keys()
        }

        for system_name, features in systems_data.items():
            if not isinstance(features, list):
                continue
            context_payload = estimation_context_map.get(system_name, {})
            for feature in features:
                if not isinstance(feature, dict):
                    continue

                fallback = _to_float_or_none(feature.get("original_estimate"))
                if fallback is None or fallback <= 0:
                    fallback = _get_ai_estimate(feature)
                if fallback <= 0:
                    fallback = 1.0

                rule_context = build_feature_rule_context(task, feature)
                requirement_context = str(task.get("requirement_content") or "").strip()

                try:
                    detail = work_estimation_agent.estimate_three_point_for_feature(
                        feature,
                        system_context=str(context_payload.get("text") or "").strip(),
                        requirement_context=requirement_context,
                        rule_context=rule_context,
                    )
                except Exception as exc:
                    logger.warning("任务估算降级 task=%s feature=%s error=%s", task_id, feature.get("id"), exc)
                    degraded = True
                    detail = {
                        "optimistic": None,
                        "most_likely": None,
                        "pessimistic": None,
                        "expected": round(float(fallback), 2),
                        "reasoning": None,
                        "original_estimate": round(float(fallback), 2),
                    }
                detail["profile_context_used"] = bool(context_payload.get("profile_context_used"))
                detail["context_source"] = str(context_payload.get("context_source") or "none").strip() or "none"

                # 兼容旧返回或测试桩：若未回传 original_estimate，则回退到 baseline。
                resolved_original_estimate = _to_float_or_none(detail.get("original_estimate"))
                if resolved_original_estimate is None or resolved_original_estimate <= 0:
                    resolved_original_estimate = round(float(fallback), 2)

                feature["optimistic"] = detail.get("optimistic")
                feature["most_likely"] = detail.get("most_likely")
                feature["pessimistic"] = detail.get("pessimistic")
                feature["expected"] = detail.get("expected")
                feature["reasoning"] = detail.get("reasoning")
                feature["original_estimate"] = resolved_original_estimate
                feature["预估人天"] = detail.get("expected")
                feature["profile_context_used"] = bool(detail.get("profile_context_used"))
                feature["context_source"] = str(detail.get("context_source") or "none").strip() or "none"
                feature["rule_context"] = rule_context
                feature["requirement_context"] = requirement_context

                features_payload.append(
                    {
                        "id": feature.get("id"),
                        "name": feature.get("功能点") or feature.get("name") or "",
                        "system": system_name,
                        "optimistic": detail.get("optimistic"),
                        "most_likely": detail.get("most_likely"),
                        "pessimistic": detail.get("pessimistic"),
                        "expected": detail.get("expected"),
                        "reasoning": detail.get("reasoning"),
                        "original_estimate": resolved_original_estimate,
                        "profile_context_used": bool(detail.get("profile_context_used")),
                        "context_source": str(detail.get("context_source") or "none").strip() or "none",
                        "rule_context": rule_context,
                    }
                )
            profile_service.record_estimation_context_artifact(
                system_name=system_name,
                task_id=task_id,
                features=[feature for feature in features if isinstance(feature, dict)],
                context_payload=context_payload,
                actor=current_user,
                trigger="task_estimate_api",
            )

    result: Dict[str, Any] = {"degraded": degraded, "features": features_payload}
    if degraded:
        result["code"] = "LLM_ESTIMATION_DEGRADED"
    return result


@router.get("/evaluation/{task_id}")
async def get_evaluation_data(
    task_id: str,
    token: Optional[str] = None,
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_roles(["expert"]))
):
    """获取评估数据（v2）"""
    with _task_storage_context() as data:
        task = data.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        _ensure_task_schema(task)
        _ensure_feature_ids(task)

        if task.get("workflow_status") not in ("evaluating", "completed"):
            raise HTTPException(status_code=400, detail="任务未进入评估阶段")

        invite_token = _extract_invite_token(token, request)
        assignment = _get_assignment_by_token(task, invite_token)
        if not assignment:
            raise HTTPException(status_code=403, detail="无效的邀请token")

        round_no = task.get("current_round", 1)
        round_key = _get_round_key(round_no)
        round_feature_ids = set(_get_round_feature_ids(task, round_no))

        draft_data = task.get("evaluation_drafts", {}).get(round_key, {}).get(assignment["expert_id"], {})
        submitted = bool(assignment.get("round_submissions", {}).get(round_key))

        systems_payload = {}
        for system_name, features in (task.get("systems_data") or {}).items():
            filtered = []
            for feature in features or []:
                if feature.get("id") not in round_feature_ids:
                    continue
                my_value = None
                if draft_data and feature.get("id") in draft_data:
                    my_value = draft_data.get(feature.get("id"))
                elif submitted:
                    my_value = task.get("evaluations", {}).get(round_key, {}).get(assignment["expert_id"], {}).get(feature.get("id"))
                filtered.append(_build_feature_response(feature, my_value))
            if filtered:
                systems_payload[system_name] = filtered

        high_deviation = []
        if round_no > 1:
            high_deviation = task.get("high_deviation_features", {}).get(_get_round_key(round_no - 1), [])

    return {
        "code": 200,
        "message": "success",
        "data": {
            "task": {
                "id": task.get("task_id"),
                "name": task.get("name"),
                "status": task.get("workflow_status"),
                "currentRound": round_no,
                "systems": list(systems_payload.keys())
            },
            "features": systems_payload,
            "myEvaluation": {
                "hasSubmitted": submitted,
                "submittedRound": round_no if submitted else 0,
                "draftData": draft_data or {}
            },
            "highDeviationFeatures": high_deviation
        }
    }


@router.post("/evaluation/{task_id}/draft")
async def save_evaluation_draft(
    task_id: str,
    payload: EvaluationDraftRequest,
    token: Optional[str] = None,
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_roles(["expert"]))
):
    """保存评估草稿"""
    with _task_storage_context() as data:
        task = data.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        _ensure_task_schema(task)
        _ensure_feature_ids(task)

        invite_token = _extract_invite_token(token, request)
        assignment = _get_assignment_by_token(task, invite_token)
        if not assignment:
            raise HTTPException(status_code=403, detail="无效的邀请token")

        round_no = task.get("current_round", 1)
        if payload.round != round_no:
            raise HTTPException(status_code=400, detail="轮次不匹配")
        round_key = _get_round_key(round_no)

        task.setdefault("evaluation_drafts", {}).setdefault(round_key, {}).setdefault(assignment["expert_id"], {})
        task["evaluation_drafts"][round_key][assignment["expert_id"]].update(payload.evaluations or {})

    return {"code": 200, "message": "success"}


@router.post("/evaluation/{task_id}/submit")
async def submit_evaluation(
    task_id: str,
    payload: EvaluationSubmitRequest,
    token: Optional[str] = None,
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_roles(["expert"]))
):
    """提交评估"""
    task_name = None
    round_no = None
    with _task_storage_context() as data:
        task = data.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        _ensure_task_schema(task)
        _ensure_feature_ids(task)

        invite_token = _extract_invite_token(token, request)
        assignment = _get_assignment_by_token(task, invite_token)
        if not assignment:
            raise HTTPException(status_code=403, detail="无效的邀请token")

        round_no = task.get("current_round", 1)
        if payload.round != round_no:
            raise HTTPException(status_code=400, detail="轮次不匹配")
        round_key = _get_round_key(round_no)

        round_feature_ids = _get_round_feature_ids(task, round_no)
        features_by_id = _build_feature_index(task)

        evaluation_map = {}
        for fid in round_feature_ids:
            if fid in payload.evaluations and payload.evaluations[fid] is not None:
                evaluation_map[fid] = payload.evaluations[fid]
            else:
                ai_value = _get_ai_estimate(features_by_id.get(fid, {}))
                evaluation_map[fid] = ai_value

        task.setdefault("evaluations", {}).setdefault(round_key, {})[assignment["expert_id"]] = evaluation_map
        assignment.setdefault("round_submissions", {})[round_key] = datetime.now().isoformat()
        assignment["status"] = "submitted"
        expert_name = str(assignment.get("expert_name") or assignment.get("expert_id") or "专家")
        _prepend_task_remark(task, f"专家：{expert_name} 提交第{round_no}轮评估")

        # 清理草稿
        if task.get("evaluation_drafts", {}).get(round_key, {}).get(assignment["expert_id"]):
            task["evaluation_drafts"][round_key].pop(assignment["expert_id"], None)

        active_assignments = _get_active_assignments(task)
        all_submitted = all(
            item.get("round_submissions", {}).get(round_key) for item in active_assignments
        ) if active_assignments else False

        if all_submitted:
            _finalize_round(task, round_no)

        task_name = task.get("name") or task.get("task_id")

    if task_name and round_no:
        try:
            from backend.api.profile_routes import record_activity
            record_activity(
                current_user,
                "submit_evaluation",
                f"提交评估：{task_name} 第{round_no}轮"
            )
        except Exception:
            logger.warning("记录评估提交日志失败", exc_info=True)

    return {
        "code": 200,
        "message": "评估已提交",
        "data": {
            "round": payload.round,
            "submittedAt": assignment.get("round_submissions", {}).get(_get_round_key(payload.round))
        }
    }


@router.post("/evaluation/{task_id}/withdraw")
async def withdraw_evaluation(
    task_id: str,
    token: Optional[str] = None,
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_roles(["expert"]))
):
    """撤回评估（报告未生成前）"""
    with _task_storage_context() as data:
        task = data.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        _ensure_task_schema(task)

        invite_token = _extract_invite_token(token, request)
        assignment = _get_assignment_by_token(task, invite_token)
        if not assignment:
            raise HTTPException(status_code=403, detail="无效的邀请token")

        if task.get("workflow_status") == "archived":
            raise HTTPException(status_code=400, detail="任务已归档，无法撤回")

        round_no = _get_withdrawable_round(task, assignment)
        if not round_no:
            raise HTTPException(status_code=400, detail="无可撤回的记录")
        round_key = _get_round_key(round_no)

        if any(rv.get("round") == round_no for rv in task.get("report_versions", [])):
            raise HTTPException(status_code=400, detail="报告已生成，无法撤回")

        evaluations_round = task.get("evaluations", {}).get(round_key, {})
        previous_values = evaluations_round.get(assignment["expert_id"])
        if previous_values:
            task.setdefault("evaluation_drafts", {}).setdefault(round_key, {})[assignment["expert_id"]] = dict(previous_values)
        evaluations_round.pop(assignment["expert_id"], None)

        assignment.get("round_submissions", {}).pop(round_key, None)
        if assignment.get("status") != "revoked":
            assignment["status"] = "invited"

        if task.get("deviations", {}).get(round_key) or task.get("current_round", round_no) > round_no:
            _rollback_round_state(task, round_no)
        elif task.get("workflow_status") != "evaluating":
            task["workflow_status"] = "evaluating"

    return {"code": 200, "message": "撤回成功"}


@router.get("/evaluation/{task_id}/high-deviation")
async def get_high_deviation_features(task_id: str):
    task = _get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    _ensure_task_schema(task)
    round_no = task.get("current_round", 1)
    if round_no <= 1:
        return {"code": 200, "data": []}
    data = task.get("high_deviation_features", {}).get(_get_round_key(round_no - 1), [])
    return {"code": 200, "data": data}


@router.get("/evaluation/{task_id}/progress")
async def get_evaluation_progress(task_id: str):
    task = _get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    _ensure_task_schema(task)
    active_assignments = _get_active_assignments(task)
    round_no = task.get("current_round", 1)
    round_key = _get_round_key(round_no)
    submitted = sum(
        1 for assignment in active_assignments
        if assignment.get("round_submissions", {}).get(round_key)
    )
    return {
        "code": 200,
        "data": {
            "round": round_no,
            "submitted": submitted,
            "total": len(active_assignments),
            "assignments": active_assignments
        }
    }


def _expert_has_task_access(task: Dict[str, Any], current_user: Dict[str, Any]) -> bool:
    return any(_assignment_matches_user(item, current_user) for item in _get_active_assignments(task))


def _compute_expert_deviation_report(task: Dict[str, Any]) -> Dict[str, Any]:
    _ensure_feature_ids(task)
    features_by_id = _build_feature_index(task)
    evaluations = task.get("evaluations") if isinstance(task.get("evaluations"), dict) else {}

    latest_round = None
    for key in evaluations.keys():
        try:
            round_no = int(key)
        except (TypeError, ValueError):
            continue
        if latest_round is None or round_no > latest_round:
            latest_round = round_no

    if latest_round is None:
        return {"summary": {"avg_deviation_pct": 0.0, "direction": "无数据"}, "by_feature": []}

    round_key = str(latest_round)
    round_evaluations = evaluations.get(round_key) or {}

    by_feature = []
    deviation_values = []

    for feature_id, feature in features_by_id.items():
        expert_values = []
        for _, expert_map in round_evaluations.items():
            if not isinstance(expert_map, dict):
                continue
            if feature_id not in expert_map:
                continue
            try:
                expert_values.append(float(expert_map.get(feature_id) or 0.0))
            except (TypeError, ValueError):
                continue

        if not expert_values:
            continue

        expert_mean = round(statistics.mean(expert_values), 2)
        ai_days = round(float(_get_ai_estimate(feature)), 2)
        base = max(expert_mean, 0.1)
        deviation_pct = round((ai_days - expert_mean) / base * 100, 2)
        deviation_values.append(deviation_pct)

        by_feature.append(
            {
                "feature_id": feature_id,
                "description": feature.get("功能点") or feature.get("name") or "",
                "system_name": feature.get("系统") or feature.get("system") or "",
                "ai_days": ai_days,
                "expert_mean_days": expert_mean,
                "deviation_pct": deviation_pct,
            }
        )

    avg_deviation = round(statistics.mean(deviation_values), 2) if deviation_values else 0.0
    direction = "AI低估" if avg_deviation < -10 else "AI高估" if avg_deviation > 10 else "基本一致"

    by_feature.sort(key=lambda item: abs(item.get("deviation_pct") or 0), reverse=True)
    return {
        "summary": {
            "avg_deviation_pct": avg_deviation,
            "direction": direction,
            "round": latest_round,
            "feature_count": len(by_feature),
        },
        "by_feature": by_feature,
    }


@router.post("/internal/tasks/{task_id}/expert-deviations/compute")
async def compute_expert_deviations(
    task_id: str,
    request: Request,
    _auth: Dict[str, Any] = Depends(require_roles(["admin"])),
):
    with _task_storage_context() as data:
        task = data.get(task_id)
        if not task:
            return build_error_response(
                request=request,
                status_code=404,
                error_code="TASK_001",
                message="评估任务不存在",
                details={"task_id": task_id},
            )

        _ensure_task_schema(task)
        report = _compute_expert_deviation_report(task)
        task["expert_deviation_report"] = report

    return {"deviation_report": report}


@router.get("/tasks/{task_id}/expert-deviations")
async def get_expert_deviations(
    task_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_roles(["admin", "manager", "expert"])),
):
    task = _get_task(task_id)
    if not task:
        return build_error_response(
            request=request,
            status_code=404,
            error_code="TASK_001",
            message="评估任务不存在",
            details={"task_id": task_id},
        )

    roles = current_user.get("roles", [])
    if "admin" not in roles:
        if "manager" in roles:
            try:
                _ensure_manager_access(task, current_user)
            except HTTPException:
                return build_error_response(
                    request=request,
                    status_code=403,
                    error_code="AUTH_001",
                    message="权限不足",
                    details={"reason": "无权访问该任务", "task_id": task_id},
                )
        elif "expert" in roles:
            if not _expert_has_task_access(task, current_user):
                return build_error_response(
                    request=request,
                    status_code=403,
                    error_code="AUTH_001",
                    message="权限不足",
                    details={"reason": "专家未参与该任务", "task_id": task_id},
                )

    report = task.get("expert_deviation_report")
    if not isinstance(report, dict):
        report = _compute_expert_deviation_report(task)

    return {"deviation_report": report}


@router.get("/tasks/{task_id}/evaluation")
async def get_task_evaluation_detail(
    task_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_roles(["admin", "manager", "expert"])),
):
    task = _get_task(task_id)
    if not task:
        return build_error_response(
            request=request,
            status_code=404,
            error_code="TASK_001",
            message="评估任务不存在",
            details={"task_id": task_id},
        )

    _ensure_task_schema(task)
    _ensure_feature_ids(task)

    roles = current_user.get("roles", [])
    if "admin" not in roles:
        if "manager" in roles:
            try:
                _ensure_manager_access(task, current_user)
            except HTTPException:
                return build_error_response(
                    request=request,
                    status_code=403,
                    error_code="AUTH_001",
                    message="权限不足",
                    details={"reason": "无权访问该任务", "task_id": task_id},
                )
        elif "expert" in roles:
            if not _expert_has_task_access(task, current_user):
                return build_error_response(
                    request=request,
                    status_code=403,
                    error_code="AUTH_001",
                    message="权限不足",
                    details={"reason": "专家未参与该任务", "task_id": task_id},
                )

    features_payload = []
    systems_data = task.get("systems_data") or {}
    for system_name, features in systems_data.items():
        if not isinstance(features, list):
            continue
        for feature in features:
            if not isinstance(feature, dict):
                continue
            estimation = _extract_estimation_detail(feature)
            features_payload.append(
                {
                    "feature_id": feature.get("id"),
                    "description": feature.get("功能点") or feature.get("description") or feature.get("name") or "",
                    "complexity_level": feature.get("complexity_level") or feature.get("复杂度等级"),
                    "complexity_score": feature.get("complexity_score") or feature.get("复杂度分数"),
                    "estimation_days": estimation["expected"],
                    "optimistic": estimation["optimistic"],
                    "most_likely": estimation["most_likely"],
                    "pessimistic": estimation["pessimistic"],
                    "expected": estimation["expected"],
                    "original_estimate": estimation["original_estimate"],
                    "reasoning": estimation["reasoning"],
                    "estimation_degraded": estimation["degraded"],
                    "profile_context_used": estimation["profile_context_used"],
                    "context_source": estimation["context_source"],
                    "system_name": system_name,
                }
            )

    systems = list((task.get("systems") or systems_data.keys()))
    primary_system = systems[0] if systems else ""
    mapped_status = {
        "draft": "pending",
        "awaiting_assignment": "pending",
        "evaluating": "in_progress",
        "completed": "completed",
        "archived": "closed",
    }.get(str(task.get("workflow_status") or ""), "pending")

    return {
        "task_id": task.get("task_id"),
        "task_name": task.get("name"),
        "system_name": primary_system,
        "status": mapped_status,
        "features": features_payload,
    }


class InternalSystemProfileRetrieveRequest(BaseModel):
    system_name: str
    query: str
    top_k: int = 20


class InternalComplexityEvaluateRequest(BaseModel):
    feature_description: str
    system_context: Optional[Dict[str, Any]] = None


def _calc_profile_completeness_score(profile: Optional[Dict[str, Any]]) -> int:
    if not profile:
        return 0
    completeness = profile.get("completeness") if isinstance(profile.get("completeness"), dict) else {}
    code_score = 30 if bool(completeness.get("code_scan")) else 0
    doc_count = int(completeness.get("documents_normal") or profile.get("document_count") or 0)
    if doc_count >= 11:
        doc_score = 40
    elif doc_count >= 6:
        doc_score = 30
    elif doc_count >= 1:
        doc_score = 10
    else:
        doc_score = 0
    esb_score = 30 if bool(completeness.get("esb")) else 0
    return max(0, min(100, code_score + doc_score + esb_score))


@router.post("/internal/system-profiles/retrieve")
async def retrieve_system_profile_context(
    payload: InternalSystemProfileRetrieveRequest,
    request: Request,
    _auth: Dict[str, Any] = Depends(require_roles(["admin"])),
):
    system_name = str(payload.system_name or "").strip()
    query = str(payload.query or "").strip()
    top_k = max(1, min(int(payload.top_k or 20), 50))

    if not system_name:
        return build_error_response(
            request=request,
            status_code=403,
            error_code="AUTH_001",
            message="权限不足",
            details={"reason": "system_name 必填"},
        )

    profile_service = get_system_profile_service()
    profile = profile_service.get_profile(system_name)
    context_bundle = profile_service.build_context_bundle(system_name, query=query, top_k=top_k)

    return {
        "system_profile": profile or {},
        "context_bundle": context_bundle,
        "capabilities": context_bundle.get("capabilities") if isinstance(context_bundle.get("capabilities"), list) else [],
        "documents": context_bundle.get("documents") if isinstance(context_bundle.get("documents"), list) else [],
        "esb_integrations": context_bundle.get("integrations") if isinstance(context_bundle.get("integrations"), list) else [],
        "completeness_score": int(
            context_bundle.get("completeness_score")
            if context_bundle.get("completeness_score") is not None
            else (
                profile.get("completeness_score")
                if isinstance(profile, dict) and profile.get("completeness_score") is not None
                else _calc_profile_completeness_score(profile)
            )
        ),
        "degraded": bool(context_bundle.get("degraded")),
    }


@router.post("/internal/complexity/evaluate")
async def evaluate_complexity_internal(
    payload: InternalComplexityEvaluateRequest,
    request: Request,
    _auth: Dict[str, Any] = Depends(require_roles(["admin"])),
):
    feature_description = str(payload.feature_description or "").strip()
    if not feature_description:
        return build_error_response(
            request=request,
            status_code=403,
            error_code="AUTH_001",
            message="权限不足",
            details={"reason": "feature_description 必填"},
        )

    context = payload.system_context if isinstance(payload.system_context, dict) else {}
    integration_points = context.get("integration_points") if isinstance(context.get("integration_points"), list) else []

    text = feature_description
    rule_keywords = ["规则", "校验", "审批", "风控", "条件", "分支"]
    integration_keywords = ["接口", "对接", "调用", "系统", "ESB", "MQ", "同步", "异步"]
    tech_keywords = ["重构", "性能", "并发", "迁移", "高可用", "容灾", "改造", "分布式"]

    business_hits = sum(1 for key in rule_keywords if key in text)
    integration_hits = sum(1 for key in integration_keywords if key in text)
    technical_hits = sum(1 for key in tech_keywords if key in text)

    business_rules_score = min(35, 8 + business_hits * 4 + min(len(text) // 120, 5))
    integration_score = min(35, 5 + integration_hits * 5 + min(len(integration_points) * 4, 12))
    technical_difficulty_score = min(30, 6 + technical_hits * 4 + min(len(text) // 160, 4))

    complexity_score = max(0, min(100, business_rules_score + integration_score + technical_difficulty_score))
    if complexity_score >= 71:
        level = "high"
    elif complexity_score >= 41:
        level = "medium"
    else:
        level = "low"

    reasoning = (
        f"规则信号{business_hits}项、集成信号{integration_hits}项、技术信号{technical_hits}项，"
        f"综合得分{complexity_score}。"
    )

    return {
        "complexity_level": level,
        "complexity_score": complexity_score,
        "business_rules_score": business_rules_score,
        "integration_score": integration_score,
        "technical_difficulty_score": technical_difficulty_score,
        "reasoning": reasoning,
    }


class ModificationTraceRequest(BaseModel):
    operation: str
    feature_id: str
    reason_code: str
    notes: Optional[str] = None


def _find_original_ai_reasoning(task: Dict[str, Any], feature_id: str) -> str:
    target_id = str(feature_id or "").strip()
    if not target_id:
        return ""

    for item in task.get("ai_initial_features") or []:
        if not isinstance(item, dict):
            continue
        item_feature_id = str(item.get("feature_id") or (item.get("feature") or {}).get("id") or "").strip()
        if item_feature_id != target_id:
            continue
        reasoning = str(item.get("reasoning") or (item.get("feature") or {}).get("reasoning") or "").strip()
        if not reasoning:
            reasoning = str((item.get("feature") or {}).get("AI分析理由") or "").strip()
        return reasoning
    return ""


def _cleanup_modification_traces(task: Dict[str, Any]) -> None:
    retention_days = int(os.getenv("MOD_TRACE_RETENTION_DAYS", "180"))
    traces = task.get("modification_traces") if isinstance(task.get("modification_traces"), list) else []
    if retention_days <= 0 or not traces:
        task["modification_traces"] = traces
        return

    cutoff = datetime.now() - timedelta(days=retention_days)
    kept = []
    for trace in traces:
        if not isinstance(trace, dict):
            continue
        recorded_at = str(trace.get("recorded_at") or "").strip()
        if not recorded_at:
            continue
        try:
            recorded_dt = datetime.fromisoformat(recorded_at)
        except Exception:
            continue
        if recorded_dt >= cutoff:
            kept.append(trace)
    task["modification_traces"] = kept


@router.post("/tasks/{task_id}/modification-traces")
async def create_modification_trace(
    task_id: str,
    payload: ModificationTraceRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_roles(["manager"])),
):
    operation = str(payload.operation or "").strip().lower()
    feature_id = str(payload.feature_id or "").strip()
    reason_code = str(payload.reason_code or "").strip()
    notes = str(payload.notes or "").strip()

    if operation not in {"delete", "adjust", "add"}:
        return build_error_response(
            request=request,
            status_code=400,
            error_code="TRACE_001",
            message="修改原因不能为空",
            details={"reason": "operation 仅支持 delete/adjust/add"},
        )

    if not feature_id or not reason_code:
        return build_error_response(
            request=request,
            status_code=400,
            error_code="TRACE_001",
            message="修改原因不能为空",
            details={"reason": "feature_id 与 reason_code 必填"},
        )

    now = datetime.now().isoformat()

    with _task_storage_context() as data:
        task = data.get(task_id)
        if not task:
            return build_error_response(
                request=request,
                status_code=404,
                error_code="TASK_001",
                message="评估任务不存在",
                details={"task_id": task_id},
            )

        _ensure_task_schema(task)

        creator_id = str(task.get("creator_id") or "").strip()
        current_user_id = str(current_user.get("id") or "").strip()
        if creator_id and creator_id != current_user_id:
            return build_error_response(
                request=request,
                status_code=403,
                error_code="AUTH_001",
                message="权限不足",
                details={"reason": "仅任务创建者可写入修改轨迹", "task_id": task_id},
            )

        _cleanup_modification_traces(task)

        original_ai_reasoning = _find_original_ai_reasoning(task, feature_id)
        if len(original_ai_reasoning) > 1000:
            original_ai_reasoning = original_ai_reasoning[:1000] + "...(truncated)"

        trace = {
            "trace_id": f"trace_{uuid.uuid4().hex}",
            "operation": operation,
            "feature_id": feature_id,
            "reason_code": reason_code,
            "notes": notes,
            "actor": current_user_id,
            "recorded_at": now,
            "original_ai_reasoning": original_ai_reasoning,
        }

        trace_size = len(json.dumps(trace, ensure_ascii=False).encode("utf-8"))
        if trace_size > 10 * 1024:
            return build_error_response(
                request=request,
                status_code=400,
                error_code="TRACE_001",
                message="修改原因不能为空",
                details={"reason": "单条轨迹超过10KB限制"},
            )

        task.setdefault("modification_traces", []).append(trace)

    return {
        "trace_id": trace["trace_id"],
        "recorded_at": trace["recorded_at"],
    }


@router.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION
    }


@router.post("/tasks/{task_id}/reevaluate")
async def trigger_task_reevaluate(
    task_id: str,
    request: Request,
    payload: Optional[ReevaluateRequest] = None,
    current_user: Dict[str, Any] = Depends(require_roles(["manager"])),
):
    with _task_storage_context() as data:
        task = data.get(task_id)
        if not task:
            return build_error_response(
                request=request,
                status_code=404,
                error_code="task_not_found",
                message="任务不存在",
            )

        _ensure_task_schema(task)
        if task.get("status") not in {"completed"}:
            return build_error_response(
                request=request,
                status_code=409,
                error_code="task_locked",
                message="任务正在评估中，请稍后再试",
            )

        active_job = _find_active_reevaluate_job(task)
        if active_job:
            return {
                "job_id": active_job.get("job_id"),
                "status": active_job.get("status"),
                "created_at": active_job.get("created_at"),
            }

        auto_enabled = bool(settings.V21_AUTO_REEVAL_ENABLED)
        force = bool(payload.force) if payload else False

        should_start_job = auto_enabled or force

        jobs = task.get("reevaluate_jobs") if isinstance(task.get("reevaluate_jobs"), list) else []
        task["reevaluate_jobs"] = jobs

        if not should_start_job:
            if settings.V21_AI_REMARK_ENABLED:
                _apply_ai_remark(task, task.get("modifications") or [])

            created_at = datetime.now().isoformat()
            skipped_job = {
                "job_id": None,
                "status": "skipped",
                "created_at": created_at,
                "requested_by": str(current_user.get("id") or ""),
                "force": force,
            }
            jobs.append(skipped_job)
            return {
                "job_id": None,
                "status": "skipped",
                "created_at": created_at,
            }

        job_id = f"reeval_{uuid.uuid4().hex}"
        created_at = datetime.now().isoformat()
        job = {
            "job_id": job_id,
            "status": "pending",
            "created_at": created_at,
            "requested_by": str(current_user.get("id") or ""),
            "force": force,
        }
        jobs.append(job)

    if settings.V21_AUTO_REEVAL_ENABLED or force:
        executor.submit(_run_reevaluate_job_sync, task_id, job_id)

    return {
        "job_id": job_id,
        "status": "pending",
        "created_at": created_at,
    }


@router.get("/system/config/feature-flags")
async def get_feature_flags(
    request: Request,
    _current_user: Dict[str, Any] = Depends(get_current_user),
):
    """返回 v2.1 功能开关状态。"""
    try:
        return {
            "V21_AUTO_REEVAL_ENABLED": bool(settings.V21_AUTO_REEVAL_ENABLED),
            "V21_AI_REMARK_ENABLED": bool(settings.V21_AI_REMARK_ENABLED),
            "V21_DASHBOARD_MGMT_ENABLED": bool(settings.V21_DASHBOARD_MGMT_ENABLED),
        }
    except Exception as exc:
        return build_error_response(
            request=request,
            status_code=500,
            error_code="FLAG_001",
            message="Feature Flags 查询失败",
            details={"reason": str(exc)},
        )


# 【v2.4】新增 API-009 和 API-010 接口

@router.get("/tasks/{task_id}/ai-output")
async def get_ai_original_output(
    task_id: str,
    current_user: Dict[str, Any] = Depends(require_roles(["admin", "manager", "expert"]))
):
    """
    获取 AI 原始输出快照（API-009）

    Args:
        task_id: 任务ID
        current_user: 当前用户

    Returns:
        Dict: AI 原始输出快照
    """
    task = _get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    _ensure_task_schema(task)

    # 权限校验
    roles = current_user.get("roles", [])
    if "admin" not in roles:
        if "manager" in roles:
            _ensure_manager_access(task, current_user)
        elif "expert" in roles:
            if not _expert_has_task_access(task, current_user):
                raise HTTPException(status_code=403, detail="无权访问该任务")

    ai_original_output = task.get("ai_original_output") or {
        "system_recognition": None,
        "feature_split": None,
        "work_estimation": None
    }

    return {
        "code": 200,
        "data": {
            "task_id": task_id,
            "ai_original_output": ai_original_output
        }
    }


@router.get("/tasks/{task_id}/correction-diff")
async def get_correction_diff(
    task_id: str,
    current_user: Dict[str, Any] = Depends(require_roles(["admin", "manager", "expert"]))
):
    """
    获取 PM 修正 diff（API-010）

    Args:
        task_id: 任务ID
        current_user: 当前用户

    Returns:
        Dict: PM 修正 diff
    """
    task = _get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    _ensure_task_schema(task)

    # 权限校验
    roles = current_user.get("roles", [])
    if "admin" not in roles:
        if "manager" in roles:
            _ensure_manager_access(task, current_user)
        elif "expert" in roles:
            if not _expert_has_task_access(task, current_user):
                raise HTTPException(status_code=403, detail="无权访问该任务")

    pm_correction_diff = task.get("pm_correction_diff") or {}

    return {
        "code": 200,
        "data": {
            "task_id": task_id,
            "pm_correction_diff": pm_correction_diff
        }
    }
