import React, { createContext, useCallback, useEffect, useMemo, useState } from 'react';
import axios from 'axios';

const AuthContext = createContext(null);

const AUTH_TOKEN_KEY = 'AUTH_TOKEN';
const AUTH_USER_KEY = 'AUTH_USER';

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
  }, []);

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
    login,
    logout,
    refreshUser,
  }), [user, token, loading, login, logout, refreshUser]);

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export const AUTH_STORAGE_KEYS = {
  token: AUTH_TOKEN_KEY,
  user: AUTH_USER_KEY,
};

export default AuthContext;
