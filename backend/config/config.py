"""
配置管理模块
管理所有系统配置项，包括大模型API、数据库连接等
"""
import os
from typing import Optional, List
from pydantic_settings import BaseSettings


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}

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
    DASHSCOPE_API_BASE: str = os.getenv("DASHSCOPE_API_BASE", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    DASHSCOPE_EMBEDDING_API_BASE: str = os.getenv("DASHSCOPE_EMBEDDING_API_BASE", "").strip()
    LLM_MODEL: str = os.getenv("LLM_MODEL", "qwen-turbo")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "4000"))
    LLM_TIMEOUT: int = int(os.getenv("LLM_TIMEOUT", "120"))  # LLM请求超时时间（秒），异步任务需要更长时间
    LLM_MAX_CONTEXT_TOKENS: int = int(os.getenv("LLM_MAX_CONTEXT_TOKENS", "32000"))
    LLM_INPUT_MAX_TOKENS: int = int(os.getenv("LLM_INPUT_MAX_TOKENS", "25000"))
    LLM_CHUNK_OVERLAP_PARAGRAPHS: int = int(os.getenv("LLM_CHUNK_OVERLAP_PARAGRAPHS", "2"))
    ENABLE_LLM_CHUNKING: bool = _env_bool("ENABLE_LLM_CHUNKING", True)

    # Milvus向量数据库配置
    MILVUS_HOST: str = os.getenv("MILVUS_HOST", "localhost")
    MILVUS_PORT: int = int(os.getenv("MILVUS_PORT", "19530"))
    MILVUS_COLLECTION_NAME: str = "system_knowledge"

    # 知识库配置
    KNOWLEDGE_ENABLED: bool = os.getenv("KNOWLEDGE_ENABLED", "true").lower() == "true"
    # 向量存储后端：local（本地文件向量库）/ milvus（Milvus向量库，需配套MinIO等）
    KNOWLEDGE_VECTOR_STORE: str = os.getenv("KNOWLEDGE_VECTOR_STORE", "local").lower()
    EMBEDDING_API_BASE: str = os.getenv("EMBEDDING_API_BASE", "").strip()  # embedding独立网关（可选）
    EMBEDDING_API_STYLE: str = os.getenv("EMBEDDING_API_STYLE", "auto").strip().lower()  # auto/openai/dashscope
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-v2")  # Embedding模型
    EMBEDDING_DIM: int = 1024  # 向量维度
    KNOWLEDGE_TOP_K: int = 5  # 检索TopK数量
    KNOWLEDGE_SIMILARITY_THRESHOLD: float = 0.6  # 相似度阈值

    # ESB embedding 批次大小配置
    ESB_EMBEDDING_BATCH_SIZE: int = int(os.getenv("ESB_EMBEDDING_BATCH_SIZE", "10"))

    # 文件上传配置
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = int(os.getenv("MAX_UPLOAD_SIZE", "10")) * 1024 * 1024  # 默认10MB
    SYSTEM_PROFILE_IMPORT_MAX_BYTES: int = int(
        os.getenv("SYSTEM_PROFILE_IMPORT_MAX_MB", "200")
    ) * 1024 * 1024
    KNOWLEDGE_IMPORT_MAX_BYTES: int = int(
        os.getenv("KNOWLEDGE_IMPORT_MAX_MB", "200")
    ) * 1024 * 1024

    # 系统画像AI总结上下文配置（字符级）
    PROFILE_SUMMARY_CONTEXT_MAX_CHARS: int = int(
        os.getenv("PROFILE_SUMMARY_CONTEXT_MAX_CHARS", "120000")
    )
    PROFILE_SUMMARY_SAMPLE_MAX_ITEMS: int = int(
        os.getenv("PROFILE_SUMMARY_SAMPLE_MAX_ITEMS", "48")
    )
    PROFILE_SUMMARY_SAMPLE_ITEM_MAX_CHARS: int = int(
        os.getenv("PROFILE_SUMMARY_SAMPLE_ITEM_MAX_CHARS", "1200")
    )

    # 非结构化文档切片配置
    KNOWLEDGE_UNSTRUCTURED_CHUNK_SIZE: int = int(
        os.getenv("KNOWLEDGE_UNSTRUCTURED_CHUNK_SIZE", "1000")
    )
    KNOWLEDGE_UNSTRUCTURED_CHUNK_OVERLAP: int = int(
        os.getenv("KNOWLEDGE_UNSTRUCTURED_CHUNK_OVERLAP", "150")
    )
    KNOWLEDGE_MAX_UNSTRUCTURED_CHUNKS: int = int(
        os.getenv("KNOWLEDGE_MAX_UNSTRUCTURED_CHUNKS", "2000")
    )

    @property
    def ALLOWED_EXTENSIONS(self) -> set:
        """获取允许的文件扩展名集合"""
        extensions_str = os.getenv("ALLOWED_EXTENSIONS", ".docx,.doc,.pdf,.txt,.xlsx,.xls")
        return {ext.strip() for ext in extensions_str.split(",") if ext.strip()}

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

    # v2.1 功能开关（Feature Flags）
    V21_AUTO_REEVAL_ENABLED: bool = _env_bool("V21_AUTO_REEVAL_ENABLED", True)
    V21_AI_REMARK_ENABLED: bool = _env_bool("V21_AI_REMARK_ENABLED", True)
    V21_DASHBOARD_MGMT_ENABLED: bool = _env_bool("V21_DASHBOARD_MGMT_ENABLED", True)

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
