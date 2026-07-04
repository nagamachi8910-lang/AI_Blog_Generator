import logging

logger = logging.getLogger(__name__)


def extract_identity(claims: dict) -> dict:
    """
    Extracts and normalizes user identity parameters from a verified Supabase JWT claims payload.
    Returns:
      - supabase_user_id (str)
      - email (str)
      - provider (str)
      - role (str)
      - email_verified (bool)
    """
    if not claims:
        raise ValueError("Invalid claims: dictionary is empty.")

    supabase_user_id = claims.get("sub")
    if not supabase_user_id:
        raise ValueError("Identity extraction failed: 'sub' (Supabase user ID) is required.")

    # Locate provider: check app_metadata, fallback to user_metadata or default to "email"
    app_metadata = claims.get("app_metadata", {})
    user_metadata = claims.get("user_metadata", {})
    
    provider = app_metadata.get("provider") or user_metadata.get("provider") or "email"
    role = claims.get("role", "authenticated")
    
    # Locate email verification status: check key directly or nested metadata structures
    email_verified = False
    if "email_verified" in claims:
        email_verified = claims["email_verified"]
    elif "email_verified" in app_metadata:
        email_verified = app_metadata["email_verified"]
    elif "email_verified" in user_metadata:
        email_verified = user_metadata["email_verified"]

    normalized_identity = {
        "supabase_user_id": supabase_user_id,
        "email": claims.get("email"),
        "provider": provider,
        "role": role,
        "email_verified": bool(email_verified),
    }

    logger.debug(f"Extracted identity: {normalized_identity['supabase_user_id']} ({normalized_identity['email']})")
    return normalized_identity
