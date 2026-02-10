# Review Report：Design / v2.0

| 项 | 值 |
|---|---|
| 阶段 | Design |
| 版本号 | v2.0 |
| 日期 | 2026-02-06 |
| 检查点 | 需求覆盖、可落地性、接口与数据模型一致性、安全与回滚、开放问题收敛 |
| 审查范围 | `docs/v2.0/design.md`（v0.1）、对照 `docs/v2.0/requirements.md`（v1.6） |
| 输入材料 | `.claude/templates/review_template.md`、`.claude/phases/03-design.md` |

## 结论摘要
- 总体结论：⚠️ 有条件通过
- Blockers（P0）：0
- 高优先级（P1）：2
- 其他建议（P2+）：3

## 关键发现（按优先级）

### RVW-DES-001（P1）效能看板“组件级”定义不足，Implementation 易出现歧义
- 证据：`design.md` 仅描述 API-009 返回 widgets，但未给出每个 page 的最小 widget 列表、字段结构与与 `requirements.md 6.3` 指标口径的映射关系。
- 风险：
  - 前端无法据此实现页面（overview/rankings/ai/system/flow）与下钻条件拼装
  - 统计口径可能与需求不一致（尤其是 `frozen_at/owner_snapshot/final_estimation_days_by_system` 口径）
- 建议修改：
  - 在 `design.md` 增加“Dashboard Widget Catalog”章节：按 page 列出最小 widget 集合（至少覆盖 REQ-009/019/021），并明确：
    - `widget_id/title/sample_size/data/drilldown_filters` 的字段约定
    - 每个 widget 的数据来源与计算公式（引用 `requirements.md 6.3` 的口径）
    - 下钻 filters → API-010 query 的映射规则
- 验证方式（可复现）：
  - `rg -n \"Widget|widgets|dashboard\" docs/v2.0/design.md`
  - 人工检查：每个 page 至少 2 个 widget，且每个 widget 都给出 drilldown_filters 规则。

### RVW-DES-002（P1）“任务冻结口径写入”缺少落点 API/状态机设计
- 证据：`design.md` 定义冻结触发为 `in_progress → completed`，但未说明由哪个现有 API/状态变更点触发，如何保证幂等（只写一次），以及与现有 `routes.py` 任务状态字段的兼容关系。
- 风险：
  - 冻结字段不一致或遗漏，导致看板统计无法按口径落窗
  - 同一任务多次冻结导致历史漂移
- 建议修改：
  - 在 `design.md` 增加“Task Workflow + Freeze”小节：
    - 明确任务状态机字段（对齐现有 `status/workflow_status/confirmed` 等）与 v2.0 `pending/in_progress/completed/closed` 的映射
    - 指定冻结写入的**唯一落点**（例如：任务确认/结束接口；或新增 `POST /api/v1/tasks/{task_id}/status`）
    - 幂等规则：若 `frozen_at` 已存在则拒绝重复写入/或忽略并返回当前快照
- 验证方式（可复现）：
  - `rg -n \"frozen_at|owner_snapshot|workflow_status\" backend/api/routes.py`
  - 设计文档中能找到明确的“触发API/触发时机/幂等规则”说明。

### RVW-DES-003（P2）代码扫描 repo_path 的“本地路径 vs Git URL”校验规则需更明确
- 证据：`design.md` 6.2 中对 repo_path 的校验描述偏向“必须绝对路径”，与 API-001 支持 Git URL 的契约容易产生误解。
- 风险：实现期可能把 Git URL 当作非法输入，或引入不安全的 URL 支持（file:// 等）。
- 建议修改：
  - 补充分支规则：当 `repo_path` 为 URL（http/https/ssh）时的允许协议与禁止协议清单；当为本地路径时才要求 absolute+allowlist。
  - 明确 Git URL 实现为“可选能力”，并在无法访问时返回 `SCAN_001`。
- 验证方式：设计中明确列出允许/禁止协议与返回错误码。

### RVW-DES-004（P2）ESB mapping_json 与知识库导入支持范围需要更贴近需求契约
- 证据：
  - `requirements.md` 的 API-003 mapping_json 示例为数组候选列名；`design.md` 未明确支持 value=list 的解析策略。
  - `requirements.md` 的 SCN-009/API-011 期望多格式导入；`design.md` 未明确“允许格式/大小限制/不落盘原文”的可验证约束。
- 风险：实现时 mapping_json 不兼容；导入失败率高或合规边界不清。
- 建议修改：
  - 增加 mapping_json 兼容规则：value 支持 string 或 list[string]。
  - 增加导入约束表：允许扩展名、单文件大小上限、失败处理策略（整体失败 vs 分条失败），与错误码映射。
- 验证方式：设计中存在“mapping_json schema + 允许格式表”。

### RVW-DES-005（P2）修改轨迹保留期清理机制需要可落地
- 证据：`design.md` 提到“清理任务定期删除”，但未说明无 cron/调度器情况下的实现方式。
- 风险：实现被阻塞或清理不执行导致文件膨胀。
- 建议修改：
  - 设计为“写入时顺带清理”：每次写入 modification_traces 时进行一次轻量清理（按 recorded_at 过滤），避免引入额外调度依赖。
- 验证方式：设计中明确“触发时机/复杂度/上限控制”。

## 建议验证清单（命令级别）
- [ ] 对照需求覆盖：`rg -n \"REQ-|API-0\" docs/v2.0/design.md`
- [ ] 核对冻结字段落点：`rg -n \"frozen_at|owner_snapshot\" docs/v2.0/design.md`
- [ ] 核对看板 widgets：`rg -n \"widget_id|drilldown_filters\" docs/v2.0/design.md`

