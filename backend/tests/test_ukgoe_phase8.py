from __future__ import annotations

import uuid
import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.security import verify_password
from app.models.entity import EntityRecord
from app.models.user import User
from app.schemas.user import ProvisionUserRequest
from app.services.graph.falkordb_client import FalkorDBClient
from app.services.permissions.permission_resolver import PermissionResolver
from app.services.users.user_provisioning_service import UserProvisioningService


@pytest.fixture(scope="module")
def falkor():
    return FalkorDBClient()


@pytest.fixture(scope="module")
def provisioning_service(falkor):
    return UserProvisioningService(falkor_client=falkor)


@pytest.mark.asyncio
async def test_list_discovered_personnel(provisioning_service):
    async with AsyncSessionLocal() as session:
        # Ensure schema
        await provisioning_service.ensure_user_schema_columns(session)

        unique_suffix = uuid.uuid4().hex[:6]
        person_id = f"person:sunita-{unique_suffix}"
        full_name = f"Dr. Sunita Rao {unique_suffix}"

        # Seed un-provisioned Person entity in PostgreSQL
        ent = EntityRecord(
            entity_id=person_id,
            entity_class="Person",
            label=full_name,
            properties={
                "name": full_name,
                "inferred_role": "Lead Architect",
                "inferred_group": "Platform Engineering",
                "is_provisioned": False,
            },
            source_document_ids=["doc_telecom_arch_spec"],
        )
        session.add(ent)
        await session.commit()

        # Call service
        candidates = await provisioning_service.list_discovered_personnel(session)
        assert len(candidates) > 0

        target = next((c for c in candidates if c.entity_id == person_id), None)
        assert target is not None
        assert target.full_name == full_name
        assert target.has_existing_user is False
        assert target.is_provisioned is False
        assert "doc_telecom_arch_spec" in target.source_documents


@pytest.mark.asyncio
async def test_provision_discovered_person_and_falkordb_sync(provisioning_service, falkor):
    async with AsyncSessionLocal() as session:
        await provisioning_service.ensure_user_schema_columns(session)

        unique_suffix = uuid.uuid4().hex[:6]
        person_id = f"person:kavita-{unique_suffix}"
        full_name = f"Kavita Krishnan {unique_suffix}"
        email = f"kavita.{unique_suffix}@telcosphere.io"
        password = "SecurePassword2026!"

        # Seed Person in FalkorDB
        falkor.query(f"CREATE (p:Person {{id: '{person_id}', name: '{full_name}'}})")

        # Seed Person entity in PostgreSQL
        ent = EntityRecord(
            entity_id=person_id,
            entity_class="Person",
            label=full_name,
            properties={"name": full_name},
            source_document_ids=["doc_sec_plan"],
        )
        session.add(ent)
        await session.commit()

        # Admin provisions this person
        req = ProvisionUserRequest(
            person_entity_id=person_id,
            full_name=full_name,
            email=email,
            password=password,
            role="Security Lead",
            department="Cybersecurity",
            clearance_level="Confidential",
            title="Director of Threat Intelligence",
            location="Dallas Headquarters",
        )

        res = await provisioning_service.provision_discovered_person(req, session)

        assert res.user_id > 0
        assert res.email == email
        assert res.role == "Security Lead"
        assert res.clearance_level == "Confidential"
        assert res.falkordb_synchronized is True

        # Verify PostgreSQL User record
        user_db = (await session.execute(
            select(User).where(User.id == res.user_id)
        )).scalar_one()
        assert user_db.email == email
        assert user_db.clearance_level == "Confidential"
        assert user_db.person_entity_id == person_id
        assert user_db.location == "Dallas Headquarters"
        assert user_db.title == "Director of Threat Intelligence"
        assert verify_password(password, user_db.password_hash) is True

        # Verify FalkorDB node synchronization
        rows = falkor.query(
            f"MATCH (p:Person {{id: '{person_id}'}}) "
            f"RETURN p.email, p.role, p.clearance_level, p.is_provisioned, p.title"
        )
        assert len(rows) == 1
        p_row = rows[0]
        assert p_row[0] == email
        assert p_row[1] == "Security Lead"
        assert p_row[2] == "Confidential"
        assert bool(p_row[3]) is True
        assert p_row[4] == "Director of Threat Intelligence"

        # Verify Location edge in FalkorDB
        loc_rows = falkor.query(
            f"MATCH (p:Person {{id: '{person_id}'}})-[:LOCATED_AT]->(loc:Location) "
            f"RETURN loc.name"
        )
        assert len(loc_rows) >= 1
        assert "Dallas" in loc_rows[0][0]

        # Verify duplicate email provisioning fails gracefully
        with pytest.raises(ValueError, match="already exists"):
            await provisioning_service.provision_discovered_person(req, session)

        # Cleanup ephemeral test user
        await session.execute(text("DELETE FROM users WHERE id > 1"))
        await session.commit()


@pytest.mark.asyncio
async def test_provisioned_user_clearance_and_status(provisioning_service):
    async with AsyncSessionLocal() as session:
        unique_suffix = uuid.uuid4().hex[:6]
        person_id = f"person:arjun-{unique_suffix}"
        full_name = f"Arjun Mehta {unique_suffix}"
        email = f"arjun.{unique_suffix}@telcosphere.io"

        req = ProvisionUserRequest(
            person_entity_id=person_id,
            full_name=full_name,
            email=email,
            password="StrongPassword123!",
            role="Senior Systems Engineer",
            department="Infrastructure",
            clearance_level="Confidential",
        )
        prov_res = await provisioning_service.provision_discovered_person(req, session)

        # Check status endpoint
        status = await provisioning_service.get_personnel_status(person_id, session)
        assert status["has_system_user"] is True
        assert status["email"] == email
        assert status["clearance_level"] == "Confidential"
        assert status["is_provisioned"] is True

        # Verify Clearance Enforcement (INV-05) for the provisioned user
        assert PermissionResolver.is_entity_authorized("Public", user_clearance=prov_res.clearance_level) is True
        assert PermissionResolver.is_entity_authorized("Internal", user_clearance=prov_res.clearance_level) is True
        assert PermissionResolver.is_entity_authorized("Confidential", user_clearance=prov_res.clearance_level) is True
        assert PermissionResolver.is_entity_authorized("Restricted", user_clearance=prov_res.clearance_level) is False

        # Cleanup ephemeral test user
        await session.execute(text("DELETE FROM users WHERE id > 1"))
        await session.commit()

