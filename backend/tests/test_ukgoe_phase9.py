from __future__ import annotations

import uuid
import pytest
from datetime import datetime, timezone
from sqlalchemy import select, text

from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.services.graph.falkordb_client import FalkorDBClient
from app.services.graph.inference_engine import UniversalInferenceEngine
from app.services.graph.ktp_service import KTPService


@pytest.fixture(scope="module")
def falkor():
    return FalkorDBClient()


@pytest.fixture(scope="module")
def ktp_service(falkor):
    return KTPService(client=falkor)


@pytest.fixture(scope="module")
def inference_engine(falkor):
    return UniversalInferenceEngine(falkordb_client=falkor)


@pytest.mark.asyncio
async def test_ktp_access_policy_gate(ktp_service, falkor):
    """
    UKGOE Step 9.1: Enforce KTP_ACCESS_POLICY Gate
    - Direct or 2-hop manager is authorized
    - System Administrator is authorized
    - Unauthorized junior peer or unrelated user is rejected (False)
    """
    suffix = uuid.uuid4().hex[:6]
    director_id = f"person:director-{suffix}"
    manager_id = f"person:manager-{suffix}"
    engineer_id = f"person:engineer-{suffix}"
    unrelated_id = f"person:unrelated-{suffix}"
    group_id = f"group:core-{suffix}"

    # Setup 2-hop management chain: Director -> Manager -> Engineer
    # And Group membership
    cypher_setup = f"""
    MERGE (d:Person {{id: '{director_id}', name: 'Director Dave', role: 'Director'}})
    MERGE (m:Person {{id: '{manager_id}', name: 'Manager Mary', role: 'Engineering Manager'}})
    MERGE (e:Person {{id: '{engineer_id}', name: 'Engineer Bob', role: 'Senior Engineer', employment_status: 'on_leave'}})
    MERGE (u:Person {{id: '{unrelated_id}', name: 'Junior John', role: 'Junior Engineer'}})
    MERGE (g:Group {{id: '{group_id}', name: 'Core Infrastructure'}})
    
    MERGE (d)-[:MANAGES]->(m)
    MERGE (m)-[:MANAGES]->(e)
    MERGE (m)-[:MEMBER_OF]->(g)
    MERGE (e)-[:MEMBER_OF]->(g)
    MERGE (u)-[:MEMBER_OF]->(g)
    """
    falkor.query(cypher_setup)

    # 1. Admin access
    admin_user = User(
        id=1,
        email="admin@example.com",
        role="Executive Admin",
        clearance_level="Restricted",
        is_active=True,
    )
    allowed, reason, eff_role = await ktp_service.evaluate_ktp_access(admin_user, engineer_id)
    assert allowed is True
    assert eff_role == "admin"

    # 2. 1-hop Manager access
    mgr_user = User(
        id=102,
        email=f"mary.{suffix}@example.com",
        person_entity_id=manager_id,
        role="Engineering Manager",
        clearance_level="Confidential",
        is_active=True,
    )
    allowed, reason, eff_role = await ktp_service.evaluate_ktp_access(mgr_user, engineer_id)
    assert allowed is True
    assert eff_role == "manager"

    # 3. 2-hop Manager (Director) access
    director_user = User(
        id=103,
        email=f"dave.{suffix}@example.com",
        person_entity_id=director_id,
        role="Director",
        clearance_level="Confidential",
        is_active=True,
    )
    allowed, reason, eff_role = await ktp_service.evaluate_ktp_access(director_user, engineer_id)
    assert allowed is True
    assert eff_role == "manager"

    # 4. Junior Peer in same group (not senior level) -> Denied
    junior_user = User(
        id=104,
        email=f"john.{suffix}@example.com",
        person_entity_id=unrelated_id,
        role="Junior Engineer",
        title="Junior Developer",
        clearance_level="Internal",
        is_active=True,
    )
    allowed, reason, eff_role = await ktp_service.evaluate_ktp_access(junior_user, engineer_id)
    assert allowed is False
    assert eff_role == "none"


