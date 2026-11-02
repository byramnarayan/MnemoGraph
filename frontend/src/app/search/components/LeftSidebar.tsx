'use client';

import React, { useState } from 'react';
import { Tag } from '@/kit';

export interface CollectionItem {
  id: string;
  name: string;
  store_type: 'FalkorDB' | 'PostgreSQL' | 'Object Storage' | 'Qdrant' | string;
  entity_count: number;
  description: string;
  can_delete: boolean;
}

export interface MemoryEpisodeItem {
  id: string;
  session_id: string;
  query: string;
  answer: string;
  confidence: number;
  sources: any[];
  provenance: any[];
  cypher_query?: string;
  created_at: string;
}

interface LeftSidebarProps {
  // Collections props
  collections: CollectionItem[];
  collectionsLoading: boolean;
  onDeleteCollection: (storeType: string, collectionId: string) => Promise<void>;
  isAdmin: boolean;

  // Memory History props
  history: MemoryEpisodeItem[];
  historyLoading: boolean;
  selectedEpisodeId: string | null;
  onSelectEpisode: (episode: MemoryEpisodeItem) => void;
  onRefreshHistory: () => void;
}

export function LeftSidebar({
  collections,
  collectionsLoading,
  onDeleteCollection,
  isAdmin,
  history,
  historyLoading,
  selectedEpisodeId,
  onSelectEpisode,
  onRefreshHistory,
}: LeftSidebarProps) {
  const [isOpen, setIsOpen] = useState(true);
  const [activeTab, setActiveTab] = useState<'collections' | 'history'>('collections');
  const [selectedStoreFilter, setSelectedStoreFilter] = useState<string>('ALL');
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const storeTypes = ['ALL', 'FalkorDB', 'PostgreSQL', 'Storage', 'Qdrant'];

  const filteredCollections = selectedStoreFilter === 'ALL'
    ? collections
    : collections.filter((c) =>
        c.store_type.toLowerCase().includes(selectedStoreFilter.toLowerCase())
      );

  const handleDelete = async (col: CollectionItem) => {
    const confirmDelete = window.confirm(
      `Are you sure you want to delete/purge collection "${col.name}" from ${col.store_type}? This operation is irreversible.`
    );
    if (!confirmDelete) return;

    setDeletingId(col.id);
    try {
      await onDeleteCollection(col.store_type, col.id);
    } finally {
      setDeletingId(null);
    }
  };

  const getStoreBadgeTone = (store: string) => {
    switch (store.toLowerCase()) {
      case 'falkordb':
        return 'accent';
      case 'qdrant':
        return 'warn';
      case 'postgresql':
        return 'ok';
      default:
        return 'neutral';
    }
  };

  const formatTimestamp = (isoStr: string) => {
    try {
      const d = new Date(isoStr);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + ', ' +
             d.toLocaleDateString([], { month: 'short', day: 'numeric' });
    } catch {
      return isoStr;
    }
  };

  return (
    <aside
      className={`transition-all duration-300 ease-in-out border-r border-border bg-card/60 backdrop-blur-sm flex flex-col shrink-0 ${
        isOpen ? 'w-80' : 'w-12'
      }`}
    >
      {/* Header Bar with Toggle Switcher */}
      <div className="h-14 border-b border-border px-3 flex items-center justify-between">
        {isOpen ? (
          <div className="flex items-center rounded-xs border border-border bg-muted/30 p-0.5 text-[11px] font-mono">
            <button
              onClick={() => setActiveTab('collections')}
              className={`px-2.5 py-1 rounded-xs uppercase tracking-wider transition-colors ${
                activeTab === 'collections'
                  ? 'bg-accent text-accent-foreground font-semibold shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              Collections ({collections.length})
            </button>
            <button
              onClick={() => {
                setActiveTab('history');
                onRefreshHistory();
              }}
              className={`px-2.5 py-1 rounded-xs uppercase tracking-wider transition-colors ${
                activeTab === 'history'
                  ? 'bg-accent text-accent-foreground font-semibold shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              Memory ({history.length})
            </button>
          </div>
        ) : (
          <span className="text-[10px] font-mono text-muted-foreground uppercase rotate-90 mx-auto">
            {activeTab}
          </span>
        )}

        <button
          onClick={() => setIsOpen(!isOpen)}
          title={isOpen ? 'Collapse panel' : 'Expand panel'}
          className="p-1.5 rounded-xs hover:bg-muted text-muted-foreground hover:text-foreground text-xs font-mono"
        >
          {isOpen ? '◀' : '▶'}
        </button>
      </div>

      {isOpen && (
        <div className="flex-1 overflow-y-auto p-3 space-y-3 font-mono text-xs">
          {/* TAB 1: COLLECTIONS */}
          {activeTab === 'collections' && (
            <div className="space-y-3">
              {/* Filter Pills */}
              <div className="flex flex-wrap gap-1 pb-1">
                {storeTypes.map((st) => (
                  <button
                    key={st}
                    onClick={() => setSelectedStoreFilter(st)}
                    className={`text-[10px] px-2 py-0.5 rounded-xs uppercase tracking-wider transition-colors ${
                      selectedStoreFilter === st
                        ? 'bg-accent text-accent-foreground font-semibold'
                        : 'bg-muted/40 text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    {st}
                  </button>
                ))}
              </div>

              {collectionsLoading ? (
                <div className="space-y-2">
                  {[1, 2, 3, 4].map((i) => (
                    <div key={i} className="h-16 rounded-xs border border-border/40 bg-muted/20 animate-pulse" />
                  ))}
                </div>
              ) : filteredCollections.length === 0 ? (
                <div className="text-center p-6 text-xs text-muted-foreground border border-dashed border-border/60 rounded-xs">
                  No collections found.
                </div>
              ) : (
                <div className="space-y-2">
                  {filteredCollections.map((col) => (
                    <div
                      key={col.id}
                      className="p-3 rounded-xs border border-border/60 bg-muted/10 hover:border-accent/50 transition-all space-y-1.5"
                    >
                      <div className="flex items-start justify-between gap-1.5">
                        <span className="text-xs font-semibold text-foreground leading-snug truncate" title={col.name}>
                          {col.name}
                        </span>
                        <Tag tone={getStoreBadgeTone(col.store_type)}>
                          {col.store_type.slice(0, 7)}
                        </Tag>
                      </div>

                      <p className="text-[10px] text-muted-foreground leading-relaxed line-clamp-2">
                        {col.description}
                      </p>

                      <div className="flex items-center justify-between pt-1 border-t border-border/30 text-[10px]">
                        <span className="text-muted-foreground">
                          {col.entity_count.toLocaleString()} items
                        </span>

                        {col.can_delete && isAdmin && (
                          <button
                            onClick={() => handleDelete(col)}
                            disabled={deletingId === col.id}
                            className="text-warn hover:underline font-medium uppercase tracking-wider transition-colors"
                          >
                            {deletingId === col.id ? 'Deleting...' : 'Delete'}
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB 2: TEMPORAL EPISODIC MEMORY HISTORY */}
          {activeTab === 'history' && (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-[10px] text-muted-foreground uppercase px-1">
                <span>Timeline (Ascending)</span>
                <span>{history.length} Sessions</span>
              </div>

              {historyLoading ? (
                <div className="space-y-2">
                  {[1, 2, 3, 4].map((i) => (
                    <div key={i} className="h-16 rounded-xs border border-border/40 bg-muted/20 animate-pulse" />
                  ))}
                </div>
              ) : history.length === 0 ? (
                <div className="text-center p-6 text-xs text-muted-foreground border border-dashed border-border/60 rounded-xs">
                  No conversation memory recorded yet. Ask a question to begin.
                </div>
              ) : (
                <div className="space-y-2">
                  {history.map((ep) => {
                    const isSelected = ep.id === selectedEpisodeId;
                    return (
                      <div
                        key={ep.id}
                        onClick={() => onSelectEpisode(ep)}
                        className={`p-3 rounded-xs border cursor-pointer transition-all space-y-1.5 ${
                          isSelected
                            ? 'border-accent bg-accent/15 shadow-sm'
                            : 'border-border/60 bg-muted/10 hover:border-accent/40'
                        }`}
                      >
                        <div className="flex items-center justify-between text-[10px]">
                          <span className="text-muted-foreground">
                            {formatTimestamp(ep.created_at)}
                          </span>
                          <Tag tone={ep.confidence >= 0.85 ? 'ok' : 'accent'}>
                            {(ep.confidence * 100).toFixed(0)}%
                          </Tag>
                        </div>

                        <h4 className="text-xs font-semibold text-foreground line-clamp-2 leading-snug">
                          {ep.query}
                        </h4>

                        <div className="flex items-center justify-between text-[10px] text-muted-foreground pt-1 border-t border-border/30">
                          <span>Sources: {ep.sources?.length || 0}</span>
                          <span className="text-accent hover:underline">Inspect ▶</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </aside>
  );
}

