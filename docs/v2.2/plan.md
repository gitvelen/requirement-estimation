# v2.2 综合优化升级 任务计划

## 文档元信息
| 项 | 值 |
|---|---|
| 状态 | In Progress |
| 日期 | 2026-02-25 |
| 版本 | v0.4 |
| 基线版本（对比口径） | `v2.1` |
| Active CR（如有） | `CR-20260225-001` |
| 关联设计 | `docs/v2.2/design.md`（v0.3） |
| 关联需求 | `docs/v2.2/requirements.md`（v0.3） |
| 关联状态 | `docs/v2.2/status.md` |

## 里程碑
| 里程碑 | 交付物 | 截止日期 |
|---|---|---|
| M1 | 路由/菜单重构（含旧 URL 兼容）+ 看板页面拆分（含近90天固定口径） | TBD |
| M2 | 任务详情页重构 + PM 编辑门禁（confirm 强制 + 预估人天只读） | TBD |
| M3 | 系统画像导入页 Tab 化 + ESB 检索/统计面板 + remark 自动生成 | TBD |
| M4 | 全量回归（REQ-C/兼容/死链）+ 主文档同步 + 部署记录 | TBD |

## Definition of Done（DoD）
- [x] 需求可追溯：任务关联 `REQ/SCN/API/TEST` 清晰
- [x] 代码可运行：不破坏主流程，旧 URL 兼容且无回退死循环
- [x] 自测通过：列出验证命令/用例与结果
- [x] 安全与合规：鉴权/输入校验/敏感信息不落盘
- [x] 文档同步：Deployment 阶段同步主文档（REQ-014）

## 禁止项引用索引（来源：requirements.md REQ-C 章节）

| REQ-C ID | 一句话摘要 |
|----------|-----------|
| REQ-C001 | PM 在功能点编辑页“预估人天”只读/不可提交修改 |
| REQ-C002 | 实质性修改必须确认；未确认不落库、不触发重评估 |
| REQ-C003 | v2.1 存量任务/报告在 v2.2 可继续访问与下载 |
| REQ-C004 | 菜单/路由无死链（无 404/空白页） |
| REQ-C005 | 不引入 DB schema 迁移/DDL（允许 JSON schema 增量字段） |
| REQ-C006 | 文档导入仅单文件上传（无批量入口） |
| REQ-C007 | 禁止保留“AI表现/AI效果报告”入口（仅允许下线提示） |
| REQ-C008 | 排行榜统计周期固定近90天且不可配置（含固定说明文案） |

## 任务概览
### 状态标记规范
- `待办` - 未开始
- `进行中` - 正在处理
- `已完成` - 实现完成，自测通过

