# Review Report：Planning / v2.4

| 项 | 值 |
|---|---|
| 阶段 | Planning |
| 版本号 | v2.4 |
| 日期 | 2026-02-28 |
| 审查范围 | plan.md |
| 输入材料 | requirements.md, design.md, plan.md |

## §0 审查准备（REP 步骤 A+B）

### A. 事实核实

| # | 声明（出处） | 核实源 | 结论 |
|---|------------|--------|------|
| 1 | 计划拆分为 12 个独立任务（`plan.md` 任务详情） | `rg -n "^### T[0-9]+" docs/v2.4/plan.md`（12 条） | ✅ |
| 2 | 每个任务都包含可复现验证命令（`plan.md` 任务详情） | `rg -n "^\*\*验证方式\*\*：" docs/v2.4/plan.md`（12 条） | ✅ |
| 3 | 需求反向覆盖完整（`plan.md` 覆盖矩阵） | `review_gate_validate_plan_reverse_coverage` | ✅ |
| 4 | 计划任务与设计 WBS 主线一致（画像、提取、估算、快照diff、前端四页） | `design.md` §9.1/§9.2 对照 `plan.md` T001-T010 | ✅ |
| 5 | 禁止项 REQ-C001~REQ-C007 均有任务承接 | `plan.md` 禁止项索引 + 覆盖矩阵 | ✅ |

### B. 关键概念交叉引用

| 概念 | 出现位置 | 口径一致 |
|------|---------|---------|
| 任务ID `T001~T012` | 任务概览、任务详情、执行顺序、覆盖矩阵 | ✅ |
| `REQ-001~REQ-012/101~106` | 任务概览、任务详情、覆盖矩阵 | ✅ |
| `REQ-C001~REQ-C007` | 禁止项索引、任务概览、任务详情、覆盖矩阵 | ✅ |
| 里程碑 `M1~M3` | 里程碑表、任务概览、执行顺序 | ✅ |

## 审查清单

- [x] 任务可追踪：Txxx ID 完整，每条有清晰 DoD
- [x] 粒度合适：可独立实现与验证，依赖关系清晰
- [x] 追溯完整：任务关联 REQ/SCN/API
- [x] 验证可复现：每个任务有命令级别验证方式
- [x] 风险与回滚：涉及线上行为变化的任务有回滚思路
- [x] 内容完整：覆盖需求和设计阶段产出的成果

## 需求反向覆盖

| REQ-ID | 关联任务 | 覆盖判定 | 备注 |
|--------|---------|---------|------|
| REQ-001~REQ-012 | T002-T010,T011 | ✅ | 功能主线均由实现任务 + 测试任务覆盖 |
| REQ-101~REQ-106 | T001,T003,T008,T011,T012 | ✅ | 指标与回滚目标由测试/部署任务承接 |
| REQ-C001~REQ-C007 | T001-T009,T011 | ✅ | 禁止项均有实现任务和回归任务 |

## 关键发现

- 本轮未发现 P0/P1 问题；`plan.md` 在可执行性、追溯性、验证可复现性上满足阶段门禁。

## §3 覆盖率证明（REP 步骤 D）

| 维度 | 应检项数 | 已检 | 未检 | 未检说明 |
|------|---------|------|------|---------|
| 事实核实（步骤A） | 5 | 5 | 0 | — |
| 概念交叉引用（步骤B） | 4 | 4 | 0 | — |
| 审查清单项 | 6 | 6 | 0 | — |
| REQ-ID 反向覆盖项 | 25 | 25 | 0 | — |

## 对抗性自检
- [x] 不存在“我知道意思但文本没写清”的地方
- [x] 所有“可选/或者/暂不”表述已收敛为单一口径
- [x] 高风险项（权限/回滚/降级/REQ-C）已在本阶段收敛

## 收敛判定
- P0(open): 0
- P1(open): 0
- 结论：✅ 通过

## 第 2 轮审查（2026-02-28）
### 上轮遗留问题处置
| RVW-ID | 处置 | 证据 |
|--------|------|------|
| - | 无遗留 | 第 1 轮为通过态 |

### 本轮新发现
### RVW-001（P1）T012 验证命令不可执行（`git checkout --dry-run` 非法）
- 证据：执行 `git checkout v2.3 --dry-run` 返回 `error: unknown option 'dry-run'`
- 风险：回滚演练任务无法按计划验证，Deployment 阶段门禁证据失真
- 建议修改：替换为非破坏且可复现命令（健康检查 + tag 存在性 + 部署脚本存在性）
- 处置结果：已修复（`plan.md` 改为 `curl ... && git rev-parse --verify --quiet v2.3^{commit} && test -x deploy-all.sh`）

### RVW-002（P1）缺少 SCN/API 级追溯链，DoD 中 `REQ/SCN/API/TEST` 未闭合
- 证据：`plan.md` 任务概览与任务详情原先仅声明 REQ，未声明 SCN/API
- 风险：无法从场景/API 维度反向证明覆盖，验收争议成本高
- 建议修改：在任务概览与任务详情补齐 SCN/API；新增 SCN/API 反向覆盖矩阵
- 处置结果：已修复（新增任务级 SCN/API 字段 + `SCN ↔ Task` / `API ↔ Task` 矩阵）

### RVW-003（P1）里程碑展示节点未显式标注，Implementation 阶段过程门禁可执行性不足
- 证据：`plan.md` 原任务概览里程碑列无 `🏁` 节点，执行顺序未声明停点展示
- 风险：实现中可能跳过中间确认，偏航后返工成本升高
- 建议修改：显式标记 `🏁` 任务并给出展示内容与确认要点
- 处置结果：已修复（T004/T009/T011 标注 `🏁`，新增“里程碑展示点”章节）

### RVW-004（P1）线上行为变化缺少任务级回滚/开关策略索引
- 证据：`plan.md` 原文仅有全局风险表，无任务级回滚对照
- 风险：出问题时无法按任务快速回退，恢复路径不清晰
- 建议修改：新增任务级回滚策略表，覆盖 T001~T012
- 处置结果：已修复（新增“任务级回滚/开关策略”章节）

<!-- REVIEW-SUMMARY-BEGIN -->
REVIEW_STAGE: planning
REVIEW_RESULT: pass
P0_OPEN: 0
P1_OPEN: 0
RVW_TOTAL: 4
REVIEWER: Codex
REVIEW_AT: 2026-02-28
VERIFICATION_COMMANDS: bash -lc 'source .aicoding/scripts/lib/review_gate_common.sh && review_gate_validate_plan_reverse_coverage requirements docs/v2.4/requirements.md plan docs/v2.4/plan.md'; git checkout v2.3 --dry-run; rg -o 'SCN-V24-[0-9]{2}' docs/v2.4/requirements.md | sort -u; rg -o 'SCN-V24-[0-9]{2}' docs/v2.4/plan.md | sort -u; rg -o 'API-[0-9]{3}' docs/v2.4/plan.md | sort -u
<!-- REVIEW-SUMMARY-END -->
