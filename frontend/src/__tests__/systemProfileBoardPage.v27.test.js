import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import '@testing-library/jest-dom';
import { message } from 'antd';
import SystemProfileBoardPage from '../pages/SystemProfileBoardPage';

jest.setTimeout(60000);

jest.mock('axios', () => ({
  get: jest.fn(),
  put: jest.fn(),
  post: jest.fn(),
}));
const axios = require('axios');

jest.mock('../hooks/useAuth', () => () => ({
  user: {
    id: 'u_pm1',
    username: 'pm1',
    displayName: '项目经理1',
    roles: ['manager'],
  },
}));

jest.mock('../hooks/usePermission', () => () => ({
  ...mockPermissionState,
}));

let mockPermissionState = {
  isManager: true,
  isAdmin: false,
  isExpert: false,
};

const createMatchMediaResult = (query) => ({
  matches: false,
  media: query,
  onchange: null,
  addListener: () => {},
  removeListener: () => {},
  addEventListener: () => {},
  removeEventListener: () => {},
  dispatchEvent: () => false,
});

const deepClone = (value) => JSON.parse(JSON.stringify(value));

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

const getSuggestionCandidates = (domainKey, fieldKey) => {
  const aliases = LEGACY_SUGGESTION_FIELD_ALIASES[domainKey]?.[fieldKey] || [];
  return [fieldKey, ...aliases].filter((item, index, array) => item && array.indexOf(item) === index);
};

const getMockSuggestionValue = (payload, domainKey, fieldKey) => {
  const candidates = getSuggestionCandidates(domainKey, fieldKey);
  for (const candidate of candidates) {
    const flatFieldPath = `${domainKey}.canonical.${candidate}`;
    if (Object.prototype.hasOwnProperty.call(payload, flatFieldPath)) {
      return deepClone(payload[flatFieldPath]?.value ?? payload[flatFieldPath]);
    }
  }

  const domainPayload = payload[domainKey];
  if (!domainPayload || typeof domainPayload !== 'object') {
    return undefined;
  }
  const canonicalPayload = domainPayload.canonical;
  if (canonicalPayload && typeof canonicalPayload === 'object') {
    for (const candidate of candidates) {
      if (Object.prototype.hasOwnProperty.call(canonicalPayload, candidate)) {
        return deepClone(canonicalPayload[candidate]?.value ?? canonicalPayload[candidate]);
      }
    }
  }
  for (const candidate of candidates) {
    if (Object.prototype.hasOwnProperty.call(domainPayload, candidate)) {
      return deepClone(domainPayload[candidate]?.value ?? domainPayload[candidate]);
    }
  }
  return undefined;
};

const removeMockSuggestionValue = (payload, domainKey, fieldKey) => {
  const next = deepClone(payload);
  const candidates = getSuggestionCandidates(domainKey, fieldKey);

  candidates.forEach((candidate) => {
    delete next[`${domainKey}.canonical.${candidate}`];
    if (next[domainKey] && typeof next[domainKey] === 'object') {
      if (next[domainKey].canonical && typeof next[domainKey].canonical === 'object') {
        delete next[domainKey].canonical[candidate];
      }
      delete next[domainKey][candidate];
    }
  });

  return next;
};

const baseProfilePayload = {
  system_id: 'SYS-PAY',
  status: 'draft',
  updated_at: '2026-03-13T12:00:00',
  pending_fields: [],
  profile_data: {
    system_positioning: {
      canonical: {
        system_type: '核心业务系统',
        system_aliases: ['PAY'],
        lifecycle_status: '生产运行',
        business_domains: ['支付'],
        business_lines: ['支付结算'],
        architecture_layer: '应用层',
        application_level: '重要系统',
        target_users: ['运营人员'],
        core_responsibility: '统一支付受理',
        extensions: {
          related_systems: ['CRM'],
        },
      },
    },
    business_capabilities: {
      canonical: {
        functional_modules: [{ name: '支付路由', description: '统一路由支付请求。' }],
        business_scenarios: [{ name: '柜面支付', description: '柜面发起支付并返回处理结果。' }],
        business_flows: [{ name: '支付处理', description: '受理、校验、路由、结果返回。' }],
        data_reports: [{ name: '交易记录', type: 'data', description: '沉淀支付明细数据。' }],
        extensions: {},
      },
    },
    integration_interfaces: {
      canonical: {
        provided_services: [
          { service_name: '支付路由服务', transaction_name: '支付查询交易', scenario_code: 'SC001', peer_system: '核心账务', status: '正常使用' },
          { service_name: '支付路由服务', transaction_name: '支付查询交易', scenario_code: 'SC001', peer_system: '清算平台', status: '正常使用' },
        ],
        consumed_services: [
          { service_name: '客户中心服务', transaction_name: '客户查询交易', scenario_code: 'SC002', peer_system: '客户中心', status: '正常使用' },
        ],
        other_integrations: [],
        extensions: {},
      },
    },
    technical_architecture: {
      canonical: {
        architecture_style: '分层架构',
        tech_stack: {
          languages: ['Java'],
          frameworks: ['Spring Boot'],
          databases: ['MySQL'],
          middleware: [],
          others: ['Redis'],
        },
        network_zone: '内网区',
        performance_baseline: {
          online: { peak_tps: '200', p95_latency_ms: '80', availability_target: '99.9%' },
          batch: { window: '', data_volume: '', peak_duration: '' },
          processing_model: '在线',
        },
        extensions: {
          code_structure: { node_count: 10 },
        },
      },
    },
    constraints_risks: {
      canonical: {
        business_constraints: [{ name: '清算窗口限制', description: '必须在清算窗口内完成对账。' }],
        prerequisites: [{ name: '数据库国产化', description: '运行环境要求国产数据库。' }],
        sensitive_points: [{ name: '路由规则', description: '规则变更会直接影响交易去向。' }],
        risk_items: [{ name: '外部通道抖动', impact: '影响支付成功率。' }],
        extensions: {},
      },
    },
  },
  field_sources: {
    'system_positioning.canonical.core_responsibility': {
      source: 'manual',
      actor: '项目经理1',
    },
  },
  ai_suggestions: {},
  ai_suggestions_previous: null,
  ai_suggestion_ignored: {},
};