| 任务分类 | 任务ID | 任务名称 | 优先级 | 预估工时 | Owner | Reviewer | 关联CR（可选） | 关联需求项 | 任务状态 | 依赖任务ID | 验证方式 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 前端 | T001 | 菜单与路由重构（看板/任务子菜单 + 旧 URL replace 重定向） | P0 | 8h | 默认 | AI-Reviewer | — | REQ-002, REQ-005, REQ-012, REQ-013, REQ-102, REQ-C004, REQ-C007 | 已完成 | — | npm build + 手工回退验证 |
| 后端 | T002 | 看板统计窗口固定近90天 + Rankings 口径补齐 | P0 | 8h | 默认 | AI-Reviewer | — | REQ-003, REQ-C008 | 已完成 | — | pytest（dashboard） |
| 前端 | T003 | 看板拆分：/dashboard/rankings + /dashboard/reports（3卡片） | P0 | 10h | 默认 | AI-Reviewer | — | REQ-001, REQ-002, REQ-003, REQ-004, REQ-012, REQ-101, REQ-C007, REQ-C008 | 已完成 | T001,T002 | npm build + 关键页面巡检 |
| 前端 | T004 | 任务列表子菜单化（ongoing/completed）+ 旧 tab 参数兼容 | P0 | 6h | 默认 | AI-Reviewer | — | REQ-001, REQ-005, REQ-013, REQ-101, REQ-102, REQ-C004 | 已完成 | T001 | npm build + 手工回退验证 |
| 前端 | T005 | 任务详情页重构：摘要聚合 + 下载报告下拉 + remark 只读展示 | P0 | 10h | 默认 | AI-Reviewer | — | REQ-006, REQ-011, REQ-101, REQ-C003 | 已完成 | T001 | npm build + 报告下载回归 |
| 后端 | T006 | PM 编辑后端门禁：confirm 强制 + PM 预估人天只读 + 新增功能点默认空 | P0 | 12h | 默认 | AI-Reviewer | — | REQ-007, REQ-C001, REQ-C002, REQ-C003 | 已完成 | — | pytest（features/systems） |
| 前端 | T007 | PM 编辑前端交互：保存并确认 + 重评估触发 + 预估人天只读 | P0 | 10h | 默认 | AI-Reviewer | — | REQ-007, REQ-011, REQ-101, REQ-C001, REQ-C002 | 已完成 | T006 | npm build + 手工流程回归 |
| 后端 | T008 | remark 自动生成（任务级，多行、倒序）并覆盖 PM/专家/AI 重评估触发点 | P1 | 10h | 默认 | AI-Reviewer | — | REQ-011, REQ-C003 | 已完成 | T006 | pytest（reevaluate/mod） |
| 前后端 | T009 | 系统画像导入页重设计：Tab 化 + 5类文档导入 + ESB 面板（检索/过滤/统计） | P0 | 16h | 默认 | AI-Reviewer | — | REQ-001, REQ-008, REQ-009, REQ-101, REQ-C006 | 已完成 | T001 | pytest + npm build + 手工验收 |
| 后端 | T010 | ESB 接口补齐：search/stats + import 返回 mapping_resolved | P0 | 10h | 默认 | AI-Reviewer | — | REQ-009 | 已完成 | — | pytest（esb） |
| 前端 | T011 | 专家评估页 COSMIC 入口调整（“?” 图标 + 弹层） | P1 | 4h | 默认 | AI-Reviewer | — | REQ-010, REQ-101 | 已完成 | — | npm build + 手工验收 |
| 质量保障 | T012 | REQ-C 全量回归：兼容/死链/无 DB 迁移证明 | P0 | 10h | 默认 | AI-Reviewer | — | REQ-C003, REQ-C004, REQ-C005, REQ-102 | 已完成 | T001~T011 | pytest + 菜单巡检清单 |
| 文档 | T013 | Deployment 阶段主文档同步清单落地 | P1 | 6h | 默认 | AI-Reviewer | — | REQ-014 | 已完成 | T012 | 文档 diff 审查 |
| 前后端+文档 | T014 | 收口后可读性与紧凑布局优化追溯补记 | P1 | 8h | 默认 | AI-Reviewer | CR-20260225-001 | REQ-004, REQ-006, REQ-007, REQ-010, REQ-101 | 已完成 | T013 | 前端回归测试 + npm build + CR 文档链路自检 |

### 引用自检（🔴 MUST，R6）
```bash
VERSION="v2.2"

# plan 引用的 REQ
rg -o "REQ-C?[0-9]+" docs/${VERSION}/plan.md | LC_ALL=C sort -u > /tmp/plan_refs_${VERSION}.txt

# requirements 定义的 REQ（仅从定义行提取）
rg "^#### REQ-C?[0-9]+[：:]" docs/${VERSION}/requirements.md | sed 's/^#### //;s/[：:].*$//' | tr -d '\r' | LC_ALL=C sort -u > /tmp/req_defs_${VERSION}.txt

# plan 引用了但 requirements 未定义（期望为空）
LC_ALL=C comm -23 /tmp/plan_refs_${VERSION}.txt /tmp/req_defs_${VERSION}.txt

# requirements 定义了但 plan 未覆盖（期望为空）
LC_ALL=C comm -23 /tmp/req_defs_${VERSION}.txt /tmp/plan_refs_${VERSION}.txt
```

## 任务详情

### T001：菜单与路由重构（看板/任务子菜单 + 旧 URL replace 重定向）
**分类**：前端  
**优先级**：P0  
**预估工时**：8h  
**Owner**：默认  
**Reviewer（可选）**：AI-Reviewer

**关联需求项**：REQ-002、REQ-005、REQ-012、REQ-013、REQ-102、REQ-C004、REQ-C007

**任务描述**：
- 侧边栏菜单改造：
  - “效能看板”仅保留两个子菜单：排行榜（`/dashboard/rankings`）/多维报表（`/dashboard/reports`）
  - “任务管理”仅保留两个子菜单：进行中（`/tasks/ongoing`）/已完成（`/tasks/completed`）
  - 系统画像子菜单第二项改名为“信息展示”（REQ-008-03）
