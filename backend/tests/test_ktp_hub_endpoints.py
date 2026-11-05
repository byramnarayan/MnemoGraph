from __future__ import annotations

import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.deps import get_current_user
from app.models.user import User
from app.services.graph.falkordb_client import FalkorDBClient


@pytest.fixture(scope="module")
def falkor():
    return FalkorDBClient()


@pytest.mark.asyncio
async def test_ktp_hub_people_and_handover_flow(falkor):
    suffix = uuid.uuid4().hex[:6]
    admin_id = f"person:admin-{suffix}"
    mgr_id = f"person:mgr-{suffix}"
    dev_id = f"person:dev-{suffix}"
    succ_id = f"person:succ-{suffix}"

    # Setup graph nodes
    falkor.query(f"MERGE (a:Person {{id: '{admin_id}', full_name: 'Admin Alice', role: 'System Admin', employment_status: 'active'}})")
    falkor.query(f"MERGE (m:Person {{id: '{mgr_id}', full_name: 'Manager Bob', role: 'Lead Manager', employment_status: 'active'}})")
    falkor.query(f"MERGE (d:Person {{id: '{dev_id}', full_name: 'Dev Charlie', role: 'Staff Engineer', employment_status: 'departing'}})")
    falkor.query(f"MERGE (s:Person {{id: '{succ_id}', full_name: 'Successor Dave', role: 'Senior Engineer', employment_status: 'active'}})")
    falkor.query(f"MATCH (m:Person {{id: '{mgr_id}'}}), (d:Person {{id: '{dev_id}'}}) MERGE (m)-[:MANAGES]->(d)")

    # Mock admin user
    admin_user = User(
        id=uuid.uuid4(),
        email="admin@test.com",
        full_name="Admin Alice",
        role="System Admin",
        clearance_level="Restricted",
        person_entity_id=admin_id,
        is_active=True,
    )
    setattr(admin_user, "is_superuser", True)

    app.dependency_overrides[get_current_user] = lambda: admin_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. List personnel
        res = await ac.get("/api/v1/ktp/people")
        assert res.status_code == 200
        people = res.json()
        assert len(people) >= 4
        person_ids = [p["person_id"] for p in people]
        assert dev_id in person_ids

        # 2. Get Person KTP Package
        res_ktp = await ac.get(f"/api/v1/ktp/people/{dev_id}")
        assert res_ktp.status_code == 200
        ktp_data = res_ktp.json()
        assert ktp_data["subject_person_id"] == dev_id
        assert ktp_data["section_a_profile"]["full_name"] == "Dev Charlie"

        # 3. Assign Handover from Charlie to Dave
        res_ho = await ac.post(
            f"/api/v1/ktp/people/{dev_id}/assign-handover",
            json={"target_person_id": succ_id, "notes": "Handover to Dave"},
        )
        assert res_ho.status_code == 200
        ho_body = res_ho.json()
        assert ho_body["success"] is True
        assert ho_body["target_person_id"] == succ_id

        # 4. Verify Successor-only access
        # Mock successor user
        succ_user = User(
            id=uuid.uuid4(),
            email="succ@test.com",
            full_name="Successor Dave",
            role="Engineer",
            clearance_level="Internal",
            person_entity_id=succ_id,
            is_active=True,
        )
        setattr(succ_user, "is_superuser", False)
        app.dependency_overrides[get_current_user] = lambda: succ_user

        # Successor lists people -> should see self and dev_id (Charlie) handed over to him
        res_succ_list = await ac.get("/api/v1/ktp/people")
        assert res_succ_list.status_code == 200
        succ_people = res_succ_list.json()
        succ_pids = [p["person_id"] for p in succ_people]
        assert dev_id in succ_pids
        assert succ_id in succ_pids
        # Admin or Manager should NOT be visible to regular engineer Dave unless handed over
        assert admin_id not in succ_pids

    app.dependency_overrides.clear()

