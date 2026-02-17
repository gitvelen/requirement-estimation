# v2.1 多模块 UI/UX 优化与功能增强 需求说明书

| 项 | 值 |
|---|---|
| 状态 | Draft |
| 作者 | AI |
| 评审 | - |
| 日期 | 2026-02-11 |
| 版本 | v0.3 |
| 关联提案 | `docs/v2.1/proposal.md` v1.8 |

## 1. 概述

### 1.1 目的与范围
本文档将 `docs/v2.1/proposal.md`（v1.8）中的 A-01~A-09（UI/UX 优化）、B-01~B-06（功能增强）、C-01（Bug 修复）转化为可验收的技术需求。

**覆盖范围**：前端 9 个页面的 UI 精简、功能点编辑流程增强（自动重评估 + 备注自动生成）、系统画像字段重构（7→4）、修改记录增强、效能看板管理驱动型指标、系统清单数据源统一。

**不覆盖（Non-goals）**：
- 权限模型角色体系变更（保持 admin/manager/expert/viewer）
- 数据库存储方案变更（继续 JSON 文件存储）
- 新增页面或菜单项
- 报告生成逻辑、登录/认证流程
- AI 评估核心算法（COSMIC 规则引擎、LLM prompt 模板）
- 旧画像数据自动迁移（D-13）

### 1.2 背景、约束与关键假设
- **现状与痛点**：见 proposal.md 背景章节（7 项问题）
- **约束**：
  - 前端：React + Ant Design
  - 后端：FastAPI + JSON 文件存储
  - 除画像字段重构接口外，保持现有 API 向后兼容
  - v2.1 前后端同步发布
- **关键假设**：
  - 系统清单数据源为 `data/系统清单20260119.xlsx`，负责人字段格式为"A角"或"A角/B角"
  - v2.0 已有功能点级别修改记录机制（`data/task_modifications.json`）可复用
  - v2.0 已在首次 AI 评估完成时保存 `ai_initial_features` 快照

### 1.3 术语与口径

| 术语 | 定义 |
|------|------|
| PM | 项目经理（manager 角色） |
| 画像 | 系统画像（system profile），描述系统特征的结构化数据 |
| 画像字段（v2.1） | system_scope、module_structure、integration_points、key_constraints 共 4 个字段 |
| module_structure | 功能模块结构，结构化 JSON，记录模块→功能清单 |
| 实质性变更 | 新增/删除/修改功能点，新增/修改/删除系统 |
| 修正率 | PM 修改的功能点数（按功能点维度去重） / AI 初始功能点总数 |
| 新增率 | PM 新增的功能点数 / AI 初始功能点总数 |
| 知识命中率 | 有命中（hit_count>0）的检索次数 / 检索总次数（任务级别，近30天窗口） |
| 画像完整度 | code_scan(30) + esb(25) + documents(0~25) + module_structure(20) = 满分 100 |
| Feature Flag | 后端环境变量开关，控制 v2.1 新行为的启用/关闭 |

**ID 前缀规则**：
- REQ-0xx：功能性需求
- REQ-1xx：非功能需求
- SCN-0xx：业务场景
- API-0xx：接口变更

### 1.4 覆盖性检查说明（🔴 MUST，R5）

#### 参考记录
| Proposal In Scope | 对应 REQ | 验收标准 | 状态 |
|---|---|---|---|
| A-01 系统清单页面布局优化 | REQ-001 | 无 subtitle，Tab 顶部 | ✅ |
| A-02 规则管理页面简化 | REQ-002 | 无 subtitle，无多余按钮，按钮右下角 | ✅ |
| A-03 效能看板布局与权限优化 | REQ-003 | Tab 顶部，无视角/AI参与选择器，无 subtitle | ✅ |
| A-04 任务管理页面简化 | REQ-004 | 无 subtitle，详情保留摘要/分析/下载 | ✅ |
| A-05 功能点编辑页冗余文字清理 | REQ-005 | 无重复标题/Tag/统计标签 | ✅ |
| A-06 知识导入页面简化 | REQ-006 | 无 subtitle | ✅ |
| A-07 信息看板页面简化 | REQ-007 | 无 subtitle | ✅ |
| A-08 专家评估页布局优化 | REQ-008 | COSMIC 规则右上角，提示左下角，按钮右下角 | ✅ |
| A-09 全局冗余文字清理 | REQ-009 | 所有页面无流程路径说明/重复角色状态提示 | ✅ |
| B-01 功能点编辑后 AI 自动重评估 | REQ-010 | 保存后单次触发（API-006），幂等，按钮置灰，完成通知 | ✅ |
| B-02 备注字段 AI 自动生成 | REQ-011 | 只读展示，混合模式生成 | ✅ |
| B-03 功能点级别修改记录 | REQ-012 | 确认复用 v2.0 机制 | ✅ |
| B-04 系统画像重构 7→4 | REQ-013 | 4 字段模型，module_structure 自动沉淀 | ✅ |
| B-05 修改记录增强：操作人字段 | REQ-014 | actor_id + actor_role | ✅ |
| B-06 效能看板管理驱动型指标 | REQ-015~REQ-021 | 6 项指标 + AI 学习趋势 | ✅ |
| C-01 系统列表为空 Bug | REQ-022 | 系统清单唯一数据源，PM 可见系统 | ✅ |

## 2. 业务场景说明

### 2.1 角色与对象
- **角色**：项目经理（PM/manager）、专家（expert）、管理员（admin）、查看者（viewer）
- **对象**：任务（task）、功能点（feature）、系统画像（system profile）、系统清单（system list）、修改记录（modification）、效能指标（dashboard metric）

### 2.2 场景列表
| 场景分类 | 场景ID | 场景名称 | 场景说明 | 主要角色 |
|---|---|---|---|---|
| 功能点编辑 | SCN-001 | PM 编辑功能点后自动获得 AI 评估 | PM 修改功能点并保存，系统自动触发 AI 重评估 | PM |
| 功能点编辑 | SCN-002 | PM 新增系统后 AI 自动补充功能点 | PM 新增系统但未手工添加功能点，AI 自动补充 | PM |
| 知识导入 | SCN-003 | PM 快速进入知识导入 | PM 登录后进入知识导入页，直接看到负责的系统列表 | PM |
| 画像沉淀 | SCN-004 | PM 修正自动沉淀为系统知识 | PM 修正功能点后，模块结构自动更新到系统画像 | PM |
| 效能管理 | SCN-005 | 管理员通过效能看板驱动画像完善 | 管理员查看画像完整度排名，督促 PM 补充画像 | admin |
| 页面浏览 | SCN-006 | 用户浏览精简后的页面 | 所有角色访问页面时不再看到冗余文字和不合理布局 | 所有角色 |
| 专家评估 | SCN-007 | 专家高效完成评估 | 专家进入评估页，功能点表格为视觉焦点 | expert |

### 2.3 场景明细

#### SCN-001：PM 编辑功能点后自动获得 AI 评估
**场景分类**：功能点编辑
**主要角色**：PM
**相关对象**：任务、功能点、系统画像
**关联需求ID**：REQ-010、REQ-011、REQ-012、REQ-014
**前置条件**：
- PM 已登录，任务处于可编辑状态
- Feature Flag `V21_AUTO_REEVAL_ENABLED` = true
**触发条件**：
- PM 对功能点进行实质性变更（新增/删除/修改功能点）并点击保存
**流程步骤**：
1. PM 在功能点编辑页修改功能点内容
2. PM 点击保存，前端逐字段调用 PUT 接口落库
3. 后端记录修改记录（含 actor_id/actor_role）
4. 前端在所有字段保存完成后，调用 `POST /api/v1/tasks/{task_id}/reevaluate` 一次性触发异步重评估（API-006）
5. 前端显示"AI 正在重新评估中"提示，编辑/提交按钮置灰
6. AI 评估完成后，后端发送通知给 PM
7. 前端按钮恢复可用，PM 查看新评估结果
8. 后端在重评估完成后自动生成备注（只读），记录本次修改摘要
9. PM 确认保存后，后端自动提取模块结构更新到系统画像
**输出产物**：
- 更新后的功能点评估结果
- 修改记录（含操作人）
- 自动生成的备注
- 更新后的系统画像 module_structure
**异常与边界处理**：
- AI 评估期间 PM 不可编辑/提交，需等待完成
- Feature Flag 关闭时：不自动触发，保留/恢复手动触发入口

