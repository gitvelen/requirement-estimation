# 需求评估系统 v2.4 需求说明书

| 项 | 值 |
|---|---|
| 状态 | Draft |
| 作者 | AI + User |
| 评审 | - |
| 日期 | 2026-02-28 |
| 版本 | v1.3 |
| 关联提案 | `docs/v2.4/proposal.md` |

## 1. 概述

### 1.1 目的与范围

本文档将 `proposal.md`（v1.2）中确认的五个变更方向转化为可验收的技术需求：

1. **文档导入页重构**（变更一）：消除下拉切换丢状态问题，提供独立操作区、导入历史、画像跳转链接。
2. **系统画像展示页增强**（变更二）：系统画像从 4 个扁平字段重构为 5 域 12 子字段结构化模型，三区布局（左侧域导航+中间内容区+右侧可折叠时间线）+ 子字段级 inline diff + AI 建议操作（采纳/忽略/回滚）。
3. **AI 结构化信息提取与回滚支持**（变更三）：文档导入和代码扫描入库后自动触发 AI 结构化信息提取，映射到画像各字段的 `ai_suggestions`；支持一级回滚。
4. **工作量估算机制激活**（变更四）：LLM 输出三点估计 + 三层知识注入；移除静态映射和复杂度反向覆写。
5. **评估经验资产沉淀**（变更五）：AI 原始输出快照 + PM 修正 diff + `ai_correction_history` 自动更新。

**前端涉及页面**（4 个既有页面，不新增菜单路由）：
- `SystemProfileImportPage`（导入页）
- `SystemProfileBoardPage`（画像展示页）
- `EvaluationPage`（评估页）
- `ReportPage`（评估报告页）

### 1.2 背景、约束与关键假设

**约束**：
- 沿用现有技术栈（FastAPI + React + Ant Design + DashScope），不引入新基础设施。
- 不新增菜单路由或独立页面。
- 上线后可一键回退到 v2.3。

**关键假设**：
- DashScope API 可用且响应时间可接受（AI 结构化提取和 LLM 估算均依赖）。
- 现有 PM-系统归属关系数据已存在（用于权限绑定）。
- 系统画像数据模型支持扩展 `ai_suggestions`、`ai_suggestions_previous`、`ai_correction_history`、`profile_events` 字段。

### 1.3 术语与口径

| 术语 | 定义 |
|---|---|
| `ai_suggestions` | 系统画像各字段的 AI 建议值，由 AI 结构化信息提取生成 |
| `ai_suggestions_previous` | `ai_suggestions` 的上一版快照，用于一级回滚 |
| `ai_correction_history` | 系统画像新增字段，记录 PM 对 AI 输出的累计修正模式（修正次数、偏差方向、常见遗漏等） |
| `profile_events` | 画像变更事件日志，记录每次变更的类型、时间、来源、摘要 |
| `ai_original_output` | 评估流水线每步（系统识别/功能拆分/工作量估算）的 AI 原始输出快照 |
| 三点估计 | 乐观值（optimistic）、最可能值（most_likely）、悲观值（pessimistic），由 LLM 输出；期望值 expected = (O + 4M + P) / 6 由系统自动计算（PERT 公式），保留 2 位小数 |
| PM 修正 diff | AI 原始输出与 PM 最终确认版本的结构化差异，分两阶段计算：Phase 1（PM 提交时）系统级（新增/删除/改名）、功能点级（新增/删除/修改描述）；Phase 2（评估完成后）估值级（专家终值 vs AI 预估偏差）。`ai_correction_history` 在 Phase 2 后更新 |
| 三层知识注入 | LLM 估算 prompt 注入的三层上下文：①系统画像上下文 ②`ai_correction_history` 校准数据（≥3 次评估后启用）③同系统历史评估结果（功能点名+描述+专家终值）|
| 策略 C（多系统过滤） | 导入时提取文档中所有系统信息，仅自动应用到当前选中系统；其他系统信息以通知形式提示 PM |

**ID 前缀规则**：详见 `.aicoding/STRUCTURE.md` 统一定义。

### 1.4 覆盖性检查（🔴 MUST，R5）

#### 覆盖映射表（🔴 MUST）

| Proposal 锚点 | 类型 | 对应 REQ-ID | 验收标准 | 状态 |
|---------------|------|------------|---------|------|
| P-DO-01: 文档导入页每种类型独立操作区 | DO | REQ-001 | GWT-REQ-001-01 | ✅已覆盖 |
| P-DO-02: 每种文档类型展示最近导入结果 | DO | REQ-001 | GWT-REQ-001-04, GWT-REQ-001-05 | ✅已覆盖 |
| P-DO-03: 画像展示页右侧时间线 | DO | REQ-002 | GWT-REQ-002-01 | ✅已覆盖 |
| P-DO-04: 画像字段旁 inline diff | DO | REQ-003 | GWT-REQ-003-01 | ✅已覆盖 |
| P-DO-05: 采纳/忽略/恢复三种操作 | DO | REQ-003 | GWT-REQ-003-02 | ✅已覆盖 |
| P-DO-06: 文档导入触发 AI 结构化信息提取 | DO | REQ-004 | GWT-REQ-004-01 | ✅已覆盖 |
| P-DO-07: AI 信息提取前保存 ai_suggestions_previous | DO | REQ-004 | GWT-REQ-004-03 | ✅已覆盖 |
| P-DO-08: LLM 输出三点估计 | DO | REQ-006 | GWT-REQ-006-01 | ✅已覆盖 |
| P-DO-09: 三类口径并行追溯 | DO | REQ-006 | GWT-REQ-006-02 | ✅已覆盖 |
| P-DO-10: 发布前可一键回退到 v2.3 | DO | REQ-106 | GWT-REQ-106-01 | ✅已覆盖 |
| P-DO-11: 评估报告导出展示三点估计字段 | DO | REQ-007 | GWT-REQ-007-01 | ✅已覆盖 |
| P-DO-12: 评估流水线每步保存 AI 原始输出快照 | DO | REQ-009 | GWT-REQ-009-01 | ✅已覆盖 |
| P-DO-13: PM 提交后自动计算 diff 并落盘 | DO | REQ-010 | GWT-REQ-010-01, GWT-REQ-010-04 | ✅已覆盖 |
| P-DO-14: 系统画像新增 ai_correction_history | DO | REQ-010 | GWT-REQ-010-02 | ✅已覆盖 |
| P-DO-15: LLM 估算 prompt 注入三层知识 | DO | REQ-006 | GWT-REQ-006-03, GWT-REQ-006-04 | ✅已覆盖 |
| P-DO-16: 导入成功后提供"查看系统画像"跳转 | DO | REQ-001 | GWT-REQ-001-03 | ✅已覆盖 |
| P-DO-17: 多系统文档仅应用选中系统+通知 | DO | REQ-005 | GWT-REQ-005-01 | ✅已覆盖 |
| P-DO-18: 评估页期望值主展示+Delphi 用期望值 | DO | REQ-008 | GWT-REQ-008-01 | ✅已覆盖 |
| P-DO-19: 代码扫描入库触发 AI 结构化信息提取 | DO | REQ-004 | GWT-REQ-004-02 | ✅已覆盖 |
| P-DO-20: PM 写操作绑定负责系统 | DO | REQ-011 | GWT-REQ-011-01 | ✅已覆盖 |
| P-DO-21: 画像重构为 5 域结构+域导航布局 | DO | REQ-012 | GWT-REQ-012-01 | ✅已覆盖 |
| P-DO-22: AI 提取输出映射 5 域 12 子字段 schema | DO | REQ-012 | GWT-REQ-012-03 | ✅已覆盖 |
| P-DONT-01: 禁止切换丢状态 | DONT | REQ-C001 | GWT-REQ-C001-01 | ✅已覆盖 |
| P-DONT-02: 禁止 AI 建议更新后无法恢复 | DONT | REQ-C002 | GWT-REQ-C002-01 | ✅已覆盖 |
| P-DONT-03: 禁止工作量估算仍为静态映射 | DONT | REQ-C003 | GWT-REQ-C003-01 | ✅已覆盖 |
| P-DONT-04: 禁止新增独立页面或菜单路由 | DONT | REQ-C004 | GWT-REQ-C004-01 | ✅已覆盖 |
| P-DONT-05: 禁止 PM 修正数据丢失 | DONT | REQ-C005 | GWT-REQ-C005-01 | ✅已覆盖 |
| P-DONT-06: 禁止自动覆盖非选中系统画像 | DONT | REQ-C006 | GWT-REQ-C006-01 | ✅已覆盖 |
| P-DONT-07: 禁止画像域重构后语义覆盖缺失 | DONT | REQ-C007 | GWT-REQ-C007-01 | ✅已覆盖 |
| P-METRIC-01: 5 种文档类型交叉零丢失 | METRIC | REQ-101 | GWT-REQ-101-01 | ✅已覆盖 |
| P-METRIC-02: 画像变更事件 100% 记入时间线 | METRIC | REQ-102 | GWT-REQ-102-01 | ✅已覆盖 |
| P-METRIC-03: AI 建议回滚成功率 100% | METRIC | REQ-103 | GWT-REQ-103-01 | ✅已覆盖 |
| P-METRIC-04: 估算五字段输出+导出可核对 | METRIC | REQ-104 | GWT-REQ-104-01 | ✅已覆盖 |
| P-METRIC-05: 快照+diff+画像字段可查询 | METRIC | REQ-105 | GWT-REQ-105-01 | ✅已覆盖 |

> 门禁验证：已映射 34 条（22 DO + 7 DONT + 5 METRIC）= proposal 锚点总数 34，无遗漏，无 defer。
> ✅ 正文验证完成：§2（场景）§3（功能需求）§4（非功能需求）§4A（禁止项）§5（权限）§6（数据接口）均已落盘，覆盖映射与正文定义一致。

## 2. 业务场景说明

### 2.1 角色与对象

**角色**（沿用 v2.3，本次不新增角色）
- manager（项目经理）：导入文档、审核画像、查看/修改评估结果、提交评估修改
- admin（管理员）：系统管理、画像发布审核
- expert（专家）：参与评估（本次变更不直接影响专家操作流程，但估算输入质量改善间接影响专家体验）

**核心对象（v2.4 新增/扩展）**
| 对象 | 说明 | 新增/扩展 |
|---|---|---|
| `ai_suggestions` | 系统画像各字段的 AI 建议值 | 扩展（从自由文本升级为结构化字段映射） |
| `ai_suggestions_previous` | `ai_suggestions` 上一版快照 | 新增 |
| `profile_events` | 画像变更事件日志 | 新增 |
| `ai_correction_history` | PM 修正模式累计记录 | 新增 |
| `ai_original_output` | 评估流水线各步 AI 原始输出快照 | 新增 |
| `pm_correction_diff` | PM 修正 diff 记录 | 新增 |
| 三点估计字段 | optimistic/most_likely/pessimistic/expected/reasoning | 新增 |

### 2.2 场景列表

