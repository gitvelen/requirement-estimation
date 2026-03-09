# v2.5 Requirements 阶段审查报告

## 审查信息
- **审查者**：Claude Opus 4.6
- **审查时间**：2026-03-06
- **审查对象**：`docs/v2.5/requirements.md` v0.2
- **审查口径**：full（Requirements 阶段首次审查）
- **适用规则**：
  - `.aicoding/phases/02-requirements.md`
  - `.aicoding/templates/requirements_template.md`
  - `docs/lessons_learned.md`（快速索引 R1-R10）

## 审查证据
1. Requirements 文档完整性核验：
   - `wc -l docs/v2.5/requirements.md`（行数统计：1503 行）
   - `rg -n "^## [0-9]" docs/v2.5/requirements.md`（章节结构：§1-§8 齐全）
2. 覆盖映射表核验：
   - `rg -n "覆盖映射表|P-DO-|P-DONT-|P-METRIC-" docs/v2.5/requirements.md`（18 个锚点全部覆盖）
3. Proposal 锚点覆盖性核验：
   - `rg -n "P-DO-|P-DONT-|P-METRIC-" docs/v2.5/proposal.md`（8 个 P-DO + 4 个 P-DONT + 4 个 P-METRIC）
   - 对比 requirements.md 覆盖映射表（100% 覆盖）
4. GWT 格式核验：
   - `rg -n "GWT-REQ-" docs/v2.5/requirements.md`（23 个 GWT，格式规范）
5. 禁止项覆盖性核验：
   - `rg -n "REQ-C00[0-9]|禁止|不得|不允许" docs/v2.5/requirements.md`（4 个禁止项 + 2 个技术约束）
6. 文本错误核验：
   - 行 728："项看 AI 建议 diff" → 已修正为 "项目经理查看 AI 建议 diff"
   - 行 760："1导入页面" → 已修正为 "1. 项目经理访问知识导入页面"

## 发现的问题（按严重度）

### P0（Blocker）
无

### P1（Major）
无

### P2（Minor）
无

## 审查清单

### 1. 文档结构完整性
- [✓] 文档元信息齐全（状态、作者、日期、版本、关联）
- [✓] §1 概述（目的与范围、背景约束假设、术语口径、覆盖性检查）
- [✓] §2 业务场景说明（角色对象、场景列表、场景明细）
- [✓] §3 功能性需求（需求列表、需求明细、GWT）
- [✓] §4 非功能需求（需求列表、需求明细、GWT）
- [✓] §4A 禁止项与约束（禁止项列表、禁止项明细、技术约束列表、技术约束明细、GWT）
- [✓] §5 权限与安全（角色权限矩阵、安全约束）
- [✓] §6 数据与接口（数据结构变更、API 接口变更、数据迁移策略）
- [✓] §7 追溯矩阵（需求追溯、验收标准追溯）
- [✓] §8 变更记录

### 2. 覆盖映射完整性（R5）
- [✓] 覆盖映射表存在（§1.4）
- [✓] Proposal 锚点总数：18（8 个 P-DO + 4 个 P-DONT + 4 个 P-METRIC + 2 个开放问题）
- [✓] 已覆盖：18
- [✓] defer：0
- [✓] 覆盖率：100%
- [✓] 每个 P-DO 映射到至少一个 REQ-ID
- [✓] 每个 P-DONT 映射到至少一个 REQ-C-ID
- [✓] 每个 P-METRIC 映射到至少一个 REQ-ID（REQ-101~104）
- [✓] 每个开放问题映射到至少一个 REQ-C-ID（REQ-C005~C006）

### 3. 场景覆盖完整性
- [✓] 场景列表存在（§2.2）
- [✓] 场景明细存在（§2.3）
- [✓] 场景总数：9（SCN-001 至 SCN-009）
- [✓] 每个场景包含：场景分类、主要角色、相关对象、关联需求ID、前置条件、触发条件、流程步骤、输出产物、异常与边界处理
- [✓] 场景覆盖正常/异常/边界情况

### 4. 功能性需求完整性
- [✓] 功能性需求列表存在（§3.1）
- [✓] 功能性需求明细存在（§3.2）
- [✓] 功能性需求总数：8（REQ-001 至 REQ-008）
- [✓] 每个需求包含：测试等级、目标/价值、入口/触发、前置条件、主流程、输入/输出、页面与交互、业务规则、异常与边界、验收标准（GWT）、关联
- [✓] 每个需求至少包含 1 个 GWT

