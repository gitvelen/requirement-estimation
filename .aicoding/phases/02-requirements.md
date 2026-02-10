# 阶段2：需求编写 (Requirements)

## 目标
将提案转化为范围明确、可验收的技术需求

## 输入
- `docs/<版本号>/proposal.md`

## 输出
- `docs/<版本号>/requirements.md` — 需求规格说明

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
**验证命令**（见 `.aicoding/templates/review_template.md` 附录 AC-02）：
```bash
rg -n "关键词1|关键词2" docs/<版本号>/requirements.md
```

### 人工确认
- [ ] 人工阅读 `review_requirements.md`
- [ ] 人工确认问题可接受
- [ ] 人工确认进入 Design 阶段
- [ ] 更新 `status.md`：当前阶段 = Design

## 完成后
1. 确认质量门禁通过
2. 询问用户："需求已完成，是否进入 Design 阶段？"
3. 用户确认后，更新 `docs/<版本号>/status.md` 中的"当前阶段"为 Design（如未创建则先创建）