| 场景分类 | 场景ID | 场景名称 | 场景说明 | 主要角色 |
|---|---|---|---|---|
| CAT-C 证据与知识 | SCN-V24-01 | 多类型文档独立导入 | PM 为同一系统依次导入多种文档，各类型独立操作互不干扰 | manager |
| CAT-C 证据与知识 | SCN-V24-02 | 导入后查看画像影响 | PM 导入文档成功后跳转画像展示页，查看 AI 建议变化 | manager |
| CAT-C 证据与知识 | SCN-V24-03 | 多系统文档导入与通知 | PM 导入的文档涉及多个系统，仅更新选中系统，通知其他系统信息 | manager |
| CAT-C 证据与知识 | SCN-V24-04 | AI 结构化信息提取 | 文档导入或代码扫描入库后自动触发 AI 提取，映射到画像字段 | manager |
| CAT-C 证据与知识 | SCN-V24-05 | 画像变更时间线查看 | PM 在画像展示页查看变更历史时间线 | manager |
| CAT-C 证据与知识 | SCN-V24-06 | AI 建议审阅与操作 | PM 通过 inline diff 逐字段审阅 AI 建议，决定采纳/忽略/回滚 | manager |
| CAT-C 证据与知识 | SCN-V24-07 | AI 建议回滚 | PM 发现新导入导致画像退化，回滚到上一版建议 | manager |
| CAT-B 任务评估主链路 | SCN-V24-08 | LLM 工作量估算 | 评估流水线中 LLM 输出三点估计替代静态映射 | manager |
| CAT-B 任务评估主链路 | SCN-V24-09 | 评估页三点估计查看 | PM 在评估页查看期望值，展开查看乐观/悲观/理由 | manager |
| CAT-B 任务评估主链路 | SCN-V24-10 | 评估报告导出含三点估计 | 导出 Excel 报告包含三点估计独立列 | manager/admin |
| CAT-B 任务评估主链路 | SCN-V24-11 | AI 原始输出快照与 PM 修正沉淀 | 评估完成后系统自动保存快照、计算 diff、更新 ai_correction_history | manager |
| CAT-A 账号与权限 | SCN-V24-12 | PM-系统写操作权限校验 | PM 写操作严格绑定负责系统，跨系统进入只读模式 | manager |
### 2.3 场景明细

#### SCN-V24-01：多类型文档独立导入
**场景分类**：CAT-C 证据与知识
**主要角色**：manager
**相关对象**：SystemProfile、导入历史记录
**关联需求ID**：REQ-001
**前置条件**：
- PM 已登录，已选择目标系统
- PM 对该系统有写权限
**触发条件**：
- PM 进入系统画像导入页
**流程步骤**：
1. 页面展示 5 种文档类型（需求文档、设计文档、技术方案、ESB 接口申请模板、知识库文档），每种类型一行 Card
2. PM 在任意类型 Card 中选择文件并点击导入
3. 导入过程中，其他类型 Card 的已选文件和导入结果不受影响
4. 导入完成后，该 Card 展示最近一次导入结果（时间、文件名、成功/失败）
5. 页面底部展示该系统的导入历史列表（默认显示最近 3 条，其余折叠在"展开全部（共 N 条）"中）
**输出产物**：
- 文档入库、导入结果展示、导入历史记录更新
**异常与边界处理**：
- 文件格式不支持：提示错误，不影响其他类型状态
- 导入失败：Card 展示失败原因，其他类型不受影响

#### SCN-V24-02：导入后查看画像影响
**场景分类**：CAT-C 证据与知识
**主要角色**：manager
**相关对象**：SystemProfile、ai_suggestions
**关联需求ID**：REQ-001、REQ-004、REQ-003
**前置条件**：
- PM 刚完成一次文档导入且导入成功
**触发条件**：
- PM 点击导入结果区域的"查看系统画像"链接按钮
**流程步骤**：
1. 导入成功后，结果区域出现"查看系统画像"链接按钮
2. PM 点击后跳转到对应系统的画像展示页（`SystemProfileBoardPage`）
3. 画像展示页各字段旁展示 AI 新建议与当前值的 inline diff
4. PM 逐字段审阅，决定采纳或忽略
**输出产物**：
- 页面跳转、画像字段 inline diff 展示
**异常与边界处理**：
- AI 结构化提取尚未完成（异步任务进行中）：画像页提示"AI 正在分析文档，请稍后刷新"

#### SCN-V24-03：多系统文档导入与通知
**场景分类**：CAT-C 证据与知识
**主要角色**：manager
**相关对象**：SystemProfile、Notification
**关联需求ID**：REQ-005
**前置条件**：
- PM 已选择当前系统，导入的文档涉及多个系统的信息
**触发条件**：
- 文档导入成功并触发 AI 结构化信息提取
**流程步骤**：
1. AI 提取文档中所有系统的信息
2. 仅将当前选中系统的信息自动应用到该系统画像的 `ai_suggestions`
3. 若检测到其他系统信息，以通知形式提示 PM（如"检测到文档中还包含系统 X、Y 的信息，如需更新请前往对应系统操作"）
4. PM 点击通知中的跨系统链接，若非该系统负责 PM，进入只读模式并提示联系对应 PM
**输出产物**：
- 当前系统画像更新、其他系统通知
**异常与边界处理**：
- 文档中仅包含当前系统信息：无通知产生
- PM 无其他系统写权限：跨系统链接进入只读模式
#### SCN-V24-04：AI 结构化信息提取
**场景分类**：CAT-C 证据与知识
**主要角色**：manager（触发者）
**相关对象**：SystemProfile、ai_suggestions、ai_suggestions_previous、profile_events
**关联需求ID**：REQ-004
**前置条件**：
- 文档导入成功入库，或代码扫描作业完成入库
**触发条件**：
- 文档导入成功后自动触发（异步任务）
- 代码扫描入库完成后自动触发（异步任务）
**流程步骤**：
1. 系统将当前 `ai_suggestions` 保存到 `ai_suggestions_previous`（一级回滚备份）
2. AI 解析文档/扫描结果，将内容映射到画像各字段（系统描述、技术栈、业务能力、接口信息等）
3. 提取结果以 `ai_suggestions` 形式写入对应字段
4. 记录一条 `profile_events` 变更事件（类型：文档导入/代码扫描，时间，来源文件名，摘要）
**输出产物**：
- 画像各字段 `ai_suggestions` 更新、`ai_suggestions_previous` 备份、`profile_events` 新增事件
**异常与边界处理**：
- AI 提取超时或失败：记录失败事件到 `profile_events`，`ai_suggestions` 保持不变，前端提示"AI 分析失败，请重试"
- 文档内容为空或无法解析：不更新 `ai_suggestions`，记录事件

#### SCN-V24-05：画像变更时间线查看
**场景分类**：CAT-C 证据与知识
**主要角色**：manager
**相关对象**：profile_events
**关联需求ID**：REQ-002
**前置条件**：
- PM 已进入系统画像展示页
**触发条件**：
- PM 展开右侧时间线侧边栏
**流程步骤**：
1. 画像展示页右侧提供可折叠时间线侧边栏
2. 默认展示最近 20 条变更事件
3. 每条事件展示：变更类型图标、时间、来源、摘要
4. 底部提供"加载更多"分页按钮
5. 时间线数据全量保留不删除，仅通过前端分页控制加载量
**输出产物**：
- 时间线事件列表展示
**异常与边界处理**：
- 无变更事件：展示空态提示"暂无变更记录"
- 事件数量超过 20 条：底部显示"加载更多"

#### SCN-V24-06：AI 建议审阅与操作
**场景分类**：CAT-C 证据与知识
**主要角色**：manager
**相关对象**：SystemProfile、ai_suggestions
**关联需求ID**：REQ-003
**前置条件**：
- 画像存在 `ai_suggestions` 且与当前值不同
**触发条件**：
- PM 进入画像展示页
**流程步骤**：
1. 每个画像字段旁展示 inline diff（当前值 vs AI 新建议）
2. 每个有差异的字段提供三个操作按钮："采纳新建议"/"忽略"/"恢复上一版建议"
3. PM 点击"采纳新建议"：当前值更新为 AI 建议值
4. PM 点击"忽略"：隐藏该字段的 diff 提示（本次会话内）
5. PM 点击"恢复上一版建议"：将 `ai_suggestions` 恢复为 `ai_suggestions_previous` 的值
**输出产物**：
- 画像字段值更新（采纳时）、diff 提示隐藏（忽略时）、建议回滚（恢复时）
**异常与边界处理**：
- `ai_suggestions` 与当前值相同：该字段不展示 diff
- `ai_suggestions_previous` 不存在（首次导入）："恢复上一版建议"按钮置灰并提示"无历史版本"

#### SCN-V24-07：AI 建议回滚
**场景分类**：CAT-C 证据与知识
**主要角色**：manager
**相关对象**：SystemProfile、ai_suggestions、ai_suggestions_previous
**关联需求ID**：REQ-003
**前置条件**：
- `ai_suggestions_previous` 存在（至少经历过一次 AI 信息提取更新）
**触发条件**：
- PM 点击某字段的"恢复上一版建议"按钮
**流程步骤**：
1. 系统将该字段的 `ai_suggestions` 恢复为 `ai_suggestions_previous` 中的值
2. 记录一条 `profile_events` 回滚事件
3. inline diff 更新为恢复后的状态
**输出产物**：
- `ai_suggestions` 回滚、`profile_events` 新增回滚事件
**异常与边界处理**：
- 连续多次导入后回滚仅能恢复到上一版（一级回滚），更早版本不可恢复
#### SCN-V24-08：LLM 工作量估算
**场景分类**：CAT-B 任务评估主链路
**主要角色**：manager
**相关对象**：Feature、WorkEstimationAgent、三点估计字段
**关联需求ID**：REQ-006
**前置条件**：
- 评估流水线已完成功能拆分（Step 2），功能点列表已生成
**触发条件**：
- 评估流水线进入 Step 3（工作量估算）
**流程步骤**：
1. `WorkEstimationAgent` 调用 LLM（DashScope），prompt 注入三层知识：
   - 第一层：当前系统画像 5 域完整上下文（系统定位与边界、业务能力、集成与接口、技术架构、约束与风险），prompt 包含全部 5 域的结构化信息
   - 第二层：`ai_correction_history` 校准数据（≥3 次评估后启用；未达阈值时不注入）
   - 第三层：同系统历史评估结果（功能点名+描述+专家终值）作为 few-shot 参照（如有）
2. LLM 对每个功能点输出：optimistic、most_likely、pessimistic、reasoning
3. 系统根据 LLM 输出的 O/M/P 自动计算 expected = (O + 4M + P) / 6（PERT 公式），保留 2 位小数
4. 保留功能拆分 Agent 输出的原始 `预估人天` 为独立追溯字段，不被 Step 3 覆写
5. Step 3 AI 基线值使用系统计算的 expected 值（替代原静态映射）
6. 不执行 `apply_estimates_to_features()` 中的复杂度反向覆写逻辑（已移除）
**输出产物**：
- 每个功能点的三点估计 + 期望值 + 估算理由；三类口径（拆分原始估值/Step 3 AI 基线/专家最终估值）并行保留
**异常与边界处理**：
- LLM 调用失败：降级为功能拆分 Agent 的原始估值作为 AI 基线，记录降级事件
- 历史评估数据不足 3 次：第二层知识不注入，仅使用第一层和第三层
- 同系统无历史评估：第三层知识不注入，仅使用第一层（和第二层如满足阈值）