#### SCN-002：PM 新增系统后 AI 自动补充功能点
**场景分类**：功能点编辑
**主要角色**：PM
**关联需求ID**：REQ-010
**前置条件**：
- PM 已登录，任务处于可编辑状态
- Feature Flag `V21_AUTO_REEVAL_ENABLED` = true
**触发条件**：
- PM 新增系统后未手工添加功能点并保存
**流程步骤**：
1. PM 在编辑页新增一个系统
2. PM 未手工添加功能点即保存，前端逐字段调用 PUT 接口落库（新增系统）
3. 前端在所有字段保存完成后，调用 `POST /api/v1/tasks/{task_id}/reevaluate`（API-006）一次性触发评估流程
4. 后端检测到该系统无功能点，进入“补充功能点”模式：调用 AI 拆分生成该系统的功能点列表并写回任务数据
5. AI 完成后通知 PM，前端刷新展示 AI 自动生成的功能点列表
**输出产物**：
- AI 自动生成的功能点列表
**异常与边界处理**：
- 若 PM 已手工添加了功能点，则走 SCN-001 的自动重评估流程
- Feature Flag 关闭时：不自动补充功能点（回退到 v2.0 行为）

#### SCN-003：PM 快速进入知识导入
**场景分类**：知识导入
**主要角色**：PM
**关联需求ID**：REQ-022
**前置条件**：
- PM 已登录
- 系统清单中该 PM 为至少一个系统的主责/B角
**触发条件**：
- PM 进入知识导入页面
**流程步骤**：
1. PM 点击菜单进入知识导入页
2. 前端调用系统清单 API 获取系统列表
3. 前端通过 `filterResponsibleSystems()` 过滤出 PM 负责的系统
4. PM 在下拉列表中看到自己负责的系统
5. PM 选择系统后上传知识文档
**输出产物**：
- 系统下拉列表显示 PM 负责的系统（≥1 个）
**异常与边界处理**：
- 若 PM 不是任何系统的主责/B角，下拉列表为空并提示"暂无负责的系统"

#### SCN-004：PM 修正自动沉淀为系统知识
**场景分类**：画像沉淀
**主要角色**：PM
**关联需求ID**：REQ-013
**前置条件**：
- PM 已确认保存功能点编辑结果
**触发条件**：
- PM 点击确认保存
**流程步骤**：
1. PM 对功能点做了修正（重命名模块、新增功能点等）
2. PM 确认保存
3. 后端根据确认后的功能点列表，按"功能模块/功能点/业务描述"聚合生成 module_structure
4. 后端对该系统画像执行 upsert：新模块/功能新增，已有模块/功能更新 last_updated，已有 desc 若人工已补充则保留
5. 下次评估同一系统时，AI 自动获取最新 module_structure
**输出产物**：
- 更新后的系统画像 module_structure
**异常与边界处理**：
- 同模块内同名功能覆盖更新
- 人工已补充的 desc 优先保留（避免自动覆盖）

#### SCN-005：管理员通过效能看板驱动画像完善
**场景分类**：效能管理
**主要角色**：admin
**关联需求ID**：REQ-015~REQ-021
**前置条件**：
- 管理员已登录
- Feature Flag `V21_DASHBOARD_MGMT_ENABLED` = true
**触发条件**：
- 管理员打开效能看板
**流程步骤**：
1. 管理员打开效能看板，查看"系统影响"页签中的画像完整度排名
2. 发现某系统完整度低且 AI 命中率也低
3. 管理员通知该系统的 PM 补充画像
4. PM 导入文档、完善模块结构
5. 下次评估该系统时 AI 修正率下降，排名改善
**输出产物**：
- 画像完整度排名、PM 修正率排行、AI 命中率排行等指标
**异常与边界处理**：
- 系统/PM 维度排名需至少 3 条已完成任务才有统计意义，不足时显示"数据不足"

#### SCN-006：用户浏览精简后的页面
**场景分类**：页面浏览
**主要角色**：所有角色
**关联需求ID**：REQ-001~REQ-009
**前置条件**：
- 用户已登录
**触发条件**：
- 用户访问任意页面
**流程步骤**：
1. 用户访问页面，不再看到冗余的 subtitle、流程路径说明、重复角色/状态提示
2. 效能看板 Tab 在顶部，视角按 activeRole 自动决定
3. 专家评估页功能点表格为视觉焦点
**输出产物**：
- 精简后的页面
**异常与边界处理**：
- 无

#### SCN-007：专家高效完成评估
**场景分类**：专家评估
**主要角色**：expert
**关联需求ID**：REQ-008
**前置条件**：
- 专家已登录，已被分配评估任务
**触发条件**：
- 专家进入评估页
**流程步骤**：
1. 专家进入评估页，功能点表格占据主要空间
2. COSMIC 规则折叠面板在右上角，需要时展开参考
3. 提示文字在左下角，不干扰主流程
4. 完成评估后点击右下角"提交评估"
**输出产物**：
- 专家评估结果
**异常与边界处理**：
- 无

## 3. 功能性需求（Functional Requirements）

> **优先级说明**：M=Must（必须交付）、S=Should（应该交付）、C=Could（可以交付）、W=Won't（本次不做）。

### 3.1 功能性需求列表
| 需求分类 | REQ-ID | 需求名称 | 优先级 | 需求说明 | 关联场景 |
|---|---|---|---|---|---|
| UI 精简 | REQ-001 | 系统清单页面布局优化 | M | 删除 subtitle，Tab 置顶 | SCN-006 |
| UI 精简 | REQ-002 | 规则管理页面简化 | M | 删除 subtitle 和多余按钮，按钮移至右下角 | SCN-006 |
| UI 精简 | REQ-003 | 效能看板布局与权限优化 | M | Tab 顶部，移除视角/AI参与选择器，删除 subtitle | SCN-006 |
| UI 精简 | REQ-004 | 任务管理页面简化 | M | 删除 subtitle，简化详情 | SCN-006 |
| UI 精简 | REQ-005 | 功能点编辑页冗余文字清理 | M | 删除重复标题/Tag/统计标签 | SCN-006 |
| UI 精简 | REQ-006 | 知识导入页面简化 | M | 删除 subtitle | SCN-006 |
| UI 精简 | REQ-007 | 信息看板页面简化 | M | 删除 subtitle | SCN-006 |
| UI 精简 | REQ-008 | 专家评估页布局优化 | M | COSMIC 规则右上角，提示左下角，按钮右下角 | SCN-007 |
| UI 精简 | REQ-009 | 全局冗余文字清理 | M | 所有页面清理流程路径说明和重复提示 | SCN-006 |
| 功能增强 | REQ-010 | 功能点编辑后 AI 自动重评估 | M | 保存后自动触发 AI 重评估 | SCN-001, SCN-002 |
| 功能增强 | REQ-011 | 备注字段 AI 自动生成（只读） | M | 备注由 AI 生成，前端只读 | SCN-001 |
| 功能增强 | REQ-012 | 功能点级别修改记录确认 | S | 确认 v2.0 机制满足 B-06 需求 | SCN-001 |
| 功能增强 | REQ-013 | 系统画像重构（7→4 字段） | M | 画像字段收敛，新增 module_structure | SCN-004 |
| 功能增强 | REQ-014 | 修改记录增强：操作人字段 | M | 补充 actor_id/actor_role | SCN-001 |
| 效能看板 | REQ-015 | 画像完整度排名 + 过期预警 | M | 按完整度排名，低分标红，过期标注 | SCN-005 |
| 效能看板 | REQ-016 | PM 修正率排行（按系统） | M | 修正率/新增率 Top N | SCN-005 |
| 效能看板 | REQ-017 | AI 命中率排行（按系统） | M | 按系统拆分命中率排名 | SCN-005 |
| 效能看板 | REQ-018 | 评估周期排行（按 PM） | M | 创建→确认平均周期排名 | SCN-005 |
| 效能看板 | REQ-019 | 画像贡献度排行（按 PM） | S | PM 对画像的贡献统计 | SCN-005 |
| 效能看板 | REQ-020 | AI 工作量偏差监控（按系统） | M | AI vs 专家工作量偏差 | SCN-005 |
| 效能看板 | REQ-021 | AI 学习趋势 | S | 同系统多次评估修正率变化 | SCN-005 |
| Bug 修复 | REQ-022 | 系统清单数据源统一 | M | 废弃 legacy CSV，统一数据源 | SCN-003 |

### 3.2 功能性需求明细

---

