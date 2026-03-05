from backend.api.system_profile_routes import _parsed_to_text


def test_parsed_to_text_extracts_docx_paragraphs_and_tables():
    parsed = {
        "paragraphs": [
            {"type": "paragraph", "text": "第四章 技术方案说明", "style": "Heading 1"},
            {"type": "paragraph", "text": "整体架构", "style": "Heading 2"},
        ],
        "tables": [
            {
                "type": "table",
                "data": [
                    ["组件", "说明"],
                    ["Redis", "缓存"],
                    ["MySQL", "数据库"],
                ],
            }
        ],
        "metadata": {"total_paragraphs": 2, "total_tables": 1},
    }

    text = _parsed_to_text(parsed)

    assert "第四章 技术方案说明" in text
    assert "整体架构" in text
    assert "Redis | 缓存" in text
    assert "MySQL | 数据库" in text
    assert "metadata" not in text
