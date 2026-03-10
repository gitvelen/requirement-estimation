# Review Report：Design / v2.6

> 轻量审查模板：聚焦需求覆盖充分性、架构合理性、风险识别、API 契约完整性。
> 不含 GWT 逐条判定表（Design 阶段无代码产出，无需 GWT 粒度判定）。

| 项 | 值 |
|---|---|
| 阶段 | Design |
| 版本号 | v2.6 |
| 日期 | 2026-03-09 |
| 审查范围 | `docs/v2.6/design.md` |
| 输入材料 | `docs/v2.6/requirements.md`, `docs/v2.6/design.md` |

## §0 审查准备（REP 步骤 A+B）

### A. 事实核实
> 从 design.md 提取事实性声明，逐条对照 requirements.md（REQ/REQ-C 清单）核实；按需查阅技术方案设计.md。

| # | 声明（出处） | 核实源 | 结论 |
|---|------------|--------|------|
| 1 | 设计要求导入接口以内存透传完整 `document_text`，避免从向量分片反拼接（design §0 / §5.3.1） | `requirements.md` REQ-001、REQ-C001 | ✅ |
| 2 | Stage 预算采用 `LLM_MAX_CONTEXT_TOKENS=32000`、`LLM_INPUT_MAX_TOKENS=25000`，并扣减输出与安全边界（design §0.5 / §5.3.1） | `requirements.md` §1.3 关键口径、REQ-001、REQ-103 | ✅ |
| 3 | Stage2 输出预算使用运行时公式 `32000 - actual_input_tokens - safety_tokens`（design §5.3.2） | `requirements.md` §1.3、proposal §解决方案概述 | ✅ |
| 4 | 关闭分块开关后，超长文档显式失败且不截断（design §5.3.4 / §6.1.3） | `requirements.md` REQ-004、REQ-C001、§6.2 错误码表 | ✅ |
| 5 | 任一块失败时整次任务失败，不写入部分 suggestions（design §5.3.2 / §5.3.4） | `requirements.md` REQ-001、REQ-002 | ✅ |
| 6 | 对外 API 路径、权限、响应包络保持兼容（design §4.3 / §5.4） | `requirements.md` REQ-C003、§5.1 权限矩阵、§6.2 错误码 | ✅ |
| 7 | 不引入新运行时依赖，仍使用启发式 Token 估算（design §3.2 / §3.3） | `requirements.md` REQ-C002 | ✅ |
| 8 | 仅记录 Token/Chunk/Latency/失败块索引，不记录正文（design §5.7 / §5.8） | `requirements.md` §5.2 客户信息与合规、REQ-101、REQ-103 | ✅ |

### B. 关键概念交叉引用
> 提取关键概念（模块名/接口名、API 路径、数据结构字段、错误码、配置项），全文搜索所有出现位置。

| 概念 | 出现位置 | 口径一致 |
|------|---------|---------|
| `context_override` | design §4.2, §4.3, §5.3.1 | ✅ |
| `LLM_MAX_CONTEXT_TOKENS` | design §0.5, §5.3.1, §5.6, §6.0 | ✅ |
| `LLM_INPUT_MAX_TOKENS` | design §0.5, §5.3.1, §5.6, §5.7 | ✅ |
| `ENABLE_LLM_CHUNKING` | design §0, §5.3.4, §5.6, §6.1.3 | ✅ |
| `PROFILE_IMPORT_FAILED` | design §1.4, §5.3.4, §5.4 | ✅ |
| `/api/v1/knowledge/imports` | design §0.5, §5.4 API-001 | ✅ |
| `/api/v1/system-profiles/{system_id}/profile/import` | design §0.5, §5.4 API-002 | ✅ |
| `/api/v1/system-profiles/{system_id}/profile/extraction-status` | design §5.4 API-003 | ✅ |
| `CHUNK_PARAGRAPH_TOO_LONG` / `CHUNKING_DISABLED_OVERSIZE` / `CHUNK_PROCESSING_FAILED` | design §5.3.1, §5.3.4, §5.4 | ✅ |
| `module_structure` / `integration_points` / `key_constraints` | design §5.3.2, §7.1 | ✅ |

## 审查清单

- [x] 与需求一一对应：关键设计点能追溯到 REQ/SCN
- [x] 依赖关系合理：无循环依赖，职责边界清晰
- [x] 失败路径充分：最常见失败模式与降级/重试策略明确
- [x] 兼容与回滚：数据/接口/配置的向后兼容与回滚可执行
- [x] 安全设计：鉴权/越权/输入验证/敏感数据处理明确
- [x] API 契约完整：受影响 API 已写明路径/参数/返回/权限/错误码
- [x] REQ-C 覆盖：每条禁止项在设计中有对应防护措施

