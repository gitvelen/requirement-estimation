# 项目建设操作手册

> 本手册帮助你理解项目开发规则和流程，了解每个阶段你需要做什么、AI 会帮你做什么。
> 具体的流程定义和技术规范由 AI 自动遵循，你无需记忆。

## 框架部署到实际项目

### 部署步骤（详细）

以下步骤适用于真实项目落地，包含准备、拷贝、配置、验证与回滚要点。

1. **准备与前置条件**
   
   项目必须是 Git 仓库，且你对工作区有写入权限。建议在部署前先提交当前变更，避免混淆。
   
   必需依赖：`git`、`awk`、`grep`。如需使用 CC hooks，还需要 `jq`。

2. **选择落地方式**
   
   直接复制 `.aicoding/` 到项目根目录是推荐方式。若是 monorepo，仍建议放在仓库根目录，保持全仓统一规则。

3. **拷贝框架文件**
   
   ```bash
   cp -r /path/to/.aicoding <你的项目根目录>/
   cd <你的项目根目录>
   ```
   
   如果项目里已存在 `.aicoding/`，先备份再覆盖，避免误删自定义内容。

4. **安装 Git hooks**
   
   ```bash
   bash .aicoding/scripts/install-hooks.sh
   ```
   
   安装脚本会将 Git hooks（`pre-commit` / `commit-msg` / `post-commit`）链接到 `.git/hooks/`，已有的非框架 hooks 会自动备份到 `.git/hooks/.aicoding.backup/`。

5. **按项目实际配置**
   
   按下文“必须个性化修改的内容”完成 `AGENTS.md` 和 `aicoding.config.yaml` 的修改。

6. **验证部署**
   
   ```bash
   ls -la .git/hooks/pre-commit .git/hooks/commit-msg .git/hooks/post-commit
   bash .aicoding/scripts/tests/run-all.sh
   ```
   
   若自测失败，优先查看脚本输出，通常是依赖或权限问题。

7. **回滚（如需）**
   
   删除 `.aicoding/` 目录并恢复备份 hooks 即可；备份位于 `.git/hooks/.aicoding.backup/`。

### 必须复制的文件

| 目录/文件 | 用途 | 是否需要个性化 |
|---|---|---|
| `.aicoding/STRUCTURE.md` | 目录结构与约定 | 否 |
| `.aicoding/ai_workflow.md` | 工作流控制规则 | 否 |
| `.aicoding/manu.md` | 操作手册（本文件） | 否 |
| `.aicoding/hooks.md` | Hook 设计索引 | 否 |
| `.aicoding/phases/*.md` | 阶段流程定义 | 否 |
| `.aicoding/templates/*.md` | 文档模板 | 否（可按项目微调） |
| `.aicoding/scripts/` | 全部脚本（hooks + lib + tests） | 否 |
| `.aicoding/aicoding.config.yaml` | 框架配置 | **是**（见下） |
| `AGENTS.md` | AI 入口指令（项目根目录） | **是**（见下） |

### 必须个性化修改的内容

1. `AGENTS.md`（项目根目录）
   - 基于 `.aicoding/AGENTS.md.template` 创建
   - 修改第 1 行的 `[项目名称]` 和版本号
   - 其余内容保持不变即可

2. `aicoding.config.yaml` — 按项目实际情况调整：
   ```yaml
   # 结果门禁命令（必填，否则门禁跳过）
   result_gate_test_command: "npm test"        # 或 pytest / go test ./... 等
   result_gate_build_command: "npm run build"   # 或 go build ./... 等
   result_gate_typecheck_command: ""            # 如 tsc --noEmit，无则留空

   # Hotfix 策略
   enable_hotfix: true
   hotfix_max_diff_files: 3                    # 按项目规模调整

   # Minor 误标启发式阈值
   minor_max_diff_files: 10
   minor_max_new_gwts: 5

   # 抽检比例（major 交付时）
   spotcheck_ratio_percent: 10
   spotcheck_min: 1
   spotcheck_max: 5
   ```

