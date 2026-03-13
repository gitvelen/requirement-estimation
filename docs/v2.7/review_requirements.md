# Review Report：Requirements / v2.7

> **共享章节**：见 `templates/review_skeleton.md`
> 本文件保留 Requirements 阶段特定审查内容，并记录本轮“发现问题 -> 直接修复 -> 复审”的完整闭环。

| 项 | 值 |
|---|---|
| 阶段 | Requirements |
| 版本号 | v2.7 |
| 日期 | 2026-03-13 |
| 审查范围 | `docs/v2.7/proposal.md` v0.5、`docs/v2.7/requirements.md` v0.10、`docs/v2.7/status.md` |
| 输入材料 | `docs/v2.7/proposal.md`, `docs/v2.7/requirements.md`, `docs/系统功能说明书.md`, 当前实现现状 |

## §0 审查准备（REP 步骤 A+B）
> 见 `templates/review_skeleton.md` 的“§0 审查准备”章节。
>
> 本阶段补充说明：
> - A. 事实核实同时校验 proposal 锚点、requirements 文本与当前仓库入口能力是否一致。
> - B. 关键概念交叉引用重点覆盖 Skill Runtime、6 个内置 Skill、服务治理/系统清单双导入联动、Memory 资产层、直接判定和扩展性口径。

### A. 事实核实

| # | 声明（出处） | 核实源 | 结论 |
|---|---|---|---|
| 1 | Proposal 已从旧版“5 个 Skill + 脚本式提取”升级为“6 个内置 Skill + Skill Runtime + Per-System Memory 资产层” | `proposal.md` 一句话总结、子方案五/六；`requirements.md` §1.1、REQ-005、REQ-007 | ✅ |
| 2 | 管理员导入能力已拆分为“服务治理导入”和“系统清单导入确认后初始化/补空画像”两条链路 | `proposal.md` 子方案三/四；`requirements.md` SCN-003、REQ-003、REQ-004、§6.4 | ✅ |
| 3 | 系统识别必须给出直接判定，候选信息只能作为解释而不能替代结论 | `proposal.md` P-DO-13、P-DONT-05；`requirements.md` REQ-008、REQ-C005 | ✅ |
| 4 | Memory 已从“补充日志”升级为必用资产层，要求沉淀画像更新、系统识别结论、功能点修改，并可扩展到未来评审能力 | `proposal.md` 子方案六；`requirements.md` REQ-007、REQ-010、REQ-C004 | ✅ |
| 5 | 系统清单导入只允许在首次初始化或空画像场景下写入，非空画像必须跳过且不进入 PM 建议接受流 | `proposal.md` 子方案四、P-DO-06、P-DONT-08；`requirements.md` SCN-003、REQ-004、REQ-009、REQ-C008 | ✅ |

### B. 关键概念交叉引用

| 概念 | 出现位置 | 口径一致 |
|------|---------|---------|
| 6 个内置 Skill 名称与职责 | `proposal.md` 子方案五；`requirements.md` REQ-005、REQ-006 | ✅ |
| Skill Runtime 五件套（Registry/Router/Scene Executor/Policy Gate/Memory） | `proposal.md` 子方案五；`requirements.md` §1.1、REQ-005 | ✅ |
| 服务治理导入与系统清单导入的角色/更新边界 | `proposal.md` 目标用户/范围；`requirements.md` §2、REQ-003、REQ-004、§5.1、§6.4 | ✅ |
| 直接判定口径与 `final_verdict` 要求 | `proposal.md` P-DO-13、P-DONT-05；`requirements.md` REQ-008、REQ-C005 | ✅ |
| Skill / Memory 扩展性边界 | `proposal.md` In Scope / Non-goals / P-DONT-04；`requirements.md` REQ-005、REQ-007、REQ-C004 | ✅ |
| 空画像判定与系统清单跳过规则 | `proposal.md` 子方案四、P-DONT-08；`requirements.md` 术语、REQ-004、REQ-009、REQ-C008 | ✅ |

## 审查清单

- [x] Proposal 覆盖：每个 `P-DO/P-DONT/P-METRIC` 在 §1.4 覆盖映射表中有对应 REQ-ID，且无遗漏锚点
- [x] 需求可验收：每条 REQ/REQ-C 都有可判定的 GWT，不依赖模糊描述
- [x] 场景完整：正常、异常、边界场景均已在场景明细与 REQ 中落盘
- [x] GWT 可判定：Given/When/Then 均为具体可观测行为或可比对结果
- [x] 禁止项固化：Proposal 的全部 `P-DONT` 已固化为 `REQ-C001-REQ-C008`
- [x] REQ-C 完整：每条 `REQ-C` 均至少绑定 1 条 GWT，且 review 清单完成 A/B 归类
- [x] ID 唯一性：`REQ-ID`、`GWT-ID` 经过结构校验，无重复和悬挂引用
- [x] 术语一致：Skill Runtime、6 个内置 Skill、服务治理/系统清单双导入、Memory、直接判定等关键术语保持一致

