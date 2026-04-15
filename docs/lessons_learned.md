# Lessons Learned（经验教训沉淀）
> 目的：把"踩坑/返工/缺陷/事故/认知偏差"沉淀为可复用的规则与验证方式，减少返工与风险。
> 维护：每次出现返工/缺陷/事故/认知偏差后，由 AI 追加 1 条；高频/高风险项需要"升级"为规则/清单/自动化检查。

## 快速索引（硬规则 Top）
> 只保留最关键的 5–10 条，优先写"可执行、可验收"的规则，便于跨项目复用。

- **R1**（需求）：提案必须包含所有用户确认的决策点，不能遗漏
- **R2**（流程）：文档更新后必须自查"是否包含所有讨论内容"
- **R3**（需求）：用户对问题的回答必须结构化落盘并逐条体现在输出文档中（含 AskUserQuestion 等工具交互结果）
- **R4**（审查）：任何阶段宣称“已收敛/P0-P1=0”前，必须通过“三层门禁”（结构门禁 + 语义门禁 + 证据门禁）
- **R5**（需求）：Requirements 必须覆盖提案 In Scope 清单（每项落到 REQ/API/验收；若 Defer 必须回写提案并重新确认）
- **R6**（追溯）：任何 REQ 编号调整后，必须同步更新 `plan.md` 的"任务关联 REQ/覆盖矩阵"，并做一次"引用存在性"自检
- **R7**（实现）：开始任何实现前，必须建立TodoList，逐项勾选完成；完成后更新TodoList状态
- **R8**（前端质量）：页面级改动必须至少包含 1 条“首屏渲染不崩溃”测试；`no-use-before-define` 视为阻断项，不得以 warning 放行
- **R9**（配置）：必须明确区分“需求目标模型口径”“样例配置文件”“当前部署主机实际配置源”；跨阶段文档只允许一套 canonical 模型名
- **R10**（运行态验证）：修复缺陷后必须核对“工作区源码、运行中容器、已部署静态资源”三者一致；未验证运行态前，不得宣称“已修复可验收”
- **R11**（前端交互）：用户明确要求“不可改的交互形式”和“前端不该展示的信息”必须先整理成禁改清单；内部 ID/scene/status code/对象结构不得直接渲染到 UI，且发现 1 处同类问题后必须联排全页/全链路

---

## 条目列表

### 2026-04-15｜宿主机与容器读取不同模型配置源，导致“本地探针正常、运行态任务卡死”错觉（部署/运行态/配置漂移）
- **标签**：部署、运行态、配置、外部依赖
- **触发（事实）**：用户反馈“项目经理导入需求变更申请表后 AI 状态一直停在 20%”；现场排查发现宿主机 Python 进程读取的是 [`.env`](/home/admin/Claude/requirement-estimation-system/.env) 中的公网 `DASHSCOPE_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1`，而 `requirement-backend` 容器实际通过 `env_file: .env.backend` 读取到 `DASHSCOPE_API_BASE=http://10.73.254.200:30000/v1`、`LLM_MODEL=Qwen3-32B`、`EMBEDDING_MODEL=Qwen3-Embedding-8B`。结果是宿主机最小 LLM 探针可成功，但容器内系统识别请求直接 `ConnectTimeout`，任务长期停在 20%。
- **根因**：
  1. 文档里虽然写了“backend 配置源是 `.env.backend`”，但现场排查时先用了宿主机进程做 LLM 探针，未第一时间核对容器实际环境变量。
  2. `.env.backend` 中的内网模型网关 `10.73.254.200:30000/v1` 当前从容器内不可达，而公网 DashScope 兼容模式可达，形成“宿主机能通、容器不通”的假象。
  3. 内网模型名 `Qwen3-32B / Qwen3-Embedding-8B` 在公网 DashScope 兼容模式下不可用，不能只切 base URL，必须连同模型名一起切到 `qwen-turbo / text-embedding-v2` 或其他可用组合。
- **影响**：
  - 运行中 backend 任务会在系统识别或后续 embedding 相关步骤超时
  - 宿主机上的成功探针不能证明线上容器真实可用
  - 配置漂移会把“代码热点”和“外部依赖不可达”混成一个问题，增加排查成本
- **改进行动（可执行）**：
  1. 任何外部依赖探针都必须同时记录“宿主机配置源”和“容器运行时环境变量”，不得只测其一。
  2. Deployment/Hotfix 阶段遇到 LLM/embedding 超时时，先执行 `docker inspect <container> --format '{{json .Config.Env}}'`，确认容器真实 `DASHSCOPE_API_BASE / LLM_MODEL / EMBEDDING_*`。
  3. 若需要从内网网关切回公网兼容模式，必须成组校验 `base_url + chat model + embedding model`，不能只改其中一项。
  4. 对“当前任务必须立即恢复”的场景，可允许一次性覆写环境补跑单任务；但后续仍需通过标准重建发布让容器正式吃到新配置。
