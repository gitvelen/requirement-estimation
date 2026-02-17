# [需求分析与评估系统] - 版本号:v2.1

---

## 核心原则
1. 先澄清再动手：目标 / 边界（不做什么）/ 约束 / 风险 / 验收方式，不清楚先问清。
2. 用户价值可量化：为谁解决什么问题；成功指标必须给出口径与“基线→目标”。
3. 范围与优先级先锁定：把要做/不做写清楚；任何“加需求/改方向”都必须说明代价（时间/风险/影响面），并重新确认验收与计划后再改。
4. 需求可验收且可追溯：每条需求都有可测试的验收标准；并维护追溯链路，能从场景一路追到实现与验证。
5. 小步可交付、始终可回滚：优先垂直切片；任何线上行为变化必须有回滚/开关/灰度方案。
6. 证据驱动、验证可复现：关键结论必须附命令/环境/关键输出（性能需基准对比）。
7. 安全合规优先：最小权限、输入校验、密钥/敏感数据不落盘；新增依赖需“必要性+替代方案+维护/安全评估”。
8. 质量闭环与透明记录：合入前自测；缺陷立即处理并记录。

---

## 文档交互约定
- **文档结构说明**：详见 `.aicoding/STRUCTURE.md`。
- **文档模板**：`.aicoding/templates/`
- **命名约定**：详见 `.aicoding/STRUCTURE.md` 的"命名与追溯"章节。
- 文档更新后必须自查"是否包含所有讨论内容"，并更新版本号和变更记录。
- REQ 编号调整后必须同步更新 plan.md 的引用，并执行引用存在性自检。

---

## 阶段化流程约定（Phase）
- **工作流控制**：详见 `.aicoding/ai_workflow.md`（时期划分、收敛判定、紧急中断）。
- **阶段化流程**：项目按 `.aicoding/phases/` 中的阶段顺序执行。
- **可选审查**：当用户消息包含 `@review` 时，读取 `.aicoding/templates/review_template.md` 执行审查，并将结论落盘到 `docs/<版本号>/review_<stage>.md`（例如 `review_proposal.md`）（建议性质；默认不修改业务代码）。
- **阶段状态**：`docs/<版本号>/status.md` 是单一真相源（YAML front matter 的 `_phase` / `_change_status` / `_run_status` / `_workflow_mode` + 最后更新 + 完成日期等；缺失则用 `.aicoding/templates/status_template.md` 创建并默认 Proposal/in_progress）；每阶段完成后由 AI 更新并提示你确认/进入下一阶段。
- **变更单（CR，可选但推荐）**：当已完成/已测试的内容出现“新增需求/改方向/范围调整”时，先写 `docs/<版本号>/cr/CR-*.md`（记录基线、影响面、验收/回滚），并在 `status.md` 的 Active CR 列表登记；日常审查默认按 diff-only 执行（除非 CR 触发强制项）。
- **经验教训沉淀**：关键教训记录在 `docs/lessons_learned.md`（缺失则用 `.aicoding/templates/lessons_learned_template.md` 初始化），每次返工/缺陷/事故后由 AI 追加；高频/高风险项需提炼成规则/清单/自动化验证。
- **Git 协作（PR）**：默认走 PR，推荐 `Squash and merge`。
- **Git 授权边界**：以下操作必须用户明确授权：`merge`（含 PR merge 动作）、`reset --hard`、`push --force`（含 `--force-with-lease`）、`--no-verify`（跳过 Git hooks）；其余常规 Git 操作可直接执行。