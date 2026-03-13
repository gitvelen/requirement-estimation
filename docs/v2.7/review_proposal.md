# v2.7 Proposal 阶段审查报告

## 审查信息
- **审查者**：Codex（GPT-5）
- **审查时间**：2026-03-12
- **审查对象**：`docs/v2.7/proposal.md` v0.1
- **审查口径**：full（`status.md` / `proposal.md` / `docs/系统功能说明书.md` / `docs/技术方案设计.md` / 当前实现现状交叉）
- **适用规则**：
  - `.aicoding/phases/01-proposal.md`
  - `.aicoding/templates/proposal_template.md`
  - `docs/lessons_learned.md`（快速索引 R1-R9）
  - `AGENTS.md`（证据驱动、单一真相源、可验收可追溯）

## §0 审查准备（REP 步骤 A+B）

### A. 事实核实
| # | 声明（出处） | 核实源 | 结论 |
|---|---|---|---|
| 1 | 当前画像为“5 域 11 字段”（`proposal.md` M1、子方案二） | `backend/service/system_profile_service.py`、`frontend/src/pages/SystemProfileBoardPage.js`、`docs/系统功能说明书.md` v2.4/v2.5 口径 | ❌ |
| 2 | 当前 PM 导入页支持 5 种文档类型（`proposal.md` 背景、M2） | `frontend/src/pages/SystemProfileImportPage.js` | ✅ |
| 3 | LLM Skill 写入模式 defer 到 Requirements（`proposal.md` 开放问题） | `proposal.md` 场景、风险、开放问题三处交叉 | ❌ |
| 4 | ESB 自动匹配成功率目标可在本版本达成（`proposal.md` M3） | `proposal.md` 风险表、In Scope、TOP 场景交叉 | ❌ |

### B. 关键概念交叉引用
| 概念 | 出现位置 | 口径一致 |
|---|---|---|
| LLM Skill 写入模式 | `proposal.md:59`, `proposal.md:109`, `proposal.md:176`, `proposal.md:203` | ❌ |
| ESB 匹配策略 | `proposal.md:46`, `proposal.md:60`, `proposal.md:121`, `proposal.md:175` | ❌ |
| 当前画像字段基线 | `proposal.md:44`, `proposal.md:76`, `docs/系统功能说明书.md:121`, `docs/技术方案设计.md:578`, `system_profile_service.py:323` | ❌ |
| 当前 PM 导入页类型 | `proposal.md:24`, `proposal.md:45`, `proposal.md:73`, `SystemProfileImportPage.js:49` | ✅ |
| 阶段状态单一真相源 | `status.md:26-40` vs `proposal.md:36-48`, `proposal.md:211-214` | ❌ |

## 发现的问题（按严重度）

### P0（Blocker）
无

### P1（Major）
1. **LLM Skill 写入模式没有收敛，Proposal 同时写了“待决策”和“已确定为建议制”两套口径**
   - 位置：`docs/v2.7/proposal.md:59`、`docs/v2.7/proposal.md:109`、`docs/v2.7/proposal.md:176`、`docs/v2.7/proposal.md:203`
   - 现状：
     - TOP 场景已写成“生成画像建议 → PM 审核确认”
     - 风险缓解也写成“Skill 产出为建议而非直接写入”
     - 但开放问题又写“直接写入 vs 生成建议待确认” defer 到 Requirements
   - 风险：Requirements 无法判断应产出哪套 REQ/API/验收口径，后续实现和测试容易出现“文档认为是建议制、接口却按直写制设计”的偏差。
   - 建议：Proposal 阶段只保留一套口径。
     - 如果确实待定，就删去 TOP 场景和风险表中已经假定为“建议制”的表述。
     - 如果用户已确认“建议制”，则关闭开放问题 #3，并把其作为明确验收锚点落盘。

