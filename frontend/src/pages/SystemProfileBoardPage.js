import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Descriptions,
  Form,
  Input,
  message,
  Progress,
  Space,
  Tabs,
  Tag,
  Typography,
} from 'antd';
import { ReloadOutlined, SaveOutlined, SendOutlined } from '@ant-design/icons';
import { useLocation, useNavigate } from 'react-router-dom';
import axios from 'axios';
import PageHeader from '../components/PageHeader';
import useAuth from '../hooks/useAuth';
import usePermission from '../hooks/usePermission';
import { formatDateTime } from '../utils/time';
import { filterResponsibleSystems, resolveSystemOwnership } from '../utils/systemOwnership';

const { TextArea } = Input;
const { Text, Title } = Typography;

const fieldLabels = {
  in_scope: '系统边界（做什么）',
  out_of_scope: '系统不做什么',
  core_functions: '核心功能',
  business_goals: '业务目标',
  business_objects: '业务对象',
  integration_points: '主要集成点',
  key_constraints: '关键约束',
};

const emptyFormValues = Object.keys(fieldLabels).reduce((acc, key) => ({ ...acc, [key]: '' }), {});

const parseErrorMessage = (error, fallback) => {
  const responseData = error?.response?.data;
  return responseData?.message || responseData?.detail || fallback;
};