## 禁止项/不做项确认清单

> 来源覆盖：对话中出现的不要/不做/禁止/不允许/不显示/不出现/不需要 + `proposal.md` Non-goals。
> 每条已归类为 A（固化为 `REQ-C`）或 B（留在 `Non-goals`）。

| # | 禁止/不做项描述 | 归类 | 目标 | 来源 |
|---|----------------|------|------|------|
| 1 | PM 导入页不得保留历史评估报告与服务治理文档入口 | A | REQ-C001 | `proposal.md` P-DONT-01 |
| 2 | 不得保留旧 schema 字段和旧数据残留 | A | REQ-C002 | `proposal.md` P-DONT-02 |
| 3 | 自动导入或自动更新不得覆盖 PM 已确认的 `manual` 内容 | A | REQ-C003 | `proposal.md` P-DONT-03 |
| 4 | 不得把 Skill 与 Memory 设计成不可扩展结构 | A | REQ-C004 | `proposal.md` P-DONT-04 |
| 5 | 系统识别不得只返回候选列表而不做直接判定 | A | REQ-C005 | `proposal.md` P-DONT-05 |
| 6 | 不得破坏现有评估主链路和报告语义 | A | REQ-C006 | `proposal.md` P-DONT-06 |
| 7 | 不得引入新的外部依赖 | A | REQ-C007 | `proposal.md` P-DONT-07 |
| 8 | 系统清单后续月度更新或覆盖导入不得覆盖非空画像 | A | REQ-C008 | `proposal.md` P-DONT-08 |
| 9 | 不做存量画像数据迁移 | B | Non-goals | `proposal.md` Non-goals #1 |
| 10 | 不照搬 Codex/Claude 的产品 UI 形态 | B | Non-goals | `proposal.md` Non-goals #2 |
| 11 | 不把 Codex SDK 绑定为生产核心运行时 | B | Non-goals | `proposal.md` Non-goals #3 |
| 12 | 本次不直接实现需求评审/架构评审等未来 Skill | B | Non-goals | `proposal.md` Non-goals #4 |
| 13 | 不升级或更换 LLM / Embedding 模型 | B | Non-goals | `proposal.md` Non-goals #5 |
| 14 | 不整体改造现有评估算法 | B | Non-goals | `proposal.md` Non-goals #6 |
| 15 | 不改造现有用户权限体系 | B | Non-goals | `proposal.md` Non-goals #7 |
| 16 | 不提供服务治理/系统清单的手动映射界面 | B | Non-goals | `proposal.md` Non-goals #8 |

<!-- CONSTRAINTS-CHECKLIST-BEGIN -->
| ITEM | CLASS | TARGET | SOURCE |
|------|-------|--------|--------|
| C-001 | A | REQ-C001 | proposal.md P-DONT-01; requirements.md REQ-C001 |
| C-002 | A | REQ-C002 | proposal.md P-DONT-02; requirements.md REQ-C002 |
| C-003 | A | REQ-C003 | proposal.md P-DONT-03; requirements.md REQ-C003 |
| C-004 | A | REQ-C004 | proposal.md P-DONT-04; requirements.md REQ-C004 |
| C-005 | A | REQ-C005 | proposal.md P-DONT-05; requirements.md REQ-C005 |
| C-006 | A | REQ-C006 | proposal.md P-DONT-06; requirements.md REQ-C006 |
| C-007 | A | REQ-C007 | proposal.md P-DONT-07; requirements.md REQ-C007 |
| C-008 | A | REQ-C008 | proposal.md P-DONT-08; requirements.md REQ-C008 |
| C-009 | B | Non-goals | proposal.md Non-goals #1 |
| C-010 | B | Non-goals | proposal.md Non-goals #2 |
| C-011 | B | Non-goals | proposal.md Non-goals #3 |
| C-012 | B | Non-goals | proposal.md Non-goals #4 |
| C-013 | B | Non-goals | proposal.md Non-goals #5 |
| C-014 | B | Non-goals | proposal.md Non-goals #6 |
| C-015 | B | Non-goals | proposal.md Non-goals #7 |
| C-016 | B | Non-goals | proposal.md Non-goals #8 |
<!-- CONSTRAINTS-CHECKLIST-END -->

## 需求覆盖判定