- 旧 URL 兼容重定向（全部使用 replace，避免回退死循环）：
  - `/dashboard` → `/dashboard/reports`
  - `/dashboard?page=rankings` → `/dashboard/rankings`
  - `/dashboard?page=overview|system|flow` → `/dashboard/reports`
  - `/dashboard?page=ai` → `/dashboard/reports` + 一次性提示“AI效果报告已下线”
  - `/reports/ai-effect` → `/dashboard/reports` + 一次性提示“AI效果报告已下线”
  - `/tasks` → `/tasks/ongoing`
  - `/tasks?tab=ongoing|completed` → `/tasks/ongoing|completed`

**影响面/修改范围**：
- 影响模块：React Router、MainLayout Menu 结构、Legacy Redirect 逻辑
- 预计修改文件：
  - `frontend/src/App.js`
  - `frontend/src/components/MainLayout.js`
  - （可选）新增：`frontend/src/pages/LegacyRedirects/*.js`

**验收标准**：
- [ ] 菜单结构满足 GWT-REQ-002-01、GWT-REQ-005-01
- [ ] 旧 URL 重定向覆盖满足 GWT-REQ-013-01~05、GWT-REQ-012-01、GWT-REQ-102-01
- [ ] 页面/菜单不出现“AI表现/AI效果报告”入口（REQ-C007）

**验证方式（🔴 MUST，可复现）**：
- 命令：`cd frontend && npm run build`
- 人工：浏览器验证 back 行为（按 requirements 的 GWT-REQ-102-01 执行）

**回滚/开关策略**：
- 回滚条件：出现 404/空白页/回退死循环
- 回滚步骤：回退前端版本到 v2.1

**依赖**：—

---

### T002：看板统计窗口固定近90天 + Rankings 口径补齐
**分类**：后端  
**优先级**：P0  
**预估工时**：8h  
**Owner**：默认  
**Reviewer（可选）**：AI-Reviewer

**关联需求项**：REQ-003、REQ-C008

**任务描述**：
- Dashboard Query 支持固定近90天口径：
  - 后端新增 `time_range=last_90d` 枚举解析（或服务端忽略前端时间选择直接强制 90 天）
  - 统一以 `frozen_at` 落入窗口为统计口径
- Rankings 返回 3 个 Tab 所需数据（REQ-003）：
  - 评估效率排行（按 expert 聚合）
  - 任务提交排行（按 manager/creator 聚合）
  - 系统活跃排行（按 system 聚合）

**影响面/修改范围**：
- 预计修改文件：
  - `backend/api/routes.py`（`/api/v1/efficiency/dashboard/query`、`_parse_dashboard_time_window` 等）
  - `tests/test_dashboard_query_api.py`
  - （如需）新增：`tests/test_dashboard_rankings_v22.py`

**验收标准**：
- [ ] 后端对 `last_90d` 解析正确；不再依赖 `last_30d/this_month` 等可配置窗口（REQ-C008）
- [ ] 能输出 3 个排行 Tab 的数据集合，且可被前端渲染

**验证方式（🔴 MUST，可复现）**：
- 命令：`pytest -q tests/test_dashboard_query_api.py`

**回滚/开关策略**：
- 回滚条件：看板接口 400/500 或口径异常
- 回滚步骤：回退后端版本到 v2.1

**依赖**：—

---

### T003：看板拆分：/dashboard/rankings + /dashboard/reports（3卡片）
**分类**：前端  
**优先级**：P0  
**预估工时**：10h  
**Owner**：默认  
**Reviewer（可选）**：AI-Reviewer

**关联需求项**：REQ-001、REQ-002、REQ-003、REQ-004、REQ-012、REQ-101、REQ-C007、REQ-C008

**任务描述**：
- 新增/拆分两页并移除旧“看板页面内 Tab”信息架构：
  - `/dashboard/rankings`：3 个排行 Tab（评估效率/任务提交/系统活跃）+ 固定“计算逻辑：…近90天…”文案
  - `/dashboard/reports`：3 张卡片（总览统计/系统影响分析/流程健康度），并确保页面文本包含指标名（修正率/命中率/画像贡献；评估周期/偏差监控/学习趋势）
- 移除所有“AI表现/AI效果报告”作为独立页面入口（REQ-012、REQ-C007）
- 统一页面状态（REQ-101）：Loading/Empty/Error/Retry

