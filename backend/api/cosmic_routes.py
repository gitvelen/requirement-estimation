"""
COSMIC规则配置API
提供COSMIC功能点分析规则的配置接口
"""
import logging
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from backend.api.auth import require_admin_api_key, require_roles
from backend.utils.cosmic_config_store import (
    DEFAULT_COSMIC_CONFIG,
    load_cosmic_config,
    save_cosmic_config,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/cosmic", tags=["COSMIC配置"])


# 数据模型
class DataMovementRule(BaseModel):
    """数据移动规则模型"""
    enabled: bool = True
    description: str
    keywords: List[str]
    weight: int = 1


class DataGroupRules(BaseModel):
    """数据组规则模型"""
    enabled: bool = True
    min_attributes: int = 2
    min_data_groups: int = 1


class FunctionalProcessRules(BaseModel):
    """功能处理规则模型"""
    enabled: bool = True
    granularity: str = "medium"  # fine/medium/coarse
    min_data_movements: int = 2
    max_data_movements: int = 50


class CountingRules(BaseModel):
    """计数规则模型"""
    cff_calculation_method: str = "sum"  # sum/weighted
    include_triggering_operations: bool = True
    count_unique_data_groups: bool = True


class ValidationRules(BaseModel):
    """验证规则模型"""
    min_cff_per_feature: int = 2
    max_cff_per_feature: int = 100
    validate_data_group_consistency: bool = True


class CosmicConfig(BaseModel):
    """COSMIC配置模型"""
    data_group_rules: DataGroupRules
    functional_process_rules: FunctionalProcessRules
    data_movement_rules: Dict[str, DataMovementRule]
    counting_rules: CountingRules
    validation_rules: ValidationRules

@router.get("/config")
async def get_cosmic_config(_auth: None = Depends(require_roles(["admin"]))):
    """
    获取COSMIC配置

    Returns:
        dict: {code, message, data}
    """
    try:
        config = load_cosmic_config()
        return {
            "code": 200,
            "message": "获取成功",
            "data": config
        }
    except Exception as e:
        logger.error(f"获取COSMIC配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")


@router.post("/config")
async def update_cosmic_config(config: CosmicConfig, _auth: None = Depends(require_admin_api_key)):
    """
    更新COSMIC配置

    Args:
        config: COSMIC配置

    Returns:
        dict: {code, message, data}
    """
    try:
        # 转换为字典
        config_dict = config.model_dump()

        # 保存配置
        save_cosmic_config(config_dict)

        logger.info("COSMIC配置已更新")
        return {
            "code": 200,
            "message": "配置更新成功",
            "data": config_dict
        }
    except Exception as e:
        logger.error(f"更新COSMIC配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新配置失败: {str(e)}")


@router.post("/reset")
async def reset_cosmic_config(_auth: None = Depends(require_admin_api_key)):
    """
    重置为默认配置

    Returns:
        dict: {code, message, data}
    """
    try:
        save_cosmic_config(DEFAULT_COSMIC_CONFIG.copy())

        logger.info("COSMIC配置已重置为默认值")
        return {
            "code": 200,
            "message": "配置已重置",
            "data": DEFAULT_COSMIC_CONFIG
        }
    except Exception as e:
        logger.error(f"重置COSMIC配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"重置配置失败: {str(e)}")


@router.get("/analyze/{feature_description}")
async def analyze_feature_cosmic(feature_description: str):
    """
    根据当前配置分析功能点的COSMIC数据移动

    Args:
        feature_description: 功能点描述

    Returns:
        dict: {code, message, data: cosmic_analysis}
    """
    try:
        from backend.utils.cosmic_analyzer import cosmic_analyzer

        # 分析功能点
        analysis = cosmic_analyzer.analyze_feature(feature_description)

        return {
            "code": 200,
            "message": "分析完成",
            "data": analysis
        }
    except Exception as e:
        logger.error(f"COSMIC分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.post("/reload")
async def reload_cosmic_config(_auth: None = Depends(require_admin_api_key)):
    """
    重新加载COSMIC配置（热加载）

    Returns:
        dict: {code, message, data}
    """
    try:
        from backend.utils.cosmic_analyzer import cosmic_analyzer

        # 重新加载配置
        cosmic_analyzer.load_config()

        logger.info("COSMIC配置已重新加载")
        return {
            "code": 200,
            "message": "重新加载成功",
            "data": {"config": cosmic_analyzer.config}
        }
    except Exception as e:
        logger.error(f"重新加载COSMIC配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"重新加载失败: {str(e)}")
