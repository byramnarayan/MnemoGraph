'use client';

import React from 'react';
import { SourceEvidenceItem } from '../types';

interface SearchEvidenceDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  sources: SourceEvidenceItem[];
  graphQuery?: string | null;
  onRunCypher: (cypher: string) => void;
}

export function SearchEvidenceDrawer({
  isOpen,
  onClose,
  sources,
  graphQuery,
  onRunCypher,
}: SearchEvidenceDrawerProps) {
  if (!isOpen) return null;

  const getGradeTone = (grade?: string) => {
    switch (grade) {
      case 'A':
        return 'bg-emerald-500/15 border-emerald-500/30 text-emerald-600 dark:text-emerald-400';
      case 'B':
        return 'bg-blue-500/15 border-blue-500/30 text-blue-600 dark:text-blue-400';
      case 'C':
        return 'bg-amber-500/15 border-amber-500/30 text-amber-600 dark:text-amber-400';
      default:
        return 'bg-rose-500/15 border-rose-500/30 text-rose-600 dark:text-rose-400';
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-background/60 backdrop-blur-xs font-mono text-xs">
      <div className="w-full max-w-lg h-full bg-card border-l border-border flex flex-col shadow-2xl animate-in slide-in-from-right duration-200">
        {/* Header */}
        <div className="p-4 border-b border-border flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h3 className="font-bold text-sm text-foreground uppercase tracking-wider">
              Grounded Evidence & Provenance
            </h3>
            <span className="text-muted-foreground">({sources.length})</span>
          </div>
          <button
            onClick={onClose}
            className="w-7 h-7 rounded-md border border-border hover:bg-muted flex items-center justify-center text-muted-foreground hover:text-foreground text-sm"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* Grounded Cypher Traversal Query */}
          {graphQuery && (
            <div className="p-3 rounded-xl border border-border bg-background space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold text-muted-foreground uppercase">
                  Executed Graph Traversal (openCypher)
                </span>
                <button
                  onClick={() => onRunCypher(graphQuery)}
                  className="px-2 py-0.5 rounded border border-accent/40 bg-accent/15 text-accent text-[10px] hover:bg-accent/25"
                >
                  Visualize Path
                </button>
              </div>
              <pre className="p-2.5 rounded bg-muted/40 text-[11px] text-foreground font-mono overflow-x-auto whitespace-pre-wrap">
                {graphQuery}
              </pre>
            </div>
          )}

          {/* Sources List */}
          <div className="space-y-3">
            <h4 className="text-[11px] font-bold text-muted-foreground uppercase tracking-wider">
              Cited Entities & Knowledge Chunks
            </h4>

            {sources.length === 0 ? (
              <p className="text-muted-foreground py-4 text-center">No source citations attached.</p>
            ) : (
              sources.map((src, idx) => (
                <div
                  key={`${src.entity_id}-${idx}`}
                  className="p-3.5 rounded-xl border border-border bg-background hover:border-accent/40 transition-colors space-y-2"
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-1.5 min-w-0">
                      <span className="px-1.5 py-0.2 rounded border border-border bg-muted text-[10px] uppercase font-bold text-muted-foreground shrink-0">
                        {src.entity_class}
                      </span>
                      <span className="font-semibold text-foreground truncate text-xs" title={src.entity_id}>
                        {src.label || src.entity_id}
                      </span>
                    </div>

                    <div className="flex items-center gap-1.5 shrink-0">
                      {src.data_quality_grade && (
                        <span className={`px-1.5 py-0.2 rounded border text-[10px] font-bold ${getGradeTone(src.data_quality_grade)}`}>
                          Grade {src.data_quality_grade}
                        </span>
                      )}
                      <span className="text-[10px] text-muted-foreground font-mono">
                        {(src.vector_score * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>

                  {/* Excerpt */}
                  <p className="text-xs font-sans text-muted-foreground leading-relaxed">
                    {src.excerpt}
                  </p>

                  {/* 1-Hop Graph Neighbors */}
                  {src.graph_neighbors && src.graph_neighbors.length > 0 && (
                    <div className="pt-2 border-t border-border/40 space-y-1">
                      <span className="text-[10px] text-muted-foreground uppercase tracking-wider block">
                        1-Hop Graph Neighbors ({src.graph_neighbors.length})
                      </span>
                      <div className="flex flex-wrap gap-1">
                        {src.graph_neighbors.map((nb, nIdx) => (
                          <span
                            key={nIdx}
                            className="px-1.5 py-0.5 rounded border border-border bg-muted/30 text-[10px] text-muted-foreground"
                          >
                            <span className="text-accent font-mono font-bold mr-1">:{nb.relation}</span>
                            {nb.label || nb.id}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

