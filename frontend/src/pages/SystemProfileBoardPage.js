import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Button,
  Card,
  Input,
  List,
  Space,
  Tabs,
  Tag,
  Typography,
  message,
} from 'antd';
import {
  LeftOutlined,
  ReloadOutlined,
  RightOutlined,
  SaveOutlined,
  SendOutlined,
} from '@ant-design/icons';
import axios from 'axios';
import { useLocation, useNavigate } from 'react-router-dom';
import useAuth from '../hooks/useAuth';
import usePermission from '../hooks/usePermission';
import { formatDateTime } from '../utils/time';
import { filterResponsibleSystems, resolveSystemOwnership } from '../utils/systemOwnership';

const { Text } = Typography;

const DOMAIN_CONFIG = [
  {
    key: 'system_positioning',
    label: 'D1 系统定位与边界',
    fields: [
      { key: 'system_type', label: '系统类型', type: 'text' },
      { key: 'business_domain', label: '业务域', type: 'list' },
      { key: 'architecture_layer', label: '架构层级', type: 'text' },
      { key: 'target_users', label: '目标用户', type: 'list' },
      { key: 'service_scope', label: '服务范围', type: 'text' },
      { key: 'system_boundary', label: '系统边界', type: 'list' },
    ],
  },
  {
    key: 'business_capabilities',
    label: 'D2 业务能力与流程',
    fields: [
      { key: 'functional_modules', label: '功能模块', type: 'list' },
      { key: 'business_processes', label: '业务流程', type: 'list' },
      { key: 'data_assets', label: '数据资产', type: 'list' },
    ],
  },
  {
    key: 'integration_interfaces',
    label: 'D3 集成与接口',
    fields: [
      { key: 'provided_services', label: '作为服务方', type: 'service_list' },
      { key: 'consumed_services', label: '作为消费方', type: 'service_list' },
      { key: 'other_integrations', label: '其他集成', type: 'integration_list' },
    ],
  },
  {
    key: 'technical_architecture',
    label: 'D4 技术架构',
    fields: [
      { key: 'architecture_style', label: '架构风格', type: 'text' },
      { key: 'tech_stack', label: '技术栈', type: 'tech_stack' },
      { key: 'network_zone', label: '网络分区', type: 'text' },
      { key: 'performance_baseline', label: '性能基线', type: 'performance' },
    ],
  },
  {
    key: 'constraints_risks',
    label: 'D5 约束与风险',
    fields: [
      { key: 'technical_constraints', label: '技术约束', type: 'list' },
      { key: 'business_constraints', label: '业务约束', type: 'list' },
      { key: 'known_risks', label: '已知风险', type: 'list' },
    ],
  },
];

const DOMAIN_BY_KEY = Object.fromEntries(DOMAIN_CONFIG.map((item) => [item.key, item]));

const EVENT_TYPE_LABELS = {
  document_import: '文档导入',
  code_scan: '代码扫描',
  manual_edit: '手动编辑',
  ai_suggestion_accept: '采纳建议',
  ai_suggestion_rollback: '建议回滚',
  profile_publish: '画像发布',
};

const TECH_STACK_GROUPS = [
  { key: 'languages', label: '语言' },
  { key: 'frameworks', label: '框架' },
  { key: 'databases', label: '数据库' },
  { key: 'middleware', label: '中间件' },
  { key: 'others', label: '其他' },
];

const PERFORMANCE_SECTIONS = [
  {
    key: 'online',
    label: '在线指标',
    fields: [
      { key: 'peak_tps', label: '峰值 TPS' },
      { key: 'p95_latency_ms', label: 'P95 延迟(ms)' },
      { key: 'availability_target', label: '可用性目标' },
    ],
  },
  {
    key: 'batch',
    label: '批处理指标',
    fields: [
      { key: 'window', label: '处理窗口' },
      { key: 'data_volume', label: '数据量' },
      { key: 'peak_duration', label: '峰值耗时' },
    ],
  },
];

const LEGACY_SUGGESTION_FIELD_ALIASES = {
  system_positioning: {
    service_scope: ['system_description'],
    system_boundary: ['boundaries'],
  },
  business_capabilities: {
    business_processes: ['core_processes'],
  },
  integration_interfaces: {
    other_integrations: ['integration_points'],
  },
  technical_architecture: {
    architecture_style: ['architecture_positioning'],
  },
  constraints_risks: {
    technical_constraints: ['key_constraints'],
  },
};

const EMPTY_SERVICE_ROW = {
  service_name: '',
  transaction_name: '',
  scenario_code: '',
  peer_system: '',
  status: '',
};

const EMPTY_INTEGRATION_ROW = {
  integration_name: '',
  peer_system: '',
  notes: '',
};

const buildEmptyProfileData = () => ({
  system_positioning: {
    canonical: {
      system_type: '',
      business_domain: [],
      architecture_layer: '',
      target_users: [],
      service_scope: '',
      system_boundary: [],
      extensions: {},
    },
  },
  business_capabilities: {
    canonical: {
      functional_modules: [],
      business_processes: [],
      data_assets: [],
      extensions: {},
    },
  },
  integration_interfaces: {
    canonical: {
      provided_services: [],
      consumed_services: [],
      other_integrations: [],
      extensions: {},
    },
  },
  technical_architecture: {
    canonical: {
      architecture_style: '',
      tech_stack: {
        languages: [],
        frameworks: [],
        databases: [],
        middleware: [],
        others: [],
      },
      network_zone: '',
      performance_baseline: {
        online: {
          peak_tps: '',
          p95_latency_ms: '',
          availability_target: '',
        },
        batch: {
          window: '',
          data_volume: '',
          peak_duration: '',
        },
        processing_model: '',
      },
      extensions: {},
    },
  },
  constraints_risks: {
    canonical: {
      technical_constraints: [],
      business_constraints: [],
      known_risks: [],
      extensions: {},
    },
  },
});

const deepClone = (value) => {
  if (value === undefined) {
    return undefined;
  }
  return JSON.parse(JSON.stringify(value));
};

const normalizeString = (value) => String(value ?? '').trim();

const normalizeStringList = (value) => {
  if (Array.isArray(value)) {
    return value.map((item) => normalizeString(item)).filter(Boolean);
  }

  const text = normalizeString(value);
  if (!text) {
    return [];
  }

  return text
    .replace(/[，、；;]/g, ',')
    .split(/[\n,]+/)
    .map((item) => item.trim())
    .filter(Boolean);
};

