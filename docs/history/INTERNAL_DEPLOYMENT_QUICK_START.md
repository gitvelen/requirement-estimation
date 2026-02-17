# 内网环境一键部署指南

本指南适用于在内网环境（前后端分离、无法访问外网）部署需求评估系统。

## 📋 环境信息

### 服务器配置
- **后端服务器**: 10.62.22.121:443
- **前端服务器**: 10.62.16.251:8000
- **Python 私服**: http://pypi.ppr.dev:8081/repository/shrbank-pypi-group/simple
- **大模型服务**: http://10.73.254.200:30000/v1 (Qwen3-32B-local)

### 基础镜像要求
- **后端基础镜像**: uv-mineru-opencv:0.1.0
- **前端基础镜像**: nginx:latest

---

## 🚀 快速部署

### 准备工作（在本地机器）

#### 1. 构建前端（在本地有 Node.js 环境的机器）

```bash
cd requirement-estimation-system/frontend
npm install
npm run build
```

#### 2. 打包文件

```bash
# 打包前端构建产物
tar czf frontend-build.tar.gz -C frontend build/

# 打包完整代码（包含所有部署文件）
tar czf requirement-internal.tar.gz \
    Dockerfile.internal \
    docker-compose.backend.internal.yml \
    docker-compose.frontend.internal.yml \
    .env.backend.internal \
    deploy-backend-internal.sh \
    deploy-frontend-internal.sh \
    backend/ \
    frontend/nginx.conf \
    frontend/Dockerfile.internal \
    entrypoint.sh \
    pyproject.toml \
    uv.lock
```

#### 3. 上传文件到服务器

```bash
# 上传完整代码到两台服务器
scp requirement-internal.tar.gz root@10.62.22.121:/home/admin/
scp requirement-internal.tar.gz root@10.62.16.251:/home/admin/

# 上传前端构建产物到前端服务器
scp frontend-build.tar.gz root@10.62.16.251:/home/admin/
```

---

### 第一步：部署后端服务 (10.62.22.121)

SSH 登录到**后端服务器**：

```bash
ssh root@10.62.22.121
```

执行以下命令：

```bash
# 1. 解压代码
cd /home/admin
tar xzf requirement-internal.tar.gz -C requirement-estimation-system/
cd requirement-estimation-system

# 2. 配置环境变量（使用内网配置）
cp .env.backend.internal .env.backend

# 3. 执行一键部署脚本
chmod +x deploy-backend-internal.sh
./deploy-backend-internal.sh
```

**部署完成后验证：**

```bash
# 查看容器状态
docker ps | grep requirement-backend

# 测试健康检查
curl http://localhost:443/api/v1/health
```

预期输出：`{"status":"healthy"}` 或类似的成功响应。

---

### 第二步：部署前端服务 (10.62.16.251)

SSH 登录到**前端服务器**：

```bash
ssh root@10.62.16.251
```

执行以下命令：

```bash
# 1. 解压代码
cd /home/admin
tar xzf requirement-internal.tar.gz -C requirement-estimation-system/
cd requirement-estimation-system

# 2. 确认前端构建包已上传
ls -la /home/admin/frontend-build.tar.gz

# 3. 执行一键部署脚本
# 脚本会自动解压 frontend-build.tar.gz 到 frontend/build 目录
chmod +x deploy-frontend-internal.sh
./deploy-frontend-internal.sh
```

**部署完成后验证：**

```bash
# 查看容器状态
docker ps | grep requirement-frontend

# 测试访问
curl -I http://localhost:8000
```

预期输出：`HTTP/1.1 200 OK`

---

### 第三步：整体测试

#### 1. 浏览器访问前端

在浏览器中访问：`http://10.62.16.251:8000`

应该能看到登录页面。

#### 2. 测试后端 API

```bash
# 在后端服务器上测试
curl http://10.62.22.121:443/api/v1/health

# 应该返回：{"status":"healthy"}
```

#### 3. 测试前后端连通性

在前端服务器上测试访问后端：

```bash
curl http://10.62.22.121:443/api/v1/health
```

---

## ✅ 部署完成

如果以上测试都通过，恭喜你部署成功！

### 访问地址
- **前端页面**: http://10.62.16.251:8000
- **后端 API**: http://10.62.22.121:443/api/v1

### 默认配置
- **调试模式**: 开启（DEBUG=true）
- **大模型**: Qwen3-32B-local (内网服务)
- **知识库**: 已启用（本地存储）

---

## 🔧 常见问题排查

### 问题1：后端容器启动失败

**排查步骤：**

```bash
# 1. 查看容器日志
docker logs requirement-backend

# 2. 检查容器状态
docker ps -a | grep requirement-backend

# 3. 检查镜像是否构建成功
docker images | grep requirement-backend
```

**常见原因：**
- 镜像构建失败（查看构建日志）
- entrypoint.sh 缺失
- Python 依赖安装失败

**解决方案：**

```bash
cd /home/admin/requirement-estimation-system
docker-compose -f docker-compose.backend.internal.yml down
docker rmi requirement-backend:latest
./deploy-backend-internal.sh
```

---

### 问题2：前端容器启动失败

**排查步骤：**

```bash
# 1. 查看容器日志
docker logs requirement-frontend

# 2. 检查容器状态
docker ps -a | grep requirement-frontend

# 3. 检查 nginx 配置
docker exec requirement-frontend cat /etc/nginx/nginx.conf

# 4. 检查构建文件
docker exec requirement-frontend ls -la /usr/share/nginx/html/
```

