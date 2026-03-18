"""
Cache service — DragonflyDB (Redis-compatible protocol).

Key schema (versioned):
    v1:url:{short_code} → JSON payload with long_url and expires_at
"""

import json
import redis
from typing import Optional
from app.core.config import get_settings
from app.core.logging import logger

settings = get_settings()

_dragonfly_client: Optional[redis.Redis] = None

# Cache key version prefix — increment to v2 for future migrations
CACHE_KEY_VERSION = "v1"


def _key(short_code: str) -> str:
    """Build a versioned cache key."""
    return f"{CACHE_KEY_VERSION}:url:{short_code}"


def get_dragonfly() -> redis.Redis:
    """Return a singleton DragonflyDB client."""
    global _dragonfly_client
    if _dragonfly_client is None:
        _dragonfly_client = redis.from_url(
            settings.dragonfly_url,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
        )
    return _dragonfly_client


def cache_url(
    short_code: str,
    long_url: str,
    expires_at_iso: Optional[str] = None,
    ttl: Optional[int] = None,               
) -> None:
    """Store a short_code → long_url mapping in DragonflyDB."""
    try:
        client = get_dragonfly()
        payload = json.dumps({
            "long_url": long_url,
            "expires_at": expires_at_iso,
        })
        effective_ttl = ttl if ttl is not None else settings.cache_ttl_seconds
        client.setex(_key(short_code), effective_ttl, payload)
        logger.debug("Cached %s (ttl=%ss)", _key(short_code), effective_ttl)
    except redis.RedisError as exc:
        logger.warning("Cache write failed for %s: %s", short_code, exc)


def get_cached_url(short_code: str) -> Optional[dict]:
    """
    Return cached payload or None on miss/error.
    Returns: {"long_url": str, "expires_at": str | None}
    """
    try:
        client = get_dragonfly()
        raw = client.get(_key(short_code))
        if raw:
            logger.debug("Cache HIT for %s", _key(short_code))
            return json.loads(raw)
        logger.debug("Cache MISS for %s", _key(short_code))
        return None
    except redis.RedisError as exc:
        logger.warning("Cache read failed for %s: %s", short_code, exc)
        return None


def invalidate_url(short_code: str) -> None:
    """Remove a cached entry."""
    try:
        get_dragonfly().delete(_key(short_code))
        logger.debug("Cache invalidated for %s", _key(short_code))
    except redis.RedisError as exc:
        logger.warning("Cache invalidation failed for %s: %s", short_code, exc)


def ping() -> bool:
    """Health check — True if DragonflyDB is reachable."""
    try:
        return get_dragonfly().ping()
    except redis.RedisError:
        return False