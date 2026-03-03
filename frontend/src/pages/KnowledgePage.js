import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Col,
  Divider,
  Input,
  message,
  Row,
  Select,
  Space,
  Spin,
  Statistic,
  Table,
  Tag,
  Typography,
  Upload,
} from 'antd';
import {
  CloudUploadOutlined,
  DatabaseOutlined,
  DownloadOutlined,
  InboxOutlined,
  ReloadOutlined,
  SearchOutlined,
} from '@ant-design/icons';
import axios from 'axios';
import usePermission from '../hooks/usePermission';

const { Title, Text, Paragraph } = Typography;

const renderMetadataValue = (value, path = 'metadata') => {
  if (value === null || value === undefined) {
    return <Text type="secondary">-</Text>;
  }

  if (Array.isArray(value)) {
    if (value.length === 0) {
      return <Text type="secondary">-</Text>;
    }
    const allPrimitive = value.every((item) => (
      item === null || item === undefined || ['string', 'number', 'boolean'].includes(typeof item)
    ));
    if (allPrimitive) {
      return <Text>{value.map((item) => String(item)).join('、')}</Text>;
    }
    return (
      <Space direction="vertical" size={4} style={{ width: '100%' }}>
        {value.map((item, index) => (
          <Card key={`${path}-${index}`} size="small" styles={{ body: { padding: 8 } }}>
            {renderMetadataValue(item, `${path}-${index}`)}
          </Card>
        ))}
      </Space>
    );
  }

  if (typeof value === 'object') {
    const entries = Object.entries(value);
    if (!entries.length) {
      return <Text type="secondary">-</Text>;
    }
    return (
      <Space direction="vertical" size={6} style={{ width: '100%' }}>
        {entries.map(([key, itemValue]) => (
          <div key={`${path}-${key}`}>
            <Text strong>{key}</Text>
            <div style={{ marginTop: 4, paddingLeft: 10 }}>
              {renderMetadataValue(itemValue, `${path}-${key}`)}
            </div>
          </div>
        ))}
      </Space>
    );
  }

  return <Text>{String(value)}</Text>;
};

