import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { message } from 'antd';
import ServiceGovernancePage from '../pages/ServiceGovernancePage';

jest.setTimeout(120000);

jest.mock('axios', () => ({
  post: jest.fn(),
  get: jest.fn(),
}));
const axios = require('axios');

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
});
