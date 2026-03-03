import React, { useEffect, useMemo, useState } from 'react';
import {
  Button,
  Card,
  Col,
  Input,
  message,
  Row,
  Select,
  Space,
  Spin,
  Statistic,
  Switch,
  Table,
  Tag,
  Typography,
  Upload,
} from 'antd';
import { CloudUploadOutlined, DatabaseOutlined, SearchOutlined } from '@ant-design/icons';
import axios from 'axios';

const { Title, Text, Paragraph } = Typography;

const EsbPage = () => {
  const [mainSystems, setMainSystems] = useState([]);
  const [selectedSystem, setSelectedSystem] = useState('');
  const [selectedSystemId, setSelectedSystemId] = useState('');
  const [uploading, setUploading] = useState(false);
  const [searching, setSearching] = useState(false);
  const [stats, setStats] = useState(null);
  const [results, setResults] = useState([]);
  const [query, setQuery] = useState('');
  const [scope, setScope] = useState('both');
  const [includeDeprecated, setIncludeDeprecated] = useState(false);

  const fetchSystems = async () => {
    try {
      const response = await axios.get('/api/v1/system/systems');
      const systems = response.data?.data?.systems || [];
      setMainSystems(systems);
      if (!selectedSystem && systems.length) {
        setSelectedSystem(systems[0].name);
        setSelectedSystemId(systems[0].id || '');
      }
    } catch (error) {
      message.error('获取主系统列表失败: ' + (error.response?.data?.detail || error.message));
    }
  };

  const fetchStats = async (systemName, systemId) => {
    const normalized = (systemName || '').trim();
    if (!normalized && !systemId) {
      setStats(null);
      return;
    }
    try {
      const response = await axios.get('/api/v1/knowledge/esb/stats', {
        params: { system_name: normalized || undefined, system_id: systemId || undefined },
      });
      if (response.data.code === 200) {
        setStats(response.data.data);
      }
    } catch (error) {
      message.error('获取ESB统计失败: ' + (error.response?.data?.detail || error.message));
    }
  };

  useEffect(() => {
    fetchSystems();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const matched = (mainSystems || []).find((item) => item.name === selectedSystem);
    setSelectedSystemId(matched?.id || '');
    if (selectedSystem || selectedSystemId) {
      fetchStats(selectedSystem, matched?.id || '');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedSystem, mainSystems]);

  const uploadProps = useMemo(() => ({
    name: 'file',
    action: '/api/v1/esb/imports',
    accept: '.csv,.xlsx',
    showUploadList: false,
    beforeUpload: (file) => {
      const name = (file?.name || '').toLowerCase();
      if (!name.endsWith('.csv') && !name.endsWith('.xlsx')) {
        message.error('仅支持CSV/XLSX');
        return Upload.LIST_IGNORE;
      }
      return true;
    },
    onChange: (info) => {
      if (info.file.status === 'uploading') {
        setUploading(true);
      }
      if (info.file.status === 'done') {
        setUploading(false);
        const response = info.file.response;
        if (response && response.code === 200) {
          const data = response.data || {};
          message.success(`导入完成：成功 ${data.imported || 0} 条，失败 ${data.skipped || 0} 条`);
          fetchStats(selectedSystem, selectedSystemId);
        } else {
          message.error('导入失败: ' + (response?.message || '未知错误'));
        }
      } else if (info.file.status === 'error') {
        setUploading(false);
        message.error(info.file?.error?.message || '上传失败');
      }
    },
  }), [selectedSystem, selectedSystemId]);

  const handleSearch = async () => {
    if (!query.trim()) {
      message.warning('请输入检索内容');
      return;
    }
    setSearching(true);
    try {
      const response = await axios.post('/api/v1/knowledge/esb/search', {
        query,
        system_name: selectedSystem || undefined,
        system_id: selectedSystemId || undefined,
        scope,
        include_deprecated: includeDeprecated,
        top_k: 10,
        similarity_threshold: 0.55,
      });
      if (response.data.code === 200) {
        setResults(response.data.data.results || []);
        message.success(`检索到 ${response.data.data.total || 0} 条`);
      }
    } catch (error) {
      message.error('检索失败: ' + (error.response?.data?.detail || error.message));
    } finally {
      setSearching(false);
    }
  };

  const columns = [
    {
      title: '交易名称',
      dataIndex: 'service_name',
      key: 'service_name',
      width: 220,
      render: (value) => value || '-',
    },
    {
      title: '提供方',
      dataIndex: 'provider_system_name',
      key: 'provider_system_name',
      width: 160,
      render: (value, record) => value || record.provider_system_id || '-',
    },
    {
      title: '调用方',
      dataIndex: 'consumer_system_name',
      key: 'consumer_system_name',
      width: 160,
      render: (value, record) => value || record.consumer_system_id || '-',
    },
    {
      title: '交易码',
      dataIndex: 'service_code',
      key: 'service_code',
      width: 140,
    },
    {
      title: '场景码',
      dataIndex: 'scenario_code',
      key: 'scenario_code',
      width: 140,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (value) => (
        <Tag color={value === '正常使用' ? 'green' : 'orange'}>{value || '-'}</Tag>
      ),
    },
    {
      title: '相似度',
      dataIndex: 'similarity',
      key: 'similarity',
      width: 100,
      render: (value) => `${(Number(value || 0) * 100).toFixed(1)}%`,
    },
  ];

  return (
    <div style={{ padding: 24, maxWidth: 1400, margin: '0 auto' }}>
      <Title level={2}>ESB索引</Title>
      <Paragraph type="secondary">
        导入ESB服务清单并进行检索，用于集成点提示与澄清问题候选。
      </Paragraph>

      <Card style={{ marginBottom: 24 }}>
        <Space wrap>
          <Text strong>主系统：</Text>
          <Select
            style={{ width: 320 }}
            placeholder="请选择主系统"
            value={selectedSystem || undefined}
            onChange={(value) => setSelectedSystem(value)}
            showSearch
            optionFilterProp="label"
            options={(mainSystems || []).map((item) => ({
              label: `${item.name}${item.abbreviation ? ` (${item.abbreviation})` : ''}`,
              value: item.name,
            }))}
          />
          <Upload {...uploadProps}>
            <Button icon={<CloudUploadOutlined />} loading={uploading}>
              导入ESB清单
            </Button>
          </Upload>
        </Space>
      </Card>

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="有效条目数"
              value={stats?.active_entry_count || 0}
              prefix={<DatabaseOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="废弃条目数"
              value={stats?.deprecated_entry_count || 0}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="有效交易去重数"
              value={stats?.active_unique_service_count || 0}
            />
          </Card>
        </Col>
      </Row>

      <Card style={{ marginBottom: 16 }}>
        <Space wrap>
          <Input
            style={{ width: 320 }}
            placeholder="请输入交易/场景/系统关键词"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <Select
            style={{ width: 160 }}
            value={scope}
            onChange={setScope}
            options={[
              { label: '提供方+调用方', value: 'both' },
              { label: '仅提供方', value: 'provider' },
              { label: '仅调用方', value: 'consumer' },
            ]}
          />
          <Space>
            <Text>包含废弃</Text>
            <Switch checked={includeDeprecated} onChange={setIncludeDeprecated} />
          </Space>
          <Button type="primary" icon={<SearchOutlined />} loading={searching} onClick={handleSearch}>
            检索
          </Button>
        </Space>
      </Card>

      <Card>
        <Table
          rowKey={(record, idx) => `${record.service_code || record.service_name}_${idx}`}
          columns={columns}
          dataSource={results}
          loading={searching ? { spinning: true, indicator: <Spin /> } : false}
          pagination={{ pageSize: 10 }}
        />
      </Card>
    </div>
  );
};

export default EsbPage;

