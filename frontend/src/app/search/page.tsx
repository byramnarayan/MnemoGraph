'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import { searchApi } from '@/lib/search-api';
import { UKGOEAnswerData, GraphNode, GraphEdge, MemoryEpisode } from './types';

import { SearchGraphLegend } from './components/SearchGraphLegend';
import { SearchGraphControls } from './components/SearchGraphControls';
import { SearchGraphView } from './components/SearchGraphView';
import { SearchQuestionPanel } from './components/SearchQuestionPanel';

export default function SearchPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();

  // Graph State
  const [graphNodes, setGraphNodes] = useState<GraphNode[]>([]);
  const [graphEdges, setGraphEdges] = useState<GraphEdge[]>([]);
  const [zoomLevel, setZoomLevel] = useState(1);
  const [panOffset, setPanOffset] = useState({ x: 0, y: 0 });
  const [isExecutingCypher, setIsExecutingCypher] = useState(false);

  // Q&A and Memory State
  const [answerData, setAnswerData] = useState<UKGOEAnswerData | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [history, setHistory] = useState<MemoryEpisode[]>([]);

  // 1. Auth Guard
  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login');
    }
  }, [user, authLoading, router]);

  // 2. Load Memory History
  const loadHistory = useCallback(async () => {
    try {
      const eps = await searchApi.getMemoryHistory('desc');
      setHistory(eps || []);
    } catch (err) {
      console.error('Failed to load memory history:', err);
    }
  }, []);

  // 3. Load Initial Authorized Subgraph from FalkorDB
  const loadInitialGraph = useCallback(async () => {
    try {
      setIsExecutingCypher(true);
      const data = await searchApi.getUserSubgraph();
      if (data && data.nodes) {
        setGraphNodes(data.nodes);
        setGraphEdges(data.edges || []);
        setZoomLevel(1);
        setPanOffset({ x: 0, y: 0 });
      }
    } catch (err) {
      console.error('Failed to load initial subgraph:', err);
    } finally {
      setIsExecutingCypher(false);
    }
  }, []);

  useEffect(() => {
    if (user) {
      loadHistory();
      loadInitialGraph();
    }
  }, [user, loadHistory, loadInitialGraph]);

  // 4. Handle Question Submission across UKGOE
  const handleSearch = async (queryText: string) => {
    setIsSearching(true);
    try {
      const res = await searchApi.search(queryText, {
        limit: 6,
        clearance: user?.clearance_level || 'Internal',
      });
      setAnswerData(res);
      loadHistory();

      // If Cypher was generated, execute it to update the vertical graph
      const cypher = res.graph_query_used || res.graph_query;
      if (cypher) {
        handleRunCypher(cypher);
      }
    } catch (err) {
      console.error('Search failed:', err);
    } finally {
      setIsSearching(false);
    }
  };

  // 5. Execute openCypher Query Live against FalkorDB
  const handleRunCypher = async (cypherQuery: string) => {
    try {
      setIsExecutingCypher(true);
      let clean = cypherQuery.trim().replace(/^```[a-z]*\s*/i, '').replace(/```$/i, '').trim();
      clean = clean.replace(/;+\s*$/, '');
      const res = await searchApi.runGraphQuery(clean, 40);
      if (res && res.nodes && res.nodes.length > 0) {
        setGraphNodes(res.nodes);
        setGraphEdges(res.edges || []);
      }
    } catch (err) {
      console.error('Failed to execute cypher query:', err);
    } finally {
      setIsExecutingCypher(false);
    }
  };

  // 6. Select Past Memory Episode
  const handleSelectEpisode = (ep: MemoryEpisode) => {
    setAnswerData({
      answer_text: ep.answer,
      intent: 'FACTUAL',
      confidence: ep.confidence || 0.9,
      sources: ep.sources || [],
      inference_insights: [],
      missing_data_gaps: [],
      cascade_warnings: [],
      graph_query_used: ep.cypher_query,
    });
    if (ep.cypher_query) {
      handleRunCypher(ep.cypher_query);
    }
  };

  if (authLoading || (!user && typeof window !== 'undefined')) {
    return (
      <div className="flex items-center justify-center min-h-[calc(100vh-4rem)] font-mono text-xs text-muted-foreground">
        Authenticating institutional clearance...
      </div>
    );
  }

  return (
    <div className="flex flex-col lg:flex-row h-[calc(100vh-4rem)] w-full overflow-hidden bg-background text-foreground font-sans">
      {/* Left: Vertical Interactive Graph Canvas (Matching User Image Format) */}
      <section className="relative flex-1 h-full min-h-[350px] overflow-hidden border-r border-border">
        {/* Floating Universal Legend */}
        <SearchGraphLegend />

        {/* Floating Zoom & Fit Toolbar */}
        <SearchGraphControls
          onZoomIn={() => setZoomLevel((z) => Math.min(z + 0.2, 2.5))}
          onZoomOut={() => setZoomLevel((z) => Math.max(z - 0.2, 0.4))}
          onReset={loadInitialGraph}
          onFit={() => { setZoomLevel(1); setPanOffset({ x: 0, y: 0 }); }}
          nodeCount={graphNodes.length}
          edgeCount={graphEdges.length}
          isExecuting={isExecutingCypher}
        />

        {/* Main Canvas */}
        <SearchGraphView
          nodes={graphNodes}
          edges={graphEdges}
          zoomLevel={zoomLevel}
          panOffset={panOffset}
          onPanChange={setPanOffset}
        />
      </section>

      {/* Right: Minimal Question & Answer Intelligence Panel */}
      <SearchQuestionPanel
        answerData={answerData}
        isLoading={isSearching}
        onSearch={handleSearch}
        onRunCypher={handleRunCypher}
        isCypherRunning={isExecutingCypher}
        history={history}
        onSelectEpisode={handleSelectEpisode}
        userClearance={user?.clearance_level}
      />
    </div>
  );
}
