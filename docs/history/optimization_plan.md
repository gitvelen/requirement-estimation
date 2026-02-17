# 需求评估系统准确性优化方案

## 📌 问题诊断

根据当前系统分析,主要存在以下准确性问题:

### 1. **知识不足**
- 仅有系统画像(system_profile),缺少:
  - 历史项目真实案例
  - 类似功能点工作量数据
  - 系统间接口/联调复杂度参考
  - 行业最佳实践

### 2. **理解偏差**
- LLM对业务理解有限:
  - 不了解银行业务复杂度
  - 不了解系统间历史债务
  - 不了解技术栈具体实现难度
  - 不了解合规/审计/性能等非功能性需求

### 3. **拆分粒度不准**
- 功能点拆分依赖LLM"想象":
  - 可能过粗或过细
  - 缺少类似案例对标
  - 边界划分主观性强

### 4. **工作量估算简单**
- 当前只按复杂度(高中低)估算:
  - 没有考虑具体技术实现
  - 没有考虑团队能力
  - 没有考虑依赖风险
  - 没有历史数据校准

---

## 🚀 优化方案(分三个阶段)

### **阶段一:知识库体系化建设(2-3周)**

#### 1.1 扩充知识类型

**当前只有**:
- `system_profile` (系统画像)

**需要新增**:

```python
# 知识类型定义
TYPE_SYSTEM_PROFILE = "system_profile"       # 系统画像
TYPE_HISTORICAL_CASE = "historical_case"     # 历史项目案例
TYPE_FEATURE_TEMPLATE = "feature_template"   # 功能模板(标准功能点)
TYPE_TECH_STANDARD = "tech_standard"         # 技术标准/规范
TYPE_INTERFACE_SPEC = "interface_spec"       # 接口规范
TYPE_BUSINESS_PROCESS = "business_process"   # 业务流程
TYPE_INDUSTRY_PRACTICE = "industry_practice" # 行业最佳实践
```

#### 1.2 历史案例库建设

**数据结构**:
```json
{
  "case_id": "CASE_2023_001",
  "project_name": "XX银行核心系统账户模块改造",
  "systems": ["新一代核心", "企业网银"],
  "features": [
    {
      "module": "账户管理",
      "feature_name": "开立个人账户",
      "description": "...",
      "complexity": "中",
      "actual_days": 3.5,
      "ai_estimated_days": 4.0,
      "expert_avg_days": 3.2,
      "deviation_rate": 14.3,
      "tech_stack": ["Java", "Oracle", "Redis"],
      "dependencies": ["客户信息系统", "征信系统"],
      "risks": ["联调窗口期短", "生产数据迁移"],
      "lessons_learned": "需提前确认征信接口规范..."
    }
  ],
  "team_profile": {
    "size": 5,
    "avg_experience": "3-5年",
    "tech_stack_familiarity": "熟悉"
  },
  "delivery_quality": {
    "on_time": true,
    "defect_rate": "低",
    "customer_satisfaction": 4.5
  }
}
```

**导入方式**:
- 从已完成项目中提取
- 专家手工整理并审核
- 可以从评估报告PDF/Word中抽取

#### 1.3 功能模板库建设

**目的**: 沉淀标准功能点(如"开立账户"、"批量转账"等)

**数据结构**:
```json
{
  "template_id": "TPL_001",
  "template_name": "开立个人账户",
  "applicable_systems": ["新一代核心", "账户系统"],
  "category": "账户管理",
  "typical_complexity": "中",
  "typical_days_range": [2.5, 4.0],
  "standard_inputs": ["身份证信息", "开户申请"],
  "standard_outputs": ["账户号", "开户确认"],
  "standard_dependencies": ["客户信息系统", "征信系统"],
  "technical_considerations": [
    "需调用征信接口",
    "需落地影像扫描件",
    "需同步企业网银权限"
  ],
  "risk_points": [
    "征信接口超时",
    "高并发场景性能",
    "反洗钱规则校验"
  ],
  "reference_cases": ["CASE_2023_001", "CASE_2022_055"]
}
```

#### 1.4 系统间关系知识库

**目的**: 理解系统复杂度,不是简单的"核心系统改造"

**数据结构**:
```json
{
  "relationship_id": "REL_001",
  "from_system": "企业网银",
  "to_system": "新一代核心",
  "relationship_type": "接口调用",
  "interface_count": 120,
  "call_frequency": "高频(>1000 TPS)",
  "integration_complexity": "高",
  "typical_joint_testing_days": 5,
  "common_issues": [
    "超时问题",
    "报文格式不一致",
    "事务回滚处理"
  ],
  "best_practices": [
    "提前mock测试",
    "预留联调窗口至少3天",
    "准备降级方案"
  ]
}
```

---

### **阶段二:Agent能力增强(2周)**

#### 2.1 系统识别Agent优化

**当前问题**:
- 只检索system_profile
- 缺少行业经验

