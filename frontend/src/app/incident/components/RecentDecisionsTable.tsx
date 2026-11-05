'use client';

import React from 'react';
import { DecisionFollowUpSummary } from '../types';

interface RecentDecisionsTableProps {
  decisions: DecisionFollowUpSummary[];
}

export function RecentDecisionsTable({ decisions }: RecentDecisionsTableProps) {
  if (!decisions || decisions.length === 0) return null;

  return (
    <section className="space-y-2 font-mono">
      <div className="flex items-center justify-between">
        <h2 className="text-xs font-bold uppercase tracking-wider text-foreground">
          Recent Decisions Follow-Up ({decisions.length})
        </h2>
      </div>

      <div className="border border-border rounded-xl overflow-hidden bg-card text-[11px]">
        <div className="grid grid-cols-12 bg-muted/50 p-2.5 font-semibold text-muted-foreground border-b border-border">
          <span className="col-span-5">Decision & Maker</span>
          <span className="col-span-3">Action Implemented</span>
          <span className="col-span-2">Follow-up</span>
          <span className="col-span-2 text-right">Observation Status</span>
        </div>

        <div className="divide-y divide-border/60 max-h-52 overflow-y-auto">
          {decisions.map((d) => (
            <div key={d.decision_id} className="grid grid-cols-12 p-2.5 items-center hover:bg-muted/20">
              <div className="col-span-5 truncate pr-2">
                <span className="font-semibold text-foreground truncate block">{d.decision_title}</span>
                <span className="text-[10px] text-muted-foreground">{d.decision_maker || 'Institutional Lead'}</span>
              </div>
              <span className="col-span-3 text-muted-foreground truncate">
                {d.related_action_title || 'Direct Configuration'}
              </span>
              <span className="col-span-2 text-muted-foreground">{d.follow_up_days} days</span>
              <span
                className={`col-span-2 text-right font-semibold truncate ${
                  d.follow_up_status.includes('NO_LINKED') ? 'text-emerald-400' : 'text-amber-400'
                }`}
              >
                {d.follow_up_status.replace(/_/g, ' ')}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

