# Hooks 方案：程序化质量门禁

## 1. 问题背景

当前框架的所有质量规则（阶段门禁、CR 追溯、文档一致性等）完全依赖 AI 自觉执行文本指令。实际开发中 AI 会跳过规则、遗漏检查，导致交付质量不稳定。

**核心矛盾**：规则写得再详细，如果没有程序化强制执行，就只是建议。

## 2. 设计约束

| 约束 | 说明 |
|------|------|
| 双工具兼容（AI 自动期） | Phase 03-06 同时使用 Claude Code 和 Codex，Git hooks 必须对两者都生效 |
| Codex 无 hooks 机制 | Codex 仅支持 AGENTS.md 文本规则 + sandbox 隔离，不支持 Claude Code 的 PreToolUse/PostToolUse |
| 最大公约数 = Git hooks | `.git/hooks/` 是唯一对 Claude Code 和 Codex 都生效的程序化执行点 |
| Claude Code hooks 全阶段生效 | CC hooks 不再限于 Phase 00-02，CC-3/CC-4/CC-6/CC-7/CC-7b 全阶段生效，CC-8 在 Phase 03-06 生效 |
| `--no-verify` 可绕过 | Git hooks 可被 `--no-verify` 跳过，但仅影响 pre-commit 和 commit-msg，post-commit 不受影响 |
| `.git/hooks/` 不被 git 跟踪 | 需要安装脚本，每次 clone 后手动执行 |

## 3. 架构决策：双层 hooks 体系

用户指挥多个 AI 工具（多个 Claude、Codex 等）协作开发，本方案默认不依赖 CI（可选启用）。根据阶段特征采用两层互补的 hooks 体系：

```
┌─────────────────────────────────────────────────────────────────┐
│                    Claude Code Hooks 层                          │
│           （全阶段生效，Phase 00-02 + Phase 03-07）              │
│                                                                  │
│  拦截 AI 的实时工具调用（Write/Edit/Read/Stop/SessionStart）     │
│  9 个 hooks：流程守卫 6 个 + 产出物校验 2 个 + 追踪 1 个       │
│  只对 Claude Code 生效                                           │
├─────────────────────────────────────────────────────────────────┤
│                      Git Hooks 层                                │
│                （全阶段通用，全工具兼容）                         │
│                                                                  │
│  拦截 commit 动作                                                │
│  硬拦截 7 个（pre-commit / commit-msg，含交付关口条件拦截+出口门禁）│
│  软警告 21 个（post-commit）                                     │
│  对 Claude Code 和 Codex 都生效                                  │
└─────────────────────────────────────────────────────────────────┘
```

两层的关系是**互补而非替代**：
- Claude Code hooks 管"AI 正在做什么"（实时行为）
- Git hooks 管"AI 提交了什么"（落盘结果）

### hooks 的定位原则

hooks 只做**流程守卫和结构校验**，不做内容质量判断：

| hooks 该管 | hooks 不该管 |
|-----------|-------------|
| 流程是否被遵守（阶段门禁、暂停机制、文件作用域） | 内容质量好不好（proposal 写得深不深、需求够不够细） |
| 结构是否完整（必填章节是否存在、GWT 是否有） | 语义是否正确（需求有没有矛盾、术语是否一致） |
| 上下文是否充分（AI 是否知道当前阶段） | 对话是否充分（AI 有没有深入追问用户） |

质量判断是人和 review 的职责。hooks 只确保"该走的流程走了、该有的东西有了"。

**无 CI/PR 时**：本方案以本地 hooks 作为最小成本门禁（注意：`pre-commit` 可被 `--no-verify` 绕过）。

**启用 CI/PR 时（推荐）**：将“门禁最终裁决”上收到 CI（如 GitHub Actions）。保护分支要求 Required checks 全绿才允许 merge；本地 hooks 仅作为开发者预检/提速。

> **GitHub 配置建议**：
> - 对 `main`/`master` 启用 Branch protection：Require PR + Require status checks
> - Required check 选择：`Quality Gates / quality-gates`

> **前置动作（🔴 MUST）**：在 AGENTS.md.template 的"Git 授权边界"中补充：`--no-verify` 必须用户明确授权，AI 不得自行使用。本方案依赖该文本层约束。

---

## 4. Claude Code Hooks：全阶段流程守卫（9 个）

Claude Code hooks 覆盖全部阶段（Phase 00-07），利用其 hooks 机制对 AI 的实时工具调用做程序化检查。Phase 00-02（人工介入期）有额外的阶段推进拦截和 Stop 门禁；Phase 03-06（AI 自动期）有阶段入口/出口门禁。

配置位置：`.claude/settings.json`（项目级）或 `.claude/settings.local.json`（本地不提交）。

### 4.1 设计原则

- **只管流程，不管质量**：检查结构和流程合规性，不判断内容好坏
- **确定性优先**：只做正则/文件存在性等确定性检查，避免语义判断导致误报
- **PreToolUse 拦截 vs PostToolUse 反馈**：破坏性操作（覆盖 review、推进阶段）用 PreToolUse 阻止；可修复的缺陷（缺章节）用 PostToolUse 反馈给 AI 自动补充
- **静默通过**：检查通过时 exit 0 无输出，不干扰正常工作流

### 4.1.1 阻断协议（🔴 MUST）

不同事件类型使用不同的阻断方式，这是 Claude Code 的官方协议：

| 事件 | 阻断方式 | 说明 |
|------|---------|------|
| **PreToolUse** | `exit 2` + stderr 消息 | stderr 内容反馈给 AI；工具调用被阻止 |
| **PostToolUse** | `exit 0` + JSON `{"decision":"block","reason":"..."}` | 工具已执行完毕，reason 反馈给 AI 做自我修正 |
| **Stop** | `exit 0` + JSON `{"decision":"block","reason":"..."}` | 阻止 AI 停止，reason 告知 AI 继续工作的原因 |
| **SessionStart** | 仅注入上下文，不阻断 | `exit 0` + JSON `{"hookSpecificOutput":{"additionalContext":"..."}}` |

> **注意**：PreToolUse 的 JSON 阻断使用 `hookSpecificOutput.permissionDecision: "deny"`（非顶层 `decision`），
> 但 `exit 2` + stderr 更简洁且效果相同，本方案统一使用 `exit 2`。

### 4.1.2 环境依赖

Claude Code hooks 脚本依赖以下工具，安装前请确认：

```bash
# 自检命令
command -v jq   >/dev/null 2>&1 && echo "✅ jq"   || echo "❌ jq 未安装（CC hooks 依赖）"
command -v sed  >/dev/null 2>&1 && echo "✅ sed"  || echo "❌ sed 未安装"
command -v awk  >/dev/null 2>&1 && echo "✅ awk"  || echo "❌ awk 未安装"
command -v grep >/dev/null 2>&1 && echo "✅ grep" || echo "❌ grep 未安装"
```

| 依赖 | 用途 | 安装方式 |
|------|------|---------|
| `jq` | 解析 Claude Code 传入的 JSON tool_input | `apt install jq` / `brew install jq` |
| `sed` | 解析 status.md YAML front matter `_phase` 字段 | 系统自带 |
| `awk` | 解析 status.md YAML front matter（必要时兼容表格） | 系统自带 |
| `grep` | 正则匹配 | 系统自带 |

### 4.2 配置总览

```jsonc
// .claude/settings.json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|MultiEdit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "bash $CLAUDE_PROJECT_DIR/.aicoding/scripts/cc-hooks/phase-gate.sh"
          }
        ]
      },
      {
        "matcher": "Edit|MultiEdit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "bash $CLAUDE_PROJECT_DIR/.aicoding/scripts/cc-hooks/doc-scope-guard.sh"
          }
        ]
      },
      {
        "matcher": "Edit|MultiEdit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "bash $CLAUDE_PROJECT_DIR/.aicoding/scripts/cc-hooks/phase-entry-gate.sh"
          }
        ]
      },
      {
        "matcher": "Edit|MultiEdit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "bash $CLAUDE_PROJECT_DIR/.aicoding/scripts/cc-hooks/phase-exit-gate.sh"
          }
        ]
      },
      {
        "matcher": "Write",
        "hooks": [
          {
            "type": "command",
            "command": "bash $CLAUDE_PROJECT_DIR/.aicoding/scripts/cc-hooks/review-append-guard.sh"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write",
        "hooks": [
          {
            "type": "command",
            "command": "bash $CLAUDE_PROJECT_DIR/.aicoding/scripts/cc-hooks/doc-structure-check.sh"
          }
        ]
      },
      {
        "matcher": "Read",
        "hooks": [
          {
            "type": "command",
            "command": "bash $CLAUDE_PROJECT_DIR/.aicoding/scripts/cc-hooks/read-tracker.sh"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash $CLAUDE_PROJECT_DIR/.aicoding/scripts/cc-hooks/stop-gate.sh"
          }
        ]
      }
    ],
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash $CLAUDE_PROJECT_DIR/.aicoding/scripts/cc-hooks/inject-phase-context.sh"
          }
        ]
      }
    ]
  }
}
```

### CC-Hook 1：阶段推进拦截（PreToolUse）

| 项 | 值 |
|---|---|
| 事件 | `PreToolUse` |
| 匹配 | `Edit\|MultiEdit\|Write` |
| 对应规则 | ai_workflow.md 强制等待机制 |
| 误报率 | 极低（正则匹配明确） |

**解决的问题**：AI 在人工介入期自行修改 status.md 的"当前阶段"字段推进到下一阶段。

**逻辑**：
```bash
#!/bin/bash
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.filePath // empty')

# 只关心 status.md
echo "$FILE_PATH" | grep -q 'status\.md$' || exit 0

# 从 file_path 反推版本目录的 status.md（优先同目录）
VERSION_DIR=$(echo "$FILE_PATH" | grep -oE 'docs/v[0-9]+\.[0-9]+/')
if [ -n "$VERSION_DIR" ]; then
  STATUS_FILE="${CLAUDE_PROJECT_DIR}/${VERSION_DIR}status.md"
else
  STATUS_FILE=$(find "$CLAUDE_PROJECT_DIR/docs" -name "status.md" -path "*/v*/status.md" \
    -exec ls -t {} + 2>/dev/null | head -1)
fi
[ -z "$STATUS_FILE" ] || [ ! -f "$STATUS_FILE" ] && exit 0

# 检查当前阶段是否在人工介入期
PHASE=$(grep '^_phase:' "$STATUS_FILE" | sed 's/^_phase:[[:space:]]*//' | tr -d '[:space:]')
[ -z "$PHASE" ] && PHASE=$(awk -F'|' '/\| 当前阶段/ {gsub(/^[ \t]+|[ \t]+$/,"",$3); print $3; exit}' "$STATUS_FILE")
case "$PHASE" in
  Proposal|Requirements|"Change Management"|ChangeManagement) ;;
  *) exit 0 ;;  # 非人工介入期，放行
esac

# 检查写入内容是否试图修改"当前阶段"到下一阶段
CONTENT=$(echo "$INPUT" | jq -r '.tool_input.content // .tool_input.new_string // empty')
if echo "$CONTENT" | grep -qE '^_phase:[[:space:]]*(Design|Planning|Implementation|Testing|Deployment)[[:space:]]*$' || \
   echo "$CONTENT" | grep -qE '当前阶段.*\| *(Design|Planning|Implementation|Testing|Deployment)'; then
  echo "❌ 当前处于人工介入期（$PHASE），禁止 AI 自行推进阶段。" >&2
    echo "   请等待用户明确确认后再更新「当前阶段」。" >&2
  exit 2
fi

exit 0
```

**行为**：exit 2 阻止工具调用，stderr 反馈给 AI。AI 仍可正常编辑 status.md 的其他字段（如设置运行状态为 `wait_confirm`）。

### CC-Hook 2：Stop 门禁（Stop）

| 项 | 值 |
|---|---|
| 事件 | `Stop` |
| 匹配 | 无（Stop 事件无 matcher） |
| 对应规则 | ai_workflow.md 强制等待机制 + 审查流程 |
| 误报率 | 低 |

**解决的问题**：AI 完成阶段产出后直接停止，没有设 `wait_confirm`，或未经过审查流程。

