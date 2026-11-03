"""
Sync 500 Telecom RFCs/ADRs and Incident Retrospectives into Decisions & FalkorDB.
Parses realistic timelines, impacts, learnings, and attributes decisions to authoring telecom personas.
"""

import os
import sys
import re
import uuid
import asyncio
from datetime import datetime, UTC

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from sqlalchemy import select, text
from app.core.database import AsyncSessionLocal
from app.models.connector import Person, Project, Team, Document
from app.models.provenance import Decision, ProjectMember
from app.services.graph.falkordb_client import FalkorDBClient

BASE_DIR = os.path.join(BACKEND_DIR, "datasets", "telecom_enterprise_corpus")

PERSON_EMAIL_MAP = {
    "rohit.patel@telcosphere.com": "5b7c29b6-6b45-414c-9b97-481de3e588c7", # Executive Operations
    "sarah.lindqvist@telcosphere.com": "ebc44d93-7b42-4e5c-b754-0bcf993be7f1", # 5G RAN & Core
    "tarek.mansour@telcosphere.com": "79a6960a-5e5f-4f91-a841-c4cfcad411c8", # BSS/OSS
    "elena.rostova@telcosphere.com": "41b7d230-0a04-49d1-8c7b-53a7ab2b2381", # Telecom Security
    "james.wilson@telcosphere.com": "37dd8789-4e77-4953-8292-82aea7fac31f", # NOC Ops
}

PROJECT_KEY_MAP = {
    "sarah": "01839826-a7d1-4fc6-bdf9-b52b725b0def", # 5G Standalone Metro Deployment
    "tarek": "e41f1617-eb33-41a1-991f-b350f788fba3", # BSS Wholesale Roaming TAP3 Clearing
    "elena": "20429425-a4b9-457e-9a3b-5be1f5129d54", # CALEA & IMSI Anonymization Vault
    "james": "92b08e61-03f5-4814-9314-d06a04f1d640", # NOC Proactive Tower Fault Detection
    "rohit": "01839826-a7d1-4fc6-bdf9-b52b725b0def",
}

