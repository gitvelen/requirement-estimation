# Review Report：Testing / v2.0

| 项 | 值 |
|---|---|
| 阶段 | Testing |
| 版本号 | v2.0 |
| 日期 | 2026-02-07 |
| 检查点 | 覆盖完整性、异常/边界覆盖、环境与数据真实性、性能验收证据、失败可诊断性 |
| 审查范围 | `docs/v2.0/test_report.md`、`docs/v2.0/requirements.md`、`docs/v2.0/status.md`、`tests/`、`frontend/src/__tests__/` |
| 输入材料 | 文档：`test_report.md`/`requirements.md`/`status.md`；命令：`.venv/bin/pytest -q`、`.venv/bin/pytest --collect-only -q`、`cd frontend && npm run build`、`cd frontend && npm test -- --watchAll=false` |

## 结论摘要
- **总体结论**：⚠️ 有条件通过（建议补齐追溯矩阵与性能验收证据后关闭 Testing）
- **Blockers（P0）**：0
- **高优先级（P1）**：2
- **其他建议（P2+）**：1

## 审查证据快照
- 后端全量回归：`.venv/bin/pytest -q` → `57 passed, 681 warnings in 7.45s`
- 前端构建：`cd frontend && npm run build` → `Compiled successfully`
- 前端单测：`cd frontend && npm test -- --watchAll=false` → `1 suite / 4 tests passed`
- 用例资产：`.venv/bin/pytest --collect-only -q` → `57 tests collected`（分布于 16 个后端测试文件）
- 缺陷闭环：`BUG-20260207-01`（证据预览404）已在 `backend/app.py` 修复并通过定向复验（见 `test_report.md`）

## 关键发现（按优先级）

### RVW-TST-001（P1）REQ→TEST 追溯矩阵缺失，无法“一键证明覆盖完整”
- **证据**：
  - `docs/v2.0/status.md` 已写明“下一步输出：持续更新 test_report 的测试记录与追溯矩阵”；
  - `docs/v2.0/test_report.md` 当前仅按 T/API 维度描述覆盖，缺少按 `REQ/REQ-NF` 的逐条映射表（未见 `REQ-xxx -> TEST-xxx -> 证据` 结构）。
- **风险**：
  - 测试通过不等于需求覆盖可证，阶段验收时难以快速证明“每条需求均被验证”；
  - 后续回归时无法精准定位“需求变更影响哪些测试”。
- **建议修改**：
  - 在 `docs/v2.0/test_report.md` 新增“需求追溯矩阵（Testing）”章节，最少字段：`REQ-ID | TEST-ID/文件 | 验证命令 | 结果 | 证据日期`；
  - 对 `REQ-NF` 单独列出“是否达标 + 证据链接/截图/日志”。
- **验证方式（可复现）**：
  - `rg -n "REQ-|REQ-NF-|追溯矩阵|TEST-" docs/v2.0/test_report.md`

### RVW-TST-002（P1）性能类需求（REQ-NF-001/002）缺少“基线→实测→结论”证据
- **证据**：
  - `docs/v2.0/requirements.md` 明确 `REQ-NF-001`（扫描<10分钟）与 `REQ-NF-002`（检索P95<500ms）为性能验收项；
  - `docs/v2.0/test_report.md` 目前未记录对应实测数据、测试数据规模、环境参数或对标基线。
- **风险**：
  - Testing 阶段结论与非功能需求验收脱节，可能在上线或生产流量下暴露性能风险；
  - 缺少基线会导致后续版本无法判断性能退化。
- **建议修改**：
  - 增补性能验收小节：`环境配置`、`数据规模`、`测试工具`、`P50/P95/P99`、`阈值判定`、`是否纳入验收`；
  - 将降级场景（如 embedding/Milvus 不可用）单独统计，不混入性能达标口径。
- **验证方式（可复现）**：
  - `rg -n "REQ-NF-001|REQ-NF-002|P95|基线|压测" docs/v2.0/test_report.md`

### RVW-TST-101（P2）测试告警噪声较高（681 warnings），建议建立收敛计划
- **证据**：
  - 本次后端回归输出 `57 passed, 681 warnings`，主要为 `DeprecationWarning`（FastAPI on_event、datetime.utcnow、pymilvus coroutinefunction）。
- **风险**：
  - 告警噪声过高会掩盖新增异常，增加真实问题漏检概率；
  - Python/依赖升级时可能突发兼容性失败。
- **建议修改**：
  - 在测试报告补充“warning 基线与治理计划”（按模块分批清理）；
  - 对自有代码优先修复可控告警（如 `datetime.utcnow()` 与 FastAPI lifespan 迁移）。
- **验证方式（可复现）**：
  - `.venv/bin/pytest -q -W default`

## 建议验证清单（命令级别）
- [ ] 回归确认：`.venv/bin/pytest -q`
- [ ] 前端确认：`cd frontend && npm run build && npm test -- --watchAll=false`
- [ ] 追溯矩阵检查：`rg -n "REQ-|REQ-NF-|TEST-|追溯矩阵" docs/v2.0/test_report.md`
- [ ] 性能证据检查：`rg -n "REQ-NF-001|REQ-NF-002|P95|基线|压测" docs/v2.0/test_report.md`
- [ ] 缺陷闭环检查：`rg -n "BUG-20260207-01|已修复" docs/v2.0/test_report.md`

## 开放问题
- [ ] REQ-NF-001/002 是否作为本次 Testing 阶段“必须关闭项”，或转入 Deployment 阶段灰度期继续验证？
- [ ] 若转入灰度验证，是否已定义样本量、观察窗口与回滚阈值？

## 处理记录（建议由开发/人工填写）
| RVW-ID | 严重度 | 处理决策（Fix/Defer/Accept） | Owner | 说明 | 链接/证据 |
|---|---|---|---|---|---|
| RVW-TST-001 | P1 |  |  |  |  |
| RVW-TST-002 | P1 |  |  |  |  |
| RVW-TST-101 | P2 |  |  |  |  |

---

## 追加记录：整改后复查（2026-02-07）

| 项 | 值 |
|---|---|
| 复查输入 | `docs/v2.0/test_report.md`（新增“Testing 阶段收口补充”）+ 最新回归/压测命令输出 |
| 复查结论 | ✅ 通过 |
| 复查说明 | 已补齐 REQ→TEST 追溯矩阵与 REQ-NF-001/002/005 性能证据；warning 项保留为持续治理项，不阻塞阶段关闭 |

### 处理记录（本轮更新）
| RVW-ID | 严重度 | 处理决策（Fix/Defer/Accept） | Owner | 说明 | 链接/证据 |
|---|---|---|---|---|---|
| RVW-TST-001 | P1 | Fix | AI | 已在 `test_report.md` 增加 TEST-001~026 追溯矩阵，覆盖 `REQ-001~020` 与 `REQ-NF-001~006` | `docs/v2.0/test_report.md` |
| RVW-TST-002 | P1 | Fix | AI | 已补齐性能验收：扫描 P95=`1.753s`、Milvus 检索 P95=`444.113ms`、并发 5+1 快照 | `docs/v2.0/test_report.md` |
| RVW-TST-101 | P2 | Defer | AI | 不影响功能正确性，纳入“warning 基线与治理计划”分批收敛 | `docs/v2.0/test_report.md` |

### 复查后结论摘要
- 总体结论：✅ 通过
- Blockers（P0）：0
- 高优先级（P1）：0
- 其他建议（P2+）：1（已记录治理计划）
