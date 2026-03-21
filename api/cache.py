"""
Redis caching layer for Bar Reviewer API
Provides get/set operations with automatic JSON serialization and TTL support
"""
import redis
import json
import os
import logging

redis_client = None

def get_redis_client():
    """Get or create Redis client instance"""
    global redis_client
    if redis_client is None:
        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            redis_client = redis.from_url(redis_url, decode_responses=True)
            # Test connection
            redis_client.ping()
            logging.info(f"Redis connected: {redis_url}")
        except Exception as e:
            logging.warning(f"Redis unavailable: {e}. Caching disabled.")
            return None
    return redis_client

def cache_get(key):
    """
    Get value from cache
    Returns: Parsed JSON data or None if not found/error
    """
    try:
        client = get_redis_client()
        if client is None:
            return None
        
        data = client.get(key)
        if data:
            logging.info(f"Cache HIT: {key}")
            return json.loads(data)
        else:
            logging.info(f"Cache MISS: {key}")
            return None
    except Exception as e:
        logging.error(f"Cache get error: {e}")
        return None

def cache_set(key, value, ttl=300):
    """
    Set value in cache with TTL
    Args:
        key: Cache key
        value: Data to cache (will be JSON serialized)
        ttl: Time-to-live in seconds (default 5 minutes)
    """
    try:
        client = get_redis_client()
        if client is None:
            return False
        
        client.setex(key, ttl, json.dumps(value, default=str))
        logging.info(f"Cache SET: {key} (TTL: {ttl}s)")
        return True
    except Exception as e:
        logging.error(f"Cache set error: {e}")
        return False

def cache_delete(key):
    """Delete key from cache"""
    try:
        client = get_redis_client()
        if client is None:
            return False
        
        client.delete(key)
        logging.info(f"Cache DELETE: {key}")
        return True
    except Exception as e:
        logging.error(f"Cache delete error: {e}")
        return False

def cache_clear_pattern(pattern):
    """Clear all keys matching pattern (e.g., 'sc_decisions:*')"""
    try:
        client = get_redis_client()
        if client is None:
            return False
        
        keys = client.keys(pattern)
        if keys:
            client.delete(*keys)
            logging.info(f"Cache CLEAR: {len(keys)} keys matching '{pattern}'")
        return True
    except Exception as e:
        logging.error(f"Cache clear error: {e}")
        return False