## 开放问题
- [ ] 系统清单 owner_id 字段模板约定（design.md 已列为开放问题，建议在 Planning 阶段落到 T 任务并给样例文件）。

## 处理记录（建议由开发/人工填写）
| RVW-ID | 严重度 | 处理决策（Fix/Defer/Accept） | Owner | 说明 | 链接/证据 |
|---|---|---|---|---|---|
| RVW-DES-001 | P1 | Fix | AI | 补齐 widget catalog + 口径映射 + 下钻映射 | `docs/v2.0/design.md` |
| RVW-DES-002 | P1 | Fix | AI | 明确冻结触发API/状态机/幂等规则 | `docs/v2.0/design.md` |
| RVW-DES-003 | P2 | Fix | AI | repo_path 本地/URL 校验规则补齐 | `docs/v2.0/design.md` |
| RVW-DES-004 | P2 | Fix | AI | mapping_json schema + 导入格式/大小表补齐 | `docs/v2.0/design.md` |
| RVW-DES-005 | P2 | Fix | AI | 轨迹清理落地为“写入时清理” | `docs/v2.0/design.md` |

---

## 追加记录：v0.2 修复后复查（2026-02-06）

| 项 | 值 |
|---|---|
| 复查输入 | `docs/v2.0/design.md`（v0.2） |
| 复查结论 | ✅ 通过 |
| 复查说明 | P1/P2 问题已按建议补齐（widget catalog、冻结落点与幂等、repo_path 分支校验、mapping_json/导入约束、轨迹清理机制） |

**抽样核对点（证据）**：
- `design.md` 已包含 `4.3.8 Dashboard Widget Catalog（MVP）`，并给出 drilldown_filters → API-010 映射规则。
- `design.md` 已包含 `4.3.6 任务工作流与冻结口径`，明确冻结写入落点与幂等规则。
- `design.md` 的 repo_path 校验已区分本地路径与 Git URL。

---

## 追加记录：v2.0 完整审查（2026-02-06）

| 项 | 值 |
|---|---|
| 审查输入 | `docs/v2.0/design.md`（v0.2, 409行） |
| 审查结论 | ✅ 通过（有条件） |
| 新增问题 | P1: 2 | P2: 6 |

**本次审查新增发现**：

### RVW-DES-101（P1）开放问题未关闭 - 系统清单 owner_id 字段来源不明确

**证据**：L401 9.2 开放问题；L355-356 资源级权限依赖 owner_id

**风险**：权限校验无法落地实现

**建议**：在 Planning 前明确模板中 owner_id 字段的列名

---

### RVW-DES-102（P1）Git URL 扫描安全决策未明确

**证据**：L402 开放问题

**风险**：安全与网络访问风险未评估

**建议**：Planning 前明确是否支持及安全策略

---

### RVW-DES-103（P2）重复标题（L250/L252）

**建议**：删除重复标题

---

### RVW-DES-104（P2）向量库容量规划不足

**证据**：L383-384 性能指标但无容量上限

**建议**：补充容量上限与扩容策略

---

### RVW-DES-105（P2）看板聚合缓存策略缺失

**证据**：L384 提到缓存但无阈值

**建议**：明确缓存触发条件

---

### RVW-DES-106（P2）文件锁实现方式未明确

**证据**：L117 提到 lock 文件或 fcntl

**建议**：明确选择与超时策略

---

### RVW-DES-107（P2）报告下载生成方式未明确

**建议**：明确格式与生成方式

---

## 开放问题状态

| 问题ID | 问题描述 | 优先级 | 状态 |
|---|---|---|---|
| OP-DES-001 | 系统清单 owner_id 字段来源 | P1 | 待决策 |
| OP-DES-002 | Git URL 扫描支持与否 | P1 | 待决策 |
| OP-DES-003 | 向量库容量上限 | P2 | 待明确 |
| OP-DES-004 | 看板聚合缓存阈值 | P2 | 待明确 |
| OP-DES-005 | 文件锁实现方式 | P2 | 待明确 |
| OP-DES-006 | 报告生成技术选型 | P2 | 待明确 |

**建议**：关闭 2 个 P1 问题后进入 Planning 阶段。

---

*审查报告追加版本: v2.0 | 审查人: AI | 日期: 2026-02-06 | 基于 design.md v0.2*

---

## 追加记录：v0.3 修复后复查（2026-02-06）

| 项 | 值 |
|---|---|
| 复查输入 | `docs/v2.0/design.md`（v0.3） |
| 复查结论 | ✅ 通过 |
| 复查说明 | RVW-DES-101~107 已全部修复：owner_id 与 Git URL 决策已关闭；删除重复标题；补齐向量库容量上限、看板缓存阈值、文件锁策略与报告生成方案；并将 9.2 开放问题改为“已关闭问题”。 |

### 修复清单（对应新增问题）
- RVW-DES-101：已在 `design.md` 增加 `4.2.6 System List owner 字段约定`，并给出模板列名决策与授权规则。
- RVW-DES-102：已在 `design.md` 明确 Git URL 扫描默认禁用 + 配置开关与 host allowlist。
- RVW-DES-103：已删除重复标题（`4.3.7` 仅保留一处）。
- RVW-DES-104：已在 `design.md 7.2` 补齐 local/Milvus 规模边界与软上限策略。
- RVW-DES-105：已在 `design.md 7.3` 补齐缓存启用阈值（>2,000）与 TTL/key/失效策略。
- RVW-DES-106：已在 `design.md 4.2` 明确“优先 fcntl + 原子写 + 锁持有最小化”的落地策略。
- RVW-DES-107：已在 `design.md 4.3.9` 明确 PDF 生成方案与 docx 处理策略（不支持则 `REPORT_002`）。

