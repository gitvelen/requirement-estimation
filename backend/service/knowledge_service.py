"""
知识库服务
提供知识的导入、检索、管理等核心功能
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from backend.service.milvus_client import get_milvus_client
from backend.service.embedding_service import get_embedding_service
from backend.service.document_parser import get_document_parser

logger = logging.getLogger(__name__)


class KnowledgeService:
    """知识库服务"""

    # 知识类型
    TYPE_SYSTEM_PROFILE = "system_profile"  # 系统知识
    TYPE_FEATURE_CASE = "feature_case"      # 功能案例
    TYPE_TECH_SPEC = "tech_spec"            # 技术规范

    def __init__(self):
        """初始化服务"""
        self.milvus_client = get_milvus_client()
        self.embedding_service = get_embedding_service()
        self.document_parser = get_document_parser()
        logger.info("知识库服务初始化完成")

    def import_from_file(
        self,
        file_content: bytes,
        filename: str,
        file_type: str = None,
        auto_extract: bool = True
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

            # 1. 解析文档
            parsed_data = self.document_parser.parse(
                file_content=file_content,
                filename=filename,
                file_type=file_type
            )

            # 2. 提取结构化知识
            if auto_extract:
                extracted = self.document_parser.extract_system_knowledge(parsed_data)
            else:
                extracted = {"raw": parsed_data}

            # 3. 导入到向量库
            result = self._import_extracted_data(
                extracted_data=extracted,
                source_file=filename
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
        source_file: str
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
                    # 构建检索文本
                    content = self._build_system_profile_text(system)

                    # 生成embedding
                    embedding = self.embedding_service.generate_embedding(content)

                    # 构建元数据
                    metadata = {
                        **system,
                        "imported_at": datetime.now().isoformat()
                    }

                    knowledge_list.append({
                        "system_name": system["system_name"],
                        "knowledge_type": self.TYPE_SYSTEM_PROFILE,
                        "content": content,
                        "embedding": embedding,
                        "metadata": metadata,
                        "source_file": source_file
                    })

                    success += 1

                except Exception as e:
                    failed += 1
                    errors.append({
                        "item": system.get("system_name", "unknown"),
                        "error": str(e)
                    })

            # 批量插入
            if knowledge_list:
                self.milvus_client.batch_insert_knowledge(knowledge_list)

        # 功能案例
        elif data_type == "feature_case":
            cases = extracted_data.get("cases", [])
            total = len(cases)

            knowledge_list = []
            for case in cases:
                try:
                    # 构建检索文本
                    content = self._build_feature_case_text(case)

                    # 生成embedding
                    embedding = self.embedding_service.generate_embedding(content)

                    # 构建元数据
                    metadata = {
                        **case,
                        "imported_at": datetime.now().isoformat()
                    }

                    knowledge_list.append({
                        "system_name": case["system_name"],
                        "knowledge_type": self.TYPE_FEATURE_CASE,
                        "content": content,
                        "embedding": embedding,
                        "metadata": metadata,
                        "source_file": source_file
                    })

                    success += 1

                except Exception as e:
                    failed += 1
                    errors.append({
                        "item": case.get("feature_name", "unknown"),
                        "error": str(e)
                    })

            # 批量插入
            if knowledge_list:
                self.milvus_client.batch_insert_knowledge(knowledge_list)

        # 非结构化数据
        elif data_type == "unstructured":
            # TODO: 实现非结构化数据的智能提取
            total = 0
            success = 0
            failed = 0
            errors.append("暂不支持非结构化数据的自动导入")

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
        similarity_threshold: float = 0.6
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
            results = self.milvus_client.search_knowledge(
                query_embedding=query_embedding,
                system_name=system_name,
                knowledge_type=knowledge_type,
                top_k=top_k,
                similarity_threshold=similarity_threshold
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
            knowledge_type = knowledge["knowledge_type"]

            # 系统知识
            if knowledge_type == self.TYPE_SYSTEM_PROFILE:
                metadata = knowledge["metadata"]
                part = f"""【知识{idx}】{metadata['system_name']} ({metadata['system_short_name']})
   - 业务目标: {metadata['business_goal']}
   - 核心功能: {metadata['core_functions']}
   - 技术栈: {metadata['tech_stack']}
   - 架构特点: {metadata['architecture']}
   - 性能指标: {metadata['performance']}
   - 相似度: {knowledge['similarity']:.2f}
"""

            # 功能案例
            elif knowledge_type == self.TYPE_FEATURE_CASE:
                metadata = knowledge["metadata"]
                part = f"""【案例{idx}】{metadata['feature_name']}
   - 系统名称: {metadata['system_name']}
   - 功能模块: {metadata['module']}
   - 业务描述: {metadata['description']}
   - 预估人天: {metadata['estimated_days']}
   - 复杂度: {metadata['complexity']}
   - 技术要点: {metadata['tech_points']}
   - 依赖系统: {metadata['dependencies']}
   - 实施案例: {metadata['project_case']}
   - 相似度: {knowledge['similarity']:.2f}
