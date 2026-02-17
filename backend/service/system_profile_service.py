"""
系统画像服务（B层）
维护系统画像的草稿/发布态与证据引用。
"""
from __future__ import annotations

import copy
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

PROFILE_FIELD_KEYS = (
    "system_scope",
    "module_structure",
    "integration_points",
    "key_constraints",
)

PROFILE_TEXT_FIELD_KEYS = {
    "system_scope",
    "integration_points",
    "key_constraints",
}


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

    def _normalize_module_structure(self, value: Any, *, strict: bool) -> List[Dict[str, Any]]:
        if value is None:
            return []

        parsed_value = value
        if isinstance(parsed_value, str):
            text = parsed_value.strip()
            if not text:
                return []
            try:
                parsed_value = json.loads(text)
            except Exception:
                if strict:
                    raise ValueError("invalid_module_structure")
                return []

        if not isinstance(parsed_value, list):
            if strict:
                raise ValueError("invalid_module_structure")
            return []

        normalized_modules: List[Dict[str, Any]] = []
        now = datetime.now().isoformat()

        for module_item in parsed_value:
            if not isinstance(module_item, dict):
                if strict:
                    raise ValueError("invalid_module_structure")
                continue

            module_name = str(module_item.get("module_name") or "").strip()
            raw_functions = module_item.get("functions")
            if (not module_name) or (not isinstance(raw_functions, list)):
                if strict:
                    raise ValueError("invalid_module_structure")
                continue

            normalized_functions: List[Dict[str, str]] = []
            seen_function_names = set()
            for function_item in raw_functions:
                if not isinstance(function_item, dict):
                    if strict:
                        raise ValueError("invalid_module_structure")
                    continue

                function_name = str(function_item.get("name") or "").strip()
                if not function_name:
                    if strict:
                        raise ValueError("invalid_module_structure")
                    continue

                if function_name in seen_function_names:
                    continue

                function_desc = "" if function_item.get("desc") is None else str(function_item.get("desc")).strip()
                normalized_functions.append({
                    "name": function_name,
                    "desc": function_desc,
                })
                seen_function_names.add(function_name)

            last_updated = str(module_item.get("last_updated") or "").strip() or now
            normalized_modules.append(
                {
                    "module_name": module_name,
                    "functions": normalized_functions,
                    "last_updated": last_updated,
                }
            )

        return normalized_modules

    def _normalize_fields_for_storage(self, fields: Dict[str, Any]) -> Dict[str, Any]:
        normalized: Dict[str, Any] = {}
        raw_fields = fields if isinstance(fields, dict) else {}

        for key in PROFILE_TEXT_FIELD_KEYS:
            if key in raw_fields:
                value = raw_fields.get(key)
                normalized[key] = "" if value is None else str(value).strip()

        if "module_structure" in raw_fields:
            normalized["module_structure"] = self._normalize_module_structure(raw_fields.get("module_structure"), strict=True)

        return normalized

    def _normalize_fields_for_output(self, fields: Dict[str, Any]) -> Dict[str, Any]:
        raw_fields = fields if isinstance(fields, dict) else {}

        return {
            "system_scope": "" if raw_fields.get("system_scope") is None else str(raw_fields.get("system_scope")).strip(),
            "module_structure": self._normalize_module_structure(raw_fields.get("module_structure"), strict=False),
            "integration_points": ""
            if raw_fields.get("integration_points") is None
            else str(raw_fields.get("integration_points")).strip(),
            "key_constraints": ""
            if raw_fields.get("key_constraints") is None
            else str(raw_fields.get("key_constraints")).strip(),
        }

    def _normalize_profile_for_output(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(profile or {})
        raw_fields = payload.get("fields") if isinstance(payload.get("fields"), dict) else {}
        payload["fields"] = self._normalize_fields_for_output(raw_fields)
        if not isinstance(payload.get("field_sources"), dict):
            payload["field_sources"] = {}
        if not isinstance(payload.get("ai_suggestions"), dict):
            payload["ai_suggestions"] = {}
        payload.setdefault("ai_suggestions_updated_at", "")
        if payload.get("ai_suggestions_updated_at") is None:
            payload["ai_suggestions_updated_at"] = ""
        if payload.get("ai_suggestions_job") is not None and not isinstance(payload.get("ai_suggestions_job"), dict):
            payload["ai_suggestions_job"] = {"raw": payload.get("ai_suggestions_job")}
        return payload

    def get_profile(self, system_name: str) -> Optional[Dict[str, Any]]:
        name = str(system_name or "").strip()
        if not name:
            return None
        with self._lock():
            items = self._load_unlocked()
        profile = self._find_profile(items, name)
        if not profile:
            return None
        return self._normalize_profile_for_output(profile)

    def list_profiles(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock():
            items = self._load_unlocked()
        if status:
            items = [item for item in items if item.get("status") == status]
        return [self._normalize_profile_for_output(item) for item in items if isinstance(item, dict)]

    def upsert_profile(
        self,
        system_name: str,
        payload: Dict[str, Any],
        actor: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        name = str(system_name or "").strip()
        if not name:
            raise ValueError("system_name不能为空")

        incoming_fields = payload.get("fields") if isinstance(payload.get("fields"), dict) else {}
        incoming_fields = self._normalize_fields_for_storage(incoming_fields)
        evidence_refs = payload.get("evidence_refs") if isinstance(payload.get("evidence_refs"), list) else []
        system_id = str(payload.get("system_id") or "").strip()
        incoming_sources = payload.get("field_sources") if isinstance(payload.get("field_sources"), dict) else {}

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
                    "field_sources": {},
                    "ai_suggestions": {},
                    "ai_suggestions_updated_at": "",
                    "created_at": now,
                }
                items.append(existing)

            existing["system_id"] = system_id or existing.get("system_id") or ""
            existing_fields = existing.get("fields") if isinstance(existing.get("fields"), dict) else {}
            existing_fields = self._normalize_fields_for_storage(existing_fields)
            for field_key in PROFILE_FIELD_KEYS:
                if field_key in incoming_fields:
                    existing_fields[field_key] = incoming_fields.get(field_key)
            existing["fields"] = existing_fields
            existing["evidence_refs"] = evidence_refs

            # field_sources: manual by default for user-provided fields; allow overriding to ai on accept action
            field_sources = existing.get("field_sources") if isinstance(existing.get("field_sources"), dict) else {}
            field_sources = dict(field_sources)
            for key in incoming_fields.keys():
                field_sources[str(key)] = "manual"
            for key, value in incoming_sources.items():
                k = str(key or "").strip()
                v = str(value or "").strip().lower()
                if not k:
                    continue
                if v not in {"manual", "ai"}:
                    continue
                field_sources[k] = v
            existing["field_sources"] = field_sources

            existing["updated_by"] = actor_id
            existing["updated_by_name"] = actor_name
            existing["updated_at"] = now

            self._save_unlocked(items)

        return self._normalize_profile_for_output(existing)

    def get_or_create_ai_suggestions_job(
        self,
        system_name: str,
        system_id: Optional[str],
        *,
        actor: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        name = str(system_name or "").strip()
        if not name:
            raise ValueError("system_name不能为空")

        now = datetime.now().isoformat()
        actor_id = (actor or {}).get("id") or (actor or {}).get("username") or "unknown"
        normalized_system_id = str(system_id or "").strip()

        with self._lock():
            items = self._load_unlocked()
            profile = self._find_profile(items, name)
            if not profile:
                raise ValueError("系统画像不存在")

            if normalized_system_id and not profile.get("system_id"):
                profile["system_id"] = normalized_system_id

            job = profile.get("ai_suggestions_job") if isinstance(profile.get("ai_suggestions_job"), dict) else {}
            job_id = str(job.get("job_id") or "").strip()
            status = str(job.get("status") or "").strip().lower()
            if job_id and status in {"queued", "running"}:
                return {"job_id": job_id, "status": status, "created_new": False}

            job_id = f"summary_{uuid.uuid4().hex}"
            profile["ai_suggestions_job"] = {
                "job_id": job_id,
                "status": "queued",
                "created_at": now,
                "updated_at": now,
                "triggered_by": actor_id,
            }
            profile["updated_at"] = now
            self._save_unlocked(items)

        return {"job_id": job_id, "status": "queued", "created_new": True}

    def update_ai_suggestions_job(
        self,
        system_name: str,
        *,
        job_id: str,
        status: str,
        error_code: Optional[str] = None,
        error_reason: Optional[str] = None,
    ) -> None:
        name = str(system_name or "").strip()
        if not name:
            raise ValueError("system_name不能为空")

        normalized_job_id = str(job_id or "").strip()
        if not normalized_job_id:
            return

        now = datetime.now().isoformat()
        normalized_status = str(status or "").strip().lower() or "running"

        with self._lock():
            items = self._load_unlocked()
            profile = self._find_profile(items, name)
            if not profile:
                return

            job = profile.get("ai_suggestions_job") if isinstance(profile.get("ai_suggestions_job"), dict) else {}
            if str(job.get("job_id") or "").strip() != normalized_job_id:
                return

            job["status"] = normalized_status
            job["updated_at"] = now
            if error_code:
                job["error_code"] = str(error_code)
            if error_reason:
                job["error_reason"] = str(error_reason)[:500]
            profile["ai_suggestions_job"] = job
            profile["updated_at"] = now
            self._save_unlocked(items)

    def set_ai_suggestions(
        self,
        system_name: str,
        *,
        suggestions: Dict[str, Any],
    ) -> Dict[str, Any]:
        name = str(system_name or "").strip()
        if not name:
            raise ValueError("system_name不能为空")

        now = datetime.now().isoformat()
        normalized: Dict[str, str] = {}
        if isinstance(suggestions, dict):
            for key, value in suggestions.items():
                k = str(key or "").strip()
                if not k:
                    continue
                v = "" if value is None else str(value).strip()
                normalized[k] = v

        with self._lock():
            items = self._load_unlocked()
            profile = self._find_profile(items, name)
            if not profile:
                raise ValueError("系统画像不存在")

            profile["ai_suggestions"] = normalized
            profile["ai_suggestions_updated_at"] = now
            profile["updated_at"] = now
            self._save_unlocked(items)

        return self._normalize_profile_for_output(profile)

    def _calculate_completeness_score(self, completeness: Dict[str, Any]) -> int:
        score = 0

        if bool(completeness.get("code_scan")):
            score += 30

        documents_normal = int(completeness.get("documents_normal") or 0)
        if documents_normal >= 11:
            score += 40
        elif documents_normal >= 6:
            score += 30
        elif documents_normal >= 1:
            score += 10

        if bool(completeness.get("esb")):
            score += 30

        return max(0, min(100, score))

    def mark_code_scan_ingested(
        self,
        system_name: str,
        system_id: Optional[str],
        job_id: str,
        result_path: str,
        actor: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        name = str(system_name or "").strip()
        if not name:
            raise ValueError("system_name不能为空")

        now = datetime.now().isoformat()
        actor_id = (actor or {}).get("id") or (actor or {}).get("username") or "unknown"
        actor_name = (actor or {}).get("displayName") or (actor or {}).get("username") or "unknown"
        normalized_system_id = str(system_id or "").strip()

        with self._lock():
            items = self._load_unlocked()
            profile = self._find_profile(items, name)
            if not profile:
                profile = {
                    "system_id": normalized_system_id,
                    "system_name": name,
                    "status": "draft",
                    "fields": {},
                    "evidence_refs": [],
                    "pending_fields": [],
                    "created_at": now,
                }
                items.append(profile)

            if normalized_system_id:
                profile["system_id"] = normalized_system_id
            elif not profile.get("system_id"):
                profile["system_id"] = ""

            completeness = profile.get("completeness") if isinstance(profile.get("completeness"), dict) else {}
            completeness = dict(completeness)
            completeness.setdefault("documents_normal", int(profile.get("document_count") or 0))
            completeness.setdefault("esb", bool(completeness.get("esb")))
            completeness["code_scan"] = True
            profile["completeness"] = completeness
            profile["document_count"] = int(completeness.get("documents_normal") or 0)
            profile["completeness_score"] = self._calculate_completeness_score(completeness)

            evidence_refs = profile.get("evidence_refs") if isinstance(profile.get("evidence_refs"), list) else []
            evidence_refs = list(evidence_refs)
            normalized_job_id = str(job_id or "").strip()
            already_exists = False
            if normalized_job_id:
                for ref in evidence_refs:
                    if not isinstance(ref, dict):
                        continue
                    if str(ref.get("source_type") or "") != "code_scan":
                        continue
                    if str(ref.get("source_id") or "") == normalized_job_id:
                        already_exists = True
                        break

            if normalized_job_id and (not already_exists):
                evidence_refs.append(
                    {
                        "source_type": "code_scan",
                        "source_id": normalized_job_id,
                        "source_path": str(result_path or ""),
                        "created_at": now,
                    }
                )
            profile["evidence_refs"] = evidence_refs

            profile["updated_by"] = actor_id
            profile["updated_by_name"] = actor_name
            profile["updated_at"] = now

            self._save_unlocked(items)

        return profile

    def mark_esb_ingested(
        self,
        system_name: str,
        system_id: Optional[str],
        import_id: str,
        source_file: str,
        actor: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        name = str(system_name or "").strip()
        if not name:
            raise ValueError("system_name不能为空")

        now = datetime.now().isoformat()
        actor_id = (actor or {}).get("id") or (actor or {}).get("username") or "unknown"
        actor_name = (actor or {}).get("displayName") or (actor or {}).get("username") or "unknown"
        normalized_system_id = str(system_id or "").strip()

        with self._lock():
            items = self._load_unlocked()
            profile = self._find_profile(items, name)
            if not profile:
                profile = {
                    "system_id": normalized_system_id,
                    "system_name": name,
                    "status": "draft",
                    "fields": {},
                    "evidence_refs": [],
                    "pending_fields": [],
                    "created_at": now,
                }
                items.append(profile)

            if normalized_system_id:
                profile["system_id"] = normalized_system_id
            elif not profile.get("system_id"):
                profile["system_id"] = ""

            completeness = profile.get("completeness") if isinstance(profile.get("completeness"), dict) else {}
            completeness = dict(completeness)
            completeness.setdefault("documents_normal", int(profile.get("document_count") or 0))
            completeness.setdefault("code_scan", bool(completeness.get("code_scan")))
            completeness["esb"] = True
            profile["completeness"] = completeness
            profile["document_count"] = int(completeness.get("documents_normal") or 0)
            profile["completeness_score"] = self._calculate_completeness_score(completeness)

            evidence_refs = profile.get("evidence_refs") if isinstance(profile.get("evidence_refs"), list) else []
            evidence_refs = list(evidence_refs)
            normalized_import_id = str(import_id or "").strip()
            already_exists = False
            if normalized_import_id:
                for ref in evidence_refs:
                    if not isinstance(ref, dict):
                        continue
                    if str(ref.get("source_type") or "") != "esb":
                        continue
                    if str(ref.get("source_id") or "") == normalized_import_id:
                        already_exists = True
                        break

            if normalized_import_id and (not already_exists):
                evidence_refs.append(
                    {
                        "source_type": "esb",
                        "source_id": normalized_import_id,
                        "source_file": str(source_file or ""),
                        "created_at": now,
                    }
                )
            profile["evidence_refs"] = evidence_refs

            profile["updated_by"] = actor_id
            profile["updated_by_name"] = actor_name
            profile["updated_at"] = now

            self._save_unlocked(items)

        return profile

    def mark_document_imported(
        self,
        system_name: str,
        system_id: Optional[str],
        import_id: str,
        source_file: str,
        level: str = "normal",
        actor: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        name = str(system_name or "").strip()
        if not name:
            raise ValueError("system_name不能为空")

        normalized_level = str(level or "normal").strip().lower() or "normal"
        now = datetime.now().isoformat()
        actor_id = (actor or {}).get("id") or (actor or {}).get("username") or "unknown"
        actor_name = (actor or {}).get("displayName") or (actor or {}).get("username") or "unknown"
        normalized_system_id = str(system_id or "").strip()

        with self._lock():
            items = self._load_unlocked()
            profile = self._find_profile(items, name)
            if not profile:
                profile = {
                    "system_id": normalized_system_id,
                    "system_name": name,
                    "status": "draft",
                    "fields": {},
                    "evidence_refs": [],
                    "pending_fields": [],
                    "created_at": now,
                }
                items.append(profile)

            if normalized_system_id:
                profile["system_id"] = normalized_system_id
            elif not profile.get("system_id"):
                profile["system_id"] = ""

            completeness = profile.get("completeness") if isinstance(profile.get("completeness"), dict) else {}
            completeness = dict(completeness)
            completeness.setdefault("code_scan", bool(completeness.get("code_scan")))
            completeness.setdefault("esb", bool(completeness.get("esb")))
            documents_normal = int(completeness.get("documents_normal") or profile.get("document_count") or 0)
            if normalized_level == "normal":
                documents_normal += 1
            completeness["documents_normal"] = max(0, documents_normal)
            profile["document_count"] = int(completeness.get("documents_normal") or 0)
            profile["completeness"] = completeness
            profile["completeness_score"] = self._calculate_completeness_score(completeness)

            evidence_refs = profile.get("evidence_refs") if isinstance(profile.get("evidence_refs"), list) else []
            evidence_refs = list(evidence_refs)
            normalized_import_id = str(import_id or "").strip()
            already_exists = False
            if normalized_import_id:
                for ref in evidence_refs:
                    if not isinstance(ref, dict):
                        continue
                    if str(ref.get("source_type") or "") != "knowledge_import":
                        continue
                    if str(ref.get("source_id") or "") == normalized_import_id:
                        already_exists = True
                        break

            if normalized_import_id and (not already_exists):
                evidence_refs.append(
                    {
                        "source_type": "knowledge_import",
                        "source_id": normalized_import_id,
                        "source_file": str(source_file or ""),
                        "level": normalized_level,
                        "created_at": now,
                    }
                )
            profile["evidence_refs"] = evidence_refs

            profile["updated_by"] = actor_id
            profile["updated_by_name"] = actor_name
            profile["updated_at"] = now

            self._save_unlocked(items)

        return profile

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

            fields = profile.get("fields") if isinstance(profile.get("fields"), dict) else {}
            fields = self._normalize_fields_for_storage(fields)

            profile_snapshot = copy.deepcopy(profile)
            profile_snapshot["fields"] = fields
            pending_fields = self._calc_pending_fields(profile_snapshot)
            profile_snapshot["pending_fields"] = pending_fields
            profile_snapshot["status"] = "published"
            profile_snapshot["published_at"] = now
            profile_snapshot["updated_by"] = actor_id
            profile_snapshot["updated_by_name"] = actor_name
            profile_snapshot["updated_at"] = now

        try:
            from backend.service.knowledge_service import get_knowledge_service
            knowledge_service = get_knowledge_service()
            text = self._build_profile_text(profile_snapshot)
            embedding = knowledge_service.embedding_service.generate_embedding(text)
            knowledge_service.vector_store.insert_knowledge(
                system_name=profile_snapshot.get("system_name"),
                knowledge_type="system_profile",
                content=text,
                embedding=embedding,
                metadata=profile_snapshot.get("fields") or {},
                source_file="system_profile_manual",
            )
        except Exception as exc:
            raise RuntimeError(f"embedding服务不可用: {exc}") from exc

        with self._lock():
            items = self._load_unlocked()
            profile = self._find_profile(items, name)
            if not profile:
                raise ValueError("系统画像不存在")

            if isinstance(profile.get("fields"), dict):
                profile["fields"] = self._normalize_fields_for_storage(profile.get("fields") or {})

            pending_fields = self._calc_pending_fields(profile)
            profile["pending_fields"] = pending_fields
            profile["status"] = "published"
            profile["published_at"] = now
            profile["updated_by"] = actor_id
            profile["updated_by_name"] = actor_name
            profile["updated_at"] = now

            self._save_unlocked(items)

            return self._normalize_profile_for_output(profile)

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
        module_structure = self._normalize_module_structure(fields.get("module_structure"), strict=False)
        module_segments: List[str] = []
        for module_item in module_structure[:20]:
            module_name = str(module_item.get("module_name") or "").strip()
            functions = module_item.get("functions") if isinstance(module_item.get("functions"), list) else []
            function_names = [
                str(function_item.get("name") or "").strip()
                for function_item in functions
                if isinstance(function_item, dict) and str(function_item.get("name") or "").strip()
            ]
            if module_name and function_names:
                module_segments.append(f"{module_name}({ '、'.join(function_names[:20]) })")
            elif module_name:
                module_segments.append(module_name)
        module_structure_text = "；".join(module_segments)
        return (
            f"系统名称:{profile.get('system_name','')} | "
            f"系统定位与边界:{fields.get('system_scope','')} | "
            f"模块结构:{module_structure_text} | "
            f"主要集成点:{fields.get('integration_points','')} | "
            f"关键约束:{fields.get('key_constraints','')}"
        )

    def has_published_profile(self, system_name: str) -> bool:
        profile = self.get_profile(system_name)
        return bool(profile and profile.get("status") == "published")

    def get_minimal_profile_flags(self, system_name: str) -> Dict[str, Any]:
        profile = self.get_profile(system_name) or {}
        fields = profile.get("fields") if isinstance(profile.get("fields"), dict) else {}
        minimal_keys = ["system_scope", "module_structure"]
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
