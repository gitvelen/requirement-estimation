# 需求评估系统优化方案 V2.0
## 基于实际约束的精简方案

> **更新时间**: 2026-01-31  
> **适用场景**: ESB接口可导出 + 历史数据质量差 + 无架构师投入

---

## 📌 实际情况分析

### 可用资源
| 数据资产 | 可用性 | 质量 | 可机器化 | 优先级 |
|---------|-------|------|---------|--------|
| **ESB接口文档** | ✅可导出 | 高 | ✅是 | **P0** |
| **功能清单** | 部分系统有 | 中 | ✅是 | P1 |
| **架构文档** | 部分系统有 | 低 | ❌否 | P2 |
| **历史评估数据** | 有 | 低(格式不统一) | ❌否 | **暂不用** |

### 核心策略
```
用"确定性强"的数据(接口/功能清单) 替代 "不确定性高"的数据(历史评估/架构文档)
```

---

## 🎯 优化目标与预期效果

### P0: 系统识别准确性
- **当前问题**: 只靠LLM理解需求文本 → 遗漏系统、错判归属
- **优化方案**: 基于ESB接口反推 → **"需求提到X功能,ESB显示Y系统提供X接口"**
- **预期提升**: 准确率 75% → 90%+

### P1: 功能拆分合理性  
- **当前问题**: 边界不清、归属混乱、依赖项缺失
- **优化方案**: 
  1. 从功能清单提取标准功能(半自动)
  2. 从ESB接口反推依赖关系
  3. 优化Prompt引导LLM边界判断
- **预期提升**: 功能归属错误率 15% → 5%

### P2: 人天预估准确性
- **当前问题**: 只按复杂度估算,无历史数据校准
- **优化方案**: 
  1. 从接口复杂度估算联调工作量
  2. 增加风险系数(新建接口 vs 改造接口)
- **预期提升**: 偏离度 ±35% → ±25%

---

## 📋 分阶段实施计划

### **Week 1: ESB接口知识库建设** ⭐最关键

#### 1.1 接口数据导出与清洗

**Step 1: 确认ESB导出格式**

典型ESB服务治理导出格式(需确认):

```csv
接口编码,接口名称,接口分类,提供方系统,调用方系统,调用频次,接口描述,状态
API_ACC_001,账户余额查询,账户管理,新一代核心,企业网银;手机银行,高,查询账户余额及可用余额,运行中
API_PAY_002,跨行转账,支付结算,支付中台,企业网银;柜面系统,中,发起跨行转账交易,运行中
API_CUS_003,客户信息查询,客户管理,客户信息系统,新一代核心;信贷系统,高,查询客户基本信息,运行中
```

**需要字段**(如果ESB没有,可以人工补充部分):
- 接口编码、接口名称 ✅必须
- 提供方系统、调用方系统 ✅必须
- 接口分类/功能分类 ✅必须
- 调用频次(高/中/低) ⭐重要
- 接口描述 ⭐重要
- 状态(运行中/已下线) ✅必须

**Step 2: 数据清洗脚本**

