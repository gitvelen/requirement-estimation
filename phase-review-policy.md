# Phase Review Policy

阶段切换前先做走查，再通过标准 runtime 入口执行命令；不要手改 `meta.yaml` 推进 phase 或切换 `focus_work_item`。标准入口解析顺序：先尝试 `codespec <cmd>`；若当前 shell 不可调用，再尝试工作区 runtime（常见布局：`../.codespec/codespec <cmd>`）；若两者都不可用，停止并报告 runtime not found。`check-gate` 是最低硬门槛，不替代语义审查；需要严格闭环时，使用 `rfr` skill 并以本文件为准。**check-gate pass 仍不等于允许切换**，phase 推进必须同时满足本文件中的人工审查结论。注意：进入 Requirements / Design / Implementation 前，runtime 已强制检查对应 review verdict artifact（`requirements-review.yaml` / `design-review.yaml` / `implementation-review.yaml`）的存在性；但 artifact 存在不等于审查质量、组织批准或 reviewer judgment 已自动成立。

本文件按三层理解：
- `必须通过`：runtime / hooks 会执行的最低机器门槛。
- `必须确认`：reviewer 或 `rfr` 必须完成的语义审查。
- `禁止切换`：即使 gate 已通过，也不能推进的阻塞条件。

## 使用方式
- 先定位当前 `./meta.yaml` 中的 `phase`、`status`、`focus_work_item`、`execution_branch`。
- 先读当前 dossier 的 agent 入口文件（`AGENTS.md` 或 `CLAUDE.md`，根据使用的 agent 选择），再读本 phase 对应的权威文件。
- 每次 phase 切换前都要给出一个结论：`允许切换`、`有条件允许切换`、`禁止切换`。
- 只有 gate 通过且人工走查未发现阻塞项，才允许执行 `codespec start-*`、`complete-change` 或 `promote-version`。

## Proposal -> Requirements
必须读取：
- `./spec.md`

必须确认：
- `spec.md` 结构完整，至少包含 `Default Read Layer`、`Intent`、`Requirements`、`Acceptance`、`Verification`、`Input Intake Summary`、`Input Intake`、`Testing Priority Rules`、`<!-- SKELETON-END -->`。
- `input_owner`、`approval_basis`、`input_refs` 不是 placeholder。
- `input_maturity` 与 `normalization_status` 使用合法枚举值。
- Goals / Anchors / Boundary Alerts / Unresolved Decisions 已经足以支撑 Requirements 正规化。
- appendix 没有私自定义正式 `REQ/ACC/VO`。
- Proposal 阶段只允许 authority 文档与输入沉淀类改动；当前粗粒度 runtime/hook 只会硬拦最明显的实现产物（`src/**`、`Dockerfile`），其他越阶段实现仍需 reviewer 明确阻止。
- 进入 Requirements 前，当前 Proposal 审查结论必须以 `./reviews/requirements-review.yaml` 落盘，并至少包含 `phase: Proposal`、`verdict: approved`、`reviewed_by`、`reviewed_at`。

必须通过：
- `./.codespec/codespec check-gate proposal-maturity`

禁止切换：
- 输入仍是模板占位。
- 目标、边界或未决策模糊到无法拆成 requirements。
- 需要靠 appendix 才能知道正式要求编号。

## Requirements -> Design
必须读取：
- `./spec.md`

必须确认：
- `Proposal Coverage Map` 与 `Clarification Status` 存在。
- 至少有一组真实 `REQ-*`、`ACC-*`、`VO-*`。
- 每个 `REQ` 都有 acceptance 映射，每个 `ACC` 都有 verification 映射。
- 所有 intake refs 都在 Requirements coverage 或 clarification 中闭合。
- 没有 high-impact clarification 仍保持 `open`。
- acceptance 可观测、可判 PASS/FAIL，verification 描述了证据形状而不是“以后补”。
- Requirements 阶段只允许 authority 文档与输入沉淀类改动；当前粗粒度 runtime/hook 只会硬拦最明显的实现产物（`src/**`、`Dockerfile`），其他越阶段实现仍需 reviewer 明确阻止。

必须通过：
- `./.codespec/codespec check-gate requirements-approval`

禁止切换：
- proposal anchor 未闭合。
- acceptance 不可测或语义过大。
- verification 义务无法指导后续 testing。
- 高影响澄清项仍未关闭。

## Design -> Implementation
必须读取：
- `./design.md`
- `./spec.md`
- `./work-items/<WI>.yaml`
- `./contracts/*.md`（若当前 WI 使用）