**逻辑**：
```bash
#!/bin/bash
INPUT=$(cat)

# 检查是否已经在 stop hook 中（防止无限循环）
IS_STOP_ACTIVE=$(echo "$INPUT" | jq -r '.stop_hook_active // false')
[ "$IS_STOP_ACTIVE" = "true" ] && exit 0

STATUS_FILE=$(find "$CLAUDE_PROJECT_DIR/docs" -name "status.md" -path "*/v*/status.md" \
  -exec ls -t {} + 2>/dev/null | head -1)
[ -z "$STATUS_FILE" ] || [ ! -f "$STATUS_FILE" ] && exit 0

PHASE=$(grep '^_phase:' "$STATUS_FILE" | sed 's/^_phase:[[:space:]]*//' | tr -d '[:space:]')
[ -z "$PHASE" ] && PHASE=$(awk -F'|' '/\| 当前阶段/ {gsub(/^[ \t]+|[ \t]+$/,"",$3); print $3; exit}' "$STATUS_FILE")
VERSION_DIR=$(dirname "$STATUS_FILE")/

case "$PHASE" in
  Proposal|Requirements|"Change Management"|ChangeManagement) ;;
  *) exit 0 ;;
esac

REASONS=""

# 检查 1：运行状态是否已设为 wait_confirm（从 YAML front matter 读取）
RUN_STATUS=$(grep '^_run_status:' "$STATUS_FILE" | awk '{print $2}')
if [ "$RUN_STATUS" != "wait_confirm" ]; then
  REASONS="status.md 的 _run_status 未设为 wait_confirm（当前值: ${RUN_STATUS:-空}）。"
fi

# 检查 2：当前阶段的 review 文件是否存在（统一使用 review_<stage>.md）
case "$PHASE" in
  "Change Management"|ChangeManagement) REVIEW_FILE="review_change_management.md" ;;
  Proposal) REVIEW_FILE="review_proposal.md" ;;
  Requirements) REVIEW_FILE="review_requirements.md" ;;
esac
if [ -n "$REVIEW_FILE" ] && [ ! -f "${VERSION_DIR}${REVIEW_FILE}" ]; then
  REASONS="${REASONS} ${REVIEW_FILE} 不存在，尚未执行审查。"
fi

if [ -n "$REASONS" ]; then
  cat <<EOF
{
  "decision": "block",
  "reason": "当前处于人工介入期（${PHASE}），结束前需满足：1) YAML front matter 的 _run_status 设为 wait_confirm；2) 审查文件 ${REVIEW_FILE} 存在。未满足项：${REASONS}"
}
EOF
fi

exit 0
```

**行为**：阻止 AI 停止，AI 会根据 reason 自动补充缺失的步骤（设 wait_confirm、执行审查）。

### CC-Hook 3：文档作用域控制（PreToolUse）

| 项 | 值 |
|---|---|
| 事件 | `PreToolUse` |
| 匹配 | `Edit\|MultiEdit\|Write` |
| 对应规则 | ai_workflow.md 阶段转换规则 |
| 误报率 | 低（白名单明确） |
| 生效范围 | **全阶段**（Phase 00-07） |

**解决的问题**：AI 在当前阶段创建/修改不属于该阶段的产出物。覆盖全部 8 个阶段，比 Git Warning 6 更强——事前拦截而非事后警告。

**逻辑**：
```bash
#!/bin/bash
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.filePath // empty')
[ -z "$FILE_PATH" ] && exit 0

# 只关心 docs/vX.Y/ 下的文件
echo "$FILE_PATH" | grep -qE 'docs/v[0-9]+\.[0-9]+/' || exit 0

# 从 file_path 反推版本目录的 status.md（优先同目录）
VERSION_DIR=$(echo "$FILE_PATH" | grep -oE 'docs/v[0-9]+\.[0-9]+/')
if [ -n "$VERSION_DIR" ]; then
  STATUS_FILE="${CLAUDE_PROJECT_DIR}/${VERSION_DIR}status.md"
else
  STATUS_FILE=$(find "$CLAUDE_PROJECT_DIR/docs" -name "status.md" -path "*/v*/status.md" \
    -exec ls -t {} + 2>/dev/null | head -1)
fi
[ -z "$STATUS_FILE" ] || [ ! -f "$STATUS_FILE" ] && exit 0

PHASE=$(grep '^_phase:' "$STATUS_FILE" | sed 's/^_phase:[[:space:]]*//' | tr -d '[:space:]')
[ -z "$PHASE" ] && PHASE=$(awk -F'|' '/\| 当前阶段/ {gsub(/^[ \t]+|[ \t]+$/,"",$3); print $3; exit}' "$STATUS_FILE")

# 各阶段允许的产出文件白名单
# review_*.md 在任何阶段都允许（审查可随时发起）
# status.md 在任何阶段都允许（状态更新）
case "$PHASE" in
  "Change Management"|ChangeManagement)
    ALLOWED="status.md|review_|cr/" ;;
  Proposal)
    ALLOWED="status.md|proposal.md|review_|cr/" ;;
  Requirements)
    # 允许 proposal.md：覆盖性检查（R5）可能需要回写 Non-goals
    ALLOWED="status.md|requirements.md|proposal.md|review_|cr/" ;;
  Design)
    ALLOWED="status.md|design.md|review_|cr/" ;;
  Planning)
    ALLOWED="status.md|plan.md|review_|cr/" ;;
  Implementation)
    # Implementation 允许 tasks/ + plan.md 回填 + design.md/requirements.md 回写（缺陷修正，可追溯）
    ALLOWED="status.md|review_|cr/|plan.md|tasks/|design.md|requirements.md" ;;
  Testing)
    # Testing 允许回写 design.md/requirements.md（设计缺陷/需求偏差修正）
    ALLOWED="status.md|test_report.md|review_|cr/|design.md|requirements.md" ;;
  Deployment)
    ALLOWED="status.md|deployment.md|test_report.md|review_|cr/" ;;
  *) exit 0 ;;
esac

MATCH=false
for pattern in $(echo "$ALLOWED" | tr '|' ' '); do
  echo "$FILE_PATH" | grep -q "$pattern" && { MATCH=true; break; }
done

if [ "$MATCH" = false ]; then
  BASENAME=$(basename "$FILE_PATH")
  echo "❌ 当前阶段 $PHASE，不允许创建/修改 $BASENAME" >&2
  echo "   本阶段允许的文件：${ALLOWED//|/, }" >&2
  exit 2
fi
exit 0
```

### CC-Hook 4：会话上下文注入（SessionStart）

| 项 | 值 |
|---|---|
| 事件 | `SessionStart` |
| 匹配 | 无 |
| 对应规则 | 全局上下文感知 + 阶段入口协议 |
| 误报率 | 零（纯信息注入，不拦截） |

**解决的问题**：新会话或 resume 时 AI 不知道当前阶段和必读文件，盲目开始工作。

**增强内容**（v2）：除基本状态信息外，注入当前阶段的入口必读文件清单，与 `phases/*.md` 的入口协议保持一致。

**逻辑**：
```bash
#!/bin/bash
# aicoding-hooks-managed
# CC-Hook 4: 会话上下文注入（SessionStart）
# 在新会话开始时注入当前项目状态和阶段入口必读清单到 AI 上下文
STATUS_FILE=$(find "$CLAUDE_PROJECT_DIR/docs" -name "status.md" -path "*/v*/status.md" \
  -exec ls -t {} + 2>/dev/null | head -1)

if [ -z "$STATUS_FILE" ]; then
  echo '{"hookSpecificOutput":{"additionalContext":"[项目状态] 当前无活跃版本目录，无 status.md。"}}'
  exit 0
fi

PHASE=$(grep '^_phase:' "$STATUS_FILE" | sed 's/^_phase:[[:space:]]*//' | tr -d '[:space:]')
[ -z "$PHASE" ] && PHASE=$(awk -F'|' '/\| 当前阶段/ {gsub(/^[ \t]+|[ \t]+$/,"",$3); print $3; exit}' "$STATUS_FILE")
RUN_STATUS=$(grep '^_run_status:' "$STATUS_FILE" | awk '{print $2}')
VERSION_DIR=$(echo "$STATUS_FILE" | sed 's/status\.md$//')

# 收集 Active CR
ACTIVE_CRS=$(awk -F'|' '{gsub(/[ \t]/,"",$2); gsub(/[ \t]/,"",$3)}
  $2 ~ /^CR-[0-9]{8}-[0-9]{3}$/ && ($3=="Accepted"||$3=="InProgress")
  {print $2}' "$STATUS_FILE" | tr '\n' ',' | sed 's/,$//')

CONTEXT="[项目状态] 版本目录: ${VERSION_DIR} | 当前阶段: ${PHASE} | 运行状态: ${RUN_STATUS}"
[ -n "$ACTIVE_CRS" ] && CONTEXT="${CONTEXT} | Active CRs: ${ACTIVE_CRS}"

# 人工介入期提示
case "$PHASE" in
  Proposal|Requirements|ChangeManagement)
    CONTEXT="${CONTEXT} | 当前处于人工介入期，阶段推进需用户明确确认。" ;;
esac

# 阶段入口必读清单（与 phases/*.md 的入口协议保持一致）
case "$PHASE" in
  ChangeManagement)
    CONTEXT="${CONTEXT} | [入口必读] status.md, phases/00-change-management.md, templates/cr_template.md" ;;
  Proposal)
    CONTEXT="${CONTEXT} | [入口必读] status.md, phases/01-proposal.md, templates/proposal_template.md, docs/系统功能说明书.md(如存在)" ;;
  Requirements)
    CONTEXT="${CONTEXT} | [入口必读] status.md, proposal.md, phases/02-requirements.md, templates/requirements_template.md, docs/系统功能说明书.md(如存在)" ;;
  Design)
    CONTEXT="${CONTEXT} | [入口必读] status.md, requirements.md, phases/03-design.md, templates/design_template.md, docs/技术方案设计.md(如存在)" ;;
  Planning)
    CONTEXT="${CONTEXT} | [入口必读] status.md, design.md, requirements.md, phases/04-planning.md, templates/plan_template.md" ;;
  Implementation)
    CONTEXT="${CONTEXT} | [入口必读] status.md, plan.md, design.md, requirements.md, phases/05-implementation.md, templates/implementation_checklist_template.md" ;;
  Testing)
    CONTEXT="${CONTEXT} | [入口必读] status.md, requirements.md, plan.md, phases/06-testing.md, templates/test_report_template.md" ;;
  Deployment)
    CONTEXT="${CONTEXT} | [入口必读] status.md, test_report.md, design.md, requirements.md, phases/07-deployment.md, templates/deployment_template.md" ;;
esac

echo "{\"hookSpecificOutput\":{\"additionalContext\":\"${CONTEXT}\"}}"
exit 0
```

**行为**：SessionStart 的 additionalContext 会被注入到 AI 的上下文中，AI 在会话开始时就知道当前状态和必读文件。零副作用。

### CC-Hook 5：产出物结构校验（PostToolUse）

| 项 | 值 |
|---|---|
| 事件 | `PostToolUse` |
| 匹配 | `Write` |
| 对应规则 | 各阶段模板必填章节 |
| 误报率 | 低（只检查章节标题存在性） |

**解决的问题**：AI 不读模板就写文档，导致缺少必填章节、缺少 GWT 验收标准、CR 影响面未勾选。

**设计要点**：
- 使用 **PostToolUse** 而非 PreToolUse——文件已写入，hook 给 AI 反馈要求补充，AI 自动修正
- 只挂在 **Write**（全量写入），不挂 Edit——避免 AI 分步编辑时中间态触发误报
- 只检查**章节标题存在性**，不检查内容质量——质量是 review 的职责

**逻辑**：
```bash
#!/bin/bash
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.filePath // empty')
[ -z "$FILE_PATH" ] && exit 0
[ ! -f "$FILE_PATH" ] && exit 0

BASENAME=$(basename "$FILE_PATH")
MISSING=""

check_section() {
  grep -q "$1" "$FILE_PATH" || MISSING="${MISSING}\n  - $1"
}

case "$BASENAME" in
  proposal.md)
    check_section "## 一句话总结"
    check_section "## 背景与现状"
    check_section "## 目标与成功指标"
    check_section "## 目标用户"
    check_section "## 方案概述"
    check_section "## 范围界定"
    check_section "## 风险与依赖"
    check_section "## 变更记录"
    ;;
  requirements.md)
    check_section "## 1\."   # 概述
    check_section "## 2\."   # 业务场景
    check_section "## 3\."   # 功能性需求
    check_section "## 4\."   # 非功能需求
    check_section "## 7\."   # 变更记录
    # 额外：是否有 GWT 格式验收标准
    if ! grep -qE 'Given .+ When .+ Then ' "$FILE_PATH"; then
      MISSING="${MISSING}\n  - GWT 格式验收标准（Given...When...Then...）"
    fi
    ;;
  CR-*.md)
    check_section "## 1\. 变更意图"
    check_section "## 2\. 变更点"
    check_section "## 3\. 影响面"
    check_section "## 6\. 验收与验证"
    # 额外：影响面是否有勾选（兼容 [✓] 和 [x]/[X] 两种勾选风格）
    if ! grep -qE '\[(✓|x|X)\](是|否)' "$FILE_PATH"; then
      MISSING="${MISSING}\n  - §3 影响面未勾选（所有行仍为模板默认状态）"
    fi
    # 额外：GWT
    if ! grep -qE 'Given .+ When .+ Then ' "$FILE_PATH"; then
      MISSING="${MISSING}\n  - §6 缺少 GWT 验收标准"
    fi
    ;;
  *) exit 0 ;;
esac

if [ -n "$MISSING" ]; then
  ESCAPED=$(echo -e "$MISSING" | sed 's/"/\\"/g' | tr '\n' ' ')
  cat <<EOF
{
  "decision": "block",
  "reason": "${BASENAME} 缺少以下必要内容：${ESCAPED}请补充完整。"
}
EOF
fi

exit 0
```

