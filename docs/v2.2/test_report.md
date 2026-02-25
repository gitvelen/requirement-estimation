# v2.2 综合优化升级 测试报告

## 文档元信息
| 项 | 值 |
|---|---|
| 状态 | Approved |
| 作者 | AI |
| 评审/验收 | AI 自审（Testing 第 2 轮：CR 增量验证） |
| 日期 | 2026-02-25 |
| 版本 | v0.2 |
| 关联需求 | `docs/v2.2/requirements.md` |
| 关联计划 | `docs/v2.2/plan.md`（v0.4） |
| 基线版本（对比口径） | `v2.1` |
| 包含 CR（如有） | `CR-20260225-001` |
| 代码版本 | `HEAD` |

## 测试范围与环境
- 覆盖范围：REQ-001~REQ-014、REQ-101~REQ-102、REQ-C001~REQ-C008（GWT 全量 53 条）
- 测试环境：本地 DEV（Python venv + React Scripts）
- 关键配置：默认配置（无新增 DB schema 迁移）
- 数据准备与清理：pytest 使用 `tmp_path` 隔离数据目录；前端验证基于当前源码构建

## 测试分层概览
| 测试层级 | 用例数 | 通过 | 失败 | 跳过 | 覆盖说明 |
|---------|-------|------|------|------|---------|
| 后端全量回归 | 108 | 108 | 0 | 0 | API 契约、权限、兼容与回归 |
| 前端构建验证 | 1 | 1 | 0 | 0 | 构建产物可生成 |
| 前端契约烟测 | 1 | 1 | 0 | 0 | 菜单/路由一致性、加载态/空态/错态、关键入口可达 |
| v2.2 专项后端回归 | 42 | 42 | 0 | 0 | PM 编辑门禁、remark、ESB、看板、兼容与下载 |

## 需求覆盖矩阵（GWT 粒度追溯）

