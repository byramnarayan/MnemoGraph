'use client';

import React, { useRef, useEffect, useState, useCallback } from 'react';
import { GraphNode, GraphEdge } from '../types';
import { UNIVERSAL_NODE_COLORS } from './SearchGraphLegend';

interface SearchGraphViewProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  onNodeClick?: (node: GraphNode) => void;
  zoomLevel: number;
  panOffset: { x: number; y: number };
  onPanChange: (offset: { x: number; y: number }) => void;
}

export function SearchGraphView({
  nodes,
  edges,
  onNodeClick,
  zoomLevel,
  panOffset,
  onPanChange,
}: SearchGraphViewProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [nodePositions, setNodePositions] = useState<Map<string, { x: number; y: number }>>(new Map());
  const draggingNodeRef = useRef<string | null>(null);
  const isPanningRef = useRef(false);
  const lastMousePosRef = useRef({ x: 0, y: 0 });

  // Initialize and distribute node positions radially
  useEffect(() => {
    const positions = new Map<string, { x: number; y: number }>();
    const total = nodes.length || 1;
    const cx = 400;
    const cy = 300;

    nodes.forEach((n, idx) => {
      const angle = (idx / total) * 2 * Math.PI;
      const radius = 180 + (idx % 3) * 60;
      positions.set(n.id, {
        x: cx + radius * Math.cos(angle) + (Math.sin(idx * 7) * 30),
        y: cy + radius * Math.sin(angle) + (Math.cos(idx * 5) * 30),
      });
    });
    setNodePositions(positions);
  }, [nodes]);

  const getNodeColor = useCallback((type?: string) => {
    const t = (type || '').toLowerCase();
    return UNIVERSAL_NODE_COLORS[t] || '#8b5cf6';
  }, []);

  // Main Canvas Render Loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const w = canvas.parentElement?.clientWidth || 800;
    const h = canvas.parentElement?.clientHeight || 600;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    ctx.scale(dpr, dpr);

    ctx.save();
    ctx.clearRect(0, 0, w, h);
    ctx.translate(panOffset.x, panOffset.y);
    ctx.scale(zoomLevel, zoomLevel);

    // 1. Draw Edges with Directed Arrows & Labels
    edges.forEach((e) => {
      const src = nodePositions.get(e.source);
      const tgt = nodePositions.get(e.target);
      if (!src || !tgt) return;

      const dx = tgt.x - src.x;
      const dy = tgt.y - src.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist === 0) return;

      // Draw Line
      ctx.strokeStyle = 'rgba(148, 163, 184, 0.45)';
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(src.x, src.y);
      ctx.lineTo(tgt.x, tgt.y);
      ctx.stroke();

      // Draw Directed Arrow
      const arrowLen = 9;
      const nodeRadius = 14;
      const stopX = tgt.x - (dx / dist) * nodeRadius;
      const stopY = tgt.y - (dy / dist) * nodeRadius;
      const angle = Math.atan2(dy, dx);

      ctx.fillStyle = 'rgba(148, 163, 184, 0.7)';
      ctx.beginPath();
      ctx.moveTo(stopX, stopY);
      ctx.lineTo(
        stopX - arrowLen * Math.cos(angle - Math.PI / 7),
        stopY - arrowLen * Math.sin(angle - Math.PI / 7)
      );
      ctx.lineTo(
        stopX - arrowLen * Math.cos(angle + Math.PI / 7),
        stopY - arrowLen * Math.sin(angle + Math.PI / 7)
      );
      ctx.closePath();
      ctx.fill();

      // Relation Label along edge
      const mx = (src.x + tgt.x) / 2;
      const my = (src.y + tgt.y) / 2;
      const relName = e.relation || e.type || '';
      if (relName) {
        ctx.font = '600 8.5px monospace';
        ctx.fillStyle = 'rgba(148, 163, 184, 0.85)';
        ctx.textAlign = 'center';
        ctx.fillText(relName.toUpperCase(), mx, my - 4);
      }
    });

    // 2. Draw Nodes (Matching image: colored core, ring, bold label below)
    nodes.forEach((n) => {
      const pos = nodePositions.get(n.id);
      if (!pos) return;

      const nodeType = n.type || n.label || n.properties?.label || 'node';
      const color = getNodeColor(nodeType);
      const isSelected = selectedNode?.id === n.id;

      // Outer Halo for selected
      if (isSelected) {
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, 20, 0, 2 * Math.PI);
        ctx.fillStyle = `${color}35`;
        ctx.fill();
      }

      // Outer border circle
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, 13, 0, 2 * Math.PI);
      ctx.fillStyle = '#ffffff';
      ctx.fill();

      // Solid colored core
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, 11, 0, 2 * Math.PI);
      ctx.fillStyle = color;
      ctx.fill();

      // Node Label Text (Rendered below node)
      const label = n.name || n.properties?.name || n.properties?.full_name || n.id;
      ctx.font = '600 11px sans-serif';
      ctx.fillStyle = isSelected ? color : 'var(--foreground, #17130e)';
      ctx.textAlign = 'center';
      ctx.fillText(label.length > 22 ? `${label.slice(0, 20)}...` : label, pos.x, pos.y + 24);
    });

    ctx.restore();
  }, [nodes, edges, nodePositions, zoomLevel, panOffset, selectedNode, getNodeColor]);

  // Pointer & Drag Handlers
  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    const mx = (e.clientX - rect.left - panOffset.x) / zoomLevel;
    const my = (e.clientY - rect.top - panOffset.y) / zoomLevel;

    // Check if clicked node
    for (const n of nodes) {
      const pos = nodePositions.get(n.id);
      if (pos && Math.hypot(pos.x - mx, pos.y - my) <= 18) {
        draggingNodeRef.current = n.id;
        setSelectedNode(n);
        onNodeClick?.(n);
        return;
      }
    }
    isPanningRef.current = true;
    lastMousePosRef.current = { x: e.clientX, y: e.clientY };
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (draggingNodeRef.current) {
      const rect = canvasRef.current?.getBoundingClientRect();
      if (!rect) return;
      const mx = (e.clientX - rect.left - panOffset.x) / zoomLevel;
      const my = (e.clientY - rect.top - panOffset.y) / zoomLevel;
      setNodePositions((prev) => new Map(prev).set(draggingNodeRef.current!, { x: mx, y: my }));
    } else if (isPanningRef.current) {
      const dx = e.clientX - lastMousePosRef.current.x;
      const dy = e.clientY - lastMousePosRef.current.y;
      lastMousePosRef.current = { x: e.clientX, y: e.clientY };
      onPanChange({ x: panOffset.x + dx, y: panOffset.y + dy });
    }
  };

  const handleMouseUp = () => {
    draggingNodeRef.current = null;
    isPanningRef.current = false;
  };

  return (
    <div className="relative w-full h-full overflow-hidden bg-background select-none cursor-grab active:cursor-grabbing">
      <canvas
        ref={canvasRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        className="w-full h-full block"
      />

      {/* Selected Node Details Floating Overlay */}
      {selectedNode && (
        <div className="absolute bottom-6 left-6 z-20 p-4 rounded-xl border border-border bg-card/90 backdrop-blur-md shadow-xl max-w-sm font-mono text-xs animate-in fade-in slide-in-from-bottom-2 duration-150">
          <div className="flex items-center justify-between gap-2 border-b border-border pb-2 mb-2">
            <span className="font-bold text-foreground truncate">
              {selectedNode.name || selectedNode.id}
            </span>
            <button
              onClick={() => setSelectedNode(null)}
              className="text-muted-foreground hover:text-foreground text-xs"
            >
              ✕
            </button>
          </div>
          <div className="space-y-1 text-[11px] text-muted-foreground">
            <p>ID: <span className="text-foreground">{selectedNode.id}</span></p>
            <p>Class: <span className="text-foreground">{selectedNode.label || selectedNode.type || 'Entity'}</span></p>
            {selectedNode.properties?.role && (
              <p>Role: <span className="text-foreground">{selectedNode.properties.role}</span></p>
            )}
            {selectedNode.properties?.classification && (
              <p>Clearance: <span className="text-foreground">{selectedNode.properties.classification}</span></p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
