# Review Report：Implementation / <版本号>

> **共享章节**：见 `templates/review_skeleton.md`
> 本模板只包含 Implementation 阶段特定的审查内容

| 项 | 值 |
|---|---|
| 阶段 | Implementation |
| 版本号 | <版本号> |
| 日期 | YYYY-MM-DD |
| 基线版本（对比口径） | tag / commit（例如 `v1.0`） |
| 复查口径 | diff-only / full |
| Active CR（如有） | CR-YYYYMMDD-001, CR-... |
| 审查范围 / 输入材料 | 代码变更（diff/PR/commit）；requirements.md, plan.md, 代码 diff |

## §-1 预审结果（🔴 MUST，审查前执行）

> 启动 REP 审查前必须先执行预审门禁（见 `phases/05-implementation.md`）。全部 ✅ 后方可继续以下审查；如有 ❌，先修复再重新预审，不进入 REP。多轮审查时每轮修复后同样须重新预审。

| 检查项 | 命令 | 结果 | 通过 |
|-------|------|------|------|
| 测试 | `<result_gate_test_command>` | <输出摘要或 pass/N条通过> | ✅/❌ |
| 构建 | `<result_gate_build_command>` | <输出摘要> | ✅/❌ |
| 类型检查 | `<result_gate_typecheck_command>` | <输出摘要> | ✅/❌ |
| 产出物就绪 | `<确认本阶段非 review 产出物已存在>` | <代码改动/实现产出摘要> | ✅/❌ |

## 结论摘要
- 总体结论：✅ 通过 / ⚠️ 有条件通过 / ❌ 不通过
- Blockers（P0）：X / 高优先级（P1）：Y / 其他建议（P2+）：Z
<!-- 严重度: P0=Blocker必须Fix / P1=Major必须Fix(Impl禁止Accept/Defer) / P2=Minor建议修复 -->

## 关键发现（按优先级）
> 见 `templates/review_skeleton.md` 的"关键发现"章节

### RVW-001（P0）<标题>
- 证据：
- 风险：
- 建议修改：
- 验证方式（可复现）：

## §0 审查准备（REP 步骤 A+B）
> 见 `templates/review_skeleton.md` 的"§0 审查准备"章节
>
> **本阶段特定说明**：
> - A. 事实核实：从代码变更中提取事实性声明，对照 git diff + 测试运行结果核实
> - B. 关键概念交叉引用：提取关键概念（变量/函数命名与设计文档对应、配置键名、API 路径）

## Implementation 审查清单
- [ ] 安全：无密钥泄露；无注入/XSS/SSRF/越权；鉴权正确
- [ ] 边界与错误：空值/极值/并发/超时/重试明确；错误不静默；错误码/提示语一致
- [ ] 可维护性：命名清晰；重复/复杂度可控；符合既有代码风格
- [ ] 内容完整性：所有任务无遗漏
- [ ] 测试与证据：关键路径有测试；给出可复现验证命令与结果
- [ ] 里程碑展示：plan.md 中标注 🏁 的任务是否都有用户确认记录

## 任务完成度
| 任务ID | 任务名称 | 状态 | 备注 |
|--------|---------|------|------|
| T001 | ... | ✅完成 | |
- 总任务数: N / 完成: X / 跳过: Y（每条必须有原因） / 变更: Z（每条必须有原因）

## 需求符合性审查（REQ 模式）
<!-- 默认 TECH+REQ(all)，建议diff-only。输入隔离：必须读requirements.md全量+被审查产出物，不得用design/plan的设计意图作为GWT通过理由 -->

### 逐条 GWT 判定表（🔴 MUST）
<!-- 每条GWT-ID必须出现并判定；表中只写定位信息（文件:行号、命令、截图链接），不内联大段代码/日志 -->
| GWT-ID | REQ-ID | 判定 | 证据类型 | 证据（可复现） | 备注 |
|--------|--------|------|---------|--------------|------|
| GWT-REQ-001-01 | REQ-001 | ✅ | CODE_REF | `src/xx.ts:42` |  |
| GWT-REQ-C001-01 | REQ-C001 | ❌ | UI_PROOF | 截图链接/E2E断言输出 |  |
<!-- 判定枚举: ✅PASS/❌FAIL/⚠️WARN(视为未通过)/DEFERRED_TO_STAGING(禁止用于REQ-C)/CARRIED(仅incremental,禁止用于REQ-C) -->
<!-- 证据类型: CODE_REF(文件:行号)/RUN_OUTPUT(命令+输出)/UI_PROOF(截图/E2E)。REQ-C必须UI_PROOF或RUN_OUTPUT -->

