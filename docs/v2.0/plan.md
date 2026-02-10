# 需求分析与评估系统 v2.0 任务计划

## 文档元信息
| 项 | 值 |
|---|---|
| 状态 | Done |
| 日期 | 2026-02-10 |
| 版本 | v1.6 |
| 基线版本（对比口径） | `v2.0.0` |
| Active CR（如有） | —（`CR-20260209-001` 已 Implemented） |
| 关联设计 | `docs/v2.0/design.md`（v0.16） |
| 关联需求 | `docs/v2.0/requirements.md`（v1.21） |
| 关联状态 | `docs/v2.0/status.md` |

> 说明：本计划覆盖 v2.0 增量修订 **CR-20260209-001（10项）**。其中 **T001~T026 为已交付 v2.0 基线任务**（保留历史参考）；本次 CR 新增 **T027~T037**，以这些任务的完成与回归证据作为收口依据。

## 里程碑
| 里程碑 | 交付物 | 截止日期 |
|---|---|---|
| M1 | 后端：API-016/017/018 + 权限口径（主责+B角）+ 旧格式解析安全（REQ-NF-007） | 2026-02-09 |
| M2 | 前端：activeRole 角色切换 + 任务管理Tab统一 + 系统画像两页体验优化 + 通知中心联动 | 2026-02-09 |
| M3 | 配置：系统清单双sheet导入（兼容单sheet）+ COSMIC 平铺Tab展示 | 2026-02-09 |
| M4 | 回归：pytest + 前端 build/test + `test_report.md` 追溯补齐（TEST-029~038） | 2026-02-09 |

**里程碑说明**：
- 本里程碑为 **CR-20260209-001** 的实现收口口径；阶段推进与证据落盘以 `docs/v2.0/status.md` 为单一真相源。

## Definition of Done（DoD）
- [x] 需求可追溯：任务关联 `REQ/SCN/API/TEST` 清晰
- [x] 代码可运行：不破坏主流程；旧接口向后兼容
- [x] 自测通过：列出验证命令/用例与结果
- [x] 安全与合规：鉴权/越权防护/输入校验/敏感信息不落盘
- [x] 错误响应统一：v2.0 新接口按 requirements 6.4 返回 `error_code/message/details/request_id`
- [x] 文档同步：必要时更新 requirements/design/操作说明

## 任务概览
### 状态标记规范
- `待办` - 未开始
- `进行中` - 正在处理
- `已完成` - 实现完成，自测通过

**任务状态维护说明**：
- 本表格包含 v2.0 基线已完成任务（T001~T026）与本次 CR 待实施任务（T027~T037）
- 实际执行期间的任务状态由 `docs/v2.0/status.md` 或项目管理系统（Issue Tracker）维护
- 每个任务完成后，建议在 `status.md` 中更新对应任务的状态，或在 DoD 检查清单中标记完成

