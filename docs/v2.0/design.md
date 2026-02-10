# 需求分析与评估系统 v2.0 技术方案设计

| 项 | 值 |
|---|---|
| 状态 | Review（增量：CR-20260209-001） |
| 作者 | AI |
| 评审 | AI（待自审；结论将追加到 `docs/v2.0/review_design.md`） |
| 日期 | 2026-02-09 |
| 版本号 | v2.0 |
| 文档版本 | v0.16 |
| 关联提案 | `docs/v2.0/proposal.md`（v0.16） |
| 关联需求 | `docs/v2.0/requirements.md`（v1.21） |
| 关联主文档 | `docs/技术方案设计.md` |
| 关联接口 | `docs/接口文档.md` |

## 0. 摘要（Executive Summary）
- 本次交付以“系统画像 + 多源知识 + 学习闭环”为主线，提升功能点拆分与工作量估算的准确性，并以“效能看板”形成可行动的指标闭环。
- 核心链路：代码扫描/ESB/文档导入 → 构建系统画像（草稿/发布）→ AI 内部检索聚合画像/能力/文档/ESB → 复杂度三维评分 → 评估结果（PM可修正并留痕）→ 看板统计（基于冻结快照）。
- 技术路线：保持“无数据库迁移”的约束，数据落地以 `data/*.json` 为主；向量检索支持 local（小规模）与 Milvus（验收/规模化）两种后端；新增/改造 API-001~015 并在 v2.0 新接口统一错误响应结构。
- 增量（CR-20260209-001）：前端支持 activeRole 角色切换与任务管理Tab统一；系统画像引入“AI总结→通知→采纳/忽略→可重试”闭环并新增通知中心接口；发起评估/知识导入兼容 `.doc/.xls` 旧格式解析并补齐安全隔离策略。
- 关键风险与边界：repo_path / repo_archive 必须受 allowlist 与安全解压保护；local 向量库存在容量上限；不做系统画像可视化/AI引用提示/治理机制等（见 Non-goals），上线以灰度+回滚方案兜底。

## 0.5 决策记录（Design 前置收集结果）

> 本章节用于固化用户已确认的关键技术决策与环境配置口径；后续如需变更，按 CR 流程记录并同步到主文档。

### 技术决策
| 编号 | 决策项 | 用户选择 | 理由/备注 |
|------|--------|---------|----------|
| D-01 | 后端语言/框架 | Python / FastAPI | 复用现有代码基线，便于快速交付 |
| D-02 | 前端语言/框架 | React + Ant Design | 复用现有前端基线与组件体系 |
| D-03 | 向量检索后端 | local（默认）/ Milvus（可选） | local 作为小规模/降级；Milvus 用于 REQ-NF-002 性能验收与规模化 |
| D-04 | 持久化存储 | JSON 文件（`data/*.json`） | 明确“不做数据库迁移”约束；写入采用锁+原子替换 |
| D-05 | 部署形态 | Docker Compose 单机 | 私有化/内网部署优先；Milvus 作为可选组件 |
| D-06 | B角（代理负责人）权限口径 | 负责系统=主责+B角 | B角可执行知识导入/草稿编辑/AI总结重试；发布与统计仍仅主责（对齐 requirements v1.21） |
| D-07 | 旧格式文件解析 | 服务端支持 `.doc/.xls` 解析 | `.doc` 通过外部工具抽取文本；`.xls` 使用解析库抽取表格文本；解析过程需满足隔离/超时/清理（REQ-NF-007） |
| D-08 | 通知留存策略 | 已读通知保留90天（可配置） | 避免 JSON 存储长期膨胀；每日自动清理已读且过期的通知（对齐 API-017） |

### 环境配置（变量名口径；敏感值不落盘）
| 配置项 | 开发环境 | 生产环境 | 敏感 | 备注 |
|--------|---------|---------|------|------|
| `ALLOWED_ORIGINS` | `.env` | `.env` | 否 | CORS 白名单（逗号分隔） |
| `DASHSCOPE_API_KEY` | `.env`/`.env.backend` | `.env.backend` | 是 | LLM/Embedding 鉴权 |
| `KNOWLEDGE_ENABLED` | `.env.backend` | `.env.backend` | 否 | 知识库开关 |
| `KNOWLEDGE_VECTOR_STORE` | `.env`/`.env.backend` | `.env.backend` | 否 | `local` / `milvus` |
| `MILVUS_HOST`/`MILVUS_PORT` | `.env` | `.env` | 否 | 仅启用 Milvus 时需要 |
| `ADMIN_API_KEY` | `.env`/`.env.backend` | `.env.backend` | 是 | 管理写接口叠加保护（可选） |
| `JWT_SECRET` | `.env`/`.env.backend` | `.env.backend` | 是 | JWT 签名密钥 |
| `JWT_EXPIRE_MINUTES` | `.env`/`.env.backend` | `.env.backend` | 否 | JWT 过期时间 |
| `CODE_SCAN_REPO_ALLOWLIST` | `.env.backend` | `.env.backend` | 否 | `repo_path` 允许前缀列表（逗号分隔） |
| `CODE_SCAN_GIT_ALLOWED_HOSTS` | `.env.backend` | `.env.backend` | 否 | Git URL host allowlist（默认禁用 Git URL） |
| `REACT_APP_API_URL` | `.env.frontend` | `.env.frontend` | 否 | 前端调用后端 Base URL |

## 1. 设计目标与非目标

### 1.1 设计目标（可验证）
1. **系统画像闭环可落地**：支持 PM 触发代码扫描/ESB导入/文档导入，生成系统画像草稿并可发布（对齐：REQ-001~004，API-001~004）。
2. **AI评估可用画像与多源知识**：内部检索接口能返回画像、能力清单、文档与ESB集成信息（对齐：REQ-005/006，API-005/006）。
3. **学习闭环可追溯**：PM 修改轨迹可记录；专家差异统计可生成（对齐：REQ-007/008，API-007/008）。
4. **效能看板可下钻**：看板查询/导航/下钻筛选口径一致（对齐：REQ-009/018/020，API-009/010）。
5. **权限边界清晰**：管理员仅系统清单导入；PM 对“自己负责系统（主责或B角）”执行画像草稿侧写操作（导入/草稿编辑/AI总结重试）；画像发布仅主责；管理员/专家仅只读系统画像；Viewer 只读看板与任务明细（下钻/任务列表，只读）（对齐：REQ-NF-004，REQ-020，5.1 权限矩阵）。
6. **无数据库迁移**：新增/扩展数据全部落地在 `settings.REPORT_DIR` 的 JSON 文件中，可回滚（对齐：Out of Scope、Proposal v0.8 决策）。
7. **UI/UX补充可落地**：支持 activeRole 角色切换；任务管理Tab统一；系统画像工作台拆分为“知识导入/信息看板”两页且不展示导入历史并优化布局；编辑功能点页与管理员任务详情页布局优化；COSMIC配置按类别平铺Tab；菜单移除“效果统计”并调整顺序（对齐：REQ-010/016/021/022/023/025/026）。

### 1.2 非目标（Non-goals）
与 `docs/v2.0/requirements.md` 的 Out of Scope 保持一致，核心包括：
- 不做系统画像可视化展示（能力树/关系图等）。
- 不做 AI 使用提示（不展示“参考了哪些材料”）。
- 不做“优化建议治理机制”（版本号/一键回滚/管理员审批）。
- 不做文档技术特征结构化自动抽取（文档仅用于检索与证据引用）。
- 不做数据库迁移（仅复用现有 JSON 文件存储）。
- 不做 B角 纳入统计口径/排行榜（B角仅代理操作；统计仍仅主责）。

### 1.3 关键约束（Constraints）
- **无数据库迁移**：所有新增数据落地到 `data/*.json`（锁文件 + 原子写）；需要可回滚。
- **可私有化/内网部署**：默认单机 Docker Compose；Milvus 为可选依赖（用于规模化/性能验收）。
- **安全合规优先**：不落地源码与敏感信息；repo_path / repo_archive 必须做 allowlist 与安全解压防护。
- **指标口径统一**：看板与统计以冻结快照为准，避免系统清单变更导致历史漂移（对齐 REQ-009/020）。
- **缺少真实工时基线**：v2.0 的“准确率”口径以“AI 初稿 vs 最终评估”对齐（不涉及实际消耗）。

