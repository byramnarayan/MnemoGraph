'use client';

import React, { useEffect, useRef, useState } from 'react';
import { Tag } from '@/kit';

export interface GraphNode {
  id: string;
  label: string;
  properties?: Record<string, any>;
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  relation: string;
  properties?: Record<string, any>;
}

interface GraphCanvasProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  height?: number;
  onNodeClick?: (node: GraphNode) => void;
}

const NODE_COLORS: Record<string, string> = {
  Notebook: '#38bdf8',
  File: '#64748b',
  Document: '#0ea5e9',
  Project: '#f59e0b',
  Decision: '#8b5cf6',
  Person: '#10b981',
  Employee: '#10b981',
  Team: '#06b6d4',
  Workspace: '#a855f7',
  EpisodeMemory: '#ec4899',
  Task: '#f97316',
  Ticket: '#ef4444',
};

export function GraphCanvas({
  nodes,
  edges,
  height = 420,
  onNodeClick,
}: GraphCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const canvasHeight = canvas.height;

    // Initialize random positions if not provided
    const simulationNodes = nodes.map((n, i) => {
      const angle = (i / Math.max(nodes.length, 1)) * 2 * Math.PI;
      const radius = Math.min(width, canvasHeight) * 0.35;
      return {
        ...n,
        x: n.x ?? width / 2 + Math.cos(angle) * radius + (Math.random() - 0.5) * 40,
        y: n.y ?? canvasHeight / 2 + Math.sin(angle) * radius + (Math.random() - 0.5) * 40,
      };
    });

    const nodeMap = new Map<string, typeof simulationNodes[0]>();
    simulationNodes.forEach((n) => nodeMap.set(n.id, n));

    // Simple 2D spring force layout steps
    for (let step = 0; step < 45; step++) {
      // Repulsion between nodes
      for (let i = 0; i < simulationNodes.length; i++) {
        for (let j = i + 1; j < simulationNodes.length; j++) {
          const a = simulationNodes[i];
          const b = simulationNodes[j];
          const dx = b.x - a.x;
          const dy = b.y - a.y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          if (dist < 160) {
            const force = ((160 - dist) / dist) * 0.45;
            a.x -= dx * force * 0.1;
            a.y -= dy * force * 0.1;
            b.x += dx * force * 0.1;
            b.y += dy * force * 0.1;
          }
        }
      }

      // Edge spring attraction
      edges.forEach((edge) => {
        const src = nodeMap.get(edge.source);
        const tgt = nodeMap.get(edge.target);
        if (src && tgt) {
          const dx = tgt.x - src.x;
          const dy = tgt.y - src.y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const desiredDist = 110;
          const force = ((dist - desiredDist) / dist) * 0.08;
          src.x += dx * force;
          src.y += dy * force;
          tgt.x -= dx * force;
          tgt.y -= dy * force;
        }
      });

      // Keep within canvas bounds
      simulationNodes.forEach((n) => {
        n.x = Math.max(45, Math.min(width - 45, n.x));
        n.y = Math.max(45, Math.min(canvasHeight - 45, n.y));
      });
    }

    // Render Frame
    ctx.clearRect(0, 0, width, canvasHeight);

    // Draw Edges
    edges.forEach((edge) => {
      const src = nodeMap.get(edge.source);
      const tgt = nodeMap.get(edge.target);
      if (src && tgt) {
        ctx.beginPath();
        ctx.moveTo(src.x, src.y);
        ctx.lineTo(tgt.x, tgt.y);

        const relUpper = (edge.relation || '').toUpperCase();
        if (relUpper.includes('CAUSED_RECURRENCE') || relUpper.includes('BLOCKED_BY')) {
          ctx.strokeStyle = '#ef4444';
          ctx.lineWidth = 2.4;
          ctx.setLineDash([5, 3]);
        } else if (relUpper.includes('PREVENTED_RECURRENCE')) {
          ctx.strokeStyle = '#10b981';
          ctx.lineWidth = 2.0;
          ctx.setLineDash([]);
        } else if (relUpper.includes('RAISED_FROM')) {
          ctx.strokeStyle = '#f97316';
          ctx.lineWidth = 1.8;
          ctx.setLineDash([]);
        } else {
          ctx.strokeStyle = '#475569';
          ctx.lineWidth = 1.3;
          ctx.setLineDash([]);
        }

        ctx.stroke();
        ctx.setLineDash([]); // reset

        // Draw Edge Label
        const midX = (src.x + tgt.x) / 2;
        const midY = (src.y + tgt.y) / 2;
        ctx.fillStyle = '#94a3b8';
        ctx.font = '9px monospace';
        ctx.fillText(edge.relation, midX + 3, midY - 3);
      }
    });

    // Draw Nodes
    simulationNodes.forEach((n) => {
      ctx.beginPath();
      ctx.arc(n.x, n.y, 16, 0, 2 * Math.PI);

      const fillColor = NODE_COLORS[n.label] || '#64748b';
      ctx.fillStyle = fillColor;
      ctx.fill();

      ctx.strokeStyle = '#0f172a';
      ctx.lineWidth = 2;
      ctx.stroke();

      // Node label text
      ctx.fillStyle = '#f8fafc';
      ctx.font = '10px monospace';
      const labelText =
        n.properties?.name ||
        n.properties?.title ||
        n.properties?.city ||
        n.id.split(':').pop() ||
        n.label;
      ctx.fillText(String(labelText).slice(0, 16), n.x - 28, n.y + 26);
    });

    // Canvas click detection
    const handleCanvasClick = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      const clickX = e.clientX - rect.left;
      const clickY = e.clientY - rect.top;

      let hit: GraphNode | null = null;
      for (const n of simulationNodes) {
        const dx = clickX - n.x;
        const dy = clickY - n.y;
        if (Math.sqrt(dx * dx + dy * dy) <= 20) {
          hit = n;
          break;
        }
      }
      setSelectedNode(hit);
      if (hit && onNodeClick) {
        onNodeClick(hit);
      }
    };

    canvas.addEventListener('click', handleCanvasClick);
    return () => {
      canvas.removeEventListener('click', handleCanvasClick);
    };
  }, [nodes, edges, onNodeClick]);

  return (
    <div className="relative w-full rounded-sm border border-border/70 bg-card/40 overflow-hidden font-mono">
      {/* Top Bar with Counts and Legend */}
      <div className="p-2 px-3 border-b border-border/50 bg-background/50 flex flex-wrap items-center justify-between gap-2 text-xs">
        <div className="flex items-center gap-2">
          <Tag tone="accent">ENTERPRISE GRAPH TOPOLOGY</Tag>
          <span className="text-[11px] text-muted-foreground uppercase">
            {nodes.length} Nodes &bull; {edges.length} Edges
          </span>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-[10px]">
          <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-sky-400 inline-block" /> Notebook</span>
          <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-slate-500 inline-block" /> File</span>
          <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-amber-500 inline-block" /> Project</span>
          <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-purple-500 inline-block" /> Decision</span>
          <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block" /> Person</span>
          <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-cyan-500 inline-block" /> Team</span>
        </div>
      </div>

      {selectedNode && (
        <div className="absolute top-12 right-3 z-10 p-3 rounded border border-accent/50 bg-card/95 shadow-xl text-xs space-y-2 max-w-sm">
          <div className="flex items-center justify-between border-b border-border/60 pb-1.5">
            <span
              className="font-bold text-[11px] px-1.5 py-0.5 rounded text-white"
              style={{ backgroundColor: NODE_COLORS[selectedNode.label] || '#64748b' }}
            >
              {selectedNode.label}
            </span>
            <button
              onClick={() => setSelectedNode(null)}
              className="text-muted-foreground hover:text-foreground text-sm font-bold ml-2"
            >
              ✕
            </button>
          </div>
          <div className="text-[11px] font-bold text-foreground truncate">{selectedNode.id}</div>
          {selectedNode.properties && Object.keys(selectedNode.properties).length > 0 && (
            <div className="text-[10px] space-y-1 max-h-48 overflow-y-auto pr-1">
              {Object.entries(selectedNode.properties).map(([k, v]) => (
                <div key={k} className="flex justify-between gap-2 border-b border-border/30 py-0.5">
                  <span className="text-muted-foreground capitalize">{k.replace(/_/g, ' ')}:</span>
                  <span className="text-foreground text-right font-medium truncate max-w-[160px]">
                    {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <canvas
        ref={canvasRef}
        width={960}
        height={height}
        className="w-full h-auto cursor-crosshair block"
      />
    </div>
  );
}
