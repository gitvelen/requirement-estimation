# v2.7 技术提案：系统画像域重构、Skill Runtime 与 Memory 资产层

## 文档元信息
| 项 | 值 |
|---|---|
| 版本号 | v2.7 |
| 文档版本 | v0.6 |
| 提案日期 | 2026-03-13 |
| 提案人 | User + Codex |
| 基线版本 | v2.6 |
| 变更级别 | major |
| 状态 | Review |

---

## 一句话总结
通过系统画像 5 域细粒度重构、PM 知识导入页瘦身、管理员服务治理/系统清单双导入入口、6 个内置 Skill、以及可扩展的 per-system memory 资产层，让系统具备“像 Codex 一样按目标调度 Skill”的能力，但不照搬 Codex/Claude 的产品形态。

---

## 背景与现状

### 现状问题
1. **画像模型粒度不足**：当前画像虽已升级为 5 域 12 子字段结构，但 D1/D3/D4 粒度仍不足，无法精确描述系统定位、集成关系和技术架构。
2. **PM 导入页职责混杂**：当前支持 5 种文档类型，历史评估报告与 ESB 服务治理文档不应继续由 PM 逐系统维护。
3. **管理员高价值导入资产没有闭环入画像**：管理员在服务治理页导入的文档、以及系统清单批量导入的数据，都包含大量可用于系统画像完善的高价值字段，但当前系统没有把它们作为画像更新资产统一利用。
4. **Skill 只是脚本，不是运行能力**：当前“不同文档类型的提取逻辑”散落在核心服务中，缺少类似 Codex 的目标驱动式运行能力，无法根据场景丝滑选择、串联和执行 Skill。
5. **缺少可积累的系统级 Memory**：系统画像更新、系统识别结论、AI 评估后的功能点修改没有沉淀为可复用资产，导致后续画像完善、系统识别和功能点拆解重复“从零开始”。

### 约束/前提
- 内网 LLM 模型口径固定为 `Qwen3-32B`（32K context）和 `Qwen3-Embedding-8B`
- v2.6 已实现 Token 感知分块机制，可复用
- 存量画像数据量有限，用户确认可接受直接清理、不迁移
- 服务治理导入模板和系统清单导入模板已存在，可复用现有批量导入链路
- v2.7 借鉴 Codex 的“Skill + Runtime + Memory + Policy”思路，但**不要求**照搬 Codex/Claude 的产品形态，也**不要求**把 Codex SDK 作为生产核心运行时

---

## 目标与成功指标

### 核心目标
将系统画像从“静态字段结构 + 零散导入逻辑”升级为“5 域结构化画像 + Skill Runtime + Per-System Memory 资产层”，让系统可以按场景自动调用合适 Skill，并把导入、识别、拆解中的高价值结论沉淀下来，持续提升系统画像质量与后续识别/拆解准确性。

### 成功指标
| ID | 指标定义（可判定） | 基线（v2.6） | 目标（v2.7） | 统计窗口 | 数据源 |
|---|---|---|---|---|---|
| M1 | 画像域字段覆盖度 | 5 域 12 子字段 | 5 域 ≥ 20 字段（含 `extensions`） | 上线时 | schema 对比 |
| M2 | PM 导入页文档类型数 | 5 种 | 3 种（需求/设计/技术方案） | 上线时 | 前端配置 |
| M3 | 服务治理导入→画像更新成功率 | 无此功能 | 对服务治理导入中系统名与系统清单标准名称一致的记录，自动匹配更新成功率 ≥ 95% | 测试阶段 | 测试日志 |
| M4 | Skill Runtime 覆盖率 | 0 | 6 个内置 Skill 全部注册、正确路由，并通过独立功能测试 | 测试阶段 | 注册表 + 功能测试 |
| M5 | Memory 写入覆盖率 | 0 | 系统画像更新、系统识别结论、AI 评估后功能点修改三类在范围内动作的 Memory 写入覆盖率 = 100% | 测试阶段 | Memory 日志 |
| M6 | 存量画像清理 | 旧 schema 数据残留 | 旧 schema 数据 = 0 | 上线时 | DB 查询 |

---

## 目标用户与典型场景

### 目标用户
- **产品经理（PM）**：导入需求/设计/技术方案文档，辅助完善系统画像，并在画像面板中复核 AI 建议
- **系统管理员（Admin）**：通过服务治理页导入治理文档、通过系统清单批量导入台账数据，并驱动全局系统画像更新
- **系统（后台 Runtime）**：按场景路由 Skill、读写 Memory、执行系统识别与功能点拆解中的策略判断

