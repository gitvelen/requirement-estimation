# 需求估算系统 - 前后端独立部署指南

## 📋 部署架构说明

本项目采用前后端分离部署架构：

- **前端服务器**：124.223.38.219（端口 80）
- **后端服务器**：8.153.194.178（端口 443）
- **代码仓库**：https://github.com/gitvelen/requirement-estimation-system.git

```
用户浏览器 → 前端服务器(124.223.38.219:80) → 后端服务器(8.153.194.178:443)
                  Nginx静态文件                    FastAPI后端
```

---

## 🚀 快速部署（推荐）⭐

### 使用一键部署脚本

**在你本地机器上**执行：

```bash
cd /home/admin/Claude/requirement-estimation-system

# 一键部署前后端
./deploy-remote-all.sh 124.223.38.219 8.153.194.178
```

脚本会自动：
1. 从GitHub克隆master分支到后端服务器
2. 配置并启动后端服务
3. 从GitHub克隆master分支到前端服务器
4. 配置并启动前端服务
5. 验证部署结果

---

## 🔧 手动部署步骤

如果需要手动控制每个步骤，请按以下流程操作：

### 第一步：部署后端服务器（8.153.194.178）

#### 1.1 SSH登录到后端服务器

```bash
ssh root@8.153.194.178
```

#### 1.2 从GitHub克隆代码

```bash
# 如果目录已存在，先备份
mv /root/requirement-estimation-system /root/requirement-estimation-system.backup 2>/dev/null || true

# 克隆master分支
git clone -b master https://github.com/gitvelen/requirement-estimation-system.git /root/requirement-estimation-system

# 进入项目目录
cd /root/requirement-estimation-system
```

#### 1.3 配置后端环境变量

创建 `.env.backend` 文件：

```bash
cp .env.backend.example .env.backend
vi .env.backend
```

**配置内容示例**：

```bash
# 后端环境变量配置

# ========== 知识库配置 ==========
KNOWLEDGE_ENABLED=true
KNOWLEDGE_VECTOR_STORE=local
DASHSCOPE_API_KEY=sk-your-actual-api-key-here

# ========== 认证配置 ==========
JWT_SECRET=please_change_this_to_a_random_string_32_chars
JWT_EXPIRE_MINUTES=120
ADMIN_API_KEY=your_admin_api_key_here

# ========== CORS配置 ==========
# 允许前端服务器访问
ALLOWED_ORIGINS=http://124.223.38.219,http://124.223.38.219:80

# ========== 其他配置 ==========
DEBUG=false
HOST=0.0.0.0
PORT=443
```

**重要提示**：
- `DASHSCOPE_API_KEY` 必须填写真实的阿里云 API Key
- `JWT_SECRET` 建议使用随机字符串（至少32位）
- `ALLOWED_ORIGINS` 必须包含前端服务器地址

#### 1.4 构建并启动后端服务

```bash
cd /root/requirement-estimation-system

# 构建并启动后端容器
docker-compose -f docker-compose.backend.yml up -d --build

# 查看容器状态
docker-compose -f docker-compose.backend.yml ps

# 查看后端日志
docker-compose -f docker-compose.backend.yml logs -f backend
```

等待后端启动完成（看到 "Application startup complete"），然后按 `Ctrl+C` 退出日志查看。

#### 1.5 验证后端服务

```bash
# 测试健康检查接口
curl -k https://localhost:443/api/v1/health

# 预期返回：{"status":"healthy"}
```

在**本地机器**测试（从外部访问）：

```bash
curl -k https://8.153.194.178:443/api/v1/health
```

---

### 第二步：部署前端服务器（124.223.38.219）

#### 2.1 SSH登录到前端服务器

```bash
ssh root@124.223.38.219
```

#### 2.2 从GitHub克隆代码

```bash
# 如果目录已存在，先备份
mv /root/requirement-estimation-system /root/requirement-estimation-system.backup 2>/dev/null || true

# 克隆master分支
git clone -b master https://github.com/gitvelen/requirement-estimation-system.git /root/requirement-estimation-system

# 进入项目目录
cd /root/requirement-estimation-system
```

#### 2.3 修改nginx配置

```bash
cd frontend

# 修改nginx配置，指向后端服务器
sed 's/BACKEND_SERVER_PLACEHOLDER/8.153.194.178/g' nginx-remote.conf > nginx-remote-deploy.conf

# 替换nginx配置
cp nginx.conf nginx.conf.local.bak 2>/dev/null || true
cp nginx-remote-deploy.conf nginx.conf

# 验证配置
cat nginx.conf | grep proxy_pass
```

确认输出为：`proxy_pass https://8.153.194.178:443;`

#### 2.4 配置前端环境变量

```bash
cd /root/requirement-estimation-system

# 创建 .env.frontend 文件
cat > .env.frontend << 'EOF'
# 前端环境变量配置
REACT_APP_API_URL=https://8.153.194.178
EOF
```

