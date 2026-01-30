import React, { createContext, useCallback, useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import useAuth from '../hooks/useAuth';

const NotificationContext = createContext(null);

export const NotificationProvider = ({ children }) => {
  const { isAuthenticated } = useAuth();
  const [unread, setUnread] = useState(0);
  const [loading, setLoading] = useState(false);

  const refreshUnread = useCallback(async () => {
    if (!isAuthenticated) {
      setUnread(0);
      return;
    }
    try {
      setLoading(true);
      const response = await axios.get('/api/v1/notifications/unread-count');
      setUnread(response.data.data?.unread || 0);
    } catch (error) {
      setUnread(0);
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated]);

  useEffect(() => {
    refreshUnread();
  }, [refreshUnread]);

  const value = useMemo(() => ({
    unread,
    loading,
    refreshUnread,
  }), [unread, loading, refreshUnread]);

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
};

export default NotificationContext;
