from __future__ import annotations

import json
from typing import Any


class PromptBuilder:
    """Constructs structured, ground-truth-bounded prompts for LLM answer synthesis."""

    SYSTEM_PROMPT = """You are the Grounded Enterprise Answer Engine.
Synthesize a concise, factual answer to the user's question using ONLY the provided evidence and graph context.

RULES:
1. Only make claims backed by the evidence. Do NOT hallucinate people, documents, or facts.
2. Keep `answer_text` concise (2-4 sentences max).
3. Generate a tailored, read-only Cypher query under `graph_query` to query the relevant traceback in FalkorDB.
   The query MUST return: `RETURN labels(a)[0], a.id, type(r), labels(b)[0], b.id`
4. Output ONLY valid JSON matching this schema:
{
  "answer_text": "<concise synthesized answer>",
  "source_document_ids": ["<document IDs from evidence>"],
  "source_urls": ["<URLs from evidence>"],
  "related_people": ["<people from evidence/graph>"],
  "related_teams": ["<teams from evidence/graph>"],
  "related_projects": ["<projects from evidence/graph>"],
  "relation_path": [{"from": "<node>", "to": "<target>", "relation": "<rel>"}],
  "confidence": 0.9,
  "graph_query": "MATCH (a)-[r]->(b) ... RETURN labels(a)[0], a.id, type(r), labels(b)[0], b.id"
}
"""

    @classmethod
    def build_prompt(
        cls,
        query: str,
        evidence_items: list[dict[str, Any]],
        graph_context: dict[str, Any],
        entity_context: dict[str, Any] | None = None,
    ) -> list[dict[str, str]]:
        """Constructs compact system and user messages to ensure response fits easily within token limits."""
        user_content_lines = [
            f"QUESTION: {query}",
            "",
            "EVIDENCE:",
        ]

        if not evidence_items:
            user_content_lines.append("No evidence.")
        else:
            for idx, ev in enumerate(evidence_items[:4], 1):
                clean_excerpt = (ev.get("excerpt") or "")[:200].replace("\n", " ")
                user_content_lines.append(
                    f"- Doc: {ev.get('document_id')} | Owners: {', '.join(ev.get('related_people', []))} | Excerpt: {clean_excerpt}"
                )

        user_content_lines.append("")
        user_content_lines.append(
            f"GRAPH: People={json.dumps(graph_context.get('people', []))} | Teams={json.dumps(graph_context.get('teams', []))} | Projects={json.dumps(graph_context.get('projects', []))}"
        )

        user_content_lines.append("")
        user_content_lines.append("GRAPH SCHEMA: Labels=(Person, Notebook, File, Workspace, Team, Decision, Project). Relations=(OWNS, CONTAINS, MEMBER_OF, BELONGS_TO, AUTHORED_BY, DEFINES).")
        user_content_lines.append("Return ONLY the requested JSON object.")

        return [
            {"role": "system", "content": cls.SYSTEM_PROMPT},
            {"role": "user", "content": "\n".join(user_content_lines)},
        ]