```python
# backend/scripts/import_esb_interfaces.py

import pandas as pd
import re
from backend.service.knowledge_service import get_knowledge_service

def clean_esb_export(excel_file: str) -> pd.DataFrame:
    """
    清洗ESB导出数据
    
    处理:
    1. 标准化系统名称(匹配system_list)
    2. 解析调用方列表(可能是"系统A;系统B"格式)
    3. 归一化调用频次(高/中/低)
    4. 过滤已下线接口
    """
    df = pd.read_excel(excel_file)
    
    # 1. 标准化列名
    column_mapping = {
        '接口编码': 'interface_code',
        '接口名称': 'interface_name',
        '接口分类': 'category',
        '提供方系统': 'provider_system',
        '调用方系统': 'consumer_systems',
        '调用频次': 'call_frequency',
        '接口描述': 'description',
        '状态': 'status'
    }
    df = df.rename(columns=column_mapping)
    
    # 2. 过滤已下线接口
    df = df[df['status'].str.contains('运行', na=False)]
    
    # 3. 解析调用方列表
    def parse_consumers(value):
        if pd.isna(value):
            return []
        # 可能的分隔符: ; , 、
        consumers = re.split(r'[;,、]', str(value))
        return [c.strip() for c in consumers if c.strip()]
    
    df['consumer_systems'] = df['consumer_systems'].apply(parse_consumers)
    
    # 4. 标准化系统名称
    system_list = load_system_list()
    
    def match_system(name):
        """匹配标准系统名称"""
        if not name or pd.isna(name):
            return None
        name = str(name).strip()
        
        # 精确匹配
        if name in system_list:
            return name
        
        # 模糊匹配
        for standard_name in system_list:
            if name in standard_name or standard_name in name:
                return standard_name
        
        # 返回原名(外部系统)
        return name
    
    df['provider_system'] = df['provider_system'].apply(match_system)
    df['consumer_systems'] = df['consumer_systems'].apply(
        lambda lst: [match_system(s) for s in lst if match_system(s)]
    )
    
    # 5. 归一化调用频次
    def normalize_frequency(value):
        if pd.isna(value):
            return '中'
        value = str(value).lower()
        if '高' in value or 'high' in value:
            return '高'
        elif '低' in value or 'low' in value:
            return '低'
        else:
            return '中'
    
    df['call_frequency'] = df['call_frequency'].apply(normalize_frequency)
    
    # 6. 过滤无效数据
    df = df.dropna(subset=['interface_code', 'interface_name', 'provider_system'])
    
    return df


def import_to_knowledge_base(df: pd.DataFrame):
    """导入到知识库"""
    knowledge_service = get_knowledge_service()
    
    knowledge_list = []
    for idx, row in df.iterrows():
        # 构建检索文本
        content = f"""
接口名称: {row['interface_name']}
接口编码: {row['interface_code']}
功能分类: {row.get('category', '')}
提供方系统: {row['provider_system']}
调用方系统: {', '.join(row['consumer_systems'])}
调用频次: {row.get('call_frequency', '中')}
接口描述: {row.get('description', '')}
        """.strip()
        
        # 构建元数据
        metadata = {
            'interface_code': row['interface_code'],
            'interface_name': row['interface_name'],
            'category': row.get('category', ''),
            'provider_system': row['provider_system'],
            'consumer_systems': row['consumer_systems'],
            'call_frequency': row.get('call_frequency', '中'),
            'description': row.get('description', ''),
            'imported_at': datetime.now().isoformat()
        }
        
        # 生成embedding
        embedding = knowledge_service.embedding_service.generate_embedding(content)
        
        knowledge_list.append({
            'system_name': row['provider_system'],
            'knowledge_type': 'interface_spec',
            'content': content,
            'embedding': embedding,
            'metadata': metadata,
            'source_file': 'ESB服务治理导出'
        })
    
    # 批量插入
    result = knowledge_service.vector_store.batch_insert_knowledge(knowledge_list)
    
    print(f"导入完成: 成功{result['success']}条, 失败{result['failed']}条")
    return result


if __name__ == '__main__':
    # 使用示例
    df = clean_esb_export('esb_export.xlsx')
    print(f"清洗后数据: {len(df)}条接口")
    
    import_to_knowledge_base(df)
```

#### 1.2 扩展知识库支持`interface_spec`类型

**修改1: 知识类型定义**

```python
# backend/service/knowledge_service.py

class KnowledgeService:
    # 知识类型
    TYPE_SYSTEM_PROFILE = "system_profile"  # 系统画像
    TYPE_INTERFACE_SPEC = "interface_spec"  # 接口规范 【新增】
```

**修改2: 检索逻辑**

当前`search_similar_knowledge`已支持`knowledge_type`过滤,无需修改。

**修改3: 统计接口**

```python
# backend/service/knowledge_service.py

def get_knowledge_stats(self, system_name: Optional[str] = None) -> Dict[str, Any]:
    """获取知识库统计信息"""
    # ... 现有代码 ...
    
    stats["system_profile_count"] = int(counts.get(self.TYPE_SYSTEM_PROFILE, 0) or 0)
    stats["interface_spec_count"] = int(counts.get(self.TYPE_INTERFACE_SPEC, 0) or 0)  # 新增
    stats["feature_case_count"] = 0
    stats["tech_spec_count"] = 0
    return stats
```

#### 1.3 系统识别Agent增强

**修改: system_identification_agent.py**

