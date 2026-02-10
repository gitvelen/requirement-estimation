# Review Report：Planning / v2.0

| 项 | 值 |
|---|---|
| 阶段 | Planning |
| 版本号 | v2.0 |
| 日期 | 2026-02-06 |
| 检查点 | 任务可执行、依赖清晰、追溯完整、验证可复现、风险与回滚 |
| 审查范围 | `docs/v2.0/plan.md`（v0.1） |
| 输入材料 | `docs/v2.0/requirements.md`（v1.6）、`docs/v2.0/design.md`（v0.2）、`.claude/templates/review_template.md` |

## 结论摘要
- 总体结论：⚠️ 有条件通过
- Blockers（P0）：1
- 高优先级（P1）：2
- 其他建议（P2+）：2

## 关键发现（按优先级）

### RVW-PLN-001（P0）需求/API 覆盖不完整：缺少内部接口与复杂度/偏差统计的实现任务
- 证据：
  - `requirements.md` 追溯矩阵包含 API-005/006/008/013（SCN-004/006/010），但 `plan.md` 任务概览中未出现对应实现/改造任务。
  - `requirements.md` 包含 REQ-006（复杂度三维度评估）与 REQ-008（专家差异统计），但 `plan.md` 未给出明确落地任务与验收/验证方式。
- 风险：
  - 进入 Implementation 后会出现“计划外需求”，导致返工/延期
  - 关键链路（AI评估依赖的内部检索/复杂度评估）缺实现落点，MVP 不完整
- 建议修改：
  - 在 `plan.md` 增加至少 2 个后端任务：
    - 覆盖 API-005（内部检索）/ API-006（复杂度评估）/ REQ-006
    - 覆盖 API-008（专家差异统计）/ API-013（评估详情契约对齐）/ REQ-008/REQ-012~015
  - 每个任务补齐：验收标准（GWT）+ 可复现验证命令（pytest/curl）
- 验证方式（可复现）：
  - `rg -n \"API-005|API-006|API-008|API-013|REQ-006|REQ-008\" docs/v2.0/plan.md`

### RVW-PLN-002（P1）系统清单（REQ-020/API-015）在计划中覆盖不充分
- 证据：
  - `plan.md` T001 聚焦 owner_id 口径，但未覆盖 REQ-020 的“模板下载/预览校验/确认导入/热加载缓存刷新/错误码对齐”等交付点。
- 风险：实现期可能遗漏热加载与错误码一致性，影响权限与系统识别准确性。
- 建议修改：
  - 增加独立任务（或扩充 T001）：明确 API-015 的契约对齐、热加载清理（system list cache / subsystem mapping cache / knowledge_service 缓存）与回归测试。
- 验证方式：
  - `pytest -q tests/test_system_list_import.py`

### RVW-PLN-003（P1）部分 P0 任务验证方式过于笼统，难复现
- 证据：多任务验证方式仅写 `pytest -q`，缺少关键用例/命令参数与预期输出。
- 风险：实现完成后很难快速判断是否达标；回归定位成本高。
- 建议修改：
  - 对 P0 任务（T002/T003/T004/T006/T008/T009）补齐至少 1 条“命令 + 关键断言/预期输出”，并尽量落到具体测试文件。

### RVW-PLN-004（P2）任务依赖关系可再校正
- 证据：T007（修改轨迹）依赖 T008（冻结）不一定必要；但依赖“task.ai_initial_features 快照写入/任务权限规则”。
- 建议修改：
  - 调整依赖：T007 依赖“AI初始快照字段落地/任务权限函数”（可并入 T008 或新增小任务）。

### RVW-PLN-005（P2）里程碑缺少日期与验收口径
- 建议修改：在进入 Implementation 前补齐 TBD（不影响计划结构，但利于推进与复盘）。

## 建议验证清单（命令级别）
- [ ] 覆盖性检查：`rg -n \"REQ-|API-\" docs/v2.0/plan.md`
- [ ] 关键后端回归：`pytest -q`

