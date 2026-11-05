'use client';

import React, { useState } from 'react';
import { PredictiveScenario } from '../types';
import { incidentApi } from '@/lib/incident-api';

interface ActionProposalModalProps {
  scenario: PredictiveScenario | null;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (proposal: any) => void;
}

export function ActionProposalModal({
  scenario,
  isOpen,
  onClose,
  onSuccess,
}: ActionProposalModalProps) {
  if (!isOpen || !scenario) return null;

  const [title, setTitle] = useState(scenario.recommended_action.action_title);
  const [priority, setPriority] = useState(scenario.recommended_action.priority || 'High');
  const [role, setRole] = useState(scenario.recommended_action.suggested_role || 'Lead Systems Engineer');
  const [stepsText, setStepsText] = useState(scenario.recommended_action.implementation_steps.join('\n'));
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setErrorMsg(null);

    const steps = stepsText.split('\n').map((s) => s.trim()).filter(Boolean);
    const scenarioPayload = {
      ...scenario,
      recommended_action: {
        ...scenario.recommended_action,
        action_title: title,
        priority,
        suggested_role: role,
        implementation_steps: steps,
      },
    };

    try {
      const created = await incidentApi.generateActionProposal(scenarioPayload);
      onSuccess(created);
      onClose();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to save action proposal.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-xs font-mono text-xs">
      <div className="w-full max-w-lg bg-card border border-border rounded-2xl p-6 shadow-2xl space-y-4 animate-in fade-in zoom-in-95 duration-150">
        <div className="flex items-center justify-between border-b border-border pb-3">
          <div>
            <span className="text-[10px] text-accent font-semibold tracking-wider uppercase">Institutional Proposal</span>
            <h3 className="font-bold text-sm text-foreground">{scenario.scenario_title}</h3>
          </div>
          <button onClick={onClose} className="w-6 h-6 rounded-md hover:bg-muted text-muted-foreground flex items-center justify-center">✕</button>
        </div>

        {errorMsg && (
          <div className="p-2.5 rounded-lg bg-rose-500/15 border border-rose-500/30 text-rose-500 text-xs">
            {errorMsg}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="block text-[10px] uppercase text-muted-foreground mb-1">Proposal Title</label>
            <input
              type="text"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full bg-background border border-border rounded-lg px-3 py-1.5 text-xs text-foreground focus:outline-none focus:border-accent"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[10px] uppercase text-muted-foreground mb-1">Responsible Role</label>
              <input
                type="text"
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="w-full bg-background border border-border rounded-lg px-3 py-1.5 text-xs text-foreground focus:outline-none focus:border-accent"
              />
            </div>
            <div>
              <label className="block text-[10px] uppercase text-muted-foreground mb-1">Priority</label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
                className="w-full bg-background border border-border rounded-lg px-3 py-1.5 text-xs text-foreground focus:outline-none focus:border-accent"
              >
                <option value="Critical">Critical</option>
                <option value="High">High</option>
                <option value="Medium">Medium</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-[10px] uppercase text-muted-foreground mb-1">Implementation Steps</label>
            <textarea
              rows={4}
              value={stepsText}
              onChange={(e) => setStepsText(e.target.value)}
              className="w-full bg-background border border-border rounded-lg p-2.5 text-xs text-foreground font-mono focus:outline-none focus:border-accent"
            />
          </div>

          <div className="pt-2 border-t border-border flex items-center justify-end gap-2">
            <button type="button" onClick={onClose} disabled={isSubmitting} className="px-3 py-1.5 rounded-lg border border-border hover:bg-muted text-xs text-muted-foreground">
              Cancel
            </button>
            <button type="submit" disabled={isSubmitting} className="px-4 py-1.5 rounded-lg bg-accent text-accent-foreground font-semibold text-xs hover:opacity-90 disabled:opacity-50">
              {isSubmitting ? 'Saving Draft...' : 'Save Draft to PostgreSQL'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

