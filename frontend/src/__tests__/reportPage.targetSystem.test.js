import React from 'react';
import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import '@testing-library/jest-dom';
import ReportPage from '../pages/ReportPage';

jest.setTimeout(15000);

jest.mock('axios', () => ({
  get: jest.fn(),
  post: jest.fn(),
}));
const axios = require('axios');

jest.mock('../hooks/usePermission', () => () => ({
  isAdmin: false,
}));

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
  <MemoryRouter initialEntries={['/report/task_target_1']}>
    <Routes>
      <Route path="/report/:taskId" element={<ReportPage />} />
    </Routes>
  </MemoryRouter>
);

const mockTaskDetail = (overrides = {}) => ({
  code: 200,
  data: {
    id: 'task_target_1',
    name: '目标系统报告',
    description: '',
    status: 'draft',
    aiStatus: 'completed',
    currentRound: 1,
    maxRounds: 3,
    creatorName: '项目经理A',
    createdAt: '2026-04-20T10:00:00',
    documentName: 'requirements.docx',
    systems: ['支付系统'],
    featureCount: 1,
    remark: '',
    targetSystemMode: 'specific',
    targetSystemName: '支付系统',
    targetSystemDisplay: '支付系统',
    expertAssignments: [],
    evaluationProgress: { submitted: 0, total: 0 },
    reportVersions: [],
    deviations: {},
    ...overrides,
  },
});

describe('ReportPage target system display', () => {
  beforeAll(() => {
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: (query) => createMatchMediaResult(query),
    });
  });

  beforeEach(() => {
    jest.clearAllMocks();
    axios.get.mockImplementation((url) => {
      if (url === '/api/v1/tasks/task_target_1') {
        return Promise.resolve({ data: mockTaskDetail() });
      }
      if (url === '/api/v1/tasks/task_target_1/high-deviation') {
        return Promise.resolve({ data: { data: { round: null, isOfficial: false, items: [] } } });
      }
      if (url === '/api/v1/tasks/task_target_1/evaluation') {
        return Promise.resolve({ data: { features: [] } });
      }
      throw new Error(`unexpected url: ${url}`);
    });
  });

  afterEach(() => {
    cleanup();
  });

  it('shows specific target system on report detail', async () => {
    renderPage();

    expect(await screen.findByText('待评估系统')).toBeInTheDocument();
    expect(screen.getAllByText('支付系统').length).toBeGreaterThan(0);
  });

  it('shows unlimited target system when task is not locked to a specific system', async () => {
    axios.get.mockImplementation((url) => {
      if (url === '/api/v1/tasks/task_target_1') {
        return Promise.resolve({
          data: mockTaskDetail({
            targetSystemMode: 'unlimited',
            targetSystemName: '',
            targetSystemDisplay: '不限',
            systems: ['支付系统', '核心账务'],
          }),
        });
      }
      if (url === '/api/v1/tasks/task_target_1/high-deviation') {
        return Promise.resolve({ data: { data: { round: null, isOfficial: false, items: [] } } });
      }
      if (url === '/api/v1/tasks/task_target_1/evaluation') {
        return Promise.resolve({ data: { features: [] } });
      }
      throw new Error(`unexpected url: ${url}`);
    });

    renderPage();

    expect(await screen.findByText('待评估系统')).toBeInTheDocument();
    expect(screen.getByText('不限')).toBeInTheDocument();
  });
});
