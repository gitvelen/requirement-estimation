import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Button,
  Card,
  Input,
  List,
  message,
  Space,
  Tabs,
  Tag,
  Typography,
} from 'antd';
import { LeftOutlined, ReloadOutlined, RightOutlined, SaveOutlined, SendOutlined } from '@ant-design/icons';
import { useLocation, useNavigate } from 'react-router-dom';
import axios from 'axios';
import useAuth from '../hooks/useAuth';
import usePermission from '../hooks/usePermission';
import { formatDateTime } from '../utils/time';
import { filterResponsibleSystems, resolveSystemOwnership } from '../utils/systemOwnership';

const { Text } = Typography;

const PROFILE_DOMAIN_CONFIG = [
  {
    key: 'system_positioning',
    label: 'D1 系统定位与边界',
    fields: [
      { key: 'system_description', label: '系统描述', type: 'text', empty: '' },
      { key: 'target_users', label: '目标用户', type: 'list', empty: [] },
      { key: 'boundaries', label: '边界说明', type: 'list', empty: [] },
    ],
  },
  {
    key: 'business_capabilities',
    label: 'D2 业务能力与流程',
    fields: [
      { key: 'module_structure', label: '模块结构', type: 'structured', empty: [] },
      { key: 'core_processes', label: '核心流程', type: 'list', empty: [] },
    ],
  },
  {
    key: 'integration_interfaces',
    label: 'D3 集成与接口',
    fields: [
      { key: 'integration_points', label: '集成点', type: 'structured', empty: [] },
      { key: 'external_dependencies', label: '外部依赖', type: 'list', empty: [] },
    ],
  },
  {
    key: 'technical_architecture',
    label: 'D4 技术架构',
    fields: [
      { key: 'architecture_positioning', label: '架构定位', type: 'text', empty: '' },
      { key: 'tech_stack', label: '技术栈', type: 'list', empty: [] },
      { key: 'performance_profile', label: '性能画像', type: 'structured', empty: {} },
    ],
  },
  {
    key: 'constraints_risks',
    label: 'D5 约束与风险',
    fields: [
      { key: 'key_constraints', label: '关键约束', type: 'structured', empty: [] },
      { key: 'known_risks', label: '已知风险', type: 'list', empty: [] },
    ],
  },
];

const PROFILE_DOMAIN_BY_KEY = Object.fromEntries(PROFILE_DOMAIN_CONFIG.map((item) => [item.key, item]));

const EVENT_TYPE_LABELS = {
  document_import: '文档导入',
  code_scan: '代码扫描',
  manual_edit: '手动编辑',
  ai_suggestion_accept: '采纳建议',
  ai_suggestion_ignore: '忽略建议',
  ai_suggestion_rollback: '建议回滚',
  profile_publish: '画像发布',
};

const getFieldPath = (domainKey, fieldKey) => `${domainKey}.${fieldKey}`;

const deepClone = (value) => JSON.parse(JSON.stringify(value));

const FIELD_EDITOR_KIND = {
  [getFieldPath('business_capabilities', 'module_structure')]: 'module_structure',
  [getFieldPath('integration_interfaces', 'integration_points')]: 'integration_points',
  [getFieldPath('technical_architecture', 'performance_profile')]: 'performance_profile',
  [getFieldPath('constraints_risks', 'key_constraints')]: 'key_constraints',
};

const normalizeStringList = (value) => {
  if (Array.isArray(value)) {
    return value
      .map((item) => String(item ?? '').trim())
      .filter(Boolean);
  }
  if (typeof value === 'string') {
    return value
      .split(/[\n,，、;；]+/)
      .map((item) => item.trim())
      .filter(Boolean);
  }
  return [];
};

const normalizeModuleStructureDraft = (value) => {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.map((moduleItem) => {
    const moduleName = String(moduleItem?.module_name ?? '').trim();
    const functions = Array.isArray(moduleItem?.functions)
      ? moduleItem.functions.map((functionItem) => ({
        name: String(functionItem?.name ?? '').trim(),
        desc: String(functionItem?.desc ?? '').trim(),
      }))
      : [];
    return {
      module_name: moduleName,
      functions,
    };
  });
};

const normalizeIntegrationPointsDraft = (value) => {
  if (typeof value === 'string') {
    const text = value.trim();
    return text ? [{ description: text, peer_system: '', protocol: '', direction: '' }] : [];
  }
  if (!Array.isArray(value)) {
    return [];
  }
  return value.map((item) => ({
    peer_system: String(item?.peer_system ?? '').trim(),
    protocol: String(item?.protocol ?? '').trim(),
    direction: String(item?.direction ?? '').trim(),
    description: String(item?.description ?? item?.name ?? '').trim(),
  }));
};

const normalizeKeyConstraintsDraft = (value) => {
  if (typeof value === 'string') {
    const text = value.trim();
    return text ? [{ category: '通用', description: text }] : [];
  }
  if (!Array.isArray(value)) {
    return [];
  }
  return value.map((item) => ({
    category: String(item?.category ?? '通用').trim() || '通用',
    description: String(item?.description ?? item?.value ?? '').trim(),
  }));
};

const normalizePerformanceRowsDraft = (value) => {
  if (Array.isArray(value)) {
    return value.map((item) => ({
      key: String(item?.key ?? item?.metric ?? '').trim(),
      value: String(item?.value ?? '').trim(),
    }));
  }
  if (value && typeof value === 'object') {
    return Object.entries(value).map(([metric, metricValue]) => ({
      key: String(metric || '').trim(),
      value: String(metricValue ?? '').trim(),
    }));
  }
  return [];
};

