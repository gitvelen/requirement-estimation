import React from 'react';
import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import '@testing-library/jest-dom';
import EditPage from '../pages/EditPage';

jest.setTimeout(15000);

jest.mock('axios', () => ({
  get: jest.fn(),
  put: jest.fn(),
  post: jest.fn(),
  delete: jest.fn(),
}));
const axios = require('axios');

jest.mock('../hooks/usePermission', () => () => ({
  isManager: true,
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
  <MemoryRouter initialEntries={['/edit/task_edit_1']}>
    <Routes>
      <Route path="/edit/:taskId" element={<EditPage />} />
    </Routes>
  </MemoryRouter>
);

const featureRow = {
  序号: '1.1',
  功能模块: '支付接入',
  功能点: '支付订单同步',
  业务描述: '同步支付订单状态',
  预估人天: 1,
};

describe('EditPage target system lock', () => {
  beforeAll(() => {
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: (query) => createMatchMediaResult(query),
    });
  });

  afterEach(() => {
    cleanup();
    jest.clearAllMocks();
  });

  it('hides system-scope actions for locked specific-system tasks but keeps feature actions', async () => {
    axios.get.mockImplementation((url) => {
      if (url === '/api/v1/requirement/result/task_edit_1') {
        return Promise.resolve({
          data: {
            data: {
              systems_data: { 支付系统: [featureRow] },
              modifications: [],
              confirmed: false,
              ai_system_analysis: {
                selected_systems: [{ name: '支付系统', type: '主系统' }],
                candidate_systems: [],
              },
              target_system_mode: 'specific',
              target_system_name: '支付系统',
              target_system_display: '支付系统',
            },
          },
        });
      }
      if (url === '/api/v1/system/systems') {
        return Promise.resolve({ data: { data: { systems: [{ name: '支付系统' }] } } });
      }
      throw new Error(`unexpected url: ${url}`);
    });

    renderPage();

    expect(await screen.findByText('单系统锁定')).toBeInTheDocument();
    expect(screen.getByText('添加功能点')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /系统操作/i })).not.toBeInTheDocument();
  });

  it('keeps system-scope actions available for unlimited tasks', async () => {
    axios.get.mockImplementation((url) => {
      if (url === '/api/v1/requirement/result/task_edit_1') {
        return Promise.resolve({
          data: {
            data: {
              systems_data: { 支付系统: [featureRow], 核心账务: [] },
              modifications: [],
              confirmed: false,
              ai_system_analysis: {
                selected_systems: [
                  { name: '支付系统', type: '主系统' },
                  { name: '核心账务', type: '从系统' },
                ],
                candidate_systems: [],
              },
              target_system_mode: 'unlimited',
              target_system_name: '',
              target_system_display: '不限',
            },
          },
        });
      }
      if (url === '/api/v1/system/systems') {
        return Promise.resolve({ data: { data: { systems: [{ name: '支付系统' }, { name: '核心账务' }] } } });
      }
      throw new Error(`unexpected url: ${url}`);
    });

    renderPage();

    expect(await screen.findByRole('button', { name: /系统操作/i })).toBeInTheDocument();
    expect(screen.queryByText('单系统锁定')).not.toBeInTheDocument();
  });
});
