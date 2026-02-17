# Review Report：Requirements / v2.1

| 项 | 值 |
|---|---|
| 阶段 | Requirements |
| 版本号 | v2.1 |
| 日期 | 2026-02-11 |
| 基线版本（对比口径） | v2.0 |
| 当前代码版本 | `f1646b5` |
| 复查口径 | full |
| Active CR（如有） | 无 |
| 检查点 | 可验收性/一致性/可追溯/边界与异常/接口与指标口径 |
| 审查范围 | 文档（`docs/v2.1/requirements.md`、`docs/v2.1/proposal.md`、`docs/v2.1/status.md`）；只读走查现有实现用于证据对照 |
| 输入材料 | `docs/v2.1/requirements.md`、`docs/v2.1/proposal.md`、`docs/v2.1/status.md`、`frontend/src/pages/EditPage.js`、`backend/api/routes.py`、`backend/api/system_routes.py`、`backend/api/system_list_routes.py`、`system_list.csv`、`backend/system_list.csv` |

## 结论摘要
- 总体结论：✅ 通过（第 3 轮走查：P0(open)=0，P1(open)=0）
- Blockers（P0）：0
- 高优先级（P1）：6（RVW-001/002/003/006/007/008，均已 Fix）
- 其他建议（P2+）：4（RVW-004/005/009/010，均已 Fix）

## 关键发现（按优先级）

### RVW-001（P1）REQ-010/API-001 的“自动重评估”触发边界未锁定，容易一次保存触发多次 AI 评估
- 证据：
  - 需求描述倾向于“保存即触发重评估”（`docs/v2.1/requirements.md`：REQ-010、API-001）。
  - 现有前端保存逻辑为“逐字段多次 PUT”（`frontend/src/pages/EditPage.js`：`handleEditSave()` 对每个变化字段分别调用 `PUT /api/v1/requirement/features/{task_id}`），若按“保存后端即触发”实现将导致一次保存触发多次重评估。
    - 复现命令：`sed -n '170,240p' frontend/src/pages/EditPage.js`
- 风险：
  - 评估任务被重复触发（成本/耗时/并发压力），且“评估中置灰”会显著拖慢编辑效率，甚至造成不可用体验。
  - 备注生成/修改记录/画像沉淀的“同一次保存”边界不清，后续指标（修正率等）口径也会被污染。
- 建议修改：
  - 在 Requirements 里明确“重评估触发的事务边界/幂等策略”，并在 API 层落地一种清晰方案（二选一即可，推荐 1）：
    1) **新增单次触发接口**：保存变更仅落库与记录修改；由前端在“保存完成/确认保存”后调用 `POST /api/v1/tasks/{task_id}/reevaluate`（或等价接口）触发一次异步重评估；后端保证同一 task 同时只允许 1 个重评估任务（重复请求返回同一 job 状态）。
    2) **改造保存为批量提交**：将 `PUT /api/v1/requirement/features/{task_id}` 改为一次提交包含 `changes: []`，后端在该批次保存后仅触发一次重评估（并生成一次备注摘要）。
  - 对应补充验收标准（建议追加到 REQ-010/API-001）：一次“保存”动作无论包含多少字段变更，**最多触发 1 次**重评估；重复点击保存/网络重试不产生重复评估（幂等）。
- 验证方式（可复现）：
  - `rg -n \"PUT /api/v1/requirement/features\" docs/v2.1/requirements.md`
  - `rg -n \"axios\\.put\\(`/api/v1/requirement/features\" frontend/src/pages/EditPage.js`

### RVW-002（P1）REQ-022 对 legacy `system_list.csv` 的路径/唯一数据源描述与现状不一致，可能导致修复目标偏离
- 证据：
  - 现有代码读取路径为仓库根目录 `system_list.csv`（`backend/api/system_routes.py` 的 `CSV_PATH=.../system_list.csv`），而 `system_list.csv` 当前仅有表头（无系统数据）。
    - 复现命令：`sed -n '30,50p' backend/api/system_routes.py`
    - 复现命令：`cat system_list.csv`
  - 同时存在 `backend/system_list.csv` 且包含 123 行数据，但当前读取链路并未指向该文件。
    - 复现命令：`head -n 5 backend/system_list.csv && wc -l backend/system_list.csv`
