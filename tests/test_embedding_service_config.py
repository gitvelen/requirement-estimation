import dashscope

from backend.config.config import settings
from backend.service.embedding_service import EmbeddingService


def test_embedding_service_uses_internal_api_base_for_dashscope_sdk(monkeypatch):
    monkeypatch.setattr(settings, "DASHSCOPE_API_KEY", "not-needed")
    monkeypatch.setattr(settings, "DASHSCOPE_API_BASE", "http://10.73.254.200:30000/v1")
    monkeypatch.setattr(settings, "DASHSCOPE_EMBEDDING_API_BASE", "")
    monkeypatch.setattr(dashscope, "base_http_api_url", "https://dashscope.aliyuncs.com/api/v1")

    EmbeddingService()

    assert dashscope.base_http_api_url == "http://10.73.254.200:30000/v1"


def test_embedding_service_prefers_embedding_specific_api_base(monkeypatch):
    monkeypatch.setattr(settings, "DASHSCOPE_API_KEY", "not-needed")
    monkeypatch.setattr(settings, "DASHSCOPE_API_BASE", "http://10.73.254.200:30000/v1")
    monkeypatch.setattr(settings, "DASHSCOPE_EMBEDDING_API_BASE", "http://10.73.254.200:30000/api/v1")
    monkeypatch.setattr(dashscope, "base_http_api_url", "https://dashscope.aliyuncs.com/api/v1")

    EmbeddingService()

    assert dashscope.base_http_api_url == "http://10.73.254.200:30000/api/v1"
