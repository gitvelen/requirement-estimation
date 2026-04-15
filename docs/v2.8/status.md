---
_baseline: v2.7
_current: HEAD
_workflow_mode: manual
_run_status: running
_change_status: in_progress
_change_level: major
_review_round: 0
_phase: Proposal
---

| 项 | 值 |
|---|---|
| 版本号 | v2.8 |
| 变更目录 | `docs/v2.8/` |
| 当前阶段 | Proposal |
| 变更状态 | In Progress |
| 变更分级 | major |
| 基线版本（对比口径） | `v2.7` |
| 当前代码版本 | `feature/v2.8-wiki-profile-compile` |
| 本次复查口径 | diff-only |
| 当前执行 AI | Codex |
| 人类决策人 | User |
| 最后更新 | 2026-04-15 13:18 CST |
| 完成日期 |  |

## 变更摘要
- 启动 `v2.8` 功能迭代，目标是修复“文档导入后画像质量差 + 画像对最终估算影响弱”的问题。
- 随着实现范围扩展到画像存储模型、候选/发布链路、前后端展示、部署链路与运行态治理，当前提交口径已按实际规模升级为 `major`。
- 已固化用户口径：后端自动判型；判型不准不报错，优先把文档语义编译清楚；`wiki` 是画像候选生产层，`canonical` 是发布真相层；估算使用口径 C（优先 canonical，缺字段时补用高置信 wiki 候选）。
- 共享 `data/system_profiles.json` 已废除；系统级画像统一落在 `data/system_profiles/sid_<short-system-id>__<system_name>/` 每系统工作区内，按 `profile/source/candidate/audit` 分层组织。
- 本轮继续补齐 6 个缺口：`output` 决策日志、wiki source anchors、估算证据归档与前端展示、raw 管理 API、health 手动触发与归档、`docs/v2.8` 文档同步。
- 2026-04-10 STAGING/TEST 发布后新增发现目录治理问题：系统级 artifact 仍落在工作区根目录且目录名不可读；当前已回退修复根目录解析，并将存储模型重构为每系统工作区 + legacy 迁移兼容逻辑，然后回到 Testing 重新收口。
- 2026-04-11 增量补齐管理员“清空画像数据”能力：支持显式删除单系统 `profile/source/candidate/audit` 工作区，并同步清理画像链路产生的 runtime execution 与 profile_update memory 记录；板页已补 admin 操作入口。
- 2026-04-11 09:29 CST 已重新发布到 STAGING/TEST：前端重新 build，后端关键 runtime 文件同步进容器，补接 backend 到 frontend 所在网络后已恢复双容器可用。
- 2026-04-11 10:32 CST 已追加前端热修发布：修复 `cards_v1` 板页“编辑卡片 -> 应用到草稿”后卡片主体仍显示旧确认内容的问题；当前服务端首页已切换到 `static/js/main.427813d7.js`。
- 2026-04-11 10:56 CST 已追加前端 UI 补丁发布：增强 `cards_v1` 板页卡片分层与边界视觉，左侧 5 域导航改为滚动时 `sticky` 固定；当前服务端首页已切换到 `static/js/main.5f7e34f0.js`。
- 2026-04-11 11:18 CST 已追加 D3 卡片表格化补丁发布：`cards_v1` 板页中“对外提供能力 / 对外依赖能力”改为沿用 `v2.7` 的三列表格（`服务名称 / 交易名称 / 对端系统`）；当前服务端首页已切换到 `static/js/main.a989444c.js`。
- 2026-04-11 12:04 CST 已追加前端展示热修发布：`cards_v1` 板页不再显示伪候选徽标、`高可信基础资料`、`当前确认内容` 标题和“最近冲突”详情；当前服务端首页已切换到 `static/js/main.46a49c1e.js`。
- 2026-04-11 12:39 CST 已追加前端卡片紧凑化与 D3 链路重构发布：`cards_v1` 板页移除“已编辑”标记、统一收紧 5 域卡片留白，并将 D3“数据交换与批量链路”重构为“交互数据 / 上下游系统 / 触发与批量关系 / 链路说明”结构；当前服务端首页已切换到 `static/js/main.80730d28.js`。
- 2026-04-11 14:33 CST 已完成候选链路重构：`source -> candidate` 改为“单文档 candidate + 系统级 projection”双层模型，`candidate/latest` 改为保存系统级 `system_projection / merged_candidates / card_render`，并让估算上下文、板页候选和高可信导入统一消费 projection；系统清单与服务治理已同时接入 candidate/projection，且不再覆盖原有 document `ai_suggestions` 兼容镜像。
- 2026-04-11 14:50 CST 已将候选 projection 链路重构重新发布到 STAGING/TEST：后端运行态已同步 `document_skill_adapter / system_profile_service / profile_artifact_service / profile_health_service / system_profile_repository / system_catalog_profile_initializer / service_governance_profile_updater`，并通过容器健康、首页可达性、关键文件 hash 一致性校验；当前前端静态资源仍为 `static/js/main.80730d28.js`。
- 2026-04-11 21:50 CST 已追加 cards_v1 候选采纳热修发布：修复“点击采纳候选后，同值 projection 候选仍被重新渲染”的问题；后端运行态已同步 `profile_schema_service / system_profile_service`，并通过新增后端回归、容器健康、首页可达性与 host/container 文件 hash 一致性校验。
- 2026-04-11 22:20 CST 已追加 cards_v1 候选动作 stale-state 热修发布：修复页面状态略旧时点击“忽略候选/采纳候选”可能报 `card_candidate_not_found` 的问题；后端运行态已同步 `system_profile_service`，并通过新增后端回归、容器健康、首页可达性与 host/container 文件 hash 一致性校验。
- 2026-04-11 22:43 CST 已追加 cards_v1 候选区布局热修发布：卡片改为“当前内容在上、候选内容在下”的顺序，并同步修正文案；前端重新 build 后，服务端首页已切换到 `static/js/main.98167f3a.js`。
- 2026-04-13 11:28 CST 已根据业务反馈完成文档编译链路热修：`tech_solution` 导入会按章节信号扩展编译到 `requirements/design`，`4.6 主要功能说明` 可抽取到 D2 `functional_modules` 与 `business_scenarios`，同时 D3 `对外提供能力 / 对外依赖能力` 强制保持以管理员导入的服务治理数据为准；随后进入 Testing 收口。
- 2026-04-13 11:46 CST 已将本轮文档编译链路热修重新发布到 STAGING/TEST：后端运行态已同步 `document_skill_adapter / system_profile_service`，frontend 保持现有 `main.98167f3a.js` 静态资源并完成重启；容器健康、首页/API 可达性、宿主/容器 hash 一致性以及容器内 D2/D3 运行态烟测均已通过，当前状态为 `wait_feedback`。
- 2026-04-13 15:18 CST 已追加登录/导入阻断热修并重新发布到 STAGING/TEST：修复 dashboard 画像过期判断的 aware/naive datetime 混比、为同步导入链路补上 `5s + 单次尝试 + 禁止 chunking` 的 LLM 限幅降级，并在仓储层强制使用 workspace manifest 覆盖历史脏 `system_id/system_name`；后端运行态已同步 `routes / config / document_skill_adapter / profile_summary_service / system_profile_repository / llm_client`，frontend 维持 `main.98167f3a.js` 并完成重启，当前再次进入 `wait_feedback`。
- 2026-04-13 16:51 CST 已完成贷款核算画像解析链路全面修复并重新发布到 STAGING/TEST：补齐目录/TOC 干扰过滤、`功能性需求要点`/`主要功能说明` 双形态模块抽取、D3/D4/D5 模板噪声过滤，以及 `candidate/latest` 同源文档候选“最新覆盖旧版”合并规则；随后重新导入《贷款核算系统技术方案建议书v2.0》并刷新 projection，运行态已确认 D2 回填 10 个功能模块、D4 `performance_baseline` 清空、D5 `technical_constraints/known_risks` 清空，当前继续等待业务复验。
- 2026-04-14 15:24 CST 已收到业务反馈：管理员“规则管理”中点击“保存配置/重置为默认”报错；本地复现确认实际阻断点为 `POST /api/v1/cosmic/config`，原因是前端提交体漏传 `data_movement_rules.*.description` 导致后端 `422`，而 `POST /api/v1/cosmic/reset` 在管理员 Bearer token 下返回 `200`。当前已修复前端保存 payload 合并逻辑并补充前后端定向回归，状态回退到 Testing 收口。
- 2026-04-14 16:00 CST 已完成 COSMIC 规则管理热修并重新发布到 STAGING/TEST：前端规则页保存逻辑改为保留 `data_movement_rules.*.description` 后再提交，后端 COSMIC 配置存储切换为优先落到可写的 `REPORT_DIR/cosmic_config.json`（运行态为 `/app/data/cosmic_config.json`），同时 `reload` 与分析器读取同一路径；frontend 首页主包已切换到 `static/js/main.d3ac986e.js`，线上 `save/reset/reload` 均返回 `200`，当前重新进入 `wait_feedback`。
- 2026-04-14 16:38 CST 已根据业务复验继续追加运行态热修：定位到信息展示页仍显示旧 D1/D2/D5 标题并非浏览器缓存，而是 `requirement-backend` 容器内 `backend/service/profile_schema_service.py` 仍为旧版 schema，导致 `/api/v1/system-profiles/<system_name>` 返回 `D1 系统身份与定位 / D2 业务能力与业务对象 / D5 约束、要求与风险` 与旧 card key。现已将宿主当前 schema 文件重新同步进容器并重启 backend；线上接口复验已切换为 `D1 系统定位 / D2 业务能力 / D5 风险约束`，当前继续等待业务复验。
- 2026-04-14 19:05 CST 已完成画像链路解耦与导入鲁棒性热修并重新发布到 STAGING/TEST：后端新增 logical-field alias 归一、`candidate -> projection -> card` 统一 canonical 映射、文档 suggestion 语义门禁与 `validator_failures/rejected_candidates` 质量产物，以及管理员全量清空接口 `POST /api/v1/system-profiles/profile/reset-all`；运行态已同步 `system_profile_routes / document_skill_adapter / profile_schema_service / system_profile_service / system_profile_repository`，并通过 75 条定向后端回归、容器健康检查、宿主/容器 hash 一致性和新路由 `401` 实接口校验。
- 2026-04-14 19:23 CST 已按用户确认在 STAGING/TEST 执行历史画像全量清空：直接在 `requirement-backend` 容器内通过 `/app/.venv/bin/python` 调用 `reset_all_profile_workspaces(reason=\"v2.8_logical_field_rebuild\")`，实际删除 `200` 个系统 workspace、`7` 条 runtime execution 与 `206` 条 profile_update memory；宿主 `data/system_profiles`、容器 `/app/data/system_profiles` 与运行仓储枚举结果均已归零，`/api/v1/health` 仍返回 healthy。按用户决策，本次未做任何历史画像迁移或回填，后续应基于新链路重新导入。
- 2026-04-15 09:41 CST 已完成服务治理导入误报热修并同步到 STAGING/TEST：排查确认《接口治理台账》导入报“ESB文件缺少必填字段”实际根因是 `data/system_profiles` 下系统 workspace 被宿主侧 root 写入为 `root:root 755`，导致容器内 `appuser` 无法创建 `manifest.json.tmp`；本次已将 `/app/data/system_profiles` 全量纠正为 `appuser` 可写，并将 `backend/api/esb_routes.py` 的全局服务治理导入异常分类改为 `ValueError -> ESB_002`、其他运行时异常 -> `500 ESB_001/服务治理导入失败`，避免再把权限/IO 异常误报成模板缺字段。定向回归 `tests/test_esb_import_api.py tests/test_service_governance_import_v27.py` 共 `19 passed`，运行态 `/api/v1/health` healthy，宿主/容器 `esb_routes.py` hash 一致，当前继续保持 `wait_feedback`。
- 2026-04-15 10:16 CST 已完成“刷新后没反应/系统卡顿”热修并同步到 STAGING/TEST：排查确认 backend 容器虽然日志打印 `WORKERS=4`，但实际由 Docker `CMD ["uvicorn", ...]` 传入显式参数，导致 `entrypoint.sh` 的“无参数默认多 worker 分支”完全未执行，运行态长期只启动了单个 `uvicorn` 进程；在服务治理导入等同步 CPU/IO 请求期间，单 worker 会阻塞整站刷新与 Docker healthcheck，表现为 backend `unhealthy`、容器内 `curl http://localhost:443/api/v1/health` 超时、CPU 短时接近 `100%`。本次已为 `entrypoint.sh` 增加 `prepare_uvicorn_command()`，确保显式 `uvicorn` 启动也会自动补齐 `--workers ${WORKERS:-4}` 与 `--log-level info`，并已同步到运行态重启 backend；定向回归 `tests/test_entrypoint_script.py` 共 `2 passed`，容器内实际命令已变为 `uvicorn ... --workers 4 --log-level info`，日志出现 parent + 4 个 server process，宿主 `/api/v1/health` 约 `34ms`、容器内 `/api/v1/health` 约 `2ms`，idle CPU 回落到 `<1%`，当前继续保持 `wait_feedback`。
- 2026-04-15 11:46 CST 已处理“项目经理导入《需求变更申请表自营免息券按金额优惠优化》后 AI 长时间卡在 20%”问题：先定位到 `system_profile_service.search_relevant_profile_contexts()` 为系统识别前置检索误走 projection/ESB 重路径，已改为仅用当前 profile 的轻量 canonical/card 摘要做相关性评分；随后补 `llm_client.chat_with_system_prompt()` 对 `timeout/retry_times` 的透传，并让 `system_identification_agent` 复用既有 `PROFILE_IMPORT_LLM_TIMEOUT=5 / PROFILE_IMPORT_LLM_RETRY_TIMES=1` 限幅，避免系统识别在 LLM 不可达时长时间重试。定向回归新增 `tests/test_system_identification_memory_v27.py::test_search_relevant_profile_contexts_does_not_build_esb_context_for_relevance`、`tests/test_system_identification_memory_v27.py::test_identify_with_verdict_uses_budgeted_llm_timeout`、`tests/test_llm_client.py::test_chat_raw_retries_and_chat_with_system_prompt`、`tests/test_modification_trace_api.py::test_process_task_sync_clears_stale_error_after_success`，并通过 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_llm_client.py tests/test_system_identification_memory_v27.py tests/test_modification_trace_api.py`（`16 passed`）。运行态已同步 `system_profile_service / llm_client / system_identification_agent / routes`；同时确认当前 backend 进程环境仍沿用旧 `.env.backend` 的内网模型网关 `http://10.73.254.200:30000/v1`，容器内连接会 `ConnectTimeout`，已将 `.env.backend` 修正为公网 DashScope (`qwen-turbo` + `text-embedding-v2`) 口径，待下一次标准重建发布时正式生效。针对已卡住任务 `f16813f4-a436-4e7e-a216-55ef8b39ee2f`，本次通过一次性公网 LLM/embedding 覆写环境补跑，当前 `GET /api/v1/requirement/status/<task_id>` 已返回 `completed / 100 / 评估完成 / report_path=data/f16813f4-a436-4e7e-a216-55ef8b39ee2f_upload_20260415_114232.xlsx / error=null`，系统为 `贷款核算`、功能点数 `3`。
- 2026-04-15 13:12 CST 已按新 `.env.backend` 完成标准重建发布到 STAGING/TEST：第一次执行 `printf '2\n' | bash deploy-all.sh` 复现 backend 镜像构建在 `uv sync --frozen --no-dev` 下载 `charset-normalizer==3.4.4` 时超时失败；补充 `tests/test_docker_build_uv_network_tuning.py` 后，在 `Dockerfile` 中为构建期增加 `UV_HTTP_TIMEOUT=120`、`UV_HTTP_RETRIES=8` 默认参数，并在 `docker-compose.yml` 的 backend build args 中显式传入，再次执行标准脚本后 backend 镜像已成功重建并替换运行容器。运行态证据确认容器真实环境已切换为公网 DashScope 兼容模式：`DASHSCOPE_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1`、`LLM_MODEL=qwen-turbo`、`EMBEDDING_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1`、`EMBEDDING_API_STYLE=openai`、`EMBEDDING_MODEL=text-embedding-v2`；容器内 chat / embedding 最小探针均成功，backend 仍以 `uvicorn ... --workers 4 --log-level info` 运行，`/api/v1/health` healthy，历史卡住任务 `f16813f4-a436-4e7e-a216-55ef8b39ee2f` 复核仍为 `completed / 100 / error=null`。当前继续保持 `Deployment + wait_feedback`，等待业务复验。

