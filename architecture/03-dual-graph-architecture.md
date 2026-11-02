# Architecture Specification: 03 Dual-Graph Architecture

## 1. Architectural Philosophy: The Dual-Graph Separation

In conventional enterprise AI systems, conversational memory is either completely absent (stateless amnesia) or dumped into the same database tables as corporate facts, risking memory pollution, provenance corruption, and data poisoning.

MnemoGraph enforces a **strict dual-layer graph model** hosted within FalkorDB (`enterprise_knowledge_graph`):

```
+─────────────────────────────────────────────────────────────────────────────+
│                       FalkorDB Property Graph Engine                        │
│                                                                             │
│  +───────────────────────────────────────────────────────────────────────+  │
│  │                    LAYER 1: CANONICAL ENTERPRISE GRAPH                │  │
│  │                                                                       │  │
│  │    (:Person) ──[:MEMBER_OF]──► (:Team) ──[:BELONGS_TO]──► (:Dept)     │  │
│  │       │                                                      ▲        │  │
│  │    [:AUTHORED_BY]                                            │        │  │
│  │       ▼                                                      │        │  │
│  │   (:Document) ──[:REFERENCES]──► (:Project) ─────────────────┘        │  │
│  │       ▲                                                               │  │
│  │    [:DERIVED_FROM]                                                    │  │
│  │       │                                                               │  │
│  │   (:Decision) ──[:RELATED_TO]──► (:Task)                              │  │
│  +───────────────────────────────────────────────────────────────────────+  │
│                                      ▲                                      │
│                                      │ [:TOUCHED]                           │
│  +───────────────────────────────────┴───────────────────────────────────+  │
│  │                   LAYER 2: COGNITIVE MEMORY OVERLAY                   │  │
│  │                                                                       │  │
│  │    (:Person) ──[:RECALLED {at: ts}]──► (:EpisodeMemory)               │  │
│  │                                            │                          │  │
│  │                                            └──[:TOUCHED]──► (Target)  │  │
│  +───────────────────────────────────────────────────────────────────────+  │
+─────────────────────────────────────────────────────────────────────────────+
```

1. **Layer 1: Canonical Enterprise Graph (Authoritative Truth)**
   - Permanently stores organizational entities, structural hierarchies, technical specifications, and architectural decisions.
   - Synchronized deterministically from Databricks, object storage, and PostgreSQL.
   - Subject to strict organizational ABAC and ownership policies.
   - Cannot be modified or mutated by user chat interactions.

2. **Layer 2: Cognitive Memory Overlay (Experiential Awareness)**
   - Records historical user episodes and conversational focus using `:EpisodeMemory` nodes.
   - Links episodes to the user's canonical `:Person` persona using directional `:RECALLED` edges.
   - Anchors episodes to canonical entities referenced during answering using directional `:TOUCHED` edges.
   - Used for pre-retrieval context expansion and anaphora resolution without altering canonical business nodes.

---

## 2. Canonical Graph Layer Schema & Entities

The canonical layer is governed by schemas defined in `app/services/graph/schema.py` and managed via `app/services/graph/repository.py`:

### 2.1 Node Labels & Property Encodings

| Node Label | ID Format / Namespace | Required Properties | Optional Properties | Source System |
| :--- | :--- | :--- | :--- | :--- |
| `:Person` | `person:{email}` | `id`, `name`, `email` | `role`, `team_id`, `department_id` | HR / Databricks / PG |
| `:Team` | `team:{normalized_name}` | `id`, `name` | `department_id` | Org Sync / PG |
| `:Department` | `dept:{normalized_name}` | `id`, `name` | - | Org Sync / PG |
| `:Project` | `project:{normalized_name}`| `id`, `name` | `workspace_id`, `description` | Databricks / PG |
| `:Workspace` | `ws:{workspace_id}` | `id`, `name` | `host` | Databricks Connector |
| `:Document` | `doc:{document_id}` | `id`, `title`, `source_id` | `source_system`, `storage_key` | S3 / Ingestion Service |
| `:Decision` | `decision:{decision_id}` | `id`, `title`, `status` | `impact`, `project_id` | ADR Extractor / PG |
| `:Task` | `task:{task_id}` | `id`, `title`, `status` | `assigned_to` | JIRA / Ticket Importer |
| `:Ticket` | `ticket:{ticket_id}` | `id`, `title`, `status` | `severity`, `related_decision` | Incident / NOC Retros |

