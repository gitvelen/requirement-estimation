"""
主系统管理API
提供标准主系统配置的CRUD接口
"""
import os
import logging
import csv
from typing import List, Dict
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


class SystemListResponse(BaseModel):
    """系统列表响应"""
    total: int
    items: List[MainSystem]


# CSV文件路径
CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "system_list.csv")


def _read_systems() -> List[Dict[str, str]]:
    """读取主系统列表"""
    systems = []
    if os.path.exists(CSV_PATH):
        try:
            with open(CSV_PATH, 'r', encoding='utf-8', newline='') as f:
                reader = csv.reader(f)
                next(reader, None)  # 跳过表头
                for row in reader:
                    if len(row) >= 3:
                        systems.append({
                            "name": row[0].strip(),
                            "abbreviation": row[1].strip(),
                            "status": row[2].strip()
                        })
                    elif len(row) >= 2:
                        systems.append({
                            "name": row[0].strip(),
                            "abbreviation": row[1].strip(),
                            "status": "运行中"
                        })
        except Exception as e:
            logger.error(f"读取主系统列表失败: {e}")
    else:
        # 文件不存在时创建空文件
        try:
            os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
            with open(CSV_PATH, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["系统名称", "英文简称", "系统状态"])
            logger.info(f"创建主系统列表文件: {CSV_PATH}")
        except Exception as e:
            logger.error(f"创建主系统列表文件失败: {e}")
    return systems


def _write_systems(systems: List[Dict[str, str]]):
    """写入主系统列表"""
    try:
        with open(CSV_PATH, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["系统名称", "英文简称", "系统状态"])
            for system in systems:
                writer.writerow([system['name'], system['abbreviation'], system['status']])
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

        # 检查是否已存在
        for s in systems:
            if s["name"] == system.name:
                raise HTTPException(status_code=400, detail=f"系统名称 '{system.name}' 已存在")
            if s["abbreviation"] == system.abbreviation:
                raise HTTPException(status_code=400, detail=f"系统简称 '{system.abbreviation}' 已存在")

        systems.append({
            "name": system.name,
            "abbreviation": system.abbreviation,
            "status": system.status
        })
        _write_systems(systems)

        logger.info(f"添加主系统: {system.name} ({system.abbreviation})")
        return {
            "code": 200,
            "message": "添加成功",
            "data": {
                "name": system.name,
                "abbreviation": system.abbreviation,
                "status": system.status
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
        system_name: 原系统名称
        system: 新的系统信息

    Returns:
        dict: {code, message, data}
    """
    try:
        systems = _read_systems()

        # 查找并更新
        found = False
        for idx, s in enumerate(systems):
            if s["name"] == system_name:
                systems[idx] = {
                    "name": system.name,
                    "abbreviation": system.abbreviation,
                    "status": system.status
                }
                found = True
                break

        if not found:
            raise HTTPException(status_code=404, detail=f"系统 '{system_name}' 不存在")

        _write_systems(systems)

        logger.info(f"更新主系统: {system_name} -> {system.name}")
        return {
            "code": 200,
            "message": "更新成功",
            "data": {
                "name": system.name,
                "abbreviation": system.abbreviation,
                "status": system.status
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
        system_name: 系统名称

    Returns:
        dict: {code, message, data}
    """
    try:
        systems = _read_systems()

        # 查找并删除
        found = False
        for idx, s in enumerate(systems):
            if s["name"] == system_name:
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
