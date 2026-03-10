# v2.6 需求说明书：文档分块处理以适配内网 LLM Token 限制

| 项 | 值 |
|---|---|
| 状态 | Review |
| 作者 | Claude Sonnet 4.5 / Codex |
| 评审 | Codex |
| 日期 | 2026-03-09 |
| 版本 | v0.4 |
| 关联提案 | `docs/v2.6/proposal.md` v1.1 |

## 1. 概述

### 1.1 目的与范围

**目的**：解决内网环境导入超长技术方案文档时的 Token 超限问题，确保任意长度的文档都能成功导入并生成完整的系统画像建议。

**范围**：
- 新增轻量级 Token 计数工具（`backend/utils/token_counter.py`）
- 扩展 LLM 客户端支持分块调用（`backend/utils/llm_client.py`）
- 改进系统画像服务的 Stage1/Stage2 调用逻辑（`backend/service/profile_summary_service.py`）
- 扩展配置项支持 Token 限制和分块开关（`backend/config/config.py`）
- 更新本地和内网环境配置文件（`.env.backend`、`.env.backend.example`、`.env.backend.internal`）
- 新增后端单元测试（`tests/test_token_counter.py`、`tests/test_llm_client.py`、扩展 `tests/test_profile_summary_service.py`）

### 1.2 背景、约束与关键假设

**现状与痛点**：
- 内网模型 `Qwen3-32B` 最大上下文为 32,000 tokens
- 当前系统使用字符级限制（120,000 字符），无 Token 计数
- 超长文档（如 525 段落 + 47 表格）导致 Token 超限失败
- 本地开发环境与内网环境模型不一致，可能导致部署后才发现问题

**约束**：
- **技术约束**：
  - 内网模型固定为 `Qwen3-32B`（32,000 tokens 上下文）
  - 本地/测试环境必须显式配置与内网等效的 LLM/Embedding 模型；样例文件需写明 `LLM_MODEL` 与 `EMBEDDING_MODEL`
  - 不引入外部依赖（tiktoken、transformers 等）
  - API 契约不变，数据格式不变
- **业务约束**：
  - 内容无损失：分块过程中不能丢失任何文档内容
  - 快速交付：总工期 2.5 天
- **运维约束**：
  - 必须支持配置开关关闭智能分块
  - 关闭分块后，普通文档走单次调用，超长文档显式失败并提示开启分块，不允许静默截断
  - 记录分块数、token 数、调用时间，便于问题排查

**关键假设**：
- Token 估算使用保守策略（字符数 / 2.5）可满足 95% 以上场景
- 段落级分块 + 1-2 段重叠可保持语义连贯性
- 深度合并逻辑可正确处理 JSON 结构（列表去重、字典递归合并、字符串拼接）
- 分块调用总耗时在可接受范围内（< 单次调用超时时间 × 分块数）
- LLM 客户端现有重试策略可覆盖瞬时失败；超过重试预算后必须显式失败而不是输出部分结果

### 1.3 术语与口径

**ID 前缀规则**：详见 `.aicoding/STRUCTURE.md` 统一定义。

**核心术语**：
- **Token**：LLM 处理的最小单位，通常 1 个中文字符约 2-3 tokens，1 个英文单词约 1-2 tokens
- **Token 估算**：基于字符数的启发式估算（字符数 / 2.5），用于快速判断是否需要分块
- **分块（Chunking）**：将超长文本按段落边界切分为多个块，每块不超过输入上限
- **重叠（Overlap）**：相邻块之间共享 1-2 个段落，保持语义连贯性
- **深度合并（Deep Merge）**：递归合并多个 JSON 对象，处理列表去重、字典合并、字符串拼接
- **Stage1**：系统画像服务的域识别阶段，输出 `relevant_domains` 和 `related_systems`
- **Stage2**：系统画像服务的建议生成阶段，输出 5 域 12 子字段的 AI 建议

**关键口径**：
- **模型最大上下文**：32,000 tokens（内网 `Qwen3-32B`）
- **单次输入上限**：25,000 tokens（为输出预留 7,000 tokens）
- **Stage1 输出上限**：600 tokens
- **Stage2 输出上限**：动态计算（32,000 - 输入 tokens - 1,000 安全边界）
- **安全边界**：1,000 tokens（用于应对估算误差和模型内部开销）

### 1.4 覆盖性检查（🔴 MUST，R5）

#### 覆盖映射表（🔴 MUST）

| Proposal 锚点 | 类型 | 对应 REQ-ID | 验收标准 | 状态 |
|---------------|------|------------|---------|------|
| P-DO-01: 超长文档 100% 成功导入 | DO | REQ-001 | GWT-REQ-001-01, GWT-REQ-001-02 | ✅已覆盖 |
| P-DO-02: AI 结果完整性 | DO | REQ-002 | GWT-REQ-002-01, GWT-REQ-002-02 | ✅已覆盖 |
| P-DO-03: 正常文档性能不变 | DO | REQ-003 | GWT-REQ-003-01 | ✅已覆盖 |
| P-DO-04: 回滚能力 | DO | REQ-004 | GWT-REQ-004-01, GWT-REQ-004-02 | ✅已覆盖 |
| P-DONT-01: 不允许文档内容丢失 | DONT | REQ-C001 | GWT-REQ-C001-01, GWT-REQ-C001-02 | ✅已覆盖 |
| P-DONT-02: 不允许引入外部依赖 | DONT | REQ-C002 | GWT-REQ-C002-01 | ✅已覆盖 |
| P-DONT-03: 不允许修改 API 契约 | DONT | REQ-C003 | GWT-REQ-C003-01 | ✅已覆盖 |
| P-DONT-04: 不允许生成超限 chunk | DONT | REQ-C004 | GWT-REQ-C004-01 | ✅已覆盖 |
| P-METRIC-01: Token 超限错误率 = 0 | METRIC | REQ-101 | GWT-REQ-101-01 | ✅已覆盖 |
| P-METRIC-02: 单元测试覆盖率 > 80% | METRIC | REQ-102 | GWT-REQ-102-01 | ✅已覆盖 |
| P-METRIC-03: 分块调用总耗时 < 单次调用超时时间 × 分块数 | METRIC | REQ-103 | GWT-REQ-103-01 | ✅已覆盖 |

