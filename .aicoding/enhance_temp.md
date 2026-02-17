# enhance_temp：基于 `@review` 的"需求不衰减"交付机制（工具无关）

> **SPEC_VERSION: 1.1**（实质性变更时递增；多项目并行时以此区分执行版本）

> 目的：解决"明明在提案/需求中说清楚了，但交付仍与要求不一致"的结构性问题，确保**要做/不许做**在全流程中不丢失，并在关键节点被**程序化门禁**拦截。
>
> 约束：**不新增阶段**；复用既有 8 阶段骨架与 `@review` 机制；兼容 Claude / Codex，审查时不需要关心由谁执行。

## 1. 人类角色的核心顾虑（要被机制解决）

> 完整来源：`worry.md`（10 条）。以下逐条列出并标注本方案的对应机制。

1) **交付偏差**：明明说清楚了，交付仍不一致——总纲性顾虑，本方案整体目标。→ §2 DoD + §7 门禁
2) **负向需求（不要/禁止/不允许）更易丢**：没有独立 ID/验收/测试，最终 UI 上"冒出来"。→ §3.2 + §5 断点1 + §8.2
3) **需求在阶段传递中衰减**：Implementation 按任务推进，AI 读过 requirements 但后续会忘；修一处漏一处。→ §5 断点3 + §6 @review
4) **测试/证据存在 ≠ 逐条验过**：`test_report.md` 可写得很好看，但可能只覆盖部分 REQ；门禁只查"证据存在性"无法拦截遗漏。→ §7.3 + §10.8
5) **门禁"查证据存在"而非"覆盖完整"**：交付关口只验证有没有证据，不验证每条需求是否都被覆盖与判定。→ §6.4.3 + §7.3
6) **自审盲区与角色泄漏**：同一 AI 先实现再审查，容易用"设计意图"合理化偏差；需要"验收者视角"的强约束。→ §6.3 + §6.3.1
7) **流程成本与上下文开销**：机制过重会导致 AI 敷衍、人类放弃执行、上下文爆炸；需要审查深度与风险成正比的分层策略。→ §6.8
8) **复制导致不一致**：验收清单/追溯表一旦分叉就会过时；必须坚持单一真相源 + ID 引用，禁止全文复制。→ §3.1 + §5 断点3
9) **不想每次手工指定审查参数**：希望自动生成并固化下来，同时可被门禁验证。→ §6.2
10) **口径强硬**：说了"不许做/不允许出现"，就必须做到（以最终用户可见为准）。→ §8.2 + §6.3.1 反向假设

## 2. 目标与收敛口径（Definition of Done）

在 Implementation→Testing、Testing→Deployment 两个阶段推进点，必须满足：
- **GWT 粒度全覆盖**：requirements 中所有 `GWT-ID` 均出现在判定表中（覆盖差集为空），且计数守恒：`GWT_CHECKED + GWT_CARRIED == GWT_TOTAL`。
  - `REVIEW_SCOPE != incremental` 时必须 `GWT_CARRIED=0`（因此 `GWT_CHECKED == GWT_TOTAL`）。
- **0 漏项**：`FAIL=0` 且 `WARN=0`（⚠️ 视为需求歧义或证据不足，必须先修正后推进）。允许有限的 `DEFERRED_TO_STAGING`（见 §6.5.1，不超过总 GWT 的 10%）。
- **证据可复现**：每条 GWT 判定都给出证据（至少 `文件:行号` 或可复现步骤/输出/截图链接等）。
- **基线一致**：requirements 或代码发生变化后，旧的审查结论自动作废，必须重审。
- **不可降级**：不允许 `fast/skip/partial` 等绕过；不允许用 `Accept/Defer` 绕过任何需求不通过/无法判定。
- **禁止项已收口**：所有“不要/不做/禁止/不允许”已在 Requirements 阶段完成确认清单并确认无漏项（见 7.0），否则后续门禁只能保证“按文档不漏”，无法保证“按对话不漏”。

## 3. 核心思想：把“讨论过的要求”变成可判定、可门禁的外键

### 3.1 单一真相源
- `docs/<版本号>/requirements.md` 是唯一需求真相源（**唯一入口**）。
- 如确需拆分为多个 requirements 文件：必须保留 `requirements.md` 作为索引/入口；且门禁/验真逻辑必须能从该入口提取**全量** REQ/GWT（默认实现一般只支持单文件，未升级门禁前禁止拆分）。
- 不复制需求内容（避免过时），只引用：追溯依靠 **ID**（REQ-ID / GWT-ID）。

### 3.2 负向需求与禁止项必须“同等地位”
所有“不要/不许/不得/不显示/不出现”的要求：
- **必须**落为 `REQ-Cxxx`（Constraints & Prohibitions，约束与禁止项），不得仅以 W（Won’t）或口头描述存在。
- **必须**写成可判定 `GWT-ID`，并纳入门禁。

### 3.3 以 `@review` 做“工具无关的验收协议入口”
`@review` 不再是“随便审审”，而是一份**可被脚本校验**的协议输出：
- 同一协议对 Claude/Codex 一致。
- 门禁入口只认“机器可读摘要块”；其中覆盖/计数（`GWT_*`）必须由脚本从源文件交叉校验（见 6.4.3），避免 AI 自报数字。

## 4. ID 与格式规范（强制）

### 4.1 REQ-ID
- 功能/非功能：`REQ-001`、`REQ-101`…
- 禁止项/约束：`REQ-C001`、`REQ-C002`…
- **唯一性（🔴 MUST）**：同一 `requirements.md` 内所有 `REQ-ID` 必须全局唯一（含 `REQ-C`）；重复视为结构错误，门禁硬拦截。

### 4.2 GWT-ID（门禁最小单位）
- **唯一性（🔴 MUST）**：同一 `requirements.md` 内所有 `GWT-ID` 必须全局唯一；重复会导致集合运算静默吞并，门禁必须显式报错并拦截。

#### 4.2.1 写法（显式 ID，强制）
在 `requirements.md` 的每条验收标准（Given/When/Then）前加 `GWT-ID`：
```markdown
**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-001-01: Given 管理员登录，When 打开订单列表页，Then 列头依次为：订单号、客户名、金额、状态、创建时间（共5列，无其他列）
- [ ] GWT-REQ-C001-01: Given 任意角色登录，When 打开订单列表页，Then 页面不出现「九大市场数据域统一展示…」描述性卡片（所有状态：空/有数据/异常）
- [ ] GWT-REQ-C001-02: Given 任意角色登录，When 打开订单列表页，Then 页面文本不包含「手工交易」
```

#### 4.2.2 稳定性规则（避免 ID 漂移）
- 允许改 GWT 文本，但**尽量不改 ID**（ID 作为外键，改动会导致历史审查/证据失效）。
- 新增 GWT 使用递增序号；不建议对既有 GWT 重新排序编号。
- **ID 格式扩展性**：GWT-ID 正则为 `GWT-REQ-C?[0-9]+-[0-9]+`（允许任意位数），以支持大型项目（100+ REQ、单个 REQ 10+ GWT）。门禁脚本中的正则同步。

#### 4.2.3 可判定要求（禁止模糊）
GWT 必须做到**第三方可判定**：
- ✅ OK：列头具体顺序/字段名、页面"不出现某组件/某文案"、接口响应"不包含某字段"
- ❌ 禁止：如"简洁""优化体验""提升性能"（除非给出量化指标与口径）

#### 4.2.4 GWT 粒度指导
- **一条 GWT = 一个可独立判定的行为断言**。不应在一条 GWT 中用 AND 连接多个断言（拆成多条，各自有 ID）。
- 粒度参考：一个 REQ 通常 2–8 条 GWT。少于 2 条说明验收标准可能不够具体；超过 10 条建议检查是否可以拆分 REQ。
- 禁止项（REQ-C）的 GWT 粒度按**适用范围维度**拆分：不同页面/不同入口/不同状态各一条，而非合并为一条大而全的 GWT。

## 5. 针对 4 个断点的“加牙齿”方案（结合 prop.md 有效思路）

> 结论：框架骨架并不缺（GWT、覆盖矩阵、追溯列都在），缺的是“**完整性与真实性**”的强制机制。

### 断点 1：负向需求没有独立地位（不要/禁止丢失）
**机制**：
- requirements 增加独立章节：`Constraints & Prohibitions（REQ-Cxxx）`。
- 每条禁止项必须有 `GWT-ID`，且默认适用范围：**所有角色 + 所有入口 + 页面所有状态**（除非明确限定）。
- UI 禁止项证据规则：必须提供**运行证据**（见第 8 节），不能只凭代码推断。
- **补缺（🔴 MUST）**：Requirements 阶段冻结/推进到 Design 前，必须输出“禁止项/不做项确认清单”（来源：对话 + proposal Non-goals），逐条映射到 `REQ-Cxxx` 并由人类确认无漏项；未确认前不得进入后续阶段（门禁以 `review_requirements.md` 为入口；清单必须出现在 `review_requirements.md`，可额外在 `requirements.md` 附录保留阅读版，但不替代门禁入口）。

### 断点 2：Design 追溯表是建议不是强制
**机制**（不新增阶段，仅增强“出口必须可验证”）：
- design 中要求出现 `REQ → 设计元素` 的追溯映射（可为表格或清单）。
- Design 阶段 `@review` 必须包含 `TRACE` 视角：缺映射或映射不全视为 `WARN`（你要求 0 WARN，所以必须补齐）。

### 断点 3：Implementation 按任务走，不按需求走（信息衰减）
**机制**：
- Planning：新增“反向覆盖”检查，确保 `requirements` 中的每条 REQ 都被 plan 的任务覆盖（避免一开始就漏）。
- plan 顶部维护一个**禁止项引用索引**（仅列 `REQ-C` ID + 一句话摘要，不复制 GWT 全文；内容以 `requirements.md` 为准）。这样既降低"忘记"概率，又避免副本过时（Worry 8）。
- Implementation 阶段推进前强制 `@review`（TECH+REQ(all)，GWT 粒度）作为硬门禁，不依赖 AI 记忆。

### 断点 4：交付门禁只查证据存在，不查覆盖完整
**机制**：
- Testing 阶段必须对齐：`test_report` 覆盖全量 REQ（最终以 `GWT-ID` 判定为准）。
- 交付关口：在现有 W16 的“证据存在性”基础上增加“覆盖完整性”硬拦截（见第 7 节）。

## 6. `@review` 协议（工具无关、自动生成参数、可门禁）

### 6.1 触发
- 用户显式触发：消息包含 `@review`
- 阶段推进隐式触发：Implementation→Testing、Testing→Deployment 前必须存在对应阶段的通过审查报告

### 6.2 默认审查模式（自动生成，不要求人工指定）
> 审查时**不需要**关心是 Codex 还是 Claude；Effective Config 会自动写入报告并被门禁校验。