const SystemProfileBoardPage = () => {
  const { user } = useAuth();
  const { isManager } = usePermission();
  const location = useLocation();
  const navigate = useNavigate();
  const [form] = Form.useForm();

  const [systems, setSystems] = useState([]);
  const [selectedSystemName, setSelectedSystemName] = useState('');

  const [loadingProfile, setLoadingProfile] = useState(false);
  const [savingProfile, setSavingProfile] = useState(false);
  const [publishingProfile, setPublishingProfile] = useState(false);
  const [retryingSuggestions, setRetryingSuggestions] = useState(false);

  const [profileMeta, setProfileMeta] = useState({
    status: 'draft',
    pending_fields: [],
    updated_at: '',
    is_stale: false,
    system_id: '',
    field_sources: {},
    ai_suggestions: {},
    ai_suggestions_updated_at: '',
    ai_suggestions_job: null,
  });

  const [completenessInfo, setCompletenessInfo] = useState(null);
  const [completenessUnknown, setCompletenessUnknown] = useState(false);

  const queryParams = useMemo(() => new URLSearchParams(location.search), [location.search]);

  const responsibleSystems = useMemo(() => filterResponsibleSystems(systems, user), [systems, user]);

  const selectedSystem = useMemo(
    () => responsibleSystems.find((item) => item.name === selectedSystemName),
    [responsibleSystems, selectedSystemName]
  );

  const canWrite = useMemo(() => {
    if (!isManager || !selectedSystem) {
      return false;
    }
    return resolveSystemOwnership(selectedSystem, user).canWrite;
  }, [isManager, selectedSystem, user]);

  const loadSystems = useCallback(async () => {
    try {
      const response = await axios.get('/api/v1/system/systems');
      const items = response.data?.data?.systems || [];
      setSystems(items);
    } catch (error) {
      message.error(parseErrorMessage(error, '加载系统清单失败'));
    }
  }, []);

  const syncSelectedSystemFromUrl = useCallback((items) => {
    if (!items.length) {
      setSelectedSystemName('');
      return;
    }

    const systemNameInUrl = String(queryParams.get('system_name') || '').trim();
    const existsInList = systemNameInUrl && items.some((item) => item.name === systemNameInUrl);
    const nextName = existsInList ? systemNameInUrl : items[0].name;

    setSelectedSystemName(nextName);

    const nextSystem = items.find((item) => item.name === nextName);
    const nextId = String(nextSystem?.id || '').trim();
    const urlName = String(queryParams.get('system_name') || '').trim();
    const urlId = String(queryParams.get('system_id') || '').trim();
    if (urlName !== nextName || urlId !== nextId) {
      const nextParams = new URLSearchParams(location.search);
      nextParams.set('system_name', nextName);
      if (nextId) {
        nextParams.set('system_id', nextId);
      } else {
        nextParams.delete('system_id');
      }
      navigate({ pathname: location.pathname, search: `?${nextParams.toString()}` }, { replace: true });
    }
  }, [location.pathname, location.search, navigate, queryParams]);

  const loadCompleteness = useCallback(async (systemName) => {
    if (!systemName) {
      setCompletenessInfo(null);
      setCompletenessUnknown(false);
      return;
    }

    try {
      setCompletenessUnknown(false);
      const response = await axios.get('/api/v1/system-profiles/completeness', {
        params: { system_name: systemName },
      });
      setCompletenessInfo(response.data || null);
    } catch (error) {
      setCompletenessUnknown(true);
      setCompletenessInfo(null);
    }
  }, []);

  const loadProfileDetail = useCallback(async (systemName) => {
    if (!systemName) {
      return;
    }

    setLoadingProfile(true);
    try {
      const response = await axios.get(`/api/v1/system-profiles/${encodeURIComponent(systemName)}`);
      const payload = response.data?.data;

      if (payload) {
        const fields = typeof payload.fields === 'object' && payload.fields ? payload.fields : {};
        form.setFieldsValue({ ...emptyFormValues, ...fields });
        setProfileMeta({
          status: payload.status || 'draft',
          pending_fields: payload.pending_fields || [],
          updated_at: payload.updated_at || payload.created_at || '',
          is_stale: Boolean(payload.is_stale),
          system_id: String(payload.system_id || selectedSystem?.id || ''),
          field_sources: payload.field_sources || {},
          ai_suggestions: payload.ai_suggestions || {},
          ai_suggestions_updated_at: payload.ai_suggestions_updated_at || '',
          ai_suggestions_job: payload.ai_suggestions_job || null,
        });
      } else {
        form.setFieldsValue(emptyFormValues);
        setProfileMeta({
          status: 'draft',
          pending_fields: [],
          updated_at: '',
          is_stale: false,
          system_id: String(selectedSystem?.id || ''),
          field_sources: {},
          ai_suggestions: {},
          ai_suggestions_updated_at: '',
          ai_suggestions_job: null,
        });
      }

      await loadCompleteness(systemName);
    } catch (error) {
      message.error(parseErrorMessage(error, '加载系统画像详情失败'));
    } finally {
      setLoadingProfile(false);
    }
  }, [form, loadCompleteness, selectedSystem?.id]);

  useEffect(() => {
    loadSystems();
  }, [loadSystems]);

  useEffect(() => {
    if (!responsibleSystems.length) {
      return;
    }
    syncSelectedSystemFromUrl(responsibleSystems);
  }, [responsibleSystems, syncSelectedSystemFromUrl]);

  useEffect(() => {
    if (!selectedSystemName) {
      return;
    }
    loadProfileDetail(selectedSystemName);
  }, [loadProfileDetail, selectedSystemName]);

  const handleSystemTabChange = (systemName) => {
    const nextName = String(systemName || '').trim();
    if (!nextName) {
      return;
    }

    const system = responsibleSystems.find((item) => item.name === nextName);
    const nextParams = new URLSearchParams(location.search);
    nextParams.set('system_name', nextName);
    const systemId = String(system?.id || '').trim();
    if (systemId) {
      nextParams.set('system_id', systemId);
    } else {
      nextParams.delete('system_id');
    }
    navigate({ pathname: location.pathname, search: `?${nextParams.toString()}` }, { replace: true });
    setSelectedSystemName(nextName);
  };

  const handleSaveDraft = async () => {
    if (!selectedSystemName) {
      message.warning('请先选择系统');
      return;
    }

    try {
      const values = form.getFieldsValue(true);
      setSavingProfile(true);
      const currentValues = form.getFieldsValue(true);
      const mergedFieldSources = { ...(profileMeta.field_sources || {}) };
      Object.keys(currentValues || {}).forEach((fieldKey) => {
        mergedFieldSources[fieldKey] = 'manual';
      });

      await axios.put(`/api/v1/system-profiles/${encodeURIComponent(selectedSystemName)}`, {
        system_id: profileMeta.system_id || selectedSystem?.id || '',
        fields: values,
        evidence_refs: [],
        field_sources: mergedFieldSources,
      });
      message.success('系统画像草稿已保存');
      await loadProfileDetail(selectedSystemName);
    } catch (error) {
      message.error(parseErrorMessage(error, '保存系统画像失败'));
    } finally {
      setSavingProfile(false);
    }
  };

  const handlePublish = async () => {
    if (!selectedSystemName) {
      message.warning('请先选择系统');
      return;
    }

    try {
      await form.validateFields(['in_scope', 'core_functions']);
    } catch (_error) {
      return;
    }

    setPublishingProfile(true);
    try {
      await axios.post(`/api/v1/system-profiles/${encodeURIComponent(selectedSystemName)}/publish`);
      message.success('系统画像已发布');
      await loadProfileDetail(selectedSystemName);
    } catch (error) {
      message.error(parseErrorMessage(error, '发布系统画像失败'));
    } finally {
      setPublishingProfile(false);
    }
  };

  const handleRetrySuggestions = async () => {
    if (!selectedSystem?.id) {
      message.warning('请选择有效系统');
      return;
    }

    setRetryingSuggestions(true);
    try {
      const response = await axios.post(
        `/api/v1/system-profiles/${encodeURIComponent(selectedSystem.id)}/ai-suggestions/retry`
      );
      const result = response.data || {};
      message.success(result.message || 'AI建议生成任务已受理');
      await loadProfileDetail(selectedSystemName);
    } catch (error) {
      message.error(parseErrorMessage(error, '触发AI建议重试失败'));
    } finally {
      setRetryingSuggestions(false);
    }
  };

  const handleApplySuggestion = async (fieldKey) => {
    if (!fieldKey) {
      return;
    }
    const suggestions = profileMeta.ai_suggestions || {};
    const suggestedValue = suggestions[fieldKey];
    if (typeof suggestedValue !== 'string') {
      return;
    }

    const currentValues = form.getFieldsValue(true);
    const nextValues = {
      ...currentValues,
      [fieldKey]: suggestedValue,
    };
    const mergedFieldSources = { ...(profileMeta.field_sources || {}), [fieldKey]: 'ai' };

    setSavingProfile(true);
    try {
      await axios.put(`/api/v1/system-profiles/${encodeURIComponent(selectedSystemName)}`, {
        system_id: profileMeta.system_id || selectedSystem?.id || '',
        fields: nextValues,
        evidence_refs: [],
        field_sources: mergedFieldSources,
      });
      form.setFieldValue(fieldKey, suggestedValue);
      message.success('已采纳AI建议');
      await loadProfileDetail(selectedSystemName);
    } catch (error) {
      message.error(parseErrorMessage(error, '采纳AI建议失败'));
    } finally {
      setSavingProfile(false);
    }
  };

  const handleIgnoreSuggestion = async (fieldKey) => {
    if (!fieldKey) {
      return;
    }

    const currentValues = form.getFieldsValue(true);
    const mergedFieldSources = { ...(profileMeta.field_sources || {}), [fieldKey]: 'manual' };

    setSavingProfile(true);
    try {
      await axios.put(`/api/v1/system-profiles/${encodeURIComponent(selectedSystemName)}`, {
        system_id: profileMeta.system_id || selectedSystem?.id || '',
        fields: currentValues,
        evidence_refs: [],
        field_sources: mergedFieldSources,
      });
      message.success('已忽略该AI建议');
      await loadProfileDetail(selectedSystemName);
    } catch (error) {
      message.error(parseErrorMessage(error, '忽略AI建议失败'));
    } finally {
      setSavingProfile(false);
    }
  };

  const profileStatusTag = useMemo(() => (
    <Tag color={profileMeta.status === 'published' ? 'green' : 'gold'}>
      {profileMeta.status === 'published' ? '已发布' : '草稿'}
    </Tag>
  ), [profileMeta.status]);

  const totalScore = completenessInfo?.completeness_score ?? 0;
  const breakdown = completenessInfo?.breakdown || {};

  return (
    <div>
      <PageHeader
        title="系统画像 / 信息看板"
        subtitle="配置管理 → 系统画像 → 信息看板（可编辑7字段、完整度分析、保存草稿/发布）"
      />

      {responsibleSystems.length === 0 ? (
        <Card>
          <Text type="secondary">暂无可操作系统（仅展示主责/B角系统）。请联系管理员维护系统负责关系。</Text>
        </Card>
      ) : (
        <Space direction="vertical" style={{ width: '100%' }} size={12}>
          <Card>
            <Space direction="vertical" style={{ width: '100%' }} size={8}>
              <Tabs
                activeKey={selectedSystemName || undefined}
                onChange={handleSystemTabChange}
                items={responsibleSystems.map((item) => ({ key: item.name, label: item.name }))}
              />

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
                <Title level={4} style={{ margin: 0 }}>{selectedSystemName || '-'}</Title>
                <Space>
                  {profileStatusTag}
                  {profileMeta.is_stale && <Tag color="orange">画像过时</Tag>}
                  <Text type="secondary">最后更新：{formatDateTime(profileMeta.updated_at)}</Text>
                </Space>
              </div>

              <Descriptions
                size="small"
                column={3}
                items={[
                  { key: 'id', label: '系统ID', children: selectedSystem?.id || profileMeta.system_id || '-' },
                  { key: 'status', label: '系统状态', children: selectedSystem?.status || '-' },
                  { key: 'score', label: '完整度', children: `${totalScore} / 100` },
                ]}
              />

              {completenessUnknown ? (
                <Alert
                  type="warning"
                  showIcon
                  message="完整度未知"
                  description="完整度接口暂时不可用，不影响继续查看与编辑画像。"
                />
              ) : (
                <Space direction="vertical" style={{ width: '100%' }} size={6}>
                  <Text type="secondary">完整度分析</Text>
                  <Progress percent={breakdown.code_scan ?? 0} size="small" strokeColor="#1677ff" format={(p) => `代码扫描 ${p}/30`} />
                  <Progress percent={breakdown.documents ?? 0} size="small" strokeColor="#52c41a" format={(p) => `文档 ${p}/40`} />
                  <Progress percent={breakdown.esb ?? 0} size="small" strokeColor="#faad14" format={(p) => `ESB ${p}/30`} />
                </Space>
              )}

              {!canWrite && (
                <Alert
                  type="warning"
                  showIcon
                  message="当前系统为只读"
                  description="仅系统主责或B角 PM 可执行保存草稿；发布仅主责可执行。"
                />
              )}

              {canWrite && (
                <Alert
                  type="info"
                  showIcon
                  message="AI建议"
                  description={(
                    <Space direction="vertical" size={4}>
                      <Text type="secondary">
                        建议更新时间：{formatDateTime(profileMeta.ai_suggestions_updated_at) || '暂无'}
                      </Text>
                      <Text type="secondary">
                        任务状态：{profileMeta.ai_suggestions_job?.status || '未触发'}
                      </Text>
                      <Space>
                        <Button
                          size="small"
                          icon={<ReloadOutlined />}
                          loading={retryingSuggestions}
                          onClick={handleRetrySuggestions}
                        >
                          重试生成AI建议
                        </Button>
                      </Space>
                    </Space>
                  )}
                />
              )}
            </Space>
          </Card>

          <Card
            title="画像字段（可编辑）"
            loading={loadingProfile}
            extra={(
              <Button icon={<ReloadOutlined />} onClick={() => loadProfileDetail(selectedSystemName)}>
                重新加载
              </Button>
            )}
          >
            <Space direction="vertical" style={{ width: '100%' }} size={12}>
              <Form form={form} layout="vertical" initialValues={emptyFormValues} disabled={!canWrite}>
                {Object.entries(fieldLabels).map(([key, label]) => (
                  <div key={key}>
                    <Form.Item
                      name={key}
                      label={label}
                      rules={[
                        key === 'in_scope' || key === 'core_functions'
                          ? { required: true, message: `请填写${label}` }
                          : {},
                      ]}
                    >
                      <TextArea rows={2} placeholder={`请输入${label}`} />
                    </Form.Item>
                    {(() => {
                      const suggestions = profileMeta.ai_suggestions || {};
                      const suggestionText = String(suggestions[key] || '').trim();
                      if (!suggestionText) {
                        return null;
                      }
                      const currentSource = String((profileMeta.field_sources || {})[key] || 'manual');
                      return (
                        <Alert
                          type="info"
                          showIcon
                          style={{ marginBottom: 12 }}
                          message={`AI建议（当前来源：${currentSource}）`}
                          description={(
                            <Space direction="vertical" size={8} style={{ width: '100%' }}>
                              <Text>{suggestionText}</Text>
                              {canWrite && (
                                <Space>
                                  <Button size="small" type="primary" onClick={() => handleApplySuggestion(key)}>
                                    采纳
                                  </Button>
                                  <Button size="small" onClick={() => handleIgnoreSuggestion(key)}>
                                    忽略
                                  </Button>
                                </Space>
                              )}
                            </Space>
                          )}
                        />
                      );
                    })()}
                  </div>
                ))}
              </Form>

              {canWrite && (
                <Space>
                  <Button type="primary" icon={<SaveOutlined />} loading={savingProfile} onClick={handleSaveDraft}>
                    保存草稿
                  </Button>
                  <Button icon={<SendOutlined />} loading={publishingProfile} onClick={handlePublish}>
                    发布画像
                  </Button>
                </Space>
              )}

              <Space wrap>
                <Text type="secondary">待补证据字段：</Text>
                {(profileMeta.pending_fields || []).length > 0
                  ? profileMeta.pending_fields.map((item) => <Tag key={item}>{item}</Tag>)
                  : <Text type="secondary">无</Text>}
              </Space>
            </Space>
          </Card>
        </Space>
      )}
    </div>
  );
};

export default SystemProfileBoardPage;
