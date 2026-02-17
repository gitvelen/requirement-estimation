# 阶段化审查模板（`review_template.md`）

> 本模板同时用于两类场景：  
> 1) **AI 自审（🔴 MUST）**：Phase 03-06（Design/Planning/Implementation/Testing）每阶段结束前必须自审并落盘 `review_<stage>.md`（见 `phases/` 的“完成条件”）。  
> 2) **独立审查（可选）**：仅当用户明确触发（推荐触发词：`@review`）时进入“Reviewer 模式”。  
>
> 目标：审查阶段产出/代码变更，给出可执行建议与可复现证据，并将报告**落盘**（若有更新，则在文末追加，并标明追加的版本号）。

## 独立审查触发约定（默认关闭）
- 触发：用户消息包含 `@review`（或 `review:` / “执行审查”）
- 行为：只做审查，不修改业务代码；仅允许创建/更新审查报告文件（除非用户明确要求“边审边改”）
- 报告落盘路径：`docs/<版本号>/review_<stage>.md`（阶段名用小写英文）
- 审查口径：优先读取 `docs/<版本号>/status.md` 中的“基线版本/本次复查口径/Active CR 列表”（支持 diff-only）

## 落盘报告格式（建议统一）
> 输出必须“可落地”：每条发现都要有**证据**、**建议动作**、**验证方式**。

```markdown
# Review Report：<阶段> / <版本号>

| 项 | 值 |
|---|---|
| 阶段 | <Proposal/Requirements/...> |
| 版本号 | <版本号> |
| 日期 | YYYY-MM-DD |
| 基线版本（对比口径） | tag / commit（例如 `v1.0`） |
| 复查口径 | diff-only / full |
| Active CR（如有） | CR-YYYYMMDD-001, CR-... |
| 检查点 | 检查了哪些点就写什么… |
| 审查范围 | 文档/代码/模块… |
| 输入材料 | 列出关键文件/链接/命令 |

## 结论摘要
- 总体结论：✅ 通过 / ⚠️ 有条件通过 / ❌ 不通过
- Blockers（P0）：X
- 高优先级（P1）：Y
- 其他建议（P2+）：Z

## 关键发现（按优先级）
### RVW-001（P0）<标题>
- 证据：
- 风险：
- 建议修改：
- 验证方式（可复现）：

### RVW-002（P1）<标题>
...

## 建议验证清单（命令级别）
- [ ] ...

## 开放问题
- [ ] ...

## 处理记录（建议由开发/人工填写）
| RVW-ID | 严重度 | 处理决策（Fix/Defer/Accept） | Owner | 说明 | 链接/证据 |
|---|---|---|---|---|---|
| RVW-001 | P0 |  |  |  |  |
```

## 严重度判定口径（🔴 MUST）

> 所有审查发现必须按以下标准分级，确保 AI 自动审查与人工审查口径一致。

| 严重度 | 判定标准 | 门禁影响 | 处理要求 |
|--------|---------|---------|---------|
| **P0（Blocker）** | 功能不可用/数据丢失/安全漏洞/API 契约破坏/编译失败/测试全量失败 | 必须修复，否则阶段不可收敛 | 必须 Fix |
| **P1（Major）** | 功能降级/边界未处理/性能不达标/文档与代码不一致/回滚方案缺失/CR 影响面遗漏 | 必须修复或明确 accept/defer（写清理由+缓解；Implementation/Testing 阶段禁止 Accept/Defer） | Fix / Accept / Defer |
| **P2（Minor）** | 代码风格/命名不规范/注释缺失/文档格式/非关键路径优化建议 | 不阻塞收敛 | 建议修复，可忽略 |

**判定原则**：
- 影响用户可见行为或数据正确性 → P0
- 影响可靠性/可维护性/可追溯性但不直接影响用户 → P1
- 仅影响代码质量/风格 → P2
- 拿不准时就高不就低（宁可 P1 不可 P2）

