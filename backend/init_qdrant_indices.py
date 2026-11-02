from app.services.vector.qdrant_client import QdrantService

def init_indexes():
    qs = QdrantService()
    print("Qdrant indices ensured.")

if __name__ == "__main__":
    init_indexes()

