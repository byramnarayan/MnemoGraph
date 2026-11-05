'use client';

import React, { useState } from 'react';
import { PredictiveScenario } from '../types';
import { getToken } from '@/lib/api-client';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

interface ActionProposalModalProps {
  scenario: PredictiveScenario | null;
  isOpen: boolean;
  onClose: () => void;
  onSaved: (proposal: any) => void;
}

export function ActionProposalModal({
  scenario,
  isOpen,
  onClose,
  onSaved,
}: ActionProposalModalProps) {
  if (!isOpen || !scenario) return null;

  const [title, setTitle] = useState(scenario.recommended_action.action_title);
  const [priority, setPriority] = useState(scenario.recommended_action.priority || 'High');
  const [role, setRole] = useState(scenario.recommended_action.suggested_role || 'Lead Systems Engineer');
  const [stepsText, setStepsText] = useState(scenario.recommended_action.implementation_steps.join('\n'));
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setErrorMsg(null);

    const steps = stepsText.split('\n').map((s) => s.trim()).filter(Boolean);
    const payload = {
      scenario_data: {
        ...scenario,
        recommended_action: {
          ...scenario.recommended_action,
          action_title: title,
          priority,
          suggested_role: role,
          implementation_steps: steps,
        },
      },
    };

    try {
      const token = getToken();
      const res = await fetch(`${API_BASE}/proposals/generate-draft`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to save action proposal draft.');
      }

      const created = await res.json();
      onSaved(created);
      onClose();
    } catch (err: any) {
      setErrorMsg(err.message || 'Error saving proposal draft.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-xs font-mono text-xs">
      <div className="w-full max-w-xl bg-card border border-border rounded-2xl p-6 shadow-2xl space-y-4 animate-in fade-in zoom-in-95 duration-150">
        <div className="flex items-center justify-between border-b border-border pb-3">
          <div>
            <span className="text-[10px] text-accent font-semibold tracking-wider uppercase">Relational Action Proposal</span>
            <h3 className="font-bold text-sm text-foreground">{scenario.scenario_title}</h3>
          </div>
          <button onClick={onClose} className="w-6 h-6 rounded-md hover:bg-muted text-muted-foreground flex items-center justify-center">✕</button>
        </div>

        {errorMsg && (
          <div className="p-2.5 rounded-lg bg-rose-500/15 border border-rose-500/30 text-rose-500 text-xs">
            {errorMsg}
          </div>
        )}

        <form onSubmit={handleSave} className="space-y-3">
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
              <label className="block text-[10px] uppercase text-muted-foreground mb-1">Suggested Role / Owner</label>
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
            <label className="block text-[10px] uppercase text-muted-foreground mb-1">Implementation Steps (One per line)</label>
            <textarea
              rows={4}
              value={stepsText}
              onChange={(e) => setStepsText(e.target.value)}
              className="w-full bg-background border border-border rounded-lg p-2.5 text-xs text-foreground font-mono focus:outline-none focus:border-accent leading-relaxed"
            />
          </div>

          <div className="p-2.5 rounded-lg bg-muted/40 border border-border/50 text-[11px] text-muted-foreground">
            <span className="font-semibold text-foreground">Verified Precedent:</span> {scenario.historical_precedent?.incident_title || 'Core network interface precedent'} ({scenario.historical_precedent?.action_effectiveness || 'EFFECTIVE'})
          </div>

          <div className="pt-2 border-t border-border flex items-center justify-end gap-2">
            <button type="button" onClick={onClose} disabled={isSubmitting} className="px-3 py-1.5 rounded-lg border border-border hover:bg-muted text-xs text-muted-foreground">
              Cancel
            </button>
            <button type="submit" disabled={isSubmitting} className="px-4 py-1.5 rounded-lg bg-accent text-accent-foreground font-semibold text-xs hover:opacity-90 disabled:opacity-50">
              {isSubmitting ? 'Saving Draft...' : 'Save Draft to Relational Ledger'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

