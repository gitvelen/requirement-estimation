import React from 'react';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { message } from 'antd';
import { MemoryRouter } from 'react-router-dom';
import SystemProfileBoardPage from '../pages/SystemProfileBoardPage';
import SystemProfileImportPage from '../pages/SystemProfileImportPage';
import TaskListPage from '../pages/TaskListPage';

jest.mock('axios', () => ({
  get: jest.fn(),
  post: jest.fn(),
  put: jest.fn(),
  delete: jest.fn(),
}));

jest.mock('../hooks/useAuth', () => jest.fn(() => ({
  user: { username: 'admin', displayName: 'Admin', roles: ['admin'] },
})));

jest.mock('../hooks/usePermission', () => jest.fn(() => ({
  activeRole: 'admin',
  isAdmin: true,
  isManager: false,
  isExpert: false,
  isViewer: false,
  roles: ['admin'],
  setActiveRole: jest.fn(),
})));

const axios = require('axios');
const useAuth = require('../hooks/useAuth');
const usePermission = require('../hooks/usePermission');

const renderWithRouter = (ui, initialEntry = '/') => render(
  <MemoryRouter initialEntries={[initialEntry]}>
    {ui}
  </MemoryRouter>
);

describe('menu request lifecycle', () => {
  beforeAll(() => {
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: (query) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: () => {},
        removeListener: () => {},
        addEventListener: () => {},
        removeEventListener: () => {},
        dispatchEvent: () => false,
      }),
    });
  });

  beforeEach(() => {
    jest.clearAllMocks();
    jest.spyOn(message, 'error').mockImplementation(() => {});
    jest.spyOn(message, 'success').mockImplementation(() => {});
    jest.spyOn(message, 'warning').mockImplementation(() => {});
    jest.spyOn(message, 'info').mockImplementation(() => {});
    useAuth.mockImplementation(() => ({
      user: { username: 'admin', displayName: 'Admin', roles: ['admin'] },
    }));
    usePermission.mockImplementation(() => ({
      activeRole: 'admin',
      isAdmin: true,
      isManager: false,
      isExpert: false,
      isViewer: false,
      roles: ['admin'],
      setActiveRole: jest.fn(),
    }));
  });

  afterEach(() => {
    cleanup();
    jest.restoreAllMocks();
  });

  it('aborts in-flight board profile detail requests after unmount', async () => {
    let profileDetailSignal;

    axios.get.mockImplementation((url, config = {}) => {
      if (url === '/api/v1/system/systems') {
        return Promise.resolve({
          data: {
            data: {
              systems: [{ id: 'SYS-001', name: '支付系统' }],
            },
          },
        });
      }
      if (url === `/api/v1/system-profiles/${encodeURIComponent('支付系统')}`) {
        profileDetailSignal = config.signal;
        return new Promise(() => {});
      }
      return Promise.resolve({ data: {} });
    });

    const { unmount } = renderWithRouter(
      <SystemProfileBoardPage />,
      '/system-profiles/board?system_name=支付系统&system_id=SYS-001'
    );

    await waitFor(() => {
      expect(profileDetailSignal).toBeDefined();
    });

    expect(profileDetailSignal.aborted).toBe(false);
    unmount();
    expect(profileDetailSignal.aborted).toBe(true);
  });

  it('aborts import history and execution status requests after unmount', async () => {
    let historySignal;
    let executionSignal;

    useAuth.mockImplementation(() => ({
      user: { username: 'manager_user', displayName: 'Manager', roles: ['manager'] },
    }));
    usePermission.mockImplementation(() => ({
      activeRole: 'manager',
      isAdmin: false,
      isManager: true,
      isExpert: false,
      isViewer: false,
      roles: ['manager'],
      setActiveRole: jest.fn(),
    }));

    axios.get.mockImplementation((url, config = {}) => {
      if (url === '/api/v1/system/systems') {
        return Promise.resolve({
          data: {
            data: {
              systems: [],
            },
          },
        });
      }
      if (url === `/api/v1/system-profiles/${encodeURIComponent('SYS-001')}/profile/import-history`) {
        historySignal = config.signal;
        return new Promise(() => {});
      }
      if (url === `/api/v1/system-profiles/${encodeURIComponent('SYS-001')}/profile/execution-status`) {
        executionSignal = config.signal;
        return new Promise(() => {});
      }
      return Promise.resolve({ data: {} });
    });

    const { unmount } = renderWithRouter(
      <SystemProfileImportPage />,
      '/system-profiles/import?system_name=支付系统&system_id=SYS-001'
    );

    await waitFor(() => {
      expect(historySignal).toBeDefined();
      expect(executionSignal).toBeDefined();
    });

    expect(historySignal.aborted).toBe(false);
    expect(executionSignal.aborted).toBe(false);
    unmount();
    expect(historySignal.aborted).toBe(true);
    expect(executionSignal.aborted).toBe(true);
  });

  it('passes AbortSignal to task list queries and keeps canceled requests silent', async () => {
    axios.get.mockRejectedValue({ code: 'ERR_CANCELED', name: 'CanceledError' });

    renderWithRouter(<TaskListPage />, '/tasks');

    await waitFor(() => {
      expect(axios.get).toHaveBeenCalledWith(
        '/api/v1/tasks',
        expect.objectContaining({
          params: expect.objectContaining({
            group_by_status: true,
            page: 1,
            page_size: 20,
            scope: 'all',
          }),
          signal: expect.any(Object),
        })
      );
    });

    await waitFor(() => {
      expect(screen.queryByText('获取任务列表失败')).not.toBeInTheDocument();
    });
  });
});