2. **M3 的 95% 成功率依赖“手动映射”能力，但该能力不在 In Scope，也没有用户场景和验收锚点**
   - 位置：`docs/v2.7/proposal.md:46`、`docs/v2.7/proposal.md:60`、`docs/v2.7/proposal.md:121`、`docs/v2.7/proposal.md:163`、`docs/v2.7/proposal.md:175`
   - 现状：
     - 指标要求“自动匹配更新 ≥ 95% 已注册系统”
     - 风险缓解写的是“模糊匹配 + 手动映射”
     - 但 In Scope、TOP 场景、P-DO/P-METRIC 都没有“手动映射”能力的页面/API/流程定义
   - 风险：如果 95% 目标需要手动映射兜底，Requirements 会被迫隐式扩 scope；如果不做手动映射，这个指标又缺少可达成依据。
   - 建议：二选一收敛。
     - 要么把“手动映射”明确纳入范围、场景、验收锚点。
     - 要么删除“手动映射”表述，仅按自动匹配能力重写目标值和缓解策略。

### P2（Minor）
1. **M1 的现状基线写错，当前不是“5 域 11 字段”，而是 5 域 12 子字段**
   - 位置：`docs/v2.7/proposal.md:44`、`docs/v2.7/proposal.md:76`
   - 证据：
     - 当前后端空画像结构为 3 + 2 + 2 + 3 + 2 = 12 个子字段（`backend/service/system_profile_service.py:325-346`）
     - 当前前端展示配置与之对应（`frontend/src/pages/SystemProfileBoardPage.js:29-68`）
     - 主文档也明确记录 v2.4 为“5 域 12 子字段结构”（`docs/系统功能说明书.md:121`、`docs/技术方案设计.md:578`）
   - 风险：成功指标基线错误会污染后续 Requirements 的 REQ/METRIC 口径，影响可追溯性和验收争议处理。
   - 建议：将 M1 / P-METRIC-01 / 子方案二中的基线统一改成 12，并说明计数规则。

2. **`status.md` 仍停留在初始化占位状态，没有同步 Proposal 阶段已确定的摘要、目标和审查入口**
   - 位置：`docs/v2.7/status.md:26-40`
   - 现状：
     - 变更摘要仍只有“版本启动”
     - 成功指标仍是“待 Proposal 阶段确定”
     - 审查链接仍是泛化的 `review_*.md`
   - 风险：`status.md` 被定义为阶段状态单一真相源，但当前无法独立反映本阶段已经收敛出的目标与审查产物，后续人工复核容易漏看。
   - 建议：至少同步 Proposal 已确认的变更摘要、关键指标，并把当前阶段审查入口明确到 `review_proposal.md`。

## 审查清单
- [x] 文档结构完整性已覆盖
- [x] P-DO / P-DONT / P-METRIC 非空
- [x] 开放问题状态已标注
- [x] 基线现状已做代码/主文档交叉核验
- [x] 关键概念一致性已做全文交叉引用
- [x] `status.md` 与 `proposal.md` 的阶段留痕已交叉核验

## §3 覆盖率证明（REP 步骤 D）
| 维度 | 应检项数 | 已检 | 未检 | 未检说明 |
|---|---|---|---|---|
| 事实核实（步骤A） | 4 | 4 | 0 | - |
| 概念交叉引用（步骤B） | 5 | 5 | 0 | - |
| Proposal 阶段核心检查项 | 6 | 6 | 0 | 文档结构、锚点完整性、开放问题状态、基线准确性、口径一致性、阶段留痕 |

## 对抗性自检
- [x] 已检查“文本是否已经暗含决策但开放问题仍写待定”
- [x] 已检查指标是否依赖未纳入范围的能力
- [x] 已检查现状基线是否用代码/主文档复核，而非仅信任提案自述
- [x] 已检查 `status.md` 是否仍停留在初始化占位

