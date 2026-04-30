# design.md

<!-- CODESPEC:DESIGN:READING -->
## 0. AI 阅读契约

- 本文件与 `work-items/*.yaml` 是 Implementation 阶段的默认权威输入。
- 实现阶段默认不读取原始材料；只有需求冲突、设计无法解释实现、或需要重开时才回读 `spec.md` / 原始材料。
- 所有架构决策、模块、接口、页面、数据结构、外部交互、测试策略和工作项必须追溯到 `REQ-*`、`ACC-*`、`VO-*`、`TC-*`。
- 若实现需要越出本文或当前 WI 的边界，必须停止并回写设计或需求，不得隐性扩 scope。

<!-- CODESPEC:DESIGN:OVERVIEW -->
## 1. 设计概览

- solution_summary: 本轮采用单个垂直 WI 完成附件解析、上传页文案、nginx/compose/部署脚本和测试收口。后端文档解析器新增 `txt` 类型解析，附件提取器把 `.txt` 后缀或可识别文本负载交给统一解析回调。后端内网镜像显式提供 `soffice`，保证既有 `.doc` 旧格式解析能力在部署环境中可用。内网前端保留 HTTP 8000 作为唯一前端入口，HTTP 响应直接返回 HSTS 与三项通用安全头，同时移除前端 443/SSL/HTTPS 启动链路。
- minimum_viable_design: 需求集中在既有上传解析链路与内网部署配置，没有新增业务数据模型或公开 API；直接扩展现有解析器、nginx 模板和部署脚本是最小改动。将 upstream 配置读取放在现有 `deploy-frontend-internal.sh` 渲染步骤内，可以复用已有 runtime nginx 生成方式。
- non_goals:
  - 不新增 HTTPS 入口、证书生成、证书挂载或浏览器信任链治理。
  - 不改变后端任务上传接口对 `.doc/.xls` 的既有兼容行为。
  - 不改 release 包、运行时生成配置或本地环境文件作为交付来源。

<!-- CODESPEC:DESIGN:TRACE -->
## 2. 需求追溯

- requirement_ref: REQ-001
  acceptance_refs: [ACC-001]
  verification_refs: [VO-001]
  test_case_refs: [TC-ACC-001-01]
  design_response: 在 `DocumentParser` 中新增 `_parse_txt`，并把 `txt` 加入支持类型；在 `EmbeddedAttachmentExtractor` 中把 `txt` 纳入类型推断和回调解析，解析失败记录到既有 `attachment_errors`。

- requirement_ref: REQ-002
  acceptance_refs: [ACC-002]
  verification_refs: [VO-002]
  test_case_refs: [TC-ACC-002-01]
  design_response: 只修改 `UploadPage` 中的展示文案，不改上传白名单和后端校验；后端内网镜像安装 LibreOffice Writer 并校验 `soffice` 可用，支撑既有 `.doc` 旧格式转换；前端测试断言新文案，后端旧格式测试和镜像依赖静态测试作为兼容回归。

- requirement_ref: REQ-003
  acceptance_refs: [ACC-003]
  verification_refs: [VO-003]
  test_case_refs: [TC-ACC-003-01]
  design_response: 在 `frontend/nginx.internal.conf` 的 HTTP server 和静态资源 location 增加 HSTS 头；保留 200 响应与现有 HTTP 入口，不添加跳转。

- requirement_ref: REQ-004
  acceptance_refs: [ACC-004]
  verification_refs: [VO-004]
  test_case_refs: [TC-ACC-004-01]
  design_response: 删除 `docker-compose.backend.internal.yml` 的 `/etc/timezone` 挂载，保留 `/etc/localtime` 和 `TZ=${TZ:-Asia/Shanghai}`。

- requirement_ref: REQ-005
  acceptance_refs: [ACC-005]
  verification_refs: [VO-005]
  test_case_refs: [TC-ACC-005-01]
  design_response: 更新 `.env.frontend.example` 增加 `FRONTEND_BACKEND_UPSTREAM`；部署脚本按环境变量、`.env.frontend`、`.env.frontend.internal`、nginx 模板的顺序解析 upstream，并继续渲染 runtime nginx。

- requirement_ref: REQ-006
  acceptance_refs: [ACC-006]
  verification_refs: [VO-006]
  test_case_refs: [TC-ACC-006-01]
  design_response: 删除内网前端 nginx 的 443 server，删除 compose 的 `443:443` 和 SSL 目录挂载，删除部署脚本中的证书生成、443 端口预检与 HTTPS 健康检查。

