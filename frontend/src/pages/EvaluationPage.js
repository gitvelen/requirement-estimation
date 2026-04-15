import React, { useEffect, useMemo, useState, useCallback } from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import {
  Alert,
  Button,
  Card,
  Checkbox,
  Input,
  InputNumber,
  message,
  Popover,
  Space,
  Table,
  Tabs,
  Tag,
  Typography,
} from 'antd';
import { QuestionCircleOutlined } from '@ant-design/icons';
import axios from 'axios';
import ExpandableText from '../components/ExpandableText';

const { Text, Paragraph } = Typography;

const COLUMN_SETTING_KEY = 'EVALUATION_VISIBLE_COLUMNS';
const DEFAULT_VISIBLE_COLUMNS = ['业务描述', '输入', '输出', '依赖项', '备注'];

const resolveCompletenessTagColor = (score) => {
  if (!Number.isFinite(score)) {
    return 'default';
  }
  if (score < 60) {
    return 'error';
  }
  if (score < 80) {
    return 'warning';
  }
  return 'success';
};

const toNumberOrNull = (value) => {
  if (value === undefined || value === null || value === '') {
    return null;
  }
  const num = Number(value);
  return Number.isFinite(num) ? num : null;
};

const resolveFeatureEstimate = (record) => {
  const optimistic = toNumberOrNull(record?.optimistic);
  const mostLikely = toNumberOrNull(record?.mostLikely ?? record?.most_likely);
  const pessimistic = toNumberOrNull(record?.pessimistic);
  const expected = toNumberOrNull(record?.expected);
  const originalEstimate = toNumberOrNull(record?.originalEstimate);
  const aiEstimated = toNumberOrNull(record?.aiEstimatedDays);

  const degraded = Boolean(record?.estimationDegraded) || optimistic === null || mostLikely === null || pessimistic === null;
  const baseline = expected ?? aiEstimated ?? originalEstimate ?? 0;

  return {
    optimistic,
    mostLikely,
    pessimistic,
    expected: expected ?? baseline,
    originalEstimate,
    baseline,
    degraded,
  };
};

const isProfileContextUsed = (record) => Boolean(record?.profileContextUsed ?? record?.profile_context_used);

