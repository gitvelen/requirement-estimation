# v2.1 多模块 UI/UX 优化与功能增强 任务计划

## 文档元信息
| 项 | 值 |
|---|---|
| 状态 | Done |
| 日期 | 2026-02-12 |
| 版本 | v0.3 |
| 基线版本（对比口径） | `v2.0` |
| Active CR（如有） | 无 |
| 关联设计 | `docs/v2.1/design.md`（v0.1） |
| 关联需求 | `docs/v2.1/requirements.md`（v0.3） |
| 关联状态 | `docs/v2.1/status.md` |

> 说明：本计划覆盖 v2.1 全量范围（REQ-001~022、REQ-101~105）。
> 来自 `review_design.md` 的 Defer 项（RVW-001）已下沉为 T004（系统清单数据源统一与迁移验证）。

## 里程碑
| 里程碑 | 交付物 | 截止日期 |
|---|---|---|
| M1 | 后端基础契约：API-001/006/007 + 审计字段 + 开关链路 | 2026-02-13 |
| M2 | 画像与系统清单：API-002/003/005 + 4 字段模型 + 数据源统一 | 2026-02-13 |
| M3 | 前端改造：9 页面 UI 精简 + 看板升级 + 编辑流程联动 | 2026-02-14 |
| M4 | 回归与发布准备：备份回滚演练 + 兼容性回归 + 文档同步 | 2026-02-14 |

## Definition of Done（DoD）
- [x] 需求可追溯：任务关联 `REQ/SCN/API/TEST` 清晰
- [x] 代码可运行：不破坏主流程，关键行为具备开关/回滚策略
- [x] 自测通过：列出验证命令/用例与结果
- [x] 安全与合规：鉴权/输入校验/敏感信息不落盘
- [x] 文档同步：必要时更新 requirements/design/操作说明

## 任务概览
### 状态标记规范
- `待办` - 未开始
- `进行中` - 正在处理
- `已完成` - 实现完成，自测通过

| 任务分类 | 任务ID | 任务名称 | 优先级 | 预估工时 | Owner | Reviewer | 关联CR（可选） | 关联需求项 | 任务状态 | 依赖任务ID | 验证方式 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 基础能力 | T001 | Feature Flag 与配置查询接口落地 | P0 | 4h | 默认 | AI-Reviewer | — | REQ-101, REQ-103, API-007 | 已完成 | — | pytest + curl |
| 后端 | T002 | 保存与重评估解耦（API-001/API-006） | P0 | 10h | 默认 | AI-Reviewer | — | REQ-010, REQ-011, REQ-014, REQ-105, API-001, API-006 | 已完成 | T001 | pytest + 接口幂等回归 |
| 后端 | T003 | 系统画像 4 字段模型与权限适配 | P0 | 8h | 默认 | AI-Reviewer | — | REQ-013, REQ-103, API-002, API-003 | 已完成 | T001 | pytest + 契约校验 |
| 后端 | T004 | 系统清单数据源统一与迁移验证 | P0 | 8h | 默认 | AI-Reviewer | — | REQ-022, API-005 | 已完成 | T001 | rg 检索 + API 回归 |
| 后端 | T005 | 看板指标扩展与口径实现 | P1 | 10h | 默认 | AI-Reviewer | — | REQ-003, REQ-015~REQ-021, REQ-104, API-004 | 已完成 | T001,T002,T003,T004 | pytest + 指标对账 |
| 前端 | T006 | UI 精简改造（系统清单/规则/任务/编辑） | P1 | 8h | 默认 | AI-Reviewer | — | REQ-001, REQ-002, REQ-004, REQ-005 | 已完成 | T001 | E2E + 截图 |
| 前端 | T007 | UI 精简改造（导入/看板/专家/全局文案） | P1 | 8h | 默认 | AI-Reviewer | — | REQ-006, REQ-007, REQ-008, REQ-009 | 已完成 | T001 | E2E + 截图 |
| 后端 | T008 | 功能点级修改记录机制复核与补齐 | P2 | 4h | 默认 | — | — | REQ-012, REQ-014 | 已完成 | T002 | 数据抽样对账 |
| 质量保障 | T009 | 备份回滚与兼容性回归 | P0 | 6h | 默认 | AI-Reviewer | — | REQ-102, REQ-103, REQ-101 | 已完成 | T002,T003,T004,T005,T006,T007,T008 | 演练记录 + 回归报告 |
| 收口 | T010 | 全链路联调、验收证据与文档收口 | P1 | 6h | 默认 | AI-Reviewer | — | REQ-001~REQ-022, REQ-101~REQ-105 | 已完成 | T009 | TEST 清单 + 文档检查 |