### TOP 场景
1. **PM 导入需求文档**：PM 上传需求文档 -> Runtime 路由 `requirements_skill` -> 生成结构化建议 -> 写入 Memory -> PM 复核并采纳/忽略
2. **Admin 导入服务治理文档**：Admin 在服务治理页上传治理文档/模板 -> Runtime 路由 `service_governance_skill` -> 以 D3 为主更新画像，并按语义对 D1/D4 形成小范围更新建议或草稿 -> 写入 Memory
3. **Admin 导入系统清单**：Admin 完成系统清单批量导入 preview/confirm -> Runtime 路由 `system_catalog_skill` -> 解析高价值字段，仅在首次初始化或目标画像全空时直接初始化画像，非空画像跳过 -> 写入 Memory
4. **系统识别与功能点拆解**：系统识别与功能点拆解在运行时读取系统画像和 Memory，优先做直接判断，再由 LLM 做补强，不再只依赖一次性的自由生成

---

## 方案概述

本次变更包含六个紧密关联的子方案：

### 子方案一：PM 知识导入页瘦身
- **做什么**：从 PM 导入页移除“历史评估报告”和“ESB/服务治理文档”两个文档类型；清理向量库中已有的历史评估报告数据
- **为什么**：PM 导入页应聚焦单系统知识导入，不再承接管理员治理入口
- **保留**：需求文档、设计文档、技术方案

### 子方案二：系统画像域重构（5 域）
- **做什么**：将现有 5 域 12 子字段扩展为 5 域 20+ 字段的结构化模型
- **为什么**：当前字段粒度不足以支撑系统识别、功能点拆解和跨来源知识融合
- **存量数据处理**：直接清理，不做迁移
- **扩展策略**：各域保留 `extensions` 字段

**新 5 域结构定义：**

| 域 | 域键 | 字段 | 类型说明 |
|---|---|---|---|
| D1 系统定位 | `system_positioning` | `system_type`, `business_domain`, `architecture_layer`, `target_users`, `service_scope`, `system_boundary`, `extensions` | 文本/列表 |
| D2 业务能力 | `business_capabilities` | `functional_modules`, `business_processes`, `data_assets`, `extensions` | 树形/列表 |
| D3 集成关系 | `integration_interfaces` | `provided_services`, `consumed_services`, `other_integrations`, `extensions` | 结构化表 |
| D4 技术架构 | `technical_architecture` | `architecture_style`, `tech_stack`, `network_zone`, `performance_baseline`, `extensions` | 分类结构 |
| D5 约束与风险 | `constraints_risks` | `technical_constraints`, `business_constraints`, `known_risks`, `extensions` | 列表 |

### 子方案三：管理员“服务治理”页
- **做什么**：新增管理员菜单“服务治理”，承接治理文档/模板导入
- **为什么**：服务治理数据是全局治理资产，应由 Admin 一次导入、批量更新相关系统画像
- **导入后行为**：
  - 以 D3 集成关系更新为主
  - 可基于语义对 D1/D4 做小范围更新，但必须遵守场景化策略，不得无条件覆盖
  - 输出匹配成功/未匹配统计，供管理员复核
- **合并策略**：merge 模式，`manual` 来源优先于自动更新

### 子方案四：管理员“系统清单导入”画像联动
- **做什么**：在系统清单批量导入 confirm 后，自动触发 `system_catalog_skill`
- **为什么**：系统清单中的标准名称、简称、归属、分类、状态、边界类字段对所有系统画像都极有价值
- **导入后行为**：
  - v2.7 仅保留单一系统清单模板与数据模型，不再区分主系统/子系统清单
  - 仅将高确定性字段初始化到 D1/D4 canonical；弱证据字段进入各域 `extensions`
  - `功能描述` 只初始化到 `D1.service_scope`，不拆分写入 D2
  - `关联系统` 仅进入 `D3.extensions.catalog_related_systems`，不直接写入 D3 canonical
  - 仅在系统首次初始化，或目标系统画像 `profile_data` 下 D1-D5 canonical 字段全部为空值/空数组/空对象时，才允许初始化命中系统画像
  - `field_sources`、`ai_suggestions`、Memory 记录不参与“空画像”判定
  - 目标画像已存在任一 canonical 内容时必须跳过，不覆盖，也不进入 PM 建议接受流

