import json
import logging
import os
from typing import Any, Dict

from backend.config.config import settings

logger = logging.getLogger(__name__)

DEFAULT_COSMIC_CONFIG = {
    "data_group_rules": {
        "enabled": True,
        "min_attributes": 2,
        "min_data_groups": 1,
    },
    "functional_process_rules": {
        "enabled": True,
        "granularity": "medium",
        "min_data_movements": 2,
        "max_data_movements": 50,
    },
    "data_movement_rules": {
        "entry": {
            "enabled": True,
            "description": "数据从用户进入功能处理",
            "keywords": ["输入", "接收", "获取", "录入", "上传", "提交"],
            "weight": 1,
        },
        "exit": {
            "enabled": True,
            "description": "数据从功能处理返回给用户",
            "keywords": ["输出", "返回", "显示", "展示", "响应", "结果"],
            "weight": 1,
        },
        "read": {
            "enabled": True,
            "description": "从持久存储读取数据",
            "keywords": ["查询", "读取", "检索", "获取", "加载"],
            "weight": 1,
        },
        "write": {
            "enabled": True,
            "description": "数据写入持久存储",
            "keywords": ["保存", "写入", "存储", "创建", "更新", "删除"],
            "weight": 1,
        },
    },
    "counting_rules": {
        "cff_calculation_method": "sum",
        "include_triggering_operations": True,
        "count_unique_data_groups": True,
    },
    "validation_rules": {
        "min_cff_per_feature": 2,
        "max_cff_per_feature": 100,
        "validate_data_group_consistency": True,
    },
}


def get_writable_cosmic_config_path() -> str:
    report_dir = os.path.realpath(str(getattr(settings, "REPORT_DIR", "") or "data"))
    return os.path.join(report_dir, "cosmic_config.json")


def get_legacy_cosmic_config_path() -> str:
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "config",
        "cosmic_config.json",
    )


def load_cosmic_config() -> Dict[str, Any]:
    writable_path = get_writable_cosmic_config_path()
    legacy_path = get_legacy_cosmic_config_path()

    for path in (writable_path, legacy_path):
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as fh:
                config = json.load(fh)
            logger.info("从文件加载COSMIC配置: %s", path)
            return config
        except Exception as exc:
            logger.warning("加载COSMIC配置失败: %s，path=%s", exc, path)

    logger.info("COSMIC配置文件不存在，使用默认配置")
    return json.loads(json.dumps(DEFAULT_COSMIC_CONFIG))


def save_cosmic_config(config: Dict[str, Any]) -> str:
    target_path = get_writable_cosmic_config_path()
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    with open(target_path, "w", encoding="utf-8") as fh:
        json.dump(config, fh, ensure_ascii=False, indent=2)
    logger.info("COSMIC配置已保存: %s", target_path)
    return target_path
