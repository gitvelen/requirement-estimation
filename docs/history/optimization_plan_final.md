# 需求评估系统全面优化方案（最终版）

> **版本**: V4.0 Final  
> **日期**: 2026-01-31  
> **综合**: optimization_plan_v2.md + enhance_v3.md  
> **核心策略**: 接口驱动 + 规则化 + 黄金数据集 + 置信度标注

---

## 📌 核心发现与优化逻辑

### 问题本质（来自enhance_v3.md）

```
AI评估不准 = 系统识别偏差 + 功能拆分偏差 × 复杂度假设错误
```

**关键洞察**:
1. ❌ 不是"评估技术"问题,是**"需求理解"问题**
2. ✅ 系统识别 + 功能拆分是准确性提升的**"杠杆点"**
3. ✅ 50-100个高质量案例 > 1000个低质量案例
4. ✅ 需要从"确定数字"转向**"区间+置信度"**

### 可用资源评估

| 资源 | 可用性 | 质量 | 可机器化 | 优先级 | 来源 |
|-----|--------|------|---------|--------|------|
| **ESB接口文档** | ✅ 可导出 | ⭐⭐⭐⭐⭐ | ✅ 是 | **P0** | optimization_plan_v2.md |
| **功能点分类体系** | ❌ 需构建 | ⭐⭐⭐⭐ | ✅ 是 | **P0** | enhance_v3.md |
| **功能清单** | 部分系统有 | ⭐⭐⭐ | ✅ 是 | P1 | 现有资源 |
| **黄金数据集** | ❌ 需构建 | ⭐⭐⭐⭐⭐ | ⚠️ 半自动 | P1 | enhance_v3.md |
| **历史评估数据** | 有 | ⭐ | ❌ 否 | **暂不用** | 质量差 |

---

## 🎯 优化方案三大支柱

### 支柱一: 接口驱动的系统识别 ⭐⭐⭐
**来源**: optimization_plan_v2.md  
**核心**: 利用ESB接口文档精准识别系统归属

### 支柱二: 规则化的功能拆分 ⭐⭐⭐
**来源**: enhance_v3.md  
**核心**: 建立功能点分类体系与拆分规则

### 支柱三: 黄金数据集驱动的持续优化 ⭐⭐
**来源**: enhance_v3.md  
**核心**: 从高质量案例中学习,建立评估标杆

---

## 📋 分阶段实施计划

### 🚀 阶段一: 接口知识库 + 功能分类体系（Week 1-2）

**目标**: 建立两个核心知识库

#### 任务1.1: ESB接口知识库建设 ⭐核心

**数据来源**: ESB服务治理导出

**数据结构**:
```json
{
  "knowledge_type": "interface_spec",
  "system_name": "新一代核心",
  "interface_code": "API_ACC_001",
  "interface_name": "账户余额查询",
  "category": "账户管理",
  "provider_system": "新一代核心",
  "consumer_systems": ["企业网银", "手机银行"],
  "call_frequency": "高",
  "description": "查询账户余额及可用余额",
  "typical_change_scope": ["接口字段扩展", "性能优化"],
  "typical_integration_days": 0.5  // 联调工作量
}
```

**实施步骤**:

```python
# Step 1: ESB清洗导入脚本
# backend/scripts/import_esb_interfaces.py

def clean_and_import_esb(excel_file: str):
    """
    从ESB导出Excel清洗并导入
    
    处理:
    1. 标准化系统名称
    2. 解析调用方列表
    3. 归一化调用频次
    4. 过滤已下线接口
    """
    df = pd.read_excel(excel_file)
    
    # 清洗逻辑(见optimization_plan_v2.md)
    df = clean_data(df)
    
    # 导入到知识库
    knowledge_service = get_knowledge_service()
    
    for idx, row in df.iterrows():
        content = build_interface_content(row)
        embedding = embedding_service.generate_embedding(content)
        
        knowledge_service.vector_store.insert_knowledge({
            'system_name': row['provider_system'],
            'knowledge_type': 'interface_spec',
            'content': content,
            'embedding': embedding,
            'metadata': dict(row),
            'source_file': 'ESB服务治理导出'
        })
```

**产出**:
- ✅ 接口知识库(预计500-1000条)
- ✅ 系统依赖关系图谱(自动生成)
- ✅ 接口分类统计

---

#### 任务1.2: 功能点分类体系建设 ⭐核心

**灵感来源**: enhance_v3.md 表格

**功能分类与拆分规则**:

| 功能类型 | 典型描述 | 基准人天 | 拆分规则 | 示例 |
|---------|---------|---------|---------|------|
| **单表查询** | 查询XX信息 | 0.5-1 | 独立功能点 | 客户信息查询 |
| **列表展示** | XX列表+筛选分页 | 1-2 | 独立功能点 | 客户列表 |
| **单表CRUD** | 新增/编辑XX | 1-2 | 增删改查各1个功能点 | 客户创建 |
| **审批流程** | XX审批 | 2-4 | 按审批节点拆分 | 开户审批(发起+审批+归档) |
| **报表统计** | XX报表 | 2-5 | 独立功能点 | 月度交易统计报表 |
| **接口开发** | 对接XX系统 | 1-3 | 独立功能点 | 征信接口对接 |
| **批量处理** | 批量XX | 2-4 | 独立功能点 | 批量转账 |
| **数据迁移** | 迁移XX数据 | 3-8 | 独立功能点(工时单算) | 历史账户数据迁移 |

**拆分规则**:
```markdown
规则1: 每个功能点应该是独立可测试的单元
规则2: 复合功能 = 1个主功能 + N个子功能
       示例: "客户管理" → "客户查询"+"客户创建"+"客户编辑"+"客户删除"
规则3: 跨系统交互单独列为功能点
       示例: "调用征信接口"应独立于"客户创建"
规则4: 数据迁移/性能优化/安全加固作为独立功能点
规则5: 功能点粒度: 0.5-5人天(超过5人天需拆分)
```

**实施步骤**:

