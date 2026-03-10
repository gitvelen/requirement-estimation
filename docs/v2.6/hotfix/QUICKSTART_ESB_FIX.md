# ESB 导入 HTTP 400 错误快速修复指南

## 问题
内网服务器导入 ESB 文档时出现 HTTP 400 Bad Request 错误。

## 原因
embedding 批次大小（默认 25）导致单次请求超过内网 API 限制。

## 快速修复（在内网服务器执行）

### 步骤 1：应用补丁
```bash
cd /path/to/requirement-estimation-system
patch -p1 < esb_embedding_batch_fix.patch
```

### 步骤 2：配置环境变量
```bash
# 方式 A：修改 .env
echo "ESB_EMBEDDING_BATCH_SIZE=10" >> .env

# 方式 B：修改 docker-compose.yml
# 在 backend 服务的 environment 部分添加：
#   - ESB_EMBEDDING_BATCH_SIZE=10
```

### 步骤 3：重启服务
```bash
docker-compose restart backend
```

### 步骤 4：验证
```bash
# 验证配置
docker exec requirement-backend /app/.venv/bin/python -c "from backend.config.config import settings; print(f'ESB_EMBEDDING_BATCH_SIZE={settings.ESB_EMBEDDING_BATCH_SIZE}')"

# 重新导入 ESB 文档，观察日志
docker logs -f requirement-backend
```

## 调优

如果仍然失败，降低批次大小：
```bash
ESB_EMBEDDING_BATCH_SIZE=5  # 或 3
```

如果成功但速度慢，可以增加：
```bash
ESB_EMBEDDING_BATCH_SIZE=15  # 或 20
```

## 回滚
```bash
git checkout backend/config/config.py backend/service/esb_service.py
sed -i '/ESB_EMBEDDING_BATCH_SIZE/d' .env
docker-compose restart backend
```

## 详细文档
参见 `ESB_FIX_README.md`