#### REQ-001：系统清单页面布局优化
**目标/价值**：减少认知负担，提升操作效率
**入口/触发**：用户访问系统清单页面
**前置条件**：用户已登录
**主流程**：
1. 删除 PageHeader 的 subtitle "统一维护标准主系统清单与子系统映射关系"
2. "主系统清单"和"子系统映射"Tab 直接置于页面顶部
**页面与交互**：
- 涉及页面：`SystemListConfigPage.js`
- 关键交互：Tab 切换位置从 PageHeader 内移至页面顶部
**验收标准**：
- [ ] Given 用户访问系统清单页面，When 页面加载完成，Then PageHeader 无 subtitle 文字
- [ ] Given 用户访问系统清单页面，When 页面加载完成，Then "主系统清单"和"子系统映射"Tab 位于页面顶部
**关联**：SCN-006

---

#### REQ-002：规则管理页面简化
**目标/价值**：减少视觉噪音，操作按钮集中
**入口/触发**：用户访问规则管理页面
**前置条件**：用户已登录
**主流程**：
1. 删除 subtitle "用业务语言先理解'拆分粒度与计数口径'，技术配置按分类平铺展示。"
2. 删除"重新加载（热更新）"和"刷新"按钮
3. "保存配置"和"重置为默认"按钮移至页面右下角
**页面与交互**：
- 涉及页面：`CosmicConfigPage.js`
- 关键交互：按钮位置调整到右下角
**验收标准**：
- [ ] Given 用户访问规则管理页面，When 页面加载完成，Then 无 subtitle 文字
- [ ] Given 用户访问规则管理页面，When 页面加载完成，Then 不存在"重新加载（热更新）"和"刷新"按钮
- [ ] Given 用户访问规则管理页面，When 页面加载完成，Then "保存配置"和"重置为默认"按钮位于页面右下角
**关联**：SCN-006

---

#### REQ-003：效能看板布局与权限优化
**目标/价值**：顶部 Tab 更符合浏览习惯，视角由角色自动决定
**入口/触发**：用户访问效能看板页面
**前置条件**：用户已登录
**主流程**：
1. "总览/排行榜/AI表现/系统影响/流程健康"Tab 从左侧菜单移至顶部，与"时间范围"筛选器同行
2. 移除"视角"选择器，按当前 `activeRole` 自动展示对应视角数据
3. 移除"AI参与"过滤选项
4. 删除 subtitle "统一口径展示趋势、排行与任务下钻"
**页面与交互**：
- 涉及页面：`EfficiencyDashboardPage.js`
- 关键交互：Tab 从左侧垂直布局改为顶部水平布局；视角自动按 activeRole 决定（manager→owner, expert→expert, 其他→executive）
**业务规则**：
- 视角映射：activeRole=manager → perspective=owner；activeRole=expert → perspective=expert；其他 → perspective=executive
- 后端 dashboard query 接口的 `perspective` 参数由前端根据 activeRole 自动填充，不再由用户手动选择
**验收标准**：
- [ ] Given 用户访问效能看板，When 页面加载完成，Then 5 个 Tab 位于页面顶部水平排列
- [ ] Given 用户访问效能看板，When 页面加载完成，Then 不存在"视角"选择器
- [ ] Given 用户访问效能看板，When 页面加载完成，Then 不存在"AI参与"过滤选项
- [ ] Given PM 角色访问效能看板，When 查询数据，Then perspective 自动为 owner
- [ ] Given 用户访问效能看板，When 页面加载完成，Then 无 subtitle 文字
**关联**：SCN-006

---

#### REQ-004：任务管理页面简化
**目标/价值**：减少信息过载
**入口/触发**：用户访问任务管理页面
**前置条件**：用户已登录
**主流程**：
1. 删除 subtitle "当前视角：项目经理"（及其他角色的类似文字）
2. 任务详情简化：保留摘要、分析和相关文档报告下载，各卡片布局合理
**页面与交互**：
- 涉及页面：`TaskListPage.js`
- 关键交互：任务详情展开后仅显示摘要、分析、文档报告下载
**验收标准**：
- [ ] Given 用户访问任务管理页面，When 页面加载完成，Then 无"当前视角：XXX"类 subtitle
- [ ] Given 用户展开任务详情，When 详情加载完成，Then 仅显示摘要、分析和文档报告下载
**关联**：SCN-006

---

#### REQ-005：功能点编辑页冗余文字清理
**目标/价值**：消除与 PageHeader 重复的信息
**入口/触发**：PM 访问功能点编辑页
**前置条件**：PM 已登录，任务处于可编辑状态
**主流程**：
1. 删除页面顶部的"功能点编辑"标题（与 PageHeader 重复）
2. 删除"编辑中"状态 Tag
3. 删除"功能点总数"和"总工作量（人天）"统计标签
**页面与交互**：
- 涉及页面：`EditPage.js`
**验收标准**：
- [ ] Given PM 访问功能点编辑页，When 页面加载完成，Then 不存在重复的"功能点编辑"标题
- [ ] Given PM 访问功能点编辑页，When 页面加载完成，Then 不存在"编辑中"状态 Tag
- [ ] Given PM 访问功能点编辑页，When 页面加载完成，Then 不存在"功能点总数"和"总工作量（人天）"统计标签
**关联**：SCN-006

---

#### REQ-006：知识导入页面简化
**目标/价值**：移除内部设计文档内容
**入口/触发**：用户访问知识导入页面
**主流程**：
1. 删除 subtitle "配置管理 → 系统画像 → 知识导入（不展示导入历史/最近任务列表，仅反馈当前操作结果）"
**页面与交互**：
- 涉及页面：`SystemProfileImportPage.js`
**验收标准**：
- [ ] Given 用户访问知识导入页面，When 页面加载完成，Then 无 subtitle 文字
**关联**：SCN-006

---

#### REQ-007：信息看板页面简化
**目标/价值**：移除内部设计文档内容
**入口/触发**：用户访问信息看板页面
**主流程**：
1. 删除 subtitle "配置管理 → 系统画像 → 信息看板（可编辑7字段、完整度分析、保存草稿/发布）"
**页面与交互**：
- 涉及页面：`SystemProfileBoardPage.js`
**验收标准**：
- [ ] Given 用户访问信息看板页面，When 页面加载完成，Then 无 subtitle 文字
**关联**：SCN-006

---

#### REQ-008：专家评估页布局优化
**目标/价值**：让功能点表格成为视觉焦点
**入口/触发**：专家访问评估页
**前置条件**：专家已登录，已被分配评估任务
**主流程**：
1. "COSMIC简明规则（只读）"折叠面板移至右上角
2. 灰色提示文字（"灰色数值为AI预估…"、"任务：- ｜ 当前轮次：1 ｜ 系统：…"）移至左下角
3. "提交评估"和"返回列表"按钮移至右下角
**页面与交互**：
- 涉及页面：`EvaluationPage.js`
- 关键交互：COSMIC 规则为折叠面板，默认收起；功能点表格占据页面主要空间
**验收标准**：
- [ ] Given 专家访问评估页，When 页面加载完成，Then COSMIC 规则折叠面板位于右上角
- [ ] Given 专家访问评估页，When 页面加载完成，Then 灰色提示文字位于左下角
- [ ] Given 专家访问评估页，When 页面加载完成，Then "提交评估"和"返回列表"按钮位于右下角
- [ ] Given 专家访问评估页，When 页面加载完成，Then 功能点表格占据页面主要空间（视觉焦点）
**关联**：SCN-007

---

#### REQ-009：全局冗余文字清理
**目标/价值**：所有页面保持简洁
**入口/触发**：用户访问任意页面
**主流程**：
1. 全面检查所有页面，清理以下类型的冗余文字：
   - PageHeader subtitle 中的流程路径说明（含"→"的描述）
   - 重复的角色/状态提示
   - 与 PageHeader 重复的标题/标签
**业务规则**：
- 检查范围：所有 23 个前端页面
- 判定标准：出现流程路径说明（含"→"）、重复状态/角色提示即为冗余
**验收标准**：
- [ ] Given 逐一访问所有页面，When 检查 PageHeader subtitle，Then 不存在含"→"的流程路径说明
- [ ] Given 逐一访问所有页面，When 检查页面内容，Then 不存在重复的角色/状态提示文字
**关联**：SCN-006

---

