# AI 项目开发流程优化方案 V2（可执行版）

> 基线输入：`enr_claude.md`（2026-02-16 走查报告）
> 修订：2026-02-16 走查后整合实际代码状态
> 目标：在不牺牲交付质量的前提下，显著降低流程与上下文成本，使流程可持续、可扩展、可审计。
> 适用范围：`.aicoding/` 框架（Claude Code + Codex 协作场景）

---

## 0. 执行摘要（先看这部分）

当前流程的核心矛盾是：
1. 过程门禁偏重（读过文件、模板字段、摘要块格式），结果门禁偏弱（测试/编译/类型/运行证据）。
2. 规则定义分散且重复，导致文档漂移、维护成本高、AI 固定 context 成本高。
3. Minor 场景仍偏重，缺少真正低摩擦的紧急修复路径。

V2 方案采用三条主线并行落地：
1. 质量主线：硬门禁重排到"结果正确性"。
2. 成本主线：模板标记分层 + 阶段瘦身 + 按需读取。
3. 治理主线：单一真相源 + 配置化 + CI 上收 + 最小人工抽检。

---

## 1. 改版目标与约束

### 1.1 目标（必须同时满足）

1. 质量稳定：减少“文档合规但实现错误”的假通过。
2. 开发提效：降低 Minor/Hotfix 场景的流程摩擦。
3. 上下文降载：把框架固定占用控制在可预算范围。
4. 可维护：同一规则只定义一次，文档与脚本不漂移。
5. 可兼容：Claude/Codex 都受同等级关键门禁约束（至少在 CI 层一致）。

### 1.2 非目标（本轮不做）

1. 不推翻现有 8 阶段编号。
2. 不引入重量级外部平台依赖。
3. 不新增 CI/CD 基础设施（GitHub Actions 等）——M3 中的 CI 上收方案仅作为未来路线记录，不在本轮执行范围内。
4. 不要求一次性重写全部模板与脚本。

---

## 2. V2 总体架构

### 2.1 三层规范模型

1. Layer A（硬规则，短小）：`AGENTS.md` + `ai_workflow.md`
   - `AGENTS.md`（由 `AGENTS.md.template` 生成）：AI agent 第一入口，定义核心原则、文档交互约定、路由到 `ai_workflow.md` 和 `phases/`。
   - `ai_workflow.md`：具体流程控制规则（变更分级、阶段推进、收敛判定、中断机制）。
   - 两者职责分离：`AGENTS.md` 管"做什么"（原则+约定），`ai_workflow.md` 管"怎么做"（流程+门禁）。
   - 当前问题：两文件存在重叠（自审规则、status.md 规则在两处都有描述）。M1 需整理：`AGENTS.md.template` 中的流程细节改为引用 `ai_workflow.md`，不重复展开。
   - 目标行数：`AGENTS.md` ≤60 行（当前 36 行，新增 hotfix/逃生通道引用后预计增长），`ai_workflow.md` ≤250 行（当前 219 行，达标）。

2. Layer B（阶段差异卡）：`phases/*.md`
   只保留阶段差异信息（入口必读、出口产出物、本阶段特有规则）。
   入口/出口大表改为引用 `common.sh` 单源定义，不在 phases 中重复。

3. Layer C（按需参考）：模板中 `<!-- SKELETON-END -->` 标记以下的部分
   详细判定口径和扩展章节放在标记之后，默认不强制读。
   不新增独立 Reference 文件，避免文件膨胀。

### 2.2 门禁分层

1. Hard Gate（必须拦截）：测试、构建、类型检查、关键风险抽检、核心状态字段合法性。
2. Soft Gate（告警提示）：读前写检查、低风险结构完整性、建议性规范。
3. Advisory（人工判断）：方案优劣、技术债接受、跨方案取舍。

**门禁与 Hook 映射表**（落地时在 `hooks.md` 同步维护）：

| 门禁项 | 级别 | 执行载体 | 行为 |
|---|---|---|---|
| status.md 枚举合法性 | Hard | `pre-commit` | exit 1 阻断 |
| 阶段出口产出物存在性 | Hard | `pre-commit` + `phase-exit-gate.sh` | exit 1 / block |
| 审查摘要 REVIEW_RESULT | Hard | `pre-commit` | exit 1 阻断 |
| 结果门禁（test/build/typecheck） | Hard | `pre-commit`（M2 新增） | exit 1 阻断 |
| hotfix diff 文件数/REQ-C 边界 | Hard | `pre-commit`（M1 新增） | exit 1 阻断 |
| 入口必读文件检查（CC-7） | Soft | `phase-entry-gate.sh` | warning（M2 降级） |
| 文档作用域控制 | Soft | `doc-scope-guard.sh` | block（CC hook） |
| minor 误标启发式 | Soft | `pre-commit` | stderr 警告 |
| 审查轮次超限 | Soft | `pre-commit` | 要求 wait_confirm |

---

## 3. 流程模型优化（Hotfix/Minor/Major 三轨）

### 3.1 变更等级定义

**判定流程（三级决策链）**：
1. 用户声明：用户可直接指定 `_change_level: hotfix|minor|major`。
2. AI 建议：AI 根据变更范围建议等级，但须用户确认后才写入 `status.md`。
3. 机器校验：pre-commit 在提交时校验等级边界，违反则阻断并提示升级。

**升级规则（只升不降，除非用户明确确认）**：
- hotfix 超出硬边界 → 必须升级为 minor 或 major
- minor 中发现复杂度超预期（跨模块、REQ-C 涉及）→ 暂停，建议升级为 major
- 降级（如 major→minor）需用户明确确认，AI 不得自行降级

