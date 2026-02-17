"""
主系统管理API
提供标准主系统配置的CRUD接口
"""
import os
import logging
import csv
import json
import uuid
import re
from typing import Any, List, Dict, Optional, Tuple
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from backend.api.auth import require_admin_api_key
from backend.config.config import settings
from backend.service import user_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/system", tags=["主系统管理"])

# 数据模型
class MainSystem(BaseModel):
    """主系统模型"""
    name: str  # 系统名称
    abbreviation: str  # 系统简称
    status: str = "运行中"  # 系统状态
    extra: Optional[Dict[str, Any]] = None  # 额外字段（来自模板的其他列）


class SystemListResponse(BaseModel):
    """系统列表响应"""
    total: int
    items: List[MainSystem]


# CSV文件路径
CSV_PATH = os.path.join(settings.REPORT_DIR, "system_list.csv")

SYSTEM_HEADER_KEYS = {
    "ID", "id",
    "系统名称", "name",
    "英文简称", "系统简称", "abbreviation", "abbr",
    "系统状态", "状态", "status",
    "扩展字段", "extra", "extra_json",
}

OWNER_EXTRA_FIELD_ALIASES: Dict[str, List[str]] = {
    "owner_id": [
        "owner_id",
        "ownerId",
        "系统负责人ID",
        "负责人ID",
        "系统主责ID",
        "主责ID",
    ],
    "owner_username": [
        "owner_username",
        "ownerUsername",
        "系统负责人账号",
        "负责人账号",
        "系统负责人用户名",
        "负责人用户名",
    ],
    "owner_name": [
        "owner_name",
        "ownerName",
        "系统负责人姓名",
        "负责人姓名",
        "系统负责人名称",
        "负责人名称",
        "系统负责人",
        "负责人",
    ],
    "backup_owner_ids": [
        "backup_owner_ids",
        "backupOwnerIds",
        "backupOwnerIDs",
        "B角ID",
        "B角IDs",
        "代理负责人ID",
        "代理负责人IDs",
        "B角用户ID",
        "代理负责人用户ID",
        "备份负责人ID",
        "备份负责人IDs",
    ],
    "backup_owner_usernames": [
        "backup_owner_usernames",
        "backupOwnerUsernames",
        "B角账号",
        "B角用户名",
        "代理负责人账号",
        "代理负责人用户名",
        "备份负责人账号",
        "备份负责人用户名",
    ],
}

_OWNER_EXTRA_ALIAS_INDEX: Dict[str, str] = {}
for canonical_key, aliases in OWNER_EXTRA_FIELD_ALIASES.items():
    for alias in aliases:
        normalized_alias = re.sub(r"[\s_\-]", "", str(alias or "")).lower()
        if normalized_alias:
            _OWNER_EXTRA_ALIAS_INDEX[normalized_alias] = canonical_key


def resolve_owner_extra_key(raw_key: Optional[str]) -> Optional[str]:
    normalized_key = re.sub(r"[\s_\-]", "", str(raw_key or "")).lower()
    if not normalized_key:
        return None
    return _OWNER_EXTRA_ALIAS_INDEX.get(normalized_key)


def normalize_system_owner_extra_fields(extra: Any) -> Tuple[Dict[str, Any], bool]:
    if not isinstance(extra, dict):
        return {}, False

    normalized_extra: Dict[str, Any] = dict(extra)
    changed = False

    def _normalize_str_list(value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, list):
            parts = value
        else:
            parts = [item.strip() for item in str(value).replace("，", ",").split(",")]
        result: List[str] = []
        for item in parts:
            text = str(item or "").strip()
            if not text:
                continue
            if text not in result:
                result.append(text)
        return result

    for key, value in list(extra.items()):
        canonical_key = resolve_owner_extra_key(key)
        if not canonical_key:
            continue

        if canonical_key in {"backup_owner_ids", "backup_owner_usernames"}:
            list_value = _normalize_str_list(value)
            existing = normalized_extra.get(canonical_key)
            existing_list = _normalize_str_list(existing)
            if existing_list != list_value:
                normalized_extra[canonical_key] = list_value
                changed = True

            if key != canonical_key and key in normalized_extra:
                del normalized_extra[key]
                changed = True
            continue

        text_value = "" if value is None else str(value).strip()
        existing_value = "" if normalized_extra.get(canonical_key) is None else str(normalized_extra.get(canonical_key)).strip()

        if not existing_value and (text_value or canonical_key not in normalized_extra):
            normalized_extra[canonical_key] = text_value
            if key != canonical_key:
                changed = True

        if key != canonical_key and key in normalized_extra:
            del normalized_extra[key]
            changed = True

    return normalized_extra, changed