## 需求覆盖判定

| REQ-ID | 设计覆盖 | 对应章节 | 备注 |
|--------|---------|---------|------|
| REQ-001 | ✅ | §5.1 / §5.3.1 | 分块、预算、透传原文 |
| REQ-002 | ✅ | §5.1 / §5.3.2 | Stage1/Stage2 合并策略明确 |
| REQ-003 | ✅ | §5.3.3 / §5.9 | 单次调用路径单独定义 |
| REQ-004 | ✅ | §5.3.4 / §5.6 / §6.1.3 | 开关、错误提示、回滚可执行 |
| REQ-101 | ✅ | §5.7 / §7.1 | Token/Chunk 日志与测试证据 |
| REQ-102 | ✅ | §7.1 | 覆盖率命令与测试资产明确 |
| REQ-103 | ✅ | §5.7 / §5.9 / §7.1 | latency 指标与阈值明确 |
| REQ-C001 | ✅ | §3.2 / §5.2 / §5.3.1 | 原文以内存透传，不从向量分片反推 |
| REQ-C002 | ✅ | §3.2 / §3.3 / §6.1.1 | 明确拒绝新增依赖 |
| REQ-C003 | ✅ | §4.3 / §5.4 | API 契约不变并有回归计划 |
| REQ-C004 | ✅ | §5.2 / §5.3.1 / §5.6 | `stage_budget` 与 chunk 校验明确 |

## 高风险语义审查（必做）

> 来源：lessons_learned "Design 自审过度依赖追溯门禁导致漏检"。以下高风险点已逐条检查。

- [x] REQ-C 禁止项：每条在设计中有明确防护措施
- [x] 兼容跳转语义：本次无前端跳转/replace/push 变更，不存在未收敛跳转语义
- [x] 新增 API 契约：本次无新增 HTTP API；受影响 API 的路径/参数/返回/权限/错误码均完整
- [x] "可选/二选一/仅提示"表述：无影响验收的模糊口径；`可选` 仅用于现有可空参数说明
- [x] 回滚路径：`ENABLE_LLM_CHUNKING=false` 的执行步骤与预期结果已写明

## 关键发现

本轮无 P0 / P1 / P2 新发现。

## §3 覆盖率证明（REP 步骤 D）

| 维度 | 应检项数 | 已检 | 未检 | 未检说明 |
|------|---------|------|------|---------|
| 事实核实（步骤A） | 8 | 8 | 0 | - |
| 概念交叉引用（步骤B） | 10 | 10 | 0 | - |
| 审查清单项 | 7 | 7 | 0 | - |
| REQ-ID 覆盖项 | 11 | 11 | 0 | - |

## 对抗性自检
- [x] 不存在“我知道意思但文本没写清”的地方
- [x] 所有受影响 API 都有完整契约或明确声明“无新增 API”
- [x] 所有“可选/或者/暂不”表述未影响验收口径
- [x] 高风险项已在本阶段收敛

## 收敛判定
- P0(open): 0
- P1(open): 0
- 结论：✅ 通过

<!-- REVIEW-SUMMARY-BEGIN -->
REVIEW_STAGE: design
REVIEW_RESULT: pass
P0_OPEN: 0
P1_OPEN: 0
RVW_TOTAL: 0
REVIEWER: Codex
REVIEW_AT: 2026-03-09
VERIFICATION_COMMANDS: bash -lc 'source .aicoding/scripts/lib/review_gate_common.sh && review_gate_validate_design_trace_coverage requirements docs/v2.6/requirements.md design docs/v2.6/design.md'; bash -lc 'source .aicoding/scripts/lib/review_gate_common.sh && review_gate_validate_design_api_contracts design docs/v2.6/design.md'; rg -n "ENABLE_LLM_CHUNKING|LLM_MAX_CONTEXT_TOKENS|LLM_INPUT_MAX_TOKENS|PROFILE_IMPORT_FAILED|/api/v1/knowledge/imports|/api/v1/system-profiles/.*/profile/import|CHUNK_PARAGRAPH_TOO_LONG|CHUNKING_DISABLED_OVERSIZE|CHUNK_PROCESSING_FAILED|REQ-C00[1-4]" docs/v2.6/design.md
<!-- REVIEW-SUMMARY-END -->
