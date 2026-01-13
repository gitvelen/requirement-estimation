# Docker部署完全傻瓜教程

> 适用人群：完全不懂Docker的开发者
> 目标：把你开发好的系统部署到另一台服务器上

> **📌 重要更新（2026-01-06）**
> - 已修复 Docker 镜像源配置问题（使用腾讯云镜像源）
> - 已修复 buildx 版本限制问题（使用 docker build 代替 docker-compose build）
> - 部署脚本已优化，可直接使用

---

## 📖 第一章：Docker是什么？（3分钟了解）

### 1.1 生活化比喻

想象一下：

**传统部署** = 你要搬家
- 你需要在新房子里重新配置床、衣柜、桌子...
- 很麻烦，而且可能忘记带某些东西

**Docker部署** = 住酒店
- 房间已经布置好了，你带着行李直接住进去
- 所有设施都是标准配置，不会少东西

**具体到我们的项目**：

```
你的程序 = 一套家具
依赖环境 = 房间基础设施
├─ Python = 房屋结构
├─ Node.js = 水电
├─ 各种库 = 装饰品

传统方式：到新服务器要重新安装Python、Node.js、配置环境...
Docker方式：把"房子+家具"整体打包，搬到哪都能用
```

### 1.2 Docker的核心概念（只需记住3个）

#### 概念1：镜像（Image）
- **是什么**：就是一个"打包文件"
- **比喻**：像一个"虚拟机模板"
- **例子**：`python:3.10` = 装了Python 3.10的Linux系统

#### 概念2：容器（Container）
- **是什么**：镜像运行后的实例
- **比喻**：像"虚拟机"
- **例子**：后端容器、前端容器

#### 概念3：Docker Compose
- **是什么**：同时管理多个容器的工具
- **比喻**：像"总控制器"
- **例子**：同时启动前端和后端

### 1.3 我们要做什么

```
开发服务器（当前环境）          生产服务器（目标环境）
├─ 程序已经写好               └─ 需要部署到这里
├─ 能正常运行                 └─ 让用户能访问
└─ 任务：打包并迁移             └─ 稳定运行
```

**你只需要做3件事**：
1. 在开发服务器打包项目
2. 传输到生产服务器
3. 在生产服务器运行一条命令

---

## 📄 第二章：关键文件详解（必读）

> 为什么需要这一章？
> 因为Docker部署需要多个配置文件，理解它们的作用，你才能知道为什么这样部署，遇到问题也知道怎么修改。

### 2.0 关键文件创建流程总览

在详细介绍每个文件之前，先了解它们的**创建时机**和**创建方式**。

#### 文件分类

**手动创建的配置文件**（需要你编写）：
```
✏️ Dockerfile              - 手动编写：定义镜像构建步骤
✏️ docker-compose.yml      - 手动编写：定义多容器编排
✏️ entrypoint.sh           - 手动编写：容器启动脚本（推荐）
✏️ .env                   - 手动编写：环境变量配置（项目初始化时）
✏️ frontend/nginx.conf    - 手动编写：Nginx 配置（前端）
```

**自动生成的文件**（由工具生成）：
```
🤖 pyproject.toml         - 自动生成：由 `uv init` 命令生成
🤖 uv.lock                - 自动生成：由 `uv lock` 命令生成
🤖 requirements.txt       - 自动生成：由 `uv pip compile` 导出（已弃用）
```

**项目源代码文件**：
```
📁 backend/               - 后端代码
📁 frontend/              - 前端代码
```

#### 创建时机和顺序

**阶段 1：项目初始化（开发环境）**

```bash
# 步骤 1：创建项目目录
mkdir requirement-estimation-system
cd requirement-estimation-system

# 步骤 2：初始化项目（自动生成 pyproject.toml）
uv init
# ✅ 自动创建 pyproject.toml

# 步骤 3：添加依赖（自动更新 pyproject.toml）
uv add fastapi uvicorn[standard] python-multipart
uv add pydantic pydantic-settings
uv add python-docx openpyxl
uv add langchain langchain-openai langgraph dashscope
# ✅ pyproject.toml 已自动更新

# 步骤 4：生成 uv.lock（自动生成）
uv lock
# ✅ 自动生成 uv.lock（锁定 91 个包的精确版本）

# 步骤 5：创建环境变量配置
cat > .env << 'EOF'
# 通义千问 API Key
DASHSCOPE_API_KEY=sk-06d3e30888684226a65056a4c6a21c4b

# 服务配置
HOST=0.0.0.0
PORT=443
DEBUG=false
WORKERS=4

# 文件路径
UPLOAD_DIR=uploads
REPORT_DIR=data

# 时区
TZ=Asia/Shanghai
EOF
# ✅ .env 已创建（不要提交到 Git）

# 步骤 6：创建后端代码
mkdir backend
# 编写 backend/app.py 等代码...

# ✅ 阶段 1 完成：依赖管理和环境配置已就绪
```

**阶段 2：Docker 配置（准备部署）**

```bash
# 步骤 7：创建 Dockerfile
cat > Dockerfile << 'EOF'
FROM python:3.10-slim
# ... Dockerfile 内容
EOF

# 步骤 8：创建 entrypoint.sh（推荐）
cat > entrypoint.sh << 'EOF'
#!/bin/bash
set -e

# 等待依赖服务（如果需要）
# until pg_isready -h db -U user; do
#   echo "等待数据库启动..."
#   sleep 2
# done

# 执行数据库迁移（如果需要）
# python manage.py migrate

# 启动应用
exec "$@"
EOF

chmod +x entrypoint.sh

# 步骤 9：创建 docker-compose.yml
cat > docker-compose.yml << 'EOF'
version: '3.8'
services:
  backend:
    build: .
    # ... 配置内容
EOF

# 步骤 10：配置 Nginx（前端）
cat > frontend/nginx.conf << 'EOF'
events {
    worker_connections 1024;
}
http {
    # ... Nginx 配置
}
EOF

# ✅ 阶段 2 完成：Docker 配置已就绪
```

**阶段 3：验证和部署**

```bash
# 步骤 11：验证文件完整性
ls -la
# 应该看到：
# - Dockerfile
# - docker-compose.yml
# - pyproject.toml
# - uv.lock
# - .env
# - entrypoint.sh

# 步骤 12：测试构建
docker build -t requirement-backend .

# 步骤 13：测试运行
docker-compose up -d

# ✅ 阶段 3 完成：项目已部署
```

#### 文件创建决策树

```
从零开始部署
│
├─ 1. 创建项目目录
│   └─ mkdir requirement-estimation-system
│
├─ 2. 初始化依赖管理
│   ├─ uv init（自动生成 pyproject.toml）
│   ├─ uv add fastapi uvicorn ...（自动更新 pyproject.toml）
│   └─ uv lock（自动生成 uv.lock）
│
├─ 3. 配置环境变量
│   └─ 创建 .env（手动编写，API Key 等配置）
│
├─ 4. 编写项目代码
│   ├─ backend/app.py（手动编写）
│   └─ frontend/（手动编写）
│
├─ 5. 配置 Docker
│   ├─ 创建 Dockerfile（手动编写）
│   ├─ 创建 entrypoint.sh（手动编写，推荐）
│   ├─ 创建 docker-compose.yml（手动编写）
│   └─ 创建 frontend/nginx.conf（手动编写）
│
└─ 6. 部署
    ├─ docker build（构建镜像）
    └─ docker-compose up（启动容器）
```

#### 各文件的详细创建时机

| 文件 | 创建时机 | 创建方式 | 谁创建 | 何时更新 |
|------|---------|---------|--------|---------|
| **pyproject.toml** | 项目初始化时 | `uv init` 自动生成 | **自动生成** | 添加/删除依赖时（uv add） |
| **uv.lock** | pyproject.toml 之后 | `uv lock` 自动生成 | **自动生成** | 依赖变更后自动更新 |
| **.env** | 项目初始化时 | 手动编写 | 开发者 | 修改配置时 |
| **Dockerfile** | 准备容器化时 | 手动编写 | 开发者 | 修改构建步骤时 |
| **entrypoint.sh** | 准备容器化时 | 手动编写 | 开发者 | 修改启动逻辑时 |
| **docker-compose.yml** | 配置多容器时 | 手动编写 | 开发者 | 修改服务配置时 |
| **frontend/nginx.conf** | 准备前端部署时 | 手动编写 | 开发者 | 修改 Nginx 配置时 |

#### 什么时候需要创建/修改这些文件？

**场景 A：从零开始新项目**

```bash
# 1. 创建项目目录
mkdir requirement-estimation-system
cd requirement-estimation-system

# 2. 初始化项目（自动生成 pyproject.toml）
uv init
# ✅ pyproject.toml 已创建

# 3. 添加依赖（自动更新 pyproject.toml）
uv add fastapi uvicorn[standard] python-multipart
uv add pydantic pydantic-settings
uv add python-docx openpyxl
uv add langchain langchain-openai langgraph dashscope
# ✅ pyproject.toml 已更新

# 4. 生成锁文件（自动生成 uv.lock）
uv lock
# ✅ uv.lock 已生成（91 个包）

# 5. 创建环境变量配置
cat > .env << 'EOF'
DASHSCOPE_API_KEY=sk-your-api-key
HOST=0.0.0.0
PORT=443
EOF

# 6. 创建后端代码
mkdir backend
vim backend/app.py

# 7. 创建 Dockerfile
vim Dockerfile

# 8. 创建 entrypoint.sh（推荐）
vim entrypoint.sh
chmod +x entrypoint.sh

# 9. 创建 docker-compose.yml
vim docker-compose.yml

# 10. 测试部署
docker-compose up -d
```

**场景 B：已有项目，添加容器化**

```bash
# 1. 项目已存在，代码已写好
ls backend/app.py  # ✅ 存在

# 2. 初始化依赖管理（自动生成 pyproject.toml）
uv init
# ✅ pyproject.toml 已创建

# 3. 添加依赖
uv add fastapi uvicorn python-multipart pydantic
# ✅ pyproject.toml 已更新

# 4. 生成锁文件
uv lock
# ✅ uv.lock 已生成

# 5. 创建环境变量配置
cat > .env << 'EOF'
DASHSCOPE_API_KEY=sk-your-api-key
HOST=0.0.0.0
PORT=443
EOF

# 6. 创建 Dockerfile
vim Dockerfile

# 7. 创建 entrypoint.sh
vim entrypoint.sh
chmod +x entrypoint.sh

# 8. 创建 docker-compose.yml
vim docker-compose.yml

# 9. 部署
docker-compose up -d
```

**场景 C：更新依赖**

```bash
# 1. 添加新依赖
uv add pandas

# ✅ 自动更新 pyproject.toml
# ✅ 自动更新 uv.lock

# 2. 提交更改
git add pyproject.toml uv.lock
git commit -m "Add pandas dependency"

# 3. 重新构建（如果使用 Docker）
docker build -t requirement-backend .
```

**场景 D：修改配置**

```bash
# 修改 .env
vim .env
# 修改配置后重启服务
docker-compose restart backend

# 修改 docker-compose.yml
vim docker-compose.yml
# 修改配置后重新启动
docker-compose down
docker-compose up -d

# 修改 Dockerfile
vim Dockerfile
# 修改后重新构建
docker build -t requirement-backend .
docker-compose up -d
```

#### 快速检查清单

部署前检查这些文件是否存在：

```bash
# ✅ 必需文件
[ -f Dockerfile ] && echo "✅ Dockerfile" || echo "❌ Dockerfile 缺失"
[ -f docker-compose.yml ] && echo "✅ docker-compose.yml" || echo "❌ docker-compose.yml 缺失"
[ -f pyproject.toml ] && echo "✅ pyproject.toml" || echo "❌ pyproject.toml 缺失"
[ -f uv.lock ] && echo "✅ uv.lock" || echo "❌ uv.lock 缺失"
[ -f entrypoint.sh ] && echo "✅ entrypoint.sh" || echo "❌ entrypoint.sh 缺失"

# ⚠️ 可选文件
[ -f .env ] && echo "✅ .env" || echo "⚠️  .env 不存在（可选）"
[ -f frontend/nginx.conf ] && echo "✅ nginx.conf" || echo "⚠️  nginx.conf 不存在"
```

#### 常见问题

**Q1：如何自动生成 pyproject.toml 和 uv.lock？**

**A**：使用 `uv` 命令自动生成。

```bash
# 步骤 1：初始化项目（自动生成 pyproject.toml）
uv init
# ✅ pyproject.toml 已创建

# 步骤 2：添加依赖（自动更新 pyproject.toml）
uv add fastapi uvicorn
# ✅ pyproject.toml 已更新

# 步骤 3：生成锁文件（自动生成 uv.lock）
uv lock
# ✅ uv.lock 已生成（91 个包）

# 完全自动化，无需手动编写！
```

**Q2：如果 uv.lock 不存在会怎样？**

**A**：Docker 构建会失败，或者运行 `uv sync` 时自动生成。

```bash
# Dockerfile 中这行会失败
COPY pyproject.toml uv.lock ./
# ❌ 如果 uv.lock 不存在，这行会报错

# 解决方案：
uv lock  # 生成 uv.lock
```

**Q3：可以手动编辑 uv.lock 吗？**

**A**：❌ 不建议！应该修改 pyproject.toml，然后重新生成 uv.lock。

```bash
# ❌ 错误：手动编辑 uv.lock
vim uv.lock

# ✅ 正确：修改 pyproject.toml
vim pyproject.toml
uv lock  # 重新生成
```

**Q4：什么时候需要重新生成 uv.lock？**

**A**：在以下情况下：

```bash
# 1. 添加/删除依赖后
uv add pandas
# ✅ 自动更新 uv.lock

# 2. 更新依赖版本后
uv lock --upgrade
# ✅ 更新 uv.lock

# 3. pyproject.toml 和 uv.lock 不一致时
uv lock
# ✅ 重新生成
```

**Q5：如何从头开始创建所有配置文件？**

