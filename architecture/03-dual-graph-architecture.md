# Architecture Specification: 03 Dual-Graph Architecture & Predictive Telecom Ontology

## 1. Architectural Philosophy: Dual-Graph Separation

In conventional enterprise AI systems, conversational memory is either completely absent (stateless amnesia) or dumped into the same database tables as corporate facts, risking memory pollution, provenance corruption, and data poisoning.

MnemoGraph enforces a **strict dual-layer graph model** hosted within FalkorDB (`enterprise_knowledge_graph`):

```
+─────────────────────────────────────────────────────────────────────────────+
│                       FalkorDB Property Graph Engine                        │
│                                                                             │
│  +───────────────────────────────────────────────────────────────────────+  │
│  │                    LAYER 1: CANONICAL ENTERPRISE GRAPH                │  │
│  │                                                                       │  │
│  │    (:Company) ──[:OWNS]──► (:Department) ──[:CONTAINS]──► (:Team)     │  │
│  │       │                                                      │        │  │
│  │    [:OPERATES_FROM]                                      [:LOCATED_AT]│
│  │       ▼                                                      ▼        │  │
│  │    (:SiteLocation) ◄───────────────────────────────── (:SiteLocation) │  │
│  │       ▲                                                      ▲        │  │
│  │    [:AFFECTS_SITE]                                        [:WORKS_FROM]
│  │       │                                                      │        │  │
│  │    (:Incident) ──[:CAUSED_RECURRENCE]──► (:Incident)         (:Employee)│
│  │       │   ▲                                                  ▲        │  │
│  │       │   └─[:RAISED_FROM]─ (:FollowUpAction) ──[:ASSIGNED_TO]┘        │  │
│  │       ▼                                                               │  │
│  │    (:ServiceType)          (:Decision) ──[:MADE_BY]───────────────────┘  │
│  │                               │       ▲                               │  │
│  │      [:BLOCKED_BY_DECISION]───┘       │                               │  │
│  │      ▼                                │                               │  │
│  │    (:Project) ──[:HAS_MILESTONE]──► (:Milestone)                     │  │
│  │       │                                                               │  │
│  │       └──[:HAS_LESSON]─────────────► (:LessonLearned)                 │  │
│  │                                                                       │  │
│  │    (:BusinessDocument) ──[:DOCUMENTS]──► (Any Canonical Entity)       │  │
│  +───────────────────────────────────────────────────────────────────────+  │
│                                      ▲                                      │
│                                      │ [:TOUCHED]                           │
│  +───────────────────────────────────┴───────────────────────────────────+  │
│  │                   LAYER 2: COGNITIVE MEMORY OVERLAY                   │  │
│  │                                                                       │  │
│  │    (:Employee) ──[:RECALLED {at: ts}]──► (:EpisodeMemory)             │  │
│  │                                              │                        │  │
│  │                                              └──[:TOUCHED]──► (Target)│  │
│  +───────────────────────────────────────────────────────────────────────+  │
+─────────────────────────────────────────────────────────────────────────────+
```

1. **Layer 1: Canonical Enterprise Graph (Authoritative Truth & Predictive Ontology)**
   - Permanently stores organizational entities, structural hierarchies, technical specifications, causal incident chains, architectural decisions, and operational metrics.
   - Synchronized deterministically from Databricks, object storage, and PostgreSQL.
   - Subject to strict organizational ABAC and ownership policies.
   - Cannot be modified or mutated by user chat interactions.

2. **Layer 2: Cognitive Memory Overlay (Experiential Awareness)**
   - Records historical user episodes and conversational focus using `:EpisodeMemory` nodes.
   - Links episodes to the user's canonical `:Employee` (`:Person`) persona using directional `:RECALLED` edges.
   - Anchors episodes to canonical entities referenced during answering using directional `:TOUCHED` edges.
   - Enables pre-retrieval context expansion and anaphora resolution without altering canonical business nodes.

---

## 2. Canonical Graph Layer Schema: Enterprise Telecom Ontology

To empower the engine with root-cause tracing, risk forecasting, and hidden-pattern discovery, the canonical graph implements the formal **Aarohan Digital Networks** enterprise ontology (`architecture/ontology.yaml`).

### 2.1 Node Class Taxonomy (7 Functional Domains)

