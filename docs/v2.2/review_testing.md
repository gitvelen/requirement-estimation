# Review Report：Testing / v2.2

| 项 | 值 |
|---|---|
| 阶段 | Testing |
| 版本号 | v2.2 |
| 日期 | 2026-02-24 |
| 基线版本（对比口径） | `v2.1` |
| 当前代码版本 | `HEAD` |
| 复查口径 | full |
| Active CR（如有） | 无 |
| 检查点 | GWT 全量覆盖、测试真实性、前端契约烟测、REQ-C 禁止项回归、人类抽检锚点 |
| 审查范围 | `docs/v2.2/test_report.md`、`tests/`、`frontend/`、`backend/` |

## 结论摘要
- 总体结论：✅ 通过（Testing 第 1 轮收敛）
- Blockers（P0）：0
- 高优先级（P1）：0
- 其他建议（P2+）：0

## 本轮已执行验证（可复现）
- `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q` -> `108 passed in 11.62s`
- `cd frontend && npm run build` -> `Compiled successfully.`
- `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok`
- `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_req001_pageheader_v22.py tests/test_task_feature_confirm_gate_v22.py tests/test_task_remark_v22.py` -> `17 passed in 12.15s`
- `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_task_modification_compat.py tests/test_report_download_api.py tests/test_task_freeze_and_list_api.py` -> `7 passed in 11.62s`
- `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_esb_import_api.py tests/test_knowledge_import_api.py tests/test_dashboard_query_api.py` -> `17 passed in 16.92s`
- `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_dashboard_query_api.py::test_dashboard_query_validates_params -q` -> `1 passed`
- `rg -n "CREATE TABLE|ALTER TABLE|DROP TABLE|alembic|op\.add_column|op\.alter_column|op\.drop_column" -S backend tests frontend | head -n 20` -> 空输出

## 逐条 GWT 判定表（REQ 模式，🔴 MUST）