- 风险：
  - 需求按“移除读取 backend/system_list.csv”实施后，根目录 `system_list.csv` 仍为空，Bug 仍可能存在（系统列表仍空/负责人字段缺失）。
  - “系统清单唯一口径”无法形成单一真相源，后续 system_identification/knowledge_import/dashboard 仍可能各走各路。
- 建议修改：
  - 在 REQ-022/API-005 中把“唯一数据源”落到可执行口径：**明确最终存储文件路径**（例如统一落到 `data/system_list.json` 或统一落到某个单一 CSV/JSON），并列出必须统一引用的模块清单（至少：`backend/api/system_routes.py`、`backend/service/knowledge_service.py`、`backend/agent/system_identification_agent.py`、系统清单导入确认流程）。
  - 明确 legacy 的判定：需要废弃的到底是根目录 `system_list.csv`、还是 `backend/system_list.csv`、或二者都需迁移/清理；避免仅清理一处导致残留。
- 验证方式（可复现）：
  - `rg -n \"system_list\\.csv\" backend -S`
  - 统一后在本地检查：系统清单 API 返回 items 非空，且负责人字段可用于 `filterResponsibleSystems()`。

### RVW-003（P1）指标口径需补齐/对齐：AI 命中率公式与现有实现不一致；PM 修正率/新增率缺少去重规则
- 证据：
  - 需求文档当前定义：`AI 命中率 = ai_estimation_days_total / final_estimation_days_total`（`docs/v2.1/requirements.md` 6.3 指标口径表）。
    - 复现命令：`sed -n '970,995p' docs/v2.1/requirements.md`
  - 现有实现的 AI “命中率/准确率”是按任务级阈值统计（`abs(ai-final)/final <= 20%`）得到 `hit_count/ai_metric_count`，语义不同。
    - 复现命令：`sed -n '2390,2445p' backend/api/routes.py`
  - 修改记录当前是“按字段变化”写入（一次 update 可能产生多条 modification），若直接用记录条数计算“修改的功能点数”会被放大。
    - 复现命令：`sed -n '1360,1415p' backend/api/routes.py`
- 风险：
  - 指标口径不一致导致“实现对不上验收”，看板结论不可解释，管理闭环无法落地。
  - 修正率/新增率失真会误导“画像需要增强”的判断与资源投入。
- 建议修改：
  - 明确 AI 命中率口径（二选一即可）：
    1) **沿用现有口径**：命中定义=误差阈值命中（建议沿用 v2.0 的 20%/0.5d 规则），命中率=命中任务数/统计任务数；并在 REQ-017/API-004 指标字段命名中体现“hit_rate”语义。
    2) **采用比值口径**：将 `ai/final` 改名为“AI估算比/偏差比”，避免与“命中率”混用；并定义如何展示 >100%（高估）与 <100%（低估）。
  - 对 REQ-016 补充“去重规则”：修正/新增的计数以**功能点维度**去重（同一功能点多字段修改只算 1）；并补充 AI 初始功能点总数的取值来源（优先 `ai_initial_features` 快照，否则降级）。
- 验证方式（可复现）：
  - `rg -n \"AI 命中率\" docs/v2.1/requirements.md`
  - 用 1 个任务样本手工对照：修改 1 个功能点 3 个字段，修正计数应为 1 而非 3。

### RVW-004（P2）Feature Flag 回滚“无需重启”的要求不现实，且前端回滚路径需补齐
- 证据：`docs/v2.1/requirements.md` REQ-101 提到“开关切换不需要重启服务（读取环境变量或配置文件热加载）”，但环境变量在进程运行期不可可靠热变更。
- 风险：紧急回滚时无法按预期快速生效；且 B-01/B-02 的 UI 行为（按钮显隐/只读）仅靠后端开关不足以回退到 v2.0 体验。
- 建议修改：
  - 明确开关生效方式：允许重启生效（降低复杂度）或改为配置文件/管理接口热更新（二选一）。
  - 补齐前端回滚策略：前端如何得知开关状态（配置接口/随响应下发），以及关闭开关后 UI 如何回退（例如显示“手动重评估”按钮、备注恢复可编辑）。

