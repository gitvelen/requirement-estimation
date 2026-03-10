# Review Report：Planning / v2.6

| 项 | 值 |
|---|---|
| 阶段 | Planning |
| 版本号 | v2.6 |
| 日期 | 2026-03-09 |
| 审查范围 | `docs/v2.6/plan.md` |
| 输入材料 | `docs/v2.6/requirements.md`, `docs/v2.6/design.md`, `docs/v2.6/plan.md` |
| 审查者 | Codex |

## §0 审查准备（REP 步骤 A+B）

### A. 事实核实

| # | 声明（出处） | 核实源 | 结论 |
|---|------------|--------|------|
| 1 | 计划包含 6 个独立任务（`plan.md` 任务详情） | `rg -c '^### T[0-9]+' docs/v2.6/plan.md` | ✅ |
| 2 | 每个任务都有可复现验证命令（`plan.md` 任务详情） | `rg -c '^\\*\\*验证方式\\*\\*' docs/v2.6/plan.md` | ✅ |
| 3 | 11 个 REQ/REQ-C 全部被任务引用（`plan.md` 覆盖矩阵） | `review_gate_validate_plan_reverse_coverage` + `requirements=11 / plan=11` | ✅ |
| 4 | Active CR `CR-20260309-001` 已在元信息、任务概览与任务详情显式标注 | `rg -n 'CR-20260309-001' docs/v2.6/plan.md` | ✅ |
| 5 | API/测试/回滚路径与 design 一致：API-001~003、TEST-001~010、`ENABLE_LLM_CHUNKING` 均已落入计划 | `rg -n 'API-001|API-002|API-003|TEST-001|TEST-010|ENABLE_LLM_CHUNKING' docs/v2.6/plan.md` | ✅ |

### B. 关键概念交叉引用

| 概念 | 出现位置 | 口径一致 |
|------|---------|---------|
| 任务 ID（T001~T006） | 任务概览、任务详情、执行顺序 | ✅ |
| REQ-001~REQ-004 | 任务概览、任务详情、REQ 覆盖矩阵 | ✅ |
| REQ-101~REQ-103 | 任务概览、任务详情、REQ 覆盖矩阵 | ✅ |
| REQ-C001~REQ-C004 | 禁止项索引、任务详情、REQ 覆盖矩阵 | ✅ |
| API-001~API-003 | 任务概览、任务详情、REQ 覆盖矩阵 | ✅ |
| TEST-001~TEST-010 | 任务详情、REQ 覆盖矩阵 | ✅ |

## 审查清单

- [x] 任务可追踪：Txxx ID 完整，每条有清晰 DoD
- [x] 粒度合适：可独立实现与验证，依赖关系清晰
- [x] 追溯完整：任务关联 `REQ/SCN/API/TEST`
- [x] 验证可复现：每个任务有命令级别验证方式
- [x] 风险与回滚：涉及线上行为变化的任务收敛到开关/基线回退方案
- [x] 内容完整：覆盖需求、设计、测试与部署收口任务

## 需求反向覆盖

| REQ-ID | 关联任务 | 覆盖判定 | 备注 |
|--------|---------|---------|------|
| REQ-001 | T001, T003, T004, T005 | ✅ | 分块基座、服务编排、原文透传与回归证据均有承接 |
| REQ-002 | T002, T003, T005 | ✅ | 合并原语、服务级合并与回归证据完整 |
| REQ-003 | T001, T003, T004, T005 | ✅ | 单次调用路径、接口兼容与回归承接明确 |
| REQ-004 | T001, T003, T005, T006 | ✅ | 开关降级、测试证据、部署回滚均已纳入 |
| REQ-101 | T001, T002, T003, T005, T006 | ✅ | Token 超限率、日志指标与部署核对均有任务承接 |
| REQ-102 | T005 | ✅ | 覆盖率统计由专门测试任务承接 |
| REQ-103 | T002, T003, T005, T006 | ✅ | latency 指标、服务日志与发布 runbook 均纳入 |
| REQ-C001 | T001, T003, T004, T005, T006 | ✅ | 段落重建顺序（T001）、原文透传、失败不截断、部署回滚路径均覆盖 |
| REQ-C002 | T001, T002, T005 | ✅ | 基座与依赖 diff 共同承接 |
| REQ-C003 | T004, T005, T006 | ✅ | API 契约回归、测试与接口文档同步完整 |
| REQ-C004 | T001, T003, T005 | ✅ | chunk 上限与预算约束在基座/服务/回归三层承接 |

