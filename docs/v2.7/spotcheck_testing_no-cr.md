# v2.7 Testing Spotcheck

## Spotcheck 范围
- CR：无 Active CR
- 日期：2026-03-14
- 抽样 GWT：
  - `GWT-REQ-003-01`
  - `GWT-REQ-004-03`
  - `GWT-REQ-102-01`
  - `GWT-REQ-C006-01`

## 抽样结果
| GWT-ID | 抽样证据 | 结果 | 备注 |
|---|---|---|---|
| GWT-REQ-003-01 | `tests/test_service_governance_import_v27.py::test_service_governance_import_updates_d3_and_returns_match_statistics` + `frontend/src/__tests__/serviceGovernancePage.render.test.js::uploads governance file and shows matched, unmatched and updated systems` | ✅ PASS | 自动化已覆盖 admin 服务治理导入、统计回显与页面结果展示；人工 E2E 记录待补 |
| GWT-REQ-004-03 | `tests/test_system_catalog_profile_init_v27.py::test_catalog_confirm_skips_non_blank_profiles_without_overwriting_existing_content` + `frontend/src/__tests__/systemListConfigPage.v27.test.js::removes subsystem tabs and shows catalog update result after confirm` | ✅ PASS | 非空画像保持不变，并在前后端结果中标记 `profile_not_blank` |
| GWT-REQ-102-01 | `tests/test_service_governance_import_v27.py::test_service_governance_import_updates_d3_and_returns_match_statistics` | ✅ PASS | 治理导入匹配统计以名称一致记录为口径，自动化统计链路已落地 |
| GWT-REQ-C006-01 | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q --tb=short` + `BASE_URL=http://127.0.0.1:18080 bash scripts/api_regression.sh` | ✅ PASS | 项目级回归和 API 基线均未被 v2.7 改造阻断 |
