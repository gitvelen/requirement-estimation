# Review Report：Testing / v2.7

| 项 | 值 |
|---|---|
| 阶段 | Testing |
| 版本号 | v2.7 |
| 日期 | 2026-03-14 |
| 基线版本（对比口径） | `v2.6` |
| 复查口径 | full |
| Active CR | 无（回溯记录：`CR-20260314-001`，状态 Implemented） |
| 审查范围 / 输入材料 | `docs/v2.7/test_report.md`、`docs/v2.7/plan.md`、`docs/v2.7/requirements.md`、`backend/**` / `frontend/**` 当前 diff、项目级结果门禁输出 |

## §-1 预审结果（🔴 MUST）
| 检查项 | 命令 | 结果 | 通过 |
|---|---|---|---|
| 测试 | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q --tb=short` | `237 passed, 1 warning` | ✅ |
| 构建 | `cd frontend && npm run build` | `Compiled successfully.` | ✅ |
| 类型检查 | `python -m compileall -q backend` | 无输出，退出码 0 | ✅ |
| 测试证据就绪 | 检查 `docs/v2.7/test_report.md` | `test_report.md` 已包含 72 条 GWT 覆盖矩阵、项目级门禁与 `REQ-003/REQ-004` 人工 E2E 通过记录 | ✅ |

## 结论摘要
- 总体结论：✅ 通过
- Blockers（P0）：0 / 高优先级（P1）：0 / 其他建议（P2+）：0
- 说明：自动化回归、项目级门禁与 `REQ-003/REQ-004` 的人工 E2E 均已完成，Testing 阶段出阶段条件满足。

## 关键发现（按优先级）

无 P0/P1 级未收敛问题。

## §0 审查准备
### A. 事实核实
| # | 声明（出处） | 核实源 | 结论 |
|---|---|---|---|
| 1 | `TEST-GATE-001`：项目级 full pytest 通过（`test_report.md`） | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q --tb=short` | ✅ |
| 2 | `TEST-BUILD-001`：frontend build 通过（`test_report.md`） | `cd frontend && npm run build` | ✅ |
| 3 | `TEST-DEPS-001` / `TEST-CONTRACT-001` / `TEST-API-001`：依赖 diff、契约对照与 API regression 已完成（`test_report.md`） | `git diff` / `rg` / `scripts/api_regression.sh` 记录 | ✅ |
| 4 | `REQ-003` / `REQ-004` 的人工 E2E 已由 User 在可验收环境完成并反馈“正常”（`test_report.md`） | `docs/v2.7/test_report.md` 人工验证结果章节 | ✅ |
| 5 | 服务治理最新模板口径已固定为 `data/esb-template.xlsx`，并保持 `data/接口申请模板.xlsx` 兼容输入 | `docs/v2.7/requirements.md`、`docs/v2.7/design.md`、`docs/v2.7/test_report.md`、`tests/test_service_governance_import_v27.py` | ✅ |
| 6 | Testing 阶段前端可读性/交互回归已补回 CR，并收敛到用户可读展示边界 | `docs/v2.7/cr/CR-20260314-001.md`、`docs/v2.7/test_report.md`、`frontend/src/__tests__/systemListConfigPage.v27.test.js` | ✅ |

### B. 关键概念交叉引用
| 概念 | 出现位置 | 口径一致 |
|---|---|---|
| `REQ-003` / `REQ-004` 标记为 `[E2E Required]` | `docs/v2.7/requirements.md`、`docs/v2.7/test_report.md`、本文件 | ✅ |
| `237 passed, 1 warning` / `Compiled successfully.` / `compileall` 通过 | `docs/v2.7/test_report.md`、本文件 §-1 | ✅ |
| `data/esb-template.xlsx` 为最新治理模板口径，`data/接口申请模板.xlsx` 为兼容输入 | `docs/v2.7/requirements.md`、`docs/v2.7/design.md`、`docs/v2.7/test_report.md` | ✅ |
| `.env.backend.internal`、四开关、`profile/execution-status` | `docs/v2.7/test_report.md`、`docs/v2.7/deployment.md`、`docs/技术方案设计.md`、`docs/接口文档.md` | ✅ |
| T009 已在 plan/status 中同步为完成态 | `docs/v2.7/plan.md`、`docs/v2.7/status.md` | ✅ |
| `CR-20260314-001` 已回填到 plan/test/status，且不进入 Active CR | `docs/v2.7/cr/CR-20260314-001.md`、`docs/v2.7/plan.md`、`docs/v2.7/test_report.md`、`docs/v2.7/status.md` | ✅ |

