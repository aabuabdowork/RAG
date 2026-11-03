import hashlib
from dataclasses import replace
from pathlib import Path
from typing import Union

from src.application.use_cases.embed_document import EmbedDocumentUseCase
from src.domain.interfaces.vector_store import IVectorStore


class IngestDocumentUseCase:
    def __init__(self, embed: EmbedDocumentUseCase, store: IVectorStore) -> None:
        self._embed = embed
        self._store = store

    def execute(self, file_path: Union[str, Path]) -> str:
        path = Path(file_path)
        doc_hash = hashlib.sha256(path.read_bytes()).hexdigest()

        if self._store.exists(doc_hash):
            return "skipped"

        replaced = self._store.delete_by_file(path.name)
        embeddings = [
            replace(emb, metadata={**emb.metadata, "doc_hash": doc_hash, "file_name": path.name})
            for emb in self._embed.execute(path)
        ]
        if not embeddings:
            return "empty"

        self._store.upsert(embeddings)
        return "updated" if replaced else "indexed"
