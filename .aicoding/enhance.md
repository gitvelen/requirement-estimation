# 流程增强落地方案

> 基于朋友的 9 条建议，结合现有框架覆盖度分析，制定具体落地方案。
>
> **原则**：
> - 只补真正的缺口，不重复建设已有能力
> - 门禁只做确定性检查，内容质量留给 review
> - 模板层"默认包含" > 流程层"靠记忆" > 门禁层"强制检查"
> - **上下文成本优先**：把“必须让 AI 记住的关键信息”集中放在少数固定位置（优先 `status.md` 索引），其余用链接/ID 引用；避免同一信息多处拷贝造成漂移；长日志/大输出不进主文档
>
> **前置条件**（否则本文的 Warning 方案无法生效）：
> - 已安装 Git hooks（至少 `post-commit` dispatcher 存在并提供 `warn()` 输出规范）
> - `docs/<版本号>/status.md` 存在且“当前阶段”字段可被脚本稳定解析

---

## 1. 评估总结

| # | 建议 | 现有覆盖度 | 判定 | 落地动作 |
|---|------|-----------|------|---------|
| 1 | 验收命令/清单 | 80% | 补强 | plan_template.md 任务级验证命令 |
| 2 | 禁止项 | 95% | 无需 | 已有 AGENTS.md 禁止条款 + hooks 拦截 |
| 3 | 文件所有权 | 60% | 不做 | 当前阶段不需要，CC-Hook 3 已按阶段限制文件范围 |
| 4 | 中间产物 | 85% | 补强 | 高风险触发器（合并到建议 9） |
| 5 | 举手阈值 | 90% | 补强 | ai_workflow.md 显式阈值清单 |
| 6 | 自动化门禁 | 70% | 补强（轻量） | 不在 hooks 中强跑测试/scan；用“证据+结论”门禁替代（落地项 B） |
| 7 | 失败策略 | 85% | 补强 | ai_workflow.md 失败处置协议 |
| 8 | 日志与审计 | 70% | 补强 | status.md 决策记录 + Warning 16 |
| 9 | 安全前置 | 85% | 补强 | 高风险触发器 + Warning 18 |

**实际需要落地的 4 项**（按优先级排序）：

1. **失败策略协议**（建议 7）— 多 AI 协作的稳定性关键
2. **审计与证据补强**（建议 8）— 可追溯性缺口
3. **验收命令强化**（建议 1）— plan.md 任务粒度补强
4. **高风险触发器**（建议 4+9）— 统一的风险感知机制

建议 2/3 不做额外动作。建议 6 不做“强跑测试/scan”的硬门禁，仅做证据与结论的轻量门禁补强（落地项 B）。建议 5 的举手阈值在现有 ai_workflow.md 基础上做小幅显式化。

### 1.1 上下文窗口成本控制（🔴 MUST，面向“开发成本可控”）

为了让流程增强不把维护成本推高（同时减少 AI 因上下文过大而遗漏规则），建议补充以下“上下文纪律”（不新增额外文件，优先复用现有文档）：

- **单一索引**：`status.md` 的「变更摘要/目标与成功指标/关键链接/Active CR」保持可在 1 屏扫完（建议 10–20 行级别摘要），把它当作会话启动的最小上下文包。
- **信息归位**（减少漂移）：验收命令写在 `plan.md`/`test_report.md`；范围与禁止项写在 `proposal/requirements`；风险触发与回滚写在 `CR`；不要把同一段内容复制到多份文档。
- **证据“摘要化”**：`test_report.md` 只保留“命令 + 关键输出摘要（建议 ≤20 行）+ 结论”，完整日志放外部链接或临时文件（避免撑爆上下文与仓库体积）。
- **按需读取**：AI 默认只读 `status.md` + 当前阶段产出物 + Active CR；其余文件在“触发器命中”或用户要求时再读（避免一次性加载全部文档）。

---

## 2. 落地项 A：失败策略协议（建议 7）

### 问题

