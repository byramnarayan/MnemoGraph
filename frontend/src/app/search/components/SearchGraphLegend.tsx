'use client';

import React from 'react';

export const UNIVERSAL_NODE_COLORS: Record<string, string> = {
  person: '#0ea5e9', // Sky Blue (Employee / Staff)
  project: '#6366f1', // Indigo (Project / Initiative)
  incident: '#f43f5e', // Rose (Network Event / Incident)
  decision: '#a855f7', // Purple (Decision / Governance)
  task: '#06b6d4', // Cyan (Service Ticket / Task)
  group: '#8b5cf6', // Violet (Department / Squad)
  location: '#f59e0b', // Amber (Radio Site / Office)
  document: '#10b981', // Emerald (Spec / Knowledge Doc)
  system: '#14b8a6', // Teal (System / Component)
};

export function SearchGraphLegend() {
  const legendItems = [
    { label: 'Employee', color: UNIVERSAL_NODE_COLORS.person },
    { label: 'Project', color: UNIVERSAL_NODE_COLORS.project },
    { label: 'Network Event', color: UNIVERSAL_NODE_COLORS.incident },
    { label: 'Decision', color: UNIVERSAL_NODE_COLORS.decision },
    { label: 'Service Ticket', color: UNIVERSAL_NODE_COLORS.task },
    { label: 'Department', color: UNIVERSAL_NODE_COLORS.group },
    { label: 'Radio Site', color: UNIVERSAL_NODE_COLORS.location },
    { label: 'Document', color: UNIVERSAL_NODE_COLORS.document },
  ];

  return (
    <div className="absolute top-4 left-6 z-20 flex items-center gap-3 px-3.5 py-1.5 rounded-xl border border-border bg-card/85 backdrop-blur-md shadow-sm text-xs font-mono select-none">
      <span className="font-bold text-[11px] uppercase tracking-wider text-muted-foreground mr-1">
        LEGEND
      </span>
      <div className="flex items-center gap-3 overflow-x-auto scrollbar-none">
        {legendItems.map((item) => (
          <div key={item.label} className="flex items-center gap-1.5 shrink-0">
            <span
              className="w-2.5 h-2.5 rounded-full shrink-0 shadow-xs"
              style={{ backgroundColor: item.color }}
            />
            <span className="text-[11px] text-foreground font-medium">
              {item.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

