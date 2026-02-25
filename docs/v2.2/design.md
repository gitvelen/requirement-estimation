# v2.2 综合优化升级 技术方案设计

## 文档信息
| 项 | 值 |
|---|---|
| 状态 | Draft |
| 作者 | AI |
| 评审 | - |
| 日期 | 2026-02-24 |
| 版本号 | `v2.2` |
| 文档版本 | `v0.3` |
| 关联提案 | `docs/v2.2/proposal.md`（v0.3） |
| 关联需求 | `docs/v2.2/requirements.md`（v0.3） |
| 关联主文档 | `docs/技术方案设计.md` |
| 关联接口 | `docs/接口文档.md` |

---

## 0. 摘要（Executive Summary）
- v2.2 聚焦 UI 精简与信息架构重构：移除冗余标题、菜单重构（看板/任务）、页面布局优化与交互一致性提升。
- 效能看板重构为两个子页面：`/dashboard/rankings`（排行榜）与 `/dashboard/reports`（多维报表）；同时兼容旧 URL（query 参数）并处理 FUNC-022 下线提示。
- 任务管理改为侧边栏子菜单：`/tasks/ongoing`、`/tasks/completed`；保留旧 `/tasks?tab=...` 的 replace 重定向，避免返回死循环。
- 任务详情页聚合摘要信息并以“下载报告”下拉替代报告版本列表；不引入 DB 迁移，复用现有报告版本 API。
- PM 编辑流程增加“保存并确认”与重评估触发：实质性修改必须确认后才允许持久化，并触发异步重评估；预估人天对 PM 强制只读（前后端双重约束）。
- 系统画像“知识导入”页改为页面内 Tab：代码扫描 / 文档导入；文档导入统一 5 种类型（含 ESB），非 ESB 复用 `POST /api/v1/knowledge/imports` 并补充 `doc_type` 元数据。
- ESB 导入后补齐检索/过滤/统计契约：新增 ESB Search/Stats API 供前端面板使用（`include_deprecated/scope` 等）。
- 备注字段统一为任务级 `remark`（text，多行，按时间倒序展示）：保留历史人工备注；触发点覆盖 PM 保存、专家提交、AI 重评估完成。
- REQ-101 统一页面 Loading/Empty/Error/Retry 落地规范，避免各页面各写一套导致验收不一致。
- 风险控制：旧入口兼容跳转统一使用 replace；上线回滚以版本回退为主（必要时可引入 UI Feature Flag 作为补充）。

## 0.5 决策记录（Design 前置收集结果）

> 本次为存量项目增量迭代，技术栈与部署形态沿用 v2.1；仅记录 v2.2 新增/变更决策。

### 技术决策
| 编号 | 决策项 | 用户选择 | 理由/备注 |
|------|--------|---------|----------|
| D-01 | 前端框架 | React + Ant Design（沿用） | 存量项目 UI 增量改造 |
| D-02 | 后端框架 | Python + FastAPI（沿用） | 复用现有接口与文件存储链路 |
| D-03 | 数据存储 | JSON 文件（`data/`，沿用） | 满足“不做 DB 迁移”约束（REQ-C005） |
| D-04 | 看板路由结构 | `/dashboard/rankings` + `/dashboard/reports` | 满足 REQ-002，且旧 URL 兼容（REQ-013） |
| D-05 | 看板统计窗口 | 固定近 90 天 | 不提供配置入口（REQ-C008）；实现上统一 `time_range=last_90d` |
| D-06 | 任务路由结构 | `/tasks/ongoing` + `/tasks/completed` | 子菜单化减少切换步骤（REQ-005） |
| D-07 | PM 实质性修改确认 | 后端强制 `confirm=true` 才允许持久化 | 防绕过确认（REQ-C002），避免仅靠 UI 约束 |
| D-08 | 重评估触发 | 复用 `POST /api/v1/tasks/{task_id}/reevaluate`（异步） | 与 v2.1 一致，降低实现风险 |
| D-09 | 文档导入 API | 不新建统一导入 API | 非 ESB 复用 `POST /api/v1/knowledge/imports`；ESB 走 `POST /api/v1/esb/imports`（REQ-008） |
| D-10 | 文档类型标记 | 在知识库 metadata 写入 `doc_type` | 不引入 DB 迁移，便于后续检索/审计（REQ-008/6.1） |
| D-11 | 备注承载方式 | 任务级 `remark`（text，多行，新记录置顶） | 保留历史人工备注并追加摘要行；前端只读展示（REQ-011） |
| D-12 | ESB 检索/统计 API | `GET /api/v1/esb/search` + `GET /api/v1/esb/stats` | 满足 REQ-009 的检索/过滤/统计面板（include_deprecated/scope/计数） |