| REQ-ID | GWT 数量 | GWT 可判定 | 备注 |
|--------|---------|-----------|------|
| REQ-001 | 3 | ✅ | PM 导入页只保留 3 类文档，并对旧类型明确拒绝 |
| REQ-002 | 3 | ✅ | 5 域 canonical 结构、D4 子结构、前端适配均已覆盖 |
| REQ-003 | 3 | ✅ | 服务治理导入、统计结果、模板异常三类路径均覆盖 |
| REQ-004 | 3 | ✅ | 系统清单 preview/confirm、首次初始化补空与非空画像跳过均覆盖 |
| REQ-005 | 5 | ✅ | Runtime 五件套、6 个内置 Skill、场景串联和未来 Skill 启停均覆盖 |
| REQ-006 | 3 | ✅ | 需求文档、治理模板、系统清单模板多格式兼容均覆盖 |
| REQ-007 | 4 | ✅ | 三类必选 Memory + 未来类型扩展均覆盖 |
| REQ-008 | 4 | ✅ | 直接判定、歧义处理、无命中处理、结果结构均覆盖 |
| REQ-009 | 5 | ✅ | 服务治理 `auto_apply`、系统清单空画像 `auto_apply/reject` 与 manual 保护均覆盖 |
| REQ-010 | 3 | ✅ | 拆解前读取 Memory、低风险局部自动化、高风险建议化均覆盖 |
| REQ-011 | 4 | ✅ | Skill 失败、preview 失败、Memory 失败、半成品防脏写均覆盖 |
| REQ-012 | 3 | ✅ | 清理成功、清零核验、异常失败均覆盖 |
| REQ-101 | 2 | ✅ | 字段总数与前后端 canonical 一致性均覆盖 |
| REQ-102 | 2 | ✅ | 成功率目标与分母口径均覆盖 |
| REQ-103 | 2 | ✅ | 6 个内置 Skill 测试与核心场景路由矩阵均覆盖 |
| REQ-104 | 2 | ✅ | 三类 Memory 覆盖率与按系统查询均覆盖 |
| REQ-105 | 2 | ✅ | 两类旧数据的核验均覆盖 |
| REQ-C001 | 2 | ✅ | 页面不可见和旧入口拒绝均覆盖 |
| REQ-C002 | 2 | ✅ | 旧字段不可见与残留计数清零均覆盖 |
| REQ-C003 | 2 | ✅ | manual 不被覆盖及跳过提示均覆盖 |
| REQ-C004 | 2 | ✅ | 未来 Skill 和未来 Memory 类型扩展均覆盖 |
| REQ-C005 | 1 | ✅ | `final_verdict` 必填口径已固化 |
| REQ-C006 | 2 | ✅ | 主链路可用性和失败隔离均覆盖 |
| REQ-C007 | 1 | ✅ | 外部依赖差异可判定 |
| REQ-C008 | 2 | ✅ | 非空画像禁更与空画像判定口径均覆盖 |

## 高风险语义审查（必做）

- [x] `REQ-C` 禁止项：每条都已落到可验收 GWT，而非仅在正文中提及
- [x] “直接判定 / 候选解释 / 场景化策略 / manual 优先 / 空画像判定”表述已收敛为单一口径
- [x] 角色差异：manager、admin、expert 的可见/可写/可导入边界已在权限矩阵与接口契约中对齐
- [x] 数据边界：多格式输入、preview/confirm、空画像判定、Memory 扩展、部分成功与补偿态等边界均有明确行为定义

## 关键发现

### RVW-001（P1）Proposal 与 Requirements 仍沿用旧版 5 Skill 口径，且把第 1 个 Skill 错写成单纯 ESB 导入
- **证据**：旧版 `proposal.md` 和 `requirements.md` 仍把范围写成 5 个 Skill，且没有把管理员服务治理导入和系统清单导入的画像联动拆开。
- **风险**：后续设计和实现会继续围绕错误的 Skill 边界展开，导致范围缺失和运行能力偏差。
- **建议修改**：将范围升级为 6 个内置 Skill，并分别固化 `service_governance_skill` 和 `system_catalog_skill`。
- **状态**：已修复。

### RVW-002（P1）旧版需求把 Skill 当作提取脚本集合，没有把 Runtime 能力写清
- **证据**：旧版需求聚焦“每类文档一个 Skill”，缺少 Registry、Router、Scene Executor、Policy Gate 和 Memory Reader/Writer 的统一口径。
- **风险**：实现很容易退化成几个独立脚本和分散逻辑，无法达到“像 Codex 一样按目标丝滑调用 Skill”的目标。
- **建议修改**：在 Proposal 和 Requirements 中把 Runtime 作为一等能力落盘，并对场景串联和未来扩展给出可验收定义。
- **状态**：已修复。

