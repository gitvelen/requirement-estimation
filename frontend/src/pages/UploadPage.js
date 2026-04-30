import React, { useEffect, useState } from 'react';
import { Upload, Button, message, Card, Space, Typography, Input, Divider, Select } from 'antd';
import { InboxOutlined, UploadOutlined } from '@ant-design/icons';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import useAuth from '../hooks/useAuth';
import { filterResponsibleSystems } from '../utils/systemOwnership';

const { Text } = Typography;
const { TextArea } = Input;
const UNLIMITED_OPTION_VALUE = '__UNLIMITED__';

const UploadPage = () => {
  const [fileList, setFileList] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [taskName, setTaskName] = useState('');
  const [taskDesc, setTaskDesc] = useState('');
  const [targetSystemOptions, setTargetSystemOptions] = useState([]);
  const [selectedTargetSystem, setSelectedTargetSystem] = useState('');
  const navigate = useNavigate();
  const { user } = useAuth();

  useEffect(() => {
    let alive = true;

    const loadTargetSystems = async () => {
      try {
        const response = await axios.get('/api/v1/system/systems');
        const systems = response.data?.data?.systems || [];
        const responsibleSystems = filterResponsibleSystems(systems, user);
        const responsibleNames = Array.from(
          new Set(
            responsibleSystems
              .map((item) => String(item?.name || '').trim())
              .filter(Boolean)
          )
        );
        const options = responsibleNames.map((name) => ({
          label: name,
          value: name,
          mode: 'specific',
        }));
        options.push({
          label: '不限',
          value: UNLIMITED_OPTION_VALUE,
          mode: 'unlimited',
        });

        if (alive) {
          setTargetSystemOptions(options);
        }
      } catch (error) {
        if (alive) {
          setTargetSystemOptions([]);
        }
        message.error(error.response?.data?.detail || '获取待评估系统失败');
      }
    };

    if (user) {
      loadTargetSystems();
    }

    return () => {
      alive = false;
    };
  }, [user]);

  const handleUpload = async () => {
    if (fileList.length === 0) {
      message.warning('请先选择文件');
      return;
    }

    const selectedOption = targetSystemOptions.find((item) => item.value === selectedTargetSystem);
    if (!selectedOption) {
      message.warning('请选择待评估系统');
      return;
    }

    const formData = new FormData();
    formData.append('file', fileList[0]);
    formData.append('target_system_mode', selectedOption.mode);
    formData.append('target_system_name', selectedOption.mode === 'specific' ? selectedOption.label : '');
    if (taskName.trim()) {
      formData.append('name', taskName.trim());
    }
    if (taskDesc.trim()) {
      formData.append('description', taskDesc.trim());
    }

    setUploading(true);

    try {
      await axios.post('/api/v1/tasks', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      message.success('任务创建成功，AI正在评估');
      navigate('/tasks/my-tasks');

    } catch (error) {
      const payload = error.response?.data;
      message.error(payload?.message || payload?.detail || '文件上传失败');
    } finally {
      setUploading(false);
    }
  };

  const uploadProps = {
    onRemove: () => {
      setFileList([]);
    },
    beforeUpload: (file) => {
      const lowerName = file.name.toLowerCase();
      const isSupported = lowerName.endsWith('.docx') || lowerName.endsWith('.doc') || lowerName.endsWith('.xls');
      if (!isSupported) {
        message.error('仅支持 .docx / .doc / .xls 格式文件');
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
    accept: '.docx,.doc,.xls',
  };

  return (
    <div>
      <Card title="发起评估任务" className="upload-card">
        <Space direction="vertical" size={16} style={{ width: '100%' }}>
          <div>
            <Text>待评估系统</Text>
            <Select
              value={selectedTargetSystem || undefined}
              onChange={setSelectedTargetSystem}
              options={targetSystemOptions}
              placeholder="请选择待评估系统"
              style={{ width: '100%', marginTop: 8 }}
            />
          </div>
          <div>
            <Text>任务名称（可选）</Text>
            <Input
              placeholder="例如：核心系统需求评估"
              value={taskName}
              onChange={(e) => setTaskName(e.target.value)}
              style={{ marginTop: 8 }}
            />
          </div>
          <div>
            <Text>任务说明（可选）</Text>
            <TextArea
              placeholder="补充评估背景、范围或重点说明"
              rows={3}
              value={taskDesc}
              onChange={(e) => setTaskDesc(e.target.value)}
              style={{ marginTop: 8 }}
            />
          </div>
        </Space>

        <Divider />

        <Upload.Dragger {...uploadProps}>
          <p className="ant-upload-drag-icon">
            <InboxOutlined />
          </p>
          <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
          <p className="ant-upload-hint">支持 .docx格式的需求文档，文件大小不超过10MB</p>
        </Upload.Dragger>

        <div style={{ marginTop: 24, textAlign: 'center' }}>
          <Button
            type="primary"
            icon={<UploadOutlined />}
            onClick={handleUpload}
            loading={uploading}
            size="large"
          >
            提交评估
          </Button>
        </div>

        <div style={{ marginTop: 24 }}>
          <h3>使用说明</h3>
          <ul>
            <li>上传需求文档（.docx格式）</li>
            <li>系统将自动解析需求内容并拆分功能点</li>
            <li>AI完成初评后进入草稿状态，可继续编辑</li>
          </ul>
        </div>
      </Card>
    </div>
  );
};

export default UploadPage;
