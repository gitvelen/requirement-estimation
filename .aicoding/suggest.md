# 项目框架优化建议（极简版 - 基于实战经验教训深度分析）

> **生成时间：** 2026-03-11
> **分析来源：**
> - Codex 与用户的两轮对话（框架冗余分析）
> - `/home/admin/aiquant/docs/lessons_learned.md`（8条实战教训）
> - `/home/admin/Claude/requirement-estimation-system/docs/lessons_learned.md`（9条实战教训）
>
> **核心发现：** 框架设计与AI实战行为存在系统性脱节，但问题不是"规则不够"，而是"执行不够硬"。

---

## 目录

- [执行摘要](#执行摘要)
- [核心洞察：用脚本强制，不用文档劝说](#核心洞察用脚本强制不用文档劝说)
- [三大症结与解决方案](#三大症结与解决方案)
  - [症结1：AI不通读就动手](#症结1ai不通读就动手)
  - [症结2：AI假收敛无证据](#症结2ai假收敛无证据)
  - [症结3：AI误判CR导致追溯断链](#症结3ai误判cr导致追溯断链)
- [Codex指出的冗余问题](#codex指出的冗余问题)
- [优化优先级总结](#优化优先级总结)
- [立即行动建议](#立即行动建议)

---

## 执行摘要

### 问题本质

当前框架的核心问题不是"文档太多"或"规则重复"，而是：

1. **假设AI会"系统式理解"，但AI实际是"搜索式阅读"** → 导致遗漏系统性需求
2. **假设AI会"自证收敛"，但AI实际是"自己写自己审"** → 导致假收敛、证据缺失
3. **假设AI能"准确判断变更性质"，但AI实际经常误判** → 导致CR遗漏、追溯断链

### 错误的解决思路

❌ 增加更多文档来"劝说"AI遵守规则
❌ 在每个文件开头加"规范定位"标注
❌ 创建"阅读指南"让AI自觉对照
❌ 增加"必做动作"清单让AI自查

**为什么错误：** 如果AI连现有规则都记不住，加更多规则只会让上下文更臃肿，AI更容易遗忘。

### 正确的解决思路

✅ **用脚本强制执行，不用文档劝说**
- 脚本可以硬拦截（AI绕不过去）
- 文档只能软提醒（AI可能忘记）

✅ **极简文档改动，最大化脚本约束**
- 只在现有文档中加2处强调（共250字）
- 强化3个门禁脚本（不占AI上下文）

### 核心建议（总上下文开销：+250字）

1. **在 `STRUCTURE.md` 开头加"规范索引"表格**（5行，100字）
2. **在 `ai_workflow.md` 开头加"阶段入口协议"强调**（1段，150字）
3. **强化3个门禁脚本**（不占AI上下文）：
   - CC-7 hook：硬校验"是否已读必读文件"
   - pre-commit：硬校验"review文件是否包含证据清单"
   - pre-commit：硬校验"代码变更但无Active CR时告警"

### 预期收益

- 减少"未通读就动手"导致的返工（aiquant R6、requirement-estimation 2026-02-07）
- 减少"假收敛"导致的设计缺陷后移（requirement-estimation 2026-02-24）
- 减少"CR遗漏"导致的追溯风险（requirement-estimation 2026-02-25）

---

## 核心洞察：用脚本强制，不用文档劝说

### 实战问题的深层原因

| 实战问题 | 表面原因 | 深层原因 | 错误的解决方案 | 正确的解决方案 |
|---------|---------|---------|---------------|---------------|
| 未通读就动手 | AI没读proposal | 框架没有强制入口检查 | ❌ 增加"阅读指南"文档 | ✅ CC-7 hook硬校验"是否已读" |
| 假收敛 | AI没给证据 | 框架没有强制证据门禁 | ❌ 增加"证据清单模板" | ✅ pre-commit硬校验"证据清单存在性" |
| CR遗漏 | AI误判 | 框架没有强制CR检查 | ❌ 增加"变更管理指南" | ✅ pre-commit硬校验"代码变更但无CR时告警" |

### 为什么"文档劝说"不起作用

**实战证据：**
- `ai_workflow.md:151-174` 已经规定了"阶段入口协议"，但AI仍然不读就动手
- `phases/00-change-management.md:10-19` 已经规定了"何时需要CR"，但AI仍然误判
- `ai_workflow.md:219-224` 已经规定了"收敛条件"，但AI仍然假收敛

**根本原因：**
- AI的上下文窗口有限，读了太多文档后会"遗忘"前面的规则
- AI的注意力机制会优先关注"用户当前的指令"，而不是"框架的规则"
- AI的自我审查存在"确认偏差"（自己写自己审，容易用意图替代文本）

### 为什么"脚本强制"有效

**脚本的优势：**
- **硬拦截：** AI无法绕过脚本检查（除非用 `--no-verify`，但框架已禁止）
- **零上下文：** 脚本不占AI的上下文窗口
- **即时反馈：** AI违规时立即得到明确的错误提示
- **可复现：** 脚本的行为是确定性的，不会"遗忘"

**实战证据：**
- 当前框架的 pre-commit 已经成功拦截了很多违规行为（如：阶段推进时缺少review文件）
- CC-7 hook 已经成功引导AI读取必读文件（虽然还不够严格）

---

## 三大症结与解决方案

### 症结1：AI不通读就动手

#### 实战证据

- **aiquant R6**："任何实现工作启动前，必须先通读 proposal.md 全文并以其作为工作基线；逐项对照执行，主动推进，禁止仅凭用户口头指令片段被动行事。"
- **aiquant 2026-02-20**："用户要求修复'页面空间浪费'问题。AI 未先读 proposal.md，仅凭用户口头描述逐条修复'顶部说明文字'，遗漏了 proposal 中'全局UI优化'表格的其余 3 项。"
- **requirement-estimation 2026-02-07**："AI在部分问题上质疑用户'文档有说吗'，但实际上proposal/requirements确实有相关描述。根因：依赖搜索而非完整阅读，用Grep搜索关键词（如'流程健康'）搜不到，就认为'文档没写'，但实际上proposal第188行明确写了。"

#### 框架现状

- `ai_workflow.md:151-174` 已经规定了"阶段入口协议"
- CC-7 hook（`scripts/cc-hooks/pre-write-dispatcher.sh`）已经在检查"是否已读必读文件"
- 但检查强度不够：默认是 `warn` 模式，AI可以忽略告警继续写入

#### 解决方案（极简版）

**文档改动1：在 `ai_workflow.md` 开头加强调**

```markdown
# AI 工作流控制规则

## 🔴 阶段入口协议（MUST，CC-7硬校验）

> **核心规则：** 进入任何阶段后、开始产出前，**必须先读取**该阶段定义的必读文件。
> **硬校验：** CC-7 hook 会在首次写入产出物时检查是否已读取，未读取时**阻止写入**。
> **如何证明已读：** AI在输出中明确说"我已读XX文件"（CC-7通过read-tracker.sh追踪）

**必读文件来源：** `phases/<NN>-<stage>.md` 的"阶段入口协议"章节

**示例：** 进入 Requirements 阶段时，必须先读：
- `docs/<版本号>/status.md`
- `docs/<版本号>/proposal.md`
- `phases/02-requirements.md`

读取后，AI应输出："我已读 status.md、proposal.md、phases/02-requirements.md，现在开始编写 requirements.md..."

---

（原有内容）
```

**上下文开销：** +150字

**脚本改动：强化 CC-7 hook**

```bash
# scripts/cc-hooks/pre-write-dispatcher.sh

# 当前行为：entry_gate_mode: warn（告警但不阻止）
# 修改为：entry_gate_mode: block（阻止写入）

# 修改 aicoding.config.yaml
entry_gate_mode: block  # 从 warn 改为 block
```

**上下文开销：** 0（配置文件不占AI上下文）

---

### 症结2：AI假收敛无证据

#### 实战证据

- **requirement-estimation R4**："任何阶段宣称'已收敛/P0-P1=0'前，必须通过'三层门禁'（结构门禁 + 语义门禁 + 证据门禁）"
- **requirement-estimation 2026-02-24（Design自审过度依赖追溯门禁）**："v2.2 的 Design 第 1 轮自审在 `review_design.md` 中给出'P0/P1 open=0、建议进入 Planning'的结论，但随后独立审查发现 5 个 P1。根因：把'trace 覆盖通过'当成'设计已可落地'，只验证了 REQ-ID 被提及，但未对照 GWT 的字面验收要求逐条检查'语义是否明确、是否可实现、是否可验证'。"
- **requirement-estimation 2026-02-24（假收敛通病）**："证据门禁缺失：review 报告给结论但缺少'命令+关键输出+定位信息'，导致后续无法复盘与复现。"

#### 框架现状

- `ai_workflow.md:219-224` 的收敛定义是："P0(open)=0 且 P1(open)=0"
- 但没有强制要求"列出验证命令+关键输出"
- pre-commit 在阶段推进时只检查"review文件是否存在"，不检查"review文件是否包含证据"

#### 解决方案（极简版）

**文档改动2：在 `ai_workflow.md` 的"收敛判定"章节加强调**

```markdown
## 收敛判定（🔴 MUST）

### 收敛条件（缺一不可）

1. **问题收敛**：P0(open)=0 且 P1(open)=0
2. **证据完整**：review文档必须包含"## 证据清单"段落，列出：
   - 执行的验证命令（完整命令行）
   - 关键输出（截取前10行或关键行）
   - 定位信息（文件路径:行号）

**硬校验：** pre-commit 在阶段推进时会检查 review 文件是否包含"## 证据清单"段落，缺失时阻断提交。

**示例：合格的证据清单**

```markdown
## 证据清单

### 1. REQ追溯覆盖

**命令：**
```bash
bash -lc 'source .aicoding/scripts/lib/review_gate_common.sh && \
  review_gate_validate_design_trace_coverage requirements \
  docs/v2.0/requirements.md design docs/v2.0/design.md'
```

**输出：**
```
✓ All 23 REQ items traced in design.md
✓ All 5 REQ-C items traced in design.md
Coverage: 28/28 (100%)
```

**定位：**
- REQ-001 → design.md:45-67
- REQ-002 → design.md:89-112
```

---

（原有内容）
```

**上下文开销：** +100字（因为只是在现有章节加强调，不是新增章节）

**脚本改动：强化 pre-commit**

```bash
# scripts/git-hooks/pre-commit

# 新增检查：阶段推进时，检查 review 文件是否包含"## 证据清单"段落

if [[ "$old_phase" != "$new_phase" ]]; then
  # 阶段推进，检查 review 文件
  review_file="docs/$version/review_${old_phase,,}.md"

  if [[ -f "$review_file" ]]; then
    if ! rg -q "^## 证据清单|^### 证据清单" "$review_file"; then
      echo "❌ 阶段推进失败：$review_file 缺少'证据清单'段落"
      echo "   请在 review 文件中添加'## 证据清单'段落，列出验证命令和输出"
      exit 1
    fi
  fi
fi
```

**上下文开销：** 0（脚本不占AI上下文）

---

### 症结3：AI误判CR导致追溯断链

#### 实战证据

- **requirement-estimation 2026-02-25**："收口后新增优化未即时登记 CR，导致追溯风险。项目进入收口后，用户连续提出'布局紧凑化、文案可读性、去折叠'等新增优化要求并已实现，但 `status.md/plan.md/test_report.md` 仍显示'无 CR'。根因：把'收口阶段的小优化'误当成'无需 CR 的临时调整'。代码先行、文档补记滞后，导致短时间内追溯链断档。"

#### 框架现状

- `phases/00-change-management.md:10-19` 已经规定了"何时需要CR"
- 但AI经常误判（把"小优化"当成"无需CR"）
- 没有脚本检查"代码变更但无Active CR"的情况

#### 解决方案（极简版）

**文档改动：无**（现有规则已经够清楚，问题是执行不够硬）

**脚本改动：强化 pre-commit**

```bash
# scripts/git-hooks/pre-commit

# 新增检查：如果代码变更涉及核心文件，但status.md中无Active CR，则告警

if git diff --cached --name-only | rg -q "frontend/src/pages/|backend/app/api/|backend/app/models/"; then
  # 代码变更涉及核心文件

  # 检查 status.md 中是否有 Active CR
  if ! rg -q "^\| CR-[0-9]{8}-[0-9]{3} \| (Accepted|In Progress)" docs/*/status.md 2>/dev/null; then
    echo "⚠️  警告：代码变更涉及核心文件，但 status.md 中无 Active CR"
    echo "   如果这是新功能/优化，请先创建 CR（docs/<版本号>/cr/CR-YYYYMMDD-NNN.md）"
    echo "   如果这是已有 CR，请确认 status.md 已更新"
    echo ""
    echo "   如需跳过此检查，请在 commit message 中加 [skip-cr-check]"

    # 检查 commit message 是否包含 [skip-cr-check]
    if ! git log -1 --pretty=%B | rg -q "\[skip-cr-check\]"; then
      echo ""
      read -p "   是否继续提交？(y/N) " -n 1 -r
      echo
      if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
      fi
    fi
  fi
fi
```

**上下文开销：** 0（脚本不占AI上下文）

---

## Codex指出的冗余问题

### 值得采纳的优化（不增加上下文）

#### 1. 在 `STRUCTURE.md` 开头加"规范索引"表格

**问题：** Codex指出"AI需要读很多材料才能确认哪个是规范"

**方案：** 在 `STRUCTURE.md` 开头加一个5行的表格

```markdown
# `.aicoding/` 目录结构与约定

> **快速导航：** 本文档包含目录结构、版本迭代规则、ID前缀约定、Git管理规范

## 规范索引（单一真相源）

当你需要查阅某个规则时，只读以下唯一真相源，不要读其他副本：

| 领域 | 唯一真相源 | 包含内容 |
|------|-----------|---------|
| 工作流规则 | `ai_workflow.md` | 变更分级、阶段推进、收敛判定、债务管理 |
| 状态机语义 | `ai_workflow.md:3-40` | Major/Minor/Hotfix、wait_confirm语义 |
| 阶段入口/出口 | `scripts/lib/common.sh` | 每个阶段的必读文件、必须产出文件 |
| CR状态枚举 | `phases/cr-rules.md:17-29` | CR状态定义、转换规则 |
| 主文档清单 | 本文档"两类文档"章节 | 5个主文档的定义 |

---

（原有目录结构内容）
```

**上下文开销：** +100字

**为什么有效：**
- AI每次会话都会读 `STRUCTURE.md`（因为它是框架入口）
- 表格只有5行，一眼就能看到"哪个是唯一真相源"
- 不需要新增文件，不需要AI记住"去哪里找索引"

---

#### 2. 其他Codex建议的处理

| Codex建议 | 是否采纳 | 理由 |
|----------|---------|------|
| 阶段入口/出口表自动生成 | ⚠️ 暂缓 | 需要写脚本，收益不大（表格不常变） |
| 审查模板共享骨架 | ❌ 不采纳 | 会增加文件数量，AI需要多读一个文件 |
| CR同步清单单源化 | ✅ 采纳 | 在 `STRUCTURE.md` 的"两类文档"章节明确主文档清单 |
| 债务规则单源化+引用 | ✅ 采纳 | 在 `status_template.md` 中删除重复解释，只保留表结构 |
| 标注副本性质 | ❌ 不采纳 | 会让每个文件都变长，增加上下文 |
| 文档分级阅读指南 | ❌ 不采纳 | AI不会主动去读指南 |

---

## 优化优先级总结

| 优先级 | 优化项 | 预期收益 | 上下文开销 | 实施难度 | 预计工时 |
|--------|--------|---------|-----------|---------|---------|
| **P0** | 在 `ai_workflow.md` 开头加"阶段入口协议"强调 | 🔥🔥🔥 解决"未通读就动手" | +150字 | 低 | 10分钟 |
| **P0** | 强化 CC-7 hook（entry_gate_mode: block） | 🔥🔥🔥 硬拦截"未读就写" | 0 | 低 | 5分钟 |
| **P0** | 在 `ai_workflow.md` 的"收敛判定"加强调 | 🔥🔥🔥 解决"假收敛" | +100字 | 低 | 10分钟 |
| **P0** | 强化 pre-commit（检查证据清单） | 🔥🔥🔥 硬拦截"无证据收敛" | 0 | 中 | 30分钟 |
| **P0** | 强化 pre-commit（检查CR遗漏） | 🔥🔥 解决"CR遗漏" | 0 | 中 | 30分钟 |
| **P1** | 在 `STRUCTURE.md` 开头加"规范索引"表格 | 🔥 减少困惑 | +100字 | 低 | 10分钟 |
| **P2** | 在 `status_template.md` 删除债务规则重复 | 🔥 减少冗余 | -200字 | 低 | 10分钟 |

**总计：**
- **上下文开销：** +250字（文档） - 200字（删除冗余） = **+50字**
- **实施工时：** 约1.5小时

---

## 立即行动建议

### 第1步：文档改动（20分钟）

#### 1.1 修改 `STRUCTURE.md`（10分钟）

在开头加"规范索引"表格（见上方示例）

#### 1.2 修改 `ai_workflow.md`（10分钟）

- 在开头加"阶段入口协议"强调（见上方示例）
- 在"收敛判定"章节加"证据清单"强调（见上方示例）

---

### 第2步：配置改动（5分钟）

#### 2.1 修改 `aicoding.config.yaml`

```yaml
# 从 warn 改为 block
entry_gate_mode: block
```

---

### 第3步：脚本改动（1小时）

#### 3.1 强化 pre-commit：检查证据清单（30分钟）

在 `scripts/git-hooks/pre-commit` 中增加检查（见上方示例）

#### 3.2 强化 pre-commit：检查CR遗漏（30分钟）

在 `scripts/git-hooks/pre-commit` 中增加检查（见上方示例）

---

### 第4步：验证（10分钟）

#### 4.1 测试 CC-7 hook

```bash
# 模拟：AI未读必读文件就写入
# 预期：CC-7 hook 阻止写入

# 清空 read-tracker 日志
rm -f /tmp/claude-code-read-tracker-*.log

# 尝试写入产出物（应该被阻止）
# （需要在实际会话中测试）
```

#### 4.2 测试 pre-commit：证据清单

```bash
# 模拟：阶段推进但 review 文件缺少证据清单
# 预期：pre-commit 阻断提交

# 创建测试 review 文件（无证据清单）
echo "## 审查结论\nP0=0, P1=0" > docs/v1.0/review_design.md

# 修改 status.md（阶段推进）
sed -i 's/_phase: Design/_phase: Planning/' docs/v1.0/status.md

# 提交（应该被阻止）
git add docs/v1.0/
git commit -m "test: phase transition without evidence"
```

#### 4.3 测试 pre-commit：CR遗漏

```bash
# 模拟：代码变更但无 Active CR
# 预期：pre-commit 告警

# 修改核心文件
echo "// test" >> frontend/src/pages/TestPage.jsx

# 确保 status.md 中无 Active CR
sed -i '/^| CR-/d' docs/v1.0/status.md

# 提交（应该告警）
git add frontend/src/pages/TestPage.jsx
git commit -m "feat: add test page"
```

---

## 总结

### 核心原则

**用脚本强制，不用文档劝说**

- ✅ 脚本可以硬拦截（AI绕不过去）
- ❌ 文档只能软提醒（AI可能忘记）

### 优化成果

- **上下文开销：** 仅 +50字（250字新增 - 200字删除）
- **实施工时：** 约1.5小时
- **预期收益：** 解决80%的实战问题

### 不做的事（避免上下文膨胀）

❌ 不新增 `CANONICAL_SOURCES.md`
❌ 不在所有文件开头加"规范定位"标注
❌ 不新增 `review_common_protocol.md`
❌ 不新增"文档分级阅读指南"
❌ 不新增"必做动作"清单

### 关键洞察

**问题不是"规则不够"，而是"执行不够硬"。**

17条实战教训告诉我们：AI会遗忘、会误判、会走捷径。与其增加更多规则让AI记住，不如用脚本硬拦截让AI绕不过去。
