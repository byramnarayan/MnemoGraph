"""
Telecom Enterprise Dataset Ingestion Engine
Ingests the 1,200+ realistic telecom artifacts through the full backend pipeline:
1. Provisions the 5 Telecom Personas, Teams, and RBAC clearances in PostgreSQL & FalkorDB.
2. Ingests files into PostgreSQL (Document, DocumentMetadata, DocumentSection, ExtractedEntity).
3. Indexes vector chunks via FastEmbed into Qdrant.
4. Builds Knowledge Graph nodes & edges (OWNS, CONTAINS, MEMBER_OF, DEFINES) in FalkorDB.
"""

import asyncio
import hashlib
import json
import os
import sys

# Ensure backend root is on Python sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from datetime import datetime, timezone

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.models.connector import Department, Team, Person, Document, DocumentMetadata, Project, SourceEntity, ConnectorConfig
from app.models.document_section import DocumentSection, ExtractedEntity
from app.models.provenance import Decision
from app.services.graph.repository import GraphRepository
from app.services.graph.schema import NodeLabel, RelationType
from app.services.vector.indexer import VectorIndexer
from app.core.security import hash_password

BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "datasets", "telecom_enterprise_corpus")

PERSONAS_SETUP = [
    {
        "full_name": "Rohit Patel",
        "email": "rohit.patel@telcosphere.com",
        "role": "Executive VP of Network & Telecom Ops",
        "team_name": "Executive Operations",
        "department": "Executive Leadership",
    },
    {
        "full_name": "Sarah Lindqvist",
        "email": "sarah.lindqvist@telcosphere.com",
        "role": "5G RAN & Core Systems Architect",
        "team_name": "5G RAN & Core Engineering",
        "department": "Radio Access Network",
    },
    {
        "full_name": "Tarek Mansour",
        "email": "tarek.mansour@telcosphere.com",
        "role": "BSS/OSS Telecom Billing Lead",
        "team_name": "BSS/OSS Rating & Billing",
        "department": "Telecom Finance & Revenue Assurance",
    },
    {
        "full_name": "Elena Rostova",
        "email": "elena.rostova@telcosphere.com",
        "role": "Telecom Security & Compliance Officer",
        "team_name": "Telecom Security & Compliance",
        "department": "Information Security & Lawful Intercept",
    },
    {
        "full_name": "James Wilson",
        "email": "james.wilson@telcosphere.com",
        "role": "Tier-1 NOC & Churn Analyst",
        "team_name": "NOC Operations & Customer Churn",
        "department": "Customer Operations",
    },
]

PROJECTS_SETUP = [
    {"name": "5G Standalone Metro Deployment", "team": "5G RAN & Core Engineering"},
    {"name": "BSS Wholesale Roaming TAP3 Clearing", "team": "BSS/OSS Rating & Billing"},
    {"name": "CALEA & IMSI Anonymization Vault", "team": "Telecom Security & Compliance"},
    {"name": "NOC Proactive Tower Fault Detection", "team": "NOC Operations & Customer Churn"},
]