- **验证方式（可复现）**：
  - `docker inspect requirement-backend --format '{{json .Config.Env}}'`
  - `docker exec requirement-backend sh -lc '/app/.venv/bin/python - <<\"PY\" ... print(settings.DASHSCOPE_API_BASE, settings.LLM_MODEL, settings.EMBEDDING_MODEL) ... PY'`
  - 对 chat 模型与 embedding 模型分别做最小探针，且分别在宿主机与容器内执行
- **升级（规则/清单/自动化）**：是（建议后续把“宿主机配置源 vs 容器运行时配置源对照”纳入 Deployment 固定门禁）

### 2026-04-15｜Docker 显式 CMD 绕过 entrypoint 默认分支，导致生产环境实际退化为单 worker（部署/运行态/启动链路）
- **标签**：部署、运行态、性能、启动链路
- **触发（事实）**：业务反馈“系统比较卡，刷新后没反应”；现场排查发现 frontend 首页静态资源毫秒级返回，但 `requirement-backend` 一度 `unhealthy`，容器内 `curl http://localhost:443/api/v1/health` 超时，backend CPU 短时接近 `100%`。继续检查 `/proc/*/cmdline` 发现运行态只有单个 `uvicorn backend.app:app --host 0.0.0.0 --port 443` 进程，并没有实际带 `--workers 4`。
- **根因**：
  1. Dockerfile 已通过 `CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "443"]` 显式传参，导致 `entrypoint.sh` 中“无参数时才补 `--workers ${WORKERS:-4}`”的默认分支永远不会执行。
  2. 启动日志只打印了配置值 `WORKERS=4`，没有校验真实进程命令行，误让人以为生产环境已经是多 worker。
  3. 缺少对启动脚本的自动化回归，导致“配置看起来对、运行态实际不对”的问题长期未被发现。
- **影响**：
  - 同步 CPU/IO 请求会阻塞唯一 worker，表现为刷新卡死、healthcheck 超时、backend 被 Docker 判为 `unhealthy`
  - 页面刷新和后台导入互相影响，业务体验退化明显
- **改进行动（可执行）**：
  1. 对显式 `uvicorn` 启动命令做统一组装，自动补齐 `--workers`、`--log-level` 等生产默认参数
  2. 启动链路验证必须同时检查“日志声明”和“真实进程命令行/worker 数”
  3. 为 `entrypoint.sh` 增加可 source 的测试入口，至少覆盖“默认生产模式会补多 worker”和“显式 workers 不被覆盖”两类回归
- **验证方式（可复现）**：
  - `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_entrypoint_script.py`
  - `docker exec requirement-backend sh -lc 'for p in /proc/[0-9]*; do cmd=$(tr "\0" " " < "$p/cmdline" 2>/dev/null); case "$cmd" in *uvicorn*|*backend.app:app*) echo "$cmd"; esac; done'`
  - `docker logs --since 2m requirement-backend | rg "Started parent process|Started server process"`
  - `curl -s -o /dev/null -w 'total=%{time_total} code=%{http_code}\n' http://127.0.0.1:443/api/v1/health`
- **升级（规则/清单/自动化）**：是（建议后续把“启动参数/worker 数需核对真实进程命令行”纳入 Deployment 固定门禁）

### 2026-04-10｜画像产物默认目录回退错误，导致运行态文件落到仓库根目录（实现/配置/运行态）
- **标签**：实现、配置、运行态、目录治理
- **触发（事实）**：v2.8 验收阶段发现 `raw/`、`wiki/`、`output/` 系统级目录直接出现在工作区根目录，且子目录名混入 `sys_pay_*` 之类测试夹具 ID；同时 `runtime_executions.json` 中出现了与系统清单真实名称不一致的目录片段。
- **根因**：
  1. `ProfileArtifactService` 的 singleton root 解析把空配置直接做了 `abspath("")`，实际落到了当前工作目录，而不是预期的 `REPORT_DIR/system_profiles`
  2. 系统级 artifact 目录曾直接按 `system_id` 或旧三层目录命名，导致目录可读性差，也容易把测试夹具 ID 暴露到真实运行态目录
  3. 缺少“默认根目录 + 每系统工作区命名 + legacy 迁移”三件套回归测试
- **影响**：
  - 运行态产物污染仓库根目录，`git status` 噪声大
  - 用户无法从目录名直接识别对应系统
  - 历史 `path/raw_artifact_path` 与真实期望口径漂移
