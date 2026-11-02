'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import {
  api,
  ConnectorResponse,
  WarehouseItem,
  TableItem,
  SyncJobResponse,
} from '@/lib/api-client';
import {
  Button,
  Frame,
  Panel,
  Tag,
} from '@/kit';
import { DocumentUploadSection } from './components/DocumentUploadSection';

const CONNECTOR_TEMPLATES = [
  {
    type: 'databricks',
    name: 'Databricks',
    description: 'Sync notebooks, SQL warehouses, tables, catalogs, and run lineage.',
    icon: (
      <svg className="w-6 h-6 text-red-500" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 2L1 7l11 5 9-4.09V17h2V7L12 2zm0 8.3L3.8 6.5 12 2.8l8.2 3.7L12 10.3zM1 12l11 5 11-5v2l-11 5-11-5v-2zm0 5l11 5 11-5v2l-11 5-11-5v-2z" />
      </svg>
    ),
    isSupported: true,
  },
  {
    type: 'github',
    name: 'GitHub',
    description: 'Repositories, commits, PRs, and developer provenance.',
    icon: (
      <svg className="w-6 h-6 text-foreground" viewBox="0 0 24 24" fill="currentColor">
        <path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
      </svg>
    ),
    isSupported: false,
  },
  {
    type: 'slack',
    name: 'Slack',
    description: 'Channels, threads, discussions, and decision mentions.',
    icon: (
      <svg className="w-6 h-6 text-amber-500" viewBox="0 0 24 24" fill="currentColor">
        <path d="M6 15a2 2 0 1 1-2-2h2v2zm1 0a2 2 0 1 1 2 2v-2H7zm0-6a2 2 0 1 1 2-2v2H7zm-1 0a2 2 0 1 1-2-2h2v2zm6 1a2 2 0 1 1 2-2h-2v2zm0-6a2 2 0 1 1-2 2V4h2zm6 5a2 2 0 1 1-2-2h2v2zm-1 0a2 2 0 1 1-2-2v2h2zm-1 6a2 2 0 1 1-2 2v-2h2zm1 0a2 2 0 1 1 2 2h-2v-2z" />
      </svg>
    ),
    isSupported: false,
  },
  {
    type: 'jira',
    name: 'Jira',
    description: 'Sprint backlogs, tickets, tasks, and project velocity.',
    icon: (
      <svg className="w-6 h-6 text-blue-500" viewBox="0 0 24 24" fill="currentColor">
        <path d="M11.53 2c0 2.4 1.97 4.35 4.4 4.35h1.74V8.7c0 2.4 1.97 4.35 4.4 4.35V2h-10.54zm-4.36 4.35c0 2.4 1.97 4.35 4.4 4.35h1.74v2.35c0 2.4 1.97 4.35 4.4 4.35V6.35H7.17zM2.8 10.7c0 2.4 1.97 4.35 4.4 4.35h1.74v2.35c0 2.4 1.97 4.35 4.4 4.35V10.7H2.8z" />
      </svg>
    ),
    isSupported: false,
  },
];