## 开放问题
- [ ] system owner_id 模板字段名/样例文件（建议在计划中明确 owner、截止与验收）

## 处理记录（建议由开发/人工填写）
| RVW-ID | 严重度 | 处理决策（Fix/Defer/Accept） | Owner | 说明 | 链接/证据 |
|---|---|---|---|---|---|
| RVW-PLN-001 | P0 | Fix | AI | 补齐 API-005/006/008/013 与 REQ-006/008 的任务、验收与验证 | `docs/v2.0/plan.md` |
| RVW-PLN-002 | P1 | Fix | AI | 补齐 REQ-020/API-015 交付点与测试 | `docs/v2.0/plan.md` |
| RVW-PLN-003 | P1 | Fix | AI | P0 任务补齐命令级验证与预期 | `docs/v2.0/plan.md` |
| RVW-PLN-004 | P2 | Fix | AI | 调整依赖关系 | `docs/v2.0/plan.md` |
| RVW-PLN-005 | P2 | Defer | AI | 里程碑日期后续与用户确认 | `docs/v2.0/plan.md` |

---

## 追加记录：v0.2 修复后复查（2026-02-06）

| 项 | 值 |
|---|---|
| 复查输入 | `docs/v2.0/plan.md`（v0.2） |
| 复查结论 | ✅ 通过（里程碑日期 TBD 已记录为 Defer） |
| 复查说明 | 已补齐 API-005/006/008/013 与 REQ-006/008 覆盖；补齐 API-015 热加载任务；增加 AI 初始快照任务；细化 P0 验证命令与依赖关系。 |

---

## 追加记录：v0.3 同步修复后复查（2026-02-07）

| 项 | 值 |
|---|---|
| 复查输入 | `docs/v2.0/plan.md`（v0.3） |
| 复查结论 | ✅ 通过 |
| 复查说明 | 同步 Design 审查：关闭 owner_id/Git URL 开放问题并落到 T001/T016/T002；新增 T021“统一错误响应结构”；补齐 Milvus 为 REQ-NF-002 验收后端与压测交付；报告下载仅 PDF（docx 预留返回 REPORT_002）。 |

---

## 追加记录：v0.5 追溯一致性修复后复查（2026-02-07）

| 项 | 值 |
|---|---|
| 复查输入 | `docs/v2.0/plan.md`（v0.5）对照 `docs/v2.0/requirements.md`（v1.11）、`docs/v2.0/design.md`（v0.8） |
| 复查结论 | ✅ 通过 |
| 复查说明 | 已修复 Planning 文档中的 REQ 关联/覆盖矩阵不一致问题（REQ-017~020），并同步引用 design v0.8；可作为 Implementation 执行入口。 |

**抽样核对点（证据）**：
- `plan.md` 不再出现 `REQ-021`：`rg -n \"REQ-021\" docs/v2.0/plan.md`
- REQ-017（报告下载）覆盖正确：`rg -n \"REQ-017\\b\" docs/v2.0/plan.md`
- REQ-020（下钻）覆盖正确：`rg -n \"REQ-020\\b\" docs/v2.0/plan.md`

---

## 追加记录：v0.6 引用版本同步复查（2026-02-07）

| 项 | 值 |
|---|---|
| 复查输入 | `docs/v2.0/plan.md`（v0.6）对照 `docs/v2.0/requirements.md`（v1.12）、`docs/v2.0/design.md`（v0.9） |
| 复查结论 | ✅ 通过 |
| 复查说明 | v0.6 仅同步 requirements/design 引用版本号，不影响任务拆解与追溯结论；Implementation 可按 plan v0.6 执行。 |

---

## 追加记录：Planning v0.9 审查（2026-02-07）

| 项 | 值 |
|---|---|
| 阶段 | Planning |
| 版本号 | v2.0 |
| 日期 | 2026-02-07 |
| 检查点 | 增量范围收口（仅3项UI/UX）、任务可执行性、依赖清晰、追溯完整性（REQ/SCN/API/TEST）、验证方式可复现、风险与回滚 |
| 审查范围 | `docs/v2.0/plan.md`（v0.9）增量内容：T022~T026、执行顺序、覆盖矩阵与风险补充 |
| 输入材料 | `docs/v2.0/requirements.md`（v1.14）、`docs/v2.0/design.md`（v0.11）、`.claude/templates/review_template.md`、`.claude/phases/04-planning.md` |