- **改进行动（可执行）**：
  1. 统一通过单一 helper 解析 system workspace root；空配置必须固定回退到 `data/system_profiles`
  2. 系统级目录默认使用 `sid_<short-system-id>__<system_name>`；仅在无法解析系统名称时回退 `system_id`
  3. 为 legacy `system_profiles.json`、`import_history.json`、`extraction_tasks.json` 与旧 artifact 路径提供迁移/兼容逻辑，并同步重写 `runtime_executions.json`
  4. 为工作区根目录产物补 `.gitignore` 保护，避免再次把运行态目录暴露为未跟踪文件
- **验证方式（可复现）**：
  - `python -m pytest -q tests/test_system_profile_repository.py tests/test_profile_storage_layout_v28.py tests/test_profile_artifact_service.py tests/test_system_profile_artifact_api.py`
  - 检查 `get_profile_artifact_service().root_dir` 是否等于 `data/system_profiles`
  - 检查工作区根目录不再出现系统级 `raw/wiki/output` 产物目录，且每系统产物进入 `sid_*__<system_name>/`
- **升级（规则/清单/自动化）**：是（建议后续把“默认运行态产物不得落到仓库根目录”纳入实现阶段固定门禁）

### 2026-04-10｜后端容器时区与宿主机不一致，且导入链路写入无时区时间戳，导致页面时间错位 8 小时（部署/运行态/时间治理）
- **标签**：部署、运行态、时间治理、前后端协同
- **触发（事实）**：知识导入页显示的“导入完成时间”与服务器时间相差 8 小时；现场核验发现宿主机为 `+0800 CST`，`requirement-backend` 容器为 `+0000 UTC`，导入历史与执行状态文件中的时间戳均为无时区 ISO 字符串。
- **根因**：
  1. Docker Compose 未为 backend 容器注入宿主机时区信息，容器默认运行在 `UTC`
  2. 后端导入链路使用 `datetime.now().isoformat()` / `datetime.utcnow().isoformat()` 写入裸时间字符串，前端 `new Date(value)` 无法区分“本地时间”还是“UTC 裸值”
  3. 修复后未同步考虑历史运行态文件，导致旧记录仍会在页面中持续显示错位时间
- **影响**：
  - 导入页、执行状态、运行态文件中的时间与宿主机不一致，用户误判导入是否刚完成
  - 新旧数据混用时，问题会表现为“有的记录对、有的记录不对”，排查成本高
- **改进行动（可执行）**：
  1. backend compose 必须显式设置 `TZ`，并挂载 `/etc/localtime`、`/etc/timezone`
  2. 用户可见或运行态追踪相关时间戳一律输出带 offset 的 ISO 字符串，例如 `2026-04-10T18:29:28.083300+08:00`
  3. 涉及时间比较的代码必须兼容 aware datetime，避免 naive/aware 混比报错
  4. 修复上线时，如已存在旧的无时区 UTC 裸时间记录，必须先备份再做一次定向回填
- **验证方式（可复现）**：
  - `date '+HOST=%Y-%m-%d %H:%M:%S %z %Z'`
  - `docker exec requirement-backend date '+CONTAINER=%Y-%m-%d %H:%M:%S %z %Z'`
  - 检查 `data/runtime_executions.json`、`data/extraction_tasks.json`、`data/system_profiles/*/source/imports/{history,extraction_task}.json` 中时间戳是否带 `+08:00`
  - `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_system_profile_import_api.py -k 'profile_import_success_returns_task_id_and_records_history or v27_profile_import_uses_runtime_and_execution_status_aliases'`
- **升级（规则/清单/自动化）**：是（建议后续把“backend 容器时间需与宿主机一致 + 用户可见时间戳必须带时区”纳入 Deployment 固定门禁）

### 2026-02-06｜提案阶段遗漏用户反馈（文档/流程）
- **标签**：文档、流程、需求
- **触发（事实）**：在v2.0提案编写过程中，用户通过多轮交互（AskUserQuestion）提供了大量决策信息，但初始提案未包含这些内容，用户指出"你问的问题和我的答复，你分析后放到提案里了吗？"
- **根因**：
  1. 过早将初始草稿视为"完成"，未将交互过程的结果系统化整理
  2. 缺少"交互→整理→验证"的闭环意识
  3. 没有在提交前自查"是否包含所有用户确认的决策"
- **影响**：
  - 文档不完整，用户需要反复提醒
  - 降低用户信任
  - 增加反复修改的时间成本
- **改进行动（可执行）**：
  1. **交互记录清单**：使用AskUserQuestion后，立即将问答结果整理成清单
  2. **完整性自查**：提交文档前，逐项检查是否包含所有用户确认的内容
  3. **变更版本记录**：每次补充内容后更新版本号（如v0.1→v0.2），并列出变更点
- **验证方式（可复现）**：
  - 提交任何文档前，问自己："用户在这次会话中确认的每一项，都在文档里了吗？"
  - 对比检查：列出用户的所有回答，逐一确认是否在文档中体现