AI 遇到失败（测试不过、依赖不可用、环境不一致）时，缺少标准处置流程，可能陷入重试风暴或盲目重构。当前 ai_workflow.md 有"连续 3 轮不收敛"的升级机制，但没有覆盖 Implementation/Testing 阶段的执行失败。

### 方案

在 ai_workflow.md 中新增"失败处置协议"，适用于 Phase 03-06 的 AI 自动期。

### 2.1 ai_workflow.md 新增章节

在"AI 自动期规则（Phase 03-06）"章节末尾追加：

```markdown
### 失败处置协议（🔴 MUST）

适用于 AI 自动期（Phase 03-06）遇到执行失败的场景。

**失败分级与处置**：

| 失败类型 | 示例 | 处置策略 |
|---------|------|---------|
| 可自动恢复 | 测试偶发失败、网络超时、依赖暂时不可用 | 重试，上限 2 次，间隔递增 |
| 需分析后修复 | 测试稳定失败、编译错误、类型不匹配 | 分析根因 → 修复 → 重新验证（计入轮次） |
| 需降级/拆分 | 性能不达标、方案不可行、依赖缺失 | 记录问题 → 提出降级/拆分方案 → 暂停等待确认 |
| 需人类决策 | 需求不明确、多方案无法取舍、安全/合规风险 | 立即暂停 → 列出选项与代价 → 等待用户决策 |

**强制规则**：
- 同一问题重试超过 2 次仍失败 → 禁止继续重试，必须升级到"需分析后修复"
- 同一问题修复超过 3 次仍失败 → 禁止继续修复，必须升级到"需人类决策"
- 升级时必须输出：问题描述、已尝试的方案、失败原因、建议的下一步选项
```

### 2.2 plan_template.md 任务详情新增字段

在每个任务详情的"依赖"之前追加：

```markdown
**失败处置**（可选，高风险任务必填）：
- 失败类型：<预期可能的失败场景>
- 处置：<重试/降级/人类决策>
- 回退方案：<如果本任务失败，如何回退到安全状态>
```

---

## 3. 落地项 B：审计与证据补强（建议 8）

### 问题

当前 status.md 有"阶段转换记录"和"紧急中断记录"，但缺少关键决策的结构化记录。test_report.md 模板已有证据结构，但没有门禁确保证据非空。

### 方案

最小可行审计：不加流水账，只在两个关键点补强。

### 3.1 status_template.md 变更

**3.1.1 `变更状态` 迁入 YAML front matter**

与 `_run_status` / `_workflow_mode` 同理，`变更状态` 从 Markdown 表格迁入 YAML front matter，避免脚本从表格取值的格式漂移风险。

YAML front matter 新增字段：

```yaml
---
_baseline: v1.0
_current: HEAD
_workflow_mode: manual
_run_status: running
_change_status: in_progress
_phase: Implementation
---
```

> - `_change_status`: 变更状态，枚举值：`in_progress` / `done`
> - `_phase`: 当前阶段，枚举值：`Proposal` / `Requirements` / `Design` / `Planning` / `Implementation` / `Testing` / `Deployment`
> - 解析方式：`grep '^_change_status:' status.md | awk '{print $2}'` / `grep '^_phase:' status.md | awk '{print $2}'`
> - Markdown 表格中的"变更状态"和"当前阶段"行保留为人类可读视图，但脚本统一从 YAML 取值

**理由**：
- `_change_status` 迁移：避免从 Markdown 表格取值的格式漂移风险（与 `_run_status` 同理）
- `_phase` 迁移：统一解析方式，pre-commit 可做枚举值校验，防止拼写错误（如 "Implmentation"）导致 post-commit 的 `case` 语句静默跳过所有检查

**3.1.2 阶段转换记录增加"关键决策"列**

在"阶段转换记录"表中增加"关键决策"列：

