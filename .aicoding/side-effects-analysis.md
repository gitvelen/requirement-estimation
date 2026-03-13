# 框架优化方案的副作用分析

> **生成时间：** 2026-03-11
> **基于方案：** `/root/.claude/plans/stateless-riding-boole.md`

---

## 执行摘要

按照优化方案执行后，会引入**7类副作用**，其中：
- 🔴 **高风险副作用**：3个（需要立即缓解）
- 🟡 **中风险副作用**：2个（需要监控）
- 🟢 **低风险副作用**：2个（可接受）

**核心矛盾：** 用脚本强制执行规则，会让AI"更听话"，但也会让AI"更机械"，可能损失灵活性和创造力。

---

## 副作用1：AI被过度约束，失去灵活性（🔴 高风险）

### 问题描述

**Phase 1.2：强化 CC-7 hook（entry_gate_mode: block）**

当前配置已经是 `entry_gate_mode: block`，但优化方案进一步强调"未读取时**阻止写入**"。

**副作用：**
1. **AI无法快速迭代**：如果AI想先写一个草稿，再回头读文档补充细节，会被阻止
2. **AI无法处理紧急情况**：如果用户说"先快速修个bug，文档稍后补"，AI无法执行
3. **AI无法应对文档缺失**：如果某个阶段的必读文件不存在（如新项目初始化），AI会卡住

### 实战证据

- **requirement-estimation 2026-02-07**："用户反馈多个实现问题，AI在部分问题上质疑用户'文档有说吗'"
- 这说明AI有时需要"先做后补"，而不是"先读后做"

### 触发场景

```
用户："快速修个typo，不用走完整流程"
AI："我需要先读 proposal.md、requirements.md..."
用户："就改一个字，别那么死板"
AI："抱歉，CC-7 hook 阻止我写入，必须先读必读文件"
用户：😤
```

### 缓解方案

**方案A：增加"快速通道"豁免机制**

在 `aicoding.config.yaml` 中增加：
```yaml
# 快速通道：允许跳过入口门禁的场景
entry_gate_quick_pass:
  - typo_fix        # typo修复
  - comment_only    # 仅修改注释
  - emergency_fix   # 紧急修复（用户明确说"紧急"）
```

在 CC-7 hook 中检查：
```bash
# 如果用户在会话中说了"紧急"或"快速"，允许跳过
if echo "$user_message" | rg -qi "紧急|快速|typo|注释"; then
  echo "检测到快速通道关键词，跳过入口门禁"
  exit 0
fi
```

**方案B：改为"延迟校验"而非"阻止写入"**

- AI可以先写入草稿
- 但在阶段推进时，pre-commit 会检查"是否已读必读文件"
- 如果未读，阻止阶段推进，但不阻止草稿写入

**推荐：** 方案B，因为它保留了灵活性，同时确保了质量门禁

---

## 副作用2：证据清单成为"形式主义"（🔴 高风险）

### 问题描述

**Phase 1.5：强化 pre-commit：检查证据清单**

要求 review 文件必须包含"## 证据清单"段落，否则阻断提交。

**副作用：**
1. **AI可能伪造证据**：为了通过门禁，AI可能写一个假的"证据清单"，但实际没有执行命令
2. **证据清单变成"复制粘贴"**：AI可能从模板复制示例，而不是真正执行验证
3. **增加AI负担**：AI需要记住"写完review后还要补证据清单"，容易遗忘

### 实战证据

- **requirement-estimation 2026-02-24**："review 报告给结论但缺少'命令+关键输出+定位信息'"
- 这说明AI确实会忘记写证据，但强制要求后，AI可能会"应付了事"

### 触发场景

```
AI写完 review_design.md：
## 审查结论
P0=0, P1=0，建议进入 Planning

## 证据清单
### 1. REQ追溯覆盖
**命令：** bash -lc '...'
**输出：** ✓ All 23 REQ items traced
（实际上AI没有执行这个命令，只是从模板复制的）

pre-commit：✅ 检测到证据清单，通过
```

### 缓解方案

**方案A：增加"证据真实性"检查**

在 pre-commit 中增加：
```bash
# 检查证据清单中的命令是否可执行
if rg -q "^## 证据清单" "$review_file"; then
  # 提取命令
  commands=$(rg -A5 "^\*\*命令：\*\*" "$review_file" | rg "^bash|^python|^npm" || true)

  if [[ -z "$commands" ]]; then
    echo "⚠️  警告：证据清单中没有可执行命令"
    echo "   请确保证据清单包含实际执行的命令，而不是示例"
  fi
fi
```

