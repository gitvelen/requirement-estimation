# 部署文档

## Docker 部署方式

项目提供两种部署方式，根据需求选择：

### 方式一：基础部署（不包含知识库功能）

适用于不需要知识库功能的场景，资源占用更少。

```bash
# 启动服务（不启动Milvus）
docker-compose up -d

# 查看状态
docker-compose ps
```

**启动的服务**：
- ✓ backend - 后端服务
- ✓ frontend - 前端服务
- ✗ Milvus - 不启动

### 方式二：完整部署（包含知识库功能）

适用于需要知识库功能的场景，提供完整的AI增强评估能力。

```bash
# 启动所有服务（包括Milvus）
docker-compose --profile milvus up -d

# 查看状态
docker-compose ps
```

**启动的服务**：
- ✓ backend - 后端服务
- ✓ frontend - 前端服务
- ✓ etcd - Milvus元数据存储
- ✓ minio - Milvus对象存储
- ✓ milvus - 向量数据库

### 方式三：生产环境部署

推荐使用 `docker-compose.prod.yml` 进行生产部署：

```bash
# 使用生产配置启动（默认包含Milvus）
docker-compose -f docker-compose.prod.yml up -d

# 查看状态
docker-compose -f docker-compose.prod.yml ps
```

## 部署步骤

### 1. 准备工作

```bash
# 克隆项目
git clone <repository-url>
cd requirement-estimation-system

# 检查配置文件
ls -la docker-compose*.yml
```

### 2. 选择部署方式

#### 基础部署（快速启动，无知识库）

```bash
# 构建并启动
docker-compose up -d --build

# 查看日志
docker-compose logs -f backend
```

#### 完整部署（包含知识库）

```bash
# 构建并启动（包含Milvus）
docker-compose --profile milvus up -d --build

# 等待Milvus启动（约1-2分钟）
docker-compose logs -f milvus

# 查看所有服务状态
docker-compose ps
```

### 3. 验证部署

```bash
# 检查服务健康状态
curl http://localhost/api/v1/health

# 检查Milvus（如果启动）
curl http://localhost:9091/healthz

# 访问前端
# 浏览器打开: http://your-server-ip
```

### 4. 访问系统

- **主页**: `http://your-server-ip`
- **知识库管理**: `http://your-server-ip/knowledge`
- **API文档**: `http://your-server-ip/api/v1/health`

## 常用命令

### 启动服务

```bash
# 基础部署
docker-compose up -d

# 完整部署（包含Milvus）
docker-compose --profile milvus up -d
```

### 停止服务

```bash
docker-compose down
```

### 停止并清理数据

```bash
# 停止服务并删除容器
docker-compose down

# 删除所有数据卷（警告：会删除所有数据）
docker-compose down -v
```

### 查看日志

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend
docker-compose logs -f milvus
```

### 重启服务

```bash
# 重启所有服务
docker-compose restart

# 重启特定服务
docker-compose restart backend
docker-compose restart milvus
```

### 更新服务

```bash
# 拉取最新代码
git pull

# 重新构建并启动
docker-compose --profile milvus up -d --build
```

## 数据持久化

### 数据卷

项目使用Docker数据卷持久化以下数据：

```yaml
volumes:
  etcd_data:      # Milvus元数据
  minio_data:     # Milvus对象存储
  milvus_data:    # Milvus向量数据
```

### 备份数据

```bash
# 备份Milvus数据
docker run --rm \
  -v requirement-estimation-system_milvus_data:/data \
  -v $(pwd)/backup:/backup \
  alpine tar czf /backup/milvus-backup-$(date +%Y%m%d).tar.gz -C /data .

# 备份应用数据
tar czf backup/data-backup-$(date +%Y%m%d).tar.gz data/
```

### 恢复数据

```bash
# 恢复Milvus数据
docker run --rm \
  -v requirement-estimation-system_milvus_data:/data \
  -v $(pwd)/backup:/backup \
  alpine tar xzf /backup/milvus-backup-20250128.tar.gz -C /data

# 恢复应用数据
tar xzf backup/data-backup-20250128.tar.gz
```

## 配置说明

### 环境变量

在 `docker-compose.yml` 中可以配置以下环境变量：

```yaml
environment:
  - MILVUS_HOST=milvus           # Milvus主机地址
  - MILVUS_PORT=19530            # Milvus端口
  - KNOWLEDGE_ENABLED=true       # 是否启用知识库功能
```

### 网络配置

所有服务使用同一个Docker网络 `app-network`，确保服务间可以通信。

```yaml
networks:
  app-network:
    driver: bridge
```

## 性能优化

### 资源限制

如果需要限制资源使用，可以在 `docker-compose.yml` 中添加：

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

### Milvus配置

Milvus默认配置适用于中小规模场景（<100万条向量）。

如果需要处理更大规模数据，需要调整Milvus配置，详见：
https://milvus.io/docs/stable/configuremilvus.md

## 故障排查

### 1. Milvus启动失败

**问题**：Milvus容器启动失败或反复重启

**解决**：
```bash
# 查看Milvus日志
docker-compose logs milvus

# 检查依赖服务
docker-compose ps etcd minio

# 重启Milvus
docker-compose restart milvus
```

### 2. Backend无法连接Milvus

**问题**：Backend日志显示连接Milvus失败

**解决**：
```bash
# 检查Milvus是否启动
docker-compose ps milvus

# 检查网络连接
docker-compose exec backend ping milvus

# 检查Milvus健康状态
curl http://localhost:9091/healthz
```

### 3. 知识库功能不可用

**问题**：知识库页面显示错误

**解决**：
```bash
# 确认Milvus已启动
docker-compose --profile milvus up -d

# 检查环境变量
docker-compose exec backend env | grep KNOWLEDGE

# 查看后端日志
docker-compose logs -f backend | grep -i knowledge
```

## 升级部署

### 平滑升级

```bash
# 1. 备份数据
./scripts/backup.sh

# 2. 拉取最新代码
git pull

# 3. 停止服务（保留数据）
docker-compose down

# 4. 重新构建并启动
docker-compose --profile milvus up -d --build

# 5. 验证升级
curl http://localhost/api/v1/health
```

## 生产环境建议

### 1. 使用外部Milvus集群

对于生产环境，建议使用独立的Milvus集群，而不是Docker部署。

修改 `backend/config/config.py`:
```python
MILVUS_HOST = "your-milvus-cluster-host"
MILVUS_PORT = 19530
```

### 2. 数据备份

- 定期备份Milvus数据（每天）
- 定期备份应用数据（每周）
- 备份配置文件

### 3. 监控告警

- 监控服务健康状态
- 监控Milvus性能指标
- 设置告警规则

### 4. 安全加固

- 修改MinIO默认密码
- 配置Milvus认证
- 使用HTTPS访问
- 限制网络访问

## 技术支持

遇到问题请查看：
1. 项目日志：`docker-compose logs`
2. 系统文档：`README.md`
3. 知识库验收：`KNOWLEDGE_ACCEPTANCE.md`
