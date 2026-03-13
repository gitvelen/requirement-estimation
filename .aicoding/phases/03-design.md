# 阶段3：技术方案设计（Design）

> 阶段入口/出口清单为脚本单源：`scripts/lib/common.sh` 的 `aicoding_phase_entry_required` / `aicoding_phase_exit_required`。

## 目标
- 输出可落地的技术方案，并与 `requirements.md` 建立可验真追溯。

## 阶段入口/出口

**入口文件：**
- `docs/<版本号>/requirements.md`
- `docs/<版本号>/status.md`
- `.aicoding/phases/03-design.md`（本文件）
- `.aicoding/templates/design_template.md`
- `.aicoding/templates/review_design_template.md`

**出口文件：**
- `docs/<版本号>/design.md`
- `docs/<版本号>/review_design.md`

## 阶段入口协议（🔴 MUST，CC-7 程序化强制）

> 脚本单源：`scripts/lib/common.sh` 的 `aicoding_phase_entry_required`。以下表格为人类可读视图，以脚本为准。

| 必读文件 | 用途 | 强制级别 |
|---------|------|---------|
| `docs/<版本号>/status.md` | 获取当前状态、Active CR、基线版本 | 🔴 CC-7 强制 |
| `docs/<版本号>/requirements.md` | 本阶段核心输入 | 🔴 CC-7 强制 |
| `.aicoding/phases/03-design.md` | 本阶段规则（本文件） | 🔴 CC-7 强制 |
| `.aicoding/templates/design_template.md` | 产出物模板 | 🔴 CC-7 强制 |
| `.aicoding/templates/review_design_template.md` | 审查模板 | 🔴 CC-7 强制 |

## 本阶段特有规则
1. 先补齐设计决策：技术栈、关键依赖、部署形态、风险与回滚。
2. 设计必须逐条覆盖需求约束，尤其 `REQ-C` 禁止项。
3. 允许记录待确认项，但必须标注影响和确认时机。
4. 如有 Active CR，按 diff-only 口径补充"变更点→设计影响"说明。
5. 涉及前后端数据交互的需求，必须在 design.md 的 5.4 节显式定义本次新增/变更 API 的完整契约；如完整 OpenAPI/接口文档维护在 `docs/接口文档.md`，5.4 可链接外部文档，但不得只写“见接口文档”而缺少最小可实现契约：
   - 端点路径（精确到参数）
   - 请求/响应数据结构（JSON Schema 或 TypeScript interface）
   - 错误码与异常处理
   - 前后端必须基于同一份契约开发

## 读取模板
编写设计时读取 `.aicoding/templates/design_template.md`。

## 完成条件（🔴 MUST）
1. `review_design.md` 通过自审（P0/P1 open=0）。
2. 追溯覆盖校验通过（requirements → design）。
3. `status.md` 更新到下一阶段前，入口/出口门禁全部通过。