**覆盖性确认**：
- Proposal 共 11 个锚点（4 个 DO + 4 个 DONT + 3 个 METRIC）
- Requirements 共 11 个需求（4 个功能性 + 4 个禁止项 + 3 个非功能）
- 覆盖率：11/11 = 100%
- 无 defer 项

## 2. 业务场景说明

### 2.1 角色与对象

**角色**：
- **产品经理（manager）**：导入技术方案文档，生成系统画像建议
- **系统管理员（admin）**：在内网环境部署和维护系统
- **系统（后台服务）**：执行文档解析、Token 计数、分块调用、结果合并

**核心对象**：
- **文档（Document）**：用户上传的技术方案文档（DOCX/PDF/TXT）
- **段落（Paragraph）**：文档的基本结构单元，分块的最小边界
- **Token 计数器（TokenCounter）**：估算文本 Token 数的工具
- **LLM 客户端（LLMClient）**：封装模型调用和分块逻辑
- **系统画像服务（ProfileSummaryService）**：处理文档导入和 AI 建议生成
- **配置（Config）**：Token 限制、分块开关等系统配置

### 2.2 场景列表

| 场景分类 | 场景ID | 场景名称 | 场景说明 | 主要角色 |
|---|---|---|---|---|
| CAT-A 文档导入 | SCN-001 | 超长文档导入（触发分块） | 用户导入包含 500+ 段落的超长文档，系统自动分块调用并合并结果 | manager, 系统 |
| CAT-A 文档导入 | SCN-002 | 正常文档导入（不触发分块） | 用户导入普通长度文档（< 25,000 tokens），系统单次调用 | manager, 系统 |
| CAT-B 降级与回滚 | SCN-003 | 关闭分块开关后的降级行为 | 管理员关闭分块开关，普通文档走单次调用，超长文档显式失败并提示 | admin, 系统 |
| CAT-C Token 计数 | SCN-004 | Token 估算与验证 | 系统对输入文本进行 Token 估算，并从 LLM 响应提取实际 Token 数 | 系统 |
| CAT-D 分块与合并 | SCN-005 | 文本分块（保持段落完整性） | 系统按段落边界切分文本，确保每块不超过输入上限，相邻块重叠 1-2 段 | 系统 |
| CAT-D 分块与合并 | SCN-006 | Stage1 结果合并（域和系统列表） | 系统合并多个 Stage1 响应的 `relevant_domains` 和 `related_systems` | 系统 |
| CAT-D 分块与合并 | SCN-007 | Stage2 结果合并（JSON 深度合并） | 系统深度合并多个 Stage2 响应的 5 域 12 子字段 JSON 结构 | 系统 |

### 2.3 场景明细

#### SCN-001：超长文档导入（触发分块）

**场景分类**：CAT-A 文档导入
**主要角色**：manager, 系统
**相关对象**：Document, Paragraph, TokenCounter, LLMClient, ProfileSummaryService
**关联需求ID**：REQ-001, REQ-002

**前置条件**：
- 用户已登录且具有 manager 角色
- 文档内容超过 25,000 tokens（估算值）
- 系统配置 `ENABLE_LLM_CHUNKING=true`

**触发条件**：
- 用户在"知识导入"页面上传技术方案文档并点击"导入"

**流程步骤**：
1. 系统解析文档，提取段落和表格
2. 系统调用 `TokenCounter.estimate_tokens()` 估算总 Token 数
3. 系统判断总 Token 数 > 25,000，决定启用分块
4. 系统调用 `TokenCounter.chunk_text()` 按段落边界切分文本，每块不超过 25,000 tokens，相邻块重叠 1-2 段
5. 系统调用 `LLMClient.chat_with_chunking()` 对每个块执行 Stage1 调用
6. 系统合并所有 Stage1 响应的 `relevant_domains` 和 `related_systems`（集合去重）
7. 系统调用 `LLMClient.chat_with_chunking()` 对每个块执行 Stage2 调用
8. 系统深度合并所有 Stage2 响应的 JSON 结构
9. 系统返回最终的系统画像建议

**输出产物**：
- 系统画像 AI 建议（5 域 12 子字段）
- 日志记录（分块数、每块 Token 数、调用时间）

**异常与边界处理**：
- 若任意块在 LLM 客户端重试后仍失败，系统终止本次总结任务并返回错误提示，不写入部分合并结果
- 若单个段落超过 25,000 tokens，系统返回错误提示"文档包含超长段落，无法分块处理"
- 若分块前检测到已有字符级截断逻辑，必须先移除该截断后再进入 Token 估算与分块流程

#### SCN-002：正常文档导入（不触发分块）

**场景分类**：CAT-A 文档导入
**主要角色**：manager, 系统
**相关对象**：Document, TokenCounter, LLMClient, ProfileSummaryService
**关联需求ID**：REQ-003

**前置条件**：
- 用户已登录且具有 manager 角色
- 文档内容不超过 25,000 tokens（估算值）
- 系统配置 `ENABLE_LLM_CHUNKING=true` 或 `false`

**触发条件**：
- 用户在"知识导入"页面上传技术方案文档并点击"导入"

**流程步骤**：
1. 系统解析文档，提取段落和表格
2. 系统调用 `TokenCounter.estimate_tokens()` 估算总 Token 数
3. 系统判断总 Token 数 ≤ 25,000，决定不启用分块
4. 系统调用 `LLMClient.chat()` 执行单次 Stage1 调用
5. 系统调用 `LLMClient.chat()` 执行单次 Stage2 调用
6. 系统返回系统画像建议

