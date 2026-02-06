"""
代码扫描API（Spring Boot MVP）
"""
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.api.auth import require_roles
from backend.service.code_scan_service import get_code_scan_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/code-scan", tags=["代码扫描"])


class CodeScanRunRequest(BaseModel):
    system_name: str
    system_id: Optional[str] = None
    repo_path: str
    options: Optional[Dict[str, Any]] = None


@router.post("/run")
async def run_scan(
    payload: CodeScanRunRequest,
    current_user: Dict[str, Any] = Depends(require_roles(["manager", "admin"]))
):
    try:
        service = get_code_scan_service()
        job_id = service.run_scan(
            system_name=payload.system_name,
            system_id=payload.system_id,
            repo_path=payload.repo_path,
            options=payload.options or {},
            created_by=current_user.get("id") or current_user.get("username") or "",
        )
        return {"code": 200, "data": {"job_id": job_id}}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(f"触发扫描失败: {exc}")
        raise HTTPException(status_code=500, detail=f"触发扫描失败: {exc}") from exc


@router.get("/status/{job_id}")
async def scan_status(
    job_id: str,
    _auth: Dict[str, Any] = Depends(require_roles(["manager", "admin"]))
):
    service = get_code_scan_service()
    job = service.get_status(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"code": 200, "data": job}


@router.get("/result/{job_id}")
async def scan_result(
    job_id: str,
    _auth: Dict[str, Any] = Depends(require_roles(["manager", "admin"]))
):
    try:
        service = get_code_scan_service()
        result = service.get_result(job_id)
        return {"code": 200, "data": result}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(f"获取扫描结果失败: {exc}")
        raise HTTPException(status_code=500, detail=f"获取扫描结果失败: {exc}") from exc


@router.post("/commit/{job_id}")
async def commit_result(
    job_id: str,
    _auth: Dict[str, Any] = Depends(require_roles(["manager", "admin"]))
):
    try:
        service = get_code_scan_service()
        result = service.commit_result(job_id)
        return {"code": 200, "data": result}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(f"提交扫描结果失败: {exc}")
        raise HTTPException(status_code=500, detail=f"提交扫描结果失败: {exc}") from exc


@router.get("/jobs")
async def list_jobs(
    _auth: Dict[str, Any] = Depends(require_roles(["manager", "admin"]))
):
    service = get_code_scan_service()
    jobs = service.list_jobs()
    return {"code": 200, "data": jobs}

