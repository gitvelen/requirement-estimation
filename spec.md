# spec.md

## Summary

本次变更用于收口安全团队在测试环境扫描发现的 4 项安全响应头问题：`X-XSS-Protection`、`X-Frame-Options`、`Strict-Transport-Security`、`X-Content-Type-Options`。
当前需求目标是在不破坏当前 Windows 浏览器通过 IP 直接访问系统方式的前提下，定义统一的整改口径、默认头值和复测边界。
本地核查已确认当前后端入口与前端 nginx 入口都未统一下发上述响应头。
Requirements 阶段成功标准是：4 项扫描问题的正式 REQ/ACC/VO、输入追溯、兼容性约束和 HSTS 的设计前提已经收口到可审查状态，可支撑进入 Design 阶段。

<!-- SKELETON-END -->

## Inputs

- source_refs:
  - docs/inputs/2026-04-24-security-headers-proposal.md#intent
  - docs/inputs/2026-04-24-security-headers-proposal.md#clarifications
- source_owner: human
- maturity: L2
- normalization_note: 将安全扫描结果、用户对 IP 访问方式与复测目标的澄清、HSTS 的默认目标值与部署前提，以及“证书缺失时允许脚本自动生成自签名证书”的新增部署约束拆开整理；避免把第 3 项误写成“只需补一个响应头”的纯实现问题。
- approval_basis: 用户已确认四项问题都需要整改并通过安全团队复测；同时确认当前长期通过 IP 直接访问，第 3 项在没有更优路径时可先采纳安全团队建议的 HSTS 头值与 HTTPS/443 前提说明，并明确选择“脚本自动生成带 IP SAN 的自签名证书，但不扩展到浏览器信任链”作为部署 fallback。

## Intent

### Problem / Background
安全团队在测试环境入口 `http://10.62.16.251:8000` 上扫描出 4 项缺失的安全响应头问题，涉及 `X-XSS-Protection`、`X-Frame-Options`、`Strict-Transport-Security` 和 `X-Content-Type-Options`。

本地代码核查确认，当前后端 `FastAPI` 入口和仓库内三个前端 `nginx` 配置文件均未统一下发这些响应头，因此扫描结果与仓库现状一致，不是单点环境漂移。

同时，当前系统的真实使用方式不是通过域名访问，而是由内网/外网 Windows 机器直接在浏览器输入 IP 访问系统。用户已明确要求：整改必须充分测试，不能把这种既有访问方式改坏。

在四项问题中，`X-XSS-Protection`、`X-Frame-Options`、`X-Content-Type-Options` 可以先按统一响应头策略推进；`Strict-Transport-Security` 则除了目标头值外，还额外受到“HTTPS/443 入口”和当前 IP 访问兼容性的约束，因此需要在 Requirements 中显式记录默认口径和风险边界。

最新澄清是：为避免其他环境部署时因为没有预置 `cert.pem` / `key.pem` 而卡住，允许安装/部署脚本在证书缺失时自动生成带目标访问 IP subjectAltName 的自签名证书，以支撑 HTTPS/HSTS 验证闭环；但这不等于浏览器信任链已经解决，浏览器根证书分发或受信任 CA 接入仍不在本轮范围内。

### Goals
- G1: 为四项安全扫描问题建立统一、可追溯的整改范围和默认策略，而不是只记录零散的扫描原文。
- G2: 明确当前整改必须兼容“Windows 浏览器直接输入 IP 访问系统”的既有使用方式。
- G3: 将 `X-XSS-Protection`、`X-Frame-Options`、`X-Content-Type-Options` 的默认头值与覆盖范围固化为正式 requirement。
- G4: 将第 3 项 HSTS 的默认目标值、入口前提和复测风险边界在当前 Requirements 阶段写清楚，避免后续 Design / Implementation 阶段出现口径漂移。
- G5: 为“目标环境没有预置 HTTPS 证书”的部署场景定义最小 fallback，确保安装脚本可重复复用，但不把浏览器信任链治理混入本轮范围。

