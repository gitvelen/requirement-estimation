from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml
from openpyxl import Workbook

try:
    import fcntl

    FCNTL_AVAILABLE = True
except ImportError:  # pragma: no cover
    FCNTL_AVAILABLE = False

from backend.config.config import settings
from metachange_inform.metachange_inform import MetadataChangeInform

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
METADATA_GOVERNANCE_DIR = PROJECT_ROOT / "metachange_inform"
METADATA_GOVERNANCE_CONFIG_PATH = METADATA_GOVERNANCE_DIR / "config.yaml"

DATA_DIR = PROJECT_ROOT / "data"
JOBS_STORE_PATH = DATA_DIR / "metadata_governance_jobs.json"
LATEST_STORE_PATH = DATA_DIR / "metadata_governance_latest.json"
RESULTS_DIR = DATA_DIR / "metadata_governance_results"

SCOPE_TO_HOURS = {
    "new": 0,
    "stock": 0,
    "all": 0,
}
HOURS_TO_SCOPE = {value: key for key, value in SCOPE_TO_HOURS.items()}
EXECUTION_TIME_TO_SCHEDULE = {
    "now": "0 23 * * *",
    "daily_23": "0 23 * * *",
}


@dataclass
class MetadataGovernanceRunResult:
    scheduled: bool
    execution_time: str
    output: Optional[BytesIO] = None
    filename: Optional[str] = None
    job_id: Optional[str] = None


@dataclass
class _Job:
    job_id: str
    status: str  # pending | running | completed | failed
    created_at: str
    completed_at: Optional[str] = None
    error: Optional[str] = None
    filename: Optional[str] = None


class _MetadataGovernanceDailyScheduler:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._last_run_key: Optional[str] = None
        self._service: Optional["MetadataGovernanceService"] = None

    def ensure_daily_job(self, service: "MetadataGovernanceService") -> None:
        with self._lock:
            self._service = service
            if self._thread and self._thread.is_alive():
                return
            self._stop_event = threading.Event()
            self._thread = threading.Thread(target=self._run_loop, name="metadata-governance-daily-job", daemon=True)
            self._thread.start()

    def _run_loop(self) -> None:
        while not self._stop_event.wait(timeout=30):
            service = self._service
            if service is None:
                continue
            now = datetime.now()
            if now.hour != 23 or now.minute != 0:
                continue
            run_key = now.strftime("%Y-%m-%d-%H-%M")
            if self._last_run_key == run_key:
                continue
            self._last_run_key = run_key
            try:
                service.run_analysis_now(persist_report=True)
            except Exception:
                continue


_daily_scheduler = _MetadataGovernanceDailyScheduler()


