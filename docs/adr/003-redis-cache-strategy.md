# ADR 003: Redis Cache Strategy for API Responses

**Status:** Accepted  
**Date:** 2024

## Context

Supreme Court decisions queries, flashcard concept loading, and RSS feed proxying are read-heavy and relatively stable. The PostgreSQL query and row-transfer cost for large decision lists was causing slow response times.

## Decision

Use **Azure Cache for Redis** as a JSON cache layer in front of PostgreSQL, with graceful fallback when Redis is unavailable.

## Reasons

- Redis reduces PostgreSQL load for identical queries within the TTL window.
- The `cache.py` module wraps Redis with try/except on every operation; a Redis outage falls back to direct DB queries without crashing the API.
- TTLs are tunable via environment variables (see `config.py` and `cache.py` documentation).
- The flashcard concepts key uses a versioned pattern (`flashcard_concepts:vN:bar_2026`) so a data refresh can be forced by bumping the key in `FLASHCARD_CONCEPTS_CACHE_KEY` without a deploy.

## TTL reference

| Data | Default TTL | Invalidation |
|------|------------|-------------|
| SC decisions list | 60 s | Auto |
| Decision detail | 600 s | Auto |
| Ponentes / filters | 300 s | Auto |
| SC judiciary feed | 900 s | Auto |
| Flashcard concepts | 86400 s (1d) | Bump `FLASHCARD_CONCEPTS_CACHE_KEY` env or call `cache_delete()` |
| Audio codal bounds | Worker lifetime | Bump `CACHE_VERSION` in `audio_provider.py` and redeploy |

## Consequences

- **Positive:** P50 latency for decisions list dropped significantly after warm-up.
- **Negative:** Stale data window equals TTL; writes to DB are not reflected until TTL expires or cache is manually invalidated.
- **Negative:** If Redis is misconfigured, every request hits PostgreSQL (acceptable performance but not ideal).
- **Negative:** `REDIS_ENABLED=false` disables all caching; use in testing environments where Redis is unavailable.
