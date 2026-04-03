// frontend/src/utils/axiosConfig.js
import axios from 'axios';

// Get the API URL from environment variables
const API_URL = process.env.REACT_APP_API_URL || 'https://api-timesheet.firsteconomy.com';

// Create axios instance with base URL and no-cache headers
const axiosInstance = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
    'Cache-Control': 'no-cache, no-store, must-revalidate',
    'Pragma': 'no-cache',
    'Expires': '0',
  },
});

// Add request interceptor to include auth token and cache-busting timestamp
axiosInstance.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    // Add timestamp to prevent cached responses
    config.params = { ...config.params, _t: Date.now() };
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add response interceptor to handle errors
axiosInstance.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized access
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default axiosInstance;
