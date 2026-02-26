# Proposal 阶段审查（v2.3）

## 审查信息
- 审查者：Codex
- 审查时间：2026-02-26
- 审查口径：full（以 `docs/v2.3/status.md` 为单一真相源）
- 适用规则：
  - `.aicoding/phases/01-proposal.md`
  - `docs/lessons_learned.md`（快速索引 R1-R7）

## 审查证据
1. `nl -ba docs/v2.3/proposal.md | sed -n '1,240p'`
2. `nl -ba docs/v2.3/status.md | sed -n '1,220p'`
3. `rg -n "影响面" docs/v2.3/proposal.md docs/v2.3/status.md -S`
4. `rg -n "复杂度|任务成功率|P-METRIC|目标与成功指标" docs/v2.3/proposal.md docs/v2.3/status.md -S`

## 发现的问题（按严重度）

### P1（Major）
1. 提案未覆盖 `status.md` 已声明的“变更影响面分析”能力
   - 位置：`docs/v2.3/status.md:28`；`docs/v2.3/proposal.md:53-73`
   - 现状：`status.md` 变更摘要包含“变更影响面分析”，但 `proposal.md` 的方案与 In Scope 未出现该能力（关键词核验：`proposal.md` 无“影响面”命中）。
   - 风险：违背 R1“提案需覆盖已确认决策点”，后续 Requirements 可能遗漏该能力，造成追溯链断裂。
   - 建议：在 `proposal.md` 的“方案概述 + In Scope + 验收锚点（P-DO/P-METRIC）”补齐“变更影响面分析”。

2. 提案成功指标与 `status.md` 口径不一致，存在验收降级
   - 位置：`docs/v2.3/status.md:37-38`；`docs/v2.3/proposal.md:33-41`；`docs/v2.3/proposal.md:99-103`
   - 现状：
     - `status.md` M5 定义了“复杂度覆盖率 >=95%”，提案目标与 P-METRIC 未纳入该指标。
     - `status.md` M6 定义了“GitLab 路径 3/3 且任务成功率 >=99%”，提案仅保留“路径 3/3”，遗漏“任务成功率 >=99%”。
   - 风险：Requirements 阶段若按 proposal 落地，会弱化既定验收标准，导致“状态文档目标”与“需求门禁目标”不一致。
   - 建议：将 `proposal.md` 的“目标与成功指标/P-METRIC”与 `status.md` M1-M6 完整对齐，避免口径漂移。

## 结论
- 结构门禁：通过（章节齐全、P-DO/P-DONT/P-METRIC 与开放问题状态满足格式要求）
- 语义门禁：未通过（P1 open = 2）
- 证据门禁：通过（核验命令与定位信息完整）

**审查结论：暂不建议进入 Requirements 阶段。建议先修复上述 P1，再发起下一轮 Proposal 审查。**

---

## 复审（第 2 轮，2026-02-26）

### 复审范围
- `docs/v2.3/proposal.md` 针对首轮 P1 的修复项：
  - “变更影响面分析”能力覆盖
  - 成功指标与 `status.md` M5/M6 口径对齐

### 复审证据
1. `rg -n "影响面|复杂度覆盖率|任务成功率|P-DO-06|P-METRIC-03|P-METRIC-04" docs/v2.3/proposal.md docs/v2.3/status.md -S`
2. `nl -ba docs/v2.3/proposal.md | sed -n '20,220p'`

### 复审结果
- 原 P1-1：已关闭  
  - 证据：`proposal.md` 已在背景、方案、In Scope、P-DO 中覆盖“变更影响面分析”（`docs/v2.3/proposal.md:25`、`docs/v2.3/proposal.md:58`、`docs/v2.3/proposal.md:75`、`docs/v2.3/proposal.md:96`）。
- 原 P1-2：已关闭  
  - 证据：`proposal.md` 已补齐“复杂度覆盖率 >=95%”与“GitLab 路径 3/3 且任务成功率 >=99%”，并与 `status.md` M5/M6 对齐（`docs/v2.3/proposal.md:41-42`、`docs/v2.3/proposal.md:106-107`；对照 `docs/v2.3/status.md:37-38`）。