```python
# Step 1: 建立功能模板库
# backend/data/feature_templates.json

FEATURE_TEMPLATES = [
    {
        "template_id": "TPL_QUERY_001",
        "template_name": "单表查询",
        "category": "查询类",
        "typical_days_range": [0.5, 1.0],
        "avg_days": 0.8,
        "complexity_mapping": {"低": 0.5, "中": 0.8, "高": 1.0},
        "keywords": ["查询", "检索", "搜索", "获取"],
        "description": "从单表查询数据,包含条件查询",
        "typical_inputs": ["查询条件"],
        "typical_outputs": ["查询结果列表"],
        "typical_dependencies": [],
        "risk_points": ["性能问题(数据量大)"],
        "estimation_rules": {
            "base": 0.8,
            "factors": {
                "复杂查询条件(>5个)": 0.2,
                "多表关联": 0.3,
                "数据量大(>10万)": 0.2
            }
        }
    },
    {
        "template_id": "TPL_LIST_001",
        "template_name": "列表展示",
        "category": "查询类",
        "typical_days_range": [1.0, 2.0],
        "avg_days": 1.5,
        "keywords": ["列表", "清单", "分页", "排序", "筛选"],
        "estimation_rules": {
            "base": 1.2,
            "factors": {
                "分页": 0.1,
                "排序": 0.1,
                "高级筛选": 0.3,
                "导出功能": 0.2
            }
        }
    },
    {
        "template_id": "TPL_CREATE_001",
        "template_name": "单表新增",
        "category": "写入类",
        "typical_days_range": [1.0, 2.0],
        "avg_days": 1.5,
        "keywords": ["新增", "创建", "录入", "添加"],
        "estimation_rules": {
            "base": 1.2,
            "factors": {
                "表单字段多(>15个)": 0.3,
                "数据校验复杂": 0.3,
                "关联数据处理": 0.2,
                "文件上传": 0.3
            }
        }
    },
    {
        "template_id": "TPL_APPROVAL_001",
        "template_name": "审批流程",
        "category": "流程类",
        "typical_days_range": [2.0, 4.0],
        "avg_days": 3.0,
        "keywords": ["审批", "审核", "流程", "工作流"],
        "description": "包含发起、审批、驳回、归档等环节",
        "estimation_rules": {
            "base": 2.0,
            "factors": {
                "审批节点": 0.5,  // 每增加1个节点
                "条件分支": 0.3,  // 每个条件分支
                "会签": 0.5,
                "超时处理": 0.3
            }
        }
    },
    {
        "template_id": "TPL_REPORT_001",
        "template_name": "报表统计",
        "category": "报表类",
        "typical_days_range": [2.0, 5.0],
        "avg_days": 3.5,
        "keywords": ["报表", "统计", "汇总", "分析"],
        "estimation_rules": {
            "base": 2.5,
            "factors": {
                "多维度统计": 0.5,
                "复杂计算逻辑": 0.8,
                "图表展示": 0.3,
                "数据量大": 0.5
            }
        }
    },
    {
        "template_id": "TPL_INTERFACE_001",
        "template_name": "接口开发",
        "category": "接口类",
        "typical_days_range": [1.0, 3.0],
        "avg_days": 2.0,
        "keywords": ["接口", "对接", "集成", "调用"],
        "estimation_rules": {
            "base": 1.5,
            "factors": {
                "新建接口": 0.5,
                "改造已有接口": 0.3,
                "复杂报文转换": 0.5,
                "高频接口(性能要求)": 0.3,
                "联调测试": 0.5  // 基础联调
            }
        }
    },
    {
        "template_id": "TPL_BATCH_001",
        "template_name": "批量处理",
        "category": "批处理类",
        "typical_days_range": [2.0, 4.0],
        "avg_days": 3.0,
        "keywords": ["批量", "批处理", "定时任务", "跑批"],
        "estimation_rules": {
            "base": 2.0,
            "factors": {
                "数据量大(>10万)": 0.8,
                "复杂业务逻辑": 0.5,
                "异常处理/重试": 0.3,
                "断点续传": 0.5
            }
        }
    },
    {
        "template_id": "TPL_MIGRATION_001",
        "template_name": "数据迁移",
        "category": "迁移类",
        "typical_days_range": [3.0, 8.0],
        "avg_days": 5.0,
        "keywords": ["迁移", "导入", "历史数据"],
        "estimation_rules": {
            "base": 3.0,
            "factors": {
                "数据量大(>100万)": 1.5,
                "数据清洗复杂": 1.0,
                "数据校验": 0.8,
                "回滚机制": 0.5
            }
        }
    }
]
```

```python
# Step 2: 导入功能模板到知识库
# backend/scripts/import_feature_templates.py

def import_feature_templates():
    """导入功能模板到知识库"""
    knowledge_service = get_knowledge_service()
    
    for template in FEATURE_TEMPLATES:
        # 构建检索文本
        content = f"""
功能模板: {template['template_name']}
分类: {template['category']}
典型描述: {template['description']}
关键词: {', '.join(template['keywords'])}
基准人天: {template['avg_days']}
人天范围: {template['typical_days_range'][0]}-{template['typical_days_range'][1]}
        """.strip()
        
        embedding = knowledge_service.embedding_service.generate_embedding(content)
        
        knowledge_service.vector_store.insert_knowledge({
            'system_name': '通用',  # 功能模板不特定于系统
            'knowledge_type': 'feature_template',
            'content': content,
            'embedding': embedding,
            'metadata': template,
            'source_file': 'feature_templates.json'
        })
    
    print(f"导入 {len(FEATURE_TEMPLATES)} 个功能模板")
```

**产出**:
- ✅ 功能分类体系(8大类)
- ✅ 功能模板库(初始8个,后续扩展)
- ✅ 拆分规则文档

---

### 🚀 阶段二: Agent优化（Week 2-3）

#### 任务2.1: 系统识别Agent增强

**优化策略**: 接口规范优先 + 系统画像参考 + 置信度标注

```python
# backend/agent/system_identification_agent.py

def identify_with_confidence(self, requirement_content: str, task_id: Optional[str] = None):
    """系统识别(带置信度)"""
    
    # Step 1: 检索接口规范(P0优先级)
    interface_specs = self.knowledge_service.search_similar_knowledge(
        query_text=requirement_content,
        knowledge_type="interface_spec",
        top_k=15,
        similarity_threshold=0.65,
        task_id=task_id,
        stage="system_identification_interface"
    )
    
    # Step 2: 从接口推断系统(高置信度)
    interface_inferred_systems = self._infer_systems_from_interfaces(interface_specs)
    
    # Step 3: 检索系统画像(P1优先级)
    system_profiles = self.knowledge_service.search_similar_knowledge(
        query_text=requirement_content,
        knowledge_type="system_profile",
        top_k=8,
        similarity_threshold=0.6,
        task_id=task_id,
        stage="system_identification_profile"
    )
    
    # Step 4: 构建候选系统榜单
    candidate_systems = self._build_candidate_systems(system_profiles, limit=8)
    
    # Step 5: LLM综合判断
    prompt = self._build_identification_prompt(
        requirement_content,
        interface_inferred_systems,
        candidate_systems,
        system_profiles
    )
    
    response = llm_client.chat_with_system_prompt(
        system_prompt=SYSTEM_IDENTIFICATION_PROMPT_V3,
        user_prompt=prompt,
        temperature=0.3
    )
    
    result = llm_client.extract_json(response)
    systems = result["systems"]
    
    # Step 6: 置信度标注
    for system in systems:
        # 根据证据来源计算置信度分数
        confidence_score = self._calculate_confidence_score(
            system=system,
            interface_evidence=interface_inferred_systems,
            profile_evidence=candidate_systems
        )
        
        system["confidence_score"] = confidence_score
        system["confidence_level"] = self._score_to_level(confidence_score)
        system["evidence"] = self._collect_evidence(system, interface_specs, system_profiles)
    
    return systems


def _calculate_confidence_score(self, system, interface_evidence, profile_evidence):
    """
    计算置信度分数(0-100)
    
    权重:
    - ESB接口证据: 60%
    - 系统画像证据: 30%
    - LLM推理: 10%
    """
    score = 0.0
    
    # 接口证据权重(60%)
    interface_match = next((s for s in interface_evidence if s['system_name'] == system['name']), None)
    if interface_match:
        interface_count = interface_match.get('interface_count', 0)
        avg_similarity = interface_match.get('confidence_score', 0.0)
        score += min(60, interface_count * 15 + avg_similarity * 30)
    
    # 系统画像证据权重(30%)
    profile_match = next((s for s in profile_evidence if s['name'] == system['name']), None)
    if profile_match:
        profile_score = profile_match.get('score', 0.0)
        score += profile_score * 30
    
    # LLM推理权重(10%)
    llm_confidence = {'高': 10, '中': 6, '低': 3}.get(system.get('confidence', '中'), 6)
    score += llm_confidence
    
    return min(100, score)


def _score_to_level(self, score):
    """置信度分数转级别"""
    if score >= 80:
        return "高"
    elif score >= 60:
        return "中"
    else:
        return "低"


def _collect_evidence(self, system, interface_specs, system_profiles):
    """收集证据明细"""
    evidence = {
        "interface_evidence": [],
        "profile_evidence": [],
        "reasoning": system.get('reasons', [])
    }
    
    # 收集接口证据
    system_name = system['name']
    for spec in interface_specs:
        metadata = spec.get('metadata', {})
        if metadata.get('provider_system') == system_name or system_name in metadata.get('consumer_systems', []):
            evidence["interface_evidence"].append({
                "interface_name": metadata.get('interface_name'),
                "interface_code": metadata.get('interface_code'),
                "category": metadata.get('category'),
                "similarity": spec.get('similarity', 0.0),
                "role": "提供方" if metadata.get('provider_system') == system_name else "调用方"
            })
    
    # 收集系统画像证据
    for profile in system_profiles:
        profile_system = profile.get('system_name') or profile.get('metadata', {}).get('system_name')
        if profile_system == system_name:
            evidence["profile_evidence"].append({
                "source_file": profile.get('source_file'),
                "similarity": profile.get('similarity', 0.0),
                "excerpt": profile.get('content', '')[:150]
            })
    
    return evidence
```

