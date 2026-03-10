"""
Token 估算与段落级分块工具。
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Dict, List


TOKEN_ESTIMATE_CHARS_PER_TOKEN = 2.5


@dataclass(frozen=True)
class ChunkPlanItem:
    chunk_index: int
    content: str
    estimated_tokens: int
    start_paragraph_index: int
    end_paragraph_index: int


def estimate_tokens(text: str) -> int:
    normalized = str(text or "")
    if not normalized:
        return 0
    return math.ceil(len(normalized) / TOKEN_ESTIMATE_CHARS_PER_TOKEN)


def extract_usage_from_response(response: Any) -> Dict[str, int]:
    usage = response.get("usage") if isinstance(response, dict) else getattr(response, "usage", None)
    if usage is None:
        return {}

    result: Dict[str, int] = {}
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        value = usage.get(key) if isinstance(usage, dict) else getattr(usage, key, None)
        if value is None:
            continue
        try:
            result[key] = int(value)
        except (TypeError, ValueError):
            continue
    return result


def chunk_text(text: str, *, max_tokens: int, overlap_paragraphs: int = 2) -> List[ChunkPlanItem]:
    if max_tokens <= 0:
        raise ValueError("max_tokens must be positive")

    paragraphs = [paragraph.strip() for paragraph in str(text or "").split("\n\n") if paragraph.strip()]
    if not paragraphs:
        return []

    for paragraph in paragraphs:
        if estimate_tokens(paragraph) > max_tokens:
            raise ValueError("CHUNK_PARAGRAPH_TOO_LONG")

    chunks: List[ChunkPlanItem] = []
    start_index = 0
    chunk_index = 0

    while start_index < len(paragraphs):
        end_index = start_index
        current_chunk: List[str] = []
        current_tokens = 0

        while end_index < len(paragraphs):
            candidate_chunk = current_chunk + [paragraphs[end_index]]
            candidate_text = "\n\n".join(candidate_chunk)
            candidate_tokens = estimate_tokens(candidate_text)
            if candidate_tokens > max_tokens:
                break
            current_chunk = candidate_chunk
            current_tokens = candidate_tokens
            end_index += 1

        if not current_chunk:
            raise ValueError("CHUNK_PARAGRAPH_TOO_LONG")

        final_end_index = end_index - 1
        chunks.append(
            ChunkPlanItem(
                chunk_index=chunk_index,
                content="\n\n".join(current_chunk),
                estimated_tokens=current_tokens,
                start_paragraph_index=start_index,
                end_paragraph_index=final_end_index,
            )
        )

        if final_end_index >= len(paragraphs) - 1:
            break

        max_overlap = min(max(int(overlap_paragraphs or 0), 0), len(current_chunk) - 1)
        next_start_index = final_end_index + 1
        next_new_index = final_end_index + 1
        for overlap in range(max_overlap, -1, -1):
            candidate_start = final_end_index - overlap + 1
            candidate_preview = "\n\n".join(paragraphs[candidate_start : next_new_index + 1])
            if estimate_tokens(candidate_preview) <= max_tokens:
                next_start_index = candidate_start
                break

        start_index = next_start_index
        chunk_index += 1

    return chunks
