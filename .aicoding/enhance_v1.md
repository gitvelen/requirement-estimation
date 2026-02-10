# AI Coding 流程优化方案 v1.3

> 基于 lessons_learned.md 的经验教训，优化 AGENTS.md.template、phases/、templates/ 和 STRUCTURE.md，提高项目质量和开发效率。
>
> 制定日期：2026-02-08
> 状态：待实施
> 版本变更：v1.0 → v1.1 → v1.2 → v1.3
>   - v1.1: R1-R10 移到 AGENTS.md.template；AI 自动期简化为单轮收敛；人工介入期改为人工指定审查者
>   - v1.2: 修正审查记录格式（统一为时间正序）；修正自动化检查命令与模板匹配；R5 改为人工检查；Deployment 阶段特殊处理
>   - v1.3: 修正 Markdown 嵌套代码块问题（改用四反引号）；拆分 status.md 的模式与状态字段；明确 P1 收敛语义（P0/P1 open=0，允许 P1 accept/defer）

---

## 一、背景与目标

### 1.1 背景

从 `lessons_learned.md` 提炼出 10 条高频/高风险规则（R1-R10），反映出以下核心问题：

| 问题类别 | 典型表现 | 涉及规则 |
|---------|---------|---------|
| 交互结果遗漏 | 用户确认的内容未写入文档 | R1, R2, R3, R4 |
| 文档一致性缺失 | 同一概念在不同章节口径不一致 | R10 |
| 覆盖性遗漏 | Proposal In Scope 未落到 Requirements | R5 |
| 引用漂移 | REQ 编号调整后未同步更新 plan.md | R6 |
| 文档阅读不充分 | 依赖搜索而非完整阅读 | R7, R9 |
| 任务追踪缺失 | 多任务并行时无 TodoList | R8 |

### 1.2 优化目标

1. **问题预防**：将教训转化为行为规则，整合到 AGENTS.md.template
2. **流程清晰**：区分人工介入期和 AI 自动期，明确行为边界
3. **简化高效**：人工指定审查者，AI 自动期单轮收敛
4. **精简有效**：职责分离，AGENTS.md.template 负责行为规则，STRUCTURE.md 负责结构信息

---

## 二、核心流程设计

### 2.1 工作流时期划分

| 时期 | 阶段 | 人工介入 | 审查触发 | 推进方式 | 收敛判定 |
|------|------|---------|---------|---------|---------|
| **人工介入期** | 00-change-management | ✅ 每阶段确认 | 人工指定 | 人工确认后推进 | 人工判定 |
| **人工介入期** | 01-proposal | ✅ 每阶段确认 | 人工指定 | 人工确认后推进 | 人工判定 |
| **人工介入期** | 02-requirements | ✅ 每阶段确认 | 人工指定 | 人工确认后推进 | 人工判定 |
| **AI 自动期** | 03-design | ❌ 无人工介入 | AI 主动 | AI 自动推进 | AI 自动判定 |
| **AI 自动期** | 04-planning | ❌ 无人工介入 | AI 主动 | AI 自动推进 | AI 自动判定 |
| **AI 自动期** | 05-implementation | ❌ 无人工介入 | AI 主动 | AI 自动推进 | AI 自动判定 |
| **AI 自动期** | 06-testing | ❌ 无人工介入 | AI 主动 | AI 自动推进 | AI 自动判定 |
| **AI 自动期（特殊）** | 07-deployment | ⚠️ 例外需确认 | AI 主动 + 例外暂停 | 人工确认后推进 | 见 2.2.3 |

### 2.2 收敛判定标准

#### 2.2.1 人工介入期（Phase 00-02）
- **触发方式**：人工指定审查者（如 `@review Claude` 或 `@review Codex`）
- **判定方式**：人工判定
- **收敛信号**：审查者输出"建议人工确认进入下一阶段"

#### 2.2.2 AI 自动期（Phase 03-06）
- **触发方式**：AI 主动自我审查
- **判定方式**：AI 自动判定
- **收敛条件**：
  - ✅ P0(open) = 0
  - ✅ P1(open) = 0
  - 允许存在 P1(accept/defer)，但必须在同一条 RVW 记录里写清理由+缓解
  - **单轮自我审查满足即收敛**
