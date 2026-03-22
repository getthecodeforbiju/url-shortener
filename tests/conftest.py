"""
Shared pytest fixtures.
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.session import get_db
from app.models.url import URL  
from app.main import create_app
from app.core.rate_limit import limiter as _limiter

# Single shared engine — SQLite in-memory with same connection reused
TEST_DATABASE_URL = "sqlite:///./test.db"  # file-based so all sessions share it

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)

# Create tables once
Base.metadata.create_all(bind=test_engine)


@pytest.fixture(autouse=True)
def reset_db():
    """Clean all rows between tests."""
    yield
    with test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())


# Dict-backed mock cache
@pytest.fixture(autouse=True)
def mock_cache():
    _store: dict = {}

    def fake_cache_url(short_code, long_url, expires_at_iso=None, ttl=None):
        _store[short_code] = {"long_url": long_url, "expires_at": expires_at_iso}

    def fake_get_cached_url(short_code):
        return _store.get(short_code)

    def fake_invalidate_url(short_code):
        _store.pop(short_code, None)

    with (
        patch("app.services.url_service.cache_url", side_effect=fake_cache_url),
        patch("app.services.redirect_service.cache_url", side_effect=fake_cache_url),
        patch("app.services.redirect_service.get_cached_url", side_effect=fake_get_cached_url),
        patch("app.services.cache_service.cache_url", side_effect=fake_cache_url),
        patch("app.services.cache_service.get_cached_url", side_effect=fake_get_cached_url),
        patch("app.services.cache_service.invalidate_url", side_effect=fake_invalidate_url),
    ):
        yield _store


# FastAPI TestClient
@pytest.fixture
def client(mock_cache):
    app = create_app()
    app.state.limiter = _limiter

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c