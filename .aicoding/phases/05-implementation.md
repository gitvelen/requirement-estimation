# 阶段5：实现 (Implementation)

## 目标
按计划高质量完成代码开发

## 输入
- `docs/<版本号>/plan.md`
- `docs/<版本号>/design.md`
- `docs/<版本号>/requirements.md`

## 输出
- 可运行的代码
- 代码文档（必要时的注释）

## 阶段开始时检查
- [ ] 确认 plan.md 已完成并通过评审
- [ ] 确认当前变更目录存在
- [ ] 确认依赖的前置任务已完成

## 实现原则
```
┌─────────────────────────────────────────────────────────────┐
│  1. 先读后写                                                 │
│     - 修改代码前必须先阅读现有代码                           │
│     - 理解现有模式和约定                                     │
│     - 不随意引入新库                                         │
│                                                              │
│  2. 保持简洁                                                 │
│     - 避免过度抽象                                           │
│     - 优先编辑而非新建文件                                   │
│     - 三行相似代码优于过早抽象                               │
│                                                              │
│  3. 遵循规范                                                 │
│     - 遵循项目代码风格                                       │
│     - 遵循语言最佳实践                                       │
│     - 保持命名清晰                                           │
│                                                              │
│  4. 安全意识                                                 │
│     - 输入验证                                               │
│     - 输出编码                                               │
│     - 敏感信息保护                                           │
│     - 不引入未知依赖                                         │
│                                                              │
│  5. 按计划执行                                               │
│     - 严格按照任务计划执行                                   │
│     - 完成一项标记一项                                       │
│     - 遇到问题及时沟通                                       │
└─────────────────────────────────────────────────────────────┘
```

## 读取模板
实现时读取 `.aicoding/templates/implementation_checklist_template.md`。

## 多 Claude 协作规则（可选）

单 Claude 工作时本节可忽略。

当多个 Claude 并行工作时：
```
┌─────────────────────────────────────────────────────────────┐
│  1. 任务归属确认                                            │
│     - 只能修改 plan.md 中 Owner=当前Claude 的任务            │
│     - 检查 plan.md 确认任务分配后再开始工作                  │
│                                                              │
│  2. 工作区隔离                                              │
│     - 代码改动先在 docs/<版本号>/tasks/                      │
│       TXXX-<任务名>/ 工作目录完成                            │
│     - Review 通过后才能合并到主代码库                        │
│                                                              │
│  3. 文件隔离                                                │
│     - 不修改其他 Claude 负责的文件和目录                     │
│     - 如需要共享代码，提前在 plan.md 中约定接口              │
│                                                              │
│  4. 共享资源协议（🔴 MUST）                                 │
│     - 数据库 schema：由单一 Owner 负责迁移脚本，其他         │
│       Agent 只读不写；如需修改须在 plan.md 中声明依赖        │
│     - 配置文件（如 .env、yaml）：修改前须在 plan.md 对应     │
│       任务中声明"需修改配置项"，避免并发覆盖                 │
│     - 共享模块/公共库：修改前须通知依赖方 Agent，并在        │
│       plan.md 中建立任务依赖关系                             │
│     - API 契约（接口签名/数据格式）：变更须在 plan.md 中     │
│       声明，所有消费方任务标记为 blocked                      │
│                                                              │
│  5. 冲突仲裁机制                                            │
│     - 发现文件冲突时：立即停止，在 status.md 记录冲突        │
│       详情，等待用户仲裁                                     │
│     - 发现接口不一致时：以 design.md 为权威源，偏离方        │
│       须提出 CR 或请求用户确认                               │
│     - 多 Agent 对同一问题有不同理解时：暂停并请求用户        │
│       澄清，不得自行假设                                     │
│                                                              │
│  6. 集成协调                                                │
│     - 各 Agent 完成任务后，在 plan.md 中标记"已完成"         │
│     - 所有任务完成后，由指定 Agent（或用户）执行集成          │
│       测试，验证跨任务交互正确性                             │
│     - 集成测试失败时：定位到责任任务，由对应 Owner 修复      │
│                                                              │
│  7. 状态同步                                                │
│     - 任务状态更新由 Owner 负责                              │
│     - 避免并发写同一文件（如 plan.md）                       │
│     - 状态更新格式：在对应任务行添加「待办/进行中/已完成」     │
└─────────────────────────────────────────────────────────────┘
```

**工作目录结构**：
```
docs/<版本号>/
└── tasks/
    ├── T001-<任务名>/    # 仅该任务 Owner 可写（Owner 见 plan.md）
    ├── T002-<任务名>/    # 仅该任务 Owner 可写（Owner 见 plan.md）
    └── T003-<任务名>/    # 仅该任务 Owner 可写（Owner 见 plan.md）
```

## 质量门禁
- [ ] 按任务计划完成
- [ ] 代码简洁清晰
- [ ] 无安全漏洞
- [ ] 代码审查
- [ ] 自测通过

## 代码追溯要求（🔴 MUST，CR 场景强制）

> **触发条件（🔴 MUST）**：仅当 status.md 的 Active CR 列表**非空**时启用本门禁；如无Active CR，跳过本检查（支持非CR迭代）

