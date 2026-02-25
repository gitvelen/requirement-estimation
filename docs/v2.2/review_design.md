# Review Report：Design / v2.2

| 项 | 值 |
|---|---|
| 阶段 | Design |
| 版本号 | v2.2 |
| 日期 | 2026-02-24 |
| 基线版本（对比口径） | `v2.1` |
| 当前代码版本 | `HEAD` |
| 复查口径 | full |
| Active CR（如有） | 无 |
| 检查点 | 需求追溯覆盖、约束/禁止项覆盖、兼容跳转策略、回滚方案、接口变更向后兼容性 |
| 审查范围 | 文档：`docs/v2.2/design.md`、`docs/v2.2/requirements.md`、`docs/v2.2/status.md` |
| 输入材料 | `docs/v2.2/design.md`、`docs/v2.2/requirements.md`、`.aicoding/phases/03-design.md`、`.aicoding/templates/design_template.md` |

## 结论摘要
- 总体结论：✅ 通过（Design 第 4 轮边审边改补齐 GWT 细节口径；RVW-001~011 已关闭）
- Blockers（P0）：0
- 高优先级（P1）：0
- 其他建议（P2+）：0

## 关键发现（按优先级）
（无）

## 建议验证清单（命令级别）
- [x] 追溯覆盖检查（requirements → design，已执行 exit=0）：`bash -lc 'source .aicoding/scripts/lib/review_gate_common.sh && review_gate_validate_design_trace_coverage requirements docs/v2.2/requirements.md design docs/v2.2/design.md'`
- [x] 排行榜“计算逻辑”文案存在性：`rg -n "计算逻辑：" docs/v2.2/design.md`
- [x] 报告下载空态口径存在性：`rg -n "暂无可下载报告" docs/v2.2/design.md`
- [x] ESB 列映射提示契约存在性：`rg -n "mapping_resolved" docs/v2.2/design.md`
- [x] doc_type 传参约定存在性：`rg -n "doc_type" docs/v2.2/design.md`

## 开放问题
- [ ] 无（Design 阶段不阻塞项已在设计文档风险章节显式记录）

## 收敛判定
- 本轮后：P0(open)=0, P1(open)=0
- 距离收敛：是
- 建议：✅ Design 已收敛，可进入 Planning 阶段

---

## 2026-02-24 13:55 | 第 2 轮 | 审查者：Codex（独立审查）

### 审查角度
- 独立走查 `docs/v2.2/design.md` 与 `docs/v2.2/requirements.md` 的一致性与可落地性（重点：REQ-C / GWT 可验收闭环）
- 证据（已执行）：
  - Trace 覆盖门禁（exit=0）：`bash -lc 'source .aicoding/scripts/lib/review_gate_common.sh && review_gate_validate_design_trace_coverage requirements docs/v2.2/requirements.md design docs/v2.2/design.md'`
  - REQ-101 设计覆盖检索：`rg -n "加载|空态|错误态|重试" docs/v2.2/design.md`
  - ESB 合约覆盖检索：`rg -n "/api/v1/esb" docs/v2.2/design.md`

### 上一轮问题处理状态
| RVW-ID | 严重度 | 上一轮描述 | 处理方式 | 本轮状态 |
|---|---|---|---|---|
| - | - | 第 1 轮为自审收敛（无 RVW 项） | - | - |