### 结论（第 2 轮）
- P0(open)=0
- P1(open)=0
- P2(open)=0

**复审结论：Proposal 阶段问题已收敛，建议人工确认后进入 Requirements 阶段。**

---

## 深入复审（第 3 轮，2026-02-26）

### 复审口径
- 三层门禁：结构门禁 + 语义门禁 + 证据门禁（对应 lessons_learned R4）
- 对齐基准：`docs/v2.3/status.md`（`_phase=Proposal`, `_change_level=major`）
- 阶段规则：`.aicoding/phases/01-proposal.md`

### 复审证据
1. `nl -ba docs/v2.3/proposal.md | sed -n '1,260p'`
2. `nl -ba docs/v2.3/status.md | sed -n '1,260p'`
3. `rg -n "capability_item|AST|调用图|数据流|复杂度|影响面|GitLab|任务成功率" docs/v2.3/proposal.md docs/v2.3/status.md -S`
4. `rg -n "\\| 版本 \\| v0\\.[0-9]+ \\||\\| v0\\.[0-9]+ \\| 2026-02-26" docs/v2.3/proposal.md -S`
5. `rg -n "审查：|review_change_management|review_proposal" docs/v2.3/status.md docs/v2.3/review_proposal.md -S`

### 发现的问题（按严重度）

#### P2（Minor）
1. `proposal.md` 文档元信息版本号与变更记录最新版本不一致
   - 位置：`docs/v2.3/proposal.md:10`，`docs/v2.3/proposal.md:146`
   - 现状：元信息写 `v0.1`，但变更记录已存在 `v0.2`。
   - 风险：评审与追溯时容易误判“当前有效文本版本”，不利于后续 Requirements 引用一致性（R2）。
   - 建议：将元信息版本号更新为 `v0.2`，并保持后续增量变更与记录同步。

2. `status.md` 的“关键链接-审查”仍指向上一阶段审查文件
   - 位置：`docs/v2.3/status.md:46`
   - 现状：当前处于 Proposal 阶段，但“审查”链接仍为 `review_change_management.md`。
   - 风险：人工审阅入口可能误导到上一阶段，增加漏看 Proposal 审查结论的概率。
   - 建议：在阶段内将该链接切换为 `review_proposal.md`（或补充多链接并标注阶段）。

### 结论（第 3 轮）
- 结构门禁：通过
- 语义门禁：通过（P0 open=0，P1 open=0）
- 证据门禁：通过
- P2(open)=2（建议修复，不阻断阶段推进）

**复审结论：Proposal 主体内容可进入人工确认；建议先修复上述 P2 一致性问题，再进入 Requirements。**

---

## 修复复审（第 4 轮，2026-02-26）

### 复审范围
- 第 3 轮提出的 2 个 P2 一致性问题：
  - `proposal.md` 元信息版本号
  - `status.md` 关键链接中的当前阶段审查指向

### 复审证据
1. `nl -ba docs/v2.3/proposal.md | sed -n '6,14p'`
2. `nl -ba docs/v2.3/status.md | sed -n '40,48p'`
3. `rg -n "\\| 版本 \\| v0\\.[0-9]+ \\|" docs/v2.3/proposal.md -S`
4. `rg -n "审查：" docs/v2.3/status.md -S`

### 复审结果
- 原 P2-1：已关闭  
  - 证据：`proposal.md` 元信息版本号已更新为 `v0.3`，且变更记录新增对应条目（`docs/v2.3/proposal.md:10`、`docs/v2.3/proposal.md:146`）。
- 原 P2-2：已关闭  
  - 证据：`status.md` 的“审查”链接已指向 `review_proposal.md`（`docs/v2.3/status.md:46`）。

### 结论（第 4 轮）
- P0(open)=0
- P1(open)=0
- P2(open)=0

**复审结论：Proposal 阶段已收敛，可由人工确认是否进入 Requirements 阶段。**
