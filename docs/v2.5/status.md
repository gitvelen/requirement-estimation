---
_baseline: v2.4
_current: HEAD
_workflow_mode: manual
_run_status: wait_confirm
_change_status: in_progress
_change_level: major
_review_round: 0
_phase: Requirements
---

| 项 | 值 |
|---|---|
| 版本号 | v2.5 |
| 变更目录 | `docs/v2.5/` |
| 当前阶段 | Requirements |
| 变更状态 | In Progress |
| 变更分级 | major |
| 基线版本（对比口径） | v2.4 |
| 当前代码版本 | HEAD |
| 本次复查口径 | full |
| 当前执行 AI | Codex |
| 人类决策人 | User |
| 最后更新 | 2026-03-07 |
| 完成日期 |  |

## 变更摘要
- 启动 v2.5 新版本迭代
- 完成 CR-20260305-001 范围澄清，状态从 Idea 更新为 Accepted
- 通过 ChangeManagement 阶段审查（第 2 轮），进入 Proposal 阶段
- 核心范围：五域展示重构（D1-D5）、知识导入模板下载、WebSocket 实时推送
- Proposal v0.3 已完成 6 轮审查，开放问题状态已符合阶段规则，进入 Requirements 阶段
- Requirements v0.4 已完成，通过审查（覆盖率 100%，23 个 GWT，无开放问题）；后续补充导航兼容、API 主/别名、REQ-007/008 页面语义，以及上传/数据兼容口径澄清，未引入范围变化
- Design v0.2 已完成审查收敛（P0/P1 open=0），进入 Planning 阶段
- Planning v0.1 已完成审查收敛（P0/P1 open=0），进入 Implementation 阶段
- Implementation 已完成 M1 后端主线（T001~T003）：`module_structure.children` 三层兼容、模板下载与 task-status 别名、WebSocket ping/pong 与状态推送
- 新增/更新回归证据：`tests/test_system_profile_v21_fields.py`、`tests/test_system_profile_import_api.py`、`tests/test_system_profile_permissions.py`、`tests/test_profile_summary_service.py`
- Implementation 已完成 M2 前端主线（T004~T005）：BoardPage 五域结构化展示、D2 三层树与阈值提示、混合 diff（文本/列表/表格/树形）；ImportPage 模板下载、WS 实时状态、失败降级 5 秒轮询（最多 10 次）
- 新增/更新前端验证证据：`frontend/src/__tests__/systemProfileBoardPage.v24.test.js`、`frontend/src/__tests__/systemProfileImportPage.render.test.js`
- M2 验证命令（2026-03-06）：
  - `cd frontend && CI=true npm test -- --watchAll=false --runInBand src/__tests__/systemProfileBoardPage.v24.test.js src/__tests__/systemProfileImportPage.render.test.js`（13 passed）
  - `cd frontend && npm run lint:system-profile-import`（0 warning，`--max-warnings=0` 通过）
  - `cd frontend && npx eslint src/pages/SystemProfileBoardPage.js`（0 warning）