- **自动推进**：满足条件后自动更新 status.md，进入下一阶段

#### 2.2.3 Deployment 阶段特殊处理（Phase 07）
- **默认行为**：AI 主动自我审查
- **收敛条件**：P0(open)=0, P1(open)=0（允许存在 P1 accept/defer）
- **自动推进**：满足后**暂停**，输出："请人工确认后部署"
- **例外情况（强制 wait_confirm）**：
  - 涉及 API 契约变更
  - 涉及数据迁移
  - 涉及权限/安全变更
  - 涉及不可逆配置
- **例外处理**：AI 自动暂停，输出："涉及 [例外类型]，请人工指定审查或确认"

### 2.3 人工介入期审查流程

```
┌─────────────────────────────────────────────────────────────┐
│  Phase 00/01/02 人工介入期审查流程                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. AI 完成阶段产出（proposal/requirements）                 │
│         ↓                                                   │
│  2. 人工指定审查者：@review Claude                           │
│         ↓                                                   │
│  3. 审查者执行审查，结果追加到 review_<stage>.md 文件末尾   │
│         ↓                                                   │
│  4. 人工可指定另一审查者：@review Codex                     │
│         ↓                                                   │
│  5. 另一审查者执行审查，结果继续追加到同一文件末尾          │
│         ↓                                                   │
│  6. 重复 2-5，直至问题收敛                                   │
│         ↓                                                   │
│  7. 人工确认进入下一阶段                                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.4 审查记录格式（追加式，时间正序）

```markdown
# Review Report：Requirements / v2.0

> 本文件记录多轮审查记录，按时间正序排列（最新在最末尾）

---

## 2026-02-08 13:20 | 第 1 轮 | 审查者：Claude

### 审查角度
系统性审查（按 `.aicoding/templates/review_template.md` Requirements 清单）

### 本轮发现问题
| RVW-ID | 严重度 | 描述 | 证据 | 建议 |
|---|---|---|---|---|
| RVW-001 | P1 | REQ-005 验收标准不明确 | ... | 补充 GWT |

### 收敛判定
- P0=0, P1=1
- 距离收敛：还需处理 RVW-001

---

## 2026-02-08 14:45 | 第 2 轮 | 审查者：Codex

### 审查角度
用户视角、边界场景、异常处理

### 上一轮问题处理状态
| RVW-ID | 严重度 | 上一轮描述 | 处理方式 | 本轮状态 |
|---|---|---|---|---|
| RVW-001 | P1 | REQ-005 验收标准不明确 | 待处理 | Open |

### 本轮新发现问题
| RVW-ID | 严重度 | 描述 | 证据 | 建议 |
|---|---|---|---|---|
| RVW-002 | P2 | 场景 SCN-003 缺少边界处理 | ... | 建议补充 |

### 收敛判定
- P0=0, P1=1
- 距离收敛：还需处理 RVW-001

---

## 2026-02-08 15:30 | 第 3 轮 | 审查者：Claude

### 审查角度
验证前两轮问题修复情况

### 上一轮问题处理状态
| RVW-ID | 严重度 | 上一轮描述 | 处理方式 | 本轮状态 |
|---|---|---|---|---|
| RVW-001 | P1 | REQ-005 验收标准不明确 | 已补充 GWT | Closed |
| RVW-002 | P2 | 场景 SCN-003 边界缺失 | 接受当前描述 | Accepted |

### 本轮新发现问题
（无）

### 收敛判定
- ✅ P0(open) = 0
- ✅ P1(open) = 0
- **结论**：已收敛，建议人工确认进入下一阶段