```markdown
## 阶段转换记录
| 从阶段 | 到阶段 | 日期 | 原因 | 触发人 | 关键决策 |
|---|---|---|---|---|---|
| - | Proposal | YYYY-MM-DD | 初始化 | User | - |
```

> "关键决策"列记录该阶段转换时的重要决策（如"跳过 Design 直接进 Planning，因为复用已有架构"），便于事后追溯。无特殊决策填 `-`。

### 3.2 scripts/git-hooks/pre-commit 修改（Git-Hook 4）

**变更内容**：扩展 YAML front matter 必填字段校验，新增 `_change_status` 和 `_phase` 的存在性与枚举值校验。

**修改位置**：Git-Hook 4（YAML front matter 校验）

**修改后的脚本片段**：

```bash
# === Git-Hook 4: status.md YAML front matter 校验 ===
if echo "$CHANGED" | grep -q 'status\.md$'; then
  VERSION_DIR=$(echo "$CHANGED" | grep 'status\.md$' | sed 's|/status\.md$|/|' | head -1)
  STATUS_FILE="${VERSION_DIR}status.md"

  if [ -f "$STATUS_FILE" ]; then
    # 检查必填字段存在性
    for field in _baseline _current _workflow_mode _run_status _change_status _phase; do
      if ! grep -q "^${field}:" "$STATUS_FILE"; then
        echo "❌ pre-commit 拦截：status.md 缺少必填字段 ${field}"
        exit 1
      fi
    done

    # 枚举值校验
    WORKFLOW_MODE=$(grep '^_workflow_mode:' "$STATUS_FILE" | awk '{print $2}')
    RUN_STATUS=$(grep '^_run_status:' "$STATUS_FILE" | awk '{print $2}')
    CHANGE_STATUS=$(grep '^_change_status:' "$STATUS_FILE" | awk '{print $2}')
    PHASE=$(grep '^_phase:' "$STATUS_FILE" | awk '{print $2}')

    case "$WORKFLOW_MODE" in
      manual|semi-auto|auto) ;;
      *) echo "❌ pre-commit 拦截：_workflow_mode 值非法（期望 manual/semi-auto/auto）"; exit 1 ;;
    esac

    case "$RUN_STATUS" in
      running|paused|wait_confirm|completed) ;;
      *) echo "❌ pre-commit 拦截：_run_status 值非法（期望 running/paused/wait_confirm/completed）"; exit 1 ;;
    esac

    case "$CHANGE_STATUS" in
      in_progress|done) ;;
      *) echo "❌ pre-commit 拦截：_change_status 值非法（期望 in_progress/done）"; exit 1 ;;
    esac

    case "$PHASE" in
      Proposal|Requirements|Design|Planning|Implementation|Testing|Deployment) ;;
      *) echo "❌ pre-commit 拦截：_phase 值非法（期望 Proposal/Requirements/Design/Planning/Implementation/Testing/Deployment）"; exit 1 ;;
    esac
  fi
fi
```

**理由**：
- W16/W17 依赖 `_change_status` 字段，必须在 pre-commit 确保其存在且合法
- `_phase` 枚举值校验防止拼写错误导致 post-commit 的 `case` 语句静默跳过检查

### 3.3 新增 Warning 16：test_report.md 证据与结论完整性（post-commit，软警告 / 条件硬拦截）

> **触发时机**：仅当 status.md 显示"准备交付"时触发（`_run_status=wait_confirm` 或 `_change_status=done`），避免日常小步提交产生 warning fatigue。
>
> **升级为硬拦截**：当本次提交将阶段推进到 Deployment 或将 `_change_status` 置为 `done` 时，W16 从软警告升级为 pre-commit 硬拦截（只卡关键节点）。

