"""
ESB 导入 API（v2.0）
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from backend.api import system_routes
from backend.api.auth import require_roles
from backend.api.error_utils import build_error_response
from backend.config.config import settings
from backend.service.esb_service import get_esb_service
from backend.service.service_governance_profile_updater import get_service_governance_profile_updater
from backend.service.system_profile_service import get_system_profile_service
from backend.service.metadata_governance_service import get_metadata_governance_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/esb", tags=["ESB导入"])

MAPPING_FORM_FIELD_KEYS = (
    "service_code",
    "scenario_code",
    "provider_system_id",
    "provider_system_name",
    "service_name",
    "consumer_system_id",
    "consumer_system_name",
    "status",
    "remark",
    "system_id",
    "system_name",
    "owner",
    "center",
    "total_interface_count",
    "no_call_interface_count",
)

V27_GOVERNANCE_REQUIRED_FLAGS = (
    "ENABLE_V27_PROFILE_SCHEMA",
    "ENABLE_V27_RUNTIME",
    "ENABLE_SERVICE_GOVERNANCE_IMPORT",
)



class MetadataGovernanceRunRequest(BaseModel):
    similarity_threshold: float = Field(..., ge=0.0, le=1.0)
    execution_time: str = Field(..., pattern="^(now|daily_23)$")
    match_scope: str = Field(..., pattern="^(new|stock|all)$")


def _parse_mapping_json(raw_mapping_json: Optional[str]) -> Dict[str, Any]:
    if raw_mapping_json is None or str(raw_mapping_json).strip() == "":
        return {}

    parsed = json.loads(raw_mapping_json)
    if not isinstance(parsed, dict):
        raise ValueError("mapping_json 必须是JSON对象")

    normalized: Dict[str, Any] = {}
    for key, value in parsed.items():
        field = str(key or "").strip()
        if not field:
            continue

        if isinstance(value, list):
            candidates = [str(item).strip() for item in value if str(item).strip()]
            normalized[field] = candidates
            continue

        if value is None:
            continue

        normalized[field] = str(value).strip()

    return normalized


def _parse_mapping_form_fields(raw_mapping_fields: Dict[str, Optional[str]]) -> Dict[str, Any]:
    normalized: Dict[str, Any] = {}
    for key in MAPPING_FORM_FIELD_KEYS:
        raw_value = raw_mapping_fields.get(key)
        text = str(raw_value or "").strip()
        if not text:
            continue
        normalized_text = text.replace("，", ",").replace("、", ",").replace("；", ",")
        candidates = []
        for line in normalized_text.splitlines():
            for part in line.split(","):
                candidate = part.strip()
                if candidate:
                    candidates.append(candidate)
        if not candidates:
            continue
        normalized[key] = candidates if len(candidates) > 1 else candidates[0]
    return normalized


def _get_missing_v27_governance_flags() -> list[str]:
    missing_flags = []
    for flag_name in V27_GOVERNANCE_REQUIRED_FLAGS:
        if not getattr(settings, flag_name, False):
            missing_flags.append(flag_name)
    return missing_flags


def _ensure_owner_permission(
    current_user: Dict[str, Any],
    *,
    request: Request,
    system_id: str,
):
    roles = current_user.get("roles") or []
    owner_info = system_routes.resolve_system_owner(system_id=system_id)

    if not owner_info.get("system_found"):
        return None, build_error_response(
            request=request,
            status_code=400,
            error_code="ESB_002",
            message="目标系统不存在",
            details={"system_id": system_id},
        )

    if "admin" in roles:
        return owner_info, None

    ownership = system_routes.resolve_system_ownership(current_user, system_id=system_id)
    if ownership.get("allowed_draft_write"):
        return owner_info, None

    resolved_owner_id = str(owner_info.get("resolved_owner_id") or "").strip()
    resolved_backups = owner_info.get("resolved_backup_owner_ids") or []
    has_backups = any(str(item).strip() for item in resolved_backups)
    reason = "当前用户不是系统主责或B角"
    if (not resolved_owner_id) and (not has_backups):
        reason = "系统清单未配置主责或B角（owner_id/owner_username/backup_owner_ids/backup_owner_usernames）"
    elif owner_info.get("mapping_status") == "owner_username_unresolved":
        reason = "owner_username 未映射到有效用户"

    return owner_info, build_error_response(
        request=request,
        status_code=403,
        error_code="AUTH_001",
        message="权限不足",
        details={"reason": reason, "system_id": system_id, "system_name": owner_info.get("system_name")},
    )


def _ensure_esb_metadata_governance_admin(current_user: Dict[str, Any], *, request: Request):
    roles = current_user.get("roles") or []
    username = str(current_user.get("username") or "").strip()
    display_name = str(current_user.get("display_name") or current_user.get("displayName") or "").strip()
    if "admin" in roles and (username == "esb" or display_name == "esb"):
        return None
    return build_error_response(
        request=request,
        status_code=403,
        error_code="AUTH_001",
        message="权限不足",
        details={"reason": "仅用户名或显示名为 esb 的管理员可使用元数据治理"},
    )


def _ensure_admin_or_owner_scope(
    current_user: Dict[str, Any],
    *,
    request: Request,
    system_id: str,
):
    normalized_system_id = str(system_id or "").strip()
    if normalized_system_id:
        return _ensure_owner_permission(
            current_user,
            request=request,
            system_id=normalized_system_id,
        )

    roles = current_user.get("roles") or []
    if "admin" in roles:
        return None, None

    return None, build_error_response(
        request=request,
        status_code=400,
        error_code="ESB_002",
        message="非管理员查询需传入 system_id",
    )


@router.get("/metadata-governance/config")
async def get_metadata_governance_config(
    request: Request,
    current_user: Dict[str, Any] = Depends(require_roles(["admin"])),
):
    permission_error = _ensure_esb_metadata_governance_admin(current_user, request=request)
    if permission_error:
        return permission_error

    service = get_metadata_governance_service()
    return service.get_current_config()


@router.post("/metadata-governance/run")
async def run_metadata_governance(
    payload: MetadataGovernanceRunRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_roles(["admin"])),
):
    permission_error = _ensure_esb_metadata_governance_admin(current_user, request=request)
    if permission_error:
        return permission_error

    service = get_metadata_governance_service()
    result = service.run_or_schedule(
        similarity_threshold=payload.similarity_threshold,
        execution_time=payload.execution_time,
        match_scope=payload.match_scope,
    )
    if result.scheduled:
        return {
            "scheduled": True,
            "execution_time": result.execution_time,
        }
    return {
        "job_id": result.job_id,
        "status": "pending",
        "execution_time": result.execution_time,
    }


@router.get("/metadata-governance/jobs/latest")
async def get_metadata_governance_latest_job(
    request: Request,
    current_user: Dict[str, Any] = Depends(require_roles(["admin"])),
):
    permission_error = _ensure_esb_metadata_governance_admin(current_user, request=request)
    if permission_error:
        return permission_error

    service = get_metadata_governance_service()
    job = service.get_latest_job()
    if not job:
        return {"job_id": None, "status": None}
    return job


@router.get("/metadata-governance/jobs/{job_id}")
async def get_metadata_governance_job_status(
    job_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_roles(["admin"])),
):
    permission_error = _ensure_esb_metadata_governance_admin(current_user, request=request)
    if permission_error:
        return permission_error

    service = get_metadata_governance_service()
    job = service.get_job(job_id)
    if not job:
        return build_error_response(
            request=request,
            status_code=404,
            error_code="MGOV_001",
            message="任务不存在",
            details={"job_id": job_id},
        )
    return job


@router.get("/metadata-governance/jobs/{job_id}/download")
async def download_metadata_governance_result(
    job_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_roles(["admin"])),
):
    permission_error = _ensure_esb_metadata_governance_admin(current_user, request=request)
    if permission_error:
        return permission_error

    service = get_metadata_governance_service()
    job_info = service.get_job(job_id)
    if not job_info:
        return build_error_response(
            request=request,
            status_code=404,
            error_code="MGOV_001",
            message="任务不存在",
            details={"job_id": job_id},
        )
    if job_info["status"] != "completed":
        return build_error_response(
            request=request,
            status_code=400,
            error_code="MGOV_002",
            message="任务尚未完成",
            details={"job_id": job_id, "status": job_info["status"]},
        )

    result_path = service.get_result_path(job_id)
    if not result_path:
        return build_error_response(
            request=request,
            status_code=500,
            error_code="MGOV_003",
            message="结果文件不可用",
            details={"job_id": job_id},
        )

    filename = os.path.basename(result_path).split("_", 1)[-1] if "_" in os.path.basename(result_path) else os.path.basename(result_path)
    return FileResponse(
        path=result_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=filename,
    )


@router.post("/imports")
async def import_esb(
    request: Request,
    file: UploadFile = File(...),
    system_id: Optional[str] = Form(None),
    mapping_json: Optional[str] = Form(None),
    mapping_service_code: Optional[str] = Form(None),
    mapping_scenario_code: Optional[str] = Form(None),
    mapping_provider_system_id: Optional[str] = Form(None),
    mapping_provider_system_name: Optional[str] = Form(None),
    mapping_service_name: Optional[str] = Form(None),
    mapping_consumer_system_id: Optional[str] = Form(None),
    mapping_consumer_system_name: Optional[str] = Form(None),
    mapping_status: Optional[str] = Form(None),
    mapping_remark: Optional[str] = Form(None),
    mapping_system_id: Optional[str] = Form(None),
    mapping_system_name: Optional[str] = Form(None),
    mapping_owner: Optional[str] = Form(None),
    mapping_center: Optional[str] = Form(None),
    mapping_total_interface_count: Optional[str] = Form(None),
    mapping_no_call_interface_count: Optional[str] = Form(None),
    current_user: Dict[str, Any] = Depends(require_roles(["manager", "admin"])),
):
    normalized_system_id = str(system_id or "").strip()
    roles = current_user.get("roles") or []

    if "admin" in roles and not normalized_system_id:
        missing_flags = _get_missing_v27_governance_flags()
        if missing_flags:
            return build_error_response(
                request=request,
                status_code=400,
                error_code="ESB_002",
                message="服务治理全局导入未启用",
                details={
                    "reason": "当前运行环境未启用 v2.7 服务治理全局导入所需开关",
                    "missing_flags": missing_flags,
                },
            )

    if getattr(settings, "ENABLE_SERVICE_GOVERNANCE_IMPORT", False) and not normalized_system_id:
        if "admin" not in roles:
            return build_error_response(
                request=request,
                status_code=403,
                error_code="AUTH_001",
                message="权限不足",
                details={"reason": "仅 admin 可执行全局服务治理导入"},
            )

        if not file.filename:
            return build_error_response(
                request=request,
                status_code=400,
                error_code="ESB_001",
                message="文件格式不支持，请上传Excel或CSV文件",
            )

        ext = os.path.splitext(file.filename.lower())[1]
        if ext not in {".xlsx", ".xls", ".csv"}:
            return build_error_response(
                request=request,
                status_code=400,
                error_code="ESB_001",
                message="文件格式不支持，请上传Excel或CSV文件",
                details={"filename": file.filename},
            )

        try:
            file_content = await file.read()
            if not file_content:
                raise ValueError("ESB文件解析失败或为空")

            updater = get_service_governance_profile_updater()
            return updater.import_governance(
                file_content=file_content,
                filename=file.filename,
                actor=current_user,
            )
        except Exception as exc:
            return build_error_response(
                request=request,
                status_code=400,
                error_code="ESB_002",
                message="ESB文件缺少必填字段",
                details={"reason": str(exc)},
            )

    if not normalized_system_id:
        return build_error_response(
            request=request,
            status_code=400,
            error_code="ESB_002",
            message="ESB文件缺少必填字段：system_id",
        )

    owner_info, owner_error = _ensure_owner_permission(
        current_user,
        request=request,
        system_id=normalized_system_id,
    )
    if owner_error:
        return owner_error

    if not file.filename:
        return build_error_response(
            request=request,
            status_code=400,
            error_code="ESB_001",
            message="文件格式不支持，请上传Excel或CSV文件",
        )

    ext = os.path.splitext(file.filename.lower())[1]
    if ext not in {".xlsx", ".xls", ".csv"}:
        return build_error_response(
            request=request,
            status_code=400,
            error_code="ESB_001",
            message="文件格式不支持，请上传Excel或CSV文件",
            details={"filename": file.filename},
        )

    try:
        mapping_override = _parse_mapping_json(mapping_json)
        form_mapping_override = _parse_mapping_form_fields(
            {
                "service_code": mapping_service_code,
                "scenario_code": mapping_scenario_code,
                "provider_system_id": mapping_provider_system_id,
                "provider_system_name": mapping_provider_system_name,
                "service_name": mapping_service_name,
                "consumer_system_id": mapping_consumer_system_id,
                "consumer_system_name": mapping_consumer_system_name,
                "status": mapping_status,
                "remark": mapping_remark,
                "system_id": mapping_system_id,
                "system_name": mapping_system_name,
                "owner": mapping_owner,
                "center": mapping_center,
                "total_interface_count": mapping_total_interface_count,
                "no_call_interface_count": mapping_no_call_interface_count,
            }
        )
        for key, value in form_mapping_override.items():
            if key not in mapping_override:
                mapping_override[key] = value
    except Exception as exc:
        return build_error_response(
            request=request,
            status_code=400,
            error_code="ESB_002",
            message="ESB文件缺少必填字段",
            details={"reason": str(exc)},
        )

    try:
        file_content = await file.read()
        if not file_content:
            raise ValueError("ESB文件解析失败或为空")

        service = get_esb_service()
        target_system_aliases = [
            str((owner_info or {}).get("system_name") or "").strip(),
            str((owner_info or {}).get("system_abbreviation") or "").strip(),
        ]
        result = service.import_esb(
            file_content=file_content,
            filename=file.filename,
            mapping_json=mapping_override,
            target_system_id=normalized_system_id,
            target_system_aliases=target_system_aliases,
            strict_embedding=True,
        )

        imported = int(result.get("imported") or 0)
        if imported > 0:
            profile_service = get_system_profile_service()
            profile_service.mark_esb_ingested(
                system_name=str((owner_info or {}).get("system_name") or ""),
                system_id=normalized_system_id,
                import_id=f"esb_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}",
                source_file=file.filename,
                actor=current_user,
            )

            # 异步触发系统画像AI总结（失败不影响主流程）
            try:
                from backend.service.profile_summary_service import get_profile_summary_service

                system_name = str((owner_info or {}).get("system_name") or "").strip()
                if normalized_system_id and system_name:
                    get_profile_summary_service().trigger_summary(
                        system_id=normalized_system_id,
                        system_name=system_name,
                        actor=current_user,
                        reason="esb_import",
                    )
            except Exception as exc:
                logger.warning("触发画像AI总结失败（忽略）: %s", exc)

        return {
            "total": int(result.get("total") or 0),
            "imported": imported,
            "skipped": int(result.get("skipped") or 0),
            "errors": result.get("errors") or [],
            "mapping_resolved": result.get("mapping_resolved") or {},
        }
    except RuntimeError as exc:
        return build_error_response(
            request=request,
            status_code=503,
            error_code="EMB_001",
            message="embedding服务不可用，请稍后重试",
            details={"reason": str(exc)},
        )
    except ValueError as exc:
        message = str(exc)
        if "缺少必填字段" in message:
            return build_error_response(
                request=request,
                status_code=400,
                error_code="ESB_002",
                message=message,
            )
        return build_error_response(
            request=request,
            status_code=400,
            error_code="ESB_001",
            message="文件格式不支持，请上传Excel或CSV文件",
            details={"reason": message},
        )
    except Exception as exc:
        logger.error("ESB导入失败: %s", exc)
        return build_error_response(
            request=request,
            status_code=500,
            error_code="ESB_001",
            message="文件格式不支持，请上传Excel或CSV文件",
            details={"reason": str(exc)},
        )


@router.get("/search")
async def search_esb(
    request: Request,
    q: str = Query(...),
    system_id: Optional[str] = Query(None),
    scope: Optional[str] = Query("both"),
    include_deprecated: bool = Query(False),
    top_k: int = Query(8),
    current_user: Dict[str, Any] = Depends(require_roles(["manager", "admin"])),
):
    normalized_query = str(q or "").strip()
    if not normalized_query:
        return build_error_response(
            request=request,
            status_code=400,
            error_code="ESB_002",
            message="检索关键词不能为空",
        )

    normalized_scope = str(scope or "both").strip().lower() or "both"
    if normalized_scope not in {"provider", "consumer", "both"}:
        return build_error_response(
            request=request,
            status_code=400,
            error_code="ESB_002",
            message="scope 仅支持 provider/consumer/both",
        )

    normalized_top_k = max(1, min(int(top_k or 8), 100))
    normalized_system_id = str(system_id or "").strip()

    _, owner_error = _ensure_admin_or_owner_scope(
        current_user,
        request=request,
        system_id=normalized_system_id,
    )
    if owner_error:
        return owner_error

    try:
        service = get_esb_service()
        items = service.search_esb(
            query=normalized_query,
            system_id=normalized_system_id or None,
            scope=normalized_scope,
            include_deprecated=bool(include_deprecated),
            top_k=normalized_top_k,
        )
        return {
            "total": len(items),
            "items": items,
        }
    except Exception as exc:
        logger.error("ESB检索失败: %s", exc)
        return build_error_response(
            request=request,
            status_code=500,
            error_code="ESB_001",
            message="ESB检索失败",
            details={"reason": str(exc)},
        )


@router.get("/stats")
async def get_esb_stats(
    request: Request,
    system_id: Optional[str] = Query(None),
    include_system_summary: bool = Query(True),
    current_user: Dict[str, Any] = Depends(require_roles(["manager", "admin"])),
):
    normalized_system_id = str(system_id or "").strip()

    _, owner_error = _ensure_admin_or_owner_scope(
        current_user,
        request=request,
        system_id=normalized_system_id,
    )
    if owner_error:
        return owner_error

    try:
        service = get_esb_service()
        stats = service.get_stats(system_id=normalized_system_id or None)
        if not include_system_summary:
            stats["system_summary"] = []
        return {
            "active_entry_count": int(stats.get("active_entry_count") or 0),
            "deprecated_entry_count": int(stats.get("deprecated_entry_count") or 0),
            "active_unique_service_count": int(stats.get("active_unique_service_count") or 0),
            "system_summary": stats.get("system_summary") or [],
        }
    except Exception as exc:
        logger.error("ESB统计失败: %s", exc)
        return build_error_response(
            request=request,
            status_code=500,
            error_code="ESB_001",
            message="ESB统计失败",
            details={"reason": str(exc)},
        )