### 2.2 Canonical Edge Topology

Canonical edges represent verified relational structures extracted from document metadata, source systems, or AST analyzers:

```cypher
// Organizational Hierarchy
(:Person)-[:MEMBER_OF]->(:Team)
(:Team)-[:BELONGS_TO]->(:Department)

// Project & Workspace Scope
(:Workspace)-[:CONTAINS]->(:Project)
(:Project)-[:CONTAINS]->(:Document)

// Document Ownership & Authorship
(:Person)-[:OWNS]->(:Document)
(:Person)-[:AUTHORED_BY]->(:Document)
(:Person)-[:CREATED_BY]->(:Decision)

// Multi-Hop Citations & Mentions
(:Document)-[:REFERENCES]->(:Project)
(:Document)-[:REFERENCES]->(:Document)
(:Document)-[:MENTIONS]->(:Person)
(:Document)-[:MENTIONS]->(:Team)
(:Document)-[:MENTIONS]->(:Decision)
(:Document)-[:MENTIONS]->(:Ticket)

// Architectural Decisions & Tasks
(:Decision)-[:DERIVED_FROM]->(:Document)
(:Decision)-[:RELATED_TO]->(:Project)
(:Task)-[:DEPENDS_ON]->(:Decision)
```

---

## 3. Cognitive Memory Overlay Schema (`GraphitiClient`)

The cognitive memory layer is managed through `app/services/memory/graphiti_client.py`. It introduces a single specialized node label and two relationship types:

### 3.1 `:EpisodeMemory` Node Structure

```cypher
(:EpisodeMemory {
    id: 'e8b7d6c5-4321-4f0a-9876-543210abcdef',
    session_id: 'sess_1_20261103_014520',
    query: 'What were the corrective action items for the Chicago outage?',
    summary: 'The Chicago outage was mitigated by rolling back the v4.12 BSS billing adapter...',
    created_at: '2026-11-03T01:45:20.123456+00:00'
})
```

### 3.2 Overlay Relationships

1. **`:RECALLED` Relationship**:
   - Direction: `(:Person)-[:RECALLED {at: ISO8601_TIMESTAMP}]->(:EpisodeMemory)`
   - Meaning: Expresses that a specific user invoked and completed a search-and-answer interaction episode.
   - Purpose: Allows chronological ordering of a user's conversational timeline directly in FalkorDB.

2. **`:TOUCHED` Relationship**:
   - Direction: `(:EpisodeMemory)-[:TOUCHED]->(target)`
   - Meaning: Binds an interaction episode to the specific canonical entities (`:Person`, `:Project`, `:Document`, `:Decision`) referenced in the answer evidence.
   - Purpose: Enables one-hop traversals from an episode into corporate entities to resolve subsequent conversational shorthand.

---

## 4. Graph Construction & Ingestion Operations

Graph nodes and edges are populated using idempotent Cypher queries via `FalkorDBClient.query()` in `app/services/graph/`:

### 4.1 Document Enrichment Ingestion (`DocumentEnrichmentGraphService`)

When a document is parsed, `app/services/graph/document_enrichment_graph_service.py` executes:

```cypher
// Upsert Document Node
MERGE (d:Document {id: 'doc:' + $document_id})
ON CREATE SET d.title = $title, d.source_id = $source_id, d.source_system = $source_system
ON MATCH SET d.title = $title;

// Link Document to Owner Person
MATCH (p:Person {email: $owner_email}), (d:Document {id: 'doc:' + $document_id})
MERGE (p)-[:OWNS]->(d);

// Link Document to Scoped Project
MATCH (pr:Project {name: $project_name}), (d:Document {id: 'doc:' + $document_id})
MERGE (pr)-[:CONTAINS]->(d);

// Link Extracted Mentions
MATCH (d:Document {id: 'doc:' + $document_id}), (t:Team {name: $team_name})
MERGE (d)-[:MENTIONS]->(t);
```

### 4.2 Decision & Provenance Ingestion (`DecisionGraphService`)

When architectural decision records (ADRs) or retrospectives are ingested:

