import base64
import hashlib
import logging
import secrets
from django.conf import settings
from .supabase import get_supabase_client

logger = logging.getLogger(__name__)


def generate_code_verifier() -> str:
    """
    Generates a high-entropy cryptographically secure random code verifier for PKCE.
    Length is between 43 and 128 characters.
    """
    return secrets.token_urlsafe(64)[:128]


def generate_code_challenge(verifier: str) -> str:
    """
    Computes the SHA-256 code challenge for a given code verifier.
    """
    sha256_hash = hashlib.sha256(verifier.encode("utf-8")).digest()
    challenge = base64.urlsafe_b64encode(sha256_hash).decode("utf-8")
    return challenge.replace("=", "")


def generate_oauth_state() -> str:
    """
    Generates a secure random state token to protect against CSRF attacks.
    """
    return secrets.token_urlsafe(32)


def initiate_google_login(request, callback_url: str) -> str:
    """
    Initiates Google OAuth authentication flow with PKCE and State validation.
    Generates challenges and saves them in the request session.
    Returns the authorization redirect URL.
    """
    # 1. Generate PKCE values
    verifier = generate_code_verifier()
    challenge = generate_code_challenge(verifier)
    
    # 2. Generate State token for CSRF protection
    state = generate_oauth_state()
    
    # 3. Save to Django Session
    request.session["supabase_code_verifier"] = verifier
    request.session["supabase_oauth_state"] = state
    
    # 4. Initiate sign-in via Supabase Client
    supabase = get_supabase_client()
    try:
        credentials = {
            "provider": "google",
            "options": {
                "redirect_to": callback_url,
                "query_params": {
                    "code_challenge": challenge,
                    "code_challenge_method": "S256",
                    "state": state,
                }
            }
        }
        logger.info(f"Initiating Supabase Google OAuth with callback url: {callback_url}")
        res = supabase.auth.sign_in_with_oauth(credentials)
        
        if not res or not getattr(res, "url", None):
            raise ValueError("No authorization URL returned from Supabase OAuth initiation.")
            
        return res.url
        
    except Exception as e:
        logger.error(f"Error initiating Supabase Google OAuth: {e}")
        raise ValueError(f"Failed to initiate Google sign-in: {str(e)}")


def handle_oauth_callback(request, code: str, state: str) -> dict:
    """
    Handles the Google OAuth callback. Validates state, exchanges the raw authorization
    code/verifier for a session, and saves minimum session info in the session structure.
    """
    # 1. State Validation (CSRF check)
    original_state = request.session.pop("supabase_oauth_state", None)
    if not original_state or state != original_state:
        logger.error("State validation failed: missing state or mismatch.")
        raise ValueError("Security validation failed (State mismatch). Please try logging in again.")

    # 2. Retrieve code verifier
    code_verifier = request.session.pop("supabase_code_verifier", None)
    if not code_verifier:
        logger.error("Code verifier is missing from session.")
        raise ValueError("Session verification expired. Please initiate login again.")
        
    if not code:
        logger.error("Authorization code is missing from callback.")
        raise ValueError("Missing authorization code from identity provider.")

    # 3. Exchange code for session
    supabase = get_supabase_client()
    try:
        logger.info("Exchanging authorization code for session.")
        res = supabase.auth.exchange_code_for_session({
            "auth_code": code,
            "code_verifier": code_verifier,
        })
        
        session = getattr(res, "session", None)
        if not session:
            raise ValueError("No session returned from token exchange.")
            
        # 4. Store minimum session info required
        auth_session_data = {
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
            "expires_at": session.expires_at,
            "user_id": session.user.id if session.user else None,
            "user_email": session.user.email if session.user else None,
        }
        
        # Save in Django Session
        request.session["supabase_auth_session"] = auth_session_data
        logger.info(f"Successfully established Supabase session for user {auth_session_data.get('user_email')}.")
        return auth_session_data

    except Exception as e:
        logger.error(f"Error exchanging authorization code for session: {e}")
        raise ValueError(f"Failed to authenticate with Supabase: {str(e)}")
