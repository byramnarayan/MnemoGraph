/**
 * Centralized API client for communicating with FastAPI backend.
 * Enterprise-ready: handles baseURL, token injection, response parsing, and error handling.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export interface UserResponse {
  id: number;
  full_name: string;
  email: string;
  tenant_slug?: string | null;
  company_name?: string | null;
  industry_vertical?: string | null;
  department?: string | null;
  role: string;
  image_file?: string | null;
  image_url: string;
  is_active: boolean;
  created_at: string;
}

export interface AuthTokenResponse {
  access_token: string;
  token_type: string;
  user: UserResponse;
}

export interface UserRegisterInput {
  full_name: string;
  email: string;
  password: string;
  tenant_slug?: string;
  company_name?: string;
  industry_vertical?: string;
  department?: string;
  role?: string;
}

export interface UserLoginInput {
  email: string;
  password: string;
}

export interface UserUpdateInput {
  full_name?: string;
  company_name?: string;
  industry_vertical?: string;
  department?: string;
}

export interface DatabricksTestInput {
  host: string;
  token: string;
  workspace_id: string;
}

export interface DatabricksCreateInput {
  name: string;
  host: string;
  workspace_id: string;
  token: string;
  org_id?: string;
  selected_warehouse_id?: string;
  selected_tables?: string[];
  auto_index?: boolean;
  sync_interval_minutes?: number;
}

export interface WarehouseItem {
  id: string;
  name: string;
  state?: string;
  http_path?: string;
}

export interface TableItem {
  full_name: string;
  name: string;
  catalog?: string;
  schema_name?: string;
  table_type?: string;
}

export interface ConnectorResponse {
  id: string;
  org_id?: string;
  name: string;
  connector_type: string;
  host: string;
  workspace_id: string;
  selected_warehouse_id?: string | null;
  selected_tables?: string | null;
  status: string;
  auto_index: boolean;
  sync_interval_minutes: number;
  created_at: string;
  updated_at: string;
}

export interface TestConnectionResponse {
  ok: boolean;
  workspace_name?: string;
  user_name?: string;
  message: string;
}

export interface SyncJobResponse {
  job_id: string;
  connector_id: string;
  mode: string;
  status: string;
  records_synced: number;
  docs_indexed: number;
  started_at: string;
  finished_at?: string | null;
  error_message?: string | null;
}

export class ApiError extends Error {
  status: number;
  data: any;

  constructor(status: number, message: string, data?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

// Token helper methods
export const TOKEN_KEY = 'mnemograph_token';

export const getToken = (): string | null => {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(TOKEN_KEY);
};

export const setToken = (token: string): void => {
  if (typeof window === 'undefined') return;
  localStorage.setItem(TOKEN_KEY, token);
};

export const clearToken = (): void => {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(TOKEN_KEY);
};

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };

  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const url = `${API_BASE_URL}${endpoint}`;

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorDetail = response.statusText;
    let data;
    try {
      data = await response.json();
      if (data && data.detail) {
        errorDetail = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
      }
    } catch {
      // response is not JSON
    }

    if (response.status === 401 && typeof window !== 'undefined') {
      clearToken();
    }

    throw new ApiError(response.status, errorDetail, data);
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

export const api = {
  auth: {
    register: (data: UserRegisterInput): Promise<AuthTokenResponse> =>
      request<AuthTokenResponse>('/auth/register', {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    login: (data: UserLoginInput): Promise<AuthTokenResponse> =>
      request<AuthTokenResponse>('/auth/login', {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    forgotPassword: (email: string): Promise<{ message: string }> =>
      request<{ message: string }>('/auth/forgot-password', {
        method: 'POST',
        body: JSON.stringify({ email }),
      }),

    resetPassword: (token: string, new_password: string): Promise<{ message: string }> =>
      request<{ message: string }>('/auth/reset-password', {
        method: 'POST',
        body: JSON.stringify({ token, new_password }),
      }),
  },

  users: {
    getMe: (): Promise<UserResponse> =>
      request<UserResponse>('/users/me'),

    updateProfile: (data: UserUpdateInput): Promise<UserResponse> =>
      request<UserResponse>('/users/me', {
        method: 'PUT',
        body: JSON.stringify(data),
      }),

    uploadAvatar: (file: File): Promise<UserResponse> => {
      const formData = new FormData();
      formData.append('file', file);
      return request<UserResponse>('/users/me/avatar', {
        method: 'POST',
        body: formData,
      });
    },

    deleteAvatar: (): Promise<UserResponse> =>
      request<UserResponse>('/users/me/avatar', {
        method: 'DELETE',
      }),
  },

  connectors: {
    list: (): Promise<ConnectorResponse[]> =>
      request<ConnectorResponse[]>('/connectors'),

    get: (id: string): Promise<ConnectorResponse> =>
      request<ConnectorResponse>(`/connectors/databricks/${id}`),

    testDatabricks: (data: DatabricksTestInput): Promise<TestConnectionResponse> =>
      request<TestConnectionResponse>('/connectors/databricks/test-connection', {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    getWarehouses: (data: DatabricksTestInput): Promise<WarehouseItem[]> =>
      request<WarehouseItem[]>('/connectors/databricks/warehouses', {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    getCatalogs: (data: DatabricksTestInput): Promise<TableItem[]> =>
      request<TableItem[]>('/connectors/databricks/catalogs', {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    createDatabricks: (data: DatabricksCreateInput): Promise<ConnectorResponse> =>
      request<ConnectorResponse>('/connectors/databricks', {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    delete: (connectorId: string): Promise<{ status: string; message: string }> =>
      request<{ status: string; message: string }>(`/connectors/${connectorId}`, {
        method: 'DELETE',
      }),

    triggerSync: (connectorId: string, mode: 'full' | 'incremental' = 'full'): Promise<SyncJobResponse> =>
      request<SyncJobResponse>(`/connectors/databricks/${connectorId}/sync`, {
        method: 'POST',
        body: JSON.stringify({ mode }),
      }),

    getSyncJobStatus: (connectorId: string, jobId: string): Promise<SyncJobResponse> =>
      request<SyncJobResponse>(`/connectors/databricks/${connectorId}/sync/${jobId}`),

    uploadDocument: (formData: FormData): Promise<any> =>
      request<any>('/connectors/documents/upload', {
        method: 'POST',
        body: formData,
      }),
  },

  hub: {
    // People & Knowledge Handover
    listPeople: (): Promise<any[]> => request<any[]>('/people'),
    getPerson: (id: string): Promise<any> => request<any>(`/people/${id}`),
    getPersonFullProfile: (id: string): Promise<any> => request<any>(`/people/${id}/full-profile`),
    createHandover: (id: string, data: { target_employee_id: string; scope?: string; notes?: string }): Promise<any> =>
      request<any>(`/people/${id}/handover`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    getPersonDecisions: (id: string): Promise<any[]> => request<any[]>(`/people/${id}/decisions`),

    // Teams
    listTeams: (): Promise<any[]> => request<any[]>('/teams'),
    getTeam: (id: string): Promise<any> => request<any>(`/teams/${id}`),
    getTeamDecisions: (id: string): Promise<any[]> => request<any[]>(`/teams/${id}/decisions`),

    // Projects
    listProjects: (): Promise<any[]> => request<any[]>('/projects'),
    getProject: (id: string): Promise<any> => request<any>(`/projects/${id}`),
    getProjectDecisions: (id: string): Promise<any[]> => request<any[]>(`/projects/${id}/decisions`),
    getProjectMentions: (id: string): Promise<any[]> => request<any[]>(`/projects/${id}/mentions`),

    // Documents
    listDocuments: (): Promise<any[]> => request<any[]>('/documents'),
    getDocument: (id: string): Promise<any> => request<any>(`/documents/${id}`),
    getDocumentSections: (id: string): Promise<any[]> => request<any[]>(`/documents/${id}/sections`),
    getDocumentEntities: (id: string): Promise<any[]> => request<any[]>(`/documents/${id}/entities`),
    getDocumentMentions: (id: string): Promise<any[]> => request<any[]>(`/documents/${id}/mentions`),
    getDocumentDecisions: (id: string): Promise<any[]> => request<any[]>(`/documents/${id}/decisions`),
    getDocumentPermissions: (id: string): Promise<any> => request<any>(`/documents/${id}/permissions`),

    // Search & Answer Engine
    search: (data: { query: string; project_id?: string; workspace_id?: string; limit?: number }): Promise<any> =>
      request<any>('/search', {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    getAnswer: (data: { query: string; project_id?: string; workspace_id?: string; limit?: number }): Promise<any> =>
      request<any>('/answers', {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    getContextAnswer: (data: { query: string; entity_id: string }): Promise<any> =>
      request<any>('/answers/context', {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    // Multi-Store Collections
    listCollections: (): Promise<any[]> => request<any[]>('/collections'),
    deleteCollection: (storeType: string, collectionId: string): Promise<any> =>
      request<any>(`/collections/${storeType}/${collectionId}`, {
        method: 'DELETE',
      }),

    // Graphiti Temporal Agent Memory
    getMemoryHistory: (order: 'asc' | 'desc' = 'asc'): Promise<any[]> => request<any[]>(`/memory/history?order=${order}`),
    getEpisodeDetails: (id: string): Promise<any> => request<any>(`/memory/history/${id}`),
    getMemorySessions: (): Promise<any[]> => request<any[]>('/memory/sessions'),
    getMemoryEntities: (): Promise<any[]> => request<any[]>('/memory/entities'),
    deleteMemorySession: (sessionId: string): Promise<any> => request<any>(`/memory/sessions/${sessionId}`, { method: 'DELETE' }),

    // Graph Queries
    getUserSubgraph: (): Promise<any> => request<any>('/graph/user-subgraph'),
    runGraphQuery: (data: { cypher: string; limit?: number }): Promise<any> =>
      request<any>('/graph/query', {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    // Decisions
    listDecisions: (): Promise<any[]> => request<any[]>('/decisions'),
    getDecision: (id: string): Promise<any> => request<any>(`/decisions/${id}`),
    getDecisionProvenance: (id: string): Promise<any> => request<any>(`/decisions/${id}/provenance`),
    addDecisionLink: (id: string, data: { related_entity_type: string; related_entity_id: string; relation_type?: string }): Promise<any> =>
      request<any>(`/decisions/${id}/links`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),
  },
};

