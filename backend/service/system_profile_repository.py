from __future__ import annotations

import copy
import json
import os
import re
import shutil
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    import fcntl

    FCNTL_AVAILABLE = True
except ImportError:  # pragma: no cover
    FCNTL_AVAILABLE = False

from backend.config.config import settings
from backend.utils.time_utils import current_time_iso


def resolve_system_profile_root(root_dir: Optional[str] = None) -> str:
    explicit_root = str(root_dir or "").strip()
    if explicit_root:
        return os.path.abspath(explicit_root)

    configured_root = str(getattr(settings, "SYSTEM_PROFILE_ROOT", "") or "").strip()
    if configured_root:
        return os.path.abspath(configured_root)

    compatible_root = str(getattr(settings, "PROFILE_ARTIFACT_ROOT", "") or "").strip()
    if compatible_root:
        return os.path.abspath(compatible_root)

    report_dir = str(getattr(settings, "REPORT_DIR", "") or "").strip() or "data"
    return os.path.abspath(os.path.join(report_dir, "system_profiles"))


class SystemProfileRepository:
    def __init__(self, root_dir: Optional[str] = None) -> None:
        self.root_dir = resolve_system_profile_root(root_dir)
        self.lock_path = os.path.join(self.root_dir, ".system_profiles.lock")
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

    def _sanitize_segment(self, value: str, fallback: str = "system") -> str:
        text = str(value or "").strip()
        if not text:
            return fallback
        text = text.replace("/", "_").replace("\\", "_")
        text = re.sub(r"[^0-9a-zA-Z_\-\.\u4e00-\u9fa5]+", "_", text)
        text = re.sub(r"_+", "_", text).strip("_")
        return text[:64] or fallback

    def _build_workspace_segment(self, system_id: str, system_name: str) -> str:
        normalized_system_id = self._sanitize_segment(system_id, fallback="system")
        short_id = normalized_system_id[:8] or "system"
        normalized_system_name = self._sanitize_segment(system_name, fallback="system")
        return f"sid_{short_id}__{normalized_system_name}"

    def _workspace_path(self, segment: str) -> str:
        return os.path.join(self.root_dir, segment)

    def _manifest_path(self, workspace_path: str) -> str:
        return os.path.join(workspace_path, "manifest.json")

    def _profile_path(self, workspace_path: str, state: str) -> str:
        return os.path.join(workspace_path, "profile", f"{state}.json")

    def _revision_dir(self, workspace_path: str) -> str:
        return os.path.join(workspace_path, "profile", "revisions")

    def _history_path(self, workspace_path: str) -> str:
        return os.path.join(workspace_path, "source", "imports", "history.json")

    def _task_path(self, workspace_path: str) -> str:
        return os.path.join(workspace_path, "source", "imports", "extraction_task.json")

    def _write_json_unlocked(self, path: str, payload: Any) -> None:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        tmp_path = f"{path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)

    def _load_json_unlocked(self, path: str, default: Any) -> Any:
        if not os.path.exists(path):
            return copy.deepcopy(default)
        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except Exception:
            return copy.deepcopy(default)
        if isinstance(default, dict):
            return payload if isinstance(payload, dict) else copy.deepcopy(default)
        if isinstance(default, list):
            return payload if isinstance(payload, list) else copy.deepcopy(default)
        return payload

    def _iter_workspaces_unlocked(self) -> Iterable[Tuple[str, Dict[str, Any]]]:
        root = Path(self.root_dir)
        if not root.exists():
            return []

        workspaces: List[Tuple[str, Dict[str, Any]]] = []
        for child in sorted(root.iterdir(), key=lambda item: item.name):
            if not child.is_dir():
                continue
            manifest = self._load_json_unlocked(str(child / "manifest.json"), {})
            if not isinstance(manifest, dict) or not manifest:
                continue
            workspaces.append((str(child), manifest))
        return workspaces

    def _find_workspace_unlocked(
        self,
        *,
        system_id: str = "",
        system_name: str = "",
    ) -> Optional[Tuple[str, Dict[str, Any]]]:
        normalized_system_id = str(system_id or "").strip()
        normalized_system_name = str(system_name or "").strip()
        for workspace_path, manifest in self._iter_workspaces_unlocked():
            manifest_id = str(manifest.get("system_id") or "").strip()
            manifest_name = str(manifest.get("system_name") or "").strip()
            if normalized_system_id and manifest_id == normalized_system_id:
                return workspace_path, manifest
            if normalized_system_name and manifest_name == normalized_system_name:
                return workspace_path, manifest
        return None

    def _ensure_workspace_unlocked(self, *, system_id: str, system_name: str) -> Tuple[str, Dict[str, Any]]:
        normalized_system_id = str(system_id or "").strip()
        normalized_system_name = str(system_name or "").strip()
        if not normalized_system_id:
            raise ValueError("system_id不能为空")
        if not normalized_system_name:
            raise ValueError("system_name不能为空")

        now = current_time_iso()
        existing = self._find_workspace_unlocked(system_id=normalized_system_id, system_name=normalized_system_name)
        target_segment = self._build_workspace_segment(normalized_system_id, normalized_system_name)
        target_workspace = self._workspace_path(target_segment)

        if existing:
            current_workspace, manifest = existing
            if os.path.abspath(current_workspace) != os.path.abspath(target_workspace):
                os.makedirs(os.path.dirname(target_workspace) or ".", exist_ok=True)
                if os.path.exists(target_workspace):
                    for item in os.listdir(current_workspace):
                        src = os.path.join(current_workspace, item)
                        dst = os.path.join(target_workspace, item)
                        if os.path.isdir(src):
                            os.makedirs(dst, exist_ok=True)
                        if not os.path.exists(dst):
                            os.replace(src, dst)
                    os.rmdir(current_workspace)
                else:
                    os.replace(current_workspace, target_workspace)
            workspace_path = target_workspace
            manifest = {
                **manifest,
                "system_id": normalized_system_id,
                "system_name": normalized_system_name,
                "slug": self._sanitize_segment(normalized_system_name, fallback="system"),
                "updated_at": now,
                "storage_version": "v28_system_workspace",
            }
        else:
            workspace_path = target_workspace
            manifest = {
                "system_id": normalized_system_id,
                "system_name": normalized_system_name,
                "slug": self._sanitize_segment(normalized_system_name, fallback="system"),
                "created_at": now,
                "updated_at": now,
                "storage_version": "v28_system_workspace",
            }

        for relative_dir in (
            "profile/revisions",
            "source/documents",
            "source/code",
            "source/esb",
            "source/imports",
            "candidate/latest",
            "candidate/documents",
            "candidate/authoritative",
            "candidate/projections/records",
            "candidate/jobs",
            "audit/decisions",
            "audit/estimation",
            "audit/health",
        ):
            os.makedirs(os.path.join(workspace_path, relative_dir), exist_ok=True)

        self._write_json_unlocked(self._manifest_path(workspace_path), manifest)
        return workspace_path, dict(manifest)

    def ensure_workspace(self, *, system_id: str, system_name: str) -> Tuple[str, Dict[str, Any]]:
        with self._lock():
            return self._ensure_workspace_unlocked(system_id=system_id, system_name=system_name)

    def get_workspace_path(self, *, system_id: str = "", system_name: str = "") -> Optional[str]:
        with self._lock():
            found = self._find_workspace_unlocked(system_id=system_id, system_name=system_name)
            return found[0] if found else None

    def get_workspace_identity(self, *, system_id: str = "", system_name: str = "") -> Optional[Dict[str, str]]:
        with self._lock():
            found = self._find_workspace_unlocked(system_id=system_id, system_name=system_name)
            if not found:
                return None
            _, manifest = found
            return {
                "system_id": str(manifest.get("system_id") or "").strip(),
                "system_name": str(manifest.get("system_name") or "").strip(),
            }

    def load_profile(self, *, state: str, system_id: str = "", system_name: str = "") -> Optional[Dict[str, Any]]:
        normalized_state = "published" if str(state or "").strip() == "published" else "working"
        with self._lock():
            found = self._find_workspace_unlocked(system_id=system_id, system_name=system_name)
            if not found:
                return None
            workspace_path, manifest = found
            path = self._profile_path(workspace_path, normalized_state)
            payload = self._load_json_unlocked(path, {})
            if not payload and normalized_state == "working":
                fallback = self._load_json_unlocked(self._profile_path(workspace_path, "published"), {})
                payload = fallback if isinstance(fallback, dict) else {}
            if not isinstance(payload, dict) or not payload:
                return None
            payload["system_id"] = str(manifest.get("system_id") or "").strip()
            payload["system_name"] = str(manifest.get("system_name") or "").strip()
            return copy.deepcopy(payload)

    def _next_revision_name_unlocked(self, workspace_path: str) -> str:
        revision_dir = self._revision_dir(workspace_path)
        existing_numbers: List[int] = []
        if os.path.isdir(revision_dir):
            for item in os.listdir(revision_dir):
                if not item.startswith("rev_") or not item.endswith(".json"):
                    continue
                try:
                    existing_numbers.append(int(item[4:-5]))
                except ValueError:
                    continue
        next_number = (max(existing_numbers) + 1) if existing_numbers else 1
        return f"rev_{next_number:06d}.json"

    def _write_revision_unlocked(
        self,
        *,
        workspace_path: str,
        profile: Dict[str, Any],
        state: str,
    ) -> None:
        revision_name = self._next_revision_name_unlocked(workspace_path)
        revision_payload = {
            "revision_name": revision_name[:-5],
            "state": state,
            "created_at": current_time_iso(),
            "profile": copy.deepcopy(profile),
        }
        self._write_json_unlocked(os.path.join(self._revision_dir(workspace_path), revision_name), revision_payload)

    def save_profile(self, *, profile: Dict[str, Any], state: str) -> Dict[str, Any]:
        normalized_state = "published" if str(state or "").strip() == "published" else "working"
        system_id = str(profile.get("system_id") or "").strip()
        system_name = str(profile.get("system_name") or "").strip()
        if not system_id:
            raise ValueError("system_id不能为空")
        if not system_name:
            raise ValueError("system_name不能为空")

        payload = copy.deepcopy(profile)
        now = current_time_iso()
        payload.setdefault("created_at", now)
        payload["updated_at"] = str(payload.get("updated_at") or now)
        if normalized_state == "published":
            payload["status"] = "published"
            payload.setdefault("published_at", now)

        with self._lock():
            workspace_path, manifest = self._ensure_workspace_unlocked(system_id=system_id, system_name=system_name)
            existing = self._load_json_unlocked(self._profile_path(workspace_path, normalized_state), {})
            if existing == payload:
                return copy.deepcopy(payload)
            self._write_json_unlocked(self._profile_path(workspace_path, normalized_state), payload)
            self._write_revision_unlocked(workspace_path=workspace_path, profile=payload, state=normalized_state)
            manifest["updated_at"] = now
            self._write_json_unlocked(self._manifest_path(workspace_path), manifest)
        return copy.deepcopy(payload)

    def save_working_profile(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        return self.save_profile(profile=profile, state="working")

    def save_published_profile(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        return self.save_profile(profile=profile, state="published")

    def save_working_profiles(self, items: List[Dict[str, Any]]) -> None:
        profiles = [dict(item) for item in items if isinstance(item, dict)]
        profiles.sort(key=lambda item: (str(item.get("system_name") or ""), str(item.get("system_id") or "")))
        for item in profiles:
            self.save_profile(profile=item, state="working")

    def list_profiles(self, *, state: str = "working") -> List[Dict[str, Any]]:
        normalized_state = "published" if str(state or "").strip() == "published" else "working"
        result: List[Dict[str, Any]] = []
        with self._lock():
            for workspace_path, manifest in self._iter_workspaces_unlocked():
                payload = self._load_json_unlocked(self._profile_path(workspace_path, normalized_state), {})
                if not payload and normalized_state == "working":
                    payload = self._load_json_unlocked(self._profile_path(workspace_path, "published"), {})
                if not isinstance(payload, dict) or not payload:
                    continue
                payload["system_id"] = str(manifest.get("system_id") or "").strip()
                payload["system_name"] = str(manifest.get("system_name") or "").strip()
                result.append(copy.deepcopy(payload))
        result.sort(key=lambda item: str(item.get("system_name") or ""))
        return result

    def list_workspace_identities(self) -> List[Dict[str, str]]:
        result: List[Dict[str, str]] = []
        with self._lock():
            for _workspace_path, manifest in self._iter_workspaces_unlocked():
                system_id = str(manifest.get("system_id") or "").strip()
                system_name = str(manifest.get("system_name") or "").strip()
                if not system_id and not system_name:
                    continue
                result.append(
                    {
                        "system_id": system_id,
                        "system_name": system_name,
                    }
                )
        result.sort(key=lambda item: (item.get("system_name") or "", item.get("system_id") or ""))
        return result

    def append_import_history(self, *, system_id: str, system_name: str, item: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock():
            workspace_path, _ = self._ensure_workspace_unlocked(system_id=system_id, system_name=system_name)
            records = self._load_json_unlocked(self._history_path(workspace_path), [])
            records = [record for record in records if isinstance(record, dict)]
            records.append(copy.deepcopy(item))
            records.sort(key=lambda record: str(record.get("imported_at") or ""), reverse=True)
            self._write_json_unlocked(self._history_path(workspace_path), records)
        return copy.deepcopy(item)

    def get_import_history(self, *, system_id: str = "", system_name: str = "") -> List[Dict[str, Any]]:
        with self._lock():
            found = self._find_workspace_unlocked(system_id=system_id, system_name=system_name)
            if not found:
                return []
            workspace_path, _ = found
            records = self._load_json_unlocked(self._history_path(workspace_path), [])
            return [dict(record) for record in records if isinstance(record, dict)]

    def save_extraction_task(self, *, system_id: str, system_name: str, task: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock():
            workspace_path, _ = self._ensure_workspace_unlocked(system_id=system_id, system_name=system_name)
            self._write_json_unlocked(self._task_path(workspace_path), task if isinstance(task, dict) else {})
        return copy.deepcopy(task)

    def get_extraction_task(self, *, system_id: str = "", system_name: str = "") -> Optional[Dict[str, Any]]:
        with self._lock():
            found = self._find_workspace_unlocked(system_id=system_id, system_name=system_name)
            if not found:
                return None
            workspace_path, _ = found
            task = self._load_json_unlocked(self._task_path(workspace_path), {})
            if not isinstance(task, dict) or not task:
                return None
            return dict(task)

    def get_extraction_task_by_task_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        normalized_task_id = str(task_id or "").strip()
        if not normalized_task_id:
            return None
        with self._lock():
            for workspace_path, manifest in self._iter_workspaces_unlocked():
                task = self._load_json_unlocked(self._task_path(workspace_path), {})
                if not isinstance(task, dict):
                    continue
                if str(task.get("task_id") or "").strip() != normalized_task_id:
                    continue
                return {
                    "system_id": str(manifest.get("system_id") or "").strip(),
                    "task": dict(task),
                }
        return None

    def delete_workspace(self, *, system_id: str = "", system_name: str = "") -> Dict[str, Any]:
        with self._lock():
            found = self._find_workspace_unlocked(system_id=system_id, system_name=system_name)
            if not found:
                return {
                    "deleted": False,
                    "system_id": str(system_id or "").strip(),
                    "system_name": str(system_name or "").strip(),
                    "workspace_path": None,
                }

            workspace_path, manifest = found
            normalized_workspace = os.path.abspath(workspace_path)
            if os.path.isdir(normalized_workspace):
                shutil.rmtree(normalized_workspace)

            return {
                "deleted": True,
                "system_id": str(manifest.get("system_id") or system_id or "").strip(),
                "system_name": str(manifest.get("system_name") or system_name or "").strip(),
                "workspace_path": normalized_workspace,
            }

    def migrate_legacy_profile_store(self, legacy_path: str) -> Dict[str, Any]:
        path = str(legacy_path or "").strip()
        if not path or not os.path.exists(path):
            return {"migrated": 0, "legacy_path": path}

        migrated = 0
        with self._lock():
            if any(True for _ in self._iter_workspaces_unlocked()):
                return {"migrated": 0, "legacy_path": path}

            try:
                with open(path, "r", encoding="utf-8") as f:
                    payload = json.load(f)
            except Exception:
                return {"migrated": 0, "legacy_path": path}

            for item in payload if isinstance(payload, list) else []:
                if not isinstance(item, dict):
                    continue
                system_id = str(item.get("system_id") or "").strip()
                system_name = str(item.get("system_name") or "").strip()
                if not system_id or not system_name:
                    continue
                workspace_path, manifest = self._ensure_workspace_unlocked(system_id=system_id, system_name=system_name)
                self._write_json_unlocked(self._profile_path(workspace_path, "working"), item)
                self._write_revision_unlocked(workspace_path=workspace_path, profile=item, state="working")
                if str(item.get("status") or "").strip() == "published":
                    self._write_json_unlocked(self._profile_path(workspace_path, "published"), item)
                    self._write_revision_unlocked(workspace_path=workspace_path, profile=item, state="published")
                manifest["updated_at"] = current_time_iso()
                self._write_json_unlocked(self._manifest_path(workspace_path), manifest)
                migrated += 1

        return {"migrated": migrated, "legacy_path": path}

    def migrate_legacy_import_history(self, legacy_path: str) -> Dict[str, Any]:
        path = str(legacy_path or "").strip()
        if not path or not os.path.exists(path):
            return {"migrated": 0, "legacy_path": path}

        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except Exception:
            return {"migrated": 0, "legacy_path": path}

        migrated = 0
        if isinstance(payload, dict):
            for system_id, records in payload.items():
                normalized_system_id = str(system_id or "").strip()
                if not normalized_system_id:
                    continue
                found = self._find_workspace_unlocked(system_id=normalized_system_id)
                if not found:
                    continue
                workspace_path, manifest = found
                self._write_json_unlocked(
                    self._history_path(workspace_path),
                    [record for record in records if isinstance(record, dict)],
                )
                _ = manifest
                migrated += len([record for record in records if isinstance(record, dict)])
        return {"migrated": migrated, "legacy_path": path}

    def migrate_legacy_extraction_tasks(self, legacy_path: str) -> Dict[str, Any]:
        path = str(legacy_path or "").strip()
        if not path or not os.path.exists(path):
            return {"migrated": 0, "legacy_path": path}

        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except Exception:
            return {"migrated": 0, "legacy_path": path}

        migrated = 0
        if isinstance(payload, dict):
            for system_id, task in payload.items():
                normalized_system_id = str(system_id or "").strip()
                if not normalized_system_id or not isinstance(task, dict):
                    continue
                found = self._find_workspace_unlocked(system_id=normalized_system_id)
                if not found:
                    continue
                workspace_path, _ = found
                self._write_json_unlocked(self._task_path(workspace_path), task)
                migrated += 1
        return {"migrated": migrated, "legacy_path": path}


_system_profile_repository: Optional[SystemProfileRepository] = None


def get_system_profile_repository() -> SystemProfileRepository:
    global _system_profile_repository
    expected_root = resolve_system_profile_root()
    if (
        _system_profile_repository is None
        or os.path.abspath(_system_profile_repository.root_dir) != expected_root
    ):
        _system_profile_repository = SystemProfileRepository(root_dir=expected_root)
    return _system_profile_repository
