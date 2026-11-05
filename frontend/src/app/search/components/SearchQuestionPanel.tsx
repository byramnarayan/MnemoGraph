'use client';

import React, { useState } from 'react';
import { UKGOEAnswerData, MemoryEpisode } from '../types';
import { PredictiveIntelligenceView } from './PredictiveIntelligenceView';

interface SearchQuestionPanelProps {
  answerData: UKGOEAnswerData | null;
  isLoading: boolean;
  onSearch: (query: string) => void;
  onRunCypher: (cypher: string) => void;
  isCypherRunning: boolean;
  history: MemoryEpisode[];
  onSelectEpisode: (ep: MemoryEpisode) => void;
  userClearance?: string;
}

export function SearchQuestionPanel({
  answerData,
  isLoading,
  onSearch,
  onRunCypher,
  isCypherRunning,
  history,
  onSelectEpisode,
  userClearance,
}: SearchQuestionPanelProps) {
  const DEFAULT_CYPHER = "MATCH (a)-[r]->(b) WHERE NOT a.id STARTS WITH 'dup_' AND NOT b.id STARTS WITH 'dup_' RETURN labels(a)[0], a.id, coalesce(a.name, a.title, a.id), type(r), labels(b)[0], b.id, coalesce(b.name, b.title, b.id) LIMIT 30";
  const [queryInput, setQueryInput] = useState('');
  const [activeTab, setActiveTab] = useState<'answer' | 'predictive' | 'citations' | 'query' | 'memory'>('answer');
  const [editableCypher, setEditableCypher] = useState(DEFAULT_CYPHER);

  const hasPredictive = Boolean(
    answerData?.intent === 'PREDICTIVE' ||
    (answerData?.predictive_scenarios && answerData.predictive_scenarios.length > 0)
  );

  React.useEffect(() => {
    if (answerData) {
      let q = answerData.graph_query_used || answerData.graph_query || '';
      q = q.replace(/^```[a-z]*\s*/i, '').replace(/```$/i, '').trim();
      setEditableCypher(q || DEFAULT_CYPHER);
      setActiveTab(hasPredictive ? 'predictive' : 'answer');
    }
  }, [answerData, hasPredictive]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!queryInput.trim() || isLoading) return;
    onSearch(queryInput.trim());
  };

  return (
    <aside className="w-full lg:w-[440px] flex flex-col h-full border-l border-border bg-card/60 backdrop-blur-md shrink-0 font-sans z-20">
      {/* Top Header */}
      <div className="p-4 border-b border-border flex items-center justify-between font-mono text-xs">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-accent animate-pulse" />
          <span className="font-bold uppercase tracking-wider text-foreground">
            Intelligence & Q&A
          </span>
        </div>
        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-accent/15 border border-accent/30 text-accent">
          {userClearance || 'Internal'}
        </span>
      </div>

      {/* Query Input Box */}
      <div className="p-4 border-b border-border bg-background/50">
        <form onSubmit={handleSubmit} className="flex gap-2 font-mono">
          <input
            type="text"
            value={queryInput}
            onChange={(e) => setQueryInput(e.target.value)}
            placeholder="Ask question across institutional graph..."
            className="flex-1 bg-background border border-border rounded-xl px-3.5 py-2 text-xs text-foreground placeholder-muted-foreground focus:outline-none focus:border-accent"
          />
          <button
            type="submit"
            disabled={isLoading || !queryInput.trim()}
            className="px-4 py-2 rounded-xl bg-accent text-accent-foreground font-semibold text-xs hover:opacity-90 disabled:opacity-50 transition-opacity shrink-0 shadow-xs"
          >
            {isLoading ? '...' : 'Ask'}
          </button>
        </form>
      </div>

      {/* Tab Navigation */}
      <div className="flex items-center border-b border-border bg-card/40 px-3 py-1.5 gap-1 font-mono text-[11px] overflow-x-auto scrollbar-none">
        {(['answer', ...(hasPredictive ? ['predictive'] : []), 'citations', 'query', 'memory'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab as any)}
            className={`px-3 py-1 rounded-lg transition-colors capitalize ${
              activeTab === tab
                ? 'bg-accent/20 text-accent font-semibold'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            {tab === 'predictive'
              ? 'Predictive Intel'
              : tab === 'citations'
              ? `Citations (${answerData?.sources.length || 0})`
              : tab}
          </button>
        ))}
      </div>

      {/* Tab Body */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {isLoading ? (
          <div className="py-16 text-center font-mono text-xs text-muted-foreground space-y-2">
            <span className="w-3 h-3 rounded-full bg-accent inline-block animate-ping" />
            <p>Traversing multi-hop ontology and synthesizing grounded answer...</p>
          </div>
        ) : !answerData && activeTab !== 'memory' ? (
          <div className="py-16 text-center font-mono text-xs text-muted-foreground">
            Submit a question above to reason across the universal knowledge graph.
          </div>
        ) : (
          <>
            {/* PREDICTIVE INTEL TAB */}
            {activeTab === 'predictive' && answerData && (
              <PredictiveIntelligenceView data={answerData} />
            )}

            {/* ANSWER TAB */}
            {activeTab === 'answer' && answerData && (
              <div className="space-y-4 text-xs">
                {/* Grounded Natural Language Answer */}
                <div className="p-5 rounded-xl bg-card border border-border text-foreground leading-relaxed whitespace-pre-wrap shadow-xs text-sm">
                  {answerData.answer_text}
                </div>

                {/* Inline Citations Preview */}
                {answerData.sources.length > 0 && (
                  <div className="space-y-2 pt-1 border-t border-border/70">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                        Supporting Citations ({answerData.sources.length})
                      </span>
                      <button
                        onClick={() => setActiveTab('citations')}
                        className="text-[10px] font-mono text-accent hover:underline"
                      >
                        Inspect All →
                      </button>
                    </div>
                    <div className="space-y-1.5">
                      {answerData.sources.slice(0, 4).map((src, i) => (
                        <div
                          key={i}
                          onClick={() => setActiveTab('citations')}
                          className="p-2 rounded-lg bg-muted/40 hover:bg-muted/70 cursor-pointer border border-border/60 transition-colors flex items-start gap-2 text-[11px]"
                        >
                          <span className="px-1.5 py-0.5 rounded bg-card border border-border font-mono font-bold text-[10px] shrink-0 text-foreground">
                            [{i + 1}]
                          </span>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-1.5 truncate">
                              <span className="font-semibold text-foreground truncate">{src.label || src.entity_id}</span>
                              <span className="text-[9px] px-1 rounded bg-accent/15 text-accent font-mono shrink-0">
                                {src.vector_score > 0 && !src.graph_path?.length ? 'Qdrant Vector' : 'Knowledge Graph'}
                              </span>
                            </div>
                            <p className="text-muted-foreground text-[10px] truncate mt-0.5">
                              {src.excerpt}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Inference Insights */}
                {answerData.inference_insights.length > 0 && (
                  <div className="space-y-2">
                    <h4 className="font-mono text-[11px] font-bold text-muted-foreground uppercase">
                      Inferences Applied
                    </h4>
                    {answerData.inference_insights.map((ins, i) => (
                      <div key={i} className="p-2.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-700 dark:text-indigo-300 font-mono text-[11px]">
                        <span className="font-bold mr-1.5">[{ins.rule_id}]</span>
                        {ins.finding}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* CITATIONS TAB */}
            {activeTab === 'citations' && answerData && (
              <div className="space-y-3 font-mono text-xs">
                {answerData.sources.map((src, idx) => (
                  <div key={idx} className="p-3 rounded-xl border border-border bg-card space-y-1.5 shadow-xs">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5">
                        <span className="px-1.5 py-0.2 rounded bg-muted text-[10px] font-bold text-foreground">
                          [{idx + 1}]
                        </span>
                        <span className="font-bold text-foreground">{src.label || src.entity_id}</span>
                      </div>
                      <span className="px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30 text-[10px] font-bold">
                        Grade {src.data_quality_grade || 'A'}
                      </span>
                    </div>
                    <p className="text-muted-foreground text-[11px] leading-relaxed">
                      {src.excerpt}
                    </p>
                    <div className="text-[10px] text-muted-foreground/80 flex items-center justify-between pt-1 border-t border-border/50">
                      <div className="flex items-center gap-2">
                        <span>Class: {src.entity_class}</span>
                        {src.source_document_id && <span>Doc: {src.source_document_id}</span>}
                      </div>
                      <span className="text-[9px] px-1.5 py-0.5 rounded bg-accent/15 text-accent font-semibold">
                        {src.vector_score > 0 && !src.graph_path?.length ? 'Qdrant Vector (RAG)' : 'FalkorDB Graph Triplet'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* QUERY TAB (openCypher + Run Button) */}
            {activeTab === 'query' && (
              <div className="space-y-3 font-mono text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold text-muted-foreground uppercase">
                    openCypher Graph Query
                  </span>
                  <button
                    onClick={() => editableCypher && onRunCypher(editableCypher)}
                    disabled={isCypherRunning || !editableCypher.trim()}
                    className="px-3 py-1 rounded-md bg-accent text-accent-foreground font-bold text-[11px] hover:opacity-90 disabled:opacity-50 transition-opacity flex items-center gap-1 shadow-xs"
                  >
                    <span>{isCypherRunning ? 'Running...' : '▶ Run Cypher'}</span>
                  </button>
                </div>
                <textarea
                  value={editableCypher}
                  onChange={(e) => setEditableCypher(e.target.value)}
                  rows={6}
                  placeholder="MATCH (n)-[r]->(m) RETURN labels(n)[0], n.id, type(r), labels(m)[0], m.id LIMIT 25"
                  className="w-full bg-background border border-border rounded-xl p-3 text-[11px] text-foreground focus:outline-none focus:border-accent font-mono leading-relaxed"
                />
                <p className="text-[10px] text-muted-foreground">
                  Running this query will project the retrieved subgraph directly onto the vertical graph canvas.
                </p>
              </div>
            )}

            {/* MEMORY TAB (Episodic Memory History) */}
            {activeTab === 'memory' && (
              <div className="space-y-2 font-mono text-xs">
                <span className="text-[11px] font-bold text-muted-foreground uppercase">
                  Episodic Memory Trail ({history.length})
                </span>
                {history.length === 0 ? (
                  <div className="py-8 text-center text-muted-foreground text-[11px]">
                    No previous memory episodes recorded yet.
                  </div>
                ) : (
                  history.map((ep) => (
                    <div
                      key={ep.id}
                      onClick={() => onSelectEpisode(ep)}
                      className="p-3 rounded-xl border border-border bg-card/50 hover:bg-card hover:border-accent/40 cursor-pointer transition-colors space-y-1"
                    >
                      <div className="flex items-center justify-between text-[10px] text-muted-foreground">
                        <span className="truncate max-w-[200px] font-semibold text-foreground">
                          {ep.query}
                        </span>
                        <span>{new Date(ep.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                      </div>
                      <p className="text-[11px] text-muted-foreground line-clamp-2">
                        {ep.answer}
                      </p>
                    </div>
                  ))
                )}
              </div>
            )}
          </>
        )}
      </div>
    </aside>
  );
}

