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

interface CollectionsBarProps {
  collections: CollectionItem[];
  loading: boolean;
  onDeleteCollection: (storeType: string, collectionId: string) => Promise<void>;
  isAdmin: boolean;
}

export function CollectionsBar({
  collections,
  loading,
  onDeleteCollection,
  isAdmin,
}: CollectionsBarProps) {
  const [isOpen, setIsOpen] = useState(true);
  const [selectedStoreFilter, setSelectedStoreFilter] = useState<string>('ALL');
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const storeTypes = ['ALL', 'FalkorDB', 'PostgreSQL', 'Object Storage', 'Qdrant'];

  const filtered = selectedStoreFilter === 'ALL'
    ? collections
    : collections.filter((c) => c.store_type.toLowerCase() === selectedStoreFilter.toLowerCase());

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

  return (
    <aside
      className={`transition-all duration-300 ease-in-out border-r border-border bg-card/60 backdrop-blur-sm flex flex-col shrink-0 ${
        isOpen ? 'w-80' : 'w-12'
      }`}
    >
      {/* Header Bar */}
      <div className="h-14 border-b border-border px-3.5 flex items-center justify-between">
        {isOpen && (
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono font-semibold uppercase tracking-wider text-foreground">
              Collections
            </span>
            <Tag tone="neutral">{collections.length}</Tag>
          </div>
        )}
        <button
          onClick={() => setIsOpen(!isOpen)}
          title={isOpen ? 'Collapse collections panel' : 'Expand collections panel'}
          className="p-1.5 rounded-xs hover:bg-muted text-muted-foreground hover:text-foreground text-xs font-mono"
        >
          {isOpen ? '◀' : '▶'}
        </button>
      </div>

      {isOpen && (
        <div className="flex-1 overflow-y-auto p-3 space-y-3 font-mono">
          {/* Store Filter Tabs */}
          <div className="flex flex-wrap gap-1 pb-1">
            {storeTypes.map((st) => (
              <button
                key={st}
                onClick={() => setSelectedStoreFilter(st)}
                className={`text-[10px] px-2 py-1 rounded-xs uppercase tracking-wider transition-colors ${
                  selectedStoreFilter === st
                    ? 'bg-accent text-accent-foreground font-semibold'
                    : 'bg-muted/40 text-muted-foreground hover:text-foreground'
                }`}
              >
                {st === 'ALL' ? 'ALL' : st.replace('Object Storage', 'Storage')}
              </button>
            ))}
          </div>

          {/* Collections List */}
          {loading ? (
            <div className="space-y-2">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-16 rounded-xs border border-border/40 bg-muted/20 animate-pulse" />
              ))}
            </div>
          ) : filtered.length === 0 ? (
            <div className="text-center p-6 text-xs text-muted-foreground border border-dashed border-border/60 rounded-xs">
              No collections found for this filter.
            </div>
          ) : (
            <div className="space-y-2">
              {filtered.map((col) => (
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

                    {/* Admin Delete Action */}
                    {col.can_delete && isAdmin && (
                      <button
                        onClick={() => handleDelete(col)}
                        disabled={deletingId === col.id}
                        className="text-warn hover:underline font-medium uppercase tracking-wider transition-colors"
                        title="Purge collection"
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
    </aside>
  );
}

