'use client';

import React from 'react';
import { DecisionDeepDiveNarrative } from '../types';
import {
  FileText,
  Clock,
  Sparkles,
  ShieldAlert,
  GitBranch,
  BookOpen,
  ArrowLeft,
  CheckCircle2,
} from 'lucide-react';

interface Props {
  data: DecisionDeepDiveNarrative;
  loading: boolean;
  onBack: () => void;
  onOpenReportModal: () => void;
}

export function DecisionNarrativeDeepDive({
  data,
  loading,
  onBack,
  onOpenReportModal,
}: Props) {
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 space-y-4">
        <div className="w-10 h-10 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        <p className="text-sm text-zinc-400">Synthesizing multi-store narrative timeline via Groq LLM...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Navigation & Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-zinc-800">
        <div className="space-y-1">
          <button
            onClick={onBack}
            className="inline-flex items-center gap-1.5 text-xs text-zinc-400 hover:text-zinc-200 transition-colors mb-1"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Back to Decisions Explorer
          </button>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-zinc-100">{data.decision_title}</h1>
            <span className="px-3 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/30">
              {Math.round(data.incident_probability * 100)}% {data.risk_tier} Hazard
            </span>
          </div>
          <p className="text-xs text-zinc-400">
            Estimated Vulnerability Window: <span className="text-zinc-200 font-medium">{data.predicted_horizon}</span>
          </p>
        </div>

        <button
          onClick={onOpenReportModal}
          className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium bg-gradient-to-r from-indigo-500 to-purple-600 text-white hover:from-indigo-600 hover:to-purple-700 shadow-md shadow-indigo-500/20 transition-all duration-200"
        >
          <Sparkles className="w-4 h-4" />
          Generate Action Proposal Report
        </button>
      </div>

      {/* 1. Executive Scenario */}
      <div className="bg-zinc-900/70 border border-zinc-800 rounded-xl p-5 space-y-2">
        <div className="flex items-center gap-2 text-rose-400 text-sm font-semibold">
          <ShieldAlert className="w-4 h-4" />
          <h3>Executive Scenario & Potential Failure Mode</h3>
        </div>
        <p className="text-sm text-zinc-300 leading-relaxed whitespace-pre-line">
          {data.executive_scenario}
        </p>
      </div>

      {/* 2. Chronological Timeline */}
      <div className="bg-zinc-900/70 border border-zinc-800 rounded-xl p-5 space-y-3">
        <div className="flex items-center gap-2 text-indigo-400 text-sm font-semibold">
          <Clock className="w-4 h-4" />
          <h3>Chronological Timeline Description</h3>
        </div>
        <div className="text-sm text-zinc-300 leading-relaxed whitespace-pre-line pl-2 border-l-2 border-indigo-500/40">
          {data.narrative_timeline}
        </div>
      </div>

      {/* 3. Interconnected Graph Context */}
      <div className="bg-zinc-900/70 border border-zinc-800 rounded-xl p-5 space-y-3">
        <div className="flex items-center gap-2 text-emerald-400 text-sm font-semibold">
          <GitBranch className="w-4 h-4" />
          <h3>Interconnected Infrastructure & Dependency Bottlenecks</h3>
        </div>
        <p className="text-sm text-zinc-300 leading-relaxed whitespace-pre-line">
          {data.interconnected_context}
        </p>
      </div>

      {/* 4. Lessons Learned & Precedents */}
      <div className="bg-zinc-900/70 border border-zinc-800 rounded-xl p-5 space-y-3">
        <div className="flex items-center gap-2 text-amber-400 text-sm font-semibold">
          <BookOpen className="w-4 h-4" />
          <h3>Historical Precedents & Lessons Learned</h3>
        </div>
        <p className="text-sm text-zinc-300 leading-relaxed whitespace-pre-line">
          {data.lessons_learned}
        </p>
      </div>

      {/* Recommended Action & Footnotes */}
      <div className="bg-gradient-to-br from-zinc-900 to-zinc-900/90 border border-indigo-500/30 rounded-xl p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-indigo-300 text-sm font-semibold">
            <CheckCircle2 className="w-4 h-4 text-indigo-400" />
            <h3>Evidence-Backed Recommended Intervention</h3>
          </div>
          <span className="text-xs px-2.5 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 font-medium">
            Role: {data.recommended_action.suggested_role}
          </span>
        </div>

        <p className="text-sm font-medium text-zinc-200">
          {data.recommended_action.action_title}
        </p>

        <div className="space-y-1.5 pl-2">
          {data.recommended_action.implementation_steps.map((step, idx) => (
            <div key={idx} className="text-xs text-zinc-300 flex items-start gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 mt-1.5 flex-shrink-0" />
              <span>{step}</span>
            </div>
          ))}
        </div>

        <div className="pt-3 border-t border-zinc-800/80 flex flex-wrap items-center justify-between gap-3 text-xs text-zinc-400">
          <div className="flex items-center gap-4">
            {data.evidence_citations.map((c) => (
              <span key={c.id} className="inline-flex items-center gap-1 text-[11px] text-zinc-400">
                <span className="font-semibold text-indigo-400">[{c.id}]</span> {c.source}: {c.detail}
              </span>
            ))}
          </div>
          <button
            onClick={onOpenReportModal}
            className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 underline underline-offset-4"
          >
            Open Full Editable Action Proposal Draft &rarr;
          </button>
        </div>
      </div>
    </div>
  );
}