---
```

### 2.5 紧急中断机制

| 紧急程度 | 触发条件 | AI 行为 | 状态标记 |
|---------|---------|---------|---------|
| 🔴 P0 阻塞 | P0 问题无法自动修复 | 立即暂停 | paused |
| 🟡 P1 高风险 | 连续 3 轮不收敛 | 完成本轮后暂停 | wait_confirm |
| 🟢 需求疑问 | 发现需求不明确 | 记录继续 | 开放问题+1 |

#### 暂停后输出

```text
⚠️⚠️⚠️ 工作已暂停 ⚠️⚠️⚠️
原因：[原因描述]
当前阶段：[阶段名]
当前状态：paused / wait_confirm
请人工确认后恢复
```

#### 恢复机制

- 人工在 `status.md` 中设置：运行状态=running
- 工作流模式 保持不变（由人工根据情况决定是否修改）
- AI 检测到状态恢复，继续工作
- 或人工直接给出"继续"指令

---

## 三、硬规则 Top 10（R1-R10）

> 规则详情移至 `AGENTS.md.template`，这里是索引

| ID | 类别 | 规则 | 违反后果 |
|----|------|------|---------|
| R1 | 需求 | 提案必须包含所有用户确认的决策点 | 返工、用户信任下降 |
| R2 | 流程 | 文档更新后必须自查并更新版本号和变更记录 | 评审口径漂移 |
| R3 | 需求 | 用户回答必须逐条体现在输出文档中 | 需求遗漏 |
| R4 | 流程 | AskUserQuestion 结果必须结构化写入文档 | 决策点丢失 |
| R5 | 需求 | Requirements 必须覆盖 Proposal In Scope | 范围承诺失效 |
| R6 | 追溯 | REQ 编号调整后必须同步更新引用 | 追溯矩阵失真 |
| R7 | 实现 | 用户指出"文档有提"时必须先读完整章节 | 增加返工次数 |
| R8 | 实现 | 多任务并行必须建立 TodoList | 任务遗漏 |
| R9 | 文档 | proposal 与 requirements 差异必须请用户确认 | 实现偏差 |
| R10 | 文档 | 关键指标必须一致，提交前自检 | 验收争议 |

---

## 四、文件变更清单

### 4.1 新建文件

| 文件 | 路径 | 用途 |
|------|------|------|
| `ai_workflow.md` | `.aicoding/` | AI 工作流控制规则、收敛判定、紧急中断机制 |

### 4.2 修改文件

| 文件 | 主要变更 | 关联规则 |
|------|---------|---------|
| `AGENTS.md.template` | **新增"硬规则"章节** | R1-R10 移入此处 |
| `STRUCTURE.md` | **精简** | 删除硬规则，保留结构信息 |
| `templates/review_template.md` | 增加追加式记录格式、自动化检查命令 | - |
| `phases/00-change-management.md` | 增加完成条件（人工确认） | - |
| `phases/01-proposal.md` | 增加完成条件（人工确认） | R1, R3, R4 |
| `phases/02-requirements.md` | 增加完成条件（人工确认）、覆盖性检查 | R5, R10 |
| `phases/03-design.md` | 增加完成条件（AI 自动，单轮收敛） | - |
| `phases/04-planning.md` | 增加完成条件（AI 自动，单轮收敛）、引用检查 | R6 |
| `phases/05-implementation.md` | 增加完成条件（AI 自动，单轮收敛）、文档阅读 | R7, R8, R9 |
| `phases/06-testing.md` | 增加完成条件（AI 自动，单轮收敛）、全量回归 | - |
| `phases/07-deployment.md` | 增加完成条件（人工确认）、例外暂停、主文档同步 | - |
| `templates/status_template.md` | 增加工作流时期字段、暂停状态 | - |
| `templates/requirements_template.md` | 增加覆盖性检查说明 | R5 |
| `templates/plan_template.md` | 增加引用自检提示 | R6 |

---

## 五、详细修改内容

### 5.1 ai_workflow.md（新建）

````markdown
# AI 工作流控制规则

## 时期划分

| 时期 | 阶段 | 人工介入 | 审查触发 | 推进方式 |
|------|------|---------|---------|---------|
| 人工介入期 | 00-change-management | ✅ | 人工指定 | 人工确认 |
| 人工介入期 | 01-proposal | ✅ | 人工指定 | 人工确认 |
| 人工介入期 | 02-requirements | ✅ | 人工指定 | 人工确认 |
| AI 自动期 | 03-design | ❌ | AI 主动 | AI 自动 |
| AI 自动期 | 04-planning | ❌ | AI 主动 | AI 自动 |
| AI 自动期 | 05-implementation | ❌ | AI 主动 | AI 自动 |
| AI 自动期 | 06-testing | ❌ | AI 主动 | AI 自动 |
| AI 自动期（特殊） | 07-deployment | ⚠️ 例外需确认 | AI 主动 + 例外暂停 | 人工确认 |

---

## 收敛判定标准

### 人工介入期（Phase 00-02）
- **触发方式**：人工指定审查者（`@review Claude` 或 `@review Codex`）
- **判定方式**：人工判定
- **收敛信号**：审查者输出"建议人工确认进入下一阶段"

### AI 自动期（Phase 03-06）
- **触发方式**：AI 主动自我审查
- **判定方式**：AI 自动判定
- **收敛条件**：
  - ✅ P0(open) = 0
  - ✅ P1(open) = 0
  - 允许存在 P1(accept/defer)，但需在 RVW 记录中写清理由+缓解
  - **单轮自我审查满足即收敛**
- **自动推进**：满足条件后自动更新 status.md，进入下一阶段

### Deployment 阶段（Phase 07）
- **默认行为**：自我审查后，满足条件则**暂停**，输出："请人工确认后部署"
- **例外情况（强制 wait_confirm）**：
  - 涉及 API 契约变更
  - 涉及数据迁移
  - 涉及权限/安全变更
  - 涉及不可逆配置
- **例外处理**：AI 自动暂停，输出："涉及 [例外类型]，请人工指定审查或确认"

---

## 人工介入期规则（Phase 00-02）

### 审查流程
1. AI 完成阶段产出
2. 人工指定审查者：`@review Claude` 或 `@review Codex`
3. 审查者执行审查，结果**追加到文件末尾**
4. 人工可继续指定其他审查者
5. 重复 2-4，直至收敛
6. 人工确认后进入下一阶段

### 审查记录格式
每轮审查追加到同一文件末尾，格式：
```
## YYYY-MM-DD HH:MM | 第 N 轮 | 审查者：<Name>

