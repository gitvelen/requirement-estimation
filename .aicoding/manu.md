# AI 协作流程使用手册（manu）

## 1. 这份手册解决什么问题
这套流程的目标是：让 AI 开发可控、可追溯、可回滚。  
你可以把它理解为“AI 在执行，人类在关键点拍板”。

核心原则只有三条：
1. 先澄清再开发（目标、边界、验收标准必须说清楚）
2. 所有阶段有证据（文档、测试、审查记录）
3. 高风险操作必须人工确认

---

## 2. 总体流程（7+1 阶段）
流程按 `status.md` 的 `_phase` 推进：

1. `ChangeManagement`（可选：版本内变更才走）
2. `Proposal`
3. `Requirements`
4. `Design`
5. `Planning`
6. `Implementation`
7. `Testing`
8. `Deployment`

人工介入重点：
- **Phase 00-02（人工介入期）**：必须人工审查并确认才能进下一阶段
- **Phase 03-06（AI 自动期）**：AI 可自动推进，但遇到风险/不收敛必须暂停等人工决策
- **Phase 07（部署）**：验收环境可自动部署，生产环境或高风险变更必须人工确认

---

## 3. 先做分级：Major / Minor / Hotfix（人工拍板）

| 级别 | 典型场景 | 人工要做什么 |
|---|---|---|
| Major | 新功能、API/DB 变更、权限安全、跨模块 | 确认走完整 8 阶段 |
| Minor | 小功能、普通 Bug、UI 微调、文档修正 | 确认可走简化审查（但测试与部署不简化） |
| Hotfix | 线上紧急修复、低风险单点改动 | 确认是否满足热修边界（文件数、无 API/DB/权限安全变更） |

说明：AI 可以建议分级，但最终由人工确认。

---

## 4. 人工必须做的事情（重点）

### A. 每次变更开始前
1. 确认这是“当前版本补丁”还是“新版本迭代”
2. 如果是版本内变更：创建 CR（`docs/<版本>/cr/CR-*.md`）
3. 在 `status.md` 明确：
   - `_change_level`（major/minor/hotfix）
   - `_phase`
   - `_baseline`
   - Active CR 列表

### B. Phase 00-02（必须人工确认推进）
1. 指定审查者（`@review Claude` 或 `@review Codex`）
2. 阅读对应 `review_*.md`（问题和结论）
3. 明确给出“进入下一阶段”的确认指令
4. 更新 `status.md` 的 `_phase`（并同步表格中的“当前阶段”）

### C. Phase 03-06（AI主导，人工做关键决策）
1. 查看 AI 的里程碑展示（尤其 Implementation 中间成果）
2. 如果出现以下情况，必须人工决策：
   - 连续 3 轮不收敛
   - 需求不清/方案冲突
   - 安全合规风险
   - 工作量明显超计划
3. 决定是继续修复、降级方案，还是回退阶段

### D. Phase 07（部署与验收）
1. 确认目标环境（STAGING/TEST/PROD）
2. 若是 PROD 或高风险项（API 契约、数据迁移、权限安全、不可逆配置），先人工批准再部署
3. 验收后给出明确结论：
   - 通过：置完成态（`_change_status: done` + `_run_status: completed`）
   - 不通过：回到 Testing/Implementation 修复

---

## 5. 落地到具体项目：人工操作清单

### 5.1 首次接入（一次性）

#### 步骤 1：复制框架文件
```bash
# 将框架目录复制到目标项目根目录
cp -r /path/to/framework/.aicoding /path/to/target-project/
cd /path/to/target-project
```

#### 步骤 2：准备文档目录
```bash
mkdir -p docs/v1.0
```

#### 步骤 3：配置 AGENTS.md（必须）
```bash
# 重命名模板文件
cp .aicoding/AGENTS.md.template AGENTS.md
# 或者如果项目已有 CLAUDE.md，合并以下内容到文件中
```

编辑 `AGENTS.md` 或 `CLAUDE.md`，添加：
```markdown
# 引入 AI 协作框架
请严格遵循 `.aicoding/ai_workflow.md` 中定义的工作流规则。

关键规则：
- 阶段推进前必须读取 `docs/<版本号>/status.md` 获取当前状态
- 人工介入期（Phase 00-02）完成产出后必须等待人工确认
- AI 自动期（Phase 03-06）收敛后可自动推进
- 所有写入操作前必须先读取对应的必读文件（见各阶段定义）

## 团队角色（根据实际情况调整）
- 阶段确认人：@tech-lead
- 生产部署审批：@ops-lead
- 安全审查：@security-team（涉及权限/鉴权变更时）

## 文档语言约定（根据团队习惯调整）
- 流程文档（status/proposal/requirements/design/plan）：中文
- 代码注释和 API 文档：英文
- 测试报告：中文
```

#### 步骤 4：配置 aicoding.config.yaml（核心）

编辑 `.aicoding/aicoding.config.yaml`，根据项目技术栈修改：

