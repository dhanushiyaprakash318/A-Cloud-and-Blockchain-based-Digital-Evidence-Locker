import axios, { AxiosError } from 'axios';
import {
  Case,
  CaseCreateRequest,
  CasesListResponse,
  CaseDetailResponse,
  KnowledgeGraphResponse,
} from '@/types/case';

// Determine API URL based on environment
let activeBaseUrl = '';

const getApiUrl = () => {
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }
  return 'http://localhost:8000/api/v1';
};

const API_URL = getApiUrl();
activeBaseUrl = API_URL;
console.log('🔗 API URL configured as:', API_URL);

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 second timeout
});

// Request interceptor for auth token
api.interceptors.request.use((config) => {
  let token = localStorage.getItem('token');

  if (token) {
    // Remove quotes if they were accidentally stored
    token = token.replace(/^"(.*)"$/, '$1');
    config.headers.Authorization = `Bearer ${token}`;
  }
  
  // Use activeBaseUrl dynamically
  config.baseURL = activeBaseUrl;
  
  console.log(`📤 ${config.method?.toUpperCase()} ${config.url}`);
  return config;
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    console.log(`✅ ${response.config.url} - Status: ${response.status}`);
    return response;
  },
  async (error: AxiosError) => {
    const status = error.response?.status;
    const responseData = error.response?.data as any;
    const message = responseData?.detail || error.message || 'Unknown error';
    
    console.error(`❌ API Error - Status: ${status}, Message: ${message}`);

    if (status === 401) {
      console.warn('⚠️ Unauthorized - clearing token');
      localStorage.removeItem('token');
    }

    const config = error.config;
    // If it's a network connection error (no response) and we haven't retried yet
    if (!error.response && config && !(config as any)._isRetry) {
      (config as any)._isRetry = true;
      
      if (activeBaseUrl.includes(':8000')) {
        activeBaseUrl = activeBaseUrl.replace(':8000', ':8046');
        console.log('🔄 Port 8000 unreachable. Swapping API base URL to:', activeBaseUrl);
      } else if (activeBaseUrl.includes(':8046')) {
        activeBaseUrl = activeBaseUrl.replace(':8046', ':8000');
        console.log('🔄 Port 8046 unreachable. Swapping API base URL to:', activeBaseUrl);
      }
      
      config.baseURL = activeBaseUrl;
      api.defaults.baseURL = activeBaseUrl;
      
      console.log(`🔄 Retrying: ${config.method?.toUpperCase()} ${config.url}`);
      return api(config);
    }

    return Promise.reject(error);
  }
);

export const auth = {
  login: async (username: string, password: string) => {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);
    const response = await api.post('/auth/login', formData);
    return response.data;
  },
};

export const evidence = {
  upload: async (caseId: string, file: File) => {
    const formData = new FormData();
    formData.append('case_id', caseId);
    formData.append('file', file);
    const response = await api.post('/evidence/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
  verify: async (evidenceId: string) => {
    const response = await api.get(`/evidence/${evidenceId}/verify`);
    return response.data;
  },
  blockchain: async (evidenceId: string) => {
    const response = await api.get(`/evidence/${evidenceId}/blockchain`);
    return response.data;
  },
};

export const cases = {
  /**
   * Fetch all cases from the API
   */
  list: async (): Promise<CasesListResponse> => {
    try {
      const response = await api.get('/cases');
      return response.data;
    } catch (error) {
      console.error('Error listing cases:', error);
      throw error;
    }
  },

  /**
   * Fetch a specific case by ID
   */
  get: async (id: string): Promise<CaseDetailResponse> => {
    try {
      const response = await api.get(`/cases/${id}`);
      return response.data;
    } catch (error) {
      console.error(`Error fetching case ${id}:`, error);
      throw error;
    }
  },

  /**
   * Create a new case
   */
  create: async (data: CaseCreateRequest): Promise<Case> => {
    try {
      // Ensure numeric fields are numbers
      const caseData = {
        ...data,
        latitude: Number(data.latitude),
        longitude: Number(data.longitude),
      };
      const response = await api.post('/cases', caseData);
      return response.data;
    } catch (error) {
      console.error('Error creating case:', error);
      throw error;
    }
  },

  graph: async (caseId: string): Promise<KnowledgeGraphResponse> => {
    try {
      const response = await api.get(`/cases/${caseId}/knowledge-graph`);
      return response.data;
    } catch (error) {
      console.error(`Error fetching knowledge graph for case ${caseId}:`, error);
      throw error;
    }
  },

  /**
   * Update an existing case
   */
  update: async (id: string, data: Partial<Case>): Promise<Case> => {
    try {
      const response = await api.put(`/cases/${id}`, data);
      return response.data.case;
    } catch (error) {
      console.error(`Error updating case ${id}:`, error);
      throw error;
    }
  },

  /**
   * Delete a case (soft delete - archives it)
   */
  delete: async (id: string): Promise<{ message: string }> => {
    try {
      const response = await api.delete(`/cases/${id}`);
      return response.data;
    } catch (error) {
      console.error(`Error deleting case ${id}:`, error);
      throw error;
    }
  },
};

export { api as apiClient };
export default api;