## 结论摘要
- **总体结论**：⚠️ 有条件通过（补齐 2 处“计划一致性/可复现验证”细节后可视为 Planning 收口）
- Blockers（P0）：0
- 高优先级（P1）：0
- 其他建议（P2+）：2

## 关键发现（按优先级）

### RVW-PLN-201（P2）里程碑口径仍偏“v2.0初版”，与“本次仅3项UI/UX增量修订”的范围说明不完全一致
- **证据**：`plan.md` 里程碑仍描述 “API-001~015关键接口可用 + 前端看板/任务管理核心流程”，超出本次增量范围。
- **风险**：读者可能误以为本次仍要交付全量 v2.0 初版能力，导致范围误读与验收跑偏。
- **建议修改**：
  - 将里程碑改为增量视角（例如：M1=后端T025+前端T022/T024可联调；M2=T023完成并通过 build；M3=T026回归通过并更新 test_report）。
  - 或明确标注：里程碑表为“历史基线”，本次仅执行 T022~T026。
- **验证方式（可复现）**：
  - `rg -n "## 里程碑|API-001~015|T022|T026" docs/v2.0/plan.md`

### RVW-PLN-202（P2）T025（发布必填字段/字段归一化）的验证命令仍偏笼统，建议收敛到“定向用例”以便回归定位
- **证据**：T025 当前验证方式仅写 `pytest -q`（未指定用例文件/关键断言）。
- **风险**：后续回归失败时难以快速定位；同时也不利于审查者确认“必填字段收敛 + business_goal兼容”是否被测试覆盖。
- **建议修改**：
  - 在 T025/T026 中补齐至少 1 条定向命令（例如新增 `tests/test_system_profile_publish_rules.py` 后写明 `pytest -q tests/test_system_profile_publish_rules.py`）。
- **验证方式（可复现）**：
  - `rg -n "T025|验证方式" docs/v2.0/plan.md`

## 建议验证清单（命令级别）
- [ ] 覆盖矩阵包含 REQ-021/022、SCN-014/015：`rg -n \"REQ-021|REQ-022|SCN-014|SCN-015\" docs/v2.0/plan.md`
- [ ] 仅增量任务执行顺序明确：`rg -n \"增量 UI/UX 变更（v0\\.9）\" docs/v2.0/plan.md`
- [ ]（修复后）T025 有定向验证命令：`rg -n \"T025.*pytest|tests/test_\" docs/v2.0/plan.md`

## 开放问题
- 无（需求/设计的关键歧义已在 v1.14 / v0.11 中关闭）

## 处理记录（新增）
| RVW-ID | 严重度 | 处理决策（Fix/Defer/Accept） | Owner | 说明 | 链接/证据 |
|---|---|---|---|---|---|
| RVW-PLN-201 | P2 | Fix | AI | 调整里程碑口径为“增量视角”，避免与范围说明冲突 | `docs/v2.0/plan.md` |
| RVW-PLN-202 | P2 | Fix | AI | 为 T025/T026 补齐定向用例与命令级验证 | `docs/v2.0/plan.md` + tests |

---

## 追加记录：Planning v0.9 修复后复查（2026-02-07）

| 项 | 值 |
|---|---|
| 复查输入 | `docs/v2.0/plan.md`（v0.9） |
| 复查结论 | ✅ 通过 |
| 复查说明 | RVW-PLN-201/202 已按建议修复：里程碑口径已改为“增量视角”；T025 已补齐定向验证命令（对应后续新增测试文件）。 |

**抽样核对点（证据）**：
- 里程碑口径：`rg -n "## 里程碑|T025|T022|T026" docs/v2.0/plan.md`
- T025 验证命令：`rg -n "### T025|tests/test_system_profile_publish_rules\\.py" docs/v2.0/plan.md`

