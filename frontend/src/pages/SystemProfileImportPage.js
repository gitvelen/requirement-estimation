import React, { useCallback, useEffect, useMemo, useState, useRef } from 'react';
import {
  Alert,
  Button,
  Card,
  Descriptions,
  Input,
  List,
  message,
  Space,
  Tabs,
  Tag,
  Typography,
  Upload,
} from 'antd';
import {
  CloudUploadOutlined,
  DownOutlined,
  FileTextOutlined,
  PlayCircleOutlined,
  ReloadOutlined,
  RightOutlined,
} from '@ant-design/icons';
import { useLocation, useNavigate } from 'react-router-dom';
import axios from 'axios';
import useAuth from '../hooks/useAuth';
import usePermission from '../hooks/usePermission';
import { formatDateTime } from '../utils/time';
import { filterResponsibleSystems, resolveSystemOwnership } from '../utils/systemOwnership';

const { Text } = Typography;

const DOC_TYPE_ESB = 'esb';

const DOC_TYPE_CONFIGS = [
  { value: 'requirements', label: '需求文档', description: '需求规格说明、用户故事等' },
  { value: 'design', label: '设计文档', description: '概要设计、详细设计等' },
  { value: 'tech_solution', label: '技术方案', description: '技术选型、架构设计等' },
  { value: 'history_report', label: '历史评估报告', description: '过往项目评估结果' },
  { value: DOC_TYPE_ESB, label: 'ESB服务治理文档', description: 'ESB接口申请模板（xlsx/csv）' },
];

