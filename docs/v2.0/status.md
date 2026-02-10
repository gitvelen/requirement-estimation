---
_baseline: v2.0.0
_current: 36fff8f
---

# 变更状态（`docs/v2.0/status.md`）

| 项 | 值 |
|---|---|
| 版本号 | v2.0 |
| 变更目录 | `docs/v2.0/` |
| 变更主题 | v2.0 增量修订：CR-20260209-001 用户体验优化与功能增强（10项） |
| 基线说明 | v2.0 初版已交付；本次为增量修订（不新开 v2.1 目录） |
| 当前阶段 | Deployment（Done，CR-20260209-001） |
| 变更状态 | Done（CR-20260209-001 已部署并完成观察窗口） |
| 基线版本（对比口径） | `v2.0.0` |
| 当前代码版本 | `v2.0-upgrade`（`36fff8f`） |
| 本次复查口径 | full（涉及权限/安全、兼容性、旧格式文件解析风险；需全链路复核） |
| 负责人 | AI |
| 最后更新 | 2026-02-10（CR-20260209-001 观察窗口通过，主文档同步完成） |
| 提案版本 | v0.16 |
| 需求版本 | v1.21 |
| 设计版本 | v0.16 |
| 计划版本 | v1.6 |
| 实现检查清单版本 | v0.1 |
| 测试报告版本 | v0.6 |
| 部署文档版本 | v0.9 |
| 审查状态 | Requirements v1.21（CR-20260209-001 增量已复审通过，负责系统=主责+B角）；Design v0.16 ✅通过（自审）；Planning v1.6 ✅通过（自审，见 review_planning.md 追加记录：2026-02-09） |
| 完成日期 | 2026-02-10 |

## 变更摘要
本次变更为 v2.0 的增量修订，包含：
1) **CR-20260209-001 用户体验优化与功能增强（10项，2026-02-09）**：
- 任务管理：多角色用户支持 activeRole 切换；任务管理统一为“进行中/已完成”两个Tab；专家“查看”权限缺陷修复。
- 系统画像：知识导入仅展示负责系统并优化为三栏卡片布局；信息看板引入“AI画像总结→通知→采纳/忽略”闭环，字段标记 `field_source`（manual/ai）。
- 评估/编辑页：PM编辑功能点页移除系统校准、Tab完整度颜色提示、备注截断；专家评估页完整度提示简化为颜色标记。
- 配置：规则管理（COSMIC）配置项平铺Tab展示（取消“技术配置（高级）”折叠）。
- 系统清单：支持双sheet导入（主系统+子系统映射），行级校验并兼容历史单sheet。
- 文件格式：发起评估与知识导入支持 `.doc/.xls` 旧格式解析（新增安全约束）。
2) 既有 v2.0 修订（2026-02-07）：Proposal/Requirements一致性修复（指标口径、权限口径、残留表述修正等，不改变已实现范围）

## 目标与成功指标
- **核心目标**：提升功能点拆分和工作量估算的准确性
- **具体指标**：
  - 功能点拆分准确性：PM修正率下降到10%以内（PM修正率=删除+调整操作数/AI初始功能点数；PM新增操作数单独统计）
  - 系统能力覆盖度：从1类（文档）扩展到3类（代码+文档+ESB）
  - 复杂度评估维度：从1个扩展到3个（业务规则+集成+技术）
  - 学习闭环记录：100%记录修改轨迹

## 关键决策记录
1. **ESB字段映射**：支持用户通过 `mapping_json` 手动指定映射关系
2. **PM可查看系统画像范围**：自己负责系统（系统清单主责或B角）或创建过评估任务的系统
3. **异常值阈值**：专家估值与均值偏差>20%时标记异常
4. **代码扫描幂等**：支持 `force=true` 参数强制创建新任务
5. **AI推理保留**：单条记录10KB限制，推理内容超1000字符截断
6. **效能看板统计口径**：系统改造=评估结论涉及系统；工作量=人天；AI准确率对齐最终评估；默认按评估时负责人快照；B角不参与统计
7. **文档完整度计分**：0篇为0分；仅统计 `knowledge_type=document`（不包含历史评估L0）
8. **范围调整**：不做系统画像可视化展示/AI使用提示/优化建议治理机制/文档技术特征结构化自动抽取
9. **向量检索性能验收前置**：REQ-NF-002 以 Milvus 后端验收（local 仅小规模/降级）
10. **报告下载格式**：v2.0 仅支持 PDF；docx 参数预留，传入返回 `REPORT_002`
11. **Git URL 扫描安全策略**：默认禁用；启用需配置开关+host allowlist 命中
12. **B角代理权限**：允许B角执行知识导入/草稿编辑/AI总结重试；发布与统计仍仅主责（由需求确认固化，见 requirements v1.21）

