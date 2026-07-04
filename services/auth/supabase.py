import logging
from django.conf import settings
from supabase import create_client, Client

logger = logging.getLogger(__name__)

# Cached client instances for reuse
_client_instance: Client = None
_service_role_client_instance: Client = None


def get_supabase_client() -> Client:
    """
    Returns a cached Supabase Client instance initialized with the anonymous key.
    Suitable for standard client-side interactions and normal user role actions.
    """
    global _client_instance
    if _client_instance is None:
        url = getattr(settings, "SUPABASE_URL", None)
        key = getattr(settings, "SUPABASE_ANON_KEY", None)
        if not url or not key:
            raise ValueError("Supabase URL or public anonymous key configuration is missing.")
        
        logger.info("Initializing Supabase client with anonymous/public key.")
        _client_instance = create_client(url, key)
        
    return _client_instance


def get_supabase_service_role_client() -> Client:
    """
    Returns a cached Supabase Client instance initialized with the service role key.
    Warning: This client bypasses Row-Level Security (RLS) policies. Use with caution.
    """
    global _service_role_client_instance
    if _service_role_client_instance is None:
        url = getattr(settings, "SUPABASE_URL", None)
        key = getattr(settings, "SUPABASE_SERVICE_ROLE_KEY", None)
        if not url or not key:
            raise ValueError("Supabase URL or service role key configuration is missing.")
            
        logger.info("Initializing Supabase client with service role key.")
        _service_role_client_instance = create_client(url, key)
        
    return _service_role_client_instance
