from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]


def test_deploy_script_initializes_users_in_container_without_host_python():
    script_text = (ROOT_DIR / "deploy-backend-internal.sh").read_text(encoding="utf-8")

    assert "command -v python3" not in script_text
    assert "python3 scripts/init_internal_users.py --data-dir data" not in script_text
    assert (
        "docker-compose -f docker-compose.backend.internal.yml run --rm --no-deps backend \\" in script_text
        or "docker-compose -f \"$COMPOSE_FILE\" run --rm --no-deps backend \\" in script_text
    )
    assert "python scripts/init_internal_users.py --data-dir /app/data" in script_text


def test_deploy_script_validates_llm_env_keys_and_runtime_injection():
    script_text = (ROOT_DIR / "deploy-backend-internal.sh").read_text(encoding="utf-8")

    assert (
        "required_env_keys=("
        "\"DASHSCOPE_API_KEY\" \"DASHSCOPE_API_BASE\" "
        "\"EMBEDDING_API_BASE\" \"EMBEDDING_MODEL\""
        ")"
    ) in script_text
    assert "grep -q \"^${key}=\"" in script_text
    assert "docker exec requirement-backend printenv DASHSCOPE_API_BASE" in script_text
    assert "docker exec requirement-backend printenv EMBEDDING_API_BASE" in script_text
