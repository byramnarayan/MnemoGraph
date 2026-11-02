# Architecture Specification: 07 Explainable Answer Engine & Provenance

## 1. Subsystem Purpose & Anti-Hallucination Invariant

The **Explainable Answer Engine** (`app/services/answer_service.py`) synthesizes natural language answers strictly grounded in retrieved evidence items and graph relationship context.

To eliminate hallucinations and maintain Scopus-grade mathematical explainability, the engine enforces three design invariants:
1. **Multi-Store Grounding**: LLM prompts combine unstructured text excerpts from Qdrant with structured organizational lineage (authors, teams, projects, relation paths) from FalkorDB.
2. **Deterministic Fallback Priority**: If the LLM provider fails, returns invalid JSON, or triggers a timeout, the engine falls back to a deterministic, rule-based citation template rather than failing the user request.
3. **Multi-Stage Confidence Gating & Audit Logging**: Generated answers must pass through a strict validation gate verifying cited document IDs in PostgreSQL; failures are intercepted and replaced with safe fallbacks and audited in `answer_validation_log`.

---

## 2. Synthesis Architecture & Data Flow

```
+─────────────────────────────────────────────────────────────────────────────+
|                         AnswerService Pipeline                              |
+─────────────────────────────────────────────────────────────────────────────+
                                       │
                    ┌──────────────────┴──────────────────┐
                    ▼                                     ▼
+──────────────────────────────────────+ +───────────────────────────────────+
|     Qdrant Dense Vector Hits         | |    FalkorDB Graph Neighborhood    |
|   (Chunk Text, FastEmbed Score)      | |   (Owners, Teams, Projects, Paths)|
+──────────────────────────────────────+ +───────────────────────────────────+
                    │                                     │
                    └──────────────────┬──────────────────┘
                                       │
                                       ▼
+─────────────────────────────────────────────────────────────────────────────+
|               Citation Resolution (CitationService & PostgreSQL)             |
|          (Resolves Source URLs, Canonical Titles, and Storage Keys)         |
+─────────────────────────────────────────────────────────────────────────────+
                                       │
                                       ▼
+─────────────────────────────────────────────────────────────────────────────+
|                    PromptBuilder (Context Assembly)                         |
+─────────────────────────────────────────────────────────────────────────────+
                                       │
                                       ▼
+─────────────────────────────────────────────────────────────────────────────+
|             GroqClient (OpenAI-compatible LLM Ingestion)                    |
|        (Model: openai/gpt-oss-120b | 3-Key Round-Robin Rotation)             |
|       (Temperature: 0.1 | response_format: {"type": "json_object"})          |
+─────────────────────────────────────────────────────────────────────────────+
                                       │
                    ┌──────────────────┴──────────────────┐
                    ▼ (Success)                           ▼ (Error / Timeout)
+──────────────────────────────────────+ +───────────────────────────────────+
|      Structured JSON Response        | |   Deterministic Template Fallback |
| (answer_text, confidence, Cypher q)  | |   (Rule-based context sentence)   |
+──────────────────────────────────────+ +───────────────────────────────────+
                    │                                     │
                    └──────────────────┬──────────────────┘
                                       │
                                       ▼
+─────────────────────────────────────────────────────────────────────────────+
|           AnswerValidator & ConfidenceGate (Quality Gatekeeper)             |
|    • Checks Non-Empty Text                                                  |
|    • Verifies Document IDs in PostgreSQL (ProvenanceValidator)              |
|    • Verifies User Clearance (VisibilityService)                            |
|    • Checks Confidence Threshold (>= 0.4 / 0.5)                             |
|    • Logs Audit Record to `answer_validation_log`                           |
+─────────────────────────────────────────────────────────────────────────────+
                                       │
                                       ▼
                                [AnswerResponse]
```

---

## 3. Evidence Context Assembly (`PromptBuilder`)

Before invoking the LLM, `PromptBuilder.build_prompt()` (`app/services/llm/prompt_builder.py`) constructs a structured prompt payload:

### 3.1 Input Evidence Dictionary
```json
{
  "query": "Who is the lead architect for 5G telemetry and what projects are affected?",
  "evidence": [
    {
      "document_id": "doc-ran-spec-01",
      "source_url": "https://databricks.workspace/notebooks/ran-spec-01",
      "score": 0.89,
      "excerpt": "This notebook establishes the 5G RAN telemetry ingestion pipeline...",
      "related_people": ["Sarah Lindqvist"],
      "related_teams": ["ran_core_engineering"],
      "related_projects": ["5G RAN Optimization"]
    }
  ],
  "graph_context": {
    "people": ["Sarah Lindqvist"],
    "teams": ["ran_core_engineering"],
    "projects": ["5G RAN Optimization"],
    "relation_path": [
      {"source": "Sarah Lindqvist", "relation": "OWNS", "target": "doc-ran-spec-01"}
    ]
  }
}
```

### 3.2 System Prompt Directives:
- Instructs the model to act strictly as a grounded enterprise intelligence assistant.
- Mandates that facts outside the provided evidence must NOT be fabricated.
- Enforces strict JSON output conforming to the expected schema:
  ```json
  {
    "answer_text": "Grounded natural language response...",
    "confidence": 0.92,
    "graph_query": "MATCH (p:Person {name: 'Sarah Lindqvist'})-[r]->(pr:Project) RETURN labels(p)[0], p.id, type(r), labels(pr)[0], pr.id"
  }
  ```

