from __future__ import annotations

import uuid
import pytest
from datetime import datetime, timezone
from sqlalchemy import select, text

from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.services.graph.falkordb_client import FalkorDBClient
from app.services.graph.incident_interconnect_service import IncidentInterconnectService


@pytest.fixture(scope="module")
def falkor():
    return FalkorDBClient()


@pytest.fixture(scope="module")
def incident_service(falkor):
    return IncidentInterconnectService(falkor_client=falkor)


@pytest.mark.asyncio
async def test_incident_interconnect_traversal_layers_0_to_7(incident_service, falkor):
    """
    UKGOE Step 10.1: Multi-Layer Interconnect Traversal (Layers 0 through 7)
    Validates Incident Header, Immediate Causes, Affected Scope, Tasks,
    Recurrence Chain, People Involved, Documents, and Lessons.
    """
    suffix = uuid.uuid4().hex[:6]
    inc_id = f"inc:telecom-outage-{suffix}"
    dec_id = f"dec:firmware-rollout-{suffix}"
    chg_id = f"chg:config-push-{suffix}"
    sys_id = f"sys:bng-gateway-{suffix}"
    loc_id = f"loc:frankfurt-{suffix}"
    proj_id = f"proj:5g-core-{suffix}"
    m_id = f"m:cutover-{suffix}"
    t_overdue = f"task:fix-bng-{suffix}"
    t_inprogress = f"task:monitor-traffic-{suffix}"
    t_done = f"task:notify-noc-{suffix}"
    lead_id = f"person:lead-{suffix}"
    assignee_id = f"person:dev-{suffix}"
    fwd_inc_id = f"inc:repeat-outage-{suffix}"
    doc_id = f"doc:pir-report-{suffix}"
    lesson_id = f"lesson:canary-deployment-{suffix}"

    cypher_seed = f"""
    // Layer 0: The Incident
    MERGE (inc:Incident {{
        id: '{inc_id}',
        title: 'Core BNG Gateway Outage {suffix}',
        severity: 'P1',
        type: 'network',
        status: 'open',
        cause_status: 'confirmed',
        confirmed_cause: 'Deadlock in BNG route table during push',
        initial_suspected_cause: 'Fiber cut',
        cause_revision_note: 'Updated after analyzing core dump',
        is_mis_diagnosed: true,
        recurrence_risk: true,
        recurrence_count: 2,
        causal_chain_depth: 3,
        data_quality_grade: 'A',
        classification: 'Internal',
        view_count: 5
    }})

    // Layer 1: Causes & Project
    MERGE (dec:Decision {{
        id: '{dec_id}',
        title: 'Skip Canary Deployment',
        outcome: 'approved',
        root_cause_analysis: 'Rushed deployment window caused deadlock',
        classification: 'Internal'
    }})
    MERGE (chg:Change {{
        id: '{chg_id}',
        change_type: 'firmware_upgrade',
        status: 'failed',
        affected_systems: 'BNG-01, BNG-02'
    }})
    MERGE (proj:Project {{id: '{proj_id}', name: '5G Core Rollout', status: 'active'}})
    MERGE (inc)<-[:CAUSED_BY]-(dec)
    MERGE (inc)<-[:CAUSED_BY]-(chg)
    MERGE (inc)-[:LINKED_TO_PROJECT]->(proj)

    // Layer 2: Scope
    MERGE (sys:System {{id: '{sys_id}', name: 'BNG Gateway Cluster', status: 'degraded', criticality: 'tier-1'}})
    MERGE (loc:Location {{id: '{loc_id}', name: 'Frankfurt Core DC', region: 'eu-central-1'}})
    MERGE (m:Milestone {{id: '{m_id}', name: 'Customer Cutover', status: 'delayed'}})
    MERGE (inc)-[:AFFECTS]->(sys)
    MERGE (inc)-[:AFFECTS]->(loc)
    MERGE (proj)-[:PART_OF]->(m)

    // Layer 3: Corrective Tasks
    MERGE (p_dev:Person {{id: '{assignee_id}', name: 'Dev Dan {suffix}', full_name: 'Dev Dan {suffix}', email: 'dan@{suffix}.com', role: 'SRE'}})
    MERGE (t1:Task {{id: '{t_overdue}', title: 'Patch BNG Driver', status: 'overdue', due_date: '2026-10-01', days_overdue: 34, classification: 'Internal'}})
    MERGE (t2:Task {{id: '{t_inprogress}', title: 'Monitor Core Traffic', status: 'in_progress', due_date: '2026-12-01', classification: 'Internal'}})
    MERGE (t3:Task {{id: '{t_done}', title: 'Notify NOC Ops', status: 'completed', completion_date: '2026-10-02', classification: 'Internal'}})
    MERGE (t1)-[:RAISED_FROM]->(inc)
    MERGE (t2)-[:RAISED_FROM]->(inc)
    MERGE (t3)-[:RAISED_FROM]->(inc)
    MERGE (t1)-[:ASSIGNED_TO]->(p_dev)

    // Layer 4: Forward Recurrence
    MERGE (sub:Incident {{id: '{fwd_inc_id}', title: 'Secondary BNG Outage', severity: 'P2', created_at: '2026-11-01'}})
    MERGE (inc)-[:CAUSED_RECURRENCE]->(sub)

    // Layer 5: People
    MERGE (p_lead:Person {{id: '{lead_id}', name: 'Lead Laura {suffix}', full_name: 'Lead Laura {suffix}', email: 'laura@{suffix}.com', role: 'Principal Architect'}})
    MERGE (p_lead)-[:LEADS]->(proj)

    // Layer 6: Documents
    MERGE (doc:Document {{id: '{doc_id}', title: 'PIR Post-Mortem Report', document_type: 'pir', status: 'approved', classification: 'Internal'}})
    MERGE (doc)-[:DOCUMENTS]->(inc)

    // Layer 7: Lessons
    MERGE (les:Lesson {{id: '{lesson_id}', title: 'Mandatory Canary Gate', summary: 'Never bypass 24h canary soak test.'}})
    MERGE (les)-[:DERIVED_FROM]->(inc)
    """
    falkor.query(cypher_seed)

    admin_user = User(
        id=1,
        email="admin@example.com",
        role="Executive Admin",
        clearance_level="Restricted",
        is_active=True,
    )

    view = await incident_service.build_incident_interconnect_view(
        incident_id=inc_id,
        user=admin_user,
        access_level=1,
    )

    # Layer 0 assertions
    assert view.layer0_incident.incident_id == inc_id
    assert view.layer0_incident.severity == "P1"
    assert view.layer0_incident.confirmed_cause == "Deadlock in BNG route table during push"
    assert view.layer0_incident.is_misdiagnosed is True
    assert view.layer0_incident.recurrence_risk is True

    # Layer 1 assertions
    assert view.layer1_causes is not None
    assert any(d["decision_id"] == dec_id for d in view.layer1_causes.cause_decisions)
    assert any(c["change_id"] == chg_id for c in view.layer1_causes.cause_changes)
    assert view.layer1_causes.linked_project is not None
    assert view.layer1_causes.linked_project["project_id"] == proj_id

    # Layer 2 assertions
    assert view.layer2_affected_scope is not None
    assert any(s["system_id"] == sys_id for s in view.layer2_affected_scope.affected_systems)
    assert any(l["location_id"] == loc_id for l in view.layer2_affected_scope.affected_locations)
    assert view.layer2_affected_scope.linked_project_context is not None
    assert len(view.layer2_affected_scope.linked_project_context["delayed_milestones"]) >= 1

    # Layer 3 assertions & sorting (overdue first)
    assert view.layer3_tasks is not None
    tasks = view.layer3_tasks.tasks
    assert len(tasks) == 3
    assert tasks[0]["status"] == "overdue"
    assert tasks[0]["task_id"] == t_overdue

    # Layer 4 assertions (forward recurrence link)
    assert view.layer4_recurrence is not None
    assert any(r["subsequent_incident_id"] == fwd_inc_id for r in view.layer4_recurrence.forward_recurrence)

    # Layer 5 assertions (people involved)
    assert view.layer5_people is not None
    assert any(p["person_id"] == assignee_id for p in view.layer5_people.task_assignees)
    assert any(p["person_id"] == lead_id for p in view.layer5_people.project_leads)

    # Layer 6 assertions (documents)
    assert view.layer6_documents is not None
    assert any(d["document_id"] == doc_id for d in view.layer6_documents.documents)

    # Layer 7 assertions (lessons)
    assert view.layer7_lessons is not None
    assert any(l["lesson_id"] == lesson_id for l in view.layer7_lessons.lessons)