### RVW-005（P2）接口验收还缺“最小错误码/校验”集合，建议在 Requirements 或 Design 补齐
- 证据：API-001~API-005 已列出变更点，但对“必填/可选字段、错误码、权限失败、JSON 校验失败、并发/重复请求”缺少可直接验收的约束。
- 风险：实现阶段容易出现“行为实现了但边界不一致”，导致返工。
- 建议修改：为 API-001/002/004/005 补充最小错误码与校验规则（例如：actor 字段缺失时的兜底策略、module_structure 非法 JSON 的返回、perspective 越权访问的 403 等）。

## 建议验证清单（命令级别）
- [ ] 一致性检查：`rg -n \"REQ-0|REQ-1|SCN-|API-\" docs/v2.1/requirements.md`
- [ ] 自动重评估多次触发风险确认：`sed -n '170,240p' frontend/src/pages/EditPage.js`
- [ ] system_list 数据源残留扫描：`rg -n \"system_list\\.csv\" backend -S`
- [ ] AI 命中率口径对照：`sed -n '2390,2445p' backend/api/routes.py`

## 开放问题
- [x] B-01：选择"单次触发接口"还是"批量保存接口"作为重评估触发边界？→ **已决策：单次触发接口**（`POST /api/v1/tasks/{task_id}/reevaluate`），更易做幂等与回滚
- [x] C-01：系统清单最终唯一数据源落在什么文件/存储（路径/格式）？是否需要一次性迁移并清理两个 CSV？→ **已决策：唯一数据源为 `data/系统清单20260119.xlsx`**（通过系统清单配置页面维护）；两个 legacy CSV（根目录 + backend/）均需废弃清理
- [x] B-06c/指标：AI 命中率口径是否沿用 v2.0 阈值命中算法？若改为比值口径，指标名称与展示方式如何调整？→ **已决策：沿用 v2.0 阈值命中算法**（abs(ai-final)/final ≤ 20% 或绝对差 ≤ 0.5d），命中率 = 命中任务数/统计任务数

## 处理记录（建议由开发/人工填写）
| RVW-ID | 严重度 | 处理决策（Fix/Defer/Accept） | Owner | 说明 | 链接/证据 |
|---|---|---|---|---|---|
| RVW-001 | P1 | Fix | AI | 采用"新增单次触发接口"方案：PUT 仅落库，新增 `POST /api/v1/tasks/{task_id}/reevaluate`（API-006）一次性触发；补充幂等策略与验收标准 | REQ-010, API-001, API-006 |
| RVW-002 | P1 | Fix | AI | 明确两个 legacy CSV 均需废弃（根目录空 CSV + backend/123行 CSV）；列出 5 个必须统一引用的模块清单；补充验收标准 | REQ-022, API-005 |
| RVW-003 | P1 | Fix | AI | AI 命中率沿用 v2.0 阈值命中算法（abs(ai-final)/final≤20% 或 ≤0.5d）；修正率/新增率补充功能点维度去重规则；更新 6.4 指标口径表 | REQ-016, REQ-017, 6.4 指标口径 |
| RVW-004 | P2 | Fix | AI | 开关改为重启生效（降低复杂度）；补齐前端回滚路径：新增 `GET /api/v1/system/config/feature-flags` 配置查询接口，前端据此决定 UI 行为 | REQ-101 |
| RVW-005 | P2 | Fix | AI | 新增 6.3 错误码与校验规则表（11 条最小错误码集合），覆盖 API-001/002/004/005/006 | 6.3 错误码与校验规则 |
| RVW-006 | P1 | Fix | AI | 统一 REQ-011 的触发时机与 REQ-010/API-006 对齐，并补齐跨 Flag 场景（AUTO_REEVAL=false 且 AI_REMARK=true） | REQ-011, API-006 |
| RVW-007 | P1 | Fix | AI | API-001 的 actor 字段改为可选：请求缺失时后端从登录态提取默认值；对齐 REQ-103 的向后兼容口径，并调整 6.3 错误码描述 | API-001, REQ-014, REQ-103, 6.3 错误码 |
| RVW-008 | P1 | Fix | AI | 在 6.2 接口变更清单中补充 API-007 `GET /api/v1/system/config/feature-flags` 的正式定义，并在 6.3 补齐未登录错误码 | API-007, 6.2/6.3 |
| RVW-009 | P2 | Fix | AI | 明确 SCN-002 的触发机制：保存完成后由前端调用 API-006，后端检测无功能点进入“补充功能点”模式 | SCN-002, REQ-010 |
| RVW-010 | P2 | Fix | AI | 明确 REQ-010 部分保存失败策略：不回滚已保存字段、不触发 API-006，并补充验收条目 | REQ-010 |

