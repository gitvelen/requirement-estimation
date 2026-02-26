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
| `docs/<版本号>/test_report.md` | 测试结果确认 | 🔴 CC-7 强制 |
| `docs/<版本号>/design.md` | 部署方案参考 | 🔴 CC-7 强制 |
| `docs/<版本号>/requirements.md` | 需求与验收依据 | 🔴 CC-7 强制 |
| `.aicoding/phases/07-deployment.md` | 本阶段规则（本文件） | 🔴 CC-7 强制 |
| `.aicoding/templates/deployment_template.md` | 部署文档模板 | 🔴 CC-7 强制 |

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

## 完成条件
1. `deployment.md` 存在，且部署文档与回滚方案完整。
2. 部署执行记录完整：
   - STAGING/TEST：AI 执行并记录；
   - PROD/高风险：人工确认后执行并记录。
3. 人类验收结论明确（通过/不通过）。
4. 验收通过时，`status.md` 标记完成且关键信息一致。
5. 完成态同步：`_change_status: done` 与 `_run_status: completed` 必须同时成立。
