import dashscope
import pytest

from backend.config.config import settings
from backend.service.embedding_service import EmbeddingService


def test_embedding_service_uses_dedicated_embedding_base_and_model(monkeypatch):
    monkeypatch.setattr(settings, "DASHSCOPE_API_KEY", "not-needed")
    monkeypatch.setattr(settings, "DASHSCOPE_API_BASE", "http://10.73.254.200:30000/v1")
    monkeypatch.setattr(settings, "DASHSCOPE_EMBEDDING_API_BASE", "")
    monkeypatch.setattr(settings, "EMBEDDING_API_BASE", "http://10.73.254.200:30200/v1")
    monkeypatch.setattr(settings, "EMBEDDING_MODEL", "Qwen3-Embedding")
    monkeypatch.setattr(settings, "EMBEDDING_API_STYLE", "openai")

    service = EmbeddingService()

    assert service.embedding_api_base == "http://10.73.254.200:30200/v1"
    assert service.model == "Qwen3-Embedding"
    assert service.api_style == "openai"


def test_embedding_service_auto_prefers_openai_for_v1_base(monkeypatch):
    monkeypatch.setattr(settings, "DASHSCOPE_API_KEY", "not-needed")
    monkeypatch.setattr(settings, "DASHSCOPE_API_BASE", "http://10.73.254.200:30000/v1")
    monkeypatch.setattr(settings, "DASHSCOPE_EMBEDDING_API_BASE", "")
    monkeypatch.setattr(settings, "EMBEDDING_API_BASE", "http://10.73.254.200:30200/v1")
    monkeypatch.setattr(settings, "EMBEDDING_MODEL", "Qwen3-Embedding")
    monkeypatch.setattr(settings, "EMBEDDING_API_STYLE", "auto")

    service = EmbeddingService()

    assert service.api_style == "openai"


def test_embedding_service_keeps_dashscope_sdk_base_for_dashscope_style(monkeypatch):
    monkeypatch.setattr(settings, "DASHSCOPE_API_KEY", "not-needed")
    monkeypatch.setattr(settings, "DASHSCOPE_API_BASE", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    monkeypatch.setattr(settings, "DASHSCOPE_EMBEDDING_API_BASE", "")
    monkeypatch.setattr(settings, "EMBEDDING_API_BASE", "")
    monkeypatch.setattr(settings, "EMBEDDING_MODEL", "text-embedding-v2")
    monkeypatch.setattr(settings, "EMBEDDING_API_STYLE", "dashscope")
    monkeypatch.setattr(dashscope, "base_http_api_url", "https://dashscope.aliyuncs.com/api/v1")

    service = EmbeddingService()

    assert service.api_style == "dashscope"
    assert dashscope.base_http_api_url == "https://dashscope.aliyuncs.com/api/v1"


def test_embedding_service_error_contains_context_for_openai_style(monkeypatch):
    monkeypatch.setattr(settings, "DASHSCOPE_API_KEY", "not-needed")
    monkeypatch.setattr(settings, "DASHSCOPE_API_BASE", "http://10.73.254.200:30000/v1")
    monkeypatch.setattr(settings, "DASHSCOPE_EMBEDDING_API_BASE", "")
    monkeypatch.setattr(settings, "EMBEDDING_API_BASE", "http://10.73.254.200:30200/v1")
    monkeypatch.setattr(settings, "EMBEDDING_MODEL", "Qwen3-Embedding")
    monkeypatch.setattr(settings, "EMBEDDING_API_STYLE", "openai")

    service = EmbeddingService()

    class _BrokenEmbeddings:
        @staticmethod
        def create(**kwargs):
            raise RuntimeError("gateway timeout")

    class _BrokenClient:
        embeddings = _BrokenEmbeddings()

    monkeypatch.setattr(service, "_openai_client", _BrokenClient())

    with pytest.raises(RuntimeError) as exc_info:
        service.batch_generate_embeddings(["技术方案内容片段A"])

    message = str(exc_info.value)
    assert "style=openai" in message
    assert "base=http://10.73.254.200:30200/v1" in message
    assert "model=Qwen3-Embedding" in message
