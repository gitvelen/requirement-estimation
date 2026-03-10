# Review Report：Requirements / v2.6

> 轻量审查模板：聚焦需求完整性、GWT 可判定性、禁止项固化。
> 本轮按“边审边改”执行，结论基于 `requirements.md v0.2`。

| 项 | 值 |
|---|---|
| 阶段 | Requirements |
| 版本号 | v2.6 |
| 日期 | 2026-03-09 |
| 审查范围 | `docs/v2.6/requirements.md` |
| 输入材料 | `docs/v2.6/proposal.md`、`docs/v2.6/cr/CR-20260309-001.md`、仓库现状代码/配置 |

## §0 审查准备（REP 步骤 A+B）

### A. 事实核实

| # | 声明（出处） | 核实源 | 结论 |
|---|------------|--------|------|
| 1 | 需求以“25,000 tokens 输入上限 + 32,000 上下文”作为核心口径（requirements §1.3） | `docs/v2.6/proposal.md`、`docs/v2.6/cr/CR-20260309-001.md` | ✅ |
| 2 | 本次变更不允许静默截断，关闭分块后超长文档必须显式失败（requirements §2.3/REQ-004） | `docs/v2.6/proposal.md` §分块与降级规则 | ✅ |
| 3 | API 契约不变，仅允许内部失败原因细分（requirements §1.2/REQ-C003/§6.2） | `backend/api/system_profile_routes.py` 导入接口响应结构 | ✅ |
| 4 | 系统画像 Stage2 结构使用 `module_name`、`system_description` 等字段（requirements REQ-002） | `backend/service/profile_summary_service.py` LLM prompt 与归一化逻辑 | ✅ |
| 5 | 文档导入链路会把解析后的文本片段写入现有知识库存储（requirements §5.2/§6.1） | `backend/api/system_profile_routes.py`、`backend/service/knowledge_service.py` | ✅ |
| 6 | 仓库现有环境文件为 `.env.backend`、`.env.backend.example`、`.env.backend.internal`（requirements §1.1） | 仓库根目录文件清单 | ✅ |

### B. 关键概念交叉引用

| 概念 | 出现位置 | 口径一致 |
|------|---------|---------|
| `25,000 tokens` 输入上限 | §1.3, SCN-001, SCN-003, REQ-001, REQ-004, REQ-C004 | ✅ |
| “任一块失败则整体失败，不产出部分结果” | SCN-001, SCN-006, SCN-007, REQ-001 | ✅ |
| API 顶层 `error_code` 保持现状 | §1.2, REQ-C003, §6.2 | ✅ |
| Stage2 字段契约 `module_name` / `system_description` | SCN-007, REQ-002 | ✅ |
| 非 UI / 非 DB / 非 embedding chunk scope | `proposal.md` Non-goals, 本文 review 约束清单 | ✅ |
| 测试等级采用 `Unit Only`，不回退为强制集成测试 | REQ-001 ~ REQ-004, `docs/v2.6/review_proposal.md` 第 3 轮 | ✅ |

## 审查清单

- [x] Proposal 覆盖：每个 P-DO/P-DONT/P-METRIC 在 §1.4 覆盖映射表中有对应 REQ-ID 或标注 defer
- [x] 需求可验收：每条 REQ 有 GWT 格式验收标准，无“优化”“提升”等模糊词
- [x] 场景完整：正常/异常/边界场景均已覆盖
- [x] GWT 可判定：Given/When/Then 三段均为具体可观测行为，无歧义
- [x] 禁止项固化：对话中出现的“不要/禁止/不允许”已固化为 REQ-C + GWT 或保留在 proposal Non-goals
- [x] REQ-C 完整：每条 REQ-C 有对应 GWT-ID，可被门禁校验
- [x] ID 唯一性：REQ-ID / GWT-ID 无重复
- [x] 术语一致：关键术语与 proposal/CR/代码契约一致，无歧义别名