3. Claude Code 用户还需配置 CC hooks：
   - 将 `.aicoding/.claude/settings.local.json` 的 `hooks` 部分合并到你项目的 `.claude/settings.local.json`
   - 如果项目已有 `.claude/settings.local.json`，只合并 `hooks` 字段，保留已有的 `permissions`
   - Codex 用户无需此步骤（Codex 不支持 CC hooks，仅受 Git hooks 约束）

### 不需要复制的内容

- `docs/` 目录：由框架在运行时自动创建（版本目录、主文档等）
- `.aicoding/enhance*.md` / `prop*.md` / `enr*.md`：框架自身的优化方案文档，与项目无关
- `.aicoding/.github/`：框架自身的 CI 配置（未来路线）

### 依赖检查

安装脚本会自动检查以下依赖：
- `jq`：JSON 解析（CC hooks 需要）
- `awk` / `grep`：文本处理（所有 hooks 需要）
- `git`：版本控制

如缺少依赖，脚本会报错提示安装。

### 验证安装

```bash
# 检查 Git hooks 是否安装成功
ls -la .git/hooks/pre-commit .git/hooks/commit-msg .git/hooks/post-commit

# 运行框架自测
bash .aicoding/scripts/tests/run-all.sh
```

---

## 项目类型判断（首次使用请先确认）

```
你的项目属于哪种情况？
│
├── 全新项目（从零开始，无历史代码）
│   → 跳过阶段 0（变更管理），从阶段 1（提案）开始
│   → 无需基线版本，版本号从 v1.0 开始
│   → 主文档（系统功能说明书等）在部署阶段首次创建
│
├── 存量项目 — 首次使用本框架
│   → 先建立基线：对当前生产代码打 tag（如 v1.0）
│   → 在 status.md 中填写基线版本
│   → 从阶段 1（提案）开始，描述本次迭代目标
│   → 建议同步初始化主文档（系统功能说明书等）
│
└── 存量项目 — 后续迭代（已有版本记录）
    → 从阶段 0（变更管理）开始，创建 CR
    → 基线版本 = 上一版本的 tag
    → 按 CR 流程推进
```

---

## 变更分级与流程选择（最新）

> 默认 `major`。你也可以直接声明 `minor` / `hotfix`，AI 会给出建议并等你确认。

| 级别 | 适用场景 | 流程 | 关键约束 |
|------|---------|------|---------|
| **Major** | 新功能、API/DB/权限/安全变更、跨模块影响 | 完整 8 阶段 | 需求与审查全量、门禁完整 |
| **Minor** | 单模块小功能、一般 Bug 修复、配置/文档修正 | 简化流程（见下） | 仍需完整测试与证据；需 `_change_level: minor`；触碰 `REQ-C` 或范围扩大必须升级 Major |
| **Hotfix** | 线上紧急修复、低风险单点变更 | 极速流程（见下） | staged 文件数 ≤ `hotfix_max_diff_files`；不得涉及 API/DB/权限/安全 或 `REQ-C` |

**补充说明**：
- 触碰 `docs/vX.Y/` 时必须在 `status.md` 标注 `_change_level: hotfix`；不触碰版本文档时可不创建 `status.md`。
- Minor/Hotfix 发现复杂度超预期 → 必须暂停并建议升级为 Major。

---

## 总览：你需要做什么 vs AI 帮你做什么（Major 完整流程）

整个项目建设分为 **8 个阶段**，按人工介入程度分为三个时期：

> **提示**：小改动可走 `minor`，紧急修复可走 `hotfix`；若不确定，一律按 `major` 完整流程。

| 时期 | 阶段 | 你的角色 | AI 的角色 |
|------|------|---------|----------|
| **人工介入期** | 00 变更管理 / 01 提案 / 02 需求 | 决策者、确认者 | 执行者、建议者 |
| **AI 自动期** | 03 设计 / 04 计划 / 05 实现 / 06 测试 | 旁观者（可随时介入） | 全自动执行+自我审查 |
| **AI 自动期（特殊）** | 07 部署 | 最终确认者 | 执行+暂停等你确认 |

---

## Minor 简化流程（小改动）

### 你需要做的

