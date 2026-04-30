# deployment.md

<!-- CODESPEC:DEPLOYMENT:READING -->
## 0. AI 阅读契约

- 本文件记录本次变更的真实交付、运行验证、回滚准备和人工验收结论。
- `release_mode=runtime` 表示需要运行部署；`artifact` 表示交付构建产物、文档或配置；`manual` 表示由人工执行交付步骤。
- 本文件不重复设计中的环境与安全要求，只引用并证明本次交付是否满足。
- `manual_verification_ready: pass` 只表示可以开始人工验收，不表示人工验收通过。

<!-- CODESPEC:DEPLOYMENT:TARGET -->
## 1. 发布对象与环境

release_mode: runtime
target_env: local-preacceptance-host:/home/admin/estimate/requirement-estimation
deployment_date: 2026-04-29
design_environment_ref: design.md#6-横切设计
release_artifact: feature-v3.5 current working tree; backend uvicorn on host port 443; frontend nginx container on host port 80 using /tmp/requirement-estimation-local-nginx.conf and frontend/build from current source

<!-- CODESPEC:DEPLOYMENT:PRECONDITIONS -->
## 2. 发布前条件

- [x] all required TC full-integration records passed: RUN-014 through RUN-019 and RUN-021 are pass in testing.md
- [x] deployment-only/manual TC evidence plan prepared: user validates through http://8.153.194.178/ or http://127.0.0.1/ with backend API proxied to local port 443
- [x] required migrations verified: no database migration is required; persistent paths remain data, logs, uploads, and backend/config
- [x] rollback plan prepared: stop local uvicorn process and remove requirement-frontend container, then restore previous frontend build if needed
- [x] smoke checks prepared: frontend index on 80, security headers, /api/v1/health through 80, backend /api/v1/health on 443, and legacy .doc parser smoke

<!-- CODESPEC:DEPLOYMENT:EXECUTION -->
## 3. 执行证据

status: pass
execution_ref: local runtime prepared by codex on 2026-04-29; backend pid 2338326 after restart, frontend container requirement-frontend
deployment_method: npm run build; docker run nginx:latest on 80 with local nginx config proxying to host.docker.internal:443; restart backend uvicorn on 443 with UPLOAD_DIR=/home/admin/estimate/requirement-estimation/uploads
deployed_at: 2026-04-29T19:14:36+08:00
deployed_revision: local-preacceptance-20260429-191436-feature-v3.5-working-tree
source_revision: feature-v3.5 HEAD 85a038f227c9a52d8bd09c8b0940ffb331053156 plus current working tree implementation changes
restart_required: yes
restart_reason: local runtime had to restart backend on 443 after installing libreoffice-writer dependencies and setting absolute UPLOAD_DIR for legacy .doc conversion; frontend was recreated on host port 80 from the current frontend/build output
runtime_observed_revision: local-preacceptance-20260429-191436-feature-v3.5-working-tree
runtime_ready_evidence: restarted backend uvicorn on 443 with pid 2338326; recreated requirement-frontend container on 80; curl http://127.0.0.1/api/v1/health and http://8.153.194.178/api/v1/health returned healthy; curl -I http://127.0.0.1/ and http://8.153.194.178/ returned Strict-Transport-Security max-age=16070400; generated .doc parsed through doc_bytes_to_text returned 本机旧版DOC解析验收文本; after backend event-loop blockage diagnostic, jixu login returned HTTP 200 through backend direct, local nginx proxy, and public HTTP entrypoint

<!-- CODESPEC:DEPLOYMENT:VERIFY -->
## 4. 运行验证

smoke_test: pass
runtime_ready: pass
manual_verification_ready: pass

说明：`release_mode=artifact|manual` 时，`runtime_ready` 可填写 `not-applicable`，但必须提供 `release_artifact` 与可复核执行证据。

<!-- CODESPEC:DEPLOYMENT:ROLLBACK -->
## 5. 回滚与监控

rollback_trigger_conditions:
  - local frontend at http://127.0.0.1/ or http://8.153.194.178/ cannot serve the login page
  - /api/v1/health through port 80 or direct backend port 443 fails
  - legacy .doc upload still reports soffice missing or conversion timeout
  - required HTTP security headers regress on the local 80 entrypoint
rollback_steps:
  1. Stop the local frontend with docker rm -f requirement-frontend
  2. Stop the local backend uvicorn process listening on 443
  3. Restore the previous frontend build from backup if user wants to return to the earlier local runtime
  4. Restart the previous known local backend command or docker compose runtime
  5. Verify rollback with curl http://127.0.0.1/ and curl http://127.0.0.1:443/api/v1/health
monitoring_metrics:
  - ss -ltnp output for host ports 443 and 80
  - docker ps status for requirement-frontend
  - curl http://127.0.0.1/api/v1/health response
  - curl -I http://127.0.0.1/ response headers
  - backend logs for old format parser errors, especially soffice missing or conversion timeout
monitoring_alerts:
  - local 80 returns non-200 or cannot load the login page
  - local 80 /api/v1/health returns non-healthy
  - backend port 443 is not listening
  - .doc parsing emits soffice missing or conversion timeout

<!-- CODESPEC:DEPLOYMENT:ACCEPTANCE -->
## 6. 人工验收与收口

status: pass
notes: local runtime acceptance passed by user on 2026-04-30; internal deployment is intentionally deferred until local acceptance passes; 2026-04-29 access diagnostic showed plain HTTP on port 80 returns 200 while the observed client request used TLS bytes against the HTTP entrypoint; 2026-04-29 jixu login delay was caused by the previous backend process being occupied by a long system profile scan after a timed-out import/governance request, and was cleared by backend restart
approved_by: user
approved_at: 2026-04-30

<!-- CODESPEC:DEPLOYMENT:POST_ACTIONS -->
## 7. 收口动作

post_deployment_actions:
  - [x] update related docs: local preacceptance deployment evidence recorded
  - [x] record user acceptance result after local verification
  - [ ] after local acceptance, deploy to internal environment with deploy-backend-internal.sh and deploy-frontend-internal.sh
  - [ ] archive stable version after internal deployment and acceptance
