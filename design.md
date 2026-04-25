# design.md

## Default Read Layer

**说明**：本章节是 Design 阶段当前结论的快照索引，用于快速浏览目标、边界和 WI 追溯；详细描述以后文正文为准。

### Goal / Scope Link
- requirement_refs:
  - REQ-001
  - REQ-002
  - REQ-003
  - REQ-004
  - REQ-005
- acceptance_refs:
  - ACC-001
  - ACC-002
  - ACC-003
  - ACC-004
  - ACC-005
- verification_refs:
  - VO-001
  - VO-002
  - VO-003
  - VO-004
  - VO-005
- spec_alignment_check:
  - spec_ref: REQ-001
    aligned: true
    notes: 三项通用安全头按“API 由后端、静态页由前端 nginx”统一补齐，避免只在局部页面生效。
  - spec_ref: REQ-002
    aligned: true
    notes: 保留现有 `http://<前端IP>:8000` 访问方式，不做 `8000 -> 443` 自动重定向。
  - spec_ref: REQ-003
    aligned: true
    notes: HSTS 只在新增的 `https://<前端IP>:443` 前端 HTTPS 入口下发，头值固定为 `max-age=16070400`。
  - spec_ref: REQ-004
    aligned: true
    notes: 设计明确了 HSTS 的复测入口、TLS 终止点、证书目录和兼容性验证路径。
  - spec_ref: REQ-005
    aligned: true
    notes: 设计允许部署脚本在证书缺失时生成带目标访问 IP SAN 的自签名证书，但不扩展到浏览器信任链分发。

### Architecture Boundary
- system_context: 当前安全扫描入口为 `http://10.62.16.251:8000`，由内网前端 nginx 承接页面与 `/api/` 代理；仓库中仍保留后端独立暴露的历史部署路径。
- impacted_capabilities:
  - 前端页面与静态资源的统一安全头下发
  - 后端 API 的统一安全头下发
  - 内网前端 HTTPS/443 入口与 HSTS 复测能力
  - 内网前端部署脚本的证书/端口预检与运行态校验
  - 内网前端证书缺失时的自签名 IP 证书 fallback
- not_impacted_capabilities:
  - 业务路由、鉴权逻辑、数据模型、任务评估流程
  - 域名体系、受信任 CA 接入与浏览器根证书分发
  - 现有 `http://IP:8000` 基本访问方式
- impacted_shared_surfaces:
  - backend/app.py
  - frontend/nginx.conf
  - frontend/nginx.internal.conf
  - frontend/nginx-remote.conf
  - docker-compose.frontend.internal.yml
  - deploy-frontend-internal.sh
  - tests/test_frontend_nginx_upload_limit.py
  - tests/test_deploy_frontend_internal_script.py
  - tests/test_backend_security_headers.py
- major_constraints:
  - HSTS 只允许在 HTTPS/TLS 终止点下发，不能在纯 HTTP 入口上做伪闭环。
  - 现有 `http://IP:8000` 必须保留可访问，不得以安全头整改为名强制改用域名或 HTTPS。
  - `/api/` 代理链路不得重复追加与后端同名的三项通用安全头。
  - 自动生成的证书只允许作为环境内自签名 fallback，必须覆盖操作人指定的访问 IP，且不应覆盖已提供的正式证书。
  - 本轮不扩展到 CSP、Referrer-Policy、Permissions-Policy 等其他安全头。
- contract_required: false
- compatibility_constraints:
  - 旧的 HTTP/IP 访问方式继续可用。
  - 新增 HTTPS/443 仅作为第 3 项 HSTS 的复测入口，不替换现有入口。
  - 仓库不内置证书；证书优先由部署环境提供，缺失时才由脚本在目标环境本地生成。

