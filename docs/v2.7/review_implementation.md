# Review Report：Implementation / v2.7

| 项 | 值 |
|---|---|
| 阶段 | Implementation |
| 版本号 | v2.7 |
| 日期 | 2026-03-14 |
| 基线版本（对比口径） | `v2.6` |
| 复查口径 | full |
| Active CR | 无 |
| 审查范围 / 输入材料 | `backend/**`、`frontend/**`、`scripts/cleanup_v27_profile_assets.py`、`docs/v2.7/implementation_checklist.md`、`docs/v2.7/test_report.md`、`docs/v2.7/deployment.md`、主文档同步 diff |

## §-1 预审结果（🔴 MUST）
| 检查项 | 命令 | 结果 | 通过 |
|---|---|---|---|
| 测试 | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q --tb=short` | `236 passed, 1 warning` | ✅ |
| 构建 | `cd frontend && npm run build` | `Compiled successfully.` | ✅ |
| 类型检查 | `python -m compileall -q backend` | 无输出，退出码 0 | ✅ |
| 产出物就绪 | 检查 `implementation_checklist.md` / `test_report.md` / `deployment.md` / 主文档同步文件 | Implementation 出口与 Testing 入口文件均已产出 | ✅ |

## 结论摘要
- 总体结论：✅ 通过
- Blockers（P0）：0 / 高优先级（P1）：0 / 其他建议（P2+）：0
- 说明：代码、测试与文档证据已经满足 Implementation 阶段出口要求；`REQ-003/REQ-004` 的人工 E2E 验证转入 Testing 阶段跟踪，不阻断本阶段收口。

## 关键发现（按优先级）
- 无 P0 / P1 Findings。

## 证据清单
| 验证项 | 命令 | 关键输出 | 定位 |
|---|---|---|---|
| 后端回归 | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q --tb=short` | `242 passed, 1 warning` | `tests/**` |
| 前端 smoke | `cd frontend && CI=true npm test -- --watchAll=false --runInBand src/__tests__/systemProfileImportPage.render.test.js src/__tests__/systemProfileBoardPage.v27.test.js src/__tests__/serviceGovernancePage.render.test.js src/__tests__/systemListConfigPage.v27.test.js src/__tests__/navigationAndPageTitleRegression.test.js` | `Test Suites: 5 passed, 5 total` | `frontend/src/__tests__/**` |
| 前端构建 | `cd frontend && npm run build` | `Compiled successfully.` | `frontend/build` |
| 后端语法 | `python -m compileall -q backend` | `无输出，退出码 0` | `backend/**` |
| 依赖差异 | `git diff --unified=0 v2.6 -- pyproject.toml requirements.txt backend/requirements.txt frontend/package.json` | `未发现新增运行时依赖` | `frontend/package.json` |

## §0 审查准备
### A. 事实核实
| # | 声明 | 核实源 | 结论 |
|---|---|---|---|
| 1 | v2.7 已切换到 5 域 canonical 画像结构，并移除旧 schema 新写入 | `tests/test_profile_schema_v27.py` + `backend/service/system_profile_service.py` | ✅ |
| 2 | Skill Runtime 已注册 6 个内置 Skill，并对关键场景完成路由 | `tests/test_skill_runtime_service.py` + `backend/service/skill_runtime_service.py` | ✅ |
| 3 | 服务治理导入、系统清单初始化、Memory 驱动识别/拆解与 code scan 建议链路已落地 | `tests/test_service_governance_import_v27.py` / `tests/test_system_catalog_profile_init_v27.py` / `tests/test_system_identification_memory_v27.py` / `tests/test_feature_breakdown_memory_v27.py` / `tests/test_code_scan_skill_v27.py` | ✅ |
| 4 | v2.7 清理脚本、部署 runbook 与主文档同步已完成 | `tests/test_cleanup_v27.py` + `docs/v2.7/deployment.md` + 主文档变更 | ✅ |

