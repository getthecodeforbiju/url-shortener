"""
URL service — handles creating short URLs.

Concurrency safety:
  - No pre-flight alias check (eliminates race condition window).
  - DB UNIQUE constraint on short_code is the single source of truth.
  - begin_nested() savepoint auto-rolls back on flush failure.
  - commit() wrapped in try/except for full transaction safety.

Exception handling:
  - IntegrityError on custom_alias → AliasAlreadyExistsError (user error)
  - IntegrityError on generated code → RuntimeError (system error, re-raised)
  - All other DB errors → re-raised as-is (never silently swallowed)

Cache strategy:
  - Dynamic TTL: cache expires when the URL expires.
  - Cache failure is non-fatal — DB is always source of truth.
  - Versioned cache keys via cache_service.
"""

from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.url import URL
from app.schemas.url_request import ShortenRequest
from app.services.cache_service import cache_url
from app.utils.base62 import encode
from app.core.config import get_settings
from app.core.logging import logger

settings = get_settings()


class AliasAlreadyExistsError(Exception):
    """Raised when a requested custom alias is already taken (user error)."""


def create_short_url(db: Session, req: ShortenRequest) -> URL:
    """
    Insert a URL record, generate a Base62 short code,
    cache it, and return the ORM object.
    """
    long_url_str = str(req.long_url)

    # url_obj created inside the transaction
    with db.begin_nested():
        url_obj = URL(
            long_url=long_url_str,
            short_code="__pending__",
            expires_at=req.expires_at,
        )

        if req.custom_alias:
            url_obj.short_code = req.custom_alias

        db.add(url_obj)

        # First flush: get auto-generated id from CockroachDB 
        try:
            db.flush()
        except IntegrityError as exc:
            if req.custom_alias:
                raise AliasAlreadyExistsError(
                    f"Alias '{req.custom_alias}' is already in use."
                ) from exc
            raise

        # Generate Base62 short code from the numeric id 
        if not req.custom_alias:
            url_obj.short_code = encode(url_obj.id)

            # Second flush: persist the generated short_code 
            try:
                db.flush()
            except IntegrityError as exc:
                logger.error(
                    "Generated short_code collision for id=%s code=%s",
                    url_obj.id,
                    url_obj.short_code,
                )
                raise RuntimeError(
                     f"Short code generation failed for id={url_obj.id}"
                ) from exc

    # Savepoint exited cleanly — commit the full transaction 
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        # Safe log — no reference to url_obj which may be invalid
        logger.error("Commit failed: %s", exc)
        raise

    db.refresh(url_obj)
    logger.info("Created short_code=%s for %.80s", url_obj.short_code, long_url_str)

    # Warm DragonflyDB cache 
    try:
        expires_iso = url_obj.expire_at.isoformat() if url_obj.expires_at else None
        dynamic_ttl = _calculate_ttl(url_obj.expire_at)
        cache_url(
            short_code=url_obj.short_code,
            long_url=long_url_str,
            expires_at_iso=expires_iso,
            ttl=dynamic_ttl,
        )
    except Exception as exc:
        logger.warning("Cache warming failed for %s: %s", url_obj.short_code, exc)

    return url_obj


# Private helpers

def _calculate_ttl(expires_at: datetime | None) -> int:
    """
    Return cache TTL in seconds.
    - URL has expiry  → TTL = seconds remaining until expiry (min 1)
    - URL never expires → TTL = default from settings
    """
    if expires_at is None:
        return settings.cache_ttl_seconds

    now = datetime.now(tz=timezone.utc)

    # Simplified timezone handling — two clear steps
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    remaining = int((expires_at - now).total_seconds())
    return max(remaining, 1)