### Work Item Derivation
- wi_id: WI-001
  input_refs:
    - docs/inputs/2026-04-24-security-headers-proposal.md#intent
    - docs/inputs/2026-04-24-security-headers-proposal.md#clarifications
  requirement_refs:
    - REQ-001
    - REQ-002
    - REQ-003
    - REQ-004
    - REQ-005
  goal: 在不改变业务行为的前提下，为 API、静态页和内网扫描入口补齐安全响应头，并新增用于 HSTS 复测的 HTTPS/443 前端入口。
  covered_acceptance_refs: [ACC-001, ACC-002, ACC-003, ACC-004, ACC-005]
  verification_refs:
    - VO-001
    - VO-002
    - VO-003
    - VO-004
    - VO-005
  dependency_refs: []
  contract_needed: false
  notes_on_boundary: 允许修改后端入口、三个前端 nginx 配置、内网前端 compose/部署脚本和对应测试，并允许在部署脚本内补充最小自签名证书 fallback；不允许扩散到业务逻辑、前端业务页面、域名体系、受信任 CA 接入或浏览器根证书分发。

### Design Slice Index
- DS-001:
  - appendix_ref: none
  - scope: 为 API、静态页和内网扫描入口补齐安全响应头，并通过新增 `https://<前端IP>:443` 前端入口承接 HSTS 复测；若目标环境缺少预置证书，则由部署脚本生成带 IP SAN 的自签名证书，同时保留现有 `http://<前端IP>:8000` 兼容访问。
  - requirement_refs: [REQ-001, REQ-002, REQ-003, REQ-004, REQ-005]
  - acceptance_refs: [ACC-001, ACC-002, ACC-003, ACC-004, ACC-005]
  - verification_refs: [VO-001, VO-002, VO-003, VO-004, VO-005]

## Summary

本次设计采用“后端统一补 API 头 + 前端 nginx 补静态页头 + 新增 HTTPS/443 前端入口承接 HSTS + 证书缺失时由部署脚本生成自签名 IP 证书”的最小闭环方案。
其中 `X-XSS-Protection`、`X-Frame-Options`、`X-Content-Type-Options` 通过 `FastAPI` 中间件和前端 nginx 静态响应双层收口，覆盖当前两类真实入口：前端页面/静态资源，以及后端 API/后端直连部署。
第 3 项 HSTS 不再停留在抽象讨论，设计上明确由内网前端 nginx 作为 TLS 终止点，对外新增 `https://<前端IP>:443` 复测入口，并在该入口统一返回 `Strict-Transport-Security: max-age=16070400`；若部署环境没有现成证书，则由部署脚本生成仅供该环境使用、覆盖目标访问 IP 的自签名证书。
为避免破坏现有使用方式，本轮保留 `http://<前端IP>:8000` 兼容访问，不做 `8000` 到 `443` 的自动重定向；这也是当前在“通过安全复测”和“不改坏用户访问”之间的最小可行平衡。

## Goal / Scope Link

### Scope Summary
- 为后端所有 HTTP API 响应补齐 `X-XSS-Protection: 1; mode=block`、`X-Frame-Options: DENY`、`X-Content-Type-Options: nosniff`。
- 为三个前端 nginx 配置中的静态页面和静态资源响应补齐相同的三项通用安全头。
- 为内网前端部署补齐 HTTPS/443 入口、证书挂载或自签名证书 fallback，以及 HSTS 响应头，以承接第 3 项复测。
- 保留现有 `http://<前端IP>:8000` 使用方式，不在本轮强制跳转或替换成 HTTPS-only 入口。

### spec_alignment_check
- spec_ref: REQ-001
  aligned: true
  notes: 设计按页面、静态资源、API 三类响应明确补齐三项通用安全头，并避免只有单点入口生效。
- spec_ref: REQ-002
  aligned: true
  notes: 明确保留 `http://<前端IP>:8000`，不做自动跳转，以兼容当前 Windows 浏览器直接输入 IP 的访问方式。
- spec_ref: REQ-003
  aligned: true
  notes: HSTS 头值固定为 `Strict-Transport-Security: max-age=16070400`，只在最终 HTTPS 复测入口统一返回。
