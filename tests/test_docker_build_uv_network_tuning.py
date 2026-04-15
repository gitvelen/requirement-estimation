from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]


def test_docker_build_exposes_uv_network_tuning_args():
    dockerfile_text = (ROOT_DIR / "Dockerfile").read_text(encoding="utf-8")
    compose_text = (ROOT_DIR / "docker-compose.yml").read_text(encoding="utf-8")

    assert "ARG UV_HTTP_TIMEOUT=" in dockerfile_text
    assert "ENV UV_HTTP_TIMEOUT=${UV_HTTP_TIMEOUT}" in dockerfile_text
    assert "ARG UV_HTTP_RETRIES=" in dockerfile_text
    assert "ENV UV_HTTP_RETRIES=${UV_HTTP_RETRIES}" in dockerfile_text
    assert "UV_HTTP_TIMEOUT=${UV_HTTP_TIMEOUT:-120}" in compose_text
    assert "UV_HTTP_RETRIES=${UV_HTTP_RETRIES:-8}" in compose_text