| Domain | Node Label | Prefix / Key Format | Key Properties | Business & Predictive Role |
| :--- | :--- | :--- | :--- | :--- |
| **Enterprise** | `:Company` | Singleton | `company_name`, `cin`, `incorporation_date`, `service_types` | Anchor for portfolio-level analysis: service coverage, strategic decision history. |
| **Spatial** | `:SiteLocation` | `SITE-XXXX` | `id`, `city`, `address` | Spatial risk concentration: site-level incident exposure and understaffing ratios. |
| **Organization**| `:Department` | `DEPT-XXXX` | `id`, `name`, `description` | Cross-departmental failure attribution and incident-to-action closure rates. |
| **Organization**| `:Team` | `TEAM-XXXX` | `id`, `name`, `department_id`, `primary_site_id` | Accountability mapping: overdue actions and site concentration risk. |
| **Human Capital**| `:Employee` *(Person)* | `EMP-XXXX` | `id`, `full_name`, `email`, `role`, `skills` (JSONB), `is_focal`, `status` | Talent risk analysis: decision-maker failure rate, single-point-of-failure detection. |
| **Human Capital**| `:RoleHistory` | `UUID` | `employee_id`, `job_title`, `start_date`, `end_date`, `reason` | Career velocity: restructure vs promotion correlations with project delivery. |
| **Delivery** | `:Project` | `PROJ-XXXX` | `id`, `name`, `status`, `planned_end_date`, `actual_end_date`, `outcome_summary` | Portfolio health: on-hold rate, milestone variance, decision-caused blockages. |
| **Delivery** | `:Milestone` | `UUID` | `project_id`, `name`, `target_date`, `actual_completion_date`, `status`, `delay_days` | Schedule performance index: bottleneck clustering by vendor, team, or phase. |
| **Retrospective**| `:LessonLearned` | `LL-XXXX` | `id`, `project_id`, `description`, `causal_incident_id`, `causal_decision_id` | Organizational learning: clustering repeated process failures across teams. |
| **Governance** | `:Decision` | `DEC-XXXX` | `id`, `title`, `decision_type`, `outcome`, `rationale`, `root_cause_analysis` | Decision quality: RCA text theme detection (deadline pressure, siloed choices). |
| **Reliability** | `:Incident` *(Ticket)* | `INC-XXXX` | `id`, `title`, `severity` (P1-P4), `incident_type`, `start_datetime`, `confirmed_cause` | Operational risk: MTTR trends, mis-diagnosis rate, recurrence chain discovery. |
| **Accountability**| `:FollowUpAction` *(Task)*| `ACT-XXXX` | `id`, `title`, `due_date`, `completion_date`, `status`, `effectiveness_label` | Action ROI: measuring `prevented_recurrence` vs `ineffective` action chains. |
| **Records** | `:BusinessDocument` *(Doc)*| `DOC-XXXX` | `id`, `title`, `document_type` (PIR, ADR, CAT, etc.), `status`, `successor_doc_id` | Knowledge coverage: detecting undocumented P1/P2 incidents or decisions. |
| **Infrastructure**| `:ServiceType` | `SVC-XXXX` | `id`, `name` | Service risk exposure: co-occurrence matrices of multi-service outages. |

---

### 2.2 Comprehensive Relationship Topology

The ontology defines 26 directional relationship types connecting organizational, operational, and causal subgraphs:

