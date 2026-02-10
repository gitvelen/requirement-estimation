# 需求评估系统升级工程 - 技术设计文档（V4）

## 文档信息

| 项目 | 内容 |
|---|---|
| 文档版本 | v4.0 |
| 编写日期 | 2026-02-01 |
| 基于需求 | `req_enhance_v4.md` v4.0 |
| 设计目标 | 可直接进入研发拆分与联调 |

---

## 0. 设计目标与约束

### 0.1 目标

1. **采购严肃模式**：输出可审计、可追溯、可解释，默认防止范围扩张。
2. **优先提升准确性**：系统识别准确性、功能拆分合理性优先于“自动给人天”。
3. **LLM 主导 + 证据约束**：LLM 负责判断与生成，证据/事实层负责“约束、阻断、回放”。
4. **小步可落地**：本期先跑通 Java/Spring Boot 代码扫描；PDF 不做 OCR；专家仅在线预览不下载。

### 0.2 关键口径（与需求对齐）

- **ESB 明细表**：交易/场景/提供方/调用方/状态；默认仅“正常使用”参与检索/注入/统计，`include_deprecated=false`。
- **ESB 检索范围**：默认 `scope=both`（提供方+调用方），可切换为仅提供方/仅调用方。
- **证据等级规则配置**：`admin` 配规则（带变更日志）；`manager` 可对**任务内单系统**结果修正（必须备注、留痕、仅影响当前任务）。
- **无代码+无材料兜底**：允许依赖“最小画像”升至 E2 进入 `selected`，但必须显著高风险提示并在报告留标识。
- **证据预览**：仅在线预览，不提供下载；优先原文件渲染，失败则降级为抽取文本预览并提示“版式可能不一致”。

---

## 1. 总体架构与数据流

### 1.1 组件划分

```
Frontend(React)
  ├─ 任务管理/评估页（系统识别、拆分、估算、专家修正、报告）
  └─ 知识与索引（证据库A、画像B、能力目录C、ESB索引I、规则配置）

Backend(FastAPI)
  ├─ 文档解析（DOCX/PPTX/PDF/XLSX/CSV）
  ├─ Embedding（DashScope）
  ├─ 向量检索（LocalVectorStore / 可选 Milvus）
  ├─ 代码扫描（Spring Boot）
  ├─ 规则引擎（证据等级、阻断、阈值）
  ├─ Agent编排（系统识别/拆分/估算）
  └─ 审计与留痕（修正备注、变更日志、任务内覆盖）

Storage（本期以文件为主，便于快速落地）
  ├─ data/task_storage.json（任务数据，已存在）
  ├─ data/knowledge_store.json（向量库落盘，已存在/可选Milvus）
  ├─ data/evidence_docs.json（证据文档元数据）
  ├─ data/esb_index.json（ESB明细索引+可选系统统计表）
  ├─ data/code_scan_jobs.json（扫描作业与结果索引）
  ├─ data/evidence_level_rules.json（证据等级规则配置）
  └─ data/audit_logs.json（操作留痕：修改/覆盖/强行确认等）
uploads/
  └─ evidence/（证据原文件存储）
```

### 1.2 关键链路（任务内）

```
需求文本
  ↓（A/B/C/I检索召回 + 规则约束）
系统识别（LLM输出 → 规则二次校验/阻断 → selected/maybe/questions）
  ↓（按selected系统）
功能拆分（模板化 + 标签 + 证据引用 + 归属复核提示）
  ↓
区间估算（置信度 + 假设 + 风控提示 + 强制规则）
  ↓
专家修正（形成基准）→ 指标统计（以专家最终为基准）
```

---

## 2. 数据模型（本期文件存储）

> 注：需求阶段不要求“主键设计”，但技术设计必须给出稳定引用方式。本期建议使用 `id`（UUID）作为内部唯一键，`system_id/system_name`作为业务字段；未来落库可平滑迁移。

### 2.1 证据库（A层）

**A1 证据文档元数据：`data/evidence_docs.json`**

```json
{
  "doc_id": "evd_...",
  "system_id": "SOFP",
  "system_name": "智慧线上贷款系统",
  "filename": "xxx.pdf",
  "stored_path": "uploads/evidence/SOFP/evd_.../xxx.pdf",
  "doc_type": "pdf|docx|pptx",
  "trust_level": "高|中|低",
  "doc_date": "2025-12-31",
  "source_org": "xx中心",
  "version_hint": "v1.2",
  "parse_meta": {
    "page_count": 12,
    "slide_count": 0
  },
  "created_by": "user_id",
  "created_at": "2026-02-01T10:00:00"
}
```

