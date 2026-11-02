'use client';

import React from 'react';
import Link from 'next/link';
import { useAuth } from '@/lib/auth-context';

export function Footer() {
  const { user } = useAuth();

  // If user is logged in, hide footer across all dashboard/portal pages to prevent congestion
  if (user) {
    return null;
  }

  return (
    <footer className="border-t border-border/80 bg-background/50 mt-auto py-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-sm tracking-tight">MnemoGraph</span>
              <span className="font-mono text-[9px] uppercase px-1 py-0.5 rounded bg-muted text-muted-foreground border border-border">
                MaaS Platform
              </span>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Unified Institutional & Enterprise Intelligence: Graph-Augmented Collective Memory (GACM), Cross-Silo Lakehouse Ingestion, and Succession Shadow AI.
            </p>
          </div>

          <div>
            <h4 className="font-mono text-[11px] font-semibold tracking-wider uppercase text-foreground mb-3">
              Platform Intelligence
            </h4>
            <ul className="space-y-2 text-xs text-muted-foreground">
              <li><Link href="#" className="hover:text-foreground">Graph Cartography Explorer</Link></li>
              <li><Link href="#" className="hover:text-foreground">Memory Ingestion Pipeline</Link></li>
              <li><Link href="#" className="hover:text-foreground">Lakehouse & Data Connectors</Link></li>
            </ul>
          </div>

          <div>
            <h4 className="font-mono text-[11px] font-semibold tracking-wider uppercase text-foreground mb-3">
              Governance & Security
            </h4>
            <ul className="space-y-2 text-xs text-muted-foreground">
              <li><Link href="#" className="hover:text-foreground">Security & ACL Audit Trail</Link></li>
              <li><Link href="#" className="hover:text-foreground">Cross-Silo Analytics</Link></li>
              <li><Link href="#" className="hover:text-foreground">Staff Directory & RBAC</Link></li>
            </ul>
          </div>

          <div>
            <h4 className="font-mono text-[11px] font-semibold tracking-wider uppercase text-foreground mb-3">
              Infrastructure Status
            </h4>
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                <span className="font-mono text-xs text-muted-foreground">Operational · 99.98% SLA</span>
              </div>
              <p className="text-[11px] text-muted-foreground/80 font-mono">
                PostgreSQL Neon • Neo4j Aura • S3 Storage
              </p>
            </div>
          </div>
        </div>

        <div className="mt-8 pt-8 border-t border-border/50 flex flex-col sm:flex-row items-center justify-between text-xs text-muted-foreground">
          <p>© 2026 MnemoGraph Enterprise Intelligence Inc. All rights reserved.</p>
          <div className="flex items-center gap-6 mt-4 sm:mt-0 font-mono text-[11px]">
            <Link href="#" className="hover:text-foreground">Privacy Protocol</Link>
            <Link href="#" className="hover:text-foreground">Security Certifications</Link>
            <Link href="#" className="hover:text-foreground">API Docs</Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
