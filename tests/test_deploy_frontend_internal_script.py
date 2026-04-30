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


def test_frontend_internal_compose_does_not_expose_https_or_mount_ssl_dir():
    compose_text = (ROOT_DIR / "docker-compose.frontend.internal.yml").read_text(encoding="utf-8")

    assert '"443:443"' not in compose_text
    assert "/etc/nginx/ssl" not in compose_text


def test_deploy_frontend_script_does_not_start_https_or_manage_certificates():
    script_text = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "FRONTEND_SSL_DIR" not in script_text
    assert "cert.pem" not in script_text
    assert "key.pem" not in script_text
    assert "check_https_prerequisites" not in script_text
    assert "ensure_https_certificate_materials" not in script_text
    assert "curl -k -f https://localhost:443" not in script_text


def test_deploy_frontend_script_reads_backend_upstream_from_env_frontend(tmp_path):
    project_dir = tmp_path / "project"
    frontend_dir = project_dir / "frontend"
    frontend_dir.mkdir(parents=True)
    (frontend_dir / "nginx.internal.conf").write_text(
        (ROOT_DIR / "frontend/nginx.internal.conf").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (project_dir / ".env.frontend").write_text(
        "FRONTEND_BACKEND_UPSTREAM=10.62.22.121:443\n",
        encoding="utf-8",
    )

    command = textwrap.dedent(
        f"""
        set -e
        export PROJECT_DIR="{project_dir}"
        source "{SCRIPT_PATH}"
        render_runtime_nginx_config
        grep 'proxy_pass' "$RUNTIME_NGINX_CONF"
        """
    )

    result = _run_bash(command)

    assert result.returncode == 0, result.stderr
    assert "proxy_pass http://10.62.22.121:443;" in result.stdout


def test_deploy_frontend_script_prefers_env_frontend_over_internal_env(tmp_path):
    project_dir = tmp_path / "project"
    frontend_dir = project_dir / "frontend"
    frontend_dir.mkdir(parents=True)
    (frontend_dir / "nginx.internal.conf").write_text(
        (ROOT_DIR / "frontend/nginx.internal.conf").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (project_dir / ".env.frontend").write_text(
        "FRONTEND_BACKEND_UPSTREAM=10.62.22.121:443\n",
        encoding="utf-8",
    )
    (project_dir / ".env.frontend.internal").write_text(
        "FRONTEND_BACKEND_UPSTREAM=10.62.22.122:443\n",
        encoding="utf-8",
    )

    command = textwrap.dedent(
        f"""
        set -e
        export PROJECT_DIR="{project_dir}"
        source "{SCRIPT_PATH}"
        render_runtime_nginx_config
        printf "%s" "$BACKEND_UPSTREAM"
        """
    )

    result = _run_bash(command)

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().endswith("10.62.22.121:443")
