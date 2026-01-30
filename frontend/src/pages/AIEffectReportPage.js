import React, { useEffect, useMemo, useState, useCallback } from 'react';
import {
  Button,
  Card,
  DatePicker,
  Form,
  message,
  Statistic,
  Table,
  Row,
  Col,
  Menu,
  Select,
  Space,
  Typography,
  Empty,
} from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import axios from 'axios';
import ReactECharts from 'echarts-for-react';
import usePermission from '../hooks/usePermission';
import './AIEffectReportPage.css';

const { RangePicker } = DatePicker;
const { Title, Text } = Typography;

const metricLabels = {
  man_day_accuracy: '人天准确率',
  feature_retention: '功能点保留率',
  field_modification_rate: '字段修改率',
  knowledge_hit_rate: '知识库命中率',
  system_identification_accuracy: '系统识别准确率',
  new_feature_ratio: '新增功能点占比',
  manager_trust: '项目经理信任度',
  system_rename_rate: '系统重命名率',
};

const metricKeys = Object.keys(metricLabels);

const buildGroupMetrics = (items, getKey) => {
  const map = new Map();
  items.forEach((item) => {
    const key = getKey(item);
    if (!key) return;
    if (!map.has(key)) {
      map.set(key, { key, name: key, metrics: {}, count: 0 });
    }
    const entry = map.get(key);
    entry.count += 1;
    const metrics = item.metrics || {};
    metricKeys.forEach((metric) => {
      entry.metrics[metric] = (entry.metrics[metric] || 0) + Number(metrics[metric] || 0);
    });
  });

  return Array.from(map.values()).map((entry) => {
    const averaged = {};
    metricKeys.forEach((metric) => {
      averaged[metric] = entry.count ? Number((entry.metrics[metric] / entry.count).toFixed(2)) : 0;
    });
    return {
      key: entry.key,
      name: entry.name,
      count: entry.count,
      metrics: averaged,
    };
  });
};

const buildTrendData = (items, metricKey) => {
  const map = new Map();
  items.forEach((item) => {
    const date = (item.created_at || '').slice(0, 10);
    if (!date) return;
    if (!map.has(date)) {
      map.set(date, { date, total: 0, count: 0 });
    }
    const entry = map.get(date);
    entry.total += Number(item.metrics?.[metricKey] || 0);
    entry.count += 1;
  });
  return Array.from(map.values())
    .map((entry) => ({
      date: entry.date,
      value: entry.count ? Number((entry.total / entry.count).toFixed(2)) : 0,
    }))
    .sort((a, b) => a.date.localeCompare(b.date));
};

const BarChart = ({ data, metricKey, emptyText }) => {
  const height = Math.max(240, data.length * 36);
  const option = useMemo(() => {
    if (!data.length) {
      return null;
    }
    const categories = data.map((item) => item.name);
    const values = data.map((item) => Number(item.metrics?.[metricKey] || 0));
    return {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        valueFormatter: (value) => `${value}%`,
      },
      grid: { left: 120, right: 24, top: 20, bottom: 20 },
      xAxis: {
        type: 'value',
        min: 0,
        max: 100,
        axisLabel: { formatter: '{value}%' },
        splitLine: { lineStyle: { color: '#eef1f6' } },
      },
      yAxis: {
        type: 'category',
        data: categories,
        axisLabel: { width: 110, overflow: 'truncate' },
      },
      series: [
        {
          type: 'bar',
          data: values,
          barWidth: 16,
          itemStyle: {
            color: '#3b6cff',
            borderRadius: [4, 4, 4, 4],
          },
          label: {
            show: true,
            position: 'right',
            formatter: '{c}%',
          },
        },
      ],
    };
  }, [data, metricKey]);

  if (!data.length) {
    return <Empty description={emptyText} />;
  }

  return <ReactECharts option={option} style={{ height }} className="ai-chart" />;
};

const TrendChart = ({ data }) => {
  const option = useMemo(() => {
    if (!data.length) {
      return null;
    }
    return {
      tooltip: { trigger: 'axis', valueFormatter: (value) => `${value}%` },
      grid: { left: 40, right: 24, top: 20, bottom: 40 },
      xAxis: {
        type: 'category',
        data: data.map((item) => item.date),
        axisLabel: { rotate: 30 },
      },
      yAxis: {
        type: 'value',
        min: 0,
        max: 100,
        axisLabel: { formatter: '{value}%' },
        splitLine: { lineStyle: { color: '#eef1f6' } },
      },
      series: [
        {
          type: 'line',
          data: data.map((item) => item.value),
          smooth: true,
          symbol: 'circle',
          symbolSize: 8,
          lineStyle: { color: '#3b6cff', width: 2 },
          itemStyle: { color: '#3b6cff' },
          areaStyle: { color: 'rgba(59, 108, 255, 0.12)' },
        },
      ],
    };
  }, [data]);

  if (!data.length) {
    return <Empty description="暂无趋势数据" />;
  }

  return <ReactECharts option={option} style={{ height: 280 }} className="ai-chart" />;
};