### 审查角度
...

### 上一轮问题处理状态
...

### 本轮新发现问题
...

### 收敛判定
...
```

---

## AI 自动期规则（Phase 03-06）

### AI 行为
1. 完成阶段产出
2. 执行自我审查（按 `.aicoding/templates/review_template.md` 对应清单）
3. 如满足 P0(open)=0 且 P1(open)=0，自动判定收敛
4. 自动更新 status.md，进入下一阶段

### 收敛后输出
```
✅ [阶段] AI 自动审查已收敛
▶️ 自动进入下一阶段：[阶段名]
```

---

## Deployment 阶段规则（Phase 07）

### AI 行为
1. 完成阶段产出
2. 执行自我审查
3. 如满足 P0(open)=0 且 P1(open)=0：
   - 检查是否涉及例外情况（API/数据迁移/权限/不可逆配置）
   - 输出 "请人工确认后部署"，暂停
4. 人工确认后才继续

---

## 紧急中断机制

### 触发条件
- P0 Blockers 无法自动修复
- 连续 3 轮不收敛
- 发现涉及安全/合规的重大风险

### AI 行为
1. 立即停止当前工作
2. 更新 `status.md`：运行状态=paused 或 wait_confirm
3. 输出醒目提示：
   ```
   ⚠️⚠️⚠️ 工作已暂停 ⚠️⚠️⚠️
   原因：[原因描述]
   当前阶段：[阶段名]
   请人工确认后恢复
   ```

### 恢复机制
- 人工在 `status.md` 中设置：运行状态=running
- 工作流模式 保持不变（由人工根据情况决定是否修改）
- AI 检测到状态恢复，继续工作

````

### 5.2 AGENTS.md.template（新增硬规则章节）

在"核心原则"后增加：

```markdown
---

## 硬规则

从 `docs/lessons_learned.md` 提炼的高频/高风险规则，必须严格遵守。

