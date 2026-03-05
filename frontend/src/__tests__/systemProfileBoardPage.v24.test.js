import React from 'react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import '@testing-library/jest-dom';
import SystemProfileBoardPage from '../pages/SystemProfileBoardPage';

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
  logout: jest.fn(),
}));

jest.mock('../hooks/usePermission', () => () => ({
  isManager: true,
}));

const createProfilePayload = () => ({
  status: 'draft',
  pending_fields: [],
  updated_at: '2026-03-01T10:00:00',
  is_stale: false,
  system_id: 'sys_alpha',
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
  },
  ai_suggestions: {
    system_positioning: {
      system_description: 'AI建议-系统描述',
      target_users: ['企业用户'],
      boundaries: ['仅覆盖开户流程'],
    },
  },
  ai_suggestions_previous: null,
});

const createEmptyProfileData = () => ({
  system_positioning: {
    system_description: '',
    target_users: [],
    boundaries: [],
  },
  business_capabilities: {
    module_structure: [],
    core_processes: [],
  },
  integration_interfaces: {
    integration_points: [],
    external_dependencies: [],
  },
  technical_architecture: {
    architecture_positioning: '',
    tech_stack: [],
    performance_profile: {},
  },
  constraints_risks: {
    key_constraints: [],
    known_risks: [],
  },
});

const createEvents = (count) => (
  Array.from({ length: count }).map((_, index) => ({
    event_id: `evt_${index + 1}`,
    event_type: 'document_import',
    timestamp: `2026-03-01T10:${String(index).padStart(2, '0')}:00`,
    source: '需求文档',
    summary: `事件${index + 1}`,
  }))
);

const setupAxiosMock = ({ profileOverrides = {}, eventPages = [], systemsOverride } = {}) => {
  const profile = { ...createProfilePayload(), ...profileOverrides };
  const systems = Array.isArray(systemsOverride) && systemsOverride.length > 0
    ? systemsOverride
    : [
      {
        id: 'sys_alpha',
        name: '系统A',
        status: 'active',
        extra: {
          owner_username: 'tester',
        },
      },
    ];

  axios.get.mockImplementation((url, config = {}) => {
    if (url === '/api/v1/system/systems') {
      return Promise.resolve({
        data: {
          data: {
            systems,
          },
        },
      });
    }

    if (url === '/api/v1/system-profiles/completeness') {
      return Promise.resolve({
        data: {
          exists: true,
          completeness_score: 88,
          breakdown: {
            code_scan: 30,
            documents: 40,
            esb: 18,
          },
        },
      });
    }

    if (url.startsWith('/api/v1/system-profiles/') && url.includes('/profile/events')) {
      const offset = Number(config?.params?.offset || 0);
      const hit = eventPages.find((item) => item.offset === offset);
      return Promise.resolve({
        data: hit ? hit.payload : { total: 0, items: [] },
      });
    }

    if (url.includes('/api/v1/system-profiles/')) {
      return Promise.resolve({
        data: {
          code: 200,
          data: profile,
        },
      });
    }

    return Promise.resolve({ data: {} });
  });
};

const renderPage = () => render(
  <MemoryRouter initialEntries={['/system-profiles/board?system_name=系统A&system_id=sys_alpha']}>
    <Routes>
      <Route path="/system-profiles/board" element={<SystemProfileBoardPage />} />
    </Routes>
  </MemoryRouter>
);

