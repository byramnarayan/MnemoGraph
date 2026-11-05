'use client';

import React from 'react';
import { TimelineEvent } from '../types';

interface DecisionTimelineProps {
  events: TimelineEvent[];
}

export function DecisionTimeline({ events }: DecisionTimelineProps) {
  if (!events || events.length === 0) return null;

  return (
    <section className="space-y-2 font-mono">
      <div className="flex items-center justify-between">
        <h2 className="text-xs font-bold uppercase tracking-wider text-foreground">
          Historical Incident Lineage ({events.length})
        </h2>
      </div>

      <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
        {events.map((ev) => (
          <div
            key={ev.event_id}
            className="flex items-center justify-between p-2.5 rounded-lg bg-card border border-border text-[11px] hover:border-accent/40 transition-colors"
          >
            <div className="flex items-center gap-2.5 truncate">
              <span className={`w-2 h-2 rounded-full shrink-0 ${ev.event_type.includes('INCIDENT') ? 'bg-rose-500' : 'bg-accent'}`} />
              <div className="truncate">
                <span className="font-semibold text-foreground truncate block">{ev.entity_name}</span>
                <span className="text-[10px] text-muted-foreground">{ev.actor_name ? `By ${ev.actor_name}` : ev.affected_scope}</span>
              </div>
            </div>
            <span className="text-[10px] px-2 py-0.5 rounded bg-muted text-muted-foreground shrink-0 font-medium">
              {ev.event_type.replace(/_/g, ' ')}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}

