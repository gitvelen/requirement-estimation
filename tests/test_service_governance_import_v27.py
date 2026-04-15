import os
import sys
import json
from io import BytesIO
from pathlib import Path

from openpyxl import Workbook

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.api import system_routes
from backend.config.config import settings
from backend.service import memory_service
from backend.service import profile_artifact_service
from backend.service import runtime_execution_service
from backend.service import system_profile_service
from backend.service.service_governance_profile_updater import ServiceGovernanceProfileUpdater


def _build_governance_workbook() -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "服务治理"
    ws.append(["系统名称", "服务场景码", "交易名称", "消费方系统名称", "状态"])
    ws.append(["统一支付平台", "SC001", "支付查询", "核心账务", "正常使用"])
    ws.append(["统一支付平台", "SC002", "支付扣款", "柜面渠道", "正常使用"])
    ws.append(["信贷核心", "SC003", "放款通知", "统一支付平台", "正常使用"])
    ws.append(["未知系统", "SC004", "孤立服务", "测试系统", "正常使用"])

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def _build_governance_workbook_with_bracket_alias() -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "服务治理"
    ws.append(["系统名称", "服务场景码", "交易名称", "消费方系统名称", "状态"])
    ws.append(["客户信息管理(小账管)", "SC001", "客户信息同步", "核心账务", "正常使用"])

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def _seed_systems():
    system_routes._write_systems(
        [
            {
                "id": "SYS-001",
                "name": "统一支付平台",
                "abbreviation": "PAY",
                "status": "运行中",
                "extra": {},
            },
            {
                "id": "SYS-002",
                "name": "信贷核心",
                "abbreviation": "LOAN",
                "status": "运行中",
                "extra": {},
            },
        ]
    )