### 环境配置
| 配置项 | 开发环境 | 生产环境 | 敏感 | 备注 |
|--------|---------|---------|------|------|
| `V21_AUTO_REEVAL_ENABLED` | `.env.backend` | `.env.backend` | 否 | 复用：重评估开关（用于 `/tasks/{id}/reevaluate`） |
| `V21_AI_REMARK_ENABLED` | `.env.backend` | `.env.backend` | 否 | 复用：备注自动生成开关（v2.2 默认开启） |
| `V21_DASHBOARD_MGMT_ENABLED` | `.env.backend` | `.env.backend` | 否 | 复用：看板管理指标（v2.2 在 reports 卡片归属展示） |
| `JWT_SECRET` | `.env.backend` | `.env.backend` | 是 | 鉴权密钥（实际值见 `.env`） |
| `DASHSCOPE_API_KEY` | `.env.backend` | `.env.backend` | 是 | LLM/Embedding 密钥（实际值见 `.env`） |

## 1. 背景、目标、非目标与约束

### 1.1 背景与问题
见 `docs/v2.2/proposal.md`“背景与现状”。本次重点是 UI 冗余与导航结构问题，而非算法/性能专项。

### 1.2 目标（Goals，可验收）
- G1（REQ-001/002/005/006/008/010/012/013）：完成页面精简与信息架构重构，并保证旧 URL 兼容与无死链（REQ-C004）。
- G2（REQ-007/REQ-C001/REQ-C002）：PM 编辑流程“可控且不可绕过”，实质性修改需确认并触发重评估。
- G3（REQ-011）：备注自动生成只读展示，保留历史人工备注，新增摘要可追溯。
- G4（REQ-014）：Deployment 阶段同步主文档，避免功能/入口漂移。

### 1.3 非目标（Non-Goals）
以 `docs/v2.2/requirements.md` 的 Out of Scope 为准（不做 DB 迁移/权限体系重构/i18n/移动端适配/性能专项等）。

### 1.4 关键约束（Constraints）
- REQ-C005：不引入 DB schema 迁移或存储结构变更（允许 JSON schema 增量字段）。
- REQ-C007：禁止保留 FUNC-022/AI效果报告入口（仅允许兼容跳转提示）。
- REQ-C008：排行榜统计窗口固定近 90 天，不提供配置入口。

### 1.5 关键假设（Assumptions）
见 `docs/v2.2/requirements.md` 1.2（A1~A3）。

## 2. 需求对齐与验收口径（Traceability）

