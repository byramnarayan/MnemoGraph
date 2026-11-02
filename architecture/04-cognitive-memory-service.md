# Architecture Specification: 04 Cognitive Memory Service

## 1. Subsystem Mission & Architectural Responsibility

The **Cognitive Memory Subsystem** (`app/services/memory/` and `app/api/v1/endpoints/memory.py`) solves conversational amnesia and context drift across multi-turn user sessions.

Instead of storing unindexed raw chat strings, it maintains a structured, human-analogous **three-tier cognitive model**:
1. **Episodic Memory**: Chronological event trace of interactions, grounded citations, confidence scores, and Cypher queries stored in PostgreSQL (`agent_episodes`) and FalkorDB (`:EpisodeMemory`).
2. **Semantic Memory**: Recalled entities and evolving affinity frequencies stored in PostgreSQL (`memory_entities`) and connected across turns via FalkorDB (`:TOUCHED`).
3. **Procedural Memory**: Generated read-only Cypher query patterns (`cypher_query`) captured per episode, recording verified retrieval paths across graph structures.

---

## 2. Component Structure & Class Collaboration

The subsystem is implemented as four collaborating classes orchestrated by `MemoryService`:

```
                 +───────────────────────────────────────────────+
                 |                 MemoryService                 |
                 |      (Unified Facade & Session Coordinator)   |
                 +───────────────────────────────────────────────+
                                         |
                     +-------------------+-------------------+
                     |                                       |
                     v                                       v
+─────────────────────────────────────────+ +─────────────────────────────────────────+
|           MemoryRecallService           | |           MemoryWriteService            |
|       (Pre-Retrieval Context Expansion) | |      (Post-Retrieval Dual-Persistence)  |
+─────────────────────────────────────────+ +─────────────────────────────────────────+
                     |                                       |
                     +-------------------+-------------------+
                                         |
                                         v
                         +───────────────────────────────+
                         |        GraphitiClient         |
                         |   (FalkorDB Overlay Driver)   |
                         +───────────────────────────────+
```

| Class | Source File | Core Responsibility in Codebase |
| :--- | :--- | :--- |
| `MemoryService` | `app/services/memory/memory_service.py` | Top-level entry point exposing `pre_search_recall` and `post_search_record`. |
| `MemoryRecallService` | `app/services/memory/memory_recall_service.py` | Extracts recent topics and entities, detects shorthand keywords, and rewrites queries. |
| `MemoryWriteService` | `app/services/memory/memory_write_service.py` | Executes atomic writes to PostgreSQL and dispatches overlay node creation in FalkorDB. |
| `GraphitiClient` | `app/services/memory/graphiti_client.py` | Executes OpenCypher queries to create `:EpisodeMemory`, `:RECALLED`, and `:TOUCHED` graph elements. |

---

## 3. Pre-Retrieval Context Expansion (`MemoryRecallService`)

When a user submits a search query in `app/api/v1/endpoints/search.py`, `MemoryService.pre_search_recall()` is executed prior to any vector search or graph retrieval:

```
[Incoming User Query]
         │
         ▼
[Step 1: PostgreSQL Entity Frequency Recall]
  SELECT entity_type, entity_value, normalized_value, frequency_count
  FROM memory_entities WHERE user_id = :uid
  ORDER BY last_seen_at DESC LIMIT 6;
         │
         ▼
[Step 2: FalkorDB Graphiti Overlay Recall]
  MATCH (p:Person {email: user_email})-[r:RECALLED]->(e:EpisodeMemory)-[:TOUCHED]->(target)
  RETURN e.query, labels(target)[0], target.id, target.name, target.title
  ORDER BY e.created_at DESC LIMIT 4;
         │
         ▼
[Step 3: Keyword Anaphora Evaluation]
  Check lowercase query for:
  ["she", "he", "it", "that", "this", "the same", "they", "outage", "project", "for it"]
         │
         ├─────────────────────────────────────────┐
         ▼ (Keyword Match & Candidate Found)       ▼ (No Match)
[Query Rewriting & Expansion]               [Pass-Through Query]
  effective_query =                           effective_query = original_query
  "{query} (context: {recent_candidate})"     has_memory_context = False
  has_memory_context = True
```

### 3.1 Shorthand Keyword Resolution Mechanics

