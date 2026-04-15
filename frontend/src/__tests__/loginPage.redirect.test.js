import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import '@testing-library/jest-dom';
import LoginPage from '../pages/LoginPage';
import useAuth from '../hooks/useAuth';

jest.mock('axios', () => ({
  get: jest.fn(),
  post: jest.fn(),
  put: jest.fn(),
  delete: jest.fn(),
}));

jest.mock('../hooks/useAuth');

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

const LocationProbe = () => {
  const location = useLocation();
  return <div data-testid="location">{`${location.pathname}${location.search}`}</div>;
};

const renderLoginPage = (initialEntry) => render(
  <MemoryRouter initialEntries={[initialEntry]}>
    <Routes>
      <Route path="/login" element={<><LoginPage /><LocationProbe /></>} />
      <Route path="/dashboard/reports" element={<LocationProbe />} />
      <Route path="/system-profiles/board" element={<LocationProbe />} />
    </Routes>
  </MemoryRouter>
);

describe('LoginPage redirect behavior', () => {
  beforeAll(() => {
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: (query) => createMatchMediaResult(query),
    });
  });

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('forces admin users to dashboard reports even when redirect points to a manager page', async () => {
    const login = jest.fn().mockResolvedValue({
      user: {
        roles: ['admin'],
      },
    });
    useAuth.mockReturnValue({
      login,
      isAuthenticated: false,
    });

    renderLoginPage('/login?redirect=/system-profiles/board');

    fireEvent.change(screen.getByLabelText('用户名'), { target: { value: 'admin' } });
    fireEvent.change(screen.getByLabelText('密码'), { target: { value: 'admin' } });
    fireEvent.click(screen.getByRole('button', { name: /登\s*录/ }));

    await waitFor(() => {
      expect(screen.getByTestId('location')).toHaveTextContent('/dashboard/reports');
    });
  });

  it('keeps honoring redirect for manager users', async () => {
    const login = jest.fn().mockResolvedValue({
      user: {
        roles: ['manager'],
      },
    });
    useAuth.mockReturnValue({
      login,
      isAuthenticated: false,
    });

    renderLoginPage('/login?redirect=/system-profiles/board');

    fireEvent.change(screen.getByLabelText('用户名'), { target: { value: 'manager' } });
    fireEvent.change(screen.getByLabelText('密码'), { target: { value: 'manager' } });
    fireEvent.click(screen.getByRole('button', { name: /登\s*录/ }));

    await waitFor(() => {
      expect(screen.getByTestId('location')).toHaveTextContent('/system-profiles/board');
    });
  });
});
