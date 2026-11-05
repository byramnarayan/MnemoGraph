'use client';

import React from 'react';

interface SearchGraphControlsProps {
  onZoomIn: () => void;
  onZoomOut: () => void;
  onReset: () => void;
  onFit: () => void;
  nodeCount: number;
  edgeCount: number;
  isExecuting?: boolean;
}

export function SearchGraphControls({
  onZoomIn,
  onZoomOut,
  onReset,
  onFit,
  nodeCount,
  edgeCount,
  isExecuting,
}: SearchGraphControlsProps) {
  return (
    <div className="absolute top-4 right-6 z-20 flex items-center gap-2 select-none font-mono">
      {/* Node / Edge stats badge */}
      <div className="px-2.5 py-1.5 rounded-xl border border-border bg-card/85 backdrop-blur-md shadow-xs text-[11px] text-muted-foreground flex items-center gap-1.5">
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
        <span className="font-semibold text-foreground">{nodeCount}</span> Nodes
        <span className="text-border">|</span>
        <span className="font-semibold text-foreground">{edgeCount}</span> Edges
        {isExecuting && (
          <span className="text-[10px] text-accent animate-pulse ml-1">
            • Querying...
          </span>
        )}
      </div>

      {/* Floating Tool Buttons (matching the uploaded image toolbar) */}
      <div className="flex items-center rounded-xl border border-border bg-card/85 backdrop-blur-md shadow-xs p-1 gap-0.5">
        <button
          type="button"
          onClick={onZoomIn}
          title="Zoom In"
          aria-label="Zoom In"
          className="w-7 h-7 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground flex items-center justify-center text-sm font-semibold transition-colors"
        >
          🔍+
        </button>
        <button
          type="button"
          onClick={onZoomOut}
          title="Zoom Out"
          aria-label="Zoom Out"
          className="w-7 h-7 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground flex items-center justify-center text-sm font-semibold transition-colors"
        >
          🔍-
        </button>
        <button
          type="button"
          onClick={onFit}
          title="Center / Fit Subgraph"
          aria-label="Fit Graph"
          className="w-7 h-7 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground flex items-center justify-center text-xs transition-colors"
        >
          ⤢
        </button>
        <button
          type="button"
          onClick={onReset}
          title="Reset to Initial Graph"
          aria-label="Reset Subgraph"
          className="w-7 h-7 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground flex items-center justify-center text-xs transition-colors"
        >
          ↺
        </button>
      </div>
    </div>
  );
}