**输出产物**：
- 系统画像 AI 建议（5 域 12 子字段）
- 日志记录（Token 数、调用时间）

**异常与边界处理**：
- 若 LLM 调用失败，系统返回错误提示"文档处理失败，请检查文档格式或联系管理员"

#### SCN-003：关闭分块开关后的降级行为

**场景分类**：CAT-B 降级与回滚
**主要角色**：admin, 系统
**相关对象**：Config, ProfileSummaryService
**关联需求ID**：REQ-004, REQ-C001

**前置条件**：
- 系统配置 `ENABLE_LLM_CHUNKING=false`

**触发条件**：
- 用户在"知识导入"页面上传文档并点击"导入"

**流程步骤**：
1. 系统解析文档，提取段落和表格
2. 系统调用 `TokenCounter.estimate_tokens()` 估算总 Token 数
3. 系统判断 `ENABLE_LLM_CHUNKING=false`
4. 若总 Token 数 ≤ 25,000，系统执行单次调用（同 SCN-002）
5. 若总 Token 数 > 25,000，系统返回错误提示"文档过长，请开启智能分块功能（ENABLE_LLM_CHUNKING=true）或缩减文档内容"

**输出产物**：
- 正常文档：系统画像 AI 建议
- 超长文档：错误提示

**异常与边界处理**：
- 不允许静默截断文档内容
- 错误提示必须明确指出问题原因和解决方案

#### SCN-004：Token 估算与验证

**场景分类**：CAT-C Token 计数
**主要角色**：系统
**相关对象**：TokenCounter
**关联需求ID**：REQ-001, REQ-003

**前置条件**：
- 系统已加载 `TokenCounter` 模块

**触发条件**：
- 系统需要判断是否启用分块
- 系统需要验证 LLM 响应的实际 Token 数

**流程步骤**：
1. **估算 Token 数**：系统调用 `TokenCounter.estimate_tokens(text)` 使用启发式算法（字符数 / 2.5）估算 Token 数
2. **提取实际 Token 数**：系统调用 `TokenCounter.extract_usage_from_response(response)` 从 LLM 响应的 `usage` 字段提取实际 Token 数
3. **记录日志**：系统记录估算值、实际值、误差率

**输出产物**：
- 估算 Token 数（整数）
- 实际 Token 数（整数，如果 LLM 响应包含 `usage` 字段）
- 日志记录

**异常与边界处理**：
- 若 LLM 响应不包含 `usage` 字段，系统使用估算值
- 若估算误差超过 20%，系统记录警告日志

#### SCN-005：文本分块（保持段落完整性）

**场景分类**：CAT-D 分块与合并
**主要角色**：系统
**相关对象**：TokenCounter, Paragraph
**关联需求ID**：REQ-001, REQ-C004

**前置条件**：
- 系统已判断需要启用分块
- 文档已解析为段落列表

**触发条件**：
- 系统调用 `TokenCounter.chunk_text(text, max_tokens, overlap_paragraphs)`

**流程步骤**：
1. 系统按段落边界（`\n\n`）切分文本
2. 系统逐段累加 Token 数，直到接近 `max_tokens`（25,000）
3. 系统创建第一个块，包含累加的段落
4. 系统从下一个段落开始，重复步骤 2-3，创建后续块
5. 系统为相邻块添加重叠段落（1-2 段）：
   - 若加入 2 段重叠后不超限，使用 2 段
   - 若加入 2 段重叠后超限但加入 1 段不超限，使用 1 段
   - 若加入 1 段重叠后仍超限，使用 0 段（无重叠）
6. 系统返回块列表

**输出产物**：
- 块列表（每块为字符串）
- 每块的 Token 数（估算值）

**异常与边界处理**：
- 若单个段落超过 `max_tokens`，系统抛出异常"文档包含超长段落，无法分块处理"
- 若重叠段落导致超限，系统自动缩减重叠数量（2 → 1 → 0）

#### SCN-006：Stage1 结果合并（域和系统列表）

**场景分类**：CAT-D 分块与合并
**主要角色**：系统
**相关对象**：LLMClient, ProfileSummaryService
**关联需求ID**：REQ-002

**前置条件**：
- 系统已完成所有块的 Stage1 调用
- 每个响应包含 `relevant_domains` 和 `related_systems` 字段

**触发条件**：
- 系统调用 `LLMClient._merge_stage1_responses(responses)`

**流程步骤**：
1. 系统初始化空集合 `all_domains` 和 `all_systems`
2. 系统遍历所有响应，提取 `relevant_domains` 和 `related_systems`
3. 系统将提取的域和系统添加到集合（自动去重）
4. 系统返回合并后的结果

**输出产物**：
- 合并后的 `relevant_domains` 列表
- 合并后的 `related_systems` 列表

**异常与边界处理**：
- 若某个响应缺少 `relevant_domains` 或 `related_systems` 等 Stage1 必需字段，系统将该块视为失败并按失败策略处理
- 不允许通过“跳过坏块、保留好块”的方式生成最终结果

#### SCN-007：Stage2 结果合并（JSON 深度合并）

**场景分类**：CAT-D 分块与合并
**主要角色**：系统
**相关对象**：LLMClient, ProfileSummaryService
**关联需求ID**：REQ-002

**前置条件**：
- 系统已完成所有块的 Stage2 调用
- 每个响应包含 5 域 12 子字段的 JSON 结构

**触发条件**：
- 系统调用 `LLMClient._deep_merge(base, update)`

**流程步骤**：
1. 系统遍历 `update` 的所有键值对
2. 对于每个键：
   - 若值为列表：追加到 `base` 的对应列表，并按字段契约去重（如 `module_structure` 按 `module_name` 去重）
   - 若值为字典：递归调用 `_deep_merge(base[key], update[key])`
   - 若值为字符串：
     - 若 `base[key]` 为空，使用 `update[key]`
     - 若 `base[key]` 非空且 `update[key]` 非空，拼接为 `base[key] + "; " + update[key]`
     - 若 `update[key]` 为空，保持 `base[key]` 不变
