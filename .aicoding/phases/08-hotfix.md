# 阶段8：热修（Hotfix）

> 阶段入口/出口的文件存在性清单以 `scripts/lib/common.sh` 的 `aicoding_phase_entry_required` / `aicoding_phase_exit_required` 为单源；Hotfix 的最小测试证据属于内容级门禁，由 CC hook / pre-commit 补充校验。

## 目标
- 在不扩张范围的前提下完成线上紧急修复，并为后续回到原阶段或继续交付保留最小可验证证据。

## 阶段入口/出口

**入口文件：**
- `docs/<版本号>/status.md`
- `.aicoding/phases/08-hotfix.md`（本文件）
- `.aicoding/templates/status_template.md`

**出口文件：**
- `docs/<版本号>/status.md`（必须内联 `TEST-RESULT` 结果块）

## 阶段入口协议（🔴 MUST，CC-7 程序化强制）

> 脚本单源：`scripts/lib/common.sh` 的 `aicoding_phase_entry_required`。以下表格为人类可读视图，以脚本为准。

| 必读文件 | 用途 | 强制级别 |
|---------|------|---------|
| `docs/<版本号>/status.md` | 获取原阶段、当前状态、回滚信息、Active CR | 🔴 CC-7 强制 |
| `.aicoding/phases/08-hotfix.md` | Hotfix 边界与退出规则 | 🔴 CC-7 强制 |
| `.aicoding/templates/status_template.md` | `TEST-RESULT` 内联格式、状态字段语义 | 🔴 CC-7 强制 |

## 本阶段特有规则
1. Hotfix 的标准路径是切换到独立 `_phase: Hotfix`；进入时应在 `status.md` 的“阶段转换记录”中记录原阶段。
2. Hotfix 只允许低风险、单点修复；pre-write / pre-commit 会执行以下硬门禁：
   - staged 文件数不得超过 `hotfix_max_diff_files`
   - 不得触碰 `REQ-C`
   - 不得涉及 API / DB schema / 权限安全敏感边界
3. Hotfix 阶段的版本文档作用域仅允许：
   - `status.md`
   - `review_*.md`
   - `cr/`
4. Hotfix 退出前，无论是回到原阶段还是继续进入后续阶段，`status.md` 都必须内联 `TEST-RESULT` 结果块，作为最小交付证据。
5. Hotfix 的 `_review_round` 独立计数，不受 5 轮限制；若退出 Hotfix 后恢复 major/minor 常规流程，应按新阶段从 `0` 重新计数，不恢复进入 Hotfix 前的旧值。

## 推荐执行路径
1. 将 `status.md` 切换为 `_change_level: hotfix`、`_phase: Hotfix`、`_workflow_mode: auto`
2. 完成最小范围修复
3. 执行最小可复现验证
4. 在 `status.md` 中写入 `TEST-RESULT` 结果块
5. 根据结果选择：
   - 回到原阶段继续常规流程
   - 直接进入 Deployment
   - 标记完成（`done` + `completed`）

## 完成条件（🔴 MUST）
1. Hotfix 边界检查通过。
2. `status.md` 已记录最小测试证据（`TEST-RESULT` 结果块）。
3. 若退出 Hotfix，目标阶段与 `_workflow_mode` 同步一致。