#### REQ-010：功能点编辑后 AI 自动重评估
**目标/价值**：消除 PM 手动判断是否需要重评估的认知负担，确保工作量数据始终与功能点一致
**入口/触发**：PM 在功能点编辑页保存实质性变更
**前置条件**：
- PM 已登录，任务处于可编辑状态
- Feature Flag `V21_AUTO_REEVAL_ENABLED` = true
**主流程**：
1. PM 对功能点进行实质性变更（新增/删除/修改功能点，新增/修改系统）并保存
2. 前端逐字段调用 `PUT /api/v1/requirement/features/{task_id}` 落库（现有保存逻辑不变），后端**仅持久化变更与记录修改**，不触发重评估
3. 前端在所有字段保存完成后，调用 `POST /api/v1/tasks/{task_id}/reevaluate` **一次性触发**异步重评估（API-006）
4. 后端校验幂等：同一 task 同时只允许 1 个重评估任务运行，重复请求返回已有 job 状态（不产生新评估）
5. 前端收到"评估中"状态，显示"AI 正在重新评估中"提示
6. 前端将编辑/提交等按钮置灰不可用
7. AI 评估完成后，后端通过通知机制通知 PM
8. 前端按钮恢复可用，PM 查看新评估结果
9. 后端在重评估完成后自动生成备注（一次保存动作仅生成一条备注摘要）
10. PM 对 AI 评估结果确认保存后才能提交管理员
**输入/输出**：
- 输入：功能点变更内容（operation: add/update/delete, 变更字段与值）
- 输出：更新后的功能点评估结果（含 AI 重新评估的工作量）
**业务规则**：
- "实质性变更"定义：新增/删除/修改功能点内容（功能模块、功能点名称、业务描述、复杂度等），新增/修改/删除系统
- **重评估触发边界**：一次"保存"动作无论包含多少字段变更，**最多触发 1 次**重评估；保存接口（PUT）仅落库，重评估由独立接口（POST reevaluate）触发
- **幂等策略**：后端对同一 task 同时只允许 1 个重评估任务；重复点击保存/网络重试调用 reevaluate 接口时，返回已有 job 状态，不产生重复评估
- 若 PM 新增系统后未手工添加功能点：由 API-006 在评估流程中检测“系统无功能点”并自动进入“补充功能点”模式（SCN-002）
- 评估期间不设超时，等待完成即可（D-01）
- Feature Flag 关闭时：不自动触发，保留/恢复手动触发入口（"重新评估"按钮）
**异常与边界**：
- AI 评估期间 PM 关闭页面后重新打开：检查任务评估状态，若仍在评估中则继续显示提示和置灰按钮
- AI 评估失败：通知 PM 评估失败，按钮恢复可用，PM 可手动重试
- 前端保存部分字段成功、部分失败时：
  - 不调用 API-006（不触发重评估/补充功能点）
  - **不回滚**已成功保存的字段（降低复杂度）；提示用户"部分字段保存失败，请重试"
**验收标准**：
- [ ] Given PM 修改 3 个字段并保存，When Feature Flag 开启，Then 前端发出 3 次 PUT（落库）+ 1 次 POST reevaluate（触发评估），后端仅执行 1 次重评估
- [ ] Given PM 快速连续点击保存 2 次，When 第 2 次调用 reevaluate，Then 后端返回已有 job 状态，不产生第 2 次评估
- [ ] Given AI 正在评估中，When PM 查看编辑页，Then 显示"AI 正在重新评估中"提示且编辑/提交按钮置灰
- [ ] Given AI 评估完成，When PM 查看编辑页，Then 按钮恢复可用且显示新评估结果
- [ ] Given AI 评估完成，When 系统发送通知，Then PM 收到评估完成通知
- [ ] Given PM 新增系统但未添加功能点，When 保存，Then AI 自动补充功能点
- [ ] Given 前端 3 次 PUT 中第 2 次失败，When 保存结束，Then 不触发 API-006 且已成功保存的字段不回滚，提示"部分字段保存失败，请重试"
- [ ] Given Feature Flag 关闭，When PM 保存变更，Then 不自动触发，显示手动"重新评估"按钮
- [ ] Given PM 未确认 AI 评估结果，When PM 尝试提交管理员，Then 提交被阻止
**关联**：SCN-001, SCN-002；API-001, API-006

---

#### REQ-011：备注字段 AI 自动生成（只读）
**目标/价值**：统一备注格式，确保修改历史可追溯
**入口/触发**：`V21_AI_REMARK_ENABLED=true` 时自动触发（触发时机见业务规则）
**前置条件**：
- Feature Flag `V21_AI_REMARK_ENABLED` = true
**主流程**：
1. PM/专家对功能点进行变更并保存（PUT 落库与记录修改）
2. 前端在一次保存动作结束后调用 API-006（触发重评估或仅生成备注）
3. 后端根据本次变更内容自动生成备注（见触发时机）
4. 备注追加到功能点的备注字段，前端只读展示
**输入/输出**：
- 输入：本次变更的功能点列表、操作类型、操作人信息
- 输出：自动生成的备注文本
**业务规则**：
- **触发时机（与 REQ-010/API-006 对齐）**：
  - 当 `V21_AUTO_REEVAL_ENABLED=true`：备注在 API-006 触发的重评估 job **完成后**生成；一次保存动作最多生成 1 条备注摘要
  - 当 `V21_AUTO_REEVAL_ENABLED=false` 且 `V21_AI_REMARK_ENABLED=true`：备注在一次保存动作结束后生成（API-006 不触发重评估，仅生成备注并返回 `status=skipped`）
- **幂等**：同一保存动作重复调用 API-006 不生成重复备注；无新增修改记录时不生成新备注
- **生成方式（混合模式）**：
  - 简单变更（单次保存中变更功能点数 < 5 且不涉及模块级变更）：规则拼接
    - 格式：`[PM 张三] 新增功能点2个，修改模块名1处`
  - 复杂变更（单次保存中变更功能点数 ≥ 5，或涉及模块级变更：新增/删除/重命名模块）：调用 LLM 生成自然语言摘要
- 前端备注字段为只读展示，用户可查看但不可编辑
- 后端忽略/拒绝客户端写入 `备注/remark` 字段（仅服务端生成）
- Feature Flag 关闭时：备注恢复为可编辑（沿用 v2.0 行为）
- 迁移时保留历史备注，新备注由 AI 生成
**异常与边界**：
- LLM 调用失败时：降级为规则拼接模式
- 备注内容过长时：截断到合理长度（如 500 字符）
**验收标准**：
- [ ] Given PM 修改 3 个功能点并保存，When 备注生成，Then 使用规则拼接格式
- [ ] Given PM 修改 5 个功能点并保存，When 备注生成，Then 调用 LLM 生成自然语言摘要
- [ ] Given PM 重命名模块并保存，When 备注生成，Then 调用 LLM 生成（模块级变更）
- [ ] Given 备注已生成，When PM 查看功能点编辑页，Then 备注字段为只读
- [ ] Given 客户端尝试写入 remark 字段，When 后端接收请求，Then 忽略客户端写入的 remark 值
- [ ] Given `V21_AUTO_REEVAL_ENABLED=false` 且 `V21_AI_REMARK_ENABLED=true`，When PM 保存变更结束，Then 不触发重评估但生成 1 条备注摘要
- [ ] Given Feature Flag 关闭，When PM 查看编辑页，Then 备注字段可编辑（v2.0 行为）
**关联**：SCN-001；API-001, API-006

---

#### REQ-012：功能点级别修改记录确认
**目标/价值**：确认 v2.0 已有机制满足 B-06 指标分析需求
**入口/触发**：功能点变更保存时
**主流程**：
1. 确认 v2.0 已有修改记录机制（`data/task_modifications.json`）记录以下内容：
   - 操作时间（timestamp）
   - 操作类型（operation: add/update/delete/add_system/rename_system/delete_system/rebreakdown_system）
   - 系统名称（system）
   - 功能点标识（feature_name, feature_id, feature_index）
   - 变更字段（field）
   - 变更前后值（old_value, new_value）
2. 确认该记录结构满足 REQ-016（PM 修正率）和 REQ-020（AI 偏差监控）的数据需求
**业务规则**：
- 操作人字段由 REQ-014 统一补充，本需求不重复实现
**验收标准**：
- [ ] Given 功能点变更保存，When 查看 task_modifications.json，Then 包含 timestamp/operation/system/feature_name/field/old_value/new_value
- [ ] Given 修改记录数据，When 用于计算 PM 修正率，Then 可区分 add/update/delete 操作并统计功能点数
**关联**：SCN-001

---

#### REQ-013：系统画像重构（7→4 字段）
**目标/价值**：精简 PM 填写负担，补齐结构知识缺口，提升 AI 评估准确性
**入口/触发**：
- 画像编辑/发布：PM/admin 在信息看板页面编辑画像
- 自动沉淀：PM 确认保存功能点编辑结果时
- AI 评估：Agent 评估时检索画像注入 prompt
**前置条件**：无（v2.1 上线时旧 7 字段废弃，新 4 字段从空开始）
**主流程**：
1. **字段模型替换**：后端画像字段从旧 7 字段（in_scope, out_of_scope, core_functions, business_goals, business_objects, integration_points, key_constraints）替换为新 4 字段：