## 关键发现

### 第 1 轮走查（2026-03-09）

#### RVW-PLAN-001：plan.md 引用了不存在的 API 和 TEST 编号 [P1] ✅已修复

**问题描述**：plan.md 中大量引用 `API-001`、`API-002`、`API-003` 和 `TEST-001` 到 `TEST-010`，但 requirements.md 中没有定义这些编号。

**影响**：追溯链断裂，无法验证 API 契约和测试覆盖。

**证据**：
- plan.md 第 40 行任务概览表中有"关联接口（API）"列
- plan.md 第 137 行 T004 任务关联 `API-001, API-002, API-003`
- plan.md 第 227 行覆盖矩阵中引用 `API-001, API-002`
- requirements.md 第 684-732 行只有"数据与接口"章节，但没有 API-001/002/003 的定义
- requirements.md 全文搜索无 `API-001`、`TEST-001` 等编号

**修复动作**：
1. 在 `requirements.md` 补充 6.4 接口清单（API-001~003），明确定义：
   - API-001: `/api/v1/system-profiles/{system_id}/profile/import`（系统画像导入）
   - API-002: `/api/v1/knowledge/imports`（知识导入）
   - API-003: `/api/v1/system-profiles/{system_id}/profile/extraction-status`（抽取状态查询）
2. 在 `requirements.md` 补充 6.5 测试用例清单（TEST-001~010）
3. 更新 `requirements.md` 版本号为 v0.3

**修复证据**：
- `docs/v2.6/requirements.md` 第 733-831 行新增 6.4 和 6.5 章节
- `docs/v2.6/requirements.md` 第 835 行变更记录新增 v0.3
- 验证命令：`rg "^#### API-001|^#### API-002|^#### API-003" docs/v2.6/requirements.md` 输出 3 行
- 验证命令：`rg "^#### TEST-" docs/v2.6/requirements.md | wc -l` 输出 10

**状态**：✅ 已修复

#### RVW-PLAN-002：plan.md 覆盖矩阵缺少 REQ-C001~REQ-C004 [P1] ✅已修复

**问题描述**：plan.md 第 227 行的"任务关联 REQ/覆盖矩阵"只覆盖了 REQ-001~REQ-004 和 REQ-101~REQ-103，缺少 REQ-C001~REQ-C004。

**影响**：禁止项需求的追溯验证不完整。

**证据**：
- plan.md 第 227-239 行覆盖矩阵中没有 REQ-C001~REQ-C004 的行
- 但任务详情中有引用（如 T001 关联 REQ-C002、REQ-C004）

**修复动作**：
1. 在 `plan.md` 覆盖矩阵补充 REQ-C001~REQ-C004 的行
2. 新增 TEST 列，明确每个 REQ 关联的测试用例
3. 修正 REQ-C001 关联任务包含 T001（token_counter.py 的段落重建顺序测试）
4. 更新 `plan.md` 版本号为 v0.2

**修复证据**：
- `docs/v2.6/plan.md` 第 226-237 行覆盖矩阵新增 REQ-C001~REQ-C004
- `docs/v2.6/plan.md` 第 8 行版本号更新为 v0.2
- `docs/v2.6/plan.md` 第 257 行变更记录新增 v0.2
- 验证命令：`rg "REQ-C001|REQ-C002|REQ-C003|REQ-C004" docs/v2.6/plan.md | grep "^| REQ-C" | wc -l` 输出 4

**状态**：✅ 已修复

---

**第 1 轮总结**：发现 2 个 P1 问题，均已修复。修复后 REQ 覆盖率 11/11 = 100%，追溯链完整。

### 第 2 轮走查（2026-03-09）

#### RVW-PLAN-003：plan.md 缺少 `🏁` 里程碑任务，无法满足 Implementation 阶段展示协议 [P1] ✅已修复

**问题描述**：当前变更为后端/逻辑功能，且 `plan.md` 共有 6 个任务，但任务概览的“里程碑”列没有任何 `🏁` 标记，任务详情也未声明里程碑展示内容。

