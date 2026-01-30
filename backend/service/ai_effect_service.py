"""
AI效果指标快照服务（文件存储版本）
"""
import json
import logging
import os
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from backend.config.config import settings
from backend.service.knowledge_service import get_knowledge_service

try:
    import fcntl
    FCNTL_AVAILABLE = True
except ImportError:
    FCNTL_AVAILABLE = False

logger = logging.getLogger(__name__)

SNAPSHOT_PATH = os.path.join(settings.REPORT_DIR, "ai_effect_snapshots.json")
SNAPSHOT_LOCK_PATH = f"{SNAPSHOT_PATH}.lock"
snapshot_lock = threading.RLock()


@contextmanager
def _snapshot_store_lock():
    if FCNTL_AVAILABLE:
        os.makedirs(os.path.dirname(SNAPSHOT_LOCK_PATH), exist_ok=True)
        with open(SNAPSHOT_LOCK_PATH, "a") as lock_file:
            fcntl.flock(lock_file, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file, fcntl.LOCK_UN)
    else:
        with snapshot_lock:
            yield


def _load_snapshots_unlocked() -> List[Dict[str, Any]]:
    if not os.path.exists(SNAPSHOT_PATH):
        return []
    try:
        with open(SNAPSHOT_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        logger.warning(f"读取AI效果快照失败: {e}")
        return []


def _save_snapshots_unlocked(items: List[Dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(SNAPSHOT_PATH), exist_ok=True)
    tmp_path = f"{SNAPSHOT_PATH}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, SNAPSHOT_PATH)


@contextmanager
def _snapshot_context():
    with _snapshot_store_lock():
        items = _load_snapshots_unlocked()
        yield items
        _save_snapshots_unlocked(items)


def _ratio_to_percent(value: float) -> float:
    if value < 0:
        value = 0
    if value > 1:
        value = 1
    return round(value * 100, 2)


def _count_features(task: Dict[str, Any], system_name: Optional[str] = None, module: Optional[str] = None) -> int:
    count = 0
    for sys_name, features in (task.get("systems_data") or {}).items():
        if system_name and sys_name != system_name:
            continue
        for feature in features or []:
            if module and feature.get("功能模块") != module:
                continue
            count += 1
    return count


def _collect_modification_stats(task: Dict[str, Any], system_name: Optional[str] = None, module: Optional[str] = None) -> Dict[str, int]:
    stats = {
        "added": 0,
        "deleted": 0,
        "updated": 0,
        "man_day_modified": 0,
        "field_modified": 0,
        "system_renamed": 0,
        "deleted_systems": 0
    }
    for mod in task.get("modifications", []) or []:
        op = mod.get("operation")
        mod_system = mod.get("system")
        mod_module = mod.get("module")

        if system_name and mod_system != system_name and op != "delete_system":
            continue

        if module and mod_module and mod_module != module:
            continue

        if op == "add":
            stats["added"] += 1
        elif op == "delete":
            stats["deleted"] += 1
        elif op == "delete_system":
            stats["deleted_systems"] += 1
            if not system_name:
                stats["deleted"] += len(mod.get("deleted_features") or [])
        elif op == "rename_system":
            stats["system_renamed"] += 1
        elif op == "update":
            stats["updated"] += 1
            field = mod.get("field")
            if field in ("预估人天", "预估人天数", "预估人天(人天)"):
                stats["man_day_modified"] += 1
            if field in ("业务描述", "输入", "输出", "依赖项"):
                stats["field_modified"] += 1
    return stats


def _compute_metrics(task: Dict[str, Any], system_name: Optional[str] = None, module: Optional[str] = None) -> Dict[str, float]:
    current_features = _count_features(task, system_name=system_name, module=module)
    mod_stats = _collect_modification_stats(task, system_name=system_name, module=module)
    added = mod_stats["added"]
    deleted = mod_stats["deleted"]

    initial_features = current_features + deleted - added
    if initial_features <= 0:
        initial_features = current_features or 1

    man_day_accuracy = _ratio_to_percent(1 - (mod_stats["man_day_modified"] / initial_features))
    feature_retention = _ratio_to_percent(current_features / initial_features)
    field_mod_rate = _ratio_to_percent(mod_stats["field_modified"] / initial_features)
    new_feature_ratio = _ratio_to_percent(added / initial_features)

    # 系统识别准确率（仅任务级别）
    if system_name is None and module is None:
        current_systems = len(task.get("systems_data") or {})
        deleted_systems = mod_stats["deleted_systems"]
        initial_systems = current_systems + deleted_systems
        system_accuracy = _ratio_to_percent(current_systems / initial_systems) if initial_systems else 0
    else:
        system_accuracy = 100.0

    knowledge_hit_rate = 0.0
    try:
        knowledge_service = get_knowledge_service()
        hit_rate = knowledge_service.get_hit_rate(
            task_id=task.get("task_id"),
            system_name=system_name,
            module=module,
            knowledge_type=None
        )
        if hit_rate is not None:
            knowledge_hit_rate = float(hit_rate)
        else:
            knowledge_hit_rate = float(knowledge_service.get_evaluation_metrics().get("hit_rate", 0.0))
    except Exception:
        knowledge_hit_rate = 0.0

    manager_trust = _ratio_to_percent(1 - ((mod_stats["man_day_modified"] + mod_stats["field_modified"]) / initial_features))

    return {
        "man_day_accuracy": man_day_accuracy,
        "feature_retention": feature_retention,
        "field_modification_rate": field_mod_rate,
        "knowledge_hit_rate": knowledge_hit_rate,
        "system_identification_accuracy": system_accuracy,
        "new_feature_ratio": new_feature_ratio,
        "manager_trust": manager_trust,
        "system_rename_rate": _ratio_to_percent(mod_stats["system_renamed"] / (len(task.get("systems_data") or {}) or 1))
    }


def create_snapshots(task: Dict[str, Any], round_no: int) -> List[Dict[str, Any]]:
    created_at = datetime.now().isoformat()
    snapshots: List[Dict[str, Any]] = []

    base_snapshot = {
        "id": f"snap_{uuid.uuid4().hex[:10]}",
        "task_id": task.get("task_id"),
        "round": round_no,
        "system": None,
        "module": None,
        "manager_id": task.get("creator_id"),
        "manager_name": task.get("creator_name"),
        "metrics": _compute_metrics(task),
        "created_at": created_at
    }
    snapshots.append(base_snapshot)

    for system_name in (task.get("systems_data") or {}).keys():
        snapshots.append({
            "id": f"snap_{uuid.uuid4().hex[:10]}",
            "task_id": task.get("task_id"),
            "round": round_no,
            "system": system_name,
            "module": None,
            "manager_id": task.get("creator_id"),
            "manager_name": task.get("creator_name"),
            "metrics": _compute_metrics(task, system_name=system_name),
            "created_at": created_at
        })

    modules = set()
    for features in (task.get("systems_data") or {}).values():
        for feature in features or []:
            module = feature.get("功能模块")
            if module:
                modules.add(module)
    for module in sorted(modules):
        snapshots.append({
            "id": f"snap_{uuid.uuid4().hex[:10]}",
            "task_id": task.get("task_id"),
            "round": round_no,
            "system": None,
            "module": module,
            "manager_id": task.get("creator_id"),
            "manager_name": task.get("creator_name"),
            "metrics": _compute_metrics(task, module=module),
            "created_at": created_at
        })

    with _snapshot_context() as items:
        items.extend(snapshots)

    return snapshots


def list_snapshots() -> List[Dict[str, Any]]:
    with _snapshot_context() as items:
        return list(items)