- Implementation 已启动 T006（测试与证据）：后端回归 `42 passed`、前端回归 `13 passed`，并新增 `docs/v2.5/test_report.md`（v0.3，GWT 覆盖 23/23）。
- Deployment 已执行 T007（发布与回滚）：执行 `printf '2\n' | bash deploy-all.sh` 发布到 STAGING；buildx 版本不足时已自动回退 legacy builder；发布后 `docker-compose ps` 显示 backend `Up (healthy)`、frontend `Up`，健康检查通过。
- UAT 反馈更正（2026-03-06）：按 User 指出回查 `v2.4` 基线后确认“系统画像”菜单仅保留 `知识导入` 与 `信息展示`；已撤销误增路由（`/system-profiles/code-scan`、`/system-profiles/workbench`、`/code-scan`），并恢复 Import/Board 页面原有功能卡片；前端回归 `navigation + import + board`（11 passed）已通过。
- 主文档同步已完成：`docs/系统功能说明书.md`、`docs/技术方案设计.md`、`docs/接口文档.md`、`docs/用户手册.md`、`docs/部署记录.md` 已补齐 v2.5 增量记录。
- Implementation 审查已完成并收敛：新增 `docs/v2.5/review_implementation.md`（`REVIEW_RESULT: pass`）。
- 已进入 Testing 阶段并完成第 1 轮审查：`docs/v2.5/review_testing.md` 已收敛（`REVIEW_RESULT: pass`），其中 `GWT-REQ-104-01` 按 User 授权记录为 `DEFERRED_TO_STAGING`。
- Deployment 逆向走查补记（2026-03-06）：按 User 指示保留 `requirements.md` 为目标，不下修目标文档；已登记当前实现/测试证据缺口（ImportPage 模板下载/WS/降级链路、BoardPage `children` 递归交互未落地、D3/D5/混合 diff 清晰化呈现不足、`test_report.md` 前端证据漂移），详见 `docs/v2.5/review_implementation.md`、`docs/v2.5/review_testing.md`。
- `docs/v2.5/test_report.md` 已更新为 v0.4“证据补遗”口径：后端回归保持通过，前端细粒度 GWT 证据改记为 `EVIDENCE_GAP` 待补测/回填。
- 当前待办：STAGING 已部署；自动化证据、主文档同步与回滚演练均已收口，唯一剩余事项为 User 在 STAGING 窗口回填 `REQ-104` 最终主观验收结论。
- `CR-20260306-001` 已完成本轮澄清并转为 `Accepted`：`REQ-006` 明确为“下载模板按钮位于对应文档类型卡片内，且与导入操作同一行”；`REQ-C006`（虚拟滚动阈值）确认延期出本期。
- 因新增版本内范围调整 CR，v2.5 已从 `Deployment` 回切 `ChangeManagement` 完成范围澄清，并依次完成 Requirements / Design 回填。
- Planning v0.9 已按 `CR-20260306-001` 回填：移除 `REQ-C006` / 虚拟滚动本期覆盖，重置 T004~T007 以补齐前端实现与证据缺口，并明确 `REQ-006` 为卡片内下载按钮与导入同排。
- User 已确认进入 Implementation；当前开始执行 T004/T005，并按 UI 里程碑先展示 BoardPage 结构化改造成果。

- 2026-03-07 收口：已完成 `CR-20260306-001` 对应的 T004~T007，补齐 D1 页面级断言、导航范围门禁、`ModuleStructurePreview` 性能门槛、ImportPage WS/轮询/模板下载证据，并修复 `ImportPage` 依赖抖动与 D2 首屏性能超阈值问题。
- 最新自动化证据（2026-03-07）：后端 `42 passed`；前端 `24 passed`（`navigationAndPageTitleRegression` + `moduleStructurePreview` + `systemProfileBoardPage.v24` + `systemProfileImportPage.render`）；前端 lint 与 build 均通过。
- `docs/v2.5/test_report.md` 已更新为 v0.5：覆盖 21/21 个本期有效 GWT，其中 20 项 `PASS`、1 项 `DEFERRED_TO_STAGING`（`REQ-104`）。
- `docs/v2.5/deployment.md` 已更新为 v0.6：同步最新健康检查、基线回滚点、L2 回滚演练、构建产物与主文档同步状态。

## 目标与成功指标
| ID | 指标定义（可判定） | 基线（v2.4） | 目标（v2.5） | 统计窗口 | 数据源 |
|---|---|---|---|---|---|
| M1 | Phase 00 完成度 | 无 v2.5 变更单 | 完成 CR 澄清并进入 Proposal | 版本启动期 | `status.md` + `review_change_management.md` |
| M2 | 需求可追溯完整度 | 无 v2.5 REQ | v2.5 需求与 CR 建立双向追溯 | 需求阶段 | `requirements.md` + `plan.md` |

## 关键链接
- 提案：`proposal.md`
- 需求：`requirements.md`
- 设计：`design.md`
- 计划：`plan.md`
- 变更单（CR）：`cr/CR-*.md`
- 审查：`review_change_management.md` / `review_*.md`
- 测试报告：`test_report.md`
- 部署：`deployment.md`

## Active CR 列表（🔴 MUST，CR场景）
| CR-ID | 状态 | 标题 | 影响面（文档/模块/ID） | 链接 |
|---|---|---|---|---|
| CR-20260305-001 | Accepted | v2.5 版本启动与范围澄清 | proposal / requirements / design / plan / test_report / deployment | `cr/CR-20260305-001.md` |
| CR-20260306-001 | Accepted | v2.5 需求/设计实现缺口补齐 | requirements / design / plan / test_report / deployment / frontend | `cr/CR-20260306-001.md` |

## Idea池（可选，非Active）
| CR-ID | 状态 | 标题 | 提出日期 | 优先级 | 链接 |
|---|---|---|---|---|---|
| - | - | - | - | - | - |