- **Design 阶段**：`TRACE + REQ(structural)`，建议 `scope=full`
- **Implementation 阶段**：`TECH + REQ(all)`，建议 `scope=diff-only`
- **Testing 阶段**：`REQ(all) + TRACE`，建议 `scope=full`

**术语补充（避免歧义）**：
- `REQ(structural)`：只检查需求文档的结构与可判定性（如 REQ/GWT-ID 存在且格式正确、无明显歧义/占位），不做“实现是否满足需求”的逐条判定。
- `REQ(all)`：对 requirements 中**全量** `GWT-ID` 做逐条判定（见 6.4.1）。

**`REVIEW_SCOPE` 口径**（门禁主要关心是否允许出现 `CARRIED`）：
- `full`：全量重判（`GWT_CARRIED=0`，判定表不允许出现 `CARRIED`）。
- `diff-only`：同 `full`（仍是全量重判），只是 TECH 审查可主要聚焦 diff（门禁仍按“全量 GWT 覆盖”验真）。
- `incremental`：允许沿用未受影响条目（判定表可出现 `CARRIED`；必须填写 `CARRIED_FROM_COMMIT` 与 `CARRIED_GWTS`；且要求 `REQ_BASELINE_HASH` 未变化）。

### 6.3 输入限制（防止"设计意图同化"）
当启用 `REQ` 模式时：
- ✅ 必须读：`requirements.md`（全量）+ 被审查产出物（代码/页面/配置/命令输出/截图）
- ❌ 不得用：`design.md/plan.md` 的"设计意图"作为通过理由（可以用来定位文件，但不能替代 GWT 的字面判定）

### 6.3.1 对抗性审查（缓解"自己审自己"的结构性盲区）

> 问题：§6.3 的输入隔离只解决了"用设计意图合理化"，但同一模型实现+审查共享认知模型，对自身决策的质疑能力天然不足（Worry 6）。以下机制不新增阶段，嵌入 `@review` 流程内部。

1. **反向假设（REQ-C 强制，按风险分层）**：对每条禁止项 GWT，审查者必须**先列出该禁止项可能泄漏的路径**，再逐条排除并给出证据。按风险等级分层执行：
   - **高风险**（涉及多角色/多入口/动态渲染）：至少列出 2 条泄漏路径并逐条排除。
   - **低风险**（纯静态文案/配置项）：简化为"确认无动态注入路径"即可。
   - 若无法完成分层分析，视为审查不充分（`WARN`）。
2. **人类抽检锚点（强制标注，动态数量）**：每次 `@review` 报告末尾，审查者必须标注 `min(5, max(1, ceil(GWT_TOTAL * 0.1)))` 条（下限 1，上限 5）"建议人类优先抽检"的 GWT（选择标准：证据最薄弱 / 判定最依赖推断 / 涉及多角色交叉的条目）。人类可选择抽检或跳过，但**标注本身是强制的**——缺少此标注视为报告不完整，门禁拦截。
3. **抽检锚点绑定风险说明**：上述抽检锚点中，**至少 1 条必须附带"潜在风险/边界条件"说明**（判定仍为 PASS；建议从抽检锚点中挑 1 条写在备注列）。这比"禁止全 PASS 零备注"更有实际价值——风险说明与抽检绑定，避免模板化填充。

### 6.4 输出落盘（强制）
路径：`docs/<版本号>/review_<stage>.md`

报告必须包含两块内容：
1) **逐条 GWT 判定表（强制包含 GWT-ID）**
2) **机器可读摘要块（门禁入口；计数需验真）**

#### 6.4.1 逐条 GWT 判定表（建议格式）
| GWT-ID | REQ-ID | 判定 | 证据类型 | 证据（可复现） | 备注 |
|---|---|---|---|---|---|
| GWT-REQ-001-01 | REQ-001 | ✅ | RUN_OUTPUT | `npm test ...` 输出片段 / 截图链接 |  |
| GWT-REQ-C001-01 | REQ-C001 | ❌ | UI_PROOF | 截图：...（含时间/环境） |  |

> **判定列取值约定（门禁解析口径）**：
> - `✅`：PASS
> - `❌`：FAIL（阶段推进门禁不允许）
> - `⚠`：WARN（阶段推进门禁不允许；视为需求歧义或证据不足，需先澄清/补证据）
> - `DEFERRED_TO_STAGING`：仅用于 §6.5.1 指定场景（受数量上限约束，且 REQ-C 禁止使用）
> - `CARRIED`：仅允许在 `REVIEW_SCOPE=incremental` 使用（表示沿用上次结论）
>
> **CARRIED 标记约定（增量审查）**：增量审查中沿用上次判定的 GWT 行，判定列填 `CARRIED`（而非 ✅/❌），表示"本次未重新判定，沿用 `CARRIED_FROM_COMMIT` 的结论"。门禁脚本通过识别 `CARRIED` 标记统计 `GWT_CARRIED` 计数。

#### 6.4.2 机器可读摘要块（固定标记，必须在文件末尾）
```text
<!-- REVIEW-SUMMARY-BEGIN -->
REVIEW_STAGE: implementation|testing|design|planning|requirements
REVIEW_SCOPE: diff-only|full|incremental
REVIEW_MODES: TECH,REQ,TRACE
CODE_BASELINE: <status.md _current>
REQ_BASELINE_HASH: <hash(requirements.md 的 GWT 定义行)>  # 仅基于 GWT-REQ...: 行计算（见 §6.7.1）
GWT_TOTAL: <number>
GWT_CHECKED: <number>          # 本次重新判定条目数（full/diff-only 时应等于 GWT_TOTAL）
GWT_CARRIED: <number>          # 增量审查时沿用的条目数（full/diff-only 填 0）
CARRIED_FROM_COMMIT: <hash>    # 沿用来源（full/diff-only 填 N/A）
CARRIED_GWTS: <GWT-ID>,<GWT-ID>,...  # 增量审查时沿用的具体 GWT-ID 列表（full/diff-only 填 N/A；门禁用于验真：与表内 CARRIED 标记一致，且不得包含 REQ-C）
GWT_DEFERRED: <number>         # DEFERRED_TO_STAGING 的条目数（无则填 0）
GWT_FAIL: <number>
GWT_WARN: <number>
SPOT_CHECK_GWTS: <GWT-ID>,<GWT-ID>,...  # 建议人类抽检，数量 = min(5, max(1, ceil(GWT_TOTAL*0.1)))，下限 1 上限 5
REVIEW_RESULT: pass|fail
<!-- REVIEW-SUMMARY-END -->
```

#### 6.4.3 摘要块计数必须可验真（🔴 MUST）
- 门禁不得仅信任摘要块内的 `GWT_*` 自报数字；必须从源文件重新计算并交叉验证（至少覆盖 `TOTAL/CHECKED/CARRIED/DEFERRED/FAIL/WARN`）。
- 最小验真逻辑（不新增文件）：
  - 从 `requirements.md` 提取全量 `GWT-ID` 集合作为“总集”（`GWT_TOTAL`）。
  - 从 `review_<stage>.md` 的“逐条 GWT 判定表”（最后一张表为准）提取 `GWT-ID` 集合作为“判定集”，并按判定列重新计算：
    - `GWT_CARRIED`：判定列为 `CARRIED` 的条目数（仅 incremental 允许）
    - `GWT_CHECKED`：判定集条目数 - `GWT_CARRIED`
    - `GWT_FAIL`/`GWT_WARN`：分别统计 `❌` / `⚠`
    - `GWT_DEFERRED`：统计 `DEFERRED_TO_STAGING`
  - **唯一性验真**：若 `requirements.md` 或判定表中出现重复 `GWT-ID`（重复会被集合运算静默吞并），计数视为不可信 → 拦截。
  - 差集非空（总集 - 判定集）→ 视为漏检 → 拦截阶段推进。
  - 差集非空（判定集 - 总集）→ 视为写错/伪造 ID → 拦截阶段推进。
  - 摘要块计数与脚本计算不一致 → 视为不可信 → 拦截阶段推进。
- 对交付门禁同理：`requirements → test_report` 的 REQ/GWT 覆盖必须由脚本从文档内容计算，不接受人工自填“X/Y”作为通过依据。

### 6.5 不一致/歧义处理（0 WARN 规则的落地）
- 任意 `GWT_WARN > 0`：**禁止推进阶段**。需要先回到 requirements 澄清（把 GWT 写到可判定）或补齐证据。
- 若 Claude/Codex（或不同轮次）对同一 GWT 判定不一致：视为 `WARN`，必须澄清/补证据后再审。

#### 6.5.1 `DEFERRED_TO_STAGING` 判定类型（处理"当前环境无法验证"）
> 问题：有些 GWT 在当前开发环境下无法验证（如性能指标需要生产环境、多角色测试需要完整权限体系）。这类 GWT 既不是 PASS 也不是 FAIL，也不该是 WARN，但当前方案要求 0 WARN，导致无处安放。

- 新增判定类型：`DEFERRED_TO_STAGING`，仅限以下场景使用：
  - 非功能性需求（性能、容量、可用性等）且验证依赖生产/预发布环境
  - 多角色/多租户测试且当前环境缺少完整权限体系
- **使用限制**：
  - 数量上限：不超过总 GWT 的 **10%**（门禁硬拦截）
  - 每条 `DEFERRED_TO_STAGING` 必须标注**验证计划**（在哪个环境、用什么方法、预计什么时间点验证）。为便于门禁验真，建议在判定表**备注列**使用可机读格式：
    - `PLAN_ENV=<env>`（如 `STAGING` / `PROD-like`）
    - `PLAN_METHOD=<method>`（如 `k6` / `JMeter` / `E2E` / 人工验证步骤）
    - `PLAN_ETA=YYYY-MM-DD`
  - 功能性需求和禁止项（REQ-C）**不允许**使用此判定类型
- 摘要块扩展字段：
```text
GWT_DEFERRED: <number>          # DEFERRED_TO_STAGING 的条目数
```
- 门禁校验：`GWT_DEFERRED / GWT_TOTAL <= 0.10`，超出则拦截。
- **脚本层强制（§10.8）**：`validate_review_summary` 必须验证：`GWT_DEFERRED` 计数不超过上限；DEFERRED 的 GWT 中不包含 REQ-C；且每条 DEFERRED 行都包含完整的验证计划（`PLAN_ENV/PLAN_METHOD/PLAN_ETA`）。

#### 6.5.2 GWT 澄清快速路径（防止 review 死循环）
> 问题：如果 review 反复失败（如某条 GWT 写得有歧义，改了代码还是 WARN），当前流程是"回到 requirements 澄清"。但如果 requirements 改了，按 §6.7 所有 review 又作废——形成死循环。

