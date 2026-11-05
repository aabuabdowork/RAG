from dataclasses import replace
from typing import List

import torch
from langsmith import traceable
from sentence_transformers import CrossEncoder

from src.core.config import settings
from src.domain.entities import SearchResult
from src.domain.interfaces.reranker import IReranker


class CrossEncoderReranker(IReranker):
    def __init__(
        self,
        model_name: str = settings.rerank_model,
        min_score: float = settings.min_rerank_score,
    ) -> None:
        self._model = CrossEncoder(model_name)
        self._min_score = min_score

    @traceable(
        name="rerank",
        run_type="chain",
        process_inputs=lambda inputs: {
            "query": inputs["query"],
            "candidates": len(inputs["results"]),
            "top_n": inputs["top_n"],
        },
    )
    def rerank(self, query: str, results: List[SearchResult], top_n: int) -> List[SearchResult]:
        if not results:
            return []
        scores = self._model.predict(
            [(query, result.text) for result in results],
            activation_fn=torch.nn.Sigmoid(),
        )
        ranked = sorted(zip(results, scores), key=lambda pair: pair[1], reverse=True)
        return [
            replace(result, rerank_score=float(score))
            for result, score in ranked[:top_n]
            if score >= self._min_score
        ]
