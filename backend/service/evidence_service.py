"""
证据库服务（A层）
负责证据材料导入、切块入库、检索、统计与预览权限控制。
"""
from __future__ import annotations

import json
import logging
import os
import re
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

try:
    import fcntl
    FCNTL_AVAILABLE = True
except ImportError:
    FCNTL_AVAILABLE = False

from backend.config.config import settings
from backend.service.embedding_service import get_embedding_service
from backend.service.document_parser import get_document_parser
from backend.service.local_vector_store import LocalVectorStore

logger = logging.getLogger(__name__)


class EvidenceService:
    """证据库服务（A层）"""

    CHUNK_SIZE = 800
    CHUNK_OVERLAP = 120
    MAX_CHUNKS = 200

    def __init__(
        self,
        store_path: Optional[str] = None,
        docs_path: Optional[str] = None,
        upload_dir: Optional[str] = None,
        embedding_service=None,
        document_parser=None,
        vector_store=None,
    ) -> None:
        self.store_path = store_path or os.path.join(settings.REPORT_DIR, "knowledge_store.json")
        self.docs_path = docs_path or os.path.join(settings.REPORT_DIR, "evidence_docs.json")
        self.upload_dir = upload_dir or os.path.join(settings.UPLOAD_DIR, "evidence")

        self.docs_lock_path = f"{self.docs_path}.lock"
        self._mutex = threading.RLock()

        self.embedding_service = embedding_service or get_embedding_service()
        self.document_parser = document_parser or get_document_parser()
        self.vector_store = vector_store or LocalVectorStore(self.store_path)

        self.task_store_path = os.path.join(settings.REPORT_DIR, "task_storage.json")
        self.task_lock_path = f"{self.task_store_path}.lock"

    @contextmanager
    def _lock(self):
        if FCNTL_AVAILABLE:
            os.makedirs(os.path.dirname(self.docs_lock_path) or ".", exist_ok=True)
            with open(self.docs_lock_path, "a") as lock_file:
                fcntl.flock(lock_file, fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(lock_file, fcntl.LOCK_UN)
        else:
            with self._mutex:
                yield

    def _load_docs_unlocked(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.docs_path):
            return []
        try:
            with open(self.docs_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception as exc:
            logger.warning(f"读取证据库元数据失败: {exc}")
            return []

    def _save_docs_unlocked(self, docs: List[Dict[str, Any]]) -> None:
        os.makedirs(os.path.dirname(self.docs_path) or ".", exist_ok=True)
        tmp_path = f"{self.docs_path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(docs, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self.docs_path)

    @contextmanager
    def _docs_context(self):
        with self._lock():
            docs = self._load_docs_unlocked()
            yield docs
            self._save_docs_unlocked(docs)

    @contextmanager
    def _task_lock(self):
        if FCNTL_AVAILABLE:
            os.makedirs(os.path.dirname(self.task_lock_path) or ".", exist_ok=True)
            with open(self.task_lock_path, "a") as lock_file:
                fcntl.flock(lock_file, fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(lock_file, fcntl.LOCK_UN)
        else:
            with self._mutex:
                yield

    def _load_tasks_unlocked(self) -> Dict[str, Any]:
        if not os.path.exists(self.task_store_path):
            return {}
        try:
            with open(self.task_store_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception as exc:
            logger.warning(f"读取任务存储失败: {exc}")
            return {}

    def _save_tasks_unlocked(self, tasks: Dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(self.task_store_path) or ".", exist_ok=True)
        tmp_path = f"{self.task_store_path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(tasks, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self.task_store_path)

    def _sanitize_name(self, value: str) -> str:
        text = str(value or "").strip()
        if not text:
            return "unknown"
        text = text.replace("/", "_").replace("\\", "_")
        text = re.sub(r"[^0-9a-zA-Z_\-\u4e00-\u9fa5]+", "_", text)
        return text[:60] or "unknown"

    def _parse_date(self, value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value).strip())
        except Exception:
            return None

    def _build_segments(self, parsed: Dict[str, Any], doc_type: str) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
        segments: List[Dict[str, str]] = []
        meta: Dict[str, Any] = {}

        if doc_type == "pdf":
            pages = parsed.get("pages") or []
            meta = parsed.get("metadata") or {}
            for page in pages:
                if not isinstance(page, dict):
                    continue
                text = str(page.get("text") or "").strip()
                if not text:
                    continue
                page_no = page.get("page") or (len(segments) + 1)
                segments.append({"loc": f"p{page_no}", "text": text})
            return segments, meta

        if doc_type == "docx":
            meta = parsed.get("metadata") or {}
            for idx, para in enumerate(parsed.get("paragraphs") or [], start=1):
                if not isinstance(para, dict):
                    continue
                text = str(para.get("text") or "").strip()
                if not text:
                    continue
                segments.append({"loc": f"para{idx}", "text": text})
            for t_idx, table in enumerate(parsed.get("tables") or [], start=1):
                if not isinstance(table, dict):
                    continue
                rows = table.get("data") or []
                for r_idx, row in enumerate(rows, start=1):
                    if not isinstance(row, list):
                        continue
                    line = " | ".join(str(cell).strip() for cell in row if str(cell).strip())
                    if not line:
                        continue
                    segments.append({"loc": f"table{t_idx}#row{r_idx}", "text": line})
            return segments, meta

        if doc_type == "pptx":
            meta = parsed.get("metadata") or {}
            for slide in parsed.get("slides") or []:
                if not isinstance(slide, dict):
                    continue
                text = str(slide.get("text") or "").strip()
                if not text:
                    continue
                slide_no = slide.get("slide") or (len(segments) + 1)
                segments.append({"loc": f"slide{slide_no}", "text": text})
            return segments, meta

        return segments, meta

    def _split_text(self, text: str, size: int, overlap: int) -> List[str]:
        cleaned = (text or "").strip()
        if not cleaned:
            return []
        if size <= 0:
            return [cleaned]
        if overlap < 0 or overlap >= size:
            overlap = max(min(120, size // 5), 0)
        step = max(size - overlap, 1)
        chunks: List[str] = []
        for start in range(0, len(cleaned), step):
            chunk = cleaned[start : start + size].strip()
            if chunk:
                chunks.append(chunk)
            if len(chunks) >= int(self.MAX_CHUNKS):
                break
        return chunks

    def _build_chunks(self, segments: List[Dict[str, str]]) -> List[Dict[str, str]]:
        chunks: List[Dict[str, str]] = []
        current_text = ""
        current_start = ""
        current_end = ""

        for seg in segments:
            text = str(seg.get("text") or "").strip()
            loc = str(seg.get("loc") or "").strip()
            if not text:
                continue

            # 超长片段直接切分
            if len(text) >= self.CHUNK_SIZE:
                if current_text:
                    chunks.append({"text": current_text, "loc": self._loc_range(current_start, current_end)})
                    current_text = ""
                    current_start = ""
                    current_end = ""
                sub_chunks = self._split_text(text, self.CHUNK_SIZE, self.CHUNK_OVERLAP)
                for idx, sub in enumerate(sub_chunks, start=1):
                    sub_loc = f"{loc}#{idx}" if len(sub_chunks) > 1 else loc
                    chunks.append({"text": sub, "loc": sub_loc})
                continue

            candidate_len = len(current_text) + (1 if current_text else 0) + len(text)
            if current_text and candidate_len > self.CHUNK_SIZE:
                chunks.append({"text": current_text, "loc": self._loc_range(current_start, current_end)})
                current_text = text
                current_start = loc
                current_end = loc
            else:
                if current_text:
                    current_text += "\n" + text
                else:
                    current_text = text
                    current_start = loc
                current_end = loc

            if len(chunks) >= self.MAX_CHUNKS:
                break

        if current_text and len(chunks) < self.MAX_CHUNKS:
            chunks.append({"text": current_text, "loc": self._loc_range(current_start, current_end)})
        return chunks

    def _loc_range(self, start: str, end: str) -> str:
        if not start:
            return end
        if not end or start == end:
            return start
        return f"{start}~{end}"

    def import_evidence(
        self,
        file_content: bytes,
        filename: str,
        system_name: str,
        system_id: Optional[str] = None,
        trust_level: str = "中",
        doc_date: Optional[str] = None,
        source_org: Optional[str] = None,
        version_hint: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not filename:
            raise ValueError("文件名不能为空")

        normalized_system = str(system_name or "").strip()
        if not normalized_system:
            raise ValueError("system_name不能为空")

        ext = os.path.splitext(filename.lower())[1]
        if ext not in (".pdf", ".docx", ".pptx"):
            raise ValueError("仅支持 PDF/DOCX/PPTX 作为证据材料")

        doc_type = ext.lstrip(".")
        doc_id = f"evd_{uuid.uuid4().hex}"

        safe_system = self._sanitize_name(normalized_system)
        doc_dir = os.path.join(self.upload_dir, safe_system, doc_id)
        os.makedirs(doc_dir, exist_ok=True)
        stored_path = os.path.join(doc_dir, filename)
        with open(stored_path, "wb") as f:
            f.write(file_content)

        parsed = self.document_parser.parse(file_content=file_content, filename=filename, file_type=doc_type)
        if isinstance(parsed, dict) and parsed.get("error"):
            raise ValueError(parsed.get("error") or "解析失败")

        segments, parse_meta = self._build_segments(parsed if isinstance(parsed, dict) else {}, doc_type)

        created_at = datetime.now().isoformat()
        chunk_count = 0
        skipped_reason = None

        if not segments:
            skipped_reason = "未提取到可用文本（可能是扫描件或图片）"
        else:
            chunks = self._build_chunks(segments)
            chunk_count = len(chunks)
            if not chunks:
                skipped_reason = "未生成可用证据块"
            else:
                texts = [item["text"] for item in chunks]
                embeddings = self.embedding_service.batch_generate_embeddings(texts)

                knowledge_items = []
                for idx, chunk in enumerate(chunks):
                    meta = {
                        "doc_id": doc_id,
                        "chunk_id": f"chk_{idx + 1}",
                        "loc": chunk.get("loc") or "",
                        "system_id": system_id or "",
                        "doc_type": doc_type,
                        "trust_level": trust_level,
                        "doc_date": doc_date or "",
                    }
                    knowledge_items.append(
                        {
                            "system_name": normalized_system,
                            "knowledge_type": "evidence_chunk",
                            "content": chunk.get("text") or "",
                            "embedding": embeddings[idx] if idx < len(embeddings) else [],
                            "metadata": meta,
                            "source_file": filename,
                            "created_at": created_at,
                        }
                    )

                result = self.vector_store.batch_insert_knowledge(knowledge_items)
                if result.get("success", 0) == 0:
                    skipped_reason = "证据块入库失败"

        doc_meta = {
            "doc_id": doc_id,
            "system_id": system_id or "",
            "system_name": normalized_system,
            "filename": filename,
            "stored_path": stored_path,
            "doc_type": doc_type,
            "trust_level": trust_level,
            "doc_date": doc_date or "",
            "source_org": source_org or "",
            "version_hint": version_hint or "",
            "parse_meta": parse_meta,
            "chunk_count": chunk_count,
            "created_by": created_by or "",
            "created_at": created_at,
        }

        with self._docs_context() as docs:
            docs.append(doc_meta)

        return {
            "doc_id": doc_id,
            "chunk_count": chunk_count,
            "skipped_reason": skipped_reason,
        }

    def list_docs(
        self,
        system_name: Optional[str] = None,
        system_id: Optional[str] = None,
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        normalized_system = str(system_name or "").strip()
        normalized_id = str(system_id or "").strip()

        with self._lock():
            docs = self._load_docs_unlocked()

        filtered = []
        for doc in docs:
            if not isinstance(doc, dict):
                continue
            if normalized_system and doc.get("system_name") != normalized_system:
                continue
            if normalized_id and doc.get("system_id") != normalized_id:
                continue
            filtered.append(doc)

        filtered.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return filtered[: max(int(limit or 0), 0)] if limit else filtered

    def get_stats(self, system_name: Optional[str] = None, system_id: Optional[str] = None) -> Dict[str, Any]:
        docs = self.list_docs(system_name=system_name, system_id=system_id, limit=0)
        trust_dist: Dict[str, int] = {"高": 0, "中": 0, "低": 0}
        doc_type_dist: Dict[str, int] = {}
        latest = None
        chunk_count = 0
        for doc in docs:
            level = str(doc.get("trust_level") or "")
            if level in trust_dist:
                trust_dist[level] += 1
            doc_type = str(doc.get("doc_type") or "")
            if doc_type:
                doc_type_dist[doc_type] = doc_type_dist.get(doc_type, 0) + 1
            created_at = doc.get("created_at")
            if created_at and (latest is None or created_at > latest):
                latest = created_at
            try:
                chunk_count += int(doc.get("chunk_count") or 0)
            except Exception:
                continue

        return {
            "doc_count": len(docs),
            "chunk_count": chunk_count,
            "trust_distribution": trust_dist,
            "doc_type_distribution": doc_type_dist,
            "latest_import_time": latest,
        }

    def _score_result(self, similarity: float, trust_level: str, doc_date: str, created_at: str) -> float:
        base = float(similarity or 0.0)
        trust_bonus = {"高": 0.08, "中": 0.04, "低": 0.0}.get(trust_level, 0.0)
        recency_bonus = 0.0
        date_value = self._parse_date(doc_date) or self._parse_date(created_at)
        if date_value:
            days = (datetime.now() - date_value).days
            if days <= 30:
                recency_bonus = 0.05
            elif days <= 180:
                recency_bonus = 0.03
            elif days <= 365:
                recency_bonus = 0.01
        return base + trust_bonus + recency_bonus

    def search_evidence(
        self,
        query: str,
        system_name: Optional[str] = None,
        system_id: Optional[str] = None,
        top_k: int = 5,
        similarity_threshold: float = 0.6,
        task_id: Optional[str] = None,
        actor: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        if not str(query or "").strip():
            return []

        query_embedding = self.embedding_service.generate_embedding(query)

        results = self.vector_store.search_knowledge(
            query_embedding=query_embedding,
            system_name=str(system_name).strip() if system_name else None,
            knowledge_type="evidence_chunk",
            top_k=max(int(top_k or 0), 1),
            similarity_threshold=float(similarity_threshold or 0.0),
        )

        filtered: List[Dict[str, Any]] = []
        normalized_id = str(system_id or "").strip()
        for item in results:
            meta = item.get("metadata") or {}
            if normalized_id and str(meta.get("system_id") or "") != normalized_id:
                continue
            filtered.append(item)

        # 计算排序权重（相似度 + trust/recency 加权）
        scored = []
        for item in filtered:
            meta = item.get("metadata") or {}
            trust_level = str(meta.get("trust_level") or "")
            doc_date = str(meta.get("doc_date") or "")
            doc_id = str(meta.get("doc_id") or "")
            created_at = self._doc_created_at(doc_id)
            score = self._score_result(float(item.get("similarity") or 0.0), trust_level, doc_date, created_at)
            scored.append((score, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        ordered = [item for _, item in scored]

        evidence_refs: List[Dict[str, Any]] = []
        doc_ids: List[str] = []
        for item in ordered[: max(int(top_k or 0), 0)]:
            meta = item.get("metadata") or {}
            doc_id = str(meta.get("doc_id") or "")
            if doc_id:
                doc_ids.append(doc_id)
            evidence_refs.append(
                {
                    "doc_id": doc_id,
                    "chunk_id": str(meta.get("chunk_id") or ""),
                    "loc": str(meta.get("loc") or ""),
                    "snippet": (str(item.get("content") or "")[:200]).strip(),
                    "similarity": round(float(item.get("similarity") or 0.0), 4),
                    "trust_level": str(meta.get("trust_level") or ""),
                    "doc_date": str(meta.get("doc_date") or ""),
                    "source_file": str(item.get("source_file") or ""),
                    "system_name": str(item.get("system_name") or ""),
                    "system_id": str(meta.get("system_id") or ""),
                    "doc_type": str(meta.get("doc_type") or ""),
                }
            )

        if task_id and doc_ids:
            try:
                self.link_doc_to_task(task_id, doc_ids)
            except Exception as exc:
                logger.warning(f"关联证据到任务失败: {exc}")

        return evidence_refs

    def _doc_created_at(self, doc_id: str) -> str:
        if not doc_id:
            return ""
        with self._lock():
            docs = self._load_docs_unlocked()
        for doc in docs:
            if isinstance(doc, dict) and doc.get("doc_id") == doc_id:
                return str(doc.get("created_at") or "")
        return ""

    def get_doc(self, doc_id: str) -> Optional[Dict[str, Any]]:
        if not doc_id:
            return None
        with self._lock():
            docs = self._load_docs_unlocked()
        for doc in docs:
            if isinstance(doc, dict) and doc.get("doc_id") == doc_id:
                return doc
        return None

    def link_doc_to_task(self, task_id: str, doc_ids: List[str]) -> None:
        if not task_id or not doc_ids:
            return
        unique_ids = {str(item) for item in doc_ids if str(item).strip()}
        if not unique_ids:
            return

        with self._task_lock():
            tasks = self._load_tasks_unlocked()
            task = tasks.get(task_id)
            if not isinstance(task, dict):
                return
            existing = set(task.get("evidence_doc_ids") or [])
            updated = list(existing | unique_ids)
            task["evidence_doc_ids"] = updated
            tasks[task_id] = task
            self._save_tasks_unlocked(tasks)

    def _assignment_matches_user(self, assignment: Dict[str, Any], user: Dict[str, Any]) -> bool:
        if not assignment or not user:
            return False
        expert_id = assignment.get("expert_id")
        if not expert_id:
            return False
        candidates = {user.get("id"), user.get("username"), user.get("display_name")}
        return expert_id in candidates

    def can_preview_doc(self, user: Dict[str, Any], doc_id: str, task_id: Optional[str] = None) -> bool:
        if not user or not doc_id:
            return False
        roles = user.get("roles", [])
        if "admin" in roles or "manager" in roles:
            return True
        if "expert" not in roles:
            return False

        with self._task_lock():
            tasks = self._load_tasks_unlocked()

        if task_id:
            task = tasks.get(task_id)
            if not isinstance(task, dict):
                return False
            if doc_id not in (task.get("evidence_doc_ids") or []):
                return False
            for assignment in task.get("expert_assignments", []):
                if self._assignment_matches_user(assignment, user):
                    return True
            return False

        # 无 task_id 时，遍历全部任务
        for task in tasks.values():
            if not isinstance(task, dict):
                continue
            if doc_id not in (task.get("evidence_doc_ids") or []):
                continue
            for assignment in task.get("expert_assignments", []):
                if self._assignment_matches_user(assignment, user):
                    return True
        return False

    def get_preview_text(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        stored_path = doc.get("stored_path")
        doc_type = doc.get("doc_type")
        if not stored_path or not os.path.exists(stored_path):
            return {"preview_type": "error", "message": "证据文件不存在"}

        if doc_type == "pdf":
            return {"preview_type": "pdf"}

        try:
            with open(stored_path, "rb") as f:
                content = f.read()
            parsed = self.document_parser.parse(file_content=content, filename=doc.get("filename"), file_type=doc_type)
            text = self._parsed_to_text(parsed)
            if not text.strip():
                return {"preview_type": "text", "content": "", "message": "未提取到可用文本"}
            # 控制预览长度
            preview = text.strip()
            if len(preview) > 20000:
                preview = preview[:20000] + "\n...（已截断）"
            return {"preview_type": "text", "content": preview}
        except Exception as exc:
            logger.warning(f"证据预览失败: {exc}")
            return {"preview_type": "error", "message": "预览解析失败"}

    def _parsed_to_text(self, parsed: Any) -> str:
        if parsed is None:
            return ""
        if isinstance(parsed, str):
            return parsed
        if isinstance(parsed, bytes):
            for encoding in ("utf-8", "utf-8-sig", "gbk"):
                try:
                    return parsed.decode(encoding)
                except Exception:
                    continue
            return ""
        if isinstance(parsed, dict):
            if "paragraphs" in parsed:
                parts = [str(p.get("text") or "").strip() for p in parsed.get("paragraphs") or []]
                parts += [" | ".join(str(c).strip() for c in row if str(c).strip())
                          for table in parsed.get("tables") or []
                          if isinstance(table, dict)
                          for row in table.get("data") or [] if isinstance(row, list)]
                return "\n".join([p for p in parts if p])
            if "pages" in parsed:
                return "\n".join(
                    str(p.get("text") or "").strip()
                    for p in parsed.get("pages") or []
                    if isinstance(p, dict) and str(p.get("text") or "").strip()
                )
            if "slides" in parsed:
                return "\n".join(
                    str(s.get("text") or "").strip()
                    for s in parsed.get("slides") or []
                    if isinstance(s, dict) and str(s.get("text") or "").strip()
                )
        if isinstance(parsed, list):
            return "\n".join(str(item).strip() for item in parsed if str(item).strip())
        return str(parsed)


_evidence_service = None


def get_evidence_service() -> EvidenceService:
    global _evidence_service
    if _evidence_service is None:
        _evidence_service = EvidenceService()
    return _evidence_service