@pytest.mark.asyncio
async def test_incident_view_access_policy_levels_1_2_3(incident_service, falkor):
    """
    UKGOE Step 10.2: Enforce INCIDENT_VIEW_ACCESS_POLICY Levels 1, 2, and 3
    - Level 3 (General): Layers 0-3 only. Layers 4-8 are None.
    - Level 2 (Team): Layers 0-6. Layers 7-8 are None.
    - Level 1 (Manager/Admin): All Layers 0-8.
    """
    suffix = uuid.uuid4().hex[:6]
    inc_id = f"inc:access-test-{suffix}"
    mgr_id = f"person:mgr-{suffix}"
    peer_id = f"person:peer-{suffix}"
    worker_id = f"person:worker-{suffix}"
    grp_id = f"group:sre-{suffix}"
    t_id = f"task:restore-{suffix}"

    cypher = f"""
    MERGE (inc:Incident {{id: '{inc_id}', title: 'Access Policy Outage {suffix}', severity: 'P2'}})
    MERGE (m:Person {{id: '{mgr_id}', name: 'Manager Mike'}})
    MERGE (w:Person {{id: '{worker_id}', name: 'Worker Wendy'}})
    MERGE (p:Person {{id: '{peer_id}', name: 'Peer Paul'}})
    MERGE (g:Group {{id: '{grp_id}', name: 'SRE Production'}})

    MERGE (m)-[:MANAGES]->(w)
    MERGE (w)-[:MEMBER_OF]->(g)
    MERGE (p)-[:MEMBER_OF]->(g)

    MERGE (t:Task {{id: '{t_id}', title: 'Restart cluster', status: 'open'}})
    MERGE (t)-[:RAISED_FROM]->(inc)
    MERGE (t)-[:ASSIGNED_TO]->(w)
    """
    falkor.query(cypher)

    # 1. Level 1 User (Manager of involved worker)
    mgr_user = User(
        id=201,
        email=f"mike.{suffix}@example.com",
        person_entity_id=mgr_id,
        role="Engineering Manager",
        clearance_level="Confidential",
        is_active=True,
    )
    lvl, desc = await incident_service.evaluate_incident_view_policy(mgr_user, inc_id)
    assert lvl == 1

    view_lvl1 = await incident_service.build_incident_interconnect_view(inc_id, mgr_user, access_level=1)
    assert view_lvl1.layer0_incident is not None
    assert view_lvl1.layer3_tasks is not None
    assert view_lvl1.layer4_recurrence is not None
    assert view_lvl1.layer5_people is not None
    assert view_lvl1.layer6_documents is not None
    assert view_lvl1.layer7_lessons is not None
    assert view_lvl1.layer8_similar_incidents is not None

    # 2. Level 2 User (Peer in same SRE group as involved worker)
    peer_user = User(
        id=202,
        email=f"paul.{suffix}@example.com",
        person_entity_id=peer_id,
        role="SRE Engineer",
        clearance_level="Internal",
        is_active=True,
    )
    lvl, desc = await incident_service.evaluate_incident_view_policy(peer_user, inc_id)
    assert lvl == 2

    view_lvl2 = await incident_service.build_incident_interconnect_view(inc_id, peer_user, access_level=2)
    assert view_lvl2.layer0_incident is not None
    assert view_lvl2.layer3_tasks is not None
    assert view_lvl2.layer4_recurrence is not None
    assert view_lvl2.layer5_people is not None
    assert view_lvl2.layer6_documents is not None
    assert view_lvl2.layer7_lessons is None  # Excluded from Level 2
    assert view_lvl2.layer8_similar_incidents is None  # Excluded from Level 2

    # 3. Level 3 User (Unrelated company member)
    unrelated_user = User(
        id=203,
        email=f"stranger.{suffix}@example.com",
        person_entity_id="person:stranger",
        role="Finance Analyst",
        clearance_level="Internal",
        is_active=True,
    )
    lvl, desc = await incident_service.evaluate_incident_view_policy(unrelated_user, inc_id)
    assert lvl == 3

    view_lvl3 = await incident_service.build_incident_interconnect_view(inc_id, unrelated_user, access_level=3)
    assert view_lvl3.layer0_incident is not None
    assert view_lvl3.layer1_causes is not None
    assert view_lvl3.layer2_affected_scope is not None
    assert view_lvl3.layer3_tasks is not None
    assert view_lvl3.layer4_recurrence is None  # Excluded from Level 3
    assert view_lvl3.layer5_people is None      # Excluded from Level 3
    assert view_lvl3.layer6_documents is None   # Excluded from Level 3
    assert view_lvl3.layer7_lessons is None
    assert view_lvl3.layer8_similar_incidents is None


