#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
元数据变更检测和冗余分析脚本
项目: SmartSG 服务治理平台
功能: 定时扫描元数据变更，使用Qwen3.5-35B-A3B大模型进行语义相似度分析
作者: AI Assistant
版本: 1.0
"""

import os
import sys
import yaml
import logging
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
import json
import pickle
import hashlib
from io import BytesIO

# 获取脚本所在目录的绝对路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 第三方依赖（按需检查，不在模块导入时退出）
try:
    import pymysql
except ImportError:
    pymysql = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    import numpy as np
except ImportError:
    np = None

try:
    from openpyxl import Workbook
except ImportError:
    Workbook = None


class _UnionFind:
    """并查集，用于将冗余对合并为组"""

    def __init__(self):
        self.parent = {}
        self.rank = {}

    def find(self, x):
        if x not in self.parent:
            self.parent[x] = x
            self.rank[x] = 0
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x, y):
        px, py = self.find(x), self.find(y)
        if px == py:
            return
        if self.rank[px] < self.rank[py]:
            px, py = py, px
        self.parent[py] = px
        if self.rank[px] == self.rank[py]:
            self.rank[px] += 1


class MetadataChangeInform:
    """元数据变更检测和冗余分析主类"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """初始化配置"""
        self.db_connection = None
        self.llm_client = None
        self.cache = {}
        # 先初始化logger再加载配置

        self.logger = self._setup_logging()
        # 确保配置文件路径是相对于脚本目录的
        if not os.path.isabs(config_path):
            config_path = os.path.join(SCRIPT_DIR, config_path)
        self.config = self._load_config(config_path)
    
    def _update_logger_config(self, config: Dict[str, Any]):
        """更新logger配置"""
        # 清除现有的处理器
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
            handler.close()
        
        log_config = config['logging']
        # 确保日志目录是相对于脚本目录的
        log_dir = config['output']['log_dir']
        if not os.path.isabs(log_dir):
            log_dir = os.path.join(SCRIPT_DIR, log_dir)
        os.makedirs(log_dir, exist_ok=True)
        
        self.logger.setLevel(getattr(logging, log_config['level']))
        
        # 文件处理器
        log_file = os.path.join(log_dir, 'metachange_inform.log')
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter(log_config['format']))
        self.logger.addHandler(file_handler)
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(log_config['format']))
        self.logger.addHandler(console_handler)
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            # 环境变量覆盖（便于在本机/测试环境运行，不修改目标环境 YAML）
            config = self._apply_env_overrides(config)

            # 更新logger配置
            self._update_logger_config(config)
            self.logger.info(f"成功加载配置文件: {config_path}")
            return config
        except Exception as e:
            self.logger.error(f"加载配置文件失败: {e}")
            raise
    
    def _setup_logging(self) -> logging.Logger:
        """设置日志"""
        # 在加载配置前使用默认日志设置
        logger = logging.getLogger('MetadataChangeInform')
        logger.setLevel(logging.INFO)

        # 文件处理器 - 使用脚本目录下的logs文件夹
        log_dir = os.path.join(SCRIPT_DIR, './logs')
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, 'metachange_inform.log')

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        return logger

    def _apply_env_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """使用环境变量覆盖配置（用于本机验证，不污染目标环境 YAML）。"""
        db = config.setdefault('database', {})
        llm = config.setdefault('llm', {})

        def _get(name: str) -> str | None:
            value = os.getenv(name)
            if value is None:
                return None
            value = str(value).strip()
            return value if value else None

        db_host = _get('METACHANGE_DB_HOST') or _get('DB_HOST')
        if db_host:
            db['host'] = db_host
        db_port = _get('METACHANGE_DB_PORT') or _get('DB_PORT')
        if db_port:
            db['port'] = int(db_port)
        db_name = _get('METACHANGE_DB_NAME') or _get('DB_NAME')
        if db_name:
            db['database'] = db_name
        db_user = _get('METACHANGE_DB_USER') or _get('DB_USER')
        if db_user:
            db['username'] = db_user
        db_password = _get('METACHANGE_DB_PASSWORD') or _get('DB_PASSWORD')
        if db_password is not None:
            db['password'] = db_password

        llm_base_url = _get('METACHANGE_LLM_BASE_URL') or _get('DASHSCOPE_API_BASE')
        if llm_base_url:
            llm['base_url'] = llm_base_url
        llm_model = _get('METACHANGE_LLM_MODEL') or _get('LLM_MODEL')
        if llm_model:
            llm['model_name'] = llm_model
        llm_key = _get('METACHANGE_LLM_API_KEY') or _get('DASHSCOPE_API_KEY')
        if llm_key is not None:
            llm['api_key'] = llm_key

        output_format = _get('METACHANGE_OUTPUT_FORMAT')
        if output_format:
            config.setdefault('output', {})['format'] = output_format

        return config
    
    def connect_database(self):
        """连接数据库"""
        if pymysql is None:
            raise RuntimeError("缺少必要依赖 PyMySQL，请安装后再执行数据库连接")
        db_config = self.config['database']
        try:
            self.db_connection = pymysql.connect(
                host=db_config['host'],
                port=db_config['port'],
                user=db_config['username'],
                password=db_config['password'],
                database=db_config['database'],
                charset=db_config['charset'],
                connect_timeout=db_config['connection_timeout'],
                read_timeout=db_config['read_timeout']
            )
            self.logger.info("数据库连接成功")
        except Exception as e:
            self.logger.error(f"数据库连接失败: {e}")
            raise
    
    def connect_llm(self):
        """连接大语言模型"""
        if OpenAI is None:
            raise RuntimeError("缺少必要依赖 openai，请安装后再执行大模型连接")
        llm_config = self.config['llm']
        try:
            # 对于不需要API密钥的本地LLM服务
            api_key = llm_config['api_key'] or ""
            
            self.llm_client = OpenAI(
                base_url=llm_config['base_url'],
                api_key=api_key
            )
            self.logger.info("大语言模型连接成功")
        except Exception as e:
            self.logger.error(f"大语言模型连接失败: {e}")
            raise
    
    def load_cache(self):
        """加载缓存"""
        if not self.config['scan']['enable_cache']:
            return
        
        cache_dir = self.config['output']['cache_dir']
        if not os.path.isabs(cache_dir):
            cache_dir = os.path.join(SCRIPT_DIR, cache_dir)
        cache_file = os.path.join(cache_dir, 'metadata_embeddings.pkl')
        
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'rb') as f:
                    self.cache = pickle.load(f)
                self.logger.info(f"加载缓存成功，包含 {len(self.cache)} 条记录")
            except Exception as e:
                self.logger.warning(f"加载缓存失败: {e}")
                self.cache = {}
        else:
            self.logger.info("缓存文件不存在，将创建新的缓存")
    
    def save_cache(self):
        """保存缓存"""
        if not self.config['scan']['enable_cache']:
            return
        
        cache_dir = self.config['output']['cache_dir']
        if not os.path.isabs(cache_dir):
            cache_dir = os.path.join(SCRIPT_DIR, cache_dir)
        cache_file = os.path.join(cache_dir, 'metadata_embeddings.pkl')
        
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(self.cache, f)
            self.logger.info(f"缓存保存成功，包含 {len(self.cache)} 条记录")
        except Exception as e:
            self.logger.error(f"缓存保存失败: {e}")
    
    def save_report(self, report_content: str):
        """保存报告到文件"""
        report_dir = self.config['output']['report_dir']
        if not os.path.isabs(report_dir):
            report_dir = os.path.join(SCRIPT_DIR, report_dir)
        os.makedirs(report_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{self.config['output']['filename_prefix']}_{timestamp}.md"
        filepath = os.path.join(report_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(report_content)
            self.logger.info(f"报告已保存到: {filepath}")
        except Exception as e:
            self.logger.error(f"保存报告失败: {e}")
            raise
    
    def get_recent_metadata_changes(self) -> List[Dict[str, Any]]:
        """获取最近的元数据变更"""
        lookback_hours = self.config['scan']['lookback_hours']
        table_names = self.config['table_names']
        use_time_filter = int(lookback_hours or 0) > 0
        params: List[Any] = []
        time_filter_sql = ""
        if use_time_filter:
            cutoff_time = datetime.now() - timedelta(hours=int(lookback_hours))
            cutoff_str = cutoff_time.strftime('%Y-%m-%d %H:%M:%S')
            time_filter_sql = " AND OPT_TIME >= %s"
            params.extend([cutoff_str, cutoff_str])

        # 只从变更表读取候选新增/变更元数据，不再把存量正式表混入变更集合
        query = f"""
        SELECT
            METADATA_ID,
            METADATA_NAME,
            CHINESE_NAME,
            CATEGORY_WORD_ID,
            TYPE,
            LENGTH,
            STATUS,
            OPT_USER,
            OPT_TIME,
            AUDIT_USER,
            AUDIT_DATE,
            REMARK,
            BUSS_DEFINE,
            BUSS_RULE,
            DATA_SOURCE,
            METADATA_ALIAS,
            VERSION_ID,
            DEFAULT_VALUE,
            BUZZ_CATEGORY,
            DATA_CATEGORY,
            PROCESS_ID
        FROM {table_names['audit']}
        WHERE 1=1 {time_filter_sql}
          AND STATUS IN ('1', '未审核', '审核中')
        ORDER BY OPT_TIME DESC
        """

        try:
            cursor_args = (pymysql.cursors.DictCursor,) if pymysql is not None else ()
            with self.db_connection.cursor(*cursor_args) as cursor:
                cursor.execute(query, tuple(params))
                results = cursor.fetchall()
                self.logger.info(f"找到 {len(results)} 条最近的元数据变更")
                return list(results)
        except Exception as e:
            self.logger.error(f"查询元数据变更失败: {e}")
            raise
    
    def get_all_current_metadata(self) -> List[Dict[str, Any]]:
        """获取所有当前有效的元数据"""
        table_names = self.config['table_names']
        
        # 根据实际表结构调整查询，注意METADATA表有DATA_FORMULA字段，而METADATA_AUDIT表没有
        query = f"""
        SELECT 
            METADATA_ID,
            METADATA_NAME,
            CHINESE_NAME,
            CATEGORY_WORD_ID,
            TYPE,
            LENGTH,
            STATUS,
            OPT_USER,
            OPT_TIME,
            AUDIT_USER,
            AUDIT_DATE,
            REMARK,
            BUSS_DEFINE,
            BUSS_RULE,
            DATA_SOURCE,
            METADATA_ALIAS,
            VERSION_ID,
            DEFAULT_VALUE,
            BUZZ_CATEGORY,
            DATA_CATEGORY,
            DATA_FORMULA,
            PROCESS_ID
        FROM {table_names['current']}
        WHERE STATUS = '正式'
        ORDER BY METADATA_ID
        """
        
        try:
            with self.db_connection.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(query)
                results = cursor.fetchall()
                self.logger.info(f"获取到 {len(results)} 条当前有效的元数据")
                return list(results)
        except Exception as e:
            self.logger.error(f"查询当前元数据失败: {e}")
            raise
    
    def detect_redundancy(self, all_changed_metas: List[Dict[str, Any]], all_current_metas: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """检测冗余元数据 - 优化版：以变更元数据为驱动"""
        threshold = self.config['scan']['similarity_threshold']
        self.logger.info(f"开始批量检测冗余，变更元数据 {len(all_changed_metas)} 条，存量元数据 {len(all_current_metas)} 条")
        
        results = []
        
        # 第一步：硬编码比较 - 以变更元数据为驱动
        self.logger.info("开始硬编码批量比较...")
        hard_results, unmatched_changed_metas = self._hard_code_driven_comparison(all_changed_metas, all_current_metas, threshold)
        results.extend(hard_results)
        self.logger.info(f"硬编码比较完成，发现 {len(hard_results)} 个匹配项，{len(unmatched_changed_metas)} 条变更元数据待LLM分析")
        
        # 第二步：LLM语义分析 - 一次性分析所有未匹配的变更元数据
        if unmatched_changed_metas:
            self.logger.info("开始LLM单次语义分析...")
            llm_results = self._llm_single_analysis(unmatched_changed_metas, all_current_metas, threshold)
            results.extend(llm_results)
            self.logger.info(f"LLM分析完成，发现 {len(llm_results)} 个语义相似项")
        else:
            self.logger.info("无需LLM分析，所有变更元数据均已匹配")
        
        self.logger.info(f"批量检测完成，总共发现 {len(results)} 个潜在冗余")
        return results, unmatched_changed_metas
    
    def _hard_code_driven_comparison(self, all_changed_metas: List[Dict[str, Any]], all_current_metas: List[Dict[str, Any]], threshold: float) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """硬编码驱动比较 - 以变更元数据为驱动，选择最佳匹配结果"""
        results = []
        unmatched_changed_metas = []  # 存储未匹配的变更元数据，供LLM分析

        for changed_meta in all_changed_metas:
            changed_chinese_name = (changed_meta.get('CHINESE_NAME') or '').lower()
            # 优先使用METADATA_NAME，如果为空则使用METADATA_ID作为英文名称
            changed_english_name = (changed_meta.get('METADATA_NAME') or changed_meta.get('METADATA_ID', '') or '').lower()

            best_result = None
            best_similarity_score = -1.0

            chinese_weight, id_weight, weight_reason_parts = self._calculate_name_weights(changed_meta, all_current_metas)

            # 遍历所有存量元数据，寻找匹配
            for current_meta in all_current_metas:
                # 跳过自身比较
                if current_meta['METADATA_ID'] == changed_meta['METADATA_ID']:
                    continue

                current_chinese_name = (current_meta.get('CHINESE_NAME') or '').lower()
                # 优先使用METADATA_NAME，如果为空则使用METADATA_ID作为英文名称
                current_english_name = (current_meta.get('METADATA_NAME') or current_meta.get('METADATA_ID', '') or '').lower()

                # 计算综合相似度（动态权重：中文名优先，短/高频中文名会降低中文权重）
                chinese_similarity = self._string_similarity(changed_chinese_name, current_chinese_name)
                english_similarity = self._string_similarity(changed_english_name, current_english_name)
                combined_similarity = chinese_similarity * chinese_weight + english_similarity * id_weight

                # 精确匹配（优先级最高）
                exact_match = (changed_chinese_name == current_chinese_name and changed_english_name == current_english_name)

                # 部分包含匹配（仅在中文名称有意义时使用）
                partial_match = False
                partial_match_score = 0.0
                if changed_chinese_name and current_chinese_name:
                    # 中文名称部分包含且长度合理（避免单字符匹配）
                    if (len(changed_chinese_name) > 2 and len(current_chinese_name) > 2 and
                        (changed_chinese_name in current_chinese_name or current_chinese_name in changed_chinese_name)):
                        partial_match = True
                        # 计算部分包含的相似度分数
                        if changed_chinese_name in current_chinese_name:
                            partial_match_score = len(changed_chinese_name) / len(current_chinese_name)
                        else:
                            partial_match_score = len(current_chinese_name) / len(changed_chinese_name)
                elif changed_english_name and current_english_name:
                    # 英文名称部分包含且长度合理
                    if (len(changed_english_name) > 3 and len(current_english_name) > 3 and
                        (changed_english_name in current_english_name or current_english_name in changed_english_name)):
                        partial_match = True
                        # 计算部分包含的相似度分数
                        if changed_english_name in current_english_name:
                            partial_match_score = len(changed_english_name) / len(current_english_name)
                        else:
                            partial_match_score = len(current_english_name) / len(changed_english_name)

                # 如果满足任一硬编码匹配条件
                if exact_match or partial_match or combined_similarity >= threshold:
                    # 使用连续的相似度值，避免离散化
                    if exact_match:
                        similarity_score = 1.0
                    elif partial_match:
                        # 部分包含匹配使用计算的相似度分数
                        similarity_score = max(combined_similarity, partial_match_score)
                    else:
                        similarity_score = combined_similarity

                    if similarity_score >= threshold:
                        reason_parts = []
                        if exact_match:
                            reason_parts.append("名称精确匹配")
                        if partial_match:
                            reason_parts.append("名称部分包含")
                        if combined_similarity >= threshold and not (exact_match or partial_match):
                            reason_parts.append(f"综合相似度高({combined_similarity:.2f})")
                        reason_parts.extend(weight_reason_parts)

                        reason = "; ".join(reason_parts)

                        result = {
                            'changed_metadata': changed_meta,
                            'existing_metadata': current_meta,
                            'similarity_score': similarity_score,
                            'redundancy_level': self._get_redundancy_level(similarity_score),
                            'reason': reason,
                            'detection_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }

                        should_replace_best = similarity_score > best_similarity_score
                        if not should_replace_best and best_result is not None and similarity_score == best_similarity_score:
                            best_existing_meta = best_result['existing_metadata']
                            current_id_similarity = self._string_similarity(
                                changed_meta.get('METADATA_ID', '') or '',
                                current_meta.get('METADATA_ID', '') or '',
                            )
                            best_id_similarity = self._string_similarity(
                                changed_meta.get('METADATA_ID', '') or '',
                                best_existing_meta.get('METADATA_ID', '') or '',
                            )
                            should_replace_best = current_id_similarity > best_id_similarity
                            if should_replace_best:
                                result['reason'] = f"{reason}; ID更接近" if reason else "ID更接近"

                        if should_replace_best:
                            best_similarity_score = similarity_score
                            best_result = result

            # 如果该变更元数据没有找到匹配，则添加到未匹配列表
            if best_result is None:
                unmatched_changed_metas.append(changed_meta)
            else:
                results.append(best_result)
                cache_key = self._get_cache_key(changed_meta['METADATA_ID'], best_result['existing_metadata']['METADATA_ID'])
                self.cache[cache_key] = best_result['similarity_score']

        return results, unmatched_changed_metas
    
    def _calculate_name_weights(self, changed_meta: Dict[str, Any], all_current_metas: List[Dict[str, Any]]) -> Tuple[float, float, List[str]]:
        """根据短中文名/高频中文名动态调整中文名与ID权重。"""
        changed_chinese_name = (changed_meta.get('CHINESE_NAME') or '').strip().lower()
        chinese_weight = 0.6
        id_weight = 0.4
        reason_parts: List[str] = []

        if changed_chinese_name:
            if len(changed_chinese_name) <= 4:
                chinese_weight -= 0.15
                id_weight += 0.15
                reason_parts.append('短中文名降权')

            frequency = sum(
                1
                for current_meta in all_current_metas
                if (current_meta.get('CHINESE_NAME') or '').strip().lower() == changed_chinese_name
            )
            if frequency >= 3:
                chinese_weight -= 0.15
                id_weight += 0.15
                reason_parts.append('高频中文名降权')

        total = chinese_weight + id_weight
        return chinese_weight / total, id_weight / total, reason_parts

    def _generate_candidates(self, changed_meta: Dict[str, Any], all_current_metas: List[Dict[str, Any]]) -> List[tuple]:
        """生成候选集 - 多维度智能筛选，动态候选集大小"""
        candidates = []
        changed_chinese_name = (changed_meta.get('CHINESE_NAME') or '').strip().lower()
        changed_english_name = (changed_meta.get('METADATA_NAME') or changed_meta.get('METADATA_ID', '') or '').strip().lower()
        changed_type = (changed_meta.get('TYPE') or '').strip().lower()
        changed_length = (changed_meta.get('LENGTH') or '').strip()
        
        # 计算变更元数据的特征
        is_short_name = len(changed_chinese_name) <= 5
        is_long_name = len(changed_chinese_name) > 10
        has_special_chars = any(char in changed_chinese_name for char in '[]{}()')
        
        for current_meta in all_current_metas:
            # 跳过自身比较
            if current_meta['METADATA_ID'] == changed_meta['METADATA_ID']:
                continue
            
            current_chinese_name = (current_meta.get('CHINESE_NAME') or '').strip().lower()
            current_english_name = (current_meta.get('METADATA_NAME') or current_meta.get('METADATA_ID', '') or '').strip().lower()
            current_type = (current_meta.get('TYPE') or '').strip().lower()
            current_length = (current_meta.get('LENGTH') or '').strip()
            
            # 基础相似度计算（使用统一的硬编码相似度方法）
            combined_similarity = self._calculate_hard_coded_similarity(changed_meta, current_meta, all_current_metas)
            
            # 候选集筛选使用固定阈值0.3，确保足够的候选范围
            # 后续会通过相似度>0.5进行二次筛选
            candidate_threshold = 0.3
            
            # 高置信度匹配（用于精确匹配判断）
            high_confidence_match = combined_similarity >= 0.95
            
            # 如果是高置信度匹配，确保包含在候选集中
            if high_confidence_match:
                candidates.append((current_meta, combined_similarity, True))  # True表示高置信度
            elif combined_similarity >= candidate_threshold:
                candidates.append((current_meta, combined_similarity, False))
        
        # 按相似度排序，高置信度优先
        candidates.sort(key=lambda x: (x[2], x[1]), reverse=True)
        return candidates
    
    def _check_high_confidence_match(self, changed_meta: Dict[str, Any], all_current_metas: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """高置信度匹配检查（相似度≥0.95）"""
        changed_chinese_name = (changed_meta.get('CHINESE_NAME') or '').strip().lower()
        changed_english_name = (changed_meta.get('METADATA_NAME') or changed_meta.get('METADATA_ID', '') or '').strip().lower()
        changed_type = (changed_meta.get('TYPE') or '').strip().lower()
        changed_length = (changed_meta.get('LENGTH') or '').strip()
        
        best_match = None
        best_similarity = 0.0
        
        for current_meta in all_current_metas:
            if current_meta['METADATA_ID'] == changed_meta['METADATA_ID']:
                continue  # 跳过自身
                
            # 使用统一的硬编码相似度计算方法
            combined_similarity = self._calculate_hard_coded_similarity(changed_meta, current_meta, all_current_metas)
            
            # 找到最高相似度的匹配
            if combined_similarity > best_similarity:
                best_similarity = combined_similarity
                best_match = current_meta
        
        # 如果最高相似度≥0.95，直接返回结果（跳过LLM）
        if best_similarity >= 0.95:
            return {
                'changed_metadata': changed_meta,
                'existing_metadata': best_match,
                'similarity_score': best_similarity,
                'redundancy_level': '高',
                'reason': f'高置信度匹配（综合相似度{best_similarity:.3f}≥0.95）',
                'detection_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        
        return None
    
    def _llm_candidate_analysis(self, changed_meta: Dict[str, Any], all_current_metas: List[Dict[str, Any]], threshold: float) -> List[Dict[str, Any]]:
        """LLM智能候选集分析 - 动态候选集大小，严格控制token数量"""
        results = []
        
        # 生成优化后的候选集
        candidate_tuples = self._generate_candidates(changed_meta, all_current_metas)
        
        # 双重筛选：先按相似度>0.5过滤，再限制数量上限
        # 确保候选集质量，避免低质量匹配
        high_quality_candidates = [
            candidate for candidate in candidate_tuples 
            if candidate[1] > 0.5  # 相似度必须大于0.5
        ]
        
        max_candidates = self.config['scan'].get('max_candidates_per_change', 50)  # 减少到50
        top_candidates = [candidate[0] for candidate in high_quality_candidates[:max_candidates]]
        
        # 如果没有候选，直接返回
        if not top_candidates:
            self.logger.info(f"  变更元数据 {changed_meta['METADATA_ID']} 无相关候选，跳过LLM分析")
            return results
        
        self.logger.info(f"  找到 {len(top_candidates)} 个相关候选（完全动态大小），进行LLM分析")
        
        # 构建优化的LLM分析提示词（强化JSON输出约束）
        changed_chinese_name = (changed_meta.get('CHINESE_NAME') or '')
        prompt = f"""