#### SCN-V24-09：评估页三点估计查看
**场景分类**：CAT-B 任务评估主链路
**主要角色**：manager
**相关对象**：Feature、三点估计字段
**关联需求ID**：REQ-008
**前置条件**：
- 评估流水线已完成工作量估算，功能点已有三点估计数据
**触发条件**：
- PM 进入评估页面（EvaluationPage）
**流程步骤**：
1. 功能点列表以期望值（expected）作为主展示值（替代原静态映射值）
2. PM 点击功能点行，行内展开（Ant Design Table expandable）浅色区域
3. 展开区域展示：乐观值、最可能值、悲观值、估算理由文本
4. Delphi 偏离度计算使用期望值（expected）作为 AI 基线
**输出产物**：
- 评估页面展示期望值 + 可展开明细
**异常与边界处理**：
- 三点估计数据缺失（LLM 降级场景）：展示功能拆分原始估值，展开区域提示"LLM 估算未成功，显示为拆分阶段原始估值"

#### SCN-V24-10：评估报告导出含三点估计
**场景分类**：CAT-B 任务评估主链路
**主要角色**：manager/admin
**相关对象**：ReportVersion、Excel 产物
**关联需求ID**：REQ-007
**前置条件**：
- 评估已完成，报告已生成
**触发条件**：
- 用户导出 Excel 报告
**流程步骤**：
1. Excel 报告新增独立列：optimistic、most_likely、pessimistic、expected、reasoning
2. 原"预估人天参考"列改为展示期望值（expected）
3. 评估报告页（ReportPage）功能点明细区域可展开查看三点估计与理由
**输出产物**：
- Excel 文件含三点估计字段；报告页可展开明细
**异常与边界处理**：
- 三点估计数据缺失：对应列填写"N/A"，reasoning 列填写"LLM 估算未成功"

#### SCN-V24-11：AI 原始输出快照与 PM 修正沉淀
**场景分类**：CAT-B 任务评估主链路
**主要角色**：manager
**相关对象**：ai_original_output、pm_correction_diff、ai_correction_history
**关联需求ID**：REQ-009、REQ-010
**前置条件**：
- 评估流水线正在执行或 PM 正在修改评估结果
**触发条件**：
- 流水线每步完成时自动保存快照；PM 提交修改时自动计算 diff
**流程步骤**：
1. 系统识别完成后，保存 AI 原始输出快照（系统列表 + 分层结果）
2. 功能拆分完成后，保存 AI 原始输出快照（各系统功能点列表）
3. 工作量估算完成后，保存 AI 原始输出快照（各功能点三点估计）
4. PM 在前端确认/修改后提交时，系统自动对比快照与 PM 最终版本
5. **Phase 1 diff（PM 提交时）**按系统维度落盘：系统级（新增/删除/改名）、功能点级（新增/删除/修改描述）
6. **Phase 2 diff（评估完成后）**：估值级（专家终值 vs AI 预估偏差）
7. Phase 2 完成后，系统自动聚合全部 diff 更新对应系统画像的 `ai_correction_history` 字段
**输出产物**：
- 三步 AI 原始输出快照、PM 修正 diff 记录、`ai_correction_history` 更新
**异常与边界处理**：
- PM 未做任何修改直接提交：diff 为空，不更新 `ai_correction_history`
- 评估中途取消：已保存的快照保留，不计算 diff，不更新 `ai_correction_history`

#### SCN-V24-12：PM-系统写操作权限校验
**场景分类**：CAT-A 账号与权限
**主要角色**：manager
**相关对象**：User、SystemProfile
**关联需求ID**：REQ-011
**前置条件**：
- PM 已登录
**触发条件**：
- PM 尝试对系统画像执行写操作（导入文档/编辑画像/采纳或回滚 AI 建议/提交评估修改）
**流程步骤**：
1. 系统校验 PM 是否为该系统的负责人
2. 若是：允许写操作
3. 若否：拒绝写操作，页面进入只读模式，提示"您无权编辑此系统，请联系对应负责人"
4. 查看所有系统画像为只读开放（不限制读权限）
5. 多系统文档通知中的跨系统链接：若 PM 非目标系统负责人，进入只读模式
**输出产物**：
- 写操作成功或只读模式提示
**异常与边界处理**：
- PM 负责多个系统：对所有负责系统均有写权限
- 系统无负责人：仅 admin 可操作

## 3. 功能性需求（Functional Requirements）

> **优先级说明**：M=Must / S=Should / C=Could / W=Won't。

### 3.1 功能性需求列表

| 需求分类 | REQ-ID | 需求名称 | 优先级 | 需求说明 | 关联场景ID |
|---|---|---|---|---|---|
| 文档导入 | REQ-001 | 文档导入页重构 | M | 每种文档类型独立操作区+导入历史+跳转链接 | SCN-V24-01/02 |
| 画像展示 | REQ-002 | 画像变更时间线 | M | 三区布局右侧可折叠时间线侧边栏展示变更历史 | SCN-V24-05 |
| 画像展示 | REQ-003 | 画像子字段 inline diff 与 AI 建议操作 | M | 子字段级 diff + 采纳/忽略/回滚 + 一级回滚 | SCN-V24-06/07 |
| AI 提取 | REQ-004 | AI 结构化信息提取 | M | 文档导入/代码扫描后自动触发，按域相关性映射到画像 5 域 12 子字段 | SCN-V24-04 |
| 多系统过滤 | REQ-005 | 多系统文档过滤与通知 | M | 策略 C：仅应用选中系统+通知其他 | SCN-V24-03 |
| 工作量估算 | REQ-006 | LLM 工作量估算 | M | 三点估计+三层知识注入+移除静态映射 | SCN-V24-08 |
| 报告导出 | REQ-007 | 评估报告导出增强 | M | Excel 新增三点估计独立列 | SCN-V24-10 |
| 评估展示 | REQ-008 | 评估页面三点估计展示 | M | 期望值主展示+行内展开明细+Delphi 用期望值 | SCN-V24-09 |
| 经验沉淀 | REQ-009 | AI 原始输出快照 | M | 流水线每步保存 AI 原始输出 | SCN-V24-11 |
| 经验沉淀 | REQ-010 | PM 修正 diff 与经验资产沉淀 | M | diff 计算+落盘+ai_correction_history 更新 | SCN-V24-11 |
| 权限 | REQ-011 | PM-系统写操作权限绑定 | M | 写操作绑定负责系统，读开放 | SCN-V24-12 |
| 画像展示 | REQ-012 | 系统画像域结构重构 | M | 5 域 12 子字段结构化模型+三区布局（域导航+内容区+时间线） | SCN-V24-05/06 |

### 3.2 功能性需求明细

#### REQ-001：文档导入页重构
**目标/价值**：消除下拉切换丢状态问题，让 PM 一目了然看到所有类型的导入状态和历史。
**入口/触发**：PM 进入 `SystemProfileImportPage`
**前置条件**：PM 已登录且对当前系统有写权限

**主流程**：
1. 页面以每种文档类型一行 Card 布局展示 5 种类型
2. 每行 Card 包含：左侧类型名+说明，右侧上传按钮+导入按钮+最近导入结果
3. PM 在任意 Card 中操作，不影响其他 Card 的状态
4. 导入成功后，结果区域展示"查看系统画像"链接按钮，点击跳转到对应系统画像展示页
5. 页面底部展示该系统的导入历史列表（默认显示最近 3 条，其余折叠）

**输入/输出**：
- 输入：文档文件（DOCX/XLSX/PDF 等）
- 输出：导入结果（成功/失败+原因）、导入历史记录

**页面与交互**：
- 涉及页面：`SystemProfileImportPage`
- 关键交互：Card 内上传+导入独立操作；导入历史折叠/展开；"查看系统画像"跳转
- 信息展示：每 Card 展示类型名、说明、最近导入结果（时间/文件名/状态）；底部导入历史列表

**业务规则**：
- 各类型 Card 状态完全独立，任何操作不影响其他类型
- 导入历史按时间倒序排列
- "查看系统画像"跳转为页内路由，不新增独立页面

**异常与边界**：
- 文件格式不支持：该 Card 提示错误，其他 Card 不受影响
- 导入失败：该 Card 展示失败原因
- 系统无导入历史：底部历史区域展示空态

**验收标准（GWT，必须可判定）**：
- [ ] GWTREF-REQ-001-01: Given PM 进入导入页，When 页面加载完成，Then 展示 5 种文档类型各一行 Card，每行含类型名+说明+上传按钮+导入按钮
- [ ] GWT-REQ-001-02: Given PM 已对类型 A 导入成功，When PM 在类型 B 的 Card 中选择文件，Then 类型 A 的导入结果和已选文件不受影响
- [ ] GWTREF-REQ-001-03: Given PM 导入成功，When 查看结果区域，Then 展示"查看系统画像"链接按钮，点击后跳转到对应系统画像展示页
- [ ] GWTREF-REQ-001-04: Given 系统有 N 条导入历史（N>3），When 页面加载，Then 默认展示最近 3 条，底部显示"展开全部（共 N 条）"
- [ ] GWTREF-REQ-001-05: Given PM 导入成功，When 查看该 Card，Then 展示最近一次导入结果（时间、文件名、成功状态）

**关联**：SCN-V24-01/02；REQ-004（导入触发 AI 提取）

#### REQ-002：画像变更时间线
**目标/价值**：让 PM 追溯画像每次变更的来源和时间，建立变更可审计能力。
**入口/触发**：PM 进入 `SystemProfileBoardPage`，展开三区布局右侧时间线侧边栏
**前置条件**：PM 已登录，已选择目标系统

**主流程**：
1. 画像展示页三区布局右侧提供可折叠时间线侧边栏（默认折叠）
2. PM 点击展开后，展示最近 20 条变更事件
3. 每条事件包含：变更类型图标、时间、来源、摘要
4. 底部提供"加载更多"分页按钮，每次加载 20 条
5. 时间线数据全量保留不删除（D14）

**输入/输出**：
- 输入：系统 ID
- 输出：`profile_events` 列表（分页）

**页面与交互**：
- 涉及页面：`SystemProfileBoardPage`
- 关键交互：侧边栏折叠/展开；分页加载
- 信息展示：事件类型图标、时间戳、来源（文件名/操作人）、变更摘要

**业务规则**：
- 事件类型包括：文档导入、代码扫描、手动编辑、AI 建议采纳、AI 建议回滚、画像发布
- 其中"手动编辑"和"画像发布"为既有功能，v2.4 需改造其写入逻辑以在操作完成时自动记录 `profile_events` 事件（既有功能改造点）
- 按时间倒序排列
- 全量保留不删除，仅通过前端分页控制加载量

**异常与边界**：
- 无变更事件：展示空态提示"暂无变更记录"
- 事件数量 ≤20：不显示"加载更多"

**验收标准（GWT，必须可判定）**：
- [ ] GWTREF-REQ-002-01: Given PM 进入画像展示页，When 展开右侧时间线，Then 展示最近 20 条变更事件，每条含类型图标+时间+来源+摘要
- [ ] GWT-REQ-002-02: Given 变更事件超过 20 条，When PM 点击"加载更多"，Then 加载下一批 20 条事件
- [ ] GWT-REQ-002-03: Given 系统无变更事件，When PM 展开时间线，Then 展示"暂无变更记录"空态提示

**关联**：SCN-V24-05；REQ-004（事件写入来源）

#### REQ-003：画像子字段 inline diff 与 AI 建议操作
**目标/价值**：让 PM 逐子字段对比 AI 建议与当前值，按需采纳/忽略/回滚，避免 AI 建议盲目覆盖。
**入口/触发**：PM 进入 `SystemProfileBoardPage`，画像存在 `ai_suggestions` 且与当前值不同
**前置条件**：至少经历过一次 AI 结构化信息提取