### 开放问题状态（更新）
| 问题ID | 问题描述 | 优先级 | 状态 |
|---|---|---|---|
| OP-DES-001 | 系统清单 owner_id 字段来源 | P1 | ✅ 已关闭（design v0.3） |
| OP-DES-002 | Git URL 扫描支持与否 | P1 | ✅ 已关闭（design v0.3） |
| OP-DES-003 | 向量库容量上限 | P2 | ✅ 已关闭（design v0.3） |
| OP-DES-004 | 看板聚合缓存阈值 | P2 | ✅ 已关闭（design v0.3） |
| OP-DES-005 | 文件锁实现方式 | P2 | ✅ 已关闭（design v0.3） |
| OP-DES-006 | 报告生成技术选型 | P2 | ✅ 已关闭（design v0.3） |

---

## Review Report：Design（Full）/ v2.0（design v0.3）

| 项 | 值 |
|---|---|
| 阶段 | Design |
| 版本号 | v2.0 |
| 日期 | 2026-02-06 |
| 检查点 | 与需求一致性、可落地性、接口/数据模型可实现、安全边界、回滚与验证可复现 |
| 审查范围 | `docs/v2.0/design.md`（v0.3） |
| 输入材料 | `docs/v2.0/requirements.md`（v1.6）、`docs/v2.0/plan.md`（v0.2）、`backend/*`（现状对照） |

### 结论摘要
- **总体结论**：⚠️ 有条件通过（设计本身已闭环，但与需求/计划的“决策同步”仍需补齐）
- **Blockers（P0）**：0
- **高优先级（P1）**：3
- **其他建议（P2+）**：3

---

## 关键发现（按优先级）

### RVW-DES-201（P1）Design 已关闭 Viewer 范围，但 Requirements 仍为开放问题（口径未同步）
- **证据**：
  - `design.md` 6.1：`viewer` 视作“管理层只读”，默认全局可见。
  - `review_requirements.md`：仍存在 OP-REQ-105（Viewer 访问范围待明确）。
- **风险**：
  - 实现阶段按 design 落地后，需求侧仍可能被认为“未决策”，导致验收争议。
- **建议修改**：
  - 将 Viewer 范围决策回写 `requirements.md`（角色/权限矩阵/API-010）并更新 `review_requirements.md` 的 OP-REQ-105 状态为已关闭；同步 `status.md` 的审查状态说明。
- **验证方式（可复现）**：
  - `rg -n "Viewer|viewer|OP-REQ-105" docs/v2.0/requirements.md docs/v2.0/review_requirements.md docs/v2.0/design.md`

### RVW-DES-202（P1）REQ-NF-002（10万条、P95<500ms）与 local 向量库回退能力存在“验收前置条件”缺口
- **证据**：
  - `requirements.md` REQ-NF-002：向量库规模≥100,000、top_k=20、P95<500ms。
  - `design.md` 7.2：local 建议≤20,000 条，≥20,000 建议启用 Milvus。
  - 现有 `LocalVectorStore` 为全量扫描（理论上难在 10万规模达到 500ms P95）。
- **风险**：
  - 若验收环境使用 local，无法满足 REQ-NF-002，导致验收失败或争议。
- **建议修改**（二选一，建议A）：
  - **A（建议）**：在 `requirements.md` 明确 REQ-NF-002 的验收前置条件：向量库后端为 Milvus（并给出部署/数据集准备/压测命令），local 仅作为降级与小规模模式。
  - B：为 local 增加索引/分片/近似检索（成本高，不建议本期）。
- **验证方式（可复现）**：
  - `pytest -q`（单测）
  - 压测脚本/命令（Planning 中补齐）：对 Milvus 后端注入 100k 数据后进行 1,000 次查询并统计 P95。

### RVW-DES-203（P1）API-014 docx 支持范围与 Design 的“可选/返回REPORT_002”口径不一致
- **证据**：
  - `requirements.md` API-014：`format` 可选，枚举 `pdf/docx`（默认pdf）。
  - `design.md` 4.3.9：docx “本期可选，不支持则返回 REPORT_002（format非法）”。
- **风险**：
  - 若前端或用户按 requirements 认为 docx 必支持，可能触发验收缺陷。
- **建议修改**：
  - 若本期必须支持 docx：在 Implementation 增加 docx 生成方案并补齐测试与依赖评估（优先复用现有依赖，避免新增）。
  - 若本期不做 docx：将 `requirements.md` API-014 的 `format` 枚举改为仅 `pdf`，并在变更记录与 Out of Scope 中说明。
- **验证方式（可复现）**：
  - `rg -n "API-014|format" docs/v2.0/requirements.md docs/v2.0/design.md`

### RVW-DES-204（P2）System owner 字段决策未同步到 Plan（Plan 仍以“是否新增列”为开放问题）
- **证据**：
  - `design.md` 4.2.6：已明确 canonical keys 与模板列名建议。
  - `plan.md` “开放问题”：仍写“是否需要新增负责人ID/账号列（建议：需要）”。
- **风险**：
  - Implementation 执行 T001/T016 时容易出现“到底算不算已决策”的返工。