const KnowledgePage = () => {
  const { isAdmin, isManager } = usePermission();
  const canUpload = isManager;

  const [mainSystems, setMainSystems] = useState([]);
  const [selectedSystem, setSelectedSystem] = useState('');

  const [uploading, setUploading] = useState(false);
  const [searching, setSearching] = useState(false);
  const [stats, setStats] = useState(null);
  const [evaluationMetrics, setEvaluationMetrics] = useState(null);
  const [searchResults, setSearchResults] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');

  const fetchSystems = async () => {
    try {
      const response = await axios.get('/api/v1/system/systems');
      const systems = response.data?.data?.systems || [];
      setMainSystems(systems);
      if (!selectedSystem && systems.length) {
        setSelectedSystem(systems[0].name);
      }
    } catch (error) {
      message.error('获取主系统列表失败: ' + (error.response?.data?.detail || error.message));
    }
  };

  const fetchStats = async (systemName) => {
    const normalized = (systemName || '').trim();
    if (!normalized) {
      setStats(null);
      return;
    }
    try {
      const response = await axios.get('/api/v1/knowledge/stats', { params: { system_name: normalized } });
      if (response.data.code === 200) {
        setStats(response.data.data);
      }
    } catch (error) {
      message.error('获取统计信息失败: ' + (error.response?.data?.detail || error.message));
    }
  };

  const fetchEvaluationMetrics = async () => {
    try {
      const response = await axios.get('/api/v1/knowledge/evaluation-metrics');
      if (response.data.code === 200) {
        setEvaluationMetrics(response.data.data);
      }
    } catch (error) {
      console.error('获取评估指标失败:', error);
    }
  };

  useEffect(() => {
    fetchSystems();
    fetchEvaluationMetrics();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (selectedSystem) {
      fetchStats(selectedSystem);
    }
  }, [selectedSystem]);

  const downloadTemplate = (type) => {
    const templates = {
      system_profile_docx: '/templates/system_profile_template.docx',
      system_profile_pptx: '/templates/system_profile_template.pptx',
    };
    const url = templates[type];
    if (!url) {
      message.error('模板文件不存在');
      return;
    }
    window.open(url, '_blank');
    message.success('模板下载已开始');
  };

  const uploadProps = useMemo(() => {
    return {
      name: 'file',
      disabled: !canUpload || !selectedSystem,
      action: '/api/v1/knowledge/imports',
      accept: '.docx,.pptx',
      data: {
        knowledge_type: 'system_profile',
        level: 'normal',
        system_name: selectedSystem,
      },
      showUploadList: false,
      beforeUpload: (file) => {
        if (!canUpload) {
          message.warning('仅项目经理可导入系统知识');
          return Upload.LIST_IGNORE;
        }
        if (!selectedSystem) {
          message.warning('请先选择主系统');
          return Upload.LIST_IGNORE;
        }

        const name = (file?.name || '').toLowerCase();
        const isValidType = name.endsWith('.docx') || name.endsWith('.pptx');
        if (!isValidType) {
          message.error('系统知识仅支持 DOCX / PPTX');
          return Upload.LIST_IGNORE;
        }

        const isLt50M = file.size / 1024 / 1024 < 50;
        if (!isLt50M) {
          message.error('文件大小不能超过 50MB');
          return Upload.LIST_IGNORE;
        }
        return true;
      },
      onChange: async (info) => {
        if (info.file.status === 'uploading') {
          setUploading(true);
        }
        if (info.file.status === 'done') {
          setUploading(false);
          const response = info.file.response;
          if (response && response.code === 200) {
            const data = response.data;
            message.success(`导入完成！成功 ${data.success} 条，失败 ${data.failed} 条`);
            if (data.errors && data.errors.length > 0) {
              console.error('导入错误:', data.errors);
              message.warning(`${data.failed} 条记录导入失败，请查看控制台`);
            }
            fetchStats(selectedSystem);
          } else {
            message.error('导入失败: ' + (response?.message || '未知错误'));
          }
        } else if (info.file.status === 'error') {
          setUploading(false);
          message.error(info.file?.error?.message || '上传失败');
        }
      },
    };
  }, [canUpload, selectedSystem]);

  const handleSearch = async () => {
    if (!selectedSystem) {
      message.warning('请先选择主系统');
      return;
    }
    if (!searchQuery.trim()) {
      message.warning('请输入查询内容');
      return;
    }

    setSearching(true);
    try {
      const response = await axios.post('/api/v1/knowledge/search', {
        query: searchQuery,
        system_name: selectedSystem,
        top_k: 10,
        similarity_threshold: 0.6,
      });

      if (response.data.code === 200) {
        setSearchResults(response.data.data.results);
        message.success(`检索到 ${response.data.data.total} 条相关知识`);
      }
    } catch (error) {
      message.error('检索失败: ' + (error.response?.data?.detail || error.message));
    } finally {
      setSearching(false);
    }
  };

  const handleRebuildIndex = async () => {
    try {
      message.loading({ content: '正在重建索引...', key: 'rebuild' });
      const response = await axios.post('/api/v1/knowledge/rebuild-index');
      if (response.data.code === 200) {
        message.success({ content: '索引重建完成', key: 'rebuild', duration: 2 });
      } else {
        message.error({ content: '索引重建失败', key: 'rebuild' });
      }
    } catch (error) {
      message.error({ content: '重建索引失败: ' + (error.response?.data?.detail || error.message), key: 'rebuild' });
    }
  };

  const columns = [
    {
      title: '主系统',
      dataIndex: 'system_name',
      key: 'system_name',
      width: 160,
    },
    {
      title: '知识类型',
      dataIndex: 'knowledge_type',
      key: 'knowledge_type',
      width: 140,
      render: () => <Tag color="blue">系统知识</Tag>,
    },
    {
      title: '内容',
      dataIndex: 'content',
      key: 'content',
      ellipsis: true,
      render: (content) => (
        <Text ellipsis={{ tooltip: content }}>
          {content}
        </Text>
      ),
    },
    {
      title: '相似度',
      dataIndex: 'similarity',
      key: 'similarity',
      width: 110,
      render: (similarity) => {
        const percent = (Number(similarity || 0) * 100).toFixed(1);
        let color = 'default';
        if (similarity >= 0.8) color = 'success';
        else if (similarity >= 0.6) color = 'processing';
        else color = 'warning';
        return <Tag color={color}>{percent}%</Tag>;
      },
    },
    {
      title: '来源文件',
      dataIndex: 'source_file',
      key: 'source_file',
      width: 220,
      ellipsis: true,
      render: (file) => file || '-',
    },
  ];

  return (
    <div style={{ padding: '24px', maxWidth: '1400px', margin: '0 auto' }}>
      <Title level={2}>知识库管理</Title>
      <Paragraph type="secondary">
        按“主系统”维度维护系统知识库：导入架构/介绍材料，供需求评估检索参考。
      </Paragraph>

      <Card style={{ marginBottom: 24 }}>
        <Space wrap>
          <Text strong>主系统：</Text>
          <Select
            style={{ width: 320 }}
            placeholder="请选择主系统"
            value={selectedSystem || undefined}
            onChange={setSelectedSystem}
            showSearch
            optionFilterProp="label"
            options={(mainSystems || []).map((item) => ({
              label: `${item.name}${item.abbreviation ? ` (${item.abbreviation})` : ''}`,
              value: item.name,
            }))}
          />
          <Button icon={<ReloadOutlined />} onClick={fetchSystems}>
            刷新主系统
          </Button>
        </Space>
      </Card>

      {/* 统计信息 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="当前系统知识总数"
              value={stats?.count || 0}
              suffix="条"
              prefix={<DatabaseOutlined style={{ fontSize: '16px' }} />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="系统知识"
              value={stats?.system_profile_count ?? stats?.count ?? 0}
              suffix="条"
              prefix={<DatabaseOutlined style={{ fontSize: '16px' }} />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="检索命中率"
              value={evaluationMetrics?.hit_rate || 0}
              suffix="%"
              prefix={<SearchOutlined style={{ fontSize: '16px' }} />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="平均相似度"
              value={evaluationMetrics?.avg_similarity || 0}
              suffix="%"
              precision={1}
              prefix={<SearchOutlined style={{ fontSize: '16px' }} />}
            />
          </Card>
        </Col>
      </Row>

      {/* 导入（仅项目经理） */}
      {isManager ? (
        <Card
          title={(
            <Space>
              <CloudUploadOutlined />
              <span>导入系统知识（DOCX / PPTX）</span>
            </Space>
          )}
          style={{ marginBottom: 24 }}
        >
          <Alert
            message="导入说明"
            description="每个主系统维护一套知识库。请先选择主系统，再导入该系统的架构说明/系统介绍材料（推荐使用模板）。"
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />

          <Space style={{ marginBottom: 16 }} wrap>
            <Button icon={<DownloadOutlined />} onClick={() => downloadTemplate('system_profile_docx')}>
              下载 DOCX 模板
            </Button>
            <Button icon={<DownloadOutlined />} onClick={() => downloadTemplate('system_profile_pptx')}>
              下载 PPTX 模板
            </Button>
            {!selectedSystem && <Text type="secondary">请选择主系统后再上传</Text>}
          </Space>

          <Upload.Dragger {...uploadProps} style={{ marginBottom: 16 }}>
            <p className="ant-upload-drag-icon">
              <InboxOutlined />
            </p>
            <p className="ant-upload-text">点击或拖拽系统知识文件到此区域上传</p>
            <p className="ant-upload-hint">支持：系统架构说明书、系统介绍材料（DOCX、PPTX）</p>
          </Upload.Dragger>

          {uploading && (
            <div style={{ textAlign: 'center' }}>
              <Spin tip="正在处理文件，智能提取系统知识..." />
            </div>
          )}
        </Card>
      ) : null}

      {/* 知识检索 */}
      <Card
        title={(
          <Space>
            <SearchOutlined />
            <span>知识检索（当前主系统）</span>
          </Space>
        )}
        extra={isAdmin ? (
          <Button icon={<ReloadOutlined />} onClick={handleRebuildIndex} size="small">
            重建索引
          </Button>
        ) : null}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <Input.Search
            placeholder="输入查询内容，例如：系统边界、核心功能、技术栈、性能指标..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onSearch={handleSearch}
            loading={searching}
            size="large"
            allowClear
            enterButton="搜索"
            disabled={!selectedSystem}
          />

          {searching && (
            <div style={{ textAlign: 'center', padding: '40px' }}>
              <Spin tip="正在检索知识库..." />
            </div>
          )}

          {!searching && searchResults.length > 0 && (
            <Table
              columns={columns}
              dataSource={searchResults}
              rowKey={(record, index) => `${record.system_name}-${index}`}
              pagination={{ pageSize: 10 }}
              expandable={{
                expandedRowRender: (record) => (
                  <div style={{ padding: '16px' }}>
                    <Paragraph>
                      <Text strong>完整内容：</Text>
                    </Paragraph>
                    <Paragraph>{record.content}</Paragraph>
                    {record.metadata && Object.keys(record.metadata).length > 0 && (
                      <>
                        <Divider />
                        <Text strong>元数据：</Text>
                        <div style={{ marginTop: 8, padding: 12, background: '#f5f5f5', borderRadius: 4 }}>
                          {renderMetadataValue(record.metadata)}
                        </div>
                      </>
                    )}
                  </div>
                ),
                rowExpandable: (record) => record.content && record.content.length > 100,
              }}
            />
          )}

          {!searching && searchQuery && searchResults.length === 0 && (
            <div style={{ textAlign: 'center', padding: '40px', color: '#999' }}>
              未找到相关知识，请尝试其他查询条件
            </div>
          )}
        </Space>
      </Card>
    </div>
  );
};

export default KnowledgePage;