### 子方案五：Skill Runtime 平台
- **做什么**：建立一套类似 Codex 工作方式的 Skill Runtime，而不是只落几个 Skill 脚本
- **运行原则**：
  - 不照搬 Codex/Claude 的产品形态
  - 学习其“目标 -> 路由 -> 执行 -> 观察 -> 决策 -> 写回 Memory”的工作思路
- **核心组件**：
  - `Skill Registry`：管理 Skill 元数据
  - `Skill Router`：按场景、输入和目标选择 Skill
  - `Scene Executor`：支持多 Skill 串联执行
  - `Policy Gate`：决定 `auto_apply / draft_apply / suggestion_only / reject`
  - `Memory Reader/Writer`：在执行前检索上下文、执行后沉淀资产
- **v2.7 内置 Skill 清单**：
  1. `service_governance_skill`：管理员服务治理导入 -> D3 为主，允许小范围 D1/D4 语义更新
  2. `system_catalog_skill`：管理员系统清单导入 -> 初始化空画像或跳过非空画像
  3. `requirements_skill`：需求文档 -> D1/D2/D5 相关要素
  4. `design_skill`：设计文档 -> D2/D4/D5 相关要素
  5. `tech_solution_skill`：技术方案 -> D4/D5 相关要素
  6. `code_scan_skill`：复用现有代码扫描链路，支持 `repo_path` 与仓库压缩包双入口，对 Java/Spring Boot + JS/TS 执行中度语义扫描，输出 D4 现状与功能点拆解辅助上下文
- **每个 Skill 至少定义**：
  - `skill_id`
  - `skill_type`
  - `supported_inputs`
  - `supported_tasks`
  - `target_artifacts`
  - `execution_mode`
  - `decision_policy`
  - `version`

### 子方案六：Per-System Memory 资产层
- **做什么**：为每个系统增加 Memory 机制，形成可扩展的系统级资产沉淀
- **v2.7 必须沉淀的 Memory 类型**：
  - `profile_update`：系统画像更新记录，且按类型分类
  - `identification_decision`：系统识别结论与依据
  - `function_point_adjustment`：AI 评估后功能点修改记录，且按类型分类
- **使用方式**：
  1. **Direct Decision**：对别名、标准名称、高置信稳定映射、已确认调整模式做直接判断
  2. **Retrieval Context**：对复杂语义、相似历史修改、拆解边界提供上下文增强
- **扩展要求**：后续需求评审、架构评审等能力，应复用同一 Memory 元模型，而不是另起一套“专用临时表”

---

## 范围界定

### 包含（In Scope）
1. ✅ 画像数据模型重构（后端 `_empty_profile_data` + 前端 `PROFILE_DOMAIN_CONFIG`）
2. ✅ PM 导入页瘦身（移除历史评估报告和服务治理文档类型）
3. ✅ 向量库中历史评估报告数据清理
4. ✅ 存量画像数据清理（旧 schema -> 清空）
5. ✅ 新增管理员“服务治理”页（前端 + 后端 API）
6. ✅ 服务治理导入后以 D3 为主更新画像，并可对 D1/D4 做小范围语义更新
7. ✅ 系统清单导入 confirm 后仅初始化命中系统中的空画像，并跳过非空画像
8. ✅ 管理员系统清单能力收敛为单一系统清单模型，不再保留子系统清单概念
9. ✅ Skill Runtime 框架（Registry/Router/Scene Executor/Policy Gate/Memory）
10. ✅ 6 个内置 Skill 实现
11. ✅ Per-System Memory 资产层
12. ✅ 用 Memory 驱动系统画像完善、系统识别和功能点拆解
13. ✅ 系统识别输出 `matched / ambiguous / unknown` 直接判定
14. ✅ 场景化的画像更新与功能点拆解应用策略
15. ✅ 画像面板适配新 5 域结构
16. ✅ `source` / Memory 元数据追溯机制
17. ✅ 为未来需求评审、架构评审等 Skill 与 Memory 用法预留可扩展结构

### 不包含（Non-goals）
1. ❌ 存量画像数据迁移（用户确认直接清理）
2. ❌ 照搬 Codex/Claude 的产品 UI 形态
3. ❌ 将 Codex SDK 绑定为本系统生产核心运行时
4. ❌ 在 v2.7 内直接实现需求评审 Skill、架构评审 Skill 等未来能力
5. ❌ LLM 模型升级或更换
6. ❌ 评估算法整体变更
7. ❌ 用户权限体系改造（复用现有 admin/PM/expert 角色）
8. ❌ 服务治理/系统清单的手动映射界面（未匹配项通过修正模板重导解决）
9. ❌ 恢复主系统/子系统双清单模型或继续维护子系统映射