| 任务分类 | 任务ID | 任务名称 | 优先级 | 预估工时 | Owner | Reviewer | 关联CR（可选） | 关联需求项 | 任务状态 | 依赖任务ID | 验证方式 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 基础 | T001 | 明确 system owner_id 口径与解析 | P0 | 4h | 默认 |  | — | REQ-019, REQ-NF-004 | 已完成 | — | 单测+样例文件 |
| 后端 | T016 | 系统清单 API-015 契约对齐 + 热加载缓存刷新 | P0 | 8h | 默认 |  | — | REQ-019, API-015 | 已完成 | — | pytest+curl |
| 基础 | T021 | 统一错误响应结构（v2.0 新接口） | P0 | 6h | 默认 |  | — | requirements 6.4 | 已完成 | — | pytest+curl |
| 后端 | T002 | 扫描任务 API-001（jobs）+ repo_archive + 安全校验 | P0 | 12h | 默认 |  | — | REQ-001, API-001 | 已完成 | T001 | pytest+curl |
| 后端 | T003 | 扫描入库 API-002（ingest）+ 画像完整度更新 | P0 | 8h | 默认 |  | — | REQ-002, REQ-004, API-002 | 已完成 | T002 | pytest+curl |
| 后端 | T004 | ESB 导入 API-003（imports）+ mapping_json 兼容 + 按 system_id 过滤 | P0 | 10h | 默认 |  | — | REQ-003, API-003 | 已完成 | T001 | pytest+curl |
| 后端 | T005 | 知识库导入 API-011（imports）+ knowledge_type/level +（可选）绑定系统 | P1 | 10h | 默认 |  | — | REQ-011, API-011 | 已完成 | T001 | pytest+curl |
| 后端 | T006 | 系统画像 API-004（列表/草稿/发布）+ API-012（完整度）+ 权限口径 | P0 | 12h | 默认 |  | — | REQ-004, REQ-013, API-004, API-012 | 已完成 | T001,T003,T004,T005 | pytest+curl |
| 后端 | T017 | AI 初始评估快照（ai_initial_features/count）落库 | P0 | 8h | 默认 |  | — | 数据字典、REQ-007（依赖） | 已完成 | — | pytest+回归 |
| 后端 | T007 | 修改轨迹 API-007 + original_ai_reasoning 补齐 + 保留期清理 | P0 | 10h | 默认 |  | — | REQ-007, API-007 | 已完成 | T017 | pytest+curl |
| 后端 | T008 | 任务冻结字段写入（frozen_at/owner_snapshot）+ 状态映射 | P0 | 10h | 默认 |  | — | REQ-009, REQ-020, 数据字典 | 已完成 | T001 | pytest+回归 |
| 后端 | T009 | 任务查询 API-010：filters + group_by_status + 资源级权限 | P0 | 10h | 默认 |  | — | REQ-010, REQ-020, API-010 | 已完成 | T008 | pytest+curl |
| 后端 | T018 | 内部检索 API-005 + 复杂度评估 API-006（含降级） | P1 | 16h | 默认 |  | — | REQ-005, REQ-006, API-005, API-006 | 已完成 | T003,T004,T005,T006 | pytest |
| 后端 | T020 | 专家差异统计 API-008 + 评估详情 API-013 契约对齐 | P1 | 12h | 默认 |  | — | REQ-008, REQ-012~015, API-008, API-013 | 已完成 | T009,T017 | pytest+curl |
| 后端 | T010 | 效能看板 API-009：widgets + drilldown_filters 口径对齐 | P1 | 16h | 默认 |  | — | REQ-009, REQ-018, REQ-020, API-009 | 已完成 | T008,T009,T006 | pytest+样例数据 |
| 后端 | T011 | 报告下载 API-014：专家权限 + 错误码对齐 | P1 | 6h | 默认 |  | — | REQ-017, API-014 | 已完成 | T009 | pytest+curl |
| 前端 | T012 | 效能看板页面（导航/视角/下钻到任务列表） | P1 | 16h | 默认 |  | — | REQ-018, REQ-020 | 已完成 | T010,T009 | 前端自测 |
| 前端 | T013 | 系统画像页：扫描/ESB/文档导入入口 + 草稿编辑/发布 | P1 | 16h | 默认 |  | — | REQ-001~004, REQ-011, API-001~004, API-011 | 已完成 | T002~T006 | 前端自测 |
| 前端 | T014 | 任务管理状态分组 + 评估页UI优化 + 完整度展示 + 报告下载 | P1 | 16h | 默认 |  | — | REQ-010, REQ-012~015, REQ-017 | 已完成 | T009,T006,T011 | 前端自测 |
| 前端 | T015 | COSMIC 配置简化（业务语言展示/默认折叠） | P2 | 10h | 默认 |  | — | REQ-016 | 已完成 | — | 前端自测 |
| 前端 | T022 | 菜单结构调整（移除效果统计/调整顺序/旧路由兼容） | P1 | 6h | 默认 |  | — | REQ-021 | 已完成 | — | 前端自测+build |
| 前端 | T023 | 系统画像工作台拆页（知识导入/信息看板） | P0 | 12h | 默认 |  | — | REQ-022, REQ-001~004, REQ-011 | 已完成 | T022 | 前端自测+build |
| 前端 | T024 | 规则管理“使用说明”移至Modal（移除顶部说明/默认折叠） | P1 | 6h | 默认 |  | — | REQ-016 | 已完成 | — | 前端自测+build |
| 后端 | T025 | 系统画像字段归一化（business_goals别名）+ 发布必填字段收敛 | P0 | 8h | 默认 |  | — | REQ-004, API-004 | 已完成 | — | pytest |
| 测试 | T026 | UI/UX增量回归用例补齐（后端字段/发布校验/前端路由） | P1 | 6h | 默认 |  | — | REQ-016/021/022 | 已完成 | T022~T025 | pytest + 前端 build/test |
| 后端 | T027 | 通知中心 API-017 契约对齐 + 留存清理 | P1 | 8h | 默认 |  | CR-20260209-001 | REQ-024, API-017 | 已完成 | — | pytest+curl |
| 后端 | T028 | 画像AI总结异步任务 + API-018 重试 + 字段来源标记 | P0 | 12h | 默认 |  | CR-20260209-001 | REQ-024, API-018, API-017, REQ-NF-004 | 已完成 | T027 | pytest+curl |
| 后端 | T029 | B角权限口径落地（主责+B角） | P0 | 10h | 默认 |  | CR-20260209-001 | REQ-004/022, REQ-NF-004, API-001/003/004/011/018 | 已完成 | — | pytest+curl |
| 后端 | T030 | 旧格式解析能力（.doc/.xls）+ 多入口格式扩展 | P0 | 16h | 默认 |  | CR-20260209-001 | REQ-027, REQ-NF-007, API-016, API-003, API-011 | 已完成 | — | pytest+docker build |
| 后端 | T031 | 系统清单双sheet导入兼容（主系统+子系统映射） | P1 | 12h | 默认 |  | CR-20260209-001 | REQ-019, API-015 | 已完成 | — | pytest+样例文件 |
| 前端 | T032 | activeRole角色切换 + 任务管理Tab统一 | P0 | 12h | 默认 |  | CR-20260209-001 | REQ-023, REQ-010 | 已完成 | — | build+前端自测 |
| 前端 | T033 | 系统画像知识导入页优化（仅负责系统+三栏卡片） | P1 | 10h | 默认 |  | CR-20260209-001 | REQ-022, REQ-013 | 已完成 | T029 | build+前端自测 |
| 前端 | T034 | 信息看板AI建议闭环（通知/采纳/忽略/重试） | P0 | 14h | 默认 |  | CR-20260209-001 | REQ-024, API-017/018 | 已完成 | T027,T028,T029 | build+前端自测 |
| 前端 | T035 | 编辑/评估/任务详情页体验优化（含专家“查看”权限修复） | P1 | 14h | 默认 |  | CR-20260209-001 | REQ-025, REQ-026, REQ-013, REQ-010 | 已完成 | — | build+前端自测 |
| 前端 | T036 | COSMIC 配置平铺Tab与使用说明交互补齐 | P2 | 8h | 默认 |  | CR-20260209-001 | REQ-016 | 已完成 | — | build+前端自测 |
| 测试 | T037 | 增量回归与追溯补齐（含 TEST-029~038） | P1 | 12h | 默认 |  | CR-20260209-001 | REQ-023~027, REQ-NF-007 | 已完成 | T027~T036 | pytest + 前端 build/test |

### 引用自检（🔴 MUST，R6）
> 目标：验证 plan.md 中引用的所有 **REQ/REQ-NF** 都存在于 requirements.md 中（避免编号漂移）。

