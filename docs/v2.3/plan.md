# 需求评估系统 v2.3 任务计划

## 文档元信息
| 项 | 值 |
|---|---|
| 状态 | In Progress |
| 日期 | 2026-02-26 |
| 版本 | v0.1 |
| 基线版本（对比口径） | `v2.2` |
| Active CR（如有） | 无 |
| 关联设计 | `docs/v2.3/design.md` |
| 关联需求 | `docs/v2.3/requirements.md` |
| 关联状态 | `docs/v2.3/status.md` |

## 里程碑
| 里程碑 | 交付物 | 截止日期 |
|---|---|---|
| M1 | 扫描契约与三模式参数门禁完成（T001-T002） | 2026-02-26 |
| M2 | 深度分析产物与指标输出完成（T003） | 2026-02-26 |
| M3 | 测试补齐与证据固化完成（T004-T007） | 2026-02-26 |

## Definition of Done（DoD）
- [ ] 需求可追溯：任务关联 `REQ/SCN/API/TEST` 清晰
- [ ] 代码可运行：扫描主流程不破坏；支持回滚
- [ ] 自测通过：关键测试命令全部可复现
- [ ] 安全合规：权限与输入边界无回退
- [ ] 文档同步：review/test/deployment 所需文档补齐

## 禁止项引用索引（来源：requirements.md REQ-C）
| REQ-C ID | 一句话摘要 |
|---|---|
| REQ-C001 | 无可证明误识别率改善证据不得上线 |
| REQ-C002 | 无回滚能力不得上线 |
| REQ-C003 | 不得新增独立图谱可视化页面 |
| REQ-C004 | 不得放宽输入边界与权限约束 |
| REQ-C005 | 不得引入重型基础设施或改变部署形态 |

## 任务概览
状态标记：`待办` / `进行中` / `已完成`

| 任务分类 | 任务ID | 任务名称 | 优先级 | 预估工时 | Owner | Reviewer | 关联需求项 | 任务状态 | 依赖任务ID | 验证方式 | 里程碑 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| API/契约 | T001 | 三模式参数门禁与错误码 `SCAN_007` | P0 | 1h | Codex | Codex | REQ-005/007/C004 | 待办 | - | `pytest -q tests/test_code_scan_api.py -k mode` | M1 |
| 服务 | T002 | `repo_source` 模式落地与任务生命周期对齐 | P0 | 1h | Codex | Codex | REQ-005/103 | 待办 | T001 | `pytest -q tests/test_code_scan_api.py -k code_scan` | M1 |
| 服务 | T003 | 深度分析产物与统一结果契约 `analysis+metrics` | P0 | 2h | Codex | Codex | REQ-002/003/004/007/102 | 待办 | T001 | `pytest -q tests/test_code_scan_api.py -k analysis` | M2 |
| 集成 | T004 | capability 链路稳定性与 retrieve 证据补测 | P1 | 1h | Codex | Codex | REQ-001/006 | 待办 | T003 | `pytest -q tests/test_internal_retrieve_complexity_api.py` | M3 |
| 测试 | T005 | 三模式与边界负向测试补齐 | P1 | 1h | Codex | Codex | REQ-005/103/C004 | 待办 | T002 | `pytest -q tests/test_code_scan_api.py` | M3 |
| 文档 | T006 | implementation/review/testing 文档证据落盘 | P1 | 1h | Codex | Codex | REQ-008/C001/C002 | 待办 | T004,T005 | 文档审查命令 `rg` | M3 |
| 验证 | T007 | 回滚命令与健康检查可复现验证 | P1 | 0.5h | Codex | Codex | REQ-008/C002 | 待办 | T006 | `curl/pytest` 命令记录 | M3 |

## 任务详情

### T001: 三模式参数门禁与错误码 `SCAN_007`
**分类**：API/契约  
**优先级**：P0  
**预估工时**：1h  
**关联需求项**：REQ-005、REQ-007、REQ-C004  
**任务描述**：
- 在 `POST /api/v1/code-scan/jobs` 增加 `repo_source` 参数解析
- 固化模式参数矩阵（local/archive/gitlab_archive/gitlab_compare/gitlab_raw）
- 缺参/冲突统一返回 `SCAN_007`
**影响面/修改范围**：
- `backend/api/code_scan_routes.py`
- `tests/test_code_scan_api.py`
**验收标准**：
- [ ] 非法模式参数返回 `SCAN_007`
- [ ] 旧入参（不传 `repo_source`）保持兼容
**验证方式**：
- 命令：`pytest -q tests/test_code_scan_api.py -k "scan and (invalid or mode)"`  

