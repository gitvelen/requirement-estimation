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
import uuid
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
        self.jobs_lock_path = f"{self.jobs_path}.lock"
        self._mutex = threading.RLock()
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="code_scan_worker")

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

    def run_scan(
        self,
        system_name: str,
        system_id: Optional[str],
        repo_path: str,
        options: Optional[Dict[str, Any]],
        created_by: str,
    ) -> str:
        if not repo_path or not os.path.isdir(repo_path):
            raise ValueError("repo_path无效或不存在")
        if not system_name:
            raise ValueError("system_name不能为空")

        job_id = f"scan_{uuid.uuid4().hex}"
        created_at = datetime.now().isoformat()

        job = {
            "job_id": job_id,
            "system_id": system_id or "",
            "system_name": system_name,
            "repo_path": repo_path,
            "status": "queued",
            "progress": 0.0,
            "result_path": "",
            "error": "",
            "options": options or {},
            "created_by": created_by or "",
            "created_at": created_at,
            "finished_at": "",
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

        self._update_job(job_id, {"status": "running", "progress": 0.01})

        try:
            items = self._scan_repo(repo_path, system_name, system_id, options, job_id)
            os.makedirs(self.result_dir, exist_ok=True)
            result_path = os.path.join(self.result_dir, f"{job_id}.json")
            payload = {
                "system_id": system_id,
                "system_name": system_name,
                "generated_at": datetime.now().isoformat(),
                "items": items,
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

        result = self.get_result(job_id)
        items = result.get("items") or []
        if not items:
            return {"success": 0, "failed": 0}

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

        return self.vector_store.batch_insert_knowledge(knowledge_items)

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
