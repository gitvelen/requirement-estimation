# AI Coding Tool 十条最佳实践

> 适用于小白到进阶的完整学习指南

---

## 目录

1. [并行 - 一个任务一个 worktree](#1-并行---一个任务一个-worktree)
2. [Plan Mode - 越复杂越要先做设计评审](#2-plan-mode---越复杂越要先做设计评审)
3. [AGENTS.md - 把纠错写成规则](#3-claudemd---把纠错写成规则)
4. [Skills - 每天重复超过一次，就做成技能](#4-skills---每天重复超过一次就做成技能)
5. [修 bug - 少微操，多给证据](#5-修-bug---少微操多给证据)
6. [Prompt 进阶 - 让它当 reviewer，而不是当打字员](#6-prompt-进阶---让它当-reviewer-而不是当打字员)
7. [终端与环境 - 把上下文成本钉在你眼前](#7-终端与环境---把上下文成本钉在你眼前)
8. [子代理与 hooks - 分工 + 守门](#8-子代理与-hooks---分工--守门)
9. [数据分析 - 让 Claude 直接跑 CLI 拉指标](#9-数据分析---让-claude-直接跑-cli-拉指标)
10. [学习 - 让 Claude 讲清楚"为什么"](#10-学习---让-claude-讲清楚为什么)

---

## 1. 并行 - 一个任务一个 worktree

### 核心思想

**把并行能力交给 Git，把上下文隔离交给 worktree。**

### 什么是 Worktree？

Worktree 让同一个 Git 仓库同时在多个目录里检出不同分支：

```
aiquant/              ← 主仓库，你在 master 分支
├── .git/
└── ...

aiquant-feature-a/    ← worktree，你在 feature-a 分支
├── .git/             （链接到主仓库的 .git）
└── ...

aiquant-bugfix/       ← worktree，你在 bugfix 分支
├── .git/             （链接到主仓库的 .git）
└── ...
```

### 为什么用它？

**没有 worktree 的痛点**：

```bash
# 你正在开发 feature-a，写到一半
$ git branch
* feature-a

# 突然线上有个紧急 bug 要修，你得：
git stash      # 暂存当前工作
git checkout bugfix  # 切分支
修 bug...
git commit
git checkout feature-a  # 切回来
git stash pop  # 恢复工作
```

**有了 worktree 后**：

```bash
# 开 feature-a 的终端
cd ~/aiquant-feature-a
# 正常写代码，不用管别的

# 修 bug 的终端
cd ~/aiquant-bugfix
# 直接修，互不影响
```

### 常用命令

```bash
# 创建 worktree + 新分支
git worktree add ../project-feature-a -b feature-a

# 基于已有分支创建 worktree
git worktree add ../project-bugfix bugfix-123

# 查看所有 worktree
git worktree list

# 删除 worktree
git worktree remove ../project-feature-a
```

### Shell 别名（推荐）

```bash
# ~/.zshrc 或 ~/.bashrc
alias za='cd ~/aiquant-feature-a'
alias zb='cd ~/aiquant-bugfix'
alias zc='cd ~/aiquant-hotfix'
alias zm='cd ~/aiquant'
```

### Worktree 合并到主版本

```
                    推送远程分支
┌─────────────┐                    ┌──────────────┐
│  worktree   │ ──────────────────► │   远程仓库   │
│ feature-a/  │   git push origin  │  origin/a    │
└─────────────┘                    └──────────────┘
                                              │
                                              ▼
                                     ┌──────────────┐
                                     │   开 PR/合并  │
                                     │   a → master │
                                     └──────────────┘
```

### 什么时候用？

| 场景 | 是否需要 |
|------|---------|
| 同时开发 + 修 bug | ✅ 推荐 |
| 同时开多个 feature | ✅ 推荐 |
| 对比两个分支 | ✅ 推荐 |
| 一次只专注一件事 | ❌ 不需要 |

---

## 2. Plan Mode - 越复杂越要先做设计评审

### 核心思想

**Plan Mode 是用来减少返工的，安全只是副产品。**

> 先规划，再执行；先评审，再动手。

### 为什么用 Plan Mode？

```
没有 Plan Mode：
你：Claude 帮我加个用户认证
Claude：好，开始写代码...
（半小时后）
你：等等，这不是我想要的...
Claude：那我重写...
（又半小时）
你：还是不对...

有 Plan Mode：
你：Claude 帮我加个用户认证
Claude：好，我先分析现状，然后给你一个计划
（10 分钟后）
Claude：这是我的计划...
你：第 3 步不对，应该这样做...
Claude：明白，我修改计划
你：没问题，开始执行
```

### 如何开启？

```bash
# 命令行
ai --permission-mode plan
```

### 推荐的结构化 Prompt

```
先只读分析现状，不要改文件。

请按这个结构给计划：
1) 现状摘要（含关键文件列表）
2) 目标与非目标（这次要做什么，不做什么）
3) 实施步骤（按 PR 切分）
4) 风险清单（每条对应规避方式）
5) 验证清单（命令级别）
6) 回滚方案
```

### 一个例子

假设你让 Claude：「给登录功能加短信验证码」

**Plan Mode 会输出**：

```
1) 现状摘要
   - 当前登录: src/login.js，只支持密码登录
   - 相关文件: src/auth.js, api/auth.js
   - 依赖: 需要短信服务

2) 目标与非目标
   ✅ 目标: 添加发送验证码接口、验证码校验、更新 UI
   ❌ 非目标: 不修改现有密码登录、不做限流

3) 实施步骤
   Step 1: 新建 src/sms.js（短信服务封装）
   Step 2: 更新 api/auth.js（添加接口）
   Step 3: 修改 src/login.js（添加表单）

4) 风险清单
   - 风险: 短信服务调用失败 → 规避: 添加重试机制
   - 风险: 验证码被滥用 → 规避: 60秒发送间隔

5) 验证清单
   - [ ] npm run test 通过
   - [ ] 本地发送验证码成功
   - [ ] 错误验证码被拒绝

6) 回滚方案
   git revert <commit-hash> 或配置关闭开关
```

### 什么时候用？

| 复杂度 | 需要 Plan Mode 吗？ |
|--------|-------------------|
| 改一个变量名 | ❌ |
| 修复明确的小 bug | ❌ |
| 新增功能（≥2个文件） | ✅ 推荐 |
| 重构模块 | ✅ 推荐 |
| 架构级改动 | ✅ 必须 |

### 关键点

**把验证步骤也写进计划**。很多失败不是代码写错，是验证没跟上。

---

## 3. AGENTS.md - 把纠错写成规则

### 核心思想

**把"口头经验"变成可复用的系统约束。**

> 每次 Claude 犯错，你纠正完就补一句：「更新 AGENTS.md，确保以后不再犯同样的错误。」

### 什么是 AGENTS.md？

```
aiquant/
├── AGENTS.md          ← 给 AI 看的项目说明书
├── README.md          ← 给人看的项目说明
├── src/
└── ...
```

| | README.md | AGENTS.md |
|---|---|---|
| 写给谁看 | 人 | Claude（AI） |
| 写什么 | 项目介绍、安装 | 代码规范、禁止事项 |
| 语气 | 描述性 | 命令式 |

### 一个 AGENTS.md 示例

```markdown
# AGENTS.md

## 项目概述
AI量化交易平台 - A股量化交易系统

## 代码规范

1. **密钥管理**
   - 所有 API_KEY、SECRET 必须使用环境变量
   - 禁止直接写在代码里
   - 禁止提交到 Git 仓库

2. **数据库操作**
   - 所有查询必须使用参数化查询
   - 敏感操作必须加 try-except

## 禁止事项
- ❌ 不得硬编码任何密钥
- ❌ 不得跳过测试直接提交

## A股交易规则约束
- T+1 制度：当日买入只能次日卖出
- 交易单位：100 股整数倍
- 涨跌停：±10%（ST ±5%，科创/创业 ±20%）
- 所有交易操作必须有人工确认
```

### 实际用法

**场景：Claude 犯错了**

```javascript
// Claude 写的代码（错误）
const apiKey = "sk-1234567890abcdef";
```

```
你: 错了！API_KEY 不能写死

Claude: 抱歉，修改为：
const apiKey = process.env.API_KEY;

你: 好，现在更新 AGENTS.md

Claude: 已更新：
## 密钥管理
- 所有密钥必须用 process.env 读取
- 启动时必须检查环境变量
```

### 标准纠错流程

```
Claude 写错了 → 你指出错误 → Claude 修复
                                    ↓
                          你说："更新 AGENTS.md"
                                    ↓
                          Claude 更新文档
                                    ↓
                          下次不会再犯
```

### 进阶：基线 + CR（差异审查）

把“测试通过的那一版”冻结成**基线**（tag/commit），后续新增想法用 **CR（变更单）** 记录，默认执行 **diff-only** 复查，避免每次都全量重读/重跑所有阶段。

- `status.md`：记录基线版本（对比口径）/复查口径（diff-only/full）/Active CR 列表
- `CR-*.md`：记录变更意图、影响面、验收与回滚（建议放在 `docs/<版本号>/cr/`）
- PR 合并：推荐 squash merge；提交/PR 标题包含 CR-ID 便于追溯

### 进阶：AGENTS.md + notes 分离

```
aiquant/
├── AGENTS.md          ← 规则（简洁）
└── notes/             ← 证据与上下文（详细）
    ├── database.md    ← 数据库设计决策
    └── auth.md        ← 认证方案讨论
```

---

## 4. Skills - 每天重复超过一次，就做成技能

### 核心思想

**重复劳动超过两次就值得自动化。**

> 把重复性操作封装成 Skill，一键调用。

### 什么是 Skill？

Skill 就是**给 Claude 定义的自定义命令**：

```
普通对话：
你: Claude，帮我检查代码里有没有重复代码
Claude: 好的，让我扫描...

用 Skill：
你: /techdebt
Claude: 自动执行技术债务检查脚本
```

### Skills 目录结构

```
~/.aicoding/skills/
├── code/                    # 代码质量
│   └── techdebt            # 技术债务扫描
├── workflow/                # 工作流程
│   ├── sync-context        # 上下文同步
│   └── review-pr           # PR 代码审查
├── project/                 # 项目特定
│   └── check-aquote        # A股规则检查
└── quant/                   # 量化交易
    ├── stock-data          # 数据查询
    ├── strategy-backtest   # 策略回测
    ├── portfolio-analysis  # 组合分析
    └── risk-metrics        # 风险指标
```

### 创建 Skill 的步骤

```bash
# 1. 创建目录
mkdir -p ~/.aicoding/skills/code

# 2. 创建 Skill 文件
vim ~/.aicoding/skills/code/techdebt
```

```python
# description: 扫描代码中的技术债务
# usage: /techdebt

请按以下步骤扫描：
1. 查找重复代码
2. 查找 TODO/FIXME/HACK
3. 查找过时代码
4. 识别高复杂度函数

输出格式：按优先级排序的报告
```

### 使用方式

```bash
# 方式一：直接调用
/techdebt

# 方式二：自然语言
"请检查技术债务"
```

### 什么时候做 Skill？

| 频率 | 建议 |
|------|------|
| 一次 | ❌ 不需要 |
| 偶尔 | ❌ 不需要 |
| 每天 | ✅ 做 Skill |

### 你可以做的第一个 Skill

```python
# ~/.aicoding/skills/check-style

# description: 检查代码规范
# usage: /check-style

检查：
1. 是否有硬编码密钥
2. 是否有未清理的 console.log
3. 是否有未处理的 TODO
4. 函数命名是否符合规范
```

---

## 5. 修 bug - 少微操，多给证据

### 核心思想

**把上下文切换成本干掉，把微操干掉。**

> 你要的是"让它把问题跑通"，不是"你替它写 plan"。

### 三种典型用法

#### 方式一：讨论串直接贴

```
有 Slack/Discussion 讨论串？
直接整个复制给 Claude，只说一个词：

fix

不需要自己总结。
```

#### 方式二：CI 爆了

```
❌ 不要指导它怎么修：
你：CI 挂了，可能是单元测试没通过...

✅ 直接下任务：
你：Go fix the failing CI tests.
```

#### 方式三：线上问题

```
把 Docker logs / 错误日志直接贴：

2024-01-15 10:23:45 ERROR: Connection refused
2024-01-15 10:23:46 WARN: Retry 1/3...

然后说：
"先分析根因，再给排查路径"
```

### 需要给哪些证据？

| 问题类型 | 需要的证据 |
|---------|-----------|
| 代码报错 | 错误堆栈、相关代码 |
| 测试失败 | 测试日志、失败输出 |
| 线上问题 | 应用日志、监控数据 |
| 性能问题 | 性能分析、慢查询 |

### 核心区别

```
❌ 微操模式：
你：第一步检查这个，第二步检查那个...
   → 你在替 AI 思考

✅ 证据模式：
你：（甩证据）+ "搞定它"
   → AI 自己分析
```

---

## 6. Prompt 进阶 - 让它当 reviewer，而不是当打字员

### 核心思想

**把 Claude 拉到"审查与证明"的位置上。**

> 你在要求"可验证的交付"，不是"看起来像对的输出"。

### 三个核心口令

#### 口令 a：严厉拷问

```
对我这些代码变更进行严厉拷问。
在我通过你的测试之前，不要创建 PR。
```

**效果**：Claude 主动找问题、挑战假设、指出风险。

#### 口令 b：证明能跑

```
向我证明这行得通。
请对比 main 分支和当前 feature 分支的行为差异，
列出你验证了什么。
```

**效果**：Claude 给出证据、对比行为、列出验证清单。

#### 口令 c：推翻重做

```
基于你现在掌握的所有信息，
废掉目前的方案，
去实现一个更优雅的解法。
```

**效果**：Claude 重新思考、发现更好的方案。

### 扩充口令（30个）

| 分类 | 口令 |
|------|------|
| 安全 | 假设我是攻击者，我会如何利用这段代码做坏事？ |
| 边界 | 列出所有边界情况：空值、空数组、并发、超时 |
| 性能 | 如果数据量增长 100 倍，哪里会先崩溃？ |
| 可读性 | 假设 6 个月后一个新人来读，会困惑什么？ |
| 测试 | 给我 5 个可能让这段代码失败的测试输入 |

### 组合使用示例

```
你：帮我重构认证模块
Claude：这是重构后的代码...

你：废掉目前的方案，实现一个更优雅的解法
Claude：重新思考后，用策略模式...

你：好，现在向我证明这行得通
Claude：这是验证报告...

你：最后，对我这些代码变更进行严厉拷问
Claude：以下是我发现的问题...
```

### 核心区别

```
❌ 打字员模式：
你：写代码
Claude：好的，写了

✅ 审查者模式：
你：拷问这段代码 / 证明它对 / 重做更好
Claude：（主动思考、分析、验证）
```

---

## 7. 终端与环境 - 把上下文成本钉在你眼前

### 核心思想

**终端体验会直接影响你写 Prompt 的质量。**

> 把关键信息固定在状态栏里。

### 推荐显示的信息

```
┌─────────────────────────────────────────────────┐
│ [feature/login] 📊 67% │ ✗ 2 未提交 │ ~/aiq-login │
└─────────────────────────────────────────────────┘
   ↑                    ↑            ↑
  当前分支           上下文用量    worktree 路径
```

### 推荐工具

| 工具 | 用途 |
|------|------|
| **Windows Terminal** | 终端模拟器（Win 推荐） |
| **tmux** | 终端复用、多窗口 |
| **Oh My Posh** | 美化提示符 |

### Shell 别名

```bash
# ~/.zshrc
alias za='cd ~/aiquant-feature-a'
alias zb='cd ~/aiquant-bugfix'
alias zm='cd ~/aiquant'

function gb { git branch --show-current }
function gs { git status }
```

### PowerShell 提示符（Windows）

```powershell
# $PROFILE
function prompt {
    $branch = git branch --show-current
    Write-Host "[$branch] " -ForegroundColor Yellow
    Write-Host $(Get-Location) -ForegroundColor Cyan
    Write-Host "`n❯" -NoNewline
    return " "
}
```

### Windows 终端工具链

```
推荐组合：
├── Windows Terminal (终端模拟器)
├── PowerShell 7 (Shell)
├── Oh My Posh (美化)
└── Git (版本控制)
```

### 一键安装（Windows）

```powershell
winget install Microsoft.WindowsTerminal
winget install Microsoft.PowerShell
winget install JanDeDobbeleer.OhMyPosh
winget install Git.Git
```

---

## 8. 子代理与 hooks - 分工 + 守门

### 核心思想

```
1. 把独立子任务 offload 给子代理
2. 通过 hooks 把权限请求路由给更强模型
```

### 什么是子代理？

```
┌─────────────────────────────────────────────┐
│              主会话                          │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐    │
│  │子代理 A │  │子代理 B │  │子代理 C │    │
│  │代码审查 │  │调试排查 │  │文档编写 │    │
│  └─────────┘  └─────────┘  └─────────┘    │
└─────────────────────────────────────────────┘
```

### 使用场景 1：需要更多推理

```
在请求末尾加一句：
use subagents
```

### 使用场景 2：独立子任务

```
会话 A：写代码
会话 B：写测试（并行）
会话 C：更新文档（并行）
```

### Hooks 自动守门

```
你执行 git push
  ↓
Hook 拦截
  ↓
交给更强模型审查
  ↓
安全 → 自动批准
不安全 → 拒绝
```

### 注意事项

```
⚠️ 自动化很强，但也更敏感

建议：
1. 先在非生产环境把流程跑顺
2. 先人工审查一批
3. 再考虑自动批准
```

### 多会话协作建议

| 场景 | 推荐方案 |
|------|---------|
| 单人开发 | 主从模式（你协调） |
| 小团队 | 明确分工边界 |
| 复杂项目 | 分工 + 状态文件 |

---

## 9. 数据分析 - 让 Claude 直接跑 CLI 拉指标

### 核心思想

**让 AI Coding Tool 调用数据源的 CLI/MCP/API，即时拉取并分析。**

> 你不需要写 SQL，让 Claude 直接跑分析查询。

### 对比

```
❌ 传统方式：
打开客户端 → 手写 SQL → 导出数据 → Excel 分析

✅ Claude 方式：
描述需求 → Claude 写 SQL → 拉取数据 → 分析 → 生成模板
```

### 支持的数据源

| 数据源 | CLI/MCP |
|--------|---------|
| PostgreSQL | psql |
| MySQL | mysql |
| BigQuery | bq |
| Redis | redis-cli |
| Elasticsearch | curl API |
| 你的 API | MCP/HTTP |

### 实战例子：PostgreSQL

```python
# ~/.aicoding/skills/analyze-db

# description: 数据库分析查询
# usage: /analyze-db <需求>

请使用 psql CLI 执行数据库查询。

步骤：
1. 理解需求
2. 生成 SQL
3. 调用 psql
4. 分析结果
5. 给出结论
```

### 使用示例

```
你：/analyze-db 统计各策略收益率

Claude：
[生成 SQL]
SELECT strategy_name, AVG(return_rate) as avg_return
FROM trades GROUP BY strategy_name;

[执行查询]
[分析结果]
[给出结论]
```

### 三个关键动作

```
1. 拉数据 - 不用自己写查询
2. 解释波动 - 自动分析原因
3. 写模板 - 可复用
```

### 量化交易 Skills

```
~/.aicoding/skills/quant/
├── stock-data          # A股数据查询
├── strategy-backtest   # 策略回测
├── portfolio-analysis  # 组合分析
└── risk-metrics        # 风险指标
```

---

## 10. 学习 - 让 Claude 讲清楚"为什么"

### 核心思想

**学习成本从"读文档"变成"对话式复盘"。**

> 让 Claude 解释每一步的原因。

### 四个学习技巧

#### 技巧 1：解释性输出

```
"帮我写这个功能，解释每一步为什么"

Claude：
1. 抽取常量 → 原因：魔法数字难维护
2. 拆分函数 → 原因：单一职责
3. 添加类型 → 原因：提前发现错误
```

#### 技巧 2：HTML 演示文档

```
"把这个模块生成幻灯片式文档"

Claude 生成：
Slide 1: 模块概述
Slide 2: 核心类
Slide 3: 数据流
...
```

#### 技巧 3：ASCII 架构图

```
"用 ASCII 图画出系统架构"

Claude：
┌─────────┐     ┌─────────┐
│ Client  │────▶│ Gateway │
└─────────┘     └─────────┘
```

#### 技巧 4：间隔复习

```
你：我理解闭包是...
Claude：那闭包的内存泄漏你知道吗？
你：不太清楚
Claude：[解释]

然后保存笔记，下次复习
```

### 学习向 Prompt 模板

```
# 解释式编程
"写代码 + 解释每一步为什么"

# 教学式讲解
"当成我是完全不懂的人来讲解"

# 对比式学习
"对比方案 A 和方案 B 的优缺点"

# 追溯式理解
"这段代码为什么这么写？有什么历史原因？"
```

### 对话式学习示例

```
你：解释 Python 装饰器
Claude：装饰器本质是...

你：能举个具体例子吗？
Claude：比如计时装饰器...

你：为什么要用 *args 和 **kwargs？
Claude：这样能适用任何函数...

你：执行顺序呢？
Claude：好问题！从下往上...
```

---

## 十条总结

| # | 条目 | 核心一句话 |
|---|------|-----------|
| 1 | 并行 worktree | 把并行交给 Git，把隔离交给 worktree |
| 2 | Plan Mode | 先规划再执行，减少返工 |
| 3 | AGENTS.md | 把纠错写成规则 |
| 4 | Skills | 重复超过两次，就自动化 |
| 5 | 修 bug | 少微操，多给证据 |
| 6 | Prompt 进阶 | 让它当审查者 |
| 7 | 终端环境 | 把上下文放眼前 |
| 8 | 子代理 | 分工 + 守门 |
| 9 | 数据分析 | 让 Claude 跑 CLI |
| 10 | 学习 | 让它讲清楚"为什么" |

---

## 共同模型

```
1. 空间换时间：worktree 并行
2. 设计重于编码：Plan Mode 先行
3. 构建数字记忆：AGENTS.md 迭代
4. 工具化与自动化：skills 降低成本
```

**从"让 AI 帮我写代码"，变成"我在调度一个工程系统"。**

---

*文档版本: v1.1 | 基于 AI Coding Tool 官方最佳实践整理*
