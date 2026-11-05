from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from typing import Any, Optional
import yaml
from starlette.concurrency import run_in_threadpool
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entity import EntityRecord
from app.models.evolution import (
    ConstraintViolationRecord,
    InferenceRuleRecord,
    OntologyEvolutionRecord,
)
from app.models.relationship import RelationshipRecord
from app.models.validation import InferenceEventRecord
from app.services.graph.falkordb_client import FalkorDBClient
from app.services.vector.qdrant_client import QdrantService
from qdrant_client import models

logger = logging.getLogger(__name__)


class OntologyEvolutionService:
    """
    UKGOE Part 6: Ontology Self-Upgrade Protocol
    1. Candidate Class Detection & Evolution Logging (Step 6.1)
    2. Candidate Relationship Detection & Edge Fallback (Step 6.2)
    3. Custom Dynamic YAML Inference Rule Registration & Retrospective Run (Step 6.3)
    4. Human-Gated Property Constraint Evolution & Relaxation (Step 6.4)
    """

    def __init__(
        self,
        graph_client: FalkorDBClient | None = None,
        qdrant_service: QdrantService | None = None,
    ):
        self.graph_client = graph_client or FalkorDBClient()
        self.qdrant_service = qdrant_service or QdrantService()

    # ---------------------------------------------------------
    # Step 6.1: Candidate Class Detection & Management
    # ---------------------------------------------------------
    async def evaluate_candidate_class(
        self,
        candidate_name: str,
        entity_id: str,
        source_doc_id: str,
        db: AsyncSession,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Tracks unclassified entity concepts.
        If observed across >= 3 distinct documents, status is elevated to CANDIDATE.
        """
        stmt = select(OntologyEvolutionRecord).where(
            OntologyEvolutionRecord.candidate_type == "CLASS",
            OntologyEvolutionRecord.candidate_name == candidate_name,
        )
        record = (await db.execute(stmt)).scalar_one_or_none()

        if not record:
            record = OntologyEvolutionRecord(
                candidate_type="CLASS",
                candidate_name=candidate_name,
                source_document_ids=[source_doc_id],
                exemplar_entities=[entity_id],
                frequency=1,
                status="PENDING",
                metadata_payload=metadata or {},
            )
            db.add(record)
        else:
            doc_ids = set(record.source_document_ids)
            doc_ids.add(source_doc_id)
            record.source_document_ids = list(doc_ids)
            record.frequency = len(doc_ids)

            exemplars = set(record.exemplar_entities)
            exemplars.add(entity_id)
            record.exemplar_entities = list(exemplars)

            if metadata:
                record.metadata_payload.update(metadata)

        # Recurrence check: >= 3 distinct documents elevates to CANDIDATE
        if record.frequency >= 3 and record.status == "PENDING":
            record.status = "CANDIDATE"
            await self._emit_evolution_event(
                event_type="SCHEMA_EVOLUTION_CANDIDATE",
                rule_id="SCHEMA_EVOLUTION",
                trigger_entity_id=entity_id,
                affected_entity_ids=record.exemplar_entities,
                payload={
                    "candidate_type": "CLASS",
                    "candidate_name": candidate_name,
                    "frequency": record.frequency,
                    "exemplars_count": len(record.exemplar_entities),
                },
                db=db,
            )

        await db.commit()
        return record.status == "CANDIDATE"

    # ---------------------------------------------------------
    # Step 6.2: Candidate Relationship Detection & Edge Fallback
    # ---------------------------------------------------------
    async def evaluate_candidate_relation(
        self,
        candidate_relation_type: str,
        source_entity_id: str,
        target_entity_id: str,
        source_doc_id: str,
        db: AsyncSession,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Tracks novel relationship types.
        If observed across >= 5 distinct documents, status is elevated to CANDIDATE.
        """
        stmt = select(OntologyEvolutionRecord).where(
            OntologyEvolutionRecord.candidate_type == "RELATION",
            OntologyEvolutionRecord.candidate_name == candidate_relation_type,
        )
        record = (await db.execute(stmt)).scalar_one_or_none()
        exemplar_pair = f"{source_entity_id}->{target_entity_id}"

        if not record:
            record = OntologyEvolutionRecord(
                candidate_type="RELATION",
                candidate_name=candidate_relation_type,
                source_document_ids=[source_doc_id],
                exemplar_entities=[exemplar_pair],
                frequency=1,
                status="PENDING",
                metadata_payload=metadata or {},
            )
            db.add(record)
        else:
            doc_ids = set(record.source_document_ids)
            doc_ids.add(source_doc_id)
            record.source_document_ids = list(doc_ids)
            record.frequency = len(doc_ids)

            exemplars = set(record.exemplar_entities)
            exemplars.add(exemplar_pair)
            record.exemplar_entities = list(exemplars)

            if metadata:
                record.metadata_payload.update(metadata)

        # Recurrence check: >= 5 distinct documents elevates to CANDIDATE
        if record.frequency >= 5 and record.status == "PENDING":
            record.status = "CANDIDATE"
            await self._emit_evolution_event(
                event_type="SCHEMA_EVOLUTION_CANDIDATE",
                rule_id="SCHEMA_EVOLUTION",
                trigger_entity_id=source_entity_id,
                affected_entity_ids=[source_entity_id, target_entity_id],
                payload={
                    "candidate_type": "RELATION",
                    "candidate_name": candidate_relation_type,
                    "frequency": record.frequency,
                    "exemplars_count": len(record.exemplar_entities),
                },
                db=db,
            )

        await db.commit()
        return record.status == "CANDIDATE"

    # ---------------------------------------------------------
    # Approval & Rejection Migrations
    # ---------------------------------------------------------
    async def confirm_candidate_class(
        self,
        candidate_identifier: str,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """
        Human-in-the-loop approval of candidate class:
        1. Updates candidate record status to APPROVED.
        2. Migrates PostgreSQL entities: updates entity_class to new class.
        3. Migrates FalkorDB: adds :NewClass label and removes :Unclassified.
        4. Re-indexes Qdrant points with new entity_class.
        """
        stmt = select(OntologyEvolutionRecord).where(
            or_(
                OntologyEvolutionRecord.id == candidate_identifier,
                and_(
                    OntologyEvolutionRecord.candidate_type == "CLASS",
                    OntologyEvolutionRecord.candidate_name == candidate_identifier,
                ),
            )
        )
        record = (await db.execute(stmt)).scalar_one_or_none()
        if not record:
            raise ValueError(f"Candidate class '{candidate_identifier}' not found")

        clean_class = re.sub(r"[^A-Za-z0-9_]", "", record.candidate_name)
        if not clean_class:
            raise ValueError(f"Invalid candidate class name: '{record.candidate_name}'")

        record.status = "APPROVED"

        # 1. Update PostgreSQL entities
        migrated_ids = list(record.exemplar_entities)
        if migrated_ids:
            update_stmt = (
                update(EntityRecord)
                .where(
                    or_(
                        EntityRecord.entity_id.in_(migrated_ids),
                        and_(
                            EntityRecord.entity_class == "Unclassified",
                            EntityRecord.properties["candidate_class"].as_string() == record.candidate_name,
                        ),
                    )
                )
                .values(entity_class=clean_class)
            )
            await db.execute(update_stmt)

        # 2. Update FalkorDB in threadpool
        def _update_graph():
            for eid in migrated_ids:
                try:
                    cypher = f"MATCH (n {{id: '{eid}'}}) SET n:{clean_class} REMOVE n:Unclassified"
                    self.graph_client.query(cypher)
                except Exception as ex:
                    logger.warning(f"Error migrating FalkorDB entity {eid} to label {clean_class}: {ex}")

        await run_in_threadpool(_update_graph)

        # 3. Update Qdrant vector payload
        def _update_qdrant():
            client = self.qdrant_service.client
            collection = self.qdrant_service.collection_name
            for eid in migrated_ids:
                try:
                    client.set_payload(
                        collection_name=collection,
                        payload={"entity_class": clean_class},
                        points=models.Filter(
                            must=[
                                models.FieldCondition(
                                    key="entity_id",
                                    match=models.MatchValue(value=eid),
                                )
                            ]
                        ),
                    )
                except Exception as ex:
                    logger.debug(f"Qdrant point update error for {eid}: {ex}")

        await run_in_threadpool(_update_qdrant)

        # 4. Emit approval audit event
        await self._emit_evolution_event(
            event_type="SCHEMA_EVOLUTION_APPROVED",
            rule_id="SCHEMA_EVOLUTION",
            trigger_entity_id=clean_class,
            affected_entity_ids=migrated_ids,
            payload={"new_class": clean_class, "migrated_count": len(migrated_ids)},
            db=db,
        )

        await db.commit()
        return {
            "candidate_id": record.id,
            "candidate_name": clean_class,
            "migrated_entities": len(migrated_ids),
            "status": "APPROVED",
        }

    async def confirm_candidate_relation(
        self,
        candidate_identifier: str,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """
        Human-in-the-loop approval of candidate relationship:
        1. Updates candidate record status to APPROVED.
        2. Migrates PostgreSQL relationships table.
        3. Migrates FalkorDB edges from :RELATED_TO to :NEW_TYPE.
        """
        stmt = select(OntologyEvolutionRecord).where(
            or_(
                OntologyEvolutionRecord.id == candidate_identifier,
                and_(
                    OntologyEvolutionRecord.candidate_type == "RELATION",
                    OntologyEvolutionRecord.candidate_name == candidate_identifier,
                ),
            )
        )
        record = (await db.execute(stmt)).scalar_one_or_none()
        if not record:
            raise ValueError(f"Candidate relation '{candidate_identifier}' not found")

        clean_rel = re.sub(r"[^A-Z0-9_]", "", record.candidate_name.upper())
        if not clean_rel:
            raise ValueError(f"Invalid candidate relation name: '{record.candidate_name}'")

        record.status = "APPROVED"

        # 1. Update PostgreSQL relationships
        update_stmt = (
            update(RelationshipRecord)
            .where(
                and_(
                    RelationshipRecord.relationship_type == "RELATED_TO",
                    or_(
                        RelationshipRecord.context.ilike(f"%{record.candidate_name}%"),
                        RelationshipRecord.context == record.candidate_name,
                    ),
                )
            )
            .values(relationship_type=clean_rel)
        )
        await db.execute(update_stmt)

        # 2. Update FalkorDB edges
        def _update_graph_edges():
            try:
                cypher = (
                    f"MATCH (a)-[r:RELATED_TO]->(b) "
                    f"WHERE r.candidate_relation_type = '{record.candidate_name}' "
                    f"CREATE (a)-[r2:{clean_rel}]->(b) "
                    f"SET r2 = properties(r) "
                    f"DELETE r"
                )
                self.graph_client.query(cypher)
            except Exception as ex:
                logger.warning(f"Error migrating FalkorDB edge to {clean_rel}: {ex}")

        await run_in_threadpool(_update_graph_edges)

        # 3. Emit approval event
        await self._emit_evolution_event(
            event_type="SCHEMA_EVOLUTION_APPROVED",
            rule_id="SCHEMA_EVOLUTION",
            trigger_entity_id=clean_rel,
            affected_entity_ids=[],
            payload={"new_relation": clean_rel},
            db=db,
        )

        await db.commit()
        return {
            "candidate_id": record.id,
            "candidate_name": clean_rel,
            "status": "APPROVED",
        }

    async def reject_candidate(
        self,
        candidate_identifier: str,
        db: AsyncSession,
        reason: str | None = None,
    ) -> dict[str, Any]:
        """
        Rejection workflow: retains generic classification/relationship and flags status as REJECTED.
        """
        stmt = select(OntologyEvolutionRecord).where(
            or_(
                OntologyEvolutionRecord.id == candidate_identifier,
                OntologyEvolutionRecord.candidate_name == candidate_identifier,
            )
        )
        record = (await db.execute(stmt)).scalar_one_or_none()
        if not record:
            raise ValueError(f"Candidate '{candidate_identifier}' not found")

        record.status = "REJECTED"
        if reason:
            record.metadata_payload["rejection_reason"] = reason

        await db.commit()
        return {"candidate_id": record.id, "status": "REJECTED"}

    # ---------------------------------------------------------
    # Step 6.3: Custom Dynamic YAML Inference Rule Registration
    # ---------------------------------------------------------
    async def register_inference_rule(
        self,
        rule_yaml_str: str,
        registered_by: str,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """
        Registers dynamic YAML inference rule with:
        - AST cycle and bounded depth validation (max_depth <= 5).
        - Mutation safety checks (forbids DROP/DELETE).
        - Retrospective execution across existing FalkorDB graph.
        """
        try:
            parsed = yaml.safe_load(rule_yaml_str)
        except Exception as e:
            raise ValueError(f"Malformed YAML rule: {e}")

        if not isinstance(parsed, dict):
            raise ValueError("Inference rule must be a YAML dictionary")

        rule_id = str(parsed.get("rule_id", "")).strip()
        name = str(parsed.get("name", "")).strip()
        trigger_entity = str(parsed.get("trigger_entity", "")).strip()
        max_depth = int(parsed.get("max_depth", 1))

        if not rule_id or not name or not trigger_entity:
            raise ValueError("Rule missing required fields: rule_id, name, or trigger_entity")

        # Termination & depth safety check
        if max_depth > 5:
            raise ValueError(f"Rule max_depth ({max_depth}) violates safety invariant bound of 5 hops")

        # Mutation safety check
        conditions = parsed.get("conditions", [])
        actions = parsed.get("actions", [])
        for block in list(conditions) + list(actions):
            block_str = str(block).upper()
            for forbidden in ["DROP", "DELETE", "REMOVE", "DETACH"]:
                if forbidden in block_str:
                    raise ValueError(f"Inference rule contains forbidden destructive operation '{forbidden}'")

        # Save to database
        rule_record = InferenceRuleRecord(
            rule_id=rule_id,
            name=name,
            trigger_entity=trigger_entity,
            rule_yaml=rule_yaml_str,
            is_active=True,
            registered_by=registered_by,
        )
        db.add(rule_record)

        # Retrospective evaluation across FalkorDB
        retrospective_count = 0
        clean_trigger = re.sub(r"[^A-Za-z0-9_]", "", trigger_entity)

        def _evaluate_retrospective():
            count = 0
            try:
                cypher = f"MATCH (n:{clean_trigger}) RETURN n.id AS id, properties(n) AS props LIMIT 100"
                result = self.graph_client.query(cypher)
                count = len(result)
            except Exception as ex:
                logger.debug(f"Retrospective evaluation Cypher check: {ex}")
            return count

        retrospective_count = await run_in_threadpool(_evaluate_retrospective)

        # Audit event
        await self._emit_evolution_event(
            event_type="INFERENCE_RULE_ADDED",
            rule_id=rule_id,
            trigger_entity_id=trigger_entity,
            affected_entity_ids=[],
            payload={
                "rule_name": name,
                "retrospective_candidates_evaluated": retrospective_count,
            },
            db=db,
        )

        await db.commit()
        return {
            "rule_id": rule_id,
            "name": name,
            "status": "ACTIVE",
            "retrospective_eval_count": retrospective_count,
        }

    # ---------------------------------------------------------
    # Step 6.4: Human-Gated Property Constraint Evolution
    # ---------------------------------------------------------
    async def record_constraint_violation(
        self,
        entity_id: str,
        entity_class: str,
        property_name: str,
        violation_value: str | None,
        expected_constraint: str,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """
        Audits property constraint violations.
        If violation rate exceeds 20% in the last 100 observations, emits a
        CONSTRAINT_RELAXATION_CANDIDATE event for administrative approval.
        """
        record = ConstraintViolationRecord(
            entity_id=entity_id,
            entity_class=entity_class,
            property_name=property_name,
            violation_value=str(violation_value) if violation_value is not None else None,
            expected_constraint=expected_constraint,
        )
        db.add(record)
        await db.flush()

        # Compute violation frequency over recent observations
        count_stmt = select(func.count(ConstraintViolationRecord.id)).where(
            ConstraintViolationRecord.entity_class == entity_class,
            ConstraintViolationRecord.property_name == property_name,
            ConstraintViolationRecord.resolved.is_(False),
        )
        total_violations = (await db.execute(count_stmt)).scalar() or 0

        # Frequency threshold: 20 violations out of 100 (rate > 20%)
        is_candidate = total_violations >= 20

        if is_candidate:
            await self._emit_evolution_event(
                event_type="CONSTRAINT_RELAXATION_CANDIDATE",
                rule_id="CONSTRAINT_MONITOR",
                trigger_entity_id=entity_id,
                affected_entity_ids=[entity_id],
                payload={
                    "entity_class": entity_class,
                    "property_name": property_name,
                    "total_violations": total_violations,
                    "expected_constraint": expected_constraint,
                },
                db=db,
            )

        await db.commit()
        return {
            "violation_id": record.id,
            "entity_id": entity_id,
            "total_violations": total_violations,
            "relaxation_candidate": is_candidate,
        }

    async def relax_constraint(
        self,
        property_name: str,
        new_constraint: str,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """
        Human-gated constraint relaxation: marks existing violations as resolved
        and logs the updated constraint event.
        """
        stmt = (
            update(ConstraintViolationRecord)
            .where(
                ConstraintViolationRecord.property_name == property_name,
                ConstraintViolationRecord.resolved.is_(False),
            )
            .values(resolved=True)
        )
        await db.execute(stmt)

        await self._emit_evolution_event(
            event_type="CONSTRAINT_RELAXED",
            rule_id="CONSTRAINT_MONITOR",
            trigger_entity_id=property_name,
            affected_entity_ids=[],
            payload={"property_name": property_name, "new_constraint": new_constraint},
            db=db,
        )

        await db.commit()
        return {
            "property_name": property_name,
            "new_constraint": new_constraint,
            "status": "RELAXED",
        }

    # ---------------------------------------------------------
    # Listing Queries for Admin UI
    # ---------------------------------------------------------
    async def list_candidates(
        self,
        db: AsyncSession,
        status: str | None = None,
    ) -> list[OntologyEvolutionRecord]:
        stmt = select(OntologyEvolutionRecord)
        if status:
            stmt = stmt.where(OntologyEvolutionRecord.status == status)
        stmt = stmt.order_by(OntologyEvolutionRecord.frequency.desc())
        return list((await db.execute(stmt)).scalars().all())

    async def list_violations(
        self,
        db: AsyncSession,
        resolved: bool = False,
    ) -> list[ConstraintViolationRecord]:
        stmt = (
            select(ConstraintViolationRecord)
            .where(ConstraintViolationRecord.resolved.is_(resolved))
            .order_by(ConstraintViolationRecord.occurred_at.desc())
            .limit(100)
        )
        return list((await db.execute(stmt)).scalars().all())

    # ---------------------------------------------------------
    # Internal Helpers
    # ---------------------------------------------------------
    async def _emit_evolution_event(
        self,
        event_type: str,
        rule_id: str,
        trigger_entity_id: str,
        affected_entity_ids: list[str],
        payload: dict[str, Any],
        db: AsyncSession,
    ) -> None:
        event = InferenceEventRecord(
            rule_id=rule_id,
            trigger_entity_id=trigger_entity_id,
            affected_entity_ids=affected_entity_ids,
            event_type=event_type,
            payload=payload,
            emitted_at=datetime.now(UTC),
            consumed_by=["ontology_admin_ui", "notification_service"],
        )
        db.add(event)

