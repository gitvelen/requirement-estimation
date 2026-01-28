"""
子系统管理API
提供子系统和主系统对应关系的CRUD接口
"""
import os
import logging
import csv
from typing import List, Dict
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from backend.api.auth import require_admin_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/subsystem", tags=["子系统管理"])

# 数据模型
class SubsystemMapping(BaseModel):
    """子系统映射模型"""
    subsystem: str
    main_system: str


class SubsystemListResponse(BaseModel):
    """子系统列表响应"""
    total: int
    items: List[SubsystemMapping]


# CSV文件路径
CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "backend", "subsystem_list.csv")


def _read_subsystem_mappings() -> Dict[str, str]:
    """读取子系统映射"""
    mappings = {}
    if os.path.exists(CSV_PATH):
        try:
            with open(CSV_PATH, 'r', encoding='utf-8', newline='') as f:
                reader = csv.reader(f)
                next(reader, None)  # 跳过表头
                for row in reader:
                    if len(row) >= 2:
                        subsystem = row[0].strip()
                        main_system = row[1].strip()
                        if subsystem and main_system:
                            mappings[subsystem] = main_system
        except Exception as e:
            logger.error(f"读取子系统映射失败: {e}")
    else:
        # 文件不存在时创建空文件
        try:
            os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
            with open(CSV_PATH, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["子系统名称", "所属主系统"])
            logger.info(f"创建子系统映射文件: {CSV_PATH}")
        except Exception as e:
            logger.error(f"创建子系统映射文件失败: {e}")
    return mappings


def _write_subsystem_mappings(mappings: Dict[str, str]):
    """写入子系统映射"""
    try:
        with open(CSV_PATH, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["子系统名称", "所属主系统"])
            for subsystem, main_system in mappings.items():
                writer.writerow([subsystem, main_system])
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
            {"subsystem": k, "mainSystem": v}
            for k, v in mappings.items()
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

        if mapping.subsystem in mappings:
            raise HTTPException(status_code=400, detail=f"子系统 '{mapping.subsystem}' 已存在")

        mappings[mapping.subsystem] = mapping.main_system
        _write_subsystem_mappings(mappings)

        logger.info(f"添加子系统映射: {mapping.subsystem} -> {mapping.main_system}")
        return {
            "code": 200,
            "message": "添加成功",
            "data": {
                "subsystem": mapping.subsystem,
                "main_system": mapping.main_system
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
        subsystem: 子系统名称
        mapping: 新的映射信息

    Returns:
        dict: {code, message, data}
    """
    try:
        mappings = _read_subsystem_mappings()

        if subsystem not in mappings:
            raise HTTPException(status_code=404, detail=f"子系统 '{subsystem}' 不存在")

        mappings[subsystem] = mapping.main_system
        _write_subsystem_mappings(mappings)

        logger.info(f"更新子系统映射: {subsystem} -> {mapping.main_system}")
        return {
            "code": 200,
            "message": "更新成功",
            "data": {
                "subsystem": subsystem,
                "main_system": mapping.main_system
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
        subsystem: 子系统名称

    Returns:
        dict: {code, message, data}
    """
    try:
        mappings = _read_subsystem_mappings()

        if subsystem not in mappings:
            raise HTTPException(status_code=404, detail=f"子系统 '{subsystem}' 不存在")

        del mappings[subsystem]
        _write_subsystem_mappings(mappings)

        logger.info(f"删除子系统映射: {subsystem}")
        return {
            "code": 200,
            "message": "删除成功",
            "data": {
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