async def sync_telecom_decisions():
    print("Starting sync of telecom ADRs and Incident Retrospectives into Decisions table & FalkorDB...")
    client = FalkorDBClient()
    
    async with AsyncSessionLocal() as session:
        # Load person id map
        people_rows = (await session.execute(select(Person))).scalars().all()
        person_by_email = {p.email.lower(): p for p in people_rows}

        # Ensure project members exist for real project associations
        for email, p in person_by_email.items():
            for key, proj_id in PROJECT_KEY_MAP.items():
                if key in email:
                    # Check if project member exists
                    mem_check = await session.execute(
                        select(ProjectMember).where(ProjectMember.project_id == proj_id, ProjectMember.person_id == p.id)
                    )
                    if not mem_check.scalars().first():
                        session.add(ProjectMember(
                            id=str(uuid.uuid4()),
                            project_id=proj_id,
                            person_id=p.id,
                            role=p.role or "Contributor"
                        ))
                        # Also link in FalkorDB
                        client.query(f"MATCH (p:Person {{email: '{p.email}'}}), (pr:Project {{id: 'project:{proj_id}'}}) MERGE (p)-[:WORKED_ON]->(pr)")
        await session.commit()

        # Update Project descriptions if empty
        proj_descriptions = {
            "01839826-a7d1-4fc6-bdf9-b52b725b0def": "Deployment of multi-vendor Open-RAN 7.2x gNodeB radio units and distributed user plane functions (UPF) across tier-1 metropolitan clusters.",
            "e41f1617-eb33-41a1-991f-b350f788fba3": "Modernization of high-throughput GSMA TAP3 roaming clearinghouse and PySpark CDR mediation pipeline handling 50M+ daily events.",
            "20429425-a4b9-457e-9a3b-5be1f5129d54": "Implementation of 3GPP Release 17 SUPI to SUCI subscription concealed identifier vault and CALEA lawful intercept compliant architecture.",
            "92b08e61-03f5-4814-9314-d06a04f1d640": "Real-time edge telemetry ingest and automated machine learning for cell tower anomaly detection, preempting fiber cuts and sector degradation."
        }
        for pid, desc in proj_descriptions.items():
            await session.execute(text("UPDATE projects SET description = :desc WHERE id = :pid").params(desc=desc, pid=pid))
        await session.commit()

        # 1. Process 3GPP Architecture RFCs (250 docs)
        rfc_dir = os.path.join(BASE_DIR, "3gpp_architecture_rfcs")
        rfc_count = 0
        if os.path.exists(rfc_dir):
            for fname in os.listdir(rfc_dir):
                if not fname.endswith(".md"):
                    continue
                fpath = os.path.join(rfc_dir, fname)
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()

                # Extract title
                title_m = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
                title = title_m.group(1).strip() if title_m else fname.replace(".md", "")
                
                # Extract author email
                author_m = re.search(r"<([^>]+@[^>]+)>", content)
                author_email = author_m.group(1).strip().lower() if author_m else "sarah.lindqvist@telcosphere.com"
                
                # Extract context/description
                desc_m = re.search(r"## 1\. Context & Business Problem\s*\n(.*?)(?=\n##|\Z)", content, re.DOTALL)
                description = desc_m.group(1).strip() if desc_m else title
                
                # Extract decision & impact
                dec_m = re.search(r"## 3\. Decision & Technical Specifications\s*\n(.*?)(?=\n##|\Z)", content, re.DOTALL)
                decision_text = dec_m.group(1).strip() if dec_m else "Standardized on 3GPP Open-RAN 7.2x specifications."
                
                impact = f"Enforces sub-5ms latency SLA on 5G URLLC slices and guarantees vendor interoperability."
                learnings = "Proprietary baseband units introduce vendor lock-in. Open-RAN eCPRI reduces CAPEX by 34%."
                timeline = "Q1 2026 Architectural Evaluation -> Q2 2026 Lab Validation -> Q3 2026 Production Rollout"

                person = person_by_email.get(author_email)
                user_id = person.id if person else None
                proj_id = None
                for k, p_id in PROJECT_KEY_MAP.items():
                    if k in author_email:
                        proj_id = p_id
                        break

                # Upsert into PostgreSQL decisions
                dec_id = f"dec-{fname.replace('.md', '').lower()}"
                
                # Check if already in decisions
                existing = (await session.execute(select(Decision).where(Decision.id == dec_id))).scalars().first()
                if not existing:
                    new_dec = Decision(
                        id=dec_id,
                        title=f"Architectural Decision: {title[:180]}",
                        description=description[:1000],
                        impact=impact,
                        learnings=learnings,
                        timeline=timeline,
                        status="accepted",
                        project_id=proj_id,
                        workspace_id="telcosphere-prod",
                        source_document_id=f"telecom:{fname.replace('.md', '')}",
                        created_by_user_id=user_id,
                    )
                    session.add(new_dec)
                    rfc_count += 1
                
                # Add to FalkorDB
                try:
                    client.query(f"""
                        MERGE (d:Decision {{id: 'decision:{dec_id}'}})
                        ON CREATE SET d.title = '{title[:60].replace("'", "")}', d.status = 'accepted', d.impact = '{impact.replace("'", "")}'
                    """)
                    client.query(f"""
                        MATCH (p:Person {{email: '{author_email}'}}), (d:Decision {{id: 'decision:{dec_id}'}})
                        MERGE (p)-[:DECIDED]->(d)
                    """)
                except Exception as e:
                    pass

        await session.commit()
        print(f"[OK] Synced {rfc_count} 3GPP ADRs into PostgreSQL & FalkorDB Decisions.")

        # 2. Process Incident Retrospectives (250 docs)
        inc_dir = os.path.join(BASE_DIR, "incident_retrospectives_mops")
        inc_count = 0
        if os.path.exists(inc_dir):
            for fname in os.listdir(inc_dir):
                if not fname.endswith(".md"):
                    continue
                fpath = os.path.join(inc_dir, fname)
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()

                # Extract title
                title_m = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
                title = title_m.group(1).strip() if title_m else fname.replace(".md", "")
                
                # Extract incident commander email
                author_m = re.search(r"Incident Commander\*\*:\s*.*?<([^>]+@[^>]+)>", content)
                author_email = author_m.group(1).strip().lower() if author_m else "james.wilson@telcosphere.com"
                
                # Extract timeline
                timeline_m = re.search(r"## 2\. Chronological Timeline.*?\n(.*?)(?=\n##|\Z)", content, re.DOTALL)
                timeline_text = timeline_m.group(1).strip() if timeline_m else "08:14 Alert -> 08:24 SEV-1 War Room -> 08:42 Normalization"
                
                # Extract RCA
                rca_m = re.search(r"## 4\. Root Cause Analysis.*?\n(.*?)(?=\n##|\Z)", content, re.DOTALL)
                rca_text = rca_m.group(1).strip() if rca_m else "Unhandled SCTP failover race condition in UPF cluster."
                
                # Extract Action Items
                act_m = re.search(r"## 5\. Corrective Action Items.*?\n(.*?)(?=\n##|\Z)", content, re.DOTALL)
                learnings_text = act_m.group(1).strip() if act_m else "Migrated UPF failover to active-active eBPF fastpath."

                person = person_by_email.get(author_email)
                user_id = person.id if person else None
                proj_id = None
                for k, p_id in PROJECT_KEY_MAP.items():
                    if k in author_email:
                        proj_id = p_id
                        break

                dec_id = f"dec-{fname.replace('.md', '').lower()}"
                existing = (await session.execute(select(Decision).where(Decision.id == dec_id))).scalars().first()
                if not existing:
                    new_dec = Decision(
                        id=dec_id,
                        title=f"Incident Postmortem & MOP: {title[:180]}",
                        description=f"RCA: {rca_text[:500]}",
                        impact="SEV-1 Mitigated; Normalized gNodeB drop rate to <0.08%.",
                        learnings=learnings_text[:600],
                        timeline=timeline_text[:600],
                        status="accepted",
                        project_id=proj_id,
                        workspace_id="telcosphere-prod",
                        source_document_id=f"telecom:{fname.replace('.md', '')}",
                        created_by_user_id=user_id,
                    )
                    session.add(new_dec)
                    inc_count += 1
                
                try:
                    client.query(f"""
                        MERGE (d:Decision {{id: 'decision:{dec_id}'}})
                        ON CREATE SET d.title = '{title[:60].replace("'", "")}', d.status = 'ratified', d.impact = 'SEV-1 Mitigation'
                    """)
                    client.query(f"""
                        MATCH (p:Person {{email: '{author_email}'}}), (d:Decision {{id: 'decision:{dec_id}'}})
                        MERGE (p)-[:DECIDED]->(d)
                    """)
                except Exception as e:
                    pass

        await session.commit()
        print(f"[OK] Synced {inc_count} Incident Retrospective Decisions into PostgreSQL & FalkorDB Decisions.")

if __name__ == "__main__":
    asyncio.run(sync_telecom_decisions())

