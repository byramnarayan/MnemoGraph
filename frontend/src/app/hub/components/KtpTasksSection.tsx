'use client';

import React from 'react';
import { SectionBActiveOwnership } from '../types';

interface KtpTasksSectionProps {
  ownership: SectionBActiveOwnership | null;
}

export function KtpTasksSection({ ownership }: KtpTasksSectionProps) {
  const tasks = ownership?.active_tasks || [];

  if (tasks.length === 0) {
    return (
      <div className="p-6 text-center text-xs text-muted-foreground font-mono bg-card/30 rounded-xl border border-border">
        No active tasks assigned to this individual.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {tasks.map((task) => (
        <div
          key={task.task_id}
          className="p-4 rounded-xl bg-card border border-border text-xs flex flex-col md:flex-row md:items-center justify-between gap-3 shadow-xs"
        >
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <h5 className="font-medium text-foreground">{task.title}</h5>
              <span
                className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded border ${
                  task.status === 'overdue'
                    ? 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/30'
                    : 'bg-amber-500/10 text-amber-600 dark:text-amber-300 border-amber-500/30'
                }`}
              >
                {task.status}
              </span>
              {task.effectiveness_label && (
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-muted text-muted-foreground border border-border">
                  {task.effectiveness_label}
                </span>
              )}
            </div>

            <div className="flex items-center gap-3 text-[11px] font-mono text-muted-foreground">
              <span>Due: {task.due_date || 'No deadline'}</span>
              {task.source_entity && (
                <span>
                  Source: {task.source_entity.labels.join(', ')} ({task.source_entity.id})
                </span>
              )}
            </div>
          </div>

          <span className="text-[10px] font-mono text-muted-foreground shrink-0">
            ID: {task.task_id}
          </span>
        </div>
      ))}
    </div>
  );
}

