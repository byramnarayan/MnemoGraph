'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { UserResponse } from '@/lib/api-client';
import { DiscoveredPerson } from '../types';
import { ProvisionUserModal } from './ProvisionUserModal';
import { getToken } from '@/lib/api-client';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

interface Phase8ProvisioningSectionProps {
  currentUser: UserResponse;
}

export function Phase8ProvisioningSection({ currentUser }: Phase8ProvisioningSectionProps) {
  const isAdmin = Boolean(
    currentUser.role &&
      ['admin', 'executive', 'director', 'vp'].some((k) =>
        currentUser.role.toLowerCase().includes(k)
      )
  );

  const [candidates, setCandidates] = useState<DiscoveredPerson[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [selectedPerson, setSelectedPerson] = useState<DiscoveredPerson | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const loadDiscoveredPersonnel = useCallback(async () => {
    if (!isAdmin) return;
    try {
      setIsLoading(true);
      setErrorMsg(null);
      const token = getToken();
      const res = await fetch(`${API_BASE_URL}/users/discovered-personnel`, {
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });

      if (!res.ok) {
        if (res.status === 403) return;
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to fetch discovered personnel.');
      }

      const data: DiscoveredPerson[] = await res.json();
      setCandidates(data || []);
    } catch (err: any) {
      setErrorMsg(err.message || 'Error loading discovered personnel.');
    } finally {
      setIsLoading(false);
    }
  }, [isAdmin]);

  useEffect(() => {
    loadDiscoveredPersonnel();
  }, [loadDiscoveredPersonnel]);

  const handleOpenProvision = (person: DiscoveredPerson) => {
    setSelectedPerson(person);
    setIsModalOpen(true);
  };

  return (
    <div className="mb-8 space-y-4 font-mono">
      {/* User Institutional Graph Clearance & Entity Status */}
      <div className="p-4 rounded-xl border border-border bg-card/60 backdrop-blur-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-foreground">
              Institutional Graph Identity & Role Clearance
            </h3>
          </div>
          <p className="text-[11px] text-muted-foreground">
            Linked Person Entity ID:{' '}
            <span className="text-foreground font-semibold">
              {currentUser.person_entity_id || 'Not linked to Person node'}
            </span>
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <span className="px-2.5 py-1 rounded-md bg-muted border border-border text-foreground font-semibold">
            {currentUser.role}
          </span>
          <span className="px-2.5 py-1 rounded-md bg-accent/15 border border-accent/30 text-accent font-semibold">
            Clearance: {currentUser.clearance_level || 'Internal'}
          </span>
        </div>
      </div>

      {/* Discovered Personnel Onboarding Queue (Admins Only) */}
      {isAdmin && (
        <div className="p-5 rounded-2xl border border-border bg-card shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-border pb-3">
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-foreground flex items-center gap-2">
                <span>Discovered Personnel Onboarding Queue</span>
                <span className="px-2 py-0.5 rounded-full text-[10px] bg-muted border border-border text-muted-foreground">
                  {candidates.length} Pending
                </span>
              </h3>
              <p className="text-[11px] text-muted-foreground mt-0.5">
                Personnel entities extracted from ingested institutional documents awaiting account provisioning.
              </p>
            </div>
            <button
              onClick={loadDiscoveredPersonnel}
              disabled={isLoading}
              className="px-2.5 py-1 text-[11px] rounded border border-border bg-background hover:bg-card text-muted-foreground hover:text-foreground transition-colors"
            >
              {isLoading ? 'Scanning...' : 'Refresh'}
            </button>
          </div>

          {errorMsg && (
            <div className="p-3 text-xs rounded-lg bg-rose-500/15 border border-rose-500/30 text-rose-600 dark:text-rose-300">
              {errorMsg}
            </div>
          )}

          {isLoading ? (
            <div className="py-8 text-center text-xs text-muted-foreground">
              Scanning canonical graph for discovered un-provisioned personnel...
            </div>
          ) : candidates.length === 0 ? (
            <div className="py-6 text-center text-xs text-muted-foreground">
              All discovered personnel from ingested documents have been provisioned or linked.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-border text-muted-foreground text-[10px] uppercase tracking-wider">
                    <th className="py-2 px-3">Candidate Name</th>
                    <th className="py-2 px-3">Entity ID</th>
                    <th className="py-2 px-3">Inferred Role & Dept</th>
                    <th className="py-2 px-3">Mentions</th>
                    <th className="py-2 px-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {candidates.map((c) => (
                    <tr key={c.entity_id} className="hover:bg-muted/40 transition-colors">
                      <td className="py-3 px-3 font-semibold text-foreground">
                        {c.full_name}
                      </td>
                      <td className="py-3 px-3 text-muted-foreground text-[11px]">
                        {c.entity_id}
                      </td>
                      <td className="py-3 px-3 text-muted-foreground text-[11px]">
                        {c.inferred_role || 'Staff Member'} • {c.inferred_department || 'Engineering'}
                      </td>
                      <td className="py-3 px-3 text-muted-foreground text-[11px]">
                        {c.mention_count} docs
                      </td>
                      <td className="py-3 px-3 text-right">
                        <button
                          onClick={() => handleOpenProvision(c)}
                          className="px-3 py-1 rounded-md bg-accent text-accent-foreground font-semibold text-[11px] hover:opacity-90 transition-opacity"
                        >
                          Provision Account
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Provisioning Modal */}
      <ProvisionUserModal
        isOpen={isModalOpen}
        person={selectedPerson}
        onClose={() => setIsModalOpen(false)}
        onSuccess={() => {
          loadDiscoveredPersonnel();
        }}
      />
    </div>
  );
}