---

## 追加记录：Planning v0.7 审查（2026-02-07）

| 项 | 值 |
|---|---|
| 阶段 | Planning |
| 版本号 | v2.0 |
| 日期 | 2026-02-07 |
| 检查点 | 任务可执行性、依赖清晰、DoD 明确、验证方式可复现、追溯完整性、风险预案 |
| 审查范围 | `docs/v2.0/plan.md`（v0.7） |
| 输入材料 | `docs/v2.0/requirements.md`（v1.12）、`docs/v2.0/design.md`（v0.9）、`.claude/templates/review_template.md`、`.claude/phases/04-planning.md` |

## 结论摘要
- **总体结论**：✅ 通过（可进入 Implementation）
- **Blockers（P0）**：0
- **高优先级（P1）**：0
- **其他建议（P2+）**：0（已全部修复）

## 关键发现（按优先级）

### RVW-PLAN-101（P2）~~建议补充~~ ✅ 已修复 - 任务状态字段"待办/进行中/已完成"与实际开发流程的联动说明
- **原证据**：
  - 任务概览表格中所有任务状态标记为 `待办`（见 `plan.md` L35-L54）
  - 但文档状态为 `Done`（见 `plan.md` L6）
- **原风险**：
  - 开发开始时可能不清楚如何维护任务状态
- **修复措施**（v0.7）：
  - 已在 `plan.md` 增加任务状态维护说明：明确任务状态由 `status.md` 或 Issue Tracker 管理，plan.md 中的状态仅为计划基准快照
  - 已在 DoD 中补充"实现完成后更新对应任务状态为已完成"
- **验证方式**：
  - `rg -n "任务状态.*维护|status.md|Issue Tracker" docs/v2.0/plan.md`

### RVW-PLAN-102（P2）~~建议补充~~ ✅ 已修复 - 里程碑截止日期 TBD 建议在 Implementation 启动前确定
- **原证据**：
  - 所有里程碑截止日期为 `TBD`（见 `plan.md` L13-L17）
- **原风险**：
  - 若实施期间未确定里程碑日期，进度跟踪将缺乏依据
- **修复措施**（v0.7）：
  - 已在 `plan.md` 中补充里程碑日期说明：Implementation 启动会议时确定 M1/M2/M3 的具体日期
  - 已在 `status.md` 中补充说明
- **验证方式**：
  - `rg -n "里程碑.*日期|Implementation.*启动|TBD" docs/v2.0/plan.md`

---

## 覆盖性核对

### 需求覆盖（REQ/REQ-NF → Task）
- ✅ **26个需求全覆盖**：REQ-001 ~ REQ-020，REQ-NF-001 ~ REQ-NF-006
- **验证**：`rg "^\\| REQ-" docs/v2.0/plan.md` 返回26行，与 requirements.md 需求清单一致

### 场景覆盖（SCN → Task）
- ✅ **13个场景全覆盖**：SCN-001 ~ SCN-013
- **验证**：`rg "^\\| SCN-0[0-9]{2}" docs/v2.0/plan.md` 返回13行，与 requirements.md 场景列表一致

### API 覆盖（API → Task）
- ✅ **15个接口全覆盖**：API-001 ~ API-015
- **验证**：任务详情中明确关联 API-001~015

---

## 任务依赖关系核对

### 依赖关系一致性
- ✅ 任务概览表格中的依赖与任务详情中的描述一致
- ✅ 执行顺序建议与依赖关系相符

### 关键依赖链（影响交付路径）
1. **T001（owner_id）** → T002/T004/T005/T006/T008（多个P0任务依赖）
   - 风险：T001 延误会阻塞多个后端接口任务
   - 缓解：已标注为 P0，优先级最高

2. **T002（代码扫描）** → T003（入库）→ T006（系统画像）
   - 风险：链式依赖，任一环节延误影响下游
   - 缓解：执行顺序建议中明确路径

---

## 追加记录：Planning v1.4（CR-20260209-001）自审（2026-02-09）

