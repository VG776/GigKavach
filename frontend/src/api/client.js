/**
 * Axios API client with configuration, interceptors, and base setup
 */
import axios from 'axios';
import { API_CONFIG, STORAGE_KEYS } from '../utils/constants.js';

// Create axios instance
const client = axios.create({
  baseURL: API_CONFIG.BASE_URL,
  timeout: API_CONFIG.TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor - add auth token
client.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN);
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor - handle errors
client.interceptors.response.use(
  (response) => {
    return response.data;
  },
  (error) => {
    if (error.response?.status === 401) {
      // Redirect to login
      localStorage.removeItem(STORAGE_KEYS.AUTH_TOKEN);
      window.location.href = '/login';
    }
    return Promise.reject(error.response?.data || error);
  }
);

// Retry wrapper
const withRetry = async (fn, retries = API_CONFIG.RETRY_ATTEMPTS) => {
  let lastError;
  for (let i = 0; i < retries; i++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;
      if (i < retries - 1) {
        await new Promise((resolve) => setTimeout(resolve, API_CONFIG.RETRY_DELAY * (i + 1)));
      }
    }
  }
  throw lastError;
};

const apiClient = {
  /**
   * GET request
   */
  get: (url, config) => withRetry(() => client.get(url, config)),

  /**
   * POST request
   */
  post: (url, data, config) => withRetry(() => client.post(url, data, config)),

  /**
   * PUT request
   */
  put: (url, data, config) => withRetry(() => client.put(url, data, config)),

  /**
   * PATCH request
   */
  patch: (url, data, config) => withRetry(() => client.patch(url, data, config)),

  /**
   * DELETE request
   */
  delete: (url, config) => withRetry(() => client.delete(url, config)),

  /**
   * Set authorization token
   */
  setToken: (token) => {
    localStorage.setItem(STORAGE_KEYS.AUTH_TOKEN, token);
    client.defaults.headers.Authorization = `Bearer ${token}`;
  },

  /**
   * Clear authorization token
   */
  clearToken: () => {
    localStorage.removeItem(STORAGE_KEYS.AUTH_TOKEN);
    delete client.defaults.headers.Authorization;
  },

  /**
   * Get current token
   */
  getToken: () => {
    return localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN);
  },
};

export default apiClient;
