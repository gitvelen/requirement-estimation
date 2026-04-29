# spec.md

<!-- CODESPEC:SPEC:READING -->
## 0. AI 阅读契约

- 本文件是需求阶段的权威文档；进入设计阶段时，不得默认依赖原始材料才能理解需求。
- 撰写本文时必须读取用户提供的原始材料；本文完成后，应把关键语义沉淀到正文，而不是要求后续阶段继续读原始材料。
- 原始材料只作为溯源证据；关键需求语义、边界、验收与约束必须写入本文正文。
- 若本文与原始材料冲突，以本文的“决策与来源”中已确认决策为准；未确认冲突必须停止并询问用户。
- 所有后续设计、工作项、测试用例必须能追溯到本文的 `REQ-*`、`ACC-*`、`VO-*`。

<!-- CODESPEC:SPEC:OVERVIEW -->
## 1. 需求概览

- change_goal: 本次变更用于修复待评估需求文档内 `txt` 附件无法解析的问题，并同步收口内网前端部署和安全扫描响应头配置。前端入口继续使用 `http://<前端IP>:8000`，该 HTTP 入口必须返回安全团队扫描需要的 HSTS 头，但前端服务不再启动或暴露 443。内网前端代理的后端地址改为由 `.env.frontend` 配置，避免每次手工修改 nginx 模板。
- success_standard: 上传含 `txt` 附件的需求文档后，附件文本能进入需求正文解析链路；发起评估页使用说明展示 `.docx格式`；`curl -I http://10.62.16.251:8000` 返回 200 且包含三项通用安全头和 `Strict-Transport-Security: max-age=16070400`；前端部署不暴露 443；后端 internal compose 不再挂载 `/etc/timezone`；`.env.frontend` 可配置前端代理后端地址。
- primary_users:
  - 项目经理
  - 内网部署执行人
  - 安全扫描复测人员
- in_scope:
  - 需求文档内嵌 `txt` 附件的文本解析与合并
  - 发起评估页上传说明文案调整
  - 内网前端 HTTP 8000 的安全响应头配置
  - 前端 443/SSL/HTTPS 部署路径移除
  - `.env.frontend` 驱动内网前端后端 upstream 渲染
  - `docker-compose.backend.internal.yml` 删除 `/etc/timezone` 只读挂载
- out_of_scope:
  - 不收窄后端任务上传接口对 `.doc/.xls` 的既有兼容能力
  - 不新增受信任 CA、浏览器根证书分发、域名体系或 HTTPS-only 访问方式
  - 不改变业务路由、权限、任务评估流程、数据模型或报告生成逻辑
  - 不追求固定 `Server`、`Date`、`ETag`、`Content-Length` 等运行时响应头值

<!-- CODESPEC:SPEC:SOURCES -->
## 2. 决策与来源

- source_refs:
  - docs/inputs/attachment-parsing-requirement.md#问题描述
  - docs/inputs/2026-04-29-vnext-deploy-and-attachment-request.md#intent
  - docs/inputs/2026-04-29-vnext-deploy-and-attachment-request.md#confirmed-decisions
  - docs/inputs/2026-04-29-vnext-deploy-and-attachment-request.md#acceptance-examples
- source_owner: human
- rigor_profile: standard
- normalization_note: 将用户提出的附件解析、页面文案、安全头、compose、前端 upstream 和 443 端口要求拆成可验收的独立 REQ/ACC/VO；同时记录“只改展示不破坏旧上传兼容”和“HTTP 8000 返回 HSTS 但不启动前端 443”的最终决策。
- approval_basis: 用户明确要求实施该计划，并补充确认 `curl -I http://10.62.16.251:8000` 返回 `Strict-Transport-Security: max-age=16070400` 即为安全团队可接受形态，同时确认前端部署目标是不启动 443 端口服务。

### 已确认决策

- decision_id: DEC-001
  source_refs:
    - docs/inputs/2026-04-29-vnext-deploy-and-attachment-request.md#confirmed-decisions
  decision: 发起评估页只调整展示文案，不在本轮收窄后端 `.doc/.xls` 上传兼容。
  rationale: 用户要求的是使用说明文案调整；后端兼容旧格式属于既有能力，收窄会带来破坏性风险。

