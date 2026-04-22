import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import '@testing-library/jest-dom';
import SystemProfileBoardPage from '../pages/SystemProfileBoardPage';
import ModuleStructurePreview from '../components/systemProfile/ModuleStructurePreview';
import StructuredFieldPreview from '../components/systemProfile/StructuredFieldPreview';
import StructuredFieldDiffPreview from '../components/systemProfile/StructuredFieldDiffPreview';

jest.setTimeout(120000);

jest.mock('axios', () => ({
  get: jest.fn(),
  post: jest.fn(),
  put: jest.fn(),
}));
const axios = require('axios');

jest.mock('../hooks/useAuth', () => () => ({
  user: {
    id: 'u_tester',
    username: 'tester',
    displayName: '测试PM',
  },
}));

jest.mock('../hooks/usePermission', () => () => ({
  isManager: true,
}));

const createProfilePayload = (overrides = {}) => ({
  status: 'draft',
  pending_fields: [],
  updated_at: '2026-03-01T10:00:00',
  is_stale: false,
  system_id: 'sys_alpha',
  ...overrides,
  profile_data: {
    system_positioning: {
      system_description: '当前系统描述',
      target_users: ['企业用户'],
      boundaries: ['仅覆盖开户流程'],
    },
    business_capabilities: {
      module_structure: [{ module_name: '开户', functions: [{ name: '证件校验', desc: 'OCR' }] }],
      core_processes: ['开户审核'],
    },
    integration_interfaces: {
      integration_points: [{ description: '调用核心系统' }],
      external_dependencies: ['OCR服务'],
    },
    technical_architecture: {
      architecture_positioning: '分层架构',
      tech_stack: ['React', 'FastAPI'],
      performance_profile: { qps: 20 },
    },
    constraints_risks: {
      key_constraints: [{ category: '合规', description: '实名校验' }],
      known_risks: ['OCR可用性'],
    },
    ...(overrides.profile_data || {}),
  },
  ai_suggestions: {
    system_positioning: {
      system_description: 'AI建议-系统描述',
      target_users: ['企业用户'],
      boundaries: ['仅覆盖开户流程'],
    },
    ...(overrides.ai_suggestions || {}),
  },
  ai_suggestions_previous: overrides.ai_suggestions_previous ?? null,
  ai_suggestion_ignored: overrides.ai_suggestion_ignored ?? {},
});

const setupAxiosMock = (profileOverrides) => {
  const profile = createProfilePayload(profileOverrides);
  const suggestionAliasMap = {
    system_positioning: {
      core_responsibility: 'system_description',
    },
    constraints_risks: {
      prerequisites: 'key_constraints',
      risk_items: 'known_risks',
    },
  };

  const clone = (value) => JSON.parse(JSON.stringify(value));

  axios.get.mockImplementation((url) => {
    if (url === '/api/v1/system/systems') {
      return Promise.resolve({
        data: {
          data: {
            systems: [
              {
                id: 'sys_alpha',
                name: '系统A',
                status: 'active',
                extra: { owner_username: 'tester' },
              },
            ],
          },
        },
      });
    }

    if (url === '/api/v1/system-profiles/completeness') {
      return Promise.resolve({
        data: {
          exists: true,
          completeness_score: 88,
          breakdown: { code_scan: 30, documents: 40, esb: 18 },
        },
      });
    }

    if (String(url).includes('/profile/events')) {
      return Promise.resolve({ data: { total: 0, items: [] } });
    }

    if (String(url).includes('/api/v1/system-profiles/')) {
      return Promise.resolve({
        data: {
          code: 200,
          data: profile,
        },
      });
    }

    return Promise.resolve({ data: {} });
  });

  axios.put.mockResolvedValue({ data: { code: 200 } });
  axios.post.mockImplementation((url, payload = {}) => {
    if (String(url).includes('/profile/suggestions/ignore')) {
      const domain = String(payload?.domain || '').trim();
      const subField = String(payload?.sub_field || '').trim();
      const aliasedSubField = suggestionAliasMap?.[domain]?.[subField] || subField;
      const suggestion = profile.ai_suggestions?.[domain]?.[aliasedSubField];
      if (domain && subField && suggestion !== undefined) {
        profile.ai_suggestion_ignored = {
          ...(profile.ai_suggestion_ignored || {}),
          [`${domain}.${aliasedSubField}`]: clone(suggestion),
        };
      }
      return Promise.resolve({
        data: {
          code: 200,
          data: clone(profile),
        },
      });
    }
    return Promise.resolve({ data: { code: 200 } });
  });
};