## 目标与成功指标
| ID | 指标定义（可判定） | 基线（v2.7） | 目标（v2.8） | 统计窗口 | 数据源 |
|---|---|---|---|---|---|
| M1 | wiki 候选是否可追溯到原文锚点 | 候选仅有 value/confidence/reason | 每个已生成候选携带 `source_anchors` | 导入后 | `data/system_profiles/sid_<short-system-id>__<system_name>/candidate/latest/candidate_profile.json` |
| M2 | AI 决策动作是否写入 `audit` 审计层 | 采纳/忽略/回滚/发布仅写画像与事件 | 4 类动作均写 `decision_log` 记录 | 动作发生时 | `data/system_profiles/sid_<short-system-id>__<system_name>/audit/records/*.json` |
| M3 | 最终估算是否归档画像证据 | 返回体带上下文字段，但无落盘 | 每系统估算调用写 `estimation_context` 产物 | 估算时 | `data/system_profiles/sid_<short-system-id>__<system_name>/audit/estimation/latest_estimation.json` |
| M4 | 健康报告是否支持手动触发并归档 | 仅查询时现算 | 支持触发，并归档到 `data/system_profiles/sid_<short-system-id>__<system_name>/audit/health/latest_report.json` | 体检时 | 健康接口 + artifact 文件 |
| M5 | raw 管理是否暴露管理员维护入口 | 仅 service 内部可归档 | 提供 raw 查询与管理员归档 API | 管理动作时 | 系统画像 API |
| M6 | 评估/报告页是否展示画像上下文使用情况 | 页面无上下文痕迹 | 展示“是否使用画像 + 来源口径” | 前端渲染时 | EvaluationPage / ReportPage |