- decision_id: DEC-002
  source_refs:
    - docs/inputs/2026-04-29-vnext-deploy-and-attachment-request.md#acceptance-examples
  decision: 内网前端 HTTP 8000 响应必须返回 `Strict-Transport-Security: max-age=16070400`，并继续返回 200，不做跳转。
  rationale: 安全团队扫描以 `curl -I http://10.62.16.251:8000` 为准；用户给出的可接受样例是 HTTP 200 加 HSTS 头。

- decision_id: DEC-003
  source_refs:
    - docs/inputs/2026-04-29-vnext-deploy-and-attachment-request.md#confirmed-decisions
  decision: 前端服务部署不再启动或暴露 443，移除前端 nginx/compose/部署脚本中的 443/SSL/HTTPS 证书路径。
  rationale: 用户明确目标是“不该启动443端口服务”，因此上一轮 HTTPS/443 复测入口设计不再适用。

- decision_id: DEC-004
  source_refs:
    - docs/inputs/2026-04-29-vnext-deploy-and-attachment-request.md#confirmed-decisions
  decision: 样例中的 `X-Content-Type-0ptions` 按标准头名 `X-Content-Type-Options` 实现。
  rationale: 数字 `0` 会形成错误头名，无法表达已有安全头语义；用户样例意图是保留 `nosniff` 安全头。

### 待澄清事项

- clarification_id: CLAR-001
  question: none
  impact_if_unresolved: none

<!-- CODESPEC:SPEC:SCENARIOS -->
## 3. 场景、流程与运行叙事

### 核心流程叙事

项目经理仍从发起评估页上传需求文档创建任务。页面对用户展示的格式说明收敛为“上传需求文档（.docx格式）”，但服务端不因此拒绝历史上已经兼容的 `.doc/.xls` 调用。后台解析主需求文档时，如果文档内部包含 `txt` 附件，系统应像处理已有 `docx/xlsx` 附件一样读取其中可用文本，并将该文本合并到需求正文解析链路；单个附件解析失败不能中断其他附件和主文档处理。

部署执行人在内网前端服务器上通过 `.env.frontend` 配置真实后端 upstream，例如 `FRONTEND_BACKEND_UPSTREAM=10.62.22.121:443`，执行前端部署脚本后，脚本渲染运行时 nginx 配置，不再要求人工把 `frontend/nginx.internal.conf` 中的 `requirement-backend` 改为 IP。前端容器只暴露 `8000:80`，不挂载 SSL 目录，不检查或生成证书，也不启动 443 监听。

安全复测人员对 `http://10.62.16.251:8000` 执行 `curl -I` 时，应看到 `HTTP/1.1 200 OK`，页面不被重定向，响应中同时包含 `X-XSS-Protection: 1; mode=block`、`X-Frame-Options: DENY`、`X-Content-Type-Options: nosniff` 和 `Strict-Transport-Security: max-age=16070400`。该头部组合用于满足当前扫描工具要求，不意味着本轮引入 HTTPS-only 或浏览器证书信任治理。

### 场景索引

- scenario_id: SCN-001
  actor: 项目经理
  trigger: 上传的需求文档内部包含 `txt` 附件
  behavior: 系统解析主文档并抽取 `txt` 附件文本，失败附件被隔离处理
  expected_outcome: 需求正文包含可读的 `txt` 附件内容，任务解析流程继续推进
  requirement_refs: [REQ-001]

- scenario_id: SCN-002
  actor: 项目经理
  trigger: 打开发起评估任务页面
  behavior: 页面使用说明展示新的 `.docx格式` 文案
  expected_outcome: 用户看到“上传需求文档（.docx格式）”，后端旧格式兼容不被破坏
  requirement_refs: [REQ-002]

- scenario_id: SCN-003
  actor: 安全扫描复测人员
  trigger: 执行 `curl -I http://10.62.16.251:8000`
  behavior: 内网前端 HTTP 入口返回 200 与安全扫描要求的响应头
  expected_outcome: 响应中出现 `Strict-Transport-Security: max-age=16070400` 和三项通用安全头
  requirement_refs: [REQ-003]

- scenario_id: SCN-004
  actor: 内网部署执行人
  trigger: 部署后端 internal compose 与前端 internal compose
  behavior: 后端不再挂载 `/etc/timezone`；前端只启动 8000，不启动 443
  expected_outcome: 后端容器仍可按 `TZ` 和 `/etc/localtime` 使用时区；前端容器端口中没有 `443->443/tcp`
  requirement_refs: [REQ-004, REQ-006]

