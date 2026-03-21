import os
import jwt
import requests
import logging
from jwt import PyJWKClient

# Clerk publishable key is needed for the JWKS URL if we want to be dynamic, 
# but usually it's cleaner to just use the secret key for backend actions.
# However, for JWT validation, we need the JWKS.
CLERK_SECRET_KEY = (os.environ.get("CLERK_SECRET_KEY") or "").strip().strip("'").strip('"')

# Replace this with your specific Clerk instance URL or use the publishable key to derive it
# For development, it's often something like:
# https://capital-ghost-60.clerk.accounts.dev/.well-known/jwks.json
CLERK_JWKS_URL = "https://capital-ghost-60.clerk.accounts.dev/.well-known/jwks.json"

_jwks_client = None

def get_jwks_client():
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(CLERK_JWKS_URL)
    return _jwks_client

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
            client = PyJWKClient(CLERK_JWKS_URL)
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
