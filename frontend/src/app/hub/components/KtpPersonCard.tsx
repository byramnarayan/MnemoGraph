'use client';

import React from 'react';
import { KtpPersonSummary } from '../types';

interface KtpPersonCardProps {
  person: KtpPersonSummary;
  isSelected: boolean;
  onSelect: (person: KtpPersonSummary) => void;
}

export function KtpPersonCard({ person, isSelected, onSelect }: KtpPersonCardProps) {
  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'active':
      case 'employed':
        return 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20';
      case 'on_leave':
        return 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20';
      case 'departing':
      case 'inactive':
      case 'resigned':
        return 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20';
      default:
        return 'bg-muted text-muted-foreground border-border';
    }
  };

  const initials = person.full_name
    ? person.full_name
        .split(' ')
        .map((n) => n[0])
        .slice(0, 2)
        .join('')
        .toUpperCase()
    : '??';

  return (
    <div
      onClick={() => onSelect(person)}
      className={`group relative p-3.5 rounded-xl border transition-all cursor-pointer select-none ${
        isSelected
          ? 'bg-card border-accent shadow-sm ring-1 ring-accent/30'
          : 'bg-card/40 hover:bg-card/80 border-border hover:border-accent/40'
      }`}
    >
      <div className="flex items-start gap-3">
        <div className="w-9 h-9 rounded-lg bg-muted border border-border flex items-center justify-center font-mono text-xs font-semibold text-foreground shrink-0">
          {initials}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-1.5 mb-0.5">
            <h4 className="text-sm font-medium text-foreground truncate">
              {person.full_name}
            </h4>
            <span
              className={`text-[10px] uppercase font-mono px-1.5 py-0.5 rounded border shrink-0 ${getStatusColor(
                person.employment_status
              )}`}
            >
              {person.employment_status}
            </span>
          </div>

          <p className="text-xs text-muted-foreground truncate mb-2">
            {person.role || 'Member'} • {person.group || person.location || 'Institutional'}
          </p>

          <div className="flex flex-wrap items-center gap-1.5">
            {person.is_handed_over_to_me && (
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-indigo-500/15 text-indigo-600 dark:text-indigo-300 border border-indigo-500/30">
                Handed Over To You
              </span>
            )}

            {person.ktp_generated && (
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-purple-500/15 text-purple-600 dark:text-purple-300 border border-purple-500/30">
                KTP Locked
              </span>
            )}

            {person.concentration_risk && (
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-600 dark:text-amber-300 border border-amber-500/30">
                Key Person Risk
              </span>
            )}

            <span className="text-[10px] font-mono text-muted-foreground ml-auto">
              {person.active_projects_count} projs • {person.open_tasks_count} tasks
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

