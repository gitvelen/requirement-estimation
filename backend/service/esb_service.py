"""
ESB 明细索引服务（本期文件存储）
支持导入/检索/统计/状态过滤
"""
from __future__ import annotations

import json
import logging
import math
import os
import threading
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

try:
    import fcntl
    FCNTL_AVAILABLE = True
except ImportError:
    FCNTL_AVAILABLE = False

from backend.config.config import settings
from backend.service.document_parser import get_document_parser
from backend.service.embedding_service import get_embedding_service

logger = logging.getLogger(__name__)


class EsbService:
    DEFAULT_VALID_STATUSES = ["正常使用"]
    DEFAULT_SCOPE = "both"

    REQUIRED_FIELDS = ("provider_system_id", "consumer_system_id", "service_name", "status")

    FIELD_ALIASES = {
        "service_code": ["交易码", "交易代码", "服务码", "服务代码"],
        "scenario_code": ["服务场景码", "场景码", "场景代码", "服务场景代码"],
        "provider_system_id": ["提供方系统简称", "提供方系统标识", "提供方系统编号", "提供方系统代码", "提供方系统ID", "提供方系统"],
        "provider_system_name": ["提供方中文名称", "提供方系统名称", "提供方系统中文名", "提供方名称"],
        "service_name": ["交易名称", "服务名称", "服务名", "交易名"],
        "consumer_system_id": ["调用方系统简称", "调用方系统标识", "调用方系统编号", "调用方系统代码", "调用方系统ID", "调用方系统"],
        "consumer_system_name": ["调用方中文名称", "调用方系统名称", "调用方系统中文名", "调用方名称"],
        "status": ["状态", "使用状态", "生效状态"],
        "remark": ["备注", "说明", "备注信息"],
    }

    SUMMARY_ALIASES = {
        "system_id": ["系统标识", "系统简称", "系统编码", "系统ID"],
        "system_name": ["系统名称"],
        "owner": ["系统负责人", "负责人"],
        "center": ["所属中心", "所属部门"],
        "total_interface_count": ["总接口", "接口总数", "总接口数"],
        "no_call_interface_count": ["无调用接口", "无调用接口数"],
    }

    def __init__(self):
        self.store_path = os.path.join(settings.REPORT_DIR, "esb_index.json")
        self.lock_path = f"{self.store_path}.lock"
        self._mutex = threading.RLock()
        self.document_parser = get_document_parser()
        self.embedding_service = None

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

    def _load_unlocked(self) -> Dict[str, Any]:
        if not os.path.exists(self.store_path):
            return {
                "meta": {
                    "valid_statuses": self.DEFAULT_VALID_STATUSES,
                    "default_scope": self.DEFAULT_SCOPE,
                    "updated_at": None,
                },
                "entries": [],
                "system_summary": [],
            }
        try:
            with open(self.store_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("invalid esb store")
            data.setdefault("meta", {})
            data.setdefault("entries", [])
            data.setdefault("system_summary", [])
            meta = data["meta"]
            if not meta.get("valid_statuses"):
                meta["valid_statuses"] = self.DEFAULT_VALID_STATUSES
            if not meta.get("default_scope"):
                meta["default_scope"] = self.DEFAULT_SCOPE
            return data
        except Exception as exc:
            logger.warning(f"读取ESB索引失败: {exc}")
            return {
                "meta": {
                    "valid_statuses": self.DEFAULT_VALID_STATUSES,
                    "default_scope": self.DEFAULT_SCOPE,
                    "updated_at": None,
                },
                "entries": [],
                "system_summary": [],
            }

    def _save_unlocked(self, data: Dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(self.store_path) or ".", exist_ok=True)
        tmp_path = f"{self.store_path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self.store_path)

    @contextmanager
    def _store_context(self):
        with self._lock():
            data = self._load_unlocked()
            yield data
            self._save_unlocked(data)

    def _ensure_embedding_service(self):
        if self.embedding_service is None:
            self.embedding_service = get_embedding_service()
        return self.embedding_service

    def _normalize_header(self, value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    def _build_header_map(self, header_row: List[Any]) -> Dict[str, int]:
        header_map: Dict[str, int] = {}
        for idx, cell in enumerate(header_row or []):
            key = self._normalize_header(cell)
            if key and key not in header_map:
                header_map[key] = idx
        return header_map

    def _resolve_mapping(self, header_map: Dict[str, int], mapping_override: Dict[str, str], aliases: Dict[str, List[str]]) -> Dict[str, str]:
        resolved: Dict[str, str] = {}
        for field, candidates in aliases.items():
            if mapping_override and mapping_override.get(field):
                col_name = str(mapping_override[field]).strip()
                if col_name in header_map:
                    resolved[field] = col_name
                    continue
            for candidate in candidates:
                if candidate in header_map:
                    resolved[field] = candidate
                    break
        return resolved

    def _rows_to_dicts(self, rows: List[List[Any]]) -> List[Dict[str, Any]]:
        if not rows:
            return []
        header_row = rows[0]
        header_map = self._build_header_map(header_row)
        if not header_map:
            return []
        data_rows = rows[1:]
        result = []
        for row in data_rows:
            if not row or not any(cell is not None and str(cell).strip() != "" for cell in row):
                continue
            row_dict = {}
            for key, idx in header_map.items():
                if idx < len(row):
                    row_dict[key] = row[idx]
            result.append(row_dict)
        return result

    def _parse_file(self, file_content: bytes, filename: str) -> Dict[str, List[Dict[str, Any]]]:
        parsed = self.document_parser.parse(file_content, filename)
        if isinstance(parsed, list):
            return {"_default": parsed}
        if isinstance(parsed, dict):
            # XLSX -> {sheet: rows}
            if parsed and all(isinstance(v, list) for v in parsed.values()):
                sheet_dict: Dict[str, List[Dict[str, Any]]] = {}
                for sheet_name, rows in parsed.items():
                    if isinstance(rows, list):
                        sheet_dict[sheet_name] = self._rows_to_dicts(rows)
                return sheet_dict
        return {}

    def _build_entry_text(self, entry: Dict[str, Any]) -> str:
        return (
            f"{entry.get('service_name','')} "
            f"提供方:{entry.get('provider_system_name') or entry.get('provider_system_id','')} "
            f"调用方:{entry.get('consumer_system_name') or entry.get('consumer_system_id','')} "
            f"场景:{entry.get('scenario_code','')} "
            f"交易码:{entry.get('service_code','')}"
        ).strip()

    def import_esb(
        self,
        file_content: bytes,
        filename: str,
        mapping_json: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        mapping_json = mapping_json or {}
        parsed_sheets = self._parse_file(file_content, filename)
        if not parsed_sheets:
            raise ValueError("ESB文件解析失败或为空")

        imported = 0
        skipped = 0
        errors: List[str] = []
        entries: List[Dict[str, Any]] = []
        system_summary: List[Dict[str, Any]] = []

        for sheet_name, rows in parsed_sheets.items():
            if not rows:
                continue
            header_map = self._build_header_map(list(rows[0].keys()))
            detail_mapping = self._resolve_mapping(header_map, mapping_json, self.FIELD_ALIASES)
            summary_mapping = self._resolve_mapping(header_map, mapping_json, self.SUMMARY_ALIASES)

            is_detail = all(field in detail_mapping for field in self.REQUIRED_FIELDS)
            is_summary = ("system_id" in summary_mapping and "system_name" in summary_mapping and not is_detail)

            if not is_detail and not is_summary:
                errors.append(f"Sheet {sheet_name}: 缺少必填列，已跳过")
                continue

            if is_summary:
                for idx, row in enumerate(rows, start=2):
                    item = self._extract_summary_row(row, summary_mapping)
                    if not item.get("system_id") or not item.get("system_name"):
                        skipped += 1
                        continue
                    item["source_file"] = filename
                    item["sheet"] = sheet_name
                    item["row_no"] = idx
                    system_summary.append(item)
                continue

            for idx, row in enumerate(rows, start=2):
                entry, reason = self._extract_detail_row(row, detail_mapping)
                if not entry:
                    skipped += 1
                    if reason:
                        errors.append(f"Sheet {sheet_name} row {idx}: {reason}")
                    continue
                entry.update(
                    {
                        "source_file": filename,
                        "sheet": sheet_name,
                        "row_no": idx,
                        "imported_at": datetime.now().isoformat(),
                    }
                )
                entries.append(entry)

        if entries:
            try:
                embedding_service = self._ensure_embedding_service()
                texts = [self._build_entry_text(e) for e in entries]
                embeddings = embedding_service.batch_generate_embeddings(texts)
                for entry, emb in zip(entries, embeddings):
                    entry["embedding"] = emb
            except Exception as exc:
                logger.warning(f"ESB embedding生成失败，降级为无embedding: {exc}")
                for entry in entries:
                    entry["embedding"] = None

        imported = len(entries)

        with self._store_context() as store:
            store["entries"] = entries
            if system_summary:
                store["system_summary"] = system_summary
            store["meta"]["updated_at"] = datetime.now().isoformat()

        return {
            "total": imported + skipped,
            "imported": imported,
            "skipped": skipped,
            "errors": errors[:50],
        }

    def _extract_detail_row(self, row: Dict[str, Any], mapping: Dict[str, str]) -> Tuple[Optional[Dict[str, Any]], str]:
        data: Dict[str, Any] = {}
        for field, col_name in mapping.items():
            value = row.get(col_name)
            data[field] = str(value).strip() if value is not None else ""
        for field in self.REQUIRED_FIELDS:
            if not data.get(field):
                return None, f"缺少字段 {field}"
        return data, ""

    def _extract_summary_row(self, row: Dict[str, Any], mapping: Dict[str, str]) -> Dict[str, Any]:
        data: Dict[str, Any] = {}
        for field, col_name in mapping.items():
            value = row.get(col_name)
            data[field] = str(value).strip() if value is not None else ""
        return data

    def search_esb(
        self,
        query: str,
        system_id: Optional[str] = None,
        system_name: Optional[str] = None,
        scope: Optional[str] = None,
        include_deprecated: bool = False,
        top_k: int = 8,
        similarity_threshold: float = 0.55,
    ) -> List[Dict[str, Any]]:
        query = str(query or "").strip()
        if not query:
            return []

        with self._lock():
            store = self._load_unlocked()
        entries = store.get("entries") or []
        meta = store.get("meta") or {}
        valid_statuses = meta.get("valid_statuses") or self.DEFAULT_VALID_STATUSES
        default_scope = meta.get("default_scope") or self.DEFAULT_SCOPE
        scope = (scope or default_scope or "both").lower()

        sid = str(system_id or "").strip()
        sname = str(system_name or "").strip()

        filtered: List[Dict[str, Any]] = []
        for entry in entries:
            status = str(entry.get("status") or "").strip()
            is_active = status in valid_statuses
            if not include_deprecated and not is_active:
                continue

            if sid or sname:
                if scope == "provider":
                    if not self._match_system(entry.get("provider_system_id"), entry.get("provider_system_name"), sid, sname):
                        continue
                elif scope == "consumer":
                    if not self._match_system(entry.get("consumer_system_id"), entry.get("consumer_system_name"), sid, sname):
                        continue
                else:
                    if not (
                        self._match_system(entry.get("provider_system_id"), entry.get("provider_system_name"), sid, sname)
                        or self._match_system(entry.get("consumer_system_id"), entry.get("consumer_system_name"), sid, sname)
                    ):
                        continue

            filtered.append(entry)

        scored: List[Tuple[float, Dict[str, Any]]] = []
        query_embedding = None
        if filtered:
            try:
                embedding_service = self._ensure_embedding_service()
                query_embedding = embedding_service.generate_embedding(query)
            except Exception as exc:
                logger.warning(f"ESB查询embedding生成失败，降级关键词匹配: {exc}")

        for entry in filtered:
            score = 0.0
            if query_embedding and entry.get("embedding"):
                score = self._cosine_similarity(query_embedding, entry["embedding"])
            else:
                score = self._keyword_score(query, entry)
            if score < similarity_threshold:
                continue
            scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        results: List[Dict[str, Any]] = []
        for score, entry in scored[: max(int(top_k or 0), 0)]:
            results.append(
                {
                    "provider_system_id": entry.get("provider_system_id"),
                    "provider_system_name": entry.get("provider_system_name"),
                    "consumer_system_id": entry.get("consumer_system_id"),
                    "consumer_system_name": entry.get("consumer_system_name"),
                    "service_code": entry.get("service_code"),
                    "scenario_code": entry.get("scenario_code"),
                    "service_name": entry.get("service_name"),
                    "status": entry.get("status"),
                    "similarity": round(float(score), 4),
                }
            )
        return results

    def get_stats(self, system_id: Optional[str] = None, system_name: Optional[str] = None) -> Dict[str, Any]:
        with self._lock():
            store = self._load_unlocked()
        entries = store.get("entries") or []
        meta = store.get("meta") or {}
        valid_statuses = meta.get("valid_statuses") or self.DEFAULT_VALID_STATUSES

        sid = str(system_id or "").strip()
        sname = str(system_name or "").strip()

        def matches(entry: Dict[str, Any]) -> bool:
            if not sid and not sname:
                return True
            return self._match_system(entry.get("provider_system_id"), entry.get("provider_system_name"), sid, sname) or \
                self._match_system(entry.get("consumer_system_id"), entry.get("consumer_system_name"), sid, sname)

        active = 0
        deprecated = 0
        services = set()
        for entry in entries:
            if not matches(entry):
                continue
            status = str(entry.get("status") or "").strip()
            if status in valid_statuses:
                active += 1
                if entry.get("service_name"):
                    services.add(entry.get("service_name"))
            else:
                deprecated += 1

        summary = store.get("system_summary") or []
        if sid or sname:
            summary = [item for item in summary if self._match_system(item.get("system_id"), item.get("system_name"), sid, sname)]

        return {
            "active_entry_count": active,
            "deprecated_entry_count": deprecated,
            "active_unique_service_count": len(services),
            "system_summary": summary,
        }

    def _match_system(self, system_id: Any, system_name: Any, sid: str, sname: str) -> bool:
        if sid and str(system_id or "").strip() == sid:
            return True
        if sname and str(system_name or "").strip() == sname:
            return True
        return False

    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        try:
            if not v1 or not v2:
                return 0.0
            dot = 0.0
            norm1 = 0.0
            norm2 = 0.0
            for a, b in zip(v1, v2):
                a = float(a)
                b = float(b)
                dot += a * b
                norm1 += a * a
                norm2 += b * b
            if norm1 <= 0 or norm2 <= 0:
                return 0.0
            return dot / (math.sqrt(norm1) * math.sqrt(norm2))
        except Exception:
            return 0.0

    def _keyword_score(self, query: str, entry: Dict[str, Any]) -> float:
        if not query:
            return 0.0
        query = query.strip()
        haystack = " ".join(
            [
                str(entry.get("service_name") or ""),
                str(entry.get("service_code") or ""),
                str(entry.get("scenario_code") or ""),
                str(entry.get("provider_system_name") or ""),
                str(entry.get("consumer_system_name") or ""),
            ]
        )
        return 1.0 if query and query in haystack else 0.0


_esb_service = None


def get_esb_service() -> EsbService:
    global _esb_service
    if _esb_service is None:
        _esb_service = EsbService()
    return _esb_service