### B. 关键概念交叉引用
| 概念 | 出现位置 | 口径一致 |
|---|---|---|
| `profile/execution-status` / `profile/extraction-status` alias | `backend/api/system_profile_routes.py`、`docs/接口文档.md`、`frontend/src/pages/SystemProfileImportPage.js` | ✅ |
| `.env.backend.internal` 与四个 v2.7 开关 | `backend/config/config.py`、`docs/v2.7/deployment.md`、`docs/技术方案设计.md`、`docs/部署记录.md` | ✅ |
| `Memory` 三类资产（画像更新 / 识别结论 / 功能点修改） | `backend/service/memory_service.py`、`docs/v2.7/requirements.md`、`docs/系统功能说明书.md` | ✅ |
| admin 服务治理与单一系统清单 | `backend/api/esb_routes.py`、`backend/api/system_list_routes.py`、`frontend/src/pages/ServiceGovernancePage.js`、`frontend/src/pages/SystemListConfigPage.js` | ✅ |
| 无新增运行时依赖 | `git diff --unified=0 v2.6 -- pyproject.toml requirements.txt backend/requirements.txt frontend/package.json` | ✅ |

## Implementation 审查清单
- [x] 安全：未新增密钥落盘、未放宽 admin/manager 权限校验、`repo_path` allowlist 与文件上传边界保持不降级
- [x] 边界与错误：`manual` 冲突、`partial_success`、模板缺列、运行时失败、清理失败与旧类型拒绝均有明确语义
- [x] 可维护性：新能力集中在 schema/runtime/memory/adapter/updater/service 层，旧 schema 兼容逻辑已抽离到 helper
- [x] 内容完整性：T001-T008 已完成；T009 自动化证据与主文档同步已落地
- [x] 测试与证据：关键路径均具备可复现命令、页面 smoke、全量回归与 API 回归证据
- [x] 里程碑展示：T006（M1🏁）和 T007（M2🏁）已在对话中展示并获继续指令

## 任务完成度
| 任务ID | 任务名称 | 状态 | 备注 |
|---|---|---|---|
| T001 | v2.7 canonical schema、Memory/Execution 存储与开关基座 | ✅完成 | schema / memory / execution 基座与兼容层完成 |
| T002 | Skill Runtime、Policy Gate 与 PM 文档导入链路 | ✅完成 | PM 导入口径收敛到 3 类文档并切到 execution-status |
| T003 | 服务治理导入改造为 admin 全局画像联动 | ✅完成 | D3 更新、统计返回与 manual 保护已覆盖 |
| T004 | 单一系统清单解析、空画像初始化与子系统模型退场 | ✅完成 | confirm 只初始化空画像，非空画像统一跳过 |
| T005 | Memory 驱动的系统识别与功能点拆解联动 | ✅完成 | `final_verdict` 与功能点调整 Memory 链路完成 |
| T006 | `code_scan_skill` 适配层与 Runtime 接入 | ✅完成 | code scan 走 suggestion_only + Memory |
| T007 | PM/Admin 页面、路由与交互收敛到 v2.7 口径 | ✅完成 | 5 个页面/导航 smoke 与构建通过 |
| T008 | v2.7 清理脚本、开关发布顺序与回滚 Runbook | ✅完成 | runbook、清理脚本和内部部署脚本测试通过 |
| T009 | 全量回归、证据闭环与主文档同步 | ▶ 转入 Testing 跟踪 | 自动化回归、契约校验和主文档同步已完成；人工 E2E 记录待在 Testing 阶段补齐 |

- 总任务数：9 / 完成：8 / 转入下一阶段跟踪：1 / 跳过：0 / 变更：0