**影响**：进入 Implementation 后无法依据 `plan.md` 判断何时必须向用户展示“核心流程里程碑”和“集成里程碑”，与 `.aicoding/phases/05-implementation.md` 的里程碑展示协议冲突。

**证据**：
- `.aicoding/phases/05-implementation.md` 明确要求：非 UI 且任务数 `> 3` 时，不可跳过里程碑展示
- `docs/v2.6/plan.md` 原任务概览中 `T001~T006` 的“里程碑”列均未包含 `🏁`
- 验证命令：`rg -o "M[0-9]+🏁|🏁" docs/v2.6/plan.md | wc -l` 修复前输出 `0`

**修复动作**：
1. 将 `T003` 标记为 `M2🏁`，作为总结服务 token-aware 双路径跑通后的“核心流程里程碑”
2. 将 `T004` 标记为 `M2🏁`，作为导入接口完成原文透传后的“集成里程碑”
3. 在 `T003` / `T004` 任务详情中补充 `里程碑展示` 段落，明确展示内容与确认要点

**修复证据**：
- `docs/v2.6/plan.md` 任务概览中 `T003` / `T004` 的“里程碑”列已改为 `M2🏁`
- `docs/v2.6/plan.md` 的 `T003` / `T004` 任务详情新增 `**里程碑展示**` 小节
- 验证命令：`rg -n "M2🏁|^\*\*里程碑展示\*\*" docs/v2.6/plan.md` 输出对应任务与小节定位

**状态**：✅ 已修复

#### RVW-PLAN-004：T005/T006 的基线证明口径不成立，无法形成可执行证据 [P1] ✅已修复

**问题描述**：`T005` 原验证命令使用 `git diff -- requirements.txt backend/requirements.txt pyproject.toml`，只检查当前工作区改动；同时仓库内并不存在可解析的 `v2.5` git ref，导致 `T006` 的 `git rev-parse --verify --quiet v2.5^{commit}` 也无法执行。

**影响**：若工作区干净，原 `git diff -- ...` 会给出“无输出”的假阳性；而 `v2.5` ref 不可达会让测试/部署阶段的基线验证命令直接失败，导致“无新增依赖”和“可回滚到基线”都缺少有效证据。

**证据**：
- `docs/v2.6/plan.md` 原 `T005` 验证命令未包含基线 tag 或 commit
- 初始 `docs/v2.6/status.md` 使用别名 `v2.5` 作为基线版本，但仓库 `git tag --list 'v2*'` 结果仅有 `v2.0.0`、`v2.1`、`v2.2`、`v2.3`、`v2.4`
- `git rev-parse --verify --quiet v2.5^{commit}` 返回非 0，说明 `v2.5` 不是可达 git ref
- 依赖证明目标应是“相对可达基线 ref 无新增运行时依赖”，而非“当前工作区无未提交改动”

**修复动作**：
1. 将 `plan.md` 文档元信息中的“基线版本（对比口径）”从不可达别名 `v2.5` 解析为当前仓库可验证 commit `7a0c6befb88ad848459264ba2456543bea5f9b44`
2. 将 `T005` 任务描述与验证命令改为基于该 commit 的差异证明：`git diff --unified=0 7a0c6befb88ad848459264ba2456543bea5f9b44 -- requirements.txt backend/requirements.txt pyproject.toml`
3. 将 `T006` 的基线回滚点说明与验证命令同步改为该 commit：`git rev-parse --verify --quiet 7a0c6befb88ad848459264ba2456543bea5f9b44^{commit}`
4. 更新 `plan.md` 版本号为 v0.4 并追加变更记录

**修复证据**：
- `docs/v2.6/plan.md` 文档元信息、`T005`、`T006` 与变更记录均已显式引用 commit `7a0c6befb88ad848459264ba2456543bea5f9b44`
- 验证命令：`rg -n "7a0c6befb88ad848459264ba2456543bea5f9b44|git diff --unified=0 7a0c6befb88ad848459264ba2456543bea5f9b44|git rev-parse --verify --quiet 7a0c6befb88ad848459264ba2456543bea5f9b44\\^\\{commit\\}" docs/v2.6/plan.md`
- 验证命令：`git rev-parse --verify --quiet 7a0c6befb88ad848459264ba2456543bea5f9b44^{commit}` 成功返回 commit