**A**：使用项目模板或手动创建。

```bash
# 方式 A：使用项目模板（推荐）
# 项目已提供所有配置文件，直接使用

# 方式 B：手动创建（学习目的）
# 按照本教程第二章逐个创建
```

---

现在你已经了解了所有关键文件的创建时机，接下来详细学习每个文件的配置和使用。

### 2.1 Dockerfile - 镜像构建配方

#### 是什么？
`Dockerfile` 是一个文本文件，包含了构建 Docker 镜像的所有指令。

#### 作用
告诉 Docker 如何一步步构建出我们的后端服务镜像，包括：
- 使用什么基础镜像（操作系统+Python环境）
- 安装哪些依赖包
- 复制哪些项目文件
- 启动什么命令

#### 文件内容详解

```dockerfile
# 第1-6行：使用官方Python镜像 + 配置私服镜像源
FROM python:3.10-slim

# 定义构建参数（可通过 docker-compose 传递）
ARG UV_INDEX_URL=https://mirrors.cloud.tencent.com/pypi/simple
ENV UV_INDEX_URL=${UV_INDEX_URL}
# ↓ 说明：
#   FROM：指定基础镜像
#   python:3.10-slim：Python 3.10的轻量级版本（带Linux系统）
#   slim表示精简版，体积小，适合生产环境
#   ARG UV_INDEX_URL：定义构建参数，支持私服镜像
#   ENV UV_INDEX_URL：将构建参数设为环境变量，供 uv 使用

# 第8-9行：设置工作目录
WORKDIR /app
# ↓ 说明：
#   后续命令都在 /app 目录下执行
#   类似于 cd /app
#   注意：/app 是容器内的目录，Docker会自动创建
#        不需要在主机上预先创建这个目录

# 第11-14行：安装系统依赖和 uv
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && mv /root/.local/bin/uv /usr/local/bin/
# ↓ 说明：
#   RUN：在镜像中执行命令
#   apt-get update：更新软件包列表
#   apt-get install -y gcc curl：安装gcc编译器和curl（某些Python包需要编译）
#   curl -LsSf https://astral.sh/uv/install.sh | sh：安装 uv 包管理器
#   mv /root/.local/bin/uv /usr/local/bin/：将 uv 移动到系统 PATH
#   rm -rf /var/lib/apt/lists/*：清理缓存，减小镜像体积

# 第16-17行：复制依赖文件
COPY --chown=appuser:appuser requirements.txt .
# ↓ 说明：
#   COPY：从主机复制文件到镜像
#   --chown=appuser:appuser：将文件所有权赋予 appuser 用户
#   requirements.txt：主机上的依赖清单
#   .（点）：复制到当前工作目录（/app）

# 第19-20行：创建非 root 用户
RUN groupadd -r appuser && useradd -r -g appuser appuser
# ↓ 说明：
#   groupadd -r appuser：创建 appuser 组（-r 表示系统组）
#   useradd -r -g appuser appuser：创建 appuser 用户并加入 appuser 组
#   安全性：容器以非 root 用户运行，降低安全风险

# 第23行：复制项目配置文件（优先级高，利用缓存）
COPY --chown=appuser:appuser pyproject.toml uv.lock ./
# ↓ 说明：
#   pyproject.toml：项目配置和依赖声明（通过 uv init 自动生成）
#   uv.lock：依赖锁文件（通过 uv lock 自动生成，锁定 91 个包的精确版本）
#   先复制这两个文件可以优化 Docker 构建缓存（代码改动不会重新安装依赖）

# 第25-28行：使用 uv sync 安装依赖
RUN uv sync --frozen --no-dev --index-url ${UV_INDEX_URL}
# ↓ 说明：
#   uv sync：uv 的现代依赖安装方式（推荐）
#   --frozen：确保不修改 uv.lock（生产环境安全，lock 文件过期会报错）
#   --no-dev：不安装开发依赖（pytest、black 等）
#   --index-url ${UV_INDEX_URL}：使用环境变量中的镜像源
#   优势：
#     - 100% 可重现构建（锁定所有 91 个包的精确版本）
#     - SHA256 哈希验证（防止依赖篡改）
#     - 速度更快（~3秒，比 uv pip install 快 2-3 倍）
#   支持私服镜像：修改 docker-compose.yml 中的 UV_INDEX_URL 即可

# 第30-31行：复制项目文件并设置权限
COPY --chown=appuser:appuser . .
# ↓ 说明：
#   把当前目录下所有文件（除了.dockerignore指定的）
#   都复制到镜像的 /app 目录
#   --chown=appuser:appuser：确保 appuser 用户拥有所有文件

# 第33-34行：创建必要的目录并设置权限
RUN mkdir -p logs data uploads && \
    chown -R appuser:appuser /app
# ↓ 说明：
#   -p 参数：递归创建目录（如果父目录不存在也会创建）
#   logs：存放日志文件
#   data：存放生成的报告
#   uploads：存放上传的文件
#   chown -R appuser:appuser /app：递归设置 /app 目录所有权

# 第37-38行：验证依赖
RUN python3 -c "import sys; sys.path.insert(0, '.'); import backend.app" || (echo "依赖检查失败，请检查pyproject.toml" && exit 1)
# ↓ 说明：
#   尝试导入主应用模块，确保所有依赖已正确安装
#   如果失败，说明 pyproject.toml 中缺少某些依赖
#   如果失败，构建终止并提示错误

# 第39-40行：切换到非 root 用户
USER appuser
# ↓ 说明：
#   后续命令以 appuser 用户身份执行
#   容器运行时也使用 appuser 用户
#   安全性提升：即使容器被攻破，攻击者也无法获得 root 权限

# 第42-43行：暴露端口
EXPOSE 443
# ↓ 说明：
#   声明容器监听443端口
#   注意：这只是声明，实际端口映射在docker-compose.yml中配置

# 第45行：启动命令
CMD ["python3", "backend/app.py"]
# ↓ 说明：
#   容器启动时执行的命令
#   以 appuser 用户身份启动后端服务
```

#### 为什么这样写？

**问题1：为什么使用 uv 而不是 pip？**

- ⚡ **速度快**：uv 比 pip 快 10-100 倍（Rust 编写，并行下载）
- 🔒 **锁文件支持**：`uv.lock` 确保 100% 可重现构建
- 📦 **统一管理**：可以管理 Python 和 Node.js 依赖
- 🌐 **私服支持**：通过 `--index-url` 轻松配置私服镜像源

**问题2：为什么要创建非 root 用户？**

- ✅ **安全性**：防止容器被突破后获得主机 root 权限
- ✅ **最小权限原则**：只给应用必要的权限
- ✅ **合规性**：满足安全审计要求（Kubernetes 默认策略）
- ✅ **防止误操作**：避免应用意外修改系统文件

**安全对比**：
```bash
# root 用户运行容器
docker run -v /:/host/root -it ubuntu bash
# → 容器内可以访问主机的整个文件系统！非常危险

# 非 root 用户（本方案）
# → 容器被攻击也无法危害主机
```

**问题3：为什么用 `python:3.10-slim` 而不是 `python:3.10`？**
- `slim` 版本体积小（~150MB vs ~900MB）
- 包含运行Python程序所需的最小环境
- 构建速度快，部署传输快

**问题4：为什么最后才 `COPY . .` ？**
- Dockerfile 每一行都会创建一个镜像层
- 把不常变的代码放在后面，可以利用缓存
- 修改代码后重新构建，前面的层（安装依赖）可以复用

**问题5：为什么安装gcc？**
- 某些Python包（如python-multipart）需要C编译
- gcc提供编译环境

#### 如何修改？

**场景A：使用私服镜像源（内网部署）**

如果目标服务器部署在内网，需要使用自建的 PyPI 私服：

**步骤1：修改 docker-compose.yml**
```yaml
services:
  backend:
    build:
      context: .
      args:
        # 修改为你的私服地址
        - UV_INDEX_URL=http://192.168.1.200:8080/simple
        # 或带认证的私服：
        # - UV_INDEX_URL=http://admin:password@192.168.1.200:8080/simple
```

**步骤2：重新构建镜像**
```bash
docker-compose build --no-cache backend
```

**常见私服镜像源配置**：
```yaml
# 公有云镜像（默认）
- UV_INDEX_URL=https://mirrors.cloud.tencent.com/pypi/simple

# 阿里云镜像
- UV_INDEX_URL=https://mirrors.aliyun.com/pypi/simple

# 清华大学镜像
- UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

# 内网私服（需要自己搭建）
- UV_INDEX_URL=http://your-pypi-server:8080/simple

# 带认证的私服
- UV_INDEX_URL=http://username:password@your-pypi-server:8080/simple
```

**场景B：需要安装新的Python包**
```bash
# 1. 编辑 requirements.txt
vim requirements.txt
# 添加新包：pandas==2.0.0

# 2. 重新构建镜像
docker build -t requirement-backend .
```

**场景B：需要修改启动命令**
```dockerfile
# 如果要启动时执行其他命令
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "443"]
```

**场景C：本地开发使用 uv（不使用 Docker）**

如果你想在本地开发环境也使用 uv 加速依赖安装：

**安装 uv**：
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# 或使用 pip
pip install uv
```

**使用 uv 安装依赖**：
```bash
# 推荐方式：使用 uv sync（从 pyproject.toml + uv.lock 安装）
uv sync --index-url https://mirrors.cloud.tencent.com/pypi/simple

# 使用私服镜像
uv sync --index-url http://192.168.1.200:8080/simple

# 运行应用
uv run python backend/app.py

# 备注：如果只有 requirements.txt，也可以用兼容模式
uv pip install -r requirements.txt --index-url https://mirrors.cloud.tencent.com/pypi/simple
# 但这种方式不如 uv sync 精确和安全
```

**对比 pip 命令**：
```bash
# 旧方式（pip）
pip install -r requirements.txt -i https://mirrors.cloud.tencent.com/pypi/simple
# 耗时：约 30 秒

# 中间方式（uv pip install - 兼容模式）
uv pip install -r requirements.txt --index-url https://mirrors.cloud.tencent.com/pypi/simple
# 耗时：约 3 秒（快 10 倍）

# 最佳方式（uv sync - 推荐）
uv sync --index-url https://mirrors.cloud.tencent.com/pypi/simple
# 耗时：约 3 秒（快 10 倍，且更安全、更精确）
```

**场景D：需要设置环境变量**
```dockerfile
# 在 CMD 之前添加
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Shanghai
```

#### ENTRYPOINT vs CMD：有什么区别？

**CMD**：
```dockerfile
CMD ["python3", "backend/app.py"]
# ↓ 说明：
#   容器启动时执行的最后命令
#   可以被 docker run 后的参数覆盖
#   示例：docker run image python3 test.py  # 覆盖 CMD
```

**ENTRYPOINT**：
```dockerfile
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python3", "backend/app.py"]
# ↓ 说明：
#   ENTRYPOINT：容器启动时的入口点
#   CMD：传递给 ENTRYPOINT 的参数
#   最终执行：/app/entrypoint.sh python3 backend/app.py
```

**使用 ENTRYPOINT 的好处**：
- ✅ 预处理：启动前执行初始化脚本
- ✅ 灵活性：可以覆盖 CMD，保留初始化逻辑
- ✅ 复用性：多个容器可以共享同一个 entrypoint.sh

**实际效果**：
```bash
# 默认启动（执行 entrypoint.sh 中的初始化，然后启动应用）
docker run requirement-backend

# 覆盖启动命令（仍然执行 entrypoint.sh，但运行不同命令）
docker run requirement-backend python3 test.py
# 执行：/app/entrypoint.sh python3 test.py

# 完全覆盖 ENTRYPOINT（跳过 entrypoint.sh）
docker run --entrypoint bash requirement-backend
# 执行：bash（不执行 entrypoint.sh）
```

---

### 2.1.1 entrypoint.sh - 容器启动脚本

#### 是什么？
`entrypoint.sh` 是一个 Shell 脚本，在容器启动时自动执行。

#### 作用
- **预处理**：启动前执行初始化操作
- **环境检查**：验证环境变量和依赖
- **等待服务**：等待数据库等依赖服务启动
- **执行迁移**：运行数据库迁移脚本
- **健康检查**：验证应用是否可以正常启动
- **灵活性**：保留被覆盖的能力

#### 为什么使用 entrypoint.sh？

**对比不使用 entrypoint.sh**：

| 场景 | 不使用 entrypoint.sh | 使用 entrypoint.sh |
|------|---------------------|-------------------|
| **启动前检查** | ❌ 无法检查环境变量 | ✅ 自动验证必需配置 |
| **依赖服务** | ❌ 可能启动失败 | ✅ 等待依赖服务就绪 |
| **数据库迁移** | ❌ 需要手动执行 | ✅ 自动执行迁移 |
| **错误处理** | ⚠️ 难以定位问题 | ✅ 清晰的错误提示 |
| **可维护性** | ❌ 逻辑分散在 Dockerfile | ✅ 集中在脚本中 |

#### 文件内容详解

**entrypoint.sh 结构**：

```bash
#!/bin/bash
set -e  # 遇到错误立即退出

========== 环境变量验证 ==========
validate_env_vars() {
    # 检查 DASHSCOPE_API_KEY 等必需变量
    # 如果缺失，输出错误并退出
}

========== 创建必要的目录 ==========
create_directories() {
    mkdir -p /app/logs /app/data /app/uploads
    # 确保数据目录存在
}

========== 等待依赖服务 ==========
wait_for_dependencies() {
    # 等待数据库、Redis 等服务
    # 本项目不依赖外部服务，但保留扩展性
}

========== 执行数据库迁移 ==========
run_migrations() {
    # 如果使用数据库，在这里执行迁移
    # 本项目不使用数据库，但保留扩展性
}

========== 健康检查 ==========
health_check() {
    # 检查 Python 环境
    # 检查主应用文件
    # 尝试导入应用模块
}

