import re
import unicodedata
from dataclasses import dataclass
from typing import List, Optional

from src.application.use_cases.ask_question import AskQuestionUseCase
from src.domain.entities import Answer, SearchMode


@dataclass(frozen=True)
class EvalCase:
    question: str
    expected: Optional[str] = None
    source: Optional[str] = None
    page: Optional[int] = None
    department: Optional[str] = None


@dataclass(frozen=True)
class EvalResult:
    case: EvalCase
    answer: str
    retrieved: Optional[bool]
    correct: bool
    cited: Optional[bool]


class EvaluateUseCase:
    def __init__(self, ask: AskQuestionUseCase) -> None:
        self._ask = ask

    def execute(self, cases: List[EvalCase], top_k: int, min_score: float, mode: SearchMode) -> List[EvalResult]:
        return [
            self._score(case, self._ask.execute(case.question, top_k, min_score, case.department, mode))
            for case in cases
        ]

    @staticmethod
    def _score(case: EvalCase, answer: Answer) -> EvalResult:
        if case.expected is None:
            return EvalResult(case, answer.text, None, not answer.found, None)

        pages = {(f"{source.department}/{source.file_name}", source.page_number) for source in answer.sources}
        return EvalResult(
            case=case,
            answer=answer.text,
            retrieved=(case.source, case.page) in pages,
            correct=re.search(case.expected, unicodedata.normalize("NFKC", answer.text), re.IGNORECASE) is not None,
            cited=f"[{case.source}, p.{case.page}]" in answer.text,
        )