**影响面/修改范围**：
- 预计修改文件：
  - `frontend/src/pages/EfficiencyDashboardPage.js`（拆分/重构或替换）
  - （建议新增）`frontend/src/pages/DashboardRankingsPage.js`
  - （建议新增）`frontend/src/pages/DashboardReportsPage.js`
  - `frontend/src/App.js`
  - `frontend/src/components/MainLayout.js`

**验收标准**：
- [ ] 满足 GWT-REQ-002-01/02、GWT-REQ-003-01/02/03、GWT-REQ-004-01~04、GWT-REQ-012-01、GWT-REQ-C008-01

**验证方式（🔴 MUST，可复现）**：
- 命令：`cd frontend && npm run build`
- 人工：检查页面文案包含要求指标名（GWT-REQ-004-02/03）

**依赖**：T001,T002

---

### T004：任务列表子菜单化（ongoing/completed）+ 旧 tab 参数兼容
**分类**：前端  
**优先级**：P0  
**预估工时**：6h  
**Owner**：默认  
**Reviewer（可选）**：AI-Reviewer

**关联需求项**：REQ-001、REQ-005、REQ-013、REQ-101、REQ-102、REQ-C004

**任务描述**：
- 新路由：
  - `/tasks/ongoing`：进行中（pending+in_progress）
  - `/tasks/completed`：已完成（completed+closed）
- 移除任务列表页内 Tab 切换；由路由决定展示集合
- 旧入口兼容：
  - `/tasks` → `/tasks/ongoing`（replace）
  - `/tasks?tab=ongoing|completed` → 对应新路由（replace）
- 去除任务列表页 PageHeader（REQ-001）
- 统一页面状态（REQ-101）

**影响面/修改范围**：
- 预计修改文件：
  - `frontend/src/App.js`
  - `frontend/src/pages/TaskListPage.js`

**验收标准**：
- [ ] 满足 GWT-REQ-005-01/02/03、GWT-REQ-013-01/05、GWT-REQ-102-01、GWT-REQ-C004-01

**验证方式（🔴 MUST，可复现）**：
- 命令：`cd frontend && npm run build`
- 人工：回退验证（/tasks?tab=completed 重定向后 back 不死循环）

**依赖**：T001

---

### T005：任务详情页重构：摘要聚合 + 下载报告下拉 + remark 只读展示
**分类**：前端  
**优先级**：P0  
**预估工时**：10h  
**Owner**：默认  
**Reviewer（可选）**：AI-Reviewer

**关联需求项**：REQ-006、REQ-011、REQ-101、REQ-C003

**任务描述**：
- ReportPage 布局重构：
  - 摘要卡片聚合：任务状态、创建时间、提交人、系统名称、功能点数量、专家评估状态（已评/待评/总数）、当前评估轮次（REQ-006）
  - “下载报告”改为 Dropdown：包含“最新报告”与历史版本项；无报告版本时置灰并提示“暂无可下载报告”
  - 移除独立“任务详情/专家评估进度/报告版本列表”区域（REQ-006-04）
- remark 只读展示（REQ-011）：显示任务级 `remark`（多行，时间倒序）；无输入框/编辑入口
- 统一页面状态（REQ-101）

**影响面/修改范围**：
- 预计修改文件：
  - `frontend/src/pages/ReportPage.js`
  - （如需）`frontend/src/components/*`（Dropdown/Empty/Alert 复用）

**验收标准**：
- [ ] 满足 GWT-REQ-006-01~04、GWT-REQ-011-02、GWT-REQ-C003-01

**验证方式（🔴 MUST，可复现）**：
- 命令：`cd frontend && npm run build`
- 后端回归：`pytest -q tests/test_report_download_api.py`

**依赖**：T001

---

### T006：PM 编辑后端门禁：confirm 强制 + PM 预估人天只读 + 新增功能点默认空
**分类**：后端  
**优先级**：P0  
**预估工时**：12h  
**Owner**：默认  
**Reviewer（可选）**：AI-Reviewer

**关联需求项**：REQ-007、REQ-C001、REQ-C002、REQ-C003

**任务描述**：
- 后端接口统一支持 `confirm` 参数（body 或 query），并按 design.md §5.5.2 判定“实质性修改”
- PM（manager）写入限制（REQ-C001）：
  - 禁止修改既有功能点的“预估人天”
  - 新增功能点时“预估人天”强制落空（不接受客户端默认值）
