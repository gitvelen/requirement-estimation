# Review Report：Design / v2.4

| 项 | 值 |
|---|---|
| 阶段 | Design |
| 版本号 | v2.4 |
| 日期 | 2026-02-28 |
| 审查范围 | design.md |
| 输入材料 | requirements.md, design.md |

## §0 审查准备（REP 步骤 A+B）

### A. 事实核实

| # | 声明（出处） | 核实源 | 结论 |
|---|------------|--------|------|
| 1 | 设计覆盖全部 REQ/REQ-C（`design.md` §2.1） | `requirements.md` §3/§4/§4A + trace 覆盖命令 | ✅ |
| 2 | 画像回滚接口为 `POST /api/v1/system-profiles/{system_id}/profile/suggestions/rollback`（`design.md` §5.4 API-006） | `design.md` §6.4 L1、§7.1 回滚测试项 | ✅（已统一） |
| 3 | 回滚无历史错误码为 `ROLLBACK_NO_PREVIOUS (409)`（`design.md` §5.4、§5.3.5） | `requirements.md` §6.3；`design.md` §7.1 | ✅（已统一） |
| 4 | 提取任务状态口径为 `pending|processing|completed|failed`（`design.md` API-003） | `requirements.md` §6.2；`design.md` §7.1 | ✅（已统一） |
| 5 | 多系统通知类型口径为 `multi_system_detected`（`design.md` API-003） | `design.md` §7.1/§7.2 | ✅（已统一） |
| 6 | `AI_EXTRACTION_TIMEOUT` 环境口径一致（`design.md` §0.5、§5.6、§6.1） | `rg -n "AI_EXTRACTION_TIMEOUT"` | ✅（已统一为 120） |
| 7 | Requirements 与 Design 的接口前缀/资源路径口径一致（`requirements.md` §6.2，`design.md` §5.4） | `rg -n "/api/systems/|/api/tasks/|/api/reports/" docs/v2.4/requirements.md docs/v2.4/design.md` | ✅（已统一为 `/api/v1/system-profiles`、`/api/v1/tasks`、`/api/v1/reports`） |
| 8 | Design API 契约完整性（路径/参数/返回/权限/错误）达标（`design.md` §5.4） | `review_gate_validate_design_api_contracts` | ✅（已补齐 API-009~012 参数/错误处理，并消除非契约段误判） |

### B. 关键概念交叉引用

| 概念 | 出现位置 | 口径一致 |
|------|---------|---------|
| `ROLLBACK_NO_PREVIOUS` | §5.3.2, §5.3.5, §5.4 API-006, §7.1 | ✅ |
| `PERMISSION_DENIED_NOT_OWNER` | §5.3.5, §5.4(API-001/005/006/008), §5.8, §7.1 | ✅ |
| `/api/v1/system-profiles/{...}` | §5.1, §5.3, §5.4, §6.4, §7.1 | ✅ |
| `/api/v1/tasks/{task_id}` / `/api/v1/reports/{report_id}` | `requirements.md` §6.2, `design.md` §5.1/§5.4 | ✅ |
| REQ-005/006/007/008/010/011/012 追溯 | §2.1, §7.1, §7.2, §9.1, §9.2 | ✅ |

## 审查清单

- [x] 与需求一一对应：关键设计点可追溯到 REQ/SCN
- [x] 依赖关系合理：模块职责与依赖可落地
- [x] 失败路径充分：超时/降级/越权/无历史回滚已定义
- [x] 兼容与回滚：L1/L2 回滚与迁移兼容口径明确
- [x] 安全设计：写操作权限、文件上传、密钥策略明确
- [x] API 契约完整：路径/参数/响应/权限/错误码齐备
- [x] REQ-C 覆盖：各禁止项在设计中有明确防护

## 需求覆盖判定

| REQ-ID | 设计覆盖 | 对应章节 | 备注 |
|--------|---------|---------|------|
| REQ-001 | ✅ | §5.10.1, §5.4 API-001/002 | 导入页重构+导入历史 |
| REQ-002 | ✅ | §5.10.2, §5.4 API-004 | 时间线与三区布局 |
| REQ-003 | ✅ | §5.10.2, §5.4 API-005/006 | inline diff + 采纳/回滚 |
| REQ-004 | ✅ | §5.3.1, §5.5, §5.4 API-003 | 异步提取与串行化 |
| REQ-005 | ✅ | §5.3.1, §5.4 API-003 | 多系统过滤与通知 |
| REQ-006 | ✅ | §5.3.3, §5.4 API-011 | LLM 三点估计与降级 |
| REQ-007 | ✅ | §5.10.4, §5.4 API-012 | 报告导出增强 |
| REQ-008 | ✅ | §5.10.3 | 评估页展示期望值+展开 |
| REQ-009 | ✅ | §5.1, §5.4 API-009 | AI 原始输出快照 |
| REQ-010 | ✅ | §5.3.4, §5.4 API-010 | 两阶段 diff + correction history |
| REQ-011 | ✅ | §5.8, §5.4 写接口权限 | PM-系统写权限绑定 |
| REQ-012 | ✅ | §5.2, §5.10.2, §6.3 | 5 域 12 子字段重构 |
| REQ-101~106 | ✅ | §2.1, §5.3.5, §6.4 | 非功能目标可追溯 |
| REQ-C001~C007 | ✅ | §2.1, §5.x, §6.4 | 禁止项均有对应防护 |

