# Review Report：Planning / v2.2

| 项 | 值 |
|---|---|
| 阶段 | Planning |
| 版本号 | v2.2 |
| 日期 | 2026-02-24 |
| 基线版本（对比口径） | `v2.1` |
| 当前代码版本 | HEAD |
| 复查口径 | full |
| Active CR（如有） | 无 |
| 检查点 | 需求反向覆盖（requirements ↔ plan）、任务拆分粒度与依赖、REQ-C 禁止项显式覆盖、验证方式可复现性 |
| 审查范围 | 文档：`docs/v2.2/plan.md`、`docs/v2.2/requirements.md`、`docs/v2.2/design.md`、`docs/v2.2/status.md` |
| 输入材料 | `docs/v2.2/plan.md`、`docs/v2.2/requirements.md`、`docs/v2.2/design.md`、`.aicoding/phases/04-planning.md`、`.aicoding/templates/plan_template.md` |

## 结论摘要
- 总体结论：✅ 通过（Planning 第 1 轮独立审查收敛）
- Blockers（P0）：0
- 高优先级（P1）：0
- 其他建议（P2+）：0

## 关键发现（按优先级）
（无）

## 建议验证清单（命令级别）
- [x] 需求反向覆盖检查（requirements → plan，已执行 exit=0）：`bash -lc 'source .aicoding/scripts/lib/review_gate_common.sh && review_gate_validate_plan_reverse_coverage requirements docs/v2.2/requirements.md plan docs/v2.2/plan.md'`
- [x] R6 引用存在性 + 反向覆盖差集（已执行，差集为空）：见 `docs/v2.2/plan.md` "引用自检（R6）"命令块
- [x] 文档结构检查（已执行 exit=0）：`bash .aicoding/scripts/cc-hooks/doc-structure-check.sh`
- [x] REQ-C 禁止项覆盖审查（见下表）：全量 8 项 REQ-C 均在 plan.md 中有对应任务覆盖

### REQ-C 禁止项覆盖验证
| REQ-C ID | 一句话摘要 | plan.md 对应任务 | 任务状态 |
|----------|-----------|-----------------|---------|
| REQ-C001 | PM 不可编辑预估人天 | T006（后端）、T007（前端） | 待办 |
| REQ-C002 | 实质性修改不可绕过确认 | T006（后端）、T007（前端） | 待办 |
| REQ-C003 | 不得破坏既有数据兼容性 | T005、T006、T008、T012 | 待办 |
| REQ-C004 | 不得出现菜单/路由死链 | T001、T004、T012 | 待办 |
| REQ-C005 | 不得引入 DB 迁移/结构变更 | 全任务（无 DB 迁移任务） | 待办 |
| REQ-C006 | 文档导入不支持批量上传 | T009 | 待办 |
| REQ-C007 | 禁止保留 FUNC-022 入口 | T001、T003 | 待办 |
| REQ-C008 | 排行榜统计周期不可配置 | T002、T003 | 待办 |

## 开放问题
- [ ] 里程碑日期与 Owner/Reviewer 指派需人工确认（不阻塞进入 Implementation）

## 收敛判定
- 本轮后：P0(open)=0, P1(open)=0
- 距离收敛：是
- 建议：✅ Planning 已收敛，可进入 Implementation 阶段

---

## 2026-02-24 | 第 1 轮 | 审查者：Codex（独立审查）

### 审查角度
- 检查 `plan.md` 是否覆盖 requirements 全量 REQ/REQ-C
- 任务拆分粒度是否可执行且可验证
- 依赖顺序是否合理
- 验证方式是否可复现（命令级别）

### 证据（已执行）
- 反向覆盖门禁（exit=0）：`bash -lc 'source .aicoding/scripts/lib/review_gate_common.sh && review_gate_validate_plan_reverse_coverage requirements docs/v2.2/requirements.md plan docs/v2.2/plan.md'`
- plan 引用的 REQ（24 项）：`REQ-001~014、REQ-101~102、REQ-C001~C008`
- requirements 定义的 REQ（24 项）：`REQ-001~014、REQ-101~102、REQ-C001~C008`
- 差集：plan 引用但 requirements 未定义 = 空；requirements 定义但 plan 未覆盖 = 空