@pytest.mark.asyncio
async def test_ktp_subgraph_extraction_sections_a_to_f(ktp_service, falkor):
    """
    UKGOE Step 9.2: Subgraph Extraction across Sections A through F
    Validates profile, active ownership, decisions, incidents, authored knowledge, and risk flags.
    """
    suffix = uuid.uuid4().hex[:6]
    person_id = f"person:lead-{suffix}"
    mgr_id = f"person:vp-{suffix}"
    group_id = f"group:data-{suffix}"
    proj_id = f"proj:lakehouse-{suffix}"
    task_id = f"task:migration-{suffix}"
    dec_id = f"dec:storage-choice-{suffix}"
    inc_id = f"inc:outage-{suffix}"
    doc_id = f"doc:arch-rfc-{suffix}"
    lesson_id = f"lesson:failover-{suffix}"

    cypher_seed = f"""
    MERGE (p:Person {{
        id: '{person_id}',
        name: 'Elena Rostova {suffix}',
        full_name: 'Elena Rostova {suffix}',
        role: 'Principal Architect',
        employment_status: 'inactive',
        skills: 'Python, Distributed Systems, FalkorDB, Kafka',
        owned_critical_items: 6,
        concentration_risk: true
    }})
    MERGE (vp:Person {{id: '{mgr_id}', name: 'VP Victor', role: 'VP Engineering'}})
    MERGE (g:Group {{id: '{group_id}', name: 'Data Platform'}})
    MERGE (vp)-[:MANAGES]->(p)
    MERGE (p)-[:MEMBER_OF]->(g)

    // Active Project & Milestone
    MERGE (proj:Project {{id: '{proj_id}', name: 'Lakehouse Migration', status: 'active', classification: 'Internal'}})
    MERGE (p)-[:LEADS]->(proj)
    MERGE (m:Milestone {{id: 'm1-{suffix}', name: 'Phase 1 Cutover', status: 'pending'}})
    MERGE (proj)-[:PART_OF]->(m)

    // Active Task
    MERGE (t:Task {{
        id: '{task_id}',
        title: 'Migrate Shards',
        status: 'open',
        due_date: '2026-12-01',
        effectiveness_label: 'pending',
        classification: 'Internal'
    }})
    MERGE (t)-[:ASSIGNED_TO]->(p)

    // Decision
    MERGE (dec:Decision {{
        id: '{dec_id}',
        title: 'Select Delta Engine',
        outcome: 'approved',
        decision_type: 'architectural',
        decision_date: '2026-05-10',
        root_cause_analysis: 'High throughput requirement',
        classification: 'Internal'
    }})
    MERGE (dec)-[:AUTHORED_BY]->(p)
    MERGE (dec)-[:LINKED_TO_PROJECT]->(proj)

    // Incident & Task linkage
    MERGE (inc:Incident {{
        id: '{inc_id}',
        title: 'Sharding Deadlock',
        severity: 'P1',
        type: 'database',
        cause_status: 'confirmed',
        classification: 'Internal'
    }})
    MERGE (t)-[:RAISED_FROM]->(inc)
    MERGE (inc)-[:LINKED_TO_PROJECT]->(proj)

    // Authored Knowledge & Lesson
    MERGE (doc:Document {{
        id: '{doc_id}',
        title: 'Lakehouse Partitioning Standard',
        document_type: 'architecture_specification',
        status: 'approved',
        creation_date: '2026-06-15',
        classification: 'Internal'
    }})
    MERGE (doc)-[:AUTHORED_BY]->(p)

    MERGE (les:Lesson {{
        id: '{lesson_id}',
        title: 'Automated Resharding Thresholds',
        summary: 'Reshard before 80% volume threshold to prevent locking.'
    }})
    MERGE (proj)-[:DERIVED_FROM]->(les)
    """
    falkor.query(cypher_seed)

    # Build KTP as Manager
    ktp = await ktp_service.build_ktp_package(
        target_person_id=person_id,
        requestor_id="1",
        requestor_role="manager",
        user_clearance="Confidential",
    )

    assert ktp.subject_person_id == person_id
    assert "Elena Rostova" in ktp.subject_person_name

    # Section A check
    assert ktp.section_a_profile is not None
    assert "Python" in ktp.section_a_profile.skills
    assert len(ktp.section_a_profile.manager_chain) >= 1

    # Section B check
    assert ktp.section_b_ownership is not None
    assert any(p["project_id"] == proj_id for p in ktp.section_b_ownership.active_projects)
    assert any(t["task_id"] == task_id for t in ktp.section_b_ownership.active_tasks)

    # Section C check
    assert ktp.section_c_decisions is not None
    assert any(d["decision_id"] == dec_id for d in ktp.section_c_decisions.decisions_made)

    # Section D check
    assert ktp.section_d_incidents is not None
    assert any(i["incident_id"] == inc_id for i in ktp.section_d_incidents.incidents_as_task_assignee)
    assert any(i["incident_id"] == inc_id for i in ktp.section_d_incidents.incidents_as_project_lead)

    # Section E check
    assert ktp.section_e_knowledge is not None
    assert any(d["document_id"] == doc_id for d in ktp.section_e_knowledge.authored_documents)
    assert any(l["lesson_id"] == lesson_id for l in ktp.section_e_knowledge.lessons_learned)

    # Section F check
    assert ktp.section_f_risks is not None
    assert ktp.section_f_risks.concentration_risk_score >= 1.0