**主流程**：
1. 每个画像域内的子字段旁展示 inline diff（当前值 vs AI 新建议）
2. 每个有差异的子字段提供三个操作按钮："采纳新建议"/"忽略"/"恢复上一版建议"
3. PM 点击"采纳新建议"：当前值更新为 AI 建议值，记录 `profile_events` 事件
4. PM 点击"忽略"：隐藏该子字段的 diff 提示（本次会话内）
5. PM 点击"恢复上一版建议"：将该子字段的 `ai_suggestions` 恢复为 `ai_suggestions_previous` 中的值，记录回滚事件

**输入/输出**：
- 输入：系统画像当前值、`ai_suggestions`、`ai_suggestions_previous`
- 输出：字段值更新（采纳时）、diff 隐藏（忽略时）、建议回滚（恢复时）

**页面与交互**：
- 涉及页面：`SystemProfileBoardPage`
- 关键交互：inline diff 展示；三按钮操作；忽略后本次会话隐藏
- 信息展示：当前值（左）vs AI 建议值（右），差异高亮

**业务规则**：
- `ai_suggestions` 与当前值相同的子字段不展示 diff
- "忽略"仅影响本次会话，刷新页面后 diff 重新展示
- "恢复上一版建议"为子字段级操作，不影响其他子字段
- 每次 AI 信息提取前，系统自动将当前 `ai_suggestions` 保存到 `ai_suggestions_previous`

**异常与边界**：
- `ai_suggestions_previous` 不存在（首次导入）："恢复上一版建议"按钮置灰并提示"无历史版本"
- 连续多次导入后回滚仅能恢复到上一版（一级回滚）

**验收标准（GWT，必须可判定）**：
- [ ] GWTREF-REQ-003-01: Given 画像子字段 A 的 `ai_suggestions` 与当前值不同，When PM 进入画像展示页，Then 子字段 A 旁展示 inline diff（当前值 vs AI 建议）
- [ ] GWTREF-REQ-003-02: Given 子字段 A 展示 diff，When PM 点击"采纳新建议"，Then 子字段 A 当前值更新为 AI 建议值
- [ ] GWT-REQ-003-03: Given `ai_suggestions_previous` 存在，When PM 点击"恢复上一版建议"，Then 该子字段 `ai_suggestions` 恢复为 `ai_suggestions_previous` 的值，并记录回滚事件
- [ ] GWT-REQ-003-04: Given `ai_suggestions_previous` 不存在，When PM 查看"恢复上一版建议"按钮，Then 按钮置灰并提示"无历史版本"
- [ ] GWT-REQ-003-05: Given 子字段 A 展示 diff，When PM 点击"忽略"，Then 该子字段 diff 提示隐藏（本次会话内）

**关联**：SCN-V24-06/07；REQ-004（AI 建议来源）

#### REQ-004：AI 结构化信息提取
**目标/价值**：文档导入或代码扫描后自动将内容映射到画像各字段，替代人工逐字段填写。
**入口/触发**：文档导入成功入库后自动触发（异步）；代码扫描作业完成入库后自动触发（异步）
**前置条件**：文档已成功入库或代码扫描已完成

**主流程**：
1. 系统将当前 `ai_suggestions` 保存到 `ai_suggestions_previous`（一级回滚备份，全量备份确保回滚完整性）
2. 调用 DashScope API，AI 解析文档/扫描结果，采用两步提取策略：
   - 第一步：LLM 先输出 `relevant_domains` 列表，判断文档与 5 域（系统定位与边界/业务能力/集成与接口/技术架构/约束与风险）中哪些域相关
   - 第二步：仅对相关域输出结构化子字段数据
3. 将提取结果按 5 域 12 子字段的结构化 JSON schema 映射到画像 `ai_suggestions`，遵循"域内替换、域间保留"原则：对判定相关的域，`ai_suggestions` 中该域整体替换；不相关的域保持 `ai_suggestions` 不变
4. 记录一条 `profile_events` 变更事件（类型：文档导入/代码扫描，时间，来源文件名，摘要，标注本次更新了哪些域）
5. 若文档涉及多个系统，仅将当前选中系统的信息应用到画像，其他系统信息交由 REQ-005 处理

**输入/输出**：
- 输入：文档内容/代码扫描结果、当前系统 ID
- 输出：`ai_suggestions` 更新、`ai_suggestions_previous` 备份、`profile_events` 新增事件

**业务规则**：
- 异步任务处理，不阻塞导入操作本身
- 同一系统同一时刻仅允许一个 AI 结构化信息提取任务运行；若前一任务尚未完成，新导入触发的提取任务排队等待（串行化），确保 `ai_suggestions_previous` 备份的完整性
- 前端通过轮询 `/api/v1/system-profiles/{system_id}/profile/extraction-status` 获知任务完成状态，完成后自动刷新画像数据
- 每次提取前必须先备份 `ai_suggestions` 到 `ai_suggestions_previous`（全量备份）
- 提取结果以子字段级粒度映射到 5 域 12 子字段结构化 schema（具体子字段定义见 REQ-012）
- **按域相关性选择性更新**：AI 判断文档内容与各域的相关性，仅更新相关域的 `ai_suggestions`，不相关的域不强行更新（不写入空值或占位值）
- 相关域的子字段允许为空（文档未提及该子字段时），不强制填充

**异常与边界**：
- AI 提取超时或失败：记录失败事件到 `profile_events`，`ai_suggestions` 保持不变，前端提示"AI 分析失败，请重试"
- 文档内容为空或无法解析：不更新 `ai_suggestions`，记录事件
- 异步任务进行中：画像页提示"AI 正在分析文档，请稍后刷新"

**验收标准（GWT，必须可判定）**：
- [ ] GWTREF-REQ-004-01: Given PM 导入文档成功，When 异步任务完成，Then 对应系统画像各字段的 `ai_suggestions` 已更新为提取结果
- [ ] GWTREF-REQ-004-02: Given 代码扫描作业完成入库，When 异步任务完成，Then 对应系统画像各字段的 `ai_suggestions` 已更新
- [ ] GWTREF-REQ-004-03: Given AI 提取执行前，When 检查数据，Then `ai_suggestions_previous` 已保存为提取前的 `ai_suggestions` 值
- [ ] GWT-REQ-004-04: Given AI 提取失败，When PM 查看画像，Then `ai_suggestions` 保持不变，`profile_events` 记录失败事件
- [ ] GWT-REQ-004-05: Given 系统 A 的提取任务 T1 正在执行且 PM 再次导入触发任务 T2，When 查询任务状态并等待 T1 完成，Then T2 在 T1 完成前保持 `pending`，并在 T1 完成后才开始执行（同系统串行化）
- [ ] GWT-REQ-004-06: Given 导入文档仅与 D3（集成与接口）相关且提取前 `ai_suggestions` 已包含 D1~D5 旧值，When 提取完成，Then 仅 D3 域被更新，D1/D2/D4/D5 与提取前完全一致且未写入空值/占位值

**关联**：SCN-V24-04；REQ-001（触发源）；REQ-003（结果展示）；REQ-005（多系统过滤）

#### REQ-005：多系统文档过滤与通知
**目标/价值**：避免多系统文档导入时误覆盖非选中系统画像，同时不遗漏其他系统信息。
**入口/触发**：AI 结构化信息提取检测到文档涉及多个系统
**前置条件**：文档导入成功并触发 AI 提取

**主流程**：
1. AI 提取文档中所有系统的信息
2. 仅将当前选中系统的信息自动应用到该系统画像的 `ai_suggestions`
3. 若检测到其他系统信息，以通知形式提示 PM（如"检测到文档中还包含系统 X、Y 的信息，如需更新请前往对应系统操作"）
4. PM 点击通知中的跨系统链接，若非该系统负责 PM，进入只读模式并提示联系对应 PM

**输入/输出**：
- 输入：AI 提取的全部系统信息、当前选中系统 ID
- 输出：当前系统画像更新、其他系统通知列表

**业务规则**：
- 仅自动应用选中系统信息，绝不自动覆盖其他系统
- 通知中包含检测到的系统名称列表和跳转链接
- 跨系统链接遵循 REQ-011 权限规则

**异常与边界**：
- 文档仅包含当前系统信息：无通知产生
- PM 无其他系统写权限：跨系统链接进入只读模式

**验收标准（GWT，必须可判定）**：
- [ ] GWTREF-REQ-005-01: Given 文档涉及系统 A（选中）和系统 B，When AI 提取完成，Then 仅系统 A 的 `ai_suggestions` 被更新，系统 B 不受影响
- [ ] GWT-REQ-005-02: Given 检测到其他系统信息，When PM 查看通知，Then 通知包含其他系统名称和跳转链接
- [ ] GWT-REQ-005-03: Given 文档仅含当前系统信息，When AI 提取完成，Then 无多系统通知产生

**关联**：SCN-V24-03；REQ-004（提取过程）；REQ-011（权限校验）

#### REQ-006：LLM 工作量估算
**目标/价值**：用 LLM 替代静态映射，输出有理由可追溯的三点估计，提升估算质量。
**入口/触发**：评估流水线进入 Step 3（工作量估算）
**前置条件**：功能拆分（Step 2）已完成，功能点列表已生成

**主流程**：
1. `WorkEstimationAgent` 调用 LLM（DashScope），prompt 注入三层知识：
   - 第一层：当前系统画像 5 域完整上下文（系统定位与边界、业务能力、集成与接口、技术架构、约束与风险），prompt 包含全部 5 域的结构化信息
   - 第二层：`ai_correction_history` 校准数据（≥3 次评估后启用；未达阈值时不注入）
   - 第三层：同系统历史评估结果（功能点名+描述+专家终值）作为 few-shot 参照（如有）
2. LLM 对每个功能点输出：optimistic、most_likely、pessimistic、reasoning
3. 系统根据 LLM 输出的 O/M/P 自动计算 expected = (O + 4M + P) / 6（PERT 公式），保留 2 位小数
4. 保留功能拆分 Agent 输出的原始 `预估人天` 为独立追溯字段，不被 Step 3 覆写
5. Step 3 AI 基线值使用系统计算的 expected 值（替代原静态映射）
6. 不执行复杂度反向覆写逻辑（已移除）

**输入/输出**：
- 输入：功能点列表（名称+描述+复杂度）、系统画像 5 域完整上下文、ai_correction_history、历史评估结果
- 输出：每个功能点的三点估计 + 期望值 + 估算理由

**业务规则**：
- 三类口径并行保留：拆分原始估值 / Step 3 AI 基线（expected）/ 专家最终估值
- 期望值计算公式：expected = (O + 4M + P) / 6
- 第二层知识仅在该系统评估次数 ≥3 时注入
- 第三层知识仅在同系统存在历史评估数据时注入

**异常与边界**：
- LLM 调用失败：降级为功能拆分 Agent 的原始估值作为 AI 基线，记录降级事件，并返回 HTTP 200（`degraded=true`，`code=LLM_ESTIMATION_DEGRADED`）
- 历史评估数据不足 3 次：第二层知识不注入
- 同系统无历史评估：第三层知识不注入