def _split_owner_candidates(value: Any) -> List[str]:
    if value is None:
        return []
    text = str(value).strip()
    if not text:
        return []
    normalized = re.sub(r"[，、;/；|]+", ",", text.replace("/", ","))
    parts = [item.strip() for item in normalized.split(",")]
    result: List[str] = []
    for item in parts:
        if not item:
            continue
        if item not in result:
            result.append(item)
    return result


def _find_user_by_owner_identity(users: List[Dict[str, Any]], candidate: str) -> Tuple[Optional[Dict[str, Any]], str]:
    text = str(candidate or "").strip()
    if not text:
        return None, ""

    by_username = user_service.find_user_by_username(users, text)
    if by_username:
        return by_username, "username"

    for user in users:
        display_name = str(user.get("display_name") or "").strip()
        if display_name and display_name == text:
            return user, "display_name"

    return None, ""


def _find_system(system_id: Optional[str] = None, system_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
    sid = str(system_id or "").strip()
    sname = str(system_name or "").strip()
    systems = _read_systems()

    if sid:
        for system in systems:
            if str(system.get("id") or "").strip() == sid:
                return system

    if sname:
        for system in systems:
            if str(system.get("name") or "").strip() == sname:
                return system

    return None


def resolve_system_owner(system_id: Optional[str] = None, system_name: Optional[str] = None) -> Dict[str, Any]:
    system = _find_system(system_id=system_id, system_name=system_name)
    if not system:
        return {
            "system_found": False,
            "is_configured": False,
            "mapping_status": "system_not_found",
            "system_id": str(system_id or "").strip(),
            "system_name": str(system_name or "").strip(),
            "owner_id": "",
            "owner_username": "",
            "owner_name": "",
            "resolved_owner_id": "",
            "resolved_by": "",
            "backup_owner_ids": [],
            "backup_owner_usernames": [],
            "resolved_backup_owner_ids": [],
        }

    extra, _ = normalize_system_owner_extra_fields(system.get("extra") or {})

    owner_id = str(extra.get("owner_id") or "").strip()
    owner_username = str(extra.get("owner_username") or "").strip()
    owner_name = str(extra.get("owner_name") or "").strip()
    backup_owner_ids = extra.get("backup_owner_ids")
    backup_owner_usernames = extra.get("backup_owner_usernames")

    def _as_str_list(value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, list):
            parts = value
        else:
            parts = _split_owner_candidates(value)
        result: List[str] = []
        for item in parts:
            text = str(item or "").strip()
            if not text:
                continue
            if text not in result:
                result.append(text)
        return result

    normalized_owner_usernames = _split_owner_candidates(owner_username)
    normalized_owner_names = _split_owner_candidates(owner_name)
    normalized_backup_ids = _as_str_list(backup_owner_ids)
    normalized_backup_usernames = _as_str_list(backup_owner_usernames)

    if normalized_owner_usernames:
        owner_username = normalized_owner_usernames[0]
        for candidate in normalized_owner_usernames[1:]:
            if candidate not in normalized_backup_usernames:
                normalized_backup_usernames.append(candidate)

    if normalized_owner_names:
        owner_name = normalized_owner_names[0]

    resolved_owner_id = owner_id
    resolved_by = "owner_id" if owner_id else ""
    mapping_status = "ok"

    resolved_backup_owner_ids: List[str] = []
    for item in normalized_backup_ids:
        if item not in resolved_backup_owner_ids:
            resolved_backup_owner_ids.append(item)

    users = user_service.list_users() if not owner_id else None

    if not owner_id and normalized_owner_usernames:
        for candidate in normalized_owner_usernames:
            owner_user, matched_by = _find_user_by_owner_identity(users or [], candidate)
            if not owner_user:
                continue
            resolved_id = str(owner_user.get("id") or "").strip()
            if not resolved_id:
                continue
            if not resolved_owner_id:
                resolved_owner_id = resolved_id
                resolved_by = "owner_username" if matched_by == "username" else "owner_display_name"
                if not owner_name:
                    owner_name = str(owner_user.get("display_name") or owner_user.get("username") or "").strip()
            elif resolved_id not in resolved_backup_owner_ids:
                resolved_backup_owner_ids.append(resolved_id)

        if not resolved_owner_id:
            mapping_status = "owner_username_unresolved"
    elif not owner_id and normalized_owner_names:
        for candidate in normalized_owner_names:
            owner_user, matched_by = _find_user_by_owner_identity(users or [], candidate)
            if not owner_user:
                continue
            resolved_id = str(owner_user.get("id") or "").strip()
            if not resolved_id:
                continue
            if not resolved_owner_id:
                resolved_owner_id = resolved_id
                resolved_by = "owner_name" if matched_by == "display_name" else "owner_username"
                if not owner_username:
                    owner_username = candidate
            elif resolved_id not in resolved_backup_owner_ids:
                resolved_backup_owner_ids.append(resolved_id)

        if not resolved_owner_id:
            mapping_status = "owner_username_unresolved"

    if normalized_backup_usernames:
        if users is None:
            users = user_service.list_users()
        for username in normalized_backup_usernames:
            backup_user, _ = _find_user_by_owner_identity(users, username)
            if backup_user:
                backup_id = str(backup_user.get("id") or "").strip()
                if backup_id and backup_id not in resolved_backup_owner_ids:
                    resolved_backup_owner_ids.append(backup_id)

    if not owner_id and not owner_username and not owner_name:
        mapping_status = "owner_not_configured"

    if not resolved_owner_id and mapping_status == "ok":
        mapping_status = "owner_not_configured"

    return {
        "system_found": True,
        "is_configured": bool(resolved_owner_id),
        "mapping_status": mapping_status,
        "system_id": str(system.get("id") or "").strip(),
        "system_name": str(system.get("name") or "").strip(),
        "owner_id": owner_id,
        "owner_username": owner_username,
        "owner_name": owner_name,
        "resolved_owner_id": resolved_owner_id,
        "resolved_by": resolved_by,
        "backup_owner_ids": normalized_backup_ids,
        "backup_owner_usernames": normalized_backup_usernames,
        "resolved_backup_owner_ids": resolved_backup_owner_ids,
    }


def resolve_system_ownership(
    current_user: Optional[Dict[str, Any]],
    *,
    system_id: Optional[str] = None,
    system_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Resolve ownership/backup ownership for resource-level permission checks.

    Returns payload:
      - allowed_draft_write: bool (owner or backup)
      - allowed_publish: bool (owner only)
      - is_owner: bool
      - is_backup: bool
      - owner_info: resolve_system_owner(...)
    """
    owner_info = resolve_system_owner(system_id=system_id, system_name=system_name)
    current_user_id = str((current_user or {}).get("id") or "").strip()
    resolved_owner_id = str(owner_info.get("resolved_owner_id") or "").strip()
    resolved_backup_owner_ids = owner_info.get("resolved_backup_owner_ids") or []
    is_owner = bool(current_user_id and resolved_owner_id and current_user_id == resolved_owner_id)
    is_backup = bool(current_user_id and current_user_id in {str(item).strip() for item in resolved_backup_owner_ids if str(item).strip()})
    allowed_draft_write = bool(is_owner or is_backup)
    allowed_publish = bool(is_owner)
    return {
        "allowed_draft_write": allowed_draft_write,
        "allowed_publish": allowed_publish,
        "is_owner": is_owner,
        "is_backup": is_backup,
        "owner_info": owner_info,
    }


def is_system_owner(current_user: Optional[Dict[str, Any]], system_id: Optional[str] = None, system_name: Optional[str] = None) -> Tuple[bool, Dict[str, Any]]:
    owner_info = resolve_system_owner(system_id=system_id, system_name=system_name)
    current_user_id = str((current_user or {}).get("id") or "").strip()
    is_owner = bool(
        current_user_id
        and owner_info.get("system_found")
        and owner_info.get("is_configured")
        and str(owner_info.get("resolved_owner_id") or "").strip() == current_user_id
    )
    return is_owner, owner_info


def _generate_system_id() -> str:
    return uuid.uuid4().hex


def _normalize_header(value: Optional[str]) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _build_header_map(header: List[str]) -> Dict[str, int]:
    header_map: Dict[str, int] = {}
    for idx, cell in enumerate(header):
        key = _normalize_header(cell)
        if key and key not in header_map:
            header_map[key] = idx
    return header_map


def _resolve_system_columns(
    header_map: Dict[str, int],
) -> Optional[Tuple[Optional[int], Optional[int], Optional[int], Optional[int], Optional[int]]]:
    if not header_map:
        return None

    if not any(key in header_map for key in SYSTEM_HEADER_KEYS):
        return None

    id_idx = header_map.get("ID")
    if id_idx is None:
        id_idx = header_map.get("id")

    name_idx = header_map.get("系统名称")
    if name_idx is None:
        name_idx = header_map.get("name")

    abbr_idx = header_map.get("英文简称")
    if abbr_idx is None:
        abbr_idx = header_map.get("系统简称")
    if abbr_idx is None:
        abbr_idx = header_map.get("abbreviation")
    if abbr_idx is None:
        abbr_idx = header_map.get("abbr")

    status_idx = header_map.get("系统状态")
    if status_idx is None:
        status_idx = header_map.get("状态")
    if status_idx is None:
        status_idx = header_map.get("status")

    extra_idx = header_map.get("扩展字段")
    if extra_idx is None:
        extra_idx = header_map.get("extra")
    if extra_idx is None:
        extra_idx = header_map.get("extra_json")

    return id_idx, name_idx, abbr_idx, status_idx, extra_idx


def _get_row_value(row: List[str], idx: Optional[int]) -> str:
    if idx is None or idx >= len(row):
        return ""
    value = row[idx]
    if value is None:
        return ""
    return str(value).strip()


def _read_systems() -> List[Dict[str, str]]:
    """读取主系统列表"""
    systems = []
    if os.path.exists(CSV_PATH):
        try:
            with open(CSV_PATH, 'r', encoding='utf-8', newline='') as f:
                reader = list(csv.reader(f))
                if not reader:
                    return systems

                header_map = _build_header_map(reader[0])
                column_indices = _resolve_system_columns(header_map)

                needs_write = False
                if column_indices is None:
                    data_rows = reader
                    id_idx = None
                    name_idx = 0
                    abbr_idx = 1
                    status_idx = 2
                    extra_idx = None
                    needs_write = True
                else:
                    data_rows = reader[1:]
                    id_idx, name_idx, abbr_idx, status_idx, extra_idx = column_indices
                    if id_idx is None or extra_idx is None:
                        needs_write = True

                seen_ids = set()
                for row in data_rows:
                    name = _get_row_value(row, name_idx)
                    abbr = _get_row_value(row, abbr_idx)
                    status = _get_row_value(row, status_idx)
                    system_id = _get_row_value(row, id_idx)
                    extra_raw = _get_row_value(row, extra_idx)
                    extra: Dict[str, Any] = {}
                    if extra_raw:
                        try:
                            parsed = json.loads(extra_raw)
                            if isinstance(parsed, dict):
                                extra = parsed
                            else:
                                extra = {"_value": parsed}
                        except Exception:
                            logger.warning("解析系统 extra 字段失败，已忽略", exc_info=True)

                    extra, extra_changed = normalize_system_owner_extra_fields(extra)
                    if extra_changed:
                        needs_write = True

                    if not (system_id or name or abbr or status or extra_raw):
                        continue

                    if not system_id or system_id in seen_ids:
                        system_id = _generate_system_id()
                        needs_write = True
                    seen_ids.add(system_id)

                    systems.append({
                        "id": system_id,
                        "name": name,
                        "abbreviation": abbr,
                        "status": status,
                        "extra": extra,
                    })

                if needs_write and systems:
                    try:
                        _write_systems(systems)
                    except Exception:
                        logger.warning("写回系统清单ID失败", exc_info=True)
        except Exception as e:
            logger.error(f"读取主系统列表失败: {e}")
    else:
        # 文件不存在时创建空文件
        try:
            os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
            with open(CSV_PATH, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "系统名称", "英文简称", "系统状态"])
            logger.info(f"创建主系统列表文件: {CSV_PATH}")
        except Exception as e:
            logger.error(f"创建主系统列表文件失败: {e}")
    return systems


def _write_systems(systems: List[Dict[str, str]]):
    """写入主系统列表"""
    try:
        with open(CSV_PATH, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "系统名称", "英文简称", "系统状态", "扩展字段"])
            for system in systems:
                system_id = system.get("id") or _generate_system_id()
                extra = system.get("extra") or {}
                if not isinstance(extra, dict):
                    extra = {"_value": extra}
                writer.writerow([
                    system_id,
                    system.get('name', ''),
                    system.get('abbreviation', ''),
                    system.get('status', ''),
                    json.dumps(extra, ensure_ascii=False) if extra else "",
                ])
        logger.info(f"保存了{len(systems)}个主系统")
    except Exception as e:
        logger.error(f"写入主系统列表失败: {e}")
        raise


@router.get("/systems")
async def get_systems():
    """
    获取所有主系统

    Returns:
        dict: {code, message, data: {total, items}}
    """
    try:
        systems = _read_systems()
        return {
            "code": 200,
            "message": "获取成功",
            "data": {
                "total": len(systems),
                "systems": systems
            }
        }
    except Exception as e:
        logger.error(f"获取主系统列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取主系统列表失败: {str(e)}")


@router.post("/systems")
async def create_system(system: MainSystem, _auth: None = Depends(require_admin_api_key)):
    """
    添加新的主系统

    Args:
        system: 主系统信息

    Returns:
        dict: {code, message, data}
    """
    try:
        systems = _read_systems()

        system_id = _generate_system_id()
        extra = system.extra or {}
        systems.append({
            "id": system_id,
            "name": system.name,
            "abbreviation": system.abbreviation,
            "status": system.status,
            "extra": extra,
        })
        _write_systems(systems)

        logger.info(f"添加主系统: {system.name} ({system.abbreviation})")
        return {
            "code": 200,
            "message": "添加成功",
            "data": {
                "id": system_id,
                "name": system.name,
                "abbreviation": system.abbreviation,
                "status": system.status,
                "extra": extra,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"添加主系统失败: {e}")
        raise HTTPException(status_code=500, detail=f"添加失败: {str(e)}")


@router.put("/systems/{system_name}")
async def update_system(system_name: str, system: MainSystem, _auth: None = Depends(require_admin_api_key)):
    """
    更新主系统信息

    Args:
        system_name: 系统ID或名称
        system: 新的系统信息

    Returns:
        dict: {code, message, data}
    """
    try:
        systems = _read_systems()

        # 查找并更新（优先按ID，其次按名称）
        found = False
        updated_id = None
        stored_extra: Dict[str, Any] = {}
        for idx, s in enumerate(systems):
            if s.get("id") == system_name:
                extra = system.extra if system.extra is not None else (s.get("extra") or {})
                systems[idx] = {
                    "id": s.get("id"),
                    "name": system.name,
                    "abbreviation": system.abbreviation,
                    "status": system.status,
                    "extra": extra,
                }
                found = True
                updated_id = s.get("id")
                stored_extra = extra
                break

        if not found:
            for idx, s in enumerate(systems):
                if s.get("name") == system_name:
                    extra = system.extra if system.extra is not None else (s.get("extra") or {})
                    systems[idx] = {
                        "id": s.get("id"),
                        "name": system.name,
                        "abbreviation": system.abbreviation,
                        "status": system.status,
                        "extra": extra,
                    }
                    found = True
                    updated_id = s.get("id")
                    stored_extra = extra
                    break

        if not found:
            raise HTTPException(status_code=404, detail=f"系统 '{system_name}' 不存在")

        _write_systems(systems)

        logger.info(f"更新主系统: {system_name} -> {system.name}")
        return {
            "code": 200,
            "message": "更新成功",
            "data": {
                "id": updated_id,
                "name": system.name,
                "abbreviation": system.abbreviation,
                "status": system.status,
                "extra": stored_extra,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新主系统失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@router.delete("/systems/{system_name}")
async def delete_system(system_name: str, _auth: None = Depends(require_admin_api_key)):
    """
    删除主系统

    Args:
        system_name: 系统ID或名称

    Returns:
        dict: {code, message, data}
    """
    try:
        systems = _read_systems()

        # 查找并删除（优先按ID）
        found = False
        for idx, s in enumerate(systems):
            if s.get("id") == system_name:
                del systems[idx]
                found = True
                break

        if not found:
            for idx, s in enumerate(systems):
                if s.get("name") == system_name:
                    del systems[idx]
                    found = True
                    break

        if not found:
            raise HTTPException(status_code=404, detail=f"系统 '{system_name}' 不存在")

        _write_systems(systems)

        logger.info(f"删除主系统: {system_name}")
        return {
            "code": 200,
            "message": "删除成功",
            "data": {
                "id": system_name,
                "name": system_name
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除主系统失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.post("/reload")
async def reload_systems(_auth: None = Depends(require_admin_api_key)):
    """
    重新加载主系统列表（热加载）

    Returns:
        dict: {code, message, data}
    """
    try:
        from backend.agent.system_identification_agent import system_identification_agent

        # 重新加载系统列表
        new_systems = system_identification_agent._load_system_list()
        system_identification_agent.system_list = new_systems

        count = len(new_systems)
        logger.info(f"重新加载了{count}个主系统")
        return {
            "code": 200,
            "message": "重新加载成功",
            "data": {
                "count": count
            }
        }
    except Exception as e:
        logger.error(f"重新加载主系统列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"重新加载失败: {str(e)}")