## 禁止项/不做项确认清单

| # | 禁止/不做项描述 | 归类 | 目标 | 来源 |
|---|----------------|------|------|------|
| 1 | 不允许文档内容丢失 | A | REQ-C001 | `proposal.md` P-DONT-01 |
| 2 | 不允许引入外部 token 计数依赖 | A | REQ-C002 | `proposal.md` P-DONT-02 |
| 3 | 不允许修改系统画像导入 API 契约 | A | REQ-C003 | `proposal.md` P-DONT-03 |
| 4 | 不允许生成超限 chunk | A | REQ-C004 | `proposal.md` P-DONT-04 |
| 5 | 不修改 Embedding 服务的分块逻辑 | B | Non-goals | `proposal.md` Non-goals |
| 6 | 不做前端 UI 变更 | B | Non-goals | `proposal.md` Non-goals |
| 7 | 不做数据库 schema 变更 | B | Non-goals | `proposal.md` Non-goals |

<!-- CONSTRAINTS-CHECKLIST-BEGIN -->
| ITEM | CLASS | TARGET | SOURCE |
|------|-------|--------|--------|
| 不允许文档内容丢失 | A | REQ-C001 | proposal.md P-DONT-01 |
| 不允许引入外部 token 计数依赖 | A | REQ-C002 | proposal.md P-DONT-02 |
| 不允许修改系统画像导入 API 契约 | A | REQ-C003 | proposal.md P-DONT-03 |
| 不允许生成超限 chunk | A | REQ-C004 | proposal.md P-DONT-04 |
| 不修改 Embedding 服务的分块逻辑 | B | Non-goals | proposal.md Non-goals |
| 不做前端 UI 变更 | B | Non-goals | proposal.md Non-goals |
| 不做数据库 schema 变更 | B | Non-goals | proposal.md Non-goals |
<!-- CONSTRAINTS-CHECKLIST-END -->

## 需求覆盖判定

| REQ-ID | GWT 数量 | GWT 可判定 | 备注 |
|--------|---------|-----------|------|
| REQ-001 | 4 | ✅ | 已补齐“任一块失败则整体失败”口径 |
| REQ-002 | 4 | ✅ | 已修正 Stage2 字段契约与去重字段 |
| REQ-003 | 2 | ✅ | 已改为验证“不进入分块路径” |
| REQ-004 | 2 | ✅ | 已去除“回退到 v2.5 截断逻辑”的歧义 |
| REQ-101 | 1 | ✅ | 已改为可准备的夹具口径 |
| REQ-102 | 1 | ✅ | 已补充 `pytest-cov` 仅属测试工具说明 |
| REQ-103 | 1 | ✅ | 已补充失败块耗时统计口径 |
| REQ-C001 | 2 | ✅ | 已将“段落总数 >= N”改为“重建序列完全一致” |
| REQ-C002 | 1 | ✅ | 与 proposal 一致 |
| REQ-C003 | 1 | ✅ | 已收敛为保持顶层 API error 契约 |
| REQ-C004 | 1 | ✅ | 与 proposal 一致 |

## 高风险语义审查（必做）

- [x] REQ-C 禁止项：每条在 `requirements.md` 中有明确 GWT，不是仅“提及”
- [x] “可选/二选一/仅提示”表述：已收敛为单一口径
- [x] 角色差异：已明确产品内角色与部署运维角色的边界
- [x] 数据边界：已明确持久化边界、错误边界、失败块处理和计时口径

## 关键发现

### RVW-001（P1）测试等级回退为强制集成测试，重新打开 Proposal 已关闭问题
- 证据：原 `requirements.md` 将 REQ-001 ~ REQ-004 全部标为 `Integration Required`，与 `review_proposal.md` 第 3 轮“单元测试 + 服务级验证”收敛口径冲突。
- 风险：会再次拉高实现/测试范围和工期，破坏 Proposal → Requirements 一致性。
- 建议修改：将 REQ-001 ~ REQ-004 统一改为 `Unit Only`，服务级验证保留在验收证据描述。
- 处置：已修复。

