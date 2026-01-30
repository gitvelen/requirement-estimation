"""
Embedding生成服务
使用阿里云DashScope的text-embedding-v2模型
"""
import logging
from typing import List, Union
import dashscope
from backend.config.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Embedding生成服务"""

    # 模型配置
    MODEL = settings.EMBEDDING_MODEL
    DIM = settings.EMBEDDING_DIM  # 向量维度

    def __init__(self):
        """初始化服务"""
        self.api_key = settings.DASHSCOPE_API_KEY
        if not self.api_key:
            raise ValueError("DASHSCOPE_API_KEY未配置")

        dashscope.api_key = self.api_key
        logger.info(f"Embedding服务初始化完成，模型: {self.MODEL}")

    def generate_embedding(self, text: str) -> List[float]:
        """
        生成单个文本的embedding

        Args:
            text: 输入文本

        Returns:
            list: 向量（维度1024）

        Raises:
            Exception: API调用失败
        """
        try:
            # 调用阿里云API
            response = dashscope.TextEmbedding.call(
                model=self.MODEL,
                input=text
            )

            # 检查响应状态
            if response.status_code != 200:
                error_msg = f"Embedding API调用失败: {response.message}"
                logger.error(error_msg)
                raise Exception(error_msg)

            # 提取向量
            embedding = response['output']['embeddings'][0]['embedding']

            logger.debug(f"成功生成embedding，文本长度: {len(text)}, 向量维度: {len(embedding)}")

            return embedding

        except Exception as e:
            logger.error(f"生成embedding失败: {str(e)}")
            raise

    def batch_generate_embeddings(
        self,
        texts: List[str],
        batch_size: int = 25
    ) -> List[List[float]]:
        """
        批量生成embeddings

        Args:
            texts: 文本列表
            batch_size: 批次大小（阿里云限制单次最多25条）

        Returns:
            list: 向量列表

        Note:
            阿里云text-embedding-v2单次最多处理25条文本
        """
        try:
            all_embeddings = []

            # 分批处理
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]

                # 调用API
                response = dashscope.TextEmbedding.call(
                    model=self.MODEL,
                    input=batch_texts
                )

                if response.status_code != 200:
                    error_msg = f"批量生成失败（批次{i//batch_size + 1}）: {response.message}"
                    logger.error(error_msg)
                    # 单条重试
                    for text in batch_texts:
                        emb = self.generate_embedding(text)
                        all_embeddings.append(emb)
                    continue

                # 提取向量
                embeddings = [
                    item['embedding']
                    for item in response['output']['embeddings']
                ]

                all_embeddings.extend(embeddings)

                logger.info(f"已处理 {len(all_embeddings)}/{len(texts)} 条文本")

            return all_embeddings

        except Exception as e:
            logger.error(f"批量生成失败: {str(e)}")
            raise

    def get_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float]
    ) -> float:
        """
        计算两个向量的相似度（余弦相似度）

        Args:
            embedding1: 向量1
            embedding2: 向量2

        Returns:
            float: 相似度（0-1之间）
        """
        try:
            import numpy as np

            # 转换为numpy数组
            v1 = np.array(embedding1)
            v2 = np.array(embedding2)

            # 计算余弦相似度
            dot_product = np.dot(v1, v2)
            norm1 = np.linalg.norm(v1)
            norm2 = np.linalg.norm(v2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            similarity = dot_product / (norm1 * norm2)

            return float(similarity)

        except Exception as e:
            logger.error(f"计算相似度失败: {str(e)}")
            return 0.0


# 全局服务实例
_embedding_service = None


def get_embedding_service() -> EmbeddingService:
    """获取Embedding服务单例"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
