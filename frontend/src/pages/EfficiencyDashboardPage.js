import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Empty,
  Menu,
  Select,
  Space,
  Spin,
  Table,
  Tag,
  Typography,
} from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import usePermission from '../hooks/usePermission';
import useAuth from '../hooks/useAuth';
import PageHeader from '../components/PageHeader';
import './EfficiencyDashboardPage.css';

const { Text } = Typography;

const PAGE_OPTIONS = [
  { key: 'overview', label: '总览' },
  { key: 'rankings', label: '排行榜' },
  { key: 'ai', label: 'AI表现' },
  { key: 'system', label: '系统影响' },
  { key: 'flow', label: '流程健康' },
];

const PERSPECTIVE_OPTIONS = [
  { label: '管理层（executive）', value: 'executive' },
  { label: '负责人（owner）', value: 'owner' },
  { label: '专家（expert）', value: 'expert' },
];

const TIME_RANGE_OPTIONS = [
  { label: '最近7天', value: 'last_7d' },
  { label: '最近30天', value: 'last_30d' },
  { label: '本月', value: 'this_month' },
  { label: '上月', value: 'last_month' },
];

const parseBoolean = (value) => {
  if (value === undefined || value === null || value === '') {
    return undefined;
  }
  const text = String(value).toLowerCase();
  if (['1', 'true', 'yes', 'y'].includes(text)) {
    return true;
  }
  if (['0', 'false', 'no', 'n'].includes(text)) {
    return false;
  }
  return undefined;
};

const resolveDefaultPerspective = ({ isManager, isExpert }) => {
  if (isManager) {
    return 'owner';
  }
  if (isExpert) {
    return 'expert';
  }
  return 'executive';
};

const mapDrilldownToTaskQuery = (filters) => {
  const params = new URLSearchParams();
  params.set('from_dashboard', '1');
  params.set('group_by_status', 'true');

  const timeRange = filters?.time_range;
  if (timeRange) {
    params.set('time_range', String(timeRange));
  }
  if (filters?.start_at) {
    params.set('start_at', String(filters.start_at));
  }
  if (filters?.end_at) {
    params.set('end_at', String(filters.end_at));
  }
  if (typeof filters?.ai_involved === 'boolean') {
    params.set('ai_involved', String(filters.ai_involved));
  }

  if (filters?.system_id) {
    params.set('system_id', String(filters.system_id));
  } else if (Array.isArray(filters?.system_ids) && filters.system_ids.length) {
    params.set('system_id', String(filters.system_ids[0]));
  }

  if (filters?.owner_id) {
    params.set('owner_id', String(filters.owner_id));
  }
  if (filters?.expert_id) {
    params.set('expert_id', String(filters.expert_id));
  }
  if (filters?.project_id) {
    params.set('project_id', String(filters.project_id));
  } else if (Array.isArray(filters?.project_ids) && filters.project_ids.length) {
    params.set('project_id', String(filters.project_ids[0]));
  }

  return params.toString();
};

const renderWidgetSummary = (data = {}) => {
  const entries = Object.entries(data).filter(([, value]) => !Array.isArray(value) && typeof value !== 'object');
  if (!entries.length) {
    return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无摘要数据" />;
  }

  return (
    <Space wrap>
      {entries.map(([key, value]) => (
        <Tag key={key} color="blue">
          {`${key}: ${value}`}
        </Tag>
      ))}
    </Space>
  );
};