- **建议修改**：
  - 将 plan 的开放问题改为“已决策：模板新增 owner_id/owner_username，并支持中文别名”，并在 T001/T016 的验收标准中补充“模板列名/别名映射”验证。
- **验证方式**：
  - `rg -n "owner_id|owner_username" docs/v2.0/plan.md docs/v2.0/design.md`

### RVW-DES-205（P2）Git URL 扫描“默认禁用+host allowlist”与 API-001 契约的默认行为需要对外解释
- **证据**：
  - `design.md` 4.3.1：Git URL 默认不启用，需配置开关与 host allowlist。
  - `requirements.md` API-001：repo_path 支持“本地路径或 Git URL”。
- **风险**：
  - 用户按契约传 Git URL，但环境未配置导致持续报错；若错误提示不清晰，体验差且难定位。
- **建议修改**：
  - 在 Implementation 中把“未启用 Git URL”作为可识别错误原因（仍用 `SCAN_001` 但 message 说明“Git URL未启用/host不在allowlist”）。
  - 在部署/操作文档中补齐相关配置项与样例。
- **验证方式**：
  - `rg -n "CODE_SCAN_ENABLE_GIT_URL|CODE_SCAN_GIT_ALLOWED_HOSTS|SCAN_001" docs/v2.0/design.md`

### RVW-DES-206（P2）错误响应结构统一仍属“实现期风险点”，建议在计划/实现中明确“统一层”
- **证据**：
  - `requirements.md` 6.4：4xx/5xx 统一返回 `error_code/message/request_id`。
  - 现有多数接口仍使用 `{code,message,data}` 风格。
- **风险**：
  - 新旧接口混用导致前端适配复杂；错误码与HTTP状态码不一致会影响验收与排障。
- **建议修改**：
  - 在 Implementation 增加“错误响应适配层”任务：对 v2.0 新接口严格按 6.4 返回；旧接口保持兼容但逐步收敛。
- **验证方式**：
  - `pytest -q`（新增接口错误分支覆盖）

---

## 建议验证清单（命令级别）
- [ ] 设计覆盖检查：`rg -n "REQ-|API-" docs/v2.0/design.md`
- [ ] 关键决策同步检查：`rg -n "Viewer|docx|Milvus|owner_id|Git URL" docs/v2.0/design.md docs/v2.0/requirements.md docs/v2.0/plan.md`

## 处理记录（建议由开发/人工填写）
| RVW-ID | 严重度 | 处理决策（Fix/Defer/Accept） | Owner | 说明 | 链接/证据 |
|---|---|---|---|---|---|
| RVW-DES-201 | P1 | Fix | AI | Viewer 全局只读决策已同步到 requirements v1.7（权限矩阵补齐“任务明细只读”）；design v0.4 同步说明 | `docs/v2.0/requirements.md`、`docs/v2.0/design.md` |
| RVW-DES-202 | P1 | Fix | AI | REQ-NF-002 明确 Milvus 为验收前置；plan v0.3 T018 补齐 Milvus 压测交付 | `docs/v2.0/requirements.md`、`docs/v2.0/plan.md` |
| RVW-DES-203 | P1 | Fix | AI | API-014/REQ-018：v2.0 仅支持 PDF；docx 预留并返回 REPORT_002；design v0.4 同步 | `docs/v2.0/requirements.md`、`docs/v2.0/design.md` |
| RVW-DES-204 | P2 | Fix | AI | plan v0.3 关闭 owner_id 列开放问题，并落到 T001/T016 验收标准 | `docs/v2.0/plan.md` |
| RVW-DES-205 | P2 | Fix | AI | Git URL 默认禁用+host allowlist 已落到 requirements API-001/SCAN_001 文案与 plan T002 验收 | `docs/v2.0/requirements.md`、`docs/v2.0/plan.md` |
| RVW-DES-206 | P2 | Fix | AI | plan v0.3 增加 T021“统一错误响应结构”并纳入执行顺序/DoD | `docs/v2.0/plan.md` |

---

## 追加记录：同步修复后复查（2026-02-07）

| 项 | 值 |
|---|---|
| 复查输入 | `docs/v2.0/design.md`（v0.4）、`docs/v2.0/requirements.md`（v1.7）、`docs/v2.0/plan.md`（v0.3） |
| 复查结论 | ✅ 通过 |
| 复查说明 | RVW-DES-201~206 已全部闭环；关键决策在设计/需求/计划之间一致，可进入 Implementation。 |

---

# Review Report：Design（Full）/ v2.0（design v0.5）

| 项 | 值 |
|---|---|
| 阶段 | Design |
| 版本号 | v2.0 |
| 日期 | 2026-02-07 |
| 检查点 | 需求追溯、接口与数据模型、失败路径与降级、兼容与回滚、安全与可观测、开发就绪度 |
| 审查范围 | `docs/v2.0/design.md`（v0.5）对照 `docs/v2.0/requirements.md`（v1.9）、`docs/v2.0/plan.md`（v0.3） |
| 输入材料 | `.claude/templates/review_template.md`、`.claude/phases/03-design.md`、`backend/api/*`（抽样核对路由现状） |

## 结论摘要
- 总体结论：❌ 不通过（需先修复 1 个 P0 + 3 个 P1）
- Blockers（P0）：1
- 高优先级（P1）：3
- 其他建议（P2+）：2

## 关键发现（按优先级）

