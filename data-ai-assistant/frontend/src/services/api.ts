import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 요청 인터셉터 - 토큰 자동 추가
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth-storage');
    if (token) {
      try {
        const authData = JSON.parse(token);
        if (authData.state?.token) {
          config.headers.Authorization = `Bearer ${authData.state.token}`;
        }
      } catch (error) {
        console.error('Error parsing auth token:', error);
      }
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 응답 인터셉터 - 401 에러 처리
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // 토큰 만료 시 로그아웃
      localStorage.removeItem('auth-storage');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface QueryRequest {
  question: string;
  context?: string;
}

export interface QueryResponse {
  success: boolean;
  question: string;
  answer: string;
  sql_query?: string;
  data?: any[];
  columns?: string[];
  row_count?: number;
  explanation?: string;
  confidence?: number;
  error?: string;
}

export const authApi = {
  login: async (credentials: LoginRequest): Promise<LoginResponse> => {
    const response = await api.post<LoginResponse>('/auth/login', credentials);
    return response.data;
  },
};

export const queryApi = {
  ask: async (request: QueryRequest): Promise<QueryResponse> => {
    const response = await api.post<QueryResponse>('/query/ask', request);
    return response.data;
  },
  
  initialize: async (): Promise<{ message: string }> => {
    const response = await api.post('/query/initialize');
    return response.data;
  },
  
  getStats: async (): Promise<{ stats: any }> => {
    const response = await api.get('/query/stats');
    return response.data;
  },
  
  getHistory: async (): Promise<{ history: any[]; message: string }> => {
    const response = await api.get('/query/history');
    return response.data;
  },
};