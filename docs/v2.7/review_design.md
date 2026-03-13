# Review Report：Design / v2.7

> **共享章节**：见 `templates/review_skeleton.md`
> 本模板只包含 Design 阶段特定的审查内容

> 轻量审查模板：聚焦需求覆盖充分性、架构合理性、风险识别、API 契约完整性。
> 不含 GWT 逐条判定表（Design 阶段无代码产出，无需 GWT 粒度判定）。

| 项 | 值 |
|---|---|
| 阶段 | Design |
| 版本号 | v2.7 |
| 日期 | 2026-03-13 |
| 审查范围 | `docs/v2.7/design.md` |
| 输入材料 | `docs/v2.7/requirements.md`, `docs/v2.7/design.md`, `docs/技术方案设计.md` |

## §0 审查准备（REP 步骤 A+B）

### A. 事实核实
> 从 design.md 提取事实性声明，逐条对照 requirements.md（REQ/REQ-C 清单）核实；按需查阅技术方案设计.md。

| # | 声明（出处） | 核实源 | 结论 |
|---|------------|--------|------|
| 1 | 设计采用“FastAPI 单体内模块化 Runtime + 文件存储 Memory”，且不新增外部运行时依赖（design §0 / §0.5 / §3.3） | `requirements.md` REQ-005、REQ-C006、REQ-C007；`技术方案设计.md` 部署基线 | ✅ |
| 2 | 正式画像唯一口径为 `profile_data.<domain>.canonical`，旧 `fields` 与旧 schema 键不再保留（design §0.5 / §5.2.1） | `requirements.md` REQ-002、REQ-C002、REQ-101 | ✅ |
| 3 | 空画像判定只看 D1-D5 canonical，忽略 `field_sources`、`ai_suggestions`、Memory（design §5.2.4 / §5.3.3） | `requirements.md` REQ-004、REQ-009、REQ-C008 | ✅ |
| 4 | Runtime 至少包含 Registry、Router、Scene Executor、Policy Gate、Memory Reader/Writer，且交付 6 个内置 Skill；其中 `code_scan_skill` 支持 `repo_path` / `repo_archive` 双入口（design §5.1 / §5.1.1 / §5.1.2） | `requirements.md` REQ-005、REQ-103、REQ-C004 | ✅ |
| 5 | 服务治理导入以 D3 `auto_apply` 为主，D1/D4 只允许 `draft_apply/suggestion_only`，不得覆盖 `manual`（design §5.1.1 / §5.3.2） | `requirements.md` REQ-003、REQ-009、REQ-C003 | ✅ |
| 6 | 系统清单 confirm 仅对空画像 `auto_apply`，非空画像返回 `profile_not_blank`，且不写 `ai_suggestions`（design §5.3.3 / API-008） | `requirements.md` REQ-004、REQ-009、REQ-C008 | ✅ |
| 7 | 系统识别通过 Direct Decision + LLM 补强统一输出 `final_verdict`（design §5.3.4） | `requirements.md` REQ-008、REQ-C005 | ✅ |
| 8 | Memory 至少支持 `profile_update`、`identification_decision`、`function_point_adjustment`，并可扩展未来类型（design §5.2.2 / §5.2.3） | `requirements.md` REQ-007、REQ-010、REQ-104、REQ-C004 | ✅ |
| 9 | 对外新增 `profile/execution-status`，同时保留 `profile/extraction-status` 兼容别名；现有主链路不改入口（design §0 / §5.4 API-003 / §6.1.1） | `requirements.md` REQ-001、REQ-011、REQ-C006 | ✅ |
| 10 | 部署策略为“备份 + 清理旧数据 + 开关灰度 + 可执行回滚”（design §6.1.2 / §6.1.3） | `requirements.md` REQ-012、REQ-105、REQ-C002 | ✅ |
| 11 | 生产/验收环境按内网配置源落盘，后端明确使用 `.env.backend.internal`，前端配置源单列（design §0.5 / §6.0） | `requirements.md` 约束口径；`lessons_learned.md` R9 | ✅ |
| 12 | 系统清单设计已收敛为单一系统清单模板与请求体，不再包含子系统清单或子系统映射（design §1.1 / §5.3.3 / API-007 / API-008） | `requirements.md` REQ-004、REQ-006；用户 2026-03-13 决策 | ✅ |
| 13 | 系统清单字段映射已收敛为“高确定性入 canonical、弱证据进 extensions、责任台账字段忽略”，且 `功能描述` / `关联系统` 的落位被单独固定（design §5.3.3） | `requirements.md` REQ-004、REQ-009、REQ-C008 | ✅ |
| 14 | 文档类 skill 的本期有效性边界已收敛：`requirements_skill` / `tech_solution_skill` 基于样本做有效设计，`design_skill` 暂为保守设计，且仅支持可直接抽文本的 `docx` / 文本型 `pdf` / `pptx`（design §5.1.3） | `requirements.md` REQ-006；用户 2026-03-13 决策 | ✅ |

