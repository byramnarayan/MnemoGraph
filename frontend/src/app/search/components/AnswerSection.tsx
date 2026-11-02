'use client';

import React from 'react';
import { Tag, Button } from '@/kit';

export interface AnswerData {
  answer_text: string;
  confidence: number;
  sources: Array<{
    document_id: string;
    source_url: string;
    excerpt: string;
    score: number;
    related_people?: string[];
    related_teams?: string[];
    related_projects?: string[];
  }>;
  provenance: Array<{
    title: string;
    path: string[];
    people: string[];
    teams: string[];
    projects: string[];
  }>;
  generated_cypher?: string;
}

interface AnswerSectionProps {
  data: AnswerData | null;
  loading: boolean;
  onOpenSource: (src: AnswerData['sources'][0]) => void;
  onOpenCitation: (cite: AnswerData['provenance'][0]) => void;
  onOpenGraph: () => void;
  onRunCypher: (cypher: string) => void;
}

export function AnswerSection({
  data,
  loading,
  onOpenSource,
  onOpenCitation,
  onOpenGraph,
  onRunCypher,
}: AnswerSectionProps) {
  if (loading) {
    return (
      <div className="p-8 rounded-sm border border-border/60 bg-card/40 animate-pulse space-y-4 font-mono">
        <div className="h-4 w-40 bg-muted rounded-xs" />
        <div className="space-y-2">
          <div className="h-3 w-full bg-muted/60 rounded-xs" />
          <div className="h-3 w-5/6 bg-muted/60 rounded-xs" />
          <div className="h-3 w-4/6 bg-muted/60 rounded-xs" />
        </div>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="p-6 rounded-sm border border-border bg-card shadow-sm space-y-5 font-mono">
      {/* Top Banner: Answer Tag + Clickable Sources & Provenance Buttons */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/70 pb-4">
        <div className="flex items-center gap-2">
          <Tag tone="accent">SYNTHESIZED ANSWER</Tag>
          <span className="text-xs text-muted-foreground">
            Confidence: {(data.confidence * 100).toFixed(0)}%
          </span>
        </div>

        {/* Clickable Sources & Citations Badges (Opens Right-Side Drawer) */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => data.sources[0] && onOpenSource(data.sources[0])}
            className="px-2.5 py-1 rounded-xs border border-border hover:border-accent bg-muted/20 hover:bg-accent/10 text-xs text-foreground flex items-center gap-1.5 transition-all"
            title="Inspect grounded evidence sources"
          >
            <span className="text-muted-foreground">Sources</span>
            <Tag tone="neutral">{data.sources.length}</Tag>
          </button>

          <button
            onClick={() => data.provenance[0] && onOpenCitation(data.provenance[0])}
            className="px-2.5 py-1 rounded-xs border border-border hover:border-accent bg-muted/20 hover:bg-accent/10 text-xs text-foreground flex items-center gap-1.5 transition-all"
            title="Inspect multi-hop provenance and ratifiers"
          >
            <span className="text-muted-foreground">Provenance & Citations</span>
            <Tag tone="accent">{data.provenance.length}</Tag>
          </button>
        </div>
      </div>

      {/* Answer Body */}
      <div className="text-sm font-sans leading-relaxed text-foreground whitespace-pre-line">
        {data.answer_text}
      </div>

      {/* Sources Strip */}
      {data.sources.length > 0 && (
        <div className="space-y-2 pt-2 border-t border-border/40 text-xs">
          <span className="text-[10px] text-muted-foreground uppercase font-semibold block">
            Grounded Citations (Click to view full excerpt)
          </span>
          <div className="flex flex-wrap gap-2">
            {data.sources.map((src, i) => (
              <button
                key={i}
                onClick={() => onOpenSource(src)}
                className="p-2 rounded-xs border border-border/60 bg-muted/15 hover:border-accent text-left max-w-xs transition-colors"
              >
                <div className="text-foreground font-semibold truncate text-[11px]">
                  {src.document_id}
                </div>
                <div className="text-[10px] text-muted-foreground truncate mt-0.5">
                  Relevance: {(src.score * 100).toFixed(0)}%
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Query & Run Button Footer */}
      {data.generated_cypher && (
        <div className="p-3.5 rounded-xs border border-border/70 bg-muted/20 space-y-2 text-xs">
          <div className="flex items-center justify-between">
            <span className="text-[10px] text-muted-foreground uppercase font-semibold">
              Traversed Graph Cypher Query
            </span>
            <div className="flex items-center gap-2">
              <Button
                onClick={onOpenGraph}
                variant="ghost"
                className="text-xs h-7 px-2.5"
              >
                Show Graph Canvas
              </Button>
              <Button
                onClick={() => onRunCypher(data.generated_cypher!)}
                className="text-xs h-7 px-3 bg-accent text-accent-foreground"
              >
                ▶ Run Query
              </Button>
            </div>
          </div>
          <code className="text-[11px] text-accent block overflow-x-auto p-2 rounded-xs bg-background/80 border border-border/40">
            {data.generated_cypher}
          </code>
        </div>
      )}
    </div>
  );
}

