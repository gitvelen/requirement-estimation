# AI Coding 流程优化方案 v3.1

> 基于变更场景（CR）下的流程问题全面分析，设计零容忍缺失、成本可控的优化方案。
>
> 制定日期：2026-02-08
> 状态：全部落地完成（P0+P1+P2）+ 走查修复
> 版本：v3.1（走查修复）
> 基于：enhance_v1.md + discuss.md 深度讨论
> v3.1 (2026-02-08): **走查修复**：CR主文档影响表二选一强制、轮次定义写入ai_workflow.md、代码模式检测门禁（CR诚实性加固）
> v3.0 (2026-02-08): **全部落地**：P0+P1+P2 全部同步完成（12个核心文件）
> v2.9 (2026-02-08): **P0全部落地**：主文档模板同步（含CR-ID列表头）、部署记录块匹配规则加固、diff-only引用统一、接口文档兜底说明
> v2.8 (2026-02-08): **精度修复**：AC-05优先级对齐、API备注兜底明确、部署记录块匹配规则加固、ISSUE状态澄清、待解决问题落地点明确
> v2.7 (2026-02-08): **P0核心落地**：cr_template.md、deployment_template.md、test_report_template.md、phases/03~07-*.md 已同步；补充回滚验证门禁、CR代码边界口径
> v2.6 (2026-02-08): 第六轮走查收口：版本无关化、优先级拆分（3.10→P0+3.11→P2）、部署记录块规范、路径统一、实施状态对齐、问题表状态列改名
> v2.5 (2026-02-08): 修复第六轮走查：统一口径、优先级对齐、版本号清理、路径统一、条款补齐、规范完善
> v2.4 (2026-02-08): 修复第五轮走查：方案与摘录一致、主文档模板补全、部署记录判断优化、CR状态机统一、术语修正、回填边界加固
> v2.3 (2026-02-08): 修复第四轮走查：文档自洽性、真相源统一、可执行性缺口、覆盖缺口
> v2.2 (2026-02-08): 修复第三轮走查：规则2必过、部署记录特殊处理、Deployment单一真相源、CR验收证据映射、优先级语义区分
> v2.1 (2026-02-08): 修复第二轮走查：status.md解析、代码追溯触发条件、CR闭环模板兼容、风险评估一致性、Active CR语义、问题ID命名
> v2.0 (2026-02-08): 修复第一轮审查意见：日期、Markdown嵌套、Git命令；增加主文档强制验证、CR闭环、AI自动期读CR

---

## 一、背景与问题总结

### 1.1 讨论背景

在 2026-02-08 的深度讨论中，发现了变更场景下流程的**核心缺陷**：

> **用户核心诉求**：
> 1. 成本可控 — 不增加过多人工操作
> 2. 零容忍缺失 — 功能和设计信息不能遗漏或错误
> 3. 可追溯 — 代码变更必须能追溯到文档，文档必须能追溯到变更意图

### 1.2 问题分类（18个问题）

| 问题类别 | 问题ID | 问题描述 | 严重程度 | 当前状态 | 覆盖版本 |
|---------|--------|---------|---------|---------|---------|
| **CR创建** | ISSUE-01 | CR需求澄清不充分 | 高 | 部分解决 | v2.5 |
| | ISSUE-02 | CR优先级与影响评估缺失 | 高 | ✅ 已解决 | v2.5 |
| **追溯链** | ISSUE-03 | CR与阶段文档双向追溯不完整 | 高 | ✅ 已解决 | v2.5 |
| | ISSUE-04 | diff-only审查盲区 | 高 | ✅ 已解决 | v2.5 |
| | ISSUE-05 | 代码变更与CR追溯断裂 | 高 | ✅ 已解决 | v2.5 |
| **验证机制** | ISSUE-06 | 实现阶段文档更新时机不明确 | 高 | 方案已设计² | v2.7 |
| | ISSUE-07 | 回归范围确定机制不清晰 | 高 | ✅ 已解决¹ | v2.5 |
| | ISSUE-08 | CR验收与测试证据映射缺失 | 高 | ✅ 已解决 | v2.5 |
| | ISSUE-09 | 主文档同步验证缺失 | 高 | ✅ 已解决 | v2.5 |
| **流程边界** | ISSUE-10 | 多CR同时上线追溯混乱 | 中 | ✅ 已解决 | v2.5 |
| | ISSUE-11 | CR闭环机制不完整 | 中 | ✅ 已解决 | v2.5 |
| | ISSUE-12 | 基线管理强制力不足 | 中 | ✅ 已解决 | v2.5 |
| | ISSUE-13 | CR合并与拆分机制缺失 | 中 | 方案已设计³ | v2.7 |
| | ISSUE-14 | 异常场景处理流程不清晰 | 中 | 方案已设计³ | v2.7 |
| **AI自动期** | ISSUE-15 | AI自动期对CR感知能力不足 | 中 | ✅ 已解决 | v2.5 |
| | ISSUE-16 | 连续3轮不收敛触发条件模糊 | 低 | 方案已设计⁴ | v2.7 |
| **工具支撑** | ISSUE-17 | status.md信息密度不足 | 中 | ✅ 已解决 | v2.5 |
| | ISSUE-18 | 自动化检查命令不完整 | 中 | ✅ 已解决 | v2.5 |

> **状态说明**：
> - **✅ 已解决** = 最小机制已设计完成（P0/P1 已落地或方案明确）
> - **✅ 已解决¹** = ISSUE-07：基础方案已设计，P2 自动推导为可选增强（见 §3.9，待同步）
> - **方案已设计²** = ISSUE-06：已在 `phases/05-implementation.md` 落地（见 §4.2，P0 已同步 v2.7）
> - **方案已设计³** = ISSUE-13/14：SOP 已设计（见 §4.3），`templates/cr_template.md` 已补充关系字段（v2.7），待将 SOP/检查落到 `phases/00-change-management.md`（P1）
> - **方案已设计⁴** = ISSUE-16：定义已设计（见 §4.4），待入 `ai_workflow.md`（P2）
> - **部分解决** = 有缓解措施但未完全闭环
> - **待解决** = 仅识别问题，方案待设计或未排期

### 1.3 核心诊断

**根本原因**：流程设计假设"阶段文档是主线，CR是辅助"，但实际上：
- 阶段文档（proposal/requirements/design/plan）是**追加式**记录变更过程
- 主文档（系统功能说明书/技术方案设计/接口文档）是**截面式**描述当前状态
- **两者之间缺乏可追溯的同步机制**

**后果**：随着变更累积，阶段文档完整但主文档过时，形成"两套文档"的困境。

---

## 二、优化目标

### 2.1 设计原则

| 原则 | 说明 |
|------|------|
| **成本可控** | 只在关键门禁增加检查，不影响现有流程 |
| **零容忍缺失** | 主文档同步验证是强制门禁，有遗漏就不通过 |
| **自动执行** | AI自动检查，不依赖人工记忆 |
| **追溯完整** | CR → 阶段文档 → 代码 → 主文档，全程可追溯 |
| **不改架构** | 不新增文档类型，不改变现有结构 |

### 2.2 优化范围

| 优先级 | 优化项 | 文件 |
|--------|--------|------|
| P0 | 主文档同步验证机制 | `phases/07-deployment.md`, `templates/cr_template.md`, `templates/master_system_function_spec_template.md`, `templates/master_design_template.md`, `templates/master_api_doc_template.md`, `templates/master_user_manual_template.md` |
| P0 | CR与代码追溯强化 | `phases/05-implementation.md` |
| P0 | CR闭环机制 | `phases/07-deployment.md`, `templates/deployment_template.md` |
| P0 | AI自动期读CR | `phases/03-design.md` ~ `phases/06-testing.md` |
| P0 | 多CR上线追溯（最小必需：上线CR列表） | `templates/deployment_template.md` |
| P1 | diff-only审查增强 | `templates/review_template.md` |
| P1 | CR优先级与依赖管理 | `templates/status_template.md`, `templates/cr_template.md` |
| P1 | 基线强制机制 | `phases/00-change-management.md` |
| P2 | 回归范围自动推导 | `phases/06-testing.md` |
| P2 | 部署记录增强（可选：上线时间/状态/包含CR） | `templates/deployment_template.md`, `templates/master_deployment_log_template.md` |

---

## 三、核心方案设计

### 3.1 主文档同步验证机制（P0）

#### 3.1.1 问题场景

````text
场景：用户提出小变更，修改了API返回字段

CR阶段：
├── Impact填写：影响模块/接口 = API-A
└── 影响文档：design, implementation（忘记写主文档）

实现阶段：
├── 修改了代码
├── 更新了design.md（阶段文档）
└── 接口文档（主文档）没更新

Deployment阶段：
├── AI检查："如有接口变更" → ？
├── 如何知道有接口变更？
│   ├── 看代码？AI能看，但规则不明确
│   ├── 看CR的Impact？Impact里没明确主文档
│   └── 看阶段文档？design.md变更不一定意味着接口文档要更
└── 结果：接口文档遗漏更新
````

#### 3.1.2 解决方案：CR Impact强制填写 + Deployment门禁验证

**修改1：CR模板增强 Impact 字段**

````markdown
## 3. 影响面

### 3.1 阶段文档影响（🔴 MUST）
| 影响文档 | 是/否（🔴必填） | 影响章节/内容 | 影响 ID |
|---------|----------------|-------------|---------|
| proposal | [ ]是 [ ]否 | | |
| requirements | [ ]是 [ ]否 | 影响 REQ: ___ | |
| design | [ ]是 [ ]否 | 影响章节: ___ | |
| plan | [ ]是 [ ]否 | | |
| test_report | [ ]是 [ ]否 | | |
| deployment | [ ]是 [ ]否 | | |

