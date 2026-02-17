# Review Report：Design / v2.1

| 项 | 值 |
|---|---|
| 阶段 | Design |
| 版本号 | v2.1 |
| 日期 | 2026-02-12 |
| 基线版本（对比口径） | `v2.0` |
| 当前代码版本 | `f1646b5` |
| 复查口径 | full |
| Active CR（如有） | 无 |
| 检查点 | 需求追溯、接口契约、失败路径、兼容回滚、安全设计、可观测性 |
| 审查范围 | 文档：`docs/v2.1/design.md`、`docs/v2.1/requirements.md`、`docs/v2.1/status.md`；只读核对实现路径（system list 数据源相关模块） |
| 输入材料 | `docs/v2.1/design.md`、`docs/v2.1/requirements.md`、`docs/v2.1/status.md`、`backend/api/system_routes.py`、`backend/api/system_list_routes.py`、`backend/service/knowledge_service.py`、`backend/agent/system_identification_agent.py` |

## 结论摘要
- 总体结论：✅ 通过（Design 第 4 轮自审收敛）
- Blockers（P0）：0
- 高优先级（P1）：0
- 其他建议（P2+）：1

## 关键发现（按优先级）

### RVW-001（P2）建议在 Planning 阶段前置“系统清单数据源迁移验证脚本”
- 证据：
  - 设计已明确统一目标路径：`data/system_list.csv` 与 `data/subsystem_list.csv`（`docs/v2.1/design.md`）。
  - 现有代码仍包含 legacy 读取路径（根目录 `system_list.csv`、`backend/subsystem_list.csv`），需在实现中完成迁移与清理（`backend/api/system_routes.py`、`backend/api/subsystem_routes.py`、`backend/service/knowledge_service.py`、`backend/agent/system_identification_agent.py`）。
- 风险：
  - 若仅改 API 层而遗漏知识服务/系统识别链路，可能出现“页面可见、识别链路仍旧数据源”的口径分叉。
- 建议修改：
  - 在 `plan.md` 中新增独立任务：统一 4 个关键模块的系统清单读取路径，并附回归命令（含 `rg` 代码检索 + API 回归）。
- 验证方式（可复现）：
  - `rg -n "system_list\.csv|subsystem_list\.csv|CSV_PATH" backend/api/system_routes.py backend/api/subsystem_routes.py backend/service/knowledge_service.py backend/agent/system_identification_agent.py`

## 建议验证清单（命令级别）
- [ ] 追溯覆盖检查：`REQ_DEF=$(rg -o "REQ-[0-9]{3}" docs/v2.1/requirements.md | sort -u); REQ_MAP=$(rg -o "REQ-[0-9]{3}" docs/v2.1/design.md | sort -u); echo "$REQ_DEF" >/tmp/req_defs_v21.txt; echo "$REQ_MAP" >/tmp/req_map_v21.txt; comm -23 /tmp/req_defs_v21.txt /tmp/req_map_v21.txt; comm -13 /tmp/req_defs_v21.txt /tmp/req_map_v21.txt`
- [ ] 接口覆盖检查：`API_DEF=$(rg -o "API-00[1-7]" docs/v2.1/requirements.md | sort -u); API_DES=$(rg -o "API-00[1-7]" docs/v2.1/design.md | sort -u); echo "$API_DEF" >/tmp/api_defs_v21.txt; echo "$API_DES" >/tmp/api_des_v21.txt; comm -23 /tmp/api_defs_v21.txt /tmp/api_des_v21.txt; comm -13 /tmp/api_defs_v21.txt /tmp/api_des_v21.txt`
- [ ] 设计关键章节检查：`rg -n "^## 2\.1|^## 5\.3|^## 6\.1|^### 5\.8|REQ-10[1-5]|API-00[1-7]|幂等|回滚" docs/v2.1/design.md`
- [ ] 数据源迁移影响面检查：`rg -n "system_list\.csv|subsystem_list\.csv|CSV_PATH" backend/api/system_routes.py backend/api/subsystem_routes.py backend/service/knowledge_service.py backend/agent/system_identification_agent.py`

## 开放问题
- [ ] 无（Design 阶段阻塞项已收敛）

## 处理记录（建议由开发/人工填写）
| RVW-ID | 严重度 | 处理决策（Fix/Defer/Accept） | Owner | 说明 | 链接/证据 |
|---|---|---|---|---|---|
| RVW-001 | P2 | Defer | AI | 迁移验证脚本在 Planning 阶段落地，不阻塞 Design 收敛 | `docs/v2.1/design.md`、`docs/v2.1/plan.md`（待创建） |

## 2026-02-11 23:59 | 第 1 轮 | 审查者：AI（Codex）

### 审查角度
Design 阶段完整性与可落地性审查：重点核对需求追溯完整性、接口/数据模型一致性、失败路径与回滚可执行性、安全与可观测性是否满足进入 Planning 前置条件。