- spec_ref: REQ-004
  aligned: true
  notes: 设计正文和 WI 已明确记录复测入口、443/TLS 前提、证书来源及兼容性验证方法。
- spec_ref: REQ-005
  aligned: true
  notes: 若部署目录缺少证书，脚本会按操作人指定 IP 生成自签名证书并显式保留“浏览器信任链未解决”的限制说明。

## Technical Approach

- 设计决策 1：通用安全头的责任边界按“API 由后端，静态页由前端”拆分。
  - `backend/app.py` 新增统一 HTTP 中间件，为所有 HTTP API 响应补齐 `X-XSS-Protection: 1; mode=block`、`X-Frame-Options: DENY`、`X-Content-Type-Options: nosniff`。
  - 前端 nginx 仅在静态页面和静态资源响应上补齐这三项头，`/api/` 代理链路不重复追加，直接透传后端响应头，避免同名响应头重复。
  - 这样既能覆盖当前通过前端入口访问的页面/静态资源，也能覆盖后端独立暴露的历史部署口径。

- 设计决策 2：HSTS 只在 HTTPS 终止点下发，不在当前 HTTP/IP 入口上做伪闭环。
  - 关闭 `DEC-001` 的具体方案为：内网前端 nginx 新增 `listen 443 ssl;` 的 HTTPS `server`，以它作为安全团队第 3 项的复测入口。
  - `Strict-Transport-Security: max-age=16070400` 只在该 HTTPS `server` 上统一追加，并覆盖首页、静态资源和代理 API 响应。
  - 现有 `http://<前端IP>:8000` 保留，不在本轮自动重定向到 HTTPS，以避免改变当前 Windows 浏览器直接输入 IP 的操作习惯。

- 设计决策 3：证书优先由部署层提供；若缺失，则由部署脚本生成带 IP SAN 的自签名证书。
  - 仓库内不存放证书；内网前端部署脚本优先读取固定证书目录中的 `cert.pem` 和 `key.pem`，挂载到容器内 `/etc/nginx/ssl/`。
  - 若证书文件缺失，脚本使用 `openssl` 在目标环境生成新的自签名证书和私钥，subjectAltName 必须覆盖操作人指定的访问 IP；建议通过 `FRONTEND_CERT_IPS=<ip1,ip2,...>` 显式传入，避免误用宿主机私网地址。
  - `docker-compose.frontend.internal.yml` 增加 `443:443` 暴露和证书目录挂载。
  - `deploy-frontend-internal.sh` 在停旧服务前先检查：`openssl` 是否可用、证书是否已存在或可按指定 IP 自动生成、443 端口是否可用、渲染后的 nginx 配置在离线镜像里可通过 `nginx -t`；任一失败都停止，避免把现有 8000 服务替换成不可用状态。
  - 该 fallback 只为 HTTPS/HSTS 落地与安装脚本复用服务，不承诺浏览器信任链闭环；若需要浏览器无告警访问，仍需单独引入受信任 CA 或根证书分发。

- 设计决策 4：配置文件按部署角色分层，不把 HSTS 强绑到所有 nginx 变体。
  - `frontend/nginx.conf`、`frontend/nginx-remote.conf`、`frontend/nginx.internal.conf` 都补齐三项通用安全头，保持不同前端交付方式的基线一致。
  - 只有内网前端运行时配置和其部署脚本/compose 负责新增 HTTPS/443 与 HSTS，因为当前安全扫描入口就是 `10.62.16.251:8000`，HSTS 闭环也只需先在该路径落地。
  - `docker-compose.yml`、`docker-compose.frontend.yml` 等未被当前复测直接依赖的交付路径，本轮不强制新增 `443` 暴露，避免把设计扩散成全环境重构。

## Architecture Boundary

