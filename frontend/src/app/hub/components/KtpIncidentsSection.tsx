'use client';

import React from 'react';
import { SectionDIncidentInvolvement } from '../types';

interface KtpIncidentsSectionProps {
  involvement: SectionDIncidentInvolvement | null;
}

export function KtpIncidentsSection({ involvement }: KtpIncidentsSectionProps) {
  const asAssignee = involvement?.incidents_as_task_assignee || [];
  const asLead = involvement?.incidents_as_project_lead || [];

  if (asAssignee.length === 0 && asLead.length === 0) {
    return (
      <div className="p-6 text-center text-xs text-muted-foreground font-mono bg-card/30 rounded-xl border border-border">
        No incident involvements recorded for this individual.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Incidents as Task Assignee */}
      {asAssignee.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-muted-foreground">
            Incidents as Task Assignee ({asAssignee.length})
          </h4>
          <div className="space-y-3">
            {asAssignee.map((inc) => (
              <div
                key={inc.incident_id}
                className="p-4 rounded-xl bg-card border border-border space-y-3 text-xs shadow-xs"
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h5 className="font-semibold text-foreground">{inc.title}</h5>
                    <div className="flex items-center gap-3 text-[11px] font-mono text-muted-foreground mt-0.5">
                      <span>Type: {inc.type || 'Operational'}</span>
                      <span>Cause Status: {inc.cause_status || 'Pending'}</span>
                    </div>
                  </div>
                  <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-rose-500/10 text-rose-600 dark:text-rose-300 border border-rose-500/30">
                    {inc.severity || 'Incident'}
                  </span>
                </div>

                {/* Subgraph: Corrective Tasks */}
                {inc.tasks.length > 0 && (
                  <div className="space-y-1.5 pt-2 border-t border-border">
                    <span className="text-[10px] font-mono uppercase text-muted-foreground tracking-wider">
                      Corrective Tasks ({inc.tasks.length})
                    </span>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-1.5">
                      {inc.tasks.map((t) => (
                        <div
                          key={t.task_id}
                          className="p-2 rounded bg-background border border-border flex items-center justify-between"
                        >
                          <span className="truncate pr-2 text-foreground">{t.title}</span>
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-muted text-muted-foreground border border-border">
                            {t.status}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Subgraph: PIR Documents */}
                {inc.pir_documents.length > 0 && (
                  <div className="flex items-center gap-2 pt-1 text-[11px] font-mono text-muted-foreground">
                    <span className="text-muted-foreground">PIR Documents:</span>
                    {inc.pir_documents.map((p) => (
                      <span
                        key={p.id}
                        className="px-2 py-0.5 rounded bg-muted text-foreground border border-border"
                      >
                        {p.title}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Incidents as Project Lead */}
      {asLead.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-muted-foreground">
            Incidents Under Led Projects ({asLead.length})
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {asLead.map((inc) => (
              <div
                key={inc.incident_id}
                className="p-3 rounded-lg bg-card/60 border border-border text-xs space-y-1"
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium text-foreground truncate pr-2">{inc.title}</span>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-rose-500/10 text-rose-600 dark:text-rose-300 border border-rose-500/20">
                    {inc.severity || 'Incident'}
                  </span>
                </div>
                <div className="text-[10px] font-mono text-muted-foreground">
                  Project: {inc.project_name || 'N/A'} • Cause: {inc.cause_status || 'Pending'}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