@pytest.mark.asyncio
async def test_incident_view_people_privacy_redaction(incident_service, falkor):
    """
    UKGOE Step 10.3: Field-Level Privacy Redaction in Layer 5
    Non-privileged callers receive redacted email and internal roles.
    """
    suffix = uuid.uuid4().hex[:6]
    inc_id = f"inc:privacy-{suffix}"
    worker_id = f"person:priv-worker-{suffix}"
    t_id = f"task:priv-{suffix}"
    grp_id = f"group:priv-{suffix}"

    cypher = f"""
    MERGE (inc:Incident {{id: '{inc_id}', title: 'Privacy Test Incident'}})
    MERGE (w:Person {{
        id: '{worker_id}',
        name: 'Private Person {suffix}',
        email: 'secret.personal@example.com',
        role: 'Specialist II'
    }})
    MERGE (g:Group {{id: '{grp_id}', name: 'Operations'}})
    MERGE (w)-[:MEMBER_OF]->(g)
    MERGE (t:Task {{id: '{t_id}', title: 'Private task'}})
    MERGE (t)-[:RAISED_FROM]->(inc)
    MERGE (t)-[:ASSIGNED_TO]->(w)
    """
    falkor.query(cypher)

    # 1. Non-privileged caller (Level 2 with 'Internal' clearance, not HR)
    regular_caller = User(
        id=301,
        email=f"colleague.{suffix}@example.com",
        person_entity_id=f"person:colleague-{suffix}",
        role="Junior Developer",
        clearance_level="Internal",
        is_active=True,
    )
    # Link colleague to same group so they have Level 2 access
    falkor.query(f"MERGE (c:Person {{id: '{regular_caller.person_entity_id}'}})-[:MEMBER_OF]->(g:Group {{id: '{grp_id}'}})")

    view_redacted = await incident_service.build_incident_interconnect_view(inc_id, regular_caller, access_level=2)
    assert view_redacted.layer5_people is not None
    person_entry = view_redacted.layer5_people.task_assignees[0]
    assert person_entry["is_redacted"] is True
    assert person_entry["email"] == "[Redacted]"
    assert person_entry["role"] == "[Redacted]"

    # 2. Privileged caller (Admin / Level 1)
    admin_caller = User(
        id=1,
        email="admin@example.com",
        role="Executive Admin",
        clearance_level="Restricted",
        is_active=True,
    )
    view_full = await incident_service.build_incident_interconnect_view(inc_id, admin_caller, access_level=1)
    assert view_full.layer5_people is not None
    unredacted_entry = view_full.layer5_people.task_assignees[0]
    assert unredacted_entry["is_redacted"] is False
    assert unredacted_entry["email"] == "secret.personal@example.com"
    assert unredacted_entry["role"] == "Specialist II"


