import React, { useEffect, useState, useCallback, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card,
  Button,
  message,
  Tag,
  Table,
  Modal,
  Form,
  Select,
  Space,
  Row,
  Col,
  Typography,
  Descriptions,
  Dropdown,
  Empty,
  Result,
} from 'antd';
import {
  ArrowLeftOutlined,
  DownloadOutlined,
  ReloadOutlined,
  DownOutlined,
} from '@ant-design/icons';
import axios from 'axios';
import usePermission from '../hooks/usePermission';
import Loading from '../components/Loading';
import { formatDateTime } from '../utils/time';

const { Text, Paragraph } = Typography;
const metricCardStyle = {
  border: '1px solid #f0f0f0',
  borderRadius: 8,
  padding: '8px 12px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: 12,
};

const reportStatusMap = {
  draft: { color: 'default', text: '草稿' },
  awaiting_assignment: { color: 'warning', text: '待分配' },
  evaluating: { color: 'processing', text: '评估中' },
  completed: { color: 'success', text: '已完成' },
  archived: { color: 'default', text: '已归档' },
};

const getReportTimestamp = (record) => {
  const source = record?.generated_at || record?.generatedAt || '';
  const parsed = Date.parse(String(source));
  return Number.isNaN(parsed) ? 0 : parsed;
};

const sortReportVersions = (versions) => (
  [...versions].sort((a, b) => {
    const tsDiff = getReportTimestamp(b) - getReportTimestamp(a);
    if (tsDiff !== 0) {
      return tsDiff;
    }
    const roundDiff = Number(b?.round || 0) - Number(a?.round || 0);
    if (roundDiff !== 0) {
      return roundDiff;
    }
    return Number(b?.version || 0) - Number(a?.version || 0);
  })
);

const toNumberOrNull = (value) => {
  if (value === undefined || value === null || value === '') {
    return null;
  }
  const num = Number(value);
  return Number.isFinite(num) ? num : null;
};

const isProfileContextUsed = (record) => Boolean(record?.profileContextUsed ?? record?.profile_context_used);

const formatProfileContextSource = (value) => {
  const normalized = String(value || 'none').trim().toLowerCase();
  if (normalized === 'canonical+wiki_candidate') {
    return '已发布画像 + wiki高置信候选补位';
  }
  if (normalized === 'canonical') {
    return '仅已发布画像';
  }
  if (normalized === 'wiki_candidate') {
    return '仅 wiki高置信候选';
  }
  return '未使用画像上下文';
};

