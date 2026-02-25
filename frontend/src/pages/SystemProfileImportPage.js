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
  PlayCircleOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useLocation, useNavigate } from 'react-router-dom';
import axios from 'axios';
import useAuth from '../hooks/useAuth';
import usePermission from '../hooks/usePermission';
import { formatDateTime } from '../utils/time';
import { filterResponsibleSystems, resolveSystemOwnership } from '../utils/systemOwnership';

const { Text } = Typography;

const DOC_TYPE_ESB = 'esb';

const DOC_TYPE_OPTIONS = [
  { value: 'requirements', label: '需求文档' },
  { value: 'design', label: '设计文档' },
  { value: 'tech_solution', label: '技术方案' },
  { value: 'history_report', label: '历史评估报告' },
  { value: DOC_TYPE_ESB, label: 'ESB服务治理文档' },
];

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

  const [esbFiles, setEsbFiles] = useState([]);
  const [esbSubmitting, setEsbSubmitting] = useState(false);
  const [esbLastResult, setEsbLastResult] = useState(null);

  const [docType, setDocType] = useState('requirements');
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
      message.warning('请上传文档文件');
      return;
    }

    setKnowledgeSubmitting(true);
    try {
      const formData = new FormData();
      formData.append('knowledge_type', 'document');
      formData.append('level', 'normal');
      formData.append('doc_type', docType);
      formData.append('file', knowledgeFiles[0]);
      formData.append('system_name', selectedSystemName);
      if (selectedSystem?.id) {
        formData.append('system_id', selectedSystem.id);
      }

      const response = await axios.post('/api/v1/knowledge/imports', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setKnowledgeLastResult(response.data || null);
      message.success('文档导入完成');
      setKnowledgeFiles([]);
    } catch (error) {
      message.error(parseErrorMessage(error, '文档导入失败'));
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
      {responsibleSystems.length === 0 ? (
        <Card>
          <Text type="secondary">暂无可操作系统（仅展示主责/B角系统）。请联系管理员维护系统负责关系。</Text>
        </Card>
      ) : (
        <Space direction="vertical" style={{ width: '100%' }} size={12}>
          <Space direction="vertical" style={{ width: '100%' }} size={6}>
            <Tabs
              size="small"
              activeKey={selectedSystemName || undefined}
              onChange={handleSystemTabChange}
              items={responsibleSystems.map((item) => ({ key: item.name, label: item.name }))}
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

          <Card
            title="代码扫描"
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
            <Space direction="vertical" style={{ width: '100%' }} size={8}>
              <Space wrap style={{ width: '100%' }} size={8}>
                <Input
                  style={{ width: 360, maxWidth: '100%' }}
                  placeholder="仓库本地路径（可选）"
                  value={scanRepoPath}
                  onChange={(event) => setScanRepoPath(event.target.value)}
                  disabled={!canWrite}
                />
                <Upload
                  accept=".zip,.tar,.gz,.tgz"
                  multiple={false}
                  beforeUpload={(file) => {
                    setScanArchiveFiles([file]);
                    return false;
                  }}
                  fileList={scanArchiveFiles.map((file) => ({ uid: file.uid || file.name, name: file.name }))}
                  onRemove={() => setScanArchiveFiles([])}
                  disabled={!canWrite}
                >
                  <Button icon={<CloudUploadOutlined />} disabled={!canWrite}>
                    选择仓库压缩包（可选）
                  </Button>
                </Upload>
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

          <Card title="文档导入">
            <Space direction="vertical" style={{ width: '100%' }} size={8}>
              <Space wrap size={8} style={{ width: '100%' }}>
                <Select
                  style={{ width: 220, maxWidth: '100%' }}
                  value={docType}
                  onChange={(value) => { setDocType(value); setEsbLastResult(null); setKnowledgeLastResult(null); }}
                  options={DOC_TYPE_OPTIONS}
                  disabled={!canWrite}
                />
                <Upload
                  accept={docType === DOC_TYPE_ESB ? '.xlsx,.csv' : undefined}
                  beforeUpload={(file) => {
                    if (docType === DOC_TYPE_ESB) {
                      setEsbFiles([file]);
                    } else {
                      setKnowledgeFiles([file]);
                    }
                    return false;
                  }}
                  onRemove={() => {
                    if (docType === DOC_TYPE_ESB) {
                      setEsbFiles([]);
                    } else {
                      setKnowledgeFiles([]);
                    }
                  }}
                  fileList={
                    (docType === DOC_TYPE_ESB ? esbFiles : knowledgeFiles)
                      .map((file) => ({ uid: file.uid || file.name, name: file.name }))
                  }
                  disabled={!canWrite}
                >
                  <Button icon={<CloudUploadOutlined />} disabled={!canWrite}>
                    {docType === DOC_TYPE_ESB ? '选择ESB文件（xlsx/csv）' : '选择文档文件'}
                  </Button>
                </Upload>

                {canWrite && (
                  <Button
                    type="primary"
                    loading={docType === DOC_TYPE_ESB ? esbSubmitting : knowledgeSubmitting}
                    onClick={docType === DOC_TYPE_ESB ? handleImportEsb : handleImportKnowledge}
                  >
                    导入
                  </Button>
                )}
              </Space>

              {docType === DOC_TYPE_ESB && esbLastResult && (
                <Alert
                  type={((esbLastResult.errors || []).length > 0) ? 'warning' : 'success'}
                  showIcon
                  message="本次导入统计"
                  description={`总计 ${esbLastResult.total ?? 0}，导入 ${esbLastResult.imported ?? 0}，跳过 ${esbLastResult.skipped ?? 0}${Array.isArray(esbLastResult.errors) && esbLastResult.errors.length > 0 ? `，提示：${esbLastResult.errors.join('；')}` : ''}`}
                />
              )}

              {docType !== DOC_TYPE_ESB && knowledgeLastResult && (
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
