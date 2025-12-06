import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 seconds for RAG queries
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      // Server responded with error
      console.error('API Error:', error.response.data);
    } else if (error.request) {
      // No response received
      console.error('Network Error:', error.message);
    }
    return Promise.reject(error);
  }
);

// API methods
export const vasudevaAPI = {
  // Health check
  checkHealth: async () => {
    const response = await api.get('/health');
    return response.data;
  },

  // Get guidance for a problem
  getGuidance: async (problem, includeSources = true) => {
    const response = await api.post('/api/guidance', {
      problem,
      include_sources: includeSources,
    });
    return response.data;
  },

  // Get mental wellness support
  getWellnessSupport: async (emotion, situation) => {
    const response = await api.post('/api/wellness', {
      emotion,
      situation,
    });
    return response.data;
  },

  // Search wisdom texts
  searchWisdom: async (query, k = 3) => {
    const response = await api.post('/api/search', {
      query,
      k,
    });
    return response.data;
  },

  // Get stats
  getStats: async () => {
    const response = await api.get('/api/stats');
    return response.data;
  },
};

export default api;

