'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import { ktpApi } from '@/lib/ktp-api';
import {
  KnowledgeTransferPackageResponse,
  KtpPersonSummary,
  SuccessorCandidate,
} from './types';

import { KtpSidebar } from './components/KtpSidebar';
import { KtpDetailHeader } from './components/KtpDetailHeader';
import { KtpProfileSection } from './components/KtpProfileSection';
import { KtpProjectsSection } from './components/KtpProjectsSection';
import { KtpTasksSection } from './components/KtpTasksSection';
import { KtpDecisionsSection } from './components/KtpDecisionsSection';
import { KtpIncidentsSection } from './components/KtpIncidentsSection';
import { KtpKnowledgeSection } from './components/KtpKnowledgeSection';
import { KtpRiskSection } from './components/KtpRiskSection';
import { KtpHandoverSection } from './components/KtpHandoverSection';
import { KtpHandoverModal } from './components/KtpHandoverModal';

export default function KtpHubPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();

  const [people, setPeople] = useState<KtpPersonSummary[]>([]);
  const [selectedPerson, setSelectedPerson] = useState<KtpPersonSummary | null>(null);
  const [ktpData, setKtpData] = useState<KnowledgeTransferPackageResponse | null>(null);

  const [isLoadingDirectory, setIsLoadingDirectory] = useState(true);
  const [isLoadingKtp, setIsLoadingKtp] = useState(false);
  const [isLocking, setIsLocking] = useState(false);
  const [activeFilter, setActiveFilter] = useState('all');
  const [isHandoverModalOpen, setIsHandoverModalOpen] = useState(false);
  const [notification, setNotification] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // 1. Auth Guard
  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/auth/login');
    }
  }, [user, authLoading, router]);

  // 2. Load Personnel Directory
  const loadPeople = useCallback(async () => {
    try {
      setIsLoadingDirectory(true);
      const data = await ktpApi.listPersonnel();
      setPeople(data);
      if (data.length > 0 && !selectedPerson) {
        // Pick first rich profile (e.g. Sarah Connor or person with active projects) over synthetic dup nodes
        const preferred =
          data.find((p) => p.person_id === 'person:sarah-connor') ||
          data.find((p) => !p.person_id.startsWith('dup_') && (p.active_projects_count > 0 || p.open_tasks_count > 0)) ||
          data.find((p) => !p.person_id.startsWith('dup_')) ||
          data[0];
        setSelectedPerson(preferred);
      }
    } catch (err: any) {
      setNotification({ type: 'error', message: err.message || 'Failed to load personnel directory.' });
    } finally {
      setIsLoadingDirectory(false);
    }
  }, [selectedPerson]);

  useEffect(() => {
    if (user) {
      loadPeople();
    }
  }, [user, loadPeople]);

  // 3. Load Person's Full KTP Subgraph
  const loadPersonKtp = useCallback(async (personId: string) => {
    try {
      setIsLoadingKtp(true);
      const data = await ktpApi.getPersonKtp(personId);
      setKtpData(data);
    } catch (err: any) {
      setNotification({ type: 'error', message: err.message || 'Failed to retrieve KTP details.' });
    } finally {
      setIsLoadingKtp(false);
    }
  }, []);

  useEffect(() => {
    if (selectedPerson) {
      loadPersonKtp(selectedPerson.person_id);
    }
  }, [selectedPerson, loadPersonKtp]);

  // 4. Lock & Generate Formal KTP Document
  const handleLockKtp = async () => {
    if (!selectedPerson) return;
    try {
      setIsLocking(true);
      const res = await ktpApi.generateKtp(selectedPerson.person_id);
      setKtpData(res);
      setSelectedPerson((prev) => (prev ? { ...prev, ktp_generated: true, ktp_doc_id: res.doc_id } : prev));
      setNotification({ type: 'success', message: `Knowledge Transfer Package locked as Document ${res.doc_id}.` });
    } catch (err: any) {
      setNotification({ type: 'error', message: err.message || 'Failed to lock KTP document.' });
    } finally {
      setIsLocking(false);
    }
  };

  // 5. Assign Handover
  const handleAssignHandover = async (targetPersonId: string, notes?: string) => {
    if (!selectedPerson) return;
    const res = await ktpApi.assignHandover(selectedPerson.person_id, {
      target_person_id: targetPersonId,
      notes,
    });
    setNotification({ type: 'success', message: res.message });
    loadPeople();
  };

  if (authLoading || (!user && typeof window !== 'undefined')) {
    return (
      <div className="flex items-center justify-center min-h-[calc(100vh-4rem)] bg-background font-mono text-xs text-muted-foreground">
        Authenticating institutional clearance...
      </div>
    );
  }

  const successorCandidates: SuccessorCandidate[] =
    ktpData?.section_g_handover?.successor_candidates || [];

  return (
    <div className="flex h-[calc(100vh-4rem)] bg-background text-foreground overflow-hidden font-sans">
      {/* Toast Notification */}
      {notification && (
        <div
          className={`fixed bottom-5 right-5 z-50 px-4 py-2.5 rounded-xl border text-xs font-mono shadow-xl transition-all ${
            notification.type === 'success'
              ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-600 dark:text-emerald-300'
              : 'bg-rose-500/15 border-rose-500/30 text-rose-600 dark:text-rose-300'
          }`}
        >
          <div className="flex items-center gap-2">
            <span>{notification.message}</span>
            <button
              onClick={() => setNotification(null)}
              className="ml-2 text-muted-foreground hover:text-foreground"
            >
              ×
            </button>
          </div>
        </div>
      )}

      {/* Handover Modal */}
      {selectedPerson && (
        <KtpHandoverModal
          isOpen={isHandoverModalOpen}
          onClose={() => setIsHandoverModalOpen(false)}
          sourcePerson={selectedPerson}
          candidates={successorCandidates}
          onAssignHandover={handleAssignHandover}
        />
      )}

      {/* Left Column: Personnel Directory Sidebar */}
      <KtpSidebar
        people={people}
        selectedPerson={selectedPerson}
        onSelectPerson={setSelectedPerson}
        isLoading={isLoadingDirectory}
        activeFilter={activeFilter}
        onFilterChange={setActiveFilter}
      />

      {/* Right Column: Interconnected Subgraph Details Pane */}
      <main className="flex-1 flex flex-col h-full overflow-hidden bg-background">
        {selectedPerson ? (
          <>
            {/* Person Header & Action Bar */}
            <KtpDetailHeader
              person={selectedPerson}
              ktpData={ktpData}
              onOpenHandoverModal={() => setIsHandoverModalOpen(true)}
              onLockKtp={handleLockKtp}
              isLocking={isLocking}
            />

            {/* Sticky Navigation Jump Bar */}
            <div className="sticky top-0 z-30 border-b border-border bg-card/85 backdrop-blur-md px-6 py-2.5 flex items-center gap-1.5 overflow-x-auto scrollbar-none text-xs font-mono">
              <span className="text-muted-foreground text-[10px] uppercase tracking-wider font-semibold mr-1.5 shrink-0">
                Jump to Section:
              </span>
              {[
                { id: 'sec-profile', label: 'A: Profile' },
                { id: 'sec-projects', label: `B.1: Projects (${ktpData?.section_b_ownership?.active_projects.length || 0})` },
                { id: 'sec-tasks', label: `B.2: Tasks (${ktpData?.section_b_ownership?.active_tasks.length || 0})` },
                { id: 'sec-decisions', label: 'C: Decisions & RCA' },
                { id: 'sec-incidents', label: 'D: Incidents & PIR' },
                { id: 'sec-knowledge', label: 'E: Knowledge' },
                { id: 'sec-risks', label: 'F: Risk Flags' },
                { id: 'sec-handover', label: 'G: Handover Actions' },
              ].map((item) => (
                <button
                  key={item.id}
                  onClick={() => {
                    const el = document.getElementById(item.id);
                    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
                  }}
                  className="px-2.5 py-1 rounded-md border border-border bg-background/80 hover:bg-card hover:border-accent/40 text-muted-foreground hover:text-foreground text-[11px] whitespace-nowrap transition-colors"
                >
                  {item.label}
                </button>
              ))}
            </div>

            {/* Continuous Full Page Body (All sections rendered sequentially) */}
            <div className="flex-1 overflow-y-auto p-6 scroll-smooth">
              {isLoadingKtp ? (
                <div className="p-12 text-center text-xs font-mono text-muted-foreground">
                  Traversing institutional graph for {selectedPerson.full_name}...
                </div>
              ) : (
                <div className="max-w-5xl mx-auto space-y-8 pb-16">
                  {/* SECTION A: Person Profile */}
                  <section id="sec-profile" className="p-6 rounded-2xl bg-card border border-border space-y-4 shadow-xs scroll-mt-6">
                    <div className="flex items-center justify-between border-b border-border pb-3">
                      <div className="flex items-center gap-2.5">
                        <span className="px-2 py-0.5 rounded bg-accent/15 border border-accent/30 font-mono text-[10px] font-bold text-accent uppercase tracking-wider">
                          Section A
                        </span>
                        <h3 className="text-sm font-semibold text-foreground">
                          Person Profile & Organizational Hierarchy
                        </h3>
                      </div>
                      <span className="text-[11px] font-mono text-muted-foreground">Tier 1 • Structural</span>
                    </div>
                    <KtpProfileSection profile={ktpData?.section_a_profile || null} />
                  </section>

                  {/* SECTION B.1: Active Projects */}
                  <section id="sec-projects" className="p-6 rounded-2xl bg-card border border-border space-y-4 shadow-xs scroll-mt-6">
                    <div className="flex items-center justify-between border-b border-border pb-3">
                      <div className="flex items-center gap-2.5">
                        <span className="px-2 py-0.5 rounded bg-blue-500/15 border border-blue-500/30 font-mono text-[10px] font-bold text-blue-600 dark:text-blue-300 uppercase tracking-wider">
                          Section B.1
                        </span>
                        <h3 className="text-sm font-semibold text-foreground">
                          Active Projects & Critical Milestones ({ktpData?.section_b_ownership?.active_projects.length || 0})
                        </h3>
                      </div>
                      <span className="text-[11px] font-mono text-muted-foreground">Tier 2–3 • Operational</span>
                    </div>
                    <KtpProjectsSection ownership={ktpData?.section_b_ownership || null} />
                  </section>

                  {/* SECTION B.2: Active Tasks */}
                  <section id="sec-tasks" className="p-6 rounded-2xl bg-card border border-border space-y-4 shadow-xs scroll-mt-6">
                    <div className="flex items-center justify-between border-b border-border pb-3">
                      <div className="flex items-center gap-2.5">
                        <span className="px-2 py-0.5 rounded bg-blue-500/15 border border-blue-500/30 font-mono text-[10px] font-bold text-blue-600 dark:text-blue-300 uppercase tracking-wider">
                          Section B.2
                        </span>
                        <h3 className="text-sm font-semibold text-foreground">
                          Active Tasks & Commitments ({ktpData?.section_b_ownership?.active_tasks.length || 0})
                        </h3>
                      </div>
                      <span className="text-[11px] font-mono text-muted-foreground">Tier 2 • Operational</span>
                    </div>
                    <KtpTasksSection ownership={ktpData?.section_b_ownership || null} />
                  </section>

                  {/* SECTION C: Decision History */}
                  <section id="sec-decisions" className="p-6 rounded-2xl bg-card border border-border space-y-4 shadow-xs scroll-mt-6">
                    <div className="flex items-center justify-between border-b border-border pb-3">
                      <div className="flex items-center gap-2.5">
                        <span className="px-2 py-0.5 rounded bg-purple-500/15 border border-purple-500/30 font-mono text-[10px] font-bold text-purple-600 dark:text-purple-300 uppercase tracking-wider">
                          Section C
                        </span>
                        <h3 className="text-sm font-semibold text-foreground">
                          Decision History & Root Cause Analysis (RCA)
                        </h3>
                      </div>
                      <span className="text-[11px] font-mono text-muted-foreground">Tier 3 • Operational</span>
                    </div>
                    <KtpDecisionsSection decisions={ktpData?.section_c_decisions || null} />
                  </section>

                  {/* SECTION D: Incident Involvement */}
                  <section id="sec-incidents" className="p-6 rounded-2xl bg-card border border-border space-y-4 shadow-xs scroll-mt-6">
                    <div className="flex items-center justify-between border-b border-border pb-3">
                      <div className="flex items-center gap-2.5">
                        <span className="px-2 py-0.5 rounded bg-rose-500/15 border border-rose-500/30 font-mono text-[10px] font-bold text-rose-600 dark:text-rose-300 uppercase tracking-wider">
                          Section D
                        </span>
                        <h3 className="text-sm font-semibold text-foreground">
                          Incident Involvement & Post-Incident Reviews (PIR)
                        </h3>
                      </div>
                      <span className="text-[11px] font-mono text-muted-foreground">Tier 3 • Events</span>
                    </div>
                    <KtpIncidentsSection involvement={ktpData?.section_d_incidents || null} />
                  </section>

                  {/* SECTION E: Knowledge Authored */}
                  <section id="sec-knowledge" className="p-6 rounded-2xl bg-card border border-border space-y-4 shadow-xs scroll-mt-6">
                    <div className="flex items-center justify-between border-b border-border pb-3">
                      <div className="flex items-center gap-2.5">
                        <span className="px-2 py-0.5 rounded bg-indigo-500/15 border border-indigo-500/30 font-mono text-[10px] font-bold text-indigo-600 dark:text-indigo-300 uppercase tracking-wider">
                          Section E
                        </span>
                        <h3 className="text-sm font-semibold text-foreground">
                          Knowledge Authored & Institutional Lessons Learned
                        </h3>
                      </div>
                      <span className="text-[11px] font-mono text-muted-foreground">Tier 4 • Knowledge</span>
                    </div>
                    <KtpKnowledgeSection knowledge={ktpData?.section_e_knowledge || null} />
                  </section>

                  {/* SECTION F: Risk Flags */}
                  <section id="sec-risks" className="p-6 rounded-2xl bg-card border border-border space-y-4 shadow-xs scroll-mt-6">
                    <div className="flex items-center justify-between border-b border-border pb-3">
                      <div className="flex items-center gap-2.5">
                        <span className="px-2 py-0.5 rounded bg-amber-500/15 border border-amber-500/30 font-mono text-[10px] font-bold text-amber-600 dark:text-amber-300 uppercase tracking-wider">
                          Section F
                        </span>
                        <h3 className="text-sm font-semibold text-foreground">
                          Inference Risk Flags & Concentration Scores
                        </h3>
                      </div>
                      <span className="text-[11px] font-mono text-muted-foreground">IR-03 · IR-06</span>
                    </div>
                    <KtpRiskSection risks={ktpData?.section_f_risks || null} />
                  </section>

                  {/* SECTION G: Handover Recommendations */}
                  <section id="sec-handover" className="p-6 rounded-2xl bg-card border border-border space-y-4 shadow-xs scroll-mt-6">
                    <div className="flex items-center justify-between border-b border-border pb-3">
                      <div className="flex items-center gap-2.5">
                        <span className="px-2 py-0.5 rounded bg-emerald-500/15 border border-emerald-500/30 font-mono text-[10px] font-bold text-emerald-600 dark:text-emerald-300 uppercase tracking-wider">
                          Section G
                        </span>
                        <h3 className="text-sm font-semibold text-foreground">
                          Recommended Handover Actions & Top Successor Candidates
                        </h3>
                      </div>
                      <span className="text-[11px] font-mono text-muted-foreground">Graph Traversal Match</span>
                    </div>
                    <KtpHandoverSection
                      handover={ktpData?.section_g_handover || null}
                      onSelectSuccessor={(targetId) => {
                        setIsHandoverModalOpen(true);
                      }}
                    />
                  </section>
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center p-8 text-center text-muted-foreground text-xs font-mono">
            Select an individual from the directory to inspect their interconnected institutional subgraph.
          </div>
        )}
      </main>
    </div>
  );
}
