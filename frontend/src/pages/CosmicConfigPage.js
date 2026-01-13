import React, { useState, useEffect } from 'react';
import {
  Card,
  Form,
  InputNumber,
  Switch,
  Button,
  Space,
  message,
  Typography,
  Divider,
  Row,
  Col,
  Tag,
  Select,
  Tabs,
  Alert
} from 'antd';
import {
  SaveOutlined,
  ReloadOutlined,
  UndoOutlined,
  CheckCircleOutlined
} from '@ant-design/icons';
import axios from 'axios';

const { Title, Text, Paragraph } = Typography;
const { TabPane } = Tabs;

const CosmicConfigPage = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [config, setConfig] = useState(null);

  // 加载配置
  const fetchConfig = async () => {
    setLoading(true);
    try {
      const response = await axios.get('/api/v1/cosmic/config');
      setConfig(response.data.data);
      form.setFieldsValue(response.data.data);
    } catch (error) {
      console.error('获取COSMIC配置失败:', error);
      message.error('获取配置失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConfig();
  }, []);

  // 保存配置
  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);

      await axios.post('/api/v1/cosmic/config', values);
      message.success('配置保存成功');
      fetchConfig();
    } catch (error) {
      console.error('保存配置失败:', error);
      message.error('保存配置失败: ' + (error.response?.data?.detail || error.message));
    } finally {
      setSaving(false);
    }
  };

  // 重置配置
  const handleReset = async () => {
    try {
      await axios.post('/api/v1/cosmic/reset');
      message.success('配置已重置为默认值');
      fetchConfig();
    } catch (error) {
      console.error('重置配置失败:', error);
      message.error('重置配置失败');
    }
  };

  // 重新加载配置
  const handleReload = async () => {
    try {
      await axios.post('/api/v1/cosmic/reload');
      message.success('配置重新加载成功');
    } catch (error) {
      console.error('重新加载配置失败:', error);
      message.error('重新加载配置失败');
    }
  };

  return (
    <div style={{ padding: '24px' }}>
      <Card>
        <div style={{ marginBottom: 16 }}>
          <Title level={3}>COSMIC功能点规则配置</Title>
          <Text type="secondary">
            配置COSMIC方法的功能点分析规则，包括数据组定义、功能处理拆分粒度、数据移动判定规则等
          </Text>
        </div>

        <Alert
          message="关于COSMIC方法"
          description="COSMIC（Common Software Measurement International Consortium）是一种国际标准的软件功能规模度量方法。它基于数据移动概念，通过统计入口(E)、出口(X)、读(R)、写(W)四种数据移动来计算功能点数(CFF)。"
          type="info"
          showIcon
          style={{ marginBottom: 24 }}
        />

        <Space style={{ marginBottom: 24 }}>
          <Button
            type="primary"
            icon={<SaveOutlined />}
            onClick={handleSave}
            loading={saving}
          >
            保存配置
          </Button>
          <Button
            icon={<UndoOutlined />}
            onClick={handleReset}
          >
            重置为默认
          </Button>
          <Button
            icon={<ReloadOutlined />}
            onClick={fetchConfig}
            loading={loading}
          >
            刷新
          </Button>
          <Button
            icon={<CheckCircleOutlined />}
            onClick={handleReload}
          >
            重新加载（热更新）
          </Button>
        </Space>

        <Form
          form={form}
          layout="vertical"
          initialValues={config}
        >
          <Tabs defaultActiveKey="1">
            <TabPane tab="数据组规则" key="1">
              <Form.Item
                label="启用数据组规则"
                name={['data_group_rules', 'enabled']}
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>

              <Form.Item
                label="最小属性数量"
                name={['data_group_rules', 'min_attributes']}
                tooltip="一个数据组至少包含的属性数量"
              >
                <InputNumber min={1} max={10} style={{ width: 200 }} />
              </Form.Item>

              <Form.Item
                label="最小数据组数量"
                name={['data_group_rules', 'min_data_groups']}
                tooltip="一个功能处理至少涉及的数据组数量"
              >
                <InputNumber min={1} max={10} style={{ width: 200 }} />
              </Form.Item>
            </TabPane>

            <TabPane tab="功能处理规则" key="2">
              <Form.Item
                label="启用功能处理规则"
                name={['functional_process_rules', 'enabled']}
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>

              <Form.Item
                label="拆分粒度"
                name={['functional_process_rules', 'granularity']}
                tooltip="功能处理的拆分细度"
              >
                <Select style={{ width: 200 }}>
                  <Select.Option value="fine">细粒度 (fine)</Select.Option>
                  <Select.Option value="medium">中等粒度 (medium)</Select.Option>
                  <Select.Option value="coarse">粗粒度 (coarse)</Select.Option>
                </Select>
              </Form.Item>

              <Form.Item
                label="最小数据移动数量"
                name={['functional_process_rules', 'min_data_movements']}
                tooltip="一个功能处理至少包含的数据移动数量"
              >
                <InputNumber min={1} max={10} style={{ width: 200 }} />
              </Form.Item>

              <Form.Item
                label="最大数据移动数量"
                name={['functional_process_rules', 'max_data_movements']}
                tooltip="一个功能处理最多包含的数据移动数量"
              >
                <InputNumber min={10} max={100} style={{ width: 200 }} />
              </Form.Item>
            </TabPane>

            <TabPane tab="数据移动规则" key="3">
              <DataMovementRuleSection form={form} movementType="entry" title="入口数据移动 (Entry)"
                description="数据从用户进入功能处理" />
              <DataMovementRuleSection form={form} movementType="exit" title="出口数据移动 (Exit)"
                description="数据从功能处理返回给用户" />
              <DataMovementRuleSection form={form} movementType="read" title="读数据移动 (Read)"
                description="从持久存储读取数据" />
              <DataMovementRuleSection form={form} movementType="write" title="写数据移动 (Write)"
                description="数据写入持久存储" />
            </TabPane>

            <TabPane tab="计数规则" key="4">
              <Form.Item
                label="CFF计算方法"
                name={['counting_rules', 'cff_calculation_method']}
                tooltip="COSMIC功能点数的计算方法"
              >
                <Select style={{ width: 200 }}>
                  <Select.Option value="sum">直接求和</Select.Option>
                  <Select.Option value="weighted">加权计算</Select.Option>
                </Select>
              </Form.Item>

              <Form.Item
                label="包含触发操作"
                name={['counting_rules', 'include_triggering_operations']}
                valuePropName="checked"
                tooltip="是否将触发操作计入数据移动"
              >
                <Switch />
              </Form.Item>

              <Form.Item
                label="计数唯一数据组"
                name={['counting_rules', 'count_unique_data_groups']}
                valuePropName="checked"
                tooltip="是否只计数唯一的数据组"
              >
                <Switch />
              </Form.Item>
            </TabPane>

            <TabPane tab="验证规则" key="5">
              <Form.Item
                label="最小CFF值"
                name={['validation_rules', 'min_cff_per_feature']}
                tooltip="每个功能点的最小CFF值"
              >
                <InputNumber min={1} max={10} style={{ width: 200 }} />
              </Form.Item>

              <Form.Item
                label="最大CFF值"
                name={['validation_rules', 'max_cff_per_feature']}
                tooltip="每个功能点的最大CFF值"
              >
                <InputNumber min={10} max={200} style={{ width: 200 }} />
              </Form.Item>

              <Form.Item
                label="验证数据组一致性"
                name={['validation_rules', 'validate_data_group_consistency']}
                valuePropName="checked"
                tooltip="是否验证数据组使用的一致性"
              >
                <Switch />
              </Form.Item>
            </TabPane>
          </Tabs>
        </Form>
      </Card>
    </div>
  );
};

