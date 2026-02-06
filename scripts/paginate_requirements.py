#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deterministic "page number" calculator for docs/requirements.md.

Why:
- Markdown has no inherent pagination.
- The requirements master document needs stable page numbers in the change-log table.
- This script defines a fixed, reproducible pagination rule (monospace-like layout)
  so the page numbers are stable as long as earlier content isn't edited.

Rule (defaults):
- Visual width per line: 110 columns (CJK wide chars count as 2).
- Lines per page: 45.
- Lines are wrapped by visual width; blank lines count as 1 line.

Usage:
  python scripts/paginate_requirements.py docs/requirements.md
  python scripts/paginate_requirements.py docs/requirements.md --show-pages
"""

from __future__ import annotations

import argparse
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


VERSION_HEADING_RE = re.compile(
    r"^##\s+(?:=+\s+)?需求版本\s+(v\d+(?:\.\d+)?)\b"
)


def _char_width(ch: str) -> int:
    # Keep this deterministic and stdlib-only.
    if ch == "\t":
        return 4
    if unicodedata.combining(ch):
        return 0
    eaw = unicodedata.east_asian_width(ch)
    if eaw in ("W", "F"):
        return 2
    if eaw == "A":
        # Ambiguous width; treat as wide to match common CJK fonts.
        return 2
    return 1


def _visual_width(s: str) -> int:
    return sum(_char_width(ch) for ch in s)


def _wrap_by_width(line: str, width: int) -> list[str]:
    if line == "":
        return [""]

    parts: list[str] = []
    buf: list[str] = []
    buf_w = 0

    for ch in line:
        ch_w = _char_width(ch)
        if buf and buf_w + ch_w > width:
            parts.append("".join(buf))
            buf = [ch]
            buf_w = ch_w
            continue
        buf.append(ch)
        buf_w += ch_w

    if buf:
        parts.append("".join(buf))
    return parts or [""]


@dataclass(frozen=True)
class PaginationConfig:
    wrap_width: int = 110
    lines_per_page: int = 45


def iter_visual_lines(raw_lines: Iterable[str], cfg: PaginationConfig) -> Iterable[str]:
    for raw in raw_lines:
        line = raw.rstrip("\n")
        for wrapped in _wrap_by_width(line, cfg.wrap_width):
            yield wrapped


def calc_version_start_pages(md_path: Path, cfg: PaginationConfig) -> dict[str, int]:
    """
    Returns { "v1.0": 1, "v2.0": 3, ... } where the number is 1-based page index.
    """
    raw_lines = md_path.read_text(encoding="utf-8").splitlines(True)

    pages: dict[str, int] = {}
    visual_line_index = 0  # 0-based

    for raw in raw_lines:
        m = VERSION_HEADING_RE.match(raw.rstrip("\n"))
        if m:
            version = m.group(1)
            # Page number for the heading line (first wrapped segment).
            page = visual_line_index // cfg.lines_per_page + 1
            pages.setdefault(version, page)

        # Advance visual lines for this raw line.
        visual_line_index += len(_wrap_by_width(raw.rstrip("\n"), cfg.wrap_width))

    return pages


def calc_total_pages(md_path: Path, cfg: PaginationConfig) -> int:
    raw_lines = md_path.read_text(encoding="utf-8").splitlines(True)
    visual_lines = 0
    for raw in raw_lines:
        visual_lines += len(_wrap_by_width(raw.rstrip("\n"), cfg.wrap_width))
    return (max(visual_lines - 1, 0) // cfg.lines_per_page) + 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("md", type=Path, help="Path to requirements markdown")
    parser.add_argument("--wrap-width", type=int, default=110)
    parser.add_argument("--lines-per-page", type=int, default=45)
    parser.add_argument(
        "--show-pages",
        action="store_true",
        help="Print per-version start pages and total pages",
    )
    args = parser.parse_args()

    cfg = PaginationConfig(wrap_width=args.wrap_width, lines_per_page=args.lines_per_page)

    pages = calc_version_start_pages(args.md, cfg)
    total = calc_total_pages(args.md, cfg)

    if args.show_pages:
        print(f"file: {args.md}")
        print(f"rule: wrap_width={cfg.wrap_width}, lines_per_page={cfg.lines_per_page}")
        for k in sorted(pages.keys()):
            print(f"{k}: P{pages[k]}")
        print(f"total: {total} pages")
    else:
        # Default output is minimal and machine-friendly.
        for k in sorted(pages.keys()):
            print(f"{k}\tP{pages[k]}")
        print(f"total\t{total}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