<!-- CODESPEC:DESIGN:DECISIONS -->
## 3. 架构决策

- decision_id: ADR-001
  requirement_refs: [REQ-001]
  decision: 在既有 `DocumentParser` / `EmbeddedAttachmentExtractor` 内扩展 `txt` 类型，而不是新增独立附件解析服务。
  alternatives_considered:
    - 新增专用 txt 附件服务；放弃原因是当前附件提取已有递归、大小和错误隔离框架，新增服务会重复边界控制。
    - 在 `DocxParser` 中特殊处理 txt；放弃原因是系统画像、知识导入等路径也复用 `DocumentParser`，类型支持应沉到通用解析层。
  rationale: 复用现有 parse callback 可让 `txt` 附件自动进入已有递归、去重和错误收集机制。
  consequences:
    - 需要用编码尝试和文本比例校验降低二进制误判风险。
    - `DocxParser` 无需理解附件类型，只继续合并 `attachments[].text`。

- decision_id: ADR-002
  requirement_refs: [REQ-003, REQ-006]
  decision: 仅保留 HTTP 8000 前端入口，并在该 HTTP 响应上返回 HSTS 头；完全移除前端 443/SSL 启动链路。
  alternatives_considered:
    - 保留 443 仅不暴露宿主端口；放弃原因是仍会在容器内启动 443 服务并保留证书依赖。
    - 保留上一版 HTTPS/HSTS 复测入口；放弃原因是用户明确要求前端不该启动 443。
  rationale: 用户给出的安全扫描验收样例以 `curl -I http://10.62.16.251:8000` 为准，且要求不启动 443。
  consequences:
    - HSTS 头在 HTTP 响应中只满足当前扫描工具头部检查，不代表浏览器标准 HSTS 生效路径。
    - 后续如果安全团队要求真实 HTTPS HSTS 语义，必须重开需求和设计。

- decision_id: ADR-003
  requirement_refs: [REQ-005]
  decision: upstream 继续通过部署脚本渲染 runtime nginx，配置来源新增 `.env.frontend`。
  alternatives_considered:
    - 在 nginx 模板中直接使用环境变量；放弃原因是默认 nginx 不会自动展开配置文件变量，仍需 entrypoint 或模板渲染。
    - 要求部署人员继续手工改 nginx；放弃原因是这正是本轮要消除的易错点。
  rationale: 现有部署脚本已经有 runtime nginx 渲染机制，扩展读取来源最小且可测试。
  consequences:
    - `.env.frontend` 中 upstream 缺失或非法时脚本必须明确失败。
    - `.env.frontend.internal` 仅作为旧部署回退，避免迁移期断裂。

### 技术栈选择

- runtime: Python 3.10 / FastAPI 后端，React 18 / Ant Design 前端，nginx 前端静态服务。
- storage: 文件系统配置与上传目录；本轮不新增数据库、缓存或迁移。
- external_dependencies:
  - Docker Compose 用于 internal 部署。
  - nginx 用于前端静态资源和 `/api/` 代理。
  - LibreOffice `soffice` 用于后端 `.doc` 旧格式文档转文本。
  - Python 标准库文本解码能力用于 `txt` 解析。
- tooling:
  - pytest 覆盖后端解析、nginx 配置和部署脚本。
  - react-scripts test 覆盖上传页文案。

<!-- CODESPEC:DESIGN:STRUCTURE -->
## 4. 系统结构

- system_context: 项目经理上传需求文档后，后端 `DocxParser` 调用通用 `DocumentParser` 抽取内嵌附件并合并正文；内网前端由 nginx 暴露 `8000:80`，并把 `/api/` 代理到后端 upstream。
- impacted_surfaces:
  - `backend/service/document_parser.py`
  - `backend/utils/embedded_attachment_extractor.py`
  - `frontend/src/pages/UploadPage.js`
  - `frontend/nginx.internal.conf`
  - `Dockerfile.internal`
  - `docker-compose.frontend.internal.yml`
  - `docker-compose.backend.internal.yml`
  - `deploy-frontend-internal.sh`
  - `.env.frontend.example`
  - 相关 pytest 与前端测试
- unchanged_surfaces:
  - 任务创建 API、鉴权、角色权限、任务状态机、报告生成逻辑保持不变。
  - `frontend/nginx.conf` 和 `frontend/nginx-remote.conf` 不新增 HSTS 或 443 变更。
  - 本地 `.env.frontend` 不纳入仓库修改。
