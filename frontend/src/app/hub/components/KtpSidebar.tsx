'use client';

import React, { useMemo, useState } from 'react';
import { KtpPersonSummary } from '../types';
import { KtpPersonCard } from './KtpPersonCard';

interface KtpSidebarProps {
  people: KtpPersonSummary[];
  selectedPerson: KtpPersonSummary | null;
  onSelectPerson: (person: KtpPersonSummary) => void;
  isLoading: boolean;
  activeFilter: string;
  onFilterChange: (filter: string) => void;
}

export function KtpSidebar({
  people,
  selectedPerson,
  onSelectPerson,
  isLoading,
  activeFilter,
  onFilterChange,
}: KtpSidebarProps) {
  const [searchQuery, setSearchQuery] = useState('');

  const filteredPeople = useMemo(() => {
    const list = people.filter((p) => {
      // 1. Hide synthetic test duplicates with no activity unless user searches for them
      if (p.person_id.startsWith('dup_') && !searchQuery.trim() && activeFilter !== 'all_raw') {
        return false;
      }

      // 2. Status Filter
      if (activeFilter === 'departing') {
        const s = (p.employment_status || '').toLowerCase();
        if (!['on_leave', 'inactive', 'terminated', 'resigned', 'departing', 'departed'].includes(s)) {
          return false;
        }
      } else if (activeFilter === 'active') {
        const s = (p.employment_status || '').toLowerCase();
        if (!['active', 'employed'].includes(s)) {
          return false;
        }
      } else if (activeFilter === 'handed_over') {
        if (!p.is_handed_over_to_me) {
          return false;
        }
      }

      // 3. Search Query
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesName = (p.full_name || '').toLowerCase().includes(q);
        const matchesRole = (p.role || '').toLowerCase().includes(q);
        const matchesGroup = (p.group || '').toLowerCase().includes(q);
        const matchesId = (p.person_id || '').toLowerCase().includes(q);
        return matchesName || matchesRole || matchesGroup || matchesId;
      }

      return true;
    });

    // 4. Sort: prioritize rich profiles with active projects/tasks/KTPs first, then alphabetical
    return list.sort((a, b) => {
      const scoreA =
        (a.active_projects_count * 3) +
        (a.open_tasks_count * 2) +
        (a.ktp_generated ? 6 : 0) +
        (a.person_id.startsWith('person:') ? 10 : 0);
      const scoreB =
        (b.active_projects_count * 3) +
        (b.open_tasks_count * 2) +
        (b.ktp_generated ? 6 : 0) +
        (b.person_id.startsWith('person:') ? 10 : 0);

      if (scoreB !== scoreA) {
        return scoreB - scoreA;
      }
      return (a.full_name || '').localeCompare(b.full_name || '');
    });
  }, [people, activeFilter, searchQuery]);

  return (
    <aside className="w-full lg:w-96 flex flex-col border-r border-border bg-card/60 backdrop-blur-sm h-full shrink-0">
      {/* Top Search & Filter Bar */}
      <div className="p-4 border-b border-border space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-accent animate-pulse" />
            <h2 className="text-sm font-semibold text-foreground tracking-wide uppercase font-mono">
              Personnel Directory
            </h2>
          </div>
          <span className="text-xs font-mono text-muted-foreground">
            {filteredPeople.length} / {people.length}
          </span>
        </div>

        {/* Search Input */}
        <div className="relative">
          <input
            type="text"
            placeholder="Search by name, role, department..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-background border border-border rounded-lg px-3 py-2 text-xs text-foreground placeholder-muted-foreground focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground text-xs"
            >
              ×
            </button>
          )}
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-[11px] font-mono scrollbar-none">
          <button
            onClick={() => onFilterChange('all')}
            className={`px-2.5 py-1 rounded-md border whitespace-nowrap transition-colors ${
              activeFilter === 'all'
                ? 'bg-accent/20 text-accent border-accent/40 font-semibold'
                : 'bg-muted text-muted-foreground border-border hover:border-accent/40 hover:text-foreground'
            }`}
          >
            All
          </button>
          <button
            onClick={() => onFilterChange('departing')}
            className={`px-2.5 py-1 rounded-md border whitespace-nowrap transition-colors ${
              activeFilter === 'departing'
                ? 'bg-rose-500/20 text-rose-600 dark:text-rose-300 border-rose-500/40 font-semibold'
                : 'bg-muted text-muted-foreground border-border hover:border-accent/40 hover:text-foreground'
            }`}
          >
            Departing / On Leave
          </button>
          <button
            onClick={() => onFilterChange('handed_over')}
            className={`px-2.5 py-1 rounded-md border whitespace-nowrap transition-colors ${
              activeFilter === 'handed_over'
                ? 'bg-indigo-500/20 text-indigo-600 dark:text-indigo-300 border-indigo-500/40 font-semibold'
                : 'bg-muted text-muted-foreground border-border hover:border-accent/40 hover:text-foreground'
            }`}
          >
            Handed Over to Me
          </button>
          <button
            onClick={() => onFilterChange('active')}
            className={`px-2.5 py-1 rounded-md border whitespace-nowrap transition-colors ${
              activeFilter === 'active'
                ? 'bg-emerald-500/20 text-emerald-600 dark:text-emerald-300 border-emerald-500/40 font-semibold'
                : 'bg-muted text-muted-foreground border-border hover:border-accent/40 hover:text-foreground'
            }`}
          >
            Active
          </button>
        </div>
      </div>

      {/* Scrollable Person List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {isLoading ? (
          <div className="p-8 text-center text-xs text-muted-foreground font-mono">
            Loading directory...
          </div>
        ) : filteredPeople.length === 0 ? (
          <div className="p-8 text-center text-xs text-muted-foreground font-mono">
            No personnel found matching filter.
          </div>
        ) : (
          filteredPeople.map((person, idx) => (
            <KtpPersonCard
              key={`${person.person_id}-${idx}`}
              person={person}
              isSelected={selectedPerson?.person_id === person.person_id}
              onSelect={onSelectPerson}
            />
          ))
        )}
      </div>
    </aside>
  );
}

