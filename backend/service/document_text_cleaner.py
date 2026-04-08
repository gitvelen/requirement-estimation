from __future__ import annotations

import json
import re
from typing import Any, List


def normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def parsed_to_text(parsed_data: Any) -> str:
    if isinstance(parsed_data, str):
        return parsed_data
    if isinstance(parsed_data, list):
        lines = []
        for item in parsed_data:
            if isinstance(item, dict):
                line = " ".join(str(value).strip() for value in item.values() if str(value).strip())
            else:
                line = str(item or "").strip()
            if line:
                lines.append(line)
        return "\n".join(lines)
    if isinstance(parsed_data, dict):
        if "text" in parsed_data and isinstance(parsed_data.get("text"), str):
            return str(parsed_data.get("text") or "")

        lines = []
        if isinstance(parsed_data.get("paragraphs"), list):
            for paragraph in parsed_data["paragraphs"]:
                if isinstance(paragraph, dict):
                    text = str(paragraph.get("text") or "").strip()
                else:
                    text = str(paragraph or "").strip()
                if text:
                    lines.append(text)
        if isinstance(parsed_data.get("tables"), list):
            for table in parsed_data["tables"]:
                if not isinstance(table, dict):
                    continue
                for row in table.get("data") or []:
                    if isinstance(row, list):
                        text = " | ".join(str(cell).strip() for cell in row if str(cell or "").strip())
                    elif isinstance(row, dict):
                        text = " ".join(str(value).strip() for value in row.values() if str(value).strip())
                    else:
                        text = str(row or "").strip()
                    if text:
                        lines.append(text)
        if isinstance(parsed_data.get("slides"), list):
            for slide in parsed_data["slides"]:
                if isinstance(slide, dict):
                    text = str(slide.get("text") or "").strip()
                else:
                    text = str(slide or "").strip()
                if text:
                    lines.append(text)
        if isinstance(parsed_data.get("pages"), list):
            for page in parsed_data["pages"]:
                if isinstance(page, dict):
                    text = str(page.get("text") or "").strip()
                else:
                    text = str(page or "").strip()
                if text:
                    lines.append(text)
        if lines:
            return "\n".join(lines)

        if parsed_data and all(isinstance(v, list) for v in parsed_data.values()):
            table_lines = []
            for rows in parsed_data.values():
                for row in rows:
                    if isinstance(row, list):
                        line = " | ".join(str(cell).strip() for cell in row if cell is not None and str(cell).strip())
                    elif isinstance(row, dict):
                        line = " ".join(str(value).strip() for value in row.values() if str(value).strip())
                    else:
                        line = str(row or "").strip()
                    if line:
                        table_lines.append(line)
            if table_lines:
                return "\n".join(table_lines)

        try:
            return json.dumps(parsed_data, ensure_ascii=False)
        except Exception:
            return str(parsed_data)
    return str(parsed_data or "").strip()


def looks_like_heading(line: str) -> bool:
    text = normalize_text(line)
    if not text:
        return False
    return bool(
        re.match(r"^(第[一二三四五六七八九十百零\d]+[章节篇]|附录)", text)
        or re.match(r"^\d+(?:\.\d+){0,3}\s*", text)
    )


def looks_like_toc_entry(line: str) -> bool:
    text = normalize_text(line)
    compact = text.replace(" ", "")
    if not text:
        return False
    if compact in {"目录", "目次"} or compact.startswith("目录"):
        return True
    if re.search(r"(?:\.{2,}|·{2,}|…{2,}|—{2,})\s*\d+$", text):
        return True
    if re.match(r"^第[一二三四五六七八九十百零\d]+[章节篇].*\d+$", text):
        return True
    return bool(re.match(r"^\d+(?:\.\d+){0,3}\s+.+\s+\d+$", text))


def extract_clean_lines(text: str) -> List[str]:
    raw_lines = [normalize_text(line) for line in str(text or "").splitlines()]
    raw_lines = [line for line in raw_lines if line]
    if not raw_lines:
        return []

    filtered: List[str] = []
    in_toc = False
    for index, line in enumerate(raw_lines):
        compact = line.replace(" ", "")
        if index < 40 and compact in {"目录", "目次"}:
            in_toc = True
            continue
        if in_toc:
            if looks_like_toc_entry(line):
                continue
            in_toc = False
        filtered.append(line)

    return filtered or raw_lines


def clean_document_text(text: str) -> str:
    return "\n".join(extract_clean_lines(text))
