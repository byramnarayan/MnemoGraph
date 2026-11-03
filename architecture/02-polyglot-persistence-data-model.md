# Architecture Specification: 02 Polyglot Persistence Data Model

## 1. Overview & Polyglot Mapping Strategy

MnemoGraph implements a strictly delineated **polyglot persistence model**. Rather than forcing graph traversals into a relational database or treating vector databases as document stores, each persistence technology is assigned an explicit set of entities, schemas, and lifecycle constraints.

```
                              +---------------------------------------+
                              |         Ingested Enterprise Entity    |
                              +---------------------------------------+
                                                  |
         +--------------------+-------------------+--------------------+
         |                    |                   |                    |
         v                    v                   v                    v
+------------------+ +------------------+ +------------------+ +------------------+
|    PostgreSQL    | |     FalkorDB     | |      Qdrant      | |    S3 / MinIO    |
| (Relational/Log) | | (Labeled Graph)  | |  (Dense Vectors) | | (Object Storage) |
|  • Metadata      | |  • Topology      | |  • 384-d vectors | |  • Raw binaries  |
|  • Section AST   | |  • OpenCypher    | |  • Chunk text    | |  • Checksums     |
|  • Version state | |  • Overlay memory| |  • UUIDv5 keys   | |  • Avatars       |
+------------------+ +------------------+ +------------------+ +------------------+
```

---

## 2. PostgreSQL Relational Schema & ORM Mapping

All relational schemas inherit from `app.core.database.Base` (`DeclarativeBase`) and are accessed via `SQLAlchemy 2.0` `AsyncSession`. The tables are divided into five functional clusters:

### 2.1 Identity, Organizations & Authentication

