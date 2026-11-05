from __future__ import annotations

import json
import logging
from typing import Any
from starlette.concurrency import run_in_threadpool

from app.schemas.ktp import KnowledgeTransferPackageResponse
from app.services.graph.falkordb_client import FalkorDBClient

logger = logging.getLogger(__name__)


def _safe_str(val: Any) -> str:
    if val is None:
        return ""
    return str(val).replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ")


class KTPPersistenceManager:
    """
    Manages persistence of KTP documents as first-class :Document nodes in FalkorDB,
    connecting them to subjects and referenced entities, and handling IR-09 stale cascades.
    """

    def __init__(self, client: FalkorDBClient):
        self.client = client

    async def persist_ktp_document(self, ktp_data: KnowledgeTransferPackageResponse) -> str:
        """
        Creates a :Document node representing the KTP artifact.
        Links (:Document)-[:DOCUMENTS]->(:Person) and to all referenced entities.
        Sets person.ktp_generated = true, ktp_doc_id = doc_id.
        """
        def _exec() -> str:
            doc_id = ktp_data.doc_id
            now_iso = ktp_data.generated_at
            title = f"Knowledge Transfer Package — {ktp_data.subject_person_name}"
            body_dict = ktp_data.model_dump(exclude={"doc_id", "is_stale", "cascade_warning"})
            body_json = _safe_str(json.dumps(body_dict))

            # 1. Create or Update :Document node
            cypher_doc = f"""
            MERGE (d:Document {{id: '{doc_id}'}})
            SET d.title = '{_safe_str(title)}',
                d.document_type = 'knowledge_transfer_package',
                d.body = '{body_json}',
                d.creation_date = '{now_iso[:10]}',
                d.author_id = '{_safe_str(ktp_data.requestor_id)}',
                d.status = 'approved',
                d.classification = '{ktp_data.classification}',
                d.downstream_recompute_needed = false,
                d.recompute_triggered_by = null,
                d.updated_at = '{now_iso}'
            RETURN d.id
            """
            self.client.query(cypher_doc)

            # 2. Link (:Document)-[:DOCUMENTS]->(:Person)
            link_person = f"""
            MATCH (d:Document {{id: '{doc_id}'}}), (p:Person {{id: '{_safe_str(ktp_data.subject_person_id)}'}})
            MERGE (d)-[:DOCUMENTS]->(p)
            SET p.ktp_generated = true,
                p.ktp_doc_id = '{doc_id}',
                p.ktp_generated_at = '{now_iso}'
            """
            self.client.query(link_person)

            # 3. Link (:Document)-[:DOCUMENTS]->(referenced_entities)
            for ref_id in ktp_data.referenced_entity_ids:
                if ref_id == ktp_data.subject_person_id:
                    continue
                safe_ref = _safe_str(ref_id)
                link_ref = f"""
                MATCH (d:Document {{id: '{doc_id}'}}), (target {{id: '{safe_ref}'}})
                MERGE (d)-[:DOCUMENTS]->(target)
                """
                try:
                    self.client.query(link_ref)
                except Exception as ex:
                    logger.debug(f"Edge creation to {safe_ref} skipped: {ex}")

            return doc_id

        return await run_in_threadpool(_exec)

    async def get_ktp_document(self, doc_id: str, requestor_clearance: str = "Internal") -> KnowledgeTransferPackageResponse | None:
        """
        Retrieves a persisted KTP document and checks staleness / IR-09 cascade warning.
        """
        def _exec() -> KnowledgeTransferPackageResponse | None:
            clean_id = _safe_str(doc_id)
            cypher = f"""
            MATCH (d:Document {{id: '{clean_id}'}})
            WHERE d.document_type = 'knowledge_transfer_package'
            OPTIONAL MATCH (d)-[:DOCUMENTS]->(p:Person)
            RETURN d.id, d.title, d.body, d.author_id, d.creation_date, d.classification,
                   d.downstream_recompute_needed, d.recompute_triggered_by, p.id, coalesce(p.full_name, p.name, p.id)
            """
            rows = self.client.query(cypher)
            if not rows or not rows[0] or not rows[0][0]:
                return None

            r = rows[0]
            body_raw = r[2] or "{}"
            try:
                body_dict = json.loads(body_raw)
            except Exception:
                body_dict = {}

            is_stale = bool(r[6])
            triggered_by = r[7]
            cascade_warning = None
            if is_stale:
                cascade_warning = f"Referenced entity '{triggered_by}' was modified after generation. Stale content detected via IR-09 Cascade."

            return KnowledgeTransferPackageResponse(
                doc_id=r[0],
                subject_person_id=r[8] or body_dict.get("subject_person_id", ""),
                subject_person_name=r[9] or body_dict.get("subject_person_name", ""),
                requestor_id=r[3] or body_dict.get("requestor_id", ""),
                requestor_role=body_dict.get("requestor_role", "admin"),
                generated_at=body_dict.get("generated_at", r[4] or ""),
                classification=r[5] or "Internal",
                is_stale=is_stale,
                cascade_warning=cascade_warning,
                referenced_entity_ids=body_dict.get("referenced_entity_ids", []),
                section_a_profile=body_dict.get("section_a_profile"),
                section_b_ownership=body_dict.get("section_b_ownership"),
                section_c_decisions=body_dict.get("section_c_decisions"),
                section_d_incidents=body_dict.get("section_d_incidents"),
                section_e_knowledge=body_dict.get("section_e_knowledge"),
                section_f_risks=body_dict.get("section_f_risks"),
                section_g_handover=body_dict.get("section_g_handover"),
            )

        return await run_in_threadpool(_exec)

