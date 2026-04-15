import json
from pathlib import Path

from backend.config.config import settings
from backend.service.system_profile_repository import SystemProfileRepository


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_repository_persists_working_and_published_profiles_in_system_workspace(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "REPORT_DIR", str(data_dir))
    monkeypatch.setattr(settings, "PROFILE_ARTIFACT_ROOT", "", raising=False)
    monkeypatch.setattr(settings, "SYSTEM_PROFILE_ROOT", "", raising=False)

    repo = SystemProfileRepository()
    working_profile = {
        "system_id": "sys_pay_repo",
        "system_name": "统一支付",
        "status": "draft",
        "profile_data": {
            "system_positioning": {
                "canonical": {
                    "service_scope": "支付统一受理",
                }
            }
        },
        "field_sources": {},
        "ai_suggestions": {},
        "evidence_refs": [],
    }
    published_profile = {
        **working_profile,
        "status": "published",
        "published_at": "2026-04-10T15:00:00",
    }

    repo.save_working_profile(working_profile)
    repo.save_published_profile(published_profile)

    system_root = data_dir / "system_profiles"
    workspaces = list(system_root.glob("sid_*__统一支付"))
    assert len(workspaces) == 1

    workspace = workspaces[0]
    assert (workspace / "manifest.json").exists()
    assert (workspace / "profile" / "working.json").exists()
    assert (workspace / "profile" / "published.json").exists()
    assert len(list((workspace / "profile" / "revisions").glob("rev_*.json"))) >= 2
    assert not (data_dir / "system_profiles.json").exists()

    manifest = _load_json(workspace / "manifest.json")
    assert manifest["system_id"] == "sys_pay_repo"
    assert manifest["system_name"] == "统一支付"

    working = _load_json(workspace / "profile" / "working.json")
    assert working["status"] == "draft"
    assert working["profile_data"]["system_positioning"]["canonical"]["service_scope"] == "支付统一受理"

    published = _load_json(workspace / "profile" / "published.json")
    assert published["status"] == "published"
    assert published["published_at"] == "2026-04-10T15:00:00"


def test_repository_delete_workspace_removes_all_workspace_layers(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "REPORT_DIR", str(data_dir))
    monkeypatch.setattr(settings, "PROFILE_ARTIFACT_ROOT", "", raising=False)
    monkeypatch.setattr(settings, "SYSTEM_PROFILE_ROOT", "", raising=False)

    repo = SystemProfileRepository()
    workspace_path, _ = repo.ensure_workspace(system_id="sys_pay_repo", system_name="统一支付")

    repo.save_working_profile(
        {
            "system_id": "sys_pay_repo",
            "system_name": "统一支付",
            "status": "draft",
            "profile_data": {
                "system_positioning": {
                    "canonical": {
                        "service_scope": "支付统一受理",
                    }
                }
            },
            "field_sources": {},
            "ai_suggestions": {},
            "evidence_refs": [],
        }
    )
    repo.append_import_history(
        system_id="sys_pay_repo",
        system_name="统一支付",
        item={"id": "hist_001", "file_name": "requirements.docx", "status": "success"},
    )
    repo.save_extraction_task(
        system_id="sys_pay_repo",
        system_name="统一支付",
        task={"task_id": "task_001", "status": "completed"},
    )

    workspace = Path(workspace_path)
    raw_file = workspace / "source" / "documents" / "src_doc_001" / "raw.bin"
    raw_file.parent.mkdir(parents=True, exist_ok=True)
    raw_file.write_bytes(b"raw payload")
    candidate_file = workspace / "candidate" / "latest" / "candidate_profile.json"
    candidate_file.parent.mkdir(parents=True, exist_ok=True)
    candidate_file.write_text("{}", encoding="utf-8")
    audit_file = workspace / "audit" / "health" / "latest_report.json"
    audit_file.parent.mkdir(parents=True, exist_ok=True)
    audit_file.write_text("{}", encoding="utf-8")

    deleted = repo.delete_workspace(system_id="sys_pay_repo")

    assert deleted["deleted"] is True
    assert deleted["system_id"] == "sys_pay_repo"
    assert deleted["system_name"] == "统一支付"
    assert deleted["workspace_path"] == str(workspace)
    assert not workspace.exists()
    assert repo.get_workspace_path(system_id="sys_pay_repo") is None
    assert repo.load_profile(state="working", system_id="sys_pay_repo") is None
    assert repo.get_import_history(system_id="sys_pay_repo") == []
    assert repo.get_extraction_task(system_id="sys_pay_repo") is None


def test_repository_load_profile_prefers_manifest_system_identity_over_stale_payload(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "REPORT_DIR", str(data_dir))
    monkeypatch.setattr(settings, "PROFILE_ARTIFACT_ROOT", "", raising=False)
    monkeypatch.setattr(settings, "SYSTEM_PROFILE_ROOT", "", raising=False)

    repo = SystemProfileRepository()
    repo.save_working_profile(
        {
            "system_id": "sys_new",
            "system_name": "贷款核算",
            "status": "draft",
            "profile_data": {
                "system_positioning": {
                    "canonical": {
                        "service_scope": "贷款核算处理",
                    }
                }
            },
            "field_sources": {},
            "ai_suggestions": {},
            "evidence_refs": [],
        }
    )

    workspace = next((data_dir / "system_profiles").glob("sid_*__贷款核算"))
    working_path = workspace / "profile" / "working.json"
    working_payload = _load_json(working_path)
    working_payload["system_id"] = "sys_old"
    working_payload["system_name"] = "旧贷款核算"
    working_path.write_text(json.dumps(working_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    loaded = repo.load_profile(state="working", system_id="sys_new")
    listed = repo.list_profiles(state="working")

    assert loaded is not None
    assert loaded["system_id"] == "sys_new"
    assert loaded["system_name"] == "贷款核算"
    assert listed[0]["system_id"] == "sys_new"
    assert listed[0]["system_name"] == "贷款核算"
