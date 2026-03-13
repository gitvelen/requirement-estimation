# Review Report：Planning / v2.7

> **共享章节**：见 `templates/review_skeleton.md`
> 本模板只包含 Planning 阶段特定的审查内容

> 轻量审查模板：聚焦任务可执行性、需求反向覆盖、验证方式可复现。
> 不含 GWT 逐条判定表（Planning 阶段无代码产出，无需 GWT 粒度判定）。

| 项 | 值 |
|---|---|
| 阶段 | Planning |
| 版本号 | v2.7 |
| 日期 | 2026-03-13 |
| 审查范围 | `docs/v2.7/plan.md` |
| 输入材料 | `docs/v2.7/requirements.md`, `docs/v2.7/design.md`, `docs/v2.7/plan.md` |

## §0 审查准备（REP 步骤 A+B）

### A. 事实核实
> 从 plan.md 提取事实性声明，逐条对照 design.md / requirements.md 核实。

| # | 声明（出处） | 核实源 | 结论 |
|---|------------|--------|------|
| 1 | 计划已按 v2.7 设计拆成 schema/Runtime/治理导入/系统清单/识别拆解/code scan/前端/部署/回归 9 个任务（plan T001-T009） | `design.md` §5.1~§5.10、§6.1、§7.1 | ✅ |
| 2 | T001 把正式画像口径、Memory、Runtime execution 与四个 v2.7 开关作为基础任务前置收敛（plan T001） | `design.md` §5.2.1、§5.2.2、§5.6、§6.1.2 | ✅ |
| 3 | T002 要求 PM 文档导入链路只保留三类文档，并迁移到 `profile/execution-status`（plan T002） | `requirements.md` REQ-001 / REQ-C001；`design.md` §5.10、API-001~003 | ✅ |
| 4 | T003 将服务治理导入收敛为 admin 全局治理，D3 为主自动更新，D1/D4 受 PolicyGate 控制（plan T003） | `requirements.md` REQ-003、REQ-009、REQ-C003；`design.md` §5.3.2、API-006 | ✅ |
| 5 | T004 收敛为单一系统清单模型，并以 BlankProfileEvaluator 执行“空画像才初始化，非空跳过”（plan T004） | `requirements.md` REQ-004、REQ-C008；`design.md` §5.2.4、§5.3.3、API-007/008 | ✅ |
| 6 | T005 将系统识别与功能点拆解改为 Memory 驱动，并强制 `final_verdict`（plan T005） | `requirements.md` REQ-007、REQ-008、REQ-010、REQ-C005；`design.md` §5.3.4、§5.3.5 | ✅ |
| 7 | T006 保留 `code_scan_skill` 双入口与 `suggestion_only` 边界，不引入新运行时依赖（plan T006） | `requirements.md` REQ-005、REQ-006、REQ-C007；`design.md` §5.1.2、§5.3.6、TEST-013 | ✅ |
| 8 | T007/T008/T009 已覆盖前端路由改造、开关发布顺序、主文档同步与全量回归证据闭环（plan T007~T009） | `design.md` §5.10、§6.1.2、§6.1.3、§7.1 | ✅ |

### B. 关键概念交叉引用
> 提取关键概念（任务 ID、REQ-ID 关联、依赖关系、关键配置/接口），全文搜索所有出现位置。

| 概念 | 出现位置 | 口径一致 |
|------|---------|---------|
| `T001`~`T009` | `plan.md` 任务概览、任务详情、执行顺序 | ✅ |
| `REQ-C007` 依赖 diff 口径 | `requirements.md` REQ-C007、`design.md` TEST-013、`plan.md` T006/T009 | ✅ |
| `.env.backend.internal` | `design.md` §0.5/§6.0、`plan.md` T001/T008 | ✅ |
| `profile/execution-status` / `profile/extraction-status` alias | `design.md` API-003/§5.10/§6.1.1、`plan.md` T002/T007/T008 | ✅ |
| `ServiceGovernancePage` | `design.md` §4.2/§5.10、`plan.md` T007 | ✅ |
| 单一系统清单 / 无子系统模型 | `requirements.md` REQ-004/REQ-006、`design.md` §5.3.3/§5.10、`plan.md` T004/T007 | ✅ |
| `review_gate_validate_plan_reverse_coverage` 与 R6 差集自检 | `plan.md` 引用自检、Planning Exit | ✅ |
| 主文档同步清单 | `status.md` 需要同步的主文档、`plan.md` T008/T009 | ✅ |

