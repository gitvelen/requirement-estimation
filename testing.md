# testing.md

<!-- CODESPEC:TESTING:READING -->
## 0. AI 阅读契约

- 本文件不是测试说明书模板，而是“测试用例计划 + 测试执行证据”的权威账本。
- `TC-*` 在需求确认后生成，用于说明每条验收如何被证明；`RUN-*` 在实际执行后追加，用于记录证据。
- `spec.md` 的 `VO-*` 定义必须验证什么和证据类型；本文件的 `TC-*` 定义如何用场景、fixture、命令、步骤和 `RUN-*` 证据执行验证。
- 复杂流程的 `TC-*` 应引用或复现 `spec.md` 中的流程叙事，覆盖 happy path、失败/降级路径和关键产物链；不能只扫描字段或禁用入口。
- Testing 阶段不得临时发明覆盖口径；若发现缺少必要测试用例，应回到 Requirement/Design 补齐。
- 人工测试不是豁免测试，必须写明人工原因、步骤、预期结果和证据形状。

<!-- CODESPEC:TESTING:CASES -->
## 1. 验收覆盖与测试用例

- tc_id: TC-ACC-001-01
  requirement_refs: [REQ-001]
  acceptance_ref: ACC-001
  verification_ref: VO-001
  work_item_refs: [WI-001]
  test_type: integration
  verification_mode: automated
  required_stage: implementation
  scenario: 解析包含 txt 嵌入附件的需求文档
  given: 一个 .docx 主文档中嵌入有效 txt 附件和可选损坏附件
  when: 调用文档解析器和需求文档解析器解析该主文档
  then: 解析结果包含有效 txt 附件正文，损坏附件不会阻断主文档和有效附件
  evidence_expectation: `python -m pytest tests/test_attachment_extraction.py tests/test_docx_parser.py -q` 通过
  automation_exception_reason: none
  manual_steps:
    - none
  status: planned

- tc_id: TC-ACC-002-01
  requirement_refs: [REQ-002]
  acceptance_ref: ACC-002
  verification_ref: VO-002
  work_item_refs: [WI-001]
  test_type: integration
  verification_mode: automated
  required_stage: implementation
  scenario: 发起评估页展示新的上传说明且旧格式后端兼容仍保留
  given: 前端发起评估页渲染，后端上传接口沿用既有兼容测试，后端 internal 镜像需要提供 `soffice`
  when: 执行前端页面测试、后端旧格式上传测试和 Dockerfile 依赖静态测试
  then: 页面出现“上传需求文档（.docx格式）”，后端 .doc/.xls 兼容测试不回退，且后端 internal 镜像构建脚本安装并校验 `soffice`
  evidence_expectation: `cd frontend && npm test -- --watchAll=false --runTestsByPath src/__tests__/uploadPage.targetSystem.test.js` 与 `python -m pytest tests/test_task_upload_legacy_doc_api.py tests/test_backend_config_env_files.py -q` 通过
  automation_exception_reason: none
  manual_steps:
    - none
  status: planned

- tc_id: TC-ACC-003-01
  requirement_refs: [REQ-003]
  acceptance_ref: ACC-003
  verification_ref: VO-003
  work_item_refs: [WI-001]
  test_type: security
  verification_mode: automated
  required_stage: implementation
  scenario: 内网前端 HTTP 8000 返回安全扫描所需响应头
  given: `frontend/nginx.internal.conf` 作为内网前端 nginx 模板
  when: 静态检查 HTTP server 和静态资源 location 的响应头配置
  then: HTTP 入口包含 HSTS 与三项通用安全头，不要求 HTTPS 跳转
  evidence_expectation: `python -m pytest tests/test_frontend_nginx_upload_limit.py -q` 通过
  automation_exception_reason: none
  manual_steps:
    - none
  status: planned

- tc_id: TC-ACC-004-01
  requirement_refs: [REQ-004]
  acceptance_ref: ACC-004
  verification_ref: VO-004
  work_item_refs: [WI-001]
  test_type: integration
  verification_mode: automated
  required_stage: implementation
  scenario: 后端 internal compose 删除 /etc/timezone 挂载
  given: `docker-compose.backend.internal.yml` 是后端内网部署配置
  when: 静态读取 compose 配置
  then: 配置不包含 `/etc/timezone:/etc/timezone:ro`，且保留 `TZ` 或 `/etc/localtime` 时区路径
  evidence_expectation: `python -m pytest tests/test_backend_config_env_files.py -q` 通过
  automation_exception_reason: none
  manual_steps:
    - none
  status: planned

