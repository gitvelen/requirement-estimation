"""
配置管理模块
管理所有系统配置项，包括大模型API、数据库连接等
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """系统配置类"""

    # 应用配置
    APP_NAME: str = "业务需求工作量评估系统"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    API_PREFIX: str = "/api/v1"

    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 443
    WORKERS: int = 4

    # 阿里云大模型配置
    DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY", "")
    DASHSCOPE_API_BASE: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    LLM_MODEL: str = "qwen-turbo"  # 默认模型
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 4000
    LLM_TIMEOUT: int = 60

    # Milvus向量数据库配置
    MILVUS_HOST: str = os.getenv("MILVUS_HOST", "localhost")
    MILVUS_PORT: int = int(os.getenv("MILVUS_PORT", "19530"))
    MILVUS_COLLECTION_NAME: str = "system_knowledge"

    # 文件上传配置
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: set = {".docx"}

    # Excel报告配置
    REPORT_DIR: str = "data"
    REPORT_TEMPLATE_DIR: str = "templates"

    # COSMIC功能点配置
    COSMIC_ENABLED: bool = True  # 是否启用COSMIC算法
    DEFAULT_DATA_MOVEMENT: dict = {
        "E": 2,  # 入口数据移动权重
        "R": 2,  # 读数据移动权重
        "W": 2,  # 写数据移动权重
        "X": 1   # 出口数据移动权重
    }

    # Delphi专家评估配置
    DELPHI_ROUNDS: int = 3  # Delphi估算轮数
    DELPHI_EXPERTS: list = ["专家1", "专家2", "专家3", "专家4", "专家5"]
    DELPHI_EXPERT_WEIGHTS: dict = {
        "专家1": 1.0,
        "专家2": 1.0,
        "专家3": 1.0,
        "专家4": 0.8,
        "专家5": 0.8
    }

    # 任务配置
    TASK_TIMEOUT: int = 600  # 任务超时时间（秒）
    TASK_RETRY_TIMES: int = 3  # 任务重试次数

    class Config:
        env_file = ".env"
        case_sensitive = True

# 全局配置实例
settings = Settings()