## 审查清单

- [x] 任务可追踪：Txxx ID 完整，每条有清晰 DoD
- [x] 粒度合适：可独立实现与验证，依赖关系清晰
- [x] 追溯完整：任务关联 REQ/SCN/API/TEST
- [x] 验证可复现：每个任务有命令级别验证方式
- [x] 风险与回滚：涉及线上行为变化的任务有开关/回滚思路
- [x] 内容完整：覆盖需求和设计阶段产出的成果

## 需求反向覆盖

| REQ-ID | 关联任务 | 覆盖判定 | 备注 |
|--------|---------|---------|------|
| REQ-001 | T002, T007, T009 | ✅ | PM 导入页收敛、前端页面与回归闭环 |
| REQ-002 | T001, T007, T009 | ✅ | canonical schema、画像面板与一致性回归 |
| REQ-003 | T003, T007, T009 | ✅ | 服务治理导入、页面与统计回归 |
| REQ-004 | T004, T007, T008, T009 | ✅ | 系统清单补空、发布与部署演练 |
| REQ-005 | T002, T006, T009 | ✅ | Runtime 组件、Skill 注册表、code scan 接入 |
| REQ-006 | T002, T003, T004, T006, T009 | ✅ | 文档/治理/系统清单 canonical 化边界 |
| REQ-007 | T001, T005, T007, T009 | ✅ | Memory 模型、查询与前端入口 |
| REQ-008 | T005, T009 | ✅ | `final_verdict` 与识别直判 |
| REQ-009 | T002, T003, T004, T006, T007, T009 | ✅ | PolicyGate 与场景化落地 |
| REQ-010 | T005, T009 | ✅ | 功能点拆解读取/写回 Memory |
| REQ-011 | T001, T002, T003, T004, T005, T006, T007, T009 | ✅ | `failed/partial_success` 与失败补偿 |
| REQ-012 | T001, T004, T008, T009 | ✅ | 清理脚本、回滚与核验 |
| REQ-101 | T001, T007, T009 | ✅ | 字段数达标与前后端一致性 |
| REQ-102 | T003, T009 | ✅ | 服务治理成功率统计 |
| REQ-103 | T002, T006, T009 | ✅ | 6 个 Skill 与 Scene 路由验证 |
| REQ-104 | T001, T005, T009 | ✅ | Memory 覆盖率统计 |
| REQ-105 | T001, T004, T008, T009 | ✅ | 旧数据清理结果核验 |
| REQ-C001 | T002, T007, T009 | ✅ | PM 旧入口移除与 API 拒绝 |
| REQ-C002 | T001, T004, T008, T009 | ✅ | 旧 schema / 子系统模型 / 历史残留清理 |
| REQ-C003 | T003, T004, T007, T009 | ✅ | `manual` 优先、防覆盖 |
| REQ-C004 | T001, T002, T006, T009 | ✅ | Registry / Memory 可扩展 |
| REQ-C005 | T005, T009 | ✅ | `final_verdict` 强校验 |
| REQ-C006 | T003, T005, T008, T009 | ✅ | 主链路兼容与发布回滚 |
| REQ-C007 | T001, T006, T008, T009 | ✅ | 无新增运行时依赖与配置口径统一 |
| REQ-C008 | T004, T007, T009 | ✅ | 非空画像跳过与结果展示 |

## 关键发现

