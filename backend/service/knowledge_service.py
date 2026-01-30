"""
知识库服务
提供知识的导入、检索、管理等核心功能
"""
import logging
import os
import json
import uuid
import re
import csv
from typing import List, Dict, Any, Optional
from datetime import datetime
from contextlib import contextmanager
try:
    import fcntl
    METRICS_LOCK_AVAILABLE = True
except ImportError:
    METRICS_LOCK_AVAILABLE = False

from backend.service.milvus_client import get_milvus_client
from backend.service.local_vector_store import LocalVectorStore
from backend.service.embedding_service import get_embedding_service
from backend.service.document_parser import get_document_parser
from backend.config.config import settings

logger = logging.getLogger(__name__)


class KnowledgeService:
    """知识库服务"""

    # 知识类型
    TYPE_SYSTEM_PROFILE = "system_profile"  # 系统知识

    # 非结构化导入切分策略（本期：本地向量库）
    UNSTRUCTURED_CHUNK_SIZE = 800
    UNSTRUCTURED_CHUNK_OVERLAP = 120
    MAX_UNSTRUCTURED_CHUNKS = 200

    def __init__(self):
        """初始化服务"""
        self.metrics_file = os.path.join(settings.REPORT_DIR, "knowledge_metrics.json")
        self.metrics_lock_file = f"{self.metrics_file}.lock"
        self.retrieval_log_file = os.path.join(settings.REPORT_DIR, "knowledge_retrieval_logs.json")
        self.retrieval_log_lock_file = f"{self.retrieval_log_file}.lock"

        self.vector_store_backend = settings.KNOWLEDGE_VECTOR_STORE or "local"
        self.local_store_path = os.path.join(settings.REPORT_DIR, "knowledge_store.json")

        if self.vector_store_backend == "milvus":
            try:
                self.vector_store = get_milvus_client()
                logger.info("知识库向量存储后端: milvus")
            except Exception as e:
                logger.warning(f"Milvus不可用，回退到本地向量库: {e}")
                self.vector_store_backend = "local"
                self.vector_store = LocalVectorStore(self.local_store_path)
        else:
            self.vector_store_backend = "local"
            self.vector_store = LocalVectorStore(self.local_store_path)
            logger.info("知识库向量存储后端: local")

        self.embedding_service = get_embedding_service()
        self.document_parser = get_document_parser()
        self._system_list: Optional[List[str]] = None
        logger.info("知识库服务初始化完成")

    def _load_system_list(self) -> List[str]:
        """加载标准系统列表（用于从文本/文件名粗略推断 system_name）。"""
        if self._system_list is not None:
            return self._system_list

        system_list: List[str] = []
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        md_path = os.path.join(base_dir, "system_list.md")
        if os.path.exists(md_path):
            try:
                with open(md_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or line.startswith(">"):
                            continue
                        if "系统名称" in line and "英文简称" in line:
                            continue
                        if "|" in line:
                            parts = [p.strip() for p in line.split("|")]
                            if parts and parts[0]:
                                system_list.append(parts[0])
                self._system_list = system_list
                return system_list
            except Exception as e:
                logger.warning(f"加载system_list.md失败: {e}，尝试加载CSV文件")

        csv_path = os.path.join(base_dir, "system_list.csv")
        if os.path.exists(csv_path):
            try:
                with open(csv_path, "r", encoding="utf-8", newline="") as f:
                    rows = list(csv.reader(f))
                    if not rows:
                        self._system_list = system_list
                        return system_list

                    header = rows[0]
                    header_map = {str(cell).strip(): idx for idx, cell in enumerate(header) if cell}
                    name_idx = None
                    if "系统名称" in header_map:
                        name_idx = header_map["系统名称"]
                    elif "name" in header_map:
                        name_idx = header_map["name"]

                    data_rows = rows[1:] if name_idx is not None else rows
                    if name_idx is None:
                        name_idx = 0

                    for row in data_rows:
                        if name_idx < len(row):
                            name = str(row[name_idx]).strip() if row[name_idx] is not None else ""
                            if name:
                                system_list.append(name)
            except Exception as e:
                logger.warning(f"加载system_list.csv失败: {e}")

        self._system_list = system_list
        return system_list

    def _guess_system_name(self, text: str, filename: str) -> str:
        """从文本/文件名猜测 system_name（尽量不为空，避免本地向量库拒绝写入）。"""
        system_list = self._load_system_list()
        haystack = text or ""

        best = None
        best_pos = None
        if system_list and haystack:
            # 简单匹配：命中位置越靠前越优，长度越长越优
            for name in system_list:
                if not name:
                    continue
                pos = haystack.find(name)
                if pos < 0:
                    continue
                if best is None:
                    best = name
                    best_pos = pos
                    continue
                if pos < (best_pos or 0) or (pos == best_pos and len(name) > len(best)):
                    best = name
                    best_pos = pos

        if best:
            return best

        stem = os.path.splitext(os.path.basename(filename or ""))[0].strip()
        if stem:
            stem = re.sub(r"[_\\-]+", " ", stem).strip()
            return stem[:50]

        return "通用"

    def _coerce_to_text(self, parsed: Any) -> str:
        """将解析结果尽量转为可用于 embedding 的纯文本。"""
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

        if isinstance(parsed, list):
            parts: List[str] = []
            for item in parsed:
                if isinstance(item, dict):
                    line = " | ".join(
                        f"{k}:{str(v).strip()}" for k, v in item.items() if str(v).strip()
                    )
                    if line.strip():
                        parts.append(line)
                elif isinstance(item, (list, tuple)):
                    line = " | ".join(str(v).strip() for v in item if str(v).strip())
                    if line.strip():
                        parts.append(line)
                else:
                    s = str(item).strip()
                    if s:
                        parts.append(s)
            return "\n".join(parts)

        if isinstance(parsed, dict):
            # DOCX
            if "paragraphs" in parsed:
                parts: List[str] = []
                for para in parsed.get("paragraphs") or []:
                    if isinstance(para, dict):
                        t = str(para.get("text") or "").strip()
                        if t:
                            parts.append(t)
                for table in parsed.get("tables") or []:
                    if not isinstance(table, dict):
                        continue
                    for row in table.get("data") or []:
                        if isinstance(row, list):
                            line = " | ".join(str(v).strip() for v in row if str(v).strip())
                            if line.strip():
                                parts.append(line)
                return "\n".join(parts)

            # PDF
            if "pages" in parsed:
                parts: List[str] = []
                for page in parsed.get("pages") or []:
                    if isinstance(page, dict):
                        t = str(page.get("text") or "").strip()
                        if t:
                            parts.append(t)
                return "\n".join(parts)

            # PPTX
            if "slides" in parsed:
                parts: List[str] = []
                for slide in parsed.get("slides") or []:
                    if isinstance(slide, dict):
                        t = str(slide.get("text") or "").strip()
                        if t:
                            parts.append(t)
                return "\n".join(parts)

            # XLSX（sheet -> rows）
            if parsed and all(isinstance(v, list) for v in parsed.values()):
                parts: List[str] = []
                for sheet_name, rows in parsed.items():
                    if not isinstance(rows, list):
                        continue
                    parts.append(f"[Sheet] {sheet_name}")
                    for row in rows[:200]:
                        if isinstance(row, list):
                            line = " | ".join(str(v).strip() for v in row if v is not None and str(v).strip())
                            if line.strip():
                                parts.append(line)
                return "\n".join(parts)

            # 兜底：JSON
            try:
                return json.dumps(parsed, ensure_ascii=False, indent=2)
            except Exception:
                return str(parsed)

        return str(parsed)

    def _chunk_text(self, text: str) -> List[str]:
        """按固定窗口切分文本，适配 embedding 单次输入长度限制。"""
        cleaned = (text or "").strip()
        if not cleaned:
            return []

        size = int(self.UNSTRUCTURED_CHUNK_SIZE)
        overlap = int(self.UNSTRUCTURED_CHUNK_OVERLAP)
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
            if len(chunks) >= int(self.MAX_UNSTRUCTURED_CHUNKS):
                break
        return chunks

    def _default_metrics(self) -> Dict[str, Any]:
        return {
            "total_tasks": 0,
            "total_searches": 0,
            "successful_searches": 0,
            "similarities": [],
            "total_cases_saved": 0,
            "total_modifications": 0,
            "quality_comparison": {
                "with_kb": 85.2,
                "without_kb": 72.1
            }
        }

    def _ensure_metrics_defaults(self, data: Any) -> Dict[str, Any]:
        if not isinstance(data, dict):
            return self._default_metrics()
        defaults = self._default_metrics()
        for key, value in defaults.items():
            if key not in data:
                data[key] = value
        return data

    @contextmanager
    def _metrics_lock(self):
        if METRICS_LOCK_AVAILABLE:
            os.makedirs(os.path.dirname(self.metrics_lock_file) or ".", exist_ok=True)
            with open(self.metrics_lock_file, "a") as lock_file:
                fcntl.flock(lock_file, fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(lock_file, fcntl.LOCK_UN)
        else:
            yield

    def _load_metrics_unlocked(self) -> Dict[str, Any]:
        if not os.path.exists(self.metrics_file):
            return self._default_metrics()
        try:
            with open(self.metrics_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return self._ensure_metrics_defaults(data)
        except Exception as e:
            logger.warning(f"读取评估指标失败: {e}")
            return self._default_metrics()

    def _save_metrics_unlocked(self, data: Dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(self.metrics_file) or ".", exist_ok=True)
        tmp_path = f"{self.metrics_file}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self.metrics_file)

    @contextmanager
    def _metrics_context(self):
        with self._metrics_lock():
            data = self._load_metrics_unlocked()
            yield data
            self._save_metrics_unlocked(data)

    def _load_metrics(self) -> Dict[str, Any]:
        with self._metrics_lock():
            return self._load_metrics_unlocked()

    @contextmanager
    def _retrieval_lock(self):
        if METRICS_LOCK_AVAILABLE:
            os.makedirs(os.path.dirname(self.retrieval_log_lock_file) or ".", exist_ok=True)
            with open(self.retrieval_log_lock_file, "a") as lock_file:
                fcntl.flock(lock_file, fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(lock_file, fcntl.LOCK_UN)
        else:
            yield

    def _load_retrieval_logs_unlocked(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.retrieval_log_file):
            return []
        try:
            with open(self.retrieval_log_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception as e:
            logger.warning(f"读取知识检索日志失败: {e}")
            return []

    def _save_retrieval_logs_unlocked(self, items: List[Dict[str, Any]]) -> None:
        os.makedirs(os.path.dirname(self.retrieval_log_file) or ".", exist_ok=True)
        tmp_path = f"{self.retrieval_log_file}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self.retrieval_log_file)

    @contextmanager
    def _retrieval_context(self):
        with self._retrieval_lock():
            items = self._load_retrieval_logs_unlocked()
            yield items
            self._save_retrieval_logs_unlocked(items)

    def import_from_file(
        self,
        file_content: bytes,
        filename: str,
        file_type: str = None,
        auto_extract: bool = True,
        knowledge_type: Optional[str] = None,
        system_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        从文件导入知识

        Args:
            file_content: 文件内容（字节）
            filename: 文件名
            file_type: 文件类型（如果为None则自动推断）
            auto_extract: 是否自动提取结构化数据

        Returns:
            dict: 导入结果
                {
                    "total": int,       # 总条数
                    "success": int,     # 成功条数
                    "failed": int,      # 失败条数
                    "errors": list      # 错误信息
                }
        """
        try:
            logger.info(f"开始导入文件: {filename}")

            normalized_system = str(system_name or "").strip()
            if not normalized_system:
                raise ValueError("system_name不能为空")

            normalized_type = str(knowledge_type or "").strip()
            if normalized_type and normalized_type != self.TYPE_SYSTEM_PROFILE:
                raise ValueError("当前仅支持导入 system_profile（系统知识）")

            # 1. 解析文档
            parsed_data = self.document_parser.parse(
                file_content=file_content,
                filename=filename,
                file_type=file_type
            )

            # 2. 提取结构化知识
            extracted = {}
            if auto_extract:
                extracted = self.document_parser.extract_system_knowledge(
                    parsed_data,
                    expected_type=self.TYPE_SYSTEM_PROFILE
                )

            if extracted.get("type") != "system_profile" or not extracted.get("systems"):
                raise ValueError("未能从文档中提取系统知识，请使用DOCX/PPTX模板填写后再导入")

            # 3. 导入到向量库
            result = self._import_extracted_data(
                extracted_data=extracted,
                source_file=filename,
                system_name=normalized_system
            )

            logger.info(f"文件导入完成: {result}")

            return result

        except Exception as e:
            logger.error(f"文件导入失败: {str(e)}")
            return {
                "total": 0,
                "success": 0,
                "failed": 1,
                "errors": [str(e)]
            }

    def _import_extracted_data(
        self,
        extracted_data: Dict[str, Any],
        source_file: str,
        system_name: str
    ) -> Dict[str, Any]:
        """
        导入提取的数据

        Args:
            extracted_data: 提取的数据
            source_file: 来源文件

        Returns:
            dict: 导入结果
        """
        total = 0
        success = 0
        failed = 0
        errors = []

        data_type = extracted_data.get("type", "")

        # 系统知识
        if data_type == "system_profile":
            systems = extracted_data.get("systems", [])
            total = len(systems)

            knowledge_list = []
            for system in systems:
                try:
                    system_record = dict(system or {})
                    original_name = str(system_record.get("system_name") or "").strip()
                    if original_name and original_name != system_name:
                        system_record["original_system_name"] = original_name
                    system_record["system_name"] = system_name

                    # 构建检索文本
                    content = self._build_system_profile_text(system_record)

                    # 生成embedding
                    embedding = self.embedding_service.generate_embedding(content)

                    # 构建元数据
                    metadata = {
                        **system_record,
                        "kb_system_name": system_name,
                        "imported_at": datetime.now().isoformat()
                    }

                    knowledge_list.append({
                        "system_name": system_name,
                        "knowledge_type": self.TYPE_SYSTEM_PROFILE,
                        "content": content,
                        "embedding": embedding,
                        "metadata": metadata,
                        "source_file": source_file
                    })

                except Exception as e:
                    failed += 1
                    errors.append({
                        "item": (system or {}).get("system_name", "unknown"),
                        "error": str(e)
                    })

            # 批量插入
            if knowledge_list:
                inserted = self.vector_store.batch_insert_knowledge(knowledge_list)
                success = int(inserted.get("success") or 0)
                failed += int(inserted.get("failed") or 0)
                if inserted.get("failed"):
                    errors.append(f"部分条目写入向量库失败: {inserted.get('failed')}")
        else:
            errors.append("无法识别的导入数据类型（仅支持system_profile）")

        return {
            "total": total,
            "success": success,
            "failed": failed,
            "errors": errors
        }

    def search_similar_knowledge(
        self,
        query_text: str,
        system_name: str = None,
        knowledge_type: str = None,
        top_k: int = 5,
        similarity_threshold: float = 0.6,
        task_id: Optional[str] = None,
        module: Optional[str] = None,
        feature_name: Optional[str] = None,
        stage: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        检索相似知识

        Args:
            query_text: 查询文本
            system_name: 过滤系统名称
            knowledge_type: 过滤知识类型
            top_k: 返回最相似的K个结果
            similarity_threshold: 相似度阈值

        Returns:
            list: 检索结果列表
        """
        try:
            # 生成查询向量
            query_embedding = self.embedding_service.generate_embedding(query_text)

            # 执行向量搜索
            results = self.vector_store.search_knowledge(
                query_embedding=query_embedding,
                system_name=system_name,
                knowledge_type=knowledge_type,
                top_k=top_k,
                similarity_threshold=similarity_threshold
            )

            # 记录检索事件（用于效果评估）
            max_similarity = max([r.get("similarity", 0.0) for r in results]) if results else 0.0
            self.log_search_event(success=len(results) > 0, similarity=max_similarity)
            self.log_retrieval_event(
                task_id=task_id,
                system_name=system_name,
                module=module,
                feature_name=feature_name,
                knowledge_type=knowledge_type,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
                results=results,
                stage=stage
            )

            logger.info(f"检索完成: 查询到 {len(results)} 条结果")

            return results

        except Exception as e:
            logger.error(f"检索失败: {str(e)}")
            return []

    def build_knowledge_context(
        self,
        knowledge_list: List[Dict[str, Any]],
        max_length: int = 2000
    ) -> str:
        """
        构建知识上下文（用于Agent Prompt）

        Args:
            knowledge_list: 知识列表
            max_length: 最大长度（字符数）

        Returns:
            str: 格式化的知识上下文
        """
        if not knowledge_list:
            return ""

        context_parts = []
        current_length = 0

        for idx, knowledge in enumerate(knowledge_list, 1):
            if not isinstance(knowledge, dict):
                continue

            knowledge_type = str(knowledge.get("knowledge_type") or "").strip()
            if knowledge_type != self.TYPE_SYSTEM_PROFILE:
                continue

            metadata = knowledge.get("metadata") or {}
            part = f"""【知识{idx}】{metadata.get('system_name', '')} ({metadata.get('system_short_name', '')})
   - 业务目标: {metadata.get('business_goal', '')}
   - 核心功能: {metadata.get('core_functions', '')}
   - 系统边界(做什么): {metadata.get('in_scope', '')}
   - 系统不做什么: {metadata.get('out_of_scope', '')}
   - 主要集成点/上下游: {metadata.get('integration_points', '')}
   - 关键约束: {metadata.get('key_constraints', '')}
   - 技术栈: {metadata.get('tech_stack', '')}
   - 架构特点: {metadata.get('architecture', '')}
   - 性能指标: {metadata.get('performance', '')}
   - 相似度: {knowledge.get('similarity', 0.0):.2f}
"""

            # 检查长度
            if current_length + len(part) > max_length:
                break

            context_parts.append(part)
            current_length += len(part)

        return "\n".join(context_parts)

    def _build_system_profile_text(self, system: Dict[str, Any]) -> str:
        """构建系统知识的检索文本"""
        system = system or {}
        return (
            f"系统名称:{system.get('system_name', '') or ''} | "
            f"系统简称:{system.get('system_short_name', '') or ''} | "
            f"系统边界(做什么):{system.get('in_scope', '') or ''} | "
            f"系统不做什么:{system.get('out_of_scope', '') or ''} | "
            f"主要集成点/上下游:{system.get('integration_points', '') or ''} | "
            f"关键约束:{system.get('key_constraints', '') or ''} | "
            f"业务目标:{system.get('business_goal', '') or ''} | "
            f"核心功能:{system.get('core_functions', '') or ''} | "
            f"技术栈:{system.get('tech_stack', '') or ''} | "
            f"架构特点:{system.get('architecture', '') or ''} | "
            f"性能指标:{system.get('performance', '') or ''} | "
            f"主要用户:{system.get('main_users', '') or ''}"
        )

    def get_knowledge_stats(self, system_name: Optional[str] = None) -> Dict[str, Any]:
        """
        获取知识库统计信息

        Returns:
            dict: 统计信息
        """
        try:
            normalized_system = str(system_name or "").strip() or None
            try:
                stats = (
                    self.vector_store.get_collection_stats(system_name=normalized_system)
                    if normalized_system
                    else self.vector_store.get_collection_stats()
                ) or {}
            except TypeError:
                stats = self.vector_store.get_collection_stats() or {}
                if normalized_system:
                    stats["filtered_by_system_name"] = normalized_system
            stats["vector_store_backend"] = self.vector_store_backend

            counts: Dict[str, int] = {}
            if hasattr(self.vector_store, "get_type_counts"):
                try:
                    try:
                        counts = (
                            self.vector_store.get_type_counts(system_name=normalized_system)
                            if normalized_system
                            else self.vector_store.get_type_counts()
                        ) or {}
                    except TypeError:
                        counts = self.vector_store.get_type_counts() or {}
                except Exception as e:
                    logger.warning(f"读取知识类型统计失败: {e}")

            stats["system_profile_count"] = int(counts.get(self.TYPE_SYSTEM_PROFILE, 0) or 0)
            stats["feature_case_count"] = 0
            stats["tech_spec_count"] = 0
            return stats
        except Exception as e:
            logger.error(f"获取统计信息失败: {str(e)}")
            return {}

    def rebuild_index(self) -> Dict[str, Any]:
        """
        重建索引

        Returns:
            dict: 重建结果
        """
        try:
            if hasattr(self.vector_store, "rebuild_index"):
                return self.vector_store.rebuild_index()

            return {"status": "success", "message": "当前存储后端无需重建索引"}
        except Exception as e:
            logger.error(f"重建索引失败: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }

    def get_evaluation_metrics(self) -> Dict[str, Any]:
        """
        获取知识库效果评估指标

        Returns:
            dict: 评估指标
                - hit_rate: 检索命中率（%）
                - avg_similarity: 平均相似度（%）
                - adoption_rate: 案例采纳率（%）
                - total_searches: 总检索次数
                - total_tasks: 总评估任务数
                - quality_comparison: 质量对比（使用 vs 未使用知识库）
        """
        try:
            metrics_data = self._load_metrics()

            # 计算检索命中率
            total_tasks = metrics_data.get("total_tasks", 0)
            total_searches = metrics_data.get("total_searches", 0)
            successful_searches = metrics_data.get("successful_searches", 0)

            hit_rate = (successful_searches / total_searches * 100) if total_searches > 0 else 0.0

            # 计算平均相似度
            similarities = metrics_data.get("similarities", [])
            avg_similarity = (sum(similarities) / len(similarities) * 100) if similarities else 0.0

            # 计算采纳率
            total_cases_saved = metrics_data.get("total_cases_saved", 0)
            total_modifications = metrics_data.get("total_modifications", 0)
            adoption_rate = (total_cases_saved / total_modifications * 100) if total_modifications > 0 else 0.0

            # 质量对比（示例数据，实际应从专家评估系统获取）
            quality_comparison = metrics_data.get("quality_comparison", {
                "with_kb": 85.2,   # 使用知识库的准确度
                "without_kb": 72.1  # 未使用知识库的准确度
            })

            return {
                "hit_rate": round(hit_rate, 1),
                "avg_similarity": round(avg_similarity, 1),
                "adoption_rate": round(adoption_rate, 1),
                "total_searches": total_searches,
                "total_tasks": total_tasks,
                "quality_comparison": quality_comparison
            }

        except Exception as e:
            logger.error(f"获取评估指标失败: {str(e)}")
            raise

    def log_search_event(self, success: bool, similarity: float = 0.0):
        """
        记录检索事件（用于评估）

        Args:
            success: 是否成功检索到知识
            similarity: 检索结果的最高相似度
        """
        try:
            with self._metrics_context() as metrics_data:
                metrics_data["total_searches"] += 1

                if success:
                    metrics_data["successful_searches"] += 1
                    if similarity > 0:
                        metrics_data["similarities"].append(similarity)
                        # 只保留最近100条
                        if len(metrics_data["similarities"]) > 100:
                            metrics_data["similarities"] = metrics_data["similarities"][-100:]

        except Exception as e:
            logger.warning(f"记录检索事件失败: {e}")

    def log_retrieval_event(
        self,
        task_id: Optional[str] = None,
        system_name: Optional[str] = None,
        module: Optional[str] = None,
        feature_name: Optional[str] = None,
        knowledge_type: Optional[str] = None,
        top_k: Optional[int] = None,
        similarity_threshold: Optional[float] = None,
        results: Optional[List[Dict[str, Any]]] = None,
        stage: Optional[str] = None
    ) -> None:
        try:
            results = results or []
            max_similarity = max([r.get("similarity", 0.0) for r in results]) if results else 0.0
            hits = []
            for item in results:
                metadata = item.get("metadata") or {}
                hits.append({
                    "system_name": item.get("system_name"),
                    "knowledge_type": item.get("knowledge_type"),
                    "module": metadata.get("module"),
                    "feature_name": metadata.get("feature_name"),
                    "similarity": item.get("similarity"),
                    "source_file": item.get("source_file")
                })
            log_item = {
                "id": f"kh_{uuid.uuid4().hex[:10]}",
                "task_id": task_id,
                "system_name": system_name,
                "module": module,
                "feature_name": feature_name,
                "knowledge_type": knowledge_type,
                "top_k": top_k,
                "similarity_threshold": similarity_threshold,
                "hit_count": len(results),
                "max_similarity": max_similarity,
                "hits": hits,
                "stage": stage,
                "created_at": datetime.now().isoformat()
            }
            with self._retrieval_context() as items:
                items.append(log_item)
        except Exception as e:
            logger.warning(f"记录知识检索日志失败: {e}")

    def get_hit_rate(
        self,
        task_id: Optional[str] = None,
        system_name: Optional[str] = None,
        module: Optional[str] = None,
        knowledge_type: Optional[str] = None
    ) -> Optional[float]:
        try:
            with self._retrieval_lock():
                logs = self._load_retrieval_logs_unlocked()
            if not logs:
                return None
            filtered = []
            for item in logs:
                if task_id and item.get("task_id") != task_id:
                    continue
                if system_name and item.get("system_name") != system_name:
                    continue
                if module and item.get("module") != module:
                    continue
                if knowledge_type and item.get("knowledge_type") != knowledge_type:
                    continue
                filtered.append(item)
            if not filtered:
                return None
            total = len(filtered)
            hit_count = sum(1 for item in filtered if item.get("hit_count", 0) > 0)
            return round((hit_count / total) * 100, 2)
        except Exception as e:
            logger.warning(f"计算知识命中率失败: {e}")
            return None

    def log_case_adoption(self):
        """
        记录案例采纳事件（用于评估）
        """
        try:
            with self._metrics_context() as metrics_data:
                metrics_data["total_cases_saved"] += 1

        except Exception as e:
            logger.warning(f"记录案例采纳失败: {e}")

    def log_task_event(self):
        """记录任务创建事件（用于评估）"""
        try:
            with self._metrics_context() as metrics_data:
                metrics_data["total_tasks"] += 1
        except Exception as e:
            logger.warning(f"记录任务事件失败: {e}")

    def log_modification_event(self):
        """记录修改事件（用于评估）"""
        try:
            with self._metrics_context() as metrics_data:
                metrics_data["total_modifications"] += 1
        except Exception as e:
            logger.warning(f"记录修改事件失败: {e}")



# 全局服务实例
_knowledge_service = None


def get_knowledge_service() -> KnowledgeService:
    """获取知识库服务单例"""
    global _knowledge_service
    if _knowledge_service is None:
        _knowledge_service = KnowledgeService()
    return _knowledge_service