```cypher
// Upsert Decision Node
MERGE (dec:Decision {id: 'decision:' + $decision_id})
ON CREATE SET dec.title = $title, dec.status = $status, dec.project_id = $project_id;

// Link Decision to Source Document
MATCH (dec:Decision {id: 'decision:' + $decision_id}), (d:Document {id: 'doc:' + $source_doc_id})
MERGE (dec)-[:DERIVED_FROM]->(d);
```

### 4.3 Memory Overlay Persistence (`GraphitiClient`)

When an interaction completes in `app/services/memory/graphiti_client.py`:

```cypher
// 1. Create EpisodeMemory and link to Person
MATCH (p:Person {email: $user_email})
MERGE (e:EpisodeMemory {id: $episode_id})
ON CREATE SET e.session_id = $session_id,
              e.query = $query,
              e.summary = $summary,
              e.created_at = $timestamp_str
MERGE (p)-[:RECALLED {at: $timestamp_str}]->(e);

// 2. Link EpisodeMemory to touched canonical entities
MATCH (e:EpisodeMemory {id: $episode_id}), (target {id: $entity_id})
MERGE (e)-[:TOUCHED]->(target);
```

---

## 5. Runtime Graph Query Patterns

The codebase executes four primary Cypher traversal patterns:

### 5.1 Pre-Retrieval Shorthand Recall (`GraphitiClient.recall_recent_entities`)

Retrieves entities touched during the user's most recent interaction turns to expand pronoun-heavy queries:

```cypher
MATCH (p:Person {email: $user_email})-[r:RECALLED]->(e:EpisodeMemory)-[:TOUCHED]->(target)
RETURN e.query, labels(target)[0], target.id, target.name, target.title
ORDER BY e.created_at DESC
LIMIT 5;
```

### 5.2 1-Hop Neighborhood Expansion (`GraphRepository.get_related_entities`)

Discovers all immediate connections for a document to enrich LLM context with owners, teams, and projects:

```cypher
// Outgoing edges
MATCH (a {id: $entity_id})-[r]->(b)
RETURN type(r), b.id, labels(b), b.name, b.title;

// Incoming edges
MATCH (a)-[r]->(b {id: $entity_id})
RETURN type(r), a.id, labels(a), a.name, a.title;
```

### 5.3 Multi-Hop Decision Provenance (`ProvenanceService.get_decision_provenance`)

Traces the root evidence chain from a decision back to source documents, authors, and projects:

```cypher
MATCH (dec:Decision {id: $decision_id})-[:DERIVED_FROM]->(d:Document)
OPTIONAL MATCH (p:Person)-[:AUTHORED_BY|OWNS]->(d)
OPTIONAL MATCH (pr:Project)-[:CONTAINS]->(d)
RETURN dec.title, d.id, d.title, p.email, pr.name;
```

### 5.4 Graph-Native ABAC Authorization Verification (`PermissionResolver`)

Evaluates whether a user holds read clearance for a document through direct authorship, direct permissions, or team inheritance:

```cypher
// 1. Direct Ownership Check
MATCH (p:Person {email: $user_email})-[r:OWNS|AUTHORED_BY|CREATED_BY]->(d:Document {id: $doc_id})
RETURN count(r) > 0;

// 2. Team Membership Inheritance Check
MATCH (p:Person {email: $user_email})-[:MEMBER_OF]->(t:Team)-[r:OWNS|HAS_PERMISSION]->(d:Document {id: $doc_id})
RETURN count(r) > 0;
```

---

## 6. OpenCypher Execution & Visualization Adapter

In `app/api/v1/endpoints/graph.py`, FalkorDB results are transformed into standard node/edge visual payloads (`GraphQueryResponse`) to power UI spring-force canvases:
- **Read-Only Safety**: Queries containing mutation keywords (`CREATE`, `DELETE`, `SET`, `REMOVE`, `DROP`, `MERGE`) are rejected with HTTP 400.
- **Node-Edge Parsing**: 5-column standard returns (`labels(a)[0], a.id, type(r), labels(b)[0], b.id`) are mapped directly into `GraphNodeItem` and `GraphEdgeItem` collections.
- **User-Scoped Subgraphs**: The `/user-subgraph` endpoint evaluates role privileges: administrators query the top-level corporate core graph, while non-privileged users receive a restricted subgraph centered strictly on their own node, team, and direct assignments.

