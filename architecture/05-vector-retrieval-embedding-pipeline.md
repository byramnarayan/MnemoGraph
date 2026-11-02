# Architecture Specification: 05 Vector Retrieval & Embedding Pipeline

## 1. Subsystem Scope & Design Principles

The **Vector Retrieval Subsystem** (`app/services/vector/`) provides semantic similarity matching over unstructured text chunks derived from notebooks, architectural specifications, runbooks, and documents.

To avoid performance bottlenecks and data corruption, the pipeline follows four concrete implementation principles:
1. **Lightweight In-Process Dense Embeddings**: Eliminates external network latency and rate limits for embedding generation by executing `FastEmbed` (`BAAI/bge-small-en-v1.5`) directly within worker threadpools.
2. **Deterministic Point Hashing**: Computes RFC 4122 UUIDv5 identifiers from document IDs and chunk indices to guarantee idempotent indexing and avoid duplicate points upon re-indexing.
3. **Overlapping Sliding Window Partitioning**: Preserves semantic continuity across paragraph boundaries using word-based sliding chunk intervals.
4. **Targeted Field Invalidation**: Encodes `document_id` as an indexed payload keyword to permit instantaneous set-based point deletion during document updates without mutating unrelated vectors.

---

## 2. Component Architecture & Class Map

```
                  +───────────────────────────────────────────────+
                  |                 VectorIndexer                 |
                  |     (Chunking, Batch Embedding, Qdrant I/O)   |
                  +───────────────────────────────────────────────+
                                         │
                     ┌───────────────────┴───────────────────┐
                     ▼                                       ▼
  +─────────────────────────────────────+ +─────────────────────────────────────+
  |              FastEmbed              | |            QdrantService            |
  |     (BAAI/bge-small-en-v1.5)        | |      (Collection Init & Client)     |
  +─────────────────────────────────────+ +─────────────────────────────────────+
                     │                                       │
                     └───────────────────┬───────────────────┘
                                         ▼
                  +───────────────────────────────────────────────+
                  |              StaleVectorCleanup               |
                  |     (Filter-Based Payload Vector Eviction)    |
                  +───────────────────────────────────────────────+
```

| Component | Source File | Core Responsibility |
| :--- | :--- | :--- |
| `embeddings.py` | `app/services/vector/embeddings.py` | Lazy-loads `TextEmbedding` singleton; exposes `embed_texts()` and `embed_query()`. |
| `QdrantService` | `app/services/vector/qdrant_client.py` | Connects to remote Qdrant or in-memory instance; creates collection and keyword payload indexes. |
| `VectorIndexer` | `app/services/vector/indexer.py` | Executes sliding-window chunking, computes embeddings, generates UUIDv5 points, and runs similarity queries. |
| `VectorSearchService` | `app/services/vector/search_service.py` | Orchestrates similarity retrieval with optional workspace and project metadata filters. |
| `ProvenanceEnricher` | `app/services/vector/provenance_enricher.py` | Queries relational ADRs and FalkorDB graph neighbors to enrich retrieval payloads. |
| `StaleVectorCleanup` | `app/services/vector/stale_vector_cleanup.py` | Counts and purges vector points by matching `payload.document_id`. |

---

## 3. Text Chunking Algorithm (`chunk_text`)

Document chunking is implemented in `app/services/vector/indexer.py` via word-level window sliding:

```python
def chunk_text(text: str, chunk_size: int = 400, overlap: int = 50) -> list[str]:
    if not text:
        return []
    words = text.split()
    if len(words) <= chunk_size:
        return [text]

    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i : i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
    return chunks
```

### Operational Parameters:
- **Default Ingestion Window**: 400 words per chunk.
- **Overlap Stride**: 50 words shared between consecutive chunks.
- **Boundary Handling**: If total text length $\le 400$ words, the string is indexed as a single point with `chunk_index = 0` to preserve holistic context.

---

## 4. Dense Vector Generation (`FastEmbed`)

Embeddings are generated via `app/services/vector/embeddings.py`:
- **Model**: `BAAI/bge-small-en-v1.5` (configured via `settings.embedding_model`).
- **Vector Dimensionality**: 384 dimensions (`settings.embedding_dimension = 384`).
- **Execution Mode**: Runs locally via ONNX Runtime inside `starlette.concurrency.run_in_threadpool`, ensuring FastAPI's async event loop is never blocked by matrix multiplications.
- **Singleton Lifecycle**: `get_embedding_model()` lazy-loads a single `TextEmbedding` instance into memory on the first request.

---

## 5. Qdrant Collection Configuration & Deterministic Indexing

### 5.1 Collection Initialization (`QdrantService.ensure_collection`)

When the backend initializes, `QdrantService` inspects the engine:
```python
client.create_collection(
    collection_name="databricks_knowledge_chunks",
    vectors_config=models.VectorParams(
        size=384,
        distance=models.Distance.COSINE
    )
)
```
In addition, a **payload field index** is created on `document_id` (`FieldType.KEYWORD`) to enable high-performance filtering during deletions.

### 5.2 Deterministic Point UUID Generation

To ensure that indexing operations are idempotent and re-indexing the same document does not produce orphan duplicates, point IDs are computed using RFC 4122 UUIDv5 hashing under the DNS namespace:

```python
point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{document_id}_{chunk_index}"))
```

### 5.3 Point Structure & Payload Schema

Points are dispatched to Qdrant via batch upsert as `qdrant_client.http.models.PointStruct` objects:

```python
PointStruct(
    id=point_id,
    vector=vector_384d,
    payload={
        "document_id": document_id,
        "chunk_index": idx,
        "text": chunk_text,
        "title": metadata.get("title"),
        "source_url": metadata.get("source_url"),
        "source_type": metadata.get("source_type", "Document"),
        "workspace_id": metadata.get("workspace_id"),
        "project_id": metadata.get("project_id"),
        "path": metadata.get("path")
    }
)
```

---

## 6. Runtime Semantic Similarity Search

Retrieval is executed in `VectorIndexer.search()` and consumed by `AnswerService`:

```python
def _search():
    q_vector = embed_query(query)
    res = client.query_points(
        collection_name="databricks_knowledge_chunks",
        query=q_vector,
        limit=limit,
        with_payload=True
    )
    return [{"id": hit.id, "score": hit.score, "payload": hit.payload} for hit in res.points]
```

### Retrieval Dynamics:
1. **Candidate Multiplier**: `AnswerService.generate_answer()` requests `limit * 3` candidates from Qdrant.
2. **Deduplication by Document**: Because a single document may yield multiple chunk hits, hits are iterated in score order and deduplicated by `document_id`.
3. **Permission Interception**: Each hit is checked against `PermissionResolver.can_user_access()` before entering the final candidate evidence set.

---

## 7. Stale Vector Cleanup & Invalidation (`StaleVectorCleanup`)

When a document is modified or deleted, `app/services/vector/stale_vector_cleanup.py` executes a targeted purge:

```python
# 1. Count matching points
count_res = client.count(
    collection_name="databricks_knowledge_chunks",
    count_filter=models.Filter(
        must=[models.FieldCondition(key="document_id", match=models.MatchValue(value=document_id))]
    )
)

# 2. Evict points matching document_id
if count_res.count > 0:
    client.delete(
        collection_name="databricks_knowledge_chunks",
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[models.FieldCondition(key="document_id", match=models.MatchValue(value=document_id))]
            )
        )
    )
```

This guarantees zero vector residue when documents are updated or pruned by the reconciliation orchestrator.

