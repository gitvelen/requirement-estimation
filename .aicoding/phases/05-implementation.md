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
- `templates/review_implementation_template.md`

## 本阶段输出
- 代码改动
- `docs/<版本号>/implementation_checklist.md`（可选，建议用于自检留痕）
- `docs/<版本号>/review_implementation.md`（major）或 `docs/<版本号>/review_minor.md`（minor）

## 阶段入口协议（🔴 MUST，CC-7 程序化强制）

> 脚本单源：`scripts/lib/common.sh` 的 `aicoding_phase_entry_required`。以下表格为人类可读视图，以脚本为准。

| 必读文件 | 用途 | 强制级别 |
|---------|------|---------|
| `docs/<版本号>/status.md` | 获取当前状态、Active CR、基线版本 | 🔴 CC-7 强制 |
| `docs/<版本号>/plan.md` | 本阶段核心输入（任务清单） | 🔴 CC-7 强制 |
| `docs/<版本号>/design.md` | 技术方案参考 | 🔴 CC-7 强制 |
| `docs/<版本号>/requirements.md` | 需求与约束依据 | 🔴 CC-7 强制 |
| `.aicoding/phases/05-implementation.md` | 本阶段规则（本文件） | 🔴 CC-7 强制 |
| `.aicoding/templates/implementation_checklist_template.md` | 自检清单模板 | 🔴 CC-7 强制 |
| `.aicoding/templates/review_implementation_template.md` | 审查模板 | 🔴 CC-7 强制 |

## 本阶段特有规则
1. 必须按任务顺序实现并逐项验证，不得跨任务"隐式扩 scope"。
2. 实现阶段默认执行 REQ 模式审查：逐条 GWT 判定 + 摘要块。
3. minor 允许精简审查，但不得触碰 `REQ-C`；触碰即升级 major。
4. hotfix 不走本阶段文档推进，按 `ai_workflow.md` 的 hotfix 轨道执行。
5. 如发现需求/设计冲突，先暂停并确认，不得自行改验收标准。
6. 版本重构（Major 且涉及架构/路由/数据源重写）时，必须在实现前产出功能对照清单（旧版功能→新版覆盖状态），逐项验证后方可推进；静态字符串匹配不能替代运行时行为验证。

## 里程碑展示协议（🔴 MUST）

> 来源：lessons_learned — Implementation 阶段从开始到出 review，中间没有向用户展示阶段性成果的节点，方向偏了返工代价最大。

AI 在实现过程中，必须在以下节点向用户展示中间结果并获得确认：

**UI 功能（有前端界面）**：
- 骨架里程碑：页面布局/路由/核心组件结构完成后，向用户描述或截图展示整体布局，确认方向正确再继续细节实现
- 交互里程碑：核心交互流程（表单提交、列表操作、状态切换）跑通后，向用户展示关键操作的输入输出

**后端/逻辑功能（无 UI）**：
- 核心流程里程碑：主流程跑通后，向用户展示关键输入→输出示例（命令+实际输出）
- 集成里程碑：与外部依赖/数据源对接完成后，展示端到端调用结果

**通用规则**：
- 每个里程碑用户确认后才继续下一批任务
- 用户在里程碑点提出的修改意见，优先于 plan.md 中的后续任务
- 里程碑展示不需要产出额外文档，在对话中完成即可
- 如果 plan.md 中任务数 ≤ 3 且无 UI，可跳过里程碑展示（简单变更）
- plan.md 中标注 🏁 的任务完成后，AI 必须暂停并向用户展示成果

## 阶段完成条件
1. 自审收敛（P0/P1 open=0）。
2. 关键验证命令通过并可复现。
3. `status.md` 更新到 Testing 前，出口门禁通过。