## 需要同步的主文档清单（如适用）
- [x] `docs/系统功能说明书.md`
- [x] `docs/技术方案设计.md`
- [x] `docs/接口文档.md`
- [x] `docs/用户手册.md`
- [x] `docs/部署记录.md`

## 回滚要点
- L1（流程级回滚）：将 v2.5 变更停留在独立分支，不合入主分支。
- L2（版本级回滚）：如已合入，回退至基线 tag `v2.4`。

## 备注
- 本文件用于显式标记阶段/完成状态，避免仅靠"文件存在性"推断导致误判。
- 当前处于 Implementation 阶段：正在执行 `plan.md` v0.9 的 T004/T005；完成 `T004`（🏁）后将先向 User 展示页面结构化成果，再继续下一批任务。

---

## 阶段转换记录
| 从阶段 | 到阶段 | 日期 | 原因 | 触发人 | 关键决策 |
|---|---|---|---|---|---|
| - | ChangeManagement | 2026-03-05 | 初始化 v2.5 新版本迭代 | User+Codex | 基线锁定 `v2.4`，启动 `CR-20260305-001` |
| ChangeManagement | Proposal | 2026-03-05 | 完成 CR 范围澄清，通过第 2 轮审查 | User+Codex | 确认三项核心功能、兼容性策略、优先级、回滚策略 |
| Proposal | Requirements | 2026-03-06 | Proposal 完成 6 轮审查，开放问题状态符合规则 | User+Claude | P-DO/P-DONT/P-METRIC 完整，跨文档一致性已修复 |
| Requirements | Design | 2026-03-06 | Requirements 完成审查，覆盖率 100%，无开放问题 | User+Claude | 18 个 Proposal 锚点全部覆盖，23 个 GWT，禁止项清单完整 |
| Design | Planning | 2026-03-06 | Design 审查收敛，满足阶段出口门禁 | User+Codex | 已形成 `design.md` v0.2 与 `review_design.md`，追溯覆盖校验通过 |
| Planning | Implementation | 2026-03-06 | Planning 审查收敛，反向覆盖校验通过 | Codex | 已形成 `plan.md` v0.1 与 `review_planning.md`，REQ 覆盖 18/18 |
| Implementation | Testing | 2026-03-06 | Implementation 审查收敛，进入 Testing；Testing 审查通过，REQ-104 按 User 授权延期到 STAGING | Codex | 已形成 `review_implementation.md`（pass）与 `review_testing.md`（pass，`GWT_DEFERRED=1`） |
| Testing | Deployment | 2026-03-06 | Testing 审查收敛并进入 Deployment | Codex | 自动化回归通过，`GWT-REQ-104-01` 标记 `DEFERRED_TO_STAGING` |
| Deployment | ChangeManagement | 2026-03-06 | 版本内新增 CR-20260306-001，需要对已部署口径做范围澄清并回填下游文档 | User+Codex | `REQ-006` 明确下载按钮位置；`REQ-C006` 延期出本期 |
| ChangeManagement | Requirements | 2026-03-06 | `CR-20260306-001` 范围澄清与变更管理审查收敛 | User+Codex | `REQ-006` 按钮位置确认；`REQ-C006` 延期出本期，进入最早受影响阶段回填 |
| Requirements | Design | 2026-03-06 | User 确认进入 Design，开始回填 `CR-20260306-001` 的设计影响 | User+Codex | 设计优先同步 `REQ-006` 卡片内下载按钮与 `REQ-C006` 延期口径 |
| Design | Planning | 2026-03-06 | User 确认进入 Planning，开始回填 `CR-20260306-001` 的任务拆解 | User+Codex | 计划移除 `REQ-C006` / 虚拟滚动覆盖，并聚焦 T004~T007 的前端实现与证据补齐 |
| Planning | Implementation | 2026-03-06 | User 确认进入 Implementation，开始执行 `CR-20260306-001` 对应代码补齐 | User+Codex | 先执行 T004 BoardPage 结构化改造，再按里程碑展示结果 |

## CR状态更新记录（部署后填写）
| CR-ID | 之前状态 | 之后状态 | 上线日期 | 备注 |
|-------|---------|---------|---------|------|

## 紧急中断记录
| 触发时间 | 原因 | 当前状态 | 恢复条件 |
|---|---|---|---|

## 技术债务登记（Deferred Items）
| 来源阶段 | RVW-ID / 问题描述 | 严重度 | defer 理由 | 缓解措施 | 目标处理版本 | 状态 |
|---------|-------------------|--------|-----------|---------|-------------|------|