**方案B：改为"证据清单可选，但必须说明原因"**

```bash
# 如果没有证据清单，检查是否有说明
if ! rg -q "^## 证据清单" "$review_file"; then
  if rg -q "证据清单省略原因|无需证据清单" "$review_file"; then
    echo "✓ 检测到证据清单省略说明，通过"
  else
    echo "❌ 缺少证据清单，且未说明原因"
    exit 1
  fi
fi
```

**推荐：** 方案A + 方案B 结合，既检查真实性，又允许合理省略

---

## 副作用3：CR遗漏检查误报率高（🔴 高风险）

### 问题描述

**Phase 1.6：强化 pre-commit：检查CR遗漏**

检查"代码变更涉及核心文件，但status.md中无Active CR"时告警。

**副作用：**
1. **误报场景1：重构代码**：重构不改变功能，不需要CR，但会触发告警
2. **误报场景2：修复bug**：小bug修复可能走hotfix，不需要CR，但会触发告警
3. **误报场景3：测试代码**：修改测试文件，不需要CR，但如果测试文件在 `frontend/src/` 下会触发告警
4. **用户疲劳**：频繁告警会让用户习惯性输入 `y`，失去警示作用

### 实战证据

- **requirement-estimation 2026-02-25**："把'收口阶段的小优化'误当成'无需 CR 的临时调整'"
- 这说明"是否需要CR"的判断本身就很模糊，脚本很难准确判断

### 触发场景

```
用户："重构一下这个函数，提取公共逻辑"
AI：修改 frontend/src/pages/UserPage.jsx

pre-commit：
⚠️  警告：代码变更涉及核心文件，但 status.md 中无 Active CR
   变更的核心文件：
     - frontend/src/pages/UserPage.jsx
   是否继续提交？(y/N)

用户：y（第10次输入y，已经麻木）
```

### 缓解方案

**方案A：缩小检查范围，只检查"新增文件"**

```bash
# 只检查新增的核心文件，不检查修改的文件
staged_new_files=$(git diff --cached --name-only --diff-filter=A | rg "frontend/src/pages/|backend/app/api/" || true)

if [[ -n "$staged_new_files" ]]; then
  # 新增核心文件，检查CR
fi
```

**方案B：增加"智能判断"，排除明显不需要CR的场景**

```bash
# 检查commit message是否包含"refactor/test/chore"
commit_msg=$(git log -1 --pretty=%B 2>/dev/null || echo "")

if [[ "$commit_msg" =~ ^(refactor|test|chore|docs): ]]; then
  echo "检测到 refactor/test/chore/docs 类型提交，跳过CR检查"
  exit 0
fi
```

**方案C：改为"建议"而非"告警"**

```bash
echo ""
echo "💡 提示：代码变更涉及核心文件，建议确认是否需要创建 CR"
echo "   如果是新功能/优化，请创建 CR"
echo "   如果是重构/bug修复/测试，可以跳过"
echo ""
# 不询问，直接通过
```

**推荐：** 方案B + 方案C 结合，减少误报，降低用户疲劳

---

## 副作用4：规范索引表格成为"又一个需要维护的地方"（🟡 中风险）

### 问题描述

**Phase 1.1：在 `STRUCTURE.md` 开头加"规范索引"表格**

增加了一个5行的表格，列出"单一真相源"。

**副作用：**
1. **维护成本**：如果某个规则的位置变了（如 `ai_workflow.md:3-40` 改为 `ai_workflow.md:5-50`），需要同步更新表格
2. **遗忘风险**：框架维护者可能忘记更新表格，导致表格过时
3. **信任问题**：如果表格过时，AI会不信任表格，反而增加困惑

### 缓解方案

**方案A：用脚本自动生成表格**

```bash
# scripts/generate-canonical-sources-table.sh
#!/bin/bash

echo "| 领域 | 唯一真相源 | 包含内容 |"
echo "|------|-----------|---------|"
echo "| 工作流规则 | \`ai_workflow.md\` | 变更分级、阶段推进、收敛判定、债务管理 |"
# ... 其他行
```

在 pre-commit 中检查：
```bash
# 如果 ai_workflow.md 有变更，提示更新表格
if git diff --cached --name-only | rg -q "ai_workflow.md"; then
  echo "⚠️  提示：ai_workflow.md 有变更，请检查是否需要更新 STRUCTURE.md 的规范索引表格"
fi
```