3. 系统返回合并后的 `base`

**输出产物**：
- 合并后的 JSON 对象（5 域 12 子字段）

**异常与边界处理**：
- 若某个响应根结构非法（非 JSON 对象或缺少 `suggestions` / 等价根对象），系统将该块视为失败并按失败策略处理
- 若合法响应仅缺少某个可选子字段，系统按空值归一化，但不允许静默丢弃整个响应

## 3. 功能性需求（Functional Requirements）

> **优先级说明**：M=Must / S=Should / C=Could / W=Won't。

### 3.1 功能性需求列表

| 需求分类 | REQ-ID | 需求名称 | 优先级 | 需求说明 | 关联场景ID |
|---|---|---|---|---|---|
| CAT-A 文档导入 | REQ-001 | 超长文档分块处理 | M | 系统对超过 25,000 tokens 的文档自动分块调用并合并结果 | SCN-001 |
| CAT-A 文档导入 | REQ-002 | 分块结果深度合并 | M | 系统深度合并多个块的 Stage1/Stage2 响应，确保结果完整性 | SCN-001, SCN-006, SCN-007 |
| CAT-A 文档导入 | REQ-003 | 正常文档单次调用 | M | 系统对不超过 25,000 tokens 的文档执行单次调用，性能不变 | SCN-002 |
| CAT-B 降级与回滚 | REQ-004 | 分块开关降级逻辑 | M | 系统支持关闭分块开关，普通文档走单次调用，超长文档显式失败 | SCN-003 |

### 3.2 功能性需求明细

#### REQ-001：超长文档分块处理 [Unit Only]

**测试等级**：Unit Only

**目标/价值**：解决内网环境超长文档导入失败问题，确保任意长度文档都能成功处理。

**入口/触发**：用户在"知识导入"页面上传技术方案文档并点击"导入"。

**前置条件**：
- 用户已登录且具有 manager 角色
- 文档内容超过 25,000 tokens（估算值）
- 系统配置 `ENABLE_LLM_CHUNKING=true`

**主流程**：
1. 系统解析文档，提取段落和表格
2. 系统调用 `TokenCounter.estimate_tokens()` 估算总 Token 数
3. 系统判断总 Token 数 > 25,000，决定启用分块
4. 系统调用 `TokenCounter.chunk_text()` 按段落边界切分文本：
   - 每块不超过 25,000 tokens
   - 相邻块重叠 1-2 段（若不超限）
   - 若重叠导致超限，自动缩减为 1 段或 0 段
5. 系统对每个块执行 Stage1 和 Stage2 调用，并沿用 LLM 客户端既有重试策略
6. 仅当所有块都成功返回合法结果时，系统才合并所有块的响应结果
7. 系统返回最终的系统画像建议

**输入/输出**：
- 输入：文档内容（字符串）、系统名称
- 输出：系统画像 AI 建议（5 域 12 子字段）、日志记录（分块数、每块 Token 数、调用时间）

**业务规则**：
- 分块阈值：25,000 tokens（为输出预留 7,000 tokens）
- 重叠策略：优先 2 段，若超限则 1 段，若仍超限则 0 段
- 段落边界：按 `\n\n` 切分
- 合并策略：Stage1 集合去重，Stage2 深度合并
- 禁止先按字符数截断上下文再做 Token 估算或分块
- 任一块最终失败时，本次任务必须显式失败，不允许返回部分合并结果

**异常与边界**：
- 若单个段落超过 25,000 tokens，系统返回错误"文档包含超长段落，无法分块处理"
- 若任一块在重试后仍失败，系统返回错误"文档处理失败，请检查文档格式或联系管理员"，且不写入部分建议

**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-001-01: Given 文档内容为 30,000 tokens（估算值）且 `ENABLE_LLM_CHUNKING=true`，When 系统处理文档，Then 系统生成至少 2 个块，每块不超过 25,000 tokens，且返回完整的系统画像建议
- [ ] GWT-REQ-001-02: Given 文档包含 525 段落 + 47 表格（约 30,000 tokens），When 系统处理文档，Then 系统不抛出 Token 超限错误，且返回系统画像建议
- [ ] GWT-REQ-001-03: Given 文档包含单个超长段落（> 25,000 tokens），When 系统处理文档，Then 系统返回错误"文档包含超长段落，无法分块处理"
- [ ] GWT-REQ-001-04: Given 文档被分为 3 个块，When 第 2 个块在 LLM 客户端重试后仍失败，Then 系统返回错误"文档处理失败，请检查文档格式或联系管理员"，且不写入部分合并结果，并记录失败块索引

**关联**：SCN-001

#### REQ-002：分块结果深度合并 [Unit Only]

**测试等级**：Unit Only

**目标/价值**：确保分块调用后的结果完整性，避免信息丢失或重复。

**入口/触发**：系统完成所有块的 Stage1/Stage2 调用后，自动触发合并逻辑。

**前置条件**：
- 系统已完成至少 2 个块的 LLM 调用
- 每个响应包含有效的 JSON 结构

**主流程**：
1. **Stage1 合并**：
   - 系统提取所有响应的 `relevant_domains` 和 `related_systems`
   - 系统使用集合去重，合并为单一列表
2. **Stage2 合并**：
   - 系统初始化空的 JSON 对象作为 `base`
   - 系统遍历所有响应，依次调用 `_deep_merge(base, response)`
   - 对于列表字段：追加并按特定字段去重（如 `module_structure` 按 `module_name` 去重）
   - 对于字典字段：递归合并
   - 对于字符串字段：拼接（用 `"; "` 分隔）
3. 系统返回合并后的结果