### B. 关键概念交叉引用
> 提取关键概念（模块名/接口名、API 路径、数据结构字段、错误码、配置项），全文搜索所有出现位置。

| 概念 | 出现位置 | 口径一致 |
|------|---------|---------|
| `SkillRegistry` | design §5.1, §5.1.1 | ✅ |
| `BlankProfileEvaluator` | design §5.1.1, §5.2.4, §5.3.3, §8.1 | ✅ |
| `profile/execution-status` | design §0, §4.3, §5.4 API-003, §5.10, §6.1.1, §7.2 | ✅ |
| `profile/extraction-status` | design §0, §4.3, §5.4 API-003, §5.10, §6.1.1, §7.2 | ✅ |
| `memory_records.json` | design §0.5, §4.2, §5.1, §5.2.2, §5.7, §5.9 | ✅ |
| `runtime_executions.json` | design §0.5, §4.2, §5.1, §5.2.2, §5.9 | ✅ |
| `final_verdict` | design §5.2.3, §5.3.4, API-009 附近内部结果说明, §5.7, §7.1 | ✅ |
| `profile_not_blank` | design §5.2.3, §5.3.3, API-008, §5.7 | ✅ |
| `manual` 优先 | design §4.2, §5.2.2, §5.3.2, §5.3.5 | ✅ |
| `mapping_incomplete` | design §5.2.3, API-008 | ✅ |
| `.env.backend.internal` | design §0.5, §6.0 | ✅ |
| `catalog_related_systems` | design §5.3.3 | ✅ |
| `CodeScanSkillAdapter` | design §5.1, §5.1.2, §5.3.6 | ✅ |
| `requirements_skill` / `tech_solution_skill` / `design_skill` 有效性边界 | design §5.1.3 | ✅ |

## 审查清单

- [x] 与需求一一对应：关键设计点能追溯到 REQ/SCN
- [x] 依赖关系合理：无循环依赖，职责边界清晰
- [x] 失败路径充分：最常见失败模式与降级/重试策略明确
- [x] 兼容与回滚：数据/接口/配置的向后兼容与回滚可执行
- [x] 安全设计：鉴权/越权/输入验证/敏感数据处理明确
- [x] API 契约完整：新增/变更 API 已写明路径/参数/返回/权限/错误码
- [x] REQ-C 覆盖：每条禁止项在设计中有对应防护措施

## 需求覆盖判定

