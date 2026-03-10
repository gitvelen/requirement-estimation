# v2.6 技术方案设计：文档分块处理以适配内网 LLM Token 限制

## 文档信息
| 项 | 值 |
|---|---|
| 状态 | Review |
| 作者 | Codex |
| 评审 | Codex |
| 日期 | 2026-03-09 |
| 版本号 | `v2.6` |
| 关联提案 | `docs/v2.6/proposal.md` v1.1 |
| 关联需求 | `docs/v2.6/requirements.md` v0.4 |
| 关联主文档 | `docs/技术方案设计.md` |
| 关联接口 | `backend/api/system_profile_routes.py` / `backend/api/knowledge_routes.py` |

---
## 0. 摘要（Executive Summary）

v2.6 的设计目标是把系统画像 AI 总结链路从“字符截断 + 单次调用”改为“Token 估算 + 段落级分块 + 两阶段合并”，解决内网 `Qwen3-32B` 32,000 tokens 上下文限制下的超长文档导入失败问题。

本次采用的核心方案是：
- 在 `backend/utils/token_counter.py` 新增轻量级 Token 估算与段落级切块能力，不引入第三方依赖。
- 在 `backend/utils/llm_client.py` 保留现有 `chat()` 兼容入口，同时新增“带 usage 的原始调用”与分块执行/合并辅助能力。
- 在 `backend/service/profile_summary_service.py` 中引入“单次调用 / 分块调用”双路径，并保证任一块失败时整次任务失败、不写入部分建议。
- 文档导入触发链路通过**内存传递原始解析文本**给总结任务，避免依赖知识库向量分片反向拼接，满足 REQ-C001 的“文档内容无损失”。
- 对外 API 路径、权限、响应包络保持不变；回滚依赖 `ENABLE_LLM_CHUNKING=false` 配置开关。

## 0.5 决策记录（Design 前置收集结果）
### 技术决策
| 编号 | 决策项 | 用户选择 | 理由/备注 |
|------|--------|---------|----------|
| D-01 | 实现位置 | 沿用现有 FastAPI 后端与 `profile_summary_service` | 避免新增服务/部署单元，最小必要变更 |
| D-02 | Token 计数策略 | 启发式估算：`字符数 / 2.5` | 满足“无外部依赖”与快速交付约束 |
| D-03 | 分块策略 | 段落级切块，重叠段自适应 `2 -> 1 -> 0` | 同时满足 REQ-C001 与 REQ-C004 |
| D-04 | 原文来源 | 导入接口以内存参数传递原始解析文本 | 避免从知识库 embedding 切片反拼接导致重叠/丢失 |
| D-05 | API 契约 | 保持 `/api/v1/knowledge/imports` 与 `/api/v1/system-profiles/{system_id}/profile/import` 对外契约不变 | 满足 REQ-C003 |
| D-06 | 回滚策略 | 配置开关降级到“单次调用 + 超长文档显式失败” | 满足 REQ-004，可快速止损 |
| D-07 | 段落保留开关 | 不额外暴露“关闭段落保留”配置 | 关闭后会直接冲突 REQ-C001，固定行为更安全 |

### 环境配置
| 配置项 | 开发环境 | 生产环境 | 敏感 | 备注 |
|--------|---------|---------|------|------|
| `DASHSCOPE_API_BASE` | `.env.backend(.example)` 显式声明 | `.env.backend.internal` 显式声明 | 是 | 走 OpenAI 兼容接口 |
| `LLM_MODEL` | `Qwen3-32B`（示例文件显式写出） | `Qwen3-32B` | 否 | 开发/内网保持一致口径 |
| `EMBEDDING_MODEL` | `Qwen3-Embedding-8B`（示例文件显式写出） | `Qwen3-Embedding-8B` | 否 | 满足需求中的环境一致性 |
| `LLM_MAX_CONTEXT_TOKENS` | `32000` | `32000` | 否 | 新增 |
| `LLM_INPUT_MAX_TOKENS` | `25000` | `25000` | 否 | 新增 |
| `LLM_CHUNK_OVERLAP_PARAGRAPHS` | `2` | `2` | 否 | 新增 |
| `ENABLE_LLM_CHUNKING` | `true` | `true` | 否 | 新增回滚开关 |
| `DASHSCOPE_API_KEY` | 示例占位值 | 内网占位值或真实值 | 是 | 不落盘真实密钥 |

## 1. 背景、目标、非目标与约束
### 1.1 背景与问题
- 当前 `profile_summary_service` 通过 [`backend/service/profile_summary_service.py`](backend/service/profile_summary_service.py) 的 `_context_max_chars()` 对上下文做字符截断，再用单次 `llm_client.chat_with_system_prompt()` 调用 Stage1/Stage2。
- 当前导入链路已把文档切成 embedding 用定长窗口片段，但总结服务只抽样 48 个片段并再次字符截断，无法保证原文完整进入 LLM。
- 内网模型 `Qwen3-32B` 上下文窗口为 32,000 tokens，现有逻辑没有 token budget 计算，因此在超长文档场景会稳定触发超限。