---

## 2026-02-11 | 第 2 轮 | 审查者：AI（Claude）

### 审查角度
Requirements v0.2 全量走查：验证第 1 轮 RVW-001~005 修复质量，并按 Requirements 阶段审查清单（可验收性/完整性/一致性/可追溯/边界与异常/数据与错误码）进行全面复查。

### 上一轮问题处理状态
| RVW-ID | 严重度 | 上一轮描述 | 处理方式 | 本轮状态 |
|---|---|---|---|---|
| RVW-001 | P1 | 重评估触发边界未锁定 | Fix：新增 API-006 `POST reevaluate`，PUT 仅落库，幂等策略明确 | ✅ 已修复。REQ-010 主流程步骤 2~4 清晰区分 PUT（落库）与 POST（触发），验收标准含"3 PUT + 1 POST"测试用例 |
| RVW-002 | P1 | system_list.csv 路径/数据源不一致 | Fix：明确两个 CSV 废弃，列出 5 个统一模块 | ✅ 已修复。REQ-022 业务规则列出根目录 + backend/ 两个 CSV 及 5 个模块清单，验收标准含代码搜索验证 |
| RVW-003 | P1 | 指标口径不一致 | Fix：沿用 v2.0 阈值算法，补充去重规则 | ✅ 已修复。REQ-017 业务规则明确阈值公式，REQ-016 补充功能点维度去重键，6.4 指标口径表已更新 |
| RVW-004 | P2 | Feature Flag 热加载不现实 | Fix：改为重启生效，补齐前端回滚路径 | ✅ 已修复。REQ-101 明确"重启服务生效"，新增 `GET /api/v1/system/config/feature-flags` 及 UI 行为映射 |
| RVW-005 | P2 | 缺少错误码/校验集合 | Fix：新增 6.3 错误码表 | ✅ 已修复。6.3 节含 11 条错误码，覆盖 API-001/002/004/005/006 |

### 本轮新发现问题
| RVW-ID | 严重度 | 描述 | 证据 | 建议 |
|---|---|---|---|---|
| RVW-006 | P1 | REQ-011 备注生成触发时机与 REQ-010/API-006 不一致，且缺少跨 Flag 场景 | 见下方明细 | 统一触发时机描述，补充跨 Flag 场景 |
| RVW-007 | P1 | API-001 新增 actor 必填字段与 REQ-103 向后兼容矛盾 | 见下方明细 | actor 字段改为可选或排除 API-001 兼容要求 |
| RVW-008 | P1 | REQ-101 的 `GET /api/v1/system/config/feature-flags` 未在 6.2 接口变更清单中定义 | 见下方明细 | 新增 API-007 正式定义 |
| RVW-009 | P2 | SCN-002 "新增系统无功能点"的触发机制在 API-006 模型下未明确 | 见下方明细 | 补充 SCN-002 触发说明 |
| RVW-010 | P2 | REQ-010 部分字段保存失败时已保存字段的回滚策略未说明 | 见下方明细 | 补充异常处理或 Accept |

### RVW-006（P1）REQ-011 备注生成触发时机与 REQ-010/API-006 不一致，且缺少跨 Flag 场景
- 证据：
  - REQ-011 的"入口/触发"写为"功能点变更保存时自动触发"（`requirements.md` 第 483 行），暗示备注在 PUT 保存时生成。
  - 但 REQ-010 步骤 9 明确写"后端在重评估完成后自动生成备注"（第 452 行），API-006 也写"重评估完成后，后端自动生成一条备注摘要"（第 1010 行）。
  - 两处描述的触发时机不同：一个是"保存时"，一个是"重评估完成后"。
  - 此外，当 `V21_AUTO_REEVAL_ENABLED=false`（不触发重评估）但 `V21_AI_REMARK_ENABLED=true`（备注自动生成开启）时，备注何时生成？需求未覆盖此跨 Flag 场景。
