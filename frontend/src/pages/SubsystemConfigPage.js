import React, { useState, useEffect, useMemo } from 'react';
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
  Tag
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

const SubsystemConfigPage = ({ embedded = false }) => {
  const [mappings, setMappings] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingRecord, setEditingRecord] = useState(null);
  const [form] = Form.useForm();

  const extraKeys = useMemo(() => {
    const order = [];
    const seen = new Set();
    (mappings || []).forEach((item) => {
      const extra = item?.extra || {};
      Object.keys(extra).forEach((key) => {
        if (!key || seen.has(key)) return;
        seen.add(key);
        order.push(key);
      });
    });
    return order;
  }, [mappings]);

  // 加载子系统映射
  const fetchMappings = async () => {
    setLoading(true);
    try {
      const response = await axios.get('/api/v1/subsystem/mappings');
      setMappings(response.data.data.items || []);
    } catch (error) {
      console.error('获取子系统映射失败:', error);
      message.error('获取子系统映射失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMappings();
  }, []);

  // 打开新增对话框
  const handleAdd = () => {
    setEditingRecord(null);
    form.resetFields();
    form.setFieldsValue({ extra: {} });
    setModalVisible(true);
  };

  // 打开编辑对话框
  const handleEdit = (record) => {
    setEditingRecord(record);
    form.setFieldsValue({
      subsystem: record.subsystem,
      main_system: record.mainSystem,
      extra: record.extra || {}
    });
    setModalVisible(true);
  };

  // 删除映射
  const handleDelete = async (mappingId) => {
    try {
      await axios.delete(`/api/v1/subsystem/mappings/${encodeURIComponent(mappingId)}`);
      message.success('删除成功');
      fetchMappings();
    } catch (error) {
      console.error('删除失败:', error);
      message.error('删除失败');
    }
  };

  // 保存映射
  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      const payload = {
        subsystem: values.subsystem ?? '',
        main_system: values.main_system ?? '',
        extra: values.extra || {}
      };

      if (editingRecord) {
        // 更新
        const targetId = editingRecord.id || editingRecord.subsystem;
        await axios.put(`/api/v1/subsystem/mappings/${encodeURIComponent(targetId)}`, {
          ...payload
        });
        message.success('更新成功');
      } else {
        // 新增
        await axios.post('/api/v1/subsystem/mappings', payload);
        message.success('添加成功');
      }

      setModalVisible(false);
      fetchMappings();
    } catch (error) {
      console.error('保存失败:', error);
      message.error(error.response?.data?.detail || '保存失败');
    }
  };

  // 重新加载映射
  const handleReload = async () => {
    try {
      await axios.post('/api/v1/subsystem/reload');
      message.success('重新加载成功');
      fetchMappings();
    } catch (error) {
      console.error('重新加载失败:', error);
      message.error('重新加载失败');
    }
  };

  // 列配置
  const columns = [
    {
      title: '子系统名称',
      dataIndex: 'subsystem',
      key: 'subsystem',
      width: 300,
      fixed: 'left',
    },
    {
      title: '所属主系统',
      dataIndex: 'mainSystem',
      key: 'mainSystem',
      width: 300,
      render: (text) => (text ? <Tag color="blue">{text}</Tag> : '-')
    },
    ...extraKeys.map((key) => ({
      title: key,
      key: `extra-${key}`,
      dataIndex: ['extra', key],
      width: 220,
      render: (text) => (text ? String(text) : '-')
    })),
    {
      title: '操作',
      key: 'action',
      width: 150,
      fixed: 'right',
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
            title="确定要删除这个映射关系吗？"
            onConfirm={() => handleDelete(record.id || record.subsystem)}
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
    <div style={{ padding: embedded ? 0 : '24px' }}>
      <Card>
        <div style={{ marginBottom: 16 }}>
          <Title level={3}>子系统与主系统映射配置</Title>
          <Text type="secondary">
            配置子系统与其所属主系统的映射关系，避免将子系统误识别为主系统
          </Text>
        </div>

        <div style={{ marginBottom: 16 }}>
          <Space>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleAdd}
            >
              新增映射
            </Button>
            <Button
              icon={<ReloadOutlined />}
              onClick={fetchMappings}
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
          dataSource={mappings}
          rowKey={(record, index) => record.id || `${record.subsystem || 'row'}-${index}`}
          loading={loading}
          scroll={{ x: 'max-content' }}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条记录`
          }}
        />
      </Card>

      <Modal
        title={editingRecord ? '编辑映射' : '新增映射'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={handleSubmit}
        width={600}
        destroyOnClose
        bodyStyle={{ maxHeight: '70vh', overflowY: 'auto' }}
      >
        <Form
          form={form}
          layout="vertical"
          autoComplete="off"
        >
          <Form.Item
            label="子系统名称"
            name="subsystem"
            rules={[
              { max: 100, message: '子系统名称不能超过100个字符' }
            ]}
          >
          <Input
            placeholder="例如：开放存、联合贷平台"
          />
          </Form.Item>

          <Form.Item
            label="所属主系统"
            name="main_system"
            rules={[
              { max: 50, message: '主系统名称不能超过50个字符' }
            ]}
          >
            <Input
              placeholder="例如：HOP、CLMP、ECIF"
              style={{ width: '100%' }}
            />
          </Form.Item>

          {extraKeys.length ? (
            <div style={{ marginTop: 8 }}>
              <Title level={5} style={{ marginBottom: 8 }}>其它字段（来自模板列）</Title>
              {extraKeys.map((key) => (
                <Form.Item key={key} label={key} name={['extra', key]}>
                  {/(描述|备注|关联系统)/.test(key) ? (
                    <Input.TextArea autoSize={{ minRows: 2, maxRows: 6 }} />
                  ) : (
                    <Input />
                  )}
                </Form.Item>
              ))}
            </div>
          ) : null}

          <div style={{ marginTop: 16, padding: 12, background: '#f0f2f5', borderRadius: 4 }}>
            <Text type="secondary" style={{ fontSize: 12 }}>
              💡 提示：
              <br />
              • 子系统名称：需求文档中可能被误识别的子系统或模块名称
              <br />
              • 主系统名称：该子系统所属的标准主系统简称（如HOP、CLMP等）
              <br />
              • 配置后，系统识别时会自动将子系统映射到主系统
            </Text>
          </div>
        </Form>
      </Modal>
    </div>
  );
};

export default SubsystemConfigPage;