const coerceServiceDraftRow = (value) => ({
  service_name: normalizeString(value?.service_name || value?.name || value?.service || value?.description),
  transaction_name: normalizeString(
    value?.transaction_name
      || value?.scenario_name
      || value?.trade_name
  ),
  scenario_code: normalizeString(value?.scenario_code || value?.service_code || value?.trade_code || value?.code),
  peer_system: normalizeString(
    value?.peer_system
      || value?.system_name
      || value?.target_system
      || value?.provider_system
      || value?.consumer_system
  ),
  status: normalizeString(value?.status || value?.state || value?.usage_status),
});

const normalizeServiceEntries = (value) => {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map((item) => {
      if (typeof item === 'string') {
        return {
          ...EMPTY_SERVICE_ROW,
          service_name: normalizeString(item),
        };
      }
      return coerceServiceDraftRow(item || {});
    })
    .filter((item) => item.service_name || item.transaction_name || item.scenario_code || item.peer_system || item.status);
};

const coerceIntegrationDraftRow = (value) => ({
  integration_name: normalizeString(
    value?.integration_name || value?.name || value?.service_name || value?.title || value?.description
  ),
  peer_system: normalizeString(value?.peer_system || value?.system_name || value?.target_system),
  notes: normalizeString(value?.notes || value?.remark || value?.protocol || value?.status || value?.description),
});

const normalizeIntegrationEntries = (value) => {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map((item) => {
      if (typeof item === 'string') {
        return {
          ...EMPTY_INTEGRATION_ROW,
          integration_name: normalizeString(item),
        };
      }
      return coerceIntegrationDraftRow(item || {});
    })
    .filter((item) => item.integration_name || item.peer_system || item.notes);
};

const normalizeTechStack = (value) => {
  const template = buildEmptyProfileData().technical_architecture.canonical.tech_stack;
  const source = value && typeof value === 'object' ? value : {};
  const next = deepClone(template);

  TECH_STACK_GROUPS.forEach((group) => {
    next[group.key] = normalizeStringList(source[group.key]);
  });

  return next;
};

const normalizePerformanceBaseline = (value) => {
  const template = buildEmptyProfileData().technical_architecture.canonical.performance_baseline;
  const source = value && typeof value === 'object' ? value : {};
  const next = deepClone(template);

  PERFORMANCE_SECTIONS.forEach((section) => {
    const sectionSource = source[section.key] && typeof source[section.key] === 'object' ? source[section.key] : {};
    section.fields.forEach((field) => {
      next[section.key][field.key] = normalizeString(sectionSource[field.key]);
    });
  });

  next.processing_model = normalizeString(source.processing_model);
  return next;
};

const normalizeExtensions = (value) => {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return {};
  }
  return deepClone(value);
};

const normalizeProfileData = (value) => {
  const template = buildEmptyProfileData();
  if (!value || typeof value !== 'object') {
    return template;
  }

  DOMAIN_CONFIG.forEach((domain) => {
    const rawDomain = value[domain.key];
    const rawCanonical = rawDomain?.canonical;
    const source = rawCanonical && typeof rawCanonical === 'object'
      ? rawCanonical
      : rawDomain && typeof rawDomain === 'object'
        ? rawDomain
        : {};

    domain.fields.forEach((field) => {
      if (!Object.prototype.hasOwnProperty.call(source, field.key)) {
        return;
      }

      if (field.type === 'text') {
        template[domain.key].canonical[field.key] = normalizeString(source[field.key]);
        return;
      }

      if (field.type === 'list') {
        template[domain.key].canonical[field.key] = normalizeStringList(source[field.key]);
        return;
      }

      if (field.type === 'service_list') {
        template[domain.key].canonical[field.key] = normalizeServiceEntries(source[field.key]);
        return;
      }

      if (field.type === 'integration_list') {
        template[domain.key].canonical[field.key] = normalizeIntegrationEntries(source[field.key]);
        return;
      }

      if (field.type === 'tech_stack') {
        template[domain.key].canonical[field.key] = normalizeTechStack(source[field.key]);
        return;
      }

      if (field.type === 'performance') {
        template[domain.key].canonical[field.key] = normalizePerformanceBaseline(source[field.key]);
      }
    });

    template[domain.key].canonical.extensions = normalizeExtensions(source.extensions);
  });

  return template;
};

const getFieldPath = (domainKey, fieldKey) => `${domainKey}.${fieldKey}`;

const parseErrorMessage = (error, fallback) => (
  error?.response?.data?.message
  || error?.response?.data?.detail
  || fallback
);

const hasMeaningfulValue = (value) => {
  if (value === null || value === undefined) {
    return false;
  }
  if (typeof value === 'string') {
    return normalizeString(value).length > 0;
  }
  if (typeof value === 'number' || typeof value === 'boolean') {
    return true;
  }
  if (Array.isArray(value)) {
    return value.some((item) => hasMeaningfulValue(item));
  }
  if (typeof value === 'object') {
    return Object.values(value).some((item) => hasMeaningfulValue(item));
  }
  return false;
};

const unwrapSuggestionValue = (value) => {
  if (
    value
    && typeof value === 'object'
    && !Array.isArray(value)
    && Object.prototype.hasOwnProperty.call(value, 'value')
  ) {
    return deepClone(value.value);
  }
  return deepClone(value);
};

const getSuggestionFieldCandidates = (domainKey, fieldKey) => {
  const aliasFields = LEGACY_SUGGESTION_FIELD_ALIASES[domainKey]?.[fieldKey] || [];
  return [fieldKey, ...aliasFields].filter((item, index, array) => item && array.indexOf(item) === index);
};

const readSuggestionValue = (payload, domainKey, fieldKey) => {
  if (!payload || typeof payload !== 'object') {
    return undefined;
  }

  const fieldCandidates = getSuggestionFieldCandidates(domainKey, fieldKey);
  const flatPathCandidates = fieldCandidates.flatMap((candidate) => [
    `${domainKey}.canonical.${candidate}`,
    `${domainKey}.${candidate}`,
  ]);

  for (const fieldPath of flatPathCandidates) {
    if (Object.prototype.hasOwnProperty.call(payload, fieldPath)) {
      return unwrapSuggestionValue(payload[fieldPath]);
    }
  }

  const domainPayload = payload[domainKey];
  if (!domainPayload || typeof domainPayload !== 'object') {
    return undefined;
  }

  const canonicalPayload = domainPayload.canonical;
  if (canonicalPayload && typeof canonicalPayload === 'object') {
    for (const candidate of fieldCandidates) {
      if (Object.prototype.hasOwnProperty.call(canonicalPayload, candidate)) {
        return unwrapSuggestionValue(canonicalPayload[candidate]);
      }
    }
  }

  for (const candidate of fieldCandidates) {
    if (Object.prototype.hasOwnProperty.call(domainPayload, candidate)) {
      return unwrapSuggestionValue(domainPayload[candidate]);
    }
  }

  return undefined;
};