const buildCardsV1Payload = () => {
  const payload = deepClone(baseProfilePayload);
  payload.board_version = 'cards_v1';
  payload.profile_cards = {
    system_identity: {
      card_key: 'system_identity',
      domain_key: 'system_positioning',
      title: '系统身份',
      summary: {
        system_type: '核心业务系统',
      },
      content: {
        'system_positioning.canonical.system_type': '核心业务系统',
      },
      source_summary: '人工确认内容',
      edited: false,
      baseline_content: {
        'system_positioning.canonical.system_type': '核心业务系统',
      },
      baseline_summary: {
        system_type: '核心业务系统',
      },
    },
    business_affiliation: {
      card_key: 'business_affiliation',
      domain_key: 'system_positioning',
      title: '业务归属',
      summary: {
        business_domain: ['支付'],
        architecture_layer: '应用层',
      },
      content: {
        'system_positioning.canonical.business_domain': ['支付'],
        'system_positioning.canonical.architecture_layer': '应用层',
      },
      source_summary: '人工确认内容',
      edited: false,
      baseline_content: {},
      baseline_summary: {},
    },
    service_positioning: {
      card_key: 'service_positioning',
      domain_key: 'system_positioning',
      title: '服务定位',
      summary: {
        target_users: ['运营人员'],
        core_responsibility: '统一支付受理',
      },
      content: {
        'system_positioning.canonical.target_users': ['运营人员'],
        'system_positioning.canonical.core_responsibility': '统一支付受理',
      },
      source_summary: '人工确认内容',
      edited: false,
      baseline_content: {},
      baseline_summary: {},
    },
    boundary_ecosystem: {
      card_key: 'boundary_ecosystem',
      domain_key: 'system_positioning',
      title: '责任边界与生态位置',
      summary: {
        system_boundary: ['不处理账务总账'],
        related_systems: ['CRM'],
      },
      content: {
        'system_positioning.canonical.system_boundary': ['不处理账务总账'],
        'integration_interfaces.canonical.extensions.catalog_related_systems': ['CRM'],
      },
      source_summary: '人工确认内容',
      edited: false,
      baseline_content: {},
      baseline_summary: {},
    },
    provided_capabilities: {
      card_key: 'provided_capabilities',
      domain_key: 'integration_interfaces',
      title: '对外提供能力',
      summary: {
        items: [
          { service_name: '支付路由服务', transaction_name: '支付查询交易', peer_system: '核心账务' },
        ],
      },
      content: {
        'integration_interfaces.canonical.provided_services': [
          { service_name: '支付路由服务', transaction_name: '支付查询交易', peer_system: '核心账务' },
        ],
      },
      source_summary: '高可信基础资料',
      edited: false,
      baseline_content: {
        'integration_interfaces.canonical.provided_services': [
          { service_name: '支付路由服务', transaction_name: '支付查询交易', peer_system: '核心账务' },
        ],
      },
      baseline_summary: {
        items: [
          { service_name: '支付路由服务', transaction_name: '支付查询交易', peer_system: '核心账务' },
        ],
      },
    },
    consumed_capabilities: {
      card_key: 'consumed_capabilities',
      domain_key: 'integration_interfaces',
      title: '对外依赖能力',
      summary: {
        items: [
          { service_name: '客户中心服务', transaction_name: '客户查询交易', peer_system: '客户中心' },
        ],
      },
      content: {
        'integration_interfaces.canonical.consumed_services': [
          { service_name: '客户中心服务', transaction_name: '客户查询交易', peer_system: '客户中心' },
        ],
      },
      source_summary: '人工确认内容',
      edited: false,
      baseline_content: {},
      baseline_summary: {},
    },
    data_exchange_batch_links: {
      card_key: 'data_exchange_batch_links',
      domain_key: 'integration_interfaces',
      title: '数据交换与批量链路',
      summary: {
        items: [],
      },
      content: {
        'integration_interfaces.canonical.other_integrations': [],
      },
      source_summary: '人工确认内容',
      edited: false,
      baseline_content: {},
      baseline_summary: {},
    },
  };
  payload.card_candidates = {
    system_identity: {
      card_key: 'system_identity',
      domain_key: 'system_positioning',
      title: '系统身份',
      summary: {
        status: '运行中',
        aliases: ['UPAY'],
      },
      content: {
        'system_positioning.canonical.extensions.status': '运行中',
        'system_positioning.canonical.extensions.aliases': ['UPAY'],
      },
    },
  };
  payload.domain_summary = {
    system_positioning: {
      domain_key: 'system_positioning',
      title: 'D1 系统定位',
      card_count: 4,
      candidate_count: 1,
      card_keys: ['system_identity', 'business_affiliation', 'service_positioning', 'boundary_ecosystem'],
    },
    business_capabilities: {
      domain_key: 'business_capabilities',
      title: 'D2 业务能力',
      card_count: 4,
      candidate_count: 0,
      card_keys: [],
    },
    integration_interfaces: {
      domain_key: 'integration_interfaces',
      title: 'D3 系统交互',
      card_count: 3,
      candidate_count: 0,
      card_keys: ['provided_capabilities', 'consumed_capabilities', 'data_exchange_batch_links'],
    },
    technical_architecture: {
      domain_key: 'technical_architecture',
      title: 'D4 技术架构',
      card_count: 4,
      candidate_count: 0,
      card_keys: [],
    },
    constraints_risks: {
      domain_key: 'constraints_risks',
      title: 'D5 风险约束',
      card_count: 5,
      candidate_count: 0,
      card_keys: [],
    },
  };
  return payload;
};