- system_context: 当前内网主入口是 `http://10.62.16.251:8000 -> frontend/nginx.internal.conf -> proxy_pass http://10.62.22.121:443`；同时仓库仍保留后端直接对外暴露的历史部署路径。
- impacted_capabilities:
  - 前端页面和静态资源统一下发三项通用安全头
  - 后端 API 统一下发三项通用安全头
  - 内网前端 HTTPS/443 + HSTS 复测入口
  - 部署脚本的证书、端口与配置校验
  - 部署脚本的自签名证书 fallback 与 IP SAN 生成功能
- not_impacted_capabilities:
  - 业务路由、鉴权逻辑、数据模型、任务评估流程
  - 前端业务页面与交互逻辑
  - 域名治理、受信任 CA 接入、浏览器信任链分发
- impacted_shared_surfaces:
  - backend/app.py
  - frontend/nginx.conf
  - frontend/nginx.internal.conf
  - frontend/nginx-remote.conf
  - docker-compose.frontend.internal.yml
  - deploy-frontend-internal.sh
  - tests/test_frontend_nginx_upload_limit.py
  - tests/test_deploy_frontend_internal_script.py
  - tests/test_backend_security_headers.py
- not_impacted_shared_surfaces:
  - 前端业务组件和页面源码
  - 后端业务路由与数据访问层
  - 其他未被当前安全复测入口直接依赖的交付路径
- major_constraints:
  - HSTS 必须只在 HTTPS/TLS 终止点返回。
  - 三项通用安全头必须覆盖复测范围内的代表性首页、静态资源和 API。
  - `/api/` 代理层不得重复追加由后端统一下发的三项通用安全头。
  - 现有 `http://<前端IP>:8000` 不得因本轮整改变成不可用。
- contract_required: false
- compatibility_constraints:
  - 内网用户继续通过 IP 直接访问系统。
  - 新增 `https://<前端IP>:443` 作为补充入口，而非替换原入口。
  - 未引入新的外部接口契约或数据迁移要求。

## Boundaries & Impacted Surfaces

- system_context: 当前内网主入口是 `http://10.62.16.251:8000 -> frontend/nginx.internal.conf -> proxy_pass http://10.62.22.121:443`；同时仓库仍保留后端直接对外暴露的历史部署路径。
- impacted_surfaces:
  - `backend/app.py`：新增统一 HTTP 安全响应头中间件。
  - `frontend/nginx.conf`：补静态页/静态资源安全头基线。
  - `frontend/nginx.internal.conf`：补静态页安全头，并为运行时渲染保留 HTTPS/HSTS 入口骨架。
  - `frontend/nginx-remote.conf`：补静态页/静态资源安全头基线，保持远程前端部署口径一致。
  - `docker-compose.frontend.internal.yml`：新增 `443:443` 暴露和证书目录挂载。
  - `deploy-frontend-internal.sh`：新增 HTTPS 证书存在性/自动生成、`openssl`/端口预检、运行时配置渲染和 HTTP/HTTPS 双路径验证。
  - `tests/test_frontend_nginx_upload_limit.py`、`tests/test_deploy_frontend_internal_script.py`、新增后端安全头测试：覆盖配置与脚本回归。
- out_of_scope:
  - 业务路由、鉴权逻辑、数据模型、任务评估流程。
  - 域名体系、受信任 CA 接入、浏览器根证书分发。
  - 强制把 `http://<前端IP>:8000` 重定向到 HTTPS。
  - `Content-Security-Policy`、`Referrer-Policy`、`Permissions-Policy` 等本轮未进入需求范围的其他安全头。

## Execution Model

- mode: single-branch
- rationale: 本轮改动集中在同一条“入口响应头与部署接线”链路上，核心共享面只有 `backend/app.py`、前端 nginx 配置、内网前端 compose/脚本与对应测试。拆成多个分支只会增加共享文件冲突和权威文档同步成本，不会带来真实并行收益。

## Work Item Mapping