## 关键链接
- 提案：`proposal.md`
- 需求：`requirements.md`
- 设计：`design.md`
- 计划：`plan.md`
- 实现检查清单：`implementation_checklist.md`
- 测试报告：`test_report.md`
- 部署：`deployment.md`
- 审查：`review_proposal.md`、`review_requirements.md`

## CR状态枚举（🔴 MUST）
| 状态值 | 含义 | 是否可入Active CR列表 | 说明 |
|--------|------|---------------------|------|
| Idea | 想法/提议 | ❌ 否 | 未确认的初步想法，不应进入 Active 列表 |
| Accepted | 已接受 | ✅ 是 | 需求已澄清，计划纳入当前版本 |
| In Progress | 进行中 | ✅ 是 | 正在实现中 |
| Implemented | 已实现 | ❌ 否 | 已上线部署完成 |
| Dropped | 已废弃 | ❌ 否 | 不再实施 |
| Suspended | 已暂停 | ❌ 否 | 暂停实施，保留恢复可能 |

## Active CR 列表（🔴 MUST，CR场景）
> v2.0 增量修订：用户体验优化与功能增强（10项）

| CR-ID | 状态 | 标题 | 影响面（文档/模块/ID） | 链接 |
|---|---|---|---|---|
| （空） | — | — | 所有本次上线 CR 已转为 Implemented | — |

## Idea池（可选，非Active）
> （空）

## 需要同步的主文档清单（如适用）
> 本轮 **CR-20260209-001** 主文档已完成同步。
- [x] `docs/系统功能说明书.md`
- [x] `docs/技术方案设计.md`
- [x] `docs/接口文档.md`
- [x] `docs/用户手册.md`
- [x] `docs/部署记录.md`

---

## 工作流状态
| 工作流模式 | 运行状态 |
|---|---|
| semi-auto | completed |

## 阶段转换记录
| 从阶段 | 到阶段 | 日期 | 原因 | 触发人 |
|---|---|---|---|---|
| - | Proposal | 2026-02-06 | 初始化 v2.0 迭代 | User |
| Proposal | Requirements | 2026-02-06 | 提案审查通过 | User |
| Requirements | Design | 2026-02-06 | 需求审查通过 | User |
| Design | Planning | 2026-02-06 | 设计审查通过 | User |
| Planning | Implementation | 2026-02-07 | 开始实现与回归 | AI |
| Implementation | Testing | 2026-02-07 | 全量回归通过 | AI |
| Testing | Deployment | 2026-02-07 | 测试收口进入发布准备 | AI |
| Deployment | Deployment（wait_confirm） | 2026-02-08 | requirements确认后完成阶段复核，按流程等待人工确认部署 | AI |
| Deployment（wait_confirm） | Proposal（CR-20260209-001） | 2026-02-09 | 部署后出现新增意图，创建并接受CR进入人工介入期 | User |
| Proposal（CR-20260209-001） | Requirements（CR-20260209-001） | 2026-02-09 | 提案确认通过，进入需求阶段 | User |
| Requirements（CR-20260209-001） | Requirements（wait_confirm） | 2026-02-09 | 需求文档更新至 v1.21 且复审通过（负责系统=主责+B角），等待人工确认进入Design | AI |
| Requirements（wait_confirm） | Design（CR-20260209-001） | 2026-02-09 | 用户确认进入Design | User |
| Design（CR-20260209-001） | Planning（CR-20260209-001） | 2026-02-09 | Design v0.16 自审收敛，进入任务计划阶段 | AI |
| Planning（CR-20260209-001） | Implementation（CR-20260209-001） | 2026-02-09 | 任务计划确认后进入实现阶段 | AI |
| Implementation（CR-20260209-001） | Testing（CR-20260209-001） | 2026-02-09 | T027~T037 实现完成并回归通过（后端61通过） | AI |
| Testing（CR-20260209-001） | Deployment（wait_confirm，CR-20260209-001） | 2026-02-09 | 涉及API/权限/兼容变更，按流程等待人工确认部署 | AI |
| Deployment（wait_confirm，CR-20260209-001） | Deployment（CR-20260209-001） | 2026-02-10 | 用户确认后执行正式部署，进入发布后观察窗口 | User+AI |
| Deployment（CR-20260209-001） | Deployment（Done，CR-20260209-001） | 2026-02-10 | 观察窗口通过并完成主文档同步，CR 状态切换为 Implemented | AI |

