import os
import jwt
import logging
from jwt import PyJWKClient

# Clerk publishable key is needed for the JWKS URL if we want to be dynamic, 
# but usually it's cleaner to just use the secret key for backend actions.
# However, for JWT validation, we need the JWKS.
CLERK_SECRET_KEY = (os.environ.get("CLERK_SECRET_KEY") or "").strip().strip("'").strip('"')

# Optional env override; otherwise JWKS is derived from JWT `iss` (see _jwks_url_for_token).
_DEFAULT_JWKS = "https://capital-ghost-60.clerk.accounts.dev/.well-known/jwks.json"
CLERK_JWKS_URL = (os.environ.get("CLERK_JWKS_URL") or "").strip() or _DEFAULT_JWKS

_jwks_clients = {}


def _jwks_url_for_token(token):
    """Use issuer from token so RS256 validates for any Clerk Frontend API domain."""
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        iss = payload.get("iss")
        if iss and isinstance(iss, str):
            return iss.rstrip("/") + "/.well-known/jwks.json"
    except Exception:
        pass
    return CLERK_JWKS_URL


def get_jwks_client(jwks_url=None):
    url = jwks_url or CLERK_JWKS_URL
    if url not in _jwks_clients:
        _jwks_clients[url] = PyJWKClient(url)
    return _jwks_clients[url]


def validate_clerk_token(token):
    """
    Validates a Clerk JWT token directly.
    Returns (user_id, error_msg).
    """
    if not token:
        return None, "Empty token"

    try:
        header = jwt.get_unverified_header(token)
        alg = header.get("alg")
        
        if alg == "HS256":
            if not CLERK_SECRET_KEY:
                return None, "Backend missing CLERK_SECRET_KEY for HS256 token"
            payload = jwt.decode(
                token, 
                CLERK_SECRET_KEY, 
                algorithms=["HS256"],
                options={"verify_aud": False}
            )
            return payload.get("sub"), None
        elif alg == "RS256":
            jwks_url = _jwks_url_for_token(token)
            client = get_jwks_client(jwks_url)
            signing_key = client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                options={"verify_aud": False} 
            )
            return payload.get("sub"), None
        else:
            return None, f"Unsupported algorithm: {alg}"
    except jwt.ExpiredSignatureError:
        return None, "Token expired"
    except Exception as e:
        # Diagnostic logging for server-side troubleshooting
        t_len = len(token) if token else 0
        logging.error(f"Clerk Auth Error ({type(e).__name__}): {str(e)} [t_len={t_len}]")
        return None, f"Auth Error: {str(e)}"

def get_authenticated_user_id(req):
    """
    Extracts and validates the Clerk JWT from the request headers.
    Returns the user's Clerk ID (sub) if valid, else None.
    """
    # 1. Check custom header first to bypass Azure hijacking
    auth_header = req.headers.get("X-Clerk-Authorization")
    
    # 2. Fallback to standard Authorization header
    if not auth_header:
        auth_header = req.headers.get("Authorization")
        
    if not auth_header:
        return None, "Missing Authorization Header"

    # Handle "Bearer <token>" format
    parts = auth_header.strip().split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None, "Invalid Authorization Header Format"
        
    token = parts[1]
    clerk_id, error = validate_clerk_token(token)
    
    if error:
        logging.warning(f"Authentication failed: {error}")
        return None, error
        
    return clerk_id, None