你是一个专业的元数据语义分析系统，严格按以下要求执行：

## 任务
比较变更元数据与候选存量元数据，找出最相似的一个候选。

## 变更元数据
- ID: {changed_meta['METADATA_ID']}
- 中文名称: {changed_chinese_name}

## 候选存量元数据（索引从0开始）
{chr(10).join([f'[{i}] ID: {current_meta["METADATA_ID"]}, 中文名称: {current_meta.get("CHINESE_NAME", "")}' for i, current_meta in enumerate(top_candidates)])}

## 输出要求
1. 只输出JSON格式结果，不要任何解释、推理或额外文本
2. 必须包含以下字段：
   - idx: 选择的候选索引（整数）
   - score: 相似度分数（0.0-1.0的浮点数）
   - reason: 简洁匹配理由（字符串）
   - selected_id: 选择的候选ID（字符串）
   - selected_chinese_name: 选择的候选中文名称（字符串）

## 评分标准
- 1.0 = 完全相同
- 0.9-0.99 = 基本一致
- 0.8-0.9 = 高度相似
- 0.6-0.7 = 中度相似
- 0.4-0.5 = 低度相似
- <0.4 = 不相似

## 示例输出（严格遵循此格式）
{{"idx": 1, "score": 0.85, "reason": "高度相似", "selected_id": "CstBscInfo", "selected_chinese_name": "客户基本信息"}}