## CR状态更新记录（部署后）
| CR-ID | 之前状态 | 之后状态 | 上线日期 | 备注 |
|---|---|---|---|---|
| CR-20260209-001 | In Progress | Implemented | 2026-02-10 | 正式部署完成，观察窗口通过，主文档同步完成 |

## 紧急中断记录
| 触发时间 | 原因 | 当前状态 | 恢复条件 |
|---|---|---|---|
| — | — | — | — |

## 回滚要点
- 前端：保留旧页面路由，通过配置切换
- 后端：新接口向后兼容，旧接口保留
- 数据库：复用现有JSON文件存储

## 备注
- 本文件用于显式标记阶段/完成状态，避免仅靠"文件存在性"推断导致误判。
- 上一轮 v2.0 已完成 Testing 阶段回归与证据固化：见 `docs/v2.0/test_report.md`（后端全量回归 `60 passed`）。本轮 **CR-20260209-001** 已完成 Design/Planning/Implementation/Testing/Deployment 全流程收口与证据补齐。

## 实施进度（Implementation）
- 2026-02-10：Deployment 观察窗口收口（CR-20260209-001）
  - 观察窗口：`2026-02-10 07:55 CST ~ 2026-02-10 08:05 CST`（STAGING，10分钟最小窗口）。
  - 可用性：`docker-compose ps` 显示 backend `healthy`、frontend `Up`。
  - 健康检查：`curl http://localhost:443/api/v1/health` 返回 `healthy`；前端首页 `HTTP/1.1 200 OK`。
  - 日志巡检：`docker-compose logs --since=30m` 后端未见 error；前端仅 `favicon.ico` 缺失噪音日志（无业务影响）。
  - 发布后回归：`.venv/bin/pytest -q tests/test_dashboard_query_api.py tests/test_task_freeze_and_list_api.py tests/test_report_download_api.py`（`8 passed in 4.78s`）；前端 build/test 均通过。
  - 文档同步：主文档 `系统功能说明书/技术方案设计/接口文档/用户手册/部署记录` 已更新并记录 CR-ID。
  - 当前状态：Deployment 收口完成，`变更状态=Done`，工作流 `completed`。

- 2026-02-10：Deployment 正式执行（CR-20260209-001）
  - 备份完成：`backups/20260210_075542_cr20260209`（`data/uploads/logs`）。
  - 服务发布：`docker-compose up -d --build` 触发 buildx 版本门槛，自动回退 `DOCKER_BUILDKIT=0 COMPOSE_DOCKER_CLI_BUILD=0` 后发布成功。
  - 运行状态：`docker-compose ps` 显示 `requirement-backend=healthy`、`requirement-frontend=Up`。
  - 健康检查：`curl http://localhost:443/api/v1/health` 返回 `{"status":"healthy", ...}`；前端首页 `HTTP/1.1 200 OK`。
  - 发布后最小回归：后端最小集 `8 passed`；前端 `build` 成功 + 单测 `4 passed`；`python -m json.tool data/task_storage.json` 通过。
  - 当前状态：Deployment 正式执行完成，并在观察窗口内通过健康/日志/回归检查。

- 2026-02-09：Deployment 前置校验（CR-20260209-001 收口）
  - 执行部署脚本语法检查：`bash -n deploy-all.sh deploy-backend.sh deploy-frontend.sh deploy-milvus.sh deploy-backend-internal.sh deploy-frontend-internal.sh deploy-milvus-remote.sh`。
  - 执行编排配置校验：`docker-compose config -q`（提示 `version` 字段过时，不影响发布）。
  - 当前状态：已进入 `Deployment（wait_confirm，CR-20260209-001）`，待人工确认后执行正式部署。

