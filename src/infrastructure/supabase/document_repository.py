from dataclasses import asdict, fields
from typing import Any, Dict, List, Optional

from supabase import Client

from src.core.config import settings
from src.domain.entities import Document, DocumentStatus
from src.domain.interfaces.document_repository import IDocumentRepository
from src.infrastructure.supabase.errors import supabase_call

COLUMNS = [field.name for field in fields(Document)]


class SupabaseDocumentRepository(IDocumentRepository):
    def __init__(self, client: Client, table: str = settings.supabase_table) -> None:
        self._client = client
        self._table = table

    @supabase_call
    def get(self, department: str, file_name: str) -> Optional[Document]:
        rows = self._select().eq("department", department).eq("file_name", file_name).execute().data
        return self._to_document(rows[0]) if rows else None

    @supabase_call
    def list(self, status: Optional[DocumentStatus] = None) -> List[Document]:
        query = self._select().order("department").order("file_name")
        if status:
            query = query.eq("status", status.value)
        return [self._to_document(row) for row in query.execute().data]

    @supabase_call
    def save(self, document: Document) -> None:
        row = {**asdict(document), "status": document.status.value}
        self._client.table(self._table).upsert(row).execute()

    @supabase_call
    def delete(self, document_id: str) -> None:
        self._client.table(self._table).delete().eq("id", document_id).execute()

    def _select(self):
        return self._client.table(self._table).select(",".join(COLUMNS))

    @staticmethod
    def _to_document(row: Dict[str, Any]) -> Document:
        return Document(**{**row, "status": DocumentStatus(row["status"])})