```cypher
// 1. Organizational & Physical Hierarchy
(:Employee)-[:MEMBER_OF_TEAM]->(:Team)
(:Team)-[:BELONGS_TO_DEPARTMENT]->(:Department)
(:Team)-[:LOCATED_AT]->(:SiteLocation)
(:Employee)-[:WORKS_FROM]->(:SiteLocation)
(:Employee)-[:MANAGES {effective_from: date}]->(:Employee)
(:Employee)-[:HAD_ROLE]->(:RoleHistory)

// 2. Project Execution & Governance
(:Employee)-[:LEADS]->(:Project)
(:Employee)-[:CONTRIBUTES_TO]->(:Project)
(:Project)-[:SPONSORED_BY]->(:Department)
(:Project)-[:HAS_MILESTONE]->(:Milestone)
(:Project)-[:HAS_LESSON]->(:LessonLearned)
(:Project)-[:BLOCKED_BY_DECISION]->(:Decision)
(:Project)-[:BLOCKED_BY_INCIDENT]->(:Incident)

// 3. Decision Rationale & Linkage
(:Decision)-[:MADE_BY]->(:Employee)
(:Decision)-[:LINKED_TO_PROJECT]->(:Project)

// 4. Incident Impact & Causal Recurrence
(:Incident)-[:AFFECTS_SERVICE]->(:ServiceType)
(:Incident)-[:AFFECTS_SITE]->(:SiteLocation)
(:Incident)-[:LINKED_TO_PROJECT]->(:Project)
(:Incident)-[:CAUSED_RECURRENCE {via_action_id: 'ACT-XXXX'}]->(:Incident)

// 5. Corrective Action Accountability & Resolution
(:FollowUpAction)-[:RAISED_FROM_INCIDENT]->(:Incident)
(:FollowUpAction)-[:RAISED_FROM_DECISION]->(:Decision)
(:FollowUpAction)-[:ASSIGNED_TO]->(:Employee)
(:FollowUpAction)-[:PREVENTED_RECURRENCE_OF]->(:Incident)

// 6. Documentation & Lineage
(:BusinessDocument)-[:DOCUMENTS]->(:AnyEntity)
(:BusinessDocument)-[:AUTHORED_BY]->(:Employee)
(:BusinessDocument)-[:SUPERSEDED_BY]->(:BusinessDocument)
(:LessonLearned)-[:LESSON_CAUSED_BY_INCIDENT]->(:Incident)
(:LessonLearned)-[:LESSON_CAUSED_BY_DECISION]->(:Decision)
```

---

## 3. Cognitive Memory Overlay Schema (`GraphitiClient`)

The cognitive memory layer operates seamlessly across the rich ontology via `app/services/memory/graphiti_client.py`:

```cypher
(:EpisodeMemory {
    id: 'e8b7d6c5-4321-4f0a-9876-543210abcdef',
    session_id: 'sess_1_20261103_014520',
    query: 'What caused the P1 outage in Mumbai and what action was taken?',
    summary: 'INC-0001 was an MPLS label corruption caused by Juniper firmware defect 21.4R3-S2. Action ACT-0001 was initially ineffective...',
    created_at: '2026-11-03T01:45:20.123456+00:00'
})
```

- **`:RECALLED` Edge**: `(:Employee)-[:RECALLED {at: timestamp}]->(:EpisodeMemory)` tracks user turn chronology.
- **`:TOUCHED` Edge**: `(:EpisodeMemory)-[:TOUCHED]->(target)` anchors the conversation to specific canonical nodes (`:Incident`, `:FollowUpAction`, `:Decision`, `:Project`, `:Employee`).

---

## 4. Inference Rules & Predictive Reasoning (R01–R10)

The engine evaluates 10 formal inference rules at query time or during reconciliation to surface hidden risks:

### R01: Decision Failure Propagation
```cypher
MATCH (d:Decision {outcome: 'negative'})-[:LINKED_TO_PROJECT]->(p:Project)
WHERE p.status IN ['on-hold', 'cancelled'] 
   OR EXISTS { MATCH (p)-[:HAS_MILESTONE]->(m:Milestone {status: 'delayed'}) }
RETURN p.name, d.title, d.root_cause_analysis;
```
*Detects projects structurally blocked by upstream architectural missteps.*

### R02: Mis-Diagnosis Recurrence Chain
```cypher
MATCH (inc1:Incident)<-[:RAISED_FROM_INCIDENT]-(act:FollowUpAction {effectiveness_label: 'ineffective'})
WHERE act.recurrence_incident_id IS NOT NULL
MATCH (inc2:Incident {id: act.recurrence_incident_id})
MERGE (inc1)-[:CAUSED_RECURRENCE {via_action_id: act.id}]->(inc2);
```
*Identifies flawed fixes that spawned secondary outages (e.g. INC-0001 $\rightarrow$ ACT-0001 $\rightarrow$ INC-0002).*

### R03: Overdue Action Escalation on Critical Incidents
```cypher
MATCH (act:FollowUpAction)-[:RAISED_FROM_INCIDENT]->(inc:Incident)
WHERE act.status = 'overdue' AND inc.severity IN ['P1', 'P2']
RETURN act.id, act.title, inc.severity, act.due_date;
```
*Surfaces high-risk open vulnerabilities exposing the company to catastrophic recurrence.*