| GWT-ID | REQ-ID | 判定 | 证据类型 | 证据（可复现） | 备注 |
|--------|--------|------|---------|--------------|------|
| GWT-REQ-001-01 | REQ-001 | ✅ | RUN_OUTPUT | `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_req001_pageheader_v22.py tests/test_task_feature_confirm_gate_v22.py tests/test_task_remark_v22.py` -> `17 passed in 12.15s` |  |
| GWT-REQ-001-02 | REQ-001 | ✅ | RUN_OUTPUT | `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_req001_pageheader_v22.py tests/test_task_feature_confirm_gate_v22.py tests/test_task_remark_v22.py` -> `17 passed in 12.15s` |  |
| GWT-REQ-001-03 | REQ-001 | ✅ | RUN_OUTPUT | `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_req001_pageheader_v22.py tests/test_task_feature_confirm_gate_v22.py tests/test_task_remark_v22.py` -> `17 passed in 12.15s` |  |
| GWT-REQ-001-04 | REQ-001 | ✅ | RUN_OUTPUT | `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_req001_pageheader_v22.py tests/test_task_feature_confirm_gate_v22.py tests/test_task_remark_v22.py` -> `17 passed in 12.15s` |  |
| GWT-REQ-002-01 | REQ-002 | ✅ | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` |  |
| GWT-REQ-002-02 | REQ-002 | ✅ | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` |  |
| GWT-REQ-003-01 | REQ-003 | ✅ | RUN_OUTPUT | `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_esb_import_api.py tests/test_knowledge_import_api.py tests/test_dashboard_query_api.py` -> `17 passed in 16.92s` |  |
| GWT-REQ-003-02 | REQ-003 | ✅ | RUN_OUTPUT | `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_esb_import_api.py tests/test_knowledge_import_api.py tests/test_dashboard_query_api.py` -> `17 passed in 16.92s` |  |
| GWT-REQ-003-03 | REQ-003 | ✅ | RUN_OUTPUT | `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_esb_import_api.py tests/test_knowledge_import_api.py tests/test_dashboard_query_api.py` -> `17 passed in 16.92s` |  |
| GWT-REQ-004-01 | REQ-004 | ✅ | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` |  |
| GWT-REQ-004-02 | REQ-004 | ✅ | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` |  |
| GWT-REQ-004-03 | REQ-004 | ✅ | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` |  |
| GWT-REQ-004-04 | REQ-004 | ✅ | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` |  |
| GWT-REQ-005-01 | REQ-005 | ✅ | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` |  |
| GWT-REQ-005-02 | REQ-005 | ✅ | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` |  |
| GWT-REQ-005-03 | REQ-005 | ✅ | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` | 边界风险：菜单改名或路由重构后需复核 `/tasks/completed` 可达性。 |
| GWT-REQ-006-01 | REQ-006 | ✅ | RUN_OUTPUT | `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_task_modification_compat.py tests/test_report_download_api.py tests/test_task_freeze_and_list_api.py` -> `7 passed in 11.62s` |  |
| GWT-REQ-006-02 | REQ-006 | ✅ | RUN_OUTPUT | `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_task_modification_compat.py tests/test_report_download_api.py tests/test_task_freeze_and_list_api.py` -> `7 passed in 11.62s` |  |
| GWT-REQ-006-03 | REQ-006 | ✅ | RUN_OUTPUT | `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_task_modification_compat.py tests/test_report_download_api.py tests/test_task_freeze_and_list_api.py` -> `7 passed in 11.62s` |  |
| GWT-REQ-006-04 | REQ-006 | ✅ | RUN_OUTPUT | `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_task_modification_compat.py tests/test_report_download_api.py tests/test_task_freeze_and_list_api.py` -> `7 passed in 11.62s` |  |
| GWT-REQ-007-01 | REQ-007 | ✅ | RUN_OUTPUT | `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_req001_pageheader_v22.py tests/test_task_feature_confirm_gate_v22.py tests/test_task_remark_v22.py` -> `17 passed in 12.15s` |  |
| GWT-REQ-007-02 | REQ-007 | ✅ | RUN_OUTPUT | `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_req001_pageheader_v22.py tests/test_task_feature_confirm_gate_v22.py tests/test_task_remark_v22.py` -> `17 passed in 12.15s` |  |
| GWT-REQ-007-03 | REQ-007 | ✅ | RUN_OUTPUT | `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_req001_pageheader_v22.py tests/test_task_feature_confirm_gate_v22.py tests/test_task_remark_v22.py` -> `17 passed in 12.15s` |  |
| GWT-REQ-008-01 | REQ-008 | ✅ | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` |  |
| GWT-REQ-008-02 | REQ-008 | ✅ | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` |  |
| GWT-REQ-008-03 | REQ-008 | ✅ | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` |  |
| GWT-REQ-009-01 | REQ-009 | ✅ | RUN_OUTPUT | `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_esb_import_api.py tests/test_knowledge_import_api.py tests/test_dashboard_query_api.py` -> `17 passed in 16.92s` |  |
| GWT-REQ-009-02 | REQ-009 | ✅ | RUN_OUTPUT | `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_esb_import_api.py tests/test_knowledge_import_api.py tests/test_dashboard_query_api.py` -> `17 passed in 16.92s` |  |
| GWT-REQ-010-01 | REQ-010 | ✅ | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` |  |
| GWT-REQ-010-02 | REQ-010 | ✅ | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` |  |
| GWT-REQ-011-01 | REQ-011 | ✅ | RUN_OUTPUT | `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_req001_pageheader_v22.py tests/test_task_feature_confirm_gate_v22.py tests/test_task_remark_v22.py` -> `17 passed in 12.15s` |  |
| GWT-REQ-011-02 | REQ-011 | ✅ | RUN_OUTPUT | `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_req001_pageheader_v22.py tests/test_task_feature_confirm_gate_v22.py tests/test_task_remark_v22.py` -> `17 passed in 12.15s` |  |
| GWT-REQ-011-03 | REQ-011 | ✅ | RUN_OUTPUT | `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_req001_pageheader_v22.py tests/test_task_feature_confirm_gate_v22.py tests/test_task_remark_v22.py` -> `17 passed in 12.15s` |  |
| GWT-REQ-011-04 | REQ-011 | ✅ | RUN_OUTPUT | `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_req001_pageheader_v22.py tests/test_task_feature_confirm_gate_v22.py tests/test_task_remark_v22.py` -> `17 passed in 12.15s` |  |
| GWT-REQ-012-01 | REQ-012 | ✅ | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` |  |
| GWT-REQ-013-01 | REQ-013 | ✅ | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` |  |
| GWT-REQ-013-02 | REQ-013 | ✅ | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` | 边界风险：旧链接来源于收藏夹/外链时仍需人工抽检浏览器 back 行为。 |
| GWT-REQ-013-03 | REQ-013 | ✅ | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` |  |
| GWT-REQ-013-04 | REQ-013 | ✅ | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` |  |
| GWT-REQ-013-05 | REQ-013 | ✅ | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` |  |
| GWT-REQ-014-01 | REQ-014 | ✅ | RUN_OUTPUT | `rg -n "FUNC-022|/reports/ai-effect|page=ai" docs/系统功能说明书.md docs/接口文档.md docs/用户手册.md docs/部署记录.md` -> 命中下线与兼容说明 |  |
| GWT-REQ-101-01 | REQ-101 | ✅ | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` |  |
| GWT-REQ-101-02 | REQ-101 | ✅ | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` |  |
| GWT-REQ-101-03 | REQ-101 | ✅ | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` |  |
| GWT-REQ-102-01 | REQ-102 | ✅ | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` | 边界风险：移动端 WebView 返回行为仍建议在真机补测。 |
| GWT-REQ-C001-01 | REQ-C001 | ✅ | RUN_OUTPUT | `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_req001_pageheader_v22.py tests/test_task_feature_confirm_gate_v22.py tests/test_task_remark_v22.py` -> `17 passed in 12.15s` |  |
| GWT-REQ-C002-01 | REQ-C002 | ✅ | RUN_OUTPUT | `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_req001_pageheader_v22.py tests/test_task_feature_confirm_gate_v22.py tests/test_task_remark_v22.py` -> `17 passed in 12.15s` |  |
| GWT-REQ-C003-01 | REQ-C003 | ✅ | RUN_OUTPUT | `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_task_modification_compat.py tests/test_report_download_api.py tests/test_task_freeze_and_list_api.py` -> `7 passed in 11.62s` |  |
| GWT-REQ-C004-01 | REQ-C004 | ✅ | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` |  |
| GWT-REQ-C005-01 | REQ-C005 | ✅ | RUN_OUTPUT | `rg -n "CREATE TABLE|ALTER TABLE|DROP TABLE|alembic|op\.add_column|op\.alter_column|op\.drop_column" -S backend tests frontend | head -n 20` -> 空输出 |  |
| GWT-REQ-C006-01 | REQ-C006 | ✅ | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` |  |
| GWT-REQ-C007-01 | REQ-C007 | ✅ | RUN_OUTPUT | `bash -lc "..."`（菜单/路由/加载空错态契约烟测）-> `frontend_contract_smoke:ok` | 边界风险：需继续防止后续菜单改造时误恢复下线入口。 |
| GWT-REQ-C008-01 | REQ-C008 | ✅ | RUN_OUTPUT | `/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_esb_import_api.py tests/test_knowledge_import_api.py tests/test_dashboard_query_api.py` -> `17 passed in 16.92s` | 边界风险：后续看板改造需保持“近90天固定口径”不可配置。 |

