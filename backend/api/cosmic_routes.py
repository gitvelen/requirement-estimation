"""
COSMIC规则配置API
提供COSMIC功能点分析规则的配置接口
"""
import os
import json
import logging
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from backend.api.auth import require_admin_api_key, require_roles

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/cosmic", tags=["COSMIC配置"])

# 配置文件路径
CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")
COSMIC_CONFIG_PATH = os.path.join(CONFIG_DIR, "cosmic_config.json")

# 默认COSMIC配置
DEFAULT_COSMIC_CONFIG = {
    "data_group_rules": {
        "enabled": True,
        "min_attributes": 2,  # 最小属性数量
        "min_data_groups": 1  # 最小数据组数量
    },
    "functional_process_rules": {
        "enabled": True,
        "granularity": "medium",  # fine/medium/coarse
        "min_data_movements": 2,  # 最小数据移动数量
        "max_data_movements": 50  # 最大数据移动数量
    },
    "data_movement_rules": {
        "entry": {
            "enabled": True,
            "description": "数据从用户进入功能处理",
            "keywords": ["输入", "接收", "获取", "录入", "上传", "提交"],
            "weight": 1
        },
        "exit": {
            "enabled": True,
            "description": "数据从功能处理返回给用户",
            "keywords": ["输出", "返回", "显示", "展示", "响应", "结果"],
            "weight": 1
        },
        "read": {
            "enabled": True,
            "description": "从持久存储读取数据",
            "keywords": ["查询", "读取", "检索", "获取", "加载"],
            "weight": 1
        },
        "write": {
            "enabled": True,
            "description": "数据写入持久存储",
            "keywords": ["保存", "写入", "存储", "创建", "更新", "删除"],
            "weight": 1
        }
    },
    "counting_rules": {
        "cff_calculation_method": "sum",  # sum/weighted
        "include_triggering_operations": True,
        "count_unique_data_groups": True
    },
    "validation_rules": {
        "min_cff_per_feature": 2,
        "max_cff_per_feature": 100,
        "validate_data_group_consistency": True
    }
}


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


def _load_cosmic_config() -> Dict[str, Any]:
    """加载COSMIC配置"""
    if os.path.exists(COSMIC_CONFIG_PATH):
        try:
            with open(COSMIC_CONFIG_PATH, 'r', encoding='utf-8') as f:
                config = json.load(f)
                logger.info(f"从文件加载COSMIC配置: {COSMIC_CONFIG_PATH}")
                return config
        except Exception as e:
            logger.warning(f"加载COSMIC配置失败: {e}，使用默认配置")
    else:
        logger.info("COSMIC配置文件不存在，使用默认配置")

    return DEFAULT_COSMIC_CONFIG.copy()


def _save_cosmic_config(config: Dict[str, Any]):
    """保存COSMIC配置"""
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(COSMIC_CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        logger.info(f"COSMIC配置已保存: {COSMIC_CONFIG_PATH}")
    except Exception as e:
        logger.error(f"保存COSMIC配置失败: {e}")
        raise


@router.get("/config")
async def get_cosmic_config(_auth: None = Depends(require_roles(["admin"]))):
    """
    获取COSMIC配置

    Returns:
        dict: {code, message, data}
    """
    try:
        config = _load_cosmic_config()
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
        config_dict = config.dict()

        # 保存配置
        _save_cosmic_config(config_dict)

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
        _save_cosmic_config(DEFAULT_COSMIC_CONFIG.copy())

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
