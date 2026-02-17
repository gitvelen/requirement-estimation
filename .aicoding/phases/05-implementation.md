# 阶段5：实现（Implementation）

> 阶段入口/出口清单为脚本单源：`scripts/lib/common.sh` 的 `aicoding_phase_entry_required` / `aicoding_phase_exit_required`。

## 目标
- 按 `plan.md` 完成实现，输出可验证代码和审查证据。

## 本阶段输入
- `docs/<版本号>/plan.md`
- `docs/<版本号>/design.md`
- `docs/<版本号>/requirements.md`
- `docs/<版本号>/status.md`
- `templates/implementation_checklist_template.md`

## 本阶段输出
- 代码改动
- `docs/<版本号>/review_implementation.md`（major）或 `docs/<版本号>/review_minor.md`（minor）

## 本阶段特有规则
1. 必须按任务顺序实现并逐项验证，不得跨任务“隐式扩 scope”。
2. 实现阶段默认执行 REQ 模式审查：逐条 GWT 判定 + 摘要块。
3. minor 允许精简审查，但不得触碰 `REQ-C`；触碰即升级 major。
4. hotfix 不走本阶段文档推进，按 `ai_workflow.md` 的 hotfix 轨道执行。
5. 如发现需求/设计冲突，先暂停并确认，不得自行改验收标准。

## 阶段完成条件
1. 自审收敛（P0/P1 open=0）。
2. 关键验证命令通过并可复现。
3. `status.md` 更新到 Testing 前，出口门禁通过。
