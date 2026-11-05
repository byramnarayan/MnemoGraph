'use client';

import React from 'react';
import { DecisionRiskSummary } from '../types';
import { AlertTriangle, Clock, User, Server, CheckCircle2, ChevronRight, Activity } from 'lucide-react';

interface Props {
  decisions: DecisionRiskSummary[];
  loading: boolean;
  selectedId?: string | null;
  onSelectDecision: (decision: DecisionRiskSummary) => void;
}

export function DecisionRiskList({
  decisions,
  loading,
  selectedId,
  onSelectDecision,
}: Props) {
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 space-y-4">
        <div className="w-10 h-10 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        <p className="text-sm text-zinc-400">Evaluating institutional decisions and graph risk topology...</p>
      </div>
    );
  }

  if (decisions.length === 0) {
    return (
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-8 text-center">
        <CheckCircle2 className="w-10 h-10 text-emerald-400 mx-auto mb-3" />
        <h3 className="text-base font-semibold text-zinc-200">No High-Risk Unmitigated Decisions</h3>
        <p className="text-sm text-zinc-400 mt-1">All recorded decisions have completed tasks or linked mitigations.</p>
      </div>
    );
  }

  const getTierBadge = (tier: string, prob: number) => {
    const pct = Math.round(prob * 100);
    if (tier === 'CRITICAL' || prob >= 0.7) {
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/30">
          <AlertTriangle className="w-3.5 h-3.5 text-rose-400 animate-pulse" />
          {pct}% Critical Risk
        </span>
      );
    }
    if (tier === 'ELEVATED' || prob >= 0.45) {
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30">
          <Clock className="w-3.5 h-3.5 text-amber-400" />
          {pct}% Elevated Risk
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/30">
        <CheckCircle2 className="w-3.5 h-3.5 text-blue-400" />
        {pct}% Moderate Risk
      </span>
    );
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between pb-2 border-b border-zinc-800">
        <div>
          <h2 className="text-lg font-semibold text-zinc-100">Institutional Decisions Without Incidents</h2>
          <p className="text-xs text-zinc-400 mt-0.5">
            Calibrated hazard probability evaluated from FalkorDB graph algorithms, LAnoBERT telemetry anomalies, and action completion state.
          </p>
        </div>
        <span className="text-xs px-2.5 py-1 rounded bg-zinc-800 text-zinc-400 border border-zinc-700">
          {decisions.length} Decisions Monitored
        </span>
      </div>

      <div className="grid grid-cols-1 gap-3.5">
        {decisions.map((dec) => {
          const isSelected = selectedId === dec.decision_id;
          return (
            <div
              key={dec.decision_id}
              onClick={() => onSelectDecision(dec)}
              className={`group cursor-pointer rounded-xl p-4 transition-all duration-200 border ${
                isSelected
                  ? 'bg-zinc-800/80 border-indigo-500/60 shadow-lg shadow-indigo-500/10 ring-1 ring-indigo-500/40'
                  : 'bg-zinc-900/60 border-zinc-800 hover:border-zinc-700 hover:bg-zinc-800/40'
              }`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 space-y-2">
                  <div className="flex items-center gap-3">
                    <h3 className="text-sm font-semibold text-zinc-100 group-hover:text-indigo-300 transition-colors">
                      {dec.decision_title}
                    </h3>
                    {getTierBadge(dec.risk_tier, dec.incident_probability)}
                  </div>

                  <div className="flex flex-wrap items-center gap-y-1.5 gap-x-4 text-xs text-zinc-400">
                    <span className="inline-flex items-center gap-1.5 text-zinc-300">
                      <User className="w-3.5 h-3.5 text-zinc-500" />
                      {dec.decision_maker || 'Institutional Architect'}
                    </span>
                    <span className="inline-flex items-center gap-1.5 text-zinc-300">
                      <Server className="w-3.5 h-3.5 text-zinc-500" />
                      {dec.affected_systems.join(', ') || 'Core Network'}
                    </span>
                    <span className="inline-flex items-center gap-1.5 text-zinc-400">
                      <Activity className="w-3.5 h-3.5 text-emerald-500" />
                      LAnoBERT error_mean: {dec.lanobert_score.toFixed(2)}
                    </span>
                    <span className="inline-flex items-center gap-1.5 text-zinc-400">
                      <Clock className="w-3.5 h-3.5 text-zinc-500" />
                      Window: {dec.predicted_horizon_days}
                    </span>
                    {dec.unimplemented_action_count > 0 && (
                      <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-amber-500/10 text-amber-300 border border-amber-500/20">
                        {dec.unimplemented_action_count} uncompleted follow-up task(s)
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex items-center self-center text-zinc-500 group-hover:text-zinc-300 pl-2">
                  <ChevronRight className="w-5 h-5 transition-transform group-hover:translate-x-0.5" />
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