---

## 关键验收锚点（Proposal 阶段初步明确）

> 这些锚点会在 Requirements 阶段映射为正式的 `REQ/REQ-C/GWT`。
> `P-DO` / `P-DONT` / `P-METRIC` 仅用于 Proposal -> Requirements 的追溯对齐。

### 必须做到（Must Have）
- [ ] P-DO-01: PM 导入页仅保留需求文档、设计文档、技术方案三种文档类型
- [ ] P-DO-02: 画像数据模型重构为 5 域结构，各域字段与本提案“新 5 域结构定义”表一致
- [ ] P-DO-03: 各域预留 `extensions` 扩展字段
- [ ] P-DO-04: 新增管理员“服务治理”页，支持导入治理文档/模板并批量更新系统画像
- [ ] P-DO-05: 服务治理导入以 D3 为主更新画像，并允许对 D1/D4 做小范围语义更新
- [ ] P-DO-06: 新增系统清单导入后的画像联动能力，仅在系统首次初始化或目标画像全空时初始化命中系统画像
- [ ] P-DO-07: 建立 Skill Runtime 平台，至少包含 Registry、Router、Scene Executor、Policy Gate、Memory Reader/Writer
- [ ] P-DO-08: 实现 6 个内置 Skill（`service_governance_skill`、`system_catalog_skill`、`requirements_skill`、`design_skill`、`tech_solution_skill`、`code_scan_skill`）
- [ ] P-DO-09: 每个 Skill 显式定义 `skill_id/skill_type/supported_inputs/supported_tasks/target_artifacts/execution_mode/decision_policy/version`
- [ ] P-DO-10: Runtime 支持按场景串联 Skill，而不是只做单次脚本调用
- [ ] P-DO-11: 为每个系统沉淀 Memory，记录画像更新、系统识别结论、AI 评估后功能点修改，且按类型分类
- [ ] P-DO-12: Memory 必须运用在系统画像完善、系统识别和功能点拆解三个工作中
- [ ] P-DO-13: 系统识别结果必须直接输出 `matched / ambiguous / unknown`
- [ ] P-DO-14: 画像更新与功能点拆解结果的落地方式必须按场景区分 `auto_apply / draft_apply / suggestion_only / reject`
- [ ] P-DO-15: 存量画像数据和向量库中历史评估报告数据完成清理
- [ ] P-DO-16: 画像面板（前端）适配新 5 域结构展示

### 绝对不能出现（Prohibitions）
- [ ] P-DONT-01: 不得保留“历史评估报告”和“服务治理文档”在 PM 导入页
- [ ] P-DONT-02: 不得在画像数据中残留旧 schema 字段
- [ ] P-DONT-03: 自动导入或自动更新不得覆盖 PM 已确认的 `manual` 内容
- [ ] P-DONT-04: 不得把 Skill 和 Memory 设计成仅支持当前 6 个 Skill 与当前 3 类记忆用途的不可扩展结构
- [ ] P-DONT-05: 系统识别不得只给候选列表而不做直接判定
- [ ] P-DONT-06: 不得破坏现有评估流程（评估算法、评估报告生成等）
- [ ] P-DONT-07: 不得引入新的外部依赖（复用现有技术栈）
- [ ] P-DONT-08: 系统清单后续月度更新或覆盖导入不得覆盖非空画像；空画像判定仅看 `profile_data` 下 D1-D5 canonical 字段，忽略 `field_sources`、`ai_suggestions` 与 Memory

### 成功指标（可量化）
- [ ] P-METRIC-01: 画像域字段数 ≥ 20（含 `extensions`），基线 12 -> 目标 ≥ 20
- [ ] P-METRIC-02: PM 导入页文档类型 = 3 种，基线 5 -> 目标 3
- [ ] P-METRIC-03: 对服务治理导入中系统名与系统清单标准名称一致的记录，自动匹配更新成功率 ≥ 95%
- [ ] P-METRIC-04: 6 个内置 Skill 全部实现、正确路由，并通过独立功能测试
- [ ] P-METRIC-05: 系统画像更新、系统识别结论、AI 评估后功能点修改三类范围内动作的 Memory 写入覆盖率 = 100%
- [ ] P-METRIC-06: 存量旧 schema 画像数据 = 0

