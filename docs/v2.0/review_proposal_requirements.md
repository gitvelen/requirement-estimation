# Review Report：Proposal & Requirements / v2.0

| 项 | 值 |
|---|---|
| 阶段 | Proposal & Requirements |
| 版本号 | v2.0 |
| 日期 | 2026-02-08 |
| 检查点 | 文档一致性、范围完整性、术语一致性、编号完整性、引用完整性、版本记录 |
| 审查范围 | proposal.md (v0.12)、requirements.md (v1.15) |
| 输入材料 | /home/admin/Claude/requirement-estimation-system/docs/v2.0/proposal.md<br>/home/admin/Claude/requirement-estimation-system/docs/v2.0/requirements.md |

## 结论摘要
- 总体结论：:white_check_mark: 通过
- Blockers（P0）：0
- 高优先级（P1）：3
- 中优先级（P2）：4
- 低优先级（P3）：3

---

## 关键发现（按优先级）

### RVW-001（P1）proposal.md 元信息版本号不一致
- **证据**：proposal.md 第7行显示 `| 版本 | v0.12 |`，但第11行又显示 `| 版本 | v0.11 |`，存在两个版本号
- **风险**：导致文档元信息混乱，读者无法确定文档当前版本
- **建议修改**：将第11行的 `v0.11` 删除或修正为 `v0.12`
- **验证方式**：打开 proposal.md 确认第7-12行只有一个版本号显示

### RVW-002（P1）requirements.md 第104行 REQ-017 引用过时
- **证据**：requirements.md 第104行显示"系统画像相关分工：...导入技术文档与历史评估文档L0（REQ-011/REQ-017）"。但根据变更记录v1.9，REQ-017已被合并到REQ-011（L0文档已在REQ-011中支持），现在REQ-017是"报告下载"
- **风险**：文档间引用不一致，可能误导读者
- **建议修改**：将第104行的 `REQ-011/REQ-017` 改为仅 `REQ-011`
- **验证方式**：grep `REQ-017` 确认所有引用上下文

### RVW-003（P1）proposal.md 与 requirements.md 版本变更记录不同步
- **证据**：
  - proposal.md 最新版本是 v0.12（2026-02-07），变更记录共13条
  - requirements.md 最新版本是 v1.16（2026-02-07），变更记录共18条
  - proposal.md 的 v0.12 和 requirements.md 的 v1.16 都记录了"删除效能看板的明细与导出功能"这一变更
- **风险**：两个文档的版本演进历史无法追溯对应关系
- **建议修改**：在 proposal.md 中补充 v0.12 之后可能遗漏的变更，或增加版本映射说明
- **验证方式**：对比两份文档的变更记录时间线

---

## 中优先级问题（P2）

### RVW-004（P2）proposal.md "In Scope" 中的效能看板描述与最新变更不完全一致
- **证据**：proposal.md 第261行提到"效能看板（原AI效果报告升级：趋势/排行/下钻/明细导出；...）"。但根据 requirements.md v1.16，已删除"明细与导出"功能，仅保留下钻到任务列表
- **风险**：提案范围描述与需求规格不一致
- **建议修改**：更新 proposal.md 第261行，删除"明细导出"相关描述
- **验证方式**：对比 proposal.md In Scope 和 requirements.md REQ-020

### RVW-005（P2）proposal.md 中的"系统画像数据结构（待设计阶段确定）"与 requirements.md 存在字段定义
- **证据**：proposal.md 第105行注明"画像数据结构在 Requirements/Design 阶段详细定义"。但 requirements.md 第841-847行已定义了7个画像字段（in_scope、out_of_scope、core_functions、business_goals、business_objects、integration_points、key_constraints）
- **风险**：提案暗示数据结构未定义，实际上需求阶段已部分定义
- **建议修改**：在 proposal.md 中说明"数据结构已在 Requirements 阶段确定核心字段"或更新描述
- **验证方式**：交叉对比两份文档的数据结构描述

### RVW-006（P2）requirements.md 变更记录中 v1.7 缺失
- **证据**：requirements.md 变更记录从 v1.6 直接跳到 v1.8，缺少 v1.7 记录（虽然实际存在）
- **风险**：变更历史不完整
- **建议修改**：补充 v1.7 变更记录
- **验证方式**：检查变更记录编号连续性

### RVW-007（P2）proposal.md 中 "A-02" 系统清单配置优化的描述与 requirements.md REQ-019 存在细微差异
- **证据**：
  - proposal.md 第179-182行描述："只保留两个Tab"、"右上角按钮：只保留'下载模板'和'批量导入'"、"Tab内容：只显示数据表格"
  - requirements.md REQ-019 第1602-1604行描述一致，但 proposal 中没有明确提及"预览校验"步骤
- **风险**：提案范围描述不够详细，可能导致实现时遗漏关键步骤
- **建议修改**：在 proposal.md 中补充"预览校验"步骤说明
- **验证方式**：对比 proposal A-02 和 requirements REQ-019 的流程步骤

---