## 消费与闭环（建议）
> 本模板产出是“建议”，不等于必须修改；但必须对建议做决策与记录，避免审查沦为形式。

- 读取 `docs/<版本号>/review_<stage>.md`（分阶段）
- 对每条 `RVW-xxx` 填写“处理记录”：Fix / Defer / Accept（必须写理由与风险）
- 若选择 Fix：将动作落到 `docs/<版本号>/plan.md`（任务/Owner/验证方式）或直接改代码；修复后可再次 `@review` 覆盖报告
- 若选择 Defer/Accept：建议补充缓解手段（监控/告警/开关/回滚/运行手册）并记录到设计/部署/状态文件（按影响面）
- 复盘沉淀：同类问题重复出现时，将要点提炼到 `docs/lessons_learned.md`

<!-- SKELETON-END: 以下为参考材料，按需阅读 -->

## 需求符合性审查协议（`@review` REQ 模式）

> 目的：把“讨论过的要求”变成**可判定、可门禁**的外键，防止需求在阶段传递中衰减。  
> 与上方 RVW-based 技术审查（TECH）**并行**，不互相替代。

### 触发与默认模式
- Implementation 阶段：默认启用 `TECH + REQ(all)`，建议 `REVIEW_SCOPE: diff-only`
- Testing 阶段：默认启用 `REQ(all) + TRACE`，建议 `REVIEW_SCOPE: full`

### 输入隔离（🔴 MUST）
- ✅ 必须读：`requirements.md`（全量）+ 被审查产出物（代码/页面/配置/命令输出/截图链接等）
- ❌ 不得用：`design.md` / `plan.md` 的“设计意图”作为 GWT 通过理由（可用于定位文件线索，但不能替代字面判定）

### 逐条 GWT 判定表（🔴 MUST）

> `requirements.md` 中的每条 `GWT-ID` 都必须在此表中出现并被判定（✅/❌/⚠️/`DEFERRED_TO_STAGING`/`CARRIED`），不允许遗漏。  
> **注意**：表中只写“定位信息”（`文件:行号`、可复现命令、截图链接等），不要内联大段代码/长日志。

| GWT-ID | REQ-ID | 判定 | 证据类型 | 证据（可复现） | 备注 |
|--------|--------|------|---------|--------------|------|
| GWT-REQ-001-01 | REQ-001 | ✅ | CODE_REF | `src/xx.ts:42` |  |
| GWT-REQ-C001-01 | REQ-C001 | ❌ | UI_PROOF | 截图链接/E2E断言输出 |  |

**判定枚举**：
- ✅ PASS：满足 GWT 字面要求
- ❌ FAIL：不满足
- ⚠️ WARN：无法判定/证据不足/需求歧义（视为未通过，必须先澄清或补证据）
- `DEFERRED_TO_STAGING`：当前环境无法验证（不计为 WARN；允许但受限；必须写验证计划；禁止用于 REQ-C）
- `CARRIED`：增量审查沿用上次结论（仅 `REVIEW_SCOPE: incremental` 允许；禁止用于 REQ-C）

**证据类型枚举（建议）**：
- `CODE_REF`：`文件:行号`（适用于静态契约、字段定义、配置默认值等）
- `RUN_OUTPUT`：命令 + 关键输出（适用于接口契约、测试结果、性能指标）
- `UI_PROOF`：截图链接 / DOM 文本断言输出 / E2E 输出（适用于 UI 展示/文案/权限差异）

**最低证据规则（🔴 MUST）**：
- REQ-C（禁止项）：必须 `UI_PROOF` 或 `RUN_OUTPUT`（不可降级，不接受仅凭 `CODE_REF` 推断 PASS）
- 正向功能（静态可判定）：最低 `CODE_REF`
- 正向功能（行为性/运行时）：最低 `RUN_OUTPUT`

**UI 禁止项最小状态矩阵（建议写在备注里）**：
- 角色：管理员/普通用户（或需求定义的全部角色）
- 状态：空/有数据/异常/加载（覆盖 2–4 个关键状态；要求更严时以 requirements 为准）