1. **说明范围与验收标准** — 做什么/不做什么/验收口径
2. **确认变更分级** — 明确 `minor`，AI 会写入 `_change_level`
3. **审阅审查报告** — 阅读 `review_minor.md`
4. **确认进入部署** — 说 "确认部署"

### AI 帮你做的（你不需要做）

- 合并 Proposal + Requirements，输出到 `status.md` 的变更摘要与验收标准
- 合并 Design/Planning/Implementation，直接编码并输出 `review_minor.md`
- 执行完整测试并给出证据（`test_report.md` 或 `status.md` 内联 `TEST-RESULT`）
- 如发现范围扩大、触碰 `REQ-C` 或跨模块影响 → 暂停并建议升级 Major

---

## Hotfix 极速流程（紧急修复）

> hotfix 不走 8 阶段流程，仅按此极速路径执行。

### 你需要做的

1. **确认这是 hotfix** — 仅紧急、低风险单点变更
2. **确认边界** — staged 文件数不超限、不触碰 `REQ-C`、不涉及 API/DB/权限/安全
3. **如需写版本文档** — 在 `status.md` 标注 `_change_level: hotfix`
4. **确认最小验证** — 审阅最小可复现测试结果

### AI 帮你做的（你不需要做）

- 最小范围修复 + 最小验证
- 使用 `fix:` 或 `fix(<scope>):` 提交前缀
- 触发 hotfix 边界门禁（文件数 / REQ-C）
- 超边界即暂停并建议升级 minor/major

---

## 阶段 0：变更管理（Major/Minor；存量项目或已完成阶段后新增需求触发）

> hotfix 不走该阶段；minor/major 在已完成阶段后新增需求时必须走 CR。

### 你需要做的

1. **提出新意图** — 告诉 AI 你想改什么、加什么
2. **确认基线版本** — AI 会从 `status.md` 读取基线并填入 CR，你确认即可
3. **审查 CR** — 指定审查者（`@review Claude` 或 `@review Codex`），阅读审查报告
4. **确认进入下一阶段** — 审查通过后，明确告诉 AI "确认进入下一阶段"

### AI 帮你做的（你不需要做）

- 创建 CR 文件（`docs/<版本号>/cr/CR-YYYYMMDD-NNN.md`）
- 自动从 `status.md` 读取基线并填入 CR
- 验证基线版本是否存在（git tag/commit 校验）
- 在 `status.md` 登记 Active CR 列表
- CR 合并/拆分/修订/暂停的具体文件操作

---

## 阶段 1：起草提案

### 你需要做的

1. **描述你的想法** — 可以很模糊，AI 会引导你深入思考
2. **回答 AI 的引导问题** — AI 会问你：核心价值是什么？目标用户是谁？成功标准是什么？
3. **审阅提案文档** — AI 写完 `proposal.md` 后，你需要阅读确认
4. **指定审查** — `@review Claude` 或 `@review Codex`，阅读 `review_proposal.md`
5. **确认进入需求阶段** — 说 "确认进入 Requirements 阶段"

### AI 帮你做的（你不需要做）

- 创建版本目录 `docs/<版本号>/`
- 按模板生成 `proposal.md`
- 将你的模糊想法结构化为清晰的产品提案（目标、范围、风险、替代方案等）
- 执行审查并输出审查报告
- 更新 `status.md`

---

## 阶段 2：需求编写

### 你需要做的

1. **逐条确认需求** — AI 会将提案转化为可验收的需求条目（REQ-001, REQ-002...），你需要逐条确认
2. **检查场景覆盖** — 确认正常/异常/边界场景是否完整
3. **覆盖性核对** — 对照 `proposal.md` 的"包含"章节，确认每项都有对应需求
4. **指定审查** — `@review Claude` 或 `@review Codex`
5. **确认进入设计阶段** — 说 "确认进入 Design 阶段"

### AI 帮你做的（你不需要做）

- 按模板生成 `requirements.md`
- 将提案转化为 SMART 需求（具体、可衡量、可验收）
- 编写所有场景（正常/异常/边界）
- 执行审查并输出审查报告
- 一致性检查（关键词交叉验证）

---

