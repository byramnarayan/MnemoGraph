'use client';

import React from 'react';
import { IncidentForecastResult } from '../types';

interface ForecastOverviewProps {
  forecast?: IncidentForecastResult;
}

export function ForecastOverview({ forecast }: ForecastOverviewProps) {
  if (!forecast) return null;

  const p30 = forecast.horizons[1]?.incident_probability ?? 0.45;
  const p7 = forecast.horizons[0]?.incident_probability ?? 0.18;

  return (
    <section className="grid grid-cols-2 md:grid-cols-4 gap-3 font-mono">
      <div className="p-4 rounded-xl bg-card border border-border space-y-1">
        <span className="text-[10px] uppercase font-semibold text-muted-foreground">30-Day Incident Hazard</span>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-bold text-rose-400">{Math.round(p30 * 100)}%</span>
          <span className="text-[10px] text-muted-foreground">7d: {Math.round(p7 * 100)}%</span>
        </div>
      </div>

      <div className="p-4 rounded-xl bg-card border border-border space-y-1">
        <span className="text-[10px] uppercase font-semibold text-muted-foreground">LAnoBERT Log Anomaly</span>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-bold text-sky-400">{forecast.lanobert_anomaly_score.toFixed(2)}</span>
          <span className="text-[10px] text-muted-foreground">error_mean</span>
        </div>
      </div>

      <div className="p-4 rounded-xl bg-card border border-border space-y-1">
        <span className="text-[10px] uppercase font-semibold text-muted-foreground">Graph Centrality</span>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-bold text-purple-400">{forecast.graph_centrality_score.toFixed(2)}</span>
          <span className="text-[10px] text-muted-foreground">PageRank</span>
        </div>
      </div>

      <div className="p-4 rounded-xl bg-card border border-border space-y-1">
        <span className="text-[10px] uppercase font-semibold text-muted-foreground">Predicted Horizon</span>
        <div className="flex items-baseline gap-2">
          <span className="text-base font-bold text-amber-400 truncate">{forecast.predicted_interval_days}</span>
        </div>
      </div>
    </section>
  );
}