```python
def identify(self, requirement_content: str, task_id: Optional[str] = None) -> List[Dict[str, str]]:
    """识别需求中涉及的所有系统"""
    
    # ... 现有代码 ...
    
    # 【原有】检索系统画像
    system_profiles: List[Dict[str, Any]] = []
    if self.knowledge_enabled and self.knowledge_service:
        system_profiles = self.knowledge_service.search_similar_knowledge(
            query_text=requirement_content,
            knowledge_type="system_profile",
            top_k=settings.KNOWLEDGE_TOP_K,
            similarity_threshold=settings.KNOWLEDGE_SIMILARITY_THRESHOLD,
            task_id=task_id,
            stage="system_identification"
        )
    
    # 【新增】检索接口规范
    interface_specs: List[Dict[str, Any]] = []
    if self.knowledge_enabled and self.knowledge_service:
        interface_specs = self.knowledge_service.search_similar_knowledge(
            query_text=requirement_content,
            knowledge_type="interface_spec",  # 接口知识
            top_k=10,  # 接口数量多,top_k设大一点
            similarity_threshold=max(settings.KNOWLEDGE_SIMILARITY_THRESHOLD, 0.65),  # 接口匹配要求更高
            task_id=task_id,
            stage="system_identification_interface"
        )
        
        if interface_specs:
            logger.info(f"[系统识别] 检索到 {len(interface_specs)} 条相关接口")
    
    # 【新增】从接口推断系统
    interface_inferred_systems = self._infer_systems_from_interfaces(interface_specs)
    
    # 构建Prompt
    user_prompt = f"需求内容：\n\n{requirement_content}\n\n"
    
    if candidate_systems:
        user_prompt += "【候选系统榜单（来自知识库system_profile）】\n"
        user_prompt += json.dumps(candidate_systems, ensure_ascii=False, indent=2)
        user_prompt += "\n\n"
    
    # 【新增】注入接口推断结果
    if interface_inferred_systems:
        user_prompt += "【接口规范推断(来自ESB,准确度高)】\n"
        user_prompt += json.dumps(interface_inferred_systems, ensure_ascii=False, indent=2)
        user_prompt += "\n\n"
    
    if knowledge_context:
        user_prompt += f"\n【系统知识参考】\n{knowledge_context}\n\n"
    
    # 【修改】识别规则
    user_prompt += """
请识别该需求涉及的所有系统，并给出置信度与理由。

【识别策略(按优先级)】
1. **接口规范优先**: 如果【接口规范推断】中明确显示某系统提供了需求中提到的功能,该系统置信度应为"高"
2. **系统画像参考**: 结合【候选系统榜单】和【系统知识参考】中的系统边界判断
3. **关键词推测**: 作为兜底策略,但置信度标为"中"或"低"

【输出要求】
每个系统必须说明:
- confidence: "高"(有接口证据) / "中"(系统画像支持) / "低"(仅关键词)
- reasons: 列表形式,优先标注 "[ESB接口]" / "[系统画像]" / "[关键词]"
"""
    
    # ... 调用LLM,解析结果 ...


def _infer_systems_from_interfaces(self, interface_specs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """从接口规范推断涉及的系统"""
    if not interface_specs:
        return []
    
    # 统计系统出现频次
    system_scores: Dict[str, Dict] = {}
    
    for spec in interface_specs:
        metadata = spec.get('metadata', {})
        provider = metadata.get('provider_system')
        consumers = metadata.get('consumer_systems', [])
        similarity = spec.get('similarity', 0.0)
        
        # 提供方系统(权重更高)
        if provider:
            if provider not in system_scores:
                system_scores[provider] = {
                    'system_name': provider,
                    'score': 0.0,
                    'interface_count': 0,
                    'interfaces': [],
                    'role': 'provider'
                }
            system_scores[provider]['score'] += similarity * 1.5  # 提供方权重1.5
            system_scores[provider]['interface_count'] += 1
            system_scores[provider]['interfaces'].append({
                'name': metadata.get('interface_name'),
                'code': metadata.get('interface_code'),
                'category': metadata.get('category'),
                'similarity': round(similarity, 3)
            })
        
        # 调用方系统
        for consumer in consumers:
            if consumer:
                if consumer not in system_scores:
                    system_scores[consumer] = {
                        'system_name': consumer,
                        'score': 0.0,
                        'interface_count': 0,
                        'interfaces': [],
                        'role': 'consumer'
                    }
                system_scores[consumer]['score'] += similarity * 1.0  # 调用方权重1.0
                system_scores[consumer]['interface_count'] += 1
                if len(system_scores[consumer]['interfaces']) < 3:  # 只保留top3接口
                    system_scores[consumer]['interfaces'].append({
                        'name': metadata.get('interface_name'),
                        'code': metadata.get('interface_code'),
                        'category': metadata.get('category'),
                        'similarity': round(similarity, 3)
                    })
    
    # 排序并格式化
    result = []
    for system_name, data in sorted(system_scores.items(), key=lambda x: x[1]['score'], reverse=True):
        result.append({
            'system_name': system_name,
            'confidence_score': round(data['score'], 3),
            'interface_count': data['interface_count'],
            'role': data['role'],  # provider / consumer
            'top_interfaces': data['interfaces'][:3],
            'reasoning': f"{'提供' if data['role'] == 'provider' else '调用'}{data['interface_count']}个相关接口"
        })
    
    return result[:8]  # 返回top8
```

**修改Prompt模板**

```python
# backend/prompts/prompt_templates.py

SYSTEM_IDENTIFICATION_PROMPT = """
你是银行系统架构专家,负责从需求文档中识别涉及的所有系统。

【识别策略(按优先级)】
1. **ESB接口规范优先** ⭐
   - 如果【接口规范推断】中显示某系统提供了需求相关的接口,该系统置信度应为"高"
   - 接口数据来自ESB服务治理,准确度高于架构文档
   - 示例: 需求提到"账户余额查询",接口规范显示"新一代核心"提供API_ACC_001接口 → 置信度"高"

2. **系统画像参考**
   - 结合【候选系统榜单】和【系统知识参考】中的系统边界(in_scope/out_of_scope)判断
   - 置信度标为"中"

3. **关键词推测**(兜底)
   - 当前两种方式都无法识别时,基于关键词推测
   - 置信度必须标为"低"

【输出格式】
{
  "systems": [
    {
      "name": "系统名称",
      "type": "主系统" / "依赖系统",
      "confidence": "高" / "中" / "低",
      "reasons": [
        "[ESB接口] 提供3个相关接口: API_ACC_001(账户查询), ...",
        "[系统画像] 系统边界包含账户管理功能"
      ],
      "description": "系统在本需求中的作用"
    }
  ],
  "maybe_systems": [
    {
      "name": "可能涉及的系统",
      "confidence": "低",
      "reason": "需求提到XX,但无明确接口证据,建议进一步确认"
    }
  ],
  "questions": [
    "是否需要调用征信系统?",
    "..."
  ]
}

【注意事项】
- 优先依赖ESB接口规范判断,其次才是系统画像
- 如果接口规范和系统画像冲突,以接口规范为准(接口是实际运行的,更准确)
- 置信度务必准确标注,便于后续人工复核
"""
```