**机器可读切换**：`status.md` 必须声明 `_change_level`（缺失按 major 处理并告警）。

1. `hotfix`（新增，最快路径）
   适用：线上紧急修复、单点低范围改动。
   硬边界（超出任一则不得使用 hotfix，pre-commit 强制校验）：
   - diff 文件数 ≤ `hotfix_max_diff_files`（默认 3，可配置）
   - 不涉及 API 契约变更、数据库 schema 变更、权限/安全变更
   - 不涉及 REQ-C（禁止项）
   最小要求：代码改动 + 关键测试通过证据 + 回滚说明。
   默认不强制完整 `review_*.md`，不强制 GWT 追溯。
   不走 8 阶段流程，直接：改代码 → 测试 → 提交（commit message 使用 `fix:` 或 `fix(<scope>):` 前缀，符合现有 commit-msg hook 格式校验）。
   与 `status.md` 的关系：hotfix 可以不创建版本目录和 `status.md`。
   pre-commit 对不涉及 `docs/vX.Y/` 的提交已默认跳过阶段校验（`STATUS_FILES` 为空时，status 校验段自然跳过）。
   若项目已有版本目录且需在其中记录 hotfix，则 `_phase` 保持不变（不推进），`_change_level: hotfix` 触发门禁短路（跳过阶段出口、审查摘要等校验，仅保留 diff 文件数和 REQ-C 边界检查）。
   若 hotfix 涉及 `docs/vX.Y/` 目录变更，则必须有 `status.md` 且 `_change_level: hotfix`，否则会被现有门禁拦截。

   **落地前置**：`pre-commit` 第 463 行硬编码 `major minor` 枚举校验，必须先改为引用 `AICODING_ENUM_CHANGE_LEVEL`（含 hotfix），否则 hotfix 提交会被拦截。注：`common.sh` 枚举已就绪，实际只需替换 pre-commit 的硬编码。

2. `minor`（轻流程）
   适用：小功能增强、局部 bugfix、UI 微调。
   要求：可追溯 REQ/GWT 子集、必要测试证据、精简审查。

3. `major`（全流程）
   适用：跨模块、架构变化、安全/权限/API/数据迁移。
   要求：完整阶段治理 + 强化抽检。

### 3.2 阶段执行模式

1. 保留 8 阶段编号（兼容现有脚本）。
2. 执行层采用 5 个工作簇：
- 需求确认（00-02）
- 方案与计划（03-04）
- 实施（05）
- 验证（06）
- 交付（07）
3. 新增“流式模式”：允许单会话跨阶段推进，但在以下节点强制暂停：
- 需求确认完成
- 高风险触发
- 部署前确认

---

## 4. 结果门禁重排（P0 核心）

### 4.1 新的硬门禁优先级（从高到低）

前置条件：`aicoding.config.yaml` 必须先新增以下配置，否则结果门禁无法执行：
```yaml
# 扁平 key（当前 aicoding_config_value 仅支持扁平解析，不支持嵌套 YAML）
result_gate_test_command: ""        # 如 "npm test", "pytest", "go test ./..."
result_gate_build_command: ""       # 如 "npm run build", "cargo build"
result_gate_typecheck_command: ""   # 如 "tsc --noEmit", "mypy ."
```
空值表示该项目不适用该检查，门禁自动跳过（跳过时输出 `⚠️ [gate:result-gate] <command> 未配置，已跳过` 到 stderr 并记录到 gate-warnings.log，避免 silent skip）。

1. 测试执行必须通过（仅在 `_phase` 推进 commit 中执行：Implementation→Testing 首次执行 + Testing→Deployment 再次执行）。
2. 构建/类型检查必须通过（按语言栈配置，执行时机同上；普通代码提交不执行）。
3. 高风险改动必须完成最小抽检（自动 + 人工）。
4. 状态文件关键字段合法（`_phase`、`_change_status`、`_run_status` 等）。

### 4.2 降级为软门禁的项

1. 纯“是否 Read 过文件”检查（CC-7 从 block 改 warning）。
2. 过细审查摘要字段（保留最小字段集）。
3. 低风险 Minor 的重结构校验。

### 4.3 审查字段分层（替代当前大摘要）

始终必填：
- `GWT_TOTAL`
- `GWT_FAIL`
- `GWT_WARN`
- `REVIEW_RESULT`

增量审查时条件必填（仅当 `CARRIED_FROM_COMMIT` 非空时要求）：
- `GWT_CARRIED`
- `CARRIED_FROM_COMMIT`
- `GWT_CHANGE_CLASS`

说明：增量审查字段支撑了"需求不衰减"机制，不可移除。
但对于首次审查（非增量），这些字段不做强制要求。

---

## 5. 文档与 context 优化（P1 核心）

### 5.1 模板标记分层（SKELETON-END 标记法）

不新增独立 Skeleton/Reference 文件。改为在现有模板中插入分隔标记：

```markdown
<!-- SKELETON-END: 以下为参考材料，非必填 -->
```

标记以上为必填骨架（目标 30-50 行），标记以下为详细参考。

需要添加标记的模板：
- `templates/review_template.md`
- `templates/master_system_function_spec_template.md`（即 requirements 模板）
- `templates/test_report_template.md`

规则：
1. `inject-phase-context.sh` 注入入口提示时，提示 AI "优先读到 SKELETON-END 标记处"。
2. 标记以下内容仅在触发条件满足时读取（权限、性能、合规、复杂 CR）。
3. 骨架部分必填字段控制在 30-50 行。

**技术限制说明**：当前 Read 工具为全文读取，`read-tracker.sh` 仅记录文件路径而非读取范围，因此 SKELETON-END 是阅读指导性软约束，不能作为硬性 context 降载机制。实际 context 降载依赖 §5.2 阶段文档瘦身和 §5.4 外置策略。