必须确认：
- `design.md` 的 `Goal / Scope Link`、`Architecture Boundary`、`Work Item Execution Strategy`、`Design Slice Index`、`Work Item Derivation`、`Contract Needs`、`Verification Design`、`Failure Paths / Reopen Triggers` 完整。
- 至少存在一个真实 `WI-*` 派生项。
- 若计划并行执行，`Work Item Execution Strategy` 已明确每条执行线的 execution_branch、work_items、owned_paths、shared_paths、shared_file_owner、forbidden_paths、merge_order 和 conflict_policy（这些字段仅用于文档化和人工审查，只有 allowed_paths/forbidden_paths 由 runtime 强制）。execution_group 非 null 表示多分支并行模式，此时 gate 会检查 owned_paths 非空。
- 当前 WI 的 `goal`、`input_refs`、`requirement_refs`、`acceptance_refs`、`verification_refs`、`allowed_paths`、`derived_from` 完整且非 placeholder。
- 当前 WI 的 `branch_execution` 与 `design.md` 的并行分支计划一致；共享文件已有唯一 owner 或父 feature 分支集成策略。
- 当前 WI 与 `design.md` 中同名 derivation row 的 input / requirement / acceptance / verification refs 完全一致。
- 当前 WI 引用的 `REQ/ACC/VO` 都存在于 `spec.md`。
- 当前 WI 的 `input_refs` 能在 spec coverage 中找到落点。
- 若 `contract_refs` 非空，对应 contract 文件存在且已 `status: frozen`。
- 若需要新增 shared contract，先以 `status: draft` 建档并完成显式 review，再冻结为 `status: frozen` 后被当前 WI 引用；不要直接新增 frozen contract。
- 若存在依赖 WI，依赖项已有 pass record。

必须通过：
- `./.codespec/codespec check-gate design-structure-complete`
- `./.codespec/codespec check-gate implementation-ready`（包含 design-structure-complete + implementation-start + implementation-readiness-baseline）

禁止切换：
- work item 仍不可执行。
- design 和 work item 追溯不一致。
- contract 边界未冻结或缺失。
- required verification 不能支撑当前 WI 完成判定。

## Implementation 阶段要求（进入 Testing 前）
必须读取：
- `./meta.yaml`
- `./work-items/<focus_work_item>.yaml`（Implementation 阶段）
- `./work-items/*.yaml`（Testing 阶段，读取所有 work items）
- `./design.md`
- `./testing.md`（它是当前项目 / 当前执行线的验证证据账本，不是 Testing 阶段才首次填写；多个独立 clone 不共享 pass records）

必须确认（Implementation 阶段）：
- `focus_work_item` 非空且存在于 `active_work_items`。
- `active_work_items` 表示按 design 建议或人工维护的 branch execution set；runtime 会把它作为进入 Testing 前 verification 的聚合集合，但不提供完整的多 WI union scope/boundary enforcement。
- `execution_group` / `execution_branch` 仅用于文档化，不由 runtime 强制。
- 当前 git branch 与 `execution_branch` 一致（人工确认）；若设置了 `feature_branch`，执行分支未落后于 feature branch。
- staged 改动全部在 `allowed_paths` 内，且未命中 `forbidden_paths`（由 scope gate 强制）。
- staged 改动没有越过 `branch_execution.owned_paths`；命中 `shared_paths` 时已遵守 `shared_file_owner` / `conflict_policy`（人工审查，不由 runtime 强制；原因：需要跨分支信息，超出单分支 gate 的能力范围；审查方式：在 PR review 或 merge 前，手动对比当前改动与其他执行分支的 work-item.yaml，确认文件所有权和冲突策略）。
- 没有修改 frozen contract；新增 frozen contract 走了显式 review flow：先以 `draft` 建档、review 后再冻结；直接新增 frozen contract 会被 `contract-boundary` gate 拒绝。
- 当前 active work items（按 design 建议或人工维护的 branch execution set，也是进入 Testing 前 verification 的聚合集合）的 approved acceptance 在 `testing.md` 中都有 record 且已有 pass record（Implementation 阶段允许 test_scope=branch-local，Testing/Deployment 阶段要求 test_scope=full-integration）。
- 当前实现仍能被 `spec.md`、`design.md`、当前 WI 合法解释，没有隐性扩 scope。

必须确认（Testing 阶段）：
- `focus_work_item` 为 null（start-testing 会清空）。
- `active_work_items` 保留 Implementation 阶段的值（start-testing 不清空），用于 verification gate 聚合所有需要验证的 work items。
- `execution_group` / `execution_branch` 被清空（start-testing 会清空）。

必须确认（Completed 状态）：
- `phase = Deployment` 且 `status = completed`。
- `focus_work_item = null`。
- `active_work_items = []`；completed dossier 不再表示“活跃验证集合”，但必须仍可重跑 `verification` / `promotion-criteria` 进行验真。

### Testing 字段定义

**测试结果（result）**：
- `pass`: 测试通过，acceptance 得到验证
- `fail`: 测试失败，需要修复实现或重新开启 spec/design