**验证命令**（期望差集为空）：
```bash
# 提取 plan.md 中的所有 REQ/REQ-NF 引用
rg -o "REQ-(NF-)?[0-9]+" docs/v2.0/plan.md | LC_ALL=C sort -u > /tmp/plan_refs.txt

# 提取 requirements.md 中定义的所有 REQ/REQ-NF（只从定义行提取）
# 格式：#### REQ-001：... / #### REQ-NF-001：...
rg "^#### REQ-(NF-)?[0-9]+：" docs/v2.0/requirements.md | sed 's/^#### //;s/：.*//' | LC_ALL=C sort -u > /tmp/req_defs.txt

# 计算差集（plan 引用但 requirements 未定义的 REQ/REQ-NF）
LC_ALL=C comm -23 /tmp/plan_refs.txt /tmp/req_defs.txt
```

## 增量任务完成记录（2026-02-07 / 2026-02-08）
- T022：菜单调整与旧路由兼容已落地，`/reports/ai-effect` 重定向可用；菜单顺序符合 REQ-021。
- T023：系统画像拆页已落地，知识导入/信息看板分离，query 参数保持系统上下文同步。
- T024：COSMIC 使用说明迁移为右上角 Modal，页面顶部说明块移除，技术配置默认折叠。
- T025：后端支持 `business_goal -> business_goals` 归一化，发布必填收敛并保持向后兼容。
- T026：回归证据已落盘至 `docs/v2.0/test_report.md`（含 TEST-027/028）。
- 收口验证：`.venv/bin/pytest -q`（`60 passed`）；`cd frontend && npm run build && npm test -- --watchAll=false`（build成功，`4 passed`）。
- 2026-02-10 Deployment 观察窗口补充验证：后端最小回归 `8 passed in 4.78s`；前端 build/test 通过；主文档同步完成。
- 需求确认后复核（2026-02-08）：执行 R6 引用存在性自检（`comm -23 /tmp/plan_refs.txt /tmp/req_defs.txt`）结果为空，未发现 REQ/REQ-NF 编号漂移。

## 任务详情

### T001：明确 system owner_id 口径与解析
**分类**：基础
**优先级**：P0
**预估工时**：4h
**Owner**：默认

**关联需求项**：REQ-019、REQ-NF-004、API-015

**任务描述**：
- 统一系统清单中“主责”的字段约定（最小可用）：
  - 模板/导入 extra 中约定 `owner_id`（优先）或 `owner_username`
  - 模板建议新增两列：`owner_id`、`owner_username`；并支持中文别名表头映射到 canonical key
  - 若仅有姓名/展示名，映射失败时视为“未配置主责”，画像写操作拒绝并提示
- 提供 `resolve_system_owner(system_id/system_name)` 工具函数，供权限判断复用。

**验收标准**：
- [ ] 给定 system_list 含 owner_id，系统能正确判定 PM 是否为主责
- [ ] 给定 system_list 使用中文表头（如“系统负责人ID/账号”），导入后可正确映射到 `owner_id/owner_username`
- [ ] 给定 system_list 缺失 owner 信息，画像写操作返回 403（`AUTH_001`）或明确错误提示

**验证方式（必须可复现）**：
- 命令：`pytest -q tests/test_system_list_import.py`

**回滚/开关策略**：
- 保持旧权限逻辑不变；新逻辑仅用于 v2.0 新接口/新功能。

---

### T016：系统清单 API-015 契约对齐 + 热加载缓存刷新
**分类**：后端
**优先级**：P0
**预估工时**：8h
**Owner**：默认

**关联需求项**：REQ-019、API-015、错误码（SYSLIST_001/002/003）

**任务描述**：
- 对齐 API-015：
  - template 下载
  - batch-import 预览校验不落盘
  - confirm 才写入并触发热加载
- 热加载策略：
  - 写入后清理 system list / subsystem mapping 缓存（含 knowledge_service 的系统清单缓存）
- 回归：权限（仅 admin）、错误码对齐。

**验收标准**：
- [ ] 导入后无需重启即可让系统识别使用新清单
- [ ] 模板包含 `owner_id/owner_username` 两列，并在导入预览中能识别/提示缺失（按 requirements/ design 的口径）
- [ ] 非管理员调用导入接口返回 403（`AUTH_001`）

**验证方式**：
- 命令：`pytest -q tests/test_system_list_import.py`

---

### T021：统一错误响应结构（v2.0 新接口）
**分类**：基础
**优先级**：P0
**预估工时**：6h
**Owner**：默认

**关联需求项**：requirements 6.4（通用错误响应约定）

**任务描述**：
- 为 v2.0 新接口提供统一错误响应结构：`error_code/message/details/request_id`
- request_id 规则：
  - 优先透传请求头 `X-Request-ID`
  - 若缺失则服务端生成，并在错误响应中返回
- 兼容策略：不强制改造历史旧接口的返回结构；仅对 v2.0 新/改造接口强制执行。

**验收标准**：
- [ ] 任一 v2.0 新接口 4xx/5xx 错误分支返回结构符合 requirements 6.4
- [ ] 错误响应包含 `request_id` 且可用于日志串联
- [ ] 不破坏已有旧接口返回结构（回归通过）

**验证方式（必须可复现）**：
- 命令：`pytest -q`（新增错误响应回归用例）

**回滚/开关策略**：
- 统一错误响应仅对新接口生效；如出现兼容问题，可按路由/开关回退到旧返回结构。

---

### T002：扫描任务 API-001（jobs）+ repo_archive + 安全校验
**分类**：后端
**优先级**：P0
**预估工时**：12h
**Owner**：默认

**关联需求项**：REQ-001、REQ-NF-001、REQ-NF-003、REQ-NF-005、API-001、错误码（SCAN_001/004/005/006）

**任务描述**：
- 新增/改造 `POST /api/v1/code-scan/jobs` 与 `GET /api/v1/code-scan/jobs/{job_id}`：
  - JSON：repo_path（本地路径或 Git URL）
  - multipart：repo_archive（zip/tar.gz）+ options_json
