import os
import sys
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.app import app
from backend.api import system_routes
from backend.config.config import settings
from backend.service import memory_service
from backend.service import profile_artifact_service
from backend.service import runtime_execution_service
from backend.service import system_profile_service
from backend.service import user_service


@pytest.fixture()
def client(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(settings, "REPORT_DIR", str(data_dir))
    monkeypatch.setattr(settings, "ENABLE_V27_PROFILE_SCHEMA", True)
    monkeypatch.setattr(settings, "ENABLE_V27_RUNTIME", True)
    monkeypatch.setattr(settings, "ENABLE_SYSTEM_CATALOG_PROFILE_INIT", True)
    monkeypatch.setattr(user_service, "USER_STORE_PATH", str(data_dir / "users.json"))
    monkeypatch.setattr(user_service, "USER_STORE_LOCK_PATH", str(data_dir / "users.json.lock"))
    monkeypatch.setattr(system_routes, "CSV_PATH", str(tmp_path / "system_list.csv"))

    system_profile_service._system_profile_service = None
    memory_service._memory_service = None
    runtime_execution_service._runtime_execution_service = None

    return TestClient(app)


def _seed_admin():
    admin = user_service.create_user_record(
        {
            "username": "admin",
            "display_name": "管理员",
            "password": "admin123",
            "roles": ["admin"],
        }
    )
    with user_service.user_storage_context() as users:
        users.append(admin)
    return admin


def _login(client: TestClient, username: str, password: str) -> str:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["data"]["token"]


def _catalog_system(
    *,
    system_id: str,
    system_name: str,
    service_scope: str,
    related_systems: str = "核心账务,柜面渠道",
) -> dict:
    return {
        "id": system_id,
        "name": system_name,
        "abbreviation": "PAY",
        "status": "运行中",
        "extra": {
            "系统类型": "渠道接入",
            "应用主题域": "支付域",
            "应用分层": "3产品服务层",
            "服务对象": "柜面,客户",
            "功能描述": service_scope,
            "开发语言": "Java,SQL",
            "RDBMS": "OceanBase",
            "应用中间件": "Tomcat",
            "操作系统": "Linux",
            "芯片": "x86",
            "新技术特征": "云原生",
            "英文简称": "PAY",
            "业务领域": "支付结算,渠道服务",
            "应用等级": "1",
            "是否云部署": "是",
            "是否有互联网出口": "否",
            "是否双活": "是",
            "集群分类": "集群I",
            "虚拟化分布": "C1",
            "全栈信创": "否",
            "等保定级": "3",
            "是否是重要信息系统": "是",
            "系统RTO": "30",
            "系统RPO": "5",
            "灾备情况": "同城双活",
            "灾备部署地": "上海",
            "应急预案更新日期": "2024-08-01",
            "知识产权": "共有",
            "产品授权证书情况": "不涉及",
            "关联系统": related_systems,
        },
    }


def test_catalog_confirm_initializes_blank_profiles_and_writes_memory(client):
    _seed_admin()
    token = _login(client, "admin", "admin123")

    response = client.post(
        "/api/v1/system-list/batch-import/confirm",
        json={"mode": "replace", "systems": [_catalog_system(system_id="SYS-001", system_name="统一支付平台", service_scope="支付统一受理")]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["result_status"] == "success"
    assert payload["catalog_import_result"]["updated_system_ids"] == ["SYS-001"]
    assert payload["catalog_import_result"]["updated_systems"] == [
        {"system_id": "SYS-001", "system_name": "统一支付平台"}
    ]
    assert payload["catalog_import_result"]["skipped_items"] == []

    profile = system_profile_service.get_system_profile_service().get_profile("统一支付平台")
    canonical_d1 = profile["profile_data"]["system_positioning"]["canonical"]
    canonical_d3 = profile["profile_data"]["integration_interfaces"]["canonical"]
    canonical_d4 = profile["profile_data"]["technical_architecture"]["canonical"]
    canonical_d5 = profile["profile_data"]["constraints_risks"]["canonical"]

    assert canonical_d1["system_type"] == "渠道接入"
    assert canonical_d1["business_domains"] == ["支付域"]
    assert canonical_d1["business_lines"] == ["支付结算", "渠道服务"]
    assert canonical_d1["architecture_layer"] == "3产品服务层"
    assert canonical_d1["target_users"] == ["柜面", "客户"]
    assert canonical_d1["core_responsibility"] == "支付统一受理"
    assert canonical_d1["system_aliases"] == ["PAY"]
    assert canonical_d3["provided_services"] == []
    assert canonical_d3["consumed_services"] == []
    assert canonical_d3["other_integrations"] == []
    assert canonical_d3["extensions"]["catalog_related_systems"] == ["核心账务", "柜面渠道"]
    assert canonical_d4["tech_stack"]["languages"] == ["Java", "SQL"]
    assert canonical_d4["tech_stack"]["databases"] == ["OceanBase"]
    assert canonical_d4["tech_stack"]["middleware"] == ["Tomcat"]
    assert canonical_d4["tech_stack"]["others"] == ["Linux", "x86", "云原生"]
    assert canonical_d5["extensions"]["dr_rto"] == "30"
    assert canonical_d5["extensions"]["dr_rpo"] == "5"
    assert profile["profile_data"]["business_capabilities"]["canonical"]["functional_modules"] == []

    field_source = profile["field_sources"]["system_positioning.canonical.core_responsibility"]
    assert field_source["source"] == "system_catalog"
    assert field_source["scene_id"] == "admin_system_catalog_import"

    memory_items = memory_service.get_memory_service().query_records("SYS-001", memory_type="profile_update")
    assert memory_items["total"] == 1
    assert memory_items["items"][0]["memory_subtype"] == "system_catalog_init"

    execution = runtime_execution_service.get_runtime_execution_service().get_execution(payload["execution_id"])
    assert execution["status"] == "completed"
    assert execution["result_summary"]["updated_system_ids"] == ["SYS-001"]
    assert execution["result_summary"]["updated_systems"] == [
        {"system_id": "SYS-001", "system_name": "统一支付平台"}
    ]

    artifact_service = profile_artifact_service.get_profile_artifact_service()
    workspace_path = artifact_service.repository.get_workspace_path(system_id="SYS-001")
    assert workspace_path
    workspace = Path(workspace_path)
    authoritative_candidate_dirs = list((workspace / "candidate" / "authoritative").glob("auth_cand_*"))
    assert len(authoritative_candidate_dirs) == 1
    assert (authoritative_candidate_dirs[0] / "authoritative_candidate.json").exists()

    with open(workspace / "candidate" / "latest" / "merged_candidates.json", "r", encoding="utf-8") as f:
        merged_candidates = json.load(f)
    core_responsibility_candidate = merged_candidates["system_positioning.canonical.core_responsibility"]
    assert core_responsibility_candidate["selected_value"] == "支付统一受理"
    assert core_responsibility_candidate["candidate_items"][0]["source_mode"] == "system_catalog"


def test_catalog_confirm_skips_non_blank_profiles_without_overwriting_existing_content(client):
    _seed_admin()
    token = _login(client, "admin", "admin123")

    profile_service = system_profile_service.get_system_profile_service()
    profile_service.upsert_profile(
        "统一支付平台",
        {
            "system_id": "SYS-001",
            "profile_data": {
                "system_positioning": {
                    "canonical": {
                        "system_type": "",
                        "business_domains": [],
                        "architecture_layer": "",
                        "target_users": [],
                        "core_responsibility": "人工维护范围",
                        "extensions": {},
                    }
                }
            },
        },
        actor={"username": "pm"},
    )
    profile_service.update_ai_suggestions_map(
        "统一支付平台",
        suggestions={
            "system_positioning.canonical.core_responsibility": {
                "value": "旧建议",
            }
        },
        actor={"username": "pm"},
    )

    response = client.post(
        "/api/v1/system-list/batch-import/confirm",
        json={"mode": "replace", "systems": [_catalog_system(system_id="SYS-001", system_name="统一支付平台", service_scope="导入值")]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["result_status"] == "success"
    assert payload["catalog_import_result"]["updated_system_ids"] == []
    assert payload["catalog_import_result"]["skipped_items"] == [
        {
            "system_id": "SYS-001",
            "system_name": "统一支付平台",
            "reason": "profile_not_blank",
        }
    ]

    profile = profile_service.get_profile("统一支付平台")
    assert profile["profile_data"]["system_positioning"]["canonical"]["core_responsibility"] == "人工维护范围"
    assert profile["ai_suggestions"]["system_positioning.canonical.core_responsibility"]["value"] == "旧建议"

    memory_items = memory_service.get_memory_service().query_records("SYS-001", memory_type="profile_update")
    assert memory_items["total"] == 0


def test_catalog_confirm_treats_field_sources_and_ai_suggestions_only_profile_as_blank(client):
    _seed_admin()
    token = _login(client, "admin", "admin123")

    profile_service = system_profile_service.get_system_profile_service()
    profile_service.upsert_profile(
        "渠道平台",
        {
            "system_id": "SYS-002",
            "profile_data": {},
            "field_sources": {
                "system_positioning.canonical.system_type": {
                    "source": "manual",
                    "scene_id": "profile_manual_edit",
                }
            },
        },
        actor={"username": "pm"},
    )
    profile_service.update_ai_suggestions_map(
        "渠道平台",
        suggestions={
            "system_positioning.canonical.core_responsibility": {
                "value": "建议范围",
            }
        },
        actor={"username": "pm"},
    )
    memory_service.get_memory_service().append_record(
        system_id="SYS-002",
        memory_type="profile_update",
        memory_subtype="document_suggestion",
        scene_id="pm_document_ingest",
        source_type="document",
        source_id="doc-001",
        summary="历史建议",
        payload={},
        decision_policy="suggestion_only",
        actor="pm",
    )

    response = client.post(
        "/api/v1/system-list/batch-import/confirm",
        json={"mode": "replace", "systems": [_catalog_system(system_id="SYS-002", system_name="渠道平台", service_scope="渠道统一入口")]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["catalog_import_result"]["updated_system_ids"] == ["SYS-002"]
    assert payload["catalog_import_result"]["skipped_items"] == []

    profile = profile_service.get_profile("渠道平台")
    assert profile["profile_data"]["system_positioning"]["canonical"]["core_responsibility"] == "渠道统一入口"
    assert profile["ai_suggestions"]["system_positioning.canonical.core_responsibility"]["value"] == "建议范围"