- 2026-02-09：CR-20260209-001 增量实现推进（第二批收口）
  - 前端完成（T035）：
    - EditPage 移除“系统校准（知识库）”卡片，系统Tab按完整度评分显示红/黄/绿标记，备注列改为“50字符截断 + Tooltip + 展开/收起”。
    - EvaluationPage 完整度展示简化为Tab颜色标记与当前系统Tag，不再展示冗长 Progress/Alert 文案。
    - ReportPage 重构为“摘要/主体/分析”三段式布局，偏离度统计与高偏离功能点合并为可折叠分析区。
  - 权限缺陷修复（T035 子项）：
    - 前端 `/report/:taskId` 开放 expert 角色访问。
    - 后端任务详情/偏离分析/报告版本/需求文档接口统一支持 expert 参与任务访问（未参与仍返回 403）。
  - 测试收口（T037）：
    - 新增后端回归用例：`tests/test_task_freeze_and_list_api.py::test_expert_can_view_assigned_task_detail_and_high_deviation`。
    - 全量复验：`.venv/bin/pytest -q`（`61 passed in 9.06s`）；`cd frontend && npm run build`（Compiled successfully）；`cd frontend && CI=true npm test -- --watchAll=false`（`4 passed`）。
  - 当前状态：T035/T037 已完成，CR-20260209-001 实现项全部落地。

- 2026-02-09：CR-20260209-001 增量实现推进（第一批收口）
  - 后端完成（T027/T028/T029/T030/T031）：
    - 通知中心 API-017 完成契约兼容：列表接口同时返回 `items` 与兼容字段 `data`；未读数接口返回 `unread_count` 与兼容字段 `data.unread`；通知项补齐兼容字段 `id/title/content/is_read`。
    - 画像 AI 总结闭环落地：导入成功后异步触发 AI 总结，写入 `ai_suggestions`/`ai_suggestions_job`，并支持 `POST /api/v1/system-profiles/{system_id}/ai-suggestions/retry` 手动重试。
    - 主责+B角权限口径完成：代码扫描、ESB导入、知识导入、画像草稿写入/AI重试统一按“主责或B角可写、发布仅主责”执行资源级权限控制。
    - 旧格式解析能力完成：`/api/v1/tasks`、`/api/v1/knowledge/imports`、`/api/v1/esb/imports` 支持 `.doc/.xls`，并通过隔离目录+超时+自动清理策略处理解析过程。
    - 系统清单双sheet兼容完成：主系统+子系统映射双sheet与单sheet历史格式兼容，行级校验与错误码对齐。
  - 前端完成（T032/T033/T034/T036）：
    - 多角色 `activeRole` 角色切换与任务管理双Tab统一（进行中/已完成）已落地。
    - 系统画像“知识导入/信息看板”两页仅展示当前用户负责系统（主责或B角），并保持跨页系统TAB同步。
    - 信息看板新增 AI 建议闭环：显示建议来源与建议内容，支持逐字段采纳/忽略，支持手动重试 AI 建议。
    - COSMIC 配置从“高级折叠”调整为分类平铺 Tab，保留使用说明弹窗。
    - 发起评估页面上传扩展为 `.docx/.doc/.xls`，并统一错误提示读取 `message/detail`。
  - 回归结果：
    - 后端：`.venv/bin/pytest -q` → `60 passed in 8.93s`
    - 前端：`cd frontend && npm run build` → `Compiled successfully`
    - 前端：`cd frontend && CI=true npm test -- --watchAll=false` → `4 passed`

- 2026-02-07：启动 Implementation（T001/T016/T021）
  - 完成 `owner_id/owner_username` 字段归一化与 `resolve_system_owner(system_id/system_name)` 能力；系统画像写入增加主责校验（非主责返回 `AUTH_001`）。
  - API-015 对齐错误码：`SYSLIST_001/002/003` 与 `AUTH_001`，并返回 `error_code/message/details/request_id` 结构。
  - 模板下载补齐 `owner_id/owner_username` 列；导入确认后增加系统识别与知识库 system list 缓存热刷新。
  - 新增回归用例：`tests/test_system_profile_permissions.py`、扩展 `tests/test_system_list_import.py`。