- **升级（规则/清单/自动化）**：
  - 是：升级为 `CLAUDE.md` 核心原则："证据驱动、验证可复现"的具体执行细则
- **证据/关联**：v2.0提案从v0.1到v0.2的多次补充过程

---

### 2026-02-06｜需求细节遗漏（文档）
- **标签**：文档、需求
- **触发（事实）**：用户指出ESB字段、COSMIC混合方式等具体决策未在提案中详细说明
- **根因**：
  1. 只记录了"做什么"，没记录"具体怎么做"
  2. 用户的详细回答被简化为标题，细节丢失
- **影响**：提案不够具体，无法作为后续设计的依据
- **改进行动（可执行）**：
  1. 用户回答包含具体字段/参数/格式时，必须完整记录，不能简化
  2. 对于用户提出的"混合方式"等决策，需解释具体含义
- **验证方式（可复现）**：
  - 检查：是否所有"XXX包含哪些字段"类问题都有完整回答
- **升级（规则/清单/自动化）**：是

---

### 2026-02-06｜需求口径不一致引发验收/实现风险（指标/降级/权限/输入边界）
- **标签**：文档、需求、验收、安全
- **触发（事实）**：Requirements 审查发现同一概念在不同章节口径不一致（如 PM修正率分母冲突、embedding 服务不可用降级策略矛盾、本地 repo_path 安全边界缺失、资源级权限未落到 API 契约）。
- **根因**：
  1. 术语表/需求明细/指标/API 契约分散编写，缺少一致性校验
  2. 开放问题未在进入下一阶段前关闭，导致“默认行为”被各段落自行假设
- **影响**：
  - 实现与测试口径不一致，验收容易争议
  - 安全边界缺失可能引入越权/路径风险
- **改进行动（可执行）**：
  1. 指标类需求必须同页给出：公式、分母/分子定义、统计周期、取值范围、目标值
  2. 外部依赖/降级策略必须在需求阶段“一处定、处处用”（需求+API+错误码+验收）
  3. 高风险输入（如本地路径）必须明确输入边界（allowlist/校验/错误码）并给出备选路径（如上传包）
  4. 在进入 Design 前固定执行一致性检查命令（如 `rg -n "PM修正率|embedding服务不可用|repo_path|资源级权限" docs/<版本号>/requirements.md`）
- **验证方式（可复现）**：
  - 以一致性 `rg` 清单作为门禁：同一关键词在文件内出现多处时，逐处检查定义是否一致
- **升级（规则/清单/自动化）**：是（纳入 Requirements 阶段“自查清单”）

---

### 2026-02-07｜实现阶段未充分阅读文档导致返工（实现/流程）
- **标签**：实现、流程、文档、沟通
- **触发（事实）**：用户反馈多个实现问题：1)效能看板报404 2)系统清单有多余Tab 3)规则管理缺少快速设置 4)效能看板布局不对 5)菜单结构调整。AI在部分问题上质疑用户"文档有说吗"，但实际上proposal/requirements确实有相关描述。
- **根因**：
  1. **依赖搜索而非完整阅读**：用Grep搜索关键词（如"流程健康"）搜不到，就认为"文档没写"，但实际上proposal第188行明确写了
  2. **文档理解不系统**：proposal是高层概要，requirements是详细需求，两者存在gap。AI没有建立"proposal→requirements"的映射意识
  3. **质疑而非验证**：用户说"明明在proposal有提"时，AI的第一反应是"让我搜索"，而不是"让我完整阅读那一部分"
  4. **缺少TodoList追踪**：多问题并行时，没有系统化追踪完成状态，导致遗漏
- **影响**：
  - 增加返工次数，降低用户信任
  - 本可以一次性完成的工作变成多轮交互
  - 用户需要反复指出"文档里有写"
- **改进行动（可执行）**：
  1. **建立文档导航**：在proposal开头明确说明"本文档定位为高层概要，详细需求见requirements.md"，并建立问题→文档的索引映射
  2. **关键词变体搜索**：用户说"流程健康"时，搜"流程健康"OR"flow"OR"流程"；中英文都要搜
  3. **先读后做**：用户提到文档有写时，先Read相关章节，列出原文和行号，再讨论差异
  4. **TodoList强制**：任何多任务实现必须用TodoWrite工具建立任务列表，完成后勾选
  5. **差异确认流程**：发现proposal与requirements不一致时，列出两处原文请用户确认，不得自行假设
- **验证方式（可复现）**：
  - 文档阅读清单：实现前检查"是否已读proposal相关章节 + requirements对应REQ"
  - 差异核对：列出proposal.md行号 + requirements.md行号，请用户选择按哪个执行
  - TodoList完整性：所有用户提出的问题都列入TodoList，完成后全部勾选