### 上一轮问题处理状态
| RVW-ID | 严重度 | 上一轮描述 | 处理方式 | 本轮状态 |
|---|---|---|---|---|
| - | - | 首轮审查，无历史问题 | - | - |

### 本轮新发现问题
| RVW-ID | 严重度 | 描述 | 证据 | 建议 |
|---|---|---|---|---|
| RVW-001 | P2 | 数据源迁移验证任务建议前置到 Planning | 设计文档与现有实现路径对照 | 在 `plan.md` 增加独立迁移与回归任务 |

### 收敛判定
- 本轮后：P0(open)=0, P1(open)=0
- 距离收敛：是
- 建议：✅ Design 已收敛，可进入 Planning 阶段


## 2026-02-12 00:03 | 第 2 轮 | 审查者：AI（Codex）

### 审查角度
追溯一致性复核：重点验证 `requirements.md` 与 `design.md` 的 REQ/API 全量对齐情况，确认无漏项/错项。

### 上一轮问题处理状态
| RVW-ID | 严重度 | 上一轮描述 | 处理方式 | 本轮状态 |
|---|---|---|---|---|
| RVW-001 | P2 | 数据源迁移验证任务建议前置到 Planning | Defer（Planning 阶段落地） | 持续有效，不阻塞 Design |

### 本轮新发现问题
| RVW-ID | 严重度 | 描述 | 证据 | 建议 |
|---|---|---|---|---|
| - | - | 未发现新增 P0/P1/P2 问题 | `REQ/API` 差异检查结果为空 | 继续保持 |

### 收敛判定
- 本轮后：P0(open)=0, P1(open)=0
- 距离收敛：是
- 建议：Design 维持收敛状态

## 2026-02-12 00:03 | 第 3 轮 | 审查者：AI（Codex）

### 审查角度
可落地性与风险复核：重点验证失败路径、回滚策略、安全章节以及“系统清单数据源统一”与现有实现差距是否被识别并纳入后续计划。

### 上一轮问题处理状态
| RVW-ID | 严重度 | 上一轮描述 | 处理方式 | 本轮状态 |
|---|---|---|---|---|
| RVW-001 | P2 | 数据源迁移验证任务建议前置到 Planning | Defer（Planning 阶段落地） | 持续有效，不阻塞 Design |

### 本轮新发现问题
| RVW-ID | 严重度 | 描述 | 证据 | 建议 |
|---|---|---|---|---|
| - | - | 未发现新增 P0/P1 问题 | 关键章节与实现差异核查完成 | 保持当前设计，进入 Planning 执行 |

### 收敛判定
- 本轮后：P0(open)=0, P1(open)=0
- 距离收敛：是
- 建议：✅ Design 已完成三轮自检并收敛，可进入 Planning 阶段

## 2026-02-12 00:05 | 第 4 轮 | 审查者：AI（Codex）

### 审查角度
按 `@review` 口径执行本阶段文档走查：重点核对 Design 与 Requirements 的追溯完整性、质量门禁章节完整性，以及已登记 defer 项是否仍可控。

### 上一轮问题处理状态
| RVW-ID | 严重度 | 上一轮描述 | 处理方式 | 本轮状态 |
|---|---|---|---|---|
| RVW-001 | P2 | 数据源迁移验证任务建议前置到 Planning | Defer（Planning 阶段落地） | 维持不变，不阻塞 Design |

### 本轮新发现问题
| RVW-ID | 严重度 | 描述 | 证据 | 建议 |
|---|---|---|---|---|
| - | - | 未发现新增 P0/P1 问题 | REQ/API 差异检查为空；Design 关键章节存在且可检索 | 保持当前结论，进入 Planning 执行 |

### 收敛判定
- 本轮后：P0(open)=0, P1(open)=0
- 距离收敛：是
- 建议：✅ Design 第 4 轮走查收敛，建议进入 Planning 阶段

## 2026-02-12 | 第 5 轮（独立审查者走查） | 审查者：AI（Claude / Opus 4.6）

### 审查角度
作为独立审查者（前 4 轮均为 Codex），对 Design v0.1 执行完整走查：需求追溯完整性、接口契约一致性、数据模型与迁移可行性、失败路径覆盖、安全设计、可观测性、代码证据核实。重点关注前 4 轮可能存在的审查盲区。

### 上一轮问题处理状态
| RVW-ID | 严重度 | 上一轮描述 | 处理方式 | 本轮状态 |
|---|---|---|---|---|
| RVW-001 | P2 | 数据源迁移验证任务建议前置到 Planning | Defer（Planning 阶段落地） | ✅ 维持有效，不阻塞 Design |

### 审查清单逐项确认