========== 显示启动信息 ==========
show_startup_info() {
    # 显示项目名称、版本、配置等信息
}

========== 启动应用 ==========
main() {
    validate_env_vars
    create_directories
    wait_for_dependencies
    run_migrations
    health_check
    show_startup_info

    # 启动应用
    exec "$@"
}

# 执行主函数
main "$@"
```

#### 本项目的 entrypoint.sh 包含哪些功能？

**1. 环境变量验证**
```bash
validate_env_vars() {
    # 检查 DASHSCOPE_API_KEY
    if [ -z "$DASHSCOPE_API_KEY" ]; then
        echo_error "缺少 DASHSCOPE_API_KEY"
        exit 1
    fi
}
```

**2. 创建必要的目录**
```bash
create_directories() {
    mkdir -p /app/logs    # 日志目录
    mkdir -p /app/data    # 数据目录
    mkdir -p /app/uploads # 上传目录
}
```

**3. 健康检查**
```bash
health_check() {
    # 检查 Python 环境
    python3 --version

    # 检查主应用文件
    [ -f "/app/backend/app.py" ]

    # 尝试导入应用
    python3 -c "import backend.app"
}
```

**4. 显示启动信息**
```bash
show_startup_info() {
    echo "项目名称: Requirement Estimation System"
    echo "Python 版本: $(python3 --version)"
    echo "端口: ${PORT}"
    echo "调试模式: ${DEBUG}"
}
```

**5. 启动应用**
```bash
# 如果有参数，执行参数命令
# 否则使用默认命令
if [ $# -gt 0 ]; then
    exec "$@"
else
    exec python3 backend/app.py
fi
```

#### 在 Dockerfile 中使用

**配置 ENTRYPOINT 和 CMD**：

```dockerfile
# 复制 entrypoint.sh
COPY --chown=appuser:appuser entrypoint.sh /app/
RUN chmod +x /app/entrypoint.sh

# 设置入口点
ENTRYPOINT ["/app/entrypoint.sh"]

# 设置默认命令（可以被覆盖）
CMD ["python3", "backend/app.py"]
```

**执行流程**：
```
容器启动
    ↓
执行 ENTRYPOINT ["/app/entrypoint.sh"]
    ↓
运行 entrypoint.sh 脚本
    ├─ validate_env_vars()      ← 验证环境变量
    ├─ create_directories()       ← 创建目录
    ├─ wait_for_dependencies()   ← 等待依赖服务
    ├─ run_migrations()          ← 执行迁移
    ├─ health_check()            ← 健康检查
    └─ show_startup_info()       ← 显示信息
    ↓
执行 CMD ["python3", "backend/app.py"]
    ↓
应用启动
```

#### 如何修改 entrypoint.sh？

**场景 A：添加新的环境变量检查**

```bash
# 编辑 entrypoint.sh
vim entrypoint.sh

# 在 validate_env_vars() 函数中添加
required_vars=("DASHSCOPE_API_KEY" "NEW_VAR")

# 重新构建镜像
docker build -t requirement-backend .
```

**场景 B：添加数据库迁移**

```bash
# 编辑 entrypoint.sh
vim entrypoint.sh

# 在 run_migrations() 函数中添加
run_migrations() {
    echo_info "执行数据库迁移..."
    python manage.py migrate
}

# 重新构建
docker build -t requirement-backend .
```

**场景 C：添加依赖服务等待**

```bash
# 编辑 entrypoint.sh
vim entrypoint.sh

# 在 wait_for_dependencies() 函数中添加
wait_for_dependencies() {
    echo_info "等待 PostgreSQL..."
    until pg_isready -h db -U user; do
        echo_warn "数据库尚未就绪..."
        sleep 2
    done
}

# 重新构建
docker build -t requirement-backend .
```

#### 何时需要 entrypoint.sh？

**需要使用 entrypoint.sh 的情况**：
- ✅ 需要启动前验证环境
- ✅ 需要等待依赖服务
- ✅ 需要执行初始化脚本
- ✅ 需要数据库迁移
- ✅ 需要收集静态文件
- ✅ 想要更好的错误提示

**不需要使用 entrypoint.sh 的情况**：
- ⚠️ 简单应用，无需预处理
- ⚠️ 无依赖服务
- ⚠️ 追求极致简单

**本项目推荐使用**：
- ✅ 本项目使用 entrypoint.sh
- ✅ 验证 API Key 配置
- ✅ 创建必要目录
- ✅ 健康检查
- ✅ 清晰的启动日志
- ✅ 为将来扩展预留空间（数据库、缓存等）

#### 常见问题

**Q1：entrypoint.sh 执行失败怎么办？**

**A**：查看容器日志。

```bash
# 查看日志
docker logs requirement-backend

# 进入容器调试
docker exec -it requirement-backend bash
/app/entrypoint.sh  # 手动执行，查看错误
```

**Q2：如何跳过 entrypoint.sh？**

**A**：使用 `--entrypoint` 参数覆盖。

```bash
# 跳过 entrypoint.sh，直接执行 bash
docker run --entrypoint bash requirement-backend
```

**Q3：entrypoint.sh 如何调试？**

**A**：添加 `set -x` 开启调试模式。

```bash
#!/bin/bash
set -e  # 遇到错误退出
set -x  # 打印执行的每条命令（调试用）

# ... 脚本内容
```

**Q4：entrypoint.sh 会在容器重启时重新执行吗？**

**A**：是的！每次容器启动都会执行 entrypoint.sh。

```bash
# 容器启动 → 执行 entrypoint.sh → 启动应用
# 容器重启 → 再次执行 entrypoint.sh → 启动应用
# 容器停止 → 不执行 entrypoint.sh
```

#### 性能影响

**entrypoint.sh 会增加启动时间吗？**

- ⚠️ 会增加少量时间（通常 <1 秒）
- ✅ 但避免了运行时错误
- ✅ 提供了清晰的日志
- ✅ 一次性验证，长期受益

**性能对比**：

| 方式 | 启动时间 | 错误检测 | 可维护性 |
|------|---------|---------|---------|
| 不使用 entrypoint.sh | ~2秒 | ❌ 运行时才发现 | 差 |
| 使用 entrypoint.sh | ~2.5秒 | ✅ 启动前发现 | 好 |

---

### 2.2 docker-compose.yml - 多容器编排配置

#### 是什么？
`docker-compose.yml` 是一个 YAML 格式的配置文件，用于定义和运行多个容器。

#### 作用
- 同时管理前端和后端两个容器
- 配置容器之间的网络连接
- 配置端口映射、数据卷、环境变量等
- 一个命令启动所有服务

#### 文件内容详解

```yaml
# 第1行：版本号
version: '3.8'
# ↓ 说明：
#   指定 docker-compose 文件的格式版本
#   3.8 是一个稳定版本，支持大部分功能

# 第3行：服务定义
services:
  # ↓ 说明：
  #   下面定义两个服务：backend 和 frontend

  ========== 后端服务配置 ==========
  # 第4行：服务名称
  backend:
    #   这是我们给后端服务起的名字

    # 第6行：构建配置
    build: .
    # ↓ 说明：
    #   . 表示使用当前目录的 Dockerfile 构建镜像
    #   相当于执行：docker build -t requirement-backend .

    # 第7行：容器名称
    container_name: requirement-backend
    # ↓ 说明：
    #   给容器起个固定名字，方便管理
    #   如果不指定，Docker会自动生成名字

    # 第8-9行：端口映射
    ports:
      - "443:443"
    # ↓ 说明：
    #   主机端口:容器端口
    #   访问主机的443端口 → 转发到容器的443端口
    #   格式： "外部端口:内部端口"

    # 第10-14行：数据卷（目录映射）
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./uploads:/app/uploads
      - ./backend/config:/app/backend/config
    # ↓ 说明：
    #   主机目录:容器目录
    #   把主机的目录映射到容器内
    #   好处：容器删除后数据还在主机上
    #   ./data:/app/data 表示：
    #     主机的 data/ 目录 → 容器的 /app/data 目录

    # 第15-16行：环境变量
    environment:
      - PYTHONUNBUFFERED=1
    # ↓ 说明：
    #   设置容器内的环境变量
    #   PYTHONUNBUFFERED=1：Python输出不缓冲（立即显示日志）

    # 第17行：重启策略
    restart: unless-stopped
    # ↓ 说明：
    #   除非手动停止，否则总是重启
    #   其他选项：
    #     no：不自动重启
    #     always：总是重启
    #     on-failure：失败时重启

    # 第18-19行：网络配置
    networks:
      - app-network
    # ↓ 说明：
    #   连接到 app-network 网络
    #   同一网络的容器可以互相访问

    # 第20-24行：健康检查
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:443/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    # ↓ 说明：
    #   每30秒检查一次服务是否健康
    #   超时10秒，重试3次
    #   如果失败，Docker会重启容器

  ========== 前端服务配置 ==========
  # 第26行：前端服务
  frontend:
    # 第28行：使用官方Nginx镜像
    image: nginx:alpine
    # ↓ 说明：
    #   不需要构建，直接使用现成的 Nginx 镜像
    #   alpine 是超轻量级 Linux 发行版

    # 第29行：容器名称
    container_name: requirement-frontend

    # 第30-31行：端口映射
    ports:
      - "80:80"
    # ↓ 说明：
    #   主机的80端口 → 容器的80端口
    #   用户通过 http://IP 访问前端

    # 第32-34行：数据卷
    volumes:
      - ./frontend/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./frontend/build:/usr/share/nginx/html:ro
    # ↓ 说明：
    #   nginx.conf:ro → 只读方式挂载配置文件
    #   build:ro → 只读方式挂载前端静态文件
    #   ro 表示 read-only（只读），提高安全性

    # 第35-36行：依赖关系
    depends_on:
      - backend
    # ↓ 说明：
    #   前端依赖后端，先启动后端再启动前端
    #   注意：只影响启动顺序，不等待后端完全就绪

    # 第37-38行：重启策略
    restart: unless-stopped

    # 第38-39行：网络配置
    networks:
      - app-network

========== 网络定义 ==========
# 第41-43行：网络定义
networks:
  app-network:
    driver: bridge
    # ↓ 说明：
    #   创建一个桥接网络
    #   类似于一个虚拟交换机
    #   连接的容器可以互相通过服务名访问
```

#### 容器间通信

```
用户浏览器 → http://服务器IP:80
            ↓
    [frontend容器] Nginx
            ↓ 检测到 /api/ 开头的请求
            ↓ proxy_pass http://backend:443
            ↓
    [backend容器] FastAPI
            ↓
    返回JSON数据
```

**关键点**：
- 前端容器通过 `backend:443` 访问后端
- `backend` 是 docker-compose.yml 中定义的服务名
- 不需要知道后端的实际IP，Docker内部DNS自动解析

#### 如何修改？

**场景A：修改端口**
```yaml
# 如果主机的80端口被占用，改成8080
ports:
  - "8080:80"  # 访问时用 http://IP:8080
```

**场景B：增加环境变量**
```yaml
environment:
  - PYTHONUNBUFFERED=1
  - DASHSCOPE_API_KEY=${DASHSCOPE_API_KEY}  # 从.env文件读取
  - TZ=Asia/Shanghai  # 设置时区
```

**场景C：限制资源使用**
```yaml
deploy:
  resources:
    limits:
      memory: 1G      # 最多使用1G内存
      cpus: '0.5'     # 最多使用50%CPU
```

---

### 2.3 pyproject.toml - 项目配置和依赖声明

> **📌 重要说明（2026-01-07）**
> 本项目已从 `requirements.txt` 迁移到现代化的 `pyproject.toml + uv.lock` 依赖管理方式。
> 这是 Python 官方推荐的标准（PEP 518/621），提供更好的依赖管理和可重现构建。

#### 是什么？
`pyproject.toml` 是一个 TOML 格式的配置文件，用于定义项目的元信息和依赖关系。

#### 作用
- **项目信息**：名称、版本、作者、描述等元数据
- **依赖声明**：列出项目所需的 Python 包
- **依赖分组**：区分生产依赖、开发依赖、测试依赖
- **构建配置**：指定构建工具和后端
- **符合标准**：Python 官方标准（PEP 518/621）

#### 为什么需要 pyproject.toml？

**对比 requirements.txt**：

| 特性 | requirements.txt | pyproject.toml |
|------|------------------|----------------|
| 项目信息 | ❌ 无 | ✅ 有（名称、版本、作者） |
| 依赖分组 | ❌ 需要多文件 | ✅ 支持分组（dev/prod/test） |
| 标准规范 | ❌ 约定俗成 | ✅ PEP 518/621 |
| 依赖锁定 | ⚠️ 部分（仅顶层） | ⚠️ 部分（配合 uv.lock） |
| 构建配置 | ❌ 无 | ✅ 支持 |

#### 文件内容详解

**pyproject.toml 结构**：

```toml
========== 项目元信息 ==========
[project]
name = "requirement-estimation-system"
version = "1.0.0"
description = "业务需求工作量评估系统"
readme = "README.md"
requires-python = ">=3.10"
license = {text = "MIT"}
authors = [
    {name = "Your Name", email = "your.email@example.com"}
]
# ↓ 说明：
#   name：项目名称（唯一标识符）
#   version：当前版本号
#   description：项目简短描述
#   requires-python：最低 Python 版本要求
#   authors：项目作者信息

========== 依赖声明 ==========
dependencies = [
    # Web 框架
    "fastapi>=0.104.1",
    "uvicorn[standard]>=0.24.0",
    "python-multipart>=0.0.6",

    # 数据验证
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",

    # 文档处理
    "python-docx>=1.1.0",
    "openpyxl>=3.1.2",

    # AI 相关
    "langchain>=0.1.0",
    "langchain-openai>=0.0.2",
    "langgraph>=0.0.26",
    "dashscope>=1.14.0",
]
# ↓ 说明：
#   dependencies：生产环境必需的依赖
#   使用 >= 而不是 ==，允许小版本更新
#   实际安装的版本由 uv.lock 锁定

========== 依赖分组 ==========
[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "black>=23.0.0",
    "flake8>=6.0.0",
]
# ↓ 说明：
#   dev：开发环境依赖（测试、格式化、检查）
#   安装方式：uv sync --all 或 uv sync --extra dev

========== 开发依赖分组（新格式）==========
[dependency-groups]
dev = [
    "pytest>=7.0.0",
    "black>=23.0.0",
]
# ↓ 说明：
#   dependency-groups：uv 的新格式（推荐使用）
#   替代已弃用的 [tool.uv.dev-dependencies]

========== 构建系统配置 ==========
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"
# ↓ 说明：
#   指定构建项目所需的工具
#   setuptools：传统的构建工具
#   也可使用其他工具如 flit、poetry、hatch

========== 项目URL==========
[project.urls]
Homepage = "http://172.18.121.196"
Documentation = "https://github.com/your-username/requirement-estimation-system"
# ↓ 说明：
#   项目的相关链接
#   Homepage、Repository、Documentation 等

========== UV 工具配置 ==========
[tool.uv.sources]
# 配置特定包的安装源（可选）
# 例如：
# fastapi = { url = "https://github.com/tiangolo/fastapi/archive/refs/tags/0.104.1.tar.gz" }
```

#### 如何使用？

**场景 A：本地开发**

```bash
# 1. 安装 uv（如果还没装）
pip install uv

# 2. 安装依赖（从 pyproject.toml 和 uv.lock）
uv sync

# 3. 安装 + 开发依赖
uv sync --all

# 4. 运行应用
uv run python backend/app.py
```

**场景 B：添加新依赖**

```bash
# 添加生产依赖
uv add pandas

# 添加开发依赖
uv add --dev pytest

# 自动更新 pyproject.toml 和 uv.lock
```

**场景 C：更新依赖**

```bash
# 更新所有依赖到最新版本
uv lock --upgrade

# 更新特定包
uv lock --upgrade-package fastapi

# 重新生成 uv.lock
uv lock
```

**场景 D：Docker 构建**

```dockerfile
# Dockerfile 自动使用 pyproject.toml 和 uv.lock
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
```

#### 版本号规则

**pyproject.toml 中的写法**：

```toml
# ✅ 推荐：灵活版本号（由 uv.lock 锁定实际版本）
"fastapi>=0.104.1"
"langchain>=0.1.0"

# ⚠️ 可接受：兼容版本号
"fastapi~=0.104.0"  # 只能是 0.104.x，不能是 0.105.0

# ❌ 不推荐：过于严格（失去灵活性）
"fastapi==0.104.1"
```

**为什么使用 >= 而不是 ==？**

```toml
# pyproject.toml 中使用 >=
"fastapi>=0.104.1"

# uv.lock 中锁定精确版本
[[package]]
name = "fastapi"
version = "0.104.1"  # 实际安装的版本
checksum = "sha256:..."  # 哈希验证
```

**好处**：
- ✅ pyproject.toml 灵活（允许小版本更新）
- ✅ uv.lock 严格（锁定精确版本）
- ✅ 兼顾灵活性和安全性

#### 如何修改？

**场景 A：修改项目信息**

```toml
[project]
name = "requirement-estimation-system"
version = "1.1.0"  # 修改版本号
description = "新的描述"  # 修改描述
```

**场景 B：添加新依赖**

```bash
# 方式 1：使用命令行（推荐）
uv add pandas

# 方式 2：手动编辑 pyproject.toml
vim pyproject.toml
# 添加 "pandas>=2.0.0" 到 dependencies
# 然后运行：uv lock
```

**场景 C：删除依赖**

```bash
# 使用命令行
uv remove pandas

# 自动更新 pyproject.toml 和 uv.lock
```

#### 常见问题

**Q1：pyproject.toml 和 requirements.txt 可以共存吗？**

**A**：可以！本项目保留 requirements.txt 用于兼容性。

```bash
# 从 pyproject.toml 导出 requirements.txt
uv pip compile pyproject.toml -o requirements.txt
```

**Q2：如何查看当前安装了哪些依赖？**

**A**：
```bash
# 查看所有依赖（包括子依赖）
uv pip list

# 查看依赖树
uv pip tree
```

**Q3：pyproject.toml 需要提交到 Git 吗？**

**A**：✅ **必须提交**！

```bash
git add pyproject.toml uv.lock
git commit -m "Update dependencies"
```

---

### 2.4 uv.lock - 依赖锁文件

#### 是什么？
`uv.lock` 是一个由 `uv` 工具自动生成的锁文件，记录了项目所有依赖包的精确版本和哈希值。

#### 作用
- **锁定版本**：记录每个包的精确版本号（包括子依赖）
- **哈希验证**：包含 SHA256 哈希值，防止依赖篡改
- **可重现构建**：确保所有环境安装的依赖完全一致
- **依赖树**：记录完整的依赖关系图
- **安全性**：防止中间人攻击和依赖混淆攻击

#### 为什么需要 uv.lock？

**场景 1：团队协作**

```bash
# 开发者 A（1月1日）
uv sync
# 安装：fastapi==0.104.1, starlette==0.27.0
git add uv.lock
git commit -m "Add lock file"

# 开发者 B（2月1日，即使过了一个月）
git pull
uv sync
# 安装：fastapi==0.104.1, starlette==0.27.0
# ✅ 版本完全一致！
```

**场景 2：生产部署**

```bash
# 没有锁文件
pip install -r requirements.txt
# 可能安装：fastapi==0.104.1, starlette==0.28.0（子依赖升级了！）
# ⚠️ 导致：生产环境行为不一致

# 有锁文件
uv sync --frozen
# 安装：fastapi==0.104.1, starlette==0.27.0
# ✅ 完全可重现
```

#### 文件内容详解

**uv.lock 结构（前30行示例）**：

```toml
version = 1           # uv.lock 文件格式版本
revision = 3          # 修订号
requires-python = ">=3.10"  # Python 版本要求

========== 包定义 ==========
[[package]]
name = "aiohappyeyeballs"
version = "2.6.1"
source = { registry = "https://pypi.org/simple" }
sdist = { url = "https://files.pythonhosted.org/packages/...", hash = "sha256:..." }
wheels = [
    { url = "https://files.pythonhosted.org/packages/...", hash = "sha256:..." },
]

[[package]]
name = "aiohttp"
version = "3.13.3"
source = { registry = "https://pypi.org/simple" }
dependencies = [
    { name = "aiohappyeyeballs" },
    { name = "aiosignal" },
    { name = "async-timeout", marker = "python_full_version < '3.11'" },
    { name = "attrs" },
    { name = "frozenlist" },
    { name = "multidict" },
    { name = "propcache" },
    { name = "yarl" },
]
# ↓ 说明：
#   name：包名
#   version：精确版本号
#   source：下载源（PyPI、Git、本地路径）
#   dependencies：依赖的其他包（包括子依赖）
#   hash：SHA256 哈希值（安全验证）
```

**本项目的 uv.lock**：

```bash
# 查看统计信息
grep "^\\[\\[package\\]\\]" uv.lock | wc -l
# 输出：91（本项目锁定了 91 个包）

# 查看文件大小
ls -lh uv.lock
# 输出：712KB（3090行）
```

#### uv.lock vs requirements.txt

| 特性 | requirements.txt | uv.lock |
|------|------------------|---------|
| **版本锁定** | 仅顶层依赖（11个） | 所有依赖（91个） |
| **子依赖锁定** | ❌ 不支持 | ✅ 支持 |
| **哈希验证** | ❌ 无 | ✅ SHA256 |
| **依赖树** | ❌ 无 | ✅ 完整记录 |
| **可重现构建** | ⚠️ 70% | ✅ 100% |
| **自动生成** | ❌ 手动维护 | ✅ 自动生成 |

#### 如何生成 uv.lock？

**方式 1：自动生成（推荐）**

```bash
# 从 pyproject.toml 生成
uv lock

# 或在安装时自动生成
uv sync
```

**方式 2：更新依赖后重新生成**

```bash
# 1. 修改 pyproject.toml
vim pyproject.toml

# 2. 更新 lock 文件
uv lock

# 3. 提交到 Git
git add pyproject.toml uv.lock
git commit -m "Update dependencies"
```

#### uv.lock 在 Docker 构建中的作用

**Dockerfile 中的使用**：

```dockerfile
# 1. 复制 pyproject.toml 和 uv.lock
COPY pyproject.toml uv.lock ./

# 2. 使用 uv sync 安装（从 lock 文件读取）
RUN uv sync --frozen --no-dev --index-url ${UV_INDEX_URL}
# ↓ 说明：
#   --frozen：严格按照 uv.lock 安装，不修改它
#   --no-dev：只安装生产依赖
#   如果 lock 文件和 pyproject.toml 不一致，构建会失败（安全）
```

**为什么使用 --frozen？**

```bash
# ❌ 不安全（生产环境）
RUN uv sync --no-dev
# 可能修改 uv.lock，导致生产环境依赖变化

# ✅ 安全（生产环境）
RUN uv sync --frozen --no-dev
# 严格按照 uv.lock 安装，不修改
# 如果不一致，构建失败，提醒开发者更新 lock 文件
```

#### 如何修改 uv.lock？

**⚠️ 重要：不要手动编辑 uv.lock！**

**正确的方式**：

```bash
# 1. 修改 pyproject.toml
vim pyproject.toml
# 添加或修改依赖

# 2. 更新 uv.lock
uv lock

# 3. 查看变化
git diff uv.lock

# 4. 提交两个文件
git add pyproject.toml uv.lock
git commit -m "Update fastapi to latest"
```

**场景 A：更新所有依赖到最新版本**

```bash
uv lock --upgrade
uv sync
```

**场景 B：更新特定包**

```bash
uv lock --upgrade-package fastapi
uv sync
```

**场景 C：解决依赖冲突**

```bash
# uv 会自动解决依赖冲突
uv lock

# 如果失败，查看详细信息
uv lock --verbose
```

#### uv.lock 必须提交到 Git！

**✅ 正确**：

```bash
git add pyproject.toml uv.lock
git commit -m "Add dependency lock file"
```

**❌ 错误**：

```bash
# 不要忽略 uv.lock！
echo "uv.lock" >> .gitignore  # ❌ 不要这样做
```

**原因**：
- uv.lock 是团队的"依赖版本快照"
- 每个成员都需要相同的依赖版本
- 忽略它会导致环境不一致

#### .dockerignore 配置

**正确的配置**：

```
# .dockerignore

# ✅ 忽略 uv 缓存目录
.uv/

# ❌ 不要忽略 uv.lock（需要复制到容器中）
# uv.lock  ← 不要添加这行！

# ✅ 保留 requirements.txt（兼容性）
requirements.txt
```

**检查 .dockerignore**：

```bash
# 确认 uv.lock 没有被忽略
cat .dockerignore | grep uv.lock

# 如果有输出，说明被忽略了（错误！）
# 需要删除这一行
```

#### 常见问题

**Q1：uv.lock 文件很大（712KB），需要提交到 Git 吗？**

**A**：✅ **必须提交**！虽然文件很大，但它是项目的重要组成部分。

**Q2：更新依赖后 Docker 构建失败？**

**A**：检查是否重新生成了 uv.lock

```bash
# 1. 更新依赖
uv lock

# 2. 提交到 Git
git add pyproject.toml uv.lock

# 3. 重新构建
docker build --no-cache -t requirement-backend .
```

**Q3：uv.lock 和 pyproject.toml 不一致怎么办？**

**A**：重新生成 lock 文件

```bash
# 方式 1：强制更新
uv lock --upgrade

# 方式 2：重新生成
rm uv.lock
uv lock

# 方式 3：检查不一致的包
uv lock --verbose
```

**Q4：如何回滚到旧版本的依赖？**

**A**：使用 Git 回滚

```bash
# 1. 查看历史版本
git log --oneline pyproject.toml uv.lock

# 2. 回滚到指定版本
git checkout <commit-hash> -- pyproject.toml uv.lock

# 3. 重新安装
uv sync --frozen
```

#### 性能优势

**对比 pip install**：

| 操作 | pip + requirements.txt | uv + lock | 提升 |
|------|----------------------|-----------|------|
| 安装 11 个顶层依赖 | ~30秒 | ~3秒 | **10倍** |
| 安装 91 个所有依赖 | ~150秒 | ~5秒 | **30倍** |
| 解析依赖关系 | ~10秒 | <1秒 | **即时** |
| 下载包 | 串行 | 并行 | **更快** |

**为什么这么快？**

1. **Rust 编写**：uv 用 Rust 编写，性能极高
2. **并行下载**：同时下载多个包
3. **锁文件**：无需重新解析依赖关系
4. **缓存机制**：智能缓存已下载的包

#### 安全性提升

**SHA256 哈希验证**：

```toml
[[package]]
name = "fastapi"
version = "0.104.1"
sdist = { url = "...", hash = "sha256:abc123..." }
# ↓ 说明：
#   hash：SHA256 哈希值
#   作用：验证包的完整性和真实性
#   防止：中间人攻击、依赖篡改
```

**安全保证**：

- ✅ **完整性**：包没有被修改
- ✅ **真实性**：包来自官方源
- ✅ **可追溯**：每个包都有哈希值
- ✅ **防篡改**：哈希不匹配会安装失败

---

### 2.5 requirements.txt - 已弃用（保留用于兼容）

#### 是什么？
`requirements.txt` 是一个文本文件，列出了项目所有Python依赖包及版本号。

#### 作用
- 告诉 pip 需要安装哪些包
- 固定版本号，确保环境一致
- 避免版本冲突

#### 文件内容详解

```
fastapi==0.104.1         # Web框架
uvicorn[standard]==0.24.0  # ASGI服务器（支持异步）
python-multipart==0.0.6  # 文件上传支持
python-docx==1.1.0       # Word文档处理
openpyxl==3.1.2          # Excel文件处理
langchain==0.1.0         # AI应用框架
langchain-openai==0.0.2  # LangChain的OpenAI集成
dashscope==1.14.0        # 通义千问SDK
pydantic==2.5.0          # 数据验证
pydantic-settings==2.1.0 # 配置管理
```

#### 版本号规则

| 写法 | 含义 | 示例 |
|------|------|------|
| `fastapi==0.104.1` | 精确版本 | 只能是0.104.1 |
| `fastapi>=0.104.0` | 大于等于 | 0.104.0或更高 |
| `fastapi~=0.104.0` | 兼容版本 | 0.104.x，但不包括0.105.0 |
| `fastapi` | 任意版本 | 总是安装最新版（不推荐） |

#### 如何生成？

**方法A：从现有环境生成**
```bash
# 在项目虚拟环境中执行
pip freeze > requirements.txt

# 或者只导出项目使用的包
pipreqs .  # 需要先安装：pip install pipreqs
```

**方法B：手动维护（推荐）**
```bash
# 创建文件
cat > requirements.txt << 'EOF'
fastapi==0.104.1
uvicorn[standard]==0.24.0
...
EOF
```

#### 如何更新依赖？

```bash
# 1. 安装新包
pip install pandas==2.0.0

# 2. 更新requirements.txt
pip freeze > requirements.txt

# 或者手动添加
echo "pandas==2.0.0" >> requirements.txt
```

---

### 2.5.1 防止依赖遗漏的最佳实践

> **⚠️ 说明（2026-01-07）**
> 本章节主要针对旧的 `requirements.txt` 方式。
>
> 使用 `pyproject.toml + uv.lock` 后，这些最佳实践已由 **uv** 自动处理：
> - ✅ 自动解析依赖树
> - ✅ 自动锁定所有依赖版本
> - ✅ 自动验证依赖完整性
> - ✅ 构建时自动检查依赖冲突
>
> 如果仍使用 `requirements.txt`，可参考本章节的防护机制。

> **为什么需要这个章节？**
>
> 在 Docker 构建过程中，如果 `requirements.txt` 遗漏了依赖包，会导致容器启动失败。
> 典型错误：`ModuleNotFoundError: No module named 'langgraph'`
>
> 本章节提供多层防护机制，确保依赖完整。

#### 实践一：Dockerfile 构建时检查（已实现✅）

在 Dockerfile 中添加依赖验证步骤，构建时自动检查：

```dockerfile
# 复制项目文件
COPY . .

# 创建必要的目录
RUN mkdir -p logs data uploads

# 验证Python依赖是否完整（构建时检查）
RUN python3 -c "import sys; sys.path.insert(0, '.'); import backend.app" || (echo "依赖检查失败，请检查pyproject.toml" && exit 1)
```

**优点**：
- 构建时立即发现依赖问题
- 避免部署到生产环境才发现错误
- 失败即停止，不会留下损坏的镜像

**工作原理**：
- 尝试导入主应用模块 `backend.app`
- 如果缺少依赖，导入失败，构建终止
- 显示明确的错误提示

---

#### 实践二：自动化依赖检查脚本

项目已提供 `check_dependencies.sh` 脚本：

```bash
#!/bin/bash

echo "🔍 检查 Python 依赖..."

# 方法1: 尝试导入所有模块
python3 -c "
import sys
sys.path.insert(0, '.')

try:
    import backend.app
    print('✅ 主应用依赖检查通过')
except ImportError as e:
    print(f'❌ 依赖缺失: {e}')
    sys.exit(1)

# 检查关键模块
modules = [
    'fastapi',
    'uvicorn',
    'langchain',
    'langgraph',
    'dashscope',
    'pydantic'
]

missing = []
for module in modules:
    try:
        __import__(module)
        print(f'✅ {module}')
    except ImportError:
        missing.append(module)
        print(f'❌ {module}')

if missing:
    print(f'\n❌ 缺失依赖: {missing}')
    print('请运行: pip install -r requirements.txt')
    sys.exit(1)

print('\n✅ 所有依赖检查通过！')
"
```

**使用方法**：

```bash
# 本地开发时检查
./check_dependencies.sh

# Docker构建前检查
docker build -t requirement-backend . 2>&1 | grep -i "依赖"
```

---

#### 实践三：使用 Makefile 标准化流程

项目已提供 `Makefile`，自动执行依赖检查：

```makefile
.PHONY: help build test check-deps deploy

help: ## 显示帮助信息
	@echo "可用命令:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

check-deps: ## 检查依赖是否完整
	@echo "🔍 检查依赖..."
	@./check_dependencies.sh

build: check-deps ## 检查依赖后构建镜像
	@echo "🔨 构建Docker镜像..."
	docker build -t requirement-estimation-system-backend .

test: check-deps ## 运行测试（含依赖检查）
	@echo "🧪 运行测试..."
	# docker-compose run --rm backend pytest

deploy: build ## 部署（构建并启动）
	@echo "🚀 部署服务..."
	docker-compose up -d backend
	@echo "✅ 部署完成"

update-requirements: ## 使用pipreqs更新requirements.txt
	@echo "📦 扫描代码更新依赖..."
	pipreqs . --force --savepath requirements.txt
	@echo "✅ requirements.txt 已更新"
```

**推荐工作流程**：

```bash
# 开发流程：
写代码 → make check-deps → make build → make deploy

# 日常使用：
make help           # 查看所有命令
make check-deps     # 本地检查依赖
make build          # 构建镜像（自动检查）
make deploy         # 部署（包含检查+构建）
```

---

#### 实践四：使用工具自动扫描依赖

> **⚠️ 重要提示**：如果 pip 安装的工具（pipreqs、pigar 等）不在系统 PATH 中，你需要：
> 1. 使用完整路径：`/usr/local/python310/bin/pipreqs`
> 2. 或者创建软链接：`sudo ln -s /usr/local/python310/bin/pipreqs /usr/local/bin/pipreqs`
> 3. 或者添加到 PATH：`export PATH="/usr/local/python310/bin:$PATH"`

**工具A：pipreqs - 扫描代码生成依赖**

```bash
# 安装
pip install pipreqs

# 扫描项目代码
pipreqs /home/admin/Claude/requirement-estimation-system --force --savepath requirements.txt

# 优点：
# - 只包含代码实际使用的包（不像 pip freeze 包含所有依赖）
# - 自动分析 import 语句
# - 可以发现遗漏的依赖
```

**工具B：pigar - 更精确的依赖检测**

```bash
# 安装
pip install pigar

# 扫描项目并生成依赖文件（推荐）
pigar generate . -f requirements_pigar.txt --with-referenced-comments --auto-select

# 只预览结果，不生成文件
pigar generate . --dry-run --with-referenced-comments --auto-select

# 使用灵活版本号（>=）而不是精确版本（==）
pigar generate . -f requirements.txt -c ">=" --auto-select

# 参数说明：
# generate                  : 生成依赖文件子命令
# .                         : 扫描当前目录
# -f FILE                   : 输出文件名
# --with-referenced-comments: 显示每个包被哪些文件引用
# --auto-select             : 自动选择最佳匹配，无需手动确认
# -c ">="                   : 使用 >= 版本标识符（默认是 ==）
# --dry-run                 : 只预览，不实际写入文件

# 优点：
# - 显示每个包在哪些文件中被使用（带注释）
# - 自动检测代码实际使用的依赖
# - 可以识别未使用的依赖
# - 支持多种版本标识符（==、>=、~=、-）
```

**工具C：pip-check - 检查依赖冲突**

```bash
# 安装
pip install pip-check

# 检查当前环境
pip-check

# 输出示例：
# fastapi 0.104.1 requires starlette<0.28.0,>=0.27.0, but you have starlette 0.28.0
```

---

#### 实践五：版本号规范（避免依赖冲突）

**推荐版本写法**：

```txt
# ✅ 推荐：灵活版本号（允许自动解决依赖冲突）
langchain>=0.1.0
langchain-openai>=0.0.2
langgraph>=0.0.26

# ❌ 避免：过于严格的版本号（容易导致冲突）
langchain==0.1.0
langchain-openai==0.0.2
langgraph==0.0.26

# ⚠️ 谨慎使用：兼容版本号
langchain~=0.1.0  # 只能是 0.1.x，不能是 0.2.0
```

**版本符号说明**：

| 符号 | 含义 | 示例 | 优点 | 缺点 |
|------|------|------|------|------|
| `==` | 精确版本 | `==0.1.0` | 完全确定 | 易冲突 |
| `>=` | 大于等于 | `>=0.1.0` | 灵活，自动兼容 | 可能有大版本变化 |
| `~=` | 兼容版本 | `~=0.1.0` | 平衡 | 仍可能冲突 |
| `*` | 通配符 | `0.1.*` | 灵活 | 不推荐使用 |

**实际案例（我们的项目）**：

```txt
# ❌ 原来的写法（导致依赖冲突）
langchain==0.1.0
langchain-openai==0.0.2
langgraph==0.0.26

# ✅ 修改后（pip自动解决兼容性）
langchain>=0.1.0
langchain-openai>=0.0.2
langgraph>=0.0.26
```

---

#### 实践六：CI/CD 自动检查（生产环境）

**在 .gitlab-ci.yml 或 GitHub Actions 中添加**：

```yaml
# 示例：GitLab CI
test:
  stage: test
  image: python:3.10-slim
  script:
    - pip install -r requirements.txt
    - python3 -c "import backend.app; print('依赖检查通过')"
    - ./check_dependencies.sh

build:
  stage: build
  script:
    - docker build -t requirement-backend .
  only:
    - main
```

**效果**：
- 每次提交代码自动检查依赖
- 构建失败阻止合并
- 防止有问题的代码进入生产环境

---

#### 实践七：开发规范（团队协作）

**规范A：依赖变更流程**

```
1. 添加新依赖
   ↓
2. 本地测试：pip install xxx
   ↓
3. 更新 requirements.txt
   ↓
4. 运行检查：./check_dependencies.sh
   ↓
5. 构建测试：make build
   ↓
6. 提交代码：git add requirements.txt
   ↓
7. 代码审查：检查依赖是否必要
   ↓
8. 合并发布
```

**规范B：Code Review 清单**

```markdown
## 依赖检查清单

- [ ] 新依赖是否必要？（能否用现有依赖替代）
- [ ] 版本号是否合理？（使用 >= 还是 ==）
- [ ] 是否通过 ./check_dependencies.sh 检查？
- [ ] 是否通过 make build 测试？
- [ ] 是否更新了文档？
```

---

#### 总结：多层防护体系

| 防护层 | 工具/方法 | 触发时机 | 作用 |
|--------|----------|----------|------|
| **第一层** | check_dependencies.sh | 本地开发 | 快速发现问题 |
| **第二层** | Makefile check-deps | 构建前 | 自动化检查 |
| **第三层** | Dockerfile 验证 | 构建时 | 失败即停止 |
| **第四层** | pipreqs 扫描 | 代码变更 | 自动发现遗漏 |
| **第五层** | CI/CD 检查 | 提交时 | 团队协作保障 |

**推荐工作流**：

```bash
# 个人开发
vim backend/app.py  # 添加新功能
pip install new-package  # 安装新依赖
vim requirements.txt  # 更新依赖
make check-deps  # 检查依赖
make build  # 构建镜像
make deploy  # 部署

# 团队协作
git add .
git commit -m "feat: 添加xxx功能"
git push
# → CI/CD 自动检查依赖
# → 检查通过才能合并
```

**遇到依赖问题时的排查步骤**：

```bash
# 1. 查看容器日志
docker logs requirement-backend

# 2. 本地验证
./check_dependencies.sh

# 3. 重新生成依赖
pipreqs . --force --savepath requirements.txt

# 4. 清理缓存重新构建
docker system prune -a
make build
```

---

---

### 2.6 frontend/nginx.conf - Nginx配置文件

#### 是什么？
`nginx.conf` 是 Nginx 服务器的配置文件。

#### 作用
- 配置 Web 服务器如何处理 HTTP 请求
- 托管前端静态文件（HTML/CSS/JS）
- 反向代理后端 API 请求

#### 文件内容详解

```nginx
========== 事件驱动配置 ==========
events {
    worker_connections 1024;
    # ↓ 说明：
    #   每个 Nginx 进程最多处理1024个连接
    #   对于小型应用足够了
}

========== HTTP配置 ==========
http {
    # 第6-7行：MIME类型
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    # ↓ 说明：
    #   加载MIME类型定义
    #   告诉浏览器文件类型（如.html .css .js）

    ========== 服务器配置 ==========
    server {
        # 第10行：监听端口
        listen 80;
        # ↓ 说明：
        #   监听80端口（HTTP）

        # 第11行：服务器名称
        server_name _;
        # ↓ 说明：
        #   _ 表示匹配所有域名
        #   如果有域名，可以写成：server_name example.com;

        ========== 前端静态文件 ==========
        # 第13-24行：静态文件托管
        location / {
            root /usr/share/nginx/html;
            # ↓ 说明：
            #   静态文件存放目录
            #   对应 docker-compose.yml 中的：
            #   ./frontend/build:/usr/share/nginx/html

            try_files $uri $uri/ /index.html;
            # ↓ 说明：
            #   按顺序尝试：
            #   1. $uri：请求的文件（如 /about.html）
            #   2. $uri/：请求的目录（如 /about/）
            #   3. /index.html：回退到首页（支持前端路由）

            index index.html;
            # ↓ 说明：
            #   默认首页文件

            # 第19-23行：静态资源缓存
            location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
                expires 1y;
                add_header Cache-Control "public, immutable";
                # ↓ 说明：
                #   静态资源缓存1年
                #   提升访问速度，减少服务器压力
            }
        }

        ========== 后端API代理 ==========
        # 第26-37行：API反向代理
        location /api/ {
            proxy_pass http://backend:443;
            # ↓ 说明：
            #   把 /api/ 开头的请求转发到后端
            #   backend 是 docker-compose.yml 中的服务名
            #   示例：
            #     浏览器请求：http://IP/api/v1/health
            #     Nginx转发到：http://backend:443/api/v1/health

            # 第29-32行：传递请求头
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            # ↓ 说明：
            #   把原始请求信息传递给后端
            #   后端可以获取真实IP、协议等信息

            # 第34-36行：超时设置
            proxy_read_timeout 300s;
            proxy_connect_timeout 300s;
            # ↓ 说明：
            #   因为AI分析任务耗时长，设置5分钟超时
            #   避免任务未完成就超时断开
        }
    }
}
```

#### 请求流程示例

**用户访问前端页面：**
```
浏览器：http://192.168.1.100/
  ↓