**行为**：PostToolUse 的 `"decision": "block"` 会将 reason 反馈给 AI，AI 自动用 Edit 补充缺失章节。用户看到的是 AI 自我修正的过程，而非被反复拦截的卡顿感。

### CC-Hook 6：review 文件追加保护（PreToolUse）

| 项 | 值 |
|---|---|
| 事件 | `PreToolUse` |
| 匹配 | `Write` |
| 对应规则 | review_template.md 审查记录格式（追加式） |
| 误报率 | 极低（仅在已有审查轮次时触发） |

**解决的问题**：AI 用 Write 覆盖已有的 review 文件，导致历史审查记录丢失。review 文件应追加新轮次，不应覆盖。

**逻辑**：
```bash
#!/bin/bash
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.filePath // empty')
[ -z "$FILE_PATH" ] && exit 0

# 只关心 review_*.md 文件
echo "$FILE_PATH" | grep -qE 'review_[a-z_]+\.md$' || exit 0

# 文件不存在（首次创建），放行
[ ! -f "$FILE_PATH" ] && exit 0

# 统计已有的审查轮次记录
EXISTING_ROUNDS=$(grep -c '## [0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}.*第.*轮' "$FILE_PATH" 2>/dev/null || echo 0)
[ "$EXISTING_ROUNDS" -eq 0 ] && exit 0

# 有已有轮次，检查新内容是否保留了它们
NEW_CONTENT=$(echo "$INPUT" | jq -r '.tool_input.content // empty')
NEW_ROUNDS=$(echo "$NEW_CONTENT" | grep -c '## [0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}.*第.*轮' 2>/dev/null || echo 0)

if [ "$NEW_ROUNDS" -lt "$EXISTING_ROUNDS" ]; then
  echo "❌ review 文件已有 ${EXISTING_ROUNDS} 轮审查记录，新内容只有 ${NEW_ROUNDS} 轮。" >&2
  echo "   审查记录必须追加，不得覆盖。请使用 Edit 工具在文件末尾追加新一轮审查。" >&2
  exit 2
fi

exit 0
```

**行为**：PreToolUse 拦截 Write（因为覆盖后历史记录不可恢复，必须事前阻止）。AI 收到反馈后会改用 Edit 在文件末尾追加。

### CC-Hook 7：阶段入口门禁（PreToolUse）

| 项 | 值 |
|---|---|
| 事件 | `PreToolUse` |
| 匹配 | `Edit\|MultiEdit\|Write` |
| 对应规则 | 各阶段入口协议（phases/*.md） |
| 误报率 | 低（基于文件读取日志的确定性检查） |
| 生效范围 | **全阶段**（Phase 00-07） |

**解决的问题**：AI 不读取必要的输入文件就开始写产出物，导致产出质量不稳定、遗漏关键上下文。这是之前"排除的 Hooks"中"先读后写"的升级实现——通过 CC-7b 追踪 Read 调用解决了跨工具状态维护问题。

**依赖**：CC-7b（read-tracker.sh）提供的读取日志。

**逻辑**：
```bash
#!/bin/bash
# aicoding-hooks-managed
# CC-Hook 7: 阶段入口门禁（PreToolUse）
# 在 AI 首次写入阶段产出物时，检查是否已读取入口协议中的必读文件。
# 使用临时文件 /tmp/aicoding-reads-<session>.log 记录本会话的 Read 调用。
# 配合 CC-7b read-tracker.sh（PostToolUse on Read）记录已读文件。
INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty')
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.filePath // empty')
[ -z "$FILE_PATH" ] && exit 0

# --- 路径过滤：判断是否需要触发入口门禁 ---
# .aicoding/ 框架文件不触发
echo "$FILE_PATH" | grep -q '\.aicoding/' && exit 0

# review_*.md 和 status.md 的写入不触发入口检查（允许随时写）
BASENAME=$(basename "$FILE_PATH")
case "$BASENAME" in
  review_*|status.md) exit 0 ;;
esac

# 定位 status.md 获取当前阶段
VERSION_DIR=$(echo "$FILE_PATH" | grep -oE 'docs/v[0-9]+\.[0-9]+/')
if [ -n "$VERSION_DIR" ]; then
  STATUS_FILE="${CLAUDE_PROJECT_DIR}/${VERSION_DIR}status.md"
else
  STATUS_FILE=$(find "$CLAUDE_PROJECT_DIR/docs" -name "status.md" -path "*/v*/status.md" \
    -exec ls -t {} + 2>/dev/null | head -1)
  [ -n "$STATUS_FILE" ] && VERSION_DIR=$(echo "$STATUS_FILE" | sed "s|${CLAUDE_PROJECT_DIR}/||;s|status\.md$||")
fi
[ -z "$STATUS_FILE" ] || [ ! -f "$STATUS_FILE" ] && exit 0

PHASE=$(grep '^_phase:' "$STATUS_FILE" | sed 's/^_phase:[[:space:]]*//' | tr -d '[:space:]')
[ -z "$PHASE" ] && exit 0

# --- 阶段感知的路径过滤 ---
IS_VERSIONED_DOC=false
echo "$FILE_PATH" | grep -qE 'docs/v[0-9]+\.[0-9]+/' && IS_VERSIONED_DOC=true

case "$PHASE" in
  Implementation)
    # Implementation: 触发范围 = docs/vX.Y/ 产出物 + 代码文件（非 docs/ 非 .aicoding/）
    if [ "$IS_VERSIONED_DOC" = false ]; then
      echo "$FILE_PATH" | grep -q 'docs/' && exit 0  # docs/ 根目录下的主文档不在 Implementation 管辖
    fi
    ;;
  Deployment)
    # Deployment: 触发范围 = docs/vX.Y/ 产出物 + docs/ 根目录下的主文档
    if [ "$IS_VERSIONED_DOC" = false ]; then
      echo "$FILE_PATH" | grep -q 'docs/' || exit 0  # 非 docs/ 文件不触发
    fi
    ;;
  *)
    # 其他阶段: 只触发 docs/vX.Y/ 下的产出物
    [ "$IS_VERSIONED_DOC" = false ] && exit 0
    ;;
esac

# --- 入口门禁已通过标记（避免每次写入都检查，只检查一次） ---
VERSION_SLUG=$(echo "$VERSION_DIR" | tr '/' '_')
GATE_PASSED="/tmp/aicoding-entry-passed-${PHASE}-${VERSION_SLUG}-${CLAUDE_SESSION_ID:-$$}"
[ -f "$GATE_PASSED" ] && exit 0

# 定义各阶段必读文件（相对于项目根目录的路径模式）
# 版本化文档使用 VERSION_DIR 前缀绑定，框架文件使用 .aicoding/ 前缀
# 使用 grep -qF 模式匹配
case "$PHASE" in
  ChangeManagement)
    REQUIRED_PATTERNS="${VERSION_DIR}status.md
phases/00-change-management.md
templates/cr_template.md" ;;
  Proposal)
    REQUIRED_PATTERNS="${VERSION_DIR}status.md
phases/01-proposal.md
templates/proposal_template.md" ;;
  Requirements)
    REQUIRED_PATTERNS="${VERSION_DIR}status.md
${VERSION_DIR}proposal.md
phases/02-requirements.md
templates/requirements_template.md" ;;
  Design)
    REQUIRED_PATTERNS="${VERSION_DIR}status.md
${VERSION_DIR}requirements.md
phases/03-design.md
templates/design_template.md" ;;
  Planning)
    REQUIRED_PATTERNS="${VERSION_DIR}status.md
${VERSION_DIR}design.md
${VERSION_DIR}requirements.md
phases/04-planning.md
templates/plan_template.md" ;;
  Implementation)
    REQUIRED_PATTERNS="${VERSION_DIR}status.md
${VERSION_DIR}plan.md
${VERSION_DIR}design.md
${VERSION_DIR}requirements.md
phases/05-implementation.md
templates/implementation_checklist_template.md" ;;
  Testing)
    REQUIRED_PATTERNS="${VERSION_DIR}status.md
${VERSION_DIR}requirements.md
${VERSION_DIR}plan.md
phases/06-testing.md
templates/test_report_template.md" ;;
  Deployment)
    REQUIRED_PATTERNS="${VERSION_DIR}status.md
${VERSION_DIR}test_report.md
${VERSION_DIR}design.md
${VERSION_DIR}requirements.md
phases/07-deployment.md
templates/deployment_template.md" ;;
  *) exit 0 ;;
esac

# 读取已记录的 Read 调用日志
READ_LOG="/tmp/aicoding-reads-${CLAUDE_SESSION_ID:-$$}.log"
[ ! -f "$READ_LOG" ] && READ_LOG_CONTENT="" || READ_LOG_CONTENT=$(cat "$READ_LOG")

# 检查每个必读模式是否已被读取
MISSING=""
while IFS= read -r pattern; do
  [ -z "$pattern" ] && continue
  if ! echo "$READ_LOG_CONTENT" | grep -qF "$pattern"; then
    MISSING="${MISSING}\n  - ${pattern}"
  fi
done <<< "$REQUIRED_PATTERNS"

if [ -n "$MISSING" ]; then
  echo "❌ 阶段入口门禁（${PHASE}）：写入产出物前必须先读取以下文件：" >&2
  echo -e "$MISSING" >&2
  echo "   请先 Read 上述文件，再继续写入。（见 phases/ 中的「阶段入口协议」）" >&2
  exit 2
fi

# 入口门禁通过，标记本阶段已通过（后续写入不再检查）
touch "$GATE_PASSED"
exit 0
```

**行为**：exit 2 阻止写入，stderr 列出未读取的文件。AI 收到反馈后会先读取必读文件再继续写入。

### CC-Hook 7b：Read 追踪器（PostToolUse）

| 项 | 值 |
|---|---|
| 事件 | `PostToolUse` |
| 匹配 | `Read` |
| 对应规则 | CC-7 阶段入口门禁的数据源 |
| 误报率 | 零（纯记录，不拦截） |

**解决的问题**：CC-7 需要知道 AI 已读取了哪些文件。CC-7b 在每次 Read 工具调用后记录文件路径到会话临时日志。

**逻辑**：
```bash
#!/bin/bash
# aicoding-hooks-managed
# CC-Hook 7b: Read 追踪器（PostToolUse on Read）
# 记录 AI 的 Read 调用到临时日志，供 CC-7 入口门禁检查。
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.filePath // empty')
[ -z "$FILE_PATH" ] && exit 0

# 记录到会话级临时文件
READ_LOG="/tmp/aicoding-reads-${CLAUDE_SESSION_ID:-$$}.log"
echo "$FILE_PATH" >> "$READ_LOG"

exit 0
```

**行为**：PostToolUse 静默记录，零副作用。日志文件按会话隔离（`CLAUDE_SESSION_ID`），会话结束后自动清理（/tmp 目录）。

### CC-Hook 8：阶段出口门禁（PreToolUse）

| 项 | 值 |
|---|---|
| 事件 | `PreToolUse` |
| 匹配 | `Edit\|MultiEdit\|Write` |
| 对应规则 | 各阶段完成条件（phases/*.md） |
| 误报率 | 极低（仅在推进阶段时触发，检查文件存在性） |
| 生效范围 | **AI 自动期**（Phase 03-06） |

**解决的问题**：AI 在产出物不完整时就推进到下一阶段（如未写 review 文件、未生成测试报告）。

**逻辑**：
```bash
#!/bin/bash
# aicoding-hooks-managed
# CC-Hook 8: 阶段出口门禁（PreToolUse）
# 当 AI 试图修改 status.md 的 _phase 推进到下一阶段时，
# 检查当前阶段的必要产出物是否存在。
# 仅在 AI 自动期（Phase 03-06）生效。
INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty')
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.filePath // empty')
[ -z "$FILE_PATH" ] && exit 0

# 只关心 status.md
echo "$FILE_PATH" | grep -q 'status\.md$' || exit 0

# 检查写入内容是否试图修改 _phase（支持 Write/Edit/MultiEdit）
case "$TOOL_NAME" in
  Write)
    CONTENT=$(echo "$INPUT" | jq -r '.tool_input.content // empty') ;;
  Edit)
    CONTENT=$(echo "$INPUT" | jq -r '.tool_input.new_string // empty') ;;
  MultiEdit)
    CONTENT=$(echo "$INPUT" | jq -r '[.tool_input.edits[]?.new_string // empty] | join("\n")') ;;
  *) exit 0 ;;