- wi_id: WI-001
  requirement_refs: [REQ-001, REQ-002, REQ-003, REQ-004, REQ-005]
  acceptance_refs: [ACC-001, ACC-002, ACC-003, ACC-004, ACC-005]
  summary: 为 API、静态页和内网扫描入口补齐安全响应头，并通过新增前端 HTTPS/443 入口承接 HSTS 复测，同时补齐后端部署环境变量样例与读取能力，保留现有 HTTP/IP 兼容访问。

## Work Item Execution Strategy

### Dependency Analysis
dependency_graph:
  WI-001:
    depends_on: []
    blocks: []
    confidence: high

### Parallel Recommendation
parallel_groups:
  - group: G1
    work_items: [WI-001]
    can_parallel: false
    rationale: 通用安全头、HSTS 入口、compose/部署脚本和测试都围绕同一条入口链路，拆成多个 WI 只会增加共享文件冲突。

### Branch Strategy Recommendation
recommended_branch_count: 1
rationale: |
  本轮是一次围绕“安全响应头 + HSTS 复测入口”的集中改动，单 WI 单分支最容易保持 `spec -> design -> work-item -> tests -> code` 一致。
  尤其 `backend/app.py`、`frontend/nginx.internal.conf`、`docker-compose.frontend.internal.yml` 和 `deploy-frontend-internal.sh` 存在强耦合，串行推进更稳妥。

alternative_if_parallel_needed: |
  若后续安全团队要求把其他交付路径也一并补齐 HTTPS/443，可在下一轮把“内网扫描入口闭环”和“其他部署变体收口”拆成新 WI。
  当前不建议预拆。

**Note**: The above three sections (Dependency Analysis, Parallel Recommendation, Branch Strategy Recommendation)
are suggestions only, not enforced by gates. User decides the actual execution strategy.

### Shared Surface Analysis
potentially_conflicting_files:
  - path: backend/app.py
    reason: 后端三项通用安全头的唯一统一入口。
    recommendation: 只在应用级统一中间件补齐，不在各路由局部重复加头。
  - path: backend/config/config.py
    reason: 后端运行参数与 env file 读取优先级集中在这里。
    recommendation: 只补 `.env.backend` / `.env.backend.internal` 读取和部署所需配置暴露，不改变业务默认行为。
  - path: frontend/nginx.internal.conf
    reason: 既承接现有 `8000` 入口，也要新增 `443` HTTPS/HSTS 入口。
    recommendation: 在同一配置内同时明确 HTTP 兼容入口、HTTPS 复测入口和 `/api/` 代理边界。
  - path: docker-compose.frontend.internal.yml
    reason: `443` 暴露和证书目录挂载都集中在这里。
    recommendation: 只增加当前 HSTS 闭环所需的最小挂载和端口，不顺带重构其他部署拓扑。
  - path: deploy-frontend-internal.sh
    reason: 需要在停旧服务前完成证书、端口和 nginx 配置预检。
    recommendation: 预检失败时直接停止，避免替换后才发现 443 路径不可用。
  - path: .env.backend.example
    reason: 独立部署示例文件需要与当前后端实际读取的参数集合保持一致。
    recommendation: 仅保留当前代码/部署脚本真实依赖的键，并把示例值写成贴近当前 IP 直连部署方式的样式。

conflict_risk_assessment:
  high_risk:
    - frontend/nginx.internal.conf
    - deploy-frontend-internal.sh
  medium_risk:
    - backend/app.py
    - docker-compose.frontend.internal.yml
    - backend/config/config.py
  low_risk:
    - .env.backend.example
    - frontend/nginx.conf
    - frontend/nginx-remote.conf
    - tests/test_frontend_nginx_upload_limit.py
    - tests/test_deploy_frontend_internal_script.py
    - tests/test_backend_security_headers.py
    - tests/test_backend_config_env_files.py

## Design Slice Index