const EfficiencyDashboardPage = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { isManager, isExpert } = usePermission();
  const { user } = useAuth();

  const defaultPerspective = useMemo(
    () => resolveDefaultPerspective({ isManager, isExpert }),
    [isManager, isExpert]
  );

  const [pageKey, setPageKey] = useState(() => {
    const raw = searchParams.get('page');
    return PAGE_OPTIONS.some((item) => item.key === raw) ? raw : 'overview';
  });
  const [perspective, setPerspective] = useState(() => {
    const raw = searchParams.get('perspective');
    return PERSPECTIVE_OPTIONS.some((item) => item.value === raw) ? raw : defaultPerspective;
  });
  const [timeRange, setTimeRange] = useState(() => searchParams.get('time_range') || 'last_30d');
  const [aiInvolved, setAiInvolved] = useState(() => {
    const parsed = parseBoolean(searchParams.get('ai_involved'));
    return parsed === undefined ? 'all' : parsed;
  });

  const [loading, setLoading] = useState(false);
  const [widgets, setWidgets] = useState([]);
  const [errorText, setErrorText] = useState('');

  const syncQuery = useCallback(
    (next) => {
      const params = new URLSearchParams();
      params.set('page', next.pageKey);
      params.set('perspective', next.perspective);
      params.set('time_range', next.timeRange);
      if (typeof next.aiInvolved === 'boolean') {
        params.set('ai_involved', String(next.aiInvolved));
      }
      setSearchParams(params, { replace: true });
    },
    [setSearchParams]
  );

  useEffect(() => {
    syncQuery({ pageKey, perspective, timeRange, aiInvolved });
  }, [pageKey, perspective, timeRange, aiInvolved, syncQuery]);

  const fetchDashboard = useCallback(async () => {
    setLoading(true);
    setErrorText('');
    try {
      const filters = {
        time_range: timeRange,
      };

      if (typeof aiInvolved === 'boolean') {
        filters.ai_involved = aiInvolved;
      }

      if (perspective === 'owner' && isManager && user?.id) {
        filters.owner_id = user.id;
      }
      if (perspective === 'expert' && isExpert) {
        filters.expert_id = user?.username || user?.id;
      }

      const response = await axios.post('/api/v1/efficiency/dashboard/query', {
        page: pageKey,
        perspective,
        filters,
      });

      const payload = response.data?.result || {};
      setWidgets(Array.isArray(payload.widgets) ? payload.widgets : []);
    } catch (error) {
      const responseData = error.response?.data;
      const messageText = responseData?.message || responseData?.detail || '效能看板加载失败';
      setErrorText(messageText);
    } finally {
      setLoading(false);
    }
  }, [pageKey, perspective, timeRange, aiInvolved, isManager, isExpert, user]);

  useEffect(() => {
    fetchDashboard();
  }, [fetchDashboard]);

  const handleWidgetDrilldown = (filters = {}) => {
    const queryString = mapDrilldownToTaskQuery(filters);
    navigate(`/tasks?${queryString}`);
  };


  const renderItemsTable = (widget, items) => {
    if (!items.length) {
      return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无榜单数据" />;
    }

    const first = items[0] || {};
    const keys = Object.keys(first).filter((key) => key !== 'drilldown_filters');
    const dataColumns = keys.map((key) => ({
      title: key,
      dataIndex: key,
      key,
      ellipsis: true,
      render: (value) => (value === null || value === undefined || value === '' ? '-' : String(value)),
    }));

    dataColumns.push({
      title: '操作',
      key: 'action',
      width: 100,
      render: (_, record) => (
        <Button
          type="link"
          size="small"
          onClick={() => {
            const mergedFilters = {
              ...(widget.drilldown_filters || {}),
              ...(record.drilldown_filters || {}),
            };
            if (!mergedFilters.system_id && record.system_id) {
              mergedFilters.system_id = record.system_id;
            }
            if (!mergedFilters.owner_id && record.owner_id) {
              mergedFilters.owner_id = record.owner_id;
            }
            handleWidgetDrilldown(mergedFilters);
          }}
        >
          查看明细
        </Button>
      ),
    });

    return (
      <Table
        size="small"
        rowKey={(record, index) => record.system_id || record.owner_id || record.task_id || index}
        columns={dataColumns}
        dataSource={items}
        pagination={false}
        scroll={{ x: true }}
      />
    );
  };


  return (
    <div>
      <PageHeader title="效能看板" subtitle="统一口径展示趋势、排行与任务下钻" />
      <div className="dashboard-layout">
        <Card className="dashboard-side-card" bodyStyle={{ padding: 8 }}>
          <Menu
            mode="inline"
            selectedKeys={[pageKey]}
            items={PAGE_OPTIONS}
            onClick={(event) => setPageKey(event.key)}
          />
        </Card>

        <div className="dashboard-main">
          <Card style={{ marginBottom: 12 }}>
            <Space wrap>
              <Text strong>视角</Text>
              <Select
                value={perspective}
                style={{ width: 220 }}
                options={PERSPECTIVE_OPTIONS}
                onChange={setPerspective}
              />

              <Text strong>时间范围</Text>
              <Select
                value={timeRange}
                style={{ width: 160 }}
                options={TIME_RANGE_OPTIONS}
                onChange={setTimeRange}
              />

              <Text strong>AI参与</Text>
              <Select
                value={aiInvolved}
                style={{ width: 140 }}
                options={[
                  { label: '全部', value: 'all' },
                  { label: '仅AI参与', value: true },
                  { label: '仅非AI参与', value: false },
                ]}
                onChange={setAiInvolved}
              />

              <Button icon={<ReloadOutlined />} onClick={fetchDashboard}>
                刷新
              </Button>
            </Space>
          </Card>

          {errorText && (
            <Alert
              type="error"
              showIcon
              message="看板加载失败"
              description={errorText}
              style={{ marginBottom: 12 }}
            />
          )}

          <Spin spinning={loading}>
            <Space direction="vertical" style={{ width: '100%' }} size={12}>
              {widgets.map((widget) => {
                  const items = Array.isArray(widget?.data?.items) ? widget.data.items : [];
                  const sampleSize = Number(widget?.sample_size || 0);
                  const showSampleHint = sampleSize > 0 && sampleSize < 10;

                  return (
                    <Card
                      key={widget.widget_id}
                      title={widget.title || widget.widget_id}
                      extra={(
                        <Space>
                          <Tag color="blue">样本量 {sampleSize}</Tag>
                          <Button
                            type="link"
                            size="small"
                            onClick={() => handleWidgetDrilldown(widget.drilldown_filters || {})}
                          >
                            查看明细
                          </Button>
                        </Space>
                      )}
                    >
                      {showSampleHint && (
                        <Alert
                          type="warning"
                          showIcon
                          message="样本较少，仅供参考"
                          style={{ marginBottom: 12 }}
                        />
                      )}
                      {items.length ? renderItemsTable(widget, items) : renderWidgetSummary(widget.data || {})}
                    </Card>
                  );
                })}
                {!loading && widgets.length === 0 && (
                  <Card>
                    <Empty description="暂无看板数据，请调整筛选后重试" />
                  </Card>
                )}
              </Space>
          </Spin>
        </div>
      </div>
    </div>
  );
};

export default EfficiencyDashboardPage;
