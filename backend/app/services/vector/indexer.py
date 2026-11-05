from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any
from starlette.concurrency import run_in_threadpool
from qdrant_client.http.models import FieldCondition, Filter, MatchValue, PointStruct

from app.services.vector.embeddings import embed_query, embed_texts
from app.services.vector.qdrant_client import QdrantService

logger = logging.getLogger(__name__)


class StructureAwareChunker:
    """
    UKGOE Step 3.1: Structure-Aware Chunking Engine:
    A) Structured Entity Rendering (fluent natural language).
    B) Document Section Boundary Chunking (headings, breadcrumbs, 350w sliding windows).
    C) Graph Relationship Triplet Batching.
    """

    @staticmethod
    def render_entity(entity_class: str, properties: dict[str, Any], neighbors: list[dict[str, Any]] | None = None) -> str:
        """
        Translates structured entity properties and 1-hop relationships into
        rich natural language text to maximize dense vector semantic retrieval.
        """
        props = dict(properties or {})
        ent_id = props.get("id") or props.get("entity_id", "")
        name = props.get("name") or props.get("full_name") or props.get("title") or ent_id

        parts = [f"{entity_class} {name} (ID: {ent_id})."]

        if entity_class == "Person":
            if props.get("full_name") and props.get("full_name") != name:
                parts.append(f"Full name: {props.get('full_name')}.")
            if props.get("current_role_id") or props.get("role"):
                parts.append(f"Role: {props.get('current_role_id') or props.get('role')}.")
            if props.get("current_group_id") or props.get("department"):
                parts.append(f"Department: {props.get('current_group_id') or props.get('department')}.")
            if props.get("contact_email") or props.get("email"):
                parts.append(f"Contact email: {props.get('contact_email') or props.get('email')}.")
            if props.get("skills"):
                skills_val = props["skills"]
                skills_str = ", ".join(skills_val) if isinstance(skills_val, list) else str(skills_val)
                parts.append(f"Skills: {skills_str}.")
            if props.get("employment_status"):
                parts.append(f"Employment status: {props.get('employment_status')}.")
            if props.get("start_date"):
                parts.append(f"Hired date: {props.get('start_date')}.")

        elif entity_class == "Project":
            if props.get("status"):
                parts.append(f"Status: {props.get('status')}.")
            if props.get("start_date"):
                parts.append(f"Start date: {props.get('start_date')}.")
            if props.get("planned_end_date"):
                parts.append(f"Target completion: {props.get('planned_end_date')}.")
            if props.get("outcome_summary"):
                parts.append(f"Outcome: {props.get('outcome_summary')}.")

        elif entity_class == "Incident":
            if props.get("severity"):
                parts.append(f"Severity: {props.get('severity')}.")
            if props.get("start_datetime"):
                parts.append(f"Occurred: {props.get('start_datetime')}.")
            if props.get("resolution_datetime"):
                parts.append(f"Resolved: {props.get('resolution_datetime')}.")
            if props.get("confirmed_cause"):
                parts.append(f"Confirmed root cause: {props.get('confirmed_cause')}.")
            if props.get("initial_suspected_cause"):
                parts.append(f"Initial suspected cause: {props.get('initial_suspected_cause')}.")
            if props.get("is_mis_diagnosed"):
                parts.append("Misdiagnosis occurred: true.")
            if props.get("description"):
                parts.append(f"Details: {props.get('description')}.")

        elif entity_class == "Decision":
            if props.get("decision_type"):
                parts.append(f"Type: {props.get('decision_type')}.")
            if props.get("decision_date"):
                parts.append(f"Date: {props.get('decision_date')}.")
            if props.get("outcome"):
                parts.append(f"Outcome: {props.get('outcome')}.")
            if props.get("rationale"):
                parts.append(f"Rationale: {props.get('rationale')}.")
            if props.get("root_cause_analysis"):
                parts.append(f"Root cause analysis: {props.get('root_cause_analysis')}.")

        elif entity_class == "Task":
            if props.get("status"):
                parts.append(f"Status: {props.get('status')}.")
            if props.get("priority"):
                parts.append(f"Priority: {props.get('priority')}.")
            if props.get("due_date"):
                parts.append(f"Due date: {props.get('due_date')}.")
            if props.get("effectiveness"):
                parts.append(f"Remediation effectiveness: {props.get('effectiveness')}.")
            if props.get("description"):
                parts.append(f"Description: {props.get('description')}.")

        elif entity_class == "Lesson":
            if props.get("description"):
                parts.append(f"Learning: {props.get('description')}.")
            if props.get("recurrence_count"):
                parts.append(f"Recurrence count: {props.get('recurrence_count')}.")

        else:
            # Universal fallback for remaining classes
            for k, v in props.items():
                if k not in ["id", "entity_id", "name", "full_name", "title", "property_history", "provenance_sources"] and v:
                    parts.append(f"{k.replace('_', ' ').capitalize()}: {v}.")

        # Append 1-Hop Graph Neighbors context if available
        if neighbors:
            neighbor_strs = []
            for n in neighbors:
                rel = n.get("relation", "CONNECTED_TO")
                lbl = n.get("label", "Entity")
                nid = n.get("id", "")
                neighbor_strs.append(f"{rel} {lbl} ({nid})")
            if neighbor_strs:
                parts.append(f"Connected graph relationships: {'; '.join(neighbor_strs)}.")

        return " ".join(parts)

    @staticmethod
    def chunk_document_sections(
        raw_text: str,
        doc_title: str = "Document",
        max_words: int = 350,
        overlap: int = 50,
        min_tokens: int = 30,
    ) -> list[dict[str, Any]]:
        """
        Splits text along logical Markdown/section boundaries with breadcrumb context.
        Sub-chunks sections exceeding max_words using a sliding window.
        """
        if not raw_text or not raw_text.strip():
            return []

        # Split on markdown headings
        heading_pattern = r"(?=(?:^|\n)#{1,4}\s+)"
        raw_sections = [s.strip() for s in re.split(heading_pattern, raw_text) if s.strip()]

        chunks = []
        for sec in raw_sections:
            lines = sec.split("\n", 1)
            first_line = lines[0].strip()
            heading = first_line.lstrip("#").strip() if first_line.startswith("#") else "General Overview"
            body = lines[1].strip() if len(lines) > 1 else first_line

            words = body.split()
            if not words:
                continue

            breadcrumb = f"[{doc_title} > {heading}]: "

            if len(words) <= max_words:
                if len(words) >= min_tokens or len(raw_sections) == 1:
                    chunks.append({
                        "heading": heading,
                        "text": breadcrumb + body,
                        "word_count": len(words),
                    })
            else:
                # Sliding window sub-chunking
                i = 0
                while i < len(words):
                    window = " ".join(words[i : i + max_words])
                    chunks.append({
                        "heading": heading,
                        "text": breadcrumb + window,
                        "word_count": len(window.split()),
                    })
                    i += max_words - overlap

        return chunks

    @staticmethod
    def chunk_graph_triplets(
        source_id: str,
        source_label: str,
        triplets: list[dict[str, Any]],
        max_per_chunk: int = 10,
    ) -> list[str]:
        """Batches graph relationships into coherent semantic paragraphs."""
        if not triplets:
            return []

        sentences = []
        for t in triplets:
            rel = t.get("relation", "CONNECTED_TO")
            tgt_lbl = t.get("label", "Entity")
            tgt_id = t.get("id", "")
            sentences.append(f"{source_label} ({source_id}) {rel} {tgt_lbl} ({tgt_id}).")

        chunks = []
        for i in range(0, len(sentences), max_per_chunk):
            batch = sentences[i : i + max_per_chunk]
            chunks.append(" ".join(batch))
        return chunks


