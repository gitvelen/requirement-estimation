import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Button,
  Card,
  Form,
  Input,
  message,
  Modal,
  Select,
  Space,
  Spin,
  Table,
  Tag,
  Typography,
} from 'antd';
import { PlayCircleOutlined, ReloadOutlined } from '@ant-design/icons';
import axios from 'axios';

const { Title, Paragraph, Text } = Typography;
const { TextArea } = Input;

const splitToList = (value) => (
  String(value || '')
    .replace(/，|、|；/g, ',')
    .split(/[\n,;]+/)
    .map((item) => item.trim())
    .filter(Boolean)
);

const CodeScanPage = () => {
  const [form] = Form.useForm();
  const [systems, setSystems] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [resultVisible, setResultVisible] = useState(false);
  const [resultLoading, setResultLoading] = useState(false);
  const [resultData, setResultData] = useState(null);

  const fetchSystems = useCallback(async () => {
    try {
      const response = await axios.get('/api/v1/system/systems');
      setSystems(response.data?.data?.systems || []);
    } catch (error) {
      message.error('获取主系统列表失败: ' + (error.response?.data?.detail || error.message));
    }
  }, []);

  const fetchJobs = useCallback(async () => {
    try {
      const response = await axios.get('/api/v1/code-scan/jobs');
      setJobs(response.data?.data || []);
    } catch (error) {
      message.error('获取扫描任务失败: ' + (error.response?.data?.detail || error.message));
    }
  }, []);

  useEffect(() => {
    fetchSystems();
    fetchJobs();
  }, [fetchSystems, fetchJobs]);

  const handleRun = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);
      const scanPaths = splitToList(values.scan_paths);
      const excludeDirs = splitToList(values.exclude_dirs);
      const options = {};
      if (scanPaths.length) {
        options.paths = scanPaths;
      }
      if (excludeDirs.length) {
        options.exclude_dirs = excludeDirs;
      }
      const response = await axios.post('/api/v1/code-scan/run', {
        system_name: values.system_name,
        system_id: values.system_id || undefined,
        repo_path: values.repo_path,
        options: Object.keys(options).length > 0 ? options : undefined,
      });
      message.success(`已触发扫描任务：${response.data?.data?.job_id || ''}`);
      form.resetFields(['repo_path', 'scan_paths', 'exclude_dirs']);
      fetchJobs();
    } catch (error) {
      if (error?.errorFields) {
        return;
      }
      message.error(error.response?.data?.detail || '触发扫描失败');
    } finally {
      setLoading(false);
    }
  };

  const handleViewResult = useCallback(async (jobId) => {
    try {
      setResultLoading(true);
      setResultVisible(true);
      const response = await axios.get(`/api/v1/code-scan/result/${jobId}`);
      setResultData(response.data?.data || null);
    } catch (error) {
      message.error(error.response?.data?.detail || '获取扫描结果失败');
    } finally {
      setResultLoading(false);
    }
  }, []);

  const handleCommit = useCallback(async (jobId) => {
    try {
      const response = await axios.post(`/api/v1/code-scan/commit/${jobId}`);
      const data = response.data?.data || {};
      message.success(`入库完成：成功${data.success || 0}条，失败${data.failed || 0}条`);
      fetchJobs();
    } catch (error) {
      message.error(error.response?.data?.detail || '提交失败');
    }
  }, [fetchJobs]);

  const jobColumns = useMemo(() => [
    {
      title: '任务ID',
      dataIndex: 'job_id',
      key: 'job_id',
      width: 200,
      ellipsis: true,
    },
    {
      title: '系统',
      dataIndex: 'system_name',
      key: 'system_name',
      width: 140,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (value) => {
        const color = value === 'completed' ? 'green' : value === 'failed' ? 'red' : 'orange';
        return <Tag color={color}>{value}</Tag>;
      },
    },
    {
      title: '进度',
      dataIndex: 'progress',
      key: 'progress',
      width: 100,
      render: (value) => `${Math.round((value || 0) * 100)}%`,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (value) => (value ? value.replace('T', ' ').slice(0, 19) : '-'),
    },
    {
      title: '操作',
      key: 'action',
      width: 220,
      render: (_, record) => (
        <Space size="small">
          <Button size="small" onClick={() => handleViewResult(record.job_id)}>
            预览结果
          </Button>
          <Button
            size="small"
            type="primary"
            disabled={record.status !== 'completed'}
            onClick={() => handleCommit(record.job_id)}
          >
            提交入库
          </Button>
        </Space>
      ),
    },
  ], [handleCommit, handleViewResult]);

  const resultColumns = [
    { title: '类型', dataIndex: 'entry_type', key: 'entry_type', width: 120 },
    { title: '标识', dataIndex: 'entry_id', key: 'entry_id', width: 240, ellipsis: true },
    { title: '摘要', dataIndex: 'summary', key: 'summary', width: 220, ellipsis: true },
    {
      title: '位置',
      dataIndex: 'location',
      key: 'location',
      width: 220,
      render: (value) => value ? `${value.file || ''}:${value.line || 0}` : '-',
    },
  ];

  return (
    <div style={{ padding: 24, maxWidth: 1400, margin: '0 auto' }}>
      <Title level={2}>代码扫描</Title>
      <Paragraph type="secondary">
        扫描Spring Boot代码仓，产出能力目录（入口/依赖），用于集成点提示与归属校验。
      </Paragraph>

      <Card style={{ marginBottom: 16 }}>
        <Form layout="vertical" form={form}>
          <Space wrap align="start" style={{ width: '100%' }}>
            <Form.Item
              name="system_name"
              label="系统"
              rules={[{ required: true, message: '请选择系统' }]}
            >
              <Select
                style={{ width: 220 }}
                placeholder="选择系统"
                options={(systems || []).map((item) => ({ label: item.name, value: item.name }))}
                onChange={(value) => {
                  const matched = (systems || []).find((item) => item.name === value);
                  form.setFieldsValue({ system_id: matched?.id || '' });
                }}
              />
            </Form.Item>
            <Form.Item name="system_id" style={{ display: 'none' }}>
              <Input />
            </Form.Item>
            <Form.Item
              name="repo_path"
              label="仓库路径"
              rules={[{ required: true, message: '请输入仓库路径' }]}
            >
              <Input style={{ width: 360 }} placeholder="/path/to/repo" />
            </Form.Item>
            <Form.Item name="scan_paths" label="扫描路径（可选）">
              <TextArea
                rows={2}
                style={{ width: 320 }}
                placeholder={'每行一个路径，例如\nsrc/main/java\nsrc/main/kotlin'}
              />
            </Form.Item>
            <Form.Item name="exclude_dirs" label="排除目录（可选）">
              <TextArea
                rows={2}
                style={{ width: 280 }}
                placeholder={'每行一个目录，例如\nbuild\ntarget'}
              />
            </Form.Item>
          </Space>
          <Space>
            <Button type="primary" icon={<PlayCircleOutlined />} loading={loading} onClick={handleRun}>
              触发扫描
            </Button>
            <Button icon={<ReloadOutlined />} onClick={fetchJobs}>
              刷新任务
            </Button>
          </Space>
        </Form>
      </Card>

      <Card>
        <Table
          rowKey="job_id"
          columns={jobColumns}
          dataSource={jobs}
          pagination={{ pageSize: 8 }}
        />
      </Card>

      <Modal
        open={resultVisible}
        onCancel={() => setResultVisible(false)}
        footer={null}
        width={900}
        title="扫描结果预览"
      >
        {resultLoading ? (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin />
          </div>
        ) : (
          <>
            <Text type="secondary">
              共 {resultData?.items?.length || 0} 条能力目录
            </Text>
            <Table
              style={{ marginTop: 16 }}
              rowKey={(record, idx) => `${record.entry_id}_${idx}`}
              columns={resultColumns}
              dataSource={resultData?.items || []}
              pagination={{ pageSize: 8 }}
            />
          </>
        )}
      </Modal>
    </div>
  );
};

export default CodeScanPage;
