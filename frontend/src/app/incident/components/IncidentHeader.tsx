'use client';

import React from 'react';

interface IncidentHeaderProps {
  activeScope: string;
  onScopeChange: (scope: string) => void;
  onRefresh: () => void;
  isLoading: boolean;
}

export function IncidentHeader({
  activeScope,
  onScopeChange,
  onRefresh,
  isLoading,
}: IncidentHeaderProps) {
  const [scopeInput, setScopeInput] = React.useState(activeScope);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!scopeInput.trim() || isLoading) return;
    onScopeChange(scopeInput.trim());
  };

  return (
    <header className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-5 border-b border-border">
      <div>
        <div className="flex items-center gap-2 mb-1">
          <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse" />
          <span className="font-mono text-[10px] uppercase font-bold tracking-wider text-rose-400">
            Predictive Incident & Decision Intelligence
          </span>
        </div>
        <h1 className="text-xl font-bold tracking-tight text-foreground">
          Incident Risk & Horizon Forecast
        </h1>
      </div>

      <form onSubmit={handleSubmit} className="flex items-center gap-2 self-stretch sm:self-auto">
        <input
          type="text"
          value={scopeInput}
          onChange={(e) => setScopeInput(e.target.value)}
          placeholder="System / Site / Entity..."
          className="bg-card border border-border rounded-lg px-3 py-1.5 font-mono text-xs text-foreground focus:outline-none focus:border-accent w-56 sm:w-64"
        />
        <button
          type="submit"
          disabled={isLoading || !scopeInput.trim()}
          className="px-3.5 py-1.5 rounded-lg bg-accent text-accent-foreground font-mono text-xs font-semibold hover:opacity-90 disabled:opacity-50"
        >
          {isLoading ? 'Forecasting...' : 'Analyze Scope'}
        </button>
      </form>
    </header>
  );
}
