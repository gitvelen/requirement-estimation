from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]


def test_deploy_frontend_script_validates_nginx_config_before_and_after_start():
    script_text = (ROOT_DIR / "deploy-frontend-internal.sh").read_text(encoding="utf-8")

    assert "docker run --rm \\" in script_text
    assert "nginx:latest nginx -t" in script_text
    assert "docker exec requirement-frontend nginx -t" in script_text


def test_deploy_frontend_script_supports_external_backend_upstream_rendering():
    script_text = (ROOT_DIR / "deploy-frontend-internal.sh").read_text(encoding="utf-8")

    assert "FRONTEND_BACKEND_UPSTREAM" in script_text
    assert "nginx.internal.runtime.conf" in script_text
    assert "proxy_pass http://${BACKEND_UPSTREAM};" in script_text
    assert "FRONTEND_NGINX_CONF" in script_text


def test_frontend_internal_compose_supports_runtime_nginx_conf_mount():
    compose_text = (ROOT_DIR / "docker-compose.frontend.internal.yml").read_text(encoding="utf-8")
    assert "${FRONTEND_NGINX_CONF:-./frontend/nginx.internal.conf}" in compose_text
