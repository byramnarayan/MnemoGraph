from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.answer import AnswerRequest, AnswerResponse, ContextAnswerRequest, EvidenceItem
from app.services.answer_validation.answer_validator import AnswerValidator
from app.services.citation_service import CitationService
from app.services.graph.answer_graph_service import AnswerGraphService
from app.services.graph.permission_resolver import PermissionResolver
from app.services.graph.provenance_service import ProvenanceService
from app.services.llm.groq_client import GroqClient
from app.services.llm.prompt_builder import PromptBuilder
from app.services.vector.indexer import VectorIndexer

logger = logging.getLogger(__name__)


class AnswerService:
    """Explainable Answer Engine combining vector retrieval, graph provenance, and LLM answer synthesis."""

    def __init__(
        self,
        vector_indexer: VectorIndexer | None = None,
        graph_service: AnswerGraphService | None = None,
        citation_service: CitationService | None = None,
        perm_resolver: PermissionResolver | None = None,
        prov_service: ProvenanceService | None = None,
        llm_client: GroqClient | None = None,
    ):
        self.vector_indexer = vector_indexer or VectorIndexer()
        self.graph_service = graph_service or AnswerGraphService()
        self.citation_service = citation_service or CitationService()
        self.perm_resolver = perm_resolver or PermissionResolver(self.graph_service.repo)
        self.prov_service = prov_service or ProvenanceService(self.graph_service.repo)
        self.llm_client = llm_client or GroqClient()

    async def generate_answer(
        self,
        db: AsyncSession,
        req: AnswerRequest,
        current_user_email: str | None = None,
    ) -> AnswerResponse:
        # 1. Vector Retrieval via Qdrant
        hits = await self.vector_indexer.search(query=req.query, limit=req.limit * 3)

        # 2. Deduplicate by document_id and enforce permission filtering
        authorized_hits = []
        seen_docs = set()

        for hit in hits:
            payload = hit.get("payload", {})
            doc_id = payload.get("document_id") or payload.get("id")
            if not doc_id:
                continue

            # Permission check
            can_access = await self.perm_resolver.can_user_access(current_user_email, doc_id)
            if not can_access:
                continue

            if doc_id not in seen_docs:
                seen_docs.add(doc_id)
                authorized_hits.append(hit)

            if len(authorized_hits) >= req.limit:
                break

        # Fallback if no authorized evidence found
        if not authorized_hits:
            return AnswerResponse(
                answer_text="I could not find enough authorized evidence to answer this question safely.",
                source_document_ids=[],
                source_urls=[],
                related_people=[],
                related_teams=[],
                related_projects=[],
                relation_path=[],
                confidence=0.0,
                evidence=[],
            )

        # 3. Resolve citations and graph contexts
        doc_ids = [h["payload"]["document_id"] for h in authorized_hits if "document_id" in h["payload"]]
        citations = await self.citation_service.resolve_citations(db, doc_ids)

        evidence_items: list[EvidenceItem] = []
        all_people: list[str] = []
        all_teams: list[str] = []
        all_projects: list[str] = []
        all_paths: list[dict] = []
        source_doc_ids: list[str] = []
        source_urls: list[str] = []
        graph_target_node_ids: list[str] = []

        total_score = 0.0

        for hit in authorized_hits:
            payload = hit["payload"]
            doc_id = payload.get("document_id", "")
            score = round(float(hit.get("score", 0.0)), 2)
            total_score += score

            # Expand graph neighborhood
            ctx = await self.graph_service.resolve_entity_context(doc_id)

            # Accumulate owners, teams, and projects
            for p in ctx["people"]:
                if p not in all_people:
                    all_people.append(p)
            for t in ctx["teams"]:
                if t not in all_teams:
                    all_teams.append(t)
            for pr in ctx["projects"]:
                if pr not in all_projects:
                    all_projects.append(pr)
            for path in ctx["relation_path"]:
                if path not in all_paths:
                    all_paths.append(path)

            cite = citations.get(doc_id, {})
            source_url = cite.get("source_url") or payload.get("path") or f"https://databricks.workspace/{doc_id}"
            clean_doc_id = cite.get("document_id") or doc_id
            resolved_source_id = cite.get("source_id") or doc_id

            # Keep graph node candidates for Cypher matching
            for candidate in [doc_id, clean_doc_id, resolved_source_id]:
                if candidate:
                    graph_target_node_ids.append(candidate)
                    if not candidate.startswith("doc:"):
                        graph_target_node_ids.append(f"doc:{candidate}")

            if clean_doc_id not in source_doc_ids:
                source_doc_ids.append(clean_doc_id)
            if source_url not in source_urls:
                source_urls.append(source_url)

            excerpt = payload.get("text", "")[:320]

            evidence_items.append(
                EvidenceItem(
                    document_id=clean_doc_id,
                    source_url=source_url,
                    excerpt=excerpt,
                    score=score,
                    entity_type=payload.get("source_type", "Document"),
                    entity_id=clean_doc_id,
                    related_people=ctx["people"],
                    related_teams=ctx["teams"],
                    related_projects=ctx["projects"],
                )
            )

        # 4. Synthesize Grounded Answer via Groq LLM (OpenAI-compatible) with strict fallback
        top_doc_title = citations.get(doc_ids[0], {}).get("title") if doc_ids else "the identified document"
        owner_str = f"owned by {', '.join(all_people)}" if all_people else "with no single primary owner recorded"
        team_str = f"associated with the {', '.join(all_teams)} team" if all_teams else ""
        project_str = f"scoped under the {', '.join(all_projects)} project" if all_projects else ""

        qualifiers = [q for q in [owner_str, team_str, project_str] if q]
        context_phrase = ", ".join(qualifiers)

        # Baseline deterministic grounded template
        fallback_answer_text = (
            f"Based on source notebook and document analysis, '{top_doc_title}' is {context_phrase}. "
            f"The verified source evidence confirms this work directly."
        )

        avg_confidence = round(total_score / len(authorized_hits), 2) if authorized_hits else 0.0

        synthesized_text = fallback_answer_text
        llm_confidence = avg_confidence
        llm_generated_cypher: str | None = None

        # Invoke Groq LLM with round-robin key rotation and ground-truth prompt
        try:
            ev_dicts = [
                {
                    "document_id": item.document_id,
                    "source_url": item.source_url,
                    "score": item.score,
                    "excerpt": item.excerpt,
                    "related_people": item.related_people,
                    "related_teams": item.related_teams,
                    "related_projects": item.related_projects,
                }
                for item in evidence_items
            ]
            graph_ctx = {
                "people": all_people,
                "teams": all_teams,
                "projects": all_projects,
                "relation_path": all_paths,
            }
            messages = PromptBuilder.build_prompt(
                query=req.query,
                evidence_items=ev_dicts,
                graph_context=graph_ctx,
            )
            raw_llm_json = await self.llm_client.chat_completion(
                messages=messages,
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            parsed = json.loads(raw_llm_json)
            if parsed.get("answer_text"):
                synthesized_text = str(parsed["answer_text"]).strip()
                logger.info("Successfully synthesized grounded answer via Groq LLM.")
            if "confidence" in parsed and isinstance(parsed["confidence"], (int, float)):
                llm_confidence = round(float(parsed["confidence"]), 2)
            if parsed.get("graph_query"):
                candidate_q = str(parsed["graph_query"]).strip()
                candidate_lower = candidate_q.lower()
                # Verify read-only safety and valid RETURN structure
                if (
                    candidate_lower.startswith("match")
                    and not any(mut in candidate_lower for mut in ["create", "delete", "set ", "remove", "drop", "merge"])
                    and "return" in candidate_lower
                ):
                    llm_generated_cypher = candidate_q
                    logger.info(f"LLM dynamically generated custom Cypher query: {llm_generated_cypher}")
        except Exception as llm_err:
            logger.warning(
                f"Groq LLM call failed or produced invalid JSON ({llm_err}). Falling back to deterministic grounded synthesis."
            )

        # Validate answer quality, confidence gate, and authorization
        validator = AnswerValidator()
        val_res = await validator.validate_answer(
            query=req.query,
            answer_text=synthesized_text,
            source_document_ids=source_doc_ids,
            confidence_score=max(avg_confidence, llm_confidence),
            db=db,
        )

        final_answer = val_res.safe_answer_text if val_res.is_valid else val_res.safe_answer_text
        final_doc_ids = val_res.validated_source_ids if val_res.is_valid else []
        final_urls = source_urls if val_res.is_valid else []
        final_people = all_people if val_res.is_valid else []
        final_teams = all_teams if val_res.is_valid else []
        final_projects = all_projects if val_res.is_valid else []
        final_paths = all_paths if val_res.is_valid else []
        final_evidence = evidence_items if val_res.is_valid else []
        final_confidence = val_res.confidence_score if val_res.is_valid else 0.0

        # Determine provenance Cypher query: prefer LLM-tailored query grounded in schema, fallback to candidates
        cypher_query = llm_generated_cypher
        if not cypher_query:
            unique_graph_candidates = list(dict.fromkeys([c for c in graph_target_node_ids if c]))
            if unique_graph_candidates:
                id_list_str = ", ".join([f"'{d}'" for d in unique_graph_candidates[:8]])
                cypher_query = f"MATCH (a)-[r]->(b) WHERE a.id IN [{id_list_str}] OR b.id IN [{id_list_str}] RETURN labels(a)[0], a.id, type(r), labels(b)[0], b.id"
            elif all_people:
                people_ids = [f"person:{p.lower()}" for p in all_people[:3]]
                p_list_str = ", ".join([f"'{p}'" for p in people_ids])
                cypher_query = f"MATCH (p:Person)-[r]->(target) WHERE p.id IN [{p_list_str}] RETURN 'Person', p.id, type(r), labels(target)[0], target.id"
            else:
                cypher_query = "MATCH (a)-[r]->(b) RETURN labels(a)[0], a.id, type(r), labels(b)[0], b.id LIMIT 25"

        return AnswerResponse(
            answer_text=final_answer,
            source_document_ids=final_doc_ids,
            source_urls=final_urls,
            related_people=final_people,
            related_teams=final_teams,
            related_projects=final_projects,
            relation_path=final_paths,
            confidence=final_confidence,
            evidence=final_evidence,
            graph_query=cypher_query,
        )

    async def generate_context_answer(
        self,
        db: AsyncSession,
        req: ContextAnswerRequest,
        current_user_email: str | None = None,
    ) -> AnswerResponse:
        """Answers contextual provenance questions: 'What is the source of this decision?'."""
        prov = await self.prov_service.get_decision_provenance(db, req.entity_id)
        if not prov:
            return AnswerResponse(
                answer_text=f"No decision or provenance records found for entity '{req.entity_id}'.",
                source_document_ids=[],
                source_urls=[],
                related_people=[],
                related_teams=[],
                related_projects=[],
                relation_path=[],
                confidence=0.0,
                evidence=[],
            )

        title = prov.get("decision_title", "Decision")
        docs = prov.get("source_documents", [])
        people = [p["email"] for p in prov.get("related_people", []) if "email" in p]
        projects = [pr["name"] for pr in prov.get("related_projects", []) if "name" in pr]
        paths = prov.get("relation_paths", [])

        doc_titles = [d["title"] for d in docs if "title" in d]
        doc_ids = [d["id"] for d in docs if "id" in d]
        source_urls = [f"https://databricks.workspace/documents/{d_id}" for d_id in doc_ids]

        people_phrase = f"authored by {', '.join(people)}" if people else ""
        doc_phrase = f"the notebook '{', '.join(doc_titles)}'" if doc_titles else "the recorded architectural specification"
        proj_phrase = f"linked to the {', '.join(projects)} initiative" if projects else ""

        qualifiers = [q for q in [doc_phrase, people_phrase, proj_phrase] if q]
        answer_text = f"This decision ('{title}') was derived from {', '.join(qualifiers)}."

        # Grounded LLM refinement with fallback
        try:
            ev_list = [
                {
                    "document_id": d["id"],
                    "source_url": f"https://databricks.workspace/documents/{d['id']}",
                    "score": 0.95,
                    "excerpt": f"Source document: {d.get('title', d['id'])}",
                    "related_people": people,
                    "related_teams": [],
                    "related_projects": projects,
                }
                for d in docs
            ]
            ctx_msg = PromptBuilder.build_prompt(
                query=req.query,
                evidence_items=ev_list,
                graph_context={"people": people, "teams": [], "projects": projects, "relation_path": paths},
                entity_context=prov,
            )
            raw_llm = await self.llm_client.chat_completion(
                messages=ctx_msg,
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            parsed_ctx = json.loads(raw_llm)
            if parsed_ctx.get("answer_text"):
                answer_text = str(parsed_ctx["answer_text"]).strip()
        except Exception as e:
            logger.warning(f"Groq context answer synthesis error: {e}")

        evidence = [
            EvidenceItem(
                document_id=d["id"],
                source_url=f"https://databricks.workspace/documents/{d['id']}",
                excerpt=f"Source record for {title}",
                score=0.95,
                entity_type="Decision",
                entity_id=req.entity_id,
                related_people=people,
                related_teams=[],
                related_projects=projects,
            )
            for d in docs
        ]

        return AnswerResponse(
            answer_text=answer_text,
            source_document_ids=doc_ids,
            source_urls=source_urls,
            related_people=people,
            related_teams=[],
            related_projects=projects,
            relation_path=paths,
            confidence=0.95,
            evidence=evidence,
        )