## Testing 审查清单
- [x] 覆盖完整：72/72 个 GWT 均已有自动化或命令级 PASS 证据
- [x] 边界/异常覆盖：旧类型拒绝、manual 冲突、partial_success、模板缺列、清理失败与主链路兼容均已覆盖
- [x] 环境与数据：测试使用本地临时目录、stub、mock 和本地 uvicorn，不依赖外部在线服务
- [x] 性能（如适用）：本期无新增性能指标；项目级全量回归与前端 build 门禁已通过
- [x] `test_report.md` 交叉校验：覆盖矩阵、依赖 diff、契约对照与本审查口径一致
- [x] 契约烟测（前端）：菜单/标题一致性、关键页面首屏与主要入口可达均已通过页面 smoke
- [x] 里程碑展示：M1 / M2 已在对话中展示并获继续指令

## 任务完成度
| 任务ID | 任务名称 | 状态 | 备注 |
|---|---|---|---|
| T001 | v2.7 canonical schema、Memory/Execution 存储与开关基座 | ✅完成 | 已进入 Testing 验证 |
| T002 | Skill Runtime、Policy Gate 与 PM 文档导入链路 | ✅完成 | 已进入 Testing 验证 |
| T003 | 服务治理导入改造为 admin 全局画像联动 | ✅完成 | 自动化与人工 E2E 均已通过 |
| T004 | 单一系统清单解析、空画像初始化与子系统模型退场 | ✅完成 | 自动化与人工 E2E 均已通过 |
| T005 | Memory 驱动的系统识别与功能点拆解联动 | ✅完成 | 已进入 Testing 验证 |
| T006 | `code_scan_skill` 适配层与 Runtime 接入 | ✅完成 | 已进入 Testing 验证 |
| T007 | PM/Admin 页面、路由与交互收敛到 v2.7 口径 | ✅完成 | 页面 smoke 与 build 已通过 |
| T008 | v2.7 清理脚本、开关发布顺序与回滚 Runbook | ✅完成 | 部署准备与 runbook 测试完成 |
| T009 | 全量回归、证据闭环与主文档同步 | ✅完成 | 自动化证据闭环、回溯 CR 补记、主文档同步与 `REQ-003/REQ-004` 人工 E2E 回填均已完成 |

- 总任务数：9 / 完成：9 / 进行中：0 / 跳过：0 / 变更：0