- 风险：
  - 实现时对备注生成时机理解不一致，导致备注丢失或重复生成。
  - 跨 Flag 场景未定义会导致实现者自行决策，可能与预期不符。
- 建议修改：
  1. 统一 REQ-011 的"入口/触发"为"重评估完成后自动触发"（与 REQ-010/API-006 对齐）。
  2. 补充跨 Flag 场景：当 `V21_AUTO_REEVAL_ENABLED=false` 且 `V21_AI_REMARK_ENABLED=true` 时，备注在 PUT 保存完成后直接生成（降级为保存触发）；或明确此场景下备注也不生成。
- 验证方式：
  - `grep -n "入口/触发" docs/v2.1/requirements.md` 对比 REQ-010 与 REQ-011 的触发描述

### RVW-007（P1）API-001 新增 actor 必填字段（400 missing_actor）与 REQ-103 向后兼容矛盾
- 证据：
  - 6.3 错误码表（第 1017 行）：API-001 PUT features 接口，`actor_id` 或 `actor_role` 缺失时返回 400 `missing_actor`。
  - REQ-103（第 871~879 行）："除画像字段重构相关接口外的所有 API"保持向后兼容，"v2.0 前端可调用 v2.1 后端不报错"。
  - 现有前端 `EditPage.js` 的 `handleEditSave()` 不发送 `actor_id`/`actor_role`（代码证据：`feature_data: { [field]: newValue }`，无 actor 字段）。
  - PUT features 不是画像接口，属于 REQ-103 兼容范围，但新增必填字段会导致 v2.0 前端调用 v2.1 后端时返回 400。
- 风险：
  - v2.1 前后端虽然同步发布，但若后端先部署或灰度期间前端未更新，PUT 接口会全量报错。
  - 与 REQ-103 的验收标准"v2.0 前端可调用 v2.1 后端不报错"直接矛盾。
- 建议修改（三选一）：
  1. **actor 字段改为可选**（推荐）：缺失时后端从 session/token 中提取 user_id 和 role 作为默认值，不返回 400。
  2. 在 REQ-103 中明确排除 API-001（PUT features）的向后兼容要求。
  3. 保持 400 但在 REQ-103 验收标准中注明"API-001 因新增必填字段不兼容，需前后端同步部署"。
- 验证方式：
  - `sed -n '170,210p' frontend/src/pages/EditPage.js`（确认现有前端不发送 actor 字段）

### RVW-008（P1）REQ-101 的 Feature Flags 查询接口未在 6.2 接口变更清单中正式定义
- 证据：
  - REQ-101（第 850 行）描述了 `GET /api/v1/system/config/feature-flags` 接口，包括返回 3 个开关状态、前端据此决定 UI 行为。
  - 但 6.2 接口变更清单（第 956~1011 行）仅定义了 API-001~API-006，未包含此接口。
  - 现有后端代码中也不存在 feature flags 相关端点（`grep -rn "feature.flag\|feature_flag\|config/feature" backend/` 无结果）。
- 风险：
  - 实现阶段可能遗漏此接口，导致前端无法获取开关状态，回滚路径失效。
  - 缺少正式的请求/响应定义，实现者需自行设计。
- 建议修改：
  - 在 6.2 中新增 API-007 正式定义此接口：
    - 接口：`GET /api/v1/system/config/feature-flags`
    - 响应体：`{ "V21_AUTO_REEVAL_ENABLED": boolean, "V21_AI_REMARK_ENABLED": boolean, "V21_DASHBOARD_MGMT_ENABLED": boolean }`
    - 权限：所有已登录用户可读
  - 同步在 6.3 错误码表中补充此接口的错误码（如未登录 401）。
- 验证方式：
  - `grep -n "API-00" docs/v2.1/requirements.md`（确认 API 编号连续性）

