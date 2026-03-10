# ESB 导入 HTTP 400 错误修复 - 交付清单

## 修复版本
- 版本：v2.6-hotfix-esb-embedding
- 日期：2026-03-10
- 类型：Hotfix（热修复）

## 问题描述
内网服务器环境导入 ESB 服务治理文档时遇到 HTTP 400 Bad Request 错误，原因是 embedding 批次大小（默认 25 条/批）导致单次请求的文本总量超过内网 embedding API 限制。

## 修复方案
添加可配置的 ESB embedding 批次大小参数 `ESB_EMBEDDING_BATCH_SIZE`，默认值为 10（从原来的 25 降低）。

## 代码变更

### 1. backend/config/config.py
- 位置：第 68-69 行
- 变更：添加配置项 `ESB_EMBEDDING_BATCH_SIZE`
- 默认值：10

### 2. backend/service/esb_service.py
- 位置：第 499 行
- 变更：使用可配置的批次大小参数
- 修改前：`embeddings = embedding_service.batch_generate_embeddings(texts)`
- 修改后：`embeddings = embedding_service.batch_generate_embeddings(texts, batch_size=settings.ESB_EMBEDDING_BATCH_SIZE)`

## 交付文件

### 核心文件
1. **esb_embedding_batch_fix.patch** - Git 补丁文件（推荐使用）
2. **ESB_FIX_README.md** - 详细修复指南（包含原理说明、应用方法、验证步骤）
3. **QUICKSTART_ESB_FIX.md** - 快速修复指南（精简版）
4. **verify_esb_fix.py** - 配置验证脚本

### 已修改的代码文件
- backend/config/config.py
- backend/service/esb_service.py

## 应用步骤（在内网服务器执行）

### 快速版本
```bash
# 1. 应用补丁
cd /path/to/requirement-estimation-system
patch -p1 < esb_embedding_batch_fix.patch

# 2. 配置环境变量
echo "ESB_EMBEDDING_BATCH_SIZE=10" >> .env

# 3. 重启服务
docker-compose restart backend

# 4. 验证
python3 verify_esb_fix.py
```

### 详细步骤
参见 `ESB_FIX_README.md` 或 `QUICKSTART_ESB_FIX.md`

## 配置说明

### 环境变量
- **名称**：`ESB_EMBEDDING_BATCH_SIZE`
- **类型**：整数
- **默认值**：10
- **推荐范围**：5-15
- **说明**：ESB 导入时每批发送给 embedding API 的条目数量

### 调优建议
- **保守配置**（字段较长）：`ESB_EMBEDDING_BATCH_SIZE=5`
- **默认配置**（推荐）：`ESB_EMBEDDING_BATCH_SIZE=10`
- **激进配置**（字段较短）：`ESB_EMBEDDING_BATCH_SIZE=20`

## 验证方法

### 1. 配置验证
```bash
python3 verify_esb_fix.py
```

### 2. 功能验证
- 重新导入之前失败的 ESB 文档
- 观察日志中无 HTTP 400 错误
- 检查导入统计数量正确
- 通过 ESB 搜索功能验证数据可检索

### 3. 日志验证
```bash
docker logs -f requirement-backend 2>&1 | grep -i "embedding\|esb\|batch"
```
应该看到类似：`Embedding批量调用: ... batch_size=10`

## 回滚方案

### L1：代码回滚
```bash
git checkout backend/config/config.py backend/service/esb_service.py
sed -i '/ESB_EMBEDDING_BATCH_SIZE/d' .env
docker-compose restart backend
```

### L2：调整批次大小
如果 batch_size=10 仍失败，降低到 5 或 3：
```bash
sed -i 's/ESB_EMBEDDING_BATCH_SIZE=10/ESB_EMBEDDING_BATCH_SIZE=5/' .env
docker-compose restart backend
```

### L3：临时绕过
将 ESB 文档按系统拆分成多个小文件，分批导入。

## 风险评估
- **风险等级**：低
- **影响范围**：仅 ESB 导入功能
- **兼容性**：向后兼容，小文档仍可正常导入
- **性能影响**：分批处理会增加总耗时（更多 API 调用），但避免了 400 错误

## 测试建议
1. 使用之前失败的 ESB 文档进行测试
2. 测试不同规模的 ESB 文档（小、中、大）
3. 验证导入后的数据完整性和可检索性
4. 监控导入耗时，必要时调整批次大小

## 后续优化
1. 根据内网 embedding API 实际性能调优 batch_size
2. 考虑根据文本长度动态调整批次大小
3. 为超大 ESB 文档提供拆分导入指南
4. 添加导入进度显示和错误重试机制

## 联系方式
如有问题，请联系技术支持团队或查看项目文档。

---
**注意**：本修复需要在用户的内网服务器上应用，当前外网 STAGING 服务器已完成代码修改，可作为参考。