- **快速路径条件**：仅修改 GWT **文本**（澄清措辞/消除歧义），**不改 GWT-ID**，且不新增/删除 GWT 条目。
- **触发效果（门禁口径）**：`REQ_BASELINE_HASH` 变化会使旧摘要块过期，因此仍需生成新的 `review_<stage>.md`（全量 GWT 判定表 + 新摘要块，建议 `REVIEW_SCOPE=full|diff-only`）。
- **触发效果（工作量口径）**：只要求对**受影响的 GWT**重新取证/复测；其余 GWT 可复用上一轮证据引用（备注中标注来源），以降低“全量重审”的实际成本（但判定列不得写 `CARRIED`，因为 baseline 已变化）。
- **限制**：若修改涉及新增/删除 GWT-ID 或改变 REQ-ID 归属，不适用快速路径，必须全量重审。
- **CONSTRAINTS_CONFIRMED 不受影响**：快速路径（仅改 GWT 文本不改 ID）不需要重新确认 `CONSTRAINTS_CONFIRMED`，因为禁止项的 REQ-C ID 和归属未变。

#### 6.5.3 轻量需求补充路径（Implementation 阶段发现遗漏时）
> 问题：Implementation 阶段发现 requirements.md 遗漏了某条需求（如边界条件、隐含约束），当前流程要求"回退到 Requirements 阶段"，但这会中断实现节奏且触发全量重审。

- **适用条件**：
  - 新增需求为**已有 REQ 的细化**（如新增 GWT 到已有 REQ-ID 下），而非全新功能方向
  - 新增 GWT 数量 ≤ 3 条
  - 不涉及 REQ-C（禁止项新增必须走完整 Requirements 确认流程）
- **执行流程**：
  1. 在 `requirements.md` 中新增 GWT（使用递增序号），标注 `<!-- 实现阶段补充 YYYY-MM-DD -->`
  2. 不回退阶段（`_phase` 保持 `Implementation`）
  3. 下次 `@review` 时，新增的 GWT 必须被判定（不允许跳过）
  4. `REQ_BASELINE_HASH` 会因 GWT 行变化而更新，旧摘要块过期 → 需要生成新的 `review_<stage>.md`（全量判定表 + 新摘要块）；工作量可按 §6.5.2 的“仅对受影响条目重新取证/复测、其余复用证据引用”来降本
- **限制**：若新增需求改变了功能方向或涉及禁止项，必须走完整的 Requirements 阶段或 CR 流程。

### 6.6 不允许降级（硬规则）
- 不允许任何 `fast/skip/partial` 口令绕过 `REQ(all)` 或 GWT 粒度判定。
- 不允许用 `Accept/Defer` 绕过任何 `FAIL/WARN`（需求不满足/不可判定必须修复或澄清）。
- **与 §6.8 的边界澄清**：本条所禁止的是**跳过 GWT 判定本身**（即某条 GWT 不做判定就放行），不禁止 §6.8 中基于影响分析的增量审查（carry-over 仍需判定记录）和分层证据（降低证据形式要求，但仍需给出判定）。简言之："每条 GWT 都必须有判定结论"是不可降级的；"判定所需的证据形式"和"判定是否需要重新执行"可以按风险分层。

### 6.7 基线失效（requirements / code 任意变更都会作废审查）
- `requirements.md` 改动后：`REQ_BASELINE_HASH` 必变 → 旧审查自动作废，必须重审。
- 代码版本变化（摘要块 `CODE_BASELINE` 与 status.md `_current` 不一致）同理：必须重审，避免"旧审查推进新代码"。

#### 6.7.1 区分实质性变更与格式性变更（降低"改错别字全量重审"的成本）
> 问题：`REQ_BASELINE_HASH` 基于 `git hash-object`，改一个错别字也会导致 hash 变化 → 所有 review 作废 → 必须全量重审。实际效果是鼓励"冻结后不改"，而不是"持续改进"。

**推荐方案**：hash 只计算 GWT-ID 行的内容（忽略说明文字的改动）：
```bash
grep -oE 'GWT-REQ-C?[0-9]+-[0-9]+:.*' requirements.md | LC_ALL=C sort | git hash-object --stdin
```
- 门禁校验此"GWT 内容 hash"而非文件整体 hash。
- 说明文字（描述、背景、格式）的修改不触发全量重审。
- GWT 文本的实质性修改（改判定条件、改预期结果）仍会触发重审。

**备选方案**：在 `requirements.md` 中维护手动递增字段 `REQ_CONTENT_VERSION: N`，只有实质性变更才递增，门禁校验此字段。

> 注意：采用 GWT 行 hash 方案时，摘要块字段名建议改为 `REQ_BASELINE_HASH`（保持兼容），但计算方式在门禁脚本中更新。

### 6.8 成本与上下文控制（防止"严谨"变成"不可执行"）

> 问题：Worry 7 明确指出——机制过重会导致 AI 敷衍、人类放弃执行、上下文爆炸。本方案新增了大量门禁与证据要求，如果不配套成本控制，最终会"形式正确但内容空洞"。
>
> 原则：**审查深度与风险成正比，而非一刀切全量**。

#### 6.8.1 分层证据要求（降低低风险 GWT 的证据成本）

不同类型的 GWT 对证据的最低要求不同：

| GWT 类型 | 最低证据 | 说明 |
|----------|---------|------|
| REQ-C（禁止项） | `UI_PROOF` 或 `RUN_OUTPUT` | 不可降级（见 §8.2），必须运行时验证 |
| 正向功能（结构性/静态可判定） | `CODE_REF` | 如字段顺序、配置默认值、类型定义 |
| 正向功能（行为性/运行时） | `RUN_OUTPUT` | 如接口返回值、计算逻辑、状态流转 |

> 这不是"放水"——而是避免对"字段名是否正确"这种一眼可判的 GWT 也要求截图，导致审查者把精力浪费在低风险项上。

#### 6.8.2 增量审查（降低"改一行重审全量"的成本）

代码变更后，如果变更范围有限，审查者可使用增量模式：

- 摘要块标注 `REVIEW_SCOPE: incremental`。
- 必须输出**影响分析**：变更文件 → 关联 REQ → 关联 GWT，明确列出本次重新判定的 GWT 子集。
- 未受影响的 GWT 可沿用上次判定，但摘要块必须注明 `CARRIED_FROM_COMMIT: <上次审查 commit>`。
- 门禁验真：`GWT_CHECKED`（本次新判定）+ `GWT_CARRIED`（沿用）= `GWT_TOTAL`，否则拦截。
- **REQ-C 类 GWT 的 carry-over 规则（硬规则）**：
  - 一律禁止 carry-over（禁止项必须每次重新验证）。
  - 表内判定列不得为 `CARRIED`；摘要块 `CARRIED_GWTS` 不得包含任何 `GWT-REQ-C...`。
- **半自动化影响分析建议**：在 `design.md` 的需求-设计追溯矩阵中增加"关联文件"列（如 `REQ-001 → OrderListPage.tsx, OrderListPage.test.tsx`），使增量审查的影响分析可基于文件级交集判定，而非纯人工推断。
- **脚本层强制（§10.8）**：门禁脚本会对 `CARRIED`/`CARRIED_GWTS` 做一致性验真，并硬拒绝任何 REQ-C carry-over。

增量审查的摘要块扩展字段：
```text
GWT_CARRIED: <number>
CARRIED_FROM_COMMIT: <commit-hash>
```

#### 6.8.3 上下文预算

- `@review` 时，审查者读取 `requirements.md` 全文（通常 < 200 行），但代码**只读与当前 GWT 相关的文件**（不要求读全量代码库）。
- 如果 `requirements.md` 超过 300 行，优先按模块做**章节化/锚点化**以保持单文件（便于门禁提取与验真）；如确需拆分为多个 requirements 文件，必须同步升级门禁/脚本的 REQ/GWT 提取范围，否则禁止拆分。
- 逐条 GWT 判定表中，证据列只写**定位信息**（文件:行号、命令、截图链接），不内联大段代码或输出——需要时读者自行查看。

#### 6.8.4 小项目快速通道（GWT_TOTAL ≤ 15 时简化）
> 问题：对于小型变更或小项目（GWT 总数很少），全套对抗性审查 + 增量模式 + 分层证据的开销可能超过项目本身的复杂度。

当 `GWT_TOTAL <= 15` 时，允许以下简化：
- **对抗性审查简化**：REQ-C 的反向假设可合并为一段总结（而非逐条列出泄漏路径），但仍需给出"已排除"的结论。
- **SPOT_CHECK_GWTS 下限**：按 `min(5, max(1, ceil(GWT_TOTAL * 0.1)))` 计算，小项目可能只需标注 1-2 条。
- **跳过增量模式**：`GWT_TOTAL <= 15` 时，建议直接使用 `scope=full`（全量审查成本可控），避免增量模式的 carry-over 管理开销。
- **不可简化项**：GWT 粒度全覆盖、0 FAIL/0 WARN、REQ-C 证据要求（UI_PROOF/RUN_OUTPUT）仍为硬要求，不因项目规模降级。

## 7. 门禁策略（阶段推进硬拦截）

### 7.0 Requirements 阶段收口（硬拦截：禁止项/不做项确认清单）

> 目标：解决人类最担心的那类遗漏——“讨论时说过的不要/不做”，没有固化进 `requirements.md`，后续再强的门禁也拦不住。
>
> 约束：不新增文件类型；仅使用既有 `requirements.md` / `review_requirements.md`。

允许将 `_phase` 从 `Requirements` 推进到 `Design`（或将 `requirements.md` 标记为可冻结/可进入下一阶段）前，必须满足：
- `review_requirements.md` 存在（门禁入口文件）
- `review_requirements.md` 中包含**“禁止项/不做项确认清单”**章节，并满足：
  - 来源覆盖：对话中出现的"不要/不做/禁止/不允许/不显示/不出现/不需要"类表述 + `proposal.md` 的 Non-goals（如有）
  - **提取可信度保障**：清单中每条禁止项必须标注来源（优先使用文档引用如 `proposal.md §X`、`requirements.md REQ-C001`；对话引用如"对话第 N 轮"仅作为补充——对话轮次不稳定，文档引用更可追溯），便于人类交叉核对是否有遗漏。AI 提取不保证完整，人类确认环节的核心职责就是**查漏**——确认"还有没有说过但没列进来的"。
  - 每条均被**明确归类**为二选一：
    - A) 已固化为 `REQ-Cxxx`（并且在 `requirements.md` 中存在对应条目 + `GWT-ID`）
    - B) 明确写入 Non-goals（说明原因与边界；不得用“先不做/以后再说”模糊带过）
  - 清单中不得出现 `TBD/待确认/unknown/...` 占位项