### 2.1 需求-设计追溯矩阵（必须）
<!-- TRACE-MATRIX-BEGIN -->
| REQ-ID | 需求摘要 | 设计落点（章节/模块/API） | 验收方式/证据 |
|---|---|---|---|
| REQ-001 | 页面标题精简 | §5.1（移除 PageHeader） | UI 巡检 + 截图 |
| REQ-002 | 效能看板导航重构 | §5.2（路由/菜单/重定向） | 路由跳转验证 + UI 截图 |
| REQ-003 | 排行榜页面 | §5.2（Rankings 页面 + API） | UI 断言 + 接口输出核验 |
| REQ-004 | 多维报表页面 | §5.2（Reports 页面 + 卡片归属） | UI 断言 + 指标名称可见性核验 |
| REQ-005 | 任务管理子菜单化 | §5.3（任务路由/菜单/重定向） | 路由跳转验证 |
| REQ-006 | 任务详情摘要与报告下载 | §5.4（ReportPage 重构 + 报告下拉） | UI 断言 + 下载接口回归 |
| REQ-007 | PM 编辑管控与重评估 | §5.5（确认门禁 + 触发重评估） | UI 交互回归 + 接口验证 |
| REQ-008 | 知识导入页重设计 | §5.6（Import Tab 化 + doc_type） | UI 交互回归 + 导入接口回归 |
| REQ-009 | ESB 特有能力保留 | §5.6/§5.7（ESB 导入/检索/统计） | UI 交互回归 + 接口验证 |
| REQ-010 | COSMIC 规则入口优化 | §5.8（“?”图标 + 弹层） | UI 断言 |
| REQ-011 | 备注字段自动生成 | §5.9（remark 追加策略 + 展示） | 数据抽样 + UI 断言 |
| REQ-012 | FUNC-022 下线 | §5.2（移除入口 + 旧入口提示） | UI 巡检 + 路由跳转验证 |
| REQ-013 | 旧 URL 兼容重定向 | §5.2/§5.3（Legacy Redirect） | 路由跳转验证 |
| REQ-014 | 主文档同步更新 | §6.1（Deployment 清单） | 文档 diff 审查 |
| REQ-101 | 统一加载/空/错误态 | §5.11（统一加载/空/错误态） | UI 验证（Loading/Empty/Error） |
| REQ-102 | 兼容跳转不产生回退死循环 | §5.2/§5.3（replace 跳转） | 浏览器回退验证 |
| REQ-C001 | PM 不可编辑预估人天 | §5.5（前后端双约束） | UI 断言 + API 拒绝验证 |
| REQ-C002 | 实质性修改不可绕过确认 | §5.5（confirm 强制） | API 负向用例 + UI 交互 |
| REQ-C003 | 不得破坏既有数据兼容性 | §5.*（兼容策略） | v2.1 数据回归抽样 |
| REQ-C004 | 不得出现菜单/路由死链 | §5.10（菜单全量巡检） | 自动化巡检脚本/人工点击 |
| REQ-C005 | 不得引入 DB 迁移/结构变更 | §5.*（存储策略） | 代码审查（无 DDL/迁移） |
| REQ-C006 | 文档导入不支持批量上传 | §5.6（单文件 Upload） | UI 断言 |
| REQ-C007 | 禁止保留 FUNC-022 入口 | §5.2（移除/仅提示） | UI 巡检（入口不存在） |
| REQ-C008 | 排行榜统计周期不可配置 | §5.2（固定 last_90d） | UI 断言（无配置控件） |
<!-- TRACE-MATRIX-END -->

## 3. 现状分析与方案选型（Options & Trade-offs）

### 3.1 现状与问题定位
- 前端路由以 `/dashboard?page=...` 与 `/tasks` 内部 Tab 为主，导致信息架构与导航不一致，且 UI 冗余（PageHeader）较多。
- 看板“AI表现”与 FUNC-022 存量入口仍在，需按 v2.2 明确下线并兼容旧链接。
- PM 编辑页允许编辑“预估人天”，且新增功能点默认填 1/2.5（前后端均需收口）。

### 3.2 方案候选与对比（至少 2 个）
| 方案 | 核心思路 | 优点 | 缺点/风险 | 成本 | 结论 |
|---|---|---|---|---|---|
| A（最小改） | 保留原 `/dashboard?page=` 与 `/tasks` 内 Tab，仅做文案/布局精简 | 改动小、回归面小 | 不符合“子菜单化”目标；旧结构继续累积复杂度 | 低 | 不采用 |
| B（本方案） | 将看板/任务提升为侧边栏子菜单，旧 URL 全 replace 重定向；页面按需求重排 | 对齐需求（REQ-002/005/013）；更易扩展与维护 | 需要路由/菜单/页面拆分回归 | 中 | 采用 |

### 3.3 关键技术选型与新增依赖评估
不新增三方依赖；复用现有 React Router、Ant Design、FastAPI 与文件存储。

## 4. 总体设计（High-level Design）

### 4.1 系统上下文与边界
不引入新外部依赖；前后端仍由 Nginx 反代 `/api` 到 FastAPI，数据落 `data/` + `uploads/`。

### 4.2 架构概述（按 C4 关注点）
本次变更以“前端路由/交互 + 后端接口小幅扩展”为主：
- 前端：新增路由与菜单层级；拆分看板页面；重排任务详情与系统画像导入页面；优化专家评估规则入口。
- 后端：看板统计口径补齐（last_90d + 三类排行）；知识导入补充 `doc_type` 元数据；ESB 对外提供检索/统计（供前端面板使用）；PM 编辑约束与确认门禁；备注追加策略。

