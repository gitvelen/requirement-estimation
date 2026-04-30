import re
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]

NGINX_FILES = [
    ROOT_DIR / "frontend/nginx.conf",
    ROOT_DIR / "frontend/nginx.internal.conf",
    ROOT_DIR / "frontend/nginx-remote.conf",
]
INTERNAL_NGINX_FILE = ROOT_DIR / "frontend/nginx.internal.conf"
NON_INTERNAL_NGINX_FILES = [
    ROOT_DIR / "frontend/nginx.conf",
    ROOT_DIR / "frontend/nginx-remote.conf",
]

STATIC_SECURITY_HEADERS = {
    "X-XSS-Protection": "1; mode=block",
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
}


def _extract_location_block(text: str, location: str) -> str:
    pattern = rf"location {re.escape(location)} \{{(?P<body>.*?)\n\s*\}}"
    match = re.search(pattern, text, re.S)
    assert match, f"missing location block for {location}"
    return match.group("body")


def test_frontend_nginx_configs_set_api_upload_limit():
    for config_path in NGINX_FILES:
        text = config_path.read_text(encoding="utf-8")
        assert "client_max_body_size 50m;" in text, f"missing upload limit in {config_path.name}"


def test_frontend_nginx_configs_set_static_security_headers():
    for config_path in NGINX_FILES:
        text = config_path.read_text(encoding="utf-8")
        for header_name, header_value in STATIC_SECURITY_HEADERS.items():
            expected_line = f'add_header {header_name} "{header_value}" always;'
            assert text.count(expected_line) >= 2, f"missing page/static header {header_name} in {config_path.name}"


def test_frontend_nginx_api_proxy_does_not_duplicate_backend_security_headers():
    for config_path in NGINX_FILES:
        text = config_path.read_text(encoding="utf-8")
        api_block = _extract_location_block(text, "/api/")
        for header_name in STATIC_SECURITY_HEADERS:
            assert header_name not in api_block, f"/api/ block should not add {header_name} in {config_path.name}"


def test_internal_nginx_config_defines_http_hsts_and_no_https_server():
    text = INTERNAL_NGINX_FILE.read_text(encoding="utf-8")

    assert "listen 80;" in text
    assert "listen 443" not in text
    assert "ssl_certificate" not in text
    assert "ssl_certificate_key" not in text
    assert text.count('add_header Strict-Transport-Security "max-age=16070400" always;') >= 2


def test_non_internal_nginx_configs_do_not_define_hsts():
    for config_path in NON_INTERNAL_NGINX_FILES:
        text = config_path.read_text(encoding="utf-8")
        assert "Strict-Transport-Security" not in text, f"unexpected HSTS in {config_path.name}"


def test_internal_nginx_static_assets_keep_hsts_when_cache_header_is_set():
    text = INTERNAL_NGINX_FILE.read_text(encoding="utf-8")
    match = re.search(r"location ~\* .*?\{\n(?P<body>.*?)\n\s*\}", text, re.S)
    assert match, "missing static assets location block"
    static_block = match.group("body")

    assert 'add_header Cache-Control "public, immutable";' in static_block
    assert 'add_header Strict-Transport-Security "max-age=16070400" always;' in static_block