### 对抗性审查（REQ-C 强制）
<!-- 每条禁止项GWT：列出≥2条泄漏路径→逐条排除并给证据→无法列出则⚠️WARN -->
对每条禁止项 GWT：1. 列出泄漏路径(≥2条) 2. 逐条排除并给证据 3. 无法列出→`⚠️ WARN`
<!-- 人类抽检: 摘要块填min(5,max(1,ceil(GWT_TOTAL*0.1)))条SPOT_CHECK_GWTS；Major还须填SPOTCHECK_FILE / 禁止全PASS零备注: pass时备注列须≥1条潜在风险说明 / 增量审查: incremental时须输出影响分析，未受影响GWT标CARRIED，REQ-C不允许carry-over -->

## §3 覆盖率证明（REP 步骤 D）
> 见 `templates/review_skeleton.md` 的"§3 覆盖率证明"章节

| 维度 | 应检项数 | 已检 | 未检 | 未检说明 |
|------|---------|------|------|---------|
| 事实核实（步骤A） | | | | |
| 概念交叉引用（步骤B） | | | | |
| 审查清单项 | 6 | | | |
| GWT 判定项 | | | | |

### 对抗性自检（🔴 MUST，自审时必填）
> 通用检查项见 `templates/review_skeleton.md`

- [ ] 是否存在"我知道意思但文本没写清"的地方？
- [ ] 所有新增 API 是否都有完整契约（路径/参数/返回/权限/错误码）？
- [ ] 所有"可选/或者/暂不"表述是否已收敛为单一口径？
- [ ] 是否有验收用例无法仅凭文档文本判定 pass/fail？
- [ ] 高风险项（兼容/回滚/权限/REQ-C）是否已在本阶段收敛，而非留给后续阶段？

## 建议验证清单（命令级别）
- [ ] ...

## 处理记录（建议由开发/人工填写）
| RVW-ID | 严重度 | 处理决策（Fix/Defer/Accept） | Owner | 说明 | 链接/证据 |
|---|---|---|---|---|---|
| RVW-001 | P0 |  |  |  |  |

## 证据清单
> 见 `templates/review_skeleton.md` 的"证据清单"章节

## 机器可读摘要块（🔴 MUST，文件末尾）

<!-- REVIEW-SUMMARY-BEGIN -->
REVIEW_STAGE: implementation
REVIEW_SCOPE: diff-only|full|incremental
REVIEW_MODES: TECH,REQ,TRACE
CODE_BASELINE: <status.md _current>
REQ_BASELINE_HASH: <hash(requirements.md 的 GWT 定义行)>
GWT_TOTAL: <number>
GWT_CHECKED: <number>
GWT_CARRIED: <number>
CARRIED_FROM_COMMIT: <hash-or-N/A>
CARRIED_GWTS: <GWT-ID>,<GWT-ID>,...
GWT_DEFERRED: <number>
GWT_FAIL: <number>
GWT_WARN: <number>
SPOT_CHECK_GWTS: <GWT-ID>,<GWT-ID>,...
SPOTCHECK_FILE: docs/<版本号>/spotcheck_implementation_<cr-id>.md
GWT_CHANGE_CLASS: clarification|structural|N/A
CLARIFICATION_CONFIRMED_BY: <human-or-N/A>
CLARIFICATION_CONFIRMED_AT: YYYY-MM-DD|N/A
VERIFICATION_COMMANDS: <实际执行的验证命令列表，逗号分隔>
REVIEW_RESULT: pass|fail
<!-- REVIEW-SUMMARY-END -->

---

## 多轮审查追加格式
> 见 `templates/review_skeleton.md` 的"多轮审查追加格式"章节
