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
import {
  PROFILE_FIELD_LABELS_V21,
  buildEmptyV21ProfileFormValues,
  parseModuleStructureDraft,
  parseV21ProfileFormValues,
  stringifyModuleStructureDraft,
} from '../utils/systemProfileV21';

const { TextArea } = Input;
const { Text, Title } = Typography;

const emptyFormValues = buildEmptyV21ProfileFormValues();

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
        form.setFieldsValue({
          ...emptyFormValues,
          ...fields,
          module_structure: stringifyModuleStructureDraft(fields.module_structure),
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
    const parsed = parseV21ProfileFormValues(values);
    if (!parsed.ok) {
      message.error(parsed.message || 'module_structure 格式错误，需为 JSON 数组');
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
    const parsed = parseV21ProfileFormValues(values);
    if (!parsed.ok) {
      message.error(parsed.message || 'module_structure 格式错误，需为 JSON 数组');
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

  const handleFormatModuleStructure = () => {
    const currentText = form.getFieldValue('module_structure');
    const parsed = parseModuleStructureDraft(currentText);
    if (!parsed.ok) {
      message.error(parsed.message || 'module_structure 格式错误，需为 JSON 数组');
      return;
    }
    try {
      form.setFieldValue('module_structure', stringifyModuleStructureDraft(parsed.value));
      message.success('JSON 已格式化');
    } catch (_error) {
      message.error('格式化失败');
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
                column={2}
                items={[
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
                {Object.entries(PROFILE_FIELD_LABELS_V21).map(([key, label]) => (
                  <div key={key}>
                    <Form.Item
                      name={key}
                      label={label}
                      rules={key === 'module_structure'
                        ? [
                          {
                            validator: (_rule, value) => {
                              const parsed = parseModuleStructureDraft(value);
                              if (parsed.ok) {
                                return Promise.resolve();
                              }
                              return Promise.reject(new Error('请输入合法 JSON 数组'));
                            },
                          },
                        ]
                        : undefined}
                    >
                      <TextArea
                        rows={key === 'module_structure' ? 10 : 3}
                        placeholder={key === 'module_structure'
                          ? '请输入 JSON 数组，例如：[{"module_name":"用户管理","functions":[{"name":"用户注册","desc":"新用户注册流程"}]}]'
                          : `请输入${label}`}
                      />
                    </Form.Item>
                    {key === 'module_structure' && canWrite && (
                      <Space style={{ marginBottom: 12 }}>
                        <Button size="small" onClick={handleFormatModuleStructure}>
                          一键格式化
                        </Button>
                      </Space>
                    )}
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