const renderPage = () => render(
  <MemoryRouter initialEntries={['/system-profiles/board?system_name=系统A&system_id=sys_alpha']}>
    <Routes>
      <Route path="/system-profiles/board" element={<SystemProfileBoardPage />} />
    </Routes>
  </MemoryRouter>
);

describe('SystemProfileBoardPage v2.4 baseline', () => {
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

  beforeAll(() => {
    jest.spyOn(console, 'warn').mockImplementation((...args) => {
      const firstArg = String(args[0] || '');
      if (firstArg.includes('React Router Future Flag Warning')) {
        return;
      }
    });
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: (query) => createMatchMediaResult(query),
    });
  });

  afterAll(() => {
    if (console.warn.mockRestore) {
      console.warn.mockRestore();
    }
  });

  beforeEach(() => {
    jest.clearAllMocks();
    setupAxiosMock();
  });

  it('keeps baseline action buttons and timeline card', async () => {
    renderPage();

    expect(await screen.findByText('保存草稿')).toBeInTheDocument();
    expect(screen.getByText('发布画像')).toBeInTheDocument();
    expect(screen.getByText('变更时间线')).toBeInTheDocument();
    expect(screen.getByText('暂无变更记录')).toBeInTheDocument();
  });

  it('keeps baseline domain tabs', async () => {
    renderPage();

    expect(await screen.findByText('D1 系统定位与边界')).toBeInTheDocument();
    expect(screen.getByText('D2 业务能力与流程')).toBeInTheDocument();
    expect(screen.getByText('D3 集成与接口')).toBeInTheDocument();
    expect(screen.getByText('D4 技术架构')).toBeInTheDocument();
    expect(screen.getByText('D5 约束与风险')).toBeInTheDocument();
  });

  it('renders D1 summary fields in preview mode and exposes edit buttons', async () => {
    renderPage();

    expect(await screen.findByText('系统描述')).toBeInTheDocument();
    expect(await screen.findByText('企业用户')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '编辑系统描述' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '编辑目标用户' })).toBeInTheDocument();
    expect(screen.queryAllByPlaceholderText('请输入系统描述')).toHaveLength(0);

    fireEvent.click(screen.getByRole('button', { name: '编辑系统描述' }));
    expect(screen.getByPlaceholderText('请输入系统描述')).toBeInTheDocument();
  });

  it('renders D2 tree with first-level expanded, legacy functions and depth guard', async () => {
    render(
      <ModuleStructurePreview
        value={[
          {
            module_name: '开户',
            description: '顶层模块',
            functions: [{ name: '证件校验', desc: 'OCR 校验' }],
            children: [
              {
                module_name: '资料审核',
                children: [
                  {
                    module_name: '人工复核',
                    children: [{ module_name: '超深节点', description: '不应渲染' }],
                  },
                ],
              },
            ],
          },
        ]}
      />
    );

    expect(screen.getByRole('button', { name: '收起 开户' })).toBeInTheDocument();
    expect(screen.getByText('证件校验')).toBeInTheDocument();
    expect(screen.getByText('资料审核')).toBeInTheDocument();
    expect(screen.queryByText('人工复核')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '展开 资料审核' }));
    expect(screen.getByText('人工复核')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '展开 人工复核' }));
    expect(screen.getByText('超出展示深度')).toBeInTheDocument();
    expect(screen.queryByText('超深节点')).not.toBeInTheDocument();
  });

  it('renders D3 and D5 structured previews as tables', () => {
    render(
      <>
        <StructuredFieldPreview
          title="当前集成点"
          kind="integration_points"
          value={[
            { peer_system: '核心账务', protocol: 'HTTP', direction: 'outbound', description: '同步开户' },
            { peer_system: '征信平台', protocol: 'MQ', direction: 'sideways', description: '异步核验' },
          ]}
        />
        <StructuredFieldPreview
          title="当前关键约束"
          kind="key_constraints"
          value={[{ category: '合规', description: '实名校验' }]}
        />
        <StructuredFieldPreview title="当前已知风险" kind="known_risks" value={['OCR可用性']} />
      </>
    );

    expect(screen.getByText('当前集成点')).toBeInTheDocument();
    expect(screen.getByText('对端系统')).toBeInTheDocument();
    expect(screen.getByText('协议')).toBeInTheDocument();
    expect(screen.getByText('方向')).toBeInTheDocument();
    expect(screen.getByText('集成说明')).toBeInTheDocument();
    expect(screen.getByText('核心账务')).toBeInTheDocument();
    expect(screen.getByText('→')).toBeInTheDocument();
    expect(screen.getByText('未知方向')).toBeInTheDocument();

    expect(screen.getByText('当前关键约束')).toBeInTheDocument();
    expect(screen.getByText('约束类型')).toBeInTheDocument();
    expect(screen.getByText('内容')).toBeInTheDocument();
    expect(screen.getByText('合规')).toBeInTheDocument();
    expect(screen.getByText('实名校验')).toBeInTheDocument();

    expect(screen.getByText('当前已知风险')).toBeInTheDocument();
    expect(screen.getByText('风险项')).toBeInTheDocument();
    expect(screen.getByText('OCR可用性')).toBeInTheDocument();
  });

  it('shows performance profile in preview mode by default and opens editor on demand', async () => {
    setupAxiosMock({
      profile_data: {
        technical_architecture: {
          architecture_positioning: '分层架构',
          tech_stack: ['React', 'FastAPI'],
          performance_profile: {
            并发量: '20并发下，平均20TPS',
            响应时间: '交易平均响应时间为3秒',
          },
        },
      },
    });

    renderPage();

    fireEvent.click(await screen.findByRole('button', { name: 'D4 技术架构' }));

    expect(await screen.findByText('性能画像')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '编辑性能画像' })).toBeInTheDocument();
    expect(screen.queryByText('当前性能画像')).not.toBeInTheDocument();
    expect(screen.queryAllByPlaceholderText('指标值')).toHaveLength(0);

    fireEvent.click(screen.getByRole('button', { name: '编辑性能画像' }));

    expect(screen.getByPlaceholderText('请输入处理模式')).toBeInTheDocument();
    expect(screen.getAllByPlaceholderText('指标值').length).toBeGreaterThan(0);
  }, 120000);

  it('applies the preview-first flow to D2 fields and shows header actions', async () => {
    renderPage();

    fireEvent.click(await screen.findByRole('button', { name: 'D2 业务能力与流程' }));
    expect(await screen.findByText('模块结构')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '编辑模块结构' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '编辑核心流程' })).toBeInTheDocument();
    expect(screen.queryByText('当前模块结构')).not.toBeInTheDocument();
    expect(screen.queryAllByPlaceholderText('模块名称')).toHaveLength(0);
    fireEvent.click(screen.getByRole('button', { name: '编辑模块结构' }));
    expect(screen.getAllByPlaceholderText('模块名称').length).toBeGreaterThan(0);
    expect(screen.queryByRole('button', { name: '收起 开户' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '展开 开户' })).not.toBeInTheDocument();
    expect(screen.queryByText('当前模块结构')).not.toBeInTheDocument();
  }, 30000);

  it('hides D2 diff when saved module structure matches suggestion after normalization', async () => {
    setupAxiosMock({
      profile_data: {
        business_capabilities: {
          module_structure: [
            {
              module_name: '贷款开户放款',
              description: '顶层模块',
              last_updated: '2026-03-07T10:00:00',
              children: [
                { module_name: '开户放款', description: '处理开户放款', children: [], last_updated: '2026-03-07T10:00:00' },
              ],
            },
          ],
          core_processes: ['开户审核'],
        },
      },
      ai_suggestions: {
        business_capabilities: {
          module_structure: [
            {
              module_name: '贷款开户放款',
              description: '顶层模块',
              functions: [{ name: '开户放款', desc: '处理开户放款' }],
            },
          ],
        },
      },
    });

    renderPage();

    fireEvent.click(await screen.findByRole('button', { name: 'D2 业务能力与流程' }));

    expect(await screen.findByText('模块结构')).toBeInTheDocument();
    expect(screen.queryByText('检测到 AI 建议变更')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '采纳新建议' })).not.toBeInTheDocument();
  }, 30000);

  it('keeps ignored D1 suggestion hidden after saving draft and reloading', async () => {
    renderPage();

    expect(await screen.findByText('系统描述')).toBeInTheDocument();
    expect(await screen.findByText('检测到 AI 建议变更')).toBeInTheDocument();

    const profileDetailCallsBeforeSave = axios.get.mock.calls.filter(([url]) => String(url).startsWith('/api/v1/system-profiles/')).length;

    fireEvent.click(screen.getByRole('button', { name: /忽\s*略/ }));

    await waitFor(() => {
      expect(axios.post).toHaveBeenCalledWith(
        '/api/v1/system-profiles/sys_alpha/profile/suggestions/ignore',
        { domain: 'system_positioning', sub_field: 'core_responsibility' }
      );
    });
    expect(screen.queryByRole('button', { name: '采纳新建议' })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /保存草稿/ }));

    await waitFor(() => {
      expect(axios.put).toHaveBeenCalledTimes(1);
    });
    await waitFor(() => {
      const profileDetailCallsAfterSave = axios.get.mock.calls.filter(([url]) => String(url).startsWith('/api/v1/system-profiles/')).length;
      expect(profileDetailCallsAfterSave).toBeGreaterThan(profileDetailCallsBeforeSave);
    });
    expect(screen.queryByRole('button', { name: '采纳新建议' })).not.toBeInTheDocument();
  }, 120000);

  it('keeps ignored D5 suggestion hidden after saving draft and reloading', async () => {
    setupAxiosMock({
      profile_data: {
        constraints_risks: {
          key_constraints: [{ category: '数据安全', description: '需要保证数据完整性' }],
          known_risks: ['OCR可用性'],
        },
      },
      ai_suggestions: {
        constraints_risks: {
          key_constraints: [{ category: '技术约束', description: '系统需基于阿里云平台开发。' }],
        },
      },
    });

    renderPage();

    fireEvent.click(await screen.findByRole('button', { name: 'D5 约束与风险' }));
    expect(await screen.findByText('关键约束')).toBeInTheDocument();
    expect(screen.getByText('检测到 AI 建议变更')).toBeInTheDocument();

    const profileDetailCallsBeforeSave = axios.get.mock.calls.filter(([url]) => String(url).startsWith('/api/v1/system-profiles/')).length;

    fireEvent.click(screen.getByRole('button', { name: /忽\s*略/ }));

    await waitFor(() => {
      expect(axios.post).toHaveBeenCalledWith(
        '/api/v1/system-profiles/sys_alpha/profile/suggestions/ignore',
        { domain: 'constraints_risks', sub_field: 'prerequisites' }
      );
    });
    expect(screen.queryByRole('button', { name: '采纳新建议' })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /保存草稿/ }));

    await waitFor(() => {
      expect(axios.put).toHaveBeenCalledTimes(1);
    });
    await waitFor(() => {
      const profileDetailCallsAfterSave = axios.get.mock.calls.filter(([url]) => String(url).startsWith('/api/v1/system-profiles/')).length;
      expect(profileDetailCallsAfterSave).toBeGreaterThan(profileDetailCallsBeforeSave);
    });
    expect(screen.queryByRole('button', { name: '采纳新建议' })).not.toBeInTheDocument();
  }, 120000);

  it('applies the preview-first flow to D3 fields and shows header actions', async () => {
    renderPage();

    fireEvent.click(await screen.findByRole('button', { name: 'D3 集成与接口' }));
    expect(await screen.findByText('集成点')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '编辑集成点' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '编辑对外提供能力' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '编辑对外依赖能力' })).toBeInTheDocument();
    expect(screen.queryByText('当前集成点')).not.toBeInTheDocument();
    expect(screen.queryAllByPlaceholderText('说明')).toHaveLength(0);
    fireEvent.click(screen.getByRole('button', { name: '编辑集成点' }));
    expect(screen.getAllByPlaceholderText('说明').length).toBeGreaterThan(0);
  }, 20000);

  it('applies the preview-first flow to D5 fields and shows header actions', async () => {
    renderPage();

    fireEvent.click(await screen.findByRole('button', { name: 'D5 约束与风险' }));
    expect(await screen.findByText('关键约束')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '编辑关键约束' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '编辑已知风险' })).toBeInTheDocument();
    expect(screen.queryByText('当前关键约束')).not.toBeInTheDocument();
    expect(screen.queryByText('当前已知风险')).not.toBeInTheDocument();
    expect(screen.queryAllByPlaceholderText('约束类别')).toHaveLength(0);
    expect(screen.queryAllByPlaceholderText('风险事项')).toHaveLength(0);
    fireEvent.click(screen.getByRole('button', { name: '编辑关键约束' }));
    expect(screen.getByPlaceholderText('约束类别')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '编辑已知风险' }));
    expect(screen.getByPlaceholderText('风险事项')).toBeInTheDocument();
  }, 20000);

  it('renders mixed diff previews for text list table and tree fields', () => {
    render(
      <>
        <StructuredFieldDiffPreview kind="text" currentValue="当前系统描述" suggestionValue="AI建议-系统描述" />
        <StructuredFieldDiffPreview
          kind="list"
          currentValue={['企业用户', '财务人员']}
          suggestionValue={['企业用户', '运营人员']}
        />
        <StructuredFieldDiffPreview
          kind="integration_points"
          currentValue={[{ peer_system: '核心账务', protocol: 'HTTP', direction: 'outbound', description: '同步开户' }]}
          suggestionValue={[{ peer_system: '核心账务', protocol: 'HTTP', direction: 'bidirectional', description: '同步开户' }]}
        />
        <StructuredFieldDiffPreview
          kind="module_structure"
          currentValue={[{ module_name: '开户', children: [{ module_name: '资料审核', children: [] }] }]}
          suggestionValue={[{ module_name: '开户', children: [{ module_name: '资料预审', children: [] }, { module_name: '风控校验', children: [] }] }]}
        />
      </>
    );

    expect(screen.getByText('当前值')).toBeInTheDocument();
    expect(screen.getByText('AI 建议')).toBeInTheDocument();
    expect(screen.getAllByText('+').length).toBeGreaterThan(0);
    expect(screen.getAllByText('-').length).toBeGreaterThan(0);
    expect(screen.getByText('财务人员')).toBeInTheDocument();
    expect(screen.getByText('运营人员')).toBeInTheDocument();
    expect(screen.getByText('表格变更')).toBeInTheDocument();
    expect(screen.getByText('⇄')).toBeInTheDocument();
    expect(screen.getByText('树形变更')).toBeInTheDocument();
    expect(screen.getByText('资料预审')).toBeInTheDocument();
    expect(screen.getByText('风控校验')).toBeInTheDocument();
  });

});