describe('SystemProfileBoardPage v2.4', () => {
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
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: (query) => createMatchMediaResult(query),
    });
  });

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders three-zone board with domain navigation', async () => {
    setupAxiosMock({ eventPages: [{ offset: 0, payload: { total: 0, items: [] } }] });

    renderPage();

    expect((await screen.findAllByText('D1 系统定位与边界')).length).toBeGreaterThan(0);
    expect(screen.getByText('D2 业务能力与流程')).toBeInTheDocument();
    expect(screen.getByText('D3 集成与接口')).toBeInTheDocument();
    expect(screen.getByText('D4 技术架构')).toBeInTheDocument();
    expect(screen.getByText('D5 约束与风险')).toBeInTheDocument();
  });

  it('does not duplicate active domain title in content area', async () => {
    setupAxiosMock({ eventPages: [{ offset: 0, payload: { total: 0, items: [] } }] });

    renderPage();

    await screen.findByText('保存草稿');
    expect(screen.getAllByText('D1 系统定位与边界')).toHaveLength(1);
  });

  it('left-aligns domain navigation buttons', async () => {
    setupAxiosMock({ eventPages: [{ offset: 0, payload: { total: 0, items: [] } }] });

    renderPage();

    await screen.findByText('保存草稿');
    const domainButton = screen.getByRole('button', { name: /D2 业务能力与流程/ });
    expect(domainButton).toHaveStyle({ justifyContent: 'flex-start', textAlign: 'left' });
  });

  it('removes redundant section header navigation labels', async () => {
    setupAxiosMock({ eventPages: [{ offset: 0, payload: { total: 0, items: [] } }] });

    renderPage();

    await screen.findByText('保存草稿');
    expect(screen.queryByText('域导航')).not.toBeInTheDocument();
    expect(screen.queryByText('要素内容')).not.toBeInTheDocument();
  });

  it('shows timeline empty state when no profile events', async () => {
    setupAxiosMock({ eventPages: [{ offset: 0, payload: { total: 0, items: [] } }] });

    renderPage();

    expect(await screen.findByText('暂无变更记录')).toBeInTheDocument();
  });

  it('supports timeline pagination via load more', async () => {
    setupAxiosMock({
      eventPages: [
        { offset: 0, payload: { total: 25, items: createEvents(20) } },
        { offset: 20, payload: { total: 25, items: createEvents(5).map((item) => ({ ...item, event_id: `${item.event_id}_p2` })) } },
      ],
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText('加载更多')).toBeInTheDocument();
    }, { timeout: 5000 });

    const loadMoreButton = screen.getByText('加载更多').closest('button');
    expect(loadMoreButton).not.toBeNull();
    fireEvent.click(loadMoreButton);

    await waitFor(() => {
      const eventCalls = axios.get.mock.calls.filter(([url]) => String(url).includes('/profile/events'));
      expect(eventCalls.length).toBe(2);
      expect(eventCalls[1][1]?.params?.offset).toBe(20);
      expect(eventCalls[1][1]?.params?.limit).toBe(20);
    });
  });

  it('prefers current system id from system list when profile carries stale system_id', async () => {
    setupAxiosMock({
      profileOverrides: {
        system_id: 'legacy_profile_id',
      },
      eventPages: [{ offset: 0, payload: { total: 0, items: [] } }],
      systemsOverride: [
        {
          id: 'sys_alpha',
          name: '系统A',
          status: 'active',
          extra: {
            owner_username: 'tester',
          },
        },
      ],
    });

    renderPage();

    await waitFor(() => {
      const eventCalls = axios.get.mock.calls.filter(([url]) => String(url).includes('/profile/events'));
      expect(eventCalls.length).toBeGreaterThan(0);
      expect(String(eventCalls[0][0])).toContain('/api/v1/system-profiles/sys_alpha/profile/events');
      expect(String(eventCalls[0][0])).not.toContain('/api/v1/system-profiles/legacy_profile_id/profile/events');
    }, { timeout: 8000 });
  }, 12000);

  it('disables rollback button when ai_suggestions_previous is missing', async () => {
    setupAxiosMock({ eventPages: [{ offset: 0, payload: { total: 0, items: [] } }] });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText('恢复上一版建议')).toBeInTheDocument();
    }, { timeout: 5000 });

    const rollbackButton = screen.getByText('恢复上一版建议').closest('button');
    expect(rollbackButton).not.toBeNull();
    expect(rollbackButton).toBeDisabled();
  });

  it('shows empty-state guidance when user has no responsible systems', async () => {
    setupAxiosMock({
      eventPages: [{ offset: 0, payload: { total: 0, items: [] } }],
      systemsOverride: [
        {
          id: 'sys_alpha',
          name: '系统A',
          status: 'active',
          extra: {
            owner_username: 'another_pm',
          },
        },
      ],
    });

    renderPage();

    expect(await screen.findByText('暂无可操作系统（仅展示主责/B角系统）。请联系管理员维护系统负责关系。')).toBeInTheDocument();
    expect(screen.queryByText('保存草稿')).not.toBeInTheDocument();
    expect(screen.queryByText('发布画像')).not.toBeInTheDocument();
  });

  it('shows only systems where current user is owner or backup owner', async () => {
    setupAxiosMock({
      eventPages: [{ offset: 0, payload: { total: 0, items: [] } }],
      systemsOverride: [
        {
          id: 'sys_alpha',
          name: '系统A',
          status: 'active',
          extra: {
            owner_username: 'tester',
          },
        },
        {
          id: 'sys_beta',
          name: '系统B',
          status: 'active',
          extra: {
            owner_username: 'another_pm',
          },
        },
      ],
    });

    renderPage();

    expect(await screen.findByText('保存草稿')).toBeInTheDocument();
    expect(screen.getByText('系统A')).toBeInTheDocument();
    expect(screen.queryByText('系统B')).not.toBeInTheDocument();
  });

  it('renders empty editors for all domain fields when profile is not imported', async () => {
    setupAxiosMock({
      profileOverrides: {
        profile_data: createEmptyProfileData(),
      },
      eventPages: [{ offset: 0, payload: { total: 0, items: [] } }],
    });

    renderPage();

    expect(await screen.findByPlaceholderText('请输入目标用户')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('请输入边界说明')).toBeInTheDocument();

    const navButton = screen.getByRole('button', { name: /D2 业务能力与流程/ });
    const navCard = navButton.closest('.ant-card');
    expect(navCard).not.toBeNull();
    const nav = within(navCard);

    fireEvent.click(nav.getByRole('button', { name: /D2 业务能力与流程/ }));
    expect(await screen.findByPlaceholderText('模块名称')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('请输入核心流程')).toBeInTheDocument();
  }, 12000);

  it('uses human-readable editors instead of raw json textarea', async () => {
    setupAxiosMock({ eventPages: [{ offset: 0, payload: { total: 0, items: [] } }] });

    renderPage();

    expect(await screen.findByText('保存草稿')).toBeInTheDocument();
    expect(screen.queryByText(/请输入合法 JSON/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/JSON 格式不合法/i)).not.toBeInTheDocument();
    expect(screen.getByPlaceholderText('请输入目标用户')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('请输入边界说明')).toBeInTheDocument();
    expect(screen.queryByText('新增目标用户')).not.toBeInTheDocument();
    expect(screen.queryByText('新增边界说明')).not.toBeInTheDocument();
    expect(screen.queryByText('删除')).not.toBeInTheDocument();
  });

  it('does not show suggestion diff for module_structure when only last_updated differs', async () => {
    setupAxiosMock({
      profileOverrides: {
        profile_data: {
          ...createProfilePayload().profile_data,
          business_capabilities: {
            module_structure: [
              {
                module_name: '开户',
                functions: [{ name: '证件校验', desc: 'OCR' }],
                last_updated: '2026-03-05T10:00:00',
              },
            ],
            core_processes: ['开户审核'],
          },
        },
        ai_suggestions: {
          business_capabilities: {
            module_structure: [
              {
                module_name: '开户',
                functions: [{ name: '证件校验', desc: 'OCR' }],
              },
            ],
          },
        },
      },
      eventPages: [{ offset: 0, payload: { total: 0, items: [] } }],
    });

    renderPage();
    await screen.findByText('保存草稿');
    fireEvent.click(screen.getByRole('button', { name: /D2 业务能力与流程/ }));

    await screen.findByDisplayValue('开户');
    expect(screen.queryByText('检测到 AI 建议变更')).not.toBeInTheDocument();
  }, 60000);

  it('keeps ignored suggestion hidden after saving draft', async () => {
    setupAxiosMock({ eventPages: [{ offset: 0, payload: { total: 0, items: [] } }] });
    axios.put.mockResolvedValue({ data: { code: 200 } });
    axios.post.mockResolvedValue({ data: { code: 200, data: createProfilePayload() } });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText('检测到 AI 建议变更')).toBeInTheDocument();
    }, { timeout: 5000 });
    const ignoreButton = screen.getByText(/忽\s*略/).closest('button');
    expect(ignoreButton).not.toBeNull();
    fireEvent.click(ignoreButton);

    await waitFor(() => {
      expect(axios.post).toHaveBeenCalledTimes(1);
      expect(String(axios.post.mock.calls[0][0])).toContain('/profile/suggestions/ignore');
    });

    await waitFor(() => {
      expect(screen.queryByText('检测到 AI 建议变更')).not.toBeInTheDocument();
    });

    const saveButton = screen.getByText('保存草稿').closest('button');
    expect(saveButton).not.toBeNull();
    fireEvent.click(saveButton);

    await waitFor(() => {
      const activeSaveButton = screen.getByText('保存草稿').closest('button');
      expect(activeSaveButton).not.toBeNull();
      expect(activeSaveButton).toHaveClass('ant-btn-loading');
    });

    await waitFor(() => {
      const activeSaveButton = screen.getByText('保存草稿').closest('button');
      expect(activeSaveButton).not.toBeNull();
      expect(activeSaveButton).not.toHaveClass('ant-btn-loading');
    });

    await waitFor(() => {
      expect(axios.put).toHaveBeenCalledTimes(1);
    });

    await waitFor(() => {
      expect(screen.queryByText('检测到 AI 建议变更')).not.toBeInTheDocument();
    });
  }, 20000);

});
