import React, { useEffect, useState } from 'react';
import { Button, Card, InputNumber, Select, Space, Typography, message } from 'antd';
import { UploadOutlined } from '@ant-design/icons';
import axios from 'axios';
import useAuth from '../hooks/useAuth';
import usePermission from '../hooks/usePermission';

const { Text } = Typography;

const METADATA_EXECUTION_OPTIONS = [
  { value: 'now', label: '现在' },
  { value: 'daily_23', label: '每天23:00' },
];

const METADATA_SCOPE_OPTIONS = [
  { value: 'new', label: '新增' },
  { value: 'stock', label: '存量' },
  { value: 'all', label: '所有' },
];

const getErrorMessage = async (error, fallback) => {
  const payload = error?.response?.data;
  if (payload instanceof Blob) {
    try {
      const text = await payload.text();
      const parsed = JSON.parse(text);
      return getErrorMessage({ response: { data: parsed } }, fallback);
    } catch (_) {
      return fallback;
    }
  }
  const detail = payload?.detail;
  const reason = payload?.details?.reason;
  const messageText = payload?.message;

  if (messageText && reason && !String(messageText).includes(String(reason))) {
    return `${messageText}：${reason}`;
  }
  if (messageText) {
    return messageText;
  }
  if (detail?.message) {
    return detail.message;
  }
  if (typeof detail === 'string' && detail) {
    return detail;
  }
  if (reason) {
    return reason;
  }
  return fallback;
};

const triggerBrowserDownload = async (response) => {
  const blob = new Blob([response.data], {
    type: response.headers?.['content-type'] || 'application/octet-stream',
  });
  const disposition = response.headers?.['content-disposition'] || '';
  const filenameMatch = disposition.match(/filename="?([^";]+)"?/i);
  const filename = filenameMatch?.[1] || 'metadata-governance.xlsx';
  const downloadUrl = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = downloadUrl;
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(downloadUrl);
};

const MetadataGovernanceToolbar = () => {
  const [threshold, setThreshold] = useState(0.8);
  const [executionTime, setExecutionTime] = useState('now');
  const [matchScope, setMatchScope] = useState('new');
  const [running, setRunning] = useState(false);
  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null); // null | 'running' | 'completed' | 'failed'

  useEffect(() => {
    let mounted = true;
    const loadConfig = async () => {
      try {
        const response = await axios.get('/api/v1/esb/metadata-governance/config');
        if (!mounted) {
          return;
        }
        setThreshold(Number(response.data?.similarity_threshold ?? 0.8));
        setExecutionTime(response.data?.execution_time || 'now');
        setMatchScope(response.data?.match_scope || 'new');
      } catch (error) {
        // 配置读取失败时保留默认值，不阻断页面使用
      }
    };
    const loadLatestJob = async () => {
      try {
        const response = await axios.get('/api/v1/esb/metadata-governance/jobs/latest');
        if (!mounted || !response.data?.job_id) {
          return;
        }
        const { job_id, status } = response.data;
        setJobId(job_id);
        if (status === 'completed') {
          setJobStatus('completed');
        } else if (status === 'failed') {
          setJobStatus('failed');
        } else if (status === 'running' || status === 'pending') {
          setJobStatus('running');
          setRunning(true);
          // Resume polling for in-progress job
          const poll = setInterval(async () => {
            try {
              const statusResp = await axios.get(
                `/api/v1/esb/metadata-governance/jobs/${job_id}`,
              );
              if (!mounted) {
                clearInterval(poll);
                return;
              }
              const { status: s, error } = statusResp.data;
              if (s === 'completed') {
                clearInterval(poll);
                setJobStatus('completed');
                setRunning(false);
                message.success('元数据治理执行完成，点击下载按钮获取结果');
              } else if (s === 'failed') {
                clearInterval(poll);
                setJobStatus('failed');
                setRunning(false);
                message.error(error || '元数据治理执行失败');
              }
            } catch (pollErr) {
              clearInterval(poll);
              setJobStatus(null);
              setRunning(false);
            }
          }, 3000);
        }
      } catch (error) {
        // 没有历史任务时静默忽略
      }
    };
    loadConfig();
    loadLatestJob();
    return () => {
      mounted = false;
    };
  }, []);

  const handleRun = async () => {
    try {
      setRunning(true);
      setJobStatus(null);
      setJobId(null);
      const response = await axios.post(
        '/api/v1/esb/metadata-governance/run',
        {
          similarity_threshold: Number(threshold),
          execution_time: executionTime,
          match_scope: matchScope,
        },
      );

      if (response.data.scheduled) {
        message.success('元数据治理配置已保存，并已启用每天23:00定时执行');
        setRunning(false);
        return;
      }

      // Async job: poll for completion
      const newJobId = response.data.job_id;
      setJobId(newJobId);
      setJobStatus('running');
      message.info('元数据治理任务已提交，正在后台执行...');

      const poll = setInterval(async () => {
        try {
          const statusResp = await axios.get(
            `/api/v1/esb/metadata-governance/jobs/${newJobId}`,
          );
          const { status, error } = statusResp.data;

          if (status === 'completed') {
            clearInterval(poll);
            setJobStatus('completed');
            setRunning(false);
            message.success('元数据治理执行完成，点击下载按钮获取结果');
          } else if (status === 'failed') {
            clearInterval(poll);
            setJobStatus('failed');
            setRunning(false);
            message.error(error || '元数据治理执行失败');
          }
        } catch (pollErr) {
          clearInterval(poll);
          setJobStatus(null);
          setRunning(false);
          message.error(await getErrorMessage(pollErr, '查询任务状态失败'));
        }
      }, 3000);
    } catch (error) {
      message.error(await getErrorMessage(error, '元数据治理执行失败'));
      setRunning(false);
    }
  };

  const handleDownload = async () => {
    try {
      const dlResp = await axios.get(
        `/api/v1/esb/metadata-governance/jobs/${jobId}/download`,
        { responseType: 'blob' },
      );
      await triggerBrowserDownload(dlResp);
      message.success('Excel 已开始下载');
    } catch (dlErr) {
      message.error(await getErrorMessage(dlErr, '下载失败'));
    }
  };

  return (
    <Space size={12} wrap={true} style={{ width: '100%' }}>
      <Button type="primary" onClick={handleRun} loading={running}>
        元数据治理
      </Button>
      <InputNumber
        value={threshold}
        min={0}
        max={1}
        step={0.01}
        precision={2}
        onChange={(value) => setThreshold(value ?? 0.8)}
      />
      <Select value={executionTime} options={METADATA_EXECUTION_OPTIONS} onChange={setExecutionTime} style={{ width: 140 }} />
      <Select value={matchScope} options={METADATA_SCOPE_OPTIONS} onChange={setMatchScope} style={{ width: 160 }} />
      {jobStatus === 'running' && <Text type="warning">分析中，请稍候...</Text>}
      {jobStatus === 'completed' && (
        <Button type="primary" style={{ background: '#52c41a', borderColor: '#52c41a' }} onClick={handleDownload}>
          下载结果
        </Button>
      )}
      {jobStatus === 'failed' && <Text type="danger">执行失败</Text>}
    </Space>
  );
};

