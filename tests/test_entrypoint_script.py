import os
import shlex
import subprocess
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]


def _prepare_uvicorn_command(*args: str, debug: str = "false", workers: str = "4") -> list[str]:
    shell_command = (
        f"source {shlex.quote(str(ROOT_DIR / 'entrypoint.sh'))}; "
        f"prepare_uvicorn_command {shlex.join(args)}"
    )
    completed = subprocess.run(
        ["bash", "-lc", shell_command],
        cwd=ROOT_DIR,
        check=True,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "ENTRYPOINT_SOURCE_ONLY": "1",
            "DEBUG": debug,
            "WORKERS": workers,
        },
    )
    return completed.stdout.strip().splitlines()


def test_prepare_uvicorn_command_adds_production_workers_when_missing():
    command = _prepare_uvicorn_command("uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "443")

    assert command == [
        "uvicorn",
        "backend.app:app",
        "--host",
        "0.0.0.0",
        "--port",
        "443",
        "--workers",
        "4",
        "--log-level",
        "info",
    ]


def test_prepare_uvicorn_command_preserves_explicit_workers():
    command = _prepare_uvicorn_command(
        "uvicorn",
        "backend.app:app",
        "--host",
        "0.0.0.0",
        "--port",
        "443",
        "--workers",
        "2",
    )

    assert command == [
        "uvicorn",
        "backend.app:app",
        "--host",
        "0.0.0.0",
        "--port",
        "443",
        "--workers",
        "2",
        "--log-level",
        "info",
    ]