```bash
# === Warning 16: test_report.md 证据与结论完整性 ===
if [ -f "$STATUS_FILE" ]; then
  W16_PHASE=$(grep '^_phase:' "$STATUS_FILE" | awk '{print $2}')
  W16_RUN_STATUS=$(grep '^_run_status:' "$STATUS_FILE" | awk '{print $2}')
  W16_CHANGE_STATUS=$(grep '^_change_status:' "$STATUS_FILE" | awk '{print $2}')

  # 判断是否为"关键节点"提交（阶段推进到 Deployment 或变更状态置为 done）
  # 关键节点时升级为硬拦截（exit 1），否则为软警告（warn）
  W16_HARD=false
  if echo "$CHANGED" | grep -q 'status\.md$'; then
    STAGED_STATUS=$(git show ":${VERSION_DIR}status.md" 2>/dev/null)
    if [ -n "$STAGED_STATUS" ]; then
      NEW_PHASE=$(echo "$STAGED_STATUS" | grep '^_phase:' | awk '{print $2}')
      NEW_CHANGE=$(echo "$STAGED_STATUS" | grep '^_change_status:' | awk '{print $2}')
      [ "$NEW_PHASE" = "Deployment" ] && W16_HARD=true
      [ "$NEW_CHANGE" = "done" ] && W16_HARD=true
    fi
  fi

  # 仅在"准备交付"时触发
  case "$W16_PHASE" in
    Testing|Deployment)
      if [ "$W16_RUN_STATUS" = "wait_confirm" ] || [ "$W16_CHANGE_STATUS" = "done" ]; then
        TEST_REPORT="${VERSION_DIR}test_report.md"
        if [ -f "$TEST_REPORT" ]; then
          W16_FAIL=false

          # 检查 1：证据存在性
          HAS_CMD_BLOCK=$(awk '
            /```(bash|sh)[ \t]*$/{in=1; next}
            in && /```/{in=0; next}
            in{
              line=$0
              gsub(/^[ \t-]+/, "", line)
              gsub(/[ \t]+$/, "", line)
              if(line!="" && line!="..." && line !~ /^<[^>]+>$/) {print 1; exit}
            }
          ' "$TEST_REPORT")

          HAS_EVID_LINE=$(grep -nE '^(\\*\\*证据\\*\\*：|证据：|证据链接：|- 完整报告链接：).+' "$TEST_REPORT" 2>/dev/null \
            | grep -vF '命令输出/日志/截图链接（如适用）' \
            | grep -vE '\\.\\.\\.|<[^>]+>' | head -1)

          HAS_CR_EVID=$(awk -F'|' '
            $0 ~ /^\\|[ \t]*CR-[0-9]{8}-[0-9]{3}[ \t]*\\|/ {
              gsub(/^[ \t]+|[ \t]+$/, "", $5);
              gsub(/^[ \t]+|[ \t]+$/, "", $6);
              if ($6 == "通过" && $5 != "" && $5 != "..." && $5 !~ /^<[^>]+>$/) {print 1; exit}
            }
          ' "$TEST_REPORT")

          if [ -z "$HAS_CMD_BLOCK" ] && [ -z "$HAS_EVID_LINE" ] && [ -z "$HAS_CR_EVID" ]; then
            warn "test_report.md 中未找到有效证据：请补充"命令块/证据链接/CR验证证据表"（至少满足其一）"
            W16_FAIL=true
          fi

          # 检查 2：整体结论可判定
          CONCLUSION=$(grep -E '^-[[:space:]]*整体结论[：:]' "$TEST_REPORT" \
            | sed 's/^-[[:space:]]*整体结论[：:][[:space:]]*//;s/[[:space:]]*$//' \
            | head -1)
          if [ -z "$CONCLUSION" ]; then
            warn 'test_report.md 的"整体结论"为空，交付前必须填写'
            W16_FAIL=true
          elif ! echo "$CONCLUSION" | grep -qE '^(通过|不通过)$'; then
            warn "test_report.md 的"整体结论"必须为"通过"或"不通过"（当前值: ${CONCLUSION}）"
            W16_FAIL=true
          elif [ "$CONCLUSION" = "不通过" ]; then
            warn 'test_report.md 的整体结论为"不通过"，禁止进入确认/交付'
            W16_FAIL=true
          fi

          # 关键节点时升级为硬拦截
          if [ "$W16_HARD" = true ] && [ "$W16_FAIL" = true ]; then
            echo "❌ [W16 硬拦截] 关键节点（Deployment/Done）提交被阻止：test_report.md 证据或结论不完整"
            exit 1
          fi
        fi
      fi ;;
  esac
fi
```