#### 2.5 构建并启动前端服务

```bash
cd /root/requirement-estimation-system

# 构建并启动前端容器
docker-compose -f docker-compose.frontend.yml up -d --build

# 查看容器状态
docker-compose -f docker-compose.frontend.yml ps

# 查看前端日志
docker-compose -f docker-compose.frontend.yml logs -f frontend
```

等待前端启动完成，然后按 `Ctrl+C` 退出日志查看。

#### 2.6 验证前端服务

```bash
# 测试前端页面
curl -I http://localhost:80
```

在**本地机器**测试：

```bash
curl -I http://124.223.38.219
```

---

## ✅ 部署验证

### 1. 浏览器访问测试

在浏览器中访问：`http://124.223.38.219`

应该能看到登录页面。

### 2. 创建初始管理员用户

在后端服务器上执行：

```bash
# 进入后端容器
docker exec -it requirement-backend bash

# 创建管理员用户脚本
python -c "
from backend.service.user_service import UserService
user_service = UserService()
user_service.create_user(
    username='admin',
    password='admin123',
    email='admin@example.com',
    role='admin',
    department='技术部'
)
print('管理员用户创建成功')
print('用户名: admin')
print('密码: admin123')
"

# 退出容器
exit
```

然后使用 `admin / admin123` 登录系统。

---

## 🔍 常见问题排查

### 问题1：后端容器启动失败

**排查步骤**：

```bash
# 在后端服务器上
docker-compose -f docker-compose.backend.yml logs backend

# 检查常见错误：
# 1. 端口443被占用
# 2. .env.backend 配置错误
# 3. DASHSCOPE_API_KEY 未配置
```

### 问题2：前端无法连接后端

**排查步骤**：

```bash
# 1. 在前端服务器上测试后端连通性
curl -k https://8.153.194.178:443/api/v1/health

# 2. 检查后端防火墙规则
# 在后端服务器上
firewall-cmd --list-ports
# 如果没有443端口，需要开放
firewall-cmd --permanent --add-port=443/tcp
firewall-cmd --reload

# 3. 检查前端 nginx 配置
docker exec requirement-frontend cat /etc/nginx/nginx.conf | grep proxy_pass
```

### 问题3：GitHub克隆失败

**排查步骤**：

```bash
# 检查网络连通性
curl -I https://github.com

# 如果GitHub访问受限，可以使用镜像
# git clone -b master https://gitee.com/mirror/requirement-estimation-system.git
```

---

## 📝 部署后操作

### 1. 修改默认密码

登录系统后，立即修改管理员默认密码。

### 2. 配置防火墙规则

**后端服务器**（8.153.194.178）：

```bash
# 开放443端口
firewall-cmd --permanent --add-port=443/tcp
firewall-cmd --reload
```

**前端服务器**（124.223.38.219）：

```bash
# 开放80端口
firewall-cmd --permanent --add-port=80/tcp
firewall-cmd --reload
```

### 3. 配置域名（可选）

如果有域名，可以将域名解析到前端服务器：

```bash
# 示例：前端使用域名
# A记录：app.yourdomain.com → 124.223.38.219

# 前端nginx配置需要修改
# server_name app.yourdomain.com;
```

---

## 🔄 更新部署

当代码有更新时，重新部署的步骤：

### 更新后端

```bash
# 在后端服务器上
cd /root/requirement-estimation-system
git pull origin master
docker-compose -f docker-compose.backend.yml up -d --build
```

### 更新前端

```bash
# 在前端服务器上
cd /root/requirement-estimation-system
git pull origin master
docker-compose -f docker-compose.frontend.yml up -d --build
```

### 使用部署脚本更新

**在本地机器上**执行：

```bash
# 重新部署后端
./deploy-backend.sh 8.153.194.178

# 重新部署前端
./deploy-frontend.sh 124.223.38.219 8.153.194.178

# 或一键重新部署
./deploy-remote-all.sh 124.223.38.219 8.153.194.178
```

---

## 📞 获取帮助

如果遇到问题：

1. 查看日志：`docker-compose logs -f`
2. 检查配置：确认 `.env.backend` 和 `.env.frontend` 配置正确
3. 网络测试：使用 `curl` 测试前后端连通性
4. 容器状态：使用 `docker ps` 查看容器是否正常运行

---

## 📦 部署文件说明

### Docker Compose 文件

- `docker-compose.backend.yml` - 后端独立部署配置
- `docker-compose.frontend.yml` - 前端独立部署配置
- `docker-compose.yml` - 本地开发环境（单机部署）

### 部署脚本

- `deploy-remote-all.sh` - 远程服务器一键部署脚本
- `deploy-backend.sh` - 后端独立部署脚本
- `deploy-frontend.sh` - 前端独立部署脚本

### Nginx配置

- `frontend/nginx.conf` - 本地开发nginx配置
- `frontend/nginx-remote.conf` - 远程部署nginx配置模板

---

*最后更新：2026-02-02*
