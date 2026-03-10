# v2.6 版本发布说明

## 版本信息
- **版本号**: v2.6
- **发布日期**: 2026-03-10
- **基线版本**: v2.5
- **变更级别**: Major

## 核心功能

### 1. 文档分块处理（CR-20260309-001）
为适配内网 LLM Token 限制，新增智能文档分块处理能力。

**主要特性：**
- Token 感知的文档分块（支持 Qwen3-32B 32K 上下文限制）
- 段落级智能重叠，保持语义完整性
- 多轮调用结果深度合并
- 可配置的分块开关（`ENABLE_LLM_CHUNKING`）

**影响模块：**
- `backend/utils/token_counter.py` - 新增 Token 计数工具
- `backend/utils/llm_client.py` - 扩展分块调用能力
- `backend/service/profile_summary_service.py` - 重构为分块处理
- `backend/config/config.py` - 新增 Token 限制配置

**配置参数：**
- `LLM_MAX_CONTEXT_TOKENS`: 模型最大上下文（默认 32000）
- `LLM_INPUT_MAX_TOKENS`: 单次输入上限（默认 25000）
- `LLM_CHUNK_OVERLAP_PARAGRAPHS`: 重叠段落数（默认 2）
- `ENABLE_LLM_CHUNKING`: 分块开关（默认 true）

### 2. ESB 导入优化（Hotfix）
修复内网环境 ESB 导入时的 HTTP 400 错误。

**问题原因：**
- Embedding 批次大小（默认 25）超过内网 API Token 限制

**解决方案：**
- 新增可配置参数 `ESB_EMBEDDING_BATCH_SIZE`（默认 10）
- 用户可根据实际环境调整批次大小（推荐范围 5-15）

**修改文件：**
- `backend/config/config.py` - 添加批次大小配置
- `backend/service/esb_service.py` - 使用可配置批次大小

**配置参数：**
- `ESB_EMBEDDING_BATCH_SIZE`: ESB embedding 批次大小（默认 10）

## 测试结果

### 后端测试
- 单元测试：210 passed
- 覆盖率：92%
- 新增测试：
  - `tests/test_token_counter.py` - Token 计数与分块逻辑
  - `tests/test_llm_client.py` - 分块调用与结果合并
  - `tests/test_profile_summary_service.py` - 超长文档处理

### 前端测试
- 编译状态：Compiled successfully
- 无功能变更，向后兼容

### 集成测试
- STAGING 环境验收通过
- ESB 导入修复验证通过

## 部署说明

### 环境要求
- Python 3.9+
- 内网 LLM：Qwen3-32B（32K 上下文）
- 内网 Embedding：Qwen3-Embedding-8B

### 配置更新

**必需配置（内网环境）：**
```bash
# Token 限制配置
LLM_MAX_CONTEXT_TOKENS=32000
LLM_INPUT_MAX_TOKENS=25000
ENABLE_LLM_CHUNKING=true

# ESB 导入配置
ESB_EMBEDDING_BATCH_SIZE=10
```

**可选配置：**
```bash
# 分块重叠段落数（默认 2）
LLM_CHUNK_OVERLAP_PARAGRAPHS=2
```

### 部署步骤

1. **拉取最新代码**
   ```bash
   git pull origin master
   ```

2. **更新环境配置**
   ```bash
   # 编辑 .env 文件，添加上述配置
   vim .env
   ```

3. **重启服务**
   ```bash
   docker-compose restart backend
   ```

4. **验证部署**
   ```bash
   # 检查配置加载
   docker exec requirement-backend /app/.venv/bin/python -c "from backend.config.config import settings; print(f'ENABLE_LLM_CHUNKING={settings.ENABLE_LLM_CHUNKING}, ESB_EMBEDDING_BATCH_SIZE={settings.ESB_EMBEDDING_BATCH_SIZE}')"

   # 查看服务日志
   docker logs -f requirement-backend
   ```

## 回滚方案

### L1：配置级回滚
关闭分块功能，回退到单次调用模式：
```bash
# 修改 .env
ENABLE_LLM_CHUNKING=false

# 重启服务
docker-compose restart backend
```

### L2：代码级回滚
回退到 v2.5 版本：
```bash
git checkout v2.5
docker-compose up -d --build
```

### L3：ESB 批次调整
如果 ESB 导入仍失败，降低批次大小：
```bash
# 修改 .env
ESB_EMBEDDING_BATCH_SIZE=5  # 或 3

# 重启服务
docker-compose restart backend
```

## 已知问题与限制

1. **Token 估算精度**
   - 使用启发式估算（字符数 / 2.5），可能与实际 Token 数有偏差
   - 已预留 1000 tokens 安全边界

2. **分块性能**
   - 超长文档分块调用会增加总耗时
   - 仅在超限时触发，正常文档无影响

3. **ESB 批次大小**
   - 默认值 10 适用于大多数场景
   - 如遇 400 错误，需根据实际环境调整

## 文档更新

- ✅ `docs/技术方案设计.md` - 已同步分块处理方案
- ✅ `docs/接口文档.md` - 已更新配置参数说明
- ✅ `docs/部署记录.md` - 已添加 v2.6 部署记录
- ✅ `docs/v2.6/deployment.md` - 详细部署指南
- ✅ `docs/v2.6/hotfix/` - ESB 修复文档与补丁

## 贡献者
- User - 需求提出与验收
- Claude Opus 4.6 - 设计、开发与测试

## 下一步计划
- 监控分块调用性能与准确性
- 根据实际使用情况优化 Token 估算算法
- 收集用户反馈，规划 v2.7 功能

---
**注意**: 本版本已在 STAGING 环境验收通过，建议在生产环境部署前进行充分测试。
