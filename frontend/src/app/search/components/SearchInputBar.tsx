'use client';

import React, { useState } from 'react';

interface SearchInputBarProps {
  onSearch: (query: string) => void;
  isLoading: boolean;
}

export function SearchInputBar({ onSearch, isLoading }: SearchInputBarProps) {
  const [query, setQuery] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || isLoading) return;
    onSearch(query.trim());
  };

  return (
    <div className="p-4 border-t border-border bg-card/60 backdrop-blur-md font-mono">
      {/* Input Form */}
      <form onSubmit={handleSubmit} className="flex items-center gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask a question across the Universal Knowledge Graph (e.g. causes, decisions, people, risks)..."
          className="flex-1 bg-background border border-border rounded-xl px-4 py-2.5 text-xs text-foreground placeholder-muted-foreground focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent"
        />
        <button
          type="submit"
          disabled={isLoading || !query.trim()}
          className="px-5 py-2.5 rounded-xl bg-accent hover:opacity-90 disabled:opacity-50 text-accent-foreground font-semibold text-xs transition-colors shrink-0 shadow-sm"
        >
          {isLoading ? 'Reasoning...' : 'Ask Knowledge Graph'}
        </button>
      </form>
    </div>
  );
}
