import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Button, Card, InputNumber, message, Select, Space, Table, Typography } from 'antd';
import { DeleteOutlined, PlusOutlined } from '@ant-design/icons';
import axios from 'axios';

const { Title, Paragraph, Text } = Typography;

const SOURCE_OPTIONS = [
  { label: '材料(evidence)', value: 'evidence' },
  { label: '画像(profile)', value: 'profile' },
  { label: '代码(code)', value: 'code' },
  { label: 'ESB(esb)', value: 'esb' },
];

const LEVEL_OPTIONS = [
  { label: 'E3', value: 'E3' },
  { label: 'E2', value: 'E2' },
  { label: 'E1', value: 'E1' },
  { label: 'E0', value: 'E0' },
];

const createLevelId = () => `lvl_${Date.now()}_${Math.random().toString(16).slice(2, 8)}`;

const normalizeSourceList = (value) => {
  const options = new Set(SOURCE_OPTIONS.map((item) => item.value));

  if (Array.isArray(value)) {
    return value
      .map((item) => String(item || '').trim().toLowerCase())
      .filter((item, idx, arr) => item && options.has(item) && arr.indexOf(item) === idx);
  }

  if (typeof value === 'string') {
    return value
      .replace(/，|、|；/g, ',')
      .split(/[\n,;]+/)
      .map((item) => item.trim().toLowerCase())
      .filter((item, idx, arr) => item && options.has(item) && arr.indexOf(item) === idx);
  }

  return [];
};

const normalizeAnyGroups = (value) => {
  if (Array.isArray(value)) {
    return value
      .map((item) => normalizeSourceList(item))
      .filter((group) => group.length > 0);
  }
  if (typeof value === 'string') {
    return value
      .split(/[|\n]+/)
      .map((item) => normalizeSourceList(item))
      .filter((group) => group.length > 0);
  }
  return [];
};

const normalizeRuleLevel = (item, index) => {
  const raw = item && typeof item === 'object' ? item : {};
  const level = String(raw.level || 'E0').trim().toUpperCase();
  return {
    id: String(raw.id || createLevelId() || `${index}`),
    level: LEVEL_OPTIONS.some((option) => option.value === level) ? level : 'E0',
    all_of: normalizeSourceList(raw.all_of),
    any_of: normalizeSourceList(raw.any_of),
    any_groups: normalizeAnyGroups(raw.any_groups),
    none_of: normalizeSourceList(raw.none_of),
  };
};

const normalizeRules = (rules) => {
  const raw = rules && typeof rules === 'object' ? rules : {};
  const levels = Array.isArray(raw.levels) ? raw.levels.map(normalizeRuleLevel) : [];
  return {
    version: Number(raw.version) > 0 ? Number(raw.version) : 1,
    levels: levels.length ? levels : [normalizeRuleLevel({ level: 'E0' }, 0)],
  };
};

const toPayloadRules = (draft) => ({
  version: Number(draft?.version) > 0 ? Number(draft.version) : 1,
  levels: (draft?.levels || []).map((item) => {
    const payload = { level: item.level || 'E0' };
    if (Array.isArray(item.all_of) && item.all_of.length) {
      payload.all_of = item.all_of;
    }
    if (Array.isArray(item.any_of) && item.any_of.length) {
      payload.any_of = item.any_of;
    }
    if (Array.isArray(item.any_groups) && item.any_groups.length) {
      payload.any_groups = item.any_groups;
    }
    if (Array.isArray(item.none_of) && item.none_of.length) {
      payload.none_of = item.none_of;
    }
    return payload;
  }),
});

