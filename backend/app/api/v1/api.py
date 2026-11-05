from fastapi import APIRouter

from app.api.v1.endpoints import (
    answer_validation,
    answers,
    auth,
    collections,
    connectors,
    connectors_postgres,
    decisions,
    document_enrichment,
    entities,
    graph,
    incidents,
    incident_intelligence,
    ktp,
    memory,
    ontology_evolution,
    permissions,
    proposals,
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
api_router.include_router(connectors_postgres.router, prefix="/connectors", tags=["PostgreSQL Connector"])
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
api_router.include_router(ontology_evolution.router, prefix="/ontology", tags=["Ontology Self-Upgrade"])
api_router.include_router(ktp.router, prefix="/ktp", tags=["Knowledge Transfer Package"])
api_router.include_router(incidents.router, prefix="/incidents", tags=["Incident Interconnect"])
api_router.include_router(incident_intelligence.router, prefix="/incident-intelligence", tags=["Incident Intelligence"])
api_router.include_router(proposals.router, prefix="/proposals", tags=["Action Proposals"])
