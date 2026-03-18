"""
POST /api/v1/shorten — create a short URL.
"""

from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.core.utils.network import get_client_ip
from app.schemas.url_request import ShortenRequest
from app.schemas.url_response import ShortenResponse
from app.services.url_service import create_short_url, AliasAlreadyExistsError
from app.core.logging import logger

router = APIRouter()
settings = get_settings()


@router.post("/shorten", response_model=ShortenResponse, status_code=201)
@limiter.limit("30/minute", key_func=get_client_ip)
async def shorten_url(
    request: Request,
    payload: ShortenRequest,
    db: Session = Depends(get_db),
):
    """Create a shortened URL with optional custom alias and expiry."""
    logger.info("POST /shorten requested for URL=%.80s", payload.long_url)

    try:
        url_obj = create_short_url(db, payload)

    except AliasAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    except RuntimeError as exc:
        logger.error(
            "Short code generation failed for URL=%.80s: %s",
            payload.long_url,
            exc,
        )
        raise HTTPException(status_code=500, detail="Internal server error.")

    except Exception as exc:
        logger.error("Unexpected error in /shorten for URL=%.80s: %s", payload.long_url, exc)
        raise HTTPException(status_code=500, detail="Internal server error.")

    base = settings.base_url.rstrip("/")
    short_url = f"{base}/{url_obj.short_code}"

    logger.info("POST /shorten success short_code=%s", url_obj.short_code)

    return ShortenResponse(
        short_url=short_url,
        short_code=url_obj.short_code,
        long_url=url_obj.long_url,
        expires_at=url_obj.expires_at,
        created_at=url_obj.created_at,
    )