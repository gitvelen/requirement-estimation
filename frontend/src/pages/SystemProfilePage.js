import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Col,
  Form,
  Input,
  message,
  Row,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  Upload,
} from 'antd';
import {
  InboxOutlined,
  PlayCircleOutlined,
  SaveOutlined,
  SendOutlined,
  ReloadOutlined,
  CloudUploadOutlined,
} from '@ant-design/icons';
import axios from 'axios';
import PageHeader from '../components/PageHeader';
import usePermission from '../hooks/usePermission';
import useAuth from '../hooks/useAuth';
import { formatDateTime } from '../utils/time';
import './SystemProfilePage.css';

const { TextArea } = Input;
const { Title, Text } = Typography;

const fieldLabels = {
  in_scope: '系统边界（做什么）',
  out_of_scope: '系统不做什么',
  core_functions: '核心功能',
  business_goal: '业务目标',
  business_objects: '业务对象',
  integration_points: '主要集成点',
  key_constraints: '关键约束',
};

const ESB_MAPPING_FIELDS = [
  { key: 'provider_system_id', label: '提供方系统列名', placeholder: '例如：提供方系统简称,提供方系统ID' },
  { key: 'consumer_system_id', label: '调用方系统列名', placeholder: '例如：调用方系统简称,调用方系统ID' },
  { key: 'service_name', label: '服务名称列名', placeholder: '例如：交易名称,服务名称' },
  { key: 'status', label: '状态列名', placeholder: '例如：状态,使用状态' },
  { key: 'service_code', label: '交易码列名（可选）', placeholder: '例如：交易码,服务码' },
];

const buildEmptyEsbMappingDraft = () => ESB_MAPPING_FIELDS.reduce(
  (acc, item) => ({ ...acc, [item.key]: '' }),
  {}
);

const parseErrorMessage = (error, fallback) => {
  const responseData = error?.response?.data;
  return responseData?.message || responseData?.detail || fallback;
};

const emptyFormValues = Object.keys(fieldLabels).reduce((acc, key) => ({ ...acc, [key]: '' }), {});
const splitMappingCandidates = (value) => (
  String(value || '')
    .replace(/，|、|；/g, ',')
    .split(/[\n,;]+/)
    .map((item) => item.trim())
    .filter(Boolean)
);

