from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]


def test_internal_zip_deploy_script_safely_updates_project_dir():
    script_text = (ROOT_DIR / "deploy-internal-from-github-zip.sh").read_text(encoding="utf-8")

    assert "ZIP_PATH=\"${1:-/home/admin/requirement-estimation-main.zip}\"" in script_text
    assert "unzip -q \"$ZIP_PATH\"" in script_text
    assert "-name deploy-backend-internal.sh" in script_text
    assert "require_root" in script_text
    assert "EUID" in script_text
    assert "sudo" in script_text

    assert "runtime_has_data" in script_text
    assert "backup_runtime_dirs" in script_text
    assert ".deploy-backups" in script_text
    assert "rm -rf \"$RELEASE_DIR/data\" \"$RELEASE_DIR/uploads\" \"$RELEASE_DIR/logs\" \"$RELEASE_DIR/.deploy-backups\"" in script_text
    assert "! -name data" in script_text
    assert "! -name uploads" in script_text
    assert "! -name logs" in script_text

    assert "bash deploy-backend-internal.sh" in script_text
    assert "DEPLOY_BACKEND" in script_text
    assert "DEPLOY_FRONTEND" in script_text
    assert "/home/admin/frontend-build.tar.gz" in script_text
    assert "bash deploy-frontend-internal.sh" in script_text
