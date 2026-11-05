'use client';

import React, { useState } from 'react';
import { KtpPersonSummary, SuccessorCandidate } from '../types';

interface KtpHandoverModalProps {
  isOpen: boolean;
  onClose: () => void;
  sourcePerson: KtpPersonSummary;
  candidates: SuccessorCandidate[];
  onAssignHandover: (targetPersonId: string, notes?: string) => Promise<void>;
}

export function KtpHandoverModal({
  isOpen,
  onClose,
  sourcePerson,
  candidates,
  onAssignHandover,
}: KtpHandoverModalProps) {
  const [selectedTargetId, setSelectedTargetId] = useState('');
  const [notes, setNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTargetId) {
      setErrorMsg('Please select or specify a target successor.');
      return;
    }

    try {
      setIsSubmitting(true);
      setErrorMsg(null);
      await onAssignHandover(selectedTargetId, notes);
      onClose();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to assign handover.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm">
      <div className="bg-card border border-border rounded-2xl w-full max-w-lg p-6 shadow-2xl space-y-5">
        <div className="flex items-center justify-between border-b border-border pb-3">
          <h3 className="text-base font-semibold text-foreground font-mono">
            Assign Knowledge Handover
          </h3>
          <button
            onClick={onClose}
            className="text-muted-foreground hover:text-foreground text-lg leading-none"
          >
            ×
          </button>
        </div>

        <p className="text-xs text-muted-foreground leading-relaxed">
          Transfer institutional subgraph and access rights for{' '}
          <strong className="text-foreground">{sourcePerson.full_name}</strong> to a designated successor. The recipient will gain direct access to this handover in their Hub.
        </p>

        {errorMsg && (
          <div className="p-3 text-xs rounded-lg bg-rose-500/15 border border-rose-500/30 text-rose-600 dark:text-rose-300">
            {errorMsg}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Candidate suggestions from Section G */}
          {candidates.length > 0 && (
            <div className="space-y-1.5">
              <label className="text-xs font-mono text-muted-foreground">
                Recommended Successors (Top Skill Overlap)
              </label>
              <div className="grid grid-cols-1 gap-1.5 max-h-36 overflow-y-auto pr-1">
                {candidates.map((c) => (
                  <button
                    type="button"
                    key={c.person_id}
                    onClick={() => setSelectedTargetId(c.person_id)}
                    className={`flex items-center justify-between p-2 rounded-lg text-left text-xs border transition-colors ${
                      selectedTargetId === c.person_id
                        ? 'bg-accent/20 border-accent text-accent font-medium'
                        : 'bg-background border-border text-foreground hover:border-accent/40'
                    }`}
                  >
                    <div>
                      <div className="font-medium text-foreground">{c.full_name}</div>
                      <div className="text-[11px] text-muted-foreground">
                        {c.role || 'Member'} • {c.shared_skills.slice(0, 3).join(', ')}
                      </div>
                    </div>
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-muted border border-border text-muted-foreground">
                      {c.skill_overlap_count} skills match
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Manual ID Input */}
          <div className="space-y-1">
            <label className="text-xs font-mono text-muted-foreground">
              Successor Person ID
            </label>
            <input
              type="text"
              required
              placeholder="e.g. person:dev-49a02f"
              value={selectedTargetId}
              onChange={(e) => setSelectedTargetId(e.target.value)}
              className="w-full bg-background border border-border rounded-lg px-3 py-2 text-xs text-foreground font-mono placeholder-muted-foreground focus:outline-none focus:border-accent"
            />
          </div>

          {/* Handover Notes */}
          <div className="space-y-1">
            <label className="text-xs font-mono text-muted-foreground">
              Transfer Notes & Directives (Optional)
            </label>
            <textarea
              rows={3}
              placeholder="Provide directives, priority project milestones, or context for the successor..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full bg-background border border-border rounded-lg px-3 py-2 text-xs text-foreground placeholder-muted-foreground focus:outline-none focus:border-accent"
            />
          </div>

          <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
            <button
              type="button"
              onClick={onClose}
              className="px-3.5 py-2 text-xs text-muted-foreground hover:text-foreground font-mono transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !selectedTargetId}
              className="px-4 py-2 text-xs font-medium rounded-lg bg-accent hover:opacity-90 disabled:opacity-50 text-accent-foreground font-mono transition-colors"
            >
              {isSubmitting ? 'Assigning...' : 'Confirm Handover'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