The query rewriter targets specific pronouns and domain shorthand:
- **Heuristic Triggers**: `"she"`, `"he"`, `"it"`, `"that"`, `"this"`, `"the same"`, `"they"`, `"outage"`, `"project"`, `"for it"`.
- **Candidate Selection Priority**:
  1. Primary Candidate: `recent_topics[0]` (the canonical target node name returned from FalkorDB's `:TOUCHED` overlay).
  2. Fallback Candidate: `recent_entities[0]["value"]` (the most recently referenced entity string from PostgreSQL's `memory_entities`).
- **Rewriting Format**:
  If a user asks *"What were the corrective action items for it?"* following a session touching the Chicago network event, the engine generates:
  ```text
  What were the corrective action items for it? (context: Chicago BSS Mediation Outage)
  ```
  This expanded query is then supplied to FastEmbed and Qdrant, preventing vector drift.

---

## 4. Post-Retrieval Dual-Persistence (`MemoryWriteService`)

Following answer generation and confidence verification in `app/services/answer_service.py`, `MemoryService.post_search_record()` commits the interaction across dual datastores.

### 4.1 PostgreSQL Relational Logging

The write operation executes four transactional SQL steps in PostgreSQL:

1. **Episode Log Insert**:
   ```sql
   INSERT INTO agent_episodes (
       id, user_id, tenant_id, session_id, query_text, answer_text,
       confidence_score, grounded_sources, provenance_chain, cypher_query, created_at
   ) VALUES (
       :id, :user_id, 'telcosphere', :session_id, :query, :answer,
       :conf, :sources_json, :prov_json, :cypher, :now
   );
   ```

2. **Session Thread Upsert**:
   - Checks `memory_sessions` for an existing `session_id`.
   - If missing: inserts a new session record with `summary = query[:120]`, `created_at = now`, `last_activity_at = now`.
   - If present: updates `last_activity_at = now` and refreshes `summary = query[:120]`.

3. **Entity Affinity Increments**:
   - Iterates through all cited document titles extracted from `grounded_sources`.
   - Checks `memory_entities` for `(user_id, normalized_value)`.
   - If present: updates `frequency_count = frequency_count + 1` and `last_seen_at = now`.
   - If missing: inserts a new record with initial `frequency_count = 1`.

4. **Transaction Commit**: Commits all relational changes or rolls back on exception.

### 4.2 FalkorDB Graph Overlay Persistence (`GraphitiClient`)

Simultaneously, `GraphitiClient.add_episode_memory()` links the episode into the property graph:

```cypher
// 1. Create EpisodeMemory node and bind to Person persona
MATCH (p:Person {email: $user_email})
MERGE (e:EpisodeMemory {id: $episode_id})
ON CREATE SET e.session_id = $session_id,
              e.query = $clean_query,
              e.summary = $clean_summary,
              e.created_at = $timestamp_str
MERGE (p)-[:RECALLED {at: $timestamp_str}]->(e);

// 2. Bind EpisodeMemory to canonical entities touched during synthesis
MATCH (e:EpisodeMemory {id: $episode_id}), (target {id: $target_entity_id})
MERGE (e)-[:TOUCHED]->(target);
```

*Referenced entities include verified canonical IDs: `person:{email}`, `project:{slug}`, and `doc:{id}`.*

---

## 5. REST API Endpoints (`app/api/v1/endpoints/memory.py`)

The memory engine exposes five HTTP endpoints protected by `CurrentUser` JWT authentication:

### 5.1 `GET /api/v1/memory/history`
- **Query Parameter**: `order` (`asc` for chronological ascending, `desc` for newest first; default `asc`).
- **Response**: Array of episode objects containing:
  - `id`: Episode UUID
  - `session_id`: Session thread identifier
  - `query`: User's original prompt
  - `answer`: Grounded response text
  - `confidence`: Evaluated confidence score (0.0 to 1.0)
  - `sources`: Deserialized list of cited evidence documents
  - `provenance`: Multi-hop relation path dictionary
  - `cypher_query`: Cypher query associated with this episode
  - `created_at`: ISO 8601 UTC timestamp

### 5.2 `GET /api/v1/memory/history/{episode_id}`
- Retrieves detailed audit metadata for an individual episode, scoped strictly to the authenticated `current_user.id`.

### 5.3 `GET /api/v1/memory/sessions`
- Returns all conversation threads belonging to the current user from `memory_sessions`, sorted by `last_activity_at DESC`.

### 5.4 `GET /api/v1/memory/sessions/{session_id}`
- Returns all chronological episodes belonging to a specific conversation thread.

### 5.5 `POST /api/v1/memory/recall-test`
- Accepts `{"query": "string"}`.
- Diagnostic endpoint executing `pre_search_recall()` without invoking vector search or the LLM.
- Returns `recent_entities`, `recent_topics`, `expanded_query`, and `has_memory_context`.