**验收标准（GWT，必须可判定）**：
- [ ] GWTREF-REQ-006-01: Given 评估流水线进入 Step 3，When LLM 估算完成，Then 每个功能点包含 optimistic/most_likely/pessimistic/expected/reasoning 五个字段
- [ ] GWTREF-REQ-006-02: Given 估算完成，When 查看功能点数据，Then 拆分原始估值、Step 3 AI 基线值、专家最终估值三类口径均独立保留
- [ ] GWTREF-REQ-006-03: Given 系统评估次数 ≥3 且有 ai_correction_history，When LLM 估算，Then prompt 包含第二层知识（ai_correction_history 校准数据）
- [ ] GWTREF-REQ-006-04: Given 同系统存在历史评估结果，When LLM 估算，Then prompt 包含第三层知识（历史功能点名+描述+专家终值作为 few-shot 参照）
- [ ] GWT-REQ-006-05: Given LLM 调用失败，When 查看估算接口响应与功能点估算值，Then 返回 HTTP 200 且 `degraded=true`/`code=LLM_ESTIMATION_DEGRADED`，AI 基线降级为功能拆分原始估值并记录降级事件

**关联**：SCN-V24-08；REQ-009（快照保存）；REQ-010（diff 计算）

#### REQ-007：评估报告导出增强
**目标/价值**：Excel 报告包含三点估计独立列，支持导出后核对与审计。
**入口/触发**：用户导出 Excel 报告
**前置条件**：评估已完成，报告已生成

**主流程**：
1. Excel 报告新增独立列：optimistic、most_likely、pessimistic、expected、reasoning
2. 原"预估人天参考"列改为展示期望值（expected）
3. 评估报告页（ReportPage）功能点明细区域可展开查看三点估计与理由

**输入/输出**：
- 输入：评估结果数据（含三点估计）
- 输出：Excel 文件含三点估计字段；报告页可展开明细

**页面与交互**：
- 涉及页面：`ReportPage`
- 关键交互：功能点行展开查看三点估计明细与理由
- Excel 导出：新增 5 列（optimistic/most_likely/pessimistic/expected/reasoning）

**业务规则**：
- Excel 列顺序：在原有列之后追加三点估计相关列
- 原"预估人天参考"列语义变更为期望值

**异常与边界**：
- 三点估计数据缺失（LLM 降级场景）：对应列填写"N/A"，reasoning 列填写"LLM 估算未成功"

**验收标准（GWT，必须可判定）**：
- [ ] GWTREF-REQ-007-01: Given 评估已完成，When 用户导出 Excel，Then 文件包含 optimistic/most_likely/pessimistic/expected/reasoning 独立列
- [ ] GWT-REQ-007-02: Given 三点估计数据缺失，When 导出 Excel，Then 对应列填写"N/A"，reasoning 填写"LLM 估算未成功"
- [ ] GWT-REQ-007-03: Given 评估已完成，When PM 在报告页点击功能点行，Then 展开区域展示三点估计与理由

**关联**：SCN-V24-10；REQ-006（数据来源）

#### REQ-008：评估页面三点估计展示
**目标/价值**：评估页以期望值为主展示，可展开查看明细，Delphi 偏离度使用期望值作为基线。
**入口/触发**：PM 进入评估页面（EvaluationPage）
**前置条件**：评估流水线已完成工作量估算

**主流程**：
1. 功能点列表以期望值（expected）作为主展示值
2. PM 点击功能点行，行内展开（Ant Design Table expandable）浅色区域
3. 展开区域展示：乐观值、最可能值、悲观值、估算理由文本
4. Delphi 偏离度计算使用期望值（expected）作为 AI 基线

**输入/输出**：
- 输入：功能点三点估计数据
- 输出：评估页面展示期望值 + 可展开明细

**页面与交互**：
- 涉及页面：`EvaluationPage`
- 关键交互：行内展开/折叠（Ant Design Table expandable）
- 信息展示：主列显示期望值；展开区域显示 O/M/P + reasoning

**业务规则**：
- 期望值替代原静态映射值作为主展示
- Delphi 偏离度公式中 AI 基线改用 expected 值

**异常与边界**：
- 三点估计数据缺失（LLM 降级）：展示功能拆分原始估值，展开区域提示"LLM 估算未成功，显示为拆分阶段原始估值"

**验收标准（GWT，必须可判定）**：
- [ ] GWTREF-REQ-008-01: Given 功能点有三点估计数据，When PM 进入评估页，Then 功能点列表主列展示期望值（expected）
- [ ] GWT-REQ-008-02: Given PM 点击功能点行，When 行展开，Then 浅色区域展示乐观值/最可能值/悲观值/估算理由
- [ ] GWT-REQ-008-03: Given 三点估计缺失，When PM 查看功能点，Then 主列展示拆分原始估值，展开区域提示"LLM 估算未成功"

**关联**：SCN-V24-09；REQ-006（数据来源）

#### REQ-009：AI 原始输出快照
**目标/价值**：保留评估流水线每步的 AI 原始输出，为 PM 修正 diff 计算和经验沉淀提供基线。
**入口/触发**：评估流水线每步（系统识别/功能拆分/工作量估算）完成时自动保存
**前置条件**：评估流水线正在执行

**主流程**：
1. 系统识别完成后，保存 AI 原始输出快照（系统列表 + 分层结果）
2. 功能拆分完成后，保存 AI 原始输出快照（各系统功能点列表）
3. 工作量估算完成后，保存 AI 原始输出快照（各功能点三点估计）
4. 快照以 `ai_original_output` 形式按 task 维度存储，JSON 格式

**输入/输出**：
- 输入：各步骤 AI 输出结果
- 输出：`ai_original_output` 快照记录（三步各一份）

**业务规则**：
- 快照为只读，保存后不可修改
- 按 task（评估任务）维度存储，每次评估独立
- 快照内容为 JSON 文本，KB 级数据量

**异常与边界**：
- 评估中途取消：已保存的快照保留，不删除
- 某步骤失败：该步骤无快照，不影响已保存的其他步骤快照

**验收标准（GWT，必须可判定）**：
- [ ] GWTREF-REQ-009-01: Given 评估流水线完成系统识别，When 查询 ai_original_output，Then 存在系统识别步骤的快照数据
- [ ] GWT-REQ-009-02: Given 评估流水线三步全部完成，When 查询 ai_original_output，Then 存在三份独立快照（系统识别/功能拆分/工作量估算）
- [ ] GWT-REQ-009-03: Given 评估中途取消（仅完成前两步），When 查询 ai_original_output，Then 已完成步骤的快照保留

**关联**：SCN-V24-11；REQ-010（diff 基线）

#### REQ-010：PM 修正 diff 与经验资产沉淀
**目标/价值**：自动计算 PM 修正与 AI 原始输出的差异，沉淀为系统级校准因子，形成 AI 改进闭环。
**入口/触发**：PM 在前端确认/修改后提交时自动计算 diff；评估完成后自动更新 `ai_correction_history`
**前置条件**：`ai_original_output` 快照已保存

**主流程**：
1. PM 在前端确认/修改评估结果后提交
2. 系统自动对比 `ai_original_output` 快照与 PM 最终确认版本
3. **Phase 1 diff（PM 提交时立即计算）**按系统维度落盘，分类记录：
   - 系统级：新增/删除/改名
   - 功能点级：新增/删除/修改描述
4. **Phase 2 diff（评估完成后计算）**：
   - 估值级：专家终值 vs AI 预估偏差（需等待专家评估完成后方可计算）
5. Phase 2 完成后，系统自动聚合全部 diff 更新对应系统画像的 `ai_correction_history` 字段
6. `ai_correction_history` 累计记录：修正次数、偏差方向、常见遗漏模式等

**输入/输出**：
- 输入：`ai_original_output` 快照、PM 最终确认版本
- 输出：`pm_correction_diff` 记录、`ai_correction_history` 更新

**业务规则**：
- diff 仅做增删改三类识别，不做合并/拆分（D17）
- PM 未做任何修改直接提交：diff 为空，不更新 `ai_correction_history`
- `ai_correction_history` 为累计聚合，每次评估追加而非覆盖

**异常与边界**：
- 评估中途取消：已保存的快照保留，不计算 diff，不更新 `ai_correction_history`
- diff 为空（PM 无修改）：不更新 `ai_correction_history`

**验收标准（GWT，必须可判定）**：
- [ ] GWTREF-REQ-010-01: Given PM 修改了评估结果并提交，When 查询 pm_correction_diff，Then 存在按系统维度的 diff 记录（含系统级/功能点级分类）
- [ ] GWTREF-REQ-010-02: Given PM 修改了评估结果并提交且评估完成（含专家评估），When 查询对应系统画像，Then `ai_correction_history` 字段已自动更新（修正次数+1）
- [ ] GWT-REQ-010-03: Given PM 未做任何修改直接提交，When 查询 pm_correction_diff，Then diff 为空，`ai_correction_history` 未变化
- [ ] GWTREF-REQ-010-04: Given PM 修改了评估结果并提交且评估完成（含专家评估），When 查询 pm_correction_diff，Then 存在估值级 diff 分类（专家终值 vs AI 预估偏差）

**关联**：SCN-V24-11；REQ-009（快照基线）；REQ-006（校准注入）

#### REQ-011：PM-系统写操作权限绑定
**目标/价值**：确保 PM 只能修改自己负责的系统，防止跨系统误操作，同时保持读权限开放。
**入口/触发**：PM 尝试对系统画像执行写操作（文档导入/画像编辑/AI 建议采纳/AI 建议回滚/评估结果修改提交）
**前置条件**：PM 已登录

**主流程**：
1. 系统校验 PM 是否为该系统的负责人
2. 若是：允许写操作
3. 若否：拒绝写操作，页面进入只读模式，提示"您无权编辑此系统，请联系对应负责人"
4. 查看所有系统画像为只读开放（不限制读权限）
5. 多系统文档通知中的跨系统链接：若 PM 非目标系统负责人，进入只读模式

**输入/输出**：
- 输入：PM 用户 ID、目标系统 ID
- 输出：写操作允许/拒绝

**业务规则**：
- 写操作包括：文档导入、画像编辑、AI 建议采纳、AI 建议回滚、评估结果修改提交
- PM 可负责多个系统，对所有负责系统均有写权限
- 系统无负责人时：仅 admin 可操作
- 读权限完全开放，不做限制

**异常与边界**：
- PM 负责多个系统：对所有负责系统均有写权限
- 系统无负责人：仅 admin 可操作
- admin 角色：不受 PM-系统绑定限制

**验收标准（GWT，必须可判定）**：
- [ ] GWTREF-REQ-011-01: Given PM-A 负责系统 X，When PM-A 对系统 X 执行导入操作，Then 操作成功
- [ ] GWT-REQ-011-02: Given PM-A 不负责系统 Y，When PM-A 尝试对系统 Y 执行写操作，Then 操作被拒绝，页面进入只读模式并提示
- [ ] GWT-REQ-011-03: Given PM-A 不负责系统 Y，When PM-A 查看系统 Y 画像，Then 可正常查看（只读）
- [ ] GWT-REQ-011-04: Given 系统 Z 无负责人，When PM 尝试写操作，Then 操作被拒绝，仅 admin 可操作

**关联**：SCN-V24-12；REQ-005（跨系统通知权限）

#### REQ-012：系统画像域结构重构
**目标/价值**：将系统画像从 4 个扁平字段重构为 5 域 12 子字段的结构化模型，使画像不仅服务于工作量估算，还能用于需求分析和架构评审；同时消除 `document_parser.py` 已提取但未持久化的数据断裂。
**入口/触发**：PM 进入 `SystemProfileBoardPage`
**前置条件**：PM 已登录，已选择目标系统

