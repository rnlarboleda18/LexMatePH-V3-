"""
Redis helpers for LexCode / codal JSON that rarely changes (long TTL).

Uses CACHE_TTL_CODAL_STATIC from config (default 24h). Respects ?nocache=1 like supreme.py.
"""
from config import REDIS_ENABLED, CACHE_TTL_CODAL_STATIC
from cache import cache_get, cache_set


def codal_cache_bypass(req) -> bool:
    try:
        return (req.params.get("nocache") or "").lower() in ("1", "true", "yes")
    except Exception:
        return False


def codal_try_get(req, cache_key: str):
    """Return cached Python object (dict/list) or None."""
    if codal_cache_bypass(req) or not REDIS_ENABLED:
        return None
    return cache_get(cache_key)


def codal_set(cache_key: str, payload, ttl=None) -> None:
    if not REDIS_ENABLED:
        return
    cache_set(cache_key, payload, ttl=ttl if ttl is not None else CACHE_TTL_CODAL_STATIC)