const performanceRowsToObject = (rows) => {
  const profile = {};
  if (!Array.isArray(rows)) {
    return profile;
  }
  rows.forEach((row) => {
    const key = String(row?.key ?? '').trim();
    if (!key) {
      return;
    }
    profile[key] = String(row?.value ?? '').trim();
  });
  return profile;
};

const renderHumanValuePreview = (value) => {
  if (value === undefined || value === null) {
    return <Text type="secondary">—</Text>;
  }

  if (Array.isArray(value)) {
    if (!value.length) {
      return <Text type="secondary">—</Text>;
    }
    return (
      <Space direction="vertical" size={4} style={{ width: '100%' }}>
        {value.map((item, index) => (
          <Card key={`preview-item-${index}`} size="small" bodyStyle={{ padding: 8 }}>
            {renderHumanValuePreview(item)}
          </Card>
        ))}
      </Space>
    );
  }

  if (typeof value === 'object') {
    const entries = Object.entries(value);
    if (!entries.length) {
      return <Text type="secondary">—</Text>;
    }
    return (
      <Space direction="vertical" size={4} style={{ width: '100%' }}>
        {entries.map(([key, itemValue]) => (
          <div key={`preview-kv-${key}`}>
            <Text strong>{key}</Text>
            <div style={{ marginTop: 2, paddingLeft: 8 }}>{renderHumanValuePreview(itemValue)}</div>
          </div>
        ))}
      </Space>
    );
  }

  const text = String(value).trim();
  return text ? <span>{text}</span> : <Text type="secondary">—</Text>;
};

const buildEmptyProfileData = () => {
  const result = {};
  PROFILE_DOMAIN_CONFIG.forEach((domain) => {
    result[domain.key] = {};
    domain.fields.forEach((field) => {
      result[domain.key][field.key] = deepClone(field.empty);
    });
  });
  return result;
};

const normalizeProfileData = (value) => {
  const normalized = buildEmptyProfileData();
  if (!value || typeof value !== 'object') {
    return normalized;
  }

  PROFILE_DOMAIN_CONFIG.forEach((domain) => {
    const incomingDomain = value[domain.key];
    if (!incomingDomain || typeof incomingDomain !== 'object') {
      return;
    }
    domain.fields.forEach((field) => {
      if (Object.prototype.hasOwnProperty.call(incomingDomain, field.key)) {
        normalized[domain.key][field.key] = deepClone(incomingDomain[field.key]);
      }
    });
  });
  return normalized;
};

const parseErrorMessage = (error, fallback) => {
  const responseData = error?.response?.data;
  return responseData?.message || responseData?.detail || fallback;
};

const isSameValue = (left, right) => {
  return JSON.stringify(left ?? null) === JSON.stringify(right ?? null);
};

const normalizeComparableValue = (domainKey, fieldKey, value) => {
  const fieldPath = getFieldPath(domainKey, fieldKey);
  const editorKind = FIELD_EDITOR_KIND[fieldPath];

  if (editorKind === 'module_structure') {
    // Ignore persistence metadata such as `last_updated` when diffing suggestions.
    return normalizeModuleStructureDraft(value);
  }
  if (editorKind === 'integration_points') {
    return normalizeIntegrationPointsDraft(value);
  }
  if (editorKind === 'key_constraints') {
    return normalizeKeyConstraintsDraft(value);
  }
  if (editorKind === 'performance_profile') {
    return normalizePerformanceRowsDraft(value)
      .map((row) => ({
        key: String(row?.key ?? '').trim(),
        value: String(row?.value ?? '').trim(),
      }))
      .sort((left, right) => `${left.key}:${left.value}`.localeCompare(`${right.key}:${right.value}`));
  }
  return value;
};

const buildIgnoredFieldsMap = (value) => {
  const ignoredMap = new Map();
  if (!value || typeof value !== 'object') {
    return ignoredMap;
  }
  Object.entries(value).forEach(([rawFieldPath, rawIgnoredValue]) => {
    const fieldPath = String(rawFieldPath || '').trim();
    const separatorIndex = fieldPath.indexOf('.');
    if (separatorIndex <= 0 || separatorIndex >= fieldPath.length - 1) {
      return;
    }
    const domainKey = fieldPath.slice(0, separatorIndex).trim();
    const fieldKey = fieldPath.slice(separatorIndex + 1).trim();
    if (!domainKey || !fieldKey) {
      return;
    }
    ignoredMap.set(fieldPath, normalizeComparableValue(domainKey, fieldKey, rawIgnoredValue));
  });
  return ignoredMap;
};

const buildDraftValues = (profileData) => {
  const draft = {};
  PROFILE_DOMAIN_CONFIG.forEach((domain) => {
    domain.fields.forEach((field) => {
      const path = getFieldPath(domain.key, field.key);
      const currentValue = profileData?.[domain.key]?.[field.key];
      const editorKind = FIELD_EDITOR_KIND[path] || field.type;

      if (editorKind === 'text') {
        draft[path] = String(currentValue ?? '');
      } else if (editorKind === 'list') {
        draft[path] = normalizeStringList(currentValue);
      } else if (editorKind === 'module_structure') {
        draft[path] = normalizeModuleStructureDraft(currentValue);
      } else if (editorKind === 'integration_points') {
        draft[path] = normalizeIntegrationPointsDraft(currentValue);
      } else if (editorKind === 'performance_profile') {
        draft[path] = normalizePerformanceRowsDraft(currentValue);
      } else if (editorKind === 'key_constraints') {
        draft[path] = normalizeKeyConstraintsDraft(currentValue);
      } else {
        draft[path] = deepClone(currentValue ?? field.empty);
      }
    });
  });
  return draft;
};