### 1.4 关键假设（Assumptions）
| 假设 | 可验证方式 | 失效影响 | 兜底策略 |
|---|---|---|---|
| ESB 治理文档能提供稳定字段集 | 用样例 Excel 跑 API-003 预览校验（含 skipped/invalid） | ESB 集成关系无法可靠导入 | 支持 `mapping_json` 手动映射；无法映射则仅提示问题不入库 |
| 代码扫描环境可访问 repo_path 或可上传压缩包 | STAGING 用样例仓验证 API-001/002；校验 allowlist 与解压阈值 | 无法生成能力清单/技术特征 | 允许 repo_archive 上传；仍失败则仅使用文档/ESB 构建画像 |
| embedding/向量库可用（或可接受降级） | 演练 DashScope 超时/禁用；验证 `EMB_001` 与 degraded 标记 | 画像发布/导入失败或检索效果下降 | 写入类失败阻断（不写半条）；检索类降级到关键词匹配 |
| 本期不引入“实际工时”闭环 | 需求确认（Out of Scope） | 无法做“评估 vs 实际”准确率 | 先固化修改轨迹与统计口径，后续版本再扩展 |

### 1.5 需求-设计追溯矩阵（必须）
| REQ-ID | 需求摘要 | 设计落点（章节/模块/API） | 验收方式/证据 |
|---|---|---|---|
| REQ-001 | 代码扫描能力提取 | 4.3.1（API-001） | `test_report.md`：TEST-001 |
| REQ-002 | 代码扫描结果入库 | 4.3.1（API-002）+ 4.2.1 | `test_report.md`：TEST-002 |
| REQ-003 | ESB 文档导入 | 4.3.2（API-003） | `test_report.md`：TEST-003 |
| REQ-004 | 系统画像管理（草稿/发布/查看） | 4.2.1 + 4.3.4（API-004/012） | `test_report.md`：TEST-004 |
| REQ-005 | 系统画像检索 | 4.3.10（API-005） | `test_report.md`：TEST-005 |
| REQ-006 | 复杂度三维度评估 | 4.3.10（API-006） | `test_report.md`：TEST-006 |
| REQ-007 | 修改轨迹记录 | 4.3.5（API-007） | `test_report.md`：TEST-007 |
| REQ-008 | 专家差异统计 | 4.3.11（API-008） | `test_report.md`：TEST-008 |
| REQ-009 | 效能看板指标展示 | 4.3.7/4.3.8（API-009） | `test_report.md`：TEST-009 |
| REQ-010 | 任务管理状态分组 | 4.3.6（API-010） | `test_report.md`：TEST-010 |
| REQ-011 | 知识库文档导入 | 4.3.3（API-011） | `test_report.md`：TEST-011 |
| REQ-012 | 时间格式统一 | 4.1.4（前端） | `test_report.md`：TEST-012 |
| REQ-013 | 系统材料完整度显示 | 4.2.1/4.3.4 + 4.1.4（前端展示） | `test_report.md`：TEST-013 |
| REQ-014 | 长文字截断优化 | 4.1.4（前端） | `test_report.md`：TEST-014 |
| REQ-015 | 评估页布局优化 | 4.1.4（前端） | `test_report.md`：TEST-015 |
| REQ-016 | COSMIC 配置简化 | 4.1.3（前端） | `test_report.md`：TEST-016 |
| REQ-017 | 报告下载 | 4.3.9（API-014） | `test_report.md`：TEST-017 |
| REQ-018 | 看板导航与视角切换 | 4.1.3 + 4.3.7（API-009/010） | `test_report.md`：TEST-018 |
| REQ-019 | 系统清单配置优化 | 4.2.6 + 4.4（API-015） | `test_report.md`：TEST-019 |
| REQ-020 | 看板任务明细下钻 | 4.3.7（drilldown_filters→API-010） | `test_report.md`：TEST-020 |
| REQ-021 | 菜单结构调整 | 4.1.3（前端） | `test_report.md`：TEST-027 |
| REQ-022 | 系统画像工作台重构 | 4.1.3（前端） | `test_report.md`：TEST-028 |
| REQ-023 | 多角色切换（activeRole） | 4.1.3（前端：AuthContext/MainLayout/usePermission） | `test_report.md`：TEST-029（待补） |
| REQ-024 | 画像AI总结与采纳 | 4.2.1 + 4.3.4 + 4.3.12（API-017/018） | `test_report.md`：TEST-030（待补） |
| REQ-025 | 编辑功能点页面优化 | 4.1.3（前端） | `test_report.md`：TEST-031（待补） |
| REQ-026 | 管理员任务详情布局重设计 | 4.1.3（前端） | `test_report.md`：TEST-032（待补） |
| REQ-027 | 旧格式文件支持（DOC+XLS） | 4.3.3 + 4.3.13（API-016） | `test_report.md`：TEST-033（待补） |
| REQ-NF-001 | 代码扫描性能 | 7.1 + 并发/排队策略（4.3.1） | `test_report.md`：TEST-021 |
| REQ-NF-002 | 向量检索性能 | 7.1 + Milvus 验收前置 | `test_report.md`：TEST-022 |
| REQ-NF-003 | 敏感信息脱敏 | 6.3（数据最小化/脱敏） | `test_report.md`：TEST-023 |
| REQ-NF-004 | 访问控制 | 6.1/6.2（RBAC/资源级权限） | `test_report.md`：TEST-024 |
| REQ-NF-005 | 并发处理 | 4.3.1（max_workers/queued） | `test_report.md`：TEST-025 |
| REQ-NF-006 | 修改轨迹保留期 | 4.3.5（清理） | `test_report.md`：TEST-026 |
| REQ-NF-007 | 旧格式解析安全 | 6.2（隔离/超时/清理） | `test_report.md`：TEST-034（待补） |

### 1.6 质量属性与典型场景（Quality Scenarios，推荐）
| Q-ID | 质量属性 | 场景描述 | 目标/阈值 | 验证方式 |
|---|---|---|---|---|
| Q-01 | 性能 | 10万行代码扫描（含并发排队） | P95 < 10min；running≤5 | TEST-021、TEST-025 |
| Q-02 | 性能 | 10万向量检索（top_k=20） | P95 < 500ms（Milvus） | TEST-022 |
| Q-03 | 安全 | 非主责 PM 访问画像写接口 | 403 + `AUTH_001` | TEST-024 |
| Q-04 | 可用性 | embedding 服务不可用 | 写入类失败 `EMB_001`；检索类 degraded | 自动化回归 + 手工演练（见 test_report） |

## 2. 系统上下文与边界

### 2.1 系统边界（输入/输出/责任）
**输入**：
- 代码仓库来源：服务端可访问的 `repo_path`（默认），或上传 `repo_archive`（备选，zip/tar.gz）。
- ESB 治理文档：Excel/CSV。
- 技术文档/历史评估文档（L0）：docx/pdf/pptx/txt/xlsx/csv（以现有解析能力为准）。
- 评估任务数据：现有任务 JSON（`task_storage.json`）。

**输出**：
- 系统画像（草稿/发布态）与完整度评分。
- 向量库条目：能力清单（code）、文档（document, level=normal/l0）、系统画像（system_profile）、ESB集成（esb）。
- 修改轨迹与统计口径数据（PM修正率/AI准确率等）。
- 效能看板查询结果 + 下钻筛选条件。

**责任边界**：
- 本系统负责采集“元数据/摘要”，不落地保存源码与原始文档（除非明确的上传文件如头像/需求文档本就存在于系统上传目录）。

### 2.2 外部依赖与失败模式
| 依赖 | 用途 | 失败模式 | 系统策略 |
|---|---|---|---|
| DashScope LLM/Embedding | 评估与向量化 | 超时/限流/不可用 | 写入类接口返回 `EMB_001`；检索类接口降级到关键词匹配 |
| Milvus（可选） | 向量库后端 | 连接失败 | 自动回退到本地向量库（local） |
| Git/本地文件系统 | 代码扫描 | 路径不可访问/权限不足 | 输入校验 + allowlist 限制，返回 `SCAN_001/SCAN_004` |

## 3. 总体架构

### 3.1 架构概述
```
┌─────────────┐       HTTP/JSON        ┌───────────────┐
│  Frontend   │  ───────────────────▶  │   FastAPI     │
│  React+Ant  │                        │   Backend     │
└─────────────┘                        ├───────────────┤
                                       │ Auth/RBAC      │
                                       │ System List    │
                                       │ System Profile │
                                       │ Code Scan Jobs │
                                       │ ESB Imports    │
                                       │ Knowledge      │
                                       │ Tasks+Traces   │
                                       │ Dashboard      │
                                       └───────┬───────┘
                                               │
                      ┌────────────────────────┼────────────────────────┐
                      │                        │                        │
                ┌─────▼─────┐            ┌─────▼─────┐            ┌─────▼─────┐
                │ JSON Store │            │ VectorStore│            │  DashScope │
                │ data/*.json│            │ local/milvus│           │ LLM/Embed  │
                └───────────┘            └────────────┘            └───────────┘
```

