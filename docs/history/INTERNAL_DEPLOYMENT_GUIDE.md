# 内网环境一键部署指南（最终版）

本指南适用于在内网环境（前后端分离、无法访问外网）部署需求评估系统。

## 📋 环境信息

### 服务器配置
- **后端服务器**: 10.62.22.121:443
- **前端服务器**: 10.62.16.251:8000
- **Python 私服**: http://pypi.ppr.dev:8081/repository/shrbank-pypi-group/simple
- **大模型服务**: http://10.73.254.200:30000/v1 (Qwen3-32B-local)
- **工作目录**: /home/admin/requirement-estimation

### 基础镜像要求
- **后端基础镜像**: uv-mineru-opencv:0.1.0
- **前端基础镜像**: nginx:latest

---

## 🚀 快速部署流程

### 准备工作（在本地机器）

#### 1. 构建前端

```bash
cd requirement-estimation-system/frontend
npm install
npm run build
```

#### 2. 打包部署文件

```bash
# 打包前端构建产物
tar czf frontend-build.tar.gz -C frontend build/

# 打包后端部署文件
tar czf backend-new-files.tar.gz \
    Dockerfile.internal \
    docker-compose.backend.internal.yml \
    .env.backend.internal \
    deploy-backend-internal.sh \
    entrypoint.sh \
    pyproject.toml \
    uv.lock \
    backend/

# 打包前端部署文件
tar czf frontend-new-files.tar.gz \
    docker-compose.frontend.internal.yml \
    deploy-frontend-internal.sh \
    frontend/Dockerfile.internal \
    frontend/nginx.conf
```

#### 3. 上传文件到服务器

```bash
# 上传后端文件
scp backend-new-files.tar.gz root@10.62.22.121:/home/admin/

# 上传前端文件
scp frontend-new-files.tar.gz root@10.62.16.251:/home/admin/
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
# 1. 创建工作目录
mkdir -p /home/admin/requirement-estimation

# 2. 解压部署文件
cd /home/admin
tar xzf backend-new-files.tar.gz -C requirement-estimation/
cd requirement-estimation

# 3. 修复文件换行符（重要！）
sed -i 's/\r$//' Dockerfile.internal
sed -i 's/\r$//' docker-compose.backend.internal.yml
sed -i 's/\r$//' deploy-backend-internal.sh
sed -i 's/\r$//' .env.backend.internal
sed -i 's/\r$//' entrypoint.sh

# 4. 删除可能有问题的 .dockerignore
rm -f .dockerignore

# 5. 配置环境变量
cp .env.backend.internal .env.backend

# 6. 执行一键部署脚本
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

---

### 第二步：部署前端服务 (10.62.16.251)

SSH 登录到**前端服务器**：

```bash
ssh root@10.62.16.251
```

执行以下命令：

```bash
# 1. 创建工作目录
mkdir -p /home/admin/requirement-estimation

# 2. 解压部署文件
cd /home/admin
tar xzf frontend-new-files.tar.gz -C requirement-estimation/
cd requirement-estimation

# 3. 修复文件换行符
sed -i 's/\r$//' docker-compose.frontend.internal.yml
sed -i 's/\r$//' deploy-frontend-internal.sh
sed -i 's/\r$//' frontend/Dockerfile.internal
sed -i 's/\r$//' frontend/nginx.conf

# 4. 确认前端构建包已上传
ls -la /home/admin/frontend-build.tar.gz

# 5. 执行一键部署脚本
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

---

## ✅ 最终验证

1. **浏览器访问**: http://10.62.16.251:8000
2. **测试后端**: curl http://10.62.22.121:443/api/v1/health
3. **测试连通性**: 从前端服务器 curl http://10.62.22.121:443/api/v1/health

---

## 🔧 常见问题

详见部署指南的"常见问题排查"章节。

---

**部署成功后，请修改 `.env.backend` 中的敏感配置！**