class VectorIndexer:
    """
    Universal Knowledge Graph Vector Indexer (UKGOE Part 3):
    1. Structure-Aware Chunking for entities, documents, and graph triplets.
    2. Exact 15-field payload enrichment with 1-hop FalkorDB neighbors.
    3. Deterministic UUID5 point IDs for idempotent writes and IR-09 cascade updates.
    """

    def __init__(self, qdrant_service: QdrantService | None = None):
        self.qdrant = qdrant_service or QdrantService()
        self.chunker = StructureAwareChunker()

    def build_15_field_payload(
        self,
        document_id: str | None,
        entity_id: str | None,
        entity_class: str,
        chunk_index: int,
        text: str,
        metadata: dict[str, Any] | None = None,
        graph_neighbors: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Constructs the canonical 15-field Qdrant payload."""
        meta = metadata or {}
        now_iso = datetime.now(timezone.utc).isoformat()

        return {
            "document_id": document_id or meta.get("document_id"),
            "entity_id": entity_id or meta.get("entity_id"),
            "entity_class": entity_class or meta.get("entity_class", "DocumentSection"),
            "chunk_index": chunk_index,
            "text": text,
            "graph_neighbors": graph_neighbors or meta.get("graph_neighbors", []),
            "classification": meta.get("classification", "Internal"),
            "department": meta.get("department", "Engineering"),
            "author_id": meta.get("author_id"),
            "project_id": meta.get("project_id"),
            "created_at": meta.get("created_at", now_iso),
            "completeness_score": float(meta.get("completeness_score", 1.0)),
            "validation_status": meta.get("validation_status", "valid"),
            "causal_chain_depth": int(meta.get("causal_chain_depth", 0)),
            "recurrence_risk": bool(meta.get("recurrence_risk", False)),
            "data_quality_grade": meta.get("data_quality_grade", "A"),
        }

    async def index_document(
        self,
        document_id: str,
        text: str,
        metadata: dict[str, Any] | None = None,
        doc_title: str = "Document",
        chunk_size: int = 350,
        overlap: int = 50,
    ) -> int:
        """
        Structure-aware chunking and indexing for documents into Qdrant.
        """
        meta = metadata or {}
        chunks = self.chunker.chunk_document_sections(
            raw_text=text,
            doc_title=doc_title,
            max_words=chunk_size,
            overlap=overlap,
        )
        if not chunks:
            # Fallback if text is flat
            chunks = [{"heading": "General", "text": text, "word_count": len(text.split())}] if text.strip() else []

        if not chunks:
            return 0

        def _index():
            chunk_texts = [c["text"] for c in chunks]
            vectors = embed_texts(chunk_texts)
            points = []

            for idx, (chunk_data, vector) in enumerate(zip(chunks, vectors)):
                # Deterministic UUID5 for idempotent writes
                point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{document_id}_{idx}"))
                payload = self.build_15_field_payload(
                    document_id=document_id,
                    entity_id=meta.get("entity_id"),
                    entity_class="DocumentSection",
                    chunk_index=idx,
                    text=chunk_data["text"],
                    metadata=meta,
                )

                points.append(
                    PointStruct(
                        id=point_id,
                        vector=vector,
                        payload=payload,
                    )
                )

            self.qdrant.client.upsert(
                collection_name=self.qdrant.collection_name,
                points=points,
            )
            return len(points)

        return await run_in_threadpool(_index)

    async def index_entity(
        self,
        entity_id: str,
        entity_class: str,
        properties: dict[str, Any],
        metadata: dict[str, Any] | None = None,
        graph_neighbors: list[dict[str, Any]] | None = None,
    ) -> str:
        """
        Translates structured entity properties into natural language and
        upserts as a Qdrant point with 1-hop graph neighbors.
        """
        meta = metadata or {}
        rendered_text = self.chunker.render_entity(entity_class, properties, neighbors=graph_neighbors)

        def _index() -> str:
            vector = embed_texts([rendered_text])[0]
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{entity_id}_0"))

            payload = self.build_15_field_payload(
                document_id=meta.get("document_id"),
                entity_id=entity_id,
                entity_class=entity_class,
                chunk_index=0,
                text=rendered_text,
                metadata=meta,
                graph_neighbors=graph_neighbors,
            )

            point = PointStruct(
                id=point_id,
                vector=vector,
                payload=payload,
            )

            self.qdrant.client.upsert(
                collection_name=self.qdrant.collection_name,
                points=[point],
            )
            return point_id

        return await run_in_threadpool(_index)

    async def search(
        self,
        query: str,
        limit: int = 10,
        filter_dict: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Semantic search over vector embeddings with fast payload pre-filtering.
        """
        def _search():
            q_vector = embed_query(query)
            qdrant_filter = None

            if filter_dict:
                conditions = []
                for k, v in filter_dict.items():
                    if v is not None:
                        conditions.append(
                            FieldCondition(key=k, match=MatchValue(value=v))
                        )
                if conditions:
                    qdrant_filter = Filter(must=conditions)

            res = self.qdrant.client.query_points(
                collection_name=self.qdrant.collection_name,
                query=q_vector,
                query_filter=qdrant_filter,
                limit=limit,
                with_payload=True,
            )
            results = []
            for hit in res.points:
                results.append({
                    "id": hit.id,
                    "score": hit.score,
                    "payload": hit.payload or {},
                })
            return results

        return await run_in_threadpool(_search)
