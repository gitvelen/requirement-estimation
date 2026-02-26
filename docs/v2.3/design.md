# 需求评估系统 v2.3 技术方案设计

## 文档信息
| 项 | 值 |
|---|---|
| 状态 | Draft |
| 作者 | AI + User |
| 评审 | - |
| 日期 | 2026-02-26 |
| 版本号 | `v2.3` |
| 关联提案 | `docs/v2.3/proposal.md` |
| 关联需求 | `docs/v2.3/requirements.md` |
| 关联主文档 | `docs/技术方案设计.md` |
| 关联接口 | `backend/api/code_scan_routes.py` |

---

## 0. 摘要（Executive Summary）
v2.3 在不改变现有部署形态与主流程接口的前提下，对代码扫描链路做“深度化 + 可追溯”增强。核心实现点：
1. 在 `code_scan_service` 内新增结构化分析产物（AST 摘要、调用关系、服务依赖、数据流、复杂度、影响面）。
2. 扫描结果契约统一扩展为 `items + analysis + metrics`，供 UI/Agent/测试统一消费。
3. `code_scan` 接口新增 `repo_source` 模式语义（`local/archive/gitlab_archive/gitlab_compare/gitlab_raw`）与参数校验。
4. 保留现有权限边界（owner/B 角 + 创建者约束）与错误码模型，新增 `SCAN_007` 处理模式参数冲突。

## 0.5 决策记录（Design 前置收集结果）
### 技术决策
| 编号 | 决策项 | 用户选择 | 理由/备注 |
|---|---|---|---|
| D-01 | 后端语言/框架 | Python + FastAPI（沿用） | 避免架构迁移风险 |
| D-02 | 扫描核心落点 | `backend/service/code_scan_service.py` 增强 | 最小改动、复用现有任务状态机 |
| D-03 | AST 方案 | 轻量 AST 摘要（正则+结构树） | 先达成可用与可测，再迭代全语法解析 |
| D-04 | GitLab 三模式 | 统一 `repo_source` 契约 + 参数门禁 | 与现有本地/归档能力兼容 |
| D-05 | 部署形态 | 不变 | 满足 REQ-C005 |

### 环境配置
| 配置项 | 开发环境 | 生产环境 | 敏感 | 备注 |
|---|---|---|---|---|
| `CODE_SCAN_REPO_ALLOWLIST` | 可配置 | 必配 | 否 | 本地路径边界 |
| `CODE_SCAN_GIT_ALLOWED_HOSTS` | 可配置 | 必配 | 否 | Git host allowlist |
| `CODE_SCAN_ENABLE_GIT_URL` | `false` 默认 | 按环境开启 | 否 | Git URL 能力开关 |
| GitLab Token | 环境变量 | Secret 注入 | 是 | 不落盘 |

## 1. 背景、目标、非目标与约束
### 1.1 背景与问题
- 现有扫描结果以入口条目为主，深度语义不足，导致误识别率下降空间有限。
- 结果契约目前偏“条目列表”，无法稳定承载覆盖率/影响面等指标。
- Git 场景存在模式语义缺失，难以对齐 Archive/Compare/Raw 三种业务入口。

### 1.2 目标（Goals，可验收）
- G1：实现 `capability_item` 到评估链路的稳定供给（REQ-001）。
- G2：产出可消费的深度分析结构（REQ-002/003/004/007）。
- G3：形成 GitLab 三模式统一参数与错误处理（REQ-005）。
- G4：保留回滚与边界防护，不扩大风险面（REQ-008、REQ-C001~005）。

### 1.3 非目标（Non-Goals）
- 不新增独立图谱页面。
- 不引入新数据库/消息中间件。
- 不改变角色体系和部署拓扑。

### 1.4 关键约束（Constraints）
- 安全边界不放宽：路径、权限、密钥、输入校验必须保持或增强。
- 兼容旧接口：`/run` `/status` `/result` `/commit` 行为可继续使用。
- 失败可降级但不可静默：必须有错误码和可追踪信息。

### 1.5 关键假设（Assumptions）
| 假设 | 可验证方式 | 失效影响 | 兜底策略 |
|---|---|---|---|
| 现有 `capability_item` 检索链路可复用 | `tests/test_internal_retrieve_complexity_api.py` | 链路断开 | 保留降级标识并补兜底检索 |
| 扫描任务状态机可承载新模式 | `tests/test_code_scan_api.py` | 模式不可用 | 增加参数门禁与降级 |
| 现有结果消费方可兼容扩展字段 | 兼容性回归 | 上游解析失败 | 新增字段保持可选，旧字段不破坏 |