### 引用自检（🔴 MUST，R6）
**验证命令**（见 `.aicoding/templates/review_template.md` 附录 AC-03）：
```bash
VERSION="v2.1"

rg -o "REQ-[0-9]+" docs/${VERSION}/plan.md | LC_ALL=C sort -u > /tmp/plan_refs_${VERSION}.txt
rg "^#### REQ-[0-9]+[：:]" docs/${VERSION}/requirements.md | sed 's/^#### //;s/[：:].*$//' | tr -d '\r' | LC_ALL=C sort -u > /tmp/req_defs_${VERSION}.txt
LC_ALL=C comm -23 /tmp/plan_refs_${VERSION}.txt /tmp/req_defs_${VERSION}.txt
```
**检查项**：所有 REQ-ID 都存在于 requirements.md 中（期望差集为空）。

## 任务详情

### T001：Feature Flag 与配置查询接口落地
**分类**：基础能力  
**优先级**：P0  
**预估工时**：4h  
**Owner**：默认  
**Reviewer（可选）**：AI-Reviewer

**关联需求项**：REQ-101、REQ-103、API-007

**任务描述**：
- 固化 `V21_AUTO_REEVAL_ENABLED`、`V21_AI_REMARK_ENABLED`、`V21_DASHBOARD_MGMT_ENABLED` 的读取逻辑。
- 实现 `GET /api/v1/system/config/feature-flags`。
- 前端统一初始化读取开关，避免页面内分散读取。

**影响面/修改范围**：
- 影响模块：后端配置与路由、前端初始化流程
- 预计修改文件：`backend/api/routes.py`、`backend/config/*`、`frontend/src/*`

**验收标准**：
- [ ] 三个开关可独立返回正确状态
- [ ] 未登录访问返回 401（`unauthorized`）
- [ ] 关闭任一开关后前端行为可回退

**验证方式（必须可复现）**：
- 命令：`pytest -q tests/test_feature_flags_api.py`
- 命令：`curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/system/config/feature-flags`

**回滚/开关策略（如涉及线上行为变化）**：
- 回滚条件：开关读写异常导致关键功能不可用
- 回滚步骤：回退接口改造并恢复静态默认行为
- 开关/灰度：三个开关默认 true，可独立关闭

**依赖**：—

---

### T002：保存与重评估解耦（API-001/API-006）
**分类**：后端  
**优先级**：P0  
**预估工时**：10h  
**Owner**：默认  
**Reviewer（可选）**：AI-Reviewer

**关联需求项**：REQ-010、REQ-011、REQ-014、REQ-105、API-001、API-006

**任务描述**：
- API-001 仅负责持久化与修改记录，忽略客户端 remark 写入。
- API-006 实现异步触发、幂等复用、`force` 支持、`skipped` 语义。
- 补齐 `actor_id/actor_role` 默认提取策略与错误码。

**影响面/修改范围**：
- 影响模块：任务保存、重评估任务调度、通知联动
- 预计修改文件：`backend/api/routes.py`、`backend/service/*reevaluate*`

**验收标准**：
- [ ] 一次保存动作最多触发一次重评估
- [ ] 同一 task 并发请求 API-006 返回同一运行任务信息
- [ ] 备注在对应开关场景下按规则生成且不重复
- [ ] 评估状态反馈满足 REQ-105（1 秒内可见）

**验证方式（必须可复现）**：
- 命令：`pytest -q tests/test_task_reevaluate_api.py`
- 命令：`pytest -q tests/test_task_modifications_actor.py`

**回滚/开关策略（如涉及线上行为变化）**：
- 回滚条件：重评估任务排队异常或状态不可恢复
- 回滚步骤：关闭 `V21_AUTO_REEVAL_ENABLED`，保留手动触发入口
- 开关/灰度：按系统/用户灰度可在前端层控制触发入口

**依赖**：T001

---

### T003：系统画像 4 字段模型与权限适配
**分类**：后端  
**优先级**：P0  
**预估工时**：8h  
**Owner**：默认  
**Reviewer（可选）**：AI-Reviewer

**关联需求项**：REQ-013、REQ-103、API-002、API-003

**任务描述**：
- API-002/API-003 收敛到 4 字段模型。
- `module_structure` 结构校验与格式错误处理。
- 权限口径对齐：admin 全局写 + manager 主责/B角写。

**影响面/修改范围**：
- 影响模块：画像存储、权限判断、请求校验
- 预计修改文件：`backend/api/system_profile_routes.py`、`backend/service/*profile*`

**验收标准**：
- [ ] 仅返回并接受 4 字段模型
- [ ] 非法 `module_structure` 返回 `invalid_module_structure`
- [ ] 权限不满足时返回 `permission_denied`