- scenario_id: SCN-005
  actor: 内网部署执行人
  trigger: 需要把前端代理指向真实后端 IP
  behavior: 在 `.env.frontend` 配置 upstream 后运行部署脚本
  expected_outcome: 运行时 nginx 配置中的 `proxy_pass` 使用 `.env.frontend` 值，无需手工改 nginx 模板
  requirement_refs: [REQ-005]

<!-- CODESPEC:SPEC:REQUIREMENTS -->
## 4. 需求与验收

### 需求

- req_id: REQ-001
  summary: 需求文档内嵌附件解析必须新增支持 `txt`，并将可读文本纳入待评估需求正文；单个 `txt` 附件解析失败时不得中断主文档或其他附件解析。
  source_ref: docs/inputs/attachment-parsing-requirement.md#问题描述
  rationale: 项目经理上传的真实需求文档可能携带文本附件；附件缺失会导致功能点拆分和工作量估算遗漏。
  priority: P0

- req_id: REQ-002
  summary: 发起评估页使用说明必须将“上传需求文档（.docx / .doc / .xls 格式）”改为“上传需求文档（.docx格式）”，但本轮不得收窄后端既有 `.doc/.xls` 上传兼容。
  source_ref: docs/inputs/2026-04-29-vnext-deploy-and-attachment-request.md#intent
  rationale: 用户要求前端说明口径收敛为 `.docx`，同时已确认只改展示，不引入破坏性后端兼容变更。
  priority: P1

- req_id: REQ-003
  summary: 内网前端 HTTP 8000 入口必须在 `curl -I http://<前端IP>:8000` 响应中返回 `Strict-Transport-Security: max-age=16070400`，并保留 `X-XSS-Protection: 1; mode=block`、`X-Frame-Options: DENY`、`X-Content-Type-Options: nosniff`。
  source_ref: docs/inputs/2026-04-29-vnext-deploy-and-attachment-request.md#acceptance-examples
  rationale: 安全团队扫描以 HTTP 8000 入口为准，用户提供的可接受样例明确新增 HSTS 头即可通过。
  priority: P0

- req_id: REQ-004
  summary: `docker-compose.backend.internal.yml` 必须删除 `/etc/timezone:/etc/timezone:ro` 挂载，并保留不依赖该挂载的时区配置路径。
  source_ref: docs/inputs/2026-04-29-vnext-deploy-and-attachment-request.md#intent
  rationale: 用户明确要求删除该挂载，避免目标环境缺少 `/etc/timezone` 或挂载策略不一致影响后端部署。
  priority: P1

- req_id: REQ-005
  summary: 内网前端后端代理地址必须可通过 `.env.frontend` 配置，部署脚本应读取该配置并渲染运行时 nginx，不要求人工修改 `frontend/nginx.internal.conf` 模板中的 `requirement-backend`。
  source_ref: docs/inputs/2026-04-29-vnext-deploy-and-attachment-request.md#intent
  rationale: 当前每次部署都手工把 `requirement-backend` 改成 IP，容易出错且不可复用。
  priority: P0

- req_id: REQ-006
  summary: 内网前端部署不得启动或暴露 443 端口服务，并应移除前端部署链路中的 SSL 证书生成、SSL 目录挂载和 HTTPS 健康检查要求。
  source_ref: docs/inputs/2026-04-29-vnext-deploy-and-attachment-request.md#confirmed-decisions
  rationale: 用户明确补充前端服务部署时不该启动 443；继续保留 443 会与目标部署行为冲突。
  priority: P0

### 验收

- acc_id: ACC-001
  requirement_ref: REQ-001
  expected_outcome: 给定一个包含 `txt` 嵌入附件的 `.docx` 需求文档，解析结果的附件正文或合并需求正文中能看到 `txt` 内容；损坏附件不会阻断有效附件解析。
  priority: P0
  priority_rationale: 附件内容遗漏会直接导致功能点遗漏和估算失真。
  status: approved

- acc_id: ACC-002
  requirement_ref: REQ-002
  expected_outcome: 发起评估页使用说明展示“上传需求文档（.docx格式）”，且后端任务上传接口对 `.doc/.xls` 的既有兼容测试仍通过。
  priority: P1
  priority_rationale: 文案是用户可见修正，但不应影响核心上传兼容链路。
  status: approved

