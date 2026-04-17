/**
 * Axios API client with configuration, interceptors, and base setup
 */
import axios from "axios";
import { API_CONFIG, STORAGE_KEYS } from "../utils/constants.js";

const backendURL = API_CONFIG.BASE_URL;

console.log("[API_CLIENT] Using backend URL:", backendURL);

// Create axios instance
const client = axios.create({
  baseURL: backendURL,
  timeout: API_CONFIG.TIMEOUT,
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor - add auth token and better logging
client.interceptors.request.use(
  (config) => {
    // Log the request
    console.log(`[API_REQUEST] ${config.method?.toUpperCase()} ${config.url}`, {
      baseURL: client.defaults.baseURL,
      fullURL: `${client.defaults.baseURL}${config.url}`,
    });

    // The backend endpoints don't require authentication
    // Supabase auth is handled client-side, not on backend
    // So we don't need to add token headers for these endpoints

    return config;
  },
  (error) => {
    return Promise.reject(error);
  },
);

// Response interceptor - handle errors with better logging
client.interceptors.response.use(
  (response) => {
    console.log(`[API_RESPONSE] ${response.config.url}:`, {
      status: response.status,
      dataKeys: response.data ? Object.keys(response.data) : "no data",
    });
    return response.data;
  },
  (error) => {
    console.error(
      `[API_ERROR] ${error.config?.method?.toUpperCase()} ${error.config?.url}:`,
      {
        status: error.response?.status,
        statusText: error.response?.statusText,
        message: error.message,
        data: error.response?.data,
      },
    );

    if (error.response?.status === 401) {
      // Backend returns 401 - redirect to login
      console.log("[API_ERROR] Unauthorized - redirecting to login");
      localStorage.removeItem(STORAGE_KEYS.AUTH_TOKEN);
      window.location.href = "/login";
    }

    // 404s are sometimes expected (API might not have that resource yet)
    if (error.response?.status === 404) {
      console.warn(`[API_ERROR] 404 Not Found: ${error.config?.url}`);
      return Promise.reject(error);
    }

    // For other errors, return the data or full error
    return Promise.reject(error.response?.data || error);
  },
);

// Retry wrapper - skip retries for 404s (fallback handles them)
const withRetry = async (fn, retries = API_CONFIG.RETRY_ATTEMPTS) => {
  let lastError;
  for (let i = 0; i < retries; i++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;
      // Don't retry 404s - let fallback logic handle them
      if (error.response?.status === 404) {
        throw error;
      }
      if (i < retries - 1) {
        await new Promise((resolve) =>
          setTimeout(resolve, API_CONFIG.RETRY_DELAY * (i + 1)),
        );
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
  patch: (url, data, config) =>
    withRetry(() => client.patch(url, data, config)),

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
