import axios from 'axios';

const applyAdminKey = (config) => {
  const adminKey = localStorage.getItem('ADMIN_API_KEY');
  if (adminKey) {
    config.headers = config.headers || {};
    config.headers['X-API-Key'] = adminKey;
  }
  return config;
};

const applyAuthToken = (config) => {
  const token = localStorage.getItem('AUTH_TOKEN');
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
};

axios.interceptors.request.use(
  (config) => applyAuthToken(applyAdminKey(config)),
  (error) => Promise.reject(error)
);

axios.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;
    const isAuthRequest = error?.config?.headers?.['X-Auth-Request'] === '1';
    if (status === 401 && !isAuthRequest) {
      localStorage.removeItem('AUTH_TOKEN');
      localStorage.removeItem('AUTH_USER');
      if (window.location.pathname !== '/login') {
        const redirect = encodeURIComponent(window.location.pathname + window.location.search);
        window.location.href = `/login?redirect=${redirect}`;
      }
    }
    return Promise.reject(error);
  }
);
