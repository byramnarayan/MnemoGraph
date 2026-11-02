from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connector import Project


@dataclass
class ProjectReferenceMatch:
    project_id: str
    project_name: str
    mention_count: int
    source_section_id: Optional[str] = None


class ProjectReferenceExtractor:
    """
    Detects project references in document text and maps them to known projects
    in PostgreSQL / Graph.
    """

    async def extract_references(
        self,
        text: str,
        db: AsyncSession,
        section_id: Optional[str] = None,
    ) -> List[ProjectReferenceMatch]:
        if not text:
            return []

        # Fetch active known projects from database
        stmt = select(Project.id, Project.name)
        result = await db.execute(stmt)
        known_projects = result.fetchall()

        matches: List[ProjectReferenceMatch] = []

        for p_id, p_name in known_projects:
            if not p_name or len(p_name.strip()) < 3:
                continue

            # Exact or word boundary regex for project name
            pattern = re.compile(rf"\b{re.escape(p_name)}\b", re.IGNORECASE)
            found = pattern.findall(text)
            if found:
                matches.append(
                    ProjectReferenceMatch(
                        project_id=p_id,
                        project_name=p_name,
                        mention_count=len(found),
                        source_section_id=section_id,
                    )
                )

        return matches