### 文档与交互（R1-R4）
- **R1**：提案必须包含所有用户确认的决策点，不得遗漏
- **R2**：文档更新后必须自查"是否包含所有讨论内容"，并更新版本号和变更记录
- **R3**：用户回答必须逐条体现在输出文档中
- **R4**：使用 AskUserQuestion 后，必须将结果结构化写入文档

### 需求与追溯（R5-R6）
- **R5**：Requirements 必须覆盖 Proposal In Scope，每条落到 REQ/API/验收；Defer 需回写 proposal.md
- **R6**：REQ 编号调整后必须同步更新 plan.md 的引用，并执行引用存在性自检

### 实现与沟通（R7-R9）
- **R7**：用户指出"文档有提"时，必须先完整阅读相关文档，列出原文和行号，不得凭搜索质疑
- **R8**：多任务并行必须使用 TodoWrite 工具建立任务列表
- **R9**：发现 proposal 与 requirements 不一致时，列出两处原文请用户确认，不得自行假设优先级

### 质量（R10）
- **R10**：关键指标必须"术语表 + 指标口径"一致，提交前执行一致性自检

> 完整内容见 `docs/lessons_learned.md`
```

### 5.3 STRUCTURE.md（精简）

**删除内容**：
- "快速索引（硬规则 Top 10）" — 移到 AGENTS.md.template

**保留内容**：
- 目录结构说明
- ID 前缀约定
- 模板索引
- 基线与版本约定
- CR 与差异审查（简化，引用 phases/00-change-management.md）

### 5.4 templates/review_template.md（增强）

在现有内容基础上增加：

````markdown
## 审查记录格式（追加式）

> 本文件记录多轮审查记录，按时间正序排列（最新在最末尾）

### 报告格式（每轮追加到文件末尾）
```markdown
## YYYY-MM-DD HH:MM | 第 N 轮 | 审查者：<Name>

### 审查角度
[本次审查的角度定位]

### 上一轮问题处理状态
| RVW-ID | 严重度 | 上一轮描述 | 处理方式 | 本轮状态 |
|---|---|---|---|---|

### 本轮新发现问题
| RVW-ID | 严重度 | 描述 | 证据 | 建议 |
|---|---|---|---|---|

### 收敛判定
- 本轮后：P0(open)=X, P1(open)=Y
- 距离收敛：是/否
- 建议：[是否建议人工确认/自动推进]
```

---

## 附录：自动化检查命令集

### AC-01: 覆盖性检查（Requirements 阶段）
> 注意：Proposal In Scope 为普通 bullet，需人工核对；Requirements 编号格式为 REQ-xxx
```bash
# 1. 提取提案 In Scope（人工阅读 "### 包含" 章节）
awk 'p && /^## /{exit} p && /^### / && !/^### 包含/{exit} /^### 包含/{p=1} p{print}' docs/<版本号>/proposal.md

# 2. 提取需求落地清单（功能性 REQ-001 和非功能 REQ-101 等）
rg -n "^#### REQ-" docs/<版本号>/requirements.md
```

### AC-02: 关键词一致性检查
```bash
rg -n "关键词1|关键词2" docs/<版本号>/requirements.md
```

### AC-03: 引用存在性检查（R6）
> 目标：验证 plan.md 中引用的所有 REQ 都存在于 requirements.md 中
> 关键：只从 `^#### REQ-` 提取"定义"，避免把引用当定义

```bash
# 1. 提取 plan.md 中的所有 REQ 引用
rg -o "REQ-[0-9]+" docs/<版本号>/plan.md | LC_ALL=C sort -u > /tmp/plan_refs.txt

# 2. 提取 requirements.md 中定义的所有 REQ（只从定义行提取）
rg -o "^#### REQ-[0-9]+" docs/<版本号>/requirements.md | sed 's/^#### //' | LC_ALL=C sort -u > /tmp/req_defs.txt

# 3. 计算差集（plan 引用但 requirements 未定义的 REQ）
LC_ALL=C comm -23 /tmp/plan_refs.txt /tmp/req_defs.txt

# 期望输出：空（无差集表示所有引用都有定义）
```