const AIEffectReportPage = () => {
  const { isAdmin, isManager, isExpert } = usePermission();
  const isExpertOnly = isExpert && !isAdmin && !isManager;
  const [form] = Form.useForm();
  const [summary, setSummary] = useState({});
  const [snapshots, setSnapshots] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeSection, setActiveSection] = useState('system');
  const [systemMetric, setSystemMetric] = useState('man_day_accuracy');
  const [moduleMetric, setModuleMetric] = useState('feature_retention');
  const [managerMetric, setManagerMetric] = useState('manager_trust');
  const [trendMetric, setTrendMetric] = useState('man_day_accuracy');

  const fetchReport = useCallback(async (params = {}) => {
    try {
      setLoading(true);
      const response = await axios.get('/api/v1/reports/ai-effect', { params });
      const data = response.data.data || {};
      setSummary(data.summary || {});
      setSnapshots(data.snapshots || []);
    } catch (error) {
      message.error(error.response?.data?.detail || '获取AI效果报告失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  const handleFilter = async () => {
    const values = await form.validateFields();
    const params = {};
    if (values.system_name) params.system_name = values.system_name;
    if (values.module) params.module = values.module;
    if (values.manager_id) params.manager_id = values.manager_id;
    if (values.round) params.round = Number(values.round);
    if (values.dateRange && values.dateRange.length === 2) {
      params.date_from = values.dateRange[0].toISOString();
      params.date_to = values.dateRange[1].toISOString();
    }
    fetchReport(params);
  };

  const navItems = useMemo(() => {
    const items = [
      { key: 'system', label: '系统对比', anchor: 'section-system' },
      { key: 'module', label: '类型分析', anchor: 'section-module' },
      { key: 'trend', label: '时间趋势', anchor: 'section-trend' },
    ];
    if (!isExpertOnly) {
      items.push({ key: 'manager', label: '项目经理维度', anchor: 'section-manager' });
    }
    return items;
  }, [isExpertOnly]);

  const handleNavClick = (key) => {
    const target = navItems.find((item) => item.key === key);
    if (target) {
      const el = document.getElementById(target.anchor);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }
    setActiveSection(key);
  };

  const systemGroups = useMemo(() => {
    const items = snapshots.filter((item) => item.system && !item.module);
    return buildGroupMetrics(items, (item) => item.system).sort((a, b) => (b.metrics[systemMetric] || 0) - (a.metrics[systemMetric] || 0));
  }, [snapshots, systemMetric]);

  const moduleGroups = useMemo(() => {
    const items = snapshots.filter((item) => item.module);
    return buildGroupMetrics(items, (item) => item.module).sort((a, b) => (b.metrics[moduleMetric] || 0) - (a.metrics[moduleMetric] || 0));
  }, [snapshots, moduleMetric]);

  const managerGroups = useMemo(() => {
    if (isExpertOnly) {
      return [];
    }
    const baseItems = snapshots.filter((item) => !item.system && !item.module);
    return buildGroupMetrics(baseItems, (item) => item.manager_name || item.manager_id || '未知').sort((a, b) => (b.metrics[managerMetric] || 0) - (a.metrics[managerMetric] || 0));
  }, [snapshots, managerMetric, isExpertOnly]);

  const trendData = useMemo(() => {
    const baseItems = snapshots.filter((item) => !item.system && !item.module);
    const source = baseItems.length ? baseItems : snapshots;
    return buildTrendData(source, trendMetric);
  }, [snapshots, trendMetric]);

  const managerOptions = useMemo(() => {
    if (isExpertOnly) {
      return [];
    }
    const items = new Map();
    snapshots.forEach((item) => {
      const name = item.manager_name || item.manager_id;
      if (name) {
        items.set(name, item.manager_id || name);
      }
    });
    return Array.from(items.entries()).map(([name, id]) => ({ label: name, value: id }));
  }, [snapshots, isExpertOnly]);

  const systemOptions = useMemo(() => {
    const set = new Set();
    snapshots.forEach((item) => {
      if (item.system) set.add(item.system);
    });
    return Array.from(set).map((value) => ({ label: value, value }));
  }, [snapshots]);

  const moduleOptions = useMemo(() => {
    const set = new Set();
    snapshots.forEach((item) => {
      if (item.module) set.add(item.module);
    });
    return Array.from(set).map((value) => ({ label: value, value }));
  }, [snapshots]);

  const roundOptions = useMemo(() => {
    const set = new Set();
    snapshots.forEach((item) => {
      if (item.round) set.add(item.round);
    });
    return Array.from(set).sort().map((value) => ({ label: `第${value}轮`, value }));
  }, [snapshots]);

  const columns = useMemo(() => {
    const baseColumns = [
      { title: '时间', dataIndex: 'created_at', key: 'created_at', width: 180 },
      { title: '任务ID', dataIndex: 'task_id', key: 'task_id', width: 200 },
      { title: '轮次', dataIndex: 'round', key: 'round', width: 80 },
      { title: '系统', dataIndex: 'system', key: 'system', width: 120, render: (value) => value || '-' },
      { title: '模块', dataIndex: 'module', key: 'module', width: 120, render: (value) => value || '-' },
      { title: '项目经理', dataIndex: 'manager_name', key: 'manager_name', width: 120 },
      {
        title: '人天准确率',
        dataIndex: ['metrics', 'man_day_accuracy'],
        key: 'man_day_accuracy',
        width: 120,
        render: (value) => `${value || 0}%`,
      },
      {
        title: '功能点保留率',
        dataIndex: ['metrics', 'feature_retention'],
        key: 'feature_retention',
        width: 120,
        render: (value) => `${value || 0}%`,
      },
      {
        title: '字段修改率',
        dataIndex: ['metrics', 'field_modification_rate'],
        key: 'field_modification_rate',
        width: 120,
        render: (value) => `${value || 0}%`,
      },
      {
        title: '知识库命中率',
        dataIndex: ['metrics', 'knowledge_hit_rate'],
        key: 'knowledge_hit_rate',
        width: 120,
        render: (value) => `${value || 0}%`,
      },
      {
        title: '系统识别准确率',
        dataIndex: ['metrics', 'system_identification_accuracy'],
        key: 'system_identification_accuracy',
        width: 140,
        render: (value) => `${value || 0}%`,
      },
      {
        title: '新增功能点占比',
        dataIndex: ['metrics', 'new_feature_ratio'],
        key: 'new_feature_ratio',
        width: 140,
        render: (value) => `${value || 0}%`,
      },
      {
        title: '项目经理信任度',
        dataIndex: ['metrics', 'manager_trust'],
        key: 'manager_trust',
        width: 140,
        render: (value) => `${value || 0}%`,
      },
      {
        title: '系统重命名率',
        dataIndex: ['metrics', 'system_rename_rate'],
        key: 'system_rename_rate',
        width: 140,
        render: (value) => `${value || 0}%`,
      },
    ];
    if (isExpertOnly) {
      return baseColumns.filter((col) => col.key !== 'manager_name');
    }
    return baseColumns;
  }, [isExpertOnly]);

  useEffect(() => {
    if (isExpertOnly && activeSection === 'manager') {
      setActiveSection('system');
    }
  }, [isExpertOnly, activeSection]);

  return (
    <div className="ai-effect-report">
      <Row gutter={16}>
        <Col xs={24} lg={5}>
          <Card className="ai-effect-nav" title="维度导航">
            <Menu
              mode="inline"
              selectedKeys={[activeSection]}
              items={navItems.map((item) => ({ key: item.key, label: item.label }))}
              onClick={({ key }) => handleNavClick(key)}
            />
          </Card>
        </Col>
        <Col xs={24} lg={19}>
          <Card
            title="AI效果报告"
            extra={(
              <Space>
                {isExpertOnly && (
                  <Text type="secondary">仅展示我参与任务的汇总匿名指标</Text>
                )}
                <Button icon={<ReloadOutlined />} onClick={() => fetchReport()}>
                  刷新
                </Button>
              </Space>
            )}
          >
            <Form form={form} layout="inline" className="ai-filter-form">
              <Form.Item name="system_name" label="系统">
                <Select allowClear placeholder="系统名称" options={systemOptions} style={{ minWidth: 140 }} />
              </Form.Item>
              <Form.Item name="module" label="模块">
                <Select allowClear placeholder="功能模块" options={moduleOptions} style={{ minWidth: 140 }} />
              </Form.Item>
              {!isExpertOnly && (
                <Form.Item name="manager_id" label="项目经理">
                  <Select
                    allowClear
                    showSearch
                    placeholder="项目经理"
                    options={managerOptions}
                    style={{ minWidth: 140 }}
                    filterOption={(input, option) => (option?.label || '').includes(input)}
                  />
                </Form.Item>
              )}
              <Form.Item name="round" label="轮次">
                <Select allowClear placeholder="轮次" options={roundOptions} style={{ minWidth: 120 }} />
              </Form.Item>
              <Form.Item name="dateRange" label="时间范围">
                <RangePicker />
              </Form.Item>
              <Form.Item>
                <Button type="primary" onClick={handleFilter}>
                  查询
                </Button>
              </Form.Item>
            </Form>

            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col span={6}>
                <Statistic title="人天准确率" value={summary.man_day_accuracy || 0} suffix="%" />
              </Col>
              <Col span={6}>
                <Statistic title="功能点保留率" value={summary.feature_retention || 0} suffix="%" />
              </Col>
              <Col span={6}>
                <Statistic title="字段修改率" value={summary.field_modification_rate || 0} suffix="%" />
              </Col>
              <Col span={6}>
                <Statistic title="知识库命中率" value={summary.knowledge_hit_rate || 0} suffix="%" />
              </Col>
            </Row>
            <Row gutter={16} style={{ marginBottom: 24 }}>
              <Col span={6}>
                <Statistic title="系统识别准确率" value={summary.system_identification_accuracy || 0} suffix="%" />
              </Col>
              <Col span={6}>
                <Statistic title="新增功能点占比" value={summary.new_feature_ratio || 0} suffix="%" />
              </Col>
              <Col span={6}>
                <Statistic title="项目经理信任度" value={summary.manager_trust || 0} suffix="%" />
              </Col>
              <Col span={6}>
                <Statistic title="系统重命名率" value={summary.system_rename_rate || 0} suffix="%" />
              </Col>
            </Row>
            <Row gutter={16} style={{ marginBottom: 24 }}>
              <Col span={6}>
                <Statistic title="样本数量" value={snapshots.length} />
              </Col>
            </Row>

            <div id="section-system" className="ai-section">
              <Title level={4}>系统对比</Title>
              <Space align="center" style={{ marginBottom: 16 }}>
                <Text type="secondary">指标</Text>
                <Select
                  value={systemMetric}
                  onChange={setSystemMetric}
                  options={metricKeys.map((key) => ({ label: metricLabels[key], value: key }))}
                  style={{ width: 220 }}
                />
              </Space>
              <BarChart
                data={systemGroups}
                metricKey={systemMetric}
                emptyText="暂无系统维度数据"
              />
            </div>

            <div id="section-module" className="ai-section">
              <Title level={4}>类型分析（功能模块）</Title>
              <Space align="center" style={{ marginBottom: 16 }}>
                <Text type="secondary">指标</Text>
                <Select
                  value={moduleMetric}
                  onChange={setModuleMetric}
                  options={metricKeys.map((key) => ({ label: metricLabels[key], value: key }))}
                  style={{ width: 220 }}
                />
              </Space>
              <BarChart
                data={moduleGroups}
                metricKey={moduleMetric}
                emptyText="暂无模块维度数据"
              />
            </div>

            <div id="section-trend" className="ai-section">
              <Title level={4}>时间趋势</Title>
              <Space align="center" style={{ marginBottom: 16 }}>
                <Text type="secondary">指标</Text>
                <Select
                  value={trendMetric}
                  onChange={setTrendMetric}
                  options={metricKeys.map((key) => ({ label: metricLabels[key], value: key }))}
                  style={{ width: 220 }}
                />
              </Space>
              <TrendChart data={trendData} />
            </div>

            {!isExpertOnly && (
              <div id="section-manager" className="ai-section">
                <Title level={4}>项目经理维度</Title>
                <Space align="center" style={{ marginBottom: 16 }}>
                  <Text type="secondary">指标</Text>
                  <Select
                    value={managerMetric}
                    onChange={setManagerMetric}
                    options={metricKeys.map((key) => ({ label: metricLabels[key], value: key }))}
                    style={{ width: 220 }}
                  />
                </Space>
                <BarChart
                  data={managerGroups}
                  metricKey={managerMetric}
                  emptyText="暂无项目经理维度数据"
                />
              </div>
            )}

            <div className="ai-section">
              <Title level={4}>明细列表</Title>
              <Table
                rowKey="id"
                columns={columns}
                dataSource={snapshots}
                loading={loading}
                scroll={{ x: 1600 }}
                pagination={{ pageSize: 10 }}
              />
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default AIEffectReportPage;