const ServiceGovernancePage = () => {
  const { user } = useAuth();
  const { isAdmin } = usePermission();
  const [fileList, setFileList] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);

  const isEsbAdmin = Boolean(
    isAdmin && (String(user?.username || '').trim() === 'esb' || String(user?.displayName || '').trim() === 'esb')
  );
  const selectedFile = fileList[0] || null;
  const updatedSystems = Array.isArray(result?.updated_systems) && result.updated_systems.length > 0
    ? result.updated_systems
    : (result?.updated_system_ids || []).map((item) => ({ system_id: item, system_name: item }));

  const handleImport = async () => {
    if (!selectedFile) {
      message.warning('请先选择服务治理文件');
      return;
    }

    try {
      setSubmitting(true);
      const formData = new FormData();
      formData.append('file', selectedFile);
      const response = await axios.post('/api/v1/esb/imports', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setResult(response.data || null);
      message.success('服务治理导入已完成');
    } catch (error) {
      message.error(await getErrorMessage(error, '服务治理导入失败'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <div style={{ padding: '4px 0 8px' }}>
        <Space direction="vertical" size={12} style={{ width: '100%' }}>
          <Text type="secondary">
            导入服务治理清单后，系统会按标准系统名匹配并联动更新画像；未匹配项会保留在结果区。
          </Text>
          <input
            type="file"
            accept=".xlsx,.xls,.csv"
            onChange={(event) => {
              const nextFile = event.target.files?.[0] || null;
              setFileList(nextFile ? [nextFile] : []);
            }}
          />

          <Button
            type="primary"
            icon={<UploadOutlined />}
            aria-label="开始导入"
            loading={submitting}
            disabled={!selectedFile}
            onClick={handleImport}
          >
            开始导入
          </Button>

          {isEsbAdmin ? <MetadataGovernanceToolbar /> : null}
        </Space>
      </div>

      {result ? (
        <Card title="导入结果">
          <Space direction="vertical" size={12} style={{ width: '100%' }}>
            <Space wrap size={16}>
              <Text strong>{`匹配成功 ${result.matched_count || 0} 条`}</Text>
              <Text strong>{`未匹配 ${result.unmatched_count || 0} 条`}</Text>
            </Space>

            <div>
              <Text strong>已更新系统</Text>
              {updatedSystems.length === 0 ? (
                <div style={{ marginTop: 8 }}>
                  <Text type="secondary">本次没有命中可更新系统。</Text>
                </div>
              ) : (
                <ul style={{ margin: '8px 0 0', paddingLeft: 20 }}>
                  {updatedSystems.map((item) => (
                    <li key={item.system_id || item.system_name}>{item.system_name || item.system_id || '-'}</li>
                  ))}
                </ul>
              )}
            </div>

            <div>
              <Text strong>未匹配项</Text>
              {(result.unmatched_items || []).length === 0 ? (
                <div style={{ marginTop: 8 }}>
                  <Text type="secondary">本次没有未匹配项。</Text>
                </div>
              ) : (
                <ul style={{ margin: '8px 0 0', paddingLeft: 20 }}>
                  {(result.unmatched_items || []).map((item, index) => (
                    <li key={`${item.system_name || 'item'}-${index}`}>
                      <div><strong>{item.system_name || '-'}</strong></div>
                      <div style={{ color: 'rgba(0, 0, 0, 0.45)' }}>{item.service_name || '-'}</div>
                      <div style={{ color: 'rgba(0, 0, 0, 0.45)' }}>{item.reason || '-'}</div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </Space>
        </Card>
      ) : null}
    </Space>
  );
};

export default ServiceGovernancePage;
