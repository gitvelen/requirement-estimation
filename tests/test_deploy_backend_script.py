from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]


def test_deploy_backend_script_rejects_placeholder_key_for_public_dashscope():
    script_text = (ROOT_DIR / "deploy-backend.sh").read_text(encoding="utf-8")

    assert "DASHSCOPE_API_BASE" in script_text
    assert "dashscope.aliyuncs.com" in script_text
    assert "not-needed" in script_text
    assert "公网 DashScope" in script_text


def test_standalone_compose_files_share_app_network():
    backend_compose = (ROOT_DIR / "docker-compose.backend.yml").read_text(encoding="utf-8")
    frontend_compose = (ROOT_DIR / "docker-compose.frontend.yml").read_text(encoding="utf-8")

    assert "networks:" in backend_compose
    assert "- app-network" in backend_compose
    assert "app-network:" in backend_compose

    assert "networks:" in frontend_compose
    assert "- app-network" in frontend_compose
    assert "app-network:" in frontend_compose