- tc_id: TC-ACC-005-01
  requirement_refs: [REQ-005]
  acceptance_ref: ACC-005
  verification_ref: VO-005
  work_item_refs: [WI-001]
  test_type: integration
  verification_mode: automated
  required_stage: implementation
  scenario: 前端部署脚本从 .env.frontend 读取后端 upstream 并渲染 nginx
  given: `.env.frontend` 中配置 `FRONTEND_BACKEND_UPSTREAM=10.62.22.121:443`
  when: 调用部署脚本的 upstream 解析和 runtime nginx 渲染逻辑
  then: 运行时 nginx 配置包含 `proxy_pass http://10.62.22.121:443;`，无需手工修改模板
  evidence_expectation: `python -m pytest tests/test_deploy_frontend_internal_script.py -q` 通过
  automation_exception_reason: none
  manual_steps:
    - none
  status: planned

- tc_id: TC-ACC-006-01
  requirement_refs: [REQ-006]
  acceptance_ref: ACC-006
  verification_ref: VO-006
  work_item_refs: [WI-001]
  test_type: integration
  verification_mode: automated
  required_stage: implementation
  scenario: 前端部署不再启动 443 端口服务
  given: 内网前端 nginx、compose 和部署脚本
  when: 静态检查 443/SSL/HTTPS 相关配置
  then: compose 不暴露 443、不挂载 SSL，nginx 不监听 443，部署脚本不执行证书生成或 HTTPS 健康检查
  evidence_expectation: `python -m pytest tests/test_frontend_nginx_upload_limit.py tests/test_deploy_frontend_internal_script.py -q` 通过
  automation_exception_reason: none
  manual_steps:
    - none
  status: planned

<!-- CODESPEC:TESTING:RUNS -->
## 2. 测试执行记录

- run_id: RUN-001
  test_case_ref: TC-ACC-001-01
  acceptance_ref: ACC-001
  work_item_ref: WI-001
  test_type: integration
  test_scope: branch-local
  verification_type: automated
  command_or_steps: python -m pytest tests/test_attachment_extraction.py tests/test_docx_parser.py -q
  artifact_ref: terminal-output 13 passed in 4.82s
  result: pass
  tested_at: 2026-04-29
  tested_by: codex
  residual_risk: low
  reopen_required: false

- run_id: RUN-002
  test_case_ref: TC-ACC-002-01
  acceptance_ref: ACC-002
  work_item_ref: WI-001
  test_type: integration
  test_scope: branch-local
  verification_type: automated
  command_or_steps: cd frontend && npm test -- --watchAll=false --runTestsByPath src/__tests__/uploadPage.targetSystem.test.js; python -m pytest tests/test_task_upload_legacy_doc_api.py -q via combined backend deploy test run
  artifact_ref: terminal-output frontend 3 passed in 10.572s; combined backend/deploy suite 19 passed in 7.31s
  result: pass
  tested_at: 2026-04-29
  tested_by: codex
  residual_risk: low
  reopen_required: false

- run_id: RUN-003
  test_case_ref: TC-ACC-003-01
  acceptance_ref: ACC-003
  work_item_ref: WI-001
  test_type: security
  test_scope: branch-local
  verification_type: automated
  command_or_steps: python -m pytest tests/test_frontend_nginx_upload_limit.py tests/test_deploy_frontend_internal_script.py tests/test_backend_config_env_files.py -q
  artifact_ref: terminal-output 17 passed in 4.69s
  result: pass
  tested_at: 2026-04-29
  tested_by: codex
  residual_risk: low
  reopen_required: false

- run_id: RUN-004
  test_case_ref: TC-ACC-004-01
  acceptance_ref: ACC-004
  work_item_ref: WI-001
  test_type: integration
  test_scope: branch-local
  verification_type: automated
  command_or_steps: python -m pytest tests/test_frontend_nginx_upload_limit.py tests/test_deploy_frontend_internal_script.py tests/test_backend_config_env_files.py tests/test_task_upload_legacy_doc_api.py -q
  artifact_ref: terminal-output 19 passed, 1 warning in 7.31s
  result: pass
  tested_at: 2026-04-29
  tested_by: codex
  residual_risk: low
  reopen_required: false

