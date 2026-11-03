'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import { api } from '@/lib/api-client';
import { Tag } from '@/kit';

// Modular Search Components
import { LeftSidebar, CollectionItem, MemoryEpisodeItem } from './components/LeftSidebar';
import { GraphCanvas, GraphNode, GraphEdge } from './components/GraphCanvas';
import { GraphCanvasModal } from './components/GraphCanvasModal';
import { RightDrawer, RightDrawerItem } from './components/RightDrawer';
import { AnswerSection, AnswerData } from './components/AnswerSection';
import { QuestionInput } from './components/QuestionInput';

export default function SearchPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();

  // Multi-Store Collections State
  const [collections, setCollections] = useState<CollectionItem[]>([]);
  const [collectionsLoading, setCollectionsLoading] = useState(true);

  // Graphiti Temporal Episodic Memory State
  const [history, setHistory] = useState<MemoryEpisodeItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [selectedEpisodeId, setSelectedEpisodeId] = useState<string | null>(null);

  // Graph Subgraph State (Initial Authorized Graph vs Search-Query Graph)
  const [graphNodes, setGraphNodes] = useState<GraphNode[]>([]);
  const [graphEdges, setGraphEdges] = useState<GraphEdge[]>([]);
  const [isGraphModalOpen, setIsGraphModalOpen] = useState(false);
  const [activeQueryTitle, setActiveQueryTitle] = useState<string>('Enterprise Canonical Knowledge Graph');

  // Answer & Search State
  const [answerData, setAnswerData] = useState<AnswerData | null>(null);
  const [searchLoading, setSearchLoading] = useState(false);

  // Right-Side Drawer State
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerItem, setDrawerItem] = useState<RightDrawerItem | null>(null);

  const isAdmin = Boolean(
    user?.role && ['admin', 'executive', 'director', 'vp'].some((k) => user.role.toLowerCase().includes(k))
  );

  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login');
      return;
    }
    if (user) {
      loadCollections();
      loadMemoryHistory();
      loadInitialUserGraph();
    }
  }, [user, authLoading]);

  // 1. Fetch Multi-Store Collections
  const loadCollections = async () => {
    setCollectionsLoading(true);
    try {
      const data = await api.hub.listCollections();
      setCollections(data || []);
    } catch (err) {
      console.error('Failed to load multi-store collections:', err);
    } finally {
      setCollectionsLoading(false);
    }
  };

  // 2. Fetch User's Chronological Memory History (Ascending in timestamp)
  const loadMemoryHistory = async () => {
    setHistoryLoading(true);
    try {
      const episodes = await api.hub.getMemoryHistory('asc');
      setHistory(episodes || []);
    } catch (err) {
      console.error('Failed to load memory history:', err);
    } finally {
      setHistoryLoading(false);
    }
  };

  // 3. Fetch User-Scoped Initial Graph from FalkorDB
  const loadInitialUserGraph = async () => {
    try {
      const graphData = await api.hub.getUserSubgraph();
      if (graphData && graphData.nodes) {
        setGraphNodes(graphData.nodes);
        setGraphEdges(graphData.edges || []);
        setActiveQueryTitle('Enterprise Canonical Knowledge Graph');
      }
    } catch (err) {
      console.error('Failed to load user authorized graph:', err);
    }
  };

  // 4. Collection Deletion Handler (Admin Only)
  const handleDeleteCollection = async (storeType: string, collectionId: string) => {
    try {
      await api.hub.deleteCollection(storeType, collectionId);
      loadCollections();
    } catch (err: any) {
      alert(err.message || 'Failed to delete collection.');
    }
  };

  // 5. Select a Past Question from Memory History
  const handleSelectEpisode = (ep: MemoryEpisodeItem) => {
    setSelectedEpisodeId(ep.id);
    setActiveQueryTitle(`Memory Recall: ${ep.query}`);

    const reconstructedAnswer: AnswerData = {
      answer_text: ep.answer,
      confidence: ep.confidence,
      sources: (ep.sources || []).map((s: any) => ({
        document_id: s.document_id || s.title || 'DOC-REF',
        source_url: s.source_url || '',
        excerpt: s.excerpt || '',
        score: s.score || 0.9,
        related_people: s.related_people || [],
        related_teams: s.related_teams || [],
        related_projects: s.related_projects || [],
      })),
      provenance: (ep.provenance || []).map((p: any) => ({
        title: `Path: ${p.from || 'Node'} -> ${p.to || 'Node'}`,
        path: [p.relation || 'RELATED_TO'],
        people: [],
        teams: [],
        projects: [],
      })),
      generated_cypher: ep.cypher_query,
    };

    setAnswerData(reconstructedAnswer);

    if (ep.cypher_query) {
      handleRunCypher(ep.cypher_query, false);
    }
  };

  // 6. Handle New Question Submission (Qdrant Vector Retrieval + Groq Synthesis)
  const handleAskQuestion = async (queryText: string) => {
    setSearchLoading(true);
    setActiveQueryTitle(`Query: ${queryText}`);

    try {
      const res = await api.hub.search({
        query: queryText,
        limit: 6,
      });

      const parsedAnswer: AnswerData = {
        answer_text: res.answer_text || 'No conclusive evidence found.',
        confidence: res.confidence || 0.8,
        sources: (res.evidence || []).map((ev: any) => ({
          document_id: ev.document_id || 'DOC-REF',
          source_url: ev.source_url || '',
          excerpt: ev.excerpt || '',
          score: ev.score || 0.85,
          related_people: ev.related_people || [],
          related_teams: ev.related_teams || [],
          related_projects: ev.related_projects || [],
        })),
        provenance: (res.relation_path || []).map((p: any) => ({
          title: `Path: ${p.from || 'Node'} -> ${p.to || 'Node'}`,
          path: [p.relation || 'RELATED_TO'],
          people: res.related_people || [],
          teams: res.related_teams || [],
          projects: res.related_projects || [],
        })),
        generated_cypher: res.provenance_cypher || `MATCH (d:Document)-[r]->(p:Person) RETURN labels(d)[0], d.id, type(r), labels(p)[0], p.id LIMIT 25`,
      };

      setAnswerData(parsedAnswer);

      // Refresh memory history so the new episode shows immediately
      loadMemoryHistory();

      if (parsedAnswer.generated_cypher) {
        handleRunCypher(parsedAnswer.generated_cypher, false);
      }
    } catch (err) {
      console.error('Search failed:', err);
    } finally {
      setSearchLoading(false);
    }
  };

  // 7. Run Cypher Query against FalkorDB
  const handleRunCypher = async (cypherQuery: string, openModal = true) => {
    try {
      const res = await api.hub.runGraphQuery({ cypher: cypherQuery, limit: 50 });
      if (res && res.nodes) {
        setGraphNodes(res.nodes);
        setGraphEdges(res.edges || []);
        if (openModal) {
          setIsGraphModalOpen(true);
        }
      }
    } catch (err) {
      console.error('Failed to run Cypher query:', err);
    }
  };

  // 8. Right-Side Drawer Openers
  const handleOpenSource = (src: AnswerData['sources'][0]) => {
    setDrawerItem({
      type: 'source',
      title: src.document_id,
      subtitle: src.source_url,
      score: src.score,
      excerpt: src.excerpt,
      sourceUrl: src.source_url,
      relatedPeople: src.related_people,
      relatedTeams: src.related_teams,
      relatedProjects: src.related_projects,
    });
    setDrawerOpen(true);
  };

  const handleOpenCitation = (cite: AnswerData['provenance'][0]) => {
    setDrawerItem({
      type: 'citation',
      title: cite.title,
      subtitle: `Traversed via relationship: ${cite.path.join(', ')}`,
      score: answerData?.confidence,
      excerpt: `Multi-hop grounded path connecting people (${cite.people.join(', ') || 'N/A'}) and teams (${cite.teams.join(', ') || 'N/A'}).`,
      relatedPeople: cite.people,
      relatedTeams: cite.teams,
      relatedProjects: cite.projects,
      provenancePath: cite.path,
    });
    setDrawerOpen(true);
  };

  return (
    <div className="flex h-[calc(100vh-4rem)] bg-background overflow-hidden font-mono">
      {/* 1. Left Sidebar: Toggle Switcher between [Collections] and [Memory & History] */}
      <LeftSidebar
        collections={collections}
        collectionsLoading={collectionsLoading}
        onDeleteCollection={handleDeleteCollection}
        isAdmin={isAdmin}
        history={history}
        historyLoading={historyLoading}
        selectedEpisodeId={selectedEpisodeId}
        onSelectEpisode={handleSelectEpisode}
        onRefreshHistory={loadMemoryHistory}
      />

      {/* 2. Main Search & Graph Workspace */}
      <main className="flex-1 flex flex-col h-full overflow-hidden bg-background">
        {/* Header Breadcrumb & Status */}
        <div className="h-14 border-b border-border/80 px-6 flex items-center justify-between shrink-0 bg-card/20">
          <div className="flex items-center gap-2 text-xs text-muted-foreground uppercase tracking-wider">
            <Link href="/" className="hover:text-foreground">Home</Link>
            <span>/</span>
            <span className="text-foreground">Enterprise Knowledge & Memory Workspace</span>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={loadInitialUserGraph}
              className="text-xs px-2.5 py-1 rounded-xs border border-border bg-muted/20 hover:border-accent text-foreground transition-all flex items-center gap-1.5"
              title="Reload canonical graph topology"
            >
              <span>↻ Reset Subgraph</span>
            </button>
            <Link
              href="/hub"
              className="text-xs px-3 py-1 rounded-xs border border-accent/40 bg-accent/10 hover:bg-accent/20 text-accent transition-all flex items-center gap-1.5"
            >
              <span>Knowledge Hub Directory →</span>
            </Link>
            <Tag tone="accent">
              {isAdmin ? 'ADMIN CLEARANCE' : 'USER CLEARANCE'}
            </Tag>
            <button
              onClick={() => setIsGraphModalOpen(true)}
              className="text-xs px-3 py-1 rounded-xs border border-border bg-muted/30 hover:border-accent text-foreground transition-all flex items-center gap-1.5"
            >
              <span>View Canvas Popup</span>
              <span className="text-accent font-semibold">[{graphNodes.length}]</span>
            </button>
          </div>
        </div>

        {/* Scrollable Center Area: Canvas on Top + Answer Section in Middle */}
        <div className="flex-1 overflow-y-auto p-6 space-y-5">
          {/* Graph Canvas */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span className="uppercase font-semibold text-foreground">
                {activeQueryTitle}
              </span>
              <span>Click nodes to inspect attributes & relationships</span>
            </div>
            <GraphCanvas
              nodes={graphNodes}
              edges={graphEdges}
              height={340}
              onNodeClick={(node) => {
                setDrawerItem({
                  type: 'ontology_node',
                  title: `${node.label}: ${node.properties?.title || node.properties?.name || node.id}`,
                  subtitle: `Label: ${node.label} | Node ID: ${node.id}`,
                  excerpt: node.properties?.description || node.properties?.path || undefined,
                  metadata: node.properties || {},
                });
                setDrawerOpen(true);
              }}
            />
          </div>

          {/* Grounded Answer Section */}
          <AnswerSection
            data={answerData}
            loading={searchLoading}
            onOpenSource={handleOpenSource}
            onOpenCitation={handleOpenCitation}
            onOpenGraph={() => setIsGraphModalOpen(true)}
            onRunCypher={(cypher) => handleRunCypher(cypher, true)}
          />
        </div>

        {/* 3. Fixed Bottom Area: Question Input Box */}
        <QuestionInput onAsk={handleAskQuestion} loading={searchLoading} />
      </main>

      {/* 4. Slide-out Right-Side Drawer */}
      <RightDrawer
        isOpen={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        item={drawerItem}
      />

      {/* 5. Closable Popup Graph Canvas Modal */}
      <GraphCanvasModal
        isOpen={isGraphModalOpen}
        onClose={() => setIsGraphModalOpen(false)}
        nodes={graphNodes}
        edges={graphEdges}
        queryTitle={activeQueryTitle}
      />
    </div>
  );
}
