# v2.1 多模块 UI/UX 优化与功能增强 部署指南

## 文档元信息
| 项 | 值 |
|---|---|
| 状态 | Approved |
| 作者 | AI |
| 评审 | - |
| 日期 | 2026-02-12 |
| 版本 | v0.1 |
| 目标环境 | STAGING / PROD |
| 基线版本（对比口径） | `v2.0` |
| 部署版本 | `v2.1` |

## 本次上线CR列表（🔴 MUST，Deployment门禁依赖）
| CR-ID | 标题 |
|-------|------|
| 无 | 本版本未启用 CR 流程 |

## 环境要求
- 后端：Python 虚拟环境 + FastAPI 服务
- 前端：Node.js 20 + React 构建产物
- 数据：`data/` 目录可读写（重点：`task_storage.json`、`task_modifications.json`、`system_profiles.json`、`system_list.csv`）

## 配置清单（env/文件）
| 配置项 | 说明 | 默认值 | 是否敏感 | 来源 |
|---|---|---|---|---|
| `V21_AUTO_REEVAL_ENABLED` | 保存后自动触发重评估 | `true` | 否 | `.env.backend` |
| `V21_AI_REMARK_ENABLED` | AI 自动备注 | `true` | 否 | `.env.backend` |
| `V21_DASHBOARD_MGMT_ENABLED` | 看板管理驱动指标 | `true` | 否 | `.env.backend` |

## 部署前检查
- [x] 已完成备份（`task_storage.json` 备份恢复演练通过）
- [x] 监控与告警就绪（见 design.md 指标定义）
- [x] 回滚步骤可执行（hash 恢复验证通过）
- [x] Feature Flag 回退策略明确（3 个开关可关闭回退）

## 部署步骤

### 1. 准备环境
```bash
python -m venv .venv
source .venv/bin/activate
cd frontend && npm ci && cd -
```

### 2. 回归验证
```bash
.venv/bin/pytest -q
cd frontend && CI=true npm test -- --watchAll=false && npm run build
```

### 3. 备份关键数据
```bash
mkdir -p backups/v2.1_$(date +%Y%m%d_%H%M%S)
cp data/task_storage.json backups/.../
cp data/task_modifications.json backups/.../
cp data/system_profiles.json backups/.../ 2>/dev/null || true
cp data/system_list.csv backups/.../
```

### 4. 发布/启动服务
```bash
# 后端（示例）
./deploy-backend.sh

# 前端（示例）
./deploy-frontend.sh
```

### 5. 验证部署（必须可复现）
```bash
curl -s http://<host>/api/v1/system/config/feature-flags
curl -s -X POST http://<host>/api/v1/efficiency/dashboard/query -H "Content-Type: application/json" -d '{"page":"ai","perspective":"executive","filters":{"time_range":"last_30d"}}'
```

## 回滚方案
- 触发条件：核心 API 5xx 持续、权限异常、看板指标异常、系统清单为空
- 回滚步骤：
```bash
# 1) 关闭 v2.1 新行为
# V21_AUTO_REEVAL_ENABLED=false
# V21_AI_REMARK_ENABLED=false
# V21_DASHBOARD_MGMT_ENABLED=false

# 2) 回退服务版本（按发布系统执行）

# 3) 恢复关键数据快照
cp backups/<snapshot>/task_storage.json data/task_storage.json
cp backups/<snapshot>/task_modifications.json data/task_modifications.json
cp backups/<snapshot>/system_profiles.json data/system_profiles.json 2>/dev/null || true
cp backups/<snapshot>/system_list.csv data/system_list.csv
```

## 上线后观察窗口（🔴 MUST）
| 项 | 值 |
|---|---|
| 观察窗口时长 | 30 分钟 |
| 观察开始时间 | 2026-02-12 08:10 |
| 观察结束时间 | 2026-02-12 08:45 |
| 观察结论 | 正常（正式部署完成，健康检查通过） |

## 本次执行结果（2026-02-12）
- 实际发布命令：`docker-compose up -d --build`（buildx 版本不足后自动回退 legacy builder 并成功）
- 容器状态：`requirement-backend` `Up (healthy)`、`requirement-frontend` `Up`
- 健康检查：`curl http://127.0.0.1/api/v1/health` 返回 `{"status":"healthy",...}`
- 发布后验证：后端全量 `86 passed`，前端测试 `4 passed`，前端构建 `Compiled successfully`

## 常见问题
| 问题 | 原因 | 解决方法 |
|------|------|----------|
| 看板查询返回 `invalid_perspective` | 前端未按角色映射 perspective | 按 manager/expert/other 映射 owner/expert/executive |
| 系统画像保存失败 `invalid_module_structure` | `module_structure` 非数组或子项格式错误 | 按 v2.1 结构（module_name + functions[]）提交 |

## 部署记录
部署完成后同步 `docs/部署记录.md` 并记录版本与验证结果。

## 变更记录
| 版本 | 日期 | 说明 | 作者 |
|---|---|---|---|
| v0.1 | 2026-02-12 | 初始化 Deployment 文档，包含回滚策略与可复现验证命令 | AI |