### 对抗性审查（REQ-C 强制）
对每条禁止项 GWT：
1. 先列出该禁止项可能泄漏的路径（至少 2 条，如：条件分支遗漏、动态渲染、第三方组件注入等）
2. 逐条排除并给出证据
3. 无法列出泄漏路径 → 记为 `⚠️ WARN`（审查不充分）

### 人类抽检锚点（🔴 MUST）
在摘要块中填写 `min(5, max(1, ceil(GWT_TOTAL * 0.1)))` 条（下限 1，上限 5）“建议人类优先抽检”的 `GWT-ID`（选择标准：证据最薄弱 / 判定最依赖推断 / 涉及多角色交叉）。缺少此标注视为报告不完整（门禁拦截）。
Major 交付还必须填写 `SPOTCHECK_FILE`，指向独立的人类抽检文件（建议：`docs/<版本号>/spotcheck_<stage>_<cr-id>.md`）。

### 禁止“全 PASS 零备注”
若最终要 `REVIEW_RESULT=pass`（所有 GWT 均 PASS），备注列必须至少补充 1 条“潜在风险/边界条件”说明（判定仍为 PASS）。  
为避免形式化填充，建议将该风险说明写在 `SPOT_CHECK_GWTS` 之一对应行（门禁也按此口径验真）。

### 增量审查（可选，变更范围有限时）
- 摘要块标注 `REVIEW_SCOPE: incremental`
- 必须输出影响分析：变更文件 → 关联 REQ → 关联 GWT，明确列出本次重新判定的 GWT 子集
- 未受影响的 GWT 可沿用上次判定：在表中将判定列标记为 `CARRIED`，并在摘要块填写 `CARRIED_FROM_COMMIT` + `CARRIED_GWTS`
- **限制**：REQ-C 类 GWT 不允许 carry-over（禁止项必须每次重新验证）

### 机器可读摘要块（🔴 MUST，文件末尾）

> 门禁只认**最后一次**摘要块；`GWT_*` 计数必须可验真（由脚本从 requirements/review 表重算交叉校验）。

```text
<!-- REVIEW-SUMMARY-BEGIN -->
REVIEW_STAGE: implementation|testing|design|planning|requirements
REVIEW_SCOPE: diff-only|full|incremental
REVIEW_MODES: TECH,REQ,TRACE
CODE_BASELINE: <status.md _current>
REQ_BASELINE_HASH: <hash(requirements.md 的 GWT 定义行)>  # 仅基于 GWT-REQ...: 行计算（避免改说明文字触发全量重审）
GWT_TOTAL: <number>
GWT_CHECKED: <number>                 # 本次新判定条目数（不含 CARRIED；含 DEFERRED_TO_STAGING）
GWT_CARRIED: <number>                 # 增量审查沿用条目数（表内标记为 CARRIED）
CARRIED_FROM_COMMIT: <hash-or-N/A>
CARRIED_GWTS: <GWT-ID>,<GWT-ID>,...  # 增量审查沿用的具体 GWT-ID 列表（非 incremental 填 N/A）
GWT_DEFERRED: <number>                # DEFERRED_TO_STAGING 条目数（无则填 0）
GWT_FAIL: <number>
GWT_WARN: <number>
SPOT_CHECK_GWTS: <GWT-ID>,<GWT-ID>,...
SPOTCHECK_FILE: docs/<版本号>/spotcheck_<stage>_<cr-id>.md
GWT_CHANGE_CLASS: clarification|structural|N/A
CLARIFICATION_CONFIRMED_BY: <human-or-N/A>
CLARIFICATION_CONFIRMED_AT: YYYY-MM-DD|N/A
REVIEW_RESULT: pass|fail
<!-- REVIEW-SUMMARY-END -->
```

### 不允许降级
- 不允许 `fast/skip/partial` 绕过 `REQ(all)` 或 GWT 粒度判定
- 不允许用 `Accept/Defer` 绕过任何 `FAIL/WARN`