const sanitizeModuleStructureForPersist = (value) => (
  normalizeModuleStructureDraft(value)
    .map((moduleItem) => ({
      module_name: moduleItem.module_name,
      functions: (moduleItem.functions || []).filter((functionItem) => (
        Boolean(functionItem?.name) || Boolean(functionItem?.desc)
      )),
    }))
    .filter((moduleItem) => moduleItem.module_name || (moduleItem.functions || []).length > 0)
);

const sanitizeIntegrationPointsForPersist = (value) => (
  normalizeIntegrationPointsDraft(value)
    .filter((item) => (
      Boolean(item.peer_system) || Boolean(item.protocol) || Boolean(item.direction) || Boolean(item.description)
    ))
);

const sanitizeKeyConstraintsForPersist = (value) => (
  normalizeKeyConstraintsDraft(value)
    .filter((item) => Boolean(item.category) || Boolean(item.description))
);

const parseDraftToProfileData = (draftValues) => {
  const nextProfileData = buildEmptyProfileData();
  PROFILE_DOMAIN_CONFIG.forEach((domain) => {
    domain.fields.forEach((field) => {
      const path = getFieldPath(domain.key, field.key);
      const editorKind = FIELD_EDITOR_KIND[path] || field.type;
      const rawValue = draftValues[path];

      if (editorKind === 'text') {
        nextProfileData[domain.key][field.key] = String(rawValue ?? '').trim();
      } else if (editorKind === 'list') {
        nextProfileData[domain.key][field.key] = normalizeStringList(rawValue);
      } else if (editorKind === 'module_structure') {
        nextProfileData[domain.key][field.key] = sanitizeModuleStructureForPersist(rawValue);
      } else if (editorKind === 'integration_points') {
        nextProfileData[domain.key][field.key] = sanitizeIntegrationPointsForPersist(rawValue);
      } else if (editorKind === 'performance_profile') {
        nextProfileData[domain.key][field.key] = performanceRowsToObject(rawValue);
      } else if (editorKind === 'key_constraints') {
        nextProfileData[domain.key][field.key] = sanitizeKeyConstraintsForPersist(rawValue);
      } else {
        nextProfileData[domain.key][field.key] = deepClone(rawValue ?? field.empty);
      }
    });
  });
  return nextProfileData;
};

