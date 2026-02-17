"""
子系统管理API
提供子系统和主系统对应关系的CRUD接口
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
from backend.config.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/subsystem", tags=["子系统管理"])

# 数据模型
class SubsystemMapping(BaseModel):
    """子系统映射模型"""
    subsystem: str
    main_system: str
    extra: Optional[Dict[str, Any]] = None  # 额外字段（来自模板的其他列）


class SubsystemListResponse(BaseModel):
    """子系统列表响应"""
    total: int
    items: List[SubsystemMapping]


# CSV文件路径
CSV_PATH = os.path.join(settings.REPORT_DIR, "subsystem_list.csv")

SUBSYSTEM_HEADER_KEYS = {
    "ID", "id",
    "子系统名称", "系统名称", "subsystem",
    "所属主系统", "所属系统", "main_system", "mainSystem",
    "扩展字段", "extra", "extra_json",
}


def _generate_mapping_id() -> str:
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


def _resolve_subsystem_columns(
    header_map: Dict[str, int],
) -> Optional[Tuple[Optional[int], Optional[int], Optional[int], Optional[int]]]:
    if not header_map:
        return None

    if not any(key in header_map for key in SUBSYSTEM_HEADER_KEYS):
        return None

    id_idx = header_map.get("ID")
    if id_idx is None:
        id_idx = header_map.get("id")

    subsystem_idx = header_map.get("子系统名称")
    if subsystem_idx is None:
        subsystem_idx = header_map.get("系统名称")
    if subsystem_idx is None:
        subsystem_idx = header_map.get("subsystem")

    main_idx = header_map.get("所属主系统")
    if main_idx is None:
        main_idx = header_map.get("所属系统")
    if main_idx is None:
        main_idx = header_map.get("main_system")
    if main_idx is None:
        main_idx = header_map.get("mainSystem")

    extra_idx = header_map.get("扩展字段")
    if extra_idx is None:
        extra_idx = header_map.get("extra")
    if extra_idx is None:
        extra_idx = header_map.get("extra_json")

    return id_idx, subsystem_idx, main_idx, extra_idx


def _get_row_value(row: List[str], idx: Optional[int]) -> str:
    if idx is None or idx >= len(row):
        return ""
    value = row[idx]
    if value is None:
        return ""
    return str(value).strip()


def _read_subsystem_mappings() -> List[Dict[str, str]]:
    """读取子系统映射"""
    mappings: List[Dict[str, str]] = []
    if os.path.exists(CSV_PATH):
        try:
            with open(CSV_PATH, 'r', encoding='utf-8', newline='') as f:
                reader = list(csv.reader(f))
                if not reader:
                    return mappings

                header_map = _build_header_map(reader[0])
                column_indices = _resolve_subsystem_columns(header_map)

                needs_write = False
                if column_indices is None:
                    data_rows = reader
                    id_idx = None
                    subsystem_idx = 0
                    main_idx = 1
                    extra_idx = None
                    needs_write = True
                else:
                    data_rows = reader[1:]
                    id_idx, subsystem_idx, main_idx, extra_idx = column_indices
                    if id_idx is None or extra_idx is None:
                        needs_write = True

                seen_ids = set()
                for row in data_rows:
                    subsystem = _get_row_value(row, subsystem_idx)
                    main_system = _get_row_value(row, main_idx)
                    mapping_id = _get_row_value(row, id_idx)
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
                            logger.warning("解析子系统 extra 字段失败，已忽略", exc_info=True)

                    if not (mapping_id or subsystem or main_system or extra_raw):
                        continue

                    if not mapping_id or mapping_id in seen_ids:
                        mapping_id = _generate_mapping_id()
                        needs_write = True
                    seen_ids.add(mapping_id)

                    mappings.append({
                        "id": mapping_id,
                        "subsystem": subsystem,
                        "main_system": main_system,
                        "extra": extra,
                    })

                if needs_write and mappings:
                    try:
                        _write_subsystem_mappings(mappings)
                    except Exception:
                        logger.warning("写回子系统映射ID失败", exc_info=True)
        except Exception as e:
            logger.error(f"读取子系统映射失败: {e}")
    else:
        # 文件不存在时创建空文件
        try:
            os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
            with open(CSV_PATH, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "子系统名称", "所属主系统", "扩展字段"])
            logger.info(f"创建子系统映射文件: {CSV_PATH}")
        except Exception as e:
            logger.error(f"创建子系统映射文件失败: {e}")
    return mappings


def _write_subsystem_mappings(mappings: List[Dict[str, str]]):
    """写入子系统映射"""
    try:
        with open(CSV_PATH, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "子系统名称", "所属主系统", "扩展字段"])
            for mapping in mappings:
                mapping_id = mapping.get("id") or _generate_mapping_id()
                extra = mapping.get("extra") or {}
                if not isinstance(extra, dict):
                    extra = {"_value": extra}
                writer.writerow([
                    mapping_id,
                    mapping.get("subsystem", ""),
                    mapping.get("main_system", ""),
                    json.dumps(extra, ensure_ascii=False) if extra else "",
                ])
        logger.info(f"保存了{len(mappings)}个子系统映射")
    except Exception as e:
        logger.error(f"写入子系统映射失败: {e}")
        raise


@router.get("/mappings")
async def get_subsystem_mappings():
    """
    获取所有子系统映射关系

    Returns:
        dict: {code, message, data: {total, items}}
    """
    try:
        mappings = _read_subsystem_mappings()
        items = [
            {
                "id": item.get("id"),
                "subsystem": item.get("subsystem"),
                "mainSystem": item.get("main_system"),
                "extra": item.get("extra") or {},
            }
            for item in mappings
        ]
        return {
            "code": 200,
            "message": "获取成功",
            "data": {
                "total": len(items),
                "items": items
            }
        }
    except Exception as e:
        logger.error(f"获取子系统映射失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取子系统映射失败: {str(e)}")


@router.post("/mappings")
async def create_subsystem_mapping(mapping: SubsystemMapping, _auth: None = Depends(require_admin_api_key)):
    """
    添加新的子系统映射关系

    Args:
        mapping: 子系统映射信息

    Returns:
        dict: {code, message, data}
    """
    try:
        mappings = _read_subsystem_mappings()

        mapping_id = _generate_mapping_id()
        extra = mapping.extra or {}
        mappings.append({
            "id": mapping_id,
            "subsystem": mapping.subsystem,
            "main_system": mapping.main_system,
            "extra": extra,
        })
        _write_subsystem_mappings(mappings)

        logger.info(f"添加子系统映射: {mapping.subsystem} -> {mapping.main_system}")
        return {
            "code": 200,
            "message": "添加成功",
            "data": {
                "id": mapping_id,
                "subsystem": mapping.subsystem,
                "main_system": mapping.main_system,
                "extra": extra,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"添加子系统映射失败: {e}")
        raise HTTPException(status_code=500, detail=f"添加失败: {str(e)}")


@router.put("/mappings/{subsystem}")
async def update_subsystem_mapping(subsystem: str, mapping: SubsystemMapping, _auth: None = Depends(require_admin_api_key)):
    """
    更新子系统映射关系

    Args:
        subsystem: 子系统ID或名称
        mapping: 新的映射信息

    Returns:
        dict: {code, message, data}
    """
    try:
        mappings = _read_subsystem_mappings()

        found = False
        updated_id = None
        stored_extra: Dict[str, Any] = {}
        for idx, item in enumerate(mappings):
            if item.get("id") == subsystem:
                extra = mapping.extra if mapping.extra is not None else (item.get("extra") or {})
                mappings[idx] = {
                    "id": item.get("id"),
                    "subsystem": mapping.subsystem,
                    "main_system": mapping.main_system,
                    "extra": extra,
                }
                found = True
                updated_id = item.get("id")
                stored_extra = extra
                break

        if not found:
            for idx, item in enumerate(mappings):
                if item.get("subsystem") == subsystem:
                    extra = mapping.extra if mapping.extra is not None else (item.get("extra") or {})
                    mappings[idx] = {
                        "id": item.get("id"),
                        "subsystem": mapping.subsystem,
                        "main_system": mapping.main_system,
                        "extra": extra,
                    }
                    found = True
                    updated_id = item.get("id")
                    stored_extra = extra
                    break

        if not found:
            raise HTTPException(status_code=404, detail=f"子系统 '{subsystem}' 不存在")

        _write_subsystem_mappings(mappings)

        logger.info(f"更新子系统映射: {subsystem} -> {mapping.main_system}")
        return {
            "code": 200,
            "message": "更新成功",
            "data": {
                "id": updated_id,
                "subsystem": mapping.subsystem,
                "main_system": mapping.main_system,
                "extra": stored_extra,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新子系统映射失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@router.delete("/mappings/{subsystem}")
async def delete_subsystem_mapping(subsystem: str, _auth: None = Depends(require_admin_api_key)):
    """
    删除子系统映射关系

    Args:
        subsystem: 子系统ID或名称

    Returns:
        dict: {code, message, data}
    """
    try:
        mappings = _read_subsystem_mappings()

        found = False
        for idx, item in enumerate(mappings):
            if item.get("id") == subsystem:
                del mappings[idx]
                found = True
                break

        if not found:
            for idx, item in enumerate(mappings):
                if item.get("subsystem") == subsystem:
                    del mappings[idx]
                    found = True
                    break

        if not found:
            raise HTTPException(status_code=404, detail=f"子系统 '{subsystem}' 不存在")

        _write_subsystem_mappings(mappings)

        logger.info(f"删除子系统映射: {subsystem}")
        return {
            "code": 200,
            "message": "删除成功",
            "data": {
                "id": subsystem,
                "subsystem": subsystem
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除子系统映射失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.post("/reload")
async def reload_subsystem_mappings(_auth: None = Depends(require_admin_api_key)):
    """
    重新加载子系统映射（热加载）

    Returns:
        dict: {code, message, data}
    """
    try:
        from backend.agent.system_identification_agent import system_identification_agent

        # 重新加载映射
        new_mappings = system_identification_agent._load_subsystem_mapping()
        system_identification_agent.subsystem_mapping = new_mappings

        count = len(new_mappings)
        logger.info(f"重新加载了{count}个子系统映射")
        return {
            "code": 200,
            "message": "重新加载成功",
            "data": {
                "count": count
            }
        }
    except Exception as e:
        logger.error(f"重新加载子系统映射失败: {e}")
        raise HTTPException(status_code=500, detail=f"重新加载失败: {str(e)}")
