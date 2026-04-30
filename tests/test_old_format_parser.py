import pytest

from backend.utils import old_format_parser as parser


def test_doc_file_to_text_falls_back_to_commercial_aspose_package(monkeypatch):
    class FakeDocument:
        def __init__(self, input_path):
            self.input_path = input_path

        def get_text(self):
            return f"正文: {self.input_path}"

    def fake_import(name):
        if name == "aspose.words_foss":
            raise ModuleNotFoundError(name)
        if name == "aspose.words":
            return type("FakeAsposeWords", (), {"Document": FakeDocument})
        raise AssertionError(f"unexpected import: {name}")

    monkeypatch.setattr(parser.importlib, "import_module", fake_import)

    assert parser._doc_file_to_text("sample.doc") == "正文: sample.doc"


def test_doc_bytes_to_text_uses_python_doc_reader(monkeypatch, tmp_path):
    monkeypatch.setattr(parser.settings, "UPLOAD_DIR", str(tmp_path))
    captured = {}

    def fake_runner(input_path, _timeout_seconds):
        captured["path"] = input_path
        return "老式 Word 正文"

    monkeypatch.setattr(parser, "_run_doc_file_to_text", fake_runner, raising=False)

    text = parser.doc_bytes_to_text(parser.OLE_COMPOUND_FILE_SIGNATURE + b"fake-doc", "sample.doc")

    assert text == "老式 Word 正文"
    assert captured["path"].endswith("sample.doc")
    assert list((tmp_path / "_old_format_parse").iterdir()) == []


def test_doc_bytes_to_text_rejects_empty_text(monkeypatch, tmp_path):
    monkeypatch.setattr(parser.settings, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(parser, "_run_doc_file_to_text", lambda _path, _timeout: "  \n", raising=False)

    with pytest.raises(RuntimeError) as exc:
        parser.doc_bytes_to_text(parser.OLE_COMPOUND_FILE_SIGNATURE + b"fake-doc", "sample.doc")

    assert "未提取到文本" in str(exc.value)


def test_xls_bytes_to_sheet_rows_uses_xlrd_directly(monkeypatch):
    called = {"xlrd": False}

    def fake_xlrd(_file_content):
        called["xlrd"] = True
        return {"sheet1": [["A", "B"], ["1", "2"]]}

    monkeypatch.setattr(parser, "_xls_bytes_to_sheet_rows_with_xlrd", fake_xlrd)

    data = parser.xls_bytes_to_sheet_rows(b"fake-xls", "sample.xls")
    assert called["xlrd"] is True
    assert data == {"sheet1": [["A", "B"], ["1", "2"]]}


def test_soffice_conversion_helpers_are_removed():
    assert not hasattr(parser, "_run_soffice_convert")
    assert not hasattr(parser, "xls_bytes_to_xlsx_bytes")


def test_xls_bytes_to_sheet_rows_raises_readable_error_when_xlrd_unavailable(monkeypatch):
    def fake_xlrd(_file_content):
        raise RuntimeError("旧格式解析工具不可用：xlrd未安装")

    monkeypatch.setattr(parser, "_xls_bytes_to_sheet_rows_with_xlrd", fake_xlrd)

    with pytest.raises(RuntimeError) as exc:
        parser.xls_bytes_to_sheet_rows(b"fake-xls", "sample.xls")

    assert "xlrd未安装" in str(exc.value)