- 安全校验：
  - 本地路径 allowlist（SCAN_004）
  - Git URL：默认可配置为禁用；启用时仅允许 `http/https/ssh` 且 host 在 allowlist（不满足视为无法访问 → SCAN_001）
  - repo_archive 安全解压（SCAN_005/006）
  - 并发上限（5）与排队（queued）
- 幂等：repo_hash/options_hash 命中返回已有 job_id；force=true 绕过。

**验收标准**：
- [ ] 本地路径不在 allowlist 时返回 `SCAN_004`
- [ ] Git URL 未启用或 host 不在 allowlist 时返回 `SCAN_001`（message 需可定位原因）
- [ ] 上传非法压缩包返回 `SCAN_005`
- [ ] 解压后超限返回 `SCAN_006`
- [ ] 同参数重复提交命中幂等返回同 job_id

**验证方式**：
- 命令：`pytest -q`（包含新增的 code-scan API 用例）
- 命令（建议固化回归子集）：`pytest -q tests/test_api_regression.py -k code_scan`
- 手工：`curl -X POST /api/v1/code-scan/jobs ...`

---

### T003：扫描入库 API-002（ingest）+ 画像完整度更新
**分类**：后端
**优先级**：P0
**预估工时**：8h
**Owner**：默认

**关联需求项**：REQ-002、REQ-004、API-002、API-004

**任务描述**：
- 实现 `POST /api/v1/code-scan/jobs/{job_id}/ingest`：
  - 从 result_path 读取能力条目
  - 写入向量库（knowledge_type=code）
  - 更新 system_profile 草稿：evidence_refs + completeness_score（code_scan=30）
- 幂等：重复 ingest 不重复写入（以 entry_id 去重）。

**验收标准**：
- [ ] ingest 后系统画像 completeness_score 至少包含 code_scan=30
- [ ] embedding 服务不可用返回 `EMB_001` 且不更新完整度

**验证方式**：
- 命令：`pytest -q`（包含新增的 ingest 用例）
- 命令（建议固化回归子集）：`pytest -q tests/test_api_regression.py -k ingest`

---

### T004：ESB 导入 API-003（imports）+ mapping_json 兼容 + 按 system_id 过滤
**分类**：后端
**优先级**：P0
**预估工时**：10h
**Owner**：默认

**关联需求项**：REQ-003、API-003、错误码（ESB_001/002/EMB_001）

**任务描述**：
- 新增 `POST /api/v1/esb/imports`（multipart）：
  - system_id 必填
  - mapping_json 支持 string 或 list[string]
  - 仅保留与 system_id 相关行，其余计 skipped
  - 写入向量库（knowledge_type=esb）
  - 更新系统画像 completeness（esb=30）

**验收标准**：
- [ ] 无必填列返回 `ESB_002`
- [ ] 过滤无关行计入 skipped

**验证方式**：
- 命令：`pytest -q tests/test_esb_service.py`

---

### T005：知识库导入 API-011（imports）+ knowledge_type/level +（可选）绑定系统
**分类**：后端
**优先级**：P1
**预估工时**：10h
**Owner**：默认

**关联需求项**：REQ-011、API-011、错误码（KNOW_001/002/EMB_001）

**任务描述**：
- 实现 `POST /api/v1/knowledge/imports`：
  - knowledge_type=document/code
  - level=normal/l0（document 才允许 l0）
  - 可选 system_name/system_id（若未提供则推断；推断失败不更新画像完整度）
- 更新系统画像的文档计数与 completeness_score（documents=0~40；排除 L0）。

**验收标准**：
- [ ] level=l0 不计入完整度文档计数
- [ ] embedding 不可用返回 `EMB_001`

**验证方式**：
- 命令：`pytest -q`（包含新增的 system-profile CRUD/权限 用例）
- 命令（建议固化回归子集）：`pytest -q tests/test_api_regression.py -k system_profile`

---

### T006：系统画像 API-004 + API-012（完整度）+ 权限口径
**分类**：后端
**优先级**：P0
**预估工时**：12h
**Owner**：默认

**关联需求项**：REQ-004、REQ-013、REQ-NF-004、API-004、API-012

**任务描述**：
- 实现/改造系统画像 CRUD：
  - 列表分页 + status/is_stale 过滤
  - 发布必填字段校验（PROFILE_003）
  - 发布成功写入向量库（knowledge_type=system_profile）
- 完整度接口 API-012：
  - 返回 breakdown +（建议）document_count
- 权限：
  - admin/expert：只读
  - PM：写仅主责；读为“主责或创建过涉及该系统任务”

**验收标准**：
- [ ] admin 不能调用画像写接口（返回403）
- [ ] PM 非主责不能写（返回403，AUTH_001）
- [ ] completeness 口径与 requirements 6.3 一致

**验证方式**：
- 命令：`pytest -q`（包含新增的 modification-trace 用例）
- 命令（建议固化回归子集）：`pytest -q tests/test_api_regression.py -k modification_trace`

---

### T017：AI 初始评估快照（ai_initial_features/count）落库
**分类**：后端
**优先级**：P0
**预估工时**：8h
**Owner**：默认

**关联需求项**：数据字典（task.ai_initial_features/count）、REQ-007（original_ai_reasoning 依赖）

**任务描述**：
- 在 AI 首次产出功能点列表的节点，固化快照：
  - `task.ai_initial_features = features`
  - `task.ai_initial_feature_count = len(features)`
- 幂等：只在首次写入（或新任务）写入，不允许 PM 后续修改污染分母与原始推理来源。

**验收标准**：
- [ ] 多次触发 AI 评估不会覆盖首次快照（除非显式 force/新任务）

**验证方式**：
- 命令：`pytest -q`

---

### T007：修改轨迹 API-007 + original_ai_reasoning 补齐 + 保留期清理
**分类**：后端
**优先级**：P0
**预估工时**：10h
**Owner**：默认