### 5. 非功能需求完整性
- [✓] 非功能需求列表存在（§4.1）
- [✓] 非功能需求明细存在（§4.2）
- [✓] 非功能需求总数：4（REQ-101 至 REQ-104）
- [✓] 每个需求包含：测试等级、目标/价值、性能指标、测试方法、优化措施、验收标准（GWT）、关联
- [✓] 每个需求至少包含 1 个 GWT

### 6. 禁止项与约束完整性
- [✓] 禁止项列表存在（§4A.1）
- [✓] 禁止项明细存在（§4A.3）
- [✓] 禁止项总数：4（REQ-C001 至 REQ-C004）
- [✓] 技术约束列表存在（§4A.2）
- [✓] 技术约束明细存在（§4A.4）
- [✓] 技术约束总数：2（REQ-C005 至 REQ-C006）
- [✓] 每个禁止项/约束包含：约束类型、约束内容、理由、验收标准（GWT）、关联
- [✓] 每个禁止项/约束至少包含 1 个 GWT

### 7. GWT 格式规范性
- [✓] GWT-ID 格式：`GWT-REQ-{REQ-ID}-{序号}`
- [✓] GWT 格式：Given-When-Then
- [✓] GWT 可判定性：每个 GWT 包含明确的前置条件、操作、预期结果
- [✓] GWT 总数：23

### 8. 追溯矩阵完整性
- [✓] 需求追溯矩阵存在（§7.1）
- [✓] 验收标准追溯矩阵存在（§7.2）
- [✓] 每个 REQ-ID 可追溯到场景、Proposal 锚点、CR
- [✓] 每个 GWT-ID 可追溯到 REQ-ID

### 9. 数据与接口完整性
- [✓] 数据结构变更说明存在（§6.1）
- [✓] API 接口变更说明存在（§6.2）
- [✓] 数据迁移策略说明存在（§6.3）
- [✓] 新增 API 接口总数：3（模板下载、任务状态查询、WebSocket 连接）

### 10. 权限与安全完整性
- [✓] 角色权限矩阵存在（§5.1）
- [✓] 安全约束说明存在（§5.2）

## 禁止项/不做项确认清单（🔴 MUST）

### 来源汇总
1. **Proposal Non-goals**（`docs/v2.5/proposal.md:133-145`）：
   - v2.4 Idea 池中的其他功能（系统识别修正、功能拆分偏好、类型归纳、其他优化建议）
   - 旧数据自动迁移脚本
   - 功能开关/灰度发布

2. **Proposal P-DONT 锚点**（`docs/v2.5/proposal.md:178-182`）：
   - P-DONT-01: 不得自动迁移 v2.4 旧数据
   - P-DONT-02: 不得在 v2.5 中包含 v2.4 Idea 池中的其他功能
   - P-DONT-03: 多层级模块结构深度不得超过 3 层
   - P-DONT-04: WebSocket 推送不得阻塞主线程

3. **对话中的禁止/不做要求**：
   - 无额外禁止项（所有禁止项均已在 Proposal 中明确）

### 禁止项分类与固化状态

```
CONSTRAINTS-CHECKLIST-BEGIN
| 禁止项内容 | 来源 | 分类 | REQ-C-ID | GWT-ID | 状态 |
|-----------|------|------|----------|--------|------|
| 不得自动迁移 v2.4 旧数据 | Proposal P-DONT-01 | A | REQ-C001 | GWT-REQ-C001-01 | ✅已固化 |
| 不得在 v2.5 中包含 v2.4 Idea 池中的其他功能 | Proposal P-DONT-02 | A | REQ-C002 | GWT-REQ-C002-01 | ✅已固化 |
| 多层级模块结构深度不得超过 3 层 | Proposal P-DONT-03 | A | REQ-C003 | GWT-REQ-C003-01 | ✅已固化 |
| WebSocket 推送不得阻塞主线程 | Proposal P-DONT-04 | A | REQ-C004 | GWT-REQ-C004-01 | ✅已固化 |
| v2.4 Idea 池中的其他功能（系统识别修正、功能拆分偏好、类型归纳、其他优化建议） | Proposal Non-goals | B | - | - | ✅已写入 Non-goals |
| 旧数据自动迁移脚本 | Proposal Non-goals | B | - | - | ✅已写入 Non-goals（与 REQ-C001 一致） |
| 功能开关/灰度发布 | Proposal Non-goals | B | - | - | ✅已写入 Non-goals |
CONSTRAINTS-CHECKLIST-END
```

