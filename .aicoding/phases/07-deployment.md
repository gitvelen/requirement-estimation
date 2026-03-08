# 阶段7：部署（Deployment）

> 阶段入口清单为脚本单源：`scripts/lib/common.sh` 的 `aicoding_phase_entry_required`。

## 目标
- 在风险受控前提下完成发布、可回滚交付和文档闭环：
  - 验收环境（STAGING/TEST）默认可自动部署
  - 生产环境（PROD）或高风险场景需人工确认

## 本阶段输入
- `docs/<版本号>/test_report.md`
- `docs/<版本号>/design.md`
- `docs/<版本号>/requirements.md`
- `docs/<版本号>/status.md`
- `templates/deployment_template.md`

## 本阶段输出
- `docs/<版本号>/deployment.md`
- 主文档同步记录（按影响面）
- `status.md` 最终状态（`_change_status: done` 且 `_run_status: completed`，二者同步）

## 阶段入口协议（🔴 MUST，CC-7 程序化强制）

> 脚本单源：`scripts/lib/common.sh` 的 `aicoding_phase_entry_required`。以下表格为人类可读视图，以脚本为准。

| 必读文件 | 用途 | 强制级别 |
|---------|------|---------|
| `docs/<版本号>/status.md` | 获取当前状态、Active CR、基线版本 | 🔴 CC-7 强制 |
| `docs/<版本号>/test_report.md` | 测试结果确认（major 必须；minor 可用 status.md 内 TEST-RESULT 块替代） | 🔴 CC-7 强制（major）/ 🟡 可选（minor） |
| `docs/<版本号>/design.md` | 部署方案参考 | 🔴 CC-7 强制 |
| `docs/<版本号>/requirements.md` | 需求与验收依据 | 🔴 CC-7 强制 |
| `.aicoding/phases/07-deployment.md` | 本阶段规则（本文件） | 🔴 CC-7 强制 |
| `.aicoding/templates/deployment_template.md` | 部署文档模板 | 🔴 CC-7 强制 |

**Minor 测试证据说明**：Minor 变更在 Testing 阶段可选择以下任一方式提供测试证据：
- 方式 1：创建 `test_report.md`（标准路径）
- 方式 2：在 `status.md` 中内联 `TEST-RESULT` 块（简化路径）

Deployment 阶段入口时，pre-commit 的 `validate_minor_test_evidence` 会检查至少存在其中一种证据。

## 本阶段特有规则
1. `deployment.md` 必须明确目标环境（STAGING / PROD）。
2. 若目标环境为 STAGING/TEST 且不涉及高风险项（API 契约、数据迁移、权限安全、不可逆配置），AI 可自动部署，供人类验收。
3. 若目标环境为 PROD，或涉及高风险项，AI 必须先请求人工确认后执行部署。
4. 本次上线 CR 必须与 `status.md` Active CR 保持一致（上线子集关系）。
5. 主文档按影响面同步：
   - `docs/系统功能说明书.md`
   - `docs/技术方案设计.md`
   - `docs/接口文档.md`
   - `docs/用户手册.md`
   - `docs/部署记录.md`
6. 若使用逃生通道（如 `--no-verify`），必须补充审计说明。
7. 自动部署到验收环境后，`status.md` 必须置 `wait_confirm`，等待人类验收结论。

## 验收反馈机制（🔴 MUST）

### AI 行为规范

部署到验收环境（STAGING/TEST）后，AI 必须：

1. **设置等待状态**：将 `status.md` 的 `_run_status` 设为 `wait_confirm`
2. **主动询问验收结果**（结构化提示）：
   ```
   ✅ 已部署到验收环境（STAGING）

   请验收并反馈：
   1. 验收通过 - 将合入主分支并打 tag v1.0
   2. 验收不通过 - 说明问题，我将回到对应阶段修复
   ```
3. **等待用户明确表态**：
   - 用户选择"验收通过"或明确说"通过"、"确认"、"可以合入" → 执行验收通过流程
   - 用户选择"验收不通过"或说明问题 → 执行验收不通过流程

### 验收通过流程

1. **记录验收结论**：在 `deployment.md` 末尾追加"验收记录"章节：
   ```markdown
   ## 验收记录
   - 验收时间：YYYY-MM-DD HH:MM
   - 验收人：<用户名或"用户">
   - 验收结论：通过
   - 验收说明：<用户反馈内容>
   ```
2. **合入主分支**：
   ```bash
   git checkout main
   git merge --squash <feature-branch>
   git commit -m "feat: <描述> [CR-YYYYMMDD-001]"
   ```
3. **打 tag**：
   ```bash
   git tag v1.0 -m "Release v1.0: <版本说明>"
   git push origin main --tags
   ```
4. **更新 status.md**：
   - `_change_status: done`
   - `_run_status: completed`
   - 更新 Active CR 列表（将已实现的 CR 状态改为 Implemented）
5. **同步主文档**（按 CR 影响面）：
   - `docs/系统功能说明书.md`
   - `docs/技术方案设计.md`
   - `docs/接口文档.md`
   - `docs/用户手册.md`
   - `docs/部署记录.md`（追加本次部署记录）

### 验收不通过流程

1. **记录验收结论**：在 `deployment.md` 末尾追加"验收记录"章节：
   ```markdown
   ## 验收记录
   - 验收时间：YYYY-MM-DD HH:MM
   - 验收人：<用户名或"用户">
   - 验收结论：不通过
   - 验收说明：<用户反馈的问题描述>
   ```
2. **分析问题**，确定需要回到哪个阶段（通常是 Testing 或 Implementation）
3. **更新 status.md**：
   - `_phase: Testing` 或 `Implementation`（根据问题性质）
   - `_run_status: running`
   - `_review_round: 0`（重置轮次）
4. **修复问题**，重新执行后续阶段
5. **再次部署到验收环境**，重新走验收流程

## 部署完成后的后续变更

当本阶段完成（`_change_status: done` + `_run_status: completed`）后，如用户提出新变更需求，AI 必须：

1. **分析变更描述**，给出建议（"建议作为 v1.0 补丁" 或 "建议创建 v1.1 新版本"）
2. **询问用户确认**："这是 v1.0 的补丁修复，还是要开始 v1.1 新版本？"
3. **按用户指定执行**：参考 `phases/00-change-management.md` 的"部署完成后的变更启动"规则
4. **版本内变更必须创建 CR**，进入 Phase 00 澄清流程；**新版本启动直接从 Proposal 开始**

## 完成条件
1. `deployment.md` 存在，且部署文档与回滚方案完整。
2. 部署执行记录完整：
   - STAGING/TEST：AI 执行并记录；
   - PROD/高风险：人工确认后执行并记录。
3. 人类验收结论明确（通过/不通过）。
4. 验收通过时，`status.md` 标记完成且关键信息一致。
5. 完成态同步：`_change_status: done` 与 `_run_status: completed` 必须同时成立。
