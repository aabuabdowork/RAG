import uuid
from typing import Any, Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    Document,
    FieldCondition,
    Filter,
    FilterSelector,
    Fusion,
    FusionQuery,
    MatchValue,
    Modifier,
    PayloadSchemaType,
    PointStruct,
    Prefetch,
    SparseVectorParams,
    VectorParams,
)

from src.core.config import settings
from src.domain.entities import DocumentEmbedding, SearchMode, SearchResult
from src.domain.interfaces.vector_store import IVectorStore

DENSE = "dense"
SPARSE = "bm25"
BM25_MODEL = "qdrant/bm25"


class QdrantVectorStore(IVectorStore):
    def __init__(
        self,
        dimension: int,
        url: str = settings.qdrant_url,
        collection_name: str = settings.qdrant_collection,
        prefetch_limit: int = settings.prefetch_limit,
    ) -> None:
        self._client = QdrantClient(url=url, cloud_inference=True)
        self._collection = collection_name
        self._prefetch_limit = prefetch_limit
        self._ensure_collection(dimension)

    def search(
        self,
        query: str,
        vector: List[float],
        top_k: int,
        min_score: float,
        department: Optional[str] = None,
        mode: SearchMode = SearchMode.HYBRID,
    ) -> List[SearchResult]:
        query_filter = self._where("department", department) if department else None
        points = self._client.query_points(
            collection_name=self._collection,
            limit=top_k,
            with_payload=True,
            **self._query(mode, query, vector, min_score, query_filter),
        ).points
        return [
            SearchResult(
                text=point.payload["text"],
                score=point.score,
                department=point.payload["department"],
                file_name=point.payload["file_name"],
                page_number=point.payload["page_number"],
                chunk_index=point.payload["chunk_index"],
            )
            for point in points
        ]

    def exists(self, doc_hash: str) -> bool:
        return self._count_where("doc_hash", doc_hash) > 0

    def delete_by_file(self, file_path: str) -> int:
        found = self._count_where("file_path", file_path)
        if found:
            self._client.delete(
                collection_name=self._collection,
                points_selector=FilterSelector(filter=self._where("file_path", file_path)),
                wait=True,
            )
        return found

    def upsert(self, embeddings: List[DocumentEmbedding]) -> int:
        points = [
            PointStruct(
                id=self._point_id(emb),
                vector={DENSE: emb.vector, SPARSE: self._bm25(emb.text)},
                payload={"text": emb.text, **self._json_safe(emb.metadata)},
            )
            for emb in embeddings
        ]
        if points:
            self._client.upsert(collection_name=self._collection, points=points, wait=True)
        return len(points)

    def count(self) -> int:
        return self._client.count(collection_name=self._collection, exact=True).count

    def _query(
        self,
        mode: SearchMode,
        query: str,
        vector: List[float],
        min_score: float,
        query_filter: Optional[Filter],
    ) -> Dict[str, Any]:
        dense = {"query": vector, "using": DENSE, "score_threshold": min_score}
        sparse = {"query": self._bm25(query), "using": SPARSE}
        if mode == SearchMode.DENSE:
            return {**dense, "query_filter": query_filter}
        if mode == SearchMode.SPARSE:
            return {**sparse, "query_filter": query_filter}
        return {
            "prefetch": [
                Prefetch(**dense, filter=query_filter, limit=self._prefetch_limit),
                Prefetch(**sparse, filter=query_filter, limit=self._prefetch_limit),
            ],
            "query": FusionQuery(fusion=Fusion.RRF),
        }

    def _ensure_collection(self, dimension: int) -> None:
        if self._client.collection_exists(self._collection):
            return
        self._client.create_collection(
            collection_name=self._collection,
            vectors_config={DENSE: VectorParams(size=dimension, distance=Distance.COSINE)},
            sparse_vectors_config={SPARSE: SparseVectorParams(modifier=Modifier.IDF)},
        )
        for field in ("doc_hash", "file_path", "department"):
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
    def _bm25(text: str) -> Document:
        return Document(text=text, model=BM25_MODEL)

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
