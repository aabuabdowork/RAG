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

    def execute(self, file_path: Union[str, Path], department: str) -> str:
        path = Path(file_path)
        department = department.upper()
        doc_hash = hashlib.sha256(path.read_bytes()).hexdigest()

        if self._store.exists(doc_hash):
            return "skipped"

        relative_path = f"{department}/{path.name}"
        replaced = self._store.delete_by_file(relative_path)
        metadata = {
            "doc_hash": doc_hash,
            "department": department,
            "file_name": path.name,
            "file_path": relative_path,
        }
        embeddings = [
            replace(emb, metadata={**emb.metadata, **metadata})
            for emb in self._embed.execute(path)
        ]
        if not embeddings:
            return "empty"

        self._store.upsert(embeddings)
        return "updated" if replaced else "indexed"