**验证方式（必须可复现）**：
- 命令：`pytest -q tests/test_system_profile_v21_fields.py`

**回滚/开关策略（如涉及线上行为变化）**：
- 回滚条件：v2.1 画像读写异常
- 回滚步骤：恢复 `data/system_profiles.json` 快照并回退版本
- 开关/灰度：结构性变更不提供灰度开关

**依赖**：T001

---

### T004：系统清单数据源统一与迁移验证
**分类**：后端  
**优先级**：P0  
**预估工时**：8h  
**Owner**：默认  
**Reviewer（可选）**：AI-Reviewer

**关联需求项**：REQ-022、API-005

**任务描述**：
- 统一 `system_routes`、`system_list_routes`、`knowledge_service`、`system_identification_agent` 的系统清单读取路径到 `data/system_list.csv` / `data/subsystem_list.csv`。
- 落地迁移与校验脚本，覆盖 legacy 文件路径清理（对应 `review_design` RVW-001 defer 项）。

**影响面/修改范围**：
- 影响模块：系统清单 API、知识检索系统识别链路
- 预计修改文件：`backend/api/system_routes.py`、`backend/api/subsystem_routes.py`、`backend/service/knowledge_service.py`、`backend/agent/system_identification_agent.py`

**验收标准**：
- [ ] API-005 仅使用新数据源
- [ ] 代码检索不存在 legacy `CSV_PATH` 引用（目标模块内）
- [ ] 知识导入与系统识别链路使用统一系统清单

**验证方式（必须可复现）**：
- 命令：`rg -n "system_list\.csv|subsystem_list\.csv|CSV_PATH" backend/api/system_routes.py backend/api/subsystem_routes.py backend/service/knowledge_service.py backend/agent/system_identification_agent.py`
- 命令：`pytest -q tests/test_system_list_unified_source.py`

**回滚/开关策略（如涉及线上行为变化）**：
- 回滚条件：系统清单读取为空或识别链路异常
- 回滚步骤：恢复迁移前数据文件并回退代码
- 开关/灰度：不适用（数据源一致性强约束）

**依赖**：T001

---

### T005：看板指标扩展与口径实现
**分类**：后端  
**优先级**：P1  
**预估工时**：10h  
**Owner**：默认  
**Reviewer（可选）**：AI-Reviewer

**关联需求项**：REQ-003、REQ-015、REQ-016、REQ-017、REQ-018、REQ-019、REQ-020、REQ-021、REQ-104、API-004

**任务描述**：
- API-004 扩展管理驱动型指标返回结构。
- 视角参数由前端 `activeRole` 自动映射。
- 样本不足场景返回 `N/A/null`，避免误导。

**影响面/修改范围**：
- 影响模块：看板聚合逻辑、指标计算逻辑
- 预计修改文件：`backend/api/routes.py`、`backend/service/*dashboard*`

**验收标准**：
- [ ] 指标口径与 requirements 6.4 一致
- [ ] 样本不足返回 `N/A/null`
- [ ] `filters.ai_involved` 不再生效

**验证方式（必须可复现）**：
- 命令：`pytest -q tests/test_dashboard_metrics_v21.py`

**依赖**：T001,T002,T003,T004

---

### T006：UI 精简改造（系统清单/规则/任务/编辑）
**分类**：前端  
**优先级**：P1  
**预估工时**：8h  
**Owner**：默认  
**Reviewer（可选）**：AI-Reviewer

**关联需求项**：REQ-001、REQ-002、REQ-004、REQ-005

**任务描述**：
- 清理 subtitle 与冗余提示；调整按钮位置；保留关键信息区块。
- 功能点编辑页联动 T002 的状态提示与按钮状态。

**影响面/修改范围**：
- 影响模块：`SystemListConfigPage`、`CosmicConfigPage`、`TaskListPage`、`EditPage`
- 预计修改文件：`frontend/src/pages/*.js`

**验收标准**：
- [ ] 对应页面不再出现需求中定义的冗余文案
- [ ] 布局位置符合 REQ 描述

**验证方式（必须可复现）**：
- 命令：`npm run test -- --watchAll=false`
- 用例：`TEST-UI-001~004`

**依赖**：T001

---

### T007：UI 精简改造（导入/看板/专家/全局文案）
**分类**：前端  
**优先级**：P1  
**预估工时**：8h  
**Owner**：默认  
**Reviewer（可选）**：AI-Reviewer

**关联需求项**：REQ-006、REQ-007、REQ-008、REQ-009

**任务描述**：
- 处理知识导入、信息看板、专家评估页布局和全局冗余文案。
- 对齐看板页新增指标展示区域和空态提示。

