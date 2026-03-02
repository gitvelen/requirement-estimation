import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import EvidenceRuleConfigPage from '../pages/EvidenceRuleConfigPage';

jest.mock('axios', () => ({
  get: jest.fn(),
  put: jest.fn(),
}));
const axios = require('axios');

describe('EvidenceRuleConfigPage render', () => {
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
      if (url === '/api/v1/evidence-level/rules') {
        return {
          data: {
            code: 200,
            data: {
              version: 3,
              levels: [
                { level: 'E2', any_of: ['profile', 'esb'] },
                { level: 'E0' },
              ],
            },
          },
        };
      }
      if (url === '/api/v1/evidence-level/rules/logs') {
        return { data: { code: 200, data: [] } };
      }
      return { data: { code: 200, data: {} } };
    });
    axios.put.mockResolvedValue({ data: { code: 200, data: {} } });
  });

  it('renders human-readable rule editor without raw json textarea', async () => {
    render(<EvidenceRuleConfigPage />);

    expect(screen.getByText('证据等级规则配置')).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText('规则版本')).toBeInTheDocument();
    });

    expect(screen.getByText('新增等级规则')).toBeInTheDocument();
    expect(screen.getAllByText('分组命中（any_groups，组间AND）').length).toBeGreaterThan(0);
    expect(screen.queryByText('规则JSON')).not.toBeInTheDocument();
    expect(screen.queryByPlaceholderText('请输入规则JSON')).not.toBeInTheDocument();
  });
});
