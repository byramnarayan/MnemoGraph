import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))
os.chdir(str(backend_dir))

from app.services.graph.falkordb_client import FalkorDBClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("enrich_falkor")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
RECORDS_DIR = OUTPUT_DIR / "records"
MANIFEST_PATH = OUTPUT_DIR / "relationship_manifest.json"


def enrich():
    falkor = FalkorDBClient()
    graph = falkor.get_graph()

    logger.info("Loading records from %s ...", RECORDS_DIR)
    emps = json.load(open(RECORDS_DIR / "employees.json", "r", encoding="utf-8"))
    roles = json.load(open(RECORDS_DIR / "role_histories.json", "r", encoding="utf-8"))
    projs = json.load(open(RECORDS_DIR / "projects.json", "r", encoding="utf-8"))
    acts = json.load(open(RECORDS_DIR / "follow_up_actions.json", "r", encoding="utf-8"))
    decs = json.load(open(RECORDS_DIR / "decisions.json", "r", encoding="utf-8"))
    docs = json.load(open(RECORDS_DIR / "business_documents.json", "r", encoding="utf-8"))
    incs = json.load(open(RECORDS_DIR / "incidents.json", "r", encoding="utf-8"))
    lessons = json.load(open(RECORDS_DIR / "lessons_learned.json", "r", encoding="utf-8"))
    teams = json.load(open(RECORDS_DIR / "teams.json", "r", encoding="utf-8"))
    depts = json.load(open(RECORDS_DIR / "departments.json", "r", encoding="utf-8"))

    team_dept_map = {t["id"]: t["department_id"] for t in teams}
    dept_name_map = {d["id"]: d["name"] for d in depts}

    # Group roles by employee_id
    emp_roles = {}
    for r in roles:
        eid = r.get("employee_id")
        if eid:
            emp_roles.setdefault(eid, []).append(r)

    # 1. Update Person nodes with rich properties & role history
    logger.info("Enriching %d Person nodes...", len(emps))
    for e in emps:
        eid = e["id"]
        full_name = e.get("full_name") or eid
        job_title = e.get("current_job_title") or "Member"
        emp_status = e.get("employment_status") or "active"
        skills = e.get("skills", [])
        skills_str = ", ".join(skills) if isinstance(skills, list) else str(skills)
        dept_id = e.get("current_department_id") or team_dept_map.get(e.get("current_team_id"), "Operations")
        dept_name = dept_name_map.get(dept_id, dept_id)
        site_id = e.get("primary_site_id") or "SITE-0001"

        cypher = """
        MERGE (p:Person {id: $id})
        SET p.name = $name,
            p.label = $name,
            p.full_name = $name,
            p.role = $role,
            p.title = $role,
            p.current_job_title = $role,
            p.department = $dept,
            p.skills = $skills,
            p.employment_status = $status,
            p.clearance_level = 'Internal',
            p.location = $site
        """
        graph.query(
            cypher,
            {
                "id": eid,
                "name": full_name,
                "role": job_title,
                "dept": dept_name,
                "skills": skills_str,
                "status": emp_status,
                "site": site_id,
            },
        )

        # Create HELD_ROLE sub-nodes for career history
        for r_entry in emp_roles.get(eid, []):
            role_cypher = """
            MATCH (p:Person {id: $pid})
            CREATE (rl:Role {title: $title, department: $dept})
            CREATE (p)-[:HELD_ROLE {start_date: $start, end_date: $end, reason: $reason}]->(rl)
            """
            try:
                graph.query(
                    role_cypher,
                    {
                        "pid": eid,
                        "title": r_entry.get("job_title", "Engineer"),
                        "dept": dept_name,
                        "start": r_entry.get("start_date") or "",
                        "end": r_entry.get("end_date") or "",
                        "reason": r_entry.get("reason") or "normal",
                    },
                )
            except Exception as ex:
                pass

    # 2. Enrich Projects and create milestones & leadership links
    logger.info("Enriching %d Project nodes...", len(projs))
    for p in projs:
        pid = p["id"]
        pname = p.get("name") or pid
        lead = p.get("lead_emp_id")
        p_status = p.get("status") or "active"

        cypher = """
        MERGE (proj:Project {id: $id})
        SET proj.name = $name,
            proj.status = $status,
            proj.classification = 'Internal',
            proj.lead_emp_id = $lead
        """
        graph.query(cypher, {"id": pid, "name": pname, "status": p_status, "lead": lead or ""})

        # Lead relationship
        if lead:
            graph.query(
                "MATCH (p:Person {id: $lead}), (proj:Project {id: $pid}) MERGE (p)-[:LEADS]->(proj) MERGE (proj)-[:LED_BY]->(p)",
                {"lead": lead, "pid": pid},
            )

        # Contributor relationships
        for mem in p.get("team_emp_ids", []):
            graph.query(
                "MATCH (p:Person {id: $mem}), (proj:Project {id: $pid}) MERGE (p)-[:CONTRIBUTES_TO]->(proj) MERGE (p)-[:MEMBER_OF]->(proj)",
                {"mem": mem, "pid": pid},
            )

        # Milestones
        for m in p.get("milestones", []):
            mid = f"MS_{pid}_{m.get('name', 'm')[:10]}"
            m_cypher = """
            MATCH (proj:Project {id: $pid})
            MERGE (ms:Milestone {id: $mid})
            SET ms.name = $name, ms.status = $status, ms.target_date = $target
            MERGE (proj)-[:PART_OF]->(ms)
            """
            graph.query(
                m_cypher,
                {
                    "pid": pid,
                    "mid": mid,
                    "name": m.get("name", "Milestone"),
                    "status": m.get("status", "open"),
                    "target": m.get("target_date") or "",
                },
            )

    # 3. Enrich Tasks (follow_up_actions) and link to Assignees & Sources
    logger.info("Enriching %d Follow-up Action / Task nodes...", len(acts))
    for a in acts:
        aid = a["id"]
        title = a.get("title") or aid
        status = a.get("status") or "open"
        due = a.get("due_date") or ""
        eff = a.get("effectiveness_label") or "not_yet_assessed"
        assigned = a.get("assigned_emp_id")
        source_id = a.get("source_id")

        cypher = """
        MERGE (t:Task {id: $id})
        SET t.title = $title,
            t.name = $title,
            t.status = $status,
            t.due_date = $due,
            t.effectiveness_label = $eff,
            t.classification = 'Internal'
        """
        graph.query(cypher, {"id": aid, "title": title, "status": status, "due": due, "eff": eff})

        if assigned:
            graph.query(
                "MATCH (t:Task {id: $aid}), (p:Person {id: $pid}) MERGE (t)-[:ASSIGNED_TO]->(p) MERGE (p)-[:ASSIGNED_TO]->(t)",
                {"aid": aid, "pid": assigned},
            )

        if source_id:
            # Source could be Decision or Incident
            graph.query(
                """
                MATCH (t:Task {id: $aid}), (s {id: $sid})
                MERGE (t)-[:RAISED_FROM]->(s)
                MERGE (t)-[:FOLLOWED_BY]->(s)
                """,
                {"aid": aid, "sid": source_id},
            )

    # 4. Enrich Decisions and link to Decider & Project
    logger.info("Enriching %d Decision nodes...", len(decs))
    for d in decs:
        did = d["id"]
        title = d.get("title") or did
        outcome = d.get("outcome") or "pending"
        dtype = d.get("decision_type") or "technical"
        ddate = d.get("decision_date") or ""
        rca = d.get("root_cause_analysis") or ""
        decider = d.get("deciding_emp_id")
        project_id = d.get("project_id")

        cypher = """
        MERGE (dec:Decision {id: $id})
        SET dec.title = $title,
            dec.name = $title,
            dec.outcome = $outcome,
            dec.decision_type = $dtype,
            dec.decision_date = $ddate,
            dec.root_cause_analysis = $rca,
            dec.classification = 'Internal'
        """
        graph.query(
            cypher,
            {
                "id": did,
                "title": title,
                "outcome": outcome,
                "dtype": dtype,
                "ddate": ddate,
                "rca": rca,
            },
        )

        if decider:
            graph.query(
                """
                MATCH (dec:Decision {id: $did}), (p:Person {id: $pid})
                MERGE (dec)-[:AUTHORED_BY]->(p)
                MERGE (dec)-[:MADE_BY]->(p)
                MERGE (p)-[:MADE_BY]->(dec)
                """,
                {"did": did, "pid": decider},
            )

        if project_id:
            graph.query(
                """
                MATCH (dec:Decision {id: $did}), (proj:Project {id: $pid})
                MERGE (dec)-[:LINKED_TO_PROJECT]->(proj)
                MERGE (proj)-[:LINKED_TO_PROJECT]->(dec)
                """,
                {"did": did, "pid": project_id},
            )

    # 5. Enrich Documents and link to Authors & Referenced Entities
    logger.info("Enriching %d Business Document nodes...", len(docs))
    for doc in docs:
        doc_id = doc["id"]
        title = doc.get("title") or doc_id
        doc_type = doc.get("document_type") or "Document"
        status = doc.get("status") or "approved"
        cdate = doc.get("creation_date") or ""
        author = doc.get("author_emp_id")
        successor = doc.get("successor_doc_id")

        cypher = """
        MERGE (d:Document {id: $id})
        SET d.title = $title,
            d.name = $title,
            d.document_type = $dtype,
            d.status = $status,
            d.creation_date = $cdate,
            d.classification = 'Internal'
        """
        graph.query(
            cypher,
            {"id": doc_id, "title": title, "dtype": doc_type, "status": status, "cdate": cdate},
        )

        if author:
            graph.query(
                """
                MATCH (d:Document {id: $did}), (p:Person {id: $pid})
                MERGE (d)-[:AUTHORED_BY]->(p)
                MERGE (p)-[:AUTHORED_BY]->(d)
                """,
                {"did": doc_id, "pid": author},
            )

        if successor:
            graph.query(
                "MATCH (d:Document {id: $did}), (succ:Document {id: $sid}) MERGE (d)-[:SUPERSEDED_BY]->(succ)",
                {"did": doc_id, "sid": successor},
            )

        for ref_id in doc.get("referenced_entity_ids", []):
            graph.query(
                """
                MATCH (d:Document {id: $did}), (ref {id: $rid})
                MERGE (d)-[:DOCUMENTS]->(ref)
                MERGE (d)-[:DOCUMENTED_IN]->(ref)
                MERGE (ref)-[:REFERENCED_BY]->(d)
                """,
                {"did": doc_id, "rid": ref_id},
            )

    # 6. Enrich Incidents and link to Projects & Documents
    logger.info("Enriching %d Incident nodes...", len(incs))
    for inc in incs:
        iid = inc["id"]
        ititle = inc.get("title") or iid
        severity = inc.get("severity") or "P2"
        itype = inc.get("incident_type") or "outage"
        cause_status = inc.get("cause_status") or "confirmed"
        project_id = inc.get("project_id")

        cypher = """
        MERGE (i:Incident {id: $id})
        SET i.title = $title,
            i.name = $title,
            i.severity = $severity,
            i.type = $itype,
            i.cause_status = $cstatus,
            i.classification = 'Internal'
        """
        graph.query(
            cypher,
            {
                "id": iid,
                "title": ititle,
                "severity": severity,
                "itype": itype,
                "cstatus": cause_status,
            },
        )

        if project_id:
            graph.query(
                """
                MATCH (i:Incident {id: $iid}), (proj:Project {id: $pid})
                MERGE (i)-[:LINKED_TO_PROJECT]->(proj)
                MERGE (proj)-[:LINKED_TO_PROJECT]->(i)
                """,
                {"iid": iid, "pid": project_id},
            )

    # 7. Lessons Learned
    logger.info("Enriching %d Lessons Learned nodes...", len(lessons))
    for l in lessons:
        lid = l["id"]
        proj_id = l.get("project_id")
        desc = l.get("description") or ""

        cypher = """
        MERGE (les:Lesson {id: $id})
        SET les.title = $title,
            les.name = $title,
            les.summary = $desc,
            les.description = $desc
        """
        graph.query(cypher, {"id": lid, "title": f"Lesson {lid}", "desc": desc})

        if proj_id:
            graph.query(
                """
                MATCH (les:Lesson {id: $lid}), (proj:Project {id: $pid})
                MERGE (proj)-[:DERIVED_FROM]->(les)
                MERGE (les)-[:DERIVED_FROM]->(proj)
                """,
                {"lid": lid, "pid": proj_id},
            )

    logger.info("Knowledge Graph Enrichment Completed Successfully!")


if __name__ == "__main__":
    enrich()

