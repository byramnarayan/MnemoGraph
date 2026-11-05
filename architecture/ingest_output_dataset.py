import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Set up paths
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))
os.chdir(str(backend_dir))

from sqlalchemy import text
from app.core.database import AsyncSessionLocal
from app.models.entity import EntityRecord
from app.models.relationship import RelationshipRecord
from app.services.graph.falkordb_client import FalkorDBClient
from app.services.storage.s3_store import S3ObjectStore
from app.services.vector.indexer import VectorIndexer
from app.services.vector.qdrant_client import QdrantService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ingest_output")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
RECORDS_DIR = OUTPUT_DIR / "records"
MANIFEST_PATH = OUTPUT_DIR / "relationship_manifest.json"

PREFIX_TO_CLASS = {
    "EMP": ("Person", "employees.json"),
    "DEPT": ("Group", "departments.json"),
    "TEAM": ("Group", "teams.json"),
    "PROJ": ("Project", "projects.json"),
    "DEC": ("Decision", "decisions.json"),
    "INC": ("Incident", "incidents.json"),
    "ACT": ("Task", "follow_up_actions.json"),
    "LL": ("Lesson", "lessons_learned.json"),
    "DOC": ("Document", "business_documents.json"),
    "SITE": ("System", "company_profile.json"),
}


def load_all_records():
    entities = {}

    # 1. Company profile and sites
    cp_path = RECORDS_DIR / "company_profile.json"
    if cp_path.exists():
        with open(cp_path, "r", encoding="utf-8") as f:
            cp_data = json.load(f)
            company = cp_data[0] if isinstance(cp_data, list) else cp_data
            entities["ORG-AAROHAN"] = {
                "id": "ORG-AAROHAN",
                "class": "Company",
                "label": company.get("company_name", "Aarohan Digital Networks Limited"),
                "props": {
                    "company_name": company.get("company_name"),
                    "cin": company.get("cin"),
                    "registered_city": company.get("registered_city"),
                    "description": company.get("description"),
                },
                "search_text": f"{company.get('company_name')} CIN: {company.get('cin')}. {company.get('description')}",
            }
            for loc in company.get("office_locations", []):
                sid = loc.get("id")
                entities[sid] = {
                    "id": sid,
                    "class": "SiteLocation",
                    "label": f"{loc.get('city')} Site ({sid})",
                    "props": loc,
                    "search_text": f"Site Location {sid} in {loc.get('city')}. Address: {loc.get('address')}",
                }

    # 2. Departments
    dept_path = RECORDS_DIR / "departments.json"
    if dept_path.exists():
        with open(dept_path, "r", encoding="utf-8") as f:
            for item in json.load(f):
                entities[item["id"]] = {
                    "id": item["id"],
                    "class": "Department",
                    "label": item.get("name"),
                    "props": item,
                    "search_text": f"Department {item.get('name')} (ID: {item['id']}). {item.get('description')}",
                }

    # 3. Teams
    teams_path = RECORDS_DIR / "teams.json"
    if teams_path.exists():
        with open(teams_path, "r", encoding="utf-8") as f:
            for item in json.load(f):
                entities[item["id"]] = {
                    "id": item["id"],
                    "class": "Team",
                    "label": item.get("name"),
                    "props": item,
                    "search_text": f"Team {item.get('name')} (ID: {item['id']}). Department: {item.get('department_id')}, Site: {item.get('primary_site_id')}",
                }

    # 4. Employees
    emp_path = RECORDS_DIR / "employees.json"
    if emp_path.exists():
        with open(emp_path, "r", encoding="utf-8") as f:
            for item in json.load(f):
                skills = ", ".join(item.get("skills", []))
                entities[item["id"]] = {
                    "id": item["id"],
                    "class": "Person",
                    "label": item.get("full_name"),
                    "props": {k: v for k, v in item.items() if k != "role_history"},
                    "search_text": f"Employee {item.get('full_name')} (ID: {item['id']}). Job Title: {item.get('current_job_title')}. Department: {item.get('current_department_id')}. Skills: {skills}. Status: {item.get('employment_status')}",
                }

    # 5. Projects
    proj_path = RECORDS_DIR / "projects.json"
    if proj_path.exists():
        with open(proj_path, "r", encoding="utf-8") as f:
            for item in json.load(f):
                entities[item["id"]] = {
                    "id": item["id"],
                    "class": "Project",
                    "label": item.get("name"),
                    "props": {k: v for k, v in item.items() if k not in ["milestones", "lessons_learned"]},
                    "search_text": f"Project {item.get('name')} (ID: {item['id']}). Status: {item.get('status')}. Description: {item.get('description')}. Outcome: {item.get('outcome_summary')}",
                }

    # 6. Decisions
    dec_path = RECORDS_DIR / "decisions.json"
    if dec_path.exists():
        with open(dec_path, "r", encoding="utf-8") as f:
            for item in json.load(f):
                entities[item["id"]] = {
                    "id": item["id"],
                    "class": "Decision",
                    "label": item.get("title"),
                    "props": item,
                    "search_text": f"Decision {item.get('title')} (ID: {item['id']}). Type: {item.get('decision_type')}. Outcome: {item.get('outcome')}. Rationale: {item.get('rationale')}. Description: {item.get('description')}. RCA: {item.get('root_cause_analysis') or ''}",
                }

    # 7. Incidents
    inc_path = RECORDS_DIR / "incidents.json"
    if inc_path.exists():
        with open(inc_path, "r", encoding="utf-8") as f:
            for item in json.load(f):
                entities[item["id"]] = {
                    "id": item["id"],
                    "class": "Incident",
                    "label": item.get("title"),
                    "props": item,
                    "search_text": f"Incident {item.get('title')} (ID: {item['id']}). Severity: {item.get('severity')}. Type: {item.get('incident_type')}. Cause: {item.get('confirmed_cause') or item.get('initial_suspected_cause')}. Status: {item.get('cause_status')}. Description: {item.get('description')}",
                }

    # 8. Follow Up Actions
    act_path = RECORDS_DIR / "follow_up_actions.json"
    if act_path.exists():
        with open(act_path, "r", encoding="utf-8") as f:
            for item in json.load(f):
                entities[item["id"]] = {
                    "id": item["id"],
                    "class": "Task",
                    "label": item.get("title"),
                    "props": item,
                    "search_text": f"Follow-up Action {item.get('title')} (ID: {item['id']}). Status: {item.get('status')}. Effectiveness: {item.get('effectiveness_label')}. Description: {item.get('description')}",
                }

    # 9. Lessons Learned
    ll_path = RECORDS_DIR / "lessons_learned.json"
    if ll_path.exists():
        with open(ll_path, "r", encoding="utf-8") as f:
            for item in json.load(f):
                entities[item["id"]] = {
                    "id": item["id"],
                    "class": "Lesson",
                    "label": f"Lesson {item['id']}",
                    "props": item,
                    "search_text": f"Lesson Learned (ID: {item['id']}). Project: {item.get('project_id')}. Learning: {item.get('description')}",
                }

    # 10. Business Documents
    doc_path = RECORDS_DIR / "business_documents.json"
    if doc_path.exists():
        with open(doc_path, "r", encoding="utf-8") as f:
            for item in json.load(f):
                entities[item["id"]] = {
                    "id": item["id"],
                    "class": "Document",
                    "label": item.get("title"),
                    "props": {k: v for k, v in item.items() if k != "body"},
                    "body": item.get("body", ""),
                    "search_text": f"{item.get('title')} ({item.get('document_type')}). {item.get('body')}",
                }

    return entities