**优化措施**:

1. **多知识源融合检索**
```python
# 检索多个知识源
system_profiles = search(TYPE_SYSTEM_PROFILE)
historical_cases = search(TYPE_HISTORICAL_CASE, filter="similar_requirement")
industry_practices = search(TYPE_INDUSTRY_PRACTICE)

# 构建更丰富的上下文
context = f"""
【系统画像】{system_profiles}
【类似历史项目】{historical_cases}
【行业经验】{industry_practices}
"""
```

2. **增加系统复杂度评估**
```python
# 不仅识别系统,还评估改造复杂度
{
  "system_name": "新一代核心",
  "confidence": "高",
  "estimated_complexity": "高", # 新增
  "reasoning": "...",
  "similar_cases": ["CASE_2023_001"], # 新增:类似案例
  "typical_workload_range": [80, 120] # 新增:参考工作量区间
}
```

#### 2.2 功能拆分Agent优化

**当前问题**:
- 拆分粒度不稳定
- 缺少功能模板参考
- 估算依据薄弱

**优化措施**:

1. **引入功能模板匹配**
```python
# 步骤1: 识别需求中的标准功能
templates = search_feature_templates(requirement_text)

# 步骤2: 基于模板拆分
for template in templates:
    # 使用模板的标准inputs/outputs/dependencies
    # 参考模板的typical_days_range
    feature = {
        "功能点": template["template_name"],
        "输入": template["standard_inputs"],
        "输出": template["standard_outputs"],
        "依赖项": template["standard_dependencies"],
        "参考人天区间": template["typical_days_range"],
        "技术考量": template["technical_considerations"],
        "风险点": template["risk_points"]
    }
```

2. **增加类似案例对标**
```python
# 对每个拆分出的功能点,检索类似案例
for feature in features:
    similar_cases = search_historical_cases(
        feature_name=feature["功能点"],
        system_name=system_name,
        complexity=feature["复杂度"]
    )
    
    if similar_cases:
        # 用历史数据校准
        case_days = [c["actual_days"] for c in similar_cases]
        feature["参考历史人天"] = {
            "min": min(case_days),
            "max": max(case_days),
            "avg": sum(case_days) / len(case_days)
        }
        feature["AI预估人天"] = adjust_by_history(
            feature["AI预估人天"],
            feature["参考历史人天"]
        )
```

3. **增加风险评估**
```python
# 为每个功能点评估风险
feature["风险评估"] = {
    "技术风险": ["Redis缓存一致性"],
    "联调风险": ["需等待征信系统升级"],
    "数据风险": ["历史数据迁移量大"],
    "风险系数": 1.2  # 用于调整工作量
}
```

#### 2.3 工作量估算Agent优化

**当前问题**:
- 只按复杂度估算
- 没有历史数据校准

**优化措施**:

1. **多维度估算模型**
```python
def estimate_workload(feature):
    base_days = get_base_days(feature["复杂度"])
    
    # 维度1: 历史案例校准
    history_factor = get_history_factor(feature)
    
    # 维度2: 技术栈熟悉度
    tech_factor = get_tech_familiarity_factor(feature["技术栈"])
    
    # 维度3: 依赖复杂度
    dependency_factor = get_dependency_factor(feature["依赖项"])
    
    # 维度4: 风险系数
    risk_factor = feature.get("风险系数", 1.0)
    
    # 综合估算
    estimated_days = (
        base_days * 
        history_factor * 
        tech_factor * 
        dependency_factor * 
        risk_factor
    )
    
    return {
        "预估人天": estimated_days,
        "置信区间": [estimated_days * 0.8, estimated_days * 1.2],
        "估算依据": {
            "基础人天": base_days,
            "历史校准系数": history_factor,
            "技术栈系数": tech_factor,
            "依赖系数": dependency_factor,
            "风险系数": risk_factor
        }
    }
```

2. **增加置信度评估**
```python
feature["估算置信度"] = calculate_confidence(
    has_similar_case=bool(similar_cases),
    has_template=bool(matched_template),
    dependency_count=len(dependencies),
    risk_level=risk_level
)
# 输出: "高" / "中" / "低"
```

---

### **阶段三:人机协作优化(1-2周)**

#### 3.1 前端展示增强

**优化目标**: 让项目经理/专家更容易理解AI推理过程并纠偏

**新增字段展示**:
1. **功能点列表增强**
   - 显示"参考案例"(点击可查看详情)
   - 显示"参考人天区间"
   - 显示"置信度"(高/中/低)
   - 显示"风险点"