### 本轮新发现问题
| RVW-ID | 严重度 | 描述 | 证据 | 建议 |
|---|---|---|---|---|
| RVW-001 | P1 | `/reports/ai-effect` 的兼容口径与 REQ-012 存在歧义：REQ 要求“自动跳转到 `/dashboard/reports` + 一次性提示”，但设计写为“保留兼容路由，仅做跳转提示”，未明确“replace/一次性提示”是否覆盖该入口 | `docs/v2.2/requirements.md:442`；`docs/v2.2/design.md:170`、`docs/v2.2/design.md:173` | 在 design.md 明确：`/reports/ai-effect` 必须 `replace` 到 `/dashboard/reports` 且展示一次性提示（与 `/dashboard?page=ai` 同口径）；验收建议按 `GWT-REQ-012-01` + `GWT-REQ-102-01` 组合验证 |
| RVW-002 | P1 | 备注字段的数据模型与落地口径不一致：决策 D-11 明确“任务级 remark 按行追加”，但详细设计又写为 `remark` 或 `remark_lines` 二选一；且 Requirements 数据字典已约束为 `remark: text`，验收还要求“按时间倒序排列” | `docs/v2.2/design.md:46`、`docs/v2.2/design.md:238`；`docs/v2.2/requirements.md:583`、`docs/v2.2/requirements.md:429` | 统一为 `remark`（text，多行）并在 design.md 补齐：行格式（建议含时间戳+来源+摘要）、排序口径（前端倒序渲染 vs 后端插入顺序）、兼容旧人工备注的拼接规则；补充最小抽样验收步骤覆盖 `GWT-REQ-011-01/03/04` |
| RVW-003 | P1 | REQ-101（统一加载/空/错误态 + 重试）在 design.md 中仅出现在追溯矩阵，未给出可复用的页面级落地规范，存在实现分散导致验收不一致的风险 | `docs/v2.2/design.md:99`；`docs/v2.2/requirements.md:482` | 在 design.md 增补“统一状态规范”：推荐的 UI 组件（Spin/Empty/Alert）、触发条件、重试交互、最小页面清单（rankings/reports/tasks/*/任务详情/画像导入）；并在 plan.md 对应拆任务（含验证：GWT-REQ-101-01/02/03） |
| RVW-004 | P1 | ESB 导入后“检索/过滤/统计面板”缺少后端契约设计：设计提到需要 search/stats 能力，但未定义 API（路径/参数/返回字段/权限）；Requirements 的 `include_deprecated=false` 检索验收无法落地 | `docs/v2.2/requirements.md:402`、`docs/v2.2/requirements.md:408`；`docs/v2.2/design.md:225`；（设计中仅出现 `POST /api/v1/esb/imports`：`docs/v2.2/design.md:223`） | 在 design.md 明确新增/复用的 ESB API（建议：list/search + stats 两类），并写清 `include_deprecated`、`scope`、分页、返回字段（至少包含 status）；同时补齐权限口径（主责/B角/管理员）；验收覆盖 `GWT-REQ-009-02` |
| RVW-005 | P1 | “实质性修改 confirm 强制”缺少后端判定规则：设计要求后端强制 `confirm=true` 才允许持久化，但未定义后端如何识别“实质性修改”以同时满足“非实质性修改可直接保存”（REQ-007-03）与“不可绕过确认”（REQ-C002） | `docs/v2.2/requirements.md:365`、`docs/v2.2/requirements.md:378`；`docs/v2.2/design.md:215` | 在 design.md 补齐后端判定规则（字段/操作白名单、diff 口径、未知变更按“实质性”处理）与失败返回（HTTP/错误码/提示语）；建议在测试阶段增加负向用例覆盖“绕过确认提交” |
| RVW-006 | P2 | `doc_type` 作为 enum 未给出稳定取值（仅有 UI 文案），后续检索/审计/统计可能受影响 | `docs/v2.2/requirements.md:582`；`docs/v2.2/design.md:222` | 在 design.md/接口文档补齐 `doc_type` 枚举（建议用稳定 code，如 `requirements/design/tech_solution/history_report`），并说明前端展示文案与 code 的映射 |
| RVW-007 | P2 | 回滚章节偏“策略陈述”，缺少可执行的触发条件与最小 Runbook（尤其是涉及旧入口兼容与提示逻辑时） | `docs/v2.2/design.md:261` | 在 design.md 将 §7 补成可执行清单：触发条件、回滚步骤、验证点（菜单巡检/旧 URL 跳转/报告下载/编辑确认） |

### 收敛判定
- 本轮后：P0(open)=0, P1(open)=5
- 距离收敛：否
- 建议：先补齐/澄清上述 P1 的设计口径并回写 `design.md`（或在 `plan.md` 明确 Fix 并形成可验收证据），再进入 Implementation 阶段

---

## 2026-02-24 14:07 | 第 3 轮 | 审查者：Codex（边审边改）

### 审查角度
- 对照 RVW-001~007 逐项复核整改是否已回写到 `docs/v2.2/design.md`（当前文档版本：v0.2）
- 证据（已执行）：
  - Trace 覆盖门禁（exit=0）：`bash -lc 'source .aicoding/scripts/lib/review_gate_common.sh && review_gate_validate_design_trace_coverage requirements docs/v2.2/requirements.md design docs/v2.2/design.md'`

### 上一轮问题处理状态
| RVW-ID | 严重度 | 上一轮描述 | 处理方式 | 本轮状态 |
|---|---|---|---|---|
| RVW-001 | P1 | `/reports/ai-effect` 兼容跳转与“一次性提示”口径不清 | 明确 replace 跳转与提示口径（§5.2.1） | ✅ 已修复 |
| RVW-002 | P1 | remark 数据模型口径不一致（`remark` vs `remark_lines`） | 统一为任务级 `remark`（text，多行，新记录置顶），补齐格式与排序（§0.5 D-11、§5.9） | ✅ 已修复 |
| RVW-003 | P1 | REQ-101 缺少统一落地规范 | 增补统一 Loading/Empty/Error/Retry 规范（§5.11） | ✅ 已修复 |
| RVW-004 | P1 | ESB 检索/统计面板缺少后端契约 | 增补 `GET /api/v1/esb/search` + `GET /api/v1/esb/stats` 契约（§0.5 D-12、§5.7.1） | ✅ 已修复 |
| RVW-005 | P1 | confirm 强制缺少后端判定规则 | 补齐实质性修改判定、confirm 传参约定与拒绝口径（§5.5.2） | ✅ 已修复 |
| RVW-006 | P2 | `doc_type` enum 未定义稳定取值 | 补齐 `doc_type` 稳定 code 映射（§5.6） | ✅ 已修复 |
| RVW-007 | P2 | 回滚缺少可执行 Runbook | 补齐触发条件与最小回滚步骤（§7） | ✅ 已修复 |

### 本轮新发现问题
| RVW-ID | 严重度 | 描述 | 证据 | 建议 |
|---|---|---|---|---|
| （无） | - | - | - | - |

### 收敛判定
- 本轮后：P0(open)=0, P1(open)=0
- 距离收敛：是
- 建议：✅ Design 已收敛，可继续 Planning/Implementation 阶段

---

## 2026-02-24 15:50 | 第 4 轮 | 审查者：Codex（边审边改）

### 审查角度
- 从 requirements 的 GWT 文本抽检 Design 易漏点：排行榜“计算逻辑”固定文案、报告下载空态、ESB 列映射提示、doc_type 传参一致性
- 证据（已执行）：
  - Trace 覆盖门禁（exit=0）：`bash -lc 'source .aicoding/scripts/lib/review_gate_common.sh && review_gate_validate_design_trace_coverage requirements docs/v2.2/requirements.md design docs/v2.2/design.md'`
  - 排行榜“计算逻辑”文案检索：`rg -n "计算逻辑：" docs/v2.2/design.md`
  - 报告下载空态口径检索：`rg -n "暂无可下载报告" docs/v2.2/design.md`
  - ESB 列映射提示契约检索：`rg -n "mapping_resolved" docs/v2.2/design.md`
  - doc_type 传参约定检索：`rg -n "doc_type" docs/v2.2/design.md`

### 本轮新发现问题
| RVW-ID | 严重度 | 描述 | 证据 | 建议 |
|---|---|---|---|---|
| RVW-008 | P1 | REQ-003 要求每个排行 Tab 右下角固定展示“计算逻辑：…近90天…”文案（GWT-REQ-003-02），design.md 未显式约束易导致实现遗漏 | `docs/v2.2/requirements.md:301`、`docs/v2.2/requirements.md:309` | 已在 `docs/v2.2/design.md` §5.2.1 补齐固定文案口径与三条“计算逻辑”文案 |
| RVW-009 | P1 | REQ-006 要求无报告版本时“下载报告”置灰并提示“暂无可下载报告”（GWT-REQ-006-02），design.md 未显式约束易漏实现 | `docs/v2.2/requirements.md:355` | 已在 `docs/v2.2/design.md` §5.4 补齐报告下载空态口径 |
| RVW-010 | P1 | REQ-009 要求 ESB 导入界面提供“列映射预览（或映射结果提示）”与导入结果（GWT-REQ-009-01）；design.md 仅提到保留 mapping_json 输入，缺少“提示/预览”落点 | `docs/v2.2/requirements.md:407` | 已在 `docs/v2.2/design.md` §5.6 补齐：ESB 导入响应新增 `mapping_resolved` 并前端展示作为“映射结果提示/预览” |
| RVW-011 | P1 | REQ-008 要求非 ESB 文档导入复用 `POST /api/v1/knowledge/imports` 并新增 `doc_type` 标记（GWT-REQ-008-02）；design.md 未写清与既有 `knowledge_type/level` 的参数组合，存在前后端联调口径不一致风险 | `docs/v2.2/requirements.md:388`、`docs/v2.2/requirements.md:390` | 已在 `docs/v2.2/design.md` §5.6 明确：非 ESB 固定 `knowledge_type=document`、`level=normal` 并追加 `doc_type`（可选字段，向后兼容） |

### 收敛判定
- 本轮后：P0(open)=0, P1(open)=0
- 距离收敛：是
- 建议：✅ Design 已收敛，可继续 Planning/Implementation 阶段