- 2026-02-07：完成 T002/T003（代码扫描 API-001/002）
  - 新增 `POST /api/v1/code-scan/jobs`（JSON + multipart）与 `GET /api/v1/code-scan/jobs/{job_id}`、`POST /api/v1/code-scan/jobs/{job_id}/ingest`，并保留 `/run/status/result/commit/jobs` 兼容入口。
  - 落地主责与创建者权限：提交扫描仅系统主责（admin 例外）；查询/入库仅任务创建者（admin 例外），越权统一返回 `AUTH_001`。
  - 补齐安全与幂等：本地路径绝对路径+allowlist（`SCAN_004`）、Git URL 默认禁用与 host 校验（`SCAN_001`）、压缩包安全解压（路径穿越/链接阻断）与大小/文件数限制（`SCAN_005/006`）、重复提交命中相同 `job_id`（支持 `force=true` 绕过）。
  - 入库接口增加幂等与画像更新：重复 ingest 不重复写入；成功后自动写入系统画像草稿 `completeness.code_scan=true` 并刷新 `completeness_score`（+30 分）；embedding 异常返回 `EMB_001` 且不更新完整度。
  - 新增回归用例 `tests/test_code_scan_api.py`（覆盖 SCAN_001/004/005/006、幂等、权限、EMB_001、完整度更新）。
  - 验证命令：`.venv/bin/pytest -q tests/test_code_scan_api.py tests/test_system_list_import.py tests/test_system_profile_permissions.py`（13 passed）。
- 2026-02-07：完成 T004/T005/T006/T017/T007（画像闭环与学习闭环核心接口）
  - API-003：新增 `POST /api/v1/esb/imports`，支持 `mapping_json`（string/array[string]）映射、按 `system_id` 过滤、主责权限校验、`ESB_001/002` 与 `EMB_001` 错误码对齐；成功导入后更新系统画像 `completeness.esb=true`。
  - API-011：新增 `POST /api/v1/knowledge/imports`，支持 `knowledge_type=document/code`、`level=normal/l0`（仅 document），文件类型白名单与 `KNOW_001/002` 错误码；embedding 异常返回 `EMB_001`；normal 文档导入自动累计文档计数并刷新完整度，L0 不计分。
  - API-004/API-012：系统画像补齐列表分页（含 `status/is_stale`）、完整度查询接口 `/api/v1/system-profiles/completeness`、发布必填校验（`PROFILE_003`）、发布 embedding 强约束（失败 `EMB_001` 不落发布态）；权限收敛为“仅 PM 主责可写”，admin/expert 只读。
  - T017：AI 首次评估快照落库（`task.ai_initial_features` / `task.ai_initial_feature_count`），并确保后续重跑不覆盖首轮快照。
  - API-007：新增 `POST /api/v1/tasks/{task_id}/modification-traces`，服务端补齐 `actor/recorded_at/original_ai_reasoning`，增加保留期清理（`MOD_TRACE_RETENTION_DAYS`）与单条 10KB/推理 1000 字限制。
  - 验证命令：`.venv/bin/pytest -q tests/test_code_scan_api.py tests/test_esb_import_api.py tests/test_knowledge_import_api.py tests/test_system_profile_permissions.py tests/test_system_list_import.py tests/test_modification_trace_api.py tests/test_esb_service.py`（28 passed）。
- 2026-02-07：完成 T008/T009（任务冻结口径与查询 API-010）
  - 冻结口径：新增 `frozen_at/owner_snapshot/ai_estimation_days_total/final_estimation_days_total/ai_estimation_days_by_system/final_estimation_days_by_system` 自动写入，触发点覆盖任务确认与评估完成状态落点，且保持幂等（已有 `frozen_at` 不覆盖）。
  - 状态映射：任务列表 `status` 统一输出 `pending/in_progress/completed/closed`，保留 `workflowStatus` 兼容字段。
  - API-010：`GET /api/v1/tasks` 新增 `group_by_status`、`time_range(start_at/end_at)`、`status/system_id/owner_id/expert_id/project_id/ai_involved` 过滤；支持分组分页返回 `task_groups`。
  - 权限口径：管理员/Viewer 全量；PM（默认）返回“创建或快照主责”；专家返回“被分配/参与任务”；兼容旧 `scope` 参数。
  - 验证命令：`.venv/bin/pytest -q tests/test_task_freeze_and_list_api.py tests/test_api_regression.py -k "task_list_scopes_and_permissions or task_freeze or group_by_status"`（3 passed）。
