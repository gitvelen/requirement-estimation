from types import SimpleNamespace

import pytest

from backend.config.config import Settings
from backend.utils.token_counter import (
    chunk_text,
    estimate_tokens,
    extract_usage_from_response,
)


def test_summary_chunking_settings_defaults_exist(monkeypatch):
    monkeypatch.setenv("LLM_MAX_CONTEXT_TOKENS", "32000")
    monkeypatch.setenv("LLM_INPUT_MAX_TOKENS", "25000")
    monkeypatch.setenv("LLM_CHUNK_OVERLAP_PARAGRAPHS", "2")
    monkeypatch.setenv("ENABLE_LLM_CHUNKING", "true")

    settings = Settings()

    assert settings.LLM_MAX_CONTEXT_TOKENS == 32000
    assert settings.LLM_INPUT_MAX_TOKENS == 25000
    assert settings.LLM_CHUNK_OVERLAP_PARAGRAPHS == 2
    assert settings.ENABLE_LLM_CHUNKING is True


def test_estimate_tokens_uses_conservative_ratio():
    assert estimate_tokens("") == 0
    assert estimate_tokens("a" * 25) == 10
    assert estimate_tokens("中" * 250) == 100


def test_extract_usage_from_response_supports_dict_and_object_shapes():
    dict_usage = extract_usage_from_response(
        {
            "usage": {
                "prompt_tokens": 101,
                "completion_tokens": 202,
                "total_tokens": 303,
            }
        }
    )
    object_usage = extract_usage_from_response(
        SimpleNamespace(
            usage=SimpleNamespace(prompt_tokens=11, completion_tokens=22, total_tokens=33)
        )
    )

    assert dict_usage == {
        "prompt_tokens": 101,
        "completion_tokens": 202,
        "total_tokens": 303,
    }
    assert object_usage == {
        "prompt_tokens": 11,
        "completion_tokens": 22,
        "total_tokens": 33,
    }
    assert extract_usage_from_response({}) == {}


def test_chunk_text_with_overlap_preserves_reconstruction_order():
    paragraphs = [
        "A" * 20000,
        "B" * 20000,
        "C" * 20000,
        "D" * 20000,
    ]
    text = "\n\n".join(paragraphs)

    chunks = chunk_text(text, max_tokens=25000, overlap_paragraphs=2)

    assert len(chunks) == 2
    assert [(chunk.start_paragraph_index, chunk.end_paragraph_index) for chunk in chunks] == [
        (0, 2),
        (1, 3),
    ]
    assert all(chunk.estimated_tokens <= 25000 for chunk in chunks)

    reconstructed = []
    last_end = -1
    for chunk in chunks:
        start = max(chunk.start_paragraph_index, last_end + 1)
        reconstructed.extend(paragraphs[start : chunk.end_paragraph_index + 1])
        last_end = max(last_end, chunk.end_paragraph_index)

    assert reconstructed == paragraphs


def test_chunk_text_shrinks_overlap_when_requested_overlap_cannot_fit():
    paragraphs = [
        "A" * 15000,
        "B" * 15000,
        "C" * 15000,
    ]
    text = "\n\n".join(paragraphs)

    chunks = chunk_text(text, max_tokens=13000, overlap_paragraphs=2)

    assert len(chunks) == 2
    assert [(chunk.start_paragraph_index, chunk.end_paragraph_index) for chunk in chunks] == [
        (0, 1),
        (1, 2),
    ]
    assert all(chunk.estimated_tokens <= 13000 for chunk in chunks)


def test_chunk_text_rejects_single_paragraph_above_budget():
    text = "A" * 62501

    with pytest.raises(ValueError, match="CHUNK_PARAGRAPH_TOO_LONG"):
        chunk_text(text, max_tokens=25000, overlap_paragraphs=2)


def test_chunk_text_handles_525_paragraph_47_table_scale_sample():
    paragraphs = [f"段落{i:03d}：" + ("系统能力说明" * 32) for i in range(525)]
    table_rows = [f"表格行{i:02d} | 字段A | 字段B | 约束说明" for i in range(47)]
    text = "\n\n".join(paragraphs + table_rows)

    chunks = chunk_text(text, max_tokens=25000, overlap_paragraphs=2)

    assert len(chunks) >= 2
    assert all(chunk.estimated_tokens <= 25000 for chunk in chunks)
