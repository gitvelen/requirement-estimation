const OVERVIEW_DEFS = [
  { key: 'task_count', label: '已完成任务数', precision: 0, suffix: '项' },
  { key: 'avg_final_days', label: '平均评估工作量', precision: 2, suffix: '人天' },
];

const AI_DEFS = [
  { key: 'rate', label: 'AI参与率', precision: 2, suffix: '%' },
  { key: 'count', label: 'AI参与任务数', precision: 0, suffix: '项' },
];

const FLOW_DEFS = [
  { key: 'avg_days', label: '平均流程周期', precision: 2, suffix: '天' },
  { key: 'completed_tasks', label: '完成任务数', precision: 0, suffix: '项' },
];

const parseNumber = (value) => {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }
  return null;
};

const buildMetrics = (source, defs) => (
  defs
    .map((def) => {
      const value = parseNumber(source?.[def.key]);
      if (value === null) {
        return null;
      }
      return {
        key: def.key,
        label: def.label,
        value,
        precision: def.precision,
        suffix: def.suffix,
      };
    })
    .filter(Boolean)
);

export const buildOverviewSummaryMetrics = (overviewData, aiData) => ([
  ...buildMetrics(overviewData, OVERVIEW_DEFS),
  ...buildMetrics(aiData, AI_DEFS),
]);

export const buildFlowSummaryMetrics = (flowCycleData, flowThroughputData) => ([
  ...buildMetrics(flowCycleData, FLOW_DEFS.slice(0, 1)),
  ...buildMetrics(flowThroughputData, FLOW_DEFS.slice(1)),
]);