### 4.3 变更影响面（Impact Analysis）
| 影响面 | 是否影响 | 说明 | 需要迁移/兼容 | Owner |
|---|---|---|---|---|
| API 契约 | 是 | 看板查询返回 widget 结构扩展；知识导入新增 `doc_type`；ESB 新增 search/stats | 向后兼容（新增字段/新接口） | - |
| 数据库/存储 | 否 | 不引入 DB；仅 JSON schema 增量字段（remark/doc_type） | 旧数据兼容读取 | - |
| 权限与审计 | 是 | PM 编辑门禁与字段不可写；ESB 检索权限按系统主责/B角 | 需回归 403/404 | - |
| 性能与容量 | 否 | 页面拆分不增加核心计算复杂度；看板统计窗口固定 90 天 | - | - |
| 运维与监控 | 否 | 复用现有部署方式 | - | - |
| 前端/交互 | 是 | 导航结构与多个页面布局变化 | 旧入口重定向 | - |

## 5. 详细设计（Low-level Design）

### 5.1 全站页面标题精简（REQ-001）
原则：侧边栏已指示当前位置的页面，移除重复 PageHeader 标题；保留必要的操作按钮区。
- 重点改动页面（示例文件）：
  - `frontend/src/pages/TaskListPage.js`（ongoing/completed）
  - `frontend/src/pages/SystemListConfigPage.js`
  - `frontend/src/pages/CosmicConfigPage.js`
  - `frontend/src/pages/UserManagementPage.js`
  - `frontend/src/pages/KnowledgePage.js`
  - `frontend/src/pages/SystemProfileImportPage.js`
  - `frontend/src/pages/SystemProfileBoardPage.js`（信息看板→信息展示）
  - `frontend/src/pages/NotificationPage.js`

### 5.2 效能看板：菜单/路由/页面拆分（REQ-002/003/004/012/013/102/REQ-C008）
#### 5.2.1 前端路由与菜单
- 新路由：
  - `/dashboard/rankings`：排行榜（含 3 个 Tab）
  - `/dashboard/reports`：多维报表（3 张卡片）
- `/dashboard/rankings` 页面交互（REQ-003/REQ-C008）：
  - Tab：评估效率排行 / 任务提交排行 / 系统活跃排行
  - 每个 Tab 右下角固定展示计算逻辑说明（以“计算逻辑：”开头，且包含“近90天”）：
    - 评估效率排行：`计算逻辑：评估效率 = 已完成评估数 / 累计评估耗时（天），仅统计近90天数据`
    - 任务提交排行：`计算逻辑：统计近90天内各项目经理提交的任务总数，按数量降序排列`
    - 系统活跃排行：`计算逻辑：统计近90天内各系统关联的评估任务数，按数量降序排列`
- 重定向（replace）：
  - `/dashboard` → `/dashboard/reports`
  - `/dashboard?page=rankings` → `/dashboard/rankings`
  - `/dashboard?page=overview|system|flow` → `/dashboard/reports`
  - `/dashboard?page=ai` → `/dashboard/reports` + 一次性提示“AI效果报告已下线”
- 下线路由兼容（replace）：
  - `/reports/ai-effect` → `/dashboard/reports` + 一次性提示“AI效果报告已下线”（与 `/dashboard?page=ai` 同口径）
- 移除入口：
  - 菜单/页面内不再出现“AI表现/AI效果报告”（REQ-C007）
  - 兼容跳转仅允许提示文案出现“已下线”，不允许出现可点击入口（REQ-C007）

#### 5.2.2 看板后端口径
- 统一统计窗口：固定近 90 天（基于 `frozen_at` 落入窗口）；实现上统一 `time_range=last_90d`，并在后端解析该枚举。
- 排行榜 3 Tab 数据（REQ-003）：
  - 评估效率排行：按 expert 维度聚合（提交数 / 累计耗时天），耗时以 `round_submissions[round]-assignment.created_at` 近似。
  - 任务提交排行：按 manager（creator）维度统计近 90 天提交任务数。
  - 系统活跃排行：按系统维度统计近 90 天关联任务数。