const EXTRACTION_POLL_INTERVAL = 3000;

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

  const [docStates, setDocStates] = useState({});
  const [importHistory, setImportHistory] = useState([]);
  const [historyExpanded, setHistoryExpanded] = useState(false);
  const [extractionStatus, setExtractionStatus] = useState(null);

  const pollTimerRef = useRef(null);

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
    setDocStates({});
    setImportHistory([]);
    setHistoryExpanded(false);
    setExtractionStatus(null);
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

  const loadImportHistory = useCallback(async (systemId) => {
    try {
      const response = await axios.get(`/api/v1/system-profiles/${encodeURIComponent(systemId)}/profile/import-history`, {
        params: { limit: 50, offset: 0 },
      });
      const records = response.data?.records || [];
      setImportHistory(records);
    } catch (error) {
      setImportHistory([]);
    }
  }, []);

  useEffect(() => {
    const systemId = String(selectedSystem?.id || '').trim();
    if (!systemId) {
      return;
    }
    loadImportHistory(systemId);
  }, [selectedSystem, loadImportHistory]);

  useEffect(() => {
    return () => {
      if (pollTimerRef.current) {
        clearTimeout(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    };
  }, []);

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

  const pollExtractionStatus = useCallback(async (systemId) => {
    if (!systemId) {
      return;
    }
    try {
      const response = await axios.get(`/api/v1/system-profiles/${encodeURIComponent(systemId)}/profile/extraction-status`);
      const status = response.data || {};
      setExtractionStatus(status);

      if (status.status === 'processing') {
        pollTimerRef.current = setTimeout(() => {
          pollExtractionStatus(systemId);
        }, EXTRACTION_POLL_INTERVAL);
      } else if (status.status === 'completed') {
        if (pollTimerRef.current) {
          clearTimeout(pollTimerRef.current);
          pollTimerRef.current = null;
        }
        loadImportHistory(systemId);
      }
    } catch (error) {
      setExtractionStatus(null);
    }
  }, [loadImportHistory]);

  const handleDocImport = useCallback(async (docType) => {
    const systemId = String(selectedSystem?.id || '').trim();
    const state = docStates[docType] || {};
    const files = state.files || [];

    if (!selectedSystemName || !systemId) {
      message.warning('请先选择已配置 system_id 的系统');
      return;
    }
    if (!files.length) {
      message.warning('请上传文件');
      return;
    }

    setDocStates((prev) => ({
      ...prev,
      [docType]: { ...prev[docType], submitting: true },
    }));

    try {
      const formData = new FormData();
      formData.append('system_id', systemId);
      formData.append('file', files[0]);

      let response;
      if (docType === DOC_TYPE_ESB) {
        response = await axios.post('/api/v1/esb/imports', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
      } else {
        formData.append('knowledge_type', 'document');
        formData.append('level', 'normal');
        formData.append('doc_type', docType);
        formData.append('system_name', selectedSystemName);
        response = await axios.post('/api/v1/knowledge/imports', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
      }

      const result = response.data || {};
      setDocStates((prev) => ({
        ...prev,
        [docType]: {
          ...prev[docType],
          submitting: false,
          files: [],
          lastResult: result,
        },
      }));

      message.success('文档导入完成');
      loadImportHistory(systemId);

      if (result.extraction_task_id) {
        pollExtractionStatus(systemId);
      }
    } catch (error) {
      setDocStates((prev) => ({
        ...prev,
        [docType]: { ...prev[docType], submitting: false },
      }));
      message.error(parseErrorMessage(error, '文档导入失败'));
    }
  }, [selectedSystem, selectedSystemName, docStates, loadImportHistory, pollExtractionStatus]);

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

      const systemId = String(selectedSystem?.id || '').trim();
      if (systemId) {
        loadImportHistory(systemId);
        pollExtractionStatus(systemId);
      }
    } catch (error) {
      message.error(parseErrorMessage(error, '扫描结果入库失败'));
    } finally {
      setScanIngesting(false);
    }
  };

  const navigateToProfile = useCallback(() => {
    const systemId = String(selectedSystem?.id || '').trim();
    if (!systemId) {
      return;
    }
    navigate(`/system-profile/board?system_id=${encodeURIComponent(systemId)}&system_name=${encodeURIComponent(selectedSystemName)}`);
  }, [selectedSystem, selectedSystemName, navigate]);

  const renderDocTypeCard = (config) => {
    const { value: docType, label, description } = config;
    const state = docStates[docType] || {};
    const files = state.files || [];
    const submitting = state.submitting || false;
    const lastResult = state.lastResult || null;

    const isEsb = docType === DOC_TYPE_ESB;
    const accept = isEsb ? '.xlsx,.csv' : undefined;

    return (
      <Card
        key={docType}
        size="small"
        title={
          <Space>
            <FileTextOutlined />
            <span>{label}</span>
            <Text type="secondary" style={{ fontSize: 12, fontWeight: 'normal' }}>
              {description}
            </Text>
          </Space>
        }
      >
        <Space direction="vertical" style={{ width: '100%' }} size={8}>
          <Space wrap size={8}>
            <Upload
              accept={accept}
              multiple={false}
              beforeUpload={(file) => {
                setDocStates((prev) => ({
                  ...prev,
                  [docType]: { ...prev[docType], files: [file] },
                }));
                return false;
              }}
              fileList={files.map((file) => ({ uid: file.uid || file.name, name: file.name }))}
              onRemove={() => {
                setDocStates((prev) => ({
                  ...prev,
                  [docType]: { ...prev[docType], files: [] },
                }));
              }}
              disabled={!canWrite}
            >
              <Button icon={<CloudUploadOutlined />} disabled={!canWrite}>
                {isEsb ? '选择ESB文件（xlsx/csv）' : '选择文档文件'}
              </Button>
            </Upload>
            {canWrite && (
              <Button
                type="primary"
                loading={submitting}
                onClick={() => handleDocImport(docType)}
                disabled={!files.length}
              >
                导入
              </Button>
            )}
          </Space>

          {lastResult && (
            <Space direction="vertical" style={{ width: '100%' }} size={4}>
              <Alert
                type={
                  isEsb
                    ? ((lastResult.errors || []).length > 0 ? 'warning' : 'success')
                    : ((lastResult.failed || 0) > 0 ? 'warning' : 'success')
                }
                showIcon
                message="本次导入统计"
                description={
                  isEsb
                    ? `总计 ${lastResult.total ?? 0}，导入 ${lastResult.imported ?? 0}，跳过 ${lastResult.skipped ?? 0}${
                        Array.isArray(lastResult.errors) && lastResult.errors.length > 0
                          ? `，提示：${lastResult.errors.join('；')}`
                          : ''
                      }`
                    : `导入 ${lastResult.imported ?? 0}，失败 ${lastResult.failed ?? 0}${
                        Array.isArray(lastResult.errors) && lastResult.errors.length
                          ? `，提示：${lastResult.errors.join('；')}`
                          : ''
                      }`
                }
              />
              {lastResult.import_result?.status === 'success' && (
                <Button type="link" size="small" onClick={navigateToProfile}>
                  查看系统画像
                </Button>
              )}
            </Space>
          )}
        </Space>
      </Card>
    );
  };

  const scanStatusTag = useMemo(() => {
    const status = String(scanJob?.status || '').trim();
    if (!status) {
      return null;
    }
    const color = status === 'completed' ? 'green' : status === 'failed' ? 'red' : 'processing';
    return <Tag color={color}>{status}</Tag>;
  }, [scanJob?.status]);

  const displayedHistory = useMemo(() => {
    if (historyExpanded) {
      return importHistory;
    }
    return importHistory.slice(0, 3);
  }, [importHistory, historyExpanded]);

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
              <Text type="secondary">当前系统只读，仅系统主责或 B 角 PM 可执行导入操作。</Text>
            )}
          </Space>

          {extractionStatus?.status === 'processing' && (
            <Alert
              type="info"
              showIcon
              message="AI 正在分析文档"
              description="系统正在提取文档中的结构化信息，请稍后刷新查看结果。"
            />
          )}

          {extractionStatus?.other_systems && extractionStatus.other_systems.length > 0 && (
            <Alert
              type="warning"
              showIcon
              message="检测到其他系统信息"
              description={`文档中还包含以下系统的信息：${extractionStatus.other_systems.join('、')}。如需更新请前往对应系统操作。`}
            />
          )}

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

          <Space direction="vertical" style={{ width: '100%' }} size={12}>
            {DOC_TYPE_CONFIGS.map((config) => renderDocTypeCard(config))}
          </Space>

          {importHistory.length > 0 && (
            <Card
              title="导入历史"
              size="small"
              extra={
                importHistory.length > 3 && (
                  <Button
                    type="link"
                    size="small"
                    icon={historyExpanded ? <DownOutlined /> : <RightOutlined />}
                    onClick={() => setHistoryExpanded(!historyExpanded)}
                  >
                    {historyExpanded ? '收起' : `展开全部（共 ${importHistory.length} 条）`}
                  </Button>
                )
              }
            >
              <List
                size="small"
                dataSource={displayedHistory}
                renderItem={(item) => (
                  <List.Item>
                    <Space direction="vertical" size={0} style={{ width: '100%' }}>
                      <Space>
                        <Tag color={item.status === 'success' ? 'green' : 'red'}>
                          {item.status === 'success' ? '成功' : '失败'}
                        </Tag>
                        <Text strong>{item.doc_type}</Text>
                        <Text type="secondary">{item.file_name}</Text>
                      </Space>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {formatDateTime(item.imported_at)} · 操作人: {item.operator_id}
                      </Text>
                      {item.failure_reason && (
                        <Text type="danger" style={{ fontSize: 12 }}>
                          失败原因: {item.failure_reason}
                        </Text>
                      )}
                    </Space>
                  </List.Item>
                )}
              />
            </Card>
          )}
        </Space>
      )}
    </div>
  );
};

export default SystemProfileImportPage;