@pytest.mark.asyncio
async def test_ktp_recommended_handover_actions(ktp_service, falkor):
    """
    UKGOE Step 9.3: Handover Recommendations in Section G
    - Identifies open tasks to reassign
    - Identifies projects needing lead
    - Identifies sole author documents
    - Recommends top matching successor candidates in the same group with overlapping skills
    """
    suffix = uuid.uuid4().hex[:6]
    departing_id = f"person:departing-{suffix}"
    group_id = f"group:ai-{suffix}"
    successor_top_id = f"person:succ-top-{suffix}"
    successor_low_id = f"person:succ-low-{suffix}"
    proj_id = f"proj:ai-platform-{suffix}"
    doc_id = f"doc:model-spec-{suffix}"

    cypher = f"""
    MERGE (dep:Person {{
        id: '{departing_id}',
        name: 'Dr. Alan Turing {suffix}',
        skills: 'Machine Learning, PyTorch, Graph Neural Networks, Cypher',
        employment_status: 'terminated'
    }})
    MERGE (grp:Group {{id: '{group_id}', name: 'AI Research'}})
    MERGE (dep)-[:MEMBER_OF]->(grp)

    // Potential successor 1 (High skill overlap: PyTorch, Graph Neural Networks, Cypher)
    MERGE (s1:Person {{
        id: '{successor_top_id}',
        name: 'Ada Lovelace {suffix}',
        role: 'Staff Researcher',
        skills: 'PyTorch, Graph Neural Networks, Cypher, CUDA',
        employment_status: 'active'
    }})
    MERGE (s1)-[:MEMBER_OF]->(grp)

    // Potential successor 2 (Low skill overlap: only Python)
    MERGE (s2:Person {{
        id: '{successor_low_id}',
        name: 'Charles Babbage {suffix}',
        role: 'Hardware Engineer',
        skills: 'Verilog, C, Architecture',
        employment_status: 'active'
    }})
    MERGE (s2)-[:MEMBER_OF]->(grp)

    // Active project led by departing person
    MERGE (prj:Project {{id: '{proj_id}', name: 'GNN Pipeline', status: 'active'}})
    MERGE (dep)-[:LEADS]->(prj)

    // Sole author document
    MERGE (d:Document {{id: '{doc_id}', title: 'GNN Architecture Spec', document_type: 'tech_spec'}})
    MERGE (d)-[:AUTHORED_BY]->(dep)
    """
    falkor.query(cypher)

    ktp = await ktp_service.build_ktp_package(
        target_person_id=departing_id,
        requestor_id="1",
        requestor_role="admin",
        user_clearance="Restricted",
    )

    assert ktp.section_g_handover is not None
    # 1. Projects needing replacement
    assert any(p["project_id"] == proj_id for p in ktp.section_g_handover.projects_needing_lead_or_contributor)

    # 2. Sole author doc identified
    assert any(d["document_id"] == doc_id for d in ktp.section_g_handover.sole_author_documents)

    # 3. Successor ranking: Ada Lovelace must rank first because of higher skill overlap
    candidates = ktp.section_g_handover.successor_candidates
    assert len(candidates) >= 1
    assert candidates[0].person_id == successor_top_id
    assert candidates[0].skill_overlap_count >= 2
    assert "pytorch" in [s.lower() for s in candidates[0].shared_skills]


