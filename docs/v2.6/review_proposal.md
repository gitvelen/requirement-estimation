# Proposal 阶段审查报告

## 文档元信息
| 项 | 值 |
|---|---|
| 版本号 | v2.6 |
| 审查阶段 | Proposal |
| 审查轮次 | 3 |
| 审查日期 | 2026-03-09 |
| 审查人 | Claude / Codex |
| 审查结果 | 待人工确认 |

---

## 第 1 轮审查（2026-03-09）

### 审查范围
- `proposal.md` 文档完整性
- P-DO/P-DONT/P-METRIC 覆盖度
- 开放问题收敛状态
- 与 CR-20260309-001 的一致性

### 审查发现

#### ✅ 符合项

1. **文档结构完整性**
   - ✅ 包含一句话总结
   - ✅ 背景与现状清晰（Token 超限问题描述详细）
   - ✅ 目标与成功指标明确（4 个可判定指标）
   - ✅ 目标用户与场景具体（产品经理、系统管理员）
   - ✅ 解决方案概述完整（5 个核心技术方案）
   - ✅ 范围定义清晰（In Scope 6 项，Non-goals 4 项）
   - ✅ 风险与依赖已识别（4 个风险及缓解措施）
   - ✅ 约束条件明确（技术、业务、运维约束）

2. **P-DO/P-DONT/P-METRIC 完整性**
   - ✅ P-DO 4 项：超长文档 100% 成功、AI 结果完整性、正常文档性能不变、回滚能力
   - ✅ P-DONT 3 项：不允许文档内容丢失、不允许引入外部依赖、不允许修改 API 契约
   - ✅ P-METRIC 3 项：Token 超限错误率 = 0、单元测试覆盖率 > 80%、分块调用总耗时限制
   - ✅ 所有验收锚点都有明确的验收方式和数据源

3. **开放问题收敛**
   - ✅ 所有开放问题已关闭（本地环境配置、测试范围、时间估算）
   - ✅ 无待关闭问题

4. **与 CR-20260309-001 一致性**
   - ✅ 技术方案与 CR 一致（轻量级 Token 估算 + 段落级分块 + 多轮调用合并）
   - ✅ 影响面与 CR 一致（backend/utils、backend/service、backend/config）
   - ✅ 时间估算与 CR 一致（2.5 天）
   - ✅ 风险评估与 CR 一致（4 个风险及缓解措施）

5. **核心价值对齐**
   - ✅ 用户核心诉求明确：解决内网超长文档导入失败问题
   - ✅ 最高优先级：不希望文档内容有损失
   - ✅ 成功指标可判定：Token 超限错误率 = 0

#### ⚠️ 需澄清项

**无 P0/P1 问题**

#### 📋 观察项（非阻塞）

**OBS-PROP-001: 监控指标未在提案中明确**
- **观察**：提案中提到"记录日志监控"，但未明确监控指标和告警阈值
- **建议**：在后续 Design 阶段补充监控指标定义（如：分块数 > 5 告警、单次调用 token > 31000 告警）
- **状态**：defer to Design

**OBS-PROP-002: 降级策略未详细说明**
- **观察**：提案中提到配置开关 `ENABLE_LLM_CHUNKING`，但未说明降级后的行为（是否截断、如何提示用户）
- **建议**：在 Design 阶段明确降级逻辑
- **状态**：defer to Design

**OBS-PROP-003: 分块重叠策略未详细说明**
- **观察**：提案中提到"按段落边界智能重叠"，但未说明具体的重叠策略（保留多少段落、如何避免重复）
- **建议**：在 Design 阶段明确分块重叠算法
- **状态**：defer to Design

### 审查结论

**当前状态**：✅ 提案质量合格，无 P0/P1 问题

**符合 Proposal 阶段要求**：
1. ✅ 结构化讨论协议完成（Q&A 覆盖核心价值、边界、验收、约束）
2. ✅ P-DO/P-DONT/P-METRIC 完整性达标
3. ✅ 所有开放问题已关闭
4. ✅ 与 CR-20260309-001 保持一致

**观察项处理**：
- 3 个观察项（监控指标、降级策略、分块重叠策略）defer 到 Design 阶段处理

