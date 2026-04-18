import os
import sys

from docx import Document

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.utils.docx_parser import DocxParser


def test_parse_uses_first_non_header_table_cell_for_basic_info(tmp_path):
    document = Document()
    table = document.add_table(rows=3, cols=4)

    name_row = table.rows[0].cells
    name_row[0].text = "需求名称"
    name_row[1].text = "需求名称"
    name_row[2].text = "2026年管理会计集市系统中收模型优化等共计33个迭代优化需求"
    name_row[3].text = "2026年管理会计集市系统中收模型优化等共计33个迭代优化需求"

    summary_row = table.rows[1].cells
    summary_row[0].text = "需求概述"
    summary_row[1].text = "需求概述"
    summary_row[2].text = "针对经营分析与绩效考核要求，管会集市进行系统优化"
    summary_row[3].text = "针对经营分析与绩效考核要求，管会集市进行系统优化"

    content_row = table.rows[2].cells
    content_row[0].text = "需求功能要点描述"
    content_row[1].text = "需求功能要点描述"
    content_row[2].text = "管会集市从取分润补录表改为接入CRM业绩分润数据"
    content_row[3].text = "管会集市从取分润补录表改为接入CRM业绩分润数据"

    file_path = tmp_path / "sample.docx"
    document.save(file_path)

    result = DocxParser().parse(str(file_path))

    assert result["requirement_name"] == "2026年管理会计集市系统中收模型优化等共计33个迭代优化需求"
    assert result["requirement_summary"] == "针对经营分析与绩效考核要求，管会集市进行系统优化"
