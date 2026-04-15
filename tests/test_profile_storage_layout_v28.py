from pathlib import Path

from backend.config.config import settings
from backend.service import profile_artifact_service as artifact_module


def test_profile_artifact_root_defaults_to_report_dir_system_profiles(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(settings, "REPORT_DIR", str(data_dir))
    monkeypatch.setattr(settings, "PROFILE_ARTIFACT_ROOT", "", raising=False)
    monkeypatch.setattr(settings, "SYSTEM_PROFILE_ROOT", "", raising=False)
    artifact_module._profile_artifact_service = None

    service = artifact_module.get_profile_artifact_service()

    assert service.root_dir == str((data_dir / "system_profiles").resolve())


def test_raw_document_is_written_under_system_workspace_source_directory(tmp_path):
    root_dir = tmp_path / "system_profiles"
    service = artifact_module.ProfileArtifactService(root_dir=str(root_dir))

    record = service.write_raw_document(
        system_id="sys_pay_layout",
        doc_type="requirements",
        source_name="需求说明书.docx",
        file_content=b"hello world",
        operator_id="tester",
        metadata={"system_name": "统一支付"},
    )

    path = Path(service.root_dir) / record["path"]
    assert path.exists()
    assert "source/documents" in record["path"]
