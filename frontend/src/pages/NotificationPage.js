import React, { useEffect, useState, useCallback } from 'react';
import { Button, Card, Tag, Space, message, Popconfirm, Badge, Tooltip } from 'antd';
import { ReloadOutlined, BellOutlined, TeamOutlined, FileTextOutlined } from '@ant-design/icons';
import axios from 'axios';
import useNotification from '../hooks/useNotification';
import PageHeader from '../components/PageHeader';
import DataTable from '../components/DataTable';
import StatusTag from '../components/StatusTag';

const NotificationPage = () => {
  const [loading, setLoading] = useState(false);
  const [items, setItems] = useState([]);
  const { refreshUnread } = useNotification() || {};

  const fetchNotifications = useCallback(async () => {
    try {
      setLoading(true);
      const response = await axios.get('/api/v1/notifications');
      setItems(response.data.data || []);
      if (refreshUnread) {
        refreshUnread();
      }
    } catch (error) {
      message.error(error.response?.data?.detail || '获取通知失败');
    } finally {
      setLoading(false);
    }
  }, [refreshUnread]);

  useEffect(() => {
    fetchNotifications();
  }, [fetchNotifications]);

  const markRead = async (id) => {
    try {
      await axios.put(`/api/v1/notifications/${id}/read`);
      message.success('已标记为已读');
      fetchNotifications();
    } catch (error) {
      message.error(error.response?.data?.detail || '操作失败');
    }
  };

  const markAllRead = async () => {
    try {
      await axios.put('/api/v1/notifications/read-all');
      message.success('已全部标记为已读');
      fetchNotifications();
    } catch (error) {
      message.error(error.response?.data?.detail || '操作失败');
    }
  };

  const clearRead = async () => {
    try {
      await axios.delete('/api/v1/notifications/clear-read');
      message.success('已清空已读通知');
      fetchNotifications();
    } catch (error) {
      message.error(error.response?.data?.detail || '操作失败');
    }
  };

  const deleteItem = async (id) => {
    try {
      await axios.delete(`/api/v1/notifications/${id}`);
      message.success('通知已删除');
      fetchNotifications();
    } catch (error) {
      message.error(error.response?.data?.detail || '删除失败');
    }
  };

  const typeMeta = {
    task_assignment: { label: '待分配', color: 'gold', icon: <TeamOutlined /> },
    expert_invite: { label: '专家邀请', color: 'blue', icon: <BellOutlined /> },
    next_round: { label: '下一轮评估', color: 'orange', icon: <BellOutlined /> },
    report_generated: { label: '报告生成', color: 'green', icon: <FileTextOutlined /> },
    system: { label: '系统通知', color: 'default', icon: <BellOutlined /> },
  };

  const columns = [
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 120,
      render: (value) => {
        const meta = typeMeta[value] || typeMeta.system;
        return (
          <Tag color={meta.color} icon={meta.icon}>
            {meta.label}
          </Tag>
        );
      },
    },
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      width: 200,
      render: (value, record) => (
        <Space>
          {!record.is_read && <Badge color="red" />}
          <span>{value || '-'}</span>
        </Space>
      ),
    },
    {
      title: '内容',
      dataIndex: 'content',
      key: 'content',
      render: (value) => value || '-',
    },
    {
      title: '状态',
      dataIndex: 'is_read',
      key: 'is_read',
      width: 100,
      render: (value) => (
        <StatusTag status={value ? 'read' : 'unread'} map={{
          read: { color: 'default', text: '已读' },
          unread: { color: 'processing', text: '未读' },
        }}
        />
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 180,
      render: (_, record) => (
        <Space>
          {!record.is_read && (
            <Tooltip title="标记为已读">
              <Button size="small" onClick={() => markRead(record.id)}>
                标记已读
              </Button>
            </Tooltip>
          )}
          <Popconfirm title="确定删除此通知吗？" onConfirm={() => deleteItem(record.id)}>
            <Button size="small" danger>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="消息通知"
        extra={(
          <Space>
            <Button icon={<ReloadOutlined />} onClick={fetchNotifications}>
              刷新
            </Button>
            <Button onClick={markAllRead}>
              全部已读
            </Button>
            <Button onClick={clearRead}>
              清空已读
            </Button>
          </Space>
        )}
      />
      <Card>
        <DataTable
          rowKey="id"
          columns={columns}
          dataSource={items}
          loading={loading}
          pagination={{ pageSize: 10 }}
        />
      </Card>
    </div>
  );
};

export default NotificationPage;
