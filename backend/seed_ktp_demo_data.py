import asyncio
import os
import sys
from pathlib import Path

backend_dir = Path("g:/memoryProject/backend")
sys.path.insert(0, str(backend_dir))
os.chdir(str(backend_dir))

from sqlalchemy import text
from app.core.database import engine
from app.services.graph.falkordb_client import FalkorDBClient

def seed_demo_data():
    falkor = FalkorDBClient()
    print("=== SEEDING 3 RICH DEMO PERSON SUBGRAPHS FOR KTP HUB ===")

    # 1. Clean up existing demo nodes if any to allow clean re-runs
    demo_ids = [
        "person:sarah-connor",
        "person:marcus-chen",
        "person:elena-rostova",
        "person:ram-admin",
        "group:platform-core",
        "group:ai-cognitive",
        "proj:titan-dr",
        "proj:nova-mesh",
        "proj:mnemocore",
    ]
    for did in demo_ids:
        try:
            falkor.query(f"MATCH (n {{id: '{did}'}}) DETACH DELETE n")
        except Exception:
            pass

    # 2. Locations & Groups
    falkor.query("""
    MERGE (loc1:Location {id: 'loc:us-east', name: 'US-East (Virginia)'})
    MERGE (loc2:Location {id: 'loc:sf-hq', name: 'San Francisco, CA'})
    MERGE (loc3:Location {id: 'loc:london', name: 'London, UK'})
    
    MERGE (g1:Group {id: 'group:platform-core', name: 'Platform Core Engineering'})
    MERGE (g2:Group {id: 'group:ai-cognitive', name: 'AI & Cognitive Intelligence'})
    """)

    # 3. Ram (Executive Admin / Logged-in user)
    falkor.query("""
    MERGE (ram:Person {
        id: 'person:ram-admin',
        full_name: 'Ram',
        name: 'Ram',
        email: 'apex@gmail.com',
        role: 'Executive Admin',
        employment_status: 'active',
        clearance_level: 'Restricted'
    })
    """)

    # 4. Sarah Connor (Staff Infrastructure Architect - Departing)
    falkor.query("""
    MERGE (s:Person {
        id: 'person:sarah-connor',
        full_name: 'Sarah Connor',
        name: 'Sarah Connor',
        email: 'sarah.connor@mnemograph.io',
        role: 'Staff Infrastructure Architect',
        employment_status: 'departing',
        clearance_level: 'Confidential',
        concentration_risk: true,
        owned_critical_items: 0.88,
        skills: 'Kubernetes, Terraform, Distributed Systems, Incident Command, Golang, Multi-Region DR',
        ktp_generated: false
    })
    WITH s
    MATCH (loc:Location {id: 'loc:us-east'}), (g:Group {id: 'group:platform-core'}), (ram:Person {id: 'person:ram-admin'})
    MERGE (s)-[:LOCATED_AT]->(loc)
    MERGE (s)-[:MEMBER_OF]->(g)
    MERGE (ram)-[:MANAGES]->(s)
    """)

    # Sarah's Role History
    falkor.query("""
    MATCH (s:Person {id: 'person:sarah-connor'})
    MERGE (r1:Role {id: 'role:staff-infra', title: 'Staff Infrastructure Architect', department: 'Platform Core Engineering'})
    MERGE (r2:Role {id: 'role:sr-infra', title: 'Senior Cloud SRE', department: 'Platform Infrastructure'})
    MERGE (s)-[:HELD_ROLE {start_date: '2023-01-15', end_date: 'present'}]->(r1)
    MERGE (s)-[:HELD_ROLE {start_date: '2020-03-01', end_date: '2023-01-14'}]->(r2)
    """)

    # Sarah's Projects & Subgraphs
    falkor.query("""
    MATCH (s:Person {id: 'person:sarah-connor'})
    MERGE (p1:Project {
        id: 'proj:titan-dr',
        name: 'Project Titan — Global Multi-Region Failover',
        status: 'active',
        classification: 'Confidential'
    })
    MERGE (s)-[:LEADS]->(p1)

    MERGE (m1:Milestone {
        id: 'ms:titan-canary',
        name: 'Canary DR Traffic Shift Validation',
        status: 'in_progress',
        target_date: '2026-12-01'
    })
    MERGE (m2:Milestone {
        id: 'ms:titan-vault',
        name: 'Cross-Region Vault Cluster Mesh',
        status: 'pending',
        target_date: '2027-01-15'
    })
    MERGE (p1)-[:IMPLEMENTS]->(m1)
    MERGE (p1)-[:IMPLEMENTS]->(m2)

    MERGE (dec1:Decision {
        id: 'dec:envoy-ratelimit',
        title: 'DEC-104: Adoption of Envoy Global Rate Limiter across Edge Nodes',
        outcome: 'positive',
        decision_type: 'Architecture',
        decision_date: '2026-03-12',
        classification: 'Internal'
    })
    MERGE (dec1)-[:LINKED_TO_PROJECT]->(p1)
    MERGE (dec1)-[:AUTHORED_BY]->(s)

    MERGE (dec2:Decision {
        id: 'dec:kafka-rebalance',
        title: 'DEC-208: Kafka Partition Rebalance during High Traffic Peak',
        outcome: 'negative',
        decision_type: 'Operational',
        decision_date: '2026-07-22',
        classification: 'Confidential',
        root_cause_analysis: 'Insufficient broker replica count caused I/O bottleneck and consumer lag spike during peak load.'
    })
    MERGE (dec2)-[:LINKED_TO_PROJECT]->(p1)
    MERGE (dec2)-[:AUTHORED_BY]->(s)

    MERGE (inc1:Incident {
        id: 'inc:9021-split-brain',
        title: 'INC-9021: Database Read Replica Split-Brain during WAN Interruption',
        severity: 'P1-Critical',
        type: 'Infrastructure',
        cause_status: 'confirmed_root_cause',
        classification: 'Confidential'
    })
    MERGE (inc1)-[:LINKED_TO_PROJECT]->(p1)

    MERGE (pir1:Document {
        id: 'doc:pir-9021',
        title: 'PIR-9021: Post-Incident Review & Latency Analysis',
        document_type: 'post_incident_review',
        status: 'approved',
        classification: 'Confidential'
    })
    MERGE (inc1)-[:DOCUMENTS]->(pir1)

    MERGE (t1:Task {
        id: 'task:titan-dns',
        title: 'Automate DNS Route53 failover health check telemetry',
        status: 'open',
        due_date: '2026-11-20',
        effectiveness_label: 'Effective',
        classification: 'Internal'
    })
    MERGE (t1)-[:ASSIGNED_TO]->(s)
    MERGE (t1)-[:RAISED_FROM]->(inc1)

    MERGE (t2:Task {
        id: 'task:titan-cert-rot',
        title: 'Rotate Root CA certificates for cluster federation before expiration',
        status: 'overdue',
        due_date: '2026-10-15',
        effectiveness_label: 'Ineffective',
        recurrence_risk_inherited: true,
        classification: 'Confidential'
    })
    MERGE (t2)-[:ASSIGNED_TO]->(s)
    MERGE (t2)-[:RAISED_FROM]->(inc1)

    MERGE (doc1:Document {
        id: 'doc:regional-outage-runbook',
        title: 'Runbook: Regional Outage Auto-Remediation Playbook',
        document_type: 'runbook',
        status: 'approved',
        creation_date: '2026-02-10',
        classification: 'Internal'
    })
    MERGE (doc1)-[:AUTHORED_BY]->(s)

    MERGE (doc2:Document {
        id: 'doc:zero-trust-rfc',
        title: 'Architecture RFC: Zero Trust Inter-Cluster Federation Protocol',
        document_type: 'rfc',
        status: 'approved',
        creation_date: '2026-05-18',
        classification: 'Confidential'
    })
    MERGE (doc2)-[:AUTHORED_BY]->(s)

    MERGE (les1:Lesson {
        id: 'les:graceful-tls',
        title: 'Graceful TLS connection draining prevents 502 gateway storms during cert updates',
        summary: 'Explicit connection keep-alive termination with 30s grace period is mandatory before TLS key replacement.'
    })
    MERGE (p1)-[:RESOLVED_BY]->(les1)
    """)

    # 5. Marcus Chen (Principal ML Engineer - On Leave)
    falkor.query("""
    MERGE (m:Person {
        id: 'person:marcus-chen',
        full_name: 'Marcus Chen',
        name: 'Marcus Chen',
        email: 'marcus.chen@mnemograph.io',
        role: 'Principal ML Engineer',
        employment_status: 'on_leave',
        clearance_level: 'Restricted',
        concentration_risk: true,
        owned_critical_items: 0.94,
        skills: 'PyTorch, Vector Search, Qdrant, FalkorDB, LLM Fine-Tuning, Knowledge Graphs, Python',
        ktp_generated: false
    })
    WITH m
    MATCH (loc:Location {id: 'loc:sf-hq'}), (g:Group {id: 'group:ai-cognitive'}), (ram:Person {id: 'person:ram-admin'})
    MERGE (m)-[:LOCATED_AT]->(loc)
    MERGE (m)-[:MEMBER_OF]->(g)
    MERGE (ram)-[:MANAGES]->(m)
    """)

    # Marcus's Projects, Decisions, Incidents, Tasks
    falkor.query("""
    MATCH (m:Person {id: 'person:marcus-chen'})
    MERGE (p2:Project {
        id: 'proj:mnemocore',
        name: 'Project MnemoCore — Enterprise Neural Graph Engine',
        status: 'active',
        classification: 'Restricted'
    })
    MERGE (m)-[:LEADS]->(p2)

    MERGE (ms3:Milestone {
        id: 'ms:mnemo-perf',
        name: 'Sub-50ms Hybrid Vector/Graph Traversal Benchmark',
        status: 'in_progress',
        target_date: '2026-11-30'
    })
    MERGE (p2)-[:IMPLEMENTS]->(ms3)

    MERGE (dec3:Decision {
        id: 'dec:hnsw-quant',
        title: 'DEC-312: Implementation of HNSW Graph Scalar Quantization',
        outcome: 'positive',
        decision_type: 'Engineering',
        decision_date: '2026-04-05',
        classification: 'Internal'
    })
    MERGE (dec3)-[:LINKED_TO_PROJECT]->(p2)
    MERGE (dec3)-[:AUTHORED_BY]->(m)

    MERGE (inc2:Incident {
        id: 'inc:8104-dim-mismatch',
        title: 'INC-8104: Vector Embedding Dimensionality Mismatch in Cross-Encoder Pipeline',
        severity: 'P2-High',
        type: 'Software',
        cause_status: 'mitigated',
        classification: 'Internal'
    })
    MERGE (inc2)-[:LINKED_TO_PROJECT]->(p2)

    MERGE (t3:Task {
        id: 'task:hnsw-bench',
        title: 'Benchmark Qdrant HNSW cosine indexing with 10M entities',
        status: 'in_progress',
        due_date: '2026-11-15',
        effectiveness_label: 'Effective',
        classification: 'Internal'
    })
    MERGE (t3)-[:ASSIGNED_TO]->(m)
    MERGE (t3)-[:RAISED_FROM]->(inc2)

    MERGE (t4:Task {
        id: 'task:falkor-pool',
        title: 'Resolve thread pool concurrency block in FalkorDB async wrapper',
        status: 'open',
        due_date: '2026-11-18',
        effectiveness_label: 'Pending',
        classification: 'Internal'
    })
    MERGE (t4)-[:ASSIGNED_TO]->(m)

    MERGE (doc3:Document {
        id: 'doc:dual-memory-paper',
        title: 'Whitepaper: Dual-Memory Cognitive Graph Engine Architecture',
        document_type: 'whitepaper',
        status: 'approved',
        creation_date: '2026-01-15',
        classification: 'Restricted'
    })
    MERGE (doc3)-[:AUTHORED_BY]->(m)

    MERGE (doc4:Document {
        id: 'doc:vector-normalization',
        title: 'Engineering Guide: Vector Space Normalization & Invariant Constraints',
        document_type: 'guide',
        status: 'approved',
        creation_date: '2026-06-20',
        classification: 'Internal'
    })
    MERGE (doc4)-[:AUTHORED_BY]->(m)

    MERGE (les2:Lesson {
        id: 'les:prewarm-cache',
        title: 'Pre-warming semantic vector cache eliminates cold-start p99 latency spikes',
        summary: 'Warm up Qdrant segment cache using representative query centroids upon worker container spawn.'
    })
    MERGE (p2)-[:RESOLVED_BY]->(les2)
    """)

    # 6. Elena Rostova (Senior DevOps & Security Lead - Active, Successor Candidate!)
    falkor.query("""
    MERGE (e:Person {
        id: 'person:elena-rostova',
        full_name: 'Elena Rostova',
        name: 'Elena Rostova',
        email: 'elena.rostova@mnemograph.io',
        role: 'Senior DevOps & Security Lead',
        employment_status: 'active',
        clearance_level: 'Confidential',
        concentration_risk: false,
        owned_critical_items: 0.20,
        skills: 'Kubernetes, Terraform, Distributed Systems, Golang, CI/CD, Vault',
        ktp_generated: false
    })
    WITH e
    MATCH (loc:Location {id: 'loc:london'}), (g:Group {id: 'group:platform-core'}), (ram:Person {id: 'person:ram-admin'})
    MERGE (e)-[:LOCATED_AT]->(loc)
    MERGE (e)-[:MEMBER_OF]->(g)
    MERGE (ram)-[:MANAGES]->(e)
    """)

    # Elena's Projects and Tasks
    falkor.query("""
    MATCH (e:Person {id: 'person:elena-rostova'}), (s:Person {id: 'person:sarah-connor'})
    MERGE (p3:Project {
        id: 'proj:nova-mesh',
        name: 'Project Nova — Zero Trust Service Mesh',
        status: 'active',
        classification: 'Confidential'
    })
    MERGE (e)-[:LEADS]->(p3)
    MERGE (s)-[:CONTRIBUTES_TO]->(p3)

    MERGE (t5:Task {
        id: 'task:vault-cluster',
        title: 'Provision HashiCorp Vault enterprise cluster in EU region',
        status: 'in_progress',
        due_date: '2026-11-25',
        effectiveness_label: 'Effective',
        classification: 'Internal'
    })
    MERGE (t5)-[:ASSIGNED_TO]->(e)
    """)

    print("\n[SUCCESS] Successfully seeded 3 rich personnel with interconnected subgraphs:")
    print("1. Sarah Connor (person:sarah-connor) -- Departing, Staff Infrastructure Architect (Key Person Risk: 0.88)")
    print("2. Marcus Chen (person:marcus-chen) -- On Leave, Principal ML Engineer (Key Person Risk: 0.94)")
    print("3. Elena Rostova (person:elena-rostova) -- Active, Senior DevOps Lead (Top Successor match for Sarah!)")

async def link_user_in_postgres():
    async with engine.begin() as conn:
        # Ensure apex@gmail.com is linked to person:ram-admin
        await conn.execute(text("""
            UPDATE users 
            SET person_entity_id = 'person:ram-admin',
                role = 'Executive Admin',
                clearance_level = 'Restricted'
            WHERE email = 'apex@gmail.com';
        """))
        print("\n[SUCCESS] Updated user 'apex@gmail.com' in PostgreSQL: role='Executive Admin', clearance='Restricted', linked to 'person:ram-admin'.")

if __name__ == "__main__":
    seed_demo_data()
    asyncio.run(link_user_in_postgres())
