'use client';

import React, { useState } from 'react';
import { api } from '@/lib/api-client';
import { PostgresConnectionConfig, DiscoveredTable, TableMappingSelection } from './types';
import { Step1ConnectionForm } from './Step1ConnectionForm';
import { Step2TableMapping } from './Step2TableMapping';
import { Step3ReviewIngest } from './Step3ReviewIngest';

interface PostgresConnectorModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function PostgresConnectorModal({ isOpen, onClose, onSuccess }: PostgresConnectorModalProps) {
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [config, setConfig] = useState<PostgresConnectionConfig>({
    name: 'External PostgreSQL Warehouse',
    host: 'localhost',
    port: 5432,
    database: 'postgres',
    username: 'postgres',
    password: '',
    ssl_mode: 'prefer',
  });

  const [discoveredTables, setDiscoveredTables] = useState<DiscoveredTable[]>([]);
  const [selectedTables, setSelectedTables] = useState<Record<string, TableMappingSelection>>({});

  if (!isOpen) return null;

  const handleTestAndDiscover = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const testRes = await api.connectors.testPostgresConnection(config);
      if (!testRes.success) {
        throw new Error(testRes.error || 'Connection failed.');
      }
      const discRes = await api.connectors.discoverPostgresSchemas(config);
      const tables: DiscoveredTable[] = discRes.tables || [];
      setDiscoveredTables(tables);

      const initialMap: Record<string, TableMappingSelection> = {};
      tables.forEach((t) => {
        const key = `${t.schema_name}.${t.table_name}`;
        initialMap[key] = {
          enabled: true,
          entity_type: t.suggested_entity_type || 'Document',
          cursor_column: t.suggested_cursor_col,
        };
      });
      setSelectedTables(initialMap);
      setStep(2);
    } catch (err: any) {
      setError(err.message || 'Failed to connect to PostgreSQL.');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateAndIngest = async () => {
    setLoading(true);
    setError(null);
    try {
      const tablesPayload = discoveredTables
        .filter((t) => selectedTables[`${t.schema_name}.${t.table_name}`]?.enabled)
        .map((t) => {
          const mapping = selectedTables[`${t.schema_name}.${t.table_name}`];
          return {
            schema_name: t.schema_name,
            table_name: t.table_name,
            primary_key_columns: t.primary_keys || [],
            cursor_column: mapping.cursor_column || t.suggested_cursor_col || null,
            included_columns: t.columns.map((c) => c.name),
            excluded_columns: [],
            text_columns: t.columns
              .filter((c) => c.data_type.includes('char') || c.data_type.includes('text'))
              .map((c) => c.name),
            entity_type: mapping.entity_type,
            visibility_policy: 'Internal',
            enabled: true,
          };
        });

      const connectorRes = await api.connectors.createPostgresConnector({
        name: config.name,
        host: config.host,
        port: Number(config.port),
        database: config.database,
        username: config.username,
        password: config.password,
        ssl_mode: config.ssl_mode,
        tables: tablesPayload,
      });

      if (connectorRes.id) {
        await api.connectors.triggerPostgresSync(connectorRes.id);
      }
      onSuccess();
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to register PostgreSQL connector.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm animate-fade-in">
      <div className="bg-card border border-border rounded-sm shadow-2xl max-w-xl w-full p-6 space-y-4">
        <div className="flex items-center justify-between border-b pb-3 border-border/50">
          <div>
            <span className="font-mono text-xs px-1.5 py-0.5 rounded-xs bg-accent/20 text-accent font-semibold mr-2">
              Step {step} of 3
            </span>
            <h3 className="text-base font-semibold inline">
              {step === 1 && 'PostgreSQL Connection'}
              {step === 2 && 'Map Tables to UKGOE Ontology'}
              {step === 3 && 'Confirm Ingestion'}
            </h3>
          </div>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
            ✕
          </button>
        </div>

        {error && (
          <div className="p-3 text-xs bg-destructive/10 border border-destructive/20 text-destructive rounded-sm">
            {error}
          </div>
        )}

        {step === 1 && (
          <Step1ConnectionForm
            config={config}
            onChange={setConfig}
            onSubmit={handleTestAndDiscover}
            loading={loading}
          />
        )}

        {step === 2 && (
          <Step2TableMapping
            discoveredTables={discoveredTables}
            selectedTables={selectedTables}
            onTableChange={(key, update) =>
              setSelectedTables((prev) => ({
                ...prev,
                [key]: { ...prev[key], ...update },
              }))
            }
            onBack={() => setStep(1)}
            onNext={() => setStep(3)}
          />
        )}

        {step === 3 && (
          <Step3ReviewIngest
            config={config}
            selectedTables={selectedTables}
            onBack={() => setStep(2)}
            onConfirm={handleCreateAndIngest}
            loading={loading}
          />
        )}
      </div>
    </div>
  );
}
