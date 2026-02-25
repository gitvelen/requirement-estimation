# v2.2 实现检查清单

> 目的：在 Implementation 阶段落地“按计划逐项实现 + 可回滚 + 可验收证据”的闭环；并按 `.aicoding/phases/05-implementation.md` 要求提供“旧版功能→新版覆盖状态”对照清单。

## 功能对照清单（v2.1 → v2.2）

| 功能/入口（v2.1） | v2.2 目标形态 | 兼容/替代策略 | 关联任务 | 关联需求 |
|---|---|---|---|---|
| 效能看板 `/dashboard?page=overview|system|flow|rankings|ai` | `/dashboard/rankings` + `/dashboard/reports` | `/dashboard` 与旧 `page=` 统一 replace 重定向；`page=ai` 仅提示“AI效果报告已下线” | T001,T003 | REQ-002, REQ-003, REQ-004, REQ-012, REQ-013, REQ-102, REQ-C007, REQ-C008 |
| AI效果报告 `/reports/ai-effect` | 下线（无入口） | 访问旧 URL replace 到 `/dashboard/reports` + 一次性提示“AI效果报告已下线” | T001 | REQ-012, REQ-C007 |
| 任务管理 `/tasks`（页面内 Tab：进行中/已完成） | 子菜单：`/tasks/ongoing`、`/tasks/completed` | `/tasks` 与 `/tasks?tab=` 统一 replace 重定向 | T001,T004 | REQ-005, REQ-013, REQ-102 |
| 任务详情页（含报告版本列表区域） | 摘要聚合 + “下载报告”下拉 | 保留历史报告下载能力，入口改为 Dropdown；无报告置灰提示 | T005 | REQ-006, REQ-C003 |
| PM 编辑页（可编辑预估人天/无确认门禁） | 预估人天只读 + 实质性修改需确认 + 触发重评估 | 前后端双重约束（后端兜底门禁） | T006,T007 | REQ-007, REQ-C001, REQ-C002 |
| 系统画像-知识导入（标题/入口形态分散） | 页面内 Tab：代码扫描/文档导入；5 类文档类型 | 非 ESB 复用 `/api/v1/knowledge/imports` + `doc_type`；ESB 走 `/api/v1/esb/imports` | T009,T010 | REQ-008, REQ-009, REQ-C006 |
| ESB 导入后检索/过滤/统计（FUNC-018） | 保留并对齐：include_deprecated/scope/统计面板 | 新增 `GET /api/v1/esb/search` + `GET /api/v1/esb/stats`；import 返回 `mapping_resolved` 供提示/预览 | T009,T010 | REQ-009 |
| 专家评估页右侧 COSMIC 常驻卡片 | 顶部“?”图标 + 弹层 | 移除右侧大卡片，弹层可滚动/可关闭且不遮挡关键按钮 | T011 | REQ-010 |
| 备注字段（功能点级 `备注` / AI备注机制分散） | 任务级 `remark`（多行、倒序、只读展示） | 触发点覆盖 PM 保存/专家提交/AI 重评估完成；不破坏 v2.1 存量 | T008,T005 | REQ-011, REQ-C003 |

## 实现前检查
- [x] 已阅读相关现有代码/文档（`docs/v2.2/requirements.md`、`docs/v2.2/design.md`、`docs/v2.2/plan.md`、`docs/v2.2/status.md`）
- [x] 已对齐范围与"不做什么"（以 requirements 的 Out of Scope 为准）
- [x] 已明确验收标准（GWT 粒度，可判定、可复现）
- [x] 已明确影响面：路由/菜单、看板、任务管理、编辑门禁、ESB、备注
- [x] 开发环境就绪（进入代码实现后补齐证据）：
  - [x] `backend` 单测可运行（`pytest -q`）
  - [x] `frontend` 可构建（`cd frontend && npm run build`）

## 实现中检查
- [x] 任务按 `docs/v2.2/plan.md` 顺序推进，避免隐式扩 scope
- [x] 关键路径：鉴权/输入校验/错误码一致/幂等（如适用）
- [x] 兼容与回滚：旧 URL replace；高风险点可回退到 v2.1
- [x] REQ-C 禁止项对抗性自检：入口是否可能“漏出”（动态渲染/条件分支/隐藏但可点击）

## 实现后检查
- [x] 关键验证命令通过并可复现（记录到 `docs/v2.2/review_implementation.md` 的证据列）
- [x] 产出 `docs/v2.2/review_implementation.md`（REQ 模式：逐条 GWT 判定 + 摘要块）