### RVW-DES-301（P0）Requirements REQ-ID“列表表格”与“明细标题/追溯矩阵”不一致，导致 Design 追溯失真
- 证据：
  - `requirements.md` 3.1 列表仍写 `REQ-017=历史评估文档导入（L0）`、`REQ-018=报告下载`（见 L554-L555）。
  - 但 `requirements.md` 明细标题已变为 `REQ-017=报告下载`（见 L1407），追溯矩阵也按新编号（如 SCN-012→REQ-017，见文末）。
- 风险：
  - 进入开发后，任务追溯/验收口径会出现“同一个 REQ-ID 指代不同内容”的争议，影响计划与实现对齐。
  - `design.md`/`plan.md` 内引用 REQ-ID 的语义将变得不可靠。
- 建议修改：
  - 先修复 `requirements.md`：统一 REQ 编号口径（3.1 列表/3.2 明细/7.1 追溯矩阵/变更记录叙述保持一致）。
  - 然后再同步 `design.md` 与 `plan.md` 内所有 REQ-ID 引用（避免“文档已升级但引用未升级”）。
- 验证方式（可复现）：
  - `rg -n "^\\| .*\\| REQ-01[7-9] \\|" docs/v2.0/requirements.md`
  - `rg -n "^#### REQ-01[7-9]" docs/v2.0/requirements.md`
  - 人工核对：同一 REQ-ID 在全文只对应一个需求名称与内容。

### RVW-DES-302（P1）Design 未覆盖关键需求/接口：缺少 SCN-004/006/010 的核心流程设计与 API-005/006/008/013 的落地说明
- 证据：
  - `design.md` 中仅在“设计目标”提到 API-005/006（L16），但全文无 SCN-004/006/010，也无 API-005/006/008/013 的设计章节（可用命令验证）。
  - `design.md` 的 API 摘要表（4.4）未包含 API-005/006/008/013（见 L345-L357）。
- 风险：
  - 进入 Implementation 后，开发需要在“复杂度评分/检索聚合/专家偏差报告/评估详情契约”上自行做关键决策，返工概率高。
  - 设计阶段“与需求一一对应”的门禁不满足（`.claude/phases/03-design.md`）。
- 建议修改：
  - 在 `design.md` 的 4.3 追加最小可落地章节（建议 4.3.10~4.3.12）：
    - SCN-004 / API-005：检索聚合策略（画像/能力/文档/ESB 的 top_k 分配、阈值、降级关键词匹配一致性）
    - API-006：三维度评分的落地规则（输入提取→分项评分→总分→reasoning 模板）
    - SCN-006 / API-008：专家差异统计的计算口径（均值/离散度/异常阈值、结果结构）
    - SCN-010 / API-013：评估详情契约与权限（PM/Expert）对齐当前 routes
  - 同步更新 4.4 API 摘要表把缺失 API 补齐（至少标注“internal/仅后端调用”）。
- 验证方式（可复现）：
  - `rg -n "SCN-004|SCN-006|SCN-010|API-005|API-006|API-008|API-013" docs/v2.0/design.md`
  - `rg -n "^#### 4\\.3\\." docs/v2.0/design.md`（确认核心流程覆盖所有关键 SCN/API）

### RVW-DES-303（P1）文档导入“允许格式”与 Requirements 的兼容性要求不一致（Office 旧格式/doc/txt）
- 证据：
  - `design.md` 4.3.3 允许格式仅列 `.docx/.pdf/.pptx/.xlsx/.csv`（见 L219-L221）。
  - `requirements.md` REQ-011 要求支持 doc/docx、xls/xlsx、ppt/pptx、txt，并要求“支持 Office 2007+ 时必须同时支持旧格式”（见 L1171-L1176）。
- 风险：
  - 若实现按 design 收敛格式，会与 requirements 验收冲突；若实现按 requirements 兼容旧格式，可能需要额外解析能力/依赖评估，影响工期。
- 建议修改：
  - 在 `design.md` 明确最终“允许格式清单 + 与现有 parser 的差距 + 处理策略（支持/拒绝/降级）”，并同步到 `plan.md` 的导入任务验收标准。
- 验证方式（可复现）：
  - `rg -n "允许格式|\\.doc\\b|\\.xls\\b|\\.ppt\\b|txt" docs/v2.0/design.md docs/v2.0/requirements.md`

### RVW-DES-304（P1）repo_archive 文件数上限口径不一致（10,000 vs 20,000）
- 证据：
  - `requirements.md` REQ-001：文件数量不超过 10,000（见 L610）。
  - `design.md` 配置建议：`CODE_SCAN_MAX_FILES=20000`（见 L369）。
- 风险：
  - 实现/测试/验收使用不同阈值导致用例不稳定；安全边界也会被误判（zip bomb 防护阈值）。
- 建议修改：
  - 在 `design.md` 与 `requirements.md` 二选一统一阈值，并在实现侧把阈值作为配置项+在错误信息里返回实际阈值，避免“黑盒阈值”。
- 验证方式（可复现）：
  - `rg -n "CODE_SCAN_MAX_FILES|文件数量不超过" docs/v2.0/design.md docs/v2.0/requirements.md`

### RVW-DES-305（P2）Design 目标中的 REQ/API 对齐项建议“按真实覆盖”校正，避免误导
- 证据：`design.md` 设计目标中将“学习闭环”对齐到 `API-007~009`、`REQ-007/008/009`（见 L17），但当前设计正文未覆盖 API-008，且 API-009 属于看板而非学习闭环。
- 风险：开发/验收阶段对“哪些设计已闭环”产生误解。
- 建议修改：将 1.1 设计目标的“对齐项”调整为：
  - 学习闭环：REQ-007/REQ-008（含 API-007/API-008）
  - 效能看板：REQ-009/REQ-018/REQ-020（含 API-009/API-010）
