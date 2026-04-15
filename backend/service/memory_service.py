from __future__ import annotations

import json
import os
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

try:
    import fcntl

    FCNTL_AVAILABLE = True
except ImportError:  # pragma: no cover
    FCNTL_AVAILABLE = False

from backend.config.config import settings


class MemoryService:
    def __init__(self, store_path: Optional[str] = None) -> None:
        self.store_path = store_path or os.path.join(settings.REPORT_DIR, "memory_records.json")
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

    def _load_unlocked(self) -> Dict[str, List[Dict[str, Any]]]:
        if not os.path.exists(self.store_path):
            return {}
        with open(self.store_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        if not isinstance(payload, dict):
            return {}
        return {str(key): list(value) for key, value in payload.items() if isinstance(value, list)}

    def _save_unlocked(self, payload: Dict[str, List[Dict[str, Any]]]) -> None:
        os.makedirs(os.path.dirname(self.store_path) or ".", exist_ok=True)
        tmp_path = f"{self.store_path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self.store_path)

    def _cleanup_expired(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        retention_days = int(getattr(settings, "MEMORY_RETENTION_DAYS", 3650) or 3650)
        cutoff = datetime.now() - timedelta(days=max(retention_days, 1))
        result: List[Dict[str, Any]] = []
        for record in records:
            created_at = str(record.get("created_at") or "").strip()
            if not created_at:
                result.append(record)
                continue
            try:
                created_dt = datetime.fromisoformat(created_at)
            except ValueError:
                result.append(record)
                continue
            if created_dt >= cutoff:
                result.append(record)
        return result

    @staticmethod
    def _parse_datetime(value: Any) -> Optional[datetime]:
        text = str(value or "").strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = f"{text[:-1]}+00:00"
        return datetime.fromisoformat(text)

    def append_record(
        self,
        *,
        system_id: str,
        memory_type: str,
        memory_subtype: str,
        scene_id: str,
        source_type: str,
        source_id: str,
        summary: str,
        payload: Optional[Dict[str, Any]] = None,
        evidence_refs: Optional[List[Dict[str, Any]]] = None,
        decision_policy: str = "",
        confidence: float = 1.0,
        actor: Optional[str] = None,
    ) -> Dict[str, Any]:
        normalized_system_id = str(system_id or "").strip()
        if not normalized_system_id:
            raise ValueError("system_id不能为空")

        record = {
            "memory_id": f"mem_{uuid.uuid4().hex}",
            "system_id": normalized_system_id,
            "memory_type": str(memory_type or "").strip(),
            "memory_subtype": str(memory_subtype or "").strip(),
            "scene_id": str(scene_id or "").strip(),
            "source_type": str(source_type or "").strip(),
            "source_id": str(source_id or "").strip(),
            "decision_policy": str(decision_policy or "").strip(),
            "confidence": float(confidence or 0),
            "summary": str(summary or "").strip(),
            "payload": payload if isinstance(payload, dict) else {},
            "evidence_refs": evidence_refs if isinstance(evidence_refs, list) else [],
            "actor": str(actor or "").strip(),
            "created_at": datetime.now().isoformat(),
        }

        with self._lock():
            data = self._load_unlocked()
            records = data.get(normalized_system_id) if isinstance(data.get(normalized_system_id), list) else []
            records = [item for item in records if isinstance(item, dict)]
            records.append(record)
            records = self._cleanup_expired(records)
            records.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
            data[normalized_system_id] = records
            self._save_unlocked(data)

        return dict(record)

    def query_records(
        self,
        system_id: str,
        *,
        memory_type: Optional[str] = None,
        scene_id: Optional[str] = None,
        start_at: Optional[str] = None,
        end_at: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        normalized_system_id = str(system_id or "").strip()
        if not normalized_system_id:
            raise ValueError("system_id不能为空")

        safe_limit = max(1, min(int(limit or 50), int(getattr(settings, "RUNTIME_MEMORY_QUERY_LIMIT", 200) or 200)))
        safe_offset = max(0, int(offset or 0))
        normalized_memory_type = str(memory_type or "").strip()
        normalized_scene_id = str(scene_id or "").strip()
        start_dt = self._parse_datetime(start_at) if start_at is not None else None
        end_dt = self._parse_datetime(end_at) if end_at is not None else None

        with self._lock():
            data = self._load_unlocked()
            records = data.get(normalized_system_id) if isinstance(data.get(normalized_system_id), list) else []

        items = [item for item in records if isinstance(item, dict)]
        if normalized_memory_type:
            items = [item for item in items if str(item.get("memory_type") or "").strip() == normalized_memory_type]
        if normalized_scene_id:
            items = [item for item in items if str(item.get("scene_id") or "").strip() == normalized_scene_id]
        if start_dt or end_dt:
            filtered_items: List[Dict[str, Any]] = []
            for item in items:
                try:
                    created_dt = self._parse_datetime(item.get("created_at"))
                except ValueError:
                    continue
                if created_dt is None:
                    continue
                if start_dt and created_dt < start_dt:
                    continue
                if end_dt and created_dt > end_dt:
                    continue
                filtered_items.append(item)
            items = filtered_items

        items.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
        return {
            "total": len(items),
            "items": items[safe_offset : safe_offset + safe_limit],
        }

    def list_records(
        self,
        *,
        memory_type: Optional[str] = None,
        memory_subtype: Optional[str] = None,
        scene_id: Optional[str] = None,
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        safe_limit = max(1, min(int(limit or 200), int(getattr(settings, "RUNTIME_MEMORY_QUERY_LIMIT", 200) or 200)))
        normalized_memory_type = str(memory_type or "").strip()
        normalized_memory_subtype = str(memory_subtype or "").strip()
        normalized_scene_id = str(scene_id or "").strip()

        with self._lock():
            data = self._load_unlocked()

        items: List[Dict[str, Any]] = []
        for system_id, records in data.items():
            if not isinstance(records, list):
                continue
            for record in records:
                if not isinstance(record, dict):
                    continue
                normalized_record = dict(record)
                normalized_record["system_id"] = str(normalized_record.get("system_id") or system_id).strip()
                items.append(normalized_record)

        if normalized_memory_type:
            items = [item for item in items if str(item.get("memory_type") or "").strip() == normalized_memory_type]
        if normalized_memory_subtype:
            items = [item for item in items if str(item.get("memory_subtype") or "").strip() == normalized_memory_subtype]
        if normalized_scene_id:
            items = [item for item in items if str(item.get("scene_id") or "").strip() == normalized_scene_id]

        items.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
        return items[:safe_limit]

    def delete_records(
        self,
        system_id: str,
        *,
        memory_type: Optional[str] = None,
        scene_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        normalized_system_id = str(system_id or "").strip()
        if not normalized_system_id:
            raise ValueError("system_id不能为空")

        normalized_memory_type = str(memory_type or "").strip()
        normalized_scene_ids = {
            str(scene_id or "").strip()
            for scene_id in (scene_ids or [])
            if str(scene_id or "").strip()
        }

        def _should_delete(record: Dict[str, Any]) -> bool:
            if normalized_memory_type and str(record.get("memory_type") or "").strip() != normalized_memory_type:
                return False
            if normalized_scene_ids and str(record.get("scene_id") or "").strip() not in normalized_scene_ids:
                return False
            return True

        with self._lock():
            data = self._load_unlocked()
            records = data.get(normalized_system_id) if isinstance(data.get(normalized_system_id), list) else []
            kept: List[Dict[str, Any]] = []
            deleted: List[Dict[str, Any]] = []
            for record in records:
                if isinstance(record, dict) and _should_delete(record):
                    deleted.append(dict(record))
                else:
                    kept.append(record)

            if len(deleted) == 0:
                return {
                    "system_id": normalized_system_id,
                    "deleted_count": 0,
                    "deleted_memory_ids": [],
                }

            if kept:
                data[normalized_system_id] = kept
            else:
                data.pop(normalized_system_id, None)
            self._save_unlocked(data)

        return {
            "system_id": normalized_system_id,
            "deleted_count": len(deleted),
            "deleted_memory_ids": [
                str(record.get("memory_id") or "").strip()
                for record in deleted
                if str(record.get("memory_id") or "").strip()
            ],
        }


_memory_service: Optional[MemoryService] = None


def get_memory_service() -> MemoryService:
    global _memory_service
    expected_path = os.path.join(settings.REPORT_DIR, "memory_records.json")
    if (
        _memory_service is None
        or os.path.realpath(_memory_service.store_path) != os.path.realpath(expected_path)
    ):
        _memory_service = MemoryService(store_path=expected_path)
    return _memory_service
