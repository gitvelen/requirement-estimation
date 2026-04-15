from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    import fcntl

    FCNTL_AVAILABLE = True
except ImportError:  # pragma: no cover
    FCNTL_AVAILABLE = False

from backend.config.config import settings
from backend.service.system_profile_repository import (
    SystemProfileRepository,
    resolve_system_profile_root,
)
from backend.utils.time_utils import current_time, current_time_iso


def resolve_profile_artifact_root(root_dir: Optional[str] = None) -> str:
    return resolve_system_profile_root(root_dir)


class ProfileArtifactService:
    INDEX_FILE = "index.json"
    MAX_FILE_NAME_LENGTH = 240
    CANDIDATE_CATEGORIES = {"documents", "authoritative", "projections"}

    def __init__(self, root_dir: Optional[str] = None) -> None:
        self.root_dir = resolve_profile_artifact_root(root_dir)
        self.lock_path = os.path.join(self.root_dir, ".profile_artifacts.lock")
        self.repository = SystemProfileRepository(root_dir=self.root_dir)
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

    def _sanitize_segment(self, value: str, fallback: str = "unknown") -> str:
        text = str(value or "").strip()
        if not text:
            return fallback
        text = text.replace("/", "_").replace("\\", "_")
        text = re.sub(r"[^0-9a-zA-Z_\-\.\u4e00-\u9fa5]+", "_", text)
        text = re.sub(r"_+", "_", text).strip("_")
        return text[:64] or fallback

    def _resolve_storage_segment(self, system_id: str) -> str:
        normalized_system_id = str(system_id or "").strip()
        if not normalized_system_id:
            return "system"
        try:
            from backend.api import system_routes

            owner_info = system_routes.resolve_system_owner(system_id=normalized_system_id)
            system_name = str((owner_info or {}).get("system_name") or "").strip()
            if system_name:
                return self._sanitize_segment(system_name, fallback="system")
        except Exception:
            pass
        return self._sanitize_segment(normalized_system_id, fallback="system")

    def _resolve_system_name(self, system_id: str, fallback: str = "") -> str:
        normalized_fallback = str(fallback or "").strip()
        if normalized_fallback:
            return normalized_fallback
        try:
            from backend.api import system_routes

            owner_info = system_routes.resolve_system_owner(system_id=str(system_id or "").strip())
        except Exception:
            owner_info = {}
        return str((owner_info or {}).get("system_name") or "").strip() or str(system_id or "").strip()

    def _workspace_path(self, system_id: str, system_name: str = "") -> str:
        normalized_system_id = str(system_id or "").strip()
        normalized_system_name = str(system_name or "").strip()
        existing_path = self.repository.get_workspace_path(system_id=normalized_system_id)
        if existing_path and not normalized_system_name:
            return existing_path
        workspace_path, _ = self.repository.ensure_workspace(
            system_id=normalized_system_id,
            system_name=self._resolve_system_name(system_id, fallback=normalized_system_name),
        )
        return workspace_path

    def _system_dir(self, layer: str, system_id: str) -> str:
        normalized_layer = str(layer or "").strip().lower()
        workspace_path = self._workspace_path(system_id)
        if normalized_layer == "raw":
            path = os.path.join(workspace_path, "source", "documents")
        elif normalized_layer == "wiki":
            path = os.path.join(workspace_path, "candidate")
        elif normalized_layer == "output":
            path = os.path.join(workspace_path, "audit")
        else:
            path = os.path.join(workspace_path, normalized_layer)
        os.makedirs(path, exist_ok=True)
        return path

    def _index_path(self, layer: str, system_id: str) -> str:
        normalized_layer = str(layer or "").strip().lower()
        workspace_path = self._workspace_path(system_id)
        if normalized_layer == "raw":
            return os.path.join(workspace_path, "source", self.INDEX_FILE)
        if normalized_layer == "wiki":
            return os.path.join(workspace_path, "candidate", self.INDEX_FILE)
        if normalized_layer == "output":
            return os.path.join(workspace_path, "audit", self.INDEX_FILE)
        return os.path.join(self._system_dir(normalized_layer, system_id), self.INDEX_FILE)

    def _candidate_index_path(self, system_id: str) -> str:
        workspace_path = self._workspace_path(system_id)
        return os.path.join(workspace_path, "candidate", self.INDEX_FILE)

    def _load_candidate_index_unlocked(self, system_id: str) -> List[Dict[str, Any]]:
        return self._load_index_file(self._candidate_index_path(system_id))

    def _save_candidate_index_unlocked(self, system_id: str, items: List[Dict[str, Any]]) -> None:
        self._write_json_unlocked(self._candidate_index_path(system_id), items)

    def _normalize_candidate_category(self, category: str) -> str:
        normalized = str(category or "").strip().lower()
        if normalized not in self.CANDIDATE_CATEGORIES:
            raise ValueError("candidate_category不支持")
        return normalized

    def _candidate_record_path(
        self,
        *,
        system_id: str,
        category: str,
        artifact_id: str,
        file_name: str,
    ) -> str:
        normalized_category = self._normalize_candidate_category(category)
        workspace_path = self._workspace_path(system_id)
        compact_id = artifact_id.split("_", 1)[-1][:12]
        if normalized_category == "documents":
            bundle_dir = os.path.join(workspace_path, "candidate", "documents", f"doc_cand_{compact_id}")
            os.makedirs(bundle_dir, exist_ok=True)
            return os.path.join(bundle_dir, file_name)
        if normalized_category == "authoritative":
            bundle_dir = os.path.join(workspace_path, "candidate", "authoritative", f"auth_cand_{compact_id}")
            os.makedirs(bundle_dir, exist_ok=True)
            return os.path.join(bundle_dir, file_name)
        records_dir = os.path.join(workspace_path, "candidate", "projections", "records")
        os.makedirs(records_dir, exist_ok=True)
        compact_now = current_time_iso().replace("-", "").replace(":", "").replace(".", "")
        return os.path.join(records_dir, f"{compact_now}__{artifact_id}.json")

    def _load_index_unlocked(self, layer: str, system_id: str) -> List[Dict[str, Any]]:
        path = self._index_path(layer, system_id)
        if not os.path.exists(path):
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            if not isinstance(payload, list):
                return []
            return [item for item in payload if isinstance(item, dict)]
        except Exception:
            return []

    def _save_index_unlocked(self, layer: str, system_id: str, items: List[Dict[str, Any]]) -> None:
        path = self._index_path(layer, system_id)
        self._write_json_unlocked(path, items)

    def _write_json_unlocked(self, path: str, payload: Any) -> None:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        tmp = f"{path}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)

    def _write_jsonl_file(self, path: str, rows: List[Dict[str, Any]]) -> None:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False))
                f.write("\n")

    def _read_json_file(self, path: str) -> Any:
        normalized_path = str(path or "").strip()
        if not normalized_path or not os.path.exists(normalized_path):
            return None
        try:
            with open(normalized_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def _load_index_file(self, path: str) -> List[Dict[str, Any]]:
        if not os.path.exists(path):
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            if not isinstance(payload, list):
                return []
            return [item for item in payload if isinstance(item, dict)]
        except Exception:
            return []

    def _replace_relative_prefix(self, value: Any, *, old_prefix: str, new_prefix: str) -> Any:
        text = str(value or "").strip()
        if not text:
            return value
        normalized_old = old_prefix.rstrip("/")
        normalized_new = new_prefix.rstrip("/")
        if text == normalized_old:
            return normalized_new
        if text.startswith(f"{normalized_old}/"):
            return f"{normalized_new}{text[len(normalized_old):]}"
        return value

    def _rewrite_runtime_execution_paths_unlocked(
        self,
        *,
        runtime_execution_path: str,
        prefix_map: Dict[str, str],
    ) -> None:
        if not prefix_map or not os.path.exists(runtime_execution_path):
            return
        try:
            with open(runtime_execution_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except Exception:
            return
        if not isinstance(payload, list):
            return

        changed = False
        for item in payload:
            if not isinstance(item, dict):
                continue
            snapshot = item.get("input_snapshot")
            if not isinstance(snapshot, dict):
                continue
            current_path = snapshot.get("raw_artifact_path")
            if current_path is None:
                continue
            updated_path = current_path
            for old_prefix, new_prefix in prefix_map.items():
                replaced = self._replace_relative_prefix(
                    updated_path,
                    old_prefix=old_prefix,
                    new_prefix=new_prefix,
                )
                if replaced != updated_path:
                    updated_path = replaced
                    break
            if updated_path != current_path:
                snapshot["raw_artifact_path"] = updated_path
                changed = True

        if changed:
            self._write_json_unlocked(runtime_execution_path, payload)

    def migrate_legacy_layout(
        self,
        *,
        legacy_root_dir: Optional[str] = None,
        runtime_execution_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        legacy_root = os.path.abspath(str(legacy_root_dir or os.getcwd()).strip() or os.getcwd())
        runtime_path = str(runtime_execution_path or os.path.join(settings.REPORT_DIR, "runtime_executions.json")).strip()
        migrated_layers: Dict[str, int] = {"raw": 0, "wiki": 0, "output": 0}
        raw_prefix_map: Dict[str, str] = {}

        with self._lock():
            for layer in ("raw", "wiki", "output"):
                legacy_layer_dir = os.path.join(legacy_root, layer)
                if not os.path.isdir(legacy_layer_dir):
                    continue

                for legacy_segment in sorted(os.listdir(legacy_layer_dir)):
                    legacy_dir = os.path.join(legacy_layer_dir, legacy_segment)
                    if not os.path.isdir(legacy_dir):
                        continue

                    legacy_index_path = os.path.join(legacy_dir, self.INDEX_FILE)
                    legacy_items = self._load_index_file(legacy_index_path)
                    if not legacy_items:
                        continue

                    system_id = ""
                    for item in legacy_items:
                        candidate = str(item.get("system_id") or "").strip()
                        if candidate:
                            system_id = candidate
                            break
                    system_id = system_id or str(legacy_segment or "").strip()
                    existing_profile = self.repository.load_profile(state="working", system_id=system_id) or self.repository.load_profile(
                        state="published",
                        system_id=system_id,
                    )
                    system_name = (
                        str((existing_profile or {}).get("system_name") or "").strip()
                        or self._resolve_system_name(system_id, fallback=str(legacy_segment or "").strip())
                    )
                    workspace_path, _ = self.repository.ensure_workspace(
                        system_id=system_id,
                        system_name=system_name,
                    )
                    workspace_segment = os.path.relpath(workspace_path, self.root_dir)
                    safe_legacy_segment = self._sanitize_segment(legacy_segment, fallback="legacy")
                    if layer == "raw":
                        target_dir = os.path.join(workspace_path, "source", "documents", f"legacy_{safe_legacy_segment}")
                    elif layer == "wiki":
                        target_dir = os.path.join(workspace_path, "candidate", f"legacy_{safe_legacy_segment}")
                    else:
                        target_dir = os.path.join(workspace_path, "audit", f"legacy_{safe_legacy_segment}")
                    if os.path.abspath(legacy_dir) == os.path.abspath(target_dir):
                        continue

                    os.makedirs(os.path.dirname(target_dir) or ".", exist_ok=True)
                    if os.path.exists(target_dir):
                        shutil.copytree(legacy_dir, target_dir, dirs_exist_ok=True)
                        shutil.rmtree(legacy_dir)
                    else:
                        shutil.move(legacy_dir, target_dir)

                    old_prefix = f"{layer}/{legacy_segment}"
                    new_prefix = os.path.relpath(target_dir, self.root_dir).replace(os.sep, "/")
                    migrated_items: List[Dict[str, Any]] = []
                    for item in legacy_items:
                        migrated_item = dict(item)
                        if "path" in migrated_item:
                            migrated_item["path"] = self._replace_relative_prefix(
                                migrated_item.get("path"),
                                old_prefix=old_prefix,
                                new_prefix=new_prefix,
                            )
                        if "latest_path" in migrated_item:
                            latest_path = str(migrated_item.get("latest_path") or "").strip()
                            relative_latest = latest_path[len(old_prefix) + 1 :] if latest_path.startswith(f"{old_prefix}/") else ""
                            if relative_latest:
                                migrated_latest_source = os.path.join(target_dir, relative_latest)
                                if layer == "wiki":
                                    latest_target = os.path.join(
                                        workspace_path,
                                        "candidate",
                                        "latest",
                                        os.path.basename(relative_latest) or "candidate_profile.json",
                                    )
                                else:
                                    latest_target = os.path.join(workspace_path, "audit", relative_latest)
                                if os.path.exists(migrated_latest_source):
                                    os.makedirs(os.path.dirname(latest_target) or ".", exist_ok=True)
                                    shutil.copy2(migrated_latest_source, latest_target)
                                    migrated_item["latest_path"] = os.path.relpath(latest_target, self.root_dir).replace(os.sep, "/")
                                else:
                                    migrated_item["latest_path"] = self._replace_relative_prefix(
                                        migrated_item.get("latest_path"),
                                        old_prefix=old_prefix,
                                        new_prefix=new_prefix,
                                    )
                        migrated_items.append(migrated_item)

                    existing_items = self._load_index_unlocked(layer, system_id)
                    merged_by_id: Dict[str, Dict[str, Any]] = {}
                    for existing_item in existing_items:
                        artifact_id = str(existing_item.get("artifact_id") or "").strip()
                        if artifact_id:
                            merged_by_id[artifact_id] = dict(existing_item)
                    for migrated_item in migrated_items:
                        artifact_id = str(migrated_item.get("artifact_id") or "").strip()
                        if artifact_id:
                            merged_by_id[artifact_id] = migrated_item
                    merged_items = list(merged_by_id.values()) if merged_by_id else migrated_items
                    merged_items.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
                    self._save_index_unlocked(layer, system_id, merged_items)
                    migrated_layers[layer] += 1
                    if layer == "raw":
                        raw_prefix_map[old_prefix] = new_prefix

            self._rewrite_runtime_execution_paths_unlocked(
                runtime_execution_path=runtime_path,
                prefix_map=raw_prefix_map,
            )

        return {
            "legacy_root_dir": legacy_root,
            "root_dir": self.root_dir,
            "migrated_layers": migrated_layers,
        }

    def _build_raw_filename(self, *, imported_at: datetime, doc_type: str, source_name: str, content_hash: str) -> str:
        timestamp = imported_at.strftime("%Y%m%dT%H%M%S")
        safe_doc_type = self._sanitize_segment(doc_type, fallback="document")
        safe_source_name = self._sanitize_segment(source_name, fallback="source")
        suffix = content_hash[:8]
        ext = os.path.splitext(str(source_name or "").strip())[1].lower() or ".bin"
        filename = f"{timestamp}__{safe_doc_type}__{suffix}__{safe_source_name}{ext}"
        if len(filename) > self.MAX_FILE_NAME_LENGTH:
            trimmed = safe_source_name[: max(16, self.MAX_FILE_NAME_LENGTH - len(timestamp) - len(safe_doc_type) - len(suffix) - 8)]
            filename = f"{timestamp}__{safe_doc_type}__{suffix}__{trimmed}{ext}"
        return filename

    def write_raw_document(
        self,
        *,
        system_id: str,
        doc_type: str,
        source_name: str,
        file_content: bytes,
        operator_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        normalized_system_id = str(system_id or "").strip()
        if not normalized_system_id:
            raise ValueError("system_id不能为空")

        content = file_content if isinstance(file_content, (bytes, bytearray)) else b""
        if not content:
            raise ValueError("file_content不能为空")

        imported_at = current_time()
        imported_at_iso = imported_at.isoformat()
        content_hash = hashlib.sha256(content).hexdigest()
        source_name_text = str(source_name or "").strip() or "document"
        file_name = self._build_raw_filename(
            imported_at=imported_at,
            doc_type=doc_type,
            source_name=source_name_text,
            content_hash=content_hash,
        )

        system_name = str((metadata or {}).get("system_name") or "").strip()
        workspace_path = self._workspace_path(normalized_system_id, system_name=system_name)

        with self._lock():
            artifact_id = f"raw_{uuid.uuid4().hex}"
            source_dir = os.path.join(workspace_path, "source", "documents", f"src_doc_{artifact_id.split('_', 1)[1][:12]}")
            os.makedirs(source_dir, exist_ok=True)

            file_path = os.path.join(source_dir, "raw.bin")
            with open(file_path, "wb") as f:
                f.write(content)

            meta_path = os.path.join(source_dir, "meta.json")
            meta_payload = {
                "artifact_id": artifact_id,
                "system_id": normalized_system_id,
                "system_name": system_name or self._resolve_system_name(normalized_system_id),
                "doc_type": str(doc_type or "").strip() or "unknown",
                "source_name": source_name_text,
                "original_file_name": file_name,
                "sha256": content_hash,
                "size": len(content),
                "created_at": imported_at_iso,
                "operator_id": str(operator_id or "").strip() or "unknown",
                "metadata": metadata if isinstance(metadata, dict) else {},
            }
            self._write_json_unlocked(meta_path, meta_payload)

            record = {
                "artifact_id": artifact_id,
                "layer": "raw",
                "system_id": normalized_system_id,
                "doc_type": str(doc_type or "").strip() or "unknown",
                "source_name": source_name_text,
                "path": os.path.relpath(file_path, self.root_dir),
                "meta_path": os.path.relpath(meta_path, self.root_dir),
                "sha256": content_hash,
                "size": len(content),
                "created_at": imported_at_iso,
                "operator_id": str(operator_id or "").strip() or "unknown",
                "status": "active",
                "metadata": metadata if isinstance(metadata, dict) else {},
            }

            items = self._load_index_unlocked("raw", normalized_system_id)
            items.append(record)
            items.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
            self._save_index_unlocked("raw", normalized_system_id, items)

        return dict(record)

    def append_layer_record(
        self,
        *,
        layer: str,
        system_id: str,
        payload: Dict[str, Any],
        operator_id: str,
        source_artifact_id: Optional[str] = None,
        latest_file_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        normalized_layer = str(layer or "").strip().lower()
        if normalized_layer not in {"wiki", "output"}:
            raise ValueError("layer仅支持wiki或output")

        normalized_system_id = str(system_id or "").strip()
        if not normalized_system_id:
            raise ValueError("system_id不能为空")

        now = current_time_iso()
        record = {
            "artifact_id": f"{normalized_layer}_{uuid.uuid4().hex}",
            "layer": normalized_layer,
            "system_id": normalized_system_id,
            "created_at": now,
            "operator_id": str(operator_id or "").strip() or "system",
            "source_artifact_id": str(source_artifact_id or "").strip() or None,
            "payload": payload if isinstance(payload, dict) else {},
            "status": "active",
        }

        with self._lock():
            layer_dir = self._system_dir(normalized_layer, normalized_system_id)
            records_dir = os.path.join(layer_dir, "records")
            compact_now = now.replace("-", "").replace(":", "").replace(".", "")
            os.makedirs(records_dir, exist_ok=True)
            if normalized_layer == "wiki":
                job_dir = os.path.join(layer_dir, "jobs", record["artifact_id"])
                os.makedirs(job_dir, exist_ok=True)
                record_path = os.path.join(job_dir, "payload.json")
            else:
                record_path = os.path.join(records_dir, f"{compact_now}__{record['artifact_id']}.json")
            self._write_json_unlocked(record_path, record["payload"])
            record["path"] = os.path.relpath(record_path, self.root_dir)
            if latest_file_name:
                latest_path = os.path.join(layer_dir, "latest", str(latest_file_name or "").strip()) if normalized_layer == "wiki" else os.path.join(layer_dir, str(latest_file_name or "").strip())
                self._write_json_unlocked(latest_path, record["payload"])
                record["latest_path"] = os.path.relpath(latest_path, self.root_dir)

            items = self._load_index_unlocked(normalized_layer, normalized_system_id)
            items.append(record)
            items.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
            self._save_index_unlocked(normalized_layer, normalized_system_id, items)

        return dict(record)

    def list_layer_records(self, *, layer: str, system_id: str, include_archived: bool = False) -> List[Dict[str, Any]]:
        normalized_layer = str(layer or "").strip().lower()
        if normalized_layer not in {"raw", "wiki", "output"}:
            raise ValueError("layer不支持")
        normalized_system_id = str(system_id or "").strip()
        if not normalized_system_id:
            raise ValueError("system_id不能为空")

        with self._lock():
            items = self._load_index_unlocked(normalized_layer, normalized_system_id)

        if include_archived:
            return [dict(item) for item in items]
        return [dict(item) for item in items if str(item.get("status") or "active") == "active"]

    def append_candidate_record(
        self,
        *,
        system_id: str,
        category: str,
        payload: Dict[str, Any],
        operator_id: str,
        source_artifact_id: Optional[str] = None,
        record_file_name: Optional[str] = None,
        latest_payloads: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        normalized_system_id = str(system_id or "").strip()
        if not normalized_system_id:
            raise ValueError("system_id不能为空")
        normalized_category = self._normalize_candidate_category(category)

        artifact_prefix = {
            "documents": "candidate",
            "authoritative": "authoritative",
            "projections": "projection",
        }[normalized_category]
        artifact_id = f"{artifact_prefix}_{uuid.uuid4().hex}"
        now = current_time_iso()
        file_name = str(record_file_name or "").strip()
        if not file_name:
            file_name = {
                "documents": "document_candidate.json",
                "authoritative": "authoritative_candidate.json",
                "projections": "system_projection.json",
            }[normalized_category]

        with self._lock():
            record_path = self._candidate_record_path(
                system_id=normalized_system_id,
                category=normalized_category,
                artifact_id=artifact_id,
                file_name=file_name,
            )
            self._write_json_unlocked(record_path, payload if isinstance(payload, dict) else {})

            latest_paths: List[str] = []
            workspace_path = self._workspace_path(normalized_system_id)
            latest_dir = os.path.join(workspace_path, "candidate", "latest")
            os.makedirs(latest_dir, exist_ok=True)
            if isinstance(latest_payloads, dict):
                for latest_file_name, latest_payload in latest_payloads.items():
                    normalized_name = str(latest_file_name or "").strip()
                    if not normalized_name:
                        continue
                    latest_path = os.path.join(latest_dir, normalized_name)
                    self._write_json_unlocked(latest_path, latest_payload)
                    latest_paths.append(os.path.relpath(latest_path, self.root_dir))

            record = {
                "artifact_id": artifact_id,
                "layer": "candidate",
                "category": normalized_category,
                "system_id": normalized_system_id,
                "created_at": now,
                "operator_id": str(operator_id or "").strip() or "system",
                "source_artifact_id": str(source_artifact_id or "").strip() or None,
                "payload": payload if isinstance(payload, dict) else {},
                "path": os.path.relpath(record_path, self.root_dir),
                "status": "active",
                "metadata": metadata if isinstance(metadata, dict) else {},
            }
            if latest_paths:
                record["latest_path"] = latest_paths[0]
                record["latest_paths"] = latest_paths

            items = self._load_candidate_index_unlocked(normalized_system_id)
            items.append(record)
            items.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
            self._save_candidate_index_unlocked(normalized_system_id, items)

        return dict(record)

    def write_candidate_support_file(
        self,
        *,
        system_id: str,
        category: str,
        artifact_id: str,
        file_name: str,
        payload: Any,
    ) -> str:
        normalized_system_id = str(system_id or "").strip()
        normalized_artifact_id = str(artifact_id or "").strip()
        normalized_file_name = str(file_name or "").strip()
        if not normalized_system_id or not normalized_artifact_id or not normalized_file_name:
            raise ValueError("candidate_support_file参数不能为空")

        with self._lock():
            path = self._candidate_record_path(
                system_id=normalized_system_id,
                category=category,
                artifact_id=normalized_artifact_id,
                file_name=normalized_file_name,
            )
            if normalized_file_name.endswith(".jsonl") and isinstance(payload, list):
                self._write_jsonl_file(path, payload)
            else:
                self._write_json_unlocked(path, payload)
        return os.path.relpath(path, self.root_dir)

    def list_candidate_records(
        self,
        *,
        system_id: str,
        category: Optional[str] = None,
        include_archived: bool = False,
    ) -> List[Dict[str, Any]]:
        normalized_system_id = str(system_id or "").strip()
        if not normalized_system_id:
            raise ValueError("system_id不能为空")
        normalized_category = self._normalize_candidate_category(category) if category else None

        with self._lock():
            items = self._load_candidate_index_unlocked(normalized_system_id)

        filtered = []
        for item in items:
            if not isinstance(item, dict):
                continue
            if normalized_category and str(item.get("category") or "").strip() != normalized_category:
                continue
            if not include_archived and str(item.get("status") or "active") != "active":
                continue
            filtered.append(dict(item))
        return filtered

    def load_latest_candidate_snapshot(self, *, system_id: str, file_name: str) -> Any:
        normalized_system_id = str(system_id or "").strip()
        normalized_file_name = str(file_name or "").strip()
        if not normalized_system_id or not normalized_file_name:
            return None
        workspace_path = self._workspace_path(normalized_system_id)
        path = os.path.join(workspace_path, "candidate", "latest", normalized_file_name)
        return self._read_json_file(path)

    def archive_raw_artifact(
        self,
        *,
        system_id: str,
        artifact_id: str,
        operator_id: str,
        reason: str,
    ) -> Dict[str, Any]:
        normalized_system_id = str(system_id or "").strip()
        normalized_artifact_id = str(artifact_id or "").strip()
        if not normalized_system_id:
            raise ValueError("system_id不能为空")
        if not normalized_artifact_id:
            raise ValueError("artifact_id不能为空")

        now = current_time_iso()
        with self._lock():
            items = self._load_index_unlocked("raw", normalized_system_id)
            target: Optional[Dict[str, Any]] = None
            for item in items:
                if str(item.get("artifact_id") or "").strip() == normalized_artifact_id:
                    target = item
                    break
            if target is None:
                raise ValueError("artifact_not_found")

            target["status"] = "archived"
            target["archived_at"] = now
            target["archived_by"] = str(operator_id or "").strip() or "unknown"
            target["archive_reason"] = str(reason or "").strip() or "manual_archive"
            self._save_index_unlocked("raw", normalized_system_id, items)

        return dict(target)


_profile_artifact_service: Optional[ProfileArtifactService] = None


def get_profile_artifact_service() -> ProfileArtifactService:
    global _profile_artifact_service
    expected_root = resolve_profile_artifact_root()
    if (
        _profile_artifact_service is None
        or os.path.abspath(_profile_artifact_service.root_dir) != expected_root
    ):
        _profile_artifact_service = ProfileArtifactService(root_dir=expected_root)
        if not str(getattr(settings, "PROFILE_ARTIFACT_ROOT", "") or "").strip():
            _profile_artifact_service.migrate_legacy_layout()
    return _profile_artifact_service
