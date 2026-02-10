# Review Report：Implementation / v2.0

| 项 | 值 |
|---|---|
| 阶段 | Implementation |
| 版本号 | v2.0 |
| 日期 | 2026-02-07 |
| 检查点 | 范围收口（仅3项UI/UX）、路由/菜单兼容、字段归一化与发布校验、错误处理与安全、可维护性、测试与证据可复现 |
| 审查范围 | 后端：`backend/service/system_profile_service.py`、`backend/service/knowledge_service.py`、`backend/agent/system_identification_agent.py`、新增测试；前端：`frontend/src/components/MainLayout.js`、`frontend/src/App.js`、`frontend/src/pages/CosmicConfigPage.js`、系统画像拆页新页面 |
| 输入材料 | `docs/v2.0/requirements.md`（v1.14）、`docs/v2.0/design.md`（v0.11）、`docs/v2.0/plan.md`（v0.9）、`.claude/templates/review_template.md` |

## 结论摘要
- **总体结论**：⚠️ 有条件通过（2 个 P2 问题建议修复后进入 Testing）
- Blockers（P0）：0
- 高优先级（P1）：0
- 其他建议（P2+）：2

## 关键发现（按优先级）

### RVW-IMP-001（P2）系统TAB query 同步逻辑不会清理“无 system_id 场景”的旧参数，可能造成 URL 语义漂移
- **证据**：
  - `SystemProfileImportPage` / `SystemProfileBoardPage` 在从 URL 同步系统时，仅在 `nextId` 存在时才会对比/刷新 `system_id`；当目标系统无 `id` 时，旧的 `system_id` 参数可能保留。
- **风险**：
  - 两页之间跳转虽然仍以 `system_name` 为主能正确选中系统，但 URL 中的 `system_id` 可能与当前系统不一致，影响可读性与问题定位。
- **建议修改**：
  - 将 query 同步判断改为：`system_name/system_id` 任一不一致即刷新；当 `nextId` 为空时显式删除 `system_id`。
- **验证方式（可复现）**：
  - 手工：访问 `/system-profiles/board?system_name=<无id系统>&system_id=xxx`，确认页面会自动清理 `system_id`。

### RVW-IMP-002（P2）“不展示导入历史”下的最小反馈依赖 localStorage，建议补齐降级处理（浏览器禁用 storage / 清理缓存）
- **证据**：知识导入页的“最近一次扫描任务 job_id”从 localStorage 读取（无 localStorage 时会失去“刷新状态”入口）。
- **风险**：
  - 少数受限浏览器/隐私模式下 localStorage 不可用时，用户只能看到 toast，刷新状态能力弱化。
- **建议修改**：
  - 在 localStorage 不可用或读取失败时，降级为仅展示“本次会话内”的 job 状态（不影响主流程）。
  - 或明确接受该限制，并在 UI 上提示“刷新需保留浏览器缓存”。
- **验证方式（可复现）**：
  - 手工：禁用站点存储/清理缓存后提交扫描任务，确认仍能看到最近任务状态（至少会话内）。

## 已验证证据（命令级别）
- 后端回归（新增）：`.venv/bin/pytest -q tests/test_system_profile_publish_rules.py`（3 passed）
- 前端构建：`cd frontend && npm run build`（Compiled successfully）
- 前端单测：`cd frontend && npm test -- --watchAll=false`（1 suite, 4 passed）

## 建议验证清单（命令级别）
- [ ] 后端全量回归：`.venv/bin/pytest -q`
- [ ] 前端路由兼容手工走查：
  - `/reports/ai-effect` 直达是否跳转 `/dashboard` 且提示迁移
  - `/system-profiles` 是否重定向到 `/system-profiles/board` 并保留 query
- [ ] 系统画像信息看板发布校验：缺少 `in_scope` 或 `core_functions` 时是否返回 `PROFILE_003`

## 开放问题
- 无

## 处理记录（建议由开发/人工填写）
| RVW-ID | 严重度 | 处理决策（Fix/Defer/Accept） | Owner | 说明 | 链接/证据 |
|---|---|---|---|---|---|
| RVW-IMP-001 | P2 | Fix | AI | 清理 query 同步逻辑，避免残留旧 system_id | 前端系统画像页 |
| RVW-IMP-002 | P2 | Fix | AI | localStorage 读写增加 try/catch；无存储能力时降级为“会话内反馈” | 前端系统画像页 |

---

## 追加记录：Implementation 修复后复查（2026-02-07）

| 项 | 值 |
|---|---|
| 复查输入 | 增量代码变更（前端/后端）对照 `requirements.md v1.14`（REQ-016/021/022） |
| 复查结论 | ✅ 通过 |
| 复查说明 | RVW-IMP-001/002 已修复：TAB query 同步会清理不匹配的 `system_id`；localStorage 读写已做降级保护，不影响“仅反馈当前操作结果”的需求口径。 |

**抽样核对点（证据）**：
- 前端构建：`cd frontend && npm run build`
- 后端增量回归：`.venv/bin/pytest -q tests/test_system_profile_publish_rules.py`