**主流程**：
1. 画像展示页采用三区布局：左侧域导航 | 中间内容区 | 右侧时间线（可折叠）
2. 左侧展示 5 个域导航项：系统定位与边界（D1）、业务能力（D2）、集成与接口（D3）、技术架构（D4）、约束与风险（D5）
3. PM 点击左侧域项，中间内容区展示该域的子字段编辑区
4. 保存草稿和发布操作保留在内容区底部
5. AI 结构化信息提取完成后，`ai_suggestions` 按 5 域 12 子字段的结构化 schema 存储

**输入/输出**：
- 输入：系统画像数据（`profile_data` 5 域嵌套结构）
- 输出：域导航+子字段编辑区展示

**页面与交互**：
- 涉及页面：`SystemProfileBoardPage`
- 关键交互：左侧域导航切换；中间子字段编辑；右侧时间线折叠/展开
- 信息展示：每域 2-3 个子字段，结构化类型（标签、枚举、小表格）天然限制篇幅

**业务规则**：
- 5 域 12 子字段定义：
  - D1 系统定位与边界：`system_description`（文本，≤300字）、`target_users`（标签列表）、`boundaries`（结构化列表，每条≤50字）
  - D2 业务能力：`module_structure`（结构化树，每模块含名称+职责≤100字+子模块）、`core_processes`（有序列表，每条含流程名+简述≤80字）
  - D3 集成与接口：`integration_points`（结构化表，每条含对端系统+协议+方向+简述）、`external_dependencies`（结构化表，每条含依赖名+类型+用途）
  - D4 技术架构：`architecture_positioning`（文本，≤200字）、`tech_stack`（分类标签，按层分类）、`performance_profile`（键值对，≤5项）
  - D5 约束与风险：`key_constraints`（分类列表，每条含类别标签+描述≤80字）、`known_risks`（结构化列表，每条含风险描述+影响级别）
- 新结构必须完整覆盖原 system_scope/module_structure/integration_points/key_constraints 的语义（REQ-C007）
- 切换域时，已编辑的子字段内容保持不变（草稿状态保留）

**异常与边界**：
- 画像无数据（新系统）：各域展示空态，PM 可直接编辑
- AI 提取尚未完成：域导航正常展示，子字段为空或展示既有数据

**验收标准（GWT，必须可判定）**：
- [ ] GWTREF-REQ-012-01: Given PM 进入画像展示页，When 页面加载，Then 左侧展示 5 个域导航项，点击任一域右侧展示对应子字段
- [ ] GWT-REQ-012-02: Given PM 编辑域 D1 的子字段并保存草稿，When 切换到域 D2 再切回 D1，Then D1 的编辑内容保持不变
- [ ] GWTREF-REQ-012-03: Given AI 结构化信息提取完成，When 查看 ai_suggestions，Then 建议值按 5 域 12 子字段的结构化 schema 存储
- [ ] GWT-REQ-012-04: Given 系统画像已有 5 域数据，When 评估流水线 Step 3 注入系统画像上下文（REQ-006 第一层知识），Then prompt 包含全部 5 域的结构化信息

**关联**：SCN-V24-05/06；REQ-003（子字段级 diff）；REQ-004（AI 提取映射）；REQ-006（知识注入）；REQ-C007（语义覆盖）

## 4. 非功能需求（Non-Functional Requirements）

> 对应 Proposal 覆盖映射表中 P-METRIC-01~05 + P-DO-10。

### 4.1 非功能需求列表

| 需求分类 | REQ-ID | 需求名称 | 优先级 | 需求说明 | 对应 Proposal 锚点 |
|---|---|---|---|---|---|
| 交互/可用性 | REQ-101 | 文档类型交叉操作零丢失 | M | 5 种文档类型交叉操作零状态丢失 | P-METRIC-01 |
| 可审计 | REQ-102 | 画像变更事件 100% 记入时间线 | M | 所有变更事件类型均记入时间线 | P-METRIC-02 |
| 可靠性 | REQ-103 | AI 建议回滚成功率 100% | M | 回滚后字段值与 previous 一致 | P-METRIC-03 |
| 数据完整性 | REQ-104 | 估算五字段输出且导出可核对 | M | LLM 成功时五字段非空，三渠道一致 | P-METRIC-04 |
| 数据完整性 | REQ-105 | 快照+diff+画像字段可查询 | M | 经验资产沉淀端到端可验证 | P-METRIC-05 |
| 可用性/回滚 | REQ-106 | 一键回退到 v2.3 | M | 执行回退命令后恢复 v2.3 功能 | P-DO-10 |

### 4.2 非功能需求明细

#### REQ-101：文档类型交叉操作零丢失
**目标/价值**：确保导入页重构后各类型 Card 状态完全独立，任何操作组合不产生状态丢失。
**度量方式**：手动测试 5 种文档类型交叉操作场景
**基线（v2.3）**：切换下拉框丢失已选文件和导入结果
**目标（v2.4）**：零状态丢失

**验收标准（GWT，必须可判定）**：
- [ ] GWTREF-REQ-101-01: Given PM 依次在 5 种文档类型 Card 中各选择一个文件，When 在任意 Card 中执行导入操作，Then 其余 4 个 Card 的已选文件和导入结果均保持不变

**关联**：REQ-001；P-METRIC-01；P-DONT-01

#### REQ-102：画像变更事件 100% 记入时间线
**目标/价值**：确保所有画像变更来源均被记录，建立完整审计链。
**度量方式**：逐类型验证事件记录完整性
**基线（v2.3）**：无变更历史
**目标（v2.4）**：所有变更事件（文档导入/代码扫描/手动编辑/AI 建议采纳/AI 建议回滚/画像发布）100% 记入时间线

**验收标准（GWT，必须可判定）**：
- [ ] GWTREF-REQ-102-01: Given 分别执行文档导入、代码扫描、手动编辑、AI 建议采纳、AI 建议回滚、画像发布操作各至少 1 次，When 查看时间线，Then 每种类型至少存在 1 条对应事件记录，且事件总数与操作总数一致

**关联**：REQ-002；P-METRIC-02

#### REQ-103：AI 建议回滚成功率 100%
**目标/价值**：确保一级回滚机制可靠，PM 可放心使用"恢复上一版建议"操作。
**度量方式**：回滚后字段值与 `ai_suggestions_previous` 一致性校验
**基线（v2.3）**：无回滚能力
**目标（v2.4）**：回滚操作成功率 100%

**验收标准（GWT，必须可判定）**：
- [ ] GWTREF-REQ-103-01: Given 画像字段 A 的 `ai_suggestions_previous` 值为 V1，When PM 点击该字段的"恢复上一版建议"，Then 该字段 `ai_suggestions` 恢复为 V1，且 `profile_events` 记录一条回滚事件

**关联**：REQ-003；P-METRIC-03；P-DONT-02

#### REQ-104：估算五字段输出且导出可核对
**目标/价值**：确保 LLM 估算结果完整输出，且在所有展示渠道（评估页/报告页/Excel）口径一致可核对。
**度量方式**：字段完整性检查 + 跨渠道数值一致性比对
**基线（v2.3）**：静态映射值（高=4/中=2.5/低=1.5），无理由
**目标（v2.4）**：LLM 成功场景下每个功能点输出 optimistic/most_likely/pessimistic/expected/reasoning 五字段，且评估页、报告页、Excel 三渠道 expected 值一致；LLM 失败场景按降级规则展示

**验收标准（GWT，必须可判定）**：
- [ ] GWTREF-REQ-104-01: Given 评估流水线完成工作量估算且 LLM 调用成功，When 查看任意功能点数据，Then 包含 optimistic/most_likely/pessimistic/expected/reasoning 五个字段且均非空
- [ ] GWT-REQ-104-02: Given 评估已完成且 LLM 调用成功，When 分别在评估页、报告页、Excel 导出中查看同一功能点的 expected 值，Then 三处数值一致
- [ ] GWT-REQ-104-03: Given LLM 调用失败，When 分别查看评估页与 Excel 导出，Then 评估页按 REQ-008 降级展示拆分原始估值且提示"LLM 估算未成功"，Excel 按 REQ-007 填写 N/A 且 reasoning 为"LLM 估算未成功"

**关联**：REQ-006、REQ-007、REQ-008；P-METRIC-04；P-DONT-03

#### REQ-105：快照+diff+画像字段可查询
**目标/价值**：确保经验资产沉淀机制端到端可验证，数据链路完整闭合。
**度量方式**：API 查询验证数据存在性与完整性
**基线（v2.3）**：PM 修正数据用完即弃
**目标（v2.4）**：AI 原始输出快照、PM 修正 diff、系统画像 `ai_correction_history` 均可通过 API 查询

**验收标准（GWT，必须可判定）**：
- [ ] GWTREF-REQ-105-01: Given 评估流水线三步全部完成且 PM 提交修改，When 通过 API 查询，Then `ai_original_output` 存在三份快照、`pm_correction_diff` 存在 diff 记录、对应系统画像 `ai_correction_history` 已更新

**关联**：REQ-009、REQ-010；P-METRIC-05；P-DONT-05

#### REQ-106：一键回退到 v2.3
**目标/价值**：确保上线后如出现严重问题可快速回退，降低发布风险。
**度量方式**：执行回退命令后系统恢复到 v2.3 功能状态
**基线**：无
**目标（v2.4）**：支持一键回退

**验收标准（GWT，必须可判定）**：
- [ ] GWTREF-REQ-106-01: Given v2.4 已部署运行，When 执行 `git checkout v2.3 && bash deploy-all.sh`，Then 系统恢复到 v2.3 功能状态，所有 v2.3 功能正常可用

**关联**：P-DO-10；status.md 回滚要点

## 4A. 禁止项/不做项确认清单（Constraints）

> 对应 Proposal 覆盖映射表中 P-DONT-01~06。每条禁止项均为硬约束，违反即判定验收失败。

### 4A.1 禁止项列表

| REQ-ID | 禁止项名称 | 适用范围 | 优先级 | 来源 | 关联GWT-ID |
|---|---|---|---|---|---|
| REQ-C001 | 禁止切换丢状态 | 全局（所有角色/状态） | M | proposal.md P-DONT-01 | GWTREF-REQ-C001-01 |
| REQ-C002 | 禁止 AI 建议更新后无法恢复 | 全局（所有角色/状态） | M | proposal.md P-DONT-02 | GWTREF-REQ-C002-01 |
| REQ-C003 | 禁止工作量估算仍为静态映射 | 全局（所有角色/状态） | M | proposal.md P-DONT-03 | GWTREF-REQ-C003-01 |
| REQ-C004 | 禁止新增独立页面或菜单路由 | 全局（所有角色/状态） | M | proposal.md P-DONT-04 | GWTREF-REQ-C004-01 |
| REQ-C005 | 禁止 PM 修正数据丢失 | 全局（所有角色/状态） | M | proposal.md P-DONT-05 | GWTREF-REQ-C005-01 |
| REQ-C006 | 禁止自动覆盖非选中系统画像 | 全局（所有角色/状态） | M | proposal.md P-DONT-06 | GWTREF-REQ-C006-01 |
| REQ-C007 | 禁止画像域重构后语义覆盖缺失 | 全局（所有角色/状态） | M | proposal.md P-DONT-07 | GWTREF-REQ-C007-01 |

### 4A.2 禁止项明细