const SystemProfileBoardPage = () => {
  const { user } = useAuth();
  const { isManager } = usePermission();
  const location = useLocation();
  const navigate = useNavigate();

  const [systems, setSystems] = useState([]);
  const [selectedSystemName, setSelectedSystemName] = useState('');

  const [loadingProfile, setLoadingProfile] = useState(false);
  const [savingProfile, setSavingProfile] = useState(false);
  const [publishingProfile, setPublishingProfile] = useState(false);
  const [suggestionMutating, setSuggestionMutating] = useState(false);

  const [profileMeta, setProfileMeta] = useState({
    status: 'draft',
    pending_fields: [],
    updated_at: '',
    is_stale: false,
    system_id: '',
  });

  const [savedProfileData, setSavedProfileData] = useState(buildEmptyProfileData());
  const [draftValues, setDraftValues] = useState({});
  const [aiSuggestions, setAiSuggestions] = useState({});
  const [aiSuggestionsPrevious, setAiSuggestionsPrevious] = useState(null);
  const [ignoredFields, setIgnoredFields] = useState(() => new Map());
  const [activeDomain, setActiveDomain] = useState(PROFILE_DOMAIN_CONFIG[0].key);

  const [timelineExpanded, setTimelineExpanded] = useState(true);
  const [timelineItems, setTimelineItems] = useState([]);
  const [timelineTotal, setTimelineTotal] = useState(0);
  const [timelineLoading, setTimelineLoading] = useState(false);
  const [timelineLoadingMore, setTimelineLoadingMore] = useState(false);

  const [completenessInfo, setCompletenessInfo] = useState(null);
  const [completenessUnknown, setCompletenessUnknown] = useState(false);

  const queryParams = useMemo(() => new URLSearchParams(location.search), [location.search]);

  const responsibleSystems = useMemo(() => filterResponsibleSystems(systems, user), [systems, user]);

  const selectedSystem = useMemo(
    () => responsibleSystems.find((item) => item.name === selectedSystemName),
    [responsibleSystems, selectedSystemName]
  );

  const effectiveSystemId = useMemo(() => {
    const currentSystemId = String(selectedSystem?.id || '').trim();
    if (currentSystemId) {
      return currentSystemId;
    }
    return String(profileMeta.system_id || '').trim();
  }, [profileMeta.system_id, selectedSystem?.id]);

  const canWrite = useMemo(() => {
    if (!isManager || !selectedSystem) {
      return false;
    }
    return resolveSystemOwnership(selectedSystem, user).canWrite;
  }, [isManager, selectedSystem, user]);

  const profileStatusTag = useMemo(() => (
    <Tag color={profileMeta.status === 'published' ? 'green' : 'gold'}>
      {profileMeta.status === 'published' ? '已发布' : '草稿'}
    </Tag>
  ), [profileMeta.status]);

  const activeDomainConfig = PROFILE_DOMAIN_BY_KEY[activeDomain] || PROFILE_DOMAIN_CONFIG[0];

  const totalScore = completenessInfo?.completeness_score ?? 0;
  const breakdown = completenessInfo?.breakdown || {};

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

  const loadTimelinePage = useCallback(async (systemId, offset) => {
    if (!systemId) {
      return { total: 0, items: [] };
    }

    try {
      const response = await axios.get(`/api/v1/system-profiles/${encodeURIComponent(systemId)}/profile/events`, {
        params: { limit: 20, offset: Math.max(0, Number(offset) || 0) },
      });
      const payload = response.data || {};
      return {
        total: Number(payload.total) || 0,
        items: Array.isArray(payload.items) ? payload.items : [],
      };
    } catch (error) {
      message.error(parseErrorMessage(error, '加载时间线失败'));
      return { total: 0, items: [] };
    }
  }, []);

  const applyProfilePayload = useCallback((payload, fallbackSystemId = '', options = {}) => {
    const normalizedProfileData = normalizeProfileData(payload?.profile_data);
    setSavedProfileData(normalizedProfileData);
    setDraftValues(buildDraftValues(normalizedProfileData));
    setAiSuggestions(payload?.ai_suggestions && typeof payload.ai_suggestions === 'object' ? payload.ai_suggestions : {});
    setAiSuggestionsPrevious(payload?.ai_suggestions_previous && typeof payload.ai_suggestions_previous === 'object'
      ? payload.ai_suggestions_previous
      : null);
    const payloadIgnoredFields = buildIgnoredFieldsMap(payload?.ai_suggestion_ignored);
    if (options?.preserveIgnored) {
      setIgnoredFields((prev) => {
        const next = new Map(payloadIgnoredFields);
        prev.forEach((ignoredValue, fieldPath) => {
          if (!next.has(fieldPath)) {
            next.set(fieldPath, ignoredValue);
          }
        });
        return next;
      });
    } else {
      setIgnoredFields(payloadIgnoredFields);
    }
    setProfileMeta({
      status: payload?.status || 'draft',
      pending_fields: Array.isArray(payload?.pending_fields) ? payload.pending_fields : [],
      updated_at: payload?.updated_at || payload?.created_at || '',
      is_stale: Boolean(payload?.is_stale),
      system_id: String(payload?.system_id || fallbackSystemId || ''),
    });
    setActiveDomain((prev) => (PROFILE_DOMAIN_BY_KEY[prev] ? prev : PROFILE_DOMAIN_CONFIG[0].key));
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

  const loadSystems = useCallback(async () => {
    try {
      const response = await axios.get('/api/v1/system/systems');
      const items = response.data?.data?.systems || [];
      setSystems(items);
    } catch (error) {
      message.error(parseErrorMessage(error, '加载系统清单失败'));
    }
  }, []);

  const loadProfileDetail = useCallback(async (systemName, options = {}) => {
    if (!systemName) {
      return;
    }

    setLoadingProfile(true);
    try {
      const response = await axios.get(`/api/v1/system-profiles/${encodeURIComponent(systemName)}`);
      const payload = response.data?.data;
      const resolvedSystemId = String(selectedSystem?.id || payload?.system_id || '').trim();

      if (payload) {
        applyProfilePayload(payload, resolvedSystemId, options);
      } else {
        applyProfilePayload(
          {
            profile_data: buildEmptyProfileData(),
            ai_suggestions: {},
            ai_suggestions_previous: null,
            pending_fields: [],
            status: 'draft',
            updated_at: '',
            is_stale: false,
            system_id: resolvedSystemId,
          },
          resolvedSystemId,
          options,
        );
      }

      setTimelineLoading(true);
      const timeline = await loadTimelinePage(resolvedSystemId, 0);
      setTimelineItems(timeline.items);
      setTimelineTotal(timeline.total);
      setTimelineLoading(false);

      await loadCompleteness(systemName);
    } catch (error) {
      message.error(parseErrorMessage(error, '加载系统画像详情失败'));
      setTimelineItems([]);
      setTimelineTotal(0);
      setTimelineLoading(false);
    } finally {
      setLoadingProfile(false);
    }
  }, [applyProfilePayload, loadCompleteness, loadTimelinePage, selectedSystem?.id]);

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

  const handleDraftValueChange = (path, value) => {
    setDraftValues((prev) => ({ ...prev, [path]: value }));
  };

  const renderListEditor = (fieldPath, value, itemLabel = '条目') => {
    const items = normalizeStringList(value);
    const visibleItems = items.length > 0 ? items : [''];
    return (
      <Space direction="vertical" size={8} style={{ width: '100%', marginTop: 6 }}>
        {visibleItems.map((item, index) => (
          <Space key={`${fieldPath}-list-${index}`} style={{ width: '100%' }}>
            <Input
              value={item}
              placeholder={`请输入${itemLabel}`}
              disabled={!canWrite}
              onChange={(event) => {
                const next = [...visibleItems];
                next[index] = event.target.value;
                handleDraftValueChange(fieldPath, next);
              }}
            />
          </Space>
        ))}
      </Space>
    );
  };

  const renderModuleStructureEditor = (fieldPath, value) => {
    const modules = normalizeModuleStructureDraft(value);
    const visibleModules = modules.length > 0 ? modules : [{ module_name: '', functions: [] }];
    return (
      <Space direction="vertical" size={8} style={{ width: '100%', marginTop: 6 }}>
        {visibleModules.map((moduleItem, moduleIndex) => (
          <Card key={`${fieldPath}-module-${moduleIndex}`} size="small" bodyStyle={{ padding: 10 }}>
            <Space direction="vertical" size={8} style={{ width: '100%' }}>
              <Space style={{ width: '100%' }}>
                <Input
                  value={moduleItem.module_name}
                  placeholder="模块名称"
                  disabled={!canWrite}
                  onChange={(event) => {
                    const next = deepClone(visibleModules);
                    next[moduleIndex].module_name = event.target.value;
                    handleDraftValueChange(fieldPath, next);
                  }}
                />
              </Space>

              {((moduleItem.functions || []).length > 0 ? moduleItem.functions : [{ name: '', desc: '' }]).map((functionItem, functionIndex) => (
                <Space key={`${fieldPath}-module-${moduleIndex}-fn-${functionIndex}`} style={{ width: '100%' }} align="start">
                  <Input
                    value={functionItem.name}
                    placeholder="功能名称"
                    disabled={!canWrite}
                    onChange={(event) => {
                      const next = deepClone(visibleModules);
                      next[moduleIndex].functions[functionIndex].name = event.target.value;
                      handleDraftValueChange(fieldPath, next);
                    }}
                  />
                  <Input
                    value={functionItem.desc}
                    placeholder="功能说明"
                    disabled={!canWrite}
                    onChange={(event) => {
                      const next = deepClone(visibleModules);
                      next[moduleIndex].functions[functionIndex].desc = event.target.value;
                      handleDraftValueChange(fieldPath, next);
                    }}
                  />
                </Space>
              ))}
            </Space>
          </Card>
        ))}
      </Space>
    );
  };

  const renderIntegrationPointsEditor = (fieldPath, value) => {
    const points = normalizeIntegrationPointsDraft(value);
    const visiblePoints = points.length > 0 ? points : [{ peer_system: '', protocol: '', direction: '', description: '' }];
    return (
      <Space direction="vertical" size={8} style={{ width: '100%', marginTop: 6 }}>
        {visiblePoints.map((point, index) => (
          <Card key={`${fieldPath}-point-${index}`} size="small" bodyStyle={{ padding: 10 }}>
            <Space direction="vertical" size={6} style={{ width: '100%' }}>
              <Space style={{ width: '100%' }} align="start">
                <Input
                  value={point.peer_system}
                  placeholder="对端系统（可选）"
                  disabled={!canWrite}
                  onChange={(event) => {
                    const next = deepClone(visiblePoints);
                    next[index].peer_system = event.target.value;
                    handleDraftValueChange(fieldPath, next);
                  }}
                />
                <Input
                  value={point.protocol}
                  placeholder="协议（可选）"
                  disabled={!canWrite}
                  onChange={(event) => {
                    const next = deepClone(visiblePoints);
                    next[index].protocol = event.target.value;
                    handleDraftValueChange(fieldPath, next);
                  }}
                />
                <Input
                  value={point.direction}
                  placeholder="方向（in/out/bidirectional）"
                  disabled={!canWrite}
                  onChange={(event) => {
                    const next = deepClone(visiblePoints);
                    next[index].direction = event.target.value;
                    handleDraftValueChange(fieldPath, next);
                  }}
                />
              </Space>
              <Space style={{ width: '100%' }}>
                <Input
                  value={point.description}
                  placeholder="集成说明"
                  disabled={!canWrite}
                  onChange={(event) => {
                    const next = deepClone(visiblePoints);
                    next[index].description = event.target.value;
                    handleDraftValueChange(fieldPath, next);
                  }}
                />
              </Space>
            </Space>
          </Card>
        ))}
      </Space>
    );
  };

  const renderKeyConstraintsEditor = (fieldPath, value) => {
    const constraints = normalizeKeyConstraintsDraft(value);
    const visibleConstraints = constraints.length > 0 ? constraints : [{ category: '', description: '' }];
    return (
      <Space direction="vertical" size={8} style={{ width: '100%', marginTop: 6 }}>
        {visibleConstraints.map((constraint, index) => (
          <Space key={`${fieldPath}-constraint-${index}`} style={{ width: '100%' }}>
            <Input
              value={constraint.category}
              placeholder="约束类别"
              disabled={!canWrite}
              onChange={(event) => {
                const next = deepClone(visibleConstraints);
                next[index].category = event.target.value;
                handleDraftValueChange(fieldPath, next);
              }}
            />
            <Input
              value={constraint.description}
              placeholder="约束说明"
              disabled={!canWrite}
              onChange={(event) => {
                const next = deepClone(visibleConstraints);
                next[index].description = event.target.value;
                handleDraftValueChange(fieldPath, next);
              }}
            />
          </Space>
        ))}
      </Space>
    );
  };

  const renderPerformanceProfileEditor = (fieldPath, value) => {
    const metrics = normalizePerformanceRowsDraft(value);
    const visibleMetrics = metrics.length > 0 ? metrics : [{ key: '', value: '' }];
    return (
      <Space direction="vertical" size={8} style={{ width: '100%', marginTop: 6 }}>
        {visibleMetrics.map((metric, index) => (
          <Space key={`${fieldPath}-metric-${index}`} style={{ width: '100%' }}>
            <Input
              value={metric.key}
              placeholder="指标名称"
              disabled={!canWrite}
              onChange={(event) => {
                const next = deepClone(visibleMetrics);
                next[index].key = event.target.value;
                handleDraftValueChange(fieldPath, next);
              }}
            />
            <Input
              value={metric.value}
              placeholder="指标值"
              disabled={!canWrite}
              onChange={(event) => {
                const next = deepClone(visibleMetrics);
                next[index].value = event.target.value;
                handleDraftValueChange(fieldPath, next);
              }}
            />
          </Space>
        ))}
      </Space>
    );
  };

  const renderFieldEditor = (field, fieldPath) => {
    const value = draftValues[fieldPath];
    const editorKind = FIELD_EDITOR_KIND[fieldPath] || field.type;

    if (editorKind === 'text') {
      return (
        <Input.TextArea
          style={{ marginTop: 6 }}
          rows={4}
          disabled={!canWrite}
          value={String(value ?? '')}
          placeholder={`请输入${field.label}`}
          onChange={(event) => handleDraftValueChange(fieldPath, event.target.value)}
        />
      );
    }

    if (editorKind === 'list') {
      return renderListEditor(fieldPath, value, field.label);
    }

    if (editorKind === 'module_structure') {
      return renderModuleStructureEditor(fieldPath, value);
    }
    if (editorKind === 'integration_points') {
      return renderIntegrationPointsEditor(fieldPath, value);
    }
    if (editorKind === 'key_constraints') {
      return renderKeyConstraintsEditor(fieldPath, value);
    }
    if (editorKind === 'performance_profile') {
      return renderPerformanceProfileEditor(fieldPath, value);
    }

    return (
      <Input.TextArea
        style={{ marginTop: 6 }}
        rows={4}
        disabled={!canWrite}
        value={String(value ?? '')}
        placeholder={`请输入${field.label}`}
        onChange={(event) => handleDraftValueChange(fieldPath, event.target.value)}
      />
    );
  };

  const handleSaveDraft = async () => {
    if (!selectedSystemName) {
      message.warning('请先选择系统');
      return;
    }
    if (!canWrite) {
      message.warning('当前系统为只读，无法保存');
      return;
    }
    if (suggestionMutating) {
      message.warning('建议操作进行中，请稍后再保存');
      return;
    }

    let profileData;
    try {
      profileData = parseDraftToProfileData(draftValues);
    } catch (error) {
      message.error(error.message || '字段格式错误');
      return;
    }

    try {
      setSavingProfile(true);
      await axios.put(`/api/v1/system-profiles/${encodeURIComponent(selectedSystemName)}`, {
        system_id: effectiveSystemId,
        profile_data: profileData,
        evidence_refs: [],
      });
      message.success('系统画像草稿已保存');
      await loadProfileDetail(selectedSystemName, { preserveIgnored: true });
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
    if (!canWrite) {
      message.warning('当前系统为只读，无法发布');
      return;
    }
    if (suggestionMutating) {
      message.warning('建议操作进行中，请稍后再发布');
      return;
    }

    let profileData;
    try {
      profileData = parseDraftToProfileData(draftValues);
    } catch (error) {
      message.error(error.message || '字段格式错误');
      return;
    }

    setPublishingProfile(true);
    try {
      await axios.put(`/api/v1/system-profiles/${encodeURIComponent(selectedSystemName)}`, {
        system_id: effectiveSystemId,
        profile_data: profileData,
        evidence_refs: [],
      });
      await axios.post(`/api/v1/system-profiles/${encodeURIComponent(selectedSystemName)}/publish`);
      message.success('系统画像已发布');
      await loadProfileDetail(selectedSystemName);
    } catch (error) {
      message.error(parseErrorMessage(error, '发布系统画像失败'));
    } finally {
      setPublishingProfile(false);
    }
  };

  const handleAcceptSuggestion = async (domainKey, fieldKey) => {
    const systemId = effectiveSystemId;
    if (!systemId) {
      message.error('系统ID缺失，无法执行操作');
      return;
    }
    if (suggestionMutating) {
      return;
    }

    try {
      setSuggestionMutating(true);
      const response = await axios.post(
        `/api/v1/system-profiles/${encodeURIComponent(systemId)}/profile/suggestions/accept`,
        { domain: domainKey, sub_field: fieldKey }
      );
      const payload = response.data?.data;
      if (payload) {
        applyProfilePayload(payload, systemId);
      }
      message.success('已采纳AI建议');
    } catch (error) {
      message.error(parseErrorMessage(error, '采纳AI建议失败'));
    } finally {
      setSuggestionMutating(false);
    }
  };

  const handleRollbackSuggestion = async (domainKey, fieldKey) => {
    const systemId = effectiveSystemId;
    if (!systemId) {
      message.error('系统ID缺失，无法执行操作');
      return;
    }
    if (suggestionMutating) {
      return;
    }

    try {
      setSuggestionMutating(true);
      const response = await axios.post(
        `/api/v1/system-profiles/${encodeURIComponent(systemId)}/profile/suggestions/rollback`,
        { domain: domainKey, sub_field: fieldKey }
      );
      const payload = response.data?.data;
      if (payload) {
        applyProfilePayload(payload, systemId);
      }
      message.success('已恢复上一版建议');
    } catch (error) {
      const code = error?.response?.data?.error_code;
      if (code === 'ROLLBACK_NO_PREVIOUS') {
        message.warning('无历史版本');
        return;
      }
      message.error(parseErrorMessage(error, '恢复上一版建议失败'));
    } finally {
      setSuggestionMutating(false);
    }
  };

  const handleIgnoreSuggestion = async (domainKey, fieldKey) => {
    const systemId = effectiveSystemId;
    if (!systemId) {
      message.error('系统ID缺失，无法执行操作');
      return;
    }
    if (suggestionMutating) {
      return;
    }

    const suggestionDomain = aiSuggestions?.[domainKey];
    if (!suggestionDomain || typeof suggestionDomain !== 'object') {
      return;
    }
    if (!Object.prototype.hasOwnProperty.call(suggestionDomain, fieldKey)) {
      return;
    }
    const fieldPath = getFieldPath(domainKey, fieldKey);
    const ignoredComparableValue = normalizeComparableValue(domainKey, fieldKey, suggestionDomain[fieldKey]);
    setIgnoredFields((prev) => {
      const next = new Map(prev);
      next.set(fieldPath, ignoredComparableValue);
      return next;
    });

    try {
      setSuggestionMutating(true);
      const response = await axios.post(
        `/api/v1/system-profiles/${encodeURIComponent(systemId)}/profile/suggestions/ignore`,
        { domain: domainKey, sub_field: fieldKey }
      );
      const payload = response.data?.data;
      if (payload) {
        applyProfilePayload(payload, systemId, { preserveIgnored: true });
      }
      message.success('已忽略AI建议');
    } catch (error) {
      message.error(parseErrorMessage(error, '忽略AI建议失败'));
      await loadProfileDetail(selectedSystemName);
    } finally {
      setSuggestionMutating(false);
    }
  };

  const hasPreviousSuggestion = useCallback((domainKey, fieldKey) => {
    if (!aiSuggestionsPrevious || typeof aiSuggestionsPrevious !== 'object') {
      return false;
    }
    const domainPayload = aiSuggestionsPrevious[domainKey];
    return Boolean(domainPayload && typeof domainPayload === 'object' && Object.prototype.hasOwnProperty.call(domainPayload, fieldKey));
  }, [aiSuggestionsPrevious]);

  const hasVisibleDiff = useCallback((domainKey, fieldKey) => {
    const fieldPath = getFieldPath(domainKey, fieldKey);
    const suggestionDomain = aiSuggestions?.[domainKey];
    if (!suggestionDomain || typeof suggestionDomain !== 'object') {
      return false;
    }
    if (!Object.prototype.hasOwnProperty.call(suggestionDomain, fieldKey)) {
      return false;
    }
    const currentValue = savedProfileData?.[domainKey]?.[fieldKey];
    const suggestionValue = suggestionDomain[fieldKey];
    const normalizedSuggestionValue = normalizeComparableValue(domainKey, fieldKey, suggestionValue);
    const ignoredComparableValue = ignoredFields.get(fieldPath);
    if (ignoredComparableValue !== undefined && isSameValue(ignoredComparableValue, normalizedSuggestionValue)) {
      return false;
    }
    return !isSameValue(
      normalizeComparableValue(domainKey, fieldKey, currentValue),
      normalizedSuggestionValue,
    );
  }, [aiSuggestions, ignoredFields, savedProfileData]);

  const domainHasDiff = useCallback((domainKey) => {
    const domain = PROFILE_DOMAIN_BY_KEY[domainKey];
    if (!domain) {
      return false;
    }
    return domain.fields.some((field) => hasVisibleDiff(domainKey, field.key));
  }, [hasVisibleDiff]);

  const handleLoadMoreTimeline = async () => {
    const systemId = effectiveSystemId;
    if (!systemId) {
      return;
    }
    setTimelineLoadingMore(true);
    const timeline = await loadTimelinePage(systemId, timelineItems.length);
    setTimelineItems((prev) => [...prev, ...timeline.items]);
    setTimelineTotal(timeline.total);
    setTimelineLoadingMore(false);
  };

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
              <Button
                size="small"
                type="text"
                icon={timelineExpanded ? <RightOutlined /> : <LeftOutlined />}
                onClick={() => setTimelineExpanded((prev) => !prev)}
              >
                {timelineExpanded ? '收起时间线' : '展开时间线'}
              </Button>
              <Button size="small" icon={<ReloadOutlined />} onClick={() => loadProfileDetail(selectedSystemName)}>
                重新加载
              </Button>
              <Text type="secondary" style={{ fontSize: 12, marginLeft: 'auto' }}>
                更新：{formatDateTime(profileMeta.updated_at)}
              </Text>
            </div>

          </Space>

          <div
            style={{
              display: 'grid',
              gap: 12,
              gridTemplateColumns: timelineExpanded ? '220px minmax(0, 1fr) 320px' : '220px minmax(0, 1fr)',
              alignItems: 'start',
            }}
          >
            <Card size="small">
              <Space direction="vertical" size={8} style={{ width: '100%' }}>
                {PROFILE_DOMAIN_CONFIG.map((domain) => (
                  <Button
                    key={domain.key}
                    type={activeDomain === domain.key ? 'primary' : 'default'}
                    onClick={() => setActiveDomain(domain.key)}
                    style={{ justifyContent: 'flex-start', textAlign: 'left' }}
                    block
                  >
                    <Space size={6}>
                      <span>{domain.label}</span>
                      {domainHasDiff(domain.key) && <Tag color="blue">有建议</Tag>}
                    </Space>
                  </Button>
                ))}
              </Space>
            </Card>

            <Card loading={loadingProfile}>
              <Space direction="vertical" size={12} style={{ width: '100%' }}>
                {activeDomainConfig.fields.map((field) => {
                  const fieldPath = getFieldPath(activeDomainConfig.key, field.key);
                  const suggestionDomain = aiSuggestions?.[activeDomainConfig.key];
                  const hasSuggestion = Boolean(
                    suggestionDomain && typeof suggestionDomain === 'object'
                    && Object.prototype.hasOwnProperty.call(suggestionDomain, field.key)
                  );
                  const currentValue = savedProfileData?.[activeDomainConfig.key]?.[field.key];
                  const suggestionValue = hasSuggestion ? suggestionDomain[field.key] : undefined;
                  const shouldShowDiff = hasVisibleDiff(activeDomainConfig.key, field.key);
                  const rollbackEnabled = hasPreviousSuggestion(activeDomainConfig.key, field.key);

                  return (
                    <div key={fieldPath}>
                      <Text strong>{field.label}</Text>
                      {renderFieldEditor(field, fieldPath)}

                      {shouldShowDiff && (
                        <Card size="small" style={{ marginTop: 8, background: '#fafcff' }}>
                          <Space direction="vertical" size={8} style={{ width: '100%' }}>
                            <Text strong>检测到 AI 建议变更</Text>
                            <div
                              style={{
                                display: 'grid',
                                gap: 8,
                                gridTemplateColumns: '1fr 1fr',
                              }}
                            >
                              <div>
                                <Text type="secondary">当前值</Text>
                                <div style={{ marginTop: 4, padding: 8, borderRadius: 4, background: '#fff' }}>
                                  {renderHumanValuePreview(currentValue)}
                                </div>
                              </div>
                              <div>
                                <Text type="secondary">AI 建议</Text>
                                <div style={{ marginTop: 4, padding: 8, borderRadius: 4, background: '#fff' }}>
                                  {renderHumanValuePreview(suggestionValue)}
                                </div>
                              </div>
                            </div>
                            <Space wrap>
                              <Button
                                size="small"
                                type="primary"
                                loading={suggestionMutating}
                                disabled={!canWrite || suggestionMutating}
                                onClick={() => handleAcceptSuggestion(activeDomainConfig.key, field.key)}
                              >
                                采纳新建议
                              </Button>
                              <Button
                                size="small"
                                disabled={!canWrite || suggestionMutating}
                                onClick={() => handleIgnoreSuggestion(activeDomainConfig.key, field.key)}
                              >
                                忽略
                              </Button>
                              <Button
                                size="small"
                                loading={suggestionMutating}
                                disabled={!canWrite || suggestionMutating || !rollbackEnabled}
                                title={rollbackEnabled ? '' : '无历史版本'}
                                onClick={() => handleRollbackSuggestion(activeDomainConfig.key, field.key)}
                              >
                                恢复上一版建议
                              </Button>
                            </Space>
                          </Space>
                        </Card>
                      )}
                    </div>
                  );
                })}

                <Space>
                  <Button
                    type="primary"
                    icon={<SaveOutlined />}
                    loading={savingProfile}
                    disabled={!canWrite || suggestionMutating}
                    onClick={handleSaveDraft}
                  >
                    保存草稿
                  </Button>
                  <Button
                    icon={<SendOutlined />}
                    loading={publishingProfile}
                    disabled={!canWrite || suggestionMutating}
                    onClick={handlePublish}
                  >
                    发布画像
                  </Button>
                </Space>

                <Space wrap>
                  <Text type="secondary">待补证据字段：</Text>
                  {(profileMeta.pending_fields || []).length > 0
                    ? profileMeta.pending_fields.map((item) => <Tag key={item}>{item}</Tag>)
                    : <Text type="secondary">无</Text>}
                </Space>
              </Space>
            </Card>

            {timelineExpanded && (
              <Card size="small" title="变更时间线">
                <Space direction="vertical" size={8} style={{ width: '100%' }}>
                  {timelineLoading && timelineItems.length === 0 ? (
                    <Text type="secondary">加载中...</Text>
                  ) : timelineItems.length === 0 ? (
                    <Text type="secondary">暂无变更记录</Text>
                  ) : (
                    <List
                      size="small"
                      dataSource={timelineItems}
                      renderItem={(item) => {
                        const type = EVENT_TYPE_LABELS[String(item?.event_type || '').trim()] || String(item?.event_type || '变更');
                        return (
                          <List.Item>
                            <Space direction="vertical" size={2} style={{ width: '100%' }}>
                              <Space size={6} wrap>
                                <Tag color="blue">{type}</Tag>
                                <Text type="secondary" style={{ fontSize: 12 }}>{formatDateTime(item?.timestamp)}</Text>
                              </Space>
                              <Text>{String(item?.summary || '-')}</Text>
                              <Text type="secondary" style={{ fontSize: 12 }}>
                                来源：{String(item?.source || '-')}
                              </Text>
                            </Space>
                          </List.Item>
                        );
                      }}
                    />
                  )}

                  {timelineItems.length < timelineTotal && (
                    <Button loading={timelineLoadingMore} onClick={handleLoadMoreTimeline}>
                      加载更多
                    </Button>
                  )}
                </Space>
              </Card>
            )}
          </div>
        </Space>
      )}
    </div>
  );
};

export default SystemProfileBoardPage;
