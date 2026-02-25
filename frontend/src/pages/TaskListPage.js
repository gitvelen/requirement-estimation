import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  DatePicker,
  message,
  Space,
  Tooltip,
  Typography,
} from 'antd';
import {
  DownloadOutlined,
  EditOutlined,
  EyeOutlined,
  PlusOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import axios from 'axios';
import { useLocation, useNavigate } from 'react-router-dom';
import usePermission from '../hooks/usePermission';
import DataTable from '../components/DataTable';
import StatusTag from '../components/StatusTag';
import { formatDateTime, toIsoEndOfDay, toIsoStartOfDay } from '../utils/time';
import { resolveActionColumnWidth } from '../utils/taskTableLayout';

const { Text } = Typography;
const { RangePicker } = DatePicker;


const statusMap = {
  pending: { color: 'default', text: '待处理' },
  in_progress: { color: 'processing', text: '进行中' },
  completed: { color: 'success', text: '已完成' },
  closed: { color: 'default', text: '已关闭' },
  unknown: { color: 'default', text: '未知' },
};

const aiStatusMap = {
  pending: { color: 'default', text: '待处理' },
  processing: { color: 'processing', text: '处理中' },
  completed: { color: 'success', text: '已完成' },
  failed: { color: 'error', text: '失败' },
};

const parseErrorMessage = (error, fallback) => {
  const responseData = error?.response?.data;
  return responseData?.message || responseData?.detail || fallback;
};

const TaskListPage = ({ defaultTab = 'ongoing' }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const intervalRef = useRef(null);
  const resolvedTab = defaultTab === 'completed' ? 'completed' : 'ongoing';

  const { activeRole, isAdmin, isManager, isExpert, isViewer } = usePermission();

  const [loading, setLoading] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [errorMessage, setErrorMessage] = useState('');
  const [dateRange, setDateRange] = useState(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [taskGroups, setTaskGroups] = useState({
    pending: { total: 0, items: [] },
    in_progress: { total: 0, items: [] },
    completed: { total: 0, items: [] },
  });

  const scope = useMemo(() => {
    if (activeRole === 'admin' || activeRole === 'viewer') {
      return 'all';
    }
    if (activeRole === 'manager') {
      return 'created';
    }
    if (activeRole === 'expert') {
      return 'assigned';
    }
    return '';
  }, [activeRole]);

  const fetchTaskGroups = useCallback(async () => {
    try {
      setLoading(true);

      const params = {
        group_by_status: true,
        page,
        page_size: pageSize,
      };
      if (scope) {
        params.scope = scope;
      }
      if (dateRange && dateRange.length === 2) {
        params.time_range = 'custom';
        params.start_at = toIsoStartOfDay(dateRange[0]);
        params.end_at = toIsoEndOfDay(dateRange[1]);
      }

      const response = await axios.get('/api/v1/tasks', { params });
      const groups = response.data?.task_groups || {};
      setErrorMessage('');
      setTaskGroups({
        pending: groups.pending || { total: 0, items: [] },
        in_progress: groups.in_progress || { total: 0, items: [] },
        completed: groups.completed || { total: 0, items: [] },
      });
      return true;
    } catch (error) {
      setErrorMessage(parseErrorMessage(error, '获取任务列表失败'));
      return false;
    } finally {
      setLoading(false);
    }
  }, [dateRange, page, pageSize, scope]);

  useEffect(() => {
    fetchTaskGroups();
    if (autoRefresh) {
      intervalRef.current = setInterval(fetchTaskGroups, 3000);
    }
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [autoRefresh, fetchTaskGroups]);

  useEffect(() => {
    setPage(1);
  }, [resolvedTab]);

  const combinedOngoingItems = useMemo(() => {
    const merged = [
      ...(taskGroups.pending?.items || []),
      ...(taskGroups.in_progress?.items || []),
    ];
    merged.sort((a, b) => String(b.createdAt || '').localeCompare(String(a.createdAt || '')));
    return merged;
  }, [taskGroups.in_progress?.items, taskGroups.pending?.items]);

  useEffect(() => {
    const candidates = resolvedTab === 'completed'
      ? (taskGroups.completed?.items || [])
      : combinedOngoingItems;
    const hasProcessingTasks = candidates.some((task) => task.aiStatus === 'processing' || task.aiStatus === 'pending');
    if (hasProcessingTasks && !autoRefresh) {
      setAutoRefresh(true);
    } else if (!hasProcessingTasks && autoRefresh) {
      setAutoRefresh(false);
    }
  }, [resolvedTab, autoRefresh, combinedOngoingItems, taskGroups.completed?.items]);

  const handleRefresh = async () => {
    const ok = await fetchTaskGroups();
    if (ok) {
      message.success('已刷新');
    }
  };

  const handleView = useCallback((taskId) => {
    navigate(`/report/${taskId}`);
  }, [navigate]);

  const handleEdit = useCallback((taskId) => {
    navigate(`/edit/${taskId}`);
  }, [navigate]);

  const handleEvaluate = useCallback((task) => {
    if (task.myInviteToken) {
      navigate(`/evaluate/${task.id}?token=${encodeURIComponent(task.myInviteToken)}`);
      return;
    }
    const token = window.prompt('请输入邀请Token');
    if (token) {
      navigate(`/evaluate/${task.id}?token=${encodeURIComponent(token)}`);
    }
  }, [navigate]);

  const handleDownload = useCallback(async (taskId) => {
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
      message.error(parseErrorMessage(error, '下载失败'));
    }
  }, []);

  const renderAiStatus = useCallback((status, progress, messageText) => (
    <Space direction="vertical" size={0}>
      <StatusTag status={status} map={aiStatusMap} />
      <Text type="secondary" style={{ fontSize: 12 }}>{progress ? `${progress}%` : '-'} {messageText || ''}</Text>
    </Space>
  ), []);

  const columns = useMemo(() => ([
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
      title: '创建时间',
      dataIndex: 'createdAt',
      key: 'createdAt',
      width: 180,
      render: (value) => formatDateTime(value),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (value) => <StatusTag status={value || 'unknown'} map={statusMap} />,
    },
    {
      title: 'AI状态',
      key: 'aiStatus',
      width: 200,
      render: (_, record) => renderAiStatus(record.aiStatus, record.progress, record.message),
    },
    {
      title: '评估进度',
      key: 'evaluationProgress',
      width: 120,
      render: (_, record) => {
        const progress = record.evaluationProgress || {};
        const submitted = progress.submitted || 0;
        const total = progress.total || 0;
        return (
          <Space direction="vertical" size={0}>
            <Text>{submitted}/{total}</Text>
            <Text type="secondary" style={{ fontSize: 12 }}>已提交/总数</Text>
          </Space>
        );
      },
    },
    {
      title: '操作',
      key: 'actions',
      width: resolveActionColumnWidth({ isExpert, resolvedTab }),
      fixed: 'right',
      render: (_, record) => (
        <Space size={4}>
          <Tooltip title="查看详情">
            <Button size="small" icon={<EyeOutlined />} onClick={() => handleView(record.id)} />
          </Tooltip>
          {isManager && record.aiStatus === 'completed' && (
            <Tooltip title="编辑功能点">
              <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(record.id)} />
            </Tooltip>
          )}
          {isExpert && resolvedTab === 'ongoing' && (
            <Tooltip title="进入评估">
              <Button size="small" type="primary" onClick={() => handleEvaluate(record)}>
                评估
              </Button>
            </Tooltip>
          )}
          {(record.status === 'completed' || record.status === 'closed') && (
            <Tooltip title="下载报告">
              <Button size="small" icon={<DownloadOutlined />} onClick={() => handleDownload(record.id)} />
            </Tooltip>
          )}
        </Space>
      ),
    },
  ]), [resolvedTab, isExpert, isManager, handleDownload, handleEdit, handleEvaluate, handleView, renderAiStatus]);

  const ongoingTotal = (taskGroups.pending?.total || 0) + (taskGroups.in_progress?.total || 0);
  const completedTotal = taskGroups.completed?.total || 0;

  const canCreateTask = isManager;
  const canSeeTasks = isAdmin || isManager || isExpert || isViewer;

  if (!canSeeTasks) {
    return (
      <Card>
        <Text type="secondary">当前角色无任务管理权限。</Text>
      </Card>
    );
  }

  const dataSource = resolvedTab === 'completed' ? (taskGroups.completed?.items || []) : combinedOngoingItems;
  const total = resolvedTab === 'completed' ? completedTotal : ongoingTotal;
  const listSummary = `共 ${total} 条`;

  return (
    <Card>
      <Space direction="vertical" size={12} style={{ width: '100%' }}>
        <Space wrap align="center" style={{ justifyContent: 'space-between', width: '100%' }}>
          <Text strong>{listSummary}</Text>
          <Space wrap>
            <RangePicker
              value={dateRange}
              onChange={(value) => {
                setDateRange(value);
                setPage(1);
              }}
            />
            {canCreateTask && (
              <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate(`/upload${location.search || ''}`)}>
                发起评估
              </Button>
            )}
            <Button icon={<ReloadOutlined />} onClick={handleRefresh} loading={loading}>
              刷新
            </Button>
          </Space>
        </Space>

        {errorMessage && (
          <Alert
            type="error"
            showIcon
            message={errorMessage}
            action={(
              <Button size="small" type="link" onClick={handleRefresh}>
                重试
              </Button>
            )}
          />
        )}

        <DataTable
          rowKey="id"
          columns={columns}
          dataSource={dataSource}
          loading={loading}
          scroll={{ x: 1200 }}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            onChange: (nextPage, nextSize) => {
              setPage(nextPage);
              if (nextSize !== pageSize) {
                setPageSize(nextSize);
              }
            },
          }}
        />
      </Space>
    </Card>
  );
};

export default TaskListPage;
