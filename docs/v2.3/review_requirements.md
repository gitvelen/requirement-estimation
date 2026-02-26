# Review Report：Requirements / v2.3

| 项 | 值 |
|---|---|
| 阶段 | Requirements |
| 版本号 | v2.3 |
| 日期 | 2026-02-26 |
| 审查范围 | `docs/v2.3/requirements.md` |
| 输入材料 | `docs/v2.3/proposal.md`、`docs/v2.3/status.md`、`docs/v2.3/requirements.md` |

## 审查清单

- [x] Proposal 覆盖：P-DO/P-DONT/P-METRIC 均在 §1.4 映射到 REQ/REQ-C + GWT
- [x] 需求可验收：每条 REQ 均有可判定 GWT
- [x] 场景完整：正常/异常/边界在 §2.3 均有落盘
- [x] GWT 可判定：Given/When/Then 可观测
- [x] 禁止项固化：`REQ-C001~REQ-C005` 已落盘并具备 GWT
- [x] 术语一致：与 proposal 与 status 关键术语一致（capability_item、AST、GitLab 3 模式、回滚）

## 禁止项/不做项确认清单

| # | 禁止/不做项描述 | 归类 | 目标 | 来源 |
|---|---|---|---|---|
| 1 | 误识别率无改善或改善不可证明 | A | REQ-C001 | proposal P-DONT-01 |
| 2 | 新增能力无法回滚到 v2.2 | A | REQ-C002 | proposal P-DONT-02 |
| 3 | 超范围新增完整图谱可视化页面 | A | REQ-C003 | proposal P-DONT-03 |
| 4 | 放宽输入边界与权限约束 | A | REQ-C004 | proposal 约束/风险 |
| 5 | 引入重型基础设施或改变部署形态 | A | REQ-C005 | proposal Non-goals |
| 6 | 重构任务评估主链路 UI 信息架构 | B | Non-goals | proposal Non-goals |

<!-- CONSTRAINTS-CHECKLIST-BEGIN -->
| ITEM | CLASS | TARGET | SOURCE |
|------|-------|--------|--------|
| C-001 | A | REQ-C001 | proposal P-DONT-01 |
| C-002 | A | REQ-C002 | proposal P-DONT-02 |
| C-003 | A | REQ-C003 | proposal P-DONT-03 |
| C-004 | A | REQ-C004 | proposal 约束/风险（安全边界） |
| C-005 | A | REQ-C005 | proposal Non-goals（部署形态不变） |
| C-006 | B | Non-goals | proposal Non-goals（不重构任务评估主链路 UI 信息架构） |
<!-- CONSTRAINTS-CHECKLIST-END -->

## 需求覆盖判定

| REQ-ID | GWT 数量 | GWT 可判定 | 备注 |
|--------|---------|-----------|------|
| REQ-001 | 3 | ✅ | 覆盖链路可达率与降级路径 |
| REQ-002 | 3 | ✅ | 覆盖 AST 主路径与错误容错 |
| REQ-003 | 4 | ✅ | 覆盖调用图/依赖/数据流/复杂度 |
| REQ-004 | 3 | ✅ | 覆盖三层影响面摘要 |
| REQ-005 | 4 | ✅ | 覆盖 GitLab 三模式与成功率门槛 |
| REQ-006 | 3 | ✅ | 覆盖最小前端接入与禁增新页 |
| REQ-007 | 3 | ✅ | 覆盖统一契约与失败结构 |
| REQ-008 | 3 | ✅ | 覆盖 L1/L2 回滚演练 |
| REQ-101 | 2 | ✅ | 覆盖误识别率与证据要素 |
| REQ-102 | 2 | ✅ | 覆盖 M1-M5 统计与门槛 |
| REQ-103 | 2 | ✅ | 覆盖 M6 指标与失败记录 |
| REQ-C001~005 | 各1 | ✅ | 全部具备可判定禁止项 GWT |

## 高风险语义审查（必做）

- [x] REQ-C 禁止项：每条均有明确 GWT
- [x] “可选/二选一/仅提示”语义：已在 API-001 模式参数约束中固化
- [x] 角色差异：manager/admin/expert/viewer 权限边界已在 §5.1 固化
- [x] 数据边界：路径/压缩包/凭据边界与错误码已在 §5.2 与 §6.2 固化

## 关键发现

本轮未发现 P0/P1 问题。

## 对抗性自检
- [x] 不存在“我知道意思但文本没写清”
- [x] 所有“禁止项”已固化为 REQ-C + GWT 或 Non-goals
- [x] 高风险边界（权限/输入/回滚）已前移收敛

## 收敛判定
- P0(open): 0
- P1(open): 0
- 结论：✅ 通过

<!-- CONSTRAINTS-CONFIRMATION-BEGIN -->
CONSTRAINTS_CONFIRMED: yes
CONFIRMED_BY: User
CONFIRMED_AT: 2026-02-26
<!-- CONSTRAINTS-CONFIRMATION-END -->

<!-- REVIEW-SUMMARY-BEGIN -->
REVIEW_STAGE: requirements
REVIEW_RESULT: pass
P0_OPEN: 0
P1_OPEN: 0
RVW_TOTAL: 0
REVIEWER: Codex
REVIEW_AT: 2026-02-26
VERIFICATION_COMMANDS: rg -n "P-DO-|P-DONT-|P-METRIC-" docs/v2.3/proposal.md; rg -n "^#### REQ-|^#### REQ-C|GWT-REQ-" docs/v2.3/requirements.md
<!-- REVIEW-SUMMARY-END -->