**关联需求项**：REQ-007、API-007、REQ-NF-006

**任务描述**：
- 新增 `POST /api/v1/tasks/{task_id}/modification-traces`
- 服务端补齐 `actor/recorded_at/original_ai_reasoning`
- 单条大小/截断规则落地
- 轨迹清理：写入时清理超过 retention_days 的记录

**验收标准**：
- [ ] reason_code 为空返回 `TRACE_001`
- [ ] original_ai_reasoning 不接受客户端传入（忽略/拒绝）

**验证方式**：
- 命令：`pytest -q`

---

### T008：任务冻结字段写入（frozen_at/owner_snapshot）+ 状态映射
**分类**：后端
**优先级**：P0
**预估工时**：10h
**Owner**：默认

**关联需求项**：数据字典（task.frozen_at/owner_snapshot）、REQ-009/REQ-020（口径依赖）

**任务描述**：
- 在“最终确认/完成”动作落点写入 frozen_at 与 owner_snapshot（幂等只写一次）
- 定义 workflow_status → API-010 status 的映射
- owner_snapshot 从系统清单读取主责信息并按最终系统拆分人天写入

**验收标准**：
- [ ] 重复确认不会覆盖 frozen_at
- [ ] owner_snapshot 写入后，API-010 owner_id 过滤可用

**验证方式**：
- 命令：`pytest -q tests/test_api_regression.py`

---

### T009：任务查询 API-010：filters + group_by_status + 资源级权限
**分类**：后端
**优先级**：P0
**预估工时**：10h
**Owner**：默认

**关联需求项**：REQ-010、REQ-020、API-010

**任务描述**：
- 扩展 `GET /api/v1/tasks`：
  - group_by_status
  - time_range/custom
  - system_id/owner_id/expert_id/project_id/ai_involved
  - 分页
- 权限：
  - admin/viewer：全量只读
  - PM：创建者 或 owner_snapshot 主责=本人
  - expert：参与任务

**验收标准**：
- [ ] PM 不能看到非创建且非其负责系统的任务
- [ ] expert 只能看到参与任务

**验证方式**：
- 命令：`pytest -q`（包含新增的 API-010 filters/group_by_status 用例）
- 命令（建议固化回归子集）：`pytest -q tests/test_api_regression.py -k \"group_by_status or owner_id\"`

---

### T018：内部检索 API-005 + 复杂度评估 API-006（含降级）
**分类**：后端
**优先级**：P1
**预估工时**：16h
**Owner**：默认

**关联需求项**：REQ-005、REQ-006、API-005、API-006、REQ-NF-002

**任务描述**：
- 新增内部检索接口 API-005：
  - 汇总 system_profile + code + documents + esb 的 top_k 检索结果
  - L0 文档：最多返回5条，排序降权（相似度×0.3）
  - embedding/向量库不可用时降级关键词匹配，并标记 degraded（内部接口）
- 新增复杂度评估 API-006：
  - 按 requirements 规则产出分项分数与 reasoning（业务规则/集成/技术难度）
  - 系统上下文缺失时默认 medium 并降低置信度
- REQ-NF-002（性能）落地：以 **Milvus** 作为验收后端；local 仅小规模/降级模式（提供可复现压测命令与结果）。

**验收标准**：
- [ ] API-005 的阈值/top_k 与 requirements 一致（0.6；capabilities<=20，documents<=10，l0<=5）
- [ ] API-006 输出包含 3 个分项分数与总分、level 与 reasoning
- [ ] Milvus 后端压测满足 REQ-NF-002 前置条件与指标（100k、top_k=20、P95<500ms），并输出可复现命令/结果摘要

**验证方式**：
- 命令：`pytest -q`
- 性能基准（Milvus）：在 Planning/Implementation 固化压测脚本与命令，结果写入 `docs/v2.0/test_report.md`

---

### T020：专家差异统计 API-008 + 评估详情 API-013 契约对齐
**分类**：后端
**优先级**：P1
**预估工时**：12h
**Owner**：默认

**关联需求项**：REQ-008、REQ-012、REQ-013、REQ-014、REQ-015、API-008、API-013

**任务描述**：
- API-013：对齐评估详情契约与权限（PM=创建者；expert=参与任务）
- API-008：实现专家均值与偏差统计：
  - by_feature + summary
  - 偏差% 公式与方向判定（AI高估/低估）
  - 偏差>20% 标记异常项列表

**验收标准**：
- [ ] expert 访问未参与任务返回 403（`AUTH_001`）
- [ ] 偏差计算公式与 requirements 一致

**验证方式**：
- 命令：`pytest -q`

---

### T010：效能看板 API-009：widgets + drilldown_filters 口径对齐
**分类**：后端
**优先级**：P1
**预估工时**：16h
**Owner**：默认

**关联需求项**：REQ-009、REQ-018、REQ-020、API-009

**任务描述**：
- 新增 `POST /api/v1/efficiency/dashboard/query`
- 按 `design.md 4.3.8` 实现 widgets（overview/rankings/ai/system/flow）
- 统计口径使用 frozen_at/owner_snapshot/final_estimation_days_by_system
- 返回 drilldown_filters 供前端下钻到 API-010

**验收标准**：
- [ ] 每个 page 至少返回 2 个 widget 且 sample_size 正确
- [ ] drilldown_filters 透传到 API-010 后列表结果与看板口径一致

**验证方式**：
- 命令：`pytest -q`

---

### T011：报告下载 API-014：专家权限 + 错误码对齐
**分类**：后端
**优先级**：P1
**预估工时**：6h
**Owner**：默认

**关联需求项**：REQ-017、API-014

**任务描述**：
- 改造 `GET /api/v1/tasks/{task_id}/report`：
  - expert 可下载参与任务报告
  - 任务未完成/未生成返回 `REPORT_003`
  - v2.0 仅支持 `format=pdf`；`format=docx` 返回 `REPORT_002`