| 字段 key | 含义 | 数据类型 | AI 用途 |
|---|---|---|---|
| system_scope | 系统定位与边界 | text | 系统识别：判断需求归属，防止越界估算 |
| module_structure | 功能模块结构（模块→功能清单） | structured JSON | 功能点拆分：模块归属、粒度参考 |
| integration_points | 主要集成点 | text | 工作量估算：接口改造/联调成本 |
| key_constraints | 关键约束 | text | 复杂度判断：非功能/合规/数据模型约束 |

2. **前端信息看板适配**：`fieldLabels` 从 7 字段替换为 4 字段；module_structure 提供结构化编辑入口（示例模板/JSON 校验/一键格式化）
3. **module_structure 自动沉淀**：PM 确认保存功能点后，后端按"功能模块/功能点/业务描述"聚合生成 module_structure 并 upsert
4. **AI Agent 适配**：system_identification_agent 和 feature_breakdown_agent 的 prompt 注入适配新字段
5. **向量嵌入适配**：knowledge_service 的向量嵌入更新适配新字段
6. **AI 摘要适配**：profile_summary_service 适配新 4 字段

**输入/输出**：
- 输入（画像编辑）：4 个字段的值
- 输入（自动沉淀）：确认后的功能点列表
- 输出：更新后的系统画像

**业务规则**：
- **module_structure 数据结构**：
  ```json
  [
    {
      "module_name": "用户管理",
      "functions": [
        { "name": "用户注册", "desc": "新用户注册流程，含手机验证" },
        { "name": "用户登录", "desc": "支持密码和SSO两种方式" }
      ],
      "last_updated": "2026-02-11T10:00:00"
    }
  ]
  ```
- **唯一键**：module 级 = `module_name`；function 级 = `module_name` + `functions[].name`
- **更新策略**：
  - 新模块/功能：新增
  - 已有模块/功能：更新 `last_updated`，更新 `functions` 列表
  - 已有 `functions[].desc`：若人工已补充且不为空则优先保留（避免自动覆盖）
  - 同模块内同名功能覆盖更新
- **填写引导**：
  - system_scope："这个系统是做什么的、不做什么、业务目标是什么"
  - module_structure：模块→功能清单，PM 日常使用中自动沉淀
  - integration_points："上下游系统、接口协议、数据流向"
  - key_constraints："非功能要求、合规限制、数据模型/业务对象约束"
- **迁移方案**：不做自动拼接迁移（D-13）。v2.1 上线时旧 7 字段数据直接废弃，4 个新字段从空开始填写
- **存储**：复用 `data/system_profiles.json`，字段 key 替换
- **admin 权限**：admin 角色新增系统画像写入权限（D-10）

**异常与边界**：
- module_structure 为空时：画像完整度中 module_structure 维度得 0 分
- PM 提交的 module_structure JSON 格式错误：前端校验拦截，提示格式要求
- prompt 注入时 module_structure 过长：限制模块数/每模块功能数，对过长描述截断

**验收标准**：
- [ ] Given 访问信息看板页面，When 查看画像字段，Then 显示 4 个字段（system_scope/module_structure/integration_points/key_constraints）而非旧 7 字段
- [ ] Given PM 编辑 module_structure，When 输入非法 JSON，Then 前端校验拦截并提示
- [ ] Given PM 编辑 module_structure，When 点击"一键格式化"，Then JSON 自动格式化
- [ ] Given PM 确认保存功能点，When 功能点包含模块"用户管理"下的"用户注册"，Then 系统画像 module_structure 中出现对应条目
- [ ] Given 系统画像已有 module_structure，When AI 评估该系统，Then prompt 中包含 module_structure 内容
- [ ] Given admin 角色访问信息看板，When 编辑画像字段，Then 可以保存（有写入权限）
- [ ] Given v2.1 上线后，When 查看旧系统画像，Then 旧 7 字段不再显示，新 4 字段为空
**关联**：SCN-004；API-002, API-003

---

#### REQ-014：修改记录增强：操作人字段
**目标/价值**：支持 B-06 指标分析时区分 PM 修正和专家评估
**入口/触发**：功能点变更保存时
**前置条件**：用户已登录
**主流程**：
1. 在现有修改记录中补充 `actor_id`（操作人 ID）和 `actor_role`（操作时角色）
2. 前端提交变更时尽量附带当前用户的 actor 信息（API-001）
3. 后端在记录修改时写入 actor_id 和 actor_role；若请求未传 actor 字段则从当前登录态提取作为默认值（兼容 v2.0 调用方）
**输入/输出**：
- 输入：当前用户 ID 和 activeRole
- 输出：修改记录中包含 actor_id 和 actor_role
**业务规则**：
- actor_role 枚举值：admin / manager / expert
- actor_id 取当前登录用户的 user_id
- 历史修改记录（v2.0 已有）不回填 actor 字段，仅新记录包含
**验收标准**：
- [ ] Given PM 修改功能点并保存，When 查看修改记录，Then 记录包含 actor_id=PM的user_id 和 actor_role=manager
- [ ] Given 专家提交评估，When 查看修改记录，Then 记录包含 actor_id=专家的user_id 和 actor_role=expert
- [ ] Given 查看 v2.0 历史修改记录，When 检查 actor 字段，Then 字段不存在（不回填）
**关联**：SCN-001；API-001

---

#### REQ-015：画像完整度排名 + 过期预警
**目标/价值**：管理员可定位画像薄弱系统，驱动 PM 补充画像
**入口/触发**：管理员访问效能看板"系统影响"页签
**前置条件**：Feature Flag `V21_DASHBOARD_MGMT_ENABLED` = true
**主流程**：
1. 在"系统影响"页签中新增画像完整度排名区域
2. 按画像完整度评分对所有系统排名，低分系统标红
3. 画像超过 30 天未更新的标"过期"
4. 支持下钻到具体系统的画像详情
**业务规则**：
- **完整度评分公式**（满分 100）：
  - code_scan: 30（有扫描结果=30，无=0）
  - esb: 25（有 ESB 数据=25，无=0）
  - documents: 0~25（0篇=0，1-5篇=5，6-10篇=15，11+篇=25）
  - module_structure: 20（有≥1条=20，无=0）
- 过期判定：复用现有 `_is_profile_stale()` 机制（30 天未更新）
- 并入现有"系统影响"页签，不新增页签
- Feature Flag 关闭时：隐藏该排名区域
**验收标准**：
- [ ] Given 管理员访问"系统影响"页签，When Feature Flag 开启，Then 显示画像完整度排名列表
- [ ] Given 系统 A 完整度 30 分（仅 code_scan），When 查看排名，Then 系统 A 标红
- [ ] Given 系统 B 画像 35 天未更新，When 查看排名，Then 系统 B 标"过期"
- [ ] Given 管理员点击某系统，When 下钻，Then 跳转到该系统画像详情
- [ ] Given 系统有 module_structure 且≥1条，When 计算完整度，Then module_structure 维度得 20 分
**关联**：SCN-005；API-004

---

#### REQ-016：PM 修正率排行（按系统）
**目标/价值**：定位 AI 理解差的系统，驱动画像增强
**入口/触发**：管理员访问效能看板"AI 表现"页签
**前置条件**：Feature Flag `V21_DASHBOARD_MGMT_ENABLED` = true
**主流程**：
1. 在"AI 表现"页签中新增 PM 修正率排行区域
2. 展示 PM 修正率最高的 Top N 系统
3. 同时展示 PM 新增率
4. 支持按时间段筛选
**业务规则**：
- 修正率 = PM 修改的功能点数 / AI 初始功能点总数
- 新增率 = PM 新增的功能点数 / AI 初始功能点总数
- **去重规则（功能点维度）**：同一功能点的多字段修改只算 1 次修正（例如 PM 同时修改某功能点的名称和描述，修正计数为 1 而非 2）；去重键 = `task_id` + `system` + `feature_id`（或 `feature_name` + `feature_index`）
- **AI 初始功能点总数取值**：优先使用任务 `ai_initial_features` 快照中的功能点数；若历史任务缺失快照，降级为当前 AI 值口径并在指标旁标注"口径降级"
- PM 操作识别：修改记录中 actor_role=manager 的记录（依赖 REQ-014）
- 修正率高的系统 = AI 对该系统理解差 = 画像需要增强
- 系统维度排名需至少 3 条已完成任务才有统计意义，不足时显示"数据不足"
**验收标准**：
- [ ] Given 管理员访问"AI 表现"页签，When Feature Flag 开启，Then 显示 PM 修正率排行
- [ ] Given 系统 A 有 5 条已完成任务，When 查看排行，Then 显示系统 A 的修正率和新增率
- [ ] Given 系统 B 仅有 2 条已完成任务，When 查看排行，Then 系统 B 显示"数据不足"
- [ ] Given 管理员选择时间段"近30天"，When 查看排行，Then 仅统计该时间段内的任务
- [ ] Given PM 修改 1 个功能点的 3 个字段（名称+描述+复杂度），When 计算修正率，Then 修正计数为 1（按功能点去重）
**关联**：SCN-005；API-004

