import React, { useState } from 'react';
import {
  Card, Upload, Button, Input, Table, Tag, message, Spin, Statistic,
  Row, Col, Space, Typography, Divider, Tabs, Alert, Collapse, Progress,
  Descriptions
} from 'antd';
import {
  InboxOutlined, SearchOutlined, CloudUploadOutlined, ReloadOutlined,
  DownloadOutlined, DatabaseOutlined, FundOutlined, FileTextOutlined
} from '@ant-design/icons';
import axios from 'axios';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;
const { TabPane } = Tabs;
const { Panel } = Collapse;

const KnowledgePage = () => {
  const [uploading, setUploading] = useState({});
  const [searching, setSearching] = useState(false);
  const [stats, setStats] = useState(null);
  const [evaluationMetrics, setEvaluationMetrics] = useState(null);
  const [searchResults, setSearchResults] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [systemFilter, setSystemFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('');

  // 获取知识库统计信息
  const fetchStats = async () => {
    try {
      const response = await axios.get('/api/v1/knowledge/stats');
      if (response.data.code === 200) {
        setStats(response.data.data);
      }
    } catch (error) {
      message.error('获取统计信息失败: ' + error.message);
    }
  };

  // 获取效果评估指标
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

  // 页面加载时获取统计信息
  React.useEffect(() => {
    fetchStats();
    fetchEvaluationMetrics();
  }, []);

  // 文件上传配置（分类导入）
  const createUploadProps = (knowledgeType) => ({
    name: 'file',
    action: '/api/v1/knowledge/import',
    accept: knowledgeType === 'system_profile'
      ? '.csv,.docx,.pptx,.pdf'
      : '.csv,.docx,.xlsx,.pdf',
    data: {
      auto_extract: true,
      knowledge_type: knowledgeType
    },
    showUploadList: false,
    beforeUpload: (file) => {
      const isValidType = knowledgeType === 'system_profile'
        ? ['.csv', '.docx', '.pptx', '.pdf'].some(ext => file.name.toLowerCase().endsWith(ext))
        : ['.csv', '.docx', '.xlsx', '.pdf'].some(ext => file.name.toLowerCase().endsWith(ext));

      if (!isValidType) {
        message.error(`系统知识支持 CSV、DOCX、PPTX、PDF 格式`);
        message.error(`功能案例支持 CSV、DOCX、XLSX、PDF 格式`);
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
      const typeKey = knowledgeType;
      if (info.file.status === 'uploading') {
        setUploading({ ...uploading, [typeKey]: true });
      }
      if (info.file.status === 'done') {
        setUploading({ ...uploading, [typeKey]: false });
        const response = info.file.response;
        if (response && response.code === 200) {
          const data = response.data;
          message.success(
            `导入完成！成功 ${data.success} 条，失败 ${data.failed} 条`
          );

          // 显示详细结果
          if (data.errors && data.errors.length > 0) {
            console.error('导入错误:', data.errors);
            message.warning(`${data.failed} 条记录导入失败，请查看控制台`);
          }

          // 刷新统计信息
          fetchStats();
        } else {
          message.error('导入失败: ' + (response?.message || '未知错误'));
        }
      } else if (info.file.status === 'error') {
        setUploading({ ...uploading, [typeKey]: false });
        message.error('上传失败');
      }
    },
  });

  // 知识检索
  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      message.warning('请输入查询内容');
      return;
    }

    setSearching(true);
    try {
      const response = await axios.post('/api/v1/knowledge/search', {
        query: searchQuery,
        system_name: systemFilter || undefined,
        knowledge_type: typeFilter || undefined,
        top_k: 10,
        similarity_threshold: 0.6
      });

      if (response.data.code === 200) {
        setSearchResults(response.data.data.results);
        message.success(`检索到 ${response.data.data.total} 条相关知识`);
      }
    } catch (error) {
      message.error('检索失败: ' + error.message);
    } finally {
      setSearching(false);
    }
  };

  // 重建索引
  const handleRebuildIndex = async () => {
    try {
      message.loading({ content: '正在重建索引...', key: 'rebuild' });
      const response = await axios.post('/api/v1/knowledge/rebuild-index');
      if (response.data.code === 200) {
        message.success({ content: '索引重建完成', key: 'rebuild', duration: 2 });
      }
    } catch (error) {
      message.error({ content: '重建索引失败: ' + error.message, key: 'rebuild' });
    }
  };

  // 搜索结果表格列
  const columns = [
    {
      title: '系统名称',
      dataIndex: 'system_name',
      key: 'system_name',
      width: 150,
    },
    {
      title: '知识类型',
      dataIndex: 'knowledge_type',
      key: 'knowledge_type',
      width: 120,
      render: (type) => {
        const colorMap = {
          'system_profile': 'blue',
          'feature_case': 'green',
          'tech_spec': 'orange'
        };
        const textMap = {
          'system_profile': '系统简介',
          'feature_case': '功能案例',
          'tech_spec': '技术规格'
        };
        return <Tag color={colorMap[type] || 'default'}>{textMap[type] || type}</Tag>;
      }
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
      )
    },
    {
      title: '相似度',
      dataIndex: 'similarity',
      key: 'similarity',
      width: 100,
      render: (similarity) => {
        const percent = (similarity * 100).toFixed(1);
        let color = 'default';
        if (similarity >= 0.8) color = 'success';
        else if (similarity >= 0.6) color = 'processing';
        else color = 'warning';
        return <Tag color={color}>{percent}%</Tag>;
      }
    },
    {
      title: '来源文件',
      dataIndex: 'source_file',
      key: 'source_file',
      width: 200,
      ellipsis: true,
      render: (file) => file || '-'
    }
  ];

  // 下载模板
  const downloadTemplate = (type) => {
    const templates = {
      system_profile_csv: '/templates/system_profile_template.csv',
      system_profile_docx: '/templates/system_profile_template.docx',
      feature_case_csv: '/templates/feature_case_template.csv',
      feature_case_docx: '/templates/feature_case_template.docx',
    };

    const url = templates[type];
    if (url) {
      window.open(url, '_blank');
      message.success('模板下载已开始');
    } else {
      message.error('模板文件不存在');
    }
  };

  return (
    <div style={{ padding: '24px', maxWidth: '1400px', margin: '0 auto' }}>
      <Title level={2}>知识库管理</Title>
      <Paragraph type="secondary">
        导入系统知识库文档，为需求评估提供参考案例和历史数据支持
      </Paragraph>

      {/* 统计信息 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="知识总数"
              value={stats?.count || 0}
              suffix="条"
              prefix={<DatabaseOutlined style={{ fontSize: '16px' }} />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="系统简介"
              value={stats?.system_profile_count || 0}
              suffix="条"
              prefix={<FundOutlined style={{ fontSize: '16px' }} />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="功能案例"
              value={stats?.feature_case_count || 0}
              suffix="条"
              prefix={<FileTextOutlined style={{ fontSize: '16px' }} />}
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
      </Row>

      {/* 效果评估指标 */}
      {evaluationMetrics && (
        <Card
          title="知识库效果评估"
          style={{ marginBottom: 24 }}
          extra={
            <Button
              icon={<ReloadOutlined />}
              onClick={fetchEvaluationMetrics}
              size="small"
            >
              刷新
            </Button>
          }
        >
          <Row gutter={[16, 16]}>
            <Col span={8}>
              <Statistic
                title="检索命中率"
                value={evaluationMetrics.hit_rate || 0}
                suffix="%"
                valueStyle={{ color: (evaluationMetrics.hit_rate || 0) > 60 ? '#3f8600' : '#cf1322' }}
              />
              <Text type="secondary">评估任务中成功检索到知识的比例</Text>
            </Col>
            <Col span={8}>
              <Statistic
                title="平均相似度"
                value={evaluationMetrics.avg_similarity || 0}
                suffix="%"
                precision={1}
              />
              <Text type="secondary">检索结果的平均相似度</Text>
            </Col>
            <Col span={8}>
              <Statistic
                title="案例采纳率"
                value={evaluationMetrics.adoption_rate || 0}
                suffix="%"
              />
              <Text type="secondary">AI建议被用户采纳的比例</Text>
            </Col>
          </Row>

          {evaluationMetrics.quality_comparison && (
            <>
              <Divider />
              <Title level={5}>评估质量对比</Title>
              <Row gutter={[16, 16]}>
                <Col span={12}>
                  <Card size="small">
                    <Statistic
                      title="使用知识库"
                      value={evaluationMetrics.quality_comparison?.with_kb || 0}
                      suffix="%"
                      precision={1}
                      valueStyle={{ color: '#3f8600' }}
                    />
                    <Text type="secondary">平均准确度（专家评分）</Text>
                  </Card>
                </Col>
                <Col span={12}>
                  <Card size="small">
                    <Statistic
                      title="未使用知识库"
                      value={evaluationMetrics.quality_comparison?.without_kb || 0}
                      suffix="%"
                      precision={1}
                      valueStyle={{ color: '#cf1322' }}
                    />
                    <Text type="secondary">平均准确度（专家评分）</Text>
                  </Card>
                </Col>
              </Row>
            </>
          )}
        </Card>
      )}

      {/* 分类导入 */}
      <Card
        title={
          <Space>
            <CloudUploadOutlined />
            <span>导入知识库文件（按分类）</span>
          </Space>
        }
        style={{ marginBottom: 24 }}
      >
        <Tabs defaultActiveKey="system_profile">
          {/* 系统知识导入 */}
          <TabPane tab="系统知识 (system_profile)" key="system_profile">
            <Alert
              message="系统知识用途"
              description="提供系统架构、技术栈、业务目标等上下文信息，帮助 AI 更准确地识别需求涉及哪些系统，理解系统边界和关系。"
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />

            <Collapse style={{ marginBottom: 16 }}>
              <Panel header="📋 字段说明与示例" key="fields">
                <Descriptions bordered size="small" column={1}>
                  <Descriptions.Item label="系统名称">标准系统名称（需与 system_list.md 一致）</Descriptions.Item>
                  <Descriptions.Item label="系统简称">英文简称或缩写（如：CBS、Payment）</Descriptions.Item>
                  <Descriptions.Item label="系统分类">核心系统/中台系统/渠道系统/管理系统等</Descriptions.Item>
                  <Descriptions.Item label="业务目标">1-2 句话描述系统的核心业务价值</Descriptions.Item>
                  <Descriptions.Item label="核心功能">枚举主要功能模块（用顿号分隔）</Descriptions.Item>
                  <Descriptions.Item label="技术栈">主要技术栈（如：Java Spring Cloud、Vue.js、MySQL）</Descriptions.Item>
                  <Descriptions.Item label="架构特点">微服务/单体/分布式、集群模式等</Descriptions.Item>
                  <Descriptions.Item label="性能指标">TPS、QPS、响应时间等关键指标</Descriptions.Item>
                  <Descriptions.Item label="主要用户">系统的使用者（如：柜员、客户经理）</Descriptions.Item>
                </Descriptions>

                <Divider orientation="left">CSV 示例</Divider>
                <pre style={{
                  background: '#f5f5f5',
                  padding: 12,
                  borderRadius: 4,
                  fontSize: 12
                }}>
{`系统名称,系统简称,系统分类,业务目标,核心功能,技术栈,架构特点,性能指标,主要用户,备注
新一代核心,CBS,核心系统,全行核心账务处理,账户管理、交易核算、日终批处理,Java Spring Cloud,微服务架构,TPS 5000+,柜员、客户经理,
支付中台,Payment,中台系统,统一支付渠道接入,微信支付、支付宝、银联整合,Node.js + Redis,分布式集群,TPS 10000+,各业务系统,`}
                </pre>
              </Panel>
            </Collapse>

            <Space style={{ marginBottom: 16 }}>
              <Button
                icon={<DownloadOutlined />}
                onClick={() => downloadTemplate('system_profile_csv')}
              >
                下载 CSV 模板
              </Button>
              <Button
                icon={<DownloadOutlined />}
                onClick={() => downloadTemplate('system_profile_docx')}
              >
                下载 DOCX 模板
              </Button>
              <Text type="secondary">支持格式：CSV、DOCX、PPTX、PDF</Text>
            </Space>

            <Upload.Dragger
              {...createUploadProps('system_profile')}
              style={{ marginBottom: 16 }}
            >
              <p className="ant-upload-drag-icon">
                <InboxOutlined />
              </p>
              <p className="ant-upload-text">点击或拖拽系统知识文件到此区域上传</p>
              <p className="ant-upload-hint">
                支持系统架构说明书、系统功能清单等文档（CSV、DOCX、PPTX、PDF）
              </p>
            </Upload.Dragger>

            {uploading['system_profile'] && (
              <div style={{ textAlign: 'center' }}>
                <Spin tip="正在处理文件，智能提取系统知识..." />
              </div>
            )}
          </TabPane>

          {/* 功能案例导入 */}
          <TabPane tab="功能案例 (feature_case)" key="feature_case">
            <Alert
              message="功能案例用途"
              description="提供历史功能点拆分案例和工作量参考，帮助 AI 学习合适的拆分粒度和复杂度评估标准。"
              type="success"
              showIcon
              style={{ marginBottom: 16 }}
            />

            <Collapse style={{ marginBottom: 16 }}>
              <Panel header="📋 字段说明与示例" key="fields">
                <Descriptions bordered size="small" column={1}>
                  <Descriptions.Item label="系统名称">标准系统名称（需与 system_list.md 一致）</Descriptions.Item>
                  <Descriptions.Item label="功能模块">功能所属的模块（如：用户管理、支付模块）</Descriptions.Item>
                  <Descriptions.Item label="功能点">功能点的简要名称（2-8个字）</Descriptions.Item>
                  <Descriptions.Item label="业务描述">详细描述功能点的业务需求和实现内容</Descriptions.Item>
                  <Descriptions.Item label="预估人天">工作量（人天），建议范围：0.5-5</Descriptions.Item>
                  <Descriptions.Item label="复杂度">高/中/低，根据技术难度和业务复杂度判断</Descriptions.Item>
                  <Descriptions.Item label="技术要点">关键技术、难点或特殊要求（可选）</Descriptions.Item>
                  <Descriptions.Item label="依赖系统">需要对接的其他系统（可选）</Descriptions.Item>
                  <Descriptions.Item label="实施案例">参考的实际项目名称（可选）</Descriptions.Item>
                </Descriptions>

                <Divider orientation="left">CSV 示例</Divider>
                <pre style={{
                  background: '#f5f5f5',
                  padding: 12,
                  borderRadius: 4,
                  fontSize: 12
                }}>
{`系统名称,功能模块,功能点,业务描述,预估人天,复杂度,技术要点,依赖系统,实施案例,创建日期
支付中台,微信支付,微信支付接入,对接微信支付API，实现扫码支付、JSAPI支付、H5支付，处理异步通知和签名验签,3,中,需要对接微信支付API、处理异步通知、签名验签,核心系统,某银行微信支付项目,2024-01-15
新一代核心,账户管理,账户开户功能,实现个人账户、对公账户开户流程，包括风险评估、反洗钱核查、核心交易,5,高,涉及核心交易、人行报送、反洗钱系统,客户信息系统、反洗钱系统,某行核心改造项目,2024-01-20`}
                </pre>
              </Panel>
            </Collapse>

            <Space style={{ marginBottom: 16 }}>
              <Button
                icon={<DownloadOutlined />}
                onClick={() => downloadTemplate('feature_case_csv')}
              >
                下载 CSV 模板
              </Button>
              <Button
                icon={<DownloadOutlined />}
                onClick={() => downloadTemplate('feature_case_docx')}
              >
                下载 DOCX 模板
              </Button>
              <Text type="secondary">支持格式：CSV、DOCX、XLSX、PDF</Text>
            </Space>

            <Upload.Dragger
              {...createUploadProps('feature_case')}
              style={{ marginBottom: 16 }}
            >
              <p className="ant-upload-drag-icon">
                <InboxOutlined />
              </p>
              <p className="ant-upload-text">点击或拖拽功能案例文件到此区域上传</p>
              <p className="ant-upload-hint">
                支持历史评估报告、功能点案例库等文档（CSV、DOCX、XLSX、PDF）
              </p>
            </Upload.Dragger>

            {uploading['feature_case'] && (
              <div style={{ textAlign: 'center' }}>
                <Spin tip="正在处理文件，智能提取功能案例..." />
              </div>
            )}
          </TabPane>

          {/* 技术规范导入（占位） */}
          <TabPane tab="技术规范 (tech_spec)" key="tech_spec">
            <Alert
              message="技术规范"
              description="技术规范类型暂不支持自动导入，将在后续版本中实现。"
              type="warning"
              showIcon
            />
          </TabPane>
        </Tabs>
      </Card>

      {/* 知识检索 */}
      <Card
        title={
          <Space>
            <SearchOutlined />
            <span>知识检索</span>
          </Space>
        }
        extra={
          <Button
            icon={<ReloadOutlined />}
            onClick={handleRebuildIndex}
            size="small"
          >
            重建索引
          </Button>
        }
      >
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <Space.Compact style={{ width: '100%' }}>
            <Input
              placeholder="输入查询内容，例如：用户管理、订单系统、支付功能..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onPressEnter={handleSearch}
              size="large"
              allowClear
            />
            <Input
              placeholder="系统名称（可选）"
              value={systemFilter}
              onChange={(e) => setSystemFilter(e.target.value)}
              style={{ width: 200 }}
              allowClear
            />
            <Input
              placeholder="知识类型（可选）"
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              style={{ width: 200 }}
              allowClear
            />
            <Button
              type="primary"
              icon={<SearchOutlined />}
              onClick={handleSearch}
              loading={searching}
              size="large"
            >
              搜索
            </Button>
          </Space.Compact>

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
                        <pre style={{ marginTop: 8, padding: 12, background: '#f5f5f5', borderRadius: 4 }}>
                          {JSON.stringify(record.metadata, null, 2)}
                        </pre>
                      </>
                    )}
                  </div>
                ),
                rowExpandable: (record) => record.content && record.content.length > 100
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
