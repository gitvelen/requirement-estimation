# 阶段2：需求编写 (Requirements)

## 目标
将提案转化为范围明确、可验收的技术需求

## 输入
- `docs/<版本号>/proposal.md`

## 输出
- `docs/<版本号>/requirements.md` — 需求规格说明

## 阶段入口协议（🔴 MUST，CC-7 程序化强制）

> 脚本单源：`scripts/lib/common.sh` 的 `aicoding_phase_entry_required`。以下表格为人类可读视图，以脚本为准。

> AI 进入本阶段后、开始产出前，**必须先读取**以下文件。CC-7 hook 会在 AI 首次写入产出物时检查是否已读取。

| 必读文件 | 用途 | 强制级别 |
|---------|------|---------|
| `docs/<版本号>/status.md` | 获取当前状态、Active CR、基线版本 | 🔴 CC-7 强制 |
| `docs/<版本号>/proposal.md` | 上一阶段产出（输入） | 🔴 CC-7 强制 |
| `.aicoding/phases/02-requirements.md` | 本阶段规则（本文件） | 🔴 CC-7 强制 |
| `.aicoding/templates/requirements_template.md` | 产出物模板 | 🔴 CC-7 强制 |
| `docs/系统功能说明书.md`（如存在） | 存量系统功能基线 | 🟡 推荐（CC-7 不强制） |

## 阶段开始时检查
- [ ] 确认 proposal.md 已完成并通过评审
- [ ] 确认当前变更目录存在

## 需求编写原则
```
┌─────────────────────────────────────────────────────────────┐
│  1. 需求必须是可验收的（Acceptable）                         │
│     - 避免"优化"、"提升"等模糊词汇                           │
│     - 使用具体数字、具体行为、具体结果                       │
│                                                              │
│  2. 需求必须是独立的（Independent）                          │
│     - 每条需求可单独开发和测试                               │
│                                                              │
│  3. 需求必须覆盖所有场景                                     │
│     - 正常场景                                               │
│     - 异常场景                                               │
│     - 边界场景                                               │
│                                                              │
│  4. 编写后必须走查                                           │
│     - 与用户逐条确认                                         │
│     - 检查遗漏和矛盾                                           │
│  5. 如果修改了 requirements.md，应形成修改记录，写明修改要点和修改章节 │
│  6. 已完成/已测试后出现新意图：优先写 CR（见 `phases/00-change-management.md`） │
└─────────────────────────────────────────────────────────────┘
```

## 分段走查协议（🔴 MUST）

> 来源：lessons_learned R1(遗漏用户反馈), R9(差异未确认)。
> Requirements 写完再一次性确认，用户面对 200+ 行文档难以逐条审。分段产出、逐段确认。

AI 编写 requirements 时，按以下顺序分段产出并逐段与用户确认：
1. §1（概述 + 术语 + 覆盖映射表）→ 用户确认
2. §2（业务场景）→ 用户确认
3. §3（功能性需求 + GWT）→ 用户确认
4. §4 + §4A（非功能 + 禁止项）→ 用户确认
5. §5-6（权限 + 数据接口）→ 用户确认

每段确认后才继续下一段。用户可以在任何一段要求修改。

## 覆盖映射强制要求（🔴 MUST，R5）

> Proposal → Requirements 的覆盖映射表（§1.4）为必填项，不再是"可选"。

- 每个 P-DO/P-DONT/P-METRIC 必须映射到至少一个 REQ-ID，或标注"defer + 原因"并回写 proposal Non-goals
- 门禁验证：已映射 + defer = proposal 锚点总数（无遗漏）

## 读取模板
编写需求时读取 `.aicoding/templates/requirements_template.md`。

如需初始化主文档，可参考 `.aicoding/templates/` 下的：
- `.aicoding/templates/master_system_function_spec_template.md`（对应 `docs/系统功能说明书.md`）

## 质量门禁
- [ ] 所有需求可验收
- [ ] 所有场景覆盖完整
- [ ] 与用户确认无误
- [ ] （如需要同步主文档）已追加/已更新主文档

## 完成条件（🔴 MUST）

### 审查要求
- 人工指定审查者：`@review Claude` 或 `@review Codex`
- 审查结果追加到 `review_requirements.md` 文件末尾
- 可多次指定不同审查者，直至问题收敛

### 覆盖性检查（R5）— 人工核对
**检查方式**：
1. 阅读 `proposal.md` 的 "### 包含" 章节
2. 逐项确认是否在 `requirements.md` 中有对应 REQ/API/验收
3. 未覆盖的项需要回写 `proposal.md` 的 Non-goals 或补充需求

### 一致性检查（R10）
**验证命令**：
```bash
rg -n "关键词1|关键词2" docs/<版本号>/requirements.md
```

### 人工确认
- [ ] 人工阅读 `review_requirements.md`
- [ ] 人工确认问题可接受
- [ ] `review_requirements.md` 包含“禁止项/不做项确认清单”章节（来源覆盖：对话中出现的不要/不做/禁止/不允许/不显示/不出现/不需要 + proposal.md Non-goals）
- [ ] 清单中每条禁止项已明确归类为二选一：A) 已固化为 `REQ-Cxxx`（requirements.md 中存在对应条目 + `GWT-ID`）或 B) 明确写入 Non-goals（含边界与原因）
- [ ] 清单中无 `TBD/待确认/unknown/...` 占位项
- [ ] 清单内包含机器可读块 `CONSTRAINTS-CHECKLIST-BEGIN/END`（门禁会校验 A/B 分类、来源引用、以及 REQ-C 映射完整性）
- [ ] `review_requirements.md` 末尾包含机器可读确认块，且 `CONSTRAINTS_CONFIRMED: yes`
- [ ] 人工确认进入 Design 阶段
- [ ] 更新 `status.md`：`_phase: Design`（并同步表格展示行"当前阶段"）

## 完成后
1. 确认质量门禁通过
2. 询问用户："需求已完成，是否进入 Design 阶段？"
3. 用户确认后，更新 `docs/<版本号>/status.md` 中的 `_phase` 为 Design（并同步表格展示行"当前阶段"；如未创建则先创建）