- 2026-02-07：完成 T011（报告下载 API-014）
  - `GET /api/v1/tasks/{task_id}/report` 增加 expert 参与任务权限校验（未参与返回 `AUTH_001`）。
  - 增加 `format` 参数校验：`format=docx` 与其他非 `pdf` 参数统一返回 `REPORT_002`。
  - 任务未完成/无报告/报告文件缺失统一返回 `REPORT_003`，并保留 PDF 下载兼容路径。
  - 验证命令：`.venv/bin/pytest -q tests/test_report_download_api.py tests/test_api_regression.py -k "report or invite_resend_revoke_and_permission"`（7 passed）。
- 2026-02-07：完成 T020（API-008/API-013 契约对齐）
  - 新增内部计算接口 `POST /api/v1/internal/tasks/{task_id}/expert-deviations/compute`，输出并持久化 `deviation_report`（summary + by_feature）。
  - 新增查询接口 `GET /api/v1/tasks/{task_id}/expert-deviations`，按角色执行资源级权限（manager=创建者，expert=参与者，admin=全量），越权返回 `AUTH_001`。
  - 新增评估详情接口 `GET /api/v1/tasks/{task_id}/evaluation`，返回 API-013 约定字段（task/status/features）。
  - 验证命令：`.venv/bin/pytest -q tests/test_evaluation_contract_api.py tests/test_api_regression.py -k "evaluation or expert_deviation or invite"`（5 passed）。
- 2026-02-07：完成 T018（内部检索 API-005 + 复杂度评估 API-006）
  - 新增 `POST /api/v1/internal/system-profiles/retrieve`：聚合返回 system_profile/capabilities/documents/esb_integrations，支持 embedding/向量检索降级（`degraded=true`）。
  - 新增 `POST /api/v1/internal/complexity/evaluate`：输出三维度评分（business/integration/technical）与综合等级 low/medium/high。
  - 验证命令：`.venv/bin/pytest -q tests/test_internal_retrieve_complexity_api.py`（2 passed）。
- 2026-02-07：完成 T010（效能看板 API-009）
  - 完成 `POST /api/v1/efficiency/dashboard/query` 五类页面 widgets 输出（overview/rankings/ai/system/flow），每页至少 2 个 widget，返回 `sample_size` 与 `drilldown_filters`。
  - 过滤口径补齐：`time_range/custom` 校验、`system_ids/project_ids/owner_id/expert_id/ai_involved` 过滤与 `REPORT_002` 参数错误返回。
  - 排行项支持 item 级 `drilldown_filters`，与 API-010 下钻参数映射一致（system_id/owner_id/time_range 等）。
  - 验证命令：`.venv/bin/pytest -q tests/test_dashboard_query_api.py`（3 passed）。
- 2026-02-07：完成前端 T012/T013/T014/T015（效能看板 + 系统画像工作台 + 任务与评估体验优化 + COSMIC简化）
  - T012：新增 `frontend/src/pages/EfficiencyDashboardPage.js`（五页导航、视角预设 executive/owner/expert、筛选保留、样本量提示、一键下钻到 `/tasks`）。
  - T013：新增 `frontend/src/pages/SystemProfilePage.js`（系统画像列表/详情、草稿保存/发布、代码扫描触发与入库、ESB导入、知识导入；非主责PM只读）。
  - T014：重构 `frontend/src/pages/TaskListPage.js`（API-010 服务端过滤与状态分组展示）、增强 `frontend/src/pages/EvaluationPage.js`（完整度卡片、完整度失败降级“完整度未知”、长文本展开收起、统一时间格式、报告下载入口权限兼容）。
  - T015：重构 `frontend/src/pages/CosmicConfigPage.js`（业务语言说明 + 细/中/粗示例 + 技术配置默认折叠，不改后端算法）。
  - 路由/导航联动：更新 `frontend/src/App.js` 与 `frontend/src/components/MainLayout.js`，新增 `/dashboard`、`/system-profiles` 菜单与权限控制。
  - 验证命令：`cd frontend && npm run build`（Compiled successfully）；`cd frontend && npm test -- --watchAll=false`（1 suite, 4 passed）。
- 2026-02-07：Implementation 阶段任务全部完成（T001~T021 覆盖闭环），当前状态更新为 `Done`。