**输入/输出**：
- 输入：多个 LLM 响应（JSON 对象列表）
- 输出：合并后的单一 JSON 对象

**业务规则**：
- Stage1 合并：集合去重（保持顺序）
- Stage2 合并：
  - 列表字段：追加 + 去重（`module_structure` 按 `module_name`；`integration_points` 按 `peer_system+protocol+direction+description`；`key_constraints` 按 `category+description`）
  - 字典字段：递归合并
  - 字符串字段：非空拼接（`base + "; " + update`）
- 对合法响应缺失的可选子字段按空值归一化，不允许静默丢弃整个响应

**异常与边界**：
- 若所有响应都缺少某个必需字段，系统在最终结果中保留该字段为空值
- 若某个响应根结构非法，系统将该块视为失败并按 REQ-001 的失败策略处理

**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-002-01: Given 2 个 Stage1 响应分别包含 `relevant_domains: ["D1", "D2"]` 和 `["D2", "D3"]`，When 系统合并，Then 最终结果为 `["D1", "D2", "D3"]`（去重）
- [ ] GWT-REQ-002-02: Given 2 个 Stage2 响应的 `module_structure` 分别包含 `[{"module_name": "M1"}]` 和 `[{"module_name": "M1"}, {"module_name": "M2"}]`，When 系统合并，Then 最终结果为 `[{"module_name": "M1"}, {"module_name": "M2"}]`（按 `module_name` 去重）
- [ ] GWT-REQ-002-03: Given 2 个 Stage2 响应的 `system_description` 分别为 `"范围A"` 和 `"范围B"`，When 系统合并，Then 最终结果为 `"范围A; 范围B"`
- [ ] GWT-REQ-002-04: Given 第 1 个合法 Stage2 响应缺少 `integration_points` 子字段，第 2 个响应包含 `integration_points`，When 系统合并，Then 系统将缺失子字段按空值处理，并保留第 2 个响应的 `integration_points`

**关联**：SCN-001, SCN-006, SCN-007

#### REQ-003：正常文档单次调用 [Unit Only]

**测试等级**：Unit Only

**目标/价值**：确保正常长度文档的处理性能不受分块逻辑影响。

**入口/触发**：用户在"知识导入"页面上传技术方案文档并点击"导入"。

**前置条件**：
- 用户已登录且具有 manager 角色
- 文档内容不超过 25,000 tokens（估算值）

**主流程**：
1. 系统解析文档，提取段落和表格
2. 系统调用 `TokenCounter.estimate_tokens()` 估算总 Token 数
3. 系统判断总 Token 数 ≤ 25,000，决定不启用分块
4. 系统调用 `LLMClient.chat()` 执行单次 Stage1 调用
5. 系统调用 `LLMClient.chat()` 执行单次 Stage2 调用
6. 系统返回系统画像建议

**输入/输出**：
- 输入：文档内容（字符串）、系统名称
- 输出：系统画像 AI 建议（5 域 12 子字段）、日志记录（Token 数、调用时间）

**业务规则**：
- 不触发分块的阈值：≤ 25,000 tokens
- 单次调用路径仍只执行 1 次 Stage1 + 1 次 Stage2
- 正常文档性能验收由 REQ-103 提供计时口径，本需求只验证“不进入分块路径”

**异常与边界**：
- 若 LLM 调用失败，系统返回错误"文档处理失败，请检查文档格式或联系管理员"

**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-003-01: Given 文档内容为 20,000 tokens（估算值），When 系统处理文档，Then 系统执行 1 次 Stage1 调用和 1 次 Stage2 调用，且不进入分块逻辑
- [ ] GWT-REQ-003-02: Given 文档内容为 25,000 tokens（估算值，边界值），When 系统处理文档，Then 系统执行单次调用（不分块）

**关联**：SCN-002

#### REQ-004：分块开关降级逻辑 [Unit Only]

**测试等级**：Unit Only

**目标/价值**：提供配置开关支持降级到“单次调用 + 超长文档显式失败”模式，确保系统可控且不丢内容。

**入口/触发**：用户在"知识导入"页面上传文档并点击"导入"。

**前置条件**：
- 系统配置 `ENABLE_LLM_CHUNKING=false`

**主流程**：
1. 系统解析文档，提取段落和表格
2. 系统调用 `TokenCounter.estimate_tokens()` 估算总 Token 数
3. 系统判断 `ENABLE_LLM_CHUNKING=false`
4. **分支 A（正常文档）**：若总 Token 数 ≤ 25,000，系统执行单次调用（同 REQ-003）
5. **分支 B（超长文档）**：若总 Token 数 > 25,000，系统返回错误"文档过长，请开启智能分块功能（ENABLE_LLM_CHUNKING=true）或缩减文档内容"

**输入/输出**：
- 输入：文档内容（字符串）、系统名称
- 输出：
  - 正常文档：系统画像 AI 建议
  - 超长文档：错误提示

**业务规则**：
- 关闭分块开关后，不允许静默截断文档内容
- 错误提示必须明确指出问题原因和解决方案

**异常与边界**：
- 不允许在关闭分块开关后对超长文档进行字符截断

**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-004-01: Given `ENABLE_LLM_CHUNKING=false` 且文档内容为 20,000 tokens，When 系统处理文档，Then 系统执行单次调用并返回系统画像建议
- [ ] GWT-REQ-004-02: Given `ENABLE_LLM_CHUNKING=false` 且文档内容为 30,000 tokens，When 系统处理文档，Then 系统返回错误"文档过长，请开启智能分块功能（ENABLE_LLM_CHUNKING=true）或缩减文档内容"，且不截断文档内容

**关联**：SCN-003

## 4. 非功能需求

### 4.1 非功能需求列表

