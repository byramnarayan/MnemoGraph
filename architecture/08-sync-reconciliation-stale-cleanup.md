# Architecture Specification: 08 Sync Reconciliation & Stale Cleanup

## 1. Subsystem Scope & Architectural Invariant

In enterprise environments, knowledge is continuously edited, renamed, moved, and deleted. When documents undergo updates across source workspaces (such as Databricks), multi-store RAG systems face severe **cross-engine synchronization drift**:
1. **Dangling Graph Edges**: FalkorDB relationships (`REFERENCES`, `MENTIONS`, `DERIVED_FROM`) reference documents that no longer exist or possess outdated contents.
2. **Ghost Vector Chunks**: Outdated embeddings persist in Qdrant, causing vector search to surface deprecated facts or duplicate chunk matches.
3. **Redundant Re-indexing**: Blindly re-embedding an entire document corpus upon every ingestion cycle wastes computational resources.

MnemoGraph enforces a **Cryptographically Verified Reconciliation Invariant**:
> **Invariant**: No document is re-embedded or re-parsed unless its cryptographic content checksum (SHA-256) differs from its recorded baseline. When a modification or deletion is confirmed, all associated vector points and graph edges are atomically evicted before new state is registered.

---

## 2. Component Collaboration Architecture

The reconciliation subsystem is implemented in `app/services/reconciliation/` and coordinated by `SyncReconciler`:

```
                    +───────────────────────────────────────────────+
                    |                SyncReconciler                 |
                    |    (Job Lifecycle & Sync Loop Coordinator)    |
                    +───────────────────────────────────────────────+
                                           │
         ┌───────────────────┬─────────────┴─────────────┬───────────────────┐
         ▼                   ▼                           ▼                   ▼
+─────────────────+ +─────────────────+         +─────────────────+ +─────────────────+
| ChangeDetector  | |VersionReconciler|         |  OrphanCleanup  | |StaleEdgeCleaner |
| (SHA-256 Hashing| |(State Transitions         |(Document Deletion|(FalkorDB Edge   |
| & Diff Engine)  | | in DB)          |         | & Detach Purge) | | Pruning)        |
+─────────────────+ +─────────────────+         +─────────────────+ +─────────────────+
                                                         │
                                                         ▼
                                                +─────────────────+
                                                |StaleVectorClean |
                                                |(Qdrant Payload  |
                                                | Field Purge)    |
                                                +─────────────────+
```

| Class | Source File | Core Responsibility in Codebase |
| :--- | :--- | :--- |
| `SyncReconciler` | `app/services/reconciliation/sync_reconciler.py` | Top-level job orchestrator handling changed, moved, and deleted document loops. |
| `ChangeDetector` | `app/services/reconciliation/change_detector.py` | Computes SHA-256 digests over content bytes and file paths; evaluates change types. |
| `VersionReconciler` | `app/services/reconciliation/version_reconciler.py` | Queries and transitions `DocumentVersionState` records in PostgreSQL. |
| `OrphanCleanup` | `app/services/reconciliation/orphan_cleanup.py` | Marks documents deleted in DB, executes `DETACH DELETE` in FalkorDB, and triggers vector eviction. |
| `StaleEdgeCleaner` | `app/services/reconciliation/stale_edge_cleaner.py` | Deletes incoming and outgoing edges for mutated or purged documents in FalkorDB. |
| `StaleVectorCleanup`| `app/services/vector/stale_vector_cleanup.py` | Deletes vector points matching `payload.document_id` from Qdrant collection. |

---

## 3. Cryptographic State Tracking (`DocumentVersionState`)

Version state is tracked in PostgreSQL via `app/models/sync_reconciliation_job.py`:

```sql
CREATE TABLE document_version_state (
    id VARCHAR(36) PRIMARY KEY,
    document_id VARCHAR(100) UNIQUE NOT NULL,
    source_id VARCHAR(255) NOT NULL,
    workspace_id VARCHAR(100),
    version_hash VARCHAR(64) NOT NULL,     -- SHA-256 hex digest
    previous_hash VARCHAR(64),
    last_synced_at TIMESTAMPTZ DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ DEFAULT NOW(),
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 3.1 Hash Computation (`ChangeDetector.compute_hash`)
The checksum incorporates both raw file content and canonical path:
```python
sha = hashlib.sha256()
if isinstance(content, str):
    sha.update(content.encode("utf-8", errors="replace"))
else:
    sha.update(content)
if path:
    sha.update(path.encode("utf-8", errors="replace"))