- confirm 门禁（REQ-C002）：
  - 实质性修改未确认 → 400 拒绝，且不产生任何持久化变更、不触发重评估
- 向后兼容（REQ-C003）：不破坏 v2.1 存量任务读取与报告下载

**影响面/修改范围**：
- 预计修改文件：
  - `backend/api/routes.py`（`update_features`、systems add/rename/delete）
  - `tests/test_task_feature_update_actor.py`
  - （建议新增）`tests/test_task_feature_confirm_gate_v22.py`

**验收标准**：
- [ ] 满足 GWT-REQ-007-01/02/03、GWT-REQ-C001-01、GWT-REQ-C002-01、GWT-REQ-C003-01

**验证方式（🔴 MUST，可复现）**：
- 命令：`pytest -q tests/test_task_feature_update_actor.py`

**依赖**：—

---

### T007：PM 编辑前端交互：保存并确认 + 重评估触发 + 预估人天只读
**分类**：前端  
**优先级**：P0  
**预估工时**：10h  
**Owner**：默认  
**Reviewer（可选）**：AI-Reviewer

**关联需求项**：REQ-007、REQ-011、REQ-101、REQ-C001、REQ-C002

**任务描述**：
- EditPage 改造：
  - “预估人天”对 PM 只读（列/表单禁用或隐藏，仅展示）
  - 新增功能点时预估人天默认值为空（不再默认 1/2.5）
  - 实质性修改检测：add/delete/核心字段变更/系统 Tab 增改删 → 仅允许“保存并确认”路径
  - “保存并确认”弹窗确认后：
    - 调用对应保存接口携带 `confirm=true`
    - 成功后触发 `POST /api/v1/tasks/{task_id}/reevaluate`
  - 非实质性修改（如排序）允许普通保存：不弹窗、不触发重评估（REQ-007-03）
- 统一页面状态（REQ-101）

**影响面/修改范围**：
- 预计修改文件：`frontend/src/pages/EditPage.js`

**验收标准**：
- [ ] 满足 GWT-REQ-007-01/02/03、GWT-REQ-011-03、GWT-REQ-C001-01、GWT-REQ-C002-01

**验证方式（🔴 MUST，可复现）**：
- 命令：`cd frontend && npm run build`
- 后端回归：`pytest -q tests/test_task_reevaluate_api.py`

**依赖**：T006

---

### T008：remark 自动生成（任务级，多行、倒序）并覆盖 PM/专家/AI 重评估触发点
**分类**：后端  
**优先级**：P1  
**预估工时**：10h  
**Owner**：默认  
**Reviewer（可选）**：AI-Reviewer

**关联需求项**：REQ-011、REQ-C003

**任务描述**：
- 数据模型：在 task 上维护 `remark`（text，多行），新摘要行置顶
- 触发点：
  - PM 保存（普通保存/保存并确认）追加 “PM” 摘要行
  - 专家提交评估成功追加 “专家” 摘要行
  - AI 重评估完成追加 “AI重评估” 摘要行
- 兼容策略：保留历史人工备注；不破坏 v2.1 存量数据（REQ-C003）

**影响面/修改范围**：
- 预计修改文件：
  - `backend/api/routes.py`
  - `tests/test_task_reevaluate_api.py`
  - （建议新增）`tests/test_task_remark_v22.py`

**验收标准**：
- [ ] 满足 GWT-REQ-011-01/02/03/04

**验证方式（🔴 MUST，可复现）**：
- 命令：`pytest -q tests/test_task_reevaluate_api.py`

**依赖**：T006

---

### T009：系统画像导入页重设计：Tab 化 + 5类文档导入 + ESB 面板（检索/过滤/统计）
**分类**：前后端  
**优先级**：P0  
**预估工时**：16h  
**Owner**：默认  
**Reviewer（可选）**：AI-Reviewer

**关联需求项**：REQ-001、REQ-008、REQ-009、REQ-101、REQ-C006

**任务描述**：
- Import 页改为“代码扫描/文档导入”两个 Tab（REQ-008）
- 文档导入统一为 5 种类型下拉（需求/设计/技术方案/历史评估报告/ESB接口文档），且仅单文件上传（REQ-C006）
- 非 ESB 文档导入复用 `POST /api/v1/knowledge/imports`，新增 `doc_type`（metadata），并保持向后兼容（REQ-008）
- ESB 导入保留 mapping_json，导入结果展示列映射预览/提示 + 导入统计（REQ-009）
- ESB 导入后提供检索/过滤/统计面板（include_deprecated/scope/计数）（REQ-009）
- 统一页面状态（REQ-101）+ 移除 PageHeader（REQ-001）

