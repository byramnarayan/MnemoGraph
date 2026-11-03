'use client';

import React, { useState } from 'react';
import { Button } from '@/kit';

interface QuestionInputProps {
  onAsk: (question: string) => void;
  loading: boolean;
}

export function QuestionInput({ onAsk, loading }: QuestionInputProps) {
  const [query, setQuery] = useState('');

  const suggestions = [
    'Which Databricks notebooks are associated with data pipelines?',
    'What architectural decisions were logged for project infrastructure?',
    'Who are the authors and teams responsible for core notebooks?',
    'Show relationships between projects and ingested document files',
  ];

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || loading) return;
    onAsk(query.trim());
  };

  return (
    <div className="w-full bg-card border-t border-border p-4 shadow-xl font-mono">
      {/* Suggestions Strip */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-2 text-[10px] text-muted-foreground">
        <span className="uppercase font-semibold shrink-0">Try:</span>
        {suggestions.map((s, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => {
              setQuery(s);
              onAsk(s);
            }}
            className="px-2.5 py-1 rounded-xs border border-border/60 bg-muted/20 hover:border-accent hover:text-foreground shrink-0 transition-colors"
          >
            {s}
          </button>
        ))}
      </div>

      {/* Input Form */}
      <form onSubmit={handleSubmit} className="flex items-center gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask any architectural, operational, or telecom question (FalkorDB + Qdrant + Database)..."
          className="flex-1 text-xs font-mono bg-background border border-border rounded-xs px-4 py-2.5 text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-accent shadow-inner"
          disabled={loading}
        />
        <Button
          type="submit"
          className="h-10 px-5 text-xs font-semibold uppercase tracking-wider shrink-0"
          disabled={loading || !query.trim()}
        >
          {loading ? 'Synthesizing...' : 'Ask Question'}
        </Button>
      </form>
    </div>
  );
}

