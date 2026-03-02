"""
证据等级规则配置API
"""
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.api.auth import require_roles
from backend.service.evidence_level_service import get_evidence_level_service
from backend.service.audit_log_service import get_audit_log_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/evidence-level", tags=["证据等级"])


class EvidenceRulePayload(BaseModel):
    rules: Optional[Dict[str, Any]] = None
    version: Optional[int] = None
    levels: Optional[List[Any]] = None


@router.get("/rules")
async def get_rules(
    _auth: Dict[str, Any] = Depends(require_roles(["admin", "manager"]))
):
    service = get_evidence_level_service()
    return {"code": 200, "data": service.get_rules()}


@router.put("/rules")
async def update_rules(
    payload: EvidenceRulePayload,
    current_user: Dict[str, Any] = Depends(require_roles(["admin"]))
):
    try:
        rules_payload = payload.rules
        if not isinstance(rules_payload, dict):
            rules_payload = {
                "version": payload.version,
                "levels": payload.levels or [],
            }

        service = get_evidence_level_service()
        updated = service.update_rules(rules_payload, actor=current_user)
        audit_service = get_audit_log_service()
        audit_service.append(
            action="evidence_rule_update",
            actor=current_user,
            detail={"rules": updated},
        )
        return {"code": 200, "data": updated}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(f"更新证据等级规则失败: {exc}")
        raise HTTPException(status_code=500, detail=f"更新证据等级规则失败: {exc}") from exc


@router.get("/rules/logs")
async def list_rule_logs(
    _auth: Dict[str, Any] = Depends(require_roles(["admin"]))
):
    audit_service = get_audit_log_service()
    logs = audit_service.list_logs(action="evidence_rule_update", limit=200)
    return {"code": 200, "data": logs}
