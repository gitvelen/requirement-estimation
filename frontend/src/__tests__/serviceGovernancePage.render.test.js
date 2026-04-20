import React from 'react';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { message } from 'antd';
import ServiceGovernancePage from '../pages/ServiceGovernancePage';

jest.mock('../hooks/useAuth', () => jest.fn(() => ({
  user: { username: 'admin', roles: ['admin'] },
})));

jest.mock('../hooks/usePermission', () => jest.fn(() => ({
  isAdmin: true,
  activeRole: 'admin',
  roles: ['admin'],
  setActiveRole: jest.fn(),
})));

jest.setTimeout(120000);

jest.mock('axios', () => ({
  post: jest.fn(),
  get: jest.fn(),
}));
const axios = require('axios');
const useAuth = require('../hooks/useAuth');
const usePermission = require('../hooks/usePermission');

const renderAsAdmin = (username = 'admin', displayName = username) => {
  useAuth.mockImplementation(() => ({
    user: { username, displayName, roles: ['admin'] },
  }));
  usePermission.mockImplementation(() => ({
    isAdmin: true,
    activeRole: 'admin',
    roles: ['admin'],
    setActiveRole: jest.fn(),
  }));
  return render(<ServiceGovernancePage />);
};

const renderAsManager = () => {
  useAuth.mockImplementation(() => ({
    user: { username: 'manager_user', roles: ['manager'] },
  }));
  usePermission.mockImplementation(() => ({
    isAdmin: false,
    isManager: true,
    activeRole: 'manager',
    roles: ['manager'],
    setActiveRole: jest.fn(),
  }));
  return render(<ServiceGovernancePage />);
};

