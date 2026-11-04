"""Local open-source embedding service using SentenceTransformers."""
import os
import warnings
from typing import List

# Disable Hugging Face symlinks warning on Windows
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
warnings.filterwarnings("ignore", category=FutureWarning)

from langsmith import traceable
from sentence_transformers import SentenceTransformer
from src.core.config import settings
from src.domain.interfaces.embedding_service import IEmbeddingService


class HuggingFaceEmbeddingService(IEmbeddingService):
    """Infrastructure adapter for local SentenceTransformers embedding models."""

    def __init__(self, model_name: str = settings.default_embedding_model) -> None:
        self._model_name = model_name
        self._model = SentenceTransformer(model_name)
        # Handle method renaming in newer sentence_transformers
        if hasattr(self._model, "get_embedding_dimension"):
            self._dimension = self._model.get_embedding_dimension()
        else:
            self._dimension = self._model.get_sentence_embedding_dimension()

    @traceable(
        name="embed_query",
        run_type="embedding",
        process_inputs=lambda inputs: {"text": inputs["text"]},
        process_outputs=lambda vector: {"dimensions": len(vector)},
    )
    def embed_text(self, text: str) -> List[float]:
        embedding = self._model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        embeddings = self._model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

    @property
    def dimension(self) -> int:
        return int(self._dimension)
