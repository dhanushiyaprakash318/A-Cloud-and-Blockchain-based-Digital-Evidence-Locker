import axios, { AxiosError } from 'axios';
import {
  Case,
  CaseCreateRequest,
  CasesListResponse,
  CaseDetailResponse,
  KnowledgeGraphResponse,
} from '@/types/case';

// Determine API URL based on environment
const getApiBaseUrl = () => {
  const envBaseUrl = import.meta.env.VITE_API_BASE_URL;
  if (!envBaseUrl) {
    throw new Error('[VITE_API_BASE_URL] environment variable is required.');
  }
  return envBaseUrl.replace(/\/$/, '');
};

const API_BASE = getApiBaseUrl();
const API_URL = `${API_BASE}/api/v1`;

console.log('API Base URL:', API_BASE);
console.log('🔗 Full API URL configured as:', API_URL);

const api = axios.create({
  baseURL: API_URL,
  timeout: 30000, // 30 second timeout
});

const getErrorType = (error: AxiosError) => {
  if (error.code === 'ECONNABORTED') return 'Timeout';
  if (!error.response) {
    if (error.message?.toLowerCase().includes('network error')) return 'Network Error';
    if (error.message?.toLowerCase().includes('cors')) return 'CORS Error';
    if (error.message?.toLowerCase().includes('getaddrinfo') || error.message?.toLowerCase().includes('dns')) return 'DNS Failure';
    return 'Backend unreachable';
  }
  switch (error.response.status) {
    case 400:
      return 'Bad Request';
    case 401:
      return 'Unauthorized';
    case 403:
      return 'Forbidden';
    case 404:
      return 'Not Found';
    case 500:
      return 'Server Error';
    default:
      return `HTTP ${error.response.status}`;
  }
};

// Request interceptor for auth token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')?.replace(/^"(.*)"$/, '$1');

  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  const requestUrl = `${config.baseURL ?? API_URL}${config.url ?? ''}`;
  console.log('📤 API Request', {
    method: config.method?.toUpperCase() ?? 'UNKNOWN',
    url: requestUrl,
    baseURL: config.baseURL ?? API_URL,
    headers: config.headers,
    payload: config.data,
  });

  return config;
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    console.log('✅ API Response', {
      method: response.config.method?.toUpperCase() ?? 'UNKNOWN',
      url: response.config.url,
      status: response.status,
      responseHeaders: response.headers,
      responseBody: response.data,
    });
    return response;
  },
  async (error: AxiosError) => {
    const config = error.config;
    const requestUrl = `${config?.baseURL ?? API_URL}${config?.url ?? ''}`;
    const method = config?.method?.toUpperCase() ?? 'UNKNOWN';
    const status = error.response?.status;
    const responseData = error.response?.data as Record<string, unknown> | undefined;
    const responseHeaders = error.response?.headers;
    const errorType = getErrorType(error);

    console.error('❌ API Request failed', {
      type: errorType,
      method,
      requestUrl,
      baseURL: config?.baseURL ?? API_URL,
      requestHeaders: config?.headers,
      requestPayload: config?.data,
      status,
      responseHeaders,
      responseBody: responseData,
      axiosErrorCode: error.code,
      axiosMessage: error.message,
      stack: error.stack,
    });

    if (status === 401) {
      console.warn('⚠️ Unauthorized - clearing token');
      localStorage.removeItem('token');
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
    const normalizedCaseId = (caseId ?? '').toString().trim();
    const invalids = new Set(['', 'undefined', 'null', 'nan']);
    if (invalids.has(normalizedCaseId.toLowerCase())) {
      console.error('Evidence upload missing or invalid caseId', { caseId, normalizedCaseId, fileName: file.name, fileType: file.type });
      throw new Error('Missing valid caseId in evidence upload request.');
    }

    const formData = new FormData();
    formData.append('case_id', normalizedCaseId);
    formData.append('file', file);

    console.log('📤 Evidence upload payload', {
      caseId,
      fileName: file.name,
      fileType: file.type,
      fileSize: file.size,
      formDataKeys: Array.from(formData.keys()),
    });

    const response = await api.post('/evidence/upload', formData);
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
      return response.data.case;
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

export const assistant = {
  query: async (text: string): Promise<any> => {
    try {
      const response = await api.post('/ai/query', { question: text });
      return response.data;
    } catch (error) {
      console.error('Error querying assistant:', error);
      throw error;
    }
  },
};

export { api as apiClient };
export default api;
