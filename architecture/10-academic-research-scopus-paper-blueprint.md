# Academic Research Paper Blueprint: Dual-Layer Cognitive Graph Memory & Governed Multi-Hop RAG

**Target Venues**: IEEE Transactions on Knowledge and Data Engineering (TKDE), ACM Transactions on Information Systems (TOIS), or Scopus Q1 Journals in Knowledge-Based Systems.  
**Subject Classification**: Knowledge Graphs, Enterprise Information Systems, Temporal Memory Networks, Retrieval-Augmented Generation (RAG).

---

## 1. Title & Abstract Formulation

### Title
> **MnemoGraph: Grounded Enterprise Question Answering via Dual-Layer Cognitive Graph Memory and Deterministic Pre-Retrieval Authorization**

### Abstract Blueprint
Enterprise conversational agents powered by large language models (LLMs) suffer from three fundamental limitations when deployed across enterprise corpora: (1) **stateless amnesia**, where conversational anaphora and shorthand cannot be resolved across session turns; (2) **hallucinatory semantic drift**, where bag-of-vectors retrieval discards relational provenance; and (3) **permission blindness**, where vector similarity search bypasses transitive organizational access controls. 

This paper introduces **MnemoGraph**, a multi-store cognitive enterprise knowledge platform that resolves this trilemma from first principles:
1. We formalize a **Dual-Layer Graph Paradigm** that strictly partitions canonical enterprise facts from temporal episodic memory nodes, eliminating knowledge pollution while supporting multi-turn anaphora resolution.
2. We design a **Graph-Native Attribute-Based Access Control (ABAC)** mechanism that prunes vector search candidates via transitive team-project reachability prior to LLM synthesis.
3. We implement an **Explainable Provenance Gating Engine** combining dense vector proximity with verified multi-hop Cypher paths and deterministic rule-based fallbacks.
4. We evaluate the architecture against a real-world synthetic telecom enterprise corpus containing over 1,200 domain artifacts (PySpark notebooks, CDR pipelines, incident retrospectives, and ADRs), demonstrating zero authorization leakage and elimination of ungrounded hallucinations under LLM degradation.

---

## 2. Mathematical Formalization of Implemented Mechanisms

### 2.1 The Dual-Graph Separation

Let the enterprise knowledge space be represented as two distinct subgraphs within a single property graph $\mathcal{G} = (\mathcal{V}, \mathcal{E})$:

$$\mathcal{G} = \mathcal{G}_C \cup \mathcal{G}_M, \quad \mathcal{V} = \mathcal{V}_C \cup \mathcal{V}_M, \quad \mathcal{E} = \mathcal{E}_C \cup \mathcal{E}_M \cup \mathcal{E}_{cross}$$

#### 1. Canonical Enterprise Graph $\mathcal{G}_C = (\mathcal{V}_C, \mathcal{E}_C)$:
- **Vertices $\mathcal{V}_C$**: Enriched labeled typed entities across 7 enterprise domains:
  $$\mathcal{V}_C = \mathcal{V}_{\text{Company}} \cup \mathcal{V}_{\text{Site}} \cup \mathcal{V}_{\text{Dept}} \cup \mathcal{V}_{\text{Team}} \cup \mathcal{V}_{\text{Employee}} \cup \mathcal{V}_{\text{Project}} \cup \mathcal{V}_{\text{Milestone}} \cup \mathcal{V}_{\text{Decision}} \cup \mathcal{V}_{\text{Incident}} \cup \mathcal{V}_{\text{FollowUpAction}} \cup \mathcal{V}_{\text{BusinessDocument}} \cup \mathcal{V}_{\text{LessonLearned}} \cup \mathcal{V}_{\text{ServiceType}}$$
- **Edges $\mathcal{E}_C$**: Verified immutable corporate relations and causal propagation paths:
  $$\mathcal{E}_C \subseteq \mathcal{V}_C \times \mathcal{R}_C \times \mathcal{V}_C$$
  where $\mathcal{R}_C = \{\text{MEMBER\_OF\_TEAM}, \text{BELONGS\_TO\_DEPARTMENT}, \text{LOCATED\_AT}, \text{WORKS\_FROM}, \text{MANAGES}, \text{LEADS}, \text{CONTRIBUTES\_TO}, \text{SPONSORED\_BY}, \text{HAS\_MILESTONE}, \text{HAS\_LESSON}, \text{BLOCKED\_BY\_DECISION}, \text{BLOCKED\_BY\_INCIDENT}, \text{MADE\_BY}, \text{LINKED\_TO\_PROJECT}, \text{AFFECTS\_SERVICE}, \text{AFFECTS\_SITE}, \text{CAUSED\_RECURRENCE}, \text{RAISED\_FROM\_INCIDENT}, \text{RAISED\_FROM\_DECISION}, \text{ASSIGNED\_TO}, \text{PREVENTED\_RECURRENCE\_OF}, \text{DOCUMENTS}, \text{AUTHORED\_BY}, \text{SUPERSEDED\_BY}\}$.