- acc_id: ACC-003
  requirement_ref: REQ-003
  expected_outcome: 内网前端 nginx 的 HTTP 80/宿主 8000 响应配置包含四项安全头，测试或运行态 `curl -I http://<front-ip>:8000` 形态为 200 且不跳转。
  priority: P0
  priority_rationale: 这是安全团队复测的直接判定入口。
  status: approved

- acc_id: ACC-004
  requirement_ref: REQ-004
  expected_outcome: `docker-compose.backend.internal.yml` 中不存在 `/etc/timezone:/etc/timezone:ro`，并保留 `TZ` 或 `/etc/localtime` 等不依赖该挂载的时区配置。
  priority: P1
  priority_rationale: 部署配置修正必须可静态验证，避免运行环境差异。
  status: approved

- acc_id: ACC-005
  requirement_ref: REQ-005
  expected_outcome: `.env.frontend` 示例包含 `FRONTEND_BACKEND_UPSTREAM`；部署脚本能从 `.env.frontend` 读取该值并渲染出对应 `proxy_pass http://<upstream>;`。
  priority: P0
  priority_rationale: upstream 配置错误会直接导致前端 API 代理不可用。
  status: approved

- acc_id: ACC-006
  requirement_ref: REQ-006
  expected_outcome: 内网前端 compose 不包含 `443:443` 暴露和 SSL 目录挂载；内网前端 nginx 不包含 `listen 443`；部署脚本不再执行证书生成、443 端口预检或 HTTPS 健康检查。
  priority: P0
  priority_rationale: 继续启动 443 与用户明确部署目标冲突，且会引入不必要的证书依赖。
  status: approved

### 验证义务

- vo_id: VO-001
  acceptance_ref: ACC-001
  verification_type: automated
  verification_profile: focused
  obligations:
    - 构造含 `txt` 嵌入附件的 `.docx` fixture 并验证解析结果包含附件文本
    - 覆盖无效附件隔离路径，确认有效附件仍被解析
  artifact_expectation: `python -m pytest tests/test_attachment_extraction.py tests/test_docx_parser.py -q`

- vo_id: VO-002
  acceptance_ref: ACC-002
  verification_type: automated
  verification_profile: focused
  obligations:
    - 验证发起评估页使用说明展示 `.docx格式`
    - 验证后端旧格式上传兼容测试仍通过
  artifact_expectation: `cd frontend && npm test -- --watchAll=false --runTestsByPath src/__tests__/uploadPage.targetSystem.test.js`；`python -m pytest tests/test_task_upload_legacy_doc_api.py -q`

- vo_id: VO-003
  acceptance_ref: ACC-003
  verification_type: automated
  verification_profile: focused
  obligations:
    - 静态验证 `frontend/nginx.internal.conf` 的 HTTP server 返回四项安全头
    - 验证配置不引入 HTTP 到 HTTPS 跳转要求
  artifact_expectation: `python -m pytest tests/test_frontend_nginx_upload_limit.py -q`

- vo_id: VO-004
  acceptance_ref: ACC-004
  verification_type: automated
  verification_profile: focused
  obligations:
    - 静态验证 backend internal compose 不再包含 `/etc/timezone` 挂载
    - 验证保留 `TZ` 或 `/etc/localtime` 时区配置路径
  artifact_expectation: `python -m pytest tests/test_backend_config_env_files.py -q`

- vo_id: VO-005
  acceptance_ref: ACC-005
  verification_type: automated
  verification_profile: focused
  obligations:
    - 验证 `.env.frontend.example` 包含 `FRONTEND_BACKEND_UPSTREAM`
    - 验证部署脚本优先读取 `.env.frontend` 并渲染运行时 nginx upstream
  artifact_expectation: `python -m pytest tests/test_deploy_frontend_internal_script.py -q`

- vo_id: VO-006
  acceptance_ref: ACC-006
  verification_type: automated
  verification_profile: focused
  obligations:
    - 静态验证前端 internal compose 不暴露 443 且不挂载 SSL 目录
    - 静态验证前端 internal nginx 不监听 443
    - 静态验证部署脚本不再执行证书生成、443 端口预检或 HTTPS 检查
  artifact_expectation: `python -m pytest tests/test_frontend_nginx_upload_limit.py tests/test_deploy_frontend_internal_script.py -q`