esac

NEW_PHASE=$(echo "$CONTENT" | grep -oE '_phase:[[:space:]]*(ChangeManagement|Proposal|Requirements|Design|Planning|Implementation|Testing|Deployment)' \
  | sed 's/_phase:[[:space:]]*//' | head -1)
[ -z "$NEW_PHASE" ] && exit 0

# 从 file_path 反推版本目录
VERSION_DIR=$(echo "$FILE_PATH" | grep -oE 'docs/v[0-9]+\.[0-9]+/')
if [ -n "$VERSION_DIR" ]; then
  STATUS_FILE="${CLAUDE_PROJECT_DIR}/${VERSION_DIR}status.md"
else
  STATUS_FILE=$(find "$CLAUDE_PROJECT_DIR/docs" -name "status.md" -path "*/v*/status.md" \
    -exec ls -t {} + 2>/dev/null | head -1)
  VERSION_DIR=$(echo "$STATUS_FILE" | sed "s|${CLAUDE_PROJECT_DIR}/||;s|status\.md$||")
fi
[ -z "$STATUS_FILE" ] || [ ! -f "$STATUS_FILE" ] && exit 0

CURRENT_PHASE=$(grep '^_phase:' "$STATUS_FILE" | sed 's/^_phase:[[:space:]]*//' | tr -d '[:space:]')
[ -z "$CURRENT_PHASE" ] && exit 0

# 如果新旧 _phase 相同，不是阶段推进，放行
[ "$CURRENT_PHASE" = "$NEW_PHASE" ] && exit 0

# 只在 AI 自动期（Phase 03-06）做出口检查
case "$CURRENT_PHASE" in
  Design|Planning|Implementation|Testing) ;;
  *) exit 0 ;;
esac

VERSION_PATH="${CLAUDE_PROJECT_DIR}/${VERSION_DIR}"
MISSING=""

check_file() {
  [ ! -f "${VERSION_PATH}$1" ] && MISSING="${MISSING}\n  - $1"
}

# 各阶段出口必须存在的产出物
case "$CURRENT_PHASE" in
  Design)
    check_file "design.md"
    check_file "review_design.md"
    ;;
  Planning)
    check_file "plan.md"
    check_file "review_planning.md"
    ;;
  Implementation)
    check_file "review_implementation.md"
    ;;
  Testing)
    check_file "test_report.md"
    check_file "review_testing.md"
    ;;
esac

if [ -n "$MISSING" ]; then
  echo "❌ 阶段出口门禁（${CURRENT_PHASE} → ${NEW_PHASE}）：以下必要产出物缺失：" >&2
  echo -e "$MISSING" >&2
  echo "   请补充完整后再推进阶段。（见 phases/ 中的「阶段出口门禁」）" >&2
  exit 2
fi

exit 0
```

**行为**：exit 2 阻止 `_phase` 字段写入，stderr 列出缺失的产出物。AI 需补充完整后再推进。

### 4.3 Claude Code Hooks 总览

| # | 名称 | 事件 | 层级 | 生效范围 | 解决的问题 |
|---|------|------|------|---------|-----------|
| CC-1 | 阶段推进拦截 | PreToolUse | 流程守卫 | Phase 00-02 | AI 自行推进阶段 |
| CC-2 | Stop 门禁 | Stop | 流程守卫 | Phase 00-02 | AI 未设 wait_confirm 或未走审查就停止 |
| CC-3 | 文档作用域控制 | PreToolUse | 流程守卫 | **全阶段** | AI 越阶段创建产出物 |
| CC-4 | 会话上下文注入 | SessionStart | 流程守卫 | **全阶段** | 新会话不知道当前阶段和必读文件 |
| CC-5 | 产出物结构校验 | PostToolUse | 产出物校验 | Phase 00-02 | 缺少必填章节、缺 GWT、CR 影响面未填 |
| CC-6 | review 追加保护 | PreToolUse | 产出物校验 | **全阶段** | 覆盖已有审查记录 |
| CC-7 | 阶段入口门禁 | PreToolUse | 流程守卫 | **全阶段** | AI 不读必要输入就写产出物 |
| CC-7b | Read 追踪器 | PostToolUse | 追踪 | **全阶段** | 为 CC-7 提供读取日志 |
| CC-8 | 阶段出口门禁 | PreToolUse | 流程守卫 | Phase 03-06 | AI 产出物不完整就推进阶段 |

---

## 5. Git Hooks：硬拦截（7 个，含交付关口条件拦截+出口门禁）

Git hooks 对 Claude Code 和 Codex 都生效，在 commit 时做程序化验证。按确定性分为硬拦截（pre-commit / commit-msg）和软警告（post-commit）两层。

```
commit 时
  │
  ├─ pre-commit / commit-msg（硬拦截，7 个）
  │   确定性高、误报率极低的检查
  │   失败 → 阻止 commit
  │
  ├─ post-commit（软警告，21 个）
  │   有价值但可能存在边界情况的检查
  │   commit 已完成，输出警告供人工/AI 判断是否修复
  │
  ▼
继续开发或修复后追加 commit
```

### Git-Hook 1：commit-msg 阶段前缀校验

| 项 | 值 |
|---|---|
| 触发点 | `commit-msg` |
| 对应规则 | STRUCTURE.md Git 规范 |
| 误报率 | 极低 |

**逻辑**：
```bash
# 校验 commit message 格式（Conventional Commits 常见子集）
# 允许的格式：
#   1. [CR-ID] 描述
#   2. type: 描述  或  type(scope): 描述
#   3. Merge/Revert 开头的自动生成消息
#   4. fixup!/squash! 前缀（rebase 中间态）
MSG=$(head -1 "$1")
if echo "$MSG" | grep -qE '^\[(CR-[0-9]{8}-[0-9]{3})\] '; then exit 0; fi
if echo "$MSG" | grep -qE '^(feat|fix|docs|test|refactor|chore)(\([^)]+\))?: '; then exit 0; fi
if echo "$MSG" | grep -qE '^(Merge|Revert|fixup!|squash!) '; then exit 0; fi
echo "❌ commit message 格式错误"
echo "   允许的格式："
echo "   1. <type>: <描述>  或  <type>(<scope>): <描述>"
echo "      type: feat|fix|docs|test|refactor|chore"
echo "   2. [CR-YYYYMMDD-NNN] <描述>"
echo "   3. Merge/Revert/fixup!/squash! 前缀"
exit 1
```

### Git-Hook 2：commit-msg CR-ID 校验（条件触发）

| 项 | 值 |
|---|---|
| 触发点 | `commit-msg` |
| 对应规则 | 05-implementation.md 代码追溯要求 |
| 触发条件 | status.md 存在 Active CR（状态为 Accepted/InProgress） |
| 误报率 | 低（无 Active CR 时自动跳过） |

**逻辑**：
```bash
# 定位当前开发版本的 status.md
# 优先：本次暂存区涉及的 docs/vX.Y/ 目录；否则 fallback 到最近修改的 status.md
STAGED=$(git diff --cached --name-only)
VERSION_DIR=$(echo "$STAGED" | grep -oE 'docs/v[0-9]+\.[0-9]+/' | head -1)
if [ -n "$VERSION_DIR" ]; then
  STATUS_FILE="${VERSION_DIR}status.md"
else
  STATUS_FILE=$(find docs/ -name "status.md" -path "*/v*/status.md" -exec ls -t {} + 2>/dev/null | head -1)
fi
if [ -z "$STATUS_FILE" ] || [ ! -f "$STATUS_FILE" ]; then exit 0; fi

# 从暂存区读取 status.md 内容（避免工作区与 index 不一致）
STATUS_CONTENT=$(git show ":$STATUS_FILE" 2>/dev/null || cat "$STATUS_FILE")

# 提取 Active CR：按 | 分列，容忍空格差异
ACTIVE_CRS=$(echo "$STATUS_CONTENT" | awk -F'|' '
  {
    gsub(/^[ \t]+|[ \t]+$/, "", $2);
    gsub(/^[ \t]+|[ \t]+$/, "", $3);
    gsub(/[ \t]/, "", $3);
    if ($2 ~ /^CR-[0-9]{8}-[0-9]{3}$/ && ($3 == "Accepted" || $3 == "InProgress"))
      print $2
  }
')
if [ -z "$ACTIVE_CRS" ]; then exit 0; fi

MSG=$(cat "$1")
FOUND=false
for CR in $ACTIVE_CRS; do
  if echo "$MSG" | grep -q "$CR"; then FOUND=true; break; fi
done

if [ "$FOUND" = false ]; then
  echo "❌ 存在 Active CR，commit message 必须包含 CR-ID"
  echo "   Active CRs:"
  echo "$ACTIVE_CRS" | sed 's/^/     /'
  exit 1
fi
```

### Git-Hook 3：.env / 密钥文件泄露拦截

| 项 | 值 |
|---|---|
| 触发点 | `pre-commit` |
| 对应规则 | 05-implementation.md 安全意识 |
| 误报率 | 极低 |

**逻辑**：
```bash
# 检查暂存区是否包含敏感文件（使用 shell case 匹配，避免 regex 转义问题）
# 白名单：.env.example / .env.template / .env.sample 是模板文件，允许提交
STAGED=$(git diff --cached --name-only)
BLOCKED=""
while IFS= read -r file; do
  [ -z "$file" ] && continue
  base=$(basename "$file")
  case "$base" in
    .env.example|.env.template|.env.sample)   continue ;;  # 白名单，跳过
    .env|.env.local|.env.production|.env.*)    BLOCKED="$BLOCKED\n  $file" ;;
    credentials.json|service-account.json)     BLOCKED="$BLOCKED\n  $file" ;;
    *.pem|*.key)                               BLOCKED="$BLOCKED\n  $file" ;;
    id_rsa|id_ed25519|id_ecdsa|id_dsa)         BLOCKED="$BLOCKED\n  $file" ;;
  esac
done <<< "$STAGED"

if [ -n "$BLOCKED" ]; then
  echo "❌ 检测到敏感文件即将被提交："
  echo -e "$BLOCKED"
  echo "   请将其加入 .gitignore 或从暂存区移除"
  echo "   （白名单：.env.example / .env.template / .env.sample 不拦截）"
  exit 1
fi
```

### Git-Hook 4：status.md YAML front matter 完整性

| 项 | 值 |
|---|---|
| 触发点 | `pre-commit` |
| 对应规则 | status_template.md YAML front matter 说明 |
| 触发条件 | 暂存区包含 status.md |
| 误报率 | 极低 |

**逻辑**：
```bash
# 仅当 status.md 被修改时触发
# 从暂存区（index）读取内容，避免工作区与暂存区不一致导致误判
# 要求 status.md 第 1 行必须是 ---（锚定文件开头，避免正文中的 --- 分隔线被误当 front matter）
STATUS_FILES=$(git diff --cached --name-only | grep 'status\.md$' || true)
if [ -z "$STATUS_FILES" ]; then exit 0; fi