- 多维报表 3 卡片（REQ-004）：
  - 总览统计：复用 overview 基础指标，并将“修正率/命中率/画像贡献”归入本卡片展示（来源：管理指标 widgets）。
  - 系统影响分析：复用 system 页面指标 + 画像完整度 widget。
  - 流程健康度：复用 flow 页面指标，并将“评估周期/偏差监控/学习趋势”归入本卡片展示。

### 5.3 任务管理：子菜单化与兼容跳转（REQ-005/013/102）
- 新路由：
  - `/tasks/ongoing`：进行中（pending+in_progress）
  - `/tasks/completed`：已完成（completed+closed）
- 兼容跳转（replace）：
  - `/tasks` → `/tasks/ongoing`
  - `/tasks?tab=ongoing|completed` → `/tasks/ongoing|completed`
- 实现策略：
  - 保留 `TaskListPage` 作为复用组件，通过路由参数决定展示 ongoing/completed（不再展示页面内 Tab）。
  - 看板 drilldown 统一跳转到 `/tasks/ongoing?from_dashboard=1&...`（或按 filters 决定 completed）。

### 5.4 任务详情页：摘要聚合与报告下载（REQ-006）
- 页面结构调整（以 `frontend/src/pages/ReportPage.js` 为主）：
  - 摘要卡片展示字段：任务状态、创建时间、提交人、系统名称、功能点数量、专家评估状态（已评/待评/总数）、当前评估轮次。
  - 下载报告：使用 Dropdown，下拉包含“最新报告”与历史版本项（来自 `GET /api/v1/tasks/{task_id}/reports`）。
    - 空态：若 reports 为空，“下载报告”按钮置灰且提示“暂无可下载报告”（满足 GWT-REQ-006-02）。
  - 删除独立卡片：不再出现标题为“任务详情 / 专家评估进度 / 报告版本列表”的独立区域（满足 GWT-REQ-006-04）。

### 5.5 PM 编辑管控与重评估（REQ-007/REQ-C001/REQ-C002）
#### 5.5.1 前端交互
- `frontend/src/pages/EditPage.js`：
  - “预估人天”列/表单对 PM 禁用或隐藏（只读展示）。
  - 新增功能点：预估人天默认值为空（不再默认填 1/2.5）。
  - 实质性修改检测：add/delete/update(core fields)/系统增改删等 → 仅允许“保存并确认”路径。
  - 点击“保存并确认”弹窗确认；确认后执行持久化并调用 `POST /api/v1/tasks/{task_id}/reevaluate`，并在 UI 展示评估中状态。
  - 非实质性修改（如排序）允许普通保存，不弹窗、不触发重评估（GWT-REQ-007-03）。

#### 5.5.2 后端强制门禁
- 涉及接口（均需鉴权，至少包含 `actor_id/actor_role`）：
  - `PUT /api/v1/requirement/features/{task_id}`（add/update/delete 功能点）
  - `POST /api/v1/requirement/systems/{task_id}`（新增系统 Tab）
  - `PUT /api/v1/requirement/systems/{task_id}/{system_name}/rename`（重命名系统 Tab）
  - `DELETE /api/v1/requirement/systems/{task_id}/{system_name}`（删除系统 Tab）
- “confirm”传参约定（请求显式携带 `confirm=true`）：
  - JSON body 接口：增加可选字段 `confirm: bool=false`
  - DELETE 接口：使用 query 参数 `?confirm=true`
- PM 不可编辑预估人天（REQ-C001）：
  - actor_role=manager 时，禁止写入/修改 `预估人天`：
    - update：若 payload 含 `预估人天` 且与旧值不同 → 拒绝（403, `AUTH_001`）
    - add：忽略 payload 中 `预估人天`，落库为空（确保新增功能点“预估人天”为空）
- 实质性修改判定与 confirm 门禁（REQ-C002 / REQ-007-03）：
  - add/delete 功能点、add/rename/delete 系统 Tab：一律视为“实质性修改”，必须 `confirm=true`
  - update 功能点：仅当修改了“核心字段”才视为实质性修改，核心字段集合：
    - `功能点`（名称）
    - `业务描述`（描述）
    - `系统`（所属系统）
    - （兜底）任何未识别字段变更默认按“实质性修改”处理（避免绕过确认）
  - 若判定为实质性修改且 `confirm!=true`：拒绝（400，建议错误码 `REQ_001`，message: "实质性修改需要确认"），且不产生任何持久化变更、不触发重评估
  - 非实质性修改（如仅修改排序字段 `序号`）：允许 `confirm=false` 正常保存（满足 GWT-REQ-007-03）

