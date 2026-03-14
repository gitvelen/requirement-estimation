# v2.7 Implementation Spotcheck

## Spotcheck 范围
- CR：无 Active CR
- 日期：2026-03-14
- 抽样 GWT：
  - `GWT-REQ-001-01`
  - `GWT-REQ-004-02`
  - `GWT-REQ-005-02`
  - `GWT-REQ-C003-01`
  - `GWT-REQ-C007-01`

## 抽样结果
| GWT-ID | 抽样证据 | 结果 | 备注 |
|---|---|---|---|
| GWT-REQ-001-01 | `frontend/src/__tests__/systemProfileImportPage.render.test.js::renders only v2.7 document types while keeping code scan entry` | ✅ PASS | PM 导入页仅保留 3 类文档卡片，历史评估报告/治理文档入口均已移除 |
| GWT-REQ-004-02 | `tests/test_system_catalog_profile_init_v27.py::test_catalog_confirm_initializes_blank_profiles_and_writes_memory` | ✅ PASS | confirm 仅初始化空画像，并返回 `updated_system_ids` / `skipped_items` 与 Memory 记录 |
| GWT-REQ-005-02 | `tests/test_skill_runtime_service.py::test_skill_runtime_registry_exposes_six_builtin_skills_and_ignores_disabled_future_skill` | ✅ PASS | 6 个内置 Skill 注册完成，disabled future skill 不会被纳入可执行集合 |
| GWT-REQ-C003-01 | `tests/test_service_governance_import_v27.py::test_service_governance_import_skips_manual_d3_field_but_keeps_other_updates` | ✅ PASS | manual 字段保持人工值，自动治理链路不会覆盖 |
| GWT-REQ-C007-01 | `git diff --unified=0 v2.6 -- pyproject.toml requirements.txt backend/requirements.txt frontend/package.json` | ✅ PASS | v2.7 未新增运行时依赖 |