- run_id: RUN-005
  test_case_ref: TC-ACC-005-01
  acceptance_ref: ACC-005
  work_item_ref: WI-001
  test_type: integration
  test_scope: branch-local
  verification_type: automated
  command_or_steps: python -m pytest tests/test_frontend_nginx_upload_limit.py tests/test_deploy_frontend_internal_script.py tests/test_backend_config_env_files.py -q
  artifact_ref: terminal-output 17 passed in 4.69s
  result: pass
  tested_at: 2026-04-29
  tested_by: codex
  residual_risk: low
  reopen_required: false

- run_id: RUN-006
  test_case_ref: TC-ACC-006-01
  acceptance_ref: ACC-006
  work_item_ref: WI-001
  test_type: integration
  test_scope: branch-local
  verification_type: automated
  command_or_steps: python -m pytest tests/test_frontend_nginx_upload_limit.py tests/test_deploy_frontend_internal_script.py tests/test_backend_config_env_files.py -q
  artifact_ref: terminal-output 17 passed in 4.69s
  result: pass
  tested_at: 2026-04-29
  tested_by: codex
  residual_risk: low
  reopen_required: false

- run_id: RUN-007
  test_case_ref: TC-ACC-001-01
  acceptance_ref: ACC-001
  work_item_ref: WI-001
  test_type: integration
  test_scope: full-integration
  verification_type: automated
  command_or_steps: python -m pytest tests/test_attachment_extraction.py tests/test_docx_parser.py -q
  artifact_ref: terminal-output 13 passed in 6.95s
  result: pass
  tested_at: 2026-04-29
  tested_by: codex
  residual_risk: low
  reopen_required: false

- run_id: RUN-008
  test_case_ref: TC-ACC-002-01
  acceptance_ref: ACC-002
  work_item_ref: WI-001
  test_type: integration
  test_scope: full-integration
  verification_type: automated
  command_or_steps: cd frontend && npm test -- --watchAll=false --runTestsByPath src/__tests__/uploadPage.targetSystem.test.js; python -m pytest tests/test_task_upload_legacy_doc_api.py -q via combined backend deploy test run
  artifact_ref: terminal-output frontend 3 passed in 12.264s; combined backend/deploy suite 19 passed, 1 warning in 10.81s
  result: pass
  tested_at: 2026-04-29
  tested_by: codex
  residual_risk: low
  reopen_required: false

- run_id: RUN-009
  test_case_ref: TC-ACC-003-01
  acceptance_ref: ACC-003
  work_item_ref: WI-001
  test_type: security
  test_scope: full-integration
  verification_type: automated
  command_or_steps: python -m pytest tests/test_frontend_nginx_upload_limit.py tests/test_deploy_frontend_internal_script.py tests/test_backend_config_env_files.py tests/test_task_upload_legacy_doc_api.py -q
  artifact_ref: terminal-output 19 passed, 1 warning in 10.81s
  result: pass
  tested_at: 2026-04-29
  tested_by: codex
  residual_risk: low
  reopen_required: false

- run_id: RUN-010
  test_case_ref: TC-ACC-004-01
  acceptance_ref: ACC-004
  work_item_ref: WI-001
  test_type: integration
  test_scope: full-integration
  verification_type: automated
  command_or_steps: python -m pytest tests/test_frontend_nginx_upload_limit.py tests/test_deploy_frontend_internal_script.py tests/test_backend_config_env_files.py tests/test_task_upload_legacy_doc_api.py -q
  artifact_ref: terminal-output 19 passed, 1 warning in 10.81s
  result: pass
  tested_at: 2026-04-29
  tested_by: codex
  residual_risk: low
  reopen_required: false