### 5.2 阶段文档瘦身

`phases/*.md` 删除重复内容：
1. 入口协议大表（改为引用配置单源）。
2. 出口门禁大表（改为引用 gate 定义）。
3. 重复"完成后自动推进"描述。
4. 非当前场景的 CR 规则长段（抽到 `phases/cr-rules.md`）。

**瘦身后最小结构示例**（以 `phases/05-implementation.md` 为例）：
```markdown
# 05 Implementation 阶段

> 入口/出口规则详见 common.sh 的 PHASE_ENTRY_REQUIRED / PHASE_EXIT_REQUIRED

## 本阶段唯一输入
- plan.md（任务清单 + 验证命令）
- design.md（架构约束）

## 本阶段唯一输出
- 代码实现 + implementation_checklist.md
- review_implementation.md（major）或 review_minor.md（minor）

## 本阶段特有规则
- 按 plan.md 任务顺序逐项实施，每项完成后执行验证命令
- 代码变更必须在 plan.md 声明的范围内
- minor: 跳过 spotcheck，使用精简审查
```

### 5.3 requirements 按需读取

1. Design/Planning：全文读取。
2. Implementation：按 `plan.md` 任务关联 REQ 子集读取。
3. Testing：全文读取。

在 `plan.md` 任务项新增：
- `related_reqs: [REQ-xxx, REQ-yyy]`

### 5.4 context 降载策略

不引入 token 预算机制（无法在 shell hooks 层面精确计量 token）。
改为以下可执行策略：

1. 模板标记分层（§5.1）自然减少必读量。
2. 阶段文档瘦身（§5.2）减少 phases 总行数。
3. `inject-phase-context.sh` 注入提示时，只列出骨架部分路径。
4. 大段日志/证据外置到独立文件，主文档仅保留关键摘要行。

---

## 6. 工程实现整改（P0/P1）

### 6.1 单一真相源整改

1. 阶段入口必读列表：收敛到 `common.sh` 关联数组（M1 落地载体）
   `phase-entry-gate.sh` 与 `inject-phase-context.sh` 共用该定义。
   说明：选择 `common.sh` 而非 `aicoding.config.yaml` 的原因——入口/出口规则是框架内部逻辑，不属于项目级可配置项。§7.2 的 `phase_rules` 配置组仅用于未来项目级覆盖（如跳过某阶段），不替代 `common.sh` 中的默认定义。

   **必须统一的 4 个脚本**（当前各自硬编码入口/出口列表，互相不引用）：
   - `scripts/cc-hooks/phase-entry-gate.sh`（CC-7 入口必读，第 47-93 行 case 块）
   - `scripts/cc-hooks/inject-phase-context.sh`（会话注入入口提示，第 32-49 行 case 块）
   - `scripts/cc-hooks/phase-exit-gate.sh`（CC-8 出口产出物，第 69-94 行 case 块）
   - `scripts/git-hooks/pre-commit`（Git Hook 7 出口门禁，第 522-560 行 case 块）

   落地方式：在 `common.sh` 新增 `aicoding_phase_entry_required()` 和 `aicoding_phase_exit_required()` 函数，4 个脚本统一调用。

2. 阶段出口产出物要求：收敛到 `common.sh` 关联数组（M1 落地载体）
   `phase-exit-gate.sh` 与 `git-hooks/pre-commit` 共用，不再双份硬编码。
   当前 `ai_workflow.md` 中的出口表与 `phase-exit-gate.sh` 中的硬编码需统一。

3. `hooks.md` 改为设计索引文档，不再内嵌实现代码（当前 1,949 行，过重）。

### 6.2 `status.md` 双轨问题整改

推荐路径（首选）：
1. 新增 `docs/<ver>/status.yaml` 作为机器真相源。
2. `status.md` 仅保留人类阅读视图与决策记录。
3. 所有脚本统一解析 `status.yaml`。

兼容路径（过渡）：
1. 先保留 `status.md` YAML front matter 为机器源。
2. pre-commit 增加 YAML 与表格一致性校验。

### 6.3 Shell 健壮性修复清单

> 以下 5 项中，#2/#3 已在 Codex 走查修复轮中完成。#1/#5 部分修复（新增函数但原函数未改），#4 待修。

1. `common.sh::aicoding_detect_version_dir`（⚠️ 部分修复）
   新增了 `aicoding_detect_version_dir_from_files`（无 find fallback，返回所有去重版本目录）。
   但原函数 `aicoding_detect_version_dir` 仍保留 `find -exec ls -t` fallback（common.sh 第 48 行），被 CC hooks 调用。
   待办：将原函数的 find fallback 移除或改为按版本号排序，与新函数行为对齐。

2. ~~`doc-scope-guard.sh`~~（✅ 已修复）
   ~~`for pattern in $(...)` 改数组遍历，避免 word splitting。~~
   实际修复：改为 basename 锚定匹配。

3. ~~`common.sh::aicoding_block`~~（✅ 已修复）
   ~~改用 `jq -n --arg reason "$reason"` 生成 JSON，避免转义缺陷。~~
   实际修复：保留 sed 转义但增强了换行处理。注：jq 方案更优，可后续升级。

4. `common.sh::aicoding_yaml_value`（⏳ 待修）
   key 匹配改安全匹配。当前 awk 中 `$0 ~ "^" k ":"` 会将 key 中的特殊字符当正则处理。
   修复方案：改用 `index($0, k ":")` 精确匹配。

