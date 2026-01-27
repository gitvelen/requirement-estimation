import React, { useState, useEffect, useRef } from 'react';
import { Table, Button, Tag, message, Card, Space, Progress, Typography, Tooltip } from 'antd';
import { EyeOutlined, DownloadOutlined, ReloadOutlined, EditOutlined } from '@ant-design/icons';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

const { Text } = Typography;

const TaskListPage = () => {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const intervalRef = useRef(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  // 获取任务列表
  const fetchTasks = async () => {
    try {
      setLoading(true);
      const response = await axios.get('/api/v1/requirement/tasks');
      setTasks(response.data.data || []);
    } catch (error) {
      console.error('获取任务列表失败:', error);
      message.error('获取任务列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // 初始加载
    fetchTasks();

    // 设置自动刷新（每3秒）
    if (autoRefresh) {
      intervalRef.current = setInterval(fetchTasks, 3000);
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [autoRefresh]);

  // 检查是否有处理中的任务，如果没有则停止自动刷新
  useEffect(() => {
    const hasProcessingTasks = tasks.some(t => t.status === 'processing');
    if (hasProcessingTasks && !autoRefresh) {
      setAutoRefresh(true);
    } else if (!hasProcessingTasks && autoRefresh) {
      // 所有任务都完成了，停止自动刷新
      setAutoRefresh(false);
    }
  }, [tasks]);

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

  const handleDownload = async (taskId) => {
    try {
      const response = await axios.get(`/api/v1/requirement/report/${taskId}`, {
        responseType: 'blob',
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `评估报告_${taskId}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();

      message.success('下载成功');
    } catch (error) {
      message.error('下载失败');
    }
  };

  // 渲染状态标签
  const renderStatus = (status) => {
    const statusMap = {
      pending: { color: 'default', text: '待处理' },
      processing: { color: 'processing', text: '处理中' },
      completed: { color: 'success', text: '已完成' },
      failed: { color: 'error', text: '失败' },
    };
    const { color, text } = statusMap[status] || { color: 'default', text: status };
    return <Tag color={color}>{text}</Tag>;
  };

  // 渲染进度条
  const renderProgress = (progress, status) => {
    if (status === 'completed') {
      return <Text type="success">✓ 已完成</Text>;
    }
    if (status === 'failed') {
      return <Text type="danger">✗ 失败</Text>;
    }
    if (status === 'pending') {
      return <Text type="secondary">等待中...</Text>;
    }
    return <Progress percent={progress} size="small" status="active" />;
  };

  const columns = [
    {
      title: '任务ID',
      dataIndex: 'task_id',
      key: 'task_id',
      width: 250,
      ellipsis: true,
      render: (text) => (
        <Tooltip title={text}>
          <Text code style={{ fontSize: 12 }}>{text.substring(0, 8)}...</Text>
        </Tooltip>
      ),
    },
    {
      title: '文件名',
      dataIndex: 'filename',
      key: 'filename',
      width: 250,
      ellipsis: true,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: renderStatus,
    },
    {
      title: '进度',
      dataIndex: 'progress',
      key: 'progress',
      width: 150,
      render: (progress, record) => renderProgress(progress, record.status),
    },
    {
      title: '当前阶段',
      dataIndex: 'message',
      key: 'message',
      width: 250,
      ellipsis: true,
      render: (text) => (
        <Tooltip title={text}>
          <Text>{text || '-'}</Text>
        </Tooltip>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
    },
    {
      title: '操作',
      key: 'action',
      width: 280,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          {record.status === 'completed' && !record.confirmed ? (
            <Button
              type="primary"
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record.task_id)}
            >
              编辑评估
            </Button>
          ) : (
            <Button
              type="primary"
              size="small"
              icon={<EyeOutlined />}
              onClick={() => handleView(record.task_id)}
              disabled={record.status !== 'completed'}
            >
              查看
            </Button>
          )}
          <Button
            size="small"
            icon={<DownloadOutlined />}
            onClick={() => handleDownload(record.task_id)}
            disabled={record.status !== 'completed'}
          >
            下载
          </Button>
          {record.status === 'processing' && (
            <Tooltip title="正在自动刷新中...">
              <Button size="small" icon={<ReloadOutlined spin />} disabled>
                刷新
              </Button>
            </Tooltip>
          )}
        </Space>
      ),
    },
  ];

  // 统计信息
  const stats = {
    total: tasks.length,
    processing: tasks.filter(t => t.status === 'processing').length,
    completed: tasks.filter(t => t.status === 'completed').length,
    failed: tasks.filter(t => t.status === 'failed').length,
  };

  return (
    <Card title="评估任务列表" className="task-list-card">
      <div style={{ marginBottom: 16 }}>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={handleRefresh} loading={loading}>
            刷新列表
          </Button>
          {autoRefresh && (
            <Tag color="processing">自动刷新中 (3秒)</Tag>
          )}
          <Tag>总计: {stats.total}</Tag>
          <Tag color="processing">处理中: {stats.processing}</Tag>
          <Tag color="success">已完成: {stats.completed}</Tag>
          <Tag color="error">失败: {stats.failed}</Tag>
        </Space>
      </div>

      <Table
        columns={columns}
        dataSource={tasks}
        rowKey="task_id"
        loading={loading}
        pagination={{
          pageSize: 10,
          showSizeChanger: true,
          showTotal: (total) => `共 ${total} 条记录`
        }}
        scroll={{ x: 1400 }}
        rowClassName={(record) => {
          if (record.status === 'processing') return 'row-processing';
          if (record.status === 'failed') return 'row-failed';
          return '';
        }}
      />

      <style>{`
        .row-processing {
          background-color: #e6f7ff;
        }
        .row-failed {
          background-color: #fff2f0;
        }
        .task-list-card .ant-table-tbody > tr:hover > td {
          background-color: #f5f5f5 !important;
        }
      `}</style>
    </Card>
  );
};

export default TaskListPage;