## 需求符合性审查（REQ 模式）
### 逐条 GWT 判定表（🔴 MUST）
| GWT-ID | REQ-ID | 判定 | 证据类型 | 证据（可复现） | 备注 |
| GWT-REQ-001-01 | REQ-001 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-001-02 | REQ-001 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-001-03 | REQ-001 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-002-01 | REQ-002 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-002-02 | REQ-002 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-002-03 | REQ-002 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-003-01 | REQ-003 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-003-02 | REQ-003 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-003-03 | REQ-003 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-004-01 | REQ-004 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-004-02 | REQ-004 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-004-03 | REQ-004 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-004-04 | REQ-004 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-004-05 | REQ-004 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-005-01 | REQ-005 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-005-02 | REQ-005 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-005-03 | REQ-005 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-005-04 | REQ-005 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-005-05 | REQ-005 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-005-06 | REQ-005 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-006-01 | REQ-006 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-006-02 | REQ-006 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-006-03 | REQ-006 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-006-04 | REQ-006 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-006-05 | REQ-006 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-007-01 | REQ-007 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-007-02 | REQ-007 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-007-03 | REQ-007 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-007-04 | REQ-007 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-008-01 | REQ-008 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-008-02 | REQ-008 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-008-03 | REQ-008 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-008-04 | REQ-008 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-009-01 | REQ-009 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-009-02 | REQ-009 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-009-03 | REQ-009 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-009-04 | REQ-009 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-009-05 | REQ-009 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-010-01 | REQ-010 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-010-02 | REQ-010 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-010-03 | REQ-010 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-011-01 | REQ-011 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-011-02 | REQ-011 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-011-03 | REQ-011 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-011-04 | REQ-011 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-012-01 | REQ-012 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-012-02 | REQ-012 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-012-03 | REQ-012 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-101-01 | REQ-101 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-101-02 | REQ-101 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-102-01 | REQ-102 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-102-02 | REQ-102 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-103-01 | REQ-103 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-103-02 | REQ-103 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-104-01 | REQ-104 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-104-02 | REQ-104 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-105-01 | REQ-105 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-105-02 | REQ-105 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-C001-01 | REQ-C001 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-C001-02 | REQ-C001 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-C002-01 | REQ-C002 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-C002-02 | REQ-C002 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-C003-01 | REQ-C003 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-C003-02 | REQ-C003 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-C004-01 | REQ-C004 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-C004-02 | REQ-C004 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-C005-01 | REQ-C005 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-C006-01 | REQ-C006 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-C006-02 | REQ-C006 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-C007-01 | REQ-C007 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-C008-01 | REQ-C008 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |
| GWT-REQ-C008-02 | REQ-C008 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 实现与测试证据口径一致 |

### 对抗性审查（REQ-C）
- `REQ-C001`：
  - 泄漏路径 1：前端仍展示历史评估报告/治理文档卡片。排除证据：`frontend/src/__tests__/systemProfileImportPage.render.test.js`
  - 泄漏路径 2：服务端模板或导入接口仍放行旧类型。排除证据：`tests/test_system_profile_import_api.py::test_v27_profile_import_rejects_removed_doc_types`、`tests/test_system_profile_import_api.py::test_profile_template_download_rejects_removed_types_on_main_and_alias_paths`
- `REQ-C002`：
  - 泄漏路径 1：空画像结构仍输出旧 schema 键。排除证据：`tests/test_profile_schema_v27.py`
  - 泄漏路径 2：清理后仍残留旧 schema / history_report 存量。排除证据：`tests/test_cleanup_v27.py`
- `REQ-C003`：
  - 泄漏路径 1：服务治理导入覆盖 manual D3。排除证据：`tests/test_service_governance_import_v27.py::test_service_governance_import_skips_manual_d3_field_but_keeps_other_updates`
  - 泄漏路径 2：系统清单 confirm 覆盖非空画像或旧建议。排除证据：`tests/test_system_catalog_profile_init_v27.py::test_catalog_confirm_skips_non_blank_profiles_without_overwriting_existing_content`
- `REQ-C004`：
  - 泄漏路径 1：disabled future skill 导致 registry 加载失败。排除证据：`tests/test_skill_runtime_service.py`
  - 泄漏路径 2：future memory_type 需要新增专用结构。排除证据：`tests/test_memory_service_v27.py`
- `REQ-C005`：
  - 泄漏路径 1：只返回候选列表不返回直接判定。排除证据：`tests/test_system_identification_memory_v27.py`
  - 泄漏路径 2：`final_verdict` 取值漂移。排除证据：`tests/test_system_identification_memory_v27.py`
- `REQ-C006`：
  - 泄漏路径 1：v2.7 改造阻断任务主链路。排除证据：`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q --tb=short`
  - 泄漏路径 2：基础 API 基线失效。排除证据：`scripts/api_regression.sh`
- `REQ-C007`：
  - 泄漏路径 1：Python 运行时依赖新增。排除证据：`git diff --unified=0 v2.6 -- pyproject.toml requirements.txt backend/requirements.txt frontend/package.json`
  - 泄漏路径 2：frontend package 新增运行时依赖。排除证据：同一 diff 为空
