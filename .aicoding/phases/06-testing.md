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

## 预审门禁（🔴 MUST，审查前执行）

> 来源：lessons_learned — 测试/构建不过就进入 REP 审查，审查轮次白费；修复后又要重新走查，是多轮不收敛的主要原因之一。

AI 在启动 REP 审查（写 `review_testing.md` 或 `review_minor.md`）之前，必须先执行以下检查并确认全部通过：

1. 运行 `aicoding.config.yaml` 中配置的 `result_gate_test_command` → 测试全部通过
2. 运行 `result_gate_build_command` → 构建成功
3. 运行 `result_gate_typecheck_command` → 类型检查通过
4. 确认 `test_report.md`（major）或测试证据（minor）已产出

预审全部通过后，将结果记录到本次审查产物再继续 REP 流程：
- major：填写审查模板的「§-1 预审结果」段落
- minor：在 `review_minor.md` 中记录同等检查结果（如本阶段走最小证据路径，也可在 `test_report.md` 或 `status.md` 的 `TEST-RESULT` 附同等检查结果）
如有失败项，先修复再重新预审，不进入 REP。

**多轮审查时同样适用**：每轮修复完成后，先重新跑预审门禁确认无回归，再启动下一轮审查。

## 阶段完成条件
1. 自审收敛（P0/P1 open=0）。
2. 覆盖差集为空（GWT 全覆盖）。
3. `status.md` 更新到 Deployment 前，出口门禁与结果门禁全部通过。
