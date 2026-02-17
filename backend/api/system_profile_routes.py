"""
系统画像 API（v2.0）
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from backend.api import system_routes
from backend.api.auth import require_roles
from backend.api.error_utils import build_error_response
from backend.service.system_profile_service import get_system_profile_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/system-profiles", tags=["系统画像"])


def _document_score(document_count: int) -> int:
    if document_count >= 11:
        return 40
    if document_count >= 6:
        return 30
    if document_count >= 1:
        return 10
    return 0


def _build_completeness(profile: Optional[Dict[str, Any]]) -> Tuple[int, Dict[str, int], int]:
    if not profile:
        return 0, {"code_scan": 0, "documents": 0, "esb": 0}, 0

    completeness = profile.get("completeness") if isinstance(profile.get("completeness"), dict) else {}
    code_scan_score = 30 if bool(completeness.get("code_scan")) else 0
    document_count = int(completeness.get("documents_normal") or profile.get("document_count") or 0)
    documents_score = _document_score(document_count)
    esb_score = 30 if bool(completeness.get("esb")) else 0
    total = max(0, min(100, code_scan_score + documents_score + esb_score))
    return total, {"code_scan": code_scan_score, "documents": documents_score, "esb": esb_score}, document_count


def _is_profile_stale(profile: Dict[str, Any]) -> bool:
    stale_days = int(os.getenv("PROFILE_STALE_DAYS", "30"))
    if stale_days <= 0:
        return False

    updated_at = str(profile.get("updated_at") or profile.get("created_at") or "").strip()
    if not updated_at:
        return True

    try:
        updated_dt = datetime.fromisoformat(updated_at)
    except Exception:
        return True

    return updated_dt < (datetime.now() - timedelta(days=stale_days))


def _forbidden_write_response(
    request: Request,
    reason: str,
    system_name: str,
    system_id: Optional[str] = None,
    *,
    error_code: str = "permission_denied",
):
    return build_error_response(
        request=request,
        status_code=403,
        error_code=error_code,
        message="无权编辑该系统画像",
        details={"reason": reason, "system_name": system_name, "system_id": system_id},
    )


def _resolve_system_ref(system_name: str, system_id: Optional[str]) -> Dict[str, Any]:
    owner_info = system_routes.resolve_system_owner(system_id=system_id, system_name=system_name)
    return {
        "owner_info": owner_info,
        "resolved_system_id": str(owner_info.get("system_id") or system_id or "").strip(),
        "resolved_system_name": str(owner_info.get("system_name") or system_name or "").strip(),
    }


def _system_not_found_response(request: Request, *, system_name: str, system_id: Optional[str] = None):
    return build_error_response(
        request=request,
        status_code=404,
        error_code="system_not_found",
        message="系统不存在",
        details={"system_name": system_name, "system_id": system_id},
    )


def _ensure_owner_or_backup_for_draft_write(
    current_user: Dict[str, Any],
    *,
    request: Request,
    system_name: str,
    system_id: Optional[str],
):
    roles = current_user.get("roles") or []
    if "admin" in roles:
        return None

    if "manager" not in roles:
        return _forbidden_write_response(request, "当前角色不可写系统画像", system_name, system_id)

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
        reason = "系统不存在"
    else:
        resolved_owner_id = str(owner_info.get("resolved_owner_id") or "").strip()
        resolved_backups = owner_info.get("resolved_backup_owner_ids") or []
        has_backups = any(str(item).strip() for item in resolved_backups)
        if (not resolved_owner_id) and (not has_backups):
            reason = "系统清单未配置主责或B角（owner_id/owner_username/backup_owner_ids/backup_owner_usernames）"
        elif owner_info.get("mapping_status") == "owner_username_unresolved":
            reason = "owner_username 未映射到有效用户"

    return _forbidden_write_response(request, reason, system_name, system_id)


def _ensure_owner_for_publish(
    current_user: Dict[str, Any],
    *,
    request: Request,
    system_name: str,
    system_id: Optional[str],
):
    roles = current_user.get("roles") or []
    if "manager" not in roles:
        return _forbidden_write_response(request, "当前角色不可发布系统画像", system_name, system_id)

    ownership = system_routes.resolve_system_ownership(
        current_user,
        system_id=system_id,
        system_name=system_name,
    )
    if ownership.get("allowed_publish"):
        return None

    owner_info = ownership.get("owner_info") or {}
    reason = "仅系统主责可发布"
    if not owner_info.get("system_found"):
        reason = "系统不存在或未纳入系统清单"
    elif owner_info.get("mapping_status") == "owner_username_unresolved":
        reason = "owner_username 未映射到有效用户"
    elif owner_info.get("mapping_status") == "owner_not_configured":
        reason = "系统清单未配置主责（owner_id/owner_username）"
    return _forbidden_write_response(request, reason, system_name, system_id)


class SystemProfilePayload(BaseModel):
    system_id: Optional[str] = None
    fields: Dict[str, Any] = Field(default_factory=dict)
    evidence_refs: Optional[list] = None
    field_sources: Optional[Dict[str, Any]] = None


@router.get("")
async def list_profiles(
    status: Optional[str] = Query(None),
    is_stale: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _auth: Dict[str, Any] = Depends(require_roles(["manager", "admin", "expert"])),
):
    service = get_system_profile_service()
    profiles = service.list_profiles(status=status)

    filtered = []
    for profile in profiles:
        stale = _is_profile_stale(profile)
        if is_stale is not None and stale != is_stale:
            continue
        total_score, breakdown, document_count = _build_completeness(profile)
        item = dict(profile)
        item["is_stale"] = stale
        item["completeness_score"] = int(item.get("completeness_score") or total_score)
        item["completeness_breakdown"] = breakdown
        item["document_count"] = int(item.get("document_count") or document_count)
        filtered.append(item)

    filtered.sort(key=lambda item: str(item.get("updated_at") or item.get("created_at") or ""), reverse=True)

    start = (page - 1) * page_size
    end = start + page_size
    return {
        "total": len(filtered),
        "page": page,
        "page_size": page_size,
        "items": filtered[start:end],
    }


@router.get("/completeness")
async def get_profile_completeness(
    system_name: str,
    _auth: Dict[str, Any] = Depends(require_roles(["manager", "admin", "expert"])),
):
    normalized_system_name = str(system_name or "").strip()
    if not normalized_system_name:
        return {
            "exists": False,
            "completeness_score": 0,
            "breakdown": {"code_scan": 0, "documents": 0, "esb": 0},
            "document_count": 0,
        }

    service = get_system_profile_service()
    profile = service.get_profile(normalized_system_name)
    if not profile:
        return {
            "exists": False,
            "completeness_score": 0,
            "breakdown": {"code_scan": 0, "documents": 0, "esb": 0},
            "document_count": 0,
        }

    score, breakdown, document_count = _build_completeness(profile)
    return {
        "exists": True,
        "completeness_score": score,
        "breakdown": breakdown,
        "document_count": document_count,
    }


@router.get("/{system_name}")
async def get_profile(
    system_name: str,
    _auth: Dict[str, Any] = Depends(require_roles(["manager", "admin", "expert"])),
):
    service = get_system_profile_service()
    profile = service.get_profile(system_name)
    if not profile:
        return {"code": 200, "data": None}

    score, breakdown, document_count = _build_completeness(profile)
    payload = dict(profile)
    payload["is_stale"] = _is_profile_stale(profile)
    payload["completeness_score"] = int(payload.get("completeness_score") or score)
    payload["completeness_breakdown"] = breakdown
    payload["document_count"] = int(payload.get("document_count") or document_count)
    return {"code": 200, "data": payload}


@router.put("/{system_name}")
async def save_profile(
    system_name: str,
    payload: SystemProfilePayload,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_roles(["manager", "admin", "expert"])),
):
    normalized_system_name = str(system_name or "").strip()
    system_ref = _resolve_system_ref(normalized_system_name, payload.system_id)
    owner_info = system_ref.get("owner_info") or {}
    if not owner_info.get("system_found"):
        return _system_not_found_response(
            request,
            system_name=normalized_system_name,
            system_id=payload.system_id,
        )

    resolved_system_name = str(system_ref.get("resolved_system_name") or normalized_system_name).strip()
    resolved_system_id = str(system_ref.get("resolved_system_id") or payload.system_id or "").strip() or None
    payload_data = payload.model_dump()
    payload_data["system_id"] = resolved_system_id

    forbidden = _ensure_owner_or_backup_for_draft_write(
        current_user,
        request=request,
        system_name=resolved_system_name,
        system_id=resolved_system_id,
    )
    if forbidden:
        return forbidden

    try:
        service = get_system_profile_service()
        profile = service.upsert_profile(resolved_system_name, payload_data, actor=current_user)
        return {"code": 200, "data": profile}
    except ValueError as exc:
        message = str(exc)
        error_code = "PROFILE_001"
        detail_message = message
        if message == "invalid_module_structure":
            error_code = "invalid_module_structure"
            detail_message = "module_structure 格式错误，需为 JSON 数组"
        return build_error_response(
            request=request,
            status_code=400,
            error_code=error_code,
            message=detail_message,
        )
    except Exception as exc:
        logger.error("保存系统画像失败: %s", exc)
        return build_error_response(
            request=request,
            status_code=500,
            error_code="PROFILE_001",
            message="保存系统画像失败",
            details={"reason": str(exc)},
        )


@router.post("/{system_name}/publish")
async def publish_profile(
    system_name: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_roles(["manager", "admin", "expert"])),
):
    forbidden = _ensure_owner_for_publish(
        current_user,
        request=request,
        system_name=system_name,
        system_id=None,
    )
    if forbidden:
        return forbidden

    try:
        service = get_system_profile_service()
        profile = service.publish_profile(system_name, actor=current_user)
        return {"code": 200, "data": profile}
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
        error_code = "PROFILE_001"
        if "发布失败，缺少必填字段" in message:
            error_code = "PROFILE_003"
        return build_error_response(
            request=request,
            status_code=400,
            error_code=error_code,
            message=message,
        )
    except Exception as exc:
        logger.error("发布系统画像失败: %s", exc)
        return build_error_response(
            request=request,
            status_code=500,
            error_code="PROFILE_001",
            message="发布系统画像失败",
            details={"reason": str(exc)},
        )


@router.post("/{system_id}/ai-suggestions/retry")
async def retry_ai_suggestions(
    system_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_roles(["manager"])),
):
    normalized_system_id = str(system_id or "").strip()
    if not normalized_system_id:
        return build_error_response(
            request=request,
            status_code=404,
            error_code="PROFILE_002",
            message="系统画像不存在",
        )

    owner_info = system_routes.resolve_system_owner(system_id=normalized_system_id)
    if not owner_info.get("system_found"):
        return build_error_response(
            request=request,
            status_code=404,
            error_code="PROFILE_002",
            message="系统画像不存在",
            details={"system_id": normalized_system_id},
        )

    system_name = str(owner_info.get("system_name") or "").strip()
    ownership = system_routes.resolve_system_ownership(
        current_user,
        system_id=normalized_system_id,
        system_name=system_name,
    )
    if not ownership.get("allowed_draft_write"):
        return build_error_response(
            request=request,
            status_code=403,
            error_code="AUTH_001",
            message="权限不足",
            details={"reason": "仅系统主责或B角可重试AI总结", "system_id": normalized_system_id, "system_name": system_name},
        )

    profile_service = get_system_profile_service()
    profile = profile_service.get_profile(system_name)
    if not profile:
        return build_error_response(
            request=request,
            status_code=404,
            error_code="PROFILE_002",
            message="系统画像不存在",
            details={"system_id": normalized_system_id, "system_name": system_name},
        )

    try:
        from backend.service.profile_summary_service import get_profile_summary_service

        job = get_profile_summary_service().trigger_summary(
            system_id=normalized_system_id,
            system_name=system_name,
            actor=current_user,
            reason="manual_retry",
        )
        status = str(job.get("status") or "").strip().lower() or "queued"
        job_id = str(job.get("job_id") or "").strip()
        created_new = bool(job.get("created_new"))
        message = "生成中" if not created_new else "已受理"
        return {
            "job_id": job_id,
            "status": status,
            "message": message,
        }
    except Exception as exc:
        logger.warning("画像AI总结重试失败: %s", exc)
        return build_error_response(
            request=request,
            status_code=503,
            error_code="SUMMARY_001",
            message="画像AI总结失败，请稍后重试",
            details={"reason": str(exc)},
        )
