from pathlib import Path
import re


REPO_ROOT = Path(__file__).resolve().parents[1]
PAGE_FILE = REPO_ROOT / "frontend/src/pages/SystemProfileImportPage.js"


def test_document_import_controls_use_single_toolbar_row() -> None:
    content = PAGE_FILE.read_text(encoding="utf-8")
    assert '<Card title="文档导入">' in content, "文档导入应保留单一入口卡片"
    assert "统一入口批量上传文档" in content, "文档导入卡片应说明统一批量上传策略"
    assert "选择文档文件" in content, "文档导入卡片应提供文件选择按钮"
    assert "批量导入文档" in content, "文档导入卡片应提供批量导入按钮"
    assert "<Select" not in content, "v2.4 导入页不应再依赖单一 Select 切换文档类型"