#### REQ-C001：禁止切换丢状态
**适用范围**：全局（所有角色/状态）
**来源**：proposal.md P-DONT-01
**禁止行为**：文档导入页中，任何操作（选择文件、执行导入、查看结果）导致其他文档类型的已选文件或导入结果丢失。
**判定方式**：在任意两种文档类型 Card 中分别选择文件并导入，验证操作后双方状态均保持完整。

**验收标准（GWT，必须可判定）**：
- [ ] GWTREF-REQ-C001-01: Given PM 在类型 A 的 Card 中已选文件且导入成功，When PM 在类型 B 的 Card 中选择文件并执行导入，Then 类型 A 的已选文件和导入结果均未丢失

**关联**：REQ-001；P-DONT-01

#### REQ-C002：禁止 AI 建议更新后无法恢复
**适用范围**：全局（所有角色/状态）
**来源**：proposal.md P-DONT-02
**禁止行为**：AI 结构化信息提取更新 `ai_suggestions` 后，PM 无法恢复到更新前的建议值。
**判定方式**：执行 AI 信息提取后，验证"恢复上一版建议"操作可用且结果正确。

**验收标准（GWT，必须可判定）**：
- [ ] GWTREF-REQ-C002-01: Given AI 信息提取已更新 `ai_suggestions`，When PM 点击任意字段的"恢复上一版建议"，Then 该字段 `ai_suggestions` 恢复为提取前的值（`ai_suggestions_previous`）

**关联**：REQ-003、REQ-004；P-DONT-02

#### REQ-C003：禁止工作量估算仍为静态映射
**适用范围**：全局（所有角色/状态）
**来源**：proposal.md P-DONT-03
**禁止行为**：评估流水线 Step 3 工作量估算仍使用静态映射值（高=4.0/中=2.5/低=1.5）作为 AI 基线。
**判定方式**：执行评估流水线后，验证功能点的 AI 基线值来自 LLM 输出的 expected 值而非静态映射。

**验收标准（GWT，必须可判定）**：
- [ ] GWTREF-REQ-C003-01: Given 评估流水线完成 Step 3，When 查看功能点的 AI 基线值，Then 值来自 LLM 输出的 expected（非固定的 1.5/2.5/4.0），且每个功能点的值可能不同

**关联**：REQ-006；P-DONT-03

#### REQ-C004：禁止新增独立页面或菜单路由
**适用范围**：全局（所有角色/状态）
**来源**：proposal.md P-DONT-04
**禁止行为**：v2.4 新增独立页面或菜单路由条目。所有变更必须在既有 4 个页面内完成。
**判定方式**：对比 v2.3 与 v2.4 的路由配置，验证无新增路由条目。

**验收标准（GWT，必须可判定）**：
- [ ] GWTREF-REQ-C004-01: Given v2.4 部署完成，When 对比 v2.3 与 v2.4 的前端路由配置，Then 无新增路由条目，菜单项数量不变

**关联**：P-DONT-04

#### REQ-C005：禁止 PM 修正数据丢失
**适用范围**：全局（所有角色/状态）
**来源**：proposal.md P-DONT-05
**禁止行为**：评估完成后，PM 对 AI 输出的修正数据（系统增删改、功能点增删改、估值调整）丢失或无法追溯。
**判定方式**：评估完成后通过 API 查询 `ai_original_output`、`pm_correction_diff`、`ai_correction_history` 验证数据存在。

**验收标准（GWT，必须可判定）**：
- [ ] GWTREF-REQ-C005-01: Given PM 在评估中修改了 AI 输出（新增系统/删除功能点/调整估值）并提交，When 评估完成后查询数据，Then `ai_original_output` 快照存在、`pm_correction_diff` 记录了修改内容、`ai_correction_history` 已更新

**关联**：REQ-009、REQ-010；P-DONT-05

#### REQ-C006：禁止自动覆盖非选中系统画像
**适用范围**：全局（所有角色/状态）
**来源**：proposal.md P-DONT-06
**禁止行为**：多系统文档导入时，AI 结构化信息提取自动将非当前选中系统的信息写入对应系统画像。
**判定方式**：导入涉及多系统的文档后，验证仅选中系统的 `ai_suggestions` 被更新，其他系统画像数据不变。

**验收标准（GWT，必须可判定）**：
- [ ] GWTREF-REQ-C006-01: Given 文档涉及系统 A（选中）和系统 B（未选中），When AI 信息提取完成，Then 系统 A 的 `ai_suggestions` 已更新，系统 B 的 `ai_suggestions` 与导入前完全一致

**关联**：REQ-005；P-DONT-06

#### REQ-C007：禁止画像域重构后语义覆盖缺失
**适用范围**：全局（所有角色/状态）
**来源**：proposal.md P-DONT-07
**禁止行为**：v2.4 画像以 5 域结构存储后，原 v2.3 的 4 个字段（system_scope/module_structure/integration_points/key_constraints）的语义信息在新结构中无明确对应子字段覆盖。
**判定方式**：逐一验证原 4 字段的语义在新 5 域 12 子字段中有明确映射关系。

**验收标准（GWT，必须可判定）**：
- [ ] GWTREF-REQ-C007-01: Given v2.3 系统画像含 system_scope/module_structure/integration_points/key_constraints 四字段信息，When v2.4 画像以 5 域结构存储，Then 原 4 字段的全部语义在新结构中有明确对应子字段覆盖

**关联**：REQ-012；P-DONT-07

## 5. 权限与合规

### 5.1 权限矩阵

> 基于 D19（PM-系统权限绑定）。沿用 v2.3 角色体系，不新增角色。

| 操作 | manager（负责该系统） | manager（非负责系统） | admin | expert |
|---|---|---|---|---|
| 查看系统画像 | ✅ 读写 | ✅ 只读 | ✅ 读写 | ✅ 只读 |
| 文档导入 | ✅ | ❌（只读模式+提示） | ✅ | ❌ |
| 编辑画像字段 | ✅ | ❌（只读模式+提示） | ✅ | ❌ |
| AI 建议采纳/回滚 | ✅ | ❌（只读模式+提示） | ✅ | ❌ |
| 提交评估修改 | ✅ | ❌（只读模式+提示） | ✅ | ❌ |
| 查看时间线 | ✅ | ✅ | ✅ | ✅ |
| 查看评估结果 | ✅ | ✅ | ✅ | ✅ |
| 导出评估报告 | ✅ | ✅ | ✅ | ❌ |
| 系统管理/画像发布审核 | ❌ | ❌ | ✅ | ❌ |

### 5.2 权限规则

1. **写操作绑定**：PM 的写操作（导入/编辑/采纳/回滚/提交）严格绑定其负责的系统列表。PM 可负责多个系统。
2. **读权限开放**：所有角色可只读查看任意系统画像、时间线、评估结果。
3. **跨系统通知链接**：多系统文档通知中的跨系统链接，若 PM 非目标系统负责人，进入只读模式并提示"您无权编辑此系统，请联系对应负责人"。
4. **无负责人系统**：系统无负责人时，仅 admin 可执行写操作。
5. **admin 豁免**：admin 角色不受 PM-系统绑定限制，对所有系统均有读写权限。

### 5.3 合规约束

1. **不新增路由**：v2.4 不新增菜单路由或独立页面（REQ-C004）。
2. **数据不删除**：`profile_events` 全量保留不删除（D14）；`ai_original_output` 快照只读不可修改。
3. **回滚能力**：上线后支持一键回退到 v2.3（REQ-106）。
4. **技术栈约束**：沿用 FastAPI + React + Ant Design + DashScope，不引入新基础设施。

## 6. 数据与接口

### 6.1 数据字典（v2.4 新增/扩展字段）

**`profile_data` 顶层结构定义（REQ-012）**：

```
profile_data: {
  system_positioning: { system_description, target_users, boundaries },
  business_capabilities: { module_structure, core_processes },
  integration_interfaces: { integration_points, external_dependencies },
  technical_architecture: { architecture_positioning, tech_stack, performance_profile },
  constraints_risks: { key_constraints, known_risks }
}
```

> 字段映射说明：
> - D1.target_users ← 原 document_parser 提取的 main_users（未入画像，现正式纳入）
> - D4.architecture_positioning ← 原 document_parser 提取的 architecture（未入画像，现正式纳入）+ 企业架构定位（新增）
> - D4.tech_stack ← 原 document_parser 提取的 tech_stack（未入画像，现正式纳入）
> - D4.performance_profile ← 原 document_parser 提取的 performance（未入画像，现正式纳入）
>
> `ai_suggestions` 和 `ai_suggestions_previous` 的结构同步更新为按域/子字段层级存储。

| 字段名 | 所属对象 | 类型 | 说明 | 必填 | 留存期 | 新增/扩展 |
|---|---|---|---|---|---|---|
| `profile_data` | SystemProfile | JSON Object | 系统画像 5 域嵌套结构（system_positioning / business_capabilities / integration_interfaces / technical_architecture / constraints_risks），各域含 2-3 个子字段 | 否 | 永久 | 新增（替代原 4 个扁平字段） |
| `ai_suggestions` | SystemProfile | JSON Object | 系统画像 5 域 12 子字段的 AI 建议值，按域/子字段层级存储（结构同 `profile_data`） | 否 | 永久 | 扩展（从自由文本升级为 5 域 12 子字段结构化映射） |
| `ai_suggestions_previous` | SystemProfile | JSON Object | `ai_suggestions` 的上一版全量快照，用于一级回滚（结构同 `profile_data`） | 否 | 永久 | 新增 |
| `ai_correction_history` | SystemProfile | JSON Object | PM 修正模式累计记录（修正次数、偏差方向、常见遗漏等） | 否 | 永久 | 新增 |
| `profile_events` | SystemProfile（关联表） | Array of Event | 画像变更事件日志列表 | — | 永久（全量保留不删除） | 新增 |
| `profile_events[].event_type` | Event | String/Enum | 事件类型：document_import / code_scan / manual_edit / ai_suggestion_accept / ai_suggestion_rollback / profile_publish | 是 | 同上 | 新增 |
| `profile_events[].timestamp` | Event | DateTime | 事件发生时间 | 是 | 同上 | 新增 |
| `profile_events[].source` | Event | String | 事件来源（文件名/操作人/扫描任务ID）；Design 阶段可细化为 source_type + source_ref | 是 | 同上 | 新增 |
| `profile_events[].summary` | Event | String | 变更摘要（简要描述变更内容） | 是 | 同上 | 新增 |
| `ai_original_output` | Task（评估任务） | JSON Object | 评估流水线各步 AI 原始输出快照，按 step 分键存储 | 否 | 永久（只读） | 新增 |
| `ai_original_output.system_recognition` | Task | JSON | 系统识别步骤的 AI 原始输出 | 否 | 同上 | 新增 |
| `ai_original_output.feature_split` | Task | JSON | 功能拆分步骤的 AI 原始输出 | 否 | 同上 | 新增 |
| `ai_original_output.work_estimation` | Task | JSON | 工作量估算步骤的 AI 原始输出 | 否 | 同上 | 新增 |
| `pm_correction_diff` | Task | JSON Object | PM 修正 diff 记录，按系统维度存储 | 否 | 永久 | 新增 |
| `pm_correction_diff[].system_level` | Diff | Array | 系统级 diff：新增/删除/改名（Phase 1，PM 提交时计算） | 否 | 同上 | 新增 |
| `pm_correction_diff[].feature_level` | Diff | Array | 功能点级 diff：新增/删除/修改描述（Phase 1，PM 提交时计算） | 否 | 同上 | 新增 |
| `pm_correction_diff[].estimation_level` | Diff | Array | 估值级 diff：专家终值 vs AI 预估偏差（Phase 2，评估完成后计算） | 否 | 同上 | 新增 |
| `optimistic` | Feature | Float | 乐观估计值（人天） | 否 | 永久 | 新增 |
| `most_likely` | Feature | Float | 最可能估计值（人天） | 否 | 永久 | 新增 |
| `pessimistic` | Feature | Float | 悲观估计值（人天） | 否 | 永久 | 新增 |
| `expected` | Feature | Float | 期望值，由系统根据 O/M/P 计算：(O + 4M + P) / 6 | 否 | 永久 | 新增 |
| `reasoning` | Feature | String | LLM 估算理由文本 | 否 | 永久 | 新增 |
| `original_estimate` | Feature | Float | 功能拆分 Agent 输出的原始预估人天（独立追溯字段） | 否 | 永久 | 新增 |
| `import_history` | SystemProfile（关联表） | Array of ImportRecord | 导入历史记录列表 | — | 永久 | 新增 |
| `import_history[].id` | ImportRecord | String/UUID | 导入记录唯一标识 | 是 | 同上 | 新增 |
| `import_history[].doc_type` | ImportRecord | String/Enum | 文档类型：requirement_doc / design_doc / tech_doc / esb_template / knowledge_doc | 是 | 同上 | 新增 |
| `import_history[].file_name` | ImportRecord | String | 导入文件名 | 是 | 同上 | 新增 |
| `import_history[].imported_at` | ImportRecord | DateTime | 导入时间 | 是 | 同上 | 新增 |
| `import_history[].status` | ImportRecord | String/Enum | 导入结果：success / failed | 是 | 同上 | 新增 |
| `import_history[].failure_reason` | ImportRecord | String（nullable） | 失败原因（成功时为 null） | 否 | 同上 | 新增 |
| `import_history[].operator_id` | ImportRecord | String | 操作人 ID | 是 | 同上 | 新增 |

