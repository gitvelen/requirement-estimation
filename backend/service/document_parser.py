"""
多格式文档解析服务
支持CSV、DOCX、XLSX、PDF等多种格式的文档解析
"""
import logging
import csv
import json
from io import StringIO, BytesIO
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class DocumentParser:
    """多格式文档解析器"""

    # 支持的文件类型
    SUPPORTED_TYPES = {
        "csv": "text/csv",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "pdf": "application/pdf"
    }

    def __init__(self):
        """初始化解析器"""
        logger.info("文档解析服务初始化完成")

    def parse(
        self,
        file_content: bytes,
        filename: str,
        file_type: str = None
    ) -> List[Dict[str, Any]]:
        """
        解析文档

        Args:
            file_content: 文件内容（字节）
            filename: 文件名
            file_type: 文件类型（如果为None则从filename推断）

        Returns:
            list: 解析后的数据列表

        Raises:
            ValueError: 不支持的文件类型
            Exception: 解析失败
        """
        # 推断文件类型
        if file_type is None:
            file_ext = Path(filename).suffix.lower().lstrip('.')
            file_type = file_ext

        # 验证文件类型
        if file_type not in self.SUPPORTED_TYPES:
            raise ValueError(
                f"不支持的文件类型: {file_type}，"
                f"支持的类型: {', '.join(self.SUPPORTED_TYPES.keys())}"
            )

        logger.info(f"开始解析文档: {filename} (类型: {file_type})")

        # 根据类型解析
        if file_type == "csv":
            return self._parse_csv(file_content)
        elif file_type == "docx":
            return self._parse_docx(file_content)
        elif file_type == "xlsx":
            return self._parse_xlsx(file_content)
        elif file_type == "pdf":
            return self._parse_pdf(file_content)
        else:
            raise ValueError(f"未实现的文件类型: {file_type}")

    def _parse_csv(self, file_content: bytes) -> List[Dict[str, Any]]:
        """
        解析CSV文件

        支持的CSV格式：
        1. 系统知识库: system_knowledge_base.csv
        2. 功能案例库: feature_case_library.csv
        """
        try:
            # 解码为文本
            text = file_content.decode('utf-8-sig')  # 处理BOM

            # 使用CSV DictReader解析
            reader = csv.DictReader(StringIO(text))

            # 转换为字典列表
            data = []
            for row in reader:
                # 过滤空行
                if any(row.values()):
                    data.append(dict(row))

            logger.info(f"CSV解析成功，共 {len(data)} 行")

            return data

        except UnicodeDecodeError:
            # 尝试GBK编码
            try:
                text = file_content.decode('gbk')
                reader = csv.DictReader(StringIO(text))
                data = [dict(row) for row in reader if any(row.values())]
                logger.info(f"CSV解析成功（GBK编码），共 {len(data)} 行")
                return data
            except Exception as e:
                logger.error(f"CSV解析失败（编码错误）: {str(e)}")
                raise
        except Exception as e:
            logger.error(f"CSV解析失败: {str(e)}")
            raise

    def _parse_docx(self, file_content: bytes) -> List[Dict[str, Any]]:
        """
        解析DOCX文件

        提取内容：
        - 段落文本
        - 表格数据
        - 标题层级
        """
        try:
            from docx import Document
            from docx.table import Table

            # 从字节加载文档
            doc = Document(BytesIO(file_content))

            data = []

            # 提取段落
            paragraphs = []
            for para in doc.paragraphs:
                if para.text.strip():
                    paragraphs.append({
                        "type": "paragraph",
                        "text": para.text.strip(),
                        "style": para.style.name if para.style else "Normal"
                    })

            # 提取表格
            tables = []
            for table in doc.tables:
                table_data = []
                for row in table.rows:
                    row_data = [cell.text.strip() for cell in row.cells]
                    table_data.append(row_data)
                tables.append({
                    "type": "table",
                    "data": table_data
                })

            logger.info(f"DOCX解析成功: {len(paragraphs)}个段落, {len(tables)}个表格")

            # 返回结构化数据
            return {
                "paragraphs": paragraphs,
                "tables": tables,
                "metadata": {
                    "total_paragraphs": len(paragraphs),
                    "total_tables": len(tables)
                }
            }

        except ImportError:
            logger.error("未安装python-docx库，请运行: pip install python-docx")
            raise Exception("缺少DOCX解析库")
        except Exception as e:
            logger.error(f"DOCX解析失败: {str(e)}")
            raise

    def _parse_xlsx(self, file_content: bytes) -> List[Dict[str, Any]]:
        """
        解析XLSX文件

        支持多个Sheet，自动识别系统知识库和功能案例库格式
        """
        try:
            from openpyxl import load_workbook

            # 从字节加载工作簿
            wb = load_workbook(BytesIO(file_content))

            data = {}

            # 遍历所有Sheet
            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]

                # 提取数据
                sheet_data = []
                for row in ws.iter_rows(values_only=True):
                    # 过滤空行
                    if any(cell is not None for cell in row):
                        sheet_data.append(list(row))

                data[sheet_name] = sheet_data
                logger.info(f"Sheet '{sheet_name}': {len(sheet_data)} 行")

            logger.info(f"XLSX解析成功，共 {len(data)} 个Sheet")

            return data

        except ImportError:
            logger.error("未安装openpyxl库，请运行: pip install openpyxl")
            raise Exception("缺少XLSX解析库")
        except Exception as e:
            logger.error(f"XLSX解析失败: {str(e)}")
            raise

    def _parse_pdf(self, file_content: bytes) -> List[Dict[str, Any]]:
        """
        解析PDF文件（基础功能）

        提取：
        - 文本内容
        - 元数据（作者、创建时间等）

        Note: PDF解析较为复杂，此为基础实现
        """
        try:
            import PyPDF2

            # 从字节加载PDF
            pdf_file = BytesIO(file_content)
            reader = PyPDF2.PdfReader(pdf_file)

            # 提取文本
            text_content = []
            for page_num, page in enumerate(reader.pages):
                try:
                    text = page.extract_text()
                    if text.strip():
                        text_content.append({
                            "page": page_num + 1,
                            "text": text.strip()
                        })
                except Exception as e:
                    logger.warning(f"第{page_num + 1}页解析失败: {e}")

            # 提取元数据
            metadata = reader.metadata

            logger.info(f"PDF解析成功: {len(text_content)}页")

            return {
                "pages": text_content,
                "metadata": {
                    "author": metadata.get("/Author", ""),
                    "creator": metadata.get("/Creator", ""),
                    "title": metadata.get("/Title", ""),
                    "page_count": len(reader.pages)
                }
            }

        except ImportError:
            logger.warning("未安装PyPDF2库，PDF解析功能不可用")
            logger.warning("请运行: pip install PyPDF2")
            return {"pages": [], "metadata": {}, "error": "缺少PDF解析库"}
        except Exception as e:
            logger.error(f"PDF解析失败: {str(e)}")
            raise

    def extract_system_knowledge(self, parsed_data: Any) -> Dict[str, Any]:
        """
        从解析后的数据中提取系统知识

        Args:
            parsed_data: 解析后的数据（来自parse方法）

        Returns:
            dict: 系统知识结构化数据
        """
        try:
            # 如果是CSV数据（系统知识库格式）
            if isinstance(parsed_data, list) and len(parsed_data) > 0:
                first_row = parsed_data[0]

                # 识别字段
                if "系统名称" in first_row or "系统简称" in first_row:
                    # 系统知识库格式
                    return self._extract_system_profile(parsed_data)
                elif "功能点名称" in first_row or "功能点" in first_row:
                    # 功能案例库格式
                    return self._extract_feature_cases(parsed_data)

            # 如果是DOCX数据
            if isinstance(parsed_data, dict) and "paragraphs" in parsed_data:
                return self._extract_from_docx(parsed_data)

            # 如果是XLSX数据
            if isinstance(parsed_data, dict) and "metadata" not in parsed_data:
                return self._extract_from_xlsx(parsed_data)

            logger.warning("无法识别的知识库格式")
            return {}

        except Exception as e:
            logger.error(f"提取系统知识失败: {str(e)}")
            return {}

    def _extract_system_profile(self, data: List[Dict]) -> Dict[str, Any]:
        """从CSV数据提取系统知识"""
        systems = []

        for row in data:
            system = {
                "system_name": row.get("系统名称", ""),
                "system_short_name": row.get("系统简称", ""),
                "system_category": row.get("系统分类", ""),
                "business_goal": row.get("业务目标", ""),
                "core_functions": row.get("核心功能", ""),
                "tech_stack": row.get("技术栈", ""),
                "architecture": row.get("架构特点", ""),
                "performance": row.get("性能指标", ""),
                "main_users": row.get("主要用户", ""),
                "notes": row.get("备注", "")
            }

            # 过滤空记录
            if system["system_name"]:
                systems.append(system)

        return {
            "type": "system_profile",
            "count": len(systems),
            "systems": systems
        }

    def _extract_feature_cases(self, data: List[Dict]) -> Dict[str, Any]:
        """从CSV数据提取功能案例"""
        cases = []

        for row in data:
            case = {
                "system_name": row.get("系统名称", ""),
                "module": row.get("功能模块", ""),
                "feature_name": row.get("功能点名称", row.get("功能点", "")),
                "description": row.get("业务描述", ""),
                "estimated_days": row.get("预估人天", 0),
                "complexity": row.get("复杂度", "中"),
                "tech_points": row.get("技术要点", ""),
                "dependencies": row.get("依赖系统", ""),
                "project_case": row.get("实施案例", ""),
                "create_date": row.get("创建日期", "")
            }

            # 过滤空记录
            if case["system_name"] and case["feature_name"]:
                cases.append(case)

        return {
            "type": "feature_case",
            "count": len(cases),
            "cases": cases
        }

    def _extract_from_docx(self, data: Dict) -> Dict[str, Any]:
        """从DOCX数据提取知识"""
        # TODO: 实现智能提取逻辑
        # 可以基于标题层级、关键词等提取结构化数据
        return {
            "type": "unstructured",
            "content": data
        }

    def _extract_from_xlsx(self, data: Dict) -> Dict[str, Any]:
        """从XLSX数据提取知识"""
        # 查找系统知识相关的Sheet
        for sheet_name, sheet_data in data.items():
            if len(sheet_data) > 0:
                first_row = sheet_data[0]

                # 判断类型
                if "系统名称" in first_row or "系统简称" in first_row:
                    # 转换为字典列表
                    headers = [str(cell) for cell in first_row]
                    rows = []
                    for row in sheet_data[1:]:
                        row_dict = {}
                        for i, cell in enumerate(row):
                            if i < len(headers):
                                row_dict[headers[i]] = str(cell) if cell is not None else ""
                        rows.append(row_dict)

                    return self._extract_system_profile(rows)

                elif "功能点名称" in first_row or "功能点" in first_row:
                    headers = [str(cell) for cell in first_row]
                    rows = []
                    for row in sheet_data[1:]:
                        row_dict = {}
                        for i, cell in enumerate(row):
                            if i < len(headers):
                                row_dict[headers[i]] = str(cell) if cell is not None else ""
                        rows.append(row_dict)

                    return self._extract_feature_cases(rows)

        return {}


# 全局解析器实例
_document_parser = None


def get_document_parser() -> DocumentParser:
    """获取文档解析器单例"""
    global _document_parser
    if _document_parser is None:
        _document_parser = DocumentParser()
    return _document_parser