Nginx：找到 /usr/share/nginx/html/index.html
  ↓
返回：HTML页面
```

**用户访问后端API：**
```
浏览器：http://192.168.1.100/api/v1/estimate
  ↓
Nginx：检测到 /api/ 开头
  ↓
Nginx：proxy_pass http://backend:443/api/v1/estimate
  ↓
后端容器：处理请求
  ↓
返回：JSON数据
```

#### 如何修改？

**场景A：修改缓存策略**
```nginx
# 如果不希望缓存（开发调试）
location ~* \.(js|css)$ {
    expires off;
    add_header Cache-Control "no-cache";
}
```

**场景B：增加跨域支持**
```nginx
location /api/ {
    # ... 其他配置 ...
    add_header Access-Control-Allow-Origin *;
    add_header Access-Control-Allow-Methods "GET, POST, OPTIONS";
}
```

**场景C：配置HTTPS（如果有SSL证书）**
```nginx
server {
    listen 443 ssl;
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    # ...
}
```

---

### 2.7 deploy.sh - 一键部署脚本

#### 是什么？
`deploy.sh` 是一个 Bash 脚本，自动化执行部署流程。

#### 作用
- 自动检查环境（Docker、Docker Compose）
- 自动构建前端（npm install + npm run build）
- 自动构建Docker镜像
- 自动启动服务
- 减少人工操作错误

#### 脚本内容详解

```bash
#!/bin/bash
# ↓ 说明：
#   Shebang：指定用bash解释器执行

