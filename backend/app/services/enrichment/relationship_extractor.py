from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.services.enrichment.entity_extractor import UniversalEntity

logger = logging.getLogger(__name__)


@dataclass
class UniversalRelationship:
    source_id: str
    target_id: str
    relationship_type: str
    confidence: float
    context: str
    source_document_id: str
    extracted_at: datetime = datetime.now(timezone.utc)
    is_inferred: bool = False
    properties: dict[str, Any] = field(default_factory=dict)


class RelationshipExtractor:
    """
    Universal Relationship Taxonomy Engine (UKGOE Step 1.3):
    Extracts directed, typed edges across 6 core categories:
    1. Structural: MANAGES, MEMBER_OF, PART_OF, LOCATED_AT, HELD_ROLE, OPERATES
    2. Operational: LEADS, CONTRIBUTES_TO, ASSIGNED_TO, DEPENDS_ON, IMPLEMENTS, AFFECTS
    3. Causal: CAUSED_BY, CAUSED_RECURRENCE, UNBLOCKED_BY, PREVENTED_BY, DERIVED_FROM, OVERRIDES
    4. Knowledge: AUTHORED_BY, DOCUMENTS, SUPERSEDED_BY, SUPPORTS, CONTRADICTS, GENERALIZES
    5. Temporal: PRECEDED_BY, TRIGGERED, OCCURRED_DURING, RESOLVED_BY
    6. Semantic: SIMILAR_TO, MENTIONED_IN, TAGGED_WITH
    """

    # Universal Relationship Matching Patterns
    PATTERNS = [
        # Operational
        (re.compile(r"\b([A-Z][a-zA-Z0-9_\-]+)\s+(?:leads|leading|headed\s+by|owner\s+of)\s+([A-Z][a-zA-Z0-9_\-]+)\b", re.I), "LEADS", 0.95),
        (re.compile(r"\b([A-Z][a-zA-Z0-9_\-]+)\s+(?:contributes\s+to|worked\s+on)\s+([A-Z][a-zA-Z0-9_\-]+)\b", re.I), "CONTRIBUTES_TO", 0.90),
        (re.compile(r"\b([A-Z][a-zA-Z0-9_\-]+)\s+(?:assigned\s+to|owned\s+by)\s+([A-Z][a-zA-Z0-9_\-]+)\b", re.I), "ASSIGNED_TO", 0.95),
        (re.compile(r"\b([A-Z][a-zA-Z0-9_\-]+)\s+(?:depends\s+on|blocked\s+by|requires)\s+([A-Z][a-zA-Z0-9_\-]+)\b", re.I), "DEPENDS_ON", 0.95),
        (re.compile(r"\b([A-Z][a-zA-Z0-9_\-]+)\s+(?:implements|adopts|executes)\s+([A-Z][a-zA-Z0-9_\-]+)\b", re.I), "IMPLEMENTS", 0.90),
        (re.compile(r"\b([A-Z][a-zA-Z0-9_\-]+)\s+(?:affects|impacts|degraded)\s+([A-Z][a-zA-Z0-9_\-]+)\b", re.I), "AFFECTS", 0.90),

        # Causal
        (re.compile(r"\b([A-Z][a-zA-Z0-9_\-]+)\s+(?:caused\s+by|due\s+to|result\s+of|triggered\s+by)\s+([A-Z][a-zA-Z0-9_\-]+)\b", re.I), "CAUSED_BY", 0.95),
        (re.compile(r"\b([A-Z][a-zA-Z0-9_\-]+)\s+(?:unblocked\s+by|rescued\s+by)\s+([A-Z][a-zA-Z0-9_\-]+)\b", re.I), "UNBLOCKED_BY", 0.90),
        (re.compile(r"\b([A-Z][a-zA-Z0-9_\-]+)\s+(?:prevented\s+by|mitigated\s+by)\s+([A-Z][a-zA-Z0-9_\-]+)\b", re.I), "PREVENTED_BY", 0.90),
        (re.compile(r"\b([A-Z][a-zA-Z0-9_\-]+)\s+(?:derived\s+from|extracted\s+from)\s+([A-Z][a-zA-Z0-9_\-]+)\b", re.I), "DERIVED_FROM", 0.90),
        (re.compile(r"\b([A-Z][a-zA-Z0-9_\-]+)\s+(?:overrides|supersedes|replaces)\s+([A-Z][a-zA-Z0-9_\-]+)\b", re.I), "OVERRIDES", 0.95),

        # Structural
        (re.compile(r"\b([A-Z][a-zA-Z0-9_\-]+)\s+(?:member\s+of|belongs\s+to\s+team|in\s+group)\s+([A-Z][a-zA-Z0-9_\-]+)\b", re.I), "MEMBER_OF", 0.95),
        (re.compile(r"\b([A-Z][a-zA-Z0-9_\-]+)\s+(?:manages|reports\s+to)\s+([A-Z][a-zA-Z0-9_\-]+)\b", re.I), "MANAGES", 0.95),
        (re.compile(r"\b([A-Z][a-zA-Z0-9_\-]+)\s+(?:operates|maintains|runs)\s+([A-Z][a-zA-Z0-9_\-]+)\b", re.I), "OPERATES", 0.90),

        # Temporal
        (re.compile(r"\b([A-Z][a-zA-Z0-9_\-]+)\s+(?:preceded\s+by|occurred\s+after)\s+([A-Z][a-zA-Z0-9_\-]+)\b", re.I), "PRECEDED_BY", 0.85),
        (re.compile(r"\b([A-Z][a-zA-Z0-9_\-]+)\s+(?:resolved\s+by|fixed\s+by)\s+([A-Z][a-zA-Z0-9_\-]+)\b", re.I), "RESOLVED_BY", 0.95),
    ]

    def extract_relationships(
        self,
        text: str,
        document_id: str,
        entities: list[UniversalEntity],
    ) -> list[UniversalRelationship]:
        """
        Extracts relationships connecting entities mentioned in text.
        """
        relationships: list[UniversalRelationship] = []
        entity_map = {ent.label.lower(): ent for ent in entities}
        entity_id_map = {ent.entity_id: ent for ent in entities}

        # 1. Pattern-based Extraction
        for pattern, rel_type, base_conf in self.PATTERNS:
            for match in pattern.finditer(text):
                src_raw = match.group(1).strip()
                tgt_raw = match.group(2).strip()
                context_str = match.group(0).strip()[:120]

                src_ent = entity_map.get(src_raw.lower())
                tgt_ent = entity_map.get(tgt_raw.lower())

                src_id = src_ent.entity_id if src_ent else f"unresolved:{src_raw.lower()}"
                tgt_id = tgt_ent.entity_id if tgt_ent else f"unresolved:{tgt_raw.lower()}"

                # Confidence adjustment if both entities are known
                conf = base_conf if (src_ent and tgt_ent) else round(base_conf * 0.8, 2)

                relationships.append(
                    UniversalRelationship(
                        source_id=src_id,
                        target_id=tgt_id,
                        relationship_type=rel_type,
                        confidence=conf,
                        context=context_str,
                        source_document_id=document_id,
                    )
                )

        # 2. Document Knowledge Links (Every entity mentioned is connected to the Document)
        doc_node_id = f"doc:{document_id}"
        for ent in entities:
            # Document -> DOCUMENTS -> Entity
            relationships.append(
                UniversalRelationship(
                    source_id=doc_node_id,
                    target_id=ent.entity_id,
                    relationship_type="DOCUMENTS",
                    confidence=1.0,
                    context=f"Document references {ent.label}",
                    source_document_id=document_id,
                )
            )

            # Entity -> MENTIONED_IN -> Document
            relationships.append(
                UniversalRelationship(
                    source_id=ent.entity_id,
                    target_id=doc_node_id,
                    relationship_type="MENTIONED_IN",
                    confidence=1.0,
                    context=f"{ent.label} mentioned in document",
                    source_document_id=document_id,
                )
            )

            # If entity is Person and identified as author/lead, link AUTHORED_BY
            if ent.entity_class == "Person" and any(k in text[:300].lower() for k in ["author", "owner", "created by"]):
                relationships.append(
                    UniversalRelationship(
                        source_id=doc_node_id,
                        target_id=ent.entity_id,
                        relationship_type="AUTHORED_BY",
                        confidence=0.95,
                        context=f"Document authored by {ent.label}",
                        source_document_id=document_id,
                    )
                )

        # 3. Deduplicate relationships by (source_id, target_id, relationship_type)
        deduped: dict[tuple[str, str, str], UniversalRelationship] = {}
        for r in relationships:
            key = (r.source_id, r.target_id, r.relationship_type)
            if key not in deduped or r.confidence > deduped[key].confidence:
                deduped[key] = r

        return list(deduped.values())