| 需求分类 | REQ-ID | 需求名称 | 优先级 | 需求说明 | 验收/指标 |
|---|---|---|---|---|---|
| 性能 | REQ-101 | Token 超限错误率 | M | 测试阶段所有超长文档导入成功，Token 超限错误率为 0 | 测试日志 |
| 质量 | REQ-102 | 单元测试覆盖率 | M | 新增代码的单元测试覆盖率 > 80% | pytest-cov 报告 |
| 性能 | REQ-103 | 分块调用总耗时 | M | 分块调用总耗时 < 单次调用超时时间 × 分块数 | 性能日志 |

### 4.2 非功能需求明细

#### REQ-101：Token 超限错误率

**需求分类**：性能

**适用范围**：全局（所有文档导入场景）

**指标与口径**：
- **指标定义**：Token 超限错误率 = Token 超限失败次数 / 总导入次数 × 100%
- **目标值**：0%（测试阶段）
- **统计窗口**：测试阶段（所有测试用例）
- **数据源**：测试日志、系统日志

**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-101-01: Given 测试集覆盖 25,000 / 30,000 / 50,000 tokens 三档超长夹具，并包含 1 个 525 段落 + 47 表格量级样本，When 系统处理所有样本，Then 0 次 Token 超限错误

**验收方法/证据**：
- 后端单元测试：`tests/test_profile_summary_service.py` 包含超长文档测试用例
- 测试日志：记录每次导入的 Token 数和调用结果

**异常与边界**：
- 若出现 Token 超限错误，系统记录详细日志（文档长度、分块数、每块 Token 数、失败块索引）

**关联**：SCN-001, SCN-004

#### REQ-102：单元测试覆盖率

**需求分类**：质量

**适用范围**：新增代码（`backend/utils/token_counter.py`、`backend/utils/llm_client.py`、`backend/service/profile_summary_service.py` 的分块相关代码）

**指标与口径**：
- **指标定义**：单元测试覆盖率 = 被测试覆盖的代码行数 / 总代码行数 × 100%
- **目标值**：> 80%
- **统计窗口**：v2.6 新增代码
- **数据源**：pytest-cov 报告

**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-102-01: Given 运行 `pytest --cov=backend/utils/token_counter --cov=backend/utils/llm_client --cov=backend/service/profile_summary_service`，When 生成覆盖率报告，Then 覆盖率 > 80%

**验收方法/证据**：
- 运行命令：`pytest --cov=backend --cov-report=html`
- 查看报告：`htmlcov/index.html`
- `pytest-cov` 仅用于测试阶段统计，不属于 REQ-C002 约束的运行时依赖

**异常与边界**：
- 若覆盖率 < 80%，需补充测试用例

**关联**：所有功能性需求

#### REQ-103：分块调用总耗时

**需求分类**：性能

**适用范围**：超长文档导入场景（触发分块）

**指标与口径**：
- **指标定义**：分块调用总耗时 = 所有块调用时间之和
- **目标值**：< 单次调用超时时间（60 秒）× 分块数
- **统计窗口**：测试阶段
- **数据源**：性能日志

**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-103-01: Given 文档被分为 3 个块，When 系统处理文档，Then 总耗时 < 180 秒（60 × 3）

**验收方法/证据**：
- 性能日志：记录每个块的调用时间和总耗时
- 对比基线：单次调用超时时间为 60 秒

**异常与边界**：
- 若总耗时超过阈值，系统记录警告日志；若同时伴随块失败，失败块的实际耗时仍需计入统计

**关联**：SCN-001

## 4A. 约束与禁止项（Constraints & Prohibitions）

### 4A.1 禁止项列表

| REQ-ID | 禁止项名称 | 适用范围 | 来源 | 关联GWT-ID |
|--------|-----------|---------|------|-----------|
| REQ-C001 | 禁止文档内容丢失 | 全局（所有文档导入场景） | proposal §P-DONT-01 | GWT-REQ-C001-01, GWT-REQ-C001-02 |
| REQ-C002 | 禁止引入外部依赖 | 全局（所有模块） | proposal §P-DONT-02 | GWT-REQ-C002-01 |
| REQ-C003 | 禁止修改 API 契约 | 全局（系统画像 API） | proposal §P-DONT-03 | GWT-REQ-C003-01 |
| REQ-C004 | 禁止生成超限 chunk | 全局（分块逻辑） | proposal §P-DONT-04 | GWT-REQ-C004-01 |

### 4A.2 禁止项明细

#### REQ-C001：禁止文档内容丢失

**适用范围**：全局（所有文档导入场景，包括分块和降级路径）

**来源**：proposal §P-DONT-01

**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-C001-01: Given 文档段落按顺序标记为 P1..Pn，When 系统分块后去除重叠段落并按原顺序重建文本，Then 重建后的段落序列与原文完全一致（无缺失、无重排、无静默截断）
- [ ] GWT-REQ-C001-02: Given `ENABLE_LLM_CHUNKING=false` 且文档超过 25,000 tokens，When 系统处理文档，Then 系统返回错误提示，不截断文档内容

#### REQ-C002：禁止引入外部依赖

**适用范围**：全局（所有模块）

**来源**：proposal §P-DONT-02

**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-C002-01: Given 检查 `requirements.txt` 和 `pyproject.toml`，When 对比 v2.5 和 v2.6，Then 无新增外部依赖（tiktoken、transformers 等）

#### REQ-C003：禁止修改 API 契约

**适用范围**：全局（系统画像 API）

**来源**：proposal §P-DONT-03

**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-C003-01: Given 系统画像导入接口的成功/失败响应契约，When 对比 v2.5 和 v2.6，Then 成功载荷结构、顶层 `error_code`（如 `PROFILE_IMPORT_FAILED`）和错误包络保持一致，不新增强制字段

#### REQ-C004：禁止生成超限 chunk

**适用范围**：全局（分块逻辑）

**来源**：proposal §P-DONT-04

