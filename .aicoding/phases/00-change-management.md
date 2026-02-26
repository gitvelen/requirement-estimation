# 通用：变更管理（CR / 基线 / 差异审查）

> 目的：在"已完成/已测试"的基础上出现新意图时，避免小改动触发全量返工，同时确保可追溯、可验收、可回滚。
> 通用 CR 规则见 `phases/cr-rules.md`。

## 适用场景
- 测试通过（但尚未合入主分支基线）后，用户提出新增/修改想法
- 任意阶段"已 Done/已评审通过"后，又出现范围调整/新增需求
- 线上（主分支基线）之后的增量迭代（v1 → v2）

> **存量项目启动新版本迭代**：此时 Phase 00 的作用是确认基线与变更范围（不要求创建 CR 文件）。CR 文件仅在"已完成/已测试后出现范围调整"时才需要。

## 核心约定
### 1) 基线（Baseline）必须明确
- **生产基线**：合入主分支（`main`/`master`）的发布点（建议打 tag，如 `v1.0`）
- **测试候选**：测试通过时可打 RC tag（如 `v2.0-rc1`），避免"测过哪一版"漂移
- 在 `docs/<版本号>/status.md` 填写：
  - 基线版本（对比口径）：`v1.0` 或 `<commit>`
  - 本次复查口径：`diff-only` / `full`

### 2) 新意图优先写 CR（不直接混改已测正文）
- 路径：`docs/<版本号>/cr/CR-YYYYMMDD-001.md`
- 模板：`.aicoding/templates/cr_template.md`
- 在 `status.md` 的 **Active CR 列表**登记 CR（含状态与链接）

### 3) 默认差异审查（diff-only），但门禁不降级
**diff-only** 的含义：只审 **Active CR + 受影响文件/模块/接口**，不强制全量重读全部阶段文档。

以下情形建议直接升级为 **full**（或至少加严清单）：
- API 契约变更（对外/对内接口、协议、错误码）
- 数据迁移/不可逆变更（表结构、迁移脚本、配置不可回滚）
- 权限/安全/合规（鉴权、越权、敏感数据、审计）
- 大范围行为改变（跨模块、核心路径、回归面不可控）

> 建议：在 CR 中勾选“强制清单触发”，并据此确定复查口径。

## 推荐流程（最小成本）
1. **记录意图**：新增 CR 文件（状态=Idea），写清：What / Impact / 验收 / 回滚
2. **需求澄清（🔴 MUST，Idea→Accepted 门禁）**：
   - AI 读取 CR 意图后，必须与用户做一轮结构化澄清对话：
     - 确认范围边界（做什么 / 不做什么）
     - 确认验收标准（GWT 是否完整、可判定）
     - 确认影响面（哪些模块/文档/接口受影响）
     - 确认风险与回滚（是否有不可逆操作）
   - 用户明确说"确认"后，CR 状态从 Idea → Accepted
   - **禁止跳过**：AI 不得在未与用户澄清的情况下直接将 CR 标记为 Accepted
3. **定范围**：在 `status.md` 更新 Active CR 与复查口径（diff-only/full）
4. **回填最少必要文档**：只更新受影响阶段产出（requirements/design/plan…），并在变更记录里引用 CR-ID
5. **实现与验证**：按 PR 流程提交；测试报告/回归范围必须覆盖 CR 影响点
6. **闭环**：CR 标记为 Implemented（或 Dropped），在 `status.md` 更新列表；必要时同步主文档清单（功能说明书/接口文档/用户手册/部署记录）

## 命名建议（可选）
- 分支：`cr/CR-YYYYMMDD-001-<short-name>`
- PR 标题/提交信息：包含 `CR-YYYYMMDD-001`

---

## 完成条件（🔴 MUST）

### 审查要求
- 人工指定审查者：`@review Claude` 或 `@review Codex`
- 审查结果追加到 `review_change_management.md` 文件末尾
- ChangeManagement 审查为自由格式；建议参考 `.aicoding/templates/review_template.md` 中 ChangeManagement 口径（至少写明问题清单、结论、审查者、时间）
- 可多次指定不同审查者，直至问题收敛