const buildRedesignedCardsV1Payload = () => ({
  ...deepClone(baseProfilePayload),
  board_version: 'cards_v1',
  domain_summary: {
    system_positioning: {
      domain_key: 'system_positioning',
      title: 'D1 系统定位',
      card_keys: ['system_identity', 'business_affiliation', 'application_hierarchy', 'service_positioning'],
    },
    business_capabilities: {
      domain_key: 'business_capabilities',
      title: 'D2 业务能力',
      card_keys: ['capability_modules', 'business_scenarios', 'business_flows', 'data_reports'],
    },
    integration_interfaces: {
      domain_key: 'integration_interfaces',
      title: 'D3 系统交互',
      card_keys: ['provided_capabilities', 'consumed_capabilities', 'data_exchange_batch_links'],
    },
    technical_architecture: {
      domain_key: 'technical_architecture',
      title: 'D4 技术架构',
      card_keys: ['architecture_deployment', 'tech_stack_infrastructure', 'design_characteristics', 'quality_attributes'],
    },
    constraints_risks: {
      domain_key: 'constraints_risks',
      title: 'D5 风险约束',
      card_keys: ['business_constraints', 'prerequisites', 'sensitive_points', 'risk_items'],
    },
  },
  profile_cards: {
    system_identity: {
      card_key: 'system_identity',
      domain_key: 'system_positioning',
      title: '系统身份',
      summary: { system_type: '核心业务系统', lifecycle_status: '生产运行', system_aliases: ['PAY'] },
      content: {
        'system_positioning.canonical.system_type': '核心业务系统',
        'system_positioning.canonical.lifecycle_status': '生产运行',
        'system_positioning.canonical.system_aliases': ['PAY'],
      },
    },
    business_affiliation: {
      card_key: 'business_affiliation',
      domain_key: 'system_positioning',
      title: '业务归属',
      summary: { business_domains: ['支付'], business_lines: ['支付结算'] },
      content: {
        'system_positioning.canonical.business_domains': ['支付'],
        'system_positioning.canonical.business_lines': ['支付结算'],
      },
    },
    application_hierarchy: {
      card_key: 'application_hierarchy',
      domain_key: 'system_positioning',
      title: '应用层级',
      summary: { architecture_layer: '业务应用层', application_level: '重要系统' },
      content: {
        'system_positioning.canonical.architecture_layer': '业务应用层',
        'system_positioning.canonical.application_level': '重要系统',
      },
    },
    service_positioning: {
      card_key: 'service_positioning',
      domain_key: 'system_positioning',
      title: '服务定位',
      summary: { target_users: ['运营'], core_responsibility: '统一支付受理与路由分发。' },
      content: {
        'system_positioning.canonical.target_users': ['运营'],
        'system_positioning.canonical.core_responsibility': '统一支付受理与路由分发。',
      },
    },
    capability_modules: {
      card_key: 'capability_modules',
      domain_key: 'business_capabilities',
      title: '功能模块',
      summary: {
        functional_modules: [
          { name: '支付路由', description: '统一路由交易请求。' },
          { name: '渠道接入', description: '接入多渠道支付请求。' },
        ],
      },
      content: {
        'business_capabilities.canonical.functional_modules': [
          { name: '支付路由', description: '统一路由交易请求。' },
          { name: '渠道接入', description: '接入多渠道支付请求。' },
        ],
      },
    },
    business_scenarios: {
      card_key: 'business_scenarios',
      domain_key: 'business_capabilities',
      title: '典型场景',
      summary: {
        business_scenarios: [{ name: '柜面支付', description: '柜面发起支付并返回结果。' }],
      },
      content: {
        'business_capabilities.canonical.business_scenarios': [{ name: '柜面支付', description: '柜面发起支付并返回结果。' }],
      },
    },
    business_flows: {
      card_key: 'business_flows',
      domain_key: 'business_capabilities',
      title: '业务流程',
      summary: {
        business_flows: [{ name: '支付处理流程', description: '受理、校验、路由、记账通知。' }],
      },
      content: {
        'business_capabilities.canonical.business_flows': [{ name: '支付处理流程', description: '受理、校验、路由、记账通知。' }],
      },
    },
    data_reports: {
      card_key: 'data_reports',
      domain_key: 'business_capabilities',
      title: '数据报表',
      summary: {
        data_reports: [
          { name: '支付流水', type: 'data', description: '记录支付明细。' },
          { name: '清算日报', type: 'report', description: '输出清算结果。' },
        ],
      },
      content: {
        'business_capabilities.canonical.data_reports': [
          { name: '支付流水', type: 'data', description: '记录支付明细。' },
          { name: '清算日报', type: 'report', description: '输出清算结果。' },
        ],
      },
    },
    business_constraints: {
      card_key: 'business_constraints',
      domain_key: 'constraints_risks',
      title: '业务约束',
      summary: {
        business_constraints: [{ name: '清算窗口', description: '需在清算前完成支付汇总。' }],
      },
      content: {
        'constraints_risks.canonical.business_constraints': [{ name: '清算窗口', description: '需在清算前完成支付汇总。' }],
      },
    },
    prerequisites: {
      card_key: 'prerequisites',
      domain_key: 'constraints_risks',
      title: '前提条件',
      summary: {
        prerequisites: [{ name: '渠道参数', description: '渠道签约和参数配置必须先完成。' }],
      },
      content: {
        'constraints_risks.canonical.prerequisites': [{ name: '渠道参数', description: '渠道签约和参数配置必须先完成。' }],
      },
    },
    sensitive_points: {
      card_key: 'sensitive_points',
      domain_key: 'constraints_risks',
      title: '敏感环节',
      summary: {
        sensitive_points: [{ name: '路由规则', description: '规则调整会直接影响交易去向。' }],
      },
      content: {
        'constraints_risks.canonical.sensitive_points': [{ name: '路由规则', description: '规则调整会直接影响交易去向。' }],
      },
    },
    risk_items: {
      card_key: 'risk_items',
      domain_key: 'constraints_risks',
      title: '风险事项',
      summary: {
        risk_items: [{ name: '外部通道抖动', impact: '影响支付成功率。' }],
      },
      content: {
        'constraints_risks.canonical.risk_items': [{ name: '外部通道抖动', impact: '影响支付成功率。' }],
      },
    },
  },
  card_candidates: {},
});

const buildBusinessCapabilityCardsV1Payload = () => {
  const payload = buildCardsV1Payload();
  const functionalModules = ['产品工厂', '贷款开户'];
  const businessScenarios = [
    '灵活新建和复制现有贷款产品，并对贷款基本信息进行维护。',
    '支持一般、特殊等各种类型的贷款开户操作。',
  ];
  const businessProcesses = ['产品配置到贷款开户', '放款计息到日终批量处理'];
  const dataAssets = ['贷款产品', '贷款账户', '还款计划'];

  payload.profile_data.business_capabilities.canonical = {
    ...payload.profile_data.business_capabilities.canonical,
    functional_modules: functionalModules,
    business_processes: businessProcesses,
    data_assets: dataAssets,
    extensions: {
      business_scenarios: businessScenarios,
      feature_context: {
        features: businessScenarios,
      },
    },
  };

  payload.profile_cards = {
    ...payload.profile_cards,
    capability_map: {
      card_key: 'capability_map',
      domain_key: 'business_capabilities',
      title: '能力地图',
      summary: {
        functional_modules: functionalModules,
      },
      content: {
        'business_capabilities.canonical.functional_modules': functionalModules,
        'business_capabilities.canonical.extensions.business_scenarios': businessScenarios,
      },
      source_summary: '人工确认内容',
      edited: false,
      baseline_content: {},
      baseline_summary: {},
    },
    business_scenarios: {
      card_key: 'business_scenarios',
      domain_key: 'business_capabilities',
      title: '关键业务场景',
      summary: {
        business_scenarios: businessScenarios,
      },
      content: {
        'business_capabilities.canonical.extensions.business_scenarios': businessScenarios,
      },
      source_summary: '人工确认内容',
      edited: false,
      baseline_content: {},
      baseline_summary: {},
    },
    e2e_processes: {
      card_key: 'e2e_processes',
      domain_key: 'business_capabilities',
      title: '端到端流程',
      summary: {
        business_processes: businessProcesses,
      },
      content: {
        'business_capabilities.canonical.business_processes': businessProcesses,
      },
      source_summary: '人工确认内容',
      edited: false,
      baseline_content: {},
      baseline_summary: {},
    },
    business_objects_assets: {
      card_key: 'business_objects_assets',
      domain_key: 'business_capabilities',
      title: '核心数据资产',
      summary: {
        data_assets: dataAssets,
      },
      content: {
        'business_capabilities.canonical.data_assets': dataAssets,
      },
      source_summary: '人工确认内容',
      edited: false,
      baseline_content: {},
      baseline_summary: {},
    },
  };
  payload.domain_summary.business_capabilities = {
    ...payload.domain_summary.business_capabilities,
    card_count: 4,
    card_keys: ['capability_map', 'business_scenarios', 'e2e_processes', 'business_objects_assets'],
  };
  return payload;
};

