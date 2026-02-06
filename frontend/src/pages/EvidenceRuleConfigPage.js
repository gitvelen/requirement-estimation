import React, { useEffect, useState } from 'react';
import { Button, Card, Input, message, Space, Table, Typography } from 'antd';
import axios from 'axios';

const { Title, Paragraph, Text } = Typography;
const { TextArea } = Input;

const EvidenceRuleConfigPage = () => {
  const [rulesJson, setRulesJson] = useState('');
  const [loading, setLoading] = useState(false);
  const [logs, setLogs] = useState([]);

  const fetchRules = async () => {
    try {
      setLoading(true);
      const response = await axios.get('/api/v1/evidence-level/rules');
      if (response.data.code === 200) {
        setRulesJson(JSON.stringify(response.data.data, null, 2));
      }
    } catch (error) {
      message.error(error.response?.data?.detail || '获取规则失败');
    } finally {
      setLoading(false);
    }
  };

  const fetchLogs = async () => {
    try {
      const response = await axios.get('/api/v1/evidence-level/rules/logs');
      if (response.data.code === 200) {
        setLogs(response.data.data || []);
      }
    } catch (error) {
      message.error(error.response?.data?.detail || '获取变更日志失败');
    }
  };

  useEffect(() => {
    fetchRules();
    fetchLogs();
  }, []);

  const handleSave = async () => {
    try {
      const parsed = JSON.parse(rulesJson || '{}');
      const response = await axios.put('/api/v1/evidence-level/rules', { rules: parsed });
      if (response.data.code === 200) {
        message.success('规则已更新');
        fetchLogs();
      }
    } catch (error) {
      if (error instanceof SyntaxError) {
        message.error('规则JSON格式错误');
      } else {
        message.error(error.response?.data?.detail || '保存失败');
      }
    }
  };

  const columns = [
    { title: '时间', dataIndex: 'created_at', key: 'created_at', width: 180 },
    { title: '操作者', dataIndex: 'actor_name', key: 'actor_name', width: 120 },
    {
      title: '摘要',
      dataIndex: 'detail',
      key: 'detail',
      render: (detail) => <Text>{detail?.rules?.version ? `version=${detail.rules.version}` : '-'}</Text>,
    },
  ];

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: '0 auto' }}>
      <Title level={2}>证据等级规则配置</Title>
      <Paragraph type="secondary">
        仅管理员可修改证据等级判定规则，变更将记录日志。
      </Paragraph>

      <Card style={{ marginBottom: 16 }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Text strong>规则JSON</Text>
          <TextArea
            rows={12}
            value={rulesJson}
            onChange={(e) => setRulesJson(e.target.value)}
            placeholder="请输入规则JSON"
          />
          <Space>
            <Button type="primary" onClick={handleSave} loading={loading}>
              保存规则
            </Button>
            <Button onClick={fetchRules}>重载规则</Button>
          </Space>
        </Space>
      </Card>

      <Card title="变更日志">
        <Table rowKey="id" columns={columns} dataSource={logs} pagination={{ pageSize: 6 }} />
      </Card>
    </div>
  );
};

export default EvidenceRuleConfigPage;