**影响面/修改范围**：
- 预计修改文件：
  - `frontend/src/pages/SystemProfileImportPage.js`
  - `backend/api/knowledge_routes.py`
  - `backend/api/esb_routes.py`
  - （如需）`backend/service/esb_service.py`
  - `tests/test_knowledge_import_api.py`

**验收标准**：
- [ ] 满足 GWT-REQ-008-01/02/03、GWT-REQ-009-01/02、GWT-REQ-C006-01

**验证方式（🔴 MUST，可复现）**：
- 命令：`pytest -q tests/test_knowledge_import_api.py`
- 命令：`cd frontend && npm run build`

**依赖**：T001

---

### T010：ESB 接口补齐：search/stats + import 返回 mapping_resolved
**分类**：后端  
**优先级**：P0  
**预估工时**：10h  
**Owner**：默认  
**Reviewer（可选）**：AI-Reviewer

**关联需求项**：REQ-009

**任务描述**：
- 新增 `GET /api/v1/esb/search`：
  - `q/system_id/scope/include_deprecated/top_k` 参数
  - 权限：owner/B角 + admin 放行
- 新增 `GET /api/v1/esb/stats`：
  - 统计：active/deprecated/unique service + 可选 system_summary
- ESB import 响应补充 `mapping_resolved`（字段→最终匹配列名），用于前端“映射结果提示/预览”

**影响面/修改范围**：
- 预计修改文件：
  - `backend/api/esb_routes.py`
  - `backend/service/esb_service.py`
  - `tests/test_esb_import_api.py`
  - （建议新增）`tests/test_esb_search_stats_api_v22.py`

**验收标准**：
- [ ] 满足 GWT-REQ-009-01/02

**验证方式（🔴 MUST，可复现）**：
- 命令：`pytest -q tests/test_esb_import_api.py`

**依赖**：—

---

### T011：专家评估页 COSMIC 入口调整（“?” 图标 + 弹层）
**分类**：前端  
**优先级**：P1  
**预估工时**：4h  
**Owner**：默认  
**Reviewer（可选）**：AI-Reviewer

**关联需求项**：REQ-010、REQ-101

**任务描述**：
- 移除右侧常驻 COSMIC 卡片
- 顶部增加 “?” 图标（Tooltip/Popover），点击展示规则详情（Modal/Drawer/Popover），可滚动、可关闭、不遮挡关键按钮
- 统一页面状态（REQ-101）

**影响面/修改范围**：
- 预计修改文件：`frontend/src/pages/EvaluationPage.js`

**验收标准**：
- [ ] 满足 GWT-REQ-010-01/02

**验证方式（🔴 MUST，可复现）**：
- 命令：`cd frontend && npm run build`

**依赖**：—

---

### T012：REQ-C 全量回归：兼容/死链/无 DB 迁移证明
**分类**：质量保障  
**优先级**：P0  
**预估工时**：10h  
**Owner**：默认  
**Reviewer（可选）**：AI-Reviewer

**关联需求项**：REQ-C003、REQ-C004、REQ-C005、REQ-102

**任务描述**：
- v2.1 存量数据回归抽样（任务列表/任务详情/报告下载）（REQ-C003）
- 全量菜单巡检（含子菜单与旧 URL 重定向）（REQ-C004/REQ-102）
- 证明不引入 DB 迁移/DDL（REQ-C005）：代码检索 + diff 说明（仅允许 JSON schema 增量字段）

**验收标准**：
- [ ] 满足 GWT-REQ-C003-01、GWT-REQ-C004-01、GWT-REQ-C005-01、GWT-REQ-102-01

**验证方式（🔴 MUST，可复现）**：
- 命令：`pytest -q`
- 命令：`rg -n \"migrate|alembic|DDL|CREATE TABLE|ALTER TABLE\" -S backend | head`
- 人工：按菜单清单逐个点击（输出清单记录到 test_report）

**依赖**：T001~T011

---

### T013：Deployment 阶段主文档同步清单落地
**分类**：文档  
**优先级**：P1  
**预估工时**：6h  
**Owner**：默认  
**Reviewer（可选）**：AI-Reviewer

**关联需求项**：REQ-014