## 关键链接
- 提案：`proposal.md`
- 需求：`requirements.md`
- 设计：`design.md`
- 计划：`plan.md`
- 测试报告：`test_report.md`
- Minor 审查：`review_minor.md`
- 部署记录：`deployment.md`

## Active CR 列表（🔴 MUST，CR场景）
| CR-ID | 状态 | 标题 | 影响面（文档/模块/ID） | 链接 |
|---|---|---|---|---|
| - | - | - | - | - |

## Idea池（可选，非Active）
| CR-ID | 状态 | 标题 | 提出日期 | 优先级 | 链接 |
|---|---|---|---|---|---|
| - | - | - | - | - | - |

## 需要同步的主文档清单（如适用）
- [x] `docs/lessons_learned.md`
- [ ] `docs/系统功能说明书.md`
- [ ] `docs/技术方案设计.md`
- [ ] `docs/接口文档.md`
- [ ] `docs/用户手册.md`
- [x] `docs/部署记录.md`

## 回滚要点
- L1（流程级回滚）：保持 `v2.8` 变更留在独立分支，不合入主分支。
- L2（版本级回滚）：若后续合入后发现问题，回退至 `v2.7` 基线。

## 备注
- 2026-04-11 22:43 CST 已将“cards_v1 候选区应显示在当前内容下方”的前端热修重新发布到 STAGING/TEST，并完成整份板页回归、lint、build 与首页静态资源校验；当时状态为 `wait_feedback`。
- `review_minor.md` 已补齐本轮 Implementation + Testing 审查记录，并固化 `MINOR-TESTING-ROUND` 结果。
- 2026-04-10 09:57 CST 已完成过一次 STAGING/TEST 运行态发布；由于目录治理问题属于 post-deploy 新发现，当前该次 deployment 记录仅保留为历史证据，不作为当前待验收基线。
- `docs/v2.8` 为本轮首次补齐，目的是让后续工作不再继续挂靠 `docs/v2.7/status.md`。
- 2026-04-11 已新增 reset 自动化收口：60 条后端回归、12 条板页前端回归和 `SystemProfileBoardPage` 定向 lint 均已通过；09:29 CST 已完成重新 Deployment 并通过健康/连通性校验。
- 2026-04-13 已收到业务验收反馈：`《贷款核算系统技术方案建议书v2.0》` 的 `4.6 主要功能说明` 未进入 D2，且 D3 `对外提供能力 / 对外依赖能力` 仍需以服务治理导入为主；对应后端热修、定向回归与重新 Deployment 已完成，当前等待业务复验。
- 2026-04-13 16:51 CST 已对 `贷款核算` 真实工作区完成一次全链路刷新：最新 `candidate/latest/merged_candidates.json` 与 `profile/working.json` 中，`business_capabilities.canonical.functional_modules` 现为 10 个模块（`产品工厂` 至 `日终批量处理`），且容器内 `get_profile('贷款核算')` 验证结果与宿主一致。
- 2026-04-14 15:24 CST 已根据管理员规则管理报错反馈回退到 Testing：新增前端 `cosmicConfigPage.render.test.js` 覆盖“保存时保留 `data_movement_rules.description`”场景，并在后端 `test_api_regression.py` 补充管理员 Bearer token 下 `reset` 回归。
- 2026-04-14 16:00 CST 已重新发布 COSMIC 规则管理热修到 STAGING/TEST：标准 frontend build 受 `SystemProfileBoardPage.js` 既有重复 key lint 阻断，实际采用 `DISABLE_ESLINT_PLUGIN=true npm run build` 产出新静态资源，再将 `backend/api/cosmic_routes.py`、`backend/utils/cosmic_analyzer.py`、`backend/utils/cosmic_config_store.py` 同步进 `requirement-backend`；修正容器内文件权限后，线上 `save/reset/reload` 与健康检查均通过。
- 2026-04-14 16:38 CST 已补做信息展示页 schema 运行态对齐：容器内 `profile_schema_service.py` hash 原为旧版，与宿主文件不一致，导致 backend 继续生成旧 `domain_summary/card_keys`；现已重新 `docker cp` + 修正权限 + 重启 backend，接口复验确认 `domain_summary` 已切换到短标题与新 card key。
- 2026-04-14 19:23 CST 已执行用户批准的 destructive 清理：运行容器内 `reset_all_profile_workspaces()` 删除了全部历史 system profile workspace，并同步清掉关联 runtime execution / profile_update memory；校验结果为宿主目录 `0`、容器目录 `0`、仓储 `list_workspace_identities()` 返回 `0`，健康检查保持正常。