const normalizeComparableValue = (field, value) => {
  if (field.type === 'text') {
    return normalizeString(value);
  }
  if (field.type === 'list') {
    return normalizeStringList(value);
  }
  if (field.type === 'service_list') {
    return normalizeServiceEntries(value);
  }
  if (field.type === 'integration_list') {
    return normalizeIntegrationEntries(value);
  }
  if (field.type === 'tech_stack') {
    return normalizeTechStack(value);
  }
  if (field.type === 'performance') {
    return normalizePerformanceBaseline(value);
  }
  return deepClone(value);
};

const isSameFieldValue = (field, left, right) => (
  JSON.stringify(normalizeComparableValue(field, left))
  === JSON.stringify(normalizeComparableValue(field, right))
);

const splitPeerSystems = (value) => normalizeString(value)
  .replace(/[，,；;]/g, '、')
  .split('、')
  .map((item) => item.trim())
  .filter(Boolean);

const buildServicePreviewRows = (value) => {
  const rows = normalizeServiceEntries(value);
  if (!rows.length) {
    return [];
  }

  const groupedRows = new Map();
  rows.forEach((row) => {
    const serviceName = normalizeString(row.service_name);
    const transactionName = normalizeString(row.transaction_name);
    const groupKey = `${serviceName}__${transactionName}`;
    const existing = groupedRows.get(groupKey) || {
      service_name: serviceName,
      transaction_name: transactionName,
      peer_systems: [],
    };

    splitPeerSystems(row.peer_system).forEach((peerSystem) => {
      if (!existing.peer_systems.includes(peerSystem)) {
        existing.peer_systems.push(peerSystem);
      }
    });
    groupedRows.set(groupKey, existing);
  });

  return Array.from(groupedRows.values()).map((row) => ({
    service_name: row.service_name,
    transaction_name: row.transaction_name,
    peer_system: row.peer_systems.join('、'),
  }));
};

