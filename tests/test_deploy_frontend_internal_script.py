import os
import subprocess
import textwrap
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT_DIR / "deploy-frontend-internal.sh"


def _run_bash(script: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        ["bash", "-lc", script],
        cwd=ROOT_DIR,
        env=merged_env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_deploy_frontend_script_validates_nginx_config_before_and_after_start():
    script_text = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "docker run --rm \\" in script_text
    assert "nginx:latest nginx -t" in script_text
    assert "docker exec requirement-frontend nginx -t" in script_text


def test_deploy_frontend_script_supports_external_backend_upstream_rendering():
    script_text = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "FRONTEND_BACKEND_UPSTREAM" in script_text
    assert "nginx.internal.runtime.conf" in script_text
    assert "proxy_pass http://${BACKEND_UPSTREAM};" in script_text
    assert "FRONTEND_NGINX_CONF" in script_text


def test_frontend_internal_compose_supports_runtime_nginx_conf_mount():
    compose_text = (ROOT_DIR / "docker-compose.frontend.internal.yml").read_text(encoding="utf-8")
    assert "${FRONTEND_NGINX_CONF:-./frontend/nginx.internal.conf}" in compose_text


def test_frontend_internal_compose_exposes_https_and_mounts_ssl_dir():
    compose_text = (ROOT_DIR / "docker-compose.frontend.internal.yml").read_text(encoding="utf-8")

    assert '"443:443"' in compose_text
    assert "${FRONTEND_SSL_DIR:-./frontend/ssl}:/etc/nginx/ssl:ro" in compose_text


def test_deploy_frontend_script_checks_ssl_prerequisites_and_https_health():
    script_text = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "FRONTEND_SSL_DIR" in script_text
    assert "cert.pem" in script_text
    assert "key.pem" in script_text
    assert "ss -ltn" in script_text
    assert ":443" in script_text
    assert "curl -k -f https://localhost:443" in script_text


def test_deploy_frontend_script_generates_self_signed_cert_with_requested_ip_sans(tmp_path):
    ssl_dir = tmp_path / "ssl"
    ssl_dir.mkdir()

    command = textwrap.dedent(
        f"""
        set -e
        export PROJECT_DIR="{ROOT_DIR}"
        export FRONTEND_SSL_DIR="{ssl_dir}"
        export FRONTEND_CERT_IPS="8.153.194.178,10.62.16.251"
        source "{SCRIPT_PATH}"
        ensure_https_certificate_materials
        openssl x509 -in "{ssl_dir / 'cert.pem'}" -noout -text
        """
    )

    result = _run_bash(command)

    assert result.returncode == 0, result.stderr
    assert "IP Address:8.153.194.178" in result.stdout
    assert "IP Address:10.62.16.251" in result.stdout


def test_deploy_frontend_script_keeps_existing_ssl_materials(tmp_path):
    ssl_dir = tmp_path / "ssl"
    ssl_dir.mkdir()
    cert_path = ssl_dir / "cert.pem"
    key_path = ssl_dir / "key.pem"
    cert_path.write_text("existing-cert", encoding="utf-8")
    key_path.write_text("existing-key", encoding="utf-8")

    command = textwrap.dedent(
        f"""
        set -e
        export PROJECT_DIR="{ROOT_DIR}"
        export FRONTEND_SSL_DIR="{ssl_dir}"
        export FRONTEND_CERT_IPS="8.153.194.178"
        source "{SCRIPT_PATH}"
        ensure_https_certificate_materials
        cat "{cert_path}"
        printf '\\n'
        cat "{key_path}"
        """
    )

    result = _run_bash(command)

    assert result.returncode == 0, result.stderr
    assert "existing-cert" in result.stdout
    assert "existing-key" in result.stdout