---

#### REQ-017：AI 命中率排行（按系统）
**目标/价值**：按系统维度定位 AI 命中率低的系统，与画像完整度交叉分析
**入口/触发**：管理员访问效能看板"AI 表现"页签
**前置条件**：Feature Flag `V21_DASHBOARD_MGMT_ENABLED` = true
**主流程**：
1. 在"AI 表现"页签中新增 AI 命中率排行区域
2. 将现有全局 AI 命中率拆分到系统维度，按系统排名
3. 命中率低的系统与画像完整度交叉展示
**业务规则**：
- **AI 命中率口径（沿用 v2.0 阈值命中算法）**：命中定义 = `abs(ai_estimation - final_estimation) / final_estimation <= 20%`（或绝对差 ≤ 0.5 人天，取宽松条件）；命中率 = 命中任务数 / 统计任务数（按系统拆分）
- 交叉展示：完整度低 + 命中率低 → 标记为"优先补画像"
- 系统维度排名需至少 3 条已完成任务才有统计意义
**验收标准**：
- [ ] Given 管理员访问"AI 表现"页签，When Feature Flag 开启，Then 显示 AI 命中率排行（按系统）
- [ ] Given 系统 A 完整度 30 分且命中率 20%，When 查看排行，Then 系统 A 标记为"优先补画像"
- [ ] Given 系统维度任务数不足 3 条，When 查看排行，Then 显示"数据不足"
**关联**：SCN-005；API-004

---

#### REQ-018：评估周期排行（按 PM）
**目标/价值**：识别评估周期长的 PM，间接反映 AI 对其负责系统的评估质量
**入口/触发**：管理员访问效能看板"排行榜"页签
**前置条件**：Feature Flag `V21_DASHBOARD_MGMT_ENABLED` = true
**主流程**：
1. 在"排行榜"页签中新增评估周期排行区域
2. 从任务创建到 PM 确认提交的平均周期，按 PM 排名
**业务规则**：
- 数据来源：任务 `created_at` → `frozen_at` 时间差
- 周期长的 PM 可能在反复修正 AI 结果
- PM 维度排名需至少 3 条已完成任务才有统计意义
**验收标准**：
- [ ] Given 管理员访问"排行榜"页签，When Feature Flag 开启，Then 显示评估周期排行（按 PM）
- [ ] Given PM 张三有 5 条任务平均周期 3 天，When 查看排行，Then 显示张三平均周期 3 天
- [ ] Given PM 仅有 2 条任务，When 查看排行，Then 显示"数据不足"
**关联**：SCN-005；API-004

---

#### REQ-019：画像贡献度排行（按 PM）
**目标/价值**：正向激励 PM 主动完善画像
**入口/触发**：管理员访问效能看板"排行榜"页签
**前置条件**：Feature Flag `V21_DASHBOARD_MGMT_ENABLED` = true
**主流程**：
1. 在"排行榜"页签中新增画像贡献度排行区域
2. 统计每个 PM 对系统画像的贡献
**业务规则**：
- 贡献维度：
  - 导入文档数（知识导入记录）
  - 完善字段数（画像更新记录）
  - 完善模块/功能清单条目数（module_structure 更新记录）
- 数据来源：知识导入记录 + 画像更新记录 + module_structure 更新记录
- 画像更新日志在 B-04 画像更新逻辑中同步记录（复用 `activity_logs.json`），记录：PM ID、更新类型、更新时间
**验收标准**：
- [ ] Given 管理员访问"排行榜"页签，When Feature Flag 开启，Then 显示画像贡献度排行（按 PM）
- [ ] Given PM 张三导入 3 份文档、完善 2 个字段、新增 5 条 module_structure，When 查看排行，Then 张三贡献度反映这些操作
**关联**：SCN-005；API-004

---

#### REQ-020：AI 工作量偏差监控（按系统）
**目标/价值**：按系统/任务维度展示 AI 与专家的工作量偏差
**入口/触发**：管理员访问效能看板"AI 表现"页签
**前置条件**：Feature Flag `V21_DASHBOARD_MGMT_ENABLED` = true
**主流程**：
1. 在"AI 表现"页签中新增 AI 工作量偏差监控区域
2. 按系统/任务维度展示 AI 初始总工作量 vs 专家最终评估总工作量的偏差百分比
**业务规则**：
- AI 初始总工作量：优先使用任务 `ai_initial_features` 快照计算
- 专家最终评估：取最新一轮均值汇总
- 若历史任务缺失 `ai_initial_features` 快照：降级为当前 AI 值口径，并在看板标注"口径降级"
- 偏差大的系统与 REQ-016/REQ-017 交叉验证
**验收标准**：
- [ ] Given 管理员访问"AI 表现"页签，When Feature Flag 开启，Then 显示 AI 工作量偏差监控
- [ ] Given 系统 A 有 ai_initial_features 快照，When 计算偏差，Then 使用快照口径
- [ ] Given 系统 B 缺失 ai_initial_features 快照，When 计算偏差，Then 使用当前 AI 值口径并标注"口径降级"
**关联**：SCN-005；API-004

---

#### REQ-021：AI 学习趋势
**目标/价值**：体现画像增强后 AI 是否在持续改进
**入口/触发**：管理员访问效能看板"AI 表现"页签
**前置条件**：Feature Flag `V21_DASHBOARD_MGMT_ENABLED` = true
**主流程**：
1. 在"AI 表现"页签中新增 AI 学习趋势区域
2. 展示同系统多次评估的修正率变化趋势（折线图）
**业务规则**：
- X 轴：评估时间（按任务创建时间排序）
- Y 轴：修正率
- 按系统分组，每个系统一条折线
- 趋势下降 = AI 在改进
**验收标准**：
- [ ] Given 管理员访问"AI 表现"页签，When Feature Flag 开启，Then 显示 AI 学习趋势折线图
- [ ] Given 系统 A 有 5 次评估，When 查看趋势，Then 显示 5 个数据点的折线
**关联**：SCN-005；API-004

---

#### REQ-022：系统清单数据源统一
**目标/价值**：修复 PM 知识导入/信息看板看不到系统的 Bug
**入口/触发**：任何读取系统清单的场景
**前置条件**：无
**主流程**：
1. 后端系统清单 API（`system_routes.py`）改为读取"系统清单配置"页面导入/维护的数据（即 `data/` 目录下的系统清单存储），不再读取任何 legacy CSV
2. 系统清单 API、系统识别、知识导入等场景统一走同一份数据
3. 系统负责人关系由导入模板补齐/维护：owner_id/owner_username/backup_owner_ids/backup_owner_usernames
**业务规则**：
- **唯一数据源**：以"系统清单配置"页面（XLSX 批量导入/CRUD）维护的数据为准（当前数据文件：`data/系统清单20260119.xlsx`）
- **明确废弃（两个 legacy CSV 均需清理）**：
  - 仓库根目录 `system_list.csv`（当前仅有表头，无系统数据）— 废弃
  - `backend/system_list.csv`（当前包含 123 行数据，但现有代码读取链路并未指向该文件）— 废弃
  - 实施时需确认 `backend/api/system_routes.py` 中 `CSV_PATH` 指向的是根目录 `system_list.csv`（空文件），这是 Bug 的直接原因
- **必须统一引用的模块清单**（所有以下模块必须从同一数据源读取系统清单）：
  - `backend/api/system_routes.py`：系统清单 API（当前 CSV_PATH 指向根目录空 CSV，需改为 `data/` 目录数据源）
  - `backend/api/system_list_routes.py`：系统清单配置 CRUD
  - `backend/service/knowledge_service.py`：知识导入时的系统列表
  - `backend/agent/system_identification_agent.py`：AI 系统识别时的系统列表
  - 前端 `filterResponsibleSystems()`：PM 端系统过滤
