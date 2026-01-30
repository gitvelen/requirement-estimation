"""
本地向量存储（无 Milvus / 无 MinIO 依赖）

用于在本期不启用 Milvus/MinIO 的情况下，提供知识库的导入与检索能力：
- 数据落盘到 JSON 文件（默认 data/knowledge_store.json）
- 检索采用简单的余弦相似度 + 全量扫描（适合小规模数据）
"""

from __future__ import annotations

import json
import logging
import math
import os
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    import fcntl

    FCNTL_AVAILABLE = True
except ImportError:
    FCNTL_AVAILABLE = False


class LocalVectorStore:
    """
    本地文件向量库

    存储格式：list[dict]
    每条记录字段：
      - id: str
      - system_name: str
      - knowledge_type: str
      - content: str
      - embedding: list[float]
      - embedding_norm: float
      - metadata: dict
      - source_file: str
      - created_at: ISO时间
    """

    def __init__(self, store_path: str):
        self.store_path = store_path
        self.lock_path = f"{store_path}.lock"
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

    def _load_unlocked(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.store_path):
            return []
        try:
            with open(self.store_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception as exc:
            logger.warning(f"读取本地知识库失败: {exc}")
            return []

    def _save_unlocked(self, items: List[Dict[str, Any]]) -> None:
        os.makedirs(os.path.dirname(self.store_path) or ".", exist_ok=True)
        tmp_path = f"{self.store_path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self.store_path)

    @contextmanager
    def _store_context(self):
        with self._lock():
            items = self._load_unlocked()
            yield items
            self._save_unlocked(items)

    def _calc_norm(self, embedding: List[float]) -> float:
        try:
            return math.sqrt(math.fsum((float(v) * float(v) for v in embedding)))
        except Exception:
            return 0.0

    def _normalize_entry(self, entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not isinstance(entry, dict):
            return None

        system_name = str(entry.get("system_name") or "").strip()
        knowledge_type = str(entry.get("knowledge_type") or "").strip()
        content = str(entry.get("content") or "").strip()
        embedding = entry.get("embedding")
        metadata = entry.get("metadata") or {}
        source_file = str(entry.get("source_file") or "")

        if not system_name or not knowledge_type or not content:
            return None
        if not isinstance(embedding, list) or not embedding:
            return None

        norm = float(entry.get("embedding_norm") or 0.0)
        if norm <= 0:
            norm = self._calc_norm(embedding)

        return {
            "id": str(entry.get("id") or f"kb_{uuid.uuid4().hex}"),
            "system_name": system_name,
            "knowledge_type": knowledge_type,
            "content": content,
            "embedding": embedding,
            "embedding_norm": norm,
            "metadata": metadata if isinstance(metadata, dict) else {"raw": metadata},
            "source_file": source_file,
            "created_at": str(entry.get("created_at") or datetime.now().isoformat()),
        }

    def insert_knowledge(
        self,
        system_name: str,
        knowledge_type: str,
        content: str,
        embedding: List[float],
        metadata: Dict[str, Any],
        source_file: str = None,
    ) -> str:
        entry = self._normalize_entry(
            {
                "system_name": system_name,
                "knowledge_type": knowledge_type,
                "content": content,
                "embedding": embedding,
                "metadata": metadata,
                "source_file": source_file or "",
            }
        )
        if not entry:
            raise ValueError("无效的知识条目，无法写入本地知识库")

        with self._store_context() as items:
            items.append(entry)
        return entry["id"]

    def batch_insert_knowledge(self, knowledge_list: List[Dict[str, Any]]) -> Dict[str, int]:
        success = 0
        failed = 0
        normalized_items: List[Dict[str, Any]] = []
        for item in knowledge_list or []:
            entry = self._normalize_entry(item)
            if not entry:
                failed += 1
                continue
            normalized_items.append(entry)
            success += 1

        if normalized_items:
            with self._store_context() as items:
                items.extend(normalized_items)

        return {"success": success, "failed": failed}

    def search_knowledge(
        self,
        query_embedding: List[float],
        system_name: str = None,
        knowledge_type: str = None,
        top_k: int = 10,
        similarity_threshold: float = 0.6,
    ) -> List[Dict[str, Any]]:
        if not isinstance(query_embedding, list) or not query_embedding:
            return []

        q_norm = self._calc_norm(query_embedding)
        if q_norm <= 0:
            return []

        system_filter = str(system_name).strip() if system_name else None
        type_filter = str(knowledge_type).strip() if knowledge_type else None

        with self._lock():
            items = self._load_unlocked()

        scored: List[Dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            if system_filter and item.get("system_name") != system_filter:
                continue
            if type_filter and item.get("knowledge_type") != type_filter:
                continue

            emb = item.get("embedding")
            if not isinstance(emb, list) or not emb:
                continue
            norm = float(item.get("embedding_norm") or 0.0)
            if norm <= 0:
                norm = self._calc_norm(emb)
                if norm <= 0:
                    continue

            # 余弦相似度
            try:
                dot = math.fsum((float(a) * float(b) for a, b in zip(query_embedding, emb)))
                similarity = dot / (q_norm * norm)
            except Exception:
                continue

            if similarity < similarity_threshold:
                continue

            scored.append(
                {
                    "system_name": item.get("system_name", ""),
                    "knowledge_type": item.get("knowledge_type", ""),
                    "content": item.get("content", ""),
                    "metadata": item.get("metadata") if isinstance(item.get("metadata"), dict) else {},
                    "source_file": item.get("source_file", ""),
                    "similarity": float(similarity),
                }
            )

        scored.sort(key=lambda x: x.get("similarity", 0.0), reverse=True)
        return scored[: max(int(top_k or 0), 0)] if top_k else scored

    def get_collection_stats(self, system_name: str = None) -> Dict[str, Any]:
        system_filter = str(system_name).strip() if system_name else None
        with self._lock():
            items = self._load_unlocked()
        if system_filter:
            items = [item for item in items if isinstance(item, dict) and item.get("system_name") == system_filter]
        return {
            "name": "local_knowledge_store",
            "count": len(items),
            "index": "LOCAL_SCAN",
            "metric_type": "COSINE",
        }

    def get_type_counts(self, system_name: str = None) -> Dict[str, int]:
        """统计各 knowledge_type 的数量（用于前端展示）。"""
        system_filter = str(system_name).strip() if system_name else None
        with self._lock():
            items = self._load_unlocked()
        counts: Dict[str, int] = {}
        for item in items:
            if not isinstance(item, dict):
                continue
            if system_filter and item.get("system_name") != system_filter:
                continue
            ktype = str(item.get("knowledge_type") or "").strip()
            if not ktype:
                continue
            counts[ktype] = counts.get(ktype, 0) + 1
        return counts

    def rebuild_index(self) -> Dict[str, Any]:
        """本地模式下用于修复/补齐 embedding_norm 等派生字段。"""
        fixed = 0
        total = 0
        with self._store_context() as items:
            total = len(items)
            for idx, item in enumerate(list(items)):
                if not isinstance(item, dict):
                    continue
                emb = item.get("embedding")
                if not isinstance(emb, list) or not emb:
                    continue
                norm = float(item.get("embedding_norm") or 0.0)
                if norm <= 0:
                    items[idx]["embedding_norm"] = self._calc_norm(emb)
                    fixed += 1
        return {
            "status": "success",
            "message": "本地索引重建完成",
            "total": total,
            "fixed": fixed,
        }