5. `read-tracker.sh` / `phase-entry-gate.sh`（⚠️ 部分修复）
   staged 函数移除工作目录 fallback：✅ 已完成。entry gate 缓存改进：✅ 已完成。
   但 `read-tracker.sh` 仍使用 `CLAUDE_SESSION_ID:-$$` 作为 session key（第 12 行），`$$` 在多进程场景下不稳定。
   待办：改用更稳定的 session 标识（如 `CLAUDE_SESSION_ID:-$(date +%Y%m%d-%H%M%S)-$$`），或在无 session ID 时写入固定日志路径。

---

## 7. 配置化扩展（P1，分批落地）

在 `aicoding.config.yaml` 分批新增以下配置组。

**约束**：当前 `aicoding_config_value` 仅支持扁平 `key: value` 解析（awk 按行匹配），不支持嵌套 YAML。所有新增配置必须使用扁平 key。

### 7.1 第一批（随 hotfix 和结果门禁一起落地）

1. `result_gate_*`（§4.1 前置条件）
   - `result_gate_test_command: ""`
   - `result_gate_build_command: ""`
   - `result_gate_typecheck_command: ""`

2. hotfix 策略（扁平 key，不使用嵌套）
   - `enable_hotfix: true`
   - `hotfix_max_diff_files: 3`

### 7.2 第二批（随单源收敛落地）

3. 门禁策略（扁平 key）
   - `entry_gate_mode: warn`（可选值：warn / block）

4. 阶段规则覆盖（项目级，可选，扁平 key）
   - 例：`phase_skip_proposal: true`（跳过 Proposal 阶段）
   - 未配置时使用 `common.sh` 关联数组中的框架默认值

### 7.3 第三批（⚠️ 依赖 CI 基础设施，标注为未来路线）

5. 审查策略（已有 key，无需改动）
   - `spotcheck_ratio_percent`（已有）
   - `spotcheck_min`（已有）
   - `spotcheck_max`（已有）

6. CI 策略（需 GitHub Actions，本轮不落地）
   - `ci_required_checks: test,build,typecheck`
   - `ci_enforce_on: minor,major,hotfix`

---

## 8. 兼容性与治理上收（Codex/Claude 对齐）— ⚠️ 未来路线

> 本章内容依赖 CI 基础设施（GitHub Actions），不在本轮执行范围内（见 §1.2 非目标第 3 条）。
> 当前版本仅强化 Git hooks 作为 Codex 最小约束层。以下方案作为条件允许时的执行路线记录。

### 8.1 CI 上收关键门禁

将以下规则迁移/镜像到 CI（GitHub Actions）：
1. 测试、构建、类型检查。
2. `status` 关键字段合法性。
3. 高风险变更是否有 CR/抽检声明。

目标：无论本地工具差异（Claude hooks 可用、Codex 无 CC hooks），关键质量门槛一致。

### 8.2 本地 hooks 职责重定义

1. CC hooks：即时反馈和流程引导（优先提醒）。
2. Git hooks：本地提交前拦截（轻量但硬）。
3. CI：最终权威拦截（统一且不可绕过）。

---

## 9. 文档可用性与逃生通道（P1）

### 9.1 统一命名与对照

1. 统一英文文件名，或在 `STRUCTURE.md` 增加中英文映射表。
2. 在 `manu.md` 增加“5 分钟定位入口”：按场景查文档。

### 9.2 新增故障排除与应急章节

`manu.md` 必须新增：
1. 门禁误报排查步骤。
2. 临时禁用特定 CC hook 方法。
3. 紧急修复 `hotfix` 标准流程。
4. 状态恢复指引（`_phase` / `_run_status` / `_change_status`）。
5. 跳阶段风险声明与最小补偿动作。

### 9.3 逃生通道使用规范

逃生通道（临时禁用 hook、跳阶段、手动修改 status.md）必须满足：

1. **谁可以做**：仅项目 owner 或明确授权的维护者。AI agent 不得自行触发逃生通道。
2. **何时记录**：每次使用逃生通道建议在 commit message 中标注 `[escape:<原因>]`；审计以 post-commit 的 W24（pre-commit 证据缺失）+ `gate-warnings.log` 留痕为准。
3. **误报处理标准流程**：
   - 确认误报（复现 + 定位 hook 规则）→ 临时 `--no-verify` 提交 → 提 issue 修复 hook → 下次提交恢复正常流程。
   - 禁止长期使用 `--no-verify` 绕过门禁。
4. **审计**：`run-all.sh` 扩展时增加"逃生通道使用频率"统计，频率过高说明门禁规则需要调整。

---

## 10. 测试体系补强（P2）

### 10.1 新增测试类型

1. 集成测试：跨 hook 交互（CC-7/CC-8/Git pre-commit）。
2. 并发测试：多会话 read-tracker 并发写入/隔离。
3. 边界测试：front matter 特殊字符、空值、超长值。
4. 回归测试：`common.sh` 共享函数改动的全链路回归。
5. E2E 流程测试：Proposal→Deployment 全流程演练。

### 10.2 最小 E2E 试点项目

1. 选一个小型真实项目（建议 CLI 工具）跑完整 Major。
2. 记录摩擦点（误报、漏报、超重模板、重复动作）。
3. 用试点数据回修配置和门禁阈值。

---

## 11. 分期落地计划（可直接执行）

### 11.1 里程碑

1. M1（P0）：Hotfix 轨道 + 单源收敛 + 剩余脚本修复 + 逃生通道
   - 新增 `hotfix` 流程并接入 `ai_workflow.md` + pre-commit 判定
   - 抽取阶段入口/出口规则为单源配置（`common.sh` 或 config）
   - 修复 `aicoding_yaml_value` key 匹配问题（§6.3 #4）
   - `manu.md` 增加逃生通道与故障排除

