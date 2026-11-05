'use client';

import React, { useState } from 'react';
import { UKGOEAnswerData, PredictiveScenario } from '../types';
import { ActionProposalModal } from './ActionProposalModal';

interface PredictiveIntelligenceViewProps {
  data: UKGOEAnswerData;
}

export function PredictiveIntelligenceView({ data }: PredictiveIntelligenceViewProps) {
  const [selectedScenario, setSelectedScenario] = useState<PredictiveScenario | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [savedSuccessMsg, setSavedSuccessMsg] = useState<string | null>(null);

  const forecast = data.forecast_result;
  const scenarios = data.predictive_scenarios || [];
  const decisions = data.decision_summaries || [];
  const timeline = data.timeline_events || [];

  const handleOpenProposal = (scen: PredictiveScenario) => {
    setSelectedScenario(scen);
    setIsModalOpen(true);
  };

  return (
    <div className="space-y-4 font-mono text-xs">
      {savedSuccessMsg && (
        <div className="p-2.5 rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 text-xs flex items-center justify-between">
          <span>{savedSuccessMsg}</span>
          <button onClick={() => setSavedSuccessMsg(null)} className="text-muted-foreground hover:text-foreground">✕</button>
        </div>
      )}

      {/* 1. Forecast Metric Overview Badges */}
      {forecast && (
        <div className="p-3 bg-muted/30 border border-border rounded-xl space-y-2">
          <div className="flex items-center justify-between text-[11px]">
            <span className="text-muted-foreground uppercase font-semibold">Temporal Hazard Forecast</span>
            <span className="px-1.5 py-0.5 rounded text-[10px] bg-accent/20 text-accent font-semibold">
              {forecast.predicted_interval_days}
            </span>
          </div>
          <div className="grid grid-cols-3 gap-2 pt-1 text-center">
            <div className="p-2 rounded-lg bg-background border border-border">
              <span className="block text-[10px] text-muted-foreground">30d Probability</span>
              <span className="text-sm font-bold text-rose-400">
                {forecast.horizons[1] ? `${int(forecast.horizons[1].incident_probability * 100)}%` : '45%'}
              </span>
            </div>
            <div className="p-2 rounded-lg bg-background border border-border">
              <span className="block text-[10px] text-muted-foreground">LAnoBERT Anomaly</span>
              <span className="text-sm font-bold text-sky-400">{forecast.lanobert_anomaly_score.toFixed(2)}</span>
            </div>
            <div className="p-2 rounded-lg bg-background border border-border">
              <span className="block text-[10px] text-muted-foreground">Graph Centrality</span>
              <span className="text-sm font-bold text-purple-400">{forecast.graph_centrality_score.toFixed(2)}</span>
            </div>
          </div>
        </div>
      )}

      {/* 2. Plausible Scenario Cards & Proposal Button */}
      {scenarios.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-[11px] uppercase font-bold text-foreground tracking-wider">Identified Risk Scenarios</h4>
          {scenarios.map((scen) => (
            <div key={scen.scenario_id} className="p-3.5 rounded-xl border border-border bg-card/80 space-y-2.5">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <span className="text-[10px] text-accent font-semibold uppercase">{scen.affected_scope}</span>
                  <h5 className="font-bold text-foreground text-xs leading-snug">{scen.scenario_title}</h5>
                </div>
                <span className="px-2 py-0.5 text-[10px] rounded font-semibold bg-rose-500/15 border border-rose-500/30 text-rose-400 shrink-0">
                  {int(scen.forecast_probability * 100)}% Risk
                </span>
              </div>
              <p className="text-[11px] text-muted-foreground leading-relaxed">{scen.recommended_action.rationale}</p>
              <div className="pt-2 border-t border-border flex items-center justify-between">
                <span className="text-[10px] text-muted-foreground">Precedent: {scen.historical_precedent?.action_effectiveness || 'EFFECTIVE'}</span>
                <button
                  onClick={() => handleOpenProposal(scen)}
                  className="px-2.5 py-1 rounded-md bg-accent text-accent-foreground font-semibold text-[10px] hover:opacity-90 flex items-center gap-1.5 shadow-sm"
                >
                  <span>📋</span> Create Action Proposal
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 3. Recent Decisions with Observation Status Table */}
      {decisions.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-[11px] uppercase font-bold text-foreground tracking-wider">Recent Decisions Follow-up</h4>
          <div className="border border-border rounded-xl overflow-hidden text-[10px]">
            <div className="grid grid-cols-12 bg-muted/50 p-2 font-semibold text-muted-foreground border-b border-border">
              <span className="col-span-6">Decision</span>
              <span className="col-span-3">Days</span>
              <span className="col-span-3 text-right">Status</span>
            </div>
            <div className="divide-y divide-border/60 max-h-36 overflow-y-auto">
              {decisions.slice(0, 6).map((d) => (
                <div key={d.decision_id} className="grid grid-cols-12 p-2 items-center hover:bg-muted/20">
                  <span className="col-span-6 truncate text-foreground font-medium">{d.decision_title}</span>
                  <span className="col-span-3 text-muted-foreground">{d.follow_up_days}d</span>
                  <span className={`col-span-3 text-right font-semibold truncate ${d.follow_up_status.includes('NO_LINKED') ? 'text-emerald-400' : 'text-amber-400'}`}>
                    {d.follow_up_status.replace(/_/g, ' ')}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* 4. Chronological Timeline List */}
      {timeline.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-[11px] uppercase font-bold text-foreground tracking-wider">Institutional Event Lineage</h4>
          <div className="space-y-1.5 max-h-40 overflow-y-auto pr-1">
            {timeline.slice(0, 6).map((ev) => (
              <div key={ev.event_id} className="flex items-center justify-between p-2 rounded-lg bg-muted/20 border border-border/60 text-[10px]">
                <div className="flex items-center gap-2 truncate">
                  <span className="w-1.5 h-1.5 rounded-full bg-accent shrink-0" />
                  <span className="font-semibold text-foreground truncate">{ev.entity_name}</span>
                </div>
                <span className="text-muted-foreground shrink-0 text-[9px]">{ev.event_type.replace(/_/g, ' ')}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <ActionProposalModal
        scenario={selectedScenario}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSaved={(prop) => setSavedSuccessMsg(`Action Proposal '${prop.title}' saved to relational ledger!`)}
      />
    </div>
  );
}

function int(val: number): number {
  return Math.round(val);
}