## 需求符合性审查（REQ 模式）
### 逐条 GWT 判定表（🔴 MUST）
| GWT-ID | REQ-ID | 判定 | 证据类型 | 证据（可复现） | 备注 |
| GWT-REQ-001-01 | REQ-001 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-001-02 | REQ-001 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-001-03 | REQ-001 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-002-01 | REQ-002 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-002-02 | REQ-002 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-002-03 | REQ-002 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-003-01 | REQ-003 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化通过；人工 E2E 已补齐 |
| GWT-REQ-003-02 | REQ-003 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化通过；人工 E2E 已补齐 |
| GWT-REQ-003-03 | REQ-003 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化通过；人工 E2E 已补齐 |
| GWT-REQ-004-01 | REQ-004 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化通过；人工 E2E 已补齐 |
| GWT-REQ-004-02 | REQ-004 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化通过；人工 E2E 已补齐 |
| GWT-REQ-004-03 | REQ-004 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化通过；人工 E2E 已补齐 |
| GWT-REQ-004-04 | REQ-004 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化通过；人工 E2E 已补齐 |
| GWT-REQ-004-05 | REQ-004 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化通过；人工 E2E 已补齐 |
| GWT-REQ-005-01 | REQ-005 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-005-02 | REQ-005 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-005-03 | REQ-005 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-005-04 | REQ-005 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-005-05 | REQ-005 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-005-06 | REQ-005 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-006-01 | REQ-006 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-006-02 | REQ-006 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-006-03 | REQ-006 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-006-04 | REQ-006 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-006-05 | REQ-006 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-007-01 | REQ-007 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-007-02 | REQ-007 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-007-03 | REQ-007 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-007-04 | REQ-007 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-008-01 | REQ-008 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-008-02 | REQ-008 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-008-03 | REQ-008 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-008-04 | REQ-008 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-009-01 | REQ-009 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-009-02 | REQ-009 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-009-03 | REQ-009 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-009-04 | REQ-009 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-009-05 | REQ-009 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-010-01 | REQ-010 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-010-02 | REQ-010 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-010-03 | REQ-010 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-011-01 | REQ-011 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-011-02 | REQ-011 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-011-03 | REQ-011 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-011-04 | REQ-011 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-012-01 | REQ-012 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-012-02 | REQ-012 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-012-03 | REQ-012 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-101-01 | REQ-101 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-101-02 | REQ-101 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-102-01 | REQ-102 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-102-02 | REQ-102 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-103-01 | REQ-103 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-103-02 | REQ-103 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-104-01 | REQ-104 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-104-02 | REQ-104 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-105-01 | REQ-105 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-105-02 | REQ-105 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-C001-01 | REQ-C001 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-C001-02 | REQ-C001 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-C002-01 | REQ-C002 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-C002-02 | REQ-C002 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-C003-01 | REQ-C003 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-C003-02 | REQ-C003 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-C004-01 | REQ-C004 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-C004-02 | REQ-C004 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-C005-01 | REQ-C005 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-C006-01 | REQ-C006 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-C006-02 | REQ-C006 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-C007-01 | REQ-C007 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-C008-01 | REQ-C008 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |
| GWT-REQ-C008-02 | REQ-C008 | ✅ | RUN_OUTPUT | `docs/v2.7/test_report.md` TEST-COVERAGE-MATRIX 中同名 GWT 行 | 自动化证据完整 |

### 对抗性审查（REQ-C 强制）
- `REQ-C001`：
  - 泄漏路径 1：PM 导入页仍展示历史评估报告/治理文档入口。排除证据：`frontend/src/__tests__/systemProfileImportPage.render.test.js`
  - 泄漏路径 2：服务端导入或模板下载仍放行旧类型。排除证据：`tests/test_system_profile_import_api.py`
- `REQ-C002`：
  - 泄漏路径 1：运行态空画像仍输出旧 schema 键。排除证据：`tests/test_profile_schema_v27.py`
  - 泄漏路径 2：清理后仍有旧 schema / history_report 残留。排除证据：`tests/test_cleanup_v27.py`
- `REQ-C003`：
  - 泄漏路径 1：服务治理导入覆盖 manual D3。排除证据：`tests/test_service_governance_import_v27.py`
  - 泄漏路径 2：系统清单 confirm 覆盖非空画像。排除证据：`tests/test_system_catalog_profile_init_v27.py`
- `REQ-C004`：
  - 泄漏路径 1：disabled future skill 无法装载。排除证据：`tests/test_skill_runtime_service.py`
  - 泄漏路径 2：future memory_type 需要新增专用结构。排除证据：`tests/test_memory_service_v27.py`
- `REQ-C005`：
  - 泄漏路径 1：识别结果只有候选列表。排除证据：`tests/test_system_identification_memory_v27.py`
  - 泄漏路径 2：`final_verdict` 取值不受控。排除证据：`tests/test_system_identification_memory_v27.py`
- `REQ-C006`：
  - 泄漏路径 1：任务评估/报告主链路被 v2.7 阻断。排除证据：full pytest
  - 泄漏路径 2：基础 API 可用性回归。排除证据：`scripts/api_regression.sh`
- `REQ-C007`：
  - 泄漏路径 1：Python 运行时依赖新增。排除证据：依赖 diff 为空
  - 泄漏路径 2：frontend runtime package 新增。排除证据：同一 diff 为空
