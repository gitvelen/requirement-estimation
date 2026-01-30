"""
部门清单服务（文件存储版本）
用于提供“固定下拉”的部门选项。
"""

from __future__ import annotations

import json
import logging
import os
import threading
from contextlib import contextmanager
from typing import List

from backend.config.config import settings

try:
    import fcntl

    FCNTL_AVAILABLE = True
except ImportError:
    FCNTL_AVAILABLE = False

logger = logging.getLogger(__name__)

DEPARTMENT_STORE_PATH = os.path.join(settings.REPORT_DIR, "departments.json")
DEPARTMENT_STORE_LOCK_PATH = f"{DEPARTMENT_STORE_PATH}.lock"
_department_lock = threading.RLock()


@contextmanager
def _department_store_lock():
    if FCNTL_AVAILABLE:
        os.makedirs(os.path.dirname(DEPARTMENT_STORE_LOCK_PATH), exist_ok=True)
        with open(DEPARTMENT_STORE_LOCK_PATH, "a") as lock_file:
            fcntl.flock(lock_file, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file, fcntl.LOCK_UN)
    else:
        with _department_lock:
            yield


def _load_departments_unlocked() -> List[str]:
    if not os.path.exists(DEPARTMENT_STORE_PATH):
        return []
    try:
        with open(DEPARTMENT_STORE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return [str(item) for item in data if item]
            return []
    except Exception as e:
        logger.warning(f"读取部门清单失败: {e}")
        return []


def _save_departments_unlocked(departments: List[str]) -> None:
    os.makedirs(os.path.dirname(DEPARTMENT_STORE_PATH), exist_ok=True)
    tmp_path = f"{DEPARTMENT_STORE_PATH}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(departments, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, DEPARTMENT_STORE_PATH)


def list_departments() -> List[str]:
    with _department_store_lock():
        departments = _load_departments_unlocked()
    # 输出排序：保持配置顺序即可
    return departments


def save_departments(departments: List[str]) -> List[str]:
    cleaned: List[str] = []
    seen = set()
    for item in departments or []:
        name = str(item).strip()
        if not name:
            continue
        if len(name) > 50:
            name = name[:50]
        if name in seen:
            continue
        seen.add(name)
        cleaned.append(name)

    with _department_store_lock():
        _save_departments_unlocked(cleaned)
    return cleaned

