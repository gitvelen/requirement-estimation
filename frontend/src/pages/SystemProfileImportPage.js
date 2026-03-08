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
  CheckCircleFilled,
  CloudUploadOutlined,
  CloseCircleFilled,
  DownOutlined,
  ExclamationCircleFilled,
  FileTextOutlined,
  InfoCircleFilled,
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
import { extractErrorMessage } from '../utils/errorMessage';

const { Text } = Typography;

const DOC_TYPE_ESB = 'esb';
const DOC_TYPE_HISTORY_REPORT = 'history_report';
const DOC_TEMPLATE_TYPE_MAP = {
  [DOC_TYPE_HISTORY_REPORT]: 'history_report',
  [DOC_TYPE_ESB]: 'esb_document',
};
const DOC_TEMPLATE_FILE_NAME_MAP = {
  [DOC_TYPE_HISTORY_REPORT]: '工作量评估模板.xlsx',
  [DOC_TYPE_ESB]: '接口申请模板.xlsx',
};

const DOC_TYPE_CONFIGS = [
  { value: 'requirements', label: '需求文档', description: '需求规格说明、用户故事等' },
  { value: 'design', label: '设计文档', description: '概要设计、详细设计等' },
  { value: 'tech_solution', label: '技术方案', description: '技术选型、架构设计等' },
  { value: 'history_report', label: '历史评估报告', description: '过往项目评估结果' },
  { value: DOC_TYPE_ESB, label: 'ESB服务治理文档', description: 'ESB接口申请模板（xlsx/csv）' },
];

const EXTRACTION_POLL_INTERVAL = 5000;
const EXTRACTION_POLL_MAX_ATTEMPTS = 10;
const WS_HEARTBEAT_INTERVAL = 30000;

const normalizeExtractionStatus = (status) => {
  const normalized = String(status || '').trim().toLowerCase();
  if (!normalized) {
    return '';
  }
  if (normalized === 'pending' || normalized === 'processing' || normalized === 'extraction_started') {
    return 'extraction_started';
  }
  if (normalized === 'completed' || normalized === 'extraction_completed') {
    return 'extraction_completed';
  }
  if (normalized === 'failed' || normalized === 'extraction_failed') {
    return 'extraction_failed';
  }
  return normalized;
};

const isTerminalExtractionStatus = (status) => {
  const normalized = normalizeExtractionStatus(status);
  return normalized === 'extraction_completed' || normalized === 'extraction_failed' || normalized === 'timeout';
};

