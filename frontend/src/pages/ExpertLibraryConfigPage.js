import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Button,
  Card,
  Col,
  Form,
  Input,
  Modal,
  Row,
  Select,
  Space,
  Switch,
  Tag,
  message,
} from 'antd';
import {
  PlusOutlined,
  ReloadOutlined,
  SettingOutlined,
  UserDeleteOutlined,
} from '@ant-design/icons';
import axios from 'axios';
import PageHeader from '../components/PageHeader';
import DataTable from '../components/DataTable';
import StatusTag from '../components/StatusTag';
import ConfirmModal from '../components/ConfirmModal';

const ExpertLibraryConfigPage = () => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);

  const [departments, setDepartments] = useState([]);
  const [deptModalVisible, setDeptModalVisible] = useState(false);
  const [deptSaving, setDeptSaving] = useState(false);
  const [deptDraft, setDeptDraft] = useState([]);
  const [deptInput, setDeptInput] = useState('');

  const [modalVisible, setModalVisible] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [selectedUserId, setSelectedUserId] = useState(null);
  const [form] = Form.useForm();

  const [removeTarget, setRemoveTarget] = useState(null);
  const [removeLoading, setRemoveLoading] = useState(false);

  const fetchUsers = useCallback(async () => {
    try {
      setLoading(true);
      const response = await axios.get('/api/v1/users');
      setUsers(response.data.data || []);
    } catch (error) {
      message.error(error.response?.data?.detail || '获取用户失败');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchDepartments = useCallback(async () => {
    try {
      const response = await axios.get('/api/v1/departments');
      const list = response.data?.data?.departments || [];
      setDepartments(list);
    } catch (error) {
      message.error(error.response?.data?.detail || '获取部门清单失败');
    }
  }, []);

  useEffect(() => {
    fetchUsers();
    fetchDepartments();
  }, [fetchUsers, fetchDepartments]);

  const experts = useMemo(() => {
    return (users || []).filter((user) => (user.roles || []).includes('expert'));
  }, [users]);

  const candidateUsers = useMemo(() => {
    return (users || []).filter((user) => !(user.roles || []).includes('expert'));
  }, [users]);

  const expertiseOptions = useMemo(() => {
    const all = new Set();
    for (const user of experts) {
      for (const item of (user.expertise || [])) {
        if (item) all.add(item);
      }
    }
    return Array.from(all).sort().map((item) => ({ label: item, value: item }));
  }, [experts]);

  const departmentOptions = useMemo(() => {
    return (departments || []).map((item) => ({ label: item, value: item }));
  }, [departments]);

  const openDeptConfig = () => {
    setDeptDraft(departments || []);
    setDeptInput('');
    setDeptModalVisible(true);
  };

  const addDepartmentDraft = () => {
    const name = (deptInput || '').trim();
    if (!name) return;
    if (deptDraft.includes(name)) {
      message.info('部门已存在');
      return;
    }
    setDeptDraft([...deptDraft, name]);
    setDeptInput('');
  };

  const saveDepartments = async () => {
    try {
      setDeptSaving(true);
      const response = await axios.put('/api/v1/departments', { departments: deptDraft });
      const saved = response.data?.data?.departments || [];
      setDepartments(saved);
      message.success('部门清单已保存');
      setDeptModalVisible(false);
    } catch (error) {
      message.error(error.response?.data?.detail || '保存部门清单失败');
    } finally {
      setDeptSaving(false);
    }
  };

  const onOpenAdd = () => {
    setEditingUser(null);
    setSelectedUserId(null);
    form.resetFields();
    form.setFieldsValue({
      onDuty: true,
      expertise: [],
    });
    setModalVisible(true);
  };

  const onOpenEdit = (record) => {
    setEditingUser(record);
    setSelectedUserId(null);
    form.resetFields();
    form.setFieldsValue({
      department: record.department || undefined,
      expertise: record.expertise || [],
      onDuty: record.on_duty ?? true,
    });
    setModalVisible(true);
  };

  const resolveTargetUser = () => {
    if (editingUser) return editingUser;
    if (!selectedUserId) return null;
    return (users || []).find((user) => user.id === selectedUserId) || null;
  };

  const saveExpert = async () => {
    const target = resolveTargetUser();
    if (!target) {
      message.warning('请选择要加入专家库的用户账号');
      return;
    }
    try {
      const values = await form.validateFields();
      const roles = Array.from(new Set([...(target.roles || []), 'expert']));
      setSaving(true);
      await axios.put(`/api/v1/users/${target.id}`, {
        roles,
        department: values.department,
        expertise: values.expertise,
        onDuty: values.onDuty,
      });
      message.success('专家信息已保存');
      setModalVisible(false);
      setEditingUser(null);
      setSelectedUserId(null);
      fetchUsers();
    } catch (error) {
      if (error.errorFields) return;
      message.error(error.response?.data?.detail || '保存失败');
    } finally {
      setSaving(false);
    }
  };

  const toggleOnDuty = async (record) => {
    try {
      const next = !(record.on_duty ?? true);
      await axios.put(`/api/v1/users/${record.id}`, { onDuty: next });
      message.success(next ? '已设为在岗' : '已设为休假');
      fetchUsers();
    } catch (error) {
      message.error(error.response?.data?.detail || '更新在岗状态失败');
    }
  };

  const removeExpert = async () => {
    if (!removeTarget) return;
    try {
      setRemoveLoading(true);
      const nextRoles = (removeTarget.roles || []).filter((role) => role !== 'expert');
      await axios.put(`/api/v1/users/${removeTarget.id}`, { roles: nextRoles });
      message.success('已移出专家库');
      setRemoveTarget(null);
      fetchUsers();
    } catch (error) {
      message.error(error.response?.data?.detail || '移出失败');
    } finally {
      setRemoveLoading(false);
    }
  };

  const onDutyTag = (value) => {
    const onDuty = value ?? true;
    return <StatusTag status={onDuty ? 'enabled' : 'disabled'} text={onDuty ? '在岗' : '休假'} color={onDuty ? 'success' : 'error'} />;
  };

  const columns = [
    { title: '账号', dataIndex: 'username', key: 'username', width: 140 },
    { title: '姓名', dataIndex: 'display_name', key: 'display_name', width: 140 },
    {
      title: '部门',
      dataIndex: 'department',
      key: 'department',
      width: 160,
      render: (value) => value || '-',
    },
    {
      title: '专长',
      dataIndex: 'expertise',
      key: 'expertise',
      width: 300,
      render: (value) => {
        const list = value || [];
        if (!list.length) return '-';
        return (
          <Space size={[4, 4]} wrap>
            {list.slice(0, 12).map((item) => (
              <Tag key={item} color="blue">{item}</Tag>
            ))}
            {list.length > 12 ? <Tag>+{list.length - 12}</Tag> : null}
          </Space>
        );
      },
    },
    {
      title: '在岗',
      dataIndex: 'on_duty',
      key: 'on_duty',
      width: 110,
      render: (value) => onDutyTag(value),
    },
    {
      title: '账号状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 110,
      render: (value) => <StatusTag status={value ? 'enabled' : 'disabled'} />,
    },
    {
      title: '操作',
      key: 'action',
      width: 240,
      fixed: 'right',
      render: (_, record) => (
        <Space>
          <Button size="small" onClick={() => onOpenEdit(record)}>编辑</Button>
          <Button size="small" onClick={() => toggleOnDuty(record)}>
            {(record.on_duty ?? true) ? '设为休假' : '设为在岗'}
          </Button>
          <Button size="small" danger icon={<UserDeleteOutlined />} onClick={() => setRemoveTarget(record)}>
            移出
          </Button>
        </Space>
      ),
    },
  ];

  const target = resolveTargetUser();
  const addMode = !editingUser;

  return (
    <div>
      <PageHeader
        title="专家库配置"
        subtitle="专家必须绑定系统用户账号；默认在岗（未休假=可用）"
        extra={(
          <Space>
            <Button icon={<SettingOutlined />} onClick={openDeptConfig}>
              部门配置
            </Button>
            <Button icon={<ReloadOutlined />} onClick={fetchUsers} loading={loading}>
              刷新
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={onOpenAdd}>
              添加专家
            </Button>
          </Space>
        )}
      />

      <Card>
        <DataTable
          rowKey="id"
          columns={columns}
          dataSource={experts}
          loading={loading}
          scroll={{ x: 1200 }}
        />
      </Card>

      <Modal
        title={addMode ? '添加专家' : '编辑专家'}
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false);
          setEditingUser(null);
          setSelectedUserId(null);
        }}
        onOk={saveExpert}
        okText="保存"
        cancelText="取消"
        confirmLoading={saving}
        width={640}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          {addMode ? (
            <Form.Item label="选择用户账号" required>
              <Select
                showSearch
                placeholder="请选择要加入专家库的用户"
                value={selectedUserId || undefined}
                optionFilterProp="label"
                onChange={setSelectedUserId}
                options={candidateUsers.map((user) => ({
                  value: user.id,
                  label: `${user.display_name || user.username}（${user.username}）`,
                }))}
              />
            </Form.Item>
          ) : (
            <Space style={{ marginBottom: 12 }}>
              <Tag color="blue">{editingUser?.display_name || '-'}</Tag>
              <Tag>{editingUser?.username || '-'}</Tag>
            </Space>
          )}

          <Row gutter={16}>
            <Col xs={24} md={12}>
              <Form.Item
                label="部门"
                name="department"
                extra={departmentOptions.length ? null : '部门清单未配置，请先点击“部门配置”维护下拉选项。'}
              >
                <Select
                  placeholder={departmentOptions.length ? '请选择部门' : '请先配置部门清单'}
                  options={departmentOptions}
                  disabled={!departmentOptions.length}
                  showSearch
                  optionFilterProp="label"
                  allowClear
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item label="在岗" name="onDuty" valuePropName="checked">
                <Switch checkedChildren="在岗" unCheckedChildren="休假" />
              </Form.Item>
            </Col>
            <Col xs={24}>
              <Form.Item label="专长（多标签）" name="expertise">
                <Select
                  mode="tags"
                  placeholder="输入专长后回车添加，例如：信贷、支付、架构、性能"
                  tokenSeparators={[' ', ',', '，']}
                  options={expertiseOptions}
                />
              </Form.Item>
            </Col>
          </Row>

          {target && addMode ? (
            <div style={{ marginTop: 8 }}>
              <Tag color="blue">{target.display_name || '-'}</Tag>
              <Tag>{target.username || '-'}</Tag>
            </div>
          ) : null}
        </Form>
      </Modal>

      <Modal
        title="部门配置（固定下拉）"
        open={deptModalVisible}
        onCancel={() => setDeptModalVisible(false)}
        onOk={saveDepartments}
        okText="保存"
        cancelText="取消"
        confirmLoading={deptSaving}
        width={720}
        destroyOnClose
      >
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Space.Compact style={{ width: '100%' }}>
            <Input
              value={deptInput}
              onChange={(e) => setDeptInput(e.target.value)}
              placeholder="输入部门名称后点击添加"
              onPressEnter={addDepartmentDraft}
            />
            <Button type="primary" onClick={addDepartmentDraft}>
              添加
            </Button>
          </Space.Compact>

          <div>
            <div style={{ marginBottom: 8, color: 'rgba(0,0,0,0.45)' }}>当前部门清单：</div>
            {deptDraft.length ? (
              <Space size={[8, 8]} wrap>
                {deptDraft.map((dept) => (
                  <Tag
                    key={dept}
                    closable
                    onClose={(e) => {
                      e.preventDefault();
                      setDeptDraft(deptDraft.filter((item) => item !== dept));
                    }}
                  >
                    {dept}
                  </Tag>
                ))}
              </Space>
            ) : (
              <div style={{ color: 'rgba(0,0,0,0.45)' }}>暂无部门，请先添加</div>
            )}
          </div>
        </Space>
      </Modal>

      <ConfirmModal
        open={Boolean(removeTarget)}
        title="移出专家库"
        content={`确定将 ${removeTarget?.display_name || removeTarget?.username || ''} 移出专家库吗？（账号不会被删除）`}
        okText="移出"
        cancelText="取消"
        onOk={removeExpert}
        onCancel={() => setRemoveTarget(null)}
        confirmLoading={removeLoading}
        danger
      />
    </div>
  );
};

export default ExpertLibraryConfigPage;