**方案B：表格只列"文件名"，不列"行号"**

```markdown
| 领域 | 唯一真相源 | 包含内容 |
|------|-----------|---------|
| 工作流规则 | `ai_workflow.md` | 变更分级、阶段推进、收敛判定、债务管理 |
| 状态机语义 | `ai_workflow.md` | Major/Minor/Hotfix、wait_confirm语义 |
```

这样即使行号变了，表格也不需要更新。

**推荐：** 方案B，简单有效

---

## 副作用5：共享验证函数库增加调试难度（🟡 中风险）

### 问题描述

**Phase 2.4：提取共享验证函数库**

将 `pre-commit` 和 `pre-write-dispatcher.sh` 中的验证函数提取到 `scripts/lib/validation.sh`。

**副作用：**
1. **调试困难**：如果验证函数出错，需要跳转到 `validation.sh` 查看，增加调试路径
2. **错误信息不清晰**：如果 `validation.sh` 中的函数返回错误，调用方可能不知道具体哪里出错
3. **依赖关系复杂**：`pre-commit` 和 `pre-write-dispatcher.sh` 都依赖 `validation.sh`，如果 `validation.sh` 有bug，两个脚本都会受影响

### 缓解方案

**方案A：在验证函数中增加详细的错误信息**

```bash
validate_minor_review_file() {
  local file="$1"

  if [[ ! -f "$file" ]]; then
    echo "❌ 验证失败：文件不存在 - $file" >&2
    return 1
  fi

  if ! rg -q 'REVIEW-SUMMARY-BEGIN' "$file"; then
    echo "❌ 验证失败：缺少 REVIEW-SUMMARY-BEGIN - $file" >&2
    return 1
  fi

  if ! rg -q 'REVIEW_RESULT:[[:space:]]*pass' "$file"; then
    echo "❌ 验证失败：REVIEW_RESULT 不是 pass - $file" >&2
    return 1
  fi

  return 0
}
```

**方案B：增加单元测试**

```bash
# scripts/tests/validation.test.sh
#!/bin/bash

source "$(dirname "$0")/../lib/validation.sh"

# 测试 validate_minor_review_file
test_validate_minor_review_file() {
  # 创建测试文件
  echo "REVIEW-SUMMARY-BEGIN" > /tmp/test_review.md
  echo "REVIEW_RESULT: pass" >> /tmp/test_review.md
  echo "REVIEW-SUMMARY-END" >> /tmp/test_review.md

  # 测试
  if validate_minor_review_file /tmp/test_review.md; then
    echo "✓ test_validate_minor_review_file passed"
  else
    echo "✗ test_validate_minor_review_file failed"
    exit 1
  fi
}

test_validate_minor_review_file
```

**推荐：** 方案A + 方案B 结合

---

## 副作用6：文档精简可能丢失重要上下文（🟢 低风险）

### 问题描述

**Phase 3：文档精简（可选）**

将 `ai_workflow.md` 从400行降至250行，`phases/00-change-management.md` 从222行降至80行。

**副作用：**
1. **信息丢失**：删除的内容可能包含重要的边界情况说明
2. **AI理解不完整**：精简后的文档可能过于简洁，AI无法理解完整语义
3. **新手不友好**：新加入的框架维护者可能看不懂精简后的文档

### 缓解方案

**方案A：将删除的内容移到"参考文档"**

```
.aicoding/
├── ai_workflow.md（精简版，250行）
└── docs/
    └── ai_workflow_reference.md（完整版，400行）
```

AI默认读精简版，需要时再读完整版。

**方案B：在精简版中增加"详见XXX"链接**

```markdown
## Hotfix 极速流程

> 核心原则：只解决紧急问题，不引入新范围。
> 详细说明见 `docs/ai_workflow_reference.md:13-40`

适用边界：
1. staged 文件数 <= 3
2. 不触碰 REQ-C
3. 不涉及 API/DB schema/权限安全变更
```

**推荐：** 方案B，保留链接，按需查阅

---

## 副作用7：过度依赖脚本，降低AI主动性（🟢 低风险）

### 问题描述

**整体方案：用脚本强制，不用文档劝说**