const extractDownloadFileName = (headers, fallback) => {
  const contentDisposition = String(headers?.['content-disposition'] || headers?.['Content-Disposition'] || '').trim();
  const matched = contentDisposition.match(/filename\*?=(?:UTF-8''|")?([^";]+)/i);
  if (!matched || !matched[1]) {
    return fallback;
  }
  try {
    return decodeURIComponent(matched[1].replace(/"/g, '').trim()) || fallback;
  } catch (error) {
    return matched[1].replace(/"/g, '').trim() || fallback;
  }
};

const buildSystemProfileWsUrl = (systemName, authToken) => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const base = `${protocol}//${window.location.host}`;
  return `${base}/ws/system-profile/${encodeURIComponent(systemName)}?token=${encodeURIComponent(authToken)}`;
};

const formatExtractionNotification = (notification) => {
  if (typeof notification === 'string') {
    return notification.trim();
  }
  if (!notification || typeof notification !== 'object') {
    return '';
  }

  const messageText = String(notification.message || '').trim();
  if (messageText) {
    return messageText;
  }

  const systems = Array.isArray(notification.systems)
    ? notification.systems.map((item) => String(item || '').trim()).filter(Boolean)
    : [];
  if (systems.length > 0) {
    return `检测到文档中还包含系统 ${systems.join('、')} 的信息，如需更新请前往对应系统操作`;
  }

  const typeText = String(notification.type || '').trim();
  if (typeText) {
    return typeText;
  }

  try {
    const serialized = JSON.stringify(notification);
    return serialized === '{}' ? '' : serialized;
  } catch (error) {
    return '';
  }
};

const formatExtractionNotifications = (notifications) => (
  Array.isArray(notifications)
    ? notifications.map(formatExtractionNotification).filter(Boolean)
    : []
);

const EXTRACTION_STATUS_STYLES = {
  info: {
    icon: InfoCircleFilled,
    color: '#1677ff',
    background: '#f3f8ff',
    border: '#d6e4ff',
  },
  success: {
    icon: CheckCircleFilled,
    color: '#389e0d',
    background: '#f6ffed',
    border: '#b7eb8f',
  },
  warning: {
    icon: ExclamationCircleFilled,
    color: '#d48806',
    background: '#fffbe6',
    border: '#ffe58f',
  },
  error: {
    icon: CloseCircleFilled,
    color: '#cf1322',
    background: '#fff2f0',
    border: '#ffccc7',
  },
};

const SystemProfileImportPage = () => {
  const { user, token } = useAuth();
  const { isManager } = usePermission();
  const location = useLocation();
  const navigate = useNavigate();

  const [systems, setSystems] = useState([]);
  const [selectedSystemName, setSelectedSystemName] = useState(() => String(new URLSearchParams(location.search).get('system_name') || '').trim());

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
  const pollAttemptRef = useRef(0);
  const wsRef = useRef(null);
  const wsHeartbeatTimerRef = useRef(null);
  const manualWsCloseRef = useRef(false);
  const trackedTaskRef = useRef({ taskId: '', systemId: '', systemName: '' });
  const extractionStatusRef = useRef(null);

  const queryParams = useMemo(() => new URLSearchParams(location.search), [location.search]);

  const ownershipUser = useMemo(() => ({
    id: user?.id,
    username: user?.username,
    displayName: user?.displayName,
    display_name: user?.display_name,
  }), [user?.id, user?.username, user?.displayName, user?.display_name]);

  const responsibleSystems = useMemo(() => filterResponsibleSystems(systems, ownershipUser), [systems, ownershipUser]);

  const selectedSystem = useMemo(
    () => responsibleSystems.find((item) => item.name === selectedSystemName),
    [responsibleSystems, selectedSystemName]
  );

  const canWrite = useMemo(() => {
    if (!isManager || !selectedSystem) {
      return false;
    }
    return resolveSystemOwnership(selectedSystem, ownershipUser).canWrite;
  }, [isManager, ownershipUser, selectedSystem]);

  const selectedSystemId = useMemo(() => String(selectedSystem?.id || '').trim(), [selectedSystem?.id]);

  const scanJobStorageKey = useMemo(() => {
    const keyPart = selectedSystemId || selectedSystemName;
    return keyPart ? `systemProfile:lastScanJobId:${keyPart}` : '';
  }, [selectedSystemId, selectedSystemName]);


  useEffect(() => {
    extractionStatusRef.current = extractionStatus;
  }, [extractionStatus]);

  const loadImportHistory = useCallback(async (systemId) => {
    try {
      const response = await axios.get(`/api/v1/system-profiles/${encodeURIComponent(systemId)}/profile/import-history`, {
        params: { limit: 50, offset: 0 },
      });
      const records = response.data?.items || response.data?.records || [];
      setImportHistory(Array.isArray(records) ? records : []);
    } catch (error) {
      setImportHistory([]);
    }
  }, []);

  const clearPollTimer = useCallback(() => {
    if (pollTimerRef.current) {
      clearTimeout(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }, []);

  const clearWsHeartbeatTimer = useCallback(() => {
    if (wsHeartbeatTimerRef.current) {
      clearInterval(wsHeartbeatTimerRef.current);
      wsHeartbeatTimerRef.current = null;
    }
  }, []);

  const closeRealtimeSocket = useCallback(() => {
    clearWsHeartbeatTimer();
    if (wsRef.current) {
      manualWsCloseRef.current = true;
      try {
        wsRef.current.close();
      } catch (error) {
        manualWsCloseRef.current = false;
      }
      wsRef.current = null;
    }
  }, [clearWsHeartbeatTimer]);

  const updateTrackedTask = useCallback((taskId, systemId, systemName) => {
    trackedTaskRef.current = {
      taskId: String(taskId || '').trim(),
      systemId: String(systemId || '').trim(),
      systemName: String(systemName || '').trim(),
    };
  }, []);

  const refreshProfileAfterExtraction = useCallback(async (systemId, systemName) => {
    if (systemName) {
      try {
        await axios.get(`/api/v1/system-profiles/${encodeURIComponent(systemName)}`);
      } catch (error) {
        // 页面不直接展示画像内容，刷新失败不阻断导入页状态更新
      }
    }
    if (systemId) {
      await loadImportHistory(systemId);
    }
  }, [loadImportHistory]);

  const applyExtractionUpdate = useCallback(async (payload, source = 'ws') => {
    const fallbackTask = trackedTaskRef.current;
    const nextTaskId = String(payload?.task_id || fallbackTask.taskId || '').trim();
    const nextSystemId = String(payload?.system_id || fallbackTask.systemId || '').trim();
    const nextSystemName = String(payload?.system_name || fallbackTask.systemName || selectedSystemName || '').trim();
    const nextStatus = normalizeExtractionStatus(payload?.status);

    updateTrackedTask(nextTaskId, nextSystemId, nextSystemName);
    setExtractionStatus({
      task_id: nextTaskId,
      system_id: nextSystemId,
      system_name: nextSystemName,
      status: nextStatus,
      error: payload?.error || null,
      notifications: Array.isArray(payload?.notifications) ? payload.notifications : [],
      other_systems: Array.isArray(payload?.other_systems) ? payload.other_systems : [],
      source,
      poll_attempts: pollAttemptRef.current,
    });

    if (isTerminalExtractionStatus(nextStatus)) {
      clearPollTimer();
      pollAttemptRef.current = 0;
      if (nextStatus === 'extraction_completed') {
        await refreshProfileAfterExtraction(nextSystemId, nextSystemName);
      }
    }
  }, [clearPollTimer, refreshProfileAfterExtraction, selectedSystemName, updateTrackedTask]);

  const pollTaskStatus = useCallback(async (taskId, systemId, systemName) => {
    const normalizedTaskId = String(taskId || '').trim();
    if (!normalizedTaskId) {
      return;
    }

    pollAttemptRef.current += 1;
    try {
      const response = await axios.get(`/api/v1/system-profiles/task-status/${encodeURIComponent(normalizedTaskId)}`);
      const payload = response.data || {};
      await applyExtractionUpdate(
        {
          ...payload,
          task_id: payload?.task_id || normalizedTaskId,
          system_id: payload?.system_id || systemId,
          system_name: payload?.system_name || systemName,
        },
        'poll'
      );

      if (isTerminalExtractionStatus(payload?.status)) {
        return;
      }

      if (pollAttemptRef.current >= EXTRACTION_POLL_MAX_ATTEMPTS) {
        setExtractionStatus({
          task_id: normalizedTaskId,
          system_id: String(systemId || '').trim(),
          system_name: String(systemName || '').trim(),
          status: 'timeout',
          error: null,
          notifications: [],
          other_systems: [],
          source: 'poll',
          poll_attempts: pollAttemptRef.current,
        });
        clearPollTimer();
        return;
      }

      pollTimerRef.current = setTimeout(() => {
        pollTaskStatus(normalizedTaskId, systemId, systemName);
      }, EXTRACTION_POLL_INTERVAL);
    } catch (error) {
      setExtractionStatus({
        task_id: normalizedTaskId,
        system_id: String(systemId || '').trim(),
        system_name: String(systemName || '').trim(),
        status: 'extraction_failed',
        error: extractErrorMessage(error, '任务状态查询失败'),
        notifications: [],
        other_systems: [],
        source: 'poll',
        poll_attempts: pollAttemptRef.current,
      });
      clearPollTimer();
    }
  }, [applyExtractionUpdate, clearPollTimer]);

  const startPollingFallback = useCallback((reason = 'WebSocket 不可用') => {
    const { taskId, systemId, systemName } = trackedTaskRef.current;
    if (!taskId || isTerminalExtractionStatus(extractionStatusRef.current?.status)) {
      return;
    }

    clearPollTimer();
    pollAttemptRef.current = 0;
    setExtractionStatus((prev) => ({
      task_id: taskId,
      system_id: systemId,
      system_name: systemName,
      status: normalizeExtractionStatus(prev?.status) || 'extraction_started',
      error: prev?.error || null,
      notifications: Array.isArray(prev?.notifications) ? prev.notifications : [],
      other_systems: Array.isArray(prev?.other_systems) ? prev.other_systems : [],
      source: 'poll',
      poll_attempts: 0,
      fallback_reason: reason,
    }));
    pollTimerRef.current = setTimeout(() => {
      pollTaskStatus(taskId, systemId, systemName);
    }, EXTRACTION_POLL_INTERVAL);
  }, [clearPollTimer, pollTaskStatus]);

  const connectRealtimeSocket = useCallback((systemName, systemId) => {
    const authToken = String(token || localStorage.getItem('AUTH_TOKEN') || '').trim();
    const normalizedSystemName = String(systemName || '').trim();
    if (!normalizedSystemName || !authToken || typeof window === 'undefined' || typeof window.WebSocket !== 'function') {
      return;
    }

    closeRealtimeSocket();

    const socket = new window.WebSocket(buildSystemProfileWsUrl(normalizedSystemName, authToken));
    wsRef.current = socket;

    socket.onopen = () => {
      clearWsHeartbeatTimer();
      wsHeartbeatTimerRef.current = setInterval(() => {
        if (socket.readyState === 1) {
          socket.send(JSON.stringify({ event: 'ping' }));
        }
      }, WS_HEARTBEAT_INTERVAL);
    };

    socket.onmessage = async (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (String(payload?.event || '').trim().toLowerCase() === 'pong') {
          return;
        }
        const payloadSystemName = String(payload?.system_name || normalizedSystemName).trim();
        if (payloadSystemName && payloadSystemName !== normalizedSystemName) {
          return;
        }
        await applyExtractionUpdate(
          {
            ...payload,
            system_id: payload?.system_id || systemId,
            system_name: payloadSystemName || normalizedSystemName,
          },
          'ws'
        );
      } catch (error) {
        // 忽略无法解析的消息，避免阻塞后续状态推送
      }
    };

    socket.onerror = () => {
      if (trackedTaskRef.current.taskId) {
        startPollingFallback('WebSocket 连接失败，已切换为 5 秒轮询');
      }
    };

    socket.onclose = () => {
      clearWsHeartbeatTimer();
      if (manualWsCloseRef.current) {
        manualWsCloseRef.current = false;
        return;
      }
      if (trackedTaskRef.current.taskId && !isTerminalExtractionStatus(extractionStatusRef.current?.status)) {
        startPollingFallback('WebSocket 已断开，已切换为 5 秒轮询');
      }
    };
  }, [applyExtractionUpdate, clearWsHeartbeatTimer, closeRealtimeSocket, startPollingFallback, token]);

  const loadCurrentExtractionStatus = useCallback(async (systemId, systemName) => {
    const normalizedSystemId = String(systemId || '').trim();
    if (!normalizedSystemId) {
      return;
    }
    try {
      const response = await axios.get(`/api/v1/system-profiles/${encodeURIComponent(normalizedSystemId)}/profile/extraction-status`);
      const payload = response.data || {};
      const nextTaskId = String(payload?.task_id || '').trim();
      const nextStatus = normalizeExtractionStatus(payload?.status);
      if (!nextTaskId) {
        updateTrackedTask('', normalizedSystemId, systemName);
        setExtractionStatus(null);
        return;
      }

      updateTrackedTask(nextTaskId, normalizedSystemId, systemName);
      setExtractionStatus({
        task_id: nextTaskId,
        system_id: normalizedSystemId,
        system_name: String(systemName || '').trim(),
        status: nextStatus,
        error: payload?.error || null,
        notifications: Array.isArray(payload?.notifications) ? payload.notifications : [],
        other_systems: Array.isArray(payload?.other_systems) ? payload.other_systems : [],
        source: 'resume',
        poll_attempts: 0,
      });
    } catch (error) {
      setExtractionStatus(null);
    }
  }, [updateTrackedTask]);

  const handleDownloadTemplate = useCallback(async (docType) => {
    const templateType = DOC_TEMPLATE_TYPE_MAP[docType];
    if (!templateType) {
      return;
    }

    setDocStates((prev) => ({
      ...prev,
      [docType]: {
        ...prev[docType],
        templateDownloading: true,
        templateFeedback: null,
      },
    }));

    try {
      const response = await axios.get(`/api/v1/system-profiles/template/${templateType}`, { responseType: 'blob' });
      const blob = response.data instanceof Blob ? response.data : new Blob([response.data]);
      const downloadUrl = window.URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = downloadUrl;
      anchor.download = extractDownloadFileName(response.headers, DOC_TEMPLATE_FILE_NAME_MAP[docType] || 'template.xlsx');
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.URL.revokeObjectURL(downloadUrl);

      setDocStates((prev) => ({
        ...prev,
        [docType]: {
          ...prev[docType],
          templateDownloading: false,
          templateFeedback: { type: 'success', message: '模板下载成功' },
        },
      }));
    } catch (error) {
      setDocStates((prev) => ({
        ...prev,
        [docType]: {
          ...prev[docType],
          templateDownloading: false,
          templateFeedback: { type: 'error', message: '模板下载失败' },
        },
      }));
    }
  }, []);

  const loadSystems = useCallback(async () => {
    try {
      const response = await axios.get('/api/v1/system/systems');
      const items = response.data?.data?.systems || [];
      setSystems(items);
    } catch (error) {
      message.error(extractErrorMessage(error, '加载系统清单失败'));
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
      message.error(extractErrorMessage(error, '加载扫描任务状态失败'));
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
    clearPollTimer();
    updateTrackedTask('', selectedSystemId, selectedSystemName);

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
  }, [clearPollTimer, fetchScanJob, scanJobStorageKey, selectedSystemId, selectedSystemName, updateTrackedTask]);

  useEffect(() => {
    const systemId = selectedSystemId;
    if (!systemId) {
      return;
    }
    loadImportHistory(systemId);
    loadCurrentExtractionStatus(systemId, selectedSystemName);
  }, [loadCurrentExtractionStatus, loadImportHistory, selectedSystemId, selectedSystemName]);

  useEffect(() => {
    const systemId = selectedSystemId;
    if (!selectedSystemName || !systemId) {
      closeRealtimeSocket();
      return undefined;
    }

    connectRealtimeSocket(selectedSystemName, systemId);
    return () => {
      closeRealtimeSocket();
    };
  }, [closeRealtimeSocket, connectRealtimeSocket, selectedSystemId, selectedSystemName]);

  useEffect(() => {
    return () => {
      clearPollTimer();
      closeRealtimeSocket();
    };
  }, [clearPollTimer, closeRealtimeSocket]);

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

      message.success(result.extraction_task_id ? '文档已上传，正在分析' : '文档导入完成');
      loadImportHistory(systemId);

      if (result.extraction_task_id) {
        clearPollTimer();
        pollAttemptRef.current = 0;
        updateTrackedTask(result.extraction_task_id, systemId, selectedSystemName);
        setExtractionStatus({
          task_id: result.extraction_task_id,
          system_id: systemId,
          system_name: selectedSystemName,
          status: 'extraction_started',
          error: null,
          notifications: [],
          other_systems: [],
          source: wsRef.current ? 'ws' : 'submitted',
          poll_attempts: 0,
        });
        if (!wsRef.current) {
          startPollingFallback('WebSocket 不可用，已切换为 5 秒轮询');
        }
      }
    } catch (error) {
      setDocStates((prev) => ({
        ...prev,
        [docType]: { ...prev[docType], submitting: false },
      }));
      message.error(extractErrorMessage(error, '文档导入失败'));
    }
  }, [clearPollTimer, docStates, loadImportHistory, selectedSystem, selectedSystemName, startPollingFallback, updateTrackedTask]);

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
      message.error(extractErrorMessage(error, '触发代码扫描失败'));
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
        loadCurrentExtractionStatus(systemId, selectedSystemName);
      }
    } catch (error) {
      message.error(extractErrorMessage(error, '扫描结果入库失败'));
    } finally {
      setScanIngesting(false);
    }
  };

  const navigateToProfile = useCallback(() => {
    const systemId = String(selectedSystem?.id || '').trim();
    if (!systemId) {
      return;
    }
    navigate(`/system-profiles/board?system_id=${encodeURIComponent(systemId)}&system_name=${encodeURIComponent(selectedSystemName)}`);
  }, [selectedSystem, selectedSystemName, navigate]);

  const renderDocTypeCard = (config) => {
    const { value: docType, label, description } = config;
    const state = docStates[docType] || {};
    const files = state.files || [];
    const submitting = state.submitting || false;
    const lastResult = state.lastResult || null;
    const templateDownloading = state.templateDownloading || false;
    const templateFeedback = state.templateFeedback || null;
    const templateType = DOC_TEMPLATE_TYPE_MAP[docType];

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
            {templateType && (
              <Button
                loading={templateDownloading}
                disabled={!canWrite}
                aria-label={`下载${label}模板`}
                onClick={() => handleDownloadTemplate(docType)}
              >
                下载模板
              </Button>
            )}
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

          {templateFeedback && (
            <Alert type={templateFeedback.type} showIcon message={templateFeedback.message} />
          )}

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

  const extractionAlert = useMemo(() => {
    const status = normalizeExtractionStatus(extractionStatus?.status);
    if (!status) {
      return null;
    }

    const notifications = formatExtractionNotifications(extractionStatus?.notifications);
    const otherSystems = Array.isArray(extractionStatus?.other_systems)
      ? extractionStatus.other_systems.map((item) => String(item || '').trim()).filter(Boolean)
      : [];
    const source = String(extractionStatus?.source || '').trim();

    if (status === 'extraction_started') {
      return {
        type: 'info',
        message: 'AI 正在分析文档',
        description: source === 'poll'
          ? `${extractionStatus?.fallback_reason || 'WebSocket 不可用'}（已轮询 ${extractionStatus?.poll_attempts || 0}/${EXTRACTION_POLL_MAX_ATTEMPTS} 次）`
          : '系统正在提取文档中的结构化信息，完成后将自动刷新画像与导入历史。',
      };
    }

    if (status === 'extraction_completed') {
      return {
        type: 'success',
        message: 'AI 已完成分析',
        description: notifications.join('；') || '画像与导入历史已自动刷新。',
      };
    }

    if (status === 'extraction_failed') {
      return {
        type: 'error',
        message: 'AI 分析失败',
        description: String(extractionStatus?.error || '').trim() || notifications.join('；') || '请稍后重试。',
      };
    }

    if (status === 'timeout') {
      return {
        type: 'warning',
        message: '任务处理超时，请稍后手动刷新',
        description: `已按 5 秒间隔轮询 ${EXTRACTION_POLL_MAX_ATTEMPTS} 次，仍未收到终态。`,
      };
    }

    if (otherSystems.length > 0) {
      return {
        type: 'warning',
        message: '检测到其他系统信息',
        description: `文档中还包含以下系统的信息：${otherSystems.join('、')}。如需更新请前往对应系统操作。`,
      };
    }

    return null;
  }, [extractionStatus]);

  const extractionStatusStrip = useMemo(() => {
    if (!extractionAlert) {
      return null;
    }

    const tone = EXTRACTION_STATUS_STYLES[extractionAlert.type] || EXTRACTION_STATUS_STYLES.info;
    const StatusIcon = tone.icon;

    return (
      <div
        data-testid="extraction-status-strip"
        role="status"
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          gap: 8,
          padding: '8px 12px',
          borderRadius: 8,
          border: `1px solid ${tone.border}`,
          background: tone.background,
        }}
      >
        <StatusIcon style={{ color: tone.color, fontSize: 16, lineHeight: '20px', marginTop: 2 }} />
        <div style={{ minWidth: 0, flex: 1 }}>
          <div style={{ color: 'rgba(0, 0, 0, 0.88)', fontWeight: 500, lineHeight: '20px' }}>
            {extractionAlert.message}
          </div>
          {extractionAlert.description ? (
            <Text type="secondary" style={{ display: 'block', marginTop: 2, lineHeight: '20px' }}>
              {extractionAlert.description}
            </Text>
          ) : null}
        </div>
      </div>
    );
  }, [extractionAlert]);

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

          {extractionStatusStrip}

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
            <Space direction="vertical" style={{ width: '100%' }} size={12}>
              {DOC_TYPE_CONFIGS.map((config) => renderDocTypeCard(config))}
            </Space>
          </Card>

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