### 3.2 模块划分与职责（后端）
- **Auth/RBAC**：JWT 登录、角色校验、资源级权限校验（system/task 粒度）。
- **System List**：系统清单模板下载、预览校验、确认导入、热加载缓存刷新。
- **System Profile**：画像草稿/发布态、证据引用、完整度评分、过时标记。
- **Code Scan Jobs**：代码扫描任务创建/查询/结果入库（能力清单写入向量库）。
- **ESB Imports**：ESB 文件解析、字段映射、过滤/入库/检索、更新画像完整度。
- **Knowledge Imports**：技术文档与历史评估L0导入、切分与向量化、更新画像完整度。
- **Tasks + Modification Traces**：任务列表筛选与分组、评估详情、修改轨迹记录、冻结口径写入。
- **Efficiency Dashboard**：聚合统计（趋势/排行/下钻），返回统一 widgets 结构。

### 3.3 技术选型与依赖策略
原则：不引入非必要新依赖；优先复用现有实现（文件存储/本地向量库/既有解析器）。

| 组件 | 选型 | 理由 | 替代方案 | 维护状态 | 安全评估 | 风险/备注 |
|---|---|---|---|---|---|---|
| Web 框架 | FastAPI | 现有代码 | Flask | 活跃 | 主流框架 | 需统一错误响应结构 |
| 向量库 | local（JSON向量）/ Milvus（可选） | 无DB迁移、可私有化 | 仅Milvus | 活跃 | 需管控访问与数据最小化 | 本地向量库容量需关注 |
| 文档解析 | 现有 `document_parser` | 已支持多格式 | 引入新解析库 | 活跃 | 需防 zip bomb/大文件 | 解析失败需降级 |
| 代码扫描 | 现有 `CodeScanService` + 扩展 | 无需额外依赖 | 外部扫描器 | 活跃 | 需限制 repo_path/解压安全 | 多语言支持非本期 |

## 4. 详细设计

### 4.1 模块与接口落地策略
#### 4.1.1 接口兼容策略
- **新增为主，保留旧接口**：按 `requirements.md` 的 API-001~018 新增/改造接口；同时保留现有已被前端使用的接口路径作为兼容层（例如 `/api/v1/code-scan/run` 兼容到 `/api/v1/code-scan/jobs`）。
- **响应结构逐步统一**：新接口优先遵循 `error_code/message/request_id` 的错误响应；旧接口短期保持 `{code, message, data}`，在 Implementation 阶段通过适配器逐步统一。

#### 4.1.2 路由与服务映射（建议）
- `backend/api/code_scan_routes.py`：实现 API-001/002（jobs + ingest），旧 `run/status/result/commit` 兼容保留。
- `backend/api/system_profile_routes.py`：实现 API-004/012（草稿/发布/列表/完整度）与 API-018（AI总结重试）。
- `backend/api/knowledge_routes.py`：实现 API-011（imports），保留旧 `/import` 作为兼容别名。
- 新增 `backend/api/esb_routes.py`：实现 API-003（/api/v1/esb/imports）。
- `backend/api/notification_routes.py`：实现 API-017（notifications 查询/已读/清理）。
- 评估任务相关接口优先在 `backend/api/routes.py` 落地（已有 `/api/v1/tasks`、`/api/v1/tasks/{task_id}/evaluation` 等），扩展以满足 API-007/010/013/014/016。
- 新增 `backend/api/efficiency_routes.py`：实现 API-009（dashboard/query）。

#### 4.1.3 前端路由与菜单结构（UI/UX补充）
> 目标：让“入口/验收路径”可复现，并与 `requirements.md` 的 REQ-016/021/022 一致。

- 菜单顺序（一级）：任务管理 → 系统画像（PM）/配置管理（Admin） → 效能看板（个人分组保持不变）
- Header 增量（REQ-023/024）：角色切换器（activeRole）+ 通知入口（未读数）
  - activeRole：前端状态（AuthContext），不刷新JWT；默认选最高权限角色（admin > manager > expert > viewer），刷新页面可恢复上次选择
  - 通知入口：Header 展示铃铛图标 + 未读数；点击进入通知列表页（建议路由 `/notifications`）
- 删除入口：侧边栏不展示“效果统计”（`/reports/ai-effect`）
  - 兼容直达：用户访问 `/reports/ai-effect` 时，前端跳转到 `/dashboard` 并提示“已迁移到效能看板”
- 菜单结构（对齐 REQ-021）：
  - 管理员：保留“配置管理”菜单（系统清单、规则管理、用户管理）
  - 项目经理：不展示“知识库管理”菜单；将“系统画像”提升为一级菜单，包含“知识导入/信息看板”
- 任务管理页（REQ-010/023）：
  - 顶部统一两个Tab：进行中（pending/in_progress）/ 已完成（completed/closed）
  - 数据范围：由 activeRole 决定（admin=全量；manager=自己发起；expert=自己参与），后端仍以真实 roles 做最终鉴权
- 规则管理（COSMIC配置）：`/config/cosmic`
  - 页面右上角提供“使用说明”按钮，点击弹出 Modal（业务语言说明 + 拆分示例）
  - 移除页面顶部的说明类 Alert/Card（避免挤占编辑区域）
  - 技术配置默认折叠（仅管理员按需展开编辑）；不改后端COSMIC算法/接口/存储
- 系统画像工作台拆页：
  - 兼容入口：`/system-profiles` 重定向到 `/system-profiles/board`（携带 query 参数）
  - 知识导入：`/system-profiles/import`（代码扫描/ESB导入/知识导入；不展示导入历史/最近任务列表）
    - 系统TAB范围：仅展示当前用户负责系统（主责或B角）
    - 反馈口径：展示“最近一次提交”的 code scan `job_id + status`（可手动刷新 `GET /api/v1/code-scan/jobs/{job_id}`）；当 completed 时展示“入库”按钮
  - 信息看板：`/system-profiles/board`（系统概览、7字段编辑、完整度分析、保存草稿/发布）
    - AI建议：如 `ai_suggestions` 存在，逐字段展示“当前值 vs 建议值”，支持采纳/忽略；失败通知可触发“重试生成AI建议”（API-018）
  - TAB同步：通过 URL query（如 `?system_name=HOP`）在两页间保持当前选中系统

#### 4.1.4 前端体验优化（补充：REQ-012~015）
> 目标：把“体验优化”也纳入可复现验收路径，避免只在实现里零散修补。

- 时间格式统一（REQ-012）：任务列表/评估页/看板等统一使用同一格式化函数（含时区与空值兜底）。
- 长文字截断与可读性（REQ-014）：评估页对长文本采用“默认折叠 + 展开/收起”交互，避免撑爆布局。
- 评估页布局优化（REQ-015）：关键卡片（功能点、复杂度、材料完整度、下载入口）分区清晰，最小分辨率（如 1366×768）可用。
- 系统材料完整度展示（REQ-013）：评估页展示完整度评分与缺失项；当完整度接口失败/无数据时展示“完整度未知”（不阻断评估）。
- 编辑功能点页优化（REQ-025）：移除“系统校准（知识库）”；系统Tab按完整度阈值红/黄/绿着色；备注列默认截断+Tooltip/展开。
- 管理员任务详情页优化（REQ-026）：三段式布局（摘要/主体/分析），下载入口收敛到顶部操作栏；偏离度分析可折叠。

### 4.2 数据模型（文件存储）
> 所有数据默认存放在 `settings.REPORT_DIR`（默认 `data/`），统一使用“文件锁 + 原子写”保证一致性。
>
> 并发与一致性策略（设计决策）：
> - **跨进程锁**：优先使用 `fcntl.flock`（Linux/Docker默认可用），以 `*.lock` 文件实现互斥。
> - **回退策略**：当 `fcntl` 不可用时，退化为进程内 `threading.RLock`（仅保证单进程/单Worker场景）。
> - **原子写**：所有写入采用 `tmp + os.replace`，避免半写文件导致 JSON 损坏。
> - **锁持有最小化**：解析/embedding 等重计算不在持锁区内执行，仅对“读-改-写”临界区加锁。