### Boundaries
- 本次 Requirements 不修改业务功能、角色权限、评估流程或数据模型。
- 本次 Requirements 不默认引入域名体系，也不把“新增域名访问方式”作为当前问题的唯一闭环路径。
- 本次 Requirements 不承诺“仅在当前 HTTP/IP 入口补一个 HSTS 响应头”就能关闭第 3 项问题；HSTS 的整改仍需在后续阶段明确适用入口和验证路径。
- 本次 Requirements 不允许通过牺牲现有 IP 直连可访问性来换取表面上的扫描通过。
- 本次 Requirements 不包含浏览器根证书分发、受信任 CA 接入或“浏览器无告警访问”的闭环承诺。

## Open Decisions

- decision_id: DEC-001
  summary: HSTS 的最终复测入口与 HTTPS/443 暴露方式
  status: resolved
  impact: high
  owner: human
  context: 用户确认当前长期通过 IP 直接访问系统，且没有可依赖的内网域名；同时接受在没有更优路径时先采纳安全团队建议的 HSTS 目标值 `max-age=16070400`。Design 阶段已将第 3 项复测入口收口为前端 nginx 新增的 `https://<前端IP>:443` HTTPS 入口，并明确保留现有 `http://<前端IP>:8000` 兼容访问，不做自动重定向。
  next_action: 后续实现按该入口补齐 HTTPS/443 暴露、证书挂载或自签名证书 fallback、HSTS 头和自动化验证命令。

## Requirements

### Proposal Coverage Map
- docs/inputs/2026-04-24-security-headers-proposal.md#intent -> REQ-001, REQ-002, REQ-003, REQ-004
- docs/inputs/2026-04-24-security-headers-proposal.md#clarifications -> REQ-002, REQ-003, REQ-004, REQ-005, DEC-001

### Source Coverage
- source_ref: docs/inputs/2026-04-24-security-headers-proposal.md#intent
  covered_by_reqs: [REQ-001, REQ-002, REQ-003, REQ-004]
  open_clarifications: []
  status: covered
- source_ref: docs/inputs/2026-04-24-security-headers-proposal.md#clarifications
  covered_by_reqs: [REQ-002, REQ-003, REQ-004, REQ-005]
  open_clarifications: []
  status: covered

### Clarification Status
- clr_id: CLR-001
  source_ref: docs/inputs/2026-04-24-security-headers-proposal.md#clarifications
  summary: 当前系统长期通过 IP 直连访问，且没有可依赖的内网域名
  status: resolved
  resolution: 后续 Requirements / Design 不得默认把“改成域名访问”当作当前整改前提，必须优先验证对 IP 访问的兼容性。
- clr_id: CLR-002
  source_ref: docs/inputs/2026-04-24-security-headers-proposal.md#clarifications
  summary: 第 3 项在没有更优路径时，可先采纳安全团队建议的 HSTS 目标头值
  status: resolved
  resolution: 当前 Requirements 默认目标值采用 `Strict-Transport-Security: max-age=16070400`；是否真正能在复测入口闭环，仍由 DEC-001 继续约束。
- clr_id: CLR-003
  source_ref: docs/inputs/2026-04-24-security-headers-proposal.md#clarifications
  summary: 整改不能把现有 Windows 浏览器输入 IP 的访问方式改坏
  status: resolved
  resolution: 兼容既有 IP 访问被提升为正式 requirement 和 acceptance，不作为口头约束保留。
- clr_id: CLR-004
  source_ref: docs/inputs/2026-04-24-security-headers-proposal.md#clarifications
  summary: 其他环境部署时若缺少现成 HTTPS 证书，允许安装/部署脚本自动生成带目标访问 IP SAN 的自签名证书
  status: resolved
  resolution: 当前 Requirements 明确允许“仅用于当前环境 HTTPS/HSTS 闭环”的自签名证书 fallback，但不把浏览器信任链、根证书分发或受信任 CA 接入纳入本轮范围。

### Functional
- REQ-001
  - summary: 系统必须为安全团队复测范围内的 Web 页面/接口建立统一安全响应头策略，至少统一下发 `X-XSS-Protection: 1; mode=block`、`X-Frame-Options: DENY`、`X-Content-Type-Options: nosniff`。
  - rationale: 这三项是当前扫描直接命中的缺失头，且不依赖额外的域名/证书前提即可先形成明确的整改目标。