**下一步**：
- 更新 `status.md`，设置 `_run_status: wait_confirm`
- 等待人工确认后进入 Requirements 阶段

---

## 审查统计

| 类别 | 数量 |
|------|------|
| P0 (Blocker) | 0 |
| P1 (Must Fix) | 0 |
| P2 (Should Fix) | 0 |
| 观察项 | 3 |

**收敛状态**：✅ 已收敛（P0 open = 0, P1 open = 0）

---

## 变更历史
| 日期 | 轮次 | 审查人 | 主要变更 |
|------|------|--------|---------|
| 2026-03-09 | 1 | Claude | 初始审查，提案质量合格，无 P0/P1 问题，3 个观察项 defer 到 Design |

---

## 第 2 轮审查（2026-03-09）

### §0 审查准备

#### 事实核实源
- `docs/v2.6/proposal.md`
- `docs/v2.6/cr/CR-20260309-001.md`
- `docs/v2.6/review_change_management.md`
- `docs/v2.6/status.md`
- `backend/service/profile_summary_service.py`
- `backend/utils/token_counter.py`

#### 关键证据
- `nl -ba docs/v2.6/proposal.md | sed -n '120,236p'`
- `nl -ba docs/v2.6/review_change_management.md | sed -n '49,90p'`
- `python - <<'PY' ... TokenCounter.chunk_by_tokens(...) ... PY`
  - 输出：`num_chunks 2`
  - 输出：`1 60000 24000`
  - 输出：`2 120002 48000`
- `python - <<'PY' ... ProfileSummaryService()._context_max_chars() ... PY`
  - 输出：`context_max_chars 120000`

### 审查发现

#### P1（Must Fix）

**P1-PROP-001: 测试口径与已关闭决策重新冲突**
- **问题**：ChangeManagement 第 1 轮已将“是否需要集成测试”收敛为“单元测试即可，无需集成测试”，但 Proposal 又同时写了：
  - In Scope 仅包含 3 个单元测试文件
  - 开放问题写明“单元测试即可，无需集成测试”
  - `P-DO-01` 要求“真实超长文档”集成测试通过
  - “后续阶段”再次写成“单元测试和集成测试”
- **影响**：验证集合、工期估算和后续 Requirements 口径无法稳定，P1-CM-002 实际被重新打开。
- **建议**：统一 In Scope / P-DO / 开放问题 / 后续阶段的测试口径；如果确实不做集成测试，应改写验收锚点，避免对下游传递矛盾要求。
- **状态**：open

**P1-PROP-002: 回滚方案与“内容无损失”禁止项冲突，当前实现也仍在先截断后分块**
- **问题**：Proposal 将 `ENABLE_LLM_CHUNKING=false` 定义为回退到原有逻辑，而 CR 已明确原有逻辑是“字符截断”；同时 Proposal 的 P-DONT 明确“不允许文档内容丢失”。当前工作树里的实现也仍先执行 `context[: self._context_max_chars()]`，再做 token 估算和分块。
- **影响**：最高优先级目标“内容无损失”在回滚路径上无法成立；对超过 `120000` 字符的文档，当前实现分块前就会丢尾部内容。
- **建议**：明确回滚是否允许牺牲完整性；若不允许，则回滚路径也必须保持无损，或者从验收锚点中移除“回退到原有截断逻辑”。
- **状态**：open

**P1-PROP-003: 当前分块实现不能保证每块都在 token 上限内**
- **问题**：`TokenCounter.chunk_by_tokens()` 在切块后把最后 1-2 个段落作为重叠内容直接带入下一块，但没有再次校验重叠后的总 token 数是否超限。最小复现中，两段各 `60000` 字符、`max_tokens=25000` 时，第二块估算达 `48000 tokens`。
- **影响**：核心缓解手段本身仍可能生成超限请求，直接复现当前版本要解决的故障类型。
- **建议**：重叠后重新检查并裁剪/重切，确保每个 chunk 都满足 `<= max_tokens`；同时补一条回归测试覆盖该场景。
- **状态**：open

### 审查结论

