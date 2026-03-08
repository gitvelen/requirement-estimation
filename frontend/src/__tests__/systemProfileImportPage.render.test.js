import React from 'react';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import '@testing-library/jest-dom';
import { message } from 'antd';
import SystemProfileImportPage from '../pages/SystemProfileImportPage';

jest.setTimeout(60000);

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
  id: '1',
  name: '支付系统',
  extra: { owner_username: 'pm1' },
};

class MockWebSocket {
  static instances = [];

  constructor(url) {
    this.url = url;
    this.readyState = 0;
    this.send = jest.fn();
    this.close = jest.fn(() => {
      this.readyState = 3;
    });
    MockWebSocket.instances.push(this);
  }

  emitOpen() {
    this.readyState = 1;
    if (this.onopen) {
      this.onopen({ type: 'open' });
    }
  }

  emitMessage(payload) {
    if (this.onmessage) {
      this.onmessage({ data: JSON.stringify(payload) });
    }
  }

  emitError() {
    if (this.onerror) {
      this.onerror(new Event('error'));
    }
  }

  emitClose(event = { code: 1006 }) {
    this.readyState = 3;
    if (this.onclose) {
      this.onclose(event);
    }
  }
}

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

const mockAxiosGet = ({
  systems = [RESPONSIBLE_SYSTEM],
  scanJob = null,
  importHistory = [],
  extractionStatus = { task_id: null, status: 'completed' },
  taskStatusQueue = [],
  templateResponses = {},
  profilePayload = {},
} = {}) => {
  const queue = [...taskStatusQueue];

  axios.get.mockImplementation(async (url, config = {}) => {
    if (url === '/api/v1/system/systems') {
      return { data: { data: { systems } } };
    }

    if (String(url).startsWith('/api/v1/code-scan/jobs/')) {
      return { data: scanJob || null };
    }

    if (String(url).includes('/profile/import-history')) {
      return { data: { total: importHistory.length, items: importHistory } };
    }

    if (String(url).includes('/profile/extraction-status')) {
      return { data: extractionStatus };
    }

    if (String(url).includes('/api/v1/system-profiles/task-status/')) {
      if (queue.length > 1) {
        return { data: queue.shift() };
      }
      return { data: queue[0] || { task_id: 'task_001', status: 'extraction_started', system_name: '支付系统' } };
    }

    if (String(url).startsWith('/api/v1/system-profiles/template/')) {
      const normalized = templateResponses[url];
      if (normalized instanceof Error) {
        return Promise.reject(normalized);
      }
      return normalized || {
        data: new Blob(['template']),
        headers: { 'content-disposition': 'attachment; filename="template.xlsx"' },
      };
    }

    if (String(url).startsWith('/api/v1/system-profiles/')) {
      return {
        data: {
          code: 200,
          data: profilePayload,
        },
      };
    }

    return { data: {} };
  });
};

const renderPage = () => render(
  <MemoryRouter initialEntries={['/system-profiles/import?system_name=支付系统&system_id=1']}>
    <SystemProfileImportPage />
  </MemoryRouter>
);

const getButtonByAriaLabel = (root, label) => {
  const scope = root || document.body;
  const button = scope.querySelector(`button[aria-label="${label}"]`);
  if (!button) {
    throw new Error(`Button with aria-label ${label} not found`);
  }
  return button;
};

const findButtonByText = (root, text) => {
  const scope = root || document.body;
  const expected = String(text || '').replace(/\s+/g, '');
  const button = Array.from(scope.querySelectorAll('button')).find((element) => (
    String(element.textContent || '').replace(/\s+/g, '').includes(expected)
  ));
  if (!button) {
    throw new Error(`Button with text ${text} not found`);
  }
  return button;
};

const waitForWritableState = async () => {
  await waitFor(() => {
    expect(getButtonByAriaLabel(document.body, '下载历史评估报告模板')).toBeEnabled();
  });
};

const getCard = (title) => screen.getByText(title).closest('.ant-card');

const uploadFileInCard = (title, fileName = 'demo.docx') => {
  const card = getCard(title);
  const fileInput = card.querySelector('input[type="file"]');
  const file = new File(['demo'], fileName, { type: 'application/octet-stream' });
  fireEvent.change(fileInput, { target: { files: [file] } });
  return { card, file };
};

