import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { Button, message, Card, Space, Typography, Tooltip, DatePicker, Select, Popconfirm, Tabs } from 'antd';
import { EyeOutlined, DownloadOutlined, ReloadOutlined, EditOutlined, PlusOutlined } from '@ant-design/icons';
import axios from 'axios';
import { useNavigate, useLocation } from 'react-router-dom';
import usePermission from '../hooks/usePermission';
import PageHeader from '../components/PageHeader';
import DataTable from '../components/DataTable';
import StatusTag from '../components/StatusTag';

const { Text } = Typography;
const { RangePicker } = DatePicker;

const TaskListPage = () => {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const intervalRef = useRef(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const { isAdmin, isManager, isExpert } = usePermission();
  const [statusFilter, setStatusFilter] = useState('all');
  const [dateRange, setDateRange] = useState(null);
  const [adminGroup, setAdminGroup] = useState('in_progress');

  const viewConfig = useMemo(() => {
    if (location.pathname === '/tasks/my-evaluations') {
      return {
        endpoint: '/api/v1/profile/my-evaluations',
        scope: 'assigned',
        title: '我参与的评估',
      };
    }
    if (location.pathname === '/tasks/my-tasks') {
      return {
        endpoint: '/api/v1/profile/my-tasks',
        scope: 'created',
        title: '我发起的任务',
      };
    }
    const params = new URLSearchParams(location.search);
    const scopeParam = params.get('scope');
    const defaultScope = isAdmin ? 'all' : isManager ? 'created' : 'assigned';
    const finalScope = scopeParam || defaultScope;
    const titleMap = {
      all: '任务管理',
      created: '我发起的任务',
      assigned: '我参与的评估',
    };
    return {
      endpoint: '/api/v1/tasks',
      scope: finalScope,
      title: location.pathname === '/tasks' ? '任务管理' : (titleMap[finalScope] || '评估任务列表'),
    };
  }, [location.pathname, location.search, isAdmin, isManager]);

  const { endpoint, scope, title } = viewConfig;
  const isEvaluationView = scope === 'assigned';

  const fetchTasks = useCallback(async () => {
    try {
      setLoading(true);
      const response = await axios.get(endpoint, {
        params: endpoint === '/api/v1/tasks' && scope ? { scope } : undefined,
      });
      setTasks(response.data.data || []);
    } catch (error) {
      console.error('获取任务列表失败:', error);
      message.error(error.response?.data?.detail || '获取任务列表失败');
    } finally {
      setLoading(false);
    }
  }, [endpoint, scope]);

  useEffect(() => {
    fetchTasks();
    if (autoRefresh) {
      intervalRef.current = setInterval(fetchTasks, 3000);
    }
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [autoRefresh, fetchTasks]);

  useEffect(() => {
    const hasProcessingTasks = tasks.some(t => t.aiStatus === 'processing' || t.aiStatus === 'pending');
    if (hasProcessingTasks && !autoRefresh) {
      setAutoRefresh(true);
    } else if (!hasProcessingTasks && autoRefresh) {
      setAutoRefresh(false);
    }
  }, [tasks, autoRefresh]);

  const handleRefresh = async () => {
    await fetchTasks();
    message.success('已刷新');
  };

  const handleView = (taskId) => {
    navigate(`/report/${taskId}`);
  };

  const handleEdit = (taskId) => {
    navigate(`/edit/${taskId}`);
  };

  const handleEvaluate = (task) => {
    if (task.myInviteToken) {
      navigate(`/evaluate/${task.id}?token=${encodeURIComponent(task.myInviteToken)}`);
      return;
    }
    const token = window.prompt('请输入邀请Token');
    if (token) {
      navigate(`/evaluate/${task.id}?token=${encodeURIComponent(token)}`);
    }
  };

  const handleDownload = async (taskId) => {
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

  const handleDelete = async (taskId) => {
    try {
      await axios.delete(`/api/v1/tasks/${taskId}`);
      message.success('任务已删除');
      fetchTasks();
    } catch (error) {
      message.error(error.response?.data?.detail || '删除失败');
    }
  };

  const handleArchive = async (taskId) => {
    try {
      await axios.put(`/api/v1/tasks/${taskId}/archive`);
      message.success('任务已归档');
      fetchTasks();
    } catch (error) {
      message.error(error.response?.data?.detail || '归档失败');
    }
  };

  const filteredTasks = useMemo(() => {
    const toDate = (value) => {
      if (!value) return null;
      if (typeof value.toDate === 'function') return value.toDate();
      return value instanceof Date ? value : new Date(value);
    };
    let result = [...tasks];
    if (isAdmin && scope === 'all') {
      const groupMap = {
        in_progress: ['draft', 'awaiting_assignment', 'evaluating'],
        completed: ['completed', 'archived'],
      };
      const allow = groupMap[adminGroup] || [];
      result = result.filter((item) => allow.includes(item.status));
    }
    if (statusFilter && statusFilter !== 'all') {
      result = result.filter((item) => item.status === statusFilter);
    }
    if (dateRange && dateRange.length === 2) {
      const start = toDate(dateRange[0]);
      const end = toDate(dateRange[1]);
      if (start && end) {
        const startTime = new Date(start.setHours(0, 0, 0, 0)).getTime();
        const endTime = new Date(end.setHours(23, 59, 59, 999)).getTime();
        result = result.filter((item) => {
          const createdAt = toDate(item.createdAt);
          if (!createdAt) return false;
          const time = createdAt.getTime();
          return time >= startTime && time <= endTime;
        });
      }
    }
    result.sort((a, b) => {
      const aTime = toDate(a.createdAt)?.getTime() || 0;
      const bTime = toDate(b.createdAt)?.getTime() || 0;
      return bTime - aTime;
    });
    return result;
  }, [tasks, statusFilter, dateRange, adminGroup, isAdmin, scope]);

  const workflowStatusMap = {
    draft: { color: 'default', text: '草稿' },
    awaiting_assignment: { color: 'warning', text: '待分配' },
    evaluating: { color: 'processing', text: '评估中' },
    completed: { color: 'success', text: '已完成' },
    archived: { color: 'default', text: '已归档' },
  };

  const aiStatusMap = {
    pending: { color: 'default', text: '待处理' },
    processing: { color: 'processing', text: '处理中' },
    completed: { color: 'success', text: '已完成' },
    failed: { color: 'error', text: '失败' },
  };

  const renderAiStatus = (status, progress, messageText) => (
    <Space direction="vertical" size={0}>
      <StatusTag status={status} map={aiStatusMap} />
      <Text type="secondary" style={{ fontSize: 12 }}>{progress ? `${progress}%` : '-'} {messageText || ''}</Text>
    </Space>
  );

  const columns = [
    {
      title: '任务名称',
      dataIndex: 'name',
      key: 'name',
      width: 220,
      ellipsis: true,
      render: (text) => (
        <Tooltip title={text}>
          <Text>{text || '-'}</Text>
        </Tooltip>
      ),
    },
    {
      title: '发起人',
      dataIndex: 'creatorName',
      key: 'creatorName',
      width: 120,
      render: (value) => value || '-',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (value) => <StatusTag status={value} map={workflowStatusMap} />,
    },
    {
      title: 'AI状态',
      key: 'aiStatus',
      width: 180,
      render: (_, record) => renderAiStatus(record.aiStatus, record.progress, record.message),
    },
    {
      title: '评估进度',
      key: 'progress',
      width: 120,
      render: (_, record) => {
        const progress = record.evaluationProgress || {};
        if (record.status !== 'evaluating') {
          return <Text type="secondary">-</Text>;
        }
        return <Text>{progress.submitted || 0}/{progress.total || 0}</Text>;
      },
    },
    {
      title: '当前轮次',
      dataIndex: 'currentRound',
      key: 'currentRound',
      width: 100,
      render: (round) => round || 1,
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      key: 'createdAt',
      width: 180,
    },
    {
      title: '操作',
      key: 'action',
      width: 420,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          {record.status === 'draft' && isManager ? (
            <Button
              type="primary"
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record.id)}
            >
              编辑功能点
            </Button>
          ) : (
            <Button
              type="primary"
              size="small"
              icon={<EyeOutlined />}
              onClick={() => handleView(record.id)}
            >
              查看
            </Button>
          )}
          {record.status === 'evaluating' && isExpert && (
            <Button size="small" onClick={() => handleEvaluate(record)}>
              进入评估
            </Button>
          )}
          {(isAdmin || isManager) && (
            <Button
              size="small"
              icon={<DownloadOutlined />}
              onClick={() => handleDownload(record.id)}
              disabled={record.status !== 'completed'}
            >
              下载报告
            </Button>
          )}
          {(isAdmin || isManager) && ['draft', 'awaiting_assignment'].includes(record.status) && (
            <Popconfirm
              title="确定删除该任务吗？"
              onConfirm={() => handleDelete(record.id)}
              okText="删除"
              cancelText="取消"
            >
              <Button size="small" danger>
                删除
              </Button>
            </Popconfirm>
          )}
          {(isAdmin || isManager) && record.status === 'completed' && (
            <Popconfirm
              title="确定归档该任务吗？"
              onConfirm={() => handleArchive(record.id)}
              okText="归档"
              cancelText="取消"
            >
              <Button size="small">
                归档
              </Button>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title={title}
        extra={isManager && !isEvaluationView ? (
          <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/upload')}>
            发起评估
          </Button>
        ) : null}
      />
      <Card className="task-list-card">
        {isAdmin && scope === 'all' && (
          <Tabs
            activeKey={adminGroup}
            onChange={(key) => {
              setAdminGroup(key);
              setStatusFilter('all');
            }}
            items={[
              { key: 'in_progress', label: '在途中' },
              { key: 'completed', label: '已完成' },
            ]}
            style={{ marginBottom: 12 }}
          />
        )}
        {isManager && isExpert && !isAdmin && location.pathname === '/tasks' && (
          <Tabs
            activeKey={scope === 'assigned' ? 'assigned' : 'created'}
            onChange={(key) => {
              const params = new URLSearchParams(location.search);
              params.set('scope', key);
              navigate(`/tasks?${params.toString()}`);
              setStatusFilter('all');
            }}
            items={[
              { key: 'created', label: '我发起的' },
              { key: 'assigned', label: '我参与的' },
            ]}
            style={{ marginBottom: 12 }}
          />
        )}
        <div style={{ marginBottom: 16 }}>
          <Space wrap>
            <Button icon={<ReloadOutlined />} onClick={handleRefresh}>
              刷新
            </Button>
            <Select
              value={statusFilter}
              onChange={setStatusFilter}
              style={{ width: 140 }}
              options={[
                { label: '全部状态', value: 'all' },
                { label: '草稿', value: 'draft' },
                { label: '待分配', value: 'awaiting_assignment' },
                { label: '评估中', value: 'evaluating' },
                { label: '已完成', value: 'completed' },
                { label: '已归档', value: 'archived' },
              ]}
            />
            <RangePicker value={dateRange} onChange={setDateRange} />
            <Button onClick={() => { setStatusFilter('all'); setDateRange(null); }}>
              清空筛选
            </Button>
          </Space>
        </div>
        <DataTable
          rowKey="id"
          columns={columns}
          dataSource={filteredTasks}
          loading={loading}
          scroll={{ x: 1400 }}
          pagination={{ pageSize: 10 }}
        />
      </Card>
    </div>
  );
};

export default TaskListPage;
