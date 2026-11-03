import asyncio
import os
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path("g:/memoryProject/backend")
sys.path.insert(0, str(backend_dir))
os.chdir(str(backend_dir))

from sqlalchemy import text
from app.core.database import engine
from app.services.graph.falkordb_client import FalkorDBClient
from app.services.vector.qdrant_client import QdrantService

async def wipe_all():
    print("=== STARTING FULL DATABASE WIPE ===")
    
    # 1. PostgreSQL Table Truncation
    print("\n1. Truncating PostgreSQL tables...")
    async with engine.begin() as conn:
        res = await conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """))
        tables = [row[0] for row in res.fetchall()]
        
        # We will truncate all domain data tables
        # For 'users', we keep the primary admin user (apex@gmail.com) so the UI session does not 401 crash
        for t in tables:
            if t == "users":
                # Delete non-admin dummy users, preserve the primary admin
                await conn.execute(text("DELETE FROM users WHERE email != 'apex@gmail.com';"))
                print(f"  Truncated non-admin users (kept apex@gmail.com active session)")
            elif t == "password_reset_tokens":
                await conn.execute(text("TRUNCATE TABLE password_reset_tokens CASCADE;"))
                print(f"  Truncated {t}")
            else:
                try:
                    await conn.execute(text(f'TRUNCATE TABLE "{t}" CASCADE;'))
                    print(f"  Truncated {t}")
                except Exception as e:
                    print(f"  Error truncating {t}: {e}")

    # 2. FalkorDB Graph Wipe
    print("\n2. Wiping FalkorDB Knowledge Graph...")
    try:
        falkor = FalkorDBClient()
        falkor.query("MATCH (n) DETACH DELETE n")
        remaining_nodes = falkor.query("MATCH (n) RETURN count(n)")[0][0]
        remaining_edges = falkor.query("MATCH ()-[r]->() RETURN count(r)")[0][0]
        print(f"  FalkorDB cleared. Remaining nodes: {remaining_nodes}, edges: {remaining_edges}")
    except Exception as e:
        print(f"  FalkorDB error: {e}")

    # 3. Qdrant Vector Collection Wipe
    print("\n3. Wiping Qdrant Vector Database...")
    try:
        qdrant = QdrantService()
        coll_name = qdrant.collection_name
        # Recreate or delete all points
        colls = [c.name for c in qdrant.client.get_collections().collections]
        if coll_name in colls:
            qdrant.client.delete_collection(coll_name)
            print(f"  Deleted Qdrant collection: {coll_name}")
            # Recreate empty collection with proper dimension
            qdrant._ensure_collection()
            qdrant._ensure_payload_indexes()
            print(f"  Recreated empty Qdrant collection: {coll_name}")
        info = qdrant.client.get_collection(coll_name)
        print(f"  Qdrant collection '{coll_name}' points count: {info.points_count}")
    except Exception as e:
        print(f"  Qdrant error: {e}")

    print("\n=== FULL DATABASE WIPE COMPLETED ===")

if __name__ == "__main__":
    asyncio.run(wipe_all())