- 验证方式：人工核对设计目标与正文章节一一对应。

### RVW-DES-306（P2）Plan 文档引用版本落后（会影响开发使用入口）
- 证据：`plan.md` 仍引用 `design.md v0.4`、`requirements.md v1.7`（见 `docs/v2.0/plan.md` 文档元信息）。
- 风险：开发按 plan 操作时引用到旧口径，产生返工。
- 建议修改：同步更新 `plan.md` 文档元信息与任务关联 REQ-ID（在修复 RVW-DES-301 后再做），并在 `status.md` 的“审查状态”备注中注明本次复查结论。
- 验证方式：`sed -n '1,20p' docs/v2.0/plan.md`

## 建议验证清单（命令级别）
- [ ] REQ 编号一致性：`rg -n \"^\\| .*\\| REQ-01[7-9] \\||^#### REQ-01[7-9]\" docs/v2.0/requirements.md`
- [ ] Design 覆盖性：`rg -n \"SCN-004|SCN-006|SCN-010|API-005|API-006|API-008|API-013\" docs/v2.0/design.md`
- [ ] 文档格式口径：`rg -n \"允许格式|支持文档类型|\\.doc\\b|\\.xls\\b|\\.ppt\\b|txt\" docs/v2.0/design.md docs/v2.0/requirements.md`
- [ ] repo_archive 阈值：`rg -n \"CODE_SCAN_MAX_FILES|文件数量不超过\" docs/v2.0/design.md docs/v2.0/requirements.md`
- [ ] 计划引用版本：`sed -n '1,20p' docs/v2.0/plan.md`

## 开放问题
- [ ] 文档导入是否必须支持 `.doc/.xls/.ppt/.txt`（如必须，需确认解析方案与依赖；如不必须，需回写 requirements 收敛范围）
- [ ] repo_archive 文件数上限最终阈值（统一为 10,000 或 20,000，并明确“可配置 + 默认值”）

## 处理记录（建议由开发/人工填写）
| RVW-ID | 严重度 | 处理决策（Fix/Defer/Accept） | Owner | 说明 | 链接/证据 |
|---|---|---|---|---|---|
| RVW-DES-301 | P0 | Fix | AI | requirements v1.10 已统一 REQ-017~020 在“列表/明细/追溯矩阵”的口径，并移除重复 REQ | `docs/v2.0/requirements.md` |
| RVW-DES-302 | P1 | Fix | AI | design v0.6 已补齐 SCN-004/006/010 与 API-005/006/008/013 章节，并更新 API 摘要表覆盖 | `docs/v2.0/design.md` |
| RVW-DES-303 | P1 | Fix | AI | requirements v1.11 与 design v0.7 已收敛文档导入格式：docx/pdf/pptx/txt/xlsx/csv；不支持 doc/xls/ppt（需预转换） | `docs/v2.0/requirements.md`、`docs/v2.0/design.md` |
| RVW-DES-304 | P1 | Fix | AI | 已统一 repo_archive 文件数阈值：默认 10,000（可配置）并在设计中对齐 requirements REQ-001 | `docs/v2.0/design.md`、`docs/v2.0/requirements.md` |
| RVW-DES-305 | P2 | Fix | AI | design v0.8 已修复设计目标中的权限表述一致性（viewer 可下钻任务明细只读） | `docs/v2.0/design.md` |
| RVW-DES-306 | P2 | Fix | AI | plan v0.4 已同步引用版本到 requirements v1.11 / design v0.7；其余追溯/覆盖矩阵一致性在 Planning 阶段继续闭环 | `docs/v2.0/plan.md` |

---

# Review Report：Design（Full）/ v2.0（design v0.8）

| 项 | 值 |
|---|---|
| 阶段 | Design |
| 版本号 | v2.0 |
| 日期 | 2026-02-07 |
| 检查点 | 需求追溯、接口/数据模型、失败路径与降级、安全边界、兼容与回滚、开放问题收敛、开发就绪度（Design视角） |
| 审查范围 | `docs/v2.0/design.md`（v0.8）对照 `docs/v2.0/requirements.md`（v1.11） |
| 输入材料 | `.claude/templates/review_template.md`、`.claude/phases/03-design.md` |

## 结论摘要
- 总体结论：✅ 通过（可进入 Planning 复查与实施拆解）
- Blockers（P0）：0
- 高优先级（P1）：0
- 其他建议（P2+）：1

## 关键发现（按优先级）

### RVW-DES-401（P2）建议在 Design 文档元信息中补充“依赖 Plan 复查”的门禁说明，避免读者误判“可直接进入 Implementation”
- 证据：`design.md` 状态为 Approved；但当前仓库仍需在 Planning 阶段闭环“追溯矩阵/覆盖矩阵”的一致性与验证证据固化。
- 风险：开发团队可能跳过 Planning 的一致性修复，导致 REQ/任务追溯混乱、验收口径争议。
- 建议修改：
  - 在 `docs/v2.0/status.md`（单一真相源）标明“进入 Implementation 的前置：Planning 复查通过”。
  - （可选）在 `design.md` 顶部加一行备注：Implementation 以 `plan.md` 为执行入口。
- 验证方式（可复现）：
  - `sed -n '1,30p' docs/v2.0/status.md`

