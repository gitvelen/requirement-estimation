# 阶段7：部署（Deployment）

> 阶段入口清单为脚本单源：`scripts/lib/common.sh` 的 `aicoding_phase_entry_required`。

## 目标
- 在人工确认下完成安全发布、可回滚交付和文档闭环。

## 本阶段输入
- `docs/<版本号>/test_report.md`
- `docs/<版本号>/design.md`
- `docs/<版本号>/requirements.md`
- `docs/<版本号>/status.md`
- `templates/deployment_template.md`

## 本阶段输出
- `docs/<版本号>/deployment.md`
- 主文档同步记录（按影响面）
- `status.md` 最终状态（`_change_status: done`）

## 本阶段特有规则
1. Deployment 必须人工确认后执行，AI 不得自启动上线。
2. 若涉及 API 契约、数据迁移、权限安全、不可逆配置，必须额外提示风险。
3. 本次上线 CR 必须与 `status.md` Active CR 保持一致（上线子集关系）。
4. 主文档按影响面同步：
   - `docs/系统功能说明书.md`
   - `docs/技术方案设计.md`
   - `docs/接口文档.md`
   - `docs/用户手册.md`
   - `docs/部署记录.md`
5. 若使用逃生通道（如 `--no-verify`），必须补充审计说明。

## 完成条件
1. 部署文档与回滚方案完整。
2. 人工确认已执行并记录。
3. `status.md` 标记完成且关键信息一致。
