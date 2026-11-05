'use client';

import React from 'react';
import { SectionCDecisionHistory } from '../types';

interface KtpDecisionsSectionProps {
  decisions: SectionCDecisionHistory | null;
}

export function KtpDecisionsSection({ decisions }: KtpDecisionsSectionProps) {
  const made = decisions?.decisions_made || [];
  const contributed = decisions?.decisions_contributed || [];

  if (made.length === 0 && contributed.length === 0) {
    return (
      <div className="p-6 text-center text-xs text-muted-foreground font-mono bg-card/30 rounded-xl border border-border">
        No institutional decision history recorded for this individual.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Decisions Made */}
      <div className="space-y-3">
        <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-muted-foreground">
          Decisions Made ({made.length})
        </h4>

        {made.length > 0 ? (
          <div className="space-y-3">
            {made.map((d) => (
              <div
                key={d.decision_id}
                className="p-4 rounded-xl bg-card border border-border space-y-2.5 text-xs shadow-xs"
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h5 className="font-semibold text-foreground">{d.title}</h5>
                    <div className="flex items-center gap-3 text-[11px] font-mono text-muted-foreground mt-0.5">
                      <span>Type: {d.decision_type || 'Operational'}</span>
                      <span>Date: {d.decision_date || 'N/A'}</span>
                      {d.open_tasks_count > 0 && (
                        <span className="text-amber-600 dark:text-amber-400 font-medium">
                          {d.open_tasks_count} tasks still open
                        </span>
                      )}
                    </div>
                  </div>
                  <span
                    className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded border ${
                      d.outcome === 'positive'
                        ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-300 border-emerald-500/30'
                        : d.outcome === 'negative'
                        ? 'bg-rose-500/10 text-rose-600 dark:text-rose-300 border-rose-500/30'
                        : 'bg-muted text-muted-foreground border-border'
                    }`}
                  >
                    {d.outcome || 'Pending'}
                  </span>
                </div>

                {/* Root Cause Analysis if negative/recorded */}
                {d.root_cause_analysis && (
                  <div className="p-3 rounded-lg bg-background border border-border space-y-1">
                    <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-amber-600 dark:text-amber-400">
                      Root Cause Analysis (RCA)
                    </span>
                    <p className="text-[11px] text-foreground leading-relaxed">
                      {d.root_cause_analysis}
                    </p>
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-muted-foreground font-mono">No decisions authored directly.</p>
        )}
      </div>

      {/* Decisions Contributed */}
      {contributed.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-muted-foreground">
            Decisions Contributed Via Project ({contributed.length})
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {contributed.map((d) => (
              <div
                key={d.decision_id}
                className="p-3 rounded-lg bg-card/60 border border-border text-xs space-y-1"
              >
                <div className="font-medium text-foreground">{d.title}</div>
                <div className="text-[10px] font-mono text-muted-foreground">
                  Project: {d.project_name || 'N/A'} • Outcome: {d.outcome || 'Pending'}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

