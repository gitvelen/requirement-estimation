import os
import sys
from datetime import datetime

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.config.config import settings
from backend.service import user_service
from backend.service import ai_effect_service
from backend.api import routes as task_routes
from backend.api import notification_routes
from backend.api import profile_routes


@pytest.fixture()
def client(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "REPORT_DIR", str(data_dir))

    monkeypatch.setattr(user_service, "USER_STORE_PATH", str(data_dir / "users.json"))
    monkeypatch.setattr(user_service, "USER_STORE_LOCK_PATH", str(data_dir / "users.json.lock"))

    monkeypatch.setattr(task_routes, "TASK_STORE_PATH", str(data_dir / "task_storage.json"))
    monkeypatch.setattr(task_routes, "TASK_STORE_LOCK_PATH", str(data_dir / "task_storage.json.lock"))

    monkeypatch.setattr(notification_routes, "NOTIFY_STORE_PATH", str(data_dir / "notifications.json"))
    monkeypatch.setattr(notification_routes, "NOTIFY_STORE_LOCK_PATH", str(data_dir / "notifications.json.lock"))

    monkeypatch.setattr(profile_routes, "ACTIVITY_STORE_PATH", str(data_dir / "activity_logs.json"))
    monkeypatch.setattr(profile_routes, "ACTIVITY_STORE_LOCK_PATH", str(data_dir / "activity_logs.json.lock"))

    monkeypatch.setattr(ai_effect_service, "SNAPSHOT_PATH", str(data_dir / "ai_effect_snapshots.json"))
    monkeypatch.setattr(ai_effect_service, "SNAPSHOT_LOCK_PATH", str(data_dir / "ai_effect_snapshots.json.lock"))

    return TestClient(app)


def seed_users():
    admin = user_service.create_user_record({
        "username": "admin",
        "display_name": "管理员",
        "password": "admin123",
        "roles": ["admin"],
    })
    manager = user_service.create_user_record({
        "username": "manager",
        "display_name": "经理",
        "password": "manager123",
        "roles": ["manager"],
    })
    manager_2 = user_service.create_user_record({
        "username": "manager2",
        "display_name": "经理二",
        "password": "manager234",
        "roles": ["manager"],
    })
    expert = user_service.create_user_record({
        "username": "expert",
        "display_name": "专家",
        "password": "expert123",
        "roles": ["expert"],
    })

    with user_service.user_storage_context() as users:
        users.extend([admin, manager, manager_2, expert])

    return admin, manager, manager_2, expert


def seed_experts():
    expert_1 = user_service.create_user_record({
        "username": "expert1",
        "display_name": "专家一",
        "password": "expert1",
        "roles": ["expert"],
    })
    expert_2 = user_service.create_user_record({
        "username": "expert2",
        "display_name": "专家二",
        "password": "expert2",
        "roles": ["expert"],
    })
    expert_3 = user_service.create_user_record({
        "username": "expert3",
        "display_name": "专家三",
        "password": "expert3",
        "roles": ["expert"],
    })
    with user_service.user_storage_context() as users:
        users.extend([expert_1, expert_2, expert_3])
    return expert_1, expert_2, expert_3


def login(client: TestClient, username: str, password: str) -> str:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["data"]["token"]


def seed_task(manager, expert, task_id="task_1"):
    feature_1 = {
        "id": "feat_1",
        "序号": 1,
        "功能模块": "账户管理",
        "功能点": "开立账户",
        "业务描述": "开户功能",
        "预估人天": 2,
    }
    feature_2 = {
        "id": "feat_2",
        "序号": 2,
        "功能模块": "账户管理",
        "功能点": "销户",
        "业务描述": "销户功能",
        "预估人天": 1,
    }
    task = {
        "task_id": task_id,
        "name": "测试任务",
        "description": "",
        "creator_id": manager["id"],
        "creator_name": manager["display_name"],
        "status": "completed",
        "ai_status": "completed",
        "progress": 100,
        "message": "评估完成",
        "created_at": datetime.now().isoformat(),
        "workflow_status": "evaluating",
        "current_round": 1,
        "max_rounds": 3,
        "expert_assignments": [
            {
                "id": "assign_1",
                "expert_id": expert["id"],
                "expert_name": expert["display_name"],
                "invite_token": "invite_token_1",
                "status": "invited",
                "round_submissions": {},
            }
        ],
        "evaluations": {},
        "evaluation_drafts": {},
        "report_versions": [],
        "round_feature_ids": {},
        "deviations": {},
        "round_means": {},
        "high_deviation_features": {},
        "systems_data": {"核心系统": [feature_1, feature_2]},
    }

    with task_routes._task_storage_context() as data:
        data[task_id] = task

    return task


