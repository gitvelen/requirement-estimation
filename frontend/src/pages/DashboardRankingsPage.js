import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Empty,
  Space,
  Spin,
  Table,
  Tabs,
  Typography,
} from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import axios from 'axios';

const { Text } = Typography;

const LOGIC_TEXT = {
  evaluation_efficiency_ranking: '计算逻辑：评估效率 = 已完成评估数 / 累计评估耗时（天），仅统计近90天数据',
  task_submission_ranking: '计算逻辑：统计近90天内各项目经理提交的任务总数，按数量降序排列',
  system_activity_ranking: '计算逻辑：统计近90天内各系统关联的评估任务数，按数量降序排列',
};

const resolveRowKey = (record, index) => (
  record?.expert_id || record?.manager_id || record?.system_id || record?.id || index
);

const isRequestCanceled = (error) => (
  error?.code === 'ERR_CANCELED'
  || error?.name === 'CanceledError'
  || error?.name === 'AbortError'
);

const DashboardRankingsPage = () => {
  const [loading, setLoading] = useState(false);
  const [errorText, setErrorText] = useState('');
  const [widgets, setWidgets] = useState([]);
  const requestControllerRef = useRef(null);
  const mountedRef = useRef(false);

  const abortActiveRequest = useCallback(() => {
    const controller = requestControllerRef.current;
    requestControllerRef.current = null;
    controller?.abort();
  }, []);

  const fetchRankings = useCallback(async () => {
    abortActiveRequest();
    const controller = new AbortController();
    requestControllerRef.current = controller;
    setLoading(true);
    setErrorText('');
    try {
      const response = await axios.post('/api/v1/efficiency/dashboard/query', {
        page: 'rankings',
        perspective: 'executive',
        filters: {},
      }, {
        signal: controller.signal,
      });
      if (!mountedRef.current || requestControllerRef.current !== controller) {
        return;
      }
      const payload = response.data?.result || {};
      setWidgets(Array.isArray(payload.widgets) ? payload.widgets : []);
    } catch (error) {
      if (isRequestCanceled(error)) {
        return;
      }
      if (!mountedRef.current || requestControllerRef.current !== controller) {
        return;
      }
      const responseData = error.response?.data;
      setErrorText(responseData?.message || responseData?.detail || '排行榜加载失败');
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
    fetchRankings();
  }, [fetchRankings]);

  const widgetsById = useMemo(() => {
    const next = {};
    (widgets || []).forEach((widget) => {
      if (!widget?.widget_id) {
        return;
      }
      next[widget.widget_id] = widget;
    });
    return next;
  }, [widgets]);

  const efficiencyItems = widgetsById?.evaluation_efficiency_ranking?.data?.items || [];
  const submissionItems = widgetsById?.task_submission_ranking?.data?.items || [];
  const activityItems = widgetsById?.system_activity_ranking?.data?.items || [];

  const efficiencyColumns = useMemo(() => ([
    { title: '专家', dataIndex: 'expert_name', key: 'expert_name', ellipsis: true },
    { title: '已完成评估数', dataIndex: 'completed_evaluations', key: 'completed_evaluations' },
    { title: '累计评估耗时（天）', dataIndex: 'evaluation_time_days', key: 'evaluation_time_days' },
    { title: '评估效率', dataIndex: 'efficiency', key: 'efficiency' },
  ]), []);

  const submissionColumns = useMemo(() => ([
    { title: '项目经理', dataIndex: 'manager_name', key: 'manager_name', ellipsis: true },
    { title: '提交任务数', dataIndex: 'task_count', key: 'task_count' },
  ]), []);

  const activityColumns = useMemo(() => ([
    {
      title: '系统',
      dataIndex: 'system_id',
      key: 'system_id',
      ellipsis: true,
      render: (value, record) => record?.system_name || value || '-',
    },
    { title: '关联任务数', dataIndex: 'task_count', key: 'task_count' },
  ]), []);

  const renderTabBody = ({ widgetId, items, columns }) => (
    <Space direction="vertical" size={12} style={{ width: '100%' }}>
      {loading ? (
        <Spin />
      ) : errorText ? (
        <Alert
          type="error"
          showIcon
          message="排行榜加载失败"
          description={errorText}
          action={(
            <Button icon={<ReloadOutlined />} onClick={fetchRankings}>
              重试
            </Button>
          )}
        />
      ) : !items.length ? (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无数据" />
      ) : (
        <Table
          rowKey={resolveRowKey}
          columns={columns}
          dataSource={items}
          pagination={{ pageSize: 20, hideOnSinglePage: true }}
          size="small"
        />
      )}
      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <Text type="secondary">{LOGIC_TEXT[widgetId]}</Text>
      </div>
    </Space>
  );

  const tabItems = [
    {
      key: 'evaluation_efficiency_ranking',
      label: '评估效率排行',
      children: renderTabBody({
        widgetId: 'evaluation_efficiency_ranking',
        items: efficiencyItems,
        columns: efficiencyColumns,
      }),
    },
    {
      key: 'task_submission_ranking',
      label: '任务提交排行',
      children: renderTabBody({
        widgetId: 'task_submission_ranking',
        items: submissionItems,
        columns: submissionColumns,
      }),
    },
    {
      key: 'system_activity_ranking',
      label: '系统活跃排行',
      children: renderTabBody({
        widgetId: 'system_activity_ranking',
        items: activityItems,
        columns: activityColumns,
      }),
    },
  ];

  return (
    <Card>
      <Tabs items={tabItems} />
    </Card>
  );
};

export default DashboardRankingsPage;