## 关键决策同步核对（抽样）
- Viewer 范围（RVW-DES-201）：design/requirements 均明确 viewer 全局只读（看板+任务明细下钻）。
- Milvus 验收前置（RVW-DES-202）：requirements REQ-NF-002 明确以 Milvus 作为性能验收后端；design 保留 local 降级与小规模模式。
- 报告格式（RVW-DES-203）：requirements API-014 明确 v2.0 仅支持 pdf；docx 预留并返回 `REPORT_002`；design 对齐该口径。

## 建议验证清单（命令级别）
- [ ] 覆盖性：`rg -n "SCN-004|SCN-006|SCN-010|API-005|API-006|API-008|API-013" docs/v2.0/design.md`
- [ ] 决策一致性：`rg -n "viewer|Viewer|REQ-NF-002|Milvus|docx|REPORT_002|API-014" docs/v2.0/design.md docs/v2.0/requirements.md`
- [ ] repo_archive 阈值一致：`rg -n "CODE_SCAN_MAX_FILES|文件数量不超过" docs/v2.0/design.md docs/v2.0/requirements.md`

## 开放问题
- 无（Design 阶段开放问题已在 design v0.8 之前全部关闭）

## 处理记录（建议由开发/人工填写）
| RVW-ID | 严重度 | 处理决策（Fix/Defer/Accept） | Owner | 说明 | 链接/证据 |
|---|---|---|---|---|---|
| RVW-DES-401 | P2 | Fix | AI | 通过更新 `docs/v2.0/status.md` 明确 Implementation 前置门禁（Planning 复查通过） | `docs/v2.0/status.md` |

---

## 追加记录：Design v0.9 引用版本同步复查（2026-02-07）

| 项 | 值 |
|---|---|
| 复查输入 | `docs/v2.0/design.md`（v0.9）对照 `docs/v2.0/requirements.md`（v1.12）、`docs/v2.0/plan.md`（v0.6） |
| 复查结论 | ✅ 通过 |
| 复查说明 | design v0.9 为“引用版本号同步”（requirements v1.12 的错误码口径修复不影响设计实现）；Design 关键决策与接口/数据模型仍保持一致，可进入 Implementation。 |

---

## 追加记录：Design v0.10 审查（2026-02-07）

| 项 | 值 |
|---|---|
| 阶段 | Design |
| 版本号 | v2.0 |
| 日期 | 2026-02-07 |
| 检查点 | 与 requirements v1.14 一致性、UI/UX变更可落地性、接口/数据模型兼容性、回滚与风险收敛 |
| 审查范围 | `docs/v2.0/design.md`（v0.10）新增/修改内容（UI/UX补充与画像字段变更） |
| 输入材料 | `docs/v2.0/requirements.md`（v1.14）、`.claude/templates/review_template.md`、`.claude/phases/03-design.md` |

## 结论摘要
- **总体结论**：⚠️ 有条件通过（补齐3处实现关键口径后可进入 Planning）
- Blockers（P0）：0
- 高优先级（P1）：2
- 其他建议（P2+）：2

## 关键发现（按优先级）

### RVW-DES-501（P1）REQ-016（规则管理/使用说明Modal）的前端设计未落盘，存在实现歧义
- **证据**：`design.md` 新增的 `4.1.3 前端路由与菜单结构` 覆盖了 REQ-021/022，但未明确 REQ-016 的“使用说明按钮/Modal内容/移除页面顶部组件/技术配置默认折叠”的落地策略与影响面。
- **风险**：实现阶段容易出现“仍保留顶部说明卡片/Modal内容不一致/折叠默认态不一致”，导致验收口径争议。
- **建议修改**：
  - 在 `design.md 4.1.3` 或新增小节补齐：`/config/cosmic` 页面交互设计（按钮位置、Modal信息结构、默认折叠组件、与后端无关的说明）
  - 明确“不改COSMIC后端算法/存储/接口”，仅前端改造与文案结构迁移
- **验证方式（可复现）**：
  - `rg -n "REQ-016|COSMIC|使用说明|Modal|/config/cosmic" docs/v2.0/design.md`

### RVW-DES-502（P1）系统画像拆页后缺少“旧路由兼容策略”，易引发线上直达/书签失效
- **证据**：`design.md 4.1.3` 定义新路由 `/system-profiles/import` 与 `/system-profiles/board`，但未说明原 `/system-profiles` 的行为（目前前端已存在该路由）。
- **风险**：用户历史链接/书签或内部跳转仍指向旧路由，导致404或落到错误页面；与“始终可回滚/向后兼容”原则冲突。
- **建议修改**：
  - 在 `design.md 4.1.3` 明确：`/system-profiles` 作为兼容入口，默认重定向到 `/system-profiles/board`（携带 query 参数以保持 TAB 同步）
  - 对应在实现中保留 route redirect（不需要保留旧页面实现）
- **验证方式（可复现）**：
  - `rg -n "/system-profiles\\b" docs/v2.0/design.md`

### RVW-DES-503（P2）business_goals 与历史字段 business_goal 的归一化策略需写清“写入/读取”口径
- **证据**：`design.md 4.2.1` 仅写“允许 business_goal 作为 business_goals 别名”，但缺少“服务端归一化发生在何处、输出是否包含两个字段”的明确口径。
- **风险**：实现期可能只在 embedding 构建处兼容，导致前端编辑/回显字段错位；或写入后数据出现双字段分裂。
- **建议修改**：
  - 明确“canonical key=business_goals”；保存草稿时若仅收到 business_goal 则转换为 business_goals；读取时只返回 business_goals（可选：兼容返回两者，但需注明）
  - 说明对历史 `data/system_profiles.json` 的兼容读取规则（无需一次性迁移，按读写归一化即可）
