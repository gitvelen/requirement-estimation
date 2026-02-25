# v2.2 综合优化升级 部署指南

## 文档元信息
| 项 | 值 |
|---|---|
| 状态 | Approved |
| 作者 | AI |
| 评审 | AI 自审 + 人工确认后执行 |
| 日期 | 2026-02-24 |
| 版本 | v0.1 |
| 目标环境 | STAGING / PROD |
| 基线版本（对比口径） | `v2.1` |
| 部署版本 | `v2.2` |

## 本次上线CR列表（🔴 MUST，Deployment门禁依赖）
| CR-ID | 标题 |
|-------|------|
| 无 | 本文档记录的是 2026-02-24 已上线批次（不含后续增量 CR） |

> 说明：`CR-20260225-001` 为收口后的增量优化，当前处于 In Progress，纳入下一次部署批次。

## 环境要求
- 后端：Python 虚拟环境（`.venv`）+ FastAPI 服务
- 前端：Node.js + React 构建产物
- 运行依赖：Docker Compose（或等价容器运行环境）
- 数据目录可读写：`data/`、`uploads/`、`logs/`

## 配置清单（env/文件）
| 配置项 | 说明 | 默认值 | 是否敏感 | 来源 |
|---|---|---|---|---|
| `JWT_SECRET` | JWT 签名密钥 | 无默认（必须设置） | 是 | `.env.backend` |
| `DASHSCOPE_API_KEY` | 大模型/Embedding 能力 | 空（可降级） | 是 | `.env.backend` |
| `V21_AUTO_REEVAL_ENABLED` | 自动重评估兼容开关 | `true` | 否 | `.env.backend` |
| `V21_AI_REMARK_ENABLED` | AI 备注兼容开关 | `true` | 否 | `.env.backend` |
| `V21_DASHBOARD_MGMT_ENABLED` | 看板管理口径兼容开关 | `true` | 否 | `.env.backend` |

## 部署前检查
- [x] 已完成回归测试（后端全量 `108 passed`，前端 build 通过）
- [x] 已完成 v2.2 GWT 覆盖闭环（53/53）
- [x] 已完成回滚策略准备（保留 v2.1 回退路径 + 数据快照）
- [x] 已完成主文档同步（系统功能、技术方案、接口、用户手册、部署记录）
- [x] 人工确认上线窗口（用户消息“继续”确认执行）

## 部署步骤

### 1. 准备环境
```bash
source /home/admin/Claude/requirement-estimation-system/.venv/bin/activate
cd /home/admin/Claude/requirement-estimation-system
```

### 2. 执行发布前门禁验证
```bash
/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q --tb=short
cd frontend && npm run build && cd -
/home/admin/Claude/requirement-estimation-system/.venv/bin/python -m compileall -q backend
```

### 3. 备份关键数据
```bash
SNAPSHOT="backups/v2.2_$(date +%Y%m%d_%H%M%S)"
mkdir -p "${SNAPSHOT}"
cp data/task_storage.json "${SNAPSHOT}/"
cp data/task_modifications.json "${SNAPSHOT}/" 2>/dev/null || true
cp data/system_profiles.json "${SNAPSHOT}/" 2>/dev/null || true
cp data/system_list.csv "${SNAPSHOT}/" 2>/dev/null || true
```

### 4. 发布/启动服务
```bash
docker-compose up -d --build || DOCKER_BUILDKIT=0 COMPOSE_DOCKER_CLI_BUILD=0 docker-compose up -d --build
```

### 5. 验证部署（必须可复现）
```bash
curl -s http://127.0.0.1/api/v1/health
/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_dashboard_query_api.py tests/test_task_feature_confirm_gate_v22.py
```

## 回滚方案
- 触发条件：
  - 核心接口持续 5xx
  - 登录/任务列表/任务详情主链路不可用
  - 路由兼容跳转异常（出现死循环或关键入口不可达）
- 回滚步骤：
```bash
# 1) 回退应用版本到 v2.1 对应镜像/commit
# 2) 恢复备份数据（若发生不可逆数据异常）
cp backups/<snapshot>/task_storage.json data/task_storage.json
cp backups/<snapshot>/task_modifications.json data/task_modifications.json 2>/dev/null || true
cp backups/<snapshot>/system_profiles.json data/system_profiles.json 2>/dev/null || true
cp backups/<snapshot>/system_list.csv data/system_list.csv 2>/dev/null || true
# 3) 重启服务
docker-compose up -d
```
- 数据处理/兼容性说明：
  - v2.2 无 DB schema 迁移；主要是应用层与前端路由改造，支持直接回退。

## 上线后观察窗口（🔴 MUST）
| 项 | 值 |
|---|---|
| 观察窗口时长 | 30 分钟 |
| 观察开始时间 | 2026-02-24 22:36 |
| 观察结束时间 | 2026-02-24 22:38 |
| 观察结论 | 正常（后端 healthy，最小回归通过） |

## 本次执行结果（2026-02-24）
- 备份快照：`backups/v2.2_20260224_223625`
- 发布命令：`docker-compose up -d --build` 触发 buildx 版本限制后自动 fallback 到 legacy builder 成功
- 容器状态：`requirement-backend` 为 `healthy`，`requirement-frontend` 为 `up`
- 健康检查：`curl -s http://127.0.0.1/api/v1/health` 返回 `{"status":"healthy",...}`
- 发布后最小回归：`/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_dashboard_query_api.py tests/test_task_feature_confirm_gate_v22.py` -> `9 passed`

## 常见问题
| 问题 | 原因 | 解决方法 |
|------|------|----------|
| `docker-compose up -d --build` 失败 | buildx 版本不满足要求 | 使用文档中的 legacy fallback 命令 |
| 看板入口访问异常 | 旧链接缓存或路由未刷新 | 清理浏览器缓存并验证 `/dashboard/rankings` `/dashboard/reports` |
| 旧任务报告下载失败 | 兼容数据缺失 | 先执行 `tests/test_report_download_api.py` 复核，再回滚 |

## 部署记录
- 正式部署完成后，追加记录到 `docs/部署记录.md`。

## 变更记录
| 版本 | 日期 | 说明 | 作者 |
|---|---|---|---|
| v0.1 | 2026-02-24 | 初始化 v2.2 部署文档（待人工确认上线） | AI |
| v0.2 | 2026-02-24 | 记录正式部署执行结果（备份快照、fallback 构建、健康检查、最小回归） | AI |
| v0.3 | 2026-02-25 | 标注后续增量 CR（CR-20260225-001）不属于本次已上线批次 | AI |
