"""
代码扫描 API（v2.0）
- 新接口：API-001 / API-002
- 兼容接口：/run /status /result /commit /jobs
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from typing import Any, Dict, Optional, Tuple

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile

from backend.api import system_routes
from backend.api.auth import require_roles
from backend.api.error_utils import build_error_response
from backend.service.code_scan_service import get_code_scan_service
from backend.service.system_profile_service import get_system_profile_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/code-scan", tags=["代码扫描"])

SUPPORTED_REPO_SOURCES = {
    "local",
    "archive",
    "gitlab_archive",
    "gitlab_compare",
    "gitlab_raw",
}


def _parse_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off", ""}:
        return False
    return default


def _parse_list_text(value: Any) -> Tuple[str, ...]:
    text = str(value or "").strip()
    if not text:
        return tuple()
    normalized = text.replace("，", ",").replace("、", ",").replace("；", ",")
    items = []
    for line in normalized.splitlines():
        for part in line.split(","):
            candidate = part.strip()
            if candidate:
                items.append(candidate)
    return tuple(items)


def _parse_options_json(value: Optional[str]) -> Dict[str, Any]:
    if not value:
        return {}
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise ValueError("options_json 必须是JSON对象")
    return parsed


def _has_non_empty_option(options: Dict[str, Any], keys: Tuple[str, ...]) -> bool:
    for key in keys:
        value = options.get(key)
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return True
    return False


def _require_option_groups(options: Dict[str, Any], groups: Tuple[Tuple[str, Tuple[str, ...]], ...]) -> Tuple[str, ...]:
    missing = []
    for label, keys in groups:
        if not _has_non_empty_option(options, keys):
            missing.append(label)
    return tuple(missing)


def _resolve_repo_source(
    raw_repo_source: str,
    *,
    repo_path: str,
    has_repo_archive: bool,
    options: Dict[str, Any],
) -> str:
    repo_source = str(raw_repo_source or "").strip().lower()
    has_repo_path = bool(str(repo_path or "").strip())

    if not repo_source:
        return "archive" if has_repo_archive else "local"

    if repo_source not in SUPPORTED_REPO_SOURCES:
        raise ValueError(f"repo_source模式参数不匹配: 不支持的repo_source={repo_source}")

    if repo_source == "local":
        if has_repo_archive:
            raise ValueError("repo_source模式参数不匹配: local 不允许 repo_archive")
        if not has_repo_path:
            raise ValueError("repo_source模式参数不匹配: local 需要 repo_path")
        return repo_source

    if repo_source in {"archive", "gitlab_archive"}:
        if not has_repo_archive:
            raise ValueError(f"repo_source模式参数不匹配: {repo_source} 需要 repo_archive")
        if has_repo_path:
            raise ValueError(f"repo_source模式参数不匹配: {repo_source} 不允许 repo_path")
        if repo_source == "gitlab_archive":
            missing = _require_option_groups(
                options,
                (
                    ("git_project_id", ("git_project_id", "project_id")),
                    ("archive_ref", ("archive_ref", "ref", "branch")),
                ),
            )
            if missing:
                raise ValueError(
                    "repo_source模式参数不匹配: gitlab_archive 缺少参数 "
                    + ",".join(missing)
                )
        return repo_source

    if repo_source == "gitlab_compare":
        if has_repo_archive:
            raise ValueError("repo_source模式参数不匹配: gitlab_compare 不允许 repo_archive")
        if not has_repo_path:
            raise ValueError("repo_source模式参数不匹配: gitlab_compare 需要 repo_path")
        missing = _require_option_groups(
            options,
            (
                ("git_project_id", ("git_project_id", "project_id")),
                ("compare_from", ("compare_from", "from_ref", "from_sha", "base_ref", "base_sha")),
                ("compare_to", ("compare_to", "to_ref", "to_sha", "head_ref", "head_sha")),
            ),
        )
        if missing:
            raise ValueError(
                "repo_source模式参数不匹配: gitlab_compare 缺少参数 " + ",".join(missing)
            )
        return repo_source

    if repo_source == "gitlab_raw":
        if has_repo_archive:
            raise ValueError("repo_source模式参数不匹配: gitlab_raw 不允许 repo_archive")
        if not has_repo_path:
            raise ValueError("repo_source模式参数不匹配: gitlab_raw 需要 repo_path")
        missing = _require_option_groups(
            options,
            (
                ("git_project_id", ("git_project_id", "project_id")),
                ("raw_ref", ("raw_ref", "ref", "branch")),
            ),
        )
        if missing:
            raise ValueError(
                "repo_source模式参数不匹配: gitlab_raw 缺少参数 " + ",".join(missing)
            )
        return repo_source

    return repo_source


def _to_job_payload(job: Dict[str, Any]) -> Dict[str, Any]:
    status = str(job.get("status") or "")
    progress_float = float(job.get("progress") or 0.0)
    progress = int(max(0.0, min(1.0, progress_float)) * 100)

    payload: Dict[str, Any] = {
        "job_id": str(job.get("job_id") or ""),
        "status": status,
        "created_at": job.get("created_at") or "",
        "progress": progress,
        "repo_source": str(job.get("repo_source") or ""),
        "execution_id": str(job.get("execution_id") or ""),
    }

    result_path = str(job.get("result_path") or "").strip()
    if result_path:
        payload["result_path"] = result_path

    if status in {"failed", "timeout"}:
        message = str(job.get("error") or "").strip()
        if message:
            payload["message"] = message

    return payload


def _map_submit_exception(exc: Exception) -> Tuple[int, str, str, Dict[str, Any]]:
    message = str(exc)

    if isinstance(exc, OverflowError):
        return 400, "SCAN_006", "仓库压缩包解压后超出大小或文件数量限制", {"reason": message}

    if isinstance(exc, PermissionError):
        if "Git URL" in message:
            return 400, "SCAN_001", "代码仓库路径不存在或无法访问", {"reason": message}
        return 400, "SCAN_004", "本地仓库路径不在允许范围内", {"reason": message}

    if isinstance(exc, ValueError):
        if "repo_source" in message or "模式参数" in message:
            return 400, "SCAN_007", "repo_source模式参数不合法", {"reason": message}
        if "repo_archive" in message or "压缩包" in message or "不支持的压缩格式" in message:
            return 400, "SCAN_005", "仓库压缩包格式不支持或解压失败", {"reason": message}
        return 400, "SCAN_001", "代码仓库路径不存在或无法访问", {"reason": message}

    return 500, "SCAN_001", "代码仓库路径不存在或无法访问", {"reason": message or "未知错误"}


def _map_ingest_exception(exc: Exception) -> Tuple[int, str, str, Dict[str, Any]]:
    message = str(exc)
    if isinstance(exc, ValueError):
        if "任务不存在" in message:
            return 404, "SCAN_002", "扫描任务不存在", {}
        if "扫描未完成" in message:
            return 400, "SCAN_003", "扫描任务状态不允许该操作", {"reason": message}
        return 400, "SCAN_003", "扫描任务状态不允许该操作", {"reason": message}

    return 503, "EMB_001", "embedding服务不可用，请稍后重试", {"reason": message or "embedding服务异常"}


def _ensure_owner(
    current_user: Dict[str, Any],
    *,
    request: Request,
    system_id: Optional[str],
    system_name: str,
):
    roles = current_user.get("roles") or []
    if "admin" in roles:
        return None

    ownership = system_routes.resolve_system_ownership(
        current_user,
        system_id=system_id,
        system_name=system_name,
    )
    if ownership.get("allowed_draft_write"):
        return None

    owner_info = ownership.get("owner_info") or {}
    reason = "当前用户不是系统主责或B角"
    if not owner_info.get("system_found"):
        reason = "系统不存在或未纳入系统清单"
    else:
        resolved_owner_id = str(owner_info.get("resolved_owner_id") or "").strip()
        resolved_backups = owner_info.get("resolved_backup_owner_ids") or []
        has_backups = any(str(item).strip() for item in resolved_backups)
        if (not resolved_owner_id) and (not has_backups):
            reason = "系统清单未配置主责或B角（owner_id/owner_username/backup_owner_ids/backup_owner_usernames）"
        elif owner_info.get("mapping_status") == "owner_username_unresolved":
            reason = "owner_username 未映射到有效用户"

    return build_error_response(
        request=request,
        status_code=403,
        error_code="AUTH_001",
        message="权限不足",
        details={
            "reason": reason,
            "system_id": system_id,
            "system_name": system_name,
        },
    )


def _ensure_job_creator(
    current_user: Dict[str, Any],
    job: Dict[str, Any],
    *,
    request: Request,
):
    roles = current_user.get("roles") or []
    if "admin" in roles:
        return None

    current_user_id = str(current_user.get("id") or "")
    created_by = str(job.get("created_by") or "")
    if current_user_id and created_by and current_user_id == created_by:
        return None

    return build_error_response(
        request=request,
        status_code=403,
        error_code="AUTH_001",
        message="权限不足",
        details={"reason": "仅允许扫描任务创建者执行该操作", "job_id": job.get("job_id")},
    )


@router.post("/jobs")
async def create_scan_job(
    request: Request,
    current_user: Dict[str, Any] = Depends(require_roles(["manager", "admin"])),
    system_name_form: Optional[str] = Form(None, alias="system_name"),
    system_id_form: Optional[str] = Form(None, alias="system_id"),
    repo_path_form: Optional[str] = Form(None, alias="repo_path"),
    repo_source_form: Optional[str] = Form(None, alias="repo_source"),
    force_form: Optional[str] = Form(None, alias="force"),
    scan_paths_form: Optional[str] = Form(None, alias="scan_paths"),
    exclude_dirs_form: Optional[str] = Form(None, alias="exclude_dirs"),
    options_json: Optional[str] = Form(None),
    repo_archive: Optional[UploadFile] = File(None),
):
    content_type = (request.headers.get("content-type") or "").lower()

    system_name = ""
    system_id = ""
    repo_path = ""
    repo_source_raw = ""
    repo_source_explicit = False
    force = False
    options: Dict[str, Any] = {}
    scan_paths: Tuple[str, ...] = tuple()
    exclude_dirs: Tuple[str, ...] = tuple()

    try:
        if "multipart/form-data" in content_type:
            system_name = str(system_name_form or "").strip()
            system_id = str(system_id_form or "").strip()
            repo_path = str(repo_path_form or "").strip()
            repo_source_raw = str(repo_source_form or "").strip().lower()
            repo_source_explicit = bool(repo_source_raw)
            force = _parse_bool(force_form, default=False)
            scan_paths = _parse_list_text(scan_paths_form)
            exclude_dirs = _parse_list_text(exclude_dirs_form)
            options = _parse_options_json(options_json)
        else:
            payload = await request.json()
            if not isinstance(payload, dict):
                payload = {}
            system_name = str(payload.get("system_name") or "").strip()
            system_id = str(payload.get("system_id") or "").strip()
            repo_path = str(payload.get("repo_path") or "").strip()
            repo_source_raw = str(payload.get("repo_source") or "").strip().lower()
            repo_source_explicit = bool(repo_source_raw)
            force = _parse_bool(payload.get("force"), default=False)
            raw_scan_paths = payload.get("scan_paths")
            if isinstance(raw_scan_paths, list):
                scan_paths = tuple(str(item).strip() for item in raw_scan_paths if str(item).strip())
            else:
                scan_paths = _parse_list_text(raw_scan_paths)
            raw_exclude_dirs = payload.get("exclude_dirs")
            if isinstance(raw_exclude_dirs, list):
                exclude_dirs = tuple(str(item).strip() for item in raw_exclude_dirs if str(item).strip())
            else:
                exclude_dirs = _parse_list_text(raw_exclude_dirs)
            raw_options = payload.get("options")
            if raw_options is None:
                options = {}
            elif isinstance(raw_options, dict):
                options = raw_options
            else:
                raise ValueError("options 必须是JSON对象")

        options = dict(options)
        if scan_paths and (not options.get("paths")):
            options["paths"] = list(scan_paths)
        if exclude_dirs and (not options.get("exclude_dirs")):
            options["exclude_dirs"] = list(exclude_dirs)

        if not system_name:
            raise ValueError("system_name不能为空")

        repo_source = _resolve_repo_source(
            repo_source_raw,
            repo_path=repo_path,
            has_repo_archive=repo_archive is not None,
            options=options,
        )

        owner_error = _ensure_owner(
            current_user,
            request=request,
            system_id=system_id or None,
            system_name=system_name,
        )
        if owner_error:
            return owner_error

        service = get_code_scan_service()
        created_by = str(current_user.get("id") or current_user.get("username") or "")

        if repo_archive is not None:
            if repo_source not in {"archive", "gitlab_archive"}:
                raise ValueError(f"repo_source模式参数不匹配: {repo_source} 不支持 repo_archive")
            archive_content = await repo_archive.read()
            if not archive_content:
                raise ValueError("repo_archive为空")

            upload_dir = os.path.join(service.extract_dir, "_uploads")
            os.makedirs(upload_dir, exist_ok=True)
            suffix = os.path.splitext(str(repo_archive.filename or "archive.zip"))[1] or ".zip"
            with tempfile.NamedTemporaryFile(prefix="repo_", suffix=suffix, dir=upload_dir, delete=False) as tmp:
                tmp.write(archive_content)
                archive_path = tmp.name
            try:
                job_id = service.run_scan_from_archive(
                    system_name=system_name,
                    system_id=system_id or None,
                    archive_path=archive_path,
                    options=options,
                    created_by=created_by,
                    force=force,
                    repo_source_override=repo_source if repo_source_explicit else None,
                )
            finally:
                if os.path.exists(archive_path):
                    os.remove(archive_path)
        else:
            if repo_source in {"archive", "gitlab_archive"}:
                raise ValueError(f"repo_source模式参数不匹配: {repo_source} 需要 repo_archive")
            if not repo_path:
                raise ValueError("repo_path无效或不存在")
            job_id = service.run_scan(
                system_name=system_name,
                system_id=system_id or None,
                repo_path=repo_path,
                options=options,
                created_by=created_by,
                force=force,
                repo_source_override=repo_source if repo_source_explicit else None,
            )

        job = service.get_status(job_id)
        if not job:
            return build_error_response(
                request=request,
                status_code=404,
                error_code="SCAN_002",
                message="扫描任务不存在",
                details={"job_id": job_id},
            )

        return _to_job_payload(job)
    except Exception as exc:
        logger.error("触发扫描失败: %s", exc)
        status_code, error_code, message, details = _map_submit_exception(exc)
        return build_error_response(
            request=request,
            status_code=status_code,
            error_code=error_code,
            message=message,
            details=details,
        )


@router.get("/jobs/{job_id}")
async def get_scan_job(
    job_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_roles(["manager", "admin"])),
):
    service = get_code_scan_service()
    job = service.get_status(job_id)
    if not job:
        return build_error_response(
            request=request,
            status_code=404,
            error_code="SCAN_002",
            message="扫描任务不存在",
            details={"job_id": job_id},
        )

    creator_error = _ensure_job_creator(current_user, job, request=request)
    if creator_error:
        return creator_error

    return _to_job_payload(job)


@router.post("/jobs/{job_id}/ingest")
async def ingest_scan_job(
    job_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_roles(["manager", "admin"])),
):
    service = get_code_scan_service()
    job = service.get_status(job_id)
    if not job:
        return build_error_response(
            request=request,
            status_code=404,
            error_code="SCAN_002",
            message="扫描任务不存在",
            details={"job_id": job_id},
        )

    creator_error = _ensure_job_creator(current_user, job, request=request)
    if creator_error:
        return creator_error

    try:
        result = service.commit_result(job_id)

        profile_service = get_system_profile_service()
        profile_service.mark_code_scan_ingested(
            system_name=str(job.get("system_name") or ""),
            system_id=str(job.get("system_id") or "") or None,
            job_id=job_id,
            result_path=str(job.get("result_path") or ""),
            actor=current_user,
        )

        # 异步触发系统画像AI总结（失败不影响主流程）
        try:
            from backend.service.profile_summary_service import get_profile_summary_service

            system_id = str(job.get("system_id") or "").strip()
            system_name = str(job.get("system_name") or "").strip()
            if system_id and system_name:
                get_profile_summary_service().trigger_summary(
                    system_id=system_id,
                    system_name=system_name,
                    actor=current_user,
                    reason="code_scan_ingest",
                )
        except Exception as exc:
            logger.warning("触发画像AI总结失败（忽略）: %s", exc)

        return {
            "success": int(result.get("success") or 0),
            "failed": int(result.get("failed") or 0),
            "errors": result.get("errors") or [],
        }
    except Exception as exc:
        logger.error("扫描结果入库失败: %s", exc)
        status_code, error_code, message, details = _map_ingest_exception(exc)
        return build_error_response(
            request=request,
            status_code=status_code,
            error_code=error_code,
            message=message,
            details=details,
        )


@router.post("/run")
async def legacy_run_scan(
    request: Request,
    current_user: Dict[str, Any] = Depends(require_roles(["manager", "admin"])),
):
    payload = await create_scan_job(
        request=request,
        current_user=current_user,
        system_name_form=None,
        system_id_form=None,
        repo_path_form=None,
        force_form=None,
        options_json=None,
        repo_archive=None,
    )
    if not isinstance(payload, dict):
        return payload
    if payload.get("error_code"):
        return payload
    return {"code": 200, "data": payload}


@router.get("/status/{job_id}")
async def legacy_scan_status(
    job_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_roles(["manager", "admin"])),
):
    payload = await get_scan_job(job_id=job_id, request=request, current_user=current_user)
    if not isinstance(payload, dict):
        return payload
    if payload.get("error_code"):
        return payload
    return {"code": 200, "data": payload}


@router.get("/result/{job_id}")
async def legacy_scan_result(
    job_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_roles(["manager", "admin"])),
):
    service = get_code_scan_service()
    job = service.get_status(job_id)
    if not job:
        return build_error_response(
            request=request,
            status_code=404,
            error_code="SCAN_002",
            message="扫描任务不存在",
            details={"job_id": job_id},
        )

    creator_error = _ensure_job_creator(current_user, job, request=request)
    if creator_error:
        return creator_error

    try:
        result = service.get_result(job_id)
        return {"code": 200, "data": result}
    except Exception as exc:
        status_code, error_code, message, details = _map_ingest_exception(exc)
        return build_error_response(
            request=request,
            status_code=status_code,
            error_code=error_code,
            message=message,
            details=details,
        )


@router.post("/commit/{job_id}")
async def legacy_commit_result(
    job_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_roles(["manager", "admin"])),
):
    payload = await ingest_scan_job(job_id=job_id, request=request, current_user=current_user)
    if not isinstance(payload, dict):
        return payload
    if payload.get("error_code"):
        return payload
    return {"code": 200, "data": payload}


@router.get("/jobs")
async def legacy_list_jobs(
    current_user: Dict[str, Any] = Depends(require_roles(["manager", "admin"])),
):
    service = get_code_scan_service()
    jobs = service.list_jobs()
    if "admin" not in (current_user.get("roles") or []):
        current_user_id = str(current_user.get("id") or "")
        jobs = [job for job in jobs if str(job.get("created_by") or "") == current_user_id]
    return {"code": 200, "data": [_to_job_payload(job) for job in jobs]}
