"""
审计日志服务
用于记录规则变更、证据等级修正等关键操作。
"""
from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    import fcntl
    FCNTL_AVAILABLE = True
except ImportError:
    FCNTL_AVAILABLE = False

from backend.config.config import settings

logger = logging.getLogger(__name__)


class AuditLogService:
    def __init__(self, path: Optional[str] = None) -> None:
        self.path = path or os.path.join(settings.REPORT_DIR, "audit_logs.json")
        self.lock_path = f"{self.path}.lock"
        self._mutex = threading.RLock()

    @contextmanager
    def _lock(self):
        if FCNTL_AVAILABLE:
            os.makedirs(os.path.dirname(self.lock_path) or ".", exist_ok=True)
            with open(self.lock_path, "a") as lock_file:
                fcntl.flock(lock_file, fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(lock_file, fcntl.LOCK_UN)
        else:
            with self._mutex:
                yield

    def _load_unlocked(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.path):
            return []
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception as exc:
            logger.warning(f"读取审计日志失败: {exc}")
            return []

    def _save_unlocked(self, logs: List[Dict[str, Any]]) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        tmp_path = f"{self.path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self.path)

    def append(self, action: str, actor: Optional[Dict[str, Any]], detail: Dict[str, Any]) -> Dict[str, Any]:
        entry = {
            "id": f"audit_{uuid.uuid4().hex}",
            "action": str(action or ""),
            "actor_id": (actor or {}).get("id") or (actor or {}).get("username") or "unknown",
            "actor_name": (actor or {}).get("displayName") or (actor or {}).get("username") or "unknown",
            "detail": detail or {},
            "created_at": datetime.now().isoformat(),
        }
        with self._lock():
            logs = self._load_unlocked()
            logs.append(entry)
            self._save_unlocked(logs)
        return entry

    def list_logs(self, action: Optional[str] = None, limit: int = 200) -> List[Dict[str, Any]]:
        with self._lock():
            logs = self._load_unlocked()
        if action:
            logs = [item for item in logs if item.get("action") == action]
        logs.sort(key=lambda x: x.get("created_at") or "", reverse=True)
        return logs[: max(int(limit or 0), 0)] if limit else logs


_audit_log_service = None


def get_audit_log_service() -> AuditLogService:
    global _audit_log_service
    if _audit_log_service is None:
        _audit_log_service = AuditLogService()
    return _audit_log_service

