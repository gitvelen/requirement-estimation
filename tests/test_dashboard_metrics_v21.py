import os
import sys
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.app import app
from backend.api import routes as task_routes
from backend.config.config import settings
from backend.service import system_profile_service
from backend.service import user_service


@pytest.fixture()
def client(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(settings, "REPORT_DIR", str(data_dir))
    monkeypatch.setattr(settings, "DEBUG", False)
    monkeypatch.setattr(settings, "V21_DASHBOARD_MGMT_ENABLED", True)

    monkeypatch.setattr(user_service, "USER_STORE_PATH", str(data_dir / "users.json"))
    monkeypatch.setattr(user_service, "USER_STORE_LOCK_PATH", str(data_dir / "users.json.lock"))

    monkeypatch.setattr(task_routes, "TASK_STORE_PATH", str(data_dir / "task_storage.json"))
    monkeypatch.setattr(task_routes, "TASK_STORE_LOCK_PATH", str(data_dir / "task_storage.json.lock"))

    system_profile_service._system_profile_service = None

    return TestClient(app)


def _seed_user(username: str, password: str, roles):
    user = user_service.create_user_record(
        {
            "username": username,
            "display_name": username,
            "password": password,
            "roles": roles,
        }
    )
    with user_service.user_storage_context() as users:
        users.append(user)
    return user


def _login(client: TestClient, username: str, password: str) -> str:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["data"]["token"]


def _seed_profiles(manager, admin):
    service = system_profile_service.get_system_profile_service()

    service.upsert_profile(
        "HOP",
        {
            "system_id": "sys_hop",
            "fields": {
                "system_scope": "账户核心",
                "module_structure": [{"module_name": "账户", "functions": [{"name": "开户"}, {"name": "销户"}]}],
                "integration_points": "账务核心",
                "key_constraints": "高可用",
            },
            "evidence_refs": [],
        },
        actor=manager,
    )
    service.mark_code_scan_ingested("HOP", "sys_hop", "scan_hop", "/tmp/scan_hop.json", actor=manager)
    service.mark_esb_ingested("HOP", "sys_hop", "esb_hop", "esb_hop.csv", actor=manager)
    service.mark_document_imported("HOP", "sys_hop", "doc_hop_1", "hop_1.txt", actor=manager)
    service.mark_document_imported("HOP", "sys_hop", "doc_hop_2", "hop_2.txt", actor=manager)

    service.upsert_profile(
        "PAY",
        {
            "system_id": "sys_pay",
            "fields": {
                "system_scope": "支付外围",
                "module_structure": [],
                "integration_points": "支付网关",
                "key_constraints": "合规",
            },
            "evidence_refs": [],
        },
        actor=admin,
    )

    # 把 PAY 画像改为过期，便于验证 stale 标记
    pay_profile = service.repository.load_profile(state="working", system_name="PAY")
    if isinstance(pay_profile, dict):
        pay_profile["updated_at"] = (datetime.now() - timedelta(days=40)).isoformat()
        service.repository.save_working_profile(pay_profile)


def _seed_task(
    *,
    task_id: str,
    manager,
    system_id: str,
    system_name: str,
    created_days_ago: int,
    frozen_days_ago: int,
    ai_days: float,
    final_days: float,
    feature_count: int,
    include_ai_initial: bool,
    include_add_mod: bool,
    include_update_mod: bool,
    include_delete_mod: bool,
):
    now = datetime.now()

    ai_initial_features = []
    systems_data_features = []
    for idx in range(feature_count):
        feature_id = f"{task_id}_feat_{idx + 1}"
        feature = {
            "id": feature_id,
            "系统": system_name,
            "功能点": f"功能{idx + 1}",
            "预估人天": round(ai_days / max(feature_count, 1), 2),
            "功能模块": "模块A",
        }
        systems_data_features.append(dict(feature))
        ai_initial_features.append(
            {
                "feature_id": feature_id,
                "system_name": system_id,
                "feature": dict(feature),
            }
        )

    modifications = []
    if include_update_mod:
        modifications.append(
            {
                "id": f"mod_{task_id}_u1",
                "timestamp": now.isoformat(),
                "operation": "update",
                "system": system_id,
                "feature_id": f"{task_id}_feat_1",
                "feature_name": "功能1",
                "field": "业务描述",
                "old_value": "旧",
                "new_value": "新",
                "actor_id": manager["id"],
                "actor_role": "manager",
            }
        )
        # 同一功能点二次字段更新，应被去重为一次修正
        modifications.append(
            {
                "id": f"mod_{task_id}_u2",
                "timestamp": now.isoformat(),
                "operation": "update",
                "system": system_id,
                "feature_id": f"{task_id}_feat_1",
                "feature_name": "功能1",
                "field": "复杂度",
                "old_value": "中",
                "new_value": "高",
                "actor_id": manager["id"],
                "actor_role": "manager",
            }
        )
    if include_delete_mod:
        modifications.append(
            {
                "id": f"mod_{task_id}_d1",
                "timestamp": now.isoformat(),
                "operation": "delete",
                "system": system_id,
                "feature_id": f"{task_id}_feat_2",
                "feature_name": "功能2",
                "actor_id": manager["id"],
                "actor_role": "manager",
            }
        )
    if include_add_mod:
        modifications.append(
            {
                "id": f"mod_{task_id}_a1",
                "timestamp": now.isoformat(),
                "operation": "add",
                "system": system_id,
                "feature_id": f"{task_id}_feat_new",
                "feature_name": "新增功能",
                "actor_id": manager["id"],
                "actor_role": "manager",
            }
        )

    with task_routes._task_storage_context() as data:
        data[task_id] = {
            "task_id": task_id,
            "name": task_id,
            "creator_id": manager["id"],
            "creator_name": manager["display_name"],
            "status": "completed",
            "workflow_status": "completed",
            "created_at": (now - timedelta(days=created_days_ago)).isoformat(),
            "frozen_at": (now - timedelta(days=frozen_days_ago)).isoformat(),
            "project_id": "proj_v21",
            "ai_involved": True,
            "ai_estimation_days_total": ai_days,
            "final_estimation_days_total": final_days,
            "final_estimation_days_by_system": [
                {"system_id": system_id, "system_name": system_name, "days": final_days}
            ],
            "owner_snapshot": {
                "primary_owner_id": manager["id"],
                "primary_owner_name": manager["display_name"],
            },
            "expert_assignments": [],
            "systems": [system_id],
            "systems_data": {system_id: systems_data_features},
            "ai_initial_features": ai_initial_features if include_ai_initial else [],
            "modifications": modifications,
        }


def _seed_dashboard_dataset(manager, admin):
    _seed_profiles(manager, admin)

    # HOP: 3条任务（满足统计门槛）
    _seed_task(
        task_id="task_hop_1",
        manager=manager,
        system_id="sys_hop",
        system_name="HOP",
        created_days_ago=4,
        frozen_days_ago=3,
        ai_days=13.0,
        final_days=10.0,
        feature_count=4,
        include_ai_initial=True,
        include_add_mod=True,
        include_update_mod=True,
        include_delete_mod=False,
    )
    _seed_task(
        task_id="task_hop_2",
        manager=manager,
        system_id="sys_hop",
        system_name="HOP",
        created_days_ago=3,
        frozen_days_ago=2,
        ai_days=12.0,
        final_days=10.0,
        feature_count=4,
        include_ai_initial=True,
        include_add_mod=False,
        include_update_mod=True,
        include_delete_mod=True,
    )
    # 缺失 ai_initial_features，触发口径降级
    _seed_task(
        task_id="task_hop_3",
        manager=manager,
        system_id="sys_hop",
        system_name="HOP",
        created_days_ago=2,
        frozen_days_ago=1,
        ai_days=11.0,
        final_days=10.0,
        feature_count=4,
        include_ai_initial=False,
        include_add_mod=False,
        include_update_mod=False,
        include_delete_mod=False,
    )

    # PAY: 2条任务（不足3，指标应 N/A）
    _seed_task(
        task_id="task_pay_1",
        manager=manager,
        system_id="sys_pay",
        system_name="PAY",
        created_days_ago=4,
        frozen_days_ago=2,
        ai_days=6.0,
        final_days=5.0,
        feature_count=3,
        include_ai_initial=True,
        include_add_mod=True,
        include_update_mod=True,
        include_delete_mod=False,
    )
    _seed_task(
        task_id="task_pay_2",
        manager=manager,
        system_id="sys_pay",
        system_name="PAY",
        created_days_ago=3,
        frozen_days_ago=1,
        ai_days=4.0,
        final_days=5.0,
        feature_count=3,
        include_ai_initial=True,
        include_add_mod=False,
        include_update_mod=False,
        include_delete_mod=False,
    )


def _query_dashboard(client: TestClient, token: str, page: str, filters=None):
    response = client.post(
        "/api/v1/efficiency/dashboard/query",
        json={
            "page": page,
            "perspective": "executive",
            "filters": filters or {"time_range": "last_30d"},
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    return response.json().get("result", {})


def test_dashboard_v21_management_widgets_exposed(client):
    admin = _seed_user("dash_v21_admin", "pwd123", ["admin"])
    manager = _seed_user("dash_v21_mgr", "pwd123", ["manager"])

    token = _login(client, "dash_v21_admin", "pwd123")
    _seed_dashboard_dataset(manager, admin)

    ai_result = _query_dashboard(client, token, "ai")
    ai_widget_ids = {item.get("widget_id") for item in ai_result.get("widgets", [])}
    assert "pm_correction_rate_ranking" in ai_widget_ids
    assert "ai_hit_rate_ranking" in ai_widget_ids
    assert "ai_deviation_monitoring" in ai_widget_ids
    assert "ai_learning_trend" in ai_widget_ids

    system_result = _query_dashboard(client, token, "system")
    system_widget_ids = {item.get("widget_id") for item in system_result.get("widgets", [])}
    assert "profile_completeness_ranking" in system_widget_ids

    rankings_result = _query_dashboard(client, token, "rankings")
    ranking_widget_ids = {item.get("widget_id") for item in rankings_result.get("widgets", [])}
    assert "evaluation_cycle_ranking" in ranking_widget_ids
    assert "profile_contribution_ranking" in ranking_widget_ids



def test_dashboard_v21_sample_guard_and_caliber_fallback(client):
    admin = _seed_user("dash_v21_admin_2", "pwd123", ["admin"])
    manager = _seed_user("dash_v21_mgr_2", "pwd123", ["manager"])

    token = _login(client, "dash_v21_admin_2", "pwd123")
    _seed_dashboard_dataset(manager, admin)

    ai_result = _query_dashboard(client, token, "ai")
    widgets = {item.get("widget_id"): item for item in ai_result.get("widgets", [])}

    pm_widget = widgets.get("pm_correction_rate_ranking") or {}
    pm_items = (pm_widget.get("data") or {}).get("items") or []
    hop_item = next(item for item in pm_items if item.get("system_id") == "sys_hop")
    pay_item = next(item for item in pm_items if item.get("system_id") == "sys_pay")

    assert hop_item.get("system_name") == "HOP"
    assert pay_item.get("system_name") == "PAY"
    assert hop_item.get("correction_rate") != "N/A"
    assert hop_item.get("caliber") in {"标准", "口径降级"}
    assert pay_item.get("correction_rate") == "N/A"

    deviation_widget = widgets.get("ai_deviation_monitoring") or {}
    deviation_items = (deviation_widget.get("data") or {}).get("items") or []
    hop_deviation = next(item for item in deviation_items if item.get("system_id") == "sys_hop")
    assert hop_deviation.get("system_name") == "HOP"
    assert hop_deviation.get("caliber") == "口径降级"



def test_dashboard_v21_profile_completeness_contains_stale_and_module_score(client):
    admin = _seed_user("dash_v21_admin_3", "pwd123", ["admin"])
    manager = _seed_user("dash_v21_mgr_3", "pwd123", ["manager"])

    token = _login(client, "dash_v21_admin_3", "pwd123")
    _seed_dashboard_dataset(manager, admin)

    system_result = _query_dashboard(client, token, "system")
    widgets = {item.get("widget_id"): item for item in system_result.get("widgets", [])}
    profile_widget = widgets.get("profile_completeness_ranking") or {}
    items = (profile_widget.get("data") or {}).get("items") or []

    hop_item = next(item for item in items if item.get("system_id") == "sys_hop")
    pay_item = next(item for item in items if item.get("system_id") == "sys_pay")

    assert hop_item.get("module_structure") == 20
    assert hop_item.get("completeness_score") >= 50
    assert pay_item.get("stale") == "过期"



def test_dashboard_v21_feature_flag_off_hides_management_widgets(client, monkeypatch):
    admin = _seed_user("dash_v21_admin_4", "pwd123", ["admin"])
    manager = _seed_user("dash_v21_mgr_4", "pwd123", ["manager"])

    monkeypatch.setattr(settings, "V21_DASHBOARD_MGMT_ENABLED", False)

    token = _login(client, "dash_v21_admin_4", "pwd123")
    _seed_dashboard_dataset(manager, admin)

    ai_result = _query_dashboard(client, token, "ai")
    ai_widget_ids = {item.get("widget_id") for item in ai_result.get("widgets", [])}
    assert "pm_correction_rate_ranking" not in ai_widget_ids
    assert "ai_hit_rate_ranking" not in ai_widget_ids



def test_dashboard_v21_invalid_perspective_error_code(client):
    admin = _seed_user("dash_v21_admin_5", "pwd123", ["admin"])
    token = _login(client, "dash_v21_admin_5", "pwd123")

    response = client.post(
        "/api/v1/efficiency/dashboard/query",
        json={"page": "overview", "perspective": "invalid", "filters": {"time_range": "last_30d"}},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload.get("error_code") == "invalid_perspective"



def test_dashboard_v21_ignores_legacy_ai_involved_filter(client):
    admin = _seed_user("dash_v21_admin_6", "pwd123", ["admin"])
    manager = _seed_user("dash_v21_mgr_6", "pwd123", ["manager"])

    token = _login(client, "dash_v21_admin_6", "pwd123")
    _seed_dashboard_dataset(manager, admin)

    baseline = _query_dashboard(client, token, "overview", {"time_range": "last_30d"})
    with_legacy_filter = _query_dashboard(client, token, "overview", {"time_range": "last_30d", "ai_involved": False})

    base_widgets = baseline.get("widgets") or []
    legacy_widgets = with_legacy_filter.get("widgets") or []
    assert base_widgets and legacy_widgets

    base_task_count = (base_widgets[0].get("data") or {}).get("task_count")
    legacy_task_count = (legacy_widgets[0].get("data") or {}).get("task_count")
    assert base_task_count == legacy_task_count
