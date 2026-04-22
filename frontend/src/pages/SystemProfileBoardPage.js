import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
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
      { key: 'system_aliases', label: '系统别名', type: 'list' },
      { key: 'lifecycle_status', label: '生命周期状态', type: 'text' },
      { key: 'business_domains', label: '业务域', type: 'list' },
      { key: 'business_lines', label: '业务条线', type: 'list' },
      { key: 'architecture_layer', label: '架构层级', type: 'text' },
      { key: 'application_level', label: '应用等级', type: 'text' },
      { key: 'target_users', label: '目标用户', type: 'list' },
      { key: 'core_responsibility', label: '核心职责', type: 'text' },
    ],
  },
  {
    key: 'business_capabilities',
    label: 'D2 业务能力与流程',
    fields: [
      { key: 'functional_modules', label: '模块结构', type: 'named_list' },
      { key: 'business_scenarios', label: '典型场景', type: 'named_list' },
      { key: 'business_flows', label: '核心流程', type: 'named_list' },
      { key: 'data_reports', label: '数据报表', type: 'data_report_list' },
    ],
  },
  {
    key: 'integration_interfaces',
    label: 'D3 集成与接口',
    fields: [
      { key: 'provided_services', label: '对外提供能力', type: 'service_list' },
      { key: 'consumed_services', label: '对外依赖能力', type: 'service_list' },
      { key: 'other_integrations', label: '集成点', type: 'integration_list' },
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
      { key: 'business_constraints', label: '关键约束', type: 'named_list' },
      { key: 'prerequisites', label: '前提条件', type: 'named_list' },
      { key: 'sensitive_points', label: '敏感环节', type: 'named_list' },
      { key: 'risk_items', label: '已知风险', type: 'risk_list' },
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

const BOARD_STICKY_TOP = 16;

const DOMAIN_NAV_CARD_STYLE = {
  position: 'sticky',
  top: BOARD_STICKY_TOP,
  alignSelf: 'start',
  zIndex: 2,
  background: 'linear-gradient(180deg, #fbfdff 0%, #f3f7fb 100%)',
  borderColor: '#d7e2ee',
  boxShadow: '0 10px 24px rgba(15, 23, 42, 0.06)',
};

const DOMAIN_BOARD_PANEL_STYLE = {
  background: 'linear-gradient(180deg, #f8fbff 0%, #f3f7fb 100%)',
  borderColor: '#dbe5f0',
  boxShadow: '0 12px 28px rgba(15, 23, 42, 0.05)',
};

const DOMAIN_CONTENT_CARD_STYLE = {
  background: 'linear-gradient(180deg, #ffffff 0%, #f8fbff 100%)',
  borderColor: '#d8e3ef',
  boxShadow: '0 8px 18px rgba(15, 23, 42, 0.05)',
};

const CONTENT_SECTION_STYLE = {
  border: '1px solid #d8e1ec',
  borderRadius: 10,
  padding: '10px 12px',
  background: '#f6f8fb',
};

const CANDIDATE_SECTION_STYLE = {
  border: '1px solid #ffd591',
  borderRadius: 10,
  padding: '10px 12px',
  background: '#fff7e6',
};

const EDITOR_SECTION_STYLE = {
  border: '1px solid #c9d9ee',
  borderRadius: 10,
  padding: '10px 12px',
  background: '#eef5ff',
};

const CARD_ROW_LIST_STYLE = {
  display: 'grid',
  gap: 10,
};

const CARD_ROW_STYLE = {
  display: 'grid',
  gap: 8,
  gridTemplateColumns: 'minmax(96px, 120px) minmax(0, 1fr)',
  alignItems: 'start',
};

const DATA_EXCHANGE_ITEM_STYLE = {
  border: '1px solid #d8e3ef',
  borderRadius: 10,
  padding: '10px 12px',
  background: '#ffffff',
};

const DATA_EXCHANGE_META_GRID_STYLE = {
  display: 'grid',
  gap: 10,
  gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))',
  marginTop: 8,
};

const SERVICE_TABLE_HEADERS = [
  { key: 'service_name', label: '服务名称' },
  { key: 'transaction_name', label: '交易名称' },
  { key: 'peer_system', label: '对端系统' },
];

const SERVICE_CARD_FIELD_PATH_BY_KEY = {
  provided_capabilities: 'integration_interfaces.canonical.provided_services',
  consumed_capabilities: 'integration_interfaces.canonical.consumed_services',
};

const CARD_HIDDEN_BY_DOMAIN = {
  business_capabilities: ['e2e_processes'],
};

const CAPABILITY_MAP_CARD_KEYS = ['capability_map', 'capability_modules'];
const BUSINESS_SCENARIOS_CARD_KEY = 'business_scenarios';
const CAPABILITY_MAP_MODULE_FIELD_PATH = 'business_capabilities.canonical.functional_modules';
const CAPABILITY_MAP_SCENARIO_FIELD_PATHS = [
  'business_capabilities.canonical.business_scenarios',
  'business_capabilities.canonical.extensions.business_scenarios',
  'business_capabilities.canonical.extensions.feature_context.features',
];
const BUSINESS_SCENARIO_FIELD_PATHS = [
  'business_capabilities.canonical.business_scenarios',
  'business_capabilities.canonical.extensions.business_scenarios',
  'business_capabilities.canonical.extensions.feature_context.features',
];

const V27_SUMMARY_LABELS = {
  system_type: '系统类型',
  system_aliases: '系统别名',
  lifecycle_status: '生命周期状态',
  business_domains: '业务域',
  business_lines: '业务条线',
  application_level: '应用等级',
  core_responsibility: '核心职责',
  status: '状态',
  aliases: '别名',
  business_domain: '业务域',
  architecture_layer: '架构层级',
  target_users: '服务对象',
  service_scope: '职责定位',
  system_boundary: '责任边界',
  related_systems: '关联系统',
  functional_modules: '功能模块',
  business_scenarios: '典型场景',
  business_flows: '业务流程',
  data_reports: '数据报表',
  business_processes: '端到端流程',
  data_assets: '核心数据资产',
  items: '条目',
  architecture_style: '架构形态',
  deployment_mode: '部署方式',
  deployment_environment: '部署环境',
  topology_characteristics: '拓扑特点',
  supplementary_notes: '补充说明',
  tech_stack: '技术栈',
  infrastructure_components: '基础设施/中间件',
  design_methods: '设计方法',
  extensibility_features: '扩展性特征',
  common_capabilities: '通用支撑能力',
  performance_requirements: '性能要求',
  availability_design: '可用性设计',
  monitoring_operations: '监控运维',
  security_requirements: '安全要求',
  network_zone: '网络区域',
  cloud_deployment: '云部署',
  internet_exit: '互联网出口',
  cluster_category: '集群类型',
  virtualization_distribution: '虚拟化分布',
  languages: '语言',
  frameworks: '框架',
  databases: '数据库',
  middleware: '中间件',
  others: '其他',
  online: '在线指标',
  batch: '批处理指标',
  processing_model: '处理模式',
  peak_tps: '峰值 TPS',
  p95_latency_ms: 'P95 延迟(ms)',
  availability_target: '可用性目标',
  window: '处理窗口',
  data_volume: '数据量',
  peak_duration: '峰值耗时',
  batch_window: '批量窗口',
  dual_active: '双活',
  dr_status: '容灾状态',
  dr_site: '容灾站点',
  mlps_level: '等保等级',
  important_system: '重要系统',
  license_certificate_status: '证照状态',
  business_constraints: '业务约束',
  prerequisites: '前提条件',
  sensitive_points: '敏感环节',
  risk_items: '风险事项',
  technical_constraints: '技术约束',
  innovation_stack: '创新栈',
  intellectual_property: '知识产权',
  dr_rto: 'RTO',
  dr_rpo: 'RPO',
  emergency_plan_updated_at: '预案更新时间',
  known_risks: '已知风险',
};