**Prompt优化**:

```python
SYSTEM_IDENTIFICATION_PROMPT_V3 = """
你是银行系统架构专家,负责从需求文档中识别涉及的所有系统。

【识别策略(按优先级)】

1. **ESB接口规范优先** ⭐⭐⭐ (置信度权重: 60%)
   - 如果【接口规范推断】中显示某系统提供/调用了需求相关的接口,优先识别该系统
   - 接口数据来自ESB服务治理,准确度最高
   - 提供方系统(提供接口): 置信度"高"
   - 调用方系统(调用接口): 置信度"中"或"高"
   
   示例:
   需求提到"账户余额查询"
   接口规范显示: "新一代核心"提供API_ACC_001(账户查询)接口
   → 识别"新一代核心",置信度"高"

2. **系统画像参考** ⭐⭐ (置信度权重: 30%)
   - 结合【候选系统榜单】和【系统知识参考】中的系统边界判断
   - 系统边界(in_scope/out_of_scope)清晰: 置信度"中"
   - 系统边界模糊: 置信度"低"

3. **关键词推测** ⭐ (置信度权重: 10%)
   - 仅当前两种方式都无法识别时使用
   - 置信度必须标为"低"

【置信度标注规则】

- **高置信度**: 有明确ESB接口证据,且接口数量≥2
- **中置信度**: 有1个接口证据,或有系统画像支持但无接口证据
- **低置信度**: 仅关键词推测,无接口或画像证据

【输出格式】

{
  "systems": [
    {
      "name": "系统名称",
      "type": "主系统" / "依赖系统",
      "confidence": "高" / "中" / "低",
      "reasons": [
        "[ESB接口] 提供3个相关接口: API_ACC_001(账户查询,相似度0.92), ...",
        "[系统画像] 系统边界包含账户管理功能(相似度0.85)"
      ],
      "description": "系统在本需求中的作用"
    }
  ],
  "maybe_systems": [
    {
      "name": "可能涉及的系统",
      "confidence": "低",
      "reason": "需求提到XX,但无明确接口证据,建议澄清"
    }
  ],
  "questions": [
    "是否需要调用征信系统?(未检测到征信相关接口)",
    "是否涉及跨行转账?(需确认是否调用人行接口)"
  ]
}

【注意事项】
1. 优先依赖ESB接口规范,其次才是系统画像
2. 如果接口规范和系统画像冲突,以接口规范为准(接口是实际运行的)
3. 置信度标注必须准确,低置信度系统建议澄清
4. reasons字段必须标注证据来源: [ESB接口] / [系统画像] / [关键词]
"""
```

---

#### 任务2.2: 功能拆分Agent增强

**优化策略**: 模板匹配 + 规则化拆分 + 接口依赖推断

```python
# backend/agent/feature_breakdown_agent.py

def breakdown_with_template(
    self, 
    requirement_content: str, 
    system_name: str,
    system_type: str = "主系统",
    task_id: Optional[str] = None
):
    """功能拆分(基于模板)"""
    
    # Step 1: 检索功能模板
    feature_templates = self.knowledge_service.search_similar_knowledge(
        query_text=requirement_content,
        knowledge_type="feature_template",
        top_k=10,
        similarity_threshold=0.6,
        task_id=task_id,
        stage="feature_breakdown_template"
    )
    
    # Step 2: 检索接口规范(用于推断依赖)
    interface_specs = self.knowledge_service.search_similar_knowledge(
        query_text=requirement_content,
        system_name=system_name,
        knowledge_type="interface_spec",
        top_k=15,
        similarity_threshold=0.6,
        task_id=task_id,
        stage="feature_breakdown_interface"
    )
    
    # Step 3: 检索系统画像(系统边界)
    system_profiles = self.knowledge_service.search_similar_knowledge(
        query_text=requirement_content,
        system_name=system_name,
        knowledge_type="system_profile",
        top_k=3,
        similarity_threshold=0.6,
        task_id=task_id,
        stage="feature_breakdown_profile"
    )
    
    # Step 4: 构建增强Prompt
    prompt = self._build_breakdown_prompt_v3(
        requirement_content,
        system_name,
        system_type,
        feature_templates,
        interface_specs,
        system_profiles
    )
    
    response = llm_client.chat_with_system_prompt(
        system_prompt=FEATURE_BREAKDOWN_PROMPT_V3,
        user_prompt=prompt,
        temperature=0.5,
        max_tokens=4000
    )
    
    result = llm_client.extract_json(response)
    features = result["features"]
    
    # Step 5: 基于模板优化预估人天
    features = self._apply_template_estimation(features, feature_templates)
    
    # Step 6: 基于接口推断依赖系统
    features = self._infer_dependencies_from_interfaces(features, interface_specs)
    
    # Step 7: 专业估算Agent重新评估
    estimation_agent = WorkloadEstimationAgent(self.knowledge_service)
    for feature in features:
        estimation = estimation_agent.estimate_with_multi_factors(
            feature=feature,
            system_name=system_name,
            matched_template=feature.get('matched_template')
        )
        feature.update(estimation)
    
    return features


def _apply_template_estimation(self, features, templates):
    """基于模板优化估算"""
    
    # 构建模板索引
    template_index = {}
    for template in templates:
        metadata = template.get('metadata', {})
        template_id = metadata.get('template_id')
        if template_id:
            template_index[template_id] = {
                'metadata': metadata,
                'similarity': template.get('similarity', 0.0)
            }
    
    for feature in features:
        # 检查是否匹配了模板
        matched_template_id = feature.get('matched_template')
        
        if matched_template_id and matched_template_id in template_index:
            template_info = template_index[matched_template_id]
            template = template_info['metadata']
            similarity = template_info['similarity']
            
            # 使用模板的估算规则
            estimation_rules = template.get('estimation_rules', {})
            base_days = estimation_rules.get('base', template.get('avg_days', 2.0))
            factors = estimation_rules.get('factors', {})
            
            # 计算调整因子
            adjustment = 0.0
            applied_factors = []
            
            # 检查feature的描述/备注中是否包含因子关键词
            feature_text = f"{feature.get('业务描述', '')} {feature.get('备注', '')}"
            
            for factor_name, factor_value in factors.items():
                # 简单关键词匹配(可优化为语义匹配)
                if any(keyword in feature_text for keyword in factor_name.split('(')):
                    adjustment += factor_value
                    applied_factors.append(factor_name)
            
            # 应用模板估算
            template_days = base_days + adjustment
            
            # 与AI初估加权平均(模板70% + AI 30%)
            ai_days = feature.get('预估人天', base_days)
            final_days = template_days * 0.7 + ai_days * 0.3
            
            # 更新功能点
            feature['预估人天'] = round(final_days, 1)
            feature['模板基准人天'] = base_days
            feature['模板调整因子'] = applied_factors
            feature['置信度'] = '高' if similarity >= 0.75 else '中'
            feature['估算依据'] = f"模板匹配({template['template_name']}, 相似度{similarity:.0%})"
        else:
            # 未匹配模板,置信度降低
            feature['置信度'] = '中' if feature.get('复杂度') in ['低', '中'] else '低'
            feature['估算依据'] = "基于复杂度基准估算(无匹配模板)"
    
    return features


def _infer_dependencies_from_interfaces(self, features, interface_specs):
    """从接口推断依赖系统"""
    
    # 构建接口索引: 接口名称/分类 -> 接口元数据
    interface_index = {}
    for spec in interface_specs:
        metadata = spec.get('metadata', {})
        interface_name = metadata.get('interface_name', '')
        category = metadata.get('category', '')
        
        if interface_name:
            interface_index[interface_name] = metadata
        if category:
            interface_index[category] = metadata
    
    for feature in features:
        # 分析功能点是否涉及接口
        feature_text = f"{feature.get('功能点', '')} {feature.get('业务描述', '')} {feature.get('备注', '')}"
        
        matched_interfaces = []
        inferred_deps = set()
        
        # 关键词匹配
        for key, metadata in interface_index.items():
            if key in feature_text:
                matched_interfaces.append(metadata)
                # 推断依赖系统
                provider = metadata.get('provider_system')
                consumers = metadata.get('consumer_systems', [])
                
                # 调用方系统成为依赖项
                if provider:
                    inferred_deps.add(provider)
                inferred_deps.update(consumers)
        
        if matched_interfaces:
            # 补充依赖项
            existing_deps = feature.get('依赖项', '').split(',')
            existing_deps = set(d.strip() for d in existing_deps if d.strip() and d.strip() not in ['无', '-'])
            
            all_deps = existing_deps | inferred_deps
            feature['依赖项'] = ', '.join(sorted(all_deps))
            
            # 补充接口证据
            interface_codes = [m.get('interface_code', '') for m in matched_interfaces if m.get('interface_code')]
            if interface_codes and '[相关接口]' not in feature.get('备注', ''):
                feature['备注'] = f"{feature.get('备注', '')}\n[相关接口] {', '.join(interface_codes[:3])}".strip()
            
            # 记录匹配的接口(用于联调工作量估算)
            feature['_matched_interfaces'] = matched_interfaces
    
    return features
```