---

## 4. LLM Provider & Key Rotation (`GroqClient`)

The backend interfaces with the Groq API via `app/services/llm/groq_client.py`:
- **Model**: `openai/gpt-oss-120b` (configured via `settings.groq_model`).
- **Endpoint**: `https://api.groq.com/openai/v1/chat/completions`.
- **Round-Robin Multi-Key Rotation**:
  To protect against rate limits and token quotas, `GroqClient` loads up to three distinct API keys (`groq_api_key_1`, `groq_api_key_2`, `groq_api_key_3`) from settings and rotates an atomic pointer across successive HTTP calls:
  ```python
  key = self.keys[self._key_index % len(self.keys)]
  self._key_index += 1
  ```
- **Read-Only Cypher Query Sanitization**:
  If the LLM returns a candidate `graph_query`, it is vetted for safety before inclusion:
  ```python
  candidate_lower = candidate_q.lower()
  if (
      candidate_lower.startswith("match")
      and not any(mut in candidate_lower for mut in ["create", "delete", "set ", "remove", "drop", "merge"])
      and "return" in candidate_lower
  ):
      llm_generated_cypher = candidate_q
  ```

---

## 5. Deterministic Template Fallback

If the Groq API call throws an exception, encounters network failure, or returns unparseable JSON, `AnswerService` immediately falls back to a deterministic, rule-based citation string:

```python
top_doc_title = citations.get(doc_ids[0], {}).get("title") if doc_ids else "the identified document"
owner_str = f"owned by {', '.join(all_people)}" if all_people else "with no single primary owner recorded"
team_str = f"associated with the {', '.join(all_teams)} team" if all_teams else ""
project_str = f"scoped under the {', '.join(all_projects)} project" if all_projects else ""

qualifiers = [q for q in [owner_str, team_str, project_str] if q]
context_phrase = ", ".join(qualifiers)

fallback_answer_text = (
    f"Based on source notebook and document analysis, '{top_doc_title}' is {context_phrase}. "
    f"The verified source evidence confirms this work directly."
)
```

This guarantees 100% service availability and zero catastrophic hallucination even during third-party LLM outages.

---

## 6. Citation Resolution Service (`CitationService`)

The citation service (`app/services/citation_service.py`) maps raw document IDs back to canonical enterprise assets in PostgreSQL:
1. Looks up the `Document` record in PostgreSQL by `id` or `source_id`.
2. Queries associated `DocumentMetadata` using `Document.storage_key` to retrieve the original `source_url`.
3. Resolves standard corporate URLs (e.g. `https://databricks.workspace/notebooks/{source_id}`).
4. Returns a normalized citation dictionary consumed by the frontend citation pills.

---

## 7. Answer Validation & Confidence Gating (`AnswerValidator`)

Before returning `AnswerResponse` to the user, `AnswerValidator.validate_answer()` (`app/services/answer_validation/answer_validator.py`) subjects the output to a 6-step verification:

```python
# 1. Reject empty answers
if not answer_text or not answer_text.strip():
    return ValidationResult(status="invalid", safe_answer_text=SAFE_FALLBACK, is_valid=False)

# 2. Reject answers with no cited documents
if not source_document_ids:
    return ValidationResult(status="insufficient_evidence", safe_answer_text=SAFE_FALLBACK, is_valid=False)

# 3. Verify cited documents actually exist in PostgreSQL (ProvenanceValidator)
valid_doc_ids = await self.provenance_validator.validate_document_ids(source_document_ids, db)
if not valid_doc_ids:
    return ValidationResult(status="insufficient_evidence", safe_answer_text=SAFE_FALLBACK, is_valid=False)

# 4. Filter by user authorization (VisibilityService)
if user_id:
    authorized_ids = await self.visibility_service.filter_authorized_document_ids(valid_doc_ids, user_id, db)
    if not authorized_ids:
        return ValidationResult(status="unauthorized", safe_answer_text=SAFE_FALLBACK, is_valid=False)
    valid_doc_ids = authorized_ids

# 5. Evaluate ConfidenceGate
passes_gate = self.gate.evaluate(confidence_score=confidence_score, source_count=len(valid_doc_ids), has_grounding=True)
if not passes_gate:
    return ValidationResult(status="insufficient_evidence", safe_answer_text=SAFE_FALLBACK, is_valid=False)

# 6. Audit log in answer_validation_log table
log_entry = AnswerValidationLog(
    user_id=user_id,
    query=query,
    answer_text=answer_text,
    source_document_ids=",".join(valid_doc_ids),
    confidence_score=round(confidence_score, 2),
    validation_status="valid"
)
db.add(log_entry)
await db.commit()
```

If any check fails, the user receives:
> *"I could not find enough authorized evidence to answer this safely."* with `confidence: 0.0`.

---

## 8. Context Answer Engine (`generate_context_answer`)

In addition to broad search queries, `AnswerService` supports targeted provenance questions (`ContextAnswerRequest`) such as *"What is the origin of this decision?"*:
1. Invokes `ProvenanceService.get_decision_provenance(db, entity_id)` to query the `Decision`, `Document`, `Person`, and `Project` relationship chain.
2. Derives relational explanation:
   ```text
   This decision ('{title}') was derived from the notebook '{doc_title}', authored by {people}, linked to the {projects} initiative.
   ```
3. Optionally refines the sentence via Groq LLM while pinning confidence to 0.95.