## 阶段 3：技术方案设计 — 填写决策清单后 AI 全自动

### 你需要做的

**Design 阶段开始时，AI 会一次性向你提问"决策与配置清单"，你回答完后全程自动。**

1. **填写技术决策** — AI 扫描需求后列出需要你拍板的技术问题（语言/框架/数据库/部署形态等），每项可以：
   - 填具体值（如"PostgreSQL 15"）
   - 标注"AI 自行决定"
   - 标注"给我两个方案对比"
2. **填写环境配置** — 包括服务器信息、数据库连接、密钥等所有部署相关参数
   - 能填的全部填完（包括密码、密钥等敏感信息）
   - 敏感信息 AI 会写入 `.env`（不进 git），不会出现在文档中
   - 实在不确定的可以留空，部署阶段 AI 会提醒你补填
3. **存量项目增量迭代** — 如果技术栈和环境都没变，AI 会自动跳过已确定的项，你可能什么都不用填

> 填完后，Design → Planning → Implementation → Testing 全程无需你介入。

### 可选介入场景

- AI 连续 3 轮自我审查未收敛时，会暂停并请你选择：
  1. 将部分 P1 问题标记为 accept/defer（仅 Design/Planning；Implementation/Testing 禁止）
  2. 给出反馈让 AI 继续修复
  3. 跳过当前阶段

### AI 帮你做的（你不需要做）

- 扫描 `requirements.md`，自动识别需要决策的技术问题
- 生成决策与配置清单供你填写
- 将你的决策写入 `design.md` 的"决策记录"章节
- 敏感配置写入 `.env`，生成 `.env.example`
- 基于你的决策完成完整技术设计
- 自我审查 + 收敛判定
- 自动更新 `status.md` 并进入 Planning 阶段

---

## 阶段 4：任务计划 — AI 全自动

### 你需要做的

**正常情况下：什么都不用做。**
如为 Major 交付，需按 `review_testing.md` 摘要块中的 `SPOT_CHECK_GWTS` 完成人工抽检并填写 `spotcheck_*.md`。

### AI 帮你做的（你不需要做）

- 读取 `design.md` + `requirements.md`，生成 `plan.md`
- 任务拆分（T001, T002...），标注依赖关系
- 分配 Owner/Reviewer（多 Agent 场景）
- 验证所有 REQ-ID 引用存在
- 自我审查 + 收敛判定
- 自动进入 Implementation 阶段

---

## 阶段 5：实现（编码）— AI 全自动

### 你需要做的

**正常情况下：什么都不用做。**
如为 Major 交付，需按 `review_testing.md` 摘要块中的 `SPOT_CHECK_GWTS` 完成人工抽检并填写 `spotcheck_*.md`。

### 可选介入场景

- AI 发现需求理解偏差 → 会暂停问你确认
- AI 发现需要"禁止的变更"（改验收标准/改功能范围/改 API 契约）→ 会暂停走 CR 流程
- 连续 3 轮未收敛 → 暂停请你介入

### AI 帮你做的（你不需要做）

- 按 `plan.md` 逐任务编码
- 遵循项目代码风格、安全规范
- 先读后写（理解现有代码再修改）
- 代码追溯（commit 消息包含 CR-ID）
- 基线合法性验证
- 自我审查 + 收敛判定
- 自动进入 Testing 阶段

---

## 阶段 6：测试 — AI 全自动

### 你需要做的

**正常情况下：什么都不用做。**

### 可选介入场景

- 发现需求理解偏差 → AI 会暂停请你确认
- 重大方向性错误 → AI 会建议回退阶段，需你确认
- 连续 3 轮未收敛 → 暂停请你介入

### AI 帮你做的（你不需要做）

- 编写并执行测试（正常/异常/边界场景全覆盖）
- 需求追溯（每条 REQ 都有对应测试）
- 全量回归测试（pytest / npm test / go test 等）
- 在推进 Implementation→Testing / Testing→Deployment 的提交中触发结果门禁（test/build/typecheck），命令由 `aicoding.config.yaml` 配置
- 回归范围自动推导（基于 CR 影响面 + 代码 diff）
- 发现 bug 直接修复
- 生成 `test_report.md`
- 为 Major 生成抽检清单并提供 `spotcheck_*.md` 模板
- 自我审查 + 收敛判定
- 自动进入 Deployment 阶段

