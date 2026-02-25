import React, { useEffect, useState } from 'react';
import { Button, Card, Col, Form, Input, Modal, Row, Space, Tag, Upload, message } from 'antd';
import { PlusOutlined, UploadOutlined } from '@ant-design/icons';
import axios from 'axios';
import DataTable from '../components/DataTable';
import StatusTag from '../components/StatusTag';
import ConfirmModal from '../components/ConfirmModal';

const roleLabelMap = {
  admin: '管理员',
  manager: '项目经理',
  expert: '专家',
};

const UserManagementPage = () => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [form] = Form.useForm();

  const [importVisible, setImportVisible] = useState(false);
  const [importFile, setImportFile] = useState(null);
  const [importRows, setImportRows] = useState([]);
  const [importing, setImporting] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  const fetchUsers = async () => {
    try {
      setLoading(true);
      const response = await axios.get('/api/v1/users');
      setUsers(response.data.data || []);
    } catch (error) {
      message.error(error.response?.data?.detail || '获取用户失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const handleCreate = () => {
    setEditingUser(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleDownloadTemplate = async () => {
    try {
      const response = await axios.get('/api/v1/users/template', {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', '用户导入模板.xlsx');
      document.body.appendChild(link);
      link.click();
      link.remove();
      message.success('模板已下载');
    } catch (error) {
      message.error(error.response?.data?.detail || '下载模板失败');
    }
  };

  const handleEdit = (record) => {
    setEditingUser(record);
    form.setFieldsValue({
      username: record.username,
      displayName: record.display_name,
      password: '',
      roles: (record.roles || []).join(','),
      email: record.email,
      phone: record.phone,
      department: record.department,
      expertise: (record.expertise || []).join(','),
    });
    setModalVisible(true);
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      const payload = {
        username: values.username,
        displayName: values.displayName,
        password: values.password,
        roles: values.roles ? values.roles.split(/[,，]/).map((v) => v.trim()).filter(Boolean) : [],
        email: values.email,
        phone: values.phone,
        department: values.department,
        expertise: values.expertise ? values.expertise.split(/[,，]/).map((v) => v.trim()).filter(Boolean) : [],
      };

      if (editingUser) {
        if (!payload.password) {
          delete payload.password;
        }
        await axios.put(`/api/v1/users/${editingUser.id}`, payload);
        message.success('用户已更新');
      } else {
        await axios.post('/api/v1/users', payload);
        message.success('用户已创建');
      }
      setModalVisible(false);
      fetchUsers();
    } catch (error) {
      if (error.errorFields) {
        return;
      }
      message.error(error.response?.data?.detail || '保存失败');
    }
  };

  const handleToggleStatus = async (record) => {
    try {
      await axios.put(`/api/v1/users/${record.id}/status`, { isActive: !record.is_active });
      message.success('状态已更新');
      fetchUsers();
    } catch (error) {
      message.error(error.response?.data?.detail || '更新失败');
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      setDeleteLoading(true);
      await axios.delete(`/api/v1/users/${deleteTarget.id}`);
      message.success('用户已删除');
      fetchUsers();
    } catch (error) {
      message.error(error.response?.data?.detail || '删除失败');
    } finally {
      setDeleteLoading(false);
      setDeleteTarget(null);
    }
  };

  const columns = [
    { title: '用户名', dataIndex: 'username', key: 'username', width: 120 },
    { title: '姓名', dataIndex: 'display_name', key: 'display_name', width: 120 },
    {
      title: '角色',
      dataIndex: 'roles',
      key: 'roles',
      width: 200,
      render: (roles) => (roles || []).map((role) => (
        <Tag key={role}>{roleLabelMap[role] || role}</Tag>
      )),
    },
    { title: '邮箱', dataIndex: 'email', key: 'email', width: 180 },
    { title: '手机', dataIndex: 'phone', key: 'phone', width: 140 },
    { title: '部门', dataIndex: 'department', key: 'department', width: 140 },
    {
      title: '专长领域',
      dataIndex: 'expertise',
      key: 'expertise',
      width: 200,
      render: (value) => (value && value.length ? value.join('、') : '-'),
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 100,
      render: (value) => <StatusTag status={value ? 'enabled' : 'disabled'} />,
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      fixed: 'right',
      render: (_, record) => (
        <Space>
          <Button size="small" onClick={() => handleEdit(record)}>
            编辑
          </Button>
          <Button size="small" onClick={() => handleToggleStatus(record)}>
            {record.is_active ? '禁用' : '启用'}
          </Button>
          <Button size="small" danger onClick={() => setDeleteTarget(record)}>
            删除
          </Button>
        </Space>
      ),
    },
  ];

  const parseImport = async () => {
    if (!importFile) {
      message.warning('请先选择文件');
      return;
    }
    try {
      setImporting(true);
      const formData = new FormData();
      formData.append('file', importFile);
      const response = await axios.post('/api/v1/users/batch-import', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setImportRows(response.data.data.rows || []);
    } catch (error) {
      message.error(error.response?.data?.detail || '解析失败');
    } finally {
      setImporting(false);
    }
  };

  const confirmImport = async () => {
    try {
      setImporting(true);
      await axios.post('/api/v1/users/batch-import/confirm', { users: importRows });
      message.success('批量导入完成');
      setImportVisible(false);
      setImportFile(null);
      setImportRows([]);
      fetchUsers();
    } catch (error) {
      message.error(error.response?.data?.detail || '导入失败');
    } finally {
      setImporting(false);
    }
  };

  const importColumns = [
    {
      title: '用户名',
      dataIndex: 'username',
      key: 'username',
      render: (value, record, index) => (
        <Input
          value={value}
          onChange={(e) => {
            const next = [...importRows];
            next[index].username = e.target.value;
            setImportRows(next);
          }}
        />
      ),
    },
    {
      title: '姓名',
      dataIndex: 'display_name',
      key: 'display_name',
      render: (value, record, index) => (
        <Input
          value={value}
          onChange={(e) => {
            const next = [...importRows];
            next[index].display_name = e.target.value;
            setImportRows(next);
          }}
        />
      ),
    },
    {
      title: '密码',
      dataIndex: 'password',
      key: 'password',
      render: (value, record, index) => (
        <Input
          value={value}
          onChange={(e) => {
            const next = [...importRows];
            next[index].password = e.target.value;
            setImportRows(next);
          }}
        />
      ),
    },
    {
      title: '角色',
      dataIndex: 'roles',
      key: 'roles',
      render: (value, record, index) => (
        <Input
          value={(value || []).join(',')}
          onChange={(e) => {
            const next = [...importRows];
            next[index].roles = e.target.value.split(/[,，]/).map((v) => v.trim()).filter(Boolean);
            setImportRows(next);
          }}
        />
      ),
    },
    {
      title: '邮箱',
      dataIndex: 'email',
      key: 'email',
      render: (value, record, index) => (
        <Input
          value={value}
          onChange={(e) => {
            const next = [...importRows];
            next[index].email = e.target.value;
            setImportRows(next);
          }}
        />
      ),
    },
    {
      title: '手机',
      dataIndex: 'phone',
      key: 'phone',
      render: (value, record, index) => (
        <Input
          value={value}
          onChange={(e) => {
            const next = [...importRows];
            next[index].phone = e.target.value;
            setImportRows(next);
          }}
        />
      ),
    },
    {
      title: '部门',
      dataIndex: 'department',
      key: 'department',
      render: (value, record, index) => (
        <Input
          value={value}
          onChange={(e) => {
            const next = [...importRows];
            next[index].department = e.target.value;
            setImportRows(next);
          }}
        />
      ),
    },
    {
      title: '专长领域',
      dataIndex: 'expertise',
      key: 'expertise',
      render: (value, record, index) => (
        <Input
          value={(value || []).join(',')}
          onChange={(e) => {
            const next = [...importRows];
            next[index].expertise = e.target.value.split(/[,，]/).map((v) => v.trim()).filter(Boolean);
            setImportRows(next);
          }}
        />
      ),
    },
    {
      title: '错误',
      dataIndex: 'errors',
      key: 'errors',
      render: (value) => value && value.length ? value.join('；') : '-',
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'flex-end' }}>
        <Space>
          <Button onClick={handleDownloadTemplate}>
            下载Excel模板
          </Button>
          <Button icon={<UploadOutlined />} onClick={() => setImportVisible(true)}>
            批量导入
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            创建用户
          </Button>
        </Space>
      </div>
      <Card>
        <DataTable
          rowKey="id"
          columns={columns}
          dataSource={users}
          loading={loading}
          scroll={{ x: 1200 }}
        />
      </Card>

      <Modal
        title={editingUser ? '编辑用户' : '创建用户'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={handleSave}
        okText="保存"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          <Row gutter={16}>
            <Col xs={24} md={12}>
              <Form.Item name="username" label="用户名" rules={[{ required: true, message: '请输入用户名' }]}>
                <Input disabled={!!editingUser} />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item name="displayName" label="姓名" rules={[{ required: true, message: '请输入姓名' }]}>
                <Input />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item name="password" label="密码" rules={editingUser ? [] : [{ required: true, message: '请输入密码' }]}>
                <Input.Password placeholder={editingUser ? '留空则不修改' : ''} />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item name="roles" label="角色">
                <Input placeholder="admin,manager,expert 或 管理员,项目经理,专家" />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item name="email" label="邮箱">
                <Input />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item name="phone" label="手机">
                <Input />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item name="department" label="部门">
                <Input />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item name="expertise" label="专长领域">
                <Input placeholder="多个用逗号分隔" />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>

      <Modal
        title="批量导入用户"
        open={importVisible}
        onCancel={() => {
          setImportVisible(false);
          setImportFile(null);
          setImportRows([]);
        }}
        onOk={importRows.length ? confirmImport : parseImport}
        okText={importRows.length ? '确认导入' : '解析文件'}
        cancelText="取消"
        confirmLoading={importing}
        width={1000}
      >
        <Upload
          beforeUpload={(file) => {
            setImportFile(file);
            return false;
          }}
          maxCount={1}
          accept=".xlsx,.xls"
        >
          <Button icon={<UploadOutlined />}>选择Excel文件</Button>
        </Upload>
        {importRows.length > 0 && (
          <DataTable
            rowKey={(record, index) => `${record.username || 'row'}-${index}`}
            columns={importColumns}
            dataSource={importRows}
            pagination={false}
            style={{ marginTop: 16 }}
            scroll={{ x: 1200, y: 360 }}
          />
        )}
      </Modal>
      <ConfirmModal
        open={Boolean(deleteTarget)}
        title="删除用户"
        content={`确定删除用户 ${deleteTarget?.display_name || deleteTarget?.username || ''} 吗？`}
        okText="删除"
        cancelText="取消"
        onOk={handleDelete}
        onCancel={() => setDeleteTarget(null)}
        confirmLoading={deleteLoading}
        danger
      />
    </div>
  );
};

export default UserManagementPage;