| REQ-ID | 设计覆盖 | 对应章节 | 备注 |
|--------|---------|---------|------|
| REQ-001 | ✅ | §5.3.1 / §5.4 API-001 / §5.10 | PM 导入页收敛到三类文档 |
| REQ-002 | ✅ | §5.2.1 / §5.10 | 5 域 24 字段 canonical schema |
| REQ-003 | ✅ | §5.1 / §5.3.2 / API-006 | admin 服务治理导入 |
| REQ-004 | ✅ | §5.2.4 / §5.3.3 / API-008 | 首次初始化/补空、非空 skip |
| REQ-005 | ✅ | §4.2 / §5.1 / §5.1.1 | Runtime 平台组件与 Scene 矩阵 |
| REQ-006 | ✅ | §5.1 / §5.2.1 / §5.3 | 多格式输入 canonical 化 |
| REQ-007 | ✅ | §5.2.2 / API-009 | Memory 模型与查询 |
| REQ-008 | ✅ | §5.3.4 | Direct Decision + `final_verdict` |
| REQ-009 | ✅ | §5.1.1 / §5.3.1~§5.3.5 | 场景化策略矩阵 |
| REQ-010 | ✅ | §5.3.5 | 功能点拆解读写 Memory |
| REQ-011 | ✅ | §5.3.1~§5.3.5 / §5.4 | `failed/partial_success` 口径 |
| REQ-012 | ✅ | §6.1.2 / §6.1.3 / §7.1 | 清理与回滚 |
| REQ-101 | ✅ | §5.2.1 | 字段数达标 |
| REQ-102 | ✅ | §5.3.2 / §5.7 / §7.1 | 治理导入成功率指标 |
| REQ-103 | ✅ | §5.1 / §5.1.1 / §7.1 | Skill 与 Scene 覆盖 |
| REQ-104 | ✅ | §5.2.2 / §7.1 | Memory 覆盖率 |
| REQ-105 | ✅ | §6.1.2 / §7.1 | 清理核验 |
| REQ-C001 | ✅ | §5.3.1 / API-001 / §5.10 | 旧入口不再保留 |
| REQ-C002 | ✅ | §5.2.1 / §6.1.2 | 旧 schema 与旧数据清理 |
| REQ-C003 | ✅ | §5.2.2 / §5.3.2 / §5.3.5 | `manual` 优先 |
| REQ-C004 | ✅ | §5.1 / §5.2.2 | Skill / Memory 可扩展 |
| REQ-C005 | ✅ | §5.3.4 | `final_verdict` 强制输出 |
| REQ-C006 | ✅ | §4.3 / §6.1.1 / §7.1 | 主链路兼容 |
| REQ-C007 | ✅ | §0.5 / §3.3 | 无新增外部依赖 |
| REQ-C008 | ✅ | §5.2.4 / §5.3.3 / API-008 | 非空画像禁更 |

## 高风险语义审查（必做）

> 来源：lessons_learned "Design 自审过度依赖追溯门禁导致漏检"。以下高风险点已逐条检查。

- [x] REQ-C 禁止项：每条在设计中有明确防护措施
- [x] 兼容跳转语义：本次无前端路由跳转语义变更；兼容点集中在 API alias，文本已收敛为单一口径
- [x] 新增 API 契约：`profile/execution-status`、`memory`、`esb/imports`、`system-list/confirm` 等均写明路径/参数/返回/权限/错误码
- [x] “可选/二选一/仅提示”表述：高风险行为已收敛；系统清单场景无“可选覆盖”或“可人工接受建议”的模糊口径
- [x] 回滚路径：数据/接口/开关的回滚步骤可执行

## 关键发现

本轮无 P0 / P1 / P2 新发现。

## §3 覆盖率证明（REP 步骤 D）

| 维度 | 应检项数 | 已检 | 未检 | 未检说明 |
|------|---------|------|------|---------|
| 事实核实（步骤A） | 14 | 14 | 0 | - |
| 概念交叉引用（步骤B） | 14 | 14 | 0 | - |
| 审查清单项 | 7 | 7 | 0 | - |
| REQ-ID 覆盖项 | 25 | 25 | 0 | - |

## 对抗性自检

- [x] 不存在“我知道意思但文本没写清”的地方
- [x] 所有新增/变更 API 都有完整契约
- [x] 所有“可选/或者/暂不”表述已收敛为单一口径
- [x] 高风险项已在本阶段收敛

## 收敛判定

- P0(open): 0
- P1(open): 0
- 结论：✅ 通过

## 证据清单

### 1. Design 追溯覆盖门禁

**命令：**
```bash
bash -lc 'source .aicoding/scripts/lib/review_gate_common.sh && review_gate_validate_design_trace_coverage requirements docs/v2.7/requirements.md design docs/v2.7/design.md'
```

**输出：**
```text
退出码=0（无输出即通过）
```

**定位：**
- `docs/v2.7/design.md:108`
- `docs/v2.7/requirements.md:575`

### 2. Design API 契约完整性门禁

**命令：**
```bash
bash -lc 'source .aicoding/scripts/lib/review_gate_common.sh && review_gate_validate_design_api_contracts design docs/v2.7/design.md'
```

**输出：**
```text
退出码=0（无输出即通过）
```