### AC-04: 全量回归检查
```bash
.venv/bin/pytest -q
```
````

### 5.5 phases/02-requirements.md（增强）

在"完成后"章节前增加：

````markdown
## 完成条件（🔴 MUST）

### 审查要求
- 人工指定审查者：`@review Claude` 或 `@review Codex`
- 审查结果追加到 `review_requirements.md` 文件末尾
- 可多次指定不同审查者，直至问题收敛

### 覆盖性检查（R5）— 人工核对
**检查方式**：
1. 阅读 `proposal.md` 的 "### 包含" 章节
2. 逐项确认是否在 `requirements.md` 中有对应 REQ/API/验收
3. 未覆盖的项需要回写 `proposal.md` 的 Non-goals 或补充需求

### 一致性检查（R10）
**验证命令**（见 `.aicoding/templates/review_template.md` 附录 AC-02）：
```bash
rg -n "关键词1|关键词2" docs/<版本号>/requirements.md
```

### 人工确认
- [ ] 人工阅读 `review_requirements.md`
- [ ] 人工确认问题可接受
- [ ] 人工确认进入 Design 阶段
- [ ] 更新 `status.md`：当前阶段 = Design
````

### 5.6 phases/03-design.md 至 06-testing.md（增强）

在"完成后"章节前增加：

````markdown
## 完成条件（🔴 MUST，AI 自动判定）

### AI 自动审查收敛
- [ ] 执行自我审查（按 `.aicoding/templates/review_template.md` 对应清单）
- [ ] P0(open)=0, P1(open)=0（允许存在 P1 accept/defer）
- [ ] 单轮满足即收敛

### 收敛后自动推进
```text
✅ [阶段] AI 自动审查已收敛
▶️ 自动进入下一阶段：[下一阶段名]
```

### AI 自动执行
- [ ] 更新 `status.md`：当前阶段 = [下一阶段]
- [ ] 开始 [下一阶段] 工作
````

### 5.7 phases/07-deployment.md（增强）

在"完成后"章节前增加：

````markdown
## 完成条件（🔴 MUST）

### AI 自动审查收敛
- [ ] 执行自我审查（按 `.aicoding/templates/review_template.md` Deployment 清单）
- [ ] P0(open)=0, P1(open)=0（允许存在 P1 accept/defer）
- [ ] 单轮满足即收敛

### 例外检查（强制）
- [ ] 检查是否涉及以下情况：
  - [ ] API 契约变更
  - [ ] 数据迁移
  - [ ] 权限/安全变更
  - [ ] 不可逆配置

### 收敛后处理
- 输出 "请人工确认后部署"，暂停等待确认（运行状态=wait_confirm）

### 主文档同步
- [ ] 系统功能说明书已更新（如有功能新增/变更）
- [ ] 技术方案设计已更新（如有架构/选型变更）
- [ ] 接口文档已更新（如有接口变更）
- [ ] 用户手册已更新（如有用户可见交互/流程变更）
- [ ] 部署记录已追加

### 回滚验证
- [ ] 回滚步骤已执行（或在测试环境演练）
- [ ] 数据回滚策略明确

### 人工确认
- [ ] 人工阅读部署文档
- [ ] 人工确认可以部署
- [ ] 人工确认后执行部署
````

### 5.8 phases/04-planning.md（增强）

在"完成后"章节前增加：

````markdown
## 完成条件（🔴 MUST，AI 自动判定）

### AI 自动审查收敛
- [ ] P0(open)=0, P1(open)=0（允许存在 P1 accept/defer）
- [ ] 单轮满足即收敛

### 引用存在性检查（R6）
**验证命令**（见 `.aicoding/templates/review_template.md` 附录 AC-03）：
```bash
# 提取 plan.md 中的所有 REQ 引用
rg -o "REQ-[0-9]+" docs/<版本号>/plan.md | LC_ALL=C sort -u > /tmp/plan_refs.txt

# 提取 requirements.md 中定义的所有 REQ（只从定义行提取）
rg -o "^#### REQ-[0-9]+" docs/<版本号>/requirements.md | sed 's/^#### //' | LC_ALL=C sort -u > /tmp/req_defs.txt

# 计算差集（期望为空）
LC_ALL=C comm -23 /tmp/plan_refs.txt /tmp/req_defs.txt
```
**检查项**：所有 REQ-ID 都存在于 requirements.md 中（期望差集为空）。