## 收敛判定
- P0(open): 0
- P1(open): 2
- P2(open): 2
- 结构门禁：✅ 通过
- 语义门禁：❌ 未通过
- 证据门禁：✅ 通过

**审查结论：❌ 当前不建议进入 Requirements 阶段。请先收敛上述 2 个 P1，再发起下一轮 Proposal 复审。**

## 证据清单

### 1. 当前画像字段基线核验

**命令：**
```bash
nl -ba backend/service/system_profile_service.py | sed -n '323,350p'
nl -ba frontend/src/pages/SystemProfileBoardPage.js | sed -n '27,80p'
nl -ba docs/系统功能说明书.md | sed -n '118,123p'
nl -ba docs/技术方案设计.md | sed -n '576,580p'
```

**输出：**
```text
325-346: 后端空画像结构包含 5 域，子字段分别为 3 / 2 / 2 / 3 / 2
29-68: 前端 PROFILE_DOMAIN_CONFIG 对应同一组 12 个字段
121: 主文档写明“5 域 12 子字段结构”
578: 技术方案设计写明“profile_data 5 域 12 子字段结构”
```

**定位：**
- `backend/service/system_profile_service.py:325`
- `frontend/src/pages/SystemProfileBoardPage.js:29`
- `docs/系统功能说明书.md:121`
- `docs/技术方案设计.md:578`
- `docs/v2.7/proposal.md:44`

### 2. PM 导入页文档类型基线核验

**命令：**
```bash
nl -ba frontend/src/pages/SystemProfileImportPage.js | sed -n '38,55p'
```

**输出：**
```text
49-55: requirements / design / tech_solution / history_report / esb 共 5 种类型
```

**定位：**
- `frontend/src/pages/SystemProfileImportPage.js:49`
- `docs/v2.7/proposal.md:24`
- `docs/v2.7/proposal.md:45`

### 3. LLM Skill 写入模式口径一致性核验

**命令：**
```bash
rg -n "PM 审核确认|写入模式|建议待确认|建议而非直接写入" docs/v2.7/proposal.md
```

**输出：**
```text
59: 生成画像建议 -> PM 审核确认
109: LLM Skill 写入模式 defer 到 Requirements 阶段决策
176: Skill 产出为"建议"而非直接写入
203: 开放问题 #3 仍为 defer 到 Requirements
```

**定位：**
- `docs/v2.7/proposal.md:59`
- `docs/v2.7/proposal.md:109`
- `docs/v2.7/proposal.md:176`
- `docs/v2.7/proposal.md:203`

### 4. ESB 匹配目标与范围一致性核验

**命令：**
```bash
rg -n "95%|手动映射|模糊匹配|自动匹配更新|匹配系统" docs/v2.7/proposal.md
```

**输出：**
```text
46: 自动匹配更新 >= 95% 已注册系统
60: 自动更新所有匹配系统的 D3 集成关系
121: In Scope 仅写“自动匹配更新系统画像 D3 域”
163: P-METRIC-03 延续 95% 指标
175: 风险缓解写“模糊匹配 + 手动映射”
```

**定位：**
- `docs/v2.7/proposal.md:46`
- `docs/v2.7/proposal.md:60`
- `docs/v2.7/proposal.md:121`
- `docs/v2.7/proposal.md:163`
- `docs/v2.7/proposal.md:175`

### 5. 阶段状态同步核验

**命令：**
```bash
nl -ba docs/v2.7/status.md | sed -n '26,40p'
nl -ba docs/v2.7/proposal.md | sed -n '36,48p'
nl -ba docs/v2.7/proposal.md | sed -n '211,214p'
```

**输出：**
```text
status.md 仍为“版本启动 / 待 Proposal 阶段确定 / review_*.md”
proposal.md 已明确 5 项成功指标，并已有 v0.1 变更记录
```

**定位：**
- `docs/v2.7/status.md:26`
- `docs/v2.7/status.md:32`
- `docs/v2.7/status.md:40`
- `docs/v2.7/proposal.md:41`
- `docs/v2.7/proposal.md:211`

