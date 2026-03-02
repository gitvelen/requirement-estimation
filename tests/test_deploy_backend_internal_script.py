from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]


def test_deploy_script_initializes_users_in_container_without_host_python():
    script_text = (ROOT_DIR / "deploy-backend-internal.sh").read_text(encoding="utf-8")

    assert "command -v python3" not in script_text
    assert "python3 scripts/init_internal_users.py --data-dir data" not in script_text
    assert "docker-compose -f docker-compose.backend.internal.yml run --rm --no-deps backend \\" in script_text
    assert "python scripts/init_internal_users.py --data-dir /app/data" in script_text
