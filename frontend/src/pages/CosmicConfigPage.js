import React, { useState, useEffect, useCallback } from 'react';
import {
  Alert,
  Button,
  Card,
  Divider,
  Dropdown,
  Form,
  InputNumber,
  Modal,
  Row,
  Col,
  Select,
  Space,
  Switch,
  Tabs,
  Tag,
  Typography,
  message,
} from 'antd';
import {
  SaveOutlined,
  UndoOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import axios from 'axios';
import usePermission from '../hooks/usePermission';

const { Title, Text, Paragraph } = Typography;
const { TabPane } = Tabs;

const CosmicConfigPage = () => {
  const { isAdmin } = usePermission();
  const readOnly = !isAdmin;
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [config, setConfig] = useState(null);
  const [helpOpen, setHelpOpen] = useState(false);

  // 快速设置预设配置
  const presetConfigs = {
    fine: {
      'functional_process_rules.granularity': 'fine',
      'functional_process_rules.min_data_movements': 1,
      'functional_process_rules.max_data_movements': 10,
      'data_group_rules.min_attributes': 1,
      'data_group_rules.min_data_groups': 1,
    },
    medium: {
      'functional_process_rules.granularity': 'medium',
      'functional_process_rules.min_data_movements': 2,
      'functional_process_rules.max_data_movements': 7,
      'data_group_rules.min_attributes': 2,
      'data_group_rules.min_data_groups': 2,
    },
    coarse: {
      'functional_process_rules.granularity': 'coarse',
      'functional_process_rules.min_data_movements': 4,
      'functional_process_rules.max_data_movements': 20,
      'data_group_rules.min_attributes': 3,
      'data_group_rules.min_data_groups': 1,
    },
  };

  const applyPreset = (preset) => {
    const values = presetConfigs[preset];
    if (values) {
      form.setFieldsValue(values);
      message.success(`已应用${preset === 'fine' ? '细' : preset === 'medium' ? '中等' : '粗'}粒度预设配置`);
    }
  };

  const fetchConfig = useCallback(async () => {
    setLoading(true);
    try {
      const response = await axios.get('/api/v1/cosmic/config');
      setConfig(response.data.data);
      form.setFieldsValue(response.data.data);
    } catch (error) {
      message.error('获取配置失败');
    } finally {
      setLoading(false);
    }
  }, [form]);

  useEffect(() => {
    fetchConfig();
  }, [fetchConfig]);

  const handleSave = async () => {
    if (readOnly) {
      message.warning('只读模式：无权限保存配置');
      return;
    }

    try {
      const values = await form.validateFields();
      setSaving(true);
      await axios.post('/api/v1/cosmic/config', values);
      message.success('配置保存成功');
      fetchConfig();
    } catch (error) {
      if (error?.errorFields) {
        return;
      }
      message.error(`保存配置失败: ${error.response?.data?.detail || error.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    if (readOnly) {
      message.warning('只读模式：无权限重置配置');
      return;
    }

    try {
      await axios.post('/api/v1/cosmic/reset');
      message.success('配置已重置为默认值');
      fetchConfig();
    } catch (error) {
      message.error('重置配置失败');
    }
  };

  return (
    <div style={{ padding: 24 }}>
      <Card loading={loading}>
        <Space direction="vertical" style={{ width: '100%' }} size={16}>
          {readOnly && (
            <Alert
              type="warning"
              showIcon
              message="只读模式"
              description="仅管理员可修改COSMIC技术配置。"
            />
          )}

          <Form
            form={form}
            layout="vertical"
            initialValues={config || {}}
            disabled={readOnly}
          >
            <Tabs
              defaultActiveKey="1"
              tabBarExtraContent={{
                right: (
                  <Space size={8}>
                    <Button onClick={() => setHelpOpen(true)}>使用说明</Button>
                    {isAdmin && (
                      <Dropdown
                        menu={{
                          items: [
                            {
                              key: 'fine',
                              label: '细粒度（每个按钮/操作=1个功能点）',
                              onClick: () => applyPreset('fine'),
                            },
                            {
                              key: 'medium',
                              label: '中等粒度（完整交易流程=1个功能点）',
                              onClick: () => applyPreset('medium'),
                            },
                            {
                              key: 'coarse',
                              label: '粗粒度（业务模块=1个功能点）',
                              onClick: () => applyPreset('coarse'),
                            },
                          ],
                        }}
                        trigger={['click']}
                      >
                        <Button icon={<ThunderboltOutlined />}>
                          快速设置
                        </Button>
                      </Dropdown>
                    )}
                  </Space>
                ),
              }}
            >
              <TabPane tab="数据组规则" key="1">
                <Row gutter={16}>
                  <Col xs={24} md={12} lg={8}>
                    <Form.Item label="启用数据组规则" name={['data_group_rules', 'enabled']} valuePropName="checked">
                      <Switch />
                    </Form.Item>
                  </Col>
                  <Col xs={24} md={12} lg={8}>
                    <Form.Item
                      label="最小属性数量"
                      name={['data_group_rules', 'min_attributes']}
                      tooltip="一个数据组至少包含的属性数量"
                    >
                      <InputNumber min={1} max={10} style={{ width: '100%' }} />
                    </Form.Item>
                  </Col>
                  <Col xs={24} md={12} lg={8}>
                    <Form.Item
                      label="最小数据组数量"
                      name={['data_group_rules', 'min_data_groups']}
                      tooltip="一个功能处理至少涉及的数据组数量"
                    >
                      <InputNumber min={1} max={10} style={{ width: '100%' }} />
                    </Form.Item>
                  </Col>
                </Row>
              </TabPane>

              <TabPane tab="功能处理规则" key="2">
                <Row gutter={16}>
                  <Col xs={24} md={12} lg={8}>
                    <Form.Item label="启用功能处理规则" name={['functional_process_rules', 'enabled']} valuePropName="checked">
                      <Switch />
                    </Form.Item>
                  </Col>
                  <Col xs={24} md={12} lg={8}>
                    <Form.Item
                      label="拆分粒度"
                      name={['functional_process_rules', 'granularity']}
                      tooltip="功能处理的拆分细度"
                    >
                      <Select style={{ width: '100%' }}>
                        <Select.Option value="fine">细粒度 (fine)</Select.Option>
                        <Select.Option value="medium">中等粒度 (medium)</Select.Option>
                        <Select.Option value="coarse">粗粒度 (coarse)</Select.Option>
                      </Select>
                    </Form.Item>
                  </Col>
                  <Col xs={24} md={12} lg={8}>
                    <Form.Item
                      label="最小数据移动数量"
                      name={['functional_process_rules', 'min_data_movements']}
                      tooltip="一个功能处理至少包含的数据移动数量"
                    >
                      <InputNumber min={1} max={10} style={{ width: '100%' }} />
                    </Form.Item>
                  </Col>
                  <Col xs={24} md={12} lg={8}>
                    <Form.Item
                      label="最大数据移动数量"
                      name={['functional_process_rules', 'max_data_movements']}
                      tooltip="一个功能处理最多包含的数据移动数量"
                    >
                      <InputNumber min={10} max={100} style={{ width: '100%' }} />
                    </Form.Item>
                  </Col>
                </Row>
              </TabPane>

              <TabPane tab="数据移动规则" key="3">
                <DataMovementRuleSection
                  form={form}
                  movementType="entry"
                  title="入口数据移动 (Entry)"
                  description="数据从用户进入功能处理"
                />
                <DataMovementRuleSection
                  form={form}
                  movementType="exit"
                  title="出口数据移动 (Exit)"
                  description="数据从功能处理返回给用户"
                />
                <DataMovementRuleSection
                  form={form}
                  movementType="read"
                  title="读数据移动 (Read)"
                  description="从持久存储读取数据"
                />
                <DataMovementRuleSection
                  form={form}
                  movementType="write"
                  title="写数据移动 (Write)"
                  description="数据写入持久存储"
                />
              </TabPane>

              <TabPane tab="计数规则" key="4">
                <Row gutter={16}>
                  <Col xs={24} md={12} lg={8}>
                    <Form.Item
                      label="CFF计算方法"
                      name={['counting_rules', 'cff_calculation_method']}
                      tooltip="COSMIC功能点数的计算方法"
                    >
                      <Select style={{ width: '100%' }}>
                        <Select.Option value="sum">直接求和</Select.Option>
                        <Select.Option value="weighted">加权计算</Select.Option>
                      </Select>
                    </Form.Item>
                  </Col>
                  <Col xs={24} md={12} lg={8}>
                    <Form.Item
                      label="包含触发操作"
                      name={['counting_rules', 'include_triggering_operations']}
                      valuePropName="checked"
                    >
                      <Switch />
                    </Form.Item>
                  </Col>
                  <Col xs={24} md={12} lg={8}>
                    <Form.Item
                      label="计数唯一数据组"
                      name={['counting_rules', 'count_unique_data_groups']}
                      valuePropName="checked"
                    >
                      <Switch />
                    </Form.Item>
                  </Col>
                </Row>
              </TabPane>

              <TabPane tab="验证规则" key="5">
                <Row gutter={16}>
                  <Col xs={24} md={12} lg={8}>
                    <Form.Item
                      label="最小CFF值"
                      name={['validation_rules', 'min_cff_per_feature']}
                    >
                      <InputNumber min={1} max={10} style={{ width: '100%' }} />
                    </Form.Item>
                  </Col>
                  <Col xs={24} md={12} lg={8}>
                    <Form.Item
                      label="最大CFF值"
                      name={['validation_rules', 'max_cff_per_feature']}
                    >
                      <InputNumber min={10} max={200} style={{ width: '100%' }} />
                    </Form.Item>
                  </Col>
                  <Col xs={24} md={12} lg={8}>
                    <Form.Item
                      label="验证数据组一致性"
                      name={['validation_rules', 'validate_data_group_consistency']}
                      valuePropName="checked"
                    >
                      <Switch />
                    </Form.Item>
                  </Col>
                </Row>
              </TabPane>
            </Tabs>
          </Form>


          {isAdmin && (
            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <Space>
                <Button icon={<UndoOutlined />} onClick={handleReset}>
                  重置为默认
                </Button>
                <Button type="primary" icon={<SaveOutlined />} loading={saving} onClick={handleSave}>
                  保存配置
                </Button>
              </Space>
            </div>
          )}

          <Modal
            title="使用说明（COSMIC）"
            open={helpOpen}
            onCancel={() => setHelpOpen(false)}
            footer={(
              <Button type="primary" onClick={() => setHelpOpen(false)}>
                我知道了
              </Button>
            )}
          >
            <Space direction="vertical" size={12} style={{ width: '100%' }}>
              <Paragraph style={{ marginBottom: 0 }}>
                COSMIC 通过统计<strong>入口/出口/读/写</strong>四类数据移动估算功能规模。前端展示仅做理解简化，后台算法保持不变。
              </Paragraph>

              <div>
                <Text strong>拆分示例（细/中/粗）</Text>
                <Space direction="vertical" size={8} style={{ marginTop: 8 }}>
                  <Text><Tag color="blue">细粒度</Tag>每个按钮/操作可拆分为单独功能点。</Text>
                  <Text><Tag color="gold">中等粒度</Tag>一个完整交易流程（输入+校验+处理+返回）作为一个功能点。</Text>
                  <Text><Tag color="purple">粗粒度</Tag>一个业务模块作为一个功能点，适合高层级粗估。</Text>
                </Space>
              </div>
            </Space>
          </Modal>
        </Space>
      </Card>
    </div>
  );
};

const DataMovementRuleSection = ({ form, movementType, title, description }) => {
  const keywords = Form.useWatch(['data_movement_rules', movementType, 'keywords'], form);

  return (
    <div style={{ marginBottom: 24 }}>
      <Title level={5}>{title}</Title>
      <Paragraph type="secondary" style={{ marginTop: -8, marginBottom: 16 }}>
        {description}
      </Paragraph>

      <Row gutter={16}>
        <Col xs={24} md={12} lg={8}>
          <Form.Item label="启用" name={['data_movement_rules', movementType, 'enabled']} valuePropName="checked">
            <Switch />
          </Form.Item>
        </Col>
        <Col xs={24} md={12} lg={8}>
          <Form.Item
            label="权重"
            name={['data_movement_rules', movementType, 'weight']}
            tooltip="该类型数据移动在计算CFF时的权重"
          >
            <InputNumber min={0.1} max={10} step={0.1} style={{ width: '100%' }} />
          </Form.Item>
        </Col>
        <Col xs={24}>
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
        </Col>
      </Row>

      {Array.isArray(keywords) && keywords.length > 0 && (
        <div style={{ marginTop: 8 }}>
          <Text type="secondary">当前关键词：</Text>
          <div style={{ marginTop: 8 }}>
            {keywords.map((keyword, index) => (
              <Tag key={`${movementType}_${index}`} color="blue">{keyword}</Tag>
            ))}
          </div>
        </div>
      )}

      <Divider />
    </div>
  );
};

export default CosmicConfigPage;