### RVW-009（P2）SCN-002 "新增系统无功能点"的触发机制在 API-006 模型下未明确
- 证据：
  - SCN-002（第 130~147 行）："系统检测到该系统无功能点，自动触发 AI 补充功能点"。
  - REQ-010 业务规则（第 461 行）："若 PM 新增系统后未手工添加功能点，AI 自动补充功能点（SCN-002）"。
  - 但在 API-006 模型下，重评估由前端显式调用 `POST reevaluate` 触发。SCN-002 的"自动触发"是由前端调用 POST reevaluate 后后端检测无功能点自动补充？还是后端在 PUT 保存时检测并自动触发？
- 风险：
  - 实现者对"谁触发"理解不一致，可能导致新增系统后 AI 不补充功能点。
- 建议修改：
  - 在 SCN-002 或 REQ-010 中明确：前端在新增系统保存完成后同样调用 `POST /api/v1/tasks/{task_id}/reevaluate`，后端检测到该系统无功能点时自动进入"补充功能点"模式（而非"重评估"模式）。
- 验证方式：
  - 阅读 SCN-002 流程步骤，确认触发方式与 API-006 一致

### RVW-010（P2）REQ-010 部分字段保存失败时已保存字段的回滚策略未说明
- 证据：
  - REQ-010 异常与边界（第 467 行）："前端保存部分字段成功、部分失败时：不调用 reevaluate 接口，提示保存失败"。
  - 但已成功保存的字段是否需要回滚？当前逐字段 PUT 模式下，前 2 个字段已落库、第 3 个失败，数据处于不一致状态。
- 风险：
  - 数据部分更新导致功能点状态不一致（如模块名已改但描述未改）。
- 建议修改：
  - 明确策略（二选一）：
    1. **不回滚**（推荐，降低复杂度）：提示用户"部分字段保存失败，请重试"，用户可再次保存补齐。
    2. **前端回滚**：记录本次保存前的快照，失败时逐字段恢复。
  - 建议在 REQ-010 异常与边界中补充一句说明即可。

### 收敛判定
- 本轮后：P0(open)=0, P1(open)=3（RVW-006/007/008）, P2(open)=2（RVW-009/010）
- 距离收敛：否（3 项 P1 需处理）
- 建议：3 项 P1 均为文档补齐/对齐类问题，修复量小，建议 Fix 后即可收敛 Requirements 阶段

## 建议验证清单（命令级别）— 第 2 轮
- [ ] REQ-011 触发时机一致性：`grep -n "入口/触发" docs/v2.1/requirements.md`
- [ ] API-001 actor 字段兼容性：`sed -n '170,210p' frontend/src/pages/EditPage.js`
- [ ] Feature Flags 接口定义完整性：`grep -n "API-00" docs/v2.1/requirements.md`
- [ ] SCN-002 触发机制：`sed -n '130,147p' docs/v2.1/requirements.md`

---

## 2026-02-11 23:13 | 第 3 轮 | 审查者：AI（Codex / GPT-5.2）

### 审查角度
- 复核 Requirements v0.3 对 RVW-006~010 的修复完整性，并按 Requirements 阶段审查清单做一致性/可验收/可追溯抽查。
- 复查口径：full（基线 v2.0；当前代码版本 `f1646b5`；当前阶段 Requirements）

### 上一轮问题处理状态
| RVW-ID | 严重度 | 上一轮描述 | 处理方式 | 本轮状态 |
|---|---|---|---|---|
| RVW-006 | P1 | REQ-011 备注生成触发时机与 REQ-010/API-006 不一致，且缺少跨 Flag 场景 | Fix：统一触发时机描述 + 补齐跨 Flag 场景 | ✅ 已修复。证据：`rg -n "触发时机（与 REQ-010/API-006 对齐）" docs/v2.1/requirements.md` → 行 501 |
| RVW-007 | P1 | API-001 actor 必填字段与 REQ-103 向后兼容矛盾 | Fix：actor 字段改为可选 + 默认值策略；调整 6.3 错误码描述 | ✅ 已修复。证据：API-001 actor 可选（行 973）；REQ-103 明确可选与默认值（行 888）；6.3 `missing_actor` 兜底条件（行 1041） |
| RVW-008 | P1 | Feature Flags 查询接口未在 6.2 接口变更清单中正式定义 | Fix：补充 API-007 正式定义 + 6.3 401 | ✅ 已修复。证据：`^#### API-007`（行 1028）；6.3 API-007 401（行 1049） |
| RVW-009 | P2 | SCN-002 "新增系统无功能点"的触发机制在 API-006 模型下未明确 | Fix：明确保存完成后调用 API-006，后端进入“补充功能点”模式 | ✅ 已修复。证据：`^#### SCN-002`（行 130），流程步骤 3~4 |
| RVW-010 | P2 | REQ-010 部分字段保存失败时已保存字段的回滚策略未说明 | Fix：明确“不回滚/不触发 API-006”+ 补充验收条目 | ✅ 已修复。证据：异常策略（行 472）；验收条目（行 480） |

