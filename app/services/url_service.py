"""
URL service — handles creating short URLs.

Concurrency safety:
  - No pre-flight alias check (eliminates race condition window).
  - DB UNIQUE constraint on short_code is the single source of truth.
  - Rollback on flush failure keeps session clean.
  - commit() wrapped in try/except for full transaction safety.

Exception handling:
  - IntegrityError on custom_alias → AliasAlreadyExistsError (user error)
  - IntegrityError on generated code → RuntimeError (system error)
  - All other DB errors → re-raised as-is

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

    # Step 1 — build ORM object
    url_obj = URL(
        long_url=long_url_str,
        short_code="__pending__",
        expire_at=req.expire_at,
    )

    # Step 2 — apply custom alias if provided
    if req.custom_alias:
        url_obj.short_code = req.custom_alias

    db.add(url_obj)

    # Step 3 — first flush to get auto-generated id from DB
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        # Only treat as user error when custom_alias was provided
        if req.custom_alias:
            raise AliasAlreadyExistsError(
                f"Alias '{req.custom_alias}' is already in use."
            ) from exc
        # Generated code IntegrityError here is unexpected — re-raise as-is
        raise

    # Step 4 — generate Base62 short code from the numeric id
    if not req.custom_alias:
        url_obj.short_code = encode(url_obj.id)

        # Step 5 — second flush to persist the generated short_code
        try:
            db.flush()
        except IntegrityError as exc:
            db.rollback()
            # This is a system error — encode(id) collision should never happen
            logger.error(
                "Generated short_code collision for id=%s code=%s",
                url_obj.id,
                url_obj.short_code,
            )
            raise RuntimeError(
                f"Short code generation failed for id={url_obj.id}"
            ) from exc

    # Step 6 — commit the full transaction
    # Wrapped in try/except — rollback on failure, safe log
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("Commit failed: %s", exc)
        raise

    db.refresh(url_obj)
    logger.info("Created short_code=%s for %.80s", url_obj.short_code, long_url_str)

    # Step 7 — warm DragonflyDB cache
    # Cache failure is non-fatal — never breaks the API
    try:
        expires_iso = url_obj.expire_at.isoformat() if url_obj.expire_at else None
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

def _calculate_ttl(expire_at: datetime | None) -> int:
    """
    Return cache TTL in seconds.
    - URL has expiry  → TTL = seconds remaining until expiry (min 1)
    - URL never expires → TTL = default from settings
    """
    if expire_at is None:
        return settings.cache_ttl_seconds

    now = datetime.now(tz=timezone.utc)

    if expire_at.tzinfo is None:
        expire_at = expire_at.replace(tzinfo=timezone.utc)

    remaining = int((expire_at - now).total_seconds())
    return max(remaining, 1)