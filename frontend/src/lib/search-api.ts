import { clearToken, getToken } from '@/lib/api-client';
import { UKGOEAnswerData, UniversalCollection, MemoryEpisode } from '@/app/search/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

function getAuthHeader(): Record<string, string> {
  if (typeof window === 'undefined') return {};
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    if (res.status === 401 && typeof window !== 'undefined') {
      clearToken();
      window.location.href = '/login?expired=true';
    }
    let errorDetail = `Request failed with status ${res.status}`;
    try {
      const errJson = await res.json();
      if (errJson && errJson.detail) {
        errorDetail = errJson.detail;
      }
    } catch {
      // Fallback message
    }
    throw new Error(errorDetail);
  }
  return res.json() as Promise<T>;
}

export const searchApi = {
  /**
   * Universal Search & Answer Engine (UKGOE Part 5 Grounding)
   */
  async search(query: string, options?: { limit?: number; clearance?: string }): Promise<UKGOEAnswerData> {
    const res = await fetch(`${API_BASE_URL}/search`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify({
        query,
        limit: options?.limit || 6,
        classification_clearance: options?.clearance || 'Internal',
      }),
    });
    return handleResponse<UKGOEAnswerData>(res);
  },

  /**
   * Multi-Store Collections across Universal Tiers
   */
  async listCollections(): Promise<UniversalCollection[]> {
    const res = await fetch(`${API_BASE_URL}/collections`, {
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
    });
    return handleResponse<UniversalCollection[]>(res);
  },

  /**
   * Delete or purge a collection (Admin only)
   */
  async deleteCollection(storeType: string, collectionId: string): Promise<{ message: string }> {
    const res = await fetch(`${API_BASE_URL}/collections/${storeType}/${collectionId}`, {
      method: 'DELETE',
      headers: {
        ...getAuthHeader(),
      },
    });
    return handleResponse<{ message: string }>(res);
  },

  /**
   * Graphiti Episodic Memory Audit History
   */
  async getMemoryHistory(order: 'asc' | 'desc' = 'asc'): Promise<MemoryEpisode[]> {
    const res = await fetch(`${API_BASE_URL}/memory/history?order=${order}`, {
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
    });
    return handleResponse<MemoryEpisode[]>(res);
  },

  /**
   * Universal Knowledge Graph Queries (openCypher execution)
   */
  async runGraphQuery(cypher: string, limit: number = 40): Promise<{ nodes: any[]; edges: any[] }> {
    const res = await fetch(`${API_BASE_URL}/graph/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify({ cypher, limit }),
    });
    return handleResponse<{ nodes: any[]; edges: any[] }>(res);
  },

  /**
   * Current user's authorized institutional subgraph
   */
  async getUserSubgraph(): Promise<{ nodes: any[]; edges: any[] }> {
    const res = await fetch(`${API_BASE_URL}/graph/user-subgraph`, {
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
    });
    return handleResponse<{ nodes: any[]; edges: any[] }>(res);
  },
};