**当前状态**：Proposal 阶段未收敛，上一轮“无 P1”结论不成立。

**收敛判定**：
- P0（open）= 0
- P1（open）= 3

**结论**：
- 不建议进入 Requirements 阶段
- 需先修正文档口径冲突，并决定是否继续保留当前已开始的实现分支
- 如继续实现，至少要先修复“先截断后分块”与“重叠后超限”两个阻断问题，否则实现方向与提案锚点不一致

## 第 2 轮审查统计

| 类别 | 数量 |
|------|------|
| P0 (Blocker) | 0 |
| P1 (Must Fix) | 3 |
| P2 (Should Fix) | 0 |
| 观察项 | 0 |

**收敛状态**：❌ 未收敛（P0 open = 0, P1 open = 3）

## 变更历史（续）
| 日期 | 轮次 | 审查人 | 主要变更 |
|------|------|--------|---------|
| 2026-03-09 | 2 | Codex | 发现 3 个 P1：测试口径冲突、回滚与无损目标冲突、分块算法上限不成立；撤销上一轮“已收敛”结论 |

---

## 第 3 轮审查（2026-03-09）

### §0 审查准备

#### 事实核实源
- `docs/v2.6/proposal.md`
- `docs/v2.6/cr/CR-20260309-001.md`
- `docs/v2.6/status.md`

#### 关键证据
- `nl -ba docs/v2.6/proposal.md | sed -n '65,250p'`
- `nl -ba docs/v2.6/cr/CR-20260309-001.md | sed -n '60,160p'`

### 审查发现

#### P1 复查结论

**P1-PROP-001: 已修复**
- **修复**：统一 Proposal 的测试口径为“后端单元测试 + 服务级验证 + 人工抽样验证”；删除“集成测试必需”的冲突表述，并将测试资产路径统一到仓库实际的 `tests/` 目录。

**P1-PROP-002: 已修复**
- **修复**：将回滚语义改为“关闭分块后，普通文档走单次调用；超长文档显式失败并提示开启分块，不做静默截断”，与“内容无损失”禁止项一致。

**P1-PROP-003: 已修复**
- **修复**：在 Proposal/CR 中显式增加“任意 chunk（含重叠段落）不得超过输入上限”“若重叠会超限则缩减为 1 个或 0 个重叠段落”“禁止先截断再分块”的规则，Proposal 阶段口径已明确可判定。

### 审查结论

**当前状态**：Proposal 文档口径已收敛。

**收敛判定**：
- P0（open）= 0
- P1（open）= 0

**结论**：
- Proposal 阶段可以等待人工确认
- 当前轮次仅修正文档口径，不对实现代码做完成性宣称

## 第 3 轮审查统计

| 类别 | 数量 |
|------|------|
| P0 (Blocker) | 0 |
| P1 (Must Fix) | 0 |
| P2 (Should Fix) | 0 |
| 观察项 | 0 |

**收敛状态**：✅ 已收敛（P0 open = 0, P1 open = 0）

## 变更历史（续）
| 日期 | 轮次 | 审查人 | 主要变更 |
|------|------|--------|---------|
| 2026-03-09 | 3 | Codex | Proposal/CR 已统一测试口径、回滚语义与分块上限规则，关闭第 2 轮 3 个 P1 |

---

## 第 4 轮审查（2026-03-09）

### §0 审查准备

#### 审查范围
用户要求"走查本阶段工作，边审边改"。本轮审查覆盖：
- Proposal 阶段文档（proposal.md, CR, status.md, review 文件）
- 已存在的代码变更（token_counter.py, llm_client.py, config.py）

#### 审查发现

本轮审查发现：**Proposal 阶段的文档与已存在的代码实现之间存在严重不一致**。

### 关键发现

**发现 1：阶段越界 — 代码实现不属于 Proposal 阶段产出物**

根据 `.aicoding/phases/01-proposal.md`：
- Proposal 阶段的唯一产出物是 `docs/<版本号>/proposal.md`
- 代码实现属于 Phase 05 (Implementation) 的工作范围