**常见原因：**
- frontend-build.tar.gz 上传位置错误
- nginx 配置错误
- build 目录文件缺失

**解决方案：**

```bash
# 确认构建包位置
ls -la /home/admin/frontend-build.tar.gz

# 重新部署
cd /home/admin/requirement-estimation-system
docker-compose -f docker-compose.frontend.internal.yml down
./deploy-frontend-internal.sh
```

---

### 问题3：前端页面可以打开，但 API 报 404

**原因：** 后端路由未正确注册或容器内代码不是最新版本

**排查步骤：**

```bash
# 1. 检查后端日志
docker logs requirement-backend | grep -i error

# 2. 检查路由是否注册
curl http://10.62.22.121:443/openapi.json | python3 -m json.tool | grep "/api/v1/users"

# 3. 检查容器内的文件
docker exec requirement-backend ls -la /app/backend/api/ | grep user
```

**解决方案：**

```bash
cd /home/admin/requirement-estimation-system

# 停止服务
docker-compose -f docker-compose.backend.internal.yml down

# 删除旧镜像
docker rmi requirement-backend:latest

# 重新构建
docker-compose -f docker-compose.backend.internal.yml build --no-cache

# 启动服务
docker-compose -f docker-compose.backend.internal.yml up -d

# 验证
docker logs -f requirement-backend
```

---

### 问题4：前端可以访问，但登录报错

**排查步骤：**

```bash
# 1. 检查后端日志
docker logs requirement-backend | tail -50

# 2. 检查前端 nginx 配置中的后端地址
docker exec requirement-frontend grep "proxy_pass" /etc/nginx/nginx.conf

# 3. 从前端服务器测试后端连通性
curl http://10.62.22.121:443/api/v1/health
```

**常见原因：**
- 后端服务未启动
- 前端 nginx 配置的后端地址错误
- 防火墙端口未开放

---

## 📝 配置说明

### 后端环境变量 (.env.backend)

主要配置项：

```bash
# 调试模式（开发环境 true，生产环境 false）
DEBUG=true

# 大模型配置
DASHSCOPE_API_BASE=http://10.73.254.200:30000/v1
MODEL_NAME=Qwen3-32B-local
DASHSCOPE_API_KEY=not-needed

# JWT 密钥（建议修改）
JWT_SECRET=internal-deploy-jwt-secret-key-change-in-production

# 管理员 API Key（建议修改）
ADMIN_API_KEY=admin-key-internal-change-in-production

# 知识库配置
KNOWLEDGE_ENABLED=true
KNOWLEDGE_VECTOR_STORE=local
```

### 前端 Nginx 配置

关键配置（`frontend/nginx.conf`）：

```nginx
# 后端 API 代理地址
location /api/ {
    proxy_pass http://10.62.22.121:443;
    # ... 其他配置
}
```

---

## 🛠️ 运维命令

### 后端服务管理

```bash
cd /home/admin/requirement-estimation-system

# 查看日志
docker logs -f requirement-backend

# 重启服务
docker-compose -f docker-compose.backend.internal.yml restart

# 停止服务
docker-compose -f docker-compose.backend.internal.yml down

# 重新部署
./deploy-backend-internal.sh
```

### 前端服务管理

```bash
cd /home/admin/requirement-estimation-system

# 查看日志
docker logs -f requirement-frontend

# 重启服务
docker-compose -f docker-compose.frontend.internal.yml restart

# 停止服务
docker-compose -f docker-compose.frontend.internal.yml down

# 重新部署
./deploy-frontend-internal.sh
```

---

## 📄 文件清单

### 后端相关
- `Dockerfile.internal` - 后端 Dockerfile（基于 uv-mineru-opencv:0.1.0）
- `docker-compose.backend.internal.yml` - 后端 docker-compose 配置
- `.env.backend.internal` - 内网环境变量配置
- `deploy-backend-internal.sh` - 后端一键部署脚本

### 前端相关
- `frontend/Dockerfile.internal` - 前端 Dockerfile（基于 nginx:latest）
- `frontend/nginx.conf` - Nginx 配置（已配置后端代理）
- `docker-compose.frontend.internal.yml` - 前端 docker-compose 配置
- `deploy-frontend-internal.sh` - 前端一键部署脚本（自动解压 frontend-build.tar.gz）

### 部署所需文件
- `frontend-build.tar.gz` - 前端构建产物（需要在本地构建后上传）
- `requirement-internal.tar.gz` - 完整代码包（包含所有部署文件）

---

## 🎯 部署流程总结

```
本地机器                    后端服务器 (10.62.22.121)    前端服务器 (10.62.16.251)
─────────────────────────────────────────────────────────────────────────────
1. 构建前端
   npm run build
                           2. 上传代码并部署
   scp代码 ───────────────> tar xzf ... ──> ./deploy-backend-internal.sh
                                                   ↓
                                            后端服务启动
                                            监听 443 端口

3. 上传前端构建                                      4. 上传代码并部署
   scp frontend-build.tar.gz ────────────────────> tar xzf ... ──> ./deploy-frontend-internal.sh
   scp代码                                                          ↓
                                                              前端服务启动
                                                              监听 8000 端口
                                                              代理到 10.62.22.121:443
```

---

## 📞 技术支持

如遇到问题，请收集以下信息：

1. 服务器操作系统版本
2. Docker 和 Docker Compose 版本
3. 容器日志（`docker logs <容器名>`）
4. 具体错误信息和截图

---

**部署成功后，请及时修改 `.env.backend` 中的敏感配置（JWT_SECRET、ADMIN_API_KEY）！**
