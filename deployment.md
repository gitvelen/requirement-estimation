# deployment.md

## Deployment Plan
target_env: staging
deployment_date: 2026-04-23
deployment_method: manual

## Pre-deployment Checklist
- [x] all acceptance items passed
- [x] required migrations verified
- [x] rollback plan prepared
- [x] smoke checks prepared

## Deployment Steps
1. On 2026-04-23, rebuild the frontend production artifact with `CI=true npm run build` under `frontend/`, producing the deployed static bundle `build/static/js/main.84a75856.js`.
2. Rebuild and recreate the backend service with `DOCKER_BUILDKIT=0 COMPOSE_DOCKER_CLI_BUILD=0 docker-compose -f docker-compose.backend.yml up -d --build backend`; the running backend image changed from `sha256:7b09ae69d2bdd5bf1bcdcd28ed15faf2c39606189cbe26bb814e056c082346e3` to `sha256:0ec892b353f7758a348878694f673934d12872ed9cc4eefd8ab36d3954ad91b5`.
3. Restart the frontend container with `docker restart requirement-frontend` so the running Nginx service immediately serves the refreshed `frontend/build` assets.
4. After container restart, execute runtime smoke checks for backend health, estimate-time COSMIC behavior, COSMIC-analysis reuse behavior, and the frontend guidance bundle actually served by the container.

## Verification Results
- smoke_test: pass
- key_features: runtime HTTP smoke on `/api/v1/tasks/{task_id}/estimate` verified that a feature without historical `cosmic_analysis` now triggers estimate-time COSMIC analysis and persists the new analysis, while a feature with preseeded COSMIC analysis reuses the original `counting_basis` and `cff=4` without overwrite; the deployed frontend bundle also contains the revised COSMIC guidance copy and preset labels.
- performance: no blocking regression was observed during real deployment or in the post-deployment smoke checks; the release remains limited to application logic and UI copy, with no schema migration and no frozen-contract change.
- restart_required: true
- restart_completed: pass
- restart_decision: the backend image does not mount application source code and the frontend serves versioned static assets from `frontend/build`, so this release required backend container recreation and frontend container restart; both actions were executed before opening manual verification.
- runtime_ready: pass
- runtime_ready_evidence: on 2026-04-23 `docker inspect requirement-backend` reported the new running image `sha256:0ec892b353f7758a348878694f673934d12872ed9cc4eefd8ab36d3954ad91b5` with `health=healthy`; `curl http://127.0.0.1:443/api/v1/health` returned `{\"status\":\"healthy\",\"service\":\"业务需求工作量评估系统\",\"version\":\"1.0.0\"}`; a temporary manager account and two temporary tasks were used to call `/api/v1/tasks/{task_id}/estimate` over real HTTP, proving `runtime_estimate.rule_status=applied` with persisted `cff=4` for the no-history case and `reuse_estimate.rule_status=applied` with preserved `counting_basis=预置COSMIC分析用于复用验证` for the reuse case; `http://127.0.0.1/asset-manifest.json` exposed `/static/js/main.84a75856.js`, and the served source map contained the updated COSMIC guidance copy plus the `偏保守口径 / 平衡口径 / 宽松口径` preset labels.
- manual_verification_ready: pass
- manual_verification_scope: on the live staging service, manually verify the rule-management page guidance modal and quick preset labels, then verify the two estimate scenarios: missing historical `cosmic_analysis` triggers runtime analysis, while existing analysis is reused.

## Acceptance Conclusion

此部分总结 testing.md 中的验收结果：

**字段定义**：
- `status`: 最终验收状态
  - `pass`: 所有 approved acceptance 都有 test_scope=full-integration 且 result=pass 的记录，且所有 residual_risk 都不是 high
  - `fail`: 任何 approved acceptance 没有通过或有 residual_risk=high（testing-coverage gate 会拒绝 residual_risk=high）
- `notes`: 部署结论和风险说明
- `approved_by`: 批准人
- `approved_at`: 批准日期

**前置条件**：
- testing.md 中每个 approved acceptance 都必须有至少一条 test_scope=full-integration 且 result=pass 的记录
- 所有 residual_risk 都已被评估和记录
- 没有 reopen_required=true 的测试记录（如果有，必须先重新开启 spec/design）

**与 testing.md 的对应关系**：
- deployment.md 的 status=pass 依赖于 testing.md 中所有 acceptance 的测试结果
- 只有当所有 acceptance 都通过 full-integration 测试时，才能标记为 pass

---

status: pass
notes: ACC-001 through ACC-004 all have full-integration pass records in `testing.md`, and on 2026-04-23 the change was actually deployed to the staging runtime on this workspace host by rebuilding the backend container and refreshing the frontend static bundle. Post-deployment HTTP smoke verified the two critical behaviors: missing historical `cosmic_analysis` now triggers runtime COSMIC analysis, while existing analysis is reused with the original counting basis preserved. The in-session manual acceptance for this project change was confirmed as passed on 2026-04-23. Residual risk remains low because the release only changes application logic and UI copy, with no schema migration or frozen-contract update.
approved_by: user
approved_at: 2026-04-23

## Rollback Plan
trigger_conditions:
  - estimate requests fail or stop producing expected `applied/degraded/skipped` COSMIC rule states after rollout
  - features without historical `cosmic_analysis` no longer trigger runtime COSMIC analysis during `/tasks/{task_id}/estimate`
  - the rule-management page regresses to wording that implies the page directly controls requirement split granularity
rollback_steps:
  1. Re-tag the previous backend image digest `sha256:7b09ae69d2bdd5bf1bcdcd28ed15faf2c39606189cbe26bb814e056c082346e3` back to `requirement-estimation-backend:latest` or rebuild from the prior approved source baseline, then rerun `docker-compose -f docker-compose.backend.yml up -d backend`.
  2. Restore the previous approved frontend build artifact, then restart `requirement-frontend` so Nginx serves the prior static bundle.
  3. Re-run the health check, the estimate-time COSMIC HTTP smoke, and the frontend bundle verification before reopening manual validation.

## Monitoring
metrics:
  - ratio of estimate requests that end in `applied`, `degraded`, and `skipped` COSMIC rule states
  - count of estimate requests that trigger runtime COSMIC analysis because historical analysis was absent
  - regression coverage status for COSMIC config page wording and estimate API behavior
alerts:
  - estimate endpoint error rate or latency increases after rollout
  - runtime COSMIC analysis unexpectedly stops executing for features without historical analysis
  - targeted frontend or backend smoke checks fail during staging rollout

## Post-deployment Actions
- [x] update related docs
- [x] record lessons learned if needed
- [x] archive change dossier to versions/