**Prompt优化**:

```python
FEATURE_BREAKDOWN_PROMPT_V3 = """
你是银行系统需求分析专家,负责将需求拆分为可执行的功能点。

【拆分策略】

1. **模板匹配优先** ⭐⭐⭐
   - 参考【功能模板】,优先使用已有模板
   - 如果需求功能与模板高度相似(>70%),直接引用模板并标注template_id
   - 模板提供了估算规则和典型人天范围,更准确

2. **遵循拆分规则** ⭐⭐⭐
   规则1: 每个功能点应该是独立可测试的单元
   规则2: 复合功能需拆分 (示例: "客户管理" → "客户查询"+"客户创建"+"客户编辑")
   规则3: 跨系统交互单独拆分 (示例: "调用征信接口"独立于"客户创建")
   规则4: 功能点粒度: 0.5-5人天 (超过5人天必须拆分)
   规则5: 数据迁移/性能优化/安全加固作为独立功能点

3. **基于接口推断依赖** ⭐⭐
   - 利用【相关接口参考(ESB)】推断该功能需要调用哪些系统
   - 接口提供方/调用方列入"依赖项"字段

4. **明确系统边界** ⭐⭐
   - 参考【系统知识】中的系统边界(in_scope/out_of_scope)
   - 只拆分属于当前系统的功能点

【输出格式】

{
  "features": [
    {
      "序号": "1.1",
      "功能模块": "账户管理",
      "功能点": "开立个人账户",
      "业务描述": "...",
      "输入": "...",
      "输出": "...",
      "预估人天": 2.0,
      "复杂度": "中",
      "依赖项": "客户信息系统, 征信系统",
      "备注": "[模板匹配] TPL_CREATE_001 | [归属依据] 系统边界明确 | [相关接口] API_ACC_001",
      
      // 新增字段
      "matched_template": "TPL_CREATE_001",  // 匹配的模板ID(如果有)
      "split_method": "模板匹配" / "规则拆分" / "新拆分",
      "confidence": "高" / "中" / "低"
    }
  ]
}

【注意事项】
1. 优先使用【功能模板】,模板覆盖的功能不要重新"发明"
2. 备注字段必须包含: [模板匹配/规则拆分/新拆分] [归属依据] [相关接口] [待确认]
3. 复杂度必须合理: 低(0.5-1.5人天) 中(1.5-3.5人天) 高(3.5-5人天)
4. 依赖项必须准确,优先从【相关接口参考】中推断
"""
```

---

#### 任务2.3: 工作量估算Agent优化

**优化策略**: 多因子估算 + 接口联调分析 + 置信区间

