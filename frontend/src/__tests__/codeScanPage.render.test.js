import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import CodeScanPage from '../pages/CodeScanPage';

jest.mock('axios', () => ({
  get: jest.fn(),
  post: jest.fn(),
}));
const axios = require('axios');

describe('CodeScanPage render', () => {
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

  beforeAll(() => {
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: (query) => createMatchMediaResult(query),
    });
  });

  beforeEach(() => {
    jest.clearAllMocks();
    axios.get.mockImplementation(async (url) => {
      if (url === '/api/v1/system/systems') {
        return { data: { data: { systems: [] } } };
      }
      if (url === '/api/v1/code-scan/jobs') {
        return { data: { data: [] } };
      }
      return { data: { data: {} } };
    });
    axios.post.mockResolvedValue({ data: { data: {} } });
  });

  it('renders page without crashing', async () => {
    render(<CodeScanPage />);
    expect(screen.getByText('代码扫描')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('触发扫描')).toBeInTheDocument();
    });
    expect(screen.getByText('扫描路径（可选）')).toBeInTheDocument();
    expect(screen.getByText('排除目录（可选）')).toBeInTheDocument();
    expect(screen.queryByText('选项(JSON)')).not.toBeInTheDocument();
  });
});
