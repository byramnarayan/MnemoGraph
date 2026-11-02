'use client';

import React from 'react';
import { GraphCanvas, GraphNode, GraphEdge } from './GraphCanvas';
import { Tag } from '@/kit';

interface GraphCanvasModalProps {
  isOpen: boolean;
  onClose: () => void;
  nodes: GraphNode[];
  edges: GraphEdge[];
  queryTitle?: string;
}

export function GraphCanvasModal({
  isOpen,
  onClose,
  nodes,
  edges,
  queryTitle,
}: GraphCanvasModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/85 backdrop-blur-md animate-fade-in font-mono">
      <div className="bg-card border border-border rounded-sm shadow-2xl max-w-5xl w-full flex flex-col max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="h-14 border-b border-border px-5 flex items-center justify-between bg-muted/20">
          <div className="flex items-center gap-2">
            <Tag tone="accent">INTERACTIVE GRAPH POPUP</Tag>
            <span className="text-xs font-semibold text-foreground truncate max-w-lg">
              {queryTitle || 'Knowledge Graph Subgraph'}
            </span>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-xs hover:bg-muted text-muted-foreground hover:text-foreground text-sm"
          >
            ✕
          </button>
        </div>

        {/* Canvas Body */}
        <div className="p-4 flex-1 overflow-hidden bg-background/50">
          <GraphCanvas nodes={nodes} edges={edges} height={520} />
        </div>

        {/* Footer */}
        <div className="p-3 border-t border-border bg-muted/10 flex items-center justify-between text-xs text-muted-foreground">
          <span>Click any node to inspect metadata. Multi-hop relationships resolved from FalkorDB.</span>
          <button
            onClick={onClose}
            className="px-3 py-1 bg-muted hover:bg-muted/80 rounded-xs text-foreground uppercase tracking-wider text-[11px]"
          >
            Close Canvas
          </button>
        </div>
      </div>
    </div>
  );
}