- 负责人字段格式：数据源为 `data/系统清单20260119.xlsx`，"系统负责人"列，格式为"A角"或"A角/B角"
- `filterResponsibleSystems()` 逻辑不变，仅数据源统一后即可正常过滤
**异常与边界**：
- 若系统清单存储文件不存在或为空：返回空列表，前端提示"暂无系统数据，请先导入系统清单"
- 导入时负责人字段缺失：系统可创建但 PM 端不可见（filterResponsibleSystems 过滤掉）
**验收标准**：
- [ ] Given PM 黄洋登录，When 进入知识导入页，Then 系统下拉列表显示 3 个系统（NESB、OAS、UJS）
- [ ] Given PM 黄洋登录，When 进入信息看板页，Then 可看到负责的系统
- [ ] Given 后端启动，When 系统清单 API 被调用，Then 不读取根目录 `system_list.csv` 也不读取 `backend/system_list.csv`
- [ ] Given 系统清单配置页面导入新系统，When 知识导入页刷新，Then 新系统出现在下拉列表中
- [ ] Given 代码搜索 `system_list.csv`，When 搜索 `backend/` 目录，Then 无 CSV_PATH 引用或已替换为新数据源路径
- [ ] Given 统一后，When 系统清单 API 返回 items，Then items 非空且负责人字段可用于 `filterResponsibleSystems()`
**关联**：SCN-003；API-005

## 4. 非功能需求

### 4.1 非功能需求列表
| 需求分类 | REQ-ID | 需求名称 | 优先级 | 需求说明 | 验收/指标 |
|---|---|---|---|---|---|
| 可用性 | REQ-101 | Feature Flag 开关机制 | M | 关键行为变更支持后端开关快速关闭 | 3 个开关均可独立关闭且回退到 v2.0 行为 |
| 可用性 | REQ-102 | 数据备份与回滚 | M | 部署前数据快照备份 | 可从备份恢复到 v2.0 状态 |
| 兼容性 | REQ-103 | API 向后兼容 | M | 除画像字段重构外保持 API 兼容 | 现有 API 调用方无需修改 |
| 可观测性 | REQ-104 | 知识命中率观测 | S | 知识命中率作为观测指标 | 指标可查询，前提条件不满足时不出值 |
| 交互体验 | REQ-105 | AI 评估状态反馈 | M | 评估期间有明确的状态提示 | 用户可感知评估进度 |

### 4.2 非功能需求明细

#### REQ-101：Feature Flag 开关机制
**需求分类**：可用性
**适用范围**：B-01、B-02、B-06 三项行为变更
**指标与口径**：

| 变更 | 开关（后端 env） | 默认 | 关闭时行为 |
|---|---|---|---|
| B-01 自动重评估 | `V21_AUTO_REEVAL_ENABLED` | true | 不自动触发；保留/恢复手动触发入口 |
| B-02 备注自动生成+只读 | `V21_AI_REMARK_ENABLED` | true | 备注恢复为可编辑（沿用 v2.0 行为） |
| B-06 管理驱动指标 | `V21_DASHBOARD_MGMT_ENABLED` | true | 隐藏 B-06a~B-06f 新增指标与下钻 |

**验收方法**：
- 逐一关闭每个开关，验证对应功能回退到 v2.0 行为
- 开关生效方式：修改环境变量后**重启服务生效**（降低实现复杂度，不要求热加载）
- **前端回滚路径**：后端提供配置查询接口 `GET /api/v1/system/config/feature-flags`，返回当前 3 个开关状态；前端在页面初始化时读取开关状态，据此决定 UI 行为：
  - `V21_AUTO_REEVAL_ENABLED=false`：隐藏自动评估提示，显示手动"重新评估"按钮
  - `V21_AI_REMARK_ENABLED=false`：备注字段恢复可编辑
  - `V21_DASHBOARD_MGMT_ENABLED=false`：隐藏 B-06a~f 新增指标区域
**关联**：REQ-010, REQ-011, REQ-015~REQ-021

#### REQ-102：数据备份与回滚
**需求分类**：可用性
**适用范围**：v2.1 部署
**指标与口径**：
- 部署前对 `data/` 关键存储做快照备份，至少包含：
  - `data/task_storage.json`
  - `data/system_profiles.json`
  - 系统清单存储文件
  - 知识库/检索日志相关文件
- 回滚时优先恢复 `data/system_profiles.json`（B-04 字段模型变化影响 v2.0 读取）
**验收方法**：
- 部署脚本包含备份步骤
- 可从备份恢复到 v2.0 可用状态
**关联**：REQ-013

#### REQ-103：API 向后兼容
**需求分类**：兼容性
**适用范围**：除画像字段重构相关接口外的所有 API
**指标与口径**：
- 画像相关接口（system_profile_routes.py）的字段模型变更为破坏性变更，v2.1 前后端同步发布
- 其他 API 接口保持请求/响应格式不变；如需新增字段，必须为**可选字段**并具备默认值策略（不影响 v2.0 调用方）
- API-001 新增的 `actor_id/actor_role` 为可选字段：缺失时后端从当前登录态提取默认值（不返回 400）
**验收方法**：
- 除画像接口外，v2.0 前端可调用 v2.1 后端不报错（验证关键接口）
**关联**：REQ-013

#### REQ-104：知识命中率观测
**需求分类**：可观测性
**适用范围**：AI 评估效果监控
**指标与口径**：
- 指标：`ai_effect_snapshots.metrics.knowledge_hit_rate`
- 统计口径：有命中（hit_count>0）的检索次数 / 检索总次数（任务级别，近30天窗口）
- 前提条件（不满足时不出值）：
  - ①统计窗口内检索次数≥30（N=30）
  - ②至少有 3 个系统已发布画像且导入≥1份知识文档（M=3）
  - ③检索阈值/TopK 参数已固定
- 本版本为观测指标，不作为门禁；具体目标值待数据准备充分后确定
**验收方法**：
- 指标可在效能看板或 API 中查询
- 前提条件不满足时返回 null/N/A 而非 0
**关联**：REQ-015~REQ-021

#### REQ-105：AI 评估状态反馈
**需求分类**：交互体验
**适用范围**：功能点编辑页
**指标与口径**：
- AI 评估触发后，前端在 1 秒内显示"AI 正在重新评估中"提示
- 评估完成后，前端在收到通知后 1 秒内恢复按钮可用状态
**验收方法**：
- 手动触发评估，观察提示出现和按钮状态变化
**关联**：REQ-010

## 5. 权限与合规

### 5.1 权限矩阵

| 角色 | 操作/权限 | 资源范围 | 备注 |
|---|---|---|---|
| admin | 系统清单 CRUD | 全局 | 不变 |
| admin | 规则管理 | 全局 | 不变 |
| admin | 效能看板（含 B-06 管理指标） | 全局 | 新增 B-06a~f 指标可见 |
| admin | 系统画像写入 | 全局 | v2.1 新增（D-10） |
| manager | 功能点编辑 | 负责的任务 | 不变 |
| manager | 知识导入 | 负责的系统（主责/B角） | 不变，数据源修复后可见 |
| manager | 信息看板（画像编辑） | 负责的系统（主责/B角） | 字段从 7→4 |
| manager | 效能看板 | 按 owner 视角 | 视角自动决定 |
| expert | 专家评估 | 被分配的任务 | 不变 |
| expert | 效能看板 | 按 expert 视角 | 视角自动决定 |
| viewer | 效能看板 | 按 executive 视角 | 视角自动决定 |

### 5.2 权限变更说明
- **admin 画像写入权限（D-10）**：v2.0 中仅 manager 且为系统主责/B角可写画像；v2.1 新增 admin 角色对所有系统画像的写入权限，用于修正画像内容保证数据质量
- **效能看板视角自动化（D-04）**：移除手动"视角"选择器，按 activeRole 自动决定视角，不影响数据访问权限

## 6. 数据与接口

### 6.1 数据字典

#### 系统画像字段（v2.1）
| 字段 | 类型 | 必填 | 来源/去向 | 备注 |
|---|---|---|---|---|
| system_scope | text | 否 | PM/admin 手工编辑 → AI prompt 注入 | 合并自 in_scope + out_of_scope + business_goals |
| module_structure | JSON array | 否 | PM 确认保存自动沉淀 + 手工编辑 → AI prompt 注入 | 结构化模块→功能清单 |
| integration_points | text | 否 | PM/admin 手工编辑 → AI prompt 注入 | 不变 |
| key_constraints | text | 否 | PM/admin 手工编辑 → AI prompt 注入 | 合并自 key_constraints + business_objects |

#### module_structure 元素结构
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| module_name | string | 是 | 模块名，唯一键 |
| functions | array | 是 | 功能列表 |
| functions[].name | string | 是 | 功能名称，模块内唯一键 |
| functions[].desc | string | 否 | 功能描述 |
| last_updated | ISO datetime | 是 | 最后更新时间，自动生成 |