- 保持现有文件路径与版本兼容

**验收标准**：
- [ ] expert 未参与任务下载返回 403（AUTH_001）
- [ ] 请求 `format=docx` 返回 400（REPORT_002）

**验证方式**：
- 命令：`pytest -q`

---

### T012：效能看板页面（导航/视角/下钻到任务列表）
**分类**：前端
**优先级**：P1
**预估工时**：16h
**Owner**：默认

**关联需求项**：REQ-018、REQ-020

**任务描述**：
- 左侧菜单：总览/排行榜/AI表现/系统影响/流程健康
- 顶部视角预设：executive/owner/expert（影响默认筛选，不改变口径）
- 点击榜单/趋势点：跳转任务列表并带筛选条件（drilldown_filters）

**验收标准**：
- [ ] PM 默认 owner 视角并自动过滤其负责系统

**验证方式**：
- 前端自测：本地启动 + 用不同角色登录验证

---

### T013：系统画像页：扫描/ESB/文档导入入口 + 草稿编辑/发布
**分类**：前端
**优先级**：P1
**预估工时**：16h
**Owner**：默认

**关联需求项**：REQ-001~004、REQ-011

**任务描述**：
- 系统画像列表/详情/草稿编辑/发布
- 触发代码扫描与 ingest、ESB导入、知识导入
- 显示 completeness_score 与 pending_fields

**验收标准**：
- [ ] 非主责 PM 不显示写入口或写操作被后端拒绝

**验证方式**：
- 前端自测

---

### T014：任务管理状态分组 + 评估页UI优化 + 完整度展示 + 报告下载
**分类**：前端
**优先级**：P1
**预估工时**：16h
**Owner**：默认

**关联需求项**：REQ-010、REQ-012、REQ-013、REQ-014、REQ-015、REQ-017

**任务描述**：
- 任务列表按状态分组（待处理/进行中/已完成）
- 评估页顶部展示完整度（API-012），长文字截断，时间格式统一
- 报告下载入口（权限由后端控制）

**验收标准**：
- [ ] 完整度接口失败不阻塞评估详情展示（显示“完整度未知”）

**验证方式**：
- 前端自测

---

### T015：COSMIC 配置简化（业务语言展示/默认折叠）
**分类**：前端
**优先级**：P2
**预估工时**：10h
**Owner**：默认

**关联需求项**：REQ-016、SCN-011

**任务描述**：
- 用业务语言展示 COSMIC 规则说明，技术配置默认折叠
- 提供“细/中/粗”拆分示例区域

**验收标准**：
- [ ] 管理员能看懂配置含义并可保持原有算法不变

**验证方式**：
- 前端自测

---

### T022：菜单结构调整（移除效果统计/调整顺序/旧路由兼容）
**分类**：前端
**优先级**：P1
**预估工时**：6h
**Owner**：默认

**关联需求项**：REQ-021、SCN-014

**任务描述**：
- 侧边栏移除“效果统计”菜单项（不展示 `/reports/ai-effect`）
- 调整一级菜单顺序：任务管理 → 配置管理 → 效能看板
- 兼容旧入口：用户直达 `/reports/ai-effect` 自动跳转 `/dashboard` 并提示迁移

**验收标准**：
- [ ] 左侧菜单不再展示“效果统计”
- [ ] 一级菜单顺序符合 REQ-021
- [ ] 访问 `/reports/ai-effect` 能自动跳转到效能看板并提示迁移

**验证方式**：
- 前端自测：登录后检查菜单与旧路由跳转
- 构建验证：`cd frontend && npm run build`

---

### T023：系统画像工作台拆页（知识导入/信息看板）
**分类**：前端
**优先级**：P0
**预估工时**：12h
**Owner**：默认

**关联需求项**：REQ-022、SCN-015；依赖接口：API-001/002/003/004/011/012

**任务描述**：
- 新增/调整路由：
  - `/system-profiles` 作为兼容入口重定向到 `/system-profiles/board`（携带 query）
  - `/system-profiles/import`：知识导入页（代码扫描/ESB导入/知识导入）
  - `/system-profiles/board`：信息看板页（概览/字段编辑/完整度分析/保存草稿/发布）
- 系统TAB同步：以 URL query（`system_name`，可选 `system_id`）在两页间保持同一选中系统
- 知识导入页不展示导入历史/最近任务列表：
  - 代码扫描仅展示“最近一次提交”的 `job_id + status`（手动刷新）与 completed 状态下的“入库”按钮
  - ESB/知识导入仅展示本次导入统计与 toast 提示
- 权限交互：
  - 非主责 PM：仅可只读查看信息看板，不展示写操作入口（或点击后提示只读）

**验收标准**：
- [ ] 菜单“配置管理 → 系统画像”下包含“知识导入/信息看板”两个入口
- [ ] 知识导入页无导入历史/任务列表；但操作后有最小反馈（scan job 状态/导入统计）
- [ ] 信息看板页显示系统概览、7字段编辑、完整度分析，并可保存草稿/发布（仅主责）
- [ ] TAB 同步：在知识导入选择系统B，切到信息看板默认仍为系统B

**验证方式**：
- 前端自测：按 GWT 手工走查（主责/非主责 PM）
- 构建验证：`cd frontend && npm run build`

---

### T024：规则管理“使用说明”移至Modal（移除顶部说明/默认折叠）
**分类**：前端
**优先级**：P1
**预估工时**：6h
**Owner**：默认

**关联需求项**：REQ-016、SCN-011

**任务描述**：
- 在 COSMIC 配置页（规则管理）右上角新增“使用说明”按钮，点击弹出 Modal
- Modal 展示：
  - 业务语言说明（COSMIC 四类数据移动）
  - 拆分示例（细/中/粗粒度）
- 移除页面顶部的说明类 Alert/Card，技术配置默认折叠
- 不改后端 COSMIC 算法/接口/存储