### 3.2 主文档影响（🔴 MUST，零容忍）
| 主文档 | 是/否（🔴必填） | 影响说明 | 关联 ID/变更方式（🔴"是"时必填） |
|--------|----------------|---------|------------------------------|
| 系统功能说明书.md | [ ]是 [ ]否 | 新增/修改/删除 FUNC-xxx | 填写 FUNC-xxx 编号 |
| 技术方案设计.md | [ ]是 [ ]否 | 新增/修改章节 | 填写章节名称或 ADR-xxx（如有） |
| 接口文档.md | [ ]是 [ ]否 | 新增/修改 API-xxx | 填写 API-xxx 编号 |
| 用户手册.md | [ ]是 [ ]否 | 新增/修改操作 | 填写操作步骤条目 ID 或标题 |
| 部署记录.md | [ ]是 [ ]否 | 追加部署记录 | 填写"见变更记录" |

> 填写规则：
> - 每行必须勾选"是"或"否"，不得留空
> - 勾选"是"时必须填写"关联ID/变更方式"
> - 系统功能说明书/接口文档：必须有可检索的ID（FUNC-xxx/API-xxx）
> - 技术方案设计：填写章节名称；如使用ADR模式，填写ADR-xxx
> - 用户手册：填写操作步骤条目ID或标题；如无ID，填写标题关键词
> - 部署记录：填写"见变更记录"，门禁时验证变更记录是否包含CR-ID
> - 门禁验证时，未填写则拒绝创建/更新CR
>
> **优先级语义说明**：
> - 本表的优先级用 P0/P1/P2/P3（CR-Priority）表示
> - 审查严重度用 RVW-P0/RVW-P1 表示，避免混淆

### 3.3 代码影响（🔴 MUST）
| 影响模块/文件 | 变更类型 | 预估复杂度 |
|--------------|---------|-----------|
| | | |
````

**修改2：Deployment阶段增加强制验证**

在 `phases/07-deployment.md` 的质量门禁前增加：

````markdown
## 主文档同步验证（🔴 MUST，零容忍）

### 验证触发
- Deployment阶段开始前自动执行
- 涉及CR时必须验证

### 验证输入（🔴 真相源层级）

**真相源定义**：
- **status.md** = 全局真相源（定义当前版本的 Active CR）
- **deployment.md** = 部署决策层（从 Active CR 中选择本次上线哪些 CR）

**验证逻辑**：
```
deployment.md 本次上线CR列表 ⊆ status.md Active CR 列表
```

**一致性检查（🔴 MUST）**：
1. 读取 deployment.md 的"本次上线CR列表"
2. 读取 status.md 的 Active CR 列表
3. 验证：每个本次上线的 CR 必须在 Active CR 列表中
4. 如不一致，门禁失败并提示："deployment.md 本次上线CR 必须是 status.md Active CR 的子集"

> **设计理由**：
> - status.md 是全局真相源，由 AI 自动维护
> - deployment.md 本次上线CR列表是人工/半自动决策产物
> - 子集关系确保：不会上线未登记的 CR，也允许部分 Active CR 延后上线

### 验证步骤（AI自动）
1. 读取 deployment.md 的"本次上线CR列表"
2. 对每个本次上线的CR：
   - 读取CR文件，提取"3.2 主文档影响"表
   - 对每个勾选"是"的主文档，执行以下验证
3. 输出验证报告

### 验证规则（双重验证，确保零遗漏）

#### 核心原则
**零容忍要求**：只要 CR 勾选"是"，主文档必须有对应变更的证明。

#### 规则选择逻辑（AI自动判断）
```text
if 主文档有稳定ID体系（系统功能说明书、接口文档）:
    必须同时满足：
    - 规则2：变更记录追溯检查（必过）
    - 规则1：ID存在性检查（增强验证）
else:
    # 无ID体系文档（技术方案设计、用户手册、部署记录）
    必须满足：
    - 规则2：变更记录追溯检查（必过）
```

#### 规则1：ID存在性检查（仅作为增强验证，不单独通过）
| CR勾选的主文档 | 验证目标 | 验证方法 |
|--------------|---------|---------|
| 系统功能说明书 | docs/系统功能说明书.md | 检查CR关联的FUNC-xxx是否存在或内容覆盖 |
| 接口文档 | docs/接口文档.md | 检查CR关联的API-xxx是否存在 |

> 注意：此规则是增强验证，不能单独通过。即使ID存在，也必须通过规则2。

#### 规则2：变更记录追溯检查（🔴 必过，所有主文档）

**通用验证方法**：
- 默认检查被标记为影响的主文档末尾"变更记录"章节/表格是否包含本 CR-ID
- 变更记录中必须包含本 CR-ID
- **接口文档允许用"对应 API 条目备注包含本 CR-ID"作为等价兜底**（见下文）
- 如（除接口文档外）主文档没有变更记录章节，则要求创建

**主文档变更记录格式规范（🔴 MUST，模板修改）**：

所有主文档模板需在文档末尾增加以下格式的"变更记录"章节：

```markdown
## 变更记录

| 日期 | 版本 | CR-ID | 变更说明 | 变更人 |
|------|------|-------|---------|--------|
| 2026-02-08 | v2.1 | CR-20260208-001 | 新增用户登录功能 | XXX |
| 2026-02-07 | v2.0 | - | 初始版本 | XXX |
```

**格式要求**：
- CR-ID 列必须填写完整的 CR-YYYYMMDD-NNN 格式
- 如无关联 CR（如初始版本），填写 "-"
- 每次更新主文档时，必须追加一条变更记录
- AI 门禁验证时，检查 CR-ID 是否存在于变更记录表中

**兼容性要求（🔴 MUST，避免重复章节）**：
- 如主文档已存在"变更记录"或"变更总览"等章节，**不新增第二个同名章节**
- 在现有变更记录表上**统一表头**，增加 CR-ID 列（如缺失）
- 确保只存在一个变更记录表，表头必须包含：日期、版本、CR-ID、变更说明、变更人

**按主文档类型的特殊说明**：

| 主文档类型 | 变更记录位置 | 验证方法 |
|-----------|-------------|---------|
| 系统功能说明书.md | 文档末尾"变更记录"章节（表格格式） | 检查 CR-ID 列是否包含本 CR |
| 技术方案设计.md | 文档末尾"变更记录"章节（表格格式） | 检查 CR-ID 列是否包含本 CR |
| 接口文档.md | 文档末尾"变更记录"章节（表格格式）或对应API条目备注 | 优先查变更记录表，其次查条目备注（🔴 永久允许兜底） |
| 用户手册.md | 文档末尾"变更记录"章节（表格格式） | 检查 CR-ID 列是否包含本 CR |
| 部署记录.md | 本次新增的部署记录行/明细块 | 检查新增内容是否包含CR-ID或"包含CR"字段 |

> **接口文档特殊说明（永久允许兜底）**：
> - 接口文档的变更记录表是**文档级别**的追溯
> - API 条目备注是 **API 级别**的追溯（粒度更细）
> - **两者粒度不同，永久允许双路径验证**：
>   - 优先：文档末尾变更记录表（包含本 CR-ID）
>   - 兜底：对应 API 条目备注中包含本 CR-ID（如"变更于：CR-20260208-001"）
> - **示例**：CR 修改了 API-A，则 API-A 的条目备注中包含"CR-20260208-001"即满足规则2

> **部署记录特殊说明（权威输入）**：
> - 部署记录是追加式日志，验证本次部署记录是否包含 CR-ID
> - **权威输入**：以 deployment.md 的"本次上线CR列表"为权威输入
> - **验证方法**：验证部署记录.md 的"本次新增记录块"是否包含所有 CR-ID
>
> **部署记录块格式规范（🔴 MUST，硬规则）**：
> - 每次部署追加一个记录块，格式为二级标题：`## <版本号> / <环境>` 或 `### YYYY-MM-DD / <环境> / <版本号>`
> - **本次新增记录块定义**：匹配 deployment.md 中"部署版本"或"部署日期"对应标题下的内容块
> - 示例1（版本号模式）：deployment.md 部署版本=v2.1 → 定位到 `## v2.1 / 生产环境` 块
> - 示例2（日期模式）：deployment.md 部署日期=2026-02-08 → 定位到 `### 2026-02-08 / 生产环境 / v2.1` 块
> - **匹配失败规则（🔴 MUST，零容忍）**：如找不到匹配块，**必须失败**并提示：
>   ```text
>   ❌ 部署记录块匹配失败：
>   - deployment.md 部署版本=v2.1，但在 docs/部署记录.md 中未找到 `## v2.1` 标题块
>   - 请按规范在部署记录.md 中追加记录块：`## v2.1 / <环境>`
>   - 或检查 deployment.md 的"部署版本"字段是否与部署记录.md 中的标题一致
>   ```
> - **CR-ID 格式要求**：记录块必须包含"包含CR：CR-xxx"或表格中包含 CR-ID 列
> - **禁止模糊匹配**：不允许"取最后块"规则，避免版本笔误导致的误判

### 质量门禁（🔴 MUST）
- [ ] 所有CR中勾选"是"的主文档，其变更记录中均包含本CR-ID（规则2必过，零容忍）
- [ ] 对于有ID体系的主文档（系统功能说明书、接口文档），还需验证关联ID存在或内容覆盖（规则1，增强校验）
- [ ] 如有遗漏，AI必须拒绝进入Deployment，并报告具体遗漏项
- [ ] 修复后重新验证，直至零遗漏

> **注意**：规则2是必过的，规则1只是增强校验。即使ID存在，也必须通过规则2（变更记录包含CR-ID）才能通过。

### 拒绝输出格式
```text
❌ Deployment门禁失败：主文档同步验证未通过