### 6.2 接口变更概要（v2.4 新增/修改）

> 详细接口定义在 Design 阶段补充。此处仅列出 Requirements 阶段可确定的接口变更方向。

| 接口 | 方法 | 说明 | 新增/修改 |
|---|---|---|---|
| `/api/v1/system-profiles/{system_id}/profile/import` | POST | 文档导入，成功后异步触发 AI 结构化信息提取 | 修改（新增异步触发逻辑） |
| `/api/v1/system-profiles/{system_id}/profile/extraction-status` | GET | 查询 AI 结构化信息提取异步任务状态（pending/processing/completed/failed），前端轮询用 | 新增 |
| `/api/v1/system-profiles/{system_id}/profile/import-history` | GET | 查询该系统的导入历史列表（支持分页） | 新增 |
| `/api/v1/system-profiles/{system_id}/profile/events` | GET | 查询画像变更事件时间线（分页，默认 20 条） | 新增 |
| `/api/v1/system-profiles/{system_id}/profile/suggestions/accept` | POST | 采纳指定域子字段的 AI 建议（参数从 field_name 改为 domain + sub_field），更新画像当前值 | 新增 |
| `/api/v1/system-profiles/{system_id}/profile/suggestions/rollback` | POST | 回滚指定域子字段的 AI 建议到 `ai_suggestions_previous`（参数从 field_name 改为 domain + sub_field） | 新增 |
| `/api/v1/system-profiles/{system_id}/profile` | GET | 获取系统画像（返回 `profile_data` 5 域嵌套结构 + `ai_suggestions`、`ai_suggestions_previous`、`ai_correction_history`） | 修改（返回结构从 4 扁平字段改为 5 域嵌套） |
| `/api/v1/system-profiles/{system_id}/profile` | PUT | 更新系统画像（请求体为 `profile_data` 5 域嵌套结构） | 修改（请求体同步变更为 5 域嵌套） |
| `/api/v1/tasks/{task_id}/ai-output` | GET | 查询评估任务的 AI 原始输出快照 | 新增 |
| `/api/v1/tasks/{task_id}/correction-diff` | GET | 查询评估任务的 PM 修正 diff | 新增 |
| `/api/v1/tasks/{task_id}/estimate` | POST | 工作量估算（修改为 LLM 三点估计输出；LLM 失败时返回降级结果） | 修改（输出格式与降级返回口径变更） |
| `/api/v1/reports/{report_id}/export` | GET | 评估报告 Excel 导出（新增三点估计列） | 修改（Excel 列扩展） |

### 6.3 错误码约定（v2.4 新增）

| 错误码 | HTTP Status | 说明 | 触发场景 |
|---|---|---|---|
| `PROFILE_IMPORT_FAILED` | 400 | 文档导入失败 | 文件格式不支持/解析失败 |
| `AI_EXTRACTION_TIMEOUT` | 504 | AI 结构化信息提取超时 | DashScope API 超时 |
| `AI_EXTRACTION_FAILED` | 502 | AI 结构化信息提取失败 | DashScope API 返回错误 |
| `ROLLBACK_NO_PREVIOUS` | 409 | 无历史版本可回滚 | `ai_suggestions_previous` 不存在（首次导入） |
| `PERMISSION_DENIED_NOT_OWNER` | 403 | 非系统负责人，无写权限 | PM 尝试对非负责系统执行写操作 |
| `LLM_ESTIMATION_DEGRADED` | 200 | LLM 工作量估算降级 | DashScope API 返回错误，接口返回降级结果（`degraded=true`），AI 基线回退为原始估值 |
| `SYSTEM_NO_OWNER` | 403 | 系统无负责人，仅 admin 可操作 | PM 尝试对无负责人系统执行写操作 |

### 6.4 外部依赖

| 依赖 | 用途 | 影响范围 | 降级策略 |
|---|---|---|---|
| DashScope API | AI 结构化信息提取、LLM 工作量估算 | REQ-004、REQ-006 | 提取失败：`ai_suggestions` 不变，记录失败事件；估算失败：降级为功能拆分原始估值 |

### 6.5 指标与计算口径

| 指标/公式 | 定义 | 计算主体 | 精度 | 适用范围 |
|---|---|---|---|---|
| 期望值（expected） | `expected = (optimistic + 4 × most_likely + pessimistic) / 6`（PERT 公式） | 系统后端根据 LLM 输出的 O/M/P 自动计算，LLM 不直接输出 expected | 保留 2 位小数，四舍五入 | REQ-006/007/008，评估页/报告页/Excel 三渠道统一 |
| Delphi 偏离度 | 沿用 v2.3 公式，AI 基线值由原静态映射改为 expected | 系统后端 | 沿用 v2.3 | REQ-008 |
| PM 修正率 | 修正功能点数 / AI 原始功能点总数 | 系统后端，评估完成后计算 | 保留 2 位小数 | REQ-010（ai_correction_history 聚合用） |

## 7. 变更记录
| 版本 | 日期 | 说明 | 作者 |
|---|---|---|---|
| v1.3 | 2026-02-28 | Design 第 2 轮审查修复：统一 §3.2 REQ-004 轮询接口与 §6.2 接口变更概要路径口径，全部切换为 api v1 的 system-profiles/tasks/reports 前缀（修复 Requirements/Design 契约前缀不一致） | Codex |
| v1.2 | 2026-02-28 | 第 14 轮审查修复：§1.4 覆盖映射 P-DO-02 GWT 引用修正为 GWTREF-REQ-001-04, GWTREF-REQ-001-05（原 GWTREF-REQ-001-02 验证跨类型独立性，与 P-DO-02 导入结果展示语义不匹配） | AI + User |
| v1.1 | 2026-02-28 | 修复审查遗留问题：REQ-004 新增 `GWTREF-REQ-004-05/06`，覆盖同系统提取串行化与按域相关性选择性更新两条高风险业务规则；同步文档头部日期与版本号 | AI + User |
| v1.0 | 2026-02-28 | 第 13 轮审查修复：REQ-004 新增并发提取串行化业务规则（确保 ai_suggestions_previous 备份完整性）；REQ-011 入口/触发写操作枚举补齐为 5 项（与业务规则一致）；§1.1 proposal 版本引用修正为 v1.2；status.md _review_round 更新为 13 | AI + User |
| v0.9 | 2026-02-28 | 新增 REQ-012（系统画像域结构重构：5 域 12 子字段+三区布局）+ REQ-C007（禁止语义覆盖缺失）；修改 REQ-002（三区布局右侧）、REQ-003（子字段级 diff）、REQ-004（5 域 schema + 按域相关性选择性更新）、REQ-006（5 域完整上下文注入）；§1.4 覆盖映射 31→34 条（+P-DO-21/22, P-DONT-07）；§6.1 新增 profile_data 顶层结构；§6.2 接口变更对齐 5 域结构 | AI + User |
| v0.8 | 2026-02-28 | 第 8 轮审查修复：修正 P-DO-15 映射 GWT 原子写法；修复 REQ-010 两阶段语义与 GWT 冲突（GWTREF-REQ-010-01 去除估值级，新增 GWTREF-REQ-010-04 验证 Phase 2 估值级 diff）；统一 LLM 失败为"HTTP 200 + degraded 标记"降级口径，并同步 REQ-006/GWTREF-REQ-006-05、接口表与错误码（`LLM_ESTIMATION_DEGRADED`） | AI + User |
| v0.7 | 2026-02-27 | 第 4 轮审查修复（16 条）：P-DO-07 覆盖映射修正→REQ-004；REQ-010 估值级 diff 拆分为两阶段（PM 提交时 Phase 1 + 评估完成后 Phase 2）；GWTREF-REQ-010-02 补充"PM 有修改"前置条件；REQ-011/§5.2 写操作列表补充"AI 建议回滚"；新增异步任务状态查询接口；§6.1 补充导入历史记录数据模型+必填/留存期列；REQ-002 明确手动编辑/画像发布为既有功能改造点；GWTREF-REQ-006-03 拆分为 03/04 分别验证第二层/第三层知识注入；§4A.1/§4A.2 补齐适用范围/来源/关联GWTREF-ID；§4.1 补齐需求分类/需求说明列；新增 §6.5 指标与计算口径；明确 expected 由系统计算（LLM 仅输出 O/M/P+reasoning）；profile_events.source 标注 Design 细化点；REQ-004 字段映射标注 Design 细化点 | AI + User |
| v0.6 | 2026-02-27 | 修复 REQ-104 与 REQ-006/007/008 的降级语义冲突：将"五字段非空/三渠道一致"限定为 LLM 成功场景，并新增 GWTREF-REQ-104-03 明确失败场景按降级规则展示 | AI + User |
| v0.5 | 2026-02-27 | 完成 §5 权限与合规（权限矩阵+规则+合规约束）+ §6 数据与接口（数据字典+接口变更+错误码+外部依赖） | AI + User |
| v0.4 | 2026-02-27 | 完成 §4 非功能需求（REQ-101~106，6 项 + 7 条 GWT）+ §4A 禁止项（REQ-C001~C006，6 项 + 6 条 GWT） | AI + User |
| v0.3 | 2026-02-27 | 完成 §3 功能性需求明细（REQ-001~REQ-011，共 11 项需求 + 42 条 GWT 验收标准） | AI + User |
| v0.2 | 2026-02-27 | 完成 §2 业务场景说明（12 个场景明细 SCN-V24-01~12） | AI + User |
| v0.1 | 2026-02-27 | 初始化 §1（概述+术语+覆盖映射表），等待用户确认后继续 §2 | AI + User |