#### 4.2.1 System Profile（画像）
- 存储：`data/system_profiles.json`
- 主键：优先 `system_id`；若缺失则降级用 `system_name` 唯一。
- 推荐结构（示意）：
```json
{
  "system_id": "sys_0001",
  "system_name": "core-banking",
  "status": "draft",
  "fields": {
    "in_scope": "...",
    "out_of_scope": "...",
    "core_functions": "...",
    "business_goals": "...",
    "business_objects": "...",
    "integration_points": "...",
    "key_constraints": "..."
  },
  "field_sources": {
    "in_scope": "manual",
    "out_of_scope": "ai",
    "core_functions": "manual",
    "business_goals": "ai",
    "business_objects": "manual",
    "integration_points": "manual",
    "key_constraints": "manual"
  },
  "ai_suggestions": {
    "in_scope": "...",
    "out_of_scope": "...",
    "core_functions": "...",
    "business_goals": "...",
    "business_objects": "...",
    "integration_points": "...",
    "key_constraints": "..."
  },
  "ai_suggestions_updated_at": "2026-02-09T10:00:00",
  "evidence_refs": [{"source_type": "code_scan", "source_id": "scan_xxx"}],
  "completeness": {"code_scan": true, "documents_normal": 8, "esb": true},
  "completeness_score": 70,
  "pending_fields": ["integration_points"],
  "is_stale": false,
  "updated_at": "2026-02-06T17:00:00",
  "published_at": null
}
```
- 字段兼容：为兼容历史数据/实现细节，允许 `business_goal` 作为 `business_goals` 的别名；服务端在写入与 embedding 构建时做归一化。
  - canonical key：`business_goals`
  - 写入归一化：若仅收到 `business_goal`，则写入时映射到 `business_goals`
  - 读取归一化：若历史数据仅存在 `business_goal`，读取时补齐 `business_goals`（必要时也可同时返回 `business_goal` 以兼容旧前端）
- AI建议字段（增量，REQ-024）：
  - `ai_suggestions`：按字段给出候选建议文本（不自动覆盖 fields）
  - `field_sources`：标记字段当前值来源（manual/ai）；当字段为 manual 时后台总结不得覆盖 fields，仅可更新 ai_suggestions
  - `ai_suggestions_updated_at`：用于前端展示“建议更新时间”与重试判断

#### 4.2.2 Code Scan Jobs（扫描任务）
- 存储：`data/code_scan_jobs.json`，结果目录：`data/code_scan_results/`
- 关键字段：`job_id/system_id/system_name/repo_source/status/progress/result_path/created_by/created_at`
- 幂等键：`(system_id, repo_hash, options_hash)`；支持 `force=true` 绕过。

#### 4.2.3 ESB Index（ESB索引）
- 存储：`data/esb_index.json`
- 兼容策略：保留现有结构（meta/entries/system_summary），新增 `system_id` 过滤能力与 `imported_at`。
- 本期设计决策：**按系统导入并过滤无关行**（若行的 `provider_system_id` 与 `consumer_system_id` 均不等于请求中的 `system_id`，计入 `skipped` 且不入库），以匹配需求口径与权限模型。
- ESB 文档字段约定（参考模板 `data/接口申请模板.xlsx`）：
  - **服务方关键字段**：`系统标识`/`provider_system_id`、`系统名称`/`provider_system_name`、`系统负责人`/`provider_owner`、`服务场景码`/`service_scenario_code`、`服务名称`/`service_name`、`交易码`/`transaction_code`、`交易名称`/`transaction_name`
  - **消费方关键字段**：`系统标识`/`consumer_system_id`、`系统名称`/`consumer_system_name`、`系统负责人`/`consumer_owner`
  - **投产字段**：`服务方投产类型`/`provider_deploy_type`、`消费方投产类型`/`consumer_deploy_type`、`申请上线`/`planned_date`、`实际上线`/`actual_date`
  - **验收检查**：`调用日志检查`/`log_check_status`、`服务方系统检查`/`provider_check_status`、`消费方系统检查`/`consumer_check_status`
  - **映射建议**：`mapping_json` 支持候选列名列表（如 `{"provider_system_id": ["系统标识", "系统ID"]}`），导入时按顺序匹配

#### 4.2.4 Knowledge Store（知识库）
- 存储：`data/knowledge_store.json`（local），或 Milvus（可选）
- 元数据最小化：
  - `knowledge_type=document/code/system_profile/esb`
  - `level=normal/l0`（仅 document 可为 l0）
  - `system_name/system_id`（尽量写入；未提供时可用现有 `guess_system_name` 推断）
- **落地决策**：为提升可控性，API-011 支持可选参数 `system_name/system_id`（不影响既有契约的兼容性；缺省时走推断逻辑），用于更新对应系统画像完整度。
- L0 文档说明：历史工作量评估结果（如 `data/工作量评估模板.xlsx`）作为 L0 文档导入时，系统将其视为自由文本进行检索与证据引用，**不依赖固定表格结构解析**。文档中包含的功能模块分解、Wideband Delphi 估算、工作量分配等数据仅用于 AI 上下文理解，不直接结构化入库。

#### 4.2.5 Task Storage（评估任务/冻结快照/轨迹）
- 存储：`data/task_storage.json`（已存在）
- 扩展字段（v2.0）：
  - `frozen_at`：当任务从 `in_progress` → `completed` 时写入（仅一次）。
  - `owner_snapshot`：冻结时从系统清单读取“主责”快照并写入（用于看板统计）。
  - `ai_initial_features/ai_initial_feature_count`：AI 首次评估完成时固化（用于修改轨迹的 `original_ai_reasoning` 与 PM修正率分母）。
  - `modification_traces`：存放 API-007 写入的轨迹记录（保留期默认 180 天）。

#### 4.2.6 System List（系统清单）owner 字段约定（关闭 OP-DES-001）
> 目标：把“系统主责”变成可程序化校验的字段，支撑资源级权限（系统画像写、扫描/导入等）。

- 存储位置（MVP）：主系统清单的 `extra` 字段（JSON）中保存 owner 信息（不新增表/不迁移）。
- **canonical keys（推荐）**：
  - `owner_id`：用户ID（`users.json` 中的 `user.id`），用于鉴权判断（强建议填写）。
  - `owner_username`：用户名（用于兜底映射到 user.id）。
  - `owner_name`：展示名（仅展示用途，不参与授权判断）。
  - `backup_owner_ids`：B角用户ID列表（字符串数组；Excel 中可用逗号分隔字符串导入后转换为数组）。
  - `backup_owner_usernames`：B角用户名列表（用于兜底映射到 user.id；可选）。
- 导入模板列名约定（Design 决策）：
  - 推荐在系统清单 Excel 直接新增两列：`owner_id`、`owner_username`（列名即 canonical key）。
  - 若需要支持B角代理操作，推荐新增两列：`backup_owner_ids`、`backup_owner_usernames`（可为空）。
  - 为兼容历史/中文表头，导入时允许别名映射到 canonical key，例如：
    - `系统负责人ID/负责人ID` → `owner_id`；`系统负责人账号/负责人账号` → `owner_username`
    - `B角ID/代理负责人ID` → `backup_owner_ids`；`B角账号/代理负责人账号` → `backup_owner_usernames`
- 授权判定规则：
  1. 若系统存在 `owner_id`：当 `owner_id == current_user.id` 时判定为“主责”。
  2. 若系统存在 `backup_owner_ids`：当 `current_user.id ∈ backup_owner_ids` 时判定为“B角”（允许草稿侧写操作，不允许发布）。
  3. 若仅存在 username 口径：分别尝试把 `owner_username/backup_owner_usernames` 映射到 user.id；映射失败则视为“未配置”。
  4. 未配置主责/代理：系统画像草稿侧写操作（扫描/导入/保存草稿/重试AI总结）一律拒绝（403，`AUTH_001`），避免越权。

#### 4.2.7 Notification Store（通知中心）
- 存储：`data/notifications.json`
- 主键：`notification_id`（实现可复用既有字段 `id` 并在 API 层映射）
- 推荐结构（示意）：
```json
{
  "notification_id": "notice_xxx",
  "user_id": "user_001",
  "type": "system_profile_summary_ready",
  "status": "unread",
  "payload": {"system_id": "sys_0001", "system_name": "core-banking", "link": "/system-profiles/board?system_id=sys_0001"},
  "created_at": "2026-02-09T10:00:00",
  "read_at": null
}
```
- 留存与清理（对齐 requirements API-017）：
  - 默认仅清理“已读且超过90天”的通知（天数可配置）
  - 用户仍可手动清理已读/删除单条；清理逻辑需走资源级权限（仅本人通知）

### 4.3 核心流程设计

#### 4.3.1 代码扫描（SCN-001 / API-001~002）
1. PM 调用 `POST /api/v1/code-scan/jobs` 创建扫描任务：
   - repo 采用 `repo_path`（默认）或 `repo_archive`（备选）。
2. 服务端校验：
   - 系统负责人校验（system_list.owner_id 或 system_list.backup_owner_ids）。
   - `repo_path` 校验分支：
     - **本地路径**：必须为绝对路径，且 realpath 命中 allowlist 根目录（否则 `SCAN_004`）。
     - **Git URL**：仅允许 `https/http/ssh`（禁止 `file://` 等本地协议）。
       - 设计决策（关闭 OP-DES-002）：默认 **不启用** Git URL 扫描；仅当配置 `CODE_SCAN_ENABLE_GIT_URL=true` 且命中 `CODE_SCAN_GIT_ALLOWED_HOSTS` allowlist 时放行。
       - clone 失败/不可访问/未启用：统一返回 `SCAN_001`。
   - `repo_archive` 解压安全（格式/大小/文件数/软链接）失败返回 `SCAN_005/SCAN_006`。