---

## 4. 落地项 C：验收命令强化（建议 1）

### 问题

plan_template.md 的任务详情已有"验证方式"字段，但没有强制要求包含可执行命令。CR §6 已有 GWT + 验证方式，Warning 15 已检查 test_report 覆盖 CR。缺口在 plan.md 的任务粒度。

### 方案

强化 plan_template.md 的"验证方式"字段描述，并新增 Warning 17 检查。

### 4.1 plan_template.md 变更

将任务详情中的"验证方式"字段描述改为（与现有模板字段名保持一致）：

```markdown
**验证方式**（🔴 MUST，必须可复现）：
- 命令：`<具体命令，如 npm test、pytest tests/xxx、curl ...>`
- 预期结果：<命令的预期输出或判定标准>
- 补充验证（可选）：<手动检查项/人工检查点>
```

### 4.2 新增 Warning 17：plan.md 任务缺少验证命令（post-commit，软警告 / 条件硬拦截）

> **触发时机**：仅当 status.md 显示"准备交付"时触发（`_run_status=wait_confirm` 或 `_change_status=done`），与 W16 一致。
>
> **升级为硬拦截**：与 W16 相同，当本次提交将阶段推进到 Deployment 或将 `_change_status` 置为 `done` 时升级。

```bash
# === Warning 17: plan.md 任务验证方式完整性 ===
[ ! -f "$STATUS_FILE" ] && exit 0

# 仅在"准备交付"时触发
W17_RUN_STATUS=$(grep '^_run_status:' "$STATUS_FILE" | awk '{print $2}')
W17_CHANGE_STATUS=$(grep '^_change_status:' "$STATUS_FILE" | awk '{print $2}')
[ "$W17_RUN_STATUS" != "wait_confirm" ] && [ "$W17_CHANGE_STATUS" != "done" ] && exit 0

# 判断是否为关键节点（复用 W16 的 W16_HARD 变量，或独立判断）
W17_HARD=false
if echo "$CHANGED" | grep -q 'status\.md$'; then
  STAGED_STATUS=$(git show ":${VERSION_DIR}status.md" 2>/dev/null)
  if [ -n "$STAGED_STATUS" ]; then
    NEW_PHASE=$(echo "$STAGED_STATUS" | grep '^_phase:' | awk '{print $2}')
    NEW_CHANGE=$(echo "$STAGED_STATUS" | grep '^_change_status:' | awk '{print $2}')
    [ "$NEW_PHASE" = "Deployment" ] && W17_HARD=true
    [ "$NEW_CHANGE" = "done" ] && W17_HARD=true
  fi
fi

PLAN="${VERSION_DIR}plan.md"
[ ! -f "$PLAN" ] && exit 0

# 统计任务数（以 ### T 或 ### 任务 开头的章节）
TASK_COUNT=$(grep -cE '^### (T[0-9]|任务)' "$PLAN" || echo 0)
[ "$TASK_COUNT" -eq 0 ] && exit 0

# 统计缺少“有效命令”的任务（排除 `...` / `<占位符>`）
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
  warn "plan.md 存在缺少验证命令的任务（请在"验证方式"中补充可复现命令）："
  echo "$MISSING" | head -20
  # 关键节点时升级为硬拦截
  if [ "$W17_HARD" = true ]; then
    echo "❌ [W17 硬拦截] 关键节点（Deployment/Done）提交被阻止：plan.md 存在缺少验证命令的任务"
    exit 1
  fi
fi
```

---

## 5. 落地项 D：高风险触发器（建议 4+9 合并）

### 问题

