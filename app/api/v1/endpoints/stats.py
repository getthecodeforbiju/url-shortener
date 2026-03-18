"""
GET /api/v1/stats/{short_code} — return click analytics.
"""

from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session

from app.core.rate_limit import limiter
from app.db.session import get_db
from app.core.utils.network import get_client_ip
from app.schemas.url_response import StatusResponse
from app.services.redirect_service import get_url_stats, URLNotFoundError
from app.core.logging import logger

router = APIRouter()


@router.get("/stats/{short_code}",response_model=StatusResponse)
@limiter.limit("60/minute", key_func=get_client_ip)
async def url_stats(
    request: Request,
    short_code: str,
    db: Session = Depends(get_db),
):
    """Return click analytics for a given short code"""
    logger.info("GET /stats requested for short_code=%s", short_code)
    
    try:
        url_obj = get_url_stats(db, short_code)
        
    except URLNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    
    except Exception as exc:
        logger.error("Unexpected error in / stats/%s: %s", short_code,exc)
        raise HTTPException(status_code=500, detail="Internal server error.")
    
    logger.info("GET .stats success short_code=%s click_count=%s",short_code, url_obj.click_count)
    
    return StatusResponse(
        short_code=url_obj.short_code,
        long_url=url_obj.long_url,
        click_count=url_obj.click_count,
        created_at=url_obj.created_at,
        expire_at=url_obj.expire_at,
    )