3. 后台扫描生成结果 JSON（仅元数据，不存源码）。
4. PM 调用 `POST /api/v1/code-scan/jobs/{job_id}/ingest` 将能力清单写入向量库（失败返回 `EMB_001`）。
5. 入库成功后更新系统画像草稿：
   - 追加 `evidence_refs`（source_type=code_scan）。
   - 标记 `completeness.code_scan=true`，刷新 `completeness_score`。

#### 4.3.2 ESB 导入（SCN-002 / API-003）
1. PM 调用 `POST /api/v1/esb/imports` 上传文件并指定 `system_id`。
   - 权限：仅允许目标系统主责或B角导入（system_list.owner_id / backup_owner_ids）。
2. 解析与字段映射：优先使用 `mapping_json`；否则用别名集合推断。
   - `mapping_json` 兼容规则（对齐 `requirements.md` API-003 示例）：
     - value 支持 `string`（列名）或 `array[string]`（候选列名列表，按顺序尝试）。
3. 按系统过滤：仅保留与 `system_id` 相关行（provider/consumer 命中其一）。
4. 生成 embedding 并写入向量库（失败返回 `EMB_001`，不更新画像完整度）。
5. 更新系统画像草稿（evidence_refs + completeness.esb）。

#### 4.3.3 文档导入（SCN-009 / API-011）
1. PM 调用 `POST /api/v1/knowledge/imports` 上传文件，指定 `knowledge_type` 与可选 `level`。
2. 文档解析 → 文本切分 → embedding → 写入向量库：
   - `knowledge_type=document`：支持 `level=normal/l0`；l0 在检索排序中降权（相似度×0.3）。
   - 允许格式（对齐 requirements REQ-011/REQ-027）：
     - 文档：`.docx` / `.doc` / `.pdf` / `.pptx` / `.txt`
     - 表格：`.xlsx` / `.xls` / `.csv`
     - 不支持：`.ppt`（旧格式；需预转换为 `.pptx` 或 `.pdf`）
   - 旧格式解析（REQ-027/REQ-NF-007）：
     - `.doc`：通过外部工具抽取文本（如 antiword 或 headless libreoffice 转换）；禁用宏/外链；在隔离临时目录执行
     - `.xls`：使用解析库抽取表格文本（不执行宏）；在隔离临时目录处理上传文件副本
     - 统一约束：非root运行、超时（默认≤60s，可配置）、成功/失败均清理临时文件
   - 单文件大小上限：建议 50MB（与现有实现保持一致）；超限返回 `KNOW_001`（或 413）。
3. 画像完整度更新规则：
   - 若请求提供 `system_name/system_id` 或推断成功，则更新对应系统画像的文档计数与 `completeness_score`。
   - 否则仅写入向量库，不更新任何画像（返回中提示“未绑定系统，不更新完整度”）。
   - 权限（绑定系统时）：仅允许目标系统主责或B角绑定系统并更新完整度（见 REQ-NF-004 / requirements API-011）。

#### 4.3.4 系统画像发布（SCN-003 / API-004）
1. PM 编辑草稿（PUT）：
   - 权限：主责或B角可保存草稿；系统计算 `pending_fields` 与 `completeness_score`。
   - 保存草稿时将对应字段 `field_sources.<field>` 置为 `manual`（与 requirements REQ-024 一致）。
2. 画像AI总结（异步，REQ-024 / API-018）：
   - 触发：代码扫描入库/ESB导入/知识库导入成功并绑定系统后，或 PM 手动调用 API-018 重试。
   - 后台任务输出 `ai_suggestions` 与 `ai_suggestions_updated_at`，**不得覆盖** `field_sources=manual` 的字段当前值（仅更新 ai_suggestions）。
   - 通知：成功发送 `system_profile_summary_ready`；失败发送 `system_profile_summary_failed`（含 error_code/error_reason + 重试入口）。
3. PM 发布（POST publish；仅主责）：
   - 校验发布必填字段：`in_scope`、`core_functions`（缺失返回 `PROFILE_003`）。
   - 写入向量库（`knowledge_type=system_profile`）：embedding 文本包含7字段（`in_scope/out_of_scope/core_functions/business_goals/business_objects/integration_points/key_constraints`，其中 `business_goal` 视作别名）。
   - embedding 失败返回 `EMB_001` 且发布不生效（保持 draft）。
4. 过时检查：每日/每周任务检查 `updated_at`，超过阈值（默认30天）标记 `is_stale=true`（仅标记，不阻塞使用）。

#### 4.3.5 修改轨迹记录（SCN-005 / API-007）
1. PM 在评估页面进行 delete/adjust/add 操作，调用 API-007 写入轨迹。
2. 服务端从 `task.ai_initial_features` 根据 `feature_id` 补齐 `original_ai_reasoning`，避免客户端篡改。
3. 单条轨迹限制：
   - 记录体 <= 10KB
   - reasoning 截断 1000 字并追加截断标记
4. 轨迹保留期：默认180天（配置项）；**实现策略**：每次写入轨迹时，对当前任务的 `modification_traces` 做一次轻量清理（按 `recorded_at` 过滤），避免引入额外调度依赖。

#### 4.3.6 任务工作流与冻结口径（用于看板统计）
**目标**：把“最终评估口径”固定到一个可追溯的冻结节点，供看板与下钻复用（对齐 `requirements.md 6.3`）。

**现有字段与v2.0口径映射（设计约定）**：
- 现有 `task.workflow_status`（内部）：`draft / awaiting_assignment / evaluating / completed / archived`
- API-010 对外 `status`（规范化）：
  - `pending`：`draft/awaiting_assignment`
  - `in_progress`：`evaluating`
  - `completed`：`completed`
  - `closed`：`archived`
- 现有 `task.status/ai_status`（AI作业进度）与 v2.0 看板统计无直接等价关系，仅用于进度展示。

**冻结写入唯一落点（实现落点）**：
- 以“PM确认最终评估结果”的动作作为冻结触发点（当前系统已存在确认接口雏形，例如 `/api/v1/requirement/confirm/{task_id}`，Implementation 阶段将补齐鉴权/幂等/字段写入）。
- 冻结写入规则（幂等）：
  - 若 `task.frozen_at` 已存在：忽略重复写入并返回当前快照（不允许覆盖，避免历史漂移）。
  - 否则写入：
    - `task.frozen_at = now`
    - `task.owner_snapshot = build_owner_snapshot(task)`（从系统清单读取当时主责快照）
    - `task.final_estimation_days_total / task.final_estimation_days_by_system`（以确认时的最终结果为准）

**owner_snapshot（建议结构，MVP）**：
```json
{
  "owners": [
    {"system_id": "sys_1", "system_name": "A", "owner_id": "user_x", "owner_name": "张三", "final_days": 12.0}
  ],
  "primary_owner_id": "user_x",
  "primary_owner_name": "张三"
}
```

#### 4.3.7 效能看板查询与下钻（SCN-007 / API-009 / API-010）
- API-009 返回 `widgets[]`，每个 widget 附带 `sample_size` 与可复用的 `drilldown_filters`。
- 下钻落地：
  - 前端将 `drilldown_filters` 映射为 API-010 的 query 参数，进入任务列表页。
  - API-010 的过滤口径必须与看板统计一致（按 `frozen_at/owner_snapshot/final_estimation_days_by_system`）。
- “导出”策略（OP-DES-106 设计决策）：
  - 本期不新增独立导出 API；由前端基于 API-010 分页拉取并导出（或后续迭代新增 `/tasks/export`）。

#### 4.3.8 Dashboard Widget Catalog（MVP）
> 目标：把 `requirements.md` 的指标口径（6.3）映射为可实现的最小 widgets 集合，并确保下钻一致。

**通用 widget 结构（API-009 返回）**：
```json
{
  "widget_id": "material_completeness_top_bottom",
  "title": "材料完整度TOP/Bottom",
  "sample_size": 60,
  "data": {"top": [], "bottom": []},
  "drilldown_filters": {"time_range": "last_30d", "system_id": "sys_1"}
}
```

**drilldown_filters → API-010 query 映射规则**：
- `time_range/start_at/end_at`：原样透传（对 completed/closed 按 frozen_at 落窗）。
- `system_id`：映射为 `system_id`（按 `final_estimation_days_by_system` 包含过滤）。
- `owner_id`：映射为 `owner_id`（按 `owner_snapshot.primary_owner_id` 过滤）。
- `expert_id`：映射为 `expert_id`（按参与专家过滤）。
- `ai_involved`：原样透传。