@pytest.mark.asyncio
async def test_ktp_first_class_document_and_cascade_warning(ktp_service, inference_engine, falkor):
    """
    UKGOE Step 9.4: First-Class :Document Persistence & IR-09 Cascade Invalidation
    - Generates & persists :Document node with [:DOCUMENTS] edges
    - Updates target Person.ktp_generated = true
    - When a referenced entity is modified, IR-09 invalidation flags KTP as stale
    - get_ktp_document surfaces cascade_warning and is_stale=true
    """
    suffix = uuid.uuid4().hex[:6]
    person_id = f"person:departing-dev-{suffix}"
    proj_id = f"proj:billing-{suffix}"

    cypher = f"""
    MERGE (p:Person {{id: '{person_id}', name: 'Alice Bob {suffix}', employment_status: 'inactive'}})
    MERGE (proj:Project {{id: '{proj_id}', name: 'Billing Migration', status: 'active'}})
    MERGE (p)-[:LEADS]->(proj)
    """
    falkor.query(cypher)

    # 1. Build and Persist KTP
    ktp = await ktp_service.build_ktp_package(
        target_person_id=person_id,
        requestor_id="1",
        requestor_role="admin",
        user_clearance="Restricted",
    )
    doc_id = await ktp_service.persist_ktp_document(ktp)
    assert doc_id == ktp.doc_id

    # 2. Verify FalkorDB node and links
    doc_check = falkor.query(
        f"MATCH (d:Document {{id: '{doc_id}'}})-[:DOCUMENTS]->(target) RETURN d.title, d.document_type, target.id"
    )
    assert len(doc_check) >= 2  # Documents person and project
    assert doc_check[0][1] == "knowledge_transfer_package"

    person_check = falkor.query(
        f"MATCH (p:Person {{id: '{person_id}'}}) RETURN p.ktp_generated, p.ktp_doc_id"
    )
    assert person_check[0][0] is True
    assert person_check[0][1] == doc_id

    # 3. Initially retrieved KTP is fresh
    fresh_ktp = await ktp_service.get_ktp_document(doc_id)
    assert fresh_ktp is not None
    assert fresh_ktp.is_stale is False
    assert fresh_ktp.cascade_warning is None

    # 4. Trigger IR-09 Cascade Invalidation on referenced project
    invalidated = await inference_engine.evaluate_ir09_cascade_invalidation(proj_id)
    assert doc_id in invalidated

    # 5. Retrieve KTP again -> must now be flagged as stale with cascade warning
    stale_ktp = await ktp_service.get_ktp_document(doc_id)
    assert stale_ktp is not None
    assert stale_ktp.is_stale is True
    assert stale_ktp.cascade_warning is not None
    assert proj_id in stale_ktp.cascade_warning