### 1.2 目标（Goals，可验收）
- G1：满足 `REQ-001`，对超长文档自动分块处理并保证所有块都在输入预算内。
- G2：满足 `REQ-002`，Stage1/Stage2 结果可稳定合并，且失败时不写入部分结果。
- G3：满足 `REQ-003`，正常文档继续走单次调用路径，不引入额外分块成本。
- G4：满足 `REQ-004`，可通过配置开关回退到“单次调用 + 超长文档显式失败”。
- G5：满足 `REQ-C001`~`REQ-C004`，不丢文档、不加依赖、不改外部 API 契约、不生成超限 chunk。

### 1.3 非目标（Non-Goals）
- 不修改知识库 embedding 分片算法；`knowledge_service._chunk_text()` 仍服务于向量入库。
- 不新增前端页面、路由或交互。
- 不引入数据库 schema、消息队列或独立异步任务系统。
- 不解决非文档来源（如 ESB、代码扫描）材料“全量召回”问题；本次仅保证导入文档原文无损进入总结链路。

### 1.4 关键约束（Constraints）
- C1：不得引入 `tiktoken`、`transformers` 等新依赖。
- C2：对外 API 成功/失败包络保持兼容，尤其 `PROFILE_IMPORT_FAILED` 等顶层错误码不变。
- C3：任一块失败后必须整次失败，不允许落部分 `ai_suggestions`。
- C4：运维必须能通过配置开关快速关闭分块。
- C5：新增日志只记录 Token/分块/耗时/失败索引等技术指标，不记录文档正文。

### 1.5 关键假设（Assumptions）
| 假设 | 可验证方式 | 失效影响 | 兜底策略 |
|---|---|---|---|
| `字符数 / 2.5` 对中英文混合文档足够保守 | 单元测试对 25k/30k/50k 样本验证无超限 | 仍可能超限 | 额外预留 prompt/safety 预算并记录 warning |
| 导入接口在触发总结任务时可获取完整 `text_content` | `tests/test_system_profile_import_api.py` / `tests/test_knowledge_import_api.py` | 无法做到原文无损 | 仅作为 fallback 才回落到旧采样路径 |
| OpenAI 兼容响应包含 `usage` 字段或可安全缺省 | `tests/test_llm_client.py` | 无法记录实际 tokens | 回落为估算 tokens + warning 日志 |
| 代码扫描/ESB 辅助材料的现有采样上限足够小 | 设计约束 + 回归测试 | 静态前缀过大，压缩正文预算 | 对辅助材料维持既有采样上限并优先保障正文预算 |

## 2. 需求对齐与验收口径（Traceability）
### 2.1 需求-设计追溯矩阵（必须）
<!-- TRACE-MATRIX-BEGIN -->
| REQ-ID | 需求摘要 | 设计落点（章节/模块/API/表） | 验收方式/证据 |
|---|---|---|---|
| REQ-001 | 超长文档自动分块处理 | §5.1 `token_counter.py` / §5.3.1 / §5.6 | `tests/test_token_counter.py`、`tests/test_profile_summary_service.py` |
| REQ-002 | Stage1/Stage2 结果深度合并 | §5.1 `llm_client.py` / §5.3.2 | `tests/test_llm_client.py`、`tests/test_profile_summary_service.py` |
| REQ-003 | 正常文档保持单次调用 | §5.3.3 / §5.9 | `tests/test_profile_summary_service.py` |
| REQ-004 | 关闭分块开关后的显式失败/降级 | §5.3.4 / §5.6 / §6.1 | `tests/test_profile_summary_service.py` |
| REQ-101 | Token 超限错误率为 0 | §5.7 / §5.9 / §7 | 单元测试日志、失败索引日志 |
| REQ-102 | 新增代码覆盖率 > 80% | §7.1 | `pytest --cov` 报告 |
| REQ-103 | 分块总耗时受控 | §5.7 / §5.9 / §7 | chunk latency 日志、单元测试 |
| REQ-C001 | 禁止文档内容丢失 | §3.2 / §5.2 / §5.3.1 | 文档重建/段落顺序测试 |
| REQ-C002 | 禁止新增外部依赖 | §3.3 / §6.1 | diff 检查 `requirements.txt` / `pyproject.toml` |
| REQ-C003 | 禁止修改 API 契约 | §4.3 / §5.4 | API 回归测试、契约对比 |
| REQ-C004 | 禁止生成超限 chunk | §5.2 / §5.3.1 / §5.6 | `tests/test_token_counter.py` |
<!-- TRACE-MATRIX-END -->

