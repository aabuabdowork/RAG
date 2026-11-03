import uuid
from typing import Any, Dict, List

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    FilterSelector,
    MatchValue,
    PayloadSchemaType,
    PointStruct,
    VectorParams,
)

from src.core.config import settings
from src.domain.entities import DocumentEmbedding
from src.domain.interfaces.vector_store import IVectorStore


class QdrantVectorStore(IVectorStore):
    def __init__(
        self,
        dimension: int,
        url: str = settings.qdrant_url,
        collection_name: str = settings.qdrant_collection,
    ) -> None:
        self._client = QdrantClient(url=url)
        self._collection = collection_name
        self._ensure_collection(dimension)

    def exists(self, doc_hash: str) -> bool:
        return self._count_where("doc_hash", doc_hash) > 0

    def delete_by_file(self, file_name: str) -> int:
        found = self._count_where("file_name", file_name)
        if found:
            self._client.delete(
                collection_name=self._collection,
                points_selector=FilterSelector(filter=self._where("file_name", file_name)),
                wait=True,
            )
        return found

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

    def _ensure_collection(self, dimension: int) -> None:
        if self._client.collection_exists(self._collection):
            return
        self._client.create_collection(
            collection_name=self._collection,
            vectors_config=VectorParams(size=dimension, distance=Distance.COSINE),
        )
        for field in ("doc_hash", "file_name"):
            self._client.create_payload_index(
                collection_name=self._collection,
                field_name=field,
                field_schema=PayloadSchemaType.KEYWORD,
            )

    def _count_where(self, key: str, value: str) -> int:
        return self._client.count(
            collection_name=self._collection,
            count_filter=self._where(key, value),
            exact=True,
        ).count

    @staticmethod
    def _where(key: str, value: str) -> Filter:
        return Filter(must=[FieldCondition(key=key, match=MatchValue(value=value))])

    @staticmethod
    def _point_id(emb: DocumentEmbedding) -> str:
        meta = emb.metadata
        key = f"{meta['doc_hash']}::{meta['page_number']}::{meta['chunk_index']}"
        return str(uuid.uuid5(uuid.NAMESPACE_URL, key))

    @staticmethod
    def _json_safe(metadata: Dict[str, Any]) -> Dict[str, Any]:
        safe_types = (str, int, float, bool, type(None))
        return {k: v if isinstance(v, safe_types) else str(v) for k, v in metadata.items()}
