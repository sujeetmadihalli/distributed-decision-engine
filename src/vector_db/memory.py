from qdrant_client import QdrantClient
from qdrant_client.http import models
import logging
import uuid

logger = logging.getLogger(__name__)

class MockEmbeddings:
    def __init__(self, size=384):
        self.size = size
    def embed_query(self, text: str):
        return [0.1] * self.size
    def embed_documents(self, texts: list):
        return [[0.1] * self.size for _ in texts]

class MemoryLayer:
    def __init__(self, collection_name="telemetry_events"):
        # Using in-memory Qdrant to bypass Docker hangs on WSL2
        self.client = QdrantClient(":memory:")
        self.collection_name = collection_name
        # Using MockEmbeddings to bypass PyTorch WSL2 CUDA deadlocks for Phase 1 verification
        self.embeddings = MockEmbeddings(size=384)
        self._ensure_collection_exists()

    def _ensure_collection_exists(self):
        try:
            collections = self.client.get_collections().collections
            if not any(c.name == self.collection_name for c in collections):
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=384, # Size for all-MiniLM-L6-v2
                        distance=models.Distance.COSINE
                    )
                )
                logger.info(f"Created collection {self.collection_name}")
        except Exception as e:
            logger.error(f"Failed to ensure collection exists: {e}")

    def store_event(self, text: str, metadata: dict):
        vector = self.embeddings.embed_query(text)
        event_id_str = metadata.get("event_id", str(uuid.uuid4()))
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, event_id_str))
        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                models.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={"text": text, **metadata}
                )
            ]
        )

    def search_similar(self, query: str, limit: int = 5):
        query_vector = self.embeddings.embed_query(query)
        hits = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=limit
        )
        return [hit.payload for hit in hits]
