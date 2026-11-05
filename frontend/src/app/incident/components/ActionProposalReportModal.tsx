'use client';

import React, { useState } from 'react';
import { DecisionDeepDiveNarrative } from '../types';
import { incidentApi } from '@/lib/incident-api';
import { X, Check, Save, FileCheck, AlertCircle, Loader2 } from 'lucide-react';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  deepDive: DecisionDeepDiveNarrative;
  onDraftSaved?: (savedDraft: any) => void;
}

export function ActionProposalReportModal({
  isOpen,
  onClose,
  deepDive,
  onDraftSaved,
}: Props) {
  const [title, setTitle] = useState(deepDive.recommended_action.action_title);
  const [suggestedRole, setSuggestedRole] = useState(deepDive.recommended_action.suggested_role);
  const [priority, setPriority] = useState(deepDive.recommended_action.priority || 'Critical');
  const [steps, setSteps] = useState(deepDive.recommended_action.implementation_steps.join('\n'));
  const [criteria, setCriteria] = useState(deepDive.recommended_action.verification_criteria);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSaveDraft = async () => {
    setSaving(true);
    setErrorMsg(null);
    try {
      const payload = {
        decision_id: deepDive.decision_id,
        decision_title: deepDive.decision_title,
        affected_scope: deepDive.recommended_action.action_title.split('on ')[1] || 'Core Network System',
        incident_probability: deepDive.incident_probability,
        executive_scenario: deepDive.executive_scenario,
        recommended_action: {
          action_title: title,
          suggested_role: suggestedRole,
          priority: priority,
          implementation_steps: steps.split('\n').filter((s) => s.trim().length > 0),
          verification_criteria: criteria,
        },
        evidence_citations: deepDive.evidence_citations,
      };

      const res = await incidentApi.generateDecisionActionReport(deepDive.decision_id, payload);
      setSuccess(true);
      if (onDraftSaved) onDraftSaved(res);
      setTimeout(() => {
        onClose();
        setSuccess(false);
      }, 1500);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to save action proposal draft');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-2xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800 bg-zinc-900/50">
          <div className="flex items-center gap-2">
            <FileCheck className="w-5 h-5 text-indigo-400" />
            <h2 className="text-base font-semibold text-zinc-100">Create Action Proposal Report Draft</h2>
          </div>
          <button onClick={onClose} className="p-1 rounded text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <div className="p-6 overflow-y-auto space-y-4 text-xs text-zinc-300">
          {errorMsg && (
            <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          <div className="space-y-1.5">
            <label className="font-semibold text-zinc-200">Proposal Title</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full bg-zinc-950 border border-zinc-700 rounded-lg px-3 py-2 text-zinc-100 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="font-semibold text-zinc-200">Suggested Role / Owner</label>
              <input
                type="text"
                value={suggestedRole}
                onChange={(e) => setSuggestedRole(e.target.value)}
                className="w-full bg-zinc-950 border border-zinc-700 rounded-lg px-3 py-2 text-zinc-100 focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div className="space-y-1.5">
              <label className="font-semibold text-zinc-200">Priority Tier</label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
                className="w-full bg-zinc-950 border border-zinc-700 rounded-lg px-3 py-2 text-zinc-100 focus:outline-none focus:border-indigo-500"
              >
                <option value="Critical">Critical</option>
                <option value="High">High</option>
                <option value="Medium">Medium</option>
                <option value="Low">Low</option>
              </select>
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="font-semibold text-zinc-200">Implementation Steps (One per line)</label>
            <textarea
              rows={4}
              value={steps}
              onChange={(e) => setSteps(e.target.value)}
              className="w-full bg-zinc-950 border border-zinc-700 rounded-lg p-3 text-zinc-100 font-mono text-xs focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="space-y-1.5">
            <label className="font-semibold text-zinc-200">Verification & Success Criteria</label>
            <input
              type="text"
              value={criteria}
              onChange={(e) => setCriteria(e.target.value)}
              className="w-full bg-zinc-950 border border-zinc-700 rounded-lg px-3 py-2 text-zinc-100 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="bg-zinc-950/80 p-3 rounded-lg border border-zinc-800 text-[11px] text-zinc-400">
            <p className="font-semibold text-zinc-300 mb-1">Architectural Invariant Guarantee:</p>
            <p>Draft will be stored in PostgreSQL <code className="text-indigo-400">action_proposal_drafts</code>. Canonical FalkorDB Knowledge Graph remains strictly read-only.</p>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-zinc-800 bg-zinc-900/50">
          <button onClick={onClose} className="px-4 py-2 rounded-lg text-xs font-medium text-zinc-400 hover:text-zinc-200">
            Cancel
          </button>
          <button
            onClick={handleSaveDraft}
            disabled={saving || success}
            className={`inline-flex items-center gap-1.5 px-5 py-2 rounded-lg text-xs font-semibold text-white transition-all ${
              success
                ? 'bg-emerald-600'
                : 'bg-indigo-600 hover:bg-indigo-500'
            }`}
          >
            {saving ? (
              <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Saving Draft...</>
            ) : success ? (
              <><Check className="w-3.5 h-3.5" /> Draft Saved in PostgreSQL</>
            ) : (
              <><Save className="w-3.5 h-3.5" /> Save Prevention Draft</>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

