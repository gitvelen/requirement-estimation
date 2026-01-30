"""
AI效果报告API
"""
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Query, Depends

from backend.service.ai_effect_service import list_snapshots
from backend.api.auth import require_roles
from backend.api import routes as task_routes

router = APIRouter(prefix="/api/v1/reports", tags=["AI效果报告"])


def _parse_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _get_expert_task_ids(current_user: Dict[str, Any]) -> set:
    task_ids = set()
    with task_routes._task_storage_context() as data:
        task_routes._cleanup_tasks(data)
        tasks = list(data.values())

    for task in tasks:
        task_routes._ensure_task_schema(task)
        for assignment in task_routes._get_active_assignments(task):
            if task_routes._assignment_matches_user(assignment, current_user):
                task_ids.add(task.get("task_id"))
                break
    return task_ids


@router.get("/ai-effect")
async def ai_effect_report(
    system_name: Optional[str] = None,
    module: Optional[str] = None,
    manager_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    round_no: Optional[int] = Query(None, alias="round"),
    current_user: Dict[str, Any] = Depends(require_roles(["admin", "manager", "expert"]))
):
    snapshots = list_snapshots()
    if not snapshots:
        return {"code": 200, "data": {"summary": {}, "snapshots": []}}

    roles = current_user.get("roles", [])
    expert_only = "expert" in roles and "admin" not in roles and "manager" not in roles
    if expert_only:
        allowed_task_ids = _get_expert_task_ids(current_user)
        snapshots = [item for item in snapshots if item.get("task_id") in allowed_task_ids]
        if not snapshots:
            return {"code": 200, "data": {"summary": {}, "snapshots": []}}

    start = _parse_date(date_from)
    end = _parse_date(date_to)

    filtered = []
    for item in snapshots:
        if system_name and item.get("system") != system_name:
            continue
        if module and item.get("module") != module:
            continue
        if manager_id and not expert_only and item.get("manager_id") != manager_id:
            continue
        if round_no is not None and item.get("round") != round_no:
            continue
        if start or end:
            created_at = _parse_date(item.get("created_at"))
            if created_at is None:
                continue
            if start and created_at < start:
                continue
            if end and created_at > end:
                continue
        filtered.append(item)

    if not filtered:
        return {"code": 200, "data": {"summary": {}, "snapshots": []}}

    # 汇总均值
    metric_keys = list(filtered[0].get("metrics", {}).keys())
    summary = {key: 0.0 for key in metric_keys}
    for item in filtered:
        metrics = item.get("metrics", {})
        for key in metric_keys:
            summary[key] += float(metrics.get(key, 0.0))
    for key in metric_keys:
        summary[key] = round(summary[key] / len(filtered), 2)

    if expert_only:
        filtered = [
            {k: v for k, v in item.items() if k not in {"manager_id", "manager_name"}}
            for item in filtered
        ]

    return {
        "code": 200,
        "data": {
            "summary": summary,
            "snapshots": filtered
        }
    }
