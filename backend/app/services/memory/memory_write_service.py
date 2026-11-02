from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.memory.graphiti_client import GraphitiClient

logger = logging.getLogger(__name__)


class MemoryWriteService:
    """
    Persists episodic and semantic memory across dual storage layers:
    1. PostgreSQL: Writes to agent_episodes, memory_sessions, and memory_entities
    2. FalkorDB: Creates :EpisodeMemory overlay nodes and connects them to touched business nodes
    """

    def __init__(self, graphiti: GraphitiClient | None = None):
        self.graphiti = graphiti or GraphitiClient()

    async def record_interaction(
        self,
        db: AsyncSession,
        user_id: int,
        user_email: str,
        session_id: str,
        query: str,
        answer: str,
        confidence_score: float,
        sources: list[dict[str, Any]],
        provenance_chain: list[dict[str, Any]],
        cypher_query: str | None,
        referenced_entity_ids: list[str] | None = None,
    ) -> str:
        episode_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        now_str = now.isoformat()
        ref_ids = referenced_entity_ids or []

        try:
            # 1. PostgreSQL: Insert into agent_episodes
            await db.execute(
                text("""
                    INSERT INTO agent_episodes (
                        id, user_id, tenant_id, session_id, query_text, answer_text,
                        confidence_score, grounded_sources, provenance_chain, cypher_query, created_at
                    ) VALUES (
                        :id, :user_id, 'telcosphere', :session_id, :query, :answer,
                        :conf, :sources, :prov, :cypher, :created_at
                    )
                """),
                {
                    "id": episode_id,
                    "user_id": user_id,
                    "session_id": session_id,
                    "query": query,
                    "answer": answer,
                    "conf": confidence_score,
                    "sources": json.dumps(sources),
                    "prov": json.dumps(provenance_chain),
                    "cypher": cypher_query,
                    "created_at": now,
                },
            )

            # 2. PostgreSQL: Upsert memory_sessions
            session_check = await db.execute(
                text("SELECT id FROM memory_sessions WHERE session_id = :sid"),
                {"sid": session_id},
            )
            session_row = session_check.fetchone()
            summary = query[:120]
            if not session_row:
                s_id = str(uuid.uuid4())
                await db.execute(
                    text("""
                        INSERT INTO memory_sessions (id, user_id, tenant_id, session_id, summary, last_activity_at, created_at)
                        VALUES (:id, :uid, 'telcosphere', :sid, :summary, :now, :now)
                    """),
                    {"id": s_id, "uid": user_id, "sid": session_id, "summary": summary, "now": now},
                )
            else:
                await db.execute(
                    text("UPDATE memory_sessions SET last_activity_at = :now, summary = :summary WHERE session_id = :sid"),
                    {"now": now, "summary": summary, "sid": session_id},
                )

            # 3. Extract & update memory_entities
            for src in sources:
                doc_title = src.get("title") or src.get("document_id") or ""
                if doc_title:
                    norm = doc_title.lower().strip()
                    ent_check = await db.execute(
                        text("SELECT id, frequency_count FROM memory_entities WHERE user_id = :uid AND normalized_value = :norm"),
                        {"uid": user_id, "norm": norm},
                    )
                    erow = ent_check.fetchone()
                    if erow:
                        await db.execute(
                            text("UPDATE memory_entities SET frequency_count = frequency_count + 1, last_seen_at = :now WHERE id = :eid"),
                            {"now": now, "eid": erow[0]},
                        )
                    else:
                        await db.execute(
                            text("""
                                INSERT INTO memory_entities (id, user_id, tenant_id, entity_type, entity_value, normalized_value, frequency_count, last_seen_at)
                                VALUES (:id, :uid, 'telcosphere', 'Document', :val, :norm, 1, :now)
                            """),
                            {"id": str(uuid.uuid4()), "uid": user_id, "val": doc_title, "norm": norm, "now": now},
                        )

            await db.commit()

            # 4. FalkorDB: Create Graphiti :EpisodeMemory overlay node & link to canonical entities
            self.graphiti.add_episode_memory(
                episode_id=episode_id,
                user_email=user_email,
                session_id=session_id,
                query=query,
                summary=answer[:250],
                referenced_entity_ids=ref_ids,
                timestamp_str=now_str,
            )

            return episode_id
        except Exception as e:
            logger.error(f"Error persisting memory interaction: {e}")
            await db.rollback()
            return episode_id

