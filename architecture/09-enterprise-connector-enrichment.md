# Architecture Specification: 09 Enterprise Connector & Document Enrichment

## 1. Subsystem Scope & Ingestion Mission

The **Enterprise Ingestion and Enrichment Subsystem** (`app/connectors/`, `app/services/parsers/`, and `app/services/enrichment/`) bridges unstructured corporate data assets and structured multi-store representations.

It ingests external workspace assets (primarily Databricks PySpark notebooks, SQL models, ADRs, and incidents) and executes five deterministic processing phases:
1. **Remote Workspace Harvesting**: Synchronizes files, notebooks, clusters, and jobs via the Databricks REST API.
2. **Multi-Format Extraction**: Parses raw files (`.ipynb`, `.pdf`, `.docx`, `.md`, `.txt`, `.csv`, `.json`) into plain text and structural AST blocks.
3. **Syntactic Section Breakdown**: Classifies content into headings, paragraphs, code blocks, lists, markdown tables, and SQL queries with exact character offsets.
4. **Named Entity & Reference Extraction**: Discovers people, teams, projects, tickets, decisions, and artifacts.
5. **Relational & Graph Synchronization**: Persists section and entity records in PostgreSQL and updates FalkorDB with `REFERENCES` and `MENTIONS` edges.

---

## 2. Ingestion Pipeline & Class Architecture

```
+─────────────────────────────────────────────────────────────────────────────+
|                          DatabricksSyncService                              |
|           (Pulls notebooks, files, jobs via Databricks REST API)            |
+─────────────────────────────────────────────────────────────────────────────+
                                       │
                                       ▼
+─────────────────────────────────────────────────────────────────────────────+
|                        DocumentParser & Storage                             |
|          • Writes raw content to S3 (DocumentStore)                         |
|          • Creates Document, DocumentMetadata, DocumentVersion in PG        |
+─────────────────────────────────────────────────────────────────────────────+
                                       │
                                       ▼
+─────────────────────────────────────────────────────────────────────────────+
|                          EnrichmentService                                  |
|                 (Top-Level Multi-Stage Orchestrator)                        |
+─────────────────────────────────────────────────────────────────────────────+
                                       │
         ┌───────────────────┬─────────┴─────────┬───────────────────┐
         ▼                   ▼                   ▼                   ▼
+─────────────────+ +─────────────────+ +─────────────────+ +─────────────────+
|  SectionParser  | | EntityExtractor | |ProjectReference | |    SQLParser    |
| (Headings, Code,| |(People, Teams,  | |& DecisionMention| | (Tables, Intent,|
| Tables, SQL AST)| | Projects, ADRs) | |   Extractors    | |     Columns)    |
+─────────────────+ +─────────────────+ +─────────────────+ +─────────────────+
         │                   │                   │                   │
         └───────────────────┼───────────────────┴───────────────────┘
                             │
                             ▼
+─────────────────────────────────────────────────────────────────────────────+
|               Multi-Store Persistence & Topology Linking                    |
|    • PostgreSQL: document_sections, extracted_entities, mentions            |
|    • FalkorDB: (:Document)-[:REFERENCES|MENTIONS]->(Entities)               |
|    • Qdrant: 400-word chunk vector embeddings via VectorIndexer             |
+─────────────────────────────────────────────────────────────────────────────+
```

---

## 3. Remote Workspace Connector (`DatabricksSyncService`)

The Databricks connector (`app/connectors/databricks/`) interacts directly with workspace instances:
- **Client Authentication**: Employs bearer token authentication (`token_encrypted` decrypted at runtime) against `settings.databricks_host`.
- **API Endpoints Invoked**:
  - `/api/2.0/workspace/list`: Recursively traverses directories to locate notebooks and files.
  - `/api/2.0/workspace/export`: Exports raw notebook sources in `SOURCE` or `JUPYTER` format.
  - `/api/2.0/clusters/list` & `/api/2.1/jobs/list`: Collects compute environment and job run provenance.
- **Relational Entity Mapping (`DatabricksMapper`)**:
  - Maps workspace items to `SourceEntity` records with `source_type="notebook"`.
  - Creates `DocumentMetadata` holding S3 `storage_key`, file sizes, and MIME types.
  - Registers `DocumentVersion` with incrementing revision numbers.

---

## 4. Multi-Format Document Parsing (`DocumentParser`)

Implemented in `app/services/parsers/document_parser.py`, supporting:
- **Jupyter & Databricks Notebooks (`.ipynb`)**: Deserializes JSON cells, separating markdown narrative from executable Python and PySpark blocks while preserving execution output.
- **Portable Document Format (`.pdf`)**: Extracts text streams page-by-page while tracking reading boundaries.
- **Word Documents (`.docx`)**: Iterates through paragraph elements and table rows.
- **Structured Data (`.json`, `.csv`)**: Formats key-value pairs and tabular rows into readable structured text blocks.
- **Plain Text & Markdown (`.md`, `.txt`)**: Ingested directly with UTF-8 normalization.

