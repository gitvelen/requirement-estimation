import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Badge, Button, Card, message, Popconfirm, Space, Tag, Tooltip, Typography } from 'antd';
import { BellOutlined, FileTextOutlined, ReloadOutlined } from '@ant-design/icons';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import useNotification from '../hooks/useNotification';
import DataTable from '../components/DataTable';
import StatusTag from '../components/StatusTag';
import { formatDateTime } from '../utils/time';

const { Text } = Typography;

const parseErrorMessage = (error, fallback) => {
  const responseData = error?.response?.data;
  return responseData?.message || responseData?.detail || fallback;
};

const NotificationPage = () => {
  const navigate = useNavigate();
  const { refreshUnread } = useNotification() || {};

  const [loading, setLoading] = useState(false);
  const [items, setItems] = useState([]);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [total, setTotal] = useState(0);

  const fetchNotifications = useCallback(async (nextPage, nextSize) => {
    try {
      setLoading(true);
      const response = await axios.get('/api/v1/notifications', {
        params: { page: nextPage, page_size: nextSize },
      });
      setItems(response.data?.items || []);
      setTotal(Number(response.data?.total || 0));
      if (refreshUnread) {
        refreshUnread();
      }
    } catch (error) {
      message.error(parseErrorMessage(error, '获取通知失败'));
    } finally {
      setLoading(false);
    }
  }, [refreshUnread]);

  useEffect(() => {
    fetchNotifications(1, pageSize);
    setPage(1);
  }, [fetchNotifications, pageSize]);

  const markRead = async (notificationId) => {
    try {
      await axios.put(`/api/v1/notifications/${encodeURIComponent(notificationId)}/read`);
      message.success('已标记为已读');
      fetchNotifications(page, pageSize);
    } catch (error) {
      message.error(parseErrorMessage(error, '操作失败'));
    }
  };

  const markAllRead = async () => {
    try {
      await axios.put('/api/v1/notifications/read-all');
      message.success('已全部标记为已读');
      fetchNotifications(page, pageSize);
    } catch (error) {
      message.error(parseErrorMessage(error, '操作失败'));
    }
  };

  const clearRead = async () => {
    try {
      await axios.delete('/api/v1/notifications/clear-read');
      message.success('已清空已读通知');
      fetchNotifications(1, pageSize);
      setPage(1);
    } catch (error) {
      message.error(parseErrorMessage(error, '操作失败'));
    }
  };

  const deleteItem = async (notificationId) => {
    try {
      await axios.delete(`/api/v1/notifications/${encodeURIComponent(notificationId)}`);
      message.success('通知已删除');
      fetchNotifications(page, pageSize);
    } catch (error) {
      message.error(parseErrorMessage(error, '删除失败'));
    }
  };

  const typeMeta = useMemo(() => ({
    system_profile_summary_ready: { label: '画像AI总结完成', color: 'green', icon: <BellOutlined /> },
    system_profile_summary_failed: { label: '画像AI总结失败', color: 'red', icon: <BellOutlined /> },
    report_generated: { label: '报告生成', color: 'green', icon: <FileTextOutlined /> },
    system: { label: '系统通知', color: 'default', icon: <BellOutlined /> },
  }), []);

  const columns = [
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (value) => formatDateTime(value),
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 160,
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
      key: 'title',
      width: 220,
      render: (_, record) => {
        const payload = record.payload && typeof record.payload === 'object' ? record.payload : {};
        const title = payload.title || '-';
        return (
          <Space>
            {record.status !== 'read' && <Badge color="red" />}
            <span>{title}</span>
          </Space>
        );
      },
    },
    {
      title: '内容',
      key: 'content',
      render: (_, record) => {
        const payload = record.payload && typeof record.payload === 'object' ? record.payload : {};
        const content = payload.content || '-';
        const errorReason = payload.error_reason || '';
        return (
          <Space direction="vertical" size={0}>
            <span>{content}</span>
            {errorReason ? <Text type="secondary">{String(errorReason)}</Text> : null}
          </Space>
        );
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (value) => (
        <StatusTag
          status={value || 'unread'}
          map={{
            read: { color: 'default', text: '已读' },
            unread: { color: 'processing', text: '未读' },
          }}
        />
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 260,
      render: (_, record) => {
        const payload = record.payload && typeof record.payload === 'object' ? record.payload : {};
        const link = String(payload.link || '').trim();
        const openLink = async () => {
          if (record.status !== 'read') {
            await markRead(record.notification_id);
          }
          if (link.startsWith('/')) {
            navigate(link);
          } else if (link) {
            window.open(link, '_blank', 'noopener,noreferrer');
          }
        };

        return (
          <Space>
            {link ? (
              <Tooltip title="打开详情">
                <Button size="small" onClick={openLink}>
                  打开
                </Button>
              </Tooltip>
            ) : null}
            {record.status !== 'read' ? (
              <Tooltip title="标记为已读">
                <Button size="small" onClick={() => markRead(record.notification_id)}>
                  标记已读
                </Button>
              </Tooltip>
            ) : null}
            <Popconfirm title="确定删除此通知吗？" onConfirm={() => deleteItem(record.notification_id)}>
              <Button size="small" danger>
                删除
              </Button>
            </Popconfirm>
          </Space>
        );
      },
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'flex-end' }}>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={() => fetchNotifications(page, pageSize)} loading={loading}>
            刷新
          </Button>
          <Button onClick={markAllRead} disabled={!items.length}>
            全部已读
          </Button>
          <Button onClick={clearRead} disabled={!items.length}>
            清空已读
          </Button>
        </Space>
      </div>
      <Card>
        <DataTable
          rowKey="notification_id"
          columns={columns}
          dataSource={items}
          loading={loading}
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
              fetchNotifications(nextPage, nextSize);
            },
          }}
        />
      </Card>
    </div>
  );
};

export default NotificationPage;
