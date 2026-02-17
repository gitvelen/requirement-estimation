# [项目名称] 任务计划

## 文档元信息
| 项 | 值 |
|---|---|
| 状态 | Draft / In Progress / Done |
| 日期 | YYYY-MM-DD |
| 版本 | v0.1 |
| 基线版本（对比口径） | tag / commit（例如 `v1.0`） |
| Active CR（如有） | `docs/<版本号>/cr/CR-*.md` |
| 关联设计 | `docs/<版本号>/design.md` |
| 关联需求 | `docs/<版本号>/requirements.md` |
| 关联状态 | `docs/<版本号>/status.md` |

## 里程碑
| 里程碑 | 交付物 | 截止日期 |
|---|---|---|
| M1 |  | YYYY-MM-DD |

## Definition of Done（DoD）
- [ ] 需求可追溯：任务关联 `REQ/SCN/API/TEST` 清晰
- [ ] 代码可运行：不破坏主流程，必要时含回滚/开关策略
- [ ] 自测通过：列出验证命令/用例与结果
- [ ] 安全与合规：鉴权/输入校验/敏感信息不落盘
- [ ] 文档同步：必要时更新 requirements/design/操作说明

## 禁止项引用索引（来源：requirements.md REQ-C 章节）

> 仅列 ID + 一句话摘要，不复制 GWT 全文。内容以 requirements.md 为准。  
> 所有任务实现时必须确保不违反以下禁止项。

| REQ-C ID | 一句话摘要 |
|----------|-----------|
| REQ-C001 | [从 requirements.md 摘录] |

## 任务概览
### 状态标记规范
- `待办` - 未开始
- `进行中` - 正在处理
- `已完成` - 实现完成，自测通过

| 任务分类 | 任务ID | 任务名称 | 优先级 | 预估工时 | Owner | Reviewer | 关联CR（可选） | 关联需求项 | 任务状态 | 依赖任务ID | 验证方式 |
|---|---|---|---|---|---|---|---|---|---|---|---|

### 引用自检（🔴 MUST，R6）
**验证命令**（见 `.aicoding/templates/review_template.md` 附录 AC-03）：
```bash
VERSION="<版本号>"  # 替换为实际版本号

# 提取 plan.md 中的所有 REQ 引用
rg -o "REQ-C?[0-9]+" docs/${VERSION}/plan.md | LC_ALL=C sort -u > /tmp/plan_refs_${VERSION}.txt

# 提取 requirements.md 中定义的所有 REQ（只从定义行提取）
# 格式：#### REQ-001：[需求名称] → 提取 REQ-001
rg "^#### REQ-C?[0-9]+[：:]" docs/${VERSION}/requirements.md | sed 's/^#### //;s/[：:].*//' | LC_ALL=C sort -u > /tmp/req_defs_${VERSION}.txt

# 计算差集（期望为空）
LC_ALL=C comm -23 /tmp/plan_refs_${VERSION}.txt /tmp/req_defs_${VERSION}.txt
```
**检查项**：所有 REQ-ID 都存在于 requirements.md 中（期望差集为空）。

### 反向覆盖检查（🔴 MUST，反向 R6）

> 确保 requirements.md 中每条 REQ（含 REQ-C）都被至少一个任务覆盖（避免一开始就漏需求）。

**验证命令**：
```bash
VERSION="<版本号>"  # 替换为实际版本号

# 反向差集：requirements 定义了但 plan 未覆盖的 REQ
LC_ALL=C comm -23 /tmp/req_defs_${VERSION}.txt /tmp/plan_refs_${VERSION}.txt
```

**检查项**：差集为空（每条 REQ 都被至少一个任务引用）。差集非空时必须补充任务或确认为 Non-goals。

## 任务详情
### T001: [任务名称]
**分类**：
**优先级**：P0/P1/P2
**预估工时**：
**Owner**：
**Reviewer（可选）**：
**关联CR（可选）**：CR-YYYYMMDD-001
**工作目录（可选，多 Agent 推荐）**：`docs/<版本号>/tasks/T001-<任务名>/`

**关联需求项**：

**任务描述**：
- ...

**影响面/修改范围**：
- 影响模块：
- 预计修改文件：

**验收标准**：
- [ ] ...

**验证方式**（🔴 MUST，必须可复现）：
- 命令：`<具体命令，如 npm test、pytest tests/xxx、curl ...>`（代码/脚本任务）
- 或：`验证方式：人工确认` / `验证方式：N/A（文档类任务）`（非代码任务）
- 预期结果：<命令的预期输出或判定标准>
- 补充验证（可选）：<手动检查项/人工检查点>

**回滚/开关策略（如涉及线上行为变化）**：
- 回滚条件：
- 回滚步骤：
- 开关/灰度：

**失败处置**（可选，高风险任务必填）：
- 失败类型：<预期可能的失败场景>
- 处置：<重试/降级/人类决策>
- 回退方案：<如果本任务失败，如何回退到安全状态>

**依赖**：

---

## 执行顺序
1. T001 → T002 → ...

## 风险与缓解
| 风险 | 影响 | 概率 | 缓解措施 |
|---|---|---|---|
|  |  | 高/中/低 |  |

## 开放问题
- [ ] ...

## 变更记录
| 版本 | 日期 | 说明 |
|---|---|---|
| v0.1 | YYYY-MM-DD | 初始化 |
