'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { DecisionRiskSummary, DecisionDeepDiveNarrative } from './types';
import { incidentApi } from '@/lib/incident-api';
import { DecisionRiskList } from './components/DecisionRiskList';
import { DecisionNarrativeDeepDive } from './components/DecisionNarrativeDeepDive';
import { ActionProposalReportModal } from './components/ActionProposalReportModal';
import { ShieldAlert, RefreshCw } from 'lucide-react';

export default function IncidentIntelligencePage() {
  const [decisions, setDecisions] = useState<DecisionRiskSummary[]>([]);
  const [loadingList, setLoadingList] = useState(false);
  const [selectedDecision, setSelectedDecision] = useState<DecisionRiskSummary | null>(null);
  const [deepDiveData, setDeepDiveData] = useState<DecisionDeepDiveNarrative | null>(null);
  const [loadingDeepDive, setLoadingDeepDive] = useState(false);
  const [isReportModalOpen, setIsReportModalOpen] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const fetchDecisions = useCallback(async () => {
    setLoadingList(true);
    setErrorMsg(null);
    try {
      const data = await incidentApi.listUnlinkedDecisions();
      setDecisions(data);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load decisions list.');
    } finally {
      setLoadingList(false);
    }
  }, []);

  useEffect(() => {
    fetchDecisions();
  }, [fetchDecisions]);

  const handleSelectDecision = async (decision: DecisionRiskSummary) => {
    setSelectedDecision(decision);
    setLoadingDeepDive(true);
    setErrorMsg(null);
    try {
      const deepDive = await incidentApi.getDecisionDeepDive(decision.decision_id);
      setDeepDiveData(deepDive);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to generate deep dive narrative.');
    } finally {
      setLoadingDeepDive(false);
    }
  };

  const handleBack = () => {
    setSelectedDecision(null);
    setDeepDiveData(null);
  };

  const handleDraftSaved = (savedDraft: any) => {
    setToastMessage(`Draft proposal '${savedDraft.title}' saved to PostgreSQL successfully!`);
    setTimeout(() => setToastMessage(null), 5000);
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 p-6 sm:p-10 font-sans">
      <div className="max-w-5xl mx-auto space-y-6">
        {/* App Title Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-zinc-800">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
              <ShieldAlert className="w-5 h-5 text-indigo-400" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-zinc-100">
                Predictive Incident & Decision Intelligence
              </h1>
              <p className="text-xs text-zinc-400">
                Decision-centric risk scoring, multi-store narrative timelines, and preventive action drafts
              </p>
            </div>
          </div>

          <button
            onClick={fetchDecisions}
            disabled={loadingList}
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium bg-zinc-900 border border-zinc-700 text-zinc-300 hover:text-zinc-100 hover:bg-zinc-800 transition-colors self-start sm:self-auto"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loadingList ? 'animate-spin' : ''}`} />
            Refresh Data
          </button>
        </div>

        {/* Global Notifications */}
        {toastMessage && (
          <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs flex items-center justify-between animate-fade-in">
            <span>{toastMessage}</span>
            <button onClick={() => setToastMessage(null)} className="text-zinc-400 hover:text-zinc-200">✕</button>
          </div>
        )}

        {errorMsg && (
          <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center justify-between">
            <span>{errorMsg}</span>
            <button onClick={() => setErrorMsg(null)} className="text-zinc-400 hover:text-zinc-200">✕</button>
          </div>
        )}

        {/* Dynamic View: Decision List or Narrative Deep-Dive */}
        {!selectedDecision ? (
          <DecisionRiskList
            decisions={decisions}
            loading={loadingList}
            selectedId={null}
            onSelectDecision={handleSelectDecision}
          />
        ) : (
          deepDiveData && (
            <DecisionNarrativeDeepDive
              data={deepDiveData}
              loading={loadingDeepDive}
              onBack={handleBack}
              onOpenReportModal={() => setIsReportModalOpen(true)}
            />
          )
        )}

        {/* Action Proposal Report Modal */}
        {deepDiveData && (
          <ActionProposalReportModal
            isOpen={isReportModalOpen}
            onClose={() => setIsReportModalOpen(false)}
            deepDive={deepDiveData}
            onDraftSaved={handleDraftSaved}
          />
        )}
      </div>
    </div>
  );
}