"""

            else:
                continue

            # 检查长度
            if current_length + len(part) > max_length:
                break

            context_parts.append(part)
            current_length += len(part)

        return "\n".join(context_parts)

    def _build_system_profile_text(self, system: Dict[str, Any]) -> str:
        """构建系统知识的检索文本"""
        return f"""系统名称:{system['system_name']} | \
系统简称:{system['system_short_name']} | \
业务目标:{system['business_goal']} | \
核心功能:{system['core_functions']} | \
技术栈:{system['tech_stack']} | \
架构特点:{system['architecture']} | \
性能指标:{system['performance']} | \
主要用户:{system['main_users']}"""

    def _build_feature_case_text(self, case: Dict[str, Any]) -> str:
        """构建功能案例的检索文本"""
        return f"""系统名称:{case['system_name']} | \
功能模块:{case['module']} | \
功能点:{case['feature_name']} | \
业务描述:{case['description']} | \
预估人天:{case['estimated_days']} | \
复杂度:{case['complexity']} | \
技术要点:{case['tech_points']} | \
依赖系统:{case['dependencies']}"""

    def get_knowledge_stats(self) -> Dict[str, Any]:
        """
        获取知识库统计信息

        Returns:
            dict: 统计信息
        """
        try:
            stats = self.milvus_client.get_collection_stats()
            return stats
        except Exception as e:
            logger.error(f"获取统计信息失败: {str(e)}")
            return {}

    def save_feature_case(
        self,
        system_name: str,
        module: str,
        feature_name: str,
        description: str,
        estimated_days: float,
        complexity: str,
        tech_points: str = "",
        dependencies: str = "",
        project_case: str = "",
        source: str = "人工修正"
    ) -> Dict[str, Any]:
        """
        保存单个功能案例到知识库

        Args:
            system_name: 系统名称
            module: 功能模块
            feature_name: 功能点名称
            description: 业务描述
            estimated_days: 预估人天
            complexity: 复杂度（高/中/低）
            tech_points: 技术要点
            dependencies: 依赖系统
            project_case: 实施案例
            source: 来源（人工修正/历史案例）

        Returns:
            dict: 保存结果
        """
        try:
            logger.info(f"保存功能案例: {system_name} - {feature_name}")

            # 构建案例数据
            case = {
                "system_name": system_name,
                "module": module,
                "feature_name": feature_name,
                "description": description,
                "estimated_days": estimated_days,
                "complexity": complexity,
                "tech_points": tech_points,
                "dependencies": dependencies,
                "project_case": project_case,
                "created_date": datetime.now().strftime("%Y-%m-%d")
            }

            # 构建检索文本
            content = self._build_feature_case_text(case)

            # 生成embedding
            embedding = self.embedding_service.generate_embedding(content)

            # 构建元数据
            metadata = {
                **case,
                "source": source,
                "imported_at": datetime.now().isoformat()
            }

            # 插入到Milvus
            self.milvus_client.insert_knowledge(
                system_name=system_name,
                knowledge_type=self.TYPE_FEATURE_CASE,
                content=content,
                embedding=embedding,
                metadata=metadata
            )

            # 追加到CSV文件
            self._append_case_to_csv(case)

            logger.info(f"功能案例保存成功: {feature_name}")

            return {
                "status": "success",
                "message": "案例保存成功",
                "case": case
            }

        except Exception as e:
            logger.error(f"保存功能案例失败: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }

    def _append_case_to_csv(self, case: Dict[str, Any]):
        """
        追加案例到CSV文件

        Args:
            case: 案例数据
        """
        import os
        import csv

        csv_file = "data/feature_case_library.csv"

        # 确保目录存在
        os.makedirs("data", exist_ok=True)

        # 检查文件是否存在，如果不存在则写入表头
        file_exists = os.path.exists(csv_file)

        # 准备数据行
        row = {
            "系统名称": case["system_name"],
            "功能模块": case["module"],
            "功能点名称": case["feature_name"],
            "业务描述": case["description"],
            "预估人天": case["estimated_days"],
            "复杂度": case["complexity"],
            "技术要点": case.get("tech_points", ""),
            "依赖系统": case.get("dependencies", ""),
            "实施案例": case.get("project_case", ""),
            "创建日期": case["created_date"]
        }

        # 追加到CSV
        with open(csv_file, 'a', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=row.keys())
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)

        logger.info(f"案例已追加到CSV: {csv_file}")

    def rebuild_index(self) -> Dict[str, Any]:
        """
        重建索引

        Returns:
            dict: 重建结果
        """
        try:
            # TODO: 实现索引重建逻辑
            return {
                "status": "success",
                "message": "索引重建功能待实现"
            }
        except Exception as e:
            logger.error(f"重建索引失败: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }


# 全局服务实例
_knowledge_service = None


def get_knowledge_service() -> KnowledgeService:
    """获取知识库服务单例"""
    global _knowledge_service
    if _knowledge_service is None:
        _knowledge_service = KnowledgeService()
    return _knowledge_service
