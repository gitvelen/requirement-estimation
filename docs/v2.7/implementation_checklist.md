# v2.7 实现检查清单

| 项 | 值 |
|---|---|
| 版本号 | v2.7 |
| 当前阶段 | Implementation |
| 日期 | 2026-03-13 |
| 当前执行批次 | Batch 1（T001-T003） |
| 首个强制展示点 | T006（M1🏁）或更早跑通的后端核心流程里程碑 |
| 关联计划 | `docs/v2.7/plan.md` |

## 实现前检查
- [x] 已阅读相关现有代码/文档（`requirements.md` / `design.md` / `plan.md` / `status.md` / `.aicoding/phases/05-implementation.md`）
- [x] 已对齐范围与“不做什么”
- [x] 已明确验收标准（以 T001-T003 对应 REQ/API/TEST 与命令级验证为准）
- [x] 已明确影响面：先聚焦 schema / Runtime / Memory 基座、PM 文档导入 Runtime、服务治理导入三条后端主线
- [x] 如涉及线上行为变化：已明确四个开关与回滚思路（`ENABLE_V27_PROFILE_SCHEMA` / `ENABLE_V27_RUNTIME` / `ENABLE_SERVICE_GOVERNANCE_IMPORT` / `ENABLE_SYSTEM_CATALOG_PROFILE_INIT`）
- [ ] 开发环境就绪：依赖安装、测试数据与必要配置已实际验证可运行
- [ ] 基线测试已记录：进入 TDD 前先确认当前相关测试基线

## 当前批次任务
- [ ] T001：v2.7 canonical schema、Memory/Execution 存储与开关基座
- [ ] T002：Skill Runtime、Policy Gate 与 PM 文档导入链路
- [ ] T003：服务治理导入改造为 admin 全局画像联动

## 实现中检查
- [ ] 按 TDD 执行：每个行为先补失败测试，再写最小实现
- [ ] 不跨任务隐式扩 scope；T001~T003 之外的改动只允许为明确依赖或编译修复
- [ ] 未引入非必要依赖；依赖变更持续对照 `REQ-C007`
- [ ] 关键路径校验：鉴权、输入校验、错误码、`failed/partial_success`、`manual` 冲突处理口径一致
- [ ] 安全检查：`repo_path`、文件上传、admin 权限与系统名匹配逻辑不降级
- [ ] 数据变更可回滚：旧 schema 不再新写入，但保留回滚开关与备份恢复路径
- [ ] 里程碑纪律：T006（🏁）完成前必须暂停并向 User 展示后端 Runtime / Skill / 治理导入核心结果

## 实现后检查
- [ ] 当前批次代码可正常运行
- [ ] 当前批次对应测试通过并记录命令输出
- [ ] 对照验收标准自测并留证据（命令、日志、必要时截图）
- [ ] 文档同步更新：如实现改变了 design/plan 假设，先停下确认；不自行改验收标准
- [ ] 敏感信息检查：不提交 secret、生产数据、个人信息

## 契约与集成验证（进入 Testing 前）

### API 契约一致性
- [ ] 前端 API 调用、后端路由与 `design.md` 5.4 契约已逐项对齐
- [ ] 所有新增 API 已在 `design.md` 中定义
- [ ] 当前仓库未发现 `scripts/validate_api_contracts.sh`；进入 Testing 前需补齐等价契约校验脚本或明确改用其他可复现命令

### 集成测试准备
- [ ] T001-T003 对应集成测试已补齐到可独立执行
- [ ] 测试脚本覆盖 API 调用、数据副作用与存储校验
- [ ] 测试脚本已验证通过并记录日志

### 人类验证准备（关键流程）
- [ ] 已准备后端核心流程里程碑展示材料（关键输入 -> 输出）
- [ ] 已准备 T006（🏁）展示项：6 个 Skill 注册定义、Scene 路由、服务治理导入与 execution 跟踪结果