## 附：更多 Reviewer 口令（可选）
- 口令库：`.aicoding/skills/workflow/reviewer-prompts.md`（按安全/边界/性能/可维护/测试等维度选择 2–3 条组合使用）
- PR 审查（如启用 skills）：`/review-pr`（见 `.aicoding/skills/workflow/review-pr`）

## 阶段审查清单（按阶段选用）

### 1) Proposal 阶段
**产出**：`docs/<版本号>/proposal.md`  
**重点**：价值、范围边界、成功指标口径、风险与依赖、替代方案、开放问题

- [ ] 价值明确：说清楚“为谁解决什么问题”
- [ ] 指标可衡量：给出口径与基线→目标
- [ ] 范围清晰：包含/非目标完整，避免范围蔓延，逻辑自洽无歧义
- [ ] 风险完整：每个风险都有应对
- [ ] 替代方案：至少比较 1 个替代方案（如适用）

### 2) Requirements 阶段
**产出**：`docs/<版本号>/requirements.md`  
**重点**：可验收、完整、一致、可追溯、边界与异常覆盖

- [ ] 每条需求可验收：有可判定验收标准（GWT/明确指标；第三方仅凭文字即可判 PASS/FAIL）
- [ ] 场景覆盖完整：正常/异常/边界覆盖
- [ ] 需求无冲突：术语/口径一致，逻辑自洽无自相矛盾
- [ ] 可追溯：REQ/SCN/API/TEST ID 使用规范
- [ ] 数据与错误码：输入/输出/约束/错误码清晰
- [ ] 内容完整：对照proposal.md逐条验证覆盖情况（缺的要承认）
- [ ] 禁止项/不做项已收口：`review_requirements.md` 含"禁止项/不做项确认清单"+ `CONSTRAINTS-CHECKLIST` + `CONSTRAINTS-CONFIRMATION`（见 `02-requirements.md §禁止项确认条款`）

### 3) Design 阶段
**产出**：`docs/<版本号>/design.md`  
**重点**：架构可落地、依赖方向、扩展性、兼容与迁移、接口与数据模型、安全与可观测

- [ ] 与需求一一对应：关键设计点能追溯到 REQ/SCN/API
- [ ] 依赖关系合理：无循环依赖，职责边界清晰
- [ ] 失败路径充分：最常见失败模式与降级/重试策略明确
- [ ] 兼容与回滚：数据/接口/配置的向后兼容与回滚可执行
- [ ] 安全设计：鉴权/越权/输入验证/敏感数据处理明确
- [ ] 内容完整：对照requirements.md逐条验证覆盖情况（缺的要承认）

### 4) Planning 阶段
**产出**：`docs/<版本号>/plan.md`  
**重点**：任务可执行、依赖清晰、DoD 明确、验证方式可复现、风险预案

- [ ] 任务可追踪：Txxx ID 完整；每条有清晰 DoD
- [ ] 粒度合适：可独立实现与验证；依赖关系清晰
- [ ] 追溯完整：任务关联 REQ/SCN/API/TEST
- [ ] 验证可复现：每个任务有命令级别验证方式
- [ ] 风险与回滚：涉及线上行为变化的任务有开关/回滚思路
- [ ] 内容完整：覆盖需求和设计阶段产出的成果

### 5) Implementation 阶段
**产出**：代码变更（diff/PR/commit）  
**重点**：对我这些代码变更进行严厉拷问安全、边界与异常、错误处理、可维护性、测试与证据

- [ ] 安全：无密钥泄露；无注入/XSS/SSRF/越权；鉴权正确
- [ ] 边界：空值/极值/并发/超时/重试处理明确
- [ ] 错误处理：错误不静默；错误码/提示语一致；审计日志必要时齐全
- [ ] 可维护性：命名清晰；重复/复杂度可控；符合既有代码风格
- [ ] 内容完整性：所有任务无遗漏
- [ ] 测试与证据：关键路径有测试；给出可复现验证命令与结果