### RVW-003（P1）旧版需求没有 Per-System Memory 模型，也没有定义其在系统识别和功能点拆解中的实际用法
- **证据**：旧版文档缺少系统级 Memory 数据模型、写入范围、读取方式，以及在系统识别和功能点拆解中的落地策略。
- **风险**：Memory 会退化成普通日志，无法成为系统画像完善、系统识别和功能点拆解的资产层。
- **建议修改**：新增 `profile_update`、`identification_decision`、`function_point_adjustment` 三类 Memory，并明确 direct decision / retrieval context 两类使用方式，以及未来扩展要求。
- **状态**：已修复。

### RVW-004（P1）旧版 review/status 仍宣称 Requirements 已通过，和当前用户确认的新范围冲突
- **证据**：`status.md` 仍保留第 2 轮已通过的旧描述，`review_requirements.md` 也仍以旧范围给出通过结论。
- **风险**：阶段推进会基于过期结论误判，造成未完成范围直接进入 Design。
- **建议修改**：重开 Requirements 第 3 轮复审，同步 proposal、requirements、review、status 四份文档。
- **状态**：已修复。

### RVW-005（P1）系统清单导入联动在 Requirements 内部曾混用“所有系统画像”和“所有命中的系统画像”两套口径
- **证据**：第 4 轮复审前，`P-DO-06` 映射行、`REQ-004` 目标描述与 Proposal v0.4 存在口径漂移。
- **风险**：实现范围会在“全量重刷全部画像”与“仅更新命中画像”之间摇摆，影响验收和性能预算。
- **建议修改**：统一 Proposal / Requirements / Status 对系统清单联动范围的口径。
- **状态**：已修复。

### RVW-006（P2）Requirements 审查产物曾引用过期的 Proposal / Requirements 版本元信息
- **证据**：第 4 轮复审前，`requirements.md` 顶部 `关联提案` 与 `review_requirements.md` 审查范围仍停留在旧版本。
- **风险**：人工复核无法准确回答“本轮需求是基于哪版提案审的”，追溯链不完整。
- **建议修改**：同步 Requirements、Review、Status 的版本与轮次留痕。
- **状态**：已修复。

### RVW-007（P1）旧版需求仍把系统清单导入定义为 confirm 后批量更新命中画像，缺少“首次初始化/空画像补写/非空跳过”业务规则
- **证据**：用户已明确：系统清单每月都会更新；首次初始化才允许批量更新且无须 PM 接受建议；若系统清单已存在，后续更新或覆盖导入时，只有 `profile_data` 下 D1-D5 canonical 字段全部为空值/空数组/空对象的画像才允许更新，且忽略 `field_sources`、`ai_suggestions`、Memory 记录。
- **风险**：如果继续沿用旧版 `REQ-004/REQ-009` 的 `draft_apply/suggestion_only` 口径，系统会把月度系统清单更新误实现为覆盖式画像回写或噪声建议流。
- **建议修改**：重写 `SCN-003`、`REQ-004`、`REQ-009`，并新增 `REQ-C008` 固化“系统清单不得覆盖非空画像”的禁止项。
- **状态**：已修复。

## §3 覆盖率证明（REP 步骤 D）
> 见 `templates/review_skeleton.md` 的“§3 覆盖率证明”章节。

| 维度 | 应检项数 | 已检 | 未检 | 未检说明 |
|------|---------|------|------|---------|
| 事实核实（步骤A） | 5 | 5 | 0 | - |
| 概念交叉引用（步骤B） | 6 | 6 | 0 | - |
| 审查清单项 | 8 | 8 | 0 | - |
| Proposal 覆盖项（P-DO + P-DONT + P-METRIC） | 30 | 30 | 0 | - |
| 禁止项 / 不做项清单 | 16 | 16 | 0 | - |

## 对抗性自检
> 通用检查项见 `templates/review_skeleton.md`。

- [x] 已检查是否存在“我知道意思但文本没写清”的位置，重点排除了 Skill Runtime 与脚本集合的口径混淆
- [x] 已检查所有“不要/禁止/不做”是否都落到了 `REQ-C` 或 `Non-goals`
- [x] 已检查所有“场景化策略 / 直接判定 / 扩展性 / 空画像判定”表述是否已收敛为单一口径
- [x] 已检查高风险项是否仍被留到 Design/Implementation 再决定，结论为未留存未决项

## 收敛判定
> 见 `templates/review_skeleton.md` 的“收敛判定”章节。

- P0(open): 0
- P1(open): 0
- P2(open): 0
- 结论：✅ 通过

<!-- CONSTRAINTS-CONFIRMATION-BEGIN -->
CONSTRAINTS_CONFIRMED: yes
CONFIRMED_BY: Codex
CONFIRMED_AT: 2026-03-13
<!-- CONSTRAINTS-CONFIRMATION-END -->

