"""
系统画像API（B层）
"""
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.api.auth import require_roles
from backend.service.system_profile_service import get_system_profile_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/system-profiles", tags=["系统画像"])


class SystemProfilePayload(BaseModel):
    system_id: Optional[str] = None
    fields: Dict[str, Any] = Field(default_factory=dict)
    evidence_refs: Optional[list] = None


@router.get("/{system_name}")
async def get_profile(
    system_name: str,
    _auth: Dict[str, Any] = Depends(require_roles(["manager", "admin"]))
):
    service = get_system_profile_service()
    profile = service.get_profile(system_name)
    if not profile:
        return {"code": 200, "data": None}
    return {"code": 200, "data": profile}


@router.put("/{system_name}")
async def save_profile(
    system_name: str,
    payload: SystemProfilePayload,
    current_user: Dict[str, Any] = Depends(require_roles(["manager", "admin"]))
):
    try:
        service = get_system_profile_service()
        profile = service.upsert_profile(system_name, payload.dict(), actor=current_user)
        return {"code": 200, "data": profile}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(f"保存系统画像失败: {exc}")
        raise HTTPException(status_code=500, detail=f"保存系统画像失败: {exc}") from exc


@router.post("/{system_name}/publish")
async def publish_profile(
    system_name: str,
    current_user: Dict[str, Any] = Depends(require_roles(["manager", "admin"]))
):
    try:
        service = get_system_profile_service()
        profile = service.publish_profile(system_name, actor=current_user)
        return {"code": 200, "data": profile}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(f"发布系统画像失败: {exc}")
        raise HTTPException(status_code=500, detail=f"发布系统画像失败: {exc}") from exc