## 2. 需求对齐与验收口径（Traceability）
### 2.1 需求-设计追溯矩阵（必须）
<!-- TRACE-MATRIX-BEGIN -->
| REQ-ID | 需求摘要 | 设计落点（章节/模块/API/表） | 验收方式/证据 |
|---|---|---|---|
| REQ-001 | `capability_item` 评估链路打通 | §4.3, §5.1（CodeScanService->commit/retrieve） | `tests/test_internal_retrieve_complexity_api.py` |
| REQ-002 | AST 解析替换关键正则路径 | §5.2（AstLiteAnalyzer） | `tests/test_code_scan_api.py` 新增用例 |
| REQ-003 | 深度扫描产物生成 | §5.2（analysis builders） | 扫描结果结构断言 |
| REQ-004 | 影响面分析 | §5.3（Impact Builder） | Compare/变更样例断言 |
| REQ-005 | GitLab 三模式扫描能力 | §5.4（repo_source adapter + API-001） | 三模式任务回归 |
| REQ-006 | 最小前端接入证据摘要 | §5.5（EvidenceSummary 契约） | 接口字段断言 |
| REQ-007 | 扫描结果统一输出契约 | §5.6（ResultContract v2） | 兼容性与字段完整性测试 |
| REQ-008 | 双路径回滚能力与演练 | §6.1（Runbook） | 回滚命令验证 |
| REQ-101 | 误识别率改进可证明 | §7（测试计划） | 指标脚本 + 测试报告 |
| REQ-102 | M1-M5 覆盖门槛 | §5.7（metrics producer） | 指标输出校验 |
| REQ-103 | M6 稳定性门槛 | §5.4, §7 | 三模式通过率统计 |
| REQ-C001~005 | 禁止项与边界 | §5.8（安全）+ §6（回滚） | REQ-C 对抗性验证 |
<!-- TRACE-MATRIX-END -->

### 2.2 质量属性与典型场景（Quality Scenarios）
| Q-ID | 质量属性 | 场景描述 | 目标/阈值 | 验证方式 |
|---|---|---|---|---|
| Q-01 | 稳定性 | 三模式任务并发提交 | 任务状态正确、失败可追踪 | API 回归 |
| Q-02 | 可观测性 | 扫描完成后出指标 | M1-M6 字段完整 | 结果契约断言 |
| Q-03 | 安全性 | 非法路径/越权访问 | 返回拒绝与错误码 | 负向测试 |

## 3. 现状分析与方案选型（Options & Trade-offs）
### 3.1 现状与问题定位
- `code_scan_service` 当前主要输出 `items`，深度语义和统一指标不足。
- `repo_source` 已存在 local/archive/git 基础，但缺乏三模式业务语义和参数门禁。

### 3.2 方案候选与对比
| 方案 | 核心思路 | 优点 | 缺点/风险 | 成本 | 结论 |
|---|---|---|---|---|---|
| A | 新建独立深度扫描服务 | 解耦彻底 | 范围过大、发布风险高 | 高 | 不采用 |
| B | 在现有 `code_scan_service` 内增强 | 变更最小、可快速验证 | 需要控制复杂度 | 中 | 采用 |

### 3.3 关键技术选型与新增依赖评估
| 组件/依赖 | 选型 | 理由 | 替代方案 | 安全评估 | 备注 |
|---|---|---|---|---|---|
| AST 摘要 | 轻量结构解析（内建） | 避免新增重依赖 | tree-sitter/javalang | 无新增供应链风险 | 后续可升级 |
| GitLab 模式 | 统一 `repo_source` 契约 | 与现有接口兼容 | 新开三套 API | 低 | 先保契约一致 |

## 4. 总体设计（High-level Design）
### 4.1 系统上下文与边界
| 依赖方/系统 | 用途 | 协议 | 失败模式 | 降级/兜底 |
|---|---|---|---|---|
| code_scan_routes | 任务入口/状态/入库 | HTTP | 参数错误/权限失败 | 错误码返回 |
| code_scan_service | 扫描执行与结果组织 | 进程内调用 | 解析失败 | 降级产物 + 失败统计 |
| vector_store | capability_item 入库与检索 | SDK | embedding异常 | EMB_001 + 不污染状态 |
| retrieve API | 评估输入构建 | HTTP | 检索异常 | degraded=true |

### 4.2 架构概述
1. API 层解析 `repo_source` 与参数，统一创建 ScanJob。
2. 服务层执行扫描并生成 `items + analysis + metrics`。
3. 入库层将 `capability_item` 及必要 metadata 写入向量库。
4. retrieve 接口将 capability 与文档、ESB 合并输出给 Agent。

### 4.3 变更影响面（Impact Analysis）
| 影响面 | 是否影响 | 说明 | 需要迁移/兼容 |
|---|---|---|---|
| API 契约 | 是 | `POST /code-scan/jobs` 支持 `repo_source` 参数族 | 向后兼容（旧参数仍可用） |
| 存储结构 | 否 | 仅结果 JSON 扩展字段 | 无 DB 迁移 |
| 权限与审计 | 是 | 强化模式参数与权限拒绝路径 | 兼容原有规则 |
| 前端交互 | 轻微 | 仅消费新增摘要字段 | 不新增页面 |

## 5. 详细设计（Low-level Design）
### 5.1 模块分解与职责
| 模块 | 职责 | 关键接口 |
|---|---|---|
| `code_scan_routes.py` | 参数解析、权限、错误码映射 | API-001/002/003 |
| `code_scan_service.py` | 扫描执行、分析产物、结果契约 | `run_scan`, `_scan_repo`, `get_result` |
| `routes.py` retrieve | 组合 capability/document/esb | `/internal/system-profiles/retrieve` |