## 高风险语义审查（必做）

- [x] REQ-C 禁止项：均有可验证防护设计
- [x] 兼容跳转语义：未出现含糊跳转（新增路由禁止项未违背）
- [x] 新增 API 契约：路径/参数/返回/权限/错误码完整
- [x] “可选/二选一/仅提示”表述：无影响验收口径的歧义残留
- [x] 回滚路径：L1 功能级 + L2 版本级可执行

## 关键发现

### RVW-DES-001（P1）API 路径/方法与错误码口径不一致
- 证据：修复前 `§6.4/§7.1` 与 `§5.4` 存在 `/api/systems/...`、`PUT ...rollback`、`NO_PREVIOUS_SUGGESTIONS` 等不一致。
- 风险：实现按不同章节落地会出现接口不兼容和验收争议。
- 处置：已修复并统一到 `API-006` 口径（`POST /api/v1/system-profiles/.../suggestions/rollback` + `ROLLBACK_NO_PREVIOUS(409)`）。

### RVW-DES-002（P1）测试追溯与 REQ 映射错位
- 证据：修复前 `§7.1/§7.2/§9.x` 存在 REQ-005/006/007/008/010/011/012 多处错配。
- 风险：测试与实现优先级会偏离需求真实边界。
- 处置：已修复测试表与 WBS 的 REQ 关联，形成“REQ→设计→测试/任务”闭环。

### RVW-DES-003（P1）环境参数口径冲突
- 证据：修复前 `§6.1` 与 `§0.5/§5.6/§5.5` 的 `AI_EXTRACTION_TIMEOUT` 值冲突。
- 风险：部署与运行期行为不可预测。
- 处置：已统一为 `AI_EXTRACTION_TIMEOUT=120`。

### RVW-DES-004（P1）Requirements 与 Design 接口契约前缀不一致
- 证据：修复前 `requirements.md` §6.2/§3.2（REQ-004）使用 `/api/systems|/api/tasks|/api/reports`，而 `design.md` 使用 `/api/v1/system-profiles|/api/v1/tasks|/api/v1/reports`。
- 风险：实现与验收将出现双口径，导致接口联调和测试脚本不可复用。
- 处置：已修复 `requirements.md` 到 v1.3（统一为 `/api/v1/...`）并同步 `design.md` 关联版本与 path 占位符口径（`system_id/task_id/report_id`）。

### RVW-DES-005（P1）API-009~012 契约粒度不完整（参数/错误处理缺失）
- 证据：修复前 `API-009~012` 缺少 path 参数表和错误处理说明；`review_gate_validate_design_api_contracts` 报告契约不完整。
- 风险：实现人员在任务查询、估算执行、报告导出场景可能对失败路径处理不一致，导致联调反复。
- 处置：已补齐 API-009~012 的请求参数与错误处理口径，并对流程/测试段补充“以 API 契约为准”约束，复跑 `review_gate_validate_design_api_contracts` 通过。

## §3 覆盖率证明（REP 步骤 D）

| 维度 | 应检项数 | 已检 | 未检 | 未检说明 |
|------|---------|------|------|---------|
| 事实核实（步骤A） | 8 | 8 | 0 | — |
| 概念交叉引用（步骤B） | 5 | 5 | 0 | — |
| 审查清单项 | 7 | 7 | 0 | — |
| REQ-ID 覆盖项 | 25 | 25 | 0 | — |

## 对抗性自检
- [x] 不存在“我知道意思但文本没写清”的关键口径
- [x] 新增 API 均有完整契约
- [x] 无影响验收的“可选/或者/暂不”歧义口径
- [x] 高风险项已在 Design 阶段收敛

## 收敛判定
- P0(open): 0
- P1(open): 0
- 结论：✅ 通过

<!-- REVIEW-SUMMARY-BEGIN -->
REVIEW_STAGE: design
REVIEW_RESULT: pass
P0_OPEN: 0
P1_OPEN: 0
RVW_TOTAL: 5
REVIEWER: Codex
REVIEW_AT: 2026-02-28
VERIFICATION_COMMANDS: bash -lc 'source .aicoding/scripts/lib/review_gate_common.sh && review_gate_validate_requirements_integrity requirements docs/v2.4/requirements.md && review_gate_validate_design_trace_coverage requirements docs/v2.4/requirements.md design docs/v2.4/design.md && review_gate_validate_design_api_contracts design docs/v2.4/design.md'; rg -n '/api/systems/|/api/tasks/|/api/reports/' docs/v2.4/requirements.md docs/v2.4/design.md; rg -n '/api/v1/system-profiles|/api/v1/tasks|/api/v1/reports' docs/v2.4/requirements.md docs/v2.4/design.md; rg -n 'AI_EXTRACTION_TIMEOUT' docs/v2.4/design.md
<!-- REVIEW-SUMMARY-END -->
