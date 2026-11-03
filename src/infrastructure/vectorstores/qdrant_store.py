import uuid
from typing import Any, Dict, List

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from src.core.config import settings
from src.domain.entities import DocumentEmbedding
from src.domain.interfaces.vector_store import IVectorStore


class QdrantVectorStore(IVectorStore):
    def __init__(
        self,
        url: str = settings.qdrant_url,
        collection_name: str = settings.qdrant_collection,
    ) -> None:
        self._client = QdrantClient(url=url)
        self._collection = collection_name

    def ensure_collection(self, dimension: int) -> None:
        if not self._client.collection_exists(self._collection):
            self._client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(size=dimension, distance=Distance.COSINE),
            )

    def upsert(self, embeddings: List[DocumentEmbedding]) -> int:
        points = [
            PointStruct(
                id=self._point_id(emb),
                vector=emb.vector,
                payload={"text": emb.text, **self._json_safe(emb.metadata)},
            )
            for emb in embeddings
        ]
        if points:
            self._client.upsert(collection_name=self._collection, points=points, wait=True)
        return len(points)

    def count(self) -> int:
        return self._client.count(collection_name=self._collection, exact=True).count

    @staticmethod
    def _point_id(emb: DocumentEmbedding) -> str:
        meta = emb.metadata
        key = f"{meta.get('source')}::{meta.get('page_number')}::{meta.get('chunk_index')}"
        return str(uuid.uuid5(uuid.NAMESPACE_URL, key))

    @staticmethod
    def _json_safe(metadata: Dict[str, Any]) -> Dict[str, Any]:
        safe_types = (str, int, float, bool, type(None))
        return {k: v if isinstance(v, safe_types) else str(v) for k, v in metadata.items()}
