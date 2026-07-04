import logging
import jwt
from jwt import PyJWKClient
from django.conf import settings

logger = logging.getLogger(__name__)


def verify_access_token(token: str) -> dict:
    """
    Verifies a Supabase JWT access token using public keys from the JWKS endpoint.
    Validates:
      - RS256 signature
      - issuer (iss)
      - audience (aud)
      - expiration (exp)
      - issued-at (iat)
    Allows a clock skew leeway configured in Django settings.
    Returns the complete dictionary of verified claims.
    """
    if not token:
        logger.error("Token verification failed: token is empty.")
        raise ValueError("Token is missing or empty.")

    try:
        # Load JWKS client configurations from settings
        jwks_url = getattr(settings, "SUPABASE_JWKS_URL", None)
        if not jwks_url:
            raise ValueError("SUPABASE_JWKS_URL is not configured in settings.")
            
        cache_timeout = getattr(settings, "SUPABASE_JWKS_CACHE_TIMEOUT", 300)
        leeway = getattr(settings, "SUPABASE_JWT_LEEWAY", 10)
        
        # Initialize JWK Client with cache details
        jwks_client = PyJWKClient(jwks_url, cache_jwk_set=True, lifespan=cache_timeout)
        
        # 1. Get signing key matching 'kid' in the JWT header
        try:
            signing_key = jwks_client.get_signing_key_from_jwt(token)
        except jwt.PyJWKClientError as e:
            logger.error(f"JWKS retrieval failure for token key: {e}")
            raise ValueError(f"JWKS endpoint unavailable or key not found: {str(e)}") from e
        
        # 2. Configure issuer and audience for verification
        supabase_url = getattr(settings, "SUPABASE_URL", None)
        if not supabase_url:
            raise ValueError("SUPABASE_URL is not configured in settings.")
        
        issuer = f"{supabase_url}/auth/v1"
        audience = "authenticated"
        
        # 3. Decode & Validate Token (RS256 only)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=audience,
            issuer=issuer,
            leeway=leeway,
            options={
                "require": ["exp", "iss", "aud", "sub", "iat"],
            }
        )
        
        logger.info("JWT access token successfully verified.")
        return claims

    except jwt.ExpiredSignatureError as e:
        logger.error("Supabase JWT access token has expired.")
        raise ValueError("Token has expired. Please log in again.") from e
        
    except jwt.InvalidSignatureError as e:
        logger.error("Supabase JWT signature is invalid.")
        raise ValueError("Invalid token signature.") from e
        
    except jwt.InvalidIssuerError as e:
        logger.error("Supabase JWT issuer verification failed.")
        raise ValueError("Invalid token issuer.") from e
        
    except jwt.InvalidAudienceError as e:
        logger.error("Supabase JWT audience verification failed.")
        raise ValueError("Invalid token audience.") from e
        
    except jwt.DecodeError as e:
        logger.error("Supabase JWT decode error / malformed token structure.")
        raise ValueError("Malformed or invalid token.") from e
        
    except jwt.PyJWTError as e:
        logger.error(f"PyJWT verification error: {e}")
        raise ValueError(f"Token validation failed: {str(e)}") from e
        
    except ValueError:
        raise
        
    except Exception as e:
        logger.error(f"Unexpected error during JWT verification: {e}")
        raise ValueError(f"JWT verification failed: {str(e)}") from e
