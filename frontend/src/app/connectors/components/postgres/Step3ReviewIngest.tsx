'use client';

import React from 'react';
import { Button } from '@/kit';
import { PostgresConnectionConfig, TableMappingSelection } from './types';

interface Step3Props {
  config: PostgresConnectionConfig;
  selectedTables: Record<string, TableMappingSelection>;
  onBack: () => void;
  onConfirm: () => void;
  loading: boolean;
}

export function Step3ReviewIngest({
  config,
  selectedTables,
  onBack,
  onConfirm,
  loading,
}: Step3Props) {
  const activeTables = Object.entries(selectedTables)
    .filter(([_, v]) => v.enabled)
    .map(([k, v]) => `${k} (${v.entity_type})`)
    .join(', ');

  return (
    <div className="space-y-4">
      <div className="p-3 bg-muted/30 border border-border rounded-xs space-y-2 text-xs">
        <div>
          <strong className="text-muted-foreground">Connector:</strong> {config.name}
        </div>
        <div>
          <strong className="text-muted-foreground">Host/DB:</strong> {config.host}:{config.port}/
          {config.database}
        </div>
        <div>
          <strong className="text-muted-foreground">Selected Tables:</strong>{' '}
          {activeTables || 'None selected'}
        </div>
      </div>
      <p className="text-[11px] text-muted-foreground">
        Ingestion runs asynchronously in the background. Entities and relations will immediately be
        available for search, incident forecasting, and knowledge transfer packages.
      </p>
      <div className="flex justify-between pt-2">
        <Button variant="ghost" onClick={onBack} className="text-xs">
          ← Back
        </Button>
        <Button onClick={onConfirm} disabled={loading} className="text-xs">
          {loading ? 'Ingesting...' : 'Confirm & Ingest'}
        </Button>
      </div>
    </div>
  );
}

