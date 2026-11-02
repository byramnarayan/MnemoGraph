from fastapi import APIRouter, HTTPException
from starlette.concurrency import run_in_threadpool

from app.core.deps import CurrentUser
from app.schemas.graph import (
    GraphEdgeItem,
    GraphEntityLookupResponse,
    GraphNeighborhoodResponse,
    GraphNodeItem,
    GraphQueryRequest,
    GraphQueryResponse,
)
from app.services.graph.repository import GraphRepository

router = APIRouter()
graph_repo = GraphRepository()


@router.post("/query", response_model=GraphQueryResponse)
async def execute_graph_query(
    req: GraphQueryRequest,
    current_user: CurrentUser,
):
    """
    Executes a real read-only Cypher query against FalkorDB and extracts nodes and directed edges
    to power interactive flow-canvas visualizations.
    """
    cypher = req.cypher.strip()
    # Safety check: only read-only MATCH queries permitted
    cypher_lower = cypher.lower()
    if any(mutation in cypher_lower for mutation in ["create", "delete", "set ", "remove", "drop", "merge"]):
        raise HTTPException(status_code=400, detail="Only read-only MATCH/RETURN queries are allowed.")

    def _exec():
        rows = graph_repo.client.query(cypher)
        nodes_dict: dict[str, GraphNodeItem] = {}
        edges_list: list[GraphEdgeItem] = []
        raw_rows: list[list] = []

        for row in rows:
            raw_rows.append([str(x) for x in row])
            # If standard 5-column edge return: [lblA, idA, rel, lblB, idB]
            if len(row) >= 5 and isinstance(row[1], str) and isinstance(row[4], str):
                lbl_a, id_a, rel_type, lbl_b, id_b = row[0], row[1], row[2], row[3], row[4]
                if id_a not in nodes_dict:
                    nodes_dict[id_a] = GraphNodeItem(id=id_a, label=str(lbl_a or "Node"), properties={"id": id_a})
                if id_b not in nodes_dict:
                    nodes_dict[id_b] = GraphNodeItem(id=id_b, label=str(lbl_b or "Node"), properties={"id": id_b})
                edges_list.append(
                    GraphEdgeItem(
                        source=id_a,
                        target=id_b,
                        relation=str(rel_type),
                    )
                )

        return GraphQueryResponse(
            cypher=cypher,
            nodes=list(nodes_dict.values()),
            edges=edges_list,
            raw_rows=raw_rows[:100],
            total_nodes=len(nodes_dict),
            total_edges=len(edges_list),
        )

    try:
        return await run_in_threadpool(_exec)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"FalkorDB execution error: {str(e)}")


@router.get("/entities/{entity_id:path}/related", response_model=GraphNeighborhoodResponse)
async def get_related_entities(
    entity_id: str,
    current_user: CurrentUser,
):
    try:
        neighborhood = await graph_repo.get_related_entities(entity_id)
        return neighborhood
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph retrieval error: {str(e)}")


@router.get("/user-subgraph", response_model=GraphQueryResponse)
async def get_user_authorized_subgraph(
    current_user: CurrentUser,
):
    """
    Returns the initial graph authorized for the logged-in user:
    - Admins see the broader organizational core graph.
    - Low-level users see strictly their own node, team, projects, and directly assigned colleagues.
    """
    user_role = (current_user.role or "").lower()
    user_email = current_user.email.lower()
    is_admin = any(k in user_role for k in ["admin", "executive", "vp", "director"])

    def _exec():
        if is_admin:
            cypher = """
            MATCH (a)-[r]->(b)
            WHERE NOT type(r) = 'DEFINES'
            RETURN labels(a)[0], a.id, type(r), labels(b)[0], b.id
            LIMIT 45
            """
        else:
            cypher = f"""
            MATCH (p:Person {{email: '{user_email}'}})-[r]-(target)
            RETURN labels(p)[0], p.id, type(r), labels(target)[0], target.id
            LIMIT 30
            """
        rows = graph_repo.client.query(cypher)
        nodes_dict: dict[str, GraphNodeItem] = {}
        edges_list: list[GraphEdgeItem] = []
        raw_rows: list[list] = []

        for row in rows:
            raw_rows.append([str(x) for x in row])
            if len(row) >= 5 and isinstance(row[1], str) and isinstance(row[4], str):
                lbl_a, id_a, rel_type, lbl_b, id_b = row[0], row[1], row[2], row[3], row[4]
                if id_a not in nodes_dict:
                    nodes_dict[id_a] = GraphNodeItem(id=id_a, label=str(lbl_a or "Node"), properties={"id": id_a})
                if id_b not in nodes_dict:
                    nodes_dict[id_b] = GraphNodeItem(id=id_b, label=str(lbl_b or "Node"), properties={"id": id_b})
                edges_list.append(
                    GraphEdgeItem(
                        source=id_a,
                        target=id_b,
                        relation=str(rel_type),
                    )
                )

        # Fallback if user has no edges yet: add single self node
        if not nodes_dict:
            self_id = f"person:{user_email}"
            nodes_dict[self_id] = GraphNodeItem(id=self_id, label="Person", properties={"email": user_email})

        return GraphQueryResponse(
            cypher=cypher.strip(),
            nodes=list(nodes_dict.values()),
            edges=edges_list,
            raw_rows=raw_rows[:100],
            total_nodes=len(nodes_dict),
            total_edges=len(edges_list),
        )

    return await run_in_threadpool(_exec)


@router.get("/entities/{entity_id:path}", response_model=GraphEntityLookupResponse)
async def get_graph_entity(
    entity_id: str,
    current_user: CurrentUser,
):
    entity = await graph_repo.get_entity(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found in graph database")
    return entity