- **升级（规则/清单/自动化）**：是（升级为R7/R8/R9）
- **证据/关联**：本次交互中关于效能看板、系统清单、规则管理、菜单结构的返工记录

---

### 2026-02-24｜Design 自审过度依赖“追溯门禁”导致漏检（审查/文档/验收）
- **标签**：审查、文档、验收、追溯
- **触发（事实）**：v2.2 的 Design 第 1 轮自审在 `review_design.md` 中给出“P0/P1 open=0、建议进入 Planning”的结论，但随后独立审查发现 5 个 P1（兼容跳转语义/备注数据模型/REQ-101 统一状态/ESB Search&Stats 契约/confirm 门禁判定），并引发设计文档返工（`design.md` v0.1→v0.2）。
- **根因**：
  1. **把“trace 覆盖通过”当成“设计已可落地”**：只验证了 REQ-ID 被提及，但未对照 GWT 的字面验收要求逐条检查“语义是否明确、是否可实现、是否可验证”。
  2. **自审偏差（自己写自己审）**：更容易用“我的意图”替代“文本是否无歧义”，对“仅提示/可选/二选一”等含糊表述不敏感。
  3. **缺少契约/存在性核验**：涉及新 API/新行为时，未核对现有代码是否已有对应契约，也未在 design 中补齐路径/参数/返回/权限，导致验收用例无法落地。
- **影响**：
  - 设计缺陷被推迟到后续阶段暴露，放大返工成本（plan/implementation/testing 补洞）
  - 容易造成实现口径漂移与验收争议（“你想的是 A，但文本能解释成 B”）
- **改进行动（可执行）**：
  1. Design 审查最小门槛拆成三段并强制落证据：
     - Trace gate：requirements→design 覆盖脚本通过
     - GWT 语义审查：重点覆盖 REQ-C / 兼容跳转 / 回滚 / “一次性提示”等高风险语义
     - Contract/Existence 审查：任何“需要后端支持”的能力必须在 design 写清 API 契约（路径/参数/返回/权限），并在仓库中 `rg` 核对是否已存在或明确为新增
  2. 审查中出现“可选/二选一/仅提示”等影响验收的表述，默认按 P1 处理，必须在进入 Implementation 前收敛为单一口径。
  3. 在 `review_design.md` 中声明 P1=0 前，必须列出已执行命令与关键输出（无证据不得宣称收敛）。
- **验证方式（可复现）**：
  - Trace：`bash -lc 'source .aicoding/scripts/lib/review_gate_common.sh && review_gate_validate_design_trace_coverage requirements docs/<版本号>/requirements.md design docs/<版本号>/design.md'`
  - 契约与语义自检（示例）：`rg -n "/reports/|/dashboard\\?page=|replace|一次性提示|confirm=true|include_deprecated|加载|空态|错误态|重试" docs/<版本号>/design.md`
- **升级（规则/清单/自动化）**：是（建议纳入 Design 阶段自审清单，并逐步脚本化“契约缺失/含糊表述”提示）
- **证据/关联**：`docs/v2.2/review_design.md` 第 2/3 轮、`docs/v2.2/design.md` v0.2

---

### 2026-02-24｜阶段审查“假收敛”通病：结构通过≠语义闭环≠证据可复现（跨阶段）
- **标签**：审查、流程、验收、证据
- **触发（事实）**：
  - v2.2 Design 自审阶段出现“trace 覆盖通过但语义/契约缺口”导致返工（见上条 Design 具体记录）。
  - 历史上也出现过“计划/测试证据断链”（如 plan 中引用不存在的测试文件）等同类问题：文档结构完整，但落地不可执行/不可复现。
- **根因**：
  1. **结构门禁替代了语义门禁**：文件/ID/矩阵存在 ≠ 验收可判定、契约可实现、失败路径可验证。
  2. **证据门禁缺失**：review 报告给结论但缺少“命令+关键输出+定位信息”，导致后续无法复盘与复现。
  3. **阶段间责任转移**：把“本阶段没写清”推给“下阶段实现/测试再补”，会在越往后成本越高的位置爆雷。
- **影响**：
  - 返工后移：问题从 Requirements/Design 延迟到 Implementation/Testing 才暴露，修复代价指数上升
  - 验收争议：同一段文本可解释为多种行为，导致“实现对了但验收不过/验收过了但行为不对”
