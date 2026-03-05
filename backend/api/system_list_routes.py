"""
系统清单配置API（XLSX批量导入）
支持从一个包含“主系统清单/子系统清单”两个Sheet的Excel文件中导入铺底数据。
"""

from __future__ import annotations

import logging
import os
import re
import uuid
import zipfile
from datetime import date, datetime
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, File, Header, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.api.auth import require_admin_api_key
from backend.api import system_routes, subsystem_routes
from backend.api.error_utils import ApiError, build_error_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/system-list", tags=["系统清单配置"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEMPLATE_PATH = os.path.join(BASE_DIR, "docs", "系统清单模板.xlsx")


class SystemListImportConfirmRequest(BaseModel):
    mode: str = Field("replace", description="replace=覆盖导入；upsert=增量导入")
    systems: List[Dict[str, Any]] = Field(default_factory=list)
    mappings: List[Dict[str, Any]] = Field(default_factory=list)


async def require_system_list_admin(
    x_api_key: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None),
) -> None:
    try:
        require_admin_api_key(x_api_key=x_api_key, authorization=authorization)
    except HTTPException as exc:
        status_code = 403
        if int(exc.status_code or 0) >= 500:
            status_code = int(exc.status_code)
        raise ApiError(
            error_code="AUTH_001",
            message="权限不足",
            status_code=status_code,
            details={"reason": str(exc.detail)},
        ) from exc


def _to_api_error(exc: Exception, *, default_error_code: str = "SYSLIST_001") -> ApiError:
    if isinstance(exc, ApiError):
        return exc
    if isinstance(exc, HTTPException):
        status_code = int(exc.status_code or 400)
        error_code = default_error_code
        if status_code == 403:
            error_code = "AUTH_001"
        message = str(exc.detail or "系统清单处理失败")
        return ApiError(error_code=error_code, message=message, status_code=status_code)
    return ApiError(
        error_code=default_error_code,
        message="系统清单处理失败",
        status_code=400,
        details={"reason": str(exc)},
    )


def _normalize_system_extra(extra: Any) -> Dict[str, Any]:
    if not isinstance(extra, dict):
        return {}

    normalized_extra: Dict[str, Any] = {}
    for raw_key, raw_value in extra.items():
        canonical_key = system_routes.resolve_owner_extra_key(str(raw_key or ""))
        key = canonical_key or str(raw_key or "").strip()
        if not key:
            continue
        if raw_value is None:
            normalized_extra[key] = ""
        elif isinstance(raw_value, (list, dict)):
            normalized_extra[key] = raw_value
        else:
            normalized_extra[key] = str(raw_value).strip()

    normalized_extra, _ = system_routes.normalize_system_owner_extra_fields(normalized_extra)
    return normalized_extra


def _normalize_header(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = text.replace("\n", "").replace("\r", "").strip()
    return text


def _cell_to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value).strip()


