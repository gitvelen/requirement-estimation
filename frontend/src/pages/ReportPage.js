import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Descriptions, Button, Spin, message, Alert, Tag, Progress } from 'antd';
import { ArrowLeftOutlined, DownloadOutlined, ReloadOutlined } from '@ant-design/icons';
import axios from 'axios';

const ReportPage = () => {
  const { taskId } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [report, setReport] = useState(null);

  useEffect(() => {
    fetchReport();
  }, [taskId]);

  const fetchReport = async () => {
    try {
      setLoading(true);
      // 获取任务状态信息
      const response = await axios.get(`/api/v1/requirement/status/${taskId}`);
      setReport(response.data.data);
    } catch (error) {
      if (error.response?.status === 404) {
        message.error('任务不存在');
      } else if (error.response?.status === 400) {
        message.warning('报告尚未生成，请等待任务完成');
      } else {
        message.error('获取任务信息失败');
      }
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async () => {
    try {
      const response = await axios.get(`/api/v1/requirement/report/${taskId}`, {
        responseType: 'blob',
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `评估报告_${report.filename || taskId}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();

      message.success('下载成功');
    } catch (error) {
      if (error.response?.status === 400) {
        message.error('报告尚未生成，请等待任务完成');
      } else if (error.response?.status === 404) {
        message.error('报告文件不存在');
      } else {
        message.error('下载失败');
      }
    }
  };

  const renderStatus = (status) => {
    const statusMap = {
      pending: { color: 'default', text: '待处理' },
      processing: { color: 'processing', text: '处理中' },
      completed: { color: 'success', text: '已完成' },
      failed: { color: 'error', text: '失败' },
    };
    const { color, text } = statusMap[status] || { color: 'default', text: status };
    return <Tag color={color}>{text}</Tag>;
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" tip="加载中..." />
      </div>
    );
  }

  if (!report) {
    return (
      <Alert
        message="未找到报告"
        description="无法加载该任务的评估报告"
        type="error"
        showIcon
      />
    );
  }

  return (
    <div className="report-page" style={{ padding: '24px' }}>
      <div style={{ marginBottom: 16 }}>
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={() => navigate('/tasks')}
        >
          返回任务列表
        </Button>
        <Button
          icon={<ReloadOutlined />}
          onClick={fetchReport}
          style={{ marginLeft: 8 }}
        >
          刷新
        </Button>
        <Button
          type="primary"
          icon={<DownloadOutlined />}
          onClick={handleDownload}
          disabled={report?.status !== 'completed'}
          style={{ marginLeft: 8 }}
        >
          下载Excel报告
        </Button>
      </div>

      <Card title="任务详情" className="report-card">
        <Descriptions title="基本信息" bordered column={2}>
          <Descriptions.Item label="任务ID">{taskId}</Descriptions.Item>
          <Descriptions.Item label="文件名">{report?.filename || '-'}</Descriptions.Item>
          <Descriptions.Item label="任务状态">
            {report ? renderStatus(report.status) : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="创建时间">{report?.created_at || '-'}</Descriptions.Item>
          <Descriptions.Item label="当前进度" span={2}>
            {report && (
              <div style={{ maxWidth: 400 }}>
                <Progress
                  percent={report.progress || 0}
                  status={report.status === 'failed' ? 'exception' : report.status === 'completed' ? 'success' : 'active'}
                />
                <div style={{ marginTop: 8, color: '#666' }}>
                  {report.message || '-'}
                </div>
              </div>
            )}
          </Descriptions.Item>
        </Descriptions>

        {report?.status === 'processing' && (
          <Alert
            message="任务处理中"
            description="任务正在后台处理中，请稍后刷新页面查看最新进度"
            type="info"
            showIcon
            style={{ marginTop: 16 }}
          />
        )}

        {report?.status === 'completed' && (
          <Alert
            message="评估已完成"
            description={`报告已生成完成，点击上方"下载Excel报告"按钮获取详细评估结果`}
            type="success"
            showIcon
            style={{ marginTop: 16 }}
          />
        )}

        {report?.status === 'failed' && (
          <Alert
            message="评估失败"
            description={report.error || '未知错误'}
            type="error"
            showIcon
            style={{ marginTop: 16 }}
          />
        )}

        {report?.status === 'pending' && (
          <Alert
            message="任务等待处理"
            description="任务已创建，正在排队等待处理"
            type="warning"
            showIcon
            style={{ marginTop: 16 }}
          />
        )}
      </Card>
    </div>
  );
};

export default ReportPage;