### T002: `repo_source` 生命周期对齐
**分类**：服务  
**优先级**：P0  
**预估工时**：1h  
**关联需求项**：REQ-005、REQ-103  
**任务描述**：
- 在 `code_scan_service` 扩展模式值并保持任务状态机一致
- job payload 返回 `repo_source`
**影响面/修改范围**：
- `backend/service/code_scan_service.py`
- `backend/api/code_scan_routes.py`
**验收标准**：
- [ ] 三模式作业均可创建并完成/失败可追踪
- [ ] `GET /jobs/{job_id}` 返回模式信息
**验证方式**：
- 命令：`pytest -q tests/test_code_scan_api.py -k "mode or idempotency"`  

### T003: 深度分析产物与统一结果契约
**分类**：服务  
**优先级**：P0  
**预估工时**：2h  
**关联需求项**：REQ-002、REQ-003、REQ-004、REQ-007、REQ-102  
**任务描述**：
- 在扫描结果中输出 `analysis`（ast/call_graph/deps/data_flow/complexity/impact）
- 输出 `metrics`（M2-M5 基础统计）
**影响面/修改范围**：
- `backend/service/code_scan_service.py`
- `tests/test_code_scan_api.py`
**验收标准**：
- [ ] 完成任务结果包含 `analysis` 与 `metrics`
- [ ] 失败任务仍返回可解析错误结构
**验证方式**：
- 命令：`pytest -q tests/test_code_scan_api.py -k "analysis or result"`  

### T004: capability 链路稳定性补测
**分类**：集成  
**优先级**：P1  
**预估工时**：1h  
**关联需求项**：REQ-001、REQ-006  
**任务描述**：
- 增强 retrieve 相关测试，确保 capability 条目可被检索并作为上下文输出
**影响面/修改范围**：
- `tests/test_internal_retrieve_complexity_api.py`
**验收标准**：
- [ ] retrieve 返回中 `capabilities` 非空（已入库条件下）
**验证方式**：
- 命令：`pytest -q tests/test_internal_retrieve_complexity_api.py`  

### T005: 三模式与边界负向测试
**分类**：测试  
**优先级**：P1  
**预估工时**：1h  
**关联需求项**：REQ-005、REQ-103、REQ-C004  
**任务描述**：
- 增加 gitlab 模式正常/异常参数用例
- 保持既有 SCAN_004/005/006 与 AUTH_001 行为
**影响面/修改范围**：
- `tests/test_code_scan_api.py`
**验收标准**：
- [ ] 新增用例通过且不破坏既有用例
**验证方式**：
- 命令：`pytest -q tests/test_code_scan_api.py`  

### T006: 实现与测试文档落盘
**分类**：文档  
**优先级**：P1  
**预估工时**：1h  
**关联需求项**：REQ-008、REQ-C001、REQ-C002  
**任务描述**：
- 产出 `review_implementation.md`、`test_report.md`、`review_testing.md`
- 填写机器可读摘要块
**影响面/修改范围**：
- `docs/v2.3/review_implementation.md`
- `docs/v2.3/test_report.md`
- `docs/v2.3/review_testing.md`
**验收标准**：
- [ ] 文档包含可复现命令与结论
**验证方式**：
- 命令：`rg -n "REVIEW-SUMMARY-BEGIN|TEST-COVERAGE-MATRIX-BEGIN" docs/v2.3/*.md`  

### T007: 回滚验证
**分类**：验证  
**优先级**：P1  
**预估工时**：0.5h  
**关联需求项**：REQ-008、REQ-C002  
**任务描述**：
- 执行回滚命令可行性检查并记录证据
**影响面/修改范围**：
- `docs/v2.3/test_report.md`
**验收标准**：
- [ ] L1/L2 命令与验证步骤可复现
**验证方式**：
- 命令：`curl -fsS http://127.0.0.1/api/v1/health`、`pytest -q tests/test_code_scan_api.py`  

## 执行顺序
1. T001 → T002 → T003
2. T004 → T005
3. T006 → T007

## 风险与缓解
| 风险 | 影响 | 概率 | 缓解措施 |
|---|---|---|---|
| 三模式与现有入参冲突 | 影响兼容性 | 中 | 默认 `repo_source=local`，旧参数继续可用 |
| 深度分析逻辑复杂度上升 | 扫描稳定性下降 | 中 | 先输出轻量可观测产物，逐步增强 |
| 测试耗时增加 | 交付延迟 | 中 | 先跑 targeted，再跑全量 code_scan 相关 |

## 开放问题
- 无（requirements 中开放问题已关闭）。

## 变更记录
| 版本 | 日期 | 说明 |
|---|---|---|
| v0.1 | 2026-02-26 | 初始化 v2.3 任务计划 |
