from pathlib import Path
import re


REPO_ROOT = Path(__file__).resolve().parents[1]
PAGE_FILE = REPO_ROOT / "frontend/src/pages/SystemProfileImportPage.js"


def test_document_import_controls_use_single_toolbar_row() -> None:
    content = PAGE_FILE.read_text(encoding="utf-8")
    pattern = re.compile(
        r'<Card title="文档导入">[\s\S]*?<Space[^>]*wrap[^>]*>[\s\S]*?<Select[\s\S]*?<Upload[\s\S]*?>[\s\S]*?导入[\s\S]*?</Space>'
    )
    assert pattern.search(content), "文档导入的下拉/上传/导入按钮应位于同一行工具条中"