- **机器可读清单块（🔴 MUST，用于门禁验真）**：为避免只靠 `CONSTRAINTS_CONFIRMED: yes` 造成“门禁太弱/可被绕过”，要求在该章节内追加以下块（门禁脚本将解析并做交叉校验）：
```text
<!-- CONSTRAINTS-CHECKLIST-BEGIN -->
| ITEM | CLASS | TARGET | SOURCE |
|---|---|---|---|
| C-001 | A | REQ-C001 | requirements.md REQ-C001（来源：proposal.md §Non-goals / 对话补充） |
| C-002 | B | Non-goals | proposal.md §Non-goals（原因：不在本期范围） |
| C-003 | B | NONE | proposal.md §Non-goals（确认：本期无新增“不做项/禁止项”） |
<!-- CONSTRAINTS-CHECKLIST-END -->
```
  - `ITEM`：条目唯一 ID（本清单内不可重复）。
  - `CLASS`：`A` 或 `B`。
  - `TARGET`：
    - `A`：必须为 `REQ-Cxxx`，且该 `REQ-Cxxx` 必须在 `requirements.md` 中定义，且必须有至少 1 条 `GWT-REQ-Cxxx-yy`（禁止项必须可验收）。
    - `B`：必须为 `Non-goals`/`NONE`（表示该条明确写入 Non-goals，或确认无此类项）。
  - `SOURCE`：必须包含可追溯的文档引用；`CLASS=B` 必须引用 `proposal.md`（Non-goals 必须可追溯）。
  - **门禁验真口径**：脚本将验证“所有 `requirements.md` 中出现的 `REQ-Cxxx` 都在清单中以 `CLASS=A` 出现且不重复”；并验证清单无占位符。
- 人类确认标记为已确认（建议追加机器可读块，便于门禁脚本判定）：
```text
<!-- CONSTRAINTS-CONFIRMATION-BEGIN -->
CONSTRAINTS_CONFIRMED: yes
CONFIRMED_BY: <human>
CONFIRMED_AT: YYYY-MM-DD
<!-- CONSTRAINTS-CONFIRMATION-END -->
```

### 7.1 Implementation → Testing（硬拦截）
推进 `_phase: Testing` 前必须满足：
- `review_implementation.md` 存在
- 摘要块满足：`GWT_FAIL=0`、`GWT_WARN=0`、`REVIEW_RESULT=pass`
- **摘要块计数验真通过（🔴 MUST）**：按 6.4.3 从源文件重新计算并交叉验证，且差集为空（防止“自报数字/漏判”）
- 摘要块的 `REQ_BASELINE_HASH` 与当前 `requirements.md` 一致
- 摘要块的 `CODE_BASELINE` 与 status.md 的 `_current` 值一致（完全一致）

### 7.2 Testing → Deployment（硬拦截）
推进 `_phase: Deployment` 前必须满足：
- `review_testing.md` 存在且摘要块满足同上（Testing 的默认模式为 `REQ(all)+TRACE`）
- **摘要块计数验真通过（🔴 MUST）**：按 6.4.3 从源文件重新计算并交叉验证，且差集为空
- `test_report.md` 存在，且 `requirements → test_report` 覆盖完整（至少 REQ 粒度 100%，建议最终以 GWT 粒度核对）

### 7.3 交付关口（补强 W16）
在现有“证据存在性”基础上，将“覆盖完整性（REQ/GWT）”纳入硬拦截：
- 覆盖不全 → 拦截
- 结论“不通过” → 拦截（覆盖矩阵/判定表结果列出现 `❌/⚠` 或空结果；或 `整体结论=不通过`）
- **覆盖计算必须可验真（🔴 MUST）**：由脚本从 `requirements.md` 提取 REQ/GWT 集合，与 `test_report.md` 的覆盖矩阵/判定表做差集；差集非空或统计不一致一律拦截（不接受人工自填“X/Y”作为通过依据）。

### 7.4 门禁执行面：CI 作为最终裁决（推荐）

> 背景：本地 hooks 可被 `--no-verify` 或“未安装 hooks”绕过，因此不能作为团队协作下“最终稳定有保证”的控制面。

- **本地 hooks**：开发者预检/提速（越早失败越省成本）。
- **CI**：唯一放行门禁（保护分支要求 Required checks 全绿才允许 merge）。
- **口径统一（避免双口径）**：
  - pre-commit 语义：校验 **git index（staged）** 的版本（即将提交的内容）。
  - CI 语义：校验 **checkout 的 commit**（工作树内容）。
  - 但两者应复用同一套“提取/验真/差集/计数”逻辑，避免规则分叉。

## 8. 证据规则（满足“最终用户看不到即可”）

### 8.1 证据类型枚举（建议）
- `CODE_REF`：`文件:行号`（适用于静态契约、字段定义、配置默认值等）
- `RUN_OUTPUT`：命令 + 关键输出（适用于接口契约、单测/集成测、性能指标）
- `UI_PROOF`：截图链接 / DOM 文本断言输出 / E2E 输出（适用于 UI 展示/文案/卡片/权限差异）

### 8.2 UI 禁止项的硬要求
- 你对“不要出现某卡片/某字”的口径是：**最终用户看不到即可**。
- 因此 UI 禁止项（`REQ-C` 类 GWT）判 PASS 的最低证据应为：
  - `UI_PROOF`（截图/断言输出/可复现实验）
  - 覆盖默认范围：所有角色 + 所有入口 + 页面关键状态（空/有数据/异常/加载等）
- 仅提供 `CODE_REF` 不足以判 PASS（否则会出现“代码里看不到，但运行时某分支会露出”的漏检）。

## 9. 需求变更级联（防止“审查通过后又改需求”）

建议将 `REQ_BASELINE_HASH` 写入：
- `review_<stage>.md`（强制）
- `plan.md`、`test_report.md`（建议）：便于检测“需求基线已过时”

一旦发现 hash 不一致：
- 必须同步更新受影响文档/用例
- 必须重新 `@review`（生成新摘要块）

## 10. 落地实施规格（不新增阶段，改模板/规则/门禁）

> ⚠️ 教训：上一轮落地（Codex）只完成了基础设施层（hooks 骨架、文件存在性门禁），核心内容层（GWT-ID、REQ-C、审查协议、覆盖验真）全部缺失。根因：本节过于抽象，实施者不知道"具体往文件里加什么"。
>
> 本次重写为**文件级实施规格**：每个变更点给出"改哪个文件→改哪个位置→加什么内容"，并在 §11 提供可机器验证的落地验收命令。


### 10.1 `templates/requirements_template.md`（E1 + E2）

#### 变更 A：GWT 格式升级（E1）
**位置**：`§3.2 功能性需求明细` 中的验收标准示例
**动作**：将"必须可测试"改为"必须可判定"，加 `GWT-ID` 前缀

替换前：
```markdown
**验收标准（GWT，必须可测试）**：
- [ ] Given 用户已登录，When 访问首页，Then 显示用户信息
- [ ] Given 用户未登录，When 访问受保护页面，Then 跳转至登录页
```
替换后：
```markdown
**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-001-01: Given 用户已登录，When 访问首页，Then 显示用户信息
- [ ] GWT-REQ-001-02: Given 用户未登录，When 访问受保护页面，Then 跳转至登录页

> GWT-ID 格式：`GWT-<REQ-ID>-<序号>`，如 `GWT-REQ-001-01`、`GWT-REQ-C001-01`。
> ID 一旦分配不得修改（作为审查/测试外键）；允许改 GWT 文本；新增用递增序号。
> 可判定要求：第三方仅凭 GWT 文本即可判定 PASS/FAIL，禁止"简洁""优化体验"等模糊表述。
```

#### 变更 B：新增 REQ-C 章节（E2）
**位置**：在 `## 4. 非功能需求` 之后、`## 5. 权限与合规` 之前，插入新章节
**动作**：新增以下内容

```markdown
## 4A. 约束与禁止项（Constraints & Prohibitions）

> 所有"不要/不许/不得/不显示/不出现"的要求必须落为 REQ-Cxxx，与功能需求同等地位。
> 默认适用范围：**所有角色 + 所有入口 + 页面所有状态**（除非在"适用范围"中明确限定）。
> 证据要求：UI 禁止项必须提供运行证据（UI_PROOF / RUN_OUTPUT），不接受仅凭代码推断（CODE_REF）。

### 4A.1 禁止项列表
| REQ-ID | 禁止项名称 | 适用范围 | 来源 |
|--------|-----------|---------|------|
| REQ-C001 | | 全局（所有角色/状态） | proposal §X / 对话补充 |

### 4A.2 禁止项明细
#### REQ-C001：[禁止项名称]
**适用范围**：[页面/模块]（所有角色，所有状态）
**来源**：[proposal.md §X / 人类明确要求 / 对话补充]
**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-C001-01: Given 任意角色登录，When [触发条件]，Then [不出现/不包含/不显示 具体内容]
- [ ] GWT-REQ-C001-02: Given 任意角色登录，When [触发条件]，Then [不出现/不包含/不显示 具体内容]
```

#### 变更 C：非功能需求 GWT-ID 同步
**位置**：`§4.2 非功能需求明细` 的验收方法
**动作**：同样加 `GWT-ID` 前缀（格式与功能需求一致）


### 10.2 `templates/review_template.md`（E4 + E10 + E11）

> 关键：新增的"需求符合性审查协议"是 **补充** 现有 RVW-based 审查，不是替换。
> 现有的 P0/P1/P2 严重度体系用于技术审查（TECH 模式）；
> 新增的 GWT 判定体系用于需求符合性审查（REQ 模式）。
> 两者在 Implementation/Testing 阶段同时执行。

**位置**：在现有 `## 阶段审查清单` 之前，插入以下完整章节

```markdown
## 需求符合性审查协议（@review REQ 模式）

> 本协议在 Implementation→Testing、Testing→Deployment 推进时**强制执行**。
> 与技术审查（TECH 模式，即上方 RVW-based 审查）并行，不互相替代。

### 触发与默认模式
- Implementation 阶段：`TECH + REQ(all)`，scope=diff-only
- Testing 阶段：`REQ(all) + TRACE`，scope=full
- 审查者无需手工指定模式，按阶段自动确定。

### 输入隔离（🔴 MUST）
- ✅ 必须读：`requirements.md`（全量）+ 被审查产出物
- ❌ 不得用：`design.md/plan.md` 的"设计意图"作为 GWT 通过理由

### 逐条 GWT 判定表（强制格式）
| GWT-ID | REQ-ID | 判定 | 证据类型 | 证据（可复现） | 备注 |
|--------|--------|------|---------|--------------|------|
| GWT-REQ-001-01 | REQ-001 | ✅ | CODE_REF | `src/xx.ts:42` | |
| GWT-REQ-C001-01 | REQ-C001 | ✅ | UI_PROOF | 截图链接/E2E输出 | |

证据类型与最低要求：
- REQ-C（禁止项）：必须 `UI_PROOF` 或 `RUN_OUTPUT`（不可降级）
- 正向功能（静态可判定）：`CODE_REF` 即可
- 正向功能（行为性）：`RUN_OUTPUT`
```

继续插入（紧接上方）：