### 收敛后自动推进
```text
✅ Planning AI 自动审查已收敛
▶️ 自动进入 Implementation 阶段
```
````

### 5.9 phases/05-implementation.md（增强）

在"实现原则"开头增加：

````markdown
### 0. 文档阅读优先（🔴 MUST，R7/R9）
```text
┌─────────────────────────────────────────────────────────────┐
│  R7: 禁止凭搜索质疑用户                                      │
│     - 用户说"文档有写"时，必须先 Read 相关章节               │
│     - 列出原文和行号，再讨论差异                             │
│                                                              │
│  R9: 差异确认流程                                            │
│     - 发现 proposal 与 requirements 不一致时                 │
│     - 列出两处原文请用户确认，不得自行假设优先级             │
└─────────────────────────────────────────────────────────────┘
```

### 6. 任务追踪强制（多任务时 🔴 MUST，R8）
- 使用 TodoWrite 工具建立任务列表
- 创建 → 执行 → 完成标记，全程追踪
````

### 5.10 templates/status_template.md（增强）

在文档元信息表格后增加：

```markdown
## 工作流状态

| 工作流模式 | 运行状态 |
|---|---|
| manual / semi-auto / auto | running / paused / wait_confirm / completed |

**说明**：
- **工作流模式**：manual（人工介入期，Phase 00-02）/ semi-auto（Deployment 阶段）/ auto（AI 自动期，Phase 03-06）
- **运行状态**：running（正常运行）/ paused（暂停）/ wait_confirm（等待确认）/ completed（已完成）
```

在文件末尾增加：

```markdown
## 阶段转换记录
| 从阶段 | 到阶段 | 日期 | 原因 | 触发人 |
|---|---|---|---|---|
| - | Proposal | YYYY-MM-DD | 初始化 | User |

## 紧急中断记录
| 触发时间 | 原因 | 当前状态 | 恢复条件 |
|---|---|---|---|
| YYYY-MM-DD HH:MM | P0无法自动修复 | paused | 人工确认 |
```

### 5.11 templates/requirements_template.md（增强）

在"1.3 术语与口径"后增加：

```markdown
### 1.4 覆盖性检查说明（🔴 MUST，R5）

#### 人工核对步骤
1. 阅读 `proposal.md` 的 "### 包含" 章节
2. 逐项确认是否在本文档中有对应 REQ/API/验收
3. 未覆盖的项需要回写 `proposal.md` 的 Non-goals 或补充需求

#### 参考记录（可选，便于人工核对）
| Proposal In Scope（来自 proposal.md） | 对应 REQ/API | 验收标准 | 状态 |
|---|---|---|---|
| （人工填写） |  |  |  |
```

### 5.12 templates/plan_template.md（增强）

在"任务概览"表格后增加：

````markdown
### 引用自检（🔴 MUST，R6）
**验证命令**（见 `.aicoding/templates/review_template.md` 附录 AC-03）：
```bash
# 提取 plan.md 中的所有 REQ 引用
rg -o "REQ-[0-9]+" docs/<版本号>/plan.md | LC_ALL=C sort -u > /tmp/plan_refs.txt

# 提取 requirements.md 中定义的所有 REQ（只从定义行提取）
rg -o "^#### REQ-[0-9]+" docs/<版本号>/requirements.md | sed 's/^#### //' | LC_ALL=C sort -u > /tmp/req_defs.txt

# 计算差集（期望为空）
LC_ALL=C comm -23 /tmp/plan_refs.txt /tmp/req_defs.txt
```
**检查项**：所有 REQ-ID 都存在于 requirements.md 中（期望差集为空）。
````

---

## 六、实施计划

### 6.1 实施顺序（考虑依赖关系）