### R04: Knowledge & Accountability Concentration Risk
```cypher
MATCH (emp:Employee)<-[:ASSIGNED_TO]-(act:FollowUpAction)
WHERE act.status IN ['open', 'in-progress', 'overdue']
WITH emp, count(act) AS open_actions
WHERE open_actions > 5
RETURN emp.full_name, open_actions;
```
*Identifies employees acting as dangerous single points of failure.*

### R05: Decision-Maker Risk Score
```cypher
MATCH (emp:Employee)<-[:MADE_BY]-(d:Decision)
WITH emp, 
     count(d) AS total_decisions,
     sum(CASE WHEN d.outcome = 'negative' THEN 1 ELSE 0 END) AS negative_decisions
WHERE total_decisions >= 3 AND (toFloat(negative_decisions) / total_decisions) > 0.40
RETURN emp.full_name, total_decisions, negative_decisions, (toFloat(negative_decisions) / total_decisions) AS failure_rate;
```
*Detects individuals with $>40\%$ negative outcome rates who continue to ratify high-stakes choices.*

### R06: Project Rescue Pattern
```cypher
MATCH (p:Project)-[:BLOCKED_BY_INCIDENT]->(inc:Incident)
MATCH (act:FollowUpAction {effectiveness_label: 'prevented_recurrence'})-[:RAISED_FROM_INCIDENT]->(inc)
WHERE p.status = 'completed'
RETURN p.name, act.title, inc.title;
```
*Measures corrective actions that successfully unblocked delayed initiatives (e.g. ACT-0005 rescuing PROJ-0002).*

### R07: Repeated Organizational Lesson Failure
```cypher
MATCH (ll1:LessonLearned), (ll2:LessonLearned)
WHERE id(ll1) < id(ll2) AND ll1.project_id <> ll2.project_id
// Evaluated via FastEmbed cosine similarity > 0.75 on descriptions
RETURN ll1.project_id, ll2.project_id, ll1.description;
```
*Flags recurring process gaps learned multiple times without systemic institutional repair.*

### R08: Spatial Site Risk Concentration
```cypher
MATCH (s:SiteLocation)<-[:AFFECTS_SITE]-(inc:Incident)
WITH s, count(inc) AS site_incidents
MATCH (all_inc:Incident)
WITH s, site_incidents, count(all_inc) AS total_incidents, count(DISTINCT s) AS site_count
WHERE site_incidents > (total_incidents / site_count) * 1.5
RETURN s.city, site_incidents;
```
*Flags geographical hubs experiencing disproportionate infrastructure instability (e.g. SITE-0001 Mumbai).*

### R09: RCA Text Pattern Clustering
```python
# Regex keyword extraction in enrichment pipeline:
DEADLINE_PRESSURE = re.compile(r"(board presentation|rushed|compressed timeline)", re.I)
SILOED_DECISION   = re.compile(r"(cross-functional review|single team|no independent)", re.I)
COST_MODEL_FLAW   = re.compile(r"(hidden integration costs|financial model excluded)", re.I)
CHANGE_MANAGEMENT = re.compile(r"(training|NOC team|operational change burden)", re.I)
```
*Categorizes negative decision post-mortems into actionable organizational failure archetypes.*

### R10: Team Skill Gap Correlating with Incidents
```cypher
MATCH (inc:Incident {incident_type: 'security_near_miss'})-[:AFFECTS_SITE]->(site:SiteLocation)<-[:LOCATED_AT]-(team:Team)
MATCH (team)<-[:MEMBER_OF_TEAM]-(emp:Employee)
RETURN team.name, collect(DISTINCT emp.skills), count(inc) AS security_incidents;
```
*Identifies operational teams facing specialized threats without prerequisite skill certifications.*

---

## 5. Analytical Graph Traversal Patterns (P01–P08)

The engine implements 8 named graph queries powering interactive analytics and answering:

