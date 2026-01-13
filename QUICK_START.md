# 快速部署指南

## 最简单的部署方式（推荐）

### 前提条件
- 目标服务器已安装 Docker 和 Docker Compose

### 三步完成部署

#### 步骤1：打包项目

```bash
# 在开发服务器上，打包整个项目
cd /home/admin/Claude
tar czf requirement-estimation-system.tar.gz requirement-estimation-system/

# 或者使用rsync直接同步到目标服务器
rsync -avz requirement-estimation-system/ user@target-server:/opt/requirement-estimation-system/
```

#### 步骤2：传输到目标服务器

```bash
# 使用scp传输
scp requirement-estimation-system.tar.gz user@target-server:/opt/

# 登录到目标服务器
ssh user@target-server

# 解压
cd /opt
tar xzf requirement-estimation-system.tar.gz
cd requirement-estimation-system
```

#### 步骤3：一键部署

```bash
# 配置环境变量
cp .env.example .env
# 编辑.env，填入你的API Key
vim .env

# 添加执行权限并运行
chmod +x deploy.sh
./deploy.sh
```

完成！访问 `http://target-server-ip` 即可使用。

---

## 使用Docker Compose（推荐给运维人员）

### 1. 准备配置文件

确保以下文件存在：
- `.env` - 环境变量配置
- `system_list.csv` - 主系统列表（可选，首次运行时自动创建）
- `backend/subsystem_list.csv` - 子系统映射（可选，首次运行时自动创建）

### 2. 启动服务

```bash
# 构建镜像
docker-compose build

# 启动服务（后台运行）
docker-compose up -d

# 查看运行状态
docker-compose ps
```

### 3. 查看日志

```bash
# 查看所有服务日志
docker-compose logs -f

# 只查看后端日志
docker-compose logs -f backend

# 只查看前端日志
docker-compose logs -f frontend
```

### 4. 停止和重启

```bash
# 停止服务
docker-compose stop

# 重启服务
docker-compose restart

# 完全删除容器
docker-compose down
```

---

## 无Docker环境的部署

### 方式一：直接运行

```bash
# 后端
nohup python3 backend/app.py > logs/backend.log 2>&1 &

# 前端（需要先build）
cd frontend
npm run build
# 然后使用Nginx或Apache托管build目录
```

### 方式二：使用Systemd管理

```bash
# 复制服务文件
sudo cp deployment/requirement-api.service /etc/systemd/system/

# 启动服务
sudo systemctl start requirement-api
sudo systemctl enable requirement-api
```

---

## 常见问题

### Q1: Docker构建失败？
A: 检查网络连接，使用国内镜像源：
```bash
# 修改Dockerfile，使用清华源
RUN pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### Q2: 前端无法访问后端API？
A: 检查防火墙设置，确保443端口开放：
```bash
sudo firewall-cmd --add-port=443/tcp --permanent
sudo firewall-cmd --reload
```

### Q3: 如何更新系统？
A:
```bash
# 拉取最新代码
git pull

# 重新构建并启动
docker-compose down
./deploy.sh
```

### Q4: 数据如何备份？
A:
```bash
# 备份配置和数据
tar czf backup-$(date +%Y%m%d).tar.gz \
    system_list.csv \
    backend/subsystem_list.csv \
    backend/config/cosmic_config.json \
    data/

# 恢复
tar xzf backup-20260105.tar.gz
```

---

## 端口说明

- **80端口**：前端Web界面
- **443端口**：后端API服务

确保目标服务器的防火墙已开放这些端口。

---

## 下一步

部署完成后，建议：

1. **配置HTTPS**：使用Let's Encrypt获取免费SSL证书
2. **设置域名**：配置域名解析到服务器IP
3. **配置备份**：设置定时备份任务
4. **监控告警**：配置服务监控和告警

详细说明请参考 `DEPLOYMENT.md`