### RVW-002（P1）允许块失败后继续合并，违反“内容无损失/结果完整性”
- 证据：原 SCN-001、SCN-006、SCN-007 和 GWT-REQ-001-04 允许“坏块跳过、好块继续”。
- 风险：任何块失败都会造成静默信息丢失，与 P-DONT-01、P-DO-02 直接冲突。
- 建议修改：收敛为“任一块在重试后仍失败则整体失败，不写入部分结果”。
- 处置：已修复。

### RVW-003（P1）权限、持久化与错误码边界写偏，等价于引入隐性 API/安全变更
- 证据：原文把“admin 配置开关”写成产品内权限，把解析文本描述为“仅内存处理”，并新增 `CHUNK_001~004` 作为对外错误码。
- 风险：会误导 Design/Implementation 新增 UI/API，或在验收时与现有 `PROFILE_IMPORT_FAILED` 契约冲突。
- 建议修改：区分产品内角色与部署运维角色；明确沿用现有知识库存储；错误表改为“顶层契约 + 内部原因标签”。
- 处置：已修复。

### RVW-004（P1）字段契约和环境文件路径与仓库事实不一致
- 证据：原 REQ-002 仍用 `module_structure.name`、`system_scope` 作为 Stage2 示例；环境文件引用 `.env.backend.internal.example`，而仓库实际为 `.env.backend.internal`。
- 风险：后续实现和测试会按错误字段/路径落地，造成无效修改或伪回归。
- 建议修改：统一到 `module_name`、`system_description` 及真实文件路径。
- 处置：已修复。

## §3 覆盖率证明（REP 步骤 D）

| 维度 | 应检项数 | 已检 | 未检 | 未检说明 |
|------|---------|------|------|---------|
| 事实核实（步骤A） | 6 | 6 | 0 | - |
| 概念交叉引用（步骤B） | 6 | 6 | 0 | - |
| 审查清单项 | 8 | 8 | 0 | - |
| Proposal 覆盖项（P-DO+P-DONT+P-METRIC） | 11 | 11 | 0 | - |

## 对抗性自检

- [x] 不存在“我知道意思但文本没写清”的地方
- [x] 所有“不要/禁止”均已固化为 REQ-C + GWT 或保留在 proposal Non-goals
- [x] 所有“可选/或者/暂不”表述已收敛为单一口径
- [x] 高风险项已在本阶段收敛

## 收敛判定

- P0(open): 0
- P1(open): 0
- 结论：✅ 通过

<!-- CONSTRAINTS-CONFIRMATION-BEGIN -->
CONSTRAINTS_CONFIRMED: yes
CONFIRMED_BY: Codex
CONFIRMED_AT: 2026-03-09
<!-- CONSTRAINTS-CONFIRMATION-END -->

<!-- REVIEW-SUMMARY-BEGIN -->
REVIEW_STAGE: requirements
REVIEW_RESULT: pass
P0_OPEN: 0
P1_OPEN: 0
RVW_TOTAL: 4
REVIEWER: Codex
REVIEW_AT: 2026-03-09
VERIFICATION_COMMANDS: bash -lc 'source .aicoding/scripts/lib/review_gate_common.sh && review_gate_validate_requirements_integrity requirements docs/v2.6/requirements.md',bash -lc 'source .aicoding/scripts/lib/review_gate_common.sh && review_gate_validate_proposal_coverage proposal docs/v2.6/proposal.md requirements docs/v2.6/requirements.md',bash -lc 'source .aicoding/scripts/lib/review_gate_common.sh && review_gate_validate_constraints_confirmation review_requirements docs/v2.6/review_requirements.md requirements docs/v2.6/requirements.md'
<!-- REVIEW-SUMMARY-END -->