- run_id: RUN-011
  test_case_ref: TC-ACC-005-01
  acceptance_ref: ACC-005
  work_item_ref: WI-001
  test_type: integration
  test_scope: full-integration
  verification_type: automated
  command_or_steps: python -m pytest tests/test_frontend_nginx_upload_limit.py tests/test_deploy_frontend_internal_script.py tests/test_backend_config_env_files.py tests/test_task_upload_legacy_doc_api.py -q
  artifact_ref: terminal-output 19 passed, 1 warning in 10.81s
  result: pass
  tested_at: 2026-04-29
  tested_by: codex
  residual_risk: low
  reopen_required: false

- run_id: RUN-012
  test_case_ref: TC-ACC-006-01
  acceptance_ref: ACC-006
  work_item_ref: WI-001
  test_type: integration
  test_scope: full-integration
  verification_type: automated
  command_or_steps: python -m pytest tests/test_frontend_nginx_upload_limit.py tests/test_deploy_frontend_internal_script.py tests/test_backend_config_env_files.py tests/test_task_upload_legacy_doc_api.py -q
  artifact_ref: terminal-output 19 passed, 1 warning in 10.81s
  result: pass
  tested_at: 2026-04-29
  tested_by: codex
  residual_risk: low
  reopen_required: false

- run_id: RUN-013
  test_case_ref: TC-ACC-002-01
  acceptance_ref: ACC-002
  work_item_ref: WI-001
  test_type: integration
  test_scope: branch-local
  verification_type: automated
  command_or_steps: python -m pytest tests/test_backend_config_env_files.py -q; python -m pytest tests/test_frontend_nginx_upload_limit.py tests/test_deploy_frontend_internal_script.py tests/test_backend_config_env_files.py tests/test_task_upload_legacy_doc_api.py -q; cd frontend && npm test -- --watchAll=false --runTestsByPath src/__tests__/uploadPage.targetSystem.test.js
  artifact_ref: terminal-output backend config 5 passed in 0.24s; combined backend/deploy suite 20 passed, 1 warning in 8.99s; frontend 3 passed in 10.073s
  result: pass
  tested_at: 2026-04-29
  tested_by: codex
  residual_risk: medium
  reopen_required: false

- run_id: RUN-014
  test_case_ref: TC-ACC-001-01
  acceptance_ref: ACC-001
  work_item_ref: WI-001
  test_type: integration
  test_scope: full-integration
  verification_type: automated
  command_or_steps: python -m pytest tests/test_attachment_extraction.py tests/test_docx_parser.py -q
  artifact_ref: terminal-output 13 passed in 4.65s
  result: pass
  tested_at: 2026-04-29
  tested_by: codex
  residual_risk: low
  reopen_required: false

- run_id: RUN-015
  test_case_ref: TC-ACC-002-01
  acceptance_ref: ACC-002
  work_item_ref: WI-001
  test_type: integration
  test_scope: full-integration
  verification_type: automated
  command_or_steps: python -m pytest tests/test_frontend_nginx_upload_limit.py tests/test_deploy_frontend_internal_script.py tests/test_backend_config_env_files.py tests/test_task_upload_legacy_doc_api.py -q; cd frontend && npm test -- --watchAll=false --runTestsByPath src/__tests__/uploadPage.targetSystem.test.js
  artifact_ref: terminal-output combined backend/deploy suite 20 passed, 1 warning in 8.27s; frontend 3 passed in 9.924s
  result: pass
  tested_at: 2026-04-29
  tested_by: codex
  residual_risk: medium
  reopen_required: false

- run_id: RUN-016
  test_case_ref: TC-ACC-003-01
  acceptance_ref: ACC-003
  work_item_ref: WI-001
  test_type: security
  test_scope: full-integration
  verification_type: automated
  command_or_steps: python -m pytest tests/test_frontend_nginx_upload_limit.py tests/test_deploy_frontend_internal_script.py tests/test_backend_config_env_files.py tests/test_task_upload_legacy_doc_api.py -q
  artifact_ref: terminal-output 20 passed, 1 warning in 8.27s
  result: pass
  tested_at: 2026-04-29
  tested_by: codex
  residual_risk: low
  reopen_required: false