# 第2行：注释
# 部署脚本 - 一键部署到Docker环境

# 第4行：错误处理
set -e
# ↓ 说明：
#   任何命令执行失败就退出脚本
#   避免继续执行导致更多错误

========== 检查环境 ==========
# 第11-19行：检查Docker
if ! command -v docker &> /dev/null; then
    echo "错误: Docker未安装，请先安装Docker"
    exit 1
fi
# ↓ 说明：
#   command -v docker：检查docker命令是否存在
#   &> /dev/null：丢弃输出
#   !：取反，如果不存在则执行if内的代码
#   exit 1：退出并返回错误码1

# 第16-19行：检查Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "错误: Docker Compose未安装，请先安装Docker Compose"
    exit 1
fi

========== 执行部署 ==========
# 第21-27行：构建前端
echo ""
echo "[步骤 1/4] 构建前端..."
cd frontend
npm install
npm run build
cd ..
# ↓ 说明：
#   进入 frontend 目录
#   安装依赖
#   构建生产版本
#   返回项目根目录

# 第29-32行：构建Docker镜像
echo ""
echo "[步骤 2/4] 构建Docker镜像..."
docker build -t requirement-backend .
# ↓ 说明：
#   -t requirement-backend：给镜像起名
#   .：使用当前目录的Dockerfile

