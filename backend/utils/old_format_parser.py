"""
旧格式解析工具（.doc / .xls）

目标：满足 REQ-NF-007 的隔离/超时/清理要求，为多入口复用。

实现策略：
- 在隔离临时目录内写入上传文件副本
- 通过 headless libreoffice (soffice) 转换为 txt/xlsx（带超时）
- 解析成功/失败均清理临时目录
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.config.config import settings

logger = logging.getLogger(__name__)


def _get_timeout_seconds(override: Optional[int] = None) -> int:
    if override is not None:
        try:
            return max(1, int(override))
        except Exception:
            return 60
    try:
        value = int(os.getenv("OLD_FORMAT_PARSE_TIMEOUT_SECONDS", "60"))
    except Exception:
        value = 60
    return max(1, min(value, 600))


def _safe_stem(filename: str, default: str = "upload") -> str:
    text = str(filename or "").strip() or default
    text = os.path.basename(text.replace("\\", "/")).replace("\x00", "").strip()
    stem = os.path.splitext(text)[0].strip() or default
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._")
    return stem or default


def _old_format_tmp_root() -> str:
    root = os.path.join(str(settings.UPLOAD_DIR or "uploads"), "_old_format_parse")
    os.makedirs(root, exist_ok=True)
    return root


def _run_soffice_convert(*, input_path: str, outdir: str, convert_to: str, timeout_seconds: int) -> None:
    """
    Run libreoffice conversion in an isolated temp dir.

    convert_to examples:
      - "txt:Text"
      - "xlsx"
    """
    cmd = [
        "soffice",
        "--headless",
        "--nologo",
        "--nofirststartwizard",
        "--norestore",
        "--nolockcheck",
        "--convert-to",
        convert_to,
        "--outdir",
        outdir,
        input_path,
    ]

    env = os.environ.copy()
    env["HOME"] = outdir
    env["TMPDIR"] = outdir

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            timeout=timeout_seconds,
            check=False,
            text=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("旧格式解析工具不可用：soffice未安装") from exc
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError("旧格式解析超时") from exc

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        detail = stderr or stdout or f"returncode={result.returncode}"
        raise RuntimeError(f"旧格式解析失败: {detail[:200]}")


def doc_bytes_to_text(file_content: bytes, filename: str, *, timeout_seconds: Optional[int] = None) -> str:
    timeout = _get_timeout_seconds(timeout_seconds)
    stem = _safe_stem(filename, default="document")

    with tempfile.TemporaryDirectory(prefix="doc_", dir=_old_format_tmp_root()) as tmpdir:
        input_path = os.path.join(tmpdir, f"{stem}.doc")
        with open(input_path, "wb") as f:
            f.write(file_content or b"")

        _run_soffice_convert(
            input_path=input_path,
            outdir=tmpdir,
            convert_to="txt:Text",
            timeout_seconds=timeout,
        )

        output_path = os.path.join(tmpdir, f"{stem}.txt")
        if not os.path.exists(output_path):
            # fallback: find first txt
            txt_files = list(Path(tmpdir).glob("*.txt"))
            if txt_files:
                output_path = str(txt_files[0])

        if not os.path.exists(output_path):
            raise RuntimeError("旧格式解析失败: 未生成txt输出")

        with open(output_path, "r", encoding="utf-8", errors="ignore") as f:
            return (f.read() or "").strip()


def xls_bytes_to_xlsx_bytes(file_content: bytes, filename: str, *, timeout_seconds: Optional[int] = None) -> bytes:
    timeout = _get_timeout_seconds(timeout_seconds)
    stem = _safe_stem(filename, default="table")

    with tempfile.TemporaryDirectory(prefix="xls_", dir=_old_format_tmp_root()) as tmpdir:
        input_path = os.path.join(tmpdir, f"{stem}.xls")
        with open(input_path, "wb") as f:
            f.write(file_content or b"")

        _run_soffice_convert(
            input_path=input_path,
            outdir=tmpdir,
            convert_to="xlsx",
            timeout_seconds=timeout,
        )

        output_path = os.path.join(tmpdir, f"{stem}.xlsx")
        if not os.path.exists(output_path):
            xlsx_files = list(Path(tmpdir).glob("*.xlsx"))
            if xlsx_files:
                output_path = str(xlsx_files[0])

        if not os.path.exists(output_path):
            raise RuntimeError("旧格式解析失败: 未生成xlsx输出")

        with open(output_path, "rb") as f:
            return f.read()


def xlsx_bytes_to_sheet_rows(xlsx_bytes: bytes) -> Dict[str, List[List[Any]]]:
    try:
        from openpyxl import load_workbook
    except Exception as exc:
        raise RuntimeError("缺少Excel解析依赖 openpyxl") from exc

    from io import BytesIO

    wb = load_workbook(BytesIO(xlsx_bytes), data_only=True)
    data: Dict[str, List[List[Any]]] = {}
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        sheet_rows: List[List[Any]] = []
        for row in ws.iter_rows(values_only=True):
            if any(cell is not None and str(cell).strip() != "" for cell in row):
                sheet_rows.append(list(row))
        data[sheet_name] = sheet_rows
    return data


def xls_bytes_to_sheet_rows(file_content: bytes, filename: str, *, timeout_seconds: Optional[int] = None) -> Dict[str, List[List[Any]]]:
    xlsx_bytes = xls_bytes_to_xlsx_bytes(file_content, filename, timeout_seconds=timeout_seconds)
    return xlsx_bytes_to_sheet_rows(xlsx_bytes)


def sheet_rows_to_text(sheet_rows: Dict[str, List[List[Any]]], *, max_lines: int = 2000) -> str:
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


def xls_bytes_to_text(file_content: bytes, filename: str, *, timeout_seconds: Optional[int] = None) -> str:
    sheet_rows = xls_bytes_to_sheet_rows(file_content, filename, timeout_seconds=timeout_seconds)
    return sheet_rows_to_text(sheet_rows)
