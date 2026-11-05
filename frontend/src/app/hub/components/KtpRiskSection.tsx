'use client';

import React from 'react';
import { SectionFRiskFlags } from '../types';

interface KtpRiskSectionProps {
  risks: SectionFRiskFlags | null;
}

export function KtpRiskSection({ risks }: KtpRiskSectionProps) {
  if (!risks) return null;

  return (
    <div className="space-y-6">
      {/* Concentration Risk Score Banner */}
      <div className="p-4 rounded-xl bg-card border border-border flex items-center justify-between shadow-xs">
        <div>
          <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-foreground">
            IR-03 Concentration Risk Score
          </h4>
          <p className="text-xs text-muted-foreground mt-0.5">
            Institutional dependency metric measuring knowledge silo concentration.
          </p>
        </div>
        <div className="text-right">
          <span
            className={`text-2xl font-mono font-bold ${
              risks.concentration_risk_score > 0.5 ? 'text-rose-600 dark:text-rose-400' : 'text-emerald-600 dark:text-emerald-400'
            }`}
          >
            {risks.concentration_risk_score.toFixed(2)}
          </span>
          <div className="text-[10px] font-mono text-muted-foreground font-semibold">
            {risks.concentration_risk_score > 0.5 ? 'HIGH RISK' : 'NORMAL'}
          </div>
        </div>
      </div>

      {/* Recurrence Risk Tasks */}
      {risks.recurrence_risk_tasks.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-rose-600 dark:text-rose-400">
            IR-06 Recurrence Risk Flags ({risks.recurrence_risk_tasks.length})
          </h4>
          <div className="space-y-1.5">
            {risks.recurrence_risk_tasks.map((task: any, idx: number) => (
              <div
                key={idx}
                className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-xs flex items-center justify-between"
              >
                <span className="font-medium text-foreground">{task.title}</span>
                <span className="text-[10px] font-mono text-rose-600 dark:text-rose-400 font-semibold">Repeated Failure Path</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Overdue Tasks */}
      {risks.overdue_tasks.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-amber-600 dark:text-amber-400">
            Open Overdue Tasks ({risks.overdue_tasks.length})
          </h4>
          <div className="space-y-1.5">
            {risks.overdue_tasks.map((task: any, idx: number) => (
              <div
                key={idx}
                className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-xs flex items-center justify-between"
              >
                <span className="font-medium text-foreground">{task.title}</span>
                <span className="text-[10px] font-mono text-amber-600 dark:text-amber-400 font-semibold">
                  Due: {task.due_date || 'Past Due'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Documentation Gaps */}
      {risks.documentation_gaps.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-muted-foreground">
            Institutional Documentation Gaps ({risks.documentation_gaps.length})
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {risks.documentation_gaps.map((gap) => (
              <div
                key={gap.id}
                className="p-2.5 rounded-lg bg-card/60 border border-border text-xs"
              >
                <div className="font-medium text-foreground">{gap.title}</div>
                <div className="text-[10px] font-mono text-muted-foreground">
                  Labels: {gap.labels.join(', ')}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

