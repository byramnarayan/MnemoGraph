from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import desc, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser
from app.services.memory.memory_service import MemoryService

router = APIRouter()
memory_service = MemoryService()


class RecallRequest(BaseModel):
    query: str


@router.get("/history")
async def get_memory_history(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    order: str = "asc",  # asc = chronological ascending, desc = latest first
) -> list[dict[str, Any]]:
    """
    Returns user's episodic conversation history.
    Default order is chronological (ascending in timestamp).
    """
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
async def get_episode_details(
    episode_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """Retrieves deep details for a specific interaction episode."""
    query = text("""
        SELECT id, session_id, query_text, answer_text, confidence_score,
               grounded_sources, provenance_chain, cypher_query, created_at
        FROM agent_episodes
        WHERE id = :eid AND user_id = :uid
    """)
    res = await db.execute(query, {"eid": episode_id, "uid": current_user.id})
    r = res.fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="Episode memory not found")

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


@router.get("/sessions")
async def list_memory_sessions(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict[str, Any]]:
    """Lists conversation memory threads for current user."""
    query = text("""
        SELECT session_id, summary, last_activity_at, created_at
        FROM memory_sessions
        WHERE user_id = :uid
        ORDER BY last_activity_at DESC
    """)
    res = await db.execute(query, {"uid": current_user.id})
    rows = res.fetchall()
    return [
        {
            "session_id": r[0],
            "summary": r[1],
            "last_activity_at": r[2].isoformat() if r[2] else None,
            "created_at": r[3].isoformat() if r[3] else None,
        }
        for r in rows
    ]


@router.get("/entities")
async def list_remembered_entities(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict[str, Any]]:
    """Returns top entities tracked in semantic memory for the current user."""
    query = text("""
        SELECT entity_type, entity_value, frequency_count, last_seen_at
        FROM memory_entities
        WHERE user_id = :uid
        ORDER BY frequency_count DESC, last_seen_at DESC
        LIMIT 25
    """)
    res = await db.execute(query, {"uid": current_user.id})
    rows = res.fetchall()
    return [
        {
            "entity_type": r[0],
            "entity_value": r[1],
            "frequency_count": r[2],
            "last_seen_at": r[3].isoformat() if r[3] else None,
        }
        for r in rows
    ]


@router.delete("/sessions/{session_id}")
async def delete_memory_session(
    session_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """Purges a memory session thread."""
    await db.execute(
        text("DELETE FROM agent_episodes WHERE session_id = :sid AND user_id = :uid"),
        {"sid": session_id, "uid": current_user.id},
    )
    await db.execute(
        text("DELETE FROM memory_sessions WHERE session_id = :sid AND user_id = :uid"),
        {"sid": session_id, "uid": current_user.id},
    )
    await db.commit()
    return {"success": True, "message": f"Memory session '{session_id}' cleared."}


@router.post("/recall")
async def recall_context(
    req: RecallRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """Pre-retrieval context recall test."""
    return await memory_service.pre_search_recall(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        query=req.query,
    )