- REQ-002
  - summary: 本次整改不得静默破坏当前基于 IP 直接访问系统的使用方式；任何需要改变浏览器输入 IP 后访问行为的方案，都必须被显式识别为兼容性风险并在后续阶段单独验证。
  - rationale: 用户已明确当前真实使用方式是 Windows 机器浏览器直接输入 IP，且整改不能把系统改坏；这属于硬约束而不是实现偏好。

- REQ-003
  - summary: 第 3 项 HSTS 的默认整改目标值采用 `Strict-Transport-Security: max-age=16070400`；若后续指定了用于复测的 HTTPS Web 服务器入口，则该入口在复测范围内的页面上必须统一返回该头值。
  - rationale: 用户已接受在没有更优路径时先采纳安全团队建议的头值，但 Requirements 需要把“头值默认口径”和“适用入口条件”一起固化，避免后续只记住其中一半。

- REQ-004
  - summary: 在对安全团队承诺关闭第 3 项问题之前，变更必须显式定义 HSTS 对应的复测入口、HTTPS/443 前提以及“不会破坏既有 IP 访问”的验证路径。
  - rationale: HSTS 不是单纯补一个响应头即可闭环的问题；如果不先写清楚适用入口和验证路径，后续 Requirements / Design 很容易出现承诺过度或复测口径不一致。

- REQ-005
  - summary: 若目标部署环境缺少预置的 `cert.pem` / `key.pem`，安装/部署脚本必须能够按指定访问 IP 生成仅供该环境使用的自签名证书，并确保生成证书的 subjectAltName 覆盖这些 IP；该能力只用于 HTTPS/HSTS 闭环，不代表浏览器信任链问题已被解决。
  - rationale: 用户已明确要求同一安装脚本可复用于其他环境；若继续强依赖人工预置证书，会让 HSTS 复测路径在新环境中反复卡住。与此同时，本轮目标仍是最小闭环，不能把浏览器根证书分发或受信任 CA 接入一并混入。

### Constraints
- 当前用户访问方式以浏览器直接输入 IP 为主，且当前没有可依赖的内网域名。
- 默认头值口径如下：`X-XSS-Protection: 1; mode=block`、`X-Frame-Options: DENY`、`X-Content-Type-Options: nosniff`、`Strict-Transport-Security: max-age=16070400`。
- 第 3 项必须同时考虑响应头取值、HTTPS/443 入口前提和既有 IP 访问兼容性，不能只选其中一项承诺。
- 自签名证书 fallback 仅用于目标环境 HTTPS/HSTS 落地；证书和私钥不得提交到版本控制，也不构成“浏览器可无告警访问”的承诺。
- 若后续发现现网存在必须被 iframe 嵌入的明确业务场景，不得直接忽略该冲突，必须回写 spec 并与安全团队重新对齐 `X-Frame-Options` 口径。

### Non-functional
- 覆盖一致性：同一复测入口下的代表性首页、API 响应和静态资源响应必须表现出一致的安全头策略，而不是只在个别接口生效。
- 兼容性：整改后的系统仍应保持用户通过现有 IP 地址直接打开页面的基本可用性。
- 可验证性：后续 Testing / Deployment 阶段必须能通过自动化命令或等效证据明确展示响应头结果，而不是只靠口头说明。
- 环境隔离：自动生成的自签名证书必须是环境本地生成、本地使用，不入库、不跨环境复用私钥。

## Acceptance

- acc_id: ACC-001
  source_ref: REQ-001
  expected_outcome: 在安全团队复测入口中抽样的代表性首页、API 响应和静态资源响应都包含 `X-XSS-Protection: 1; mode=block`、`X-Frame-Options: DENY`、`X-Content-Type-Options: nosniff`。
  priority: P0
  priority_rationale: 这是当前扫描命中的直接整改项，也是后续复测最基础、最可判定的关闭条件。
  status: approved

- acc_id: ACC-002
  source_ref: REQ-002
  expected_outcome: 整改完成后，用户仍可在 Windows 浏览器中通过当前 IP 地址直接访问系统，不会因为整改被静默切换到必须依赖域名的新访问方式。
  priority: P1
  priority_rationale: 用户已将“不能把系统改坏”明确为硬约束；若访问方式被破坏，整改即使关闭扫描项也不可接受。
  status: approved

