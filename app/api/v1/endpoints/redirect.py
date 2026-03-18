"""
GET /r/{short_code} — redirect to the original long URL.

Route prefix /r/ avoids conflicts with /docs, /health, /favicon.ico etc.
"""

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.rate_limit import limiter
from app.core.utils.network import get_client_ip
from app.services.redirect_service import (
    resolve_url,
    URLNotFoundError,
    URLExpiredError,
)
from app.core.logging import logger

router = APIRouter()

# Only allow Base62 characters — 0-9, A-Z, a-z, hyphens, underscores
VALID_SHORT_CODE_CHARS = frozenset(
    "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_"
)

MAX_CODE_LENGTH = 32


def _is_valid_short_code(code: str) -> bool:
    """Return True if short_code only contains valid Base62 + alias characters."""
    return (
        bool(code)
        and len(code) <= MAX_CODE_LENGTH
        and all(c in VALID_SHORT_CODE_CHARS for c in code)
    )


@router.get("/r/{short_code}")
@limiter.limit("120/minute", key_func=get_client_ip)
async def redirect_url(
    request: Request,
    short_code: str,
    db: Session = Depends(get_db),
):
    """Resolve a short code and issue an HTTP 307 redirect."""

    short_code = short_code.strip()

    if not _is_valid_short_code(short_code):
        raise HTTPException(status_code=400, detail="Invalid short code format.")

    logger.info("Redirect request short_code=%s", short_code)

    try:
        long_url = resolve_url(db, short_code)

    except URLNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    except URLExpiredError as exc:
        raise HTTPException(status_code=410, detail=str(exc))

    except Exception as exc:
        logger.error("Unexpected error resolving short_code=%s: %s", short_code, exc)
        raise HTTPException(status_code=500, detail="Internal server error.")

    logger.info("Redirect success short_code=%s → %.80s", short_code, long_url)

    return RedirectResponse(url=long_url, status_code=307)