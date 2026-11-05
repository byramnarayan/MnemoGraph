from __future__ import annotations

import logging
from app.models.user import User
from app.schemas.ktp import (
    AssignHandoverResponse,
    KTPCandidateResponse,
    KnowledgeTransferPackageResponse,
    KtpPersonSummary,
)
from app.services.graph.falkordb_client import FalkorDBClient
from app.services.graph.repository import GraphRepository
from app.services.graph.ktp.access import KTPAccessEvaluator
from app.services.graph.ktp.directory import KTPDirectoryManager
from app.services.graph.ktp.builder import KTPBuilder
from app.services.graph.ktp.persistence import KTPPersistenceManager

logger = logging.getLogger(__name__)


class KTPService:
    """
    Knowledge Transfer Package (UKGOE Phase 9):
    Read-only subgraph traversal service with strict access control (KTP_ACCESS_POLICY),
    dynamic role scoping, handover recommendations, successor-only access gating,
    and first-class Document node persistence with IR-09 cascade invalidation.

    Modularized into sub-managers:
    - KTPAccessEvaluator: permissions & policy gates
    - KTPDirectoryManager: directory listing & handover assignment
    - KTPBuilder: sections A-G traversal & package synthesis
    - KTPPersistenceManager: FalkorDB Document persistence & staleness
    """

    def __init__(self, client: FalkorDBClient | None = None, repo: GraphRepository | None = None):
        self.client = client or FalkorDBClient()
        self.repo = repo or GraphRepository(self.client)
        self.access = KTPAccessEvaluator(self.client)
        self.directory = KTPDirectoryManager(self.client)
        self.builder = KTPBuilder(self.client)
        self.persistence = KTPPersistenceManager(self.client)

    # 1. Access Evaluation
    async def evaluate_ktp_access(self, user: User, target_person_id: str) -> tuple[bool, str, str]:
        return await self.access.evaluate_access(user, target_person_id)

    # 2. Directory & Candidates
    async def list_candidates(self) -> list[KTPCandidateResponse]:
        return await self.directory.list_candidates()

    async def list_all_personnel(self, user: User, status_filter: str | None = None) -> list[KtpPersonSummary]:
        return await self.directory.list_all_personnel(user, status_filter)

    async def assign_ktp_handover(
        self,
        source_person_id: str,
        target_person_id: str,
        notes: str | None,
        user: User,
    ) -> AssignHandoverResponse:
        return await self.directory.assign_handover(source_person_id, target_person_id, notes, user)

    # 3. Subgraph Extraction
    async def build_ktp_package(
        self,
        target_person_id: str,
        requestor_id: str,
        requestor_role: str,
        user_clearance: str = "Internal",
    ) -> KnowledgeTransferPackageResponse:
        return await self.builder.build(target_person_id, requestor_id, requestor_role, user_clearance)

    # 4. Document Persistence & Retrieval
    async def persist_ktp_document(self, ktp_data: KnowledgeTransferPackageResponse) -> str:
        return await self.persistence.persist_ktp_document(ktp_data)

    async def get_ktp_document(self, doc_id: str, requestor_clearance: str = "Internal") -> KnowledgeTransferPackageResponse | None:
        return await self.persistence.get_ktp_document(doc_id, requestor_clearance)

