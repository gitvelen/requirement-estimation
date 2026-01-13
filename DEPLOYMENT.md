# 需求评估系统 - 部署指南

## 环境要求

### 开发环境
- Python 3.10+
- Node.js 16+
- 通义千问API Key

### 生产环境（Docker）
- Docker 20.10+
- Docker Compose 2.0+

---

## 方案一：Docker部署（推荐）

### 1. 准备工作

```bash
# 克隆项目到目标服务器
git clone <repository-url> /opt/requirement-estimation-system
cd /opt/requirement-estimation-system
```

### 2. 配置环境变量

编辑 `.env` 文件：

```bash
# 通义千问API配置
DASHSCOPE_API_KEY=your-api-key-here

# 服务配置
HOST=0.0.0.0
PORT=443
DEBUG=False
WORKERS=4

# 文件路径
UPLOAD_DIR=uploads
REPORT_DIR=data
```

### 3. 一键部署

```bash
# 添加执行权限
chmod +x deploy.sh

# 执行部署
./deploy.sh
```

### 4. 访问系统

- 前端地址: `http://your-server-ip`
- 后端API: `http://your-server-ip/api/v1`

### 5. 常用命令

```bash
# 查看日志
docker-compose logs -f backend
docker-compose logs -f frontend

# 重启服务
docker-compose restart

# 停止服务
docker-compose down

# 更新代码后重新部署
git pull
docker-compose down
./deploy.sh
```

---

## 方案二：手动部署

### 1. 前端部署

```bash
cd frontend

# 安装依赖
npm install

# 生产环境打包
npm run build

# 使用Nginx托管静态文件
sudo cp -r build/* /var/www/html/
```

### 2. 后端部署

```bash
# 安装Python依赖
pip3 install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑.env文件，填入真实配置

# 使用Systemd管理服务
sudo cat > /etc/systemd/system/requirement-api.service << 'EOF'
[Unit]
Description=Requirement Estimation API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/requirement-estimation-system
ExecStart=/usr/bin/python3 backend/app.py
Restart=always
Environment=PATH=/usr/bin:/usr/local/bin

[Install]
WantedBy=multi-user.target
EOF

# 启动服务
sudo systemctl daemon-reload
sudo systemctl start requirement-api
sudo systemctl enable requirement-api
```

---

## 方案三：使用Gunicorn + Nginx（生产级）

### 1. 后端使用Gunicorn

```bash
# 安装Gunicorn
pip install gunicorn

# 启动服务
gunicorn backend.app:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:443
```

### 2. Nginx配置

```nginx
upstream backend {
    server 127.0.0.1:443;
}

server {
    listen 80;
    server_name your-domain.com;

    # 前端
    location / {
        root /var/www/html;
        try_files $uri $uri/ /index.html;
    }

    # 后端API
    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_read_timeout 300;
    }
}
```

---

## 数据迁移

### 1. 导出配置数据

```bash
# 导出主系统配置
cp system_list.csv system_list.csv.backup

# 导出子系统配置
cp backend/subsystem_list.csv backend/subsystem_list.csv.backup

# 导出COSMIC配置
cp backend/config/cosmic_config.json backend/config/cosmic_config.json.backup
```

### 2. 导入到新环境

```bash
# 恢复配置文件
scp system_list.csv.backup user@new-server:/opt/requirement-estimation-system/
scp backend/subsystem_list.csv.backup user@new-server:/opt/requirement-estimation-system/backend/subsystem_list.csv
```

---

## 端口说明

| 服务 | 端口 | 说明 |
|------|------|------|
| 前端 | 80 | HTTP访问 |
| 后端 | 443 | API服务 |

**防火墙配置**：

```bash
# 开放端口
sudo firewall-cmd --permanent --add-port=80/tcp
sudo firewall-cmd --permanent --add-port=443/tcp
sudo firewall-cmd --reload
```

---

## 性能优化建议

### 1. 后端优化

- 根据CPU核心数调整worker数量：`WORKERS=CPU核心数*2+1`
- 启用Uvicorn的多进程模式
- 配置反向代理（Nginx）

### 2. 前端优化

- 启用CDN加速静态资源
- 配置Gzip压缩
- 设置浏览器缓存

### 3. 数据库（可选）

当前使用内存存储，生产环境建议使用Redis：

```python
# 安装Redis
pip install redis

# 修改config.py使用Redis存储任务状态
```

---

## 监控和日志

### 日志文件

- 后端日志: `logs/backend.log`
- 前端日志: `logs/frontend.log`

### 日志轮转

```bash
# 创建logrotate配置
sudo cat > /etc/logrotate.d/requirement-api << 'EOF'
/opt/requirement-estimation-system/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
}
EOF
```

---

## 故障排查

### 1. 后端启动失败

```bash
# 检查日志
tail -f logs/backend.log

# 检查端口占用
lsof -i :443
```

### 2. 前端无法访问

```bash
# 检查Nginx状态
sudo systemctl status nginx

# 查看Nginx错误日志
sudo tail -f /var/log/nginx/error.log
```

### 3. API请求失败

- 检查后端服务是否运行
- 检查防火墙规则
- 检查API Key配置

---

## 更新部署

```bash
# 1. 备份数据
cp -r data data.backup
cp system_list.csv system_list.csv.backup

# 2. 拉取最新代码
git pull

# 3. 重新部署（Docker）
docker-compose down
./deploy.sh

# 4. 验证更新
curl http://localhost/api/v1/health
```

---

## 安全建议

1. **修改默认端口**：避免使用默认的80/443
2. **配置HTTPS**：使用Let's Encrypt免费证书
3. **限制访问**：配置防火墙白名单
4. **定期备份**：自动备份配置和数据
5. **API密钥管理**：使用环境变量，不要硬编码

---

## 技术支持

遇到问题请查看：
1. 日志文件：`logs/backend.log` 和 `logs/frontend.log`
2. 项目文档：`memory.md`
3. GitHub Issues