```markdown
### 对抗性审查（REQ-C 强制，§6.3.1，按风险分层）
对每条禁止项 GWT，按风险等级执行：
- **高风险**（涉及多角色/多入口/动态渲染）：列出至少 2 条泄漏路径，逐条排除并给出证据
- **低风险**（纯静态文案/配置项）：确认无动态注入路径即可
- 无法完成分层分析 → WARN

### 人类抽检锚点（强制）
报告末尾必须标注 `min(5, max(1, ceil(GWT_TOTAL * 0.1)))` 条（下限 1，上限 5）"建议人类优先抽检"的 GWT：
- 选择标准：证据最薄弱 / 判定最依赖推断 / 涉及多角色交叉
- 缺少此标注 → 报告不完整 → 门禁拦截

### 禁止"全 PASS 零备注"
若最终要 `REVIEW_RESULT=pass`（所有 GWT 均 PASS），备注列必须至少补充 1 条"潜在风险/边界条件"说明（判定仍为 PASS）。

### 增量审查（可选，变更范围有限时）
- 摘要块标注 `REVIEW_SCOPE: incremental`
- 输出影响分析：变更文件 → 关联 REQ → 关联 GWT
- 未受影响的 GWT 沿用上次判定，摘要块填写 `CARRIED_FROM_COMMIT: <commit>`
- 限制：REQ-C 类 GWT 不允许 carry-over

### 机器可读摘要块（🔴 MUST，文件末尾）
```text
<!-- REVIEW-SUMMARY-BEGIN -->
REVIEW_STAGE: implementation|testing|design|planning|requirements
REVIEW_SCOPE: diff-only|full|incremental
REVIEW_MODES: TECH,REQ,TRACE
CODE_BASELINE: <status.md _current>
REQ_BASELINE_HASH: <hash(requirements.md 的 GWT 定义行)>  # 仅基于 GWT-REQ...: 行计算（见 §6.7.1）
GWT_TOTAL: <number>
GWT_CHECKED: <number>
GWT_CARRIED: <number>
CARRIED_FROM_COMMIT: <hash>
CARRIED_GWTS: <GWT-ID>,<GWT-ID>,...
GWT_DEFERRED: <number>
GWT_FAIL: <number>
GWT_WARN: <number>
SPOT_CHECK_GWTS: <GWT-ID>,<GWT-ID>,...
REVIEW_RESULT: pass|fail
<!-- REVIEW-SUMMARY-END -->
```

### 不允许降级
- 不允许 fast/skip/partial 绕过 REQ(all)
- 不允许 Accept/Defer 绕过任何 FAIL/WARN
```


### 10.3 `templates/plan_template.md`（E3）

#### 变更 A：禁止项引用索引
**位置**：在 `## 任务概览` 之前插入
```markdown
## 禁止项引用索引（来源：requirements.md REQ-C 章节）
> 仅列 ID + 一句话摘要，不复制 GWT 全文。内容以 requirements.md 为准。
> 所有任务实现时必须确保不违反以下禁止项。

| REQ-C ID | 一句话摘要 |
|----------|-----------|
| REQ-C001 | [从 requirements.md 摘录] |
```

#### 变更 B：反向覆盖检查（反向 R6）
**位置**：在现有 `### 引用自检（🔴 MUST，R6）` 之后追加

````markdown
### 反向覆盖检查（🔴 MUST，反向 R6）
> 确保 requirements.md 中每条 REQ 都被至少一个任务覆盖（避免一开始就漏需求）。

**验证命令**：
```bash
VERSION="<版本号>"

# 提取 requirements.md 中定义的所有 REQ（功能 + 非功能 + 禁止项）
rg "^#### REQ-" docs/${VERSION}/requirements.md | sed 's/^#### //;s/[：:].*//' | LC_ALL=C sort -u > /tmp/req_all_${VERSION}.txt

# 提取 plan.md 中引用的所有 REQ
rg -o "REQ-C?[0-9]+" docs/${VERSION}/plan.md | LC_ALL=C sort -u > /tmp/plan_refs_${VERSION}.txt

# 反向差集：requirements 定义了但 plan 未覆盖的 REQ
LC_ALL=C comm -23 /tmp/req_all_${VERSION}.txt /tmp/plan_refs_${VERSION}.txt
```
**检查项**：差集为空（每条 REQ 都被至少一个任务引用）。差集非空时必须补充任务或确认为 Non-goals。
````


### 10.4 `templates/test_report_template.md`（E5 配套）

#### 变更：需求覆盖矩阵升级为 GWT 粒度
**位置**：替换现有 `## 需求覆盖矩阵（追溯）`
```markdown
## 需求覆盖矩阵（GWT 粒度追溯）

> 每条 GWT-ID 必须有对应判定，不允许遗漏。门禁会从此表提取覆盖集合与 requirements.md 做差集。

| GWT-ID | REQ-ID | 需求摘要 | 对应测试(TEST-ID) | 证据类型 | 证据 | 结果 |
|--------|--------|---------|-------------------|---------|------|------|
| GWT-REQ-001-01 | REQ-001 | 用户登录 | TEST-001 | RUN_OUTPUT | pytest输出 | ✅ |
| GWT-REQ-C001-01 | REQ-C001 | 禁止描述卡片 | TEST-010 | UI_PROOF | 截图链接 | ✅ |
```

### 10.5 `phases/05-implementation.md`（E6）

#### 变更 A：收敛条件去掉 accept/defer
**位置**：`### AI 自动审查收敛` 章节
**动作**：将
```
- [ ] P0(open)=0, P1(open)=0（允许存在 P1 accept/defer）
```
替换为：
```
- [ ] P0(open)=0, P1(open)=0（不允许 accept/defer，见 enhance_temp §6.6）
- [ ] 需求符合性审查通过：review_implementation.md 包含 GWT 判定表 + 摘要块，且 GWT_FAIL=0, GWT_WARN=0, REVIEW_RESULT=pass
```

#### 变更 B：出口门禁增加摘要块验证
**位置**：`### 阶段出口门禁` 章节，在现有检查项后追加
```markdown
- [ ] `review_implementation.md` 包含机器可读摘要块（`REVIEW-SUMMARY-BEGIN/END`）
- [ ] 摘要块：`GWT_FAIL=0`、`GWT_WARN=0`、`REVIEW_RESULT=pass`
- [ ] 摘要块：`REQ_BASELINE_HASH` 与当前 `requirements.md` 的“GWT 定义行 hash”一致（见 §6.7.1）
- [ ] 摘要块：`SPOT_CHECK_GWTS` 非空（人类抽检锚点）
```


### 10.6 `phases/06-testing.md`（E6）

与 10.5 同理：
- 收敛条件去掉 accept/defer
- 出口门禁增加 `review_testing.md` 摘要块验证
- 额外：出口门禁增加 `test_report.md` GWT 覆盖完整性检查（requirements 中全量 GWT-ID 必须在 test_report 覆盖矩阵中出现）

### 10.7 `phases/04-planning.md`（E3）

**位置**：在现有 `### 引用存在性检查（R6）` 之后追加反向 R6 检查
**内容**：与 10.3 变更 B 相同的验证命令和检查项

### 10.8 `scripts/git-hooks/pre-commit`（E5 + E6）

#### 优化建议（降低日常 commit 的摩擦）
> 问题：`validate_review_summary` 约 120 行 bash 做 markdown 解析与集合运算，每次 commit 都跑（包括与审查无关的纯代码 commit）。bash 对 markdown 格式敏感（空行/缩进变化可能导致误判），调试困难。

- **条件触发**：只在阶段推进 commit（检测到 `_phase` 变更）时才触发完整的 `validate_review_summary`，普通 commit 跳过。
- **`--dry-run` 模式**：建议增加 `REVIEW_DRY_RUN=1 git commit ...` 环境变量，让开发者提前自检摘要块是否合规，而不必真正 commit。
- **健壮性改进方向**：长期考虑用 Python/Node 脚本替代 bash 做 markdown 解析（`grep -oE` + `comm -23` 对格式变化脆弱），当前 bash 实现作为 MVP 可接受。

#### 变更 A：Git-Hook 7 增加摘要块验证
**位置**：`case "$OLD_PHASE" in` 的 `Implementation)` 和 `Testing)` 分支
**动作**：在检查文件存在性之后，增加摘要块内容验证

