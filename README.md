# 需求评估系统（v4升级版）

面向“业务需求工作量评估”的一体化系统，集成AI解析、Delphi多专家多轮评估、报告版本管理、知识库增强与效果报告。

## 关键能力
- 任务全流程：上传 → AI解析 → 人机协作修正 → 提交分配 → 多轮专家评估 → PDF报告版本
- 角色化入口：管理员/项目经理/专家
- 通知中心、个人中心（头像、我的任务/评估、操作记录）
- AI效果报告（指标快照 + 图表）
- 证据库/ESB索引/代码扫描（V4）
- 证据等级规则与系统画像（V4）
- 知识库导入与检索（可选）

## 快速启动
```bash
cp .env.example .env
docker-compose up -d
curl http://localhost:443/api/v1/health
```

## V4样例与演练
```bash
# 生成V4样例数据（证据/ESB/代码扫描）
python scripts/prepare_v4_samples.py

# 试点验收演练（生成报告与指标快照）
EMBEDDING_FALLBACK=1 python scripts/run_v4_pilot_demo.py
```

## 测试与联调
```bash
# 后端单测
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q

# 前端单测
cd frontend && npm test -- --watchAll=false

# 接口回归
BASE_URL=http://127.0.0.1:443 ADMIN_API_KEY=change_me SKIP_KNOWLEDGE=1 bash scripts/api_regression.sh

# 联调烟囱（无HTTP服务时）
MODE=testclient ADMIN_API_KEY=change_me python scripts/integration_smoke.py

# AI服务连通性
DASHSCOPE_API_KEY=sk-your-key python scripts/ai_smoke_test.py
```

## V4文档索引
- 需求/设计/任务：`docs/req_enhance_v4.md`、`docs/design_enhance_v4.md`、`docs/tasks_enhance_v4.md`

## 文档索引
- 需求/设计/任务：`docs/requirements.md`、`docs/design.md`、`docs/task.md`
- 接口文档：`docs/接口文档.md`
- 测试用例：`docs/测试用例.md`
- 开发/部署：`docs/开发手册.md`、`docs/部署手册.md`
