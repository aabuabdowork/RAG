from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from src.core.config import settings
from src.domain.entities import Document, DocumentStatus, SearchMode, SearchResult


def check_department(value: str) -> str:
    department = value.strip().upper()
    if department not in settings.departments:
        raise ValueError(f"unknown department, use one of: {', '.join(settings.departments)}")
    return department


class QueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000, examples=["How much is the home office allowance?"])
    department: Optional[str] = Field(default=None, examples=["HR"])
    top_k: int = Field(default=settings.top_k, ge=1, le=settings.max_top_k)
    min_score: float = Field(default=settings.min_score, ge=-1, le=1)
    mode: SearchMode = SearchMode(settings.search_mode)
    rerank: bool = settings.rerank_enabled
    multi_query: bool = settings.multi_query_enabled

    @field_validator("department")
    @classmethod
    def known_department(cls, value: Optional[str]) -> Optional[str]:
        return check_department(value) if value else None


class Source(BaseModel):
    department: str
    file_name: str
    page: int
    chunk: int
    score: float
    rerank_score: Optional[float] = None
    text: Optional[str] = None

    @classmethod
    def of(cls, result: SearchResult, with_text: bool = False) -> "Source":
        return cls(
            department=result.department,
            file_name=result.file_name,
            page=result.page_number,
            chunk=result.chunk_index,
            score=result.score,
            rerank_score=result.rerank_score,
            text=result.text if with_text else None,
        )


class AskResponse(BaseModel):
    request_id: str
    answer: str
    found: bool
    sources: List[Source]
    queries: List[str]
    tokens: Dict[str, int]


class SearchResponse(BaseModel):
    request_id: str
    queries: List[str]
    results: List[Source]


class DocumentOut(BaseModel):
    id: str
    department: str
    file_name: str
    status: DocumentStatus
    chunk_count: int
    error: Optional[str] = None

    @classmethod
    def of(cls, document: Document) -> "DocumentOut":
        return cls(
            id=document.id,
            department=document.department,
            file_name=document.file_name,
            status=document.status,
            chunk_count=document.chunk_count,
            error=document.error,
        )


class UploadResponse(BaseModel):
    id: str
    document: str
    result: str