for f in $STATUS_FILES; do
  CONTENT=$(git show ":$f" 2>/dev/null) || continue
  # 锚定：第 1 行必须是 ---
  FIRST_LINE=$(echo "$CONTENT" | head -1)
  if [ "$FIRST_LINE" != "---" ]; then
    echo "❌ $f 第 1 行必须是 ---（YAML front matter 起始标记）"; exit 1
  fi
  # 必须存在闭合标记（第二个 ---）
  HAS_END_MARKER=$(echo "$CONTENT" | awk 'NR==1{next} /^---$/{print 1; exit}')
  if [ -z "$HAS_END_MARKER" ]; then
    echo "❌ $f 的 YAML front matter 未闭合（缺少第二个 ---）"; exit 1
  fi
  # 提取首个 --- ... --- 块（从第 2 行开始到下一个 ---）
  FRONT_MATTER=$(echo "$CONTENT" | awk 'NR==1{next} /^---$/{exit} {print}')
  if [ -z "$FRONT_MATTER" ]; then
    echo "❌ $f 缺少 YAML front matter 内容（--- 块为空或未闭合）"; exit 1
  fi
  for field in _baseline _current _workflow_mode _run_status _change_status _phase; do
    if ! echo "$FRONT_MATTER" | grep -q "^${field}:"; then
      echo "❌ $f 的 YAML front matter 中缺少 ${field} 字段"; exit 1
    fi
    VALUE=$(echo "$FRONT_MATTER" | grep "^${field}:" | sed "s/^${field}:[[:space:]]*//" | tr -d '[:space:]')
    if [ -z "$VALUE" ]; then
      echo "❌ $f 的 ${field} 值为空"; exit 1
    fi
  done

  # 枚举值校验（防止拼写错误导致门禁静默跳过）
  WORKFLOW_MODE=$(echo "$FRONT_MATTER" | grep '^_workflow_mode:' | sed 's/^_workflow_mode:[[:space:]]*//' | tr -d '[:space:]')
  RUN_STATUS=$(echo "$FRONT_MATTER" | grep '^_run_status:' | sed 's/^_run_status:[[:space:]]*//' | tr -d '[:space:]')
  CHANGE_STATUS=$(echo "$FRONT_MATTER" | grep '^_change_status:' | sed 's/^_change_status:[[:space:]]*//' | tr -d '[:space:]')
  CHANGE_LEVEL=$(echo "$FRONT_MATTER" | grep '^_change_level:' | sed 's/^_change_level:[[:space:]]*//' | tr -d '[:space:]')
  REVIEW_ROUND=$(echo "$FRONT_MATTER" | grep '^_review_round:' | sed 's/^_review_round:[[:space:]]*//' | tr -d '[:space:]')
  PHASE=$(echo "$FRONT_MATTER" | grep '^_phase:' | sed 's/^_phase:[[:space:]]*//' | tr -d '[:space:]')

  case "$WORKFLOW_MODE" in manual|semi-auto|auto) ;; *)
    echo "❌ $f: _workflow_mode 值非法（期望 manual/semi-auto/auto）"; exit 1 ;; esac
  case "$RUN_STATUS" in running|paused|wait_confirm|completed) ;; *)
    echo "❌ $f: _run_status 值非法（期望 running/paused/wait_confirm/completed）"; exit 1 ;; esac
  case "$CHANGE_STATUS" in in_progress|done) ;; *)
    echo "❌ $f: _change_status 值非法（期望 in_progress/done）"; exit 1 ;; esac
  # _change_level 兼容期：缺失仅告警，存在时必须 major/minor
  if [ -n "$CHANGE_LEVEL" ]; then
    case "$CHANGE_LEVEL" in major|minor) ;; *)
      echo "❌ $f: _change_level 值非法（兼容期仅允许 major/minor）"; exit 1 ;; esac
  fi
  if [ -n "$REVIEW_ROUND" ] && ! echo "$REVIEW_ROUND" | grep -qE '^[0-9]+$'; then
    echo "❌ $f: _review_round 必须是非负整数"; exit 1
  fi
  case "$PHASE" in ChangeManagement|Proposal|Requirements|Design|Planning|Implementation|Testing|Deployment) ;; *)
    echo "❌ $f: _phase 值非法（期望 ChangeManagement/Proposal/Requirements/Design/Planning/Implementation/Testing/Deployment）"; exit 1 ;; esac
done
```

### Git-Hook 5：git config 防篡改

| 项 | 值 |
|---|---|
| 触发点 | `pre-commit` |
| 对应规则 | STRUCTURE.md "禁止危险操作" |
| 误报率 | 极低 |

**逻辑**：
```bash
# 检查暂存区是否包含 git 配置文件的异常修改（路径锚定，避免误伤普通文件）
STAGED=$(git diff --cached --name-only)
if echo "$STAGED" | grep -qE '(^|/)\.gitconfig$|(^|/)\.gitmodules$'; then
  echo "❌ 检测到 git 配置文件变更，需人工确认"
  exit 1
fi
```

### Git-Hook 6：交付关口证据与计划（条件硬拦截）

| 项 | 值 |
|---|---|
| 触发点 | `pre-commit` |
| 对应规则 | enhance.md 落地项 B/C（证据与验收命令） |
| 触发条件 | 暂存区包含 status.md 且本次提交推进到 Deployment 或 `_change_status=done` |
| 误报率 | 低（仅关键节点触发） |

**语义**：不强跑测试/scan，只做确定性检查：交付前必须有可复现证据与可判定结论；plan.md 任务必须有验证命令。

**检查项**：
- **W16（条件硬拦截）**：当 `_phase` 为 `Testing/Deployment` 且 `_run_status=wait_confirm` 或 `_change_status=done` 时，要求 `test_report.md`：
  - 至少满足其一：包含 `bash/sh` 命令块 / 证据链接行 / “CR验证证据”表中存在“通过”的证据
  - `- 整体结论：通过/不通过` 必须可判定，且不允许为“不通过”
- **W17（条件硬拦截）**：同样触发条件下，要求 `plan.md` 的每个任务在"验证方式"中填写有效命令（非 `...` / `<占位符>`）

---

### Git-Hook 7：阶段出口门禁（Phase 03-06 产出物检查）

| 项 | 值 |
|---|---|
| 触发点 | `pre-commit` |
| 对应规则 | CC-8 出口门禁的 Git 层等价物 |
| 触发条件 | 暂存区 status.md 的 `_phase` 与 HEAD 不同，且旧阶段为 Design/Planning/Implementation/Testing |
| 误报率 | 极低（仅阶段推进时触发） |

**语义**：当 `_phase` 从 AI 自动期阶段（03-06）推进到下一阶段时，检查当前阶段的必要产出物是否存在。与 CC-8 逻辑一致，但在 Git 层拦截，对 Claude Code 和 Codex 都生效。

**设计决策**：CC-8 仅拦截 Claude Code 的 Write/Edit 工具调用，Codex 可绕过。将同等逻辑落到 Git pre-commit 层，确保无论哪个 AI 工具提交，阶段推进都必须满足产出物要求。

**各阶段必须存在的产出物**：

| 离开阶段 | 必须存在的文件 |
|---------|--------------|
| Design | `design.md`, `review_design.md` |
| Planning | `plan.md`, `review_planning.md` |
| Implementation | `review_implementation.md` |
| Testing | `test_report.md`, `review_testing.md` |

```bash
# 获取暂存区（新）和 HEAD（旧）的 _phase，比较是否发生阶段推进
for f in $STATUS_FILES; do
  NEW_CONTENT=$(git show ":$f" 2>/dev/null) || continue
  NEW_FM=$(echo "$NEW_CONTENT" | awk 'NR==1{next} /^---$/{exit} {print}')
  [ -z "$NEW_FM" ] && continue
  NEW_PHASE=$(echo "$NEW_FM" | grep '^_phase:' | sed 's/^_phase:[[:space:]]*//' | tr -d '[:space:]')
  [ -z "$NEW_PHASE" ] && continue

  OLD_CONTENT=$(git show "HEAD:$f" 2>/dev/null) || continue
  OLD_FM=$(echo "$OLD_CONTENT" | awk 'NR==1{next} /^---$/{exit} {print}')
  OLD_PHASE=$(echo "$OLD_FM" | grep '^_phase:' | sed 's/^_phase:[[:space:]]*//' | tr -d '[:space:]')
  [ -z "$OLD_PHASE" ] && continue

  [ "$OLD_PHASE" = "$NEW_PHASE" ] && continue

  case "$OLD_PHASE" in
    Design|Planning|Implementation|Testing) ;;
    *) continue ;;
  esac

  VERSION_DIR="${f%status.md}"
  MISSING=""
  check_exit_artifact() {
    # 优先检查暂存区（git cat-file），回退检查工作目录
    if ! git cat-file -e ":$1" 2>/dev/null && [ ! -f "$1" ]; then
      MISSING="${MISSING}\n  - $(basename "$1")"
    fi
  }

  case "$OLD_PHASE" in
    Design)
      check_exit_artifact "${VERSION_DIR}design.md"
      check_exit_artifact "${VERSION_DIR}review_design.md" ;;
    Planning)
      check_exit_artifact "${VERSION_DIR}plan.md"
      check_exit_artifact "${VERSION_DIR}review_planning.md" ;;
    Implementation)
      check_exit_artifact "${VERSION_DIR}review_implementation.md" ;;
    Testing)
      check_exit_artifact "${VERSION_DIR}test_report.md"
      check_exit_artifact "${VERSION_DIR}review_testing.md" ;;
  esac

  if [ -n "$MISSING" ]; then
    echo "❌ 阶段出口门禁（${OLD_PHASE} → ${NEW_PHASE}）：以下必要产出物缺失："
    echo -e "$MISSING"
    echo "   请补充完整后再推进阶段。"
    exit 1
  fi
done
```

---

## 6. Git Hooks：软警告（21 个）

post-commit 在 commit 完成后执行，不阻断工作流。输出警告信息，AI 看到后可自行修复并追加 commit。

> **`--no-verify` 与 post-commit**：`--no-verify` 只跳过 pre-commit 和 commit-msg，**不跳过 post-commit**。即使 AI 使用了 `--no-verify` 绕过硬拦截，21 个软警告仍然会正常执行并输出到终端。

### 公共基础设施

所有 Warning 共用以下逻辑获取上下文：

```bash
# 获取本次 commit 变更的文件列表
CHANGED=$(git diff-tree --no-commit-id --name-only -r HEAD)

# 定位当前版本目录
VERSION_DIR=$(echo "$CHANGED" | grep -oE 'docs/v[0-9]+\.[0-9]+/' | head -1)
if [ -z "$VERSION_DIR" ]; then
  VERSION_DIR=$(find docs/ -name "status.md" -path "*/v*/status.md" \
    -exec ls -t {} + 2>/dev/null | head -1 | sed 's/status\.md$//')
fi
STATUS_FILE="${VERSION_DIR}status.md"

# 输出格式：统一前缀，便于 AI 识别和人工过滤
warn() { echo "⚠️  [post-commit] $1"; }
```

**通过/失败判定**：每个 Warning 独立运行，输出 `⚠️` 前缀的警告行。无警告输出 = 通过。Warning 之间互不阻断。

> **`set -e` 注意**：post-commit dispatcher 不得启用 `set -e`，否则 grep 无匹配（退出码 1）会中断后续 Warning。各 Warning 脚本中的 grep 已加 `|| true` 防护。

### Warning 6：文档阶段出现代码文件变更

| 项 | 值 |
|---|---|
| 对应规则 | ai_workflow.md 阶段转换规则 |
| 触发条件 | status.md 当前阶段为 Proposal/Requirements/Design/Planning |

```bash
if [ ! -f "$STATUS_FILE" ]; then exit 0; fi
PHASE=$(grep '^_phase:' "$STATUS_FILE" | sed 's/^_phase:[[:space:]]*//' | tr -d '[:space:]')
[ -z "$PHASE" ] && PHASE=$(awk -F'|' '/\| 当前阶段/ {gsub(/^[ \t]+|[ \t]+$/,"",$3); print $3; exit}' "$STATUS_FILE")
case "$PHASE" in
  Proposal|Requirements|Design|Planning)
    CODE_FILES=$(echo "$CHANGED" | grep -vE '\.(md|txt|yaml|yml|json)$' || true)
    CODE_FILES=$(echo "$CODE_FILES" | head -5)
    if [ -n "$CODE_FILES" ]; then
      warn "当前阶段为 $PHASE，但检测到代码文件变更："
      echo "$CODE_FILES" | sed 's/^/     /'
      warn "请确认是否应先完成文档阶段"
    fi ;;
esac
```

### Warning 7：CR 必填字段完整性

| 项 | 值 |
|---|---|
| 对应规则 | cr_template.md §1-§3, §6 |
| 触发条件 | 本次 commit 包含 `docs/*/cr/CR-*.md` 文件变更 |

```bash
CR_FILES=$(echo "$CHANGED" | grep -E 'docs/.*/cr/CR-.*\.md$' || true)
# 占位符排除规则：模板中的 <角色>/<做什么> 等尖括号占位、"- ..." 省略号、
# 纯空表格行（只有 | 和空格）、未勾选的 [ ]是 [ ]否 均不算实质内容
for cr in $CR_FILES; do
  [ ! -f "$cr" ] && continue
  # §1 变更意图（排除 <xxx> 占位符和 ... 省略号）
  if grep -q '## 1\. 变更意图' "$cr"; then
    awk '/## 1\. 变更意图/{f=1;next} /^##/{f=0}
      f && NF>0 && !/<[^>]+>/ && !/^[ \t]*-?[ \t]*\.\.\.[ \t]*$/' "$cr" \
      | grep -q . || warn "$cr: §1 变更意图为空（或仅含模板占位符）"
  fi
  # §2 变更点（排除 ... 省略号）
  if grep -q '## 2\. 变更点' "$cr"; then
    awk '/## 2\. 变更点/{f=1;next} /^##/{f=0}
      f && NF>0 && !/^[ \t]*-?[ \t]*\.\.\.[ \t]*$/' "$cr" \
      | grep -q . || warn "$cr: §2 变更点为空（或仅含模板占位符）"
  fi
  # §3 影响面（排除 ... 省略号、未勾选的 [ ]是 [ ]否、纯空表格行）
  if grep -q '## 3\. 影响面' "$cr"; then
    awk '/## 3\. 影响面/{f=1;next} /^## [0-9]/{f=0}
      f && NF>0 && !/^[ \t]*-?[ \t]*\.\.\.[ \t]*$/ && !/\[ \]是.*\[ \]否/ && !/^[ \t]*\|[ \t|:-]*$/' "$cr" \
      | grep -q . || warn "$cr: §3 影响面为空（或仅含模板占位符）"
  fi
  # §6 验收标准（至少一条 GWT，Given 前不能是 <前置条件> 占位）
  if grep -q '## 6\. 验收与验证' "$cr"; then
    awk '/## 6\. 验收与验证/{f=1;next} /^## [0-9]/{f=0}
      f && /Given / && !/<[^>]+>/' "$cr" \
      | grep -q . || warn "$cr: §6 缺少 GWT 验收标准（或仅含模板占位符）"
  fi
