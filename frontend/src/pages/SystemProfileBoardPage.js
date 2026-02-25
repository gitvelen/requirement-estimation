import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Form,
  Input,
  message,
  Space,
  Tabs,
  Tag,
  Typography,
} from 'antd';
import { DeleteOutlined, PlusOutlined, ReloadOutlined, SaveOutlined, SendOutlined } from '@ant-design/icons';
import { useLocation, useNavigate } from 'react-router-dom';
import axios from 'axios';
import useAuth from '../hooks/useAuth';
import usePermission from '../hooks/usePermission';
import { formatDateTime } from '../utils/time';
import { filterResponsibleSystems, resolveSystemOwnership } from '../utils/systemOwnership';
import {
  PROFILE_FIELD_LABELS_V21,
  parseV21ProfileFormValues,
} from '../utils/systemProfileV21';

const { Text } = Typography;

const TEXT_FIELD_LABELS = Object.fromEntries(
  Object.entries(PROFILE_FIELD_LABELS_V21).filter(([key]) => key !== 'module_structure')
);

const emptyFormValues = {
  system_scope: '',
  integration_points: '',
  key_constraints: '',
  modules: [],
};

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

  const [profileMeta, setProfileMeta] = useState({
    status: 'draft',
    pending_fields: [],
    updated_at: '',
    is_stale: false,
    system_id: '',
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
        const moduleArray = Array.isArray(fields.module_structure) ? fields.module_structure : [];
        const modules = moduleArray.map((m) => ({
          module_name: m.module_name || '',
          functions: (m.functions || []).map((f) => ({ name: f.name || '', desc: f.desc || '' })),
        }));
        form.setFieldsValue({
          ...emptyFormValues,
          system_scope: fields.system_scope || '',
          integration_points: fields.integration_points || '',
          key_constraints: fields.key_constraints || '',
          modules,
        });
        setProfileMeta({
          status: payload.status || 'draft',
          pending_fields: payload.pending_fields || [],
          updated_at: payload.updated_at || payload.created_at || '',
          is_stale: Boolean(payload.is_stale),
          system_id: String(payload.system_id || selectedSystem?.id || ''),
        });
      } else {
        form.setFieldsValue(emptyFormValues);
        setProfileMeta({
          status: 'draft',
          pending_fields: [],
          updated_at: '',
          is_stale: false,
          system_id: String(selectedSystem?.id || ''),
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

    const values = form.getFieldsValue(true);
    const moduleStructure = (values.modules || [])
      .filter((m) => m && m.module_name)
      .map((m) => ({
        module_name: m.module_name,
        functions: (m.functions || []).filter((f) => f && f.name).map((f) => ({ name: f.name, desc: f.desc || '' })),
      }));
    const parsed = parseV21ProfileFormValues({ ...values, module_structure: moduleStructure });
    if (!parsed.ok) {
      message.error(parsed.message || '数据格式错误');
      return;
    }

    try {
      setSavingProfile(true);

      await axios.put(`/api/v1/system-profiles/${encodeURIComponent(selectedSystemName)}`, {
        system_id: profileMeta.system_id || selectedSystem?.id || '',
        fields: parsed.value,
        evidence_refs: [],
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

    const values = form.getFieldsValue(true);
    const moduleStructure = (values.modules || [])
      .filter((m) => m && m.module_name)
      .map((m) => ({
        module_name: m.module_name,
        functions: (m.functions || []).filter((f) => f && f.name).map((f) => ({ name: f.name, desc: f.desc || '' })),
      }));
    const parsed = parseV21ProfileFormValues({ ...values, module_structure: moduleStructure });
    if (!parsed.ok) {
      message.error(parsed.message || '数据格式错误');
      return;
    }
    if (!parsed.value.system_scope) {
      message.warning('请先填写系统定位与边界');
      return;
    }
    if (!Array.isArray(parsed.value.module_structure) || parsed.value.module_structure.length === 0) {
      message.warning('请先填写功能模块结构（至少包含一个模块）');
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

  const profileStatusTag = useMemo(() => (
    <Tag color={profileMeta.status === 'published' ? 'green' : 'gold'}>
      {profileMeta.status === 'published' ? '已发布' : '草稿'}
    </Tag>
  ), [profileMeta.status]);

  const totalScore = completenessInfo?.completeness_score ?? 0;
  const breakdown = completenessInfo?.breakdown || {};

  return (
    <div>
      {responsibleSystems.length === 0 ? (
        <Card>
          <Text type="secondary">暂无可操作系统（仅展示主责/B角系统）。请联系管理员维护系统负责关系。</Text>
        </Card>
      ) : (
        <Space direction="vertical" style={{ width: '100%' }} size={12}>
          <Space direction="vertical" style={{ width: '100%' }} size={6}>
            <Tabs
              size="small"
              activeKey={selectedSystemName || undefined}
              onChange={handleSystemTabChange}
              items={responsibleSystems.map((item) => ({ key: item.name, label: item.name }))}
            />

            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
              {profileStatusTag}
              {profileMeta.is_stale && <Tag color="orange">画像过时</Tag>}
              <Tag>{selectedSystem?.status || '-'}</Tag>
              {completenessUnknown ? (
                <Tag color="default">完整度未知</Tag>
              ) : (
                <>
                  <Tag color="blue">完整度 {totalScore}/100</Tag>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    代码{breakdown.code_scan ?? 0}/30 · 文档{breakdown.documents ?? 0}/40 · ESB{breakdown.esb ?? 0}/30
                  </Text>
                </>
              )}
              <Text type="secondary" style={{ fontSize: 12, marginLeft: 'auto' }}>
                更新：{formatDateTime(profileMeta.updated_at)}
              </Text>
            </div>

            {!canWrite && (
              <Alert
                type="warning"
                showIcon
                message="当前系统为只读"
                description="仅系统主责或B角 PM 可执行保存草稿；发布仅主责可执行。"
              />
            )}
          </Space>

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
                {Object.entries(TEXT_FIELD_LABELS).map(([key, label]) => (
                  <Form.Item key={key} name={key} label={label}>
                    <Input.TextArea rows={3} placeholder={`请输入${label}`} />
                  </Form.Item>
                ))}

                <Form.Item label="功能模块结构">
                  <Form.List name="modules">
                    {(moduleFields, { add: addModule, remove: removeModule }) => (
                      <Space direction="vertical" style={{ width: '100%' }} size={8}>
                        {moduleFields.map((moduleField) => (
                          <Card
                            key={moduleField.key}
                            size="small"
                            title={
                              <Form.Item name={[moduleField.name, 'module_name']} noStyle>
                                <Input placeholder="模块名称" style={{ width: 200 }} />
                              </Form.Item>
                            }
                            extra={
                              canWrite && (
                                <Button type="text" danger icon={<DeleteOutlined />} onClick={() => removeModule(moduleField.name)} />
                              )
                            }
                          >
                            <Form.List name={[moduleField.name, 'functions']}>
                              {(funcFields, { add: addFunc, remove: removeFunc }) => (
                                <Space direction="vertical" style={{ width: '100%' }} size={4}>
                                  {funcFields.map((funcField) => (
                                    <Space key={funcField.key} align="baseline" style={{ width: '100%' }}>
                                      <Form.Item name={[funcField.name, 'name']} noStyle>
                                        <Input placeholder="功能名称" style={{ width: 160 }} />
                                      </Form.Item>
                                      <Form.Item name={[funcField.name, 'desc']} noStyle>
                                        <Input placeholder="功能描述" style={{ width: 240 }} />
                                      </Form.Item>
                                      {canWrite && (
                                        <Button type="text" danger size="small" icon={<DeleteOutlined />} onClick={() => removeFunc(funcField.name)} />
                                      )}
                                    </Space>
                                  ))}
                                  {canWrite && (
                                    <Button type="dashed" size="small" onClick={() => addFunc({ name: '', desc: '' })} icon={<PlusOutlined />}>
                                      添加功能
                                    </Button>
                                  )}
                                </Space>
                              )}
                            </Form.List>
                          </Card>
                        ))}
                        {canWrite && (
                          <Button
                            type="dashed"
                            onClick={() => addModule({ module_name: '', functions: [{ name: '', desc: '' }] })}
                            icon={<PlusOutlined />}
                            style={{ width: '100%' }}
                          >
                            添加模块
                          </Button>
                        )}
                      </Space>
                    )}
                  </Form.List>
                </Form.Item>
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
