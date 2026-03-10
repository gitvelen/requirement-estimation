# v2.6 实现检查清单

## 实现前检查
- [x] 已阅读 `docs/v2.6/status.md`、`docs/v2.6/plan.md`、`docs/v2.6/design.md`、`docs/v2.6/requirements.md`
- [x] 已对齐范围：仅覆盖 `backend/utils`、`backend/service`、`backend/api`、`backend/config`、测试与文档
- [x] 已明确验收标准：以 `plan.md` 的 T001~T006 和 `requirements.md` 的 20 个 GWT 为准
- [x] 已明确回滚策略：优先 `ENABLE_LLM_CHUNKING=false`，必要时版本回退到 `v2.5`
- [x] 开发环境就绪：本地 Python/pytest 可执行，测试全部使用临时目录和 mock

## 实现中检查
- [x] 仅做最小必要变更：不修改对外 API 契约，不新增运行时依赖
- [x] 安全与边界：保留既有权限/错误码，新增仅为内部 `context_override`
- [x] 可观测性：补齐 token/chunk/latency 相关测试与日志分支
- [x] 内容完整性：导入成功链路透传完整 `document_text`，不再依赖知识切片反拼装

## 实现后检查
- [x] 代码可运行：`python -m compileall -q backend`
- [x] 测试通过：`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_token_counter.py tests/test_llm_client.py tests/test_profile_summary_service.py tests/test_system_profile_import_api.py tests/test_knowledge_import_api.py tests/test_knowledge_routes_helpers.py`
- [x] 覆盖率满足门禁：`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -p pytest_cov --cov=backend.utils.token_counter --cov=backend.utils.llm_client --cov=backend.service.profile_summary_service --cov-report=term-missing tests/test_token_counter.py tests/test_llm_client.py tests/test_profile_summary_service.py`
- [x] 文档同步：已更新 `test_report.md`、`deployment.md`、`docs/技术方案设计.md`、`docs/接口文档.md`、`docs/部署记录.md`
- [x] 敏感信息检查：未写入真实密钥或生产数据

## 契约与集成验证
- [x] 仓库不存在 `scripts/validate_api_contracts.sh`；改用接口回归与契约检索代替
- [x] 契约检索通过：`rg -n "/api/v1/knowledge/imports|/api/v1/system-profiles/.*/profile/import|/api/v1/system-profiles/.*/profile/extraction-status" backend/api/system_profile_routes.py backend/api/knowledge_routes.py docs/v2.6/design.md docs/接口文档.md`
- [x] API 集成回归通过：系统画像导入、知识导入、任务状态查询均包含自动化证据
- [x] 当前无统一 typecheck 脚本；`pyproject.toml` 仅声明 `mypy` 依赖，未配置稳定门禁

## 关键结果
- [x] T001 完成：Token 预算、段落分块、配置项与环境文件落地
- [x] T002 完成：LLM raw 调用、usage 提取与 Stage1/Stage2 合并原语落地
- [x] T003 完成：`profile_summary_service` Token-aware 单次/分块路径与失败原子性落地
- [x] T004 完成：导入接口原文透传与 API 契约回归落地
- [x] T005 完成：回归、覆盖率、依赖差异与测试报告证据闭环
- [x] T006 完成：部署 runbook、回滚步骤与主文档同步落地