### 6) Testing 阶段
**产出**：`docs/<版本号>/test_report.md`  
**重点**：覆盖率（含回归范围）、真实性、独立性、失败可诊断、性能基线（如适用）

- [ ] 覆盖完整：所有 REQ 追溯到 TEST/证据
- [ ] 边界/异常覆盖：空值/异常/并发/超时等
- [ ] 环境与数据：接近真实；数据准备/清理说明
- [ ] 性能（如适用）：有基线→实测→结论

### 7) Deployment 阶段
**产出**：`docs/<版本号>/deployment.md`  
**重点**：可执行步骤、回滚可行、迁移安全、灰度与监控、影响评估与通知

- [ ] 回滚：触发条件与步骤明确（必要时演练）
- [ ] 迁移：备份/校验/失败处理清楚，可重复执行
- [ ] 灰度/开关：策略与扩大条件明确（如适用）
- [ ] 监控告警：关键指标/阈值/观察窗口明确
- [ ] 影响面：用户可感知变更与沟通计划清楚

## 通用审查视角（可按需附加）
- **证据驱动**：列出“你验证了什么、怎么验证、关键输出是什么”；避免仅凭推断
- **红队视角**：假设我是攻击者/最挑剔的测试，如何打爆它？防护是否到位？
- **文档寿命**：6 个月后新人能否快速上手？是否有模糊/过期/不一致术语？

---

*模板版本: v2.0 | 建议配合 `status.md/plan.md` 做闭环（review 报告→处理决策→验证证据）*

---

## 审查记录格式（追加式）

> 本文件记录多轮审查记录，按时间正序排列（最新在最末尾）

### 报告格式（每轮追加到文件末尾）

````markdown
## YYYY-MM-DD HH:MM | 第 N 轮 | 审查者：<Name>

### 审查角度
[本次审查的角度定位]

### 上一轮问题处理状态
| RVW-ID | 严重度 | 上一轮描述 | 处理方式 | 本轮状态 |
|---|---|---|---|---|

### 本轮新发现问题
| RVW-ID | 严重度 | 描述 | 证据 | 建议 |
|---|---|---|---|---|

### 收敛判定
- 本轮后：P0(open)=X, P1(open)=Y
- 距离收敛：是/否
- 建议：[是否建议人工确认/自动推进]
````

---

## 附录：自动化检查命令集

> **重要说明**：以下命令为 AI 参考的示例伪代码，AI 应根据项目实际环境、工具链和目录结构调整后执行。
> - 如项目未安装 `rg`（ripgrep），可替换为 `grep -rn`
> - 临时文件应使用唯一名称（如包含版本号），避免多人/多版本并行时冲突
> - 命令执行前应检查目标文件是否存在，不存在时给出明确提示

### AC-01: 覆盖性检查（Requirements 阶段）
> 注意：Proposal In Scope 为普通 bullet，需人工核对；Requirements 编号格式为 REQ-xxx

```bash
# 1. 提取提案 In Scope（人工阅读 "### 包含" 章节）
awk 'p && /^## /{exit} p && /^### / && !/^### 包含/{exit} /^### 包含/{p=1} p{print}' docs/<版本号>/proposal.md

# 2. 提取需求落地清单（功能性 REQ-001 和非功能 REQ-101 等）
rg -n "^#### REQ-" docs/<版本号>/requirements.md
# 备选（无 rg 时）：grep -n "^#### REQ-" docs/<版本号>/requirements.md
```

### AC-02: 关键词一致性检查
```bash
rg -n "关键词1|关键词2" docs/<版本号>/requirements.md
# 备选：grep -n "关键词1\|关键词2" docs/<版本号>/requirements.md
```

### AC-03: 引用存在性检查（R6）
> 目标：验证 plan.md 中引用的所有 REQ 都存在于 requirements.md 中
> 关键：只从 `^#### REQ-` 提取"定义"，避免把引用当定义

