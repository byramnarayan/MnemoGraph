'use client';

import React from 'react';
import { SectionBActiveOwnership } from '../types';

interface KtpProjectsSectionProps {
  ownership: SectionBActiveOwnership | null;
}

export function KtpProjectsSection({ ownership }: KtpProjectsSectionProps) {
  const projects = ownership?.active_projects || [];

  if (projects.length === 0) {
    return (
      <div className="p-6 text-center text-xs text-muted-foreground font-mono bg-card/30 rounded-xl border border-border">
        No active project ownerships recorded for this individual.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {projects.map((proj) => (
        <div
          key={proj.project_id}
          className="p-5 rounded-xl bg-card border border-border space-y-4 shadow-xs"
        >
          {/* Project Header */}
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <h4 className="text-sm font-semibold text-foreground font-mono">
                  {proj.name}
                </h4>
                <span
                  className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded border ${
                    proj.relationship === 'LEADS'
                      ? 'bg-purple-500/10 text-purple-600 dark:text-purple-300 border-purple-500/30'
                      : 'bg-accent/10 text-accent border-accent/30'
                  }`}
                >
                  {proj.relationship}
                </span>
                <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-muted border border-border text-muted-foreground">
                  {proj.status}
                </span>
              </div>
              <p className="text-[11px] font-mono text-muted-foreground">ID: {proj.project_id}</p>
            </div>
          </div>

          {/* Subgraph: Milestones */}
          {proj.milestones.length > 0 && (
            <div className="space-y-1.5 pt-2 border-t border-border">
              <h5 className="text-[11px] font-mono uppercase text-muted-foreground tracking-wider">
                Current Milestones ({proj.milestones.length})
              </h5>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {proj.milestones.map((m) => (
                  <div
                    key={m.id}
                    className="p-2.5 rounded-lg bg-background border border-border text-xs flex items-center justify-between"
                  >
                    <div>
                      <div className="font-medium text-foreground">{m.name}</div>
                      <div className="text-[10px] text-muted-foreground font-mono">
                        Target: {m.target_date || 'Ongoing'}
                      </div>
                    </div>
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-muted text-muted-foreground border border-border">
                      {m.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Subgraph: Linked Decisions & Linked Incidents */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2 border-t border-border">
            {/* Linked Decisions */}
            <div>
              <h5 className="text-[11px] font-mono uppercase text-muted-foreground tracking-wider mb-1.5">
                Linked Decisions ({proj.linked_decisions.length})
              </h5>
              {proj.linked_decisions.length > 0 ? (
                <div className="space-y-1">
                  {proj.linked_decisions.map((d) => (
                    <div
                      key={d.id}
                      className="p-2 rounded bg-background border border-border text-xs"
                    >
                      <div className="text-foreground font-medium">{d.title}</div>
                      {d.outcome && (
                        <div className="text-[10px] text-muted-foreground font-mono">
                          Outcome: {d.outcome}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-[11px] text-muted-foreground font-mono">None linked.</p>
              )}
            </div>

            {/* Linked Incidents */}
            <div>
              <h5 className="text-[11px] font-mono uppercase text-muted-foreground tracking-wider mb-1.5">
                Linked Incidents ({proj.linked_incidents.length})
              </h5>
              {proj.linked_incidents.length > 0 ? (
                <div className="space-y-1">
                  {proj.linked_incidents.map((i) => (
                    <div
                      key={i.id}
                      className="p-2 rounded bg-background border border-border text-xs flex items-center justify-between"
                    >
                      <span className="text-foreground font-medium truncate pr-2">{i.title}</span>
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-rose-500/10 text-rose-600 dark:text-rose-300 border border-rose-500/20 shrink-0">
                        {i.severity || 'Incident'}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-[11px] text-muted-foreground font-mono">None linked.</p>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