```bash
# Implementation → Testing 时额外检查
# 读取 git index（staged）内容（pre-commit 语义：校验即将提交的版本，而非工作树）
staged_content() {
  git show ":$1" 2>/dev/null || { echo "❌ $1 不在 git index（请先 git add）"; return 1; }
}

validate_review_summary() {
  local REVIEW_FILE="$1"
  local REQ_FILE="$2"
  local STATUS_FILE="$3"
  local REVIEW_CONTENT REQ_CONTENT STATUS_CONTENT
  REVIEW_CONTENT=$(staged_content "$REVIEW_FILE") || return 1
  REQ_CONTENT=$(staged_content "$REQ_FILE") || return 1
  STATUS_CONTENT=$(staged_content "$STATUS_FILE") || return 1

  # 提取摘要块（从暂存区内容）
  local SUMMARY=$(echo "$REVIEW_CONTENT" | sed -n '/REVIEW-SUMMARY-BEGIN/,/REVIEW-SUMMARY-END/p')
  [ -z "$SUMMARY" ] && { echo "❌ $REVIEW_FILE 缺少机器可读摘要块"; return 1; }

  # 检查 REVIEW_RESULT
  local RESULT=$(echo "$SUMMARY" | grep '^REVIEW_RESULT:' | awk '{print $2}')
  [ "$RESULT" != "pass" ] && { echo "❌ $REVIEW_FILE REVIEW_RESULT=$RESULT (期望 pass)"; return 1; }

  # 检查 REQ_BASELINE_HASH（使用 GWT 行 hash，见 §6.7.1）
  local CURRENT_HASH=$(echo "$REQ_CONTENT" | grep -oE 'GWT-REQ-C?[0-9]+-[0-9]+:.*' | LC_ALL=C sort | git hash-object --stdin)
  local SAVED_HASH=$(echo "$SUMMARY" | grep '^REQ_BASELINE_HASH:' | awk '{print $2}')
  [ "$CURRENT_HASH" != "$SAVED_HASH" ] && {
    echo "❌ REQ_BASELINE_HASH 不一致（requirements.md 已变更，审查结论已过期）"
    return 1
  }

  # 检查 CODE_BASELINE（与 status.md 的 _current 值一致）
  local CODE_BASELINE=$(echo "$SUMMARY" | grep '^CODE_BASELINE:' | awk '{print $2}')
  local CURRENT=$(echo "$STATUS_CONTENT" | grep '^_current:' | awk '{print $2}')
  [ -z "$CODE_BASELINE" ] && { echo "❌ $REVIEW_FILE 缺少 CODE_BASELINE"; return 1; }
  [ -z "$CURRENT" ] && { echo "❌ $STATUS_FILE 缺少 _current，无法校验 CODE_BASELINE"; return 1; }

  [ "$CURRENT" = "$CODE_BASELINE" ] || {
    echo "❌ $REVIEW_FILE CODE_BASELINE 与 $STATUS_FILE _current 不一致："
    echo "   - _current: ${CURRENT}"
    echo "   - CODE_BASELINE: ${CODE_BASELINE}"
    return 1
  }
  local CODE_COMMIT=$(git rev-parse --verify "${CODE_BASELINE}^{commit}" 2>/dev/null || true)
  [ -n "$CODE_COMMIT" ] || { echo "❌ $REVIEW_FILE CODE_BASELINE 非法（无法解析为 commit）：$CODE_BASELINE"; return 1; }

  # 检查 SPOT_CHECK_GWTS 非空
  local SPOT=$(echo "$SUMMARY" | grep '^SPOT_CHECK_GWTS:' | sed 's/^SPOT_CHECK_GWTS:[[:space:]]*//')
  [ -z "$SPOT" ] && { echo "❌ SPOT_CHECK_GWTS 为空（缺少人类抽检锚点）"; return 1; }

  # 检查 REVIEW_MODES 包含 REQ（防止只做 TECH 审查就通过）
  local MODES=$(echo "$SUMMARY" | grep '^REVIEW_MODES:' | awk '{print $2}')
  echo "$MODES" | grep -q 'REQ' || { echo "❌ REVIEW_MODES=$MODES（缺少 REQ 模式）"; return 1; }

  # ===== §6.4.3 核心验真：从源文件交叉验证 GWT 计数 =====
  # 从 requirements.md 提取全量 GWT-ID（总集）
  local REQ_GWTS_SORTED=$(echo "$REQ_CONTENT" | grep -oE 'GWT-REQ-C?[0-9]+-[0-9]+' | LC_ALL=C sort)
  local REQ_GWTS=$(echo "$REQ_GWTS_SORTED" | uniq)
  local DUP_REQ_GWTS=$(echo "$REQ_GWTS_SORTED" | uniq -d || true)
  if [ -n "$DUP_REQ_GWTS" ]; then
    echo "❌ requirements.md 存在重复 GWT-ID（重复会导致计数不可信）："
    echo "$DUP_REQ_GWTS" | head -10 | sed 's/^/  - /'
    return 1
  fi
  local SCRIPT_TOTAL=$(echo "$REQ_GWTS" | grep -c . 2>/dev/null || echo 0)

  # 从 review 的最后一张 GWT 判定表提取覆盖集合（总判定集 = CHECKED + CARRIED）
  local TABLE_ROWS=$(echo "$REVIEW_CONTENT" | last_gwt_table_rows)
  local TABLE_GWTS_SORTED=$(echo "$TABLE_ROWS" | grep -oE 'GWT-REQ-C?[0-9]+-[0-9]+' | LC_ALL=C sort)
  local TABLE_GWTS=$(echo "$TABLE_GWTS_SORTED" | uniq)
  local DUP_TABLE_GWTS=$(echo "$TABLE_GWTS_SORTED" | uniq -d || true)
  if [ -n "$DUP_TABLE_GWTS" ]; then
    echo "❌ $REVIEW_FILE 判定表存在重复 GWT-ID（计数将不可信）："
    echo "$DUP_TABLE_GWTS" | head -10 | sed 's/^/  - /'
    return 1
  fi

  # 差集：总集 - 判定集（漏检的 GWT）
  local MISSING_GWTS=$(comm -23 <(echo "$REQ_GWTS") <(echo "$TABLE_GWTS"))
  if [ -n "$MISSING_GWTS" ]; then
    local MISSING_COUNT=$(echo "$MISSING_GWTS" | grep -c .)
    echo "❌ GWT 覆盖不完整：${MISSING_COUNT} 条 GWT 未在审查判定表中出现"
    echo "$MISSING_GWTS" | head -10 | sed 's/^/  - /'
    return 1
  fi

  # 反向差集：判定集 - 总集（写错/伪造的 GWT）
  local EXTRA_GWTS=$(comm -23 <(echo "$TABLE_GWTS") <(echo "$REQ_GWTS"))
  if [ -n "$EXTRA_GWTS" ]; then
    local EXTRA_COUNT=$(echo "$EXTRA_GWTS" | grep -c .)
    echo "❌ GWT-ID 不合法：${EXTRA_COUNT} 条判定表中的 GWT 不存在于 requirements.md"
    echo "$EXTRA_GWTS" | head -10 | sed 's/^/  - /'
    return 1
  fi

  # 从判定表重算 FAIL/WARN/DEFERRED/CARRIED（不信任摘要自报数字）
  local TABLE_CARRIED_GWTS=$(echo "$TABLE_ROWS" | awk -F'|' '
    function trim(s){ gsub(/^[ \t]+|[ \t]+$/, "", s); return s }
    $0 ~ /GWT-REQ-/ { gwt=trim($2); verdict=trim($4); if(index(verdict,"CARRIED")>0) print gwt }
  ' | LC_ALL=C sort -u)
  local TABLE_CARRIED=$(echo "$TABLE_CARRIED_GWTS" | grep -c . || echo 0)
  local TABLE_DEFERRED=$(echo "$TABLE_ROWS" | awk -F'|' '
    function trim(s){ gsub(/^[ \t]+|[ \t]+$/, "", s); return s }
    $0 ~ /GWT-REQ-/ { verdict=trim($4); if(index(verdict,"DEFERRED_TO_STAGING")>0) c++ }
    END{print c+0}
  ')
  local TABLE_FAIL=$(echo "$TABLE_ROWS" | awk -F'|' '
    function trim(s){ gsub(/^[ \t]+|[ \t]+$/, "", s); return s }
    $0 ~ /GWT-REQ-/ { verdict=trim($4); if(verdict ~ /❌/) c++ }
    END{print c+0}
  ')
  local TABLE_WARN=$(echo "$TABLE_ROWS" | awk -F'|' '
    function trim(s){ gsub(/^[ \t]+|[ \t]+$/, "", s); return s }
    $0 ~ /GWT-REQ-/ { verdict=trim($4); if(verdict ~ /⚠/) c++ }
    END{print c+0}
  ')
  local TABLE_TOTAL=$(echo "$TABLE_GWTS" | grep -c . || echo 0)
  local TABLE_CHECKED=$((TABLE_TOTAL - TABLE_CARRIED))

  # 摘要块计数与脚本计算交叉验证
  local BLOCK_TOTAL=$(echo "$SUMMARY" | grep '^GWT_TOTAL:' | awk '{print $2}')
  local BLOCK_CHECKED=$(echo "$SUMMARY" | grep '^GWT_CHECKED:' | awk '{print $2}')
  local BLOCK_CARRIED=$(echo "$SUMMARY" | grep '^GWT_CARRIED:' | awk '{print $2}')
  local BLOCK_DEFERRED=$(echo "$SUMMARY" | grep '^GWT_DEFERRED:' | awk '{print $2}')
  local BLOCK_FAIL=$(echo "$SUMMARY" | grep '^GWT_FAIL:' | awk '{print $2}')
  local BLOCK_WARN=$(echo "$SUMMARY" | grep '^GWT_WARN:' | awk '{print $2}')
  BLOCK_CARRIED=${BLOCK_CARRIED:-0}
  BLOCK_DEFERRED=${BLOCK_DEFERRED:-0}
  BLOCK_FAIL=${BLOCK_FAIL:-0}
  BLOCK_WARN=${BLOCK_WARN:-0}

  if [ "$BLOCK_TOTAL" != "$SCRIPT_TOTAL" ]; then
    echo "❌ GWT_TOTAL 不一致：摘要块=$BLOCK_TOTAL，脚本计算=$SCRIPT_TOTAL"
    return 1
  fi

  if [ "$BLOCK_CHECKED" != "$TABLE_CHECKED" ] || [ "$BLOCK_CARRIED" != "$TABLE_CARRIED" ]; then
    echo "❌ GWT_CHECKED/CARRIED 不一致：摘要块(CHECKED=$BLOCK_CHECKED,CARRIED=$BLOCK_CARRIED) != 表内验真(CHECKED=$TABLE_CHECKED,CARRIED=$TABLE_CARRIED)"
    return 1
  fi

  local BLOCK_SUM=$((BLOCK_CHECKED + BLOCK_CARRIED))
  if [ "$BLOCK_SUM" != "$SCRIPT_TOTAL" ]; then
    echo "❌ GWT_CHECKED($BLOCK_CHECKED) + GWT_CARRIED($BLOCK_CARRIED) = $BLOCK_SUM ≠ GWT_TOTAL($SCRIPT_TOTAL)"
    return 1
  fi

  # FAIL/WARN/DEFERRED：摘要块必须与表内验真一致，且 FAIL/WARN 必须为 0
  if [ "$BLOCK_FAIL" != "$TABLE_FAIL" ] || [ "$BLOCK_WARN" != "$TABLE_WARN" ] || [ "$BLOCK_DEFERRED" != "$TABLE_DEFERRED" ]; then
    echo "❌ FAIL/WARN/DEFERRED 不一致：摘要块(FAIL=$BLOCK_FAIL,WARN=$BLOCK_WARN,DEFERRED=$BLOCK_DEFERRED) != 表内验真(FAIL=$TABLE_FAIL,WARN=$TABLE_WARN,DEFERRED=$TABLE_DEFERRED)"
    return 1
  fi
  [ "$TABLE_FAIL" = "0" ] && [ "$TABLE_WARN" = "0" ] || {
    echo "❌ 判定表存在 FAIL/WARN（fail=$TABLE_FAIL, warn=$TABLE_WARN）"
    return 1
  }

  # REVIEW_SCOPE 约束：非 incremental 不允许出现 CARRIED
  local SCOPE=$(echo "$SUMMARY" | grep '^REVIEW_SCOPE:' | awk '{print $2}')
  if [ "$SCOPE" != "incremental" ] && [ "$TABLE_CARRIED" -gt 0 ]; then
    echo "❌ REVIEW_SCOPE=$SCOPE 但判定表包含 CARRIED（仅 incremental 允许）"
    return 1
  fi

  # ===== §6.8.2 增量审查：REQ-C 类 GWT 不允许 carry-over =====
  if [ "$SCOPE" = "incremental" ] && [ "$BLOCK_CARRIED" -gt 0 ]; then
    local CARRIED_LIST=$(echo "$SUMMARY" | grep '^CARRIED_GWTS:' | sed 's/^CARRIED_GWTS:[[:space:]]*//')
    [ -n "$CARRIED_LIST" ] && [ "$CARRIED_LIST" != "N/A" ] || { echo "❌ 增量审查缺少 CARRIED_GWTS（必须显式列出沿用条目）"; return 1; }
    local CARRIED_REQC=$(echo "$CARRIED_LIST" | tr ',' '\n' | grep 'GWT-REQ-C' || true)
    if [ -n "$CARRIED_REQC" ]; then
      echo "❌ 增量审查中 REQ-C 类 GWT 不允许 carry-over（CARRIED_GWTS 包含禁止项）："
      echo "$CARRIED_REQC" | sed 's/^/  - /'
      return 1
    fi
  fi
  local TABLE_CARRIED_REQC=$(echo "$TABLE_CARRIED_GWTS" | grep '^GWT-REQ-C' || true)
  if [ -n "$TABLE_CARRIED_REQC" ]; then
    echo "❌ 增量审查中 REQ-C 类 GWT 不允许 carry-over（判定表 CARRIED 包含禁止项）："
    echo "$TABLE_CARRIED_REQC" | head -10 | sed 's/^/  - /'
    return 1
  fi

  # ===== §6.5.1 DEFERRED 验证：数量上限 + REQ-C 排除 + 验证计划 =====
  if [ "$BLOCK_DEFERRED" -gt 0 ] && [ "$SCRIPT_TOTAL" -gt 0 ]; then
    # 检查 DEFERRED 不超过 10%
    local MAX_DEFERRED=$(( (SCRIPT_TOTAL + 9) / 10 ))  # ceil(TOTAL * 0.1)
    if [ "$TABLE_DEFERRED" -gt "$MAX_DEFERRED" ]; then
      echo "❌ DEFERRED_TO_STAGING=$TABLE_DEFERRED 超过上限（GWT_TOTAL=$SCRIPT_TOTAL 的 10% = $MAX_DEFERRED）"
      return 1
    fi
    local DEFERRED_REQC=$(echo "$TABLE_ROWS" | awk -F'|' '
      function trim(s){ gsub(/^[ \t]+|[ \t]+$/, "", s); return s }
      $0 ~ /GWT-REQ-/ { gwt=trim($2); verdict=trim($4); if(index(verdict,"DEFERRED_TO_STAGING")>0) print gwt }
    ' | grep '^GWT-REQ-C' || true)
    if [ -n "$DEFERRED_REQC" ]; then
      echo "❌ DEFERRED_TO_STAGING 不允许用于 REQ-C（禁止项必须验证）："
      echo "$DEFERRED_REQC" | head -10 | sed 's/^/  - /'
      return 1
    fi
    local MISSING_PLANS=$(echo "$TABLE_ROWS" | awk -F'|' '
      function trim(s){ gsub(/^[ \t]+|[ \t]+$/, "", s); return s }
      $0 ~ /GWT-REQ-/ {
        gwt=trim($2); verdict=trim($4); remark=trim($7)
        if(index(verdict,"DEFERRED_TO_STAGING")>0){
          if(remark !~ /PLAN_ENV=/ || remark !~ /PLAN_METHOD=/ || remark !~ /PLAN_ETA=/) print gwt
        }
      }
    ' || true)
    if [ -n "$MISSING_PLANS" ]; then
      echo "❌ DEFERRED_TO_STAGING 缺少验证计划（备注列需包含 PLAN_ENV/PLAN_METHOD/PLAN_ETA）："
      echo "$MISSING_PLANS" | head -10 | sed 's/^/  - /'
      return 1
    fi
  fi

  return 0
}
```

