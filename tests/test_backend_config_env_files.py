from pathlib import Path

import pytest

from backend.config.config import Settings


def _parse_env_file(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        entries[key.strip()] = value.strip()
    return entries


@pytest.mark.parametrize("env_file_name", [".env.backend", ".env.backend.internal"])
def test_settings_reads_backend_env_file_variants(tmp_path, monkeypatch, env_file_name):
    for key in ("PORT", "REPORT_DIR", "UPLOAD_DIR", "EMBEDDING_DIM"):
        monkeypatch.delenv(key, raising=False)

    monkeypatch.chdir(tmp_path)
    (tmp_path / env_file_name).write_text(
        "\n".join(
            [
                "PORT=8444",
                "REPORT_DIR=custom_data",
                "UPLOAD_DIR=custom_uploads",
                "EMBEDDING_DIM=2048",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    settings = Settings()

    assert settings.PORT == 8444
    assert settings.REPORT_DIR == "custom_data"
    assert settings.UPLOAD_DIR == "custom_uploads"
    assert settings.EMBEDDING_DIM == 2048


def test_backend_env_example_covers_deploy_required_keys():
    env_entries = _parse_env_file(Path(".env.backend.example"))

    required_keys = {
        "DEBUG",
        "TZ",
        "ALLOWED_ORIGINS",
        "DASHSCOPE_API_BASE",
        "DASHSCOPE_API_KEY",
        "EMBEDDING_API_BASE",
        "EMBEDDING_API_STYLE",
        "EMBEDDING_MODEL",
        "KNOWLEDGE_ENABLED",
        "KNOWLEDGE_VECTOR_STORE",
        "LLM_MODEL",
        "LLM_MAX_CONTEXT_TOKENS",
        "LLM_INPUT_MAX_TOKENS",
        "ENABLE_LLM_CHUNKING",
        "PORT",
        "WORKERS",
        "MAX_UPLOAD_SIZE",
        "ALLOWED_EXTENSIONS",
        "JWT_SECRET",
        "JWT_EXPIRE_MINUTES",
        "ADMIN_API_KEY",
        "TASK_RETENTION_DAYS",
    }

    missing_keys = sorted(required_keys - set(env_entries))
    assert not missing_keys, f".env.backend.example 缺少键: {missing_keys}"

    assert env_entries["PORT"] == "443"
    assert env_entries["KNOWLEDGE_VECTOR_STORE"] == "local"
    assert env_entries["EMBEDDING_MODEL"] == "text-embedding-v2"
    assert env_entries["JWT_EXPIRE_MINUTES"] == "120"
    assert env_entries["TZ"] == "Asia/Shanghai"
    assert "10." in env_entries["ALLOWED_ORIGINS"] or "8." in env_entries["ALLOWED_ORIGINS"]