<!-- REVIEW-SUMMARY-BEGIN -->
REVIEW_STAGE: requirements
REVIEW_RESULT: pass
P0_OPEN: 0
P1_OPEN: 0
RVW_TOTAL: 7
REVIEWER: Codex
REVIEW_AT: 2026-03-13
VERIFICATION_COMMANDS: bash -lc 'source .aicoding/scripts/lib/review_gate_common.sh && review_gate_validate_requirements_integrity docs/v2.7/requirements.md docs/v2.7/requirements.md; echo EXIT:$?'; bash -lc 'source .aicoding/scripts/lib/review_gate_common.sh && review_gate_validate_proposal_coverage docs/v2.7/proposal.md docs/v2.7/proposal.md docs/v2.7/requirements.md docs/v2.7/requirements.md; echo EXIT:$?'; bash -lc 'source .aicoding/scripts/lib/review_gate_common.sh && review_gate_validate_constraints_confirmation docs/v2.7/review_requirements.md docs/v2.7/review_requirements.md docs/v2.7/requirements.md docs/v2.7/requirements.md docs/v2.7/proposal.md docs/v2.7/proposal.md; echo EXIT:$?'
<!-- REVIEW-SUMMARY-END -->

---

## 复审（第 6 轮，2026-03-13）

### 复审范围
- 用户新增“系统清单月度更新不得覆盖非空画像”的业务规则后，Requirements 是否已同步
- Proposal / Requirements / Status 对“首次初始化、空画像判定、非空跳过、不进入 PM 建议流”的口径是否一致

### 复审证据
1. `rg -n 'v0\\.5|v0\\.10|首次初始化|空画像|P-DONT-08|REQ-C008|profile_data|field_sources|ai_suggestions|system_catalog|profile_not_blank' docs/v2.7/proposal.md docs/v2.7/requirements.md docs/v2.7/review_requirements.md docs/v2.7/status.md`
2. `bash -lc 'source .aicoding/scripts/lib/review_gate_common.sh && review_gate_validate_requirements_integrity docs/v2.7/requirements.md docs/v2.7/requirements.md; echo EXIT:$?'`
3. `bash -lc 'source .aicoding/scripts/lib/review_gate_common.sh && review_gate_validate_proposal_coverage docs/v2.7/proposal.md docs/v2.7/proposal.md docs/v2.7/requirements.md docs/v2.7/requirements.md; echo EXIT:$?'`
4. `bash -lc 'source .aicoding/scripts/lib/review_gate_common.sh && review_gate_validate_constraints_confirmation docs/v2.7/review_requirements.md docs/v2.7/review_requirements.md docs/v2.7/requirements.md docs/v2.7/requirements.md docs/v2.7/proposal.md docs/v2.7/proposal.md; echo EXIT:$?'`

### 修复影响面扫描（REP 步骤 E）
- 已重新全文检索 `首次初始化|空画像|P-DONT-08|REQ-C008|profile_data|field_sources|ai_suggestions|system_catalog|profile_not_blank`
- 本轮修复落在 `proposal.md`、`requirements.md`、`review_proposal.md`、`review_requirements.md`、`status.md`
- 本轮修复改变了 Requirements 阶段对系统清单导入的业务规则，因此同步回写 Proposal 追溯锚点；当前全局阶段仍保持 `Requirements`

### 修复内容
- 将 `proposal.md` 升级为 `v0.5`，把系统清单导入统一为“首次初始化或空画像时初始化写入，非空画像跳过”，并新增 `P-DONT-08`
- 将 `requirements.md` 升级为 `v0.10`，重写 `SCN-003`、`REQ-004`、`REQ-009`，新增空画像术语和 `REQ-C008`
- 将 `status.md` 更新为 `_review_round: 6`，同步本轮业务规则收敛摘要

### 复审结果
- 原 RVW-007：已关闭
  - **证据**：
    - `requirements.md` 已把系统清单场景收敛为“首次初始化或空画像时 `auto_apply`，非空画像 `reject/skip`”
    - `REQ-C008` 已将“系统清单不得覆盖非空画像”固化为禁止项，并明确空画像判定仅检查 `profile_data` 下 D1-D5 canonical 字段
    - `proposal.md` v0.5 与 `status.md` 摘要已同步同一口径

### 结论（第 6 轮）
- P0(open)=0
- P1(open)=0
- P2(open)=0

**复审结论：Requirements 阶段问题继续保持收敛。新增业务规则已完成“发现问题 -> 修复文档 -> 复审验证”的闭环；当前保持 `wait_confirm`，等待人工确认是否进入 Design。**

<!-- CONSTRAINTS-CONFIRMATION-BEGIN -->
CONSTRAINTS_CONFIRMED: yes
CONFIRMED_BY: Codex
CONFIRMED_AT: 2026-03-13
<!-- CONSTRAINTS-CONFIRMATION-END -->