- 2026-02-07：进入 Testing 阶段（用户确认）
  - 已完成 Implementation 收口并冻结当前实现基线，测试阶段将按 `requirements.md` 与 `plan.md` 执行场景覆盖、异常/边界验证与回归。
  - 下一步输出：持续更新 `docs/v2.0/test_report.md` 的测试记录与追溯矩阵。
- 2026-02-07：Testing 阶段首轮全量回归
  - 执行 `.venv/bin/pytest -q`，首次发现 `tests/test_evidence_permissions.py::test_expert_preview_permission` 失败（404）。
  - 根因定位：`backend/app.py` 缺少 `evidence_router/evidence_level_router` 注册；已补齐并执行定向复验（1 passed）。
  - 修复后再次执行 `.venv/bin/pytest -q`：`60 passed`。
  - 前端复验：`cd frontend && npm run build && npm test -- --watchAll=false`，build 成功、单测 4 passed。
  - 详细证据与缺陷闭环见 `docs/v2.0/test_report.md`。
- 2026-02-07：Testing 阶段收口（审查整改完成）
  - 已补齐 `docs/v2.0/test_report.md` 的 REQ/REQ-NF 追溯矩阵（TEST-001~026），满足“需求可追溯到测试证据”。
  - 已补齐非功能性能证据：
    - REQ-NF-001：代码扫描性能 P95=`1.753s`（目标 <600s）
    - REQ-NF-002：Milvus 检索性能 P95=`444.113ms`（目标 <500ms）
    - REQ-NF-005：并发能力快照 `running=5/queued=1`
  - `@review` 复查已通过（`docs/v2.0/review_testing.md`），P0/P1 均已清零；warning 项进入持续治理。
- 2026-02-07：Testing 阶段完成，已进入 Deployment 阶段
  - Testing 阶段产出已收口：`test_report.md` 追溯矩阵/性能验收证据齐备，`review_testing.md` 复查通过。
  - 当前进入 Deployment 文档化与发布准备：编制 `deployment.md`、同步主文档/手册、准备灰度与回滚检查清单。
- 2026-02-07：Deployment 阶段执行本地 STAGING 手工部署演练
  - 已执行数据备份：`backups/20260207_134728`，并创建 `.env/.env.backend/.env.frontend`。
  - 首次执行 `docker-compose up -d --build` 触发 Docker metadata 崩溃；改用兼容路径（清理同名容器后 `docker-compose up -d`）完成拉起。
  - 部署后验证通过：`/api/v1/health=healthy`、前端首页 `HTTP 200`、后端最小回归 `7 passed`、前端单测 `4 passed`。
  - 结果：Deployment 手工路径已验证可执行；一键脚本已修复并内置 BuildKit 回退路径，可推进正式发布。
- 2026-02-07：Deployment 工具链修复（一键脚本语法）
  - 已修复 `deploy-all.sh`、`deploy-milvus.sh`、`deploy-milvus-remote.sh` 的 `CRLF` 行尾问题。
  - 验证通过：`bash -n` 三脚本均通过，且 mock 干运行流程可完整结束。
  - 当前剩余风险收敛点：BuildKit 原生路径受限于本机 buildx 版本（<0.17）；已具备脚本自动回退路径。
- 2026-02-07：Deployment 构建兼容根因定位与修复
  - 根因确认：`docker-compose up -d --build` 失败与 Docker 工具链相关（用户目录异常插件覆盖 + 本机 buildx 版本 `v0.10.5` 低于当前 compose 构建路径要求）。
  - 已处理：
    - 异常插件已迁移备份到 `~/.docker/cli-plugins/backup_20260207_155602/`
    - 部署脚本已统一加入 BuildKit 失败自动回退（`DOCKER_BUILDKIT=0 COMPOSE_DOCKER_CLI_BUILD=0`）
  - 验证：`bash -n deploy-*.sh` 全部通过；`deploy-all.sh` 干运行可触发回退路径并继续执行。
  - 剩余项：后续可择机升级 buildx 到 `>=0.17` 以恢复原生 BuildKit 路径。

- 2026-02-07：Deployment 阶段收口（文档与验证闭环）
  - 文档：`docs/v2.0/deployment.md` 更新为 v0.2（Done），并已同步主文档/手册：`docs/系统功能说明书.md`、`docs/用户手册.md`、`docs/部署记录.md`
  - 关键验证：后端 `.venv/bin/pytest -q` → `60 passed`；前端 `npm test -- --watchAll=false` → `4 passed`；`bash -n deploy-*.sh` → 通过