### 2.2 质量属性与典型场景（Quality Scenarios）
| Q-ID | 质量属性 | 场景描述 | 目标/阈值 | 验证方式 |
|---|---|---|---|---|
| Q-01 | 可用性 | 30,000+ tokens 文档导入 | 0 次 Token 超限 | 分块单元测试 |
| Q-02 | 正确性 | 单个段落本身超过正文预算 | 快速失败，返回固定错误原因 | 单元测试断言错误标签 |
| Q-03 | 一致性 | 第 2 块在重试后失败 | 不写入部分建议，任务状态为 failed | 服务测试 |
| Q-04 | 兼容性 | 外部 API 调用方不升级 | 成功/失败包络不变 | API 回归测试 |
| Q-05 | 性能 | 20,000/25,000 tokens 普通文档 | 仍只执行 1 次 Stage1 + 1 次 Stage2 | 服务测试 |
| Q-06 | 可观测性 | 运行超长文档任务 | 记录 chunk_count / chunk_tokens / latency / failed_chunk_index | 日志断言 |

## 3. 现状分析与方案选型（Options & Trade-offs）
### 3.1 现状与问题定位
- 现状关键路径：导入接口解析文件 -> 写知识库向量片段 -> `trigger_summary()` -> `_build_context()` 抽样拼接 -> `_call_llm()` 截断后单次调用。
- 根因不是“字符阈值太小”，而是**没有 token 预算 + 把导入文档降级成采样片段 + 最终再次字符截断**。
- 不可改动点：对外 API 契约、角色权限、现有异步任务/通知框架、知识库向量切片用途。

### 3.2 方案候选与对比（至少 2 个）
| 方案 | 核心思路 | 优点 | 缺点/风险 | 成本 | 结论 |
|---|---|---|---|---|---|
| A | 继续使用字符截断，只把阈值调大 | 改动小 | 仍无法保证 32k token 内；直接违背 REQ-C001 | 低 | 不采用 |
| B | 新增 Token 估算 + 段落级分块；导入接口把原始文本以内存传给总结任务 | 满足无损、回滚、可测性要求；不改外部 API | 需要同时改 service/utils/api 内部调用 | 中 | 采用 |
| C | 引入外部 token 库或独立预处理服务 | 计数更精确 | 新依赖/新部署形态，违反 REQ-C002 与交付约束 | 高 | 不采用 |

### 3.3 关键技术选型与新增依赖评估
| 组件/依赖 | 选型 | 理由 | 替代方案 | 维护状态 | 安全评估 | 移除/替换成本 | 风险/备注 |
|---|---|---|---|---|---|---|---|
| Token 计数 | 自研启发式估算 | 无外部依赖、可快速交付 | `tiktoken` / `transformers` | 仓内维护 | 无额外供应链风险 | 低 | 精度有限，靠 safety margin 兜底 |
| LLM SDK | 继续使用 `openai.OpenAI` 兼容客户端 | 现网已使用 | 自研 HTTP 调用 | 已存在 | 不新增风险 | 低 | 需补 raw response / usage 支持 |
| 文档原文传递 | 任务提交时内存参数传递 | 不新增持久化副本 | 从向量切片反拼接 | 仓内维护 | 不落盘正文 | 低 | 仅适用于导入触发链路 |

## 4. 总体设计（High-level Design）
### 4.1 系统上下文与边界
| 依赖方/系统 | 用途 | 协议 | SLA/SLO | 失败模式 | 降级/兜底 | Owner |
|---|---|---|---|---|---|---|
| 浏览器 / 前端页面 | 发起文档导入 | HTTP multipart | 现有接口 SLA | 上传失败、权限不足 | 保持现有错误包络 | 前端 |
| FastAPI 导入接口 | 解析文件并触发总结 | 内部 Python 调用 | 请求期成功返回 | 文件解析失败、embedding 失败 | 保持现有 4xx/5xx | 后端 |
| `profile_summary_service` | 执行异步总结任务 | 线程池 | 任务级成功/失败 | LLM 超限、块失败、JSON 非法 | 显式失败，不写部分结果 | 后端 |
| DashScope/OpenAI 兼容 LLM | Stage1/Stage2 推理 | HTTP JSON | 受 `LLM_TIMEOUT` 控制 | 超时、usage 缺失、返回非法 JSON | 重试后失败即终止 | 外部依赖 |
| 知识库/向量存储 | 保留现有导入资料 | 内部 Python 调用 | 现有能力 | 写入失败 | 主导入流程已有错误处理 | 后端 |
| 代码扫描/ESB 数据源 | 辅助上下文 | 文件/本地存储 | best-effort | 数据不存在/读取失败 | 忽略辅助材料，不影响主流程 | 后端 |

### 4.2 架构概述（建议按 C4）
1. 导入接口解析文件后拿到完整 `text_content`。
2. 向量入库仍沿用现有 `knowledge_service._chunk_text()`。
3. 导入成功后，接口通过 `trigger_summary(..., context_override=...)` 把原始文档正文与来源文件名传给后台任务。
4. 总结任务构建 `SummaryContextBundle`：
   - `static_prefix_text`：系统名、代码扫描摘要、ESB 摘要等辅助信息。
   - `chunkable_body_text`：完整原始文档正文。