---

## 阶段 7：部署 — AI 执行，你最终确认

### 你需要做的

1. **补填留空配置（如有）** — 如果 Design 阶段有留空的配置项，AI 会列出清单请你补填
2. **阅读部署文档** — AI 生成 `deployment.md` 后，你需要阅读
3. **确认部署** — AI 会输出 "请人工确认后部署"，你说 "确认" 后才会执行
4. **特别注意** — 涉及以下情况时 AI 会额外提醒你：
   - API 契约变更
   - 数据迁移
   - 权限/安全变更
   - 不可逆配置

### AI 帮你做的（你不需要做）

- **从 `design.md` + `.env` 自动提取配置**，生成 `deployment.md`（无需重复填写）
- 生成部署步骤、回滚方案、验证测试
- **主文档同步验证（零容忍门禁）**：
  - 检查所有受影响的主文档是否已更新（系统功能说明书、技术方案设计、接口文档、用户手册、部署记录）
  - 验证变更记录中包含 CR-ID
- **代码模式检测**：自动扫描是否有 API/数据迁移/权限/配置变更但 CR 未声明
- CR 闭环（状态更新为 Implemented，清理 Active CR 列表）
- 更新所有主文档
- 更新 `status.md`（`_change_status: done`，填写完成日期，并同步表格展示行"变更状态"）

---

## 快速参考：你的操作清单

```
阶段 0 变更管理  →  提出意图 → 确认基线 → @review → 确认进入下一阶段
阶段 1 提案      →  描述想法 → 回答引导问题 → 审阅提案 → @review → 确认进入需求
阶段 2 需求      →  逐条确认需求 → 检查覆盖 → @review → 确认进入设计
阶段 3 设计      →  填写决策与配置清单 → AI 全自动完成设计
阶段 4 计划      →  (无需操作，AI 全自动)
阶段 5 实现      →  (无需操作，AI 全自动)
阶段 6 测试      →  (无需操作，AI 全自动)
阶段 7 部署      →  补填留空配置(如有) → 阅读部署文档 → 确认部署

Minor 简化流程 →  需求确认 → 合并设计/计划/实现 → 测试 → 部署确认
Hotfix 极速流程 →  修复 → 最小验证 → 提交
```

---

## 异常情况处理

| 异常 | 触发条件 | 你需要做什么 |
|------|---------|-------------|
| **3 轮不收敛** | AI 自动期（阶段 3-6）连续 3 轮自我审查仍有 P0/P1 问题 | 选择：(1) 标记部分 P1 为 accept/defer（仅 Design/Planning；Implementation/Testing 禁止）(2) 给反馈 (3) 跳过阶段 |
| **紧急中断** | P0 无法修复 / 安全风险 | AI 自动暂停，你确认后恢复（在 `status.md` 设置运行状态=running，或直接说"继续"） |
| **需求偏差** | 实现/测试中发现需求理解有误 | AI 暂停，你确认正确理解后继续 |
| **分级升级** | Minor/Hotfix 复杂度超预期或触碰禁止项 | AI 暂停并建议升级为 Major，你确认后执行 |
| **新需求插入** | 任何阶段完成后想加新东西 | 走变更管理（阶段 0），创建 CR |

---

## 关键文件速查

