from typing import Annotated, Any
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser
from app.schemas.answer import AnswerRequest, AnswerResponse
from app.services.answer_service import AnswerService
from app.services.memory.memory_service import MemoryService

router = APIRouter()
answer_service = AnswerService()
memory_service = MemoryService()


class SearchAskRequest(BaseModel):
    query: str
    session_id: str | None = None
    project_id: str | None = None
    workspace_id: str | None = None
    limit: int = 6


@router.post("")
async def search_and_answer(
    req: AnswerRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Memory-augmented search & answering engine:
    1. Pre-retrieval: Recall temporal context from Graphiti memory.
    2. Retrieval: Fetch canonical business facts from FalkorDB, Qdrant vectors, and Postgres metadata.
    3. Gating: Strict permission and RBAC enforcement.
    4. Synthesis: Groq LLM composes explainable response with citations.
    5. Persistence: Saves episode to PostgreSQL agent_episodes & FalkorDB Graphiti overlay.
    """
    user_email = current_user.email.lower()
    session_id = getattr(req, "session_id", None) or f"sess_{current_user.id}_{datetime_str()}"

    try:
        # Step 1: Pre-retrieval context recall via Graphiti memory overlay
        mem_ctx = await memory_service.pre_search_recall(
            db=db,
            user_id=current_user.id,
            user_email=user_email,
            query=req.query,
        )
        effective_query = mem_ctx.get("expanded_query", req.query)

        # Step 2 & 3 & 4: Execute retrieval-first synthesis
        augmented_req = AnswerRequest(
            query=effective_query,
            project_id=req.project_id,
            workspace_id=req.workspace_id,
            limit=req.limit,
        )
        answer_res = await answer_service.generate_answer(
            db=db,
            req=augmented_req,
            current_user_email=user_email,
        )

        # Prepare evidence dictionaries for memory persistence
        ev_sources = [
            {
                "document_id": ev.document_id,
                "source_url": ev.source_url,
                "excerpt": ev.excerpt,
                "score": ev.score,
                "related_people": ev.related_people,
                "related_teams": ev.related_teams,
                "related_projects": ev.related_projects,
            }
            for ev in answer_res.evidence
        ]
        prov_chain = answer_res.relation_path or []

        # Candidate canonical entity IDs for Graphiti memory linking
        referenced_entity_ids = []
        for p in answer_res.related_people:
            referenced_entity_ids.append(f"person:{p.lower()}")
        for pr in answer_res.related_projects:
            referenced_entity_ids.append(f"project:{pr.lower().replace(' ', '-')}")

        # Retrieve generated Cypher query (field name in AnswerResponse is graph_query)
        cypher_query_str = getattr(answer_res, "graph_query", None) or getattr(answer_res, "provenance_cypher", None)

        # Step 5: Post-retrieval persistence into PostgreSQL & FalkorDB
        episode_id = await memory_service.post_search_record(
            db=db,
            user_id=current_user.id,
            user_email=user_email,
            session_id=session_id,
            query=req.query,
            answer=answer_res.answer_text,
            confidence_score=answer_res.confidence,
            sources=ev_sources,
            provenance_chain=prov_chain,
            cypher_query=cypher_query_str,
            referenced_entity_ids=referenced_entity_ids,
        )

        # Return comprehensive response including episode ID and memory status
        return {
            **answer_res.model_dump(),
            "provenance_cypher": cypher_query_str,
            "graph_query": cypher_query_str,
            "episode_id": episode_id,
            "session_id": session_id,
            "memory_context_applied": mem_ctx.get("has_memory_context", False),
            "recent_recalled_topics": mem_ctx.get("recent_topics", []),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Knowledge retrieval error: {str(e)}")


@router.get("/history")
async def get_search_history(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    order: str = "asc",
) -> list[dict[str, Any]]:
    """Returns past asked questions in chronological order."""
    order_clause = "ASC" if order.lower() == "asc" else "DESC"
    query = text(f"""
        SELECT id, session_id, query_text, answer_text, confidence_score,
               grounded_sources, provenance_chain, cypher_query, created_at
        FROM agent_episodes
        WHERE user_id = :uid
        ORDER BY created_at {order_clause}
        LIMIT 100
    """)
    res = await db.execute(query, {"uid": current_user.id})
    rows = res.fetchall()

    return [
        {
            "id": r[0],
            "session_id": r[1],
            "query": r[2],
            "answer": r[3],
            "confidence": r[4],
            "sources": r[5] if isinstance(r[5], list) else [],
            "provenance": r[6] if isinstance(r[6], list) else [],
            "cypher_query": r[7],
            "created_at": r[8].isoformat() if r[8] else None,
        }
        for r in rows
    ]


@router.get("/history/{episode_id}")
async def get_history_episode(
    episode_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    query = text("""
        SELECT id, session_id, query_text, answer_text, confidence_score,
               grounded_sources, provenance_chain, cypher_query, created_at
        FROM agent_episodes
        WHERE id = :eid AND user_id = :uid
    """)
    res = await db.execute(query, {"eid": episode_id, "uid": current_user.id})
    r = res.fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="Interaction episode not found")

    return {
        "id": r[0],
        "session_id": r[1],
        "query": r[2],
        "answer": r[3],
        "confidence": r[4],
        "sources": r[5] if isinstance(r[5], list) else [],
        "provenance": r[6] if isinstance(r[6], list) else [],
        "cypher_query": r[7],
        "created_at": r[8].isoformat() if r[8] else None,
    }


def datetime_str() -> str:
    from datetime import datetime
    return datetime.utcnow().strftime("%Y%m%d%H%M")
