import React, { createContext, useCallback, useEffect, useMemo, useState } from 'react';
import axios from 'axios';

const AuthContext = createContext(null);

const AUTH_TOKEN_KEY = 'AUTH_TOKEN';
const AUTH_USER_KEY = 'AUTH_USER';
const AUTH_ACTIVE_ROLE_KEY = 'AUTH_ACTIVE_ROLE';

const ROLE_PRIORITY = ['admin', 'manager', 'expert', 'viewer'];

const resolveDefaultRole = (roles = []) => {
  const roleList = Array.isArray(roles) ? roles : [];
  for (const role of ROLE_PRIORITY) {
    if (roleList.includes(role)) {
      return role;
    }
  }
  return roleList[0] || '';
};

const readStoredUser = () => {
  try {
    const raw = localStorage.getItem(AUTH_USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (error) {
    return null;
  }
};

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(() => localStorage.getItem(AUTH_TOKEN_KEY) || '');
  const [user, setUser] = useState(() => readStoredUser());
  const [activeRole, setActiveRoleState] = useState(() => localStorage.getItem(AUTH_ACTIVE_ROLE_KEY) || '');
  const [loading, setLoading] = useState(true);

  const persistAuth = useCallback((nextToken, nextUser) => {
    if (nextToken) {
      localStorage.setItem(AUTH_TOKEN_KEY, nextToken);
    } else {
      localStorage.removeItem(AUTH_TOKEN_KEY);
    }

    if (nextUser) {
      localStorage.setItem(AUTH_USER_KEY, JSON.stringify(nextUser));
    } else {
      localStorage.removeItem(AUTH_USER_KEY);
    }

    setToken(nextToken || '');
    setUser(nextUser || null);

    if (!nextToken || !nextUser) {
      localStorage.removeItem(AUTH_ACTIVE_ROLE_KEY);
      setActiveRoleState('');
      return;
    }

    const roles = Array.isArray(nextUser?.roles) ? nextUser.roles : [];
    const storedRole = localStorage.getItem(AUTH_ACTIVE_ROLE_KEY) || '';
    const nextRole = storedRole && roles.includes(storedRole) ? storedRole : resolveDefaultRole(roles);
    if (nextRole) {
      localStorage.setItem(AUTH_ACTIVE_ROLE_KEY, nextRole);
    } else {
      localStorage.removeItem(AUTH_ACTIVE_ROLE_KEY);
    }
    setActiveRoleState(nextRole);
  }, []);

  const setActiveRole = useCallback((nextRole) => {
    const roles = Array.isArray(user?.roles) ? user.roles : [];
    const normalized = String(nextRole || '').trim();
    if (!normalized || !roles.includes(normalized)) {
      return;
    }
    localStorage.setItem(AUTH_ACTIVE_ROLE_KEY, normalized);
    setActiveRoleState(normalized);
  }, [user]);

  const logout = useCallback(() => {
    persistAuth('', null);
  }, [persistAuth]);

  const refreshUser = useCallback(async () => {
    if (!token) {
      setLoading(false);
      return;
    }
    try {
      const response = await axios.get('/api/v1/auth/me');
      const payload = response.data.data;
      if (payload) {
        persistAuth(token, payload);
      }
    } catch (error) {
      persistAuth('', null);
    } finally {
      setLoading(false);
    }
  }, [token, persistAuth]);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  useEffect(() => {
    const roles = Array.isArray(user?.roles) ? user.roles : [];
    if (!roles.length) {
      if (activeRole) {
        localStorage.removeItem(AUTH_ACTIVE_ROLE_KEY);
        setActiveRoleState('');
      }
      return;
    }

    if (activeRole && roles.includes(activeRole)) {
      return;
    }

    const nextRole = resolveDefaultRole(roles);
    if (nextRole) {
      localStorage.setItem(AUTH_ACTIVE_ROLE_KEY, nextRole);
    } else {
      localStorage.removeItem(AUTH_ACTIVE_ROLE_KEY);
    }
    setActiveRoleState(nextRole);
  }, [activeRole, user]);

  const login = useCallback(async (username, password) => {
    const response = await axios.post('/api/v1/auth/login', {
      username,
      password,
    }, {
      headers: { 'X-Auth-Request': '1' },
    });
    const data = response.data.data;
    persistAuth(data?.token || '', data?.user || null);
    return data;
  }, [persistAuth]);

  const value = useMemo(() => ({
    user,
    token,
    loading,
    isAuthenticated: Boolean(token && user),
    activeRole,
    setActiveRole,
    login,
    logout,
    refreshUser,
  }), [user, token, loading, activeRole, setActiveRole, login, logout, refreshUser]);

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export const AUTH_STORAGE_KEYS = {
  token: AUTH_TOKEN_KEY,
  user: AUTH_USER_KEY,
  activeRole: AUTH_ACTIVE_ROLE_KEY,
};

export default AuthContext;
