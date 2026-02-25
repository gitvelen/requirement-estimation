from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]

REQ001_PAGES = [
    "frontend/src/pages/TaskListPage.js",
    "frontend/src/pages/SystemListConfigPage.js",
    "frontend/src/pages/CosmicConfigPage.js",
    "frontend/src/pages/UserManagementPage.js",
    "frontend/src/pages/KnowledgePage.js",
    "frontend/src/pages/SystemProfileImportPage.js",
    "frontend/src/pages/SystemProfileBoardPage.js",
    "frontend/src/pages/NotificationPage.js",
]


@pytest.mark.parametrize("page_path", REQ001_PAGES)
def test_req001_pages_do_not_use_page_header(page_path: str) -> None:
    page_file = REPO_ROOT / page_path
    assert page_file.exists(), f"页面文件不存在: {page_path}"
    content = page_file.read_text(encoding="utf-8")
    assert "PageHeader" not in content, f"{page_path} 仍包含 PageHeader，未满足 REQ-001"
