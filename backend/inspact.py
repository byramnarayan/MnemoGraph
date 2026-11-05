import asyncio
import os
import sys
from pathlib import Path

backend_dir = Path("g:/memoryProject/backend")
sys.path.insert(0, str(backend_dir))
os.chdir(str(backend_dir))

from sqlalchemy import text
from app.core.database import engine
from app.services.graph.falkordb_client import FalkorDBClient
from app.services.vector.qdrant_client import QdrantService


async def inspect():
    print("--- POSTGRESQL TABLES ---")
    try:
        async with engine.connect() as conn:
            res = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name;
            """))
            tables = [row[0] for row in res.fetchall()]
            for t in tables:
                try:
                    cnt = (await conn.execute(text(f'SELECT count(*) FROM "{t}";'))).scalar()
                    print(f"  {t}: {cnt} rows")
                except Exception as e:
                    print(f"  {t}: error {e}")
    finally:
        await engine.dispose()

    print("\n--- FALKORDB ---")
    try:
        falkor = FalkorDBClient()
        lbls = falkor.query("MATCH (n) RETURN DISTINCT labels(n)")
        total_nodes = falkor.query("MATCH (n) RETURN count(n)")[0][0]
        total_edges = falkor.query("MATCH ()-[r]->() RETURN count(r)")[0][0]
        print(f"  Total nodes: {total_nodes}, Total edges: {total_edges}")
        for l in lbls:
            if l and l[0]:
                lbl_name = l[0][0]
                cnt = falkor.query(f"MATCH (n:{lbl_name}) RETURN count(n)")[0][0]
                print(f"    Label {lbl_name}: {cnt}")
    except Exception as e:
        print(f"  FalkorDB error: {e}")

    print("\n--- QDRANT ---")
    try:
        qdrant = QdrantService()
        colls = qdrant.client.get_collections().collections
        for c in colls:
            info = qdrant.client.get_collection(c.name)
            print(f"  Collection {c.name}: {info.points_count} points")
    except Exception as e:
        print(f"  Qdrant error: {e}")


if __name__ == "__main__":
    asyncio.run(inspect())
