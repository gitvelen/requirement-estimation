import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Col,
  Empty,
  Row,
  Space,
  Spin,
  Table,
  Typography,
} from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import axios from 'axios';
import { extractErrorMessage } from '../utils/errorMessage';
import { buildFlowSummaryMetrics, buildOverviewSummaryMetrics } from '../utils/dashboardMetrics';

const { Text } = Typography;

const SECTION_LOGIC_TEXT = {
  correction_rate: '看 PM 在 AI 初稿上改了多少：修正率 = 修正功能点数 / AI 初估功能点总数。值越低，说明初稿越稳定。',
  hit_rate: '看 AI 估算是否接近最终结果：误差在 20% 内或不超过 0.5 人天记为命中。命中率越高，估算越准。',
  profile_contribution: '看系统画像资料对评估结果的支撑程度：由文档数量、关键字段完备度、模块能力项共同计算。',
  evaluation_cycle: '看任务从创建到冻结平均用了多久。周期越短，流程协同通常越顺畅。',
  deviation_monitoring: '看 AI 与最终工时差了多少（偏差）。绝对值越小，结果越稳定；偏差过大建议优先排查。',
  learning_trend: '看修正率是持续下降还是上升：下降表示 AI 在变好，上升表示近期准确度在变差。',
};

const resolveRowKey = (record, index) => (
  record?.system_id
  || record?.owner_id
  || record?.manager_id
  || record?.expert_id
  || record?.id
  || index
);

const renderSummaryStats = (metrics = []) => {
  if (!Array.isArray(metrics) || !metrics.length) {
    return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无数据" />;
  }

  const lgSpan = metrics.length >= 4 ? 6 : metrics.length === 3 ? 8 : 12;
  const formatValue = (value, precision) => {
    if (typeof value !== 'number' || !Number.isFinite(value)) {
      return '-';
    }
    return value.toLocaleString('zh-CN', {
      minimumFractionDigits: precision,
      maximumFractionDigits: precision,
    });
  };

  return (
    <Row gutter={[12, 12]}>
      {metrics.map((metric) => (
        <Col key={metric.key} xs={24} sm={12} lg={lgSpan}>
          <Card size="small" styles={{ body: { padding: '8px 12px' } }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: 8,
              }}
            >
              <Text
                type="secondary"
                style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}
              >
                {metric.label}
              </Text>
              <Text strong style={{ whiteSpace: 'nowrap', flexShrink: 0 }}>
                {formatValue(metric.value, metric.precision)}
                {metric.suffix || ''}
              </Text>
            </div>
          </Card>
        </Col>
      ))}
    </Row>
  );
};

const renderItemsTable = (items = [], columns = []) => {
  if (!Array.isArray(items) || !items.length) {
    return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无数据" />;
  }
  return (
    <Table
      rowKey={resolveRowKey}
      columns={columns}
      dataSource={items}
      pagination={{ pageSize: 5, hideOnSinglePage: true }}
      size="small"
      scroll={{ x: true }}
    />
  );
};

const renderSectionLogic = (text) => (
  <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
    <Text type="secondary">{text}</Text>
  </div>
);

const renderMetricCard = ({ title, loading, items, columns, logicText }) => (
  <Card title={title} size="small" style={{ height: '100%' }}>
    <Space direction="vertical" size={12} style={{ width: '100%' }}>
      {loading ? <Spin /> : renderItemsTable(items, columns)}
      {renderSectionLogic(logicText)}
    </Space>
  </Card>
);

const isRequestCanceled = (error) => (
  error?.code === 'ERR_CANCELED'
  || error?.name === 'CanceledError'
  || error?.name === 'AbortError'
);