**验收标准**：
- [ ] 右上角有“使用说明”按钮且默认不占据页面顶部空间
- [ ] 点击后 Modal 内容与 requirements REQ-016 一致
- [ ] 技术配置默认折叠，展开后可正常编辑与保存

**验证方式**：
- 前端自测 + 构建验证：`cd frontend && npm run build`

---

### T025：系统画像字段归一化（business_goals别名）+ 发布必填字段收敛
**分类**：后端
**优先级**：P0
**预估工时**：8h
**Owner**：默认

**关联需求项**：REQ-004、API-004；设计：design v0.11（字段归一化/发布必填字段）

**任务描述**：
- 字段归一化：
  - canonical key：`business_goals`
  - 兼容别名：`business_goal`（历史数据/旧前端）
  - 保存草稿/发布/embedding 构建时按 canonical key 归一化；读取时补齐 canonical 字段
- 发布必填字段收敛：仅校验 `in_scope`、`core_functions`（缺失返回 `PROFILE_003`）
- 更新系统画像 embedding 文本拼接：包含 7 字段（对齐 requirements REQ-004）
- 同步知识上下文构建处对 `business_goals` 的兼容读取（避免展示为空）

**验收标准**：
- [ ] Given 仅提供 `in_scope/core_functions`，When 发布画像，Then 发布成功
- [ ] Given 仅提供 `business_goal`（旧字段），When 保存草稿并发布，Then embedding/检索上下文中“业务目标”不为空

**验证方式（必须可复现）**：
- 命令：`pytest -q tests/test_system_profile_publish_rules.py`

---

### T026：UI/UX增量回归用例补齐（后端字段/发布校验/前端路由）
**分类**：测试
**优先级**：P1
**预估工时**：6h
**Owner**：默认

**关联需求项**：REQ-016/021/022

**任务描述**：
- 后端：补齐系统画像发布必填字段与 business_goal→business_goals 归一化回归用例
- 前端：补齐关键路由兼容与构建验证（/reports/ai-effect、/system-profiles redirect）

**验收标准**：
- [ ] pytest 全量/定向用例通过
- [ ] 前端 build 通过且路由兼容符合 REQ-021/022

**验证方式**：
- 后端：`.venv/bin/pytest -q`
- 前端：`cd frontend && npm run build && npm test -- --watchAll=false`

---

## 执行顺序（建议）
**CR-20260209-001（v1.4）**：
0. T029（主责+B角权限口径）+ T027（通知中心 API-017）→ 先收敛资源级权限与通知链路基础
1. T028（画像AI总结 + API-018）→ 打通“导入/入库→异步总结→通知→重试”闭环
2. T030（.doc/.xls 旧格式解析）→ 扩展 API-016/003/011 文件格式并落实 REQ-NF-007 安全约束
3. T031（系统清单双sheet导入）→ 保障后续“负责系统”判定与导入入口一致
4. T032（activeRole + 任务Tab统一）→ 统一任务管理入口与多角色用户体验
5. T033/T034（系统画像两页体验 + AI建议交互）→ 完成用户核心工作台体验优化
6. T035/T036（编辑/评估/任务详情/COSMIC UI）→ 完成剩余体验优化项
7. T037（增量回归 + 追溯补齐）→ 进入 Implementation/Testing 前置收口

**历史增量（v0.9，已完成）**：
8. T025 → T022/T024 → T023 → T026（菜单/系统画像拆页/COSMIC使用说明等）

**历史基线（v0.8，已完成）**：
9. T021（错误响应统一层）→ 作为后端接口改造前置，避免后期返工
10. T001（owner_id 口径）+ T016（system-list 热加载）→ T008（冻结）→ T009（任务查询权限/过滤）
11. T017（AI初始快照）→ T007（修改轨迹）
12. T002/T003（代码扫描）与 T004/T005（ESB/知识导入）可并行
13. T006（系统画像）依赖扫描/导入结果聚合
14. T018/T020（内部检索/复杂度/偏差/评估详情）与前端 T014 联调
15. T010（看板）依赖冻结+任务查询+画像
16. T011（报告下载）与前端 T012~T014 联调

## 风险与缓解
| 风险 | 影响 | 概率 | 缓解措施 |
|---|---|---|---|
| system owner_id 字段来源不清导致权限不可用 | 高 | 中 | T001 优先落地并提供模板样例/回退策略（缺失则拒绝写操作） |
| repo_path/解压处理存在安全风险 | 高 | 中 | 严格 allowlist + 解压上限 + 审计日志；默认关闭非 allowlist |
| 看板口径与任务数据不一致 | 中 | 中 | T008 冻结字段一次性写入；T010/ T009 用同一过滤函数；加回归测试 |
| 错误响应结构不统一导致前端/验收争议 | 中 | 中 | 在实现期优先落地统一异常处理与回归用例（覆盖 v2.0 新接口错误分支） |
| 菜单/路由调整导致历史书签失效或用户找不到入口 | 中 | 中 | T022/T023 通过 redirect 兼容旧路由并提示迁移；保留 query 保证 TAB 同步 |
| “不展示导入历史”导致用户缺少反馈 | 低 | 中 | 按 REQ-022 仅展示当前操作的最小反馈（scan job 状态/导入统计）并提供刷新按钮 |
| `.doc/.xls` 旧格式解析外部依赖缺失/行为不确定 | 高 | 中 | T030：引入必要依赖并在 Dockerfile 固化安装；按 REQ-NF-007 做隔离/超时/清理；失败返回 TASK_004/KNOW_002 并可重试 |
| 通知中心无限增长导致存储膨胀 | 中 | 中 | T027：留存期默认90天（可配置）+ 惰性清理；提供 clear-read 删除入口 |

## 开放问题
- （无；相关决策已在 design/requirements 中关闭并同步到本计划：owner_id 列、Git URL 默认禁用+allowlist、Milvus 为 NF-002 验收后端、报告下载仅 PDF）

