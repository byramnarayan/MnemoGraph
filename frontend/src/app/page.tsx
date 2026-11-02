'use client';

import React from 'react';
import Link from 'next/link';
import { useAuth } from '@/lib/auth-context';
import { Button, Eyebrow, Frame, Panel, Section, Stat, StatRow, Tag } from '@/kit';

export default function HomePage() {
  const { user } = useAuth();

  return (
    <div>
      {/* Hero Section */}
      <section className="dashed-b relative overflow-hidden">
        <div className="grid-bg pointer-events-none absolute inset-0 opacity-40" aria-hidden="true" />
        <Frame className="relative py-20">
          <Eyebrow>00 / INSTITUTIONAL MEMORY ENGINE</Eyebrow>
          <h1 className="rise mt-6 max-w-4xl text-4xl font-semibold leading-[1.08] tracking-tight sm:text-6xl text-foreground">
            Graph-Augmented Collective Memory <span className="text-accent">& Succession AI</span>.
          </h1>
          <p className="mt-6 max-w-2xl text-base sm:text-lg text-muted-foreground leading-relaxed">
            Eliminate operational blindness across distributed engineering silos. Ingest telemetry, run continuous graph reasoning, and preserve institutional knowledge with enterprise RBAC security.
          </p>

          <div className="mt-8 flex flex-wrap items-center gap-4">
            {user ? (
              <>
                <Link href="/profile">
                  <Button className="bg-accent text-accent-foreground font-semibold px-6 py-2.5 shadow-[0_0_20px_rgba(14,165,233,0.35)]">
                    Access Executive Dashboard →
                  </Button>
                </Link>
                <div className="flex items-center gap-2 font-mono text-xs text-muted-foreground">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                  Logged in as <span className="text-foreground">{user.email}</span>
                </div>
              </>
            ) : (
              <>
                <Link href="/register">
                  <Button className="bg-accent text-accent-foreground font-semibold px-6 py-2.5 shadow-[0_0_20px_rgba(14,165,233,0.35)]">
                    Provision Organization Brain →
                  </Button>
                </Link>
                <Link href="/login">
                  <Button variant="ghost" className="px-5 py-2.5">
                    Sign In to Portal
                  </Button>
                </Link>
              </>
            )}
          </div>
        </Frame>
      </section>

      {/* Stats Section */}
      <Section n="01" label="System Telemetry" title="Enterprise Lakehouse & Graph Ingestion">
        <StatRow>
          <Stat k="Knowledge Nodes" v="2.4M+" sub="cross-silo entities" />
          <Stat k="Ingestion Latency" v="< 85ms" sub="real-time lakehouse" />
          <Stat k="Active Silos" v="14" sub="network & billing" />
          <Stat k="Isolation SLA" v="99.99%" sub="strict tenant boundary" />
        </StatRow>
      </Section>

      {/* Feature Breakdown */}
      <Section n="02" label="Core Architecture" title="Multi-Tiered Knowledge Preservation">
        <div className="grid gap-6 md:grid-cols-3">
          <Panel title="Neon Cloud PostgreSQL">
            <div className="p-5 space-y-3">
              <Tag tone="accent">ACID Storage</Tag>
              <h3 className="font-medium text-foreground">Relational Identity & RBAC</h3>
              <p className="text-xs text-muted-foreground leading-relaxed">
                High-concurrency serverless Postgres engine storing administrative tenant schemas, encrypted credentials, and access logs.
              </p>
            </div>
          </Panel>

          <Panel title="AWS S3 Object Store">
            <div className="p-5 space-y-3">
              <Tag tone="ok">Media Layer</Tag>
              <h3 className="font-medium text-foreground">Profile & Document Lakehouse</h3>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Auto-resizing, EXIF-sanitized asset ingestion pipeline with low-latency CDN delivery and default avatar failover.
              </p>
            </div>
          </Panel>

          <Panel title="Knowledge Graphs">
            <div className="p-5 space-y-3">
              <Tag tone="info">Semantic Engine</Tag>
              <h3 className="font-medium text-foreground">Neo4j & Vector Pipeline</h3>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Multi-hop graph cartography and vector similarity indexing powering automated succession reasoning across departments.
              </p>
            </div>
          </Panel>
        </div>
      </Section>
    </div>
  );
}