当代码变更涉及高风险路径（API 契约、DB schema、权限/安全、不可逆配置）时，应触发更严格的检查。当前 CR 模板 §3 已有"强制清单触发器"（勾选项），但没有门禁验证"勾了没有"。

### 方案

新增 Warning 18，当检测到高风险路径变更时，检查是否存在 Active CR 且 CR §3.4 至少勾选了 1 项高风险项（不强绑定到具体类别，降低误报）。

### 5.1 高风险路径配置

高风险路径模式集中定义在 post-commit dispatcher 顶部的变量区（与公共基础设施同层），W18 和未来其他需要高风险判断的 Warning 统一引用，避免多处维护。

**post-commit 顶部变量区新增**：

```bash
# === 高风险路径模式（集中配置，按项目实际调整） ===
# 格式：case 模式|标签，用 ; 分隔多组
# W18 及其他需要高风险判断的 Warning 统一引用此变量
HIGH_RISK_PATTERNS="db/migrations/*|db/schema*|*/migration*:schema/migration;auth/*|*/permission*|*/rbac*:auth/permission;api/*|*/swagger*|*/openapi*|*.proto:API contract;infra/*|k8s/*|terraform/*:infrastructure"
```

> 修改高风险路径时只需改这一处，文档中的路径表仅作说明用途。

### 5.2 高风险路径分类说明

复用 CR 模板 §3 的强制清单触发器类别：

| 触发器 | 路径模式（示例，按项目调整） |
|--------|--------------------------|
| API 契约变更 | `api/**`, `**/swagger.*`, `**/openapi.*`, `**/*.proto` |
| 数据迁移/schema | `db/migrations/**`, `db/schema.*`, `**/migration*` |
| 权限/安全 | `auth/**`, `**/permission*`, `**/rbac*` |
| 不可逆配置 | `infra/**`, `k8s/**`, `terraform/**` |

### 5.3 新增 Warning 18：高风险变更缺少 CR 声明（post-commit，软警告）

```bash
# === Warning 18: 高风险变更 CR 声明检查 ===
# 引用顶部变量区的 HIGH_RISK_PATTERNS
# 注意：不要排除 yaml/yml/json（k8s/openapi 等高风险配置常为 YAML/JSON）
CHANGED_FILES=$(echo "$CHANGED" | grep -vE '\.(md|txt)$' || true)
[ -z "$CHANGED_FILES" ] && exit 0

# 解析集中配置的高风险路径模式
HIGH_RISK=""
IFS=';' read -ra PATTERN_GROUPS <<< "$HIGH_RISK_PATTERNS"
for f in $CHANGED_FILES; do
  for group in "${PATTERN_GROUPS[@]}"; do
    patterns="${group%%:*}"
    label="${group##*:}"
    IFS='|' read -ra pats <<< "$patterns"
    for pat in "${pats[@]}"; do
      case "$f" in $pat) HIGH_RISK="${HIGH_RISK}\n  $f ($label)"; break 2 ;; esac
    done
  done
done
[ -z "$HIGH_RISK" ] && exit 0

# 有高风险变更：要求存在 Active CR 且 §3.4 至少勾选 1 项
if [ -f "$STATUS_FILE" ]; then
  ACTIVE_CRS=$(awk -F'|' '{gsub(/[ \t]/,"",$2); gsub(/[ \t]/,"",$3)}
    $2 ~ /^CR-[0-9]{8}-[0-9]{3}$/ && ($3=="Accepted"||$3=="InProgress")
    {print $2}' "$STATUS_FILE")
  if [ -z "$ACTIVE_CRS" ]; then
    warn "检测到高风险路径变更，但无 Active CR："
    echo -e "$HIGH_RISK" | head -5
    warn "建议创建 CR 并在 §3.4 勾选对应高风险项"
  else
    # 检查任意 Active CR 的 §3.4 是否至少勾选了 1 项（不绑定具体类别）
    HAS_ANY_FLAG=false
    for cr_id in $ACTIVE_CRS; do
      CR_FILE=$(find "${VERSION_DIR}cr/" -name "${cr_id}*.md" 2>/dev/null | head -1)
      [ -z "$CR_FILE" ] && continue
      if grep -qE '^- \[[xX✓]\]' "$CR_FILE"; then
        HAS_ANY_FLAG=true; break
      fi
    done
    if [ "$HAS_ANY_FLAG" = false ]; then
      warn "检测到高风险路径变更，但 Active CR 的 §3.4 未勾选任何高风险项："
      echo -e "$HIGH_RISK" | head -5
    fi
  fi
fi
```

