# deployment.md

## Deployment Plan
target_env: staging
deployment_date: 2026-04-20
deployment_method: manual

## Pre-deployment Checklist
- [x] all acceptance items passed
- [x] required migrations verified
- [x] rollback plan prepared
- [x] smoke checks prepared

## Deployment Steps
1. 发布后端 `target_system` 相关改动到 staging，并同步发布前端页面资源，覆盖创建页、详情页和编辑页。
2. 确认本次变更不涉及数据库迁移；刷新前端静态资源后，检查任务创建接口与详情/编辑接口已返回待评估系统字段。
3. 按 `testing.md` 中 full-integration 命令执行 smoke checks，重点覆盖创建页候选项、specific/unlimited 编排分支、详情展示与编辑期单系统锁定。

## Verification Results
- smoke_test: pass
- key_features: ACC-001 至 ACC-005 在 parent feature 分支上的 full-integration 验证均已通过，覆盖创建、持久化、编排、详情展示与编辑锁定闭环。
- performance: 本次仅涉及条件分支与页面展示调整，针对性自动化验证中未观察到新增性能回归信号。

## Acceptance Conclusion

此部分总结 testing.md 中的验收结果：

**字段定义**：
- `status`: 最终验收状态
  - `pass`: 所有 approved acceptance 都有 test_scope=full-integration 且 result=pass 的记录，且所有 residual_risk 都不是 high
  - `fail`: 任何 approved acceptance 没有通过或有 residual_risk=high（testing-coverage gate 会拒绝 residual_risk=high）
- `notes`: 部署结论和风险说明
- `approved_by`: 批准人
- `approved_at`: 批准日期

**前置条件**：
- testing.md 中每个 approved acceptance 都必须有至少一条 test_scope=full-integration 且 result=pass 的记录
- 所有 residual_risk 都已被评估和记录
- 没有 reopen_required=true 的测试记录（如果有，必须先重新开启 spec/design）

**与 testing.md 的对应关系**：
- deployment.md 的 status=pass 依赖于 testing.md 中所有 acceptance 的测试结果
- 只有当所有 acceptance 都通过 full-integration 测试时，才能标记为 pass

---

status: pass
notes: 所有 approved acceptance 均已有 full-integration pass 记录，`residual_risk` 均为 `low`，且不存在 `reopen_required=true` 的记录；当前变更满足作为 staging 发布基线的条件。
approved_by: codex
approved_at: 2026-04-20

## Rollback Plan
trigger_conditions:
  - 创建页无法正确提交 specific 或 unlimited 的待评估系统选择
  - specific 模式错误地进入系统识别链路，或 unlimited 模式失去既有多系统输出
  - 具体系统任务在编辑期仍可执行新增系统、重命名系统、删除系统或重新拆分
rollback_steps:
  1. 回退前端 `UploadPage`、`ReportPage`、`EditPage` 到上一个稳定版本，移除待评估系统输入、展示与单系统锁定 UI。
  2. 回退后端 `backend/api/routes.py` 与 `backend/agent/agent_orchestrator.py` 到不含 `target_system` 逻辑的稳定版本。
  3. 重新执行任务创建、详情查看和编辑页 smoke checks，确认 unlimited 多系统主路径恢复正常。

## Monitoring
metrics:
  - `POST /api/v1/tasks` 创建成功率，以及与 `target_system` 参数相关的 4xx/5xx 比例
  - specific 模式任务处理失败率，重点关注越权校验失败和零功能点失败占比
  - 编辑期系统级锁定接口的拒绝次数与异常返回率
alerts:
  - 创建接口连续出现待评估系统参数校验错误或任务落盘缺少 `target_system` 元数据
  - orchestrator specific 分支异常升高，或 unlimited 结果结构与既有多系统格式不兼容
  - 编辑页出现系统级操作入口回归，或后端锁定接口拒绝率异常波动

## Post-deployment Actions
- [x] update related docs
- [x] record lessons learned if needed
- [ ] archive change dossier to versions/
