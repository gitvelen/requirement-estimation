"""
配置管理模块
管理所有系统配置项，包括大模型API、数据库连接等
"""
import os
from typing import Optional, List
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

    # CORS配置（从环境变量读取，支持多个域名用逗号分隔）
    # 注意：ALLOWED_ORIGINS是属性，不需要在model_config中声明

    @property
    def ALLOWED_ORIGINS(self) -> List[str]:
        """获取允许的CORS域名列表"""
        origins_str = os.getenv("ALLOWED_ORIGINS", "http://172.18.121.196,http://172.18.121.196:80")
        return [origin.strip() for origin in origins_str.split(",") if origin.strip()]

    # 阿里云大模型配置
    DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY", "")
    DASHSCOPE_API_BASE: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    LLM_MODEL: str = "qwen-turbo"  # 默认模型
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 4000
    LLM_TIMEOUT: int = 120  # LLM请求超时时间（秒），异步任务需要更长时间

    # Milvus向量数据库配置
    MILVUS_HOST: str = os.getenv("MILVUS_HOST", "localhost")
    MILVUS_PORT: int = int(os.getenv("MILVUS_PORT", "19530"))
    MILVUS_COLLECTION_NAME: str = "system_knowledge"

    # 知识库配置
    KNOWLEDGE_ENABLED: bool = os.getenv("KNOWLEDGE_ENABLED", "true").lower() == "true"
    # 向量存储后端：local（本地文件向量库）/ milvus（Milvus向量库，需配套MinIO等）
    KNOWLEDGE_VECTOR_STORE: str = os.getenv("KNOWLEDGE_VECTOR_STORE", "local").lower()
    EMBEDDING_MODEL: str = "text-embedding-v2"  # 阿里云Embedding模型
    EMBEDDING_DIM: int = 1024  # 向量维度
    KNOWLEDGE_TOP_K: int = 5  # 检索TopK数量
    KNOWLEDGE_SIMILARITY_THRESHOLD: float = 0.6  # 相似度阈值

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
    TASK_RETENTION_DAYS: int = int(os.getenv("TASK_RETENTION_DAYS", "7"))  # 任务保留天数

    # 简单鉴权（生产环境建议启用）
    ADMIN_API_KEY: str = os.getenv("ADMIN_API_KEY", "")

    # JWT配置
    JWT_SECRET: str = os.getenv("JWT_SECRET", "change_me")
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "120"))

    model_config = {
        "extra": "ignore",
        "env_file": ".env",
        "case_sensitive": True
    }

# 全局配置实例
settings = Settings()