### 5.2 深度分析产物设计
- `analysis.ast_summary`: 文件级节点统计（class/method/import）
- `analysis.call_graph`: 调用边列表（caller->callee）与覆盖统计
- `analysis.service_dependencies`: feign/http/mq/dubbo 依赖关系
- `analysis.data_flow`: 读写关系摘要（entity->operations）
- `analysis.complexity`: 方法级 CC/WMC 与汇总

### 5.3 影响面分析设计
- 输入：变更文件集合（Compare/Raw 模式可带入）
- 输出：
  - `impact.systems[]`
  - `impact.features[]`
  - `impact.apis[]`
  - 每项附 `evidence`（file/line/source）

### 5.4 GitLab 三模式设计
- `repo_source` 枚举：`local/archive/gitlab_archive/gitlab_compare/gitlab_raw`
- 参数门禁：
  - 模式缺参/冲突 => `SCAN_007`
  - 非法来源 => `SCAN_001/004/005/006` 按现有语义
- 任务状态机保持不变（queued/running/completed/failed/timeout）

### 5.5 证据摘要契约（给 UI）
- `evidence_summary` 最小字段：
  - `m1_chain_reachability`
  - `m2_m5_coverages`
  - `m6_gitlab_pass_rate`
  - `impact_summary`
  - `updated_at`
  - `source`

### 5.6 扫描结果契约（ResultContract v2）
```json
{
  "system_id": "sys_x",
  "system_name": "X",
  "generated_at": "ISO8601",
  "items": [],
  "analysis": {
    "ast_summary": {},
    "call_graph": {},
    "service_dependencies": {},
    "data_flow": {},
    "complexity": {},
    "impact": {}
  },
  "metrics": {
    "m1": 0.0,
    "m2": 0.0,
    "m3": 0.0,
    "m4": 0.0,
    "m5": 0.0,
    "m6": 0.0
  }
}
```

### 5.7 指标产出设计
- M1：在 retrieve + evaluate 链路记录 capability 命中统计
- M2-M5：扫描时计算并随结果输出
- M6：按 `repo_source` 模式聚合任务通过率和成功率

### 5.8 安全设计（REQ-C）
| 禁止项 | 防护措施 | 验证方式 |
|---|---|---|
| REQ-C001 | 发布前必须有误识别率证据 | test_report 门禁 |
| REQ-C002 | L1/L2 回滚 runbook 与演练 | 回滚验证记录 |
| REQ-C003 | 不新增独立页面，仅扩字段 | 前端路由检查 |
| REQ-C004 | 路径/权限/模式参数校验 | API 负向测试 |
| REQ-C005 | 不新增重型依赖与部署组件 | 依赖/部署清单审查 |

## 6. 环境与部署（Environments & Deployment）
### 6.1 发布、迁移与回滚
- 兼容策略：旧接口兼容，新增字段可选。
- 上线步骤：先灰度启用 `V23_DEEP_SCAN_ENABLED`，验证指标后放量。
- 回滚：
  - L1：关闭 `V23_DEEP_SCAN_ENABLED` + `V23_GITLAB_SOURCE_ENABLED`
  - L2：`git checkout v2.2 && bash deploy-all.sh`

## 7. 测试与验收计划（Test Plan）
| TEST-ID | 对应 REQ-ID | 用例说明 | 类型 | 证据 |
|---|---|---|---|---|
| TEST-001 | REQ-001 | capability_item 进入 retrieve 链路 | integration | `tests/test_internal_retrieve_complexity_api.py` |
| TEST-002 | REQ-002/003 | 扫描结果包含 analysis 结构 | integration | `tests/test_code_scan_api.py` |
| TEST-003 | REQ-005/103 | 三模式任务创建与完成 | integration | `tests/test_code_scan_api.py` |
| TEST-004 | REQ-C004 | 非法参数/越权拒绝 | integration | `tests/test_code_scan_api.py` |
| TEST-005 | REQ-008/C002 | 回滚命令可执行性 | manual | `test_report.md` 回滚块 |

## 8. 风险与开放问题
### 8.1 风险清单
| 风险 | 影响 | 概率 | 缓解措施 |
|---|---|---|---|
| 轻量 AST 精度不足 | 指标波动 | 中 | 先可测可用，再迭代 parser |
| GitLab 模式参数歧义 | 接口误用 | 中 | `SCAN_007` + 参数矩阵 |
| 指标口径漂移 | 验收争议 | 中 | 统一 `metrics` 输出和脚本 |

### 8.2 开放问题
- 无（requirements 中 3 项开放问题已收敛并在 §6 对齐）。

## 10. 变更记录
| 版本 | 日期 | 修改章节 | 说明 | 作者 |
|---|---|---|---|---|
| v0.1 | 2026-02-26 | 初始化 | 完成 v2.3 设计初稿 | AI |
