"""
v2 接口错误响应工具
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import Request
from fastapi.responses import JSONResponse

REQUEST_ID_HEADER = "X-Request-ID"


class ApiError(Exception):
    def __init__(
        self,
        *,
        error_code: str,
        message: str,
        status_code: int,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.details = details


def generate_request_id() -> str:
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    suffix = uuid.uuid4().hex[:8]
    return f"req_{timestamp}_{suffix}"


def ensure_request_id(request: Request) -> str:
    request_id = str(request.headers.get(REQUEST_ID_HEADER) or "").strip()
    if not request_id:
        request_id = str(getattr(request.state, "request_id", "") or "").strip()
    if not request_id:
        request_id = generate_request_id()
    request.state.request_id = request_id
    return request_id


def build_error_payload(
    *,
    request: Request,
    error_code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "error_code": error_code,
        "message": message,
        "request_id": ensure_request_id(request),
    }
    if details:
        payload["details"] = details
    return payload


def build_error_response(
    *,
    request: Request,
    status_code: int,
    error_code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
) -> JSONResponse:
    payload = build_error_payload(
        request=request,
        error_code=error_code,
        message=message,
        details=details,
    )
    return JSONResponse(status_code=status_code, content=payload)

