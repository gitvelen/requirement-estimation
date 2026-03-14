"""
系统画像 API（v2.0）
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile, WebSocket, WebSocketDisconnect, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.api import system_routes
from backend.api.auth import decode_access_token, require_roles
from backend.api.error_utils import build_error_response
from backend.config.config import settings
from backend.service.document_skill_adapter import get_document_skill_adapter
from backend.service.knowledge_service import get_knowledge_service
from backend.service.memory_service import get_memory_service
from backend.service.runtime_execution_service import get_runtime_execution_service
from backend.service.system_profile_service import get_system_profile_service
from backend.service import user_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/system-profiles", tags=["系统画像"])
compat_router = APIRouter(prefix="/api/system-profile", tags=["系统画像"])
ws_router = APIRouter(tags=["系统画像"])

TEMPLATE_FILE_MAPPING: Dict[str, str] = {}
TASK_STATUS_MAPPING = {
    "pending": "extraction_started",
    "processing": "extraction_started",
    "completed": "extraction_completed",
    "failed": "extraction_failed",
}
WS_HEARTBEAT_EVENT = "ping"
WS_HEARTBEAT_RESPONSE = "pong"

_ws_connections: Dict[str, List[WebSocket]] = {}
_ws_registry_lock = threading.RLock()
_ws_event_loop: Optional[asyncio.AbstractEventLoop] = None

SUPPORTED_IMPORT_DOC_TYPES = {
    "requirements",
    "design",
    "tech_solution",
}
V27_SUPPORTED_IMPORT_DOC_TYPES = {"requirements", "design", "tech_solution"}

SUPPORTED_IMPORT_EXTENSIONS = {".docx", ".doc", ".pdf", ".pptx", ".txt", ".xlsx", ".xls", ".csv"}


def _parsed_to_text(parsed_data: Any) -> str:
    if isinstance(parsed_data, str):
        return parsed_data

    if isinstance(parsed_data, list):
        lines = []
        for item in parsed_data:
            if isinstance(item, dict):
                line = " ".join(str(v).strip() for v in item.values() if str(v).strip())
                if line:
                    lines.append(line)
            elif item is not None:
                line = str(item).strip()
                if line:
                    lines.append(line)
        return "\n".join(lines)

    if isinstance(parsed_data, dict):
        if "text" in parsed_data and isinstance(parsed_data.get("text"), str):
            return str(parsed_data.get("text") or "")

        # DOCX parser output: {"paragraphs": [...], "tables": [...], "metadata": {...}}
        if "paragraphs" in parsed_data:
            lines = []
            for paragraph in parsed_data.get("paragraphs") or []:
                if isinstance(paragraph, dict):
                    line = str(paragraph.get("text") or "").strip()
                else:
                    line = str(paragraph or "").strip()
                if line:
                    lines.append(line)

            for table in parsed_data.get("tables") or []:
                if not isinstance(table, dict):
                    continue
                for row in table.get("data") or []:
                    if isinstance(row, list):
                        line = " | ".join(str(cell).strip() for cell in row if cell is not None and str(cell).strip())
                    elif isinstance(row, dict):
                        line = " ".join(str(v).strip() for v in row.values() if str(v).strip())
                    else:
                        line = str(row or "").strip()
                    if line:
                        lines.append(line)

            if lines:
                return "\n".join(lines)

        # PPTX parser output: {"slides": [...]}
        if "slides" in parsed_data:
            lines = []
            for slide in parsed_data.get("slides") or []:
                if isinstance(slide, dict):
                    line = str(slide.get("text") or "").strip()
                else:
                    line = str(slide or "").strip()
                if line:
                    lines.append(line)
            if lines:
                return "\n".join(lines)

        # PDF parser output: {"pages": [...]}
        if "pages" in parsed_data:
            lines = []
            for page in parsed_data.get("pages") or []:
                if isinstance(page, dict):
                    line = str(page.get("text") or "").strip()
                else:
                    line = str(page or "").strip()
                if line:
                    lines.append(line)
            if lines:
                return "\n".join(lines)

        if parsed_data and all(isinstance(v, list) for v in parsed_data.values()):
            lines = []
            for _, rows in parsed_data.items():
                for row in rows:
                    if isinstance(row, list):
                        line = " | ".join(str(cell).strip() for cell in row if cell is not None and str(cell).strip())
                        if line:
                            lines.append(line)
                    elif isinstance(row, dict):
                        line = " ".join(str(v).strip() for v in row.values() if str(v).strip())
                        if line:
                            lines.append(line)
            if lines:
                return "\n".join(lines)

        try:
            return json.dumps(parsed_data, ensure_ascii=False)
        except Exception:
            return str(parsed_data)

    return str(parsed_data)


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


def _map_task_status(raw_status: Any) -> str:
    normalized = str(raw_status or "").strip().lower()
    return TASK_STATUS_MAPPING.get(normalized, "extraction_started")


def _resolve_task_system_name(system_id: str) -> str:
    owner_info = system_routes.resolve_system_owner(system_id=system_id)
    return str(owner_info.get("system_name") or "").strip()


def _build_task_status_payload(*, system_id: str, task: Dict[str, Any]) -> Dict[str, Any]:
    normalized_system_id = str(system_id or "").strip()
    task_id = str(task.get("task_id") or "").strip()
    status_name = _map_task_status(task.get("status"))
    system_name = _resolve_task_system_name(normalized_system_id)
    updated_at = str(task.get("completed_at") or task.get("created_at") or datetime.now().isoformat())

    payload = {
        "task_id": task_id,
        "system_id": normalized_system_id,
        "system_name": system_name,
        "status": status_name,
        "updated_at": updated_at,
        "error": task.get("error"),
    }
    if isinstance(task.get("notifications"), list):
        payload["notifications"] = task.get("notifications")
    return payload


def _resolve_template_path(template_type: str) -> Tuple[str, str]:
    normalized_type = str(template_type or "").strip()
    if normalized_type not in TEMPLATE_FILE_MAPPING:
        raise ValueError("TEMPLATE_TYPE_INVALID")

    file_path = str(TEMPLATE_FILE_MAPPING.get(normalized_type) or "").strip()
    if not file_path or not os.path.exists(file_path):
        raise FileNotFoundError("TEMPLATE_NOT_FOUND")

    return file_path, os.path.basename(file_path)


async def _download_template_impl(template_type: str, request: Request) -> Any:
    try:
        template_path, file_name = _resolve_template_path(template_type)
    except ValueError:
        return build_error_response(
            request=request,
            status_code=400,
            error_code="TEMPLATE_TYPE_INVALID",
            message="模板类型无效",
            details={"template_type": str(template_type or "").strip()},
        )
    except FileNotFoundError:
        return build_error_response(
            request=request,
            status_code=404,
            error_code="TEMPLATE_NOT_FOUND",
            message="模板文件不存在",
            details={"template_type": str(template_type or "").strip()},
        )

    return FileResponse(
        template_path,
        filename=file_name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def _task_not_found_response(request: Request, *, task_id: str):
    return build_error_response(
        request=request,
        status_code=404,
        error_code="TASK_NOT_FOUND",
        message="任务不存在",
        details={"task_id": task_id},
    )


def _get_current_task_by_task_id(task_id: str) -> Optional[Dict[str, Any]]:
    service = get_system_profile_service()
    record = service.get_extraction_task_by_task_id(task_id)
    if not isinstance(record, dict):
        return None
    system_id = str(record.get("system_id") or "").strip()
    task = record.get("task") if isinstance(record.get("task"), dict) else {}
    if not system_id or not task:
        return None
    return _build_task_status_payload(system_id=system_id, task=task)


async def _get_task_status_impl(task_id: str, request: Request) -> Any:
    normalized_task_id = str(task_id or "").strip()
    if not normalized_task_id:
        return _task_not_found_response(request, task_id=normalized_task_id)

    payload = _get_current_task_by_task_id(normalized_task_id)
    if payload is None:
        return _task_not_found_response(request, task_id=normalized_task_id)
    return payload


def _resolve_ws_user(websocket: WebSocket) -> Optional[Dict[str, Any]]:
    auth_header = str(websocket.headers.get("authorization") or "").strip()
    token = ""
    if auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1].strip()
    if not token:
        token = str(websocket.query_params.get("token") or "").strip()
    if not token:
        return None

    try:
        payload = decode_access_token(token)
    except Exception:
        return None

    user_id = str(payload.get("user_id") or "").strip()
    if not user_id:
        return None

    users = user_service.list_users()
    user = next((item for item in users if str(item.get("id") or "").strip() == user_id), None)
    if not user or not user.get("is_active"):
        return None
    return user


def _register_ws_connection(system_name: str, websocket: WebSocket) -> None:
    with _ws_registry_lock:
        connections = _ws_connections.get(system_name) or []
        if websocket not in connections:
            connections.append(websocket)
        _ws_connections[system_name] = connections


def _remove_ws_connection(system_name: str, websocket: WebSocket) -> None:
    with _ws_registry_lock:
        connections = list(_ws_connections.get(system_name) or [])
        if websocket in connections:
            connections.remove(websocket)
        if connections:
            _ws_connections[system_name] = connections
        else:
            _ws_connections.pop(system_name, None)


async def _broadcast_ws_event(system_name: str, payload: Dict[str, Any]) -> None:
    with _ws_registry_lock:
        targets = list(_ws_connections.get(system_name) or [])

    disconnected: List[WebSocket] = []
    for websocket in targets:
        try:
            await websocket.send_json(payload)
        except Exception:
            disconnected.append(websocket)

    if disconnected:
        with _ws_registry_lock:
            active = list(_ws_connections.get(system_name) or [])
            for socket in disconnected:
                if socket in active:
                    active.remove(socket)
            if active:
                _ws_connections[system_name] = active
            else:
                _ws_connections.pop(system_name, None)


def _schedule_ws_event(system_name: str, payload: Dict[str, Any]) -> None:
    event_loop = _ws_event_loop
    if event_loop is None or event_loop.is_closed():
        return
    try:
        asyncio.run_coroutine_threadsafe(_broadcast_ws_event(system_name, payload), event_loop)
    except Exception as exc:
        logger.warning("调度 WebSocket 推送失败: %s", exc)


def _on_extraction_task_event(event: Dict[str, Any]) -> None:
    if not isinstance(event, dict):
        return
    system_id = str(event.get("system_id") or "").strip()
    task = event.get("task") if isinstance(event.get("task"), dict) else {}
    if not system_id or not task:
        return

    payload = _build_task_status_payload(system_id=system_id, task=task)
    system_name = str(payload.get("system_name") or "").strip()
    if not system_name:
        return
    _schedule_ws_event(system_name, payload)


def _ensure_extraction_listener_registered() -> None:
    service = get_system_profile_service()
    service.register_extraction_task_listener(_on_extraction_task_event)


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
    profile_data: Optional[Dict[str, Any]] = None
    evidence_refs: Optional[list] = None
    field_sources: Optional[Dict[str, Any]] = None


class SuggestionActionPayload(BaseModel):
    domain: str
    sub_field: str


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


@router.get("/template/{template_type}")
async def download_profile_template(
    template_type: str,
    request: Request,
    _auth: Dict[str, Any] = Depends(require_roles(["manager"])),
):
    return await _download_template_impl(template_type, request)


@compat_router.get("/template/{template_type}")
async def download_profile_template_alias(
    template_type: str,
    request: Request,
    _auth: Dict[str, Any] = Depends(require_roles(["manager"])),
):
    return await _download_template_impl(template_type, request)


@router.get("/task-status/{task_id}")
async def get_profile_task_status_by_task_id(
    task_id: str,
    request: Request,
    _auth: Dict[str, Any] = Depends(require_roles(["manager"])),
):
    return await _get_task_status_impl(task_id, request)


@compat_router.get("/task-status/{task_id}")
async def get_profile_task_status_by_task_id_alias(
    task_id: str,
    request: Request,
    _auth: Dict[str, Any] = Depends(require_roles(["manager"])),
):
    return await _get_task_status_impl(task_id, request)


@ws_router.websocket("/ws/system-profile/{system_name}")
async def system_profile_task_websocket(websocket: WebSocket, system_name: str):
    normalized_system_name = str(system_name or "").strip()
    if not normalized_system_name:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    current_user = _resolve_ws_user(websocket)
    if not current_user or ("manager" not in (current_user.get("roles") or [])):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    _ensure_extraction_listener_registered()

    global _ws_event_loop
    _ws_event_loop = asyncio.get_running_loop()
    _register_ws_connection(normalized_system_name, websocket)

    try:
        while True:
            message_text = await websocket.receive_text()
            event_name = str(message_text or "").strip().lower()
            try:
                parsed = json.loads(message_text)
                if isinstance(parsed, dict):
                    event_name = str(parsed.get("event") or event_name).strip().lower()
            except Exception:
                pass

            if event_name == WS_HEARTBEAT_EVENT:
                await websocket.send_json(
                    {
                        "event": WS_HEARTBEAT_RESPONSE,
                        "system_name": normalized_system_name,
                        "timestamp": datetime.now().isoformat(),
                    }
                )
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning("system profile websocket 连接异常: %s", exc)
    finally:
        _remove_ws_connection(normalized_system_name, websocket)


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


@router.post("/{system_id}/profile/import")
async def import_profile_document(
    system_id: str,
    request: Request,
    file: UploadFile = File(...),
    doc_type: str = Form(...),
    current_user: Dict[str, Any] = Depends(require_roles(["manager", "admin"])),
):
    normalized_system_id = str(system_id or "").strip()
    owner_info = system_routes.resolve_system_owner(system_id=normalized_system_id)
    if not owner_info.get("system_found"):
        return _system_not_found_response(request, system_name="", system_id=normalized_system_id)

    resolved_system_name = str(owner_info.get("system_name") or "").strip()
    forbidden = _ensure_owner_or_backup_for_draft_write(
        current_user,
        request=request,
        system_name=resolved_system_name,
        system_id=normalized_system_id,
    )
    if forbidden:
        return forbidden

    profile_service = get_system_profile_service()
    operator_id = str(current_user.get("id") or current_user.get("username") or "unknown")
    normalized_doc_type = str(doc_type or "").strip().lower()
    file_name = str(file.filename or "").strip()

    def _record_failed_import(reason: str, execution_id: Optional[str] = None) -> Dict[str, Any]:
        return profile_service.record_import_history(
            normalized_system_id,
            doc_type=normalized_doc_type or "unknown",
            file_name=file_name or "unknown",
            status="failed",
            operator_id=operator_id,
            failure_reason=reason,
            execution_id=execution_id,
        )

    if getattr(settings, "ENABLE_V27_RUNTIME", False):
        if normalized_doc_type not in V27_SUPPORTED_IMPORT_DOC_TYPES:
            _record_failed_import("doc_type不支持")
            return build_error_response(
                request=request,
                status_code=400,
                error_code="PROFILE_IMPORT_FAILED",
                message="文档导入失败",
                details={"reason": f"doc_type 仅支持 {', '.join(sorted(V27_SUPPORTED_IMPORT_DOC_TYPES))}"},
            )

        if not file_name:
            _record_failed_import("文件名不能为空")
            return build_error_response(
                request=request,
                status_code=400,
                error_code="PROFILE_IMPORT_FAILED",
                message="文档导入失败",
                details={"reason": "文件名不能为空"},
            )

        try:
            file_content = await file.read()
            if not file_content:
                raise ValueError("文件内容为空")

            max_bytes = int(getattr(settings, "SYSTEM_PROFILE_IMPORT_MAX_BYTES", 200 * 1024 * 1024))
            max_mb = max(int(max_bytes // (1024 * 1024)), 1)
            if len(file_content) > max_bytes:
                raise ValueError(f"文件大小超过{max_mb}MB限制")

            adapter = get_document_skill_adapter()
            result = adapter.ingest_document(
                system_id=normalized_system_id,
                system_name=resolved_system_name,
                doc_type=normalized_doc_type,
                file_name=file_name,
                file_content=file_content,
                actor=current_user,
            )
            execution = result["execution"]
            history = profile_service.record_import_history(
                normalized_system_id,
                doc_type=normalized_doc_type,
                file_name=file_name,
                status="success",
                operator_id=operator_id,
                failure_reason=None,
                execution_id=execution["execution_id"],
            )
            return {
                "result_status": "queued",
                "execution_id": execution["execution_id"],
                "scene_id": "pm_document_ingest",
                "import_result": {
                    "status": "success",
                    "file_name": file_name,
                    "imported_at": history.get("imported_at"),
                    "failure_reason": None,
                },
                "execution_status": {
                    "status": execution.get("status") or "queued",
                    "error": execution.get("error"),
                },
            }
        except ValueError as exc:
            history = _record_failed_import(str(exc))
            return build_error_response(
                request=request,
                status_code=400,
                error_code="PROFILE_IMPORT_FAILED",
                message="文档导入失败",
                details={"reason": history.get("failure_reason")},
            )
        except Exception as exc:
            logger.error("v2.7 系统画像文档导入失败: %s", exc)
            history = _record_failed_import(str(exc))
            return build_error_response(
                request=request,
                status_code=400,
                error_code="PROFILE_IMPORT_FAILED",
                message="文档导入失败",
                details={"reason": history.get("failure_reason")},
            )

    if normalized_doc_type not in SUPPORTED_IMPORT_DOC_TYPES:
        _record_failed_import("doc_type不支持")
        return build_error_response(
            request=request,
            status_code=400,
            error_code="PROFILE_IMPORT_FAILED",
            message="文档导入失败",
            details={"reason": f"doc_type 仅支持 {', '.join(sorted(SUPPORTED_IMPORT_DOC_TYPES))}"},
        )

    if not file_name:
        _record_failed_import("文件名不能为空")
        return build_error_response(
            request=request,
            status_code=400,
            error_code="PROFILE_IMPORT_FAILED",
            message="文档导入失败",
            details={"reason": "文件名不能为空"},
        )

    ext = os.path.splitext(file_name.lower())[1]
    if ext not in SUPPORTED_IMPORT_EXTENSIONS:
        _record_failed_import(f"文件类型不支持: {ext}")
        return build_error_response(
            request=request,
            status_code=400,
            error_code="PROFILE_IMPORT_FAILED",
            message="文档导入失败",
            details={"reason": f"文件类型不支持: {ext}"},
        )

    try:
        file_content = await file.read()
        if not file_content:
            raise ValueError("文件内容为空")

        max_bytes = int(getattr(settings, "SYSTEM_PROFILE_IMPORT_MAX_BYTES", 200 * 1024 * 1024))
        max_mb = max(int(max_bytes // (1024 * 1024)), 1)
        if len(file_content) > max_bytes:
            raise ValueError(f"文件大小超过{max_mb}MB限制")

        knowledge_service = get_knowledge_service()
        parsed_data = knowledge_service.document_parser.parse(
            file_content=file_content,
            filename=file_name,
        )
        text_content = _parsed_to_text(parsed_data)
        if not str(text_content or "").strip():
            text_content = file_content.decode("utf-8", errors="ignore")

        chunks = knowledge_service._chunk_text(text_content)
        if not chunks:
            raise ValueError("未提取到可入库内容")

        embeddings = knowledge_service.embedding_service.batch_generate_embeddings(chunks)
        knowledge_list = []
        for idx, chunk in enumerate(chunks):
            embedding = embeddings[idx] if idx < len(embeddings) else []
            metadata = {
                "doc_type": normalized_doc_type,
                "chunk_index": idx,
                "source_filename": file_name,
                "bound_system_id": normalized_system_id,
                "bound_system_name": resolved_system_name,
                "imported_by": operator_id,
            }
            knowledge_list.append(
                {
                    "system_name": resolved_system_name,
                    "knowledge_type": "document",
                    "content": chunk,
                    "embedding": embedding,
                    "metadata": metadata,
                    "source_file": file_name,
                }
            )

        insert_result = knowledge_service.vector_store.batch_insert_knowledge(knowledge_list)
        imported = int(insert_result.get("success") or 0)
        failed = int(insert_result.get("failed") or 0)
        if imported <= 0:
            failure_reason = "文档入库失败"
            if failed > 0:
                failure_reason = f"文档入库失败，失败条目: {failed}"
            history = profile_service.record_import_history(
                normalized_system_id,
                doc_type=normalized_doc_type,
                file_name=file_name,
                status="failed",
                operator_id=operator_id,
                failure_reason=failure_reason,
            )
            return build_error_response(
                request=request,
                status_code=400,
                error_code="PROFILE_IMPORT_FAILED",
                message="文档导入失败",
                details={"reason": history.get("failure_reason")},
            )

        history = profile_service.record_import_history(
            normalized_system_id,
            doc_type=normalized_doc_type,
            file_name=file_name,
            status="success",
            operator_id=operator_id,
            failure_reason=None,
        )

        profile_service.mark_document_imported(
            system_name=resolved_system_name,
            system_id=normalized_system_id,
            import_id=str(history.get("id") or uuid.uuid4().hex),
            source_file=file_name,
            level="normal",
            actor=current_user,
        )

        from backend.service.profile_summary_service import get_profile_summary_service

        job = get_profile_summary_service().trigger_summary(
            system_id=normalized_system_id,
            system_name=resolved_system_name,
            actor=current_user,
            reason="document_import",
            source_file=file_name,
            trigger="document_import",
            context_override={"document_text": text_content},
        )

        payload: Dict[str, Any] = {
            "import_result": {
                "status": "success",
                "file_name": file_name,
                "imported_at": history.get("imported_at"),
                "failure_reason": None,
            }
        }
        extraction_task_id = str(job.get("job_id") or "").strip()
        if extraction_task_id:
            payload["extraction_task_id"] = extraction_task_id
        return payload
    except ValueError as exc:
        history = _record_failed_import(str(exc))
        return build_error_response(
            request=request,
            status_code=400,
            error_code="PROFILE_IMPORT_FAILED",
            message="文档导入失败",
            details={"reason": history.get("failure_reason")},
        )
    except Exception as exc:
        logger.error("系统画像文档导入失败: %s", exc)
        history = _record_failed_import(str(exc))
        return build_error_response(
            request=request,
            status_code=400,
            error_code="PROFILE_IMPORT_FAILED",
            message="文档导入失败",
            details={"reason": history.get("failure_reason")},
        )


@router.get("/{system_id}/profile/import-history")
async def get_profile_import_history(
    system_id: str,
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _auth: Dict[str, Any] = Depends(require_roles(["manager", "admin", "expert"])),
):
    normalized_system_id = str(system_id or "").strip()
    owner_info = system_routes.resolve_system_owner(system_id=normalized_system_id)
    if not owner_info.get("system_found"):
        return _system_not_found_response(request, system_name="", system_id=normalized_system_id)

    service = get_system_profile_service()
    return service.get_import_history(normalized_system_id, limit=limit, offset=offset)


def _default_v27_execution_status() -> Dict[str, Any]:
    return {
        "execution_id": None,
        "scene_id": None,
        "status": "completed",
        "created_at": None,
        "completed_at": None,
        "skill_chain": [],
        "policy_results": [],
        "error": None,
        "notifications": [],
    }


def _get_execution_status_payload(system_id: str) -> Dict[str, Any]:
    if getattr(settings, "ENABLE_V27_RUNTIME", False):
        latest = get_runtime_execution_service().get_latest_execution(system_id)
        if not latest:
            return _default_v27_execution_status()
        return {
            "execution_id": latest.get("execution_id"),
            "scene_id": latest.get("scene_id"),
            "status": latest.get("status") or "queued",
            "created_at": latest.get("created_at"),
            "completed_at": latest.get("completed_at"),
            "skill_chain": latest.get("skill_chain") if isinstance(latest.get("skill_chain"), list) else [],
            "policy_results": latest.get("policy_results") if isinstance(latest.get("policy_results"), list) else [],
            "error": latest.get("error"),
            "notifications": latest.get("notifications") if isinstance(latest.get("notifications"), list) else [],
        }

    service = get_system_profile_service()
    task = service.get_extraction_task(system_id)
    if not task:
        return {
            "task_id": None,
            "status": "completed",
            "trigger": "document_import",
            "created_at": None,
            "completed_at": None,
            "error": None,
            "notifications": [],
        }

    return {
        "task_id": task.get("task_id"),
        "status": task.get("status") or "pending",
        "trigger": task.get("trigger") or "document_import",
        "created_at": task.get("created_at"),
        "completed_at": task.get("completed_at"),
        "error": task.get("error"),
        "notifications": task.get("notifications") if isinstance(task.get("notifications"), list) else [],
    }


@router.get("/{system_id}/profile/execution-status")
async def get_profile_execution_status(
    system_id: str,
    request: Request,
    _auth: Dict[str, Any] = Depends(require_roles(["manager", "admin", "expert"])),
):
    normalized_system_id = str(system_id or "").strip()
    owner_info = system_routes.resolve_system_owner(system_id=normalized_system_id)
    if not owner_info.get("system_found"):
        return _system_not_found_response(request, system_name="", system_id=normalized_system_id)

    return _get_execution_status_payload(normalized_system_id)


@router.get("/{system_id}/profile/extraction-status")
async def get_profile_extraction_status(
    system_id: str,
    request: Request,
    _auth: Dict[str, Any] = Depends(require_roles(["manager", "admin", "expert"])),
):
    normalized_system_id = str(system_id or "").strip()
    owner_info = system_routes.resolve_system_owner(system_id=normalized_system_id)
    if not owner_info.get("system_found"):
        return _system_not_found_response(request, system_name="", system_id=normalized_system_id)
    return _get_execution_status_payload(normalized_system_id)


@router.get("/{system_id}/memory")
async def get_profile_memory(
    system_id: str,
    request: Request,
    memory_type: Optional[str] = Query(None),
    scene_id: Optional[str] = Query(None),
    start_at: Optional[str] = Query(None),
    end_at: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    _auth: Dict[str, Any] = Depends(require_roles(["manager", "admin", "expert"])),
):
    normalized_system_id = str(system_id or "").strip()
    owner_info = system_routes.resolve_system_owner(system_id=normalized_system_id)
    if not owner_info.get("system_found"):
        return _system_not_found_response(request, system_name="", system_id=normalized_system_id)

    try:
        return get_memory_service().query_records(
            normalized_system_id,
            memory_type=memory_type,
            scene_id=scene_id,
            start_at=start_at,
            end_at=end_at,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        return build_error_response(
            request=request,
            status_code=400,
            error_code="PROFILE_002",
            message="查询系统 Memory 失败",
            details={"reason": str(exc), "system_id": normalized_system_id},
        )
    except Exception as exc:
        logger.error("查询系统 Memory 失败: %s", exc)
        return build_error_response(
            request=request,
            status_code=500,
            error_code="PROFILE_002",
            message="查询系统 Memory 失败",
            details={"reason": str(exc), "system_id": normalized_system_id},
        )


@router.get("/{system_id}/profile/events")
async def get_profile_events(
    system_id: str,
    request: Request,
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _auth: Dict[str, Any] = Depends(require_roles(["manager", "admin", "expert"])),
):
    normalized_system_id = str(system_id or "").strip()
    owner_info = system_routes.resolve_system_owner(system_id=normalized_system_id)
    if not owner_info.get("system_found"):
        return _system_not_found_response(request, system_name="", system_id=normalized_system_id)

    resolved_system_name = str(owner_info.get("system_name") or "").strip()
    service = get_system_profile_service()
    try:
        return service.get_profile_events(resolved_system_name, limit=limit, offset=offset)
    except ValueError:
        return _system_not_found_response(
            request,
            system_name=resolved_system_name,
            system_id=normalized_system_id,
        )
    except Exception as exc:
        logger.error("查询系统画像事件失败: %s", exc)
        return build_error_response(
            request=request,
            status_code=500,
            error_code="PROFILE_EVENTS_QUERY_FAILED",
            message="查询画像事件失败",
            details={"reason": str(exc)},
        )


@router.post("/{system_id}/profile/suggestions/accept")
async def accept_profile_suggestion(
    system_id: str,
    payload: SuggestionActionPayload,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_roles(["manager", "admin"])),
):
    normalized_system_id = str(system_id or "").strip()
    owner_info = system_routes.resolve_system_owner(system_id=normalized_system_id)
    if not owner_info.get("system_found"):
        return _system_not_found_response(request, system_name="", system_id=normalized_system_id)

    resolved_system_name = str(owner_info.get("system_name") or "").strip()
    forbidden = _ensure_owner_or_backup_for_draft_write(
        current_user,
        request=request,
        system_name=resolved_system_name,
        system_id=normalized_system_id,
    )
    if forbidden:
        return forbidden

    service = get_system_profile_service()
    try:
        profile = service.accept_ai_suggestion(
            resolved_system_name,
            domain=payload.domain,
            sub_field=payload.sub_field,
            actor=current_user,
        )
        return {"code": 200, "data": profile}
    except ValueError as exc:
        if str(exc) == "SUGGESTION_NOT_FOUND":
            return build_error_response(
                request=request,
                status_code=404,
                error_code="SUGGESTION_NOT_FOUND",
                message="AI 建议不存在",
                details={"domain": payload.domain, "sub_field": payload.sub_field},
            )
        return build_error_response(
            request=request,
            status_code=400,
            error_code="PROFILE_ACCEPT_FAILED",
            message=str(exc),
        )
    except Exception as exc:
        logger.error("采纳 AI 建议失败: %s", exc)
        return build_error_response(
            request=request,
            status_code=500,
            error_code="PROFILE_ACCEPT_FAILED",
            message="采纳 AI 建议失败",
            details={"reason": str(exc)},
        )


@router.post("/{system_id}/profile/suggestions/ignore")
async def ignore_profile_suggestion(
    system_id: str,
    payload: SuggestionActionPayload,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_roles(["manager", "admin"])),
):
    normalized_system_id = str(system_id or "").strip()
    owner_info = system_routes.resolve_system_owner(system_id=normalized_system_id)
    if not owner_info.get("system_found"):
        return _system_not_found_response(request, system_name="", system_id=normalized_system_id)

    resolved_system_name = str(owner_info.get("system_name") or "").strip()
    forbidden = _ensure_owner_or_backup_for_draft_write(
        current_user,
        request=request,
        system_name=resolved_system_name,
        system_id=normalized_system_id,
    )
    if forbidden:
        return forbidden

    service = get_system_profile_service()
    try:
        profile = service.ignore_ai_suggestion(
            resolved_system_name,
            domain=payload.domain,
            sub_field=payload.sub_field,
            actor=current_user,
        )
        return {"code": 200, "data": profile}
    except ValueError as exc:
        if str(exc) == "SUGGESTION_NOT_FOUND":
            return build_error_response(
                request=request,
                status_code=404,
                error_code="SUGGESTION_NOT_FOUND",
                message="AI 建议不存在",
                details={"domain": payload.domain, "sub_field": payload.sub_field},
            )
        return build_error_response(
            request=request,
            status_code=400,
            error_code="PROFILE_IGNORE_FAILED",
            message=str(exc),
        )
    except Exception as exc:
        logger.error("忽略 AI 建议失败: %s", exc)
        return build_error_response(
            request=request,
            status_code=500,
            error_code="PROFILE_IGNORE_FAILED",
            message="忽略 AI 建议失败",
            details={"reason": str(exc)},
        )


@router.post("/{system_id}/profile/suggestions/rollback")
async def rollback_profile_suggestion(
    system_id: str,
    payload: SuggestionActionPayload,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_roles(["manager", "admin"])),
):
    normalized_system_id = str(system_id or "").strip()
    owner_info = system_routes.resolve_system_owner(system_id=normalized_system_id)
    if not owner_info.get("system_found"):
        return _system_not_found_response(request, system_name="", system_id=normalized_system_id)

    resolved_system_name = str(owner_info.get("system_name") or "").strip()
    forbidden = _ensure_owner_or_backup_for_draft_write(
        current_user,
        request=request,
        system_name=resolved_system_name,
        system_id=normalized_system_id,
    )
    if forbidden:
        return forbidden

    service = get_system_profile_service()
    try:
        rollback_result = service.rollback_ai_suggestion(
            resolved_system_name,
            domain=payload.domain,
            sub_field=payload.sub_field,
            actor=current_user,
        )
        return {
            "code": 200,
            "data": rollback_result.get("profile"),
            "rolled_back_value": rollback_result.get("rolled_back_value"),
        }
    except ValueError as exc:
        message = str(exc)
        if message == "ROLLBACK_NO_PREVIOUS":
            return build_error_response(
                request=request,
                status_code=409,
                error_code="ROLLBACK_NO_PREVIOUS",
                message="无历史版本可回滚",
                details={"domain": payload.domain, "sub_field": payload.sub_field},
            )
        return build_error_response(
            request=request,
            status_code=400,
            error_code="PROFILE_ROLLBACK_FAILED",
            message=message,
        )
    except Exception as exc:
        logger.error("回滚 AI 建议失败: %s", exc)
        return build_error_response(
            request=request,
            status_code=500,
            error_code="PROFILE_ROLLBACK_FAILED",
            message="回滚 AI 建议失败",
            details={"reason": str(exc)},
        )


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