# 第34-37行：启动服务
echo ""
echo "[步骤 3/4] 启动服务..."
docker-compose up -d
# ↓ 说明：
#   up：启动服务
#   -d：后台运行（detached模式）

# 第39-43行：检查状态
echo ""
echo "[步骤 4/4] 检查服务状态..."
sleep 5
docker-compose ps
# ↓ 说明：
#   sleep 5：等待5秒让服务启动
#   docker-compose ps：查看容器状态

========== 输出提示 ==========
# 第45-57行：显示完成信息
echo ""
echo "========================================="
echo "部署完成！"
echo "========================================="
# ... 输出访问地址、查看日志的命令等
```

#### 为什么用脚本？

**不用脚本的问题：**
- 每次部署要手动执行多条命令
- 容易遗漏步骤
- 容易出错（如忘记 cd 回来）

**用脚本的好处：**
- 一条命令完成部署
- 步骤固定，不会遗漏
- 有错误提示
- 可以重复执行

#### 执行流程图

```
./deploy.sh
    ↓
[步骤1] 检查Docker ✓
    ↓
[步骤2] 构建前端
    ├─ npm install（安装依赖）
    └─ npm run build（打包）
    ↓
[步骤3] 构建Docker镜像
    └─ 根据 Dockerfile 构建后端镜像
    ↓
[步骤4] 启动容器
    └─ docker-compose up -d
    ↓
[步骤5] 检查状态
    ├─ 等待5秒
    └─ 显示容器状态
    ↓
完成 ✓
```

#### 如何修改？

**场景A：需要清理旧容器**
```bash
# 在 docker-compose up -d 之前添加
docker-compose down  # 停止并删除旧容器
```

**场景B：需要备份数据**
```bash
# 在构建之前添加
echo "备份旧数据..."
cp -r data data.backup.$(date +%Y%m%d)
```

**场景C：需要配置环境变量**
```bash
# 在启动之前检查 .env 文件
if [ ! -f .env ]; then
    echo "错误：.env 文件不存在"
    exit 1
fi
```

---

### 2.8 package.sh - 打包脚本（开发环境）

#### 是什么？
`package.sh` 是在开发环境使用的脚本，只打包不运行。

#### 与 deploy.sh 的区别

| 特性 | package.sh | deploy.sh |
|------|-----------|-----------|
| 使用场景 | 开发服务器 | 生产服务器 |
| 是否启动服务 | 否 | 是 |
| 输出结果 | tar.gz打包文件 | 运行中的容器 |
| 是否需要Docker | 是（构建镜像） | 是（运行容器） |
| 执行位置 | 开发环境 | 目标环境 |

#### 脚本内容详解

```bash
#!/bin/bash
# 打包脚本 - 开发环境使用，构建前端+Docker镜像

set -e

echo "========================================="
echo "需求评估系统 - 打包脚本"
echo "========================================="

# 1. 构建前端
echo ""
echo "[步骤 1/3] 构建前端..."
cd frontend
npm install
npm run build
cd ..

# 2. 构建Docker镜像
echo ""
echo "[步骤 2/3] 构建Docker镜像..."
docker build -t requirement-backend .

# 3. 打包项目
echo ""
echo "[步骤 3/3] 打包项目..."
cd ..
tar czf requirement-system-$(date +%Y%m%d-%H%M%S).tar.gz requirement-estimation-system/

echo ""
echo "========================================="
echo "打包完成！"
echo "========================================="
ls -lh requirement-system-*.tar.gz
```

---

### 2.9 .env - 环境变量配置（可选但推荐）

#### 是什么？
`.env` 是一个隐藏文件，存储环境变量和敏感配置。

#### 作用
- 存储API密钥、数据库密码等敏感信息
- 不同环境使用不同配置（开发/测试/生产）
- 不把敏感信息提交到Git

#### 文件示例

```bash
# 通义千问API Key
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxx

# 服务配置
HOST=0.0.0.0
PORT=443
DEBUG=false
WORKERS=4

# 文件路径
UPLOAD_DIR=uploads
REPORT_DIR=data

# 时区
TZ=Asia/Shanghai
```

#### 使用方式

**在 docker-compose.yml 中引用：**
```yaml
services:
  backend:
    environment:
      - DASHSCOPE_API_KEY=${DASHSCOPE_API_KEY}
      - TZ=${TZ}
```

**在 Python 代码中读取：**
```python
import os
api_key = os.getenv("DASHSCOPE_API_KEY")
```

---

## 📦 第三章：准备工作清单

### 3.1 确认开发环境（当前环境）

在当前服务器执行以下命令，确认环境就绪：

```bash
# 1. 检查项目目录
cd /home/admin/Claude/requirement-estimation-system
ls -la

# 应该看到：
# backend/  - 后端代码
# frontend/ - 前端代码
# system_list.csv - 主系统配置
# ... 等文件
```

```bash
# 2. 检查Docker是否安装
docker --version

# 如果显示版本号（例如：Docker version 20.10.7）✓ 已安装
# 如果提示"command not found"✗ 需要安装
```

```bash
# 3. 检查Docker Compose是否安装
docker-compose --version

# 如果显示版本号✓ 已安装
# 如果提示"command not found"✗ 需要安装
```

**如果Docker没安装，按照下面的步骤安装**：

```bash
# CentOS/RHEL系统
sudo yum install -y docker
sudo systemctl start docker
sudo systemctl enable docker

# 安装Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 验证安装
docker --version
docker-compose --version
```

### 3.2 确认项目文件完整

```bash
cd /home/admin/Claude/requirement-estimation-system

# 检查关键文件是否存在
ls -l Dockerfile
ls -l docker-compose.yml
ls -l deploy.sh
ls -l requirements.txt
ls -l frontend/nginx.conf

# 如果都存在✓ 准备工作完成
# 如果有文件缺失✗ 需要创建（下面会讲到怎么创建）
```

---

## 🚀 第四章：在开发环境打包项目

### 4.1 打包脚本说明

项目中有两个部署脚本，用途不同：

#### package.sh - 打包脚本（开发环境使用）
- **用途**：只构建前端和Docker镜像，不启动服务
- **场景**：在开发环境打包，准备传输到其他服务器
- **执行位置**：开发服务器
- **输出**：生成tar.gz打包文件
- **已优化**：
  - 使用 `docker build` 避免 buildx 版本限制
  - Dockerfile 使用腾讯云 pip 镜像源，确保依赖安装成功

```bash
cd /home/admin/Claude/requirement-estimation-system
chmod +x package.sh
./package.sh
```

#### deploy.sh - 部署脚本（目标环境使用）
- **用途**：构建并启动Docker容器
- **场景**：在目标服务器部署运行
- **执行位置**：目标服务器
- **输出**：运行中的服务
- **已优化**：
  - 使用 `docker build` 避免 buildx 版本限制
  - Dockerfile 使用腾讯云 pip 镜像源，确保依赖安装成功

```bash
cd /opt/requirement-estimation-system
chmod +x deploy.sh
./deploy.sh
```

### 4.2 使用打包脚本（推荐）

```bash
cd /home/admin/Claude/requirement-estimation-system

# 执行打包脚本
./package.sh

# 你会看到：
# [步骤 1/3] 构建前端...
# [步骤 2/3] 构建Docker镜像...
# [步骤 3/3] 打包项目...
#
# 打包完成: requirement-system-20260105-180000.tar.gz
# 文件大小: 50M
```

### 4.3 手动打包（可选方式）

**方式A：打包成tar.gz文件（推荐）**

```bash
# 1. 回到项目根目录
cd /home/admin/Claude

# 2. 打包项目
tar czf requirement-system-$(date +%Y%m%d-%H%M%S).tar.gz requirement-estimation-system/

# 3. 查看打包文件
ls -lh requirement-system-*.tar.gz

# 你会看到类似：
# -rw-r--r-- 1 root root 50M Jan  5 18:00 requirement-system-20260105-180000.tar.gz
# ↑ 这就是你的项目包，50M左右
```

**方式B：使用rsync同步（适合频繁更新）**

```bash
# 同步到目标服务器
rsync -avz --exclude 'node_modules' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude 'data/' \
    --exclude 'logs/' \
    requirement-estimation-system/ \
    root@192.168.1.100:/opt/requirement-estimation-system/

# 注意：把192.168.1.100改成你目标服务器的IP地址
```

### 4.4 创建requirements.txt（如果不存在）

```bash
cd /home/admin/Claude/requirement-estimation-system

# 创建依赖文件
cat > requirements.txt << 'EOF'
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6
python-docx==1.1.0
openpyxl==3.1.2
langchain==0.1.0
langchain-openai==0.0.2
dashscope==1.14.0
pydantic==2.5.0
pydantic-settings==2.1.0
EOF

# 验证
cat requirements.txt
```

---

## 📡 第五章：传输到目标服务器

### 5.1 确认目标服务器能访问

```bash
# 从开发服务器测试连通性
ping 192.168.1.100

# 如果能ping通✓ 可以继续
# 如果不通✗ 检查网络或IP地址
```

### 5.2 传输打包文件

**方式A：使用scp传输（推荐）**

```bash
# 在开发服务器执行
cd /home/admin/Claude

# 传输文件到目标服务器
scp requirement-system-20260105-180000.tar.gz root@192.168.1.100:/tmp/

# 会提示输入密码，输入目标服务器的root密码

# 查看传输进度
# 文件大时会显示进度条
```

**方式B：使用rsync传输**

```bash
# 优势：支持断点续传
rsync -avz --progress \
    requirement-system-20260105-180000.tar.gz \
    root@192.168.1.100:/tmp/

# 传输完成后会显示统计信息
```

### 5.3 传输完成后验证

```bash
# 在目标服务器上检查文件
ssh root@192.168.1.100

# 登录后执行：
ls -lh /tmp/requirement-system-*.tar.gz

# 应该能看到你传输的文件
```

---

## 🛠️ 第六章：在目标服务器部署

### 6.1 登录目标服务器并准备

```bash
# SSH登录目标服务器
ssh root@192.168.1.100

# 进入临时目录
cd /tmp

# 解压项目文件
tar xzf requirement-system-20260105-180000.tar.gz

# 移动到工作目录
mv requirement-estimation-system /opt/
cd /opt/requirement-estimation-system

# 查看项目结构
ls -la

# 应该看到：
# backend/
# frontend/
# Dockerfile
# docker-compose.yml
# 等文件
```

### 6.2 安装Docker（目标服务器）

```bash
# 1. 检查系统版本
cat /etc/redhat-release

# 2. 安装Docker
sudo yum install -y docker

