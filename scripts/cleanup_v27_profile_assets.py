#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


V27_DOMAIN_KEYS = (
    "system_positioning",
    "business_capabilities",
    "integration_interfaces",
    "technical_architecture",
    "constraints_risks",
)
LEGACY_SCHEMA_KEYS = {
    "fields",
    "pending_fields",
    "system_scope",
    "module_structure",
    "integration_points",
    "architecture_positioning",
    "performance_profile",
    "key_constraints",
    "system_description",
    "boundaries",
    "core_processes",
    "external_dependencies",
}
PROFILE_STORE = "system_profiles.json"
IMPORT_HISTORY_STORE = "import_history.json"
KNOWLEDGE_STORE = "knowledge_store.json"


def _load_json(path: Path, expected_type: type) -> Any:
    if not path.exists():
        return expected_type()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path.name} JSON 解析失败: {exc.msg}") from exc
    if not isinstance(payload, expected_type):
        raise ValueError(f"{path.name} 数据结构非法，期望 {expected_type.__name__}")
    return payload


def _save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(f"{path.suffix}.tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(path)


def _contains_legacy_schema_key(value: Any) -> bool:
    if isinstance(value, dict):
        for key, nested in value.items():
            if str(key) in LEGACY_SCHEMA_KEYS:
                return True
            if _contains_legacy_schema_key(nested):
                return True
    elif isinstance(value, list):
        return any(_contains_legacy_schema_key(item) for item in value)
    return False


def _profile_data_is_legacy_shape(profile_data: Any) -> bool:
    if not isinstance(profile_data, dict):
        return False
    domain_hits = 0
    for domain_key in V27_DOMAIN_KEYS:
        domain_payload = profile_data.get(domain_key)
        if domain_payload is None:
            continue
        domain_hits += 1
        if not isinstance(domain_payload, dict):
            return True
        if "canonical" not in domain_payload:
            return True
    return False if domain_hits else False


def _is_legacy_profile_record(record: Any) -> bool:
    if not isinstance(record, dict):
        return False
    if _contains_legacy_schema_key(record):
        return True
    return _profile_data_is_legacy_shape(record.get("profile_data"))


def _count_history_report_imports(payload: Dict[str, Any]) -> int:
    total = 0
    for records in payload.values():
        if not isinstance(records, list):
            continue
        total += sum(1 for item in records if isinstance(item, dict) and str(item.get("doc_type") or "").strip() == "history_report")
    return total


def _count_history_report_knowledge(items: Iterable[Any]) -> int:
    total = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        if str(metadata.get("doc_type") or "").strip() == "history_report":
            total += 1
    return total


def _clean_profiles(items: List[Any]) -> Tuple[List[Any], int]:
    removed = 0
    kept: List[Any] = []
    for item in items:
        if _is_legacy_profile_record(item):
            removed += 1
            continue
        kept.append(item)
    return kept, removed


def _clean_import_history(payload: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    removed = 0
    cleaned: Dict[str, Any] = {}
    for system_id, records in payload.items():
        if not isinstance(records, list):
            cleaned[system_id] = records
            continue
        next_records = []
        for item in records:
            if isinstance(item, dict) and str(item.get("doc_type") or "").strip() == "history_report":
                removed += 1
                continue
            next_records.append(item)
        if next_records:
            cleaned[system_id] = next_records
    return cleaned, removed


def _clean_knowledge_items(items: List[Any]) -> Tuple[List[Any], int]:
    removed = 0
    kept: List[Any] = []
    for item in items:
        if not isinstance(item, dict):
            kept.append(item)
            continue
        metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        if str(metadata.get("doc_type") or "").strip() == "history_report":
            removed += 1
            continue
        kept.append(item)
    return kept, removed


def _backup_files(backup_dir: Path, files: Iterable[Path]) -> List[str]:
    backup_dir.mkdir(parents=True, exist_ok=True)
    copied: List[str] = []
    for file_path in files:
        if not file_path.exists():
            continue
        shutil.copy2(file_path, backup_dir / file_path.name)
        copied.append(file_path.name)
    return copied


def _build_default_backup_dir(data_dir: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return data_dir / f"backup_v27_cleanup_{timestamp}"


def run_cleanup(data_dir: Path, backup_dir: Path | None = None) -> Dict[str, Any]:
    system_profiles_path = data_dir / PROFILE_STORE
    import_history_path = data_dir / IMPORT_HISTORY_STORE
    knowledge_store_path = data_dir / KNOWLEDGE_STORE

    profiles = _load_json(system_profiles_path, list)
    import_history = _load_json(import_history_path, dict)
    knowledge_items = _load_json(knowledge_store_path, list)

    before_profile_count = sum(1 for item in profiles if _is_legacy_profile_record(item))
    before_history_report_import_count = _count_history_report_imports(import_history)
    before_history_report_knowledge_count = _count_history_report_knowledge(knowledge_items)

    cleaned_profiles, removed_profiles = _clean_profiles(profiles)
    cleaned_import_history, removed_imports = _clean_import_history(import_history)
    cleaned_knowledge_items, removed_knowledge_items = _clean_knowledge_items(knowledge_items)

    changed_files: List[Path] = []
    if removed_profiles > 0:
        changed_files.append(system_profiles_path)
    if removed_imports > 0:
        changed_files.append(import_history_path)
    if removed_knowledge_items > 0:
        changed_files.append(knowledge_store_path)

    resolved_backup_dir: Path | None = None
    backed_up_files: List[str] = []
    if changed_files:
        resolved_backup_dir = backup_dir or _build_default_backup_dir(data_dir)
        backed_up_files = _backup_files(resolved_backup_dir, changed_files)
        _save_json(system_profiles_path, cleaned_profiles)
        _save_json(import_history_path, cleaned_import_history)
        _save_json(knowledge_store_path, cleaned_knowledge_items)

    return {
        "status": "success",
        "data_dir": str(data_dir),
        "backup_dir": str(resolved_backup_dir) if resolved_backup_dir else None,
        "backed_up_files": backed_up_files,
        "counts": {
            "legacy_profile_records": {
                "before": before_profile_count,
                "removed": removed_profiles,
                "after": sum(1 for item in cleaned_profiles if _is_legacy_profile_record(item)),
            },
            "history_report_import_records": {
                "before": before_history_report_import_count,
                "removed": removed_imports,
                "after": _count_history_report_imports(cleaned_import_history),
            },
            "history_report_knowledge_records": {
                "before": before_history_report_knowledge_count,
                "removed": removed_knowledge_items,
                "after": _count_history_report_knowledge(cleaned_knowledge_items),
            },
        },
    }


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="清理 v2.7 旧 schema 与 history_report 存量数据")
    parser.add_argument("--data-dir", default="data", help="数据目录，默认 data")
    parser.add_argument("--backup-dir", default="", help="备份目录；未传时自动按时间戳生成")
    args = parser.parse_args(argv)

    data_dir = Path(args.data_dir).resolve()
    backup_dir = Path(args.backup_dir).resolve() if str(args.backup_dir).strip() else None

    try:
        result = run_cleanup(data_dir=data_dir, backup_dir=backup_dir)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "failed",
                    "data_dir": str(data_dir),
                    "error": str(exc),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
