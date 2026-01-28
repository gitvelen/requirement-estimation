import axios from 'axios';

const applyAdminKey = (config) => {
  const adminKey = localStorage.getItem('ADMIN_API_KEY');
  if (adminKey) {
    config.headers = config.headers || {};
    config.headers['X-API-Key'] = adminKey;
  }
  return config;
};

axios.interceptors.request.use(
  (config) => applyAdminKey(config),
  (error) => Promise.reject(error)
);