## 重要提醒
- 不要输出任何解释、推理过程或额外文本
- 只输出JSON对象
- 如果无法确定结果，输出：{{"idx": -1, "score": 0.0, "reason": "无法确定", "selected_id": "", "selected_chinese_name": ""}}
"""
        
        try:
            # 调用LLM进行分析（使用更强的系统消息强制JSON输出）
            response = self.llm_client.chat.completions.create(
                model=self.config['llm']['model_name'],
                messages=[
                    {"role": "system", "content": "你是一个严格的JSON输出机器。只输出指定格式的JSON对象，不要任何解释、推理、自然语言或额外文本。重复：不要输出任何自然语言，只输出JSON。如果无法确定结果，请输出{\"idx\": -1, \"score\": 0.0, \"reason\": \"无法确定\"}"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,  # 严格限制响应长度
                temperature=self.config['llm']['temperature'],
                timeout=self.config['llm']['timeout']
            )
            
            response_content = response.choices[0].message.content.strip()
            self.logger.debug(f"  LLM原始响应: {response_content}")
            
            # 解析JSON结果
            import json
            import re
            current_idx = -1
            similarity_score = 0.0
            reason_detail = "LLM语义分析"
            result = {}  # 初始化result变量
            
            try:
                # 首先尝试提取JSON部分 - 使用更宽松的正则表达式
                # 匹配完整的JSON对象，包括嵌套的大括号
                json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_content)
                if json_match:
                    json_str = json_match.group()
                    result = json.loads(json_str)
                    current_idx = result.get('idx', -1)
                    similarity_score = result.get('score', 0.0)
                    reason_detail = result.get('reason', 'LLM语义分析')
                else:
                    # 如果没有找到JSON，尝试直接解析整个响应
                    result = json.loads(response_content)
                    current_idx = result.get('idx', -1)
                    similarity_score = result.get('score', 0.0)
                    reason_detail = result.get('reason', 'LLM语义分析')
                    # 如果返回了selected_id和selected_chinese_name，则使用它们
                    if 'selected_id' in result and 'selected_chinese_name' in result:
                        selected_id = result['selected_id']
                        selected_chinese_name = result['selected_chinese_name']
                    
            except Exception as parse_error:
                self.logger.warning(f"  LLM响应解析失败: {parse_error}, 响应内容: {response_content[:100]}...")
                # 专门处理Qwen模型的思维链输出
                try:
                    # 从自然语言响应中提取最相似的候选索引
                    # 寻找类似 "最相似的是候选[3]" 或 "索引为2" 的模式
                    idx_patterns = [
                        r'最相似.*?候选\[(\d+)\]',
                        r'最相似.*?\[(\d+)\]',
                        r'索引.*?(\d+)',
                        r'第(\d+)个',
                        r'候选(\d+)',
                        r'\[(\d+)\]',
                        # 新增模式：直接数字匹配
                        r'(?:选择|选中|匹配|对应).*?(\d+)',
                        r'(\d+).*?(?:号候选|号选项)'
                    ]
                    
                    current_idx = -1
                    for pattern in idx_patterns:
                        idx_match = re.search(pattern, response_content)
                        if idx_match:
                            current_idx = int(idx_match.group(1))
                            break
                    
                    # 提取相似度分数
                    score_patterns = [
                        r'(?:相似度|分数|得分|score).*?([0-1]\.\d{1,3})',
                        r'([0-1]\.\d{1,3}).*?(?:相似|分数|得分)',
                        r'([0-1]\.[0-9]+)',
                        # 新增：匹配小数点后一位或两位的分数
                        r'(?:高度相似|很相似).*?([0-9]\.\d)',
                        r'(?:中度相似|有些相似).*?([0-6]\.\d)',
                        r'(?:低度相似|不太相似).*?([0-4]\.\d)'
                    ]
                    
                    similarity_score = 0.0
                    for pattern in score_patterns:
                        score_match = re.search(pattern, response_content)
                        if score_match:
                            similarity_score = float(score_match.group(1))
                            break
                    
                    # 提取理由
                    if "高度相似" in response_content or "很相似" in response_content:
                        reason_detail = "高度相似"
                        # 不再设置固定相似度值，保持原有的相似度计算
                    elif "中度相似" in response_content or "有些相似" in response_content:
                        reason_detail = "中度相似"
                        # 不再设置固定相似度值，保持原有的相似度计算
                    elif "低度相似" in response_content or "不太相似" in response_content:
                        reason_detail = "低度相似"
                        # 不再设置固定相似度值，保持原有的相似度计算
                    else:
                        # 根据相似度分数自动生成理由
                        if similarity_score >= 0.8:
                            reason_detail = "高度相似"
                        elif similarity_score >= 0.6:
                            reason_detail = "中度相似"
                        elif similarity_score >= 0.4:
                            reason_detail = "低度相似"
                        else:
                            reason_detail = "语义相关"
                    
                # 如果找到了有效索引但相似度为0，根据业务逻辑给出更合理的默认值
                    if current_idx >= 0 and similarity_score == 0.0:
                        # 验证提取的索引是否在有效范围内
                        if current_idx >= len(top_candidates):
                            self.logger.warning(f"  提取的索引 {current_idx} 超出候选集范围 {len(top_candidates)}，使用硬编码最高相似度")
                            current_idx = -1
                        else:
                            # 验证该候选是否真的与变更元数据相关
                            extracted_candidate = top_candidates[current_idx]
                            extracted_chinese_name = (extracted_candidate.get('CHINESE_NAME') or '').lower()
                            changed_chinese_name = (changed_meta.get('CHINESE_NAME') or '').lower()
                            extracted_similarity = self._string_similarity(changed_chinese_name, extracted_chinese_name)
                            
                            # 如果提取的候选与变更元数据的硬编码相似度很低，说明提取可能错误
                            if extracted_similarity < 0.2:
                                self.logger.warning(f"  提取的候选相似度过低 ({extracted_similarity:.3f})，可能提取错误，使用硬编码最高相似度")
                                current_idx = -1
                            else:
                                # 根据提取的候选给出更合理的默认相似度
                                if any(keyword in response_content for keyword in ["高度", "很相似", "基本一致"]):
                                    similarity_score = max(0.85, extracted_similarity)
                                elif any(keyword in response_content for keyword in ["中度", "有些", "相关"]):
                                    similarity_score = max(0.65, extracted_similarity)
                                elif any(keyword in response_content for keyword in ["低度", "不太", "弱"]):
                                    similarity_score = max(0.45, extracted_similarity)
                                else:
                                    similarity_score = max(0.7, extracted_similarity)  # 默认中等相似度但不低于硬编码相似度
                    
                    # 如果仍然没有有效索引，使用硬编码候选集中的最高相似度结果
                    if current_idx < 0 and candidate_tuples:
                        best_candidate = candidate_tuples[0][0]
                        best_similarity = candidate_tuples[0][1]
                        current_idx = top_candidates.index(best_candidate) if best_candidate in top_candidates else 0
                        similarity_score = best_similarity
                        reason_detail = f"硬编码回退: 最高相似度({best_similarity:.3f})"
                    
                    # 在自然语言解析的情况下，不强制设置selected_id，保持结果真实性
                    # 只有JSON解析成功时才设置selected_id
                        
                except Exception as extract_error:
                    self.logger.warning(f"  自然语言解析也失败: {extract_error}")
            
            # 验证结果有效性
            if (0 <= current_idx < len(top_candidates)):
                # 确保相似度在0-1范围内
                similarity_score = max(0.0, min(1.0, float(similarity_score)))
                
                # 验证selected_id是否与候选列表中的实际ID一致
                selected_candidate = top_candidates[current_idx]
                is_valid_llm_result = False
                if result and 'selected_id' in result and 'selected_chinese_name' in result:
                    # 验证返回的ID和中文名称是否与候选列表中的一致
                    if (result['selected_id'] != selected_candidate['METADATA_ID'] or 
                        result['selected_chinese_name'] != selected_candidate['CHINESE_NAME']):
                        self.logger.warning(f"  LLM返回的候选信息不一致 - 返回: {result['selected_id']}({result['selected_chinese_name']}), 实际: {selected_candidate['METADATA_ID']}({selected_candidate['CHINESE_NAME']})")
                        # 标记为硬编码回退，因为LLM结果不可信
                        reason_detail = f"硬编码回退: LLM结果不一致({reason_detail})"
                    else:
                        self.logger.info(f"  LLM验证通过: 返回的候选信息与候选列表一致")
                        is_valid_llm_result = True
                elif current_idx >= 0 and similarity_score > 0:
                    # 成功从LLM自然语言响应中提取有效信息
                    self.logger.info(f"  LLM自然语言解析成功: 提取索引={current_idx}, 相似度={similarity_score:.3f}")
                    is_valid_llm_result = True
                else:
                    # 没有有效的LLM结果字段，标记为硬编码回退
                    self.logger.warning("  LLM返回缺少必要字段，使用硬编码结果")
                    reason_detail = f"硬编码回退: LLM响应不完整({reason_detail})"
                
                # 额外验证：确保LLM返回的相似度不低于硬编码基础相似度
                hard_coded_similarity = self._calculate_hard_coded_similarity(changed_meta, selected_candidate)
                if similarity_score < hard_coded_similarity * 0.8:  # LLM相似度不应比硬编码低太多
                    self.logger.warning(f"  LLM相似度({similarity_score:.3f})显著低于硬编码相似度({hard_coded_similarity:.3f})，使用硬编码值")
                    similarity_score = hard_coded_similarity
                
                # 打印匹配到的最相似元数据
                self.logger.info(f"  LLM匹配到最相似元数据: ID={selected_candidate['METADATA_ID']}, 中文名称={selected_candidate.get('CHINESE_NAME', '')}, 相似度={similarity_score:.3f}")
                
                # 只有有效的LLM结果才标记为LLM分析
                detection_method = "LLM候选集分析" if is_valid_llm_result else "硬编码回退"
                # 根据项目规范，冗余理由应只包含具体描述，不包含检测方法前缀
                final_reason = reason_detail if is_valid_llm_result else f"{detection_method}: {reason_detail}"
                result_item = {
                    'changed_metadata': changed_meta,
                    'existing_metadata': selected_candidate,
                    'similarity_score': similarity_score,
                    'redundancy_level': self._get_redundancy_level(similarity_score),
                    'reason': final_reason,
                    'detection_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                # 只有相似度达到阈值才添加到最终结果
                if similarity_score >= threshold:
                    results.append(result_item)
                    cache_key = self._get_cache_key(changed_meta['METADATA_ID'], selected_candidate['METADATA_ID'])
                    self.cache[cache_key] = similarity_score
                else:
                    self.logger.debug(f"  LLM分析结果相似度({similarity_score:.3f})低于阈值({threshold})，不添加到结果")
            else:
                self.logger.warning(f"  LLM返回的索引无效: {current_idx}, 候选集大小: {len(top_candidates)}")
                
            self.logger.info(f"  LLM候选集分析完成，相似度: {similarity_score:.3f}")
                
        except Exception as e:
            self.logger.error(f"  LLM候选集分析失败: {e}")
            # 如果分析失败，使用最高相似度的候选结果
            if candidate_tuples:
                best_candidate = candidate_tuples[0][0]
                best_similarity = candidate_tuples[0][1]
                if best_similarity >= threshold:
                    result_item = {
                        'changed_metadata': changed_meta,
                        'existing_metadata': best_candidate,
                        'similarity_score': best_similarity,
                        'redundancy_level': self._get_redundancy_level(best_similarity),
                        'reason': f"硬编码回退: 最高相似度({best_similarity:.3f})",
                        'detection_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    results.append(result_item)
                    cache_key = self._get_cache_key(changed_meta['METADATA_ID'], best_candidate['METADATA_ID'])
                    self.cache[cache_key] = best_similarity
        
        return results

    def _llm_single_analysis(self, unmatched_changed_metas: List[Dict[str, Any]], all_current_metas: List[Dict[str, Any]], threshold: float) -> List[Dict[str, Any]]:
        """LLM分析 - 直接使用智能候选集筛选，避免无效的完整批次尝试"""
        results = []
        
        if not unmatched_changed_metas:
            return results  # 如果没有未匹配的变更元数据，直接返回
        
        # 直接启动智能候选集分析模式（避免对大量存量数据进行无效的完整批次分析）
        self.logger.info(f"启动智能候选集分析模式，处理 {len(unmatched_changed_metas)} 条变更元数据")
        
        for changed_meta in unmatched_changed_metas:
            # 先检查高置信度匹配（相似度≥0.95）
            high_confidence_match = self._check_high_confidence_match(changed_meta, all_current_metas)
            if high_confidence_match:
                results.append(high_confidence_match)
                continue
            
            self.logger.info(f"智能候选集分析变更元数据: {changed_meta['METADATA_ID']}")
            llm_result = self._llm_candidate_analysis(changed_meta, all_current_metas, threshold)
            results.extend(llm_result)
        
        return results

    def _estimate_tokens_for_batch(self, changed_metas: List[Dict[str, Any]], current_metas: List[Dict[str, Any]]) -> int:
        """估算一批元数据的token数量（只包含元数据ID和中文名称）"""
        # 构建变更元数据列表信息（只包含元数据ID和中文名称）
        changed_metas_info = []
        for i, changed_meta in enumerate(changed_metas):
            chinese_name = (changed_meta.get('CHINESE_NAME') or '').lower()
            info = f"{i+1}. ID: {changed_meta['METADATA_ID']}; 中文名称: {chinese_name}"
            changed_metas_info.append(info)
        
        # 构建存量元数据列表信息（只包含元数据ID和中文名称）
        current_metas_info = []
        for j, current_meta in enumerate(current_metas):
            chinese_name = (current_meta.get('CHINESE_NAME') or '').lower()
            info = f"{j+1}. ID: {current_meta['METADATA_ID']}; 中文名称: {chinese_name}"
            current_metas_info.append(info)
        
        # 构建完整的提示词
        prompt = f"""