### 本轮新发现问题
| RVW-ID | 严重度 | 描述 | 证据 | 建议 |
|---|---|---|---|---|
| （无） | - | - | - | - |

### 审查通过理由
1. **需求覆盖完整性**：plan.md 任务概览表（T001~T013）覆盖了 requirements.md 中定义的全量 24 项 REQ/REQ-C，无遗漏。
2. **任务拆分粒度**：13 个任务均包含清晰的关联需求项、描述、验收标准、验证方式、依赖关系，具备可执行性。
3. **依赖顺序合理性**：执行顺序（§执行顺序）明确标注串行依赖，符合技术逻辑（如 T001 路由重构 → T003 看板拆分；T006 后端门禁 → T007 前端交互）。
4. **验证方式可复现性**：所有任务均提供命令级别验证方式（npm build、pytest、人工巡检清单），符合 R6 要求。
5. **REQ-C 禁止项覆盖**：全量 8 项 REQ-C 在任务概览表中均有对应任务（T001/T002/T003/T004/T005/T006/T007/T008/T009/T012），并在任务详情中明确验收标准。
6. **里程碑与 DoD**：里程碑 M1~M4 划分清晰，DoD 五项要求明确。

### 收敛判定
- 本轮后：P0(open)=0, P1(open)=0
- 距离收敛：是
- 建议：✅ 可进入 Implementation

---

## 审查检查表（Review Checklist）

### 文档结构（🔴 MUST）
- [x] plan.md 存在且符合模板结构（`.aicoding/templates/plan_template.md`）
- [x] 版本号、基线版本、关联设计/需求/状态文档正确
- [x] 任务概览表完整（13 行任务）
- [x] 任务详情章节完整（T001~T013）

### 需求追溯（🔴 MUST）
- [x] 全量 REQ/REQ-C 在任务概览表中有关联任务
- [x] 任务详情中明确"关联需求项"
- [x] 验收标准引用对应 GWT-ID
- [x] 反向覆盖检查通过（差集为空）

### 任务可执行性（🔴 MUST）
- [x] 每个任务包含：分类、优先级、预估工时、Owner、关联需求、任务状态、依赖任务、验证方式
- [x] 任务描述清晰，包含影响面/修改范围
- [x] 验收标准可判定（PASS/FAIL）
- [x] 验证方式可复现（命令/步骤）

### 依赖与风险（🔴 MUST）
- [x] 执行顺序章节明确标注依赖关系
- [x] 风险与缓解表覆盖核心风险（路由死循环、confirm 门禁误判、ESB 权限、remark 兼容）
- [x] 回滚/开关策略在各任务中明确

### R6 引用自检（🔴 MUST）
- [x] plan.md 包含"引用自检（R6）"命令块
- [x] plan 引用的 REQ 与 requirements 定义一致
- [x] 无悬空引用

---

## 质量度量

| 指标 | 值 | 目标 | 达成 |
|------|-----|------|------|
| 需求覆盖率 | 100% (24/24) | ≥100% | ✅ |
| 任务数 | 13 | - | - |
| P0 任务数 | 10 | - | - |
| P1 任务数 | 3 | - | - |
| 平均预估工时 | 9.2h | - | - |
| 总预估工时 | 120h | - | - |
| 阻塞问题数（P0/P1） | 0 | 0 | ✅ |

---

## 后续行动建议
1. **Implementation 阶段启动前**：确认里程碑日期与 Owner/Reviewer 指派（当前为"默认"，需人工确认）。
2. **执行过程中**：按执行顺序分 5 条泳道并行推进（见 plan.md §执行顺序）。
3. **Testing 阶段入口**：T012 全量回归必须在所有功能任务完成后执行，重点验证 REQ-C 禁止项。