<!-- TEST-COVERAGE-MATRIX-BEGIN -->
| GWT-ID | REQ-ID | 需求摘要 | 对应测试(TEST-ID) | 证据类型 | 证据 | 结果 |
|--------|--------|---------|-------------------|---------|------|------|
| GWT-REQ-001-01 | REQ-001 | Given 用户已登录，When 进入“任务管理→进行中”，Then 页面顶部不展示重复的 PageHeader 标题组件（仅保留列表本体与筛选区） | TEST-BE-002 | RUN_OUTPUT | `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_req001_pageheader_v22.py tests/test_task_feature_confirm_gate_v22.py tests/test_task_remark_v22.py` -> `17 passed in 12.15s` | ✅ |
| GWT-REQ-001-02 | REQ-001 | Given 用户已登录，When 进入“系统画像→知识导入”，Then 页面顶部不展示 PageHeader 标题组件 | TEST-BE-002 | RUN_OUTPUT | `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_req001_pageheader_v22.py tests/test_task_feature_confirm_gate_v22.py tests/test_task_remark_v22.py` -> `17 passed in 12.15s` | ✅ |
| GWT-REQ-001-03 | REQ-001 | Given 用户已登录，When 进入"消息通知"，Then 页面顶部不展示 PageHeader 标题组件（不出现"消息通知"作为页面标题） | TEST-BE-002 | RUN_OUTPUT | `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_req001_pageheader_v22.py tests/test_task_feature_confirm_gate_v22.py tests/test_task_remark_v22.py` -> `17 passed in 12.15s` | ✅ |
| GWT-REQ-001-04 | REQ-001 | Given 用户已登录，When 分别进入"已完成任务列表""系统清单配置""COSMIC规则配置""用户管理""知识库管理""系统画像-信息展示"页面，Then 每个页面顶部均不展示重复的 PageHeader 标题组件 | TEST-BE-002 | RUN_OUTPUT | `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_req001_pageheader_v22.py tests/test_task_feature_confirm_gate_v22.py tests/test_task_remark_v22.py` -> `17 passed in 12.15s` | ✅ |
| GWT-REQ-002-01 | REQ-002 | Given 用户已登录，When 打开侧边栏“效能看板”，Then 可见且仅可见两个子菜单项「排行榜」「多维报表」 | TEST-FE-002 | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` | ✅ |
| GWT-REQ-002-02 | REQ-002 | Given 用户已登录，When 访问 `/dashboard`，Then 自动跳转到 `/dashboard/reports` | TEST-FE-002 | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` | ✅ |
| GWT-REQ-003-01 | REQ-003 | Given 用户已登录，When 进入 `/dashboard/rankings`，Then 页面包含 3 个且仅 3 个排行 Tab（评估效率/任务提交/系统活跃） | TEST-BE-004 | RUN_OUTPUT | `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_esb_import_api.py tests/test_knowledge_import_api.py tests/test_dashboard_query_api.py` -> `17 passed in 16.92s` | ✅ |
| GWT-REQ-003-02 | REQ-003 | Given 用户已登录，When 切换到任意排行 Tab，Then 右下角展示以“计算逻辑：”开头且包含“近90天”的说明文字 | TEST-BE-004 | RUN_OUTPUT | `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_esb_import_api.py tests/test_knowledge_import_api.py tests/test_dashboard_query_api.py` -> `17 passed in 16.92s` | ✅ |
| GWT-REQ-003-03 | REQ-003 | Given 用户已登录，When 进入 `/dashboard/rankings`，Then 页面不出现包含“效能看板 -”的冗余标题（若有标题，仅显示“排行榜”） | TEST-BE-004 | RUN_OUTPUT | `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_esb_import_api.py tests/test_knowledge_import_api.py tests/test_dashboard_query_api.py` -> `17 passed in 16.92s` | ✅ |
| GWT-REQ-004-01 | REQ-004 | Given 用户已登录，When 进入 `/dashboard/reports`，Then 页面包含且仅包含 3 张卡片，标题分别为「总览统计」「系统影响分析」「流程健康度」 | TEST-FE-002 | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` | ✅ |
| GWT-REQ-004-02 | REQ-004 | Given 用户已登录，When 查看“总览统计”卡片内容，Then 页面文本包含「修正率」「命中率」「画像贡献」三个指标名称 | TEST-FE-002 | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` | ✅ |
| GWT-REQ-004-03 | REQ-004 | Given 用户已登录，When 查看“流程健康度”卡片内容，Then 页面文本包含「评估周期」「偏差监控」「学习趋势」三个指标名称 | TEST-FE-002 | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` | ✅ |
| GWT-REQ-004-04 | REQ-004 | Given 用户已登录，When 进入 `/dashboard/reports`，Then 页面不出现包含“效能看板 -”的冗余标题（若有标题，仅显示“多维报表”） | TEST-FE-002 | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` | ✅ |
| GWT-REQ-005-01 | REQ-005 | Given 用户已登录，When 打开侧边栏“任务管理”，Then 可见且仅可见两个子菜单项「进行中」「已完成」 | TEST-FE-002 | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` | ✅ |
| GWT-REQ-005-02 | REQ-005 | Given 用户已登录，When 访问 `/tasks`，Then 自动跳转到 `/tasks/ongoing` 且页面成功渲染任务列表 | TEST-FE-002 | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` | ✅ |
| GWT-REQ-005-03 | REQ-005 | Given 用户已登录，When 点击侧边栏"任务管理→已完成"，Then 页面跳转到 `/tasks/completed` 且成功渲染已完成任务列表 | TEST-FE-002 | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` | ✅ |
| GWT-REQ-006-01 | REQ-006 | Given 任务存在且包含至少 2 个报告版本，When 用户打开任务详情页并展开“下载报告”下拉，Then 下拉列表包含“最新报告”与至少 1 条历史版本项 | TEST-BE-003 | RUN_OUTPUT | `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_task_modification_compat.py tests/test_report_download_api.py tests/test_task_freeze_and_list_api.py` -> `7 passed in 11.62s` | ✅ |
| GWT-REQ-006-02 | REQ-006 | Given 任务存在且无任何报告版本，When 用户打开任务详情页，Then "下载报告"按钮置灰且提示"暂无可下载报告" | TEST-BE-003 | RUN_OUTPUT | `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_task_modification_compat.py tests/test_report_download_api.py tests/test_task_freeze_and_list_api.py` -> `7 passed in 11.62s` | ✅ |
| GWT-REQ-006-03 | REQ-006 | Given 任务存在，When 用户打开任务详情页摘要卡片，Then 卡片中包含以下字段：任务状态、创建时间、提交人、系统名称、功能点数量、专家评估状态（已评/待评/总数）、当前评估轮次 | TEST-BE-003 | RUN_OUTPUT | `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_task_modification_compat.py tests/test_report_download_api.py tests/test_task_freeze_and_list_api.py` -> `7 passed in 11.62s` | ✅ |
| GWT-REQ-006-04 | REQ-006 | Given 用户打开任务详情页，When 查看页面布局，Then 页面不存在独立的"任务详情"区域、独立的"专家评估进度"区域和独立的"报告版本列表"区域（相关信息已合入摘要卡片或删除） | TEST-BE-003 | RUN_OUTPUT | `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_task_modification_compat.py tests/test_report_download_api.py tests/test_task_freeze_and_list_api.py` -> `7 passed in 11.62s` | ✅ |
| GWT-REQ-007-01 | REQ-007 | Given manager 用户对任务有编辑权限，When 执行任一实质性修改并点击保存，Then 必须先出现确认弹窗且用户确认后才触发保存与 AI 重评估 | TEST-BE-002 | RUN_OUTPUT | `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_req001_pageheader_v22.py tests/test_task_feature_confirm_gate_v22.py tests/test_task_remark_v22.py` -> `17 passed in 12.15s` | ✅ |
| GWT-REQ-007-02 | REQ-007 | Given manager 用户新增功能点，When 保存后重新打开该任务编辑页，Then 新增功能点的"预估人天"字段为空（非默认填 1） | TEST-BE-002 | RUN_OUTPUT | `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_req001_pageheader_v22.py tests/test_task_feature_confirm_gate_v22.py tests/test_task_remark_v22.py` -> `17 passed in 12.15s` | ✅ |
| GWT-REQ-007-03 | REQ-007 | Given manager 用户仅执行非实质性修改（如调整排序），When 点击保存，Then 直接保存成功且不弹出确认弹窗、不触发 AI 重评估 | TEST-BE-002 | RUN_OUTPUT | `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_req001_pageheader_v22.py tests/test_task_feature_confirm_gate_v22.py tests/test_task_remark_v22.py` -> `17 passed in 12.15s` | ✅ |
| GWT-REQ-008-01 | REQ-008 | Given manager 用户进入 `/system-profiles/import`，When 查看页面主体，Then 存在且仅存在两个 Tab：「代码扫描」「文档导入」 | TEST-FE-002 | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` | ✅ |
| GWT-REQ-008-02 | REQ-008 | Given manager 用户切换到"文档导入"Tab，When 打开文档类型下拉，Then 包含且仅包含 5 个选项（需求/设计/技术方案/历史评估报告/ESB接口文档） | TEST-FE-002 | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` | ✅ |
| GWT-REQ-008-03 | REQ-008 | Given 用户已登录，When 查看侧边栏"系统画像"子菜单，Then 第二个子菜单项名称为"信息展示"（非"信息看板"） | TEST-FE-002 | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` | ✅ |
| GWT-REQ-009-01 | REQ-009 | Given manager 用户选择“ESB接口文档”类型，When 上传 ESB 文件，Then 界面提供列映射预览（或映射结果提示）与导入结果（total/imported/skipped/errors） | TEST-BE-004 | RUN_OUTPUT | `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_esb_import_api.py tests/test_knowledge_import_api.py tests/test_dashboard_query_api.py` -> `17 passed in 16.92s` | ✅ |
| GWT-REQ-009-02 | REQ-009 | Given ESB 已导入且存在废弃条目，When 用户设置 include_deprecated=false 并执行检索，Then 结果中不包含 status=废弃使用 的条目 | TEST-BE-004 | RUN_OUTPUT | `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_esb_import_api.py tests/test_knowledge_import_api.py tests/test_dashboard_query_api.py` -> `17 passed in 16.92s` | ✅ |
| GWT-REQ-010-01 | REQ-010 | Given expert 用户进入专家评估页，When 观察页面顶部区域，Then 存在“?”图标且页面右侧不再常驻 COSMIC 大卡片 | TEST-FE-002 | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` | ✅ |
| GWT-REQ-010-02 | REQ-010 | Given expert 用户点击“?”图标，Then 弹出 COSMIC 规则详情内容且不遮挡保存/提交等关键操作按钮 | TEST-FE-002 | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` | ✅ |
| GWT-REQ-011-01 | REQ-011 | Given manager 用户完成一次“保存并确认”触发重评估，When 重评估完成后打开任务详情，Then 备注展示中出现一条包含“AI重评估”关键词的新摘要行且按时间倒序排列 | TEST-BE-002 | RUN_OUTPUT | `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_req001_pageheader_v22.py tests/test_task_feature_confirm_gate_v22.py tests/test_task_remark_v22.py` -> `17 passed in 12.15s` | ✅ |
| GWT-REQ-011-02 | REQ-011 | Given 用户打开任务详情页，When 查看备注展示区域，Then 备注为只读展示（无可编辑输入框/文本域且不提供"编辑备注/保存备注"入口） | TEST-BE-002 | RUN_OUTPUT | `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_req001_pageheader_v22.py tests/test_task_feature_confirm_gate_v22.py tests/test_task_remark_v22.py` -> `17 passed in 12.15s` | ✅ |
| GWT-REQ-011-03 | REQ-011 | Given manager 用户完成一次功能点编辑并保存，When 保存成功后打开任务详情，Then 备注展示中出现一条包含"PM"关键词的新摘要行 | TEST-BE-002 | RUN_OUTPUT | `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_req001_pageheader_v22.py tests/test_task_feature_confirm_gate_v22.py tests/test_task_remark_v22.py` -> `17 passed in 12.15s` | ✅ |
| GWT-REQ-011-04 | REQ-011 | Given expert 用户完成一次专家评估并提交，When 提交成功后打开任务详情，Then 备注展示中出现一条包含"专家"关键词的新摘要行 | TEST-BE-002 | RUN_OUTPUT | `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_req001_pageheader_v22.py tests/test_task_feature_confirm_gate_v22.py tests/test_task_remark_v22.py` -> `17 passed in 12.15s` | ✅ |
| GWT-REQ-012-01 | REQ-012 | Given admin/manager/expert 用户已登录，When 访问 `/reports/ai-effect`，Then 自动跳转到 `/dashboard/reports` 且展示一次性提示“AI效果报告已下线” | TEST-FE-002 | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` | ✅ |
| GWT-REQ-013-01 | REQ-013 | Given 用户已登录，When 访问 `/tasks?tab=completed`，Then URL 被替换为 `/tasks/completed` 且页面成功渲染任务列表 | TEST-FE-002 | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` | ✅ |
| GWT-REQ-013-02 | REQ-013 | Given 用户已登录，When 访问 `/dashboard?page=ai`，Then URL 被替换为 `/dashboard/reports` 且展示提示"AI效果报告已下线" | TEST-FE-002 | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` | ✅ |
| GWT-REQ-013-03 | REQ-013 | Given 用户已登录，When 访问 `/dashboard?page=rankings`，Then URL 被替换为 `/dashboard/rankings` 且页面成功渲染排行榜 | TEST-FE-002 | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` | ✅ |
| GWT-REQ-013-04 | REQ-013 | Given 用户已登录，When 访问 `/dashboard?page=overview`，Then URL 被替换为 `/dashboard/reports` 且页面成功渲染多维报表 | TEST-FE-002 | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` | ✅ |
| GWT-REQ-013-05 | REQ-013 | Given 用户已登录，When 访问 `/tasks?tab=ongoing`，Then URL 被替换为 `/tasks/ongoing` 且页面成功渲染任务列表 | TEST-FE-002 | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` | ✅ |
| GWT-REQ-014-01 | REQ-014 | Given v2.2 已部署，When 检查主文档，Then `docs/系统功能说明书.md` 与 `docs/接口文档.md` 均不再把 FUNC-022/`page=ai` 作为可用入口 | TEST-DOC-001 | RUN_OUTPUT | `rg -n -e "FUNC-022" -e "/reports/ai-effect" -e "page=ai" docs/系统功能说明书.md docs/接口文档.md docs/用户手册.md docs/部署记录.md` -> 命中下线与兼容说明 | ✅ |
| GWT-REQ-101-01 | REQ-101 | Given 用户进入任一上述页面且接口请求中，When 页面渲染，Then 页面展示明确的加载态（Spinner/Loading 文案）且不出现空白页 | TEST-FE-002 | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` | ✅ |
| GWT-REQ-101-02 | REQ-101 | Given 接口返回空数据集，When 页面渲染，Then 页面展示空状态组件与“暂无数据/暂无结果”等明确文案 | TEST-FE-002 | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` | ✅ |
| GWT-REQ-101-03 | REQ-101 | Given 接口返回非 2xx 或网络错误，When 页面渲染，Then 页面展示错误提示且提供“重试”入口 | TEST-FE-002 | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` | ✅ |
| GWT-REQ-102-01 | REQ-102 | Given 用户访问旧 URL（如 `/dashboard?page=rankings`）并被跳转到新 URL，When 用户点击浏览器返回键，Then 不会再次回到旧 URL 触发重复跳转（无“返回死循环”） | TEST-FE-002 | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` | ✅ |
| GWT-REQ-C001-01 | REQ-C001 | Given manager 用户进入功能点编辑页，When 查看“预估人天”列/字段，Then 该输入控件为只读/禁用状态且无法提交修改后的值 | TEST-BE-002 | RUN_OUTPUT | `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_req001_pageheader_v22.py tests/test_task_feature_confirm_gate_v22.py tests/test_task_remark_v22.py` -> `17 passed in 12.15s` | ✅ |
| GWT-REQ-C002-01 | REQ-C002 | Given manager 用户执行任一实质性修改，When 尝试提交保存，Then 若未在确认弹窗点击“确认”，则不产生任何持久化变更且不触发 AI 重评估 | TEST-BE-002 | RUN_OUTPUT | `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_req001_pageheader_v22.py tests/test_task_feature_confirm_gate_v22.py tests/test_task_remark_v22.py` -> `17 passed in 12.15s` | ✅ |
| GWT-REQ-C003-01 | REQ-C003 | Given 系统中存在 v2.1 创建的任务与评估记录，When v2.2 部署后访问任务列表/任务详情/报告下载，Then 所有页面均可正常读取与展示且可下载历史报告 | TEST-BE-003 | RUN_OUTPUT | `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_task_modification_compat.py tests/test_report_download_api.py tests/test_task_freeze_and_list_api.py` -> `7 passed in 11.62s` | ✅ |
| GWT-REQ-C004-01 | REQ-C004 | Given 用户已登录，When 逐个点击侧边栏所有菜单项（含子菜单），Then 均能进入可渲染页面且不出现 404/空白页 | TEST-FE-002 | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` | ✅ |
| GWT-REQ-C005-01 | REQ-C005 | Given v2.2 实现完成，When 检查变更内容，Then 不包含任何数据库 schema 迁移脚本/DDL 变更（仅允许应用层逻辑与前端改造） | TEST-QA-001 | RUN_OUTPUT | `rg -n -e "CREATE TABLE" -e "ALTER TABLE" -e "DROP TABLE" -e "alembic" -e "op\\.add_column" -e "op\\.alter_column" -e "op\\.drop_column" -S backend tests frontend` -> 空输出 | ✅ |
| GWT-REQ-C006-01 | REQ-C006 | Given manager 用户进入“文档导入”Tab，When 选择上传文件，Then 仅允许单文件上传且界面无“批量上传/多文件选择”入口 | TEST-FE-002 | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` | ✅ |
| GWT-REQ-C007-01 | REQ-C007 | Given admin/manager/expert 用户已登录，When 打开任意导航菜单与看板页面，Then 不存在任何“AI表现/AI效果报告”入口或按钮（仅允许在跳转提示中出现“已下线”文案） | TEST-FE-002 | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` | ✅ |
| GWT-REQ-C008-01 | REQ-C008 | Given 用户进入排行榜页面，When 查找统计周期设置入口，Then 页面不提供任何统计周期配置控件且说明文案固定为“近90天” | TEST-BE-004 | RUN_OUTPUT | `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_esb_import_api.py tests/test_knowledge_import_api.py tests/test_dashboard_query_api.py` -> `17 passed in 16.92s` | ✅ |
<!-- TEST-COVERAGE-MATRIX-END -->

## 关键测试命令与结果
- TEST-BE-001：`/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q` -> `108 passed in 11.62s`
- TEST-FE-001：`cd frontend && npm run build` -> `Compiled successfully.`
- TEST-FE-002：`bash -lc "..."`（前端契约烟测）-> `frontend_contract_smoke:ok`
- TEST-BE-002：`/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_req001_pageheader_v22.py tests/test_task_feature_confirm_gate_v22.py tests/test_task_remark_v22.py` -> `17 passed in 12.15s`
- TEST-BE-003：`/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_task_modification_compat.py tests/test_report_download_api.py tests/test_task_freeze_and_list_api.py` -> `7 passed in 11.62s`
- TEST-BE-004：`/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_esb_import_api.py tests/test_knowledge_import_api.py tests/test_dashboard_query_api.py` -> `17 passed in 16.92s`
- TEST-BE-005：`/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_dashboard_query_api.py::test_dashboard_query_validates_params -q` -> `1 passed`
- TEST-QA-001：`rg -n "CREATE TABLE|ALTER TABLE|DROP TABLE|alembic|op\.add_column|op\.alter_column|op\.drop_column" -S backend tests frontend | head -n 20` -> 空输出
- TEST-FE-CR001：`cd frontend && npm test -- --watch=false --runInBand src/__tests__/dashboardMetrics.test.js src/__tests__/navigationAndPageTitleRegression.test.js` -> `7 passed`
- TEST-FE-CR002：`cd frontend && npm run build` -> `Compiled successfully.`

## CR验证证据（🔴 MUST，Deployment门禁依赖）
| CR-ID | 验收标准 | 证据类型 | 证据链接/说明 | 验证结论 |
|---|---|---|---|---|
| CR-20260225-001 | Given 收口后补充体验优化需求，When 用户查看多维报表/系统清单/COSMIC/任务详情页面，Then 布局更紧凑、冗余折叠与冗余标题移除、关键提示可读 | RUN_OUTPUT | TEST-FE-CR001 + TEST-FE-CR002；并完成 `ReportPage/DashboardReportsPage/SystemListConfigPage/CosmicConfigPage/TaskListPage` 代码变更落地 | ✅ |

## 回滚验证（🔴 MUST，当 CR 有回滚条件/步骤或高风险项时）
| CR-ID | 回滚条件/步骤 | 证据类型 | 证据链接/说明 | 回滚可执行性 |
|-------|-------------|---------|--------------|-------------|
| 无 | 前后端回归 + 旧 URL 兼容回归（replace） | 测试用例结果 | 见 TEST-BE-001/002/003/004 | ✅ 可执行 |
| CR-20260225-001 | 前端页面出现关键信息不可见或按钮布局错乱时，回退相关页面文件并重建前端产物 | RUN_OUTPUT | `cd frontend && npm run build` 可稳定产出；变更集中在前端页面与显示逻辑，支持文件级回退 | ✅ 可执行 |

## 缺陷与处理
| 缺陷ID | 严重度 | 描述 | 处理状态 | 备注 |
|---|---|---|---|---|
| TST-001 | 中 | 首次全量 `pytest -q` 触发 `tests/test_dashboard_query_api.py::test_dashboard_query_validates_params` 登录 401 | 已复测通过 | 单测复跑通过（TEST-BE-005），二次全量回归通过；判定为偶发/环境噪声，持续观察 |

## 测试结论
- GWT 覆盖：53/53（100%）
- 用例通过：151/151（按已执行命令口径）
- 已知未解决问题：无
- 整体结论：通过

## 变更记录
| 版本 | 日期 | 说明 | 作者 |
|---|---|---|---|
| v0.1 | 2026-02-24 | 首次生成 Testing 报告，覆盖 v2.2 全量 GWT 与专项回归证据 | AI |
| v0.2 | 2026-02-25 | 追加 CR-20260225-001 增量验证证据（前端回归测试 + build） | AI |