<!-- REVIEW-SUMMARY-BEGIN -->
REVIEW_STAGE: requirements
REVIEW_RESULT: pass
P0_OPEN: 0
P1_OPEN: 0
RVW_TOTAL: 7
REVIEWER: Codex
REVIEW_AT: 2026-03-13
VERIFICATION_COMMANDS: rg -n 'v0\.5|v0\.10|首次初始化|空画像|P-DONT-08|REQ-C008|profile_data|field_sources|ai_suggestions|system_catalog|profile_not_blank' docs/v2.7/proposal.md docs/v2.7/requirements.md docs/v2.7/review_requirements.md docs/v2.7/status.md; bash -lc 'source .aicoding/scripts/lib/review_gate_common.sh && review_gate_validate_requirements_integrity docs/v2.7/requirements.md docs/v2.7/requirements.md; echo EXIT:$?'; bash -lc 'source .aicoding/scripts/lib/review_gate_common.sh && review_gate_validate_proposal_coverage docs/v2.7/proposal.md docs/v2.7/proposal.md docs/v2.7/requirements.md docs/v2.7/requirements.md; echo EXIT:$?'; bash -lc 'source .aicoding/scripts/lib/review_gate_common.sh && review_gate_validate_constraints_confirmation docs/v2.7/review_requirements.md docs/v2.7/review_requirements.md docs/v2.7/requirements.md docs/v2.7/requirements.md docs/v2.7/proposal.md docs/v2.7/proposal.md; echo EXIT:$?'
<!-- REVIEW-SUMMARY-END -->

---

## 证据清单

### 1. Requirements 结构完整性校验

**命令：**
```bash
bash -lc 'source .aicoding/scripts/lib/review_gate_common.sh && review_gate_validate_requirements_integrity docs/v2.7/requirements.md docs/v2.7/requirements.md; echo EXIT:$?'
```

**输出：**
```text
EXIT:0
```

**定位：**
- `docs/v2.7/requirements.md`

### 2. Proposal -> Requirements 覆盖校验

**命令：**
```bash
bash -lc 'source .aicoding/scripts/lib/review_gate_common.sh && review_gate_validate_proposal_coverage docs/v2.7/proposal.md docs/v2.7/proposal.md docs/v2.7/requirements.md docs/v2.7/requirements.md; echo EXIT:$?'
```

**输出：**
```text
EXIT:0
```

**定位：**
- `docs/v2.7/proposal.md`
- `docs/v2.7/requirements.md`

### 3. Skill Runtime、系统清单初始化规则与 Memory 关键口径核验

**命令：**
```bash
rg -n "system_catalog_skill|首次初始化|空画像|profile_not_blank|final_verdict|function_point_adjustment" docs/v2.7/requirements.md docs/v2.7/proposal.md | sed -n '1,120p'
```

**输出：**
```text
docs/v2.7/requirements.md:22:- 在系统清单批量导入 confirm 后，自动触发 `system_catalog_skill`，仅对系统首次初始化或画像全空的命中系统执行画像初始化/补空。
docs/v2.7/requirements.md:82:- **空画像（Blank Profile）**：仅当 `profile_data` 下 D1-D5 canonical 字段全部为空值、空数组或空对象时，判定为空画像；`field_sources`、`ai_suggestions`、Memory 记录不参与判定。
docs/v2.7/requirements.md:152:- **Identification Result**：系统识别结果，至少含 `final_verdict`、`selected_systems`、`candidate_systems`、`questions`。
docs/v2.7/requirements.md:585:4. `system_catalog_skill` 解析高价值字段，并按空画像规则筛选可初始化目标。
docs/v2.7/requirements.md:605:- 命中非空画像不属于失败，但必须返回明确跳过原因（如 `profile_not_blank`）。
docs/v2.7/proposal.md:127:  2. `system_catalog_skill`：管理员系统清单导入 -> 初始化空画像或跳过非空画像
```

**定位：**
- `docs/v2.7/requirements.md:22`
- `docs/v2.7/requirements.md:82`
- `docs/v2.7/requirements.md:152`
- `docs/v2.7/requirements.md:585`
- `docs/v2.7/requirements.md:605`
- `docs/v2.7/proposal.md:127`

### 4. 机器可读约束确认校验

**命令：**
```bash
bash -lc 'source .aicoding/scripts/lib/review_gate_common.sh && review_gate_validate_constraints_confirmation docs/v2.7/review_requirements.md docs/v2.7/review_requirements.md docs/v2.7/requirements.md docs/v2.7/requirements.md docs/v2.7/proposal.md docs/v2.7/proposal.md; echo EXIT:$?'
```

**输出：**
```text
EXIT:0
```

**定位：**
- `docs/v2.7/review_requirements.md`
- `docs/v2.7/requirements.md`
- `docs/v2.7/proposal.md`

### 5. 状态文件同步核验