async def provision_telecom_org(db, graph_repo):
    """Provisions teams, users, projects, and FalkorDB graph nodes for the 5 telecom personas."""
    print("Provisioning telecom organization hierarchy and RBAC roles...")
    
    # 1. Provision default company workspace node
    await graph_repo.upsert_node(
        label=NodeLabel.WORKSPACE,
        entity_id="workspace:telcosphere-prod",
        properties={"name": "TelcoSphere Production Lakehouse", "domain": "telcosphere.com"}
    )

    team_map = {}
    for p in PERSONAS_SETUP:
        # Check team
        t_res = await db.execute(select(Team).where(Team.name == p["team_name"]))
        team = t_res.scalars().first()
        if not team:
            team = Team(name=p["team_name"])
            db.add(team)
            await db.flush()
        team_map[p["team_name"]] = team

        # Check Person in Postgres
        per_res = await db.execute(select(Person).where(Person.email == p["email"]))
        person = per_res.scalars().first()
        if not person:
            person = Person(
                full_name=p["full_name"],
                email=p["email"],
                role=p["role"],
                team_id=team.id
            )
            db.add(person)
            await db.flush()

        # Check User login account in Postgres
        u_res = await db.execute(select(User).where(User.email == p["email"]))
        user = u_res.scalars().first()
        if not user:
            user = User(
                full_name=p["full_name"],
                email=p["email"],
                password_hash=hash_password("password123"),
                company_name="TelcoSphere Telecom",
                role=p["role"],
                department=p["department"],
            )
            db.add(user)
            await db.flush()

        # Graph Nodes in FalkorDB
        p_node_id = f"person:{p['email'].lower()}"
        t_node_id = f"team:{team.name.lower().replace(' ', '_').replace('/', '_')}"
        
        await graph_repo.upsert_node(NodeLabel.PERSON, p_node_id, {"email": p["email"], "name": p["full_name"], "role": p["role"]})
        await graph_repo.upsert_node(NodeLabel.TEAM, t_node_id, {"name": team.name})
        await graph_repo.upsert_edge(p_node_id, t_node_id, RelationType.MEMBER_OF)
        await graph_repo.upsert_edge(p_node_id, "workspace:telcosphere-prod", RelationType.BELONGS_TO)

    # 2. Provision Projects
    for prj in PROJECTS_SETUP:
        t = team_map.get(prj["team"])
        pr_res = await db.execute(select(Project).where(Project.name == prj["name"]))
        project = pr_res.scalars().first()
        if not project and t:
            project = Project(name=prj["name"], owner_team_id=t.id, workspace_id="telcosphere-prod")
            db.add(project)
            await db.flush()
            
        proj_node_id = f"project:{prj['name'].lower().replace(' ', '_')}"
        await graph_repo.upsert_node(NodeLabel.PROJECT, proj_node_id, {"name": prj["name"]})
        if t:
            t_node_id = f"team:{t.name.lower().replace(' ', '_').replace('/', '_')}"
            await graph_repo.upsert_edge(t_node_id, proj_node_id, RelationType.OWNS)

    # Ensure a default Telecom ConnectorConfig exists
    cc_res = await db.execute(select(ConnectorConfig).where(ConnectorConfig.name == "TelcoSphere Lakehouse Connector"))
    connector = cc_res.scalars().first()
    if not connector:
        connector = ConnectorConfig(
            name="TelcoSphere Lakehouse Connector",
            connector_type="databricks",
            host="telcosphere.cloud.databricks.com",
            workspace_id="telcosphere-prod",
            token_encrypted="encrypted-telecom-token",
            status="active"
        )
        db.add(connector)
        await db.flush()

    await db.commit()
    print("[OK] Telecom organization and personas successfully provisioned.")
    return team_map, connector