#### 修改记录扩展字段（v2.1 新增）
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| actor_id | string | 是（v2.1 新记录） | 操作人 user_id（若请求未传 actor 字段则由后端从登录态补齐） |
| actor_role | enum(admin/manager/expert) | 是（v2.1 新记录） | 操作时角色（若请求未传 actor 字段则由后端从登录态补齐） |

### 6.2 接口变更清单

#### API-001：功能点保存接口增强
- **现有接口**：`PUT /api/v1/requirement/features/{task_id}`
- **变更内容**：
  - 请求体新增（可选）`actor_id`、`actor_role` 字段；缺失时后端从当前登录态提取默认值（兼容 v2.0 调用方）
  - **保存接口仅负责持久化变更与记录修改**，不再直接触发 AI 重评估（重评估由 API-006 独立触发）
  - 后端忽略客户端写入的 `备注/remark` 字段（静默忽略，不返回错误；服务端生成的备注覆盖客户端值）
  - 响应体移除 `reeval_triggered` 字段（重评估状态由 API-006 返回）

#### API-002：系统画像保存接口适配
- **现有接口**：`PUT /api/v1/system-profile/{system_name}`
- **变更内容**：
  - `fields` 参数从 7 字段替换为 4 字段（system_scope/module_structure/integration_points/key_constraints）
  - module_structure 字段接受 JSON array
  - 新增 admin 角色写入权限

#### API-003：系统画像查询接口适配
- **现有接口**：`GET /api/v1/system-profile/{system_name}`
- **变更内容**：
  - 响应体字段从 7 字段替换为 4 字段
  - module_structure 返回结构化 JSON array

#### API-004：效能看板查询接口扩展
- **现有接口**：`POST /api/v1/efficiency/dashboard/query`
- **变更内容**：
  - 请求体移除 `filters.ai_involved` 参数
  - `perspective` 参数由前端根据 activeRole 自动填充
  - 响应体新增 B-06a~f 排名数据（Feature Flag 控制）：
    - `profile_completeness_ranking`：画像完整度排名
    - `pm_correction_rate_ranking`：PM 修正率排行
    - `ai_hit_rate_ranking`：AI 命中率排行
    - `evaluation_cycle_ranking`：评估周期排行
    - `profile_contribution_ranking`：画像贡献度排行
    - `ai_deviation_monitoring`：AI 工作量偏差监控
    - `ai_learning_trend`：AI 学习趋势数据

#### API-005：系统清单接口数据源修复
- **现有接口**：`GET /api/v1/system/systems`
- **变更内容**：
  - 数据源从 legacy CSV（根目录 `system_list.csv` 和 `backend/system_list.csv`）改为系统清单配置页面导入/维护的数据存储（`data/` 目录）
  - 必须统一引用的模块：`system_routes.py`、`system_list_routes.py`、`knowledge_service.py`、`system_identification_agent.py`
  - 响应格式不变

#### API-006：重评估触发接口（新增）
- **新增接口**：`POST /api/v1/tasks/{task_id}/reevaluate`
- **说明**：前端在一次保存动作结束后调用此接口：
  - `V21_AUTO_REEVAL_ENABLED=true`：一次性触发异步 AI 重评估
  - `V21_AUTO_REEVAL_ENABLED=false`：默认不触发重评估，仅用于生成备注（若开启）并返回 `status=skipped`；前端保留手动触发入口时可用 `force=true` 触发重评估
- **请求体**：可选 `force: boolean`（默认 false）
- **响应体**：
  - `job_id: string | null`：重评估任务 ID（未触发重评估时为 null）
  - `status: "pending" | "running" | "completed" | "failed" | "skipped"`：当前状态
  - `created_at: ISO datetime`：任务创建时间（skipped 时返回请求时间）
- **幂等规则**：同一 task 同时只允许 1 个重评估任务运行；若已有 running/pending 任务，返回已有 job 信息（HTTP 200，不产生新任务）
- **备注生成**：
  - `V21_AI_REMARK_ENABLED=true` 时自动生成一条备注摘要：重评估完成后生成；或在 skipped 模式下立即生成
  - 同一保存动作重复调用接口不生成重复备注（无新增修改记录则不生成）
- **关联**：REQ-010, REQ-011

#### API-007：Feature Flags 查询接口（新增）
- **新增接口**：`GET /api/v1/system/config/feature-flags`
- **说明**：前端页面初始化时读取开关状态，用于决定 UI 行为与回滚路径（REQ-101）
- **响应体**：
  - `V21_AUTO_REEVAL_ENABLED: boolean`
  - `V21_AI_REMARK_ENABLED: boolean`
  - `V21_DASHBOARD_MGMT_ENABLED: boolean`
- **权限**：所有已登录用户可读

### 6.3 错误码与校验规则（最小集合）

| 接口 | 场景 | HTTP 状态码 | 错误码 | 提示语/处理 |
|---|---|---|---|---|
| API-001 PUT features | 请求未传 actor 字段且后端无法从登录态获取 | 400 | `missing_actor` | "缺少操作人信息" |
| API-001 PUT features | task_id 不存在 | 404 | `task_not_found` | "任务不存在" |
| API-001 PUT features | 任务处于评估中（locked） | 409 | `task_locked` | "任务正在评估中，请稍后再试" |
| API-002 PUT system-profile | `module_structure` 非法 JSON | 400 | `invalid_module_structure` | "module_structure 格式错误，需为 JSON 数组" |
| API-002 PUT system-profile | 非 admin 且非系统主责/B角 | 403 | `permission_denied` | "无权编辑该系统画像" |
| API-002 PUT system-profile | system_name 不存在 | 404 | `system_not_found` | "系统不存在" |
| API-004 POST dashboard query | `perspective` 值不在枚举范围 | 400 | `invalid_perspective` | "perspective 必须为 owner/expert/executive" |
| API-005 GET systems | 系统清单存储文件不存在或为空 | 200 | - | 返回空列表 `{"items": []}` |
| API-007 GET feature-flags | 未登录 | 401 | `unauthorized` | "请先登录" |
| API-006 POST reevaluate | 已有 running/pending 任务 | 200 | - | 返回已有 job 信息（幂等） |
| API-006 POST reevaluate | task_id 不存在 | 404 | `task_not_found` | "任务不存在" |

### 6.4 指标与计算口径

| 指标 | 公式 | 统计周期 | 最小样本量 | 精度 |
|---|---|---|---|---|
| 画像完整度 | code_scan(30) + esb(25) + documents(0~25) + module_structure(20) | 实时 | - | 整数 |
| PM 修正率 | PM 修改的功能点数（按功能点去重） / AI 初始功能点总数 | 可按时间段筛选 | 系统≥3条已完成任务 | 百分比，1位小数 |
| PM 新增率 | PM 新增的功能点数 / AI 初始功能点总数 | 同上 | 同上 | 同上 |
| AI 命中率 | 命中任务数 / 统计任务数（命中定义：`abs(ai-final)/final ≤ 20%` 或绝对差 ≤ 0.5d，按系统拆分） | 同上 | 同上 | 同上 |
| 评估周期 | avg(frozen_at - created_at) | 同上 | PM≥3条已完成任务 | 天，1位小数 |
| AI 工作量偏差 | (AI初始总工作量 - 专家最终总工作量) / 专家最终总工作量 × 100% | 同上 | 系统≥3条已完成任务 | 百分比，1位小数 |
| 知识命中率（观测） | hit_count>0 的检索次数 / 检索总次数 | 近30天窗口 | 检索次数≥30，已发布画像系统≥3 | 百分比，1位小数 |

## 7. 变更记录
| 版本 | 日期 | 说明 | 作者 |
|---|---|---|---|
| v0.1 | 2026-02-11 | 初始化：22 条功能性需求 + 5 条非功能需求 + 7 个场景 + 5 个接口变更 + 权限矩阵 + 数据字典 + 指标口径 | AI |
| v0.2 | 2026-02-11 | Requirements Review 修复（RVW-001~005）：新增 API-006 重评估触发接口与幂等策略；明确两个 legacy CSV 废弃范围与 5 个统一引用模块；AI 命中率沿用 v2.0 阈值算法 + 修正率去重规则；Feature Flag 改为重启生效 + 前端配置查询接口；新增 6.3 错误码与校验规则表 | AI |
| v0.3 | 2026-02-11 | Requirements Review 第 2 轮修复（RVW-006~010）：统一备注生成触发时机并补齐跨 Flag 场景；API-001 actor 字段改为可选以满足 REQ-103 向后兼容；在 6.2 正式补充 API-007 Feature Flags 查询接口；明确 SCN-002 触发机制与 REQ-010 部分保存失败“不回滚”策略 | AI |
