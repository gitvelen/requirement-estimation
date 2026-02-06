"""
系统画像服务（B层）
维护系统画像的草稿/发布态与证据引用。
"""
from __future__ import annotations

import json
import logging
import os
import threading
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


class SystemProfileService:
    def __init__(self, store_path: Optional[str] = None) -> None:
        self.store_path = store_path or os.path.join(settings.REPORT_DIR, "system_profiles.json")
        self.lock_path = f"{self.store_path}.lock"
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
        if not os.path.exists(self.store_path):
            return []
        try:
            with open(self.store_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception as exc:
            logger.warning(f"读取系统画像失败: {exc}")
            return []

    def _save_unlocked(self, items: List[Dict[str, Any]]) -> None:
        os.makedirs(os.path.dirname(self.store_path) or ".", exist_ok=True)
        tmp_path = f"{self.store_path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self.store_path)

    def _find_profile(self, items: List[Dict[str, Any]], system_name: str) -> Optional[Dict[str, Any]]:
        for item in items:
            if isinstance(item, dict) and item.get("system_name") == system_name:
                return item
        return None

    def get_profile(self, system_name: str) -> Optional[Dict[str, Any]]:
        name = str(system_name or "").strip()
        if not name:
            return None
        with self._lock():
            items = self._load_unlocked()
        profile = self._find_profile(items, name)
        return profile

    def list_profiles(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock():
            items = self._load_unlocked()
        if status:
            items = [item for item in items if item.get("status") == status]
        return items

    def upsert_profile(
        self,
        system_name: str,
        payload: Dict[str, Any],
        actor: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        name = str(system_name or "").strip()
        if not name:
            raise ValueError("system_name不能为空")

        fields = payload.get("fields") if isinstance(payload.get("fields"), dict) else {}
        evidence_refs = payload.get("evidence_refs") if isinstance(payload.get("evidence_refs"), list) else []
        system_id = str(payload.get("system_id") or "").strip()

        now = datetime.now().isoformat()
        actor_id = (actor or {}).get("id") or (actor or {}).get("username") or "unknown"
        actor_name = (actor or {}).get("displayName") or (actor or {}).get("username") or "unknown"

        with self._lock():
            items = self._load_unlocked()
            existing = self._find_profile(items, name)
            if not existing:
                existing = {
                    "system_id": system_id,
                    "system_name": name,
                    "status": "draft",
                    "fields": {},
                    "evidence_refs": [],
                    "pending_fields": [],
                    "created_at": now,
                }
                items.append(existing)

            existing["system_id"] = system_id or existing.get("system_id") or ""
            existing["fields"] = fields
            existing["evidence_refs"] = evidence_refs
            existing["updated_by"] = actor_id
            existing["updated_by_name"] = actor_name
            existing["updated_at"] = now

            self._save_unlocked(items)

        return existing

    def publish_profile(
        self,
        system_name: str,
        actor: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        name = str(system_name or "").strip()
        if not name:
            raise ValueError("system_name不能为空")

        now = datetime.now().isoformat()
        actor_id = (actor or {}).get("id") or (actor or {}).get("username") or "unknown"
        actor_name = (actor or {}).get("displayName") or (actor or {}).get("username") or "unknown"

        with self._lock():
            items = self._load_unlocked()
            profile = self._find_profile(items, name)
            if not profile:
                raise ValueError("系统画像不存在")

            pending_fields = self._calc_pending_fields(profile)
            profile["pending_fields"] = pending_fields
            profile["status"] = "published"
            profile["published_at"] = now
            profile["updated_by"] = actor_id
            profile["updated_by_name"] = actor_name
            profile["updated_at"] = now

            self._save_unlocked(items)

        # 发布态同步写入向量库（作为强约束检索信号）
        try:
            from backend.service.knowledge_service import get_knowledge_service
            knowledge_service = get_knowledge_service()
            text = self._build_profile_text(profile)
            embedding = knowledge_service.embedding_service.generate_embedding(text)
            knowledge_service.vector_store.insert_knowledge(
                system_name=profile.get("system_name"),
                knowledge_type="system_profile",
                content=text,
                embedding=embedding,
                metadata=profile.get("fields") or {},
                source_file="system_profile_manual",
            )
        except Exception:
            logger.debug("发布画像写入向量库失败（忽略）", exc_info=True)

        return profile

    def _calc_pending_fields(self, profile: Dict[str, Any]) -> List[str]:
        fields = profile.get("fields") if isinstance(profile.get("fields"), dict) else {}
        evidence_refs = profile.get("evidence_refs") if isinstance(profile.get("evidence_refs"), list) else []

        filled_fields = [key for key, value in fields.items() if self._has_value(value)]
        if not filled_fields:
            return []

        covered = set()
        for ref in evidence_refs:
            if not isinstance(ref, dict):
                continue
            field_name = str(ref.get("field") or "").strip()
            if field_name:
                covered.add(field_name)

        if not evidence_refs:
            return filled_fields

        # 若证据引用未指明字段，默认认为已覆盖
        if evidence_refs and not covered:
            return []

        return [field for field in filled_fields if field not in covered]

    def _build_profile_text(self, profile: Dict[str, Any]) -> str:
        fields = profile.get("fields") if isinstance(profile.get("fields"), dict) else {}
        return (
            f"系统名称:{profile.get('system_name','')} | "
            f"系统边界(做什么):{fields.get('in_scope','')} | "
            f"系统不做什么:{fields.get('out_of_scope','')} | "
            f"核心功能:{fields.get('core_functions','')} | "
            f"业务目标:{fields.get('business_goal','')} | "
            f"业务对象:{fields.get('business_objects','')} | "
            f"主要集成点:{fields.get('integration_points','')} | "
            f"关键约束:{fields.get('key_constraints','')}"
        )

    def has_published_profile(self, system_name: str) -> bool:
        profile = self.get_profile(system_name)
        return bool(profile and profile.get("status") == "published")

    def get_minimal_profile_flags(self, system_name: str) -> Dict[str, Any]:
        profile = self.get_profile(system_name) or {}
        fields = profile.get("fields") if isinstance(profile.get("fields"), dict) else {}
        minimal_keys = ["in_scope", "out_of_scope", "core_functions", "business_objects", "integration_points"]
        missing = [key for key in minimal_keys if not self._has_value(fields.get(key))]
        return {
            "has_profile": bool(profile),
            "is_published": profile.get("status") == "published",
            "missing_minimal_fields": missing,
        }

    def _has_value(self, value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, (list, tuple, set)):
            return any(str(item).strip() for item in value)
        return bool(str(value).strip())


_system_profile_service = None


def get_system_profile_service() -> SystemProfileService:
    global _system_profile_service
    if _system_profile_service is None:
        _system_profile_service = SystemProfileService()
    return _system_profile_service
