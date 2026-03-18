from fastapi import APIRouter
from app.api.v1.endpoints import shorten, redirect, stats

api_router = APIRouter()

api_router.include_router(shorten.router, tags=["Shorten"])
api_router.include_router(stats.router, tags=["Stats"])

# Redirect must be last — it catches all /{short_code} patterns
api_router.include_router(redirect.router, tags=["Redirect"])