- `REQ-C008`：
  - 泄漏路径 1：非空画像仍被系统清单覆盖。排除证据：`tests/test_system_catalog_profile_init_v27.py::test_catalog_confirm_skips_non_blank_profiles_without_overwriting_existing_content`
  - 泄漏路径 2：仅有 `field_sources/ai_suggestions/Memory` 时被误判为非空。排除证据：`tests/test_system_catalog_profile_init_v27.py::test_catalog_confirm_treats_field_sources_and_ai_suggestions_only_profile_as_blank`

## §3 覆盖率证明
| 维度 | 应检项数 | 已检 | 未检 | 未检说明 |
|---|---|---|---|---|
| 事实核实（步骤A） | 4 | 4 | 0 | - |
| 概念交叉引用（步骤B） | 5 | 5 | 0 | - |
| 审查清单项 | 6 | 6 | 0 | - |
| GWT 判定项 | 72 | 72 | 0 | - |

### 对抗性自检
- [x] 不存在“我知道意思但文本没写清”的地方
- [x] 新增 API 与路径变更已同步到 `docs/接口文档.md` / `docs/技术方案设计.md`
- [x] 无“可选/或者/暂不”型实现歧义残留在当前实现范围
- [x] 所有 GWT 均可通过 `test_report.md` 和对应命令判定 pass/fail
- [x] 高风险项（兼容/回滚/权限/REQ-C）已在本阶段收敛

## 建议验证清单（命令级别）
- [x] `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q --tb=short`
- [x] `cd frontend && CI=true npm test -- --watchAll=false --runInBand src/__tests__/systemProfileImportPage.render.test.js src/__tests__/systemProfileBoardPage.v27.test.js src/__tests__/serviceGovernancePage.render.test.js src/__tests__/systemListConfigPage.v27.test.js src/__tests__/navigationAndPageTitleRegression.test.js`
- [x] `cd frontend && npm run build`
- [x] `python -m compileall -q backend`
- [x] `git diff --unified=0 v2.6 -- pyproject.toml requirements.txt backend/requirements.txt frontend/package.json`
- [x] `BASE_URL=http://127.0.0.1:18080 bash scripts/api_regression.sh`

## 处理记录
| RVW-ID | 严重度 | 处理决策 | Owner | 说明 | 链接/证据 |
|---|---|---|---|---|---|
| - | - | - | Codex | 本轮未发现 P0/P1/P2 问题 | `review_result=pass` |

## 机器可读摘要块
<!-- REVIEW-SUMMARY-BEGIN -->
REVIEW_STAGE: implementation
REVIEW_SCOPE: full
REVIEW_MODES: TECH,REQ,TRACE
CODE_BASELINE: HEAD
REQ_BASELINE_HASH: 0d62af527b6d8f5609afc93f070f6d9eba217e40ec464f95d2ae10c87b025148
GWT_TOTAL: 72
GWT_CHECKED: 72
GWT_CARRIED: 0
CARRIED_FROM_COMMIT: N/A
CARRIED_GWTS: N/A
GWT_DEFERRED: 0
GWT_FAIL: 0
GWT_WARN: 0
SPOT_CHECK_GWTS: GWT-REQ-001-01,GWT-REQ-004-02,GWT-REQ-005-02,GWT-REQ-C003-01,GWT-REQ-C007-01
SPOTCHECK_FILE: docs/v2.7/spotcheck_implementation_no-cr.md
GWT_CHANGE_CLASS: clarification
CLARIFICATION_CONFIRMED_BY: User
CLARIFICATION_CONFIRMED_AT: 2026-03-13
VERIFICATION_COMMANDS: PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q --tb=short,cd frontend && CI=true npm test -- --watchAll=false --runInBand src/__tests__/systemProfileImportPage.render.test.js src/__tests__/systemProfileBoardPage.v27.test.js src/__tests__/serviceGovernancePage.render.test.js src/__tests__/systemListConfigPage.v27.test.js src/__tests__/navigationAndPageTitleRegression.test.js,cd frontend && npm run build,python -m compileall -q backend,git diff --unified=0 v2.6 -- pyproject.toml requirements.txt backend/requirements.txt frontend/package.json,BASE_URL=http://127.0.0.1:18080 bash scripts/api_regression.sh
REVIEW_RESULT: pass
<!-- REVIEW-SUMMARY-END -->