### 5.6 系统画像：知识导入页 Tab 化 + 文档类型（REQ-008/REQ-C006）
- `frontend/src/pages/SystemProfileImportPage.js`：
  - 页面内部 Tab：代码扫描 / 文档导入。
  - 文档导入 Tab：单文件 Upload + 文档类型下拉（5 种）；不提供批量入口（REQ-C006）。
    - 5 种选项（稳定 code → 展示文案）：
      - `requirements` → 需求文档
      - `design` → 设计文档
      - `tech_solution` → 技术方案
      - `history_report` → 历史评估报告
      - `esb` → ESB接口文档
  - 非 ESB 文档导入（前后端约定）：
    - 调用 `POST /api/v1/knowledge/imports`，并固定：`knowledge_type=document`、`level=normal`
    - 追加 `doc_type`（Form 字段，取值为 `requirements|design|tech_solution|history_report`），写入知识库 metadata（不引入 DB 迁移）
    - 向后兼容：`doc_type` 为可选字段；旧调用方不传不影响导入
  - ESB 接口文档（REQ-009-01）：
    - 调用 `POST /api/v1/esb/imports`，保留 `mapping_json` 输入（可选）
    - 导入结果除 `total/imported/skipped/errors` 外，补充返回 `mapping_resolved`（字段→最终匹配列名）作为“列映射结果提示/预览”，前端导入后展示该提示（满足“列映射预览/提示”验收）

### 5.7 ESB 能力对齐（REQ-009）
- 后端对外提供 ESB 检索/统计接口（供前端“导入后检索/过滤/统计面板”使用），能力包含：
  - 状态过滤：正常/废弃（include_deprecated）
  - scope：provider/consumer/both
  - 统计：有效/废弃/去重接口数

#### 5.7.1 ESB API 契约（供前端面板调用）
> 说明：接口路径与鉴权沿用 `backend/api/esb_routes.py` 的 owner/B角权限口径；admin 例外放行。

- `GET /api/v1/esb/search`
  - query：
    - `q`：检索关键词（必填）
    - `system_id`：系统标识（推荐用 system_id；与导入口径一致）
    - `scope`：`provider|consumer|both`（默认 both）
    - `include_deprecated`：`true|false`（默认 false；false 时过滤非“正常使用”状态）
    - `top_k`：返回条数（默认 8）
  - response（示例结构）：
    - `items[]`：至少包含 `provider_system_id/provider_system_name/consumer_system_id/consumer_system_name/service_name/status/similarity`
- `GET /api/v1/esb/stats`
  - query：`system_id`（可选；为空则返回全局统计）
  - response：
    - `active_entry_count`：有效条目数
    - `deprecated_entry_count`：废弃条目数
    - `active_unique_service_count`：有效去重接口数
    - `system_summary[]`：系统汇总表（如导入文件包含该 sheet）

### 5.8 专家评估：COSMIC 规则入口（REQ-010）
- `frontend/src/pages/EvaluationPage.js`：
  - 移除右侧常驻 COSMIC 卡片。
  - 顶部增加“?”图标（Tooltip/Popover）；点击展示规则详情（Modal/Drawer/Popover 任选其一，但需可滚动、可关闭，且不遮挡关键按钮）。

### 5.9 备注字段自动生成（REQ-011）
- 后端生成策略：
  - 在 task 上维护 `remark`（text，多行）字段：保留历史人工备注；v2.2 起新增摘要行**置顶**（时间倒序展示）。
  - 摘要行格式（建议）：
    - `[YYYY-MM-DD HH:MM] PM(<actor_id>): ...`
    - `[YYYY-MM-DD HH:MM] 专家(<actor_id>): ...`
    - `[YYYY-MM-DD HH:MM] AI重评估: ...`
  - 摘要行必须包含关键词：`PM` / `专家` / `AI重评估`（满足对应 GWT）。
  - 触发点：
    - PM 编辑保存（普通保存/保存并确认均可追加 PM 摘要；重评估完成追加 AI 摘要）
    - 专家提交评估成功（追加 专家 摘要）
