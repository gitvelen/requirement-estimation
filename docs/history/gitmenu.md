# Git 版本管理实用手册

> 手把手教你使用 Git 进行版本控制，适合初学者快速上手

---

## 目录

1. [为什么要用 Git](#为什么要用-git)
2. [基础概念](#基础概念)
3. [常见场景与操作](#常见场景与操作)
4. [Cursor 中的 Git 操作](#cursor-中的-git-操作)
5. [实用技巧](#实用技巧)
6. [问题排查](#问题排查)

---

## 为什么要用 Git

### 需要使用 Git 的场景

✅ **适合使用 Git 的情况**：
- 编写代码（任何编程项目）
- 编写文档（需要追踪修改历史）
- 团队协作（多人同时开发）
- 需要回滚到历史版本
- 需要对比修改内容
- 需要在多台电脑同步工作

❌ **不需要 Git 的情况**：
- 临时测试脚本（用完即删）
- 敏感配置文件（包含密码、密钥）
- 大型二进制文件（视频、音频等）
- 编译生成的文件（.pyc, node_modules 等）

### Git 的核心价值

| 功能 | 价值 |
|------|------|
| **版本快照** | 随时回到任何历史版本 |
| **修改对比** | 清楚看到改了什么 |
| **分支管理** | 并行开发不影响主线 |
| **远程备份** | 代码安全存储在云端 |
| **团队协作** | 多人协同开发不冲突 |

---

## 基础概念

### Git 的三个区域

```
工作区 ──add──> 暂存区 ──commit──> 本地仓库 ──push──> 远程仓库
  ↑                                                      ↓
  └──────────────── checkout/pull ───────────────────────┘
```

| 区域 | 说明 | 命令 |
|------|------|------|
| **工作区** | 你实际编辑文件的地方 | `git status` 查看 |
| **暂存区** | 准备提交的文件列表 | `git add` 添加 |
| **本地仓库** | 本地的版本历史 | `git commit` 提交 |
| **远程仓库** | GitHub/GitLab 等云端 | `git push` 推送 |

### Git 的四种文件状态

```
未跟踪 ──add──> 已暂存 ──commit──> 已修改
   ↑                           ↓
   └──────────── checkout ──────┘
```

| 状态 | 说明 | 如何处理 |
|------|------|----------|
| **未跟踪** | 新文件，Git 还没管理 | `git add` 添加 |
| **已暂存** | 已添加，准备提交 | `git commit` 提交 |
| **已修改** | 文件有变化 | `git add` 然后 `git commit` |
| **未修改** | 文件和仓库一致 | 无需操作 |

---

## 常见场景与操作

### 场景一：新项目初始化

**适用情况**：刚开始一个新项目，需要用 Git 管理版本

```bash
# 1. 进入项目目录
cd /path/to/your/project

# 2. 初始化 Git 仓库
git init
# 意义：创建 .git 隐藏目录，Git 开始跟踪这个项目

# 3. 创建 .gitignore 文件（指定不需要管理的文件）
cat > .gitignore << EOF
# Python
__pycache__/
*.pyc
*.pyo
.venv/
venv/

# Node
node_modules/
npm-debug.log

# IDE
.vscode/
.idea/
*.swp

# 敏感信息
.env
*.key
*.pem

# 日志
logs/
*.log

# 其他
.DS_Store
uploads/
data/
EOF
# 意义：避免提交敏感文件和无用文件

# 4. 查看文件状态
git status
# 意义：了解哪些文件被修改、哪些未跟踪

# 5. 添加所有文件到暂存区
git add .
# 意义：把所有改动加入待提交列表
# 注意：.gitignore 中列出的文件不会被添加

# 6. 提交到本地仓库
git commit -m "初始提交"
# 意义：创建第一个版本快照
# 注意：提交信息要清晰描述做了什么

# 7. 关联远程仓库（可选）
git remote add origin https://github.com/yourname/repo.git
# 意义：连接到 GitHub/GitLab 仓库

# 8. 推送到远程仓库
git push -u origin master
# 意义：上传代码到云端
# 注意：-u 参数设置默认上游分支，下次只需 git push
```

### 场景二：日常开发提交

**适用情况**：日常写代码，需要保存进度

```bash
# 1. 查看当前状态
git status
# 意义：了解哪些文件被修改了
# 输出示例：
#   modified:   app.py          # 已修改
#   new file:   utils.py        # 新文件
#   untracked: test.tmp         # 未跟踪

# 2. 查看具体修改内容
git diff
# 意义：查看文件的具体改动
# 注意：只显示已跟踪文件的修改

# 3. 添加修改的文件（方式一：添加单个文件）
git add app.py
# 意义：只提交 app.py 的修改

# 4. 添加修改的文件（方式二：添加所有修改）
git add .
# 或
git add -A
# 意义：添加所有修改、删除、新增的文件
# 注意：这会添加所有改动，包括不想提交的，请谨慎使用

# 5. 查看暂存区的文件
git status
# 意义：确认哪些文件将被提交
# 注意：绿色的文件是已暂存的，红色的未暂存

# 6. 提交到本地仓库
git commit -m "修复：用户登录接口参数验证错误"
# 意义：创建版本快照
# 注意：提交信息格式建议：
#   - 新功能：feat: 添加用户注册功能
#   - 修复：fix: 修复登录超时问题
#   - 文档：docs: 更新 README
#   - 重构：refactor: 优化代码结构

# 7. 查看提交历史
git log --oneline -10
# 意义：查看最近的提交记录
# 输出示例：
#   a1b2c3d 修复：用户登录接口参数验证错误
#   d4e5f6g feat: 添加用户注册功能
```

### 场景三：修改后想撤销

**适用情况**：修改错了，想回退

```bash
# 情况1：修改了文件，但还没 add（想撤销修改）
git checkout -- app.py
# 或
git restore app.py
# 意义：丢弃工作区的修改，回到最近一次 commit 的状态
# 警告：这个操作不可逆，修改会永久丢失！

# 情况2：已经 add，但还没 commit（想撤销暂存）
git reset HEAD app.py
# 或
git restore --staged app.py
# 意义：从暂存区移除，但保留修改
# 注意：文件修改还在，只是不提交了

# 情况3：已经 commit，但想撤销这次提交
git reset --soft HEAD~1
# 意义：撤销最近一次提交，但保留修改在暂存区
# 适用场景：发现提交信息写错了，或者想补充文件

git reset --hard HEAD~1
# 意义：撤销最近一次提交，并丢弃所有修改
# 警告：这个操作不可逆，所有改动会丢失！

# 情况4：想回到某个历史版本
git log --oneline  # 查看提交历史，找到目标版本的 hash
git reset --hard a1b2c3d  # 回到指定版本
# 意义：完全回到某个历史版本
# 注意：之后的提交会"消失"（但还在，可以通过 git reflog 找回）
```

### 场景四：查看历史和对比

**适用情况**：想看修改历史、对比不同版本

```bash
# 1. 查看提交历史
git log
# 意义：查看所有提交记录（详细信息）
# 输出包含：提交 hash、作者、时间、提交信息

# 2. 查看精简历史
git log --oneline -10
# 意义：只看最近 10 次提交（一行一条）
# 输出格式：提交 hash(前7位)  提交信息

# 3. 查看图形化历史
git log --graph --oneline --all
# 意义：查看分支合并情况
# 适用场景：有多分支开发时

# 4. 查看某次提交的详细信息
git show a1b2c3d
# 意义：查看某次提交的具体改动
# 输出：提交信息 + 修改的文件 + 具体改动

# 5. 对比两个版本
git diff a1b2c3d d4e5f6g
# 意义：对比两个版本的差异
# 适用场景：想看某个功能改动了什么

# 6. 对比当前和暂存区
git diff
# 意义：查看工作区还没暂存的修改

# 7. 对比暂存区和最后一次提交
git diff --cached
# 或
git diff --staged
# 意义：查看即将提交的内容
```

### 场景五：分支管理

**适用情况**：需要开发新功能，不影响主线代码

```bash
# 1. 查看所有分支
git branch
# 意义：列出本地所有分支
# 输出示例：
#   * master        # * 表示当前分支
#     feature-login

# 2. 创建新分支
git branch feature-register
# 意义：创建新分支但保持当前分支
# 适用场景：准备开始新功能开发

# 3. 切换到新分支
git checkout feature-register
# 或
git switch feature-register
# 意义：切换到指定分支
# 注意：切换前确保当前分支的修改已提交或暂存

# 4. 创建并切换到新分支（一步完成）
git checkout -b feature-register
# 或
git switch -c feature-register
# 意义：创建新分支并立即切换过去
# 常用场景：开始新功能开发

# 5. 在分支上开发
git add .
git commit -m "feat: 完成用户注册功能"

# 6. 合并分支到主线
git checkout master    # 切换回主线
git merge feature-register
# 意义：将 feature-register 的改动合并到 master
# 注意：如果有冲突需要解决冲突

# 7. 删除已合并的分支
git branch -d feature-register
# 意义：删除不需要的分支
# 注意：-d 只能删除已合并的分支，-D 强制删除

# 8. 查看远程分支
git branch -r
# 意义：列出所有远程分支
```

### 场景六：团队协作

**适用情况**：多人协同开发，需要同步代码

```bash
# 1. 克隆远程仓库
git clone https://github.com/yourname/repo.git
# 意义：下载远程仓库到本地
# 注意：会自动创建远程连接 origin

# 2. 查看远程仓库
git remote -v
# 意义：查看配置的远程仓库地址
# 输出示例：
#   origin  https://github.com/yourname/repo.git (fetch)
#   origin  https://github.com/yourname/repo.git (push)

# 3. 拉取远程更新
git pull origin master
# 意义：从远程仓库拉取最新代码并合并
# 注意：等同于 git fetch + git merge
# 适用场景：每天开始工作前，先同步最新代码

# 4. 推送本地更新
git push origin master
# 意义：将本地提交推送到远程仓库
# 注意：如果是首次推送，使用 git push -u origin master

# 5. 安全的拉取方式（推荐）
git fetch origin
git log HEAD..origin/master  # 查看远程有哪些新提交
git merge origin/master
# 意义：先拉取再合并，可以预览远程改动
# 适用场景：想了解远程改动后再合并

# 6. 处理推送冲突
git push origin master
# 如果报错：Updates were rejected
git pull origin master  # 先拉取
# 解决冲突后
git add .
git commit -m "合并远程更新"
git push origin master
```

### 场景七：解决冲突

**适用情况**：合并分支或 pull 时出现冲突

```bash
# 1. 尝试合并时出现冲突
git merge feature-login
# 输出：CONFLICT (content): Merge conflict in app.py

# 2. 查看冲突文件
git status
# 意义：列出所有有冲突的文件
# 输出示例：
#   both modified:  app.py

# 3. 打开冲突文件，查找冲突标记
cat app.py
# 冲突标记示例：
#
# <<<<<<< HEAD
# def login(username, password):
#     return "v1"
# =======
# def login(username, password, code):
#     return "v2"
# >>>>>>> feature-login
#
# 意义：
#   HEAD 之间的内容：当前分支的代码
#   ===== 到 >>>>> 之间的内容：要合并分支的代码

# 4. 手动编辑文件，解决冲突
def login(username, password, code=None):
    if code:
        return "v2"
    return "v1"
# 注意：删除所有 <<<<<<< ======= >>>>>>> 标记

# 5. 标记冲突已解决
git add app.py
# 意义：告诉 Git 冲突已经解决

# 6. 完成合并
git commit -m "合并 feature-login 分支，解决登录参数冲突"
# 意义：完成合并提交
```

---

## Cursor 中的 Git 操作

> Cursor 是基于 AI 的代码编辑器，内置了强大的 Git 图形化界面。对于日常开发，使用 Cursor 的可视化操作比命令行更直观方便。

### Cursor 的 Git 界面介绍

#### 1. 打开 Git 面板

**方法一**：点击左侧活动栏的分支图标
```
位置：左侧边栏，第三个图标（类似分叉的线条）
快捷键：Ctrl+Shift+G (Windows/Linux) 或 Cmd+Shift+G (Mac)
```

**方法二**：使用命令面板
```
Ctrl+Shift+P (Windows/Linux) 或 Cmd+Shift+P (Mac)
输入 "Git: " 可以看到所有 Git 命令
```

#### 2. Git 面板说明

```
┌─────────────────────────────────────┐
│  源代码管理面板                      │
├─────────────────────────────────────┤
│  main (分支名称) ▼                   │  ← 当前分支
│  ┌───────────────────────────────┐  │
│  │ 更改 3                          │  ← 文件改动数量
│  ├───────────────────────────────┤  │
│  │ M app.py      (修改)           │  ← 已修改文件
│  │ A utils.py    (新增)           │  ← 新增文件
│  │ D old.py      (删除)           │  ← 删除文件
│  │ ? test.tmp    (未跟踪)         │  ← 未跟踪文件
│  └───────────────────────────────┘  │
│                                      │
│  [暂存更改] [放弃] [提交]            │  ← 操作按钮
│  [消息框] 输入提交信息...            │  ← 提交信息
│                                      │
│  ⬆ 推送  ⬇ 拉取  ...更多           │  ← 推送/拉取
└─────────────────────────────────────┘
```

### 日常开发操作（Cursor 版）

#### 操作1：查看文件修改

**步骤**：
1. 打开源代码管理面板（Ctrl+Shift+G）
2. 点击文件名，查看修改对比

**界面说明**：
```
左侧：原版本内容       右侧：修改后内容
────────────────      ───────────────
def hello():          def hello():
    return "hi"   →       return "hello"
                      ┃
                   绿色=新增
                   红色=删除
                   蓝色=修改
```

**快捷操作**：
- 点击文件右侧的 `M` 图标：查看单个文件修改
- 右键文件 → "打开文件"：直接跳转到文件
- 双击文件：在编辑器中打开修改对比

#### 操作2：暂存文件修改

**方法一：暂存单个文件**
```
1. 在 Git 面板找到要暂存的文件
2. 点击文件名右侧的 `+` 号
3. 文件从"更改"区域移到"暂存的更改"区域
```

**方法二：暂存所有修改**
```
1. 点击"更改"标题右侧的 `+` 号
2. 或使用快捷键：Ctrl+Enter
```

**方法三：暂存部分修改（交互式暂存）**
```
1. 右键文件 → "暂存选中的更改"
2. 或点击文件，选择要暂存的代码块
3. 点击代码块标题的 `+` 号
```

**场景示例**：
```
假设 app.py 中有两个功能修改：
  - 修改了登录功能
  - 添加了注册功能

只想提交注册功能：
  1. 点击 app.py 查看修改
  2. 找到注册功能的代码块
  3. 点击该代码块的 `+` 号
  4. 只暂存注册相关的修改
```

#### 操作3：提交代码

**步骤**：
```
1. 暂存要提交的文件（见操作2）
2. 在顶部的消息框输入提交信息
   例如："feat: 添加用户注册功能"
3. 点击 "✓ 提交" 按钮（或按 Ctrl+Enter）
```

**提交信息规范**：
```
✅ 好的提交信息：
  - feat: 添加用户登录功能
  - fix: 修复登录超时问题
  - docs: 更新 README 文档

❌ 不好的提交信息：
  - update
  - 修改
  - 1
```

**注意**：
- 提交前确保暂存区文件正确
- 提交信息清晰描述做了什么
- Cursor 会自动显示暂存的文件数量

#### 操作4：推送到远程

**方法一：使用状态栏**
```
1. 查看底部状态栏
2. 点击 "↓↗" 图标（同步更改）
3. 或点击分支名称，选择 "推送"
```

**方法二：使用 Git 面板**
```
1. 在 Git 面板顶部找到"..."菜单
2. 选择 "推送" (Push)
3. 或使用快捷键：Ctrl+Shift+P → "Git: 推送"
```

**方法三：推送时设置上游**
```
首次推送分支时：
1. 点击状态栏的分支图标
2. 选择 "发布分支" (Publish Branch)
```

#### 操作5：拉取远程更新

**方法一：使用状态栏**
```
1. 查看底部状态栏
2. 点击 "↓↗" 图标（拉取）
3. Cursor 会自动拉取并合并
```

**方法二：定期自动拉取**
```
设置自动拉取：
1. Ctrl+, 打开设置
2. 搜索 "git.autofetch"
3. 勾选 "Git: Auto Fetch"
4. 设置间隔时间（例如：5分钟）
```

**方法三：手动拉取**
```
1. Ctrl+Shift+P
2. 输入 "Git: 拉取"
3. 回车执行
```

#### 操作6：创建和切换分支

**创建新分支**：
```
1. 点击状态栏的分支名称（如 "main"）
2. 输入新分支名称（如 "feature-login"）
3. 回车确认
4. Cursor 会自动创建并切换到新分支
```

**切换已有分支**：
```
1. 点击状态栏的分支名称
2. 从下拉列表选择目标分支
3. 点击分支名称切换
```

**查看所有分支**：
```
1. 点击状态栏分支名称
2. 查看列表：
   - main (当前分支，有✓标记)
   - feature-login
   - feature-register
```

**从远程创建本地分支**：
```
1. Ctrl+Shift+P
2. 输入 "Git: 从...签出"
3. 选择远程分支（如 origin/feature-login）
4. Cursor 会创建本地分支并切换
```

#### 操作7：解决冲突（可视化）

**冲突发生时**：
```
1. Cursor 会自动检测冲突
2. 冲突文件显示在 "更改" 列表中
3. 文件旁边显示特殊图标 (!)
```

**打开冲突文件**：
```
文件内容示例：
┌──────────────────────────────────────────┐
│ <<<<<<< HEAD                              │
│ def login(username, password):           │  ← 当前分支
│     return "v1"                           │
│ =======                                   │
│ def login(username, password, code):     │  ← 合并分支
│     return "v2"                           │
│ >>>>>>> feature-login                     │
└──────────────────────────────────────────┘
```

**解决冲突的方法**：

**方法一：使用操作按钮（推荐）**
```
1. 点击冲突标记上方的操作栏
2. 选择：
   - "接受当前更改" (保留 HEAD 的内容)
   - "接受传入更改" (保留合并分支的内容)
   - "接受两者" (两边都保留)
   - "比较更改" (手动合并)
```

**方法二：手动编辑**
```
1. 删除 <<<<<<< ======= >>>>>>> 标记
2. 编辑代码为最终想要的结果：
   def login(username, password, code=None):
       if code:
           return "v2"
       return "v1"
3. 保存文件
```

**标记冲突已解决**：
```
1. 右键文件 → "添加"
2. 或点击文件名右侧的 `+` 号
3. 提交合并：
   Ctrl+Shift+P → "Git: 完成合并"
```

#### 操作8：查看历史记录

**查看提交历史**：
```
1. Ctrl+Shift+P
2. 输入 "Git: 显示提交历史"
3. 右侧会显示时间线视图
```

**时间线视图说明**：
```
┌──────────────────────────────────────┐
│ 提交历史                              │
├──────────────────────────────────────┤
│ ● a1b2c3d (当前)                     │
│ │ feat: 添加登录功能                  │
│ │ 张三 2024-01-26                    │
│ ├────────────────────────────────────┤
│ ● d4e5f6g                            │
│ │ fix: 修复超时问题                   │
│ │ 李四 2024-01-25                    │
│ └────────────────────────────────────┘

点击提交：
  - 查看详细信息
  - 查看修改内容
  - 回退到此版本
```

**查看文件历史**：
```
1. 右键文件 → "打开文件"
2. 右键编辑器标题 → "打开时间线"
3. 查看该文件的所有修改历史
```

**查看某行代码的提交**：
```
1. 右键代码行 → "Git: 查看 blamed"
2. 或使用 blame 模式：
   Ctrl+Shift+P → "Git: 查看文件修订版本"
3. 每行代码旁边显示提交信息和作者
```

#### 操作9：撤销修改

**撤销工作区修改**：
```
1. 在 Git 面板找到要撤销的文件
2. 右键文件 → "放弃更改"
3. 确认对话框：点击"放弃更改"
⚠️ 注意：此操作不可逆！
```

**取消暂存**：
```
1. 在"暂存的更改"区域找到文件
2. 点击文件名右侧的 `-` 号
3. 文件回到"更改"区域
```

**撤销最近一次提交**：
```
1. Ctrl+Shift+P
2. 输入 "Git: 撤销上一次提交"
3. 选择：
   - "软撤消"：保留修改在暂存区
   - "硬撤消"：丢弃所有修改
⚠️ 注意：如果已推送，需要强制推送！
```

#### 操作10：使用 Stash 暂存工作现场

**暂存当前工作**：
```
1. 在 Git 面板点击 "..." 菜单
2. 选择 "Stash: 暂存更改"
3. 输入 stash 描述（可选）
4. 工作区变干净
```

**查看 Stash 列表**：
```
1. Ctrl+Shift+P
2. 输入 "Git: 显示所有 Stash"
3. 显示所有暂存的现场
```

**恢复 Stash**：
```
1. 在 Stash 列表中选择要恢复的项
2. 点击 "应用 Stash"：恢复但不删除记录
3. 或点击 "弹出 Stash"：恢复并删除记录
```

### Cursor Git 常用快捷键

| 操作 | Windows/Linux | Mac |
|------|---------------|-----|
| 打开源代码管理 | `Ctrl+Shift+G` | `Cmd+Shift+G` |
| 提交 | `Ctrl+Enter` | `Cmd+Enter` |
| 暂存文件 | `Ctrl+K Ctrl+I` | `Cmd+K Cmd+I` |
| 推送 | `Ctrl+Shift+P` → "推送" | `Cmd+Shift+P` → "推送" |
| 拉取 | `Ctrl+Shift+P` → "拉取" | `Cmd+Shift+P` → "拉取" |
| 撤销文件修改 | 右键 → "放弃更改" | 右键 → "放弃更改" |
| 查看历史 | `Ctrl+Shift+P` → "显示历史" | `Cmd+Shift+P` → "显示历史" |

### Cursor Git 最佳实践

#### ✅ 推荐工作流

**1. 每天开始工作前**
```
1. 打开 Cursor
2. 点击状态栏的 "↓↗" 拉取最新代码
3. 查看是否有冲突
```

**2. 开发新功能时**
```
1. 创建功能分支：
   点击状态栏分支名 → 输入 "feature-xxx"
2. 编写代码
3. 随时查看修改（Git 面板）
4. 分阶段提交：
   - 暂存相关文件
   - 输入清晰提交信息
   - 提交
```

**3. 提交前检查**
```
1. 打开 Git 面板
2. 查看暂存的文件列表
3. 点击文件查看修改内容
4. 确认无误后提交
```

**4. 定期推送**
```
1. 完成一个功能点 → 提交
2. 点击状态栏 "↓↗" 推送
3. 避免大量本地未推送提交
```

**5. 遇到冲突时**
```
1. 不要慌，仔细查看冲突内容
2. 使用 Cursor 的冲突解决工具
3. 保留正确的代码
4. 测试后再提交
```

#### ❌ 常见错误

**1. 忘记拉取最新代码**
```
❌ 直接修改 → 推送 → 冲突
✅ 拉取 → 修改 → 推送
```

**2. 提交了不该提交的文件**
```
❌ git add . → 提交了 node_modules/
✅ 查看 Git 面板 → 只暂存需要的文件
```

**3. 提交信息不清晰**
```
❌ "update" / "修改" / "1"
✅ "feat: 添加用户登录功能"
```

**4. 在主分支直接开发**
```
❌ 在 main/master 直接修改
✅ 创建功能分支 → 开发 → 合并
```

### Cursor vs 命令行对比

| 操作 | Cursor 操作 | 命令行操作 | 优劣势 |
|------|------------|-----------|--------|
| 查看状态 | Git 面板 | `git status` | Cursor 更直观 |
| 暂存文件 | 点击 `+` 号 | `git add` | Cursor 可视化 |
| 查看修改 | 点击文件 | `git diff` | Cursor 对比清晰 |
| 提交 | 填写消息框 | `git commit -m "xxx"` | Cursor 需要更多点击 |
| 推送/拉取 | 状态栏图标 | `git push/pull` | 持平 |
| 切换分支 | 点击分支名 | `git checkout` | Cursor 更方便 |
| 查看历史 | 时间线视图 | `git log` | Cursor 图形化 |
| 解决冲突 | 可视化操作 | 手动编辑 | Cursor 更友好 |

**建议**：
- 日常开发：使用 Cursor 界面（更直观）
- 复杂操作：结合命令行（更灵活）
- 批量操作：使用命令行（更高效）

---

## 实用技巧

### 技巧1：提交前检查

```bash
# 1. 提交前查看要提交什么
git diff --cached
# 意义：确认即将提交的内容是否符合预期
# 好习惯：每次提交前都看一眼

# 2. 只添加部分修改（交互式暂存）
git add -p app.py
# 意义：选择性地添加某几行修改
# 操作：
#   y - 暂存这块修改
#   n - 不暂存这块修改
#   q - 退出
# 适用场景：一个文件改了多个功能，想分开提交
```

### 技巧2：修改最后一次提交

```bash
# 1. 忘记添加某个文件
git add forgotten_file.py
git commit --amend
# 意义：将新文件加入上一次提交
# 注意：不要修改已推送的提交！

# 2. 提交信息写错了
git commit --amend -m "正确的提交信息"
# 意义：修改上一次提交的说明
# 注意：会改变提交 hash

# 3. 想修改提交内容
git add new_file.py
git commit --amend --no-edit
# 意义：添加新文件到上一次提交，但不修改提交信息
```

### 技巧3：暂存工作现场

```bash
# 1. 临时切换分支，但当前还有未提交的修改
git stash
# 意义：保存当前工作现场，清空工作区
# 适用场景：紧急修复 bug，需要切换到其他分支

# 2. 查看暂存列表
git stash list
# 输出示例：
#   stash@{0}: On master: 修复登录问题

# 3. 恢复暂存的工作现场
git stash pop
# 意义：恢复最近一次暂存，并删除暂存记录

# 或只恢复不删除记录
git stash apply
```

### 技巧4：查看文件历史

```bash
# 1. 查看文件的修改历史
git log --follow app.py
# 意义：查看文件的所有修改记录（包括重命名）
# 适用场景：想了解某个文件是怎么演变的

# 2. 查看某行代码是谁写的
git blame app.py
# 意义：显示每一行代码的提交信息
# 输出示例：
#   a1b2c3d (张三 2024-01-01 10:00:00) def hello():
#   d4e5f6g (李四 2024-01-02 11:00:00)     print("world")
# 适用场景：代码出问题，想找到责任人

# 3. 查看某次提交修改了哪些文件
git show --name-only a1b2c3d
# 意义：列出某次提交涉及的文件
```

### 技巧5：清除未跟踪文件

```bash
# 1. 查看哪些文件会被删除
git clean -n
# 意义：预览将要删除的未跟踪文件
# 注意：只删除未跟踪文件，不会删除已跟踪文件

# 2. 删除未跟踪文件
git clean -f
# 意义：删除所有未跟踪文件
# 警告：删除后不可恢复！

# 3. 删除未跟踪文件和目录
git clean -fd
# 意义：更彻底的清理

# 4. 一起删除忽略的文件
git clean -fx
# 意义：删除 .gitignore 中指定的文件
# 警告：非常危险！慎用！
```

---

## 问题排查

### 问题1：提交了敏感信息

**情况**：不小心把密码、密钥提交了

```bash
# 方案1：修改文件并重新提交（推荐，最安全）
# 1. 修改文件，删除敏感信息
vim config.py  # 删除密码
git add config.py
git commit -m "fix: 删除敏感信息"

# 2. 推送到远程
git push origin master

# 3. 通知团队成员拉取更新
# 注意：历史版本中仍有敏感信息，但最新版本已删除

# 方案2：使用 BFG Repo-Cleaner（快速清理，推荐）
# 安装：需要先安装 BFG 工具
# 下载：https://rtyley.github.io/bfg-repo-cleaner/

# 1. 备份仓库
git clone --mirror https://github.com/yourname/repo.git repo-backup

# 2. 清除敏感文件
bfg --delete-files config.py repo-backup

# 3. 清理仓库历史
cd repo-backup
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# 4. 强制推送
git push origin master --force

# 方案3：使用 git filter-repo（Python 工具，更强大）
# 安装：pip install git-filter-repo

# 1. 备份仓库
git clone --mirror https://github.com/yourname/repo.git repo-backup

# 2. 过滤文件
git filter-repo --invert-paths --path config.py

# 3. 强制推送（⚠️ 危险！）
git push origin master --force

# ⚠️ 警告：
# - 方案2和3会改变 Git 历史，所有提交 hash 都会改变
# - 如果其他人已经克隆了仓库，需要重新克隆
# - 只在确实需要完全清除敏感信息时使用
```

### 问题2：想撤销已推送的提交

```bash
# 情况1：还没人拉取你的代码（安全）
git reset --hard HEAD~1  # 本地回退
git push -f origin master  # 强制推送
# 意义：覆盖远程仓库的历史
# 警告：-f 是危险操作！

# 情况2：已经有人拉取了（推荐）
git revert HEAD  # 创建新提交撤销之前的修改
git push origin master
# 意义：不改变历史，用新提交撤销旧提交
# 优点：不会影响其他开发者
```

### 问题3：文件大小写修改 Git 没检测到

```bash
# Git 默认忽略文件名大小写
git config core.ignorecase false  # 关闭忽略大小写
git add -A
git commit -m "修改文件名大小写"
```

### 问题4：提示 detached HEAD

```bash
# 情况：切换到某个具体提交时
git checkout a1b2c3d
# 状态：HEAD detached at a1b2c3d

# 解决方案1：回到分支
git checkout master

# 解决方案2：基于这个提交创建新分支
git checkout -b new-branch
```

### 问题5：合并后想撤销

```bash
# 合并后发现有问题
git reset --hard HEAD~1
# 意义：撤销合并提交
# 注意：如果已经推送，使用 git revert

# 或者：使用 reflog 恢复
git reflog  # 查看操作历史
git reset --hard HEAD@{1}  # 回退到之前的状态
```

---

## 日常开发最佳实践

### ✅ 推荐习惯

1. **小步提交**：每个功能分多次提交，而不是一次性提交大改动
   ```bash
   # 不好：一次性提交所有功能
   git commit -m "完成所有功能"

   # 好：分步骤提交
   git commit -m "添加数据库模型"
   git commit -m "实现业务逻辑"
   git commit -m "添加单元测试"
   ```

2. **清晰的提交信息**：让别人（包括未来的自己）看懂
   ```bash
   # 不好
   git commit -m "update"

   # 好
   git commit -m "修复：用户注册时缺少邮箱验证"
   ```

3. **提交前检查**：确认要提交的内容
   ```bash
   git diff --cached  # 看看要提交什么
   git status         # 确认文件列表
   ```

4. **及时推送**：本地提交后尽快推送，避免丢失
   ```bash
   git commit -m "xxx"
   git push origin master  # 养成习惯
   ```

5. **善用 .gitignore**：避免提交无用文件
   ```bash
   cat .gitignore
   # 忽略编译文件
   __pycache__/
   *.pyc
   # 忽略依赖
   node_modules/
   # 忽略配置
   .env
   ```

### ❌ 避免的错误

1. **不要提交敏感信息**
   ```bash
   # 提交前检查
   git diff | grep -i "password\|key\|secret"
   ```

2. **不要在 .gitignore 中已经忽略的文件里修改**
   ```bash
   # 如果 .gitignore 有 *.log
   # 但你修改了 debug.log，Git 不会跟踪这个文件
   ```

3. **不要强制推送公共分支**
   ```bash
   # 危险操作
   git push -f origin master
   # 会覆盖别人的代码
   ```

4. **不要提交编译生成的文件**
   ```bash
   # Python
   __pycache__/
   *.pyc
   *.pyo

   # JavaScript
   node_modules/
   package-lock.json  # 可选

   # Java
   *.class
   target/
   ```

---

## 快速参考命令

### 日常操作

```bash
git status                  # 查看状态
git add <file>              # 添加文件
git add .                   # 添加所有修改
git commit -m "msg"         # 提交
git push origin master      # 推送
git pull origin master      # 拉取
```

### 查看操作

```bash
git log                     # 查看历史
git log --oneline           # 精简历史
git diff                    # 查看修改
git show <commit>           # 查看某次提交
```

### 分支操作

```bash
git branch                  # 查看分支
git branch <name>           # 创建分支
git checkout <name>         # 切换分支
git checkout -b <name>      # 创建并切换
git merge <name>            # 合并分支
```

### 撤销操作

```bash
git checkout -- <file>      # 撤销文件修改
git reset HEAD <file>       # 取消暂存
git reset --soft HEAD~1     # 撤销提交保留修改
git reset --hard HEAD~1     # 撤销提交丢弃修改
```

---

## 总结

### Git 工作流程图

```
开始工作
   ↓
拉取最新代码 (git pull)
   ↓
创建功能分支 (git checkout -b feature-xxx)
   ↓
编写代码、修改文件
   ↓
查看修改 (git diff)
   ↓
添加到暂存区 (git add)
   ↓
提交到本地 (git commit -m "描述")
   ↓
推送到远程 (git push)
   ↓
发起合并请求 (Pull Request)
   ↓
代码审查通过
   ↓
合并到主分支 (git merge)
   ↓
删除功能分支 (git branch -d)
```

### 学习建议

1. **从简单开始**：先掌握 add/commit/pull/push 四个命令
2. **多用 git log**：了解项目的演进历史
3. **善用图形工具**：VS Code、Sourcetree 等工具可视化操作
4. **不怕犯错**：Git 的操作大多可以撤销，大胆尝试
5. **查阅文档**：遇到问题查 [Git 官方文档](https://git-scm.com/doc)

---

## 附录：常见问题 FAQ

### Q1: git 和 GitHub 的区别？

**A**: Git 是版本控制工具（软件），GitHub 是托管平台（网站）。就像浏览器和网站的关系。

### Q2: 什么时候用分支？

**A**:
- ✅ 开发新功能时
- ✅ 修复 bug 时
- ✅ 实验性代码时
- ❌ 修改一句话时没必要

### Q3: commit 和 push 的区别？

**A**:
- commit：提交到本地仓库（自己的电脑）
- push：推送到远程仓库（GitHub/GitLab）
- 类比：commit 是存到本地硬盘，push 是上传到网盘

### Q4: 如何写好 commit message？

**A**: 遵循 [约定式提交](https://www.conventionalcommits.org/) 规范

```bash
# 格式：<类型>: <描述>

# 类型
feat:     新功能
fix:      修复 bug
docs:     文档修改
style:    代码格式（不影响功能）
refactor: 重构（不是新功能也不是修复）
test:     测试相关
chore:    构建/工具相关

# 示例
feat: 添加用户登录功能
fix: 修复登录超时问题
docs: 更新 README 安装说明
refactor: 优化数据库查询逻辑
```

### Q5: .gitignore 文件不生效？

**A**: 可能文件已经被 Git 跟踪了，需要先清除缓存

```bash
git rm -r --cached .
git add .
git commit -m "修复：.gitignore 生效"
```

---

**手册版本**: v2.0
**更新时间**: 2026-01-26
**更新内容**：
- 增加 Cursor 编辑器的 Git 操作指南
- 修正 `git refind` 为 `git reflog`
- 更新敏感信息清理方案（替换已弃用的 `git filter-branch`）
- 优化 Cursor 可视化操作说明

**适用场景**: 日常开发、团队协作、Cursor 用户

> 💡 **提示**: Git 的功能非常强大，本手册只涵盖最常用的 20% 命令，但足以应对 80% 的场景。遇到复杂问题时，建议查阅官方文档或寻求帮助。