---

## 6. 落地项 E：举手阈值显式化（建议 5）

### 问题

ai_workflow.md 已有"连续 3 轮不收敛"和"紧急中断"机制，但缺少 Implementation 阶段的显式举手条件清单。

### 方案

在 ai_workflow.md 的"AI 自动期规则"中追加显式阈值清单。

### 6.1 ai_workflow.md 新增内容

在"失败处置协议"之后追加：

```markdown
### 举手阈值（🔴 MUST）

以下情况 AI 必须立即暂停并征询用户，不得默默推进：

| 触发条件 | 处置 |
|---------|------|
| 需求不清且影响范围/验收标准 | 暂停，列出 1-3 个具体问题 |
| 发现需要"禁止的变更"（见 05-implementation.md） | 暂停，建议走 CR 修订 |
| 连续 2 次验证失败且原因不明 | 暂停，列出已尝试方案和失败原因 |
| 需要危险 Git 操作（`--no-verify`/`--force`/`reset --hard`） | 暂停，说明必要性 |
| 发现安全/合规风险（密钥泄露、权限越界） | 立即停止，报告风险 |
| 实际工作量显著超出 plan.md 预估 | 暂停，建议调整计划 |
```

---

## 7. 变更汇总

### 7.1 文件变更清单

| 文件 | 变更类型 | 变更内容 |
|------|---------|---------|
| `.aicoding/ai_workflow.md` | 追加 | 失败处置协议 + 举手阈值（2 个章节） |
| `.aicoding/templates/plan_template.md` | 修改 | 验证方式字段强化 + 失败处置字段 |
| `.aicoding/templates/status_template.md` | 修改 | YAML 新增 `_change_status` + `_phase` + 阶段转换记录增加"关键决策"列 |
| `.aicoding/scripts/git-hooks/pre-commit` | 修改 | Git-Hook 4 扩展：新增 `_change_status` 和 `_phase` 的存在性与枚举值校验 |
| `.aicoding/scripts/git-hooks/post-commit` | 追加 | Warning 16/17/18（3 个软警告） |
| `.aicoding/hooks.md` | 追加 | 新增 hooks 的文档说明 + 决策记录 |

### 7.2 新增门禁清单

| # | 名称 | 层级 | 类型 | 触发条件 |
|---|------|------|------|---------|
| Warning 16 | test_report 证据与结论完整性 | post-commit | 软警告 → 条件硬拦截 | 准备交付时；推进 Deployment 或 Done 时升级硬拦截 |
| Warning 17 | plan.md 验证命令完整性 | post-commit | 软警告 → 条件硬拦截 | 准备交付时；推进 Deployment 或 Done 时升级硬拦截 |
| Warning 18 | 高风险变更 CR 声明 | post-commit | 软警告 | 高风险路径文件变更（CR §3.4 至少勾 1 项） |

### 7.3 不做的事（明确排除）

| 排除项 | 理由 |
|--------|------|
| 建议 2（禁止项模板化） | 已有 AGENTS.md 禁止条款 + 05-implementation.md 禁止变更清单，覆盖度 95% |
| 建议 3（文件所有权/受保护路径） | 当前阶段不需要，CC-Hook 3 已按阶段限制文件范围 |
| 建议 6（自动化门禁默认开启） | 不在 hooks 中强跑测试/scan（耗时且误伤风险）；以“证据+结论”轻量门禁替代，未来有 CI 再升级为硬门禁 |
| 在 hooks 中强跑测试命令 | 耗时且可能误伤；以"证据存在性"检查替代 |
| 结构化操作日志（流水账） | 维护成本高、形式主义风险大；用 git log + status.md 决策记录替代 |
| CC-Hook 扩展（失败策略章节检查） | design.md/plan.md 的失败策略是"建议填写"而非"必须存在"，不适合硬门禁 |

