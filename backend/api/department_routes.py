"""
部门配置API（文件存储版本）
提供部门下拉选项的读取与维护。
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from backend.api.auth import require_roles
from backend.service import department_service

router = APIRouter(prefix="/api/v1/departments", tags=["部门配置"])


class DepartmentsUpdateRequest(BaseModel):
    departments: List[str] = Field(default_factory=list)


@router.get("")
async def get_departments(_user=Depends(require_roles(["admin"]))):
    return {"code": 200, "data": {"departments": department_service.list_departments()}}


@router.put("")
async def update_departments(request: DepartmentsUpdateRequest, _user=Depends(require_roles(["admin"]))):
    saved = department_service.save_departments(request.departments)
    return {"code": 200, "message": "success", "data": {"departments": saved}}