<!-- CODESPEC:SPEC:CONSTRAINTS -->
## 5. 运行约束

- environment_constraints:
  - 内网前端部署入口保持 `http://<front-ip>:8000`。
  - `.env.frontend` 是前端 upstream 配置的目标文件；允许脚本兼容 `.env.frontend.internal` 作为旧部署回退。
  - 后端 internal compose 不再依赖宿主机 `/etc/timezone` 文件存在。
- security_constraints:
  - HTTP 8000 响应头必须包含 `Strict-Transport-Security: max-age=16070400`、`X-XSS-Protection: 1; mode=block`、`X-Frame-Options: DENY`、`X-Content-Type-Options: nosniff`。
  - `X-Content-Type-Options` 必须使用标准头名，不能写成带数字 `0` 的变体。
  - 本轮不新增其他安全头策略，也不改变鉴权或跨域策略。
- reliability_constraints:
  - 单个内嵌附件解析失败时必须继续处理主文档和其他附件。
  - 前端部署脚本在 upstream 缺失或非法时应失败并提示配置 `.env.frontend`，不能生成不可用代理配置。
- performance_constraints:
  - 继续沿用现有附件解析深度、大小和数量限制；本轮不扩大容量上限。
- compatibility_constraints:
  - 不改变后端 `.doc/.xls` 上传兼容能力。
  - 不启动前端 443，不要求证书材料，不做 8000 到 HTTPS 的跳转。
  - 不修改 release 包和本地运行时生成文件作为本轮交付来源。

<!-- CODESPEC:SPEC:BUSINESS_CONTRACT -->
## 6. 业务契约

- terminology:
  - term: 待评估需求文档附件
    definition: 项目经理上传的主需求文档内部携带的嵌入文件，本轮新增关注 `txt`，并保持既有 `docx/xlsx` 等附件解析能力。
  - term: 内网前端 HTTP 入口
    definition: 由前端 nginx 容器对宿主机暴露的 `8000:80` 入口，是本轮安全扫描和人工复测的目标入口。
  - term: 前端 upstream
    definition: 前端 nginx `/api/` 代理使用的后端服务地址，由 `FRONTEND_BACKEND_UPSTREAM` 提供，格式为 `<host>:<port>`。
- invariants:
  - 项目经理上传任务的主流程不能因为单个附件解析失败而整体失败。
  - 前端部署完成后，前端容器不应暴露 443。
  - `frontend/nginx.internal.conf` 作为模板保留占位式后端名，实际 IP 由部署脚本渲染到运行时配置。
- prohibitions:
  - 禁止以实现本轮安全头为由强制启用 HTTPS-only 或 8000 跳转。
  - 禁止把用户样例中的错误头名 `X-Content-Type-0ptions` 写入正式配置。
  - 禁止删除或弱化既有 `.doc/.xls` 后端上传兼容能力。

<!-- CODESPEC:SPEC:HANDOFF -->
## 7. 设计交接

- design_must_address:
  - `txt` 类型识别、编码解码策略、二进制误判防护，以及附件失败隔离。
  - HTTP 8000 安全头落在哪个 nginx server/location，确保首页与静态资源都能返回。
  - 前端 443/SSL/证书逻辑删除范围，避免 compose、nginx、部署脚本或测试残留互相矛盾。
  - `.env.frontend` upstream 读取优先级、渲染方式和非法配置失败路径。
  - `docker-compose.backend.internal.yml` 删除 `/etc/timezone` 后的时区配置保留方式。
- narrative_handoff:
  - 设计阶段必须把“前端不启动 443，但 HTTP 8000 仍返回 HSTS 头用于扫描”的取舍写清楚。
  - 设计阶段必须列出唯一 work item 的 allowed_paths，避免实现阶段越界修改 release 包或运行时生成文件。
- suggested_slices:
  - WI-001 覆盖附件解析、前端文案、nginx/compose/部署脚本和对应测试。
- reopen_triggers:
  - 如果安全团队改为要求真正 HTTPS HSTS 语义或要求 8000 跳转 HTTPS，必须回到需求阶段重定。
  - 如果 `txt` 附件来自 OLE Native 封装而不能通过简单文件名/内容推断可靠恢复，必须回到需求阶段重新界定样本和解析策略。
  - 如果需要收窄 `.doc/.xls` 上传兼容，必须回到需求阶段确认破坏性变更。
