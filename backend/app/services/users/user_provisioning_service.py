from __future__ import annotations

import logging
import re
from typing import Any, Optional
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.security import hash_password
from app.models.entity import EntityRecord
from app.models.user import User
from app.models.validation import InferenceEventRecord
from app.schemas.user import (
    DiscoveredPersonResponse,
    ProvisionUserRequest,
    ProvisionedUserResponse,
)
from app.services.graph.falkordb_client import FalkorDBClient

logger = logging.getLogger(__name__)


class UserProvisioningService:
    """
    UKGOE Part 8: Discovered Person Provisioning & Manual User Onboarding.
    Connects un-provisioned Person entities discovered in ingested documents
    to authenticated system User accounts in PostgreSQL and synchronizes FalkorDB.
    """

    def __init__(self, falkor_client: FalkorDBClient | None = None):
        self.falkor = falkor_client or FalkorDBClient()

    async def ensure_user_schema_columns(self, db: AsyncSession) -> None:
        """Ensures the users table contains Part 8 extension columns."""
        try:
            await db.execute(text("""
                ALTER TABLE users ADD COLUMN IF NOT EXISTS person_entity_id VARCHAR(100);
                ALTER TABLE users ADD COLUMN IF NOT EXISTS clearance_level VARCHAR(50) DEFAULT 'Internal';
                ALTER TABLE users ADD COLUMN IF NOT EXISTS location VARCHAR(100);
                ALTER TABLE users ADD COLUMN IF NOT EXISTS title VARCHAR(100);
            """))
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.debug(f"User schema check note: {e}")

    async def list_discovered_personnel(self, db: AsyncSession) -> list[DiscoveredPersonResponse]:
        """
        Retrieves all extracted Person entities from PostgreSQL/FalkorDB and flags
        whether a corresponding User login account already exists.
        """
        await self.ensure_user_schema_columns(db)

        # 1. Fetch all existing users
        users_res = await db.execute(select(User))
        existing_users = users_res.scalars().all()
        user_emails = {u.email.lower() for u in existing_users if u.email}
        user_person_ids = {u.person_entity_id for u in existing_users if u.person_entity_id}

        # 2. Fetch all Person entities from canonical relational ledger
        person_res = await db.execute(
            select(EntityRecord).where(EntityRecord.entity_class == "Person")
        )
        person_entities = person_res.scalars().all()

        results: list[DiscoveredPersonResponse] = []
        for p in person_entities:
            props = p.properties or {}
            email = props.get("email") or props.get("contact_email")
            is_prov = bool(props.get("is_provisioned", False))

            has_user = bool(
                p.entity_id in user_person_ids
                or (bool(email) and email.lower() in user_emails)
            )

            results.append(
                DiscoveredPersonResponse(
                    entity_id=p.entity_id,
                    full_name=p.label or props.get("name") or p.entity_id,
                    inferred_department=props.get("department") or props.get("inferred_group"),
                    inferred_role=props.get("title") or props.get("role") or props.get("inferred_role"),
                    source_documents=p.source_document_ids or [],
                    mention_count=len(p.source_document_ids or [1]),
                    has_existing_user=has_user,
                    is_provisioned=bool(is_prov or has_user),
                )
            )

        return results

    async def provision_discovered_person(
        self,
        req: ProvisionUserRequest,
        db: AsyncSession,
        admin_email: str = "admin@memory.internal",
    ) -> ProvisionedUserResponse:
        """
        Creates authenticated User in PostgreSQL and synchronizes FalkorDB Person node.
        """
        await self.ensure_user_schema_columns(db)

        # 1. Check email availability
        existing = await db.execute(
            select(User).where(func.lower(User.email) == req.email.lower())
        )
        if existing.scalars().first():
            raise ValueError(f"An account with email '{req.email}' already exists.")

        # 2. Create PostgreSQL User
        pw_hash = hash_password(req.password)
        new_user = User(
            full_name=req.full_name,
            email=req.email.lower(),
            password_hash=pw_hash,
            role=req.role,
            department=req.department,
            clearance_level=req.clearance_level,
            person_entity_id=req.person_entity_id,
            location=req.location,
            title=req.title,
            is_active=True,
        )
        db.add(new_user)
        await db.flush()

        # 3. Update canonical EntityRecord in PostgreSQL
        ent_stmt = select(EntityRecord).where(EntityRecord.entity_id == req.person_entity_id)
        ent = (await db.execute(ent_stmt)).scalar_one_or_none()
        if ent:
            props = dict(ent.properties or {})
            props.update({
                "email": req.email.lower(),
                "role": req.role,
                "department": req.department,
                "clearance_level": req.clearance_level,
                "is_provisioned": True,
                "title": req.title,
                "location": req.location,
            })
            ent.properties = props
            ent.label = req.full_name

        # 4. Synchronize FalkorDB Person node
        def _sync_falkordb() -> bool:
            clean_pid = req.person_entity_id.replace("'", "\\'")
            clean_email = req.email.replace("'", "\\'")
            clean_role = req.role.replace("'", "\\'")
            clean_dept = req.department.replace("'", "\\'")
            clean_clearance = req.clearance_level.replace("'", "\\'")
            clean_title = (req.title or "").replace("'", "\\'")

            # Update Person node properties
            cypher_person = f"""
            MERGE (p:Person {{id: '{clean_pid}'}})
            SET p.email = '{clean_email}',
                p.user_id = {new_user.id},
                p.role = '{clean_role}',
                p.department = '{clean_dept}',
                p.clearance_level = '{clean_clearance}',
                p.is_provisioned = true,
                p.title = '{clean_title}'
            """
            self.falkor.query(cypher_person)

            # Link location if provided
            if req.location:
                loc_slug = re.sub(r"[^\w\s-]", "", req.location.lower()).replace(" ", "-")
                clean_loc = req.location.replace("'", "\\'")
                cypher_loc = f"""
                MERGE (loc:Location {{id: 'location:{loc_slug}'}})
                ON CREATE SET loc.name = '{clean_loc}', loc.type = 'Office'
                WITH loc
                MATCH (p:Person {{id: '{clean_pid}'}})
                MERGE (p)-[:LOCATED_AT]->(loc)
                """
                self.falkor.query(cypher_loc)

            return True

        falkor_ok = await run_in_threadpool(_sync_falkordb)

        # 5. Emit audit event in inference_events
        audit_event = InferenceEventRecord(
            rule_id="USER_PROVISIONING",
            trigger_entity_id=req.person_entity_id,
            affected_entity_ids=[req.person_entity_id],
            event_type="USER_PROVISIONED",
            payload={
                "user_id": new_user.id,
                "email": req.email,
                "role": req.role,
                "clearance_level": req.clearance_level,
                "provisioned_by": admin_email,
            },
        )
        db.add(audit_event)

        await db.commit()
        await db.refresh(new_user)

        return ProvisionedUserResponse(
            user_id=new_user.id,
            person_entity_id=req.person_entity_id,
            full_name=new_user.full_name,
            email=new_user.email,
            role=new_user.role,
            department=new_user.department,
            clearance_level=new_user.clearance_level,
            title=new_user.title,
            location=new_user.location,
            is_active=new_user.is_active,
            falkordb_synchronized=falkor_ok,
        )

    async def get_personnel_status(self, person_id: str, db: AsyncSession) -> dict[str, Any]:
        """Returns the current graph and user status for a specific person entity."""
        await self.ensure_user_schema_columns(db)

        user_stmt = select(User).where(User.person_entity_id == person_id)
        u = (await db.execute(user_stmt)).scalar_one_or_none()

        ent_stmt = select(EntityRecord).where(EntityRecord.entity_id == person_id)
        ent = (await db.execute(ent_stmt)).scalar_one_or_none()

        def _get_graph_person():
            clean_pid = person_id.replace("'", "\\'")
            rows = self.falkor.query(f"MATCH (p:Person {{id: '{clean_pid}'}}) RETURN p.email, p.role, p.is_provisioned, p.clearance_level")
            return rows[0] if rows else None

        graph_data = await run_in_threadpool(_get_graph_person)

        return {
            "person_entity_id": person_id,
            "has_system_user": u is not None,
            "user_id": u.id if u else None,
            "email": u.email if u else (graph_data[0] if graph_data else None),
            "role": u.role if u else (graph_data[1] if graph_data else None),
            "clearance_level": u.clearance_level if u else (graph_data[3] if graph_data else "Internal"),
            "is_provisioned": bool(graph_data[2]) if graph_data else (u is not None),
            "entity_label": ent.label if ent else None,
        }