**状态**：✅ 已修复

---

**第 2 轮总结**：发现 2 个 P1 问题，均已修复。修复后计划文档同时满足追溯闭环、Implementation 里程碑展示协议和“可达基线 ref”证据口径。

### 第 3 轮补记（2026-03-09）

**背景**：用户确认需要正式 `v2.5` tag 后，已在仓库为 commit `7a0c6befb88ad848459264ba2456543bea5f9b44` 补建 annotated tag `v2.5`。

**处理动作**：
1. 将 `docs/v2.6/plan.md` 的基线口径从临时 commit fallback 回切为正式 tag `v2.5`
2. 将 `docs/v2.6/status.md` 的 `_baseline` 与回滚描述同步回切为 `v2.5`
3. 将本审查记录中的验证命令同步回切为 `v2.5^{commit}` 口径

**验证证据**：
- `git rev-parse --verify --quiet v2.5^{commit}` 成功返回 `7a0c6befb88ad848459264ba2456543bea5f9b44`
- `git cat-file -t v2.5` 输出 `tag`
- `docs/v2.6/plan.md` 已更新为 `v0.5`，基线版本恢复为 `v2.5`

**结论**：无新增开放问题；本轮为基线标识归一化补记，不改变 P0/P1 统计。

## §3 覆盖率证明（REP 步骤 D）

| 维度 | 应检项数 | 已检 | 未检 | 未检说明 |
|------|---------|------|------|---------|
| 事实核实（步骤A） | 5 | 5 | 0 | - |
| 概念交叉引用（步骤B） | 6 | 6 | 0 | - |
| 审查清单项 | 6 | 6 | 0 | - |
| REQ-ID 反向覆盖项 | 11 | 11 | 0 | - |

## 对抗性自检
- [x] 不存在"我知道意思但文本没写清"的关键行为
- [x] 所有"可选/或者/暂不"表述已收敛为单一口径
- [x] 高风险项（原文无损、API 兼容、回滚、依赖约束）已在本阶段收敛

## 收敛判定
- P0(open): 0
- P1(open): 0
- P1(fixed): 4
- 结论：✅ 通过（累计 2 轮发现 4 个 P1，均已全部修复）

<!-- REVIEW-SUMMARY-BEGIN -->
REVIEW_STAGE: planning
REVIEW_RESULT: pass
P0_OPEN: 0
P1_OPEN: 0
P1_FIXED: 4
RVW_TOTAL: 4
REVIEWER: Codex
REVIEW_AT: 2026-03-09
VERIFICATION_COMMANDS: bash -lc 'source .aicoding/scripts/lib/review_gate_common.sh && review_gate_validate_plan_reverse_coverage requirements docs/v2.6/requirements.md plan docs/v2.6/plan.md'; rg -n "^### T[0-9]+|^\\*\\*验证方式\\*\\*" docs/v2.6/plan.md; bash -lc 'echo requirements=$(rg -o "REQ-C?[0-9]{3}" docs/v2.6/requirements.md | sort -u | wc -l); echo plan=$(rg -o "REQ-C?[0-9]{3}" docs/v2.6/plan.md | sort -u | wc -l)'; rg -n "CR-20260309-001|API-001|API-002|API-003|TEST-001|TEST-010|ENABLE_LLM_CHUNKING" docs/v2.6/plan.md; rg "^#### API-001|^#### API-002|^#### API-003" docs/v2.6/requirements.md; rg "^#### TEST-" docs/v2.6/requirements.md | wc -l; rg "REQ-C001|REQ-C002|REQ-C003|REQ-C004" docs/v2.6/plan.md | grep "^| REQ-C" | wc -l; rg -o "M[0-9]+🏁|🏁" docs/v2.6/plan.md | wc -l; rg -n "M2🏁|^\\*\\*里程碑展示\\*\\*|\\| 版本 \\| v0\\.5|git diff --unified=0 v2.5|git rev-parse --verify --quiet v2.5\\^\\{commit\\}" docs/v2.6/plan.md; git cat-file -t v2.5; git rev-parse --verify --quiet v2.5^{commit}
<!-- REVIEW-SUMMARY-END -->
