import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { message } from 'antd';
import KnowledgePage from '../pages/KnowledgePage';

jest.mock('axios', () => ({
  get: jest.fn(),
}));
const axios = require('axios');

jest.mock('../hooks/usePermission', () => () => ({
  isAdmin: false,
  isManager: true,
}));

describe('KnowledgePage upload guard', () => {
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
        return { data: { data: { systems: [{ id: 'sys_pay', name: '支付系统' }] } } };
      }
      if (url === '/api/v1/knowledge/evaluation-metrics') {
        return { data: { code: 200, data: {} } };
      }
      if (url === '/api/v1/knowledge/stats') {
        return { data: { code: 200, data: {} } };
      }
      return { data: { code: 200, data: {} } };
    });
  });

  afterEach(() => {
    cleanup();
  });

  it('accepts legacy doc in upload guard', async () => {
    const { container } = render(<KnowledgePage />);

    await waitFor(() => expect(axios.get).toHaveBeenCalledWith('/api/v1/system/systems'));

    const input = container.querySelector('input[type="file"]');
    const legacyFile = new File(['legacy'], 'knowledge.doc', { type: 'application/msword' });
    fireEvent.change(input, { target: { files: [legacyFile] } });

    expect(message.error).not.toHaveBeenCalledWith('系统知识仅支持 DOCX / DOC / PPTX');
    expect(screen.getByText('知识库管理')).toBeInTheDocument();
  });
});