**任务描述**：
- 同步主文档（以 v2.2 实际上线行为为准）：
  - `docs/系统功能说明书.md`：移除/标记 FUNC-022（AI效果报告）入口与描述
  - `docs/接口文档.md`：旧 URL 兼容说明、废弃参数说明
  - `docs/用户手册.md`：更新导航结构与报告下载入口说明
  - `docs/部署记录.md`：追加上线与回滚记录

**影响面/修改范围**：
- 预计修改文件：`docs/*.md`

**验收标准**：
- [ ] `docs/` 主文档与 v2.2 实际行为一致（不允许“入口漂移”）

**验证方式**：
- 验证方式：人工确认（diff 审查 + spotcheck）

**依赖**：T012

---

### T014：收口后可读性与紧凑布局优化追溯补记
**分类**：前后端+文档  
**优先级**：P1  
**预估工时**：8h  
**Owner**：默认  
**Reviewer（可选）**：AI-Reviewer  
**关联CR**：CR-20260225-001

**关联需求项**：REQ-004、REQ-006、REQ-007、REQ-010、REQ-101

**任务描述**：
- 在项目收口后，针对用户连续反馈的问题执行增量优化并补齐追溯：
  - PM 保存异常报错可读化（避免 `[object Object]`）；
  - 多维报表指标文案与布局紧凑化（单行展示、释义强化）；
  - 系统清单/COSMIC 页面头部布局一行化；
  - 任务详情分析区去折叠与冗余标题清理；
  - 在 `status.md/plan.md/test_report.md/cr/` 中补齐 CR 追溯链路。

**影响面/修改范围**：
- `backend/api/routes.py`
- `frontend/src/pages/*.js`
- `frontend/src/utils/*.js`
- `frontend/src/__tests__/*.test.js`
- `tests/*.py`
- `docs/v2.2/*.md` 与 `docs/v2.2/cr/*.md`

**验收标准**：
- [ ] CR 文档与 status/plan/test_report 三处引用一致可追溯。
- [ ] 关键页面布局满足“减少折叠、减少冗余标题、操作区更紧凑”的反馈目标。
- [ ] 增量回归测试与构建通过。

**验证方式（🔴 MUST，可复现）**：
- 命令：`cd frontend && npm test -- --watch=false --runInBand src/__tests__/dashboardMetrics.test.js src/__tests__/navigationAndPageTitleRegression.test.js`
- 命令：`cd frontend && npm run build`
- 命令：`rg -n "CR-20260225-001" docs/v2.2/status.md docs/v2.2/plan.md docs/v2.2/test_report.md docs/v2.2/cr/CR-20260225-001.md`

**依赖**：T013

---

## 执行顺序
1. T001 → T002 → T003 → T004
2. T006 → T007 → T008
3. T010 → T009
4. T005 → T011
5. T012 → T013 → T014

## 风险与缓解
| 风险 | 影响 | 概率 | 缓解措施 |
|---|---|---|---|
| 路由/菜单改造导致死链或回退死循环 | 违反 REQ-C004/REQ-102，核心可用性受损 | 中 | 全部重定向使用 replace；T012 全量菜单巡检；必要时回退 v2.1 |
| confirm 门禁误判导致 PM 正常保存被拒绝 | 违反 REQ-007，影响编辑流程 | 中 | 后端按字段白名单判定；未知字段兜底“实质性”；联调后补齐负向用例 |
| ESB search/stats 权限口径不一致 | 403/越权风险 | 中 | 复用 esb_import 的 owner/B角校验；补齐 API 测试用例 |
| remark 生成影响存量任务展示 | 违反 REQ-C003 | 低 | 仅新增 task.remark 字段；前端展示空态兼容；回归抽样 |

## 开放问题
- [ ] 里程碑日期与 Owner/Reviewer 指派待用户确认（当前默认）

## 变更记录
| 版本 | 日期 | 说明 |
|---|---|---|
| v0.1 | 2026-02-24 | 初始化 v2.2 任务计划（覆盖 requirements 全量 REQ/REQ-C） |
| v0.4 | 2026-02-25 | 新增 CR-20260225-001 增量任务 T014，并更新 Active CR 与追溯验证命令 |
| v0.2 | 2026-02-24 | 实施进展同步：T009/T010/T011 标记已完成，剩余 T012/T013 待办 |
| v0.3 | 2026-02-24 | 实施收口：T012/T013 完成（全量回归证据 + 主文档同步） |
