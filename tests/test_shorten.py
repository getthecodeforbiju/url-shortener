"""
Integration tests for POST /api/vi/shorten
"""

from datetime import datetime, timedelta, timezone
import pytest

LONG_URL = "https://www.example.com/some/long/path"


class TestShortHappyPath:
    def test_returns_201(self, client):
        resp = client.post("/api/v1/shorten", json={"long_url": LONG_URL})
        assert resp.status_code == 201
        
    def test_response_contains_short_url(self, client):
        resp = client.post("/api/v1/shorten", json={"long_url": LONG_URL})
        assert "short_code" in resp.json()
        
    def test_response_contains_short_code(self, client):
        resp = client.post("/api/v1/shorten", json={"long_url": LONG_URL})
        assert "short_code" in resp.json()
        
    def test_response_echoes_long_url(self, client):
        resp = client.post("/api/v1/shorten", json={"long_url": LONG_URL})
        assert resp.json()["long_url"] == LONG_URL
        
    def test_short_code_is_base62(self, client):
        from app.utils.base62 import ALPHABET
        resp = client.post("/api/v1/shorten", json={"long_url": LONG_URL})
        code = resp.json()["short_code"]
        assert all(c in ALPHABET for c in code)
        
    def test_two_urls_get_different_code(self, client):
        r1 = client.post("/api/v1/shorten", json={"long_url": "https://example.com/a"})
        r2 = client.post("/api/v1/shorten", json={"long_url": "https://example.com/b"})
        assert r1.json()["short_code"] != r2.json()["short_code"]


class TestCustomAlias:
    def test_custom_alias_accepted(self, client):
        resp = client.post("/api/v1/shorten", json={
            "long_url": LONG_URL,
            "custom_alias": "my_link"
        })        
        assert resp.status_code == 201
        assert resp.json()["short_code"] == "my_link"
        
    def test_duplicate_alias_returns_409(self, client):
        payload = {"long_url": LONG_URL, "custom_alias": "duplicate"}
        client.post("/api/v1/shorten", json=payload)
        resp = client.post("/api/v1/shorten", json=payload)
        assert resp.status_code == 409
        
    def test_alias_too_short_return_422(self, client):
        resp = client.post("/api/v1/shorten", json={
            "long_url": LONG_URL,
            "custom_alias": "ab"
        })
        assert resp.status_code == 422
        
    def test_alias_with_special_chars_return_422(self, client):
        resp = client.post("/api/v1/shorten", json={
            "long_url": LONG_URL,
            "custom_alias": "bad@alias"
        })
        assert resp.status_code == 422
        
        
class TestExpiringLinks:
    def test_future_expiry_accepted(self, client):
        future = (datetime.now(tz=timezone.utc) + timedelta(hours=1)).isoformat()
        resp = client.post("/api/v1/shorten", json={
            "long_url": LONG_URL,
            "expire_at": future
        })
        assert resp.status_code == 201
        assert resp.json()["expire_at"] is not None
        
    def test_past_expiry_return_422(self, client):
        past = (datetime.now(tz=timezone.utc) - timedelta(hours=1)).isoformat()
        resp = client.post("/api/v1/shorten", json={
            "long_url": LONG_URL,
            "expire_at": past
        })
        assert resp.status_code == 422
        
class TestInvalidInput:
    def test_missing_url_returns_422(self, client):
        resp = client.post("/api/v1/shorten", json={})
        assert resp.status_code == 422
        
    def test_invalid_url_returns_422(self, client):
        resp = client.post("/api/v1/shorten", json={"long_url": "not-a-url"})
        assert resp.status_code == 422
        