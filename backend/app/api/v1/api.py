from fastapi import APIRouter

from app.api.v1.endpoints import (
    answer_validation,
    answers,
    auth,
    collections,
    connectors,
    decisions,
    document_enrichment,
    entities,
    graph,
    memory,
    permissions,
    provenance,
    reconciliation,
    search,
    users,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(collections.router, prefix="/collections", tags=["Multi-Store Collections"])
api_router.include_router(memory.router, prefix="/memory", tags=["Graphiti Agent Memory"])
api_router.include_router(connectors.router, prefix="/connectors", tags=["Connectors"])
api_router.include_router(graph.router, prefix="/graph", tags=["Knowledge Graph"])
api_router.include_router(search.router, prefix="/search", tags=["Semantic Search & Intelligence"])
api_router.include_router(answers.router, prefix="/answers", tags=["Explainable Answer Engine"])
api_router.include_router(decisions.router, prefix="/decisions", tags=["Decisions"])
api_router.include_router(document_enrichment.router, prefix="", tags=["Document Enrichment"])
api_router.include_router(reconciliation.router, prefix="", tags=["Sync Reconciliation"])
api_router.include_router(permissions.router, prefix="", tags=["Permissions"])
api_router.include_router(answer_validation.router, prefix="", tags=["Answer Quality Validation"])
api_router.include_router(provenance.router, prefix="", tags=["Provenance Cross-Links"])
api_router.include_router(entities.router, prefix="", tags=["Entities & Provenance"])

