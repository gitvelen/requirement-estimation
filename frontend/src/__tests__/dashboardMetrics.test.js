import {
  buildFlowSummaryMetrics,
  buildOverviewSummaryMetrics,
} from '../utils/dashboardMetrics';

describe('dashboard summary metrics formatting', () => {
  it('maps overview and ai metrics to readable labels', () => {
    const metrics = buildOverviewSummaryMetrics(
      { task_count: 0, avg_final_days: 0 },
      { rate: 0, count: 0 }
    );

    expect(metrics).toEqual([
      { key: 'task_count', label: '已完成任务数', value: 0, precision: 0, suffix: '项' },
      { key: 'avg_final_days', label: '平均评估工作量', value: 0, precision: 2, suffix: '人天' },
      { key: 'rate', label: 'AI参与率', value: 0, precision: 2, suffix: '%' },
      { key: 'count', label: 'AI参与任务数', value: 0, precision: 0, suffix: '项' },
    ]);
  });

  it('maps flow metrics to readable labels', () => {
    const metrics = buildFlowSummaryMetrics(
      { avg_days: 1.25 },
      { completed_tasks: 12 }
    );

    expect(metrics).toEqual([
      { key: 'avg_days', label: '平均流程周期', value: 1.25, precision: 2, suffix: '天' },
      { key: 'completed_tasks', label: '完成任务数', value: 12, precision: 0, suffix: '项' },
    ]);
  });
});
