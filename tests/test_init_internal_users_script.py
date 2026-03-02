import json
import os
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]


def _read_users(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def test_init_script_bootstraps_users_without_pydantic_settings(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    blocker_dir = tmp_path / "blocker"
    blocker_dir.mkdir(parents=True, exist_ok=True)
    (blocker_dir / "sitecustomize.py").write_text(
        "import builtins\n"
        "_orig_import = builtins.__import__\n"
        "def _block_import(name, globals=None, locals=None, fromlist=(), level=0):\n"
        "    if name == 'pydantic_settings' or name.startswith('pydantic_settings.'):\n"
        "        raise ModuleNotFoundError(\"No module named 'pydantic_settings'\")\n"
        "    return _orig_import(name, globals, locals, fromlist, level)\n"
        "builtins.__import__ = _block_import\n",
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["PYTHONPATH"] = (
        f"{blocker_dir}{os.pathsep}{env['PYTHONPATH']}"
        if env.get("PYTHONPATH")
        else str(blocker_dir)
    )

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT_DIR / "scripts" / "init_internal_users.py"),
            "--data-dir",
            str(data_dir),
        ],
        cwd=str(ROOT_DIR),
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, (
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}\n"
    )

    users_path = data_dir / "users.json"
    assert users_path.exists()

    users = _read_users(users_path)
    by_username = {item.get("username"): item for item in users}
    assert {"admin", "manager", "expert1", "expert2", "expert3"} <= set(by_username.keys())