const SimpleTable = ({ headers, rows }) => {
  if (!rows.length) {
    return <Text type="secondary">—</Text>;
  }

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            {headers.map((header) => (
              <th
                key={header.key}
                style={{
                  borderBottom: '1px solid #f0f0f0',
                  padding: '8px',
                  textAlign: 'left',
                  fontWeight: 600,
                  whiteSpace: 'nowrap',
                }}
              >
                {header.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={`row-${rowIndex}`}>
              {headers.map((header) => (
                <td
                  key={`${rowIndex}-${header.key}`}
                  style={{
                    borderBottom: '1px solid #f5f5f5',
                    padding: '8px',
                    verticalAlign: 'top',
                  }}
                >
                  {normalizeString(row[header.key]) || <Text type="secondary">—</Text>}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

const SystemProfileBoardPage = () => {
  const { user } = useAuth();
  const permission = usePermission();
  const {
    isManager = false,
    isAdmin = false,
    isExpert = false,
  } = permission || {};
  const location = useLocation();
  const navigate = useNavigate();

  const [systems, setSystems] = useState([]);
  const [selectedSystemName, setSelectedSystemName] = useState(() => (
    normalizeString(new URLSearchParams(location.search).get('system_name'))
  ));
  const [activeDomain, setActiveDomain] = useState(DOMAIN_CONFIG[0].key);

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

  const [savedProfileData, setSavedProfileData] = useState(buildEmptyProfileData());
  const [draftProfileData, setDraftProfileData] = useState(buildEmptyProfileData());
  const [editingFields, setEditingFields] = useState({});

  const [aiSuggestions, setAiSuggestions] = useState({});
  const [aiSuggestionsPrevious, setAiSuggestionsPrevious] = useState(null);
  const [ignoredSuggestions, setIgnoredSuggestions] = useState({});

  const [timelineItems, setTimelineItems] = useState([]);
  const [timelineTotal, setTimelineTotal] = useState(0);
  const [timelineLoading, setTimelineLoading] = useState(false);
  const [timelineLoadingMore, setTimelineLoadingMore] = useState(false);
  const [timelineExpanded, setTimelineExpanded] = useState(true);

  const [completenessInfo, setCompletenessInfo] = useState(null);
  const [completenessUnknown, setCompletenessUnknown] = useState(false);

  const queryParams = useMemo(() => new URLSearchParams(location.search), [location.search]);
  const requestedSystemName = useMemo(
    () => normalizeString(queryParams.get('system_name')),
    [queryParams]
  );
  const requestedSystemId = useMemo(
    () => normalizeString(queryParams.get('system_id')),
    [queryParams]
  );

  useEffect(() => {
    if (!selectedSystemName && requestedSystemName) {
      setSelectedSystemName(requestedSystemName);
    }
  }, [requestedSystemName, selectedSystemName]);

  const visibleSystems = useMemo(() => {
    if (isManager) {
      return filterResponsibleSystems(systems, user);
    }
    if (isAdmin || isExpert) {
      return Array.isArray(systems) ? systems : [];
    }
    return [];
  }, [isAdmin, isExpert, isManager, systems, user]);

  const effectiveSystems = useMemo(() => {
    if (visibleSystems.length > 0) {
      return visibleSystems;
    }
    if (!requestedSystemName) {
      return [];
    }
    return [
      {
        id: requestedSystemId || requestedSystemName,
        name: requestedSystemName,
        status: '',
        extra: isManager ? { owner_username: user?.username || '' } : {},
      },
    ];
  }, [isManager, requestedSystemId, requestedSystemName, user?.username, visibleSystems]);

  const selectedSystem = useMemo(
    () => effectiveSystems.find((item) => item.name === selectedSystemName),
    [effectiveSystems, selectedSystemName]
  );

  const effectiveSystemId = useMemo(
    () => normalizeString(selectedSystem?.id || profileMeta.system_id || requestedSystemId),
    [profileMeta.system_id, requestedSystemId, selectedSystem?.id]
  );

  const canWrite = useMemo(() => {
    if (!isManager || !selectedSystem) {
      return false;
    }
    return resolveSystemOwnership(selectedSystem, user).canWrite;
  }, [isManager, selectedSystem, user]);

  const activeDomainConfig = DOMAIN_BY_KEY[activeDomain] || DOMAIN_CONFIG[0];

  const loadSystems = useCallback(async () => {
    try {
      const response = await axios.get('/api/v1/system/systems');
      setSystems(Array.isArray(response.data?.data?.systems) ? response.data.data.systems : []);
    } catch (error) {
      message.error(parseErrorMessage(error, '加载系统清单失败'));
    }
  }, []);

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

  const applyProfilePayload = useCallback((payload, fallbackSystemId = '') => {
    const normalizedProfileData = normalizeProfileData(payload?.profile_data);

    setSavedProfileData(normalizedProfileData);
    setDraftProfileData(deepClone(normalizedProfileData));
    setAiSuggestions(payload?.ai_suggestions && typeof payload.ai_suggestions === 'object' ? payload.ai_suggestions : {});
    setAiSuggestionsPrevious(
      payload?.ai_suggestions_previous && typeof payload.ai_suggestions_previous === 'object'
        ? payload.ai_suggestions_previous
        : null
    );
    setIgnoredSuggestions(
      payload?.ai_suggestion_ignored && typeof payload.ai_suggestion_ignored === 'object'
        ? payload.ai_suggestion_ignored
        : {}
    );
    setProfileMeta({
      status: payload?.status || 'draft',
      pending_fields: Array.isArray(payload?.pending_fields) ? payload.pending_fields : [],
      updated_at: payload?.updated_at || payload?.created_at || '',
      is_stale: Boolean(payload?.is_stale),
      system_id: normalizeString(payload?.system_id || fallbackSystemId),
    });
  }, []);

  const loadProfileDetail = useCallback(async (systemName, systemIdHint = '') => {
    if (!systemName) {
      return;
    }

    setLoadingProfile(true);
    try {
      const response = await axios.get(`/api/v1/system-profiles/${encodeURIComponent(systemName)}`);
      const payload = response.data?.data;
      const resolvedSystemId = normalizeString(payload?.system_id || systemIdHint);

      applyProfilePayload(
        payload || {
          profile_data: buildEmptyProfileData(),
          field_sources: {},
          ai_suggestions: {},
          ai_suggestions_previous: null,
          ai_suggestion_ignored: {},
          pending_fields: [],
          status: 'draft',
          updated_at: '',
          is_stale: false,
          system_id: resolvedSystemId,
        },
        resolvedSystemId
      );

      setLoadingProfile(false);
      setTimelineLoading(true);
      const [timeline] = await Promise.all([
        loadTimelinePage(resolvedSystemId, 0),
        loadCompleteness(systemName),
      ]);
      setTimelineItems(timeline.items);
      setTimelineTotal(timeline.total);
      setTimelineLoading(false);
    } catch (error) {
      message.error(parseErrorMessage(error, '加载系统画像详情失败'));
      setTimelineItems([]);
      setTimelineTotal(0);
      setTimelineLoading(false);
    } finally {
      setLoadingProfile(false);
    }
  }, [applyProfilePayload, loadCompleteness, loadTimelinePage]);

  const syncSelectedSystemFromUrl = useCallback((items) => {
    if (!items.length) {
      setSelectedSystemName('');
      return;
    }

    const existsInList = requestedSystemName && items.some((item) => item.name === requestedSystemName);
    const nextName = existsInList ? requestedSystemName : items[0].name;
    const nextSystem = items.find((item) => item.name === nextName);
    const nextSystemId = normalizeString(nextSystem?.id);

    setSelectedSystemName(nextName);

    if (requestedSystemName !== nextName || requestedSystemId !== nextSystemId) {
      const nextParams = new URLSearchParams(location.search);
      nextParams.set('system_name', nextName);
      if (nextSystemId) {
        nextParams.set('system_id', nextSystemId);
      } else {
        nextParams.delete('system_id');
      }
      navigate(
        {
          pathname: location.pathname,
          search: `?${nextParams.toString()}`,
        },
        { replace: true }
      );
    }
  }, [location.pathname, location.search, navigate, requestedSystemId, requestedSystemName]);

  useEffect(() => {
    loadSystems();
  }, [loadSystems]);

  useEffect(() => {
    if (!effectiveSystems.length) {
      setSelectedSystemName('');
      return;
    }

    syncSelectedSystemFromUrl(effectiveSystems);
  }, [effectiveSystems, syncSelectedSystemFromUrl]);

  useEffect(() => {
    if (!selectedSystemName) {
      return;
    }
    loadProfileDetail(selectedSystemName, selectedSystem?.id || requestedSystemId);
  }, [loadProfileDetail, requestedSystemId, selectedSystem?.id, selectedSystemName]);

  const setDraftFieldValue = useCallback((domainKey, fieldKey, nextValue) => {
    setDraftProfileData((previous) => {
      const next = deepClone(previous);
      const currentValue = next?.[domainKey]?.canonical?.[fieldKey];
      next[domainKey].canonical[fieldKey] = typeof nextValue === 'function' ? nextValue(currentValue) : nextValue;
      return next;
    });
  }, []);

  const toggleFieldEditMode = useCallback((fieldPath) => {
    setEditingFields((previous) => ({ ...previous, [fieldPath]: !previous[fieldPath] }));
  }, []);

  const domainHasDiff = useCallback((domainKey) => {
    const domain = DOMAIN_BY_KEY[domainKey];
    if (!domain) {
      return false;
    }

    return domain.fields.some((field) => {
      const currentValue = savedProfileData?.[domainKey]?.canonical?.[field.key];
      const suggestionValue = readSuggestionValue(aiSuggestions, domainKey, field.key);
      const ignoredValue = readSuggestionValue(ignoredSuggestions, domainKey, field.key);

      if (suggestionValue === undefined || !hasMeaningfulValue(suggestionValue)) {
        return false;
      }
      if (ignoredValue !== undefined && isSameFieldValue(field, ignoredValue, suggestionValue)) {
        return false;
      }
      return !isSameFieldValue(field, currentValue, suggestionValue);
    });
  }, [aiSuggestions, ignoredSuggestions, savedProfileData]);

  const renderTextPreview = (value) => {
    const text = normalizeString(value);
    return (
      <Card size="small">
        {text ? (
          <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>{text}</div>
        ) : (
          <Text type="secondary">—</Text>
        )}
      </Card>
    );
  };

  const renderListPreview = (value) => {
    const items = normalizeStringList(value);
    return (
      <Card size="small">
        {items.length > 0 ? (
          <Space wrap size={[6, 6]}>
            {items.map((item, index) => <Tag key={`tag-${index}`}>{item}</Tag>)}
          </Space>
        ) : (
          <Text type="secondary">—</Text>
        )}
      </Card>
    );
  };

  const renderServicePreview = (value) => (
    <Card size="small">
      <SimpleTable
        headers={[
          { key: 'service_name', label: '服务名称' },
          { key: 'transaction_name', label: '交易名称' },
          { key: 'peer_system', label: '对端系统' },
        ]}
        rows={buildServicePreviewRows(value)}
      />
    </Card>
  );

  const renderIntegrationPreview = (value) => (
    <Card size="small">
      <SimpleTable
        headers={[
          { key: 'integration_name', label: '集成项' },
          { key: 'peer_system', label: '对端系统' },
          { key: 'notes', label: '说明' },
        ]}
        rows={normalizeIntegrationEntries(value)}
      />
    </Card>
  );

  const renderTechStackPreview = (value) => {
    const techStack = normalizeTechStack(value);
    const groups = TECH_STACK_GROUPS
      .map((group) => ({ ...group, items: normalizeStringList(techStack[group.key]) }))
      .filter((group) => group.items.length > 0);

    return (
      <Card size="small">
        {groups.length > 0 ? (
          <Space direction="vertical" size={8} style={{ width: '100%' }}>
            {groups.map((group) => (
              <div key={group.key}>
                <Text strong>{group.label}</Text>
                <div style={{ marginTop: 6 }}>
                  <Space wrap size={[6, 6]}>
                    {group.items.map((item, index) => <Tag key={`${group.key}-${index}`}>{item}</Tag>)}
                  </Space>
                </div>
              </div>
            ))}
          </Space>
        ) : (
          <Text type="secondary">—</Text>
        )}
      </Card>
    );
  };

  const renderPerformancePreview = (value) => {
    const performance = normalizePerformanceBaseline(value);
    const onlineRows = PERFORMANCE_SECTIONS[0].fields.map((field) => ({
      metric: field.label,
      value: performance.online[field.key],
    }));
    const batchRows = PERFORMANCE_SECTIONS[1].fields.map((field) => ({
      metric: field.label,
      value: performance.batch[field.key],
    }));

    return (
      <Card size="small">
        <Space direction="vertical" size={12} style={{ width: '100%' }}>
          <div>
            <Text strong>处理模式</Text>
            <div style={{ marginTop: 4 }}>
              {normalizeString(performance.processing_model) || <Text type="secondary">—</Text>}
            </div>
          </div>
          <div>
            <Text strong>在线指标</Text>
            <div style={{ marginTop: 6 }}>
              <SimpleTable
                headers={[
                  { key: 'metric', label: '指标' },
                  { key: 'value', label: '值' },
                ]}
                rows={onlineRows.filter((row) => normalizeString(row.value))}
              />
            </div>
          </div>
          <div>
            <Text strong>批处理指标</Text>
            <div style={{ marginTop: 6 }}>
              <SimpleTable
                headers={[
                  { key: 'metric', label: '指标' },
                  { key: 'value', label: '值' },
                ]}
                rows={batchRows.filter((row) => normalizeString(row.value))}
              />
            </div>
          </div>
        </Space>
      </Card>
    );
  };

  const renderFieldPreview = (field, value) => {
    if (field.type === 'text') {
      return renderTextPreview(value);
    }
    if (field.type === 'list') {
      return renderListPreview(value);
    }
    if (field.type === 'service_list') {
      return renderServicePreview(value);
    }
    if (field.type === 'integration_list') {
      return renderIntegrationPreview(value);
    }
    if (field.type === 'tech_stack') {
      return renderTechStackPreview(value);
    }
    if (field.type === 'performance') {
      return renderPerformancePreview(value);
    }
    return renderTextPreview('');
  };

  const renderStringListEditor = (domainKey, field, value) => {
    const items = Array.isArray(value) ? value.map((item) => String(item ?? '')) : [];
    const visibleItems = items.length > 0 ? items : [''];

    return (
      <Space direction="vertical" size={8} style={{ width: '100%' }}>
        {visibleItems.map((item, index) => (
          <Space key={`${field.key}-${index}`} style={{ width: '100%' }} align="start">
            <Input
              value={item}
              placeholder={`请输入${field.label}`}
              disabled={!canWrite}
              onChange={(event) => {
                const next = [...visibleItems];
                next[index] = event.target.value;
                setDraftFieldValue(domainKey, field.key, next);
              }}
            />
            {visibleItems.length > 1 && (
              <Button
                size="small"
                disabled={!canWrite}
                onClick={() => {
                  const next = visibleItems.filter((_, itemIndex) => itemIndex !== index);
                  setDraftFieldValue(domainKey, field.key, next);
                }}
              >
                删除
              </Button>
            )}
          </Space>
        ))}
        <Button
          size="small"
          disabled={!canWrite}
          onClick={() => setDraftFieldValue(domainKey, field.key, [...visibleItems, ''])}
        >
          新增一项
        </Button>
      </Space>
    );
  };

  const renderServiceListEditor = (domainKey, field, value) => {
    const rows = Array.isArray(value)
      ? value.map((item) => ({ ...EMPTY_SERVICE_ROW, ...coerceServiceDraftRow(item || {}) }))
      : [];
    const visibleRows = rows.length > 0 ? rows : [deepClone(EMPTY_SERVICE_ROW)];

    return (
      <Space direction="vertical" size={8} style={{ width: '100%' }}>
        {visibleRows.map((row, index) => (
          <Card key={`${field.key}-${index}`} size="small">
            <Space direction="vertical" size={8} style={{ width: '100%' }}>
              <Space style={{ width: '100%' }} align="start">
                <Input
                  value={row.service_name}
                  placeholder="服务名称"
                  disabled={!canWrite}
                  onChange={(event) => {
                    const next = deepClone(visibleRows);
                    next[index].service_name = event.target.value;
                    setDraftFieldValue(domainKey, field.key, next);
                  }}
                />
                <Input
                  value={row.transaction_name}
                  placeholder="交易名称"
                  disabled={!canWrite}
                  onChange={(event) => {
                    const next = deepClone(visibleRows);
                    next[index].transaction_name = event.target.value;
                    setDraftFieldValue(domainKey, field.key, next);
                  }}
                />
              </Space>
              <Input
                value={row.peer_system}
                placeholder="对端系统"
                disabled={!canWrite}
                onChange={(event) => {
                  const next = deepClone(visibleRows);
                  next[index].peer_system = event.target.value;
                  setDraftFieldValue(domainKey, field.key, next);
                }}
              />
              {visibleRows.length > 1 && (
                <div>
                  <Button
                    size="small"
                    disabled={!canWrite}
                    onClick={() => {
                      const next = visibleRows.filter((_, rowIndex) => rowIndex !== index);
                      setDraftFieldValue(domainKey, field.key, next);
                    }}
                  >
                    删除
                  </Button>
                </div>
              )}
            </Space>
          </Card>
        ))}
        <Button
          size="small"
          disabled={!canWrite}
          onClick={() => setDraftFieldValue(domainKey, field.key, [...visibleRows, deepClone(EMPTY_SERVICE_ROW)])}
        >
          新增服务
        </Button>
      </Space>
    );
  };

  const renderIntegrationListEditor = (domainKey, field, value) => {
    const rows = Array.isArray(value)
      ? value.map((item) => ({ ...EMPTY_INTEGRATION_ROW, ...coerceIntegrationDraftRow(item || {}) }))
      : [];
    const visibleRows = rows.length > 0 ? rows : [deepClone(EMPTY_INTEGRATION_ROW)];

    return (
      <Space direction="vertical" size={8} style={{ width: '100%' }}>
        {visibleRows.map((row, index) => (
          <Card key={`${field.key}-${index}`} size="small">
            <Space direction="vertical" size={8} style={{ width: '100%' }}>
              <Space style={{ width: '100%' }} align="start">
                <Input
                  value={row.integration_name}
                  placeholder="集成项"
                  disabled={!canWrite}
                  onChange={(event) => {
                    const next = deepClone(visibleRows);
                    next[index].integration_name = event.target.value;
                    setDraftFieldValue(domainKey, field.key, next);
                  }}
                />
                <Input
                  value={row.peer_system}
                  placeholder="对端系统"
                  disabled={!canWrite}
                  onChange={(event) => {
                    const next = deepClone(visibleRows);
                    next[index].peer_system = event.target.value;
                    setDraftFieldValue(domainKey, field.key, next);
                  }}
                />
              </Space>
              <Input.TextArea
                autoSize={{ minRows: 2, maxRows: 4 }}
                value={row.notes}
                placeholder="说明"
                disabled={!canWrite}
                onChange={(event) => {
                  const next = deepClone(visibleRows);
                  next[index].notes = event.target.value;
                  setDraftFieldValue(domainKey, field.key, next);
                }}
              />
              {visibleRows.length > 1 && (
                <div>
                  <Button
                    size="small"
                    disabled={!canWrite}
                    onClick={() => {
                      const next = visibleRows.filter((_, rowIndex) => rowIndex !== index);
                      setDraftFieldValue(domainKey, field.key, next);
                    }}
                  >
                    删除
                  </Button>
                </div>
              )}
            </Space>
          </Card>
        ))}
        <Button
          size="small"
          disabled={!canWrite}
          onClick={() => setDraftFieldValue(domainKey, field.key, [...visibleRows, deepClone(EMPTY_INTEGRATION_ROW)])}
        >
          新增集成项
        </Button>
      </Space>
    );
  };

  const renderTechStackEditor = (domainKey, field, value) => {
    const techStack = value && typeof value === 'object' ? value : {};

    return (
      <Space direction="vertical" size={12} style={{ width: '100%' }}>
        {TECH_STACK_GROUPS.map((group) => {
          const items = Array.isArray(techStack[group.key])
            ? techStack[group.key].map((item) => String(item ?? ''))
            : [];
          const visibleItems = items.length > 0 ? items : [''];

          return (
            <Card key={group.key} size="small" title={group.label}>
              <Space direction="vertical" size={8} style={{ width: '100%' }}>
                {visibleItems.map((item, index) => (
                  <Space key={`${group.key}-${index}`} style={{ width: '100%' }} align="start">
                    <Input
                      value={item}
                      placeholder={`请输入${group.label}`}
                      disabled={!canWrite}
                      onChange={(event) => {
                        const nextGroupItems = [...visibleItems];
                        nextGroupItems[index] = event.target.value;
                        const nextTechStack = {
                          ...normalizeTechStack(techStack),
                          [group.key]: nextGroupItems,
                        };
                        setDraftFieldValue(domainKey, field.key, nextTechStack);
                      }}
                    />
                    {visibleItems.length > 1 && (
                      <Button
                        size="small"
                        disabled={!canWrite}
                        onClick={() => {
                          const nextGroupItems = visibleItems.filter((_, itemIndex) => itemIndex !== index);
                          const nextTechStack = {
                            ...normalizeTechStack(techStack),
                            [group.key]: nextGroupItems,
                          };
                          setDraftFieldValue(domainKey, field.key, nextTechStack);
                        }}
                      >
                        删除
                      </Button>
                    )}
                  </Space>
                ))}
                <Button
                  size="small"
                  disabled={!canWrite}
                  onClick={() => {
                    const nextTechStack = {
                      ...normalizeTechStack(techStack),
                      [group.key]: [...visibleItems, ''],
                    };
                    setDraftFieldValue(domainKey, field.key, nextTechStack);
                  }}
                >
                  新增一项
                </Button>
              </Space>
            </Card>
          );
        })}
      </Space>
    );
  };

  const renderPerformanceEditor = (domainKey, field, value) => {
    const performance = normalizePerformanceBaseline(value);

    return (
      <Space direction="vertical" size={12} style={{ width: '100%' }}>
        <Card size="small" title="处理模式">
          <Input
            value={performance.processing_model}
            placeholder="请输入处理模式"
            disabled={!canWrite}
            onChange={(event) => {
              setDraftFieldValue(domainKey, field.key, {
                ...performance,
                processing_model: event.target.value,
              });
            }}
          />
        </Card>

        {PERFORMANCE_SECTIONS.map((section) => (
          <Card key={section.key} size="small" title={section.label}>
            <Space direction="vertical" size={8} style={{ width: '100%' }}>
              {section.fields.map((sectionField) => (
                <Space key={`${section.key}-${sectionField.key}`} style={{ width: '100%' }} align="start">
                  <Text style={{ width: 120, flexShrink: 0 }}>{sectionField.label}</Text>
                  <Input
                    value={performance[section.key][sectionField.key]}
                    placeholder={`请输入${sectionField.label}`}
                    disabled={!canWrite}
                    onChange={(event) => {
                      const nextSection = {
                        ...performance[section.key],
                        [sectionField.key]: event.target.value,
                      };
                      setDraftFieldValue(domainKey, field.key, {
                        ...performance,
                        [section.key]: nextSection,
                      });
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

  const renderFieldEditor = (domainKey, field, value) => {
    if (field.type === 'text') {
      return (
        <Input.TextArea
          rows={4}
          disabled={!canWrite}
          value={String(value ?? '')}
          placeholder={`请输入${field.label}`}
          onChange={(event) => setDraftFieldValue(domainKey, field.key, event.target.value)}
        />
      );
    }
    if (field.type === 'list') {
      return renderStringListEditor(domainKey, field, value);
    }
    if (field.type === 'service_list') {
      return renderServiceListEditor(domainKey, field, value);
    }
    if (field.type === 'integration_list') {
      return renderIntegrationListEditor(domainKey, field, value);
    }
    if (field.type === 'tech_stack') {
      return renderTechStackEditor(domainKey, field, value);
    }
    if (field.type === 'performance') {
      return renderPerformanceEditor(domainKey, field, value);
    }
    return null;
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

    try {
      setSavingProfile(true);
      const payload = normalizeProfileData(draftProfileData);
      await axios.put(`/api/v1/system-profiles/${encodeURIComponent(selectedSystemName)}`, {
        system_id: effectiveSystemId,
        profile_data: payload,
        evidence_refs: [],
      });
      message.success('系统画像草稿已保存');
      await loadProfileDetail(selectedSystemName, effectiveSystemId);
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

    try {
      setPublishingProfile(true);
      const payload = normalizeProfileData(draftProfileData);
      await axios.put(`/api/v1/system-profiles/${encodeURIComponent(selectedSystemName)}`, {
        system_id: effectiveSystemId,
        profile_data: payload,
        evidence_refs: [],
      });
      await axios.post(`/api/v1/system-profiles/${encodeURIComponent(selectedSystemName)}/publish`);
      message.success('系统画像已发布');
      await loadProfileDetail(selectedSystemName, effectiveSystemId);
    } catch (error) {
      message.error(parseErrorMessage(error, '发布系统画像失败'));
    } finally {
      setPublishingProfile(false);
    }
  };

  const handleAcceptSuggestion = async (domainKey, fieldKey) => {
    if (!effectiveSystemId) {
      message.error('系统ID缺失，无法执行操作');
      return;
    }

    try {
      const response = await axios.post(
        `/api/v1/system-profiles/${encodeURIComponent(effectiveSystemId)}/profile/suggestions/accept`,
        { domain: domainKey, sub_field: fieldKey }
      );
      if (response.data?.data) {
        applyProfilePayload(response.data.data, effectiveSystemId);
      }
      message.success('已采纳AI建议');
    } catch (error) {
      message.error(parseErrorMessage(error, '采纳AI建议失败'));
    }
  };

  const handleIgnoreSuggestion = async (domainKey, fieldKey) => {
    if (!effectiveSystemId) {
      message.error('系统ID缺失，无法执行操作');
      return;
    }

    try {
      const response = await axios.post(
        `/api/v1/system-profiles/${encodeURIComponent(effectiveSystemId)}/profile/suggestions/ignore`,
        { domain: domainKey, sub_field: fieldKey }
      );
      if (response.data?.data) {
        applyProfilePayload(response.data.data, effectiveSystemId);
      }
      message.success('已忽略AI建议');
    } catch (error) {
      const errorCode = error?.response?.data?.error_code;
      if (errorCode === 'SUGGESTION_NOT_FOUND') {
        message.warning('AI 建议不存在');
        return;
      }
      message.error(parseErrorMessage(error, '忽略AI建议失败'));
    }
  };

  const handleRollbackSuggestion = async (domainKey, fieldKey) => {
    if (!effectiveSystemId) {
      message.error('系统ID缺失，无法执行操作');
      return;
    }

    try {
      const response = await axios.post(
        `/api/v1/system-profiles/${encodeURIComponent(effectiveSystemId)}/profile/suggestions/rollback`,
        { domain: domainKey, sub_field: fieldKey }
      );
      if (response.data?.data) {
        applyProfilePayload(response.data.data, effectiveSystemId);
      }
      message.success('已恢复上一版建议');
    } catch (error) {
      const errorCode = error?.response?.data?.error_code;
      if (errorCode === 'ROLLBACK_NO_PREVIOUS') {
        message.warning('无历史版本');
        return;
      }
      message.error(parseErrorMessage(error, '恢复上一版建议失败'));
    }
  };

  const handleSystemTabChange = (systemName) => {
    const nextName = normalizeString(systemName);
    if (!nextName) {
      return;
    }

    const nextSystem = effectiveSystems.find((item) => item.name === nextName);
    const nextParams = new URLSearchParams(location.search);
    nextParams.set('system_name', nextName);
    const nextId = normalizeString(nextSystem?.id);
    if (nextId) {
      nextParams.set('system_id', nextId);
    } else {
      nextParams.delete('system_id');
    }

    navigate(
      {
        pathname: location.pathname,
        search: `?${nextParams.toString()}`,
      },
      { replace: true }
    );
    setSelectedSystemName(nextName);
  };

  const handleLoadMoreTimeline = async () => {
    if (!effectiveSystemId) {
      return;
    }

    setTimelineLoadingMore(true);
    const timeline = await loadTimelinePage(effectiveSystemId, timelineItems.length);
    setTimelineItems((previous) => [...previous, ...timeline.items]);
    setTimelineTotal(timeline.total);
    setTimelineLoadingMore(false);
  };

  const profileStatusTag = (
    <Tag color={profileMeta.status === 'published' ? 'green' : 'gold'}>
      {profileMeta.status === 'published' ? '已发布' : '草稿'}
    </Tag>
  );

  const totalScore = completenessInfo?.completeness_score ?? 0;
  const breakdown = completenessInfo?.breakdown || {};

  if (!effectiveSystems.length) {
    return (
      <Card>
        <Text type="secondary">暂无可查看系统。请联系管理员维护系统负责关系。</Text>
      </Card>
    );
  }

  return (
    <Space direction="vertical" style={{ width: '100%' }} size={12}>
      <Space direction="vertical" style={{ width: '100%' }} size={6}>
        <Tabs
          size="small"
          activeKey={selectedSystemName || undefined}
          onChange={handleSystemTabChange}
          items={effectiveSystems.map((item) => ({ key: item.name, label: item.name }))}
        />

        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          {profileStatusTag}
          {profileMeta.is_stale && <Tag color="orange">画像过时</Tag>}
          <Tag>{selectedSystem?.status || '-'}</Tag>
          {completenessUnknown ? (
            <Tag>完整度未知</Tag>
          ) : (
            <>
              <Tag color="blue">完整度 {totalScore}/100</Tag>
              <Text type="secondary" style={{ fontSize: 12 }}>
                代码{breakdown.code_scan ?? 0}/30 · 文档{breakdown.documents ?? 0}/40 · ESB{breakdown.esb ?? 0}/30
              </Text>
            </>
          )}
          {!canWrite && isManager && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              当前系统只读，仅主责或B角可编辑。
            </Text>
          )}
          <Button
            size="small"
            type="text"
            icon={timelineExpanded ? <RightOutlined /> : <LeftOutlined />}
            onClick={() => setTimelineExpanded((previous) => !previous)}
          >
            {timelineExpanded ? '收起时间线' : '展开时间线'}
          </Button>
          <Button
            size="small"
            icon={<ReloadOutlined />}
            onClick={() => loadProfileDetail(selectedSystemName, effectiveSystemId)}
          >
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
            {DOMAIN_CONFIG.map((domain) => (
              <Button
                key={domain.key}
                type={activeDomain === domain.key ? 'primary' : 'default'}
                block
                onClick={() => setActiveDomain(domain.key)}
                style={{ justifyContent: 'flex-start', textAlign: 'left' }}
              >
                <Space size={6}>
                  <span>{domain.label}</span>
                  {domainHasDiff(domain.key) && <Tag color="blue">有建议</Tag>}
                </Space>
              </Button>
            ))}
          </Space>
        </Card>

        <Card>
          <Space direction="vertical" size={12} style={{ width: '100%' }}>
            {loadingProfile && <Text type="secondary">加载中...</Text>}
            {activeDomainConfig.fields.map((field) => {
              const fieldPath = getFieldPath(activeDomainConfig.key, field.key);
              const value = draftProfileData?.[activeDomainConfig.key]?.canonical?.[field.key];
              const currentValue = savedProfileData?.[activeDomainConfig.key]?.canonical?.[field.key];
              const suggestionValue = readSuggestionValue(aiSuggestions, activeDomainConfig.key, field.key);
              const ignoredValue = readSuggestionValue(ignoredSuggestions, activeDomainConfig.key, field.key);
              const hasVisibleSuggestion = suggestionValue !== undefined
                && hasMeaningfulValue(suggestionValue)
                && !(ignoredValue !== undefined && isSameFieldValue(field, ignoredValue, suggestionValue))
                && !isSameFieldValue(field, currentValue, suggestionValue);
              const previousSuggestionValue = readSuggestionValue(aiSuggestionsPrevious, activeDomainConfig.key, field.key);
              const hasPreviousSuggestion = previousSuggestionValue !== undefined
                && hasMeaningfulValue(previousSuggestionValue);
              const editing = canWrite && Boolean(editingFields[fieldPath]);

              return (
                <div key={fieldPath}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'center' }}>
                    <Text strong>{field.label}</Text>
                    {canWrite && (
                      <Button
                        size="small"
                        type="link"
                        aria-label={`${editing ? '收起编辑' : '编辑'}${field.label}`}
                        style={{ paddingInline: 0 }}
                        onClick={() => toggleFieldEditMode(fieldPath)}
                      >
                        {editing ? '收起编辑' : '编辑'}
                      </Button>
                    )}
                  </div>

                  <div style={{ marginTop: 6 }}>
                    {editing
                      ? renderFieldEditor(activeDomainConfig.key, field, value)
                      : renderFieldPreview(field, value)}
                  </div>

                  {hasVisibleSuggestion && (
                    <Card size="small" style={{ marginTop: 8, background: '#fafcff' }}>
                      <Space direction="vertical" size={8} style={{ width: '100%' }}>
                        <Text strong>检测到 AI 建议变更</Text>
                        <div style={{ display: 'grid', gap: 8, gridTemplateColumns: '1fr 1fr' }}>
                          <div>
                            <Text type="secondary">当前值</Text>
                            <div style={{ marginTop: 6 }}>
                              {renderFieldPreview(field, currentValue)}
                            </div>
                          </div>
                          <div>
                            <Text type="secondary">AI 建议</Text>
                            <div style={{ marginTop: 6 }}>
                              {renderFieldPreview(field, suggestionValue)}
                            </div>
                          </div>
                        </div>
                        <Space wrap>
                          <Button
                            size="small"
                            type="primary"
                            aria-label="采纳新建议"
                            disabled={!canWrite}
                            onClick={() => handleAcceptSuggestion(activeDomainConfig.key, field.key)}
                          >
                            采纳新建议
                          </Button>
                          <Button
                            size="small"
                            aria-label="忽略"
                            disabled={!canWrite}
                            onClick={() => handleIgnoreSuggestion(activeDomainConfig.key, field.key)}
                          >
                            忽略
                          </Button>
                          <Button
                            size="small"
                            aria-label="恢复上一版建议"
                            disabled={!canWrite || !hasPreviousSuggestion}
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
                aria-label="保存草稿"
                loading={savingProfile}
                disabled={!canWrite}
                onClick={handleSaveDraft}
              >
                保存草稿
              </Button>
              <Button
                icon={<SendOutlined />}
                aria-label="发布画像"
                loading={publishingProfile}
                disabled={!canWrite}
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
                    const eventType = EVENT_TYPE_LABELS[normalizeString(item?.event_type)] || normalizeString(item?.event_type || '变更');
                    return (
                      <List.Item>
                        <Space direction="vertical" size={2} style={{ width: '100%' }}>
                          <Space size={6} wrap>
                            <Tag color="blue">{eventType || '变更'}</Tag>
                            <Text type="secondary" style={{ fontSize: 12 }}>{formatDateTime(item?.timestamp)}</Text>
                          </Space>
                          <Text>{normalizeString(item?.summary) || '-'}</Text>
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
  );
};

export default SystemProfileBoardPage;