**A2 证据块向量：存入 `data/knowledge_store.json`（knowledge_type=`evidence_chunk`）**

- `content`：chunk_text
- `system_name`：建议填 `system_name`（便于按系统过滤）
- `metadata`：至少包含：

```json
{
  "doc_id": "evd_...",
  "chunk_id": "chk_...",
  "system_id": "SOFP",
  "doc_type": "pdf",
  "page": 3,
  "loc": "p3#para12",
  "trust_level": "高",
  "doc_date": "2025-12-31"
}
```

### 2.2 系统画像（B层）

**画像存储：`data/system_profiles.json`（新增）**

```json
{
  "system_id": "SOFP",
  "system_name": "智慧线上贷款系统",
  "status": "draft|published",
  "fields": {
    "business_goal": "...",
    "core_functions": ["..."],
    "in_scope": "...",
    "out_of_scope": "...",
    "business_objects": ["..."],
    "terminology": [{"alias":"...", "canonical":"..."}],
    "integration_points": ["..."],
    "key_constraints": ["..."]
  },
  "evidence_refs": [
    {"doc_id":"evd_...", "chunk_id":"chk_...", "loc":"p3#para12", "snippet":"..."}
  ],
  "updated_by": "user_id",
  "updated_at": "2026-02-01T10:00:00"
}
```

> 向量召回仍可复用现有知识库：发布态画像可同步写入向量库（knowledge_type=`system_profile_published`），草稿态可选不写入，仅用于提示性文字。

### 2.3 ESB 索引（FR-I）

**ESB 明细索引：`data/esb_index.json`**

```json
{
  "meta": {
    "valid_statuses": ["正常使用"],
    "default_scope": "both",
    "updated_at": "2026-02-01T10:00:00"
  },
  "entries": [
    {
      "provider_system_id": "SOFP",
      "provider_system_name": "智慧线上贷款系统",
      "consumer_system_id": "HOP",
      "consumer_system_name": "开放平台",
      "service_code": "SOFP500002",
      "scenario_code": "2022000206",
      "service_name": "白名单查询接口",
      "status": "正常使用",
      "remark": "",
      "source_file": "esb.xlsx",
      "row_no": 12,
      "imported_at": "2026-02-01T10:00:00",
      "embedding": [0.1, 0.2, "..."]
    }
  ],
  "system_summary": [
    {
      "system_id": "SOFP",
      "system_name": "智慧线上贷款系统",
      "owner": "张三",
      "center": "基础平台开发",
      "total_interface_count": 89,
      "no_call_interface_count": 0,
      "extra": {}
    }
  ]
}
```

> 说明：ESB 需要支持过滤（system_id/system_name、status、scope），本期用“索引文件 + embedding字段”最容易落地；未来可切换为 Milvus + metadata filter。

### 2.4 代码扫描（FR-C）

**扫描作业索引：`data/code_scan_jobs.json`**

```json
{
  "job_id": "scan_...",
  "system_id": "SOFP",
  "system_name": "智慧线上贷款系统",
  "repo_path": "/path/to/repo",
  "status": "queued|running|completed|failed",
  "progress": 0.42,
  "result_path": "data/code_scan_results/scan_....json",
  "error": "",
  "created_by": "user_id",
  "created_at": "2026-02-01T10:00:00",
  "finished_at": "2026-02-01T10:03:00"
}
```

**能力目录结果：`data/code_scan_results/<job_id>.json`**

```json
{
  "system_id": "SOFP",
  "system_name": "智慧线上贷款系统",
  "generated_at": "2026-02-01T10:03:00",
  "items": [
    {
      "entry_type": "http_api|scheduled|mq_listener|outbound_call",
      "entry_id": "GET /api/v1/white-list/query",
      "owner": "SOFP",
      "summary": "白名单查询",
      "keywords": ["白名单","查询","客户"],
      "location": {"file":".../WhiteListController.java", "line": 120},
      "related_calls": [
        {"type":"feign", "target":"HOP", "hint":"OpenPlatformClient#xxx"}
      ]
    }
  ]
}
```

> 能力目录写入向量库：可选把每条 `item` 写入 `knowledge_store.json`（knowledge_type=`capability_item`），用于召回与归属提示（不扩范围）。

### 2.5 规则与审计

**证据等级规则：`data/evidence_level_rules.json`**

```json
{
  "version": 1,
  "rules": {
    "E3": {"require": ["capability_catalog"], "any_of": ["evidence_hit", "profile_published"]},
    "E2": {"any_of": ["evidence_hit", "profile_published"], "require_any": ["esb", "capability_catalog"]},
    "E1": {"any_of": ["esb", "evidence_hit_only"]},
    "E0": {"otherwise": true}
  },
  "updated_by": "admin_id",
  "updated_at": "2026-02-01T10:00:00"
}
```

