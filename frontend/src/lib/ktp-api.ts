import {
  AssignHandoverRequest,
  AssignHandoverResponse,
  KnowledgeTransferPackageResponse,
  KtpPersonSummary,
} from '@/app/hub/types';

import { clearToken, getToken } from '@/lib/api-client';

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
      // If unauthorized / token expired, redirect to login cleanly
      window.location.href = '/login?expired=true';
    }
    let errorDetail = `Request failed with status ${res.status}`;
    try {
      const errJson = await res.json();
      if (errJson && errJson.detail) {
        errorDetail = errJson.detail;
      }
    } catch {
      // Use fallback errorDetail
    }
    throw new Error(errorDetail);
  }
  return res.json() as Promise<T>;
}

export const ktpApi = {
  /**
   * Lists personnel visible to current user (role & successor gated).
   */
  async listPersonnel(status?: string): Promise<KtpPersonSummary[]> {
    const url = new URL(`${API_BASE_URL}/ktp/people`);
    if (status) {
      url.searchParams.set('status', status);
    }
    const res = await fetch(url.toString(), {
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
    });
    return handleResponse<KtpPersonSummary[]>(res);
  },

  /**
   * Retrieves the full interconnected institutional subgraph for a person.
   */
  async getPersonKtp(personId: string): Promise<KnowledgeTransferPackageResponse> {
    const res = await fetch(`${API_BASE_URL}/ktp/people/${encodeURIComponent(personId)}`, {
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
    });
    return handleResponse<KnowledgeTransferPackageResponse>(res);
  },

  /**
   * Generates and locks a formal KTP Document node in FalkorDB.
   */
  async generateKtp(personId: string): Promise<KnowledgeTransferPackageResponse> {
    const res = await fetch(`${API_BASE_URL}/ktp/generate/${encodeURIComponent(personId)}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
    });
    return handleResponse<KnowledgeTransferPackageResponse>(res);
  },

  /**
   * Retrieves a generated KTP document by ID, checking staleness.
   */
  async getKtpDocument(docId: string): Promise<KnowledgeTransferPackageResponse> {
    const res = await fetch(`${API_BASE_URL}/ktp/${encodeURIComponent(docId)}`, {
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
    });
    return handleResponse<KnowledgeTransferPackageResponse>(res);
  },

  /**
   * Assigns a person's knowledge handover to another team member (successor).
   */
  async assignHandover(
    personId: string,
    req: AssignHandoverRequest
  ): Promise<AssignHandoverResponse> {
    const res = await fetch(`${API_BASE_URL}/ktp/people/${encodeURIComponent(personId)}/assign-handover`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify(req),
    });
    return handleResponse<AssignHandoverResponse>(res);
  },
};

