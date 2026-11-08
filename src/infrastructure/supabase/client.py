from supabase import Client, create_client

from src.core.config import settings


def create_supabase_client(url: str = settings.supabase_url, key: str = settings.supabase_service_key) -> Client:
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env.")
    return create_client(url, key)