---
审查完成时间：2026-03-12

---

## 复审（第 2 轮，2026-03-12）

### 复审范围
- 首轮 P1-1：LLM Skill 写入模式口径冲突
- 首轮 P1-2：ESB 95% 指标依赖未入 scope 的“手动映射”
- 首轮 P2-1：M1 / P-METRIC / 子方案二的基线字段数错误
- 首轮 P2-2：`status.md` 未同步 Proposal 阶段摘要、指标与审查入口

### 复审证据
1. `rg -n "辅助生成系统画像相关提取结果|写入模式|建议制|匹配成功/未匹配统计|手动映射|5 域 12 子字段|文档版本|v0.2" docs/v2.7/proposal.md docs/v2.7/status.md`
2. `nl -ba docs/v2.7/proposal.md | sed -n '1,240p'`
3. `nl -ba docs/v2.7/status.md | sed -n '1,120p'`

### 复审结果
- 原 P1-1：已关闭
  - 证据：`proposal.md` 已将 PM 侧表述改为“辅助生成系统画像相关提取结果”，TOP 场景改为“按 Requirements 阶段确定的写入模式进入画像链路”，同时保留开放问题 #3 为 `defer 到 Requirements`，不再混入已确定的“建议制”口径（`docs/v2.7/proposal.md:56`、`docs/v2.7/proposal.md:60`、`docs/v2.7/proposal.md:110`、`docs/v2.7/proposal.md:206`）。
- 原 P1-2：已关闭
  - 证据：`proposal.md` 已删除“手动映射”假设，改为“匹配成功/未匹配统计 + 修正模板后重新导入”；同时把“ESB 手动映射界面”明确列入 Non-goals，避免 Requirements 隐式扩 scope（`docs/v2.7/proposal.md:48`、`docs/v2.7/proposal.md:61`、`docs/v2.7/proposal.md:96`、`docs/v2.7/proposal.md:122`、`docs/v2.7/proposal.md:133`、`docs/v2.7/proposal.md:147`）。
- 原 P2-1：已关闭
  - 证据：M1、子方案二、P-METRIC-01 已统一为“5 域 12 子字段”基线（`docs/v2.7/proposal.md:45`、`docs/v2.7/proposal.md:77`、`docs/v2.7/proposal.md:160`）。
- 原 P2-2：已关闭
  - 证据：`status.md` 已同步 Proposal 阶段变更摘要、5 项成功指标和当前阶段审查入口 `review_proposal.md`，并注明 Proposal v0.2 已完成第 2 轮复审并收敛（`docs/v2.7/status.md:26`、`docs/v2.7/status.md:34`、`docs/v2.7/status.md:43`、`docs/v2.7/status.md:75`）。

### 结论（第 2 轮）
- P0(open)=0
- P1(open)=0
- P2(open)=0

**复审结论：Proposal 阶段问题已收敛，建议人工确认后进入 Requirements 阶段。**

## 追加复核（第 3 轮，2026-03-12）

### 复核范围
- `status.md` 的 `_review_round` 是否与 Proposal 阶段已发生的审查轮次一致
- `status.md` 摘要/备注中的轮次表述是否与 `review_proposal.md` 最新结论保持同步

### 复核证据
1. `rg -n "^_review_round:|第 2 轮|第2轮|Proposal v0.2 已完成|P0\\(open\\)=0|P1\\(open\\)=0|P2\\(open\\)=0" docs/v2.7/status.md docs/v2.7/review_proposal.md`
2. `sed -n '288,296p' .aicoding/ai_workflow.md`
3. `sed -n '1,30p' .aicoding/templates/status_template.md`