#### ✅ 需求追溯完整性
- 追溯矩阵（§2.1，行 100-128）：27/27 REQ 全覆盖（REQ-001~022 + REQ-101~105），每条均有设计落点与验收方式
- API 覆盖：API-001~007 在 §5.4（行 279-287）全部定义，与 requirements.md 一致
- 测试计划（§7.2，行 428-442）：12 条 TEST 覆盖全部 27 REQ
- 质量属性场景（§2.2，行 131-137）：5 条 Q-ID 覆盖幂等/兼容/可观测/安全/交互体验

#### ✅ 接口契约一致性
- API-001：PUT，actor 可选，忽略 remark，向后兼容 — 与 requirements API-001 一致
- API-002/003：PUT/GET，7→4 字段破坏性变更 — 与 requirements 一致，设计明确标注"破坏性"
- API-004：POST，扩展管理指标，移除 ai_involved — 与 requirements 一致
- API-005：GET，统一数据源 — 与 requirements 一致
- API-006：POST，task 维度幂等，异步，Flag 关闭返回 skipped — 与 requirements 一致
- API-007：GET，返回 3 个开关 — 与 requirements 一致

#### ✅ 数据模型与迁移
- 画像字段 7→4 收敛：设计明确"不做旧数据自动拼接"，迁移 SOP 7 项全部勾选（行 248-254）
- 修改记录 actor 字段：增量写入，旧记录允许缺失 — 向后兼容
- 系统清单迁移：legacy 路径 → `data/` 统一路径，回滚依赖快照恢复
- 回滚策略（§6.1.3）：关闭开关 → 回退版本 → 恢复快照，三步可执行

#### ✅ 失败路径覆盖
- 4 条失败路径（行 269-274）：重复触发/JSON 非法/无权限/模型失败，均有期望行为与兜底
- 重试与补偿（行 264-265）：幂等键 `task_id + running/pending job`，备注与重评估解耦

#### ✅ 安全设计
- STRIDE 简表（行 328-333）：4 条威胁/缓解，覆盖越权/非法输入/审计缺失/配置误用
- 敏感配置：JWT_SECRET/DASHSCOPE_API_KEY 仅在 `.env`，不入文档与日志
- 权限：画像写入仅 admin/主责/B角，默认拒绝

#### ✅ 可观测性
- 监控清单（行 314-318）：3 项指标（重评估失败率/看板查询 P95/系统清单空率），均有阈值与告警级别
- 日志字段（行 308）：task_id/job_id/actor_id/actor_role/activeRole/request_id

### 代码证据核实
| 设计声明 | 代码证据 | 状态 |
|---|---|---|
| EditPage 逐字段 PUT | `frontend/src/pages/EditPage.js:194-202` for 循环 `axios.put` | ✅ 确认 |
| system_routes CSV_PATH 指向根目录 | `backend/api/system_routes.py:37` `os.path.dirname` 三层上溯 | ✅ 确认 |
| knowledge_service 读 backend/system_list.csv | `backend/service/knowledge_service.py:74,95` base_dir=backend/ | ✅ 确认（路径分叉已识别） |
| system_identification_agent 读 backend/system_list.csv | `backend/agent/system_identification_agent.py:63,87` 同上 | ✅ 确认 |
| system_profile_routes 存在 | `backend/api/system_profile_routes.py:22` router 定义 | ✅ 确认 |
| 前端画像 7 字段 | `frontend/src/pages/SystemProfileBoardPage.js:28-36` fieldLabels 7 项 | ✅ 确认 |
| 现有 rebreakdown 端点可参考 | `backend/api/routes.py:1811` rebreakdown_system | ✅ 确认（API-006 可参考此模式） |
| V21_* Feature Flags 在 .env | .env/.env.backend 中未找到 V21_* 定义 | ⚠️ 见 RVW-002 |

### 本轮新发现问题
| RVW-ID | 严重度 | 描述 | 证据 | 建议 |
|---|---|---|---|---|
| RVW-002 | P2 | Feature Flag 环境变量尚未在 .env 中定义 | 检查 `.env` 和 `.env.backend` 均无 `V21_*` 条目；设计 §0.5 环境配置表（行 48-50）声明 Flag 存放于 `.env.backend` | 在 Planning/Implementation 阶段确保 `.env.backend` 和 `.env.example` 中补齐 `V21_AUTO_REEVAL_ENABLED=true`、`V21_AI_REMARK_ENABLED=true`、`V21_DASHBOARD_MGMT_ENABLED=true` 默认值 |

### 收敛判定
- 本轮后：P0(open)=0, P1(open)=0, P2(open)=1（RVW-002，不阻塞）
- 距离收敛：**是（已收敛）**
- 结论：Design v0.1 经过 5 轮审查（含 2 位独立审查者），RVW-001（P2 Defer）+ RVW-002（P2 新发现）均不阻塞收敛。追溯矩阵 27/27 REQ 全覆盖，7/7 API 全对齐，代码证据 7/8 确认（1 项为实现阶段补齐项）。**Design 阶段已收敛，可进入 Planning 阶段**。
