import os

from backend.service.evidence_service import EvidenceService
from backend.service.local_vector_store import LocalVectorStore


class DummyEmbeddingService:
    def generate_embedding(self, text):
        return [1.0, 0.0, 0.0]

    def batch_generate_embeddings(self, texts, batch_size=25):
        return [[1.0, 0.0, 0.0] for _ in texts]


class DummyDocumentParser:
    def parse(self, file_content, filename, file_type=None):
        if file_type == "docx":
            return {
                "paragraphs": [{"text": "这是证据内容A"}],
                "tables": [],
                "metadata": {"total_paragraphs": 1, "total_tables": 0},
            }
        if file_type == "pdf":
            return {
                "pages": [{"page": 1, "text": "PDF证据内容"}],
                "metadata": {"page_count": 1},
            }
        if file_type == "pptx":
            return {
                "slides": [{"slide": 1, "text": "PPT证据内容"}],
                "metadata": {"total_slides": 1},
            }
        return {}


def build_service(tmp_path):
    store_path = tmp_path / "knowledge_store.json"
    docs_path = tmp_path / "evidence_docs.json"
    upload_dir = tmp_path / "uploads"
    return EvidenceService(
        store_path=str(store_path),
        docs_path=str(docs_path),
        upload_dir=str(upload_dir),
        embedding_service=DummyEmbeddingService(),
        document_parser=DummyDocumentParser(),
        vector_store=LocalVectorStore(str(store_path)),
    )


def test_import_search_preview_docx(tmp_path):
    service = build_service(tmp_path)

    result = service.import_evidence(
        file_content=b"dummy",
        filename="sample.docx",
        system_name="系统A",
        trust_level="高",
        created_by="tester",
    )
    assert result["doc_id"].startswith("evd_")
    assert result["chunk_count"] >= 1

    docs = service.list_docs(system_name="系统A")
    assert len(docs) == 1

    stats = service.get_stats(system_name="系统A")
    assert stats["doc_count"] == 1
    assert stats["chunk_count"] >= 1

    results = service.search_evidence(
        query="证据",
        system_name="系统A",
        top_k=5,
        similarity_threshold=0.0,
        task_id="task_1",
    )
    assert results
    assert results[0]["doc_id"] == result["doc_id"]

    doc = service.get_doc(result["doc_id"])
    preview = service.get_preview_text(doc)
    assert preview["preview_type"] == "text"
    assert "证据内容" in preview.get("content", "")


def test_import_preview_pdf(tmp_path):
    service = build_service(tmp_path)

    result = service.import_evidence(
        file_content=b"dummy",
        filename="sample.pdf",
        system_name="系统B",
        trust_level="中",
    )
    assert result["doc_id"].startswith("evd_")

    doc = service.get_doc(result["doc_id"])
    preview = service.get_preview_text(doc)
    assert preview["preview_type"] == "pdf"
    assert os.path.exists(doc.get("stored_path"))