- run_id: RUN-017
  test_case_ref: TC-ACC-004-01
  acceptance_ref: ACC-004
  work_item_ref: WI-001
  test_type: integration
  test_scope: full-integration
  verification_type: automated
  command_or_steps: python -m pytest tests/test_frontend_nginx_upload_limit.py tests/test_deploy_frontend_internal_script.py tests/test_backend_config_env_files.py tests/test_task_upload_legacy_doc_api.py -q
  artifact_ref: terminal-output 20 passed, 1 warning in 8.27s
  result: pass
  tested_at: 2026-04-29
  tested_by: codex
  residual_risk: low
  reopen_required: false

- run_id: RUN-018
  test_case_ref: TC-ACC-005-01
  acceptance_ref: ACC-005
  work_item_ref: WI-001
  test_type: integration
  test_scope: full-integration
  verification_type: automated
  command_or_steps: python -m pytest tests/test_frontend_nginx_upload_limit.py tests/test_deploy_frontend_internal_script.py tests/test_backend_config_env_files.py tests/test_task_upload_legacy_doc_api.py -q
  artifact_ref: terminal-output 20 passed, 1 warning in 8.27s
  result: pass
  tested_at: 2026-04-29
  tested_by: codex
  residual_risk: low
  reopen_required: false

- run_id: RUN-019
  test_case_ref: TC-ACC-006-01
  acceptance_ref: ACC-006
  work_item_ref: WI-001
  test_type: integration
  test_scope: full-integration
  verification_type: automated
  command_or_steps: python -m pytest tests/test_frontend_nginx_upload_limit.py tests/test_deploy_frontend_internal_script.py tests/test_backend_config_env_files.py tests/test_task_upload_legacy_doc_api.py -q
  artifact_ref: terminal-output 20 passed, 1 warning in 8.27s
  result: pass
  tested_at: 2026-04-29
  tested_by: codex
  residual_risk: low
  reopen_required: false

- run_id: RUN-020
  test_case_ref: TC-ACC-002-01
  acceptance_ref: ACC-002
  work_item_ref: WI-001
  test_type: integration
  test_scope: branch-local
  verification_type: automated
  command_or_steps: python -m pytest tests/test_backend_config_env_files.py -q; local runtime smoke with backend on 443 using absolute UPLOAD_DIR and frontend on 8000 proxying to backend 443; generated .doc parsed through backend.utils.old_format_parser.doc_bytes_to_text
  artifact_ref: terminal-output backend config 6 passed in 0.27s; curl http://127.0.0.1:8000/api/v1/health returned healthy; curl -I http://127.0.0.1:8000 returned Strict-Transport-Security max-age=16070400; .doc parser returned 本机旧版DOC解析验收文本
  result: pass
  tested_at: 2026-04-29
  tested_by: codex
  residual_risk: low
  reopen_required: false

- run_id: RUN-021
  test_case_ref: TC-ACC-002-01
  acceptance_ref: ACC-002
  work_item_ref: WI-001
  test_type: integration
  test_scope: full-integration
  verification_type: automated
  command_or_steps: python -m pytest tests/test_attachment_extraction.py tests/test_docx_parser.py -q; python -m pytest tests/test_frontend_nginx_upload_limit.py tests/test_deploy_frontend_internal_script.py tests/test_backend_config_env_files.py tests/test_task_upload_legacy_doc_api.py -q; cd frontend && npm test -- --watchAll=false --runTestsByPath src/__tests__/uploadPage.targetSystem.test.js
  artifact_ref: terminal-output attachment/docx 13 passed in 5.55s; backend/deploy suite 21 passed, 1 warning in 8.44s; frontend UploadPage 3 passed in 10.59s
  result: pass
  tested_at: 2026-04-29
  tested_by: codex
  residual_risk: low
  reopen_required: false

<!-- CODESPEC:TESTING:RISKS -->
## 3. 残留风险与返工判断

- residual_risk: low
- reopen_required: false
- notes:
  - HTTP 返回 HSTS 仅用于当前安全扫描头部检查；若后续要求真实 HTTPS HSTS 语义，需要回到需求阶段调整。
  - 当前机器执行 `docker build -f Dockerfile.internal -t requirement-backend:legacy-doc-soffice-check .` 时，基础镜像 `uv-mineru-opencv:0.1.0` 经 `docker.m.daocloud.io` 拉取返回 403，未进入 apt/soffice 安装阶段；需在可访问内网基础镜像的构建环境中重跑镜像构建和 `.doc` 上传烟测。
