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
    impact: string;
    learnings: string;
    timeline: string;
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

export default function KnowledgeHubPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();

  const [employees, setEmployees] = useState<EmployeeItem[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [profile, setProfile] = useState<FullProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [profileLoading, setProfileLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // Handover modal state
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
    }
  }, [user, authLoading]);

  const loadEmployees = async () => {
    setLoading(true);
    try {
      const data = await api.hub.listPeople();
      setEmployees(data);
      if (data.length > 0) {
        selectEmployee(data[0].id);
      }
    } catch (err) {
      console.error('Failed to load employee directory:', err);
      setEmployees([]);
    } finally {
      setLoading(false);
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
      // Reload current employee profile to reflect updated handovers
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
              Employee Knowledge Directory & Handover Hub
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              Deep organizational intelligence: inspect complete employee projects, documentation, strategic decisions, and manage cross-team knowledge handovers.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-muted-foreground">Signed in as:</span>
            <Tag tone="accent">{user?.role || 'User'}</Tag>
          </div>
        </div>

        {/* Master-Detail Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column: Employee Directory */}
          <div className="lg:col-span-4 space-y-3">
            <div className="flex items-center justify-between text-xs font-mono text-muted-foreground px-1">
              <span>EMPLOYEES ({filteredEmployees.length})</span>
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
                No employees match your search or authorization scope.
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

          {/* Right Column: Deep Unified Employee Data Sections */}
          <div className="lg:col-span-8">
            {profileLoading ? (
              <Panel className="p-12 text-center text-xs font-mono text-muted-foreground animate-pulse">
                Resolving full employee knowledge graph, projects, and decision history...
              </Panel>
            ) : !profile ? (
              <Panel className="p-12 text-center text-xs text-muted-foreground">
                Select an employee from the directory to inspect their complete profile and enterprise deliverables.
              </Panel>
            ) : (
              <div className="space-y-6">
                {/* 1. EMPLOYEE HEADER & PROFILE METADATA */}
                <Panel className="p-6 space-y-4">
                  <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 border-b border-border/60 pb-4">
                    <div>
                      <div className="flex items-center gap-2">
                        <Tag tone="accent">EMPLOYEE PROFILE</Tag>
                        <span className="font-mono text-xs text-muted-foreground">ID: {profile.profile.id}</span>
                      </div>
                      <h2 className="text-2xl font-semibold text-foreground mt-1.5">
                        {profile.profile.full_name}
                      </h2>
                      <p className="text-xs text-muted-foreground mt-0.5 font-mono">
                        {profile.profile.role || 'Enterprise Engineer'} &bull; {profile.profile.department_id}
                      </p>
                    </div>

                    {/* Action: Assign Knowledge Handover (Visible to HR / Manager / Admin) */}
                    {profile.profile.can_assign_handover && (
                      <Button
                        onClick={() => setIsHandoverModalOpen(true)}
                        className="text-xs h-9 px-4 shrink-0 font-medium"
                      >
                        + Assign Knowledge Handover
                      </Button>
                    )}
                  </div>

                  {handoverSuccessMsg && (
                    <div className="p-3 rounded-xs border border-ok/40 bg-ok/10 text-xs font-mono text-ok">
                      [OK] {handoverSuccessMsg}
                    </div>
                  )}

                  {/* Profile Metadata Grid */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono text-xs">
                    <div className="p-2.5 rounded-xs border border-border/40 bg-muted/20">
                      <span className="text-muted-foreground block text-[10px] uppercase">Corporate Email</span>
                      <span className="text-foreground truncate block font-medium">{profile.profile.email}</span>
                    </div>
                    <div className="p-2.5 rounded-xs border border-border/40 bg-muted/20">
                      <span className="text-muted-foreground block text-[10px] uppercase">Assigned Team</span>
                      <span className="text-foreground truncate block font-medium">{profile.profile.team_name}</span>
                    </div>
                    <div className="p-2.5 rounded-xs border border-border/40 bg-muted/20">
                      <span className="text-muted-foreground block text-[10px] uppercase">Department</span>
                      <span className="text-foreground truncate block font-medium">{profile.profile.department_id}</span>
                    </div>
                    <div className="p-2.5 rounded-xs border border-border/40 bg-muted/20">
                      <span className="text-muted-foreground block text-[10px] uppercase">Directory Status</span>
                      <span className="text-ok truncate block font-medium">Active Clearance</span>
                    </div>
                  </div>

                  {/* Active Knowledge Handovers Display */}
                  {(profile.handovers.outgoing.length > 0 || profile.handovers.incoming.length > 0) && (
                    <div className="pt-2 border-t border-border/40 space-y-2">
                      <span className="text-[10px] font-mono text-muted-foreground uppercase tracking-wider block">
                        Knowledge Handover Links
                      </span>
                      <div className="flex flex-wrap gap-2 text-xs font-mono">
                        {profile.handovers.outgoing.map((h) => (
                          <div key={h.id} className="p-2 rounded-xs border border-accent/40 bg-accent/10 flex items-center gap-2">
                            <span className="text-accent font-semibold">Handed over to:</span>
                            <span className="text-foreground">{h.target_employee_name} ({h.target_employee_email})</span>
                            <Tag tone="accent">ACTIVE</Tag>
                          </div>
                        ))}
                        {profile.handovers.incoming.map((h) => (
                          <div key={h.id} className="p-2 rounded-xs border border-ok/40 bg-ok/10 flex items-center gap-2">
                            <span className="text-ok font-semibold">Inherited from:</span>
                            <span className="text-foreground">{h.source_employee_name} ({h.source_employee_email})</span>
                            <Tag tone="ok">INHERITED</Tag>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </Panel>

                {/* 2. ALL PROJECTS DATA SECTION */}
                <Panel className="p-6 space-y-4">
                  <div className="flex items-center justify-between border-b border-border/60 pb-3">
                    <h3 className="text-sm font-semibold tracking-tight text-foreground uppercase tracking-wider font-mono">
                      Associated Projects & Initiatives ({profile.projects.length})
                    </h3>
                    <Tag tone="neutral">PORTFOLIO</Tag>
                  </div>

                  {profile.projects.length === 0 ? (
                    <p className="text-xs text-muted-foreground font-mono">No direct projects assigned.</p>
                  ) : (
                    <div className="grid grid-cols-1 gap-3">
                      {profile.projects.map((proj) => (
                        <div key={proj.id} className="p-4 rounded-xs border border-border/60 bg-muted/15 space-y-2">
                          <div className="flex items-start justify-between">
                            <div>
                              <h4 className="text-sm font-semibold text-foreground">{proj.name}</h4>
                              <span className="text-[10px] font-mono text-muted-foreground">Workspace: {proj.workspace_id || 'telcosphere-prod'}</span>
                            </div>
                            <Tag tone="accent">ACTIVE INITIATIVE</Tag>
                          </div>
                          <p className="text-xs text-muted-foreground leading-relaxed">
                            {proj.description}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                </Panel>

                {/* 3. STRATEGIC DECISIONS, TIMELINES & LEARNINGS SECTION */}
                <Panel className="p-6 space-y-4">
                  <div className="flex items-center justify-between border-b border-border/60 pb-3">
                    <div>
                      <h3 className="text-sm font-semibold tracking-tight text-foreground uppercase tracking-wider font-mono">
                        Strategic Decisions, Impact & Retrospective Learnings ({profile.decisions.length})
                      </h3>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        Architectural Decision Records (ADRs) and post-incident corrective procedures authored by this employee.
                      </p>
                    </div>
                    <Tag tone="ok">RATIFIED</Tag>
                  </div>

                  {profile.decisions.length === 0 ? (
                    <p className="text-xs text-muted-foreground font-mono">No ratified decisions recorded.</p>
                  ) : (
                    <div className="space-y-3.5 max-h-[600px] overflow-y-auto pr-1">
                      {profile.decisions.map((dec) => (
                        <div key={dec.id} className="p-4 rounded-xs border border-border/70 bg-card/60 space-y-3">
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <h4 className="text-sm font-semibold text-foreground leading-snug">
                                {dec.title}
                              </h4>
                              {dec.description && (
                                <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                                  {dec.description}
                                </p>
                              )}
                            </div>
                            <Tag tone="accent">{dec.status.toUpperCase()}</Tag>
                          </div>

                          {/* Decision Sub-Grids: Timeline, Impact, Learnings */}
                          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 text-xs font-mono pt-1">
                            {/* Timeline */}
                            <div className="p-2.5 rounded-xs border border-border/50 bg-muted/20 space-y-1">
                              <span className="text-[10px] font-semibold uppercase text-accent block">Timeline</span>
                              <p className="text-muted-foreground text-[11px] leading-relaxed">
                                {dec.timeline}
                              </p>
                            </div>

                            {/* Impact */}
                            <div className="p-2.5 rounded-xs border border-border/50 bg-muted/20 space-y-1">
                              <span className="text-[10px] font-semibold uppercase text-ok block">Business & Tech Impact</span>
                              <p className="text-muted-foreground text-[11px] leading-relaxed">
                                {dec.impact}
                              </p>
                            </div>

                            {/* Learnings */}
                            <div className="p-2.5 rounded-xs border border-border/50 bg-muted/20 space-y-1">
                              <span className="text-[10px] font-semibold uppercase text-warn block">Key Learnings & RCA</span>
                              <p className="text-muted-foreground text-[11px] leading-relaxed">
                                {dec.learnings}
                              </p>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </Panel>

                {/* 4. ALL DOCUMENTS & NOTEBOOKS SECTION */}
                <Panel className="p-6 space-y-4">
                  <div className="flex items-center justify-between border-b border-border/60 pb-3">
                    <div>
                      <h3 className="text-sm font-semibold tracking-tight text-foreground uppercase tracking-wider font-mono">
                        Authored Documents, Telemetry Notebooks & Specifications ({profile.documents.length})
                      </h3>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        PySpark data pipelines, 3GPP RFC specifications, and MOP runbooks owned by this employee.
                      </p>
                    </div>
                    <Tag tone="neutral">DELIVERABLES</Tag>
                  </div>

                  {profile.documents.length === 0 ? (
                    <p className="text-xs text-muted-foreground font-mono">No documents or notebooks owned.</p>
                  ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 max-h-[450px] overflow-y-auto pr-1">
                      {profile.documents.map((doc) => (
                        <div key={doc.id} className="p-3 rounded-xs border border-border/50 bg-muted/15 flex flex-col justify-between space-y-2">
                          <div>
                            <div className="flex items-center justify-between">
                              <span className="text-[10px] font-mono text-muted-foreground uppercase">{doc.source_system}</span>
                              <Tag tone="neutral">{doc.mime_type?.includes('python') ? 'PYSPARK' : 'MARKDOWN'}</Tag>
                            </div>
                            <h5 className="text-xs font-semibold text-foreground mt-1 truncate" title={doc.title}>
                              {doc.title}
                            </h5>
                          </div>
                          <span className="text-[10px] font-mono text-muted-foreground truncate block">
                            Key: {doc.storage_key || doc.source_id}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </Panel>
              </div>
            )}
          </div>
        </div>
      </Frame>

      {/* Handover Assignment Modal */}
      {isHandoverModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm animate-fade-in">
          <div className="bg-card border border-border rounded-sm shadow-2xl max-w-md w-full p-6 space-y-4">
            <h3 className="text-base font-semibold text-foreground">
              Assign Knowledge Handover
            </h3>
            <p className="text-xs text-muted-foreground">
              Transfer or assign <strong className="text-foreground">{profile?.profile.full_name}</strong>'s complete engineering knowledge, project deliverables, and decision context to another team member.
            </p>

            <form onSubmit={handleCreateHandover} className="space-y-3 text-xs font-mono">
              <div className="space-y-1">
                <label className="text-muted-foreground uppercase text-[10px]">Recipient Employee</label>
                <select
                  value={targetEmployeeId}
                  onChange={(e) => setTargetEmployeeId(e.target.value)}
                  className="w-full rounded-xs border border-border bg-background px-3 py-2 text-foreground focus:outline-none focus:border-accent"
                  required
                >
                  <option value="">Select target colleague...</option>
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
                  <option value="all">Full Portfolio (All Projects, Documents & Decisions)</option>
                  <option value="projects">Project Handover Only</option>
                  <option value="runbooks">MOP & Runbooks Only</option>
                </select>
              </div>

              <div className="space-y-1">
                <label className="text-muted-foreground uppercase text-[10px]">Handover Instructions / Notes</label>
                <textarea
                  value={handoverNotes}
                  onChange={(e) => setHandoverNotes(e.target.value)}
                  placeholder="Specify handover reason, onboarding notes, or NOC supervision scope..."
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