| ID | Pattern Name | Operational Query Logic | Concrete Business Value |
| :--- | :--- | :--- | :--- |
| **P01** | **Full Causal Chain Trace** | `(Decision {outcome: 'negative'})-[:LINKED_TO_PROJECT]->(Project)-[:HAS_LESSON]->(LessonLearned)` | Single multi-hop query calculating the entire corporate cost of a flawed technical decision. |
| **P02** | **Incident Recurrence Graph** | `(i1:Incident)<-[:RAISED_FROM]-(act:FollowUpAction {effectiveness_label: 'ineffective'})-[:CAUSED_RECURRENCE]->(i2:Incident)` | Computes cumulative subscriber downtime hours caused by erroneous root-cause diagnoses. |
| **P03** | **Employee Risk Profile** | Composite score: `(Negative Decisions * 2) + Overdue Actions Assigned` | Identifies personnel carrying compound accountability and governance risk. |
| **P04** | **Department Accountability** | Aggregates overdue vs completed `FollowUpAction` items grouped by `Department` | Produces cross-departmental SLA closure and remediation velocity rankings. |
| **P05** | **Document Coverage Audit** | Matches P1/P2 incidents without a linked `PIR` and negative decisions without a `CAT` | Automates regulatory compliance and post-mortem documentation audits. |
| **P06** | **Skill Coverage Heat-Map** | Traverses `(Team)-[:LOCATED_AT]->(Site)<-[:AFFECTS_SITE]-(Incident)` vs `Employee.skills` | Pinpoints geographical skill deficits driving localized network incidents. |
| **P07** | **Portfolio Health Scorecard**| Evaluates `(Project)-[:HAS_MILESTONE]` delay variance alongside blocking causes | Executive portfolio dashboard attributing project slips directly to decisions or outages. |
| **P08** | **Knowledge Retention Risk** | Discovers critical documents and open actions owned by `terminated` or `on_leave` staff | Pre-empts organizational paralysis following key employee departures. |

---

## 6. Business Growth & Opportunity Patterns (BG01–BG07)

The upgraded ontology connects operational topology directly to revenue protection and CapEx optimization:

```
[BG01: Network Reliability] ──► Reduces 30% mis-diagnosis rate → recovers 4–6 hours P1/P2 uptime annually.
[BG02: Decision Governance] ──► Enforces 2-week review gate on CapEx >₹2cr → cuts 24% negative decision rate.
[BG03: Action ROI Metric]   ──► Measures revenue protected by `prevented_recurrence` fixes (e.g. ACT-0005).
[BG04: Talent Concentration]──► Computes authorship Gini coefficient → eliminates single-point-of-failure roles.
[BG05: Security Early-Warn] ──► Alerts on suspected security near-misses unconfirmed after 30 days.
[BG06: 5G Program Recovery] ──► Dependency graph automatically unblocks 5G Phase 2 upon ACT completion.
[BG07: Enterprise SLA Guard]──► Correlates B2B customer SLA breaches with Revenue Assurance pipeline delivery.
```

---

## 7. Backward Compatibility & Non-Breaking Product Guarantees

To ensure that existing backend APIs, vector embeddings, memory services, and frontend UI components continue operating without disruption, the architecture implements **zero-breaking-change aliases**:

```
+─────────────────────────────────+─────────────────────────────────+
|      Legacy Product Concept     |    Upgraded Ontology Entity     |
+─────────────────────────────────+─────────────────────────────────+
| :Person                         | :Employee (includes Person)     |
| :Document                       | :BusinessDocument (adds types)  |
| :Task                           | :FollowUpAction (adds efficacy) |
| :Ticket                         | :Incident (adds severity P1-P4) |
| :MEMBER_OF                      | :MEMBER_OF_TEAM                 |
| :AUTHORED_BY                    | :AUTHORED_BY (retained)         |
| :OWNS                           | :OWNS / :LEADS                  |
| :REFERENCES                     | :DOCUMENTS / :REFERENCES        |
| :DERIVED_FROM                   | :RAISED_FROM / :DERIVED_FROM    |
+─────────────────────────────────+─────────────────────────────────+
```

### Invariants Preserved:
1. **Graph-Native ABAC**: `PermissionResolver` checks for `AUTHORED_BY`, `OWNS`, and `MEMBER_OF` continue matching existing edges; newly introduced relationships (`LEADS`, `ASSIGNED_TO`) strictly expand clearance scope without revoking valid access.
2. **Cognitive Memory Overlay**: `GraphitiClient` creates `:EpisodeMemory` and connects `:TOUCHED` edges to both existing labels and enriched entity types without schema conflicts.
3. **Qdrant Vector Pipeline**: Text chunking and UUIDv5 hashing remain identical; vector payloads are enriched with new tags (`incident_type`, `severity`, `decision_outcome`) for enhanced filtering.
4. **Answer Validation**: `ProvenanceValidator` continues verifying cited entity IDs against PostgreSQL tables while supporting newly introduced entity prefixes (`ACT-`, `INC-`, `DEC-`, `PROJ-`, `DOC-`).