```python
# backend/agent/workload_estimation_agent.py

class WorkloadEstimationAgent:
    """工作量估算Agent(多因子模型)"""
    
    def estimate_with_multi_factors(
        self, 
        feature: Dict, 
        system_name: str,
        matched_template: Optional[Dict] = None
    ) -> Dict:
        """
        多因子估算
        
        因子:
        1. 模板基准人天(如果有)
        2. 接口联调工作量
        3. 依赖系统数量
        4. 复杂度
        5. 风险系数
        """
        
        # 因子1: 基础工作量
        if matched_template:
            # 有模板,使用模板规则
            base_days = feature.get('模板基准人天', 2.0)
            source = "模板基准"
        else:
            # 无模板,按复杂度
            complexity = feature.get('复杂度', '中')
            base_days = {'低': 1.2, '中': 2.5, '高': 4.5}[complexity]
            source = "复杂度基准"
        
        # 因子2: 接口联调工作量
        integration_days, interface_details = self._estimate_integration_effort(feature)
        
        # 因子3: 依赖系统数量(除接口外的额外协调成本)
        deps = feature.get('依赖项', '').split(',')
        dep_count = len([d for d in deps if d.strip() and d.strip() not in ['无', '-']])
        coordination_days = max(0, (dep_count - len(interface_details)) * 0.2)  # 无接口的依赖,按0.2人天/个
        
        # 因子4: 风险系数
        risk_factor = self._calculate_risk_factor(feature)
        
        # 总工作量
        total_days = (base_days + integration_days + coordination_days) * risk_factor
        
        # 置信区间(±20%)
        confidence_interval = [
            round(total_days * 0.8, 1),
            round(total_days * 1.2, 1)
        ]
        
        # 置信度评级
        confidence_level = self._calculate_confidence_level(
            has_template=bool(matched_template),
            has_interface=len(interface_details) > 0,
            complexity=feature.get('复杂度', '中')
        )
        
        return {
            '预估人天': round(total_days, 1),
            '置信区间': confidence_interval,
            '置信度': confidence_level,
            '估算细节': {
                '基础工作量': {
                    '人天': base_days,
                    '来源': source
                },
                '接口联调': {
                    '人天': round(integration_days, 1),
                    '接口数': len(interface_details),
                    '明细': interface_details
                },
                '协调成本': {
                    '人天': round(coordination_days, 1),
                    '依赖系统数': dep_count
                },
                '风险系数': risk_factor,
                '风险说明': self._explain_risk_factor(feature, risk_factor)
            },
            '估算说明': self._build_estimation_summary(
                base_days, integration_days, coordination_days, risk_factor, source
            )
        }
    
    
    def _estimate_integration_effort(self, feature: Dict) -> Tuple[float, List[Dict]]:
        """
        估算接口联调工作量
        
        规则:
        - 新建接口: 0.8人天/个
        - 改造已有接口: 0.3人天/个
        - 高频接口: +0.2人天
        - 联调测试基础: 1.0人天(如果有接口)
        """
        matched_interfaces = feature.get('_matched_interfaces', [])
        
        if not matched_interfaces:
            return 0.0, []
        
        integration_days = 1.0  # 基础联调工作量
        interface_details = []
        
        for interface in matched_interfaces:
            interface_name = interface.get('interface_name', '')
            interface_code = interface.get('interface_code', '')
            call_frequency = interface.get('call_frequency', '中')
            
            # 判断是新建还是改造(简单规则: 如果备注中有"新建"/"新增")
            is_new = '新建' in feature.get('备注', '') or '新增' in feature.get('备注', '')
            
            if is_new:
                days = 0.8
            else:
                days = 0.3
            
            # 高频接口额外增加
            if call_frequency == '高':
                days += 0.2
            
            integration_days += days
            
            interface_details.append({
                'interface_name': interface_name,
                'interface_code': interface_code,
                'call_frequency': call_frequency,
                'type': '新建' if is_new else '改造',
                'days': round(days, 1)
            })
        
        return integration_days, interface_details
    
    
    def _calculate_risk_factor(self, feature: Dict) -> float:
        """
        计算风险系数(1.0-1.5)
        
        风险因素:
        - 新建功能: +0.2
        - 复杂度高: +0.1
        - 依赖系统多(>3): +0.1
        - 数据迁移/性能/安全: +0.1
        """
        risk_factor = 1.0
        
        remark = feature.get('备注', '')
        
        # 新建功能
        if '新建' in remark or '新增' in remark:
            risk_factor += 0.2
        
        # 复杂度高
        if feature.get('复杂度') == '高':
            risk_factor += 0.1
        
        # 依赖系统多
        deps = feature.get('依赖项', '').split(',')
        dep_count = len([d for d in deps if d.strip() and d.strip() not in ['无', '-']])
        if dep_count > 3:
            risk_factor += 0.1
        
        # 特殊类型
        special_keywords = ['迁移', '性能', '安全', '加密', '合规']
        if any(k in remark or k in feature.get('功能点', '') for k in special_keywords):
            risk_factor += 0.1
        
        return min(risk_factor, 1.5)
    
    
    def _calculate_confidence_level(self, has_template, has_interface, complexity) -> str:
        """计算置信度级别"""
        if has_template and has_interface:
            return '高'
        elif has_template or has_interface:
            return '中'
        elif complexity in ['低', '中']:
            return '中'
        else:
            return '低'
    
    
    def _explain_risk_factor(self, feature, risk_factor) -> str:
        """解释风险系数"""
        if risk_factor <= 1.0:
            return "无特殊风险"
        
        explanations = []
        remark = feature.get('备注', '')
        
        if '新建' in remark or '新增' in remark:
            explanations.append("新建功能")
        if feature.get('复杂度') == '高':
            explanations.append("复杂度高")
        
        deps = feature.get('依赖项', '').split(',')
        dep_count = len([d for d in deps if d.strip() and d.strip() not in ['无', '-']])
        if dep_count > 3:
            explanations.append(f"依赖系统多({dep_count}个)")
        
        special_keywords = ['迁移', '性能', '安全']
        for k in special_keywords:
            if k in remark or k in feature.get('功能点', ''):
                explanations.append(f"涉及{k}")
        
        return ", ".join(explanations)
    
    
    def _build_estimation_summary(
        self, base_days, integration_days, coordination_days, risk_factor, source
    ) -> str:
        """构建估算说明"""
        parts = [f"{source} {base_days:.1f}人天"]
        
        if integration_days > 0:
            parts.append(f"接口联调 {integration_days:.1f}人天")
        
        if coordination_days > 0:
            parts.append(f"协调成本 {coordination_days:.1f}人天")
        
        if risk_factor > 1.0:
            parts.append(f"风险系数 ×{risk_factor:.1f}")
        
        return " + ".join(parts)
```

---

### 🚀 阶段三: 黄金数据集建设（Week 3-4）

**灵感来源**: enhance_v3.md 的核心理念

#### 任务3.1: 黄金数据集定义与标准

**目标**: 建立50-100个高质量评估案例作为标杆

**选择标准**(来自enhance_v3.md):

| 标准 | 说明 | 权重 |
|------|------|------|
| **专家一致性高** | 多个专家评估结果接近(偏差<10%) | 30% |
| **实际偏差小** | 预估vs实际偏差<15% | 30% |
| **覆盖典型场景** | CRUD/审批/报表/接口/批处理/迁移等 | 20% |
| **需求文档完整** | 有完整的原始需求文档 | 20% |

**数据结构**:

```json
{
  "case_id": "GOLDEN_CASE_001",
  "project_name": "XX银行客户管理系统改造",
  "requirement_doc": "完整需求文档(原文)",
  "requirement_summary": "需求摘要(200字)",
  
  "expert_evaluation": {
    "expert_name": "张三",
    "evaluation_date": "2025-12-01",
    "systems": [
      {
        "system_name": "客户管理系统",
        "type": "主系统",
        "confidence": "高",
        "reasons": ["系统边界明确", "有接口证据"]
      }
    ],
    "features": [
      {
        "feature_id": "F001",
        "module": "客户管理",
        "feature_name": "客户信息查询",
        "description": "...",
        "estimated_days": 1.0,
        "complexity": "低",
        "dependencies": [],
        "template_used": "TPL_QUERY_001"
      }
    ],
    "total_days": 15.5
  },
  
  "actual_execution": {
    "start_date": "2025-12-15",
    "end_date": "2026-01-05",
    "actual_total_days": 16.2,
    "features_actual": [
      {
        "feature_id": "F001",
        "actual_days": 1.2,
        "deviation_rate": 0.2,
        "deviation_reason": "数据量比预期大"
      }
    ]
  },
  
  "quality_metrics": {
    "expert_consistency_score": 0.95,  // 专家一致性分数
    "actual_deviation_rate": 0.045,    // 实际偏差率
    "feature_coverage": ["查询", "创建", "编辑"],
    "overall_quality_score": 0.92      // 综合质量分数
  },
  
  "lessons_learned": [
    "客户数据量评估不准,建议增加数据量确认环节",
    "接口联调比预期顺利,接口文档准确"
  ]
}
```

#### 任务3.2: 黄金数据集收集流程

**流程设计**:

```
Step 1: 筛选候选案例
├─ 标准1: 最近1年内完成的项目
├─ 标准2: 有完整需求文档
├─ 标准3: 专家评估过的项目
└─ 目标: 筛选出100个候选案例

Step 2: 专家Review与评分
├─ 专家填写评估表单
├─ 多专家评估对比(至少2人)
├─ 计算一致性分数
└─ 过滤: 一致性<0.8的案例淘汰

Step 3: 补充实际执行数据
├─ 从项目管理系统获取实际工时
├─ 计算偏差率
└─ 过滤: 偏差>20%的案例淘汰

Step 4: 标注与入库
├─ 人工标注功能点类型(匹配功能模板)
├─ 标注依赖关系
├─ 导入到知识库(knowledge_type: golden_case)
└─ 产出: 50-100个黄金案例
```

**实施工具**:

