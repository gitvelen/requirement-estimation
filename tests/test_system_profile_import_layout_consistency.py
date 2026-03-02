from pathlib import Path
import re


REPO_ROOT = Path(__file__).resolve().parents[1]
PAGE_FILE = REPO_ROOT / "frontend/src/pages/SystemProfileImportPage.js"


def test_document_import_controls_use_single_toolbar_row() -> None:
    content = PAGE_FILE.read_text(encoding="utf-8")
    card_pattern = re.compile(
        r"const renderDocTypeCard = \(config\) => \{[\s\S]*?<Card[\s\S]*?<Upload[\s\S]*?导入[\s\S]*?</Card>"
    )
    assert card_pattern.search(content), "文档导入应为每类文档独立 Card，且每个 Card 内含上传与导入操作"
    assert "DOC_TYPE_CONFIGS.map((config) => renderDocTypeCard(config))" in content, "文档导入应按文档类型渲染独立 Card"
    assert "<Select" not in content, "v2.4 导入页不应再依赖单一 Select 切换文档类型"