### 复核结果
- 新增 P1-1：`status.md` 的 `_review_round` 仍为 `0`，与 Proposal 阶段已完成 2 轮复审的事实不一致
  - 证据：
    - `review_proposal.md` 已存在“复审（第 2 轮）”且结论为 P0/P1/P2 open=0
    - `status.md` 仍写 `_review_round: 0`，并在摘要/备注中声明“已完成第 2 轮复审并收敛”
    - `ai_workflow.md` 与 `status_template.md` 都要求 `_review_round` 表示“当前阶段审查轮次”，仅在阶段切换时重置为 `0`
  - 风险：
    - `status.md` 作为阶段状态单一真相源时，无法准确反映 Proposal 阶段已发生的审查轮次
    - 后续若同阶段继续修复/复审，3 轮停下复盘和 5 轮硬拦截的计数基线会失真
  - 建议：
    - 将 `_review_round` 回填为当前 Proposal 阶段的真实轮次
    - 同步更新 `status.md` 中所有“第 2 轮”描述，避免与最新审查留痕冲突

### 结论（第 3 轮）
- P0(open)=0
- P1(open)=1
- P2(open)=0

**复核结论：❌ 当前不建议直接以现状进入 Requirements。请先修正 `status.md` 的轮次留痕，再做一轮复审确认。**

---

## 复审（第 4 轮，2026-03-12）

### 复审范围
- 第 3 轮新增问题：`status.md` 的 `_review_round` 与 Proposal 阶段轮次不一致
- `status.md` 摘要/备注中的轮次表述是否已与当前审查结论同步

### 复审证据
1. `rg -n "^_review_round:|第 4 轮|第4轮|Proposal v0.2 已完成|wait_confirm" docs/v2.7/status.md docs/v2.7/review_proposal.md`
2. `sed -n '1,120p' docs/v2.7/status.md`
3. `sed -n '288,296p' .aicoding/ai_workflow.md`

### 复审结果
- 原 P1-1：已关闭
  - 证据：
    - `status.md` 已将 `_review_round` 更新为 `4`，与当前 Proposal 阶段实际审查轮次一致
    - `status.md` 摘要与备注中的“第 2 轮复审”已同步更新为“第 4 轮复审”
    - 当前状态仍保持 `_phase: Proposal` + `_run_status: wait_confirm`，符合“Proposal 已收敛，等待人工确认是否进入 Requirements”的阶段语义

### 结论（第 4 轮）
- P0(open)=0
- P1(open)=0
- P2(open)=0

**复审结论：Proposal 阶段问题已收敛，建议人工确认后进入 Requirements 阶段。**

---

## 复审（第 5 轮，2026-03-13）

### 复审范围
- 针对 `proposal.md` v0.3 重开范围后的 Proposal 阶段补审，确认新增的 6 个内置 Skill、Skill Runtime、Per-System Memory、服务治理/系统清单双导入联动、系统识别/功能点拆解口径是否已形成阶段门禁证据
- Proposal 产物与 `status.md` 摘要中的“系统清单导入联动”口径是否一致
- 利益相关方表是否覆盖本轮新增影响面

### 复审证据
1. `rg -n "文档版本|v0.3|2026-03-13|所有系统画像|所有命中的系统画像|P-DO-06|利益相关方|Expert|expert|系统识别|功能点拆解" docs/v2.7/proposal.md docs/v2.7/review_proposal.md docs/v2.7/status.md docs/v2.7/requirements.md`
2. `nl -ba docs/v2.7/proposal.md | sed -n '56,276p'`
3. `nl -ba docs/v2.7/review_proposal.md | tail -n 40`