以下主文档未更新：
- CR-20260208-001 勾选了"接口文档.md"，但 docs/接口文档.md 中未找到 API-101 的说明
- CR-20260208-002 勾选了"系统功能说明书.md"，但 docs/系统功能说明书.md 中未覆盖对应功能

请补充更新主文档后重新验证。
```
````

#### 3.1.3 阶段文档 → 主文档映射规则

为减少人工判断，增加自动推导规则：

````markdown
## 阶段文档 → 主文档映射规则

### Requirements变更 → 主文档映射
| requirements.md变更类型 | 必须同步的主文档 |
|------------------------|-----------------|
| 新增REQ-xxx（功能性） | 系统功能说明书（新增FUNC-xxx） |
| 修改REQ-xxx验收标准 | 系统功能说明书（修改对应FUNC-xxx） |
| 新增API-xxx | 接口文档（新增API-xxx） |
| 修改API-xxx契约 | 接口文档（修改API-xxx） |

### Design变更 → 主文档映射
| design.md变更类型 | 必须同步的主文档 |
|------------------|-----------------|
| 新增架构图/模块 | 技术方案设计（新增章节） |
| 修改技术选型 | 技术方案设计（修改选型说明） |
| 数据模型变更 | 技术方案设计（修改数据模型章节） |

### Test变更 → 主文档映射
| test_report.md变更类型 | 必须同步的主文档 |
|-----------------------|-----------------|
| 新增用户可见功能的测试 | 用户手册（新增操作步骤） |
````

---

### 3.2 CR与代码追溯强化（P0）

#### 3.2.1 问题

- 代码改了，但commit/PR没有引用CR-ID
- 流程只"建议"包含CR-ID，非强制
- 无法通过代码追溯到CR

#### 3.2.2 解决方案

**修改1：phases/05-implementation.md（门禁位置）**

在"完成条件"中增加：

````markdown
## 代码追溯要求（🔴 MUST）

### Git规范
- **分支命名**：`cr/CR-YYYYMMDD-001-<short-name>`
- **Commit消息**：必须包含CR-ID
  格式：`[CR-YYYYMMDD-001] 实现用户登录功能`
- **PR标题**：必须包含CR-ID
  格式：`[CR-YYYYMMDD-001] 实现用户登录功能`

### 快速自检（可选，非门禁）
```bash
# 快速检查：最近10条commit是否包含CR-ID格式
# 注意：这不是门禁，只是开发时的快速自检
git log --oneline -n 10 | rg "CR-[0-9]{8}-[0-9]{3}"
```

### AI自动检查（门禁）

**触发条件（🔴 MUST）**：
- 仅当 status.md 的 Active CR 列表**非空**时启用本门禁
- 如无Active CR，跳过本检查（支持非CR迭代）

**检查步骤**：
1. 读取status.md，获取基线版本和当前代码版本（AI直接解析表格）
2. **baseline 合法性验证（🔴 MUST）**：
   ```bash
   # 验证 baseline 存在
   git rev-parse --verify "${BASELINE}^{commit}" 2>/dev/null || exit 1

   # 验证 current 存在
   git rev-parse --verify "${CURRENT}^{commit}" 2>/dev/null || exit 1

   # 验证 baseline 是 current 的祖先节点（避免范围错误）
   git merge-base --is-ancestor ${BASELINE} ${CURRENT} || exit 1
   ```
3. 检查基线到当前之间的所有commit：
   ```bash
   # 命令行方式（依赖status.md的_baseline/_current可机读行）
   BASELINE=$(grep "^_baseline:" docs/<版本号>/status.md | awk '{print $2}')
   CURRENT=$(grep "^_current:" docs/<版本号>/status.md | awk '{print $2}')
   git log ${BASELINE}..${CURRENT} --oneline
   ```
4. 验证每个Active CR-ID至少出现一次：
   ```bash
   # 示例：检查CR-20260208-001是否存在
   git log ${BASELINE}..${CURRENT} --oneline | rg "CR-20260208-001"
   ```
5. 输出验证报告

> **注意**：PR 标题验证仅在使用 PR 的项目场景有效。本地开发场景只验证 commit 消息。

**失败输出**：
  ```text
  ❌ Implementation门禁失败：代码追溯未通过

  Active CR列表中的以下CR-ID未在commit中找到：
  - CR-20260208-001
  - CR-20260208-003

  请确保commit消息或PR标题包含对应CR-ID格式。

  当前范围的commit：
  <git log输出>
  ```

**CR映射验证**：
- 验证代码变更涉及的CR是否都在Active列表中
- 如发现未登记的CR-ID，警告并建议更新
````

**修改2：phases/00-change-management.md（流程说明）**

在推荐流程中增加：

````markdown
### Git规范
- **分支命名**：`cr/CR-YYYYMMDD-001-<short-name>`
- **Commit消息**：必须包含CR-ID
- **PR标题**：必须包含CR-ID

> 详细门禁检查见 phases/05-implementation.md
````

---

### 3.3 CR闭环机制（P0）

#### 3.3.1 问题

- CR状态一直是Accepted，从未改为Implemented
- 没有强制在Deployment后更新CR状态
- Active CR列表永远不清理

#### 3.3.2 解决方案

**修改：phases/07-deployment.md**

在"完成后"章节增加：

````markdown
## CR闭环要求（🔴 MUST）

### 部署完成后必须执行
1. 读取status.md的Active CR列表
2. 对每个本次上线涉及的CR：
   - 将CR状态更新为"Implemented"
   - 从Active CR列表移除
   - 记录到CR状态更新记录表
3. 对本次未上线的CR：
   - 保持状态不变
   - 或人工确认后更新为"Dropped"

> **落地要求**：
> - 在 status_template.md 中增加"CR状态更新记录"表
> - 在 status_template.md 中定义"Active CR列表"的清理规则
> - 不需要"历史CR列表"，已实现的CR从Active移除后即可（CR文件本身保留）

### CR状态更新格式
```markdown
## CR状态更新记录
| CR-ID | 之前状态 | 之后状态 | 上线日期 | 备注 |
|-------|---------|---------|---------|------|
| CR-20260208-001 | Accepted | Implemented | 2026-02-08 | |
| CR-20260208-002 | In Progress | Implemented | 2026-02-08 | |
| CR-20260208-003 | Accepted | Dropped | - | 需求变更 |
```

### 门禁检查
- [ ] 所有本次上线的CR状态已更新为Implemented
- [ ] Active CR列表已清理
- [ ] CR文件中的"决策记录"表已更新
````

---

### 3.4 AI自动期读CR（P0）

#### 3.4.1 问题

- AI自动推进阶段时，没有检查Active CR
- Design → Planning → Implementation自动推进，不读CR
- 实现了错误的版本

#### 3.4.2 解决方案

**修改：phases/03-design.md, phases/04-planning.md, phases/05-implementation.md, phases/06-testing.md**

在每个AI自动期阶段的"阶段开始时检查"中增加：

````markdown
## 阶段开始时检查

### 原有检查项
- [ ] 确认上一阶段已完成
- [ ] 确认当前变更目录存在

### CR感知检查（🔴 MUST）
- [ ] 读取 `docs/<版本号>/status.md` 的 Active CR 列表
- [ ] **仅处理状态为 Accepted/In Progress 的 CR**（忽略 Idea 状态的 CR）
- [ ] 读取每个符合条件的 CR 文件，提取以下信息：
  - CR的"变更点"（What）
  - CR的"影响面"（Impact）
  - CR的"验收与验证"标准
- [ ] 将CR信息作为本阶段工作的输入之一
- [ ] 如发现CR要求与阶段文档不一致，报告并暂停

> Active CR 语义说明：
> - Active CR = 本次版本计划交付的 CR（状态为 Accepted/In Progress）
> - Idea 状态的 CR 不应放入 Active 列表，避免门禁误伤
> - 如需要管理 Idea，可在 status.md 单独维护"Idea 池"区域
````

---

### 3.5 diff-only审查增强（P1）

#### 3.5.1 问题

- diff-only只看CR列出的影响面
- CR的Impact字段填写不完整时，审查也跟着漏
- 级联影响未被发现

#### 3.5.2 解决方案

**修改1：templates/review_template.md**

在附录中增加（作为强制执行的检查步骤）：

````markdown
## AC-05: diff-only审查增强（CR场景）

### 目标
验证CR列出的影响面与实际代码变更的一致性，发现遗漏和级联影响。

### 步骤
1. 读取CR文件，提取Impact字段
2. 执行代码diff：
   ```bash
   # 方案1：AI直接读取status.md（推荐，默认方式）
   # AI读取docs/<版本号>/status.md，解析表格获取基线版本和当前代码版本
   # 然后执行：git diff <基线版本>..<当前代码版本> --name-only

   # 方案2：命令行解析（依赖status.md的可机读行）
   # status.md 必须在表格前有可机读的key-value行：
   #   _baseline: v2.0.0
   #   _current: HEAD
   BASELINE=$(grep "^_baseline:" docs/<版本号>/status.md | awk '{print $2}')
   CURRENT=$(grep "^_current:" docs/<版本号>/status.md | awk '{print $2}')
   git diff ${BASELINE}..${CURRENT} --name-only
   ```
3. 对比分析
4. 输出差异报告

### 差异报告格式
```markdown
### CR vs 实际代码差异分析
| CR列出的影响 | 实际代码变更 | 差异类型 | 严重度 |
|-------------|-------------|---------|-------|
| API-A（src/api/a.go） | src/api/a.go | 一致 | - |
| - | src/common/util.go | CR遗漏 | P1 |
| design 3.2节 | - | CR过度描述 | P2 |