def test_service_governance_import_accepts_latest_esb_template(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(settings, "REPORT_DIR", str(data_dir))
    monkeypatch.setattr(settings, "ENABLE_V27_PROFILE_SCHEMA", True)
    monkeypatch.setattr(settings, "ENABLE_V27_RUNTIME", True)
    monkeypatch.setattr(settings, "ENABLE_SERVICE_GOVERNANCE_IMPORT", True)
    system_profile_service._system_profile_service = None
    memory_service._memory_service = None
    runtime_execution_service._runtime_execution_service = None

    system_routes._write_systems(
        [
            {
                "id": "SYS-OAS",
                "name": "办公自动化",
                "abbreviation": "OAS",
                "status": "运行中",
                "extra": {},
            },
            {
                "id": "SYS-IRBS",
                "name": "智能报销",
                "abbreviation": "IRBS",
                "status": "运行中",
                "extra": {},
            },
        ]
    )

    template_path = Path(__file__).resolve().parents[1] / "data" / "esb-template.xlsx"
    updater = ServiceGovernanceProfileUpdater()
    result = updater.import_governance(
        file_content=template_path.read_bytes(),
        filename="esb-template.xlsx",
        actor={"username": "admin"},
    )

    assert result["matched_count"] == 1
    assert result["unmatched_count"] == 0
    assert result["updated_system_ids"] == ["SYS-IRBS", "SYS-OAS"]
    assert result["status"] == "completed"

    profile = system_profile_service.get_system_profile_service().get_profile("办公自动化")
    d3 = profile["profile_data"]["integration_interfaces"]["canonical"]
    assert d3["provided_services"][0]["service_name"] == "处理流程"
    assert d3["provided_services"][0]["transaction_name"] == "cus提交流程"
    assert d3["provided_services"][0]["peer_system"] == "智能报销"
    assert d3["extensions"]["governance_summary"]["matched_rows"] == 1

    consumer_profile = system_profile_service.get_system_profile_service().get_profile("智能报销")
    consumer_d3 = consumer_profile["profile_data"]["integration_interfaces"]["canonical"]
    assert consumer_d3["consumed_services"][0]["peer_system"] == "办公自动化"


def test_service_governance_import_updates_d3_and_returns_match_statistics(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(settings, "REPORT_DIR", str(data_dir))
    monkeypatch.setattr(settings, "ENABLE_V27_PROFILE_SCHEMA", True)
    monkeypatch.setattr(settings, "ENABLE_V27_RUNTIME", True)
    monkeypatch.setattr(settings, "ENABLE_SERVICE_GOVERNANCE_IMPORT", True)
    system_profile_service._system_profile_service = None
    memory_service._memory_service = None
    runtime_execution_service._runtime_execution_service = None

    _seed_systems()

    updater = ServiceGovernanceProfileUpdater()
    result = updater.import_governance(
        file_content=_build_governance_workbook(),
        filename="治理模板.xlsx",
        actor={"username": "admin"},
    )

    assert result["matched_count"] == 3
    assert result["unmatched_count"] == 1
    assert result["updated_system_ids"] == ["SYS-001", "SYS-002"]
    assert result["status"] == "completed"

    profile = system_profile_service.get_system_profile_service().get_profile("统一支付平台")
    d3 = profile["profile_data"]["integration_interfaces"]["canonical"]
    assert len(d3["provided_services"]) == 2
    assert d3["provided_services"][0]["service_name"] == "支付查询"
    assert d3["provided_services"][0]["transaction_name"] == "支付查询"
    assert d3["extensions"]["governance_summary"]["active_provider_count"] == 2

    memory_items = memory_service.get_memory_service().query_records("SYS-001", memory_type="profile_update")
    assert memory_items["total"] == 1
    assert memory_items["items"][0]["memory_subtype"] == "service_governance"
    assert result["updated_systems"] == [
        {"system_id": "SYS-001", "system_name": "统一支付平台"},
        {"system_id": "SYS-002", "system_name": "信贷核心"},
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
    provided_services = merged_candidates["integration_interfaces.canonical.provided_services"]
    assert provided_services["candidate_items"][0]["source_mode"] == "governance"
    assert provided_services["selected_value"][0]["service_name"] == "支付查询"


def test_service_governance_import_matches_names_after_ignoring_parentheses(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(settings, "REPORT_DIR", str(data_dir))
    monkeypatch.setattr(settings, "ENABLE_V27_PROFILE_SCHEMA", True)
    monkeypatch.setattr(settings, "ENABLE_V27_RUNTIME", True)
    monkeypatch.setattr(settings, "ENABLE_SERVICE_GOVERNANCE_IMPORT", True)
    system_profile_service._system_profile_service = None
    memory_service._memory_service = None
    runtime_execution_service._runtime_execution_service = None

    system_routes._write_systems(
        [
            {
                "id": "SYS-ECIF",
                "name": "客户信息管理",
                "abbreviation": "ECIF",
                "status": "运行中",
                "extra": {},
            },
            {
                "id": "SYS-CORE",
                "name": "核心账务",
                "abbreviation": "CORE",
                "status": "运行中",
                "extra": {},
            },
        ]
    )

    updater = ServiceGovernanceProfileUpdater()
    result = updater.import_governance(
        file_content=_build_governance_workbook_with_bracket_alias(),
        filename="治理模板.xlsx",
        actor={"username": "admin"},
    )

    assert result["matched_count"] == 1
    assert result["unmatched_count"] == 0
    assert result["updated_system_ids"] == ["SYS-CORE", "SYS-ECIF"]
    assert result["updated_systems"] == [
        {"system_id": "SYS-CORE", "system_name": "核心账务"},
        {"system_id": "SYS-ECIF", "system_name": "客户信息管理"},
    ]

    profile = system_profile_service.get_system_profile_service().get_profile("客户信息管理")
    d3 = profile["profile_data"]["integration_interfaces"]["canonical"]
    assert d3["provided_services"][0]["service_name"] == "客户信息同步"
    assert d3["provided_services"][0]["transaction_name"] == "客户信息同步"
    assert d3["provided_services"][0]["peer_system"] == "核心账务"


def test_service_governance_import_skips_manual_d3_field_but_keeps_other_updates(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(settings, "REPORT_DIR", str(data_dir))
    monkeypatch.setattr(settings, "ENABLE_V27_PROFILE_SCHEMA", True)
    monkeypatch.setattr(settings, "ENABLE_V27_RUNTIME", True)
    monkeypatch.setattr(settings, "ENABLE_SERVICE_GOVERNANCE_IMPORT", True)
    system_profile_service._system_profile_service = None

    _seed_systems()
    profile_service = system_profile_service.get_system_profile_service()
    profile_service.upsert_profile(
        "统一支付平台",
        {
            "system_id": "SYS-001",
            "profile_data": {
                "system_positioning": {"canonical": {}},
                "business_capabilities": {"canonical": {}},
                "integration_interfaces": {
                    "canonical": {
                        "provided_services": [{"service_name": "人工维护服务"}],
                        "consumed_services": [],
                        "other_integrations": [],
                        "extensions": {},
                    }
                },
                "technical_architecture": {"canonical": {}},
                "constraints_risks": {"canonical": {}},
            },
            "field_sources": {
                "integration_interfaces.canonical.provided_services": {
                    "source": "manual",
                    "scene_id": "profile_manual_edit",
                }
            },
            "evidence_refs": [],
        },
        actor={"username": "pm"},
    )

    updater = ServiceGovernanceProfileUpdater()
    result = updater.import_governance(
        file_content=_build_governance_workbook(),
        filename="治理模板.xlsx",
        actor={"username": "admin"},
    )

    assert result["status"] == "completed"

    profile = profile_service.get_profile("统一支付平台")
    d3 = profile["profile_data"]["integration_interfaces"]["canonical"]
    assert d3["provided_services"] == [{"service_name": "人工维护服务"}]
    assert len(d3["consumed_services"]) == 1