class MetadataGovernanceService:
    def __init__(self, config_path: Path | None = None, *, data_dir: Path | None = None) -> None:
        self.config_path = Path(config_path or METADATA_GOVERNANCE_CONFIG_PATH)
        self._data_dir = Path(data_dir) if data_dir else DATA_DIR
        self._jobs_store_path = self._data_dir / "metadata_governance_jobs.json"
        self._latest_store_path = self._data_dir / "metadata_governance_latest.json"
        self._results_dir = self._data_dir / "metadata_governance_results"
        self._lock_path = str(self._jobs_store_path) + ".lock"
        self._mutex = threading.RLock()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="mgov")

    # ── persistence primitives (same pattern as RuntimeExecutionService) ──

    @contextmanager
    def _lock(self):
        if FCNTL_AVAILABLE:
            os.makedirs(os.path.dirname(self._lock_path) or ".", exist_ok=True)
            with open(self._lock_path, "a", encoding="utf-8") as lock_file:
                fcntl.flock(lock_file, fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(lock_file, fcntl.LOCK_UN)
        else:
            with self._mutex:
                yield

    def _load_jobs_unlocked(self) -> Dict[str, Any]:
        if not os.path.exists(self._jobs_store_path):
            return {}
        with open(self._jobs_store_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        return payload if isinstance(payload, dict) else {}

    def _save_jobs_unlocked(self, payload: Dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(str(self._jobs_store_path)) or ".", exist_ok=True)
        tmp_path = str(self._jobs_store_path) + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, str(self._jobs_store_path))

    def _load_latest_unlocked(self) -> Dict[str, Any]:
        if not os.path.exists(self._latest_store_path):
            return {}
        with open(self._latest_store_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        return payload if isinstance(payload, dict) else {}

    def _save_latest_unlocked(self, payload: Dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(str(self._latest_store_path)) or ".", exist_ok=True)
        tmp_path = str(self._latest_store_path) + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, str(self._latest_store_path))

    def _result_path(self, job_id: str, filename: str) -> Path:
        self._results_dir.mkdir(parents=True, exist_ok=True)
        return self._results_dir / f"{job_id}_{filename}"

    def _persist_result(self, job_id: str, filename: str, output: BytesIO) -> str:
        path = self._result_path(job_id, filename)
        with open(path, "wb") as f:
            f.write(output.getvalue())
        return str(path)

    # ── config helpers ──────────────────────────────────────────

    def _load_config(self) -> Dict[str, Any]:
        with open(self.config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _save_config(self, config: Dict[str, Any]) -> None:
        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(config, f, allow_unicode=True, sort_keys=False)

    def _sync_model_config(self, config: Dict[str, Any], *, persist_secret: bool = False) -> Dict[str, Any]:
        llm_config = config.setdefault("llm", {})
        llm_config["base_url"] = settings.DASHSCOPE_API_BASE
        llm_config["model_name"] = settings.LLM_MODEL
        llm_config["timeout"] = int(getattr(settings, "LLM_TIMEOUT", 120) or 120)
        llm_config["temperature"] = float(getattr(settings, "LLM_TEMPERATURE", 0.7) or 0.7)
        llm_config["max_tokens"] = int(getattr(settings, "LLM_MAX_TOKENS", 4000) or 4000)
        if persist_secret:
            llm_config["api_key"] = settings.DASHSCOPE_API_KEY
        else:
            llm_config["api_key"] = ""
        return config

    # ── public config API ───────────────────────────────────────

    def get_current_config(self) -> Dict[str, Any]:
        config = self._sync_model_config(self._load_config())
        scan_config = config.get("scan", {})
        similarity_threshold = float(scan_config.get("similarity_threshold", 0.8) or 0.8)
        lookback_hours = int(scan_config.get("lookback_hours", 24) or 24)
        schedule = str(scan_config.get("schedule") or "0 23 * * *").strip() or "0 23 * * *"
        return {
            "similarity_threshold": round(similarity_threshold, 2),
            "execution_time": "daily_23" if schedule == "0 23 * * *" else "now",
            "match_scope": HOURS_TO_SCOPE.get(lookback_hours, "new"),
        }

    def update_runtime_config(self, *, similarity_threshold: float, execution_time: str, match_scope: str) -> Dict[str, Any]:
        config = self._sync_model_config(self._load_config())
        scan_config = config.setdefault("scan", {})
        scan_config["similarity_threshold"] = float(similarity_threshold)
        scan_config["schedule"] = EXECUTION_TIME_TO_SCHEDULE.get(execution_time, "0 23 * * *")
        scan_config["lookback_hours"] = SCOPE_TO_HOURS[match_scope]
        self._save_config(config)
        return config

    # ── async job management (disk-persisted) ───────────────────

    def _cleanup_expired_jobs(self, jobs: Dict[str, Any]) -> Dict[str, Any]:
        retention_days = int(getattr(settings, "METADATA_GOVERNANCE_RETENTION_DAYS", 180) or 180)
        max_jobs = int(getattr(settings, "METADATA_GOVERNANCE_MAX_JOBS", 50) or 50)
        cutoff = datetime.now() - timedelta(days=max(retention_days, 1))

        kept: Dict[str, Any] = {}
        for jid, job in jobs.items():
            created_at = str(job.get("created_at") or "").strip()
            if created_at:
                try:
                    created_dt = datetime.fromisoformat(created_at)
                    if created_dt < cutoff:
                        # Remove result file for expired job
                        self._remove_result_file(job)
                        continue
                except (ValueError, TypeError):
                    pass
            kept[jid] = job

        # If still over max, remove oldest completed/failed
        finished = sorted(
            (jid for jid, j in kept.items() if j.get("status") in ("completed", "failed")),
            key=lambda jid: kept[jid].get("created_at", ""),
        )
        for jid in finished[: max(0, len(finished) - max_jobs)]:
            self._remove_result_file(kept.pop(jid))

        return kept

    def _remove_result_file(self, job: Dict[str, Any]) -> None:
        result_path = job.get("result_path")
        if result_path and os.path.exists(result_path):
            try:
                os.unlink(result_path)
            except OSError:
                pass

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock():
            jobs = self._load_jobs_unlocked()
        job = jobs.get(job_id)
        if job is None:
            return None
        result: Dict[str, Any] = {
            "job_id": job["job_id"],
            "status": job["status"],
            "created_at": job["created_at"],
            "completed_at": job.get("completed_at"),
        }
        if job.get("error"):
            result["error"] = job["error"]
        return result

    def get_latest_job(self) -> Optional[Dict[str, Any]]:
        with self._lock():
            latest = self._load_latest_unlocked()
        job_id = latest.get("job_id")
        if not job_id:
            return None
        return self.get_job(job_id)

    def get_result_path(self, job_id: str) -> Optional[str]:
        with self._lock():
            jobs = self._load_jobs_unlocked()
        job = jobs.get(job_id)
        if not job or job.get("status") != "completed":
            return None
        result_path = job.get("result_path")
        if not result_path or not os.path.exists(result_path):
            return None
        return result_path

    def _save_job(self, job: Dict[str, Any]) -> None:
        with self._lock():
            jobs = self._load_jobs_unlocked()
            jobs[job["job_id"]] = job
            jobs = self._cleanup_expired_jobs(jobs)
            self._save_jobs_unlocked(jobs)
            # Update latest pointer
            self._save_latest_unlocked({"job_id": job["job_id"], "updated_at": datetime.now().isoformat()})

    def _run_job_background(self, job_id: str, match_scope: str = "all") -> None:
        # Mark as running
        with self._lock():
            jobs = self._load_jobs_unlocked()
            job = jobs.get(job_id)
            if job is None:
                return
            job["status"] = "running"
            self._save_jobs_unlocked(jobs)
            self._save_latest_unlocked({"job_id": job_id, "updated_at": datetime.now().isoformat()})

        try:
            result = self.run_analysis_now(persist_report=True, match_scope=match_scope)
            # Persist result file to disk
            result_path = self._persist_result(job_id, result.filename or "result.xlsx", result.output)

            with self._lock():
                jobs = self._load_jobs_unlocked()
                job = jobs.get(job_id)
                if job is None:
                    return
                job["status"] = "completed"
                job["completed_at"] = datetime.now().isoformat()
                job["filename"] = result.filename
                job["result_path"] = result_path
                jobs = self._cleanup_expired_jobs(jobs)
                self._save_jobs_unlocked(jobs)
                self._save_latest_unlocked({"job_id": job_id, "updated_at": datetime.now().isoformat()})
        except Exception as exc:
            logger.error("元数据治理后台任务失败: %s", exc, exc_info=True)
            with self._lock():
                jobs = self._load_jobs_unlocked()
                job = jobs.get(job_id)
                if job is None:
                    return
                job["status"] = "failed"
                job["completed_at"] = datetime.now().isoformat()
                job["error"] = str(exc)[:500]
                self._save_jobs_unlocked(jobs)
                self._save_latest_unlocked({"job_id": job_id, "updated_at": datetime.now().isoformat()})

    # ── core analysis ───────────────────────────────────────────

    def _build_excel(self, new_rows: List[Dict[str, Any]], stock_rows: List[Dict[str, Any]]) -> BytesIO:
        wb = Workbook()
        filtered_new_rows = [item for item in new_rows if item.get("redundancy_status") == "有冗余"]
        has_new = bool(new_rows)
        has_stock = bool(stock_rows)

        # Sheet 1: 新增（只展示有冗余记录；即使为空也保留表头）
        if has_new:
            ws_new = wb.active
            ws_new.title = "新增"
            ws_new.append([
                "元数据ID", "中文名称", "数据类型", "涉及的场景服务（拟新增）",
                "操作时间", "操作用户", "相似度",
                "最匹配的元数据ID（运行中）", "匹配中文名（运行中）", "涉及的场景服务（运行中）",
            ])
            for item in filtered_new_rows:
                ws_new.append([
                    item.get("metadata_id") or "",
                    item.get("chinese_name") or "",
                    item.get("data_type") or "",
                    item.get("service_ids") or "",
                    item.get("opt_time") or "",
                    item.get("opt_user") or "",
                    item.get("similarity_score") or "",
                    item.get("matched_metadata_id") or "",
                    item.get("matched_chinese_name") or "",
                    item.get("matched_service_ids") or "",
                ])

        # Sheet 2: 存量（仅在有数据时创建）
        if has_stock:
            ws_stock = wb.create_sheet(title="存量")
            ws_stock.append(["组别", "元数据ID", "中文名称", "数据类型", "操作时间", "操作用户", "涉及的场景服务"])
            for item in stock_rows:
                ws_stock.append([
                    item.get("group") or "",
                    item.get("metadata_id") or "",
                    item.get("chinese_name") or "",
                    item.get("data_type") or "",
                    item.get("opt_time") or "",
                    item.get("opt_user") or "",
                    item.get("service_ids") or "",
                ])

        output = BytesIO()
        wb.save(output)
        output.seek(0)
        return output

    def _fetch_service_ids_by_metadata(self, db_connection: Any) -> Dict[str, List[str]]:
        query = """
        SELECT METADATA_ID, SERVICE_ID
        FROM sda
        WHERE METADATA_ID IS NOT NULL
          AND METADATA_ID <> ''
          AND SERVICE_ID IS NOT NULL
          AND SERVICE_ID <> ''
        ORDER BY METADATA_ID, SERVICE_ID
        """
        mapping: Dict[str, List[str]] = {}
        seen: Dict[str, Set[str]] = {}
        with db_connection.cursor() as cursor:
            cursor.execute(query)
            for metadata_id, service_id in cursor.fetchall():
                meta_key = str(metadata_id or '').strip()
                service_key = str(service_id or '').strip()
                if not meta_key or not service_key:
                    continue
                service_bucket = seen.setdefault(meta_key, set())
                if service_key in service_bucket:
                    continue
                service_bucket.add(service_key)
                mapping.setdefault(meta_key, []).append(service_key)
        return mapping

    def _attach_service_ids(self, rows: List[Dict[str, Any]], service_ids_by_metadata: Dict[str, List[str]]) -> List[Dict[str, Any]]:
        for row in rows:
            metadata_id = str(row.get("metadata_id") or '').strip()
            service_ids = service_ids_by_metadata.get(metadata_id, [])
            row["service_ids"] = " | ".join(service_ids)
            # Also attach service_ids for the matched (stock) metadata
            matched_metadata_id = str(row.get("matched_metadata_id") or '').strip()
            matched_service_ids = service_ids_by_metadata.get(matched_metadata_id, [])
            row["matched_service_ids"] = " | ".join(matched_service_ids)
        return rows

    def _build_runtime_config_for_execution(self) -> Path:
        config = self._sync_model_config(self._load_config(), persist_secret=True)
        runtime_path = self.config_path.with_name(f"{self.config_path.stem}.runtime.yaml")
        with open(runtime_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(config, f, allow_unicode=True, sort_keys=False)
        return runtime_path

    def run_analysis_now(self, *, persist_report: bool = True, match_scope: str = "all") -> MetadataGovernanceRunResult:
        runtime_config_path = self._build_runtime_config_for_execution()
        try:
            inform = MetadataChangeInform(str(runtime_config_path))

            new_rows = []
            stock_rows = []
            service_ids_by_metadata: Dict[str, List[str]] = {}

            if match_scope in ("new", "all"):
                inform.connect_database()
                service_ids_by_metadata = self._fetch_service_ids_by_metadata(inform.db_connection)
                try:
                    inform.connect_llm()
                except Exception:
                    inform.llm_client = None
                if hasattr(inform, "load_cache"):
                    inform.load_cache()
                new_rows = inform.get_new_vs_stock_report_rows()
                new_rows = self._attach_service_ids(new_rows, service_ids_by_metadata)
                if hasattr(inform, "save_cache"):
                    inform.save_cache()

            if match_scope in ("stock", "all"):
                try:
                    if inform.db_connection is None:
                        inform.connect_database()
                    # Fetch service_ids mapping before detect_existing_redundancy closes the connection
                    service_ids_by_metadata = self._fetch_service_ids_by_metadata(inform.db_connection)
                    stock_rows = inform.detect_existing_redundancy()
                    stock_rows = self._attach_service_ids(stock_rows, service_ids_by_metadata)
                except Exception as exc:
                    logger.warning("存量冗余检测失败: %s", exc)
                    stock_rows = []
        finally:
            try:
                if inform.db_connection:
                    inform.db_connection.close()
            except Exception:
                pass
            try:
                runtime_config_path.unlink(missing_ok=True)
            except Exception:
                pass
        output = self._build_excel(
            new_rows=new_rows,
            stock_rows=stock_rows,
        )
        filename = f"ESB元数据冗余报告_{datetime.now().strftime('%Y%m%d')}.xlsx"
        return MetadataGovernanceRunResult(
            scheduled=False,
            execution_time="now",
            output=output,
            filename=filename,
        )

    def bootstrap_scheduler_from_config(self) -> None:
        config = self._load_config()
        schedule = str((config.get("scan") or {}).get("schedule") or "").strip()
        if schedule == "0 23 * * *":
            _daily_scheduler.ensure_daily_job(self)

    def run_or_schedule(self, *, similarity_threshold: float, execution_time: str, match_scope: str) -> MetadataGovernanceRunResult:
        self.update_runtime_config(
            similarity_threshold=similarity_threshold,
            execution_time=execution_time,
            match_scope=match_scope,
        )
        if execution_time == "daily_23":
            _daily_scheduler.ensure_daily_job(self)
            return MetadataGovernanceRunResult(scheduled=True, execution_time="daily_23")

        # "now" mode: submit async job
        job_id = f"mgov_{uuid.uuid4().hex[:12]}"
        job = {
            "job_id": job_id,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "completed_at": None,
            "error": None,
            "filename": None,
            "result_path": None,
        }
        self._save_job(job)
        self._executor.submit(self._run_job_background, job_id, match_scope)
        return MetadataGovernanceRunResult(scheduled=False, execution_time="now", job_id=job_id)


_metadata_governance_service: Optional[MetadataGovernanceService] = None


def get_metadata_governance_service() -> MetadataGovernanceService:
    global _metadata_governance_service
    if _metadata_governance_service is None:
        _metadata_governance_service = MetadataGovernanceService()
    return _metadata_governance_service
