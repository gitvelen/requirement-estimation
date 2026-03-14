import React, { useState } from 'react';
import { Alert, Button, Card, Space, Switch, Typography, message } from 'antd';
import { DownloadOutlined, UploadOutlined } from '@ant-design/icons';
import axios from 'axios';
import MainSystemConfigPage from './MainSystemConfigPage';

const { Text } = Typography;

const EMPTY_RESULT = {
  preview_errors: [],
  updated_system_ids: [],
  updated_systems: [],
  skipped_items: [],
  errors: [],
};

const SKIP_REASON_LABELS = {
  profile_not_blank: '画像已有内容，已跳过初始化',
  profile_not_found: '未找到对应系统，已跳过初始化',
  mapping_incomplete: '系统清单信息不完整，已跳过初始化',
};

const getErrorMessage = (error, fallback) => {
  const payload = error?.response?.data;
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

const SystemListConfigPage = () => {
  const [importVisible, setImportVisible] = useState(false);
  const [importFile, setImportFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [replaceMode, setReplaceMode] = useState(true);
  const [parsing, setParsing] = useState(false);
  const [importing, setImporting] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [catalogImportResult, setCatalogImportResult] = useState(null);

  const resetImportPanel = () => {
    setImportFile(null);
    setPreview(null);
    setReplaceMode(true);
  };

  const downloadTemplate = async () => {
    try {
      const response = await axios.get('/api/v1/system-list/template', { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'syslist-template.xlsx');
      document.body.appendChild(link);
      link.click();
      link.remove();
      message.success('模板已下载');
    } catch (error) {
      message.error(getErrorMessage(error, '下载模板失败'));
    }
  };

  const parseImport = async (selectedFile = importFile, { showSuccess = false } = {}) => {
    if (!selectedFile) {
      message.warning('请先选择Excel文件');
      return null;
    }

    try {
      setParsing(true);
      const formData = new FormData();
      formData.append('file', selectedFile);
      const response = await axios.post('/api/v1/system-list/batch-import', formData);
      const nextPreview = response.data?.data || null;
      setPreview(nextPreview);
      if (showSuccess) {
        message.success('预检完成');
      }
      return nextPreview;
    } catch (error) {
      message.error(getErrorMessage(error, '预检失败'));
      return null;
    } finally {
      setParsing(false);
    }
  };

  const confirmImport = async () => {
    const currentPreview = preview || await parseImport();
    if (!currentPreview) {
      return;
    }

    try {
      setImporting(true);
      const response = await axios.post('/api/v1/system-list/batch-import/confirm', {
        mode: replaceMode ? 'replace' : 'upsert',
        systems: currentPreview.systems || [],
      });
      setCatalogImportResult({
        ...EMPTY_RESULT,
        ...(response.data?.catalog_import_result || {}),
      });
      setImportVisible(false);
      resetImportPanel();
      setRefreshKey((value) => value + 1);
      message.success('导入成功');
    } catch (error) {
      message.error(getErrorMessage(error, '导入失败'));
    } finally {
      setImporting(false);
    }
  };

  const linkageResult = {
    ...EMPTY_RESULT,
    ...(catalogImportResult || {}),
  };
  const updatedSystems = Array.isArray(linkageResult.updated_systems) && linkageResult.updated_systems.length > 0
    ? linkageResult.updated_systems
    : linkageResult.updated_system_ids.map((item) => ({ system_id: item, system_name: item }));

  return (
    <div style={{ padding: '24px' }}>
      <Space style={{ marginBottom: 16 }} wrap>
        <Button icon={<DownloadOutlined />} onClick={downloadTemplate}>
          下载模板
        </Button>
        <Button
          type="primary"
          icon={<UploadOutlined />}
          aria-label="批量导入（XLSX）"
          onClick={() => setImportVisible((value) => !value)}
        >
          批量导入（XLSX）
        </Button>
      </Space>

      {importVisible ? (
        <div
          style={{
            marginBottom: 16,
            padding: '8px 0 12px',
            borderBottom: '1px solid #f0f0f0',
          }}
        >
          <Space direction="vertical" size={12} style={{ width: '100%' }}>
            <Text type="secondary">
              请使用最新系统清单模板；preview 仅校验，confirm 才会写入并按空画像规则联动初始化。
            </Text>
            <Space wrap size={12}>
              <span>导入模式：</span>
              <Switch checked={replaceMode} onChange={setReplaceMode} checkedChildren="覆盖" unCheckedChildren="增量" />
              <Text type="secondary">{replaceMode ? '覆盖现有系统清单' : '保留现有系统清单并追加更新'}</Text>
            </Space>

            <input
              type="file"
              accept=".xlsx,.xls"
              onChange={(event) => {
                const nextFile = event.target.files?.[0] || null;
                setImportFile(nextFile);
                setPreview(null);
                if (nextFile) {
                  void parseImport(nextFile);
                }
              }}
            />

            <Space wrap size={8}>
              <Button type="primary" onClick={confirmImport} loading={importing} disabled={!importFile || parsing}>
                确认导入
              </Button>
            </Space>

            {parsing ? <Text type="secondary">正在预检文件，请稍候。</Text> : null}

            {preview ? (
              <div
                style={{
                  paddingTop: 8,
                  borderTop: '1px solid #f5f5f5',
                }}
              >
                <Space direction="vertical" size={8} style={{ width: '100%' }}>
                  <Text>系统数：{preview.summary?.systems_total || 0}</Text>
                  <div>
                    {(preview.systems || []).map((item, index) => (
                      <div key={`${item.name || 'row'}-${index}`} style={{ padding: '8px 0', borderTop: index === 0 ? 'none' : '1px solid #f0f0f0' }}>
                        <div><strong>{item.name || '-'}</strong></div>
                        <div style={{ color: 'rgba(0, 0, 0, 0.45)' }}>{item.abbreviation || '-'}</div>
                        <div style={{ color: 'rgba(0, 0, 0, 0.45)' }}>{item.status || '-'}</div>
                        {(item.errors || []).length > 0 ? (
                          <div style={{ color: '#ff4d4f' }}>{item.errors.join('；')}</div>
                        ) : null}
                      </div>
                    ))}
                  </div>
                </Space>
              </div>
            ) : null}
          </Space>
        </div>
      ) : null}

      <MainSystemConfigPage embedded key={`main-${refreshKey}`} />

      {catalogImportResult ? (
        <Card title="画像联动结果" style={{ marginTop: 16 }}>
          <Space direction="vertical" size={12} style={{ width: '100%' }}>
            <div>
              <Text strong>已更新系统</Text>
              {updatedSystems.length === 0 ? (
                <div style={{ marginTop: 8 }}>
                  <Text type="secondary">本次没有新增画像初始化。</Text>
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
              <Text strong>预检错误</Text>
              {linkageResult.preview_errors.length === 0 ? (
                <div style={{ marginTop: 8 }}>
                  <Text type="secondary">本次没有预检错误。</Text>
                </div>
              ) : (
                <ul style={{ margin: '8px 0 0', paddingLeft: 20 }}>
                  {linkageResult.preview_errors.map((item, index) => (
                    <li key={`${item.row_number || 'preview-error'}-${index}`}>
                      <div><strong>{item.system_name || '-'}</strong></div>
                      <div style={{ color: 'rgba(0, 0, 0, 0.45)' }}>{`第 ${item.row_number || '-'} 行`}</div>
                      <div style={{ color: 'rgba(0, 0, 0, 0.45)' }}>
                        {(item.errors || []).join('；') || '-'}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div>
              <Text strong>跳过项</Text>
              {linkageResult.skipped_items.length === 0 ? (
                <div style={{ marginTop: 8 }}>
                  <Text type="secondary">本次没有跳过项。</Text>
                </div>
              ) : (
                <ul style={{ margin: '8px 0 0', paddingLeft: 20 }}>
                  {linkageResult.skipped_items.map((item, index) => (
                    <li key={`${item.system_id || item.system_name || 'skip'}-${index}`}>
                      <div><strong>{item.system_name || item.system_id || '-'}</strong></div>
                      <div style={{ color: 'rgba(0, 0, 0, 0.45)' }}>
                        {SKIP_REASON_LABELS[item.reason] || item.reason || '-'}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {linkageResult.errors.length > 0 ? (
              <Alert
                type="warning"
                showIcon
                message="导入存在异常"
                description={linkageResult.errors.join('；')}
              />
            ) : null}
          </Space>
        </Card>
      ) : null}
    </div>
  );
};

export default SystemListConfigPage;
