# 阶段4：任务计划（Planning）

> 阶段入口/出口清单为脚本单源：`scripts/lib/common.sh` 的 `aicoding_phase_entry_required` / `aicoding_phase_exit_required`。

## 目标
- 把设计拆解为可执行、可验证、可追溯的任务。

## 本阶段输入
- `docs/<版本号>/design.md`
- `docs/<版本号>/requirements.md`
- `docs/<版本号>/status.md`
- `templates/plan_template.md`
- `templates/review_planning_template.md`

## 本阶段输出
- `docs/<版本号>/plan.md`
- `docs/<版本号>/review_planning.md`

## 阶段入口协议（🔴 MUST，CC-7 程序化强制）

> 脚本单源：`scripts/lib/common.sh` 的 `aicoding_phase_entry_required`。以下表格为人类可读视图，以脚本为准。

| 必读文件 | 用途 | 强制级别 |
|---------|------|---------|
| `docs/<版本号>/status.md` | 获取当前状态、Active CR、基线版本 | 🔴 CC-7 强制 |
| `docs/<版本号>/design.md` | 本阶段核心输入 | 🔴 CC-7 强制 |
| `docs/<版本号>/requirements.md` | 反向覆盖与约束依据 | 🔴 CC-7 强制 |
| `.aicoding/phases/04-planning.md` | 本阶段规则（本文件） | 🔴 CC-7 强制 |
| `.aicoding/templates/plan_template.md` | 产出物模板 | 🔴 CC-7 强制 |
| `.aicoding/templates/review_planning_template.md` | 审查模板 | 🔴 CC-7 强制 |

## 本阶段特有规则
1. 每个任务必须声明 `related_reqs`，确保需求反向覆盖。
2. 每个任务必须给出可复现验证命令（文档类可标注人工确认）。
3. 任务粒度优先“可独立提交 + 可独立验证”。
4. 若存在 Active CR，需在任务中标注 CR 影响范围。

## 阶段完成条件
1. `review_planning.md` 通过自审（P0/P1 open=0）。
2. 需求反向覆盖校验通过（requirements ↔ plan）。
3. `status.md` 更新到下一阶段前，入口/出口门禁全部通过。
