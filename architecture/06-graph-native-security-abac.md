# Architecture Specification: 06 Graph-Native Security & ABAC

## 1. Problem Definition & Security Invariant

In standard RAG pipelines, dense vector search engines operate as security-blind indices: any document indexed into the collection is eligible for semantic similarity retrieval regardless of organizational boundaries. Filtering results *after* generation leaks existence proofs and wastes LLM compute, while filtering *inside* the vector store requires maintaining duplicate metadata tags across thousands of chunk partitions.

MnemoGraph enforces a **Graph-Native Pre-Retrieval Authorization Invariant**:
> **Invariant**: No document candidate retrieved from Qdrant can enter evidence neighborhood expansion, LLM prompt assembly, or synthesis unless the requesting identity possesses verifiable transitive read clearance across the FalkorDB enterprise graph or relational permission policy tables.

---

## 2. Multi-Tier Permission Engine Architecture

Authorization logic is implemented across two cooperating layers:
1. **Graph Permission Resolver (`app/services/graph/permission_resolver.py`)**: Traverses FalkorDB relationships to evaluate real-time organizational ownership and team memberships.
2. **Relational ABAC & Policy Resolver (`app/services/permissions/`)**: Resolves hierarchical container inheritance (`Workspace` $\rightarrow$ `Project` $\rightarrow$ `Document`) and explicit role-based grants.

```
                              [Incoming Document Candidate (doc_id)]
                                                 │
                                                 ▼
                          +─────────────────────────────────────────────+
                          |   PermissionResolver (Graph / FalkorDB)     |
                          +─────────────────────────────────────────────+
                                                 │
                    ┌────────────────────────────┴────────────────────────────┐
                    ▼                                                         ▼
     [Direct Authorship / Ownership]                           [Team-Inherited Membership]
  (:Person)-[:OWNS|AUTHORED_BY]->(:Doc)                    (:Person)-[:MEMBER_OF]->(:Team)-[:OWNS]->(:Doc)
                    │                                                         │
                    └────────────────────────────┬────────────────────────────┘
                                                 │
                                                 ▼
                          +─────────────────────────────────────────────+
                          |  InheritedPermissionResolver (Relational)   |
                          +─────────────────────────────────────────────+
                                                 │
                    ┌────────────────────────────┴────────────────────────────┐
                    ▼                                                         ▼
      [Container Project Ownership]                            [Explicit Permission Policy]
  Document.project_id -> Project.owner_team_id               SELECT FROM permission_policy WHERE ...
                                                 │
                                                 ▼
                          +─────────────────────────────────────────────+
                          |      VisibilityService Decision Gating      |
                          |      (Allow Hit or Drop from Evidence)      |
                          +─────────────────────────────────────────────+
```

---

## 3. Graph-Native Authorization Traversals (`app/services/graph/permission_resolver.py`)

When `AnswerService` receives candidate vector chunks from Qdrant, it passes the caller's email and the chunk's `document_id` to `PermissionResolver.can_user_access()`:

```python
person_id = f"person:{user_email.lower()}"
doc_node_id = f"doc:{entity_id}"
```

The graph resolver evaluates three sequential clearance checks:

### 3.1 Direct Authorship and Ownership Check
Inspects incoming edges targeting `doc_node_id` in FalkorDB:
```cypher
MATCH (p:Person {id: $person_id})-[r:OWNS|AUTHORED_BY|CREATED_BY]->(d:Document {id: $doc_node_id})
RETURN count(r) > 0;
```
If the requesting user is the direct author or owner, read access is granted immediately.

### 3.2 Transitive Team Membership Check
If direct ownership is absent, the resolver queries the caller's team affiliations:
```cypher
// Discover user teams
MATCH (p:Person {id: $person_id})-[:MEMBER_OF]->(t:Team)
RETURN t.id;
```
It then checks whether any incoming edge on `doc_node_id` originates from one of the user's teams:
```cypher
MATCH (t:Team)-[r:OWNS|HAS_PERMISSION]->(d:Document {id: $doc_node_id})
WHERE t.id IN $user_teams
RETURN count(r) > 0;
```
If a team match is confirmed, transitive access is granted.

### 3.3 Default Corporate Clearance
If a document has no explicit restrictive `HAS_PERMISSION` edges attached in FalkorDB, it is treated as open internal corporate documentation, allowing internal team members to retrieve it.

---

## 4. Relational Policy Inheritance (`app/services/permissions/`)

For granular attribute-based access control, `InheritedPermissionResolver` evaluates policies stored in PostgreSQL across four scopes:

### 4.1 Container Hierarchy Resolution

Permissions cascade downward along container boundaries:

```
+─────────────────────────────────────────────────────────────+
|                          WORKSPACE                          |
|  (Workspace admins hold implicit clearance over all items)  |
+─────────────────────────────────────────────────────────────+
                               │
                               ▼
+─────────────────────────────────────────────────────────────+
|                           PROJECT                           |
|  (Project.owner_team_id grants inherited access to docs)    |
+─────────────────────────────────────────────────────────────+
                               │
                               ▼
+─────────────────────────────────────────────────────────────+
|                          DOCUMENT                           |
|  (Document.owner_user_id grants DIRECT ADMIN)               |
|  (Document.team_id grants DIRECT READ)                      |
+─────────────────────────────────────────────────────────────+
```

1. **Document Direct Grants**:
   - `Document.owner_user_id` $\rightarrow$ `AccessGrant(principal_type="User", access_level="ADMIN", scope="DIRECT")`
   - `Document.team_id` $\rightarrow$ `AccessGrant(principal_type="Team", access_level="READ", scope="DIRECT")`
2. **Project Inherited Grants**:
   - Queries `Project` where `id == Document.project_id`.
   - If `Project.owner_team_id` exists $\rightarrow$ `AccessGrant(principal_type="Team", principal_id=proj.owner_team_id, access_level="READ", scope="INHERITED", inherited_from=f"Project:{proj.id}")`
3. **Explicit Database Policies**:
   - Queries `permission_policy` table where `entity_type == 'Document'` and `entity_id == Document.id`.
   - Appends matching user, team, or role-based policies.

---

## 5. Pre-Retrieval Filtering Pipeline (`AnswerService`)

In `app/services/answer_service.py`, authorization filtering occurs before citation extraction, evidence neighborhood expansion, or LLM invocation:

```python
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
```

### Fail-Safe Fallback:
If all candidate hits are pruned due to lack of clearance:
```python
if not authorized_hits:
    return AnswerResponse(
        answer_text="I could not find enough authorized evidence to answer this question safely.",
        source_document_ids=[],
        confidence=0.0,
        evidence=[]
    )
```
No prompt is sent to the LLM, completely preventing unauthorized information leakage.

---

## 6. Access Evaluation APIs (`app/api/v1/endpoints/permissions.py`)

The permissions subsystem exposes four management and auditing endpoints:

| Endpoint | Method | Input Parameters | Operational Output |
| :--- | :--- | :--- | :--- |
| `/api/v1/permissions/policies` | `POST` | `PermissionPolicyCreate` schema | Persists an explicit direct permission policy in PostgreSQL. |
| `/api/v1/permissions/policies/{entity_type}/{entity_id}` | `GET` | `entity_type`, `entity_id` | Returns all direct policies registered for that entity. |
| `/api/v1/permissions/check` | `POST` | `user_id`, `entity_type`, `entity_id` | Returns `PermissionCheckResult(allowed=bool, access_level=str)`. |
| `/api/v1/permissions/inherited/{entity_type}/{entity_id}` | `GET` | `entity_type`, `entity_id` | Returns resolved list of direct and inherited `AccessGrant` items. |