### RVW-PLN-001（P2，已修复）依赖 diff 证据口径少了 `pyproject.toml` 与根目录 `requirements.txt`
- **证据**：本轮收敛后，`requirements.md` REQ-C007、`design.md` TEST-013 与 `plan.md` T006/T009 已统一为对比 `pyproject.toml` / `requirements.txt` / `backend/requirements.txt` / `frontend/package.json`；而 `plan.md` 初版 T006/T009 只写了 `backend/requirements.txt frontend/package.json`。
- **风险**：Implementation/Testing 阶段会缺失对运行时依赖完整口径的验证，可能导致 REQ-C007 证据链不完整。
- **建议修改**：把 T006/T009 的依赖 diff 命令统一扩展为 `git diff --unified=0 v2.6 -- pyproject.toml requirements.txt backend/requirements.txt frontend/package.json`。
- **验证方式**：`rg -n 'git diff --unified=0 v2.6 -- pyproject.toml requirements.txt backend/requirements.txt frontend/package.json' docs/v2.7/plan.md`

### RVW-PLN-002（P2，已修复）T004 与 T007 对系统清单前端文件存在重叠归属
- **证据**：`plan.md` 初版中 `frontend/src/pages/SystemListConfigPage.js`、`frontend/src/pages/MainSystemConfigPage.js` 同时出现在 T004 和 T007。
- **风险**：任务边界不清，Implementation 阶段容易出现并行改同文件、验收责任模糊和回归范围漂移。
- **建议修改**：让 T004 收敛为后端单一系统清单解析与 blank evaluator；系统清单页面/UI 归属统一留在 T007。
- **验证方式**：确认 `SystemListConfigPage.js` / `MainSystemConfigPage.js` 只在 T007 中出现为前端改造范围。

### RVW-PLN-003（P2，已修复）主文档同步范围未覆盖 `系统功能说明书` 与 `用户手册`
- **证据**：`status.md` 的“需要同步的主文档清单”包含 `docs/系统功能说明书.md`、`docs/用户手册.md`；`plan.md` 初版 T008 仅提到 `技术方案设计.md`、`接口文档.md`、`部署记录.md`。
- **风险**：Deployment/收口阶段会遗留未决同步项，无法闭环状态清单。
- **建议修改**：在 T008 中补充“同步或明确标注不适用”的处理要求，并将结论回写 `status.md`。
- **验证方式**：`rg -n '系统功能说明书|用户手册|status.md' docs/v2.7/plan.md`

本轮无 P0 / P1 / P2 open 新发现。

## §3 覆盖率证明（REP 步骤 D）

| 维度 | 应检项数 | 已检 | 未检 | 未检说明 |
|------|---------|------|------|---------|
| 事实核实（步骤A） | 8 | 8 | 0 | - |
| 概念交叉引用（步骤B） | 8 | 8 | 0 | - |
| 审查清单项 | 6 | 6 | 0 | - |
| REQ-ID 反向覆盖项 | 25 | 25 | 0 | - |

## 对抗性自检

- [x] 不存在“我知道意思但文本没写清”的地方
- [x] 所有“可选/或者/暂不”表述已收敛为单一口径
- [x] 高风险项已在本阶段收敛

## 收敛判定

- P0(open): 0
- P1(open): 0
- P2(open): 0
- 结论：✅ 通过

## 证据清单

### 1. Planning 反向覆盖门禁

**命令：**
```bash
bash -lc 'source .aicoding/scripts/lib/review_gate_common.sh && review_gate_validate_plan_reverse_coverage requirements docs/v2.7/requirements.md plan docs/v2.7/plan.md'
```

**输出：**
```text
退出码=0（无输出即通过）
```

**定位：**
- `docs/v2.7/plan.md:77`
- `docs/v2.7/requirements.md:456`

### 2. R6 引用存在性差集自检

**命令：**
```bash
bash -lc 'VERSION="v2.7"; rg -o "REQ-C?[0-9]{3}" docs/${VERSION}/plan.md | LC_ALL=C sort -u > /tmp/plan_refs_${VERSION}.txt; rg "^#### REQ-C?[0-9]{3}[：:]" docs/${VERSION}/requirements.md | sed "s/^#### //;s/[：:].*$//" | tr -d "\r" | LC_ALL=C sort -u > /tmp/req_defs_${VERSION}.txt; echo "plan_only:"; LC_ALL=C comm -23 /tmp/plan_refs_${VERSION}.txt /tmp/req_defs_${VERSION}.txt; echo "req_only:"; LC_ALL=C comm -23 /tmp/req_defs_${VERSION}.txt /tmp/plan_refs_${VERSION}.txt'
```

