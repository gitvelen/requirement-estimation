from __future__ import annotations

import json
import os
import threading
import uuid
from contextlib import contextmanager
from datetime import timedelta
from typing import Any, Dict, List, Optional

try:
    import fcntl

    FCNTL_AVAILABLE = True
except ImportError:  # pragma: no cover
    FCNTL_AVAILABLE = False

from backend.config.config import settings
from backend.utils.time_utils import current_time, current_time_iso, parse_iso_datetime


class RuntimeExecutionService:
    def __init__(
        self,
        store_path: Optional[str] = None,
        latest_status_path: Optional[str] = None,
    ) -> None:
        self.store_path = store_path or os.path.join(settings.REPORT_DIR, "runtime_executions.json")
        self.latest_status_path = latest_status_path or os.path.join(settings.REPORT_DIR, "extraction_tasks.json")
        self.lock_path = f"{self.store_path}.lock"
        self._mutex = threading.RLock()

    @contextmanager
    def _lock(self):
        if FCNTL_AVAILABLE:
            os.makedirs(os.path.dirname(self.lock_path) or ".", exist_ok=True)
            with open(self.lock_path, "a", encoding="utf-8") as lock_file:
                fcntl.flock(lock_file, fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(lock_file, fcntl.LOCK_UN)
        else:
            with self._mutex:
                yield

    def _load_executions_unlocked(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.store_path):
            return []
        with open(self.store_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        return payload if isinstance(payload, list) else []

    def _save_executions_unlocked(self, payload: List[Dict[str, Any]]) -> None:
        os.makedirs(os.path.dirname(self.store_path) or ".", exist_ok=True)
        tmp_path = f"{self.store_path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self.store_path)

    def _load_latest_unlocked(self) -> Dict[str, Any]:
        if not os.path.exists(self.latest_status_path):
            return {}
        with open(self.latest_status_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        return payload if isinstance(payload, dict) else {}

    def _save_latest_unlocked(self, payload: Dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(self.latest_status_path) or ".", exist_ok=True)
        tmp_path = f"{self.latest_status_path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self.latest_status_path)

    def _cleanup_expired(self, executions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        retention_days = int(getattr(settings, "RUNTIME_EXECUTION_RETENTION_DAYS", 180) or 180)
        cutoff = current_time() - timedelta(days=max(retention_days, 1))
        kept: List[Dict[str, Any]] = []
        for item in executions:
            created_at = str(item.get("created_at") or "").strip()
            if not created_at:
                kept.append(item)
                continue
            created_dt = parse_iso_datetime(created_at)
            if created_dt is None:
                kept.append(item)
                continue
            if created_dt >= cutoff:
                kept.append(item)
        return kept

    def _build_latest_summary(self, execution: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "task_id": execution.get("execution_id"),
            "execution_id": execution.get("execution_id"),
            "scene_id": execution.get("scene_id"),
            "status": execution.get("status"),
            "created_at": execution.get("created_at"),
            "completed_at": execution.get("completed_at"),
            "error": execution.get("error"),
            "skill_chain": list(execution.get("skill_chain") or []),
            "policy_results": list(execution.get("policy_results") or []),
            "notifications": list(execution.get("notifications") or []),
            "source_file": execution.get("source_file"),
            "trigger": execution.get("scene_id"),
        }

    def create_execution(
        self,
        *,
        scene_id: str,
        system_id: str,
        source_type: str,
        source_file: str,
        skill_chain: List[str],
        status: str = "queued",
        notifications: Optional[List[str]] = None,
        input_snapshot: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        now = current_time_iso()
        execution = {
            "execution_id": f"exec_{uuid.uuid4().hex}",
            "scene_id": str(scene_id or "").strip(),
            "system_id": str(system_id or "").strip(),
            "source_type": str(source_type or "").strip(),
            "source_file": str(source_file or "").strip(),
            "skill_chain": list(skill_chain or []),
            "status": str(status or "").strip() or "queued",
            "policy_results": [],
            "notifications": list(notifications or []),
            "error": None,
            "result_summary": {},
            "input_snapshot": input_snapshot if isinstance(input_snapshot, dict) else None,
            "created_at": now,
            "completed_at": None,
        }

        with self._lock():
            executions = self._load_executions_unlocked()
            executions.append(execution)
            executions = self._cleanup_expired(executions)
            self._save_executions_unlocked(executions)

            latest = self._load_latest_unlocked()
            if execution["system_id"]:
                latest[execution["system_id"]] = self._build_latest_summary(execution)
                self._save_latest_unlocked(latest)

        return dict(execution)

    def update_execution(
        self,
        execution_id: str,
        *,
        status: str,
        error: Optional[str] = None,
        result_summary: Optional[Dict[str, Any]] = None,
        policy_results: Optional[List[Dict[str, Any]]] = None,
        notifications: Optional[List[str]] = None,
        input_snapshot: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        normalized_execution_id = str(execution_id or "").strip()
        if not normalized_execution_id:
            raise ValueError("execution_id不能为空")

        updated: Optional[Dict[str, Any]] = None
        with self._lock():
            executions = self._load_executions_unlocked()
            for item in executions:
                if str(item.get("execution_id") or "").strip() != normalized_execution_id:
                    continue
                item["status"] = str(status or "").strip() or item.get("status") or "queued"
                item["error"] = str(error).strip() if error is not None and str(error).strip() else None
                if result_summary is not None:
                    item["result_summary"] = result_summary if isinstance(result_summary, dict) else {}
                if policy_results is not None:
                    item["policy_results"] = policy_results if isinstance(policy_results, list) else []
                if notifications is not None:
                    item["notifications"] = notifications if isinstance(notifications, list) else []
                if input_snapshot is not None:
                    item["input_snapshot"] = input_snapshot if isinstance(input_snapshot, dict) else None
                if item["status"] in {"completed", "failed", "partial_success"}:
                    item["completed_at"] = current_time_iso()
                updated = dict(item)
                break

            if updated is None:
                raise ValueError("execution_not_found")

            executions = self._cleanup_expired(executions)
            self._save_executions_unlocked(executions)

            latest = self._load_latest_unlocked()
            if updated.get("system_id"):
                latest[str(updated["system_id"])] = self._build_latest_summary(updated)
                self._save_latest_unlocked(latest)

        return updated

    def get_execution(self, execution_id: str) -> Optional[Dict[str, Any]]:
        normalized_execution_id = str(execution_id or "").strip()
        if not normalized_execution_id:
            return None
        with self._lock():
            executions = self._load_executions_unlocked()
        for item in reversed(executions):
            if str(item.get("execution_id") or "").strip() == normalized_execution_id:
                return dict(item)
        return None

    def get_latest_execution(self, system_id: str) -> Optional[Dict[str, Any]]:
        normalized_system_id = str(system_id or "").strip()
        if not normalized_system_id:
            return None
        with self._lock():
            latest = self._load_latest_unlocked()
        item = latest.get(normalized_system_id)
        return dict(item) if isinstance(item, dict) else None

    def delete_executions(
        self,
        system_id: str,
        *,
        scene_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        normalized_system_id = str(system_id or "").strip()
        if not normalized_system_id:
            raise ValueError("system_id不能为空")

        normalized_scene_ids = {
            str(scene_id or "").strip()
            for scene_id in (scene_ids or [])
            if str(scene_id or "").strip()
        }

        def _should_delete(item: Dict[str, Any]) -> bool:
            if str(item.get("system_id") or "").strip() != normalized_system_id:
                return False
            if not normalized_scene_ids:
                return True
            return str(item.get("scene_id") or "").strip() in normalized_scene_ids

        with self._lock():
            executions = self._load_executions_unlocked()
            kept: List[Dict[str, Any]] = []
            deleted: List[Dict[str, Any]] = []
            for item in executions:
                if isinstance(item, dict) and _should_delete(item):
                    deleted.append(dict(item))
                else:
                    kept.append(item)

            if len(deleted) == 0:
                return {
                    "system_id": normalized_system_id,
                    "deleted_count": 0,
                    "deleted_execution_ids": [],
                }

            self._save_executions_unlocked(kept)

            latest = self._load_latest_unlocked()
            remaining_for_system = [
                item for item in kept
                if isinstance(item, dict) and str(item.get("system_id") or "").strip() == normalized_system_id
            ]
            if remaining_for_system:
                latest[normalized_system_id] = self._build_latest_summary(remaining_for_system[-1])
            else:
                latest.pop(normalized_system_id, None)
            self._save_latest_unlocked(latest)

        return {
            "system_id": normalized_system_id,
            "deleted_count": len(deleted),
            "deleted_execution_ids": [
                str(item.get("execution_id") or "").strip()
                for item in deleted
                if str(item.get("execution_id") or "").strip()
            ],
        }


_runtime_execution_service: Optional[RuntimeExecutionService] = None


def get_runtime_execution_service() -> RuntimeExecutionService:
    global _runtime_execution_service
    expected_store = os.path.join(settings.REPORT_DIR, "runtime_executions.json")
    expected_latest = os.path.join(settings.REPORT_DIR, "extraction_tasks.json")
    if (
        _runtime_execution_service is None
        or os.path.realpath(_runtime_execution_service.store_path) != os.path.realpath(expected_store)
        or os.path.realpath(_runtime_execution_service.latest_status_path) != os.path.realpath(expected_latest)
    ):
        _runtime_execution_service = RuntimeExecutionService(
            store_path=expected_store,
            latest_status_path=expected_latest,
        )
    return _runtime_execution_service
