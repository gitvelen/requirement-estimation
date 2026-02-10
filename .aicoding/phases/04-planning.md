# 阶段4：任务计划 (Planning)

## 目标
生成可执行的开发任务清单

## 输入
- `docs/<版本号>/design.md`
- `docs/<版本号>/requirements.md`

## 输出
- `docs/<版本号>/plan.md` — 任务计划文档

## 阶段开始时检查
- [ ] 确认 design.md 已完成并通过评审
- [ ] 确认当前变更目录存在
- [ ] **CR感知检查（🔴 MUST，CR场景）**：
  - [ ] 读取 status.md 的 Active CR 列表
  - [ ] 读取每个 Active CR 的"变更点"和"影响面"
  - [ ] 将 CR 信息作为本阶段工作的输入

## 任务拆分原则
```
┌─────────────────────────────────────────────────────────────┐
│  1. 任务粒度适中                                             │
│     - 单个任务可在合理时间内完成                             │
│     - 任务之间依赖关系清晰                                   │
│                                                              │
│  2. 任务必须可验收                                           │
│     - 明确的完成定义                                         │
│     - 对应具体需求                                           │
│                                                              │
│  3. 任务之间无重叠                                           │
│     - 避免重复工作                                           │
│     - 职责边界清晰                                           │
│                                                              │
│  4. 考虑多Agent协作                                          │
│     - 可并行的任务                                           │
│     - 需要串行的依赖                                         │
│                                                              │
│  5. 指定执行角色（Owner）                                    │
│     - 单 Claude 场景可写"默认"或省略                         │
│     - 多 Agent 协作时明确指定每个任务的负责 Agent             │
│                                                              │
│  6. 指定复核角色（Reviewer）（可选但推荐）                    │
│     - 建议 P0/P1 任务指定复核Agent                           │
│     - 尽量与Owner不同                                       │
│                                                              │
│  7. 如果修改了 plan.md，应形成修改记录，写明修改要点和修改章节 │
│  8. 如有 CR：在 plan.md 中登记 CR-ID，并将任务关联 CR（见 `phases/00-change-management.md`） │
└─────────────────────────────────────────────────────────────┘
```

## 读取模板
编写计划时读取 `.aicoding/templates/plan_template.md`。

## 质量门禁
- [ ] 所有需求有对应任务
- [ ] 任务依赖关系正确
- [ ] 多 Agent 协作时每个任务已指定 Owner，单 Claude 可写"默认"或省略
- [ ] P0/P1 任务已指定复核角色（Reviewer）（可选但推荐）
- [ ] 可作为开发核对清单使用

## 完成条件（🔴 MUST，AI 自动判定）

### AI 自动审查收敛
- [ ] P0(open)=0, P1(open)=0（允许存在 P1 accept/defer）
- [ ] 单轮满足即收敛

### diff-only检查（🔴 MUST，有Active CR时）
- [ ] 如存在Active CR，执行diff-only审查增强（见 `.aicoding/templates/review_template.md` 附录 AC-05）
- [ ] 验证CR影响面与实际计划变更一致
- [ ] 如发现P1差异，必须修复后才能收敛（🔴 MUST）

> **执行入口（🔴 MUST）**：diff-only 检查步骤详见 `.aicoding/templates/review_template.md` 附录 AC-05，包含完整的 AI 执行命令、差异报告格式和级联影响分析。

### 引用存在性检查（R6）
**验证命令**（见 `.aicoding/templates/review_template.md` 附录 AC-03）：
```bash
VERSION="<版本号>"  # 替换为实际版本号

# 提取 plan.md 中的所有 REQ 引用
rg -o "REQ-[0-9]+" docs/${VERSION}/plan.md | LC_ALL=C sort -u > /tmp/plan_refs_${VERSION}.txt

# 提取 requirements.md 中定义的所有 REQ（只从定义行提取）
# 格式：#### REQ-001：[需求名称] → 提取 REQ-001
rg "^#### REQ-[0-9]+：" docs/${VERSION}/requirements.md | sed 's/^#### //;s/:.*//' | LC_ALL=C sort -u > /tmp/req_defs_${VERSION}.txt

# 计算差集（期望为空）
LC_ALL=C comm -23 /tmp/plan_refs_${VERSION}.txt /tmp/req_defs_${VERSION}.txt
```
**检查项**：所有 REQ-ID 都存在于 requirements.md 中（期望差集为空）。

### 收敛后自动推进
```text
✅ Planning AI 自动审查已收敛
▶️ 自动进入 Implementation 阶段
```

## 完成后
1. AI 自动推进到 Implementation 阶段
2. 用户可在 `status.md` 查看当前进度
