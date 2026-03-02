import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import SystemProfileImportPage from '../pages/SystemProfileImportPage';

jest.mock('axios', () => ({
  get: jest.fn(),
  post: jest.fn(),
}));
const axios = require('axios');

jest.mock('../hooks/useAuth', () => () => ({
  user: { username: 'pm1', displayName: '项目经理1' },
}));

jest.mock('../hooks/usePermission', () => () => ({
  isManager: true,
}));

describe('SystemProfileImportPage render', () => {
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
        return {
          data: {
            data: {
              systems: [
                {
                  id: 1,
                  name: '支付系统',
                  manager: 'pm1',
                  owner_username: 'pm1',
                },
              ],
            },
          },
        };
      }

      if (String(url).includes('/profile/import-history')) {
        return { data: { records: [] } };
      }

      if (String(url).includes('/profile/extraction-status')) {
        return { data: { status: 'idle' } };
      }

      return { data: {} };
    });
    axios.post.mockResolvedValue({ data: {} });
  });

  it('renders import cards without crashing', async () => {
    render(
      <MemoryRouter initialEntries={['/system-profiles/import']}>
        <SystemProfileImportPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/暂无可操作系统/)).toBeInTheDocument();
    });
  });
});
