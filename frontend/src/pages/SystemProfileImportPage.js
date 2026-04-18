import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Descriptions,
  Input,
  List,
  Space,
  Tag,
  Typography,
  Upload,
  message,
} from 'antd';
import {
  CloudUploadOutlined,
  FileTextOutlined,
  PlayCircleOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useLocation, useNavigate } from 'react-router-dom';
import axios from 'axios';
import useAuth from '../hooks/useAuth';
import usePermission from '../hooks/usePermission';
import { formatDateTime } from '../utils/time';
import { extractErrorMessage } from '../utils/errorMessage';
import { filterResponsibleSystems, resolveSystemOwnership } from '../utils/systemOwnership';

const { Text } = Typography;

const DOC_TYPE_CONFIGS = [
  { value: 'requirements', label: '需求文档', description: '需求规格说明、用户故事等' },
  { value: 'design', label: '设计文档', description: '概要设计、详细设计等' },
  { value: 'tech_solution', label: '技术方案', description: '技术选型、架构设计等' },
  { value: 'general', label: '综合文档', description: '自动判型后按多域编译处理' },
];
const DOC_TYPE_LABELS = Object.fromEntries(DOC_TYPE_CONFIGS.map((item) => [item.value, item.label]));

const EXECUTION_STATUS_META = {
  queued: { color: 'default', tagColor: 'default', text: '排队中' },
  running: { color: 'processing', tagColor: 'processing', text: '执行中' },
  completed: { color: 'green', tagColor: 'success', text: '已完成' },
  partial_success: { color: 'gold', tagColor: 'warning', text: '部分成功' },
  failed: { color: 'red', tagColor: 'error', text: '失败' },
};

const normalizeStatus = (value, fallback = 'completed') => String(value || fallback).trim().toLowerCase();

const getDocTypeLabel = (docType) => DOC_TYPE_LABELS[docType] || String(docType || '未分类文档').trim() || '未分类文档';

const getExecutionStatusSummary = (executionStatus) => {
  const normalizedStatus = normalizeStatus(executionStatus?.status);
  const statusMeta = EXECUTION_STATUS_META[normalizedStatus] || EXECUTION_STATUS_META.completed;
  const completedAt = formatDateTime(executionStatus?.completed_at || executionStatus?.created_at);

  if (executionStatus?.error) {
    return {
      tagColor: statusMeta.tagColor,
      message: `最近一次处理${statusMeta.text}`,
      description: executionStatus.error,
    };
  }

  if (normalizedStatus === 'queued' || normalizedStatus === 'running') {
    return {
      tagColor: statusMeta.tagColor,
      message: `最近一次处理${statusMeta.text}`,
      description: '系统正在处理中，可稍后刷新查看。',
    };
  }

  return {
    tagColor: statusMeta.tagColor,
    message: `最近一次处理${statusMeta.text}`,
    description: completedAt ? `完成时间：${completedAt}` : '可前往信息展示页查看最新结果。',
  };
};

const getBatchImportSummary = (batchResult) => {
  const successCount = Number(batchResult?.success_count || 0);
  const failureCount = Number(batchResult?.failure_count || 0);
  const batchCount = Number(batchResult?.batch_count || 0);
  if (failureCount > 0) {
    return {
      textType: 'warning',
      text: `本次批量导入共 ${batchCount} 个文件，成功 ${successCount} 个，失败 ${failureCount} 个。`,
    };
  }
  return {
    textType: 'secondary',
    text: `本次批量导入已提交 ${successCount || batchCount} 个文件，可前往信息展示查看建议。`,
  };
};

const getImportStatusTag = (status) => {
  const normalizedStatus = normalizeStatus(status, 'success');
  if (normalizedStatus === 'success' || normalizedStatus === 'completed') {
    return { color: 'green', text: '成功' };
  }
  if (normalizedStatus === 'running' || normalizedStatus === 'queued') {
    return { color: 'blue', text: '处理中' };
  }
  return { color: 'red', text: '失败' };
};

const getRepoSourceLabel = (repoSource) => {
  const normalizedSource = String(repoSource || '').trim().toLowerCase();
  if (normalizedSource === 'archive') {
    return '压缩包上传';
  }
  if (normalizedSource === 'path') {
    return '本地路径';
  }
  return repoSource || '-';
};