2. M2（P1）：结果门禁 + 模板分层 + 阶段瘦身 + CC-7 降级
   - 新增 `result_gate` 配置（test/build/typecheck 命令）
   - 结果门禁上硬（Testing→Deployment 前置校验）
   - 模板插入 `<!-- SKELETON-END -->` 标记 + CC-7 从 block 改 warning
   - `phases/*.md` 删除重复内容（入口/出口大表改引用）
   - `hooks.md` 拆分（设计与实现解耦）

3. M3（P2）：CI 上收 + E2E 测试 + 增量审查字段条件化 — ⚠️ 条件允许时执行
   - CI 上收关键门禁（Codex/Claude 对齐）— 依赖 GitHub Actions 基础设施
   - 补齐集成/E2E 测试并完成一次真实项目演练（本地 `run-all.sh` 扩展可先行）
   - 审查字段条件化（增量审查字段仅在 CARRIED 场景要求）

### 11.2 任务清单（按执行顺序）

**任务间依赖关系**：
- OPT-001（hotfix）依赖 pre-commit 枚举修改（第 463 行 `major minor` → 引用 `AICODING_ENUM_CHANGE_LEVEL`），必须先改枚举再测 hotfix 流程。
- OPT-002（单源收敛）是 OPT-005/006/007 的前置——入口/出口定义统一后，结果门禁和模板分层才能引用单源。
- OPT-005（结果门禁）依赖 `aicoding.config.yaml` 新增扁平 key，需同步补测试。
- M3 任务依赖 CI 基础设施就绪，与 M1/M2 无硬依赖。

**M1 任务：**

1. OPT-001：新增 `hotfix` 流程并接入 `ai_workflow.md` + pre-commit 判定。
   输出：可跑通 hotfix 最小提交流程。
   配置：`enable_hotfix`, `hotfix_max_diff_files`（扁平 key）。
   前置：`pre-commit` 第 463 行硬编码 `major minor`，需同步改为引用 `AICODING_ENUM_CHANGE_LEVEL`。
   文档草稿：`ai_workflow.md` 变更分级表新增 hotfix 行 + hotfix 极速流程（边界、门禁、提交流程）。

2. OPT-002：抽取阶段入口/出口规则为 `common.sh` 关联数组单源。
   输出：CC/Git hooks 共用定义，消除 `phase-entry-gate.sh` / `inject-phase-context.sh` / `phase-exit-gate.sh` / `pre-commit` 之间的重复。
   补充：`review_gate_common.sh` 保持内容级校验单源，与 `common.sh` 的结构级校验互补。
   补充：`inject-phase-context.sh` 消除 `find -exec ls -t` fallback，改为稳定版本目录推断。
   补充：`AGENTS.md.template` 中流程细节改为引用 `ai_workflow.md`，不重复展开。

3. OPT-003：修复 `common.sh::aicoding_yaml_value` / `aicoding_config_value` key 匹配，并处理 `read-tracker.sh` 会话 key 稳定性。
   输出：单元测试覆盖特殊字符 key。

4. OPT-004：`manu.md` 增加逃生通道与故障排除。
   输出：应急手册可执行步骤（门禁误报排查、临时禁用 hook、hotfix 流程、状态恢复）。

**M2 任务：**

5. OPT-005：新增 `result_gate_*` 配置并实现结果门禁。
   输出：`aicoding.config.yaml` 新增 test/build/typecheck 命令配置（扁平 key），pre-commit 在 `_phase` 推进 commit 中执行（Implementation→Testing / Testing→Deployment）。
   补充：增加 status.md 兼容校验（YAML front matter 与表格关键字段一致性）。

6. OPT-006：模板插入 SKELETON-END 标记 + CC-7 降级。
   输出：3 个模板完成标记分层，入口读取策略更新；`phase-entry-gate.sh` 的 CC-7 从 block 改 warning（§4.2）。

7. OPT-007：`phases/*.md` 瘦身（删除重复入口/出口大表）。
   输出：phases 总行数降低 30%+。

8. OPT-008：`hooks.md` 拆分（设计与实现解耦）。
   输出：精简版设计文档 + 脚本索引。

**M3 任务（⚠️ 条件允许时执行）：**

9. OPT-009：CI 上收关键门禁（Codex/Claude 对齐）。
   输出：Actions 工作流 + 必过检查。
   前置：GitHub Actions 基础设施就绪。

10. OPT-010：补齐集成/E2E 测试并完成一次真实项目演练。
    输出：试点报告 + 参数回调建议。
    注：本地 `run-all.sh` 扩展部分可在 M2 期间先行落地，不依赖 CI。

---

## 12. 文件级变更清单

### 12.1 M1 必改文件

1. `AGENTS.md.template` — 流程细节改为引用 `ai_workflow.md`，消除重叠
2. `ai_workflow.md` — 新增 hotfix 流程定义
3. `aicoding.config.yaml` — 新增 `enable_hotfix`、`hotfix_max_diff_files`、`result_gate_*` 配置
4. `scripts/lib/common.sh` — 修复 `aicoding_yaml_value`，新增入口/出口单源定义
5. `scripts/cc-hooks/phase-entry-gate.sh` — 改用 common.sh 单源定义
6. `scripts/cc-hooks/phase-exit-gate.sh` — 改用 common.sh 单源定义
7. `scripts/cc-hooks/inject-phase-context.sh` — 改用 common.sh 单源定义
8. `scripts/git-hooks/pre-commit` — 接入 hotfix 判定 + 改用单源定义
9. `manu.md` — 新增逃生通道与故障排除章节

### 12.2 M2 必改文件