const EvidenceRuleConfigPage = () => {
  const [rulesDraft, setRulesDraft] = useState(normalizeRules({}));
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [logs, setLogs] = useState([]);

  const fetchRules = useCallback(async () => {
    try {
      setLoading(true);
      const response = await axios.get('/api/v1/evidence-level/rules');
      if (response.data.code === 200) {
        setRulesDraft(normalizeRules(response.data.data));
      }
    } catch (error) {
      message.error(error.response?.data?.detail || '获取规则失败');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchLogs = useCallback(async () => {
    try {
      const response = await axios.get('/api/v1/evidence-level/rules/logs');
      if (response.data.code === 200) {
        setLogs(response.data.data || []);
      }
    } catch (error) {
      message.error(error.response?.data?.detail || '获取变更日志失败');
    }
  }, []);

  useEffect(() => {
    fetchRules();
    fetchLogs();
  }, [fetchLogs, fetchRules]);

  const sourceOptionValues = useMemo(
    () => SOURCE_OPTIONS.map((item) => item.value),
    []
  );

  const updateLevel = (levelId, updater) => {
    setRulesDraft((prev) => ({
      ...prev,
      levels: prev.levels.map((level) => {
        if (level.id !== levelId) {
          return level;
        }
        const next = typeof updater === 'function' ? updater(level) : updater;
        return normalizeRuleLevel({ ...level, ...next }, 0);
      }),
    }));
  };

  const addLevel = () => {
    setRulesDraft((prev) => ({
      ...prev,
      levels: [
        ...prev.levels,
        normalizeRuleLevel({ id: createLevelId(), level: 'E0' }, prev.levels.length),
      ],
    }));
  };

  const removeLevel = (levelId) => {
    setRulesDraft((prev) => {
      const nextLevels = prev.levels.filter((item) => item.id !== levelId);
      return {
        ...prev,
        levels: nextLevels.length ? nextLevels : [normalizeRuleLevel({ level: 'E0' }, 0)],
      };
    });
  };

  const addAnyGroup = (levelId) => {
    updateLevel(levelId, (level) => ({
      any_groups: [...(level.any_groups || []), []],
    }));
  };

  const removeAnyGroup = (levelId, groupIndex) => {
    updateLevel(levelId, (level) => ({
      any_groups: (level.any_groups || []).filter((_, index) => index !== groupIndex),
    }));
  };

  const updateAnyGroup = (levelId, groupIndex, value) => {
    updateLevel(levelId, (level) => ({
      any_groups: (level.any_groups || []).map((group, index) => (index === groupIndex ? value : group)),
    }));
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      const payload = toPayloadRules(rulesDraft);
      const response = await axios.put('/api/v1/evidence-level/rules', { rules: payload });
      if (response.data.code === 200) {
        message.success('规则已更新');
        setRulesDraft(normalizeRules(response.data.data));
        fetchLogs();
      }
    } catch (error) {
      message.error(error.response?.data?.detail || '保存失败');
    } finally {
      setSaving(false);
    }
  };

  const columns = [
    { title: '时间', dataIndex: 'created_at', key: 'created_at', width: 180 },
    { title: '操作者', dataIndex: 'actor_name', key: 'actor_name', width: 120 },
    {
      title: '摘要',
      dataIndex: 'detail',
      key: 'detail',
      render: (detail) => <Text>{detail?.rules?.version ? `version=${detail.rules.version}` : '-'}</Text>,
    },
  ];

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: '0 auto' }}>
      <Title level={2}>证据等级规则配置</Title>
      <Paragraph type="secondary">
        仅管理员可修改证据等级判定规则，变更将记录日志。
      </Paragraph>

      <Card style={{ marginBottom: 16 }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Space align="center" wrap>
            <Text strong>规则版本</Text>
            <InputNumber
              min={1}
              precision={0}
              value={rulesDraft.version}
              onChange={(value) => {
                setRulesDraft((prev) => ({ ...prev, version: Number(value) > 0 ? Number(value) : 1 }));
              }}
              disabled={loading}
            />
            <Button icon={<PlusOutlined />} onClick={addLevel} disabled={loading}>
              新增等级规则
            </Button>
          </Space>

          {(rulesDraft.levels || []).map((item, index) => (
            <Card
              key={item.id}
              size="small"
              title={`规则 ${index + 1}`}
              extra={(
                <Button
                  type="text"
                  danger
                  size="small"
                  icon={<DeleteOutlined />}
                  onClick={() => removeLevel(item.id)}
                >
                  删除
                </Button>
              )}
            >
              <Space direction="vertical" size={10} style={{ width: '100%' }}>
                <Space wrap>
                  <Text>等级</Text>
                  <Select
                    style={{ width: 120 }}
                    value={item.level}
                    options={LEVEL_OPTIONS}
                    onChange={(value) => updateLevel(item.id, { level: value })}
                  />
                </Space>

                <Space direction="vertical" size={4} style={{ width: '100%' }}>
                  <Text>必须全部满足（all_of）</Text>
                  <Select
                    mode="multiple"
                    style={{ width: '100%' }}
                    options={SOURCE_OPTIONS}
                    value={item.all_of}
                    onChange={(value) => updateLevel(item.id, { all_of: value.filter((v) => sourceOptionValues.includes(v)) })}
                    placeholder="可多选"
                  />
                </Space>

                <Space direction="vertical" size={4} style={{ width: '100%' }}>
                  <Text>至少命中一项（any_of）</Text>
                  <Select
                    mode="multiple"
                    style={{ width: '100%' }}
                    options={SOURCE_OPTIONS}
                    value={item.any_of}
                    onChange={(value) => updateLevel(item.id, { any_of: value.filter((v) => sourceOptionValues.includes(v)) })}
                    placeholder="可多选"
                  />
                </Space>

                <Space direction="vertical" size={4} style={{ width: '100%' }}>
                  <Text>分组命中（any_groups，组间AND）</Text>
                  {(item.any_groups || []).map((group, groupIndex) => (
                    <Space key={`${item.id}-group-${groupIndex}`} style={{ width: '100%' }} align="start">
                      <Select
                        mode="multiple"
                        style={{ flex: 1 }}
                        options={SOURCE_OPTIONS}
                        value={group}
                        onChange={(value) => updateAnyGroup(item.id, groupIndex, value.filter((v) => sourceOptionValues.includes(v)))}
                        placeholder="每组至少命中一项"
                      />
                      <Button
                        danger
                        size="small"
                        icon={<DeleteOutlined />}
                        onClick={() => removeAnyGroup(item.id, groupIndex)}
                      >
                        删除分组
                      </Button>
                    </Space>
                  ))}
                  <Button size="small" onClick={() => addAnyGroup(item.id)} icon={<PlusOutlined />}>
                    新增分组
                  </Button>
                </Space>

                <Space direction="vertical" size={4} style={{ width: '100%' }}>
                  <Text>必须不满足（none_of）</Text>
                  <Select
                    mode="multiple"
                    style={{ width: '100%' }}
                    options={SOURCE_OPTIONS}
                    value={item.none_of}
                    onChange={(value) => updateLevel(item.id, { none_of: value.filter((v) => sourceOptionValues.includes(v)) })}
                    placeholder="可多选"
                  />
                </Space>
              </Space>
            </Card>
          ))}

          <Text type="secondary">
            条件说明：`all_of` 全命中；`any_of` 命中其一；`any_groups` 每个分组至少命中一项（组间 AND）；`none_of` 必须不命中。
          </Text>

          <Space>
            <Button type="primary" onClick={handleSave} loading={saving || loading}>
              保存规则
            </Button>
            <Button onClick={fetchRules} loading={loading}>重载规则</Button>
          </Space>

          <Text type="secondary" style={{ fontSize: 12 }}>
            当前为结构化编辑，不需要输入 JSON。
          </Text>
        </Space>
      </Card>

      <Card title="变更日志">
        <Table rowKey="id" columns={columns} dataSource={logs} pagination={{ pageSize: 6 }} />
      </Card>
    </div>
  );
};

export default EvidenceRuleConfigPage;