**命令：**
```bash
rg -n "^_run_status:|^_review_round:|^_phase:|v0\\.5|v0\\.10|首次初始化|Memory 写入覆盖率" docs/v2.7/status.md
```

**输出：**
```text
5:_run_status: wait_confirm
8:_review_round: 6
9:_phase: Requirements
30:- 新增系统清单导入后的画像联动能力，但已收敛为“仅首次初始化或空画像时初始化写入，非空画像跳过且不进入 PM 建议流”
32:- `proposal.md` 已同步到 v0.5，`requirements.md` 已升级到 v0.10，`review_requirements.md` 已完成第 6 轮复审并收敛；当前保持 `_phase: Requirements`，等待人工确认是否进入 Design
41:| M5 | Memory 写入覆盖率 | 0 | 系统画像更新、系统识别结论、AI 评估后功能点修改三类范围内动作的 Memory 写入覆盖率 = 100% | 测试阶段 | Memory 日志 |
```

**定位：**
- `docs/v2.7/status.md:5`
- `docs/v2.7/status.md:8`
- `docs/v2.7/status.md:9`
- `docs/v2.7/status.md:30`
- `docs/v2.7/status.md:32`
- `docs/v2.7/status.md:41`

## 多轮审查追加格式
> 见 `templates/review_skeleton.md` 的“多轮审查追加格式”章节。

---

## 复审（第 4 轮，2026-03-13）

### 复审范围
- Proposal 升级到 v0.4 后，Requirements 阶段文档与审查产物是否已同步最新版本引用
- `P-DO-06`、`REQ-004` 和相关摘要对“系统清单导入联动”范围的口径是否仍然一致

### 复审证据
1. `rg -n 'v0\\.3|v0\\.4|所有系统画像|所有命中的系统画像|P-DO-06|关联提案' docs/v2.7/requirements.md docs/v2.7/review_requirements.md docs/v2.7/proposal.md docs/v2.7/status.md`
2. `nl -ba docs/v2.7/requirements.md | sed -n '1,120p'`
3. `nl -ba docs/v2.7/requirements.md | sed -n '567,600p'`

### 复审结果
- 新增 RVW-005（P1）系统清单导入联动在 Requirements 内部仍混用“所有系统画像”和“所有命中的系统画像”两套口径
  - **证据**：
    - `proposal.md` v0.4 已统一为“批量更新所有命中的系统画像”
    - `requirements.md` 的术语口径已写“所有命中的系统画像”
    - 但覆盖映射表 `P-DO-06` 和 `REQ-004` 目标/价值仍写“所有系统画像”
  - **风险**：
    - `REQ-004` 的实现范围会在“只更新命中画像”和“重刷全部画像”之间摇摆
    - 后续 Design/Planning/Implementation 对性能预算、数据影响面和验收样本的理解会失真
  - **建议修改**：
    - 将 `requirements.md` 的 `关联提案`、`P-DO-06` 映射行、`REQ-004` 目标描述统一收敛到 Proposal v0.4 当前口径
  - **验证方式**：
    - `rg -n '所有系统画像|所有命中的系统画像|P-DO-06' docs/v2.7/requirements.md docs/v2.7/proposal.md`
- 新增 RVW-006（P2）Requirements 审查产物仍引用 `proposal.md` v0.3，追溯元信息已过时
  - **证据**：
    - `requirements.md` 顶部 `关联提案` 仍指向 `proposal.md` v0.3
    - `review_requirements.md` 审查范围也仍写 `proposal.md` v0.3 / `requirements.md` v0.8
    - 当前 Proposal 已升级到 v0.4，Requirements 将随本轮修正升级到 v0.9
  - **风险**：
    - Review 追溯链不能准确回答“本轮需求是基于哪版提案审的”
    - 后续人工复核容易误判已覆盖范围
  - **建议修改**：
    - 同步 Requirements 与 Review 的版本元信息，并在 `status.md` 回填最新 Requirements 轮次与版本
  - **验证方式**：
    - `rg -n 'v0\\.3|v0\\.4|v0\\.8|v0\\.9|关联提案|审查范围' docs/v2.7/requirements.md docs/v2.7/review_requirements.md docs/v2.7/status.md`

### 结论（第 4 轮）
- P0(open)=0
- P1(open)=1
- P2(open)=1

**复审结论：❌ 当前不通过。请先同步 Requirements 口径与版本留痕，再继续复审。**

---

## 复审（第 5 轮，2026-03-13）

### 复审范围
- 第 4 轮新增 RVW-005：系统清单导入联动范围口径冲突
- 第 4 轮新增 RVW-006：Proposal / Requirements / Review / Status 版本与轮次留痕漂移