5. `_call_llm()` 先估算 token：
   - 未超预算：走单次调用。
   - 超预算且开关开启：按段落切块，逐块执行 Stage1/Stage2，再合并。
   - 超预算且开关关闭：显式失败。
6. 任一块失败或返回非法结构，任务整体失败，不调用 `set_ai_suggestions()`。

```mermaid
flowchart TD
    A[导入接口 parse file] --> B[写知识库/向量存储]
    B --> C[trigger_summary(context_override=document_text)]
    C --> D[build SummaryContextBundle]
    D --> E{estimate_tokens <= budget?}
    E -- yes --> F[单次 Stage1 + Stage2]
    E -- no && chunking=true --> G[段落级 chunk plan]
    G --> H[Stage1 per chunk]
    H --> I[merge domains/systems]
    I --> J[Stage2 per chunk]
    J --> K[deep merge suggestions]
    F --> L[set_ai_suggestions]
    K --> L
    H --> M[任一块失败 -> task failed]
    J --> M
    E -- no && chunking=false --> M
```

### 4.3 变更影响面（Impact Analysis）
| 影响面 | 是否影响 | 说明 | 需要迁移/兼容 | Owner |
|---|---|---|---|---|
| API 契约 | 否（外部形态不变） | 仅内部调用多传 `context_override`，HTTP 路径/响应不变 | 需做 API 回归测试 | 后端 |
| 数据库/存储 | 否 | 无 schema 变更；不新增正文持久化副本 | 无 | 后端 |
| 权限与审计 | 否 | 沿用现有 `manager/admin` 与 owner/B 角校验 | 无 | 后端 |
| 性能与容量 | 是 | 超长文档会触发多次 LLM 调用 | 通过日志监控 chunk 数与耗时 | 后端 |
| 运维与监控 | 是 | 新增 Token/Chunk/Latency 指标日志 | 需补环境变量 | 后端/运维 |
| 前端交互 | 否 | 不增字段、不改轮询接口 | 仅保留回归测试 | 前端 |

**Active CR diff-only 影响说明**

| CR 变更点 | 设计影响 |
|---|---|
| `backend/utils` | 新增 `token_counter.py`；增强 `llm_client.py` 的 usage/分块执行/合并工具 |
| `backend/service` | `profile_summary_service.py` 改为 token-aware 双路径执行 |
| `backend/config` | 新增 token/chunking 相关配置项 |
| `backend/api`（内部调用点） | 导入接口增加原始文本透传，但不改变对外 API 契约 |

## 5. 详细设计（Low-level Design）
### 5.1 模块分解与职责（Components）
| 模块 | 职责 | 关键接口 | 关键数据 | 依赖 |
|---|---|---|---|---|
| `backend/utils/token_counter.py` | Token 估算、usage 提取、段落切块、重叠收缩 | `estimate_tokens()`、`extract_usage_from_response()`、`chunk_text()` | `ChunkPlanItem` | 无外部依赖 |
| `backend/utils/llm_client.py` | 原始 chat completion、重试、分块执行、Stage1/Stage2 合并辅助 | `_chat_raw()`、`chat()`、`chat_with_chunking()`、`deep_merge()` | `ChunkExecutionMetric` | OpenAI 兼容 SDK |
| `backend/service/profile_summary_service.py` | 组装上下文、选择单次/分块路径、规范化结果、失败映射 | `trigger_summary()`、`_build_context_bundle()`、`_call_llm()` | `SummaryContextBundle`、`SummaryLLMResult` | `llm_client`、`token_counter` |
| `backend/config/config.py` | 暴露 chunking/token 相关配置 | `settings.*` | 环境变量 | `.env.backend*` |
| `backend/api/system_profile_routes.py` | 系统画像导入后以内存方式透传原始文档正文 | `import_profile_document()` | `text_content` | `profile_summary_service` |
| `backend/api/knowledge_routes.py` | 知识导入（绑定系统）后透传原始文档正文 | `import_knowledge_v2()` | `text_content` | `profile_summary_service` |

### 5.2 数据模型与存储（Data Model）
| 表/集合 | 字段 | 类型 | 约束 | 索引 | 说明 |
|---|---|---|---|---|---|
| `SummaryContextBundle`（内存） | `static_prefix_text` | string | 可空 | N/A | 系统元信息 + 代码扫描/ESB 摘要 |
| `SummaryContextBundle`（内存） | `chunkable_body_text` | string | 文档导入链路必填 | N/A | 原始解析正文，不持久化 |
| `ChunkPlanItem`（内存） | `chunk_index` | int | 从 0 递增 | N/A | 便于日志与失败定位 |
| `ChunkPlanItem`（内存） | `content` | string | `estimated_tokens <= stage_budget` | N/A | 单块正文 |
| `ChunkPlanItem`（内存） | `estimated_tokens` | int | >0 | N/A | 预算判定 |
| `ChunkExecutionMetric`（内存/日志） | `stage` / `chunk_index` / `latency_ms` / `actual_total_tokens` | mixed | 可序列化到日志 | N/A | 观测证据 |