- 前端展示：
  - 在任务详情页只读展示 remark（无输入框/编辑入口）。

### 5.10 死链与全量菜单巡检（REQ-C004）
- 在 Testing 阶段补充菜单点击巡检脚本/用例，覆盖全部菜单项与子菜单（含重定向场景）。

### 5.11 统一加载/空/错误态（REQ-101）
为避免各页面各写一套导致验收不一致，新增/重构页面统一遵循以下规范：
- Loading：接口请求中展示 `Spin`（或明确 Loading 文案），禁止空白页
- Empty：数据集为空展示 `Empty`（含“暂无数据/暂无结果”等文案）
- Error：请求失败展示错误提示（`Alert`/message）+ “重试”按钮
- Retry：重试按钮必须触发同一请求重新拉取数据，并清理错误态
- 覆盖页面清单：`/dashboard/rankings`、`/dashboard/reports`、`/tasks/*`、任务详情页、`/system-profiles/import`

## 6. 部署与文档同步（REQ-014）

### 6.1 主文档同步清单
Deployment 阶段（Phase 07）完成上线后，同步更新以下主文档（以 v2.2 实际上线行为为准）：
- `docs/系统功能说明书.md`：移除/标记 FUNC-022（AI效果报告）入口与相关描述
- `docs/接口文档.md`：标记 `API-009` 的 `page=ai` 参数废弃；同步旧 URL 兼容入口说明
- `docs/用户手册.md`：更新导航结构（看板/任务子菜单）与报告下载入口说明
- `docs/部署记录.md`：追加本次上线与回滚记录

### 6.2 配置、密钥与开关（Config/Secrets/Flags）
本次不新增敏感配置；复用 v2.1 既有 Feature Flags（见 §0.5）。如上线风险偏高，可补充 v2.2 UI 结构开关作为灰度/回滚手段（可选，需走 CR）。

## 7. 回滚与发布策略（含风险）
- 回滚首选：版本回退到 v2.1（保留旧 URL 与页面，回退风险最低）。
- 兼容策略：v2.2 保留所有旧 URL 且统一使用 replace 重定向，避免死链与返回死循环。
- 触发条件（任一满足即可考虑回滚）：
  - 菜单/路由出现 404/空白页（违反 REQ-C004）
  - 旧 URL 兼容跳转出现“返回死循环”（违反 REQ-102）
  - 报告下载入口不可用（违反 REQ-006/REQ-C003）
  - PM 编辑保存被误拒绝/误放行（违反 REQ-007/REQ-C001/REQ-C002）
- 回滚步骤（最小 Runbook）：
  1. 回退前端/后端版本到 v2.1
  2. 验证菜单巡检：逐个点击所有菜单项（含子菜单）
  3. 验证旧 URL：`/tasks?tab=ongoing|completed`、`/dashboard?page=rankings|overview|ai`、`/reports/ai-effect`
  4. 验证任务详情：摘要卡片可渲染；“下载报告”可下载最新与历史版本
  5. 验证编辑门禁：PM 无法编辑预估人天；实质性修改必须确认；非实质性修改可直接保存
- 风险点：
  - 看板口径与数据源：新增近 90 天窗口与排行维度，需对现有字段（assignment.created_at、round_submissions）做数据完整性检查。
  - PM 编辑门禁：后端 confirm 强制可能影响现有调用方，需联调前端一起上线。

## 8. 变更记录
| 版本 | 日期 | 修改章节 | 说明 | 作者 |
|---|---|---|---|---|
| v0.1 | 2026-02-24 | 初始化 | v2.2 设计初稿落盘 | AI |
| v0.2 | 2026-02-24 | 5.2/5.5/5.7/5.9/5.11/7 | 补齐下线路由兼容口径、confirm 门禁判定、ESB Search/Stats 契约、remark 数据模型、REQ-101 统一状态规范与可执行回滚步骤 | AI |
| v0.3 | 2026-02-24 | 5.2/5.4/5.5/5.6 | 补齐排行榜“计算逻辑”固定文案、报告下载空态口径、doc_type 传参约定与 ESB 列映射提示契约 | AI |