```sql
-- User Account Table (app/models/user.py)
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    tenant_slug VARCHAR(50),
    company_name VARCHAR(150),
    industry_vertical VARCHAR(100),
    department VARCHAR(100),
    role VARCHAR(50) NOT NULL DEFAULT 'Executive Admin',
    password_hash VARCHAR(255) NOT NULL,
    image_file VARCHAR(255) DEFAULT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Password Reset Tokens (app/models/user.py)
CREATE TABLE password_reset_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(64) UNIQUE NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 2.2 Enterprise Organizational Entities

```sql
-- Departments (app/models/connector.py)
CREATE TABLE departments (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(150) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Teams (app/models/connector.py)
CREATE TABLE teams (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(150) UNIQUE NOT NULL,
    department_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- People (app/models/connector.py)
CREATE TABLE people (
    id VARCHAR(36) PRIMARY KEY,
    full_name VARCHAR(150) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    role VARCHAR(100),
    team_id VARCHAR(100),
    department_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Projects (app/models/connector.py)
CREATE TABLE projects (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    description TEXT,
    workspace_id VARCHAR(100),
    owner_team_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Project Members (app/models/provenance.py)
CREATE TABLE project_members (
    id VARCHAR(36) PRIMARY KEY,
    project_id VARCHAR(36) NOT NULL,
    person_id VARCHAR(36) NOT NULL,
    role VARCHAR(100) NOT NULL DEFAULT 'Contributor',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 2.3 Connectors, Ingestion & Document Provenance

```sql
-- Connectors (app/models/connector.py)
CREATE TABLE connectors (
    id VARCHAR(36) PRIMARY KEY,
    org_id VARCHAR(100),
    name VARCHAR(150) NOT NULL,
    connector_type VARCHAR(50) NOT NULL DEFAULT 'databricks',
    host VARCHAR(255) NOT NULL,
    workspace_id VARCHAR(100) NOT NULL,
    token_encrypted TEXT NOT NULL,
    selected_warehouse_id VARCHAR(100),
    selected_tables TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'configured',
    auto_index BOOLEAN NOT NULL DEFAULT TRUE,
    sync_interval_minutes INTEGER NOT NULL DEFAULT 60,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Connector Sync Jobs (app/models/connector.py)
CREATE TABLE connector_sync_jobs (
    id VARCHAR(36) PRIMARY KEY,
    connector_id VARCHAR(36) NOT NULL REFERENCES connectors(id) ON DELETE CASCADE,
    mode VARCHAR(30) NOT NULL DEFAULT 'full',
    status VARCHAR(30) NOT NULL DEFAULT 'queued',
    started_at TIMESTAMPTZ DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    error_message TEXT,
    records_synced INTEGER NOT NULL DEFAULT 0,
    docs_indexed INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Source Entities (app/models/connector.py)
CREATE TABLE source_entities (
    id VARCHAR(36) PRIMARY KEY,
    connector_id VARCHAR(36) NOT NULL REFERENCES connectors(id) ON DELETE CASCADE,
    source_type VARCHAR(50) NOT NULL,
    source_id VARCHAR(255) NOT NULL,
    source_url TEXT,
    workspace_id VARCHAR(100),
    project_id VARCHAR(100),
    owner_user_id VARCHAR(100),
    team_id VARCHAR(100),
    title VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    synced_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Document Metadata (app/models/connector.py)
CREATE TABLE document_metadata (
    id VARCHAR(36) PRIMARY KEY,
    source_entity_id VARCHAR(36) NOT NULL REFERENCES source_entities(id) ON DELETE CASCADE,
    storage_key VARCHAR(255) NOT NULL,
    bucket_name VARCHAR(100) NOT NULL,
    mime_type VARCHAR(100),
    size_bytes INTEGER NOT NULL DEFAULT 0,
    checksum VARCHAR(64),
    source_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Document Versions (app/models/connector.py)
CREATE TABLE document_versions (
    id VARCHAR(36) PRIMARY KEY,
    document_id VARCHAR(36) NOT NULL REFERENCES document_metadata(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL DEFAULT 1,
    storage_key VARCHAR(255) NOT NULL,
    checksum VARCHAR(64),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Canonical Documents (app/models/connector.py)
CREATE TABLE documents (
    id VARCHAR(36) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    source_system VARCHAR(50) NOT NULL DEFAULT 'databricks',
    source_id VARCHAR(255) NOT NULL,
    project_id VARCHAR(100),
    team_id VARCHAR(100),
    owner_user_id VARCHAR(100),
    storage_key VARCHAR(255),
    mime_type VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 2.4 Structural Parsing & Extracted AST Encodings

```sql
-- Document Sections (app/models/document_section.py)
CREATE TABLE document_sections (
    id VARCHAR(36) PRIMARY KEY,
    document_id VARCHAR(100) NOT NULL,
    section_type VARCHAR(50) NOT NULL, -- heading, paragraph, list, code, table, sql
    heading VARCHAR(255),
    content TEXT NOT NULL,
    order_index INTEGER NOT NULL DEFAULT 0,
    source_start INTEGER NOT NULL DEFAULT 0,
    source_end INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Extracted Named Entities (app/models/document_section.py)
CREATE TABLE extracted_entities (
    id VARCHAR(36) PRIMARY KEY,
    document_id VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) NOT NULL, -- person, team, project, product, meeting, decision, ticket, artifact
    entity_value VARCHAR(255) NOT NULL,
    normalized_value VARCHAR(255) NOT NULL,
    confidence_score FLOAT NOT NULL DEFAULT 1.0,
    source_section_id VARCHAR(36) REFERENCES document_sections(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Explicit References & Mentions (app/models/document_section.py)
CREATE TABLE document_mentions (
    id VARCHAR(36) PRIMARY KEY,
    document_id VARCHAR(100) NOT NULL,
    mention_type VARCHAR(50) NOT NULL,
    mention_value VARCHAR(255) NOT NULL,
    normalized_value VARCHAR(255) NOT NULL,
    source_section_id VARCHAR(36),
    confidence_score FLOAT NOT NULL DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE project_mentions (
    id VARCHAR(36) PRIMARY KEY,
    document_id VARCHAR(100) NOT NULL,
    project_id VARCHAR(100) NOT NULL,
    mention_count INTEGER NOT NULL DEFAULT 1,
    source_section_id VARCHAR(36),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE decision_mentions (
    id VARCHAR(36) PRIMARY KEY,
    document_id VARCHAR(100) NOT NULL,
    decision_id VARCHAR(100) NOT NULL,
    mention_count INTEGER NOT NULL DEFAULT 1,
    source_section_id VARCHAR(36),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 2.5 Operational State, Reconciliation & Memory Logs

```sql
-- Document Version State (app/models/sync_reconciliation_job.py)
CREATE TABLE document_version_state (
    id VARCHAR(36) PRIMARY KEY,
    document_id VARCHAR(100) UNIQUE NOT NULL,
    source_id VARCHAR(255) NOT NULL,
    workspace_id VARCHAR(100),
    version_hash VARCHAR(64) NOT NULL, -- SHA-256
    previous_hash VARCHAR(64),
    last_synced_at TIMESTAMPTZ DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ DEFAULT NOW(),
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Sync Reconciliation Jobs (app/models/sync_reconciliation_job.py)
CREATE TABLE sync_reconciliation_jobs (
    id VARCHAR(36) PRIMARY KEY,
    connector_id VARCHAR(100) NOT NULL,
    source_type VARCHAR(50) NOT NULL DEFAULT 'databricks',
    mode VARCHAR(30) NOT NULL DEFAULT 'incremental',
    status VARCHAR(30) NOT NULL DEFAULT 'queued',
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    documents_checked INTEGER NOT NULL DEFAULT 0,
    documents_changed INTEGER NOT NULL DEFAULT 0,
    docs_deleted INTEGER NOT NULL DEFAULT 0,
    stale_edges_removed INTEGER NOT NULL DEFAULT 0,
    vector_entries_removed INTEGER NOT NULL DEFAULT 0,
    summary TEXT,
    errors TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Permission Policies (app/models/sync_reconciliation_job.py)
CREATE TABLE permission_policy (
    id VARCHAR(36) PRIMARY KEY,
    principal_type VARCHAR(50) NOT NULL, -- User, Team, Role, Public
    principal_id VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,    -- Document, Project, Workspace
    entity_id VARCHAR(100) NOT NULL,
    access_level VARCHAR(30) NOT NULL DEFAULT 'READ',
    scope VARCHAR(50) NOT NULL DEFAULT 'DIRECT', -- DIRECT, INHERITED
    inherited_from VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Answer Validation Audit Logs (app/models/sync_reconciliation_job.py)
CREATE TABLE answer_validation_log (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(100),
    query TEXT NOT NULL,
    answer_text TEXT NOT NULL,
    source_document_ids TEXT NOT NULL,
    confidence_score FLOAT NOT NULL DEFAULT 0.0,
    validation_status VARCHAR(50) NOT NULL, -- valid, insufficient_evidence, unauthorized, invalid
    failure_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Episodic Agent Memory (app/services/memory/memory_write_service.py)
CREATE TABLE agent_episodes (
    id VARCHAR(36) PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    tenant_id VARCHAR(50) NOT NULL DEFAULT 'telcosphere',
    session_id VARCHAR(100) NOT NULL,
    query_text TEXT NOT NULL,
    answer_text TEXT NOT NULL,
    confidence_score FLOAT NOT NULL DEFAULT 0.0,
    grounded_sources JSONB NOT NULL DEFAULT '[]'::jsonb,
    provenance_chain JSONB NOT NULL DEFAULT '[]'::jsonb,
    cypher_query TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Conversational Sessions (app/services/memory/memory_write_service.py)
CREATE TABLE memory_sessions (
    id VARCHAR(36) PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    tenant_id VARCHAR(50) NOT NULL DEFAULT 'telcosphere',
    session_id VARCHAR(100) NOT NULL UNIQUE,
    summary TEXT,
    last_activity_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Recalled Memory Entities (app/services/memory/memory_write_service.py)
CREATE TABLE memory_entities (
    id VARCHAR(36) PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    tenant_id VARCHAR(50) NOT NULL DEFAULT 'telcosphere',
    entity_type VARCHAR(50) NOT NULL,
    entity_value VARCHAR(255) NOT NULL,
    normalized_value VARCHAR(255) NOT NULL,
    frequency_count INTEGER NOT NULL DEFAULT 1,
    last_seen_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 3. FalkorDB Property Graph Schema & Enterprise Ontology Mapping

The property graph schema is defined via Enums in `app/services/graph/schema.py` and extended by the formal **Aarohan Digital Networks** enterprise ontology (`architecture/ontology.yaml`). It unifies operational entities into 7 functional domains:

### 3.1 Node Labels & Identity Schemes

| Domain | Node Label | Primary ID Key | Standard Properties | Codebase & Ontology Mapping |
| :--- | :--- | :--- | :--- | :--- |
| **Enterprise** | `:Company` | Singleton | `company_name`, `cin`, `incorporation_date`, `service_types` | Legal entity anchor for portfolio analysis |
| **Spatial** | `:SiteLocation` | `SITE-XXXX` | `id`, `city`, `address` | Co-located offices & data centers |
| **Organization**| `:Department` | `DEPT-XXXX` | `id`, `name`, `description` | `Department` ORM & functional divisions |
| **Organization**| `:Team` | `TEAM-XXXX` | `id`, `name`, `department_id`, `primary_site_id` | `Team` ORM & squad hierarchy |
| **Human Capital**| `:Employee` | `EMP-XXXX` | `id`, `full_name`, `email`, `role`, `skills`, `is_focal`, `status` | `Person` ORM alias with skill arrays |
| **Human Capital**| `:RoleHistory` | `UUID` | `employee_id`, `job_title`, `start_date`, `end_date`, `reason` | Career velocity & promotion tracking |
| **Delivery** | `:Project` | `PROJ-XXXX` | `id`, `name`, `status`, `planned_end_date`, `actual_end_date` | `Project` ORM & initiative tracker |
| **Delivery** | `:Milestone` | `UUID` | `project_id`, `name`, `target_date`, `actual_completion_date`, `delay_days` | Time-boxed project checkpoint |
| **Retrospective**| `:LessonLearned` | `LL-XXXX` | `id`, `project_id`, `description`, `causal_incident_id`, `causal_decision_id` | Post-project organizational learning |
| **Governance** | `:Decision` | `DEC-XXXX` | `id`, `title`, `decision_type`, `outcome`, `rationale`, `root_cause_analysis` | `Decision` ORM with RCA failure analysis |
| **Reliability** | `:Incident` | `INC-XXXX` | `id`, `title`, `severity` (P1-P4), `incident_type`, `confirmed_cause` | `Ticket` ORM alias with outage timeline |
| **Accountability**| `:FollowUpAction`| `ACT-XXXX` | `id`, `title`, `due_date`, `completion_date`, `status`, `effectiveness_label` | `Task` ORM alias with recurrence prevention |
| **Records** | `:BusinessDocument`| `DOC-XXXX` | `id`, `title`, `document_type` (PIR, ADR, CAT, etc.), `status`, `successor_doc_id` | `Document` ORM alias with revision lineage |
| **Infrastructure**| `:ServiceType` | `SVC-XXXX` | `id`, `name` | Telecom offerings (Broadband, FTTH, Leased Line) |
| **Memory** | `:EpisodeMemory` | `UUID` | `id`, `session_id`, `query`, `summary`, `created_at` | `GraphitiClient` experiential overlay |

### 3.2 Directional & Causal Relationship Topology

```cypher
// Organizational Hierarchy & Spatial Topology
(:Employee)-[:MEMBER_OF_TEAM]->(:Team)
(:Team)-[:BELONGS_TO_DEPARTMENT]->(:Department)
(:Team)-[:LOCATED_AT]->(:SiteLocation)
(:Employee)-[:WORKS_FROM]->(:SiteLocation)
(:Employee)-[:MANAGES {effective_from: date}]->(:Employee)
(:Employee)-[:HAD_ROLE]->(:RoleHistory)

// Project Delivery, Blockages & Checkpoints
(:Employee)-[:LEADS]->(:Project)
(:Employee)-[:CONTRIBUTES_TO]->(:Project)
(:Project)-[:SPONSORED_BY]->(:Department)
(:Project)-[:HAS_MILESTONE]->(:Milestone)
(:Project)-[:HAS_LESSON]->(:LessonLearned)
(:Project)-[:BLOCKED_BY_DECISION]->(:Decision)
(:Project)-[:BLOCKED_BY_INCIDENT]->(:Incident)

// Decision Governance & Rationale
(:Decision)-[:MADE_BY]->(:Employee)
(:Decision)-[:LINKED_TO_PROJECT]->(:Project)

// Incident Outages & Causal Recurrence Chains
(:Incident)-[:AFFECTS_SERVICE]->(:ServiceType)
(:Incident)-[:AFFECTS_SITE]->(:SiteLocation)
(:Incident)-[:LINKED_TO_PROJECT]->(:Project)
(:Incident)-[:CAUSED_RECURRENCE {via_action_id: 'ACT-XXXX'}]->(:Incident)

// Corrective Action Accountability & Resolution
(:FollowUpAction)-[:RAISED_FROM_INCIDENT]->(:Incident)
(:FollowUpAction)-[:RAISED_FROM_DECISION]->(:Decision)
(:FollowUpAction)-[:ASSIGNED_TO]->(:Employee)
(:FollowUpAction)-[:PREVENTED_RECURRENCE_OF]->(:Incident)

// Documentation, Retrospectives & Revisions
(:BusinessDocument)-[:DOCUMENTS]->(:AnyEntity)
(:BusinessDocument)-[:AUTHORED_BY]->(:Employee)
(:BusinessDocument)-[:SUPERSEDED_BY]->(:BusinessDocument)
(:LessonLearned)-[:LESSON_CAUSED_BY_INCIDENT]->(:Incident)
(:LessonLearned)-[:LESSON_CAUSED_BY_DECISION]->(:Decision)

// Cognitive Memory Overlay
(:Employee)-[:RECALLED {at: timestamp}]->(:EpisodeMemory)
(:EpisodeMemory)-[:TOUCHED]->(:AnyEntity)
```
```

---

## 4. Qdrant Dense Vector Data Model

The dense vector store operates on a single primary collection initialized through `app/services/vector/qdrant_client.py`:

```
Collection Name:       databricks_knowledge_chunks (configurable via settings)
Vector Dimension:      384
Distance Metric:       Cosine
Embeddings Engine:     FastEmbed (BAAI/bge-small-en-v1.5)
```

### 4.1 Point Identification & Payload Schema

Points are inserted into Qdrant as `qdrant_client.http.models.PointStruct` items using a deterministic UUIDv5 identifier:

```python
point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{document_id}_{chunk_index}"))
```

#### Payload Field Schema:

```json
{
  "document_id": "doc-uuid-string",
  "chunk_index": 0,
  "text": "Raw excerpt of text chunk (typically 400 words)",
  "title": "5G RAN Telemetry Mediation Notebook",
  "source_url": "https://databricks.workspace/documents/doc-uuid-string",
  "source_type": "notebook",
  "workspace_id": "ws-telecom-01",
  "project_id": "proj-ran-optimization",
  "owner_user_id": "sarah.lindqvist@telcosphere.com"
}
```

### 4.2 Stale Vector Deletion Filtering

During deletion or document re-indexing, Qdrant vectors are targeted by a `FieldCondition` filter on the payload's `document_id`:

```python
models.Filter(
    must=[
        models.FieldCondition(
            key="document_id",
            match=models.MatchValue(value=document_id)
        )
    ]
)
```

---

## 5. S3 Object Storage File Layout

Binary objects are stored in S3/MinIO via `app/services/storage/s3_store.py` and `app/services/s3_service.py`:

```
s3://baseproject-media/
├── avatars/
│   └── {uuid4}.(png|jpg|webp)
└── documents/
    └── {source_id}/
        └── {raw_filename}.(ipynb|pdf|docx|md|csv|json)
```

Every document upload registers:
- `bucket_name`: `settings.s3_bucket_name` (default: `"baseproject-media"`)
- `storage_key`: `"documents/{source_id}/{filename}"`
- `checksum`: Computed SHA-256 hex digest for data integrity verification
- `mime_type`: Resolved via `mimetypes` or HTTP Content-Type headers

