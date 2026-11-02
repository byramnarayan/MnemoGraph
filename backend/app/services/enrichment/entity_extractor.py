from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Set


@dataclass
class ExtractedEntityResult:
    entity_type: str  # person, team, project, product, meeting, decision, ticket, artifact
    entity_value: str
    normalized_value: str
    confidence_score: float
    source_section_id: Optional[str] = None


class EntityExtractor:
    """
    Practical, deterministic entity extractor detecting:
    - People (@username, 'Owner: John Doe', 'Lead: Alice Smith')
    - Teams (team-*, * team, Engineering Team, Platform Team)
    - Projects (project-*, Project Apollo, Apollo Project, PROJ-123)
    - Tickets/Tasks (JIRA-1234, ABC-99, TASK-10, TICKET-22, issue #12)
    - Meetings (Daily Standup, Sprint Planning, Architecture Review, Sync with ...)
    - Decisions (Decision: ..., Decided to ..., ADR-*)
    - Artifacts (*.pdf, *.ipynb, notebook, dashboard)
    """

    TICKET_PATTERN = re.compile(r"\b([A-Z]{2,10}-\d{1,6})\b")
    ISSUE_PATTERN = re.compile(r"\b(?:issue|task|ticket)\s+#?(\d{1,6})\b", re.IGNORECASE)
    PERSON_HANDLE_PATTERN = re.compile(r"(?<!\w)@([a-zA-Z0-9_\.\-]+)")
    PERSON_LEAD_PATTERN = re.compile(
        r"\b(?:Author|Owner|Lead|Assigned to|Assignee|Speaker|Contributor|Reviewer|Driver)\s*[:=]\s*([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){1,2})",
        re.IGNORECASE,
    )
    TEAM_PATTERN = re.compile(
        r"\b([A-Z][a-zA-Z0-9_-]+\s+Team|Team\s+[A-Z][a-zA-Z0-9_-]+|Squad\s+[A-Z][a-zA-Z0-9_-]+)\b",
        re.IGNORECASE,
    )
    PROJECT_PATTERN = re.compile(
        r"\b(?:Project\s+([A-Z][a-zA-Z0-9_-]+)|([A-Z][a-zA-Z0-9_-]+)\s+Project)\b",
        re.IGNORECASE,
    )
    DECISION_PATTERN = re.compile(
        r"\b(?:Decision|ADR|Resolution)\s*[:\-#]\s*([A-Za-z0-9_\-\s]{4,60})|\b(decided\s+to\s+[a-z0-9_\-\s]{6,50})\b",
        re.IGNORECASE,
    )
    MEETING_PATTERN = re.compile(
        r"\b([A-Z][a-zA-Z\s]{2,25}(?:Standup|Sync|Planning|Retro|Retrospective|Review|All-Hands|Townhall|1:1))\b",
        re.IGNORECASE,
    )
    ARTIFACT_PATTERN = re.compile(
        r"\b([a-zA-Z0-9_\-]+\.(?:ipynb|py|sql|parquet|csv|pdf|json|md|yaml|yml))\b",
        re.IGNORECASE,
    )

    def extract(self, text: str, section_id: Optional[str] = None) -> List[ExtractedEntityResult]:
        if not text:
            return []

        results: List[ExtractedEntityResult] = []
        seen: Set[tuple[str, str]] = set()

        def add_entity(entity_type: str, val: str, confidence: float):
            clean_val = val.strip().strip(":,-.")
            if not clean_val or len(clean_val) < 2:
                return
            normalized = clean_val.lower()
            key = (entity_type, normalized)
            if key in seen:
                return
            seen.add(key)
            results.append(
                ExtractedEntityResult(
                    entity_type=entity_type,
                    entity_value=clean_val,
                    normalized_value=normalized,
                    confidence_score=confidence,
                    source_section_id=section_id,
                )
            )

        # 1. Tickets
        for m in self.TICKET_PATTERN.finditer(text):
            add_entity("ticket", m.group(1), 0.95)
        for m in self.ISSUE_PATTERN.finditer(text):
            add_entity("ticket", f"ISSUE-{m.group(1)}", 0.85)

        # 2. People handles (@username)
        for m in self.PERSON_HANDLE_PATTERN.finditer(text):
            handle = m.group(1)
            # Filter common false positives like email domains
            if handle.lower() not in {"example.com", "gmail.com", "databricks.com"}:
                add_entity("person", f"@{handle}", 0.9)

        # 3. People leadership / ownership phrases
        for m in self.PERSON_LEAD_PATTERN.finditer(text):
            name = m.group(1)
            add_entity("person", name, 0.95)

        # 4. Teams
        for m in self.TEAM_PATTERN.finditer(text):
            team_str = m.group(1)
            add_entity("team", team_str, 0.9)

        # 5. Projects
        for m in self.PROJECT_PATTERN.finditer(text):
            proj_name = m.group(1) or m.group(2)
            if proj_name and proj_name.lower() not in {"this", "the", "a", "our", "new"}:
                add_entity("project", f"Project {proj_name}", 0.9)

        # 6. Decisions
        for m in self.DECISION_PATTERN.finditer(text):
            dec_text = m.group(1) or m.group(2)
            if dec_text:
                add_entity("decision", dec_text.strip(), 0.85)

        # 7. Meetings
        for m in self.MEETING_PATTERN.finditer(text):
            meeting_name = m.group(1)
            add_entity("meeting", meeting_name.strip(), 0.9)

        # 8. Artifacts
        for m in self.ARTIFACT_PATTERN.finditer(text):
            art_name = m.group(1)
            add_entity("artifact", art_name.strip(), 0.9)

        return results

