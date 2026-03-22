"""
Redirect service — resolves a short code to a long URL
and increments the click counter.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.url import URL
from app.services.cache_service import cache_url, get_cached_url
from app.core.logging import logger


class URLNotFoundError(Exception):
    """Raised when short_code does not exists ."""
    
class URLExpiredError(Exception):
    """Raised when short_code exists but has passed its expiry"""
    

def resolve_url(db: Session, short_code: str) -> str:
    """
    Resolve short_code → long_url.
    Checks cache first, falls back to DB.
    Increments click counter on every hit.
    """
    now = datetime.now(tz=timezone.utc)
    
    # Step 1 - check DragonflyDB cache
    cached = get_cached_url(short_code)
    if cached:
        _check_expiry(cached.get("expire_at"), now, short_code)
        _increment_click(db, short_code)
        return cached["long_url"]
    
    # Step 2 - cache miss, query CockroachDB
    url_obj = db.query(URL).filter(URL.short_code == short_code).first()
    if not url_obj:
        raise URLNotFoundError(f"Short code '{short_code}' not found.")
    
    # Step 3 - check expiry
    if url_obj.expire_at:
        exp = url_obj.expire_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp < now:
            raise URLExpiredError(f"Short code '{short_code}' has expired.")
        
    # Step 4 - re-warm the cache
    expires_iso = url_obj.expire_at.isoformat() if url_obj.expire_at else None
    cache_url(short_code, url_obj.long_url, expires_iso)
    
    # Step 5 - increment click counter
    _increment_click(db, short_code)
    
    logger.info("Resolved short_code=%s -> %.80s", short_code, url_obj.long_url)
    return url_obj.long_url

def get_url_stats(db: Session, short_code: str) -> URL:
    """Return the URL object for analytics. Raises URLNotFoundError if absent."""
    url_obj = db.query(URL).filter(URL.short_code == short_code).first()
    if not url_obj:
        raise URLNotFoundError(f"Short code '{short_code}' not found")
    return url_obj

# Private helpers

def _check_expiry(expires_at_iso: Optional[str], now: datetime, short_code: str) -> None:
    if  not expires_at_iso:
        return
    exp = datetime.fromisoformat(expires_at_iso)
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if exp < now:
        raise URLExpiredError(f"Short code '{short_code}' has expired.")
    
def _increment_click(db: Session, short_code: str) -> None:
    db.query(URL).filter(URL.short_code == short_code).update(
        {URL.click_count: URL.click_count +  1}
    )
    db.commit()
    
        