### 本轮新发现问题
| RVW-ID | 严重度 | 描述 | 证据 | 建议 |
|---|---|---|---|---|
| - | - | 本轮未发现新增 P0/P1 问题 | - | - |

### 建议验证清单（命令级别）— 第 3 轮
- [ ] RVW-006 触发一致性：`sed -n '487,530p' docs/v2.1/requirements.md`
- [ ] RVW-007 actor 兼容：`sed -n '860,910p' docs/v2.1/requirements.md` + `sed -n '968,980p' docs/v2.1/requirements.md`
- [ ] RVW-008 API-007 定义：`sed -n '1028,1055p' docs/v2.1/requirements.md`
- [ ] RVW-009/010 SCN-002 与部分失败策略：`sed -n '130,170p' docs/v2.1/requirements.md` + `sed -n '440,490p' docs/v2.1/requirements.md`

### 收敛判定
- 本轮后：P0(open)=0, P1(open)=0
- 距离收敛：是
- 建议：人工确认后可进入 Design 阶段，并按流程更新 `docs/v2.1/status.md` 当前阶段为 Design

---

## 2026-02-11 | 第 4 轮（确认走查） | 审查者：AI（Claude / Opus 4.6）

### 审查角度
Requirements v0.3 最终确认走查：按 Requirements 阶段审查清单（可验收性/完整性/一致性/可追溯/边界与异常/数据与错误码）做全面复核，确认是否满足进入 Design 阶段的条件。

### 上一轮问题处理状态
| RVW-ID | 严重度 | 上一轮描述 | 处理方式 | 本轮状态 |
|---|---|---|---|---|
| RVW-001~005 | P1/P2 | 第 1 轮发现（重评估触发边界/CSV 数据源/指标口径/Feature Flag/错误码） | Fix（v0.2） | ✅ 已修复（第 2 轮确认） |
| RVW-006 | P1 | REQ-011 备注生成触发时机不一致 + 跨 Flag 场景缺失 | Fix（v0.3） | ✅ 已修复。REQ-011 行 501-503 明确两种触发时机，与 REQ-010/API-006 对齐 |
| RVW-007 | P1 | API-001 actor 必填字段与 REQ-103 向后兼容矛盾 | Fix（v0.3） | ✅ 已修复。API-001 行 973 actor 可选；REQ-103 行 888 明确兼容策略 |
| RVW-008 | P1 | Feature Flags 查询接口未在 6.2 定义 | Fix（v0.3） | ✅ 已修复。API-007 行 1028-1035 正式定义；6.3 行 1049 补齐 401 错误码 |
| RVW-009 | P2 | SCN-002 触发机制不明确 | Fix（v0.3） | ✅ 已修复。SCN-002 行 142-143 明确调用 API-006 触发 |
| RVW-010 | P2 | REQ-010 部分保存失败回滚策略缺失 | Fix（v0.3） | ✅ 已修复。REQ-010 行 470-472 明确"不回滚"策略；行 480 补充验收条目 |

### 阶段审查清单逐项确认

#### ✅ 可验收性（Verifiability）
- 27 条需求（22 功能 + 5 非功能）均有验收标准/验收方法
- 功能性需求（REQ-001~022）全部使用 Given/When/Then 格式
- 非功能需求（REQ-101~105）使用叙述式验收方法，可接受（非功能需求的验收通常在 Testing/Deployment 阶段细化）
- REQ-010 验收标准覆盖：正常流程、幂等、部分失败、Flag 关闭、SCN-002 触发、评估中状态、通知、确认前不可提交（8 条，覆盖充分）

