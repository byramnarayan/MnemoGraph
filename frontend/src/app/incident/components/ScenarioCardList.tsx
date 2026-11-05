'use client';

import React from 'react';
import { PredictiveScenario } from '../types';

interface ScenarioCardListProps {
  scenarios: PredictiveScenario[];
  onSelectScenario: (scenario: PredictiveScenario) => void;
}

export function ScenarioCardList({ scenarios, onSelectScenario }: ScenarioCardListProps) {
  if (!scenarios || scenarios.length === 0) return null;

  return (
    <section className="space-y-3 font-mono">
      <div className="flex items-center justify-between">
        <h2 className="text-xs font-bold uppercase tracking-wider text-foreground">
          Plausible Operational Scenarios ({scenarios.length})
        </h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {scenarios.map((scen) => (
          <div
            key={scen.scenario_id}
            className="p-4 rounded-xl border border-border bg-card flex flex-col justify-between space-y-3"
          >
            <div className="space-y-2">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <span className="text-[10px] text-accent uppercase font-bold">{scen.affected_scope}</span>
                  <h3 className="font-bold text-xs text-foreground leading-snug">{scen.scenario_title}</h3>
                </div>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/15 border border-rose-500/30 text-rose-400 shrink-0">
                  {Math.round(scen.forecast_probability * 100)}% Risk
                </span>
              </div>

              <p className="text-[11px] text-muted-foreground leading-relaxed">
                {scen.recommended_action.rationale}
              </p>

              <div className="space-y-1 pt-1 text-[10px] text-muted-foreground">
                {scen.contributing_factors.map((f, i) => (
                  <div key={i} className="flex items-center gap-1.5">
                    <span className="w-1 h-1 rounded-full bg-accent" />
                    <span>{f}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="pt-3 border-t border-border flex items-center justify-between">
              <span className="text-[10px] text-muted-foreground">
                Precedent: {scen.historical_precedent?.action_effectiveness || 'EFFECTIVE'}
              </span>
              <button
                onClick={() => onSelectScenario(scen)}
                className="px-3 py-1.5 rounded-lg bg-accent text-accent-foreground font-semibold text-[10px] hover:opacity-90 flex items-center gap-1.5 shadow-sm"
              >
                <span>📋</span> Create Action Proposal
              </button>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

