"""
Integration tests for GET /api/v1/r/{short_code} and GET /api/v1/stats/{short_code}
"""

from datetime import datetime, timedelta, timezone
import pytest

LONG_URL = "https://www.example.com/target"


def create_short(client, long_url=LONG_URL, **kwargs):
    """Helper — POST /shorten and return response body."""
    resp = client.post("/api/v1/shorten", json={"long_url": long_url, **kwargs})
    assert resp.status_code == 201, resp.text
    return resp.json()


class TestRedirect:
    def test_redirect_returns_307(self, client):
        data = create_short(client)
        resp = client.get(f"/api/v1/r/{data['short_code']}", follow_redirects=False)
        assert resp.status_code == 307

    def test_redirect_location_header(self, client):
        data = create_short(client)
        resp = client.get(f"/api/v1/r/{data['short_code']}", follow_redirects=False)
        assert resp.headers["location"] == LONG_URL

    def test_unknown_code_returns_404(self, client):
        resp = client.get("/api/v1/r/doesnotexist", follow_redirects=False)
        assert resp.status_code == 404

    def test_invalid_code_returns_400(self, client):
        resp = client.get("/api/v1/r/@@@invalid", follow_redirects=False)
        assert resp.status_code == 400

    def test_too_long_code_returns_400(self, client):
        long_code = "a" * 33
        resp = client.get(f"/api/v1/r/{long_code}", follow_redirects=False)
        assert resp.status_code == 400


class TestExpiredURL:
    def test_expired_url_returns_410(self, client, mock_cache):
        future = (datetime.now(tz=timezone.utc) + timedelta(seconds=2)).isoformat()
        data = create_short(client, expire_at=future)
        code = data["short_code"]

        # Simulate expiry by overwriting cache with past timestamp
        past_iso = (datetime.now(tz=timezone.utc) - timedelta(hours=1)).isoformat()
        mock_cache[code] = {"long_url": LONG_URL, "expire_at": past_iso}

        resp = client.get(f"/api/v1/r/{code}", follow_redirects=False)
        assert resp.status_code == 410


class TestClickCounter:
    def test_click_count_increments(self, client, mock_cache):
        data = create_short(client)
        code = data["short_code"]

        mock_cache.clear()  # force DB path so counter increments
        client.get(f"/api/v1/r/{code}", follow_redirects=False)

        stats = client.get(f"/api/v1/stats/{code}").json()
        assert stats["click_count"] >= 1


class TestCacheBehaviour:
    def test_cache_populated_after_creation(self, client, mock_cache):
        data = create_short(client)
        assert data["short_code"] in mock_cache

    def test_redirect_works_after_cache_cleared(self, client, mock_cache):
        data = create_short(client)
        mock_cache.clear()  # simulate cache eviction
        resp = client.get(f"/api/v1/r/{data['short_code']}", follow_redirects=False)
        assert resp.status_code == 307


class TestStats:
    def test_stats_returns_200(self, client):
        data = create_short(client)
        resp = client.get(f"/api/v1/stats/{data['short_code']}")
        assert resp.status_code == 200

    def test_stats_fields_present(self, client):
        data = create_short(client)
        stats = client.get(f"/api/v1/stats/{data['short_code']}").json()
        for field in ("short_code", "long_url", "click_count", "created_at"):
            assert field in stats

    def test_stats_unknown_code_returns_404(self, client):
        resp = client.get("/api/v1/stats/nonexistent")
        assert resp.status_code == 404

    def test_initial_click_count_is_zero(self, client):
        data = create_short(client)
        stats = client.get(f"/api/v1/stats/{data['short_code']}").json()
        assert stats["click_count"] == 0