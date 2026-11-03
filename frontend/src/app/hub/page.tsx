'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import { api } from '@/lib/api-client';
import { Button, Frame, Panel, Tag } from '@/kit';

interface EmployeeItem {
  id: string;
  full_name: string;
  email: string;
  role: string | null;
  team_id: string | null;
  department_id: string | null;
  created_at: string;
}

interface FullProfile {
  profile: {
    id: string;
    full_name: string;
    email: string;
    role: string | null;
    team_id: string | null;
    team_name: string;
    department_id: string;
    created_at: string;
    can_assign_handover: boolean;
  };
  projects: Array<{
    id: string;
    name: string;
    description: string;
    workspace_id: string | null;
    owner_team_id: string | null;
    created_at: string;
  }>;
  documents: Array<{
    id: string;
    title: string;
    source_system: string;
    source_id: string;
    project_id: string | null;
    storage_key: string | null;
    mime_type: string | null;
    created_at: string;
  }>;
  decisions: Array<{
    id: string;
    title: string;
    description: string | null;
    status: string;
    impact?: string | null;
    learnings?: string | null;
    timeline?: string | null;
    source_document_id: string | null;
    created_at: string;
  }>;
  handovers: {
    outgoing: Array<{
      id: string;
      target_employee_id: string;
      target_employee_name: string;
      target_employee_email: string;
      status: string;
      scope: string;
      handover_notes: string | null;
      created_at: string;
    }>;
    incoming: Array<{
      id: string;
      source_employee_id: string;
      source_employee_name: string;
      source_employee_email: string;
      status: string;
      scope: string;
      handover_notes: string | null;
      created_at: string;
    }>;
  };
}

interface DecisionItem {
  id: string;
  title: string;
  description: string | null;
  status: string;
  impact?: string | null;
  learnings?: string | null;
  timeline?: string | null;
  project_id?: string | null;
  source_document_id?: string | null;
  created_at: string;
}

