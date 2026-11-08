import mimetypes

from supabase import Client

from src.core.config import settings
from src.domain.interfaces.object_storage import IObjectStorage
from src.infrastructure.supabase.errors import supabase_call


class SupabaseObjectStorage(IObjectStorage):
    def __init__(self, client: Client, bucket: str = settings.supabase_bucket) -> None:
        self._bucket = client.storage.from_(bucket)

    @supabase_call
    def upload(self, path: str, data: bytes) -> None:
        content_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
        self._bucket.upload(path, data, {"content-type": content_type, "upsert": "true"})

    @supabase_call
    def download(self, path: str) -> bytes:
        return self._bucket.download(path)

    @supabase_call
    def delete(self, path: str) -> None:
        self._bucket.remove([path])