const buildTechnicalArchitectureCardsV1Payload = () => {
  const payload = buildCardsV1Payload();

  payload.profile_data.technical_architecture.canonical = {
    ...payload.profile_data.technical_architecture.canonical,
    architecture_style: '分布式微服务架构',
    network_zone: '生产内网区',
    tech_stack: {
      languages: ['Java'],
      frameworks: ['Spring Boot'],
      databases: ['MySQL'],
      middleware: ['Redis'],
      others: ['Docker'],
    },
    performance_baseline: {
      online: { peak_tps: '200 TPS', p95_latency_ms: '80', availability_target: '99.99%' },
      batch: { window: '日终 30 分钟', data_volume: '', peak_duration: '' },
      processing_model: '',
    },
    extensions: {
      deployment_mode: '云上分布式集群部署',
      topology_characteristics: ['应用节点互备', '数据库一主多从'],
      architecture_deployment_notes: '支持按业务量横向扩容。',
      infrastructure_components: ['服务注册中心', '配置中心', '数据库连接池'],
      design_methods: ['组件化设计', '插件化扩展'],
      extensibility_features: ['参数可配置化', '支持灵活扩展'],
      common_capabilities: ['日志', '权限控制', '订阅发布'],
      availability_design: ['应用节点互备', '自动故障切换'],
      monitoring_operations: ['服务监控', '异常诊断', '资源监控'],
      security_requirements: ['等保三级', '敏感数据传输加密'],
    },
  };

  payload.profile_cards = {
    ...payload.profile_cards,
    architecture_deployment: {
      card_key: 'architecture_deployment',
      domain_key: 'technical_architecture',
      title: '架构与部署方式',
      summary: {
        architecture_style: '分布式微服务架构',
        deployment_mode: '云上分布式集群部署',
        deployment_environment: '网络区域：生产内网区',
        topology_characteristics: ['应用节点互备', '数据库一主多从'],
        supplementary_notes: '支持按业务量横向扩容。',
      },
      content: {
        'technical_architecture.canonical.architecture_style': '分布式微服务架构',
        'technical_architecture.canonical.extensions.deployment_mode': '云上分布式集群部署',
        'technical_architecture.canonical.network_zone': '生产内网区',
        'technical_architecture.canonical.extensions.topology_characteristics': ['应用节点互备', '数据库一主多从'],
        'technical_architecture.canonical.extensions.architecture_deployment_notes': '支持按业务量横向扩容。',
      },
      source_summary: '人工确认内容',
      edited: false,
      baseline_content: {},
      baseline_summary: {},
    },
    tech_stack_infrastructure: {
      card_key: 'tech_stack_infrastructure',
      domain_key: 'technical_architecture',
      title: '技术栈与基础设施',
      summary: {
        tech_stack: {
          languages: ['Java'],
          frameworks: ['Spring Boot'],
          databases: ['MySQL'],
          middleware: ['Redis'],
          others: ['Docker'],
        },
        infrastructure_components: ['服务注册中心', '配置中心', '数据库连接池'],
        supplementary_notes: '',
      },
      content: {
        'technical_architecture.canonical.tech_stack': {
          languages: ['Java'],
          frameworks: ['Spring Boot'],
          databases: ['MySQL'],
          middleware: ['Redis'],
          others: ['Docker'],
        },
        'technical_architecture.canonical.extensions.infrastructure_components': ['服务注册中心', '配置中心', '数据库连接池'],
      },
      source_summary: '人工确认内容',
      edited: false,
      baseline_content: {},
      baseline_summary: {},
    },
    design_characteristics: {
      card_key: 'design_characteristics',
      domain_key: 'technical_architecture',
      title: '系统设计特点',
      summary: {
        design_methods: ['组件化设计', '插件化扩展'],
        extensibility_features: ['参数可配置化', '支持灵活扩展'],
        common_capabilities: ['日志', '权限控制', '订阅发布'],
      },
      content: {
        'technical_architecture.canonical.extensions.design_methods': ['组件化设计', '插件化扩展'],
        'technical_architecture.canonical.extensions.extensibility_features': ['参数可配置化', '支持灵活扩展'],
        'technical_architecture.canonical.extensions.common_capabilities': ['日志', '权限控制', '订阅发布'],
      },
      source_summary: '人工确认内容',
      edited: false,
      baseline_content: {},
      baseline_summary: {},
    },
    quality_attributes: {
      card_key: 'quality_attributes',
      domain_key: 'technical_architecture',
      title: '性能、安全与可用性',
      summary: {
        performance_requirements: {
          peak_tps: '200 TPS',
          p95_latency_ms: '80',
          availability_target: '99.99%',
          batch_window: '日终 30 分钟',
        },
        availability_design: ['应用节点互备', '自动故障切换'],
        monitoring_operations: ['服务监控', '异常诊断', '资源监控'],
        security_requirements: ['等保三级', '敏感数据传输加密'],
        supplementary_notes: '',
      },
      content: {
        'technical_architecture.canonical.performance_baseline': {
          online: { peak_tps: '200 TPS', p95_latency_ms: '80', availability_target: '99.99%' },
          batch: { window: '日终 30 分钟', data_volume: '', peak_duration: '' },
          processing_model: '',
        },
        'technical_architecture.canonical.extensions.availability_design': ['应用节点互备', '自动故障切换'],
        'technical_architecture.canonical.extensions.monitoring_operations': ['服务监控', '异常诊断', '资源监控'],
        'technical_architecture.canonical.extensions.security_requirements': ['等保三级', '敏感数据传输加密'],
      },
      source_summary: '人工确认内容',
      edited: false,
      baseline_content: {},
      baseline_summary: {},
    },
  };

  payload.domain_summary.technical_architecture = {
    ...payload.domain_summary.technical_architecture,
    card_count: 4,
    card_keys: [
      'architecture_deployment',
      'tech_stack_infrastructure',
      'design_characteristics',
      'quality_attributes',
    ],
  };

  return payload;
};

let currentProfilePayload = deepClone(baseProfilePayload);

const memoryPayload = {
  total: 2,
  items: [
    {
      memory_id: 'mem_001',
      memory_type: 'profile_update',
      memory_subtype: 'code_scan_suggestion',
      scene_id: 'code_scan_ingest',
      source_type: 'code_scan',
      source_id: 'exec_001',
      decision_policy: 'suggestion_only',
      confidence: 0.7,
      summary: '代码扫描生成画像建议',
      payload: { changed_fields: ['technical_architecture.canonical.tech_stack'] },
      evidence_refs: [],
      created_at: '2026-03-13T12:10:00',
    },
    {
      memory_id: 'mem_002',
      memory_type: 'function_point_adjustment',
      memory_subtype: 'task_feature_update',
      scene_id: 'feature_breakdown',
      source_type: 'task',
      source_id: 'task_001',
      decision_policy: 'manual',
      confidence: 1,
      summary: 'PM 合并功能点',
      payload: { adjustment_type: 'merge' },
      evidence_refs: [],
      created_at: '2026-03-13T12:11:00',
    },
  ],
};

const profileHealthPayload = {
  system_id: 'SYS-PAY',
  system_name: '支付系统',
  coverage: {
    target_field_count: 5,
    candidate_field_count: 4,
    missing_target_fields: ['constraints_risks.canonical.business_constraints'],
    coverage_ratio: 0.8,
  },
  low_confidence_candidates: [
    {
      field_path: 'technical_architecture.canonical.architecture_style',
      confidence: 0.42,
      value: '分层微服务架构',
      reason: '技术方案存在多处不一致表述',
    },
  ],
  conflicts: [
    {
      field_path: 'integration_interfaces.canonical.other_integrations',
      conflict_type: 'wiki_candidate_changed',
      previous_value: ['核心账务接口'],
      latest_value: ['核心账务接口', '数据仓库同步'],
    },
  ],
  latest_output_quality: {
    artifact_id: 'output_001',
    line_count: 36,
    suggestion_count: 4,
    missing_targets: ['constraints_risks.canonical.business_constraints'],
    missing_target_count: 1,
    noise_ratio: 0.2,
  },
};

const renderPage = () => render(
  <MemoryRouter
    future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    initialEntries={['/system-profiles/board?system_name=支付系统&system_id=SYS-PAY']}
  >
    <Routes>
      <Route path="/system-profiles/board" element={<SystemProfileBoardPage />} />
    </Routes>
  </MemoryRouter>
);

