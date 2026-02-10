import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Descriptions,
  Input,
  message,
  Select,
  Space,
  Tabs,
  Tag,
  Typography,
  Upload,
} from 'antd';
import {
  CloudUploadOutlined,
  InboxOutlined,
  PlayCircleOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useLocation, useNavigate } from 'react-router-dom';
import axios from 'axios';
import PageHeader from '../components/PageHeader';
import useAuth from '../hooks/useAuth';
import usePermission from '../hooks/usePermission';
import { formatDateTime } from '../utils/time';
import { filterResponsibleSystems, resolveSystemOwnership } from '../utils/systemOwnership';

const { TextArea } = Input;
const { Text } = Typography;

const parseErrorMessage = (error, fallback) => {
  const responseData = error?.response?.data;
  return responseData?.message || responseData?.detail || fallback;
};

const SystemProfileImportPage = () => {
  const { user } = useAuth();
  const { isManager } = usePermission();
  const location = useLocation();
  const navigate = useNavigate();

  const [systems, setSystems] = useState([]);
  const [selectedSystemName, setSelectedSystemName] = useState('');

  const [scanRepoPath, setScanRepoPath] = useState('');
  const [scanArchiveFiles, setScanArchiveFiles] = useState([]);
  const [scanSubmitting, setScanSubmitting] = useState(false);
  const [scanRefreshing, setScanRefreshing] = useState(false);
  const [scanIngesting, setScanIngesting] = useState(false);
  const [scanJob, setScanJob] = useState(null);
  const [scanIngestResult, setScanIngestResult] = useState(null);
  const [storedScanJobId, setStoredScanJobId] = useState('');

  const [esbMappingJson, setEsbMappingJson] = useState('');
  const [esbFiles, setEsbFiles] = useState([]);
  const [esbSubmitting, setEsbSubmitting] = useState(false);
  const [esbLastResult, setEsbLastResult] = useState(null);

  const [knowledgeType, setKnowledgeType] = useState('document');
  const [knowledgeLevel, setKnowledgeLevel] = useState('normal');
  const [knowledgeFiles, setKnowledgeFiles] = useState([]);
  const [knowledgeSubmitting, setKnowledgeSubmitting] = useState(false);
  const [knowledgeLastResult, setKnowledgeLastResult] = useState(null);

  const queryParams = useMemo(() => new URLSearchParams(location.search), [location.search]);

  const responsibleSystems = useMemo(() => filterResponsibleSystems(systems, user), [systems, user]);

  const selectedSystem = useMemo(
    () => responsibleSystems.find((item) => item.name === selectedSystemName),
    [responsibleSystems, selectedSystemName]
  );

  const canWrite = useMemo(() => {
    if (!isManager || !selectedSystem) {
      return false;
    }
    return resolveSystemOwnership(selectedSystem, user).canWrite;
  }, [isManager, selectedSystem, user]);

  const scanJobStorageKey = useMemo(() => {
    const keyPart = selectedSystem?.id || selectedSystemName;
    return keyPart ? `systemProfile:lastScanJobId:${keyPart}` : '';
  }, [selectedSystem?.id, selectedSystemName]);

  const loadSystems = useCallback(async () => {
    try {
      const response = await axios.get('/api/v1/system/systems');
      const items = response.data?.data?.systems || [];
      setSystems(items);
    } catch (error) {
      message.error(parseErrorMessage(error, '加载系统清单失败'));
    }
  }, []);

  const syncSelectedSystemFromUrl = useCallback((items) => {
    if (!items.length) {
      setSelectedSystemName('');
      return;
    }

    const systemNameInUrl = String(queryParams.get('system_name') || '').trim();
    const existsInList = systemNameInUrl && items.some((item) => item.name === systemNameInUrl);
    const nextName = existsInList ? systemNameInUrl : items[0].name;

    setSelectedSystemName(nextName);

    const nextSystem = items.find((item) => item.name === nextName);
    const nextId = String(nextSystem?.id || '').trim();
    const urlName = String(queryParams.get('system_name') || '').trim();
    const urlId = String(queryParams.get('system_id') || '').trim();
    if (urlName !== nextName || urlId !== nextId) {
      const nextParams = new URLSearchParams(location.search);
      nextParams.set('system_name', nextName);
      if (nextId) {
        nextParams.set('system_id', nextId);
      } else {
        nextParams.delete('system_id');
      }
      navigate({ pathname: location.pathname, search: `?${nextParams.toString()}` }, { replace: true });
    }
  }, [location.pathname, location.search, navigate, queryParams]);

  const fetchScanJob = useCallback(async (jobId) => {
    if (!jobId) {
      return;
    }

    setScanRefreshing(true);
    try {
      const response = await axios.get(`/api/v1/code-scan/jobs/${encodeURIComponent(jobId)}`);
      setScanJob(response.data || null);
    } catch (error) {
      setScanJob(null);
      message.error(parseErrorMessage(error, '加载扫描任务状态失败'));
    } finally {
      setScanRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadSystems();
  }, [loadSystems]);

  useEffect(() => {
    if (!responsibleSystems.length) {
      return;
    }
    syncSelectedSystemFromUrl(responsibleSystems);
  }, [responsibleSystems, syncSelectedSystemFromUrl]);

  useEffect(() => {
    setScanIngestResult(null);
    setEsbLastResult(null);
    setKnowledgeLastResult(null);
    setStoredScanJobId('');

    if (!scanJobStorageKey) {
      setScanJob(null);
      return;
    }

    let stored = '';
    try {
      stored = localStorage.getItem(scanJobStorageKey) || '';
    } catch (error) {
      stored = '';
    }
    setStoredScanJobId(stored);
    if (!stored) {
      setScanJob(null);
      return;
    }
    fetchScanJob(stored);
  }, [fetchScanJob, scanJobStorageKey]);

  const handleSystemTabChange = (systemName) => {
    const nextName = String(systemName || '').trim();
    if (!nextName) {
      return;
    }

    const system = responsibleSystems.find((item) => item.name === nextName);
    const nextParams = new URLSearchParams(location.search);
    nextParams.set('system_name', nextName);
    const systemId = String(system?.id || '').trim();
    if (systemId) {
      nextParams.set('system_id', systemId);
    } else {
      nextParams.delete('system_id');
    }
    navigate({ pathname: location.pathname, search: `?${nextParams.toString()}` }, { replace: true });
    setSelectedSystemName(nextName);
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
      let response;
      if (scanArchiveFiles.length > 0) {
        const formData = new FormData();
        formData.append('system_name', selectedSystemName);
        if (selectedSystem?.id) {
          formData.append('system_id', selectedSystem.id);
        }
        formData.append('repo_archive', scanArchiveFiles[0]);
        response = await axios.post('/api/v1/code-scan/jobs', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
      } else {
        response = await axios.post('/api/v1/code-scan/jobs', {
          system_name: selectedSystemName,
          system_id: selectedSystem?.id || undefined,
          repo_path: scanRepoPath.trim(),
        });
      }

      const payload = response.data || null;
      setScanJob(payload);
      if (payload?.job_id && scanJobStorageKey) {
        try {
          localStorage.setItem(scanJobStorageKey, payload.job_id);
          setStoredScanJobId(payload.job_id);
        } catch (error) {
          setStoredScanJobId('');
        }
      }

      message.success(`代码扫描任务已提交${payload?.job_id ? `（${payload.job_id}）` : ''}`);
      setScanRepoPath('');
      setScanArchiveFiles([]);
      setScanIngestResult(null);
    } catch (error) {
      message.error(parseErrorMessage(error, '触发代码扫描失败'));
    } finally {
      setScanSubmitting(false);
    }
  };

  const handleIngestScan = async () => {
    const jobId = scanJob?.job_id;
    if (!jobId) {
      message.warning('暂无可入库的任务');
      return;
    }

    setScanIngesting(true);
    try {
      const response = await axios.post(`/api/v1/code-scan/jobs/${encodeURIComponent(jobId)}/ingest`);
      setScanIngestResult(response.data || null);
      message.success('扫描结果已入库并更新完整度');
    } catch (error) {
      message.error(parseErrorMessage(error, '扫描结果入库失败'));
    } finally {
      setScanIngesting(false);
    }
  };

  const handleImportEsb = async () => {
    const systemId = String(selectedSystem?.id || '').trim();
    if (!selectedSystemName || !systemId) {
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
      formData.append('system_id', systemId);
      formData.append('file', esbFiles[0]);
      if (esbMappingJson.trim()) {
        formData.append('mapping_json', esbMappingJson.trim());
      }
      const response = await axios.post('/api/v1/esb/imports', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setEsbLastResult(response.data || null);
      message.success('ESB导入完成');
      setEsbFiles([]);
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
      if (selectedSystem?.id) {
        formData.append('system_id', selectedSystem.id);
      }

      const response = await axios.post('/api/v1/knowledge/imports', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setKnowledgeLastResult(response.data || null);
      message.success('知识导入完成');
      setKnowledgeFiles([]);
    } catch (error) {
      message.error(parseErrorMessage(error, '知识导入失败'));
    } finally {
      setKnowledgeSubmitting(false);
    }
  };

  const scanStatusTag = useMemo(() => {
    const status = String(scanJob?.status || '').trim();
    if (!status) {
      return null;
    }
    const color = status === 'completed' ? 'green' : status === 'failed' ? 'red' : 'processing';
    return <Tag color={color}>{status}</Tag>;
  }, [scanJob?.status]);

  return (
    <div>
      <PageHeader
        title="系统画像 / 知识导入"
        subtitle="配置管理 → 系统画像 → 知识导入（不展示导入历史/最近任务列表，仅反馈当前操作结果）"
      />

      {responsibleSystems.length === 0 ? (
        <Card>
          <Text type="secondary">暂无可操作系统（仅展示主责/B角系统）。请联系管理员维护系统负责关系。</Text>
        </Card>
      ) : (
        <Space direction="vertical" style={{ width: '100%' }} size={12}>
          <Card>
            <Space direction="vertical" style={{ width: '100%' }} size={8}>
              <Tabs
                activeKey={selectedSystemName || undefined}
                onChange={handleSystemTabChange}
                items={responsibleSystems.map((item) => ({ key: item.name, label: item.name }))}
              />
              <Descriptions
                size="small"
                column={3}
                items={[
                  { key: 'name', label: '系统', children: selectedSystem?.name || '-' },
                  { key: 'id', label: 'ID', children: selectedSystem?.id || '-' },
                  { key: 'status', label: '状态', children: selectedSystem?.status || '-' },
                ]}
              />
              {!canWrite && (
                <Alert
                  type="warning"
                  showIcon
                  message="当前系统为只读"
                  description="仅系统主责或B角 PM 可执行导入操作。"
                />
              )}
            </Space>
          </Card>

          <Card
            title="代码扫描（API-001 / API-002）"
            extra={(
              <Button
                size="small"
                icon={<ReloadOutlined />}
                onClick={() => fetchScanJob(scanJob?.job_id || storedScanJobId)}
                loading={scanRefreshing}
                disabled={!scanJob?.job_id && !storedScanJobId}
              >
                刷新状态
              </Button>
            )}
          >
            <Space direction="vertical" style={{ width: '100%' }} size={12}>
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

              {scanJob?.job_id ? (
                <Space direction="vertical" style={{ width: '100%' }} size={8}>
                  <Descriptions
                    size="small"
                    column={3}
                    items={[
                      { key: 'job_id', label: '最近任务', children: scanJob.job_id },
                      { key: 'status', label: '状态', children: scanStatusTag },
                      { key: 'progress', label: '进度', children: `${scanJob.progress ?? 0}%` },
                      { key: 'created_at', label: '创建时间', children: formatDateTime(scanJob.created_at) },
                      { key: 'message', label: '说明', children: scanJob.message || '-' },
                    ]}
                  />

                  <Space>
                    <Button
                      loading={scanRefreshing}
                      onClick={() => fetchScanJob(scanJob.job_id)}
                      icon={<ReloadOutlined />}
                    >
                      刷新
                    </Button>
                    <Button
                      type="primary"
                      loading={scanIngesting}
                      disabled={!canWrite || scanJob.status !== 'completed'}
                      onClick={handleIngestScan}
                    >
                      入库
                    </Button>
                  </Space>

                  {scanIngestResult && (
                    <Alert
                      type="success"
                      showIcon
                      message="入库结果"
                      description={`成功 ${scanIngestResult.success ?? 0}，失败 ${scanIngestResult.failed ?? 0}`}
                    />
                  )}
                </Space>
              ) : (
                <Text type="secondary">暂无任务。提交扫描后将在此处展示最近一次任务状态。</Text>
              )}
            </Space>
          </Card>

          <Card title="ESB导入（API-003）">
            <Space direction="vertical" style={{ width: '100%' }} size={12}>
              <TextArea
                rows={3}
                value={esbMappingJson}
                onChange={(event) => setEsbMappingJson(event.target.value)}
                placeholder='可选：mapping_json，例如 {"provider_system":["提供方系统","provider"]}'
                disabled={!canWrite}
              />
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

              {esbLastResult && (
                <Alert
                  type="info"
                  showIcon
                  message="本次导入统计"
                  description={`总计 ${esbLastResult.total ?? 0}，导入 ${esbLastResult.imported ?? 0}，跳过 ${esbLastResult.skipped ?? 0}`}
                />
              )}
            </Space>
          </Card>

          <Card title="知识导入（API-011）">
            <Space direction="vertical" style={{ width: '100%' }} size={12}>
              <Space wrap>
                <Select
                  style={{ width: 180 }}
                  value={knowledgeType}
                  onChange={setKnowledgeType}
                  options={[
                    { label: '系统文档(document)', value: 'document' },
                    { label: '代码知识(code)', value: 'code' },
                  ]}
                  disabled={!canWrite}
                />
                <Select
                  style={{ width: 180 }}
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

              {knowledgeLastResult && (
                <Alert
                  type={(knowledgeLastResult.failed || 0) > 0 ? 'warning' : 'success'}
                  showIcon
                  message="本次导入统计"
                  description={`导入 ${knowledgeLastResult.imported ?? 0}，失败 ${knowledgeLastResult.failed ?? 0}${Array.isArray(knowledgeLastResult.errors) && knowledgeLastResult.errors.length ? `，提示：${knowledgeLastResult.errors.join('；')}` : ''}`}
                />
              )}
            </Space>
          </Card>
        </Space>
      )}
    </div>
  );
};

export default SystemProfileImportPage;