### 复审证据
1. `rg -n 'v0\\.3|v0\\.4|v0\\.8|v0\\.9|所有系统画像|所有命中的系统画像|P-DO-06|关联提案|审查范围' docs/v2.7/requirements.md docs/v2.7/review_requirements.md docs/v2.7/proposal.md docs/v2.7/status.md`
2. `bash -lc 'source .aicoding/scripts/lib/review_gate_common.sh && review_gate_validate_requirements_integrity docs/v2.7/requirements.md docs/v2.7/requirements.md; echo EXIT:$?'`
3. `bash -lc 'source .aicoding/scripts/lib/review_gate_common.sh && review_gate_validate_proposal_coverage docs/v2.7/proposal.md docs/v2.7/proposal.md docs/v2.7/requirements.md docs/v2.7/requirements.md; echo EXIT:$?'`
4. `bash -lc 'source .aicoding/scripts/lib/review_gate_common.sh && review_gate_validate_constraints_confirmation docs/v2.7/review_requirements.md docs/v2.7/review_requirements.md docs/v2.7/requirements.md docs/v2.7/requirements.md docs/v2.7/proposal.md docs/v2.7/proposal.md; echo EXIT:$?'`

### 修复影响面扫描（REP 步骤 E）
- 已重新全文检索 `v0.3|v0.4|v0.8|v0.9|所有系统画像|所有命中的系统画像|P-DO-06|关联提案|审查范围`
- 本轮修复仅落在 Requirements 阶段产物：`requirements.md`、`review_requirements.md`、`status.md`
- 未改动 Proposal 范围、业务规则、GWT 逻辑和接口契约，只同步已确认口径与文档追溯元信息

### 修复内容
- 将 `requirements.md` 升级为 `v0.9`，并把 `关联提案` 同步到 `proposal.md` v0.4
- 将 `requirements.md` 中 `P-DO-06` 映射行和 `REQ-004` 目标描述统一为“所有命中的系统画像”
- 将 `review_requirements.md` 的审查范围同步到 `proposal.md` v0.4 / `requirements.md` v0.9
- 将 `status.md` 的 `_review_round`、摘要和备注同步到 Requirements 第 5 轮复审结果

### 复审结果
- 原 RVW-005：已关闭
  - **证据**：
    - `requirements.md` 的 `P-DO-06` 映射和 `REQ-004` 目标/价值已统一为“所有命中的系统画像”
    - 全文检索后，Requirements 阶段产物中不再保留旧的“所有系统画像”口径
- 原 RVW-006：已关闭
  - **证据**：
    - `requirements.md` 已升级为 `v0.9`，`关联提案` 指向 `proposal.md` v0.4
    - `review_requirements.md` 审查范围已同步最新版本
    - `status.md` 已回填 `_review_round: 5`，并明确第 5 轮 Requirements 复审已收敛

### 结论（第 5 轮）
- P0(open)=0
- P1(open)=0
- P2(open)=0

**复审结论：Requirements 阶段问题已收敛，当前可继续保持 `wait_confirm`，等待人工确认是否进入 Design。**

<!-- CONSTRAINTS-CONFIRMATION-BEGIN -->
CONSTRAINTS_CONFIRMED: yes
CONFIRMED_BY: Codex
CONFIRMED_AT: 2026-03-13
<!-- CONSTRAINTS-CONFIRMATION-END -->

<!-- REVIEW-SUMMARY-BEGIN -->
REVIEW_STAGE: requirements
REVIEW_RESULT: pass
P0_OPEN: 0
P1_OPEN: 0
RVW_TOTAL: 6
REVIEWER: Codex
REVIEW_AT: 2026-03-13
VERIFICATION_COMMANDS: rg -n 'v0\.3|v0\.4|v0\.8|v0\.9|所有系统画像|所有命中的系统画像|P-DO-06|关联提案|审查范围' docs/v2.7/requirements.md docs/v2.7/review_requirements.md docs/v2.7/proposal.md docs/v2.7/status.md; bash -lc 'source .aicoding/scripts/lib/review_gate_common.sh && review_gate_validate_requirements_integrity docs/v2.7/requirements.md docs/v2.7/requirements.md; echo EXIT:$?'; bash -lc 'source .aicoding/scripts/lib/review_gate_common.sh && review_gate_validate_proposal_coverage docs/v2.7/proposal.md docs/v2.7/proposal.md docs/v2.7/requirements.md docs/v2.7/requirements.md; echo EXIT:$?'; bash -lc 'source .aicoding/scripts/lib/review_gate_common.sh && review_gate_validate_constraints_confirmation docs/v2.7/review_requirements.md docs/v2.7/review_requirements.md docs/v2.7/requirements.md docs/v2.7/requirements.md docs/v2.7/proposal.md docs/v2.7/proposal.md; echo EXIT:$?'
<!-- REVIEW-SUMMARY-END -->
