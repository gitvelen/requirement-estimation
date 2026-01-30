import React, { useMemo, useState } from 'react';
import { Alert, Button, Divider, Modal, Space, Switch, Tabs, Upload, message } from 'antd';
import { DownloadOutlined, InboxOutlined, UploadOutlined } from '@ant-design/icons';
import axios from 'axios';
import PageHeader from '../components/PageHeader';
import DataTable from '../components/DataTable';
import MainSystemConfigPage from './MainSystemConfigPage';
import SubsystemConfigPage from './SubsystemConfigPage';

const { TabPane } = Tabs;

const SystemListConfigPage = () => {
  const [importVisible, setImportVisible] = useState(false);
  const [importFile, setImportFile] = useState(null);
  const [parsing, setParsing] = useState(false);
  const [importing, setImporting] = useState(false);
  const [replaceMode, setReplaceMode] = useState(true);
  const [preview, setPreview] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const downloadTemplate = async () => {
    try {
      const response = await axios.get('/api/v1/system-list/template', { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', '系统清单模板.xlsx');
      document.body.appendChild(link);
      link.click();
      link.remove();
      message.success('模板已下载');
    } catch (error) {
      if (error.response?.status === 404) {
        message.error('下载模板失败：后端接口不存在（请更新/重启后端服务）');
        return;
      }
      message.error(error.response?.data?.detail || '下载模板失败');
    }
  };

  const parseImport = async () => {
    if (!importFile) {
      message.warning('请先选择Excel文件');
      return;
    }
    try {
      setParsing(true);
      const formData = new FormData();
      formData.append('file', importFile);
      const response = await axios.post('/api/v1/system-list/batch-import', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setPreview(response.data?.data || null);
      message.success('解析完成');
    } catch (error) {
      if (error.response?.status === 404) {
        message.error('解析失败：后端接口不存在（请更新/重启后端服务）');
        return;
      }
      const detail = error.response?.data?.detail;
      if (detail?.message) {
        message.error(detail.message);
      } else {
        message.error(detail || '解析失败');
      }
    } finally {
      setParsing(false);
    }
  };

  const hasErrors = useMemo(() => {
    const systems = preview?.systems || [];
    const mappings = preview?.mappings || [];
    return (
      systems.some((item) => item.errors && item.errors.length > 0)
      || mappings.some((item) => item.errors && item.errors.length > 0)
    );
  }, [preview]);

  const confirmImport = async () => {
    if (!preview) {
      await parseImport();
      return;
    }
    if (hasErrors) {
      message.warning('存在提示信息，将按Excel内容继续导入');
    }
    try {
      setImporting(true);
      await axios.post('/api/v1/system-list/batch-import/confirm', {
        mode: replaceMode ? 'replace' : 'upsert',
        systems: preview.systems || [],
        mappings: preview.mappings || [],
      });
      message.success('导入成功');
      setImportVisible(false);
      setImportFile(null);
      setPreview(null);
      setReplaceMode(true);
      setRefreshKey((val) => val + 1);
    } catch (error) {
      if (error.response?.status === 404) {
        message.error('导入失败：后端接口不存在（请更新/重启后端服务）');
        return;
      }
      const detail = error.response?.data?.detail;
      if (detail?.message) {
        message.error(detail.message);
      } else {
        message.error(detail || '导入失败');
      }
    } finally {
      setImporting(false);
    }
  };

  const systemColumns = [
    { title: '系统名称', dataIndex: 'name', key: 'name', width: 260, render: (v) => v || '-' },
    { title: '英文简称', dataIndex: 'abbreviation', key: 'abbreviation', width: 140, render: (v) => v || '-' },
    { title: '状态', dataIndex: 'status', key: 'status', width: 120, render: (v) => v || '-' },
    {
      title: '提示',
      dataIndex: 'errors',
      key: 'errors',
      render: (value) => (value && value.length ? <span style={{ color: '#cf1322' }}>{value.join('；')}</span> : '-'),
    },
  ];

  const mappingColumns = [
    { title: '子系统名称', dataIndex: 'subsystem', key: 'subsystem', width: 260, render: (v) => v || '-' },
    { title: '所属系统', dataIndex: 'main_system', key: 'main_system', width: 200, render: (v) => v || '-' },
    {
      title: '提示',
      dataIndex: 'errors',
      key: 'errors',
      render: (value) => (value && value.length ? <span style={{ color: '#cf1322' }}>{value.join('；')}</span> : '-'),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <PageHeader
        title="系统清单配置"
        subtitle="统一维护标准主系统清单与子系统映射关系"
        extra={(
          <Space>
            <Button icon={<DownloadOutlined />} onClick={downloadTemplate}>
              下载模板
            </Button>
            <Button type="primary" icon={<UploadOutlined />} onClick={() => setImportVisible(true)}>
              批量导入（XLSX）
            </Button>
          </Space>
        )}
      />
      <Tabs defaultActiveKey="main">
        <TabPane tab="主系统清单" key="main">
          <MainSystemConfigPage embedded key={`main-${refreshKey}`} />
        </TabPane>
        <TabPane tab="子系统映射" key="subsystem">
          <SubsystemConfigPage embedded key={`sub-${refreshKey}`} />
        </TabPane>
      </Tabs>

      <Modal
        title="批量导入系统清单（XLSX）"
        open={importVisible}
        onCancel={() => {
          setImportVisible(false);
          setImportFile(null);
          setPreview(null);
          setReplaceMode(true);
        }}
        onOk={confirmImport}
        okText={preview ? '确认导入' : '解析文件'}
        cancelText="取消"
        confirmLoading={parsing || importing}
        width={1000}
        destroyOnClose
      >
        <Alert
          type="info"
          showIcon
          message="导入说明"
          description="请使用“系统清单模板.xlsx”填写后导入。系统会按表头识别两个Sheet：主系统清单（系统名称/英文简称/状态）与子系统清单（子系统名称/所属系统）；其它列也会一并保存，导入后可在页面查看与修改。"
          style={{ marginBottom: 16 }}
        />

        <Space style={{ marginBottom: 16 }} wrap>
          <span>覆盖导入：</span>
          <Switch checked={replaceMode} onChange={setReplaceMode} checkedChildren="覆盖" unCheckedChildren="增量" />
          <span style={{ color: 'rgba(0,0,0,0.45)' }}>
            {replaceMode ? '覆盖会用导入内容替换现有配置' : '增量会保留现有配置并追加导入'}
          </span>
        </Space>

        <Upload.Dragger
          accept=".xlsx"
          maxCount={1}
          beforeUpload={(file) => {
            setImportFile(file);
            setPreview(null);
            return false;
          }}
          onRemove={() => {
            setImportFile(null);
            setPreview(null);
          }}
        >
          <p className="ant-upload-drag-icon">
            <InboxOutlined />
          </p>
          <p className="ant-upload-text">点击或拖拽Excel文件到此区域</p>
          <p className="ant-upload-hint">仅支持 .xlsx</p>
        </Upload.Dragger>

        <div style={{ marginTop: 12 }}>
          <Button onClick={parseImport} loading={parsing} disabled={!importFile}>
            解析文件
          </Button>
        </div>

        {preview ? (
          <>
            <Divider />
            <Space wrap style={{ marginBottom: 12 }}>
              <span>主系统：{preview.summary?.systems_total || 0} 条</span>
              <span style={{ color: preview.summary?.systems_error ? '#cf1322' : 'rgba(0,0,0,0.45)' }}>
                错误：{preview.summary?.systems_error || 0} 条
              </span>
              <span>子系统：{preview.summary?.mappings_total || 0} 条</span>
              <span style={{ color: preview.summary?.mappings_error ? '#cf1322' : 'rgba(0,0,0,0.45)' }}>
                错误：{preview.summary?.mappings_error || 0} 条
              </span>
            </Space>

            <Tabs defaultActiveKey="systems">
              <TabPane tab="主系统清单预览" key="systems">
                <DataTable
                  rowKey={(record, index) => `${record.name || 'row'}-${index}`}
                  columns={systemColumns}
                  dataSource={preview.systems || []}
                  pagination={{ pageSize: 8 }}
                  scroll={{ x: 900, y: 320 }}
                />
              </TabPane>
              <TabPane tab="子系统清单预览" key="mappings">
                <DataTable
                  rowKey={(record, index) => `${record.subsystem || 'row'}-${index}`}
                  columns={mappingColumns}
                  dataSource={preview.mappings || []}
                  pagination={{ pageSize: 8 }}
                  scroll={{ x: 900, y: 320 }}
                />
              </TabPane>
            </Tabs>

            {hasErrors ? (
              <Alert
                type="warning"
                showIcon
                message="存在提示"
                description="将按Excel内容导入，如需修正请在导入后修改。"
                style={{ marginTop: 16 }}
              />
            ) : null}
          </>
        ) : null}
      </Modal>
    </div>
  );
};

export default SystemListConfigPage;