当前工作树中存在以下代码文件：
- `backend/utils/token_counter.py` (新增)
- `backend/utils/llm_client.py` (扩展)
- `backend/config/config.py` (扩展)
- `backend/service/profile_summary_service.py` (未修改)

这些代码不应在 Proposal 阶段存在。

**发现 2：文档声称"已修复"但代码未修复**

`review_proposal.md` 第 3 轮将 P1-PROP-003 标记为"已修复"：
> 在 Proposal/CR 中显式增加"任意 chunk（含重叠段落）不得超过输入上限"的规则

但代码审查发现：
1. **P1-PROP-003 overlap guard 未实现**：`token_counter.py:142-144` 在添加重叠段落后未检查是否超限
2. **P1-PROP-002 rollback 未实现**：`ENABLE_LLM_CHUNKING=false` 的回滚逻辑不存在
3. **P1-PROP-002 pre-truncation 仍存在**：`profile_summary_service.py:525` 和 `:366` 的字符截断未移除
4. **Important: `adjusted_max_tokens` 无 floor guard**：可能为负数或零
5. **Important: `LLM_INPUT_MAX_TOKENS` 未连线**：config 定义了但未传给 `chunk_by_tokens()`
6. **Important: `profile_summary_service.py` 未修改**：In Scope 声明要改但实际未改
7. **Suggestion: `preserve_paragraphs=False` 分支无上限检查**
8. **Suggestion: JSON 解析失败静默丢弃 chunk**

### 审查结论

**当前状态**：Proposal 阶段文档与代码实现严重不一致。

**根本问题**：
1. **阶段越界**：代码实现出现在 Proposal 阶段，违反工作流定义
2. **文档与代码脱节**：第 3 轮审查声称"已修复"仅指文档文本，代码仍有 3 个 Critical + 3 个 Important 问题

**建议处理方式（二选一）**：

**方案 A：回退到纯 Proposal 阶段**
1. 删除或 stash 所有代码文件（token_counter.py, llm_client.py 的扩展, config.py 的扩展）
2. 保留 Proposal 文档（proposal.md, CR, status.md, review 文件）
3. 在 `review_proposal.md` 中明确：第 3 轮"已修复"仅指文档口径，代码正确性 defer 到 Implementation 阶段
4. 等待人工确认后进入 Requirements 阶段

**方案 B：承认已进入 Implementation 阶段**
1. 更新 `status.md`：`_phase: Implementation`
2. 修复代码中的 3 个 Critical + 3 个 Important 问题
3. 补充 Requirements、Design、Planning 文档（或标记为 skip）
4. 完成 Implementation 后进入 Testing 阶段

**推荐方案 A**，理由：
- 符合工作流定义（Proposal → Requirements → Design → Planning → Implementation）
- 避免跳过 Requirements/Design/Planning 导致的需求/设计缺失
- 代码问题可在 Implementation 阶段系统性修复

## 第 4 轮审查统计

| 类别 | 数量 |
|------|---------|
| P0 (Blocker) | 1（阶段越界） |
| P1 (Must Fix) | 0（文档层面已收敛） |
| 代码 Critical | 3（defer 到 Implementation） |
| 代码 Important | 3（defer 到 Implementation） |
| 代码 Suggestion | 2（defer 到 Implementation） |

**收敛状态**：✅ 已收敛（P0 已处理：代码 stash，阶段越界问题消除；文档层面 P0=0, P1=0）

**下一步**：等待用户选择方案 A 或方案 B

**用户决策（2026-03-09）**：选择方案 A。
- 已将代码文件（token_counter.py、llm_client.py 扩展、config.py 扩展）stash，stash message: "v2.6 代码实现 - defer 到 Implementation 阶段"
- 工作树恢复为纯 Proposal 阶段状态
- 代码中的 3 个 Critical + 3 个 Important 问题已记录，defer 到 Implementation 阶段处理

## 变更历史（续）
| 日期 | 轮次 | 审查人 | 主要变更 |
|------|------|--------|---------|
| 2026-03-09 | 4 | Claude + code-reviewer | 发现阶段越界问题：代码实现不应在 Proposal 阶段存在；文档与代码严重不一致；用户选择方案 A，代码已 stash，阶段越界问题消除 |
