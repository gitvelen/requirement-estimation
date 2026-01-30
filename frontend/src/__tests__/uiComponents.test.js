import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import PageHeader from '../components/PageHeader';
import StatusTag from '../components/StatusTag';
import Loading from '../components/Loading';
import Empty from '../components/Empty';

describe('UI components', () => {
  it('renders PageHeader title and subtitle', () => {
    render(<PageHeader title="标题" subtitle="副标题" />);
    expect(screen.getByText('标题')).toBeInTheDocument();
    expect(screen.getByText('副标题')).toBeInTheDocument();
  });

  it('renders StatusTag with default mapping', () => {
    render(<StatusTag status="completed" />);
    expect(screen.getByText('已完成')).toBeInTheDocument();
  });

  it('renders Loading with tip', () => {
    render(<Loading tip="加载中..." />);
    expect(screen.getByText('加载中...')).toBeInTheDocument();
  });

  it('renders Empty with default description', () => {
    render(<Empty />);
    expect(screen.getByText('暂无数据')).toBeInTheDocument();
  });
});
