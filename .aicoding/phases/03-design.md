# 阶段3：技术方案设计（Design）

> 阶段入口/出口清单为脚本单源：`scripts/lib/common.sh` 的 `aicoding_phase_entry_required` / `aicoding_phase_exit_required`。

## 目标
- 输出可落地的技术方案，并与 `requirements.md` 建立可验真追溯。

## 本阶段输入
- `docs/<版本号>/requirements.md`
- `docs/<版本号>/status.md`
- `templates/design_template.md`

## 本阶段输出
- `docs/<版本号>/design.md`
- `docs/<版本号>/review_design.md`

## 本阶段特有规则
1. 先补齐设计决策：技术栈、关键依赖、部署形态、风险与回滚。
2. 设计必须逐条覆盖需求约束，尤其 `REQ-C` 禁止项。
3. 允许记录待确认项，但必须标注影响和确认时机。
4. 如有 Active CR，按 diff-only 口径补充“变更点→设计影响”说明。

## 阶段完成条件
1. `review_design.md` 通过自审（P0/P1 open=0）。
2. 追溯覆盖校验通过（requirements → design）。
3. `status.md` 更新到下一阶段前，入口/出口门禁全部通过。
