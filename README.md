# MnemoGraph: Cognitive Temporal Memory & Governed Enterprise Knowledge Engine

[![Architecture: Multi-Tiered Cognitive Graph](https://img.shields.io/badge/Architecture-Dual--Layer%20Graph-blueviolet.svg)](#core-architectural-pillars)
[![Memory: Episodic + Semantic + Procedural](https://img.shields.io/badge/Memory-Episodic%20%7C%20Semantic%20%7C%20Procedural-0ea5e9.svg)](#the-tri-part-cognitive-memory-engine)
[![Governance: Graph-Native ABAC](https://img.shields.io/badge/Security-Graph--Native%20RBAC%2FABAC-emerald.svg)](#deterministic-security--governance)
[![Grounding: Multi-Hop Provenance](https://img.shields.io/badge/Provenance-Multi--Hop%20Verified-amber.svg)](#multi-hop-provenance--confidence-gating)

---

## Executive Overview

**MnemoGraph** is a cognitive enterprise knowledge platform that combines **graph databases, dense vector retrieval, and persistent temporal agent memory**. 

Modern enterprise AI systems suffer from three fundamental limitations:
1. **Stateless Amnesia**: LLMs treat every session in isolation, unable to maintain evolving context across turns or recall previous decisions, entities, and shorthand follow-up discussions.
2. **Hallucinatory Semantic Drift**: Standard Retrieval-Augmented Generation (RAG) blindly merges unstructured text chunks without structural relationship context, generating factually disconnected or unverifiable responses.
3. **Permission Blindness**: Generic vector search engines cannot enforce complex organizational hierarchies, project boundaries, or transitive role-based access controls before returning search results.

**MnemoGraph solves these challenges from first principles** by separating **canonical organizational truth** from **temporal agent memory**, enforcing strict access governance at the graph layer, and requiring multi-hop evidence validation for every generated answer.

---

## Core Architectural Pillars

```
                     +---------------------------------------------+
                     |            User & Agent Requests            |
                     +---------------------------------------------+
                                            |
                         [1] Pre-Retrieval Memory Expansion
                               (Pronouns, Entities, Episodes)
                                            v
                     +---------------------------------------------+
                     |         Graph-Native ABAC Boundary          |
                     |  Transitive Ownership & Clearance Filtering |
                     +---------------------------------------------+
                                            |
                    +-----------------------+-----------------------+
                    |                                               |
                    v                                               v
   +---------------------------------+             +---------------------------------+
   |      CANONICAL GRAPH LAYER      |             |       DENSE VECTOR LAYER        |
   |      (FalkorDB / OpenCypher)    |             |       (Qdrant & FastEmbed)      |
   |  • People, Teams, Projects      |             |  • Deep Semantic Embeddings     |
   |  • Documents, Decisions, Specs  |             |  • Segmented Structural Chunks  |
   |  • Immutable Business Truth     |             |  • Cosine Similarity Filtering  |
   +---------------------------------+             +---------------------------------+
                    |                                               |
                    +-----------------------+-----------------------+
                                            |
                               [2] Multi-Hop Graph Traversal
                                            v
                     +---------------------------------------------+
                     |     Evidence Ranker & Confidence Gating     |
                     |   Validates Provenance Chains & Citations   |
                     +---------------------------------------------+
                                            |
                               [3] Grounded Synthesis
                                            v
                     +---------------------------------------------+
                     |            Groq LLM Engine Layer            |
                     |     Deterministic Summarization Only        |
                     +---------------------------------------------+
                                            |
                               [4] Post-Search Dual Persistence
                                            v
                    +-----------------------------------------------+
                    |             TEMPORAL MEMORY OVERLAY           |
                    |           (Graphiti Engine on FalkorDB)       |
                    |  • :EpisodeMemory & :TOUCHED Edges            |
                    |  • Semantic Entity Evolution Across Turns     |
                    |  • Procedural Graph Patterns & Feedback Loops |
                    +-----------------------------------------------+
```

---

## The Tri-Part Cognitive Memory Engine

Unlike simple chat logs or vector caches, MnemoGraph implements a human-analogous **three-tier cognitive memory model**:

### 1. Episodic Memory (Temporal Continuity)
- Preserves the chronological trajectory of every agent and user conversation.
- Models every interaction as an `:EpisodeMemory` graph node linked directly to the canonical entities referenced during that exchange.
- Enables autonomous **anaphora and shorthand pronoun resolution**: asking *"What were the corrective action items for it?"* automatically traces back through recent episodes, extracts the incident identifier, and grounds the query without user re-prompting.

### 2. Semantic Memory (Entity & Relationship Evolution)
- Continuously extracts, normalizes, and connects named entities across independent sessions.
- Tracks interaction frequencies, evolving affinity scores, and cross-departmental references over time.
- Allows agents to dynamically understand how topics relate across disparate teams, projects, and architectural decisions.

### 3. Procedural Memory (Reusable Operational Patterns)
- Records verified graph traversal paths, generated Cypher execution templates, and evidence-gathering heuristics.
- Enables agents to share successful query strategies with each other, refining retrieval accuracy as the enterprise knowledge base scales.

---

## The Dual-Graph Paradigm

MnemoGraph maintains a strict architectural division between two distinct graph layers in FalkorDB:

| Layer | Responsibility | Persistence Policy | Access Governance |
| :--- | :--- | :--- | :--- |
| **Canonical Enterprise Graph** | Authoritative ground truth: People, Teams, Projects, Documents, Architectural Decision Records (ADRs), Incidents. | Permanent, versioned, synchronized with raw storage and relational databases. | Strict ABAC / RBAC. Scoped to verified organizational permissions. |
| **Cognitive Memory Overlay** | Experiential awareness: `:EpisodeMemory`, `:RECALLED`, and `:TOUCHED` relationships tracking user focus and session context. | Chronologically indexed, tenant/user-isolated, statefully evolving. | User/Session scoped. Private to the user or shared among designated agent teams. |

This separation ensures that an agent's memory never pollutes or alters authoritative enterprise facts, while still allowing the agent to remember every interaction.

---

## Deterministic Security & Governance

Security in MnemoGraph is **graph-native and enforced before retrieval**:
- **Attribute-Based Access Control (ABAC)**: Access levels (`READ`, `WRITE`, `ADMIN`) and security classifications (`Internal`, `Confidential`, `Restricted`) are evaluated at query time.
- **Transitive Lineage Filtering**: If an employee lacks clearance for a project or decision, all descendant document nodes, vector chunks, and relationship paths are pruned from the query graph before evidence is surfaced.
- **Tenant Isolation**: Complete logical and relational boundary enforcement prevents cross-tenant data leakage across PostgreSQL, FalkorDB, and Qdrant.

---

## Multi-Hop Provenance & Confidence Gating

MnemoGraph replaces probabilistic guesses with mathematically verifiable provenance:
- **Graph-Traversed Citations**: Every generated statement is backed by an explicit Cypher path connecting the document, author, decision, and project.
- **Confidence Gate**: A dedicated validation engine scores retrieved evidence based on relationship depth, vector cosine similarity, and source freshness.
- **No Hallucination Fallback**: When grounded facts do not exist in the enterprise graph, the system explicitly acknowledges the absence of information rather than fabricating answers.

---

## Key Functional Capabilities

- **Interactive Topology Visualizer**: Real-time spring-force canvas dynamically renders the authorized enterprise subgraph and highlights active citation paths.
- **Direct Multi-Format Ingestion**: Ingests `.pdf`, `.docx`, `.md`, `.txt`, `.json`, and `.csv` files into MinIO/S3, extracts structured sections and named entities, and synchronizes vectors and graph nodes.
- **Multi-Store Collection Governance**: Role-based management across relational databases, FalkorDB graph collections, Qdrant vector partitions, and object storage buckets.
- **Chronological Memory Timeline**: Full historical audit trail of past queries, confidence scores, grounded sources, and generated Cypher queries with instant recall.

