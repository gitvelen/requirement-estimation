import json
import os

import pytest

from backend.api import system_routes
from backend.config.config import settings
from backend.service import profile_artifact_service as artifact_module


@pytest.fixture()
def artifact_service(tmp_path):
    root_dir = tmp_path / "profile_artifacts"
    return artifact_module.ProfileArtifactService(root_dir=str(root_dir))


def test_write_raw_document_creates_file_and_index(artifact_service):
    record = artifact_service.write_raw_document(
        system_id="sys_pay",
        doc_type="requirements",
        source_name="需求说明.docx",
        file_content=b"hello world",
        operator_id="manager_1",
        metadata={"scene": "manual_import"},
    )

    assert record["layer"] == "raw"
    assert record["system_id"] == "sys_pay"
    assert record["doc_type"] == "requirements"
    assert record["operator_id"] == "manager_1"
    assert record["status"] == "active"
    workspace_path = artifact_service.repository.get_workspace_path(system_id="sys_pay")
    assert workspace_path
    workspace_prefix = os.path.basename(workspace_path)
    assert record["path"].startswith(f"{workspace_prefix}/source/documents/src_doc_")
    assert record["path"].endswith("/raw.bin")
    assert record["meta_path"].startswith(f"{workspace_prefix}/source/documents/src_doc_")
    assert record["meta_path"].endswith("/meta.json")

    full_path = os.path.join(artifact_service.root_dir, record["path"])
    assert os.path.exists(full_path)
    with open(full_path, "rb") as f:
        assert f.read() == b"hello world"


def test_write_raw_document_is_append_only_even_same_content(artifact_service):
    first = artifact_service.write_raw_document(
        system_id="sys_pay",
        doc_type="requirements",
        source_name="需求说明.docx",
        file_content=b"same-bytes",
        operator_id="manager_1",
    )

    second = artifact_service.write_raw_document(
        system_id="sys_pay",
        doc_type="requirements",
        source_name="需求说明.docx",
        file_content=b"same-bytes",
        operator_id="manager_1",
    )

    assert first["artifact_id"] != second["artifact_id"]
    assert first["path"] != second["path"]

    items = artifact_service.list_layer_records(layer="raw", system_id="sys_pay", include_archived=True)
    assert len(items) == 2


def test_archive_raw_artifact_marks_record_archived(artifact_service):
    record = artifact_service.write_raw_document(
        system_id="sys_crm",
        doc_type="design",
        source_name="设计文档.docx",
        file_content=b"payload",
        operator_id="manager_2",
    )

    archived = artifact_service.archive_raw_artifact(
        system_id="sys_crm",
        artifact_id=record["artifact_id"],
        operator_id="admin_1",
        reason="duplicate_upload",
    )

    assert archived["status"] == "archived"
    assert archived["archived_by"] == "admin_1"
    assert archived["archive_reason"] == "duplicate_upload"

    active_items = artifact_service.list_layer_records(layer="raw", system_id="sys_crm")
    assert active_items == []

    all_items = artifact_service.list_layer_records(layer="raw", system_id="sys_crm", include_archived=True)
    assert len(all_items) == 1
    assert all_items[0]["status"] == "archived"


def test_append_layer_record_for_wiki_and_output(artifact_service):
    wiki_record = artifact_service.append_layer_record(
        layer="wiki",
        system_id="sys_pay",
        payload={"candidate_count": 3},
        operator_id="system",
        source_artifact_id="raw_001",
    )
    output_record = artifact_service.append_layer_record(
        layer="output",
        system_id="sys_pay",
        payload={"quality_score": 85},
        operator_id="system",
        source_artifact_id="wiki_001",
    )

    assert wiki_record["layer"] == "wiki"
    assert output_record["layer"] == "output"

    wiki_items = artifact_service.list_layer_records(layer="wiki", system_id="sys_pay")
    output_items = artifact_service.list_layer_records(layer="output", system_id="sys_pay")

    assert len(wiki_items) == 1
    assert wiki_items[0]["payload"]["candidate_count"] == 3
    assert len(output_items) == 1
    assert output_items[0]["payload"]["quality_score"] == 85