```bash
VERSION="<版本号>"  # 替换为实际版本号

# 1. 提取 plan.md 中的所有 REQ 引用
rg -o "REQ-[0-9]+" docs/${VERSION}/plan.md | LC_ALL=C sort -u > /tmp/plan_refs_${VERSION}.txt

# 2. 提取 requirements.md 中定义的所有 REQ（只从定义行提取）
rg "^#### REQ-[0-9]+：" docs/${VERSION}/requirements.md | sed 's/^#### //;s/:.*//' | LC_ALL=C sort -u > /tmp/req_defs_${VERSION}.txt

# 3. 计算差集（plan 引用但 requirements 未定义的 REQ）
LC_ALL=C comm -23 /tmp/plan_refs_${VERSION}.txt /tmp/req_defs_${VERSION}.txt

# 期望输出：空（无差集表示所有引用都有定义）
# 如文件不存在，命令会报错，AI 应提示"请先确认文件路径"
```

### AC-04: 全量回归检查
> 注：以下为示例命令，请按项目实际测试框架调整
```bash
# Python 项目示例
.venv/bin/pytest -q

# 其他项目示例（按需选用）：
# npm test          # Node.js/JavaScript
# mvn test         # Java
# go test ./...    # Go
# cargo test       # Rust
```

### AC-05: diff-only审查增强（CR场景，P1）

> **目标**：验证CR列出的影响面与实际代码/文档变更的一致性，发现遗漏和级联影响。
> **触发条件**：有 Active CR 时自动启用
> **执行入口**：详见本文档附录 AC-05

#### 步骤

1. **读取CR文件，提取Impact字段**
   - 阶段文档影响：proposal/requirements/design/plan/test_report/deployment
   - 主文档影响：系统功能说明书/技术方案设计/接口文档/用户手册/部署记录
   - 代码影响：影响模块/文件

2. **执行代码diff**
   ```bash
   # 方案1：AI直接读取status.md（推荐，默认方式）
   # AI读取docs/<版本号>/status.md，解析表格获取基线版本和当前代码版本
   # 然后执行：git diff <基线版本>..<当前代码版本> --name-only

   # 方案2：命令行解析（依赖status.md的可机读行）
   # status.md 必须在表格前有可机读的key-value行：
   #   _baseline: v1.0
   #   _current: HEAD
   BASELINE=$(grep "^_baseline:" docs/<版本号>/status.md | awk '{print $2}')
   CURRENT=$(grep "^_current:" docs/<版本号>/status.md | awk '{print $2}')
   git diff ${BASELINE}..${CURRENT} --name-only
   ```

3. **对比分析**
   - CR列出的影响 vs 实际代码变更
   - CR列出的影响 vs 实际文档变更
   - 识别遗漏（CR未列出但实际变更）
   - 识别过度描述（CR列出了但实际未变更）

4. **输出差异报告**

#### 差异报告格式

```markdown
### CR vs 实际代码差异分析
| CR列出的影响 | 实际代码变更 | 差异类型 | 严重度 |
|-------------|-------------|---------|-------|
| API-A（src/api/a.go） | src/api/a.go | 一致 | - |
| - | src/common/util.go | CR遗漏 | P1 |
| design 3.2节 | - | CR过度描述 | P2 |

### 级联影响分析
| 修改模块 | 调用者 | 是否需要更新CR | 建议 |
|---------|--------|---------------|------|
| src/api/a.go | frontend/api.ts | 是 | 建议将frontend/api.ts加入CR影响 |
| src/auth/service.go | src/user/profile.go | 否 | 无影响，仅内部调用 |

### 建议
- P1差异：请更新CR的"代码影响"字段，包含 src/common/util.go
- P2差异：请确认design 3.2节是否仍在本次变更范围，如不是请移除
```

#### 超时处理（避免分析耗时过长）

- 如分析超过30秒，跳过级联影响分析
- 保留 CR vs 代码差异报告 + 强制人工确认

#### 收敛判定

- P1差异必须修复后才能收敛（🔴 MUST）
- P2差异可接受人工确认后继续