---

## 5. Structural Section Parsing (`SectionParser`)

In `app/services/enrichment/section_parser.py`, raw text is segmented into typed `ParsedSection` records:

```python
@dataclass
class ParsedSection:
    section_type: str  # heading, paragraph, list, code, table, sql
    content: str
    heading: Optional[str] = None
    order_index: int = 0
    source_start: int = 0
    source_end: int = 0
```

### Classification Heuristics:
1. **Headings**: Matches `#`, `##`, `###` prefixes or standalone uppercase strings; becomes the active `heading` context for subsequent paragraphs.
2. **Fenced Code**: Detects ` ``` ` boundaries, recording language indicators (`python`, `sql`, `sh`).
3. **SQL Queries**: Detects ` ```sql ` blocks or raw statements starting with SQL keywords (`SELECT`, `INSERT`, `CREATE`, `WITH`).
4. **Tables**: Recognizes markdown pipe tables (`| col1 | col2 |`).
5. **Lists**: Identifies bulleted (`* `, `- `) and ordered (`1. `) lines.
6. **Paragraphs**: Groups consecutive plain text lines, computing absolute character start and end offsets (`source_start`, `source_end`).

All sections are persisted to the PostgreSQL `document_sections` table.

---

## 6. Entity & Reference Extraction Pipeline

### 6.1 Named Entity Extraction (`EntityExtractor`)
`app/services/enrichment/entity_extractor.py` scans sections using compiled regex patterns and domain dictionaries:
- **Person**: Matches corporate emails (`[a-zA-Z0-9_.+-]+@telcosphere\.com`) and capitalized name sequences.
- **Team**: Detects known departments and squads (`ran_core_engineering`, `bss_oss_billing`, `telecom_security`, `noc_customer_ops`).
- **Project**: Discovers initiatives (`5G RAN Optimization`, `Mediation Modernization`).
- **Tickets & Incidents**: Identifies identifiers matching `INC-\d+`, `JIRA-\d+`, `TICK-\d+`.
- **Decisions & ADRs**: Matches `ADR-\d+` and decision title markers.
- **Meetings & Retrospectives**: Discovers sprint reviews, retrospectives, and architecture boards.

Each match is persisted in `extracted_entities` with `confidence_score` (0.80 to 1.0) and linked to `source_section_id`.

### 6.2 Reference Mentions (`ProjectReferenceExtractor` & `DecisionMentionExtractor`)
- Counts occurrences of known project IDs and architectural decisions within each section.
- Upserts rows into `project_mentions` and `decision_mentions` recording `mention_count`.

### 6.3 AST SQL Parsing (`SQLParser`)
When a section is typed as `sql`, `app/services/enrichment/sql_parser.py` extracts:
- **Query Intent**: `SELECT`, `INSERT`, `UPDATE`, `DELETE`, `CREATE`, `MERGE`.
- **Referenced Tables**: Extracted via `re.compile(r"\b(?:FROM|JOIN|INTO|UPDATE|TABLE)\s+([a-zA-Z0-9_.\`\"\[\]]+)")`.
- **Columns & Schemas**: Identifies catalog schemas (e.g. `telecom_prod.cdr.mediation_events`).

---

## 7. FalkorDB Graph Synchronization (`DocumentEnrichmentGraphService`)

Once sections and entities are persisted in PostgreSQL, `DocumentEnrichmentGraphService` executes Cypher queries to reflect structural linkages in FalkorDB:

```cypher
// 1. Link Document to Author / Owner
MATCH (p:Person {email: $owner_email}), (d:Document {id: 'doc:' + $document_id})
MERGE (p)-[:AUTHORED_BY]->(d);

// 2. Link Document to Scoped Project Container
MATCH (pr:Project {name: $project_name}), (d:Document {id: 'doc:' + $document_id})
MERGE (pr)-[:CONTAINS]->(d);

// 3. Create Explicit REFERENCES Edges for Project Mentions
MATCH (d:Document {id: 'doc:' + $document_id}), (pr:Project {id: $project_id})
MERGE (d)-[:REFERENCES]->(pr);

// 4. Create Explicit MENTIONS Edges for Extracted Entities
MATCH (d:Document {id: 'doc:' + $document_id}), (target {id: $entity_id})
MERGE (d)-[:MENTIONS]->(target);
```

---

## 8. Ingestion Management APIs (`app/api/v1/endpoints/`)

The ingestion pipeline is controlled via authenticated REST endpoints:
- `POST /api/v1/documents/upload`: Accepts file uploads via `multipart/form-data`, stores them in S3, parses sections, extracts entities, and triggers vector indexing.
- `POST /api/v1/connectors/{connector_id}/sync`: Triggers asynchronous Databricks workspace synchronization.
- `GET /api/v1/documents/{document_id}/sections`: Returns all structured sections and extracted entities for a document.
- `GET /api/v1/documents/{document_id}/entities`: Returns all named entities extracted with confidence scores.