const DashboardReportsPage = () => {
  const [loading, setLoading] = useState(false);
  const [errorText, setErrorText] = useState('');
  const [widgetsByPage, setWidgetsByPage] = useState({});
  const requestControllerRef = useRef(null);
  const mountedRef = useRef(false);

  const abortActiveRequest = useCallback(() => {
    const controller = requestControllerRef.current;
    requestControllerRef.current = null;
    controller?.abort();
  }, []);

  const fetchReports = useCallback(async () => {
    abortActiveRequest();
    const controller = new AbortController();
    requestControllerRef.current = controller;
    setLoading(true);
    setErrorText('');
    try {
      const pages = ['overview', 'system', 'flow', 'ai', 'rankings'];
      const responses = await Promise.all(
        pages.map((page) => axios.post('/api/v1/efficiency/dashboard/query', {
          page,
          perspective: 'executive',
          filters: {},
        }, {
          signal: controller.signal,
        }))
      );

      const next = {};
      pages.forEach((page, index) => {
        const payload = responses[index]?.data?.result || {};
        next[page] = Array.isArray(payload.widgets) ? payload.widgets : [];
      });
      if (!mountedRef.current || requestControllerRef.current !== controller) {
        return;
      }
      setWidgetsByPage(next);
    } catch (error) {
      if (isRequestCanceled(error)) {
        return;
      }
      if (!mountedRef.current || requestControllerRef.current !== controller) {
        return;
      }
      setErrorText(extractErrorMessage(error, '多维报表加载失败'));
    } finally {
      if (requestControllerRef.current === controller) {
        requestControllerRef.current = null;
        if (mountedRef.current) {
          setLoading(false);
        }
      }
    }
  }, [abortActiveRequest]);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      abortActiveRequest();
    };
  }, [abortActiveRequest]);

  useEffect(() => {
    fetchReports();
  }, [fetchReports]);

  const pickWidget = useCallback((page, widgetId) => {
    const widgets = widgetsByPage?.[page] || [];
    return (widgets || []).find((widget) => widget?.widget_id === widgetId);
  }, [widgetsByPage]);

  const systemWidgets = useMemo(() => widgetsByPage?.system || [], [widgetsByPage]);
  const flowWidgets = useMemo(() => widgetsByPage?.flow || [], [widgetsByPage]);
  const aiWidgets = useMemo(() => widgetsByPage?.ai || [], [widgetsByPage]);
  const rankingsWidgets = useMemo(() => widgetsByPage?.rankings || [], [widgetsByPage]);

  const overviewSummaryWidget = useMemo(
    () => pickWidget('overview', 'task_completion_overview'),
    [pickWidget]
  );
  const aiInvolvedWidget = useMemo(
    () => pickWidget('overview', 'ai_involved_rate'),
    [pickWidget]
  );

  const pmCorrectionWidget = useMemo(
    () => (aiWidgets || []).find((widget) => widget?.widget_id === 'pm_correction_rate_ranking'),
    [aiWidgets]
  );
  const aiHitWidget = useMemo(
    () => (aiWidgets || []).find((widget) => widget?.widget_id === 'ai_hit_rate_ranking'),
    [aiWidgets]
  );
  const profileContributionWidget = useMemo(
    () => (rankingsWidgets || []).find((widget) => widget?.widget_id === 'profile_contribution_ranking'),
    [rankingsWidgets]
  );

  const evaluationCycleWidget = useMemo(
    () => (rankingsWidgets || []).find((widget) => widget?.widget_id === 'evaluation_cycle_ranking'),
    [rankingsWidgets]
  );
  const deviationWidget = useMemo(
    () => (aiWidgets || []).find((widget) => widget?.widget_id === 'ai_deviation_monitoring'),
    [aiWidgets]
  );
  const learningTrendWidget = useMemo(
    () => (aiWidgets || []).find((widget) => widget?.widget_id === 'ai_learning_trend'),
    [aiWidgets]
  );

  const profileCompletenessWidget = useMemo(
    () => (systemWidgets || []).find((widget) => widget?.widget_id === 'profile_completeness_ranking'),
    [systemWidgets]
  );

  const flowCycleWidget = useMemo(
    () => (flowWidgets || []).find((widget) => widget?.widget_id === 'flow_cycle_time'),
    [flowWidgets]
  );
  const flowThroughputWidget = useMemo(
    () => (flowWidgets || []).find((widget) => widget?.widget_id === 'flow_throughput'),
    [flowWidgets]
  );

  const overviewSummaryMetrics = useMemo(
    () => buildOverviewSummaryMetrics(overviewSummaryWidget?.data, aiInvolvedWidget?.data),
    [overviewSummaryWidget?.data, aiInvolvedWidget?.data]
  );

  const flowSummaryMetrics = useMemo(
    () => buildFlowSummaryMetrics(flowCycleWidget?.data, flowThroughputWidget?.data),
    [flowCycleWidget?.data, flowThroughputWidget?.data]
  );

  const correctionColumns = useMemo(() => ([
    {
      title: '系统',
      dataIndex: 'system_id',
      key: 'system_id',
      ellipsis: true,
      render: (value, record) => record?.system_name || value || '-',
    },
    { title: '修正率', dataIndex: 'correction_rate', key: 'correction_rate' },
    { title: '新增率', dataIndex: 'addition_rate', key: 'addition_rate' },
    { title: '样本任务数', dataIndex: 'sample_tasks', key: 'sample_tasks' },
  ]), []);

  const hitColumns = useMemo(() => ([
    {
      title: '系统',
      dataIndex: 'system_id',
      key: 'system_id',
      ellipsis: true,
      render: (value, record) => record?.system_name || value || '-',
    },
    { title: '命中率', dataIndex: 'hit_rate', key: 'hit_rate' },
    { title: '画像分', dataIndex: 'profile_score', key: 'profile_score' },
    { title: '样本任务数', dataIndex: 'sample_tasks', key: 'sample_tasks' },
  ]), []);

  const contributionColumns = useMemo(() => ([
    { title: '项目经理', dataIndex: 'owner_name', key: 'owner_name', ellipsis: true },
    { title: '画像贡献', dataIndex: 'contribution_score', key: 'contribution_score' },
    { title: '文档数', dataIndex: 'document_count', key: 'document_count' },
    { title: '系统数', dataIndex: 'systems_count', key: 'systems_count' },
  ]), []);

  const cycleColumns = useMemo(() => ([
    { title: '项目经理', dataIndex: 'owner_name', key: 'owner_name', ellipsis: true },
    { title: '评估周期（天）', dataIndex: 'avg_cycle_days', key: 'avg_cycle_days' },
    { title: '样本任务数', dataIndex: 'sample_tasks', key: 'sample_tasks' },
  ]), []);

  const deviationColumns = useMemo(() => ([
    {
      title: '系统',
      dataIndex: 'system_id',
      key: 'system_id',
      ellipsis: true,
      render: (value, record) => record?.system_name || value || '-',
    },
    { title: '平均偏差(%)', dataIndex: 'avg_deviation_pct', key: 'avg_deviation_pct' },
    { title: '最大偏差(%)', dataIndex: 'max_deviation_pct', key: 'max_deviation_pct' },
    { title: '最小偏差(%)', dataIndex: 'min_deviation_pct', key: 'min_deviation_pct' },
  ]), []);

  const trendColumns = useMemo(() => ([
    {
      title: '系统',
      dataIndex: 'system_id',
      key: 'system_id',
      ellipsis: true,
      render: (value, record) => record?.system_name || value || '-',
    },
    { title: '学习趋势', dataIndex: 'trend', key: 'trend' },
    { title: '首点修正率(%)', dataIndex: 'first_correction_rate', key: 'first_correction_rate' },
    { title: '最新修正率(%)', dataIndex: 'latest_correction_rate', key: 'latest_correction_rate' },
  ]), []);

  const profileColumns = useMemo(() => ([
    { title: '系统', dataIndex: 'system_name', key: 'system_name', ellipsis: true },
    { title: '完整度', dataIndex: 'completeness_score', key: 'completeness_score' },
    { title: '文档', dataIndex: 'documents', key: 'documents' },
    { title: '代码扫描', dataIndex: 'code_scan', key: 'code_scan' },
    { title: 'ESB', dataIndex: 'esb', key: 'esb' },
  ]), []);

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      {errorText && (
        <Alert
          type="error"
          showIcon
          message="多维报表加载失败"
          description={errorText}
          action={(
            <Button icon={<ReloadOutlined />} onClick={fetchReports}>
              重试
            </Button>
          )}
        />
      )}

      <Card title="总览统计">
        <Space direction="vertical" size={12} style={{ width: '100%' }}>
          {loading ? <Spin /> : renderSummaryStats(overviewSummaryMetrics)}
          <Row gutter={[12, 12]}>
            <Col xs={24} lg={8}>
              {renderMetricCard({
                title: '修正率分析',
                loading,
                items: pmCorrectionWidget?.data?.items || [],
                columns: correctionColumns,
                logicText: SECTION_LOGIC_TEXT.correction_rate,
              })}
            </Col>
            <Col xs={24} lg={8}>
              {renderMetricCard({
                title: '命中率分析',
                loading,
                items: aiHitWidget?.data?.items || [],
                columns: hitColumns,
                logicText: SECTION_LOGIC_TEXT.hit_rate,
              })}
            </Col>
            <Col xs={24} lg={8}>
              {renderMetricCard({
                title: '画像贡献分析',
                loading,
                items: profileContributionWidget?.data?.items || [],
                columns: contributionColumns,
                logicText: SECTION_LOGIC_TEXT.profile_contribution,
              })}
            </Col>
          </Row>
        </Space>
      </Card>

      <Card title="系统影响分析">
        <Space direction="vertical" size={12} style={{ width: '100%' }}>
          <Text type="secondary">系统影响分析基于近90天已完成任务。</Text>
          {loading ? (
            <Spin />
          ) : profileCompletenessWidget ? (
            renderItemsTable(profileCompletenessWidget?.data?.items || [], profileColumns)
          ) : (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无数据" />
          )}
        </Space>
      </Card>

      <Card title="流程健康度">
        <Space direction="vertical" size={12} style={{ width: '100%' }}>
          {loading ? <Spin /> : renderSummaryStats(flowSummaryMetrics)}
          <Row gutter={[12, 12]}>
            <Col xs={24} lg={8}>
              {renderMetricCard({
                title: '评估周期分析',
                loading,
                items: evaluationCycleWidget?.data?.items || [],
                columns: cycleColumns,
                logicText: SECTION_LOGIC_TEXT.evaluation_cycle,
              })}
            </Col>
            <Col xs={24} lg={8}>
              {renderMetricCard({
                title: '偏差监控分析',
                loading,
                items: deviationWidget?.data?.items || [],
                columns: deviationColumns,
                logicText: SECTION_LOGIC_TEXT.deviation_monitoring,
              })}
            </Col>
            <Col xs={24} lg={8}>
              {renderMetricCard({
                title: '学习趋势分析',
                loading,
                items: learningTrendWidget?.data?.items || [],
                columns: trendColumns,
                logicText: SECTION_LOGIC_TEXT.learning_trend,
              })}
            </Col>
          </Row>
        </Space>
      </Card>
    </Space>
  );
};

export default DashboardReportsPage;