# 3. 启动Docker服务
sudo systemctl start docker
sudo systemctl enable docker

# 4. 验证安装
docker --version

# 5. 安装Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 6. 验证安装
docker-compose --version
```

### 6.3 配置环境变量

```bash
cd /opt/requirement-estimation-system

# 创建.env文件
cat > .env << 'EOF'
# 通义千问API Key（必须填写真实的）
DASHSCOPE_API_KEY=你的API-Key填在这里

# 服务配置
HOST=0.0.0.0
PORT=443
DEBUG=false
WORKERS=4

# 文件路径
UPLOAD_DIR=uploads
REPORT_DIR=data
EOF

# 编辑API Key
vim .env

# 在vim中：
# 1. 按 i 进入编辑模式
# 2. 修改"你的API-Key填在这里"为真实Key
# 3. 按 Esc 退出编辑
# 4. 输入 :wq 保存并退出
```

### 6.4 一键部署

```bash
# 1. 添加执行权限
chmod +x deploy.sh

# 2. 执行部署
./deploy.sh

# 你会看到大量输出，包括：
# - 前端构建过程（npm install）
# - Docker镜像构建
# - 容器启动
```

### 6.5 验证部署成功

```bash
# 1. 检查容器状态
docker-compose ps

# 正常输出应该显示：
# NAME                      STATUS    PORTS
# requirement-backend       Up        0.0.0.0:443->443/tcp
# requirement-frontend      Up        0.0.0.0:80->80/tcp

# 2. 检查后端健康接口
curl http://localhost/api/v1/health

# 正常输出：
# {"status":"healthy","service":"业务需求工作量评估系统",...}

# 3. 打开浏览器访问
# http://192.168.1.100  （替换成你的服务器IP）

# 如果能看到页面✓ 部署成功！
```

---

## ⚠️ 第七章：常见问题及解决方案

### 7.1 端口被占用

**问题**：
```
Error: port 443 is already in use
```

**解决方案**：

```bash
# 1. 查看端口占用
sudo lsof -i :443
sudo lsof -i :80

# 2. 如果显示有进程占用
#   选项A：停止占用端口的进程
sudo systemctl stop nginx  # 如果是nginx占用
# 或
#   选项B：修改docker-compose.yml使用其他端口
vim docker-compose.yml
# 把 443:443 改成 8443:443
# 把 80:80 改成 8080:80
```

### 7.2 Docker构建失败

**问题**：
```
Error: Failed to build image
```

**解决方案**：

```bash
# 1. 清理Docker缓存
docker system prune -a

# 2. 清理构建缓存
docker builder prune -a

# 3. 重新构建
docker build -t requirement-backend .
```

**常见原因及修复**：

**原因A：pip镜像源无法访问**
```bash
# 检查 Dockerfile 中的镜像源配置
cat Dockerfile | grep -i pip

# 如果使用清华源或中科大源无法访问，修改为腾讯云源
# 编辑 Dockerfile 第16行：
# RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.cloud.tencent.com/pypi/simple
```

**原因B：buildx版本限制**
```bash
# 如果遇到 "buildx" 相关错误
# 不要使用 docker-compose build
# 改用：docker build -t requirement-backend .
```

### 7.3 容器启动失败

**问题**：
```
Container exited immediately
```

**解决方案**：

```bash
# 1. 查看容器日志
docker-compose logs backend
docker-compose logs frontend

# 2. 查看详细日志
docker logs requirement-backend --tail 100

# 3. 检查配置文件
cat .env
# 确保API Key正确

# 4. 检查端口占用
sudo lsof -i :443
sudo lsof -i :80
```

### 7.4 前端无法访问后端API

**问题**：
前端页面显示，但点击按钮没反应，F12看到API请求失败

**解决方案**：

```bash
# 1. 检查后端容器是否运行
docker-compose ps backend

# 2. 检查网络连通性
docker exec -it requirement-frontend ping backend

# 3. 查看Nginx配置
docker exec -it requirement-frontend cat /etc/nginx/nginx.conf

# 4. 手动测试后端
curl http://localhost/api/v1/health

# 5. 如果后端正常，前端不能访问，重启前端容器
docker-compose restart frontend
```

### 7.5 内存不足

**问题**：
```
Cannot allocate memory
```

**解决方案**：

```bash
# 1. 查看服务器内存
free -h

# 2. 如果内存确实不足，增加swap空间
sudo dd if=/dev/zero of=/swapfile bs=1G count=2
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 3. 永久生效
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# 4. 限制容器内存（可选）
vim docker-compose.yml
# 添加：
# deploy:
#   resources:
#     limits:
#       memory: 1G
```

### 7.6 权限问题

**问题**：
```
Permission denied: './data'
```

**解决方案**：

```bash
# 1. 创建必要的目录并设置权限
mkdir -p data logs uploads
chmod 755 data logs uploads

# 2. 检查文件所有者
ls -la data/

# 3. 如果权限不对，修改所有者
sudo chown -R root:root data logs uploads
```

### 7.7 API Key错误

**问题**：
```
Error: Invalid API key
```

**解决方案**：

```bash
# 1. 检查.env文件
cat .env

# 2. 验证API Key格式
# 应该类似：sk-xxxxxxxxxxxxxxxx

# 3. 修改API Key
vim .env
# 保存后重启容器
docker-compose restart backend

# 4. 查看后端日志确认
docker-compose logs -f backend
```

### 7.8 防火墙阻止访问

**问题**：
本地能访问，其他电脑无法访问

**解决方案**：

```bash
# 1. 检查防火墙状态
sudo firewall-cmd --state

# 2. 开放端口
sudo firewall-cmd --permanent --add-port=80/tcp
sudo firewall-cmd --permanent --add-port=443/tcp

# 3. 重载防火墙
sudo firewall-cmd --reload

# 4. 查看规则
sudo firewall-cmd --list-all
```

---

## 🔧 第八章：修改程序和配置

### 8.1 修改代码后重新部署

```bash
# 1. 在开发环境修改代码
cd /home/admin/Claude/requirement-estimation-system

# 2. 重新打包
tar czf requirement-system-new.tar.gz requirement-estimation-system/

# 3. 传输到目标服务器
scp requirement-system-new.tar.gz root@192.168.1.100:/tmp/

# 4. 在目标服务器部署
ssh root@192.168.1.100

cd /tmp
tar xzf requirement-system-new.tar.gz

# 停止旧容器
cd /opt/requirement-estimation-system
docker-compose down

# 备份旧版本（可选）
cp -r . ../requirement-estimation-system.backup

# 解压新版本
tar xzf /tmp/requirement-system-new.tar.gz -C /opt/
cd /opt/requirement-estimation-system

# 重新部署
./deploy.sh
```

### 8.2 只修改配置文件

```bash
# 如果只修改了配置，不需要重新构建

# 1. 修改配置文件
vim .env
# 或
vim system_list.csv

# 2. 重启容器（重新加载配置）
docker-compose restart backend

# 3. 验证配置生效
docker-compose logs -f backend
```

### 8.3 修改前端代码

```bash
# 1. 在开发环境修改前端代码
cd /home/admin/Claude/requirement-estimation-system/frontend

# 2. 重新构建前端
npm run build