10. `templates/review_template.md` — 插入 SKELETON-END 标记
11. `templates/master_system_function_spec_template.md` — 插入 SKELETON-END 标记
12. `templates/test_report_template.md` — 插入 SKELETON-END 标记
13. `phases/03-design.md` — 删除重复入口/出口大表
14. `phases/04-planning.md` — 同上
15. `phases/05-implementation.md` — 同上
16. `phases/06-testing.md` — 同上
17. `phases/07-deployment.md` — 同上
18. `hooks.md` — 拆分为设计索引 + 脚本引用
19. `STRUCTURE.md` — 更新文件映射
20. `scripts/cc-hooks/phase-entry-gate.sh` — CC-7 从 block 改 warning（§4.2）

### 12.3 M3 新增文件

1. `.github/workflows/quality-gates.yml` — 扩展 CI 门禁
2. `scripts/tests/e2e-major-flow.test.sh` — E2E 流程测试
3. `phases/cr-rules.md` — 从 phases 中抽出的 CR 规则集中文档

---

## 13. 验收指标（Definition of Done）

### 13.1 质量指标

1. “文档通过但测试失败”拦截率显著下降（目标：下降 80%+）。
2. 交付后 7/14 天缺陷率下降（目标：下降 30%+）。
3. 高风险变更抽检覆盖率达到配置目标（默认 10%，可调）。

### 13.2 成本指标

1. 单任务框架必读 token 降低 30%+。
2. `phases/*.md` 总行数降低 35%+。
3. 模板骨架部分（`SKELETON-END` 以上）控制在 50 行以内；实际 context 降载依赖阶段瘦身与按需读取。

### 13.3 体验指标

1. Minor/hotfix 平均交付时长下降。
2. 门禁误报次数下降。
3. `--no-verify` 等绕过行为频次下降。

---

## 14. 风险与回滚策略

### 14.1 主要风险

1. 门禁重排初期可能误伤历史项目。
2. 模板拆分可能导致旧流程短期不适配。
3. CI 上收后会暴露历史隐性质量债。

### 14.2 回滚原则

1. 所有新规则均提供 `warn` 模式开关。
2. 先灰度到 `minor`/试点仓库，再全量启用。
3. 保留旧模板 1 个迭代周期，提供兼容适配脚本。

---

## 15. ENR 全覆盖映射（17/17，不遗漏）

| ENR | 问题摘要 | 对应优化动作 | 落地载体 | 状态 |
|---|---|---|---|---|
| ENR-001 | `status.md` 双轨脆弱 | 兼容路径：保留 YAML front matter 为机器源 + 一致性校验 | `common.sh`, `pre-commit` | 待定（M3） |
| ENR-002 | 框架 context 过重 | 模板标记分层 + 阶段瘦身 | `templates/*`, `phases/*` | M2 |
| ENR-003 | 先读后写机制缺陷 | CC-7 降级 warning，重心改结果门禁 | `phase-entry-gate.sh`, `ai_workflow.md` | M2 |
| ENR-004 | Minor 仍偏重 | 新增 `hotfix`，Minor 审查条件化可跳过 | `ai_workflow.md`, `pre-commit`, `config` | M1 |
| ENR-005 | 8 阶段过线性 | 5 工作簇 + 流式模式 + 关键节点暂停 | `ai_workflow.md`, `phases/*` | M2 |
| ENR-006 | 自审形式主义 | 结构检查与质量审查分离，强化抽检 | `review_template`, `post-commit` | M2 |
| ENR-007 | Codex 兼容名义化 | 关键门禁上收 CI | `.github/workflows/*` | M3 |
| ENR-008 | Shell 健壮性边界 | 5 项函数级修复（2/5 已完成、2/5 部分修复、1/5 待修） | `common.sh` | M1 |
| ENR-009 | `hooks.md` 承载过重 | 设计文档与实现解耦 | `hooks.md`, `scripts/*` | M2 |
| ENR-010 | 配置化不足 | 分批扩展配置组（§7.1/7.2/7.3） | `aicoding.config.yaml`, hooks | M1-M3 |
| ENR-011 | CC-8 与 Git-Hook7 重复 | 出口规则单源复用 | `common.sh`, `phase-exit`, `pre-commit` | M1 |
| ENR-012 | 入口协议多处重复 | 入口规则单源复用 | `common.sh`, `phase-entry`, `inject-context` | M1 |
| ENR-013 | 中英文混用负担 | `STRUCTURE.md` 已有中英文映射表，保持维护即可 | `STRUCTURE.md` | 已有 |
| ENR-014 | 模板过重 | SKELETON-END 标记分层 | `templates/*` | M2 |
| ENR-015 | 缺少逃生通道 | 新增故障排除/应急流程 | `manu.md` | M1 |
| ENR-016 | 缺少真实 E2E 验证 | 引入试点项目完整演练 | `scripts/tests/*`, 试点报告 | M3 |
| ENR-017 | 测试覆盖不足 | 增加集成/E2E 测试 | `scripts/tests/*` | M3 |

---

## 16. 立即执行建议

1. M1 先行：OPT-001（hotfix，需先改 pre-commit 枚举）→ OPT-002（单源收敛）→ OPT-003（yaml_value 修复）→ OPT-004（逃生通道）。
   OPT-001 有硬前置（pre-commit 枚举），其余可并行。落地后即可获得 hotfix 快速路径和应急能力。

2. M2 跟进：OPT-005（结果门禁）→ OPT-006（模板标记 + CC-7 降级）→ OPT-007（phases 瘦身）→ OPT-008（hooks.md 拆分）。
   OPT-005 依赖 OPT-002 的单源收敛完成，需先完成 M1 再启动 M2。新增配置需同步补测试。

