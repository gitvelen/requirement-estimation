"""
主系统管理API
提供标准主系统配置的CRUD接口
"""
import os
import logging
import csv
import json
import uuid
from typing import Any, List, Dict, Optional, Tuple
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from backend.api.auth import require_admin_api_key

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
CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "system_list.csv")

SYSTEM_HEADER_KEYS = {
    "ID", "id",
    "系统名称", "name",
    "英文简称", "系统简称", "abbreviation", "abbr",
    "系统状态", "状态", "status",
    "扩展字段", "extra", "extra_json",
}


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