- **改进行动（可执行）**：
  1. **所有阶段 review 统一按“三层门禁”出具证据**：
     - 结构门禁：产出物齐全、编号与追溯关系成立（例如 trace/引用存在性）
     - 语义门禁：按该阶段的验收粒度逐条判定“文本是否无歧义、是否可实现、是否可验证”（REQ-C/兼容/回滚/权限默认最高优先级）
     - 证据门禁：写明“我验证了什么、怎么验证、关键输出是什么”（命令/输出/文件定位）
  2. **把高风险点前移收敛**：凡涉及“兼容跳转语义 / 权限与越权 / 回滚 / 新增 API 契约 / REQ-C 禁止项”，不得留到后续阶段“再补”。
  3. **默认从最坏情况出发写清拒绝口径**：例如 confirm 门禁、include_deprecated 过滤、错误码与 HTTP 状态码，必须在设计/接口层写明。
- **验证方式（可复现）**（示例清单，按阶段选用）：
  - Trace：`bash -lc 'source .aicoding/scripts/lib/review_gate_common.sh && review_gate_validate_design_trace_coverage requirements docs/<版本号>/requirements.md design docs/<版本号>/design.md'`
  - 引用存在性（Planning）：`rg -o "REQ-[0-9]+" docs/<版本号>/plan.md | sort -u | wc -l`
  - 计划命令资产存在性（Implementation 前置）：`rg -o "tests/[^` ]+" docs/<版本号>/plan.md | while read f; do test -f \"$f\" || echo \"MISSING:$f\"; done`
- **升级（规则/清单/自动化）**：是（已升级为 Quick Index `R4`；建议后续将“证据门禁”固化到各阶段 `review_<stage>.md` 模板必填字段）

---

### 2026-02-25｜收口后新增优化未即时登记 CR，导致追溯风险（变更管理/可追溯）
- **标签**：变更管理、追溯、收口治理
- **触发（事实）**：项目进入收口后，用户连续提出“布局紧凑化、文案可读性、去折叠”等新增优化要求并已实现，但 `status.md/plan.md/test_report.md` 仍显示“无 CR”。
- **根因**：
  1. 把“收口阶段的小优化”误当成“无需 CR 的临时调整”。
  2. 代码先行、文档补记滞后，导致短时间内追溯链断档。
- **影响**：
  - 难以回答“这批改动是谁提的、范围是什么、怎么验收、如何回滚”。
  - 后续审查与发布时，diff-only 范围边界不清晰。
- **改进行动（可执行）**：
  1. 收口阶段出现新增需求时，先创建 `docs/<版本号>/cr/CR-*.md`，再改代码。
  2. 同步更新 `status.md` Active CR、`plan.md` 任务映射、`test_report.md` CR 证据（三联更新）。
  3. 每日结束前执行一次 CR 引用一致性检查。
- **验证方式（可复现）**：
  - `rg -n "CR-YYYYMMDD-[0-9]{3}" docs/<版本号>/status.md docs/<版本号>/plan.md docs/<版本号>/test_report.md docs/<版本号>/cr/*.md`
- **升级（规则/清单/自动化）**：是（建议在 pre-commit 增加“代码变更命中高风险前端页面但无 Active CR”提示）
- **证据/关联**：`docs/v2.2/cr/CR-20260225-001.md`，`docs/v2.2/status.md`，`docs/v2.2/plan.md`，`docs/v2.2/test_report.md`

---

### 2026-03-01｜导入页首屏渲染漏测导致线上页面打不开（实现/测试）
- **标签**：实现、测试、前端、门禁
- **触发（事实）**：`SystemProfileImportPage` 运行时报 `ReferenceError: Cannot access 'loadImportHistory' before initialization`，知识导入页首屏崩溃无法打开。
- **根因**：
  1. 页面重构后 `useEffect` 依赖了尚未初始化的 `const` 回调（TDZ 错误）。
  2. 测试覆盖偏结构和静态断言（布局一致性/通用组件），缺少页面首屏渲染 smoke。
  3. 评审阶段已出现 `no-use-before-define` warning，但被降级为 P2 建议未阻断。
- **影响**：
  - 页面首屏不可用，核心业务入口受阻。
  - 造成“已通过回归但运行态失败”的信任损耗。
- **改进行动（可执行）**：
  1. 页面级变更必须新增至少 1 条首屏渲染测试（render + waitFor，不抛异常）。
  2. 将前端 lint 纳入强门禁：`eslint --max-warnings=0`，禁止 warning 带病放行。
  3. 对 `no-use-before-define`、`no-undef`、`react-hooks/exhaustive-deps` 建立“默认 P1”处置规则。
- **验证方式（可复现）**：
  - `cd frontend && CI=true npm test -- --watchAll=false --runInBand src/__tests__/systemProfileImportPage.render.test.js`
  - `cd frontend && npm run lint:system-profile-import`
- **升级（规则/清单/自动化）**：是（已升级为 Quick Index `R8`）
- **证据/关联**：`frontend/src/pages/SystemProfileImportPage.js`，`frontend/src/__tests__/systemProfileImportPage.render.test.js`

---