**页面（page）与最小 widgets 集合**：
1. `overview`
   - `task_completion_kpi`：完成量/进行中/待处理（完成口径按 frozen_at；未完成按 created_at）。
   - `ai_accuracy_kpi`：hit_rate/MAE/Bias（仅 ai_involved=true 且存在 final_estimation_days_total）。
2. `rankings`
   - `material_completeness_top_bottom`：按 `system_profile.completeness_score` 排序（可选过滤：窗口内参与过评估的系统）。
   - `system_remodel_workload_top`：按系统汇总 `final_estimation_days_by_system.sum(days)` Top10。
3. `ai`
   - `ai_hit_rate_trend`：按 week/month 聚合 hit_rate/MAE/Bias（口径见 `requirements.md 6.3`）。
   - `ai_accuracy_by_system_top_bottom`：按系统维度聚合 hit_rate/MAE/Bias（粒度 `(task_id, system_id)`）。
4. `system`
   - `system_remodel_count_top`：系统改造次数 Top10（见 `requirements.md 6.3` 定义）。
   - `system_remodel_workload_top`：系统改造工作量 Top10（人天）。
5. `flow`
   - `material_completeness_distribution`：完整度分布（0-20/21-40/41-70/71-100）+ 样本量。
   - `profile_stale_top`：`is_stale=true` 的系统Top10（用于提醒补齐画像）。

#### 4.3.9 报告生成与下载（SCN-012 / API-014）（关闭 OP-DES-006）
**目标**：对齐 `requirements.md` API-014（默认pdf；v2.0 仅支持 `pdf`，`docx` 预留），并兼容现有 Excel 报告下载。

**生成时机（设计决策）**：
- “最终确认/冻结”（见 4.3.6）时生成 **PDF** 作为对外报告主格式。
- 旧 Excel（`.xlsx`）作为兼容产物继续生成（对应历史接口 `/api/v1/requirement/report/{task_id}`），不作为 v2.0 API-014 的主返回格式。

**格式与实现建议**：
- PDF：使用 `backend/utils/pdf_report.py`（reportlab 可用则表格化渲染；不可用则最小PDF兜底）。
- DOCX：v2.0 不实现（预留参数）；对 `format=docx` 返回 `REPORT_002`（报表参数不合法：format）。

**版本与存储（MVP）**：
- 存储目录：`data/reports/`
- 任务字段：
  - `task.report_versions[]`：记录每次生成的报告版本（`id/format/file_path/generated_at/is_official`）
  - `task.report_path`：保留旧字段（Excel路径）用于兼容。
- 保留策略：每任务保留最近 5 个版本，超出删除最旧版本（避免磁盘膨胀）。

**下载行为**：
- `GET /api/v1/tasks/{task_id}/report?format=pdf`：返回 latest official PDF；若任务未完成/未生成返回 `REPORT_003`。
- 权限：admin 全局；PM=创建者；expert=参与任务（对齐 REQ-017/API-014）。

#### 4.3.10 内部检索与复杂度评估（SCN-004 / API-005 / API-006）
**目标**：为 AI 评估提供可复用的“检索+评分”能力：检索系统画像/能力/文档/ESB上下文（API-005），并输出三维度复杂度评分（API-006），避免实现期散落逻辑不一致。

**API-005：检索聚合策略（MVP 口径）**：
- 输入：`system_name` + `query` + `top_k`（默认 20）
- 输出四类结果：
  - `system_profile`：读取已发布画像（若不存在则为空）
  - `capabilities`：`knowledge_type=code`（建议 top_k<=20，阈值>=0.6）
  - `documents`：`knowledge_type=document AND level=normal`（建议 top_k<=10，阈值>=0.6）
  - `l0_documents`：`knowledge_type=document AND level=l0`（建议 top_k<=5，**排序降权**：score×0.3）
  - `esb_integrations`：`knowledge_type=esb`（建议 top_k<=10，阈值>=0.6）
- 合并规则：
  - 去重键：`(knowledge_id/source_id/chunk_id)`（以现有向量库实现为准）
  - 返回时按“类目内得分降序”排列，类目之间不强行打散（前端/Agent 可按需融合）

**降级策略**：
- 向量库/embedding 不可用：API-005 降级到关键词匹配（见 5.1），并返回 `degraded=true`（内部接口可返回该字段）；同时记录错误日志与 request_id，便于排障。

**API-006：三维度复杂度评分（MVP 口径）**：
- 输入：`feature_description` + 可选 `system_context`
  - 推荐 system_context 由 API-005 聚合结果生成（如：integration_points、capability_hits、esb_hits、doc_hits）
- 输出：`business_rules_score (0-35)`、`integration_score (0-35)`、`technical_difficulty_score (0-30)`、`complexity_score (0-100)`、`complexity_level (high/medium/low)` 与 `reasoning`
- 评分建议（可落地规则）：
  - business_rules_score：基于描述中识别的“规则/校验/分支/状态”数量与强度（由 LLM 结构化提取为 rules[] 后计分）
  - integration_score：基于集成点数量（从描述 + system_context 命中推断），0/1/2+ 分段计分
  - technical_difficulty_score：基于“并发/一致性/性能/安全/灰度/数据迁移”等技术关键词 + system_context 命中（由 LLM 输出 tech_risks[] 后计分）
  - complexity_level 映射（建议）：`0-40=low`，`41-70=medium`，`71-100=high`
- 可观测：API-006 需记录输入摘要（截断）与输出评分，便于回溯（避免落盘敏感原文）。

#### 4.3.11 专家差异统计与评估详情（SCN-006 / API-008 / SCN-010 / API-013）
**API-013：评估详情契约落地**：
- 路径：`GET /api/v1/tasks/{task_id}/evaluation`（对齐 requirements API-013）
- 权限：PM=任务创建者；expert=参与/被分配任务；admin/viewer 不提供写操作
- 关键点：features 返回需包含 `reasoning`（可选）与复杂度字段（对齐 API-006 输出结构），以支撑评估页展示与后续轨迹。

**API-008：专家差异统计（计算口径）**：
- 输入：`task_id`
- 数据来源：任务内的“专家估值”（按 feature 维度聚合）
- 输出：
  - by_feature：每个 feature 的 `ai_days`、`expert_mean_days`、`deviation_pct`、`direction`
  - summary：整体均值偏差、异常项数量、离散度提示（如标准差/离群点）
- 计算建议（与 requirements 口径一致）：
  - `expert_mean_days = mean(expert_days[])`
  - `deviation_pct = (expert_mean_days - ai_days) / max(ai_days, 0.1) * 100%`（避免除零；最终口径以 requirements 为准）
  - 异常阈值：`abs(deviation_pct) > 20%` 标记异常项（对齐关键决策与看板口径）
- 幂等与触发：
  - 计算接口可重复调用但结果应可复现（相同输入得到相同输出）
  - 推荐触发时机：当“全部专家提交”或“PM确认最终评估”后生成一次报告（也可随时重算）。

#### 4.3.12 通知中心（SCN-003/009/015 / API-017）
**目标**：为“画像AI总结→通知→采纳/忽略→可重试”链路提供稳定的用户触达与状态管理（对齐 `requirements.md` API-017）。

**核心约束**：
- 通知仅允许用户访问**自己的通知**（资源级权限：`notification.user_id == current_user.id`）
- 通知留存默认90天（可配置），避免 JSON 存储无限膨胀

**通知生成（内部调用）**：
- 画像AI总结成功：创建 `system_profile_summary_ready`
- 画像AI总结失败：创建 `system_profile_summary_failed`（payload 包含 `error_code/error_reason` + retry link）

**API 行为要点**：
- 列表查询：`GET /api/v1/notifications?page&page_size`
  - 仅返回本人通知，按 `created_at desc` 排序
  - 返回 `items/total/page/page_size`
- 未读数：`GET /api/v1/notifications/unread-count` 返回 `unread_count`
- 标记已读：
  - `PUT /api/v1/notifications/{notification_id}/read`（幂等）
  - `PUT /api/v1/notifications/read-all`（幂等）
- 清理：
  - `DELETE /api/v1/notifications/clear-read`：删除本人所有已读通知（幂等）
  - `DELETE /api/v1/notifications/{notification_id}`：删除单条（幂等：重复删除返回 404 或 success，口径以 requirements 为准）

**留存清理落地（无cron场景）**：
- 推荐采用“惰性清理”实现每日清理语义：在 `list/unread-count/mark-read/clear-read` 等入口触发清理
- 清理规则：删除“已读且 created_at < now - retention_days”的通知；保留未读
- 为避免每次请求全量清理，可在文件中额外保存 `meta.last_cleanup_at`（可选）；当天已清理则跳过

#### 4.3.13 评估任务创建（上传需求文档）（SCN-004 / API-016）
**目标**：支持 PM 上传需求文档创建评估任务，AI 在后台异步解析与评估；接口层仅负责校验/落盘与任务初始化（对齐 `requirements.md` API-016）。