done
```

### Warning 8：阶段产出文件存在性

| 项 | 值 |
|---|---|
| 对应规则 | 各 phase 输出要求 |
| 触发条件 | 本次 commit 包含 `status.md` 变更 |

**阶段→必须存在的产出文件**：

| 当前阶段 | 检查的文件 | 检查语义 |
|---------|-----------|---------|
| Requirements | `proposal.md` | 上一阶段产出，必须存在 |
| Design | `requirements.md` | 上一阶段产出，必须存在 |
| Planning | `design.md` | 上一阶段产出，必须存在 |
| Implementation | `plan.md` | 上一阶段产出，必须存在 |
| Testing | （不检查） | 本阶段产出 test_report.md 允许后补 |
| Deployment | `test_report.md` | 上一阶段产出必须存在 |

> **Minor 简化流程豁免**：如 status.md 变更摘要中包含 `[Minor]` 标记，跳过 Requirements 阶段对 `proposal.md` 的检查（Minor 流程合并了 Proposal + Requirements）。

```bash
if [ ! -f "$STATUS_FILE" ]; then exit 0; fi
PHASE=$(grep '^_phase:' "$STATUS_FILE" | sed 's/^_phase:[[:space:]]*//' | tr -d '[:space:]')
[ -z "$PHASE" ] && PHASE=$(awk -F'|' '/\| 当前阶段/ {gsub(/^[ \t]+|[ \t]+$/,"",$3); print $3; exit}' "$STATUS_FILE")
IS_MINOR=$(grep -c '\[Minor\]' "$STATUS_FILE" || true)

check_exists() {
  [ ! -f "${VERSION_DIR}$1" ] && warn "当前阶段 $PHASE，但 $1 不存在"
}

case "$PHASE" in
  Requirements)
    [ "$IS_MINOR" -eq 0 ] && check_exists "proposal.md" ;;
  Design)
    check_exists "requirements.md" ;;
  Planning)
    check_exists "design.md" ;;
  Implementation)
    check_exists "plan.md" ;;
  Testing)
    ;; # test_report.md 本阶段产出，允许后补
  Deployment)
    check_exists "test_report.md" ;;
esac
```

### Warning 9：REQ 引用存在性

| 项 | 值 |
|---|---|
| 对应规则 | R6（lessons_learned.md） |
| 触发条件 | 本次 commit 包含 `plan.md` 或 `design.md` 变更 |

```bash
DOC_FILES=$(echo "$CHANGED" | grep -E '(plan|design)\.md$' || true)
[ -z "$DOC_FILES" ] && exit 0
REQ_FILE="${VERSION_DIR}requirements.md"
[ ! -f "$REQ_FILE" ] && { warn "requirements.md 不存在，无法校验 REQ 引用"; exit 0; }

# 提取 requirements.md 中定义的 REQ-ID
# 默认格式：REQ-NNN（如 REQ-001）；如项目使用 REQ-FUNC-001 等带模块前缀的格式，
# 请将下方正则调整为 REQ-[A-Z]+-[0-9]{3} 或项目实际约定
REQ_PATTERN='REQ-[0-9]{3}'
DEFINED=$(grep -oE "$REQ_PATTERN" "$REQ_FILE" | sort -u)

for doc in $DOC_FILES; do
  [ ! -f "$doc" ] && continue
  REFS=$(grep -oE "$REQ_PATTERN" "$doc" | sort -u)
  for ref in $REFS; do
    echo "$DEFINED" | grep -qx "$ref" || warn "$doc 引用了 $ref，但 requirements.md 中不存在"
  done
done
```

### Warning 10：基线版本可达性

| 项 | 值 |
|---|---|
| 对应规则 | 00-change-management.md 基线验证 |
| 触发条件 | 本次 commit 包含 `status.md` 变更 |

```bash
[ ! -f "$STATUS_FILE" ] && exit 0
BASELINE=$(grep '^_baseline:' "$STATUS_FILE" | awk '{print $2}')
[ -z "$BASELINE" ] && exit 0  # Git-Hook 4 已拦截空值
git rev-parse --verify "${BASELINE}^{commit}" 2>/dev/null || \
  warn "基线版本 $BASELINE 不可达（git rev-parse 失败）"
```

### Warning 11：文档变更日志同步

| 项 | 值 |
|---|---|
| 对应规则 | 05-implementation.md 阶段文档回填 |
| 触发条件 | 本次 commit 包含 `requirements.md` / `design.md` / `plan.md` 变更 |

```bash
for doc_name in requirements.md design.md plan.md; do
  echo "$CHANGED" | grep -q "$doc_name" || continue
  doc_path="${VERSION_DIR}${doc_name}"
  [ ! -f "$doc_path" ] && continue
  if ! grep -qE '(变更记录|版本|修订|Changelog)' "$doc_path"; then
    warn "$doc_name 被修改但未找到变更记录章节"
  fi
