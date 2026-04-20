# AGENTS.md

尽量用简体中文交流（除非涉及专业术语），禁止用 worktree。

---

## 一、当前阶段要读什么

**每次启动必读**：
1. `../lessons_learned.md` - 只读取硬规则部分
2. `./meta.yaml` - 获取当前 phase、focus_work_item、active_work_items

**按当前 phase 读取**（从 meta.yaml 的 phase 字段获取）：

**Proposal**：
- `spec.md` - 首次浏览读 Default Read Layer（到 `<!-- SKELETON-END -->`）；工作时填充 Intent、Proposal Coverage Map、Clarification Status（替换模板占位和示例）
- `spec-appendices/*` - 按需深入，但不能在 appendix 中定义正式 REQ/ACC/VO

**Requirements**：
- `spec.md` - 完整读取，填充 REQ-*、ACC-*、VO-*（替换模板占位）
- `spec-appendices/*` - 按需深入

**Design**：
- `spec.md` - 读取 approved requirements、acceptance、verification
- `design.md` - 首次浏览读 Default Read Layer（Goal/Scope Link、Architecture Boundary、Work Item Derivation、Design Slice Index）；工作时填充 Goal/Scope Link、Architecture Boundary、Work Item Derivation、Verification Design、Implementation Readiness Baseline（替换模板占位）
- `design-appendices/*` - 按需深入（通过 Design Slice Index）

**Implementation**：
- `work-items/<focus_work_item>.yaml` - 读取当前 WI 的 goal、allowed_paths、requirement_refs、acceptance_refs、verification_refs
- `design.md` - 读取当前 WI 对应的 design slice（通过 Design Slice Index）
- `spec.md` - 验证 REQ/ACC/VO 引用是否存在
- `contracts/*.md` - 如果当前 WI 的 contract_refs 非空，读取对应合约
- `testing.md` - 添加 branch-local 测试记录

**Testing**：
- `testing.md` - 添加 full-integration 测试记录
- `work-items/*.yaml` - 读取所有 work-items（Testing 阶段 verification gate 会检查 active_work_items 中所有 WI 的 approved acceptance）
- `spec.md` - 读取 approved acceptance 和 verification obligations
- `design.md` - 参考 Verification Design

**Deployment**：
- `deployment.md` - 填充 Deployment Plan、Verification Results、Acceptance Conclusion、Rollback Plan、Monitoring（替换模板占位）
- `testing.md` - 验证所有 approved acceptance 都有 test_scope=full-integration 且 result=pass 的记录

**说明**：
- 文档可能是模板内容（阶段刚开始）或已填充内容（阶段进行中），都要读取
- Default Read Layer 是快速索引，首次浏览时读取；工作时需要读取完整章节
- `focus_work_item` 为 null 时跳过 work-items 读取
- `contract_refs` 为空时跳过 contracts 读取
- appendices 按需深入，不是每次必读

---

## 二、什么时候必须停下

**范围越界**：
- 需要修改不在当前 WI 的 `allowed_paths` 中的文件 → 停止
- 需要修改 `forbidden_paths` 中的文件 → 停止
- 需要实现 `out_of_scope` 中的功能 → 停止
- 需要修改 frozen contract → 停止

**目标不清**：
- 目标/边界/验收不清楚 → 先问用户
- `spec.md` / `design.md` / `work-items/*.yaml` 之间描述不一致 → 先对齐
- 需要做产品判断（非纯工程判断）→ 先问用户
- `Clarification Status` 中有 open decision 影响当前动作 → 先澄清

**执行偏离**：
- 连续失败或复杂度超预期 → 停下重新规划
- 发现需要先回写权威文件（spec/design/testing/deployment）→ 停止当前任务，先更新文档
- 依赖 Work Item 尚未完成，但当前任务需要其结果 → 停止，等待依赖
- 测试失败且无法在当前 scope 内修复 → 回看 work-item.yaml，可能需要扩大 allowed_paths
- Proposal 阶段在 appendix 中定义正式 REQ/ACC/VO → 停止，只能在主文档中定义

---

## 三、核心原则

1. **先澄清再动手，偏了就停**：目标/边界/约束/风险/验收不清楚先问；范围变更必须说明代价并重新确认；执行中发现方向偏离、连续失败、或复杂度超预期，立即停下重新规划，不硬推。

2. **可验收可追溯**：需求有可判定验收标准（第三方可判 PASS/FAIL）；成功指标给出"基线→目标"；维护场景→需求→实现→验证追溯链。

3. **最小必要变更、始终可回滚**：只改必须改的；垂直切片优先；线上行为变化必须有回滚/开关/灰度方案。

4. **证据驱动、质量闭环**：关键结论附命令/环境/输出；完成前 diff 基线确认变更范围；合入前自测；缺陷立即处理并记录。

5. **安全合规优先**：最小权限、输入校验、密钥不落盘；新依赖需评估必要性与安全性。

6. **第一性原理**：拒绝经验主义和路径盲从，不要假设我完全清楚目标，应保持审慎；若目标模糊请停下和我讨论；若目标清晰但路径非最优，请直接建议路径更优的办法；任务澄清且明确无歧义之后就直接执行。

7. **冲突升级**：同一 concern 内冲突以后更新且证据充分的为准；跨 concern 冲突必须回写权威文件对齐（Spec/Design/Work Item/Testing/Deployment/Contract），必要时暂停并升级决策。

---

## 四、阶段切换前检查

**命令与 gate 映射**（runtime 会自动检查）：
- `codespec start-requirements` → 检查 `proposal-maturity`
- `codespec start-design` → 检查 `requirements-approval`
- `codespec start-implementation <WI-ID>` → 检查 `implementation-ready`
- `codespec start-testing` → 检查 `metadata-consistency` + `scope` + `contract-boundary` + `verification`
- `codespec start-deployment` → 检查 `trace-consistency` + `verification`
- `codespec complete-change` → 检查 `promotion-criteria`
- `codespec promote-version` → 检查 `promotion`

**说明**：
- gate 检查由 runtime 自动执行，失败会阻止阶段切换
- 手动检查：`codespec check-gate <gate-name>`
- 详细检查项：`codespec check-gate <gate-name> --verbose`

---

## 五、Compact Instructions 保留优先级

1. 架构决策，不得摘要
2. 已修改文件和关键变更
3. 验证状态，pass/fail
4. 未解决的 TODO 和回滚笔记
5. 工具输出，可删，只保留 pass/fail 结论

---
