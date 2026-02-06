import os
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from fastapi.testclient import TestClient

from backend.app import app
from backend.config.config import settings
from backend.service import user_service
from backend.api import routes as task_routes
from backend.api import notification_routes
from backend.api import profile_routes
from backend.service import ai_effect_service


DEMO_DATA_DIR = BASE_DIR / "data" / "v4_demo"
DEMO_UPLOAD_DIR = BASE_DIR / "uploads" / "v4_demo"


def _reset_paths():
    DEMO_DATA_DIR.mkdir(parents=True, exist_ok=True)
    DEMO_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    settings.REPORT_DIR = str(DEMO_DATA_DIR)
    settings.UPLOAD_DIR = str(DEMO_UPLOAD_DIR)

    user_service.USER_STORE_PATH = str(DEMO_DATA_DIR / "users.json")
    user_service.USER_STORE_LOCK_PATH = str(DEMO_DATA_DIR / "users.json.lock")

    task_routes.TASK_STORE_PATH = str(DEMO_DATA_DIR / "task_storage.json")
    task_routes.TASK_STORE_LOCK_PATH = str(DEMO_DATA_DIR / "task_storage.json.lock")

    notification_routes.NOTIFY_STORE_PATH = str(DEMO_DATA_DIR / "notifications.json")
    notification_routes.NOTIFY_STORE_LOCK_PATH = str(DEMO_DATA_DIR / "notifications.json.lock")

    profile_routes.ACTIVITY_STORE_PATH = str(DEMO_DATA_DIR / "activity_logs.json")
    profile_routes.ACTIVITY_STORE_LOCK_PATH = str(DEMO_DATA_DIR / "activity_logs.json.lock")

    ai_effect_service.SNAPSHOT_PATH = str(DEMO_DATA_DIR / "ai_effect_snapshots.json")
    ai_effect_service.SNAPSHOT_LOCK_PATH = str(DEMO_DATA_DIR / "ai_effect_snapshots.json.lock")


def _seed_user(username: str, password: str, roles):
    user = user_service.create_user_record({
        "username": username,
        "display_name": username,
        "password": password,
        "roles": roles,
    })
    with user_service.user_storage_context() as users:
        users.append(user)
    return user


def _login(client: TestClient, username: str, password: str) -> str:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    if response.status_code != 200:
        raise RuntimeError(f"login failed: {response.text}")
    return response.json()["data"]["token"]


def _seed_task(manager_id: str, manager_name: str, expert_assignments):
    features = [
        {
            "id": "feat_a",
            "序号": "1.1",
            "功能模块": "账户管理",
            "功能点": "开立账户",
            "业务描述": "开户与开户校验",
            "输入": "客户信息",
            "输出": "开户结果",
            "依赖": "核心系统",
            "预估人天": 2.0,
            "复杂度": "中",
            "备注": "",
            "aiEstimatedDays": 2.0,
        },
        {
            "id": "feat_b",
            "序号": "1.2",
            "功能模块": "额度管理",
            "功能点": "额度同步",
            "业务描述": "对接ESB同步额度",
            "输入": "额度变更",
            "输出": "同步结果",
            "依赖": "ESB",
            "预估人天": 3.0,
            "复杂度": "中",
            "备注": "",
            "aiEstimatedDays": 3.0,
        },
    ]

    task = {
        "task_id": "task_v4_demo",
        "name": "V4试点验收演练",
        "creator_id": manager_id,
        "creator_name": manager_name,
        "status": "completed",
        "ai_status": "completed",
        "progress": 100,
        "message": "评估完成",
        "created_at": datetime.now().isoformat(),
        "workflow_status": "evaluating",
        "current_round": 1,
        "max_rounds": 2,
        "expert_assignments": expert_assignments,
        "systems_data": {"系统A": features},
    }

    with task_routes._task_storage_context() as data:
        data[task["task_id"]] = task

    return task["task_id"]


def main():
    os.environ.setdefault("EMBEDDING_FALLBACK", "1")
    _reset_paths()

    manager = _seed_user("manager_demo", "manager_demo", ["manager"])
    expert1 = _seed_user("expert_demo_1", "expert_demo", ["expert"])
    expert2 = _seed_user("expert_demo_2", "expert_demo", ["expert"])

    assignments = [
        {
            "assignment_id": "assign_1",
            "expert_id": expert1["id"],
            "expert_name": expert1["display_name"],
            "invite_token": "token_demo_1",
            "status": "invited",
            "created_at": datetime.now().isoformat(),
            "round_submissions": {},
        },
        {
            "assignment_id": "assign_2",
            "expert_id": expert2["id"],
            "expert_name": expert2["display_name"],
            "invite_token": "token_demo_2",
            "status": "invited",
            "created_at": datetime.now().isoformat(),
            "round_submissions": {},
        },
    ]

    task_id = _seed_task(manager["id"], manager["display_name"], assignments)

    client = TestClient(app)

    token1 = _login(client, "expert_demo_1", "expert_demo")
    token2 = _login(client, "expert_demo_2", "expert_demo")

    payload = {
        "round": 1,
        "evaluations": {
            "feat_a": 2.0,
            "feat_b": 3.0,
        },
    }

    resp1 = client.post(
        f"/api/v1/evaluation/{task_id}/submit",
        params={"token": "token_demo_1"},
        headers={"Authorization": f"Bearer {token1}"},
        json=payload,
    )
    if resp1.status_code != 200:
        raise RuntimeError(f"expert1 submit failed: {resp1.text}")

    resp2 = client.post(
        f"/api/v1/evaluation/{task_id}/submit",
        params={"token": "token_demo_2"},
        headers={"Authorization": f"Bearer {token2}"},
        json=payload,
    )
    if resp2.status_code != 200:
        raise RuntimeError(f"expert2 submit failed: {resp2.text}")

    with task_routes._task_storage_context() as data:
        task = data.get(task_id) or {}

    report_versions = task.get("report_versions") or []
    expert_final = task.get("expert_final") or {}

    output = {
        "task_id": task_id,
        "workflow_status": task.get("workflow_status"),
        "report_versions": report_versions,
        "expert_final": expert_final,
    }

    (DEMO_DATA_DIR / "v4_demo_result.json").write_text(
        __import__("json").dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