#### ✅ 完整性（Completeness）
- 1.4 覆盖性检查表：Proposal A-01~A-09、B-01~B-06、C-01 全部映射到 REQ，16/16 覆盖
- 场景覆盖：7 个 SCN 覆盖功能点编辑、知识导入、画像沉淀、效能管理、页面浏览、专家评估
- 数据字典：画像字段（4 字段）、module_structure 元素结构、修改记录扩展字段均已定义
- 接口变更：API-001~007 共 7 个接口，覆盖保存/画像/画像查询/看板/系统清单/重评估/Feature Flags
- 错误码：6.3 节 11 条最小错误码集合，覆盖 API-001/002/004/005/006/007
- 指标口径：6.4 节 7 项指标公式/周期/样本量/精度完整

#### ✅ 一致性（Consistency）
- Feature Flag 命名：V21_AUTO_REEVAL_ENABLED / V21_AI_REMARK_ENABLED / V21_DASHBOARD_MGMT_ENABLED 全文一致（分别出现 13/8/12 次）
- REQ-011 触发时机与 REQ-010/API-006 已对齐（行 501-503）
- API-001 actor 可选策略与 REQ-103 向后兼容已对齐（行 973 vs 行 888）
- AI 命中率口径：REQ-017（行 710）与 6.4 指标口径表（行 1060）一致，均为阈值命中算法
- 修正率去重规则：REQ-016（行 686）与 6.4（行 1058）一致，均为功能点维度去重

#### ✅ 可追溯性（Traceability）
- ID 编号完整：REQ-001~022 连续、REQ-101~105 连续、SCN-001~007 连续、API-001~007 连续，无缺号
- 交叉引用完整：所有 SCN 的"关联需求ID"指向有效 REQ；所有 REQ 的"关联"指向有效 SCN/API
- 覆盖性检查表双向可追溯：Proposal In Scope → REQ → 验收标准

#### ✅ 边界与异常（Boundary & Exception）
- REQ-010：评估中关闭页面、评估失败、部分保存失败、幂等重复请求、Flag 关闭回退均已覆盖
- REQ-011：LLM 调用失败降级、备注过长截断、跨 Flag 场景均已覆盖
- REQ-013：同模块同名功能覆盖、人工 desc 优先保留、旧数据不迁移均已说明
- REQ-022：系统清单存储文件不存在/为空返回空列表（6.3 错误码表）
- SCN-002：无功能点自动补充 vs 有功能点走重评估的分支已明确

#### ✅ 数据与错误码（Data & Error Codes）
- 6.1 数据字典：画像字段、module_structure、修改记录扩展字段定义完整
- 6.3 错误码：11 条，覆盖 missing_actor / task_not_found / task_locked / invalid_module_structure / permission_denied / system_not_found / invalid_perspective / unauthorized + 幂等返回
- 6.4 指标口径：7 项指标均有公式、统计周期、最小样本量、精度

### 本轮新发现问题
| RVW-ID | 严重度 | 描述 | 证据 | 建议 |
|---|---|---|---|---|
| - | - | 本轮未发现新增 P0/P1/P2 问题 | - | - |

### 观察项（不阻塞收敛，供 Design 阶段参考）
1. **非功能需求验收细化**：REQ-101（Feature Flag）、REQ-102（备份回滚）、REQ-105（状态反馈 1s SLA）的验收方法为叙述式，建议在 Design/Testing 阶段补充具体测试用例
2. **UI 需求主观性**：REQ-008 "视觉焦点"、REQ-004 "布局合理"等 UI 描述存在一定主观性，建议在 Design 阶段出 UI mockup 作为验收基准

### 收敛判定
- 本轮后：P0(open)=0, P1(open)=0, P2(open)=0
- 距离收敛：**是（已收敛）**
- 结论：Requirements v0.3 通过 4 轮审查（含 2 位独立审查者），10 项发现全部 Fix 并验证，阶段审查清单 6 项全部通过。**建议人工确认后进入 Design 阶段**。