const ReportPage = () => {
  const { taskId } = useParams();
  const navigate = useNavigate();
  const { isAdmin } = usePermission();

  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [task, setTask] = useState(null);
  const [assignVisible, setAssignVisible] = useState(false);
  const [assignmentDetailVisible, setAssignmentDetailVisible] = useState(false);
  const [assignments, setAssignments] = useState([]);
  const [assignForm] = Form.useForm();
  const [expertCandidates, setExpertCandidates] = useState([]);
  const [expertLoading, setExpertLoading] = useState(false);
  const [highDeviation, setHighDeviation] = useState({ round: null, isOfficial: false, items: [] });
  const [highDeviationLoading, setHighDeviationLoading] = useState(false);
  const [featureDetails, setFeatureDetails] = useState([]);
  const [featureLoading, setFeatureLoading] = useState(false);

  const fetchTask = useCallback(async () => {
    try {
      setLoading(true);
      setHighDeviationLoading(true);
      setFeatureLoading(true);
      const [taskRes, highRes, evalRes] = await Promise.all([
        axios.get(`/api/v1/tasks/${taskId}`),
        axios.get(`/api/v1/tasks/${taskId}/high-deviation`).catch(() => ({ data: { data: { round: null, isOfficial: false, items: [] } } })),
        axios.get(`/api/v1/tasks/${taskId}/evaluation`).catch(() => ({ data: { features: [] } })),
      ]);
      const payload = taskRes.data?.data || null;
      setTask(payload);
      setAssignments(payload?.expertAssignments || []);
      const highPayload = highRes.data?.data || { round: null, isOfficial: false, items: [] };
      setHighDeviation(highPayload);
      setFeatureDetails(Array.isArray(evalRes.data?.features) ? evalRes.data.features : []);
      setLoadError('');
    } catch (error) {
      const detail = error?.response?.data?.detail || error?.response?.data?.message || '获取任务信息失败';
      setLoadError(detail);
    } finally {
      setHighDeviationLoading(false);
      setFeatureLoading(false);
      setLoading(false);
    }
  }, [taskId]);

  useEffect(() => {
    fetchTask();
  }, [fetchTask]);

  const fetchExperts = useCallback(async () => {
    try {
      setExpertLoading(true);
      const response = await axios.get('/api/v1/users');
      const users = response.data?.data || [];
      const experts = users
        .filter((user) => (user.roles || []).includes('expert'))
        .filter((user) => user.is_active)
        .filter((user) => (user.on_duty ?? true));
      setExpertCandidates(experts);
    } catch (error) {
      message.error(error.response?.data?.detail || '获取专家列表失败');
    } finally {
      setExpertLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!assignVisible) {
      return;
    }
    fetchExperts();
  }, [assignVisible, fetchExperts]);

  const reportVersions = useMemo(
    () => sortReportVersions(task?.reportVersions || []),
    [task?.reportVersions],
  );

  const latestReport = reportVersions[0] || null;
  const historyReports = reportVersions.slice(1);

  const downloadMenuItems = useMemo(() => {
    if (!latestReport) {
      return [];
    }
    return [
      {
        key: 'latest',
        label: '最新报告',
      },
      ...historyReports.map((record) => ({
        key: `history-${record.id}`,
        label: `历史版本 · 第${record.round || '-'}轮 · v${record.version || '-'} · ${record.generated_at || record.generatedAt || '-'}`,
      })),
    ];
  }, [historyReports, latestReport]);

  const historyReportMap = useMemo(
    () => new Map(historyReports.map((record) => [`history-${record.id}`, record])),
    [historyReports],
  );

  const downloadBlob = useCallback((blobData, filename) => {
    const url = window.URL.createObjectURL(new Blob([blobData]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.remove();
  }, []);

  const handleDownloadLatest = useCallback(async () => {
    if (!latestReport?.id) {
      message.warning('暂无可导出报告');
      return;
    }
    try {
      const response = await axios.get(`/api/v1/reports/${latestReport.id}/export`, {
        responseType: 'blob',
      });
      downloadBlob(response.data, `评估报告_${taskId}.xlsx`);
      message.success('下载成功');
    } catch (error) {
      message.error(error.response?.data?.detail || '下载失败');
    }
  }, [downloadBlob, latestReport?.id, taskId]);

  const handleDownloadVersion = useCallback(async (record) => {
    try {
      const response = await axios.get(`/api/v1/reports/${record.id}/export`, {
        responseType: 'blob',
      });
      const exportName = (record.file_name || `评估报告_${taskId}`).replace(/\.pdf$/i, '.xlsx');
      downloadBlob(response.data, exportName);
      message.success('下载成功');
    } catch (error) {
      message.error(error.response?.data?.detail || '下载失败');
    }
  }, [downloadBlob, taskId]);

  const handleDownloadReportMenu = useCallback(async ({ key }) => {
    if (key === 'latest') {
      await handleDownloadLatest();
      return;
    }
    const record = historyReportMap.get(String(key));
    if (record) {
      await handleDownloadVersion(record);
    }
  }, [handleDownloadLatest, handleDownloadVersion, historyReportMap]);

  const handleDownloadDocument = async () => {
    try {
      const response = await axios.get(`/api/v1/tasks/${taskId}/document`, {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', task?.documentName || `需求文档_${taskId}.docx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      message.success('下载成功');
    } catch (error) {
      message.error(error.response?.data?.detail || '下载失败');
    }
  };

  const handleCopy = async (text) => {
    try {
      await navigator.clipboard.writeText(text);
      message.success('已复制邀请链接');
    } catch (error) {
      message.error('复制失败');
    }
  };

  const handleAssign = async () => {
    try {
      const values = await assignForm.validateFields();
      const expertIds = [values.expert1Id, values.expert2Id, values.expert3Id];
      if (new Set(expertIds).size !== expertIds.length) {
        message.error('专家不能重复');
        return;
      }
      await axios.post(`/api/v1/tasks/${taskId}/assign-experts`, {
        expertIds,
      });
      message.success('专家已分配');
      setAssignVisible(false);
      assignForm.resetFields();
      fetchTask();
    } catch (error) {
      if (error.errorFields) {
        return;
      }
      message.error(error.response?.data?.detail || '分配失败');
    }
  };

  const handleResend = useCallback(async (assignmentId) => {
    try {
      await axios.post(`/api/v1/tasks/${taskId}/invites/${assignmentId}/resend`);
      message.success('已重发邀请');
      fetchTask();
    } catch (error) {
      message.error(error.response?.data?.detail || '重发失败');
    }
  }, [taskId, fetchTask]);

  const handleRevoke = useCallback(async (assignmentId) => {
    try {
      await axios.post(`/api/v1/tasks/${taskId}/invites/${assignmentId}/revoke`);
      message.success('已撤销邀请');
      fetchTask();
    } catch (error) {
      message.error(error.response?.data?.detail || '撤销失败');
    }
  }, [taskId, fetchTask]);

  const renderStatus = (status) => {
    const { color, text } = reportStatusMap[status] || { color: 'default', text: status || '-' };
    return <Tag color={color}>{text}</Tag>;
  };

  const deviationSummary = useMemo(() => {
    const deviations = task?.deviations || {};
    const rounds = Object.keys(deviations)
      .map((key) => Number(key))
      .filter((val) => !Number.isNaN(val))
      .sort((a, b) => a - b);
    if (!rounds.length) {
      return { available: false };
    }
    const latestRound = rounds[rounds.length - 1];
    const roundKey = String(latestRound);
    const values = Object.values(deviations[roundKey] || {}).map((item) => Number(item) || 0);
    const total = values.length;
    const avg = total ? (values.reduce((sum, val) => sum + val, 0) / total) : 0;
    const highCount = values.filter((val) => val > 20).length;
    const hasReport = (task?.reportVersions || []).some((item) => item.round === latestRound);
    return {
      available: true,
      round: latestRound,
      total,
      avg: avg.toFixed(2),
      highCount,
      isOfficial: hasReport,
    };
  }, [task]);

  const highDeviationColumns = [
    { title: '系统', dataIndex: 'system', key: 'system', width: 120, render: (value) => value || '-' },
    { title: '功能模块', dataIndex: 'module', key: 'module', width: 140, render: (value) => value || '-' },
    { title: '功能点', dataIndex: 'name', key: 'name', width: 200, render: (value) => value || '-' },
    { title: 'AI预估', dataIndex: 'aiEstimatedDays', key: 'aiEstimatedDays', width: 100, render: (value) => value ?? '-' },
    { title: '专家均值', dataIndex: 'meanDays', key: 'meanDays', width: 100, render: (value) => value ?? '-' },
    { title: '偏离度%', dataIndex: 'deviation', key: 'deviation', width: 100, render: (value) => value ?? '-' },
  ];

  const featureColumns = [
    { title: '系统', dataIndex: 'system_name', key: 'system_name', width: 120, render: (value) => value || '-' },
    { title: '功能点', dataIndex: 'description', key: 'description', width: 260, render: (value) => value || '-' },
    {
      title: '期望人天数',
      dataIndex: 'expected',
      key: 'expected',
      width: 120,
      render: (value, record) => {
        const expected = toNumberOrNull(value);
        const fallback = toNumberOrNull(record?.estimation_days) ?? toNumberOrNull(record?.original_estimate);
        return expected ?? fallback ?? '-';
      },
    },
  ];

  const renderFeatureExpandedRow = (record) => {
    const optimistic = toNumberOrNull(record?.optimistic);
    const mostLikely = toNumberOrNull(record?.most_likely);
    const pessimistic = toNumberOrNull(record?.pessimistic);
    const degraded = Boolean(record?.estimation_degraded) || optimistic === null || mostLikely === null || pessimistic === null;
    const profileContextUsed = isProfileContextUsed(record);
    const contextEvidence = (
      <div style={{ background: '#f8fafc', border: '1px solid #d9e2ec', borderRadius: 8, padding: 10 }}>
        <Space direction="vertical" size={6}>
          <Tag color={profileContextUsed ? 'blue' : 'default'}>
            {`画像上下文：${profileContextUsed ? '已使用' : '未使用'}`}
          </Tag>
          <Text>来源：{formatProfileContextSource(record?.contextSource || record?.context_source)}</Text>
        </Space>
      </div>
    );

    if (degraded) {
      return (
        <Space direction="vertical" size={8} style={{ width: '100%' }}>
          <div style={{ background: '#fffbe6', border: '1px solid #ffe58f', borderRadius: 8, padding: 10 }}>
            <Text>LLM 估算未成功，显示为拆分阶段原始估值</Text>
          </div>
          {contextEvidence}
        </Space>
      );
    }

    return (
      <div style={{ background: '#f6fbff', border: '1px solid #d6e4ff', borderRadius: 8, padding: 10 }}>
        <Space direction="vertical" size={6}>
          <Text>乐观值：{optimistic}</Text>
          <Text>最可能值：{mostLikely}</Text>
          <Text>悲观值：{pessimistic}</Text>
          <Text>估算理由：{record?.reasoning || 'LLM 未返回理由'}</Text>
          {contextEvidence}
        </Space>
      </div>
    );
  };

  const assignmentColumns = useMemo(() => {
    const columns = [
      { title: '专家', dataIndex: 'expert_name', key: 'expert_name', width: 160 },
      { title: '账号', dataIndex: 'expert_id', key: 'expert_id', width: 160 },
      {
        title: '本轮状态',
        dataIndex: 'round_submissions',
        key: 'round_submissions',
        width: 120,
        render: (rounds, record) => {
          if (record.status === 'revoked') {
            return <Tag>已撤销</Tag>;
          }
          const roundNo = task?.currentRound || 1;
          const key = String(roundNo);
          return rounds && rounds[key] ? <Tag color="success">已提交</Tag> : <Tag color="processing">未提交</Tag>;
        },
      },
      {
        title: '提交时间',
        dataIndex: 'round_submissions',
        key: 'submitted_at',
        width: 180,
        render: (rounds) => {
          const roundNo = task?.currentRound || 1;
          const key = String(roundNo);
          return rounds && rounds[key] ? rounds[key] : '-';
        },
      },
    ];

    if (isAdmin) {
      columns.push({
        title: '邀请链接',
        dataIndex: 'invite_link',
        key: 'invite_link',
        width: 360,
        render: (link) => {
          if (!link) {
            return '-';
          }
          const fullLink = `${window.location.origin}${link}`;
          return (
            <Space>
              <span style={{ maxWidth: 260, display: 'inline-block', overflow: 'hidden', textOverflow: 'ellipsis' }}>{fullLink}</span>
              <Button size="small" onClick={() => handleCopy(fullLink)}>复制</Button>
            </Space>
          );
        },
      });
      columns.push({
        title: '操作',
        key: 'action',
        width: 180,
        render: (_, record) => (
          <Space>
            <Button size="small" onClick={() => handleResend(record.assignment_id)} disabled={record.status === 'revoked'}>
              重发
            </Button>
            <Button size="small" danger onClick={() => handleRevoke(record.assignment_id)} disabled={record.status === 'revoked'}>
              撤销
            </Button>
          </Space>
        ),
      });
    }

    return columns;
  }, [isAdmin, task, handleResend, handleRevoke]);

  const expertProgress = useMemo(() => {
    const submitted = Number(task?.evaluationProgress?.submitted || 0);
    const total = Number(task?.evaluationProgress?.total || 0);
    const pending = Math.max(total - submitted, 0);
    return `${submitted}/${pending}/${total}`;
  }, [task?.evaluationProgress?.submitted, task?.evaluationProgress?.total]);

  if (loading) {
    return <Loading fullScreen tip="加载中..." />;
  }

  if (loadError) {
    return (
      <Result
        status="error"
        title="获取任务信息失败"
        subTitle={loadError}
        extra={[
          <Button key="retry" type="primary" onClick={fetchTask}>重试</Button>,
          <Button key="back" onClick={() => navigate('/tasks/ongoing')}>返回任务列表</Button>,
        ]}
      />
    );
  }

  if (!task) {
    return (
      <Card>
        <Empty description="未找到该任务的评估报告" />
      </Card>
    );
  }

  return (
    <div className="report-page" style={{ padding: '24px' }}>
      <Space style={{ marginBottom: 16 }} wrap>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/tasks/ongoing')}>
          返回任务列表
        </Button>
        <Button icon={<ReloadOutlined />} onClick={fetchTask}>
          刷新
        </Button>
        <Dropdown
          menu={{
            items: downloadMenuItems,
            onClick: handleDownloadReportMenu,
          }}
          disabled={!latestReport}
        >
          <Button type="primary" icon={<DownloadOutlined />} disabled={!latestReport}>
            下载报告
            <DownOutlined style={{ marginLeft: 8 }} />
          </Button>
        </Dropdown>
        {!latestReport && <Text type="secondary">暂无可下载报告</Text>}
        <Button onClick={handleDownloadDocument} disabled={!task.documentName}>
          下载需求文档
        </Button>
        <Button onClick={() => setAssignmentDetailVisible(true)} disabled={!assignments.length}>
          专家评估明细
        </Button>
        {isAdmin && task.status === 'awaiting_assignment' && (
          <Button type="primary" onClick={() => setAssignVisible(true)}>
            分配专家
          </Button>
        )}
      </Space>

      <Card title="摘要" style={{ marginBottom: 16 }}>
        <Descriptions bordered column={{ xs: 1, sm: 2, md: 3 }} size="small">
          <Descriptions.Item label="任务状态">{renderStatus(task.status)}</Descriptions.Item>
          <Descriptions.Item label="创建时间">{formatDateTime(task.createdAt)}</Descriptions.Item>
          <Descriptions.Item label="提交人">{task.creatorName || '-'}</Descriptions.Item>
          <Descriptions.Item label="待评估系统">{task.targetSystemDisplay || task.targetSystemName || '不限'}</Descriptions.Item>
          <Descriptions.Item label="系统名称">{(task.systems || []).join('、') || '-'}</Descriptions.Item>
          <Descriptions.Item label="功能点数量">{task.featureCount ?? '-'}</Descriptions.Item>
          <Descriptions.Item label="专家评估状态（已评/待评/总数）">{expertProgress}</Descriptions.Item>
          <Descriptions.Item label="当前评估轮次">第 {task.currentRound || 1} 轮</Descriptions.Item>
        </Descriptions>

        <Card type="inner" title="备注" style={{ marginTop: 16 }}>
          <Paragraph style={{ marginBottom: 0, whiteSpace: 'pre-wrap' }}>
            {task.remark || '-'}
          </Paragraph>
        </Card>
      </Card>

      <Card title="分析" style={{ marginBottom: 16 }}>
        <Space direction="vertical" size={12} style={{ width: '100%' }}>
          {deviationSummary.available && (
            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <Tag color={deviationSummary.isOfficial ? 'success' : 'warning'}>
                {deviationSummary.isOfficial ? '正式' : '预览'}
              </Tag>
            </div>
          )}

          {deviationSummary.available ? (
            <Row gutter={[8, 8]}>
              <Col xs={24} sm={12} md={8} lg={6}>
                <div style={metricCardStyle}>
                  <Text type="secondary">统计轮次</Text>
                  <Text strong>第 {deviationSummary.round} 轮</Text>
                </div>
              </Col>
              <Col xs={24} sm={12} md={8} lg={6}>
                <div style={metricCardStyle}>
                  <Text type="secondary">平均偏离度</Text>
                  <Text strong>{deviationSummary.avg}%</Text>
                </div>
              </Col>
              <Col xs={24} sm={12} md={8} lg={6}>
                <div style={metricCardStyle}>
                  <Text type="secondary">高偏离数</Text>
                  <Text strong>{deviationSummary.highCount}</Text>
                </div>
              </Col>
              <Col xs={24} sm={12} md={8} lg={6}>
                <div style={metricCardStyle}>
                  <Text type="secondary">功能点数</Text>
                  <Text strong>{deviationSummary.total}</Text>
                </div>
              </Col>
            </Row>
          ) : (
            <Text type="secondary">报告生成后展示偏离度统计</Text>
          )}

          {highDeviation.items && highDeviation.items.length ? (
            <>
              <Space size={8}>
                <Text type="secondary">高偏离功能点（第 {highDeviation.round} 轮）</Text>
                <Tag color={highDeviation.isOfficial ? 'success' : 'warning'}>
                  {highDeviation.isOfficial ? '正式' : '预览'}
                </Tag>
              </Space>
              <Table
                rowKey="id"
                columns={highDeviationColumns}
                dataSource={highDeviation.items}
                pagination={false}
                size="small"
                scroll={{ x: 800 }}
                loading={highDeviationLoading}
              />
            </>
          ) : (
            <Text type="secondary">暂无高偏离功能点</Text>
          )}
        </Space>
      </Card>

      <Card title="功能点明细" style={{ marginBottom: 16 }}>
        <Table
          rowKey={(record) => record.feature_id || `${record.system_name || 'system'}_${record.description || 'feature'}`}
          columns={featureColumns}
          dataSource={featureDetails}
          loading={featureLoading}
          pagination={false}
          size="small"
          scroll={{ x: 700 }}
          expandable={{
            expandRowByClick: true,
            expandedRowRender: renderFeatureExpandedRow,
          }}
          locale={{ emptyText: '暂无功能点明细' }}
        />
      </Card>

      <Modal
        title="专家评估明细"
        open={assignmentDetailVisible}
        onCancel={() => setAssignmentDetailVisible(false)}
        footer={<Button onClick={() => setAssignmentDetailVisible(false)}>关闭</Button>}
        width={980}
      >
        <Table
          rowKey="assignment_id"
          columns={assignmentColumns}
          dataSource={assignments}
          pagination={false}
          scroll={{ x: 920 }}
        />
      </Modal>

      <Modal
        title="分配专家"
        open={assignVisible}
        onCancel={() => setAssignVisible(false)}
        onOk={handleAssign}
        okText="分配"
        cancelText="取消"
      >
        <Form form={assignForm} layout="vertical">
          <Row gutter={16}>
            <Col xs={24} md={8}>
              <Form.Item
                label="专家1账号"
                name="expert1Id"
                rules={[{ required: true, message: '请输入专家1账号' }]}
              >
                <Select
                  placeholder="请选择专家1"
                  loading={expertLoading}
                  showSearch
                  optionFilterProp="label"
                  options={expertCandidates.map((user) => ({
                    value: user.username,
                    label: `${user.display_name || user.username}（${user.username}）`,
                  }))}
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item
                label="专家2账号"
                name="expert2Id"
                rules={[{ required: true, message: '请输入专家2账号' }]}
              >
                <Select
                  placeholder="请选择专家2"
                  loading={expertLoading}
                  showSearch
                  optionFilterProp="label"
                  options={expertCandidates.map((user) => ({
                    value: user.username,
                    label: `${user.display_name || user.username}（${user.username}）`,
                  }))}
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item
                label="专家3账号"
                name="expert3Id"
                rules={[{ required: true, message: '请输入专家3账号' }]}
              >
                <Select
                  placeholder="请选择专家3"
                  loading={expertLoading}
                  showSearch
                  optionFilterProp="label"
                  options={expertCandidates.map((user) => ({
                    value: user.username,
                    label: `${user.display_name || user.username}（${user.username}）`,
                  }))}
                />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>
    </div>
  );
};

export default ReportPage;
