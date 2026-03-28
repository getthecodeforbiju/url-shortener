from contextlib import asynccontextmanager
from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import get_settings
from app.core.logging import logger
from app.core.rate_limit import limiter
from app.api.v1 import api_router

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s ...", settings.app_name)
    yield
    logger.info("Shutting down %s", settings.app_name)
    
def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description="Production-style URL shortener - FastAPI + CockroachDB + DragonflyDB ",
        version="1.0.0",
        lifespan=lifespan,
    )
    
    #rate limiter
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    
    # Health check
    @app.get("/health",tags=["Health"])
    async def health():
        return {"status": "ok", "service": settings.app_name}
    
    # ALL API routes under api/v1
    app.include_router(api_router, prefix="/api/v1")
    
    return app

app = create_app()
    
        
    