迁移方案：
- 无数据库/文件格式迁移。
- 不新增永久化数据对象。
- `PROFILE_SUMMARY_CONTEXT_MAX_CHARS` 保留为兼容字段，但**不再用于文档导入触发链路的最终裁剪**。

### 5.3 核心流程（Flow）
#### 5.3.1 超长文档分块路径（REQ-001 / REQ-C001 / REQ-C004）

1. 导入接口解析文件得到 `text_content`。
2. 导入接口完成现有入库逻辑后，调用：
   - `trigger_summary(..., reason="document_import"|"knowledge_import", source_file=file_name, context_override={"document_text": text_content, "source_type": "document"})`
3. `ProfileSummaryService._build_context_bundle()` 组装：
   - `static_prefix_text`：系统名、代码扫描摘要、ESB 摘要、少量辅助标签。
   - `chunkable_body_text`：完整 `document_text`。
4. 计算 stage 预算：
   - `prompt_overhead_tokens = estimate_tokens(stage_prompt_without_body)`
   - `stage_budget = min(LLM_INPUT_MAX_TOKENS, LLM_MAX_CONTEXT_TOKENS - reserved_output_tokens - safety_tokens - prompt_overhead_tokens - static_prefix_tokens)`
   - 其中 `reserved_output_tokens`：Stage1 固定 600；Stage2 运行时动态计算但按最小预留 2500 验证。
5. 若 `chunkable_body_text` 的估算 tokens `<= stage_budget`，则转单次路径。
6. 否则调用 `TokenCounter.chunk_text(text, max_tokens=stage_budget, overlap_paragraphs=LLM_CHUNK_OVERLAP_PARAGRAPHS)`：
   - 先按 `\n\n` 切段；
   - 单段超限直接抛 `CHUNK_PARAGRAPH_TOO_LONG`；
   - 拼块时优先追加段落直到接近预算；
   - 为下一块尝试携带 `2` 段重叠，如超限则降为 `1`，再不行则 `0`。
7. 生成的每个块都带 `chunk_index` 与 `estimated_tokens`，写入结构化日志。

**无损保证**
- 文档正文只来自导入阶段的完整 `text_content`，不再从知识库 embedding 定长分片反推正文。
- `chunk_text()` 提供“去重叠后可重建原段落序列”的测试能力，作为 REQ-C001 的直接证据。

#### 5.3.2 Stage1 / Stage2 调用与合并（REQ-002）

**Stage1**
- 输入：`static_prefix_text + 当前 chunk 正文`
- 输出：`relevant_domains[]`、`related_systems[]`
- 合并规则：
  - 按首次出现顺序去重；
  - 任一块缺失 Stage1 根字段、JSON 非法或重试后失败，整次任务失败。

**Stage2**
- 先基于所有 Stage1 结果确定最终 `relevant_domains`。
- 针对每个 chunk 调用 Stage2，并在每块返回后做 canonical normalize：
  - `stage2_max_tokens = min(settings.LLM_MAX_TOKENS, LLM_MAX_CONTEXT_TOKENS - actual_input_tokens - safety_tokens)`；
  - 若 `stage2_max_tokens <= 0`，视为预算计算失败并终止任务；
  - 根对象统一折叠到 `suggestions`；
  - 域只允许 5 个 canonical keys；
  - 缺失可选子字段按空值归一化。
- 合并规则：
  - 字典：递归合并；
  - 字符串：`base + "; " + update"`；
  - 列表：稳定追加并去重；
  - `module_structure`：按 `module_name` 聚合，同名模块下的 `functions` 再按 `name + desc` 去重；
  - `integration_points`：按 `peer_system + protocol + direction + description` 去重；
  - `key_constraints`：按 `category + description` 去重；
  - 其他列表：按 canonical JSON 字符串去重。

**写入时机**
- 只有 Stage1 全部成功且 Stage2 全部成功后，才调用 `set_ai_suggestions()`。
- 任一块失败时，仅更新 task 状态和通知，不修改现有 `ai_suggestions`。

#### 5.3.3 正常文档单次调用路径（REQ-003）

| 场景 | 触发 | 期望行为 | 用户提示/错误码 | 是否可重试 | 兜底 |
|---|---|---|---|---|---|
| 正常文档 | `estimated_tokens <= stage_budget` | 只执行 1 次 Stage1 + 1 次 Stage2 | 无新增提示 | 是，沿用现有 LLM 重试 | 无 |

实现要求：
- 不进入 chunk plan，不生成 chunk 指标日志。
- 仍记录整体 `estimated_tokens`、stage latency、actual usage（如可用）。

#### 5.3.4 关闭分块开关与失败映射（REQ-004）