**定位：**
- `docs/v2.7/design.md:757`
- `docs/v2.7/design.md:1045`

### 3. 现有后端路由与设计变更点对照

**命令：**
```bash
rg -n 'profile/extraction-status|profile/import-history|/batch-import/preview|/batch-import/confirm|@router.post\("/imports"\)|@router.post\("/\{system_name\}/publish"\)' backend/api/system_profile_routes.py backend/api/esb_routes.py backend/api/system_list_routes.py docs/v2.7/design.md
```

**输出：**
```text
docs/v2.7/design.md:763:| API-003 | GET | `/api/v1/system-profiles/{system_id}/profile/execution-status` | query: 无 | `ProfileExecutionStatusResponse` | `AUTH_001` / `PROFILE_002` | 新增；保留 `/profile/extraction-status` alias | Runtime 状态查询 |
docs/v2.7/design.md:768:| API-008 | POST | `/api/v1/system-list/batch-import/confirm` | `CatalogConfirmRequest` | `CatalogConfirmResponse` | `AUTH_001` / `CATALOG_001` / `CATALOG_002` / `MEMORY_001` | 保持现有路径；扩展响应字段 | confirm + Runtime 联动 |
docs/v2.7/design.md:900:- `GET /api/v1/system-profiles/{system_id}/profile/extraction-status` 作为兼容别名返回相同结构，至少保留到 v2.8。
backend/api/esb_routes.py:161:@router.post("/imports")
backend/api/system_list_routes.py:605:@router.post("/batch-import/confirm", dependencies=[Depends(require_system_list_admin)])
backend/api/system_profile_routes.py:893:@router.get("/{system_id}/profile/import-history")
backend/api/system_profile_routes.py:910:@router.get("/{system_id}/profile/extraction-status")
backend/api/system_profile_routes.py:1214:@router.post("/{system_name}/publish")
```

**定位：**
- `backend/api/system_profile_routes.py:910`
- `docs/v2.7/design.md:763`
- `docs/v2.7/design.md:1045`

### 4. 系统识别现状缺口与设计收敛点对照

**命令：**
```bash
rg -n "final_verdict|candidate_systems|maybe_systems|questions|BlankProfileEvaluator|profile_not_blank|manual_conflict|mapping_incomplete" backend/agent/system_identification_agent.py docs/v2.7/design.md
```

**输出：**
```text
backend/agent/system_identification_agent.py:235:            questions = result.get("questions") or []
backend/agent/system_identification_agent.py:236:            maybe_systems = result.get("maybe_systems") or []
backend/agent/system_identification_agent.py:374:            "candidate_systems": self._last_candidate_systems or [],
docs/v2.7/design.md:302:| `system_identification` | 需求文本 | `DirectDecisionResolver -> LLMResolver(必要时) -> MemoryWriter` | sync | 直接输出 `final_verdict` |
docs/v2.7/design.md:560:空画像判定器 `BlankProfileEvaluator` 只看 `profile_data.<domain>.canonical`，忽略 `field_sources`、`ai_suggestions`、Memory：
docs/v2.7/design.md:676:   - 画像存在且 non-blank：返回 `skipped_items.reason=profile_not_blank`，不写 `profile_data`，不写 `ai_suggestions`。
docs/v2.7/design.md:1073:      reason: 'profile_not_blank' | 'profile_not_found' | 'mapping_incomplete';
```

**定位：**
- `backend/agent/system_identification_agent.py:235`
- `backend/agent/system_identification_agent.py:374`
- `docs/v2.7/design.md:302`
- `docs/v2.7/design.md:560`
- `docs/v2.7/design.md:676`
- `docs/v2.7/design.md:1073`

### 5. 子系统概念清除、内网配置与代码扫描 Skill 收敛检查

**命令：**
```bash
bash -lc 'if rg -n "mappings_total|mappings_error|mappings: Array<Record<string, unknown>>" docs/v2.7/design.md; then exit 1; else rg -n "\\.env\\.backend\\.internal|catalog_related_systems|CodeScanSkillAdapter|repo_archive|repo_path" docs/v2.7/proposal.md docs/v2.7/requirements.md docs/v2.7/design.md; fi'
```