```python
# backend/scripts/golden_case_builder.py

class GoldenCaseBuilder:
    """黄金数据集构建工具"""
    
    def collect_candidate_cases(self, project_list: List[str]) -> List[Dict]:
        """Step 1: 收集候选案例"""
        candidates = []
        
        for project_name in project_list:
            # 检查是否有完整数据
            has_requirement = self._check_requirement_doc(project_name)
            has_evaluation = self._check_expert_evaluation(project_name)
            has_actual = self._check_actual_execution(project_name)
            
            if has_requirement and has_evaluation:
                candidates.append({
                    'project_name': project_name,
                    'has_requirement': has_requirement,
                    'has_evaluation': has_evaluation,
                    'has_actual': has_actual,
                    'quality_score': 0.0  # 待计算
                })
        
        return candidates
    
    
    def calculate_quality_score(self, case: Dict) -> float:
        """Step 2: 计算质量分数"""
        
        # 专家一致性(如果有多个专家评估)
        consistency_score = self._calculate_expert_consistency(case)
        
        # 实际偏差率(如果有实际数据)
        deviation_score = self._calculate_deviation_score(case)
        
        # 需求文档完整性
        completeness_score = self._calculate_completeness_score(case)
        
        # 综合分数
        quality_score = (
            consistency_score * 0.4 +
            deviation_score * 0.3 +
            completeness_score * 0.3
        )
        
        return quality_score
    
    
    def annotate_and_import(self, case: Dict):
        """Step 4: 标注并导入"""
        
        # 自动标注功能点类型
        for feature in case['expert_evaluation']['features']:
            # 匹配功能模板
            matched_template = self._match_feature_template(feature)
            if matched_template:
                feature['template_id'] = matched_template['template_id']
                feature['template_name'] = matched_template['template_name']
        
        # 导入到知识库
        knowledge_service = get_knowledge_service()
        
        content = self._build_golden_case_content(case)
        embedding = knowledge_service.embedding_service.generate_embedding(content)
        
        knowledge_service.vector_store.insert_knowledge({
            'system_name': case['expert_evaluation']['systems'][0]['system_name'],
            'knowledge_type': 'golden_case',
            'content': content,
            'embedding': embedding,
            'metadata': case,
            'source_file': 'golden_case_dataset'
        })
```

#### 任务3.3: 黄金数据集应用

**应用场景1: 相似案例推荐** (来自enhance_v3.md)

```python
# backend/agent/case_recommendation_agent.py

class CaseRecommendationAgent:
    """相似案例推荐Agent"""
    
    def recommend_similar_cases(
        self, 
        requirement_content: str,
        system_name: str,
        top_k: int = 3
    ) -> List[Dict]:
        """
        推荐相似案例
        
        输出格式(来自enhance_v3.md):
        当前需求: XX
        
        相似案例1: XX项目(总15人天) - 相似度85%
        差异点:
          - 你的是"客户管理",案例是"会员管理" → 无差异
          - 你的有"数据迁移",案例没有 → +3人天
        
        综合建议: 15±3人天, 置信度85%
        """
        
        # 检索黄金案例
        golden_cases = self.knowledge_service.search_similar_knowledge(
            query_text=requirement_content,
            system_name=system_name,
            knowledge_type="golden_case",
            top_k=top_k,
            similarity_threshold=0.6
        )
        
        recommendations = []
        
        for case in golden_cases:
            metadata = case.get('metadata', {})
            similarity = case.get('similarity', 0.0)
            
            # 分析差异点
            differences = self._analyze_differences(
                requirement_content,
                metadata.get('requirement_summary', '')
            )
            
            # 计算调整建议
            adjustment = self._calculate_adjustment(differences)
            
            expert_total = metadata.get('expert_evaluation', {}).get('total_days', 0)
            actual_total = metadata.get('actual_execution', {}).get('actual_total_days', expert_total)
            
            recommendations.append({
                'case_id': metadata.get('case_id'),
                'project_name': metadata.get('project_name'),
                'similarity': similarity,
                'expert_estimated_days': expert_total,
                'actual_days': actual_total,
                'differences': differences,
                'adjustment': adjustment,
                'suggested_range': [
                    round(actual_total + adjustment['min'], 1),
                    round(actual_total + adjustment['max'], 1)
                ]
            })
        
        return recommendations
    
    
    def _analyze_differences(self, current_req: str, case_req: str) -> List[Dict]:
        """分析差异点(使用LLM)"""
        
        prompt = f"""
        对比两个需求,找出关键差异点:
        
        当前需求: {current_req[:500]}
        参考案例: {case_req[:500]}
        
        请列出:
        1. 功能范围差异(当前有但案例没有,或反之)
        2. 复杂度差异(当前更复杂/更简单)
        3. 系统数量差异
        
        输出格式:
        [
          {{"type": "功能增加", "description": "当前需求包含数据迁移,案例没有", "impact": "+3人天"}},
          {{"type": "复杂度降低", "description": "当前是单表查询,案例是多表关联", "impact": "-1人天"}}
        ]
        """
        
        response = llm_client.chat(prompt, temperature=0.3)
        differences = llm_client.extract_json(response)
        
        return differences
    
    
    def _calculate_adjustment(self, differences: List[Dict]) -> Dict:
        """计算调整建议"""
        total_adjustment = 0.0
        
        for diff in differences:
            impact_str = diff.get('impact', '0人天')
            # 解析: "+3人天" / "-1人天"
            match = re.search(r'([+-]?\d+\.?\d*)', impact_str)
            if match:
                total_adjustment += float(match.group(1))
        
        return {
            'total': total_adjustment,
            'min': total_adjustment * 0.8,
            'max': total_adjustment * 1.2
        }
```

**应用场景2: 多模型集成评估** (来自enhance_v3.md)

```python
# backend/agent/multi_model_estimator.py

class MultiModelEstimator:
    """多模型集成评估器"""
    
    def estimate_with_ensemble(
        self,
        requirement_content: str,
        system_name: str,
        features: List[Dict]
    ) -> Dict:
        """
        多模型集成评估
        
        模型权重(来自enhance_v3.md):
        - 相似案例匹配: 40%
        - 规则引擎(模板): 30%
        - LLM理解: 30%
        """
        
        results = []
        
        for feature in features:
            # 模型1: 相似案例匹配(40%)
            case_recommendation = self.case_agent.recommend_similar_cases(
                requirement_content=feature.get('业务描述', ''),
                system_name=system_name,
                top_k=3
            )
            
            if case_recommendation:
                case_days = np.mean([c['actual_days'] for c in case_recommendation])
                case_confidence = np.mean([c['similarity'] for c in case_recommendation])
            else:
                case_days = None
                case_confidence = 0.0
            
            # 模型2: 规则引擎(模板)(30%)
            template_days = feature.get('模板基准人天')
            template_confidence = 0.9 if feature.get('matched_template') else 0.0
            
            # 模型3: LLM预测(30%)
            llm_days = feature.get('预估人天')
            llm_confidence = 0.7  # LLM固定置信度
            
            # 加权平均
            weights = []
            values = []
            
            if case_days and case_confidence > 0.6:
                weights.append(0.4 * case_confidence)
                values.append(case_days)
            
            if template_days and template_confidence > 0.6:
                weights.append(0.3 * template_confidence)
                values.append(template_days)
            
            if llm_days:
                weights.append(0.3 * llm_confidence)
                values.append(llm_days)
            
            # 归一化权重
            total_weight = sum(weights)
            if total_weight > 0:
                normalized_weights = [w / total_weight for w in weights]
                ensemble_days = sum(v * w for v, w in zip(values, normalized_weights))
            else:
                ensemble_days = llm_days
            
            # 综合置信度
            ensemble_confidence = (
                (case_confidence * 0.4 if case_days else 0) +
                (template_confidence * 0.3 if template_days else 0) +
                (llm_confidence * 0.3)
            ) / sum([
                0.4 if case_days else 0,
                0.3 if template_days else 0,
                0.3
            ])
            
            results.append({
                'feature': feature,
                'ensemble_days': round(ensemble_days, 1),
                'ensemble_confidence': round(ensemble_confidence, 2),
                'model_breakdown': {
                    'case_model': {
                        'days': case_days,
                        'confidence': case_confidence,
                        'weight': 0.4 if case_days else 0
                    },
                    'template_model': {
                        'days': template_days,
                        'confidence': template_confidence,
                        'weight': 0.3 if template_days else 0
                    },
                    'llm_model': {
                        'days': llm_days,
                        'confidence': llm_confidence,
                        'weight': 0.3
                    }
                }
            })
        
        return results
```

---

### 🚀 阶段四: 前端优化与置信度可视化（Week 4）

#### 任务4.1: 置信度可视化

**灵感来源**: enhance_v3.md 的"区间+置信度"理念