export default function ConnectorsPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();

  const [connectors, setConnectors] = useState<ConnectorResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);
  const [successBanner, setSuccessBanner] = useState<string | null>(null);

  // Multi-Step Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [currentStep, setCurrentStep] = useState<1 | 2 | 3>(1);

  // Step 1: Credentials
  const [credentials, setCredentials] = useState({
    name: 'Databricks Production Workspace',
    host: 'https://dbc-95027497-0df9.cloud.databricks.com',
    workspace_id: '95027497-0df9',
    token: '',
    sync_interval_minutes: 60,
    auto_index: true,
  });

  const [verifying, setVerifying] = useState(false);
  const [verifiedUser, setVerifiedUser] = useState<string | null>(null);

  // Step 2: Warehouses & Tables
  const [warehouses, setWarehouses] = useState<WarehouseItem[]>([]);
  const [selectedWarehouseId, setSelectedWarehouseId] = useState<string>('');
  const [tables, setTables] = useState<TableItem[]>([]);
  const [selectedTables, setSelectedTables] = useState<string[]>([]);
  const [loadingWarehouseData, setLoadingWarehouseData] = useState(false);

  // Step 3: Submitting
  const [submitting, setSubmitting] = useState(false);
  const [syncingId, setSyncingId] = useState<string | null>(null);

  // Deletion Modal
  const [deleteTarget, setDeleteTarget] = useState<ConnectorResponse | null>(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login');
      return;
    }
    if (user) {
      loadConnectors();
    }
  }, [user, authLoading]);

  const loadConnectors = async () => {
    try {
      setLoading(true);
      setErrorBanner(null);
      const data = await api.connectors.list();
      setConnectors(data);
    } catch (err: any) {
      setErrorBanner(err.message || 'Failed to fetch configured connectors.');
    } finally {
      setLoading(false);
    }
  };

  // Step 1: Verify & Fetch Data
  const handleVerifyStep1 = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!credentials.host || !credentials.token || !credentials.workspace_id) {
      setErrorBanner('Please fill in Host, Workspace ID, and PAT token.');
      return;
    }

    setVerifying(true);
    setErrorBanner(null);
    try {
      const testRes = await api.connectors.testDatabricks({
        host: credentials.host,
        token: credentials.token,
        workspace_id: credentials.workspace_id,
      });

      if (!testRes.ok) {
        setErrorBanner(testRes.message || 'Could not verify credentials.');
        setVerifying(false);
        return;
      }

      setVerifiedUser(testRes.user_name || 'Authenticated User');

      // Fetch SQL warehouses & catalogs
      setLoadingWarehouseData(true);
      const [whList, tblList] = await Promise.all([
        api.connectors.getWarehouses({
          host: credentials.host,
          token: credentials.token,
          workspace_id: credentials.workspace_id,
        }).catch(() => []),
        api.connectors.getCatalogs({
          host: credentials.host,
          token: credentials.token,
          workspace_id: credentials.workspace_id,
        }).catch(() => []),
      ]);

      setWarehouses(whList);
      if (whList.length > 0) {
        setSelectedWarehouseId(whList[0].id);
      }
      setTables(tblList);
      // Default: select all discovered tables
      setSelectedTables(tblList.map((t) => t.full_name));

      setCurrentStep(2);
    } catch (err: any) {
      setErrorBanner(err.message || 'Verification failed');
    } finally {
      setVerifying(false);
      setLoadingWarehouseData(false);
    }
  };

  const handleToggleTable = (fullName: string) => {
    if (selectedTables.includes(fullName)) {
      setSelectedTables(selectedTables.filter((t) => t !== fullName));
    } else {
      setSelectedTables([...selectedTables, fullName]);
    }
  };

  const handleSelectAllTables = () => {
    if (selectedTables.length === tables.length) {
      setSelectedTables([]);
    } else {
      setSelectedTables(tables.map((t) => t.full_name));
    }
  };

  // Step 3: Save & Ingest
  const handleFinalSave = async () => {
    setSubmitting(true);
    setErrorBanner(null);
    try {
      const created = await api.connectors.createDatabricks({
        name: credentials.name,
        host: credentials.host,
        workspace_id: credentials.workspace_id,
        token: credentials.token,
        selected_warehouse_id: selectedWarehouseId || undefined,
        selected_tables: selectedTables,
        sync_interval_minutes: Number(credentials.sync_interval_minutes),
        auto_index: credentials.auto_index,
      });

      setSuccessBanner(`Workspace '${created.name}' successfully connected. Triggering initial ingestion...`);
      setIsModalOpen(false);
      setCurrentStep(1);

      // Trigger initial sync
      await api.connectors.triggerSync(created.id, 'full');
      loadConnectors();
    } catch (err: any) {
      setErrorBanner(err.message || 'Failed to create connector.');
    } finally {
      setSubmitting(false);
    }
  };

  // Delete Connector with cascade cleanup
  const handleDeleteConnector = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await api.connectors.delete(deleteTarget.id);
      setSuccessBanner(`Connector '${deleteTarget.name}' and all associated graph nodes and vectors removed.`);
      setDeleteTarget(null);
      loadConnectors();
    } catch (err: any) {
      setErrorBanner(err.message || 'Failed to delete connector.');
    } finally {
      setDeleting(false);
    }
  };

  const handleTriggerSync = async (connectorId: string, mode: 'full' | 'incremental' = 'full') => {
    try {
      setSyncingId(connectorId);
      const res = await api.connectors.triggerSync(connectorId, mode);
      setSuccessBanner(`Sync job ${res.job_id.slice(0, 8)} started in ${mode} mode.`);
    } catch (err: any) {
      setErrorBanner(err.message);
    } finally {
      setSyncingId(null);
    }
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] bg-background py-8">
      <Frame className="space-y-8">
        {/* Alerts / Banners */}
        {errorBanner && (
          <div className="p-3 rounded-sm border border-bad/40 bg-bad/10 text-bad text-xs font-mono flex items-center justify-between">
            <span>{errorBanner}</span>
            <button onClick={() => setErrorBanner(null)} className="text-bad hover:underline font-bold">✕</button>
          </div>
        )}
        {successBanner && (
          <div className="p-3 rounded-sm border border-ok/40 bg-ok/10 text-ok text-xs font-mono flex items-center justify-between">
            <span>{successBanner}</span>
            <button onClick={() => setSuccessBanner(null)} className="text-ok hover:underline font-bold">✕</button>
          </div>
        )}

        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border/70 pb-6">
          <div>
            <div className="flex items-center gap-2 text-xs font-mono text-muted-foreground uppercase tracking-wider">
              <Link href="/" className="hover:text-foreground">Home</Link>
              <span>/</span>
              <span className="text-foreground">Data Sources & Connectors</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-foreground mt-2">
              Enterprise Connectors
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              Select SQL warehouses and tables to feed graph reasoning and vector embeddings.
            </p>
          </div>

          <Button
            onClick={() => {
              setCurrentStep(1);
              setIsModalOpen(true);
            }}
            className="bg-accent text-accent-foreground font-semibold px-4 py-2 text-sm shadow-[0_0_15px_rgba(14,165,233,0.35)] self-start sm:self-auto"
          >
            + Connect New Source
          </Button>
        </div>

        {/* Active Connected Instances */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-medium text-foreground">Active Knowledge Connectors</h2>
            <span className="text-xs font-mono text-muted-foreground">
              {connectors.length} Connected
            </span>
          </div>

          {/* Direct Document Ingestion Pipeline Section */}
          <DocumentUploadSection onSuccess={() => loadConnectors()} />

          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[1, 2].map((i) => (
                <div key={i} className="h-40 rounded-sm border border-border/60 bg-card/40 animate-pulse p-5" />
              ))}
            </div>
          ) : connectors.length === 0 ? (
            <div className="rounded-sm border border-dashed border-border bg-card/30 p-10 text-center space-y-3">
              <div className="w-12 h-12 rounded-full bg-accent/10 border border-accent/30 mx-auto flex items-center justify-center text-accent">
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <h3 className="text-base font-medium text-foreground">No Active Connectors Configured</h3>
              <p className="text-xs text-muted-foreground max-w-md mx-auto">
                Connect Databricks to select your warehouse and tables for semantic intelligence.
              </p>
              <Button
                onClick={() => {
                  setCurrentStep(1);
                  setIsModalOpen(true);
                }}
                className="mt-2 text-xs px-4 py-2"
              >
                Setup Databricks Connector
              </Button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {connectors.map((c) => {
                let parsedTables: string[] = [];
                try {
                  if (c.selected_tables) {
                    parsedTables = JSON.parse(c.selected_tables);
                  }
                } catch {
                  parsedTables = [];
                }

                return (
                  <Panel key={c.id} className="p-5 flex flex-col justify-between space-y-4">
                    <div className="space-y-3">
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-3">
                          <div className="p-2 rounded-sm bg-red-500/10 border border-red-500/20 text-red-500">
                            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                              <path d="M12 2L1 7l11 5 9-4.09V17h2V7L12 2zm0 8.3L3.8 6.5 12 2.8l8.2 3.7L12 10.3zM1 12l11 5 11-5v2l-11 5-11-5v-2zm0 5l11 5 11-5v2l-11 5-11-5v-2z" />
                            </svg>
                          </div>
                          <div>
                            <h4 className="text-sm font-semibold text-foreground truncate max-w-[160px]">{c.name}</h4>
                            <span className="text-[10px] font-mono text-muted-foreground uppercase">{c.connector_type}</span>
                          </div>
                        </div>
                        <Tag tone="ok">{c.status}</Tag>
                      </div>

                      <div className="space-y-1 font-mono text-[11px] text-muted-foreground bg-muted/30 p-2.5 rounded-sm border border-border/40">
                        <div className="truncate">Host: <span className="text-foreground">{c.host}</span></div>
                        <div>Workspace: <span className="text-foreground">{c.workspace_id}</span></div>
                        {c.selected_warehouse_id && (
                          <div className="truncate">Warehouse: <span className="text-foreground">{c.selected_warehouse_id}</span></div>
                        )}
                        <div>
                          Tables: <span className="text-accent font-semibold">{parsedTables.length > 0 ? `${parsedTables.length} selected` : 'All notebooks'}</span>
                        </div>
                      </div>
                    </div>

                    <div className="space-y-2 pt-2 border-t border-border/40">
                      <div className="flex items-center gap-2">
                        <Button
                          variant="ghost"
                          className="text-xs h-8 flex-1"
                          disabled={syncingId === c.id}
                          onClick={() => handleTriggerSync(c.id, 'incremental')}
                        >
                          {syncingId === c.id ? 'Starting...' : 'Sync (Incr)'}
                        </Button>
                        <Button
                          className="text-xs h-8 flex-1"
                          disabled={syncingId === c.id}
                          onClick={() => handleTriggerSync(c.id, 'full')}
                        >
                          Full Ingest
                        </Button>
                      </div>
                      <button
                        onClick={() => setDeleteTarget(c)}
                        className="w-full text-center text-[11px] text-bad hover:underline py-1"
                      >
                        Disconnect & Cascade Delete
                      </button>
                    </div>
                  </Panel>
                );
              })}
            </div>
          )}
        </div>

        {/* Directory Catalog */}
        <div className="space-y-4 pt-6 border-t border-border/70">
          <div>
            <h2 className="text-lg font-medium text-foreground">Available Integration Catalog</h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              Select and configure enterprise systems.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {CONNECTOR_TEMPLATES.map((item) => (
              <div
                key={item.type}
                className="p-5 rounded-sm border border-border bg-card flex flex-col justify-between space-y-4 hover:border-accent/30 transition-colors"
              >
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="p-2.5 rounded-sm bg-muted border border-border">
                      {item.icon}
                    </div>
                    {item.isSupported ? (
                      <Tag tone="ok">Available</Tag>
                    ) : (
                      <Tag tone="neutral">Roadmap</Tag>
                    )}
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-foreground">{item.name}</h3>
                    <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                      {item.description}
                    </p>
                  </div>
                </div>

                <div>
                  {item.isSupported ? (
                    <Button
                      onClick={() => {
                        setCurrentStep(1);
                        setIsModalOpen(true);
                      }}
                      className="w-full text-xs h-8"
                    >
                      Configure Workspace →
                    </Button>
                  ) : (
                    <Button
                      disabled
                      variant="ghost"
                      className="w-full text-xs h-8 text-muted-foreground/60 cursor-not-allowed border border-border/40"
                    >
                      Coming Soon
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </Frame>

      {/* Multi-Step Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm animate-fade-in">
          <div className="bg-card border border-border rounded-sm shadow-2xl max-w-xl w-full p-6 space-y-5 relative">
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs px-1.5 py-0.5 rounded-xs bg-accent/20 text-accent font-semibold">
                    Step {currentStep} of 3
                  </span>
                  <h3 className="text-lg font-semibold text-foreground">
                    {currentStep === 1 && 'Databricks Credentials'}
                    {currentStep === 2 && 'Select SQL Warehouse & Tables'}
                    {currentStep === 3 && 'Confirm & Ingest'}
                  </h3>
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  {currentStep === 1 && 'Enter workspace host and personal access token (PAT).'}
                  {currentStep === 2 && 'Choose the SQL Warehouse and tables to include in the knowledge graph.'}
                  {currentStep === 3 && 'Verify settings before saving and beginning pipeline ingestion.'}
                </p>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-muted-foreground hover:text-foreground text-sm p-1"
              >
                ✕
              </button>
            </div>

            {/* Step 1: Credentials */}
            {currentStep === 1 && (
              <form onSubmit={handleVerifyStep1} className="space-y-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-mono text-muted-foreground uppercase">Connector Label</label>
                  <input
                    type="text"
                    value={credentials.name}
                    onChange={(e) => setCredentials({ ...credentials, name: e.target.value })}
                    className="w-full rounded-sm border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:border-accent"
                    required
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-mono text-muted-foreground uppercase">Databricks Host URL</label>
                  <input
                    type="url"
                    value={credentials.host}
                    onChange={(e) => setCredentials({ ...credentials, host: e.target.value })}
                    className="w-full rounded-sm border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:border-accent"
                    required
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-mono text-muted-foreground uppercase">Workspace ID</label>
                  <input
                    type="text"
                    value={credentials.workspace_id}
                    onChange={(e) => setCredentials({ ...credentials, workspace_id: e.target.value })}
                    className="w-full rounded-sm border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:border-accent"
                    required
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-mono text-muted-foreground uppercase">Personal Access Token (PAT)</label>
                  <input
                    type="password"
                    value={credentials.token}
                    onChange={(e) => setCredentials({ ...credentials, token: e.target.value })}
                    placeholder="dapi..."
                    className="w-full rounded-sm border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:border-accent"
                    required
                  />
                </div>

                <div className="flex items-center justify-end gap-2 pt-3 border-t border-border">
                  <Button
                    type="button"
                    variant="ghost"
                    className="text-xs h-9"
                    onClick={() => setIsModalOpen(false)}
                  >
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    className="text-xs h-9 px-4"
                    disabled={verifying}
                  >
                    {verifying ? 'Verifying...' : 'Next: Select Tables →'}
                  </Button>
                </div>
              </form>
            )}

            {/* Step 2: Warehouse & Tables */}
            {currentStep === 2 && (
              <div className="space-y-4">
                <div className="p-2.5 rounded-sm bg-ok/10 border border-ok/40 text-ok text-xs font-mono">
                  ✓ Verified connection for {verifiedUser}
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-mono text-muted-foreground uppercase">SQL Warehouse</label>
                  {warehouses.length > 0 ? (
                    <select
                      value={selectedWarehouseId}
                      onChange={(e) => setSelectedWarehouseId(e.target.value)}
                      className="w-full rounded-sm border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:border-accent"
                    >
                      {warehouses.map((w) => (
                        <option key={w.id} value={w.id}>
                          {w.name} ({w.id}) {w.state ? `[${w.state}]` : ''}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <div className="text-xs font-mono text-muted-foreground p-2 rounded-sm border border-border/60 bg-muted/20">
                      No Dedicated SQL Warehouses found. Standard workspace cluster compute will be used.
                    </div>
                  )}
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-mono text-muted-foreground uppercase">
                      Select Tables to Ingest ({selectedTables.length}/{tables.length})
                    </label>
                    <button
                      type="button"
                      onClick={handleSelectAllTables}
                      className="text-xs font-mono text-accent hover:underline"
                    >
                      {selectedTables.length === tables.length ? 'Deselect All' : 'Select All'}
                    </button>
                  </div>

                  <div className="max-h-48 overflow-y-auto rounded-sm border border-border bg-muted/20 p-2 space-y-1.5 font-mono text-xs">
                    {tables.map((t) => (
                      <label
                        key={t.full_name}
                        className="flex items-center justify-between p-1.5 rounded-xs hover:bg-card cursor-pointer"
                      >
                        <div className="flex items-center gap-2">
                          <input
                            type="checkbox"
                            checked={selectedTables.includes(t.full_name)}
                            onChange={() => handleToggleTable(t.full_name)}
                            className="rounded-xs border-border"
                          />
                          <span className="text-foreground">{t.full_name}</span>
                        </div>
                        <span className="text-[10px] text-muted-foreground uppercase">{t.table_type || 'TABLE'}</span>
                      </label>
                    ))}
                  </div>
                </div>

                <div className="flex items-center justify-between pt-3 border-t border-border">
                  <Button
                    type="button"
                    variant="ghost"
                    className="text-xs h-9"
                    onClick={() => setCurrentStep(1)}
                  >
                    ← Back
                  </Button>
                  <Button
                    type="button"
                    className="text-xs h-9 px-4"
                    onClick={() => setCurrentStep(3)}
                  >
                    Next: Review & Confirm →
                  </Button>
                </div>
              </div>
            )}

            {/* Step 3: Confirmation */}
            {currentStep === 3 && (
              <div className="space-y-4 font-mono text-xs">
                <div className="p-3 rounded-sm border border-border bg-muted/20 space-y-2">
                  <div>Workspace Host: <span className="text-foreground">{credentials.host}</span></div>
                  <div>Workspace ID: <span className="text-foreground">{credentials.workspace_id}</span></div>
                  <div>Selected Warehouse: <span className="text-foreground">{selectedWarehouseId || 'Default Cluster'}</span></div>
                  <div>Ingested Tables: <span className="text-accent">{selectedTables.length} tables selected</span></div>
                  <div>Auto-Index Vector Embeddings: <span className="text-foreground">Enabled</span></div>
                </div>

                <div className="flex items-center justify-between pt-3 border-t border-border">
                  <Button
                    type="button"
                    variant="ghost"
                    className="text-xs h-9"
                    onClick={() => setCurrentStep(2)}
                  >
                    ← Back
                  </Button>
                  <Button
                    type="button"
                    className="text-xs h-9 px-5 bg-accent text-accent-foreground font-semibold"
                    disabled={submitting}
                    onClick={handleFinalSave}
                  >
                    {submitting ? 'Connecting & Ingesting...' : 'Save & Begin Ingestion'}
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Confirmation Modal for Delete */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm animate-fade-in">
          <div className="bg-card border border-border rounded-sm shadow-2xl max-w-md w-full p-6 space-y-4">
            <h3 className="text-base font-semibold text-foreground">Disconnect & Delete Connector</h3>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Are you sure you want to disconnect <span className="text-foreground font-semibold">{deleteTarget.name}</span>?
              This will trigger a cascade cleanup across:
            </p>
            <ul className="text-xs font-mono text-muted-foreground list-disc list-inside space-y-1 bg-muted/30 p-2.5 rounded-sm">
              <li>PostgreSQL metadata & sync job history</li>
              <li>FalkorDB workspace, document, and ownership edges</li>
              <li>Qdrant vector chunks</li>
              <li>S3 raw files under databricks/{deleteTarget.workspace_id}/</li>
            </ul>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
              <Button
                variant="ghost"
                className="text-xs h-8"
                onClick={() => setDeleteTarget(null)}
              >
                Cancel
              </Button>
              <Button
                className="text-xs h-8 bg-bad/80 hover:bg-bad text-white"
                disabled={deleting}
                onClick={handleDeleteConnector}
              >
                {deleting ? 'Deleting...' : 'Confirm Disconnect'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