### 2026-03-09｜模型口径与部署环境口径混写，导致跨阶段文档漂移并误导发布（需求/部署/配置）
- **标签**：需求、部署、配置、文档
- **触发（事实）**：v2.6 的 `CR/proposal` 中同时出现了 `Qwen3-32B` 与 `Qwen3-32B-local` 两种写法；后续 `requirements/design/plan/test_report/deployment` 又把 Embedding 从 `Qwen3-Embedding-8B` 漂移成 `Qwen3-Embedding`，并进一步把内网样例文件 `.env.backend*` 误当成这台外网服务器的默认发布配置源。
- **根因**：
  1. 同一需求在上游文档中存在两套模型命名，后续阶段没有先冻结 canonical 名称再落盘
  2. 下游文档编写时直接复用了 `.env.backend*` 的示例值，等于让样例文件反向定义了需求口径
  3. Deployment 文档没有明确区分“需求目标模型口径”“内网样例配置”“当前主机实际运行配置源”
  4. 缺少跨阶段一致性门禁，未对 `CR -> proposal -> requirements -> design -> plan -> test_report -> deployment -> .env.backend*` 做模型名与配置源的统一校验
- **影响**：
  - 文档链路内同一需求出现多套模型名，需求、设计、测试、部署无法保持单一真相源
  - 外网服务器被错误切到内网样例配置，造成部署口径与机器实际环境不符
- **改进行动（可执行）**：
  1. 在 Proposal 或 CR 固化一张“canonical 模型/配置口径表”，明确 `LLM_MODEL`、`EMBEDDING_MODEL`、配置源、适用环境
  2. 进入 Requirements/Design 前执行跨文件一致性检查：`rg -n "Qwen3-32B|Qwen3-32B-local|Qwen3-Embedding-8B|Qwen3-Embedding|\\.env\\.backend|docker-compose.yml" docs/<版本号> .env.backend*`
  3. Deployment 文档必须显式分开写“需求目标口径”和“当前部署主机实际运行配置”，不得混写
  4. 发布后除健康检查外，必须补一条应用内配置核验：`docker exec <container> /app/.venv/bin/python -c "from backend.config.config import settings; ..."`
- **验证方式（可复现）**：
  - `rg -n "Qwen3-32B|Qwen3-32B-local|Qwen3-Embedding-8B|Qwen3-Embedding" docs/v2.6 .env.backend .env.backend.example .env.backend.internal`
  - `docker exec requirement-backend /app/.venv/bin/python -c "from backend.config.config import settings; print(settings.DASHSCOPE_API_BASE); print(settings.LLM_MODEL); print(settings.EMBEDDING_MODEL)"`
  - `docker-compose config | rg -n "DASHSCOPE_API_KEY|ADMIN_API_KEY|JWT_SECRET|KNOWLEDGE_ENABLED|KNOWLEDGE_VECTOR_STORE"`
- **升级（规则/清单/自动化）**：是（已升级为 Quick Index `R9`，建议纳入 Proposal/Deployment 阶段门禁）
- **证据/关联**：`docs/v2.6/cr/CR-20260309-001.md`、`docs/v2.6/proposal.md`、`docs/v2.6/requirements.md`、`docs/v2.6/deployment.md`、`docs/部署记录.md`

---

### 2026-03-14｜只核对源码未核对运行态，导致“已修复”判断失真（实现/部署/验证）
- **标签**：实现、部署、验证、返工
- **触发（事实）**：本轮修复“贷款核算 D1 采纳新建议无反应”时，工作区源码已包含修复，但运行中的 `requirement-backend` 容器仍是旧镜像；同时前端页面虽已修改源码，但未重新确认已部署的静态资源是否更新，导致用户看到的实际系统行为与我口头描述不一致。
- **根因**：
  1. 把“本地代码已改”误当成“系统已生效”，没有显式区分工作区源码、容器内运行代码、浏览器实际加载的静态资源。
  2. 缺少修复后的三层核对：源码 diff、容器内关键实现、对外服务实际返回/静态文件 hash。
  3. 在用户已经连续指出问题未生效后，没有第一时间把调查重点切到运行态与部署链路。
- **影响**：
  - 错把“未部署/未加载新资源”当成“功能逻辑仍有问题”，增加无效排查和往返沟通成本。
  - 用户拿到“可以验证”的信号后却仍看到旧行为，直接损害信任。
- **改进行动（可执行）**：
  1. 缺陷修复完成后，必须同时核对三处：工作区源码、运行中容器文件、对外服务/静态资源。
  2. 后端问题至少执行：健康检查 + 容器内关键代码 grep + 一条最小接口或函数级回归验证。
  3. 前端问题至少执行：`eslint` + `npm run build` + 校验 Nginx/静态目录实际指向的新 bundle hash。
  4. 向用户回复“可验证”前，必须附上至少一条运行态证据，而不是只引用源码状态。