def _sanitize_xlsx_for_openpyxl(content: bytes) -> bytes:
    """
    兼容性处理：当前环境 openpyxl 无法解析带 dataValidation 的部分文件（含 id 属性）。
    这里移除 worksheet xml 中的 <dataValidations>...</dataValidations> 片段，避免解析失败。
    """
    in_mem = BytesIO(content)
    out_mem = BytesIO()
    try:
        with zipfile.ZipFile(in_mem, "r") as zin, zipfile.ZipFile(out_mem, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename.startswith("xl/worksheets/") and item.filename.endswith(".xml"):
                    try:
                        text = data.decode("utf-8")
                        text = re.sub(r"<dataValidations[^>]*/>", "", text, flags=re.DOTALL)
                        text = re.sub(r"<dataValidations[^>]*>[\s\S]*?</dataValidations>", "", text, flags=re.DOTALL)
                        data = text.encode("utf-8")
                    except UnicodeDecodeError:
                        pass
                zout.writestr(item, data)
        return out_mem.getvalue()
    except zipfile.BadZipFile as exc:
        raise ApiError(
            error_code="SYSLIST_001",
            message="系统清单文件不合法",
            status_code=400,
            details={"reason": "无效的XLSX文件"},
        ) from exc


def _load_workbook(content: bytes):
    try:
        from openpyxl import load_workbook
    except Exception as exc:
        raise ApiError(
            error_code="SYSLIST_001",
            message="系统清单文件不合法",
            status_code=500,
            details={"reason": "缺少Excel解析依赖 openpyxl"},
        ) from exc

    sanitized = _sanitize_xlsx_for_openpyxl(content)
    try:
        return load_workbook(BytesIO(sanitized), data_only=True)
    except Exception as exc:
        logger.exception("解析XLSX失败")
        raise ApiError(
            error_code="SYSLIST_001",
            message="系统清单文件不合法",
            status_code=400,
            details={"reason": f"解析XLSX失败: {str(exc)}"},
        ) from exc


def _detect_sheets(wb) -> Tuple[Any, Any]:
    main_sheet = None
    subsystem_sheet = None

    name_headers = {"系统名称", "系统名", "系统", "name", "system_name"}
    abbr_headers = {"英文简称", "系统简称", "英文缩写", "abbreviation", "abbr"}
    status_headers = {"状态", "系统状态", "status"}
    main_system_headers = {"所属系统", "所属主系统", "主系统", "main_system", "mainSystem"}

    for name in wb.sheetnames:
        ws = wb[name]
        first_row = [ _normalize_header(cell) for cell in next(ws.iter_rows(values_only=True), []) ]
        if not first_row:
            continue
        header_set = {item for item in first_row if item}
        if header_set & main_system_headers:
            subsystem_sheet = ws
        elif (header_set & name_headers) and (header_set & abbr_headers):
            main_sheet = ws

    if not subsystem_sheet:
        # fallback: find by header in first 10 rows
        for name in wb.sheetnames:
            ws = wb[name]
            for row in ws.iter_rows(min_row=1, max_row=10, values_only=True):
                headers = {_normalize_header(cell) for cell in row if _normalize_header(cell)}
                if headers & main_system_headers:
                    subsystem_sheet = ws
                    break
            if subsystem_sheet:
                break

    if not main_sheet:
        for name in wb.sheetnames:
            ws = wb[name]
            for row in ws.iter_rows(min_row=1, max_row=10, values_only=True):
                headers = {_normalize_header(cell) for cell in row if _normalize_header(cell)}
                if (headers & name_headers) and (headers & abbr_headers) and (headers & status_headers):
                    if not (headers & main_system_headers):
                        main_sheet = ws
                        break
            if main_sheet:
                break

    if not main_sheet or not subsystem_sheet:
        raise ApiError(
            error_code="SYSLIST_002",
            message="系统清单模板不匹配",
            status_code=400,
            details={"reason": "未找到有效的Sheet，请使用系统清单模板填写后导入"},
        )

    return main_sheet, subsystem_sheet


def _find_header_row(ws, header_aliases: Dict[str, List[str]]) -> Tuple[int, Dict[str, int]]:
    """
    尽量容错识别表头：通过别名集合匹配并输出 canonical -> index 的映射。
    header_aliases: {"name": [...], "abbreviation": [...], "status": [...]} 等
    """
    required_keys = [key for key in header_aliases.keys() if key in {"name", "abbreviation", "subsystem", "main_system"}]
    for idx, row in enumerate(ws.iter_rows(min_row=1, max_row=20, values_only=True), start=1):
        headers = [_normalize_header(cell) for cell in row]
        raw_map: Dict[str, int] = {}
        for col_index, header in enumerate(headers):
            if header and header not in raw_map:
                raw_map[header] = col_index

        canonical_map: Dict[str, int] = {}
        for canonical, aliases in header_aliases.items():
            for alias in aliases:
                if alias in raw_map:
                    canonical_map[canonical] = raw_map[alias]
                    break

        if all(key in canonical_map for key in required_keys):
            return idx, canonical_map
    raise ApiError(
        error_code="SYSLIST_002",
        message="系统清单模板不匹配",
        status_code=400,
        details={"reason": "模板表头无法识别，请尽量使用模板字段名（系统名称/英文简称/状态/所属系统）"},
    )


def _validate_systems(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    for item in rows:
        item.setdefault("errors", [])

    return rows


def _validate_mappings(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    for item in rows:
        item.setdefault("errors", [])
    return rows


def _parse_systems_sheet(ws) -> List[Dict[str, Any]]:
    header_row, header_map = _find_header_row(ws, {
        "name": ["系统名称", "系统名", "系统", "name", "system_name"],
        "abbreviation": ["英文简称", "系统简称", "英文缩写", "abbreviation", "abbr"],
        "status": ["状态", "系统状态", "status"],
    })
    name_idx = header_map["name"]
    abbr_idx = header_map["abbreviation"]
    status_idx = header_map.get("status")

    header_values = next(ws.iter_rows(min_row=header_row, max_row=header_row, values_only=True), [])
    normalized_headers = [_normalize_header(cell) for cell in header_values]
    seen_headers: Dict[str, int] = {}
    index_to_header: Dict[int, str] = {}
    for col_index, raw_header in enumerate(normalized_headers):
        if not raw_header:
            continue
        if raw_header in seen_headers:
            seen_headers[raw_header] += 1
            header_key = f"{raw_header}#{seen_headers[raw_header]}"
        else:
            seen_headers[raw_header] = 1
            header_key = raw_header
        index_to_header[col_index] = header_key

    core_indices = {name_idx, abbr_idx}
    if status_idx is not None:
        core_indices.add(status_idx)

    results = []
    for row in ws.iter_rows(min_row=header_row + 1, values_only=True):
        if not any(_cell_to_text(cell) for cell in row):
            continue

        name = row[name_idx] if name_idx < len(row) else None
        abbr = row[abbr_idx] if abbr_idx < len(row) else None
        status = row[status_idx] if status_idx is not None and status_idx < len(row) else None

        name = _cell_to_text(name)
        abbr = _cell_to_text(abbr)
        status = _cell_to_text(status)

        extra: Dict[str, Any] = {}
        for col_index, header_key in index_to_header.items():
            if col_index in core_indices:
                continue
            cell_value = row[col_index] if col_index < len(row) else None
            extra[header_key] = _cell_to_text(cell_value)

        extra = _normalize_system_extra(extra)

        results.append({
            "name": name,
            "abbreviation": abbr,
            "status": status,
            "extra": extra,
            "errors": [],
        })
    return _validate_systems(results)


def _parse_subsystem_sheet(ws) -> List[Dict[str, Any]]:
    header_row, header_map = _find_header_row(ws, {
        "subsystem": ["子系统名称", "系统名称", "子系统", "subsystem"],
        "main_system": ["所属系统", "所属主系统", "主系统", "main_system", "mainSystem"],
    })
    subsystem_idx = header_map["subsystem"]
    main_system_idx = header_map["main_system"]

    header_values = next(ws.iter_rows(min_row=header_row, max_row=header_row, values_only=True), [])
    normalized_headers = [_normalize_header(cell) for cell in header_values]
    seen_headers: Dict[str, int] = {}
    index_to_header: Dict[int, str] = {}
    for col_index, raw_header in enumerate(normalized_headers):
        if not raw_header:
            continue
        if raw_header in seen_headers:
            seen_headers[raw_header] += 1
            header_key = f"{raw_header}#{seen_headers[raw_header]}"
        else:
            seen_headers[raw_header] = 1
            header_key = raw_header
        index_to_header[col_index] = header_key

    core_indices = {subsystem_idx, main_system_idx}

    results = []
    for row in ws.iter_rows(min_row=header_row + 1, values_only=True):
        if not any(_cell_to_text(cell) for cell in row):
            continue

        subsystem = row[subsystem_idx] if subsystem_idx < len(row) else None
        main_system = row[main_system_idx] if main_system_idx < len(row) else None

        subsystem = _cell_to_text(subsystem)
        main_system = _cell_to_text(main_system)

        extra: Dict[str, Any] = {}
        for col_index, header_key in index_to_header.items():
            if col_index in core_indices:
                continue
            cell_value = row[col_index] if col_index < len(row) else None
            extra[header_key] = _cell_to_text(cell_value)

        results.append({
            "subsystem": subsystem,
            "main_system": main_system,
            "extra": extra,
            "errors": [],
        })
    return _validate_mappings(results)


def _reload_system_identification_cache() -> None:
    try:
        from backend.agent.system_identification_agent import get_system_identification_agent

        system_identification_agent = get_system_identification_agent()
        system_identification_agent.system_list = system_identification_agent._load_system_list()
        system_identification_agent.subsystem_mapping = system_identification_agent._load_subsystem_mapping()
    except Exception:
        logger.warning("重载系统识别缓存失败", exc_info=True)


def _reload_knowledge_service_system_cache() -> None:
    try:
        from backend.service.knowledge_service import get_knowledge_service

        knowledge_service = get_knowledge_service()
        if hasattr(knowledge_service, "_system_list"):
            knowledge_service._system_list = None
    except Exception:
        logger.warning("重载知识库系统清单缓存失败", exc_info=True)


def _reload_related_caches() -> None:
    _reload_system_identification_cache()
    _reload_knowledge_service_system_cache()


@router.get("/template", dependencies=[Depends(require_system_list_admin)])
async def download_template(request: Request):
    if os.path.exists(TEMPLATE_PATH):
        try:
            from openpyxl import load_workbook

            with open(TEMPLATE_PATH, "rb") as template_file:
                wb = load_workbook(BytesIO(template_file.read()))

            main_ws = wb["应用系统清单"] if "应用系统清单" in wb.sheetnames else wb.active
            header_values = [
                _normalize_header(cell)
                for cell in next(main_ws.iter_rows(min_row=1, max_row=1, values_only=True), [])
            ]
            need_owner_id = "owner_id" not in header_values
            need_owner_username = "owner_username" not in header_values
            if need_owner_id:
                main_ws.cell(row=1, column=len(header_values) + 1, value="owner_id")
                header_values.append("owner_id")
            if need_owner_username:
                main_ws.cell(row=1, column=len(header_values) + 1, value="owner_username")

            output = BytesIO()
            wb.save(output)
            output.seek(0)
            filename = os.path.basename(TEMPLATE_PATH)
            headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
            return StreamingResponse(
                output,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers=headers,
            )
        except Exception:
            logger.warning("读取模板文件失败，使用兜底模板", exc_info=True)

    # 兜底：当容器未包含 docs 模板文件时，生成一个最小可用模板（仅用于批量导入铺底数据）。
    try:
        from openpyxl import Workbook
    except Exception as exc:
        api_error = ApiError(
            error_code="SYSLIST_001",
            message="系统清单文件不合法",
            status_code=500,
            details={"reason": "缺少Excel解析依赖 openpyxl"},
        )
        return build_error_response(
            request=request,
            status_code=api_error.status_code,
            error_code=api_error.error_code,
            message=api_error.message,
            details=api_error.details,
        )

    wb = Workbook()
    ws_main = wb.active
    ws_main.title = "应用系统清单"
    ws_main.append(["系统名称", "英文简称", "状态", "owner_id", "owner_username"])
    ws_main.append(["示例：HOP", "HOP", "运行中", "user_demo_owner", "pm_demo"])

    ws_sub = wb.create_sheet("应用子系统清单")
    ws_sub.append(["编号", "英文简称", "系统名称", "所属系统"])
    ws_sub.append([1, "KFC", "示例：开放存", "HOP"])

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    filename = "系统清单模板.xlsx"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@router.post("/batch-import", dependencies=[Depends(require_system_list_admin)])
async def batch_import_preview(request: Request, file: UploadFile = File(...)):
    try:
        content = await file.read()
        if not content:
            raise ApiError(
                error_code="SYSLIST_001",
                message="系统清单文件不合法",
                status_code=400,
                details={"reason": "文件内容为空"},
            )

        wb = _load_workbook(content)
        main_ws, subsystem_ws = _detect_sheets(wb)

        systems = _parse_systems_sheet(main_ws)
        mappings = _parse_subsystem_sheet(subsystem_ws)

        return {
            "code": 200,
            "data": {
                "systems": systems,
                "mappings": mappings,
                "summary": {
                    "systems_total": len(systems),
                    "systems_error": sum(1 for item in systems if item.get("errors")),
                    "mappings_total": len(mappings),
                    "mappings_error": sum(1 for item in mappings if item.get("errors")),
                },
            },
        }
    except Exception as exc:
        api_error = _to_api_error(exc, default_error_code="SYSLIST_001")
        return build_error_response(
            request=request,
            status_code=api_error.status_code,
            error_code=api_error.error_code,
            message=api_error.message,
            details=api_error.details,
        )


def _upsert_systems(current_systems: List[Dict[str, Any]], incoming_systems: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = [dict(item) for item in current_systems]
    index_by_id: Dict[str, int] = {}
    index_by_name: Dict[str, int] = {}

    for idx, item in enumerate(merged):
        sid = str(item.get("id") or "").strip()
        sname = str(item.get("name") or "").strip()
        if sid:
            index_by_id[sid] = idx
        if sname:
            index_by_name[sname] = idx

    for item in incoming_systems:
        sid = str(item.get("id") or "").strip()
        sname = str(item.get("name") or "").strip()
        target_idx = None
        if sid and sid in index_by_id:
            target_idx = index_by_id[sid]
        elif sname and sname in index_by_name:
            target_idx = index_by_name[sname]

        if target_idx is None:
            merged.append(item)
            idx = len(merged) - 1
            if sid:
                index_by_id[sid] = idx
            if sname:
                index_by_name[sname] = idx
            continue

        merged[target_idx] = item
        if sid:
            index_by_id[sid] = target_idx
        if sname:
            index_by_name[sname] = target_idx

    return merged


def _upsert_mappings(current_mappings: List[Dict[str, Any]], incoming_mappings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = [dict(item) for item in current_mappings]
    index_by_id: Dict[str, int] = {}
    index_by_key: Dict[str, int] = {}

    for idx, item in enumerate(merged):
        mapping_id = str(item.get("id") or "").strip()
        subsystem = str(item.get("subsystem") or "").strip()
        main_system = str(item.get("main_system") or "").strip()
        if mapping_id:
            index_by_id[mapping_id] = idx
        if subsystem and main_system:
            index_by_key[f"{subsystem}|{main_system}"] = idx

    for item in incoming_mappings:
        mapping_id = str(item.get("id") or "").strip()
        subsystem = str(item.get("subsystem") or "").strip()
        main_system = str(item.get("main_system") or "").strip()
        key = f"{subsystem}|{main_system}" if subsystem and main_system else ""

        target_idx = None
        if mapping_id and mapping_id in index_by_id:
            target_idx = index_by_id[mapping_id]
        elif key and key in index_by_key:
            target_idx = index_by_key[key]

        if target_idx is None:
            merged.append(item)
            idx = len(merged) - 1
            if mapping_id:
                index_by_id[mapping_id] = idx
            if key:
                index_by_key[key] = idx
            continue

        merged[target_idx] = item
        if mapping_id:
            index_by_id[mapping_id] = target_idx
        if key:
            index_by_key[key] = target_idx

    return merged


@router.post("/batch-import/confirm", dependencies=[Depends(require_system_list_admin)])
async def batch_import_confirm(request: Request, payload: SystemListImportConfirmRequest):
    mode = (payload.mode or "replace").strip().lower()
    if mode not in {"replace", "upsert"}:
        return build_error_response(
            request=request,
            status_code=400,
            error_code="SYSLIST_003",
            message="导入模式不支持",
            details={"mode": mode, "supported_modes": ["replace", "upsert"]},
        )

    def _normalize_value(value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    systems = []
    for item in payload.systems or []:
        extra = item.get("extra")
        extra = _normalize_system_extra(extra)
        systems.append({
            "id": item.get("id") or uuid.uuid4().hex,
            "name": _normalize_value(item.get("name")),
            "abbreviation": _normalize_value(item.get("abbreviation")),
            "status": _normalize_value(item.get("status")),
            "extra": extra,
        })

    mappings = []
    for item in payload.mappings or []:
        extra = item.get("extra")
        if not isinstance(extra, dict):
            extra = {}
        mappings.append({
            "id": item.get("id") or uuid.uuid4().hex,
            "subsystem": _normalize_value(item.get("subsystem")),
            "main_system": _normalize_value(item.get("main_system")),
            "extra": extra,
        })

    try:
        if mode == "replace":
            final_systems = systems
            final_mappings = mappings
        else:
            current_systems = system_routes._read_systems()
            current_mappings = subsystem_routes._read_subsystem_mappings()
            final_systems = _upsert_systems(current_systems, systems)
            final_mappings = _upsert_mappings(current_mappings, mappings)

        system_routes._write_systems(final_systems)
        subsystem_routes._write_subsystem_mappings(final_mappings)

        _reload_related_caches()
        return {"code": 200, "message": "success"}
    except Exception as exc:
        api_error = _to_api_error(exc, default_error_code="SYSLIST_003")
        return build_error_response(
            request=request,
            status_code=api_error.status_code,
            error_code=api_error.error_code,
            message=api_error.message,
            details=api_error.details,
        )
