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

describe('SystemProfileImportPage batch import', () => {
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
      if (String(url).includes('/api/v1/code-scan/jobs/')) {
        return { data: null };
      }
      return { data: {} };
    });
    axios.post.mockResolvedValue({
      data: {
        result_status: 'queued',
        execution_id: 'exec_batch_001',
        scene_id: 'pm_document_ingest',
        execution_status: {
          status: 'completed',
          error: null,
        },
        import_result: {
          status: 'success',
          file_name: 'batch.zip',
          imported_at: '2026-03-13T12:00:00',
          failure_reason: null,
        },
      },
    });
  });

  afterEach(() => {
    cleanup();
  });

  it('renders a single batch import entry instead of per-doc-type cards', async () => {
    renderPage();

    expect(await screen.findByText('文档导入')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '选择文档文件' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '批量导入文档' })).toBeInTheDocument();
    expect(screen.queryByText('需求文档')).not.toBeInTheDocument();
    expect(screen.queryByText('设计文档')).not.toBeInTheDocument();
    expect(screen.queryByText('技术方案')).not.toBeInTheDocument();
  });

  it('submits selected files through batch import API', async () => {
    renderPage();

    const importCard = screen.getByText('文档导入').closest('.ant-card');
    const input = importCard.querySelector('input[type="file"]');
    const reqFile = new File(['req'], 'requirements.docx', { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' });
    const designFile = new File(['design'], 'design.docx', { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' });
    fireEvent.change(input, { target: { files: [reqFile, designFile] } });

    fireEvent.click(await screen.findByRole('button', { name: '批量导入文档' }));

    await waitFor(() => {
      expect(axios.post).toHaveBeenCalledWith(
        '/api/v1/system-profiles/sys_pay/profile/import-batch',
        expect.any(FormData),
        expect.objectContaining({
          headers: { 'Content-Type': 'multipart/form-data' },
        }),
      );
    });
  });

  it('allows legacy doc files in batch import selection', async () => {
    renderPage();

    const importCard = screen.getByText('文档导入').closest('.ant-card');
    const input = importCard.querySelector('input[type="file"]');
    const legacyFile = new File(['legacy'], 'requirements.doc', { type: 'application/msword' });
    fireEvent.change(input, { target: { files: [legacyFile] } });

    fireEvent.click(await screen.findByRole('button', { name: '批量导入文档' }));

    await waitFor(() => {
      expect(axios.post).toHaveBeenCalledWith(
        '/api/v1/system-profiles/sys_pay/profile/import-batch',
        expect.any(FormData),
        expect.objectContaining({
          headers: { 'Content-Type': 'multipart/form-data' },
        }),
      );
    });
  });
});