```javascript
// frontend/src/components/FeatureCard.js

function FeatureCard({ feature }) {
  const [showDetails, setShowDetails] = useState(false);
  
  // 置信度颜色
  const confidenceColor = {
    '高': 'success',
    '中': 'warning',
    '低': 'error'
  }[feature.置信度 || '中'];
  
  return (
    <Card>
      <CardContent>
        <Grid container spacing={2}>
          {/* 基本信息 */}
          <Grid item xs={8}>
            <Typography variant="h6">{feature.功能点}</Typography>
            <Typography variant="body2" color="text.secondary">
              {feature.业务描述}
            </Typography>
          </Grid>
          
          {/* 工作量估算 */}
          <Grid item xs={4}>
            <Box textAlign="right">
              <Typography variant="h5">
                {feature.预估人天} 人天
              </Typography>
              
              {/* 置信区间 */}
              {feature.置信区间 && (
                <Typography variant="caption" color="text.secondary">
                  区间: {feature.置信区间[0]}-{feature.置信区间[1]} 人天
                </Typography>
              )}
              
              {/* 置信度标签 */}
              <Chip 
                label={`置信度: ${feature.置信度}`}
                color={confidenceColor}
                size="small"
                sx={{ mt: 1 }}
              />
            </Box>
          </Grid>
        </Grid>
        
        {/* 估算依据(折叠) */}
        <Accordion expanded={showDetails} onChange={() => setShowDetails(!showDetails)}>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="subtitle2">
              📊 估算依据与置信度分析
            </Typography>
          </AccordionSummary>
          
          <AccordionDetails>
            <Stack spacing={2}>
              {/* 估算说明 */}
              <Alert severity="info">
                {feature.估算说明}
              </Alert>
              
              {/* 估算细节 */}
              {feature.估算细节 && (
                <TableContainer component={Paper} variant="outlined">
                  <Table size="small">
                    <TableBody>
                      <TableRow>
                        <TableCell>基础工作量</TableCell>
                        <TableCell align="right">
                          {feature.估算细节.基础工作量?.人天} 人天
                          <Typography variant="caption" display="block">
                            ({feature.估算细节.基础工作量?.来源})
                          </Typography>
                        </TableCell>
                      </TableRow>
                      
                      {feature.估算细节.接口联调?.人天 > 0 && (
                        <TableRow>
                          <TableCell>
                            接口联调
                            <Tooltip title={
                              <div>
                                {feature.估算细节.接口联调.明细?.map((iface, idx) => (
                                  <div key={idx}>
                                    {iface.interface_name} ({iface.type}): {iface.days}人天
                                  </div>
                                ))}
                              </div>
                            }>
                              <IconButton size="small">
                                <InfoIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          </TableCell>
                          <TableCell align="right">
                            {feature.估算细节.接口联调.人天} 人天
                            <Typography variant="caption" display="block">
                              ({feature.估算细节.接口联调.接口数}个接口)
                            </Typography>
                          </TableCell>
                        </TableRow>
                      )}
                      
                      {feature.估算细节.风险系数 > 1.0 && (
                        <TableRow>
                          <TableCell>
                            风险系数
                            <Typography variant="caption" display="block">
                              {feature.估算细节.风险说明}
                            </Typography>
                          </TableCell>
                          <TableCell align="right">
                            ×{feature.估算细节.风险系数}
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
              
              {/* 模板匹配信息 */}
              {feature.matched_template && (
                <Alert severity="success" icon={<CheckCircleIcon />}>
                  <AlertTitle>模板匹配</AlertTitle>
                  匹配功能模板: {feature.matched_template}
                  {feature.模板调整因子 && feature.模板调整因子.length > 0 && (
                    <Typography variant="caption" display="block" sx={{ mt: 1 }}>
                      应用调整因子: {feature.模板调整因子.join(', ')}
                    </Typography>
                  )}
                </Alert>
              )}
              
              {/* 接口证据 */}
              {feature.备注?.includes('[相关接口]') && (
                <Alert severity="info" icon={<ApiIcon />}>
                  <AlertTitle>接口证据(ESB)</AlertTitle>
                  {feature.备注.match(/\[相关接口\]([^\n]+)/)?.[1] || ''}
                </Alert>
              )}
              
              {/* 相似案例推荐 */}
              {feature.similar_cases && feature.similar_cases.length > 0 && (
                <Box>
                  <Typography variant="subtitle2" gutterBottom>
                    📚 相似历史案例
                  </Typography>
                  {feature.similar_cases.map((scase, idx) => (
                    <Card key={idx} variant="outlined" sx={{ mb: 1, p: 1 }}>
                      <Typography variant="body2">
                        <strong>{scase.project_name}</strong> (相似度: {(scase.similarity * 100).toFixed(0)}%)
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        专家评估: {scase.expert_estimated_days}人天 | 
                        实际: {scase.actual_days}人天
                      </Typography>
                      {scase.differences && scase.differences.length > 0 && (
                        <Box mt={0.5}>
                          <Typography variant="caption" color="text.secondary">
                            差异点:
                          </Typography>
                          {scase.differences.slice(0, 2).map((diff, didx) => (
                            <Typography key={didx} variant="caption" display="block">
                              • {diff.description} ({diff.impact})
                            </Typography>
                          ))}
                        </Box>
                      )}
                    </Card>
                  ))}
                </Box>
              )}
              
              {/* 置信度低的提示 */}
              {feature.置信度 === '低' && (
                <Alert severity="warning">
                  <AlertTitle>置信度较低</AlertTitle>
                  建议澄清需求细节后重新评估,或由专家人工复核。
                </Alert>
              )}
            </Stack>
          </AccordionDetails>
        </Accordion>
      </CardContent>
    </Card>
  );
}
```

#### 任务4.2: 系统识别结果增强

```javascript
// frontend/src/components/SystemIdentificationResult.js

function SystemIdentificationResult({ systems }) {
  return (
    <TableContainer component={Paper}>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>系统名称</TableCell>
            <TableCell>置信度</TableCell>
            <TableCell>证据来源</TableCell>
            <TableCell>操作</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {systems.map((system, idx) => (
            <TableRow key={idx}>
              <TableCell>
                <Typography variant="body1">
                  {system.name}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {system.type}
                </Typography>
              </TableCell>
              
              <TableCell>
                <Stack direction="row" spacing={1} alignItems="center">
                  <Chip 
                    label={system.confidence_level || system.confidence}
                    color={
                      (system.confidence_level || system.confidence) === '高' ? 'success' : 
                      (system.confidence_level || system.confidence) === '中' ? 'warning' : 
                      'error'
                    }
                    size="small"
                  />
                  {system.confidence_score && (
                    <Typography variant="caption">
                      ({system.confidence_score}分)
                    </Typography>
                  )}
                </Stack>
              </TableCell>
              
              <TableCell>
                <Stack spacing={0.5}>
                  {system.reasons?.map((reason, ridx) => (
                    <Typography key={ridx} variant="body2">
                      {reason.includes('[ESB接口]') && '🔌 '}
                      {reason.includes('[系统画像]') && '📄 '}
                      {reason.includes('[关键词]') && '🔍 '}
                      {reason}
                    </Typography>
                  ))}
                </Stack>
                
                {/* 证据明细(可展开) */}
                {system.evidence && (
                  <Accordion>
                    <AccordionSummary>
                      <Typography variant="caption">
                        查看证据明细
                      </Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                      {/* 接口证据 */}
                      {system.evidence.interface_evidence?.length > 0 && (
                        <Box mb={2}>
                          <Typography variant="subtitle2" gutterBottom>
                            接口证据(ESB)
                          </Typography>
                          <List dense>
                            {system.evidence.interface_evidence.map((iface, iidx) => (
                              <ListItem key={iidx}>
                                <ListItemText
                                  primary={iface.interface_name}
                                  secondary={
                                    `${iface.interface_code} | ${iface.category} | 
                                    ${iface.role} | 相似度: ${(iface.similarity * 100).toFixed(0)}%`
                                  }
                                />
                              </ListItem>
                            ))}
                          </List>
                        </Box>
                      )}
                      
                      {/* 系统画像证据 */}
                      {system.evidence.profile_evidence?.length > 0 && (
                        <Box>
                          <Typography variant="subtitle2" gutterBottom>
                            系统画像证据
                          </Typography>
                          <List dense>
                            {system.evidence.profile_evidence.map((profile, pidx) => (
                              <ListItem key={pidx}>
                                <ListItemText
                                  primary={profile.source_file}
                                  secondary={
                                    `相似度: ${(profile.similarity * 100).toFixed(0)}% | 
                                    ${profile.excerpt}`
                                  }
                                />
                              </ListItem>
                            ))}
                          </List>
                        </Box>
                      )}
                    </AccordionDetails>
                  </Accordion>
                )}
              </TableCell>
              
              <TableCell>
                <IconButton size="small">
                  <CheckIcon />
                </IconButton>
                <IconButton size="small">
                  <CloseIcon />
                </IconButton>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
```