**调用点**：在 `case "$OLD_PHASE" in` 的对应分支中，文件存在性检查之后调用：
```bash
    case "$OLD_PHASE" in
      # ... 现有 check_exit_artifact 调用保留 ...
      Implementation)
        check_exit_artifact "${VERSION_DIR}review_implementation.md"
        # 新增：摘要块内容验证
        validate_review_summary "${VERSION_DIR}review_implementation.md" "${VERSION_DIR}requirements.md" "${VERSION_DIR}status.md" || {
          echo "❌ 阶段出口门禁（Implementation → Testing）：review_implementation.md 摘要块验证失败"
          exit 1
        }
        ;;
      Design)
        check_exit_artifact "${VERSION_DIR}review_design.md"
        # Design 阶段：验证 TRACE 视角（追溯映射覆盖）
        # 注：Design 阶段不要求完整的 validate_review_summary（无 GWT 全量判定），
        # 但要求 review_design.md 存在且包含追溯映射
        ;;
      Testing)
        check_exit_artifact "${VERSION_DIR}test_report.md"
        check_exit_artifact "${VERSION_DIR}review_testing.md"
        # 新增：摘要块内容验证
        validate_review_summary "${VERSION_DIR}review_testing.md" "${VERSION_DIR}requirements.md" "${VERSION_DIR}status.md" || {
          echo "❌ 阶段出口门禁（Testing → Deployment）：review_testing.md 摘要块验证失败"
          exit 1
        }
        ;;
    esac
```

#### 变更 B：Git-Hook 6（W16）增加 GWT 覆盖完整性
**位置**：W16 硬拦截逻辑之后
**动作**：新增 GWT 覆盖差集检查

```bash
# W16 扩展：覆盖完整性 + 结论通过（requirements → test_report）
REQ_FILE="${VERSION_DIR}requirements.md"
if git cat-file -e ":$REQ_FILE" 2>/dev/null && git cat-file -e ":$TEST_REPORT" 2>/dev/null; then
  REQ_CONTENT=$(staged_content "$REQ_FILE") || exit 1
  TEST_CONTENT=$(staged_content "$TEST_REPORT") || exit 1

  # 提取 requirements 总集（并校验唯一性）
  REQ_GWTS_SORTED=$(echo "$REQ_CONTENT" | grep -oE 'GWT-REQ-C?[0-9]+-[0-9]+' | LC_ALL=C sort)
  DUP_REQ=$(echo "$REQ_GWTS_SORTED" | uniq -d || true)
  [ -z "$DUP_REQ" ] || { echo "❌ [W16 硬拦截] requirements.md 存在重复 GWT-ID"; echo "$DUP_REQ" | head -10 | sed 's/^/  - /'; exit 1; }
  REQ_GWTS=$(echo "$REQ_GWTS_SORTED" | uniq)
  REQ_GWT_COUNT=$(echo "$REQ_GWTS" | grep -c . || echo 0)

  if [ "$REQ_GWT_COUNT" -gt 0 ]; then
    # 提取 test_report 覆盖矩阵中的 GWT 集合
    MATRIX=$(echo "$TEST_CONTENT" | awk '
      /^##[[:space:]]+需求覆盖矩阵（GWT/{in_matrix=1; next}
      in_matrix && /^## / {exit}
      in_matrix {print}
    ')
    TEST_GWTS_SORTED=$(echo "$MATRIX" | grep -oE 'GWT-REQ-C?[0-9]+-[0-9]+' | LC_ALL=C sort)
    DUP_TEST=$(echo "$TEST_GWTS_SORTED" | uniq -d || true)
    [ -z "$DUP_TEST" ] || { echo "❌ [W16 硬拦截] test_report.md 覆盖矩阵存在重复 GWT-ID"; echo "$DUP_TEST" | head -10 | sed 's/^/  - /'; exit 1; }
    TEST_GWTS=$(echo "$TEST_GWTS_SORTED" | uniq)

    # 覆盖差集（漏覆盖/写错 ID）
    MISSING_GWTS=$(comm -23 <(echo "$REQ_GWTS") <(echo "$TEST_GWTS"))
    EXTRA_GWTS=$(comm -23 <(echo "$TEST_GWTS") <(echo "$REQ_GWTS"))
    if [ -n "$MISSING_GWTS" ]; then
      MISSING_COUNT=$(echo "$MISSING_GWTS" | grep -c .)
      echo "❌ [W16 硬拦截] test_report.md GWT 覆盖不完整：${MISSING_COUNT} 条 GWT 未覆盖"
      echo "$MISSING_GWTS" | head -10 | sed 's/^/  - /'
      exit 1
    fi
    if [ -n "$EXTRA_GWTS" ]; then
      EXTRA_COUNT=$(echo "$EXTRA_GWTS" | grep -c .)
      echo "❌ [W16 硬拦截] test_report.md 覆盖矩阵包含 requirements.md 中不存在的 GWT-ID：${EXTRA_COUNT} 条"
      echo "$EXTRA_GWTS" | head -10 | sed 's/^/  - /'
      exit 1
    fi

    # 结论通过：矩阵结果列不得出现 ❌/⚠
    echo "$MATRIX" | awk '
      /GWT-REQ-/ { if($0 ~ /❌|⚠/) bad=1 }
      END{exit bad}
    ' || { echo "❌ [W16 硬拦截] test_report.md 覆盖矩阵中存在 ❌/⚠ 结果"; exit 1; }

    # 结论通过：整体结论必须为"通过"
    CONCLUSION=$(echo "$TEST_CONTENT" | grep -E '^-[[:space:]]*整体结论[：:]' \
      | sed 's/^-[[:space:]]*整体结论[：:][[:space:]]*//;s/[[:space:]]*$//' \
      | head -1 || true)
    [ "$CONCLUSION" = "通过" ] || { echo "❌ [W16 硬拦截] test_report.md 整体结论必须为\"通过\"（当前：${CONCLUSION:-<empty>}）"; exit 1; }
  fi
fi
```

### 10.9 `scripts/git-hooks/post-commit`（E7）

**位置**：在 W18 之后追加 W19
**动作**：新增需求变更级联告警
**前置依赖**：post-commit 头部已定义 `warn()` 函数（输出黄色警告到 stderr）和 `$VERSION_DIR` 变量；本段直接使用。

```bash
# === Warning 19: 需求变更级联告警（requirements.md 变更时触发）===
echo "$CHANGED" | grep -q 'requirements\.md$' && {
  if [ -n "$VERSION_DIR" ]; then
    for doc in review_implementation review_testing review_planning test_report; do
      DOC_FILE="${VERSION_DIR}${doc}.md"
      [ ! -f "$DOC_FILE" ] && continue
      SAVED_HASH=$(sed -n '/REVIEW-SUMMARY-BEGIN/,/REVIEW-SUMMARY-END/p' "$DOC_FILE" \
        | grep '^REQ_BASELINE_HASH:' | awk '{print $2}')
      [ -z "$SAVED_HASH" ] && continue
      CURRENT_HASH=$(grep -oE 'GWT-REQ-C?[0-9]+-[0-9]+:.*' "${VERSION_DIR}requirements.md" 2>/dev/null | LC_ALL=C sort | git hash-object --stdin)
      if [ -n "$CURRENT_HASH" ] && [ "$SAVED_HASH" != "$CURRENT_HASH" ]; then
        warn "W19: requirements.md 已变更，${doc}.md 的 REQ_BASELINE_HASH 已过期，需重新审查"
      fi
    done
  fi
}
```

### 10.10 `scripts/cc-hooks/doc-structure-check.sh`（E1 + E2 配套）

**位置**：`requirements.md)` 分支
**动作**：增加 GWT-ID 格式检查，并强制存在“约束与禁止项（§4A / REQ-C）”章节（即使本次无禁止项，也应保留章节并写明“无”）

