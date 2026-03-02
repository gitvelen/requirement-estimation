"""
证据等级服务（E0~E3）
负责证据等级规则加载/更新与系统级证据等级计算。
"""
from __future__ import annotations

import json
import logging
import os
import re
import threading
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    import fcntl
    FCNTL_AVAILABLE = True
except ImportError:
    FCNTL_AVAILABLE = False

from backend.config.config import settings
from backend.service.evidence_service import get_evidence_service
from backend.service.esb_service import get_esb_service
from backend.service.knowledge_service import get_knowledge_service
from backend.service.system_profile_service import get_system_profile_service

logger = logging.getLogger(__name__)


DEFAULT_RULES = {
    "version": 1,
    "levels": [
        {"level": "E3", "all_of": ["code"], "any_groups": [["evidence", "profile"]]},
        {"level": "E2", "any_groups": [["evidence", "profile"], ["code", "esb"]]},
        {"level": "E1", "any_of": ["evidence", "profile", "esb"]},
        {"level": "E0"},
    ],
    "updated_at": None,
    "updated_by": None,
}

SUPPORTED_EVIDENCE_SOURCES = ("evidence", "profile", "code", "esb")
SUPPORTED_EVIDENCE_LEVELS = ("E0", "E1", "E2", "E3")


class EvidenceLevelService:
    def __init__(self, rule_path: Optional[str] = None) -> None:
        self.rule_path = rule_path or os.path.join(settings.REPORT_DIR, "evidence_level_rules.json")
        self.lock_path = f"{self.rule_path}.lock"
        self._mutex = threading.RLock()

    @contextmanager
    def _lock(self):
        if FCNTL_AVAILABLE:
            os.makedirs(os.path.dirname(self.lock_path) or ".", exist_ok=True)
            with open(self.lock_path, "a") as lock_file:
                fcntl.flock(lock_file, fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(lock_file, fcntl.LOCK_UN)
        else:
            with self._mutex:
                yield

    def _load_rules_unlocked(self) -> Dict[str, Any]:
        if not os.path.exists(self.rule_path):
            return DEFAULT_RULES.copy()
        try:
            with open(self.rule_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and data.get("levels"):
                normalized = self._normalize_rules_payload(data)
                normalized["updated_at"] = data.get("updated_at")
                normalized["updated_by"] = data.get("updated_by")
                return normalized
        except Exception as exc:
            logger.warning(f"读取证据等级规则失败: {exc}")
        return DEFAULT_RULES.copy()

    def _save_rules_unlocked(self, rules: Dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(self.rule_path) or ".", exist_ok=True)
        tmp_path = f"{self.rule_path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(rules, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self.rule_path)

    def get_rules(self) -> Dict[str, Any]:
        with self._lock():
            return self._load_rules_unlocked()

    def _normalize_source_list(self, value: Any) -> List[str]:
        allowed = set(SUPPORTED_EVIDENCE_SOURCES)

        if isinstance(value, list):
            normalized = []
            for item in value:
                candidate = str(item or "").strip().lower()
                if candidate and candidate in allowed and candidate not in normalized:
                    normalized.append(candidate)
            return normalized

        if isinstance(value, str):
            normalized = []
            text = value.replace("，", ",").replace("、", ",").replace("；", ",")
            for part in re.split(r"[,;\n]+", text):
                candidate = str(part or "").strip().lower()
                if candidate and candidate in allowed and candidate not in normalized:
                    normalized.append(candidate)
            return normalized

        return []

    def _normalize_any_groups(self, value: Any) -> List[List[str]]:
        if isinstance(value, list):
            groups: List[List[str]] = []
            for item in value:
                group = self._normalize_source_list(item)
                if group:
                    groups.append(group)
            return groups

        if isinstance(value, str):
            groups = []
            for part in re.split(r"[|\n]+", value):
                group = self._normalize_source_list(part)
                if group:
                    groups.append(group)
            return groups

        return []

    def _normalize_level_item(self, item: Any) -> Dict[str, Any]:
        if isinstance(item, str):
            level = str(item or "").strip().upper()
            if level not in SUPPORTED_EVIDENCE_LEVELS:
                raise ValueError(f"不支持的证据等级: {item}")
            return {"level": level}

        if not isinstance(item, dict):
            raise ValueError("规则项格式不正确")

        level = str(item.get("level") or "").strip().upper()
        if level not in SUPPORTED_EVIDENCE_LEVELS:
            raise ValueError(f"不支持的证据等级: {item.get('level')}")

        normalized = {"level": level}
        all_of = self._normalize_source_list(item.get("all_of"))
        any_of = self._normalize_source_list(item.get("any_of"))
        none_of = self._normalize_source_list(item.get("none_of"))
        any_groups = self._normalize_any_groups(item.get("any_groups"))

        if all_of:
            normalized["all_of"] = all_of
        if any_of:
            normalized["any_of"] = any_of
        if none_of:
            normalized["none_of"] = none_of
        if any_groups:
            normalized["any_groups"] = any_groups

        return normalized

    def _normalize_rules_payload(self, rules: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(rules, dict):
            raise ValueError("规则格式不正确")

        raw_levels = rules.get("levels")
        if not isinstance(raw_levels, list) or not raw_levels:
            raise ValueError("规则格式不正确")

        normalized_levels = [self._normalize_level_item(item) for item in raw_levels]
        version = int(rules.get("version") or DEFAULT_RULES["version"])

        return {
            "version": version if version > 0 else DEFAULT_RULES["version"],
            "levels": normalized_levels,
        }

    def update_rules(self, rules: Dict[str, Any], actor: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        normalized = self._normalize_rules_payload(rules)
        payload = dict(normalized)
        payload["updated_at"] = datetime.now().isoformat()
        payload["updated_by"] = (actor or {}).get("id") or (actor or {}).get("username") or "unknown"
        with self._lock():
            self._save_rules_unlocked(payload)
        return payload

    def evaluate_system(
        self,
        system_name: str,
        system_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        name = str(system_name or "").strip()
        sid = str(system_id or "").strip()

        evidence_service = get_evidence_service()
        esb_service = get_esb_service()
        knowledge_service = get_knowledge_service()
        profile_service = get_system_profile_service()

        has_evidence = False
        has_profile = False
        has_code = False
        has_esb = False

        try:
            docs = evidence_service.list_docs(system_name=name or None, system_id=sid or None, limit=1)
            has_evidence = bool(docs)
        except Exception:
            has_evidence = False

        try:
            has_profile = profile_service.has_published_profile(name)
        except Exception:
            has_profile = False

        minimal_flags = {}
        try:
            minimal_flags = profile_service.get_minimal_profile_flags(name)
        except Exception:
            minimal_flags = {}

        try:
            if hasattr(knowledge_service.vector_store, "get_type_counts"):
                counts = knowledge_service.vector_store.get_type_counts(system_name=name)
                has_code = int(counts.get("capability_item", 0) or 0) > 0
        except Exception:
            has_code = False

        try:
            stats = esb_service.get_stats(system_id=sid or None, system_name=name or None)
            has_esb = int(stats.get("active_entry_count") or 0) > 0
        except Exception:
            has_esb = False

        sources = {
            "evidence": has_evidence,
            "profile": has_profile,
            "code": has_code,
            "esb": has_esb,
        }

        rules = self.get_rules()
        level = self._evaluate_level(sources, rules.get("levels") or [])

        # 最小画像兜底：无代码+无材料时，允许发布画像提升至E2
        if level in ("E0", "E1") and has_profile and not has_code and not has_evidence:
            if not minimal_flags.get("missing_minimal_fields"):
                level = "E2"

        missing_raw = [key for key, present in sources.items() if not present]
        missing = ["material" if item == "evidence" else item for item in missing_raw]
        risk_flags: List[str] = []
        if not has_code and not has_evidence:
            risk_flags.append("missing_code_material")
        if level == "E2" and has_profile and not has_code and not has_evidence:
            risk_flags.append("minimal_profile_only")

        return {
            "evidence_level": level,
            "missing_evidence": missing,
            "sources": sources,
            "risk_flags": risk_flags,
            "rules_version": rules.get("version"),
        }

    def _evaluate_level(self, sources: Dict[str, bool], levels: List[Dict[str, Any]]) -> str:
        for item in levels:
            level = str(item.get("level") or "").strip()
            if not level:
                continue
            if self._match_rule(sources, item):
                return level
        return "E0"

    def _match_rule(self, sources: Dict[str, bool], rule: Dict[str, Any]) -> bool:
        all_of = rule.get("all_of") or []
        any_of = rule.get("any_of") or []
        any_groups = rule.get("any_groups") or []
        none_of = rule.get("none_of") or []

        for key in all_of:
            if not sources.get(key, False):
                return False
        for key in none_of:
            if sources.get(key, False):
                return False
        if any_of:
            if not any(sources.get(key, False) for key in any_of):
                return False
        if any_groups:
            for group in any_groups:
                if not any(sources.get(key, False) for key in (group or [])):
                    return False
        return True


_evidence_level_service = None


def get_evidence_level_service() -> EvidenceLevelService:
    global _evidence_level_service
    if _evidence_level_service is None:
        _evidence_level_service = EvidenceLevelService()
    return _evidence_level_service