**审计日志：`data/audit_logs.json`**

```json
{
  "id": "log_...",
  "scope": "task|global",
  "task_id": "task_...",
  "actor_role": "manager|admin",
  "actor_id": "user_id",
  "action": "override_evidence_level|force_confirm_system|update_rule_config",
  "target": {"system_id":"SOFP", "system_name":"..."},
  "before": {"evidence_level":"E1"},
  "after": {"evidence_level":"E2"},
  "remark": "原因...",
  "created_at": "2026-02-01T10:00:00"
}
```

---

## 3. 核心算法与规则（落地口径）

### 3.1 证据检索排序（A层）

1. 向量相似度：cosine(similarity)
2. 加权排序：`rank_score = similarity × trust_weight × recency_weight`
3. 召回不足触发：低于阈值视为“命中不足”，用于严肃模式阻断依据之一。

### 3.2 ESB 检索与过滤

- 过滤：
  - `include_deprecated=false`：只取 `status ∈ valid_statuses`
  - `scope=both|provider|consumer`：决定 system_id/system_name 的匹配字段
- 相似度对象文本（建议）：
  - `esb_text = "{service_name} 提供方:{provider_system_name} 调用方:{consumer_system_name} 场景:{scenario_code}"`

### 3.3 证据等级计算（E0~E3）

- 计算输入（每系统）：
  - A：是否有 evidence_hit（阈值以上命中）
  - B：是否有 profile_published
  - C：是否有 capability_catalog（扫描已提交/可用）
  - I：是否有 esb_entries（有效状态）
- 输出：
  - `evidence_level` + `missing_evidence[]`
- 任务内修正：
  - `manager` 可改 `evidence_level`，必须 `remark`，并写审计日志；仅影响当前任务。

### 3.4 严肃模式阻断（System Identify）

阻断条件建议（与需求一致，可配置）：
- `selected_systems` 必须每个都有 ≥1 条证据引用（A/B/C/I之一）；
- E0 不允许进入 selected；
- E1 默认进入 maybe（除非 manager 强行确认，且低置信度、扩大区间、留痕）。

---

## 4. Agent 输出 JSON Schema（设计阶段落地）

> 下列为“前后端契约”。后端需对 LLM 输出做校验与裁剪，保证结构稳定。

### 4.1 EvidenceRef

```json
{
  "source_type": "evidence|profile|capability|esb",
  "doc_id": "evd_...",
  "chunk_id": "chk_...",
  "loc": "p3#para12",
  "snippet": "最多200字",
  "score": 0.83
}
```

### 4.2 SystemIdentifyResult

```json
{
  "serious_mode": true,
  "selected_systems": [
    {
      "system_id": "SOFP",
      "system_name": "智慧线上贷款系统",
      "confidence": "高|中|低",
      "evidence_level": "E0|E1|E2|E3",
      "reasons": ["..."],
      "evidence_refs": [/* EvidenceRef */],
      "manual_override": false
    }
  ],
  "maybe_systems": [
    {
      "system_id": "HOP",
      "system_name": "开放平台",
      "reason": "证据不足/冲突点...",
      "missing_evidence": ["code","material","profile_published"],
      "evidence_refs": [/* EvidenceRef */]
    }
  ],
  "questions": [
    {"priority":"高|中|低", "question":"面向业务可回答的问题"}
  ],
  "block_reason": "触发阻断原因（如有）"
}
```

### 4.3 FeatureBreakdownResult（按系统）

```json
{
  "system_id": "SOFP",
  "system_name": "智慧线上贷款系统",
  "features": [
    {
      "feature_id": "feat_...",
      "feature_type": "crud|query|workflow|report|integration|other",
      "module": "功能模块",
      "title": "功能点名称",
      "description": "业务描述",
      "tags": ["归属依据", "集成点", "待确认", "非功能工作项"],
      "evidence_refs": [/* EvidenceRef */],
      "integration_hints": [
        {"provider_system_id":"SOFP","consumer_system_id":"HOP","service_name":"白名单查询接口","status":"正常使用"}
      ],
      "assumptions": ["..."]
    }
  ]
}
```

### 4.4 EstimateResult（按功能点）

```json
{
  "feature_id": "feat_...",
  "estimate_range": {"min": 2.0, "max": 5.0},
  "confidence": "高|中|低",
  "assumptions": ["..."],
  "key_factors": ["数据量", "规则复杂度", "集成点数量", "权限改造"],
  "risk_flags": ["low_confidence", "assumptions_over_threshold", "manual_override"],
  "notes": "可审计说明"
}
```

---

