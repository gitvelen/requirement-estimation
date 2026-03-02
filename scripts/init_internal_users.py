#!/usr/bin/env python3
"""
初始化内网部署默认账号到 data/users.json。
"""
import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.service import user_service


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize internal default users.")
    parser.add_argument(
        "--data-dir",
        default=str(ROOT_DIR / "data"),
        help="Directory that contains users.json (default: ./data)",
    )
    parser.add_argument(
        "--preserve-password",
        action="store_true",
        help="Do not reset existing default users password to username.",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir).resolve()
    data_dir.mkdir(parents=True, exist_ok=True)

    users_path = data_dir / "users.json"
    user_service.USER_STORE_PATH = str(users_path)
    user_service.USER_STORE_LOCK_PATH = f"{users_path}.lock"

    summary = user_service.ensure_internal_default_users(force_reset_password=not args.preserve_password)
    print(
        "internal users initialized: "
        f"file={users_path}, created={summary['created']}, updated={summary['updated']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
