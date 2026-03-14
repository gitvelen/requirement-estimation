import React, { useState } from 'react';
import { Button, Card, Space, Typography, message } from 'antd';
import { UploadOutlined } from '@ant-design/icons';
import axios from 'axios';

const { Text } = Typography;

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

const ServiceGovernancePage = () => {
  const [fileList, setFileList] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);

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
      message.error(getErrorMessage(error, '服务治理导入失败'));
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