const V27_FIELD_LABELS = {
  'system_positioning.canonical.system_type': '系统类型',
  'system_positioning.canonical.system_aliases': '系统别名',
  'system_positioning.canonical.lifecycle_status': '生命周期状态',
  'system_positioning.canonical.business_domains': '业务域',
  'system_positioning.canonical.business_lines': '业务条线',
  'system_positioning.canonical.extensions.status': '状态',
  'system_positioning.canonical.extensions.aliases': '别名',
  'system_positioning.canonical.business_domain': '业务域',
  'system_positioning.canonical.extensions.business_lines': '业务条线',
  'system_positioning.canonical.architecture_layer': '架构层级',
  'system_positioning.canonical.application_level': '应用等级',
  'system_positioning.canonical.extensions.application_level': '应用级别',
  'system_positioning.canonical.target_users': '服务对象',
  'system_positioning.canonical.core_responsibility': '核心职责',
  'system_positioning.canonical.service_scope': '职责定位',
  'system_positioning.canonical.system_boundary': '责任边界',
  'integration_interfaces.canonical.extensions.catalog_related_systems': '关联系统',
  'business_capabilities.canonical.functional_modules': '功能模块',
  'business_capabilities.canonical.business_scenarios': '典型场景',
  'business_capabilities.canonical.business_flows': '业务流程',
  'business_capabilities.canonical.data_reports': '数据报表',
  'business_capabilities.canonical.extensions.business_scenarios': '关键业务场景',
  'business_capabilities.canonical.extensions.feature_context.features': '业务场景补充',
  'business_capabilities.canonical.business_processes': '端到端流程',
  'business_capabilities.canonical.data_assets': '核心业务对象与数据资产',
  'integration_interfaces.canonical.provided_services': '对外提供能力',
  'integration_interfaces.canonical.consumed_services': '对外依赖能力',
  'integration_interfaces.canonical.other_integrations': '数据交换与批量链路',
  'technical_architecture.canonical.architecture_style': '架构形态',
  'technical_architecture.canonical.extensions.deployment_mode': '部署方式',
  'technical_architecture.canonical.extensions.topology_characteristics': '拓扑特点',
  'technical_architecture.canonical.extensions.architecture_deployment_notes': '补充说明',
  'technical_architecture.canonical.tech_stack': '技术栈',
  'technical_architecture.canonical.extensions.infrastructure_components': '基础设施/中间件',
  'technical_architecture.canonical.extensions.technical_stack_notes': '补充说明',
  'technical_architecture.canonical.extensions.design_methods': '设计方法',
  'technical_architecture.canonical.extensions.extensibility_features': '扩展性特征',
  'technical_architecture.canonical.extensions.common_capabilities': '通用支撑能力',
  'technical_architecture.canonical.extensions.design_characteristics_notes': '补充说明',
  'technical_architecture.canonical.network_zone': '网络区域',
  'technical_architecture.canonical.extensions.cloud_deployment': '云部署',
  'technical_architecture.canonical.extensions.internet_exit': '互联网出口',
  'technical_architecture.canonical.extensions.cluster_category': '集群类型',
  'technical_architecture.canonical.extensions.virtualization_distribution': '虚拟化分布',
  'technical_architecture.canonical.performance_baseline': '性能要求',
  'technical_architecture.canonical.extensions.availability_design': '可用性设计',
  'technical_architecture.canonical.extensions.monitoring_operations': '监控运维',
  'technical_architecture.canonical.extensions.security_requirements': '安全要求',
  'technical_architecture.canonical.extensions.quality_attribute_notes': '补充说明',
  'technical_architecture.canonical.extensions.dual_active': '双活',
  'constraints_risks.canonical.extensions.dr_status': '容灾状态',
  'constraints_risks.canonical.extensions.dr_site': '容灾站点',
  'constraints_risks.canonical.extensions.mlps_level': '等保等级',
  'constraints_risks.canonical.extensions.important_system': '重要系统',
  'constraints_risks.canonical.extensions.license_certificate_status': '证照状态',
  'constraints_risks.canonical.business_constraints': '业务约束',
  'constraints_risks.canonical.prerequisites': '前提条件',
  'constraints_risks.canonical.sensitive_points': '敏感环节',
  'constraints_risks.canonical.risk_items': '风险事项',
  'constraints_risks.canonical.technical_constraints': '技术与资源约束',
  'constraints_risks.canonical.extensions.innovation_stack': '创新栈',
  'constraints_risks.canonical.extensions.intellectual_property': '知识产权',
  'constraints_risks.canonical.extensions.dr_rto': 'RTO',
  'constraints_risks.canonical.extensions.dr_rpo': 'RPO',
  'constraints_risks.canonical.extensions.emergency_plan_updated_at': '应急预案更新时间',
  'constraints_risks.canonical.known_risks': '已知风险与治理事项',
};

const DATA_EXCHANGE_OBJECT_KEYWORDS = [
  '账户',
  '账务',
  '贷款',
  '授信',
  '还款',
  '结清',
  '逾期',
  '余额',
  '状态',
  '流水',
  '信息',
  '放款',
  '计息',
];

const DATA_EXCHANGE_BATCH_KEYWORDS = [
  '实时',
  '批量',
  '日终',
  '日切',
  '跑批',
  '定时',
  '逐笔',
  '接口',
  '同步',
  '异步',
];

const LEGACY_SUGGESTION_FIELD_ALIASES = {
  system_positioning: {
    system_aliases: ['extensions.aliases', 'aliases'],
    lifecycle_status: ['extensions.status', 'status'],
    business_domains: ['business_domain'],
    business_lines: ['extensions.business_lines'],
    application_level: ['extensions.application_level'],
    core_responsibility: ['service_scope', 'system_description'],
  },
  business_capabilities: {
    functional_modules: ['module_structure'],
    business_scenarios: ['extensions.business_scenarios', 'extensions.feature_context.features'],
    business_flows: ['business_processes', 'core_processes'],
    data_reports: ['data_assets'],
  },
  integration_interfaces: {
    other_integrations: ['integration_points'],
  },
  technical_architecture: {
    architecture_style: ['architecture_positioning'],
  },
  constraints_risks: {
    prerequisites: ['technical_constraints', 'key_constraints'],
    risk_items: ['known_risks'],
  },
};

const LEGACY_PROFILE_FIELD_ALIASES = {
  system_positioning: {
    target_users: ['target_users'],
    core_responsibility: ['core_responsibility', 'system_description'],
  },
  business_capabilities: {
    functional_modules: ['functional_modules', 'module_structure'],
    business_flows: ['business_flows', 'core_processes'],
  },
  integration_interfaces: {
    other_integrations: ['other_integrations', 'integration_points', 'external_dependencies'],
  },
  technical_architecture: {
    architecture_style: ['architecture_style', 'architecture_positioning'],
    tech_stack: ['tech_stack'],
    performance_baseline: ['performance_baseline', 'performance_profile'],
  },
  constraints_risks: {
    business_constraints: ['business_constraints', 'key_constraints'],
    risk_items: ['risk_items', 'known_risks'],
  },
};

const LEGACY_FIELD_LABELS = {
  'system_positioning.target_users': '目标用户',
  'system_positioning.core_responsibility': '系统描述',
  'business_capabilities.functional_modules': '模块结构',
  'business_capabilities.business_flows': '核心流程',
  'integration_interfaces.other_integrations': '集成点',
  'constraints_risks.business_constraints': '关键约束',
  'constraints_risks.risk_items': '已知风险',
  'technical_architecture.performance_baseline': '性能画像',
};

const LEGACY_EDITOR_LABELS = {
  'system_positioning.core_responsibility': '系统描述',
  'system_positioning.target_users': '目标用户',
  'business_capabilities.functional_modules': '模块结构',
  'business_capabilities.business_flows': '核心流程',
  'integration_interfaces.other_integrations': '集成点',
  'constraints_risks.business_constraints': '关键约束',
  'constraints_risks.risk_items': '已知风险',
  'technical_architecture.performance_baseline': '性能画像',
};

const getLegacyFieldLabel = (domainKey, field) => (
  LEGACY_FIELD_LABELS[`${domainKey}.${field.key}`] || field.label
);

const getLegacyEditorLabel = (domainKey, field) => (
  LEGACY_EDITOR_LABELS[`${domainKey}.${field.key}`] || getLegacyFieldLabel(domainKey, field)
);