done
```

### Warning 12：CR 影响面与 diff 一致性

| 项 | 值 |
|---|---|
| 对应规则 | review_template.md AC-05 |
| 触发条件 | 存在 Active CR 且本次 commit 包含代码文件变更 |

```bash
# 口径：所有 Active CR 的 §3.3 声明取并集，校验"每个变更文件至少被某个 CR 覆盖"
[ ! -f "$STATUS_FILE" ] && exit 0
ACTIVE_CRS=$(awk -F'|' '{gsub(/[ \t]/,"",$2); gsub(/[ \t]/,"",$3)}
  $2 ~ /^CR-[0-9]{8}-[0-9]{3}$/ && ($3=="Accepted"||$3=="InProgress")
  {print $2}' "$STATUS_FILE")
[ -z "$ACTIVE_CRS" ] && exit 0

CODE_CHANGED=$(echo "$CHANGED" | grep -vE '\.(md|txt|yaml|yml|json)$' || true)
[ -z "$CODE_CHANGED" ] && exit 0

ALL_DECLARED=""
for cr_id in $ACTIVE_CRS; do
  CR_FILE=$(find "${VERSION_DIR}cr/" -name "${cr_id}*.md" 2>/dev/null | head -1)
  if [ -z "$CR_FILE" ]; then
    warn "Active CR $cr_id 的 CR 文件不存在"; continue
  fi
  DECLARED=$(awk '/### 3\.3/{found=1;next} /^#/{found=0} found && /\|/' "$CR_FILE" \
    | awk -F'|' '{gsub(/^[ \t]+|[ \t]+$/,"",$2);
      if($2!="" && $2!~/^-+$/ && $2!~/影响模块/ && $2!~/影响文件/) print $2}')
  if [ -z "$DECLARED" ]; then
    warn "$cr_id: §3.3 代码影响为空，但本次有代码变更"
  else
    ALL_DECLARED="${ALL_DECLARED}
${DECLARED}"
  fi
done

if [ -n "$ALL_DECLARED" ]; then
  for changed_file in $CODE_CHANGED; do
    COVERED=false
    while IFS= read -r decl; do
      [ -z "$decl" ] && continue
      echo "$changed_file" | grep -Fq "$decl" && { COVERED=true; break; }
    done <<< "$ALL_DECLARED"
    [ "$COVERED" = false ] && \
      warn "$changed_file 不在任何 Active CR 的 §3.3 声明范围内"
  done
fi
```

### Warning 13：部署阶段 CR 子集验证

| 项 | 值 |
|---|---|
| 对应规则 | 07-deployment.md 门禁 |
| 触发条件 | 当前阶段 = Deployment |

```bash
[ ! -f "$STATUS_FILE" ] && exit 0
PHASE=$(grep '^_phase:' "$STATUS_FILE" | sed 's/^_phase:[[:space:]]*//' | tr -d '[:space:]')
[ -z "$PHASE" ] && PHASE=$(awk -F'|' '/\| 当前阶段/ {gsub(/^[ \t]+|[ \t]+$/,"",$3); print $3; exit}' "$STATUS_FILE")
[ "$PHASE" != "Deployment" ] && exit 0

BASELINE=$(grep '^_baseline:' "$STATUS_FILE" | awk '{print $2}')
[ -z "$BASELINE" ] && exit 0

ACTIVE_CRS=$(awk -F'|' '{gsub(/[ \t]/,"",$2); gsub(/[ \t]/,"",$3)}
  $2 ~ /^CR-[0-9]{8}-[0-9]{3}$/ && ($3=="Accepted"||$3=="InProgress")
  {print $2}' "$STATUS_FILE")
[ -z "$ACTIVE_CRS" ] && exit 0

COMMITS=$(git log "${BASELINE}..HEAD" --format=%B 2>/dev/null)
for cr_id in $ACTIVE_CRS; do
  echo "$COMMITS" | grep -q "$cr_id" || \
    warn "Active CR $cr_id 未出现在 ${BASELINE}..HEAD 的 commit message 中"
done
```

### Warning 14：设计文档决策记录非空

| 项 | 值 |
|---|---|
| 对应规则 | 03-design.md 完成条件 |
| 触发条件 | 本次 commit 包含 `design.md` 变更 |

```bash
echo "$CHANGED" | grep -q 'design\.md$' || exit 0
DESIGN="${VERSION_DIR}design.md"
[ ! -f "$DESIGN" ] && exit 0
HAS_RECORD=$(awk -F'|' '
  /^### 技术决策/{found=1; next}
  found && /^#/{found=0}
  found && /\|/ && !/---/ && !/编号.*决策项/ && !/决策项.*用户选择/ {
    gsub(/^[ \t]+|[ \t]+$/, "", $4);
    if ($4 != "" && $4 !~ /^[ \t]*$/) { print; exit }
  }
' "$DESIGN")
[ -z "$HAS_RECORD" ] && warn "design.md 的技术决策表中'用户选择'列全部为空"
```

### Warning 15：测试报告覆盖 CR 验收标准

| 项 | 值 |
|---|---|
| 对应规则 | 06-testing.md 门禁 |
| 触发条件 | 本次 commit 包含 `test_report.md` 变更且存在 Active CR |

```bash
echo "$CHANGED" | grep -q 'test_report\.md$' || exit 0
[ ! -f "$STATUS_FILE" ] && exit 0

ACTIVE_CRS=$(awk -F'|' '{gsub(/[ \t]/,"",$2); gsub(/[ \t]/,"",$3)}
  $2 ~ /^CR-[0-9]{8}-[0-9]{3}$/ && ($3=="Accepted"||$3=="InProgress")
  {print $2}' "$STATUS_FILE")
[ -z "$ACTIVE_CRS" ] && exit 0

TEST_REPORT="${VERSION_DIR}test_report.md"
[ ! -f "$TEST_REPORT" ] && { warn "test_report.md 不存在"; exit 0; }

for cr_id in $ACTIVE_CRS; do
  CR_FILE=$(find "${VERSION_DIR}cr/" -name "${cr_id}*.md" 2>/dev/null | head -1)
  [ -z "$CR_FILE" ] && continue
  GWT_COUNT=$(grep -cE '^- Given ' "$CR_FILE" 2>/dev/null || echo 0)
  [ "$GWT_COUNT" -eq 0 ] && continue
  grep -q "$cr_id" "$TEST_REPORT" || \
    warn "$cr_id 有 $GWT_COUNT 条 GWT 验收标准，但 test_report.md 中未引用该 CR"
done
```

### Warning 16：test_report 证据与结论完整性（准备交付时触发）

| 项 | 值 |
|---|---|
| 对应规则 | enhance.md 落地项 B（审计与证据补强） |
| 触发条件 | status.md `_phase` 为 Testing/Deployment，且 `_run_status=wait_confirm` 或 `_change_status=done` |

> 只在“准备交付”信号出现时触发，避免日常小步提交产生 warning fatigue。

```bash
PHASE=$(grep '^_phase:' "$STATUS_FILE" | sed 's/^_phase:[[:space:]]*//' | tr -d '[:space:]')
RUN_STATUS=$(grep '^_run_status:' "$STATUS_FILE" | awk '{print $2}')
CHANGE_STATUS=$(grep '^_change_status:' "$STATUS_FILE" | awk '{print $2}')

case "$PHASE" in
  Testing|Deployment)
    [ "$RUN_STATUS" != "wait_confirm" ] && [ "$CHANGE_STATUS" != "done" ] && exit 0

    TEST_REPORT="${VERSION_DIR}test_report.md"
    [ ! -f "$TEST_REPORT" ] && { warn "W16: ${TEST_REPORT} 不存在，交付前必须补齐"; exit 0; }

    # 检查 1：证据存在性（命令块/证据链接/CR验证证据表，至少满足其一）
    HAS_CMD_BLOCK=$(awk '
      /```(bash|sh)[ \t]*$/{in_block=1; next}
      in_block && /```/{in_block=0; next}
      in_block{
        line=$0
        gsub(/^[ \t-]+/, "", line)
        gsub(/[ \t]+$/, "", line)
        if(line!="" && line!="..." && line !~ /^<[^>]+>$/) {print 1; exit}
      }
    ' "$TEST_REPORT")

    HAS_EVID_LINE=$(grep -nE '^(\*\*证据\*\*：|证据：|证据链接：|- 完整报告链接：).+' "$TEST_REPORT" 2>/dev/null \
      | grep -vF '命令输出/日志/截图链接（如适用）' \
      | grep -vE '\.\.\.|<[^>]+>' | head -1 || true)

    HAS_CR_EVID=$(awk -F'|' '
      $0 ~ /^\|[ \t]*CR-[0-9]{8}-[0-9]{3}[ \t]*\|/ {
        gsub(/^[ \t]+|[ \t]+$/, "", $5);
        gsub(/^[ \t]+|[ \t]+$/, "", $6);
        if ($6 == "通过" && $5 != "" && $5 != "..." && $5 !~ /^<[^>]+>$/) {print 1; exit}
      }
    ' "$TEST_REPORT")

    if [ -z "$HAS_CMD_BLOCK" ] && [ -z "$HAS_EVID_LINE" ] && [ -z "$HAS_CR_EVID" ]; then
      warn "W16: test_report.md 中未找到有效证据（请补充命令块/证据链接/CR验证证据表，至少满足其一）"
    fi

    # 检查 2：整体结论可判定
    CONCLUSION=$(grep -E '^-[[:space:]]*整体结论[：:]' "$TEST_REPORT" \
      | sed 's/^-[[:space:]]*整体结论[：:][[:space:]]*//;s/[[:space:]]*$//' \
      | head -1 || true)
    if [ -z "$CONCLUSION" ]; then
      warn 'W16: test_report.md 的"整体结论"为空，交付前必须填写'
    elif ! echo "$CONCLUSION" | grep -qE '^(通过|不通过)$'; then
      warn "W16: test_report.md 的\"整体结论\"必须为\"通过\"或\"不通过\"（当前值: ${CONCLUSION}）"
    elif [ "$CONCLUSION" = "不通过" ]; then
      warn 'W16: test_report.md 的整体结论为"不通过"，禁止进入确认/交付'
    fi
    ;;
esac
```

### Warning 17：plan.md 任务缺少验证命令（准备交付时触发）

| 项 | 值 |
|---|---|
| 对应规则 | enhance.md 落地项 C（验收命令强化） |
| 触发条件 | status.md `_run_status=wait_confirm` 或 `_change_status=done` 且存在 plan.md |

```bash
RUN_STATUS=$(grep '^_run_status:' "$STATUS_FILE" | awk '{print $2}')
CHANGE_STATUS=$(grep '^_change_status:' "$STATUS_FILE" | awk '{print $2}')
[ "$RUN_STATUS" != "wait_confirm" ] && [ "$CHANGE_STATUS" != "done" ] && exit 0

PLAN="${VERSION_DIR}plan.md"
[ ! -f "$PLAN" ] && exit 0

TASK_COUNT=$(grep -cE '^### (T[0-9]|任务)' "$PLAN" || echo 0)
[ "$TASK_COUNT" -eq 0 ] && exit 0

MISSING=$(awk '
  function flush(){
    if(task_title!="" && has_cmd==0) {
      missing++
      print "  - " task_title
    }
  }
  /^### (T[0-9]+|任务)/{
    flush()
    task_title=$0
    has_cmd=0
    in_verify=0
    next
  }
  /验证方式/ {in_verify=1}
  in_verify && /^- *命令：/{
    if(match($0, /`[^`]+`/)) {
      cmd=substr($0, RSTART+1, RLENGTH-2)
      gsub(/^[ \t]+|[ \t]+$/, "", cmd)
      if(cmd!="" && cmd!="..." && cmd !~ /^<[^>]+>$/) has_cmd=1
    }
  }
  END{
    flush()
  }
' "$PLAN")

if [ -n "$MISSING" ]; then
  warn 'W17: plan.md 存在缺少验证命令的任务（请在"验证方式"中补充可复现命令）：'
  echo "$MISSING" | head -20
fi
```

### Warning 18：高风险变更缺少 CR 声明（高风险路径触发）

| 项 | 值 |
|---|---|
| 对应规则 | enhance.md 落地项 D（高风险触发器） |
| 触发条件 | commit 变更命中“高风险路径模式”且存在非文档文件变更 |

> 高风险路径模式集中配置在 post-commit dispatcher 顶部变量区的 `HIGH_RISK_PATTERNS`，便于单处维护。

```bash
# 注意：不要排除 yaml/yml/json（k8s/openapi 等高风险配置常为 YAML/JSON）
CHANGED_FILES=$(echo "$CHANGED" | grep -vE '\.(md|txt)$' || true)
[ -z "$CHANGED_FILES" ] && exit 0

# 解析 HIGH_RISK_PATTERNS 命中高风险文件（示例：匹配 api/* / db/migrations/* / auth/* / infra/* 等）
HIGH_RISK=""
IFS=';' read -ra PATTERN_GROUPS <<< "$HIGH_RISK_PATTERNS"
for f in $CHANGED_FILES; do
  for group in "${PATTERN_GROUPS[@]}"; do
    patterns="${group%%:*}"
    label="${group##*:}"
    IFS='|' read -ra pats <<< "$patterns"
    for pat in "${pats[@]}"; do
      case "$f" in
        $pat) HIGH_RISK="${HIGH_RISK}\n  $f ($label)"; break 2 ;;
      esac
    done
  done
done
[ -z "$HIGH_RISK" ] && exit 0

# 有高风险变更：要求存在 Active CR，且 CR §3.4 至少勾选 1 项高风险项
ACTIVE_CRS=$(awk -F'|' '{gsub(/[ \t]/,"",$2); gsub(/[ \t]/,"",$3)}
  $2 ~ /^CR-[0-9]{8}-[0-9]{3}$/ && ($3=="Accepted"||$3=="InProgress")
  {print $2}' "$STATUS_FILE")

if [ -z "$ACTIVE_CRS" ]; then
  warn "W18: 检测到高风险路径变更，但无 Active CR："
  echo -e "$HIGH_RISK" | head -5
  warn "W18: 建议创建 CR 并在 §3.4 勾选高风险项"
  exit 0
fi

HAS_ANY_FLAG=false
for cr_id in $ACTIVE_CRS; do
  CR_FILE=$(find "${VERSION_DIR}cr/" -name "${cr_id}*.md" 2>/dev/null | head -1)
  [ -z "$CR_FILE" ] && continue
  awk '
    /^### 3\.4/{in_section=1; next}
    in_section && /^### /{exit}
    in_section && /^## /{exit}
    in_section && /^- \[[xX✓]\]/{print 1; exit}
  ' "$CR_FILE" | grep -q 1 && { HAS_ANY_FLAG=true; break; }
done

if [ "$HAS_ANY_FLAG" = false ]; then
  warn "W18: 检测到高风险路径变更，但 Active CR 的 §3.4 未勾选任何高风险项："
  echo -e "$HIGH_RISK" | head -5
fi
```

---

## 7. 副作用分析与应对

### 7.1 Git Hooks 副作用

| # | 副作用 | 严重度 | 应对措施 |
|---|--------|--------|---------|
| 1 | **误报累积** | 中 | 硬拦截 7 个（含交付关口条件拦截+出口门禁）只卡确定性高的缺口；软警告 21 个不阻断，误报可忽略 |
| 2 | **AI 行为扭曲**（形式主义、重试循环） | 中 | 失败信息明确给出修复指引，避免 AI 猜测 |
| 3 | **`--no-verify` 逃逸** | 中 | 只跳过 pre-commit/commit-msg，post-commit 仍执行；AGENTS.md 禁止 AI 使用 `--no-verify` |
| 4 | **维护负担** | 低 | pre-commit / commit-msg / post-commit 各一个 dispatcher 脚本 |
| 5 | **安装分发问题** | 低 | 提供 `install-hooks.sh`，clone 后执行一次 |
| 6 | **git rebase/merge 边界** | 低 | rebase 时 hooks 逐 commit 触发，可能产生中间态误报；文档说明 |
| 7 | **性能开销** | 低 | 全部 shell 脚本，硬拦截 < 1 秒，软警告 < 2 秒 |
| 8 | **Hook 交互冲突** | 低 | dispatcher 统一管理，顺序执行，任一硬拦截失败即停止 |

### 7.2 Claude Code Hooks 副作用

| # | 副作用 | 严重度 | 应对措施 |
|---|--------|--------|---------|
| 1 | **CC-5 结构检查中间态误报** | 中 | 只挂在 Write（全量写入），不挂 Edit；AI 用 Edit 逐步补充时不触发 |
| 2 | **CC-5 导致 AI 形式主义**（塞空章节通过检查） | 低 | 只检查章节标题存在性，不检查内容；空章节问题留给 review 环节 |
| 3 | **CC-2 Stop 门禁过严**（AI 中途暂停也被拦） | 中 | 只在人工介入期 + 非 wait_confirm 时拦截；如误拦，用户说"继续"即可恢复 |
| 4 | **CC-6 review 追加检查误判**（用户主动要求重写） | 低 | 极少见；如发生，用户可手动编辑文件 |
| 5 | **CC-3 白名单过窄**（合法文件被拦截） | 低 | 白名单已覆盖各阶段产出物 + review + CR；如遗漏，加一行即可 |
| 6 | **性能开销** | 低 | shell + grep/awk，< 100ms；hooks 并行执行 |
| 7 | **CC-5 维护负担**（模板章节标题改了要同步） | 中 | 章节标题是框架稳定接口，变更频率低；脚本头部集中定义，改一处即可 |
| 8 | **CC-7 读取日志跨会话失效** | 低 | 日志按 `CLAUDE_SESSION_ID` 隔离，新会话重新读取是正确行为；/tmp 自动清理 |
| 9 | **CC-7 Bash 直接读取不经过 hook** | 低 | Claude Code 的 Read 工具覆盖绝大多数读取场景；Bash cat 读取极少见且通常是用户主动操作 |
| 10 | **CC-8 出口检查仅检查文件存在性** | 低 | 不检查文件内容质量，这是 review 的职责；CC-5 已检查结构完整性 |

### 7.3 排除的 Hooks

| 想法 | 排除理由 |
|------|---------|
| ~~**先读后写（R7）**~~ | ~~需要跨工具调用维护"已读文件"状态~~ → **已实现为 CC-7 + CC-7b**，通过 PostToolUse on Read 追踪解决了状态维护问题 |
| ~~**检查 AI 是否读了模板**~~ | ~~需要跟踪 Read 调用维护状态~~ → **已纳入 CC-7 入口门禁**，模板文件列入各阶段必读清单 |
| **内容质量判断**（目标是否 SMART、风险是否完整） | 语义判断，shell 脚本做不了。这是 review 环节的职责 |
| **语义一致性检查**（术语矛盾、需求冲突） | 同上，语义层面不适合程序化检查 |
| **UserPromptSubmit 注入上下文** | 每次用户输入都触发，过于频繁。SessionStart 已够用 |
| **CR Idea→Accepted 状态转换拦截** | 需要解析 CR 文件 diff 的语义，误报风险高；且动作发生在人机对话中，用户在场 |
| **检查 AI 是否与用户充分讨论** | 无法程序化判断"充分"，这是人的判断 |

---

## 8. 落地策略

### 8.1 分批上线

**Claude Code Hooks**：

| 批次 | hooks | 理由 |
|------|-------|------|
| **第一批** | CC-1（阶段推进拦截）+ CC-4（上下文注入+入口必读清单） | 最核心（阶段门禁）+ 零副作用（信息注入），立即见效 |
| **第二批** | CC-2（Stop 门禁）+ CC-3（文档作用域，全阶段）+ CC-7/CC-7b（入口门禁+Read 追踪） | 流程守卫完整化，入口门禁确保 AI 先读后写 |
| **第三批** | CC-5（结构校验）+ CC-6（review 追加保护）+ CC-8（出口门禁） | 产出物校验 + 出口门禁，需根据实际模板微调检查项 |

**Git Hooks**：

| 批次 | 内容 | 风险 |
|------|------|------|
| **第一批** | Git-Hook 1（commit-msg 格式）+ Git-Hook 3（.env 拦截） | 最低，格式检查无业务逻辑 |
| **第二批** | Git-Hook 2（CR-ID）+ Git-Hook 4（status.md YAML）+ Warning 6-10 | 低，条件触发，无 Active CR 时不生效 |
| **第三批** | Git-Hook 5 + Warning 11-18 | 中，涉及文档内容检查、CR 追溯与交付关口提示 |

### 8.2 安装与分发

**Git Hooks 安装**：

```bash
#!/bin/bash
# .aicoding/scripts/install-hooks.sh
# 从任意目录执行都能定位 repo root；支持备份现有 hooks；可重复安装
set -euo pipefail

# 定位 repo root（无论从哪个目录执行）
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
if [ -z "$REPO_ROOT" ]; then
  echo "❌ 当前不在 git 仓库中，请在项目目录下执行" >&2
  exit 1
fi

HOOK_DIR="${REPO_ROOT}/.git/hooks"
SCRIPT_DIR="${REPO_ROOT}/.aicoding/scripts/git-hooks"
BACKUP_DIR="${HOOK_DIR}/backup-$(date +%Y%m%d%H%M%S)"

# 依赖检查
for cmd in jq awk grep; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "❌ 缺少依赖: $cmd" >&2; exit 1; }
done

BACKED_UP=false
for hook in pre-commit commit-msg post-commit; do
  SOURCE="${SCRIPT_DIR}/${hook}"
  TARGET="${HOOK_DIR}/${hook}"

  if [ ! -f "$SOURCE" ]; then
    echo "⚠️  源文件不存在，跳过: $SOURCE"
    continue
  fi

  # 备份已有 hook（非本框架安装的）
  if [ -f "$TARGET" ]; then
    if ! grep -q '# aicoding-hooks-managed' "$TARGET" 2>/dev/null; then
      [ "$BACKED_UP" = false ] && mkdir -p "$BACKUP_DIR" && BACKED_UP=true
      cp "$TARGET" "${BACKUP_DIR}/${hook}"
      echo "📦 已备份原有 $hook → ${BACKUP_DIR}/${hook}"
    fi
  fi

  cp "$SOURCE" "$TARGET"
  chmod +x "$TARGET"
  echo "✅ 已安装 $hook"
done

echo ""
echo "✅ Git hooks 安装完成"
[ "$BACKED_UP" = true ] && echo "📦 原有 hooks 已备份至 ${BACKUP_DIR}/"
```

**Claude Code Hooks 配置**：

Claude Code hooks 通过 `.claude/settings.json` 配置，无需安装脚本。配置内容见 §4.2。

> 注意：Claude Code 在启动时快照 hooks 配置。修改 settings.json 后需通过 `/hooks` 菜单确认变更生效。

### 8.3 文件结构

```
.aicoding/
├── phases/                          ← 阶段定义
├── templates/                       ← 文档模板
├── scripts/
│   ├── install-hooks.sh             ← Git hooks 安装脚本
│   ├── git-hooks/
│   │   ├── pre-commit               ← Git-Hook 3-7 dispatcher
│   │   ├── commit-msg               ← Git-Hook 1-2 dispatcher
│   │   └── post-commit              ← Warning 6-18 dispatcher
│   └── cc-hooks/
│       ├── phase-gate.sh            ← CC-Hook 1：阶段推进拦截
│       ├── stop-gate.sh             ← CC-Hook 2：Stop 门禁
│       ├── doc-scope-guard.sh       ← CC-Hook 3：文档作用域控制（全阶段）
│       ├── inject-phase-context.sh  ← CC-Hook 4：会话上下文注入（含入口必读清单）
│       ├── doc-structure-check.sh   ← CC-Hook 5：产出物结构校验
│       ├── review-append-guard.sh   ← CC-Hook 6：review 追加保护
│       ├── phase-entry-gate.sh      ← CC-Hook 7：阶段入口门禁（全阶段）
│       ├── read-tracker.sh          ← CC-Hook 7b：Read 追踪器
│       └── phase-exit-gate.sh       ← CC-Hook 8：阶段出口门禁（Phase 03-06）
├── ai_workflow.md
├── hooks.md                         ← 本文件（方案说明）
└── AGENTS.md.template

.claude/
└── settings.json                    ← Claude Code hooks 配置
```

---

## 9. 与现有框架的关系

| 框架组件 | Git hooks 的作用 | Claude Code hooks 的作用 |
|---------|-----------------|------------------------|
| `ai_workflow.md` | commit 时验证阶段一致性 | 实时拦截阶段推进（CC-1）、Stop 门禁（CC-2）、上下文注入（CC-4）、入口/出口门禁（CC-7/CC-8） |
| `phases/*.md` | 各阶段完成条件由 AI 自我审查执行，post-commit 做事后提醒 | 入口门禁（CC-7）确保必读文件已读取；出口门禁（CC-8）确保产出物完整；CC-5 检查结构 |
| `templates/*.md` | Warning 7 检查 CR 必填字段 | CC-5 检查 proposal/requirements/CR 结构完整性；CC-7 确保模板被读取 |
| `lessons_learned.md` R1-R10 | R6（REQ 引用漂移）→ Warning 9；R8（TodoList）→ 不适合 hook | R7（先读后写）→ **CC-7 + CC-7b 程序化强制** |
| `AGENTS.md` | hooks 是 AGENTS.md 文本规则的程序化补充，不是替代 | 同左 |
| `review_template.md` | AC-05（diff-only 检查）→ Warning 12 | CC-6 保护 review 文件追加完整性；CC-2 确保审查文件存在；CC-8 确保 review 文件存在才能推进 |

**扩展路径**：如未来引入 CI/PR 流程，post-commit 软警告可直接升级为 CI 硬门禁，无需重构。

---

## 10. 决策记录

| 日期 | 决策 | 理由 |
|------|------|------|
| 2026-02-10 | 采用纯本地 Git hooks 方案 | 多 AI 工具本地协作、无 CI，本地 hooks 是最小成本方案 |
| 2026-02-10 | 硬拦截 7 个（含交付关口条件拦截+出口门禁）+ 软警告 21 个分层 | 确定性高的检查硬拦截；有边界情况的检查移入软警告；交付关口补充条件拦截减少漏检 |
| 2026-02-10 | 排除"先读后写" hook | 工程复杂度高，跨会话状态维护不可靠 |
| 2026-02-10 | `--no-verify` 风险接受 | 只跳过 pre-commit/commit-msg，post-commit 仍执行；AGENTS.md 文本层禁止 |
| 2026-02-10 | 分三批上线 | 渐进式引入，每批验证后再扩展 |
| 2026-02-10 | 引入 Claude Code hooks 层（6 个） | Phase 00-02 锁定 Claude Code，可利用其 hooks 做实时行为控制 |
| 2026-02-10 | hooks 只管流程和结构，不管内容质量 | 质量判断是人和 review 的职责；程序化检查只做确定性高的结构/流程校验 |
| 2026-02-10 | CC-5 用 PostToolUse 而非 PreToolUse | 文件已写入后反馈给 AI 自动修正，体验优于反复拦截 |
| 2026-02-10 | 脚本目录放在 .aicoding/scripts/ 下 | 框架自包含，可整体复制到其他项目 |
| 2026-02-10 | `_run_status` / `_workflow_mode` 迁入 YAML front matter | 原表格行存枚举列表不可解析；YAML 字段可用 `grep + awk` 直接提取单值 |
| 2026-02-11 | `_change_status` / `_phase` 迁入 YAML front matter | 避免从 Markdown 表格取值的格式漂移风险；脚本统一从 YAML 取值 |
| 2026-02-11 | Git-Hook 4 扩展校验 `_change_status` / `_phase` | W16/W17 依赖这两个字段；枚举值校验防止拼写错误导致门禁静默跳过 |
| 2026-02-11 | W16/W17 绑定“准备交付”信号 | 仅 `_run_status=wait_confirm` 或 `_change_status=done` 时触发，减少 warning fatigue |
| 2026-02-11 | W16/W17 关键节点升级为条件硬拦截 | 只卡 Deployment/Done 交付关口，避免漏检且不影响日常提交节奏 |
| 2026-02-11 | 高风险路径模式集中配置到 `HIGH_RISK_PATTERNS` | 单处维护，W18 与未来高风险判断统一复用 |
| 2026-02-10 | 统一 review 文件命名为 `review_<stage>.md` | 消除 `review.md` 与 `review_<stage>.md` 双轨导致的门禁/保护不一致 |
| 2026-02-10 | PreToolUse 用 `exit 2` + stderr，PostToolUse/Stop 用 JSON `decision` | 遵循 Claude Code 官方协议；PreToolUse 的 `exit 2` 更简洁，PostToolUse/Stop 需要 JSON 传递 reason |
| 2026-02-10 | Git-Hook 4 锚定 status.md 第 1 行为 `---` | 避免正文中的 `---` 分隔线被误当 front matter |
| 2026-02-10 | CC hooks 优先从 `file_path` 反推版本目录 | 多版本并存时 `find ... ls -t` 可能拿错版本；从工具输入的路径反推更精确 |
| 2026-02-10 | install-hooks.sh 支持备份 + 幂等 + repo root 定位 | 避免覆盖项目原有 hooks；支持从任意目录执行 |
| 2026-02-10 | CC-5 勾选符号兼容 `[✓]` 和 `[x]`/`[X]` | 不同编辑器/习惯使用不同勾选符号 |
| 2026-02-10 | 创建实际脚本文件（落地） | 方案从"仅设计"变为"可安装可执行"，交付稳定性从 0 到 1 |
| 2026-02-12 | CC hooks 从 6 个扩展到 9 个（CC-7/7b/8） | 解决 AI 不读输入就写产出、产出不完整就推进阶段的问题 |
| 2026-02-12 | CC-3 文档作用域控制扩展到全阶段 | 原仅覆盖 Phase 00-02，扩展后 Phase 03-07 也受白名单约束 |
| 2026-02-12 | CC-4 增强：注入阶段入口必读清单 | 新会话开始时 AI 即知道需要读取哪些文件 |
| 2026-02-12 | CC-7 实现"先读后写"（原排除项） | 通过 CC-7b PostToolUse on Read 追踪解决了跨工具状态维护问题 |
| 2026-02-12 | CC-8 阶段出口门禁仅在 Phase 03-06 生效 | Phase 00-02 由人工确认把关；Phase 07 有独立的部署确认流程 |
| 2026-02-12 | 各阶段定义文件增加入口协议和出口门禁章节 | 规则与程序化强制一一对应，消除"规则写了但没执行"的缝隙 |
| 2026-02-12 | status_template.md 增加 `_phase_log` 字段 | I/O 审计日志，记录每次阶段转换的入口读取和出口产出物状态 |
| 2026-02-12 | Git-Hook 7：阶段出口门禁落到 Git pre-commit 层 | CC-8 仅拦截 Claude Code，Codex 可绕过；Git hooks 是两者的最大公约数，补上 Codex 出口门禁缺口 |
| 2026-02-12 | AGENTS.md.template 补充阶段入口必读清单+出口产出物表 | Codex 仅支持 AGENTS.md 文本规则，显式列出入口/出口要求提高 Codex 合规概率 |
| 2026-02-12 | commit-msg CR 状态值 gsub 归一化 | status_template.md 显示值为 "In Progress"（含空格），awk 按 `\|` 分列后 `$3` 只取到 "In"；加 `gsub(/[ \t]/,"",\$3)` 统一为 "InProgress" |
| 2026-02-12 | Git-Hook 7 出口门禁改用 `git cat-file` + 文件系统双重检查 | 原 `[ ! -f ]` 只检查工作目录，暂存区有但未写盘的文件会漏检 |
| 2026-02-12 | CC-7 入口门禁通行证纳入版本目录 | 多版本并存时 v1.0 的通行证不应让 v2.0 跳过入口检查 |
| 2026-02-12 | CC-7 入口门禁必读模式绑定版本目录前缀 | 原 `status.md` 模式会匹配任意版本的 status.md，绑定 `${VERSION_DIR}status.md` 精确匹配 |
| 2026-02-12 | pre-commit YAML 字段解析统一为 `sed + tr` | `awk '{print \$2}'` 对含空格值截断；`sed` 取冒号后全部内容 + `tr -d '[:space:]'` 更健壮 |
| 2026-02-12 | Implementation 白名单增加 design.md/requirements.md 回写 | 实现阶段发现设计缺陷/需求偏差需回写修正，post-commit Warning 7 已覆盖追溯告警 |
