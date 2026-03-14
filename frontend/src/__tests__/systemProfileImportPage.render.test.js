import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import '@testing-library/jest-dom';
import { message } from 'antd';
import SystemProfileImportPage from '../pages/SystemProfileImportPage';

jest.setTimeout(120000);

jest.mock('axios', () => ({
  get: jest.fn(),
  post: jest.fn(),
}));
const axios = require('axios');

jest.mock('../hooks/useAuth', () => () => ({
  user: {
    id: 'u_pm1',
    username: 'pm1',
    displayName: '项目经理1',
  },
  token: 'token_pm1',
}));

jest.mock('../hooks/usePermission', () => () => ({
  isManager: true,
}));

const RESPONSIBLE_SYSTEM = {
  id: 'sys_pay',
  name: '支付系统',
  extra: { owner_username: 'pm1' },
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

const renderPage = () => render(
  <MemoryRouter initialEntries={['/system-profiles/import?system_name=支付系统&system_id=sys_pay']}>
    <SystemProfileImportPage />
  </MemoryRouter>
);

const uploadFileInCard = (title, fileName = 'demo.docx') => {
  const card = screen.getByText(title).closest('.ant-card');
  const input = card.querySelector('input[type="file"]');
  const file = new File(['demo'], fileName, { type: 'application/octet-stream' });
  fireEvent.change(input, { target: { files: [file] } });
  return file;
};

describe('SystemProfileImportPage v2.7', () => {
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
    axios.get.mockImplementation(async (url) => {
      if (url === '/api/v1/system/systems') {
        return { data: { data: { systems: [RESPONSIBLE_SYSTEM] } } };
      }
      if (url === '/api/v1/code-scan/jobs/') {
        return { data: null };
      }
      if (String(url).includes('/profile/import-history')) {
        return { data: { total: 0, items: [] } };
      }
      if (String(url).includes('/profile/execution-status')) {
        return {
          data: {
            execution_id: 'exec_latest_001',
            scene_id: 'pm_document_ingest',
            status: 'completed',
            created_at: '2026-03-13T12:00:00',
            completed_at: '2026-03-13T12:00:01',
            skill_chain: ['requirements_skill'],
            notifications: [],
            error: null,
          },
        };
      }
      return { data: {} };
    });
    axios.post.mockResolvedValue({
      data: {
        result_status: 'queued',
        execution_id: 'exec_req_001',
        scene_id: 'pm_document_ingest',
        execution_status: {
          status: 'completed',
          error: null,
        },
        import_result: {
          status: 'success',
          file_name: 'demo.docx',
          imported_at: '2026-03-13T12:00:00',
          failure_reason: null,
        },
      },
    });
  });

  afterEach(() => {
    cleanup();
  });

  it('renders only v2.7 document types while keeping code scan entry', async () => {
    renderPage();

    expect(await screen.findByText('代码扫描')).toBeInTheDocument();
    expect(screen.getByText('需求文档')).toBeInTheDocument();
    expect(screen.getByText('设计文档')).toBeInTheDocument();
    expect(screen.getByText('技术方案')).toBeInTheDocument();
    expect(screen.queryByText('历史评估报告')).not.toBeInTheDocument();
    expect(screen.queryByText('ESB服务治理文档')).not.toBeInTheDocument();
  });

  it('submits document imports through v2.7 profile import and refreshes execution status', async () => {
    renderPage();

    uploadFileInCard('需求文档');
    fireEvent.click(await screen.findByRole('button', { name: '导入需求文档' }));

    await waitFor(() => {
      expect(axios.post).toHaveBeenCalledWith(
        '/api/v1/system-profiles/sys_pay/profile/import',
        expect.any(FormData),
        expect.objectContaining({
          headers: { 'Content-Type': 'multipart/form-data' },
        }),
      );
    });

    await waitFor(() => {
      expect(axios.get).toHaveBeenCalledWith('/api/v1/system-profiles/sys_pay/profile/execution-status');
    });
  });

  it('hides raw execution metadata and shows readable import summaries', async () => {
    axios.get.mockImplementation(async (url) => {
      if (url === '/api/v1/system/systems') {
        return { data: { data: { systems: [RESPONSIBLE_SYSTEM] } } };
      }
      if (url === '/api/v1/code-scan/jobs/') {
        return { data: null };
      }
      if (String(url).includes('/profile/import-history')) {
        return {
          data: {
            total: 1,
            items: [
              {
                doc_type: 'tech_solution',
                status: 'success',
                file_name: 'req-temp1.docx',
                imported_at: '2026-03-14T13:57:29',
                execution_id: 'exec_hist_001',
              },
            ],
          },
        };
      }
      if (String(url).includes('/profile/execution-status')) {
        return {
          data: {
            execution_id: 'exec_latest_001',
            scene_id: 'pm_document_ingest',
            status: 'completed',
            created_at: '2026-03-14T13:57:20',
            completed_at: '2026-03-14T13:57:29',
            skill_chain: ['tech_solution_skill'],
            notifications: [],
            error: null,
          },
        };
      }
      return { data: {} };
    });

    renderPage();

    expect(await screen.findByText('最近一次处理已完成')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.getAllByText('技术方案').length).toBeGreaterThan(0);
    expect(screen.getByText('req-temp1.docx')).toBeInTheDocument();
    expect(screen.queryByText(/execution_id/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/scene/i)).not.toBeInTheDocument();
    expect(screen.queryByText('pm_document_ingest')).not.toBeInTheDocument();
    expect(screen.queryByText('tech_solution')).not.toBeInTheDocument();

    uploadFileInCard('需求文档');
    fireEvent.click(screen.getByRole('button', { name: '导入需求文档' }));

    expect(await screen.findByText('demo.docx 已导入，可前往信息展示查看建议。')).toBeInTheDocument();
    expect(screen.queryByText('本次导入结果')).not.toBeInTheDocument();
    expect(screen.queryByText('completed')).not.toBeInTheDocument();
  });
});