---

### **Week 2: 功能拆分优化** ⭐第二重点

#### 2.1 从功能清单半自动提取功能模板

**方案**: 即使没有历史评估数据,仍然可以从**现有系统的功能清单**提取功能模板

**Step 1: 收集功能清单**

```
来源:
1. 部分系统有功能清单文档(Word/Excel)
2. 从系统画像(DOCX/PPTX)中提取"核心功能"字段
3. 从ESB接口分类中反推功能模块
```

**Step 2: 半自动提取脚本**

```python
# backend/scripts/extract_feature_templates.py

def extract_from_function_list(excel_file: str, system_name: str):
    """从功能清单提取功能模板"""
    df = pd.read_excel(excel_file)
    
    # 假设功能清单格式: [功能模块, 功能名称, 功能描述]
    templates = []
    for idx, row in df.iterrows():
        templates.append({
            'template_id': f"TPL_{system_name}_{idx:03d}",
            'template_name': row['功能名称'],
            'module': row.get('功能模块', ''),
            'description': row.get('功能描述', ''),
            'applicable_systems': [system_name],
            'typical_complexity': '中',  # 默认
            'typical_days_range': [2.0, 4.0],  # 默认
            'source': 'function_list'
        })
    
    return templates


def extract_from_system_profiles():
    """从已导入的system_profile中提取功能"""
    knowledge_service = get_knowledge_service()
    
    # 获取所有system_profile
    all_profiles = knowledge_service.vector_store.get_all_by_type('system_profile')
    
    templates = []
    for profile in all_profiles:
        metadata = profile.get('metadata', {})
        system_name = metadata.get('system_name', '')
        core_functions = metadata.get('core_functions', '')  # "账户管理、支付结算、..."
        
        if not core_functions:
            continue
        
        # 分词
        functions = re.split(r'[,、;；]', core_functions)
        
        for func in functions:
            func = func.strip()
            if not func:
                continue
            
            templates.append({
                'template_id': f"TPL_{system_name}_{hash(func) % 1000:03d}",
                'template_name': func,
                'module': '',
                'description': f"{system_name}的核心功能之一",
                'applicable_systems': [system_name],
                'typical_complexity': '中',
                'typical_days_range': [2.0, 4.0],
                'source': 'system_profile'
            })
    
    return templates


def extract_from_esb_interfaces():
    """从ESB接口分类反推功能模板"""
    knowledge_service = get_knowledge_service()
    
    # 获取所有interface_spec
    all_interfaces = knowledge_service.vector_store.get_all_by_type('interface_spec')
    
    # 按(系统, 功能分类)聚合
    grouped = {}
    for interface in all_interfaces:
        metadata = interface.get('metadata', {})
        system_name = metadata.get('provider_system', '')
        category = metadata.get('category', '')
        
        key = (system_name, category)
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(metadata.get('interface_name', ''))
    
    templates = []
    for (system_name, category), interface_names in grouped.items():
        if not category:
            continue
        
        templates.append({
            'template_id': f"TPL_{system_name}_{hash(category) % 1000:03d}",
            'template_name': category,
            'module': category,
            'description': f"包含接口: {', '.join(interface_names[:3])}...",
            'applicable_systems': [system_name],
            'typical_complexity': '中',
            'typical_days_range': [2.0, 4.0],
            'related_interfaces': interface_names,
            'source': 'esb_interface'
        })
    
    return templates


def merge_and_import():
    """合并去重并导入"""
    templates = []
    
    # 来源1: 功能清单(如果有)
    # templates += extract_from_function_list('核心系统功能清单.xlsx', '新一代核心')
    
    # 来源2: system_profile
    templates += extract_from_system_profiles()
    
    # 来源3: ESB接口
    templates += extract_from_esb_interfaces()
    
    # 去重(相似功能合并)
    templates = deduplicate_templates(templates)
    
    print(f"提取到 {len(templates)} 个功能模板")
    
    # 导入到知识库
    knowledge_service = get_knowledge_service()
    for template in templates:
        content = f"""
功能模板: {template['template_name']}
适用系统: {', '.join(template['applicable_systems'])}
功能模块: {template.get('module', '')}
描述: {template.get('description', '')}
        """.strip()
        
        embedding = knowledge_service.embedding_service.generate_embedding(content)
        
        knowledge_service.vector_store.insert_knowledge({
            'system_name': template['applicable_systems'][0],
            'knowledge_type': 'feature_template',
            'content': content,
            'embedding': embedding,
            'metadata': template,
            'source_file': f"auto_extract_{template['source']}"
        })
```