const SystemProfilePage = () => {
  const { isManager } = usePermission();
  const { user } = useAuth();
  const [form] = Form.useForm();

  const [systems, setSystems] = useState([]);
  const [profiles, setProfiles] = useState([]);
  const [selectedSystemName, setSelectedSystemName] = useState('');
  const [selectedSystemId, setSelectedSystemId] = useState('');
  const [profileMeta, setProfileMeta] = useState({
    status: 'draft',
    pending_fields: [],
    updated_at: '',
    is_stale: false,
  });

  const [completenessInfo, setCompletenessInfo] = useState(null);
  const [completenessUnknown, setCompletenessUnknown] = useState(false);

  const [loadingProfile, setLoadingProfile] = useState(false);
  const [savingProfile, setSavingProfile] = useState(false);
  const [publishingProfile, setPublishingProfile] = useState(false);

  const [scanRepoPath, setScanRepoPath] = useState('');
  const [scanArchiveFiles, setScanArchiveFiles] = useState([]);
  const [scanSubmitting, setScanSubmitting] = useState(false);
  const [scanJobsLoading, setScanJobsLoading] = useState(false);
  const [scanJobs, setScanJobs] = useState([]);

  const [esbMappingDraft, setEsbMappingDraft] = useState(buildEmptyEsbMappingDraft());
  const [esbFiles, setEsbFiles] = useState([]);
  const [esbSubmitting, setEsbSubmitting] = useState(false);

  const [knowledgeType, setKnowledgeType] = useState('document');
  const [knowledgeLevel, setKnowledgeLevel] = useState('normal');
  const [knowledgeFiles, setKnowledgeFiles] = useState([]);
  const [knowledgeSubmitting, setKnowledgeSubmitting] = useState(false);

  const selectedSystem = useMemo(
    () => systems.find((item) => item.name === selectedSystemName),
    [systems, selectedSystemName]
  );

  const canWrite = useMemo(() => {
    if (!isManager || !selectedSystem) {
      return false;
    }

    const extra = typeof selectedSystem.extra === 'object' && selectedSystem.extra ? selectedSystem.extra : {};
    const ownerId = String(extra.owner_id || '').trim();
    const ownerUsername = String(extra.owner_username || '').trim();

    if (!ownerId && !ownerUsername) {
      return false;
    }

    const userId = String(user?.id || '').trim();
    const userCandidates = [
      String(user?.username || '').trim(),
      String(user?.displayName || '').trim(),
      String(user?.display_name || '').trim(),
    ].filter(Boolean);

    if (ownerId && ownerId === userId) {
      return true;
    }

    return Boolean(ownerUsername && userCandidates.includes(ownerUsername));
  }, [isManager, selectedSystem, user]);

  const loadSystems = useCallback(async () => {
    try {
      const response = await axios.get('/api/v1/system/systems');
      const items = response.data?.data?.systems || [];
      setSystems(items);
      if (!selectedSystemName && items.length > 0) {
        setSelectedSystemName(items[0].name);
      }
    } catch (error) {
      message.error(parseErrorMessage(error, '加载系统清单失败'));
    }
  }, [selectedSystemName]);

  const loadProfiles = useCallback(async () => {
    try {
      const response = await axios.get('/api/v1/system-profiles', {
        params: { page: 1, page_size: 200 },
      });
      setProfiles(response.data?.items || []);
    } catch (error) {
      message.error(parseErrorMessage(error, '加载系统画像列表失败'));
    }
  }, []);

  const loadCompleteness = useCallback(async (systemName) => {
    if (!systemName) {
      setCompletenessInfo(null);
      setCompletenessUnknown(false);
      return;
    }

    try {
      setCompletenessUnknown(false);
      const response = await axios.get('/api/v1/system-profiles/completeness', {
        params: { system_name: systemName },
      });
      setCompletenessInfo(response.data || null);
    } catch (error) {
      setCompletenessUnknown(true);
      setCompletenessInfo(null);
    }
  }, []);

  const loadProfileDetail = useCallback(async (systemName, systemIdHint) => {
    if (!systemName) {
      return;
    }

    setLoadingProfile(true);
    try {
      const response = await axios.get(`/api/v1/system-profiles/${encodeURIComponent(systemName)}`);
      const payload = response.data?.data;

      if (payload) {
        const fields = typeof payload.fields === 'object' && payload.fields ? payload.fields : {};
        form.setFieldsValue({ ...emptyFormValues, ...fields });
        setProfileMeta({
          status: payload.status || 'draft',
          pending_fields: payload.pending_fields || [],
          updated_at: payload.updated_at || payload.created_at || '',
          is_stale: Boolean(payload.is_stale),
        });
        setSelectedSystemId(String(payload.system_id || systemIdHint || ''));
      } else {
        form.setFieldsValue(emptyFormValues);
        setProfileMeta({ status: 'draft', pending_fields: [], updated_at: '', is_stale: false });
        setSelectedSystemId(String(systemIdHint || selectedSystem?.id || ''));
      }

      await loadCompleteness(systemName);
    } catch (error) {
      message.error(parseErrorMessage(error, '加载系统画像详情失败'));
    } finally {
      setLoadingProfile(false);
    }
  }, [form, loadCompleteness, selectedSystem]);

  const refreshScanJobs = useCallback(async () => {
    setScanJobsLoading(true);
    try {
      const response = await axios.get('/api/v1/code-scan/jobs');
      const payload = Array.isArray(response.data?.data)
        ? response.data.data
        : Array.isArray(response.data)
          ? response.data
          : [];
      setScanJobs(payload);
    } catch (error) {
      message.error(parseErrorMessage(error, '加载扫描任务失败'));
    } finally {
      setScanJobsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSystems();
    loadProfiles();
    refreshScanJobs();
  }, [loadSystems, loadProfiles, refreshScanJobs]);

  useEffect(() => {
    if (!selectedSystemName) {
      return;
    }
    const systemIdHint = selectedSystem?.id || '';
    setSelectedSystemId(systemIdHint);
    loadProfileDetail(selectedSystemName, systemIdHint);
  }, [selectedSystemName, selectedSystem, loadProfileDetail]);

  const handleSaveDraft = async () => {
    if (!selectedSystemName) {
      message.warning('请先选择系统');
      return;
    }

    try {
      const values = await form.validateFields();
      setSavingProfile(true);
      await axios.put(`/api/v1/system-profiles/${encodeURIComponent(selectedSystemName)}`, {
        system_id: selectedSystemId || selectedSystem?.id || '',
        fields: values,
        evidence_refs: [],
      });
      message.success('系统画像草稿已保存');
      await Promise.all([loadProfiles(), loadProfileDetail(selectedSystemName, selectedSystemId)]);
    } catch (error) {
      if (error?.errorFields) {
        return;
      }
      message.error(parseErrorMessage(error, '保存系统画像失败'));
    } finally {
      setSavingProfile(false);
    }
  };

  const handlePublish = async () => {
    if (!selectedSystemName) {
      message.warning('请先选择系统');
      return;
    }

    setPublishingProfile(true);
    try {
      await axios.post(`/api/v1/system-profiles/${encodeURIComponent(selectedSystemName)}/publish`);
      message.success('系统画像已发布');
      await Promise.all([loadProfiles(), loadProfileDetail(selectedSystemName, selectedSystemId)]);
    } catch (error) {
      message.error(parseErrorMessage(error, '发布系统画像失败'));
    } finally {
      setPublishingProfile(false);
    }
  };

  const handleRunScan = async () => {
    if (!selectedSystemName) {
      message.warning('请先选择系统');
      return;
    }
    if (!scanRepoPath.trim() && scanArchiveFiles.length === 0) {
      message.warning('请填写仓库路径或上传仓库压缩包');
      return;
    }

    setScanSubmitting(true);
    try {
      if (scanArchiveFiles.length > 0) {
        const formData = new FormData();
        formData.append('system_name', selectedSystemName);
        if (selectedSystemId) {
          formData.append('system_id', selectedSystemId);
        }
        formData.append('repo_archive', scanArchiveFiles[0]);
        await axios.post('/api/v1/code-scan/jobs', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
      } else {
        await axios.post('/api/v1/code-scan/jobs', {
          system_name: selectedSystemName,
          system_id: selectedSystemId || undefined,
          repo_path: scanRepoPath.trim(),
        });
      }

      message.success('代码扫描任务已提交');
      setScanArchiveFiles([]);
      setScanRepoPath('');
      await refreshScanJobs();
    } catch (error) {
      message.error(parseErrorMessage(error, '触发代码扫描失败'));
    } finally {
      setScanSubmitting(false);
    }
  };

  const handleIngestScan = async (jobId) => {
    try {
      await axios.post(`/api/v1/code-scan/jobs/${jobId}/ingest`);
      message.success('扫描结果已入库并更新完整度');
      await Promise.all([
        refreshScanJobs(),
        loadProfiles(),
        loadProfileDetail(selectedSystemName, selectedSystemId),
      ]);
    } catch (error) {
      message.error(parseErrorMessage(error, '扫描结果入库失败'));
    }
  };

  const handleImportEsb = async () => {
    if (!selectedSystemName || !selectedSystemId) {
      message.warning('请先选择已配置 system_id 的系统');
      return;
    }
    if (!esbFiles.length) {
      message.warning('请上传ESB文件');
      return;
    }

    setEsbSubmitting(true);
    try {
      const formData = new FormData();
      formData.append('system_id', selectedSystemId);
      formData.append('file', esbFiles[0]);
      ESB_MAPPING_FIELDS.forEach((item) => {
        const candidates = splitMappingCandidates(esbMappingDraft[item.key]);
        if (!candidates.length) {
          return;
        }
        formData.append(`mapping_${item.key}`, candidates.join('\n'));
      });
      await axios.post('/api/v1/esb/imports', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      message.success('ESB导入完成');
      setEsbFiles([]);
      setEsbMappingDraft(buildEmptyEsbMappingDraft());
      await Promise.all([loadProfiles(), loadProfileDetail(selectedSystemName, selectedSystemId)]);
    } catch (error) {
      message.error(parseErrorMessage(error, 'ESB导入失败'));
    } finally {
      setEsbSubmitting(false);
    }
  };

  const handleImportKnowledge = async () => {
    if (!selectedSystemName) {
      message.warning('请先选择系统');
      return;
    }
    if (!knowledgeFiles.length) {
      message.warning('请上传知识文件');
      return;
    }

    setKnowledgeSubmitting(true);
    try {
      const formData = new FormData();
      formData.append('knowledge_type', knowledgeType);
      formData.append('level', knowledgeLevel);
      formData.append('file', knowledgeFiles[0]);
      formData.append('system_name', selectedSystemName);
      if (selectedSystemId) {
        formData.append('system_id', selectedSystemId);
      }

      await axios.post('/api/v1/knowledge/imports', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      message.success('知识导入完成');
      setKnowledgeFiles([]);
      await Promise.all([loadProfiles(), loadProfileDetail(selectedSystemName, selectedSystemId)]);
    } catch (error) {
      message.error(parseErrorMessage(error, '知识导入失败'));
    } finally {
      setKnowledgeSubmitting(false);
    }
  };

  const profileColumns = [
    {
      title: '系统',
      dataIndex: 'system_name',
      key: 'system_name',
      render: (value) => value || '-',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (value) => (
        <Tag color={value === 'published' ? 'green' : 'gold'}>
          {value === 'published' ? '已发布' : '草稿'}
        </Tag>
      ),
    },
    {
      title: '完整度',
      dataIndex: 'completeness_score',
      key: 'completeness_score',
      width: 80,
      render: (value) => `${value || 0}`,
    },
  ];

  const scanColumns = [
    { title: '任务ID', dataIndex: 'job_id', key: 'job_id', ellipsis: true },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (value) => <Tag color={value === 'completed' ? 'green' : value === 'failed' ? 'red' : 'processing'}>{value}</Tag>,
    },
    {
      title: '进度',
      dataIndex: 'progress',
      key: 'progress',
      width: 80,
      render: (value) => `${value || 0}%`,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 170,
      render: (value) => formatDateTime(value),
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_, record) => (
        <Button
          type="link"
          size="small"
          disabled={record.status !== 'completed' || !canWrite}
          onClick={() => handleIngestScan(record.job_id)}
        >
          入库
        </Button>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="系统画像工作台"
        subtitle="在同一页面完成扫描/ESB/文档导入、草稿编辑与发布"
      />

      <Row gutter={12}>
        <Col span={8}>
          <Card
            title="系统画像列表"
            extra={(
              <Button size="small" icon={<ReloadOutlined />} onClick={loadProfiles}>
                刷新
              </Button>
            )}
          >
            <Space direction="vertical" style={{ width: '100%' }}>
              <Select
                showSearch
                value={selectedSystemName || undefined}
                placeholder="选择系统"
                optionFilterProp="label"
                options={systems.map((item) => ({
                  label: `${item.name}${item.id ? ` (${item.id})` : ''}`,
                  value: item.name,
                }))}
                onChange={(value) => {
                  const system = systems.find((item) => item.name === value);
                  setSelectedSystemName(value);
                  setSelectedSystemId(system?.id || '');
                }}
              />

              <Table
                rowKey={(record) => record.system_name}
                size="small"
                columns={profileColumns}
                dataSource={profiles}
                pagination={{ pageSize: 8 }}
                onRow={(record) => ({
                  onClick: () => {
                    setSelectedSystemName(record.system_name);
                    setSelectedSystemId(record.system_id || '');
                  },
                })}
              />
            </Space>
          </Card>
        </Col>

        <Col span={16}>
          <Space direction="vertical" style={{ width: '100%' }} size={12}>
            <Card loading={loadingProfile}>
              <Space direction="vertical" style={{ width: '100%' }}>
                <div className="profile-meta-row">
                  <Title level={4} style={{ margin: 0 }}>{selectedSystemName || '未选择系统'}</Title>
                  <Space>
                    <Tag color={profileMeta.status === 'published' ? 'green' : 'gold'}>
                      {profileMeta.status === 'published' ? '已发布' : '草稿'}
                    </Tag>
                    {profileMeta.is_stale && <Tag color="orange">画像过时</Tag>}
                    <Text type="secondary">最后更新：{formatDateTime(profileMeta.updated_at)}</Text>
                  </Space>
                </div>

                {completenessUnknown ? (
                  <Alert type="warning" showIcon message="完整度未知" description="完整度接口暂时不可用，不影响继续查看与编辑画像。" />
                ) : (
                  <Alert
                    type="info"
                    showIcon
                    message={`完整度 ${completenessInfo?.completeness_score ?? 0} / 100`}
                    description={`代码扫描 ${completenessInfo?.breakdown?.code_scan ?? 0}，文档 ${completenessInfo?.breakdown?.documents ?? 0}，ESB ${completenessInfo?.breakdown?.esb ?? 0}`}
                  />
                )}

                {isManager && !canWrite && (
                  <Text type="secondary">当前系统只读，仅系统主责 PM 可执行保存、发布及导入操作。</Text>
                )}

                <Form form={form} layout="vertical" initialValues={emptyFormValues}>
                  {Object.entries(fieldLabels).map(([key, label]) => (
                    <Form.Item
                      key={key}
                      name={key}
                      label={label}
                      rules={[
                        key === 'in_scope' || key === 'out_of_scope' || key === 'core_functions' || key === 'business_objects' || key === 'integration_points'
                          ? { required: true, message: `请填写${label}` }
                          : {},
                      ]}
                    >
                      <TextArea rows={2} placeholder={`请输入${label}`} />
                    </Form.Item>
                  ))}
                </Form>

                <Space>
                  {canWrite && (
                    <Button type="primary" icon={<SaveOutlined />} loading={savingProfile} onClick={handleSaveDraft}>
                      保存草稿
                    </Button>
                  )}
                  {canWrite && (
                    <Button icon={<SendOutlined />} loading={publishingProfile} onClick={handlePublish}>
                      发布画像
                    </Button>
                  )}
                  <Button onClick={() => loadProfileDetail(selectedSystemName, selectedSystemId)}>
                    重新加载
                  </Button>
                </Space>

                <Space wrap>
                  <Text type="secondary">待补证据字段：</Text>
                  {(profileMeta.pending_fields || []).length > 0
                    ? profileMeta.pending_fields.map((item) => <Tag key={item}>{item}</Tag>)
                    : <Text type="secondary">无</Text>}
                </Space>
              </Space>
            </Card>

            <Card title="代码扫描（API-001 / API-002）" extra={<Button size="small" onClick={refreshScanJobs}>刷新任务</Button>}>
              <Space direction="vertical" style={{ width: '100%' }}>
                <Space wrap style={{ width: '100%' }}>
                  <Input
                    style={{ width: 360 }}
                    placeholder="仓库本地路径（可选）"
                    value={scanRepoPath}
                    onChange={(event) => setScanRepoPath(event.target.value)}
                    disabled={!canWrite}
                  />
                  <Upload.Dragger
                    accept=".zip,.tar,.gz,.tgz"
                    multiple={false}
                    beforeUpload={(file) => {
                      setScanArchiveFiles([file]);
                      return false;
                    }}
                    fileList={scanArchiveFiles.map((file) => ({ uid: file.uid || file.name, name: file.name }))}
                    onRemove={() => setScanArchiveFiles([])}
                    disabled={!canWrite}
                    style={{ width: 320 }}
                  >
                    <p className="ant-upload-drag-icon"><InboxOutlined /></p>
                    <p className="ant-upload-text">上传仓库压缩包（可选）</p>
                  </Upload.Dragger>
                  {canWrite && (
                    <Button type="primary" icon={<PlayCircleOutlined />} loading={scanSubmitting} onClick={handleRunScan}>
                      提交扫描
                    </Button>
                  )}
                </Space>

                <Table
                  rowKey="job_id"
                  size="small"
                  loading={scanJobsLoading}
                  columns={scanColumns}
                  dataSource={scanJobs}
                  pagination={{ pageSize: 5 }}
                />
              </Space>
            </Card>

            <Card title="ESB导入（API-003）">
              <Space direction="vertical" style={{ width: '100%' }}>
                <Text type="secondary">
                  可选：按表头填写映射列名，支持逗号或换行分隔多个候选名。
                </Text>
                <Row gutter={8}>
                  {ESB_MAPPING_FIELDS.map((item) => (
                    <Col key={item.key} span={12}>
                      <Input
                        value={esbMappingDraft[item.key]}
                        onChange={(event) => {
                          const nextValue = event.target.value;
                          setEsbMappingDraft((prev) => ({ ...prev, [item.key]: nextValue }));
                        }}
                        placeholder={item.placeholder}
                        disabled={!canWrite}
                        addonBefore={item.label}
                      />
                    </Col>
                  ))}
                </Row>
                <Upload
                  beforeUpload={(file) => {
                    setEsbFiles([file]);
                    return false;
                  }}
                  onRemove={() => setEsbFiles([])}
                  fileList={esbFiles.map((file) => ({ uid: file.uid || file.name, name: file.name }))}
                  disabled={!canWrite}
                >
                  <Button icon={<CloudUploadOutlined />} disabled={!canWrite}>选择ESB文件（xlsx/csv）</Button>
                </Upload>
                {canWrite && (
                  <Button type="primary" loading={esbSubmitting} onClick={handleImportEsb}>
                    导入ESB
                  </Button>
                )}
              </Space>
            </Card>

            <Card title="知识导入（API-011）">
              <Space direction="vertical" style={{ width: '100%' }}>
                <Space wrap>
                  <Select
                    style={{ width: 160 }}
                    value={knowledgeType}
                    onChange={setKnowledgeType}
                    options={[
                      { label: '系统文档(document)', value: 'document' },
                      { label: '代码知识(code)', value: 'code' },
                    ]}
                    disabled={!canWrite}
                  />
                  <Select
                    style={{ width: 160 }}
                    value={knowledgeLevel}
                    onChange={setKnowledgeLevel}
                    options={[
                      { label: '正常样本(normal)', value: 'normal' },
                      { label: '历史样本(L0)', value: 'l0' },
                    ]}
                    disabled={!canWrite || knowledgeType !== 'document'}
                  />
                </Space>

                <Upload
                  beforeUpload={(file) => {
                    setKnowledgeFiles([file]);
                    return false;
                  }}
                  onRemove={() => setKnowledgeFiles([])}
                  fileList={knowledgeFiles.map((file) => ({ uid: file.uid || file.name, name: file.name }))}
                  disabled={!canWrite}
                >
                  <Button icon={<CloudUploadOutlined />} disabled={!canWrite}>选择知识文件</Button>
                </Upload>

                {canWrite && (
                  <Button type="primary" loading={knowledgeSubmitting} onClick={handleImportKnowledge}>
                    导入知识
                  </Button>
                )}
              </Space>
            </Card>
          </Space>
        </Col>
      </Row>
    </div>
  );
};

export default SystemProfilePage;