| 项 | 值 |
|---|---|
| 阶段 | Planning |
| 版本号 | v2.0 |
| 日期 | 2026-02-09 |
| 审查范围 | `docs/v2.0/plan.md`（v1.4，新增 T027~T037） |
| 输入材料 | `docs/v2.0/requirements.md`（v1.21）、`docs/v2.0/design.md`（v0.16）、`docs/v2.0/status.md` |
| 审查口径 | full（权限/安全、兼容性、旧格式解析风险；对齐 status.md） |

### 结论摘要
- **总体结论**：✅ 通过（可进入 Implementation）
- **Blockers（P0）**：0
- **高优先级（P1）**：0
- **其他建议（P2+）**：0

### 关键核对点（证据驱动）
1. **范围与任务对齐**：
   - `plan.md` 已新增 CR 待实施任务：T027~T037（覆盖通知中心、AI总结重试、主责+B角权限、旧格式解析安全、activeRole、系统画像联动等）。
2. **追溯完整性（R6）**：
   - 已执行引用存在性自检：`plan.md` 中引用的所有 `REQ/REQ-NF` 均在 `requirements.md` 中定义（差集为空）。
3. **关键决策已固化**：
   - 已关闭 RVW-021：负责系统=主责+B角；B角可导入/编辑草稿/重试AI总结；发布与统计仍仅主责（见 requirements v1.21 / design v0.16）。
4. **风险与回滚**：
   - 旧格式解析（REQ-NF-007）已在计划中单列（T030），并明确“最小权限/隔离目录/超时/清理”的门禁与验证。
   - 通知留存与清理已纳入计划（T027，默认90天可配置，惰性清理落地）。

### 处理记录
| RVW-ID | 严重度 | 处理决策 | Owner | 说明 | 链接/证据 |
|---|---|---|---|---|---|
| RVW-PLN-CR-001 | P0 | Fix ✅ | AI | 已补齐 CR-20260209-001 对应任务（T027~T037）并更新追溯矩阵与执行顺序；R6 自检通过 | `docs/v2.0/plan.md` + R6 自检命令 |


3. **T008（冻结）** → T009（任务查询）→ T010（看板）/T020（专家差异）
   - 风险：看板与统计功能依赖冻结字段
   - 缓解：已在执行顺序中标注

### 并行机会
- ✅ T002/T003（代码扫描）与 T004/T005（ESB/知识导入）可并行
- ✅ T018/T020（内部检索/复杂度/偏差）与前端 T014 联调时可并行

---

## DoD 与验证方式核对

### Definition of Done 完整性
- ✅ 需求可追溯：覆盖矩阵完整
- ✅ 代码可运行：回归测试要求明确
- ✅ 自测通过：每个任务有验证方式
- ✅ 安全与合规：鉴权/越权/输入校验在多个任务中明确
- ✅ 错误响应统一：T021 专门处理
- ✅ 文档同步：DoD 中已包含

### 验证方式可复现性
- ✅ 所有后端任务提供 `pytest` 验证命令
- ✅ 关键任务提供回归测试子集命令（如 `pytest -q tests/test_api_regression.py -k xxx`）
- ✅ 前端任务明确"前端自测"验证方式

---

## 风险与缓解核对

### plan.md 中已识别的风险
| 风险 | 影响 | 概率 | 缓解措施 |
|---|---|---|---|
| system owner_id 字段来源不清 | 高 | 中 | T001 优先落地并提供模板样例/回退策略 |
| repo_path/解压处理安全风险 | 高 | 中 | 严格 allowlist + 解压上限 + 审计日志 |
| 看板口径与任务数据不一致 | 中 | 中 | T008 冻结字段一次性写入；T010/T009 用同一过滤函数 |
| 错误响应结构不统一 | 中 | 中 | T021 优先落地统一异常处理与回归用例 |

### 补充建议
- **性能验证风险**：T018 中 REQ-NF-002（Milvus 压测）需要在 Implementation 早期准备测试环境与数据集
- **前端联调风险**：T012~T015 依赖后端接口完成，建议在 M2 里程碑前预留联调缓冲时间

