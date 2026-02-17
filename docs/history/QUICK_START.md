# 快速启动指南（本期：本地知识库，无 Milvus/MinIO）

本期知识库采用**本地文件向量库**实现，不依赖 Redis/MinIO/Milvus：
- 向量数据：`data/knowledge_store.json`
- 指标与日志：`data/knowledge_metrics.json`、`data/knowledge_retrieval_logs.json`

## 1) 配置

```bash
cp .env.example .env
```

编辑 `.env`，至少配置：
```bash
DASHSCOPE_API_KEY=sk-your-key
KNOWLEDGE_VECTOR_STORE=local
```

> 不配置 `DASHSCOPE_API_KEY` 也能启动系统，但知识库导入/检索会不可用（Embedding 需要该Key）。

## 2) 启动

```bash
docker-compose up -d --build
```

## 3) 验证

```bash
curl http://localhost:443/api/v1/health
```

访问：
- 前端：`http://localhost`
- 知识库管理：`http://localhost/knowledge`

## 4) 下一期启用 Milvus/MinIO（提示）

下一期如果要切换为服务化向量库（Milvus/MinIO），建议单独启用相关服务并将 `KNOWLEDGE_VECTOR_STORE` 切换为 `milvus`；可参考 `docker-compose.milvus.yml` 与 `deploy-milvus.sh`（本期不启用）。

## 🎯 验收策略

### 阶段1：基础功能验收（现在可做）✅

**验收项目**：
- ✅ Docker服务启动
- ✅ API健康检查
- ✅ 前端访问
- ✅ 需求评估流程
- ✅ 系统识别功能
- ✅ 功能拆分功能
- ✅ 工作量估算
- ✅ 报告生成

**命令**：
```bash
# 1. 启动服务
docker-compose up -d backend frontend

# 2. 测试
curl http://localhost/api/v1/health

# 3. 访问
# http://your-server-ip
```

### 阶段2：知识库功能验收（稍后完成）

**前置条件**：
- ⏳ MinIO镜像下载完成
- ⏳ etcd + MinIO + Milvus 启动

**验收项目**：
- 知识库文档导入
- 知识检索功能
- 效果评估指标
- Agent知识库集成

**验收命令**：
```bash
# 1. 下载MinIO
docker pull minio/minio:RELEASE.2023-03-20T20-16-18Z

# 2. 启动完整服务
docker-compose --profile milvus up -d

# 3. 验收测试
python scripts/knowledge_acceptance.py
```

## 💡 临时解决方案

如果急需知识库功能，可以考虑：

### 选项1：使用本地文件系统

修改Milvus配置为使用本地存储（不推荐生产环境）

### 选项2：使用云存储服务

如果企业有对象存储服务（如OSS、S3），可以配置Milvus使用云存储

### 选项3：先交付基础功能

- ✅ 基础评估功能完全可用
- ✅ 知识库功能可以后续升级
- ✅ 系统架构支持平滑升级

## 📝 总结

**现状**：
- 所有代码100%实现 ✅
- Docker配置完成 ✅
- 文档齐全 ✅
- MinIO待下载 ⏳

**建议**：
1. **立即行动**：先验收基础评估功能
2. **后续优化**：网络稳定后部署Milvus
3. **平滑升级**：不影响现有功能

**降级机制**：
```python
# 系统自动检测并降级
if knowledge_available:
    使用知识库增强评估
else:
    使用传统方式评估（功能不受影响）
```

---

## 🚀 快速命令

```bash
# 测试基础功能（推荐）
cd /home/admin/Claude/requirement-estimation-system
docker-compose up -d backend frontend

# 查看服务状态
docker ps

# 查看日志
docker logs -f requirement-backend

# 测试API
curl http://localhost/api/v1/health
```

---

**建议先进行基础功能验收，等网络稳定后再补充MinIO和完整知识库功能！** 🎯