- **验证方式（可复现）**：
  - `rg -n "business_goal|business_goals" docs/v2.0/design.md`

### RVW-DES-504（P2）“知识导入页不展示导入历史”缺少“如何反馈当前操作结果”的最小交互说明
- **证据**：`design.md 4.1.3` 写“不展示导入历史/最近任务列表”，但未定义代码扫描的“当前任务状态/入库入口”如何展示（REQ-022要求“操作后展示当前任务状态/导入统计作为反馈”）。
- **风险**：实现时要么完全不展示状态导致体验差，要么又回退成“列表”导致与需求冲突。
- **建议修改**：
  - 追加最小交互口径：展示“最近一次提交”的 job_id + 状态（通过 `GET /api/v1/code-scan/jobs/{job_id}` 刷新），并在 completed 时展示“入库”按钮
  - ESB/知识导入用“导入统计 + toast”即可，不保留列表
- **验证方式（可复现）**：
  - `rg -n "不展示导入历史|job_id|code-scan/jobs\\/" docs/v2.0/design.md`

---

## 建议验证清单（命令级别）
- [ ] UI/UX设计覆盖性：`rg -n "REQ-016|REQ-021|REQ-022" docs/v2.0/design.md`
- [ ] 系统画像路由兼容：`rg -n "/system-profiles\\b" docs/v2.0/design.md`
- [ ] 字段归一化口径：`rg -n "business_goal|business_goals" docs/v2.0/design.md`

## 开放问题
- 无（均为设计补齐项，可在Design阶段闭环）

## 处理记录（新增）
| RVW-ID | 严重度 | 处理决策（Fix/Defer/Accept） | Owner | 说明 | 链接/证据 |
|---|---|---|---|---|---|
| RVW-DES-501 | P1 | Fix | AI | 补齐 `/config/cosmic` 的“使用说明Modal/移除顶部说明/技术配置默认折叠”落地口径，明确不改后端 | design.md v0.11 |
| RVW-DES-502 | P1 | Fix | AI | 明确 `/system-profiles` 旧路由重定向到 `/system-profiles/board`（携带query保持TAB同步） | design.md v0.11 |
| RVW-DES-503 | P2 | Fix | AI | 明确 business_goals 作为 canonical key，并补齐读写归一化与兼容返回口径 | design.md v0.11 |
| RVW-DES-504 | P2 | Fix | AI | 明确“最近一次提交”的 code scan job 状态反馈与入库入口（不展示历史列表） | design.md v0.11 |

---

## 追加记录：Design v0.11 修复后复查（2026-02-07）

| 项 | 值 |
|---|---|
| 复查输入 | `docs/v2.0/design.md`（v0.11） |
| 复查结论 | ✅ 通过 |
| 复查说明 | RVW-DES-501~504 已按建议补齐到设计文档，口径可落地且与 requirements v1.14 一致，可进入 Planning。 |

**抽样核对点（证据）**：
- REQ-016落地口径：`rg -n "/config/cosmic|使用说明|Modal|技术配置默认折叠" docs/v2.0/design.md`
- 系统画像旧路由兼容：`rg -n "/system-profiles\\b" docs/v2.0/design.md`
- 字段归一化口径：`rg -n "business_goal|business_goals|canonical key" docs/v2.0/design.md`
- “不展示历史 + 最小反馈”：`rg -n "不展示导入历史|job_id \\+ status|code-scan/jobs" docs/v2.0/design.md`

---

## 追加记录：Design v0.16 增量自审（CR-20260209-001）（2026-02-09）

| 项 | 值 |
|---|---|
| 阶段 | Design |
| 版本号 | v2.0 |
| 日期 | 2026-02-09 |
| 基线版本（对比口径） | design v0.15 |
| 复查口径 | full（CR 触发权限/安全、兼容性） |
| Active CR | CR-20260209-001 |
| 审查范围 | `docs/v2.0/design.md`（v0.16）增量章节：4.3.12/4.3.13、4.4 API摘要表、4.5 配置项、6.1 资源级权限口径 |
| 输入材料 | `docs/v2.0/requirements.md`（v1.21）、`docs/v2.0/review_requirements.md`、`docs/v2.0/cr/CR-20260209-001.md`、`.aicoding/templates/review_template.md` |

## 结论摘要
- **总体结论**：✅ 通过
- Blockers（P0）：0
- 高优先级（P1）：0
- 其他建议（P2+）：0

## 核对点（可复现证据）
- 新增API覆盖：`rg -n "API-016|API-017|API-018" docs/v2.0/design.md`
- 核心流程落盘：`rg -n "^#### 4\\.3\\.12|^#### 4\\.3\\.13" docs/v2.0/design.md`
- 权限口径对齐（主责+B角/发布仅主责/viewer限制）：`rg -n "backup_owner_ids|主责或B角|发布：仅|viewer：禁止" docs/v2.0/design.md`
- 配置项命名对齐（与现有实现一致 + 新增可配项）：`rg -n "CODE_SCAN_REPO_ALLOWLIST|CODE_SCAN_ARCHIVE_MAX_BYTES|CODE_SCAN_ARCHIVE_MAX_FILES|NOTIFICATION_RETENTION_DAYS|OLD_FORMAT_PARSE_TIMEOUT_SECONDS" docs/v2.0/design.md`

## 开放问题
- 无

## 收敛判定
- P0(open)=0 ✅
- P1(open)=0 ✅
- **结论**：Design 阶段已收敛，可自动进入 Planning。