## 5. 后端接口设计（DTO + 权限）

> 路径可按现有 `API_PREFIX=/api/v1` 风格落地；此处给最小集合与请求/响应关键字段。

### 5.1 证据库（A）

1) `POST /api/v1/knowledge/evidence/import`（manager）
- form-data：`file` + `system_id/system_name` + `trust_level` + 可选 `doc_date/source_org/version_hint`
- 返回：`doc_id`、`chunk_count`、`skipped_reason`（如图片/空文本）

2) `POST /api/v1/knowledge/evidence/search`（manager/expert）
- body：`query`、可选 `system_id/system_name`、`top_k`、`similarity_threshold`
- 返回：命中列表（含 EvidenceRef + 预览入口信息）

3) `GET /api/v1/knowledge/evidence/stats?system_id=&system_name=`（manager）
- 返回：doc_count、chunk_count、trust_level分布、最近导入时间等

4) `GET /api/v1/knowledge/evidence/preview/{doc_id}`（manager/expert）
- 返回：在线预览（PDF inline / DOCX/PPTX HTML或文本预览）
- 约束：不提供下载；需校验“是否在任务关联范围内”（expert）

### 5.2 ESB（I）

1) `POST /api/v1/knowledge/esb/import`（manager）
- form-data：`file`（xlsx/csv）+ 可选列映射 `mapping_json`
- 返回：`imported`、`skipped`（缺列/空值/无效状态）+ 示例错误

2) `POST /api/v1/knowledge/esb/search`（manager/expert）
- body：`query`、可选 `system_id/system_name`、`scope`、`include_deprecated`、`top_k`

3) `GET /api/v1/knowledge/esb/stats?system_id=&system_name=`（manager）
- 返回：active_entry_count、deprecated_entry_count、active_unique_service_count

### 5.3 代码扫描（C）

1) `POST /api/v1/code-scan/run`（manager）
- body：`system_id/system_name`、`repo_path`、`options`（过滤规则等）
- 返回：`job_id`

2) `GET /api/v1/code-scan/status/{job_id}`（manager）

3) `GET /api/v1/code-scan/result/{job_id}`（manager）

4) `POST /api/v1/code-scan/commit/{job_id}`（manager）
- 将能力目录写入向量库（knowledge_type=`capability_item`）并可生成统计

### 5.4 规则配置与任务内覆盖（Z）

1) `GET /api/v1/rules/evidence-level`（admin/manager只读）
2) `PUT /api/v1/rules/evidence-level`（admin，写审计日志）
3) `POST /api/v1/tasks/{task_id}/override/evidence-level`（manager）
- body：`system_id/system_name`、`new_level`、`remark`（必填）

---

## 6. 前端页面与交互（最小可用）

### 6.1 知识与索引（manager）

建议在现有“知识库管理”页扩展为多 Tab：
- Tab1：系统画像（B）——草稿/发布、字段编辑、证据引用选择
- Tab2：证据库（A）——导入、列表、检索、在线预览
- Tab3：ESB索引（I）——导入、检索、统计、状态过滤
- Tab4：代码扫描（C）——填写 repo_path 触发、进度、结果预览、提交入库

### 6.2 规则配置（admin）

新增“证据等级规则配置”页：
- 可视化编辑（JSON编辑器亦可）+ 变更日志列表
- 默认值一键恢复

### 6.3 任务评估页（manager/expert）

- 系统识别区：展示 `selected/maybe/questions` + 每系统 evidence_level、证据入口、风险提示
- 支持 manager：
  - 强行确认（现有口径）与 evidence_level 结果修正（必须备注）
- 专家侧：
  - 可查看证据全文在线预览（无下载）

---

## 7. 风险与降级策略

1. DashScope 不可用：允许任务进入“仅规则+人工”的降级（输出强制低置信度+阻断提示），并记录失败原因。
2. DOCX/PPTX 预览：无法渲染原文件时降级为抽取文本预览（已在需求中明确）。
3. ESB 列名不一致：导入提供列映射；仍缺必填列则失败并提示。
4. 代码扫描性能：默认只扫 `src/main/java` + 关键注解；大仓库按目录/文件数分批并显示进度。

---

## 8. 研发拆分建议（用于下一步task拆分）

1. 后端：证据库 A（导入/切分/检索/预览/权限）
2. 后端：ESB 索引 I（导入/embedding/检索/统计/过滤）
3. 后端：代码扫描 C（job+结果+commit入库）
4. 后端：证据等级规则 Z（配置界面API + 任务内修正+审计）
5. Agent：系统识别/拆分/估算 prompt 与 JSON schema 校验
6. 前端：知识库页多Tab + 规则配置页 + 任务页展示与操作