3. M3 条件执行：OPT-009（CI）→ OPT-010（E2E）。
   依赖 GitHub Actions 基础设施。OPT-010 中本地 `run-all.sh` 扩展部分可在 M2 期间先行。
   CI 上收是最终一致性保障，E2E 是验收手段。

> 该顺序可在不推翻现有框架的前提下，最短路径实现"质量更稳 + 成本更低 + 执行更顺"。

---

## 17. 落地前待修清单（V2 走查发现）

> 走查日期：2026-02-16
> 走查范围：enhance_v2.md 全文 × 现有代码交叉比对
> 状态标记：🔴 必须修复（阻塞落地）| 🟡 建议修复（不阻塞但影响质量）| 🔵 文字/格式修正

### 17.1 方案内部一致性问题

**FIX-001** 🔴 §12.1 第 3 条 config key 名与 §7.1 不一致
- 问题：§12.1 写 `change_level_policy`，但 §7.1 实际定义的扁平 key 是 `enable_hotfix` + `hotfix_max_diff_files`。`change_level_policy` 在 §7 中从未出现。
- 修复：§12.1 第 3 条改为"新增 `enable_hotfix`、`hotfix_max_diff_files`、`result_gate_*` 配置"。

**FIX-002** 🟡 OPT-003 遗漏 `aicoding_config_value` 的同类正则注入
- 问题：`common.sh:277` 的 `aicoding_config_value` 用 `line ~ "^[[:space:]]*" k "[[:space:]]*:"` 匹配 key，与 `aicoding_yaml_value` 存在完全相同的正则注入风险。OPT-003 只修后者。
- 修复：OPT-003 扩展范围，同时修复 `aicoding_config_value` 的 key 匹配（改用 `index()` 精确匹配）。

**FIX-003** 🟡 §5.1 SKELETON-END 效果与 §13.2 验收指标不匹配
- 问题：§5.1 末尾已承认"SKELETON-END 是阅读指导性软约束，不能作为硬性 context 降载机制"（Read 工具全文读取），但 §13.2 仍写"模板必读行数降低 40%"。实际 token 消耗不会因标记而减少。
- 修复：§13.2 第 3 条改为"模板骨架部分（SKELETON-END 以上）控制在 50 行以内；实际 context 降载依赖 §5.2 阶段瘦身和 §5.4 外置策略"。

**FIX-004** 🟡 §3.1 hotfix 不创建 status.md 的隐含路径未说清
- 问题：§3.1 说"hotfix 可以不创建版本目录和 status.md"，但没有解释为什么 pre-commit 不会拦截——原因是 pre-commit 第 402 行 `STATUS_FILES` 为空时整个 status.md 校验段自然跳过。
- 修复：在 §3.1 的 `hotfix` 定义中补充一句："不涉及 `docs/vX.Y/` 的 hotfix 提交，pre-commit 的 status.md 校验段（第 402-567 行）因 `STATUS_FILES` 为空而自然跳过，无需额外处理。"

### 17.2 与现有代码的对齐问题

**FIX-005** 🔵 `AICODING_ENUM_CHANGE_LEVEL` 已包含 hotfix
- 现状：`common.sh:264` 已定义 `AICODING_ENUM_CHANGE_LEVEL="major minor hotfix"`。OPT-001 的前置工作量比描述的更小。
- 修复：OPT-001 描述中补充"注：`common.sh` 枚举已就绪，仅需修改 pre-commit 第 463 行从硬编码 `major minor` 改为引用 `$AICODING_ENUM_CHANGE_LEVEL`"。

**FIX-006** 🟡 OPT-002 未提及 `review_gate_common.sh` 的定位
- 问题：`phase-exit-gate.sh:10` source 了 `review_gate_common.sh`（提供 `review_gate_validate_*` 系列内容级校验函数），但 OPT-002 只提到 4 个脚本的入口/出口列表统一，未明确 `review_gate_common.sh` 的角色。
- 修复：OPT-002 描述中补充"`review_gate_common.sh` 保持为内容级校验单源（GWT 覆盖、追溯矩阵、摘要块验真），与 `common.sh` 的结构级校验互补，两者职责不重叠"。

**FIX-007** 🟡 `inject-phase-context.sh` 的 `find` fallback 未纳入 OPT-002
- 问题：`inject-phase-context.sh:12` 调用 `aicoding_detect_version_dir ""`（空字符串），走到 `common.sh:48` 的 `find -exec ls -t` fallback。§6.3 #1 说要修复此 fallback，但 OPT-002 任务描述未覆盖。
- 修复：OPT-002 增加子项："`inject-phase-context.sh` 改用 `aicoding_detect_version_dir_from_files` 或改为从 git status 推断版本目录，消除 `find` fallback 依赖"。

### 17.3 任务清单遗漏

**FIX-008** 🔴 `read-tracker.sh` 的 `$$` 问题未进入任何 OPT 任务
- 问题：§6.3 #5 明确标注 `read-tracker.sh` 的 `CLAUDE_SESSION_ID:-$$` 在多进程场景下不稳定，但 §11.2 的 10 个 OPT 任务均未覆盖。
- 修复：归入 OPT-003（Shell 健壮性修复），或新增 OPT-003b。修复方案：改用 `CLAUDE_SESSION_ID:-$(date +%Y%m%d-%H%M%S)-$$` 或在无 session ID 时写入固定日志路径。