const SystemProfileImportPage = () => {
  const { user } = useAuth();
  const { isManager } = usePermission();
  const location = useLocation();
  const navigate = useNavigate();

  const [systems, setSystems] = useState([]);
  const [selectedSystemName, setSelectedSystemName] = useState('');
  const [batchFiles, setBatchFiles] = useState([]);
  const [batchSubmitting, setBatchSubmitting] = useState(false);
  const [batchResult, setBatchResult] = useState(null);
  const [importHistory, setImportHistory] = useState([]);
  const [executionStatus, setExecutionStatus] = useState(null);

  // 性能优化：添加缓存
  const [importHistoryCache, setImportHistoryCache] = useState({});
  const [executionStatusCache, setExecutionStatusCache] = useState({});

  // 性能优化：添加分页状态
  const [historyPage, setHistoryPage] = useState(1);
  const [historyPageSize] = useState(10);

  const [scanRepoPath, setScanRepoPath] = useState('');
  const [scanArchiveFiles, setScanArchiveFiles] = useState([]);
  const [scanSubmitting, setScanSubmitting] = useState(false);
  const [scanRefreshing, setScanRefreshing] = useState(false);
  const [scanIngesting, setScanIngesting] = useState(false);
  const [scanJob, setScanJob] = useState(null);
  const [scanIngestResult, setScanIngestResult] = useState(null);

  const queryParams = useMemo(() => new URLSearchParams(location.search), [location.search]);
  const requestedSystemName = useMemo(() => String(queryParams.get('system_name') || '').trim(), [queryParams]);
  const requestedSystemId = useMemo(() => String(queryParams.get('system_id') || '').trim(), [queryParams]);
  const responsibleSystems = useMemo(() => {
    const filteredSystems = filterResponsibleSystems(systems, user);
    if (filteredSystems.length > 0) {
      return filteredSystems;
    }
    if (!isManager || !requestedSystemName) {
      return [];
    }
    return systems.filter((item) => item.name === requestedSystemName);
  }, [isManager, requestedSystemName, systems, user]);
  const effectiveSystems = useMemo(() => {
    if (responsibleSystems.length > 0) {
      return responsibleSystems;
    }
    if (!requestedSystemName) {
      return [];
    }
    return [
      {
        id: requestedSystemId || requestedSystemName,
        name: requestedSystemName,
        extra: { owner_username: user?.username || '' },
      },
    ];
  }, [requestedSystemId, requestedSystemName, responsibleSystems, user?.username]);
  const selectedSystem = useMemo(
    () => effectiveSystems.find((item) => item.name === selectedSystemName),
    [effectiveSystems, selectedSystemName]
  );
  const selectedSystemId = useMemo(() => String(selectedSystem?.id || '').trim(), [selectedSystem?.id]);
  const canWrite = useMemo(() => {
    if (!isManager || !selectedSystem) {
      return false;
    }
    return resolveSystemOwnership(selectedSystem, user).canWrite;
  }, [isManager, selectedSystem, user]);

  // 性能优化：分页数据计算
  const paginatedHistory = useMemo(() => {
    const startIndex = (historyPage - 1) * historyPageSize;
    return importHistory.slice(startIndex, startIndex + historyPageSize);
  }, [importHistory, historyPage, historyPageSize]);

  const loadSystems = useCallback(async () => {
    try {
      const response = await axios.get('/api/v1/system/systems');
      const items = response.data?.data?.systems || [];
      setSystems(Array.isArray(items) ? items : []);
    } catch (error) {
      message.error(extractErrorMessage(error, '加载系统清单失败'));
    }
  }, []);

  const loadImportHistory = useCallback(async (systemId) => {
    if (!systemId) {
      setImportHistory([]);
      return;
    }

    // 检查缓存（5分钟有效期）
    const cached = importHistoryCache[systemId];
    if (cached && Date.now() - cached.timestamp < 5 * 60 * 1000) {
      setImportHistory(cached.data);
      return;
    }

    try {
      const response = await axios.get(`/api/v1/system-profiles/${encodeURIComponent(systemId)}/profile/import-history`);
      const data = Array.isArray(response.data?.items) ? response.data.items : [];
      setImportHistory(data);

      // 更新缓存
      setImportHistoryCache(prev => ({
        ...prev,
        [systemId]: { data, timestamp: Date.now() }
      }));
    } catch (error) {
      setImportHistory([]);
    }
  }, [importHistoryCache]);

  const loadExecutionStatus = useCallback(async (systemId) => {
    if (!systemId) {
      setExecutionStatus(null);
      return;
    }

    // 检查缓存（5分钟有效期）
    const cached = executionStatusCache[systemId];
    if (cached && Date.now() - cached.timestamp < 5 * 60 * 1000) {
      setExecutionStatus(cached.data);
      return;
    }

    try {
      const response = await axios.get(`/api/v1/system-profiles/${encodeURIComponent(systemId)}/profile/execution-status`);
      const data = response.data || null;
      setExecutionStatus(data);

      // 更新缓存
      setExecutionStatusCache(prev => ({
        ...prev,
        [systemId]: { data, timestamp: Date.now() }
      }));
    } catch (error) {
      setExecutionStatus(null);
    }
  }, [executionStatusCache]);

  const loadScanJob = useCallback(async (jobId) => {
    const normalizedJobId = String(jobId || '').trim();
    if (!normalizedJobId) {
      setScanJob(null);
      return;
    }

    setScanRefreshing(true);
    try {
      const response = await axios.get(`/api/v1/code-scan/jobs/${encodeURIComponent(normalizedJobId)}`);
      setScanJob(response.data || null);
    } catch (error) {
      message.error(extractErrorMessage(error, '加载扫描任务状态失败'));
      setScanJob(null);
    } finally {
      setScanRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadSystems();
  }, [loadSystems]);

  useEffect(() => {
    if (!effectiveSystems.length) {
      if (selectedSystemName) {
        setSelectedSystemName('');
      }
      return;
    }

    const existsByName = effectiveSystems.some((item) => item.name === requestedSystemName);
    const existsBySelection = selectedSystemName && effectiveSystems.some((item) => item.name === selectedSystemName);
    const nextName = existsByName
      ? requestedSystemName
      : existsBySelection
        ? selectedSystemName
        : effectiveSystems[0].name;

    if (nextName !== selectedSystemName) {
      setSelectedSystemName(nextName);
    }
  }, [effectiveSystems, requestedSystemName, selectedSystemName]);

  useEffect(() => {
    setBatchFiles([]);
    setBatchResult(null);
    setScanJob(null);
    setScanIngestResult(null);

    if (!selectedSystemId) {
      setImportHistory([]);
      setExecutionStatus(null);
      return;
    }

    loadImportHistory(selectedSystemId);
    loadExecutionStatus(selectedSystemId);
  }, [loadExecutionStatus, loadImportHistory, selectedSystemId]);

  const handleSystemChange = (systemName) => {
    const nextName = String(systemName || '').trim();
    if (!nextName) {
      return;
    }
    const nextSystem = effectiveSystems.find((item) => item.name === nextName);
    const nextParams = new URLSearchParams(location.search);
    nextParams.set('system_name', nextName);
    if (nextSystem?.id) {
      nextParams.set('system_id', String(nextSystem.id));
    } else {
      nextParams.delete('system_id');
    }
    navigate({ pathname: location.pathname, search: `?${nextParams.toString()}` }, { replace: true });
    setSelectedSystemName(nextName);
  };

  const handleBatchImport = async () => {
    if (!selectedSystemId || !selectedSystemName) {
      message.warning('请先选择系统');
      return;
    }

    if (!batchFiles.length) {
      message.warning('请上传文件');
      return;
    }

    setBatchSubmitting(true);

    try {
      const formData = new FormData();
      batchFiles.forEach((file) => {
        formData.append('files', file);
      });

      const response = await axios.post(
        `/api/v1/system-profiles/${encodeURIComponent(selectedSystemId)}/profile/import-batch`,
        formData,
        {
          headers: { 'Content-Type': 'multipart/form-data' },
        }
      );

      setBatchFiles([]);
      setBatchResult(response.data || null);

      await loadImportHistory(selectedSystemId);
      await loadExecutionStatus(selectedSystemId);
      message.success('文档批量导入已提交');
    } catch (error) {
      message.error(extractErrorMessage(error, '文档导入失败'));
    } finally {
      setBatchSubmitting(false);
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
      let response;
      if (scanArchiveFiles.length > 0) {
        const formData = new FormData();
        formData.append('system_name', selectedSystemName);
        if (selectedSystemId) {
          formData.append('system_id', selectedSystemId);
        }
        formData.append('repo_archive', scanArchiveFiles[0]);
        response = await axios.post('/api/v1/code-scan/jobs', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
      } else {
        response = await axios.post('/api/v1/code-scan/jobs', {
          system_name: selectedSystemName,
          system_id: selectedSystemId || undefined,
          repo_path: scanRepoPath.trim(),
        });
      }

      const payload = response.data || null;
      setScanJob(payload);
      setScanRepoPath('');
      setScanArchiveFiles([]);
      setScanIngestResult(null);
      message.success('代码扫描任务已提交');
    } catch (error) {
      message.error(extractErrorMessage(error, '触发代码扫描失败'));
    } finally {
      setScanSubmitting(false);
    }
  };

  const handleIngestScan = async () => {
    const jobId = String(scanJob?.job_id || '').trim();
    if (!jobId) {
      message.warning('暂无可入库的任务');
      return;
    }

    setScanIngesting(true);
    try {
      const response = await axios.post(`/api/v1/code-scan/jobs/${encodeURIComponent(jobId)}/ingest`);
      setScanIngestResult(response.data || null);
      await loadExecutionStatus(selectedSystemId);
      message.success('扫描结果已入库');
    } catch (error) {
      message.error(extractErrorMessage(error, '扫描结果入库失败'));
    } finally {
      setScanIngesting(false);
    }
  };

  const navigateToBoard = () => {
    if (!selectedSystemId || !selectedSystemName) {
      return;
    }
    navigate(`/system-profiles/board?system_id=${encodeURIComponent(selectedSystemId)}&system_name=${encodeURIComponent(selectedSystemName)}`);
  };

  const executionStatusAlert = useMemo(() => {
    if (!executionStatus) {
      return null;
    }

    const summary = getExecutionStatusSummary(executionStatus);
    return (
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          flexWrap: 'wrap',
          padding: '6px 10px',
          border: '1px solid #dbe7f3',
          borderRadius: 8,
          background: '#ffffff',
        }}
      >
        <Tag color={summary.tagColor}>{summary.message}</Tag>
        <Text type={executionStatus.error ? 'danger' : 'secondary'} style={{ fontSize: 12 }}>
          {summary.description}
        </Text>
      </div>
    );
  }, [executionStatus]);

  if (effectiveSystems.length === 0) {
    return (
      <Card>
        <Text type="secondary">暂无可操作系统（仅展示主责/B角系统）。请联系管理员维护系统负责关系。</Text>
      </Card>
    );
  }

  return (
    <Space direction="vertical" style={{ width: '100%' }} size={12}>
      <Space wrap size={8}>
        {effectiveSystems.map((item) => (
          <Button
            key={item.name}
            size="small"
            type={item.name === selectedSystemName ? 'primary' : 'default'}
            onClick={() => handleSystemChange(item.name)}
          >
            {item.name}
          </Button>
        ))}
      </Space>

      {!canWrite && (
        <Text type="secondary">当前系统只读，仅系统主责或 B 角 PM 可执行导入操作。</Text>
      )}

      {executionStatusAlert}

      <Card
        title="代码扫描"
        extra={(
          <Button
            size="small"
            icon={<ReloadOutlined />}
            loading={scanRefreshing}
            disabled={!scanJob?.job_id}
            onClick={() => loadScanJob(scanJob?.job_id)}
          >
            刷新状态
          </Button>
        )}
      >
        <Space direction="vertical" size={8} style={{ width: '100%' }}>
          <Space wrap size={8}>
            <Input
              style={{ width: 360, maxWidth: '100%' }}
              value={scanRepoPath}
              disabled={!canWrite}
              placeholder="仓库本地路径（可选）"
              onChange={(event) => setScanRepoPath(event.target.value)}
            />
            <Upload
              accept=".zip,.tar,.gz,.tgz"
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
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              loading={scanSubmitting}
              disabled={!canWrite}
              onClick={handleRunScan}
            >
              提交扫描
            </Button>
          </Space>

          {scanJob?.job_id ? (
            <>
              <Descriptions
                size="small"
                column={3}
                items={[
                  { key: 'job_id', label: '任务号', children: scanJob.job_id },
                  {
                    key: 'status',
                    label: '状态',
                    children: <Tag>{(EXECUTION_STATUS_META[normalizeStatus(scanJob.status, 'queued')] || EXECUTION_STATUS_META.queued).text}</Tag>,
                  },
                  { key: 'progress', label: '进度', children: `${scanJob.progress ?? 0}%` },
                  { key: 'created_at', label: '创建时间', children: formatDateTime(scanJob.created_at) },
                  { key: 'repo_source', label: '来源', children: getRepoSourceLabel(scanJob.repo_source) },
                ]}
              />

              <Space>
                <Button
                  type="primary"
                  loading={scanIngesting}
                  disabled={!canWrite || scanJob.status !== 'completed'}
                  onClick={handleIngestScan}
                >
                  入库
                </Button>
                <Button type="link" onClick={navigateToBoard}>
                  查看系统画像
                </Button>
              </Space>

              {scanIngestResult ? (
                <Alert
                  type="success"
                  showIcon
                  message="入库结果"
                  description={`成功 ${scanIngestResult.success ?? 0}，失败 ${scanIngestResult.failed ?? 0}`}
                />
              ) : null}
            </>
          ) : (
            <Text type="secondary">暂无扫描任务。</Text>
          )}
        </Space>
      </Card>

      <Card title="文档导入">
        <Space direction="vertical" style={{ width: '100%' }} size={12}>
          <Text type="secondary">
            统一入口批量上传文档，后端会自动判型；判型不确定时按综合文档做多域编译，不直接报错。
          </Text>
          <Space wrap size={8}>
            <Upload
              multiple
              beforeUpload={(_, fileList) => {
                setBatchFiles(fileList);
                return false;
              }}
              fileList={batchFiles.map((file) => ({ uid: file.uid || file.name, name: file.name }))}
              onRemove={(file) => {
                setBatchFiles((prev) => prev.filter((item) => (item.uid || item.name) !== (file.uid || file.name)));
              }}
              disabled={!canWrite}
            >
              <Button aria-label="选择文档文件" icon={<CloudUploadOutlined />} disabled={!canWrite}>
                选择文档文件
              </Button>
            </Upload>
            <Button
              aria-label="批量导入文档"
              type="primary"
              icon={<FileTextOutlined />}
              loading={batchSubmitting}
              disabled={!canWrite || batchFiles.length === 0}
              onClick={handleBatchImport}
            >
              批量导入文档
            </Button>
          </Space>

          {batchResult ? (
            <Text type={getBatchImportSummary(batchResult).textType}>{getBatchImportSummary(batchResult).text}</Text>
          ) : null}
        </Space>
      </Card>

      {importHistory.length > 0 ? (
        <Card title="导入历史">
          <List
            size="small"
            dataSource={paginatedHistory}
            pagination={{
              current: historyPage,
              pageSize: historyPageSize,
              total: importHistory.length,
              onChange: (page) => setHistoryPage(page),
              showSizeChanger: false,
              showTotal: (total) => `共 ${total} 条记录`
            }}
            renderItem={(item) => {
              const statusTag = getImportStatusTag(item.status);
              return (
                <List.Item>
                  <Space direction="vertical" size={2} style={{ width: '100%' }}>
                    <Space wrap size={8}>
                      <Tag color={statusTag.color}>{statusTag.text}</Tag>
                      <Text strong>{getDocTypeLabel(item.doc_type)}</Text>
                      <Text type="secondary">{item.file_name}</Text>
                    </Space>
                    <Text type="secondary">{formatDateTime(item.imported_at)}</Text>
                  </Space>
                </List.Item>
              );
            }}
          />
        </Card>
      ) : null}
    </Space>
  );
};

export default SystemProfileImportPage;