# 3. 只传输build目录到目标服务器
scp -r build/* root@192.168.1.100:/opt/requirement-estimation-system/frontend/build/

# 4. 在目标服务器重启前端容器
ssh root@192.168.1.100
cd /opt/requirement-estimation-system
docker-compose restart frontend

# 注意：前端代码修改不需要重新构建Docker镜像
```

### 8.4 修改后端代码

```bash
# 1. 在开发环境修改后端代码
cd /home/admin/Claude/requirement-estimation-system

# 2. 重新打包整个项目
tar czf requirement-system-new.tar.gz requirement-estimation-system/

# 3. 传输并重新部署
scp requirement-system-new.tar.gz root@192.168.1.100:/tmp/
# ... （参考7.1的完整步骤）
```

### 8.5 增量更新（只传输修改的文件）

```bash
# 1. 在开发环境
cd /home/admin/Claude/requirement-estimation-system

# 2. 只传输修改的文件
scp backend/app.py root@192.168.1.100:/opt/requirement-estimation-system/backend/

# 3. 在目标服务器重启容器
ssh root@192.168.1.100
cd /opt/requirement-estimation-system
docker-compose restart backend

# 注意：Python文件修改会自动重载（如果在debug模式）
# 但建议使用restart确保生效
```

### 8.6 查看和编辑容器内文件

```bash
# 1. 进入容器内部
docker exec -it requirement-backend bash

# 2. 你现在在容器内部，可以查看和编辑文件
ls -la
cat .env
vim .env

# 3. 编辑完成后退出容器
exit

# 4. 重启容器使修改生效
docker-compose restart backend
```

### 8.7 容器内安装软件

```bash
# 1. 进入容器
docker exec -it requirement-backend bash

# 2. 安装软件（例如：安装vim）
apt-get update
apt-get install -y vim

# 3. 退出容器
exit

# 注意：容器重启后安装的软件会消失
# 永久安装需要修改Dockerfile
```

---

## 🔄 第八章：Git版本部署方案（推荐）

> 为什么要用Git管理版本？
> - 版本可控：每次修改都有记录，可以随时回滚
> - 协作方便：多人开发时不会冲突
> - 自动化：可以配合CI/CD实现自动部署
> - 安全：代码托管在云端，不会丢失

### 8.1 Git版本管理基础

#### 8.1.1 初始化Git仓库

```bash
# 1. 在项目根目录初始化Git
cd /home/admin/Claude/requirement-estimation-system
git init

# 2. 创建 .gitignore 文件（排除不需要提交的文件）
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.venv/
*.egg-info/
dist/
build/

# Node.js
node_modules/
npm-debug.log
yarn-error.log
frontend/build/

# IDE
.vscode/
.idea/
*.swp
*.swo

# 日志和数据
logs/
data/
uploads/
*.log

# 环境变量
.env
.env.local

# Docker
.dockerignore

# 临时文件
*.tmp
*.bak
.DS_Store
EOF

# 3. 添加所有文件到Git
git add .

# 4. 创建初始提交
git commit -m "feat: 初始化需求评估系统项目"
```

#### 8.1.2 Git工作流程

```
工作区（你编辑的文件）
    ↓ git add
暂存区（准备提交的文件）
    ↓ git commit
本地仓库（提交历史）
    ↓ git push
远程仓库（GitHub/GitLab等）
```

### 8.2 Git版本部署方案对比

| 方案 | 优点 | 缺点 | 适用场景 |
|------|------|------|---------|
| **方案A：手动传输** | 简单直接，不需要Git | 无法回滚，无版本记录 | 单次部署，简单项目 |
| **方案B：Git拉取部署** | 版本可控，可回滚，有历史 | 需要网络访问Git | **推荐：生产环境** |
| **方案C：CI/CD自动部署** | 完全自动化，测试覆盖 | 配置复杂，需要CI/CD平台 | 大型团队，频繁发布 |

**本章重点讲解方案B（Git拉取部署）**，这是最适合中小团队的方案。

---

### 8.3 方案B：Git拉取部署（完整流程）

#### 8.3.1 在开发环境：提交代码到Git

**步骤1：配置Git用户信息**
```bash
# 配置Git用户（只需配置一次）
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

**步骤2：连接远程仓库（首次）**
```bash
# 方式A：使用GitHub
# 1. 在GitHub创建新仓库：requirement-estimation-system
# 2. 关联远程仓库
git remote add origin https://github.com/your-username/requirement-estimation-system.git

# 方式B：使用GitLab
git remote add origin https://gitlab.com/your-username/requirement-estimation-system.git

# 方式C：使用自建Git服务器
git remote add origin ssh://git@your-git-server.com/requirement-estimation-system.git

# 验证远程仓库
git remote -v
```

**步骤3：创建版本标签**
```bash
# 开发完成后，创建版本标签
git tag -a v1.0.0 -m "版本1.0.0：首次发布"

# 查看标签
git tag

# 推送标签到远程仓库
git push origin v1.0.0

# 或者推送所有标签
git push origin --tags
```

#### 8.3.2 在目标服务器：从Git拉取并部署

**步骤1：首次部署（克隆仓库）**
```bash
# SSH登录目标服务器
ssh root@192.168.1.100

# 进入工作目录
cd /opt

# 克隆仓库
git clone https://github.com/your-username/requirement-estimation-system.git
# 或者使用SSH（推荐，更安全）
git clone git@github.com:your-username/requirement-estimation-system.git

# 进入项目目录
cd requirement-estimation-system

# 配置环境变量
vim .env
# 填写真实的API Key

# 执行部署
./deploy.sh
```

**步骤2：更新部署（拉取最新代码）**
```bash
# SSH登录目标服务器
ssh root@192.168.1.100

# 进入项目目录
cd /opt/requirement-estimation-system

# 1. 备份当前版本（可选）
git tag backup-$(date +%Y%m%d-%H%M%S)

# 2. 拉取最新代码
git fetch origin
git pull origin main

# 3. 检查是否有新标签（版本）
git fetch --tags

# 4. 如果需要切换到指定版本
git checkout v1.1.0

# 5. 重新构建并部署
docker-compose down
./deploy.sh

# 6. 验证部署
curl http://localhost/api/v1/health
```

---

### 8.4 版本管理最佳实践

#### 8.4.1 分支策略

**Git Flow 工作流（推荐）：**

```
main (主分支)
  ├─ 生产环境代码
  └─ 只接受merge请求，不直接修改

develop (开发分支)
  ├─ 开发环境代码
  └─ 功能开发完成后合并到这里

feature/xxx (功能分支)
  ├─ 从develop创建
  └─ 开发完成后合并回develop

hotfix/xxx (紧急修复分支)
  ├─ 从main创建
  └─ 修复后同时合并到main和develop
```

**简化版工作流（适合小型项目）：**

```
main (主分支)
  └─ 直接在main上开发，使用标签标记版本
```

#### 8.4.2 提交信息规范

```bash
# 格式：<类型>: <描述>

# 类型说明：
feat:     新功能
fix:      修复bug
docs:     文档更新
style:    代码格式（不影响功能）
refactor: 重构代码
test:     添加测试
chore:    构建/工具变更

# 示例：
git commit -m "feat: 添加批量导入功能"
git commit -m "fix: 修复API超时问题"
git commit -m "docs: 更新部署文档"
```

#### 8.4.3 版本号规范

**语义化版本（Semantic Versioning）：**

```
格式：v主版本.次版本.修订号

示例：
v1.0.0  - 首次发布
v1.1.0  - 添加新功能（向后兼容）
v1.1.1  - 修复bug
v2.0.0  - 重大变更（不向后兼容）
```

**创建版本标签：**
```bash
# 开发环境
git tag -a v1.0.0 -m "版本1.0.0：首次发布"
git push origin v1.0.0

# 生产环境
git fetch --tags
git checkout v1.0.0
./deploy.sh
```

---

### 8.5 完整部署流程示例

#### 场景：开发新功能并部署到生产环境

**开发环境（你的电脑）：**

```bash
# 1. 创建功能分支
git checkout -b feature/add-export-feature

# 2. 开发新功能（编辑代码）
vim backend/app.py
vim frontend/src/App.jsx

# 3. 本地测试
cd frontend
npm run build
cd ..
docker build -t requirement-backend .
docker-compose up -d
# 测试功能...

# 4. 提交代码
git add .
git commit -m "feat: 添加导出Excel功能"

# 5. 合并到主分支
git checkout main
git merge feature/add-export-feature

# 6. 创建版本标签
git tag -a v1.1.0 -m "版本1.1.0：添加导出Excel功能"

# 7. 推送到远程仓库
git push origin main
git push origin v1.1.0

# 8. 删除功能分支
git branch -d feature/add-export-feature
```

**生产服务器：**

```bash
# 1. 登录服务器
ssh root@192.168.1.100
cd /opt/requirement-estimation-system

# 2. 查看当前版本
git describe --tags
# 输出：v1.0.0

# 3. 拉取最新代码
git fetch origin
git pull origin main

# 4. 查看新版本
git tag
# 输出：v1.0.0  v1.1.0

# 5. 切换到新版本
git checkout v1.1.0

# 6. 重新部署
docker-compose down
./deploy.sh

# 7. 验证
curl http://localhost/api/v1/health

# 8. 如果有问题，立即回滚
git checkout v1.0.0
docker-compose down
./deploy.sh
```

---

### 8.6 版本回滚方案

#### 8.6.1 回滚到指定版本

```bash
# 1. 查看所有版本
git tag

# 2. 回滚到上一个版本
git checkout v1.0.0

# 3. 重新部署
docker-compose down
./deploy.sh

# 4. 验证回滚成功
curl http://localhost/api/v1/health
```

#### 8.6.2 紧急回滚脚本

**创建回滚脚本：**
```bash
cat > /opt/requirement-estimation-system/rollback.sh << 'EOF'
#!/bin/bash
set -e

echo "========================================="
echo "需求评估系统 - 版本回滚脚本"
echo "========================================="

# 显示当前版本
CURRENT_VERSION=$(git describe --tags 2>/dev/null || echo "未标记")
echo "当前版本: $CURRENT_VERSION"
echo ""

# 列出所有版本
echo "可用版本："
git tag
echo ""

# 提示输入版本号
read -p "请输入要回滚到的版本号（如 v1.0.0）: " VERSION

# 检查版本是否存在
if ! git rev-parse "$VERSION" >/dev/null 2>&1; then
    echo "错误：版本 $VERSION 不存在"
    exit 1
fi

# 确认回滚
echo ""
read -p "确认回滚到版本 $VERSION ? (y/n): " CONFIRM
if [ "$CONFIRM" != "y" ]; then
    echo "取消回滚"
    exit 0
fi

# 备份当前版本
BACKUP_TAG="backup-$(date +%Y%m%d-%H%M%S)"
git tag "$BACKUP_TAG"
echo "已备份当前版本为: $BACKUP_TAG"

# 切换版本
echo "切换到版本: $VERSION"
git checkout "$VERSION"

# 停止服务
echo "停止服务..."
docker-compose down

# 重新部署
echo "重新部署..."
./deploy.sh

# 验证
echo ""
echo "========================================="
echo "回滚完成！"
echo "========================================="
echo "当前版本: $(git describe --tags)"
echo "备份版本: $BACKUP_TAG"
echo ""
echo "如需再次回滚，使用："
echo "  git checkout $BACKUP_TAG"
echo "  ./deploy.sh"
echo "========================================="
EOF

chmod +x /opt/requirement-estimation-system/rollback.sh
```

**使用回滚脚本：**
```bash
# 执行回滚
/opt/requirement-estimation-system/rollback.sh

# 按提示操作即可
```

---

### 8.7 Git与Docker结合的进阶技巧

#### 8.7.1 将版本信息注入镜像

**修改 Dockerfile：**
```dockerfile
# 在构建时传入版本信息
ARG VERSION=unknown
ENV APP_VERSION=$VERSION

# 其余内容...
```

**构建时指定版本：**
```bash
# 获取Git版本号
VERSION=$(git describe --tags)

# 构建镜像时传入版本号
docker build \
  --build-arg VERSION=$VERSION \
  -t requirement-backend:$VERSION \
  -t requirement-backend:latest \
  .
```

**在代码中读取版本：**
```python
import os
version = os.getenv("APP_VERSION", "unknown")
print(f"当前版本: {version}")
```

#### 8.7.2 使用Git钩子自动部署

**创建 post-merge 钩子：**
```bash
cat > .git/hooks/post-merge << 'EOF'
#!/bin/bash
echo "检测到代码更新，自动开始部署..."
./deploy.sh
EOF

chmod +x .git/hooks/post-merge
```

**效果：**
```bash
# 每次执行 git pull 后，自动触发部署
git pull origin main
# 自动运行 ./deploy.sh
```

#### 8.7.3 多环境配置

**目录结构：**
```
requirement-estimation-system/
├── .env.example        # 环境变量模板
├── .env.development    # 开发环境配置
├── .env.production     # 生产环境配置
└── deploy.sh
```

**修改 deploy.sh 支持多环境：**
```bash
#!/bin/bash

# 检测环境
ENV=${1:-production}

echo "部署环境: $ENV"

# 复制对应的配置文件
if [ -f ".env.$ENV" ]; then
    cp ".env.$ENV" .env
    echo "已加载配置: .env.$ENV"
else
    echo "警告：配置文件 .env.$ENV 不存在"
fi

# 继续部署...
./deploy.sh
```

**使用：**
```bash
# 开发环境部署
./deploy.sh development

# 生产环境部署
./deploy.sh production
```

---

### 8.8 常见Git问题及解决

#### 8.8.1 拉取代码时冲突

```bash
# 问题：git pull 时提示冲突
error: Your local changes to the following files would be overwritten by merge

# 解决方案1：暂存本地修改
git stash
git pull origin main
git stash pop

# 解决方案2：放弃本地修改（谨慎）
git reset --hard HEAD
git pull origin main
```

#### 8.8.2 推送被拒绝

```bash
# 问题：git push 时提示 rejected
! [rejected]        main -> main (fetch first)

# 解决方案：先拉取再推送
git pull --rebase origin main
git push origin main
```

#### 8.8.3 忘记拉取直接修改

```bash
# 问题：远程有新提交，本地直接修改了

# 解决步骤：
# 1. 暂存本地修改
git stash

# 2. 拉取远程最新代码
git pull origin main

# 3. 恢复本地修改
git stash pop

# 4. 解决冲突后提交
git add .
git commit -m "fix: 解决合并冲突"
git push origin main
```

---

## 📊 第十章：监控和维护

### 10.1 日常监控命令

```bash
# 1. 查看容器状态（每天执行）
docker-compose ps

# 2. 查看资源占用（每天执行）
docker stats

# 3. 查看日志（每天执行）
docker-compose logs --tail 100

# 4. 检查磁盘空间（每周执行）
df -h
du -sh /opt/requirement-estimation-system/data/*
```

### 10.2 日志管理

```bash
# 1. 清理旧日志（保留最近7天）
find logs/ -name "*.log" -mtime +7 -delete

# 2. 查看日志大小
du -sh logs/

# 3. 实时监控日志
docker-compose logs -f
```

### 10.3 数据备份

```bash
# 1. 创建备份脚本
cat > /opt/backup-requirement.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/backup/requirement-$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# 备份配置和数据
cd /opt/requirement-estimation-system
cp -r .env $BACKUP_DIR/
cp -r system_list.csv $BACKUP_DIR/ 2>/dev/null || true
cp -r backend/subsystem_list.csv $BACKUP_DIR/ 2>/dev/null || true
cp -r backend/config/cosmic_config.json $BACKUP_DIR/ 2>/dev/null || true
cp -r data $BACKUP_DIR/

echo "备份完成: $BACKUP_DIR"
EOF

chmod +x /opt/backup-requirement.sh

# 2. 手动备份
/opt/backup-requirement.sh

# 3. 设置定时备份（每天凌晨2点）
crontab -e
# 添加一行：
# 0 2 * * * /opt/backup-requirement.sh
```

### 10.4 清理Docker资源

```bash
# 1. 清理未使用的镜像
docker image prune -a

# 2. 清理未使用的容器
docker container prune

# 3. 清理未使用的卷
docker volume prune

# 4. 清理所有未使用资源
docker system prune -a
```

---

## 🎯 第十一章：快速参考卡

### 11.1 部署流程速查

```bash
# 步骤1：开发服务器 - 打包
cd /home/admin/Claude/requirement-estimation-system
./package.sh  # 自动构建前端+Docker镜像+打包

# 步骤2：开发服务器 - 传输
scp requirement-system-*.tar.gz root@目标IP:/tmp/

# 步骤3：目标服务器 - 部署
ssh root@目标IP
cd /tmp
tar xzf requirement-system-*.tar.gz
mv requirement-estimation-system /opt/
cd /opt/requirement-estimation-system
vim .env  # 配置API Key
./deploy.sh  # 在目标服务器执行部署

# 步骤4：验证
curl http://localhost/api/v1/health
```

### 11.2 常用命令速查

```bash
# 查看容器状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 重启服务
docker-compose restart

# 停止服务
docker-compose down

# 进入容器
docker exec -it requirement-backend bash

# 查看资源占用
docker stats

# 清理资源
docker system prune -a
```

### 11.3 故障排查速查

```bash
# 问题1：容器启动失败
docker-compose logs backend

# 问题2：端口被占用
sudo lsof -i :443

# 问题3：权限错误
sudo chown -R root:root data logs uploads

# 问题4：内存不足
free -h

# 问题5：防火墙
sudo firewall-cmd --list-all

# 问题6：Docker构建失败（镜像源或buildx问题）
docker build -t requirement-backend .  # 不用 docker-compose build
# 检查 Dockerfile 中的 pip 镜像源是否使用腾讯云源
```

---

### 7.9 Dockerfile中的路径问题

**问题**：
项目目录下没有 /app，但 Dockerfile 中有 `WORKDIR /app`，是否有问题？

**解答**：
这是完全正常的！

```dockerfile
WORKDIR /app  # 这是在容器内部创建目录
```

**概念说明**：
- `/app` 是**容器内部**的路径，不是主机路径
- Docker 构建镜像时会自动在容器内创建这个目录
- 不需要在主机上预先创建

**主机与容器的目录映射**：

```
主机目录                         容器目录
/home/admin/Claude/...     →    /app/           (WORKDIR 创建)
                          →    /app/backend/    (COPY 复制)
                          →    /app/frontend/   (COPY 复制)
./data                     →    /app/data/       (volumes 映射)
./logs                     →    /app/logs/       (volumes 映射)
```

**为什么容器内要用 /app 而不是主机路径？**

1. **移植性**：不同电脑项目路径不同，容器内路径保持一致
2. **简洁性**：容器内用简单路径，如 /app、/data
3. **安全性**：不暴露主机的目录结构

**主机目录通过 docker-compose.yml 映射**：
```yaml
volumes:
  - ./data:/app/data      # 左边是主机，右边是容器内
  - ./logs:/app/logs      # 左边是主机，右边是容器内
```

---

## 📞 第十三章：获取帮助

### 13.1 获取日志信息

遇到问题时，提供以下信息可以快速定位：

```bash
# 1. 容器状态
docker-compose ps > docker-status.txt

# 2. 容器日志
docker-compose logs backend > backend-logs.txt
docker-compose logs frontend > frontend-logs.txt

# 3. 系统信息
uname -a > system-info.txt
docker version > docker-version.txt

# 4. 网络测试
curl -v http://localhost/api/v1/health > network-test.txt 2>&1
```

### 13.2 紧急回滚

如果部署后出现严重问题，快速回滚：

```bash
# 1. 停止新版本
cd /opt/requirement-estimation-system
docker-compose down

# 2. 恢复旧版本
mv requirement-estimation-system requirement-estimation-system.new
mv ../requirement-estimation-system.backup .

# 3. 重新启动
./deploy.sh

# 或者如果有完整的旧备份
cd /opt
tar xzf requirement-system-backup.tar.gz
cd requirement-estimation-system
./deploy.sh
```

---

## ✅ 总结

### 部署检查清单

- [ ] Docker已安装
- [ ] Docker Compose已安装
- [ ] 项目已打包
- [ ] 文件已传输到目标服务器
- [ ] .env文件已配置
- [ ] 部署脚本已执行
- [ ] 容器状态正常
- [ ] 健康检查通过
- [ ] 浏览器可以访问
- [ ] API功能正常

### 你只需要记住的3条命令

```bash
# 1. 查看状态
docker-compose ps

# 2. 查看日志
docker-compose logs -f

# 3. 重启服务
docker-compose restart
```

恭喜你完成部署！🎉

有任何问题，参考本手册对应章节即可。