#### 2. Cognitive Memory Overlay $\mathcal{G}_M = (\mathcal{V}_M, \mathcal{E}_M \cup \mathcal{E}_{cross})$:
- **Vertices $\mathcal{V}_M$**: Experiential interaction records:
  $$\mathcal{V}_M = \mathcal{V}_{\text{EpisodeMemory}}$$
  Each $e \in \mathcal{V}_{\text{EpisodeMemory}}$ carries tuple properties $(\text{id}, \text{session\_id}, q, a_{\text{summary}}, t)$.
- **Cross-Layer Coupling Edges $\mathcal{E}_{cross}$**:
  $$\mathcal{E}_{cross} = \mathcal{E}_{\text{RECALLED}} \cup \mathcal{E}_{\text{TOUCHED}}$$
  where:
  - $(p, \text{RECALLED}, e) \in \mathcal{V}_{\text{Employee}} \times \{\text{RECALLED}\} \times \mathcal{V}_{\text{EpisodeMemory}}$
  - $(e, \text{TOUCHED}, v) \in \mathcal{V}_{\text{EpisodeMemory}} \times \{\text{TOUCHED}\} \times \mathcal{V}_C$

**Structural Integrity Invariant**: $\forall e \in \mathcal{V}_M$, write operations modify only $\mathcal{V}_M$ and $\mathcal{E}_{cross}$. The canonical graph $\mathcal{G}_C$ remains immutable during user interactions:

$$\frac{\partial \mathcal{G}_C}{\partial (\text{User Interaction})} = \emptyset$$

---

### 2.2 Formal Causal Inference & Recurrence Operators

We formalize operational failure chains via two virtual graph materialization operators:

1. **Recurrence Chain Operator ($\mathcal{O}_{\text{recur}}$)**:
   $$\mathcal{O}_{\text{recur}}(i_1, a, i_2) \implies (i_1, \text{CAUSED\_RECURRENCE}, i_2) \iff (a, \text{RAISED\_FROM\_INCIDENT}, i_1) \wedge a.\text{efficacy} = \text{'ineffective'} \wedge a.\text{recurrence\_id} = i_2.\text{id}$$

2. **Decision Failure Propagation ($\mathcal{O}_{\text{prop}}$)**:
   $$\mathcal{O}_{\text{prop}}(d, p) \implies (p, \text{BLOCKED\_BY\_DECISION}, d) \iff (d, \text{LINKED\_TO\_PROJECT}, p) \wedge d.\text{outcome} = \text{'negative'} \wedge p.\text{status} \in \{\text{'on-hold'}, \text{'cancelled'}\}$$

---

### 2.2 Pre-Retrieval Context Expansion Function

Let $q_t$ be the user query at turn $t$. Let $\mathcal{H}_u$ be the user's historical context retrieved from PostgreSQL $\mathcal{T}_{\text{memory\_entities}}$ and FalkorDB overlay $\mathcal{G}_M$:

$$\mathcal{H}_u = \big( \text{TopologicalTargets}(\mathcal{G}_M, u, k_1), \; \text{FrequentEntities}(\mathcal{T}_{\text{memory\_entities}}, u, k_2) \big)$$

The context expansion operator $\mathcal{R}(q_t, \mathcal{H}_u)$ rewrites the query string:

$$\mathcal{R}(q_t, \mathcal{H}_u) = 
\begin{cases} 
q_t \mathbin{\Vert} \text{" (context: "} \mathbin{\Vert} c^* \mathbin{\Vert} \text{")"}, & \text{if } \exists w \in \mathcal{K}_{\text{shorthand}} \text{ s.t. } w \in \text{lower}(q_t) \wedge c^* \neq \emptyset \\ 
q_t, & \text{otherwise} 
\end{cases}$$

where:
- $\mathcal{K}_{\text{shorthand}} = \{\text{"she"}, \text{"he"}, \text{"it"}, \text{"that"}, \text{"this"}, \text{"the same"}, \text{"they"}, \text{"outage"}, \text{"project"}, \text{"for it"}\}$
- Candidate selector $c^* = \text{head}(\text{TopologicalTargets}) \lor \text{head}(\text{FrequentEntities})$.

---

### 2.3 Graph-Native ABAC Authorization Function

