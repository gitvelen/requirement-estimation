import json

from backend.config.config import settings
from backend.service.esb_service import EsbService


class DummyEmbeddingService:
    def generate_embedding(self, text):
        return [1.0, 0.0, 0.0]

    def batch_generate_embeddings(self, texts, batch_size=25):
        return [[1.0, 0.0, 0.0] for _ in texts]


def build_service(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "REPORT_DIR", str(tmp_path))
    service = EsbService()
    service.embedding_service = DummyEmbeddingService()
    return service


def test_import_search_scope_and_status(tmp_path, monkeypatch):
    service = build_service(tmp_path, monkeypatch)

    csv_content = (
        "提供方系统简称,提供方中文名称,调用方系统简称,调用方中文名称,交易名称,交易码,服务场景码,状态\n"
        "SYS_A,系统A,SYS_B,系统B,白名单查询,SOFP500001,SC001,正常使用\n"
        "SYS_C,系统C,SYS_A,系统A,同步接口,SOFP500002,SC002,废弃使用\n"
    ).encode("utf-8")

    result = service.import_esb(csv_content, "esb.csv")
    assert result["imported"] == 2

    stats = service.get_stats(system_id="SYS_A")
    assert stats["active_entry_count"] == 1
    assert stats["deprecated_entry_count"] == 1

    provider_results = service.search_esb(
        query="接口",
        system_id="SYS_A",
        scope="provider",
        include_deprecated=False,
        similarity_threshold=0.0,
        top_k=5,
    )
    assert len(provider_results) == 1
    assert provider_results[0]["service_name"] == "白名单查询"

    consumer_results = service.search_esb(
        query="接口",
        system_id="SYS_A",
        scope="consumer",
        include_deprecated=True,
        similarity_threshold=0.0,
        top_k=5,
    )
    assert any(item["service_name"] == "同步接口" for item in consumer_results)