---

## 风险与依赖

### 风险评估
| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|---------|
| 画像 schema 变更导致前后端不一致 | 页面崩溃或数据丢失 | 中 | 前后端同步重构，统一 canonical schema；存量数据直接清理 |
| 服务治理和系统清单导入的字段口径不稳定 | 批量更新结果不一致 | 中 | 定义 skill 输入契约、字段映射、场景化策略和行级错误输出 |
| Skill Runtime 仍停留在“脚本集合”而非运行能力 | 无法丝滑调度，多场景难扩展 | 中 | 强制引入 Registry/Router/Scene Executor/Policy Gate/Memory 五件套 |
| Memory 写而不用，成为日志堆积 | 沉淀成本高但业务无收益 | 中 | 在 Requirements 阶段明确 Memory 的 direct decision / retrieval context 用法 |
| 系统识别或功能点拆解继续只依赖一次性 LLM 输出 | 结果不稳定、可复用性差 | 中 | 把直接判定和 Memory 约束前置，LLM 仅作为补强 |

### 依赖关系
- **内部依赖**：v2.6 Token 感知分块机制；现有系统清单导入链路；现有系统识别与功能点拆解链路
- **外部依赖**：无新增外部依赖

---

## 利益相关方（Stakeholders）
| 角色/团队 | 关注点 | 影响程度 | 沟通方式 |
|-----------|--------|---------|---------|
| 产品经理（PM） | 导入页变化、画像面板新结构、AI 建议/Memory 行为 | 高 | 需通知 |
| 系统管理员（Admin） | 服务治理页、系统清单导入后的画像联动、全局治理流程 | 高 | 需通知 |
| 专家（Expert） | 系统识别与功能点拆解引用的画像/Memory 口径、只读查询范围 | 中 | 需通知 |
| 运维团队 | 数据清理、批量导入与回滚策略 | 中 | 需通知 |

---

## 开放问题

> 所有条目必须在提交前标记状态。不得带未决问题进入下一阶段。

| # | 问题 | 状态 | 说明 |
|---|------|------|------|
| 1 | 存量画像数据如何处理？ | 已关闭 | 用户确认：直接清理，不迁移 |
| 2 | 服务治理导入与 PM 手动编辑冲突时如何处理？ | 已关闭 | 用户确认：merge 策略，`manual` 优先 |
| 3 | Skill 的运行方式是脚本集合还是像 Codex 一样的运行能力？ | 已关闭 | 用户确认：学习 Codex 思路，但不照搬产品形态；本次实现 Runtime 能力 |
| 4 | v2.7 Skill 实现范围？ | 已关闭 | 用户确认：6 个内置 Skill 全部在 v2.7 实现 |
| 5 | 系统识别结果是候选列表还是直接判定？ | 已关闭 | 用户确认：必须直接判定，允许保留候选作为解释，不得只有候选 |
| 6 | 画像更新与功能点拆解结果如何落地？ | 已关闭 | 用户确认：按场景区分，需给出可落地策略 |
| 7 | Memory 是否需要为未来需求评审、架构评审扩展？ | 已关闭 | 用户确认：必须按可扩展资产层设计 |

---

## 变更记录
| 版本 | 日期 | 说明 | 作者 |
|---|---|---|---|
| v0.1 | 2026-03-12 | 初始版本，基于用户讨论落盘四大诉求 | Claude |
| v0.2 | 2026-03-12 | 修复 Proposal 首轮审查问题：统一 Skill 写入模式口径、移除手动映射假设、校正 12 子字段基线并补齐状态同步依据 | Codex |
| v0.3 | 2026-03-13 | 按用户纠偏重开范围：修正 Skill 数量为 6，新增服务治理/系统清单双导入联动、Skill Runtime、Per-System Memory，以及系统识别/功能点拆解的场景化落地策略 | Codex |
| v0.4 | 2026-03-13 | 统一系统清单导入联动为“所有命中的系统画像”口径，并补充专家利益相关方 | Codex |
| v0.5 | 2026-03-13 | 按用户确认补充系统清单月度更新规则：仅在首次初始化或空画像场景下初始化画像，非空画像跳过且不进入 PM 建议流 | Codex |
| v0.6 | 2026-03-13 | 删除子系统清单口径，明确系统清单字段映射策略，并补充 `code_scan_skill` 双入口与中度语义扫描范围 | Codex |
