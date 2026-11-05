'use client';

import React from 'react';
import { SectionGHandoverRecommendations } from '../types';

interface KtpHandoverSectionProps {
  handover: SectionGHandoverRecommendations | null;
  onSelectSuccessor: (targetPersonId: string) => void;
}

export function KtpHandoverSection({ handover, onSelectSuccessor }: KtpHandoverSectionProps) {
  if (!handover) return null;

  const successors = handover.successor_candidates || [];
  const reassignTasks = handover.tasks_to_reassign || [];
  const replaceProjects = handover.projects_needing_lead_or_contributor || [];
  const soleAuthorDocs = handover.sole_author_documents || [];

  return (
    <div className="space-y-6">
      {/* Top 5 Ranked Successors (Derived from Graph Traversal) */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-foreground">
            Top Ranked Successor Candidates (Skill Overlap Traversal)
          </h4>
          <span className="text-[11px] font-mono text-muted-foreground">
            Same Group & Competencies
          </span>
        </div>

        {successors.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {successors.map((cand) => (
              <div
                key={cand.person_id}
                className="p-4 rounded-xl bg-card border border-border space-y-3 flex flex-col justify-between shadow-xs"
              >
                <div>
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <h5 className="font-semibold text-foreground text-sm">
                        {cand.full_name}
                      </h5>
                      <p className="text-xs text-muted-foreground">
                        {cand.role || 'Member'} • {cand.group || 'Team'}
                      </p>
                    </div>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-accent/10 text-accent border border-accent/20 font-semibold">
                      {cand.skill_overlap_count} overlapping skills
                    </span>
                  </div>

                  {cand.shared_skills.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {cand.shared_skills.map((s, idx) => (
                        <span
                          key={idx}
                          className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-muted text-muted-foreground"
                        >
                          {s}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                <button
                  onClick={() => onSelectSuccessor(cand.person_id)}
                  className="w-full mt-2 py-1.5 px-3 rounded-lg bg-muted hover:bg-card text-foreground text-xs font-mono transition-colors border border-border hover:border-accent/40 font-medium"
                >
                  Select for Handover →
                </button>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-muted-foreground font-mono">
            No direct peer successor candidates with overlapping skills found in this group.
          </p>
        )}
      </div>

      {/* Projects Needing Lead or Contributor */}
      {replaceProjects.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-amber-600 dark:text-amber-400">
            Projects Requiring Successor Lead ({replaceProjects.length})
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {replaceProjects.map((p: any, idx: number) => (
              <div
                key={idx}
                className="p-3 rounded-lg bg-card/60 border border-border text-xs flex items-center justify-between"
              >
                <span className="font-medium text-foreground">{p.name}</span>
                <span className="text-[10px] font-mono text-muted-foreground">{p.relationship}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Sole Author Knowledge Risk */}
      {soleAuthorDocs.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-rose-600 dark:text-rose-400">
            Sole-Author Knowledge Loss Risks ({soleAuthorDocs.length})
          </h4>
          <div className="space-y-1.5">
            {soleAuthorDocs.map((doc: any, idx: number) => (
              <div
                key={idx}
                className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-xs flex items-center justify-between"
              >
                <span className="font-medium text-foreground">{doc.title}</span>
                <span className="text-[10px] font-mono text-rose-600 dark:text-rose-400 font-semibold">Sole Author</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tasks Needing Reassignment */}
      {reassignTasks.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-muted-foreground">
            Tasks Scheduled for Reassignment ({reassignTasks.length})
          </h4>
          <div className="space-y-1.5">
            {reassignTasks.map((t: any, idx: number) => (
              <div
                key={idx}
                className="p-2.5 rounded-lg bg-card/60 border border-border text-xs flex items-center justify-between"
              >
                <span className="text-foreground">{t.title}</span>
                <span className="text-[10px] font-mono text-muted-foreground">Due: {t.due_date || 'N/A'}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