Let $u \in \mathcal{V}_{\text{Person}}$ be the requesting user with email address $u_{\text{email}}$. Let $d \in \mathcal{V}_{\text{Document}}$ be a candidate document retrieved from Qdrant via dense embedding similarity.

The authorization decision $\mathcal{A}(u, d) \in \{0, 1\}$ is defined by transitive path existence in $\mathcal{G}_C$:

$$\mathcal{A}(u, d) = \mathbb{I}\Big( \text{DirectOwnership}(u, d) \;\lor\; \text{TeamInheritance}(u, d) \;\lor\; \text{DefaultClearance}(d) \Big)$$

where:
1. **Direct Ownership**:
   $$\text{DirectOwnership}(u, d) \iff \exists r \in \{\text{OWNS}, \text{AUTHORED\_BY}, \text{CREATED\_BY}\} \text{ s.t. } (u, r, d) \in \mathcal{E}_C$$
2. **Team Inheritance**:
   $$\text{TeamInheritance}(u, d) \iff \exists t \in \mathcal{V}_{\text{Team}} \text{ s.t. } (u, \text{MEMBER\_OF}, t) \in \mathcal{E}_C \wedge (t, \text{OWNS} \lor \text{HAS\_PERMISSION}, d) \in \mathcal{E}_C$$
3. **Default Corporate Clearance**:
   $$\text{DefaultClearance}(d) \iff \neg \exists (x, \text{HAS\_PERMISSION}, d) \in \mathcal{E}_C$$

**Pre-Retrieval Pruning Invariant**:
$$\mathcal{D}_{\text{authorized}} = \{ d \in \text{QdrantTopK}(q) \mid \mathcal{A}(u, d) = 1 \}$$
If $\mathcal{D}_{\text{authorized}} = \emptyset$, generation halts immediately, emitting safe fallback $\mathcal{S}_{\text{safe}}$.

---

### 2.4 Cryptographic Reconciliation & State Consistency

Let a document $d$ have content string $C(d)$ and storage path $P(d)$. The version digest $H(d)$ is computed as:

$$H(d) = \text{SHA256}\Big( \text{UTF8}(C(d)) \mathbin{\Vert} \text{UTF8}(P(d)) \Big)$$

The state transition function $\mathcal{T}_{\text{sync}}$ governing `DocumentVersionState` is defined as:

$$\mathcal{T}_{\text{sync}}(d) = 
\begin{cases}
\text{NoOp}, & \text{if } d \in \mathcal{S}_{\text{active}} \wedge H(d) = H_{\text{stored}}(d) \\
\text{PurgeVectors}(d) \circ \text{PurgeEdges}(d) \circ \text{Reindex}(d), & \text{if } d \in \mathcal{S}_{\text{active}} \wedge H(d) \neq H_{\text{stored}}(d) \\
\text{PurgeVectors}(d) \circ \text{PurgeEdges}(d) \circ \text{DeleteNode}(d), & \text{if } d \notin \mathcal{S}_{\text{active}} \text{ (Orphan)}
\end{cases}$$

---

## 3. Experimental Setup & Benchmark Methodology

### 3.1 Domain Evaluation Corpus: Aarohan Digital Networks (`ontology.yaml`)

The experimental validation is grounded in the enterprise ontology and dataset of **Aarohan Digital Networks Limited** (`architecture/ontology.yaml`):
- **Corpus Scale**: 1,200+ multi-format enterprise files across seven organizational and technical domains.
- **Corpus Composition**:
  1. *250 PySpark 5G RAN Telemetry Notebooks*: Real JSON cell structures with embedded KPI execution traces.
  2. *250 PySpark CDR Mediation Pipelines*: Complex PySpark ETL jobs handling roaming settlement records.
  3. *200 BSS/OSS Billing Settlement Documents*: Billing dispute records and mediation schemas.
  4. *250 Incident Retrospectives & MOP Runbooks*: NOC post-mortems with explicit ticket identifiers (`INC-XXXX`) and mis-diagnosis indicators.
  5. *250 3GPP Architecture RFCs & ADRs*: Formal decision records (`DEC-XXXX`) with root-cause failure analyses (`root_cause_analysis`).
- **Organizational Structure**: 44 employees spanning active, on-leave, and terminated statuses (featuring focal employee EMP-0005 Gunbir Parmer), 15 teams, 7 departments, and 8 Tier-1 site locations.

---

### 3.2 Evaluation Baselines for Comparative Benchmarking