def seed_task_with_assignments(manager, experts, task_id="task_multi"):
    feature_1 = {
        "id": "feat_a",
        "序号": 1,
        "功能模块": "账户管理",
        "功能点": "开立账户",
        "业务描述": "开户功能",
        "预估人天": 1,
    }
    feature_2 = {
        "id": "feat_b",
        "序号": 2,
        "功能模块": "账户管理",
        "功能点": "销户",
        "业务描述": "销户功能",
        "预估人天": 2,
    }
    assignments = []
    for idx, expert in enumerate(experts, start=1):
        assignments.append({
            "assignment_id": f"assign_{idx}",
            "expert_id": expert["id"],
            "expert_name": expert["display_name"],
            "invite_token": f"token_{idx}",
            "status": "invited",
            "created_at": datetime.now().isoformat(),
            "round_submissions": {},
        })

    task = {
        "task_id": task_id,
        "name": "多轮评估任务",
        "description": "",
        "creator_id": manager["id"],
        "creator_name": manager["display_name"],
        "status": "completed",
        "ai_status": "completed",
        "progress": 100,
        "message": "评估完成",
        "created_at": datetime.now().isoformat(),
        "workflow_status": "evaluating",
        "current_round": 1,
        "max_rounds": 3,
        "expert_assignments": assignments,
        "evaluations": {},
        "evaluation_drafts": {},
        "report_versions": [],
        "round_feature_ids": {},
        "deviations": {},
        "round_means": {},
        "high_deviation_features": {},
        "systems_data": {"核心系统": [feature_1, feature_2]},
    }

    with task_routes._task_storage_context() as data:
        data[task_id] = task

    return task


