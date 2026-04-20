import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import '@testing-library/jest-dom';
import { message } from 'antd';
import UploadPage from '../pages/UploadPage';

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
    roles: ['manager'],
  },
  token: 'token_pm1',
  activeRole: 'manager',
}));

const RESPONSIBLE_SYSTEMS = [
  { id: 'sys_pay', name: '支付系统', extra: { owner_username: 'pm1' } },
  { id: 'sys_risk', name: '风控系统', extra: { backup_owner_usernames: ['pm1'] } },
  { id: 'sys_core', name: '核心账务', extra: { owner_username: 'other_pm' } },
];

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
  <MemoryRouter initialEntries={['/upload']}>
    <UploadPage />
  </MemoryRouter>
);

describe('UploadPage target system selection', () => {
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
    axios.get.mockResolvedValue({
      data: {
        data: {
          systems: RESPONSIBLE_SYSTEMS,
        },
      },
    });
    axios.post.mockResolvedValue({ data: { task_id: 'task_001' } });
  });

  afterEach(() => {
    cleanup();
  });

  it('renders target system before task name and keeps unlimited last after responsible systems', async () => {
    renderPage();

    const targetSystemLabel = await screen.findByText('待评估系统');
    const taskNameLabel = screen.getByText('任务名称（可选）');
    expect(targetSystemLabel.compareDocumentPosition(taskNameLabel) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();

    const targetSystemSelect = screen.getByRole('combobox');
    expect(targetSystemSelect).toBeInTheDocument();
    expect(screen.queryByRole('radio')).not.toBeInTheDocument();

    fireEvent.mouseDown(targetSystemSelect);

    const paymentOption = await screen.findByTitle('支付系统');
    const riskOption = await screen.findByTitle('风控系统');
    const unlimitedOption = await screen.findByTitle('不限');

    expect(screen.queryByText('核心账务')).not.toBeInTheDocument();
    expect(paymentOption.compareDocumentPosition(riskOption) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(riskOption.compareDocumentPosition(unlimitedOption) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('shows only unlimited when manager has no primary or backup systems and still allows submit path', async () => {
    axios.get.mockResolvedValueOnce({
      data: {
        data: {
          systems: [{ id: 'sys_core', name: '核心账务', extra: { owner_username: 'other_pm' } }],
        },
      },
    });

    renderPage();

    const targetSystemSelect = await screen.findByRole('combobox');
    fireEvent.mouseDown(targetSystemSelect);

    const unlimitedOption = await screen.findByRole('option', { name: '不限' });
    expect(unlimitedOption).toBeInTheDocument();
    expect(screen.queryByRole('option', { name: '核心账务' })).not.toBeInTheDocument();
  });

  it('requires target system selection and submits selected payload in multipart form', async () => {
    renderPage();

    const fileInput = document.querySelector('input[type="file"]');
    const submitButton = screen.getByText('提交评估').closest('button');
    const reqFile = new File(['req'], 'requirements.docx', {
      type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    });
    fireEvent.change(fileInput, { target: { files: [reqFile] } });

    fireEvent.click(submitButton);
    await waitFor(() => expect(message.warning).toHaveBeenCalled());

    const targetSystemSelect = screen.getByRole('combobox');
    fireEvent.mouseDown(targetSystemSelect);
    fireEvent.click(await screen.findByTitle('支付系统'));
    fireEvent.click(submitButton);

    await waitFor(() => expect(axios.post).toHaveBeenCalled());
    const [, formData] = axios.post.mock.calls[0];
    expect(formData.get('target_system_mode')).toBe('specific');
    expect(formData.get('target_system_name')).toBe('支付系统');
  });
});