- `REQ-C008`：
  - 泄漏路径 1：非空画像被系统清单覆盖。排除证据：`tests/test_system_catalog_profile_init_v27.py::test_catalog_confirm_skips_non_blank_profiles_without_overwriting_existing_content`
  - 泄漏路径 2：仅有 `field_sources/ai_suggestions/Memory` 时被误判非空。排除证据：`tests/test_system_catalog_profile_init_v27.py::test_catalog_confirm_treats_field_sources_and_ai_suggestions_only_profile_as_blank`

## §3 覆盖率证明
| 维度 | 应检项数 | 已检 | 未检 | 未检说明 |
|---|---|---|---|---|
| 事实核实（步骤A） | 6 | 6 | 0 | - |
| 概念交叉引用（步骤B） | 6 | 6 | 0 | - |
| 审查清单项 | 7 | 7 | 0 | - |
| GWT 判定项 | 72 | 72 | 0 | - |

### 对抗性自检
- [x] 不存在“我知道意思但文本没写清”的地方
- [x] 所有新增 API 已在主文档中同步完成
- [x] 自动化覆盖与 GWT 判定口径已收敛
- [x] 验收用例可仅凭文档和命令判定 pass/fail
- [x] 高风险项已全部收敛：`REQ-003/REQ-004` 人工 E2E 验证已完成

## 建议验证清单（命令级别）
- [x] `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q --tb=short`
- [x] `cd frontend && CI=true npm test -- --watchAll=false --runInBand src/__tests__/systemProfileImportPage.render.test.js src/__tests__/systemProfileBoardPage.v27.test.js src/__tests__/serviceGovernancePage.render.test.js src/__tests__/systemListConfigPage.v27.test.js src/__tests__/navigationAndPageTitleRegression.test.js`
- [x] `cd frontend && npm run build`
- [x] `python -m compileall -q backend`
- [x] `BASE_URL=http://127.0.0.1:18080 bash scripts/api_regression.sh`
- [x] 按 `docs/v2.7/test_report.md` 回填 `REQ-003` / `REQ-004` 的人工验证记录

## 处理记录
| RVW-ID | 严重度 | 处理决策 | Owner | 说明 | 链接/证据 |
|---|---|---|---|---|---|
| RVW-001 | P1 | 已收敛 | User + Codex | `REQ-003/REQ-004` 已在可验收环境完成人工 E2E，并由 User 反馈“正常” | `docs/v2.7/test_report.md` 人工验证结果章节 |

## 机器可读摘要块
<!-- REVIEW-SUMMARY-BEGIN -->
REVIEW_STAGE: testing
REVIEW_SCOPE: full
REVIEW_MODES: REQ,TRACE
CODE_BASELINE: HEAD
REQ_BASELINE_HASH: 2676cc37e1af6844fe98980db4adb4c1e180ca7ad114c7dfde3d781bad207532
GWT_TOTAL: 72
GWT_CHECKED: 72
GWT_CARRIED: 0
CARRIED_FROM_COMMIT: N/A
CARRIED_GWTS: N/A
GWT_DEFERRED: 0
GWT_FAIL: 0
GWT_WARN: 0
SPOT_CHECK_GWTS: GWT-REQ-003-01,GWT-REQ-004-03,GWT-REQ-102-01,GWT-REQ-C006-01
SPOTCHECK_FILE: docs/v2.7/spotcheck_testing_no-cr.md
GWT_CHANGE_CLASS: structural
CLARIFICATION_CONFIRMED_BY: User
CLARIFICATION_CONFIRMED_AT: 2026-03-13
VERIFICATION_COMMANDS: PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q --tb=short,cd frontend && CI=true npm test -- --watchAll=false --runInBand src/__tests__/systemProfileImportPage.render.test.js src/__tests__/systemProfileBoardPage.v27.test.js src/__tests__/serviceGovernancePage.render.test.js src/__tests__/systemListConfigPage.v27.test.js src/__tests__/navigationAndPageTitleRegression.test.js,cd frontend && npm run build,python -m compileall -q backend,BASE_URL=http://127.0.0.1:18080 bash scripts/api_regression.sh
REVIEW_RESULT: pass
<!-- REVIEW-SUMMARY-END -->
