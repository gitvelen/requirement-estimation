"""
PDF report generator with Unicode font support (reportlab).
Falls back to a minimal PDF writer if reportlab is unavailable.
"""
from typing import List, Tuple, Dict, Any
import os

REPORTLAB_AVAILABLE = False
try:
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False


def _escape_pdf_text(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
    )


def _to_latin1(text: str) -> str:
    return text.encode("latin-1", "replace").decode("latin-1")


def _find_font_path() -> str:
    env_path = os.getenv("PDF_FONT_PATH")
    if env_path and os.path.exists(env_path):
        return env_path

    candidates = [
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJKsc-Regular.otf",
        "/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/arphic/ukai.ttc",
        "/usr/share/fonts/truetype/arphic/uming.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return ""


def _select_font() -> Tuple[str, int, Dict[str, Any]]:
    font_size = 10
    if not REPORTLAB_AVAILABLE:
        return "Helvetica", font_size, {"source": "fallback"}

    font_path = _find_font_path()
    if font_path:
        font_name = "CJKFont"
        if font_name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(font_name, font_path))
        return font_name, font_size, {"source": "path", "path": font_path}

    try:
        font_name = "STSong-Light"
        if font_name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(UnicodeCIDFont(font_name))
        return font_name, font_size, {"source": "cid"}
    except Exception:
        return "Helvetica", font_size, {"source": "fallback"}


def get_font_info() -> Dict[str, Any]:
    if not REPORTLAB_AVAILABLE:
        return {
            "reportlab_available": False,
            "font_name": "Helvetica",
            "font_size": 10,
            "source": "fallback",
            "font_path": ""
        }

    font_name, font_size, meta = _select_font()
    return {
        "reportlab_available": True,
        "font_name": font_name,
        "font_size": font_size,
        "source": meta.get("source"),
        "font_path": meta.get("path", "")
    }


def _wrap_line(text: str, max_width: float, font_name: str, font_size: int) -> List[str]:
    if not REPORTLAB_AVAILABLE:
        return [text]
    if not text:
        return [""]

    lines = []
    current = ""
    for ch in text:
        trial = current + ch
        if pdfmetrics.stringWidth(trial, font_name, font_size) <= max_width:
            current = trial
        else:
            lines.append(current)
            current = ch
    if current:
        lines.append(current)
    return lines


def _write_with_reportlab(lines: List[str], path: str) -> None:
    font_name, font_size, _ = _select_font()
    page_width, page_height = A4
    left_margin = 40
    top = page_height - 40
    line_height = font_size + 4

    c = canvas.Canvas(path, pagesize=A4)
    c.setFont(font_name, font_size)
    y = top
    max_width = page_width - left_margin * 2

    for line in lines:
        wrapped = _wrap_line(line, max_width, font_name, font_size)
        for item in wrapped:
            if y < 40:
                c.showPage()
                c.setFont(font_name, font_size)
                y = top
            c.drawString(left_margin, y, item)
            y -= line_height

    c.save()


def _write_minimal_pdf(lines: List[str], path: str) -> None:
    page_width = 595
    page_height = 842
    left_margin = 40
    top = page_height - 40
    line_height = 14

    content_lines = []
    y = top
    for line in lines:
        if y < 40:
            break
        safe_line = _to_latin1(line)
        content_lines.append(
            f"BT /F1 10 Tf {left_margin} {y} Td ({_escape_pdf_text(safe_line)}) Tj ET"
        )
        y -= line_height

    content_stream = "\n".join(content_lines)
    content_bytes = content_stream.encode("latin-1", "replace")
    length = len(content_bytes)

    objects = []
    objects.append("1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj")
    objects.append("2 0 obj << /Type /Pages /Count 1 /Kids [3 0 R] >> endobj")
    objects.append(
        f"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 {page_width} {page_height}] "
        f"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >> endobj"
    )
    objects.append(
        "4 0 obj << /Length %d >> stream\n%s\nendstream endobj" % (length, content_stream)
    )
    objects.append("5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj")

    pdf = "%PDF-1.4\n"
    offsets = []
    for obj in objects:
        offsets.append(len(pdf))
        pdf += obj + "\n"

    xref_offset = len(pdf)
    pdf += f"xref\n0 {len(objects)+1}\n"
    pdf += "0000000000 65535 f \n"
    for offset in offsets:
        pdf += f"{offset:010d} 00000 n \n"
    pdf += f"trailer << /Size {len(objects)+1} /Root 1 0 R >>\n"
    pdf += f"startxref\n{xref_offset}\n%%EOF"

    with open(path, "wb") as f:
        f.write(pdf.encode("latin-1", "replace"))


def write_simple_pdf(lines: List[str], path: str) -> None:
    if REPORTLAB_AVAILABLE:
        _write_with_reportlab(lines, path)
    else:
        _write_minimal_pdf(lines, path)


def write_report_pdf(meta_lines: List[str], headers: List[str], rows: List[List[str]], path: str) -> None:
    if not REPORTLAB_AVAILABLE:
        fallback_lines = meta_lines + [""] + [" | ".join(headers)] + [" | ".join(row) for row in rows]
        _write_minimal_pdf(fallback_lines, path)
        return

    font_name, font_size, _ = _select_font()
    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    normal.fontName = font_name
    normal.fontSize = font_size
    normal.leading = font_size + 4

    elements = []
    for line in meta_lines:
        if not line:
            elements.append(Spacer(1, 8))
        else:
            elements.append(Paragraph(line, normal))
    elements.append(Spacer(1, 12))

    table_data = [[Paragraph(str(cell) if cell is not None else "", normal) for cell in headers]]
    for row in rows:
        table_data.append([Paragraph(str(cell) if cell is not None else "", normal) for cell in row])

    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f5f5f5")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#222222")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))

    doc = SimpleDocTemplate(
        path,
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    doc.build(elements + [table])