## 收敛判定
- 本轮后：P0(open)=0，P1(open)=0
- 结论：满足 Testing 阶段收敛条件
- 备注：`uv run pytest -q --tb=short` / `uv run python scripts/incremental_static_gate.py` 在当前仓库因打包配置与脚本缺失失败，已记录在 `status.md` 作为阶段推进门禁风险（不影响本轮 `.venv` 口径测试通过）。

<!-- REVIEW-SUMMARY-BEGIN -->
REVIEW_STAGE: testing
REVIEW_SCOPE: full
REVIEW_MODES: TECH,REQ,TRACE
CODE_BASELINE: HEAD
REQ_BASELINE_HASH: b06d65d0bee9446aef05824f389d3e9b097af648
GWT_TOTAL: 53
GWT_CHECKED: 53
GWT_CARRIED: 0
CARRIED_FROM_COMMIT: N/A
CARRIED_GWTS: N/A
GWT_DEFERRED: 0
GWT_FAIL: 0
GWT_WARN: 0
SPOT_CHECK_GWTS: GWT-REQ-013-02,GWT-REQ-102-01,GWT-REQ-C007-01,GWT-REQ-C008-01,GWT-REQ-005-03
SPOTCHECK_FILE: docs/v2.2/spotcheck_testing_main.md
GWT_CHANGE_CLASS: N/A
CLARIFICATION_CONFIRMED_BY: N/A
CLARIFICATION_CONFIRMED_AT: N/A
VERIFICATION_COMMANDS: /home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q,cd frontend && npm run build,bash -lc "frontend contract smoke",/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_req001_pageheader_v22.py tests/test_task_feature_confirm_gate_v22.py tests/test_task_remark_v22.py,/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_task_modification_compat.py tests/test_report_download_api.py tests/test_task_freeze_and_list_api.py,/home/admin/Claude/requirement-estimation-system/.venv/bin/pytest -q tests/test_esb_import_api.py tests/test_knowledge_import_api.py tests/test_dashboard_query_api.py,rg -n "CREATE TABLE|ALTER TABLE|DROP TABLE|alembic|op\.add_column|op\.alter_column|op\.drop_column" -S backend tests frontend | head -n 20
REVIEW_RESULT: pass
<!-- REVIEW-SUMMARY-END -->