## 低优先级问题（P3）

### RVW-008（P3）proposal.md 和 requirements.md 中"学习闭环"术语使用存在轻微不一致
- **证据**：
  - proposal.md 主要使用"学习闭环"（Learning Loop）
  - requirements.md 1.2节背景使用"学习闭环"，但在场景分类中使用"学习闭环"和"修改轨迹记录"等更具体的术语
- **风险**：术语使用可能导致理解偏差，但不影响实质
- **建议修改**：建议统一术语表，明确"学习闭环"作为总称，"修改轨迹记录"、"专家差异统计"作为子项
- **验证方式**：在术语表中补充层级关系说明

### RVW-009（P3）proposal.md "约束/前提"中描述的数据源类型数量与 requirements.md 不完全一致
- **证据**：
  - proposal.md 第75行："系统能力覆盖度"指标基线→目标为"数据源类型计数（1→3）"
  - requirements.md 第25行明确三个数据源是"代码扫描、ESB集成、人工维护（文档）"
  - 但 proposal.md 第98-104行描述画像数据来源为"代码扫描 + 人工维护（可引用文档证据）"和"ESB清单 + 代码扫描"，表述顺序不同
- **风险**：表述不一致可能导致理解偏差，但不影响实质
- **建议修改**：统一表述顺序和命名
- **验证方式**：对比两份文档关于数据源的描述

### RVW-010（P3）proposal.md 中"开放问题与决策"表格格式可优化
- **证据**：proposal.md 第319-326行的"开放问题与决策"表格，没有包含"决策日期"、"决策人"等字段
- **风险**：审计追溯不完整
- **建议修改**：增加"决策日期"、"决策人"列
- **验证方式**：参考其他项目文档的最佳实践

---

## 验证通过的审查项

### :white_check_mark: 编号完整性验证
- REQ 编号：REQ-001 到 REQ-022 连续，无重复、无遗漏
- API 编号：API-001 到 API-015 连续，无重复、无遗漏
- SCN 编号：SCN-001 到 SCN-015 连续，无重复、无遗漏
- 非功能需求：REQ-NF-001 到 REQ-NF-006 连续

### :white_check_mark: 场景-需求-API 追溯矩阵完整性
- 所有 SCN 都有对应的 REQ
- 所有 SCN-011、SCN-014、SCN-015 无 API（纯UI调整）已明确标注"—"
- 追溯矩阵（第7.1节）与场景明细、需求明细的关联关系一致

### :white_check_mark: 术语一致性主要验证项
- "系统画像"（System Profile）定义一致
- "复杂度三维度评估"权重（35%/35%/30%）一致
- "PM修正率"计算口径一致
- "完整度评分"计算口径（代码30%+文档40%+ESB30%）一致

### :white_check_mark: 范围完整性主要验证项
- proposal.md In Scope 核心功能（第242-250行）在 requirements.md 都有对应 REQ
- proposal.md In Scope 体验优化（第252-264行）在 requirements.md 都有对应 REQ
- proposal.md Non-goals（第266-272行）与 requirements.md Out of Scope（第32-42行）基本一致

---

## 建议验证清单（命令级别）
- [x] 确认 REQ 编号连续性：`grep -o "REQ-[0-9]*" docs/v2.0/requirements.md | sort -u`
- [x] 确认 API 编号连续性：`grep -o "API-[0-9]*" docs/v2.0/requirements.md | sort -u`
- [x] 确认 SCN 编号连续性：`grep -o "SCN-[0-9]*" docs/v2.0/requirements.md | sort -u`
- [x] 检查 proposal 元信息版本号：`head -15 docs/v2.0/proposal.md | grep "版本"`
- [x] 检查 REQ-017 引用是否过时：`grep -n "REQ-017" docs/v2.0/requirements.md`
- [ ] 验证 RVW-001 修复后：`sed -n '7,12p' docs/v2.0/proposal.md | grep "版本" | wc -l` 应为1
- [ ] 验证 RVW-002 修复后：`grep -n "REQ-011/REQ-017" docs/v2.0/requirements.md` 应无结果

---

## 开放问题
- [ ] 是否需要在 proposal.md 和 requirements.md 之间建立明确的版本映射关系？
- [ ] proposal.md 的版本号策略是否应与 requirements.md 保持同步？

---

## 处理记录（建议由开发/人工填写）
| RVW-ID | 严重度 | 处理决策（Fix/Defer/Accept） | Owner | 说明 | 链接/证据 |
|---|---|---|---|---|---|
| RVW-001 | P1 | | | | |
| RVW-002 | P1 | | | | |
| RVW-003 | P1 | | | | |
| RVW-004 | P2 | | | | |
| RVW-005 | P2 | | | | |
| RVW-006 | P2 | | | | |
| RVW-007 | P2 | | | | |
| RVW-008 | P3 | | | | |
| RVW-009 | P3 | | | | |
| RVW-010 | P3 | | | | |

---

*审查报告版本: v1.0 | 生成时间: 2026-02-08*