**FIX-009** 🔴 `AGENTS.md.template` 重叠整理未进入任何 OPT 任务
- 问题：§2.1 第 1 条说"M1 需整理：`AGENTS.md.template` 中的流程细节改为引用 `ai_workflow.md`"，§12.1 第 1 条也列了此文件，但 OPT-001~004 均未包含。
- 修复：归入 OPT-002（单源收敛）的子项，或新增 OPT-002b。具体工作：`AGENTS.md.template` 中的自审规则、status.md 规则等流程细节改为引用 `ai_workflow.md`，不重复展开。

**FIX-010** 🟡 OPT-001 缺少 `ai_workflow.md` hotfix 章节的内容草稿
- 问题：OPT-001 说"新增 hotfix 流程并接入 ai_workflow.md"，但方案未给出具体文本。当前 `ai_workflow.md` 第 6-8 行的变更分级表只有 major/minor。
- 修复：在 §3.1 或 OPT-001 中补充 `ai_workflow.md` hotfix 章节的最小草稿（变更分级表新增 hotfix 行 + hotfix 简化流程描述），避免落地时再设计。

### 17.4 机制可行性问题

**FIX-011** 🔴 §9.3 逃生通道的 `gate-warnings.log` 审计机制不可行
- 问题：§9.3 第 2 条要求"每次使用逃生通道必须在 `gate-warnings.log` 中留痕"。但 `--no-verify` 跳过整个 pre-commit，`aicoding_gate_log_warning` 的调用在 pre-commit 内部，日志根本不会被写入。
- 修复方案（二选一）：
  - A：在 `post-commit` hook 中检测上一次 commit 是否跳过了 pre-commit（对比 `gate-pass.log` 最后记录的 HEAD 与当前 HEAD），缺失则写入 `gate-warnings.log`。
  - B：改为要求在 commit message 中标注 `[escape:<原因>]`（commit-msg hook 不受 `--no-verify` 影响——**更正：`--no-verify` 同样跳过 commit-msg hook**）。因此只能用方案 A，或接受 `--no-verify` 场景下日志缺失，改为依赖 `git log --format` 事后审计。

**FIX-012** 🟡 结果门禁（§4.1）的执行时机需要更精确
- 问题：方案说"Implementation→Testing 推进时首次执行 + Testing→Deployment 前置再次执行"，但 pre-commit 在每次 `git commit` 时触发。如果测试命令耗时较长（如 `pytest` 跑数分钟），每次 commit 都等待会严重影响体验。
- 修复：明确结果门禁仅在检测到 `_phase` 字段变更的 commit 中触发（即阶段推进 commit），普通代码 commit 不执行 `result_gate_*` 命令。在 OPT-005 中补充此触发条件。

**FIX-013** 🟡 §6.2 status.md 双轨问题在 M1/M2 中无任何修复
- 问题：§6.2 推荐路径（status.yaml）标注为 M3，兼容路径（YAML↔表格一致性校验）也未进入任何 OPT 任务。M1/M2 落地后双轨问题仍然存在。
- 修复：将兼容路径（pre-commit 增加 YAML front matter 与表格关键字段一致性校验）归入 M2，作为 OPT-005 的子项或独立 OPT-005b。

### 17.5 文字/格式修正

**FIX-014** 🔵 §15 ENR-008 状态描述不准确
- 问题：写"4/5 已完成，剩余 #4"，但 §6.3 明确说 #1 和 #5 是"部分修复"（⚠️ 标记）。实际是 2/5 完成、2/5 部分修复、1/5 待修。
- 修复：改为"2/5 已完成（#2/#3）、2/5 部分修复（#1/#5）、1/5 待修（#4）"。

**FIX-015** 🔵 §7.2 第 4 条 `phase_skip_proposal: false` 语义反直觉
- 问题：`false` 表示"不跳过"，这是默认行为，配置项的存在没有意义。
- 修复：改为"例：`phase_skip_proposal: true`（跳过 Proposal 阶段）"，未配置时默认不跳过。

---

### 17.6 待修清单汇总

| ID | 级别 | 归属任务 | 摘要 |
|---|---|---|---|
| FIX-001 | 🔴 | 文档修正 | §12.1 config key 名与 §7.1 不一致 |
| FIX-002 | 🟡 | OPT-003 扩展 | `aicoding_config_value` 同类正则注入 |
| FIX-003 | 🟡 | 文档修正 | §13.2 验收指标与 SKELETON-END 实际能力不匹配 |
| FIX-004 | 🟡 | 文档补充 | §3.1 hotfix 隐含路径未说清 |
| FIX-005 | 🔵 | OPT-001 补注 | 枚举已就绪，工作量更小 |
| FIX-006 | 🟡 | OPT-002 补充 | `review_gate_common.sh` 定位未明确 |
| FIX-007 | 🟡 | OPT-002 补充 | `inject-phase-context.sh` find fallback |
| FIX-008 | 🔴 | OPT-003 扩展 | `read-tracker.sh` $$ 问题未入任务 |
| FIX-009 | 🔴 | OPT-002 扩展 | `AGENTS.md.template` 整理未入任务 |
| FIX-010 | 🟡 | OPT-001 补充 | hotfix 章节缺内容草稿 |
| FIX-011 | 🔴 | OPT-004 修正 | 逃生通道日志机制不可行 |
| FIX-012 | 🟡 | OPT-005 补充 | 结果门禁执行时机需精确 |
| FIX-013 | 🟡 | M2 新增 | status.md 双轨兼容校验未入任务 |
| FIX-014 | 🔵 | 文档修正 | ENR-008 状态描述不准确 |
| FIX-015 | 🔵 | 文档修正 | `phase_skip_proposal` 语义反直觉 |

**落地建议**：4 个 🔴 项（FIX-001/008/009/011）必须在对应 OPT 任务启动前修正，否则会导致落地偏差或机制失效。其余 🟡/🔵 项可在落地过程中顺带修正。
