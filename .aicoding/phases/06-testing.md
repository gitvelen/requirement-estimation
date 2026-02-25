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

## 本阶段输出
- `docs/<版本号>/test_report.md`
- `docs/<版本号>/review_testing.md`（major）或 `docs/<版本号>/review_minor.md`（minor）

## 本阶段特有规则
1. 覆盖矩阵必须覆盖 requirements 中全部 `GWT-ID`。
2. major 必须有审查摘要块和人类抽检锚点；minor 至少提供最小测试证据。
3. 有 Active CR 时，需显式说明回归范围和 CR 影响验证结果。
4. 阶段推进 commit 触发结果门禁：`result_gate_test/build/typecheck`。
5. 发现失败先修复再重测，禁止"带失败推进"。
6. 涉及前端页面改造时，必须存在对应的契约烟测（覆盖：菜单/标题一致性、空态/错态/加载态、关键入口可达），仅 `npm run build` 通过不视为充分验证。

## 阶段完成条件
1. 自审收敛（P0/P1 open=0）。
2. 覆盖差集为空（GWT 全覆盖）。
3. `status.md` 更新到 Deployment 前，出口门禁与结果门禁全部通过。