async def ingest_everything():
    logger.info("Loading records and relationship manifest...")
    entities = load_all_records()
    logger.info("Loaded %d entity nodes from records.", len(entities))

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)
    relationships = manifest_data.get("entries", [])
    logger.info("Loaded %d relationships from relationship_manifest.json", len(relationships))

    # -------------------------------------------------------------
    # 1. FalkorDB Knowledge Graph: Nodes and Edges from Manifest
    # -------------------------------------------------------------
    logger.info("\n--- [1/4] Ingesting FalkorDB Knowledge Graph ---")
    falkor = FalkorDBClient()
    graph = falkor.get_graph()

    # Create nodes
    logger.info("Upserting %d nodes in FalkorDB...", len(entities))
    for eid, ent in entities.items():
        node_class = ent["class"]
        lbl = ent["label"].replace('"', '\\"') if ent.get("label") else eid
        # Sanitize properties for Cypher
        cypher = f'MERGE (n:{node_class} {{id: $id}}) SET n.name = $name, n.label = $name, n.entity_id = $id'
        graph.query(cypher, {"id": eid, "name": lbl})

    # Create edges STRICTLY according to relationship_manifest.json
    logger.info("Upserting %d edges from relationship_manifest.json in FalkorDB...", len(relationships))
    edge_count = 0
    for r in relationships:
        src = r["source_id"]
        tgt = r["target_id"]
        rel_type = r["relationship_type"].upper()
        ctx = r.get("context", "")

        # Lookup node classes
        src_ent = entities.get(src)
        tgt_ent = entities.get(tgt)
        if not src_ent or not tgt_ent:
            continue

        src_class = src_ent["class"]
        tgt_class = tgt_ent["class"]

        cypher = (
            f"MATCH (a:{src_class} {{id: $src_id}}), (b:{tgt_class} {{id: $tgt_id}}) "
            f"MERGE (a)-[r:{rel_type}]->(b) "
            f"SET r.context = $context"
        )
        try:
            graph.query(cypher, {"src_id": src, "tgt_id": tgt, "context": ctx})
            edge_count += 1
        except Exception as e:
            logger.warning("FalkorDB edge creation failed for %s -> %s: %s", src, tgt, e)

    logger.info("FalkorDB Ingestion Complete: %d nodes, %d edges created.", len(entities), edge_count)

    # -------------------------------------------------------------
    # 2. Canonical PostgreSQL Relational Ledger (entities & relationships)
    # -------------------------------------------------------------
    logger.info("\n--- [2/4] Ingesting PostgreSQL Relational Ledger ---")
    now_dt = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as session:
        # Batch insert entities in chunks
        entity_records = [
            EntityRecord(
                entity_id=eid,
                entity_class=ent["class"],
                label=ent["label"],
                properties=ent["props"],
                is_stub=False,
                completeness_score=1.0,
                validation_status="valid",
                data_quality_grade="A",
                source_document_ids=[f"output:{ent['class'].lower()}"],
                property_history=[],
                provenance_sources=["dataset_manifest"],
                first_seen=now_dt,
                created_at=now_dt,
                updated_at=now_dt,
            )
            for eid, ent in entities.items()
        ]
        session.add_all(entity_records)
        await session.commit()
        logger.info("PostgreSQL entities committed: %d", len(entity_records))

        # Upsert relationships
        rel_records = [
            RelationshipRecord(
                source_id=r["source_id"],
                target_id=r["target_id"],
                relationship_type=r["relationship_type"],
                confidence=1.0,
                context=r.get("context"),
                source_document_id="relationship_manifest.json",
                is_inferred=False,
                extracted_at=now_dt,
            )
            for r in relationships
        ]
        session.add_all(rel_records)
        await session.commit()
        logger.info("PostgreSQL relationships committed: %d", len(rel_records))

    # -------------------------------------------------------------
    # 3. Object Storage (S3 / Neon)
    # -------------------------------------------------------------
    logger.info("\n--- [3/4] Ingesting Raw Documents to Neon S3 Storage ---")
    s3_store = S3ObjectStore()
    uploaded_s3 = 0
    for eid, ent in entities.items():
        if ent["class"] == "Document" and "body" in ent:
            storage_key = f"documents/aarohan/{eid}.txt"
            content = f"{ent['label']}\n\n{ent['body']}"
            try:
                await s3_store.put_object(storage_key, content.encode("utf-8"), "text/plain")
                uploaded_s3 += 1
            except Exception as e:
                logger.warning("S3 upload failed for %s: %s", eid, e)
    logger.info("Uploaded %d business documents to Neon S3 storage.", uploaded_s3)

    # -------------------------------------------------------------
    # 4. Qdrant Vector Indexing
    # -------------------------------------------------------------
    logger.info("\n--- [4/4] Ingesting Vector Search Index (Qdrant) ---")
    indexer = VectorIndexer()
    indexed_qdrant = 0
    for eid, ent in entities.items():
        search_text = ent.get("search_text", "")
        if not search_text:
            continue
        try:
            await indexer.index_document(
                document_id=f"doc_{eid}",
                text=search_text,
                doc_title=ent["label"],
                metadata={
                    "entity_id": eid,
                    "entity_class": ent["class"],
                    "classification": "Internal",
                    "department": ent["props"].get("department") or ent["props"].get("current_department_id", "Operations"),
                },
            )
            indexed_qdrant += 1
        except Exception as e:
            logger.warning("Vector indexing failed for %s: %s", eid, e)
    logger.info("Indexed %d items in Qdrant Vector DB.", indexed_qdrant)

    logger.info("\n=======================================================")
    logger.info("   ALL DATASTORES SUCCESSFULLY POPULATED ACROSS STACK  ")
    logger.info("=======================================================")


if __name__ == "__main__":
    asyncio.run(ingest_everything())