#### 任务4.3: 知识库统计Dashboard

```javascript
// frontend/src/pages/KnowledgeDashboard.js

function KnowledgeDashboard() {
  const [stats, setStats] = useState(null);
  
  useEffect(() => {
    fetch('/api/knowledge/stats')
      .then(res => res.json())
      .then(data => setStats(data));
  }, []);
  
  if (!stats) return <CircularProgress />;
  
  return (
    <Container>
      <Typography variant="h4" gutterBottom>
        知识库统计
      </Typography>
      
      <Grid container spacing={3}>
        {/* 知识类型统计 */}
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                系统画像
              </Typography>
              <Typography variant="h3">
                {stats.system_profile_count}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                接口规范(ESB)
              </Typography>
              <Typography variant="h3">
                {stats.interface_spec_count}
              </Typography>
              <Typography variant="caption">
                覆盖{stats.interface_covered_systems}个系统
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                功能模板
              </Typography>
              <Typography variant="h3">
                {stats.feature_template_count || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                黄金案例
              </Typography>
              <Typography variant="h3">
                {stats.golden_case_count || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        
        {/* 效果评估 */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h5" gutterBottom>
                优化效果评估
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} md={4}>
                  <Typography variant="subtitle2" color="text.secondary">
                    系统识别准确率
                  </Typography>
                  <LinearProgress 
                    variant="determinate" 
                    value={stats.system_identification_accuracy || 0} 
                    sx={{ height: 10, borderRadius: 5, my: 1 }}
                  />
                  <Typography variant="h6">
                    {stats.system_identification_accuracy || 0}%
                  </Typography>
                </Grid>
                
                <Grid item xs={12} md={4}>
                  <Typography variant="subtitle2" color="text.secondary">
                    功能拆分一致性
                  </Typography>
                  <LinearProgress 
                    variant="determinate" 
                    value={stats.feature_breakdown_consistency || 0} 
                    sx={{ height: 10, borderRadius: 5, my: 1 }}
                  />
                  <Typography variant="h6">
                    {stats.feature_breakdown_consistency || 0}%
                  </Typography>
                </Grid>
                
                <Grid item xs={12} md={4}>
                  <Typography variant="subtitle2" color="text.secondary">
                    人天估算准确度
                  </Typography>
                  <LinearProgress 
                    variant="determinate" 
                    value={100 - (stats.average_deviation_rate || 0)} 
                    sx={{ height: 10, borderRadius: 5, my: 1 }}
                  />
                  <Typography variant="h6">
                    ±{stats.average_deviation_rate || 0}%
                  </Typography>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Container>
  );
}
```

---

## 📊 效果评估与成功指标

### 定量指标

| 指标 | 当前(估计) | 目标 | 测量方式 |
|------|----------|------|---------|
| **系统识别准确率** | ~75% | >90% | 黄金数据集对比测试 |
| **系统识别置信度标注准确性** | 无 | >85% | 专家验证置信度标签 |
| **功能拆分一致性** | ~70% | >85% | 多专家对比/模板覆盖率 |
| **人天估算偏离度** | ±35% | ±15% | 黄金数据集实际执行对比 |
| **高置信度功能点占比** | 0% | >70% | 统计置信度分布 |
| **黄金数据集规模** | 0 | 50-100 | 数据统计 |
| **功能模板覆盖率** | 0% | >80% | 统计模板命中率 |

### 定性指标

- ✅ 专家修改幅度降低(目标: <30%)
- ✅ 估算依据可解释、可追溯
- ✅ 低置信度案例能主动标识
- ✅ 专家对AI评估信任度提升

---

## ⏱️ 总体时间表

```
Week 1: 接口知识库 + 功能分类体系
├─ ESB接口导入(3天)
├─ 功能模板构建(2天)
└─ 产出: interface_spec(500+) + feature_template(8+)

Week 2: Agent优化(系统识别 + 功能拆分)
├─ 系统识别Agent增强(2天)
├─ 功能拆分Agent增强(2天)
├─ 工作量估算Agent优化(1天)
└─ 产出: 准确率提升15%+

Week 3: 黄金数据集建设
├─ 定义标准与数据结构(1天)
├─ 收集候选案例(2天)
├─ 专家Review与标注(2天)
└─ 产出: 黄金案例20-30个(初期)

Week 4: 前端优化 + 效果评估
├─ 置信度可视化(2天)
├─ 相似案例推荐UI(1天)
├─ 效果对比测试(1天)
├─ 优化调整(1天)
└─ 产出: 评估报告 + 上线

Week 5-8: 持续优化(可选)
├─ 黄金数据集扩充至50-100个
├─ 功能模板扩展至30-50个
├─ 多模型集成评估
└─ 持续学习闭环
```

---

## 💡 实施建议

### 优先级排序(基于投入产出比)

**P0 (Week 1-2,必做)**: ⭐⭐⭐⭐⭐
1. ESB接口知识库建设 → **最大杠杆点**
2. 功能分类体系与模板 → **标准化关键**
3. Agent优化(接口驱动) → **立竿见影**

**P1 (Week 3-4,建议做)**: ⭐⭐⭐⭐
4. 黄金数据集(初期20-30个) → **持续优化基础**
5. 前端置信度可视化 → **用户体验提升**

**P2 (Week 5+,长期)**: ⭐⭐⭐
6. 黄金数据集扩充至50-100个
7. 多模型集成评估
8. 相似案例推荐
9. 持续学习闭环

### 快速启动建议

**今天**:
1. 导出ESB接口样例数据(100-200条)
2. 阅读本方案,确认可行性

**明天**:
1. 我帮你写ESB清洗导入脚本
2. 设计功能模板JSON结构

**Week 1启动**:
1. 批量导入ESB接口
2. 导入功能模板
3. 测试系统识别效果

---

## 🎯 核心创新点总结

### 来自optimization_plan_v2.md的精华:
✅ **接口驱动** - 利用ESB高质量数据,准确度最高  
✅ **可机器化** - 不依赖人工Review,可自动化处理  
✅ **证据溯源** - 每个识别结果都有明确证据

### 来自enhance_v3.md的精华:
✅ **规则化拆分** - 功能分类体系+拆分规则,提升一致性  
✅ **黄金数据集** - 50-100个高质量案例,持续优化基础  
✅ **置信度标注** - 从"确定数字"转向"区间+置信度",更科学

### 融合创新:
✅ **多因子估算** - 模板+接口+历史案例,综合评估  
✅ **置信度量化** - 基于证据来源计算置信度分数(0-100)  
✅ **可解释性** - 每个估算都有明确依据,可追溯

---

**下一步**: 请确认ESB接口数据格式,我们立即启动Week 1! 🚀
