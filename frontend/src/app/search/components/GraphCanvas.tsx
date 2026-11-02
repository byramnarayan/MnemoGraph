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
}

interface GraphCanvasProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  height?: number;
  onNodeClick?: (node: GraphNode) => void;
}

export function GraphCanvas({
  nodes,
  edges,
  height = 360,
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
    for (let step = 0; step < 40; step++) {
      // Repulsion between nodes
      for (let i = 0; i < simulationNodes.length; i++) {
        for (let j = i + 1; j < simulationNodes.length; j++) {
          const a = simulationNodes[i];
          const b = simulationNodes[j];
          const dx = b.x - a.x;
          const dy = b.y - a.y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          if (dist < 180) {
            const force = (180 - dist) / dist * 0.5;
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
          const desiredDist = 120;
          const force = (dist - desiredDist) / dist * 0.1;
          src.x += dx * force;
          src.y += dy * force;
          tgt.x -= dx * force;
          tgt.y -= dy * force;
        }
      });

      // Keep within canvas bounds
      simulationNodes.forEach((n) => {
        n.x = Math.max(40, Math.min(width - 40, n.x));
        n.y = Math.max(40, Math.min(canvasHeight - 40, n.y));
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
        ctx.strokeStyle = '#475569';
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // Edge label
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

      // Color by label
      if (n.label === 'Person') ctx.fillStyle = '#3b82f6';
      else if (n.label === 'Team') ctx.fillStyle = '#10b981';
      else if (n.label === 'Project') ctx.fillStyle = '#f59e0b';
      else if (n.label === 'Decision') ctx.fillStyle = '#8b5cf6';
      else ctx.fillStyle = '#64748b';

      ctx.fill();
      ctx.strokeStyle = '#1e293b';
      ctx.lineWidth = 2;
      ctx.stroke();

      // Node label text
      ctx.fillStyle = '#f8fafc';
      ctx.font = '10px monospace';
      const labelText = n.properties?.name || n.properties?.title || n.id.split(':').pop() || n.label;
      ctx.fillText(labelText.slice(0, 14), n.x - 24, n.y + 28);
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
        if (Math.sqrt(dx * dx + dy * dy) <= 18) {
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
      <div className="absolute top-2 left-3 z-10 flex items-center gap-2">
        <Tag tone="accent">GRAPH TOPOLOGY</Tag>
        <span className="text-[10px] text-muted-foreground uppercase">
          {nodes.length} Nodes &bull; {edges.length} Edges
        </span>
      </div>

      {selectedNode && (
        <div className="absolute top-2 right-3 z-10 p-2 rounded-xs border border-accent/40 bg-card/90 shadow-lg text-[10px] space-y-1 max-w-xs">
          <div className="flex items-center justify-between">
            <span className="text-accent font-semibold">{selectedNode.label}</span>
            <button onClick={() => setSelectedNode(null)} className="text-muted-foreground hover:text-foreground">✕</button>
          </div>
          <div className="text-foreground truncate">{selectedNode.id}</div>
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

