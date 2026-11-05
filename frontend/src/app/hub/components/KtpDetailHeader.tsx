'use client';

import React from 'react';
import { KnowledgeTransferPackageResponse, KtpPersonSummary } from '../types';

interface KtpDetailHeaderProps {
  person: KtpPersonSummary;
  ktpData: KnowledgeTransferPackageResponse | null;
  onOpenHandoverModal: () => void;
  onLockKtp: () => void;
  isLocking: boolean;
}

export function KtpDetailHeader({
  person,
  ktpData,
  onOpenHandoverModal,
  onLockKtp,
  isLocking,
}: KtpDetailHeaderProps) {
  const profile = ktpData?.section_a_profile;

  return (
    <div className="border-b border-border bg-card/70 p-6 space-y-4">
      {/* IR-09 Cascade Warning Banner */}
      {ktpData?.is_stale && (
        <div className="p-3 rounded-lg bg-amber-500/15 border border-amber-500/30 text-amber-700 dark:text-amber-200 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="font-mono font-bold text-amber-600 dark:text-amber-400">[IR-09 CASCADE ALERT]</span>
            <span>{ktpData.cascade_warning || 'Downstream entities modified. Stale subgraph detected.'}</span>
          </div>
          <button
            onClick={onLockKtp}
            disabled={isLocking}
            className="px-2.5 py-1 text-[11px] font-mono bg-amber-500/20 hover:bg-amber-500/30 text-amber-700 dark:text-amber-300 rounded border border-amber-500/40"
          >
            {isLocking ? 'Recomputing...' : 'Recompute Now'}
          </button>
        </div>
      )}

      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        {/* Left: Info */}
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-foreground font-mono tracking-tight">
              {profile?.full_name || person.full_name}
            </h1>
            <span className="px-2 py-0.5 text-xs font-mono rounded bg-muted border border-border text-muted-foreground font-semibold">
              {ktpData?.classification || person.clearance_level}
            </span>
            {person.ktp_generated && (
              <span className="px-2 py-0.5 text-xs font-mono rounded bg-purple-500/20 border border-purple-500/40 text-purple-600 dark:text-purple-300 font-semibold">
                LOCKED KTP
              </span>
            )}
          </div>

          <p className="text-xs text-muted-foreground">
            {profile?.current_role || person.role || 'Member'} • {profile?.current_group || person.group || 'Team'} • {profile?.location || person.location || 'HQ'}
            <span className="mx-2 text-border">|</span>
            <span className="font-mono text-muted-foreground">ID: {person.person_id}</span>
          </p>
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-2.5">
          <button
            onClick={onOpenHandoverModal}
            className="px-3.5 py-1.5 text-xs font-medium rounded-lg bg-muted hover:bg-card text-foreground border border-border hover:border-accent/40 transition-colors flex items-center gap-2"
          >
            <span>Assign / Send Handover</span>
          </button>

          <button
            onClick={onLockKtp}
            disabled={isLocking}
            className="px-3.5 py-1.5 text-xs font-medium rounded-lg bg-accent hover:opacity-90 disabled:opacity-50 text-accent-foreground font-semibold shadow-sm transition-colors flex items-center gap-2"
          >
            <span>{isLocking ? 'Generating...' : person.ktp_generated ? 'Re-lock KTP' : 'Lock & Generate KTP'}</span>
          </button>
        </div>
      </div>
    </div>
  );
}

