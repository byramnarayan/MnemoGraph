'use client';

import React from 'react';
import { UKGOEAnswerData } from '../types';

interface SearchAnswerCardProps {
  data: UKGOEAnswerData | null;
  loading: boolean;
  onOpenEvidence: () => void;
  onOpenGraph: () => void;
}

export function SearchAnswerCard({
  data,
  loading,
  onOpenEvidence,
  onOpenGraph,
}: SearchAnswerCardProps) {
  if (loading) {
    return (
      <div className="p-6 rounded-xl border border-border bg-card/60 animate-pulse space-y-3 font-mono text-xs">
        <div className="flex items-center gap-2">
          <div className="h-5 w-24 bg-muted rounded-md" />
          <div className="h-5 w-32 bg-muted rounded-md" />
        </div>
        <div className="space-y-2">
          <div className="h-3 w-full bg-muted/60 rounded" />
          <div className="h-3 w-5/6 bg-muted/60 rounded" />
          <div className="h-3 w-4/6 bg-muted/60 rounded" />
        </div>
      </div>
    );
  }

  if (!data) return null;

  const getIntentTone = (intent: string) => {
    switch (intent.toUpperCase()) {
      case 'CAUSAL':
        return 'bg-purple-500/15 border-purple-500/30 text-purple-600 dark:text-purple-300';
      case 'PREDICTIVE':
        return 'bg-amber-500/15 border-amber-500/30 text-amber-600 dark:text-amber-300';
      case 'RELATIONAL':
        return 'bg-blue-500/15 border-blue-500/30 text-blue-600 dark:text-blue-300';
      case 'AGGREGATIVE':
        return 'bg-emerald-500/15 border-emerald-500/30 text-emerald-600 dark:text-emerald-300';
      case 'COMPARATIVE':
        return 'bg-cyan-500/15 border-cyan-500/30 text-cyan-600 dark:text-cyan-300';
      default:
        return 'bg-accent/15 border-accent/30 text-accent';
    }
  };

  const confidencePct = Math.round((data.confidence || 0.85) * 100);

  return (
    <div className="p-5 rounded-2xl border border-border bg-card shadow-xs space-y-4 font-mono">
      {/* Top Meta Bar */}
      <div className="flex flex-wrap items-center justify-end gap-3 border-b border-border pb-3">
        <div className="flex items-center gap-2">
          <button
            onClick={onOpenEvidence}
            className="px-2.5 py-1 rounded-md border border-border hover:border-accent bg-background hover:bg-card text-xs text-foreground flex items-center gap-1.5 transition-colors"
          >
            <span className="text-muted-foreground text-[11px]">Evidence</span>
            <span className="px-1.5 py-0.2 rounded bg-muted text-[10px]">{data.sources?.length || 0}</span>
          </button>

          <button
            onClick={onOpenGraph}
            className="px-2.5 py-1 rounded-md border border-border hover:border-accent bg-background hover:bg-card text-xs text-foreground transition-colors"
            title="Inspect graph query in topology visualizer"
          >
            Graph Provenance
          </button>
        </div>
      </div>

      {/* Answer Body */}
      <div className="text-sm font-sans leading-relaxed text-foreground whitespace-pre-line">
        {data.answer_text}
      </div>

      {/* Inference Insights (IR-01 through IR-10) */}
      {data.inference_insights && data.inference_insights.length > 0 && (
        <div className="pt-2 border-t border-border space-y-1.5">
          <h5 className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
            Inference Insights Applied ({data.inference_insights.length})
          </h5>
          <div className="flex flex-wrap gap-1.5">
            {data.inference_insights.map((ins, idx) => (
              <div
                key={idx}
                className="px-2.5 py-1 rounded-md border border-accent/30 bg-accent/10 text-accent text-[11px] flex items-center gap-1.5"
                title={ins.finding}
              >
                <span className="font-bold">{ins.rule_id}</span>
                <span className="text-foreground/80">{ins.finding}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* IR-09 Cascade Warnings */}
      {data.cascade_warnings && data.cascade_warnings.length > 0 && (
        <div className="p-3 rounded-lg bg-amber-500/15 border border-amber-500/30 text-amber-700 dark:text-amber-200 text-xs space-y-1">
          <div className="font-bold font-mono">[IR-09 CASCADE WARNING]</div>
          {data.cascade_warnings.map((cw, idx) => (
            <div key={idx} className="text-[11px]">
              Downstream recompute needed for {cw.entity_id}: {cw.reason} (triggered by {cw.triggered_by})
            </div>
          ))}
        </div>
      )}

      {/* Missing Data Gaps */}
      {data.missing_data_gaps && data.missing_data_gaps.length > 0 && (
        <div className="p-2.5 rounded-lg bg-muted/60 border border-border text-[11px] text-muted-foreground flex items-center justify-between">
          <span>{data.missing_data_gaps.length} missing data gap(s) identified in traversal path.</span>
          <span className="font-mono text-[10px] uppercase text-amber-600 dark:text-amber-400">Quality Grade D</span>
        </div>
      )}
    </div>
  );
}