```yaml
# 1. 测试命令（必须修改）
result_gate_test_command: "uv run pytest -q --tb=short"
# 常见替换示例：
# - Node.js: "npm test"
# - Go: "go test ./..."
# - Java: "mvn test"
# - Python (pytest): "pytest -q"
# - 无测试: ""（留空，但不推荐）

# 2. 构建命令（必须修改）
result_gate_build_command: "cd frontend && npm run build"
# 常见替换示例：
# - 纯后端 Go: "go build ./cmd/..."
# - Python: "python -m build"
# - Java: "mvn package"
# - 无构建步骤: ""（留空）

# 3. 类型检查命令（根据语言调整）
result_gate_typecheck_command: "uv run python scripts/incremental_static_gate.py"
# 常见替换示例：
# - TypeScript: "tsc --noEmit"
# - Go: "go vet ./..."
# - Python (mypy): "mypy src/"
# - 无类型检查: ""（留空）

# 4. 门禁阈值（根据团队规模和项目复杂度调整）
spotcheck_ratio_percent: 10          # 抽检比例，建议 5-15
spotcheck_min: 1                     # 最少抽检项数
spotcheck_max: 5                     # 最多抽检项数
minor_max_diff_files: 10             # Minor 最大改动文件数
minor_max_new_gwts: 5                # Minor 最大新增验收标准数
hotfix_max_diff_files: 3             # Hotfix 最大改动文件数
quality_debt_max_total: 10           # 质量债务上限（小项目可降到 5）
tech_debt_max_total: 15              # 技术债务上限（大项目可提高到 20）

# 5. 入口门禁模式（根据环境选择）
entry_gate_mode: block               # 生产环境推荐 block，开发环境可用 warn
```

#### 步骤 5：安装 Git Hooks
```bash
bash .aicoding/scripts/install-hooks.sh

# 验证安装成功
ls -la .git/hooks/pre-commit .git/hooks/commit-msg
# 应该看到两个可执行文件
```

#### 步骤 6：配置 .gitignore
```bash
echo ".aicoding/.claude/" >> .gitignore
echo "docs/*/review_*.md.bak" >> .gitignore
```

#### 步骤 7：创建初始文档
```bash
# 复制模板
cp .aicoding/templates/status_template.md docs/v1.0/status.md
cp .aicoding/templates/proposal_template.md docs/v1.0/proposal.md
cp .aicoding/templates/requirements_template.md docs/v1.0/requirements.md

# 编辑 status.md，填写项目元信息
# - 项目名称
# - 版本号（v1.0）
# - 基线版本（如果是已有项目，先打 tag: git tag v1.0-baseline）
# - 技术栈描述
# - 部署环境列表
# - _phase: ChangeManagement（必须从这里开始）
```

#### 步骤 8：首次提交测试
```bash
# 提交框架文件
git add .aicoding/ AGENTS.md .gitignore
git commit -m "chore: setup aicoding framework"

# 提交初始文档（会触发门禁检查）
git add docs/v1.0/
git commit -m "chore: init v1.0 status"
# 如果 status.md 的 _phase 不是 ChangeManagement，pre-commit 会拦截
```

#### 步骤 9：可选自检
```bash
# 运行框架自带的测试套件
bash .aicoding/scripts/tests/run-all.sh
```

#### 步骤 10：项目特定调整（根据实际情况）

**如果有前后端分离**，调整契约验证脚本：
```bash
# 编辑 .aicoding/scripts/validate_api_contracts.sh
# 修改以下变量：
# - FRONTEND_API_CALLS_PATH（前端 API 调用扫描路径）
# - BACKEND_ROUTES_FILE（后端路由定义文件）
# - DESIGN_DOC_PATH（API 契约文档路径）
```

**如果有 CI/CD**，集成门禁检查：
```yaml
# 示例：.github/workflows/ci.yml
- name: Validate aicoding compliance
  run: bash .aicoding/scripts/tests/run-all.sh
```

**如果是已有项目**（非全新项目）：
```bash
# 1. 创建基线 tag
git tag v1.0-baseline

# 2. 在 status.md 中设置基线
_baseline: v1.0-baseline

# 3. 首次变更建议走 Minor 流程熟悉框架
```

**如果团队有特定文档规范**：
- 可以修改 `.aicoding/templates/` 下的模板文件
- 但必须保留机器可读块（`METADATA`、`GWT-ID`、`TEST-RESULT` 等）

**如果项目有架构文档/编码规范**：
- 在 `phases/03-design.md` 中添加架构文档到必读列表
- 在 `phases/05-implementation.md` 中添加编码规范到必读列表
- 在 `phases/07-deployment.md` 中添加部署手册到必读列表

**如果使用 Git Flow 或其他分支策略**：
- 在 `ai_workflow.md` 的 Hotfix 章节补充项目约定
- 确认主分支名称（默认假设为 `main` 或 `master`）

**如果团队已有验收标准 ID 规范**：
```yaml
# 在 aicoding.config.yaml 中修改
gwt_id_regex: ^GWT-REQ-C?[0-9]+-[0-9]+$
```

