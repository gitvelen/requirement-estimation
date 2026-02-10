# AI Coding Tool Skills

本目录包含自定义 AI Skills，按功能分类组织。

## 目录结构

```
skills/
├── code/           # 代码质量相关
│   └── techdebt    # 技术债务扫描
├── workflow/       # 工作流程相关
│   ├── sync-context    # 上下文同步
│   └── review-pr       # PR 代码审查
│   └── reviewer-prompts.md  # 审查口令集
├── project/        # 项目特定技能
│   └── check-aquote    # A股交易规则检查
├── quant/          # 量化交易相关
│   ├── stock-data      # A股数据查询
│   ├── strategy-backtest # 策略回测分析
│   ├── portfolio-analysis # 组合分析
│   └── risk-metrics    # 风险指标计算
└── README.md       # 本文件
```

## 使用方法

### 方式一：直接调用
```
/techdebt
/sync-context
/review-pr
/check-aquote
/stock-data
/strategy-backtest
/portfolio-analysis
/risk-metrics
```

### 方式二：自然语言描述
```
"请检查技术债务"
"同步一下项目上下文"
"审查这个 PR"
"检查 A 股交易规则"
```

## 各 Skill 说明

### /techdebt
扫描代码中的技术债务，包括：
- 重复代码
- TODO/FIXME/HACK 标记
- 过时代码
- 高复杂度函数

### /sync-context
生成项目上下文快照，包括：
- 项目基本信息
- 当前工作状态
- 代码结构
- 最近变更
- 待办事项

### /review-pr
对 PR 进行代码审查，检查：
- 安全问题
- 功能正确性
- 代码质量
- 测试覆盖
- 性能影响

### /check-aquote
检查代码是否符合 A 股交易规则，包括：
- T+1 制度
- 交易单位（100股整数倍）
- 涨跌停限制
- 人工确认环节
- 复权数据处理
- 交易时间检查
- 停牌处理
- 密钥保护

### /stock-data
A股数据查询与分析，包括：
- 个股行情（实时/历史）
- 指数数据
- 财务数据
- 技术指标计算

### /strategy-backtest
策略回测分析，包括：
- 回测执行
- 收益指标计算
- 风险分析
- 交易统计

### /portfolio-analysis
投资组合分析，包括：
- 持仓分布
- 行业分布
- 收益归因
- 风险分析

### /risk-metrics
风险指标计算，包括：
- 波动性指标
- 下行风险（VaR、CVaR）
- 风险调整收益（夏普、索提诺）
- 系统性风险（Beta、Alpha）

## 添加新 Skill

1. 在对应分类目录下创建文件
2. 文件格式：
```python
# description: 简短描述
# usage: 使用方式

详细指令内容...
```

3. 重新加载 AI Coding Tool 生效
