'use client';

import React, { useState } from 'react';
import { UniversalCollection, MemoryEpisode } from '../types';

interface SearchSidebarProps {
  collections: UniversalCollection[];
  collectionsLoading: boolean;
  onDeleteCollection: (storeType: string, collectionId: string) => Promise<void>;
  isAdmin: boolean;
  history: MemoryEpisode[];
  historyLoading: boolean;
  selectedEpisodeId: string | null;
  onSelectEpisode: (ep: MemoryEpisode) => void;
  onRefreshHistory: () => void;
}

export function SearchSidebar({
  collections,
  collectionsLoading,
  onDeleteCollection,
  isAdmin,
  history,
  historyLoading,
  selectedEpisodeId,
  onSelectEpisode,
  onRefreshHistory,
}: SearchSidebarProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [activeTab, setActiveTab] = useState<'collections' | 'memory'>('collections');
  const [storeFilter, setStoreFilter] = useState<string>('ALL');
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const stores = ['ALL', 'FalkorDB', 'PostgreSQL', 'Storage'];

  const filteredCollections = storeFilter === 'ALL'
    ? collections
    : collections.filter((c) => c.store_type.toLowerCase().includes(storeFilter.toLowerCase()));

  const handleDelete = async (col: UniversalCollection) => {
    if (!confirm(`Purge collection "${col.name}"? This operation cannot be reversed.`)) return;
    setDeletingId(col.id);
    try {
      await onDeleteCollection(col.store_type, col.id);
    } finally {
      setDeletingId(null);
    }
  };

  if (isCollapsed) {
    return (
      <aside className="w-12 border-r border-border bg-card/60 flex flex-col items-center py-4 space-y-4 shrink-0 transition-all font-mono select-none">
        <button
          onClick={() => setIsCollapsed(false)}
          className="w-8 h-8 rounded-md border border-border bg-background hover:bg-card flex items-center justify-center text-muted-foreground hover:text-foreground text-xs transition-colors"
          title="Expand sidebar"
        >
          ▶
        </button>
        <button
          onClick={() => { setIsCollapsed(false); setActiveTab('collections'); }}
          className={`w-8 h-8 rounded-md border flex items-center justify-center text-xs transition-colors ${
            activeTab === 'collections' ? 'bg-accent/20 border-accent/40 text-accent font-bold' : 'border-border text-muted-foreground hover:text-foreground'
          }`}
          title="Collections"
        >
          🗂
        </button>
        <button
          onClick={() => { setIsCollapsed(false); setActiveTab('memory'); }}
          className={`w-8 h-8 rounded-md border flex items-center justify-center text-xs transition-colors ${
            activeTab === 'memory' ? 'bg-accent/20 border-accent/40 text-accent font-bold' : 'border-border text-muted-foreground hover:text-foreground'
          }`}
          title="Memory History"
        >
          🧠
        </button>
      </aside>
    );
  }

  return (
    <aside className="w-80 border-r border-border bg-card/60 flex flex-col h-full shrink-0 transition-all font-mono select-none">
      {/* Header & Collapse Toggle */}
      <div className="p-3 border-b border-border flex items-center justify-between">
        <div className="flex items-center gap-1.5 p-0.5 rounded-lg border border-border bg-background text-[11px]">
          <button
            onClick={() => setActiveTab('collections')}
            className={`px-3 py-1 rounded-md transition-colors ${
              activeTab === 'collections' ? 'bg-accent text-accent-foreground font-semibold shadow-xs' : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            Collections ({collections.length})
          </button>
          <button
            onClick={() => setActiveTab('memory')}
            className={`px-3 py-1 rounded-md transition-colors ${
              activeTab === 'memory' ? 'bg-accent text-accent-foreground font-semibold shadow-xs' : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            Memory ({history.length})
          </button>
        </div>
        <button
          onClick={() => setIsCollapsed(true)}
          className="w-7 h-7 rounded-md border border-border bg-background hover:bg-card flex items-center justify-center text-muted-foreground hover:text-foreground text-xs"
          title="Collapse sidebar"
        >
          ◀
        </button>
      </div>

      {/* Body: Collections Tab */}
      {activeTab === 'collections' ? (
        <div className="flex-1 overflow-y-auto p-3 space-y-3 text-xs">
          {/* Filter Pills */}
          <div className="flex items-center gap-1 overflow-x-auto pb-1 text-[10px]">
            {stores.map((s) => (
              <button
                key={s}
                onClick={() => setStoreFilter(s)}
                className={`px-2 py-0.5 rounded border whitespace-nowrap transition-colors ${
                  storeFilter === s ? 'bg-accent/20 text-accent border-accent/40 font-semibold' : 'bg-muted/40 text-muted-foreground border-border hover:text-foreground'
                }`}
              >
                {s}
              </button>
            ))}
          </div>

          {collectionsLoading ? (
            <div className="p-8 text-center text-muted-foreground text-xs">Loading partitions...</div>
          ) : filteredCollections.length === 0 ? (
            <div className="p-8 text-center text-muted-foreground text-xs">No collections found.</div>
          ) : (
            <div className="space-y-2">
              {filteredCollections.map((col, idx) => (
                <div
                  key={`${col.store_type}-${col.id}-${idx}`}
                  className="p-2.5 rounded-lg border border-border bg-card/70 hover:border-accent/40 transition-colors space-y-1"
                >
                  <div className="flex items-center justify-between gap-1">
                    <span className="font-semibold text-foreground truncate text-xs" title={col.name}>
                      {col.name}
                    </span>
                    <span className="text-[9px] uppercase px-1.5 py-0.2 rounded border border-border bg-muted text-muted-foreground shrink-0">
                      {col.store_type}
                    </span>
                  </div>
                  <p className="text-[11px] text-muted-foreground line-clamp-2 leading-relaxed">
                    {col.description}
                  </p>
                  <div className="flex items-center justify-between pt-1 border-t border-border/40 text-[10px]">
                    <span className="text-muted-foreground">{col.entity_count.toLocaleString()} items</span>
                    {col.can_delete && isAdmin && (
                      <button
                        onClick={() => handleDelete(col)}
                        disabled={deletingId === col.id}
                        className="text-rose-500 hover:underline uppercase text-[9px]"
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
      ) : (
        /* Body: Memory Episodes Tab */
        <div className="flex-1 overflow-y-auto p-3 space-y-2 text-xs">
          <div className="flex items-center justify-between pb-1 text-[11px] text-muted-foreground border-b border-border">
            <span>Episodic Recall</span>
            <button onClick={onRefreshHistory} className="hover:text-foreground">Refresh</button>
          </div>
          {historyLoading ? (
            <div className="p-8 text-center text-muted-foreground">Recalling memory...</div>
          ) : history.length === 0 ? (
            <div className="p-8 text-center text-muted-foreground">No prior episodes recorded.</div>
          ) : (
            history.map((ep, idx) => (
              <div
                key={`${ep.id}-${idx}`}
                onClick={() => onSelectEpisode(ep)}
                className={`p-2.5 rounded-lg border transition-colors cursor-pointer space-y-1 ${
                  selectedEpisodeId === ep.id ? 'bg-accent/15 border-accent text-foreground' : 'bg-card/70 border-border hover:border-accent/40'
                }`}
              >
                <div className="flex items-center justify-between gap-1">
                  <span className="font-medium truncate text-xs text-foreground">{ep.query}</span>
                  <span className="text-[10px] text-muted-foreground">{(ep.confidence * 100).toFixed(0)}%</span>
                </div>
                <p className="text-[11px] text-muted-foreground line-clamp-2">{ep.answer}</p>
              </div>
            ))
          )}
        </div>
      )}
    </aside>
  );
}