**影响面/修改范围**：
- 影响模块：`SystemProfileImportPage`、`SystemProfileBoardPage`、`EvaluationPage`、全局 Layout
- 预计修改文件：`frontend/src/pages/*.js`、`frontend/src/components/*`

**验收标准**：
- [ ] UI 结构与需求一致
- [ ] 全局冗余文案清理完成

**验证方式（必须可复现）**：
- 命令：`npm run test -- --watchAll=false`
- 用例：`TEST-UI-005~008`

**依赖**：T001

---

### T008：功能点级修改记录机制复核与补齐
**分类**：后端  
**优先级**：P2  
**预估工时**：4h  
**Owner**：默认

**关联需求项**：REQ-012、REQ-014

**任务描述**：
- 对现有 v2.0 修改记录机制执行兼容复核。
- 核验新增 actor 字段与既有记录并存策略。

**验收标准**：
- [ ] 旧记录不破坏读取
- [ ] 新记录 actor 字段可用于统计与追溯

**验证方式（必须可复现）**：
- 命令：`pytest -q tests/test_task_modification_compat.py`

**依赖**：T002

---

### T009：备份回滚与兼容性回归
**分类**：质量保障  
**优先级**：P0  
**预估工时**：6h  
**Owner**：默认  
**Reviewer（可选）**：AI-Reviewer

**关联需求项**：REQ-102、REQ-103、REQ-101

**任务描述**：
- 执行 `data/` 关键文件备份与恢复演练。
- 验证 v2.0 调用方调用 v2.1（非画像接口）兼容。

**验收标准**：
- [ ] 备份恢复流程可执行
- [ ] 非画像接口兼容回归通过
- [ ] 三个开关关闭时可回退

**验证方式（必须可复现）**：
- 命令：`.venv/bin/pytest -q tests/test_api_regression.py tests/test_feature_flags_api.py`
- 命令：`bash -lc "mkdir -p /tmp/v21_backup_rehearsal && ORIG_HASH=$(sha256sum data/task_storage.json | awk '{print $1}') && cp data/task_storage.json /tmp/v21_backup_rehearsal/task_storage.json.bak && printf '\n' >> data/task_storage.json && cp /tmp/v21_backup_rehearsal/task_storage.json.bak data/task_storage.json && RESTORED_HASH=$(sha256sum data/task_storage.json | awk '{print $1}') && test "$ORIG_HASH" = "$RESTORED_HASH""`

**依赖**：T002,T003,T004,T005,T006,T007,T008

---

### T010：全链路联调、验收证据与文档收口
**分类**：收口  
**优先级**：P1  
**预估工时**：6h  
**Owner**：默认  
**Reviewer（可选）**：AI-Reviewer

**关联需求项**：REQ-001~REQ-022、REQ-101~REQ-105

**任务描述**：
- 汇总测试证据到 `test_report.md`。
- 完成主文档同步清单与阶段状态更新。

**验收标准**：
- [ ] 测试报告可追溯到 REQ/API
- [ ] `status.md` 与阶段文档版本一致

**验证方式（必须可复现）**：
- 命令：`pytest -q`
- 命令：`npm run test -- --watchAll=false`

**依赖**：T009

---

## 执行顺序
1. T001
2. T002 / T003 / T004（并行）
3. T005 / T006 / T007 / T008（并行）
4. T009
5. T010

## 风险与缓解
| 风险 | 影响 | 概率 | 缓解措施 |
|---|---|---|---|
| 重评估幂等实现缺陷导致重复任务 | 成本上升、体验劣化 | 中 | API-006 幂等键 + 并发回归测试 |
| 数据源迁移遗漏模块 | 系统列表口径分叉 | 中 | T004 强制 4 模块统一检索与回归 |
| 看板指标口径偏差 | 管理决策误导 | 中 | 指标对账脚本 + 样本阈值控制 |
| 画像结构变更回滚失败 | 数据不可读 | 低 | 部署前快照 + 恢复演练 |

## 开放问题
- [ ] 无（当前已知问题已转化为任务）

## 变更记录
| 版本 | 日期 | 说明 |
|---|---|---|
| v0.1 | 2026-02-12 | 初始化 Planning 文档；完成任务拆分、依赖编排、RVW-001（defer）任务化与命令级验收定义 |
| v0.2 | 2026-02-12 | 完成 T001~T004：开关接口、保存与重评估解耦、系统画像 4 字段与权限适配、系统清单数据源统一；补充并通过对应测试用例 |
| v0.3 | 2026-02-12 | 完成 T005~T010：看板口径实现、前端 UI 精简、修改记录兼容测试补齐、备份回滚演练与全链路回归证据收口 |