| 文件 | 作用 | 谁维护 |
|------|------|--------|
| `docs/<版本号>/status.md` | 单一真相源：当前阶段、基线、Active CR | AI 自动更新 |
| `docs/<版本号>/proposal.md` | 产品提案 | AI 写，你确认 |
| `docs/<版本号>/requirements.md` | 需求规格 | AI 写，你确认 |
| `docs/<版本号>/design.md` | 技术设计 | AI 全自动 |
| `docs/<版本号>/plan.md` | 任务计划 | AI 全自动 |
| `docs/<版本号>/review_<stage>.md` | 阶段审查报告（major） | AI 自审 / 审查者 |
| `docs/<版本号>/test_report.md` | 测试报告 | AI 全自动 |
| `docs/<版本号>/review_minor.md` | Minor 审查报告 | AI 自动生成 |
| `docs/<版本号>/spotcheck_*.md` | 人工抽检记录（major） | 人工 |
| `docs/<版本号>/deployment.md` | 部署文档 | AI 写，你确认 |
| `docs/系统功能说明书.md` | 系统功能主文档 | AI 在部署时同步更新 |
| `docs/技术方案设计.md` | 技术设计主文档 | AI 在部署时同步更新 |
| `docs/接口文档.md` | API 文档 | AI 在部署时同步更新 |
| `docs/用户手册.md` | 用户手册 | AI 在部署时同步更新 |
| `docs/部署记录.md` | 部署日志 | AI 在部署时追加 |

---

## 一句话总结

**Major：前两个阶段（提案+需求）深度参与决策，中间四个阶段（设计→测试）AI 全自动完成，最后部署阶段你做最终确认。** Minor/Hotfix 按简化/极速流程推进，但仍需给出可复现的验证证据。整个过程中，AI 负责文档生成、审查、门禁验证和状态管理，你只需要在关键节点做决策和确认。

---

## 故障排除与应急（更新）

### 1. 门禁误报排查步骤（先排查再绕过）
1. 复现：在本地直接运行对应 hook（例如 `bash scripts/git-hooks/pre-commit`）。
2. 定位：根据报错中的 gate 名称，打开对应脚本和规则（`scripts/git-hooks/*`、`scripts/cc-hooks/*`）。
3. 最小化：仅保留触发文件重试，确认是否为规则误报或输入不完整。
4. 处置：
   - 规则正确：按提示补齐文档/证据/字段。
   - 规则误报：记录复现条件并提修复任务，必要时走一次应急提交流程。

### 2. 临时禁用特定 CC hook（仅限故障窗口）
1. 修改 `.claude/settings.json` 中对应 hook 条目，临时注释目标脚本。
2. 完成修复后立即恢复配置并回归验证。
3. 禁止长期关闭 CC hooks 作为“常态流程”。

### 3. Hotfix 标准流程（紧急修复）
1. 在 `aicoding.config.yaml` 确认：
   - `enable_hotfix: true`
   - `hotfix_max_diff_files` 阈值合理（默认 3）
2. 若涉及 `docs/vX.Y/`，在 `status.md` 标注 `_change_level: hotfix`（不推进阶段）。
3. 执行最小改动 + 最小验证（关键测试命令可复现）。
4. 提交使用 `fix:` 或 `fix(<scope>):` 前缀。
5. 边界：
   - 不允许触碰 `REQ-C`；
   - 不允许 API/DB schema/权限安全变更；
   - 超边界必须升级为 minor/major。

### 4. 状态恢复指引（status.md）
1. `_phase` 恢复：
   - 只允许按实际进度回退到最近可信阶段；
   - 大跨度降级需人工确认。
2. `_run_status` 恢复：
   - `paused`/`wait_confirm` → 继续执行前必须人工确认。
3. `_change_status` 恢复：
   - 未交付完成时保持 `in_progress`，禁止提前标记 `done`。
4. 恢复后执行一次 `bash scripts/git-hooks/pre-commit` 做完整自检。

### 5. 逃生通道使用规范（必须留痕）
1. AI 不得自行使用 `--no-verify`，必须先取得用户明确授权。
2. 若因紧急故障使用了逃生通道，commit message 必须包含 `[escape:<原因>]`。
3. post-commit 会执行逃生审计（W24）；出现告警后必须补充审计说明并尽快修复门禁规则。
4. 连续出现逃生告警时，优先修规则，不要把“绕过”当流程。

### 6. 入口门禁与结果门禁配置（M2）
1. 入口门禁默认 `warn`，需要硬拦截可在 `aicoding.config.yaml` 设置 `entry_gate_mode: block`。
2. 结果门禁仅在阶段推进提交（Implementation→Testing / Testing→Deployment）执行。
3. 执行命令来自 `result_gate_test/build/typecheck`；为空会跳过并给 warning。