export default function KnowledgeHubPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();

  // Active Tab: 'employees' | 'decisions'
  const [activeTab, setActiveTab] = useState<'employees' | 'decisions'>('employees');

  // Employee Directory State
  const [employees, setEmployees] = useState<EmployeeItem[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [profile, setProfile] = useState<FullProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [profileLoading, setProfileLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // Decisions Registry State (503 real decisions)
  const [decisions, setDecisions] = useState<DecisionItem[]>([]);
  const [selectedDecision, setSelectedDecision] = useState<DecisionItem | null>(null);
  const [decisionsLoading, setDecisionsLoading] = useState(false);
  const [decisionSearch, setDecisionSearch] = useState('');

  // Handover Modal State
  const [isHandoverModalOpen, setIsHandoverModalOpen] = useState(false);
  const [targetEmployeeId, setTargetEmployeeId] = useState('');
  const [handoverNotes, setHandoverNotes] = useState('');
  const [submittingHandover, setSubmittingHandover] = useState(false);
  const [handoverSuccessMsg, setHandoverSuccessMsg] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login');
      return;
    }
    if (user) {
      loadEmployees();
      loadDecisions();
    }
  }, [user, authLoading]);

  // Load Real Personnel from PostgreSQL
  const loadEmployees = async () => {
    setLoading(true);
    try {
      const data = await api.hub.listPeople();
      setEmployees(data || []);
      if (data && data.length > 0) {
        selectEmployee(data[0].id);
      }
    } catch (err) {
      console.error('Failed to load employee directory:', err);
      setEmployees([]);
    } finally {
      setLoading(false);
    }
  };

  // Load Real Decisions from PostgreSQL
  const loadDecisions = async () => {
    setDecisionsLoading(true);
    try {
      const data = await api.hub.listDecisions();
      setDecisions(data || []);
      if (data && data.length > 0) {
        setSelectedDecision(data[0]);
      }
    } catch (err) {
      console.error('Failed to load decisions registry:', err);
      setDecisions([]);
    } finally {
      setDecisionsLoading(false);
    }
  };

  const selectEmployee = async (id: string) => {
    setSelectedId(id);
    setProfileLoading(true);
    setHandoverSuccessMsg(null);
    try {
      const fullProf = await api.hub.getPersonFullProfile(id);
      setProfile(fullProf);
    } catch (err) {
      console.error('Failed to load full profile for employee:', id, err);
      setProfile(null);
    } finally {
      setProfileLoading(false);
    }
  };

  const handleCreateHandover = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedId || !targetEmployeeId) return;
    setSubmittingHandover(true);
    try {
      const res = await api.hub.createHandover(selectedId, {
        target_employee_id: targetEmployeeId,
        scope: 'all',
        notes: handoverNotes,
      });
      setHandoverSuccessMsg(res.message || 'Knowledge handover registered successfully!');
      setIsHandoverModalOpen(false);
      setHandoverNotes('');
      setTargetEmployeeId('');
      selectEmployee(selectedId);
    } catch (err: any) {
      console.error('Failed to assign knowledge handover:', err);
      alert(err.message || 'Failed to assign knowledge handover.');
    } finally {
      setSubmittingHandover(false);
    }
  };

  const filteredEmployees = employees.filter((emp) => {
    const q = searchQuery.toLowerCase();
    return (
      emp.full_name?.toLowerCase().includes(q) ||
      emp.email?.toLowerCase().includes(q) ||
      emp.role?.toLowerCase().includes(q)
    );
  });

  const filteredDecisions = decisions.filter((dec) => {
    const q = decisionSearch.toLowerCase();
    return (
      dec.title?.toLowerCase().includes(q) ||
      dec.description?.toLowerCase().includes(q) ||
      dec.status?.toLowerCase().includes(q) ||
      dec.impact?.toLowerCase().includes(q)
    );
  });

  return (
    <div className="min-h-[calc(100vh-4rem)] bg-background py-8">
      <Frame className="space-y-6">
        {/* Hub Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border/70 pb-5">
          <div>
            <div className="flex items-center gap-2 text-xs font-mono text-muted-foreground uppercase tracking-wider">
              <Link href="/" className="hover:text-foreground">Home</Link>
              <span>/</span>
              <span className="text-foreground">Enterprise Knowledge Hub</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-foreground mt-2">
              Enterprise Knowledge Directory & Architecture Hub
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              Live organizational intelligence: Inspect employees, team deliverables, knowledge handovers, and the complete registry of real architecture decisions.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Link
              href="/search"
              className="text-xs px-3 py-1.5 rounded border border-accent/40 bg-accent/10 hover:bg-accent/20 text-accent transition-all font-mono"
            >
              ← Search & Traversal Workspace
            </Link>
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-mono text-muted-foreground">Signed in as:</span>
              <Tag tone="accent">{user?.role || 'User'}</Tag>
            </div>
          </div>
        </div>

        {/* Tab Switcher */}
        <div className="flex border-b border-border/80 gap-2 font-mono text-xs">
          <button
            onClick={() => setActiveTab('employees')}
            className={`px-4 py-2.5 font-medium border-b-2 transition-all flex items-center gap-2 ${
              activeTab === 'employees'
                ? 'border-accent text-accent bg-accent/5'
                : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
            }`}
          >
            <span>Employees & Handover</span>
            <Tag tone={activeTab === 'employees' ? 'accent' : 'neutral'}>{employees.length}</Tag>
          </button>

          <button
            onClick={() => setActiveTab('decisions')}
            className={`px-4 py-2.5 font-medium border-b-2 transition-all flex items-center gap-2 ${
              activeTab === 'decisions'
                ? 'border-accent text-accent bg-accent/5'
                : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
            }`}
          >
            <span>Architecture Decisions Registry</span>
            <Tag tone={activeTab === 'decisions' ? 'accent' : 'neutral'}>{decisions.length}</Tag>
          </button>
        </div>

        {/* TAB 1: EMPLOYEES & HANDOVER */}
        {activeTab === 'employees' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            {/* Left Column: Employee Directory */}
            <div className="lg:col-span-4 space-y-3 font-mono">
              <div className="flex items-center justify-between text-xs text-muted-foreground px-1">
                <span>PERSONNEL ({filteredEmployees.length})</span>
                <span>SELECT TO INSPECT</span>
              </div>

              {/* Search Input */}
              <div className="relative">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search by name, role, email..."
                  className="w-full text-xs font-mono bg-card border border-border rounded-sm px-3 py-2 text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-accent"
                />
              </div>

              {loading ? (
                <div className="space-y-2">
                  {[1, 2, 3, 4, 5].map((i) => (
                    <div key={i} className="h-16 rounded-sm border border-border/60 bg-card/40 animate-pulse" />
                  ))}
                </div>
              ) : filteredEmployees.length === 0 ? (
                <div className="rounded-sm border border-dashed border-border p-8 text-center text-xs text-muted-foreground">
                  No employees match your search criteria.
                </div>
              ) : (
                <div className="space-y-2 max-h-[720px] overflow-y-auto pr-1">
                  {filteredEmployees.map((emp) => {
                    const isSelected = emp.id === selectedId;
                    return (
                      <div
                        key={emp.id}
                        onClick={() => selectEmployee(emp.id)}
                        className={`p-3.5 rounded-sm border cursor-pointer transition-all ${
                          isSelected
                            ? 'border-accent bg-accent/10 shadow-sm'
                            : 'border-border bg-card hover:border-accent/40'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <h4 className="text-sm font-medium text-foreground truncate max-w-[210px]">
                            {emp.full_name}
                          </h4>
                          <Tag tone={isSelected ? 'accent' : 'neutral'}>
                            {emp.role?.includes('VP') ? 'EXEC' : emp.role?.includes('Architect') ? 'ARCH' : 'MEMBER'}
                          </Tag>
                        </div>
                        <p className="text-xs font-mono text-muted-foreground mt-1 truncate">
                          {emp.role || emp.email}
                        </p>
                        <p className="text-[10px] font-mono text-muted-foreground/80 mt-0.5 truncate">
                          {emp.email}
                        </p>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Right Column: Employee Profile Details & Handover */}
            <div className="lg:col-span-8">
              {profileLoading ? (
                <div className="p-8 rounded-sm border border-border bg-card animate-pulse space-y-4 font-mono">
                  <div className="h-6 w-1/3 bg-muted rounded" />
                  <div className="h-4 w-1/2 bg-muted rounded" />
                  <div className="h-32 bg-muted/40 rounded mt-4" />
                </div>
              ) : !profile ? (
                <div className="rounded-sm border border-dashed border-border p-12 text-center text-muted-foreground text-sm font-mono">
                  Select an employee from the directory to inspect their portfolio and governance links.
                </div>
              ) : (
                <div className="space-y-5 font-mono">
                  {handoverSuccessMsg && (
                    <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-sm text-xs text-emerald-400">
                      ✓ {handoverSuccessMsg}
                    </div>
                  )}

                  {/* Profile Header Card */}
                  <Panel className="p-5 border-border bg-card">
                    <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
                      <div>
                        <div className="flex items-center gap-2">
                          <h2 className="text-xl font-bold text-foreground">{profile.profile.full_name}</h2>
                          <Tag tone="accent">{profile.profile.role || 'Contributor'}</Tag>
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">
                          {profile.profile.email} &bull; Team: <strong className="text-foreground">{profile.profile.team_name}</strong>
                        </p>
                      </div>

                      <Button
                        onClick={() => setIsHandoverModalOpen(true)}
                        className="text-xs font-mono h-8 px-3"
                      >
                        Assign Knowledge Handover →
                      </Button>
                    </div>
                  </Panel>

                  {/* Incoming & Outgoing Handovers */}
                  {(profile.handovers.outgoing.length > 0 || profile.handovers.incoming.length > 0) && (
                    <Panel className="p-4 border-border bg-card text-xs space-y-3">
                      <h4 className="font-semibold text-foreground uppercase tracking-wide">Knowledge Handover Register</h4>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        <div className="space-y-2">
                          <span className="text-[10px] text-muted-foreground uppercase block font-medium">Outgoing Handovers</span>
                          {profile.handovers.outgoing.length === 0 ? (
                            <span className="text-muted-foreground text-[11px]">None recorded</span>
                          ) : (
                            profile.handovers.outgoing.map((h) => (
                              <div key={h.id} className="p-2.5 rounded border border-border/50 bg-muted/10 space-y-1">
                                <div className="flex justify-between">
                                  <span className="text-foreground font-medium">To: {h.target_employee_name}</span>
                                  <Tag tone="ok">{h.status}</Tag>
                                </div>
                                {h.handover_notes && <p className="text-[11px] text-muted-foreground">{h.handover_notes}</p>}
                              </div>
                            ))
                          )}
                        </div>

                        <div className="space-y-2">
                          <span className="text-[10px] text-muted-foreground uppercase block font-medium">Incoming Handovers</span>
                          {profile.handovers.incoming.length === 0 ? (
                            <span className="text-muted-foreground text-[11px]">None recorded</span>
                          ) : (
                            profile.handovers.incoming.map((h) => (
                              <div key={h.id} className="p-2.5 rounded border border-border/50 bg-muted/10 space-y-1">
                                <div className="flex justify-between">
                                  <span className="text-foreground font-medium">From: {h.source_employee_name}</span>
                                  <Tag tone="accent">{h.status}</Tag>
                                </div>
                                {h.handover_notes && <p className="text-[11px] text-muted-foreground">{h.handover_notes}</p>}
                              </div>
                            ))
                          )}
                        </div>
                      </div>
                    </Panel>
                  )}

                  {/* Portfolio Grid: Projects, Decisions, Documents */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Projects */}
                    <Panel className="p-4 border-border bg-card text-xs space-y-2.5">
                      <div className="flex justify-between items-center">
                        <span className="font-semibold text-foreground uppercase">Associated Projects</span>
                        <Tag tone="accent">{profile.projects.length}</Tag>
                      </div>
                      {profile.projects.length === 0 ? (
                        <p className="text-muted-foreground text-[11px]">No active projects assigned</p>
                      ) : (
                        <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                          {profile.projects.map((pr) => (
                            <div key={pr.id} className="p-2 rounded border border-border/50 bg-muted/10">
                              <h5 className="font-semibold text-foreground">{pr.name}</h5>
                              {pr.description && <p className="text-[11px] text-muted-foreground mt-0.5 line-clamp-2">{pr.description}</p>}
                            </div>
                          ))}
                        </div>
                      )}
                    </Panel>

                    {/* Decisions */}
                    <Panel className="p-4 border-border bg-card text-xs space-y-2.5">
                      <div className="flex justify-between items-center">
                        <span className="font-semibold text-foreground uppercase">Decisions Made</span>
                        <Tag tone="warn">{profile.decisions.length}</Tag>
                      </div>
                      {profile.decisions.length === 0 ? (
                        <p className="text-muted-foreground text-[11px]">No decisions recorded</p>
                      ) : (
                        <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                          {profile.decisions.map((dec) => (
                            <div key={dec.id} className="p-2 rounded border border-border/50 bg-muted/10">
                              <div className="flex justify-between items-start gap-1">
                                <h5 className="font-semibold text-foreground text-[11px]">{dec.title}</h5>
                                <Tag tone="ok">{dec.status}</Tag>
                              </div>
                              {dec.description && <p className="text-[10px] text-muted-foreground mt-0.5 line-clamp-2">{dec.description}</p>}
                            </div>
                          ))}
                        </div>
                      )}
                    </Panel>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 2: ARCHITECTURE DECISIONS REGISTRY (503 Real Decisions) */}
        {activeTab === 'decisions' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start font-mono">
            {/* Decisions Master List */}
            <div className="lg:col-span-5 space-y-3">
              <div className="flex items-center justify-between text-xs text-muted-foreground px-1">
                <span>DECISIONS ({filteredDecisions.length} OF {decisions.length})</span>
                <span>POSTGRESQL STORE</span>
              </div>

              {/* Search */}
              <div className="relative">
                <input
                  type="text"
                  value={decisionSearch}
                  onChange={(e) => setDecisionSearch(e.target.value)}
                  placeholder="Filter decisions by title, impact, status..."
                  className="w-full text-xs font-mono bg-card border border-border rounded-sm px-3 py-2 text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-accent"
                />
              </div>

              {decisionsLoading ? (
                <div className="space-y-2">
                  {[1, 2, 3, 4, 5].map((i) => (
                    <div key={i} className="h-16 rounded border border-border/60 bg-card/40 animate-pulse" />
                  ))}
                </div>
              ) : filteredDecisions.length === 0 ? (
                <div className="rounded border border-dashed border-border p-8 text-center text-xs text-muted-foreground">
                  No decisions match your search query.
                </div>
              ) : (
                <div className="space-y-2 max-h-[720px] overflow-y-auto pr-1">
                  {filteredDecisions.map((dec) => {
                    const isSelected = dec.id === selectedDecision?.id;
                    return (
                      <div
                        key={dec.id}
                        onClick={() => setSelectedDecision(dec)}
                        className={`p-3 rounded border cursor-pointer transition-all ${
                          isSelected
                            ? 'border-accent bg-accent/10 shadow-sm'
                            : 'border-border bg-card hover:border-accent/40'
                        }`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <h4 className="text-xs font-semibold text-foreground line-clamp-1">{dec.title}</h4>
                          <Tag tone={dec.status === 'accepted' ? 'ok' : 'neutral'}>
                            {dec.status.toUpperCase()}
                          </Tag>
                        </div>
                        {dec.description && (
                          <p className="text-[11px] text-muted-foreground mt-1 line-clamp-2">
                            {dec.description}
                          </p>
                        )}
                        <div className="mt-1.5 flex items-center gap-2 text-[10px] text-muted-foreground">
                          {dec.project_id && <span>Project: <strong className="text-foreground">{dec.project_id}</strong></span>}
                          <span>&bull;</span>
                          <span>ID: {dec.id.slice(0, 8)}...</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Decision Details Panel */}
            <div className="lg:col-span-7">
              {!selectedDecision ? (
                <div className="rounded border border-dashed border-border p-12 text-center text-muted-foreground text-xs">
                  Select a decision from the registry to inspect rationale, impact, and learnings.
                </div>
              ) : (
                <Panel className="p-5 border-border bg-card space-y-4 text-xs font-mono">
                  <div className="flex items-start justify-between gap-3 border-b border-border/70 pb-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <Tag tone="accent">ARCHITECTURE DECISION</Tag>
                        <span className="text-muted-foreground text-[10px]">ID: {selectedDecision.id}</span>
                      </div>
                      <h3 className="text-base font-bold text-foreground mt-1.5">{selectedDecision.title}</h3>
                    </div>
                    <Tag tone={selectedDecision.status === 'accepted' ? 'ok' : 'neutral'}>
                      {selectedDecision.status.toUpperCase()}
                    </Tag>
                  </div>

                  {selectedDecision.description && (
                    <div className="space-y-1">
                      <span className="text-[10px] uppercase text-muted-foreground font-semibold block">Decision Scope & Description</span>
                      <p className="p-3 rounded border border-border/50 bg-muted/10 text-foreground leading-relaxed">
                        {selectedDecision.description}
                      </p>
                    </div>
                  )}

                  {selectedDecision.impact && (
                    <div className="space-y-1">
                      <span className="text-[10px] uppercase text-accent font-semibold block">Architectural Impact</span>
                      <p className="p-3 rounded border border-accent/20 bg-accent/5 text-foreground leading-relaxed">
                        {selectedDecision.impact}
                      </p>
                    </div>
                  )}

                  {selectedDecision.learnings && (
                    <div className="space-y-1">
                      <span className="text-[10px] uppercase text-emerald-400 font-semibold block">Key Learnings & Observations</span>
                      <p className="p-3 rounded border border-emerald-500/20 bg-emerald-500/5 text-foreground leading-relaxed">
                        {selectedDecision.learnings}
                      </p>
                    </div>
                  )}

                  {selectedDecision.timeline && (
                    <div className="space-y-1">
                      <span className="text-[10px] uppercase text-muted-foreground font-semibold block">Execution Timeline</span>
                      <p className="p-2.5 rounded border border-border/40 bg-muted/10 text-foreground">
                        {selectedDecision.timeline}
                      </p>
                    </div>
                  )}

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 border-t border-border/50 text-[11px]">
                    <div>
                      <span className="text-[10px] uppercase text-muted-foreground font-medium block">Parent Project</span>
                      <span className="text-foreground font-semibold">{selectedDecision.project_id || 'Global Enterprise Architecture'}</span>
                    </div>

                    <div>
                      <span className="text-[10px] uppercase text-muted-foreground font-medium block">Source Document</span>
                      <span className="text-foreground font-mono">{selectedDecision.source_document_id || 'Direct Governance Log'}</span>
                    </div>
                  </div>
                </Panel>
              )}
            </div>
          </div>
        )}
      </Frame>

      {/* Handover Assignment Modal */}
      {isHandoverModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm animate-fade-in font-mono">
          <div className="bg-card border border-border rounded-sm shadow-2xl max-w-md w-full p-6 space-y-4">
            <h3 className="text-base font-semibold text-foreground">
              Assign Knowledge Handover
            </h3>
            <p className="text-xs text-muted-foreground">
              Transfer or assign <strong className="text-foreground">{profile?.profile.full_name}</strong>'s complete engineering portfolio and decision context to another colleague.
            </p>

            <form onSubmit={handleCreateHandover} className="space-y-3 text-xs">
              <div className="space-y-1">
                <label className="text-muted-foreground uppercase text-[10px]">Recipient Colleague</label>
                <select
                  value={targetEmployeeId}
                  onChange={(e) => setTargetEmployeeId(e.target.value)}
                  className="w-full rounded-xs border border-border bg-background px-3 py-2 text-foreground focus:outline-none focus:border-accent"
                  required
                >
                  <option value="">Select recipient...</option>
                  {employees
                    .filter((e) => e.id !== selectedId)
                    .map((e) => (
                      <option key={e.id} value={e.id}>
                        {e.full_name} ({e.role || e.email})
                      </option>
                    ))}
                </select>
              </div>

              <div className="space-y-1">
                <label className="text-muted-foreground uppercase text-[10px]">Handover Scope</label>
                <select
                  defaultValue="all"
                  className="w-full rounded-xs border border-border bg-background px-3 py-2 text-foreground focus:outline-none focus:border-accent"
                >
                  <option value="all">Full Portfolio (Projects, Documents & Decisions)</option>
                  <option value="projects">Projects Only</option>
                  <option value="decisions">Decisions & Governance Only</option>
                </select>
              </div>

              <div className="space-y-1">
                <label className="text-muted-foreground uppercase text-[10px]">Handover Instructions / Notes</label>
                <textarea
                  value={handoverNotes}
                  onChange={(e) => setHandoverNotes(e.target.value)}
                  placeholder="Specify handover reason, onboarding details, or project scope..."
                  className="w-full h-20 rounded-xs border border-border bg-background px-3 py-2 text-foreground focus:outline-none focus:border-accent"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-border">
                <Button
                  type="button"
                  variant="ghost"
                  className="text-xs h-8"
                  onClick={() => setIsHandoverModalOpen(false)}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  className="text-xs h-8 px-4"
                  disabled={submittingHandover}
                >
                  {submittingHandover ? 'Assigning...' : 'Confirm Handover'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