**流程（建议）**：
1. PM 调用 `POST /api/v1/tasks`（`multipart/form-data`）上传文件 + 可选 `name/description`
2. 服务端校验：
   - 角色：仅 `manager`
   - 文件白名单：`.docx/.doc/.xls`（对齐 API-016；不在白名单返回 `TASK_002`）
   - 文件大小：默认 ≤10MB（可配置）；超限返回 `TASK_003`
3. 任务初始化：写入 `task_storage.json`（`workflow_status=draft`、`status=pending`、`ai_status=pending`），并持久化上传文件（`uploads/`；文件名清洗）
4. 后台异步执行：
   - 文档解析：`.docx` → 直接解析；`.doc/.xls` → 旧格式解析（必须满足 REQ-NF-007：最小权限/隔离目录/超时/清理）
   - `.xls` 语义：按“需求表格”抽取文本（全Sheet按顺序抽取可读单元格文本，不执行宏），抽取结果作为任务文本输入 AI 评估
   - 解析失败：任务标记失败并产出可定位错误信息；对外错误码以 `TASK_004` 为准
5. 前端提示：创建成功后跳转任务列表；用户可在任务详情查看进度/错误

### 4.4 API 设计（摘要表）
> 详细契约以 `docs/v2.0/requirements.md` 的 6.4 为准；本表用于实现侧核对鉴权、幂等与超时策略。

| API-ID | 方法 | 路径 | 鉴权 | 幂等 | 超时 | 备注 |
|---|---|---|---|---|---|---|
| API-001 | POST/GET | `/api/v1/code-scan/jobs` | PM（主责或B角） | 是 | 30min | 支持 repo_path / repo_archive |
| API-002 | POST | `/api/v1/code-scan/jobs/{job_id}/ingest` | PM（仅创建者） | 是 | 5min | embedding失败返回 `EMB_001` |
| API-003 | POST | `/api/v1/esb/imports` | PM（主责或B角） | 是 | 5min | 过滤无关行 |
| API-004 | CRUD | `/api/v1/system-profiles...` | 读：admin/PM/expert；草稿写：主责或B角；发布：仅主责 | - | 5s | admin/expert 只读；发布必填校验 |
| API-005 | POST | `/api/v1/internal/system-profiles/retrieve` | internal | 是 | 5s | 检索聚合（可返回 degraded） |
| API-006 | POST | `/api/v1/internal/complexity/evaluate` | internal | 是 | 10s | 三维度评分 |
| API-007 | POST | `/api/v1/tasks/{task_id}/modification-traces` | PM（仅任务创建者） | 否 | 5s | 服务端补齐原始推理 |
| API-008 | POST/GET | `/api/v1/internal/tasks/{task_id}/expert-deviations/compute` | internal | 是 | 10s | 另有 GET `/api/v1/tasks/{task_id}/expert-deviations` |
| API-009 | POST | `/api/v1/efficiency/dashboard/query` | admin/viewer/PM/expert | 是 | 5s | 按角色范围返回 |
| API-010 | GET | `/api/v1/tasks` | admin/viewer/PM/expert | 是 | 5s | 支持 group_by_status + 多筛选 |
| API-011 | POST | `/api/v1/knowledge/imports` | PM（绑定系统时需主责或B角） | 是 | 30s | 可选绑定 system_name/system_id |
| API-012 | GET | `/api/v1/system-profiles/completeness` | PM/expert | 是 | 5s | 建议补充 document_count（P2） |
| API-013 | GET | `/api/v1/tasks/{task_id}/evaluation` | PM/expert | 是 | 5s | 评估详情契约 |
| API-014 | GET | `/api/v1/tasks/{task_id}/report` | admin/PM/expert | 是 | 30s | expert 仅参与任务 |
| API-015 | GET/POST | `/api/v1/system-list/...` | admin | 是 | 30s | 可叠加 ADMIN_API_KEY |
| API-016 | POST | `/api/v1/tasks` | PM（manager） | 否 | 30s | `multipart/form-data` 上传；支持 `.docx/.doc/.xls`；满足 REQ-NF-007 |
| API-017 | GET/PUT/DELETE | `/api/v1/notifications...` | admin/PM/expert/viewer（仅本人） | 是 | 5s | 未读数/已读/清理；留存默认90天 |
| API-018 | POST | `/api/v1/system-profiles/{system_id}/ai-suggestions/retry` | PM（主责或B角） | 是 | 10s | 失败后手动重试；运行中返回当前 job_id |

### 4.5 配置与密钥（新增/确认）
| 配置项 | 默认 | 说明 |
|---|---|---|
| `DEBUG` | true | 生产环境必须为 false（影响管理接口保护） |
| `ADMIN_API_KEY` | "" | 可选：对系统清单导入叠加保护 |
| `JWT_SECRET` | change_me | 必须替换 |
| `REPORT_DIR` | data | 文件存储根目录 |
| `KNOWLEDGE_VECTOR_STORE` | local | local/milvus |
| `MAX_FILE_SIZE` | 10MB | API-016 上传文件大小上限（可配置） |
| `CODE_SCAN_REPO_ALLOWLIST` | "" | repo_path allowlist 前缀列表（逗号分隔） |
| `CODE_SCAN_ARCHIVE_MAX_BYTES` | 300MB | repo_archive 解压前大小上限（对齐代码实现） |
| `CODE_SCAN_ARCHIVE_MAX_FILES` | 20000 | repo_archive 解压后文件数上限（对齐代码实现） |
| `CODE_SCAN_ENABLE_GIT_URL` | false | 是否启用 Git URL 扫描（默认禁用） |
| `CODE_SCAN_GIT_ALLOWED_HOSTS` | "" | 允许的 Git host allowlist（逗号分隔） |
| `MOD_TRACE_RETENTION_DAYS` | 180 | 修改轨迹保留期 |
| `PROFILE_STALE_DAYS` | 30 | 画像过时阈值 |
| `NOTIFICATION_RETENTION_DAYS` | 90 | 通知留存天数（已读且超期自动清理；可配置） |
| `OLD_FORMAT_PARSE_TIMEOUT_SECONDS` | 60 | `.doc/.xls` 旧格式解析超时（满足 REQ-NF-007） |

## 5. 可靠性与可观测性

### 5.1 降级策略（补齐 P2）
当向量库/embedding 不可用时：
- **写入类**（导入/入库/发布）：直接失败并返回 `EMB_001`，保证“不写半条/不更新完整度”。
- **检索类**：降级到关键词匹配，并在响应中标记 `degraded=true`（内部接口可返回；对外接口按需要隐藏）。

关键词匹配规则（落地建议）：
- code_scan：对 `entry_id/path/method` 做包含匹配；按命中字段数排序。
- esb：对 `service_name/provider_system_id/consumer_system_id/scenario_code` 做包含匹配。
- documents/system_profile：对 `content` 片段做包含匹配，返回 top_k（按出现次数排序）。

### 5.2 日志与审计
- 每个请求生成 `request_id`（中间件）并写入日志。
- 审计日志（写操作）：系统清单导入、系统画像发布、代码扫描入库、ESB导入、知识导入、修改轨迹写入、报告下载。

## 6. 安全设计

### 6.1 认证与授权
**角色**：
- `admin`：系统清单导入；看板全局；画像只读；任务全局。
- `manager`（PM）：扫描/导入/画像写；任务（创建者 + 负责系统相关）范围。
- `expert`：参与任务范围内读取任务/报告；画像只读（按任务涉及系统）。
- `viewer`：仅看板与任务只读（全局）。**设计决策（已同步 requirements v1.17）**：viewer 视作“管理层只读”，默认全局可见；如需限制可后续加“数据域/部门”维度。

**资源级权限（关键点）**：
- 系统画像草稿写（保存草稿/采纳忽略/重试AI总结）：当 `system_list.owner_id == current_user.id` 或 `current_user.id ∈ system_list.backup_owner_ids`。
- 系统画像发布：仅当 `system_list.owner_id == current_user.id`（B角禁止发布）。
- ESB导入/代码扫描/知识导入绑定系统：同“草稿写”权限（主责或B角）。
- 系统画像读：
  - admin：全局
  - PM：主责或B角系统；或创建过涉及该系统的任务
  - expert：参与任务涉及的系统
  - viewer：禁止访问系统画像（按 requirements 权限测试口径）
- 报告下载：PM（自己创建）、expert（参与任务）、admin（全局）。
- 通知：仅本人通知（见 4.3.12 / API-017）。

