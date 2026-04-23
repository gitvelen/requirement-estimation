# COSMIC 规则说明与拆分边界优化输入

## intent

用户要求深入核实两件事。

第一，当前功能点拆分过程是否真正考虑了 COSMIC 的要求，还是主要按 LLM 自由拆分来生成功能点。用户在核实后确认，后续需要把“最小必要的 COSMIC 边界约束”纳入考虑，但不希望因此引入激进的全量重拆或大量额外 token 消耗。

第二，当前“规则管理”页的“使用说明”存在明显误导倾向。用户希望整体优化该说明：只保留必要内容，让管理员快速理解各项指标和配置的意义，并有利于按照组织内部要求配置 COSMIC 规则。

## local-observations

- 当前规则管理页的使用说明包含“细粒度 / 中等粒度 / 粗粒度”等教学式示例，容易让管理员理解为该页面配置会直接控制功能点拆分粒度。
- 本地代码核查显示，当前功能点拆分主链路主要由 `feature_breakdown_agent` 的 LLM prompt 完成；COSMIC 分析器存在独立 API 和分析能力，但未接入拆分主链路。

## clarifications

### scope-priority

本轮优先处理 COSMIC 使用说明的纠偏与能力边界澄清；拆分链路的 COSMIC 边界补强作为后续 Requirements / Design direction，不在 Proposal 阶段直接实现。

### estimation-context

工作量估算不能退化为只根据功能点短描述或只言片语估算；若未来引入局部 refine，估算仍须保留完整原始需求上下文。

### conservative-policy

后续若增加粗粒度检测，应采取偏保守策略，优先减少误伤和无意义的额外 LLM 调用。

### capability-boundary

当前 COSMIC 规则管理页用于解释和配置计量口径，不应继续暗示其直接控制当前功能点拆分行为。

### future-scope

是否要在未来单独引入“可配置拆分粒度”能力，可后续单独评估，不默认纳入 `v3.1` 当前范围。
