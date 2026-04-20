import React from 'react';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import DashboardReportsPage from '../pages/DashboardReportsPage';
import DashboardRankingsPage from '../pages/DashboardRankingsPage';

jest.mock('axios', () => ({
  post: jest.fn(),
}));

const axios = require('axios');

describe('dashboard request lifecycle', () => {
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
  });

  afterEach(() => {
    cleanup();
    jest.clearAllMocks();
  });

  it('passes AbortSignal to dashboard reports queries and keeps canceled requests silent', async () => {
    axios.post.mockRejectedValue({ code: 'ERR_CANCELED', name: 'CanceledError' });

    render(<DashboardReportsPage />);

    await waitFor(() => {
      expect(axios.post).toHaveBeenCalledWith(
        '/api/v1/efficiency/dashboard/query',
        expect.objectContaining({
          page: 'overview',
          perspective: 'executive',
          filters: {},
        }),
        expect.objectContaining({
          signal: expect.any(Object),
        }),
      );
    });

    await waitFor(() => {
      expect(screen.queryByText('多维报表加载失败')).not.toBeInTheDocument();
    });
  });

  it('passes AbortSignal to dashboard rankings query and keeps canceled requests silent', async () => {
    axios.post.mockRejectedValue({ code: 'ERR_CANCELED', name: 'CanceledError' });

    render(<DashboardRankingsPage />);

    await waitFor(() => {
      expect(axios.post).toHaveBeenCalledWith(
        '/api/v1/efficiency/dashboard/query',
        expect.objectContaining({
          page: 'rankings',
          perspective: 'executive',
          filters: {},
        }),
        expect.objectContaining({
          signal: expect.any(Object),
        }),
      );
    });

    await waitFor(() => {
      expect(screen.queryByText('排行榜加载失败')).not.toBeInTheDocument();
    });
  });
});
