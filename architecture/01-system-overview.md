# Architecture Specification: 01 System Overview

## 1. Executive Summary & Purpose

**MnemoGraph** is a governed, multi-store knowledge and memory platform built with FastAPI, PostgreSQL, FalkorDB, Qdrant, and S3-compatible object storage. 

The system directly addresses three concrete failure modes present in naive Retrieval-Augmented Generation (RAG) architectures:
1. **Stateless Conversational Amnesia**: Generic LLM interfaces fail to resolve anaphoric pronouns and implicit conversational context across session turns.
2. **Topological Disconnect & Ungrounded Hallucinations**: Standard RAG flattens documents into unstructured text chunks, discarding the relational provenance between authors, teams, specifications, and architectural decisions.
3. **Permission Blindness**: Dense vector indexes lack relational authorization boundaries, risking the retrieval and synthesis of documents beyond a caller's organizational clearance.

To resolve these challenges without over-engineering or speculative abstractions, the codebase implements:
- A **Dual-Layer Graph Paradigm** in FalkorDB that strictly separates immutable canonical enterprise facts from temporal episodic memory nodes.
- A **Pre-Retrieval Memory Expansion Hook** that resolves conversational shorthand (`"it"`, `"she"`, `"that outage"`) against prior session entities before querying storage engines.
- A **Graph-Native Access Control Layer** that prunes inaccessible documents and relational subgraphs via ownership and team inheritance before evidence synthesis.
- A **Multi-Store Invalidation and Reconciliation Subsystem** that monitors SHA-256 version hashes and evicts stale vectors and graph edges upon document mutation or deletion.

---

## 2. High-Level Subsystem Topology

The runtime architecture is organized across five decoupled infrastructure layers:

```
                                  +---------------------------------------------+
                                  |         FastAPI REST Layer (/api/v1)        |
                                  |   (Auth, Search, Graph, Memory, Ingestion)   |
                                  +---------------------------------------------+
                                                         |
                   +-------------------------------------+-------------------------------------+
                   |                                     |                                     |
                   v                                     v                                     v
+-------------------------------------+ +-------------------------------------+ +-------------------------------------+
|        Memory Engine Subsystem      | |      Retriever & Security Subsystem | |    Reconciliation & Sync Subsystem  |
|  • Pre-Search Shorthand Expansion   | |  • FastEmbed Vector Embedding       | |  • SHA-256 State Change Detection |
|  • PostgreSQL Session & Entity Log  | |  • Qdrant Dense Similarity Search   | |  • Orphan Node & Edge Purging     |
|  • FalkorDB :EpisodeMemory Graph    | |  • Graph-Native ABAC Filtering      | |  • Stale Vector Chunk Cleanup     |
+-------------------------------------+ +-------------------------------------+ +-------------------------------------+
                   |                                     |                                     |
                   +-------------------------------------+-------------------------------------+
                                                         |
                                                         v
                                  +---------------------------------------------+
                                  |        Synthesis & Validation Subsystem     |
                                  |  • Groq LLM (Round-Robin Key Rotation)      |
                                  |  • Provenance Validator & Confidence Gate   |
                                  |  • Deterministic Grounded Fallback          |
                                  +---------------------------------------------+
```

---

## 3. Polyglot Storage Architecture & Roles

The system uses four distinct datastores, each fulfilling an explicit, non-overlapping storage responsibility:

| Datastore | Technology & Client | Core Domain Responsibility in Codebase |
| :--- | :--- | :--- |
| **Relational Database** | PostgreSQL (Neon-compatible) via `SQLAlchemy 2.0` (async) | Primary system of record for users, permissions, document metadata, section breakdowns, extracted entities, synchronization jobs, and episodic chat logs. |
| **Property Graph Database** | FalkorDB via `falkordb` Python client | Canonical enterprise topology (Persons, Teams, Projects, Documents, Decisions) and Graphiti temporal overlay (`:EpisodeMemory`, `:RECALLED`, `:TOUCHED`). |
| **Dense Vector Database** | Qdrant via `qdrant-client` | Vector similarity search over segmented document chunks embedded using `FastEmbed` (`BAAI/bge-small-en-v1.5`, 384 dimensions). |
| **Object Storage** | S3 / MinIO via `aioboto3` & `boto3` | Immutable storage of raw source files (PDF, DOCX, Markdown, PySpark notebooks, JSON, CSV) and avatar image files. |

---

## 4. End-to-End Search & Answering Life Cycle

The primary operational flow is implemented in `app/api/v1/endpoints/search.py` and `app/services/answer_service.py`. Every query executes in five deterministic stages:

```
[User Query]
     │
     ▼
[Stage 1: Pre-Retrieval Memory Expansion]
  ├─ Fetch recent entities from PostgreSQL `memory_entities`
  ├─ Query FalkorDB for recently touched `:EpisodeMemory` nodes
  └─ If shorthand keywords detected ("she", "it", "that", "this"), expand query text
     │
     ▼
[Stage 2: Vector Search & Candidate Generation]
  ├─ Embed expanded query using FastEmbed (`BAAI/bge-small-en-v1.5`)
  └─ Search Qdrant collection (`databricks_knowledge_chunks`) for top `limit * 3` candidates
     │
     ▼
[Stage 3: Graph-Native ABAC & Neighborhood Resolution]
  ├─ Deduplicate hits by `document_id`
  ├─ Evaluate `PermissionResolver.can_user_access(user_email, doc_id)` via FalkorDB
  ├─ Prune unauthorized document candidates from retrieval list
  └─ Expand 1-hop graph neighborhood for authorized hits (extract people, teams, projects, paths)
     │
     ▼
[Stage 4: Synthesis & Validation Gating]
  ├─ Assemble context-grounded prompt via `PromptBuilder`
  ├─ Invoke Groq LLM (`openai/gpt-oss-120b`) with rotating API keys (fallback to template if offline)
  ├─ Parse structured JSON (`answer_text`, `confidence`, optional `graph_query`)
  ├─ Validate citations in PostgreSQL (`ProvenanceValidator`)
  └─ Pass through `ConfidenceGate`; if score < threshold, emit safe fallback response
     │
     ▼
[Stage 5: Post-Search Dual-Store Persistence]
  ├─ Insert record into PostgreSQL `agent_episodes`
  ├─ Upsert session state into PostgreSQL `memory_sessions`
  ├─ Update entity encounter frequencies in PostgreSQL `memory_entities`
  └─ Create `:EpisodeMemory` node in FalkorDB and link to canonical entities with `:TOUCHED`
```

---

## 5. Ingestion, Parsing & Enrichment Life Cycle

Document processing is handled across `app/services/storage/`, `app/services/parsers/`, and `app/services/enrichment/`:

1. **Storage Ingestion (`DocumentStore`)**:
   - Files uploaded directly or synced from external systems (such as Databricks) are stored in S3/MinIO under hashed keys.
   - A `DocumentMetadata` and `DocumentVersion` record is persisted in PostgreSQL.
2. **Structural Chunking & Section Parsing (`SectionParser`)**:
   - Documents are broken down into semantically typed sections: `heading`, `paragraph`, `code`, `sql`, `table`, and `list`.
   - Each section tracks character offsets (`source_start`, `source_end`) and display sequence order (`order_index`).
3. **Entity & Reference Extraction**:
   - `EntityExtractor` detects named entities (`Person`, `Team`, `Project`, `Ticket`, `Decision`, `Meeting`, `Artifact`) with confidence scores.
   - `ProjectReferenceExtractor` and `DecisionMentionExtractor` map explicit references to existing projects and ADRs.
   - `SQLParser` and `TableParser` extract structured schema elements from embedded code blocks.
4. **Graph & Vector Synchronization**:
   - Extracted entities and structural linkages are synced to FalkorDB via `DocumentEnrichmentGraphService` using `REFERENCES` and `MENTIONS` edges.
   - Text chunks are passed to `VectorIndexer`, embedded via FastEmbed, and upserted to Qdrant with deterministic UUIDs (`uuid5(NAMESPACE_DNS, f"{document_id}_{chunk_index}")`).

---

## 6. Security & Authorization Architecture

Access control is graph-native and enforced prior to LLM synthesis:
- **Hierarchical Inheritance**: Permissions cascade downward through organizational containers: `Workspace` $\rightarrow$ `Project` $\rightarrow$ `Document`.
- **Identity Evaluation**: A user's read access is validated by `PermissionResolver` by checking:
  1. Direct author or creator edge (`OWNS`, `AUTHORED_BY`, `CREATED_BY`).
  2. Direct user permission grant (`HAS_PERMISSION`).
  3. Team membership grant (`(User)-[:MEMBER_OF]->(Team)-[:OWNS|HAS_PERMISSION]->(Document)`).
  4. Explicit `permission_policy` records registered in PostgreSQL.
- **Fail-Safe Behavior**: If a document has explicit access policies and the caller lacks transitive clearance, the document is excluded from the retrieval candidate pool.

---

## 7. Multi-Store Consistency & Reconciliation Architecture

Because data resides simultaneously across PostgreSQL, FalkorDB, and Qdrant, state divergence is mitigated by `SyncReconciler` (`app/services/reconciliation/`):
- **Version Tracking**: `DocumentVersionState` stores the current and previous SHA-256 hashes of every ingested document.
- **Selective Re-indexing**: Documents whose hashes have not changed are skipped during incremental synchronization runs.
- **Stale Vector Purging**: When a document is modified or deleted, `StaleVectorCleanup` removes all points matching `document_id` from Qdrant before new chunks are written.
- **Orphan Edge Elimination**: `StaleEdgeCleaner` prunes disconnected graph edges in FalkorDB, preventing dead citations and broken relation paths.
- **Job Auditing**: Every synchronization cycle records its start time, finish time, checked count, changed count, deleted count, and edge/vector removal metrics in `sync_reconciliation_jobs`.

---

## 8. Concrete Technology Stack & Configuration

Every component reflects exact backend configuration dependencies defined in `pyproject.toml` and `app/core/config.py`:

```
Backend Framework:      FastAPI 0.115+
ASGI Server:            Uvicorn
Relational ORM:         SQLAlchemy 2.0 (AsyncSession, asyncpg/psycopg)
Graph Engine:           FalkorDB (falkordb Python SDK, OpenCypher)
Vector Database:        Qdrant (qdrant-client)
Embeddings:             FastEmbed (BAAI/bge-small-en-v1.5, 384 dimensions)
LLM Provider:           Groq API (openai/gpt-oss-120b, 3-key round-robin rotation)
Object Storage:         S3 / MinIO (aioboto3, boto3)
Security / Auth:        OAuth2 Password Bearer, JWT (HS256), pwdlib (Argon2/Bcrypt)
Event Loop Policy:      WindowsSelectorEventLoopPolicy (applied conditionally on win32)
```