**分类说明**：
- **A 类**：已固化为 REQ-Cxxx（requirements.md 中存在对应条目 + GWT-ID）
- **B 类**：明确写入 Non-goals（含边界与原因）

**覆盖性统计**：
- 禁止项总数：7
- A 类（已固化为 REQ-C）：4
- B 类（已写入 Non-goals）：3
- 覆盖率：100%（无遗漏、无 TBD）

## 结论
- 结构门禁：✅ 通过（文档结构完整、章节齐全）
- 语义门禁：✅ 通过（P0 open = 0，P1 open = 0，P2 open = 0）
- 证据门禁：✅ 通过（覆盖映射 100%、GWT 格式规范、追溯矩阵完整）
- 禁止项门禁：✅ 通过（禁止项清单完整、分类明确、无 TBD）

**审查结论：✅ 通过，建议进入 Design 阶段**

## 建议
1. Design 阶段需要详细展开 WebSocket 连接管理、心跳保活、断线重连机制
2. Design 阶段需要详细展开多层级模块结构的递归渲染算法
3. Design 阶段需要详细展开 AI 建议混合 diff 展示的实现方案
4. Plan 阶段需要细化性能测试用例（100 个模块渲染 < 2s、WebSocket 延迟 < 500ms）
5. Testing 阶段需要准备人类验证清单（五域展示用户验收）

## 机器可读确认块

```
REVIEW-CONFIRMATION-BEGIN
PHASE: Requirements
VERSION: v0.1
REVIEW_DATE: 2026-03-06
REVIEWER: Claude Opus 4.6
STRUCTURE_GATE: PASS
SEMANTIC_GATE: PASS
EVIDENCE_GATE: PASS
CONSTRAINTS_CONFIRMED: yes
COVERAGE_RATE: 100%
P0_OPEN: 0
P1_OPEN: 0
P2_OPEN: 0
RECOMMENDATION: PROCEED_TO_DESIGN
REVIEW-CONFIRMATION-END
```

---
审查完成时间：2026-03-06


---

## 第 2 轮审查（2026-03-06，CR-20260306-001 增量回填）

### 审查信息
- **审查者**：Codex
- **审查时间**：2026-03-06
- **审查对象**：`docs/v2.5/requirements.md` v0.5
- **审查范围**：`CR-20260306-001` 影响的需求增量（`REQ-002`、`REQ-006`、`REQ-101`、覆盖映射、追溯矩阵）
- **审查口径**：full（针对受影响章节全文一致性回看）

### 审查证据
1. 覆盖映射与 defer 核验：
   - `nl -ba docs/v2.5/requirements.md | sed -n '67,93p'`
2. `REQ-006` 下载按钮位置核验：
   - `nl -ba docs/v2.5/requirements.md | sed -n '744,806p'`
3. `REQ-002` / `REQ-101` 虚拟滚动口径移除核验：
   - `nl -ba docs/v2.5/requirements.md | sed -n '486,535p'`
   - `nl -ba docs/v2.5/requirements.md | sed -n '946,981p'`
4. 追溯矩阵与变更记录核验：
   - `nl -ba docs/v2.5/requirements.md | sed -n '1426,1477p'`
   - `rg -n "REQ-C006|GWT-REQ-C006-01|虚拟滚动" docs/v2.5/requirements.md`

### 发现的问题（按严重度）

#### P0（Blocker）
无

#### P1（Major）
无

#### P2（Minor）
1. `proposal.md` 仍保留“虚拟滚动”原始表述；在后续 Design/Plan/Test 回填前，需明确以 `requirements.md v0.5 + CR-20260306-001` 为最新边界，避免下游继续引用旧口径。

### 审查结论
- 结构门禁：✅ 通过
- 语义门禁：✅ 通过（P0 open = 0，P1 open = 0）
- 证据门禁：✅ 通过（按钮位置、defer、追溯链均可复现）

**审查结论：✅ 通过。`requirements.md` 已完成 `CR-20260306-001` 的需求层回填，可等待人工确认是否进入 Design 阶段。**

### 机器可读确认块

```
REVIEW-CONFIRMATION-BEGIN
PHASE: Requirements
VERSION: v0.5
REVIEW_DATE: 2026-03-06
REVIEWER: Codex
SCOPE: CR-20260306-001 delta
STRUCTURE_GATE: PASS
SEMANTIC_GATE: PASS
EVIDENCE_GATE: PASS
P0_OPEN: 0
P1_OPEN: 0
P2_OPEN: 1
RECOMMENDATION: WAIT_USER_CONFIRM_FOR_DESIGN
REVIEW-CONFIRMATION-END
```
