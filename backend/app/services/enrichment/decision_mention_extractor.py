from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.provenance import Decision


@dataclass
class DecisionMentionMatch:
    decision_id: str
    decision_title: str
    mention_count: int
    source_section_id: Optional[str] = None


class DecisionMentionExtractor:
    """
    Detects mentions of decisions inside documents and maps them to known decisions
    in PostgreSQL / Graph.
    """

    async def extract_mentions(
        self,
        text: str,
        db: AsyncSession,
        section_id: Optional[str] = None,
    ) -> List[DecisionMentionMatch]:
        if not text:
            return []

        stmt = select(Decision.id, Decision.title)
        result = await db.execute(stmt)
        known_decisions = result.fetchall()

        matches: List[DecisionMentionMatch] = []

        for d_id, d_title in known_decisions:
            if not d_title or len(d_title.strip()) < 3:
                continue

            # Word boundary search for decision title
            pattern = re.compile(rf"\b{re.escape(d_title)}\b", re.IGNORECASE)
            found = pattern.findall(text)
            if found:
                matches.append(
                    DecisionMentionMatch(
                        decision_id=d_id,
                        decision_title=d_title,
                        mention_count=len(found),
                        source_section_id=section_id,
                    )
                )

        return matches