---

## 8. 执行顺序

```
第 1 批（文档层变更，低风险）
├── 修改 ai_workflow.md（追加失败处置协议 + 举手阈值）
├── 修改 plan_template.md（强化验证方式 + 新增失败处置字段）
└── 修改 status_template.md（阶段转换记录加列）

第 2 批（脚本层变更）
├── 修改 post-commit（追加 Warning 16/17/18）
└── 更新 hooks.md（文档同步）

验证
├── 手动测试 Warning 16/17/18（各触发一次）
└── 确认现有 hooks 不受影响
```

---

## 9. 决策记录

| 日期 | 决策 | 理由 |
|------|------|------|
| 2026-02-10 | 不做受保护路径机制（建议 3） | 用户判断当前阶段不需要，CC-Hook 3 已按阶段限制文件范围 |
| 2026-02-10 | 失败策略写入 ai_workflow.md 而非单独文件 | 与现有"连续 3 轮不收敛"机制同层，便于 AI 统一遵循 |
| 2026-02-10 | 审计采用"最小可行"方案（决策列 + 证据检查） | 避免流水账式日志的形式主义风险 |
| 2026-02-10 | 高风险触发器用软警告而非硬拦截 | 路径模式匹配可能误报（项目结构差异大）；软警告提醒即可，不卡住开发 |
| 2026-02-10 | 排除建议 2 的额外动作；建议 6 仅做轻量门禁 | 禁止项覆盖度已高；自动化门禁不强跑测试/scan，先用“证据+结论”替代，未来有 CI 再升级 |
| 2026-02-10 | 排除 CC-Hook 扩展检查失败策略章节 | 失败策略是"建议"而非"必须"，不适合程序化强制 |
| 2026-02-10 | W16/W17 绑定"交付信号"而非仅看阶段/文件变更 | 日常小步提交不触发，仅 `_run_status=wait_confirm` 或变更状态=Done 时输出，减少 warning fatigue |
| 2026-02-10 | W16 追加"整体结论可判定"检查 | 确定性检查（通过/不通过二选一），防止"有证据但没结论"或"结论不通过仍交付"的偏差 |
| 2026-02-10 | W18 高风险路径模式集中到 post-commit 顶部变量区 | 单处配置，避免脚本/文档多处维护；项目结构变化时只改一处 |
| 2026-02-10 | `变更状态` 迁入 YAML front matter（`_change_status`） | 与 `_run_status` 同理，避免从 Markdown 表格取值的格式漂移风险；脚本统一用 `grep '^_change_status:'` 解析 |
| 2026-02-10 | W16/W17 关键节点（Deployment/Done）升级为硬拦截 | 只卡交付关口，噪声趋近于零；日常提交仍为软警告不影响开发节奏 |
| 2026-02-10 | W18 简化为"CR §3.4 至少勾选 1 项"而非按类别匹配 | 类别绑定误报率高（路径模式与勾选项难以精确对应）；"至少勾 1 项"已足够提醒开发者审视风险 |
| 2026-02-11 | `_phase` 迁入 YAML front matter + pre-commit 枚举值校验 | 统一解析方式（与 `_change_status` 一致），防止拼写错误（如 "Implmentation"）导致 post-commit 的 `case` 语句静默跳过检查 |
| 2026-02-11 | pre-commit Git-Hook 4 扩展校验 `_change_status` 和 `_phase` | W16/W17 依赖这两个字段，必须在 pre-commit 确保其存在且合法，否则 post-commit 的检查前置条件不成立 |
