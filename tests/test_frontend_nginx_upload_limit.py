from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]

NGINX_FILES = [
    ROOT_DIR / "frontend/nginx.conf",
    ROOT_DIR / "frontend/nginx.internal.conf",
    ROOT_DIR / "frontend/nginx-remote.conf",
]


def test_frontend_nginx_configs_set_api_upload_limit():
    for config_path in NGINX_FILES:
        text = config_path.read_text(encoding="utf-8")
        assert "client_max_body_size 50m;" in text, f"missing upload limit in {config_path.name}"