---

## 建议验证清单（命令级别）
- [x] 需求覆盖：`rg "^\\| REQ-" docs/v2.0/plan.md | wc -l` 应为 26
- [x] 场景覆盖：`rg "^\\| SCN-0[0-9]{2}" docs/v2.0/plan.md | wc -l` 应为 13
- [x] API 覆盖：`rg -o "API-[0-9]\+" docs/v2.0/plan.md | sort -u | wc -l` 应为 15
- [x] 依赖一致性：核对任务概览表格与任务详情中的依赖描述一致
- [x] 验证方式覆盖：每个任务都有明确的 pytest/前端自测/手工命令

---

## 开放问题
- 无（plan.md v0.7 已明确标注开放问题已全部关闭）

---

## 与 design/requirements 同步核对

### 关键决策同步（抽样）
- ✅ owner_id 列决策：T001/T016 明确模板新增 `owner_id/owner_username` 并支持中文别名映射
- ✅ Git URL 扫描：T002 明确默认禁用 + allowlist 校验，返回 `SCAN_001`
- ✅ Milvus 验收前置：T018 明确以 Milvus 作为 REQ-NF-002 验收后端
- ✅ 报告下载仅 PDF：T011 明确 `format=docx` 返回 `REPORT_002`

### 版本号同步
- ✅ plan.md v0.7 引用 requirements.md v1.12、design.md v0.9
- ✅ 变更记录完整（v0.1 ~ v0.7）

---

## 处理记录汇总
| RVW-ID | 严重度 | 处理决策（Fix/Defer/Accept） | Owner | 说明 | 链接/证据 |
|---|---|---|---|---|---|
| RVW-PLN-001 | P0 | Fix | AI | 补齐 API-005/006/008/013 与 REQ-006/008 的任务、验收与验证 | `docs/v2.0/plan.md` |
| RVW-PLN-002 | P1 | Fix | AI | 补齐 REQ-020/API-015 交付点与测试 | `docs/v2.0/plan.md` |
| RVW-PLN-003 | P1 | Fix | AI | P0 任务补齐命令级验证与预期 | `docs/v2.0/plan.md` |
| RVW-PLN-004 | P2 | Fix | AI | 调整依赖关系 | `docs/v2.0/plan.md` |
| RVW-PLN-005 | P2 | Defer | AI | 里程碑日期后续与用户确认 | `docs/v2.0/plan.md` |
| RVW-PLN-201 | P2 | Fix | AI | 调整里程碑口径为"增量视角" | `docs/v2.0/plan.md` |
| RVW-PLN-202 | P2 | Fix | AI | 为 T025/T026 补齐定向用例与命令级验证 | `docs/v2.0/plan.md` + tests |
| RVW-PLAN-101 | P2 | Fix | AI | plan.md v0.7 已补充任务状态维护说明 | `docs/v2.0/plan.md` |
| RVW-PLAN-102 | P2 | Fix | AI | plan.md v0.7 已补充里程碑日期说明 | `docs/v2.0/plan.md` |

---

## 最终结论

**✅ 可进入 Implementation**

plan.md v0.7 满足 Planning 阶段要求：
- ✅ 任务可追踪（T001~T021 完整）
- ✅ 粒度合适（可独立实现与验证）
- ✅ 追溯完整（REQ/SCN/API → Task 映射完整）
- ✅ 验证可复现（每个任务有命令级别验证方式）
- ✅ 风险与回滚（风险清单完整，关键任务有回滚策略）
- ✅ 开放问题已关闭（相关决策已在 design/requirements 中明确）

建议在 Implementation 启动时：
1. 确定 M1/M2/M3 里程碑日期（已说明在计划中）
2. 使用 status.md 或 Issue Tracker 跟踪任务状态（已说明在计划中）
3. 准备 Milvus 压测环境（T018 前置）

---

*审查报告版本: v2.0 | 日期: 2026-02-07 | 审查人: AI | 状态: 所有问题已修复，通过审查*