**验收标准（GWT，必须可判定）**：
- [ ] GWT-REQ-C004-01: Given 系统对文档进行分块，When 检查所有块的 Token 数（估算值），Then 所有块的 Token 数 ≤ 25,000

## 5. 权限与合规

### 5.1 权限矩阵

| 角色 | 操作/权限 | 资源范围 | 备注 |
|---|---|---|---|
| manager / admin | 触发系统画像文档导入 | 自己负责或被授权的系统 | 沿用现有导入 API 权限，不新增角色 |
| manager / admin / expert | 查询导入历史与抽取状态 | 已授权系统 | 仅查询，不新增写权限 |
| 运维管理员（部署者） | 修改分块相关环境变量 | 部署环境配置文件 | 仅部署配置（如 `.env.backend`、`.env.backend.internal`），不新增产品内 API/UI |

### 5.2 客户信息与合规

**本次变更不新增客户信息字段与对外展示范围。**

- 原始上传文件的处理链路沿用现有导入流程；解析后的文本片段仍会写入现有知识库/向量存储，本次变更不新增第二份持久化副本
- 系统画像建议：与 v2.5 保持一致，无新增字段
- 本次新增日志仅记录 Token 数、分块数、调用时间、失败块索引等技术指标，不记录文档正文

## 6. 数据与接口

### 6.1 数据字典

| 字段/对象 | 类型 | 必填 | 来源/去向 | 脱敏 | 留存期 | 备注 |
|---|---|---|---|---|---|---|
| document_text | string | 是 | 文档解析结果 → 分块/LLM 处理 | 否 | 处理态 / 现有知识库留存策略 | 原始上传内容解析后的文本视图 |
| estimated_tokens | int | 是 | TokenCounter 估算 | 否 | 日志 | 估算的 Token 数 |
| actual_tokens | int | 否 | LLM 响应 | 否 | 日志 | 实际的 Token 数（如果可用） |
| chunk_count | int | 是 | 分块逻辑 | 否 | 日志 | 分块数量 |
| chunk_tokens | list[int] | 是 | 分块逻辑 | 否 | 日志 | 每个块的 Token 数 |
| ai_suggestions | dict | 是 | LLM 响应 → 系统画像存储 | 否 | 永久 | 系统画像 AI 建议（5 域 12 子字段） |

### 6.2 错误码与提示语

> 保持现有 API 顶层错误契约；如下“内部原因标签”用于 `details.reason`/日志分类，不新增对外必填字段。

| 顶层 error_code | 内部原因标签 | 场景 | 提示语 | HTTP状态码 | 处理建议 |
|---|---|---|---|---|---|
| PROFILE_IMPORT_FAILED | CHUNK_PARAGRAPH_TOO_LONG | 单个段落超过 Token 上限 | 文档包含超长段落，无法分块处理 | 400 | 缩减段落长度或拆分为多个段落 |
| PROFILE_IMPORT_FAILED | CHUNKING_DISABLED_OVERSIZE | 关闭分块开关后超长文档 | 文档过长，请开启智能分块功能（ENABLE_LLM_CHUNKING=true）或缩减文档内容 | 400 | 开启分块开关或缩减文档 |
| PROFILE_IMPORT_FAILED | CHUNK_PROCESSING_FAILED | 任意块在重试后仍失败 | 文档处理失败，请检查文档格式或联系管理员 | 400 | 检查文档格式、LLM 服务状态 |

**内部告警约定**：
- `TOKEN_ESTIMATE_WARNING` 仅用于日志/监控标签，不进入对外 API `error_code` 字段

### 6.3 指标与计算口径

**Token 超限错误率**：
- 公式：Token 超限错误率 = Token 超限失败次数 / 总导入次数 × 100%
- 统计周期：测试阶段（所有测试用例）
- 取数范围：所有触发 LLM 调用的文档导入场景；其中超长文档样本必须单独统计
- 异常值处理：若 LLM 服务不可用导致失败，不计入 Token 超限错误
- 精度与舍入规则：保留 2 位小数

**单元测试覆盖率**：
- 公式：单元测试覆盖率 = 被测试覆盖的代码行数 / 总代码行数 × 100%
- 统计周期：v2.6 新增代码
- 取数范围：`backend/utils/token_counter.py`、`backend/utils/llm_client.py`、`backend/service/profile_summary_service.py` 的分块相关代码
- 异常值处理：不包含注释、空行、导入语句
- 精度与舍入规则：保留 2 位小数

**分块调用总耗时**：
- 公式：分块调用总耗时 = 所有块调用时间之和
- 统计周期：测试阶段
- 取数范围：超长文档导入场景（触发分块）
- 异常值处理：若某个块调用失败，仍记录该块已发生的实际耗时，并额外标记失败原因
- 精度与舍入规则：保留 2 位小数（秒）

### 6.4 接口清单

> 本次变更保持现有 API 契约不变（REQ-C003），以下接口定义用于追溯与测试覆盖。

#### API-001：系统画像导入接口

**接口标识**：API-001
**路径**：`POST /api/v1/system-profiles/{system_id}/profile/import`
**功能**：上传技术方案文档，触发系统画像 AI 建议生成
**关联需求**：REQ-001, REQ-003, REQ-004, REQ-C001, REQ-C003
**关联场景**：SCN-001, SCN-002, SCN-003

**请求参数**：
- `system_id`（路径参数，必填）：系统 ID
- `file`（表单文件，必填）：技术方案文档（DOCX/PDF/TXT）

**响应包络**（成功）：
```json
{
  "status": "success",
  "data": {
    "task_id": "string",
    "message": "文档导入成功，正在处理"
  }
}
```

**响应包络**（失败）：
```json
{
  "status": "error",
  "error_code": "PROFILE_IMPORT_FAILED",
  "message": "错误提示语",
  "details": {
    "reason": "CHUNK_PARAGRAPH_TOO_LONG | CHUNKING_DISABLED_OVERSIZE | CHUNK_PROCESSING_FAILED"
  }
}
```

