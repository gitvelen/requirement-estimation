import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { message } from 'antd';
import MainSystemConfigPage from '../pages/MainSystemConfigPage';

jest.setTimeout(15000);

jest.mock('antd', () => {
  const React = require('react');
  const actual = jest.requireActual('antd');

  const MockTable = ({ columns = [], dataSource = [], rowKey, expandable }) => {
    const [expandedKeys, setExpandedKeys] = React.useState([]);

    const resolveRowKey = (record, index) => {
      if (typeof rowKey === 'function') {
        return rowKey(record, index);
      }
      if (typeof rowKey === 'string') {
        return record?.[rowKey];
      }
      return record?.key || index;
    };

    return (
      <div>
        <div data-testid="table-columns">
          {columns.map((column) => (
            <span key={column.key || column.dataIndex || column.title}>{column.title}</span>
          ))}
        </div>
        {dataSource.map((record, index) => {
          const key = resolveRowKey(record, index);
          const isExpanded = expandedKeys.includes(key);
          return (
            <div key={key}>
              {expandable ? (
                <button
                  type="button"
                  onClick={() => {
                    setExpandedKeys((prev) => (
                      prev.includes(key) ? prev.filter((item) => item !== key) : [...prev, key]
                    ));
                  }}
                >
                  展开
                </button>
              ) : null}
              {columns.map((column) => {
                const value = Array.isArray(column.dataIndex)
                  ? column.dataIndex.reduce((result, segment) => result?.[segment], record)
                  : record?.[column.dataIndex];
                const rendered = column.render ? column.render(value, record, index) : value;
                return (
                  <div key={`${key}-${column.key || column.dataIndex || column.title}`}>
                    {rendered}
                  </div>
                );
              })}
              {isExpanded && expandable?.expandedRowRender ? expandable.expandedRowRender(record, index) : null}
            </div>
          );
        })}
      </div>
    );
  };

  return {
    ...actual,
    Table: MockTable,
  };
});

jest.mock('axios', () => ({
  get: jest.fn(),
  post: jest.fn(),
  put: jest.fn(),
  delete: jest.fn(),
}));

const axios = require('axios');

describe('MainSystemConfigPage', () => {
  beforeAll(() => {
    jest.spyOn(message, 'success').mockImplementation(() => {});
    jest.spyOn(message, 'error').mockImplementation(() => {});
  });

  afterAll(() => {
    message.success.mockRestore();
    message.error.mockRestore();
  });

  beforeEach(() => {
    jest.clearAllMocks();
    axios.get.mockResolvedValue({
      data: {
        data: {
          systems: [
            {
              id: 'SYS-001',
              name: '支付系统',
              abbreviation: 'PAY',
              status: '运行中',
              extra: {
                产品经理: '张三',
                功能描述: '负责支付清算与渠道接入',
              },
            },
          ],
        },
      },
    });
  });

  afterEach(() => {
    cleanup();
  });

  it('keeps extra fields out of the main columns and shows them in expanded details', async () => {
    render(<MainSystemConfigPage embedded />);

    expect(await screen.findByText('支付系统', {}, { timeout: 10000 })).toBeInTheDocument();
    expect(screen.getByText('系统名称')).toBeInTheDocument();
    expect(screen.getByText('系统简称')).toBeInTheDocument();
    expect(screen.getByText('系统状态')).toBeInTheDocument();

    expect(screen.queryByText('产品经理')).not.toBeInTheDocument();
    expect(screen.queryByText('功能描述')).not.toBeInTheDocument();
    expect(screen.getByText('2 项')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '展开' }));

    await waitFor(() => {
      expect(screen.getByText('产品经理')).toBeInTheDocument();
      expect(screen.getByText('张三')).toBeInTheDocument();
      expect(screen.getByText('功能描述')).toBeInTheDocument();
      expect(screen.getByText('负责支付清算与渠道接入')).toBeInTheDocument();
    }, { timeout: 10000 });
  });
});
