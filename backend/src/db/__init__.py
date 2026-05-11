from supabase import create_client, Client
from src.config import settings

# Service role client — server-side only, never expose to frontend
db: Client = create_client(settings.supabase_url, settings.supabase_service_role_key)






























  