#### 2.2 功能拆分Agent增强

```python
# backend/agent/feature_breakdown_agent.py

def breakdown(self, requirement_content: str, system_name: str, system_type: str = "主系统", task_id: Optional[str] = None):
    """对指定系统进行功能点拆分"""
    
    # ... 现有代码 ...
    
    # 【原有】检索系统画像
    system_profiles = self.knowledge_service.search_similar_knowledge(
        query_text=requirement_content,
        system_name=system_name,
        knowledge_type="system_profile",
        ...
    )
    
    # 【新增】检索功能模板
    feature_templates = []
    if self.knowledge_enabled and self.knowledge_service:
        feature_templates = self.knowledge_service.search_similar_knowledge(
            query_text=requirement_content,
            system_name=system_name,
            knowledge_type="feature_template",
            top_k=10,
            similarity_threshold=0.65,
            task_id=task_id,
            stage="feature_breakdown_template"
        )
        
        if feature_templates:
            logger.info(f"[功能拆分] 检索到 {len(feature_templates)} 个相关功能模板")
    
    # 【新增】检索相关接口
    interface_specs = []
    if self.knowledge_enabled and self.knowledge_service:
        interface_specs = self.knowledge_service.search_similar_knowledge(
            query_text=requirement_content,
            system_name=system_name,
            knowledge_type="interface_spec",
            top_k=15,
            similarity_threshold=0.6,
            task_id=task_id,
            stage="feature_breakdown_interface"
        )
        
        if interface_specs:
            logger.info(f"[功能拆分] 检索到 {len(interface_specs)} 个相关接口")
    
    # 构建Prompt
    user_prompt = f"""需求内容：\n\n{requirement_content}\n\n"""
    user_prompt += f"""请针对【{system_name}】（类型：{system_type}）进行功能点拆分。\n\n"""
    
    # 【新增】注入功能模板
    if feature_templates:
        user_prompt += "【功能模板参考】\n"
        for idx, template in enumerate(feature_templates[:5], 1):
            metadata = template.get('metadata', {})
            user_prompt += f"{idx}. {metadata.get('template_name')} (模块:{metadata.get('module')}, 来源:{metadata.get('source')})\n"
        user_prompt += "\n"
    
    # 【新增】注入接口参考
    if interface_specs:
        user_prompt += "【相关接口参考(ESB)】\n"
        for idx, spec in enumerate(interface_specs[:8], 1):
            metadata = spec.get('metadata', {})
            user_prompt += f"{idx}. {metadata.get('interface_name')} ({metadata.get('category')})\n"
        user_prompt += "\n"
    
    # 【修改】拆分规则
    user_prompt += """拆分要求：
1. **优先参考功能模板**: 如果需求中的功能与【功能模板参考】高度相似,可直接引用模板
2. **基于接口推断依赖**: 利用【相关接口参考】推断该功能需要调用哪些下游系统
3. **明确系统边界**: 只拆分属于【{system_name}】的功能点,参考【系统知识参考】中的系统边界
4. 功能点粒度控制在0.5-5人天
5. 评估复杂度（高/中/低）
6. 备注字段必须包含以下标签：
   - [模板匹配] 或 [新拆分]
   - [相关接口]: 列出ESB接口编码
   - [依赖系统]: 基于接口推断
   - [待确认]: 不确定的地方
"""
    
    # ... 调用LLM,解析结果 ...
    
    # 【新增】后处理: 补充接口依赖
    features = result["features"]
    features = self._enrich_features_with_interfaces(features, interface_specs)
    
    return features


def _enrich_features_with_interfaces(self, features: List[Dict], interface_specs: List[Dict]) -> List[Dict]:
    """基于接口规范补充功能点的依赖项"""
    if not interface_specs:
        return features
    
    # 构建接口索引: 接口名称 -> 接口元数据
    interface_index = {}
    for spec in interface_specs:
        metadata = spec.get('metadata', {})
        interface_name = metadata.get('interface_name', '')
        if interface_name:
            interface_index[interface_name] = metadata
    
    for feature in features:
        # 检查备注中是否提到接口
        remark = feature.get('备注', '')
        matched_interfaces = []
        
        for interface_name, metadata in interface_index.items():
            # 简单匹配(可优化为语义匹配)
            if interface_name in remark or interface_name in feature.get('业务描述', ''):
                matched_interfaces.append(metadata)
        
        if matched_interfaces:
            # 推断依赖系统
            deps = set()
            interface_codes = []
            
            for metadata in matched_interfaces:
                # 调用方系统成为依赖项
                deps.update(metadata.get('consumer_systems', []))
                # 记录接口编码
                interface_codes.append(metadata.get('interface_code', ''))
            
            # 补充依赖项
            existing_deps = feature.get('依赖项', '').split(',') if feature.get('依赖项') else []
            all_deps = set(d.strip() for d in existing_deps if d.strip()) | deps
            feature['依赖项'] = ', '.join(sorted(all_deps))
            
            # 补充备注
            if '[相关接口]' not in feature.get('备注', ''):
                feature['备注'] += f"\n[相关接口] {', '.join(interface_codes[:3])}"
    
    return features
```