**输出：**
```text
plan_only:
req_only:
```

**定位：**
- `docs/v2.7/plan.md:62`
- `docs/v2.7/requirements.md:456`

### 3. 任务数、验证数与 REQ 覆盖计数

**命令：**
```bash
bash -lc 'echo tasks=$(rg "^### T[0-9]{3}:" docs/v2.7/plan.md | wc -l); echo validations=$(rg "^\*\*验证方式\*\*" docs/v2.7/plan.md | wc -l); echo reqs=$(rg -o "REQ-C?[0-9]{3}" docs/v2.7/requirements.md | sort -u | wc -l); echo reqs_in_plan=$(rg -o "REQ-C?[0-9]{3}" docs/v2.7/plan.md | sort -u | wc -l)'
```

**输出：**
```text
tasks=9
validations=9
reqs=25
reqs_in_plan=25
```

**定位：**
- `docs/v2.7/plan.md:82`
- `docs/v2.7/plan.md:402`

### 4. Runtime / 前端 / 开关 / 主文档同步关键锚点

**命令：**
```bash
rg -n '^### T00[1-9]|ENABLE_V27_PROFILE_SCHEMA|profile/execution-status|ServiceGovernancePage|SystemListConfigPage|pyproject\.toml|系统功能说明书|用户手册' docs/v2.7/plan.md docs/v2.7/design.md
```

**输出：**
```text
docs/v2.7/plan.md:92:- 在 `backend/config/config.py` 与 `.env.backend*` 中补齐 `ENABLE_V27_PROFILE_SCHEMA`、`ENABLE_V27_RUNTIME`、`ENABLE_SERVICE_GOVERNANCE_IMPORT`、`ENABLE_SYSTEM_CATALOG_PROFILE_INIT`，并固定 `.env.backend.internal` 为验收/生产后端配置源。
docs/v2.7/plan.md:294:- 修改 `frontend/src/pages/SystemProfileImportPage.js`，只保留三类 PM 文档卡片，删除 `history_report` / `esb` 常量与模板映射，并把轮询切到 `profile/execution-status`。
docs/v2.7/plan.md:295:- 修改 `frontend/src/pages/SystemProfileBoardPage.js` 读取 `profile_data.<domain>.canonical`，新增 `extensions` 与 Memory 入口；新增 `frontend/src/pages/ServiceGovernancePage.js` 承载 admin 服务治理页。
docs/v2.7/plan.md:339:- 评估并同步 `docs/系统功能说明书.md`、`docs/用户手册.md`；若判定本期不适用，需在 `docs/v2.7/status.md` 留下明确结论，而不是保持悬空勾选。
docs/v2.7/design.md:763:| API-003 | GET | `/api/v1/system-profiles/{system_id}/profile/execution-status` | query: 无 | `ProfileExecutionStatusResponse` | `AUTH_001` / `PROFILE_002` | 新增；保留 `/profile/extraction-status` alias | Runtime 状态查询 |
docs/v2.7/design.md:1248:- 新增 `ServiceGovernancePage`：
docs/v2.7/design.md:1325:| TEST-013 | REQ-C007 | `pyproject.toml` / `requirements.txt` / `backend/requirements.txt` / `frontend/package.json` 运行时依赖 diff | static check | AI | 依赖 diff 命令 |
```

**定位：**
- `docs/v2.7/plan.md:92`
- `docs/v2.7/plan.md:294`
- `docs/v2.7/plan.md:339`
- `docs/v2.7/design.md:763`
- `docs/v2.7/design.md:1248`
- `docs/v2.7/design.md:1325`

### 5. 本轮直接修复项复核