2. **新增"估算依据"面板**
```
┌─ 功能点: 开立个人账户 ─────────────┐
│ AI预估: 3.5人天 (置信度: 高)        │
│                                      │
│ 【估算依据】                        │
│ - 基础工作量: 3.0人天(中复杂度)    │
│ - 历史案例校准: +0.3人天            │
│   参考案例: CASE_2023_001 (3.2人天)│
│ - 技术栈: 熟悉 (×1.0)               │
│ - 依赖系统: 2个 (+0.2人天)         │
│ - 风险系数: 1.0                     │
│                                      │
│ 【类似案例】                        │
│ - XX银行账户改造(2023): 3.2人天    │
│ - XX银行核心升级(2022): 3.8人天    │
│                                      │
│ 【风险提示】                        │
│ - 需提前确认征信接口版本           │
│ - 联调窗口预留3天                   │
└──────────────────────────────────┘
```

#### 3.2 专家反馈机制

**优化目标**: 让专家的修正成为知识积累

1. **专家修正时收集反馈**
```javascript
// 专家修改AI估算时,弹窗收集
{
  "feature_id": "...",
  "ai_estimated_days": 3.5,
  "expert_adjusted_days": 4.5,
  "adjustment_reason": [
    "联调复杂度被低估",
    "历史数据迁移工作量未考虑",
    "需增加性能测试"
  ],
  "expert_note": "该功能涉及大量历史数据迁移..."
}
```

2. **自动入库为新案例**
```python
# 任务完成后,自动生成历史案例
def archive_as_case(task):
    case = {
        "project_name": task["name"],
        "features": [
            {
                "feature_name": f["功能点"],
                "ai_estimated_days": f["AI预估人天"],
                "expert_avg_days": f["专家均值"],
                "actual_days": f["实际人天"],  # 如果有
                "adjustment_reasons": f["专家反馈"]
            }
            for f in task["features"]
        ]
    }
    knowledge_service.import_case(case)
```

---

## 📊 效果评估指标

### 1. 准确性指标
- **AI人天偏离度**: 目标从当前±30%降低到±15%
- **系统识别准确率**: 目标>95%
- **功能点遗漏率**: 目标<5%

### 2. 知识库指标
- **历史案例覆盖率**: 至少覆盖50%常见功能点
- **功能模板数量**: 至少100个标准模板
- **知识命中率**: 每个任务至少命中3条以上相关知识

### 3. 用户体验指标
- **项目经理修改率**: 目标<30%(当前可能>50%)
- **专家二次评估通过率**: 目标>85%
- **用户满意度**: 目标>4.0/5.0

---

## 🛠️ 实施建议

### 第一步:知识采集(优先)

**建议先做**:
1. **整理5-10个典型项目作为案例库**
   - 选择不同规模(小型/中型/大型)
   - 选择不同类型(新建/改造/升级)
   - 必须有完整的实际工作量数据

2. **梳理20-30个高频功能点作为模板**
   - 账户相关: 开户/销户/冻结/解冻
   - 支付相关: 转账/批量转账/跨行支付
   - 查询相关: 余额查询/流水查询/对账

3. **补充系统间关系知识**
   - 核心系统与各渠道的接口关系
   - 常见联调问题与解决方案

### 第二步:Agent升级

- 先升级功能拆分Agent(影响最大)
- 再升级系统识别Agent
- 最后升级工作量估算Agent

### 第三步:前端优化

- 增加"估算依据"展示
- 增加"类似案例"参考
- 增加专家反馈收集

---

## 🎓 长期优化方向

### 1. 引入更强的模型
- 当前用DashScope(通用模型)
- 可以fine-tune专用模型(如基于银行项目数据)

### 2. 多Agent协作
- 增加"技术债务评估Agent"
- 增加"风险评估Agent"
- 增加"接口复杂度评估Agent"

### 3. 主动学习
- AI持续学习专家修正
- 自动调整估算参数
- 动态优化Prompt

---

## 💡 关键成功因素

1. **知识质量>知识数量**: 10个高质量案例胜过100个低质量
2. **专家参与**: 需要资深专家审核案例/模板
3. **持续迭代**: 每个项目完成后都要沉淀为案例
4. **人机协作**: AI辅助但不替代专家判断

---

## ⏱️ 预期时间表

- **Week 1-2**: 知识采集与整理(历史案例/功能模板)
- **Week 3**: 知识库扩展开发(新增知识类型)
- **Week 4-5**: Agent升级开发(多知识源检索/估算优化)
- **Week 6**: 前端优化(估算依据展示/反馈收集)
- **Week 7**: 测试与调优
- **Week 8+**: 上线试运行并持续优化

---

## 📝 附录:快速验证方案

如果想快速验证优化效果,可以先做"最小可行方案":

### MVP方案(1周)

1. **手工整理3个典型案例**(Excel即可)
2. **在Prompt中hard-code注入案例**
   ```python
   prompt += f"""
   【参考案例】
   案例1: XX银行账户管理改造
   - 开立个人账户: 3.2人天
   - 销户: 2.5人天
   ...
   """
   ```
3. **对比优化前后的偏离度**

如果MVP有效,再投入资源做完整方案。