---

### **Week 3: 人天估算优化**

#### 3.1 基于接口复杂度的联调工作量估算

```python
# backend/agent/workload_estimation_agent.py (新增)

class WorkloadEstimationAgent:
    """工作量估算Agent(独立拆出)"""
    
    def estimate_with_interface_analysis(self, feature: Dict, system_name: str) -> Dict:
        """基于接口分析估算工作量"""
        
        # 基础工作量(按复杂度)
        complexity = feature.get('复杂度', '中')
        base_days = {
            '低': 1.5,
            '中': 3.0,
            '高': 5.0
        }[complexity]
        
        # 【新增】接口联调工作量
        integration_days = 0.0
        interface_count = 0
        
        # 从备注中提取接口编码
        remark = feature.get('备注', '')
        interface_pattern = r'API_\w+_\d+'
        interface_codes = re.findall(interface_pattern, remark)
        
        if interface_codes:
            # 查询接口详情
            knowledge_service = get_knowledge_service()
            for code in interface_codes:
                results = knowledge_service.vector_store.search_by_metadata(
                    knowledge_type='interface_spec',
                    filters={'interface_code': code}
                )
                
                if results:
                    interface = results[0].get('metadata', {})
                    interface_count += 1
                    
                    # 估算单个接口的联调工作量
                    call_frequency = interface.get('call_frequency', '中')
                    
                    if call_frequency == '高':
                        integration_days += 0.5  # 高频接口需要更多测试
                    elif call_frequency == '中':
                        integration_days += 0.3
                    else:
                        integration_days += 0.2
        
        # 如果有依赖系统但没有明确接口,按系统数估算
        deps = feature.get('依赖项', '').split(',')
        dep_count = len([d for d in deps if d.strip() and d.strip() not in ['无', '-']])
        
        if dep_count > 0 and interface_count == 0:
            # 假设每个依赖系统至少1个接口
            integration_days = dep_count * 0.3
        
        # 联调基础工作量(如果有接口)
        if integration_days > 0:
            integration_days += 1.0  # 基础联调准备
        
        # 总工作量
        total_days = base_days + integration_days
        
        # 风险系数
        risk_factor = 1.0
        if '新建' in remark or '新增' in remark:
            risk_factor = 1.2  # 新建功能风险高
        elif '改造' in remark:
            risk_factor = 1.1
        
        total_days *= risk_factor
        
        return {
            '预估人天': round(total_days, 1),
            '基础人天': base_days,
            '接口联调人天': round(integration_days, 1),
            '接口数量': interface_count,
            '依赖系统数': dep_count,
            '风险系数': risk_factor,
            '置信度': '中' if interface_count > 0 else '低',
            '估算说明': self._build_estimation_explanation(
                base_days, integration_days, interface_count, dep_count, risk_factor
            )
        }
    
    def _build_estimation_explanation(self, base_days, integration_days, interface_count, dep_count, risk_factor):
        """构建估算说明"""
        parts = [
            f"基础开发 {base_days}人天"
        ]
        
        if integration_days > 0:
            parts.append(f"接口联调 {integration_days:.1f}人天({interface_count}个接口)")
        
        if risk_factor > 1.0:
            parts.append(f"风险系数 ×{risk_factor}")
        
        return " + ".join(parts)
```

**集成到功能拆分流程**

```python
# backend/agent/feature_breakdown_agent.py

def breakdown(self, ...):
    # ... 拆分逻辑 ...
    
    features = result["features"]
    
    # 【新增】使用专门的估算Agent重新评估工作量
    estimation_agent = WorkloadEstimationAgent(self.knowledge_service)
    
    for feature in features:
        estimation = estimation_agent.estimate_with_interface_analysis(feature, system_name)
        
        # 更新预估人天
        feature['预估人天'] = estimation['预估人天']
        
        # 补充估算细节(用于前端展示)
        feature['估算细节'] = {
            '基础人天': estimation['基础人天'],
            '接口联调人天': estimation['接口联调人天'],
            '接口数量': estimation['接口数量'],
            '依赖系统数': estimation['依赖系统数'],
            '风险系数': estimation['风险系数'],
            '置信度': estimation['置信度'],
            '说明': estimation['估算说明']
        }
    
    return features
```

---

### **Week 4: 前端优化与效果评估**

#### 4.1 前端展示"估算依据"