describe('ServiceGovernancePage', () => {
  beforeAll(() => {
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
    jest.useRealTimers();
    useAuth.mockImplementation(() => ({
      user: { username: 'admin', roles: ['admin'] },
    }));
    usePermission.mockImplementation(() => ({
      isAdmin: true,
      isManager: false,
      activeRole: 'admin',
      roles: ['admin'],
      setActiveRole: jest.fn(),
    }));
    axios.post.mockResolvedValue({
      data: {
        status: 'completed',
        execution_id: 'exec_governance_001',
        matched_count: 2,
        unmatched_count: 1,
        updated_system_ids: ['SYS-001', 'SYS-002'],
        updated_systems: [
          { system_id: 'SYS-001', system_name: '统一支付平台' },
          { system_id: 'SYS-002', system_name: '信贷核心' },
        ],
        unmatched_items: [
          {
            system_name: '未知系统',
            service_name: '测试服务',
            reason: 'system_not_found',
          },
        ],
      },
    });
  });

  afterEach(() => {
    cleanup();
  });

  it('shows metadata governance toolbar for admin whose display name is esb', () => {
    renderAsAdmin('admin', 'esb');

    expect(screen.getByRole('button', { name: '元数据治理' })).toBeInTheDocument();
    expect(screen.getByDisplayValue('0.80')).toBeInTheDocument();
    expect(screen.getByText('现在')).toBeInTheDocument();
    expect(screen.getByText('新增')).toBeInTheDocument();
  });

  it('loads persisted metadata governance config for admin whose display name is esb', async () => {
    axios.get.mockResolvedValueOnce({
      data: {
        similarity_threshold: 0.91,
        execution_time: 'daily_23',
        match_scope: 'all',
      },
    });
    // Second call: /jobs/latest (returns no active job)
    axios.get.mockResolvedValueOnce({
      data: { job_id: null, status: null },
    });

    renderAsAdmin('admin', 'esb');

    await waitFor(() => {
      expect(axios.get).toHaveBeenCalledWith('/api/v1/esb/metadata-governance/config');
    });
    await waitFor(() => {
      expect(axios.get).toHaveBeenCalledWith('/api/v1/esb/metadata-governance/jobs/latest');
    });
  });

  it('hides metadata governance toolbar for non-esb admin', () => {
    renderAsAdmin('other-admin');

    expect(screen.queryByRole('button', { name: '元数据治理' })).not.toBeInTheDocument();
    expect(screen.queryByDisplayValue('0.80')).not.toBeInTheDocument();
  });

  it('hides metadata governance toolbar for non-admin users', () => {
    renderAsManager();

    expect(screen.queryByRole('button', { name: '元数据治理' })).not.toBeInTheDocument();
  });

  it('uses compact layout and shows matched, unmatched and updated systems', async () => {
    render(<ServiceGovernancePage />);

    expect(screen.queryByText('服务治理导入')).not.toBeInTheDocument();
    expect(screen.queryByText('导入说明')).not.toBeInTheDocument();
    expect(
      screen.getByText('导入服务治理清单后，系统会按标准系统名匹配并联动更新画像；未匹配项会保留在结果区。'),
    ).toBeInTheDocument();

    const input = document.querySelector('input[type="file"]');
    const file = new File(['governance'], 'governance.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });
    fireEvent.change(input, { target: { files: [file] } });

    fireEvent.click(screen.getByRole('button', { name: '开始导入' }));

    await waitFor(() => {
      expect(axios.post).toHaveBeenCalledWith(
        '/api/v1/esb/imports',
        expect.any(FormData),
        expect.objectContaining({
          headers: { 'Content-Type': 'multipart/form-data' },
        }),
      );
    });

    expect(await screen.findByText('匹配成功 2 条')).toBeInTheDocument();
    expect(screen.getByText('未匹配 1 条')).toBeInTheDocument();
    expect(screen.queryByText(/execution_id/i)).not.toBeInTheDocument();
    expect(screen.getByText('统一支付平台')).toBeInTheDocument();
    expect(screen.getByText('信贷核心')).toBeInTheDocument();
    expect(screen.queryByText('SYS-001')).not.toBeInTheDocument();
    expect(screen.queryByText('SYS-002')).not.toBeInTheDocument();
    expect(screen.getByText('未知系统')).toBeInTheDocument();
    expect(screen.getByText('system_not_found')).toBeInTheDocument();
  });

  it('shows backend error message instead of generic import failed text', async () => {
    axios.post.mockRejectedValueOnce({
      response: {
        data: {
          error_code: 'ESB_002',
          message: 'ESB文件缺少必填字段：system_id',
          details: {
            reason: '未启用服务治理全局导入',
          },
        },
      },
    });

    render(<ServiceGovernancePage />);

    const input = document.querySelector('input[type="file"]');
    const file = new File(['governance'], 'governance.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });
    fireEvent.change(input, { target: { files: [file] } });
    fireEvent.click(screen.getByRole('button', { name: '开始导入' }));

    await waitFor(() => {
      expect(message.error).toHaveBeenCalledWith('ESB文件缺少必填字段：system_id：未启用服务治理全局导入');
    });
  });

  it('stops metadata governance polling after unmount', async () => {
    jest.useFakeTimers();
    axios.get.mockImplementation((url) => {
      if (url === '/api/v1/esb/metadata-governance/config') {
        return Promise.resolve({
          data: {
            similarity_threshold: 0.8,
            execution_time: 'now',
            match_scope: 'new',
          },
        });
      }
      if (url === '/api/v1/esb/metadata-governance/jobs/latest') {
        return Promise.resolve({
          data: {
            job_id: null,
            status: null,
          },
        });
      }
      if (url === '/api/v1/esb/metadata-governance/jobs/job-001') {
        return Promise.resolve({
          data: {
            status: 'running',
          },
        });
      }
      return Promise.resolve({ data: {} });
    });
    axios.post.mockResolvedValueOnce({
      data: {
        scheduled: false,
        job_id: 'job-001',
      },
    });

    const { unmount } = renderAsAdmin('admin', 'esb');

    fireEvent.click(await screen.findByRole('button', { name: '元数据治理' }));

    await waitFor(() => {
      expect(axios.post).toHaveBeenCalledWith(
        '/api/v1/esb/metadata-governance/run',
        {
          similarity_threshold: 0.8,
          execution_time: 'now',
          match_scope: 'new',
        },
      );
    });

    const callCountBeforeUnmount = axios.get.mock.calls.length;
    unmount();

    await act(async () => {
      jest.advanceTimersByTime(9000);
      await Promise.resolve();
    });

    expect(axios.get.mock.calls.length).toBe(callCountBeforeUnmount);
  });
});