- DS-001:
  - appendix_ref: none
  - scope: 为 API、静态页和内网扫描入口补齐安全响应头，并通过新增 `https://<前端IP>:443` 前端入口承接 HSTS 复测；若目标环境缺少预置证书，则由部署脚本生成带 IP SAN 的自签名证书，同时保留现有 `http://<前端IP>:8000` 兼容访问，并补齐后端独立部署 env 样例与 `Settings()` 对 `.env.backend` / `.env.backend.internal` 的直接读取。
  - requirement_refs: [REQ-001, REQ-002, REQ-003, REQ-004, REQ-005]
  - acceptance_refs: [ACC-001, ACC-002, ACC-003, ACC-004, ACC-005]
  - verification_refs: [VO-001, VO-002, VO-003, VO-004, VO-005]

## Work Item Derivation

- wi_id: WI-001
  input_refs:
    - docs/inputs/2026-04-24-security-headers-proposal.md#intent
    - docs/inputs/2026-04-24-security-headers-proposal.md#clarifications
  requirement_refs:
    - REQ-001
    - REQ-002
    - REQ-003
    - REQ-004
    - REQ-005
  goal: 在不改变业务行为的前提下，为 API、静态页和内网扫描入口补齐安全响应头，新增用于 HSTS 复测的 HTTPS/443 前端入口，并收口后端独立部署所需的环境变量样例与读取方式。
  covered_acceptance_refs: [ACC-001, ACC-002, ACC-003, ACC-004, ACC-005]
  verification_refs:
    - VO-001
    - VO-002
    - VO-003
    - VO-004
    - VO-005
  dependency_refs: []
  contract_needed: false
  notes_on_boundary: 允许修改 `backend/app.py`、`backend/config/config.py`、`.env.backend.example`、三个前端 nginx 配置、内网前端 compose/部署脚本和对应测试，并允许在部署脚本内新增最小自签名证书 fallback；不允许扩散到业务路由、前端业务页面、数据结构、域名体系、受信任 CA 接入或浏览器根证书分发。
  work_item_alignment: keep equal to work-items/WI-001.yaml acceptance_refs

## Contract Needs

- contract_id: none
  required: false
  reason: 本轮不引入新的外部接口契约，只在既有 HTTP 入口、nginx 配置和部署接线内补齐安全响应头与运行态校验。
  consumers: []

## Implementation Readiness Baseline

### Environment Configuration Matrix
- 后端验证继续使用现有 pytest + FastAPI TestClient，不引入新的外部依赖。
- 后端配置补充 `Settings()` 读取 `.env.backend` / `.env.backend.internal` 的自动化测试，并用示例文件键集合测试锁定 `.env.backend.example` 的完整性。
- nginx 配置验证沿用现有配置测试方式，扩展断言页面/静态资源安全头和 `/api/` 代理边界。
- 内网前端部署脚本测试沿用现有脚本测试结构，增加 `443` 暴露、证书目录挂载、自签名证书生成和 `nginx -t` 预检断言。

### Security Baseline
- HSTS 只在 `https://<前端IP>:443` 下发，不在 `http://<前端IP>:8000` 返回。
- 三项通用安全头必须在后端 API 和前端静态资源路径上都可见。
- 证书优先从部署环境提供的目录挂载；若脚本自动生成自签名证书，则也只允许在目标环境本地生成、本地使用，不入库、不落地到版本控制。
- 自动生成的自签名证书不解决浏览器信任链，相关风险需在测试/部署证据中显式记录。

### Data / Migration Strategy
- 本轮不涉及数据库或持久化结构迁移。
- 本轮不新增业务数据字段；变化集中在 HTTP 响应头、nginx 配置和部署脚本接线。

### Operability / Health Checks
- `deploy-frontend-internal.sh` 需要在停旧服务前完成 `openssl` 可用性检查、证书存在性或自动生成、`443` 端口可用性和运行时 `nginx -t` 校验。
- 部署后需保留 `http://localhost:8000` 可访问验证，以及 `https://localhost:443`/目标 IP 的 HSTS 头验证命令。
- 预检失败或运行态校验失败时必须中止替换，避免把现有 `8000` 入口改坏。