describe('SystemProfileImportPage v2.5 implementation', () => {
  beforeAll(() => {
    jest.spyOn(console, 'warn').mockImplementation((...args) => {
      const firstArg = String(args[0] || '');
      if (firstArg.includes('React Router Future Flag Warning')) {
        return;
      }
    });
    jest.spyOn(message, 'success').mockImplementation(() => {});
    jest.spyOn(message, 'error').mockImplementation(() => {});
    jest.spyOn(message, 'warning').mockImplementation(() => {});
    jest.spyOn(message, 'destroy').mockImplementation(() => {});
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: (query) => createMatchMediaResult(query),
    });
    Object.defineProperty(window, 'WebSocket', {
      writable: true,
      value: MockWebSocket,
    });
    Object.defineProperty(window.URL, 'createObjectURL', {
      writable: true,
      value: jest.fn(() => 'blob:demo'),
    });
    Object.defineProperty(window.URL, 'revokeObjectURL', {
      writable: true,
      value: jest.fn(),
    });
    Object.defineProperty(window.HTMLAnchorElement.prototype, 'click', {
      writable: true,
      value: jest.fn(),
    });
  });

  afterAll(() => {
    if (console.warn.mockRestore) {
      console.warn.mockRestore();
    }
    if (message.success.mockRestore) {
      message.success.mockRestore();
      message.error.mockRestore();
      message.warning.mockRestore();
      message.destroy.mockRestore();
    }
  });

  beforeEach(() => {
    jest.clearAllMocks();
    jest.useRealTimers();
    localStorage.clear();
    MockWebSocket.instances = [];
    mockAxiosGet({ systems: [] });
    axios.post.mockResolvedValue({ data: { job_id: 'job_001', status: 'submitted' } });
  });

  afterEach(() => {
    message.destroy();
    cleanup();
    jest.useRealTimers();
  });

  it('keeps import cards and code scan baseline', async () => {
    mockAxiosGet({ systems: [RESPONSIBLE_SYSTEM] });
    renderPage();

    expect(await screen.findByText('代码扫描')).toBeInTheDocument();
    expect(screen.getByText('文档导入')).toBeInTheDocument();
    expect(findButtonByText(document.body, '提交扫描')).toBeInTheDocument();
    expect(Array.from(document.body.querySelectorAll('button')).filter((button) => String(button.textContent || '').replace(/\s+/g, '').includes('导入')).length).toBeGreaterThan(0);
  });

  it('renders empty state when user has no responsible systems', async () => {
    mockAxiosGet({ systems: [] });
    renderPage();

    expect(await screen.findByText(/暂无可操作系统/)).toBeInTheDocument();
  });

  it('submits code scan job with repo path', async () => {
    mockAxiosGet({ systems: [RESPONSIBLE_SYSTEM] });
    renderPage();

    const pathInput = await screen.findByPlaceholderText('仓库本地路径（可选）');
    fireEvent.change(pathInput, { target: { value: '/tmp/demo-repo' } });
    fireEvent.click(findButtonByText(document.body, '提交扫描'));

    await waitFor(() => {
      expect(axios.post).toHaveBeenCalledWith('/api/v1/code-scan/jobs', {
        system_name: '支付系统',
        system_id: '1',
        repo_path: '/tmp/demo-repo',
      });
    });
  });

  it('renders template download buttons in target cards and downloads both templates successfully', async () => {
    mockAxiosGet({
      systems: [RESPONSIBLE_SYSTEM],
      templateResponses: {
        '/api/v1/system-profiles/template/history_report': {
          data: new Blob(['history-template']),
          headers: { 'content-disposition': 'attachment; filename="工作量评估模板.xlsx"' },
        },
        '/api/v1/system-profiles/template/esb_document': {
          data: new Blob(['esb-template']),
          headers: { 'content-disposition': 'attachment; filename="接口申请模板.xlsx"' },
        },
      },
    });
    renderPage();
    await waitForWritableState();
    const historyCard = getCard('历史评估报告');
    const esbCard = getCard('ESB服务治理文档');
    const historyButton = getButtonByAriaLabel(historyCard, '下载历史评估报告模板');
    const esbButton = getButtonByAriaLabel(esbCard, '下载ESB服务治理文档模板');

    expect(historyButton).toBeInTheDocument();
    expect(esbButton).toBeInTheDocument();
    expect(document.body.querySelector('button[aria-label="下载需求文档模板"]')).not.toBeInTheDocument();

    fireEvent.click(historyButton);
    await waitFor(() => {
      expect(axios.get).toHaveBeenCalledWith('/api/v1/system-profiles/template/history_report', { responseType: 'blob' });
    });
    await waitFor(() => {
      expect(screen.getByText('模板下载成功')).toBeInTheDocument();
    }, { timeout: 3000 });

    fireEvent.click(esbButton);
    await waitFor(() => {
      expect(axios.get).toHaveBeenCalledWith('/api/v1/system-profiles/template/esb_document', { responseType: 'blob' });
    });
    await waitFor(() => {
      expect(screen.getAllByText('模板下载成功').length).toBeGreaterThan(0);
    }, { timeout: 3000 });
  });

  it('shows failure feedback when template download request fails', async () => {
    mockAxiosGet({
      systems: [RESPONSIBLE_SYSTEM],
      templateResponses: {
        '/api/v1/system-profiles/template/history_report': {
          data: new Blob(['history-template']),
          headers: { 'content-disposition': 'attachment; filename="工作量评估模板.xlsx"' },
        },
        '/api/v1/system-profiles/template/esb_document': new Error('template failed'),
      },
    });

    renderPage();
    await waitForWritableState();
    const esbCard = getCard('ESB服务治理文档');

    fireEvent.click(getButtonByAriaLabel(esbCard, '下载ESB服务治理文档模板'));
    await waitFor(() => {
      expect(screen.getByText('模板下载失败')).toBeInTheDocument();
    }, { timeout: 3000 });
  });

  it('uses websocket first after import, sends heartbeat and refreshes on completion', async () => {
    jest.useFakeTimers();
    mockAxiosGet({
      systems: [RESPONSIBLE_SYSTEM],
      importHistory: [],
      extractionStatus: { task_id: null, status: 'completed' },
      profilePayload: { system_id: '1' },
    });
    axios.post.mockResolvedValue({
      data: {
        imported: 1,
        failed: 0,
        extraction_task_id: 'task_doc_001',
        import_result: { status: 'success' },
      },
    });

    renderPage();
    await waitForWritableState();
    await screen.findByText('文档导入');
    expect(MockWebSocket.instances).toHaveLength(1);
    expect(MockWebSocket.instances[0].url).toContain('/ws/system-profile/%E6%94%AF%E4%BB%98%E7%B3%BB%E7%BB%9F?token=token_pm1');

    const { card } = uploadFileInCard('历史评估报告', 'history.docx');
    await act(async () => {
      fireEvent.click(findButtonByText(card, '导入'));
    });

    await waitFor(() => {
      expect(axios.post).toHaveBeenCalledWith(
        '/api/v1/knowledge/imports',
        expect.any(FormData),
        expect.objectContaining({ headers: { 'Content-Type': 'multipart/form-data' } })
      );
    });

    act(() => {
      MockWebSocket.instances[0].emitOpen();
      jest.advanceTimersByTime(30000);
    });
    expect(MockWebSocket.instances[0].send).toHaveBeenCalled();

    act(() => {
      MockWebSocket.instances[0].emitMessage({
        task_id: 'task_doc_001',
        system_name: '支付系统',
        status: 'extraction_completed',
      });
    });

    expect(await screen.findByText('AI 已完成分析')).toBeInTheDocument();
    await waitFor(() => {
      expect(axios.get).toHaveBeenCalledWith('/api/v1/system-profiles/%E6%94%AF%E4%BB%98%E7%B3%BB%E7%BB%9F');
    });
  });

  it('falls back to task-status polling when websocket fails and stops on terminal status', async () => {
    jest.useFakeTimers();
    mockAxiosGet({
      systems: [RESPONSIBLE_SYSTEM],
      extractionStatus: { task_id: null, status: 'completed' },
      taskStatusQueue: [
        { task_id: 'task_doc_001', status: 'extraction_started', system_name: '支付系统' },
        { task_id: 'task_doc_001', status: 'extraction_completed', system_name: '支付系统' },
      ],
      profilePayload: { system_id: '1' },
    });
    axios.post.mockResolvedValue({
      data: {
        imported: 1,
        failed: 0,
        extraction_task_id: 'task_doc_001',
        import_result: { status: 'success' },
      },
    });

    renderPage();
    await waitForWritableState();
    await screen.findByText('文档导入');

    const { card } = uploadFileInCard('历史评估报告', 'history.docx');
    await act(async () => {
      fireEvent.click(findButtonByText(card, '导入'));
    });
    await waitFor(() => expect(axios.post).toHaveBeenCalled());

    act(() => {
      MockWebSocket.instances[0].emitError();
    });
    expect(await screen.findByText(/已切换为 5 秒轮询/)).toBeInTheDocument();

    act(() => {
      jest.advanceTimersByTime(5000);
    });
    await waitFor(() => {
      expect(axios.get).toHaveBeenCalledWith('/api/v1/system-profiles/task-status/task_doc_001');
    });

    act(() => {
      jest.advanceTimersByTime(5000);
    });
    expect(await screen.findByText('AI 已完成分析')).toBeInTheDocument();
  });

  it('renders a compact status strip and formats object notifications', async () => {
    mockAxiosGet({
      systems: [RESPONSIBLE_SYSTEM],
      extractionStatus: {
        task_id: 'task_doc_001',
        status: 'extraction_completed',
        notifications: [
          {
            type: 'multi_system_detected',
            systems: ['核心账务'],
            message: '检测到文档中还包含系统 核心账务 的信息，如需更新请前往对应系统操作',
          },
        ],
      },
    });

    renderPage();
    await waitForWritableState();

    const statusStrip = await screen.findByTestId('extraction-status-strip');
    expect(statusStrip).toBeInTheDocument();
    expect(screen.getByText('AI 已完成分析')).toBeInTheDocument();
    expect(screen.getByText(/检测到文档中还包含系统 核心账务 的信息/)).toBeInTheDocument();
    expect(screen.queryByText('[object Object]')).not.toBeInTheDocument();
  });

  it('processes websocket completion within 500ms and keeps interactions responsive', async () => {
    mockAxiosGet({
      systems: [RESPONSIBLE_SYSTEM],
      extractionStatus: { task_id: null, status: 'completed' },
      profilePayload: { system_id: '1' },
      templateResponses: {
        '/api/v1/system-profiles/template/history_report': {
          data: new Blob(['history-template']),
          headers: { 'content-disposition': 'attachment; filename="工作量评估模板.xlsx"' },
        },
      },
    });
    axios.post.mockResolvedValue({
      data: {
        imported: 1,
        failed: 0,
        extraction_task_id: 'task_doc_001',
        import_result: { status: 'success' },
      },
    });

    renderPage();
    await waitForWritableState();
    const historyCard = getCard('历史评估报告');
    const historyDownloadButton = getButtonByAriaLabel(historyCard, '下载历史评估报告模板');

    uploadFileInCard('历史评估报告', 'history.docx');
    await act(async () => {
      fireEvent.click(findButtonByText(historyCard, '导入'));
    });
    await waitFor(() => expect(axios.post).toHaveBeenCalled());

    act(() => {
      MockWebSocket.instances[0].emitOpen();
    });

    const startTime = Date.now();
    act(() => {
      MockWebSocket.instances[0].emitMessage({
        task_id: 'task_doc_001',
        system_name: '支付系统',
        status: 'extraction_completed',
      });
    });

    await waitFor(() => {
      expect(screen.getByText('AI 已完成分析')).toBeInTheDocument();
    });
    expect(Date.now() - startTime).toBeLessThan(500);

    fireEvent.click(historyDownloadButton);
    await waitFor(() => {
      expect(axios.get).toHaveBeenCalledWith('/api/v1/system-profiles/template/history_report', { responseType: 'blob' });
    });
  });

  it('shows timeout warning after 10 polling attempts without terminal status', async () => {
    jest.useFakeTimers();
    mockAxiosGet({
      systems: [RESPONSIBLE_SYSTEM],
      extractionStatus: { task_id: null, status: 'completed' },
      taskStatusQueue: new Array(10).fill({ task_id: 'task_doc_001', status: 'extraction_started', system_name: '支付系统' }),
    });
    axios.post.mockResolvedValue({
      data: {
        imported: 1,
        failed: 0,
        extraction_task_id: 'task_doc_001',
        import_result: { status: 'success' },
      },
    });

    renderPage();
    await waitForWritableState();
    await screen.findByText('文档导入');

    const { card } = uploadFileInCard('历史评估报告', 'history.docx');
    await act(async () => {
      fireEvent.click(findButtonByText(card, '导入'));
    });
    await waitFor(() => expect(axios.post).toHaveBeenCalled());

    act(() => {
      MockWebSocket.instances[0].emitClose({ code: 1011 });
    });

    for (let attempt = 0; attempt < 10; attempt += 1) {
      await act(async () => {
        jest.advanceTimersByTime(5000);
      });
    }

    await waitFor(() => {
      const taskStatusCalls = axios.get.mock.calls.filter(([url]) => String(url).includes('/api/v1/system-profiles/task-status/'));
      expect(taskStatusCalls.length).toBeGreaterThanOrEqual(10);
    });

    await waitFor(() => {
      expect(screen.getByText('任务处理超时，请稍后手动刷新')).toBeInTheDocument();
    });
  });
});
