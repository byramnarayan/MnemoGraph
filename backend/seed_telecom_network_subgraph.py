import asyncio
import os
import sys
from pathlib import Path

backend_dir = Path("g:/memoryProject/backend")
sys.path.insert(0, str(backend_dir))
os.chdir(str(backend_dir))

from app.services.graph.falkordb_client import FalkorDBClient
from app.services.vector.indexer import VectorIndexer
from app.core.database import AsyncSessionLocal
from app.services.ledger.relational_ledger_service import RelationalLedgerService
from app.models.entity import EntityRecord

async def seed_telecom_network():
    print("=== SEEDING CANONICAL TELECOM NETWORK SUBGRAPH (Ramnarayan & Team) ===")
    falkor = FalkorDBClient()
    indexer = VectorIndexer()
    ledger = RelationalLedgerService()

    # 1. Clean previous telecom demo nodes if any
    telecom_ids = [
        "person:ramnarayan-maurya",
        "person:vikram-malhotra",
        "person:rohan-sharma",
        "person:ananya-roy",
        "person:arjun-nair",
        "group:customer-support-sla",
        "loc:connaught-place-hub",
        "loc:bandra-kurla-tower",
        "incident:site-blr-0012",
        "incident:site-hyd-0008",
        "dec:buffer-tuning-bandra",
        "dec:bgp-route-aggregation-cp",
        "dec:transceiver-power-calibration-blr",
        "dec:mtu-jumbo-frames-hyd",
        "task:queue-buffer-monitor",
        "task:bgp-convergence-audit",
        "task:transceiver-telemetry",
        "task:mtu-switch-audit",
    ]
    for tid in telecom_ids:
        try:
            falkor.query(f"MATCH (n {{id: '{tid}'}}) DETACH DELETE n")
        except Exception:
            pass

    # 2. FalkorDB Nodes
    cypher_nodes = """
    MERGE (ram:Person {
        id: 'person:ramnarayan-maurya',
        name: 'Ramnarayan Arvind Maurya',
        full_name: 'Ramnarayan Arvind Maurya',
        role: 'Senior Network Operations Lead',
        department: 'Customer Support & SLA',
        classification: 'Internal',
        skills: 'Optical Transport, DWDM, Microwave Transmission, BGP, Incident Command',
        employment_status: 'active'
    })

    MERGE (vikram:Person {
        id: 'person:vikram-malhotra',
        name: 'Vikram Malhotra',
        full_name: 'Vikram Malhotra',
        role: 'Principal Network SRE',
        department: 'Customer Support & SLA',
        classification: 'Internal',
        employment_status: 'active'
    })

    MERGE (rohan:Person {
        id: 'person:rohan-sharma',
        name: 'Rohan Sharma',
        full_name: 'Rohan Sharma',
        role: 'Customer Support Technical Lead',
        department: 'Customer Support & SLA',
        classification: 'Internal',
        employment_status: 'active'
    })

    MERGE (ananya:Person {
        id: 'person:ananya-roy',
        name: 'Ananya Roy',
        full_name: 'Ananya Roy',
        role: 'SLA Operations & Compliance Specialist',
        department: 'Customer Support & SLA',
        classification: 'Internal',
        employment_status: 'active'
    })

    MERGE (arjun:Person {
        id: 'person:arjun-nair',
        name: 'Arjun Nair',
        full_name: 'Arjun Nair',
        role: 'Lead Infrastructure Architect',
        department: 'Customer Support & SLA',
        classification: 'Internal',
        employment_status: 'active'
    })

    MERGE (dept:Group {
        id: 'group:customer-support-sla',
        name: 'Customer Support & SLA',
        full_name: 'Customer Support & SLA Department',
        department: 'Network Operations'
    })

    MERGE (cp:Location {
        id: 'loc:connaught-place-hub',
        name: 'Connaught Place Hub Road Site',
        title: 'Connaught Place Hub Road Site',
        city: 'New Delhi'
    })

    MERGE (bk:Location {
        id: 'loc:bandra-kurla-tower',
        name: 'Bandra Kurla Telecom Tower',
        title: 'Bandra Kurla Telecom Tower',
        city: 'Mumbai'
    })

    MERGE (inc1:Incident {
        id: 'incident:site-blr-0012',
        name: 'SITE-BLR-0012',
        title: 'SITE-BLR-0012 Transport Flap',
        severity: 'P1',
        status: 'resolved'
    })

    MERGE (inc2:Incident {
        id: 'incident:site-hyd-0008',
        name: 'SITE-HYD-0008',
        title: 'SITE-HYD-0008 Gateway Saturation',
        severity: 'P2',
        status: 'resolved'
    })

    MERGE (dec1:Decision {
        id: 'dec:buffer-tuning-bandra',
        title: 'Dynamic Ingress Queue Buffer Expansion on Bandra Kurla Tower',
        rationale: 'Mitigate high-frequency burst packet drops during evening peak traffic hours.',
        decision_date: '2026-10-24T14:30:00Z',
        created_at: '2026-10-24T14:30:00Z',
        status: 'approved',
        classification: 'Internal'
    })

    MERGE (dec2:Decision {
        id: 'dec:bgp-route-aggregation-cp',
        title: 'Autonomous BGP Prefix Aggregation at Connaught Place Hub',
        rationale: 'Reduce routing table memory footprint and FIB convergence delays across north aggregation nodes.',
        decision_date: '2026-10-28T09:15:00Z',
        created_at: '2026-10-28T09:15:00Z',
        status: 'approved',
        classification: 'Internal'
    })

    MERGE (dec3:Decision {
        id: 'dec:transceiver-power-calibration-blr',
        title: 'Optical Transceiver Power Margin Recalibration',
        rationale: 'Lower optical amplifier gain margin to reduce laser thermal degradation under continuous load.',
        decision_date: '2026-11-01T11:00:00Z',
        created_at: '2026-11-01T11:00:00Z',
        status: 'approved',
        classification: 'Internal'
    })

    MERGE (dec4:Decision {
        id: 'dec:mtu-jumbo-frames-hyd',
        title: 'Jumbo Frame 9000 MTU Enablement across Gateway Trunk',
        rationale: 'Boost inter-datacenter replication throughput across high-capacity gateway interfaces.',
        decision_date: '2026-11-03T16:00:00Z',
        created_at: '2026-11-03T16:00:00Z',
        status: 'approved',
        classification: 'Internal'
    })

    MERGE (t1:Task {
        id: 'task:queue-buffer-monitor',
        title: 'Deploy optical queue monitoring daemon on Bandra Kurla',
        status: 'in_progress',
        due_date: '2026-11-12',
        effectiveness_label: 'pending',
        classification: 'Internal'
    })

    MERGE (t2:Task {
        id: 'task:bgp-convergence-audit',
        title: 'Audit route reflector convergence under failover simulation',
        status: 'open',
        due_date: '2026-11-15',
        effectiveness_label: 'pending',
        classification: 'Internal'
    })

    MERGE (t3:Task {
        id: 'task:transceiver-telemetry',
        title: 'Run 48-hour continuous power telemetry verification',
        status: 'open',
        due_date: '2026-11-18',
        effectiveness_label: 'pending',
        classification: 'Internal'
    })

    MERGE (t4:Task {
        id: 'task:mtu-switch-audit',
        title: 'Audit core switch MTU consistency across all spine ports',
        status: 'completed',
        due_date: '2026-11-04',
        effectiveness_label: 'effective',
        classification: 'Internal'
    })
    """
    falkor.query(cypher_nodes)
    print("[OK] Nodes merged into FalkorDB")

    # 3. FalkorDB Edges (Exactly matching uploaded reference topology)
    cypher_edges = """
    MATCH (ram:Person {id: 'person:ramnarayan-maurya'})
    MATCH (vikram:Person {id: 'person:vikram-malhotra'})
    MATCH (rohan:Person {id: 'person:rohan-sharma'})
    MATCH (ananya:Person {id: 'person:ananya-roy'})
    MATCH (arjun:Person {id: 'person:arjun-nair'})
    MATCH (dept:Group {id: 'group:customer-support-sla'})
    MATCH (cp:Location {id: 'loc:connaught-place-hub'})
    MATCH (bk:Location {id: 'loc:bandra-kurla-tower'})
    MATCH (inc1:Incident {id: 'incident:site-blr-0012'})
    MATCH (inc2:Incident {id: 'incident:site-hyd-0008'})
    MATCH (dec1:Decision {id: 'dec:buffer-tuning-bandra'})
    MATCH (dec2:Decision {id: 'dec:bgp-route-aggregation-cp'})
    MATCH (dec3:Decision {id: 'dec:transceiver-power-calibration-blr'})
    MATCH (dec4:Decision {id: 'dec:mtu-jumbo-frames-hyd'})
    MATCH (t1:Task {id: 'task:queue-buffer-monitor'})
    MATCH (t2:Task {id: 'task:bgp-convergence-audit'})
    MATCH (t3:Task {id: 'task:transceiver-telemetry'})
    MATCH (t4:Task {id: 'task:mtu-switch-audit'})

    MERGE (rohan)-[:CONNECTED_TO]->(dept)
    MERGE (rohan)-[:CONNECTED_TO]->(ananya)
    MERGE (ananya)-[:CONNECTED_TO]->(dept)
    MERGE (vikram)-[:CONNECTED_TO]->(dept)
    MERGE (dept)-[:CONNECTED_TO]->(arjun)
    MERGE (ram)-[:CONNECTED_TO]->(dept)
    MERGE (ram)-[:CONNECTED_TO]->(arjun)
    MERGE (ram)-[:CONNECTED_TO]->(cp)
    MERGE (arjun)-[:CONNECTED_TO]->(bk)
    MERGE (arjun)-[:CONNECTED_TO]->(inc1)
    MERGE (bk)-[:CONNECTED_TO]->(inc2)

    MERGE (arjun)-[:DECIDED]->(dec1)
    MERGE (dec1)-[:AFFECTS]->(bk)
    MERGE (t1)-[:RAISED_FROM]->(dec1)
    MERGE (t1)-[:ASSIGNED_TO]->(arjun)

    MERGE (vikram)-[:DECIDED]->(dec2)
    MERGE (dec2)-[:AFFECTS]->(cp)
    MERGE (t2)-[:RAISED_FROM]->(dec2)
    MERGE (t2)-[:ASSIGNED_TO]->(vikram)

    MERGE (ram)-[:DECIDED]->(dec3)
    MERGE (dec3)-[:AFFECTS]->(bk)
    MERGE (t3)-[:RAISED_FROM]->(dec3)
    MERGE (t3)-[:ASSIGNED_TO]->(ram)

    MERGE (rohan)-[:DECIDED]->(dec4)
    MERGE (dec4)-[:AFFECTS]->(cp)
    MERGE (t4)-[:RAISED_FROM]->(dec4)
    MERGE (t4)-[:ASSIGNED_TO]->(rohan)
    """
    falkor.query(cypher_edges)
    print("[OK] Edges merged into FalkorDB")

    # 4. Qdrant Vector Indexing for Semantic Search & RAG
    docs_to_index = [
        {
            "id": "doc:ramnarayan-dossier",
            "title": "Ramnarayan Arvind Maurya - Operational Profile & Infrastructure Responsibilities",
            "text": (
                "Ramnarayan Arvind Maurya is the Senior Network Operations Lead for Customer Support & SLA. "
                "His primary work involves managing high-throughput microwave and optical backbone connectivity at the Connaught Place Hub Road Site. "
                "Ramnarayan collaborates directly with Lead Architect Arjun Nair on inter-city core fiber resilience and resolved major transport outage SITE-BLR-0012. "
                "He coordinates SLA compliance and escalation protocols with Ananya Roy and technical support lead Rohan Sharma."
            ),
            "entity_id": "person:ramnarayan-maurya",
            "entity_class": "Person",
        },
        {
            "id": "doc:site-blr-0012-rca",
            "title": "Incident Root Cause Analysis: SITE-BLR-0012 Optical Transport Failure",
            "text": (
                "Post-Incident Review for SITE-BLR-0012: The optical transport route to the Bengaluru south aggregation hub flapped due to a fiber cut. "
                "Ramnarayan Arvind Maurya and Arjun Nair redirected traffic via the Connaught Place and Bandra Kurla backup rings within 14 minutes, restoring SLA compliance."
            ),
            "entity_id": "incident:site-blr-0012",
            "entity_class": "Incident",
        },
        {
            "id": "doc:customer-support-sla-overview",
            "title": "Customer Support & SLA Department Organizational Structure",
            "text": (
                "The Customer Support & SLA department ensures 99.999% network uptime across metropolitan telecom hubs. "
                "Key personnel include Vikram Malhotra (Network SRE), Ramnarayan Arvind Maurya (Operations Lead), Arjun Nair (Infrastructure Architect), "
                "Rohan Sharma (Technical Support), and Ananya Roy (Compliance Specialist)."
            ),
            "entity_id": "group:customer-support-sla",
            "entity_class": "Group",
        },
        {
            "id": "doc:incident-buffer-overflow-lessons",
            "title": "Post-Mortem & Lessons Learned: Aggregation Queue Buffer Tuning & Flapping",
            "text": (
                "Historical Post-Mortem: Expanding ingress queue buffers on core aggregation nodes without real-time jitter monitoring "
                "caused bufferbloat and subsequent packet desynchronization on downstream BNG routers. "
                "Key Lesson Learned: Dynamic buffer tuning must be accompanied by synchronous telemetry daemons and strict 24-hour verification. "
                "Unassigned follow-up tasks historically lead to repeat outages within 14 to 30 days."
            ),
            "entity_id": "dec:buffer-tuning-bandra",
            "entity_class": "Lesson",
        },
        {
            "id": "doc:incident-bgp-flapping-lessons",
            "title": "Post-Mortem & Lessons Learned: BGP Aggregation and Route Convergence",
            "text": (
                "Historical Post-Mortem: Autonomous route aggregation without secondary peer verification caused asynchronous routing loops "
                "between Delhi and Mumbai transit paths. "
                "Key Lesson Learned: Route reflector policies must undergo staging verification with automated rollback thresholds before full production deployment."
            ),
            "entity_id": "dec:bgp-route-aggregation-cp",
            "entity_class": "Lesson",
        },
    ]

    for doc in docs_to_index:
        await indexer.index_document(
            document_id=doc["id"],
            text=doc["text"],
            doc_title=doc["title"],
            metadata={
                "entity_id": doc["entity_id"],
                "entity_class": doc["entity_class"],
                "classification": "Internal",
                "completeness_score": 1.0,
                "data_quality_grade": "A",
            },
        )
    print("[OK] Qdrant semantic vectors indexed successfully")

if __name__ == "__main__":
    asyncio.run(seed_telecom_network())