请分析以下变更元数据与存量元数据的语义相似性：

变更元数据列表：
{chr(10).join(changed_metas_info)}

存量元数据列表：
{chr(10).join(current_metas_info)}

请分析每条变更元数据与存量元数据中最相似的一项，返回JSON格式结果：
[
  {{
    "changed_index": 变更元数据在列表中的索引(从0开始),
    "matched_current_index": 最相似的存量元数据索引(从0开始),
    "similarity_score": 0-1之间的相似度分数,
    "reason": 简短的理由说明
  }}
]

评分标准：
- 1.0: 完全相同或语义等价
- 0.8-0.9: 高度相似，可能为重复定义
- 0.6-0.7: 中度相似，需要人工确认
- 0.4-0.5: 低度相似，可能是相关概念
- <0.4: 不相似
        """
        
        # 简单的token估算：每个字符约1.3个token（中文字符更多）
        # 这是一个粗略估算，实际token数量可能有所不同
        char_count = len(prompt)
        estimated_tokens = int(char_count * 1.3)
        return estimated_tokens
    
    def _get_cache_key(self, changed_id: str, existing_id: str) -> str:
        """生成缓存键"""
        return hashlib.md5(f"{changed_id}-{existing_id}".encode()).hexdigest()
    
    def _get_redundancy_level(self, score: float) -> str:
        """根据相似度分数获取冗余级别"""
        if score >= 0.8:
            return "高"
        elif score >= 0.6:
            return "中"
        elif score >= 0.4:
            return "低"
        else:
            return "无"
    
    def _get_redundancy_reason(self, score: float, level: str, reasons: List[str]) -> str:
        """生成冗余理由"""
        level_desc = "高冗余" if level == "高" else "中冗余" if level == "中" else "低冗余" if level == "低" else "无冗余"
        return f"相似度{score:.2f}，{level_desc}。原因: {'; '.join(reasons)}"
    
    def _calculate_hard_coded_similarity(self, changed_meta: Dict[str, Any], current_meta: Dict[str, Any], all_current_metas: Optional[List[Dict[str, Any]]] = None) -> float:
        """计算两个元数据之间的硬编码相似度"""
        if current_meta['METADATA_ID'] == changed_meta['METADATA_ID']:
            return 1.0

        changed_chinese_name = (changed_meta.get('CHINESE_NAME') or '').lower()
        changed_english_name = (changed_meta.get('METADATA_NAME') or changed_meta.get('METADATA_ID', '') or '').lower()

        current_chinese_name = (current_meta.get('CHINESE_NAME') or '').lower()
        current_english_name = (current_meta.get('METADATA_NAME') or current_meta.get('METADATA_ID', '') or '').lower()

        chinese_weight, id_weight, _ = self._calculate_name_weights(changed_meta, all_current_metas or [current_meta])
        chinese_similarity = self._string_similarity(changed_chinese_name, current_chinese_name)
        english_similarity = self._string_similarity(changed_english_name, current_english_name)
        return chinese_similarity * chinese_weight + english_similarity * id_weight
    
    def _string_similarity(self, str1: str, str2: str) -> float:
        """计算字符串相似度"""
        if not str1 or not str2:
            return 0.0
        from difflib import SequenceMatcher
        return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()
    
    def _build_report_rows(self, redundancy_results: List[Dict[str, Any]], all_changed_metas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """构建结构化报告行，供Excel/API复用"""
        report_entries = {}

        for result in redundancy_results:
            changed_id = result['changed_metadata']['METADATA_ID']
            if (
                changed_id not in report_entries
                or result['similarity_score'] > report_entries[changed_id].get('similarity_score', 0)
            ):
                report_entries[changed_id] = result

        for meta in all_changed_metas:
            changed_id = meta['METADATA_ID']
            if changed_id not in report_entries:
                report_entries[changed_id] = {
                    'changed_metadata': meta,
                    'non_redundant': True,
                }

        ordered_items = sorted(report_entries.values(), key=lambda x: x['changed_metadata']['METADATA_ID'])
        rows: List[Dict[str, Any]] = []
        for item in ordered_items:
            changed_meta = item['changed_metadata']
            row = {
                'metadata_id': changed_meta.get('METADATA_ID') or '',
                'chinese_name': changed_meta.get('CHINESE_NAME') or '',
                'data_type': f"{changed_meta.get('TYPE') or ''}({changed_meta.get('LENGTH') or ''})",
                'opt_time': changed_meta.get('OPT_TIME') or '',
                'opt_user': changed_meta.get('OPT_USER') or '',
                'redundancy_status': '无冗余',
                'similarity_score': '',
                'matched_metadata_id': '',
                'matched_chinese_name': '',
            }
            if not item.get('non_redundant'):
                existing_meta = item['existing_metadata']
                row.update(
                    {
                        'redundancy_status': '有冗余',
                        'similarity_score': f"{item['similarity_score']:.3f}",
                        'matched_metadata_id': existing_meta.get('METADATA_ID') or '',
                        'matched_chinese_name': existing_meta.get('CHINESE_NAME') or '',
                    }
                )
            rows.append(row)
        return rows

    def generate_report(self, redundancy_results: List[Dict[str, Any]], all_changed_metas: List[Dict[str, Any]]) -> str:
        """生成分析报告"""
        
        # 统计信息
        total_changed_count = len(all_changed_metas)
        redundant_count = len(redundancy_results)
        non_redundant_count = total_changed_count - redundant_count
        
        high_redundancy = sum(1 for r in redundancy_results if r['redundancy_level'] == '高')
        medium_redundancy = sum(1 for r in redundancy_results if r['redundancy_level'] == '中')
        low_redundancy = sum(1 for r in redundancy_results if r['redundancy_level'] == '低')
        
        hard_coded_count = sum(1 for r in redundancy_results if '硬编码检测' in r['reason'])
        llm_analyzed_count = sum(1 for r in redundancy_results if 'LLM' in r['reason'])
        
        report = "# 元数据冗余分析报告\n\n"
        report += "## 扫描概要\n\n"
        report += f"- **扫描时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += f"- **相似度阈值**: {self.config['scan']['similarity_threshold']}\n"
        report += f"- **变更元数据总数**: {total_changed_count} 项\n"
        report += f"- **发现潜在冗余**: {redundant_count} 项\n"
        report += f"- **无冗余元数据**: {non_redundant_count} 项\n\n"
        
        report += "## 详细结果\n\n"
        
        # 为每个变更元数据创建唯一记录，避免重复
        report_entries = {}
        
        # 首先处理冗余检测结果，确保每个变更元数据只保留一个结果
        for result in redundancy_results:
            changed_id = result['changed_metadata']['METADATA_ID']
            # 如果还没有这个变更元数据的记录，或者新结果的相似度更高，则更新
            if (changed_id not in report_entries or 
                result['similarity_score'] > report_entries[changed_id].get('similarity_score', 0)):
                report_entries[changed_id] = result
        
        # 然后添加所有变更元数据，包括无冗余的
        for meta in all_changed_metas:
            changed_id = meta['METADATA_ID']
            if changed_id not in report_entries:
                report_entries[changed_id] = {
                    'changed_metadata': meta,
                    'non_redundant': True
                }
        
        # 创建表格
        report += "| 序号 | 元数据ID | 中文名称 | 数据类型 | 操作时间 | 操作用户 | 冗余状态 | 相似度 | 匹配元数据ID | 匹配中文名 |\n"
        report += "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
        report_rows = self._build_report_rows(redundancy_results, all_changed_metas)

        for i, row in enumerate(report_rows, 1):
            report += (
                f"| {i} | {row['metadata_id']} | {row['chinese_name']} | {row['data_type']} | "
                f"{row['opt_time']} | {row['opt_user']} | {row['redundancy_status']} | {row['similarity_score'] or '-'} | "
                f"{row['matched_metadata_id'] or '-'} | {row['matched_chinese_name'] or '-'} |\n"
            )

        report += "\n\n"

        return report
    
    def _build_excel_workbook(self, report_rows: List[Dict[str, Any]]) -> Workbook:
        """构建Excel工作簿。"""
        if Workbook is None:
            raise RuntimeError("缺少必要依赖 openpyxl，请安装后再执行 Excel 导出")
        wb = Workbook()
        ws = wb.active
        ws.title = '元数据冗余分析结果'
        ws.append(['元数据ID', '中文名称', '数据类型', '操作时间', '操作用户', '冗余状态', '相似度', '匹配元数据ID', '匹配中文名'])
        for row in report_rows:
            ws.append([
                row.get('metadata_id') or '',
                row.get('chinese_name') or '',
                row.get('data_type') or '',
                row.get('opt_time') or '',
                row.get('opt_user') or '',
                row.get('redundancy_status') or '',
                row.get('similarity_score') or '',
                row.get('matched_metadata_id') or '',
                row.get('matched_chinese_name') or '',
            ])
        return wb

    def save_report(self, report_content: str, report_rows: Optional[List[Dict[str, Any]]] = None):
        """保存报告到文件。支持 markdown / excel。"""
        report_dir = self.config['output']['report_dir']
        if not os.path.isabs(report_dir):
            report_dir = os.path.join(SCRIPT_DIR, report_dir)
        os.makedirs(report_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename_prefix = self.config['output']['filename_prefix']
        output_format = str(self.config['output'].get('format') or 'markdown').strip().lower()

        if output_format == 'excel':
            filepath = os.path.join(report_dir, f"{filename_prefix}_{timestamp}.xlsx")
            wb = self._build_excel_workbook(report_rows or [])
            wb.save(filepath)
            self.logger.info(f"报告已保存到: {filepath}")
            return filepath

        filepath = os.path.join(report_dir, f"{filename_prefix}_{timestamp}.md")
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(report_content)
            self.logger.info(f"报告已保存到: {filepath}")
            return filepath
        except Exception as e:
            self.logger.error(f"保存报告失败: {e}")
            raise

    def should_run_now(self, run_now: bool = False) -> bool:
        """判断是否应该立即运行（基于计划时间或run_now参数）"""
        if run_now:
            self.logger.info("--now 参数被设置，立即执行任务")
            return True
        
        # 解析计划时间 (cron格式: "分 时 日 月 周")
        schedule = self.config['scan']['schedule']
        parts = schedule.split()
        
        if len(parts) != 5:
            self.logger.warning(f"计划时间格式错误: {schedule}，将立即执行")
            return True
        
        # 获取当前时间
        now = datetime.now()
        minute, hour, day, month, weekday = parts
        
        # 检查当前时间是否匹配计划时间
        # cron格式: "分钟 小时 日 月 星期几"
        # 例如: "0 23 * * *" 表示每天23:00执行
        
        # 简单匹配小时，'*' 表示任意值
        current_hour = now.hour
        scheduled_hour_is_match = (hour == '*' or str(current_hour) == hour)
        
        # 检查小时
        current_hour = now.hour
        scheduled_hour_is_match = (hour == '*' or str(current_hour) == hour)
        
        # 检查分钟
        current_minute = now.minute
        scheduled_minute_is_match = (minute == '*' or str(current_minute) == minute)
        
        # 只有当小时和分钟都匹配时才执行
        if scheduled_hour_is_match and scheduled_minute_is_match:
            self.logger.info(f"当前时间 {current_hour}:{current_minute:02d} 与计划时间 {hour}:{minute} 模式匹配，执行任务")
            return True
        
        self.logger.info(f"当前时间 {current_hour}:{now.minute:02d} 与计划时间 {hour}:{minute} 不匹配，跳过执行")
        return False
    
    # ── 存量冗余检测 ─────────────────────────────────────────────

    def _generate_embeddings_batch(self, texts: List[str], batch_size: int = 25) -> List[List[float]]:
        """批量生成 embedding 向量（使用已初始化的 OpenAI 客户端）"""
        if not self.llm_client:
            raise RuntimeError("LLM/Embedding 客户端未初始化")

        embedding_model = self.config.get('embedding', {}).get('model_name', 'text-embedding-v2')
        all_embeddings: List[List[float]] = []
        total = len(texts)

        for i in range(0, total, batch_size):
            batch = texts[i : i + batch_size]
            batch_no = i // batch_size + 1
            try:
                response = self.llm_client.embeddings.create(
                    model=embedding_model,
                    input=batch,
                )
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)
                self.logger.info(f"Embedding 进度: {len(all_embeddings)}/{total} (批次 {batch_no})")
            except Exception as e:
                self.logger.error(f"Embedding 批次 {batch_no} 失败: {e}")
                raise

        return all_embeddings

    def _llm_confirm_redundancy_groups(
        self,
        all_metas: List[Dict[str, Any]],
        groups: Dict[int, List[int]],
        embeddings_norm,
        confirm_threshold: float = 0.95,
        batch_size: int = 10,
    ) -> set:
        """LLM 确认边界冗余组（组内最低成对相似度 < confirm_threshold 的组）"""
        confirmed_roots: set = set()
        borderline_groups: Dict[int, List[int]] = {}

        for root, indices in groups.items():
            min_sim = 1.0
            for ii in range(len(indices)):
                for jj in range(ii + 1, len(indices)):
                    sim = float(embeddings_norm[indices[ii]] @ embeddings_norm[indices[jj]])
                    min_sim = min(min_sim, sim)

            if min_sim >= confirm_threshold:
                confirmed_roots.add(root)
            else:
                borderline_groups[root] = indices

        if not borderline_groups:
            self.logger.info("所有候选组均为高置信度，无需 LLM 确认")
            return confirmed_roots

        self.logger.info(f"{len(borderline_groups)} 个边界组需要 LLM 确认")

        if not self.llm_client:
            self.logger.warning("LLM 客户端不可用，保留所有边界组")
            return confirmed_roots | set(borderline_groups.keys())

        borderline_roots = list(borderline_groups.keys())
        for batch_start in range(0, len(borderline_roots), batch_size):
            batch_roots = borderline_roots[batch_start : batch_start + batch_size]
            prompt_parts = []

            for i, root in enumerate(batch_roots):
                indices = borderline_groups[root]
                items_desc = []
                for idx in indices:
                    m = all_metas[idx]
                    items_desc.append(
                        f"  - {m.get('METADATA_ID', '')}: {m.get('CHINESE_NAME', '')} ({m.get('METADATA_NAME', '')})"
                    )
                prompt_parts.append(f"组{i + 1}:\n" + "\n".join(items_desc))

            prompt = (
                "你是元数据冗余分析专家。以下是几组元数据，判断每组中的元数据是否表示完全相同或高度相似的含义（语义冗余）。\n"
                "冗余的定义：表示同一个业务概念的不同命名，例如\"联系电话\"和\"手机号码\"是冗余的，但\"客户姓名\"和\"客户年龄\"不是冗余的。\n\n"
                + "\n".join(prompt_parts)
                + "\n\n请只输出 JSON 数组: [{\"group\": 1, \"redundant\": true}, ...]"
            )

            try:
                response = self.llm_client.chat.completions.create(
                    model=self.config['llm']['model_name'],
                    messages=[
                        {"role": "system", "content": "你是严格的 JSON 输出机器，只输出 JSON 数组。"},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=500,
                    temperature=0.1,
                    timeout=self.config['llm']['timeout'],
                )

                content = response.choices[0].message.content.strip()
                import re as _re
                json_match = _re.search(r'\[.*\]', content, _re.DOTALL)
                if json_match:
                    results = json.loads(json_match.group())
                    for item in results:
                        group_idx = item.get("group", 0) - 1
                        if 0 <= group_idx < len(batch_roots) and item.get("redundant", False):
                            confirmed_roots.add(batch_roots[group_idx])
            except Exception as e:
                self.logger.warning(f"LLM 批量确认失败，保留所有边界组: {e}")
                confirmed_roots.update(batch_roots)

        return confirmed_roots

    def _get_stock_metadata_from_meta_data_pre(self) -> List[Dict[str, Any]]:
        """从 meta_data_pre 表加载存量元数据（正式使用的存量元数据表）"""
        query = """
        SELECT
            METADATA_ID,
            ATTR_NAME AS CHINESE_NAME,
            DATA_TYPE AS TYPE,
            DATA_LENGTH AS LENGTH,
            OPT_TIME
        FROM meta_data_pre
        WHERE METADATA_STATUS = '0'
        ORDER BY METADATA_ID
        """
        try:
            with self.db_connection.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(query)
                results = cursor.fetchall()
                self.logger.info(f"从 meta_data_pre 获取到 {len(results)} 条存量元数据")
                return list(results)
        except Exception as e:
            self.logger.error(f"查询 meta_data_pre 存量元数据失败: {e}")
            raise

    def get_new_metadata_candidates(self) -> List[Dict[str, Any]]:
        """获取新增元数据候选（在 metadata/metadata_audit 中但不在 meta_data_pre 中）"""
        table_names = self.config['table_names']

        query = f"""
        SELECT METADATA_ID, METADATA_NAME, CHINESE_NAME, CATEGORY_WORD_ID,
               TYPE, LENGTH, STATUS, OPT_USER, OPT_TIME
        FROM {table_names['current']}
        WHERE STATUS = '正式'
          AND NOT EXISTS (
            SELECT 1 FROM meta_data_pre p WHERE p.METADATA_ID = {table_names['current']}.METADATA_ID
          )
        """

        try:
            with self.db_connection.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(query)
                results = list(cursor.fetchall())

                # Also check audit table for IDs not found in metadata
                found_ids = [r['METADATA_ID'] for r in results]
                if found_ids:
                    placeholders = ','.join(['%s'] * len(found_ids))
                    audit_query = f"""
                    SELECT METADATA_ID, METADATA_NAME, CHINESE_NAME, CATEGORY_WORD_ID,
                           TYPE, LENGTH, STATUS, OPT_USER, OPT_TIME
                    FROM {table_names['audit']}
                    WHERE METADATA_ID NOT IN ({placeholders})
                      AND NOT EXISTS (
                        SELECT 1 FROM meta_data_pre p WHERE p.METADATA_ID = {table_names['audit']}.METADATA_ID
                      )
                    """
                    cursor.execute(audit_query, tuple(found_ids))
                else:
                    audit_query = f"""
                    SELECT METADATA_ID, METADATA_NAME, CHINESE_NAME, CATEGORY_WORD_ID,
                           TYPE, LENGTH, STATUS, OPT_USER, OPT_TIME
                    FROM {table_names['audit']}
                    WHERE NOT EXISTS (
                        SELECT 1 FROM meta_data_pre p WHERE p.METADATA_ID = {table_names['audit']}.METADATA_ID
                    )
                    """
                    cursor.execute(audit_query)
                results.extend(cursor.fetchall())

                self.logger.info(f"获取到 {len(results)} 条新增元数据候选（不在 meta_data_pre 中）")
                return results
        except Exception as e:
            self.logger.error(f"查询新增元数据候选失败: {e}")
            raise

    def get_new_vs_stock_report_rows(self) -> List[Dict[str, Any]]:
        """新增元数据与存量(meta_data_pre)冗余对比。
        仅使用硬编码字符串相似度，跳过 LLM 以提升性能。
        需要 db_connection 已连接。
        """
        self.logger.info("开始新增 vs 存量冗余分析（仅硬编码比较）...")

        new_candidates = self.get_new_metadata_candidates()
        if not new_candidates:
            self.logger.info("未发现新增元数据候选")
            return []

        self.logger.info(f"发现 {len(new_candidates)} 条新增元数据候选，开始与存量对比")

        stock_metas = self._get_stock_metadata_from_meta_data_pre()
        threshold = self.config['scan']['similarity_threshold']

        # 直接使用硬编码比较，跳过耗时的 LLM 分析
        hard_results, _ = self._hard_code_driven_comparison(new_candidates, stock_metas, threshold)
        report_rows = self._build_report_rows(hard_results, new_candidates)

        self.logger.info(f"新增 vs 存量分析完成，{len(report_rows)} 条报告行（硬编码匹配: {len(hard_results)}）")
        return report_rows

    def detect_existing_redundancy(self) -> List[Dict[str, Any]]:
        """
        检测存量元数据中的冗余组。
        使用 meta_data_pre 正式存量表进行检测。
        第一层：字符倒排索引 + 硬编码字符串相似度两两比较；
        第二层：边界组（组内最低相似度 < 0.95）送 LLM 确认。
        返回 [{group, metadata_id, chinese_name, data_type, opt_time, opt_user}, ...]
        """
        self.logger.info("开始检测存量元数据冗余（硬编码 + LLM 两层匹配）...")

        # 1. 从 meta_data_pre 表加载所有存量元数据
        if not self.db_connection:
            self.connect_database()
        try:
            all_metas = self._get_stock_metadata_from_meta_data_pre()
        finally:
            if self.db_connection:
                self.db_connection.close()
                self.db_connection = None

        if not all_metas or len(all_metas) < 2:
            self.logger.info("存量元数据不足，无需检测")
            return []

        n = len(all_metas)
        threshold = self.config['scan']['similarity_threshold']
        self.logger.info(f"共 {n} 条存量元数据，相似度阈值={threshold}，开始硬编码比较...")

        # 2. 构建字符倒排索引，只比较中文名共享 ≥1 字符的条目对
        from collections import defaultdict as _dd
        char_index: Dict[str, List[int]] = _dd(list)
        for idx, m in enumerate(all_metas):
            cn = m.get('CHINESE_NAME') or ''
            for ch in set(cn):
                if ch.strip():
                    char_index[ch].append(idx)

        self.logger.info(f"字符倒排索引构建完成，共 {len(char_index)} 个不同字符")

        # 3. 通过倒排索引生成候选对，去重后计算相似度
        uf = _UnionFind()
        pair_sims: Dict[Tuple[int, int], float] = {}
        total_pairs = 0
        seen: set = set()

        for ch, idx_list in char_index.items():
            if len(idx_list) < 2:
                continue
            # 过大的字符组跳过（如"号""名"等高频字，覆盖上万条，比较无意义）
            if len(idx_list) > 500:
                continue
            for ii in range(len(idx_list)):
                for jj in range(ii + 1, len(idx_list)):
                    gi, gj = idx_list[ii], idx_list[jj]
                    if gi > gj:
                        gi, gj = gj, gi
                    if (gi, gj) in seen:
                        continue
                    seen.add((gi, gj))
                    sim = self._string_similarity(
                        (all_metas[gi].get('CHINESE_NAME') or '').lower(),
                        (all_metas[gj].get('CHINESE_NAME') or '').lower(),
                    )
                    if sim >= threshold:
                        uf.union(gi, gj)
                        pair_sims[(gi, gj)] = sim
                        total_pairs += 1

        self.logger.info(f"字符预筛完成，候选对 {len(seen)} 个，发现 {total_pairs} 个冗余对")

        # 4. 收集分组（只保留 >= 2 条记录的组）
        groups: Dict[int, List[int]] = {}
        for idx in range(n):
            if idx in uf.parent:
                root = uf.find(idx)
                groups.setdefault(root, []).append(idx)

        groups = {k: v for k, v in groups.items() if len(v) >= 2}

        if not groups:
            self.logger.info("未发现存量冗余元数据")
            return []

        self.logger.info(f"硬编码检测到 {len(groups)} 个候选冗余组")

        # 5. LLM 确认边界组（组内最低相似度 < 0.95）
        confirmed_roots: set = set()
        borderline_groups: Dict[int, List[int]] = {}

        for root, indices in groups.items():
            min_sim = 1.0
            for ii in range(len(indices)):
                for jj in range(ii + 1, len(indices)):
                    key = (indices[ii], indices[jj])
                    rev_key = (indices[jj], indices[ii])
                    sim = pair_sims.get(key, pair_sims.get(rev_key, 1.0))
                    min_sim = min(min_sim, sim)
            if min_sim >= 0.95:
                confirmed_roots.add(root)
            else:
                borderline_groups[root] = indices

        if not borderline_groups:
            self.logger.info("所有候选组均为高置信度，无需 LLM 确认")
            confirmed_roots = set(groups.keys())
        else:
            self.logger.info(f"{len(borderline_groups)} 个边界组需要 LLM 确认")
            try:
                if not self.llm_client:
                    try:
                        self.connect_llm()
                    except Exception:
                        self.llm_client = None

                if self.llm_client:
                    batch_roots = list(borderline_groups.keys())
                    batch_size = 10
                    for batch_start in range(0, len(batch_roots), batch_size):
                        sub = batch_roots[batch_start:batch_start + batch_size]
                        prompt_parts = []
                        for i, root in enumerate(sub):
                            descs = []
                            for idx in borderline_groups[root]:
                                m = all_metas[idx]
                                descs.append(f"  - {m.get('METADATA_ID', '')}: {m.get('CHINESE_NAME', '')} ({m.get('METADATA_NAME', '')})")
                            prompt_parts.append(f"组{i + 1}:\n" + "\n".join(descs))

                        prompt = (
                            "你是元数据冗余分析专家。以下是几组元数据，判断每组中的元数据是否表示完全相同或高度相似的含义（语义冗余）。\n"
                            '冗余的定义：表示同一个业务概念的不同命名，例如"联系电话"和"手机号码"是冗余的，但"客户姓名"和"客户年龄"不是冗余的。\n\n'
                            + "\n".join(prompt_parts)
                            + '\n\n请只输出 JSON 数组: [{"group": 1, "redundant": true}, ...]'
                        )

                        try:
                            response = self.llm_client.chat.completions.create(
                                model=self.config['llm']['model_name'],
                                messages=[
                                    {"role": "system", "content": "你是严格的 JSON 输出机器，只输出 JSON 数组。"},
                                    {"role": "user", "content": prompt},
                                ],
                                max_tokens=500,
                                temperature=0.1,
                                timeout=self.config['llm']['timeout'],
                            )
                            content = response.choices[0].message.content.strip()
                            import re as _re
                            json_match = _re.search(r'\[.*\]', content, _re.DOTALL)
                            if json_match:
                                results = json.loads(json_match.group())
                                for item in results:
                                    gidx = item.get("group", 0) - 1
                                    if 0 <= gidx < len(sub) and item.get("redundant", False):
                                        confirmed_roots.add(sub[gidx])
                        except Exception as e:
                            self.logger.warning(f"LLM 批量确认失败，保留所有边界组: {e}")
                            confirmed_roots.update(sub)
                else:
                    self.logger.warning("LLM 客户端不可用，保留所有边界组")
                    confirmed_roots.update(borderline_groups.keys())
            except Exception as e:
                self.logger.warning(f"LLM 确认异常，保留全部候选组: {e}")
                confirmed_roots = set(groups.keys())

        groups = {k: v for k, v in groups.items() if k in confirmed_roots}

        if not groups:
            self.logger.info("LLM 确认后无冗余组")
            return []

        # 6. 生成结果
        result: List[Dict[str, Any]] = []
        group_num = 1
        for root in sorted(groups.keys(), key=lambda r: min(groups[r])):
            indices = groups[root]
            for idx in sorted(indices):
                m = all_metas[idx]
                result.append({
                    'group': group_num,
                    'metadata_id': m.get('METADATA_ID') or '',
                    'chinese_name': m.get('CHINESE_NAME') or '',
                    'data_type': f"{m.get('TYPE') or ''}({m.get('LENGTH') or ''})",
                    'opt_time': m.get('OPT_TIME') or '',
                    'opt_user': m.get('OPT_USER') or '',
                })
            group_num += 1

        self.logger.info(f"存量冗余检测完成，共 {group_num - 1} 个冗余组，{len(result)} 条记录")
        return result

    def run_analysis(self, run_now: bool = False, persist_report: bool = True) -> Dict[str, Any]:
        """执行分析并返回结构化结果，供主系统复用"""
        if not self.should_run_now(run_now):
            self.logger.info("根据计划时间，本次不执行任务")
            return {
                'executed': False,
                'report_rows': [],
                'report_content': '',
                'redundancy_results': [],
                'all_changed_metas': [],
            }

        self.logger.info("开始元数据变更检测和冗余分析")
        self.connect_database()
        try:
            try:
                self.connect_llm()
                self.logger.info("LLM连接成功，将使用语义相似度分析")
            except Exception as e:
                self.logger.warning(f"LLM连接失败，将使用备用的字符串相似度算法: {e}")
                self.llm_client = None

            self.load_cache()
            all_changed_metas = self.get_recent_metadata_changes()
            if not all_changed_metas:
                report = "# 元数据冗余分析报告\n\n## 扫描结果\n\n未发现最近的元数据变更。\n\n---\n**扫描时间**: {}".format(
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                )
                if persist_report:
                    self.save_report(report, report_rows=[])
                return {
                    'executed': True,
                    'report_rows': [],
                    'report_content': report,
                    'redundancy_results': [],
                    'all_changed_metas': [],
                }

            all_current_metas = self.get_all_current_metadata()
            redundancy_results, _ = self.detect_redundancy(all_changed_metas, all_current_metas)
            report = self.generate_report(redundancy_results, all_changed_metas)
            report_rows = self._build_report_rows(redundancy_results, all_changed_metas)
            if persist_report:
                self.save_report(report, report_rows=report_rows)
            self.save_cache()
            return {
                'executed': True,
                'report_rows': report_rows,
                'report_content': report,
                'redundancy_results': redundancy_results,
                'all_changed_metas': all_changed_metas,
            }
        finally:
            if self.db_connection:
                self.db_connection.close()
                self.db_connection = None
                self.logger.info("数据库连接已关闭")

    def run(self, force_full_scan: bool = False, run_now: bool = False):
        """执行主流程 - 优化版批量处理"""
        try:
            analysis = self.run_analysis(run_now=run_now, persist_report=True)
            if not analysis.get('executed'):
                return
            self.logger.info("元数据变更检测和冗余分析完成")
        except Exception as e:
            self.logger.error(f"执行过程中发生错误: {e}")
            raise

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='元数据变更检测和冗余分析脚本')
    parser.add_argument('--config', '-c', default='config.yaml', help='配置文件路径')
    parser.add_argument('--force-full-scan', '-f', action='store_true', help='强制全量扫描')
    parser.add_argument('--now', action='store_true', help='立即执行，忽略计划时间')
    parser.add_argument('--hours', type=int, help='扫描最近N小时的变更')
    
    args = parser.parse_args()
    
    # 如果指定了小时数，更新配置
    inform = MetadataChangeInform(args.config)
    if args.hours:
        inform.config['scan']['lookback_hours'] = args.hours
    
    inform.run(force_full_scan=args.force_full_scan, run_now=args.now)

if __name__ == '__main__':
    main()