### 6.2 高风险输入校验
- `repo_path`：
  - 若为本地路径：必须为绝对路径，且 realpath 命中 allowlist 根目录，否则 `SCAN_004`。
  - 若为 Git URL：仅允许 `https/http/ssh`，禁止 `file://` 等本地协议；无法访问返回 `SCAN_001`。
  - 禁止扫描根目录/系统目录（如 `/etc`、`/proc`），并限制扫描目录白名单。
- `repo_archive`：
  - 安全解压：禁止软链接/硬链接逃逸；限制解压后大小与文件数（对应 `SCAN_006`）。
- 文档导入：
  - 限制单文件大小；解析失败返回 `KNOW_002`；不落地原文档。

### 6.3 威胁与缓解（简表）
| 威胁/攻击面 | 风险 | 缓解措施 |
|---|---|---|
| repo_path 越权/路径穿越 | 读系统敏感文件 | allowlist + realpath 校验 + 禁止系统目录 |
| zip bomb | 磁盘/内存耗尽 | 解压后大小/文件数上限，流式解压与超时 |
| 越权访问系统画像/任务 | 数据泄露 | 资源级权限校验（system/task）+ 审计日志 |
| embedding/LLM 将敏感信息外发 | 合规风险 | 数据最小化、脱敏、可配置关闭外部服务、日志不落敏感原文 |

## 7. 性能与容量
### 7.1 性能目标
- 代码扫描：10万行 <10min（线程池并发≤5，超过排队）。
- 向量检索：10万条、top_k=20、P95<500ms（优先由 Milvus 满足；local 仅用于小规模）。

### 7.2 向量库容量上限与策略（关闭 OP-DES-003）
**关键约束**：本地向量库（JSON）存储完整 embedding（默认 1024 维）会导致文件快速膨胀，且检索为全量扫描。

设计决策：
- **local 适用规模**：建议 ≤20,000 条 knowledge entries（或 `knowledge_store.json` ≤200MB）；超过该规模建议启用 Milvus。
- **Milvus 适用规模**：≥20,000 条；目标覆盖 NF-002 的 100,000 条规模与 P95 目标。
- 保护策略（MVP，避免引入新错误码）：
  - 当 local 达到软上限时：写入类接口把新增条目计入 `failed` 并在 `errors[]` 中提示“容量达到上限，请启用 Milvus/清理数据”；不更新画像完整度（与 EMB_001 处理一致，保持一致性）。
  - L0 文档有天然上限：单文件切分上限 `MAX_UNSTRUCTURED_CHUNKS=200`（已存在），防止单次导入爆炸增长。

### 7.3 看板聚合缓存策略（关闭 OP-DES-004）
设计决策（MVP）：
- 当任务量 `task_storage.json` 记录数 > 2,000 或请求高频（同一筛选条件短时间重复请求）时，启用 **进程内 TTL cache**：
  - TTL：60s
  - key：`(user_id, roles, page, perspective, filters)`，避免跨用户数据串扰
  - 失效：当任务冻结（写入 frozen_at）或系统画像发布/导入完成后，主动清理相关 key（或全量清理，简单优先）
- 当任务量较小（≤2,000）时：默认不启用缓存，直接全量聚合，保证实现简单。

## 8. 兼容性、发布与回滚

### 8.1 测试与验收入口（Test Plan）
- 任务级验证与 DoD：见 `docs/v2.0/plan.md`
- 需求追溯与回归证据：见 `docs/v2.0/test_report.md`（REQ/REQ-NF → TEST 矩阵 + 性能验收证据）
- 发布前最小回归集（Deployment 复用）：见 `docs/v2.0/deployment.md` 的“验证部署”章节

### 8.2 向后兼容与回滚策略
- 数据：JSON schema 采用“补字段不删字段”，保证可回滚。
- 接口：保留旧路由并在内部转发到新实现；前端逐步切换到新契约。
- 回滚：通过开关禁用看板/画像写入（仅保留读取）并停止后台清理任务。

## 9. 风险与开放问题

### 9.1 风险清单
| 风险 | 影响 | 概率 | 应对措施 | Owner |
|---|---|---|---|---|
| 文件存储并发写入导致数据损坏 | 高 | 中 | 全部写操作使用 lock 文件；写入使用 tmp + os.replace 原子替换 | 开发 |
| repo_path 安全边界不严 | 高 | 中 | allowlist + realpath 校验 + 默认关闭非 allowlist 路径 | 开发 |
| 看板统计口径与任务数据不一致 | 中 | 中 | 冻结口径统一写入 `frozen_at/owner_snapshot`；加单元测试与回归用例 | 开发 |

### 9.2 已关闭问题（本次 Design 决策）
- 系统清单 owner 字段：采用 `extra.owner_id/owner_username` canonical keys，并支持中文别名映射（见 4.2.6）。
- Git URL 扫描：默认禁用，配置开启且 host allowlist 命中才允许（见 4.3.1）。
- 向量库容量：local 设定软上限并建议 Milvus 承载 10万规模（见 7.2）。
- 看板缓存：任务量>2,000 启用 TTL=60s 的进程内缓存（见 7.3）。
- 文件锁策略：优先 `fcntl.flock`，回退进程内锁；原子写 `tmp+replace`（见 4.2）。
- 报告生成：冻结时生成 PDF 为主；docx 预留（传入返回 `REPORT_002`）（见 4.3.9）。

## 10. 变更记录
| 版本 | 日期 | 说明 | 作者 |
|---|---|---|---|
| v0.1 | 2026-02-06 | 初始化：给出 v2.0 端到端可实现设计（含权限/存储/兼容/降级策略） | AI |
| v0.2 | 2026-02-06 | 根据设计审查修复：补齐widget catalog/下钻映射、冻结落点与幂等、repo_path本地/URL校验、mapping_json与导入约束、轨迹清理落地 | AI |
| v0.3 | 2026-02-06 | 修复 review_design 新增问题：关闭 owner_id/Git URL 决策；删除重复标题；补齐向量库容量上限、看板缓存阈值、文件锁策略与报告生成方案 | AI |
| v0.4 | 2026-02-07 | 与 requirements v1.7 同步：报告下载仅 PDF（docx 预留）；Viewer 决策同步说明；更新关联版本号 | AI |
| v0.5 | 2026-02-07 | 与 requirements v1.9 同步：更新需求编号（REQ-017~021→REQ-017~020）；删除冗余REQ-017（L0已在REQ-011中） | AI |
| v0.6 | 2026-02-07 | 修复开发就绪问题：补齐 SCN-004/006/010 与 API-005/006/008/013 设计；统一文档导入格式与 repo_archive 文件数默认阈值；补齐 Git URL 配置项与 API 摘要表覆盖 | AI |
| v0.7 | 2026-02-07 | 同步 requirements v1.11：收敛知识库导入格式口径（不支持 doc/xls/ppt 需预转换）并更新关联版本号 | AI |
| v0.8 | 2026-02-07 | 修复一致性：补齐“viewer 可下钻任务明细只读”在设计目标中的表述；补齐输入文档类型包含 txt；更新 viewer 同步到 requirements v1.11 的备注 | AI |
| v0.9 | 2026-02-07 | 同步 requirements v1.12：更新关联版本号（错误码口径修复不影响设计实现） | AI |
| v0.10 | 2026-02-07 | 同步 requirements v1.14（UI/UX补充）：菜单移除效果统计与顺序调整；系统画像拆页（知识导入/信息看板、TAB同步、不展示导入历史）；画像字段补齐7字段（business_goals别名兼容）；发布必填字段收敛为in_scope/core_functions | AI |
| v0.11 | 2026-02-07 | 修复 design v0.10 审查项：补齐 REQ-016 的前端落地口径（Modal/折叠/移除顶部说明）；明确 `/system-profiles` 旧路由兼容重定向；补齐 business_goals 读写归一化策略；补齐“最近一次扫描任务状态”最小反馈交互 | AI |
| v0.12 | 2026-02-07 | 同步 requirements v1.17：更新文档元信息与 Viewer 口径引用版本；确认设计与已实现代码一致（无新增架构变更） | AI |
| v0.13 | 2026-02-08 | 对齐模板：补齐摘要、需求-设计追溯矩阵、关键约束/假设与测试入口；更新元信息引用版本（不改变设计结论） | AI |
| v0.14 | 2026-02-08 | 需求确认后复核：修正导出策略内部决策标识（`OP-DES-106`），并完成 Design→Testing 追溯一致性复查（不改变架构/接口结论） | AI |
| v0.15 | 2026-02-09 | 对齐模板：补齐 Design 决策记录（技术决策/环境配置口径）；更新引用版本号（不改变架构/接口结论） | AI |
| v0.16 | 2026-02-09 | 对齐 CR-20260209-001：补齐 API-016/017/018 核心流程与 API 摘要表；修正权限口径（主责+B角草稿侧写/发布仅主责）；补齐通知留存与旧格式解析超时配置项 | AI |