| 场景 | 触发 | 期望行为 | 用户提示/错误码 | 是否可重试 | 兜底 |
|---|---|---|---|---|---|
| 分块关闭且正文超预算 | `ENABLE_LLM_CHUNKING=false` 且 `estimated_tokens > stage_budget` | 快速失败，不切块，不截断 | `PROFILE_IMPORT_FAILED` + `details.reason=文档过长，请开启智能分块功能（ENABLE_LLM_CHUNKING=true）或缩减文档内容` | 否 | 打开开关或缩短文档 |
| 单段超限 | 单个段落 > `stage_budget` | 快速失败 | `PROFILE_IMPORT_FAILED` + `details.reason=文档包含超长段落，无法分块处理` | 否 | 用户拆分段落 |
| 块处理失败 | 任一块重试后仍失败 / 非法 JSON | 整次任务失败，不写入部分结果 | `PROFILE_IMPORT_FAILED` + `details.reason=文档处理失败，请检查文档格式或联系管理员` | 否 | 排查文档或 LLM 状态 |

### 5.4 API 设计（Contracts）

本次不新增 HTTP API，但受影响的对外接口必须显式声明“契约不变、行为内部增强”。

| API-ID | 方法 | 路径 | 请求体结构 | 响应体结构 | 错误码 | 兼容性 | 备注 |
|---|---|---|---|---|---|---|---|
| API-001 | POST | `/api/v1/knowledge/imports` | multipart/form-data：`file`、`knowledge_type`、`level`、`doc_type?`、`system_name?`、`system_id?` | `{code, message, data:{imported, failed, errors[]}}` | `KNOW_001` / `KNOW_002` / `EMB_001` / `AUTH_001` | 向后兼容 | 成功后若绑定系统且 `knowledge_type=document`，异步触发总结任务 |
| API-002 | POST | `/api/v1/system-profiles/{system_id}/profile/import` | multipart/form-data：`file`、`doc_type` | `{import_result:{status,file_name,imported_at,failure_reason}, extraction_task_id?}` | `PROFILE_IMPORT_FAILED` / `AUTH_001` | 向后兼容 | 成功后异步触发总结任务 |
| API-003 | GET | `/api/v1/system-profiles/{system_id}/profile/extraction-status` | 路径参数：`system_id` | `{task_id,status,trigger,error,notifications[]}` | 现有错误包络 | 向后兼容 | 任务失败时承载异步总结失败信息 |

#### API-001：`POST /api/v1/knowledge/imports`

参数/请求体：
- `file`: 必填，支持现有导入扩展名。
- `knowledge_type`: 必填，仅支持 `document` / `code`。
- `level`: 可选，默认 `normal`。
- `doc_type`: 可选，仅 `knowledge_type=document` 时允许。
- `system_name` / `system_id`: 可选，用于绑定系统。

权限：
- 仅 `manager` 可调用，且绑定系统时仍沿用现有 owner/B 角校验。

返回：
- 成功：`200`，结构保持 `{code, message, data}`。
- 异步总结任务不会改变本接口同步返回结构。

错误码：
- `KNOW_001`：文件类型/参数/大小不合法。
- `KNOW_002`：文件解析失败。
- `EMB_001`：embedding 服务不可用。
- `AUTH_001`：绑定目标系统但权限不足。

```typescript
interface KnowledgeImportResponse {
  code: number;
  message: string;
  data: {
    imported: number;
    failed: number;
    errors: string[];
  };
}
```

#### API-002：`POST /api/v1/system-profiles/{system_id}/profile/import`

参数/请求体：
- 路径参数 `system_id`: 必填，目标系统 ID。
- multipart `file`: 必填，导入文件。
- multipart `doc_type`: 必填，现有受支持文档类型。

权限：
- `manager` / `admin` 可调用，且必须满足现有 owner/B 角写权限。

返回：
- 成功：保留 `import_result` 和可选 `extraction_task_id`。
- 新设计只改变后台任务如何消费原文，不增加强制字段。

错误码：
- 顶层仍使用 `PROFILE_IMPORT_FAILED`。
- `details.reason` 内部原因标签落在 `CHUNK_PARAGRAPH_TOO_LONG` / `CHUNKING_DISABLED_OVERSIZE` / `CHUNK_PROCESSING_FAILED` 语义范围，但不改变包络结构。

```typescript
interface ProfileImportSuccessResponse {
  import_result: {
    status: "success";
    file_name: string;
    imported_at: string | null;
    failure_reason: null;
  };
  extraction_task_id?: string;
}

interface ProfileImportErrorResponse {
  error_code: "PROFILE_IMPORT_FAILED" | "AUTH_001";
  message: string;
  request_id: string;
  details?: {
    reason?: string;
  };
}
```

#### API-003：`GET /api/v1/system-profiles/{system_id}/profile/extraction-status`

参数/请求体：
- 路径参数 `system_id`: 必填。

权限：
- 沿用现有 `manager/admin/expert` 查询权限。

返回：
- 保持 `task_id/status/trigger/error/notifications[]` 不变。
- 当异步总结因 chunking 失败时，`error` 字段继续承载失败原因文本。

错误码：
- 沿用现有错误包络，不新增状态码和强制字段。

