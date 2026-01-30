"""
Milvus向量数据库客户端
提供知识库的向量存储和检索功能
"""
import logging
from typing import List, Dict, Any, Optional
from pymilvus import (
    connections,
    Collection,
    CollectionSchema,
    FieldSchema,
    DataType,
    utility
)
from backend.config.config import settings

logger = logging.getLogger(__name__)


class MilvusClient:
    """Milvus向量数据库客户端"""

    # Collection名称
    COLLECTION_NAME = "system_knowledge"

    # 向量维度（阿里云text-embedding-v2）
    EMBEDDING_DIM = 1024

    def __init__(self):
        """初始化Milvus客户端"""
        self.host = settings.MILVUS_HOST
        self.port = settings.MILVUS_PORT
        self.collection = None
        self._connect()
        self._init_collection()

    def _connect(self):
        """连接到Milvus服务器"""
        try:
            connections.connect(
                alias="default",
                host=self.host,
                port=self.port
            )
            logger.info(f"成功连接到Milvus: {self.host}:{self.port}")

            # 测试连接
            from pymilvus import utility
            if utility.has_collection("test"):
                logger.info("Milvus连接测试成功")
        except Exception as e:
            logger.error(f"连接Milvus失败: {str(e)}")
            raise

    def _init_collection(self):
        """初始化Collection（如果不存在则创建）"""
        try:
            # 检查Collection是否存在
            if utility.has_collection(self.COLLECTION_NAME):
                self.collection = Collection(self.COLLECTION_NAME)
                logger.info(f"已加载Collection: {self.COLLECTION_NAME}")

                # 加载到内存（以便搜索）
                self.collection.load()
                logger.info("Collection已加载到内存")
            else:
                # 创建新的Collection
                self._create_collection()
        except Exception as e:
            logger.error(f"初始化Collection失败: {str(e)}")
            raise

    def _create_collection(self):
        """创建Collection"""
        try:
            # 定义Schema
            fields = [
                FieldSchema(
                    name="id",
                    dtype=DataType.INT64,
                    is_primary=True,
                    auto_id=True
                ),
                FieldSchema(
                    name="system_name",
                    dtype=DataType.VARCHAR,
                    max_length=255
                ),
                FieldSchema(
                    name="knowledge_type",
                    dtype=DataType.VARCHAR,
                    max_length=50
                ),
                FieldSchema(
                    name="content",
                    dtype=DataType.VARCHAR,
                    max_length=65535  # 最大64KB
                ),
                FieldSchema(
                    name="embedding",
                    dtype=DataType.FLOAT_VECTOR,
                    dim=self.EMBEDDING_DIM
                ),
                FieldSchema(
                    name="metadata",
                    dtype=DataType.VARCHAR,
                    max_length=65535
                ),
                FieldSchema(
                    name="source_file",
                    dtype=DataType.VARCHAR,
                    max_length=500
                )
            ]

            schema = CollectionSchema(
                fields=fields,
                description="系统知识库 - 存储系统知识"
            )

            # 创建Collection
            self.collection = Collection(
                name=self.COLLECTION_NAME,
                schema=schema
            )

            # 创建索引
            index_params = {
                "index_type": "IVF_FLAT",
                "metric_type": "IP",  # Inner Product（内积）
                "params": {"nlist": 128}
            }

            self.collection.create_index(
                field_name="embedding",
                index_params=index_params
            )

            logger.info(f"成功创建Collection: {self.COLLECTION_NAME}")

        except Exception as e:
            logger.error(f"创建Collection失败: {str(e)}")
            raise

    def insert_knowledge(
        self,
        system_name: str,
        knowledge_type: str,
        content: str,
        embedding: List[float],
        metadata: Dict[str, Any],
        source_file: str = None
    ) -> str:
        """
        插入知识条目

        Args:
            system_name: 系统名称
            knowledge_type: 知识类型（当前仅维护 system_profile）
            content: 原始文本内容
            embedding: 向量embedding
            metadata: 元数据（JSON序列化后的字典）
            source_file: 来源文件

        Returns:
            str: 插入结果的描述
        """
        try:
            import json

            # 准备数据
            data = [
                [system_name],
                [knowledge_type],
                [content],
                [embedding],
                [json.dumps(metadata, ensure_ascii=False)],
                [source_file or ""]
            ]

            # 插入数据
            insert_result = self.collection.insert(data)

            # 刷新（使数据可搜索）
            self.collection.flush()

            logger.info(f"成功插入知识: system={system_name}, type={knowledge_type}")

            return f"插入成功，ID: {insert_result.primary_keys[0]}"

        except Exception as e:
            logger.error(f"插入知识失败: {str(e)}")
            raise

    def batch_insert_knowledge(
        self,
        knowledge_list: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """
        批量插入知识

        Args:
            knowledge_list: 知识列表
                每个元素包含: system_name, knowledge_type, content,
                           embedding, metadata, source_file

        Returns:
            dict: {"success": int, "failed": int}
        """
        try:
            import json

            success_count = 0
            failed_count = 0

            # 准备批量数据
            system_names = []
            knowledge_types = []
            contents = []
            embeddings = []
            metadatas = []
            source_files = []

            for knowledge in knowledge_list:
                try:
                    system_names.append(knowledge["system_name"])
                    knowledge_types.append(knowledge["knowledge_type"])
                    contents.append(knowledge["content"])
                    embeddings.append(knowledge["embedding"])
                    metadatas.append(
                        json.dumps(knowledge["metadata"], ensure_ascii=False)
                    )
                    source_files.append(knowledge.get("source_file", ""))
                    success_count += 1
                except Exception as e:
                    logger.warning(f"准备数据失败: {e}")
                    failed_count += 1

            if success_count > 0:
                # 批量插入
                data = [
                    system_names,
                    knowledge_types,
                    contents,
                    embeddings,
                    metadatas,
                    source_files
                ]

                self.collection.insert(data)
                self.collection.flush()

                logger.info(f"批量插入成功: {success_count}条")

            return {
                "success": success_count,
                "failed": failed_count
            }

        except Exception as e:
            logger.error(f"批量插入失败: {str(e)}")
            raise

    def search_knowledge(
        self,
        query_embedding: List[float],
        system_name: str = None,
        knowledge_type: str = None,
        top_k: int = 10,
        similarity_threshold: float = 0.6
    ) -> List[Dict[str, Any]]:
        """
        向量搜索

        Args:
            query_embedding: 查询向量
            system_name: 过滤系统名称
            knowledge_type: 过滤知识类型
            top_k: 返回最相似的K个结果
            similarity_threshold: 相似度阈值

        Returns:
            list: 检索结果列表
        """
        try:
            import json

            # 构建过滤表达式
            filter_expr = self._build_filter_expr(system_name, knowledge_type)

            # 执行搜索
            results = self.collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param={"metric_type": "IP", "params": {"nprobe": 10}},
                limit=top_k,
                expr=filter_expr,
                output_fields=[
                    "system_name",
                    "knowledge_type",
                    "content",
                    "metadata",
                    "source_file"
                ]
            )

            # 格式化结果
            knowledge_list = []
            for result in results[0]:
                # 相似度过滤
                if result.distance < similarity_threshold:
                    continue

                knowledge_list.append({
                    "system_name": result.entity.get("system_name", ""),
                    "knowledge_type": result.entity.get("knowledge_type", ""),
                    "content": result.entity.get("content", ""),
                    "metadata": json.loads(result.entity.get("metadata", "{}")),
                    "source_file": result.entity.get("source_file", ""),
                    "similarity": float(result.distance)
                })

            logger.info(f"搜索完成: 查询到 {len(knowledge_list)} 条结果")

            return knowledge_list

        except Exception as e:
            logger.error(f"搜索失败: {str(e)}")
            raise

    def _build_filter_expr(
        self,
        system_name: str = None,
        knowledge_type: str = None
    ) -> str:
        """构建过滤表达式"""
        conditions = []

        if system_name:
            safe_system = self._escape_expr_value(system_name)
            conditions.append(f'system_name == "{safe_system}"')

        if knowledge_type:
            safe_type = self._escape_expr_value(knowledge_type)
            conditions.append(f'knowledge_type == "{safe_type}"')

        return " && ".join(conditions) if conditions else ""

    def _escape_expr_value(self, value: str) -> str:
        """转义Milvus表达式字符串"""
        if value is None:
            return ""
        return str(value).replace("\\", "\\\\").replace('"', '\\"')

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        获取Collection统计信息

        Returns:
            dict: 统计信息
        """
        try:
            stats = {
                "name": self.COLLECTION_NAME,
                "count": self.collection.num_entities,
                "index": "IVF_FLAT",
                "metric_type": "IP"
            }

            logger.info(f"Collection统计: {stats}")

            return stats

        except Exception as e:
            logger.error(f"获取统计信息失败: {str(e)}")
            return {}

    def drop_collection(self):
        """删除Collection（慎用！）"""
        try:
            utility.drop_collection(self.COLLECTION_NAME)
            logger.warning(f"已删除Collection: {self.COLLECTION_NAME}")
        except Exception as e:
            logger.error(f"删除Collection失败: {str(e)}")
            raise


# 全局客户端实例
_milvus_client = None


def get_milvus_client() -> MilvusClient:
    """获取Milvus客户端单例"""
    global _milvus_client
    if _milvus_client is None:
        _milvus_client = MilvusClient()
    return _milvus_client