def test_ai_progress_access(client):
    admin, manager, _, expert = seed_users()
    task = seed_task(manager, expert, task_id="task_progress")

    admin_token = login(client, "admin", "admin123")
    manager_token = login(client, "manager", "manager123")
    expert_token = login(client, "expert", "expert123")

    for token in (admin_token, manager_token, expert_token):
        response = client.get(
            f"/api/v1/tasks/{task['task_id']}/ai-progress",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["progress"] == 100
        assert data["aiStatus"] == "completed"


def test_notification_filtering(client):
    admin, manager, _, expert = seed_users()

    notification_routes.create_notification(
        title="管理员通知",
        content="仅管理员可见",
        notify_type="task_assignment",
        roles=["admin"],
    )
    notification_routes.create_notification(
        title="经理通知",
        content="仅经理可见",
        notify_type="system",
        roles=["manager"],
    )
    notification_routes.create_notification(
        title="专家通知",
        content="仅专家可见",
        notify_type="expert_invite",
        user_ids=[expert["id"]],
    )
    notification_routes.create_notification(
        title="系统广播",
        content="所有人可见",
        notify_type="system",
    )

    admin_token = login(client, "admin", "admin123")
    manager_token = login(client, "manager", "manager123")
    expert_token = login(client, "expert", "expert123")

    admin_titles = {item["title"] for item in client.get(
        "/api/v1/notifications",
        headers={"Authorization": f"Bearer {admin_token}"},
    ).json()["data"]}
    assert "管理员通知" in admin_titles
    assert "系统广播" in admin_titles
    assert "经理通知" not in admin_titles

    manager_titles = {item["title"] for item in client.get(
        "/api/v1/notifications",
        headers={"Authorization": f"Bearer {manager_token}"},
    ).json()["data"]}
    assert "经理通知" in manager_titles
    assert "系统广播" in manager_titles
    assert "管理员通知" not in manager_titles

    expert_titles = {item["title"] for item in client.get(
        "/api/v1/notifications",
        headers={"Authorization": f"Bearer {expert_token}"},
    ).json()["data"]}
    assert "专家通知" in expert_titles
    assert "系统广播" in expert_titles
    assert "经理通知" not in expert_titles


def test_evaluation_submit_activity_log(client):
    _, manager, _, expert = seed_users()
    task = seed_task(manager, expert, task_id="task_eval")

    expert_token = login(client, "expert", "expert123")
    submit_response = client.post(
        f"/api/v1/evaluation/{task['task_id']}/submit",
        params={"token": "invite_token_1"},
        json={"round": 1, "evaluations": {"feat_1": 2.5}},
        headers={"Authorization": f"Bearer {expert_token}"},
    )
    assert submit_response.status_code == 200

    activity_response = client.get(
        "/api/v1/profile/activity-logs",
        headers={"Authorization": f"Bearer {expert_token}"},
    )
    assert activity_response.status_code == 200
    items = activity_response.json()["data"]["items"]
    assert any(item.get("action") == "submit_evaluation" for item in items)


def test_multi_round_evaluation_and_report_version(client):
    admin, manager, _, _ = seed_users()
    expert_1, expert_2, expert_3 = seed_experts()
    task = seed_task_with_assignments(manager, [expert_1, expert_2, expert_3], task_id="task_rounds")

    expert_tokens = [
        login(client, "expert1", "expert1"),
        login(client, "expert2", "expert2"),
        login(client, "expert3", "expert3"),
    ]

    for idx, token in enumerate(expert_tokens, start=1):
        submit_response = client.post(
            f"/api/v1/evaluation/{task['task_id']}/submit",
            params={"token": f"token_{idx}"},
            json={"round": 1, "evaluations": {"feat_a": 5, "feat_b": 2}},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert submit_response.status_code == 200

    stored_task = task_routes._get_task(task["task_id"])
    assert stored_task["current_round"] == 2
    assert stored_task["workflow_status"] == "evaluating"
    assert stored_task["report_versions"]
    report_path = stored_task["report_versions"][0]["file_path"]
    assert report_path and os.path.exists(report_path)
    high_ids = stored_task.get("high_deviation_features", {}).get("1", [])
    assert "feat_a" in high_ids
    assert stored_task.get("round_feature_ids", {}).get("2") == ["feat_a"]

    eval_response = client.get(
        f"/api/v1/evaluation/{task['task_id']}",
        params={"token": "token_1"},
        headers={"Authorization": f"Bearer {expert_tokens[0]}"},
    )
    assert eval_response.status_code == 200
    features = eval_response.json()["data"]["features"]
    feature_count = sum(len(items) for items in features.values())
    assert feature_count == 1


def test_withdraw_before_report(client):
    _, manager, _, _ = seed_users()
    expert_1, expert_2, expert_3 = seed_experts()
    task = seed_task_with_assignments(manager, [expert_1, expert_2, expert_3], task_id="task_withdraw")

    expert_token = login(client, "expert1", "expert1")
    submit_response = client.post(
        f"/api/v1/evaluation/{task['task_id']}/submit",
        params={"token": "token_1"},
        json={"round": 1, "evaluations": {"feat_a": 4}},
        headers={"Authorization": f"Bearer {expert_token}"},
    )
    assert submit_response.status_code == 200

    withdraw_response = client.post(
        f"/api/v1/evaluation/{task['task_id']}/withdraw",
        params={"token": "token_1"},
        headers={"Authorization": f"Bearer {expert_token}"},
    )
    assert withdraw_response.status_code == 200

    stored_task = task_routes._get_task(task["task_id"])
    round_key = "1"
    assert stored_task.get("evaluations", {}).get(round_key, {}).get(expert_1["id"]) is None
    drafts = stored_task.get("evaluation_drafts", {}).get(round_key, {}).get(expert_1["id"], {})
    assert drafts


def test_withdraw_blocked_after_report(client):
    _, manager, _, _ = seed_users()
    expert_1, expert_2, expert_3 = seed_experts()
    task = seed_task_with_assignments(manager, [expert_1, expert_2, expert_3], task_id="task_withdraw_block")

    expert_tokens = [
        login(client, "expert1", "expert1"),
        login(client, "expert2", "expert2"),
        login(client, "expert3", "expert3"),
    ]

    for idx, token in enumerate(expert_tokens, start=1):
        submit_response = client.post(
            f"/api/v1/evaluation/{task['task_id']}/submit",
            params={"token": f"token_{idx}"},
            json={"round": 1, "evaluations": {"feat_a": 5, "feat_b": 2}},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert submit_response.status_code == 200

    withdraw_response = client.post(
        f"/api/v1/evaluation/{task['task_id']}/withdraw",
        params={"token": "token_1"},
        headers={"Authorization": f"Bearer {expert_tokens[0]}"},
    )
    assert withdraw_response.status_code == 400
    detail = withdraw_response.json().get("detail", "")
    assert detail in ("报告已生成，无法撤回", "无可撤回的记录")


def test_invite_resend_revoke_and_permission(client):
    admin, manager, _, _ = seed_users()
    expert_1, expert_2, expert_3 = seed_experts()
    task = seed_task_with_assignments(manager, [expert_1, expert_2, expert_3], task_id="task_invites")

    admin_token = login(client, "admin", "admin123")
    manager_token = login(client, "manager", "manager123")
    expert_token = login(client, "expert1", "expert1")

    # manager cannot assign experts
    assign_response = client.post(
        f"/api/v1/tasks/{task['task_id']}/assign-experts",
        json={"expertIds": [expert_1["id"], expert_2["id"], expert_3["id"]]},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert assign_response.status_code == 403

    # admin assign experts
    assign_response = client.post(
        f"/api/v1/tasks/{task['task_id']}/assign-experts",
        json={
            "expertIds": [expert_1["id"], expert_2["id"], expert_3["id"]],
            "expertNames": [expert_1["display_name"], expert_2["display_name"], expert_3["display_name"]],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert assign_response.status_code == 200
    invite_links = assign_response.json()["data"]["inviteLinks"]
    first_assignment_id = invite_links[0]["assignmentId"]
    old_token = invite_links[0]["token"]

    # expert cannot resend
    resend_response = client.post(
        f"/api/v1/tasks/{task['task_id']}/invites/{first_assignment_id}/resend",
        headers={"Authorization": f"Bearer {expert_token}"},
    )
    assert resend_response.status_code == 403

    resend_response = client.post(
        f"/api/v1/tasks/{task['task_id']}/invites/{first_assignment_id}/resend",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resend_response.status_code == 200
    new_token = resend_response.json()["data"]["invite_token"]
    assert new_token != old_token

    stored_task = task_routes._get_task(task["task_id"])
    assignment = next(item for item in stored_task["expert_assignments"] if item["assignment_id"] == first_assignment_id)
    assert old_token in assignment.get("invalid_tokens", [])

    # old token invalid
    eval_response = client.get(
        f"/api/v1/evaluation/{task['task_id']}",
        params={"token": old_token},
        headers={"Authorization": f"Bearer {expert_token}"},
    )
    assert eval_response.status_code == 403

    revoke_response = client.post(
        f"/api/v1/tasks/{task['task_id']}/invites/{first_assignment_id}/revoke",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert revoke_response.status_code == 200

    eval_response = client.get(
        f"/api/v1/evaluation/{task['task_id']}",
        params={"token": new_token},
        headers={"Authorization": f"Bearer {expert_token}"},
    )
    assert eval_response.status_code == 403


def test_task_list_scopes_and_permissions(client):
    admin, manager, manager_2, expert = seed_users()
    seed_experts()

    seed_task(manager, expert, task_id="task_created")
    seed_task(manager_2, expert, task_id="task_other")

    admin_token = login(client, "admin", "admin123")
    manager_token = login(client, "manager", "manager123")
    expert_token = login(client, "expert", "expert123")

    all_response = client.get(
        "/api/v1/tasks",
        params={"scope": "all"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert all_response.status_code == 200
    all_ids = {item["id"] for item in all_response.json()["data"]}
    assert {"task_created", "task_other"} <= all_ids

    manager_response = client.get(
        "/api/v1/tasks",
        params={"scope": "created"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert manager_response.status_code == 200
    manager_ids = {item["id"] for item in manager_response.json()["data"]}
    assert "task_created" in manager_ids
    assert "task_other" not in manager_ids

    expert_response = client.get(
        "/api/v1/tasks",
        params={"scope": "assigned"},
        headers={"Authorization": f"Bearer {expert_token}"},
    )
    assert expert_response.status_code == 200
    expert_ids = {item["id"] for item in expert_response.json()["data"]}
    assert {"task_created", "task_other"} <= expert_ids


def test_profile_update_and_me(client):
    _, manager, _, _ = seed_users()
    token = login(client, "manager", "manager123")
    response = client.get(
        "/api/v1/profile",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["displayName"] == "经理"

    update_response = client.put(
        "/api/v1/profile",
        json={"displayName": "经理改名", "email": "mgr@example.com"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert update_response.status_code == 200

    me_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["data"]["displayName"] == "经理改名"


def test_notifications_read_and_clear(client):
    admin, _, _, _ = seed_users()
    admin_token = login(client, "admin", "admin123")

    notification_routes.create_notification(
        title="通知1",
        content="内容1",
        notify_type="system",
        user_ids=[admin["id"]],
    )
    notification_routes.create_notification(
        title="通知2",
        content="内容2",
        notify_type="system",
        user_ids=[admin["id"]],
    )

    unread_response = client.get(
        "/api/v1/notifications/unread-count",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert unread_response.status_code == 200
    assert unread_response.json()["data"]["unread"] == 2

    list_response = client.get(
        "/api/v1/notifications",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert list_response.status_code == 200
    first_id = list_response.json()["data"][0]["id"]

    mark_response = client.put(
        f"/api/v1/notifications/{first_id}/read",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert mark_response.status_code == 200

    read_all_response = client.put(
        "/api/v1/notifications/read-all",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert read_all_response.status_code == 200

    clear_response = client.delete(
        "/api/v1/notifications/clear-read",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert clear_response.status_code == 200

    after_clear = client.get(
        "/api/v1/notifications",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert after_clear.status_code == 200
    assert after_clear.json()["data"] == []


def test_ai_effect_report_expert_scoped_and_anonymized(client):
    admin, manager, manager_2, expert = seed_users()
    task = seed_task(manager, expert, task_id="task_ai_effect_1")

    ai_effect_service.create_snapshots(task, round_no=1)

    token = login(client, expert["username"], "expert123")
    response = client.get(
        "/api/v1/reports/ai-effect",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    payload = response.json()["data"]
    snapshots = payload["snapshots"]
    assert snapshots
    assert {item["task_id"] for item in snapshots} == {"task_ai_effect_1"}
    assert all("manager_id" not in item and "manager_name" not in item for item in snapshots)


def test_knowledge_endpoints_manager_only(client):
    admin, manager, manager_2, expert = seed_users()

    admin_token = login(client, admin["username"], "admin123")
    response = client.get(
        "/api/v1/knowledge/health",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 403

    manager_token = login(client, manager["username"], "manager123")
    response = client.get(
        "/api/v1/knowledge/health",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    # knowledge store may be empty in tests; allow 200 or 503 but not 403
    assert response.status_code in (200, 503)


def test_cosmic_config_admin_only(client):
    admin, manager, manager_2, expert = seed_users()

    manager_token = login(client, manager["username"], "manager123")
    response = client.get(
        "/api/v1/cosmic/config",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 403

    admin_token = login(client, admin["username"], "admin123")
    response = client.get(
        "/api/v1/cosmic/config",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json().get("code") == 200
