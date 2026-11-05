'use client';

import React from 'react';
import { Button } from '@/kit';
import { DiscoveredTable, TableMappingSelection, ONTOLOGY_CLASSES } from './types';

interface Step2Props {
  discoveredTables: DiscoveredTable[];
  selectedTables: Record<string, TableMappingSelection>;
  onTableChange: (key: string, update: Partial<TableMappingSelection>) => void;
  onBack: () => void;
  onNext: () => void;
}

export function Step2TableMapping({
  discoveredTables,
  selectedTables,
  onTableChange,
  onBack,
  onNext,
}: Step2Props) {
  return (
    <div className="space-y-4">
      <p className="text-xs text-muted-foreground">
        Select tables to ingest and map each to its Universal Entity class. Ingested nodes populate
        FalkorDB, Qdrant search, Decision Risk Explorer, and KTP Hub.
      </p>
      <div className="max-h-60 overflow-y-auto space-y-2 pr-1">
        {discoveredTables.map((t) => {
          const key = `${t.schema_name}.${t.table_name}`;
          const mapping = selectedTables[key] || { enabled: true, entity_type: 'Document' };
          return (
            <div
              key={key}
              className="flex items-center justify-between p-2 border border-border/50 rounded-xs bg-muted/20"
            >
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={mapping.enabled}
                  onChange={(e) => onTableChange(key, { enabled: e.target.checked })}
                />
                <span className="font-mono text-xs">{key}</span>
                <span className="text-[10px] text-muted-foreground">
                  ({t.columns?.length || 0} cols)
                </span>
              </div>
              <select
                className="px-2 py-1 text-xs bg-background border border-border rounded-xs"
                value={mapping.entity_type}
                onChange={(e) => onTableChange(key, { entity_type: e.target.value })}
              >
                {ONTOLOGY_CLASSES.map((cls) => (
                  <option key={cls} value={cls}>
                    {cls}
                  </option>
                ))}
              </select>
            </div>
          );
        })}
      </div>
      <div className="flex justify-between pt-2">
        <Button variant="ghost" onClick={onBack} className="text-xs">
          ← Back
        </Button>
        <Button onClick={onNext} className="text-xs">
          Next: Review Ingestion →
        </Button>
      </div>
    </div>
  );
}

