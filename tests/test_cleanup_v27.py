import json
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]


def _write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _run_cleanup(data_dir: Path, backup_dir: Path):
    return subprocess.run(
        [
            sys.executable,
            str(ROOT_DIR / "scripts" / "cleanup_v27_profile_assets.py"),
            "--data-dir",
            str(data_dir),
            "--backup-dir",
            str(backup_dir),
        ],
        cwd=str(ROOT_DIR),
        capture_output=True,
        text=True,
    )


def test_cleanup_v27_removes_legacy_profiles_and_history_report_assets(tmp_path):
    data_dir = tmp_path / "data"
    backup_dir = tmp_path / "backup"

    v27_profile = {
        "system_name": "支付系统",
        "system_id": "SYS-PAY",
        "profile_data": {
            "system_positioning": {
                "canonical": {
                    "system_type": "业务系统",
                    "business_domain": ["支付"],
                    "architecture_layer": "",
                    "target_users": [],
                    "service_scope": "统一支付受理",
                    "system_boundary": [],
                    "extensions": {},
                }
            },
            "business_capabilities": {"canonical": {"functional_modules": [], "business_processes": [], "data_assets": [], "extensions": {}}},
            "integration_interfaces": {"canonical": {"provided_services": [], "consumed_services": [], "other_integrations": [], "extensions": {}}},
            "technical_architecture": {
                "canonical": {
                    "architecture_style": "",
                    "tech_stack": {"languages": [], "frameworks": [], "databases": [], "middleware": [], "others": []},
                    "network_zone": "",
                    "performance_baseline": {
                        "online": {"peak_tps": "", "p95_latency_ms": "", "availability_target": ""},
                        "batch": {"window": "", "data_volume": "", "peak_duration": ""},
                        "processing_model": "",
                    },
                    "extensions": {},
                }
            },
            "constraints_risks": {"canonical": {"technical_constraints": [], "business_constraints": [], "known_risks": [], "extensions": {}}},
        },
    }
    legacy_profile_with_fields = {
        "system_name": "老系统A",
        "fields": {
            "system_scope": "老边界",
            "module_structure": [{"module_name": "开户"}],
        },
        "profile_data": {
            "system_positioning": {"system_description": "老描述"},
            "business_capabilities": {"module_structure": [{"module_name": "开户"}]},
        },
    }
    legacy_profile_without_profile_data = {
        "system_name": "老系统B",
        "fields": {
            "system_scope": "仅旧字段",
        },
    }
    _write_json(
        data_dir / "system_profiles.json",
        [v27_profile, legacy_profile_with_fields, legacy_profile_without_profile_data],
    )

    _write_json(
        data_dir / "import_history.json",
        {
            "SYS-PAY": [
                {"id": "h1", "doc_type": "history_report", "file_name": "history.xlsx"},
                {"id": "h2", "doc_type": "requirements", "file_name": "req.docx"},
            ],
            "SYS-CRM": [
                {"id": "h3", "doc_type": "design", "file_name": "design.docx"},
            ],
        },
    )

    _write_json(
        data_dir / "knowledge_store.json",
        [
            {
                "id": "k1",
                "system_name": "支付系统",
                "knowledge_type": "document",
                "content": "旧评估报告内容",
                "embedding": [0.1, 0.2],
                "embedding_norm": 0.3,
                "metadata": {"doc_type": "history_report", "source_filename": "history.xlsx"},
                "source_file": "history.xlsx",
            },
            {
                "id": "k2",
                "system_name": "支付系统",
                "knowledge_type": "document",
                "content": "需求文档内容",
                "embedding": [0.2, 0.3],
                "embedding_norm": 0.36,
                "metadata": {"doc_type": "requirements", "source_filename": "req.docx"},
                "source_file": "req.docx",
            },
        ],
    )

    result = _run_cleanup(data_dir, backup_dir)

    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    payload = json.loads(result.stdout)
    assert payload["status"] == "success"
    assert payload["counts"]["legacy_profile_records"]["before"] == 2
    assert payload["counts"]["legacy_profile_records"]["after"] == 0
    assert payload["counts"]["history_report_import_records"]["before"] == 1
    assert payload["counts"]["history_report_import_records"]["after"] == 0
    assert payload["counts"]["history_report_knowledge_records"]["before"] == 1
    assert payload["counts"]["history_report_knowledge_records"]["after"] == 0

    profiles = json.loads((data_dir / "system_profiles.json").read_text(encoding="utf-8"))
    assert profiles == [v27_profile]

    import_history = json.loads((data_dir / "import_history.json").read_text(encoding="utf-8"))
    assert [item["doc_type"] for item in import_history["SYS-PAY"]] == ["requirements"]
    assert [item["doc_type"] for item in import_history["SYS-CRM"]] == ["design"]

    knowledge_items = json.loads((data_dir / "knowledge_store.json").read_text(encoding="utf-8"))
    assert len(knowledge_items) == 1
    assert knowledge_items[0]["metadata"]["doc_type"] == "requirements"

    assert (backup_dir / "system_profiles.json").exists()
    assert (backup_dir / "import_history.json").exists()
    assert (backup_dir / "knowledge_store.json").exists()


def test_cleanup_v27_reports_failure_when_json_is_invalid(tmp_path):
    data_dir = tmp_path / "data"
    backup_dir = tmp_path / "backup"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "system_profiles.json").write_text("{broken json", encoding="utf-8")

    result = _run_cleanup(data_dir, backup_dir)

    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "failed"
    assert "system_profiles.json" in payload["error"]