- **验证方式（可复现）**：
  - `docker exec requirement-backend sh -lc "grep -n '_resolve_v27_canonical_sub_field\\|current_canonical_payload\\[target_sub_field\\]\\|ai_suggestions_previous' /app/backend/service/system_profile_service.py"`
  - `curl -sf http://127.0.0.1:443/api/v1/health`
  - `cd frontend && npx eslint src/pages/SystemProfileBoardPage.js src/__tests__/systemProfileBoardPage.v27.test.js`
  - `cd frontend && npm run build`
  - `curl -sf http://127.0.0.1 | rg -o "main\\.[a-f0-9]+\\.(js|css)"`
- **升级（规则/清单/自动化）**：是（已升级为 Quick Index `R10`，建议纳入 Testing/Deployment 阶段“运行态一致性”门禁）
- **证据/关联**：`backend/service/system_profile_service.py`，`frontend/src/pages/SystemProfileBoardPage.js`，`frontend/src/__tests__/systemProfileBoardPage.v27.test.js`，`docker-compose.yml`

---

### 2026-03-14｜把后台实现视角带到前端，且未把用户交互边界当成硬约束，导致连续返工（前端/交互/验证）
- **标签**：前端、交互、验收、返工
- **触发（事实）**：本轮系统画像与知识导入改造中，用户连续指出以下问题：1）页面交互形式偏离上个版本，系统 TAB 和 5 个域 TAB 被大改；2）前端暴露了 `execution_id`、`scene`、原始状态码、来源、操作人、扩展信息、Memory 资产等后台信息；3）结构化建议对象直接渲染成 `[object Object]`；4）修复时只改单点，没有举一反三排查同类问题，导致多轮往返。
- **根因**：
  1. **以后端返回结构驱动前端展示**：直接按接口结构渲染，没有先做“用户可读”转换层，导致内部元数据和对象结构泄漏到页面。
  2. **没有把用户明确口径升级为禁改边界**：对“不要展示什么”“交互形式不能改”“保持上版体验”这类要求，没有在动手前整理成硬约束清单。
  3. **修点不修面**：发现一个展示缺陷后，没有立即联排同类页面、同类字段、同类建议渲染路径。
  4. **证据意识不足**：在真实导入文件、真实返回数据、真实运行态未充分核对时，先按推测做了实现和解释。
- **影响**：
  - 同一批问题被用户多次指出，造成明显返工和信任损耗。
  - 前端出现“反人类”展示，直接影响业务验收效率。
  - 局部修复掩盖了系统性问题，增加后续排查成本。
- **改进行动（可执行）**：
  1. **先列 UI 禁改清单再动手**：凡用户明确说“不可改/不要展示/保持上版”的内容，必须先整理成页面级 checklist，并在实现与自测时逐项核对。
  2. **前端统一做用户视角适配**：后端的 `execution_id`、`scene_id`、原始状态码、结构化 suggestion wrapper、来源元数据等，只能在适配后按用户可读文案展示，禁止直接 render。
  3. **发现 1 处同类问题后联排全页/全链路**：例如发现对象直出或内部字段泄漏时，立即全局检查导入页、历史区、结果区、详情页、建议区、事件区是否存在相同模式问题。
  4. **涉及导入/模板问题必须优先取真实证据**：优先保留并读取用户真实导入文件、真实接口返回、真实数据库/运行态结果，不以本地样例或记忆替代。
  5. **验收前补一轮“人类视角 smoke”**：至少从“普通业务用户是否看得懂、是否符合上版操作习惯、是否暴露后台概念”三个角度过一遍页面。
- **验证方式（可复现）**：
  - `rg -n "execution_id|scene_id|\\[object Object\\]|来源：|操作人|扩展信息|Memory 资产" frontend/src`
  - `cd frontend && CI=true npm test -- --watchAll=false --runInBand src/__tests__/systemProfileImportPage.render.test.js src/__tests__/systemProfileBoardPage.v27.test.js src/__tests__/navigationAndPageTitleRegression.test.js`
  - 人工检查：逐页确认“系统 TAB / 5 域 TAB 交互形式未偏离上版、页面不出现内部 ID/scene/status code/对象文本”
- **升级（规则/清单/自动化）**：是（已升级为 Quick Index `R11`，建议后续把“前端禁改清单 + 内部元数据泄漏扫描”纳入页面改动门禁）
- **证据/关联**：`frontend/src/pages/SystemProfileBoardPage.js`，`frontend/src/pages/SystemProfileImportPage.js`，`frontend/src/components/MainLayout.js`，`frontend/src/__tests__/systemProfileBoardPage.v27.test.js`，`frontend/src/__tests__/systemProfileImportPage.render.test.js`，`frontend/src/__tests__/navigationAndPageTitleRegression.test.js`