**命令：**
```bash
rg -n 'git diff --unified=0 v2.6 -- pyproject.toml requirements.txt backend/requirements.txt frontend/package.json|SystemListConfigPage\.js|MainSystemConfigPage\.js|系统功能说明书|用户手册' docs/v2.7/plan.md
```

**输出：**
```text
docs/v2.7/plan.md:276:- 命令：`git diff --unified=0 v2.6 -- pyproject.toml requirements.txt backend/requirements.txt frontend/package.json`
docs/v2.7/plan.md:296:- 修改 `frontend/src/pages/SystemListConfigPage.js` / `frontend/src/pages/MainSystemConfigPage.js` / `frontend/src/App.js` / `frontend/src/components/MainLayout.js`，使系统清单页仅保留单一导入视图，不再展示子系统 tab，并新增 `/admin/service-governance` 路由。
docs/v2.7/plan.md:339:- 评估并同步 `docs/系统功能说明书.md`、`docs/用户手册.md`；若判定本期不适用，需在 `docs/v2.7/status.md` 留下明确结论，而不是保持悬空勾选。
docs/v2.7/plan.md:395:- 命令：`git diff --unified=0 v2.6 -- pyproject.toml requirements.txt backend/requirements.txt frontend/package.json`
```

**定位：**
- `docs/v2.7/plan.md:276`
- `docs/v2.7/plan.md:296`
- `docs/v2.7/plan.md:339`
- `docs/v2.7/plan.md:395`

<!-- REVIEW-SUMMARY-BEGIN -->
REVIEW_STAGE: planning
REVIEW_RESULT: pass
P0_OPEN: 0
P1_OPEN: 0
RVW_TOTAL: 3
REVIEWER: Codex
REVIEW_AT: 2026-03-13
VERIFICATION_COMMANDS: bash -lc 'source .aicoding/scripts/lib/review_gate_common.sh && review_gate_validate_plan_reverse_coverage requirements docs/v2.7/requirements.md plan docs/v2.7/plan.md'; bash -lc 'VERSION="v2.7"; rg -o "REQ-C?[0-9]{3}" docs/${VERSION}/plan.md | LC_ALL=C sort -u > /tmp/plan_refs_${VERSION}.txt; rg "^#### REQ-C?[0-9]{3}[：:]" docs/${VERSION}/requirements.md | sed "s/^#### //;s/[：:].*$//" | tr -d "\r" | LC_ALL=C sort -u > /tmp/req_defs_${VERSION}.txt; echo "plan_only:"; LC_ALL=C comm -23 /tmp/plan_refs_${VERSION}.txt /tmp/req_defs_${VERSION}.txt; echo "req_only:"; LC_ALL=C comm -23 /tmp/req_defs_${VERSION}.txt /tmp/plan_refs_${VERSION}.txt'; bash -lc 'echo tasks=$(rg "^### T[0-9]{3}:" docs/v2.7/plan.md | wc -l); echo validations=$(rg "^\*\*验证方式\*\*" docs/v2.7/plan.md | wc -l); echo reqs=$(rg -o "REQ-C?[0-9]{3}" docs/v2.7/requirements.md | sort -u | wc -l); echo reqs_in_plan=$(rg -o "REQ-C?[0-9]{3}" docs/v2.7/plan.md | sort -u | wc -l)'; rg -n '^### T00[1-9]|ENABLE_V27_PROFILE_SCHEMA|profile/execution-status|ServiceGovernancePage|SystemListConfigPage|pyproject\.toml|系统功能说明书|用户手册' docs/v2.7/plan.md docs/v2.7/design.md; rg -n 'git diff --unified=0 v2.6 -- pyproject.toml requirements.txt backend/requirements.txt frontend/package.json|SystemListConfigPage\.js|MainSystemConfigPage\.js|系统功能说明书|用户手册' docs/v2.7/plan.md
<!-- REVIEW-SUMMARY-END -->

## 多轮审查追加格式
> 见 `templates/review_skeleton.md` 的"多轮审查追加格式"章节
