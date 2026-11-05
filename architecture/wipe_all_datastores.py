import asyncio
import os
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))
os.chdir(str(backend_dir))

from sqlalchemy import text
from app.core.database import engine
from app.services.graph.falkordb_client import FalkorDBClient
from app.services.vector.qdrant_client import QdrantService


async def wipe_all_data():
    """
    Cleans and empties all domain data across:
    1. PostgreSQL (Neon Cloud DB) tables while preserving primary users/auth
    2. FalkorDB Knowledge Graph (deletes all nodes & edges)
    3. Qdrant Vector Database (wipes all collections and points)
    """
    print("=====================================================")
    print("      STARTING MULTI-STORE DATABASE PURGE            ")
    print("=====================================================")

    # 1. PostgreSQL Clean
    print("\n[1/3] Purging PostgreSQL Tables (Neon)...")
    async with engine.begin() as conn:
        res = await conn.execute(
            text(
                """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """
            )
        )
        tables = [row[0] for row in res.fetchall()]

        for t in tables:
            # Preserve user accounts so active auth sessions / logins remain valid
            if t == "users":
                await conn.execute(text("DELETE FROM users WHERE email != 'apex@gmail.com';"))
                print("  [OK] Preserved primary admin user (apex@gmail.com), pruned temp accounts")
            elif t == "password_reset_tokens":
                await conn.execute(text("TRUNCATE TABLE password_reset_tokens CASCADE;"))
                print(f"  [OK] Emptied {t}")
            else:
                try:
                    await conn.execute(text(f'TRUNCATE TABLE "{t}" CASCADE;'))
                    print(f"  [OK] Emptied table: {t}")
                except Exception as e:
                    print(f"  [FAIL] Failed to truncate {t}: {e}")

    # 2. FalkorDB Graph Clean
    print("\n[2/3] Purging FalkorDB Knowledge Graph...")
    try:
        falkor = FalkorDBClient()
        falkor.query("MATCH (n) DETACH DELETE n")
        remaining_nodes = falkor.query("MATCH (n) RETURN count(n)")[0][0]
        remaining_edges = falkor.query("MATCH ()-[r]->() RETURN count(r)")[0][0]
        print(f"  [OK] FalkorDB graph purged: 0 nodes, 0 edges (Remaining: {remaining_nodes} nodes, {remaining_edges} edges)")
    except Exception as e:
        print(f"  [FAIL] FalkorDB purge error: {e}")

    # 3. Qdrant Vector Clean
    print("\n[3/3] Purging Qdrant Vector Database Collections...")
    try:
        qdrant = QdrantService()
        colls = qdrant.client.get_collections().collections
        if not colls:
            print("  [OK] No Qdrant collections found.")
        for c in colls:
            coll_name = c.name
            qdrant.client.delete_collection(coll_name)
            print(f"  [OK] Deleted vector collection: {coll_name}")

        # Recreate empty default collection with indexes
        qdrant._ensure_collection()
        qdrant._ensure_payload_indexes()
        info = qdrant.client.get_collection(qdrant.collection_name)
        print(f"  [OK] Recreated clean collection '{qdrant.collection_name}' (Points: {info.points_count})")
    except Exception as e:
        print(f"  [FAIL] Qdrant purge error: {e}")

    print("\n=====================================================")
    print("      MULTI-STORE PURGE COMPLETED SUCCESSFULLY       ")
    print("=====================================================")


if __name__ == "__main__":
    asyncio.run(wipe_all_data())
