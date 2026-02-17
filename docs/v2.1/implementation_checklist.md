# v2.1 实现检查清单

## 文档元信息
| 项 | 值 |
|---|---|
| 状态 | Done |
| 作者 | AI |
| 日期 | 2026-02-12 |
| 版本 | v0.1 |
| 关联计划 | `docs/v2.1/plan.md` v0.3 |
| 关联需求 | `docs/v2.1/requirements.md` v0.3 |

## 实现前检查
- [x] 已阅读相关现有代码/文档（requirements/design/plan）
- [x] 已对齐范围与"不做什么"（避免范围漂移）
- [x] 已明确验收标准（可测试、可复现）
- [x] 已明确影响面：后端 API/服务 + 前端 8 个页面 + 文档状态流转
- [x] 已明确开关与回滚策略（`V21_*` Feature Flags + `data/` 快照恢复）
- [x] 开发环境就绪
  - [x] Python/Node 依赖可用
  - [x] 后端测试可运行
  - [x] 前端测试/构建可运行

## 实现中检查
- [x] 代码改动与 v2.1 需求保持一致（REQ-001~009、REQ-015~022）
- [x] 未引入非必要依赖
- [x] 关键路径包含权限/输入校验（画像权限、dashboard 参数）
- [x] 向后兼容受控（`filters.ai_involved` 兼容忽略；旧 modifications 记录可读）
- [x] 数据源统一到 `data/system_list.csv` / `data/subsystem_list.csv`

## 实现后检查
- [x] 代码可正常运行
- [x] 后端测试通过：`.venv/bin/pytest -q`（86 passed）
- [x] 前端测试通过：`cd frontend && CI=true npm test -- --watchAll=false`（4 passed）
- [x] 前端构建通过：`cd frontend && npm run build`（Compiled successfully）
- [x] 关键验收点可复现：
  - [x] 看板 API v2.1 指标：`tests/test_dashboard_metrics_v21.py`
  - [x] 画像 4 字段与权限：`tests/test_system_profile_v21_fields.py`、`tests/test_system_profile_permissions.py`
  - [x] 修改记录兼容：`tests/test_task_modification_compat.py`
  - [x] UI 冗余文案清理：`rg -n "subtitle=|当前视角：|配置管理\s*→" frontend/src/pages -g "*.js"`

## 变更记录
| 版本 | 日期 | 说明 |
|---|---|---|
| v0.1 | 2026-02-12 | Implementation 阶段完成，覆盖 T001~T008 并补齐 T008 兼容性验证用例 |
