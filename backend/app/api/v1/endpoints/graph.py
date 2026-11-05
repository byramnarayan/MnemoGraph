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
        # Clean any surrounding markdown fences or trailing semicolons
        clean_cypher = cypher.strip().replace("```cypher", "").replace("```", "").strip().rstrip(";")
        rows = graph_repo.client.query(clean_cypher)
        nodes_dict: dict[str, GraphNodeItem] = {}
        edges_list: list[GraphEdgeItem] = []
        raw_rows: list[list] = []

        for row in rows:
            raw_rows.append([str(x) for x in row])
            # Case 1: 7-column return [lbl_a, id_a, name_a, rel_type, lbl_b, id_b, name_b]
            if len(row) >= 7 and isinstance(row[1], str) and isinstance(row[5], str):
                lbl_a, id_a, name_a, rel_type, lbl_b, id_b, name_b = row[0], row[1], row[2], row[3], row[4], row[5], row[6]
                if id_a not in nodes_dict:
                    nodes_dict[id_a] = GraphNodeItem(id=id_a, label=str(lbl_a or "Node"), properties={"id": id_a, "name": str(name_a or id_a)})
                if id_b not in nodes_dict:
                    nodes_dict[id_b] = GraphNodeItem(id=id_b, label=str(lbl_b or "Node"), properties={"id": id_b, "name": str(name_b or id_b)})
                edges_list.append(
                    GraphEdgeItem(
                        source=id_a,
                        target=id_b,
                        relation=str(rel_type),
                    )
                )
            # Case 2: Standard 5-column return [lbl_a, id_a, rel_type, lbl_b, id_b]
            elif len(row) >= 5 and isinstance(row[1], str) and isinstance(row[4], str):
                lbl_a, id_a, rel_type, lbl_b, id_b = row[0], row[1], row[2], row[3], row[4]
                if id_a not in nodes_dict:
                    nodes_dict[id_a] = GraphNodeItem(id=id_a, label=str(lbl_a or "Node"), properties={"id": id_a, "name": id_a})
                if id_b not in nodes_dict:
                    nodes_dict[id_b] = GraphNodeItem(id=id_b, label=str(lbl_b or "Node"), properties={"id": id_b, "name": id_b})
                edges_list.append(
                    GraphEdgeItem(
                        source=id_a,
                        target=id_b,
                        relation=str(rel_type),
                    )
                )
            # Case 3: Path list format [target_id, path_nodes_list, path_rels_list, depth]
            elif len(row) >= 3 and isinstance(row[1], (list, tuple)) and isinstance(row[2], (list, tuple)):
                p_nodes = [str(n) for n in row[1]]
                p_rels = [str(r) for r in row[2]]
                for nid in p_nodes:
                    if nid not in nodes_dict:
                        nodes_dict[nid] = GraphNodeItem(id=nid, label="Entity", properties={"id": nid, "name": nid})
                for idx in range(min(len(p_nodes) - 1, len(p_rels))):
                    edges_list.append(
                        GraphEdgeItem(
                            source=p_nodes[idx],
                            target=p_nodes[idx + 1],
                            relation=p_rels[idx],
                        )
                    )
            # Case 4: Node/Edge objects or single node returns
            else:
                for item in row:
                    if hasattr(item, "properties") and hasattr(item, "labels"):
                        nid = str(item.properties.get("id") or getattr(item, "id", str(id(item))))
                        lbl = item.labels[0] if item.labels else "Node"
                        nm = str(item.properties.get("name") or item.properties.get("full_name") or nid)
                        if nid not in nodes_dict:
                            nodes_dict[nid] = GraphNodeItem(id=nid, label=lbl, properties={"id": nid, "name": nm, **item.properties})
                    elif hasattr(item, "relation") and hasattr(item, "src_node") and hasattr(item, "dest_node"):
                        src_id = str(getattr(item.src_node, "properties", {}).get("id", item.src_node))
                        dst_id = str(getattr(item.dest_node, "properties", {}).get("id", item.dest_node))
                        edges_list.append(GraphEdgeItem(source=src_id, target=dst_id, relation=item.relation))

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
            WHERE NOT type(r) = 'DEFINES' AND NOT a.id STARTS WITH 'dup_' AND NOT b.id STARTS WITH 'dup_'
            RETURN labels(a)[0], a.id, coalesce(a.full_name, a.name, a.title, a.id), type(r), labels(b)[0], b.id, coalesce(b.full_name, b.name, b.title, b.id)
            LIMIT 50
            """
        else:
            cypher = f"""
            MATCH (p:Person {{email: '{user_email}'}})-[r]-(target)
            WHERE NOT target.id STARTS WITH 'dup_'
            RETURN labels(p)[0], p.id, coalesce(p.full_name, p.name, p.id), type(r), labels(target)[0], target.id, coalesce(target.full_name, target.name, target.title, target.id)
            LIMIT 40
            """
        rows = graph_repo.client.query(cypher)
        nodes_dict: dict[str, GraphNodeItem] = {}
        edges_list: list[GraphEdgeItem] = []
        raw_rows: list[list] = []

        for row in rows:
            raw_rows.append([str(x) for x in row])
            if len(row) >= 7 and isinstance(row[1], str) and isinstance(row[5], str):
                lbl_a, id_a, name_a, rel_type, lbl_b, id_b, name_b = row[0], row[1], row[2], row[3], row[4], row[5], row[6]
                if id_a not in nodes_dict:
                    nodes_dict[id_a] = GraphNodeItem(id=id_a, label=str(lbl_a or "Node"), properties={"id": id_a, "name": str(name_a or id_a)})
                if id_b not in nodes_dict:
                    nodes_dict[id_b] = GraphNodeItem(id=id_b, label=str(lbl_b or "Node"), properties={"id": id_b, "name": str(name_b or id_b)})
                edges_list.append(
                    GraphEdgeItem(
                        source=id_a,
                        target=id_b,
                        relation=str(rel_type),
                    )
                )
            elif len(row) >= 5 and isinstance(row[1], str) and isinstance(row[4], str):
                lbl_a, id_a, rel_type, lbl_b, id_b = row[0], row[1], row[2], row[3], row[4]
                if id_a not in nodes_dict:
                    nodes_dict[id_a] = GraphNodeItem(id=id_a, label=str(lbl_a or "Node"), properties={"id": id_a, "name": id_a})
                if id_b not in nodes_dict:
                    nodes_dict[id_b] = GraphNodeItem(id=id_b, label=str(lbl_b or "Node"), properties={"id": id_b, "name": id_b})
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