```bash
requirements.md)
    # ... 现有检查保留 ...
    check_section "## 4A\\."  # 约束与禁止项（REQ-C）
    # 新增：GWT-ID 格式检查
    if ! grep -qE 'GWT-REQ-C?[0-9]+-[0-9]+' "$FILE_PATH"; then
      MISSING="${MISSING}\n  - GWT-ID 格式验收标准（如 GWT-REQ-001-01）"
    fi
    ;;
```

### 10.11 Requirements→Design 门禁：禁止项确认清单（§7.0 落地）

> §7.0 定义了 `CONSTRAINTS-CONFIRMATION` 机器可读块作为 Requirements→Design 的硬拦截条件，但之前没有指定落地位置。

#### 变更 A：`scripts/git-hooks/pre-commit`（Git-Hook 7 扩展）
**位置**：`case "$OLD_PHASE" in` 增加 `Requirements)` 分支
**动作**：检查 `review_requirements.md` 中的确认标记

```bash
      Requirements)
        check_exit_artifact "${VERSION_DIR}review_requirements.md"
        # 检查禁止项确认清单
        REVIEW_REQ="${VERSION_DIR}review_requirements.md"
        # 注意：git index 使用相对于仓库根目录的路径
        REPO_ROOT=$(git rev-parse --show-toplevel)
        REVIEW_REQ_REL="${REVIEW_REQ#$REPO_ROOT/}"
        if [ -f "$REVIEW_REQ" ] || git cat-file -e ":$REVIEW_REQ_REL" 2>/dev/null; then
          REVIEW_CONTENT=$(git show ":$REVIEW_REQ_REL" 2>/dev/null || cat "$REVIEW_REQ" 2>/dev/null)
          # 检查 CONSTRAINTS-CONFIRMATION 块
          CONFIRMED=$(echo "$REVIEW_CONTENT" \
            | sed -n '/CONSTRAINTS-CONFIRMATION-BEGIN/,/CONSTRAINTS-CONFIRMATION-END/p' \
            | grep '^CONSTRAINTS_CONFIRMED:' | awk '{print $2}')
          if [ "$CONFIRMED" != "yes" ]; then
            MISSING="${MISSING}\n  - 禁止项确认清单未确认（CONSTRAINTS_CONFIRMED != yes）"
          fi
        fi
        ;;
```

#### 变更 B：`phases/02-requirements.md`
**位置**：阶段出口条件章节，追加
```markdown
- [ ] `review_requirements.md` 包含"禁止项/不做项确认清单"章节
- [ ] 清单中每条禁止项已归类为 A（已固化为 REQ-Cxxx）或 B（明确写入 Non-goals）
- [ ] 清单中无 TBD/待确认/unknown 占位项
- [ ] `<!-- CONSTRAINTS-CONFIRMATION-BEGIN -->` 块中 `CONSTRAINTS_CONFIRMED: yes`（人类已确认）
```

### 10.12 `phases/03-design.md`（断点 2：Design TRACE 审查落地）

> §5 断点 2 要求 Design 阶段 `@review` 必须包含 TRACE 视角，但之前没有 §10 落地规格。

**位置**：`### 阶段出口门禁` 或 `### AI 自动审查收敛` 章节，追加
```markdown
- [ ] `review_design.md` 存在
- [ ] `review_design.md` 包含 TRACE 视角：每条 REQ 都有对应的设计元素映射
- [ ] 追溯映射无遗漏：requirements.md 中的 REQ-ID 集合 ⊆ design.md 追溯表中的 REQ-ID 集合
```

## 11. 落地验收清单（行为断言优先）

> 原则：验收要验证“门禁行为是否真的拦得住绕过”，而不是 grep 到关键字。
> 关键词 grep 只能做 smoke check，不能作为“落地完成”的通过依据。

### 11.1 必须覆盖的行为断言（最小集）

至少覆盖以下“绕过/漂移”场景（任一失败都视为未落地）：
- **摘要篡改拦截**：判定表中存在 `❌/⚠/DEFERRED_TO_STAGING/CARRIED` 等变化时，摘要块自报数字不一致必须被拦截（不信任自报）。
- **覆盖差集拦截**：`requirements.md` 总集与 `review_*.md`/`test_report.md` 的判定集差集非空必须被拦截（漏覆盖/多写 ID 都拦）。
- **重复 ID 拦截**：`requirements.md` / 判定表 / 覆盖矩阵出现重复 `REQ-ID` 或 `GWT-ID` 必须被拦截（重复会被集合运算吞掉，计数不可信）。
- **增量审查拦截**：`CARRIED` 仅允许在 `REVIEW_SCOPE=incremental`；`CARRIED_GWTS` 与表内 `CARRIED` 标记一致；且 **REQ-C 一律禁止 carry-over**。
- **DEFERRED 规则拦截**：数量上限 + 非 REQ-C + 每条都有可机读验证计划（`PLAN_ENV/PLAN_METHOD/PLAN_ETA`）。
- **W16 交付拦截**：`test_report.md` 覆盖完整且结果通过（覆盖矩阵无 `❌/⚠`，整体结论为“通过”）。

### 11.2 推荐验收方式（脚本/测试）

推荐把上述行为断言写成可复现的脚本/测试，并在 CI 中运行（见 §7.4）。如果使用本仓库的实现，直接运行：

```bash
bash scripts/tests/run-all.sh
```

## 附录 A：最小示例（禁止项）
```markdown
#### REQ-C001：页面不得出现描述性卡片/冗余文案
**适用范围**：订单列表页（所有角色，所有状态）
**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-C001-01: Given 任意角色登录，When 打开订单列表页，Then 页面不出现「九大市场数据域统一展示…」描述性卡片（空/有数据/异常）
- [ ] GWT-REQ-C001-02: Given 任意角色登录，When 打开订单列表页，Then 页面文本不包含「手工交易」
```

## 附录 B：审查摘要块（门禁解析）
见 6.4.2，门禁只认最后一次摘要块。

## 附录 C：`enhance_v3` 借鉴路线图（E1–E9 对照表，含验真）

> 目的：将 `enhance_v3.md` 中“有效改进项”映射到本方案，并用“验真”避免把“文档宣称”当作“机制已生效”。  
> 验真时间：2026-02-14（本地工作区 + 脚本测试）  
> 状态口径：A（必须**已纳入 git** 且可通过 `bash scripts/tests/run-all.sh` 验真；启用 CI/PR 时以 CI 结果为最终口径）

| E# | 改进项（enhance_v3） | 对应 `enhance_temp` | 计划落地文件（最小集） | 优先级 | 状态（验真） | 备注 |
|---|---|---|---|---|---|---|
| E1 | GWT 精度升级：从"可测试"到"可判定" | §4.2.3、§2 | `templates/requirements_template.md` | 高 | 已实施（已验真） | 模板已包含 `GWT-ID` + “必须可判定”；`doc-structure-check` 强制校验 |
| E2 | 负向需求独立章节（REQ-C） | §3.2、§5(断点1)、§8 | `templates/requirements_template.md` | 高 | 已实施（已验真） | 模板新增 `§4A 约束与禁止项（REQ-C）`（强制存在） |
| E3 | 反向 R6（REQ → plan 覆盖完整性） | §5(断点3)、§10.2 | `templates/plan_template.md`、`phases/04-planning.md` | 高 | 已实施（已验真） | 模板与阶段规则已提供反向差集检查；门禁在阶段推进时做覆盖验真 |
| E4 | `@review` 需求符合性审查维度 | §6.3–§6.5、§7 | `templates/review_template.md`、`AGENTS.md.template` | 高 | 已实施（已验真） | review 模板新增 REQ 协议：逐条 GWT 判定表 + 摘要块；AGENTS 同步说明 |
| E5 | REQ 覆盖率交付门禁 | §7.3、§6.4.2 | `scripts/git-hooks/pre-commit`（W16 扩展） | 高 | 已实施（已验真） | W16 硬拦截加入 requirements→test_report 的 GWT 覆盖差集验真 |
| E6 | Implementation/Testing 阶段收敛条件强化 | §7.1、§7.2、§6.5–§6.6 | `phases/05-implementation.md`、`phases/06-testing.md` | 高 | 已实施（已验真） | 去除 accept/defer；阶段门禁验真 `REVIEW-SUMMARY` + GWT 覆盖完整性 |
| E7 | 需求变更级联告警 | §6.7、§9 | `scripts/git-hooks/post-commit` | 中 | 已实施（已验真） | 新增 W19：requirements 变更 → REQ_BASELINE_HASH 过期提醒 |
| E8 | Implementation 白名单增加 design/requirements 回写 | §5(断点3)、§9 | `scripts/cc-hooks/doc-scope-guard.sh` | 高 | 已实施（已验真） | Implementation/Testing 阶段允许回写 `design.md/requirements.md` |
| E9 | hooks 层修复（阶段门禁、入口必读、文档同步等） | §7、§10.3 | `scripts/git-hooks/*`、`scripts/cc-hooks/*`、`hooks.md` | 高 | 已实施（已验真） | 以 `bash scripts/tests/run-all.sh` 的行为断言为准；启用 CI/PR 时建议将其设为 Required check（见 §7.4） |
| E10 | 对抗性审查（缓解自审盲区） | §6.3.1 | `templates/review_template.md` | 高 | 已实施（已验真） | 反向假设 + 人类抽检锚点（`SPOT_CHECK_GWTS`）+ 禁止全 PASS 零备注 |
| E11 | 成本与上下文控制 | §6.8 | `templates/review_template.md`、阶段规则 | 高 | 已实施（已验真） | 分层证据 + 增量审查（可验真）+ 上下文预算 |
| E12 | Requirements→Design 禁止项确认门禁 | §7.0 | `scripts/git-hooks/pre-commit`、`phases/02-requirements.md` | 高 | 已实施（已验真） | `CONSTRAINTS-CONFIRMATION` 硬拦截 + 阶段规则同步 |
| E13 | Design TRACE 审查落地 | §5 断点2 | `phases/03-design.md` | 中 | 已实施（已验真） | 阶段门禁校验 design 追溯矩阵覆盖 requirements 全量 REQ |

### 建议落地顺序（参考 `enhance_v3`，按本方案依赖调整）

第一批（直接补齐"需求符合性 + 不遗漏"牙齿）：
1. E4（@review 需求符合性审查维度）
2. E10（对抗性审查：反向假设 + 抽检锚点 + 禁止全 PASS 零备注）
3. E6（Implementation/Testing 收敛条件强化）
4. E1（GWT 可判定 + `GWT-ID`）
5. E2（REQ-C 禁止项独立章节）
6. E3（反向 R6：REQ → plan 覆盖）
7. E12（Requirements→Design 禁止项确认门禁）

第二批（把"覆盖完整性"下沉到交付硬门禁 + 成本控制 + 需求变更提醒）：
8. E11（成本与上下文控制：分层证据 + 增量审查 + 上下文预算）
9. E5（REQ/GWT 覆盖率门禁落到 W16）
10. E7（需求变更级联告警）
11. E13（Design TRACE 审查落地）
