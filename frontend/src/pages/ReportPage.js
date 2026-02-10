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
  Collapse,
  Statistic,
  Typography,
} from 'antd';
import { ArrowLeftOutlined, DownloadOutlined, ReloadOutlined } from '@ant-design/icons';
import axios from 'axios';
import usePermission from '../hooks/usePermission';
import Loading from '../components/Loading';

const { Text } = Typography;

const ReportPage = () => {
  const { taskId } = useParams();
  const navigate = useNavigate();
  const { isAdmin } = usePermission();
  const [loading, setLoading] = useState(true);
  const [task, setTask] = useState(null);
  const [assignVisible, setAssignVisible] = useState(false);
  const [assignments, setAssignments] = useState([]);
  const [assignForm] = Form.useForm();
  const [expertCandidates, setExpertCandidates] = useState([]);
  const [expertLoading, setExpertLoading] = useState(false);
  const [highDeviation, setHighDeviation] = useState({ round: null, isOfficial: false, items: [] });
  const [highDeviationLoading, setHighDeviationLoading] = useState(false);

  const fetchTask = useCallback(async () => {
    try {
      setLoading(true);
      setHighDeviationLoading(true);
      const [taskRes, highRes] = await Promise.all([
        axios.get(`/api/v1/tasks/${taskId}`),
        axios.get(`/api/v1/tasks/${taskId}/high-deviation`).catch(() => ({ data: { data: { round: null, isOfficial: false, items: [] } } })),
      ]);
      const payload = taskRes.data.data;
      setTask(payload);
      setAssignments(payload.expertAssignments || []);
      const highPayload = highRes.data.data || { round: null, isOfficial: false, items: [] };
      setHighDeviation(highPayload);
    } catch (error) {
      if (error.response?.status === 404) {
        message.error('任务不存在');
      } else {
        message.error(error.response?.data?.detail || '获取任务信息失败');
      }
    } finally {
      setHighDeviationLoading(false);
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

  const handleDownloadLatest = async () => {
    try {
      const response = await axios.get(`/api/v1/tasks/${taskId}/report`, {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `评估报告_${taskId}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      message.success('下载成功');
    } catch (error) {
      message.error(error.response?.data?.detail || '下载失败');
    }
  };

  const handleDownloadVersion = async (record) => {
    try {
      const response = await axios.get(`/api/v1/tasks/${taskId}/reports/${record.id}`, {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', record.file_name || `评估报告_${taskId}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      message.success('下载成功');
    } catch (error) {
      message.error(error.response?.data?.detail || '下载失败');
    }
  };

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
    const statusMap = {
      draft: { color: 'default', text: '草稿' },
      awaiting_assignment: { color: 'warning', text: '待分配' },
      evaluating: { color: 'processing', text: '评估中' },
      completed: { color: 'success', text: '已完成' },
      archived: { color: 'default', text: '已归档' },
    };
    const { color, text } = statusMap[status] || { color: 'default', text: status || '-' };
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

  const reportColumns = [
    { title: '轮次', dataIndex: 'round', key: 'round', width: 80 },
    { title: '版本', dataIndex: 'version', key: 'version', width: 80 },
    { title: '文件名', dataIndex: 'file_name', key: 'file_name', width: 280 },
    { title: '生成时间', dataIndex: 'generated_at', key: 'generated_at', width: 200 },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_, record) => (
        <Button size="small" icon={<DownloadOutlined />} onClick={() => handleDownloadVersion(record)}>
          下载
        </Button>
      ),
    },
  ];

  if (loading) {
    return <Loading fullScreen tip="加载中..." />;
  }

  if (!task) {
    return <Text>未找到该任务的评估报告。</Text>;
  }

  return (
    <div className="report-page" style={{ padding: '24px' }}>
      <Space style={{ marginBottom: 16 }} wrap>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/tasks')}>
          返回任务列表
        </Button>
        <Button icon={<ReloadOutlined />} onClick={fetchTask}>
          刷新
        </Button>
        <Button
          type="primary"
          icon={<DownloadOutlined />}
          onClick={handleDownloadLatest}
          disabled={!task.reportVersions || task.reportVersions.length === 0}
        >
          下载最新报告
        </Button>
      </Space>

      <Card title="摘要" style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]} align="middle">
          <Col xs={24} md={8}>
            <Space direction="vertical" size={4}>
              <Text type="secondary">任务名称</Text>
              <Text strong>{task.name || '-'}</Text>
              <Space>
                {renderStatus(task.status)}
                <Tag color="processing">第 {task.currentRound || 1} 轮</Tag>
              </Space>
            </Space>
          </Col>
          <Col xs={12} md={4}>
            <Statistic title="已提交" value={task.evaluationProgress?.submitted || 0} />
          </Col>
          <Col xs={12} md={4}>
            <Statistic title="总专家数" value={task.evaluationProgress?.total || 0} />
          </Col>
          <Col xs={12} md={4}>
            <Statistic title="涉及系统" value={(task.systems || []).length} />
          </Col>
          <Col xs={12} md={4}>
            <Statistic title="报告版本" value={(task.reportVersions || []).length} />
          </Col>
        </Row>
      </Card>

      <Card title="主体" style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]}>
          <Col xs={24} lg={8}>
            <Card type="inner" title="任务详情">
              <Space direction="vertical" size={12} style={{ width: '100%' }}>
                <div>
                  <Text type="secondary">发起人</Text>
                  <div>{task.creatorName || '-'}</div>
                </div>
                <div>
                  <Text type="secondary">创建时间</Text>
                  <div>{task.createdAt || '-'}</div>
                </div>
                <div>
                  <Text type="secondary">涉及系统</Text>
                  <div>{(task.systems || []).join('、') || '-'}</div>
                </div>
                <div>
                  <Text type="secondary">需求文档</Text>
                  <Space wrap>
                    <Text>{task.documentName || '未上传'}</Text>
                    <Button size="small" onClick={handleDownloadDocument} disabled={!task.documentName}>
                      下载
                    </Button>
                  </Space>
                </div>
                <div>
                  <Text type="secondary">任务说明</Text>
                  <div>{task.description || '-'}</div>
                </div>
              </Space>
            </Card>
          </Col>

          <Col xs={24} lg={16}>
            <Card
              type="inner"
              title="专家评估进度"
              extra={task.status === 'awaiting_assignment' && isAdmin ? (
                <Button type="primary" onClick={() => setAssignVisible(true)}>
                  分配专家
                </Button>
              ) : null}
            >
              <Table
                rowKey="assignment_id"
                columns={assignmentColumns}
                dataSource={assignments}
                pagination={false}
                scroll={{ x: 900 }}
              />
            </Card>
          </Col>
        </Row>
      </Card>

      <Card title="分析" style={{ marginBottom: 16 }}>
        <Collapse
          defaultActiveKey={[]}
          items={[
            {
              key: 'deviation-panel',
              label: '偏离度统计与高偏离功能点',
              children: (
                <Space direction="vertical" size={16} style={{ width: '100%' }}>
                  {deviationSummary.available ? (
                    <Row gutter={16}>
                      <Col xs={12} md={6}>
                        <Statistic title="统计轮次" value={`第${deviationSummary.round}轮`} />
                      </Col>
                      <Col xs={12} md={6}>
                        <Statistic title="平均偏离度" value={`${deviationSummary.avg}%`} />
                      </Col>
                      <Col xs={12} md={6}>
                        <Statistic title="高偏离数" value={deviationSummary.highCount} />
                      </Col>
                      <Col xs={12} md={6}>
                        <Statistic title="功能点数" value={deviationSummary.total} />
                      </Col>
                      <Col xs={24} style={{ marginTop: 12 }}>
                        <Tag color={deviationSummary.isOfficial ? 'success' : 'warning'}>
                          {deviationSummary.isOfficial ? '正式' : '预览'}
                        </Tag>
                      </Col>
                    </Row>
                  ) : (
                    <Text type="secondary">报告生成后展示偏离度统计</Text>
                  )}

                  {highDeviation.items && highDeviation.items.length ? (
                    <>
                      <Space>
                        <Text type="secondary">统计轮次：</Text>
                        <Text>第 {highDeviation.round} 轮</Text>
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
              ),
            },
          ]}
        />
      </Card>

      <Card title="报告版本列表" style={{ marginTop: 16 }}>
        <Table
          rowKey="id"
          columns={reportColumns}
          dataSource={task.reportVersions || []}
          pagination={false}
          scroll={{ x: 800 }}
        />
      </Card>

      <Modal
        title="分配专家"
        open={assignVisible}
        onCancel={() => setAssignVisible(false)}
        onOk={handleAssign}
        okText="分配"
        cancelText="取消"
      >
        <Form form={assignForm} layout="vertical">
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
        </Form>
      </Modal>
    </div>
  );
};

export default ReportPage;