- data_flow:
  - 上传文档字节进入 `DocumentParser.parse`，主文档中的 `word/embeddings/*` 被 `EmbeddedAttachmentExtractor` 遍历；`.txt` 附件通过类型推断进入 `_parse_txt`，输出 `{"text": ...}` 后被 flatten 并加入 `attachments`。
  - 前端部署脚本解析 `FRONTEND_BACKEND_UPSTREAM`，生成 `frontend/nginx.internal.runtime.conf`，compose 挂载该 runtime 配置到 nginx 容器。
  - HTTP 请求进入 nginx 80 server，首页/静态资源返回安全头，`/api/` 继续代理到后端且不在代理块重复注入后端已有通用安全头。
- external_interactions:
  - name: 安全扫描工具
    direction: inbound
    protocol: HTTP
    failure_handling: 若 `curl -I http://<front-ip>:8000` 缺少任一安全头或返回跳转，视为部署验证失败。
  - name: 后端服务 upstream
    direction: outbound
    protocol: HTTP
    failure_handling: upstream 缺失、仍为 `requirement-backend` 或包含空格时，部署脚本停止并提示配置 `.env.frontend`。

<!-- CODESPEC:DESIGN:CONTRACTS -->
## 5. 契约设计

- api_contracts:
  - contract_ref: none
    requirement_refs: [REQ-001, REQ-002]
    summary: 不新增或修改公开 API；任务上传接口的 `.doc/.xls` 兼容行为保持原状。
- data_contracts:
  - contract_ref: none
    requirement_refs: [REQ-001]
    summary: `DocumentParser` 对 `txt` 返回 `{"text": "<decoded text>"}`，由既有 `_flatten_to_text` 合并到附件正文；不新增持久化字段。
  - contract_ref: none
    requirement_refs: [REQ-005]
    summary: `.env.frontend.example` 新增 `FRONTEND_BACKEND_UPSTREAM=<host>:<port>`，部署脚本将其标准化为无 scheme、无尾部斜杠的 upstream。
- compatibility_policy:
  - 后端上传白名单和旧格式解析保持不变。
  - 前端部署从支持 80/443 双入口收敛为仅 80；所有证书相关配置从前端部署链路移除。
  - `.env.frontend.internal` 作为回退读取，降低旧部署文件迁移风险。

<!-- CODESPEC:DESIGN:CROSS_CUTTING -->
## 6. 横切设计

- environment_config:
  - `Dockerfile.internal` 基于 Debian 内网基础镜像安装 `libreoffice-writer`，并在构建期执行 `command -v soffice` 作为旧格式解析依赖检查。
  - `.env.frontend` 可配置 `FRONTEND_BACKEND_UPSTREAM=10.62.22.121:443`。
  - `docker-compose.frontend.internal.yml` 只暴露 `8000:80`，不再要求 `FRONTEND_SSL_DIR`。
  - `docker-compose.backend.internal.yml` 保留 `TZ=${TZ:-Asia/Shanghai}` 和 `/etc/localtime:/etc/localtime:ro`。
- security_design:
  - HTTP 80 server 统一返回 `Strict-Transport-Security: max-age=16070400` 与三项通用安全头。
  - `/api/` 代理块不重复追加后端已经返回的三项通用安全头，避免代理层与后端头值冲突。
  - 文本附件解析使用大小/数量/递归深度既有边界，并通过解码失败隔离避免单附件拖垮任务。
- reliability_design:
  - `.doc` 旧格式解析继续通过 `soffice` 在隔离临时目录内转换；缺失 `soffice` 属于部署镜像缺陷，应在镜像构建期暴露，而不是等任务后台解析失败。
  - `txt` 解码按 `utf-8-sig`、`utf-8`、`gb18030`、`gbk` 顺序尝试；全部失败或文本质量过低时抛出解析错误并进入附件错误记录。
  - 部署脚本在 upstream 缺失、非法或仍为容器名时失败，避免生成不可用 runtime nginx。
  - 移除 HTTPS 检查后，部署验证只检查 HTTP 8000 和容器内 `nginx -t`。
- observability_design:
  - 文档解析继续沿用现有 logger 记录解析成功数量和附件错误。
  - 部署脚本输出解析出的后端代理目标和 HTTP 服务验证结果，作为现场排障证据。
- performance_design:
  - 继续沿用现有附件递归深度、单附件大小和附件数量限制；`txt` 解码为内存内操作，不新增异步队列或外部服务。

<!-- CODESPEC:DESIGN:WORK_ITEMS -->
## 7. 工作项与验证

### 工作项映射