const formatProfileContextSource = (value) => {
  const normalized = String(value || 'none').trim().toLowerCase();
  if (normalized === 'canonical+wiki_candidate') {
    return '已发布画像 + wiki高置信候选补位';
  }
  if (normalized === 'canonical') {
    return '仅已发布画像';
  }
  if (normalized === 'wiki_candidate') {
    return '仅 wiki高置信候选';
  }
  return '未使用画像上下文';
};

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
  const [cosmicPopoverOpen, setCosmicPopoverOpen] = useState(false);

  const [completenessMap, setCompletenessMap] = useState({});

  const [visibleColumns, setVisibleColumns] = useState(() => {
    try {
      const raw = localStorage.getItem(COLUMN_SETTING_KEY);
      const parsed = raw ? JSON.parse(raw) : null;
      if (Array.isArray(parsed) && parsed.length) {
        return parsed;
      }
    } catch (error) {
      return DEFAULT_VISIBLE_COLUMNS;
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

  const fetchCompletenessBatch = useCallback(async (systemNames) => {
    if (!systemNames.length) {
      setCompletenessMap({});
      return;
    }

    const pairs = await Promise.all(
      systemNames.map(async (systemName) => {
        try {
          const response = await axios.get('/api/v1/system-profiles/completeness', {
            params: { system_name: systemName },
          });
          return [systemName, { ...(response.data || {}), unknown: false }];
        } catch (error) {
          return [systemName, { unknown: true }];
        }
      })
    );

    setCompletenessMap(Object.fromEntries(pairs));
  }, []);

  const fetchEvaluation = useCallback(async (inviteToken) => {
    try {
      setLoading(true);
      const response = await axios.get(`/api/v1/evaluation/${taskId}`, {
        params: { token: inviteToken },
      });
      const payload = response.data.data;
      const features = payload.features || {};
      const systemNames = Object.keys(features);

      setTaskInfo(payload.task);
      setSystemsData(features);
      setCurrentSystem((prev) => (prev && systemNames.includes(prev) ? prev : (systemNames[0] || '')));
      setDraftValues(payload.myEvaluation?.draftData || {});
      setHasSubmitted(payload.myEvaluation?.hasSubmitted || false);
      setRoundNo(payload.task?.currentRound || 1);
      setHighDeviationFeatures(payload.highDeviationFeatures || []);
      fetchCompletenessBatch(systemNames);
    } catch (error) {
      message.error(error.response?.data?.detail || '获取评估数据失败');
    } finally {
      setLoading(false);
    }
  }, [taskId, fetchCompletenessBatch]);

  useEffect(() => {
    if (tokenReady && token) {
      fetchEvaluation(token);
    }
  }, [tokenReady, token, fetchEvaluation]);

  useEffect(() => {
    try {
      localStorage.setItem(COLUMN_SETTING_KEY, JSON.stringify(visibleColumns));
    } catch (error) {
      return;
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
      Object.values(systemsData).forEach((list) => {
        list.forEach((item) => {
          const value = draftValues[item.id] !== undefined
            ? draftValues[item.id]
            : (item.myEvaluation !== null && item.myEvaluation !== undefined ? item.myEvaluation : item.aiEstimatedDays);
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
      setTimeout(() => navigate('/tasks'), 1200);
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
    const estimate = resolveFeatureEstimate(record);
    const baselineValue = estimate.baseline;
    const draftValue = draftValues[record.id];
    const submittedValue = record.myEvaluation !== null && record.myEvaluation !== undefined ? record.myEvaluation : undefined;
    const displayValue = draftValue !== undefined ? draftValue : (submittedValue !== undefined ? submittedValue : baselineValue);
    const isEdited = (draftValue !== undefined && draftValue !== baselineValue)
      || (draftValue === undefined && submittedValue !== undefined && submittedValue !== baselineValue);

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
            setDraftValues((prev) => ({ ...prev, [record.id]: value }));
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

  const renderExpandedEstimate = (record) => {
    const estimate = resolveFeatureEstimate(record);
    const profileContextUsed = isProfileContextUsed(record);
    const contextEvidence = (
      <div style={{ background: '#f8fafc', border: '1px solid #d9e2ec', borderRadius: 8, padding: 12 }}>
        <Space direction="vertical" size={6}>
          <Tag color={profileContextUsed ? 'blue' : 'default'}>
            {`画像上下文：${profileContextUsed ? '已使用' : '未使用'}`}
          </Tag>
          <Text>来源：{formatProfileContextSource(record?.contextSource || record?.context_source)}</Text>
        </Space>
      </div>
    );

    if (estimate.degraded) {
      return (
        <Space direction="vertical" size={8} style={{ width: '100%' }}>
          <Alert
            type="warning"
            showIcon
            message="LLM 估算未成功，显示为拆分阶段原始估值"
          />
          {contextEvidence}
        </Space>
      );
    }

    return (
      <div style={{ background: '#f6fbff', border: '1px solid #d6e4ff', borderRadius: 8, padding: 12 }}>
        <Space direction="vertical" size={6}>
          <Text>乐观值：{estimate.optimistic}</Text>
          <Text>最可能值：{estimate.mostLikely}</Text>
          <Text>悲观值：{estimate.pessimistic}</Text>
          <Text>估算理由：{record.reasoning || 'LLM 未返回理由'}</Text>
          {contextEvidence}
        </Space>
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
        {lines.map((line, index) => {
          const match = line.match(/^\[([^\]]+)\]\s*(.*)$/);
          if (!match) {
            return (
              <div key={`${index}_${line}`} style={{ marginBottom: 6 }}>
                <ExpandableText value={line} limit={150} />
              </div>
            );
          }
          const label = match[1];
          const content = match[2] || '';
          return (
            <div key={`${index}_${label}`} style={{ marginBottom: 6 }}>
              <Tag color={tagColors[label] || 'default'} style={{ marginRight: 6 }}>{label}</Tag>
              <ExpandableText value={content} limit={150} empty="-" />
            </div>
          );
        })}
      </div>
    );
  };

  const baseColumns = [
    { title: '序号', dataIndex: 'sequence', key: 'sequence', width: 80 },
    { title: '功能模块', dataIndex: 'module', key: 'module', width: 120 },
    { title: '功能点', dataIndex: 'name', key: 'name', width: 160, render: (value) => <ExpandableText value={value} limit={40} /> },
  ];

  const optionalColumns = {
    业务描述: {
      title: '业务描述',
      dataIndex: 'description',
      key: 'description',
      width: 280,
      render: (value) => <ExpandableText value={value} limit={80} />,
    },
    输入: {
      title: '输入',
      dataIndex: 'inputs',
      key: 'inputs',
      width: 200,
      render: (items) => <ExpandableText value={(items || []).join('、')} limit={80} />,
    },
    输出: {
      title: '输出',
      dataIndex: 'outputs',
      key: 'outputs',
      width: 200,
      render: (items) => <ExpandableText value={(items || []).join('、')} limit={80} />,
    },
    依赖项: {
      title: '依赖项',
      dataIndex: 'dependencies',
      key: 'dependencies',
      width: 200,
      render: (items) => <ExpandableText value={(items || []).join('、')} limit={80} />,
    },
  };

  const estimateColumn = {
    title: '期望人天数',
    key: 'estimate',
    width: 140,
    render: (_, record) => renderEstimateCell(record),
  };

  const remarkColumn = {
    title: '备注',
    dataIndex: 'remark',
    key: 'remark',
    width: 240,
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
    estimateColumn,
    ...(visibleColumns.includes('备注') ? [remarkColumn] : []),
  ];

  const renderCompletenessTabLabel = (systemName) => {
    const info = completenessMap[systemName] || {};
    const score = Number(info.completeness_score);
    const hasScore = Number.isFinite(score) && !info.unknown;
    const breakdown = info.breakdown || { code_scan: 0, documents: 0, esb: 0 };
    const tooltip = hasScore
      ? `完整度：${score}（代码${breakdown.code_scan || 0}，文档${breakdown.documents || 0}，ESB${breakdown.esb || 0}）`
      : '完整度未知';

    return (
      <Popover content={tooltip} title={systemName}>
        <Space size={6}>
          <span>{systemName}</span>
          <Tag color={resolveCompletenessTagColor(hasScore ? score : NaN)}>
            {hasScore ? `完整度 ${score}` : '完整度未知'}
          </Tag>
        </Space>
      </Popover>
    );
  };

  const currentCompleteness = completenessMap[currentSystem] || {};
  const currentScore = Number(currentCompleteness.completeness_score);
  const currentHasScore = Number.isFinite(currentScore) && !currentCompleteness.unknown;

  if (!tokenReady) {
    return (
      <Card title="输入邀请Token" style={{ maxWidth: 480, margin: '0 auto' }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Input placeholder="请输入邀请Token" value={token} onChange={(event) => setToken(event.target.value)} />
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
        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <Space size={8} align="center">
            <Text type="secondary">COSMIC规则</Text>
            <Popover
              trigger="click"
              placement="bottomRight"
              open={cosmicPopoverOpen}
              onOpenChange={setCosmicPopoverOpen}
              title={(
                <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                  <Text strong>COSMIC简明规则</Text>
                  <Button size="small" type="text" onClick={() => setCosmicPopoverOpen(false)}>
                    关闭
                  </Button>
                </Space>
              )}
              content={(
                <div style={{ width: 'min(86vw, 520px)', maxHeight: 360, overflowY: 'auto' }}>
                  <Space direction="vertical" size={8}>
                    <Paragraph style={{ marginBottom: 0 }}>
                      细粒度：每个按钮/操作可拆分为独立功能点；中等粒度：一个完整交易流程（输入+校验+处理+返回）作为一个功能点；粗粒度：一个业务模块作为一个功能点。
                    </Paragraph>
                    <Paragraph type="secondary" style={{ marginBottom: 0 }}>
                      评估时优先保证“功能边界清晰、输入输出明确”，避免过细拆分导致噪声。
                    </Paragraph>
                  </Space>
                </div>
              )}
            >
              <Button
                type="text"
                shape="circle"
                icon={<QuestionCircleOutlined />}
                aria-label="查看COSMIC规则"
              />
            </Popover>
          </Space>
        </div>

        <Card loading={loading}>
          <div style={{ marginBottom: 12 }}>
            <Space>
              <Popover
                placement="bottom"
                title="列设置"
                content={(
                  <Checkbox.Group value={visibleColumns} options={columnOptions} onChange={(values) => setVisibleColumns(values)} />
                )}
              >
                <Button>列设置</Button>
              </Popover>
              <Button onClick={() => setVisibleColumns(DEFAULT_VISIBLE_COLUMNS)}>重置列</Button>
            </Space>
          </div>

          <Tabs
            activeKey={currentSystem}
            onChange={setCurrentSystem}
            items={Object.keys(systemsData).map((systemName) => ({
              key: systemName,
              label: renderCompletenessTabLabel(systemName),
              children: (
                <Table
                  rowKey="id"
                  dataSource={systemsData[systemName]}
                  columns={resolvedColumns}
                  expandable={{
                    expandRowByClick: true,
                    expandedRowRender: renderExpandedEstimate,
                  }}
                  pagination={false}
                  scroll={{ x: 1400 }}
                  rowClassName={(record) => (highDeviationSet.has(record.id) ? 'row-high-deviation' : '')}
                />
              ),
            }))}
          />
        </Card>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', gap: 12, flexWrap: 'wrap' }}>
          <Card size="small" style={{ flex: 1, minWidth: 320 }}>
            <Space direction="vertical" size={8} style={{ width: '100%' }}>
              <Text type="secondary">灰色数值为AI预估，点击可修改。未修改的值将以AI预估作为您的评估结果。</Text>
              {taskInfo && (
                <Space wrap>
                  <Text>任务：{taskInfo.name || taskInfo.id} ｜ 当前轮次：{roundNo} ｜ 系统：{currentSystem || '-'}</Text>
                  <Tag color={resolveCompletenessTagColor(currentHasScore ? currentScore : NaN)}>
                    {currentHasScore ? `当前系统完整度 ${currentScore}` : '当前系统完整度未知'}
                  </Tag>
                </Space>
              )}
              {roundNo > 1 && (
                <Alert
                  type="warning"
                  message={`第${roundNo}轮仅展示高偏离功能点，共${highDeviationFeatures.length}条`}
                  showIcon
                />
              )}
            </Space>
          </Card>

          <Card size="small" bodyStyle={{ padding: '8px 12px' }}>
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
        </div>
      </Space>
    </div>
  );
};

export default EvaluationPage;
