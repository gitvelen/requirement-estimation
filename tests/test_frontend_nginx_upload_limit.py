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


def test_internal_nginx_config_defines_https_server_with_hsts():
    text = INTERNAL_NGINX_FILE.read_text(encoding="utf-8")

    assert "listen 443 ssl;" in text
    assert "ssl_certificate /etc/nginx/ssl/cert.pem;" in text
    assert "ssl_certificate_key /etc/nginx/ssl/key.pem;" in text
    assert 'add_header Strict-Transport-Security "max-age=16070400" always;' in text


def test_non_internal_nginx_configs_do_not_define_hsts():
    for config_path in NON_INTERNAL_NGINX_FILES:
        text = config_path.read_text(encoding="utf-8")
        assert "Strict-Transport-Security" not in text, f"unexpected HSTS in {config_path.name}"


def _extract_ssl_server_block(text: str) -> str:
    pattern = r"server\s*\{.*?listen\s+443\s+ssl;.*?\n\s*\}"
    match = re.search(pattern, text, re.S)
    assert match, "missing HTTPS server block"
    return match.group()


def test_internal_nginx_ssl_protocols_require_tls12_and_tls13():
    ssl_block = _extract_ssl_server_block(INTERNAL_NGINX_FILE.read_text(encoding="utf-8"))

    assert "ssl_protocols" in ssl_block, "missing ssl_protocols directive"
    assert "TLSv1.2" in ssl_block
    assert "TLSv1.3" in ssl_block


def test_internal_nginx_ssl_protocols_exclude_legacy_tls():
    ssl_block = _extract_ssl_server_block(INTERNAL_NGINX_FILE.read_text(encoding="utf-8"))

    for legacy in ["SSLv2", "SSLv3"]:
        assert legacy not in ssl_block, f"legacy protocol {legacy} should not be enabled"
    # TLSv1 without .2/.3 suffix = TLSv1.0
    for line in ssl_block.splitlines():
        stripped = line.strip()
        if stripped.startswith("ssl_protocols"):
            assert re.search(r"\bTLSv1\b(?!\.\d)", stripped) is None, "TLSv1.0 should not be in ssl_protocols"


def test_internal_nginx_ssl_ciphers_are_configured():
    ssl_block = _extract_ssl_server_block(INTERNAL_NGINX_FILE.read_text(encoding="utf-8"))

    assert "ssl_ciphers" in ssl_block, "missing ssl_ciphers directive"
    assert "ssl_prefer_server_ciphers on;" in ssl_block


def test_internal_nginx_https_server_block_has_hsts_at_server_level():
    ssl_block = _extract_ssl_server_block(INTERNAL_NGINX_FILE.read_text(encoding="utf-8"))

    hsts_line = 'add_header Strict-Transport-Security "max-age=16070400" always;'
    assert hsts_line in ssl_block, "HSTS missing in HTTPS server block"
