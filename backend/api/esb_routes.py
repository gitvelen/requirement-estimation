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

from backend.api import system_routes
from backend.api.auth import require_roles
from backend.api.error_utils import build_error_response
from backend.service.esb_service import get_esb_service
from backend.service.system_profile_service import get_system_profile_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/esb", tags=["ESB导入"])


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


@router.post("/imports")
async def import_esb(
    request: Request,
    file: UploadFile = File(...),
    system_id: str = Form(...),
    mapping_json: Optional[str] = Form(None),
    current_user: Dict[str, Any] = Depends(require_roles(["manager", "admin"])),
):
    normalized_system_id = str(system_id or "").strip()
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
        result = service.import_esb(
            file_content=file_content,
            filename=file.filename,
            mapping_json=mapping_override,
            target_system_id=normalized_system_id,
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