describe('SystemProfileBoardPage v2.7', () => {
  beforeAll(() => {
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: (query) => createMatchMediaResult(query),
    });
    jest.spyOn(message, 'success').mockImplementation(() => {});
    jest.spyOn(message, 'error').mockImplementation(() => {});
    jest.spyOn(message, 'warning').mockImplementation(() => {});
    jest.spyOn(window, 'confirm').mockImplementation(() => true);
  });

  afterAll(() => {
    message.success.mockRestore();
    message.error.mockRestore();
    message.warning.mockRestore();
    window.confirm.mockRestore();
  });

  beforeEach(() => {
    jest.clearAllMocks();
    window.confirm.mockImplementation(() => true);
    mockPermissionState = {
      isManager: true,
      isAdmin: false,
      isExpert: false,
    };
    currentProfilePayload = deepClone(baseProfilePayload);
    axios.get.mockImplementation(async (url) => {
      if (url === '/api/v1/system/systems') {
        return {
          data: {
            data: {
              systems: [
                {
                  id: 'SYS-PAY',
                  name: '支付系统',
                  status: '运行中',
                  extra: { owner_username: 'pm1' },
                },
              ],
            },
          },
        };
      }
      if (String(url).startsWith('/api/v1/system-profiles/completeness')) {
        return {
          data: {
            exists: true,
            completeness_score: 90,
            breakdown: { code_scan: 30, documents: 30, esb: 30 },
          },
        };
      }
      if (String(url).startsWith('/api/v1/system-profiles/SYS-PAY/profile/events')) {
        return { data: { total: 0, items: [] } };
      }
      if (String(url).startsWith('/api/v1/system-profiles/SYS-PAY/profile/health-report')) {
        return { data: profileHealthPayload };
      }
      if (String(url).startsWith('/api/v1/system-profiles/SYS-PAY/memory')) {
        return { data: memoryPayload };
      }
      if (String(url).startsWith('/api/v1/system-profiles/')) {
        return {
          data: {
            code: 200,
            data: currentProfilePayload,
          },
        };
      }
      return { data: {} };
    });
    axios.put.mockImplementation(async (_url, payload) => {
      currentProfilePayload = {
        ...currentProfilePayload,
        ...deepClone(payload),
      };
      return {
        data: {
          code: 200,
          data: currentProfilePayload,
        },
      };
    });
    axios.post.mockImplementation(async (url, payload) => {
      if (String(url).endsWith('/profile/cards/accept')) {
        delete currentProfilePayload.card_candidates?.[payload.card_key];
        return { data: { code: 200, data: currentProfilePayload } };
      }

      if (String(url).endsWith('/profile/cards/ignore')) {
        delete currentProfilePayload.card_candidates?.[payload.card_key];
        return { data: { code: 200, data: currentProfilePayload } };
      }

      if (String(url).endsWith('/profile/cards/restore-baseline')) {
        return { data: { code: 200, data: currentProfilePayload } };
      }

      if (String(url).endsWith('/profile/reset')) {
        currentProfilePayload = null;
        return {
          data: {
            code: 200,
            data: {
              system_id: 'SYS-PAY',
              deleted: true,
              workspace_deleted: true,
              deleted_runtime_executions: 1,
              deleted_memory_records: 1,
            },
          },
        };
      }

      if (String(url).endsWith('/profile/suggestions/accept')) {
        const suggestionValue = getMockSuggestionValue(
          currentProfilePayload.ai_suggestions,
          payload.domain,
          payload.sub_field
        );
        if (suggestionValue !== undefined) {
          currentProfilePayload.profile_data[payload.domain].canonical[payload.sub_field] = suggestionValue;
          currentProfilePayload.ai_suggestions = removeMockSuggestionValue(
            currentProfilePayload.ai_suggestions,
            payload.domain,
            payload.sub_field
          );
        }
        return { data: { code: 200, data: currentProfilePayload } };
      }

      if (String(url).endsWith('/profile/suggestions/ignore')) {
        const ignoredValue = getMockSuggestionValue(
          currentProfilePayload.ai_suggestions,
          payload.domain,
          payload.sub_field
        );
        currentProfilePayload.ai_suggestion_ignored = {
          ...deepClone(currentProfilePayload.ai_suggestion_ignored),
          [`${payload.domain}.${payload.sub_field}`]: deepClone(ignoredValue),
        };
        return { data: { code: 200, data: currentProfilePayload } };
      }

      if (String(url).endsWith('/profile/suggestions/rollback')) {
        return { data: { code: 200, data: currentProfilePayload } };
      }

      return { data: { code: 200, data: currentProfilePayload } };
    });
  });

  afterEach(() => {
    cleanup();
  });

  it('keeps the baseline tabs timeline and preview-first interaction', async () => {
    renderPage();

    expect(await screen.findByRole('tab', { name: '支付系统' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'D1 系统定位' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'D2 业务能力' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'D3 系统交互' })).toBeInTheDocument();
    expect(screen.getByText('变更时间线')).toBeInTheDocument();
    expect(screen.getByText('暂无变更记录')).toBeInTheDocument();

    expect(screen.getByText('核心职责')).toBeInTheDocument();
    expect(screen.getByText('统一支付受理')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '编辑核心职责' })).toBeInTheDocument();
    expect(screen.queryByLabelText('system_positioning.canonical.core_responsibility')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'D3 系统交互' }));

    expect(await screen.findByText('作为服务方')).toBeInTheDocument();
    expect(screen.getAllByText('支付路由服务')).toHaveLength(1);
    expect(screen.getByText('支付查询交易')).toBeInTheDocument();
    expect(screen.getByText('核心账务、清算平台')).toBeInTheDocument();
    expect(screen.getByText('客户中心服务')).toBeInTheDocument();
    expect(screen.getByText('客户查询交易')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '编辑作为服务方' })).toBeInTheDocument();
    expect(screen.queryByLabelText('integration_interfaces.canonical.provided_services')).not.toBeInTheDocument();
    expect(screen.queryByText(/来源：/)).not.toBeInTheDocument();
    expect(screen.queryByText('扩展信息')).not.toBeInTheDocument();
    expect(screen.queryByText('Memory 资产')).not.toBeInTheDocument();
    expect(screen.queryByText('代码扫描生成画像建议')).not.toBeInTheDocument();
    expect(screen.queryByText('PM 合并功能点')).not.toBeInTheDocument();
  });

  it('renders wiki compile health summary on the board page', async () => {
    renderPage();

    expect(await screen.findByText('Wiki 编译健康')).toBeInTheDocument();
    expect(screen.getByText('覆盖率 80%')).toBeInTheDocument();
    expect(screen.getByText('低置信 1')).toBeInTheDocument();
    expect(screen.getByText('冲突 1')).toBeInTheDocument();
    expect(screen.getByText('缺失目标 1')).toBeInTheDocument();
    expect(screen.getByText(/technical_architecture\.canonical\.architecture_style/)).toBeInTheDocument();
    expect(screen.queryByText(/integration_interfaces\.canonical\.other_integrations/)).not.toBeInTheDocument();
  });

  it('saves canonical edits through preview-first editor', async () => {
    renderPage();

    fireEvent.click(await screen.findByRole('button', { name: '编辑核心职责' }));

    const input = await screen.findByPlaceholderText('请输入核心职责');
    fireEvent.change(input, { target: { value: '统一支付受理与渠道接入' } });
    fireEvent.click(screen.getByRole('button', { name: '保存草稿' }));

    await waitFor(() => {
      expect(axios.put).toHaveBeenCalledWith(
        '/api/v1/system-profiles/%E6%94%AF%E4%BB%98%E7%B3%BB%E7%BB%9F',
        expect.objectContaining({
          system_id: 'SYS-PAY',
          profile_data: expect.objectContaining({
            system_positioning: expect.objectContaining({
              canonical: expect.objectContaining({
                core_responsibility: '统一支付受理与渠道接入',
              }),
            }),
          }),
        }),
      );
    });
  });

  it('maps legacy D1 suggestions to the preview card and accepts them with legacy field keys', async () => {
    currentProfilePayload.ai_suggestions = {
      system_positioning: {
        system_description: '统一支付受理与渠道接入',
      },
    };

    renderPage();

    expect(await screen.findByText('检测到 AI 建议变更')).toBeInTheDocument();
    expect(screen.getByText('统一支付受理与渠道接入')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '采纳新建议' }));

    await waitFor(() => {
      expect(axios.post).toHaveBeenCalledWith(
        '/api/v1/system-profiles/SYS-PAY/profile/suggestions/accept',
        { domain: 'system_positioning', sub_field: 'core_responsibility' }
      );
    });
    await waitFor(() => {
      expect(screen.queryByText('检测到 AI 建议变更')).not.toBeInTheDocument();
    });
    expect(screen.getByText('统一支付受理与渠道接入')).toBeInTheDocument();
  });

  it('hides ignored v27 suggestions after ignore and keeps the tab clean after saving', async () => {
    currentProfilePayload.ai_suggestions = {
      technical_architecture: {
        tech_stack: {
          languages: ['Java', 'Go'],
          frameworks: ['Spring Boot'],
          databases: ['MySQL'],
          middleware: [],
          others: ['Redis'],
        },
      },
    };

    renderPage();

    const d4Button = await screen.findByRole('button', { name: /D4 技术架构/ });
    expect(within(d4Button).getByText('有建议')).toBeInTheDocument();

    fireEvent.click(d4Button);
    expect(await screen.findByText('检测到 AI 建议变更')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '忽略' }));

    await waitFor(() => {
      expect(axios.post).toHaveBeenCalledWith(
        '/api/v1/system-profiles/SYS-PAY/profile/suggestions/ignore',
        { domain: 'technical_architecture', sub_field: 'tech_stack' }
      );
    });
    await waitFor(() => {
      expect(screen.queryByText('检测到 AI 建议变更')).not.toBeInTheDocument();
    });
    expect(within(screen.getByRole('button', { name: /D4 技术架构/ })).queryByText('有建议')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '保存草稿' }));

    await waitFor(() => {
      expect(axios.put).toHaveBeenCalled();
    });
    await waitFor(() => {
      expect(screen.queryByText('检测到 AI 建议变更')).not.toBeInTheDocument();
    });
    expect(within(screen.getByRole('button', { name: /D4 技术架构/ })).queryByText('有建议')).not.toBeInTheDocument();
  });

  it('unwraps structured document suggestions instead of rendering object text', async () => {
    currentProfilePayload.ai_suggestions = {
      constraints_risks: {
        known_risks: {
          value: ['缓存击穿导致交易超时'],
          scene_id: 'pm_document_ingest',
          skill_id: 'tech_solution_skill',
          decision_policy: 'suggestion_only',
          confidence: 0.7,
          reason: '从技术方案正文提取',
        },
      },
    };

    renderPage();

    fireEvent.click(await screen.findByRole('button', { name: /D5 风险约束/ }));

    expect(await screen.findByText('检测到 AI 建议变更')).toBeInTheDocument();
    expect(screen.getByText('缓存击穿导致交易超时')).toBeInTheDocument();
    expect(screen.queryByText('[object Object]')).not.toBeInTheDocument();
  });

  it('accepts flat canonical document suggestions and removes the diff card', async () => {
    currentProfilePayload.ai_suggestions = {
      'technical_architecture.canonical.architecture_style': {
        value: '分层微服务架构',
        scene_id: 'pm_document_ingest',
        skill_id: 'tech_solution_skill',
        decision_policy: 'suggestion_only',
        confidence: 0.82,
        reason: '从技术方案正文提取',
      },
    };

    renderPage();

    fireEvent.click(await screen.findByRole('button', { name: /D4 技术架构/ }));
    expect(await screen.findByText('检测到 AI 建议变更')).toBeInTheDocument();
    expect(screen.getByText('分层微服务架构')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '采纳新建议' }));

    await waitFor(() => {
      expect(axios.post).toHaveBeenCalledWith(
        '/api/v1/system-profiles/SYS-PAY/profile/suggestions/accept',
        { domain: 'technical_architecture', sub_field: 'architecture_style' }
      );
    });
    await waitFor(() => {
      expect(screen.queryByText('检测到 AI 建议变更')).not.toBeInTheDocument();
    });
  });

  it('ignores flat canonical document suggestions and clears the domain badge', async () => {
    currentProfilePayload.ai_suggestions = {
      'integration_interfaces.canonical.other_integrations': {
        value: ['提供贷款核算查询接口，对接核心系统和数据仓库'],
        scene_id: 'pm_document_ingest',
        skill_id: 'tech_solution_skill',
        decision_policy: 'suggestion_only',
        confidence: 0.82,
        reason: '从技术方案正文提取',
      },
    };

    renderPage();

    const d3Button = await screen.findByRole('button', { name: /D3 系统交互/ });
    expect(within(d3Button).getByText('有建议')).toBeInTheDocument();

    fireEvent.click(d3Button);
    expect(await screen.findByText('检测到 AI 建议变更')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '忽略' }));

    await waitFor(() => {
      expect(axios.post).toHaveBeenCalledWith(
        '/api/v1/system-profiles/SYS-PAY/profile/suggestions/ignore',
        { domain: 'integration_interfaces', sub_field: 'other_integrations' }
      );
    });
    await waitFor(() => {
      expect(screen.queryByText('检测到 AI 建议变更')).not.toBeInTheDocument();
    });
    expect(within(screen.getByRole('button', { name: /D3 系统交互/ })).queryByText('有建议')).not.toBeInTheDocument();
  });

  it('renders the cards_v1 board with current content above candidate content for v2.8 payloads', async () => {
    currentProfilePayload = buildCardsV1Payload();

    renderPage();

    expect(await screen.findByText('当前内容展示在上方，候选内容在下方待确认；采纳后先进入草稿，保存后更新画像；高可信基线可随时恢复。')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /D1 系统定位/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /D3 系统交互/ })).toBeInTheDocument();
    expect(screen.getByText('系统身份')).toBeInTheDocument();
    expect(screen.getByText('候选内容')).toBeInTheDocument();
    expect(screen.queryAllByText('当前确认内容')).toHaveLength(0);
    expect(screen.queryByText('高可信基础资料')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: '采纳候选' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '忽略候选' })).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: '编辑卡片' }).length).toBeGreaterThan(0);
  });

  it('keeps the cards_v1 domain navigator sticky while the page scrolls', async () => {
    currentProfilePayload = buildCardsV1Payload();

    renderPage();

    const domainText = await screen.findByText(/D1 系统定位/);
    const domainButton = domainText.closest('button');
    const navCard = domainButton.closest('.ant-card');
    expect(navCard).toHaveStyle({
      position: 'sticky',
      top: '16px',
    });
  });

  it('uses layered surfaces to distinguish the cards_v1 sections', async () => {
    currentProfilePayload = buildCardsV1Payload();

    renderPage();

    await screen.findByText('核心业务系统');
    const currentContentCard = screen.getByTestId('card-current-section-system_identity');
    expect(currentContentCard).toHaveStyle({
      background: '#f6f8fb',
      borderColor: '#d8e1ec',
    });
  });

  it('renders cards_v1 candidate content below the current content section', async () => {
    currentProfilePayload = buildCardsV1Payload();

    renderPage();

    await screen.findByText('核心业务系统');
    const currentContentCard = screen.getByTestId('card-current-section-system_identity');
    const candidateContentCard = screen.getByTestId('card-candidate-section-system_identity');

    expect(
      currentContentCard.compareDocumentPosition(candidateContentCard) & Node.DOCUMENT_POSITION_FOLLOWING
    ).toBeTruthy();
  });

  it('recomputes cards_v1 domain candidate badges from visible candidates only', async () => {
    currentProfilePayload = buildCardsV1Payload();
    currentProfilePayload.domain_summary.integration_interfaces.candidate_count = 1;
    currentProfilePayload.card_candidates = {
      ...currentProfilePayload.card_candidates,
      data_exchange_batch_links: {
        card_key: 'data_exchange_batch_links',
        domain_key: 'integration_interfaces',
        title: '数据交换与批量链路',
        summary: { items: [] },
        content: {
          'integration_interfaces.canonical.other_integrations': [],
        },
      },
    };

    renderPage();

    expect(await screen.findByText('当前内容展示在上方，候选内容在下方待确认；采纳后先进入草稿，保存后更新画像；高可信基线可随时恢复。')).toBeInTheDocument();
    const d1Button = screen.getByRole('button', { name: /D1 系统定位/ });
    const d3Button = screen.getByRole('button', { name: /D3 系统交互/ });
    expect(within(d1Button).getByText('候选 1')).toBeInTheDocument();
    expect(within(d3Button).queryByText(/候选/)).not.toBeInTheDocument();
  });

  it('does not render recent conflict details on the cards_v1 board health card', async () => {
    currentProfilePayload = buildCardsV1Payload();

    renderPage();

    expect(await screen.findByText('Wiki 编译健康')).toBeInTheDocument();
    expect(screen.queryByText('最近冲突')).not.toBeInTheDocument();
    expect(screen.queryByText('integration_interfaces.canonical.other_integrations')).not.toBeInTheDocument();
  });

  it('renders D3 cards_v1 service cards with the v2.7 table headers', async () => {
    currentProfilePayload = buildCardsV1Payload();

    renderPage();

    const d3DomainText = await screen.findByText(/D3 系统交互/);
    fireEvent.click(d3DomainText.closest('button'));

    expect(await screen.findByText('对外提供能力')).toBeInTheDocument();
    expect(screen.getByText('对外依赖能力')).toBeInTheDocument();
    expect(screen.getAllByText('服务名称').length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText('交易名称').length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText('对端系统').length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText('支付路由服务')).toBeInTheDocument();
    expect(screen.getByText('客户中心服务')).toBeInTheDocument();
  });

  it('renders D3 batch link cards as structured interaction blocks', async () => {
    currentProfilePayload = buildCardsV1Payload();
    currentProfilePayload.profile_cards.data_exchange_batch_links.summary = {
      items: [
        {
          exchange_object: '授信额度、贷款账户、账务信息',
          peer_system: '融资系统,核心系统',
          exchange_mode: '接口 + 批量',
          schedule: '日终',
          notes: '融资系统在审批后调用贷款核算系统放款开户；核心系统记录账户余额、状态并提供查询接口。',
        },
        {
          exchange_object: '还款流水、计息记录',
          peer_system: '核心总行',
          exchange_mode: '批量',
          schedule: '日切',
          notes: '内部账户之间的放款还款、日终计息计提通过核心总行记账。',
        },
      ],
    };
    currentProfilePayload.profile_cards.data_exchange_batch_links.content = {
      'integration_interfaces.canonical.other_integrations': currentProfilePayload.profile_cards.data_exchange_batch_links.summary.items,
    };

    renderPage();

    const d3DomainText = await screen.findByText(/D3 系统交互/);
    fireEvent.click(d3DomainText.closest('button'));

    expect(await screen.findByText('数据交换与批量链路')).toBeInTheDocument();
    expect(screen.getAllByText('交互数据').length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText('上下游系统').length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText('触发与批量关系').length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText('链路说明').length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText('授信额度、贷款账户、账务信息')).toBeInTheDocument();
    expect(screen.getByText('还款流水、计息记录')).toBeInTheDocument();
    expect(screen.queryByText('条目')).not.toBeInTheDocument();
  });

  it('renders redesigned D2 cards_v1 with structured entries', async () => {
    currentProfilePayload = buildRedesignedCardsV1Payload();

    renderPage();

    const d2DomainText = await screen.findByText(/D2 业务能力/);
    fireEvent.click(d2DomainText.closest('button'));

    const capabilityCard = (await screen.findByText('功能模块', { selector: '.ant-card-head-title' })).closest('.ant-card');
    const scenarioCard = screen.getByText('典型场景', { selector: '.ant-card-head-title' }).closest('.ant-card');
    expect(capabilityCard).not.toBeNull();
    expect(scenarioCard).not.toBeNull();
    expect(screen.getByText('业务流程', { selector: '.ant-card-head-title' })).toBeInTheDocument();
    expect(screen.getByText('数据报表', { selector: '.ant-card-head-title' })).toBeInTheDocument();
    expect(
      within(capabilityCard).getByText('- 支付路由:统一路由交易请求。')
    ).toBeInTheDocument();
    expect(
      within(capabilityCard).getByText('- 渠道接入:接入多渠道支付请求。')
    ).toBeInTheDocument();
    expect(
      within(scenarioCard).getByText('- 柜面发起支付并返回结果。')
    ).toBeInTheDocument();
  });

  it('renders the redesigned short domain titles and D1 D2 D5 card groups', async () => {
    currentProfilePayload = buildRedesignedCardsV1Payload();

    renderPage();

    expect(await screen.findByRole('button', { name: /D1 系统定位/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /D2 业务能力/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /D3 系统交互/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /D4 技术架构/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /D5 风险约束/ })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /D1 系统定位/ }));
    expect(await screen.findByText('系统身份', { selector: '.ant-card-head-title' })).toBeInTheDocument();
    expect(screen.getByText('业务归属', { selector: '.ant-card-head-title' })).toBeInTheDocument();
    expect(screen.getByText('应用层级', { selector: '.ant-card-head-title' })).toBeInTheDocument();
    expect(screen.getByText('服务定位', { selector: '.ant-card-head-title' })).toBeInTheDocument();
    expect(screen.queryByText('责任边界与生态位置', { selector: '.ant-card-head-title' })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /D2 业务能力/ }));
    expect(await screen.findByText('功能模块', { selector: '.ant-card-head-title' })).toBeInTheDocument();
    expect(screen.getByText('典型场景', { selector: '.ant-card-head-title' })).toBeInTheDocument();
    expect(screen.getByText('业务流程', { selector: '.ant-card-head-title' })).toBeInTheDocument();
    expect(screen.getByText('数据报表', { selector: '.ant-card-head-title' })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /D5 风险约束/ }));
    expect(await screen.findByText('业务约束', { selector: '.ant-card-head-title' })).toBeInTheDocument();
    expect(screen.getByText('前提条件', { selector: '.ant-card-head-title' })).toBeInTheDocument();
    expect(screen.getByText('敏感环节', { selector: '.ant-card-head-title' })).toBeInTheDocument();
    expect(screen.getByText('风险事项', { selector: '.ant-card-head-title' })).toBeInTheDocument();
  });

  it('renders D4 cards_v1 with the new generic fixed slots and hides empty supplementary notes', async () => {
    currentProfilePayload = buildTechnicalArchitectureCardsV1Payload();

    renderPage();

    const d4DomainText = await screen.findByText(/D4 技术架构/);
    fireEvent.click(d4DomainText.closest('button'));

    const architectureCard = (await screen.findByText('架构与部署方式', { selector: '.ant-card-head-title' })).closest('.ant-card');
    const stackCard = screen.getByText('技术栈与基础设施', { selector: '.ant-card-head-title' }).closest('.ant-card');
    const designCard = screen.getByText('系统设计特点', { selector: '.ant-card-head-title' }).closest('.ant-card');
    const qualityCard = screen.getByText('性能、安全与可用性', { selector: '.ant-card-head-title' }).closest('.ant-card');

    expect(screen.queryByText('架构形态与处理模式', { selector: '.ant-card-head-title' })).not.toBeInTheDocument();

    expect(within(architectureCard).getByText('部署方式')).toBeInTheDocument();
    expect(within(architectureCard).getByText('部署环境')).toBeInTheDocument();
    expect(within(architectureCard).getByText('拓扑特点')).toBeInTheDocument();
    expect(within(architectureCard).getByText('补充说明')).toBeInTheDocument();

    expect(within(stackCard).getByText('技术栈')).toBeInTheDocument();
    expect(within(stackCard).getByText('基础设施/中间件')).toBeInTheDocument();
    expect(within(stackCard).queryByText('补充说明')).not.toBeInTheDocument();

    expect(within(designCard).getByText('设计方法')).toBeInTheDocument();
    expect(within(designCard).getByText('扩展性特征')).toBeInTheDocument();
    expect(within(designCard).getByText('通用支撑能力')).toBeInTheDocument();

    expect(within(qualityCard).getByText('性能要求')).toBeInTheDocument();
    expect(within(qualityCard).getByText('可用性设计')).toBeInTheDocument();
    expect(within(qualityCard).getByText('监控运维')).toBeInTheDocument();
    expect(within(qualityCard).getByText('安全要求')).toBeInTheDocument();
    expect(within(qualityCard).queryByText('补充说明')).not.toBeInTheDocument();
  });

  it('renders D4 nested summary labels in Chinese instead of raw english keys', async () => {
    currentProfilePayload = buildTechnicalArchitectureCardsV1Payload();

    renderPage();

    const d4DomainText = await screen.findByText(/D4 技术架构/);
    fireEvent.click(d4DomainText.closest('button'));

    const stackCard = screen.getByText('技术栈与基础设施', { selector: '.ant-card-head-title' }).closest('.ant-card');
    const qualityCard = screen.getByText('性能、安全与可用性', { selector: '.ant-card-head-title' }).closest('.ant-card');

    expect(within(stackCard).getByText('语言：Java')).toBeInTheDocument();
    expect(within(stackCard).getByText('框架：Spring Boot')).toBeInTheDocument();
    expect(within(stackCard).queryByText('languages')).not.toBeInTheDocument();
    expect(within(stackCard).queryByText('frameworks')).not.toBeInTheDocument();

    expect(within(qualityCard).getByText('P95 延迟(ms)：80')).toBeInTheDocument();
    expect(within(qualityCard).getByText('可用性目标：99.99%')).toBeInTheDocument();
    expect(within(qualityCard).queryByText('p95_latency_ms')).not.toBeInTheDocument();
    expect(within(qualityCard).queryByText('availability_target')).not.toBeInTheDocument();
  });

  it('accepts cards_v1 candidate cards through the card action api', async () => {
    currentProfilePayload = buildCardsV1Payload();

    renderPage();

    expect(await screen.findByText('候选内容')).toBeInTheDocument();
    fireEvent.click((await screen.findAllByRole('button', { name: '采纳候选' }))[0]);

    await waitFor(() => {
      expect(axios.post).toHaveBeenCalledWith(
        '/api/v1/system-profiles/SYS-PAY/profile/cards/accept',
        { card_key: 'system_identity' }
      );
    });
  });

  it('applies card edits to the visible draft content immediately on cards_v1 board', async () => {
    currentProfilePayload = buildCardsV1Payload();

    renderPage();

    const cardTitle = await screen.findByText('服务定位');
    const card = cardTitle.closest('.ant-card');
    expect(card).not.toBeNull();

    fireEvent.click(within(card).getByRole('button', { name: '编辑卡片' }));

    const textareas = within(card).getAllByRole('textbox');
    fireEvent.change(textareas[0], { target: { value: '内部柜员\n贷款产品经理' } });
    fireEvent.change(textareas[1], { target: { value: '本文件编写的目的是为贷款产品经理提供工作指导。' } });

    fireEvent.click(within(card).getByRole('button', { name: '应用到草稿' }));

    expect(within(card).getByText('贷款产品经理')).toBeInTheDocument();
    expect(
      within(card).getByText('本文件编写的目的是为贷款产品经理提供工作指导。')
    ).toBeInTheDocument();
    expect(within(card).queryByText('运营人员')).not.toBeInTheDocument();
    expect(within(card).queryByText('统一支付受理')).not.toBeInTheDocument();
    expect(within(card).queryByText('已编辑')).not.toBeInTheDocument();
  });

  it('allows admin to reset profile workspace from the board page', async () => {
    mockPermissionState = {
      isManager: false,
      isAdmin: true,
      isExpert: false,
    };
    currentProfilePayload = buildCardsV1Payload();

    renderPage();

    const resetButton = await screen.findByRole('button', { name: '清空画像数据' });
    fireEvent.click(resetButton);

    await waitFor(() => {
      expect(window.confirm).toHaveBeenCalled();
    });
    await waitFor(() => {
      expect(axios.post).toHaveBeenCalledWith(
        '/api/v1/system-profiles/SYS-PAY/profile/reset',
        { reason: 'admin_reset_workspace' }
      );
    });
    await waitFor(() => {
      expect(message.success).toHaveBeenCalledWith('已清空该系统的画像数据');
    });
  });

  it('triggers ai suggestion retry from the board and reloads profile data', async () => {
    axios.post.mockImplementation(async (url, payload) => {
      if (String(url).endsWith('/ai-suggestions/retry')) {
        currentProfilePayload.ai_suggestions = {
          'technical_architecture.canonical.architecture_style': {
            value: '分层微服务架构',
            scene_id: 'pm_document_ingest',
            skill_id: 'tech_solution_skill',
            decision_policy: 'suggestion_only',
            confidence: 0.81,
            reason: '从技术方案正文提取',
          },
        };
        return {
          data: {
            execution_id: 'exec_retry_001',
            status: 'completed',
            message: '已重新生成 AI 建议',
          },
        };
      }
      return { data: { code: 200, data: currentProfilePayload } };
    });

    renderPage();

    const retryButton = await screen.findByRole('button', { name: '重新生成 AI 建议' });
    fireEvent.click(retryButton);

    await waitFor(() => {
      expect(axios.post).toHaveBeenCalledWith('/api/v1/system-profiles/SYS-PAY/ai-suggestions/retry');
    });
    await waitFor(() => {
      expect(message.success).toHaveBeenCalledWith('已重新生成 AI 建议');
    });
  });
});
