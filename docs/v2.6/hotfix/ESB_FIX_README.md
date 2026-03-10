# ESB 导入 HTTP 400 错误修复指南

## 问题描述

在内网服务器环境导入 ESB 服务治理文档时遇到 HTTP 400 Bad Request 错误：
```
HTTP Request: POST http://10.73.254.200:3000/v1/cr... HTTP/1 400 Bad Request
```

**根本原因：** ESB 导入时 embedding 批次大小（默认 25 条/批）导致单次请求的文本总量超过内网 embedding API 限制。

## 修复方案

本次修复添加了可配置的 ESB embedding 批次大小参数，默认值为 10（从原来的 25 降低），可根据实际环境调整。

### 修改内容

1. **backend/config/config.py** - 添加配置项 `ESB_EMBEDDING_BATCH_SIZE`
2. **backend/service/esb_service.py** - 使用可配置的批次大小

## 应用修复（在内网服务器上执行）

### 方法 1：使用 patch 命令（推荐）

```bash
cd /path/to/requirement-estimation-system

# 应用补丁
patch -p1 < esb_embedding_batch_fix.patch

# 验证修改
git diff backend/config/config.py backend/service/esb_service.py
```

### 方法 2：手动修改

**步骤 1：修改 backend/config/config.py**

在第 66 行（`KNOWLEDGE_SIMILARITY_THRESHOLD` 之后）添加：

```python
    # ESB embedding 批次大小配置
    ESB_EMBEDDING_BATCH_SIZE: int = int(os.getenv("ESB_EMBEDDING_BATCH_SIZE", "10"))
```

**步骤 2：修改 backend/service/esb_service.py**

找到第 499 行，将：
```python
embeddings = embedding_service.batch_generate_embeddings(texts)
```

改为：
```python
embeddings = embedding_service.batch_generate_embeddings(texts, batch_size=settings.ESB_EMBEDDING_BATCH_SIZE)
```

## 配置环境变量

根据部署方式选择以下方法之一：

### 方式 A：修改 .env 文件

```bash
echo "ESB_EMBEDDING_BATCH_SIZE=10" >> .env
```

### 方式 B：修改 docker-compose.yml

在 backend 服务的 environment 部分添加：
```yaml
services:
  backend:
    environment:
      - ESB_EMBEDDING_BATCH_SIZE=10
```

### 方式 C：修改 .env.backend（如果使用）

```bash
echo "ESB_EMBEDDING_BATCH_SIZE=10" >> .env.backend
```

## 重启服务

```bash
# Docker Compose 部署
docker-compose restart backend

# 或强制重建
docker-compose up -d --force-recreate backend

# Systemd 部署
systemctl restart requirement-backend
```

## 验证修复

### 1. 验证配置是否生效

```bash
docker exec requirement-backend /app/.venv/bin/python -c "from backend.config.config import settings; print(f'ESB_EMBEDDING_BATCH_SIZE={settings.ESB_EMBEDDING_BATCH_SIZE}')"
```

预期输出：`ESB_EMBEDDING_BATCH_SIZE=10`

### 2. 查看服务日志

```bash
docker logs -f requirement-backend 2>&1 | grep -i "embedding\|esb\|batch"
```

### 3. 重新导入 ESB 文档

- 通过前端界面重新上传之前失败的 ESB 文档
- 观察日志中应该看到类似：`Embedding批量调用: ... batch_size=10`
- 确认无 HTTP 400 错误
- 检查导入统计（imported 数量）

### 4. 功能验证

- 导入成功后，通过 ESB 搜索功能验证数据可检索
- 检查导入的服务数量是否与文档行数一致

## 配置调优

如果仍然出现问题或需要优化性能，可以调整 `ESB_EMBEDDING_BATCH_SIZE` 的值：

### 保守配置（适合字段较长的 ESB 文档）
```bash
ESB_EMBEDDING_BATCH_SIZE=5
```

### 默认配置（推荐）
```bash
ESB_EMBEDDING_BATCH_SIZE=10
```

### 激进配置（适合字段较短的 ESB 文档）
```bash
ESB_EMBEDDING_BATCH_SIZE=20
```

**调优建议：**
- 如果仍然出现 400 错误，降低到 5 或 3
- 如果导入成功但速度慢，可以尝试增加到 15 或 20
- 根据内网 embedding API 的实际限制调整（通常 Qwen3-Embedding-8B 支持约 2048 tokens/请求）

## 回滚方法

如果修改后出现问题，可以回滚：

```bash
# 恢复代码（如果使用了 git）
git checkout backend/config/config.py backend/service/esb_service.py

# 移除环境变量
sed -i '/ESB_EMBEDDING_BATCH_SIZE/d' .env

# 重启服务
docker-compose restart backend
```

## 技术说明

### 修改前
- ESB 导入调用 `batch_generate_embeddings(texts)` 使用默认 batch_size=25
- 每批 25 条 × 平均每条 100-200 字符 = 2500-5000 字符 ≈ 1250-2500 tokens
- 可能超过内网 embedding API 的单次请求限制（通常 2048 tokens）

### 修改后
- ESB 导入调用 `batch_generate_embeddings(texts, batch_size=10)` 使用可配置的批次大小
- 每批 10 条 × 平均每条 100-200 字符 = 1000-2000 字符 ≈ 500-1000 tokens
- 在 embedding API 限制范围内，避免 HTTP 400 错误

### 性能影响
- 分批处理会增加总耗时（更多 API 调用）
- 但避免了 400 错误导致的完全失败
- 可根据实际环境调整批次大小以平衡性能和稳定性

## 后续优化建议

1. **监控与调优：** 根据内网 embedding API 的实际性能，调整最优 batch_size
2. **智能分批：** 未来可根据文本长度动态调整批次大小
3. **文档拆分指导：** 为超大 ESB 文档提供拆分导入的用户指南

## 支持

如有问题，请联系技术支持团队或查看项目文档。
