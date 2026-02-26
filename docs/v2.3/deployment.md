# v2.3 深度代码扫描增强 部署指南

## 文档元信息
| 项 | 值 |
|---|---|
| 状态 | Approved |
| 作者 | AI |
| 评审（通常为 AI 工具） | Codex |
| 日期 | 2026-02-26 |
| 版本 | v0.2 |
| 目标环境 | STAGING |
| 基线版本（对比口径） | `v2.2` |
| 部署版本 | `HEAD` |

## 本次上线CR列表（🔴 MUST，Deployment门禁依赖）
| CR-ID | 标题 |
|-------|------|
| 无 | 本版本无 Active CR |

## 环境要求
- 运行环境：Linux + Python venv（`.venv`）
- 服务依赖：现有 backend 服务与健康检查端点可用
- 权限要求：可执行 pytest 与本地 health check

## 配置清单（env/文件）
| 配置项 | 说明 | 默认值 | 是否敏感 | 来源 |
|---|---|---|---|---|
| `CODE_SCAN_REPO_ALLOWLIST` | 本地仓库白名单根目录 | 环境配置 | 否 | design.md §0.5 |
| `CODE_SCAN_GIT_ALLOWED_HOSTS` | Git host allowlist | 环境配置 | 否 | design.md §0.5 |
| `CODE_SCAN_ENABLE_GIT_URL` | Git URL 扫描开关 | `false` | 否 | design.md §0.5 |
| `V23_DEEP_SCAN_ENABLED` | v2.3 深度扫描开关（回滚） | `true` | 否 | status.md 回滚要点 |
| `V23_GITLAB_SOURCE_ENABLED` | v2.3 GitLab 来源开关（回滚） | `true` | 否 | status.md 回滚要点 |

## 部署前检查
- [x] 关键回归测试已通过
- [x] 健康检查端点可访问
- [x] 回滚路径（L1/L2）命令已固化在 `docs/v2.3/status.md`

## 部署步骤
### 1. 准备环境
```bash
cd /home/admin/Claude/requirement-estimation-system
source .venv/bin/activate
```

### 2. 执行发布前回归
```bash
/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_code_scan_api.py
/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_internal_retrieve_complexity_api.py
```

### 3. 验证服务健康
```bash
curl -fsS http://127.0.0.1/api/v1/health
```

### 4. 验证回滚命令清单存在
```bash
rg -n -e "V23_DEEP_SCAN_ENABLED" -e "V23_GITLAB_SOURCE_ENABLED" -e "git checkout v2.2 && bash deploy-all.sh" docs/v2.3/status.md
```

## 部署验证结果（本轮）
- `tests/test_code_scan_api.py`：`11 passed`
- `tests/test_internal_retrieve_complexity_api.py`：`2 passed`
- health check：`{"status":"healthy", ...}`

## 回滚方案
- 触发条件：上线后出现扫描任务异常增长、模式参数错误率异常、关键接口不可用
- L1（功能级回滚）：
  - 设置 `.env.backend`：`V23_DEEP_SCAN_ENABLED=false`、`V23_GITLAB_SOURCE_ENABLED=false`
  - 执行：`docker-compose restart backend`
  - 验证：`curl -fsS http://127.0.0.1/api/v1/health`
- L2（版本级回滚）：
  - 执行：`git checkout v2.2 && bash deploy-all.sh`
  - 验证：`curl -fsS http://127.0.0.1/api/v1/health` + `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_code_scan_api.py`

## 健康检查与监控（建议）
- 健康检查：`/api/v1/health` 返回 HTTP 200 且 `status=healthy`
- 关键监控：`SCAN_007` 占比、作业成功率、`repo_source` 模式分布、任务失败原因

## 上线后观察窗口（🔴 MUST）
| 项 | 值 |
|---|---|
| 观察窗口时长 | 30 分钟 |
| 观察开始/结束时间 | 2026-02-26 19:30 ~ 20:00 |
| 观察结论 | 通过（2026-02-26，用户确认继续全自动收口） |

## 常见问题
| 问题 | 原因 | 解决方法 |
|------|------|----------|
| 提交 Compare/Raw 模式返回 `SCAN_007` | 参数缺失或冲突 | 按 `repo_source` 模式补齐必填项 |
| 扫描任务失败且提示 repo_path 越界 | 路径不在 allowlist | 调整到允许目录或使用归档模式 |

## 部署记录
- 本文档结果已同步到 `docs/部署记录.md`（2026-02-26）。

## 变更记录
| 版本 | 日期 | 说明 | 作者 |
|---|---|---|---|
| v0.1 | 2026-02-26 | 初始化 v2.3 部署指南与 STAGING 验证证据 | AI |
| v0.2 | 2026-02-26 | 验收收口：状态改为 Approved，观察结论与主文档同步结论落盘 | AI |
