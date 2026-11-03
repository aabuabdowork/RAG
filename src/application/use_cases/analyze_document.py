"""Use case for extracting and analyzing documents using LLM."""
from pathlib import Path
from typing import Union

from src.domain.interfaces.document_loader import IDocumentLoader
from src.domain.interfaces.llm_service import ILLMService


class AnalyzeDocumentUseCase:
    """Use case coordinating document extraction and LLM analysis."""

    def __init__(self, loader: IDocumentLoader, llm: ILLMService) -> None:
        self._loader = loader
        self._llm = llm

    def execute(self, file_path: Union[str, Path], prompt_instruction: str = "Summarize this document:") -> str:
        document = self._loader.load(file_path)
        prompt = f"{prompt_instruction}\n\nDocument Content:\n{document.full_text}"
        return self._llm.generate(prompt)

