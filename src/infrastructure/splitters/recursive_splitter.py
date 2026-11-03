from typing import List

from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.core.config import settings
from src.domain.interfaces.text_splitter import ITextSplitter


class RecursiveTextSplitter(ITextSplitter):
    def __init__(
        self,
        chunk_size: int = settings.chunk_size,
        chunk_overlap: int = settings.chunk_overlap,
    ) -> None:
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def split(self, text: str) -> List[str]:
        return self._splitter.split_text(text)