return sha.hexdigest()
```

### 3.2 Change Evaluation Logic
- **`is_new`**: No prior `stored_hash` exists $\rightarrow$ Schedule full parse and vector index.
- **`content_changed`**: `current_hash != stored_hash` $\rightarrow$ Evict stale vectors/edges, re-enrich, and re-index.
- **`moved`**: `current_hash == stored_hash` but `path != stored_path` $\rightarrow$ Update path in metadata without re-computing expensive embeddings.
- **`none`**: Hashes match $\rightarrow$ Update `last_seen_at` timestamp and skip re-indexing.

---

## 4. End-to-End Reconciliation Workflow (`SyncReconciler.run_reconciliation`)

When a synchronization job is triggered (via API or cron), `run_reconciliation()` performs a 4-phase audit:

```
[Start Reconciliation Job]
           │
           ▼
[Phase 1: Initialize Sync Job Audit Record]
  Insert into `sync_reconciliation_jobs` (status="running", mode="incremental")
           │
           ▼
[Phase 2: Source Deletion Audit]
  For each Document in DB:
  Is doc.source_id present in active_source_ids?
           │
           ├────────────────────────────┐
           ▼ (No -> Deleted at Source)   ▼ (Yes -> Still Active)
  [Execute OrphanCleanup]       [Phase 3: Content Change Audit]
  • Set is_deleted = True         • Read raw bytes from DocumentStore
  • Delete FalkorDB node/edges    • Compute current SHA-256
  • Purge Qdrant vectors          • Compare against DocumentVersionState
  • Increment docs_deleted                  │
                                 ┌──────────┴──────────┐
                                 ▼ (Changed)           ▼ (Unchanged)
                        [Targeted Re-index]         [Skip Document]
                        • Purge old vectors           • Increment checked_count
                        • Purge old edges
                        • Force re-enrichment
                        • Index new vectors
                        • Increment changed_count
                                 │
                                 ▼
[Phase 4: Finalize Job Record & Commit Metrics]
  Update `sync_reconciliation_jobs`
  (status="completed", completed_at=now, checked, changed, deleted, edges_removed, vectors_removed)
```

---

## 5. Deletion & Orphan Purge Mechanics (`OrphanCleanup`)

When a document is removed from the external source system, `OrphanCleanup.mark_deleted_and_purge()` guarantees that all references across all stores are eliminated:

### 5.1 Relational Tombstone
Updates `document_version_state` setting `is_deleted = True`.

### 5.2 FalkorDB Node & Edge Elimination
Executes through `ReconciliationGraphService`:
```cypher
// Remove all incoming and outgoing edges
MATCH (d:Document {id: $doc_id})-[r]-()
DELETE r;

// Delete Document node
MATCH (d:Document {id: $doc_id})
DELETE d;
```

### 5.3 Qdrant Vector Eviction
`StaleVectorCleanup.delete_document_vectors()` executes a targeted collection filter:
```python
client.delete(
    collection_name="databricks_knowledge_chunks",
    points_selector=models.FilterSelector(
        filter=models.Filter(
            must=[models.FieldCondition(key="document_id", match=models.MatchValue(value=document_id))]
        )
    )
)
```

---

## 6. Targeted Modification Re-indexing

When `ChangeDetector` identifies that an existing document has mutated:
1. **Eviction Before Upsert**: Old vector chunks and relational AST sections are removed first to prevent chunk count inflation when a modified document is shorter than its previous revision.
2. **AST Section Re-parsing**: `EnrichmentService.enrich_document(doc.id, db, raw_text=content, force_reparse=True)` clears previous `document_sections`, `extracted_entities`, and `mentions` before generating fresh structured records.
3. **Graph Relationship Refresh**: `DocumentEnrichmentGraphService` recreates updated `REFERENCES` and `MENTIONS` edges reflecting the new file contents.
4. **Vector Chunk Indexing**: `VectorIndexer.index_document()` splits the updated text into 400-word windows and upserts fresh 384-dimensional FastEmbed vectors to Qdrant.

---

## 7. Audit & Job Monitoring APIs (`app/api/v1/endpoints/reconciliations.py`)

The reconciliation subsystem exposes endpoints for triggering and inspecting synchronization jobs:

```
POST /api/v1/reconciliations/reconcile
Request:  {"connector_id": "databricks-conn-01", "mode": "incremental"}
Response: SyncReconciliationJob object with initial status "running"

GET /api/v1/reconciliations/jobs
Response: List of all past reconciliation jobs with summary metrics

GET /api/v1/reconciliations/jobs/{job_id}
Response: Detailed breakdown:
  - documents_checked: 1250
  - documents_changed: 14
  - docs_deleted: 3
  - stale_edges_removed: 42
  - vector_entries_removed: 87
  - status: "completed"

POST /api/v1/reconciliations/cleanup-stale
Request:  {"document_id": "doc-uuid-string"}
Response: {"edges_removed": 6, "vectors_removed": 12}
```

