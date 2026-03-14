import React from 'react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { fireEvent, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import MainLayout from '../components/MainLayout';
import DashboardRankingsPage from '../pages/DashboardRankingsPage';
import DashboardReportsPage from '../pages/DashboardReportsPage';
import CosmicConfigPage from '../pages/CosmicConfigPage';
import usePermission from '../hooks/usePermission';

jest.setTimeout(60000);

jest.mock('axios', () => ({
  get: jest.fn(),
  post: jest.fn(),
  put: jest.fn(),
  delete: jest.fn(),
}));
const axios = require('axios');

jest.mock('../hooks/useAuth', () => () => ({
  user: { displayName: '测试用户', username: 'tester' },
  logout: jest.fn(),
}));

jest.mock('../hooks/usePermission');

jest.mock('../hooks/useNotification', () => () => ({
  unread: 0,
  refreshUnread: jest.fn(),
}));

describe('navigation and page title regression', () => {
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
    axios.post.mockResolvedValue({ data: { result: { widgets: [] } } });
    axios.get.mockResolvedValue({ data: { data: {} } });
  });

  it('keeps sidebar order: task -> config -> dashboard for admin', () => {
    usePermission.mockReturnValue({
      roles: ['admin'],
      activeRole: 'admin',
      setActiveRole: jest.fn(),
      isAdmin: true,
      isManager: false,
      isExpert: false,
      isViewer: false,
    });

    render(
      <MemoryRouter initialEntries={['/dashboard/reports']}>
        <Routes>
          <Route path="/" element={<MainLayout />}>
            <Route path="dashboard/reports" element={<div>content</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    );

    const menuText = document.querySelector('.ant-menu')?.textContent || '';
    const taskPos = menuText.indexOf('任务管理');
    const configPos = menuText.indexOf('配置管理');
    const dashboardPos = menuText.indexOf('效能看板');

    expect(taskPos).toBeGreaterThan(-1);
    expect(configPos).toBeGreaterThan(-1);
    expect(dashboardPos).toBeGreaterThan(-1);
    expect(taskPos).toBeLessThan(configPos);
    expect(configPos).toBeLessThan(dashboardPos);
  });

  it('shows service governance under admin config menu and keeps subsystem entry removed', () => {
    usePermission.mockReturnValue({
      roles: ['admin'],
      activeRole: 'admin',
      setActiveRole: jest.fn(),
      isAdmin: true,
      isManager: false,
      isExpert: false,
      isViewer: false,
    });

    render(
      <MemoryRouter initialEntries={['/dashboard/reports']}>
        <Routes>
          <Route path="/" element={<MainLayout />}>
            <Route path="dashboard/reports" element={<div>content</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    );

    const menuText = document.querySelector('.ant-menu')?.textContent || '';
    expect(menuText).toContain('服务治理');
    expect(menuText).not.toContain('子系统');
  });

  it('keeps manager system profile entries aligned with v2.4 baseline only', () => {
    usePermission.mockReturnValue({
      roles: ['manager'],
      activeRole: 'manager',
      setActiveRole: jest.fn(),
      isAdmin: false,
      isManager: true,
      isExpert: false,
      isViewer: false,
    });

    render(
      <MemoryRouter initialEntries={['/system-profiles/board']}>
        <Routes>
          <Route path="/" element={<MainLayout />}>
            <Route path="system-profiles/board" element={<div>content</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    );

    const menuText = document.querySelector('.ant-menu')?.textContent || '';
    expect(menuText).toContain('系统画像');
    fireEvent.click(screen.getByText('系统画像'));

    const expandedMenuText = document.querySelector('.ant-menu')?.textContent || '';
    expect(expandedMenuText).toContain('知识导入');
    expect(expandedMenuText).toContain('信息展示');
    expect(expandedMenuText).not.toContain('代码扫描');
    expect(expandedMenuText).not.toContain('画像工作台');
  });

  it('renders a fixed shell so sidebar and content can scroll independently', () => {
    usePermission.mockReturnValue({
      roles: ['manager'],
      activeRole: 'manager',
      setActiveRole: jest.fn(),
      isAdmin: false,
      isManager: true,
      isExpert: false,
      isViewer: false,
    });

    const { container } = render(
      <MemoryRouter initialEntries={['/system-profiles/import']}>
        <Routes>
          <Route path="/" element={<MainLayout />}>
            <Route path="system-profiles/import" element={<div>content</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    );

    expect(container.querySelector('.app-shell')).toBeInTheDocument();
    expect(container.querySelector('.app-sider-menu')).toBeInTheDocument();
  });

  it('does not render redundant top-left title on rankings page', () => {
    render(<DashboardRankingsPage />);
    expect(screen.queryByText('排行榜')).not.toBeInTheDocument();
  });

  it('shows metric logic tips for all report sections on dashboard reports page', async () => {
    axios.post.mockImplementation(async () => ({
      data: {
        result: {
          widgets: [
            {
              widget_id: 'pm_correction_rate_ranking',
              data: { items: [{ system_id: 'S1', system_name: '系统A', correction_rate: 12.3, addition_rate: 4.5, sample_tasks: 5 }] },
            },
            {
              widget_id: 'ai_hit_rate_ranking',
              data: { items: [{ system_id: 'S1', system_name: '系统A', hit_rate: 80, profile_score: 75, sample_tasks: 5 }] },
            },
            {
              widget_id: 'profile_contribution_ranking',
              data: { items: [{ owner_name: '张三', contribution_score: 88, document_count: 10, systems_count: 3 }] },
            },
            {
              widget_id: 'evaluation_cycle_ranking',
              data: { items: [{ owner_name: '李四', avg_cycle_days: 6.5, sample_tasks: 4 }] },
            },
            {
              widget_id: 'ai_deviation_monitoring',
              data: { items: [{ system_id: 'S1', system_name: '系统A', avg_deviation_pct: 10.2, max_deviation_pct: 15.1, min_deviation_pct: 2.3 }] },
            },
            {
              widget_id: 'ai_learning_trend',
              data: { items: [{ system_id: 'S1', system_name: '系统A', trend: 'improving', first_correction_rate: 20.0, latest_correction_rate: 10.0 }] },
            },
          ],
        },
      },
    }));

    render(<DashboardReportsPage />);

    expect(await screen.findByText('修正率分析')).toBeInTheDocument();
    expect(screen.getByText('命中率分析')).toBeInTheDocument();
    expect(screen.getByText('画像贡献分析')).toBeInTheDocument();
    expect(screen.getByText('评估周期分析')).toBeInTheDocument();
    expect(screen.getByText('偏差监控分析')).toBeInTheDocument();
    expect(screen.getByText('学习趋势分析')).toBeInTheDocument();

    expect(screen.getByText(/看 PM 在 AI 初稿上改了多少/i)).toBeInTheDocument();
    expect(screen.getByText(/看 AI 估算是否接近最终结果/i)).toBeInTheDocument();
    expect(screen.getByText(/看系统画像资料对评估结果的支撑程度/i)).toBeInTheDocument();
    expect(screen.getByText(/看任务从创建到冻结平均用了多久/i)).toBeInTheDocument();
    expect(screen.getByText(/看 AI 与最终工时差了多少/i)).toBeInTheDocument();
    expect(screen.getByText(/看修正率是持续下降还是上升/i)).toBeInTheDocument();
  });

  it('renders summary metrics in compact single-line rows on dashboard reports page', async () => {
    axios.post.mockResolvedValue({
      data: {
        result: {
          widgets: [
            { widget_id: 'task_completion_overview', data: { task_count: 12, avg_final_days: 3.5 } },
            { widget_id: 'ai_involved_rate', data: { rate: 66.7, count: 8 } },
            { widget_id: 'flow_cycle_time', data: { avg_days: 4.2 } },
            { widget_id: 'flow_throughput', data: { completed_tasks: 10 } },
          ],
        },
      },
    });

    const { container } = render(<DashboardReportsPage />);

    expect(await screen.findByText('已完成任务数')).toBeInTheDocument();
    expect(screen.getByText('AI参与率')).toBeInTheDocument();
    expect(container.querySelector('.ant-statistic')).not.toBeInTheDocument();
  });

  it('does not render redundant top-left title on cosmic config page', () => {
    usePermission.mockReturnValue({
      isAdmin: true,
    });

    render(<CosmicConfigPage />);
    expect(screen.queryByRole('heading', { name: /估算规则配置/ })).not.toBeInTheDocument();
  });
});