### 5.5 异步/消息/作业（如适用）
| EVT-ID | Topic/Queue | 生产者 | 消费者 | 投递语义 | 幂等/去重 | DLQ | 备注 |
|---|---|---|---|---|---|---|---|
| EVT-001 | 线程池任务 `profile_summary` | 导入接口 | `ProfileSummaryService._run_job` | at-most-one write on success | 同一任务只在全部成功时写 suggestions | 无 | 沿用现有线程池执行器 |

### 5.6 配置、密钥与开关（Config/Secrets/Flags）
- 新增配置项：

| 配置项 | 默认值 | 取值范围 | 用途 | 兼容性 |
|---|---|---|---|---|
| `LLM_MAX_CONTEXT_TOKENS` | `32000` | `>0` | 模型上下文总预算 | 新增 |
| `LLM_INPUT_MAX_TOKENS` | `25000` | `< LLM_MAX_CONTEXT_TOKENS` | 单次输入正文最大预算 | 新增 |
| `LLM_CHUNK_OVERLAP_PARAGRAPHS` | `2` | `0..2` | 相邻 chunk 的目标重叠段数 | 新增 |
| `ENABLE_LLM_CHUNKING` | `true` | `true/false` | 分块总开关 | 新增 |
| `PROFILE_SUMMARY_CONTEXT_MAX_CHARS` | 保留现值 | `>=12000` | 仅兼容旧采样逻辑，不再作为正文裁剪门禁 | 保留兼容 |

- 密钥管理：
  - `DASHSCOPE_API_KEY` 继续通过 `.env` 注入，不写入文档实际值。
- Feature Flag：
  - `ENABLE_LLM_CHUNKING=true`：默认开启。
  - 回滚时改为 `false`，普通文档仍可运行，超长文档显式失败。

### 5.7 可靠性与可观测性（Reliability/Observability）
| 指标 | 维度 | 阈值 | 告警级别 | 处理指引 |
|---|---|---|---|---|
| `profile_summary_chunk_count` | `system_id, source_file` | > 1 仅记录 | P3 | 观察文档体量分布 |
| `profile_summary_chunk_tokens` | `stage, chunk_index` | `> LLM_INPUT_MAX_TOKENS` 视为缺陷 | P1 | 立即排查 chunk 预算逻辑 |
| `profile_summary_chunk_latency_ms` | `stage, chunk_index` | 仅记录 | P3 | 分析性能瓶颈 |
| `profile_summary_failed_chunk_index` | `stage` | 任意出现 | P1 | 结合 request_id/任务 ID 排查 |
| `profile_summary_token_warning` | `system_id` | 估算/实际误差 > 20% | P2 | 调整 safety margin 或提示风险 |

日志要求：
- 每次任务记录：`estimated_total_tokens`、`chunk_count`、`stage1_chunks`、`stage2_chunks`、`total_elapsed_ms`。
- 每个块记录：`chunk_index`、`estimated_tokens`、`actual_prompt_tokens?`、`actual_total_tokens?`、`latency_ms`、`retry_count`。
- 失败时记录：`stage`、`chunk_index`、`reason_label`，但不记录正文。

### 5.8 安全设计（Security）
| 威胁/攻击面 | 风险 | 缓解措施 | 验证方式 |
|---|---|---|---|
| 超长文档导致资源耗尽 | 线程池长期占用 | 继续受上传大小、LLM timeout、chunking 开关约束 | 单元测试 + 配置检查 |
| 文档正文落盘泄露 | 敏感内容持久化 | 原文仅以内存参数传给后台任务；日志不记录正文 | 代码审查 |
| 越权触发总结 | 非 owner/B 角写入他人系统 | 沿用现有接口权限校验，不新增旁路入口 | API 回归测试 |
| 非法 JSON / prompt 注入 | 解析异常或结构漂移 | 每块都必须 `extract_json` + schema normalize；非法即失败 | 单元测试 |

### 5.9 性能与容量（Performance/Capacity）
- 指标与口径：
  - 普通文档：仍为 1 次 Stage1 + 1 次 Stage2。
  - 超长文档：`chunk_count = ceil((body_tokens - overlap_tokens) / effective_chunk_budget)` 的近似结果。
- 主要瓶颈：
  - LLM 串行调用次数增加。
- 设计取舍：
  - 本版先采用**串行执行**，保证合并和失败定位简单；不在 v2.6 引入并行块调用，避免放大限流/重试复杂度。
- 扩展方案：
  - 如后续需要，可在不改对外契约前提下把 Stage1/Stage2 的 per-chunk 调用改为受控并发。

## 6. 环境与部署（Environments & Deployment）
### 6.0 环境一致性矩阵（推荐）
| 维度 | DEV | STAGING | PROD |
|------|-----|---------|------|
| LLM / Embedding | `.env.backend(.example)` 显式声明 `LLM_MODEL`/`EMBEDDING_MODEL` | 与内网等效配置 | `Qwen3-32B` / `Qwen3-Embedding-8B` |
| Token 配置 | `32000 / 25000 / overlap=2 / chunking=true` | 同 PROD | 同 PROD |
| 配置来源 / 密钥管理 | `.env.backend` / 示例占位 | `.env.backend.internal` / 脱敏 | `.env.backend.internal` / 实际部署值 |