**修改: frontend/src/components/SystemBreakdown.js**

```javascript
// 功能点卡片增加"估算依据"折叠面板

<Card>
  <CardContent>
    <Typography variant="h6">{feature.功能点}</Typography>
    <Typography>预估人天: {feature.预估人天}</Typography>
    
    {/* 新增: 估算依据 */}
    <Accordion>
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Typography variant="subtitle2">
          📊 估算依据 (置信度: {feature.估算细节?.置信度 || '中'})
        </Typography>
      </AccordionSummary>
      <AccordionDetails>
        <Box>
          <Typography variant="body2">
            <strong>基础开发:</strong> {feature.估算细节?.基础人天 || 0} 人天
          </Typography>
          <Typography variant="body2">
            <strong>接口联调:</strong> {feature.估算细节?.接口联调人天 || 0} 人天 
            ({feature.估算细节?.接口数量 || 0}个接口)
          </Typography>
          <Typography variant="body2">
            <strong>依赖系统:</strong> {feature.依赖项 || '无'}
          </Typography>
          <Typography variant="body2">
            <strong>风险系数:</strong> ×{feature.估算细节?.风险系数 || 1.0}
          </Typography>
          <Divider sx={{ my: 1 }} />
          <Typography variant="body2" color="text.secondary">
            {feature.估算细节?.说明 || ''}
          </Typography>
          
          {/* 接口参考 */}
          {feature.备注?.includes('[相关接口]') && (
            <Box mt={1}>
              <Typography variant="caption" color="primary">
                📡 {feature.备注.match(/\[相关接口\]([^\n]+)/)?.[1] || ''}
              </Typography>
            </Box>
          )}
        </Box>
      </AccordionDetails>
    </Accordion>
  </CardContent>
</Card>
```

#### 4.2 系统识别结果增加"接口证据"

```javascript
// frontend/src/components/SystemIdentification.js

<TableRow>
  <TableCell>{system.name}</TableCell>
  <TableCell>
    <Chip 
      label={system.confidence} 
      color={system.confidence === '高' ? 'success' : 'default'}
    />
  </TableCell>
  <TableCell>
    {system.reasons.map((reason, idx) => (
      <Typography key={idx} variant="body2">
        {reason.includes('[ESB接口]') ? '🔌 ' : '📄 '}
        {reason}
      </Typography>
    ))}
    
    {/* 新增: 接口证据详情 */}
    {system.interface_evidence && (
      <Accordion>
        <AccordionSummary>
          <Typography variant="caption">
            查看接口证据({system.interface_evidence.length}个)
          </Typography>
        </AccordionSummary>
        <AccordionDetails>
          <List dense>
            {system.interface_evidence.map((iface, idx) => (
              <ListItem key={idx}>
                <ListItemText
                  primary={iface.interface_name}
                  secondary={`${iface.interface_code} | ${iface.category}`}
                />
              </ListItem>
            ))}
          </List>
        </AccordionDetails>
      </Accordion>
    )}
  </TableCell>
</TableRow>
```

#### 4.3 增加知识库效果统计

**后端: 增加接口知识统计**

```python
# backend/api/knowledge_routes.py

@router.get("/stats")
def get_knowledge_stats():
    """获取知识库统计"""
    stats = knowledge_service.get_knowledge_stats()
    
    # 【新增】接口知识统计
    if stats.get('interface_spec_count', 0) > 0:
        # 统计接口覆盖的系统数
        interface_systems = knowledge_service.vector_store.get_distinct_systems(
            knowledge_type='interface_spec'
        )
        stats['interface_covered_systems'] = len(interface_systems)
        
        # 统计接口分类分布
        interface_categories = knowledge_service.vector_store.get_category_distribution(
            knowledge_type='interface_spec'
        )
        stats['interface_categories'] = interface_categories
    
    return stats
```

**前端: 展示接口知识统计**

```javascript
// frontend/src/pages/KnowledgePage.js

<Grid container spacing={2}>
  <Grid item xs={12} md={3}>
    <Card>
      <CardContent>
        <Typography color="textSecondary">系统画像</Typography>
        <Typography variant="h4">{stats.system_profile_count}</Typography>
      </CardContent>
    </Card>
  </Grid>
  
  {/* 新增 */}
  <Grid item xs={12} md={3}>
    <Card>
      <CardContent>
        <Typography color="textSecondary">接口规范(ESB)</Typography>
        <Typography variant="h4">{stats.interface_spec_count}</Typography>
        <Typography variant="caption">
          覆盖{stats.interface_covered_systems}个系统
        </Typography>
      </CardContent>
    </Card>
  </Grid>
  
  <Grid item xs={12} md={3}>
    <Card>
      <CardContent>
        <Typography color="textSecondary">功能模板</Typography>
        <Typography variant="h4">{stats.feature_template_count || 0}</Typography>
      </CardContent>
    </Card>
  </Grid>
</Grid>
```

---

## 📊 效果评估方案

### 对比测试(Week 4末)

