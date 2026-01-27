import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Tabs, Table, Button, Space, message, Card, Tag, Typography, Popconfirm, Modal, Input, Select, Row, Col, Statistic, Form, Tooltip } from 'antd';
import { CheckOutlined, PlusOutlined, DeleteOutlined, ArrowLeftOutlined, HistoryOutlined, EditOutlined, SaveOutlined } from '@ant-design/icons';
import axios from 'axios';

const { Title, Text } = Typography;
const { Option } = Select;
const { TextArea } = Input;

const EditPage = () => {
  const { taskId } = useParams();
  const navigate = useNavigate();
  const [form] = Form.useForm();

  const [systemsData, setSystemsData] = useState({});
  const [modifications, setModifications] = useState([]);
  const [confirmed, setConfirmed] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [currentSystem, setCurrentSystem] = useState('');
  const [historyVisible, setHistoryVisible] = useState(false);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [editingFeature, setEditingFeature] = useState(null);
  const [editingIndex, setEditingIndex] = useState(null);

  // 加载评估结果
  useEffect(() => {
    fetchEvaluationResult();
  }, [taskId]);

  const fetchEvaluationResult = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`/api/v1/requirement/result/${taskId}`);
      const { systems_data, modifications, confirmed } = response.data.data;

      setSystemsData(systems_data);
      setModifications(modifications || []);
      setConfirmed(confirmed);

      // 设置默认选中第一个系统
      const systemNames = Object.keys(systems_data);
      if (systemNames.length > 0) {
        setCurrentSystem(systemNames[0]);
      }
    } catch (error) {
      console.error('获取评估结果失败:', error);
      message.error(error.response?.data?.detail || '获取评估结果失败');
      navigate('/tasks');
    } finally {
      setLoading(false);
    }
  };

  // 打开编辑Modal
  const handleEdit = (feature, index) => {
    setEditingFeature({ ...feature });
    setEditingIndex(index);
    form.setFieldsValue(feature);
    setEditModalVisible(true);
  };

  // 保存编辑
  const handleEditSave = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);

      // 找出变化的字段
      const changes = {};
      Object.keys(values).forEach(key => {
        if (values[key] !== editingFeature[key]) {
          changes[key] = values[key];
        }
      });

      if (Object.keys(changes).length === 0) {
        message.info('没有修改');
        setEditModalVisible(false);
        return;
      }

      // 保存每个变化
      for (const [field, newValue] of Object.entries(changes)) {
        await axios.put(`/api/v1/requirement/features/${taskId}`, {
          system: currentSystem,
          operation: 'update',
          feature_index: editingIndex,
          feature_data: { [field]: newValue }
        });
      }

      // 更新本地状态
      const updatedFeatures = [...systemsData[currentSystem]];
      updatedFeatures[editingIndex] = { ...updatedFeatures[editingIndex], ...values };
      setSystemsData({ ...systemsData, [currentSystem]: updatedFeatures });

      // 刷新修改记录
      const response = await axios.get(`/api/v1/requirement/modifications/${taskId}`);
      setModifications(response.data.data.modifications);

      message.success('保存成功');
      setEditModalVisible(false);
    } catch (error) {
      console.error('保存失败:', error);
      if (error.errorFields) {
        message.error('请检查输入');
      } else {
        message.error('保存失败: ' + (error.response?.data?.detail || error.message));
      }
    } finally {
      setSaving(false);
    }
  };

  // 删除功能点
  const handleDelete = async (index) => {
    try {
      setSaving(true);
      await axios.put(`/api/v1/requirement/features/${taskId}`, {
        system: currentSystem,
        operation: 'delete',
        feature_index: index
      });

      // 更新本地状态
      const updatedFeatures = systemsData[currentSystem].filter((_, idx) => idx !== index);
      setSystemsData({ ...systemsData, [currentSystem]: updatedFeatures });

      // 刷新修改记录
      const response = await axios.get(`/api/v1/requirement/modifications/${taskId}`);
      setModifications(response.data.data.modifications);

      message.success('删除成功');
    } catch (error) {
      console.error('删除失败:', error);
      message.error('删除失败: ' + (error.response?.data?.detail || error.message));
    } finally {
      setSaving(false);
    }
  };

  // 添加新功能点
  const handleAdd = () => {
    setEditingFeature({
      序号: '',
      功能模块: '',
      功能点: '',
      业务描述: '',
      预估人天: 1,
      复杂度: '中'
    });
    setEditingIndex(null);
    form.resetFields();
    form.setFieldsValue({
      预估人天: 1,
      复杂度: '中'
    });
    setEditModalVisible(true);
  };

  // 保存新功能点
  const handleAddSave = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);

      const maxIndex = systemsData[currentSystem].length;
      const newFeature = {
        ...values,
        序号: `1.${maxIndex + 1}`,
        预估人天: parseFloat(values.预估人天) || 1
      };

      await axios.put(`/api/v1/requirement/features/${taskId}`, {
        system: currentSystem,
        operation: 'add',
        feature_data: newFeature
      });

      // 更新本地状态
      const updatedFeatures = [...systemsData[currentSystem], newFeature];
      setSystemsData({ ...systemsData, [currentSystem]: updatedFeatures });

      // 刷新修改记录
      const response = await axios.get(`/api/v1/requirement/modifications/${taskId}`);
      setModifications(response.data.data.modifications);

      message.success('添加成功');
      setEditModalVisible(false);
    } catch (error) {
      console.error('添加失败:', error);
      if (error.errorFields) {
        message.error('请检查输入');
      } else {
        message.error('添加失败: ' + (error.response?.data?.detail || error.message));
      }
    } finally {
      setSaving(false);
    }
  };

  // 保存功能点到知识库
  const handleSaveToLibrary = async (feature) => {
    try {
      setSaving(true);

      await axios.post('/api/v1/knowledge/save_case', {
        system_name: currentSystem,
        module: feature['功能模块'],
        feature_name: feature['功能点'],
        description: feature['业务描述'],
        estimated_days: feature['预估人天'],
        complexity: feature['复杂度'],
        tech_points: '',  // 可以从表单获取
        dependencies: '',  // 可以从表单获取
        project_case: `任务${taskId.substring(0, 8)}`,  // 使用任务ID作为案例来源
        source: '人工修正'
      });

      message.success('已保存到知识库，AI后续将参考此案例');
    } catch (error) {
      console.error('保存到知识库失败:', error);
      message.error('保存失败: ' + (error.response?.data?.detail || error.message));
    } finally {
      setSaving(false);
    }
  };

  // 确认完成
  const handleConfirm = async () => {
    try {
      setLoading(true);
      const response = await axios.post(`/api/v1/requirement/confirm/${taskId}`);

      message.success('确认成功，最终报告已生成');
      setConfirmed(true);

      Modal.success({
        title: '报告生成成功',
        content: `最终报告已生成，请前往任务列表下载`,
        okText: '前往下载',
        onOk: () => navigate('/tasks')
      });
    } catch (error) {
      console.error('确认失败:', error);
      message.error('确认失败: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  // 表格列配置
  const columns = [
    {
      title: '序号',
      dataIndex: '序号',
      key: '序号',
      width: 80,
    },
    {
      title: '功能模块',
      dataIndex: '功能模块',
      key: '功能模块',
      width: 150,
      ellipsis: true,
    },
    {
      title: '功能点',
      dataIndex: '功能点',
      key: '功能点',
      width: 200,
      ellipsis: true,
    },
    {
      title: '业务描述',
      dataIndex: '业务描述',
      key: '业务描述',
      width: 300,
      ellipsis: true,
      render: (text) => (
        <Tooltip title={text}>
          <Text ellipsis>{text}</Text>
        </Tooltip>
      ),
    },
    {
      title: '预估人天',
      dataIndex: '预估人天',
      key: '预估人天',
      width: 100,
      render: (value) => <Text strong>{value}</Text>,
    },
    {
      title: '复杂度',
      dataIndex: '复杂度',
      key: '复杂度',
      width: 100,
      render: (value) => {
        const colorMap = { '高': 'red', '中': 'orange', '低': 'green' };
        return <Tag color={colorMap[value] || 'default'}>{value}</Tag>;
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 280,
      fixed: 'right',
      render: (_, record, index) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record, index)}
            disabled={confirmed}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定要删除这个功能点吗？"
            onConfirm={() => handleDelete(index)}
            okText="确定"
            cancelText="取消"
          >
            <Button
              type="link"
              size="small"
              danger
              icon={<DeleteOutlined />}
              disabled={confirmed}
            >
              删除
            </Button>
          </Popconfirm>
          <Popconfirm
            title="确定要将此功能点存入知识库吗？存入后AI会参考此案例进行后续评估"
            onConfirm={() => handleSaveToLibrary(record)}
            okText="确定"
            cancelText="取消"
          >
            <Button
              type="link"
              size="small"
              style={{ color: '#52c41a' }}
              disabled={saving}
            >
              存入知识库
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  // 计算统计数据
  const calculateStats = () => {
    let totalFeatures = 0;
    let totalDays = 0;
    let complexityCount = { 高: 0, 中: 0, 低: 0 };

    Object.values(systemsData).forEach(features => {
      totalFeatures += features.length;
      features.forEach(f => {
        totalDays += f['预估人天'] || 0;
        const complexity = f['复杂度'];
        if (complexityCount.hasOwnProperty(complexity)) {
          complexityCount[complexity]++;
        }
      });
    });

    return { totalFeatures, totalDays, complexityCount };
  };

  const stats = calculateStats();

  if (loading) {
    return <Card loading={true}>加载中...</Card>;
  }

  return (
    <Card>
      {/* 顶部操作栏 */}
      <div style={{ marginBottom: 16 }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/tasks')}>
            返回列表
          </Button>
          <Title level={4} style={{ margin: 0 }}>
            在线编辑评估结果
          </Title>
          <Tag color={confirmed ? 'success' : 'processing'}>
            {confirmed ? '已确认' : '编辑中'}
          </Tag>
        </Space>
      </div>

      {/* 统计信息 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Statistic title="功能点总数" value={stats.totalFeatures} />
        </Col>
        <Col span={6}>
          <Statistic title="总工作量（人天）" value={stats.totalDays.toFixed(1)} />
        </Col>
        <Col span={4}>
          <Statistic
            title="高复杂度"
            value={stats.complexityCount.高}
            valueStyle={{ color: '#cf1322' }}
          />
        </Col>
        <Col span={4}>
          <Statistic
            title="中复杂度"
            value={stats.complexityCount.中}
            valueStyle={{ color: '#fa8c16' }}
          />
        </Col>
        <Col span={4}>
          <Statistic
            title="低复杂度"
            value={stats.complexityCount.低}
            valueStyle={{ color: '#52c41a' }}
          />
        </Col>
      </Row>

      {/* 操作按钮 */}
      <div style={{ marginBottom: 16 }}>
        <Space>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleAdd}
            disabled={confirmed || saving}
          >
            添加功能点
          </Button>
          <Button
            icon={<HistoryOutlined />}
            onClick={() => setHistoryVisible(true)}
          >
            查看修改历史 ({modifications.length})
          </Button>
          {!confirmed && (
            <Popconfirm
              title="确认后将生成最终报告，确认后无法继续编辑"
              onConfirm={handleConfirm}
              okText="确认完成"
              cancelText="取消"
            >
              <Button
                type="primary"
                icon={<CheckOutlined />}
                loading={loading}
                disabled={saving}
              >
                确认完成
              </Button>
            </Popconfirm>
          )}
        </Space>
      </div>

      {/* 系统Tab页 */}
      <Tabs
        activeKey={currentSystem}
        onChange={setCurrentSystem}
        items={Object.keys(systemsData).map(system => ({
          label: `${system} (${systemsData[system].length})`,
          key: system,
          children: (
            <Table
              columns={columns}
              dataSource={systemsData[system]}
              rowKey={(record, index) => index}
              pagination={false}
              scroll={{ x: 1200 }}
            />
          ),
        }))}
      />

      {/* 编辑/添加Modal */}
      <Modal
        title={editingIndex === null ? '添加新功能点' : '编辑功能点'}
        open={editModalVisible}
        onCancel={() => setEditModalVisible(false)}
        onOk={editingIndex === null ? handleAddSave : handleEditSave}
        confirmLoading={saving}
        width={600}
        okText="保存"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="功能模块"
                name="功能模块"
                rules={[{ required: true, message: '请输入功能模块' }]}
              >
                <Input placeholder="例如：账户管理" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="功能点"
                name="功能点"
                rules={[{ required: true, message: '请输入功能点' }]}
              >
                <Input placeholder="例如：开立个人账户" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item
            label="业务描述"
            name="业务描述"
            rules={[{ required: true, message: '请输入业务描述' }]}
          >
            <TextArea rows={4} placeholder="详细描述该功能点的业务需求..." />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="预估人天"
                name="预估人天"
                rules={[
                  { required: true, message: '请输入预估人天' },
                  { type: 'number', min: 0.5, max: 50, message: '人天范围: 0.5-50' }
                ]}
              >
                <Input type="number" step="0.5" placeholder="建议范围: 0.5-5" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="复杂度"
                name="复杂度"
                rules={[{ required: true, message: '请选择复杂度' }]}
              >
                <Select placeholder="选择复杂度">
                  <Option value="低">低</Option>
                  <Option value="中">中</Option>
                  <Option value="高">高</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>

      {/* 修改历史Modal */}
      <Modal
        title="修改历史"
        open={historyVisible}
        onCancel={() => setHistoryVisible(false)}
        footer={[
          <Button key="close" onClick={() => setHistoryVisible(false)}>
            关闭
          </Button>
        ]}
        width={900}
      >
        <Table
          columns={[
            {
              title: '时间',
              dataIndex: 'timestamp',
              key: 'timestamp',
              width: 180,
            },
            {
              title: '操作',
              dataIndex: 'operation',
              key: 'operation',
              width: 80,
              render: (op) => {
                const opMap = { add: '添加', update: '修改', delete: '删除' };
                const colorMap = { add: 'green', update: 'blue', delete: 'red' };
                return <Tag color={colorMap[op]}>{opMap[op]}</Tag>;
              },
            },
            {
              title: '系统',
              dataIndex: 'system',
              key: 'system',
              width: 150,
              ellipsis: true,
            },
            {
              title: '字段',
              dataIndex: 'field',
              key: 'field',
              width: 100,
              render: (field) => field || '-',
            },
            {
              title: '旧值',
              dataIndex: 'old_value',
              key: 'old_value',
              width: 150,
              ellipsis: true,
              render: (val) => val !== undefined ? String(val) : '-',
            },
            {
              title: '新值',
              dataIndex: 'new_value',
              key: 'new_value',
              width: 150,
              ellipsis: true,
              render: (val) => val !== undefined ? String(val) : '-',
            },
          ]}
          dataSource={modifications}
          rowKey="id"
          pagination={{ pageSize: 10 }}
          scroll={{ x: 900 }}
        />
      </Modal>
    </Card>
  );
};

export default EditPage;