### Backup / Restore
- 回滚方式是回退 nginx 配置、compose 和部署脚本，不涉及数据回滚。
- 若 `443` 路径不可用，允许回退到仅保留原有 `8000` 服务的状态，但第 3 项 HSTS 需重新开启设计决策。

### UX / Experience Readiness
- 用户继续在 Windows 浏览器中通过 IP 直接输入现有地址访问系统。
- 本轮不引入“必须改用域名”或“必须信任新证书后才能继续工作”的流程变更承诺；如部署环境使用脚本自动生成的自签名证书，浏览器证书信任问题需要在测试/部署证据中显式记录，而不是在设计里假设自动解决。

## Verification Design

- ACC-001:
  - approach: 使用 `FastAPI TestClient` 验证 API 响应头，使用配置测试验证三个 nginx 配置中的静态页/静态资源安全头均存在。
  - evidence: 后端安全头测试通过；`tests/test_frontend_nginx_upload_limit.py` 或等效 nginx 配置测试扩展后通过。
- ACC-002:
  - approach: 部署脚本和人工验证双轨收口。脚本侧验证 `http://localhost:8000` 仍可访问；人工侧在 Windows 浏览器继续用当前 IP 打开首页，确认不需要切换到域名或强制 HTTPS。
  - evidence: `deploy-frontend-internal.sh` 的验证步骤、脚本测试，以及后续 `testing.md`/`deployment.md` 中的浏览器验证记录。
- ACC-003:
  - approach: 使用 `curl -k -I https://<前端IP>:443` 和 `curl -k -I https://<前端IP>:443/api/v1/health` 检查 HSTS 头；同时用脚本测试验证内网部署支持 `443` 暴露、证书挂载和运行时 nginx 配置校验。
  - evidence: `tests/test_deploy_frontend_internal_script.py` 扩展后通过；运行态 HTTP 头检查命令输出保留为测试/部署证据。
- ACC-004:
  - approach: 通过本设计文档、`work-items/WI-001.yaml` 和后续部署检查项明确记录 HSTS 的复测入口、TLS 终止边界、证书目录和“不做 `8000 -> 443` 重定向”的兼容策略。
  - evidence: `design.md`、`work-items/WI-001.yaml` 和后续 `deployment.md` 的对应章节可直接引用，无需依赖口头说明。
- ACC-005:
  - approach: 使用脚本测试验证“证书缺失 -> 自动生成 `cert.pem` / `key.pem` -> 证书包含指定 IP SAN -> HTTPS 健康检查继续可用”的闭环；同时在部署文档保留“自签名证书不解决浏览器信任链”的说明。
  - evidence: `tests/test_deploy_frontend_internal_script.py` 的新增断言、`openssl x509 -text` 等价输出，以及 `deployment.md` 中对浏览器信任限制的记录。

## Failure Paths / Reopen Triggers

- 如果安全团队坚持原始 `http://10.62.16.251:8000` 本身必须返回 HSTS，或必须自动重定向到 HTTPS，需重新开启 spec/design，因为这会改变当前“保留 `8000` 兼容入口”的既定边界。
- 如果 `X-Frame-Options: DENY` 被证实现网依赖 iframe/门户嵌入，需重新开启 spec/design，并与安全团队重新对齐取值。
- 如果前端服务器无法提供 `443` 端口、`openssl` 或正确的访问 IP 信息，导致 HTTPS/443 入口或自签名证书 fallback 不可落地，需重新开启 spec/design，重新选择第 3 项闭环路径。
- 如果后续要求把浏览器信任链下发、受信任 CA 接入或域名治理也纳入本次交付，需重新开启 spec/design，因为这已超出当前最小闭环范围。

## Appendix Map

- none