**残留风险（residual_risk）**：
- `none`: 无残留风险
- `low`: 低风险，可接受的小问题
- `medium`: 中等风险，需要监控
- `high`: 高风险，需要立即处理或重新开启 spec/design

**重新开启标记（reopen_required）**：
- `true`: 需要重新开启 spec/design 进行调整
- `false`: 不需要重新开启

必须通过：
- `./.codespec/codespec check-gate metadata-consistency`
- `./.codespec/codespec check-gate scope`
- `./.codespec/codespec check-gate contract-boundary`
- `./.codespec/codespec check-gate verification`

禁止切换：
- 改动越出当前 WI 边界。
- 依赖或当前 acceptance 没有 pass record。
- frozen contract 被直接修改。
- design / spec 已经解释不了当前实现。

## Testing -> Deployment
必须读取：
- `./meta.yaml`
- `./spec.md`
- `./design.md`
- `./work-items/*.yaml`
- `./testing.md`（继续作为全量 approved acceptance 的验证证据账本）
- `REQ -> ACC -> VO` 链路完整，且每个 `REQ/ACC/VO` 都被至少一个 work item 引用。
- 每个 input ref 都在 requirements closure 中有落点。
- 每个 approved acceptance 在 `testing.md` 中都有 record 和 pass 结果。
- 每条 testing 记录都提供真实 `artifact_ref`，不是 placeholder。
- `verification_type` 与 acceptance priority 匹配：`P0` 必须 automated；`P1/P2` 只能 automated/manual/equivalent。
- `residual_risk` 与 `reopen_required` 已经被认真填写。

必须通过：
- `./.codespec/codespec check-gate trace-consistency`（检查追溯链完整性和测试记录存在性，不检查 test_scope）
- `./.codespec/codespec check-gate verification`（包含 testing-coverage，检查 full-integration pass 记录和 verification_type 要求）

禁止切换：
- 任一 approved acceptance 没有 pass record。
- `P0` 只靠 manual/equivalent。
- artifact 无法让第三方复核。
- `reopen_required: true` 仍试图推进 Deployment。

## Deployment -> Completed / Promotion
必须读取：
- `./deployment.md`
- `./testing.md`
- `./meta.yaml`

必须确认：
- `start-deployment` 只表示进入 Deployment 阶段，并在缺少 `deployment.md` 时自动 materialize 工作载体；不等于 deployment readiness 已达成。
- `complete-change` 会把 dossier 置为 completed 状态，并清空 `active_work_items`；后续重跑 gate 时应以 completed 语义验真，而不是继续要求活跃 WI 集合。
- `deployment.md` 已 materialize，并包含 `Deployment Plan`、`Pre-deployment Checklist`、`Deployment Steps`、`Verification Results`、`Acceptance Conclusion`、`Rollback Plan`、`Monitoring`、`Post-deployment Actions`。
- `Acceptance Conclusion.status = pass`，`approved_by` 非空，`approved_at` 日期合法。
- `deployment_date` 与 `target_env` 合法。
- `smoke_test: pass`。
- 文档中没有任何模板占位。
- rollback plan 与 monitoring 能覆盖本次变更的主要失败模式。
- 若要 promotion，`versions/` 目录存在且允许归档。

必须通过：
- `./.codespec/codespec check-gate trace-consistency`（start-deployment 时检查）
- `./.codespec/codespec check-gate verification`（start-deployment 时检查）
- `./.codespec/codespec check-gate deployment-readiness`（complete-change 时通过 promotion-criteria 间接检查）
- `./.codespec/codespec check-gate promotion-criteria`（complete-change 时检查）
- `./.codespec/codespec check-gate promotion`（执行 promote-version 前检查）

禁止切换：
- deployment.md 仍是模板。
- smoke / deployment verification 没有真实通过证据。
- rollback 或 monitoring 只是形式条目。
- promotion 证据不足却尝试归档稳定版本。

## 命令映射
- `start-requirements` -> `proposal-maturity` + `review-verdict-present`（要求 reviews/requirements-review.yaml 存在且 phase=Proposal, verdict=approved）
- `start-design` -> `requirements-approval` + `review-verdict-present`（要求 reviews/design-review.yaml 存在且 phase=Requirements, verdict=approved）
- `start-implementation` -> `implementation-ready` + `review-verdict-present`（从 `Design` 进入 `Implementation`，或在 `Implementation` 内切换 `focus_work_item`；要求 reviews/implementation-review.yaml 存在且 phase=Design, verdict=approved）
- `start-testing` -> `metadata-consistency` + `scope` + `contract-boundary` + `verification`
- `start-deployment` -> `trace-consistency` + `verification`，并在缺少 `deployment.md` 时自动 materialize
- `complete-change` -> `promotion-criteria`
- `promote-version` -> `promotion`