| 批次 | 文件 | 操作 | 理由 |
|------|------|------|------|
| 第一批 | `ai_workflow.md` | 新建 | 基础规则，其他文件引用 |
| 第一批 | `AGENTS.md.template` | 修改 | 新增硬规则章节 |
| 第一批 | `STRUCTURE.md` | 修改 | 精简，删除硬规则 |
| 第二批 | `templates/review_template.md` | 修改 | 审查模板，被 phase 引用 |
| 第二批 | `templates/status_template.md` | 修改 | 状态模板，被所有阶段使用 |
| 第三批 | `phases/00/01/02-*.md` | 修改 | 人工介入期 |
| 第三批 | `phases/03/04/05/06-*.md` | 修改 | AI 自动期 |
| 第三批 | `phases/07-deployment.md` | 修改 | Deployment 特殊处理 |
| 第四批 | `templates/requirements_template.md` | 修改 | 覆盖性检查说明 |
| 第四批 | `templates/plan_template.md` | 修改 | 引用自检 |

### 6.2 验证方式

每批次修改完成后：
1. 检查文件间引用是否正确
2. 确认格式一致
3. 验证规则完整性

---

## 七、风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 单轮收敛可能遗漏问题 | 质量/返工 | 重大变更时可人工指定多轮审查 |
| 规则分散在多个文件 | 遗漏/不一致 | AGENTS.md.template 集中行为规则，STRUCTURE.md 集中结构信息 |
| 人工指定审查者增加操作成本 | 效率 | 灵活性更高，可根据实际情况调整 |
| Deployment 自动化风险 | 生产事故 | 始终需要人工确认，例外情况强制暂停 |

---

## 八、附录

### 8.1 术语表

| 术语 | 定义 |
|------|------|
| 人工介入期 | Phase 00-02，每阶段需人工确认后推进 |
| AI 自动期 | Phase 03-06，AI 自动完成并推进 |
| Deployment 特殊期 | Phase 07，始终需要人工确认 |
| 收敛 | P0(open)=0 且 P1(open)=0；允许存在 P1(accept/defer)，但需在 RVW 记录中写清理由+缓解 |
| 追加式记录 | 多轮审查记录追加到同一文件末尾，按时间正序排列 |
| 紧急中断 | AI 遇到无法处理的问题时暂停工作 |

### 8.2 文件职责划分

| 文件 | 职责 | 内容类型 |
|------|------|---------|
| AGENTS.md.template | AI 行为规则 | 核心原则 + 硬规则（R1-R10） |
| STRUCTURE.md | 目录结构约定 | 目录结构、ID约定、模板索引 |
| ai_workflow.md | 工作流控制 | 时期划分、收敛判定、紧急中断 |
| templates/review_template.md | 审查模板 | 阶段清单、记录格式、检查命令 |
| phases/*.md | 阶段流程 | 各阶段的输入/输出/完成条件 |
| templates/*.md | 文档模板 | 各类文档的结构模板 |

### 8.3 相关文档

- `lessons_learned.md` — 经验教训来源
- `best_practices.md` — 最佳实践参考
- `AGENTS.md.template` — AI 行为规则（含 R1-R10）
- `STRUCTURE.md` — 目录结构与约定
- `phases/` — 阶段流程文件
- `templates/` — 文档模板

---

## 九、版本变更记录

| 版本 | 日期 | 变更说明 |
|------|------|---------|
| v1.3 | 2026-02-08 | 修正 Markdown 嵌套代码块（改用四反引号）；拆分 status.md 模式与状态字段；明确 P1 收敛语义（P0/P1 open=0，允许 P1 accept/defer）；统一状态枚举为小写；改进 AC-01/AC-03 检查命令；全篇统一收敛口径与路径引用 |
| v1.2 | 2026-02-08 | 修正审查记录格式（统一为时间正序）；修正自动化检查命令与模板匹配；R5 改为人工检查；Deployment 阶段始终需人工确认 |
| v1.1 | 2026-02-08 | R1-R10 移到 AGENTS.md.template；AI 自动期简化为单轮收敛；人工介入期改为人工指定审查者 |
| v1.0 | 2026-02-08 | 初始版本 |

---

*文档版本: v1.3*
*制定日期: 2026-02-08*
