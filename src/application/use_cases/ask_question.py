from typing import List, Optional

from src.application.use_cases.search_documents import SearchDocumentsUseCase
from src.domain.entities import Answer, SearchMode, SearchResult
from src.domain.interfaces.llm_service import ILLMService

NOT_FOUND = "I couldn't find this in the documents."

PROMPT = """You answer questions using ONLY the context below.

Rules:
- Use only facts from the context. No outside knowledge.
- After each fact, cite its source exactly as shown, e.g. [HR/remote_work_policy.pdf, p.1].
- If the context does not contain the answer, reply exactly: {not_found}
- Be short and clear.

Context:
{context}

Question: {question}
Answer:"""


class AskQuestionUseCase:
    def __init__(self, search: SearchDocumentsUseCase, llm: ILLMService) -> None:
        self._search = search
        self._llm = llm

    def execute(
        self,
        question: str,
        top_k: int,
        min_score: float,
        department: Optional[str] = None,
        mode: SearchMode = SearchMode.HYBRID,
    ) -> Answer:
        sources = self._search.execute(question, top_k, min_score, department, mode)
        if not sources:
            return Answer(text=NOT_FOUND, sources=[])

        prompt = PROMPT.format(
            not_found=NOT_FOUND,
            context=self._build_context(sources),
            question=question,
        )
        return Answer(text=self._llm.generate(prompt).strip(), sources=sources)

    @staticmethod
    def _build_context(sources: List[SearchResult]) -> str:
        return "\n\n".join(
            f"[{source.department}/{source.file_name}, p.{source.page_number}]\n{source.text}"
            for source in sources
        )