async def ingest_all_artifacts():
    """Traverses generated telecom files and ingests them into Postgres, FalkorDB, and Qdrant."""
    graph_repo = GraphRepository()
    vector_indexer = VectorIndexer()

    async with AsyncSessionLocal() as db:
        team_map, connector = await provision_telecom_org(db, graph_repo)

        # Collect all files
        all_files = []
        for root, _, files in os.walk(BASE_DIR):
            for file in files:
                if file.endswith((".py", ".sql", ".md", ".json")):
                    all_files.append(os.path.join(root, file))

        print(f"Starting ingestion of {len(all_files)} telecom artifacts into Qdrant, FalkorDB, and Postgres...")
        
        indexed_count = 0
        batch_size = 50

        for idx, file_path in enumerate(all_files, 1):
            rel_path = os.path.relpath(file_path, BASE_DIR).replace("\\", "/")
            file_name = os.path.basename(file_path)
            doc_id = os.path.splitext(file_name)[0]
            
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            file_size = len(content.encode("utf-8"))
            checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()

            # Determine Owner and Category
            if "ran_telemetry" in rel_path or "RFC" in rel_path:
                owner_email = "sarah.lindqvist@telcosphere.com"
                team_name = "5G RAN & Core Engineering"
                doc_type = "Notebook" if file_name.endswith(".py") else "Architecture_RFC"
            elif "cdr_mediation" in rel_path or "bss_oss" in rel_path:
                owner_email = "tarek.mansour@telcosphere.com"
                team_name = "BSS/OSS Rating & Billing"
                doc_type = "Mediation_Pipeline" if file_name.endswith(".py") else "Settlement_Model"
            elif "incident" in rel_path:
                owner_email = "james.wilson@telcosphere.com"
                team_name = "NOC Operations & Customer Churn"
                doc_type = "Incident_Postmortem"
            elif "unity_catalog" in rel_path:
                owner_email = "rohit.patel@telcosphere.com"
                team_name = "Executive Operations"
                doc_type = "Data_Table"
            else:
                owner_email = "elena.rostova@telcosphere.com"
                team_name = "Telecom Security & Compliance"
                doc_type = "Security_Specification"

            # 1. PostgreSQL SourceEntity + Document records
            se_res = await db.execute(select(SourceEntity).where(SourceEntity.source_id == f"telecom:{doc_id}"))
            source_entity = se_res.scalars().first()
            if not source_entity:
                t_obj = team_map.get(team_name)
                source_entity = SourceEntity(
                    connector_id=connector.id,
                    source_type="notebook" if file_name.endswith(".py") else "file",
                    source_id=f"telecom:{doc_id}",
                    source_url=f"https://telcosphere.lakehouse/{rel_path}",
                    workspace_id="telcosphere-prod",
                    team_id=t_obj.id if t_obj else None,
                    owner_user_id=owner_email,
                    title=file_name.replace("_", " ").replace(".py", "").replace(".md", "").replace(".sql", ""),
                    status="active"
                )
                db.add(source_entity)
                await db.flush()

            doc_res = await db.execute(select(Document).where(Document.source_id == f"telecom:{doc_id}"))
            doc = doc_res.scalars().first()
            if not doc:
                t_obj = team_map.get(team_name)
                doc = Document(
                    title=file_name.replace("_", " ").replace(".py", "").replace(".md", "").replace(".sql", ""),
                    source_system="TelecomLakehouse",
                    source_id=f"telecom:{doc_id}",
                    storage_key=f"telecom/{rel_path}",
                    team_id=t_obj.id if t_obj else None,
                    owner_user_id=owner_email,
                    mime_type="text/x-python" if file_name.endswith(".py") else ("text/markdown" if file_name.endswith(".md") else "application/json")
                )
                db.add(doc)
                await db.flush()

                # Document Metadata
                meta = DocumentMetadata(
                    source_entity_id=source_entity.id,
                    storage_key=doc.storage_key,
                    bucket_name="telecom-lakehouse-uploads",
                    source_url=f"https://telcosphere.lakehouse/{rel_path}",
                    size_bytes=file_size,
                    checksum=checksum,
                    mime_type=doc.mime_type,
                )
                db.add(meta)

                # Parsed structured section
                sec = DocumentSection(
                    document_id=doc.id,
                    heading=doc.title,
                    content=content[:1500],
                    order_index=1,
                    section_type="code" if file_name.endswith((".py", ".sql")) else "text"
                )
                db.add(sec)

            # 2. FalkorDB Knowledge Graph Upsert
            node_label = NodeLabel.NOTEBOOK if file_name.endswith(".py") else NodeLabel.FILE
            graph_doc_id = f"doc:{doc.source_id}"
            await graph_repo.upsert_node(
                node_label,
                graph_doc_id,
                {
                    "id": graph_doc_id,
                    "title": doc.title,
                    "path": f"/{rel_path}",
                    "storage_key": doc.storage_key,
                    "type": doc_type,
                    "owner": owner_email,
                }
            )
            # Graph ownership edge
            await graph_repo.upsert_edge(f"person:{owner_email}", graph_doc_id, RelationType.OWNS)
            await graph_repo.upsert_edge(graph_doc_id, "workspace:telcosphere-prod", RelationType.CONTAINS)

            # 3. Vector indexing in Qdrant (with retry logic)
            chunk_text_data = f"Title: {doc.title}\nCategory: {doc_type}\nOwner: {owner_email}\nTeam: {team_name}\nContent:\n{content[:900]}"
            for attempt in range(3):
                try:
                    await vector_indexer.index_document(
                        document_id=doc.id,
                        text=chunk_text_data,
                        metadata={
                            "document_id": doc.id,
                            "source_id": doc.source_id,
                            "title": doc.title,
                            "path": rel_path,
                            "owner": owner_email,
                            "team": team_name,
                            "source_type": doc_type,
                        }
                    )
                    break
                except Exception as ve:
                    if attempt == 2:
                        print(f"Warning: vector indexing skipped for {doc.id} after 3 attempts: {ve}")
                    await asyncio.sleep(1)

            indexed_count += 1
            if indexed_count % batch_size == 0 or indexed_count == len(all_files):
                await db.commit()
                print(f"[{indexed_count}/{len(all_files)}] Ingested and indexed into Postgres, Qdrant, and FalkorDB.")

    print(f"Successfully finished ingestion of {indexed_count} telecom artifacts!")


if __name__ == "__main__":
    asyncio.run(ingest_all_artifacts())