**权限**：manager / admin，且对目标系统有权限
**变更说明**：本次变更仅在内部透传完整 `text_content` 给总结服务，对外契约不变

#### API-002：知识导入接口

**接口标识**：API-002
**路径**：`POST /api/v1/knowledge/imports`
**功能**：上传技术方案文档到知识库，并触发绑定系统的画像总结
**关联需求**：REQ-001, REQ-003, REQ-004, REQ-C001, REQ-C003
**关联场景**：SCN-001, SCN-002, SCN-003

**请求参数**：
- `file`（表单文件，必填）：技术方案文档
- `system_id`（表单字段，可选）：绑定的系统 ID

**响应包络**（成功）：
```json
{
  "status": "success",
  "data": {
    "import_id": "string",
    "message": "知识导入成功"
  }
}
```

**响应包络**（失败）：同 API-001

**权限**：manager / admin
**变更说明**：本次变更仅在内部透传完整 `text_content` 给总结服务，对外契约不变

#### API-003：系统画像抽取状态查询接口

**接口标识**：API-003
**路径**：`GET /api/v1/system-profiles/{system_id}/profile/extraction-status`
**功能**：查询系统画像 AI 建议生成任务的状态
**关联需求**：REQ-C003
**关联场景**：SCN-001, SCN-002, SCN-003

**请求参数**：
- `system_id`（路径参数，必填）：系统 ID

**响应包络**（成功）：
```json
{
  "status": "success",
  "data": {
    "task_status": "pending | processing | completed | failed",
    "ai_suggestions": { /* 5 域 12 子字段，仅 completed 时返回 */ }
  }
}
```

**权限**：manager / admin / expert，且对目标系统有权限
**变更说明**：本次变更不影响此接口

### 6.5 测试用例清单

> 本次变更测试等级为 Unit Only，以下测试用例编号用于追溯与覆盖验证。

#### TEST-001：Token 估算基本功能

**测试标识**：TEST-001
**测试文件**：`tests/test_token_counter.py::test_estimate_tokens_basic`
**关联需求**：REQ-001, REQ-003
**关联场景**：SCN-004
**测试目标**：验证 `estimate_tokens()` 对不同长度文本的估算结果

#### TEST-002：文本分块与重叠

**测试标识**：TEST-002
**测试文件**：`tests/test_token_counter.py::test_chunk_text_with_overlap`
**关联需求**：REQ-001, REQ-C001, REQ-C004
**关联场景**：SCN-005
**测试目标**：验证 `chunk_text()` 按段落边界切分、重叠收缩与重建顺序

#### TEST-003：LLM 客户端 usage 提取

**测试标识**：TEST-003
**测试文件**：`tests/test_llm_client.py::test_extract_usage_from_response`
**关联需求**：REQ-002, REQ-101
**关联场景**：SCN-004
**测试目标**：验证从 LLM 响应中提取 `usage` 字段

#### TEST-004：Stage1/Stage2 结果合并

**测试标识**：TEST-004
**测试文件**：`tests/test_llm_client.py::test_merge_stage1_stage2_responses`
**关联需求**：REQ-002, REQ-C001
**关联场景**：SCN-006, SCN-007
**测试目标**：验证 Stage1 列表去重与 Stage2 深度合并逻辑

#### TEST-005：正常文档单次调用路径

**测试标识**：TEST-005
**测试文件**：`tests/test_profile_summary_service.py::test_single_call_path`
**关联需求**：REQ-003
**关联场景**：SCN-002
**测试目标**：验证 20k/25k 文档走单次调用，不触发分块

#### TEST-006：超长文档分块路径

**测试标识**：TEST-006
**测试文件**：`tests/test_profile_summary_service.py::test_chunking_path`
**关联需求**：REQ-001, REQ-002, REQ-101, REQ-103
**关联场景**：SCN-001
**测试目标**：验证 30k/50k 文档触发分块，无 Token 超限错误

#### TEST-007：导入接口原文透传

**测试标识**：TEST-007
**测试文件**：`tests/test_system_profile_import_api.py::test_full_text_passthrough`
**关联需求**：REQ-001, REQ-C001, REQ-C003
**关联场景**：SCN-001, SCN-002
**测试目标**：验证导入接口把完整 `text_content` 透传给总结服务

#### TEST-008：关闭分块开关的降级行为

**测试标识**：TEST-008
**测试文件**：`tests/test_profile_summary_service.py::test_chunking_disabled`
**关联需求**：REQ-004, REQ-C001
**关联场景**：SCN-003
**测试目标**：验证 `ENABLE_LLM_CHUNKING=false` 时普通文档可处理，超长文档显式失败

#### TEST-009：单段超限错误

**测试标识**：TEST-009
**测试文件**：`tests/test_token_counter.py::test_single_paragraph_too_long`
**关联需求**：REQ-C004
**关联场景**：SCN-005
**测试目标**：验证单个段落超过 25,000 tokens 时返回固定错误

#### TEST-010：API 契约回归

**测试标识**：TEST-010
**测试文件**：`tests/test_system_profile_import_api.py::test_api_contract_regression`
**关联需求**：REQ-C003
**关联场景**：SCN-001, SCN-002, SCN-003
**测试目标**：验证导入接口成功/失败包络、错误码与权限不回归

## 7. 变更记录

| 版本 | 日期 | 说明 | 作者 |
|---|---|---|---|
| v0.1 | 2026-03-09 | 初始化，基于 proposal v1.1 编写 | Claude Sonnet 4.6 |
| v0.2 | 2026-03-09 | 修正测试等级、失败语义、API/权限/持久化边界、字段契约与环境文件路径 | Codex |
| v0.3 | 2026-03-09 | 补充 6.4 接口清单（API-001~003）与 6.5 测试用例清单（TEST-001~010），修复 plan.md 追溯断链问题 | Codex |