### 复审结果
- 新增 P1-1：`review_proposal.md` 尚未覆盖 `proposal.md` v0.3 的重开范围，Proposal 阶段缺少与当前范围匹配的门禁留痕
  - 证据：
    - `proposal.md` 已在 2026-03-13 升级到 v0.3，并新增 6 个内置 Skill、Skill Runtime、Per-System Memory、系统识别/功能点拆解策略等范围
    - `review_proposal.md` 最后一轮仍停留在 2026-03-12 的“第 4 轮”，结论仅覆盖 v0.2 收敛
  - 风险：
    - Proposal 阶段的审查证据无法证明“重开后的范围”已经过门禁
    - 后续 Requirements 虽已推进，但 Proposal 作为上游输入缺少与现状一致的审查闭环
  - 建议修改：
    - 追加一轮针对 v0.3 重开范围的 Proposal 复审记录，并在修复后继续复审直到 P0/P1 收敛
  - 验证方式：
    - 检查 `review_proposal.md` 是否出现 2026-03-13 的新增轮次，并明确覆盖 v0.3 范围
- 新增 P1-2：系统清单导入联动在 Proposal 产物内同时出现“批量更新所有系统画像”和“批量更新所有命中的系统画像”两套口径
  - 证据：
    - `proposal.md` 的 TOP 场景、Skill 描述、In Scope、P-DO-06 仍多处写“所有系统画像”
    - 同一文档的子方案四已经写成“所有命中的系统画像”
    - `requirements.md` 的运行口径也以“所有命中系统画像”为主
  - 风险：
    - 实现范围会在“全量重刷全部画像”与“仅更新命中画像”之间摇摆
    - 性能预算、验收样本和失败处理口径会随之失真
  - 建议修改：
    - Proposal 与 `status.md` 摘要统一改为“批量更新所有命中的系统画像”
  - 验证方式：
    - `rg -n "所有系统画像|所有命中的系统画像" docs/v2.7/proposal.md docs/v2.7/status.md`
- 新增 P2-1：利益相关方表遗漏 Expert 角色，未显式覆盖系统识别和功能点拆解受影响方
  - 证据：
    - Proposal 已把系统识别、功能点拆解和 Memory 读写纳入范围
    - Non-goals 明确继续复用 `admin/PM/expert` 角色
    - 当前利益相关方表仅列出 PM / Admin / 运维
  - 风险：
    - 需求沟通与验收通知容易漏掉只读使用画像、执行结果和 Memory 的专家角色
  - 建议修改：
    - 在 Stakeholders 表补充 Expert 角色及其关注点
  - 验证方式：
    - 检查 `proposal.md` 的 Stakeholders 表是否包含 Expert 行

### 结论（第 5 轮）
- P0(open)=0
- P1(open)=2
- P2(open)=1

**复审结论：❌ 当前 Proposal 产物不通过。先补齐 v0.3 范围的审查留痕，并统一“系统清单导入联动”口径后再复审。**

---

## 复审（第 6 轮，2026-03-13）

### 复审范围
- 第 5 轮新增问题：Proposal v0.3 缺少门禁留痕
- 第 5 轮新增问题：系统清单导入联动口径不一致
- 第 5 轮新增问题：利益相关方遗漏 Expert

### 复审证据
1. `rg -n "文档版本|v0.4|所有系统画像|所有命中的系统画像|P-DO-06|利益相关方|Expert|系统清单导入后的画像联动能力" docs/v2.7/proposal.md docs/v2.7/status.md docs/v2.7/review_proposal.md`
2. `nl -ba docs/v2.7/proposal.md | sed -n '1,280p'`
3. `nl -ba docs/v2.7/status.md | sed -n '24,40p'`

### 修复影响面扫描（REP 步骤 E）
- 已重新全文检索 `所有系统画像|所有命中的系统画像|P-DO-06|system_catalog_skill|Expert|expert`
- 本轮修复仅落在 Proposal 阶段产物：`proposal.md`、`status.md`、`review_proposal.md`
- 当前全局阶段保持 `Requirements`，本轮不回退 `_phase`，仅补齐 Proposal 阶段留痕与口径收敛

### 复审结果
- 原 P1-1：已关闭
  - 证据：`review_proposal.md` 已追加 2026-03-13 的第 5/6 轮记录，Proposal v0.3 重开范围已有与当前口径匹配的审查留痕