- 2026-02-07：Deployment 阶段 `@review` 全量复审与整改
  - 审查报告已落盘：`docs/v2.0/review_deployment.md`。
  - 本轮修复：
    - `backend/app.py` 启停事件由 `@app.on_event` 迁移为 FastAPI `lifespan`。
    - `backend/api/auth.py` 的 JWT 过期时间改为 `datetime.now(timezone.utc)`。
  - 复测结果：后端 `.venv/bin/pytest -q` → `60 passed`；前端 `cd frontend && npm run build && CI=true npm test -- --watchAll=false` → build 成功、`4 passed`。
- 2026-02-07：`@review` 追加整改（告警即时收口）
  - 依赖升级：`pymilvus 2.6.6→2.6.8`、`langchain 1.2.1→1.2.9`、`langchain-core 1.2.6→1.2.9`、`langgraph 1.0.5→1.0.8`。
  - 白名单收敛：在 `pyproject.toml` 增加 `pytest` 定向 `filterwarnings`，仅忽略上述第三方已知兼容告警。
  - 复测结果：后端 `.venv/bin/pytest -q` → `60 passed in 12.00s`（无 warning 输出）；前端 build/test 与部署脚本语法检查均通过。
- 2026-02-07：需求与代码修正（效能看板删除明细与导出）
  - 变更内容：删除效能看板的"明细与导出"页面功能，仅保留榜单下钻到任务列表的能力
  - 代码修改：
    - `frontend/src/pages/EfficiencyDashboardPage.js`：删除"details"页面选项、导出CSV按钮和相关渲染函数
    - `backend/api/routes.py`：删除"details"页面支持（page验证移除details选项）
  - 文档更新：
    - `proposal.md`：更新为 v0.12，删除 A-04 中的"明细与导出页面"描述
    - `requirements.md`：更新为 v1.16，更新 REQ-020 标题为"效能看板任务明细下钻"，删除导出相关内容
    - `requirements.md`：修复第104行 REQ-017 引用错误（改为 REQ-019）
  - 回归验证：后端 `.venv/bin/pytest -q` → `60 passed`；前端 `npm run build` → 成功
- 2026-02-07：Proposal/Requirements 文档一致性修复
  - `docs/v2.0/proposal.md`：更新为 v0.13（修复指标表格、澄清PM修正率口径、对齐任务分组与导入口径）
  - `docs/v2.0/requirements.md`：更新为 v1.17（澄清PM修正率/PM新增口径、补齐Viewer权限、移除导出残留表述、修复步骤编号）
- 2026-02-07：最终收口复验与文档同步
  - 设计/计划文档已同步为 `design v0.12`、`plan v1.0`，并完成里程碑与 DoD 关闭。
  - 最终复验通过：后端 `.venv/bin/pytest -q` → `60 passed in 7.14s`；前端 `npm run build && npm test -- --watchAll=false` → build 成功、`4 passed`。
  - 部署就绪校验通过：`bash -n deploy-*.sh` 全通过；`docker-compose config -q` 通过（仅 `version` 字段过时 warning）。
  - 部署文档与主记录已同步：`docs/v2.0/deployment.md` v0.3、`docs/部署记录.md` 新增“STAGING（最终复验）”。

- 2026-02-08：requirements 确认后推进“剩余阶段”复核收口
  - Planning：`docs/v2.0/plan.md` 升级至 v1.2，补充 R6 引用存在性自检实测结论（`comm -23` 差集为空）。
  - Design：`docs/v2.0/design.md` 升级至 v0.14，修正内部决策标识 `OP-REQ-106 → OP-DES-106`，并完成 Design→Testing 追溯一致性复查。
  - Testing：执行全量复验 `.venv/bin/pytest -q`（`60 passed in 14.52s`）、`cd frontend && npm run build`（成功）、`cd frontend && CI=true npm test -- --watchAll=false`（`4 passed`），结果同步至 `docs/v2.0/test_report.md` v0.3。
  - Deployment：执行 `bash -n deploy-*.sh` 与 `docker-compose config -q`，语法与配置复核通过（仅 `version` 过时 warning），结果同步至 `docs/v2.0/deployment.md` v0.5。
  - 阶段状态：按 Phase 07 规则更新运行状态为 `wait_confirm`，等待人工确认后执行正式部署。