**输出：**
```text
docs/v2.7/proposal.md:112:  - `关联系统` 仅进入 `D3.extensions.catalog_related_systems`，不直接写入 D3 canonical
docs/v2.7/requirements.md:677:- `code_scan_skill` 必须支持 `repo_path` 与源码压缩包两种输入源，并通过统一 skill 定义暴露给 Runtime。
docs/v2.7/design.md:49:| 后端配置源 | `.env.backend` / `.env.backend.example` | `.env.backend.internal` | `.env.backend.internal` | 是 | 验收与生产均为内网后端配置源 |
docs/v2.7/design.md:288:| `CodeScanSkillAdapter` | 复用现有代码扫描 API/Service，统一 `repo_path` 与源码压缩包输入，合并 Java 与 JS/TS 中度扫描结果 | `run(payload, context)` | D4 suggestions, breakdown context | `code_scan_routes`, `code_scan_service` |
```

### 6. 文档类 Skill 有效性边界检查

**命令：**
```bash
rg -n '文本型 `pdf`|requirements_skill|tech_solution_skill|design_skill|保守设计|有效设计' docs/v2.7/requirements.md docs/v2.7/design.md
```

**输出：**
```text
docs/v2.7/requirements.md:712:- PM 文档类 skill 在 v2.7 的输入格式边界固定为可直接抽文本的 `docx`、文本型 `pdf`、`pptx`；扫描件 PDF、纯图片型 PPTX/OCR 场景不属于本期有效性目标。
docs/v2.7/design.md:331:| `requirements_skill` | `req-temp1.docx`、`req-temp2.docx`、`req-temp3.docx` | D1 / D2 / D5 为主；少量 D3 / D4 弱证据 | 有效设计 | 三份样本虽格式不同，但都稳定提供概述、范围、流程、功能、角色、约束类信息 |
docs/v2.7/design.md:332:| `tech_solution_skill` | `arch-temp.docx` | D4 / D5 为主；补充 D2 / D3 | 有效设计 | 技术方案样本稳定包含架构、部署、接口、技术栈、风险与实施约束，且大量证据在表格中 |
docs/v2.7/design.md:333:| `design_skill` | 暂无真实样本 | D2 / D4 / D5 | 保守设计 | v2.7 先接入统一解析链路，但不承诺高质量字段提取；默认只输出 `suggestion_only` |
```

<!-- REVIEW-SUMMARY-BEGIN -->
REVIEW_STAGE: design
REVIEW_RESULT: pass
P0_OPEN: 0
P1_OPEN: 0
RVW_TOTAL: 0
REVIEWER: Codex
REVIEW_AT: 2026-03-13
VERIFICATION_COMMANDS: bash -lc 'source .aicoding/scripts/lib/review_gate_common.sh && review_gate_validate_design_trace_coverage requirements docs/v2.7/requirements.md design docs/v2.7/design.md'; bash -lc 'source .aicoding/scripts/lib/review_gate_common.sh && review_gate_validate_design_api_contracts design docs/v2.7/design.md'; rg -n 'profile/extraction-status|profile/import-history|/batch-import/preview|/batch-import/confirm|@router.post\\(\"/imports\"\\)|@router.post\\(\"/\\{system_name\\}/publish\"\\)' backend/api/system_profile_routes.py backend/api/esb_routes.py backend/api/system_list_routes.py docs/v2.7/design.md; rg -n 'final_verdict|candidate_systems|maybe_systems|questions|BlankProfileEvaluator|profile_not_blank|manual_conflict|mapping_incomplete' backend/agent/system_identification_agent.py docs/v2.7/design.md; bash -lc 'if rg -n "mappings_total|mappings_error|mappings: Array<Record<string, unknown>>" docs/v2.7/design.md; then exit 1; else rg -n "\\.env\\.backend\\.internal|catalog_related_systems|CodeScanSkillAdapter|repo_archive|repo_path" docs/v2.7/proposal.md docs/v2.7/requirements.md docs/v2.7/design.md; fi'; rg -n '文本型 `pdf`|requirements_skill|tech_solution_skill|design_skill|保守设计|有效设计' docs/v2.7/requirements.md docs/v2.7/design.md
<!-- REVIEW-SUMMARY-END -->