### 6.1 发布、迁移与回滚（Release/Migration/Rollback）
#### 6.1.1 向后兼容策略
- API 兼容：HTTP 路径、返回包络、顶层错误码不变。
- 数据兼容：不改存储结构。
- 配置兼容：新增配置都有默认值；旧 `PROFILE_SUMMARY_CONTEXT_MAX_CHARS` 保留。

#### 6.1.2 上线步骤（Runbook 级别）
1. 更新 `backend/config/config.py` 与 `.env.backend*` 样例文件。
2. 部署代码。
3. 在目标环境核对 `LLM_MODEL`、`EMBEDDING_MODEL`、`LLM_MAX_CONTEXT_TOKENS`、`LLM_INPUT_MAX_TOKENS`、`ENABLE_LLM_CHUNKING`。
4. 运行超长文档回归测试/抽样任务，确认无 Token 超限。

#### 6.1.3 回滚策略（必须可执行）
- 触发条件：
  - 分块逻辑导致总结大量失败，或 latency 明显不可接受。
- 回滚步骤：
  1. 将 `ENABLE_LLM_CHUNKING=false`。
  2. 保持其余代码与 API 契约不变。
  3. 验证普通文档仍可单次调用成功，超长文档返回固定错误提示。
- 数据处理：
  - 无 schema 回滚需求；
  - 未成功写入的任务不会产生部分 suggestions，因此无需数据清理。

## 7. 测试与验收计划（Test Plan）
### 7.1 测试用例清单（建议按 REQ-ID）
| TEST-ID | 对应 REQ-ID | 用例说明 | 类型 | 负责人 | 证据 |
|---|---|---|---|---|---|
| TEST-001 | REQ-001 / REQ-C004 | 30k 文档生成 >=2 个 chunk 且每块不超预算 | unit | AI | `tests/test_token_counter.py` |
| TEST-002 | REQ-001 | 单个超长段落触发固定错误 | unit | AI | `tests/test_token_counter.py` |
| TEST-003 | REQ-002 | Stage1 域/系统列表去重合并 | unit | AI | `tests/test_llm_client.py` |
| TEST-004 | REQ-002 | Stage2 `module_structure` / `integration_points` / `key_constraints` 深度合并 | unit | AI | `tests/test_llm_client.py` |
| TEST-005 | REQ-003 | 20k/25k 文档只走单次调用 | unit | AI | `tests/test_profile_summary_service.py` |
| TEST-006 | REQ-004 / REQ-C001 | chunking 关闭时超长文档显式失败且不截断 | unit | AI | `tests/test_profile_summary_service.py` |
| TEST-007 | REQ-001 / REQ-C001 | 导入接口把完整 `text_content` 透传给总结任务 | unit | AI | `tests/test_system_profile_import_api.py` / `tests/test_knowledge_import_api.py` |
| TEST-008 | REQ-101 / REQ-103 | 25k/30k/50k 样本无 Token 超限并记录 chunk latency | unit | AI | `tests/test_profile_summary_service.py` |
| TEST-009 | REQ-102 | 新增代码覆盖率 > 80% | unit | AI | `pytest --cov` |
| TEST-010 | REQ-C003 | 外部 API 成功/失败包络回归不变 | unit/API | AI | `tests/test_system_profile_import_api.py` / `tests/test_knowledge_import_api.py` |

### 7.2 验收清单（可勾选）
- [ ] 所有 `REQ-xxx` / `REQ-Cxxx` 均有对应验证证据。
- [ ] 关键失败路径已覆盖：单段超限、块失败、关闭分块。
- [ ] 回滚步骤已可执行并具备验证方式。
- [ ] 无新增运行时外部依赖。
- [ ] 日志字段足以定位失败块与 token 预算问题。

## 8. 风险与开放问题
### 8.1 风险清单
| 风险 | 影响 | 概率 | 应对措施 | Owner |
|---|---|---|---|---|
| 启发式 Token 估算偏差过大 | 仍可能超限 | 中 | prompt_overhead + safety reserve + usage warning | 后端 |
| Stage2 深度合并误去重 | 信息丢失或重复 | 中 | 先 canonical normalize，再做字段级合并测试 | 后端 |
| 导入接口未透传原始正文 | 无法满足 REQ-C001 | 低 | API 调用点强制补测 | 后端 |
| 串行分块耗时偏高 | 用户等待异步结果更久 | 中 | 先记录指标，后续再评估受控并发 | 后端 |

### 8.2 开放问题（必须收敛）
- [x] 无待确认项。本次设计不保留“可选/二选一/暂定”口径。

## 10. 变更记录
| 版本 | 日期 | 修改章节 | 说明 | 作者 |
|---|---|---|---|---|
| v0.1 | 2026-03-09 | 初始化 | 完成 v2.6 Design 阶段首版技术设计 | Codex |
