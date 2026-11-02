'use client';

import React from 'react';
import { Tag } from '@/kit';

export interface RightDrawerItem {
  type: 'source' | 'citation';
  title: string;
  subtitle?: string;
  score?: number;
  excerpt?: string;
  sourceUrl?: string;
  relatedPeople?: string[];
  relatedTeams?: string[];
  relatedProjects?: string[];
  provenancePath?: string[];
  metadata?: Record<string, any>;
}

interface RightDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  item: RightDrawerItem | null;
}

export function RightDrawer({ isOpen, onClose, item }: RightDrawerProps) {
  if (!isOpen || !item) return null;

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-full sm:w-[480px] bg-card border-l border-border shadow-2xl flex flex-col animate-fade-in font-mono">
      {/* Header */}
      <div className="h-14 border-b border-border px-5 flex items-center justify-between bg-muted/20">
        <div className="flex items-center gap-2">
          <Tag tone={item.type === 'source' ? 'neutral' : 'accent'}>
            {item.type.toUpperCase()}
          </Tag>
          <span className="text-xs font-semibold text-foreground truncate max-w-[280px]">
            {item.title}
          </span>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded-xs hover:bg-muted text-muted-foreground hover:text-foreground text-sm"
          title="Close drawer"
        >
          ✕
        </button>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-5 space-y-5 text-xs">
        {/* Title & Subtitle */}
        <div>
          <h3 className="text-base font-semibold text-foreground">{item.title}</h3>
          {item.subtitle && (
            <p className="text-muted-foreground text-xs mt-1 truncate">{item.subtitle}</p>
          )}
          {typeof item.score === 'number' && (
            <div className="mt-2 flex items-center gap-2">
              <span className="text-muted-foreground text-[10px] uppercase">Relevance Score:</span>
              <Tag tone="ok">{(item.score * 100).toFixed(1)}%</Tag>
            </div>
          )}
        </div>

        {/* Excerpt / Raw Grounded Evidence */}
        {item.excerpt && (
          <div className="space-y-1.5">
            <span className="text-[10px] text-muted-foreground uppercase font-semibold block">
              Grounded Evidence Excerpt
            </span>
            <div className="p-3 rounded-xs border border-border/70 bg-muted/20 text-foreground leading-relaxed whitespace-pre-wrap">
              {item.excerpt}
            </div>
          </div>
        )}

        {/* Source URL / Document Storage Key */}
        {item.sourceUrl && (
          <div className="space-y-1">
            <span className="text-[10px] text-muted-foreground uppercase font-semibold block">
              Storage Resource Locator
            </span>
            <div className="p-2 rounded-xs border border-border/40 bg-background text-[11px] text-accent truncate">
              {item.sourceUrl}
            </div>
          </div>
        )}

        {/* Multi-Hop Provenance Associations */}
        <div className="space-y-3 pt-3 border-t border-border/50">
          <span className="text-[10px] text-muted-foreground uppercase font-semibold block">
            Multi-Hop Provenance Attribution
          </span>

          <div className="grid grid-cols-1 gap-2.5">
            {/* Authors / Owners */}
            <div className="p-2.5 rounded-xs border border-border/40 bg-muted/15 space-y-1">
              <span className="text-[10px] text-muted-foreground uppercase">Authoring Persons</span>
              <div className="flex flex-wrap gap-1">
                {item.relatedPeople && item.relatedPeople.length > 0 ? (
                  item.relatedPeople.map((p) => (
                    <Tag key={p} tone="accent">{p}</Tag>
                  ))
                ) : (
                  <span className="text-muted-foreground text-[11px]">System Ingested</span>
                )}
              </div>
            </div>

            {/* Teams */}
            <div className="p-2.5 rounded-xs border border-border/40 bg-muted/15 space-y-1">
              <span className="text-[10px] text-muted-foreground uppercase">Responsible Team</span>
              <div className="flex flex-wrap gap-1">
                {item.relatedTeams && item.relatedTeams.length > 0 ? (
                  item.relatedTeams.map((t) => (
                    <Tag key={t} tone="ok">{t}</Tag>
                  ))
                ) : (
                  <span className="text-muted-foreground text-[11px]">Cross-functional</span>
                )}
              </div>
            </div>

            {/* Projects */}
            <div className="p-2.5 rounded-xs border border-border/40 bg-muted/15 space-y-1">
              <span className="text-[10px] text-muted-foreground uppercase">Parent Initiative</span>
              <div className="flex flex-wrap gap-1">
                {item.relatedProjects && item.relatedProjects.length > 0 ? (
                  item.relatedProjects.map((pr) => (
                    <Tag key={pr} tone="warn">{pr}</Tag>
                  ))
                ) : (
                  <span className="text-muted-foreground text-[11px]">Core Architecture</span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Traversal Paths if available */}
        {item.provenancePath && item.provenancePath.length > 0 && (
          <div className="space-y-1.5 pt-2 border-t border-border/50">
            <span className="text-[10px] text-muted-foreground uppercase font-semibold block">
              Knowledge Graph Traversal Chain
            </span>
            <div className="p-2.5 rounded-xs border border-border/40 bg-background space-y-1">
              {item.provenancePath.map((pathStr, idx) => (
                <div key={idx} className="text-[11px] text-muted-foreground flex items-center gap-1.5">
                  <span className="text-foreground">●</span>
                  <span>{pathStr}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