### 人工确认
- [ ] 人工阅读 `review_change_management.md`
- [ ] 人工确认问题可接受
- [ ] 人工确认进入下一阶段
- [ ] 更新 `status.md`：`_phase: <下一阶段>`（并同步表格展示行"当前阶段"）

> 提交期硬门禁：`pre-commit` 在 `ChangeManagement -> 下一阶段` 转换时会强制检查 `review_change_management.md` 存在。

---

## CR创建强制检查（🔴 MUST，P1）

### 基线验证

1. **AI从 status.md 读取 _baseline（唯一真相源）**
   ```bash
   # 从 status.md 可机读行读取基线
   BASELINE=$(grep "^_baseline:" docs/<版本号>/status.md | awk '{print $2}')
   ```

2. **AI将 _baseline 值自动填入CR的"基线版本"字段**

3. **AI验证基线版本是否存在**：
   ```bash
   # 支持tag、commit、branch验证
   git rev-parse --verify "${BASELINE}^{commit}" 2>/dev/null
   ```

4. **如基线不存在，拒绝创建CR**：
   ```text
   ❌ CR创建失败：基线版本 ${BASELINE} 不存在

   可用基线版本（tag）：
   - v1.0
   - v1.1
   - v2.0

   请选择有效基线或先创建基线tag。
   ```

### 基线一致性规则

- **CR 的基线版本必须与 status.md 的 _baseline 一致**
- 人工修改CR基线时，AI 检查是否与 status.md 一致
- **如不一致，门禁失败并提示**：
  ```text
  ❌ 基线版本不一致
  - CR基线版本：${CR_BASELINE}
  - status.md 基线：${STATUS_BASELINE}
  - 请确认是否需要同步更新
  ```

### 推荐基线创建时机

- 每次稳定 release 后创建 tag：`vN.M`（如 `v1.0`、`v1.1`、`v2.0`）

---

## CR合并、拆分、修订、暂停SOP（P1，参考）

> **详细操作流程见下方"CR合并、拆分、修订、暂停SOP"章节**

### CR合并

> **场景**：多个小 CR 依赖紧密，应合并为一个

**判断标准**：
- CR-A 的完成依赖 CR-B
- CR-A 和 CR-B 同时修改同一模块
- 合并后总工作量 < 分别实现工作量之和

**操作流程（使用关系字段）**：
1. 创建新 CR-C，状态设为 Accepted
2. CR-A 填写：Superseded by: CR-C，状态改为 Dropped
3. CR-B 填写：Superseded by: CR-C，状态改为 Dropped
4. CR-C 填写：Supersedes: CR-A, CR-B
5. CR-C 的 Impact 包含 CR-A/B 的所有影响

### CR拆分

> **场景**：大 CR 应拆分成多个小的

**判断标准**：
- 包含多个独立功能点
- 预估工期 > 2 周
- 不同功能点有不同的优先级

**操作流程（使用关系字段）**：
1. 创建多个子 CR（CR-X, CR-Y），状态设为 Accepted
2. 原大 CR 填写：Superseded by: CR-X, CR-Y，状态改为 Dropped
3. CR-X 填写：Parent CR: [原大CR编号]
4. CR-Y 填写：Parent CR: [原大CR编号]
5. 明确子 CR 之间的依赖关系（Depends on 字段）

### CR修订

> **场景**：实现时发现 CR 写错了

**操作流程**：
1. 在 CR 文件末尾追加"修订记录"章节
2. 记录：修订时间、原因、修订人、修订前/后内容
3. 如影响范围变化，更新 Impact 字段
4. 修订不改变 CR 状态，只记录变更历史

### CR暂停/挂起

> **场景**：CR 实现一半发现做不完

**操作流程**：
1. 在 status.md 中标记 CR 状态为 "Suspended"
2. 记录暂停原因
3. 如有部分代码，用 tag 保存临时状态