- acc_id: ACC-003
  source_ref: REQ-003
  expected_outcome: 若最终确定了 HTTPS Web 服务器复测入口，则该入口在复测范围内的页面上统一返回 `Strict-Transport-Security: max-age=16070400`。
  priority: P0
  priority_rationale: 用户要求四项问题都以通过安全团队复测为目标，第 3 项的默认目标值必须能在最终复测入口被客观验证。
  status: approved

- acc_id: ACC-004
  source_ref: REQ-004
  expected_outcome: 在请求安全团队复测第 3 项之前，规格与后续设计/测试材料已经明确记录 HSTS 的复测入口、HTTPS/443 前提和 IP 访问兼容性验证方式，不存在口头默认或隐含前提。
  priority: P1
  priority_rationale: 若不先收口入口与验证路径，第 3 项最容易在实现、测试和复测阶段出现“各自理解不同”的问题。
  status: approved

- acc_id: ACC-005
  source_ref: REQ-005
  expected_outcome: 当目标环境未预置 `cert.pem` / `key.pem` 且操作人提供目标访问 IP 后，安装/部署脚本能够自动生成带这些 IP subjectAltName 的自签名证书，拉起 HTTPS/443 入口并保留“浏览器仍可能因自签名而提示风险”的书面说明。
  priority: P1
  priority_rationale: 这是让同一安装脚本可复用于其他环境的关键部署闭环，但它仍属于第 3 项的部署支撑能力，而不是新的业务功能。
  status: approved

## Verification

- vo_id: VO-001
  acceptance_ref: ACC-001
  verification_type: automated
  verification_profile: focused
  obligations:
    - 通过自动化命令或等效自动化测试验证代表性页面、API 响应和静态资源响应均返回三项直接整改的安全响应头。
    - 验证抽样范围覆盖最终安全团队复测所依赖的实际入口，而不是只覆盖本地单一子路径。
  artifact_expectation: 基于 `curl -I`、自动化 HTTP 测试或等效集成脚本的验证记录，能明确展示三项响应头的实际返回结果。

- vo_id: VO-002
  acceptance_ref: ACC-002
  verification_type: manual
  verification_profile: focused
  obligations:
    - 在目标环境使用 Windows 浏览器直接输入当前 IP 地址访问系统，验证首页和核心使用链路仍可正常打开。
    - 若整改引入 HTTPS/443 或其他入口调整，需验证用户输入 IP 后不会直接落入不可接受的中断状态。
  artifact_expectation: 浏览器人工验证记录、截图或 Deployment / Testing 阶段的兼容性验证证据。

- vo_id: VO-003
  acceptance_ref: ACC-003
  verification_type: automated
  verification_profile: focused
  obligations:
    - 在最终确定的 HTTPS 复测入口上自动检查 `Strict-Transport-Security` 头值是否精确等于 `max-age=16070400`。
    - 验证该头覆盖安全团队复测范围内的代表性页面，而不是只在单个响应上偶发出现。
  artifact_expectation: 指向最终 HTTPS 复测入口的自动化 HTTP 验证命令或脚本输出，能够显示 HSTS 头值。

- vo_id: VO-004
  acceptance_ref: ACC-004
  verification_type: manual
  verification_profile: focused
  obligations:
    - 检查 `spec.md`、后续 `design.md`、`testing.md` 或 `deployment.md` 是否明确记录 HSTS 的复测入口、HTTPS/443 前提和 IP 访问兼容性验证方式。
    - 在进入安全团队复测前确认不存在“入口未定、兼容性未测、却已承诺关闭第 3 项”的文档缺口。
  artifact_expectation: 权威文档中的明确章节引用和审查记录，能够证明第 3 项的入口与验证路径已经书面收口。

- vo_id: VO-005
  acceptance_ref: ACC-005
  verification_type: automated
  verification_profile: focused
  obligations:
    - 通过自动化测试或等效脚本验证：当证书文件缺失时，部署脚本会生成新的 `cert.pem` / `key.pem`，且证书 subjectAltName 精确覆盖操作人指定的访问 IP。
    - 验证生成逻辑不会覆盖已存在的人工证书，并且相关文档明确声明“自签名证书不解决浏览器信任链”。
  artifact_expectation: 基于部署脚本测试、`openssl x509 -text` 或等效命令的证据，能展示证书文件生成结果与 IP SAN 内容。
