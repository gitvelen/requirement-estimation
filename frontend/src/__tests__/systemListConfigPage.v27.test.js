import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { message } from 'antd';
import SystemListConfigPage from '../pages/SystemListConfigPage';

jest.setTimeout(120000);

jest.mock('axios', () => ({
  get: jest.fn(),
  post: jest.fn(),
}));
const axios = require('axios');

jest.mock('../pages/MainSystemConfigPage', () => () => (
  <div data-testid="main-system-config-page">main-system-config-page</div>
));

describe('SystemListConfigPage v2.7', () => {
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
    axios.get.mockResolvedValue({
      data: {
        data: {
          systems: [],
        },
      },
    });
    axios.post.mockImplementation(async (url) => {
      if (url === '/api/v1/system-list/batch-import') {
        return {
          data: {
            code: 200,
            data: {
              systems: [
                {
                  name: '支付系统',
                  abbreviation: 'PAY',
                  status: '运行中',
                  errors: [],
                },
              ],
              summary: {
                systems_total: 1,
                systems_error: 0,
              },
            },
          },
        };
      }
      if (url === '/api/v1/system-list/batch-import/confirm') {
        return {
          data: {
            code: 200,
            message: 'success',
            result_status: 'partial_success',
            execution_id: 'exec_catalog_001',
            catalog_import_result: {
              preview_errors: [
                {
                  row_number: 3,
                  system_name: '老营销系统',
                  abbreviation: '',
                  errors: ['英文简称不能为空'],
                },
              ],
              updated_systems: [
                { system_id: 'SYS-001', system_name: '支付系统' },
              ],
              updated_system_ids: ['SYS-001'],
              skipped_items: [
                { system_name: 'CRM', reason: 'profile_not_blank' },
              ],
              errors: [],
            },
          },
        };
      }
      return { data: {} };
    });
  });

  afterEach(() => {
    cleanup();
  });

  it('removes subsystem tabs and shows catalog update result after confirm', async () => {
    render(<SystemListConfigPage />);

    expect(screen.queryByText('主系统清单')).not.toBeInTheDocument();
    expect(screen.queryByText('子系统映射')).not.toBeInTheDocument();
    expect(screen.getByTestId('main-system-config-page')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '批量导入（XLSX）' }));

    const input = document.querySelector('input[type="file"]');
    const file = new File(['catalog'], 'syslist.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });
    fireEvent.change(input, { target: { files: [file] } });

    expect(screen.queryByText('批量导入系统清单（XLSX）')).not.toBeInTheDocument();
    expect(
      screen.getByText('请使用最新系统清单模板；preview 仅校验，confirm 才会写入并按空画像规则联动初始化。'),
    ).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '解析文件' })).not.toBeInTheDocument();
    expect(await screen.findByText('支付系统')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '确认导入' }));

    expect(await screen.findByText('画像联动结果')).toBeInTheDocument();
    expect(screen.getByText('支付系统')).toBeInTheDocument();
    expect(screen.queryByText('SYS-001')).not.toBeInTheDocument();
    expect(screen.getByText('CRM')).toBeInTheDocument();
    expect(screen.getByText('画像已有内容，已跳过初始化')).toBeInTheDocument();
    expect(screen.queryByText('profile_not_blank')).not.toBeInTheDocument();
    expect(screen.getByText('老营销系统')).toBeInTheDocument();
    expect(screen.getByText('第 3 行')).toBeInTheDocument();
    expect(screen.getByText('英文简称不能为空')).toBeInTheDocument();

    await waitFor(() => {
      expect(axios.post).toHaveBeenCalledWith(
        '/api/v1/system-list/batch-import/confirm',
        expect.objectContaining({
          systems: expect.any(Array),
        }),
      );
    });
  });
});