### Git 规范
- **分支命名**：`cr/CR-YYYYMMDD-NNN-<short-name>`
- **Commit 消息**：必须包含 CR-ID，格式：`[CR-YYYYMMDD-NNN] 实现用户登录功能`
- **PR 标题**：必须包含 CR-ID
- **CR代码边界**：默认 1 PR 1 CR；如合并实现，必须在 PR/commit 中列出全部 CR-ID

### 快速自检（可选，非门禁）
```bash
# 快速检查：最近10条commit是否包含CR-ID格式
# 注意：这不是门禁，只是开发时的快速自检
git log --oneline -n 10 | rg "CR-[0-9]{8}-[0-9]{3}"
```

### AI 自动检查（门禁）

**检查步骤**：
1. 读取 status.md，获取基线版本和当前代码版本（AI直接解析表格）
2. **baseline 合法性验证（🔴 MUST）**：
   ```bash
   # 验证 baseline 存在
   git rev-parse --verify "${BASELINE}^{commit}" 2>/dev/null || exit 1

   # 验证 current 存在
   git rev-parse --verify "${CURRENT}^{commit}" 2>/dev/null || exit 1

   # 验证 baseline 是 current 的祖先节点（避免范围错误）
   git merge-base --is-ancestor ${BASELINE} ${CURRENT} || exit 1
   ```
3. 检查基线到当前之间的所有 commit：
   ```bash
   # 命令行方式（依赖status.md的_baseline/_current可机读行）
   BASELINE=$(grep "^_baseline:" docs/<版本号>/status.md | awk '{print $2}')
   CURRENT=$(grep "^_current:" docs/<版本号>/status.md | awk '{print $2}')
   git log ${BASELINE}..${CURRENT} --oneline
   ```
4. 验证每个 Active CR-ID 至少出现一次：
   ```bash
   # 示例：检查CR-20260208-001是否存在
   git log ${BASELINE}..${CURRENT} --oneline | rg "CR-20260208-001"
   ```
5. 输出验证报告

> **注意**：PR 标题验证仅在使用 PR 的项目场景有效。本地开发场景只验证 commit 消息。

**失败输出**：
  ```text
  ❌ Implementation门禁失败：代码追溯未通过

  Active CR列表中的以下CR-ID未在commit中找到：
  - CR-20260208-001
  - CR-20260208-003

  请确保commit消息或PR标题包含对应CR-ID格式。

  当前范围的commit：
  <git log输出>
  ```

## 阶段文档回填（🔴 MUST，CR 场景参考）

> **回填规则**：

**允许的回填（无需额外审批）**：
- [ ] 补写遗漏的实现细节（如新增的辅助函数、数据结构）
- [ ] 澄清口径/描述优化（不改变语义，只改表述）
- [ ] 修复明显的文档错误（如笔误、格式问题）
- [ ] 回填内容已标记"实现阶段补充"及日期

**禁止的变更（必须走CR修订+用户确认）**：
- ❌ 改变验收标准（Given-When-Then）
- ❌ 调整功能范围（增加/删除需求）
- ❌ 修改API契约（接口签名、数据格式）
- ❌ 变更非功能性约束（性能目标、安全要求）

**边界处理流程**：
1. 如发现需要"禁止的变更"，暂停实现
2. 创建CR修订或回退到Requirements/Change-Management阶段
3. 用户确认后继续实施

## 完成条件（🔴 MUST，AI 自动判定）

### 0. 文档阅读优先（🔴 MUST，R7/R9）
```text
┌─────────────────────────────────────────────────────────────┐
│  R7: 禁止凭搜索质疑用户                                      │
│     - 用户说"文档有写"时，必须先 Read 相关章节               │
│     - 列出原文和行号，再讨论差异                             │
│                                                              │
│  R9: 差异确认流程                                            │
│     - 发现 proposal 与 requirements 不一致时                 │
│     - 列出两处原文请用户确认，不得自行假设优先级             │
└─────────────────────────────────────────────────────────────┘
```

### 6. 任务追踪强制（多任务时 🔴 MUST，R8）
- 使用任务追踪工具（如 TodoWrite）建立任务列表
- 创建 → 执行 → 完成标记，全程追踪

### AI 自动审查收敛
- [ ] 执行自我审查（按 `.aicoding/templates/review_template.md` Implementation 清单）
- [ ] P0(open)=0, P1(open)=0（允许存在 P1 accept/defer）
- [ ] 单轮满足即收敛

### diff-only检查（🔴 MUST，有Active CR时）
- [ ] 如存在Active CR，执行diff-only审查增强（见 `.aicoding/templates/review_template.md` 附录 AC-05）
- [ ] 验证CR影响面与实际代码变更一致
- [ ] 如发现P1差异，必须修复后才能收敛（🔴 MUST）

> **执行入口（🔴 MUST）**：diff-only 检查步骤详见 `.aicoding/templates/review_template.md` 附录 AC-05，包含完整的 AI 执行命令、差异报告格式和级联影响分析。

### 收敛后自动推进
```text
✅ Implementation AI 自动审查已收敛
▶️ 自动进入下一阶段：Testing
```

### AI 自动执行
- [ ] 更新 `status.md`：当前阶段 = Testing
- [ ] 开始 Testing 工作

## 完成后
1. AI 自动推进到 Testing 阶段
2. 用户可在 `status.md` 查看当前进度