- wi_id: WI-001
  requirement_refs: [REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-006]
  acceptance_refs: [ACC-001, ACC-002, ACC-003, ACC-004, ACC-005, ACC-006]
  verification_refs: [VO-001, VO-002, VO-003, VO-004, VO-005, VO-006]
  test_case_refs: [TC-ACC-001-01, TC-ACC-002-01, TC-ACC-003-01, TC-ACC-004-01, TC-ACC-005-01, TC-ACC-006-01]
  summary: 单一垂直切片，完成 txt 附件解析、上传页文案、HTTP 安全头、前端 443 移除、compose 和 upstream 配置。

### 工作项派生

- wi_id: WI-001
  requirement_refs:
    - REQ-001
    - REQ-002
    - REQ-003
    - REQ-004
    - REQ-005
    - REQ-006
  goal: 交付 vNext 附件解析与内网部署修正，使 txt 附件可解析、上传页文案收敛、HTTP 8000 安全头满足扫描、前端不启动 443、后端 compose 和 upstream 配置符合新部署口径。
  covered_acceptance_refs: [ACC-001, ACC-002, ACC-003, ACC-004, ACC-005, ACC-006]
  verification_refs:
    - VO-001
    - VO-002
    - VO-003
    - VO-004
    - VO-005
    - VO-006
  test_case_refs:
    - TC-ACC-001-01
    - TC-ACC-002-01
    - TC-ACC-003-01
    - TC-ACC-004-01
    - TC-ACC-005-01
    - TC-ACC-006-01
  dependency_refs: []
  dependency_type: none
  contract_refs: []
  notes_on_boundary: 允许修改解析器、上传页、internal nginx/compose/Dockerfile/部署脚本、env 示例和对应测试；禁止改业务 API 语义、release 包、本地运行时生成文件或已归档版本。

### 验证设计

- test_case_ref: TC-ACC-001-01
  acceptance_ref: ACC-001
  approach: 先写失败测试构造含 `.txt` 嵌入附件的 docx，验证 `DocumentParser` 和 `DocxParser` 都能暴露附件文本；再实现 txt 类型解析。
  evidence: `python -m pytest tests/test_attachment_extraction.py tests/test_docx_parser.py -q`
  required_stage: implementation

- test_case_ref: TC-ACC-002-01
  acceptance_ref: ACC-002
  approach: 前端测试断言新文案；后端旧格式上传测试作为回归，确认没有收窄兼容；后端内网 Dockerfile 静态测试确认镜像安装并校验 `soffice`。
  evidence: `cd frontend && npm test -- --watchAll=false --runTestsByPath src/__tests__/uploadPage.targetSystem.test.js`；`python -m pytest tests/test_task_upload_legacy_doc_api.py tests/test_backend_config_env_files.py -q`
  required_stage: implementation

- test_case_ref: TC-ACC-003-01
  acceptance_ref: ACC-003
  approach: 静态测试解析 internal nginx，确认 HTTP server 和静态资源配置包含 HSTS 与三项通用安全头，且没有 HTTPS 跳转要求。
  evidence: `python -m pytest tests/test_frontend_nginx_upload_limit.py -q`
  required_stage: implementation

- test_case_ref: TC-ACC-004-01
  acceptance_ref: ACC-004
  approach: 静态测试 backend internal compose，不再包含 `/etc/timezone` 挂载，同时保留时区配置路径。
  evidence: `python -m pytest tests/test_backend_config_env_files.py -q`
  required_stage: implementation

- test_case_ref: TC-ACC-005-01
  acceptance_ref: ACC-005
  approach: 脚本级测试创建临时 `.env.frontend` 并调用 upstream 解析和 runtime nginx 渲染，确认 `proxy_pass` 使用 env 值。
  evidence: `python -m pytest tests/test_deploy_frontend_internal_script.py -q`
  required_stage: implementation

- test_case_ref: TC-ACC-006-01
  acceptance_ref: ACC-006
  approach: 静态测试 internal compose、nginx 和部署脚本，确认 443/SSL/HTTPS 证书路径被移除。
  evidence: `python -m pytest tests/test_frontend_nginx_upload_limit.py tests/test_deploy_frontend_internal_script.py -q`
  required_stage: implementation

### 重开触发器

- 如果安全团队要求真实 HTTPS HSTS 语义、443 入口或 HTTP 到 HTTPS 跳转，必须重开 Requirement/Design。
- 如果 txt 附件样本无法通过后缀或内容可靠识别，需要补充样本并重开解析策略。
- 如果实现需要改变任务上传 API 白名单、鉴权、任务状态或报告输出语义，必须重开 Design。
