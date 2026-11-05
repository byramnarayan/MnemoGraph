'use client';

import React from 'react';
import { SectionEKnowledgeAuthored } from '../types';

interface KtpKnowledgeSectionProps {
  knowledge: SectionEKnowledgeAuthored | null;
}

export function KtpKnowledgeSection({ knowledge }: KtpKnowledgeSectionProps) {
  const docs = knowledge?.authored_documents || [];
  const lessons = knowledge?.lessons_learned || [];

  if (docs.length === 0 && lessons.length === 0) {
    return (
      <div className="p-6 text-center text-xs text-muted-foreground font-mono bg-card/30 rounded-xl border border-border">
        No authored documents or lessons learned recorded.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Authored Documents */}
      {docs.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-muted-foreground">
            Authored Documents ({docs.length})
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {docs.map((doc) => (
              <div
                key={doc.document_id}
                className="p-4 rounded-xl bg-card border border-border text-xs space-y-2 shadow-xs"
              >
                <div className="flex items-start justify-between gap-2">
                  <h5 className="font-semibold text-foreground">{doc.title}</h5>
                  <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-muted text-foreground border border-border shrink-0">
                    {doc.document_type || 'Document'}
                  </span>
                </div>

                <div className="flex items-center gap-3 text-[11px] font-mono text-muted-foreground">
                  <span>Status: {doc.status || 'Active'}</span>
                  <span>Date: {doc.creation_date || 'N/A'}</span>
                </div>

                {doc.successor_document_id && (
                  <div className="p-2 rounded bg-amber-500/10 border border-amber-500/20 text-[11px] font-mono text-amber-700 dark:text-amber-300">
                    Superseded by: {doc.successor_document_id}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Lessons Learned */}
      {lessons.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-muted-foreground">
            Institutional Lessons Learned ({lessons.length})
          </h4>
          <div className="space-y-2">
            {lessons.map((les) => (
              <div
                key={les.lesson_id}
                className="p-3 rounded-lg bg-card/60 border border-border text-xs space-y-1"
              >
                <div className="font-medium text-foreground">{les.title}</div>
                {les.summary && (
                  <p className="text-[11px] text-muted-foreground leading-relaxed">
                    {les.summary}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

