import React, { useState } from 'react';
import { Upload, Button, message, Card, Space, Typography, Input, Divider } from 'antd';
import { InboxOutlined, UploadOutlined, SettingOutlined } from '@ant-design/icons';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

const { Text } = Typography;

const UploadPage = () => {
  const [fileList, setFileList] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [adminKey, setAdminKey] = useState(localStorage.getItem('ADMIN_API_KEY') || '');
  const navigate = useNavigate();

  const saveAdminKey = () => {
    const trimmed = adminKey.trim();
    if (trimmed) {
      localStorage.setItem('ADMIN_API_KEY', trimmed);
      message.success('管理口令已保存（仅本地）');
    } else {
      localStorage.removeItem('ADMIN_API_KEY');
      message.info('管理口令已清除');
    }
  };

  const handleUpload = async () => {
    if (fileList.length === 0) {
      message.warning('请先选择文件');
      return;
    }

    const formData = new FormData();
    formData.append('file', fileList[0]);

    setUploading(true);

    try {
      const response = await axios.post('/api/v1/requirement/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      message.success('文件上传成功');
      const taskId = response.data.data.task_id;
      navigate(`/tasks`);

    } catch (error) {
      message.error('文件上传失败: ' + error.message);
    } finally {
      setUploading(false);
    }
  };

  const uploadProps = {
    onRemove: () => {
      setFileList([]);
    },
    beforeUpload: (file) => {
      const isDocx = file.name.toLowerCase().endsWith('.docx');
      if (!isDocx) {
        message.error('仅支持.docx格式文件');
        return false;
      }
      const isLt10M = file.size / 1024 / 1024 < 10;
      if (!isLt10M) {
        message.error('文件大小不能超过10MB');
        return false;
      }
      setFileList([file]);
      return false;
    },
    fileList,
  };

  return (
    <div>
      <Card title="上传需求文档" className="upload-card">
        <div style={{ marginBottom: 16 }}>
          <Space>
            <Button
              icon={<SettingOutlined />}
              onClick={() => navigate('/config/subsystem')}
            >
              子系统配置
            </Button>
            <Button
              icon={<SettingOutlined />}
              onClick={() => navigate('/config/mainsystem')}
            >
              主系统配置
            </Button>
            <Button
              icon={<SettingOutlined />}
              onClick={() => navigate('/config/cosmic')}
            >
              COSMIC规则配置
            </Button>
            <Button
              onClick={() => navigate('/tasks')}
            >
              查看任务列表
            </Button>
          </Space>
        </div>

        <Divider />
        <div style={{ marginBottom: 16 }}>
          <Space>
            <Text>管理口令（可选，仅本地/内网使用）</Text>
            <Input.Password
              placeholder="X-API-Key"
              value={adminKey}
              onChange={(e) => setAdminKey(e.target.value)}
              style={{ width: 260 }}
            />
            <Button onClick={saveAdminKey}>保存</Button>
          </Space>
        </div>

        <Upload.Dragger {...uploadProps}>
          <p className="ant-upload-drag-icon">
            <InboxOutlined />
          </p>
          <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
          <p className="ant-upload-hint">支持.docx格式的需求文档，文件大小不超过10MB</p>
        </Upload.Dragger>

        <div style={{ marginTop: 24, textAlign: 'center' }}>
          <Button
            type="primary"
            icon={<UploadOutlined />}
            onClick={handleUpload}
            loading={uploading}
            size="large"
          >
            开始评估
          </Button>
        </div>

        <div style={{ marginTop: 24 }}>
          <h3>使用说明</h3>
          <ul>
            <li>上传需求文档（.docx格式）</li>
            <li>系统将自动解析需求内容</li>
            <li>识别涉及系统并拆分功能点</li>
            <li>使用Delphi法进行工作量估算</li>
            <li>生成Excel评估报告</li>
          </ul>
        </div>
      </Card>
    </div>
  );
};

export default UploadPage;
