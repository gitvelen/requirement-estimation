import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import '@testing-library/jest-dom';
import { message } from 'antd';
import SystemProfileBoardPage from '../pages/SystemProfileBoardPage';

jest.setTimeout(30000);

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
  isManager: true,
  isAdmin: false,
  isExpert: false,
}));

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

const baseProfilePayload = {
  system_id: 'SYS-PAY',
  status: 'draft',
  updated_at: '2026-03-13T12:00:00',
  pending_fields: [],
  profile_data: {
    system_positioning: {
      canonical: {
        system_type: '核心业务系统',
        business_domain: ['支付'],
        architecture_layer: '应用层',
        target_users: ['运营人员'],
        service_scope: '统一支付受理',
        system_boundary: ['不处理账务总账'],
        extensions: {
          related_systems: ['CRM'],
        },
      },
    },
    business_capabilities: {
      canonical: {
        functional_modules: ['支付路由'],
        business_processes: ['支付处理'],
        data_assets: ['交易记录'],
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
        technical_constraints: ['数据库国产化'],
        business_constraints: ['清算窗口限制'],
        known_risks: ['外部通道抖动'],
        extensions: {},
      },
    },
  },
  field_sources: {
    'system_positioning.canonical.service_scope': {
      source: 'manual',
      actor: '项目经理1',
    },
  },
  ai_suggestions: {},
  ai_suggestions_previous: null,
  ai_suggestion_ignored: {},
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
  });

  afterAll(() => {
    message.success.mockRestore();
    message.error.mockRestore();
    message.warning.mockRestore();
  });

  beforeEach(() => {
    jest.clearAllMocks();
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
      if (String(url).endsWith('/profile/suggestions/accept')) {
        if (payload.domain === 'system_positioning' && payload.sub_field === 'service_scope') {
          currentProfilePayload.profile_data.system_positioning.canonical.service_scope =
            currentProfilePayload.ai_suggestions.system_positioning.system_description;
        }
        if (payload.domain === 'technical_architecture' && payload.sub_field === 'tech_stack') {
          currentProfilePayload.profile_data.technical_architecture.canonical.tech_stack =
            deepClone(currentProfilePayload.ai_suggestions.technical_architecture.tech_stack);
        }
        return { data: { code: 200, data: currentProfilePayload } };
      }

      if (String(url).endsWith('/profile/suggestions/ignore')) {
        currentProfilePayload.ai_suggestion_ignored = {
          ...deepClone(currentProfilePayload.ai_suggestion_ignored),
          [`${payload.domain}.${payload.sub_field}`]:
            deepClone(currentProfilePayload.ai_suggestions[payload.domain][payload.sub_field]),
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
    expect(screen.getByRole('button', { name: 'D1 系统定位与边界' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'D2 业务能力与流程' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'D3 集成与接口' })).toBeInTheDocument();
    expect(screen.getByText('变更时间线')).toBeInTheDocument();
    expect(screen.getByText('暂无变更记录')).toBeInTheDocument();

    expect(screen.getByText('服务范围')).toBeInTheDocument();
    expect(screen.getByText('统一支付受理')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '编辑服务范围' })).toBeInTheDocument();
    expect(screen.queryByLabelText('system_positioning.canonical.service_scope')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'D3 集成与接口' }));

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

  it('saves canonical edits through preview-first editor', async () => {
    renderPage();

    fireEvent.click(await screen.findByRole('button', { name: '编辑服务范围' }));

    const input = await screen.findByPlaceholderText('请输入服务范围');
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
                service_scope: '统一支付受理与渠道接入',
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
        { domain: 'system_positioning', sub_field: 'service_scope' }
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

    fireEvent.click(await screen.findByRole('button', { name: /D5 约束与风险/ }));

    expect(await screen.findByText('检测到 AI 建议变更')).toBeInTheDocument();
    expect(screen.getByText('缓存击穿导致交易超时')).toBeInTheDocument();
    expect(screen.queryByText('[object Object]')).not.toBeInTheDocument();
  });
});