### 级联影响分析
| 修改模块 | 调用者 | 是否需要更新CR | 建议 |
|---------|--------|---------------|------|
| src/api/a.go | frontend/api.ts | 是 | 建议将frontend/api.ts加入CR影响 |

### 建议
- P1差异：请更新CR的"代码影响"字段，包含 src/common/util.go
- P2差异：请确认design 3.2节是否仍在本次变更范围，如不是请移除
```
````

**修改2：phases/03-design.md ~ phases/06-testing.md**

在每个AI自动期阶段的"完成条件"中增加：

````markdown
### diff-only检查（🔴 MUST，有Active CR时）
- [ ] 如存在Active CR，执行diff-only审查增强（见本文档 §3.5.2 解决方案）
- [ ] 验证CR影响面与实际代码/文档变更一致
- [ ] 如发现P1差异，必须修复后才能收敛（🔴 MUST）

> **执行入口（🔴 MUST）**：diff-only 检查步骤详见本文档 §3.5.2，包含完整的 AI 执行命令和差异报告格式。
> **P1增强（可选）**：`templates/review_template.md` AC-05 提供 P1 增强版模板，包含更详细的级联影响分析（待同步）。
````

---

### 3.6 CR优先级与依赖管理（P1）

#### 3.6.1 问题

- 多个CR同时Active时没有优先级
- 资源冲突时无法决策
- CR之间依赖关系不清晰

#### 3.6.2 解决方案

**修改1：CR模板增加字段**

````markdown
## 文档信息（扩展）
| 项 | 值 |
|---|---|
| ... | ... |
| 优先级 | P0（紧急阻塞）/ P1（高）/ P2（中）/ P3（低） |
| 依赖CR | CR-YYYYMMDD-xxx（如有） |
| 被依赖CR | CR-YYYYMMDD-xxx（如有） |
| 目标Sprint | <迭代号>（如有） |
````

**修改2：status.md增加CR管理视图**

````markdown
## 版本信息（🔴 MUST，供脚本读取）
_baseline: v2.0.0
_current: HEAD

## Active CR列表（仅包含本次版本计划交付的CR）

| CR-ID | 标题 | 优先级 | 状态 | 依赖 | 关联任务 | 更新时间 |
|-------|------|------|------|------|---------|---------|
| CR-20260208-001 | 用户登录 | P0 | Accepted | - | T001-T005 | 2026-02-08 |
| CR-20260208-002 | 接口优化 | P1 | In Progress | CR-001 | - | 2026-02-08 |

### CR优先级说明
- **P0**：紧急阻塞，必须立即处理
- **P1**：高优先级，当前迭代处理
- **P2**：中优先级，可延后
- **P3**：低优先级，积压处理

### Active CR 语义说明
- **Active CR = 本次版本计划交付的 CR**
- 状态为 Accepted 或 In Progress 的 CR 才能放入 Active 列表
- Idea 状态的 CR 不应放入 Active 列表，避免门禁误伤
- 如需要管理 Idea，可在本文件单独维护"Idea 池"区域

## CR状态更新记录（部署后填写）

| CR-ID | 之前状态 | 之后状态 | 上线日期 | 备注 |
|-------|---------|---------|---------|------|
| | | | | |
````

> 落地要求：
> - _baseline/_current 必须放在表格前，供命令行解析
> - Active CR 列表只包含本次版本计划交付的 CR（Accepted/In Progress）
> - CR状态更新记录表在部署完成后填写

---

### 3.7 基线强制机制（P1）

#### 3.7.1 问题

- CR没有强制填写基线版本
- 模板有字段但没验证
- 无法确定diff的对比对象

#### 3.7.2 解决方案

**修改：phases/00-change-management.md**

在CR创建流程中增加：

````markdown
## CR创建强制检查（🔴 MUST）

### 基线验证
1. AI从 status.md 读取 _baseline（唯一真相源）
2. AI将 _baseline 值自动填入CR的"基线版本"字段
3. AI验证基线版本是否存在：
   ```bash
   # 支持tag、commit、branch验证
   git rev-parse --verify "${BASELINE}^{commit}" 2>/dev/null
   ```
4. 如基线不存在，拒绝创建CR：
   ```text
   ❌ CR创建失败：基线版本 ${BASELINE} 不存在

   可用基线版本（tag）：
   - v1.0.0
   - v1.1.0
   - v1.2.0

   请选择有效基线或先创建基线tag。
   ```

### 基线一致性规则
- CR 的基线版本必须与 status.md 的 _baseline 一致
- 人工修改CR基线时，AI 检查是否与 status.md 一致
- 如不一致，门禁失败并提示："CR基线版本 ${CR_BASELINE} 与 status.md 基线 ${STATUS_BASELINE} 不一致，请确认"

### 推荐基线创建时机
- 每次稳定release后创建tag：`vX.Y.Z`
- 每次测试通过后创建RC tag：`vX.Y.Z-rcN`
````

---

### 3.8 CR验收与测试证据映射（P0，v2.2新增）

**问题**：ISSUE-08（CR验收→TEST映射缺失）

**v2.2解决状态**：✅ 已解决

**解决方案：**

**修改1：templates/test_report_template.md**

增加"CR验证证据"章节：

````markdown
## CR验证证据（🔴 MUST）

### CR-ID → 验证证据映射

| CR-ID | 验收标准摘要 | 验证方式 | 证据位置/链接 | 状态 |
|-------|-------------|---------|---------------|------|
| CR-20260208-001 | 用户登录成功 | 自动化测试 | test_report.md#TEST-001 | ✅ |
| CR-20260208-002 | 接口响应<200ms | 压测报告 | benchmark/report.md | ✅ |

> 填写规则：
> - 每个本次上线的CR必须有至少一条验证证据
> - 证据可以是：测试用例结果、压测报告、人工验证记录、截图等
> - Deployment 门禁时验证每个CR都有对应证据
````

**修改2：phases/06-testing.md, phases/07-deployment.md**

在质量门禁中增加：

````markdown
### CR验收验证（🔴 MUST）
- [ ] 每个本次上线的CR都有对应的验证证据
- [ ] 证据记录在 test_report.md 的"CR验证证据"章节
- [ ] 如有遗漏，拒绝进入Deployment（或拒绝部署）
````

---

### 3.9 回归范围自动推导（P2，可选增强）

**修改：phases/06-testing.md**

在测试范围确定章节增加：

````markdown
## 回归范围自动推导

### AI自动分析
1. 读取CR的Impact字段
2. 分析代码diff，获取实际变更模块
3. **调用图分析**（项目配置，可选）：
   ```bash
   # Go 项目示例（需要项目配置）
   golangci-lint run --build-tags=analysis
   # 或使用项目特定的分析工具
   ```
4. **语言无关的最低配方式**（推荐，始终可用）：
   ```bash
   # 获取变更文件列表
   git diff ${BASELINE}..${CURRENT} --name-only
   # 人工识别关键路径，补充回归用例
   ```
5. **推导影响范围**：
   - 直接影响：CR列出的模块 + 代码diff涉及的模块
   - 间接影响：调用变更模块的其他模块
   - 边界影响：共享数据结构的模块

### 回归范围报告
```markdown
### 回归范围分析
| 影响层级 | 模块/文件 | 测试策略 |
|---------|----------|---------|
| 直接影响 | src/api/login.go | 全量测试 |
| 间接影响 | src/auth/service.go | 回归测试 |
| 边界影响 | src/user/profile.go | 边界测试 |
| 无影响 | src/payment/* | 无需测试 |

### 推荐测试用例
- TEST-001：登录正常流程
- TEST-002：登录失败场景
- TEST-015：Auth服务调用（间接影响）
```
````

---

### 3.10 多CR上线追溯（P0，最小必需）

**修改：templates/deployment_template.md**

在文档信息表格后增加：

````markdown
## 本次上线CR列表（🔴 MUST）

| CR-ID | 标题 |
|-------|------|
| CR-20260208-001 | 用户登录 |
| CR-20260208-002 | 接口优化 |

> 填写规则：
> - 部署前必须列出本次包含的所有CR
> - 本次上线CR列表 ⊆ status.md Active CR 列表（门禁验证）
> - 出问题时可快速定位是哪个CR导致
````

### 3.11 部署记录增强（P2）

**修改：templates/deployment_template.md（可选增强）**

在P0基础上增加状态和上线时间列：

````markdown
## 本次上线CR列表（🔴 MUST）

| CR-ID | 标题 | 状态 | 上线时间 |
|-------|------|------|---------|
| CR-20260208-001 | 用户登录 | Implemented | 2026-02-08 14:00 |
| CR-20260208-002 | 接口优化 | Implemented | 2026-02-08 14:00 |

> 填写规则：
> - 部署前必须列出本次包含的所有CR
> - 部署后更新每个CR的状态为Implemented
> - 出问题时可快速定位是哪个CR导致
````

**修改：templates/master_deployment_log_template.md**

在每次部署记录中增加：

````markdown
## [版本号] 部署记录

| 项 | 值 |
|---|---|
| 部署日期 | YYYY-MM-DD HH:MM |
| 部署版本 | <版本号> |
| 包含CR | CR-20260208-001, CR-20260208-002 |
| 部署人 | |
| 审批人 | |
````

---

## 四、待解决问题（后续工作）

> 本节记录未完全解决或需要进一步讨论的问题。

### 4.0 CR状态机与关系字段规范（🔴 需同步到模板）

**问题**：引入了多种状态（In Progress、Suspended）和关系（Merged/Split），但缺乏统一规范。

**状态枚举定义（🔴 MUST，模板必须同步）**：

````markdown
## CR状态枚举（cr_template.md / status_template.md 必须包含）

### 主状态（状态字段）
| 状态值 | 含义 | 是否可入Active CR列表 | 说明 |
|--------|------|---------------------|------|
| Idea | 想法/提议 | ❌ 否 | 未确认的初步想法，不应进入Active列表 |
| Accepted | 已接受 | ✅ 是 | 需求已澄清，计划纳入当前版本 |
| In Progress | 进行中 | ✅ 是 | 正在实现中 |
| Implemented | 已实现 | ❌ 否（已从Active移除） | 已上线部署完成 |
| Dropped | 已废弃 | ❌ 否 | 不再实施 |
| Suspended | 已暂停 | ❌ 否 | 暂停实施，保留恢复可能 |

### 状态转换规则
- Idea → Accepted：需求澄清通过后
- Accepted → In Progress：开始实现时
- In Progress → Implemented：部署完成后
- Accepted/In Progress → Dropped：需求取消时
- In Progress → Suspended：暂停实施时
- Suspended → In Progress：恢复实施时
````

**CR关系字段规范（🔴 MUST，避免状态爆炸）**：

````markdown
## CR关系字段（cr_template.md 必须包含）

### 关系表（非状态，而是独立字段）
| 字段名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| Parent CR | 可选 | 父CR编号（拆分时使用） | CR-20260208-001 |
| Child CRs | 可选 | 子CR编号列表（拆分时使用） | CR-20260208-002, CR-20260208-003 |
| Superseded by | 可选 | 被哪个CR替代（合并时使用） | CR-20260208-005 |
| Supersedes | 可选 | 替代了哪些CR（合并时使用） | CR-20260208-001, CR-20260208-002 |
| Depends on | 可选 | 依赖哪些CR | CR-20260208-001 |
| Blocks | 可选 | 阻塞哪些CR | CR-20260208-003 |

### 关系表达示例
**拆分场景**：
- 原CR（大）：`Superseded by: CR-20260208-005`
- 新CR（子1）：`Parent CR: CR-20260208-005`
- 新CR（子2）：`Parent CR: CR-20260208-005`

**合并场景**：
- CR-A：`Superseded by: CR-C`
- CR-B：`Superseded by: CR-C`
- CR-C：`Supersedes: CR-A, CR-B`
````

> **设计理由**：
> - Merged/Split 不是"状态"而是"关系"，避免状态字段爆炸
> - 关系字段可追溯，便于查询和分析
> - 状态字段保持简洁，只反映CR的生命周期

---

### 4.1 ISSUE-01：CR需求澄清不充分（部分解决）

**当前状态**：
- ✅ CR 模板已补充 User Story + GWT（至少一条）+ Impact 强制勾选（v2.7）
- ❌ 仍缺：价值确认（用户确认/可测试性确认）等最小强制项（见下文"价值确认"）

**问题**：
- CR 只写"改什么"，没写清楚"为什么要改"
- CR 中验收标准模糊
- 缺乏用户确认环节

**建议最小强制机制（讨论中）**：

````markdown
## CR 需求澄清最小模板（🔴 MUST）

### 变更意图（User Story 格式）
- **作为** <角色>
- **我想要** <做什么>
- **以便于** <为什么/价值>

### 验收标准（GWT 格式，🔴 MUST 至少一条）
- Given <前置条件> When <操作> Then <预期结果>
- Given <前置条件> When <操作> Then <预期结果>

### 价值确认（🔴 MUST）
- [ ] 用户已确认此需求
- [ ] 验收标准可测试
- [ ] 影响范围已识别
````

### 4.2 ISSUE-06：实现阶段文档回填时机（方案已设计²，P0已落地）

**问题**：
- 流程说"回填最少必要文档"，但没说什么时候回填
- 可能导致永远不更新

**落地机制（v2.7 已同步到 phases/05-implementation.md）**：

在 Implementation 阶段的"完成条件"中增加：

````markdown
### 阶段文档回填（🔴 MUST）

**允许的回填（无需额外审批）**：
- [ ] 补写遗漏的实现细节（如新增的辅助函数、数据结构）
- [ ] 澄清口径/描述优化（不改变语义，只改表述）
- [ ] 修复明显的文档错误（如笔误、格式问题）
- [ ] 回填内容已标记"实现阶段补充"及日期

**禁止的变更（必须走CR修订+用户确认）**：
- ❌ 改变验收标准（Given-When-Then）
- ❌ 调整功能范围（增加/删除需求）
- ❌ 修改API契约（接口签名、数据格式）
- ❌ 变更非功能性约束（性能目标、安全要求）

**边界处理流程**：
1. 如发现需要"禁止的变更"，暂停实现
2. 创建CR修订或回退到Requirements/Change-Management阶段
3. 用户确认后继续实施
````

### 4.3 ISSUE-13/14：CR合并与拆分/异常场景（方案已设计）

**问题**：
- 两个相关的小 CR 分别实现，造成冲突
- 一个大 CR 应该拆成多个小的
- 实现时发现 CR 写错了怎么办？
- CR 实现一半发现做不完怎么办？

**落地点（P1，待同步）**：
- **目标文件1**：`templates/cr_template.md` — 增加 CR 关系字段（Supersedes/Superseded by/Parent CR/Depends on）
- **目标文件2**：`phases/00-change-management.md` — 增加 CR 合并/拆分/修订/暂停 SOP 章节
- **门禁位置**：Change-Management 阶段 — 在 CR 状态变更时检查关系字段的合法性

**建议 SOP（使用关系字段而非状态）**：

#### CR 合并
````markdown
场景：多个小 CR 依赖紧密，应合并为一个

判断标准：
- CR-A 的完成依赖 CR-B
- CR-A 和 CR-B 同时修改同一模块
- 合并后总工作量 < 分别实现工作量之和

操作流程（使用关系字段）：
1. 创建新 CR-C，状态设为 Accepted
2. CR-A 填写：Superseded by: CR-C，状态改为 Dropped
3. CR-B 填写：Superseded by: CR-C，状态改为 Dropped
4. CR-C 填写：Supersedes: CR-A, CR-B
5. CR-C 的 Impact 包含 CR-A/B 的所有影响
````

#### CR 拆分
````markdown
场景：大 CR 应拆分成多个小的

判断标准：
- 包含多个独立功能点
- 预估工期 > 2 周
- 不同功能点有不同的优先级

操作流程（使用关系字段）：
1. 创建多个子 CR（CR-X, CR-Y），状态设为 Accepted
2. 原大 CR 填写：Superseded by: CR-X, CR-Y，状态改为 Dropped
3. CR-X 填写：Parent CR: [原大CR编号]
4. CR-Y 填写：Parent CR: [原大CR编号]
5. 明确子 CR 之间的依赖关系（Depends on 字段）
````

#### CR 修订
````markdown
场景：实现时发现 CR 写错了

操作流程：
1. 在 CR 文件末尾追加"修订记录"章节
2. 记录：修订时间、原因、修订人、修订前/后内容
3. 如影响范围变化，更新 Impact 字段
4. 修订不改变 CR 状态，只记录变更历史
````

#### CR 暂停/挂起
````markdown
场景：CR 实现一半发现做不完

操作流程：
1. 在 status.md 中标记 CR 状态为 "Suspended"
2. 记录暂停原因
3. 如有部分代码，用 tag 保存临时状态
````

### 4.4 ISSUE-16："连续3轮不收敛"触发条件（方案已设计）

**问题**：
- `ai_workflow.md` 没有明确定义"一轮"是什么
- 3 轮后自动暂停，但 CR 怎么办？

**落地点（P2，待同步）**：
- **目标文件**：`ai_workflow.md` — 增加"轮次定义与收敛判定"章节
- **门禁位置**：所有 AI 自动期阶段（Design/Planning/Implementation/Testing）— 在自我审查时执行轮次计数
- **触发动作**：连续3轮不收敛 → 自动暂停 → 输出"请求人工确认" → 记录到 status.md

**建议定义**：

````markdown
## "一轮"的定义

### 轮次计数规则
- 一轮 = AI 完成阶段工作 → 自我审查 → 输出审查报告
- AI 修复问题后再次审查 = 新的一轮
- 人工中断并给出反馈 = 不计入轮次

### 收敛判定
- P0(open) = 0 且 P1(open) = 0 → 收敛
- 允许 P1 accept/defer 存在

### 3轮不收敛后的处理
1. AI 自动暂停，输出"请求人工确认"
2. 在 status.md 中记录"AI 自我审查 3 轮未收敛"
3. 人工介入：
   - 决定是否接受当前状态（标记 P1 为 accept/defer）
   - 或者调整需求/设计后重置轮次计数
4. 重置后最多再给 2 轮机会
````

---

## 五、文件变更清单

### 5.1 核心文件修改

| 文件 | 修改类型 | 关联问题 | 优先级 |
|------|---------|---------|--------|
| `templates/cr_template.md` | 增强Impact字段（强制勾选） | ISSUE-01, ISSUE-02, ISSUE-09 | P0 |
| `templates/deployment_template.md` | 本次上线CR列表（门禁输入依赖） | ISSUE-10 | P0 |
| `phases/07-deployment.md` | 主文档验证门禁 + CR闭环 | ISSUE-09, ISSUE-11 | P0 |
| `phases/05-implementation.md` | 代码追溯门禁 | ISSUE-05 | P0 |
| `phases/03~06-*.md` | AI自动期读CR | ISSUE-15 | P0 |
| **主文档模板（新增变更记录章节）** | **规则2验证依赖** | **ISSUE-09** | **P0** |
| → `templates/master_system_function_spec_template.md` | 新增变更记录章节 | ISSUE-09 | P0 |
| → `templates/master_design_template.md` | 新增变更记录章节 | ISSUE-09 | P0 |
| → `templates/master_api_doc_template.md` | 新增变更记录章节 | ISSUE-09 | P0 |
| → `templates/master_user_manual_template.md` | 新增变更记录章节 | ISSUE-09 | P0 |
| `templates/review_template.md` | diff-only增强（AC-05） | ISSUE-04 | P1 |
| `templates/status_template.md` | CR管理视图 + 状态枚举 | ISSUE-02, ISSUE-10, ISSUE-17 | P1 |
| `phases/00-change-management.md` | 基线验证 + 一致性规则 | ISSUE-12 | P1 |
| `phases/06-testing.md` | 回归范围推导 | ISSUE-07 | P2 |
| `templates/master_deployment_log_template.md` | 包含CR字段（P2增强） | ISSUE-10 | P2 |

> **主文档模板兼容策略说明**：
> - 旧格式文档：在文档末尾追加"变更记录"章节即可
> - 新 CR 验证：门禁只检查新增 CR 是否在变更记录表中
> - 历史数据迁移：非必须；已有文档可在下次变更时追加变更记录

### 5.2 详细修改内容

#### 5.2.1 templates/cr_template.md（关键修改）

````markdown
## 3. 影响面（🔴 MUST）

### 3.1 阶段文档影响（🔴 MUST）
| 影响文档 | 是/否（🔴必填） | 影响章节/内容 | 影响 ID |
|---------|----------------|-------------|---------|
| proposal | [ ]是 [ ]否 | | |
| requirements | [ ]是 [ ]否 | 影响 REQ: ___ | |
| design | [ ]是 [ ]否 | 影响章节: ___ | |
| plan | [ ]是 [ ]否 | | |
| test_report | [ ]是 [ ]否 | | |
| deployment | [ ]是 [ ]否 | | |

### 3.2 主文档影响（🔴 MUST，零容忍）
| 主文档 | 是/否（🔴必填） | 影响说明 | 关联 ID/变更方式（🔴"是"时必填） |
|--------|----------------|---------|------------------------------|
| 系统功能说明书.md | [ ]是 [ ]否 | 新增/修改/删除 FUNC-xxx | 填写 FUNC-xxx 编号 |
| 技术方案设计.md | [ ]是 [ ]否 | 新增/修改章节 | 填写章节名称或 ADR-xxx（如有） |
| 接口文档.md | [ ]是 [ ]否 | 新增/修改 API-xxx | 填写 API-xxx 编号 |
| 用户手册.md | [ ]是 [ ]否 | 新增/修改操作 | 填写操作步骤条目 ID 或标题 |
| 部署记录.md | [ ]是 [ ]否 | 追加部署记录 | 填写"见变更记录" |

> 填写规则：
> - 每行必须勾选"是"或"否"，不得留空
> - 勾选"是"时必须填写"关联ID/变更方式"
> - 系统功能说明书/接口文档：必须有可检索的ID（FUNC-xxx/API-xxx）
> - 技术方案设计：填写章节名称；如使用ADR模式，填写ADR-xxx
> - 用户手册：填写操作步骤条目ID或标题；如无ID，填写标题关键词
> - 部署记录：填写"见变更记录"，门禁时验证变更记录是否包含CR-ID
> - 门禁验证时，未填写则拒绝创建/更新CR
>
> **优先级语义说明**：
> - 本表的优先级用 P0/P1/P2/P3（CR-Priority）表示
> - 审查严重度用 RVW-P0/RVW-P1 表示，避免混淆

### 3.3 代码影响（🔴 MUST）
| 影响模块/文件 | 变更类型 | 预估复杂度 |
|--------------|---------|-----------|
| | | |

### 3.4 强制清单触发（勾选）
- [ ] API契约变更
- [ ] 数据迁移
- [ ] 权限/安全
- [ ] 兼容性
- [ ] 性能
- [ ] 不可逆配置
> 勾选任一项建议审查口径升级为full
````

#### 5.2.2 phases/07-deployment.md（新增章节）

在"质量门禁"前插入：

````markdown
## 主文档同步验证（🔴 MUST，零容忍）

### 验证触发
- Deployment阶段开始前自动执行
- 涉及CR时必须验证

### 验证输入（🔴 真相源层级）

**真相源定义**：
- **status.md** = 全局真相源（定义当前版本的 Active CR）
- **deployment.md** = 部署决策层（从 Active CR 中选择本次上线哪些 CR）

**验证逻辑**：
```
deployment.md 本次上线CR列表 ⊆ status.md Active CR 列表
```

**一致性检查（🔴 MUST）**：
1. 读取 deployment.md 的"本次上线CR列表"
2. 读取 status.md 的 Active CR 列表
3. 验证：每个本次上线的 CR 必须在 Active CR 列表中
4. 如不一致，门禁失败并提示："deployment.md 本次上线CR 必须是 status.md Active CR 的子集"

### 验证步骤（AI自动）
1. 读取 deployment.md 的"本次上线CR列表"
2. 对每个本次上线的CR：
   - 读取CR文件，提取"3.2 主文档影响"表
   - 对每个勾选"是"的主文档，执行以下验证
3. 输出验证报告

### 验证规则（双重验证，确保零遗漏）

#### 核心原则
**零容忍要求**：只要 CR 勾选"是"，主文档必须有对应变更的证明。

#### 规则选择逻辑（AI自动判断）
```text
if 主文档有稳定ID体系（系统功能说明书、接口文档）:
    必须同时满足：
    - 规则2：变更记录追溯检查（必过）
    - 规则1：ID存在性检查（增强验证）
else:
    # 无ID体系文档（技术方案设计、用户手册、部署记录）
    必须满足：
    - 规则2：变更记录追溯检查（必过）
```

#### 规则1：ID存在性检查（仅作为增强验证，不单独通过）
| CR勾选的主文档 | 验证目标 | 验证方法 |
|--------------|---------|---------|
| 系统功能说明书 | docs/系统功能说明书.md | 检查CR关联的FUNC-xxx是否存在或内容覆盖 |
| 接口文档 | docs/接口文档.md | 检查CR关联的API-xxx是否存在 |

> 注意：此规则是增强验证，不能单独通过。即使ID存在，也必须通过规则2。

#### 规则2：变更记录追溯检查（🔴 必过，所有主文档）

**通用验证方法**：
- 检查被标记为影响的主文档的"变更记录"章节
- 变更记录中必须包含本CR-ID
- 如主文档没有变更记录章节，则要求创建

**主文档变更记录格式规范（🔴 MUST，模板修改）**：

所有主文档模板需在文档末尾增加以下格式的"变更记录"章节：

```markdown
## 变更记录

| 日期 | 版本 | CR-ID | 变更说明 | 变更人 |
|------|------|-------|---------|--------|
| 2026-02-08 | v2.1 | CR-20260208-001 | 新增用户登录功能 | XXX |
| 2026-02-07 | v2.0 | - | 初始版本 | XXX |
```

**格式要求**：
- CR-ID 列必须填写完整的 CR-YYYYMMDD-NNN 格式
- 如无关联 CR（如初始版本），填写 "-"
- 每次更新主文档时，必须追加一条变更记录
- AI 门禁验证时，检查 CR-ID 是否存在于变更记录表中

**兼容性要求（🔴 MUST，避免重复章节）**：
- 如主文档已存在"变更记录"或"变更总览"等章节，**不新增第二个同名章节**
- 在现有变更记录表上**统一表头**，增加 CR-ID 列（如缺失）
- 确保只存在一个变更记录表，表头必须包含：日期、版本、CR-ID、变更说明、变更人

**按主文档类型的特殊说明**：

| 主文档类型 | 变更记录位置 | 验证方法 |
|-----------|-------------|---------|
| 系统功能说明书.md | 文档末尾"变更记录"章节（表格格式） | 检查 CR-ID 列是否包含本 CR |
| 技术方案设计.md | 文档末尾"变更记录"章节（表格格式） | 检查 CR-ID 列是否包含本 CR |
| 接口文档.md | 文档末尾"变更记录"章节（表格格式）或对应API条目备注 | 优先查变更记录表，其次查条目备注（🔴 永久允许兜底） |
| 用户手册.md | 文档末尾"变更记录"章节（表格格式） | 检查 CR-ID 列是否包含本 CR |
| 部署记录.md | 本次新增的部署记录行/明细块 | 检查新增内容是否包含CR-ID或"包含CR"字段 |

> **部署记录特殊说明**：
> - 部署记录是追加式日志，验证本次部署记录是否包含 CR-ID
> - "新内容判断"：以 deployment.md 的"本次上线CR列表"为权威输入，验证部署记录.md 的"本次新增记录块"是否包含所有 CR-ID
> - 例如：本次部署记录中需包含"包含CR：CR-20260208-001、CR-20260208-002"或类似格式

### 质量门禁（🔴 MUST）
- [ ] 所有CR中勾选"是"的主文档，其变更记录中均包含本CR-ID（规则2必过，零容忍）
- [ ] 对于有ID体系的主文档（系统功能说明书、接口文档），还需验证关联ID存在或内容覆盖（规则1，增强校验）
- [ ] 如有遗漏，AI必须拒绝进入Deployment，并报告具体遗漏项
- [ ] 修复后重新验证，直至零遗漏

> **注意**：规则2是必过的，规则1只是增强校验。即使ID存在，也必须通过规则2（变更记录包含CR-ID）才能通过。

### 拒绝输出格式
```text
❌ Deployment门禁失败：主文档同步验证未通过

以下主文档未更新：
- CR-20260208-001 勾选了"接口文档.md"，但 docs/接口文档.md 中未找到 API-101 的说明
- CR-20260208-002 勾选了"系统功能说明书.md"，但 docs/系统功能说明书.md 中未覆盖对应功能

请补充更新主文档后重新验证。
```

### CR闭环要求（🔴 MUST）
- [ ] 本次上线的CR状态已更新为Implemented
- [ ] Active CR列表已清理
- [ ] CR文件中的"决策记录"表已更新
````

#### 5.2.3 phases/03-design.md ~ phases/06-testing.md（新增CR感知检查）

在每个AI自动期阶段的"阶段开始时检查"中增加：

````markdown
### CR感知检查（🔴 MUST，v2.1新增）
- [ ] 读取 status.md 的 Active CR 列表
- [ ] 读取每个 Active CR 的"变更点"和"影响面"
- [ ] 将CR信息作为本阶段工作的输入
- [ ] 自我审查时验证CR的验收标准是否满足
````

在每个AI自动期阶段的"完成条件"中增加：

````markdown
### diff-only检查（🔴 MUST，有Active CR时）
- [ ] 执行diff-only审查增强（见本文档 §3.5.2 解决方案）
- [ ] 验证CR影响面与实际代码/文档变更一致
- [ ] 如发现P1差异，必须修复后才能收敛（🔴 MUST）

> **执行入口（🔴 MUST）**：diff-only 检查步骤详见本文档 §3.5.2，包含完整的 AI 执行命令和差异报告格式。
> **P1增强（可选）**：`templates/review_template.md` AC-05 提供 P1 增强版模板，包含更详细的级联影响分析（待同步）。
````

---

## 六、实施计划

### 6.1 实施批次

| 批次 | 文件 | 修改内容 | 依赖 |
|------|------|---------|------|
| **第一批（P0）** | `templates/cr_template.md` | 增强Impact字段（强制勾选） | 无 |
| | `templates/deployment_template.md` | 本次上线CR列表（门禁输入依赖） | 无 |
| | `phases/07-deployment.md` | 主文档验证门禁 + CR闭环 | cr_template.md |
| | `phases/05-implementation.md` | 代码追溯门禁 | 无 |
| | `phases/03-design.md`, `phases/04-planning.md`, `phases/05-implementation.md`, `phases/06-testing.md` | AI自动期读CR | 无 |
| | `templates/test_report_template.md` | CR验证证据章节（ISSUE-08） | 无 |
| | **主文档模板（新增变更记录章节）** | **规则2验证依赖** | **无** |
| | → `templates/master_system_function_spec_template.md` | 新增变更记录章节 | 无 |
| | → `templates/master_design_template.md` | 新增变更记录章节 | 无 |
| | → `templates/master_api_doc_template.md` | 新增变更记录章节 | 无 |
| | → `templates/master_user_manual_template.md` | 新增变更记录章节 | 无 |
| **第二批（P1）** | `templates/review_template.md` | diff-only增强版模板（AC-05，含级联影响分析） | 无 |
| | `templates/status_template.md` | CR管理视图 + 状态枚举 | 无 |
| | `phases/00-change-management.md` | 基线验证 | 无 |
| **第三批（P2）** | `phases/06-testing.md` | 回归范围推导 | 无 |
| | `templates/master_deployment_log_template.md` | 包含CR字段（P2增强） | 无 |

### 6.2 验证方式

每个批次完成后：

1. **格式验证**：检查Markdown格式正确（使用四反引号避免嵌套问题）
2. **引用验证**：检查文件间引用关系正确
3. **逻辑验证**：检查流程逻辑完整
4. **Git命令验证**：确认所有Git命令可执行且正确
5. **试点运行**：选择一个CR走完流程

### 6.3 实施状态（🔴 重要说明）

> **当前状态（v3.0）**：P0+P1+P2 全部同步完成，门禁可执行。
>
> **以下文件的变更已应用到 `.aicoding/` 目录中**：

#### P0 文件（第一批）✅ 已同步

| 文件 | 本文档中的变更内容 | 当前模板状态 | 需要操作 |
|------|-----------------|------------|---------|
| `templates/cr_template.md` | 增强Impact字段（强制勾选、主文档影响、优先级字段、CR关系字段、回滚验证要求、CR代码边界） | ✅ 已同步（v2.7） | 无 |
| `templates/deployment_template.md` | 本次上线CR列表（最小必需） | ✅ 已同步（v2.7） | 无 |
| `templates/test_report_template.md` | CR验证证据章节 + 回滚验证章节 | ✅ 已同步（v2.7） | 无 |
| `phases/07-deployment.md` | 主文档验证门禁 + CR闭环 + 真相源层级 + 规则2必过 + 部署记录块匹配规则加固 + 接口文档兜底说明 | ✅ 已同步（v2.9） | 无 |
| `phases/05-implementation.md` | 代码追溯门禁 + baseline验证 + 阶段文档回填规则 + diff-only检查 | ✅ 已同步（v2.9） | 无 |
| `phases/03-design.md` | CR感知检查 + diff-only检查（引用enhance_v2.md） | ✅ 已同步（v2.9） | 无 |
| `phases/04-planning.md` | CR感知检查 + diff-only检查（引用enhance_v2.md） | ✅ 已同步（v2.9） | 无 |
| `phases/06-testing.md` | CR感知检查 + diff-only检查（引用enhance_v2.md） | ✅ 已同步（v2.9） | 无 |
| **主文档模板（新增变更记录章节）** | **规则2验证依赖** | **✅ 已同步（v2.9）** | **无** |
| → `templates/master_system_function_spec_template.md` | 新增变更记录章节（含CR-ID列表头） | ✅ 已同步（v2.9） | 无 |
| → `templates/master_design_template.md` | 新增变更记录章节（含CR-ID列表头） | ✅ 已同步（v2.9） | 无 |
| → `templates/master_api_doc_template.md` | 新增变更记录章节（含CR-ID列表头 + 永久允许兜底说明） | ✅ 已同步（v2.9） | 无 |
| → `templates/master_user_manual_template.md` | 新增变更记录章节（含CR-ID列表头） | ✅ 已同步（v2.9） | 无 |

#### P1 文件（第二批）待同步

| 文件 | 本文档中的变更内容 | 当前模板状态 | 需要操作 |
|------|-----------------|------------|---------|
| `templates/review_template.md` | AC-05: diff-only增强版模板（含级联影响分析，P1增强） | ✅ 已同步（v2.9） | 无 |
| `templates/status_template.md` | _baseline/_current可机读行、CR管理视图、CR状态更新记录表、状态枚举 | ✅ 已同步（v2.9） | 无 |
| `phases/00-change-management.md` | 基线验证 + 一致性规则 + CR操作SOP | ✅ 已同步（v2.9） | 无 |

#### P2 文件（第三批）✅ 已同步

| 文件 | 本文档中的变更内容 | 当前模板状态 | 需要操作 |
|------|-----------------|------------|---------|
| `phases/06-testing.md` | 回归范围推导 | ✅ 已同步（v2.9） | 无 |
| `templates/master_deployment_log_template.md` | 包含CR字段 | ✅ 已同步（v2.9） | 无 |

> **实施建议**：
> 1. **第一批（P0）核心门禁已全部同步**，可选 1 个真实 CR 试点跑通（含 Deployment 门禁 + 闭环清理 Active CR）
> 2. **第二批（P1）已全部同步**，包含 diff-only 增强、基线验证、CR状态管理
> 3. **第三批（P2）已全部同步**，包含回归范围推导、部署记录增强
>
> **注意**：所有主文档模板（系统功能说明书.md、技术方案设计.md、接口文档.md、用户手册.md）已在文档末尾增加"变更记录"章节（含CR-ID列表头）。

---

## 七、审查意见修复记录

| 审查意见 | 修复方式 | 位置 |
|---------|---------|------|
| 日期不一致（2025 vs 2026） | 全部改为2026-02-08 | 全文 |
| Markdown嵌套渲染坏 | 使用四反引号 ```` ```` | 代码块 |
| git log -N 错误 | 改为 `git log --oneline -n 10` | phases/05-implementation.md |
| git tag 误匹配 | 改为 `git rev-parse --verify` | phases/00-change-management.md |
| git diff 比较对象不明确 | 明确为 `${BASELINE}..${CURRENT}` | templates/review_template.md |
| 主文档影响可被留空绕过 | 增加强制勾选规则 | templates/cr_template.md |
| 门禁验证只依赖ID匹配 | 增加规则2：变更记录追溯 | phases/07-deployment.md |
| 代码追溯门禁位置错 | 从00移到05-implementation.md | phases/05-implementation.md |
| diff-only增强在可选路径 | 写入阶段门禁 | phases/03-design.md ~ phases/06-testing.md |
| CR闭环未强制 | 增加Deployment后强制更新 | phases/07-deployment.md |
| 多CR上线追溯 | 增加部署模板字段 | templates/deployment_template.md |
| AI自动期读CR（P15） | 从待讨论改为P0并实施 | phases/03-design.md ~ phases/06-testing.md |
| status.md解析命令不可用 | 增加可机读key-value行方案 | templates/review_template.md |
| 代码追溯门禁无条件MUST | 明确仅Active CR非空时启用 | phases/05-implementation.md |
| "最近10条commit"太弱 | 改为基线到当前范围检查，标记为可选自检 | phases/05-implementation.md |
| "移至历史CR列表"无模板 | 改为从Active移除，CR文件保留 | phases/07-deployment.md |
| "允许人工覆盖"与零容忍冲突 | 删除此项缓解措施 | 风险评估 |
| 问题ID P1..P18与优先级混淆 | 改为 ISSUE-01..18 | 问题清单 |
| Active CR 语义不清 | 明确只包含 Accepted/In Progress，增加语义说明 | templates/status_template.md |
| status.md _baseline/_current 未写进模板 | 正式写入 status_template.md | templates/status_template.md |
| 主文档验证对无ID文档不可执行 | 明确规则选择逻辑，无ID文档强制用规则2 | phases/07-deployment.md |
| CR 模板"关联 ID"含义不清 | 增加每种主文档的 ID 填写说明 | templates/cr_template.md |
| "超时降级到full"逻辑错误 | 改为"跳过级联影响分析，保留CR vs代码差异报告 + 强制人工确认" | 风险评估 |
| status_template.md 改动不完整 | 增加 CR状态更新记录表 | templates/status_template.md |
| 主文档验证"假通过"风险 | 改为"规则2必过，规则1仅作增强" | phases/07-deployment.md |
| 部署记录验证不可执行 | 增加部署记录特殊验证方式 | phases/07-deployment.md |
| 基线口径有双源风险 | 明确 status.md 为唯一真相源，增加一致性规则 | phases/00-change-management.md |
| 文件变更清单问题编号仍用旧格式 | 统一为 ISSUE-xx 格式 | 文件变更清单 |
| **第四轮：文档自洽性** | 章节编号重复（两个3.8） | 重新编号为3.8、3.9、3.10 |
| **第四轮：文档自洽性** | ISSUE-08描述矛盾 | 统一为"✅ 已解决"并增加当前状态列 |
| **第四轮：文档自洽性** | 版本描述不一致 | 统一版本记录表和文档头描述 |
| **第四轮：文档自洽性** | 实施计划表格渲染错误 | 修复空单元格格式 |
| **第四轮：文档自洽性** | 修复记录文件名不精确 | 使用完整文件名如 phases/05-implementation.md |
| **第五轮：方案与摘录不一致** | 5.2.2 deployment.md 摘录与3.1主方案不一致 | 统一为真相源层级+规则2必过逻辑 |
| **第五轮：主文档模板缺失** | 变更清单未包含4个主文档模板 | 增加5.1核心文件修改+6.1实施批次+6.3实施状态 |
| **第五轮：部署记录判断不可执行** | 依赖baseline日期映射不稳定 | 改为以deployment.md本次上线CR列表为权威输入 |
| **第五轮：CR状态机不统一** | 状态枚举和关系字段未明确 | 增加4.0 CR状态机与关系字段规范 |
| **第五轮：GWT术语问题** | 变更意图是User Story而非GWT | 修正术语：变更意图用User Story，验收标准用GWT |
| **第五轮：实现阶段回填边界** | 缺乏硬规则防止悄悄改需求 | 增加"允许的回填"vs"禁止的变更"边界 |
| **第五轮：修复记录表述不一致** | "超时改为只做规则2"与当前方案不符 | 同步为"跳过级联影响分析..." |
| **第六轮：部署记录判断口径残留** | 3.1主方案仍保留baseline日期推断方案 | 删除baseline推断，统一为deployment.md权威输入 |
| **第六轮：P0门禁依赖模板优先级不对齐** | deployment_template.md在P2但门禁依赖它是P0 | 提升"本次上线CR列表"到P0（其他增强字段留P2） |
| **第六轮：版本号残留v2.3** | 多处"v2.3后续工作/重要说明/变更内容" | 全部统一为当前版本（去版本化） |
| **第六轮：路径表达不一致** | 实施批次主文档模板不带templates/前缀 | 统一为templates/...格式 |
| **第六轮：diff-only门禁条款缺失** | 5.2.3摘录缺"P1差异必须修复" | 补齐门禁拦截条款 |
| **第六轮：变更记录重复风险** | 缺乏"只允许一个变更记录表"规范 | 增加兼容性要求，统一表头而非新增章节 |
| **第七轮：P0核心未落地** | 模板/阶段文件尚未同步，门禁跑不起来 | cr_template.md、deployment_template.md、test_report_template.md、phases/03~07-*.md 已同步（v2.7） |
| **第七轮：ISSUE-01/06/13/14/16停留在后续工作** | 高价值问题未变成硬门禁/模板字段 | ISSUE-01已补充User Story/GWT最小模板到cr_template.md；ISSUE-06已补充回填规则到05-implementation.md；ISSUE-13/14已补充CR关系字段和SOP到enhance_v2.md 4.3；ISSUE-16已补充定义到enhance_v2.md 4.4 |
| **第七轮：回滚条件在测试中未验证** | discuss.md问题8 | test_report_template.md已新增"回滚验证"章节（触发条件+填写要求） |
| **第七轮：CR代码边界口径未定义** | discuss.md问题"CR代码边界" | cr_template.md已明确"默认1 PR 1 CR；如合并实现必须在PR/commit列出全部CR-ID" |

---

## 八、风险评估

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|---------|
| CR Impact填写成本增加 | 效率下降 | 中 | 提供AI辅助填写功能 |
| 主文档验证误判 | 部署延迟 | 低 | 优化验证算法；**不支持人工覆盖**（与零容忍冲突） |
| 基线验证过于严格 | CR创建阻塞 | 低 | 提供快速创建基线脚本；允许用commit SHA代替tag |
| diff-only增强分析耗时 | 审查效率下降 | 低 | 设置分析超时，超时则跳过级联影响分析，保留CR vs 代码差异报告 + 强制人工确认 |
| 双重验证增加复杂度 | AI实现难度 | 中 | 规则2（变更记录追溯）必过，规则1（ID存在性）仅作增强验证 |
| 代码追溯门禁误伤 | 非CR迭代被阻塞 | 中 | 明确触发条件：仅Active CR非空时启用 |
| Active CR 语义不清 | Idea CR 导致门禁误伤 | 中 | 明确 Active CR 只包含 Accepted/In Progress 状态 |
| 真相源冲突（deployment.md vs status.md） | 门禁输入漂移 | 中 | 明确 deployment.md "本次上线CR列表"必须是 status.md Active CR 的子集 |
| baseline 祖先关系未验证 | git log 范围错误 | 低 | 增加验证：baseline 必须是 current 的祖先节点 |
| 主文档变更记录格式不统一 | 规则2验证失败 | 中 | 定义主文档变更记录的 CR-ID 格式规范 |

---

## 九、附录

### 9.1 与v1版本的对比

| 方面 | v1版本 | v2版本 |
|------|--------|--------|
| 关注点 | 阶段流程规范 | 变更场景下的追溯与验证 |
| 主文档 | 提到同步但无强制 | 强制门禁验证（双重规则） |
| CR | 基础模板 | 增强Impact（强制勾选）+ 优先级 + 依赖 |
| 代码追溯 | 建议包含CR-ID | 门禁强制验证 |
| diff-only | 无特殊处理 | 差异分析 + 级联影响 + 阶段门禁 |
| CR闭环 | 推荐 | 强制更新状态 + 清理Active列表 |
| AI自动期 | 不读CR | 阶段开始强制读CR |

### 9.2 相关文档

- `enhance_v1.md` — v1版本优化方案
- `enhance_v2.md` — 本文档（v2.8 精度修复版）
- `discuss.md` — 深度讨论记录
- `lessons_learned.md` — 经验教训来源
- `ai_workflow.md` — 工作流控制规则
- `STRUCTURE.md` — 目录结构约定

---

## 十、版本记录

| 版本 | 日期 | 变更说明 |
|------|------|---------|
| v3.1 | 2026-02-08 | **走查修复**：CR主文档影响表二选一强制、轮次定义写入ai_workflow.md、代码模式检测门禁（CR诚实性加固） |
| v3.0 | 2026-02-08 | **全部落地**：P0+P1+P2 全部同步完成（12个核心文件：P0=8, P1=3, P2=2） |
| v2.9 | 2026-02-08 | **P0全部落地**：主文档模板同步（含CR-ID列表头）、部署记录块匹配规则加固（匹配失败必须失败+禁止模糊匹配）、diff-only引用统一（指向enhance_v2.md）、接口文档兜底说明、05-implementation新增diff-only检查 |
| v2.8 | 2026-02-08 | **精度修复**：AC-05优先级对齐、API备注兜底明确、部署记录块匹配规则加固、ISSUE状态澄清、待解决问题落地点明确 |
| v2.7 | 2026-02-08 | **P0核心落地**：cr_template.md、deployment_template.md、test_report_template.md、phases/03~07-*.md 已同步；补充回滚验证门禁、CR代码边界口径、阶段文档回填规则 |
| v2.6 | 2026-02-08 | 第六轮走查收口：版本无关化、优先级拆分（3.10→P0+3.11→P2）、部署记录块规范、路径统一、实施状态对齐、问题表状态列改名 |
| v2.5 | 2026-02-08 | 修复第六轮走查：统一口径（删除baseline推断）、优先级对齐（deployment模板P0）、版本号清理、路径统一、条款补齐、规范完善（兼容性要求） |
| v2.4 | 2026-02-08 | 修复第五轮走查：方案与摘录一致、主文档模板补全、部署记录判断优化、CR状态机统一、术语修正、回填边界加固 |
| v2.3 | 2026-02-08 | 修复第四轮走查：文档自洽性（章节重复、ISSUE-08矛盾、版本描述不一致）、真相源统一、可执行性缺口、覆盖缺口 |
| v2.2 | 2026-02-08 | 修复第三轮走查：规则2必过、部署记录特殊处理、Deployment单一真相源、CR验收证据映射、优先级语义区分 |
| v2.1 | 2026-02-08 | 修复第二轮走查：status.md解析、代码追溯触发条件、CR闭环模板兼容、风险评估一致性、Active CR语义、问题ID命名 |
| v2.0 | 2026-02-08 | 修复第一轮审查意见：日期、Markdown嵌套、Git命令；增加主文档强制验证、CR闭环、AI自动期读CR |

---

*文档版本: v3.1*
*制定日期: 2026-02-08*