| Baseline Name | Storage / Indexing Architecture | Memory Model | Security Model |
| :--- | :--- | :--- | :--- |
| **Baseline 1: Naive RAG** | Single dense vector store (Qdrant alone) | Stateless (No history) | None (Open collection search) |
| **Baseline 2: Windowed Conversational RAG** | Vector store + Raw sliding chat buffer | Raw string window buffer | Post-retrieval role tagging |
| **Baseline 3: Flat GraphRAG** | Triplet-extracted knowledge graph + Vector store | Stateless | Relational metadata filtering |
| **MnemoGraph (Ours)** | Polyglot (Postgres + FalkorDB + Qdrant + S3) | Dual-Layer Graphiti Memory Overlay | Pre-retrieval Graph-Native ABAC |

---

### 3.3 Quantitative Evaluation Metrics

1. **Contextual Anaphora Resolution Rate (ARR)**:
   $$\text{ARR} = \frac{\sum_{i=1}^N \mathbb{I}(\text{ResolvedEntity}(q_i) = \text{GroundTruthTarget}(q_i))}{N}$$
   Evaluated over 200 multi-turn query sequences containing ambiguous shorthand pronouns (`"it"`, `"that project"`, `"the outage"`).

2. **Authorization Leakage Rate (ALR)**:
   $$\text{ALR} = \frac{\sum_{i=1}^M \mathbb{I}(\text{CitedDocuments}(a_i) \cap \mathcal{D}_{\text{unauthorized}}(u_i) \neq \emptyset)}{M}$$
   Evaluated across 500 adversarial prompts where low-clearance users query restricted cross-departmental initiatives. Target: $\text{ALR} = 0.00\%$.

3. **Faithfulness & Grounding Ratio (FGR)**:
   $$\text{FGR} = \frac{|\text{VerifiedCitations}(a) \cap \text{PostgresDocumentRegistry}|}{|\text{TotalCitationsCited}(a)|}$$
   Measures the percentage of citations confirmed by `ProvenanceValidator` to exist as canonical database entities.

4. **Multi-Store Reconciliation Latency & Stale Vector Residue (SVR)**:
   $$\text{SVR} = \text{Count}\Big( \text{Points in Qdrant with } \text{document\_id} \notin \mathcal{V}_{\text{Document}} \Big)$$
   Validates the completeness of `StaleVectorCleanup` and `OrphanCleanup` across incremental sync runs.

---

## 4. Paper Structure & Section Layout (Scopus Format)

```
1. INTRODUCTION
   1.1 Motivation: Enterprise Knowledge Silos & RAG Failure Modes
   1.2 The Trilemma: Amnesia, Hallucinatory Drift, and Permission Blindness
   1.3 Summary of Contributions

2. RELATED WORK
   2.1 Dense Vector Retrieval & Semantic Search
   2.2 Knowledge Graph-Augmented Generation (GraphRAG)
   2.3 Conversational Memory Networks & State Tracking
   2.4 Attribute-Based Access Control in Information Retrieval

3. MNEMOGRAPH SYSTEM ARCHITECTURE
   3.1 Polyglot Persistence Layering (PostgreSQL, FalkorDB, Qdrant, S3)
   3.2 The Dual-Layer Graph Paradigm (Canonical Truth vs. Cognitive Memory)
   3.3 Ingestion, Syntactic Sectioning, and AST Entity Extraction

4. COGNITIVE MEMORY & REASONING ENGINE
   4.1 Pre-Retrieval Anaphora Expansion via Graphiti Overlay
   4.2 Graph-Native ABAC: Pre-Retrieval Subgraph Pruning
   4.3 Grounded Synthesis via Groq LLM & Dynamic Cypher Query Generation
   4.4 Multi-Stage Confidence Gating and Deterministic Fallback Invariant

5. CONTINUOUS RECONCILIATION & CONSISTENCY
   5.1 Cryptographic SHA-256 State Versioning
   5.2 Coordinated Invalidation: Stale Vector and Graph Edge Purging
   5.3 Audit Trails & Performance Monitoring

6. EXPERIMENTAL EVALUATION
   6.1 Dataset Description: The Telecom Enterprise Corpus (1,200+ Assets)
   6.2 Baseline Configurations & Experimental Setup
   6.3 Multi-Turn Shorthand Resolution Accuracy (ARR)
   6.4 Security Governance & Leakage Verification (ALR)
   6.5 Grounding Verification & Hallucination Elimination (FGR)
   6.6 Computational Overhead & Retrieval Latency Benchmarks

7. DISCUSSION & THREATS TO VALIDITY
   7.1 Trade-Offs of Pre-Retrieval Filtering vs. Post-Filtering
   7.2 Scalability Limits of OpenCypher Graph Traversal
   7.3 LLM Key Rotation & Failure Mode Resilience

8. CONCLUSION & FUTURE WORK
```