// 数据移动规则子组件
const DataMovementRuleSection = ({ form, movementType, title, description }) => {
  const keywords = Form.useWatch(['data_movement_rules', movementType, 'keywords'], form);

  return (
    <div style={{ marginBottom: 24 }}>
      <Title level={5}>{title}</Title>
      <Paragraph type="secondary" style={{ marginTop: -8, marginBottom: 16 }}>
        {description}
      </Paragraph>

      <Form.Item
        label="启用"
        name={['data_movement_rules', movementType, 'enabled']}
        valuePropName="checked"
      >
        <Switch />
      </Form.Item>

      <Form.Item
        label="权重"
        name={['data_movement_rules', movementType, 'weight']}
        tooltip="该类型数据移动在计算CFF时的权重"
      >
        <InputNumber min={0.1} max={10} step={0.1} style={{ width: 200 }} />
      </Form.Item>

      <Form.Item
        label="判定关键词"
        name={['data_movement_rules', movementType, 'keywords']}
        tooltip="用于识别该类型数据移动的关键词列表"
      >
        <Select
          mode="tags"
          style={{ width: '100%' }}
          placeholder="输入关键词后按回车添加"
          tokenSeparators={[' ', ',']}
        />
      </Form.Item>

      {keywords && keywords.length > 0 && (
        <div style={{ marginTop: 8 }}>
          <Text type="secondary">当前关键词：</Text>
          <div style={{ marginTop: 8 }}>
            {keywords.map((keyword, index) => (
              <Tag key={index} color="blue">{keyword}</Tag>
            ))}
          </div>
        </div>
      )}

      <Divider />
    </div>
  );
};

export default CosmicConfigPage;
