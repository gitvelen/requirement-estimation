# 阶段6：测试（Testing）

> 阶段入口/出口清单为脚本单源：`scripts/lib/common.sh` 的 `aicoding_phase_entry_required` / `aicoding_phase_exit_required`。

## 目标
- 验证需求闭环，确保发布前结果正确性可证明。

## 本阶段输入
- 代码实现
- `docs/<版本号>/requirements.md`
- `docs/<版本号>/plan.md`
- `docs/<版本号>/status.md`
- `templates/test_report_template.md`
- `templates/review_testing_template.md`

## 本阶段输出
- `docs/<版本号>/test_report.md`
- `docs/<版本号>/review_testing.md`（major）或测试证据（minor：`test_report.md` 或 `status.md` 内联 `TEST-RESULT`；`review_minor.md` 基于实现阶段结果继续追加 Testing 轮次机器可读结论 `MINOR-TESTING-ROUND`）
- `docs/<版本号>/plan.md`（如需回填任务完成状态）

## 阶段入口协议（🔴 MUST，CC-7 程序化强制）

> 脚本单源：`scripts/lib/common.sh` 的 `aicoding_phase_entry_required`。以下表格为人类可读视图，以脚本为准。

| 必读文件 | 用途 | 强制级别 |
|---------|------|---------|
| `docs/<版本号>/status.md` | 获取当前状态、Active CR、基线版本 | 🔴 CC-7 强制 |
| `docs/<版本号>/requirements.md` | 需求与 GWT 覆盖依据 | 🔴 CC-7 强制 |
| `docs/<版本号>/plan.md` | 任务清单与验证命令参考 | 🔴 CC-7 强制 |
| `.aicoding/phases/06-testing.md` | 本阶段规则（本文件） | 🔴 CC-7 强制 |
| `.aicoding/templates/test_report_template.md` | 测试报告模板 | 🔴 CC-7 强制 |
| `.aicoding/templates/review_testing_template.md` | 审查模板 | 🔴 CC-7 强制 |

## 本阶段特有规则
1. 覆盖矩阵必须覆盖 requirements 中全部 `GWT-ID`。
2. major 必须有审查摘要块和人类抽检锚点；minor 至少提供最小测试证据。
3. 有 Active CR 时，需显式说明回归范围和 CR 影响验证结果。
4. 阶段推进 commit 触发结果门禁：`Implementation -> Testing` 与 `Testing -> Deployment` 均触发 `result_gate_test/build/typecheck`。
5. 发现失败先修复再重测，禁止"带失败推进"。
6. 涉及前端页面改造时，必须存在对应的契约烟测（覆盖：菜单/标题一致性、空态/错态/加载态、关键入口可达），仅 `npm run build` 通过不视为充分验证。
7. 标注 [Integration Required] 的 REQ，必须提供分层测试证据：
   - AI 自动化测试：API 集成测试脚本 + 执行日志（🔴 MUST）
   - 人类验证清单：操作步骤 + 预期结果（🟡 建议，关键流程推荐）
8. 标注 [E2E Required] 的 REQ（仅关键业务流程），必须提供：
   - AI 自动化测试：完整链路测试脚本 + 执行日志（🔴 MUST）
   - 人类验收记录：验证人 + 验证时间 + 通过/失败（🔴 MUST）

## 预审门禁（🔴 MUST，审查前执行）

> 通用规则见 `ai_workflow.md` 的"预审门禁"章节。本阶段特有检查项：

**Testing 阶段特有检查项**：
1. 确认 `test_report.md`（major）或测试证据（minor）已产出

## 阶段完成条件
1. 自审收敛（P0/P1 open=0）。
2. 覆盖差集为空（GWT 全覆盖）。
3. `status.md` 更新到 Deployment 前，出口门禁与结果门禁全部通过。
