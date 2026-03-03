import pytest

from backend.utils import old_format_parser as parser


def test_xls_bytes_to_sheet_rows_fallbacks_to_xlrd_when_soffice_unavailable(monkeypatch):
    called = {"fallback": False}

    def fake_convert(*_args, **_kwargs):
        raise RuntimeError("旧格式解析工具不可用：soffice未安装")

    def fake_fallback(_file_content):
        called["fallback"] = True
        return {"sheet1": [["A", "B"], ["1", "2"]]}

    monkeypatch.setattr(parser, "xls_bytes_to_xlsx_bytes", fake_convert)
    monkeypatch.setattr(parser, "_xls_bytes_to_sheet_rows_with_xlrd", fake_fallback)

    data = parser.xls_bytes_to_sheet_rows(b"fake-xls", "sample.xls")
    assert called["fallback"] is True
    assert data == {"sheet1": [["A", "B"], ["1", "2"]]}


def test_xls_bytes_to_sheet_rows_raises_readable_error_when_both_parsers_unavailable(monkeypatch):
    def fake_convert(*_args, **_kwargs):
        raise RuntimeError("旧格式解析工具不可用：soffice未安装")

    def fake_fallback(_file_content):
        raise RuntimeError("旧格式解析工具不可用：xlrd未安装")

    monkeypatch.setattr(parser, "xls_bytes_to_xlsx_bytes", fake_convert)
    monkeypatch.setattr(parser, "_xls_bytes_to_sheet_rows_with_xlrd", fake_fallback)

    with pytest.raises(RuntimeError) as exc:
        parser.xls_bytes_to_sheet_rows(b"fake-xls", "sample.xls")

    assert "soffice未安装" in str(exc.value)
    assert "xlrd未安装" in str(exc.value)
