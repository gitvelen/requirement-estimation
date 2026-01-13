import React, { useState, useEffect } from 'react';
import {
  Table,
  Button,
  Modal,
  Form,
  Input,
  message,
  Space,
  Popconfirm,
  Card,
  Typography,
  Tag,
  Select
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  ReloadOutlined,
  SaveOutlined
} from '@ant-design/icons';
import axios from 'axios';

const { Title, Text } = Typography;

const MainSystemConfigPage = () => {
  const [systems, setSystems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingRecord, setEditingRecord] = useState(null);
  const [form] = Form.useForm();

  // 状态选项
  const statusOptions = [
    { label: '运行中', value: '运行中' },
    { label: '建设中', value: '建设中' },
    { label: '已停用', value: '已停用' },
    { label: '规划中', value: '规划中' }
  ];

  // 加载主系统列表
  const fetchSystems = async () => {
    setLoading(true);
    try {
      const response = await axios.get('/api/v1/system/systems');
      setSystems(response.data.data.systems || []);
    } catch (error) {
      console.error('获取主系统列表失败:', error);
      message.error('获取主系统列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSystems();
  }, []);

  // 打开新增对话框
  const handleAdd = () => {
    setEditingRecord(null);
    form.resetFields();
    setModalVisible(true);
  };

  // 打开编辑对话框
  const handleEdit = (record) => {
    setEditingRecord(record);
    form.setFieldsValue({
      name: record.name,
      abbreviation: record.abbreviation,
      status: record.status
    });
    setModalVisible(true);
  };

  // 删除系统
  const handleDelete = async (systemName) => {
    try {
      await axios.delete(`/api/v1/system/systems/${encodeURIComponent(systemName)}`);
      message.success('删除成功');
      fetchSystems();
    } catch (error) {
      console.error('删除失败:', error);
      message.error(error.response?.data?.detail || '删除失败');
    }
  };

  // 保存系统
  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();

      if (editingRecord) {
        // 更新
        await axios.put(
          `/api/v1/system/systems/${encodeURIComponent(editingRecord.name)}`,
          values
        );
        message.success('更新成功');
      } else {
        // 新增
        await axios.post('/api/v1/system/systems', values);
        message.success('添加成功');
      }

      setModalVisible(false);
      fetchSystems();
    } catch (error) {
      console.error('保存失败:', error);
      message.error(error.response?.data?.detail || '保存失败');
    }
  };

  // 重新加载系统列表
  const handleReload = async () => {
    try {
      await axios.post('/api/v1/system/reload');
      message.success('重新加载成功');
      fetchSystems();
    } catch (error) {
      console.error('重新加载失败:', error);
      message.error('重新加载失败');
    }
  };

  // 状态颜色映射
  const getStatusColor = (status) => {
    const colorMap = {
      '运行中': 'green',
      '建设中': 'blue',
      '已停用': 'red',
      '规划中': 'orange'
    };
    return colorMap[status] || 'default';
  };

  // 列配置
  const columns = [
    {
      title: '系统名称',
      dataIndex: 'name',
      key: 'name',
      width: 300,
    },
    {
      title: '系统简称',
      dataIndex: 'abbreviation',
      key: 'abbreviation',
      width: 150,
      render: (text) => <Tag color="blue">{text}</Tag>
    },
    {
      title: '系统状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (text) => <Tag color={getStatusColor(text)}>{text}</Tag>
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定要删除这个系统吗？"
            onConfirm={() => handleDelete(record.name)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="link" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Card>
        <div style={{ marginBottom: 16 }}>
          <Title level={3}>标准主系统配置</Title>
          <Text type="secondary">
            配置标准主系统列表，用于系统识别和名称标准化
          </Text>
        </div>

        <div style={{ marginBottom: 16 }}>
          <Space>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleAdd}
            >
              新增系统
            </Button>
            <Button
              icon={<ReloadOutlined />}
              onClick={fetchSystems}
              loading={loading}
            >
              刷新
            </Button>
            <Button
              icon={<SaveOutlined />}
              onClick={handleReload}
            >
              重新加载（热更新）
            </Button>
          </Space>
        </div>

        <Table
          columns={columns}
          dataSource={systems}
          rowKey="name"
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条记录`
          }}
        />
      </Card>

      <Modal
        title={editingRecord ? '编辑系统' : '新增系统'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={handleSubmit}
        width={600}
        destroyOnClose
      >
        <Form
          form={form}
          layout="vertical"
          autoComplete="off"
        >
          <Form.Item
            label="系统名称"
            name="name"
            rules={[
              { required: true, message: '请输入系统名称' },
              { max: 100, message: '系统名称不能超过100个字符' }
            ]}
          >
            <Input
              placeholder="例如：新一代核心、支付中台、新移动银行"
              disabled={!!editingRecord}
            />
          </Form.Item>

          <Form.Item
            label="系统简称"
            name="abbreviation"
            rules={[
              { required: true, message: '请输入系统简称' },
              { max: 20, message: '系统简称不能超过20个字符' },
              { pattern: /^[A-Z0-9]+$/, message: '系统简称只能包含大写字母和数字' }
            ]}
          >
            <Input
              placeholder="例如：CBS、PAY、MBANK"
              style={{ textTransform: 'uppercase' }}
            />
          </Form.Item>

          <Form.Item
            label="系统状态"
            name="status"
            rules={[{ required: true, message: '请选择系统状态' }]}
          >
            <Select
              placeholder="请选择系统状态"
              options={statusOptions}
            />
          </Form.Item>

          <div style={{ marginTop: 16, padding: 12, background: '#f0f2f5', borderRadius: 4 }}>
            <Text type="secondary" style={{ fontSize: 12 }}>
              💡 提示：
              <br />
              • 系统名称：完整的系统名称，用于系统识别时的精确匹配
              <br />
              • 系统简称：系统的英文简称或缩写，通常使用大写字母
              <br />
              • 系统状态：标识系统的当前状态（运行中、建设中、已停用、规划中）
              <br />
              • 配置后，系统识别时会自动将需求中的系统名称标准化
            </Text>
          </div>
        </Form>
      </Modal>
    </div>
  );
};

export default MainSystemConfigPage;
