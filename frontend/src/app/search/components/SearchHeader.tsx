'use client';

import React from 'react';
import Link from 'next/link';

interface SearchHeaderProps {
  activeTitle: string;
  clearanceLevel?: string;
  onResetGraph: () => void;
  isResetting: boolean;
}

export function SearchHeader({
  activeTitle,
  clearanceLevel = 'Internal',
  onResetGraph,
  isResetting,
}: SearchHeaderProps) {
  const getClearanceTone = (level: string) => {
    switch (level.toLowerCase()) {
      case 'restricted':
        return 'bg-purple-500/15 border-purple-500/30 text-purple-600 dark:text-purple-300';
      case 'confidential':
        return 'bg-amber-500/15 border-amber-500/30 text-amber-600 dark:text-amber-300';
      default:
        return 'bg-blue-500/15 border-blue-500/30 text-blue-600 dark:text-blue-300';
    }
  };

  return (
    <header className="h-14 border-b border-border/80 px-6 flex items-center justify-between shrink-0 bg-card/40 backdrop-blur-sm font-mono text-xs">
      <div className="flex items-center gap-3 min-w-0">
        <div className="flex items-center gap-1.5 text-muted-foreground uppercase tracking-wider shrink-0">
          <Link href="/" className="hover:text-foreground transition-colors">Home</Link>
          <span>/</span>
          <span className="text-foreground font-semibold">Knowledge & Memory Workspace</span>
        </div>
        <span className="text-border hidden sm:inline">|</span>
        <span className="text-muted-foreground truncate hidden md:inline text-[11px]" title={activeTitle}>
          {activeTitle}
        </span>
      </div>

      <div className="flex items-center gap-3 shrink-0">
        <button
          onClick={onResetGraph}
          disabled={isResetting}
          className="px-2.5 py-1 rounded border border-border bg-background hover:bg-card text-[11px] text-muted-foreground hover:text-foreground transition-colors"
          title="Reset graph canvas to institutional root"
        >
          {isResetting ? 'Resetting...' : 'Reset Graph'}
        </button>

        <Link
          href="/hub"
          className="px-2.5 py-1 rounded border border-accent/40 bg-accent/10 hover:bg-accent/20 text-accent text-[11px] font-semibold transition-colors flex items-center gap-1"
        >
          <span>KTP Hub</span>
          <span>→</span>
        </Link>

        <div className={`px-2 py-0.5 rounded border font-mono text-[10px] font-bold uppercase tracking-wider ${getClearanceTone(clearanceLevel)}`}>
          {clearanceLevel} Clearance
        </div>
      </div>
    </header>
  );
}

