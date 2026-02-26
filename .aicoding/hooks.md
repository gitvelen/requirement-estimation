# Hooks 设计索引（V2）

> 本文档只保留“规则设计与索引”。
> 具体实现细节请查看 `hooks_implementation_reference.md` 与 `scripts/` 下实际脚本。

## 1. 设计目标
1. 关键质量门禁前置到可执行脚本（pre-commit）。
2. 入口/出口规则单源化（`scripts/lib/common.sh`）。
3. 将“提醒型规则”与“阻断型规则”分层。
4. 保留可审计的逃生通道检测（W24）。

## 2. 门禁分层
| 层级 | 载体 | 说明 |
|---|---|---|
| Hard Gate | `scripts/git-hooks/pre-commit` | 阻断提交，保障结构与结果正确性 |
| Soft Gate | `scripts/git-hooks/post-commit` | 输出告警，不阻断提交 |
| 协议提醒 | `scripts/cc-hooks/*` | 会话入口提示、读写引导、阶段辅助 |

## 3. 规则索引

### 3.1 pre-commit（硬门禁）
- status front matter 枚举与关键字段校验
- 阶段推进出口门禁（含 major/minor 分支）
- minor Testing 轮次结论门禁（`review_minor.md` 的 `MINOR-TESTING-ROUND` 块）
- hotfix 边界检查（文件数、REQ-C）
- 结果门禁（`result_gate_test/build/typecheck`，仅阶段推进 commit）
- requirements 结构完整性与引用一致性
- 交付关口条件校验

### 3.2 commit-msg（提交信息）
- 提交前缀格式校验（`feat/fix/docs/...`）
- Active CR 场景下的 CR-ID 映射校验

### 3.3 post-commit（软警告）
- 风险提示集合：`scripts/git-hooks/warnings/w*.sh`
- 当前基线约定：`post-commit（软警告脚本 21 个：W6–W22 + W25–W28；内置检查 W23/W24）`
- 逃生通道审计：W24（检测 pre-commit 通过证据缺失）

### 3.4 CC hooks（流程引导）
- `inject-phase-context.sh`：会话开始上下文注入
- `pre-write-dispatcher.sh`：PreToolUse 统一入口（合并 phase-gate / doc-scope-guard / phase-entry-gate / phase-exit-gate / review-append-guard）
- `doc-structure-check.sh`：PostToolUse（Write）文档结构校验
- `read-tracker.sh`：Read 路径追踪
- `stop-gate.sh`：Stop 时人工介入期收口校验

## 4. 单源定义
- `scripts/lib/common.sh`
  - `aicoding_phase_entry_required`
  - `aicoding_phase_exit_required`
  - `aicoding_config_value` / `aicoding_yaml_value`
  - `aicoding_precommit_evidence_matches_current_head`
- `scripts/lib/review_gate_common.sh`
  - 内容级校验单源（GWT 覆盖、摘要块验真、追溯校验）

## 5. 运维与审计
1. 安装：`bash scripts/install-hooks.sh`
2. 全量测试：`bash scripts/tests/run-all.sh`
3. 逃生审计：检查 `.git/aicoding/gate-warnings.log` 中的 W24
4. 严禁 AI 未授权使用 `--no-verify`

## 6. 兼容与演进
1. 关键门禁以 Git hooks 为最小闭环。
2. CI 上收由 `.github/workflows/quality-gates.yml` 承载。
3. 本文不重复粘贴脚本实现，避免文档与代码漂移。
