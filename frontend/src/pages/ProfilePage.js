import React, { useEffect, useState, useCallback, useMemo } from 'react';
import {
  Avatar,
  Button,
  Card,
  Collapse,
  Col,
  Form,
  Input,
  message,
  Row,
  Space,
  Table,
  Typography,
  Upload,
} from 'antd';
import { UploadOutlined, UserOutlined } from '@ant-design/icons';
import axios from 'axios';
import useAuth from '../hooks/useAuth';
import './ProfilePage.css';

const { Text } = Typography;

const ProfilePage = () => {
  const { user, refreshUser } = useAuth();
  const [loading, setLoading] = useState(false);
  const [profileForm] = Form.useForm();
  const [activityItems, setActivityItems] = useState([]);
  const [activityLoading, setActivityLoading] = useState(false);
  const [passwordForm] = Form.useForm();
  const [profile, setProfile] = useState(null);
  const [avatarUploading, setAvatarUploading] = useState(false);

  const avatarSrc = useMemo(() => profile?.avatar || user?.avatar || '', [profile, user]);

  const fetchProfile = useCallback(async () => {
    try {
      const response = await axios.get('/api/v1/profile');
      const data = response.data.data || {};
      setProfile(data);
      profileForm.setFieldsValue({
        displayName: data.displayName || '',
        email: data.email || '',
        phone: data.phone || '',
        department: data.department || '',
      });
    } catch (error) {
      message.error(error.response?.data?.detail || '获取个人信息失败');
    }
  }, [profileForm]);

  const fetchActivities = useCallback(async () => {
    try {
      setActivityLoading(true);
      const response = await axios.get('/api/v1/profile/activity-logs');
      setActivityItems(response.data.data?.items || []);
    } catch (error) {
      message.error(error.response?.data?.detail || '获取操作记录失败');
    } finally {
      setActivityLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProfile();
    fetchActivities();
  }, [fetchProfile, fetchActivities]);

  const handleUpdateProfile = async () => {
    try {
      const values = await profileForm.validateFields();
      setLoading(true);
      await axios.put('/api/v1/profile', {
        displayName: values.displayName,
        email: values.email,
        phone: values.phone,
        department: values.department,
      });
      message.success('个人信息已更新');
      refreshUser();
      fetchProfile();
    } catch (error) {
      if (error.errorFields) {
        return;
      }
      message.error(error.response?.data?.detail || '更新失败');
    } finally {
      setLoading(false);
    }
  };

  const handleChangePassword = async () => {
    try {
      const values = await passwordForm.validateFields();
      setLoading(true);
      await axios.post('/api/v1/auth/change-password', {
        oldPassword: values.oldPassword,
        newPassword: values.newPassword,
      });
      message.success('密码已更新');
      passwordForm.resetFields();
      refreshUser();
      fetchActivities();
    } catch (error) {
      if (error.errorFields) {
        return;
      }
      message.error(error.response?.data?.detail || '修改失败');
    } finally {
      setLoading(false);
    }
  };

  const handleAvatarUpload = async ({ file, onSuccess, onError }) => {
    try {
      setAvatarUploading(true);
      const formData = new FormData();
      formData.append('file', file);
      const response = await axios.post('/api/v1/profile/avatar', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      message.success('头像已更新');
      onSuccess?.(response.data);
      refreshUser();
      fetchProfile();
    } catch (error) {
      onError?.(error);
      message.error(error.response?.data?.detail || '上传失败');
    } finally {
      setAvatarUploading(false);
    }
  };

  const beforeAvatarUpload = (file) => {
    if (!file.type || !file.type.startsWith('image/')) {
      message.error('仅支持图片格式');
      return Upload.LIST_IGNORE;
    }
    return true;
  };

  const formatDate = (value) => {
    if (!value) {
      return '-';
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value;
    }
    return date.toLocaleString();
  };

  return (
    <div className="profile-page">
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={8}>
          <Card>
            <div className="profile-avatar">
              <Avatar size={96} src={avatarSrc} icon={<UserOutlined />} />
              <Upload
                showUploadList={false}
                customRequest={handleAvatarUpload}
                beforeUpload={beforeAvatarUpload}
              >
                <Button icon={<UploadOutlined />} loading={avatarUploading}>
                  上传头像
                </Button>
              </Upload>
            </div>
            <Space direction="vertical" size={8} className="profile-info-list">
              <Text>用户名：{user?.username || '-'}</Text>
              <Text>姓名：{profile?.displayName || user?.displayName || '-'}</Text>
              <Text>邮箱：{profile?.email || '-'}</Text>
              <Text>手机：{profile?.phone || '-'}</Text>
              <Text>部门：{profile?.department || '-'}</Text>
              <Text>角色：{(user?.roles || []).join(' / ') || '-'}</Text>
              <Text>最近登录：{formatDate(profile?.lastLoginAt)}</Text>
            </Space>
          </Card>
        </Col>
        <Col xs={24} lg={16}>
          <Card>
            <Collapse
              defaultActiveKey={['basic']}
              items={[
                {
                  key: 'basic',
                  label: '基本信息',
                  children: (
                    <Form form={profileForm} layout="vertical" style={{ maxWidth: 480 }}>
                      <Form.Item
                        label="姓名"
                        name="displayName"
                        rules={[{ required: true, message: '请输入姓名' }]}
                      >
                        <Input />
                      </Form.Item>
                      <Form.Item label="邮箱" name="email">
                        <Input />
                      </Form.Item>
                      <Form.Item label="手机" name="phone">
                        <Input />
                      </Form.Item>
                      <Form.Item label="部门" name="department">
                        <Input />
                      </Form.Item>
                      <Button type="primary" onClick={handleUpdateProfile} loading={loading}>
                        保存资料
                      </Button>
                    </Form>
                  ),
                },
                {
                  key: 'security',
                  label: '密码安全',
                  children: (
                    <Form form={passwordForm} layout="vertical" style={{ maxWidth: 360 }}>
                      <Form.Item
                        label="旧密码"
                        name="oldPassword"
                        rules={[{ required: true, message: '请输入旧密码' }]}
                      >
                        <Input.Password />
                      </Form.Item>
                      <Form.Item
                        label="新密码"
                        name="newPassword"
                        rules={[{ required: true, message: '请输入新密码' }]}
                      >
                        <Input.Password />
                      </Form.Item>
                      <Button type="primary" onClick={handleChangePassword} loading={loading}>
                        更新密码
                      </Button>
                    </Form>
                  ),
                },
                {
                  key: 'activity',
                  label: '操作记录',
                  children: (
                    <Table
                      rowKey="id"
                      dataSource={activityItems}
                      loading={activityLoading}
                      pagination={{ pageSize: 5 }}
                      columns={[
                        { title: '时间', dataIndex: 'created_at', key: 'created_at', width: 180 },
                        { title: '操作', dataIndex: 'action', key: 'action', width: 140 },
                        { title: '详情', dataIndex: 'detail', key: 'detail' },
                      ]}
                    />
                  ),
                },
              ]}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default ProfilePage;