**副作用：**
1. **AI变成"执行机器"**：AI只会"按脚本要求做"，不会"主动思考为什么这样做"
2. **AI失去创造力**：AI不会提出"这个规则不合理，我有更好的方案"
3. **AI无法应对新场景**：如果遇到脚本没有覆盖的场景，AI会不知所措

### 实战证据

- **aiquant R6**："任何实现工作启动前，必须先通读 proposal.md 全文并以其作为工作基线；逐项对照执行，**主动推进**"
- 这说明框架期望AI"主动推进"，而不是"被动执行"

### 缓解方案

**方案A：在文档中保留"为什么"的说明**

```markdown
## 🔴 阶段入口协议（MUST，CC-7硬校验）

> **为什么需要这个规则：**
> 实战证据显示，AI经常"不通读就动手"，导致遗漏系统性需求（见 aiquant R6、requirement-estimation 2026-02-07）。
> 强制读取必读文件，可以确保AI理解完整上下文。

> **核心规则：** 进入任何阶段后、开始产出前，**必须先读取**该阶段定义的必读文件。
```

**方案B：允许AI"挑战规则"**

在 `CLAUDE.md` 中增加：
```markdown
## 核心原则

1. 先澄清再动手：目标/边界/约束/风险/验收，不清楚先问；范围变更必须说明代价并重新确认。
2. **质疑不合理规则**：如果你认为某个规则不合理，可以向用户说明原因，建议调整。
3. 偏了就停：执行中发现方向偏离、连续失败、或复杂度超预期，立即停下重新规划，不硬推。
```

**推荐：** 方案A + 方案B 结合

---

## 副作用总结表

| 副作用 | 风险等级 | 触发概率 | 影响范围 | 缓解难度 | 推荐缓解方案 |
|--------|---------|---------|---------|---------|-------------|
| 1. AI被过度约束 | 🔴 高 | 高（50%） | 所有阶段 | 中 | 改为"延迟校验" |
| 2. 证据清单形式主义 | 🔴 高 | 中（30%） | Review阶段 | 中 | 检查真实性 + 允许省略 |
| 3. CR遗漏检查误报 | 🔴 高 | 高（60%） | 代码提交 | 易 | 智能判断 + 改为提示 |
| 4. 规范索引表格维护 | 🟡 中 | 低（10%） | STRUCTURE.md | 易 | 不列行号 |
| 5. 共享库调试困难 | 🟡 中 | 低（20%） | 脚本调试 | 中 | 详细错误信息 + 单元测试 |
| 6. 文档精简丢失上下文 | 🟢 低 | 低（10%） | 文档理解 | 易 | 保留链接 |
| 7. 过度依赖脚本 | 🟢 低 | 中（30%） | AI主动性 | 易 | 保留"为什么" + 允许挑战 |

---

## 建议行动

### 立即执行（Phase 1）

1. ✅ 执行 Phase 1.1-1.3（文档改动）
2. ⚠️ **暂缓** Phase 1.4（CC-7 hook改为block）→ 改为"延迟校验"
3. ⚠️ **修改** Phase 1.5（证据清单检查）→ 增加真实性检查 + 允许省略
4. ⚠️ **修改** Phase 1.6（CR遗漏检查）→ 增加智能判断 + 改为提示

### 谨慎执行（Phase 2-3）

5. ✅ 执行 Phase 2.1（删除债务规则重复）
6. ✅ 执行 Phase 2.2-2.3（统一命名）
7. ⚠️ **增强** Phase 2.4（共享验证库）→ 增加详细错误信息 + 单元测试
8. ⚠️ **修改** Phase 3（文档精简）→ 保留链接到完整版

### 补充措施

9. 在所有强制规则中增加"为什么"的说明
10. 在 `CLAUDE.md` 中增加"允许AI挑战规则"的原则
11. 建立"副作用监控"机制，定期检查误报率和用户疲劳度

---

## 结论

**核心矛盾：** 用脚本强制执行规则，会让AI"更听话"，但也会让AI"更机械"。

**平衡之道：**
- ✅ 对"明确可判定"的规则（如：文件存在性、格式正确性），用脚本强制
- ⚠️ 对"需要判断"的规则（如：是否需要CR、证据是否真实），用脚本提示 + AI判断
- ❌ 对"需要创造力"的规则（如：设计方案、实现方式），不用脚本约束

**最终建议：** 执行 Phase 1-2，但需要根据上述缓解方案调整；暂缓 Phase 3，观察 Phase 1-2 的效果后再决定。
