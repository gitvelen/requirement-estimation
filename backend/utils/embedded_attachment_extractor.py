import hashlib
import logging
import re
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import olefile


logger = logging.getLogger(__name__)


def _extract_doc_text_from_worddocument_stream(blob: bytes, *, max_lines: int = 2000) -> str:
    if not blob:
        return ""

    text = blob.decode("utf-16le", errors="ignore")
    matches = re.findall(r"[\u4e00-\u9fffA-Za-z0-9《》、，。：；（）\-]{6,}", text)

    lines: List[str] = []
    seen = set()
    for item in matches:
        normalized = str(item or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        lines.append(normalized)
        if len(lines) >= max_lines:
            break

    return "\n".join(lines).strip()


def _sheet_rows_to_text(sheet_rows: Dict[str, List[List[Any]]], *, max_lines: int = 2000) -> str:
    lines: List[str] = []
    for sheet_name, rows in (sheet_rows or {}).items():
        if sheet_name:
            lines.append(f"[Sheet] {sheet_name}")
        for row in rows or []:
            if not isinstance(row, list):
                continue
            line = " | ".join(str(cell).strip() for cell in row if cell is not None and str(cell).strip())
            if line:
                lines.append(line)
            if len(lines) >= max_lines:
                break
        if len(lines) >= max_lines:
            break
    return "\n".join(lines).strip()


class EmbeddedAttachmentExtractor:
    """从 OOXML/OLE 宿主中提取嵌入附件，并递归解析支持格式。"""

    SUPPORTED_TYPES = {"doc", "docx", "xlsx", "pptx", "pdf"}
    OOXML_EMBEDDING_PREFIXES = (
        "word/embeddings/",
        "xl/embeddings/",
        "ppt/embeddings/",
    )
    OLE_NATIVE_STREAMS = (
        ("package",),
        ("ObjectPool", "_1234567890", "Workbook"),
        ("Workbook",),
        ("WordDocument",),
    )

    def __init__(
        self,
        parse_callback: Callable[[bytes, str, Optional[str], int, Set[str]], Any],
        max_depth: int = 3,
        max_attachment_size: int = 10 * 1024 * 1024,
        max_attachment_count: int = 20,
    ):
        self._parse_callback = parse_callback
        self._max_depth = max_depth
        self._max_attachment_size = max_attachment_size
        self._max_attachment_count = max_attachment_count

    def extract_from_ooxml(
        self,
        file_content: bytes,
        *,
        host_filename: str,
        depth: int,
        seen_hashes: Set[str],
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
        attachments: List[Dict[str, Any]] = []
        errors: List[Dict[str, str]] = []

        if depth >= self._max_depth:
            return attachments, errors

        try:
            with zipfile.ZipFile(BytesIO(file_content)) as archive:
                names = [
                    name
                    for name in archive.namelist()
                    if any(name.startswith(prefix) for prefix in self.OOXML_EMBEDDING_PREFIXES)
                    and not name.endswith("/")
                ]
                for name in names:
                    if len(attachments) >= self._max_attachment_count:
                        errors.append({"name": name, "reason": "attachment-count-limit-exceeded"})
                        break
                    try:
                        raw_payload = archive.read(name)
                        parsed = self._parse_embedded_payload(
                            payload=raw_payload,
                            payload_name=name,
                            depth=depth + 1,
                            seen_hashes=seen_hashes,
                        )
                        if parsed:
                            attachments.extend(parsed)
                    except Exception as exc:
                        logger.warning("提取嵌入附件失败: host=%s entry=%s error=%s", host_filename, name, exc)
                        errors.append({"name": name, "reason": str(exc)})
        except zipfile.BadZipFile:
            logger.debug("非 OOXML 文件跳过附件提取: %s", host_filename)

        return attachments, errors

    def _parse_embedded_payload(
        self,
        *,
        payload: bytes,
        payload_name: str,
        depth: int,
        seen_hashes: Set[str],
    ) -> List[Dict[str, Any]]:
        direct_rows = None
        if olefile.isOleFile(payload):
            with olefile.OleFileIO(payload) as ole:
                direct_rows = self._extract_xls_rows_from_ole(ole)

        if direct_rows:
            rendered = _sheet_rows_to_text(direct_rows)
            if rendered:
                payload_hash = hashlib.sha256(rendered.encode("utf-8")).hexdigest()
                if payload_hash not in seen_hashes:
                    seen_hashes.add(payload_hash)
                    return [{
                        "name": f"{Path(payload_name).stem}-Workbook.txt",
                        "type": "xls",
                        "text": rendered,
                        "depth": depth,
                    }]

        if olefile.isOleFile(payload):
            with olefile.OleFileIO(payload) as ole:
                if ole.exists(("WordDocument",)):
                    word_blob = ole.openstream(("WordDocument",)).read()
                    rendered_doc = _extract_doc_text_from_worddocument_stream(word_blob)
                    if rendered_doc:
                        payload_hash = hashlib.sha256(rendered_doc.encode("utf-8")).hexdigest()
                        if payload_hash not in seen_hashes:
                            seen_hashes.add(payload_hash)
                            return [{
                                "name": f"{Path(payload_name).stem}-WordDocument.txt",
                                "type": "doc",
                                "text": rendered_doc,
                                "depth": depth,
                            }]

        candidates = self._unwrap_payload_candidates(payload, payload_name)
        results: List[Dict[str, Any]] = []

        for candidate_name, candidate_bytes, candidate_type in candidates:
            if len(candidate_bytes) > self._max_attachment_size:
                raise ValueError(f"attachment-too-large:{candidate_name}")

            payload_hash = hashlib.sha256(candidate_bytes).hexdigest()
            if payload_hash in seen_hashes:
                continue
            seen_hashes.add(payload_hash)

            parsed = self._parse_callback(candidate_bytes, candidate_name, candidate_type, depth, seen_hashes)
            text = self._flatten_to_text(parsed)
            if text:
                results.append({
                    "name": candidate_name,
                    "type": candidate_type or self._infer_type(candidate_name, candidate_bytes),
                    "text": text,
                    "depth": depth,
                })

            for nested in parsed.get("attachments") or []:
                if isinstance(nested, dict) and nested.get("text"):
                    results.append(nested)

        return results

    def _unwrap_payload_candidates(self, payload: bytes, payload_name: str) -> List[Tuple[str, bytes, Optional[str]]]:
        inferred = self._infer_type(payload_name, payload)
        if inferred:
            return [(Path(payload_name).name, payload, inferred)]

        if olefile.isOleFile(payload):
            candidates = self._extract_from_ole(payload_name, payload)
            if candidates:
                return candidates

        raise ValueError(f"unsupported-embedded-payload:{payload_name}")

    def _extract_from_ole(self, payload_name: str, payload: bytes) -> List[Tuple[str, bytes, Optional[str]]]:
        results: List[Tuple[str, bytes, Optional[str]]] = []
        with olefile.OleFileIO(payload) as ole:
            for stream_path in self.OLE_NATIVE_STREAMS:
                if ole.exists(stream_path):
                    stream_leaf = stream_path[-1].replace("\x01", "").replace("\x03", "")
                    if stream_leaf == "WordDocument":
                        results.append((f"{Path(payload_name).stem}.doc", payload, "doc"))
                        continue
                    blob = ole.openstream(stream_path).read()
                    candidate_name = self._candidate_name_from_stream(payload_name, stream_path, blob)
                    candidate_type = self._infer_stream_type(stream_path, candidate_name, blob)
                    if candidate_type:
                        results.append((candidate_name, blob, candidate_type))

            if results:
                return results

            for entry in ole.listdir():
                name = "/".join(entry)
                if name.endswith("Workbook") or name.endswith("WordDocument"):
                    if name.endswith("WordDocument"):
                        results.append((f"{Path(payload_name).stem}.doc", payload, "doc"))
                        continue
                    blob = ole.openstream(entry).read()
                    candidate_name = self._candidate_name_from_stream(payload_name, tuple(entry), blob)
                    candidate_type = self._infer_stream_type(tuple(entry), candidate_name, blob)
                    if candidate_type:
                        results.append((candidate_name, blob, candidate_type))

        return results

    def _extract_xls_rows_from_ole(self, ole: olefile.OleFileIO) -> Dict[str, List[List[Any]]]:
        workbook_path = None
        for candidate in (("ObjectPool", "_1234567890", "Workbook"), ("Workbook",)):
            if ole.exists(candidate):
                workbook_path = candidate
                break
        if workbook_path is None:
            return {}

        try:
            import xlrd
        except Exception:
            return {}

        workbook_blob = ole.openstream(workbook_path).read()
        workbook = xlrd.open_workbook(file_contents=workbook_blob)
        data: Dict[str, List[List[Any]]] = {}
        for sheet in workbook.sheets():
            rows: List[List[Any]] = []
            for row_idx in range(sheet.nrows):
                row_values = sheet.row_values(row_idx)
                if any(cell is not None and str(cell).strip() != "" for cell in row_values):
                    rows.append(list(row_values))
            data[sheet.name] = rows
        return data

    def _candidate_name_from_stream(self, payload_name: str, stream_path: Tuple[str, ...], blob: bytes) -> str:
        stream_leaf = stream_path[-1].replace("\x01", "").replace("\x03", "") or "embedded"
        ext = self._extension_for_payload(blob)
        base_name = Path(payload_name).stem or "embedded"
        return f"{base_name}-{stream_leaf}{ext}"

    def _infer_stream_type(self, stream_path: Tuple[str, ...], candidate_name: str, blob: bytes) -> Optional[str]:
        stream_leaf = stream_path[-1].replace("\x01", "").replace("\x03", "")
        if stream_leaf == "Workbook":
            return None
        if stream_leaf == "WordDocument":
            return self._infer_type(candidate_name, blob)
        return self._infer_type(candidate_name, blob)

    def _extension_for_payload(self, payload: bytes) -> str:
        payload_type = self._infer_type("", payload)
        if payload_type == "doc":
            return ".doc"
        if payload_type == "docx":
            return ".docx"
        if payload_type == "xlsx":
            return ".xlsx"
        if payload_type == "pptx":
            return ".pptx"
        if payload_type == "pdf":
            return ".pdf"
        return ""

    def _infer_type(self, name: str, payload: bytes) -> Optional[str]:
        suffix = Path(name).suffix.lower().lstrip(".") if name else ""
        if suffix in self.SUPPORTED_TYPES:
            return suffix

        if payload.startswith(b"%PDF"):
            return "pdf"

        if payload.startswith(b"PK"):
            try:
                with zipfile.ZipFile(BytesIO(payload)) as archive:
                    members = set(archive.namelist())
            except zipfile.BadZipFile:
                return None
            if "word/document.xml" in members:
                return "docx"
            if "xl/workbook.xml" in members:
                return "xlsx"
            if "ppt/presentation.xml" in members:
                return "pptx"

        if payload.startswith(b"\xd0\xcf\x11\xe0"):
            return None

        return None

    def _flatten_to_text(self, parsed: Any) -> str:
        if isinstance(parsed, dict):
            if isinstance(parsed.get("paragraphs"), list):
                lines = [str(item.get("text") or "").strip() for item in parsed["paragraphs"] if isinstance(item, dict)]
                table_lines = []
                for table in parsed.get("tables") or []:
                    if not isinstance(table, dict):
                        continue
                    for row in table.get("data") or []:
                        if isinstance(row, list):
                            rendered = " | ".join(str(cell).strip() for cell in row if str(cell or "").strip())
                            if rendered:
                                table_lines.append(rendered)
                return "\n".join(line for line in lines + table_lines if line)

            if isinstance(parsed.get("pages"), list):
                return "\n".join(str(item.get("text") or "").strip() for item in parsed["pages"] if isinstance(item, dict) and str(item.get("text") or "").strip())

            if isinstance(parsed.get("slides"), list):
                return "\n".join(str(item.get("text") or "").strip() for item in parsed["slides"] if isinstance(item, dict) and str(item.get("text") or "").strip())

            if parsed and all(isinstance(v, list) for v in parsed.values()):
                rows: List[str] = []
                for value in parsed.values():
                    for row in value:
                        if isinstance(row, list):
                            text = " | ".join(str(cell).strip() for cell in row if str(cell or "").strip())
                            if text:
                                rows.append(text)
                return "\n".join(rows)

            if isinstance(parsed.get("text"), str):
                return str(parsed.get("text") or "").strip()

        return ""
