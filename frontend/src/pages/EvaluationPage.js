import React, { useEffect, useMemo, useState, useCallback } from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import { Alert, Button, Card, Checkbox, Input, InputNumber, message, Popover, Space, Table, Tabs, Tag, Typography } from 'antd';
import axios from 'axios';

const { Text } = Typography;

const COLUMN_SETTING_KEY = 'EVALUATION_VISIBLE_COLUMNS';
const DEFAULT_VISIBLE_COLUMNS = ['业务描述', '输入', '输出', '依赖项', '备注'];

const EvaluationPage = () => {
  const { taskId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();

  const [token, setToken] = useState('');
  const [tokenReady, setTokenReady] = useState(false);
  const [loading, setLoading] = useState(false);
  const [taskInfo, setTaskInfo] = useState(null);
  const [systemsData, setSystemsData] = useState({});
  const [currentSystem, setCurrentSystem] = useState('');
  const [draftValues, setDraftValues] = useState({});
  const [editingId, setEditingId] = useState(null);
  const [roundNo, setRoundNo] = useState(1);
  const [hasSubmitted, setHasSubmitted] = useState(false);
  const [highDeviationFeatures, setHighDeviationFeatures] = useState([]);
  const [visibleColumns, setVisibleColumns] = useState(() => {
    try {
      const raw = localStorage.getItem(COLUMN_SETTING_KEY);
      const parsed = raw ? JSON.parse(raw) : null;
      if (Array.isArray(parsed) && parsed.length) {
        return parsed;
      }
    } catch (error) {
      // ignore storage errors
    }
    return DEFAULT_VISIBLE_COLUMNS;
  });

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const urlToken = params.get('token');
    const savedToken = localStorage.getItem(`INVITE_TOKEN_${taskId}`);
    const initToken = urlToken || savedToken;
    if (initToken) {
      setToken(initToken);
      setTokenReady(true);
      localStorage.setItem(`INVITE_TOKEN_${taskId}`, initToken);
    }
  }, [location.search, taskId]);

  const fetchEvaluation = useCallback(async (inviteToken) => {
    try {
      setLoading(true);
      const response = await axios.get(`/api/v1/evaluation/${taskId}`, {
        params: { token: inviteToken },
      });
      const payload = response.data.data;
      setTaskInfo(payload.task);
      setSystemsData(payload.features || {});
      const systemNames = Object.keys(payload.features || {});
      if (systemNames.length > 0) {
        setCurrentSystem(systemNames[0]);
      }
      setDraftValues(payload.myEvaluation?.draftData || {});
      setHasSubmitted(payload.myEvaluation?.hasSubmitted || false);
      setRoundNo(payload.task?.currentRound || 1);
      setHighDeviationFeatures(payload.highDeviationFeatures || []);
    } catch (error) {
      console.error('获取评估数据失败:', error);
      message.error(error.response?.data?.detail || '获取评估数据失败');
    } finally {
      setLoading(false);
    }
  }, [taskId]);

  useEffect(() => {
    if (tokenReady && token) {
      fetchEvaluation(token);
    }
  }, [tokenReady, token, fetchEvaluation]);

  useEffect(() => {
    try {
      localStorage.setItem(COLUMN_SETTING_KEY, JSON.stringify(visibleColumns));
    } catch (error) {
      // ignore storage errors
    }
  }, [visibleColumns]);

  const highDeviationSet = useMemo(() => new Set(highDeviationFeatures), [highDeviationFeatures]);

  const handleSaveDraft = async (featureId, value) => {
    try {
      await axios.post(`/api/v1/evaluation/${taskId}/draft`, {
        round: roundNo,
        evaluations: { [featureId]: value },
      }, {
        params: { token },
      });
    } catch (error) {
      message.error(error.response?.data?.detail || '自动保存失败');
    }
  };

  const handleSubmit = async () => {
    try {
      const evaluations = {};
      Object.values(systemsData).forEach(list => {
        list.forEach(item => {
          const value = draftValues[item.id] !== undefined ? draftValues[item.id] : (item.myEvaluation !== null && item.myEvaluation !== undefined ? item.myEvaluation : item.aiEstimatedDays);
          evaluations[item.id] = value;
        });
      });

      await axios.post(`/api/v1/evaluation/${taskId}/submit`, {
        round: roundNo,
        evaluations,
      }, {
        params: { token },
      });
      message.success('评估已提交');
      setTimeout(() => navigate('/tasks'), 1500);
    } catch (error) {
      message.error(error.response?.data?.detail || '提交失败');
    }
  };

  const handleWithdraw = async () => {
    try {
      await axios.post(`/api/v1/evaluation/${taskId}/withdraw`, null, {
        params: { token },
      });
      message.success('已撤回');
      fetchEvaluation(token);
    } catch (error) {
      message.error(error.response?.data?.detail || '撤回失败');
    }
  };

  const renderEstimateCell = (record) => {
    const draftValue = draftValues[record.id];
    const submittedValue = record.myEvaluation !== null && record.myEvaluation !== undefined ? record.myEvaluation : undefined;
    const displayValue = draftValue !== undefined ? draftValue : (submittedValue !== undefined ? submittedValue : record.aiEstimatedDays);
    const isEdited = (draftValue !== undefined && draftValue !== record.aiEstimatedDays)
      || (draftValue === undefined && submittedValue !== undefined && submittedValue !== record.aiEstimatedDays);

    if (hasSubmitted) {
      return (
        <div className={`estimate-cell ${isEdited ? 'estimate-edited' : 'estimate-ai'}`}>
          <Text style={{ color: isEdited ? '#000' : '#999' }}>{displayValue}</Text>
        </div>
      );
    }

    if (editingId === record.id) {
      return (
        <InputNumber
          min={0}
          step={0.5}
          autoFocus
          value={displayValue}
          onChange={(value) => {
            setDraftValues(prev => ({ ...prev, [record.id]: value }));
          }}
          onBlur={() => {
            setEditingId(null);
            const finalValue = draftValues[record.id] !== undefined ? draftValues[record.id] : displayValue;
            handleSaveDraft(record.id, finalValue);
          }}
          onPressEnter={() => {
            setEditingId(null);
            const finalValue = draftValues[record.id] !== undefined ? draftValues[record.id] : displayValue;
            handleSaveDraft(record.id, finalValue);
          }}
        />
      );
    }

    return (
      <div
        className={`estimate-cell ${isEdited ? 'estimate-edited' : 'estimate-ai'}`}
        onClick={() => setEditingId(record.id)}
        role="button"
        tabIndex={0}
      >
        <Text style={{ color: isEdited ? '#000' : '#999' }}>{displayValue}</Text>
      </div>
    );
  };

  const renderRemark = (text) => {
    const raw = String(text || '').trim();
    if (!raw) {
      return <Text type="secondary">-</Text>;
    }
    const tagColors = {
      归属依据: 'blue',
      系统约束: 'purple',
      集成点: 'geekblue',
      知识引用: 'cyan',
      待确认: 'orange',
      归属复核: 'red',
    };
    const lines = raw.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
    return (
      <div>
        {lines.map((line, idx) => {
          const match = line.match(/^\[([^\]]+)\]\s*(.*)$/);
          if (!match) {
            return (
              <div key={`${idx}-${line}`} style={{ marginBottom: 4 }}>
                <Text style={{ whiteSpace: 'pre-wrap' }}>{line}</Text>
              </div>
            );
          }
          const label = match[1];
          const content = match[2] || '';
          return (
            <div key={`${idx}-${label}`} style={{ marginBottom: 4 }}>
              <Tag color={tagColors[label] || 'default'} style={{ marginRight: 6 }}>
                {label}
              </Tag>
              <Text style={{ whiteSpace: 'pre-wrap' }}>{content}</Text>
            </div>
          );
        })}
      </div>
    );
  };

  const baseColumns = [
    { title: '序号', dataIndex: 'sequence', key: 'sequence', width: 80 },
    { title: '功能模块', dataIndex: 'module', key: 'module', width: 120 },
    { title: '功能点', dataIndex: 'name', key: 'name', width: 160 },
  ];

  const optionalColumns = {
    业务描述: { title: '业务描述', dataIndex: 'description', key: 'description', width: 240 },
    输入: {
      title: '输入',
      dataIndex: 'inputs',
      key: 'inputs',
      width: 160,
      render: (items) => (items && items.length ? items.join('、') : '-'),
    },
    输出: {
      title: '输出',
      dataIndex: 'outputs',
      key: 'outputs',
      width: 160,
      render: (items) => (items && items.length ? items.join('、') : '-'),
    },
    依赖项: {
      title: '依赖项',
      dataIndex: 'dependencies',
      key: 'dependencies',
      width: 160,
      render: (items) => (items && items.length ? items.join('、') : '-'),
    },
  };

  const estimateColumn = {
    title: '预估人天数',
    key: 'estimate',
    width: 140,
    render: (_, record) => renderEstimateCell(record),
  };

  const remarkColumn = {
    title: '备注',
    dataIndex: 'remark',
    key: 'remark',
    width: 200,
    render: (value) => renderRemark(value),
  };

  const columnOptions = [
    { label: '业务描述', value: '业务描述' },
    { label: '输入', value: '输入' },
    { label: '输出', value: '输出' },
    { label: '依赖项', value: '依赖项' },
    { label: '备注', value: '备注' },
  ];

  const resolvedColumns = [
    ...baseColumns,
    ...columnOptions
      .map((option) => option.value)
      .filter((key) => visibleColumns.includes(key) && optionalColumns[key])
      .map((key) => optionalColumns[key]),
    {
      ...estimateColumn,
    },
    ...(visibleColumns.includes('备注') ? [remarkColumn] : []),
  ];

  if (!tokenReady) {
    return (
      <Card title="输入邀请Token" style={{ maxWidth: 480, margin: '0 auto' }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Input
            placeholder="请输入邀请Token"
            value={token}
            onChange={(e) => setToken(e.target.value)}
          />
          <Button
            type="primary"
            onClick={() => {
              if (!token.trim()) {
                message.warning('请输入Token');
                return;
              }
              setTokenReady(true);
              localStorage.setItem(`INVITE_TOKEN_${taskId}`, token.trim());
            }}
          >
            进入评估
          </Button>
        </Space>
      </Card>
    );
  }

  return (
    <div className="evaluation-page">
      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        <Card>
          <Space direction="vertical" size={8}>
            <Text type="secondary">
              灰色数值为AI预估，点击可修改。未修改的值将以AI预估作为您的评估结果。
            </Text>
            {roundNo > 1 && (
              <Alert
                type="warning"
                message={`第${roundNo}轮仅展示高偏离功能点，共${highDeviationFeatures.length}条`}
                showIcon
              />
            )}
            {taskInfo && (
              <Text>
                任务：{taskInfo.name || taskInfo.id} ｜ 当前轮次：{roundNo}
              </Text>
            )}
          </Space>
        </Card>

        <Card loading={loading}>
          <div style={{ marginBottom: 12 }}>
            <Space>
              <Popover
                placement="bottom"
                title="列设置"
                content={(
                  <Checkbox.Group
                    value={visibleColumns}
                    options={columnOptions}
                    onChange={(values) => setVisibleColumns(values)}
                  />
                )}
              >
                <Button>列设置</Button>
              </Popover>
              <Button onClick={() => setVisibleColumns(DEFAULT_VISIBLE_COLUMNS)}>
                重置列
              </Button>
            </Space>
          </div>
          <Tabs
            activeKey={currentSystem}
            onChange={setCurrentSystem}
            items={Object.keys(systemsData).map(systemName => ({
              key: systemName,
              label: systemName,
              children: (
                <Table
                  rowKey="id"
                  dataSource={systemsData[systemName]}
                  columns={resolvedColumns}
                  pagination={false}
                  scroll={{ x: 1200 }}
                  rowClassName={(record) => (highDeviationSet.has(record.id) ? 'row-high-deviation' : '')}
                />
              ),
            }))}
          />
        </Card>

        <Card>
          <Space>
            {!hasSubmitted && (
              <Button type="primary" onClick={handleSubmit}>
                提交评估
              </Button>
            )}
            {hasSubmitted && (
              <Button danger onClick={handleWithdraw}>
                撤回评估
              </Button>
            )}
            <Button onClick={() => navigate('/tasks')}>返回列表</Button>
          </Space>
        </Card>
      </Space>
    </div>
  );
};

export default EvaluationPage;
