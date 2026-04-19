from qdrant_client import QdrantClient
from qdrant_client.http import models
from sentence_transformers import SentenceTransformer
import logging
import uuid
import os

logger = logging.getLogger(__name__)

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
EMBED_MODEL = os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2")
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "telemetry_events")


class MemoryLayer:
    def __init__(self, collection_name: str = COLLECTION_NAME, use_local: bool = False):
        url = os.getenv("QDRANT_URL", "http://localhost:6333")
        if use_local or url == ":memory:":
            self.client = QdrantClient(":memory:")
        else:
            self.client = QdrantClient(url=url)
        self.collection_name = collection_name
        self.embedder = SentenceTransformer(EMBED_MODEL)
        self.vector_size = self.embedder.get_embedding_dimension()
        self._ensure_collection_exists()

    def _ensure_collection_exists(self):
        try:
            collections = self.client.get_collections().collections
            if not any(c.name == self.collection_name for c in collections):
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=self.vector_size,
                        distance=models.Distance.COSINE,
                    ),
                )
                logger.info("Created collection %s", self.collection_name)
        except Exception:
            logger.exception("Failed to ensure collection exists")
            raise

    def embed(self, text: str) -> list[float]:
        return self.embedder.encode(text).tolist()

    def store_event(self, text: str, metadata: dict):
        vector = self.embed(text)
        event_id_str = metadata.get("event_id", str(uuid.uuid4()))
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, event_id_str))
        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                models.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={"text": text, **metadata},
                )
            ],
        )

    def search_similar(self, query: str, limit: int = 5) -> list[dict]:
        query_vector = self.embed(query)
        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=limit,
        )
        return [point.payload for point in results.points]