---

### 5.2 首次启动完整检查清单

```bash
# 1. 文件就位检查
[ -f .aicoding/aicoding.config.yaml ] && echo "✓ Config"
[ -f AGENTS.md ] || [ -f CLAUDE.md ] && echo "✓ Agent config"
[ -d docs/v1.0 ] && echo "✓ Version dir"
[ -f docs/v1.0/status.md ] && echo "✓ Status file"

# 2. Hooks 安装检查
[ -x .git/hooks/pre-commit ] && echo "✓ Pre-commit hook"
[ -x .git/hooks/commit-msg ] && echo "✓ Commit-msg hook"

# 3. 配置检查
grep -q "result_gate_test_command" .aicoding/aicoding.config.yaml && echo "✓ Test command configured"
grep -q "result_gate_build_command" .aicoding/aicoding.config.yaml && echo "✓ Build command configured"

# 4. 测试门禁是否生效
# 尝试修改 status.md 的 _phase 为非法值，应该被 pre-commit 拦截
```

---

### 5.3 每次新需求进入时
1. 判断：补丁（CR）还是新版本
2. 选分级：major/minor/hotfix
3. 确认验收标准（至少能判断 pass/fail）
4. 按阶段推进并在关键点做人工确认

---

## 6. 最容易踩的坑（必读）

| 问题 | 后果 | 解决方法 |
|------|------|---------|
| 忘记修改测试命令 | pre-commit 执行失败，无法提交 | 在 `aicoding.config.yaml` 中配置正确的测试命令 |
| 没有配置 AGENTS.md | AI 不知道要遵循框架规则 | 复制模板并添加框架引用 |
| 直接在主分支开发 | 违反 Git 管理规范，难以回滚 | 从主分支切出工作分支（`feat/<描述>` 或 `cr/<CR-ID>`） |
| 跳过 ChangeManagement 阶段 | pre-commit 拦截，无法提交 | 新建 status.md 时 `_phase` 必须从 `ChangeManagement` 开始 |
| Minor 变更触碰 REQ-C | pre-commit 硬拦截 | 必须升级为 Major 并执行完整流程 |
| Hotfix 修改了 _phase | pre-commit 拦截 | Hotfix 不推进阶段，只能修改 `_run_status`、`_change_status`、`_review_round` |
| 测试命令返回非零退出码 | 阶段推进被阻断 | 修复测试失败后再推进 |
| 阶段推进时缺少审查文件 | CC-8 hook 阻止写入 | 补充对应阶段的审查文件（`review_*.md`） |
| 忘记在 status.md 中重置 _review_round | 轮次累积超过 5 时 pre-commit 拦截 | 阶段切换时必须重置 `_review_round: 0` |
| 测试命令配置错误（如路径不对） | 每次 pre-commit 都失败 | 在项目根目录测试命令是否能正常执行 |

**建议**：先用一个小需求（真实的 Minor 级别变更）完整走一遍流程，熟悉各个门禁的触发时机。

---

## 7. 关键规范（不要踩线）

### 7.1 流程规范
1. `status.md` 是流程单一真相源，阶段与状态以它为准
2. 不要跳阶段推进（尤其 Proposal/Requirements/Design/Planning）
3. 不要绕过门禁提交（原则上禁止 `--no-verify`）
4. Hotfix 只做紧急修复，不扩范围
5. 完成态必须同步：`done` 和 `completed` 必须同时成立

### 7.2 文档规范
1. 不要修改机器可读块格式（`METADATA`、`GWT-ID`、`TEST-RESULT`、`MINOR-TESTING-ROUND` 等）
2. 阶段定义文件（`phases/*.md`）不建议修改，除非团队有特殊流程需求
3. 模板文件可以定制，但必须保留机器可读块

### 7.3 Git 规范
1. 不在主分支直接开发，必须切出工作分支
2. 禁止危险操作（`push --force`、`reset --hard`、`branch -D`）需用户授权
3. Commit message 格式：`<type>: <描述>`，有 CR 时加 `[CR-ID]`
4. 部署完成后在主分支打 tag（如 `v1.0`）
5. 非 PR 的主分支操作完成后，须将 commit 和 tag 一并 push 到远端

### 7.4 安全规范
1. 不要在代码/文档中硬编码密钥和敏感信息
2. 权限/鉴权变更必须走 Major 流程并经过安全审查
3. 生产环境部署必须人工确认

---

## 8. 推荐阅读顺序（新人上手）
1. `.aicoding/ai_workflow.md`（总规则）
2. `.aicoding/phases/*.md`（分阶段规则）
3. `.aicoding/STRUCTURE.md`（目录和文档约定）
4. `.aicoding/hooks.md`（门禁与告警机制）
5. `.aicoding/aicoding.config.yaml`（本项目阈值与命令）

如果只记一件事：**人工负责”决策和验收”，AI负责”执行和留证据”。**
