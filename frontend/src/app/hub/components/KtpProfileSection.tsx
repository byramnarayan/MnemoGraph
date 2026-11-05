'use client';

import React from 'react';
import { SectionAPersonProfile } from '../types';

interface KtpProfileSectionProps {
  profile: SectionAPersonProfile | null;
}

export function KtpProfileSection({ profile }: KtpProfileSectionProps) {
  if (!profile) return null;

  return (
    <div className="space-y-6">
      {/* Skills */}
      <div className="space-y-2">
        <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-muted-foreground">
          Institutional Skills & Competencies
        </h4>
        <div className="flex flex-wrap gap-1.5">
          {profile.skills.length > 0 ? (
            profile.skills.map((skill, idx) => (
              <span
                key={idx}
                className="px-2.5 py-1 text-xs font-mono rounded-md bg-muted border border-border text-foreground"
              >
                {skill}
              </span>
            ))
          ) : (
            <p className="text-xs text-muted-foreground font-mono">No specific skill tags recorded.</p>
          )}
        </div>
      </div>

      {/* Organizational Hierarchy Chain */}
      {profile.manager_chain.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-muted-foreground">
            Manager Reporting Chain
          </h4>
          <div className="flex flex-col space-y-1.5 pl-2 border-l border-border">
            {profile.manager_chain.map((m, idx) => (
              <div key={idx} className="flex items-center gap-2 text-xs">
                <span className="font-mono text-muted-foreground text-[11px]">Level {m.depth}:</span>
                <span className="font-medium text-foreground">{m.name}</span>
                <span className="text-muted-foreground">({m.role || 'Manager'})</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Role History Chain */}
      {profile.role_history.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-muted-foreground">
            Held Role History Chain
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {profile.role_history.map((rh, idx) => (
              <div
                key={idx}
                className="p-3 rounded-lg bg-card/60 border border-border text-xs space-y-1"
              >
                <div className="font-medium text-foreground">{rh.title}</div>
                <div className="text-[11px] text-muted-foreground font-mono">
                  {rh.department || 'Department'} • {rh.start_date || 'N/A'} - {rh.end_date || 'Present'}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