def test_archive_raw_artifact_raises_when_not_found(artifact_service):
    with pytest.raises(ValueError, match="artifact_not_found"):
        artifact_service.archive_raw_artifact(
            system_id="sys_pay",
            artifact_id="raw_not_exist",
            operator_id="admin",
            reason="cleanup",
        )


def test_get_profile_artifact_service_defaults_to_report_dir_system_profiles(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "REPORT_DIR", "data")
    monkeypatch.setattr(settings, "PROFILE_ARTIFACT_ROOT", "", raising=False)
    artifact_module._profile_artifact_service = None

    service = artifact_module.get_profile_artifact_service()

    assert service.root_dir == str((data_dir / "system_profiles").resolve())


def test_migrate_legacy_layout_moves_system_dirs_and_rewrites_runtime_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    artifact_root = data_dir / "system_profiles"
    runtime_path = data_dir / "runtime_executions.json"

    monkeypatch.setattr(system_routes, "CSV_PATH", str(data_dir / "system_list.csv"))
    system_routes._write_systems(
        [
            {
                "id": "sys_pay",
                "name": "统一支付",
                "abbreviation": "PAY",
                "status": "运行中",
                "extra": {},
            }
        ]
    )

    raw_dir = tmp_path / "raw" / "sys_pay"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_file = raw_dir / "20260410T010000Z__requirements__deadbeef__requirements.docx"
    raw_file.write_bytes(b"raw payload")
    raw_index_path = raw_dir / "index.json"
    raw_index_path.write_text(
        json.dumps(
            [
                {
                    "artifact_id": "raw_001",
                    "layer": "raw",
                    "system_id": "sys_pay",
                    "doc_type": "requirements",
                    "source_name": "requirements.docx",
                    "path": f"raw/sys_pay/{raw_file.name}",
                    "sha256": "deadbeef",
                    "size": len(b"raw payload"),
                    "created_at": "2026-04-10T01:00:00",
                    "operator_id": "manager_1",
                    "status": "active",
                    "metadata": {},
                }
            ],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    wiki_dir = tmp_path / "wiki" / "sys_pay"
    wiki_records_dir = wiki_dir / "records"
    wiki_records_dir.mkdir(parents=True, exist_ok=True)
    wiki_record = wiki_records_dir / "20260410T010001__wiki_001.json"
    wiki_record.write_text(json.dumps({"candidate_count": 1}, ensure_ascii=False), encoding="utf-8")
    wiki_latest = wiki_dir / "candidate_profile.json"
    wiki_latest.write_text(json.dumps({"system_id": "sys_pay"}, ensure_ascii=False), encoding="utf-8")
    (wiki_dir / "index.json").write_text(
        json.dumps(
            [
                {
                    "artifact_id": "wiki_001",
                    "layer": "wiki",
                    "system_id": "sys_pay",
                    "created_at": "2026-04-10T01:00:01",
                    "operator_id": "system",
                    "source_artifact_id": "raw_001",
                    "payload": {"candidate_count": 1},
                    "status": "active",
                    "path": f"wiki/sys_pay/records/{wiki_record.name}",
                    "latest_path": "wiki/sys_pay/candidate_profile.json",
                }
            ],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    output_dir = tmp_path / "output" / "sys_pay"
    output_records_dir = output_dir / "records"
    output_health_dir = output_dir / "health"
    output_records_dir.mkdir(parents=True, exist_ok=True)
    output_health_dir.mkdir(parents=True, exist_ok=True)
    output_record = output_records_dir / "20260410T010002__output_001.json"
    output_record.write_text(json.dumps({"quality_score": 88}, ensure_ascii=False), encoding="utf-8")
    output_latest = output_health_dir / "latest_report.json"
    output_latest.write_text(json.dumps({"artifact_id": "output_001"}, ensure_ascii=False), encoding="utf-8")
    (output_dir / "index.json").write_text(
        json.dumps(
            [
                {
                    "artifact_id": "output_001",
                    "layer": "output",
                    "system_id": "sys_pay",
                    "created_at": "2026-04-10T01:00:02",
                    "operator_id": "system",
                    "source_artifact_id": "wiki_001",
                    "payload": {"quality_score": 88},
                    "status": "active",
                    "path": f"output/sys_pay/records/{output_record.name}",
                    "latest_path": "output/sys_pay/health/latest_report.json",
                }
            ],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    runtime_path.write_text(
        json.dumps(
            [
                {
                    "execution_id": "exec_001",
                    "system_id": "sys_pay",
                    "input_snapshot": {
                        "raw_artifact_path": f"raw/sys_pay/{raw_file.name}",
                    },
                }
            ],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    service = artifact_module.ProfileArtifactService(root_dir=str(artifact_root))
    service.migrate_legacy_layout(
        legacy_root_dir=str(tmp_path),
        runtime_execution_path=str(runtime_path),
    )

    workspaces = list(artifact_root.glob("sid_sys_pay__*"))
    assert len(workspaces) == 1
    workspace = workspaces[0]
    workspace_prefix = workspace.name
    migrated_raw_index_path = workspace / "source" / "index.json"
    migrated_wiki_index_path = workspace / "candidate" / "index.json"
    migrated_output_index_path = workspace / "audit" / "index.json"

    assert workspace.exists()
    assert migrated_raw_index_path.exists()
    assert migrated_wiki_index_path.exists()
    assert migrated_output_index_path.exists()
    assert not raw_dir.exists()
    assert not wiki_dir.exists()
    assert not output_dir.exists()

    with open(migrated_raw_index_path, "r", encoding="utf-8") as f:
        migrated_raw_index = json.load(f)
    assert migrated_raw_index[0]["path"].startswith(f"{workspace_prefix}/source/documents/legacy_sys_pay/")
    assert os.path.exists(artifact_root / migrated_raw_index[0]["path"])

    with open(migrated_wiki_index_path, "r", encoding="utf-8") as f:
        migrated_wiki_index = json.load(f)
    assert migrated_wiki_index[0]["path"].startswith(f"{workspace_prefix}/candidate/legacy_sys_pay/")
    assert migrated_wiki_index[0]["latest_path"] == f"{workspace_prefix}/candidate/latest/candidate_profile.json"
    assert os.path.exists(artifact_root / migrated_wiki_index[0]["path"])
    assert os.path.exists(artifact_root / migrated_wiki_index[0]["latest_path"])

    with open(migrated_output_index_path, "r", encoding="utf-8") as f:
        migrated_output_index = json.load(f)
    assert migrated_output_index[0]["path"].startswith(f"{workspace_prefix}/audit/legacy_sys_pay/")
    assert migrated_output_index[0]["latest_path"] == f"{workspace_prefix}/audit/health/latest_report.json"
    assert os.path.exists(artifact_root / migrated_output_index[0]["path"])
    assert os.path.exists(artifact_root / migrated_output_index[0]["latest_path"])

    with open(runtime_path, "r", encoding="utf-8") as f:
        runtime_payload = json.load(f)
    assert runtime_payload[0]["input_snapshot"]["raw_artifact_path"].startswith(
        f"{workspace_prefix}/source/documents/legacy_sys_pay/"
    )


def test_migrate_legacy_layout_keeps_existing_workspace_system_name(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    artifact_root = data_dir / "system_profiles"
    runtime_path = data_dir / "runtime_executions.json"
    runtime_path.write_text("[]", encoding="utf-8")

    raw_dir = tmp_path / "raw" / "sys_pay"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_file = raw_dir / "foo.docx"
    raw_file.write_bytes(b"legacy")
    (raw_dir / "index.json").write_text(
        json.dumps(
            [
                {
                    "artifact_id": "raw_001",
                    "layer": "raw",
                    "system_id": "sys_pay",
                    "path": "raw/sys_pay/foo.docx",
                    "created_at": "2026-04-10T01:00:00",
                    "status": "active",
                }
            ],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    service = artifact_module.ProfileArtifactService(root_dir=str(artifact_root))
    service.repository.save_working_profile(
        {
            "system_id": "sys_pay",
            "system_name": "统一支付",
            "status": "draft",
            "profile_data": {},
        }
    )

    service.migrate_legacy_layout(
        legacy_root_dir=str(tmp_path),
        runtime_execution_path=str(runtime_path),
    )

    assert (artifact_root / "sid_sys_pay__统一支付").exists()
    assert not (artifact_root / "sid_sys_pay__sys_pay").exists()