## 覆盖矩阵（追溯用）

### 需求覆盖（REQ/REQ-NF → Task）
| 需求ID | 覆盖任务 |
|---|---|
| REQ-001 | T002, T013, T023 |
| REQ-002 | T003, T013, T023 |
| REQ-003 | T004, T013, T023 |
| REQ-004 | T006, T013, T023, T025 |
| REQ-005 | T018 |
| REQ-006 | T018 |
| REQ-007 | T017, T007 |
| REQ-008 | T020 |
| REQ-009 | T008, T010 |
| REQ-010 | T009, T014, T032, T035 |
| REQ-011 | T005, T013, T023, T030 |
| REQ-012 | T020, T014 |
| REQ-013 | T006, T014, T033, T034, T035 |
| REQ-014 | T014 |
| REQ-015 | T014 |
| REQ-016 | T015, T024, T036 |
| REQ-017 | T011, T014 |
| REQ-018 | T010, T012 |
| REQ-019 | T001, T016, T031 |
| REQ-020 | T009, T010, T012 |
| REQ-021 | T022 |
| REQ-022 | T023, T025, T026, T029, T033, T034 |
| REQ-023 | T032 |
| REQ-024 | T027, T028, T034 |
| REQ-025 | T035 |
| REQ-026 | T035 |
| REQ-027 | T030 |
| REQ-NF-001 | T002 |
| REQ-NF-002 | T018 |
| REQ-NF-003 | T002, T003 |
| REQ-NF-004 | T001, T006, T009, T028, T029 |
| REQ-NF-005 | T002 |
| REQ-NF-006 | T007 |
| REQ-NF-007 | T030 |

### 场景覆盖（SCN → Task）
| 场景ID | 覆盖任务 |
|---|---|
| SCN-001 | T002, T003, T006, T013, T023 |
| SCN-002 | T004, T006, T013, T023 |
| SCN-003 | T006, T013, T023, T025, T027, T028, T029, T034 |
| SCN-004 | T018, T030 |
| SCN-005 | T017, T007 |
| SCN-006 | T020 |
| SCN-007 | T010, T012, T009, T008 |
| SCN-008 | T009, T014, T032, T035 |
| SCN-009 | T005, T013, T023, T027, T028, T030 |
| SCN-010 | T020, T014, T035 |
| SCN-011 | T015, T024, T036 |
| SCN-012 | T011, T014 |
| SCN-013 | T016, T031 |
| SCN-014 | T022 |
| SCN-015 | T023, T027, T028, T029, T033, T034 |

## 变更记录
| 版本 | 日期 | 说明 |
|---|---|---|
| v0.1 | 2026-02-06 | 初始化任务计划（覆盖 v2.0 关键 REQ/API 与前后端任务） |
| v0.2 | 2026-02-06 | 根据 Planning 审查修复：补齐 API-005/006/008/013 与 REQ-006/008 覆盖；补齐 API-015 热加载任务；增加 AI 初始快照任务；调整依赖与执行顺序 |
| v0.3 | 2026-02-07 | 同步 Design 审查：关闭 owner_id/ Git URL 决策并落到 T001/T016/T002；明确 Milvus 为 REQ-NF-002 验收后端并补齐压测交付；报告下载仅 PDF（docx 返回 REPORT_002）；增加错误响应统一风险与 DoD |
| v0.4 | 2026-02-07 | 同步 requirements v1.11 / design v0.7：更新文档元信息与任务概览引用版本 |
| v0.5 | 2026-02-07 | 修复追溯一致性：修正任务关联 REQ 与覆盖矩阵（REQ-017~020），同步 design v0.8 |
| v0.6 | 2026-02-07 | 同步 requirements v1.12 / design v0.9：更新引用版本号（错误码口径修复不影响计划拆解） |
| v0.7 | 2026-02-07 | 根据 Planning 审查修复：补充任务状态维护说明（状态由 status.md 或 Issue Tracker 管理）；补充里程碑日期说明（Implementation 启动会议确认） | 
| v0.8 | 2026-02-07 | Implementation 收口：标记 T001/T016/T021/T018/T010/T012~T015 已完成，并与最新实现/验证结果对齐 |
| v0.9 | 2026-02-07 | 增量 UI/UX 补充：新增 T022~T026；同步覆盖矩阵到 REQ-021/022 与 SCN-014/015；补齐 REQ-016 的实现任务（Modal）与后端字段归一化/发布校验任务（T025） |
| v1.0 | 2026-02-07 | 收口更新：同步 design/requirements 引用版本到 v0.12/v1.17；标记 T022~T026 已完成；里程碑与 DoD 全量闭环并补充增量实现证据 |
| v1.1 | 2026-02-08 | 对齐模板：补齐元信息（基线/状态链接）与 R6 引用自检；同步 requirements/design 引用版本 | 
| v1.2 | 2026-02-08 | 需求确认后复核：补充 R6 引用自检实测结论（差集为空），同步 Testing/Deployment 最新验证版本引用 | 
| v1.3 | 2026-02-09 | 同步文档版本引用：design 升级为 v0.15（补齐决策记录）；不改变计划范围与任务结论 | 
| v1.4 | 2026-02-09 | 纳入 CR-20260209-001：新增 T027~T037（API-016/017/018、主责+B角权限口径、旧格式解析安全、activeRole与任务Tab、系统画像两页与AI建议闭环、双sheet导入、COSMIC平铺Tab、回归追溯补齐），并更新覆盖矩阵 | 
| v1.5 | 2026-02-09 | 完成 CR-20260209-001 收口：T035/T037 标记已完成；补齐里程碑 M4 完成日期与 TEST-029~038 追溯引用 | 
| v1.6 | 2026-02-10 | Deployment 收口同步：DoD 全量勾选完成，里程碑 M1~M3 截止日期回填，状态更新为 Done | 
