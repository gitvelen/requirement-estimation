import json
import os
import sys
import time

import pytest
from fastapi.testclient import TestClient

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.app import app
from backend.api import system_routes
from backend.config.config import settings
from backend.service import knowledge_service as ks
from backend.service import system_profile_service
from backend.service import user_service


class DummyEmbeddingService:
    def generate_embedding(self, text: str):
        return [1.0, 0.0, 0.0]


class FailingEmbeddingService:
    def generate_embedding(self, text: str):
        raise TimeoutError("embedding timeout")


class SlowEmbeddingService:
    def __init__(self, delay: float):
        self.delay = delay

    def generate_embedding(self, text: str):
        time.sleep(self.delay)
        return [1.0, 0.0, 0.0]


@pytest.fixture()
def client(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(settings, "REPORT_DIR", str(data_dir))
    monkeypatch.setattr(settings, "KNOWLEDGE_VECTOR_STORE", "local")

    monkeypatch.setattr(user_service, "USER_STORE_PATH", str(data_dir / "users.json"))
    monkeypatch.setattr(user_service, "USER_STORE_LOCK_PATH", str(data_dir / "users.json.lock"))
    monkeypatch.setattr(system_routes, "CSV_PATH", str(tmp_path / "system_list.csv"))

    # Avoid real embedding initialization (depends on DASHSCOPE_API_KEY / network).
    monkeypatch.setattr(ks, "get_embedding_service", lambda: DummyEmbeddingService())

    system_profile_service._system_profile_service = None
    ks._knowledge_service = None

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


def _seed_system(owner, system_id: str = "sys_hop", system_name: str = "HOP"):
    system_routes._write_systems(
        [
            {
                "id": system_id,
                "name": system_name,
                "abbreviation": system_name,
                "status": "运行中",
                "extra": {"owner_id": owner["id"], "owner_name": "负责人"},
            }
        ]
    )


def _load_working_profile(*, system_id: str = "", system_name: str = ""):
    repository = system_profile_service.get_system_profile_service().repository
    profile = repository.load_profile(state="working", system_id=system_id, system_name=system_name)
    assert isinstance(profile, dict)
    return profile


def _save_working_profile(profile):
    repository = system_profile_service.get_system_profile_service().repository
    repository.save_working_profile(profile)


def test_publish_allows_v21_four_fields(client, monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", False)

    owner = _seed_user("owner_publish_ok", "owner123", ["manager"])
    _seed_system(owner)

    token = _login(client, "owner_publish_ok", "owner123")

    saved = client.put(
        "/api/v1/system-profiles/HOP",
        json={
            "system_id": "sys_hop",
            "fields": {
                "system_scope": "账户管理系统",
                "module_structure": [{"module_name": "账户", "functions": [{"name": "开户", "desc": "开户流程"}]}],
                "integration_points": "核心账务",
                "key_constraints": "合规",
            },
            "evidence_refs": [],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert saved.status_code == 200

    published = client.post(
        "/api/v1/system-profiles/HOP/publish",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert published.status_code == 200
    payload = published.json()
    assert payload.get("code") == 200
    assert payload.get("data", {}).get("status") == "published"


def test_publish_succeeds_when_embedding_unavailable(client, monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", False)

    class DummyKnowledgeService:
        def __init__(self):
            self.embedding_service = FailingEmbeddingService()
            self.vector_store = object()

    monkeypatch.setattr(ks, "get_knowledge_service", lambda: DummyKnowledgeService())

    owner = _seed_user("owner_publish_degraded", "owner123", ["manager"])
    _seed_system(owner)

    token = _login(client, "owner_publish_degraded", "owner123")

    saved = client.put(
        "/api/v1/system-profiles/HOP",
        json={
            "system_id": "sys_hop",
            "fields": {
                "system_scope": "账户管理系统",
                "module_structure": [{"module_name": "账户", "functions": [{"name": "开户", "desc": "开户流程"}]}],
                "integration_points": "核心账务",
                "key_constraints": "合规",
            },
            "evidence_refs": [],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert saved.status_code == 200

    published = client.post(
        "/api/v1/system-profiles/HOP/publish",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert published.status_code == 200
    payload = published.json()
    assert payload.get("code") == 200
    assert payload.get("data", {}).get("status") == "published"

    stored_profile = _load_working_profile(system_id="sys_hop")
    assert stored_profile.get("status") == "published"
    assert stored_profile.get("published_at")


def test_publish_returns_before_slow_embedding_finishes(client, monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", False)
    monkeypatch.setattr(settings, "PUBLISH_KNOWLEDGE_WAIT_SECONDS", 0.01, raising=False)

    class DummyVectorStore:
        def insert_knowledge(self, **kwargs):
            return {"id": "knowledge_001"}

    class DummyKnowledgeService:
        def __init__(self):
            self.embedding_service = SlowEmbeddingService(delay=0.2)
            self.vector_store = DummyVectorStore()

    monkeypatch.setattr(ks, "get_knowledge_service", lambda: DummyKnowledgeService())

    owner = _seed_user("owner_publish_async", "owner123", ["manager"])
    _seed_system(owner)

    token = _login(client, "owner_publish_async", "owner123")

    saved = client.put(
        "/api/v1/system-profiles/HOP",
        json={
            "system_id": "sys_hop",
            "fields": {
                "system_scope": "账户管理系统",
                "module_structure": [{"module_name": "账户", "functions": [{"name": "开户", "desc": "开户流程"}]}],
                "integration_points": "核心账务",
                "key_constraints": "合规",
            },
            "evidence_refs": [],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert saved.status_code == 200

    started = time.monotonic()
    published = client.post(
        "/api/v1/system-profiles/HOP/publish",
        headers={"Authorization": f"Bearer {token}"},
    )
    elapsed = time.monotonic() - started

    assert published.status_code == 200
    assert elapsed < 0.15
    payload = published.json()
    assert payload.get("code") == 200
    assert payload.get("data", {}).get("status") == "published"

    stored_profile = _load_working_profile(system_id="sys_hop")
    assert stored_profile.get("status") == "published"


def test_save_rejects_invalid_module_structure(client, monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", False)

    owner = _seed_user("owner_publish_missing", "owner123", ["manager"])
    _seed_system(owner)

    token = _login(client, "owner_publish_missing", "owner123")

    response = client.put(
        "/api/v1/system-profiles/HOP",
        json={
            "system_id": "sys_hop",
            "fields": {
                "system_scope": "账户管理系统",
                "module_structure": {"module_name": "账户"},
            },
            "evidence_refs": [],
        },
        headers={"Authorization": f"Bearer {token}", "X-Request-ID": "req_profile_publish_missing"},
    )
    assert response.status_code == 400
    payload = response.json()
    assert payload.get("error_code") == "invalid_module_structure"
    assert payload.get("request_id") == "req_profile_publish_missing"
    assert "module_structure" in str(payload.get("message") or "")


def test_profile_fields_only_keep_v21_contract(client, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "DEBUG", False)

    owner = _seed_user("owner_business_goal", "owner123", ["manager"])
    _seed_system(owner)

    token = _login(client, "owner_business_goal", "owner123")

    saved = client.put(
        "/api/v1/system-profiles/HOP",
        json={
            "system_id": "sys_hop",
            "fields": {
                "system_scope": "做A",
                "module_structure": [{"module_name": "账户", "functions": [{"name": "开立", "desc": "开立账户"}]}],
                "integration_points": "核心账务",
                "key_constraints": "高可用",
                "business_goal": "应被忽略",
                "core_functions": "应被忽略",
            },
            "evidence_refs": [],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert saved.status_code == 200

    fetched = client.get(
        "/api/v1/system-profiles/HOP",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert fetched.status_code == 200
    data = fetched.json().get("data") or {}
    fields = data.get("fields") or {}
    assert set(fields.keys()) == {"system_scope", "module_structure", "integration_points", "key_constraints"}
    assert fields.get("system_scope") == "做A"
    assert isinstance(fields.get("module_structure"), list)
    assert fields.get("module_structure")[0].get("module_name") == "账户"

    stored_profile = _load_working_profile(system_id="sys_hop")
    stored_fields = stored_profile.get("fields") or {}
    assert set(stored_fields.keys()) == {"system_scope", "module_structure", "integration_points", "key_constraints"}
    assert not os.path.exists(os.path.join(settings.REPORT_DIR, "system_profiles.json"))
    workspace_path = system_profile_service.get_system_profile_service().repository.get_workspace_path(system_id="sys_hop")
    assert workspace_path
    assert os.path.exists(os.path.join(workspace_path, "profile", "working.json"))

    published = client.post(
        "/api/v1/system-profiles/HOP/publish",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert published.status_code == 200
    published_payload = published.json().get("data") or {}
    assert published_payload.get("status") == "published"
    assert published_payload.get("published_at")

    stored_profile = _load_working_profile(system_id="sys_hop")
    assert stored_profile.get("status") == "published"
    assert stored_profile.get("published_at")


def test_profile_suggestion_accept_rollback_and_events(client, monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", False)

    owner = _seed_user("owner_profile_actions", "owner123", ["manager"])
    _seed_system(owner, system_id="sys_actions", system_name="ACTIONS")
    token = _login(client, "owner_profile_actions", "owner123")

    saved = client.put(
        "/api/v1/system-profiles/ACTIONS",
        json={
            "system_id": "sys_actions",
            "fields": {
                "system_scope": "旧系统描述",
                "module_structure": [{"module_name": "账户", "functions": [{"name": "开户"}]}],
                "integration_points": "旧集成点",
                "key_constraints": "旧约束",
            },
            "evidence_refs": [],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert saved.status_code == 200

    stored_profile = _load_working_profile(system_id="sys_actions")
    stored_profile["ai_suggestions"] = {
        "system_scope": "新系统描述",
        "integration_points": "新集成点",
    }
    stored_profile["ai_suggestions_previous"] = {
        "system_scope": "上一版系统描述",
        "integration_points": "上一版集成点",
    }
    stored_profile["profile_events"] = []
    _save_working_profile(stored_profile)

    accepted = client.post(
        "/api/v1/system-profiles/sys_actions/profile/suggestions/accept",
        json={"domain": "system_positioning", "sub_field": "system_description"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert accepted.status_code == 200
    accepted_data = accepted.json().get("data") or {}
    assert accepted_data.get("profile_data", {}).get("system_positioning", {}).get("system_description") == "新系统描述"

    rolled_back = client.post(
        "/api/v1/system-profiles/sys_actions/profile/suggestions/rollback",
        json={"domain": "system_positioning", "sub_field": "system_description"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert rolled_back.status_code == 200
    rollback_data = rolled_back.json().get("data") or {}
    assert rollback_data.get("ai_suggestions", {}).get("system_positioning", {}).get("system_description") == "上一版系统描述"

    events = client.get(
        "/api/v1/system-profiles/sys_actions/profile/events",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert events.status_code == 200
    items = events.json().get("items") or []
    event_types = [item.get("event_type") for item in items]
    assert "ai_suggestion_accept" in event_types
    assert "ai_suggestion_rollback" in event_types


def test_profile_suggestion_ignore_persists_and_records_event(client, monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", False)

    owner = _seed_user("owner_profile_ignore", "owner123", ["manager"])
    _seed_system(owner, system_id="sys_ignore", system_name="IGNORE_CASE")
    token = _login(client, "owner_profile_ignore", "owner123")

    saved = client.put(
        "/api/v1/system-profiles/IGNORE_CASE",
        json={
            "system_id": "sys_ignore",
            "profile_data": {
                "system_positioning": {
                    "system_description": "当前系统描述",
                    "target_users": [],
                    "boundaries": [],
                },
                "business_capabilities": {
                    "module_structure": [],
                    "core_processes": [],
                },
                "integration_interfaces": {
                    "integration_points": [],
                    "external_dependencies": [],
                },
                "technical_architecture": {
                    "architecture_positioning": "",
                    "tech_stack": [],
                    "performance_profile": {},
                },
                "constraints_risks": {
                    "key_constraints": [],
                    "known_risks": [],
                },
            },
            "evidence_refs": [],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert saved.status_code == 200

    stored_profile = _load_working_profile(system_id="sys_ignore")
    stored_profile["ai_suggestions"] = {
        "system_positioning": {
            "system_description": "AI建议-系统描述",
        }
    }
    stored_profile["profile_events"] = []
    _save_working_profile(stored_profile)

    ignored = client.post(
        "/api/v1/system-profiles/sys_ignore/profile/suggestions/ignore",
        json={"domain": "system_positioning", "sub_field": "system_description"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert ignored.status_code == 200
    ignored_data = ignored.json().get("data") or {}
    ignored_map = ignored_data.get("ai_suggestion_ignored") or {}
    assert ignored_map.get("system_positioning.system_description") == "AI建议-系统描述"

    fetched = client.get(
        "/api/v1/system-profiles/IGNORE_CASE",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert fetched.status_code == 200
    fetched_data = fetched.json().get("data") or {}
    assert (fetched_data.get("ai_suggestion_ignored") or {}).get("system_positioning.system_description") == "AI建议-系统描述"

    events = client.get(
        "/api/v1/system-profiles/sys_ignore/profile/events",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert events.status_code == 200
    items = events.json().get("items") or []
    event_types = [item.get("event_type") for item in items]
    assert "ai_suggestion_ignore" in event_types


def test_profile_events_returns_empty_when_profile_not_created(client, monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", False)

    owner = _seed_user("owner_profile_events_empty", "owner123", ["manager"])
    _seed_system(owner, system_id="sys_events_empty", system_name="EVENTS_EMPTY")
    token = _login(client, "owner_profile_events_empty", "owner123")

    events = client.get(
        "/api/v1/system-profiles/sys_events_empty/profile/events",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert events.status_code == 200
    payload = events.json()
    assert payload.get("total") == 0
    assert payload.get("items") == []


def test_profile_suggestion_rollback_without_previous_returns_409(client, monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", False)

    owner = _seed_user("owner_profile_rollback_empty", "owner123", ["manager"])
    _seed_system(owner, system_id="sys_rb_empty", system_name="RB_EMPTY")
    token = _login(client, "owner_profile_rollback_empty", "owner123")

    saved = client.put(
        "/api/v1/system-profiles/RB_EMPTY",
        json={
            "system_id": "sys_rb_empty",
            "fields": {
                "system_scope": "系统描述",
                "module_structure": [{"module_name": "账户", "functions": [{"name": "开户"}]}],
            },
            "evidence_refs": [],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert saved.status_code == 200

    rolled_back = client.post(
        "/api/v1/system-profiles/sys_rb_empty/profile/suggestions/rollback",
        json={"domain": "system_positioning", "sub_field": "system_description"},
        headers={"Authorization": f"Bearer {token}", "X-Request-ID": "req_rollback_no_previous"},
    )
    assert rolled_back.status_code == 409
    payload = rolled_back.json()
    assert payload.get("error_code") == "ROLLBACK_NO_PREVIOUS"
    assert payload.get("request_id") == "req_rollback_no_previous"


def test_profile_put_with_profile_data_keeps_legacy_fields_compatible(client, monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", False)

    owner = _seed_user("owner_profile_data_put", "owner123", ["manager"])
    _seed_system(owner, system_id="sys_profile_data", system_name="PROFILE_DATA")
    token = _login(client, "owner_profile_data_put", "owner123")

    profile_data = {
        "system_positioning": {
            "system_description": "画像系统描述",
            "target_users": ["运营", "客服"],
            "boundaries": ["仅管理账户域"],
        },
        "business_capabilities": {
            "module_structure": [{"module_name": "账户", "functions": [{"name": "开户", "desc": "开户流程"}]}],
            "core_processes": ["开户审批"],
        },
        "integration_interfaces": {
            "integration_points": [{"description": "核心账务"}],
            "external_dependencies": ["消息总线"],
        },
        "technical_architecture": {
            "architecture_positioning": "单体",
            "tech_stack": ["FastAPI"],
            "performance_profile": {"qps": "100"},
        },
        "constraints_risks": {
            "key_constraints": [{"category": "合规", "description": "数据留痕"}],
            "known_risks": ["峰值流量风险"],
        },
    }

    saved = client.put(
        "/api/v1/system-profiles/PROFILE_DATA",
        json={
            "system_id": "sys_profile_data",
            "profile_data": profile_data,
            "evidence_refs": [],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert saved.status_code == 200
    saved_data = saved.json().get("data") or {}
    assert saved_data.get("profile_data", {}).get("system_positioning", {}).get("system_description") == "画像系统描述"

    fields = saved_data.get("fields") or {}
    assert fields.get("system_scope") == "画像系统描述"
    assert fields.get("integration_points") == "核心账务"

    fetched = client.get(
        "/api/v1/system-profiles/PROFILE_DATA",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert fetched.status_code == 200
    fetched_data = fetched.json().get("data") or {}
    assert fetched_data.get("profile_data", {}).get("system_positioning", {}).get("system_description") == "画像系统描述"
    assert (fetched_data.get("fields") or {}).get("system_scope") == "画像系统描述"


def test_profile_put_normalizes_human_friendly_profile_data_shapes(client, monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", False)

    owner = _seed_user("owner_profile_humanized_put", "owner123", ["manager"])
    _seed_system(owner, system_id="sys_profile_humanized", system_name="PROFILE_HUMANIZED")
    token = _login(client, "owner_profile_humanized_put", "owner123")

    profile_data = {
        "system_positioning": {
            "system_description": "画像系统描述",
        },
        "business_capabilities": {
            "module_structure": [
                {"module_name": "账户", "functions": [{"name": "开户", "desc": "开户流程"}]},
            ],
        },
        "integration_interfaces": {
            "integration_points": "核心账务、支付网关",
        },
        "technical_architecture": {
            "performance_profile": [
                {"key": "qps", "value": "100"},
                {"key": "latency", "value": "50ms"},
            ],
        },
        "constraints_risks": {
            "key_constraints": "需满足合规审计",
        },
    }

    saved = client.put(
        "/api/v1/system-profiles/PROFILE_HUMANIZED",
        json={
            "system_id": "sys_profile_humanized",
            "profile_data": profile_data,
            "evidence_refs": [],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert saved.status_code == 200

    saved_data = saved.json().get("data") or {}
    saved_profile = saved_data.get("profile_data") or {}

    integration_points = (
        saved_profile.get("integration_interfaces", {}).get("integration_points") or []
    )
    assert integration_points == [{"description": "核心账务、支付网关"}]

    performance_profile = (
        saved_profile.get("technical_architecture", {}).get("performance_profile") or {}
    )
    assert performance_profile == {"qps": "100", "latency": "50ms"}

    key_constraints = (
        saved_profile.get("constraints_risks", {}).get("key_constraints") or []
    )
    assert key_constraints == [{"category": "通用", "description": "需满足合规审计"}]