<!-- TEST-RESULT-BEGIN -->
TEST_AT: 2026-04-15 13:12 CST
TEST_SCOPE: v2.8-standard-rebuild-public-dashscope-runtime
TEST_RESULT: pass
TEST_COMMANDS: PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_docker_build_uv_network_tuning.py && printf '2\n' | bash deploy-all.sh && docker inspect requirement-backend --format '{{json .Config.Env}}' && docker exec requirement-backend sh -lc '/app/.venv/bin/python - <<'"'"'PY'"'"' ... print(settings.DASHSCOPE_API_BASE, settings.LLM_MODEL, settings.EMBEDDING_API_BASE, settings.EMBEDDING_API_STYLE, settings.EMBEDDING_MODEL) ... PY' && docker exec requirement-backend sh -lc '/app/.venv/bin/python - <<'"'"'PY'"'"' ... OpenAI chat/embedding probe ... PY' && curl -fsS http://127.0.0.1:443/api/v1/health && curl -fsS http://127.0.0.1:443/api/v1/requirement/status/f16813f4-a436-4e7e-a216-55ef8b39ee2f
<!-- TEST-RESULT-END -->

## 阶段转换记录
| 从阶段 | 到阶段 | 日期 | 原因 | 触发人 | 关键决策 |
|---|---|---|---|---|---|
| - | Proposal | 2026-04-09 | 启动 `v2.8` minor 版本迭代 | User + Codex | 聚焦文档编译式画像与估算接入 |
| Proposal | Requirements | 2026-04-09 | 用户确认核心口径 | User + Codex | 后端自动判型；wiki 为候选层；canonical 为发布层；估算口径 C |
| Requirements | Implementation | 2026-04-09 | minor 路径跳过 Design/Planning，进入实现 | User + Codex | 三层目录物理化，先补 raw/wiki/output |
| Implementation | Testing | 2026-04-10 | 六项缺口代码与自动化验证已完成 | Codex | 进入 Testing 收口，待后续审查/部署 |
| Testing | Deployment | 2026-04-10 | 已完成 STAGING/TEST 运行态发布并通过健康检查与一致性校验 | Codex | 标准 compose 重建卡在 `uv sync`，改走 runtime fallback 发布，状态切换为 wait_confirm 等待业务反馈 |
| Deployment | Implementation | 2026-04-10 | 用户指出 `raw/wiki/output` 系统级目录命名异常且根目录落盘不对，需要回退修复 | User + Codex | 废除共享 `system_profiles.json`，改为 `data/system_profiles` 每系统工作区，并补 legacy 迁移 |
| Implementation | Testing | 2026-04-10 | 存储模型重构完成并通过定向回归 | Codex | 已补根目录解析、每系统工作区、candidate bundle、legacy 迁移与文档口径同步 |
| Testing | Deployment | 2026-04-11 | reset 能力与 cards/direct-context 回归通过，已重新发布到 STAGING/TEST | Codex | 前端 build + backend runtime patch + 网络补接后，frontend/backend 均恢复可用 |
| Deployment | Testing | 2026-04-11 | 用户追加“candidate 不压缩 + 系统级 projection + 高可信源并入统一链路”实现需求，本地代码与回归已完成，待新一轮部署 | User + Codex | `candidate/latest` 改为系统 projection，`profile` 改为 rich canonical 发布层，catalog/governance 同步进入 candidate/projection |
| Testing | Deployment | 2026-04-11 | 候选 projection 链路重构已重新发布到 STAGING/TEST | Codex | 运行态已切换到系统级 projection candidate 链路，并完成健康/首页/关键文件 hash 校验，等待业务反馈 |
| Deployment | Implementation | 2026-04-13 | 用户反馈《贷款核算系统技术方案建议书v2.0》`4.6 主要功能说明` 未被编译到 D2，且要求 D3 提供/依赖能力继续以服务治理导入为主 | User + Codex | 回退到实现阶段，修正文档判型、D2 模块抽取与 D3 治理字段过滤逻辑 |
| Implementation | Testing | 2026-04-13 | 文档编译链路热修完成并通过定向后端回归 | Codex | `tech_solution` 扩展编译到 `requirements/design`，`主要功能说明` 回填 D2 模块/场景，D3 `provided/consumed` 候选强制 governance-only |
| Testing | Deployment | 2026-04-13 | 文档编译链路热修已重新发布到 STAGING/TEST | Codex | 运行态已同步 `document_skill_adapter / system_profile_service`，并通过容器健康、首页/API、hash 一致性与容器内 D2/D3 逻辑烟测校验 |
| Deployment | Implementation | 2026-04-13 | 用户补充反馈“系统名称异常 + manager 重登长时间不可用”；排查确认登录后 dashboard 500、导入链路同步 LLM 易超时、画像读取残留旧 `system_id` | User + Codex | 回退到实现阶段，优先修复登录后接口阻断与导入降级问题，同时校正 manifest/历史 payload 身份漂移 |
| Implementation | Testing | 2026-04-13 | 登录/导入阻断热修完成并通过定向后端回归 | Codex | `dashboard` 改用 aware datetime stale 判定；导入链路增加同步 LLM budget guard；repository 读取强制以 manifest 标识为准 |
| Testing | Deployment | 2026-04-13 | 登录/导入阻断热修已重新发布到 STAGING/TEST | Codex | 运行态已同步 `routes / config / document_skill_adapter / profile_summary_service / system_profile_repository / llm_client`，并通过容器健康、首页/API、宿主/容器 hash 一致性及真实 `dashboard/profile/events/health-report` 接口校验 |
| Deployment | Implementation | 2026-04-13 | 用户要求对 D1-D5 做整体排查，确认不只 D2 缺失、还存在候选合并残留与模板噪声污染 | User + Codex | 回退到实现阶段，按“章节抽取 + 字段过滤 + 同源候选覆盖”三层修复 |
| Implementation | Testing | 2026-04-13 | 全面解析链路与候选合并规则修复完成，并通过 33 条定向后端回归 | Codex | `document_skill_adapter / document_text_cleaner / system_profile_service` 完成修订；新增“同文件最新候选覆盖旧候选”回归 |
| Testing | Deployment | 2026-04-13 | 全面解析链路修复已重新发布到 STAGING/TEST，并完成真实贷款核算文档重导入/projection 刷新 | Codex | 运行态已确认 D2=10 个模块、D4 `performance_baseline=null`、D5 `technical_constraints/known_risks=null`，frontend/backend 均已重启并通过健康校验 |
| Deployment | Testing | 2026-04-14 | 用户反馈管理员“规则管理”页点击“保存配置/重置为默认”报错；本地复现确认保存请求漏传 `data_movement_rules.*.description` 导致 `422`，reset 在管理员 Bearer token 下可用 | User + Codex | 回退到 Testing，修复规则页保存 payload 合并逻辑并补充前后端定向回归，待重新发布到 STAGING/TEST |
| Testing | Deployment | 2026-04-14 | COSMIC 规则管理热修已重新发布到 STAGING/TEST，并完成线上 `save/reset/reload` 实接口复验 | Codex | 前端主包切换到 `main.d3ac986e.js`；后端配置持久化改为 `/app/data/cosmic_config.json`；运行态健康与 COSMIC 管理接口均已通过，等待业务复验 |
| Deployment | Deployment | 2026-04-14 | 用户继续反馈信息展示页仍显示旧 D1/D2/D5；排查确认是 backend 容器内 `profile_schema_service.py` 漏同步导致 runtime schema 漂移 | User + Codex | 重新同步 `profile_schema_service.py` 并重启 backend；线上 `domain_summary` 已切换为短标题与新 card key，继续等待业务复验 |
| Deployment | Implementation | 2026-04-14 | 用户要求将 D2 排查结论扩展为“candidate 能正确喂给 profile，模块和画像字段变化都不能再把链路搞坏”，并明确历史画像不做迁移、按全量清空处理 | User + Codex | 采用 logical-field alias/semantic gate/全量清空能力替代旧字段直连与固定标题硬编码 |
| Implementation | Testing | 2026-04-14 | 画像链路解耦与导入鲁棒性热修完成，并通过 75 条定向后端回归 | Codex | projection/card/ignore 统一 canonical 归一；文档 suggestion 增加 `logical_field/validation_status` 与 `validator_failures/rejected_candidates` |
| Testing | Deployment | 2026-04-14 | 画像链路解耦与导入鲁棒性热修已重新发布到 STAGING/TEST，并完成运行态一致性校验 | Codex | backend 宿主/容器 5 个关键文件 hash 一致，`/health` 返回 healthy，`POST /api/v1/system-profiles/profile/reset-all` 运行态返回 `401` 证明新路由已生效 |
| Deployment | Deployment | 2026-04-15 | 用户要求按新 `.env.backend` 做标准重建发布；第一次标准脚本复现 `uv sync` 下载超时，补齐 Docker 构建期 `UV_HTTP_TIMEOUT/RETRIES` 后重新执行成功 | User + Codex | 已从 runtime patch 基线切回标准 compose 重建，backend 容器真实环境已切换为公网 DashScope 兼容模式且通过 chat/embedding 探针 |

## CR状态更新记录（部署后填写）
| CR-ID | 之前状态 | 之后状态 | 上线日期 | 备注 |
|-------|---------|---------|---------|------|

## 紧急中断记录
| 触发时间 | 原因 | 当前状态 | 恢复条件 |
|---|---|---|---|

## 技术债务登记（Deferred Items）
| 来源阶段 | RVW-ID / 问题描述 | 严重度 | defer 理由 | 缓解措施 | 目标处理版本 | 状态 |
|---------|-------------------|--------|-----------|---------|-------------|------|

## 质量债务登记（🔴 MUST）
| 债务ID | 类型 | 描述 | 风险等级 | 计划偿还版本 | 状态 |
|--------|------|------|---------|-------------|------|
