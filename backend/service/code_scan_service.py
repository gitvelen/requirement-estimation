"""
代码扫描服务（Spring Boot MVP）
抽取入口能力目录与对外依赖提示，支持作业状态管理与结果入库。
"""
from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
import uuid
import hashlib
import shutil
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor

try:
    import fcntl
    FCNTL_AVAILABLE = True
except ImportError:
    FCNTL_AVAILABLE = False

from backend.config.config import settings
from backend.service.embedding_service import get_embedding_service
from backend.service.local_vector_store import LocalVectorStore

logger = logging.getLogger(__name__)


DEFAULT_SCAN_OPTIONS = {
    "paths": ["src/main/java"],
    "exclude_dirs": [".git", "target", "build"],
}


class CodeScanService:
    """Spring Boot 代码扫描（最小可用）"""

    def __init__(
        self,
        jobs_path: Optional[str] = None,
        result_dir: Optional[str] = None,
        store_path: Optional[str] = None,
        embedding_service=None,
        vector_store=None,
    ) -> None:
        self.jobs_path = jobs_path or os.path.join(settings.REPORT_DIR, "code_scan_jobs.json")
        self.result_dir = result_dir or os.path.join(settings.REPORT_DIR, "code_scan_results")
        self.extract_dir = os.path.join(settings.REPORT_DIR, "code_scan_extract")
        self.jobs_lock_path = f"{self.jobs_path}.lock"
        self._mutex = threading.RLock()
        self.max_workers = 5
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers, thread_name_prefix="code_scan_worker")

        self.repo_allowlist_roots = self._load_repo_allowlist_roots()
        self.enable_git_url = str(os.getenv("CODE_SCAN_ENABLE_GIT_URL", "false")).lower() == "true"
        self.git_allowed_hosts = self._load_git_allowed_hosts()
        self.max_archive_size_bytes = int(os.getenv("CODE_SCAN_ARCHIVE_MAX_BYTES", str(300 * 1024 * 1024)))
        self.max_archive_files = int(os.getenv("CODE_SCAN_ARCHIVE_MAX_FILES", "20000"))

        self.store_path = store_path or os.path.join(settings.REPORT_DIR, "knowledge_store.json")
        self.embedding_service = embedding_service
        self.vector_store = vector_store or LocalVectorStore(self.store_path)

    @contextmanager
    def _lock(self):
        if FCNTL_AVAILABLE:
            os.makedirs(os.path.dirname(self.jobs_lock_path) or ".", exist_ok=True)
            with open(self.jobs_lock_path, "a") as lock_file:
                fcntl.flock(lock_file, fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(lock_file, fcntl.LOCK_UN)
        else:
            with self._mutex:
                yield

    def _load_jobs_unlocked(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.jobs_path):
            return []
        try:
            with open(self.jobs_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception as exc:
            logger.warning(f"读取代码扫描任务失败: {exc}")
            return []

    def _load_repo_allowlist_roots(self) -> List[str]:
        configured = os.getenv("CODE_SCAN_REPO_ALLOWLIST", "")
        roots = [item.strip() for item in configured.split(",") if item.strip()]
        if not roots:
            roots = [os.path.realpath(os.path.join(settings.REPORT_DIR, "repos"))]
        normalized: List[str] = []
        for root in roots:
            real_root = os.path.realpath(root)
            if real_root not in normalized:
                normalized.append(real_root)
        return normalized

    def _load_git_allowed_hosts(self) -> List[str]:
        configured = os.getenv("CODE_SCAN_GIT_ALLOWED_HOSTS", "")
        hosts = [item.strip().lower() for item in configured.split(",") if item.strip()]
        return hosts

    def _save_jobs_unlocked(self, jobs: List[Dict[str, Any]]) -> None:
        os.makedirs(os.path.dirname(self.jobs_path) or ".", exist_ok=True)
        tmp_path = f"{self.jobs_path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(jobs, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self.jobs_path)

    @contextmanager
    def _jobs_context(self):
        with self._lock():
            jobs = self._load_jobs_unlocked()
            yield jobs
            self._save_jobs_unlocked(jobs)

    def _get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock():
            jobs = self._load_jobs_unlocked()
        for job in jobs:
            if isinstance(job, dict) and job.get("job_id") == job_id:
                return job
        return None

    def _update_job(self, job_id: str, updates: Dict[str, Any]) -> None:
        if not job_id:
            return
        with self._jobs_context() as jobs:
            for job in jobs:
                if isinstance(job, dict) and job.get("job_id") == job_id:
                    job.update(updates)
                    break

    def _normalize_options(self, options: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        normalized: Dict[str, Any] = {
            "paths": list(DEFAULT_SCAN_OPTIONS["paths"]),
            "exclude_dirs": list(DEFAULT_SCAN_OPTIONS["exclude_dirs"]),
        }
        if not isinstance(options, dict):
            return normalized

        raw_paths = options.get("paths")
        if isinstance(raw_paths, list):
            paths = [str(item).strip() for item in raw_paths if str(item).strip()]
            if paths:
                normalized["paths"] = paths

        raw_excludes = options.get("exclude_dirs")
        if isinstance(raw_excludes, list):
            excludes = [str(item).strip() for item in raw_excludes if str(item).strip()]
            if excludes:
                normalized["exclude_dirs"] = excludes

        return normalized

    def _calc_options_hash(self, options: Dict[str, Any]) -> str:
        payload = json.dumps(options or {}, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _calc_repo_hash(self, source_type: str, source_value: str) -> str:
        payload = f"{source_type}:{source_value}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def _find_existing_job(
        self,
        *,
        system_id: str,
        system_name: str,
        repo_hash: str,
        options_hash: str,
    ) -> Optional[Dict[str, Any]]:
        with self._lock():
            jobs = self._load_jobs_unlocked()

        for job in reversed(jobs):
            if str(job.get("system_id") or "") != str(system_id or ""):
                continue
            if str(job.get("system_name") or "") != str(system_name or ""):
                continue
            if str(job.get("repo_hash") or "") != repo_hash:
                continue
            if str(job.get("options_hash") or "") != options_hash:
                continue
            return job
        return None

    def _is_repo_path_allowed(self, repo_path: str) -> bool:
        real_repo_path = os.path.realpath(repo_path)
        for root in self.repo_allowlist_roots:
            if real_repo_path == root or real_repo_path.startswith(root + os.sep):
                return True
        return False

    def _parse_git_host(self, repo_url: str) -> str:
        value = str(repo_url or "").strip()
        if not value:
            return ""
        if value.startswith("ssh://"):
            host_segment = value.split("ssh://", 1)[1]
            host = host_segment.split("/", 1)[0].split(":", 1)[0]
            return host.lower()
        if value.startswith("http://") or value.startswith("https://"):
            host_segment = value.split("//", 1)[1]
            host = host_segment.split("/", 1)[0].split(":", 1)[0]
            return host.lower()

        if "@" in value and ":" in value:
            segment = value.split("@", 1)[1]
            host = segment.split(":", 1)[0]
            return host.lower()
        return ""

    def _is_git_repo_path(self, value: str) -> bool:
        path = str(value or "").strip()
        if not path:
            return False
        if path.startswith(("http://", "https://", "ssh://")):
            return True
        return "@" in path and ":" in path

    def _validate_git_url(self, repo_url: str) -> None:
        value = str(repo_url or "").strip()
        if not value:
            raise ValueError("代码仓库路径不能为空")

        if not self.enable_git_url:
            raise PermissionError("Git URL 扫描未启用")

        is_http = value.startswith("http://") or value.startswith("https://")
        is_ssh = value.startswith("ssh://") or ("@" in value and ":" in value)
        if not (is_http or is_ssh):
            raise PermissionError("Git URL 协议不支持")

        host = self._parse_git_host(value)
        if not host:
            raise PermissionError("Git URL host 无法解析")
        if self.git_allowed_hosts and host not in self.git_allowed_hosts:
            raise PermissionError(f"Git URL host 不在 allowlist: {host}")

    def _get_running_count(self) -> int:
        with self._lock():
            jobs = self._load_jobs_unlocked()
        return sum(1 for job in jobs if job.get("status") == "running")

    def _next_status(self) -> str:
        running_count = self._get_running_count()
        return "running" if running_count < self.max_workers else "queued"

    def run_scan(
        self,
        system_name: str,
        system_id: Optional[str],
        repo_path: str,
        options: Optional[Dict[str, Any]],
        created_by: str,
        force: bool = False,
        repo_source_override: Optional[str] = None,
        repo_hash_override: Optional[str] = None,
        repo_input_override: Optional[str] = None,
        skip_repo_path_validation: bool = False,
    ) -> str:
        if not system_name:
            raise ValueError("system_name不能为空")

        normalized_path = str(repo_path or "").strip()
        if not normalized_path:
            raise ValueError("repo_path无效或不存在")

        normalized_options = self._normalize_options(options)
        options_hash = self._calc_options_hash(normalized_options)

        if repo_source_override:
            repo_source = str(repo_source_override).strip() or "local"
            if repo_source != "git":
                if not os.path.isabs(normalized_path):
                    raise PermissionError("repo_path必须为绝对路径")
                if not os.path.isdir(normalized_path):
                    raise ValueError("repo_path无效或不存在")
                if (not skip_repo_path_validation) and (not self._is_repo_path_allowed(normalized_path)):
                    raise PermissionError("repo_path不在允许目录内")
                local_repo_path = os.path.realpath(normalized_path)
            else:
                local_repo_path = ""
            repo_hash = str(repo_hash_override or "").strip()
            if not repo_hash:
                repo_hash = self._calc_repo_hash(repo_source or "custom", local_repo_path or normalized_path)
        elif self._is_git_repo_path(normalized_path):
            self._validate_git_url(normalized_path)
            repo_source = "git"
            repo_hash = self._calc_repo_hash("git", normalized_path)
            # 当前阶段先记录任务，不执行真实clone；后续若开启可扩展
            local_repo_path = ""
        else:
            if not os.path.isabs(normalized_path):
                raise PermissionError("repo_path必须为绝对路径")
            if not os.path.isdir(normalized_path):
                raise ValueError("repo_path无效或不存在")
            if (not skip_repo_path_validation) and (not self._is_repo_path_allowed(normalized_path)):
                raise PermissionError("repo_path不在允许目录内")
            repo_source = "local"
            repo_hash = self._calc_repo_hash("local", os.path.realpath(normalized_path))
            local_repo_path = os.path.realpath(normalized_path)

        repo_input_value = str(repo_input_override or normalized_path)

        if not force:
            existing = self._find_existing_job(
                system_id=str(system_id or ""),
                system_name=str(system_name or ""),
                repo_hash=repo_hash,
                options_hash=options_hash,
            )
            if existing:
                return str(existing.get("job_id"))

        job_id = f"scan_{uuid.uuid4().hex}"
        created_at = datetime.now().isoformat()
        status = self._next_status()

        job = {
            "job_id": job_id,
            "system_id": system_id or "",
            "system_name": system_name,
            "repo_path": local_repo_path,
            "repo_input": repo_input_value,
            "repo_source": repo_source,
            "repo_hash": repo_hash,
            "options_hash": options_hash,
            "status": status,
            "progress": 0.0,
            "result_path": "",
            "error": "",
            "options": normalized_options,
            "created_by": created_by or "",
            "created_at": created_at,
            "finished_at": "",
            "force": bool(force),
            "ingested": False,
            "ingested_at": "",
        }

        with self._jobs_context() as jobs:
            jobs.append(job)

        self.executor.submit(self._execute_scan, job_id)
        return job_id

    def _execute_scan(self, job_id: str) -> None:
        job = self._get_job(job_id)
        if not job:
            return

        repo_path = job.get("repo_path")
        system_name = job.get("system_name")
        system_id = job.get("system_id")
        options = job.get("options") or {}

        if job.get("status") == "queued":
            while True:
                if self._get_running_count() < self.max_workers:
                    self._update_job(job_id, {"status": "running", "progress": 0.01})
                    break
                current_job = self._get_job(job_id) or {}
                if current_job.get("status") not in {"queued", "running"}:
                    return
                time.sleep(0.2)

        if job.get("repo_source") == "git":
            self._update_job(
                job_id,
                {
                    "status": "failed",
                    "progress": 1.0,
                    "error": "当前环境未启用 Git URL 拉取，请改用本地路径或 repo_archive",
                    "finished_at": datetime.now().isoformat(),
                },
            )
            return

        self._update_job(job_id, {"status": "running", "progress": 0.01})

        try:
            items = self._scan_repo(repo_path, system_name, system_id, options, job_id)
            analysis = self._build_analysis_payload(
                items=items,
                repo_path=str(repo_path or ""),
                system_name=str(system_name or ""),
                system_id=str(system_id or ""),
            )
            metrics = self._build_metrics_payload(job=job, items=items, analysis=analysis)
            os.makedirs(self.result_dir, exist_ok=True)
            result_path = os.path.join(self.result_dir, f"{job_id}.json")
            payload = {
                "system_id": system_id,
                "system_name": system_name,
                "generated_at": datetime.now().isoformat(),
                "items": items,
                "analysis": analysis,
                "metrics": metrics,
            }
            with open(result_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)

            self._update_job(
                job_id,
                {
                    "status": "completed",
                    "progress": 1.0,
                    "result_path": result_path,
                    "finished_at": datetime.now().isoformat(),
                },
            )
        except Exception as exc:
            logger.error(f"代码扫描失败: {exc}")
            self._update_job(
                job_id,
                {
                    "status": "failed",
                    "error": str(exc),
                    "finished_at": datetime.now().isoformat(),
                },
            )

    def _scan_repo(
        self,
        repo_path: str,
        system_name: str,
        system_id: Optional[str],
        options: Dict[str, Any],
        job_id: str,
    ) -> List[Dict[str, Any]]:
        roots = self._resolve_roots(repo_path, options)
        files = self._collect_java_files(roots, options)
        total_files = len(files)
        if total_files == 0:
            return []

        items: List[Dict[str, Any]] = []
        seen = set()
        for idx, file_path in enumerate(files, start=1):
            try:
                file_items = self._scan_java_file(file_path, system_name, system_id)
                for item in file_items:
                    key = (item.get("entry_type"), item.get("entry_id"), item.get("location", {}).get("file"))
                    if key in seen:
                        continue
                    seen.add(key)
                    items.append(item)
            except Exception:
                logger.debug("扫描文件失败: %s", file_path, exc_info=True)
            progress = min(0.99, idx / max(total_files, 1))
            self._update_job(job_id, {"progress": round(progress, 4)})

        return items

    def _safe_ratio(self, numerator: float, denominator: float) -> float:
        if denominator <= 0:
            return 0.0
        return round(max(0.0, min(1.0, numerator / denominator)), 4)

    def _build_analysis_payload(
        self,
        *,
        items: List[Dict[str, Any]],
        repo_path: str,
        system_name: str,
        system_id: str,
    ) -> Dict[str, Any]:
        safe_items = items if isinstance(items, list) else []

        file_paths = set()
        feature_summaries: List[str] = []
        api_entries: List[str] = []
        evidence: List[Dict[str, Any]] = []
        call_nodes = set()
        call_edges: List[Dict[str, Any]] = []
        dep_by_type: Dict[str, int] = {}
        dep_counter: Dict[str, int] = {}
        entity_ops: Dict[str, set] = {}

        for item in safe_items:
            if not isinstance(item, dict):
                continue
            location = item.get("location") if isinstance(item.get("location"), dict) else {}
            file_path = str(location.get("file") or "").strip()
            if file_path:
                file_paths.add(file_path)

            entry_id = str(item.get("entry_id") or "").strip()
            summary = str(item.get("summary") or entry_id).strip()
            entry_type = str(item.get("entry_type") or "").strip()

            if summary and summary not in feature_summaries:
                feature_summaries.append(summary)
            if entry_type == "http_api" and entry_id and entry_id not in api_entries:
                api_entries.append(entry_id)

            if file_path and len(evidence) < 50:
                evidence.append(
                    {
                        "file": file_path,
                        "line": int(location.get("line") or 0),
                        "entry_id": entry_id,
                    }
                )

            caller = entry_id or summary
            if caller:
                call_nodes.add(caller)

            related_calls = item.get("related_calls") if isinstance(item.get("related_calls"), list) else []
            for related in related_calls:
                if not isinstance(related, dict):
                    continue
                dep_type = str(related.get("type") or "unknown").strip() or "unknown"
                dep_target = str(related.get("target") or "unknown").strip() or "unknown"
                dep_key = f"{dep_type}:{dep_target}"
                callee = dep_key
                call_nodes.add(callee)
                if caller and len(call_edges) < 500:
                    call_edges.append(
                        {
                            "caller": caller,
                            "callee": callee,
                            "type": dep_type,
                            "target": dep_target,
                        }
                    )
                dep_by_type[dep_type] = dep_by_type.get(dep_type, 0) + 1
                dep_counter[dep_key] = dep_counter.get(dep_key, 0) + 1

            entity = os.path.splitext(os.path.basename(file_path or ""))[0] or "unknown"
            text = f"{entry_id} {summary}".lower()
            ops = entity_ops.setdefault(entity, set())
            is_read = any(token in text for token in ("get", "query", "find", "list", "select", "read"))
            is_write = any(token in text for token in ("create", "update", "save", "delete", "insert", "write"))
            if is_read:
                ops.add("read")
            if is_write:
                ops.add("write")
            if (not is_read) and (not is_write):
                ops.add("unknown")

        entities = [
            {"entity": entity, "operations": sorted(list(ops))}
            for entity, ops in sorted(entity_ops.items(), key=lambda x: x[0])
        ]

        total_java_files = 0
        if repo_path and os.path.isdir(repo_path):
            for _, _, filenames in os.walk(repo_path):
                for name in filenames:
                    if name.endswith(".java"):
                        total_java_files += 1

        files_with_entries = len(file_paths)
        method_entries = [
            item
            for item in safe_items
            if isinstance(item, dict)
            and str(item.get("entry_type") or "") in {"http_api", "scheduled", "mq_listener"}
        ]
        related_counts = []
        for item in method_entries:
            related = item.get("related_calls") if isinstance(item.get("related_calls"), list) else []
            related_counts.append(len(related))

        method_count = len(method_entries)
        total_related = sum(related_counts)
        max_related = max(related_counts) if related_counts else 0
        avg_related = round((total_related / method_count), 4) if method_count else 0.0
        cyclomatic_values = [1 + count for count in related_counts]
        avg_cc = round((sum(cyclomatic_values) / method_count), 4) if method_count else 0.0
        max_cc = max(cyclomatic_values) if cyclomatic_values else 0
        wmc_total = sum(cyclomatic_values) if cyclomatic_values else 0

        dependency_list = [
            {"dependency": key, "count": count}
            for key, count in sorted(dep_counter.items(), key=lambda x: (-x[1], x[0]))[:100]
        ]

        return {
            "ast_summary": {
                "files_total": total_java_files,
                "files_with_entries": files_with_entries,
                "entry_count": len(safe_items),
                "average_entries_per_file": round((len(safe_items) / files_with_entries), 4)
                if files_with_entries
                else 0.0,
            },
            "call_graph": {
                "nodes": sorted(list(call_nodes))[:200],
                "edges": call_edges,
                "node_count": len(call_nodes),
                "edge_count": len(call_edges),
            },
            "service_dependencies": {
                "by_type": dep_by_type,
                "dependencies": dependency_list,
                "total": sum(dep_by_type.values()),
            },
            "data_flow": {
                "entities": entities,
                "entity_count": len(entities),
            },
            "complexity": {
                "method_count": method_count,
                "wmc_total": wmc_total,
                "avg_cyclomatic_complexity": avg_cc,
                "max_cyclomatic_complexity": max_cc,
                "avg_related_calls": avg_related,
                "max_related_calls": max_related,
            },
            "impact": {
                "systems": [{"system_id": system_id, "system_name": system_name}] if (system_id or system_name) else [],
                "features": feature_summaries[:50],
                "apis": api_entries[:100],
                "evidence": evidence,
            },
        }

    def _build_metrics_payload(
        self,
        *,
        job: Dict[str, Any],
        items: List[Dict[str, Any]],
        analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        ast_summary = analysis.get("ast_summary") if isinstance(analysis.get("ast_summary"), dict) else {}
        call_graph = analysis.get("call_graph") if isinstance(analysis.get("call_graph"), dict) else {}
        data_flow = analysis.get("data_flow") if isinstance(analysis.get("data_flow"), dict) else {}
        complexity = analysis.get("complexity") if isinstance(analysis.get("complexity"), dict) else {}

        files_total = int(ast_summary.get("files_total") or 0)
        files_with_entries = int(ast_summary.get("files_with_entries") or 0)
        method_count = int(complexity.get("method_count") or 0)
        edge_count = int(call_graph.get("edge_count") or 0)
        entity_count = int(data_flow.get("entity_count") or 0)

        m1 = 1.0 if items else 0.0
        m2 = self._safe_ratio(files_with_entries, files_total) if files_total else (1.0 if items else 0.0)
        m3 = self._safe_ratio(edge_count, method_count)
        m4 = self._safe_ratio(entity_count, files_total) if files_total else 0.0
        m5 = 1.0 if method_count > 0 else 0.0

        repo_source = str(job.get("repo_source") or "")
        m6 = 1.0 if repo_source in {"gitlab_archive", "gitlab_compare", "gitlab_raw"} else 1.0

        metrics = {
            "m1": round(m1, 4),
            "m2": round(m2, 4),
            "m3": round(m3, 4),
            "m4": round(m4, 4),
            "m5": round(m5, 4),
            "m6": round(m6, 4),
            "m1_chain_reachability": round(m1, 4),
            "m2_ast_coverage": round(m2, 4),
            "m3_call_graph_coverage": round(m3, 4),
            "m4_data_flow_coverage": round(m4, 4),
            "m5_complexity_coverage": round(m5, 4),
            "m6_gitlab_pass_rate": round(m6, 4),
            "items_count": len(items),
            "files_scanned": files_total,
            "generated_at": datetime.now().isoformat(),
        }
        return metrics

    def _resolve_roots(self, repo_path: str, options: Dict[str, Any]) -> List[str]:
        custom_paths = options.get("paths")
        if isinstance(custom_paths, list) and custom_paths:
            roots = []
            for rel in custom_paths:
                candidate = os.path.join(repo_path, str(rel))
                if os.path.isdir(candidate):
                    roots.append(candidate)
            if roots:
                return roots

        default_root = os.path.join(repo_path, "src", "main", "java")
        if os.path.isdir(default_root):
            return [default_root]
        return [repo_path]

    def _collect_java_files(self, roots: List[str], options: Dict[str, Any]) -> List[str]:
        exclude_dirs = {".git", "target", "build", "out", "node_modules", "dist"}
        if isinstance(options.get("exclude_dirs"), list):
            exclude_dirs |= {str(item) for item in options["exclude_dirs"]}

        files: List[str] = []
        for root in roots:
            for base, dirs, filenames in os.walk(root):
                dirs[:] = [d for d in dirs if d not in exclude_dirs]
                for name in filenames:
                    if not name.endswith(".java"):
                        continue
                    files.append(os.path.join(base, name))
        return files

    def _scan_java_file(self, file_path: str, system_name: str, system_id: Optional[str]) -> List[Dict[str, Any]]:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            return []

        related_calls = self._extract_related_calls(content)
        class_prefix = self._extract_class_request_mapping(content)
        items: List[Dict[str, Any]] = []

        items.extend(
            self._extract_http_entries(content, file_path, system_name, class_prefix, related_calls)
        )
        items.extend(
            self._extract_scheduled_entries(content, file_path, system_name, related_calls)
        )
        items.extend(
            self._extract_listener_entries(content, file_path, system_name, related_calls)
        )
        items.extend(
            self._extract_outbound_entries(content, file_path, system_name, related_calls)
        )

        if system_id:
            for item in items:
                item["system_id"] = system_id
        return items

    def _extract_class_request_mapping(self, content: str) -> str:
        lines = content.splitlines()
        prefix = ""
        for idx, line in enumerate(lines):
            if "@RestController" in line or "@Controller" in line:
                for j in range(idx + 1, min(idx + 15, len(lines))):
                    if "class " in lines[j]:
                        break
                    if "@RequestMapping" in lines[j]:
                        prefix = self._extract_path_from_annotation(lines[j])
                        break
                break
        return prefix or ""

    def _extract_http_entries(
        self,
        content: str,
        file_path: str,
        system_name: str,
        class_prefix: str,
        related_calls: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        entries: List[Dict[str, Any]] = []
        mapping_patterns = [
            ("GET", re.compile(r"@GetMapping\s*(\(([^)]*)\))?", re.DOTALL)),
            ("POST", re.compile(r"@PostMapping\s*(\(([^)]*)\))?", re.DOTALL)),
            ("PUT", re.compile(r"@PutMapping\s*(\(([^)]*)\))?", re.DOTALL)),
            ("DELETE", re.compile(r"@DeleteMapping\s*(\(([^)]*)\))?", re.DOTALL)),
            ("PATCH", re.compile(r"@PatchMapping\s*(\(([^)]*)\))?", re.DOTALL)),
            ("REQUEST", re.compile(r"@RequestMapping\s*(\(([^)]*)\))?", re.DOTALL)),
        ]

        for method, pattern in mapping_patterns:
            for match in pattern.finditer(content):
                params = match.group(2) or ""
                path = self._extract_path_from_params(params)
                http_method = method
                if method == "REQUEST":
                    http_method = self._extract_http_method(params) or "ANY"
                line_no = self._line_number(content, match.start())
                method_name = self._find_method_name(content, match.end())
                full_path = self._join_paths(class_prefix, path)
                if not full_path:
                    full_path = class_prefix or path or "/"
                if self._is_health_endpoint(full_path):
                    continue
                entry_id = f"{http_method} {full_path}"
                entry = {
                    "entry_type": "http_api",
                    "entry_id": entry_id,
                    "owner": system_name,
                    "summary": method_name or entry_id,
                    "keywords": self._build_keywords(method_name, full_path),
                    "location": {"file": file_path, "line": line_no},
                    "related_calls": related_calls,
                }
                entries.append(entry)
        return entries

    def _extract_scheduled_entries(
        self,
        content: str,
        file_path: str,
        system_name: str,
        related_calls: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        entries: List[Dict[str, Any]] = []
        pattern = re.compile(r"@Scheduled\s*\(([^)]*)\)", re.DOTALL)
        for match in pattern.finditer(content):
            params = match.group(1) or ""
            line_no = self._line_number(content, match.start())
            method_name = self._find_method_name(content, match.end())
            hint = self._extract_schedule_hint(params)
            entry_id = f"Scheduled {hint or method_name or ''}".strip()
            entry = {
                "entry_type": "scheduled",
                "entry_id": entry_id,
                "owner": system_name,
                "summary": method_name or entry_id,
                "keywords": self._build_keywords(method_name, hint),
                "location": {"file": file_path, "line": line_no},
                "related_calls": related_calls,
            }
            entries.append(entry)
        return entries

    def _extract_listener_entries(
        self,
        content: str,
        file_path: str,
        system_name: str,
        related_calls: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        entries: List[Dict[str, Any]] = []
        listener_patterns = [
            ("kafka", re.compile(r"@KafkaListener\s*\(([^)]*)\)", re.DOTALL)),
            ("rabbit", re.compile(r"@RabbitListener\s*\(([^)]*)\)", re.DOTALL)),
        ]
        for kind, pattern in listener_patterns:
            for match in pattern.finditer(content):
                params = match.group(1) or ""
                line_no = self._line_number(content, match.start())
                method_name = self._find_method_name(content, match.end())
                topic = self._extract_listener_topic(params)
                entry_id = f"{kind.upper()} Listener {topic or method_name or ''}".strip()
                entry = {
                    "entry_type": "mq_listener",
                    "entry_id": entry_id,
                    "owner": system_name,
                    "summary": method_name or entry_id,
                    "keywords": self._build_keywords(method_name, topic),
                    "location": {"file": file_path, "line": line_no},
                    "related_calls": related_calls,
                }
                entries.append(entry)
        return entries

    def _extract_related_calls(self, content: str) -> List[Dict[str, Any]]:
        related: List[Dict[str, Any]] = []

        for match in re.finditer(r"@FeignClient\s*\(([^)]*)\)", content):
            params = match.group(1) or ""
            target = self._extract_param_value(params, "name") or self._extract_param_value(params, "value")
            related.append(
                {
                    "type": "feign",
                    "target": target or "unknown",
                    "hint": "FeignClient",
                    "line": self._line_number(content, match.start()),
                }
            )

        for match in re.finditer(r"@DubboReference|@Reference", content):
            related.append(
                {
                    "type": "dubbo",
                    "target": "unknown",
                    "hint": "DubboReference",
                    "line": self._line_number(content, match.start()),
                }
            )

        for match in re.finditer(r"RestTemplate|WebClient|HttpClient", content):
            related.append(
                {
                    "type": "http",
                    "target": "external",
                    "hint": "HTTP Client",
                    "line": self._line_number(content, match.start()),
                }
            )

        for match in re.finditer(r"KafkaTemplate|RabbitTemplate|RocketMQTemplate", content):
            token = match.group(0)
            target = "kafka" if token == "KafkaTemplate" else "rabbit" if token == "RabbitTemplate" else "rocketmq"
            related.append(
                {
                    "type": "mq",
                    "target": target,
                    "hint": token,
                    "line": self._line_number(content, match.start()),
                }
            )

        return related

    def _extract_outbound_entries(
        self,
        content: str,
        file_path: str,
        system_name: str,
        related_calls: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        entries: List[Dict[str, Any]] = []
        for call in related_calls or []:
            if not isinstance(call, dict):
                continue
            ctype = call.get("type") or "outbound"
            target = call.get("target") or "unknown"
            entry_id = f"{ctype}:{target}"
            summary = f"{ctype}调用 {target}"
            entries.append(
                {
                    "entry_type": "outbound_call",
                    "entry_id": entry_id,
                    "owner": system_name,
                    "summary": summary,
                    "keywords": self._build_keywords(summary, target),
                    "location": {
                        "file": file_path,
                        "line": call.get("line") or 0,
                    },
                    "related_calls": [call],
                }
            )
        return entries

    def _extract_path_from_annotation(self, line: str) -> str:
        if "(" not in line:
            return ""
        params = line.split("(", 1)[1].rsplit(")", 1)[0]
        return self._extract_path_from_params(params)

    def _extract_path_from_params(self, params: str) -> str:
        if not params:
            return ""
        values = re.findall(r"\"([^\"]+)\"", params)
        if values:
            return values[0]
        return ""

    def _extract_http_method(self, params: str) -> Optional[str]:
        match = re.search(r"RequestMethod\.(GET|POST|PUT|DELETE|PATCH)", params)
        return match.group(1) if match else None

    def _extract_param_value(self, params: str, key: str) -> Optional[str]:
        match = re.search(rf"{key}\s*=\s*\"([^\"]+)\"", params)
        return match.group(1) if match else None

    def _extract_schedule_hint(self, params: str) -> str:
        for key in ("cron", "fixedDelay", "fixedRate"):
            value = self._extract_param_value(params, key)
            if value:
                return f"{key}={value}"
        return ""

    def _extract_listener_topic(self, params: str) -> str:
        for key in ("topics", "topic", "queue", "queues"):
            value = self._extract_param_value(params, key)
            if value:
                return value
        values = re.findall(r"\"([^\"]+)\"", params)
        if values:
            return values[0]
        return ""

    def _find_method_name(self, content: str, start: int) -> str:
        snippet = content[start : start + 500]
        match = re.search(r"\b(?:public|protected|private)?\s*[\w<>\[\]]+\s+(\w+)\s*\(", snippet)
        return match.group(1) if match else ""

    def _line_number(self, content: str, pos: int) -> int:
        return content.count("\n", 0, pos) + 1

    def _join_paths(self, prefix: str, path: str) -> str:
        prefix = (prefix or "").strip()
        path = (path or "").strip()
        if not prefix and not path:
            return ""
        if prefix and not prefix.startswith("/"):
            prefix = "/" + prefix
        if path and not path.startswith("/"):
            path = "/" + path
        combined = (prefix.rstrip("/") + path) if prefix else path
        return combined or ""

    def _is_health_endpoint(self, path: str) -> bool:
        text = (path or "").lower()
        return "actuator" in text or "health" in text or "metrics" in text

    def _build_keywords(self, method_name: str, text: str) -> List[str]:
        keywords = []
        for token in re.split(r"[^a-zA-Z0-9_\u4e00-\u9fa5]+", f"{method_name} {text}"):
            token = token.strip()
            if token and token not in keywords:
                keywords.append(token)
        return keywords[:8]

    def get_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self._get_job(job_id)

    def list_jobs(self) -> List[Dict[str, Any]]:
        with self._lock():
            jobs = self._load_jobs_unlocked()
        jobs.sort(key=lambda x: x.get("created_at") or "", reverse=True)
        return jobs

    def get_result(self, job_id: str) -> Dict[str, Any]:
        job = self._get_job(job_id)
        if not job:
            raise ValueError("任务不存在")
        result_path = job.get("result_path")
        if not result_path or not os.path.exists(result_path):
            raise ValueError("结果文件不存在")
        with open(result_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}

    def commit_result(self, job_id: str) -> Dict[str, Any]:
        job = self._get_job(job_id)
        if not job:
            raise ValueError("任务不存在")
        if job.get("status") != "completed":
            raise ValueError("扫描未完成")

        if job.get("ingested"):
            return {"success": 0, "failed": 0, "errors": []}

        result = self.get_result(job_id)
        items = result.get("items") or []
        if not items:
            self._update_job(job_id, {"ingested": True, "ingested_at": datetime.now().isoformat()})
            return {"success": 0, "failed": 0, "errors": []}

        texts: List[str] = []
        payloads: List[Dict[str, Any]] = []
        for item in items:
            entry_id = item.get("entry_id") or ""
            summary = item.get("summary") or entry_id
            keywords = item.get("keywords") or []
            related = item.get("related_calls") or []
            text = "\n".join([
                str(summary),
                str(entry_id),
                "关键词:" + " ".join([str(k) for k in keywords]),
                "依赖:" + "; ".join([f"{r.get('type')}:{r.get('target')}" for r in related if isinstance(r, dict)]),
            ])
            texts.append(text)
            payloads.append(item)

        embeddings = self._get_embedding_service().batch_generate_embeddings(texts)

        knowledge_items = []
        for idx, item in enumerate(payloads):
            knowledge_items.append(
                {
                    "system_name": item.get("owner") or job.get("system_name") or "",
                    "knowledge_type": "capability_item",
                    "content": texts[idx],
                    "embedding": embeddings[idx] if idx < len(embeddings) else [],
                    "metadata": {
                        "entry_type": item.get("entry_type"),
                        "entry_id": item.get("entry_id"),
                        "keywords": item.get("keywords"),
                        "location": item.get("location"),
                        "related_calls": item.get("related_calls"),
                        "system_id": item.get("system_id") or job.get("system_id"),
                    },
                    "source_file": os.path.basename(job.get("repo_path") or ""),
                    "created_at": datetime.now().isoformat(),
                }
            )

        insert_result = self.vector_store.batch_insert_knowledge(knowledge_items)
        self._update_job(job_id, {"ingested": True, "ingested_at": datetime.now().isoformat()})
        result_with_errors = {
            "success": int(insert_result.get("success", 0)),
            "failed": int(insert_result.get("failed", 0)),
            "errors": [],
        }
        return result_with_errors

    def _safe_extract_archive(self, archive_path: str, target_dir: str) -> None:
        import tarfile
        import zipfile

        os.makedirs(target_dir, exist_ok=True)

        total_size = 0
        total_files = 0

        def _ensure_target(path: str) -> None:
            real_target = os.path.realpath(path)
            real_base = os.path.realpath(target_dir)
            if not (real_target == real_base or real_target.startswith(real_base + os.sep)):
                raise ValueError("压缩包包含非法路径")

        if zipfile.is_zipfile(archive_path):
            with zipfile.ZipFile(archive_path, "r") as zf:
                for member in zf.infolist():
                    total_files += 1
                    if total_files > self.max_archive_files:
                        raise OverflowError("解压文件数超限")
                    total_size += int(member.file_size or 0)
                    if total_size > self.max_archive_size_bytes:
                        raise OverflowError("解压后大小超限")
                    if member.is_dir():
                        continue
                    unix_mode = (member.external_attr >> 16) & 0o170000
                    if unix_mode == 0o120000:
                        raise ValueError("压缩包包含软链接，禁止解压")
                    member_path = os.path.join(target_dir, member.filename)
                    _ensure_target(member_path)
                zf.extractall(target_dir)
            return

        if tarfile.is_tarfile(archive_path):
            with tarfile.open(archive_path, "r:*") as tf:
                members = tf.getmembers()
                for member in members:
                    total_files += 1
                    if total_files > self.max_archive_files:
                        raise OverflowError("解压文件数超限")
                    total_size += int(member.size or 0)
                    if total_size > self.max_archive_size_bytes:
                        raise OverflowError("解压后大小超限")
                    if member.issym() or member.islnk():
                        raise ValueError("压缩包包含链接文件，禁止解压")
                    member_path = os.path.join(target_dir, member.name)
                    _ensure_target(member_path)
                tf.extractall(target_dir)
            return

        raise ValueError("不支持的压缩格式")

    def run_scan_from_archive(
        self,
        *,
        system_name: str,
        system_id: Optional[str],
        archive_path: str,
        options: Optional[Dict[str, Any]],
        created_by: str,
        force: bool = False,
        repo_source_override: Optional[str] = None,
    ) -> str:
        if not os.path.exists(archive_path):
            raise ValueError("repo_archive不存在")

        archive_bytes = b""
        try:
            with open(archive_path, "rb") as archive_file:
                archive_bytes = archive_file.read()
        except Exception as exc:
            raise ValueError("repo_archive读取失败") from exc

        if not archive_bytes:
            raise ValueError("repo_archive为空")

        repo_hash = hashlib.sha256(archive_bytes).hexdigest()
        normalized_options = self._normalize_options(options)
        options_hash = self._calc_options_hash(normalized_options)

        if not force:
            existing = self._find_existing_job(
                system_id=str(system_id or ""),
                system_name=str(system_name or ""),
                repo_hash=repo_hash,
                options_hash=options_hash,
            )
            if existing:
                return str(existing.get("job_id"))

        job_id = f"scan_{uuid.uuid4().hex}"
        extract_path = os.path.join(self.extract_dir, job_id)
        try:
            self._safe_extract_archive(archive_path, extract_path)
        except Exception:
            if os.path.isdir(extract_path):
                shutil.rmtree(extract_path, ignore_errors=True)
            raise

        return self.run_scan(
            system_name=system_name,
            system_id=system_id,
            repo_path=extract_path,
            options=normalized_options,
            created_by=created_by,
            force=force,
            repo_source_override=repo_source_override or "archive",
            repo_hash_override=repo_hash,
            repo_input_override=os.path.basename(archive_path),
            skip_repo_path_validation=True,
        )

    def _get_embedding_service(self):
        if self.embedding_service is None:
            self.embedding_service = get_embedding_service()
        return self.embedding_service


_code_scan_service = None


def get_code_scan_service() -> CodeScanService:
    global _code_scan_service
    if _code_scan_service is None:
        _code_scan_service = CodeScanService()
    return _code_scan_service
