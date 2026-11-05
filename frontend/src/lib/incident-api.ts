import { getToken } from '@/lib/api-client';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const errorJson = await res.json().catch(() => ({}));
    throw new Error(errorJson.detail || `Request failed with status ${res.status}`);
  }
  return res.json() as Promise<T>;
}

function getAuthHeaders(): HeadersInit {
  const token = getToken();
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

export const incidentApi = {
  async listUnlinkedDecisions(clearance: string = 'Internal') {
    const res = await fetch(`${API_BASE_URL}/incident-intelligence/unlinked-decisions?clearance=${encodeURIComponent(clearance)}`, {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    return handleResponse<any[]>(res);
  },

  async getDecisionDeepDive(decisionId: string, clearance: string = 'Internal') {
    const res = await fetch(`${API_BASE_URL}/incident-intelligence/decisions/${encodeURIComponent(decisionId)}/deep-dive?clearance=${encodeURIComponent(clearance)}`, {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    return handleResponse<any>(res);
  },

  async generateDecisionActionReport(decisionId: string, payload: any) {
    const res = await fetch(`${API_BASE_URL}/incident-intelligence/decisions/${encodeURIComponent(decisionId)}/generate-report`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(payload),
    });
    return handleResponse<any>(res);
  },

  async fetchPredictiveIntelligence(query: string, scope?: string) {
    const res = await fetch(`${API_BASE_URL}/search`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({
        query: scope ? `${query} on ${scope}` : query,
        limit: 5,
        classification_clearance: 'Internal',
      }),
    });
    return handleResponse<any>(res);
  },

  async generateActionProposal(scenarioData: any) {
    const res = await fetch(`${API_BASE_URL}/proposals/generate-draft`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ scenario_data: scenarioData }),
    });
    return handleResponse<any>(res);
  },

  async listProposals(limit = 20) {
    const res = await fetch(`${API_BASE_URL}/proposals?limit=${limit}`, {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    return handleResponse<any[]>(res);
  },

  async updateProposal(proposalId: string, updates: any) {
    const res = await fetch(`${API_BASE_URL}/proposals/${proposalId}`, {
      method: 'PUT',
      headers: getAuthHeaders(),
      body: JSON.stringify(updates),
    });
    return handleResponse<any>(res);
  },
};

