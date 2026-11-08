import threading
from functools import cached_property
from typing import Dict

from src.application.cached_llm import CachedLLMService
from src.application.use_cases.ask_question import AskQuestionUseCase
from src.application.use_cases.delete_document import DeleteDocumentUseCase
from src.application.use_cases.embed_document import EmbedDocumentUseCase
from src.application.use_cases.expand_query import ExpandQueryUseCase
from src.application.use_cases.index_documents import IndexDocumentsUseCase
from src.application.use_cases.metrics_report import MetricsReportUseCase
from src.application.use_cases.reconcile import ReconcileUseCase
from src.application.use_cases.search_documents import SearchDocumentsUseCase
from src.application.use_cases.upload_document import UploadDocumentUseCase
from src.core.config import settings
from src.domain.interfaces.document_repository import IDocumentRepository
from src.domain.interfaces.llm_service import ILLMService
from src.domain.interfaces.metrics import IMetrics
from src.domain.interfaces.object_storage import IObjectStorage
from src.infrastructure.cache.sqlite_cache import SqliteCache
from src.infrastructure.embeddings.huggingface_service import HuggingFaceEmbeddingService
from src.infrastructure.llm.openrouter_service import OpenRouterLLMService
from src.infrastructure.loaders.pypdf_loader import PyPDFDocumentLoader
from src.infrastructure.rerankers.cross_encoder_reranker import CrossEncoderReranker
from src.infrastructure.splitters.recursive_splitter import RecursiveTextSplitter
from src.infrastructure.supabase.client import create_supabase_client
from src.infrastructure.supabase.document_repository import SupabaseDocumentRepository
from src.infrastructure.supabase.object_storage import SupabaseObjectStorage
from src.infrastructure.tokenizers.tiktoken_counter import TiktokenCounter
from src.infrastructure.vectorstores.qdrant_store import QdrantVectorStore


class Container:
    def __init__(self, metrics: IMetrics, cache_enabled: bool = settings.cache_enabled) -> None:
        self.metrics = metrics
        self._cache_enabled = cache_enabled
        self._index_lock = threading.Lock()

    @cached_property
    def embedder(self) -> HuggingFaceEmbeddingService:
        return HuggingFaceEmbeddingService()

    @cached_property
    def store(self) -> QdrantVectorStore:
        return QdrantVectorStore(dimension=self.embedder.dimension)

    @cached_property
    def counter(self) -> TiktokenCounter:
        return TiktokenCounter()

    @cached_property
    def reranker(self) -> CrossEncoderReranker:
        return CrossEncoderReranker()

    @cached_property
    def llm(self) -> ILLMService:
        llm = OpenRouterLLMService(metrics=self.metrics)
        if not self._cache_enabled:
            return llm
        namespace = f"{settings.default_model}|{settings.llm_temperature}|{settings.max_output_tokens}"
        return CachedLLMService(llm, SqliteCache(), namespace, self.metrics)

    @cached_property
    def expander(self) -> ExpandQueryUseCase:
        return ExpandQueryUseCase(self.llm, self.counter, settings.max_query_variants, settings.max_question_tokens)

    @cached_property
    def repository(self) -> IDocumentRepository:
        return SupabaseDocumentRepository(self._supabase)

    @cached_property
    def storage(self) -> IObjectStorage:
        return SupabaseObjectStorage(self._supabase)

    @cached_property
    def _supabase(self):
        return create_supabase_client()

    def search(self, rerank: bool, multi_query: bool) -> SearchDocumentsUseCase:
        return SearchDocumentsUseCase(
            embedder=self.embedder,
            store=self.store,
            max_top_k=settings.max_top_k,
            reranker=self.reranker if rerank else None,
            expander=self.expander if multi_query else None,
            rerank_candidates=settings.rerank_candidates,
            multi_query_candidates=settings.multi_query_candidates,
        )

    def ask(self, rerank: bool, multi_query: bool) -> AskQuestionUseCase:
        return AskQuestionUseCase(
            search=self.search(rerank, multi_query),
            llm=self.llm,
            counter=self.counter,
            max_question_tokens=settings.max_question_tokens,
            max_context_tokens=settings.max_context_tokens,
        )

    def upload(self) -> UploadDocumentUseCase:
        return UploadDocumentUseCase(self.repository, self.storage)

    def delete(self) -> DeleteDocumentUseCase:
        return DeleteDocumentUseCase(self.repository, self.storage, self.store)

    def reconcile(self) -> ReconcileUseCase:
        return ReconcileUseCase(self.repository, self.store)

    def stats(self) -> MetricsReportUseCase:
        return MetricsReportUseCase(self.metrics, settings.default_model)

    def index_pending(self) -> Dict[str, str]:
        embed = EmbedDocumentUseCase(PyPDFDocumentLoader(), RecursiveTextSplitter(), self.embedder)
        with self._index_lock:
            return IndexDocumentsUseCase(self.repository, self.storage, embed, self.store).execute()
