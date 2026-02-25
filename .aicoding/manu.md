# 项目建设操作手册（.aicoding）

> 目标：让你**不用记规则**也能把框架落地并顺畅迭代。  
> 细则与门禁以脚本为准：`.aicoding/scripts/`；流程规则见 `.aicoding/phases/` 与 `.aicoding/ai_workflow.md`。

---

## 1. 快速落地到你的项目（推荐）

> 以下命令默认在**项目根目录**执行。

### 1.1 前置条件

- 你的项目是 Git 仓库（能运行 `git status`）
- 依赖：`git`、`bash`、`awk`、`grep`、`sed`
- 若使用 Claude Code 的 **CC hooks**：额外需要 `jq`

### 1.2 落地步骤

1. **拷贝框架目录**
   ```bash
   cp -r /path/to/.aicoding .
   ```
   - 若项目已存在 `.aicoding/`：先备份再覆盖，避免误删自定义内容。

2. **创建项目根目录的 AI 入口指令**
   - 从 `.aicoding/AGENTS.md.template` 复制到项目根目录：`AGENTS.md`（或按你工具习惯用 `CLAUDE.md`）
   - 修改第一行的 `[项目名称]` / 版本号，其余保持不变即可

3. **按项目配置 `.aicoding/aicoding.config.yaml`**
   - **结果门禁命令（强烈建议填写）**：
     - `result_gate_test_command`
     - `result_gate_build_command`
     - `result_gate_typecheck_command`
   - **Hotfix 阈值**：`enable_hotfix`、`hotfix_max_diff_files`
   - **抽检比例**（Major 交付）：`spotcheck_ratio_percent/min/max`

4. **安装 Git hooks**
   ```bash
   bash .aicoding/scripts/install-hooks.sh
   ```
   - 行为：将 `pre-commit` / `commit-msg` / `post-commit` **复制**到 `.git/hooks/`
   - 备份：若检测到既有的非框架 hooks，会备份到 `.git/hooks/backup-<timestamp>/` 并在输出中提示路径

5. **（可选）启用 Claude Code 的 CC hooks**
   - 将 `.aicoding/.claude/settings.local.json` 的 `hooks` 字段合并到你项目的 `.claude/settings.local.json`
   - 若你项目已有该文件：**只合并 `hooks`**，保留已有 `permissions`
   - Codex 用户可跳过（Codex 不支持 CC hooks，仅受 Git hooks 约束）

6. **验证落地**
   ```bash
   ls -la .git/hooks/pre-commit .git/hooks/commit-msg .git/hooks/post-commit
   bash .aicoding/scripts/tests/run-all.sh
   ```

### 1.3 回滚（需要时）

1. 删除 `.aicoding/`
2. 从 `.git/hooks/backup-*` 恢复原 hooks（以 `install-hooks.sh` 输出为准）

---

## 2. 首次使用：先确认项目类型

```
你的项目属于哪种情况？
│
├── 全新项目（从零开始，无历史代码）
│   → 从阶段 01（提案）开始
│   → 版本号从 v1.0 开始
│
├── 存量项目 — 首次引入本框架
│   → 先建立基线：对当前生产代码打 tag（如 v1.0）
│   → 在 docs/<版本号>/status.md 写入 _baseline/_current
│   → 从阶段 01（提案）开始
│
└── 存量项目 — 后续迭代（已有版本记录）
    → 从阶段 00（变更管理）开始（CR）
    → 基线版本 = 上一版本 tag
```

---

## 3. 变更分级与流程选择（默认 major）

> 你可以直接说 `major` / `minor` / `hotfix`；不确定就按 `major` 走完整流程。

| 级别 | 适用场景 | 流程 | 关键约束 |
|------|---------|------|---------|
| **Major** | 新功能、API/DB/权限/安全变更、跨模块影响 | 完整 8 阶段（00–07） | 门禁与审查全量 |
| **Minor** | 单模块小改动、一般 Bug 修复、配置/文档修正 | 简化流程 | 仍需测试证据；需 `_change_level: minor`；触碰 `REQ-C` 或范围扩大必须升级 Major |
| **Hotfix** | 线上紧急修复、低风险单点变更 | 极速流程 | staged 文件数 ≤ `hotfix_max_diff_files`；不得涉及 API/DB/权限/安全 或 `REQ-C` |

补充：
- Minor/Hotfix 过程中发现复杂度超预期 → 必须暂停并建议升级为 Major。
- 触碰 `docs/vX.Y/` 且走 Minor/Hotfix 时：在对应 `status.md` 标注 `_change_level`（否则门禁按 Major 处理或告警）。

---

## 4. Major（完整 8 阶段）你需要做什么

> 详细规则以阶段文件为准：`.aicoding/phases/00-07-*.md`。