**测试数据**: 准备10个真实需求案例

**对比维度**:

| 维度 | 优化前 | 优化后 | 目标提升 |
|-----|--------|--------|---------|
| **系统识别准确率** | 人工统计 | 人工统计 | +15% |
| **系统遗漏率** | 人工统计 | 人工统计 | -10% |
| **功能归属错误率** | 人工统计 | 人工统计 | -10% |
| **依赖项识别准确率** | 新指标 | 人工统计 | >80% |
| **人天偏离度** | ±35% | ±25% | -10% |
| **置信度标注准确性** | 无 | 人工验证 | 新功能 |

**测试方法**:

```python
# backend/scripts/evaluate_optimization.py

def evaluate_system_identification(test_cases):
    """评估系统识别效果"""
    results = []
    
    for case in test_cases:
        # AI识别
        ai_systems = agent.identify(case['requirement'])
        
        # 人工标注的真实系统
        true_systems = case['true_systems']
        
        # 计算准确率
        ai_system_names = set(s['name'] for s in ai_systems)
        true_system_names = set(true_systems)
        
        precision = len(ai_system_names & true_system_names) / len(ai_system_names) if ai_system_names else 0
        recall = len(ai_system_names & true_system_names) / len(true_system_names) if true_system_names else 0
        
        # 统计接口证据的系统
        interface_based = set(s['name'] for s in ai_systems if any('[ESB接口]' in r for r in s.get('reasons', [])))
        
        results.append({
            'case_id': case['id'],
            'precision': precision,
            'recall': recall,
            'interface_based_count': len(interface_based),
            'interface_based_accuracy': len(interface_based & true_system_names) / len(interface_based) if interface_based else 0
        })
    
    # 汇总
    avg_precision = sum(r['precision'] for r in results) / len(results)
    avg_recall = sum(r['recall'] for r in results) / len(results)
    avg_interface_accuracy = sum(r['interface_based_accuracy'] for r in results) / len(results)
    
    print(f"系统识别准确率: {avg_precision:.2%}")
    print(f"系统识别召回率: {avg_recall:.2%}")
    print(f"接口推断准确率: {avg_interface_accuracy:.2%}")
    
    return results
```

---

## 💡 关键成功因素(调整后)

### 1. **ESB接口数据质量** ⭐⭐⭐
- 确保导出的接口数据完整(提供方、调用方、分类)
- 过滤已下线接口
- 系统名称标准化匹配

### 2. **不依赖人工Review** ⭐⭐
- 功能模板从现有数据自动提取
- 接口关系自动分析
- 减少人工介入成本

### 3. **渐进式优化**
- Week 1-2: 接口知识库(见效最快)
- Week 3: 功能模板(提升拆分质量)
- Week 4: 前端优化(提升用户体验)

### 4. **效果可量化**
- 每个优化点都有明确的评估指标
- 对比测试验证提升幅度

---

## 🚦 风险与应对

| 风险 | 可能性 | 影响 | 应对措施 |
|-----|-------|------|---------|
| ESB导出格式不标准 | 中 | 高 | 先导出样例数据,确认格式后再开发 |
| 系统名称匹配失败 | 中 | 中 | 建立系统名称映射表,人工补充 |
| 接口分类不明确 | 高 | 低 | 使用接口名称做语义匹配,不强依赖分类 |
| 功能模板数量少 | 中 | 中 | 从多个来源提取,逐步积累 |

---

## 📅 实施时间表(4周)

```
Week 1: ESB接口导入
├─ Day 1-2: 导出样例数据,确认格式,设计数据结构
├─ Day 3: 开发清洗脚本
├─ Day 4: 扩展知识库支持interface_spec
└─ Day 5: 批量导入,测试检索

Week 2: 系统识别优化
├─ Day 1-2: 修改system_identification_agent
├─ Day 3: 优化Prompt模板
├─ Day 4-5: 测试与调优

Week 3: 功能拆分优化
├─ Day 1-2: 半自动提取功能模板
├─ Day 3: 修改feature_breakdown_agent
├─ Day 4: 开发WorkloadEstimationAgent
└─ Day 5: 测试与调优

Week 4: 前端优化与评估
├─ Day 1-2: 前端展示"估算依据"
├─ Day 3: 准备测试案例,对比测试
├─ Day 4: 修复问题,优化细节
└─ Day 5: 输出评估报告,上线试运行
```

---

## 🎯 下一步行动

我建议你:

1. **确认ESB导出格式**(今天)
   - 导出一份样例数据
   - 发给我,我帮你设计清洗脚本

2. **启动Week 1**(明天开始)
   - 我可以帮你写:
     - ESB清洗导入脚本
     - 知识库扩展代码
     - 测试脚本

3. **准备10个测试案例**(Week 1-2同步进行)
   - 找10个真实需求文档
   - 人工标注"真实涉及的系统"(用于对比测试)

你觉得这个方案如何?需要我先帮你写ESB导入脚本吗? 🚀
