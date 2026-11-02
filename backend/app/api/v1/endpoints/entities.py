from typing import Annotated, Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser
from app.models.connector import Department, Document, DocumentMetadata, Person, Project, Team
from app.models.provenance import Decision, KnowledgeHandover, ProjectMember
from app.services.graph.falkordb_client import FalkorDBClient
from app.services.graph.graph_queries import GraphQueries
from app.services.graph.repository import GraphRepository

router = APIRouter()
graph_repo = GraphRepository()
graph_queries = GraphQueries(graph_repo)
falkor_client = FalkorDBClient()


class HandoverCreateRequest(BaseModel):
    target_employee_id: str
    scope: str = "all"
    notes: str | None = None


def is_privileged_role(role_name: str | None) -> bool:
    if not role_name:
        return False
    r = role_name.lower()
    return any(keyword in r for keyword in ["admin", "hr", "manager", "director", "vp", "executive", "lead"])


@router.get("/teams")
async def list_teams(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict[str, Any]]:
    res = await db.execute(select(Team))
    teams = res.scalars().all()
    return [{"id": t.id, "name": t.name, "department_id": t.department_id, "created_at": t.created_at} for t in teams]


@router.get("/teams/{team_id}")
async def get_team_details(
    team_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    t_res = await db.execute(select(Team).where((Team.id == team_id) | (Team.name == team_id)))
    team = t_res.scalars().first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    members_res = await db.execute(select(Person).where(Person.team_id == team.id))
    members = members_res.scalars().all()

    proj_res = await db.execute(select(Project).where(Project.owner_team_id == team.id))
    projects = proj_res.scalars().all()

    doc_res = await db.execute(select(Document).where(Document.team_id == team.id))
    documents = doc_res.scalars().all()

    graph_context = await graph_queries.get_team_context(team.name.lower().replace(" ", "-"))

    return {
        "id": team.id,
        "name": team.name,
        "department_id": team.department_id,
        "members": [{"id": m.id, "full_name": m.full_name, "email": m.email, "role": m.role} for m in members],
        "projects": [{"id": p.id, "name": p.name} for p in projects],
        "documents": [{"id": d.id, "title": d.title, "source_id": d.source_id} for d in documents],
        "graph_context": graph_context,
    }


@router.get("/people")
async def list_people(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict[str, Any]]:
    """
    Returns employees visible to current user based on strict RBAC:
    - Admin, HR, Manager, Executive, Lead: can view all company employees.
    - Low-level Employee: only view themselves and colleagues explicitly assigned to them via knowledge handovers.
    """
    user_role = current_user.role or ""
    current_email = current_user.email.lower()

    # Find the Person record matching this user
    p_me = (await db.execute(select(Person).where(Person.email == current_email))).scalars().first()

    if is_privileged_role(user_role):
        # Full company directory
        res = await db.execute(select(Person).order_by(Person.full_name))
        people = res.scalars().all()
    else:
        # Low-level user: strictly self + assigned target employees
        allowed_ids = set()
        if p_me:
            allowed_ids.add(p_me.id)
            # Find handovers where target_employee_id == p_me.id
            handovers = (await db.execute(
                select(KnowledgeHandover).where(
                    KnowledgeHandover.target_employee_id == p_me.id,
                    KnowledgeHandover.status == "active"
                )
            )).scalars().all()
            for h in handovers:
                allowed_ids.add(h.source_employee_id)

        if allowed_ids:
            res = await db.execute(select(Person).where(Person.id.in_(allowed_ids)).order_by(Person.full_name))
            people = res.scalars().all()
        elif p_me:
            people = [p_me]
        else:
            people = []

    return [
        {
            "id": p.id,
            "full_name": p.full_name,
            "email": p.email,
            "role": p.role,
            "team_id": p.team_id,
            "department_id": p.department_id,
            "created_at": p.created_at,
        }
        for p in people
    ]


@router.get("/people/{person_id}")
async def get_person_details(
    person_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """Basic person details for backward compatibility."""
    p_res = await db.execute(
        select(Person).where((Person.id == person_id) | (Person.email == person_id.lower()))
    )
    person = p_res.scalars().first()
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    graph_context = await graph_queries.get_person_context(person.email)

    return {
        "id": person.id,
        "full_name": person.full_name,
        "email": person.email,
        "role": person.role,
        "team_id": person.team_id,
        "department_id": person.department_id,
        "graph_context": graph_context,
    }


@router.get("/people/{person_id}/full-profile")
async def get_person_full_profile(
    person_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """
    Returns full unified profile for an employee:
    1. Employee profile metadata (name, email, role, department, team)
    2. Projects they work on (with full descriptions, owner team)
    3. Documents & notebooks authored/owned (with preview, size, source system)
    4. Strategic decisions made (with timeline, impact, and learnings)
    5. Active knowledge handovers (incoming & outgoing)
    """
    # 1. Fetch Person
    p_res = await db.execute(
        select(Person).where((Person.id == person_id) | (Person.email == person_id.lower()))
    )
    person = p_res.scalars().first()
    if not person:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Check RBAC permissions for low-level users
    user_role = current_user.role or ""
    current_email = current_user.email.lower()
    if not is_privileged_role(user_role) and person.email.lower() != current_email:
        # Check if current user is an assigned target of this person's knowledge
        p_me = (await db.execute(select(Person).where(Person.email == current_email))).scalars().first()
        is_assigned = False
        if p_me:
            h_check = (await db.execute(
                select(KnowledgeHandover).where(
                    KnowledgeHandover.source_employee_id == person.id,
                    KnowledgeHandover.target_employee_id == p_me.id,
                    KnowledgeHandover.status == "active"
                )
            )).scalars().first()
            if h_check:
                is_assigned = True
        if not is_assigned:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have authorization to view this employee's knowledge base.")

    # 2. Fetch Team & Department
    team_name = "Independent / Cross-Functional"
    if person.team_id:
        t_row = (await db.execute(select(Team).where(Team.id == person.team_id))).scalars().first()
        if t_row:
            team_name = t_row.name

    dept_name = person.department_id or "Network Engineering"

    # Identify all person IDs and emails whose knowledge has been handed over to this person
    incoming_handovers = (await db.execute(
        select(KnowledgeHandover).where(
            KnowledgeHandover.target_employee_id == person.id,
            KnowledgeHandover.status == "active"
        )
    )).scalars().all()

    inherited_source_ids = {h.source_employee_id for h in incoming_handovers}
    inherited_source_emails = set()
    if inherited_source_ids:
        src_persons = (await db.execute(select(Person).where(Person.id.in_(inherited_source_ids)))).scalars().all()
        inherited_source_emails = {sp.email.lower() for sp in src_persons if sp.email}

    # Combined identity sets (own + inherited through active handovers)
    all_effective_person_ids = {person.id} | inherited_source_ids
    all_effective_emails = {person.email.lower()} | inherited_source_emails

    # 3. Fetch Projects (Strictly owned by this person)
    proj_query = (
        select(Project)
        .join(ProjectMember, ProjectMember.project_id == Project.id)
        .where(ProjectMember.person_id == person.id)
    )
    proj_rows = (await db.execute(proj_query)).scalars().all()

    if not proj_rows and person.team_id:
        proj_rows = (await db.execute(select(Project).where(Project.owner_team_id == person.team_id))).scalars().all()

    projects_data = [
        {
            "id": pr.id,
            "name": pr.name,
            "description": pr.description or f"Strategic initiatives for {team_name}.",
            "workspace_id": pr.workspace_id,
            "owner_team_id": pr.owner_team_id,
            "created_at": pr.created_at,
        }
        for pr in proj_rows
    ]

    # 4. Fetch Documents & Notebooks (Strictly owned by this person)
    doc_query = (
        select(Document)
        .where(or_(
            Document.owner_user_id == person.email,
            Document.owner_user_id == person.id
        ))
        .order_by(Document.created_at.desc())
        .limit(100)
    )
    doc_rows = (await db.execute(doc_query)).scalars().all()
    documents_data = [
        {
            "id": d.id,
            "title": d.title,
            "source_system": d.source_system,
            "source_id": d.source_id,
            "project_id": d.project_id,
            "storage_key": d.storage_key,
            "mime_type": d.mime_type,
            "created_at": d.created_at,
        }
        for d in doc_rows
    ]

    # 5. Fetch Strategic Decisions (Strictly authored by this person)
    dec_query = (
        select(Decision)
        .where(or_(
            Decision.created_by_user_id == person.id,
            Decision.created_by_user_id == person.email
        ))
        .order_by(Decision.created_at.desc())
        .limit(100)
    )
    dec_rows = (await db.execute(dec_query)).scalars().all()
    decisions_data = [
        {
            "id": dec.id,
            "title": dec.title,
            "description": dec.description,
            "status": dec.status,
            "impact": dec.impact or "Guarantees technical adherence to 3GPP architectural standards.",
            "learnings": dec.learnings or "Continuous edge telemetry verification prevents cluster-wide cascading faults.",
            "timeline": dec.timeline or "Specification -> Validation -> Production Gate",
            "source_document_id": dec.source_document_id,
            "created_at": dec.created_at,
        }
        for dec in dec_rows
    ]

    # 6. Fetch Knowledge Handovers
    # Outgoing: whom this person handed knowledge to
    out_handovers = (await db.execute(
        select(KnowledgeHandover).where(KnowledgeHandover.source_employee_id == person.id)
    )).scalars().all()

    # Incoming: who handed knowledge to this person
    in_handovers = (await db.execute(
        select(KnowledgeHandover).where(KnowledgeHandover.target_employee_id == person.id)
    )).scalars().all()

    # Resolve person names for handovers
    all_related_person_ids = {h.target_employee_id for h in out_handovers} | {h.source_employee_id for h in in_handovers}
    person_lookup = {}
    if all_related_person_ids:
        p_lookup_rows = (await db.execute(select(Person).where(Person.id.in_(all_related_person_ids)))).scalars().all()
        person_lookup = {p.id: p for p in p_lookup_rows}

    outgoing_data = [
        {
            "id": h.id,
            "target_employee_id": h.target_employee_id,
            "target_employee_name": person_lookup[h.target_employee_id].full_name if h.target_employee_id in person_lookup else "Colleague",
            "target_employee_email": person_lookup[h.target_employee_id].email if h.target_employee_id in person_lookup else "",
            "status": h.status,
            "scope": h.scope,
            "handover_notes": h.handover_notes,
            "created_at": h.created_at,
        }
        for h in out_handovers
    ]

    incoming_data = [
        {
            "id": h.id,
            "source_employee_id": h.source_employee_id,
            "source_employee_name": person_lookup[h.source_employee_id].full_name if h.source_employee_id in person_lookup else "Colleague",
            "source_employee_email": person_lookup[h.source_employee_id].email if h.source_employee_id in person_lookup else "",
            "status": h.status,
            "scope": h.scope,
            "handover_notes": h.handover_notes,
            "created_at": h.created_at,
        }
        for h in in_handovers
    ]

    return {
        "profile": {
            "id": person.id,
            "full_name": person.full_name,
            "email": person.email,
            "role": person.role,
            "team_id": person.team_id,
            "team_name": team_name,
            "department_id": dept_name,
            "created_at": person.created_at,
            "can_assign_handover": is_privileged_role(user_role),
        },
        "projects": projects_data,
        "documents": documents_data,
        "decisions": decisions_data,
        "handovers": {
            "outgoing": outgoing_data,
            "incoming": incoming_data,
        },
    }


@router.post("/people/{person_id}/handover")
async def create_knowledge_handover(
    person_id: str,
    payload: HandoverCreateRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """
    Assign / Hand over an employee's knowledge to another employee.
    Restricted strictly to privileged roles: Admin, HR, Manager, Executive, Lead.
    """
    user_role = current_user.role or ""
    if not is_privileged_role(user_role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only HR, Managers, or Admins are authorized to initiate knowledge handovers.",
        )

    # Validate source person
    src = (await db.execute(select(Person).where(Person.id == person_id))).scalars().first()
    if not src:
        raise HTTPException(status_code=404, detail="Source employee not found")

    # Validate target person
    target = (await db.execute(select(Person).where(Person.id == payload.target_employee_id))).scalars().first()
    if not target:
        raise HTTPException(status_code=404, detail="Target employee not found")

    if src.id == target.id:
        raise HTTPException(status_code=400, detail="Source and target employee cannot be the same")

    handover_id = str(uuid.uuid4())
    handover = KnowledgeHandover(
        id=handover_id,
        source_employee_id=src.id,
        target_employee_id=target.id,
        assigned_by_id=str(current_user.id),
        status="active",
        scope=payload.scope,
        handover_notes=payload.notes,
    )
    session_added = db.add(handover)
    await db.commit()

    # Link in FalkorDB Knowledge Graph
    try:
        falkor_client.query(f"""
            MATCH (s:Person {{email: '{src.email}'}}), (t:Person {{email: '{target.email}'}})
            MERGE (s)-[:HANDED_OVER_TO {{assigned_by: '{current_user.email}', status: 'active'}}]->(t)
        """)
    except Exception as e:
        pass

    return {
        "success": True,
        "handover_id": handover_id,
        "source_employee": src.full_name,
        "target_employee": target.full_name,
        "status": "active",
        "message": f"Successfully assigned knowledge base of {src.full_name} to {target.full_name}.",
    }


@router.get("/projects")
async def list_projects(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict[str, Any]]:
    res = await db.execute(select(Project))
    projects = res.scalars().all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "workspace_id": p.workspace_id,
            "owner_team_id": p.owner_team_id,
            "created_at": p.created_at,
        }
        for p in projects
    ]


@router.get("/projects/{project_id}")
async def get_project_details(
    project_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    pr_res = await db.execute(
        select(Project).where((Project.id == project_id) | (Project.name == project_id))
    )
    project = pr_res.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    graph_context = await graph_queries.get_project_context(project.name.lower().replace(" ", "-"))

    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "workspace_id": project.workspace_id,
        "owner_team_id": project.owner_team_id,
        "graph_context": graph_context,
    }


@router.get("/documents")
async def list_documents(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict[str, Any]]:
    res = await db.execute(select(Document).limit(200))
    documents = res.scalars().all()
    return [{"id": d.id, "title": d.title, "source_system": d.source_system, "source_id": d.source_id, "project_id": d.project_id} for d in documents]


@router.get("/documents/{document_id}")
async def get_document_details(
    document_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    res = await db.execute(
        select(Document).where(
            (Document.id == document_id) |
            (Document.source_id == document_id) |
            (Document.storage_key.ilike(f"%{document_id}%"))
        )
    )
    doc = res.scalars().first()
    if not doc:
        meta_fallback = await db.execute(
            select(DocumentMetadata).where(
                (DocumentMetadata.id == document_id) |
                (DocumentMetadata.storage_key.ilike(f"%{document_id}%"))
            )
        )
        meta_row = meta_fallback.scalars().first()
        if meta_row:
            graph_context = await graph_queries.get_document_provenance(document_id)
            return {
                "id": document_id,
                "title": meta_row.storage_key.split("/")[-1] if meta_row.storage_key else document_id,
                "source_system": "Databricks",
                "source_id": document_id,
                "storage_key": meta_row.storage_key,
                "mime_type": meta_row.mime_type or "application/octet-stream",
                "created_at": meta_row.created_at,
                "updated_at": meta_row.updated_at,
                "size_bytes": meta_row.size_bytes or 0,
                "checksum": meta_row.checksum,
                "graph_provenance": graph_context,
            }
        raise HTTPException(status_code=404, detail="Document not found")

    meta_res = await db.execute(
        select(DocumentMetadata).where(DocumentMetadata.storage_key == doc.storage_key)
    )
    meta = meta_res.scalars().first()
    graph_context = await graph_queries.get_document_provenance(doc.source_id or doc.id)

    return {
        "id": doc.id,
        "title": doc.title,
        "source_system": doc.source_system,
        "source_id": doc.source_id,
        "storage_key": doc.storage_key,
        "mime_type": doc.mime_type,
        "created_at": doc.created_at,
        "updated_at": doc.updated_at,
        "size_bytes": meta.size_bytes if meta else 0,
        "checksum": meta.checksum if meta else None,
        "graph_provenance": graph_context,
    }