- 原 P1-2：已关闭
  - 证据：
    - `proposal.md` 已升级为 v0.4
    - TOP 场景、Skill 描述、In Scope、P-DO-06 统一改为“批量更新所有命中的系统画像”
    - `status.md` 变更摘要同步改为同一口径
- 原 P2-1：已关闭
  - 证据：`proposal.md` Stakeholders 表已补充 Expert 角色，明确其关注系统识别/功能点拆解引用的画像与 Memory 口径

### 结论（第 6 轮）
- P0(open)=0
- P1(open)=0
- P2(open)=0

**复审结论：Proposal 阶段问题已收敛。本轮已为重开后的 Proposal 范围补齐审查闭环；当前全局阶段保持 Requirements，不需要回退。**

---

## 复审（第 7 轮，2026-03-13）

### 复审范围
- 用户新增“系统清单月度更新不得覆盖非空画像”的业务规则后，Proposal 是否已同步
- Proposal 与 Requirements / Status 对“首次初始化、空画像判定、非空跳过、不进入 PM 建议流”的口径是否一致

### 复审证据
1. `rg -n "文档版本|v0.5|首次初始化|空画像|P-DO-06|P-DONT-08|field_sources|ai_suggestions|Memory|系统清单导入" docs/v2.7/proposal.md docs/v2.7/requirements.md docs/v2.7/status.md docs/v2.7/review_proposal.md`
2. `nl -ba docs/v2.7/proposal.md | sed -n '56,285p'`
3. `nl -ba docs/v2.7/requirements.md | sed -n '53,1120p'`

### 修复影响面扫描（REP 步骤 E）
- 已重新全文检索 `首次初始化|空画像|P-DO-06|P-DONT-08|field_sources|ai_suggestions|Memory|系统清单导入`
- 本轮修复落在 `proposal.md`、`requirements.md`、`review_proposal.md`、`review_requirements.md`、`status.md`
- 当前全局阶段保持 `Requirements`，本轮仅补齐 Proposal 对新增业务规则的追溯与门禁留痕

### 复审结果
- 新增 P1-1：Proposal v0.4 仍将系统清单联动定义为“批量更新所有命中画像”，缺少“首次初始化/空画像补写/非空跳过/忽略元数据判空”的限制
  - **证据**：
    - 用户已明确：系统清单每月更新，首次初始化可批量更新且无须 PM 接受建议；后续更新或覆盖导入时，非空画像不得被系统清单内容粗暴更新
    - 旧版 Proposal 仅写“批量更新所有命中的系统画像”，未写空画像判定与非空跳过规则
  - **风险**：
    - Design / Plan / Implementation 会沿用过宽口径，把月度系统清单更新误实现为覆盖式画像回写
    - 需求追溯无法回答“为什么系统清单场景不走 PM 建议接受流”
  - **建议修改**：
    - 将 Proposal 的 TOP 场景、子方案四、In Scope、P-DO-06 同步为“首次初始化或空画像时初始化写入”
    - 新增 `P-DONT-08`，显式禁止系统清单覆盖非空画像，并把空画像判定口径写清
  - **状态**：已修复。
    - `proposal.md` 已升级为 v0.5
    - TOP 场景、子方案四、In Scope、`P-DO-06` 已统一为“初始化空画像或跳过非空画像”
    - 已新增 `P-DONT-08`，明确空画像判定仅看 `profile_data` 下 D1-D5 canonical 字段，忽略 `field_sources`、`ai_suggestions` 与 Memory

### 结论（第 7 轮）
- P0(open)=0
- P1(open)=0
- P2(open)=0

**复审结论：Proposal 阶段问题继续保持收敛。新增业务规则已回写到 Proposal，并与 Requirements / Status 保持一致；当前全局阶段仍为 Requirements。**