const getLegacyProfileFieldCandidates = (domainKey, fieldKey) => {
  const aliasFields = LEGACY_PROFILE_FIELD_ALIASES[domainKey]?.[fieldKey] || [];
  return [fieldKey, ...aliasFields].filter((item, index, array) => item && array.indexOf(item) === index);
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

const EMPTY_NAMED_ROW = {
  name: '',
  description: '',
};

const EMPTY_DATA_REPORT_ROW = {
  name: '',
  type: 'data',
  description: '',
};

const EMPTY_RISK_ROW = {
  name: '',
  impact: '',
};

const buildEmptyProfileData = () => ({
  system_positioning: {
    canonical: {
      system_type: '',
      system_aliases: [],
      lifecycle_status: '',
      business_domains: [],
      business_lines: [],
      architecture_layer: '',
      application_level: '',
      target_users: [],
      core_responsibility: '',
      extensions: {},
    },
  },
  business_capabilities: {
    canonical: {
      functional_modules: [],
      business_scenarios: [],
      business_flows: [],
      data_reports: [],
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
      business_constraints: [],
      prerequisites: [],
      sensitive_points: [],
      risk_items: [],
      extensions: {},
    },
  },
});

const deepClone = (value) => {
  if (value === undefined) {
    return undefined;
  }
  // 使用 structuredClone（现代浏览器原生支持，比JSON方式快2-3倍）
  if (typeof structuredClone === 'function') {
    try {
      return structuredClone(value);
    } catch (e) {
      // 降级到JSON方式（兼容性fallback）
      console.warn('structuredClone failed, falling back to JSON:', e);
    }
  }
  // 降级方案：JSON序列化（兼容旧浏览器）
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

const normalizeNamedEntries = (value) => {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map((item) => {
      if (typeof item === 'string') {
        return { name: normalizeString(item), description: '' };
      }

      const name = normalizeString(
        item?.name
        || item?.module_name
        || item?.scenario_name
        || item?.title
        || item?.description
      );
      const description = normalizeString(
        item?.description
        || item?.summary
        || item?.desc
        || item?.notes
      );

      if (!name && !description) {
        return null;
      }

      return {
        name: name || description,
        description: name ? description : '',
      };
    })
    .filter((item) => item && (item.name || item.description));
};

const normalizeDataReportEntries = (value) => {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map((item) => {
      if (typeof item === 'string') {
        return {
          name: normalizeString(item),
          type: '',
          description: '',
        };
      }

      const name = normalizeString(item?.name || item?.title || item?.description);
      const type = normalizeString(item?.type).toLowerCase();
      const description = normalizeString(item?.description || item?.summary || item?.notes);

      if (!name && !description) {
        return null;
      }

      return {
        name: name || description,
        type: type === 'report' || type === 'data' ? type : '',
        description: name ? description : '',
      };
    })
    .filter((item) => item && (item.name || item.description));
};

const normalizeRiskEntries = (value) => {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map((item) => {
      if (typeof item === 'string') {
        return { name: normalizeString(item), impact: '' };
      }

      const name = normalizeString(item?.name || item?.title || item?.description || item?.impact);
      const impact = normalizeString(item?.impact || item?.impact_level || item?.notes);

      if (!name && !impact) {
        return null;
      }

      return {
        name: name || impact,
        impact: name ? impact : '',
      };
    })
    .filter((item) => item && (item.name || item.impact));
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

  const legacyEntries = Object.entries(source)
    .filter(([key]) => !['online', 'batch', 'processing_model'].includes(key))
    .map(([metric, metricValue]) => [normalizeString(metric), normalizeString(metricValue)])
    .filter(([, metricValue]) => metricValue);

  if (legacyEntries.length > 0) {
    next.online = Object.fromEntries(legacyEntries);
    return next;
  }

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
      const sourceKey = getLegacyProfileFieldCandidates(domain.key, field.key)
        .find((candidate) => Object.prototype.hasOwnProperty.call(source, candidate));

      if (!sourceKey) {
        return;
      }

      const rawValue = source[sourceKey];

      if (field.type === 'text') {
        template[domain.key].canonical[field.key] = normalizeString(rawValue);
        return;
      }

      if (field.type === 'list') {
        template[domain.key].canonical[field.key] = normalizeStringList(rawValue);
        return;
      }

      if (field.type === 'named_list') {
        template[domain.key].canonical[field.key] = normalizeNamedEntries(rawValue);
        return;
      }

      if (field.type === 'data_report_list') {
        template[domain.key].canonical[field.key] = normalizeDataReportEntries(rawValue);
        return;
      }

      if (field.type === 'risk_list') {
        template[domain.key].canonical[field.key] = normalizeRiskEntries(rawValue);
        return;
      }

      if (field.type === 'service_list') {
        template[domain.key].canonical[field.key] = normalizeServiceEntries(rawValue);
        return;
      }

      if (field.type === 'integration_list') {
        template[domain.key].canonical[field.key] = normalizeIntegrationEntries(rawValue);
        return;
      }

      if (field.type === 'tech_stack') {
        template[domain.key].canonical[field.key] = normalizeTechStack(rawValue);
        return;
      }

      if (field.type === 'performance') {
        template[domain.key].canonical[field.key] = normalizePerformanceBaseline(rawValue);
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

const isRequestCanceled = (error) => (
  error?.code === 'ERR_CANCELED'
  || error?.name === 'CanceledError'
  || error?.name === 'AbortError'
);

const normalizeHealthReport = (value) => {
  if (!value || typeof value !== 'object') {
    return null;
  }

  const coverage = value.coverage && typeof value.coverage === 'object' ? value.coverage : {};
  const latestOutputQuality = value.latest_output_quality && typeof value.latest_output_quality === 'object'
    ? value.latest_output_quality
    : {};

  return {
    system_id: normalizeString(value.system_id),
    system_name: normalizeString(value.system_name),
    coverage: {
      target_field_count: Number(coverage.target_field_count) || 0,
      candidate_field_count: Number(coverage.candidate_field_count) || 0,
      missing_target_fields: Array.isArray(coverage.missing_target_fields) ? coverage.missing_target_fields : [],
      coverage_ratio: Number(coverage.coverage_ratio) || 0,
    },
    low_confidence_candidates: Array.isArray(value.low_confidence_candidates) ? value.low_confidence_candidates : [],
    conflicts: Array.isArray(value.conflicts) ? value.conflicts : [],
    latest_output_quality: {
      line_count: Number(latestOutputQuality.line_count) || 0,
      suggestion_count: Number(latestOutputQuality.suggestion_count) || 0,
      missing_targets: Array.isArray(latestOutputQuality.missing_targets) ? latestOutputQuality.missing_targets : [],
      missing_target_count: Number(latestOutputQuality.missing_target_count) || 0,
      noise_ratio: Number(latestOutputQuality.noise_ratio) || 0,
    },
  };
};

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

const getValueByPath = (payload, path) => {
  const parts = String(path || '').split('.');
  let cursor = payload;
  for (const part of parts) {
    if (!cursor || typeof cursor !== 'object') {
      return undefined;
    }
    cursor = cursor[part];
  }
  return deepClone(cursor);
};

const setValueByPath = (payload, path, value) => {
  const parts = String(path || '').split('.');
  if (parts.length < 2) {
    return payload;
  }

  const next = deepClone(payload);
  let cursor = next;
  parts.slice(0, -1).forEach((part) => {
    if (!cursor[part] || typeof cursor[part] !== 'object' || Array.isArray(cursor[part])) {
      cursor[part] = {};
    }
    cursor = cursor[part];
  });
  cursor[parts[parts.length - 1]] = deepClone(value);
  return next;
};

const getV27FieldLabel = (fieldPath) => {
  const normalizedPath = normalizeString(fieldPath);
  if (!normalizedPath) {
    return '字段';
  }
  if (V27_FIELD_LABELS[normalizedPath]) {
    return V27_FIELD_LABELS[normalizedPath];
  }
  const key = normalizedPath.split('.').slice(-1)[0];
  return V27_SUMMARY_LABELS[key] || key.replace(/_/g, ' ');
};

const formatObjectEntry = (value) => {
  if (!value || typeof value !== 'object') {
    return normalizeString(value);
  }
  const typeLabel = value.type === 'report' ? '报表' : value.type === 'data' ? '数据' : '';
  const candidates = [
    value.name,
    typeLabel,
    value.description,
    value.impact,
    value.service_name,
    value.transaction_name,
    value.peer_system,
    value.exchange_object,
    value.exchange_mode,
    value.notes,
  ]
    .map((item) => normalizeString(item))
    .filter(Boolean);
  if (candidates.length > 0) {
    return candidates.join(' / ');
  }
  return JSON.stringify(value, null, 2);
};

const splitInlineTextTokens = (value) => normalizeString(value)
  .split(/[\n,，、/;；]+/)
  .map((item) => normalizeString(item))
  .filter(Boolean);

const uniqueDisplayValues = (values) => values.filter((item, index, array) => item && array.indexOf(item) === index);

const extractKeywordMentions = (text, keywords) => uniqueDisplayValues(
  keywords.filter((keyword) => normalizeString(text).includes(keyword))
);

const extractSystemMentions = (text) => uniqueDisplayValues(
  (normalizeString(text).match(/[\u4e00-\u9fa5A-Za-z0-9_-]{1,20}(系统|平台|中心|总行)/g) || [])
    .map((item) => normalizeString(item))
    .filter(Boolean)
);

const renderCompactTags = (values, keyPrefix) => {
  if (!Array.isArray(values) || values.length === 0) {
    return <Text type="secondary">—</Text>;
  }
  return (
    <Space wrap size={[6, 6]}>
      {values.map((item, index) => (
        <Tag key={`${keyPrefix}-${index}`}>{item}</Tag>
      ))}
    </Space>
  );
};

const renderCompactValue = (value) => {
  if (!hasMeaningfulValue(value)) {
    return <Text type="secondary">—</Text>;
  }

  if (Array.isArray(value)) {
    if (value.every((item) => typeof item !== 'object' || item === null)) {
      return (
        <Space wrap size={[6, 6]}>
          {value.map((item, index) => (
            <Tag key={`compact-${index}`}>{normalizeString(item)}</Tag>
          ))}
        </Space>
      );
    }
    return (
      <Space direction="vertical" size={4} style={{ width: '100%' }}>
        {value.map((item, index) => (
          <div key={`compact-object-${index}`} style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
            {formatObjectEntry(item)}
          </div>
        ))}
      </Space>
    );
  }

  if (value && typeof value === 'object') {
    return (
      <Space direction="vertical" size={4} style={{ width: '100%' }}>
        {Object.entries(value)
          .filter(([, nested]) => hasMeaningfulValue(nested))
          .map(([key, nested]) => (
            Array.isArray(nested) && nested.every((item) => typeof item !== 'object' || item === null) ? (
              <div key={key} style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
                {`${V27_SUMMARY_LABELS[key] || key}：${normalizeStringList(nested).join('、')}`}
              </div>
            ) : (typeof nested === 'string' || typeof nested === 'number' || typeof nested === 'boolean') ? (
              <div key={key} style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
                {`${V27_SUMMARY_LABELS[key] || key}：${normalizeString(nested)}`}
              </div>
            ) : (
              <div key={key} style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
                <Text strong>{V27_SUMMARY_LABELS[key] || key}</Text>
                <div style={{ marginTop: 4 }}>
                  {renderCompactValue(nested)}
                </div>
              </div>
            )
          ))}
      </Space>
    );
  }

  return <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>{normalizeString(value)}</div>;
};

const buildSummaryRows = (summary) => {
  if (!summary || typeof summary !== 'object') {
    return [];
  }
  return Object.entries(summary)
    .filter(([, value]) => hasMeaningfulValue(value))
    .map(([key, value]) => ({
      key,
      label: V27_SUMMARY_LABELS[key] || key.replace(/_/g, ' '),
      value,
    }));
};

const getVisibleDomainCardKeys = (domainKey, cardKeys) => {
  if (!Array.isArray(cardKeys)) {
    return [];
  }
  const hiddenCardKeys = CARD_HIDDEN_BY_DOMAIN[normalizeString(domainKey)] || [];
  if (!hiddenCardKeys.length) {
    return cardKeys;
  }
  return cardKeys.filter((cardKey) => !hiddenCardKeys.includes(cardKey));
};

const normalizeNamedCardEntries = (value) => {
  if (!Array.isArray(value)) {
    return [];
  }
  if (value.some((item) => item && typeof item === 'object')) {
    return normalizeNamedEntries(value);
  }
  return normalizeStringList(value).map((item) => ({ name: item, description: '' }));
};

const buildCapabilityMapLines = (modules, scenarios) => {
  const normalizedModules = normalizeNamedCardEntries(modules);
  const normalizedScenarios = normalizeNamedCardEntries(scenarios);
  if (!normalizedModules.length && !normalizedScenarios.length) {
    return [];
  }

  const lineCount = Math.max(normalizedModules.length, normalizedScenarios.length);
  const lines = [];
  for (let index = 0; index < lineCount; index += 1) {
    const moduleName = normalizeString(normalizedModules[index]?.name || normalizedModules[index]?.description);
    const moduleDescription = normalizeString(normalizedModules[index]?.description);
    const scenarioText = normalizeString(
      normalizedScenarios[index]?.description
      || normalizedScenarios[index]?.name
      || moduleDescription
    );
    if (moduleName && scenarioText) {
      lines.push(`- ${moduleName}:${scenarioText}`);
      continue;
    }
    if (moduleName) {
      lines.push(`- ${moduleName}`);
      continue;
    }
    if (scenarioText) {
      lines.push(`- ${scenarioText}`);
    }
  }
  return lines;
};

const getCapabilityMapCardLines = (content, summary, profileData, preferDraft = false) => {
  const modules = preferDraft
    ? getValueByPath(profileData, CAPABILITY_MAP_MODULE_FIELD_PATH)
    : (
      (content && Object.prototype.hasOwnProperty.call(content, CAPABILITY_MAP_MODULE_FIELD_PATH)
        ? content[CAPABILITY_MAP_MODULE_FIELD_PATH]
        : undefined)
      ?? summary?.functional_modules
    );

  const scenarios = CAPABILITY_MAP_SCENARIO_FIELD_PATHS
    .map((fieldPath) => (
      preferDraft
        ? getValueByPath(profileData, fieldPath)
        : (
          (content && Object.prototype.hasOwnProperty.call(content, fieldPath) ? content[fieldPath] : undefined)
          ?? summary?.business_scenarios
        )
    ))
    .find((value) => hasMeaningfulValue(value));

  return buildCapabilityMapLines(modules, scenarios);
};

const getBusinessScenarioCardLines = (content, summary, profileData, preferDraft = false) => {
  const scenarios = BUSINESS_SCENARIO_FIELD_PATHS
    .map((fieldPath) => (
      preferDraft
        ? getValueByPath(profileData, fieldPath)
        : (
          (content && Object.prototype.hasOwnProperty.call(content, fieldPath) ? content[fieldPath] : undefined)
          ?? summary?.business_scenarios
        )
    ))
    .find((value) => hasMeaningfulValue(value));

  return normalizeNamedCardEntries(scenarios)
    .map((item) => normalizeString(item.description || item.name))
    .filter(Boolean)
    .map((item) => `- ${item}`);
};

const renderBulletLineList = (lines) => {
  if (!Array.isArray(lines) || lines.length === 0) {
    return <Text type="secondary">暂无已确认内容</Text>;
  }
  return (
    <Space direction="vertical" size={6} style={{ width: '100%' }}>
      {lines.map((line, index) => (
        <div key={`line-${index}`} style={{ whiteSpace: 'pre-wrap', lineHeight: 1.7 }}>
          {line}
        </div>
      ))}
    </Space>
  );
};

const renderCompactSummaryRows = (rows, keyPrefix) => {
  if (!Array.isArray(rows) || rows.length === 0) {
    return <Text type="secondary">暂无已确认内容</Text>;
  }
  return (
    <div style={CARD_ROW_LIST_STYLE}>
      {rows.map((row) => (
        <div key={`${keyPrefix}-${row.key}`} style={CARD_ROW_STYLE}>
          <Text type="secondary" style={{ fontSize: 12, lineHeight: '20px' }}>{row.label}</Text>
          <div>{renderCompactValue(row.value)}</div>
        </div>
      ))}
    </div>
  );
};

const getCardFieldPaths = (content) => (
  content && typeof content === 'object'
    ? Object.keys(content).filter(Boolean)
    : []
);

const buildCardDraftRows = (fieldPaths, profileData) => fieldPaths
  .map((fieldPath) => ({
    key: fieldPath,
    label: getV27FieldLabel(fieldPath),
    value: getValueByPath(profileData, fieldPath),
  }))
  .filter((row) => hasMeaningfulValue(row.value));

const hasCardDraftChanges = (fieldPaths, draftProfileData, savedProfileData) => {
  // 优化：使用简单的深度比较，避免 JSON 序列化
  const isEqual = (a, b) => {
    if (a === b) return true;
    if (a == null || b == null) return false;
    if (typeof a !== typeof b) return false;
    if (typeof a !== 'object') return false;

    if (Array.isArray(a)) {
      if (!Array.isArray(b) || a.length !== b.length) return false;
      return a.every((item, index) => isEqual(item, b[index]));
    }

    const keysA = Object.keys(a);
    const keysB = Object.keys(b);
    if (keysA.length !== keysB.length) return false;

    return keysA.every(key => isEqual(a[key], b[key]));
  };

  return fieldPaths.some((fieldPath) =>
    !isEqual(
      getValueByPath(draftProfileData, fieldPath),
      getValueByPath(savedProfileData, fieldPath)
    )
  );
};

const getServiceCardTableValue = (cardKey, content, summary, profileData, preferDraft = false) => {
  const fieldPath = SERVICE_CARD_FIELD_PATH_BY_KEY[cardKey];
  if (!fieldPath) {
    return null;
  }
  if (preferDraft) {
    return getValueByPath(profileData, fieldPath);
  }
  if (content && Object.prototype.hasOwnProperty.call(content, fieldPath)) {
    return content[fieldPath];
  }
  if (summary && Array.isArray(summary.items)) {
    return summary.items;
  }
  return [];
};

const getDataExchangeCardValue = (content, summary, profileData, preferDraft = false) => {
  const fieldPath = 'integration_interfaces.canonical.other_integrations';
  if (preferDraft) {
    return getValueByPath(profileData, fieldPath);
  }
  if (content && Object.prototype.hasOwnProperty.call(content, fieldPath)) {
    return content[fieldPath];
  }
  if (summary && Array.isArray(summary.items)) {
    return summary.items;
  }
  return [];
};

const buildDataExchangePreviewItems = (items) => {
  if (!Array.isArray(items)) {
    return [];
  }
  return items
    .filter((item) => item && typeof item === 'object')
    .map((item, index) => {
      const noteText = normalizeString(item.notes || item.description);
      const dataObjects = uniqueDisplayValues([
        ...splitInlineTextTokens(item.exchange_object),
        ...splitInlineTextTokens(item.service_name),
        ...splitInlineTextTokens(item.transaction_name),
        ...extractKeywordMentions(noteText, DATA_EXCHANGE_OBJECT_KEYWORDS),
      ]);
      const peerSystems = uniqueDisplayValues([
        '本系统',
        ...splitInlineTextTokens(item.peer_system),
        ...extractSystemMentions(noteText),
      ]);
      const batchSignals = uniqueDisplayValues([
        ...splitInlineTextTokens(item.exchange_mode),
        ...splitInlineTextTokens(item.schedule),
        ...extractKeywordMentions(noteText, DATA_EXCHANGE_BATCH_KEYWORDS),
      ]);
      const title = normalizeString(item.exchange_object)
        || normalizeString(item.service_name)
        || normalizeString(item.transaction_name)
        || normalizeString(noteText.split(/[。；;]/)[0])
        || `链路 ${index + 1}`;
      return {
        key: `${title}-${index}`,
        title,
        dataObjects,
        peerSystems,
        batchSignals,
        notes: noteText,
      };
    })
    .filter((item) => hasMeaningfulValue(item.title) || hasMeaningfulValue(item.notes));
};

const renderDataExchangePreview = (items, keyPrefix) => {
  const previewItems = buildDataExchangePreviewItems(items);
  if (previewItems.length === 0) {
    return <Text type="secondary">暂无链路信息</Text>;
  }
  return (
    <Space direction="vertical" size={8} style={{ width: '100%' }}>
      {previewItems.map((item, index) => (
        <div key={`${keyPrefix}-${item.key}-${index}`} style={DATA_EXCHANGE_ITEM_STYLE}>
          <Text strong>{item.title}</Text>
          <div style={DATA_EXCHANGE_META_GRID_STYLE}>
            <div>
              <Text type="secondary" style={{ fontSize: 12 }}>交互数据</Text>
              <div style={{ marginTop: 6 }}>
                {renderCompactTags(item.dataObjects, `${keyPrefix}-data-${index}`)}
              </div>
            </div>
            <div>
              <Text type="secondary" style={{ fontSize: 12 }}>上下游系统</Text>
              <div style={{ marginTop: 6 }}>
                {renderCompactTags(item.peerSystems, `${keyPrefix}-peers-${index}`)}
              </div>
            </div>
            <div>
              <Text type="secondary" style={{ fontSize: 12 }}>触发与批量关系</Text>
              <div style={{ marginTop: 6 }}>
                {renderCompactTags(item.batchSignals, `${keyPrefix}-batch-${index}`)}
              </div>
            </div>
          </div>
          {hasMeaningfulValue(item.notes) && (
            <div style={{ marginTop: 10 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>链路说明</Text>
              <div style={{ marginTop: 4, whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
                {item.notes}
              </div>
            </div>
          )}
        </div>
      ))}
    </Space>
  );
};

const hasVisibleCardCandidate = (cardKey, candidateCard) => {
  if (!candidateCard || typeof candidateCard !== 'object') {
    return false;
  }
  const summaryRows = buildSummaryRows(candidateCard.summary);
  if (summaryRows.length > 0) {
    return true;
  }
  return hasMeaningfulValue(
    getServiceCardTableValue(cardKey, candidateCard.content, candidateCard.summary, null, false)
  );
};

const countVisibleDomainCandidates = (cardKeys, cardCandidates) => {
  if (!Array.isArray(cardKeys)) {
    return 0;
  }
  return cardKeys.filter((cardKey) => hasVisibleCardCandidate(cardKey, cardCandidates?.[cardKey])).length;
};

const summarizeCardCandidateBadge = (cardKey, candidateCard) => {
  if (!hasVisibleCardCandidate(cardKey, candidateCard)) {
    return null;
  }
  const summaryRows = buildSummaryRows(candidateCard.summary);
  if (summaryRows.length > 0) {
    return <Tag color="orange">候选 {summaryRows.length}</Tag>;
  }
  return <Tag color="orange">候选</Tag>;
};

const serializeCardEditorValue = (value) => {
  if (typeof value === 'string') {
    return value;
  }
  if (Array.isArray(value)) {
    if (value.every((item) => typeof item !== 'object' || item === null)) {
      return value.map((item) => normalizeString(item)).join('\n');
    }
    return JSON.stringify(value, null, 2);
  }
  if (value && typeof value === 'object') {
    return JSON.stringify(value, null, 2);
  }
  return normalizeString(value);
};

const parseCardEditorValue = (text, sampleValue) => {
  if (typeof sampleValue === 'string') {
    return text;
  }
  if (Array.isArray(sampleValue)) {
    if (sampleValue.every((item) => typeof item !== 'object' || item === null)) {
      return normalizeStringList(text);
    }
    return JSON.parse(text || '[]');
  }
  if (sampleValue && typeof sampleValue === 'object') {
    return JSON.parse(text || '{}');
  }
  return text;
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
  if (field.type === 'named_list') {
    return normalizeNamedEntries(value);
  }
  if (field.type === 'data_report_list') {
    return normalizeDataReportEntries(value);
  }
  if (field.type === 'risk_list') {
    return normalizeRiskEntries(value);
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
  const [retryingSuggestions, setRetryingSuggestions] = useState(false);

  const [profileMeta, setProfileMeta] = useState({
    status: 'draft',
    pending_fields: [],
    updated_at: '',
    is_stale: false,
    system_id: '',
    board_version: '',
  });

  const [savedProfileData, setSavedProfileData] = useState(buildEmptyProfileData());
  const [draftProfileData, setDraftProfileData] = useState(buildEmptyProfileData());
  const [editingFields, setEditingFields] = useState({});
  const [profileCards, setProfileCards] = useState({});
  const [cardCandidates, setCardCandidates] = useState({});
  const [domainSummary, setDomainSummary] = useState({});
  const [editingCards, setEditingCards] = useState({});

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
  const [profileHealth, setProfileHealth] = useState(null);
  const mountedRef = useRef(false);
  const requestControllersRef = useRef({
    systems: null,
    profileDetail: null,
    completeness: null,
    timeline: null,
    profileHealth: null,
  });

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

  const abortRequest = useCallback((key) => {
    const controller = requestControllersRef.current[key];
    requestControllersRef.current[key] = null;
    controller?.abort();
  }, []);

  const beginRequest = useCallback((key) => {
    abortRequest(key);
    const controller = new AbortController();
    requestControllersRef.current[key] = controller;
    return controller;
  }, [abortRequest]);

  const finishRequest = useCallback((key, controller) => {
    if (requestControllersRef.current[key] !== controller) {
      return false;
    }
    requestControllersRef.current[key] = null;
    return true;
  }, []);

  const isActiveRequest = useCallback((key, controller) => (
    mountedRef.current && requestControllersRef.current[key] === controller
  ), []);

  const abortAllRequests = useCallback(() => {
    Object.keys(requestControllersRef.current).forEach((key) => {
      abortRequest(key);
    });
  }, [abortRequest]);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      abortAllRequests();
    };
  }, [abortAllRequests]);

  const loadSystems = useCallback(async () => {
    const controller = beginRequest('systems');
    try {
      const response = await axios.get('/api/v1/system/systems', {
        signal: controller.signal,
      });
      if (!isActiveRequest('systems', controller)) {
        return;
      }
      setSystems(Array.isArray(response.data?.data?.systems) ? response.data.data.systems : []);
    } catch (error) {
      if (isRequestCanceled(error) || !isActiveRequest('systems', controller)) {
        return;
      }
      message.error(parseErrorMessage(error, '加载系统清单失败'));
    } finally {
      finishRequest('systems', controller);
    }
  }, [beginRequest, finishRequest, isActiveRequest]);

  const loadCompleteness = useCallback(async (systemName) => {
    if (!systemName) {
      abortRequest('completeness');
      setCompletenessInfo(null);
      setCompletenessUnknown(false);
      return;
    }

    const controller = beginRequest('completeness');
    try {
      setCompletenessUnknown(false);
      const response = await axios.get('/api/v1/system-profiles/completeness', {
        params: { system_name: systemName },
        signal: controller.signal,
      });
      if (!isActiveRequest('completeness', controller)) {
        return;
      }
      setCompletenessInfo(response.data || null);
    } catch (error) {
      if (isRequestCanceled(error) || !isActiveRequest('completeness', controller)) {
        return;
      }
      setCompletenessUnknown(true);
      setCompletenessInfo(null);
    } finally {
      finishRequest('completeness', controller);
    }
  }, [abortRequest, beginRequest, finishRequest, isActiveRequest]);

  const loadTimelinePage = useCallback(async (systemId, offset) => {
    if (!systemId) {
      abortRequest('timeline');
      return { total: 0, items: [] };
    }

    const controller = beginRequest('timeline');
    try {
      const response = await axios.get(`/api/v1/system-profiles/${encodeURIComponent(systemId)}/profile/events`, {
        params: { limit: 20, offset: Math.max(0, Number(offset) || 0) },
        signal: controller.signal,
      });
      if (!isActiveRequest('timeline', controller)) {
        return { total: 0, items: [] };
      }
      const payload = response.data || {};
      return {
        total: Number(payload.total) || 0,
        items: Array.isArray(payload.items) ? payload.items : [],
      };
    } catch (error) {
      if (isRequestCanceled(error) || !isActiveRequest('timeline', controller)) {
        return { total: 0, items: [] };
      }
      message.error(parseErrorMessage(error, '加载时间线失败'));
      return { total: 0, items: [] };
    } finally {
      finishRequest('timeline', controller);
    }
  }, [abortRequest, beginRequest, finishRequest, isActiveRequest]);

  const loadProfileHealth = useCallback(async (systemId) => {
    if (!systemId) {
      abortRequest('profileHealth');
      setProfileHealth(null);
      return null;
    }

    const controller = beginRequest('profileHealth');
    try {
      const response = await axios.get(
        `/api/v1/system-profiles/${encodeURIComponent(systemId)}/profile/health-report`,
        {
          signal: controller.signal,
        }
      );
      if (!isActiveRequest('profileHealth', controller)) {
        return null;
      }
      const normalized = normalizeHealthReport(response.data);
      setProfileHealth(normalized);
      return normalized;
    } catch (_error) {
      if (!isActiveRequest('profileHealth', controller)) {
        return null;
      }
      setProfileHealth(null);
      return null;
    } finally {
      finishRequest('profileHealth', controller);
    }
  }, [abortRequest, beginRequest, finishRequest, isActiveRequest]);

  const applyProfilePayload = useCallback((payload, fallbackSystemId = '') => {
    const normalizedProfileData = normalizeProfileData(payload?.profile_data);

    setSavedProfileData(normalizedProfileData);
    setDraftProfileData(deepClone(normalizedProfileData));
    setEditingFields({});
    setEditingCards({});
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
      board_version: normalizeString(payload?.board_version),
    });
    setProfileCards(payload?.profile_cards && typeof payload.profile_cards === 'object' ? payload.profile_cards : {});
    setCardCandidates(payload?.card_candidates && typeof payload.card_candidates === 'object' ? payload.card_candidates : {});
    setDomainSummary(payload?.domain_summary && typeof payload.domain_summary === 'object' ? payload.domain_summary : {});
  }, []);

  const loadProfileDetail = useCallback(async (systemName, systemIdHint = '') => {
    if (!systemName) {
      return;
    }

    abortRequest('profileDetail');
    abortRequest('timeline');
    abortRequest('completeness');
    abortRequest('profileHealth');
    const controller = beginRequest('profileDetail');
    setLoadingProfile(true);
    try {
      const response = await axios.get(`/api/v1/system-profiles/${encodeURIComponent(systemName)}`, {
        signal: controller.signal,
      });
      if (!isActiveRequest('profileDetail', controller)) {
        return;
      }
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

      if (!isActiveRequest('profileDetail', controller)) {
        return;
      }
      setLoadingProfile(false);
      setTimelineLoading(true);
      const [timeline] = await Promise.all([
        loadTimelinePage(resolvedSystemId, 0),
        loadCompleteness(systemName),
        loadProfileHealth(resolvedSystemId),
      ]);
      if (!isActiveRequest('profileDetail', controller)) {
        return;
      }
      setTimelineItems(timeline.items);
      setTimelineTotal(timeline.total);
      setTimelineLoading(false);
    } catch (error) {
      if (isRequestCanceled(error) || !isActiveRequest('profileDetail', controller)) {
        return;
      }
      message.error(parseErrorMessage(error, '加载系统画像详情失败'));
      setTimelineItems([]);
      setTimelineTotal(0);
      setTimelineLoading(false);
      setProfileHealth(null);
    } finally {
      const isCurrent = finishRequest('profileDetail', controller);
      if (isCurrent && mountedRef.current) {
        setLoadingProfile(false);
      }
    }
  }, [
    abortRequest,
    applyProfilePayload,
    beginRequest,
    finishRequest,
    isActiveRequest,
    loadCompleteness,
    loadProfileHealth,
    loadTimelinePage,
  ]);

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
      abortRequest('profileDetail');
      abortRequest('timeline');
      abortRequest('completeness');
      abortRequest('profileHealth');
      return;
    }
    loadProfileDetail(selectedSystemName, selectedSystem?.id || requestedSystemId);
  }, [abortRequest, loadProfileDetail, requestedSystemId, selectedSystem?.id, selectedSystemName]);

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

  const renderNamedListPreview = (value) => {
    const items = normalizeNamedEntries(value);
    return (
      <Card size="small">
        {items.length > 0 ? (
          <Space direction="vertical" size={8} style={{ width: '100%' }}>
            {items.map((item, index) => (
              <div key={`named-${index}`} style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
                <Text strong>{item.name}</Text>
                {normalizeString(item.description) && <div>{item.description}</div>}
              </div>
            ))}
          </Space>
        ) : (
          <Text type="secondary">—</Text>
        )}
      </Card>
    );
  };

  const renderDataReportPreview = (value) => {
    const rows = normalizeDataReportEntries(value).map((item) => ({
      name: item.name,
      type: item.type === 'report' ? '报表' : item.type === 'data' ? '数据' : '—',
      description: item.description,
    }));

    return (
      <Card size="small">
        <SimpleTable
          headers={[
            { key: 'name', label: '名称' },
            { key: 'type', label: '类型' },
            { key: 'description', label: '说明' },
          ]}
          rows={rows}
        />
      </Card>
    );
  };

  const renderRiskListPreview = (value) => {
    const rows = normalizeRiskEntries(value).map((item) => ({
      name: item.name,
      impact: item.impact,
    }));

    return (
      <Card size="small">
        <SimpleTable
          headers={[
            { key: 'name', label: '风险项' },
            { key: 'impact', label: '影响' },
          ]}
          rows={rows}
        />
      </Card>
    );
  };

const renderServicePreview = (value) => (
  <Card size="small">
    <SimpleTable
      headers={SERVICE_TABLE_HEADERS}
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
    if (field.type === 'named_list') {
      return renderNamedListPreview(value);
    }
    if (field.type === 'data_report_list') {
      return renderDataReportPreview(value);
    }
    if (field.type === 'risk_list') {
      return renderRiskListPreview(value);
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
              placeholder={`请输入${getLegacyEditorLabel(domainKey, field)}`}
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

  const renderNamedListEditor = (domainKey, field, value) => {
    const rows = Array.isArray(value)
      ? value.map((item) => ({ ...EMPTY_NAMED_ROW, ...(item || {}) }))
      : [];
    const visibleRows = rows.length > 0 ? rows : [deepClone(EMPTY_NAMED_ROW)];

    return (
      <Space direction="vertical" size={8} style={{ width: '100%' }}>
        {visibleRows.map((row, index) => (
          <Card key={`${field.key}-${index}`} size="small">
            <Space direction="vertical" size={8} style={{ width: '100%' }}>
              <Input
                value={row.name}
                placeholder={field.key === 'functional_modules' ? '模块名称' : field.key === 'business_constraints' ? '约束类别' : '名称'}
                disabled={!canWrite}
                onChange={(event) => {
                  const next = deepClone(visibleRows);
                  next[index].name = event.target.value;
                  setDraftFieldValue(domainKey, field.key, next);
                }}
              />
              <Input.TextArea
                autoSize={{ minRows: 2, maxRows: 4 }}
                value={row.description}
                placeholder="说明"
                disabled={!canWrite}
                onChange={(event) => {
                  const next = deepClone(visibleRows);
                  next[index].description = event.target.value;
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
          onClick={() => setDraftFieldValue(domainKey, field.key, [...visibleRows, deepClone(EMPTY_NAMED_ROW)])}
        >
          新增一项
        </Button>
      </Space>
    );
  };

  const renderDataReportEditor = (domainKey, field, value) => {
    const rows = Array.isArray(value)
      ? value.map((item) => ({ ...EMPTY_DATA_REPORT_ROW, ...(item || {}) }))
      : [];
    const visibleRows = rows.length > 0 ? rows : [deepClone(EMPTY_DATA_REPORT_ROW)];

    return (
      <Space direction="vertical" size={8} style={{ width: '100%' }}>
        {visibleRows.map((row, index) => (
          <Card key={`${field.key}-${index}`} size="small">
            <Space direction="vertical" size={8} style={{ width: '100%' }}>
              <Space style={{ width: '100%' }} align="start">
                <Input
                  value={row.name}
                  placeholder="名称"
                  disabled={!canWrite}
                  onChange={(event) => {
                    const next = deepClone(visibleRows);
                    next[index].name = event.target.value;
                    setDraftFieldValue(domainKey, field.key, next);
                  }}
                />
                <Input
                  value={row.type}
                  placeholder="类型（data/report）"
                  disabled={!canWrite}
                  onChange={(event) => {
                    const next = deepClone(visibleRows);
                    next[index].type = event.target.value;
                    setDraftFieldValue(domainKey, field.key, next);
                  }}
                />
              </Space>
              <Input.TextArea
                autoSize={{ minRows: 2, maxRows: 4 }}
                value={row.description}
                placeholder="说明"
                disabled={!canWrite}
                onChange={(event) => {
                  const next = deepClone(visibleRows);
                  next[index].description = event.target.value;
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
          onClick={() => setDraftFieldValue(domainKey, field.key, [...visibleRows, deepClone(EMPTY_DATA_REPORT_ROW)])}
        >
          新增一项
        </Button>
      </Space>
    );
  };

  const renderRiskListEditor = (domainKey, field, value) => {
    const rows = Array.isArray(value)
      ? value.map((item) => ({ ...EMPTY_RISK_ROW, ...(item || {}) }))
      : [];
    const visibleRows = rows.length > 0 ? rows : [deepClone(EMPTY_RISK_ROW)];

    return (
      <Space direction="vertical" size={8} style={{ width: '100%' }}>
        {visibleRows.map((row, index) => (
          <Card key={`${field.key}-${index}`} size="small">
            <Space direction="vertical" size={8} style={{ width: '100%' }}>
              <Input
                value={row.name}
                placeholder="风险事项"
                disabled={!canWrite}
                onChange={(event) => {
                  const next = deepClone(visibleRows);
                  next[index].name = event.target.value;
                  setDraftFieldValue(domainKey, field.key, next);
                }}
              />
              <Input.TextArea
                autoSize={{ minRows: 2, maxRows: 4 }}
                value={row.impact}
                placeholder="影响"
                disabled={!canWrite}
                onChange={(event) => {
                  const next = deepClone(visibleRows);
                  next[index].impact = event.target.value;
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
          onClick={() => setDraftFieldValue(domainKey, field.key, [...visibleRows, deepClone(EMPTY_RISK_ROW)])}
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
                    placeholder="指标值"
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
          placeholder={`请输入${getLegacyEditorLabel(domainKey, field)}`}
          onChange={(event) => setDraftFieldValue(domainKey, field.key, event.target.value)}
        />
      );
    }
    if (field.type === 'list') {
      return renderStringListEditor(domainKey, field, value);
    }
    if (field.type === 'named_list') {
      return renderNamedListEditor(domainKey, field, value);
    }
    if (field.type === 'data_report_list') {
      return renderDataReportEditor(domainKey, field, value);
    }
    if (field.type === 'risk_list') {
      return renderRiskListEditor(domainKey, field, value);
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

  const handleRetryAiSuggestions = async () => {
    if (!selectedSystemName) {
      message.warning('请先选择系统');
      return;
    }
    if (!effectiveSystemId) {
      message.error('系统ID缺失，无法执行操作');
      return;
    }
    if (!canWrite) {
      message.warning('当前系统为只读，无法重新生成 AI 建议');
      return;
    }

    try {
      setRetryingSuggestions(true);
      const response = await axios.post(
        `/api/v1/system-profiles/${encodeURIComponent(effectiveSystemId)}/ai-suggestions/retry`
      );
      message.success(response?.data?.message || '已重新生成 AI 建议');
      await loadProfileDetail(selectedSystemName, effectiveSystemId);
    } catch (error) {
      message.error(parseErrorMessage(error, '重新生成 AI 建议失败'));
    } finally {
      setRetryingSuggestions(false);
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

  const isV27CardBoard = profileMeta.board_version === 'cards_v1';

  const v27Domains = useMemo(() => {
    if (!isV27CardBoard) {
      return [];
    }
    return Object.values(domainSummary || {})
      .filter((item) => item && typeof item === 'object')
      .sort((left, right) => DOMAIN_CONFIG.findIndex((item) => item.key === left.domain_key) - DOMAIN_CONFIG.findIndex((item) => item.key === right.domain_key));
  }, [domainSummary, isV27CardBoard]);

  const activeV27Domain = useMemo(() => {
    if (!isV27CardBoard) {
      return null;
    }
    return domainSummary?.[activeDomain] || v27Domains[0] || null;
  }, [activeDomain, domainSummary, isV27CardBoard, v27Domains]);

  const activeV27Cards = useMemo(() => {
    if (!activeV27Domain) {
      return [];
    }
    const cardKeys = getVisibleDomainCardKeys(
      activeV27Domain.domain_key,
      Array.isArray(activeV27Domain.card_keys) ? activeV27Domain.card_keys : []
    );
    return cardKeys
      .map((cardKey) => {
        const candidate = cardCandidates?.[cardKey] || null;
        return {
          current: profileCards?.[cardKey] || {},
          candidate,
          hasVisibleCandidate: hasVisibleCardCandidate(cardKey, candidate),
        };
      })
      .sort((left, right) => Number(right.hasVisibleCandidate) - Number(left.hasVisibleCandidate));
  }, [activeV27Domain, cardCandidates, profileCards]);

  const beginCardEdit = useCallback((cardKey, seedContent) => {
    const content = seedContent && typeof seedContent === 'object' ? seedContent : {};
    const nextValues = {};
    Object.keys(content).forEach((fieldPath) => {
      const currentValue = getValueByPath(draftProfileData, fieldPath);
      nextValues[fieldPath] = serializeCardEditorValue(currentValue !== undefined ? currentValue : content[fieldPath]);
    });
    setEditingCards((previous) => ({ ...previous, [cardKey]: nextValues }));
  }, [draftProfileData]);

  const cancelCardEdit = useCallback((cardKey) => {
    setEditingCards((previous) => {
      const next = { ...previous };
      delete next[cardKey];
      return next;
    });
  }, []);

  const handleCardEditorChange = useCallback((cardKey, fieldPath, text) => {
    setEditingCards((previous) => ({
      ...previous,
      [cardKey]: {
        ...(previous[cardKey] || {}),
        [fieldPath]: text,
      },
    }));
  }, []);

  const applyCardEditDraft = useCallback((cardKey, sampleContent) => {
    const editorValues = editingCards?.[cardKey];
    if (!editorValues) {
      return;
    }

    try {
      let nextProfile = deepClone(draftProfileData);
      Object.entries(editorValues).forEach(([fieldPath, rawText]) => {
        const sampleValue = sampleContent?.[fieldPath];
        const parsedValue = parseCardEditorValue(rawText, sampleValue);
        nextProfile = setValueByPath(nextProfile, fieldPath, parsedValue);
      });
      setDraftProfileData(normalizeProfileData(nextProfile));
      cancelCardEdit(cardKey);
      message.success('卡片编辑已应用到草稿');
    } catch (error) {
      message.error(`卡片编辑格式错误：${error.message || '请检查 JSON / 列表内容'}`);
    }
  }, [cancelCardEdit, draftProfileData, editingCards]);

  const handleAcceptCardCandidate = useCallback(async (cardKey) => {
    if (!effectiveSystemId) {
      message.error('系统ID缺失，无法执行操作');
      return;
    }

    try {
      const response = await axios.post(
        `/api/v1/system-profiles/${encodeURIComponent(effectiveSystemId)}/profile/cards/accept`,
        { card_key: cardKey }
      );
      if (response.data?.data) {
        applyProfilePayload(response.data.data, effectiveSystemId);
      }
      message.success('已采纳卡片候选');
    } catch (error) {
      message.error(parseErrorMessage(error, '采纳卡片候选失败'));
    }
  }, [applyProfilePayload, effectiveSystemId]);

  const handleIgnoreCardCandidate = useCallback(async (cardKey) => {
    if (!effectiveSystemId) {
      message.error('系统ID缺失，无法执行操作');
      return;
    }

    try {
      const response = await axios.post(
        `/api/v1/system-profiles/${encodeURIComponent(effectiveSystemId)}/profile/cards/ignore`,
        { card_key: cardKey }
      );
      if (response.data?.data) {
        applyProfilePayload(response.data.data, effectiveSystemId);
      }
      message.success('已忽略卡片候选');
    } catch (error) {
      message.error(parseErrorMessage(error, '忽略卡片候选失败'));
    }
  }, [applyProfilePayload, effectiveSystemId]);

  const handleRestoreCardBaseline = useCallback(async (cardKey) => {
    if (!effectiveSystemId) {
      message.error('系统ID缺失，无法执行操作');
      return;
    }

    try {
      const response = await axios.post(
        `/api/v1/system-profiles/${encodeURIComponent(effectiveSystemId)}/profile/cards/restore-baseline`,
        { card_key: cardKey }
      );
      if (response.data?.data) {
        applyProfilePayload(response.data.data, effectiveSystemId);
      }
      message.success('已恢复高可信基线');
    } catch (error) {
      message.error(parseErrorMessage(error, '恢复高可信基线失败'));
    }
  }, [applyProfilePayload, effectiveSystemId]);

  const handleResetProfileWorkspace = useCallback(async () => {
    if (!effectiveSystemId) {
      message.error('系统ID缺失，无法执行操作');
      return;
    }

    const confirmed = window.confirm(
      `确认清空 ${selectedSystemName || effectiveSystemId} 的画像数据吗？该操作会删除 source/candidate/profile/audit 产物，且不可恢复。`
    );
    if (!confirmed) {
      return;
    }

    try {
      await axios.post(
        `/api/v1/system-profiles/${encodeURIComponent(effectiveSystemId)}/profile/reset`,
        { reason: 'admin_reset_workspace' }
      );
      await loadProfileDetail(selectedSystemName, effectiveSystemId);
      message.success('已清空该系统的画像数据');
    } catch (error) {
      message.error(parseErrorMessage(error, '清空画像数据失败'));
    }
  }, [effectiveSystemId, loadProfileDetail, selectedSystemName]);

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
  const healthCoveragePercent = Math.round((profileHealth?.coverage?.coverage_ratio || 0) * 100);
  const healthLowConfidenceCount = profileHealth?.low_confidence_candidates?.length || 0;
  const healthConflictCount = profileHealth?.conflicts?.length || 0;
  const healthMissingTargetCount = profileHealth?.latest_output_quality?.missing_target_count
    ?? profileHealth?.coverage?.missing_target_fields?.length
    ?? 0;

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
          <Button
            size="small"
            icon={<ReloadOutlined />}
            aria-label="重新生成 AI 建议"
            loading={retryingSuggestions}
            disabled={!canWrite}
            onClick={handleRetryAiSuggestions}
          >
            重新生成 AI 建议
          </Button>
          {isAdmin && (
            <Button
              size="small"
              danger
              disabled={!effectiveSystemId}
              onClick={handleResetProfileWorkspace}
            >
              清空画像数据
            </Button>
          )}
          <Text type="secondary" style={{ fontSize: 12, marginLeft: 'auto' }}>
            更新：{formatDateTime(profileMeta.updated_at)}
          </Text>
        </div>
      </Space>

      {profileHealth && (
        <Card size="small" title="Wiki 编译健康">
          <Space direction="vertical" size={8} style={{ width: '100%' }}>
            <Space wrap size={[8, 8]}>
              <Tag color="blue">覆盖率 {healthCoveragePercent}%</Tag>
              <Tag>低置信 {healthLowConfidenceCount}</Tag>
              <Tag>冲突 {healthConflictCount}</Tag>
              <Tag>缺失目标 {healthMissingTargetCount}</Tag>
              <Tag>最新建议 {profileHealth.latest_output_quality?.suggestion_count || 0}</Tag>
            </Space>
            <Text type="secondary" style={{ fontSize: 12 }}>
              AI 建议对应最新 wiki 编译候选；评估优先使用 canonical，缺字段时补用高置信 wiki 候选。
            </Text>
            {healthLowConfidenceCount > 0 && (
              <Space direction="vertical" size={4} style={{ width: '100%' }}>
                <Text strong style={{ fontSize: 12 }}>低置信候选</Text>
                {profileHealth.low_confidence_candidates.slice(0, 3).map((item) => (
                  <Text key={`low-${item.field_path}`} type="secondary" style={{ fontSize: 12 }}>
                    {item.field_path} · 置信度 {Math.round((Number(item.confidence) || 0) * 100)}%
                  </Text>
                ))}
              </Space>
            )}
          </Space>
        </Card>
      )}

      <div
        style={{
          display: 'grid',
          gap: 12,
          gridTemplateColumns: timelineExpanded ? '220px minmax(0, 1fr) 320px' : '220px minmax(0, 1fr)',
          alignItems: 'start',
        }}
      >
        <Card size="small" style={DOMAIN_NAV_CARD_STYLE}>
          <Space direction="vertical" size={8} style={{ width: '100%' }}>
            {(isV27CardBoard ? v27Domains : DOMAIN_CONFIG).map((domain) => {
              const domainKey = domain.domain_key || domain.key;
              const domainLabel = domain.title || domain.label;
              const candidateCount = isV27CardBoard
                ? countVisibleDomainCandidates(getVisibleDomainCardKeys(domainKey, domain.card_keys), cardCandidates)
                : (Number(domain.candidate_count) || 0);
              return (
                <Button
                  key={domainKey}
                  type={activeDomain === domainKey ? 'primary' : 'default'}
                  block
                  onClick={() => setActiveDomain(domainKey)}
                  style={{ justifyContent: 'flex-start', textAlign: 'left' }}
                >
                  <Space size={6}>
                    <span>{domainLabel}</span>
                    {isV27CardBoard
                      ? (candidateCount > 0 && <Tag color="orange">候选 {candidateCount}</Tag>)
                      : (domainHasDiff(domainKey) && <Tag color="blue">有建议</Tag>)}
                  </Space>
                </Button>
              );
            })}
          </Space>
        </Card>

        {isV27CardBoard ? (
          <Card style={DOMAIN_BOARD_PANEL_STYLE}>
            <Space direction="vertical" size={12} style={{ width: '100%' }}>
              {loadingProfile && <Text type="secondary">加载中...</Text>}
              <Text type="secondary">
                当前内容展示在上方，候选内容在下方待确认；采纳后先进入草稿，保存后更新画像；高可信基线可随时恢复。
              </Text>

              {activeV27Cards.map(({ current, candidate, hasVisibleCandidate }) => {
                const cardKey = current.card_key || candidate?.card_key;
                const seedContent = current.content && Object.keys(current.content || {}).length > 0
                  ? current.content
                  : candidate?.content || current.baseline_content || {};
                const cardFieldPaths = getCardFieldPaths(seedContent);
                const draftChanged = hasCardDraftChanges(cardFieldPaths, draftProfileData, savedProfileData);
                const currentRows = draftChanged
                  ? buildCardDraftRows(cardFieldPaths, draftProfileData)
                  : buildSummaryRows(current.summary);
                const candidateRows = buildSummaryRows(candidate?.summary);
                const baselineRows = buildSummaryRows(current.baseline_summary);
                const currentCapabilityMapLines = CAPABILITY_MAP_CARD_KEYS.includes(cardKey)
                  ? getCapabilityMapCardLines(current.content, current.summary, draftProfileData, draftChanged)
                  : [];
                const candidateCapabilityMapLines = CAPABILITY_MAP_CARD_KEYS.includes(cardKey)
                  ? getCapabilityMapCardLines(candidate?.content, candidate?.summary, draftProfileData, false)
                  : [];
                const currentBusinessScenarioLines = cardKey === BUSINESS_SCENARIOS_CARD_KEY
                  ? getBusinessScenarioCardLines(current.content, current.summary, draftProfileData, draftChanged)
                  : [];
                const candidateBusinessScenarioLines = cardKey === BUSINESS_SCENARIOS_CARD_KEY
                  ? getBusinessScenarioCardLines(candidate?.content, candidate?.summary, draftProfileData, false)
                  : [];
                const editorValues = editingCards?.[cardKey];
                const showMetadataRow = baselineRows.length > 0;
                const currentServiceTableValue = getServiceCardTableValue(
                  cardKey,
                  current.content,
                  current.summary,
                  draftProfileData,
                  draftChanged
                );
                const candidateServiceTableValue = getServiceCardTableValue(
                  cardKey,
                  candidate?.content,
                  candidate?.summary,
                  draftProfileData,
                  false
                );
                const currentDataExchangeValue = cardKey === 'data_exchange_batch_links'
                  ? getDataExchangeCardValue(current.content, current.summary, draftProfileData, draftChanged)
                  : null;
                const candidateDataExchangeValue = cardKey === 'data_exchange_batch_links'
                  ? getDataExchangeCardValue(candidate?.content, candidate?.summary, draftProfileData, false)
                  : null;

                return (
                  <Card
                    key={cardKey}
                    size="small"
                    title={current.title || candidate?.title || cardKey}
                    extra={summarizeCardCandidateBadge(cardKey, candidate)}
                    style={DOMAIN_CONTENT_CARD_STYLE}
                  >
                    <Space direction="vertical" size={8} style={{ width: '100%' }}>
                      {showMetadataRow && (
                        <Space wrap size={[6, 6]}>
                          {baselineRows.length > 0 && <Tag color="green">可恢复基线</Tag>}
                        </Space>
                      )}

                      <div data-testid={`card-current-section-${cardKey}`} style={CONTENT_SECTION_STYLE}>
                        <Space direction="vertical" size={8} style={{ width: '100%' }}>
                          {currentCapabilityMapLines.length > 0 ? (
                            renderBulletLineList(currentCapabilityMapLines)
                          ) : currentBusinessScenarioLines.length > 0 ? (
                            renderBulletLineList(currentBusinessScenarioLines)
                          ) : currentServiceTableValue ? (
                            <SimpleTable
                              headers={SERVICE_TABLE_HEADERS}
                              rows={buildServicePreviewRows(currentServiceTableValue)}
                            />
                          ) : currentDataExchangeValue ? (
                            renderDataExchangePreview(currentDataExchangeValue, `${cardKey}-current`)
                          ) : renderCompactSummaryRows(currentRows, `${cardKey}-current`)}
                        </Space>
                      </div>

                      {hasVisibleCandidate && (
                        <div data-testid={`card-candidate-section-${cardKey}`} style={CANDIDATE_SECTION_STYLE}>
                          <Space direction="vertical" size={8} style={{ width: '100%' }}>
                            <Text strong>候选内容</Text>
                            {candidateCapabilityMapLines.length > 0 ? (
                              renderBulletLineList(candidateCapabilityMapLines)
                            ) : candidateBusinessScenarioLines.length > 0 ? (
                              renderBulletLineList(candidateBusinessScenarioLines)
                            ) : candidateServiceTableValue ? (
                              <SimpleTable
                                headers={SERVICE_TABLE_HEADERS}
                                rows={buildServicePreviewRows(candidateServiceTableValue)}
                              />
                            ) : candidateDataExchangeValue ? (
                              renderDataExchangePreview(candidateDataExchangeValue, `${cardKey}-candidate`)
                            ) : candidateRows.map((row) => (
                              <React.Fragment key={`${cardKey}-candidate-${row.key}`}>
                                {renderCompactSummaryRows([row], `${cardKey}-candidate-row`)}
                              </React.Fragment>
                            ))}
                            <Space wrap>
                              <Button
                                size="small"
                                type="primary"
                                disabled={!canWrite}
                                onClick={() => handleAcceptCardCandidate(cardKey)}
                              >
                                采纳候选
                              </Button>
                              <Button
                                size="small"
                                disabled={!canWrite}
                                onClick={() => handleIgnoreCardCandidate(cardKey)}
                              >
                                忽略候选
                              </Button>
                            </Space>
                          </Space>
                        </div>
                      )}

                      {editorValues ? (
                        <div style={EDITOR_SECTION_STYLE}>
                          <Space direction="vertical" size={8} style={{ width: '100%' }}>
                            <Text strong>编辑卡片草稿</Text>
                            {Object.entries(editorValues).map(([fieldPath, textValue]) => (
                              <div key={`${cardKey}-${fieldPath}`}>
                                <Text type="secondary">{getV27FieldLabel(fieldPath)}</Text>
                                <Input.TextArea
                                  style={{ marginTop: 6 }}
                                  rows={Array.isArray(seedContent?.[fieldPath]) || (seedContent?.[fieldPath] && typeof seedContent?.[fieldPath] === 'object') ? 5 : 3}
                                  value={textValue}
                                  disabled={!canWrite}
                                  onChange={(event) => handleCardEditorChange(cardKey, fieldPath, event.target.value)}
                                />
                              </div>
                            ))}
                            <Space wrap>
                              <Button
                                size="small"
                                type="primary"
                                disabled={!canWrite}
                                onClick={() => applyCardEditDraft(cardKey, seedContent)}
                              >
                                应用到草稿
                              </Button>
                              <Button size="small" onClick={() => cancelCardEdit(cardKey)}>
                                取消
                              </Button>
                            </Space>
                          </Space>
                        </div>
                      ) : (
                        <Space wrap>
                          <Button
                            size="small"
                            disabled={!canWrite}
                            onClick={() => beginCardEdit(cardKey, seedContent)}
                          >
                            编辑卡片
                          </Button>
                          <Button
                            size="small"
                            disabled={!canWrite || baselineRows.length === 0}
                            onClick={() => handleRestoreCardBaseline(cardKey)}
                          >
                            恢复高可信基线
                          </Button>
                        </Space>
                      )}
                    </Space>
                  </Card>
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
            </Space>
          </Card>
        ) : (
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
                      <Text strong>{getLegacyFieldLabel(activeDomainConfig.key, field)}</Text>
                      {canWrite && (
                        <Button
                          size="small"
                          type="link"
                          aria-label={`${editing ? '收起编辑' : '编辑'}${getLegacyEditorLabel(activeDomainConfig.key, field)}`}
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
        )}

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