@pytest.mark.asyncio
async def test_incident_view_episodic_memory_and_view_count(incident_service, falkor):
    """
    UKGOE Step 10.4: View Access Audit & Graphiti :EpisodeMemory Logging
    - Viewing an incident increments view_count and updates last_viewed_at
    - Creates :EpisodeMemory and links [:TOUCHED] edges to the incident and traversed entities
    """
    suffix = uuid.uuid4().hex[:6]
    inc_id = f"inc:view-count-{suffix}"

    cypher = f"""
    MERGE (inc:Incident {{
        id: '{inc_id}',
        title: 'View Counter Test Incident {suffix}',
        view_count: 3
    }})
    """
    falkor.query(cypher)

    user = User(
        id=1,
        email="apex@gmail.com",
        role="Executive Admin",
        clearance_level="Restricted",
        is_active=True,
    )

    view = await incident_service.build_incident_interconnect_view(inc_id, user, access_level=1)

    async with AsyncSessionLocal() as session:
        await incident_service.record_view_access(
            incident_id=inc_id,
            user=user,
            view_response=view,
            db=session,
        )

    # 1. Assert view_count incremented in FalkorDB
    vc_res = falkor.query(f"MATCH (inc:Incident {{id: '{inc_id}'}}) RETURN inc.view_count, inc.last_viewed_at")
    assert vc_res[0][0] == 4
    assert vc_res[0][1] is not None

    # 2. Assert :EpisodeMemory node created and linked via [:TOUCHED]
    ep_res = falkor.query(
        f"MATCH (e:EpisodeMemory)-[:TOUCHED]->(inc:Incident {{id: '{inc_id}'}}) RETURN e.id, e.query_text"
    )
    assert len(ep_res) >= 1
    assert "Incident Interconnect View" in ep_res[0][1]

