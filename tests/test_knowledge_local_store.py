import pytest

from backend.config.config import settings
from backend.service import knowledge_service as ks


class DummyEmbeddingService:
    def generate_embedding(self, text: str):
        # 固定向量，便于本地检索用例稳定
        return [1.0, 0.0, 0.0]


@pytest.fixture()
def service(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(settings, "REPORT_DIR", str(data_dir))
    monkeypatch.setattr(settings, "KNOWLEDGE_VECTOR_STORE", "local")

    # 避免在测试中触发真实Embedding初始化（依赖DASHSCOPE_API_KEY）
    monkeypatch.setattr(ks, "get_embedding_service", lambda: DummyEmbeddingService())

    svc = ks.KnowledgeService()
    return svc


def test_local_store_basic_flow(service):
    service.document_parser.parse = lambda *_args, **_kwargs: {"dummy": True}
    service.document_parser.extract_system_knowledge = lambda *_args, **_kwargs: {
        "type": "system_profile",
        "count": 1,
        "systems": [
            {
                "system_name": "原系统名称",
                "system_short_name": "SYS",
                "business_goal": "用于测试的业务目标",
                "core_functions": "账户管理、交易核算",
                "tech_stack": "Python",
                "architecture": "微服务",
                "performance": "TPS 1000+",
                "main_users": "测试用户",
                "notes": "",
            }
        ],
    }

    result = service.import_from_file(
        file_content=b"dummy",
        filename="system_profile.docx",
        auto_extract=True,
        knowledge_type="system_profile",
        system_name="测试系统",
    )
    assert result["success"] == 1

    stats = service.get_knowledge_stats(system_name="测试系统")
    assert stats.get("count") == 1
    assert stats.get("system_profile_count") == 1
    assert stats.get("feature_case_count") == 0
    assert stats.get("tech_spec_count") == 0
    assert stats.get("index") in ("LOCAL_SCAN", "IVF_FLAT")

    results = service.search_similar_knowledge(
        query_text="随便查询一下",
        system_name="测试系统",
        knowledge_type="system_profile",
        top_k=5,
        similarity_threshold=0.1,
    )
    assert results
    assert results[0]["knowledge_type"] == "system_profile"
    assert results[0]["system_name"] == "测试系统"

    rebuild = service.rebuild_index()
    assert rebuild.get("status") == "success"


def test_import_requires_system_name(service):
    service.document_parser.parse = lambda *_args, **_kwargs: {"dummy": True}
    service.document_parser.extract_system_knowledge = lambda *_args, **_kwargs: {
        "type": "system_profile",
        "count": 1,
        "systems": [{"system_name": "任意系统"}],
    }

    result = service.import_from_file(
        file_content=b"dummy",
        filename="system_profile.docx",
        auto_extract=True,
        knowledge_type="system_profile",
        system_name=None,
    )
    assert result["failed"] == 1
    assert any("system_name不能为空" in str(item) for item in result.get("errors", []))