| 时期 | 阶段 | 你的动作（最少） |
|------|------|------------------|
| 人工介入期 | 00 变更管理 | 提出意图 → 确认基线 → 指定审查者（`@review Claude`/`@review Codex`）→ 明确“确认进入下一阶段” |
| 人工介入期 | 01 提案 | 回答澄清问题 → 审阅 `proposal.md` → 指定审查 → 确认进入需求 |
| 人工介入期 | 02 需求 | 逐条确认 REQ/GWT → 指定审查 → 确认进入设计 |
| AI 自动期 | 03–06 设计/计划/实现/测试 | 通常无需操作；**Major 交付需做一次人工抽检（spotcheck）**（见下） |
| AI 自动期（需确认） | 07 部署 | 阅读 `deployment.md` → 明确“确认部署” |

---

### 4.1 Major 人工抽检（spotcheck）

AI 在 `review_testing.md` 的摘要块里会给出：
- `SPOT_CHECK_GWTS`：建议你优先抽检的 GWT 列表
- `SPOTCHECK_FILE`：抽检记录文件路径（`docs/<版本号>/spotcheck_*.md`）

你需要做的：
1. 打开 `SPOTCHECK_FILE`，按模板填写并记录抽检结论（模板：`templates/spotcheck_template.md`）
2. 覆盖范围：`REQ-C:all + SPOT_CHECK_GWTS`
3. 表格里逐条填 `PASS/FAIL`，最后写 `SPOTCHECK_RESULT: pass|fail`（`pass` 才能继续部署）

---

## 5. Minor（小改动）流程

你需要做的：
1. 说明范围与验收标准（做什么/不做什么/验收口径）
2. 明确 `minor`（写入 `_change_level: minor`）
3. 审阅 `review_minor.md`
4. 确认部署（例如说“确认部署”）

AI 会做的：
- 合并 Proposal+Requirements，写入 `status.md` 的变更摘要与验收标准
- 合并 Design/Planning/Implementation 并直接编码
- 跑测试并给出证据：`test_report.md` 或 `status.md` 内联 `TEST-RESULT`（二选一）

---

## 6. Hotfix（紧急修复）流程

你需要做的：
1. 确认这是 hotfix（紧急、低风险、单点）
2. 确认边界：文件数不超限、不触碰 `REQ-C`、不涉及 API/DB/权限/安全
3. 审阅最小可复现验证结果

AI 会做的：
- 最小范围修复 + 最小验证
- 提交前缀使用 `fix:` 或 `fix(<scope>):`
- 若触碰 `docs/vX.Y/`：在对应 `status.md` 标注 `_change_level: hotfix`

---

## 7. 关键文件速查

| 文件/目录 | 作用 |
|---|---|
| `docs/<版本号>/status.md` | 单一真相源：阶段、基线、运行状态、Active CR |
| `docs/<版本号>/proposal.md` / `requirements.md` | 提案与可验收需求（含 GWT） |
| `docs/<版本号>/design.md` / `plan.md` | 设计与任务计划 |
| `docs/<版本号>/review_*.md` | 阶段审查（Major） |
| `docs/<版本号>/review_minor.md` | Minor 审查报告 |
| `docs/<版本号>/test_report.md` | 测试证据 |
| `docs/<版本号>/spotcheck_*.md` | Major 人工抽检记录 |
| `.aicoding/aicoding.config.yaml` | 阈值、结果门禁命令、入口门禁模式等 |

---

## 8. 故障排除（门禁/流程）

### 8.1 门禁误报/拦截如何排查

1. **复现**：在项目根目录直接运行对应 hook：
   - `bash .aicoding/scripts/git-hooks/pre-commit`
   - `bash .aicoding/scripts/git-hooks/commit-msg <msg-file>`
2. **定位规则**：看输出中的 gate/warning 编号，对应脚本在：
   - `.aicoding/scripts/git-hooks/*`
   - `.aicoding/scripts/git-hooks/warnings/w*.sh`
3. **处置**：
   - 规则正确：按提示补齐文档/证据/字段
   - 规则误报：记录最小复现条件并提修复任务（必要时走应急提交流程）

### 8.2 `VERIFICATION_COMMANDS` 必填（常见拦截点）

当 `review_implementation.md` / `review_testing.md` 的摘要块中 `REVIEW_RESULT: pass` 时，必须填写 `VERIFICATION_COMMANDS`（不可为空/占位）。示例：

```text
VERIFICATION_COMMANDS: uv run pytest -q --tb=short, npm test
```

### 8.3 临时禁用 CC hook（仅限故障窗口）

1. 修改项目 `.claude/settings.local.json` 中对应 hook 条目，临时注释目标脚本
2. 故障处理完立即恢复配置并回归验证

### 8.4 逃生通道（必须留痕）

1. AI 不得自行使用 `--no-verify`，必须先取得你的明确授权
2. 若紧急使用了逃生通道：commit message 必须包含 `[escape:<原因>]`
3. post-commit 会做逃生审计并告警，告警后必须补齐审计说明并尽快修复门禁规则
